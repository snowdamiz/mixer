defmodule MixerHosted.CustomerBuilds.Context do
  @moduledoc false
  alias MixerHosted.Repo
  alias MixerHosted.CustomerBuilds.{Policy, Schema, Snapshot}
  alias MixerHosted.Authorization.Postgres.Session
  @active {__MODULE__, :active}
  @receipt {__MODULE__, :receipt}
  @event [:mixer_hosted, :customer_builds, :transaction]
  @handler {__MODULE__, :receipt_handler}
  @settings ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase directory_mode)

  def read(identity, selection) do
    with :ok <- Policy.request(identity),
         true <- Process.get(@active) == nil,
         false <- MixerHosted.Authorization.Transaction.Context.active?(),
         true <- Repo.get_dynamic_repo() === Repo,
         false <- Repo.in_transaction?(),
         pid when is_pid(pid) <- Process.whereis(Repo) do
      state = %{
        owner: self(),
        runtime: pid,
        identity: identity,
        selection: selection,
        admitted_at: System.system_time(:second),
        deadline: System.monotonic_time(:millisecond) + 5_000,
        marker: Base.encode16(:crypto.strong_rand_bytes(32), case: :lower),
        request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
      }

      Process.put(@active, state)
      :ok = handler!()
      ref = make_ref()
      Process.put(@receipt, {self(), ref, :await_begin})

      result =
        Repo.transaction(fn -> execute!(state) end,
          timeout: 5_000,
          deadline: state.deadline,
          queue: false,
          log: false,
          telemetry_event: @event,
          telemetry_options: [build_read: {self(), ref}]
        )

      case {result, Process.get(@receipt)} do
        {{:ok, {dto, evidence, backend}}, {owner, ^ref, {:committed, ack_backend}}}
        when owner == self() and backend == ack_backend ->
          publish!(state, evidence)
          {:ok, dto}

        {{:error, reason}, _}
        when reason in [:unauthenticated, :not_found, :permission_denied, :storage_unavailable] ->
          {:error, reason}

        _ ->
          {:error, :authorization_unavailable}
      end
    else
      {:error, _} = e -> e
      _ -> {:error, :authorization_unavailable}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  after
    Process.delete(@receipt)
    Process.delete(@active)
  end

  defp execute!(s) do
    scope = %{
      organization_id: s.selection.organization_id,
      project_id: s.selection.project_id,
      application_id: s.selection.application_id,
      environment_id: nil
    }

    Session.prepare!(Repo, %{
      identity: MixerHosted.Authorization.Policy.identity_key(s.identity),
      target: scope
    })

    Session.context!(Repo,
      action: "build.read",
      required_scope: "mixer.build.read",
      phase: "build_read",
      transaction_marker: s.marker,
      token_issued_at: Integer.to_string(s.identity.issued_at),
      token_expires_at: Integer.to_string(s.identity.expires_at)
    )

    Schema.admit!(Repo)
    binding = binding!()
    [backend | _] = binding

    case Process.get(@receipt) do
      {owner, _, {:begun, ^backend}} when owner == self() -> :ok
      _ -> Repo.rollback(:authorization_unavailable)
    end

    # SQL locks the exact binding, tenant rows, memberships and build before its
    # current READ COMMITTED evidence statement. No callback runs in this scope.
    e = evidence!(s)
    checkpoint!(s, binding, e)

    row =
      Map.new(
        ~w(organization_id project_id application_id build_id platform request_key revision journal)a,
        fn k -> {k, Map.fetch!(e["record"], Atom.to_string(k))} end
      )

    dto =
      case Snapshot.project(row, s.selection) do
        {:ok, dto} -> dto
        _ -> Repo.rollback(:storage_unavailable)
      end

    # A new statement after every domain lock and immediately before commit.
    current = evidence!(s)
    if current !== e, do: Repo.rollback(:authorization_unavailable)
    checkpoint!(s, binding, current)
    {dto, current, backend}
  end

  defp evidence!(s) do
    x = s.selection

    case query!(
           "SELECT public.mixer_customer_build_read_v1($1,$2,$3,$4,$5)",
           [
             x.build_id,
             x.platform,
             x.source_sha256,
             x.toolchain_lock_sha256,
             x.build_definition_sha256
           ]
         ).rows do
      [[e]] when is_map(e) -> e
      _ -> Repo.rollback(:not_found)
    end
  end

  defp checkpoint!(s, binding, e) do
    if Process.get(@active) !== s or s.owner != self() or Process.whereis(Repo) != s.runtime or
         Repo.get_dynamic_repo() !== Repo or not Repo.in_transaction?() or
         MixerHosted.Authorization.Transaction.Context.active?() or binding!() !== binding,
       do: Repo.rollback(:authorization_unavailable)

    publish!(s, e)
  end

  defp publish!(s, e), do: publish!(s, e, s.admitted_at, 2)

  defp publish!(s, e, previous, remaining) do
    now = System.system_time(:second)
    true = Process.get(@active) === s and self() == s.owner and Process.whereis(Repo) == s.runtime

    true =
      Repo.get_dynamic_repo() === Repo and now >= s.admitted_at and now >= previous and
        System.monotonic_time(:millisecond) < s.deadline and Policy.live?(s.identity, e, now)

    # Revalidate once after a second change, retaining the original deadline.
    final_time = System.system_time(:second)
    true = final_time >= now and System.monotonic_time(:millisecond) < s.deadline

    cond do
      final_time == now -> :ok
      remaining > 1 -> publish!(s, e, final_time, remaining - 1)
      true -> raise MatchError, term: false
    end
  end

  defp binding! do
    fields = Enum.map_join(@settings, ",", &"current_setting('mixer.authz.#{&1}',true)")

    [row] =
      query!(
        "SELECT pg_backend_pid(),pg_current_xact_id()::text,current_user::text,session_user::text," <>
          fields,
        []
      ).rows

    row
  end

  defp query!(sql, params),
    do:
      Ecto.Adapters.SQL.query!(Repo, sql, params,
        timeout: 5_000,
        queue: false,
        log: false,
        telemetry_event: nil
      )

  defp handler! do
    handler = &__MODULE__.transaction_event/4

    case :telemetry.attach(@handler, @event, handler, nil) do
      :ok ->
        :ok

      {:error, :already_exists} ->
        true =
          Enum.any?(
            :telemetry.list_handlers(@event),
            &(&1.id === @handler and &1.function === handler and &1.config === nil)
          )

        :ok
    end
  end

  @doc false
  def transaction_event(@event, _, metadata, nil) do
    case Process.get(@receipt) do
      {caller, ref, status} when caller == self() ->
        next =
          case metadata do
            %{
              type: :ecto_sql_query,
              repo: Repo,
              options: [build_read: {^caller, ^ref}],
              query: q,
              result: r
            } ->
              advance(status, q, r)

            _ ->
              :unknown
          end

        Process.put(@receipt, {caller, ref, next})

      _ ->
        :ok
    end

    :ok
  end

  defp advance(:await_begin, "begin", {:ok, %Postgrex.Result{command: :begin, connection_id: b}})
       when is_integer(b) and b > 0, do: {:begun, b}

  defp advance(
         {:begun, b},
         "commit",
         {:ok, %Postgrex.Result{command: :commit, connection_id: b}}
       ),
       do: {:committed, b}

  defp advance({:begun, b}, q, {:ok, %Postgrex.Result{command: :rollback, connection_id: b}})
       when q in ["commit", "rollback"], do: {:rolled_back, b}

  defp advance(_, _, _), do: :unknown
end
