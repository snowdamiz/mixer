defmodule MixerHosted.CatalogInspector do
  @moduledoc """
  Private point-in-time inspection of the selected authority-only contract.

  Caller supplies its trusted dedicated runtime Repo, before serving protected
  traffic, and owns connection freshness and migration/publication coordination.
  Observed settings cannot establish that a pooled connection has never been
  used. Success is diagnostic metadata, never an authorization capability.
  """
  alias MixerHosted.CatalogInspector.Raw

  @priv Path.expand("../../priv", __DIR__)
  @baseline_path Path.join(@priv, "selected-expected.json")
  @manifest_path Path.join(@priv, "observer-profile.json")
  @catalog_path Path.join(@priv, "catalog.sql")
  @enforcement_path Path.join(@priv, "enforcement.sql")
  @session_path Path.join(@priv, "session.sql")
  @external_resource @manifest_path
  @external_resource @baseline_path
  @external_resource @catalog_path
  @external_resource @enforcement_path
  @external_resource @session_path
  @manifest_bytes File.read!(@manifest_path)
  @manifest_sha256 "a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395"
  if Base.encode16(:crypto.hash(:sha256, File.read!(@baseline_path)), case: :lower) !=
       "78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e",
     do: raise("original catalog baseline bytes changed")

  if Base.encode16(:crypto.hash(:sha256, @manifest_bytes), case: :lower) != @manifest_sha256,
    do: raise("selected catalog manifest bytes changed")

  @expected Jason.decode!(@manifest_bytes)
  @catalog File.read!(@catalog_path)
  @enforcement File.read!(@enforcement_path)
  @session File.read!(@session_path)
  @budget_ms 5000
  @payload_bytes 4_194_304
  # These are resource ceilings, not a claim that all catalog allocation or
  # server work is bounded. Count only LIMIT+1 rows; never aggregate them here.
  @counts [
    {"pg_roles", 4096},
    {"pg_auth_members", 4096},
    {"pg_namespace", 4096},
    {"pg_class", 32768},
    {"pg_attribute", 262_144},
    {"pg_proc", 32768},
    {"pg_constraint", 32768},
    {"pg_trigger", 32768},
    {"pg_default_acl", 4096},
    {"pg_database", 4096},
    {"pg_settings", 4096},
    {"pg_parameter_acl", 4096}
  ]
  @preflight "SELECT " <>
               Enum.map_join(@counts, ",", fn {table, limit} ->
                 "(SELECT count(*) FROM (SELECT 1 FROM pg_catalog.#{table} LIMIT #{limit + 1}) AS bounded) <= #{limit}"
               end)
  @state "SELECT pg_backend_pid(), session_user::text, current_user::text, current_setting('role'), current_setting('transaction_isolation'), current_setting('transaction_read_only'), current_setting('row_security'), current_setting('session_replication_role')"
  @observer "catalog_inspector_observer"
  @observer_access """
  SELECT r.rolcanlogin, r.rolsuper, r.rolbypassrls, r.rolcreatedb,
    r.rolcreaterole, r.rolreplication, r.rolinherit,
    (SELECT coalesce(array_agg(rolname::text ORDER BY rolname),ARRAY[]::text[])
       FROM pg_roles WHERE oid<>r.oid AND pg_has_role(r.oid,oid,'MEMBER')),
    (SELECT count(*)=1 AND bool_and(NOT admin_option AND inherit_option AND NOT set_option
       AND roleid=(SELECT oid FROM pg_roles WHERE rolname='pg_read_all_settings'))
       FROM pg_auth_members WHERE member=r.oid),
    has_database_privilege(r.oid,current_database(),'CONNECT'),
    has_database_privilege(r.oid,current_database(),'CREATE'),
    has_database_privilege(r.oid,current_database(),'TEMP'),
    EXISTS(SELECT 1 FROM pg_namespace WHERE nspowner=r.oid OR has_schema_privilege(r.oid,oid,'CREATE')),
    EXISTS(SELECT 1 FROM pg_class WHERE relowner=r.oid),
    EXISTS(SELECT 1 FROM pg_proc WHERE proowner=r.oid),
    EXISTS(SELECT 1 FROM pg_database WHERE datdba=r.oid),
    EXISTS(SELECT 1 FROM pg_type WHERE typowner=r.oid),
    has_schema_privilege(r.oid,'mixer_authz','USAGE'),
    EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='mixer_authz' AND c.relkind IN ('r','v','m','p','f')
      AND (has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
           OR has_any_column_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))),
    EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='mixer_authz' AND has_function_privilege(r.oid,p.oid,'EXECUTE'))
  FROM pg_roles r WHERE r.rolname='catalog_inspector_observer'
  """

  @type result ::
          {:ok, %{manifest_sha256: String.t(), snapshot_scope: :point_in_time}}
          | {:error, :catalog_unavailable | :catalog_mismatch | :malformed_catalog}
  @spec verify(module(), module()) :: result()
  def verify(catalog_repo, runtime_repo) when is_atom(catalog_repo) and is_atom(runtime_repo) do
    deadline = System.monotonic_time(:millisecond) + @budget_ms
    owner = self()
    runtime = context!(runtime_repo, owner, deadline)
    catalog = context!(catalog_repo, owner, deadline)
    if runtime.dynamic === catalog.dynamic, do: unavailable!()
    runtime = Map.put(runtime, :peer, {catalog.repo, catalog.dynamic})
    catalog = Map.put(catalog, :peer, {runtime.repo, runtime.dynamic})

    runtime_repo.checkout(
      fn ->
        # The exact original session comparison is deliberately outside BEGIN:
        # the read-only snapshot's isolation/read-only fields are different.
        fresh = capture!(runtime, @session, false)
        if fresh !== @expected["fresh_session"], do: throw(:catalog_mismatch)
        [[runtime_backend]] = query!(runtime, "SELECT pg_catalog.pg_backend_pid()")

        catalog_repo.checkout(
          fn ->
            # Both trusted dynamic Repo identities remain pinned across both
            # acquisitions. Neither context is adopted from an existing checkout.
            budget!(runtime)
            [[backend]] = query!(catalog, "SELECT pg_catalog.pg_backend_pid()")
            if backend == runtime_backend, do: unavailable!()

            result =
              catalog_repo.transaction(
                fn ->
                  query!(catalog, "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                  budget!(catalog)
                  # Fixed settings revert on success and rollback. No session SET, role,
                  # advisory lock, DDL, temp object, or application-data access is used.
                  query!(catalog, "SET LOCAL search_path = pg_catalog")
                  query!(catalog, "SET LOCAL lock_timeout = '250ms'")
                  query!(catalog, "SET LOCAL idle_in_transaction_session_timeout = '5s'")
                  assert_state!(catalog, backend)
                  rows = timed_query!(catalog, @preflight)

                  case rows do
                    [counts] when length(counts) == length(@counts) ->
                      if not Enum.all?(counts, &(&1 === true)), do: unavailable!()

                    _ ->
                      unavailable!()
                  end

                  assert_observer!(catalog)

                  raw = %{
                    "legacy" => capture!(catalog, @catalog, true),
                    "enforcement" => capture!(catalog, @enforcement, true),
                    "fresh_session" => fresh
                  }

                  normalized = Raw.normalize!(raw)
                  if normalized !== @expected, do: throw(:catalog_mismatch)
                  assert_state!(catalog, backend)
                  assert_observer!(catalog)
                  budget!(runtime)
                  budget!(catalog)
                  %{manifest_sha256: @manifest_sha256, snapshot_scope: :point_in_time}
                end, queue: false, timeout: remaining!(catalog), log: false)

            case result do
              {:ok, metadata} ->
                after_session = capture!(runtime, @session, false)
                [[^runtime_backend]] = query!(runtime, "SELECT pg_catalog.pg_backend_pid()")
                if after_session !== fresh, do: throw(:catalog_mismatch)
                budget!(catalog)
                budget!(runtime)
                {:ok, metadata}

              _ ->
                unavailable!()
            end
          end, queue: false, timeout: remaining!(catalog))
      end, queue: false, timeout: remaining!(runtime))
  rescue
    _ -> {:error, :catalog_unavailable}
  catch
    kind when kind in [:catalog_unavailable, :catalog_mismatch, :malformed_catalog] ->
      {:error, kind}

    _, _ ->
      {:error, :catalog_unavailable}
  end

  def verify(_, _), do: {:error, :catalog_unavailable}
  def verify(_), do: {:error, :catalog_unavailable}

  defp context!(repo, owner, deadline) do
    if repo.__adapter__() != Ecto.Adapters.Postgres or repo.checked_out?() or
         repo.in_transaction?(), do: unavailable!()

    %{repo: repo, dynamic: repo.get_dynamic_repo(), owner: owner, deadline: deadline}
  end

  defp capture!(context, sql, transaction?) do
    # The accepted SELECT bytes are preserved in resources. The separately
    # tested envelope suppresses oversized payloads before Postgrex/Jason decode.
    body = sql |> String.trim() |> String.trim_trailing(";")

    envelope =
      "WITH mixer_catalog_capture(value) AS MATERIALIZED (" <>
        body <>
        ") SELECT CASE WHEN pg_catalog.octet_length(value::pg_catalog.text) <= #{@payload_bytes} THEN value::pg_catalog.text ELSE NULL END FROM mixer_catalog_capture"

    rows = if transaction?, do: timed_query!(context, envelope), else: query!(context, envelope)

    case rows do
      [[bytes]] when is_binary(bytes) and byte_size(bytes) <= @payload_bytes -> Raw.decode!(bytes)
      _ -> unavailable!()
    end
  end

  defp assert_state!(context, backend) do
    case timed_query!(context, @state) do
      [[^backend, @observer, @observer, "none", "repeatable read", "on", "on", "origin"]] -> :ok
      _ -> unavailable!()
    end
  end

  defp assert_observer!(context) do
    expected = [
      [
        true,
        false,
        false,
        false,
        false,
        false,
        true,
        ["pg_read_all_settings"],
        true,
        true,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false
      ]
    ]

    if timed_query!(context, @observer_access) !== expected, do: unavailable!()
  end

  defp timed_query!(context, sql) do
    ms = remaining!(context)

    query!(context, "SELECT pg_catalog.set_config('statement_timeout', $1, true)", [
      Integer.to_string(ms) <> "ms"
    ])

    query!(context, sql)
  end

  defp query!(context, sql, params \\ []) do
    remaining = remaining!(context)

    case Ecto.Adapters.SQL.query(context.dynamic, sql, params,
           queue: false,
           timeout: remaining,
           log: false,
           telemetry_options: [mixer_catalog_inspector: true]
         ) do
      {:ok, %Postgrex.Result{rows: rows}} ->
        budget!(context)
        rows

      _ ->
        unavailable!()
    end
  end

  defp remaining!(context) do
    if self() != context.owner or context.repo.get_dynamic_repo() !== context.dynamic,
      do: unavailable!()

    if Map.has_key?(context, :peer) do
      {peer_repo, peer_dynamic} = context.peer
      if peer_repo.get_dynamic_repo() !== peer_dynamic, do: unavailable!()
    end

    ms = context.deadline - System.monotonic_time(:millisecond)
    if ms <= 0, do: unavailable!()
    ms
  end

  defp budget!(context), do: remaining!(context)
  defp unavailable!, do: throw(:catalog_unavailable)
end
