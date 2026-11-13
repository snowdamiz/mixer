Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.CustomerCreateBuildPolicyExclusivityR2156Test do
  use ExUnit.Case, async: false
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  alias MixerHosted.BrowserAuth.{
    LifecycleRepo,
    BuildCatalogAdmission,
    ActivationPreparationSchema,
    ActiveReadSchema
  }

  alias MixerHosted.CustomerBuilds.CreateSchema

  setup_all do
    parent = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")

    previous =
      for k <- ~w(MIXER_BROWSER_CATALOG_FIXTURE_ROOT MIXER_BROWSER_CATALOG_EVIDENCE),
          do: {k, System.fetch_env(k)}

    attempt = Path.join(parent, "attempt-" <> Base.encode16(:crypto.strong_rand_bytes(6)))
    File.mkdir!(attempt)
    System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", attempt)

    on_exit(fn ->
      for {k, value} <- previous do
        case value do
          {:ok, v} -> System.put_env(k, v)
          :error -> System.delete_env(k)
        end
      end

      assert System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT") == parent
      File.write!(Path.join(parent, "parent-restored.json"), Jason.encode!(%{restored: true}))
    end)

    conn = F.connection!("browser_admin", "postgres")

    try do
      for {role, login} <- [
            {"mixer_customer_build_catalog_definer_v1", false},
            {"mixer_build_create", true}
          ] do
        case Postgrex.query!(
               conn,
               "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=$1",
               [role]
             ).rows do
          [] ->
            Postgrex.query!(
              conn,
              "CREATE ROLE " <>
                role <>
                if(login, do: " LOGIN", else: " NOLOGIN") <>
                " NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT",
              []
            )

          [[^login, false, false, false, false, false, false]] ->
            :ok
        end
      end

      Postgrex.query!(
        conn,
        "CREATE DATABASE browser_ordinary_installation_r1422 OWNER browser_schema_owner",
        []
      )
    after
      GenServer.stop(conn)
    end

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_ordinary_installation_r1422",
      pool_size: 2,
      log: false
    ]

    old_admin = Application.fetch_env(:browser_storage_fixture, Admin)
    Application.put_env(:browser_storage_fixture, Admin, settings ++ [username: "browser_admin"])

    on_exit(fn ->
      case old_admin do
        {:ok, value} -> Application.put_env(:browser_storage_fixture, Admin, value)
        :error -> Application.delete_env(:browser_storage_fixture, Admin)
      end

      conn = F.connection!("browser_admin", "postgres")

      try do
        Postgrex.query!(conn, "DROP DATABASE browser_ordinary_installation_r1422", [])
      after
        GenServer.stop(conn)
      end
    end)

    start_supervised!({Admin, settings ++ [username: "browser_admin"]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "browser_admin",
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end
         ]}
    )

    F.install!()
    F.q!(Admin, "GRANT USAGE ON SCHEMA public TO browser_ordinary")
    F.q!(Admin, "GRANT SELECT ON ALL TABLES IN SCHEMA public TO browser_ordinary")

    for h <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.q!(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_" <> h <> "() TO browser_ordinary"
          )

    for t <- ~w(sessions session_vault oidc_attempts session_events),
        do: F.q!(Admin, "REVOKE SELECT ON public.mixer_browser_" <> t <> " FROM browser_ordinary")

    for sql <- ActivationPreparationSchema.statements(), do: F.q!(Migration, sql)
    F.provision!()
    conn = F.connection!("browser_admin")

    try do
      for sql <-
            ActivationPreparationSchema.provisioning_statements(
              "browser_writer",
              "browser_lifecycle",
              "browser_schema_owner"
            ),
          do: Postgrex.query!(conn, sql, [])
    after
      GenServer.stop(conn)
    end

    for sql <- ActiveReadSchema.statements(), do: F.q!(Migration, sql)
    conn = F.connection!("browser_admin")

    try do
      for sql <- ActiveReadSchema.provisioning_statements(), do: Postgrex.query!(conn, sql, [])
    after
      GenServer.stop(conn)
    end

    Code.require_file("priv/repo/migrations/20261025000000_add_build_journals.exs")

    :ok =
      Ecto.Migrator.up(
        Migration,
        20_261_025_000_000,
        MixerHosted.Repo.Migrations.AddBuildJournals,
        log: false
      )

    :ok = Ecto.Migrator.up(Migration, 1, R1026.ObanMigration, log: false)
    F.q!(Migration, MixerHosted.CustomerBuilds.Schema.ddl())

    F.q!(
      Migration,
      "REVOKE ALL ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) FROM PUBLIC"
    )

    F.q!(
      Migration,
      "GRANT EXECUTE ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) TO browser_ordinary"
    )

    for sql <- MixerHosted.CustomerArtifacts.Schema.statements(), do: F.q!(Migration, sql)
    for sql <- MixerHosted.CustomerBuildCatalog.Schema.private_statements(), do: F.q!(Admin, sql)
    # The same complete fixed LifecycleRepo configuration as the ordinary fixture.
    life = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_ordinary_installation_r1422",
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

    start_supervised!({LifecycleRepo, life})

    roles = %{
      lifecycle_login: "browser_lifecycle",
      writer: "browser_writer",
      relation_owner: "browser_schema_owner",
      ordinary_runtime_login: "browser_ordinary"
    }

    %{roles: roles, evidence: attempt}
  end

  defp admission(roles, enabled) do
    try do
      LifecycleRepo.transaction(
        fn ->
          F.q!(LifecycleRepo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

          F.q!(
            LifecycleRepo,
            "SELECT set_config('search_path','pg_catalog',true),set_config('jit','off',true),set_config('statement_timeout','5s',true),set_config('lock_timeout','500ms',true),set_config('idle_in_transaction_session_timeout','5s',true),set_config('bytea_output','hex',true)"
          )

          [["browser_lifecycle", "browser_lifecycle", "pg_catalog", "5s", "500ms"]] =
            F.q!(
              LifecycleRepo,
              "SELECT current_user::text,session_user::text,current_setting('search_path'),current_setting('statement_timeout'),current_setting('lock_timeout')"
            ).rows

          BuildCatalogAdmission.check!(
            LifecycleRepo,
            roles,
            System.monotonic_time(:millisecond) + 5000,
            enabled
          )
        end,
        timeout: 5000,
        queue: false
      )
    rescue
      MixerHosted.BrowserAuth.RelationCatalog.Unavailable -> :refused
    end
  end

  defp ready!(deadline, attempts \\ []) do
    remaining = deadline - System.monotonic_time(:millisecond)

    assert remaining > 0,
           "same-repo SQL readiness exceeded original 5000ms bound: #{inspect(attempts)}"

    result =
      try do
        {:ready,
         Ecto.Adapters.SQL.query!(
           LifecycleRepo,
           "SELECT current_database()::text,current_user::text,session_user::text,pg_backend_pid()",
           [],
           timeout: min(5000, remaining),
           queue: false
         ).rows}
      rescue
        e in DBConnection.ConnectionError -> {:checkout_refused, Exception.message(e)}
      end

    case result do
      {:ready,
       [["browser_ordinary_installation_r1422", "browser_lifecycle", "browser_lifecycle", pid]] =
           rows} ->
        proof = %{
          repo: inspect(LifecycleRepo),
          rows: rows,
          backend: pid,
          queue: false,
          deadline_ms: 5000,
          checkout_refusals: Enum.reverse(attempts)
        }

        File.write!(
          Path.join(
            System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
            "same-repo-ready.json"
          ),
          Jason.encode!(proof)
        )

        IO.puts("R2224_READY_ACTUAL " <> Jason.encode!(proof))

      {:checkout_refused, reason} ->
        Process.sleep(min(10, max(0, deadline - System.monotonic_time(:millisecond))))
        ready!(deadline, [reason | attempts])
    end
  end

  defp sql(statements), do: Enum.each(List.wrap(statements), &F.q!(Admin, &1))
  defp note(label), do: IO.puts("R2156_PASS " <> label)

  defp refuses(roles, enabled),
    do: assert(admission(roles, enabled) in [:refused, {:error, :authorization_unavailable}])

  @tag :actual_create_build_policy_exclusivity_pg_join
  test "actual_create_build_policy_exclusivity_pg_join", c do
    ready!(System.monotonic_time(:millisecond) + 5000)
    assert {:ok, :ok} = admission(c.roles, false)
    note("legacy_before_create_ddl")

    for {label, change, restore} <- [
          {"legacy_lock_check",
           "ALTER POLICY catalog_applications_lock_v1 ON public.mixer_authz_applications WITH CHECK(true)",
           "ALTER POLICY catalog_applications_lock_v1 ON public.mixer_authz_applications WITH CHECK(false)"},
          {"legacy_read_role",
           "ALTER POLICY catalog_applications_read_v1 ON public.mixer_authz_applications TO browser_ordinary",
           "ALTER POLICY catalog_applications_read_v1 ON public.mixer_authz_applications TO mixer_customer_build_catalog_definer_v1"},
          {"legacy_creator_exact",
           "CREATE POLICY build_catalog_owner ON public.mixer_builds FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)",
           "DROP POLICY build_catalog_owner ON public.mixer_builds"},
          {"legacy_creator_wrong_body",
           "CREATE POLICY build_catalog_lock ON public.mixer_builds FOR UPDATE TO mixer_customer_build_catalog_definer_v1 USING(false) WITH CHECK(true)",
           "DROP POLICY build_catalog_lock ON public.mixer_builds"},
          {"legacy_wrong_relation_same_name",
           "CREATE POLICY build_catalog_owner ON public.mixer_authz_profiles FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)",
           "DROP POLICY build_catalog_owner ON public.mixer_authz_profiles"}
        ] do
      sql(change)
      refuses(c.roles, false)
      sql(restore)
      assert {:ok, :ok} = admission(c.roles, false)
      note(label <> "_reject_restore")
    end

    sql("GRANT USAGE ON SCHEMA public TO mixer_build_create")

    sql(
      "GRANT SELECT ON " <>
        Enum.map_join(
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
          ",",
          &("public.mixer_authz_" <> &1)
        ) <> " TO mixer_build_create"
    )

    for h <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.q!(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_" <>
              h <> "() TO mixer_build_create"
          )

    for statement <- CreateSchema.statements(), do: F.q!(Migration, statement)

    for statement <- MixerHosted.BrowserAuth.ActiveCreateSchema.statements(),
        do: F.q!(Migration, statement)

    sql("GRANT CREATE ON SCHEMA public TO browser_writer")

    sql(
      "ALTER FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) OWNER TO browser_writer"
    )

    sql("REVOKE CREATE ON SCHEMA public FROM browser_writer")

    sql(
      "GRANT EXECUTE ON FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) TO mixer_build_create"
    )

    assert {:ok, :ok} = admission(c.roles, true)
    note("exact_create_mode_accepts")

    assert {:ok, [[false]]} =
             LifecycleRepo.transaction(fn ->
               F.q!(
                 LifecycleRepo,
                 "SELECT (SELECT count(*) FROM pg_catalog.pg_policy WHERE polrelid='public.mixer_authz_applications'::regclass)=4 AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_policy p WHERE (SELECT oid FROM pg_catalog.pg_roles WHERE rolname='mixer_customer_build_catalog_definer_v1')=ANY(p.polroles) AND NOT(p.polrelid='public.mixer_authz_applications'::regclass AND p.polname=ANY(ARRAY['catalog_applications_read_v1','catalog_applications_lock_v1']::text[])))"
               ).rows
             end)

    note("original_exclusivity_predicate_actual_false")
    refuses(c.roles, false)
    note("create_false_preserves_legacy_rls")

    sql([
      "ALTER TABLE public.mixer_builds NO FORCE ROW LEVEL SECURITY",
      "ALTER TABLE public.mixer_builds DISABLE ROW LEVEL SECURITY"
    ])

    refuses(c.roles, false)
    note("create_false_rejects_exact_creator_policies_even_with_legacy_rls")

    sql([
      "ALTER TABLE public.mixer_builds ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE public.mixer_builds FORCE ROW LEVEL SECURITY"
    ])

    assert {:ok, :ok} = admission(c.roles, true)

    mutations = [
      {"body", "ALTER POLICY build_catalog_owner ON public.mixer_builds USING(false)",
       "ALTER POLICY build_catalog_owner ON public.mixer_builds USING(true)"},
      {"check", "ALTER POLICY build_catalog_lock ON public.mixer_builds WITH CHECK(true)",
       "ALTER POLICY build_catalog_lock ON public.mixer_builds WITH CHECK(false)"},
      {"role", "ALTER POLICY build_catalog_owner ON public.mixer_builds TO browser_ordinary",
       "ALTER POLICY build_catalog_owner ON public.mixer_builds TO mixer_customer_build_catalog_definer_v1"},
      {"multi_role",
       "ALTER POLICY build_catalog_owner ON public.mixer_builds TO browser_ordinary,mixer_customer_build_catalog_definer_v1",
       "ALTER POLICY build_catalog_owner ON public.mixer_builds TO mixer_customer_build_catalog_definer_v1"},
      {"wrong_relation_same_name",
       "CREATE POLICY build_catalog_owner ON public.mixer_authz_profiles FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)",
       "DROP POLICY build_catalog_owner ON public.mixer_authz_profiles"},
      {"extra_unknown_policy",
       "CREATE POLICY r2156_extra ON public.mixer_authz_profiles FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)",
       "DROP POLICY r2156_extra ON public.mixer_authz_profiles"},
      {"extra_build_policy",
       "CREATE POLICY r2156_extra ON public.mixer_builds FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)",
       "DROP POLICY r2156_extra ON public.mixer_builds"},
      {"command",
       [
         "DROP POLICY build_catalog_owner ON public.mixer_builds",
         "CREATE POLICY build_catalog_owner ON public.mixer_builds FOR UPDATE TO mixer_customer_build_catalog_definer_v1 USING(true)"
       ],
       [
         "DROP POLICY build_catalog_owner ON public.mixer_builds",
         "CREATE POLICY build_catalog_owner ON public.mixer_builds FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)"
       ]},
      {"permissive",
       [
         "DROP POLICY build_catalog_owner ON public.mixer_builds",
         "CREATE POLICY build_catalog_owner ON public.mixer_builds AS RESTRICTIVE FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)"
       ],
       [
         "DROP POLICY build_catalog_owner ON public.mixer_builds",
         "CREATE POLICY build_catalog_owner ON public.mixer_builds FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)"
       ]},
      {"legacy_in_create",
       "ALTER POLICY catalog_applications_lock_v1 ON public.mixer_authz_applications WITH CHECK(true)",
       "ALTER POLICY catalog_applications_lock_v1 ON public.mixer_authz_applications WITH CHECK(false)"}
    ]

    for {label, change, restore} <- mutations do
      sql(change)
      refuses(c.roles, true)
      sql(restore)
      assert {:ok, :ok} = admission(c.roles, true)
      note(label <> "_reject_restore")
    end

    rows =
      F.q!(
        Admin,
        "SELECT c.relname::text,p.polname::text,p.polcmd::text,p.polpermissive,ARRAY(SELECT r.rolname::text FROM pg_roles r WHERE r.oid=ANY(p.polroles) ORDER BY r.rolname),pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid) FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid WHERE (SELECT oid FROM pg_roles WHERE rolname='mixer_customer_build_catalog_definer_v1')=ANY(p.polroles) ORDER BY c.relname,p.polname"
      ).rows

    assert length(rows) == 4

    File.write!(
      Path.join(c.evidence, "actual-component-matrix.json"),
      Jason.encode!(%{
        test: "actual_create_build_policy_exclusivity_pg_join",
        strict_repo: "LifecycleRepo",
        legacy_mutations: 5,
        create_mutations: length(mutations),
        all_restored: true,
        final_policy_rows: rows,
        app_runtime_owner_started: false,
        store_admit_called: false,
        providers_started: false
      })
    )

    assert Process.whereis(MixerHosted.BrowserAuth.RuntimeOwner) == nil
    assert Process.whereis(MixerHosted.BrowserAuth.ProviderOwner) == nil
  end
end
