defmodule MixerHosted.BrowserAuth.ProviderOwner do
  @moduledoc "Raw provider boundary. Production transport is deliberately unconfigured and fails closed."
  use GenServer
  alias MixerHosted.BrowserAuth.ConfigurationDigest
  alias MixerHosted.Identity.{Admission, KeyOwner, TrustSnapshot}
  alias MixerHosted.BrowserAuth.Config
  @trust_owner MixerHosted.BrowserAuth.ProviderTrustOwner

  defmodule TrustTicket do
    @moduledoc false
    @enforce_keys [
      :owner,
      :owner_monitor,
      :lease,
      :permit,
      :deadline,
      :caller,
      :caller_monitor,
      :timer,
      :phase
    ]
    defstruct @enforce_keys
  end

  def exchange(config, code, verifier, deadline) do
    GenServer.call(__MODULE__, {:exchange, config, code, verifier, deadline}, remaining(deadline))
  catch
    :exit, _ -> {:error, :provider_unavailable}
  end

  def finish(ticket, config, deadline) do
    GenServer.call(__MODULE__, {:finish, ticket, config}, remaining(deadline))
  catch
    :exit, _ -> {:error, :provider_unavailable}
  end

  def start_link(:unconfigured),
    do: GenServer.start_link(__MODULE__, :unconfigured, name: __MODULE__)

  if Mix.env() == :test do
    @doc false
    def start_trust_fixture(%Config{} = config, transport) when is_pid(transport),
      do: GenServer.start_link(__MODULE__, {:trust_fixture, config, transport}, name: __MODULE__)

    @doc false
    def start_fixture(config, snapshot, transport),
      do:
        GenServer.start_link(__MODULE__, {:fixture, config, snapshot, transport},
          name: __MODULE__
        )
  end

  def init(:unconfigured), do: {:ok, :unconfigured}

  if Mix.env() == :test do
    def init({:trust_fixture, %Config{} = config, transport}) when is_pid(transport) do
      Process.flag(:trap_exit, true)

      with {:ok, digest} <- ConfigurationDigest.digest(config) do
        {:ok,
         %{
           mode: :trust_fixture,
           config: config,
           digest: digest,
           transport: transport,
           generation: make_ref(),
           tickets: %{}
         }}
      else
        _ -> {:stop, :invalid_provider_configuration}
      end
    end

    def init({:fixture, config, snapshot, transport}) when is_pid(transport) do
      {:ok, digest} = ConfigurationDigest.digest(config)

      {:ok,
       %{
         config: config,
         digest: digest,
         snapshot: snapshot,
         transport: transport,
         generation: make_ref()
       }}
    end
  end

  def handle_call(
        {:exchange, config, code, verifier, requested},
        from,
        %{mode: :trust_fixture, config: config} = s
      ) do
    deadline = min(requested, System.monotonic_time(:millisecond) + 5_000)
    owner = Process.whereis(@trust_owner)
    workers = Process.whereis(Module.concat(@trust_owner, FetchSupervisor))

    if is_pid(owner) and is_pid(workers) and Process.whereis(@trust_owner) === owner and
         System.monotonic_time(:millisecond) < deadline do
      ref = make_ref()
      parent = self()
      caller = elem(from, 0)
      transport = s.transport
      request = request(config, code, verifier)

      case start_trust_worker(workers, fn ->
             trust_work(parent, ref, caller, owner, workers, transport, request, deadline)
           end) do
        {:ok, worker} ->
          monitor = Process.monitor(worker)

          entry = %TrustTicket{
            owner: owner,
            owner_monitor: Process.monitor(owner),
            lease: nil,
            permit: nil,
            deadline: deadline,
            caller: caller,
            caller_monitor: Process.monitor(caller),
            timer:
              Process.send_after(
                self(),
                {:trust_expired, ref},
                max(0, deadline - System.monotonic_time(:millisecond))
              ),
            phase: {:exchange, from, worker, monitor}
          }

          {:noreply, put_in(s.tickets[ref], entry)}

        _ ->
          {:reply, {:error, :provider_unavailable}, s}
      end
    else
      {:reply, {:error, :provider_unavailable}, s}
    end
  end

  def handle_call(
        {:finish, {pid, generation, digest, ref}, config},
        from,
        %{mode: :trust_fixture} = s
      ) do
    case s.tickets[ref] do
      %TrustTicket{caller: caller, phase: {:issued, worker, monitor}} = entry
      when caller === elem(from, 0) and config === s.config and
             pid === self() and generation === s.generation and digest === s.digest ->
        send(worker, {:trust_finish, self(), ref})
        {:noreply, put_in(s.tickets[ref], %{entry | phase: {:finish, from, worker, monitor}})}

      _ ->
        {:reply, {:error, :provider_unavailable}, s}
    end
  end

  def handle_call(_, _, %{mode: :trust_fixture} = s),
    do: {:reply, {:error, :provider_unavailable}, s}

  def handle_call({:exchange, config, code, verifier, deadline}, _from, %{config: config} = s) do
    if fresh?(s) and System.monotonic_time(:millisecond) < deadline do
      request = %{
        issuer: config.issuer,
        client_id: config.client_id,
        redirect_uri: config.redirect_uri,
        token_endpoint: config.token_endpoint,
        client_auth_method: config.client_auth_method,
        client_credential_ref: config.client_credential_ref,
        code: code,
        code_verifier: verifier,
        grant_type: "authorization_code"
      }

      result = GenServer.call(s.transport, {:exchange, request}, remaining(deadline))

      case result do
        {:ok, raw} when is_binary(raw) and byte_size(raw) <= 16384 ->
          if fresh?(s) and System.monotonic_time(:millisecond) < deadline,
            do: {:reply, {:ok, raw, s.snapshot, {self(), s.generation, s.digest}}, s},
            else: {:reply, {:error, :provider_unavailable}, s}

        _ ->
          {:reply, {:error, :provider_unavailable}, s}
      end
    else
      {:reply, {:error, :provider_unavailable}, s}
    end
  end

  def handle_call({:finish, {pid, generation, digest}, config}, _from, %{config: config} = s) do
    valid = pid === self() and generation === s.generation and digest === s.digest and fresh?(s)
    {:reply, if(valid, do: :ok, else: {:error, :provider_unavailable}), s}
  end

  def handle_call(_, _, s), do: {:reply, {:error, :provider_unconfigured}, s}

  def handle_info({:trust_transport, ref, worker, result}, %{mode: :trust_fixture} = s) do
    case s.tickets[ref] do
      %TrustTicket{phase: {:exchange, from, ^worker, monitor}} = entry ->
        case result do
          {:ok, raw, snapshot} ->
            if live_entry?(entry) do
              GenServer.reply(from, {:ok, raw, snapshot, {self(), s.generation, s.digest, ref}})
              {:noreply, put_in(s.tickets[ref].phase, {:issued, worker, monitor})}
            else
              {:noreply, consume(s, ref)}
            end

          _ ->
            {:noreply, consume(s, ref)}
        end

      _ ->
        {:noreply, s}
    end
  end

  def handle_info({:trust_finished, ref, worker, result}, %{mode: :trust_fixture} = s) do
    case s.tickets[ref] do
      %TrustTicket{phase: {:finish, from, ^worker, _}} = entry ->
        result =
          if live_entry?(entry) and result === :ok, do: :ok, else: {:error, :provider_unavailable}

        # Clear the pending reply before the common terminal cleanup.
        {:finish, _, _, monitor} = entry.phase
        s = put_in(s.tickets[ref].phase, {:issued, worker, monitor})
        s = consume(s, ref)
        GenServer.reply(from, result)
        {:noreply, s}

      _ ->
        {:noreply, s}
    end
  end

  def handle_info({:trust_expired, ref}, %{mode: :trust_fixture} = s),
    do: {:noreply, consume(s, ref)}

  def handle_info({:DOWN, monitor, :process, _pid, _reason}, %{mode: :trust_fixture} = s) do
    refs =
      for {ref, entry} <- s.tickets,
          monitor in [entry.owner_monitor, entry.caller_monitor] or
            worker_monitor(entry.phase) === monitor,
          do: ref

    s =
      Enum.reduce(refs, s, fn ref, acc ->
        if worker_monitor(acc.tickets[ref].phase) === monitor do
          entry = acc.tickets[ref]
          reply_failure(entry.phase)
          consume(put_in(acc.tickets[ref].phase, :terminal), ref)
        else
          consume(acc, ref)
        end
      end)

    {:noreply, s}
  end

  def handle_info(_, %{mode: :trust_fixture} = s), do: {:noreply, s}

  def terminate(_, %{mode: :trust_fixture} = s) do
    Enum.reduce(Map.keys(s.tickets), s, &consume(&2, &1))
    :ok
  end

  def terminate(_, _), do: :ok

  defp live_entry?(entry),
    do:
      Process.whereis(@trust_owner) === entry.owner and Process.alive?(entry.caller) and
        System.monotonic_time(:millisecond) < entry.deadline

  defp start_trust_worker(workers, work) do
    child = Supervisor.child_spec({Task, work}, restart: :temporary, shutdown: :brutal_kill)
    DynamicSupervisor.start_child(workers, child)
  catch
    :exit, _ -> {:error, :provider_unavailable}
  end

  defp trust_work(parent, ref, caller, owner, workers, transport, request, deadline) do
    Process.flag(:trap_exit, true)
    Process.link(parent)
    parent_monitor = Process.monitor(parent)
    caller_monitor = Process.monitor(caller)

    with true <- Process.alive?(parent) and Process.alive?(caller),
         true <- Process.whereis(Module.concat(@trust_owner, FetchSupervisor)) === workers,
         true <- Process.whereis(@trust_owner) === owner,
         true <- System.monotonic_time(:millisecond) < deadline,
         {:ok, permit} <- Admission.acquire(@trust_owner, :configured),
         {:ok, lease} <- KeyOwner.checkout(owner, permit, System.system_time(:second)),
         true <- worker_current?(parent, caller, owner, lease, deadline) do
      result =
        try do
          GenServer.call(transport, {:exchange, request}, remaining(deadline))
        catch
          :exit, _ -> {:error, :provider_unavailable}
        end

      case result do
        {:ok, raw} when is_binary(raw) and byte_size(raw) <= 16384 ->
          if worker_current?(parent, caller, owner, lease, deadline) do
            send(parent, {:trust_transport, ref, self(), {:ok, raw, lease.snapshot}})

            receive do
              {:trust_finish, ^parent, ^ref} ->
                result =
                  if worker_current?(parent, caller, owner, lease, deadline),
                    do: :ok,
                    else: {:error, :provider_unavailable}

                send(parent, {:trust_finished, ref, self(), result})

              {:EXIT, ^parent, _} ->
                :ok

              {:DOWN, ^parent_monitor, :process, ^parent, _} ->
                :ok

              {:DOWN, ^caller_monitor, :process, ^caller, _} ->
                :ok
            after
              max(0, deadline - System.monotonic_time(:millisecond)) -> :ok
            end
          else
            send(parent, {:trust_transport, ref, self(), {:error, :provider_unavailable}})
          end

        _ ->
          send(parent, {:trust_transport, ref, self(), {:error, :provider_unavailable}})
      end
    else
      _ -> send(parent, {:trust_transport, ref, self(), {:error, :provider_unavailable}})
    end

    # No release while this process is live. Admission's real caller monitor
    # and reaper reclaim the reservation only after this worker is terminal.
    :ok
  end

  defp worker_current?(parent, caller, owner, lease, deadline),
    do:
      Process.alive?(parent) and Process.alive?(caller) and
        Process.whereis(@trust_owner) === owner and
        System.monotonic_time(:millisecond) < deadline and
        KeyOwner.finish(owner, lease) === :ok and
        System.monotonic_time(:millisecond) < deadline and
        Process.alive?(parent) and Process.alive?(caller)

  defp consume(s, ref) do
    case Map.pop(s.tickets, ref) do
      {nil, _} ->
        s

      {entry, rest} ->
        Process.cancel_timer(entry.timer)
        Process.demonitor(entry.owner_monitor, [:flush])
        Process.demonitor(entry.caller_monitor, [:flush])
        reply_failure(entry.phase)
        reap_worker(entry.phase)
        %{s | tickets: rest}
    end
  end

  defp reply_failure({phase, from, _, _}) when phase in [:exchange, :finish],
    do: GenServer.reply(from, {:error, :provider_unavailable})

  defp reply_failure(_), do: :ok
  defp worker_monitor({_, _, _, monitor}), do: monitor
  defp worker_monitor({:issued, _, monitor}), do: monitor
  defp worker_monitor(:terminal), do: nil
  defp reap_worker({_, _, worker, monitor}), do: reap_worker({:issued, worker, monitor})

  defp reap_worker({:issued, worker, monitor}) do
    Process.exit(worker, :kill)

    receive do
      {:DOWN, ^monitor, :process, ^worker, _} -> :ok
    after
      1_000 -> exit(:provider_worker_cleanup_unconfirmed)
    end
  end

  defp reap_worker(:terminal), do: :ok

  defp request(config, code, verifier),
    do: %{
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      token_endpoint: config.token_endpoint,
      client_auth_method: config.client_auth_method,
      client_credential_ref: config.client_credential_ref,
      code: code,
      code_verifier: verifier,
      grant_type: "authorization_code"
    }

  def format_status(status),
    do:
      Map.new(status, fn {k, v} ->
        if k in [:state, :message, :reason, :log], do: {k, :redacted}, else: {k, v}
      end)

  defp fresh?(s), do: TrustSnapshot.status(s.snapshot, System.system_time(:second)) === :fresh
  defp remaining(d), do: max(1, min(5000, d - System.monotonic_time(:millisecond)))
end
