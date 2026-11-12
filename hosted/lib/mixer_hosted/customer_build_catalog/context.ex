defmodule MixerHosted.CustomerBuildCatalog.Context do
  @moduledoc false
  alias MixerHosted.Repo
  alias MixerHosted.CustomerBuilds.Policy
  alias MixerHosted.CustomerBuildCatalog.{Schema, Snapshot}
  alias MixerHosted.Authorization.Postgres.Session
  @active {__MODULE__, :active}
  @receipt {__MODULE__, :receipt}
  @event [:mixer_hosted, :customer_build_catalog, :transaction]
  @handler {__MODULE__, :receipt_handler}
  @settings ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase directory_mode)

  def read(identity, input) do
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
        input: input,
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
      organization_id: s.input.scope.organization_id,
      project_id: s.input.scope.project_id,
      application_id: Map.get(s.input.scope, :application_id),
      environment_id: nil
    }

    Session.prepare!(Repo, %{
      identity: MixerHosted.Authorization.Policy.identity_key(s.identity),
      target: scope
    })

    Session.context!(Repo,
      action: "build.read",
      required_scope: "mixer.build.read",
      phase: "build_catalog_#{s.input.kind}",
      transaction_marker: s.marker,
      token_issued_at: Integer.to_string(s.identity.issued_at),
      token_expires_at: Integer.to_string(s.identity.expires_at)
    )

    Schema.admit!(Repo, s.input.kind)
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

    dto =
      case Snapshot.project(s.input, e) do
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
    {sql, params} =
      case {s.input.kind, s.input.last} do
        {:applications, nil} ->
          {"SELECT public.mixer_customer_build_applications_v1($1)", [nil]}

        {:applications, [id]} ->
          {"SELECT public.mixer_customer_build_applications_v1($1)", [id]}

        {:builds, nil} ->
          {"SELECT public.mixer_customer_build_catalog_v1($1,$2)", [nil, nil]}

        {:builds, [id, platform]} ->
          {"SELECT public.mixer_customer_build_catalog_v1($1,$2)", [id, platform]}
      end

    case query!(sql, params).rows do
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

  defp publish!(s, e) do
    now = System.system_time(:second)
    true = Process.get(@active) === s and self() == s.owner and Process.whereis(Repo) == s.runtime

    true =
      Repo.get_dynamic_repo() === Repo and now >= s.admitted_at and
        System.monotonic_time(:millisecond) < s.deadline and Policy.live?(s.identity, e, now)

    # Withhold a result if descheduling crossed either temporal boundary.
    true = System.system_time(:second) == now and System.monotonic_time(:millisecond) < s.deadline
    :ok
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
