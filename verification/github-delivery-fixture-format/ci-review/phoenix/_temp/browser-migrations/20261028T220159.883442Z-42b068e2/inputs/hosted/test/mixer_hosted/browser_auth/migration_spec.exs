Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :warning)

defmodule MixerBrowserMigrationFixture.Repo do
  use Ecto.Repo, otp_app: :mixer_browser_migration_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerBrowserMigrationFixture.Test do
  use ExUnit.Case, async: false
  alias MixerBrowserMigrationFixture.Repo
  alias MixerHosted.BrowserAuth.{ActivationPreparationSchema, StorageSchema}

  @versions [
    20_261_024_000_000,
    20_261_025_000_000,
    20_261_025_000_001,
    20_261_025_000_002,
    20_261_025_000_003,
    20_261_025_000_004,
    20_261_025_000_005,
    20_261_025_000_006,
    20_261_025_000_007,
    20_261_025_000_008
  ]

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_BROWSER_MIGRATION_PORT")),
       database: "browser_migrations",
       username: "migration_owner",
       ssl: false,
       pool_size: 2,
       log: false}
    )

    :ok
  end

  test "ten ordinary migrations remain inert and reversible under an unprivileged schema owner" do
    path = Path.expand("../../../priv/repo/migrations", __DIR__)
    roles_before = Repo.query!("SELECT oid,rolname FROM pg_roles ORDER BY oid").rows
    assert @versions == Ecto.Migrator.run(Repo, path, :up, all: true, log: false)
    assert [] == Ecto.Migrator.run(Repo, path, :up, all: true, log: false)
    assert_inert()

    # Existing build data predates the latest seven migrations and must survive
    # their rollback/reapply. This exercises real foreign-key/policy teardown.
    Repo.query!("""
    INSERT INTO mixer_builds
      (id,organization_id,project_id,application_id,build_id,platform,request_key,
       revision,journal,inserted_at,updated_at)
    VALUES ('00000000-0000-4000-8000-000000000001','org','project','app','build',
            'ios','request',0,'{}',now(),now())
    """)

    before = Repo.query!("SELECT * FROM mixer_builds ORDER BY id").rows
    baseline = baseline_surface()
    unload()
    assert [List.last(@versions)] == Ecto.Migrator.run(Repo, path, :down, step: 1, log: false)

    assert %{rows: [[nil, nil]]} =
             Repo.query!("""
             SELECT (SELECT oid::text FROM pg_proc WHERE proname='mixer_browser_prepare_activation'),
                    to_regtype('public.mixer_browser_access_evidence')::text
             """)

    assert baseline_surface() == baseline
    unload()
    assert [List.last(@versions)] == Ecto.Migrator.run(Repo, path, :up, all: true, log: false)
    assert baseline_surface() == baseline
    assert before == Repo.query!("SELECT * FROM mixer_builds ORDER BY id").rows
    assert_inert()
    unload()
    latest = Enum.drop(@versions, 3)
    assert Enum.reverse(latest) == Ecto.Migrator.run(Repo, path, :down, step: 7, log: false)

    assert %{rows: [[nil, nil, nil]]} =
             Repo.query!("""
             SELECT to_regclass('public.mixer_browser_sessions')::text,
                    to_regclass('public.mixer_authz_profiles')::text,
                    to_regclass('public.mixer_build_fleet_capacity')::text
             """)

    assert before == Repo.query!("SELECT * FROM mixer_builds ORDER BY id").rows
    unload()
    assert latest == Ecto.Migrator.run(Repo, path, :up, all: true, log: false)
    assert before == Repo.query!("SELECT * FROM mixer_builds ORDER BY id").rows
    assert_inert()
    unload()
    assert Enum.reverse(@versions) == Ecto.Migrator.run(Repo, path, :down, all: true, log: false)
    unload()
    assert @versions == Ecto.Migrator.run(Repo, path, :up, all: true, log: false)
    assert [] == Ecto.Migrator.run(Repo, path, :up, all: true, log: false)
    assert_inert()
    assert roles_before == Repo.query!("SELECT oid,rolname FROM pg_roles ORDER BY oid").rows
  end

  defp assert_inert do
    tables = ~w(sessions session_vault oidc_attempts session_events)

    for suffix <- tables do
      table = "mixer_browser_" <> suffix

      assert %{rows: [[true, true, false, false, false, false]]} =
               Repo.query!(
                 """
                 SELECT c.relrowsecurity,c.relforcerowsecurity,
                        has_table_privilege('migration_runtime',c.oid,'SELECT'),
                        has_table_privilege('migration_runtime',c.oid,'INSERT'),
                        has_table_privilege('migration_runtime',c.oid,'UPDATE'),
                        has_table_privilege('migration_runtime',c.oid,'DELETE')
                 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                 WHERE n.nspname='public' AND c.relname=$1
                 """,
                 [table]
               )

      assert %{rows: [[0]]} =
               Repo.query!(
                 """
                 SELECT count(*) FROM pg_policies
                 WHERE schemaname='public' AND tablename=$1
                 """,
                 [table]
               )
    end

    for {name, signature} <-
          Map.merge(StorageSchema.signatures(), ActivationPreparationSchema.signatures()) do
      qualified = "public.#{name}(#{signature})"

      assert %{rows: [[false]]} =
               Repo.query!("SELECT has_function_privilege('migration_runtime',$1,'EXECUTE')", [
                 qualified
               ])
    end

    assert %{rows: [[false, false]]} =
             Repo.query!("""
             SELECT has_type_privilege('migration_runtime','public.mixer_browser_access_evidence','USAGE'),
                    EXISTS(SELECT 1 FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) a
                      WHERE t.oid='public.mixer_browser_access_evidence'::regtype AND a.grantee=0)
             """)

    # Discovery remains empty before separate operator provisioning and any
    # browser lifecycle owner are installed.
    assert %{rows: [[nil]]} =
             Repo.query!("SELECT public.mixer_browser_load($1,$2)", [<<0::256>>, <<1::256>>])
  end

  defp baseline_surface do
    # Rows include object OIDs, exact source/ACLs, relation owners/RLS, policies,
    # constraints and persisted data; only the new helper/type are excluded.
    queries = [
      "SELECT oid,proname,proowner,prosrc,proacl::text FROM pg_proc WHERE left(proname::text,14)='mixer_browser_' AND proname<>'mixer_browser_prepare_activation' ORDER BY oid",
      "SELECT oid,typname,typowner,typacl::text FROM pg_type WHERE typname IN ('mixer_browser_cipher','mixer_browser_attempt','mixer_browser_verified') ORDER BY oid",
      "SELECT oid,relname,relowner,relacl::text,relrowsecurity,relforcerowsecurity FROM pg_class WHERE left(relname::text,14)='mixer_browser_' AND relname<>'mixer_browser_access_evidence' ORDER BY oid",
      "SELECT to_jsonb(p) FROM pg_policy p WHERE polrelid IN (SELECT oid FROM pg_class WHERE left(relname::text,14)='mixer_browser_' AND relname<>'mixer_browser_access_evidence') ORDER BY oid",
      "SELECT to_jsonb(c) FROM pg_constraint c WHERE conrelid IN (SELECT oid FROM pg_class WHERE left(relname::text,14)='mixer_browser_' AND relname<>'mixer_browser_access_evidence') ORDER BY oid",
      "SELECT to_jsonb(b) FROM public.mixer_builds b ORDER BY id"
    ]

    queries =
      queries ++
        Enum.map(~w(sessions session_vault oidc_attempts session_events), fn suffix ->
          "SELECT to_jsonb(r) FROM public.mixer_browser_" <>
            suffix <> " r ORDER BY to_jsonb(r)::text"
        end)

    Enum.map(queries, &Repo.query!(&1).rows)
  end

  defp unload do
    for module <- [
          MixerHosted.Repo.Migrations.AddOban,
          MixerHosted.Repo.Migrations.AddBuildJournals,
          MixerHosted.Repo.Migrations.AddBuildAdmission,
          MixerHosted.Repo.Migrations.AddBuildAggregateLimits,
          MixerHosted.Repo.Migrations.AddCustomerAuthorization,
          MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
          MixerHosted.Repo.Migrations.AddCustomerArtifactStorage,
          MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery,
          MixerHosted.Repo.Migrations.AddBrowserSessions,
          MixerHosted.Repo.Migrations.AddBrowserActivationPreparation
        ] do
      :code.purge(module)
      :code.delete(module)
    end
  end
end
