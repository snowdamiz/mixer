defmodule MixerHosted.Builds.Coordinator do
  @moduledoc """
  Internal Oban build coordinator, unavailable without a trusted dispatch adapter.

  Jobs wake reconciliation; their arguments never authorize execution. Every
  invocation replays the exact scoped journal and rejects superseded intents.
  Admission/start and all resulting intents are committed before external I/O.
  A lease transfer preserves the original worker operation and its fence.
  Uncertain effects retain capacity, including after callback death or timeout.
  """
  use Oban.Worker, queue: :builds, max_attempts: 20
  alias Ecto.Multi
  alias MixerHosted.Builds.{Admission, Dispatch, Lifecycle, Storage}
  alias MixerHosted.Repo

  @scope [:organization_id, :project_id, :application_id, :build_id, :platform]
  @keys Enum.map(@scope, &Atom.to_string/1) ++
          ["build_record_id", "revision", "attempt", "fence", "kind"]
  @kinds ["created", "start", "cancel", "expire", "completed", "stopped", "retry"]
  @terminal [:succeeded, :failed, :cancelled, :timed_out]

  @impl true
  def perform(%Oban.Job{args: args} = job) do
    with {:ok, scope} <- arguments(args),
         {:ok, current} <- Storage.read(scope),
         :ok <- current_intent(current, args),
         {:ok, config} <- configuration() do
      owner = "oban:#{job.id || "manual"}:#{Ecto.UUID.generate()}"
      reconcile(current, scope, args, owner, config)
    else
      {:error, :superseded_intent} -> :ok
      {:error, :invalid_intent} -> {:cancel, :invalid_build_intent}
      {:error, :not_found} -> {:cancel, :build_not_found}
      {:error, error} -> {:error, error}
    end
  end

  defp reconcile(%{build: %{state: state}} = current, scope, args, owner, config)
       when state in @terminal do
    case transaction(
           Admission.claim_multi(Multi.new(), :claim, scope, owner, config.lease_ttl_ms)
           |> Multi.merge(fn %{claim: claimed} ->
             with_current(claimed, args, fn ->
               Admission.release_multi(
                 Multi.new(),
                 :release,
                 claimed.token,
                 terminal_event(claimed)
               )
             end)
           end)
         ) do
      {:ok, _} -> retry(current, scope, config)
      {:error, :attempt_already_released} -> retry(current, scope, config)
      {:error, :not_queued} -> retry(current, scope, config)
      {:error, :superseded_intent} -> :ok
      {:error, _} -> snooze(config)
    end
  end

  defp reconcile(_current, scope, args, owner, config) do
    multi =
      Admission.claim_multi(Multi.new(), :claim, scope, owner, config.lease_ttl_ms)
      |> Multi.merge(fn %{claim: claimed} ->
        with_current(claimed, args, fn -> prepare(claimed) end)
      end)

    case transaction(multi) do
      {:ok, %{prepared: :transitioned}} -> :ok
      {:ok, %{prepared: context}} -> external(context, args, config)
      {:error, :superseded_intent} -> :ok
      {:error, _} -> snooze(config)
    end
  end

  defp prepare(%{build: %{state: :queued}} = context) do
    {:ok, ref} = Lifecycle.worker_ref(context.build)

    transition(context, :start, %{type: :start, ref: ref})
    |> Admission.yield_multi(:yield, context.token)
    |> Multi.put(:prepared, :transitioned)
  end

  defp prepare(%{build: %{state: :running}} = context)
       when context.now_ms >= context.build.deadline do
    transition(context, :expire, %{type: :expire, ref: context.build.active_ref})
    |> Admission.yield_multi(:yield, context.token)
    |> Multi.put(:prepared, :transitioned)
  end

  defp prepare(context), do: Multi.new() |> Multi.put(:prepared, context)

  defp external(context, args, config) do
    with {:ok, context} <- refresh(context.token, args, config),
         request = Dispatch.request(context),
         {:ok, status} <- invoke(:query, request, config) do
      case status do
        terminal when is_tuple(terminal) -> finish(context, args, terminal, config)
        :running when context.build.state == :running -> wait(context, config)
        _ -> act(context, args, config)
      end
    else
      {:error, :superseded_intent} -> :ok
      {:error, _} -> wait(context, config)
    end
  end

  defp act(context, args, config) do
    # Recheck SQL ownership, current intent and deadline between callbacks.
    with {:ok, context} <- refresh(context.token, args, config),
         request = Dispatch.request(context),
         callback = if(context.build.state == :running, do: :ensure_started, else: :stop),
         {:ok, status} <- invoke(callback, request, config) do
      case status do
        terminal when is_tuple(terminal) -> finish(context, args, terminal, config)
        _ -> wait(context, config)
      end
    else
      {:error, :superseded_intent} -> :ok
      {:error, _} -> wait(context, config)
    end
  end

  defp refresh(token, args, config) do
    multi =
      Admission.renew_multi(Multi.new(), :renew, token, config.lease_ttl_ms)
      |> Multi.merge(fn %{renew: renewed} ->
        with_current(renewed, args, fn ->
          if renewed.build.state == :running and renewed.now_ms >= renewed.build.deadline do
            transition(renewed, :expire, %{type: :expire, ref: renewed.build.active_ref})
            |> Admission.yield_multi(:yield, renewed.token)
            |> Multi.put(:current, :transitioned)
          else
            Multi.new() |> Multi.put(:current, renewed)
          end
        end)
      end)

    case transaction(multi) do
      {:ok, %{current: :transitioned}} -> {:error, :superseded_intent}
      {:ok, %{current: current}} -> {:ok, current}
      error -> error
    end
  end

  defp finish(context, args, status, config) do
    {kind, event} =
      case status do
        {:completed, result} ->
          {:completed, %{type: :completed, ref: context.build.active_ref, result: result}}

        {:stopped, digest} ->
          {:stopped, %{type: :stopped, ref: context.build.active_ref, diagnostic_sha256: digest}}
      end

    id = event_id(context, kind)

    multi =
      Admission.renew_multi(Multi.new(), :renew, context.token, config.lease_ttl_ms)
      |> Multi.merge(fn %{renew: latest} ->
        with_current(latest, args, fn ->
          transition(latest, kind, event, id)
          |> Admission.release_multi(:release, latest.token, id)
        end)
      end)

    case transaction(multi) do
      {:ok, _} -> :ok
      {:error, :superseded_intent} -> :ok
      {:error, _} -> wait(context, config)
    end
  end

  defp retry(current, scope, config) do
    {:ok, status} = Lifecycle.customer_status(current.build)

    if status.retryable do
      multi =
        Admission.retry_multi(
          Multi.new(),
          :retry,
          scope,
          current.record.revision,
          event_id(current, :retry),
          &__MODULE__.new/1
        )

      case transaction(multi) do
        {:ok, _} -> :ok
        {:error, :released_current_attempt_required} -> :ok
        {:error, _} -> snooze(config)
      end
    else
      :ok
    end
  end

  defp transition(context, kind, event, id \\ nil) do
    Admission.transition_multi(
      Multi.new(),
      :transition,
      context.token,
      context.record.revision,
      id || event_id(context, kind),
      event,
      &__MODULE__.new/1
    )
  end

  defp with_current(context, args, fun) do
    case current_intent(context, args) do
      :ok -> fun.()
      error -> Multi.new() |> Multi.run(:intent, fn _, _ -> error end)
    end
  end

  defp event_id(context, kind),
    do: "coordinator:#{context.build.attempt}:#{context.record.revision}:#{kind}"

  defp terminal_event(context) do
    # Terminal state follows the last replayed event. Do not choose an earlier
    # cancellation merely because both events happened in the same millisecond.
    List.last(context.record.journal["events"])["id"]
  end

  defp current_intent(current, args) do
    kind =
      case List.last(current.record.journal["events"]) do
        nil -> "created"
        event -> event["event"]["type"]
      end

    if current.record.id == args["build_record_id"] and
         current.record.revision == args["revision"] and
         current.build.attempt == args["attempt"] and current.build.fence == args["fence"] and
         kind == args["kind"],
       do: :ok,
       else: {:error, :superseded_intent}
  end

  defp arguments(args) when is_map(args) and map_size(args) == length(@keys) do
    with true <- Enum.all?(@keys, &Map.has_key?(args, &1)),
         {:ok, _} <- Ecto.UUID.cast(args["build_record_id"]),
         true <- is_integer(args["revision"]) and args["revision"] in 0..32,
         true <- is_integer(args["attempt"]) and args["attempt"] in 1..5,
         true <- is_integer(args["fence"]) and args["fence"] in 1..9_223_372_036_854_775_807,
         true <- args["kind"] in @kinds,
         true <- args["platform"] in ["ios", "android"],
         true <- Enum.all?(@scope -- [:platform], &text?(args[Atom.to_string(&1)])) do
      scope = Map.new(@scope, &{&1, args[Atom.to_string(&1)]})
      {:ok, %{scope | platform: if(scope.platform == "ios", do: :ios, else: :android)}}
    else
      _ -> {:error, :invalid_intent}
    end
  end

  defp arguments(_), do: {:error, :invalid_intent}

  defp text?(value),
    do:
      is_binary(value) and byte_size(value) in 1..128 and String.valid?(value) and
        String.printable?(value)

  defp configuration do
    case Application.get_env(:mixer_hosted, :build_dispatch) do
      config when is_list(config) ->
        if Keyword.keyword?(config) and length(config) == 4 and
             Enum.sort(Keyword.keys(config)) ==
               Enum.sort([:adapter, :lease_ttl_ms, :call_timeout_ms, :poll_ms]) do
          c = Map.new(config)

          if is_atom(c.adapter) and c.adapter != nil and Code.ensure_loaded?(c.adapter) and
               Enum.all?([:query, :ensure_started, :stop], &function_exported?(c.adapter, &1, 1)) and
               is_integer(c.call_timeout_ms) and c.call_timeout_ms in 1..10_000 and
               is_integer(c.lease_ttl_ms) and c.lease_ttl_ms in 1..300_000 and
               c.lease_ttl_ms >= 3 * c.call_timeout_ms and
               is_integer(c.poll_ms) and c.poll_ms in 1..60_000,
             do: {:ok, c},
             else: {:error, :invalid_dispatch_configuration}
        else
          {:error, :invalid_dispatch_configuration}
        end

      nil ->
        {:error, :dispatch_unavailable}

      _ ->
        {:error, :invalid_dispatch_configuration}
    end
  end

  defp invoke(callback, request, config) do
    parent = self()
    reference = make_ref()

    {pid, monitor} =
      spawn_monitor(fn ->
        transport = self()

        # The external operation survives locally, but its BEAM transport must
        # not leak when its coordinator is abruptly terminated.
        spawn(fn ->
          parent_monitor = Process.monitor(parent)
          transport_monitor = Process.monitor(transport)

          receive do
            {:DOWN, ^parent_monitor, :process, ^parent, _} -> Process.exit(transport, :kill)
            {:DOWN, ^transport_monitor, :process, ^transport, _} -> :ok
          end
        end)

        result =
          try do
            apply(config.adapter, callback, [request])
          rescue
            _ -> {:error, :uncertain}
          catch
            _, _ -> {:error, :uncertain}
          end

        send(parent, {reference, result})
      end)

    result =
      receive do
        {^reference, value} ->
          Process.demonitor(monitor, [:flush])
          value

        {:DOWN, ^monitor, :process, ^pid, _reason} ->
          {:error, :uncertain}
      after
        config.call_timeout_ms ->
          Process.exit(pid, :kill)

          receive do
            {:DOWN, ^monitor, :process, ^pid, _} -> :ok
          after
            1_000 -> Process.demonitor(monitor, [:flush])
          end

          receive do
            {^reference, _} -> :ok
          after
            0 -> :ok
          end

          {:error, :uncertain}
      end

    Dispatch.observation(request, result)
  end

  defp transaction(multi) do
    case Repo.transaction(multi) do
      {:ok, results} -> {:ok, results}
      {:error, _step, reason, _changes} -> {:error, reason}
    end
  end

  defp wait(context, config) do
    # A finished local invocation needs no lease while waiting for its next wake.
    # Uncertainty still retains the reservation; an actual coordinator crash
    # before this point leaves the ordinary lease expiry protection intact.
    Admission.yield_multi(Multi.new(), :yield, context.token) |> transaction()
    snooze(config)
  end

  defp snooze(config), do: {:snooze, max(1, div(config.poll_ms + 999, 1000))}
end
