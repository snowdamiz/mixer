Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule PreparationMigrationReview.Admin do
  use Ecto.Repo, otp_app: :preparation_migration_review, adapter: Ecto.Adapters.Postgres
end

defmodule PreparationMigrationReview.Owner do
  use Ecto.Repo, otp_app: :preparation_migration_review, adapter: Ecto.Adapters.Postgres
end

defmodule PreparationMigrationReview.Lifecycle do
  use Ecto.Repo, otp_app: :preparation_migration_review, adapter: Ecto.Adapters.Postgres
end

defmodule PreparationMigrationReview.Test do
  use ExUnit.Case, async: false
  alias PreparationMigrationReview.{Admin, Owner, Lifecycle}
  alias MixerHosted.BrowserAuth.{ActivationPreparationSchema, Catalog, StorageSchema}
  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  @version 20_261_025_000_008
  @migration MixerHosted.Repo.Migrations.AddBrowserActivationPreparation
  @helper "public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)"
  @type_name "public.mixer_browser_access_evidence"
  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: Application.ensure_all_started(app)
    Logger.configure(level: :warning)

    for repo <- [Admin, Owner, Lifecycle] do
      opts = [
        hostname: "127.0.0.1",
        port: F.port(),
        database: "browser_storage",
        username: if(repo == Lifecycle, do: "browser_lifecycle", else: "browser_admin"),
        pool_size: 2,
        log: false
      ]

      after_connect = fn conn ->
        if repo == Owner, do: Postgrex.query!(conn, "SET ROLE browser_schema_owner", [])

        if repo == Lifecycle do
          for sql <- [
                "SET search_path=pg_catalog",
                "SET statement_timeout='5s'",
                "SET lock_timeout='500ms'",
                "SET idle_in_transaction_session_timeout='5s'",
                "SET jit=off",
                "SET bytea_output=hex"
              ],
              do: Postgrex.query!(conn, sql, [])
        end
      end

      start_supervised!({repo, opts ++ [after_connect: after_connect]})
    end

    assert length(Ecto.Migrator.run(Owner, path(), :up, to: @version - 1, log: false)) == 9
    conn = F.connection!("browser_admin")

    try do
      for statement <-
            StorageSchema.provisioning_statements("browser_writer", "browser_lifecycle"),
          do: Postgrex.query!(conn, statement, [])
    after
      GenServer.stop(conn)
    end

    q(
      "INSERT INTO mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)"
    )

    q("INSERT INTO mixer_authz_principals VALUES('person-1','human',true,0,1)")
    q("INSERT INTO mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)")

    q(
      "INSERT INTO mixer_builds (id,organization_id,project_id,application_id,build_id,platform,request_key,revision,journal,inserted_at,updated_at) VALUES ('00000000-0000-4000-8000-000000000009','review-org','review-project','review-app','review-build','android','review-key',3,'{" <>
        "\"preserved\":true" <> "}',now(),now())"
    )

    :ok
  end

  setup do
    assert @version not in Ecto.Migrator.migrated_versions(Admin)
    before = baseline()

    on_exit(fn ->
      q("DROP EVENT TRIGGER IF EXISTS review_fail_preparation")
      q("DROP FUNCTION IF EXISTS public.review_fail_preparation()")
      q("DROP TABLE IF EXISTS public.review_type_dependency")
      if @version in Ecto.Migrator.migrated_versions(Admin), do: down!()
    end)

    %{baseline: before}
  end

  test "preexisting conflicting type keeps its OID and failed up records no migration", %{
    baseline: before
  } do
    q("CREATE TYPE #{@type_name} AS (unrelated integer)")
    [[oid]] = q("SELECT '#{@type_name}'::regtype::oid::bigint").rows
    assert_raise Postgrex.Error, fn -> up!() end
    assert [[^oid]] = q("SELECT '#{@type_name}'::regtype::oid::bigint").rows

    assert [[0]] =
             q("SELECT count(*) FROM pg_proc WHERE proname='mixer_browser_prepare_activation'").rows

    assert @version not in Ecto.Migrator.migrated_versions(Admin)
    q("DROP TYPE #{@type_name}")
    assert baseline() == before

    persist("conflict-up", %{conflicting_oid: oid, version_absent: true, baseline_preserved: true})
  end

  test "injected CREATE FUNCTION failure rolls back the preceding CREATE TYPE and migration record",
       %{baseline: before} do
    q(
      "CREATE FUNCTION public.review_fail_preparation() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'independent mid-up fault'; END $$"
    )

    q(
      "CREATE EVENT TRIGGER review_fail_preparation ON ddl_command_end WHEN TAG IN ('CREATE FUNCTION') EXECUTE FUNCTION public.review_fail_preparation()"
    )

    try do
      error = assert_raise Postgrex.Error, fn -> up!() end
      assert error.postgres.code == :raise_exception
      absent!()
      assert @version not in Ecto.Migrator.migrated_versions(Admin)
    after
      q("DROP EVENT TRIGGER review_fail_preparation")
      q("DROP FUNCTION public.review_fail_preparation()")
    end

    assert baseline() == before
    up!()
    down!()
    assert baseline() == before

    persist("mid-up-atomicity", %{
      type_and_function_absent: true,
      failed_version_absent: true,
      retry_after_fault_removal: true
    })
  end

  test "fixed version selection round trip preserves a claimed session and actual preparation is read only" do
    assert admit(1) == :function_surface_verified
    assert admit(:legacy) == :function_surface_verified
    deny(2)
    conn = F.connection!()

    try do
      browser = F.bootstrap(conn)
      {browser, attempt} = F.begin_login(conn, browser)
      {claim, snapshot} = F.claim(conn, browser, attempt)
      before = baseline()
      up!()
      for version <- [1, 2, :legacy], do: deny(version)
      assert error_code(prepare(conn, browser, attempt, claim)) == :insufficient_privilege
      inert!()
      upgrade!()
      assert admit(2) == :function_surface_verified
      for version <- [1, :legacy, 2.0, "2", nil, 0, 3], do: deny(version)

      for _ <- 1..2 do
        assert {:ok, %{rows: [[prepared]]}} = prepare(conn, browser, attempt, claim)
        assert prepared["snapshot"] == snapshot
        assert prepared["principal_id"] == "person-1"
      end

      assert baseline() == before
      down!()
      assert admit(1) == :function_surface_verified
      assert admit(:legacy) == :function_surface_verified
      deny(2)
      assert baseline() == before
      up!()
      inert!()
      deny(2)
      upgrade!()
      assert admit(2) == :function_surface_verified
      down!()
      assert baseline() == before

      persist("version-roundtrip", %{
        baseline: before,
        claim_preparation_repeated_without_mutation: true,
        reapply_requires_provisioning: true
      })
    after
      GenServer.stop(conn)
    end
  end

  test "failed down after function DROP restores function ownership ACLs OIDs and version", %{
    baseline: before
  } do
    up!()
    upgrade!()
    initial = addition()
    q("CREATE TABLE public.review_type_dependency(value #{@type_name})")

    try do
      error = assert_raise Postgrex.Error, fn -> down!() end
      assert error.postgres.code == :dependent_objects_still_exist
      assert addition() == initial
      assert @version in Ecto.Migrator.migrated_versions(Admin)
      assert admit(2) == :function_surface_verified
    after
      q("DROP TABLE public.review_type_dependency")
    end

    assert baseline() == before
    down!()
    assert baseline() == before

    persist("failed-down-atomicity", %{
      restored_addition: initial,
      migration_version_retained: true
    })
  end

  test "disconnect at each of twelve precommit prefixes rolls back all temporary ownership and grants",
       %{baseline: before} do
    up!()
    initial = addition()
    statements = plan()
    assert length(statements) == 13

    observations =
      for prefix <- 1..12 do
        conn = F.connection!("browser_admin")
        [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
        for statement <- Enum.take(statements, prefix), do: Postgrex.query!(conn, statement, [])
        GenServer.stop(conn)
        await_backend_exit(pid)
        assert addition() == initial
        inert!()
        assert baseline() == before
        %{prefix: prefix, backend_pid: pid, disconnected: true, restored: true}
      end

    persist("disconnect-prefixes", observations)
  end

  test "finish-time ACL denial aborts even after execution and type grants were issued", %{
    baseline: before
  } do
    up!()
    initial = addition()
    conn = F.connection!("browser_admin")

    try do
      for statement <- Enum.take(plan(), 11), do: Postgrex.query!(conn, statement, [])
      Postgrex.query!(conn, "GRANT EXECUTE ON FUNCTION #{@helper} TO review_neighbor", [])
      assert error_code(Postgrex.query(conn, Enum.at(plan(), 11), [])) == :insufficient_privilege
      assert error_code(Postgrex.query(conn, "SELECT 1", [])) == :in_failed_sql_transaction
      Postgrex.query!(conn, "ROLLBACK", [])
    after
      GenServer.stop(conn)
    end

    assert addition() == initial
    inert!()
    assert baseline() == before
    persist("finish-denial", %{aborted_before_commit: true, baseline_and_addition_restored: true})
  end

  test "actual runtime logins cannot provision acquire owner roles or drop helper or type", %{
    baseline: before
  } do
    up!()
    initial = addition()

    for login <- ["browser_lifecycle", "browser_ordinary"] do
      conn = F.connection!(login)

      try do
        for statement <- Enum.take(plan(), 5), do: Postgrex.query!(conn, statement, [])
        assert error_code(Postgrex.query(conn, Enum.at(plan(), 5), [])) == :insufficient_privilege
        Postgrex.query!(conn, "ROLLBACK", [])

        for role <- ["browser_writer", "browser_schema_owner"] do
          assert error_code(Postgrex.query(conn, "SET ROLE " <> role, [])) ==
                   :insufficient_privilege
        end

        assert error_code(invalid_prepare(conn)) == :insufficient_privilege
      after
        GenServer.stop(conn)
      end
    end

    assert addition() == initial
    upgrade!()
    upgraded = addition()

    for login <- ["browser_lifecycle", "browser_ordinary"] do
      conn = F.connection!(login)

      try do
        expected =
          if login == "browser_lifecycle", do: :raise_exception, else: :insufficient_privilege

        assert error_code(invalid_prepare(conn)) == expected

        for statement <- ["DROP FUNCTION #{@helper}", "DROP TYPE #{@type_name}"] do
          Postgrex.query!(conn, "BEGIN", [])
          assert error_code(Postgrex.query(conn, statement, [])) == :insufficient_privilege
          Postgrex.query!(conn, "ROLLBACK", [])
        end
      after
        GenServer.stop(conn)
      end
    end

    assert addition() == upgraded
    assert baseline() == before

    persist("runtime-authority", %{
      logins: ["browser_lifecycle", "browser_ordinary"],
      provisioning_denied: true,
      set_role_denied: true,
      drops_denied: true,
      lifecycle_execution_only_after_upgrade: true
    })
  end

  test "existing restricted schema owner can drop upgraded addition through database schema authority",
       %{baseline: before} do
    up!()
    upgrade!()

    assert [["browser_writer", "browser_schema_owner"]] =
             q(
               "SELECT p.proowner::regrole::text,t.typowner::regrole::text FROM pg_proc p,pg_type t WHERE p.oid=$1::text::regprocedure AND t.oid=$2::text::regtype",
               [@helper, @type_name]
             ).rows

    {:ok, authority} =
      Owner.transaction(fn ->
        Ecto.Adapters.SQL.query!(
          Owner,
          "SELECT current_user::text,session_user::text,(SELECT datdba=current_user::regrole FROM pg_database WHERE datname=current_database()),has_schema_privilege(current_user,'public','CREATE')",
          [],
          log: false
        ).rows
      end)

    assert [["browser_schema_owner", "browser_admin", true, true]] = authority
    down!(Owner)
    absent!()
    assert baseline() == before
    assert admit(1) == :function_surface_verified

    persist("schema-owner-authority", %{
      actual: authority,
      post_transfer_down: true,
      new_membership_or_grant: false
    })
  end

  test "new role memberships deny preflight atomically and removal permits the same upgrade", %{
    baseline: before
  } do
    up!()

    for sql <- [
          "GRANT review_neighbor TO browser_lifecycle",
          "GRANT browser_writer TO review_neighbor"
        ] do
      q(sql)
      initial = addition()

      try do
        rejected_plan!(:insufficient_privilege)
        assert addition() == initial
        inert!()
      after
        q(String.replace(sql, "GRANT", "REVOKE") |> String.replace(" TO ", " FROM "))
      end
    end

    assert baseline() == before
    upgrade!()
    assert admit(2) == :function_surface_verified

    persist("role-edge-denial", %{
      both_directions_denied: true,
      same_plan_succeeds_after_removal: true
    })
  end

  test "grant-option ACL adversity denies before modification and is preserved on error", %{
    baseline: before
  } do
    up!()

    for sql <- [
          "GRANT EXECUTE ON FUNCTION #{@helper} TO review_neighbor WITH GRANT OPTION",
          "GRANT USAGE ON TYPE #{@type_name} TO review_neighbor WITH GRANT OPTION"
        ] do
      q(sql)
      initial = addition()

      try do
        rejected_plan!(:insufficient_privilege)
        assert addition() == initial
        assert baseline() == before
      after
        q(
          sql
          |> String.replace("GRANT ", "REVOKE ", global: false)
          |> String.replace(" TO ", " FROM ")
          |> String.replace(" WITH GRANT OPTION", "")
        )
      end
    end

    inert!()
    upgrade!()
    assert admit(2) == :function_surface_verified

    persist("grant-option-denial", %{function_and_type_denied: true, existing_acl_preserved: true})
  end

  test "repeating initial provisioning over V2 fails closed without damaging the accepted surface",
       %{baseline: before} do
    up!()
    upgrade!()
    initial = addition()
    rejected_plan!(:insufficient_privilege)
    assert addition() == initial
    assert admit(2) == :function_surface_verified
    assert baseline() == before
    persist("repeat-denial", %{repeat_denied: true, accepted_v2_unchanged: true})
  end

  defp q(sql, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, sql, params, log: false)
  defp path, do: Path.expand("hosted/priv/repo/migrations")

  defp unload do
    :code.purge(@migration)
    :code.delete(@migration)
  end

  defp up! do
    unload()
    assert [@version] == Ecto.Migrator.run(Owner, path(), :up, all: true, log: false)
    assert [] == Ecto.Migrator.run(Owner, path(), :up, all: true, log: false)
  end

  defp down!(repo \\ Admin) do
    unload()
    assert [@version] == Ecto.Migrator.run(repo, path(), :down, step: 1, log: false)
  end

  defp plan,
    do:
      ActivationPreparationSchema.provisioning_statements(
        "browser_writer",
        "browser_lifecycle",
        "browser_schema_owner"
      )

  defp upgrade! do
    conn = F.connection!("browser_admin")

    try do
      [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
      for sql <- plan(), do: Postgrex.query!(conn, sql, [])
      assert [[^pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
    after
      GenServer.stop(conn)
    end
  end

  defp rejected_plan!(expected) do
    conn = F.connection!("browser_admin")

    try do
      code =
        Enum.reduce_while(plan(), nil, fn sql, _ ->
          case Postgrex.query(conn, sql, []) do
            {:ok, _} -> {:cont, nil}
            {:error, error} -> {:halt, error.postgres.code}
          end
        end)

      assert code == expected
      Postgrex.query!(conn, "ROLLBACK", [])
    after
      GenServer.stop(conn)
    end
  end

  defp admit(version) do
    {:ok, result} =
      Lifecycle.transaction(
        fn ->
          deadline = System.monotonic_time(:millisecond) + 4_500

          if version == :legacy,
            do: Catalog.check_function_surface!(Lifecycle, @roles, deadline),
            else: Catalog.check_function_surface!(Lifecycle, @roles, deadline, version)
        end,
        timeout: 5_000,
        queue: false
      )

    result
  end

  defp deny(version), do: assert_raise(Catalog.Unavailable, fn -> admit(version) end)

  defp absent!,
    do:
      assert(
        [[nil, 0]] ==
          q(
            "SELECT to_regtype('#{@type_name}')::text,(SELECT count(*) FROM pg_proc WHERE proname='mixer_browser_prepare_activation')"
          ).rows
      )

  defp inert! do
    assert [
             [
               "browser_schema_owner",
               "browser_schema_owner",
               false,
               false,
               false,
               false,
               false,
               false
             ]
           ] =
             q(
               "SELECT p.proowner::regrole::text,t.typowner::regrole::text,has_function_privilege('browser_lifecycle',p.oid,'EXECUTE'),has_function_privilege('browser_ordinary',p.oid,'EXECUTE'),has_type_privilege('browser_lifecycle',t.oid,'USAGE'),has_type_privilege('browser_ordinary',t.oid,'USAGE'),has_schema_privilege('browser_writer','public','CREATE'),has_schema_privilege('browser_lifecycle','public','CREATE') FROM pg_proc p,pg_type t WHERE p.oid=$1::text::regprocedure AND t.oid=$2::text::regtype",
               [@helper, @type_name]
             ).rows
  end

  defp addition do
    q(
      "SELECT to_jsonb(p) FROM pg_proc p WHERE oid=$1::text::regprocedure UNION ALL SELECT to_jsonb(t) FROM pg_type t WHERE oid=$2::text::regtype",
      [@helper, @type_name]
    ).rows
  end

  defp baseline do
    queries = %{
      "functions" =>
        "SELECT to_jsonb(p) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname<>'mixer_browser_prepare_activation' ORDER BY p.oid",
      "relations" =>
        "SELECT to_jsonb(c) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname NOT IN ('mixer_browser_access_evidence','schema_migrations','schema_migrations_pkey') ORDER BY c.oid",
      "types" =>
        "SELECT to_jsonb(t) FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public' AND t.typname NOT IN ('mixer_browser_access_evidence','_mixer_browser_access_evidence','schema_migrations','_schema_migrations') ORDER BY t.oid",
      "policies" => "SELECT to_jsonb(p) FROM pg_policy p ORDER BY oid",
      "constraints" =>
        "SELECT to_jsonb(c) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' ORDER BY c.oid",
      "defaults" => "SELECT to_jsonb(a) FROM pg_attrdef a ORDER BY oid",
      "triggers" => "SELECT to_jsonb(t) FROM pg_trigger t ORDER BY oid",
      "role_authority" =>
        "SELECT oid::bigint,rolname::text,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls FROM pg_roles ORDER BY oid",
      "memberships" => "SELECT to_jsonb(m) FROM pg_auth_members m ORDER BY roleid,member",
      "namespace_authority" =>
        "SELECT oid::bigint,nspname::text,nspowner::bigint,nspacl::text FROM pg_namespace ORDER BY oid"
    }

    result = Map.new(queries, fn {label, sql} -> {label, q(sql).rows} end)

    tables =
      q(
        "SELECT c.relname::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname<>'schema_migrations' ORDER BY c.relname"
      ).rows

    data =
      Map.new(tables, fn [name] ->
        {name, q("SELECT to_jsonb(t) FROM public.\"#{name}\" t ORDER BY to_jsonb(t)::text").rows}
      end)

    Map.put(result, "data", data)
  end

  defp error_code({:error, error}), do: error.postgres.code
  defp error_code(other), do: flunk("expected PostgreSQL error, got #{inspect(other)}")

  defp invalid_prepare(conn),
    do:
      Postgrex.query(
        conn,
        "SELECT public.mixer_browser_prepare_activation(NULL,NULL,NULL,NULL,NULL,NULL::#{@type_name})",
        []
      )

  defp prepare(conn, browser, attempt, claim) do
    identity = F.identity()

    Postgrex.query(
      conn,
      "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,ROW($6,$7,$8,$9,$10,$11,$12,$13,$14)::#{@type_name})",
      [
        browser.cookie,
        attempt.state,
        browser.config,
        claim,
        browser.revision,
        identity.profile,
        1,
        identity.issuer,
        identity.subject,
        identity.client,
        identity.jti,
        identity.iat,
        identity.exp,
        identity.scopes
      ]
    )
  end

  defp await_backend_exit(pid) do
    assert Enum.reduce_while(1..50, false, fn _, _ ->
             if q("SELECT count(*) FROM pg_stat_activity WHERE pid=$1", [pid]).rows == [[0]],
               do: {:halt, true},
               else:
                 (
                   Process.sleep(10)
                   {:cont, false}
                 )
           end)
  end

  defp persist(label, value),
    do:
      File.write!(
        Path.join(System.fetch_env!("MIXER_MIGRATION_REVIEW_OUTPUT"), label <> ".json"),
        Jason.encode!(value, pretty: true)
      )
end
