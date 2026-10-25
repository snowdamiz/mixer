Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

for {module, username} <- [
      {MixerHosted.BrowserAuth.MigrationUpgrade.Admin, "browser_admin"},
      {MixerHosted.BrowserAuth.MigrationUpgrade.Owner, "browser_admin"},
      {MixerHosted.BrowserAuth.MigrationUpgrade.Lifecycle, "browser_lifecycle"}
    ] do
  defmodule module do
    use Ecto.Repo, otp_app: :browser_migration_upgrade, adapter: Ecto.Adapters.Postgres
    def synthetic_username, do: unquote(username)
  end
end

defmodule MixerHosted.BrowserAuth.MigrationUpgradeTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{ActivationPreparationSchema, Catalog}
  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias MixerHosted.BrowserAuth.MigrationUpgrade.{Admin, Owner, Lifecycle}

  @version 20_261_025_000_008
  @module MixerHosted.Repo.Migrations.AddBrowserActivationPreparation
  @helper "public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)"
  @type_name "public.mixer_browser_access_evidence"
  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @tables ~w(mixer_browser_sessions mixer_browser_session_vault mixer_browser_oidc_attempts mixer_browser_session_events mixer_authz_profiles mixer_authz_bindings mixer_authz_principals mixer_authz_families mixer_authz_credentials mixer_builds)

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: Application.ensure_all_started(app)

    for repo <- [Admin, Owner, Lifecycle] do
      extra =
        cond do
          repo == Owner ->
            [after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end]

          repo == Lifecycle ->
            [
              after_connect: fn c ->
                for sql <- [
                      "SET search_path=pg_catalog",
                      "SET statement_timeout='5s'",
                      "SET lock_timeout='500ms'",
                      "SET idle_in_transaction_session_timeout='5s'",
                      "SET jit=off",
                      "SET bytea_output=hex"
                    ],
                    do: Postgrex.query!(c, sql, [])
              end
            ]

          true ->
            []
        end

      start_supervised!(
        {repo,
         [
           hostname: "127.0.0.1",
           port: F.port(),
           username: repo.synthetic_username(),
           database: "browser_storage",
           pool_size: if(repo == Owner or repo == Admin, do: 2, else: 1),
           log: false
         ] ++ extra}
      )
    end

    path = Path.expand("hosted/priv/repo/migrations")
    assert length(Ecto.Migrator.run(Owner, path, :up, to: @version - 1, log: false)) == 9
    assert [] == Ecto.Migrator.run(Owner, path, :up, to: @version - 1, log: false)
    F.provision!()

    q(
      Admin,
      "INSERT INTO mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)"
    )

    q(Admin, "INSERT INTO mixer_authz_principals VALUES('person-1','human',true,0,1)")

    q(
      Admin,
      "INSERT INTO mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)"
    )

    q(Admin, """
    INSERT INTO mixer_builds
      (id,organization_id,project_id,application_id,build_id,platform,request_key,
       revision,journal,inserted_at,updated_at)
    VALUES ('00000000-0000-4000-8000-000000000001','org','project','app','build',
            'ios','request',0,'{}',now(),now())
    """)

    q(Lifecycle, "SELECT 1")
    :ok
  end

  test "actual additive Ecto upgrade is inert, explicit V2 provisioning works, and operator down restores V1 with baseline data intact" do
    assert admission(1) == :function_surface_verified
    assert admission(:default) == :function_surface_verified
    denied(2)
    c = F.connection!()

    try do
      b = F.bootstrap(c)
      {b, a} = F.begin_login(c, b)
      {claim, snapshot} = F.claim(c, b, a)
      baseline = baseline_surface()
      persist("baseline-before", baseline)
      up!()

      try do
        assert baseline_surface() == baseline
        denied(1)
        denied(:default)
        denied(2)
        assert {:error, %{postgres: %{code: :insufficient_privilege}}} = prepare(c, b, a, claim)
        assert_closed_addition()
        upgrade!("valid-upgrade")
        assert admission(2) == :function_surface_verified
        denied(1)
        denied(:default)
        assert {:ok, %{rows: [[result]]}} = prepare(c, b, a, claim)
        assert result["snapshot"] == snapshot
        assert result["principal_id"] == "person-1"
        assert baseline_surface() == baseline

        # Runtime identities receive no teardown authority. The synthetic
        # database/public-schema owner retains its pre-existing DROP authority;
        # writer ownership does not imply a new rollback grant is needed.
        assert_runtime_cannot_rollback()
        assert @version in Ecto.Migrator.migrated_versions(Admin)
        assert admission(2) == :function_surface_verified
        assert baseline_surface() == baseline
        down!(Admin)
        assert_addition_absent()
        assert admission(1) == :function_surface_verified
        assert admission(:default) == :function_surface_verified
        denied(2)
        assert baseline_surface() == baseline

        # Reapply creates an inert addition again. No implicit provisioning or
        # automatic fixed-version fallback follows a down/up cycle.
        up!()
        denied(1)
        denied(2)
        assert_closed_addition()
        assert baseline_surface() == baseline
        upgrade!("reapplied-explicit-upgrade")
        assert admission(2) == :function_surface_verified
        down!(Owner)

        persist("owner-drop-authority", %{
          current_user: "browser_schema_owner",
          database_owner: true,
          public_schema_owner_via: "pg_database_owner",
          existing_authority: true,
          post_provision_down_passed: true
        })

        assert admission(1) == :function_surface_verified
        assert baseline_surface() == baseline
        persist("baseline-after", baseline_surface())
      after
        remove_if_present!()
      end
    after
      GenServer.stop(c)
    end
  end

  test "malformed or duplicate role identifiers reject before producing an operator transaction" do
    for value <- [
          nil,
          "",
          "public",
          "pg_reserved",
          "bad-role",
          "writer;GRANT",
          "A",
          String.duplicate("w", 64)
        ] do
      assert_raise ArgumentError, fn ->
        ActivationPreparationSchema.provisioning_statements(
          value,
          "browser_lifecycle",
          "browser_schema_owner"
        )
      end
    end

    assert_raise ArgumentError, fn ->
      ActivationPreparationSchema.provisioning_statements(
        "browser_writer",
        "browser_writer",
        "browser_schema_owner"
      )
    end
  end

  test "unsafe existing writer flags abort the entire one-connection upgrade" do
    baseline = baseline_surface()
    up!()
    q(Admin, "ALTER ROLE browser_writer INHERIT")

    try do
      rejected_upgrade!("unsafe-writer")
      assert_closed_addition()
      assert baseline_surface() == baseline
    after
      q(Admin, "ALTER ROLE browser_writer NOINHERIT")
      remove_if_present!()
    end

    assert admission(1) == :function_surface_verified
  end

  test "unexpected initial third-party helper or type grants deny and roll back every upgrade statement" do
    for {kind, target, privilege} <- [
          {"FUNCTION", @helper, "EXECUTE"},
          {"TYPE", @type_name, "USAGE"}
        ] do
      baseline = baseline_surface()
      up!()
      q(Admin, "GRANT #{privilege} ON #{kind} #{target} TO migration_neighbor")

      try do
        initial = addition_surface()
        rejected_upgrade!("third-party-" <> String.downcase(kind))
        assert addition_surface() == initial
        assert baseline_surface() == baseline
        denied(1)
        denied(2)
      after
        remove_if_present!()
      end
    end

    assert admission(1) == :function_surface_verified
  end

  test "unexpected operator default privileges remain visible and make the newly migrated addition unprovisionable" do
    for {kind, privilege} <- [{"FUNCTIONS", "EXECUTE"}, {"TYPES", "USAGE"}] do
      baseline = baseline_surface()

      q(
        Admin,
        "ALTER DEFAULT PRIVILEGES FOR ROLE browser_schema_owner GRANT #{privilege} ON #{kind} TO migration_neighbor"
      )

      try do
        up!()
        initial = addition_surface()

        assert Enum.any?(initial, fn [_oid, _owner, acl] ->
                 String.contains?(acl, "migration_neighbor")
               end)

        rejected_upgrade!("default-" <> String.downcase(kind))
        assert addition_surface() == initial
        assert baseline_surface() == baseline
        denied(1)
        denied(2)
      after
        q(
          Admin,
          "ALTER DEFAULT PRIVILEGES FOR ROLE browser_schema_owner REVOKE #{privilege} ON #{kind} FROM migration_neighbor"
        )

        remove_if_present!()
      end
    end

    assert admission(1) == :function_surface_verified
  end

  test "operator failure after function ownership transfer rolls back owner, temporary CREATE and all grants" do
    baseline = baseline_surface()
    up!()

    try do
      initial = addition_surface()
      plan = plan!()
      before_commit = Enum.take(plan, 7)
      conn = F.connection!("browser_admin")

      try do
        Enum.each(before_commit, &Postgrex.query!(conn, &1, []))

        assert [[true, "browser_writer"]] =
                 Postgrex.query!(
                   conn,
                   "SELECT has_schema_privilege('browser_writer','public','CREATE'), proowner::regrole::text FROM pg_proc WHERE oid=$1::text::regprocedure",
                   [@helper]
                 ).rows

        assert {:error, %{postgres: %{code: :raise_exception}}} =
                 Postgrex.query(
                   conn,
                   "DO $failure$ BEGIN RAISE EXCEPTION 'synthetic operator interruption'; END $failure$",
                   []
                 )

        Postgrex.query!(conn, "ROLLBACK", [])
      after
        GenServer.stop(conn)
      end

      assert addition_surface() == initial
      assert_closed_addition()
      assert baseline_surface() == baseline

      persist("interrupted-upgrade", %{
        statements_executed: before_commit,
        connection: "browser_admin",
        rolled_back: true
      })
    after
      remove_if_present!()
    end

    assert admission(1) == :function_surface_verified
  end

  defp q(repo, sql, params \\ []), do: Ecto.Adapters.SQL.query!(repo, sql, params, log: false)
  defp migration_path, do: Path.expand("hosted/priv/repo/migrations")

  defp unload do
    :code.purge(@module)
    :code.delete(@module)
  end

  defp up! do
    unload()
    assert [@version] == Ecto.Migrator.run(Owner, migration_path(), :up, all: true, log: false)
    assert [] == Ecto.Migrator.run(Owner, migration_path(), :up, all: true, log: false)
  end

  defp down!(repo) do
    unload()
    assert [@version] == Ecto.Migrator.run(repo, migration_path(), :down, step: 1, log: false)
  end

  defp remove_if_present! do
    if @version in Ecto.Migrator.migrated_versions(Admin), do: down!(Admin)
  end

  defp plan!,
    do:
      ActivationPreparationSchema.provisioning_statements(
        "browser_writer",
        "browser_lifecycle",
        "browser_schema_owner"
      )

  defp upgrade!(label) do
    conn = F.connection!("browser_admin")

    try do
      [[pid, "browser_admin", "browser_admin"]] =
        Postgrex.query!(
          conn,
          "SELECT pg_backend_pid(), session_user::text, current_user::text",
          []
        ).rows

      plan = plan!()
      assert List.first(plan) == "BEGIN"
      assert List.last(plan) == "COMMIT"
      results = Enum.map(plan, fn sql -> Postgrex.query!(conn, sql, []).command end)
      assert [[^pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows

      persist(label, %{
        statements: plan,
        commands: results,
        backend_pid: pid,
        session_user: "browser_admin",
        current_user: "browser_admin",
        one_connection: true
      })
    after
      GenServer.stop(conn)
    end
  end

  defp rejected_upgrade!(label) do
    conn = F.connection!("browser_admin")

    try do
      [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows

      results =
        Enum.reduce_while(plan!(), [], fn sql, results ->
          result = Postgrex.query(conn, sql, [])

          if match?({:error, _}, result),
            do: {:halt, results ++ [result]},
            else: {:cont, results ++ [result]}
        end)

      assert Enum.any?(
               results,
               &match?({:error, %{postgres: %{code: :insufficient_privilege}}}, &1)
             )

      # Stop at the first failure and roll back the same connection. Never
      # continue or retry the remaining statements of a failed plan.
      Postgrex.query!(conn, "ROLLBACK", [])
      assert [[^pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows

      persist(label, %{
        backend_pid: pid,
        one_connection: true,
        rolled_back: true,
        commands:
          Enum.map(results, fn
            {:ok, result} -> %{command: result.command}
            {:error, error} -> %{error: error.postgres.code}
          end)
      })
    after
      GenServer.stop(conn)
    end
  end

  defp admission(version) do
    {:ok, result} =
      Lifecycle.transaction(
        fn ->
          deadline = System.monotonic_time(:millisecond) + 4_500

          if version == :default,
            do: Catalog.check_function_surface!(Lifecycle, @roles, deadline),
            else: Catalog.check_function_surface!(Lifecycle, @roles, deadline, version)
        end,
        timeout: 5_000,
        queue: false
      )

    result
  end

  defp denied(version) do
    error = assert_raise Catalog.Unavailable, fn -> admission(version) end
    assert Exception.message(error) == "browser catalog function surface unavailable"
  end

  defp assert_closed_addition do
    assert [["browser_schema_owner", "browser_schema_owner", false, false, false, false]] =
             q(
               Admin,
               """
               SELECT p.proowner::regrole::text,t.typowner::regrole::text,
                 has_function_privilege('browser_lifecycle',p.oid,'EXECUTE'),
                 has_type_privilege('browser_lifecycle',t.oid,'USAGE'),
                 has_schema_privilege('browser_writer','public','CREATE'),
                 has_schema_privilege('browser_lifecycle','public','CREATE')
               FROM pg_proc p JOIN pg_type t ON t.oid='public.mixer_browser_access_evidence'::regtype
               WHERE p.oid=$1::text::regprocedure
               """,
               [@helper]
             ).rows
  end

  defp assert_runtime_cannot_rollback do
    for role <- ["browser_lifecycle", "browser_ordinary"] do
      conn = F.connection!(role)

      try do
        for {kind, target} <- [{"FUNCTION", @helper}, {"TYPE", @type_name}] do
          Postgrex.query!(conn, "BEGIN", [])

          assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
                   Postgrex.query(conn, "DROP #{kind} #{target}", [])

          Postgrex.query!(conn, "ROLLBACK", [])
        end
      after
        GenServer.stop(conn)
      end
    end

    persist("runtime-teardown-denied", %{
      roles: ["browser_lifecycle", "browser_ordinary"],
      fixed_drops: [@helper, @type_name],
      each_rolled_back: true,
      code: "insufficient_privilege"
    })
  end

  defp assert_addition_absent do
    assert [[0, nil]] =
             q(
               Admin,
               "SELECT (SELECT count(*) FROM pg_proc WHERE proname='mixer_browser_prepare_activation'), to_regtype('public.mixer_browser_access_evidence')::text"
             ).rows
  end

  defp addition_surface do
    q(
      Admin,
      """
      SELECT oid::bigint,proowner::regrole::text,proacl::text FROM pg_proc WHERE oid=$1::text::regprocedure
      UNION ALL SELECT oid::bigint,typowner::regrole::text,typacl::text FROM pg_type WHERE oid='public.mixer_browser_access_evidence'::regtype
      ORDER BY 1
      """,
      [@helper]
    ).rows
  end

  defp baseline_surface do
    catalogs = [
      {"functions",
       "SELECT to_jsonb(p) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND left(p.proname::text,14)='mixer_browser_' AND p.proname<>'mixer_browser_prepare_activation' ORDER BY p.oid"},
      {"types",
       "SELECT to_jsonb(t) FROM pg_type t WHERE typname IN('mixer_browser_cipher','mixer_browser_attempt','mixer_browser_verified') ORDER BY oid"},
      {"tables",
       "SELECT c.oid::bigint,c.relname::text,c.relowner::bigint,c.relacl::text,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname<>'schema_migrations' ORDER BY c.oid"},
      {"policies", "SELECT to_jsonb(p) FROM pg_policy p ORDER BY oid"},
      {"constraints",
       "SELECT to_jsonb(c) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' ORDER BY c.oid"},
      {"roles", "SELECT oid::bigint,rolname::text FROM pg_roles ORDER BY oid"}
    ]

    Map.new(catalogs, fn {name, sql} -> {name, q(Admin, sql).rows} end)
    |> Map.put(
      "data",
      Map.new(@tables, fn table ->
        {table,
         q(Admin, "SELECT to_jsonb(t) FROM public.#{table} t ORDER BY to_jsonb(t)::text").rows}
      end)
    )
  end

  defp prepare(c, b, a, claim) do
    i = F.identity()

    Postgrex.query(
      c,
      """
      SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,
        ROW($6,$7,$8,$9,$10,$11,$12,$13,$14)::public.mixer_browser_access_evidence)
      """,
      [
        b.cookie,
        a.state,
        b.config,
        claim,
        b.revision,
        i.profile,
        1,
        i.issuer,
        i.subject,
        i.client,
        i.jti,
        i.iat,
        i.exp,
        i.scopes
      ]
    )
  end

  defp persist(name, value),
    do:
      File.write!(
        Path.join(System.fetch_env!("MIXER_MIGRATION_UPGRADE_OUTPUT"), name <> ".json"),
        Jason.encode!(value, pretty: true)
      )
end
