Code.require_file("storage_fixture.exs", __DIR__)

defmodule R1242.Direct do
  alias MixerHosted.BrowserAuth.{
    StorageFixture,
    LifecycleRepo,
    ActiveCatalog,
    RelationCatalog,
    RelationManifest
  }

  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  @acl_sql """
  WITH targets AS (SELECT c.oid,n.nspname::text||'.'||c.relname::text AS name FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.oid::bigint=ANY($1::bigint[]))
  SELECT q.* FROM (
  SELECT x.name AS relation,NULL::text AS column,c.relacl IS NULL AS null,a.grantee::bigint AS grantee,a.grantor::bigint AS grantor,a.privilege_type::text AS privilege,a.is_grantable AS option FROM targets x JOIN pg_catalog.pg_class c ON c.oid=x.oid CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(c.relacl,pg_catalog.acldefault('r',c.relowner))) a
  UNION ALL
  SELECT x.name,a.attname::text,false,e.grantee::bigint,e.grantor::bigint,e.privilege_type::text,e.is_grantable FROM targets x JOIN pg_catalog.pg_attribute a ON a.attrelid=x.oid CROSS JOIN LATERAL pg_catalog.aclexplode(a.attacl) e WHERE a.attnum>0
  ) q ORDER BY q.relation,q.column,q.grantee,q.privilege LIMIT 513
  """
  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  def run do
    baseline = fixture("r1258_b_baseline", false)
    catalog = fixture("r1258_b_catalog", true)
    result = %{baseline: baseline, catalog: catalog}

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "four-sql-cases.json"),
      Jason.encode!(result)
    )

    result
  end

  def cleanup_direct_databases! do
    conn = connect("browser_admin", "postgres")

    try do
      for name <- ["r1258_b_baseline", "r1258_b_catalog"],
          do: Postgrex.query!(conn, "DROP DATABASE " <> name, [])
    after
      GenServer.stop(conn)
    end
  end

  defp connect(role, database) do
    {:ok, conn} =
      Postgrex.start_link(
        hostname: "127.0.0.1",
        port: StorageFixture.port(),
        username: role,
        database: database,
        ssl: false,
        backoff_type: :stop
      )

    conn
  end

  defp fixture(database, catalog?) do
    conn = connect("browser_admin", "postgres")
    Postgrex.query!(conn, "CREATE DATABASE " <> database <> " OWNER browser_schema_owner", [])
    GenServer.stop(conn)

    settings = [
      hostname: "127.0.0.1",
      port: StorageFixture.port(),
      database: database,
      pool_size: 2,
      log: false
    ]

    Application.put_env(:browser_storage_fixture, Admin, settings ++ [username: "browser_admin"])
    {:ok, admin} = Admin.start_link(settings ++ [username: "browser_admin"])

    {:ok, migration} =
      Migration.start_link(
        settings ++
          [
            username: "browser_admin",
            after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end
          ]
      )

    try do
      StorageFixture.install!()
      q(Admin, "GRANT USAGE ON SCHEMA public TO browser_ordinary")
      q(Admin, "GRANT SELECT ON ALL TABLES IN SCHEMA public TO browser_ordinary")

      for helper <- ~w(profiles principals families credentials organization_heads project_heads),
          do:
            q(
              Admin,
              "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO browser_ordinary"
            )

      for table <- ~w(sessions session_vault oidc_attempts session_events),
          do: q(Admin, "REVOKE SELECT ON public.mixer_browser_#{table} FROM browser_ordinary")

      for sql <- MixerHosted.BrowserAuth.ActivationPreparationSchema.statements(),
          do: q(Migration, sql)

      provision(
        database,
        MixerHosted.BrowserAuth.StorageSchema.provisioning_statements(
          "browser_writer",
          "browser_lifecycle"
        )
      )

      provision(
        database,
        MixerHosted.BrowserAuth.ActivationPreparationSchema.provisioning_statements(
          "browser_writer",
          "browser_lifecycle",
          "browser_schema_owner"
        )
      )

      for sql <- MixerHosted.BrowserAuth.ActiveReadSchema.statements(), do: q(Migration, sql)
      provision(database, MixerHosted.BrowserAuth.ActiveReadSchema.provisioning_statements())

      unless Code.ensure_loaded?(MixerHosted.Repo.Migrations.AddBuildJournals),
        do: Code.require_file("priv/repo/migrations/20261025000000_add_build_journals.exs")

      :ok =
        Ecto.Migrator.up(
          Migration,
          20_261_025_000_000,
          MixerHosted.Repo.Migrations.AddBuildJournals,
          log: false
        )

      :ok = Ecto.Migrator.up(Migration, 1, R1026.ObanMigration, log: false)
      q(Migration, MixerHosted.CustomerBuilds.Schema.ddl())

      q(
        Migration,
        "REVOKE ALL ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) FROM PUBLIC"
      )

      q(
        Migration,
        "GRANT EXECUTE ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) TO browser_ordinary"
      )

      {:ok, :ok} =
        Migration.transaction(fn ->
          Enum.each(MixerHosted.CustomerArtifacts.Schema.statements(), &q(Migration, &1))
        end)

      if catalog?,
        do: Enum.each(MixerHosted.CustomerBuildCatalog.Schema.private_statements(), &q(Admin, &1))

      life = [
        hostname: "127.0.0.1",
        port: StorageFixture.port(),
        database: database,
        username: "browser_lifecycle",
        password: "synthetic",
        pool_size: 2,
        pool_count: 1,
        timeout: 5000,
        connect_timeout: 5000,
        queue: false,
        show_sensitive_data_on_connection_error: false,
        ssl: false
      ]

      {:ok, lifecycle} = LifecycleRepo.start_link(life)

      try do
        true = LifecycleRepo.bound?(life)
        acl = acl_vector(database)
        v2 = observe(database, :browser_auth_v2)
        v3 = observe(database, :build_catalog_v3)
        controls = []
        %{v2: v2, v3: v3, acl: acl, controls: controls}
      after
        Supervisor.stop(lifecycle)
      end
    after
      Supervisor.stop(migration)
      Supervisor.stop(admin)
    end
  end

  defp provision(database, statements) do
    conn = connect("browser_admin", database)

    try do
      Enum.each(statements, &Postgrex.query!(conn, &1, []))
    after
      GenServer.stop(conn)
    end
  end

  defp q(repo, sql), do: StorageFixture.q!(repo, sql)

  defp acl_vector(label) do
    targets =
      RelationManifest.for_major(17)["structure"]["writer_grants"] |> Map.keys() |> Enum.sort()

    %{rows: ids} =
      q(
        LifecycleRepo,
        "SELECT c.oid::bigint FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname::text||'.'||c.relname::text = ANY($1::text[]) ORDER BY c.oid",
        [targets]
      )

    true = length(ids) == 9
    sql = @acl_sql
    result = q(LifecycleRepo, sql, [List.flatten(ids)])
    rows = Enum.map(result.rows, &Map.new(Enum.zip(result.columns, &1)))
    value = %{count: result.num_rows, columns: result.columns, rows: rows, targets: targets}

    File.write!(
      Path.join(
        System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
        "proof/" <> label <> "-acl.json"
      ),
      Jason.encode!(value)
    )

    %{count: result.num_rows, vector: "proof/" <> label <> "-acl.json"}
  end

  defp q(repo, sql, params), do: StorageFixture.q!(repo, sql, params)

  defp observe(label, profile) do
    result =
      LifecycleRepo.transaction(
        fn ->
          q(LifecycleRepo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

          %{num_rows: 1} =
            q(
              LifecycleRepo,
              "SELECT pg_catalog.set_config('search_path','pg_catalog',true),pg_catalog.set_config('jit','off',true),pg_catalog.set_config('statement_timeout','5s',true),pg_catalog.set_config('lock_timeout','500ms',true),pg_catalog.set_config('idle_in_transaction_session_timeout','5s',true),pg_catalog.set_config('bytea_output','hex',true)"
            )

          deadline = System.monotonic_time(:millisecond) + 5000

          relation =
            if profile == :browser_auth_v2,
              do: :check_relation_surface!,
              else: :check_build_catalog_surface!

          checks = [
            {ActiveCatalog, :check_function_surface!, [LifecycleRepo, @roles, deadline, 2]},
            {RelationCatalog, relation, [LifecycleRepo, @roles, deadline]}
          ]

          checks =
            if profile == :build_catalog_v3,
              do:
                checks ++
                  [
                    {MixerHosted.BrowserAuth.BuildCatalogAdmission, :check!,
                     [LifecycleRepo, @roles, deadline]}
                  ],
              else: checks

          surfaces =
            for {module, function, args} <- checks do
              try do
                value = apply(module, function, args)

                IO.puts(
                  "SURFACE " <>
                    label <> " " <> Atom.to_string(module) <> " " <> Atom.to_string(value)
                )

                %{surface: Atom.to_string(module), result: Atom.to_string(value)}
              rescue
                error ->
                  LifecycleRepo.rollback(%{
                    outcome: "refused",
                    surface: Atom.to_string(module),
                    class: Atom.to_string(error.__struct__)
                  })
              end
            end

          %{outcome: "admitted", surfaces: surfaces}
        end,
        log: false,
        timeout: 5000,
        queue: false
      )

    case result do
      {:ok, row} -> row
      {:error, row} -> row
    end
  end

  def controls do
    role = MixerHosted.CustomerBuildCatalog.Schema.role()
    grants = MixerHosted.CustomerBuildCatalog.Schema.surface_contract().grants

    missing =
      for {relation, privilege} <- grants do
        {"missing #{relation} #{privilege}", "REVOKE #{privilege} ON #{relation} FROM #{role}",
         "GRANT #{privilege} ON #{relation} TO #{role}"}
      end

    old_expression =
      MixerHosted.CustomerBuildCatalog.Schema.surface_contract().old_policy_expression

    q(Admin, "CREATE TABLE public.r1258_unrelated_column(id text)")

    cases =
      missing ++
        [
          {"extra PUBLIC application policy",
           "CREATE POLICY r1258_public ON public.mixer_authz_applications FOR SELECT USING(true)",
           "DROP POLICY r1258_public ON public.mixer_authz_applications"},
          {"changed old read policy",
           "ALTER POLICY scoped_read ON public.mixer_authz_applications USING(true)",
           "ALTER POLICY scoped_read ON public.mixer_authz_applications USING(" <>
             old_expression <> ")"},
          {"changed old lock policy",
           "ALTER POLICY scoped_lock ON public.mixer_authz_applications USING(true)",
           "ALTER POLICY scoped_lock ON public.mixer_authz_applications USING(" <>
             old_expression <> ")"},
          {"PUBLIC SELECT-only unrelated column",
           "GRANT SELECT(id) ON public.r1258_unrelated_column TO PUBLIC",
           "REVOKE SELECT(id) ON public.r1258_unrelated_column FROM PUBLIC"},
          {"extra function",
           "CREATE FUNCTION public.r1258_extra() RETURNS boolean LANGUAGE sql SECURITY DEFINER AS 'SELECT true'",
           "DROP FUNCTION public.r1258_extra()"},
          {"changed catalog function volatility",
           "ALTER FUNCTION public.mixer_customer_build_applications_v1(text) STABLE",
           "ALTER FUNCTION public.mixer_customer_build_applications_v1(text) VOLATILE"},
          {"same-count substituted SELECT",
           "REVOKE SELECT ON public.mixer_authz_profiles FROM #{role}; GRANT DELETE ON public.mixer_authz_profiles TO #{role}",
           "REVOKE DELETE ON public.mixer_authz_profiles FROM #{role}; GRANT SELECT ON public.mixer_authz_profiles TO #{role}"},
          {"extra MAINTAIN", "GRANT MAINTAIN ON public.mixer_authz_profiles TO #{role}",
           "REVOKE MAINTAIN ON public.mixer_authz_profiles FROM #{role}"},
          {"grant option",
           "GRANT SELECT ON public.mixer_authz_profiles TO #{role} WITH GRANT OPTION",
           "REVOKE GRANT OPTION FOR SELECT ON public.mixer_authz_profiles FROM #{role}"},
          {"login role", "ALTER ROLE #{role} LOGIN", "ALTER ROLE #{role} NOLOGIN"},
          {"inherit role", "ALTER ROLE #{role} INHERIT", "ALTER ROLE #{role} NOINHERIT"},
          {"lifecycle EXECUTE",
           "GRANT EXECUTE ON FUNCTION public.mixer_customer_build_applications_v1(text) TO browser_lifecycle",
           "REVOKE EXECUTE ON FUNCTION public.mixer_customer_build_applications_v1(text) FROM browser_lifecycle"},
          {"function search_path",
           "ALTER FUNCTION public.mixer_customer_build_applications_v1(text) SET search_path=public",
           "ALTER FUNCTION public.mixer_customer_build_applications_v1(text) SET search_path=pg_catalog"},
          {"application FORCE",
           "ALTER TABLE public.mixer_authz_applications NO FORCE ROW LEVEL SECURITY",
           "ALTER TABLE public.mixer_authz_applications FORCE ROW LEVEL SECURITY"},
          {"extra application policy",
           "CREATE POLICY r1242_extra ON public.mixer_authz_applications FOR SELECT TO #{role} USING(true)",
           "DROP POLICY r1242_extra ON public.mixer_authz_applications"}
        ]

    accepted = observe("pre-negative positive", :build_catalog_v3)
    if accepted.outcome != "admitted", do: raise("positive lost before mutations")

    controls =
      Enum.map(cases, fn {name, mutation, restore} ->
        Enum.each(String.split(mutation, ";", trim: true), &q(Admin, &1))
        result = observe(name, :build_catalog_v3)
        Enum.each(String.split(restore, ";", trim: true), &q(Admin, &1))
        if result.outcome != "refused", do: raise("accepted closed control " <> name)

        if name in [
             "extra PUBLIC application policy",
             "changed old read policy",
             "changed old lock policy",
             "PUBLIC SELECT-only unrelated column",
             "changed catalog function volatility"
           ] and
             result.surface != "Elixir.MixerHosted.BrowserAuth.BuildCatalogAdmission",
           do: raise("wrong refusal surface " <> name)

        if observe("restored " <> name, :build_catalog_v3).outcome != "admitted",
          do: raise("restore failed " <> name)

        %{name: name, outcome: result.outcome, surface: result.surface, restored_positive: true}
      end)

    q(Admin, "DROP TABLE public.r1258_unrelated_column")

    File.write!(
      Path.join(
        System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
        "qualified-negative-controls.json"
      ),
      Jason.encode!(controls)
    )

    controls
  end
end

defmodule MixerHosted.BrowserAuth.CatalogBrowserCurrentSurfaceJoinTest do
  use ExUnit.Case, async: false
  @tag :catalog_browser_current_surface_join
  test "catalog_browser_current_surface_join compares actual PG17 baseline and installed authority" do
    result = R1242.Direct.run()
    assert result.baseline.acl.count == 132
    assert result.catalog.acl.count == 138
    assert result.baseline.v2.outcome == "admitted"
    assert result.baseline.v3.outcome == "refused"
    assert result.catalog.v2.outcome == "refused"
    assert result.catalog.v3.outcome == "admitted", inspect(result.catalog.v3)
    R1242.Direct.cleanup_direct_databases!()
  end
end
