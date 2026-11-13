Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.ActualCreatorEffectiveCreatePrivilegesPGJoinTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.BrowserAuth.{LifecycleRepo, RelationCatalog, RelationManifest}

  setup_all do
    conn = F.connection!("browser_admin", "postgres")

    case Postgrex.query!(
           conn,
           "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname='mixer_customer_build_catalog_definer_v1'",
           []
         ).rows do
      [] ->
        Postgrex.query!(
          conn,
          "CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT",
          []
        )

      [[false, false, false, false, false, false, false]] ->
        :ok
    end

    GenServer.stop(conn)
    parent = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
    ev = Path.join(parent, "attempt-" <> Base.encode16(:crypto.strong_rand_bytes(6)))
    File.mkdir!(ev)
    System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", ev)
    on_exit(fn -> System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", parent) end)
    c = Fixture.prepare!(true)

    case F.q!(
           Admin,
           "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname='mixer_build_create'"
         ).rows do
      [] ->
        F.q!(
          Admin,
          "CREATE ROLE mixer_build_create LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION"
        )

      [[true, false, false, false, false, false, false]] ->
        :ok
    end

    F.q!(Admin, "GRANT USAGE ON SCHEMA public TO mixer_build_create")

    F.q!(
      Admin,
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

    for sql <- MixerHosted.CustomerBuilds.CreateSchema.statements(), do: F.q!(Migration, sql)
    for sql <- MixerHosted.BrowserAuth.ActiveCreateSchema.statements(), do: F.q!(Migration, sql)
    F.q!(Admin, "GRANT CREATE ON SCHEMA public TO browser_writer")

    F.q!(
      Admin,
      "ALTER FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) OWNER TO browser_writer"
    )

    F.q!(Admin, "REVOKE CREATE ON SCHEMA public FROM browser_writer")

    F.q!(
      Admin,
      "GRANT EXECUTE ON FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) TO mixer_build_create"
    )

    F.q!(Admin, "UPDATE mixer_authz_memberships SET role='developer' WHERE id='member-a'")

    for {id, ref} <- [{"input-a", "immutable-input-a"}, {"input-b", "immutable-input-b"}] do
      F.q!(
        Admin,
        "INSERT INTO mixer_customer_build_inputs VALUES('org-a','project-a','fieldlog','ios',$1,'revision',$2,$3,$4,$5,2,10000,0)",
        [id, ref, String.duplicate("a", 64), String.duplicate("b", 64), String.duplicate("c", 64)]
      )
    end

    create =
      c.hosted.repo |> Keyword.put(:username, "mixer_build_create") |> Keyword.put(:pool_size, 4)

    c = Map.put(c, :hosted, %{c.hosted | create_repo: create})
    Fixture.start!(c)
  end

  defp check(c) do
    try do
      LifecycleRepo.transaction(
        fn ->
          F.q!(LifecycleRepo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

          F.q!(
            LifecycleRepo,
            "SELECT set_config('search_path','pg_catalog',true),set_config('jit','off',true),set_config('statement_timeout','5s',true),set_config('lock_timeout','500ms',true),set_config('idle_in_transaction_session_timeout','5s',true),set_config('bytea_output','hex',true)"
          )

          assert [["browser_lifecycle", "browser_lifecycle", "pg_catalog", "5s", "500ms"]] ==
                   F.q!(
                     LifecycleRepo,
                     "SELECT current_user::text,session_user::text,current_setting('search_path'),current_setting('statement_timeout'),current_setting('lock_timeout')"
                   ).rows

          RelationCatalog.check_create_catalog_surface!(
            LifecycleRepo,
            c.runtime.expected_roles,
            System.monotonic_time(:millisecond) + 5000
          )
        end,
        timeout: 5000,
        queue: false
      )
    rescue
      e in RelationCatalog.Unavailable -> {:refused, e.__struct__}
    end
  end

  defp sql(s), do: F.q!(Admin, s)

  defp snapshot do
    role =
      sql(
        "SELECT oid::bigint,rolcanlogin,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolinherit,EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.roleid=r.oid OR m.member=r.oid),pg_has_role('browser_ordinary',r.oid,'MEMBER') FROM pg_roles r WHERE rolname='mixer_build_create'"
      ).rows

    acl =
      F.q!(
        Admin,
        """
          SELECT * FROM (
            SELECT n.nspname::text||'.'||c.relname::text AS rel,''::text AS col,
              a.grantee::bigint,a.grantor::bigint,a.privilege_type::text,a.is_grantable
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL aclexplode(COALESCE(c.relacl,acldefault('r',c.relowner))) a
            WHERE n.nspname='public' AND n.nspname::text||'.'||c.relname::text=ANY($1::text[])
            UNION ALL
            SELECT n.nspname::text||'.'||c.relname::text,t.attname::text,
              a.grantee::bigint,a.grantor::bigint,a.privilege_type::text,a.is_grantable
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_attribute t ON t.attrelid=c.oid
            CROSS JOIN LATERAL aclexplode(t.attacl) a
            WHERE t.attnum>0 AND n.nspname='public' AND n.nspname::text||'.'||c.relname::text=ANY($1::text[])
          ) x ORDER BY 1,2,3,4,5,6
        """,
        [RelationManifest.names()]
      ).rows

    %{role: role, acl: acl}
  end

  defp effective(oid, object) do
    case object do
      :database ->
        F.q!(
          Admin,
          "SELECT pg_catalog.has_database_privilege($1::oid,oid,'CREATE') FROM pg_catalog.pg_database WHERE datname=current_database()",
          [oid]
        ).rows

      name ->
        F.q!(
          Admin,
          "SELECT pg_catalog.has_schema_privilege($1::oid,oid,'CREATE') FROM pg_catalog.pg_namespace WHERE nspname=$2",
          [oid, name]
        ).rows
    end
  end

  @tag :actual_creator_effective_create_privileges_pg_join
  test "actual_creator_effective_create_privileges_pg_join", c do
    assert MixerHosted.BrowserAuth.RuntimeOwner.status().phase == :storage_ready
    assert check(c) == {:ok, :relation_surface_verified}
    baseline = snapshot()
    [[oid, true, false, false, false, false, false, false, false, false]] = baseline.role
    assert length(baseline.acl) == 143
    sql("CREATE SCHEMA r2166_application AUTHORIZATION browser_admin")
    [[database]] = sql("SELECT quote_ident(current_database())").rows

    mutations = [
      {"creator_public_schema", "GRANT CREATE ON SCHEMA public TO mixer_build_create",
       "REVOKE CREATE ON SCHEMA public FROM mixer_build_create", "public"},
      {"creator_application_schema",
       "GRANT CREATE ON SCHEMA r2166_application TO mixer_build_create",
       "REVOKE CREATE ON SCHEMA r2166_application FROM mixer_build_create", "r2166_application"},
      {"creator_database", "GRANT CREATE ON DATABASE " <> database <> " TO mixer_build_create",
       "REVOKE CREATE ON DATABASE " <> database <> " FROM mixer_build_create", :database},
      {"PUBLIC_public_schema", "GRANT CREATE ON SCHEMA public TO PUBLIC",
       "REVOKE CREATE ON SCHEMA public FROM PUBLIC", "public"},
      {"PUBLIC_database", "GRANT CREATE ON DATABASE " <> database <> " TO PUBLIC",
       "REVOKE CREATE ON DATABASE " <> database <> " FROM PUBLIC", :database},
      {"creator_application_ownership",
       "ALTER SCHEMA r2166_application OWNER TO mixer_build_create",
       "ALTER SCHEMA r2166_application OWNER TO browser_admin", "r2166_application"},
      {"creator_pg_catalog", "GRANT CREATE ON SCHEMA pg_catalog TO mixer_build_create",
       "REVOKE CREATE ON SCHEMA pg_catalog FROM mixer_build_create", "pg_catalog"},
      {"creator_information_schema",
       "GRANT CREATE ON SCHEMA information_schema TO mixer_build_create",
       "REVOKE CREATE ON SCHEMA information_schema FROM mixer_build_create",
       "information_schema"},
      {"PUBLIC_application_schema", "GRANT CREATE ON SCHEMA r2166_application TO PUBLIC",
       "REVOKE CREATE ON SCHEMA r2166_application FROM PUBLIC", "r2166_application"}
    ]

    assert snapshot() == baseline

    for {name, bad, restore, object} <- mutations do
      assert effective(oid, object) == [[false]], name <> " baseline effective"
      sql(bad)

      try do
        assert snapshot() == baseline, name <> " original guard premise unchanged"
        assert effective(oid, object) == [[true]], name <> " effective privilege witness"
        assert check(c) == {:refused, RelationCatalog.Unavailable}, name <> " admission"
      after
        sql(restore)
      end

      assert effective(oid, object) == [[false]], name <> " restored effective"
      assert snapshot() == baseline, name <> " restored role/ACL"
      assert check(c) == {:ok, :relation_surface_verified}, name <> " restored admission"

      IO.puts(
        "R2166_PASS " <> name <> "_effective_true_unchanged_143_flags_membership_reject_restore"
      )
    end

    # Execute the exact corrected standalone source pair, including both commands.
    source = File.read!(Path.join(__DIR__, "actual_create_relation_profile_pg_join_test.exs"))

    pair =
      "{\"column_SELECT\",\"GRANT SELECT(id) ON public.mixer_authz_profiles TO mixer_build_create\",\"REVOKE SELECT(id) ON public.mixer_authz_profiles FROM mixer_build_create\"}"

    strip_positions = fn ast ->
      Macro.prewalk(ast, fn
        {form, meta, args} when is_list(meta) ->
          {form, Keyword.drop(meta, [:line, :column]), args}

        node ->
          node
      end)
    end

    pair_ast = strip_positions.(Code.string_to_quoted!(pair))

    {_, pairs} =
      Macro.prewalk(Code.string_to_quoted!(source), [], fn
        {:{}, _, ["column_SELECT", grant, revoke]} = node, acc
        when is_binary(grant) and is_binary(revoke) ->
          {node, acc ++ [strip_positions.(node)]}

        node, acc ->
          {node, acc}
      end)

    assert pairs == [pair_ast]
    {"column_SELECT", grant, revoke} = Code.eval_string(pair) |> elem(0)
    sql(grant)

    try do
      assert snapshot().role == baseline.role
      assert length(snapshot().acl) == 144
      assert check(c) == {:refused, RelationCatalog.Unavailable}
    after
      sql(revoke)
    end

    assert snapshot() == baseline
    assert check(c) == {:ok, :relation_surface_verified}
    IO.puts("R2166_PASS corrected_standalone_column_SELECT_id_reject_restore")
    sql("DROP SCHEMA r2166_application")

    File.write!(
      Path.join(
        System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
        "effective-privileges.json"
      ),
      Jason.encode!(%{
        name: "actual_creator_effective_create_privileges_pg_join",
        baseline: baseline,
        privilege_reject_recoveries: length(mutations),
        column_reject_recoveries: 1,
        strict_policy: true,
        startup_storage_ready: true,
        HTTP_atomicity: false
      })
    )
  end
end
