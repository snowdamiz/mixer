Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.ActualCreateRelationProfilePGJoinTest do
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
    Fixture.configure!(c, :fixture)
    start_supervised!({LifecycleRepo, c.runtime.lifecycle_repo})

    assert [["browser_lifecycle", "browser_lifecycle"]] ==
             Ecto.Adapters.SQL.query!(
               LifecycleRepo,
               "SELECT current_user::text,session_user::text",
               [],
               timeout: 5000,
               queue: true,
               log: false
             ).rows

    c
  end

  defp install_create!(c) do
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

    c
  end

  defp note(name), do: IO.puts("R2154_CONTROL_PASS " <> name)
  defp query(sql), do: F.q!(Admin, sql)

  defp check(c, profile) do
    try do
      LifecycleRepo.transaction(
        fn ->
          F.q!(LifecycleRepo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

          F.q!(
            LifecycleRepo,
            "SELECT set_config('search_path','pg_catalog',true),set_config('jit','off',true),set_config('statement_timeout','5s',true),set_config('lock_timeout','500ms',true),set_config('idle_in_transaction_session_timeout','5s',true),set_config('bytea_output','hex',true)"
          )

          deadline = System.monotonic_time(:millisecond) + 5000

          case profile do
            :read ->
              RelationCatalog.check_build_catalog_surface!(
                LifecycleRepo,
                c.runtime.expected_roles,
                deadline
              )

            :create ->
              RelationCatalog.check_create_catalog_surface!(
                LifecycleRepo,
                c.runtime.expected_roles,
                deadline
              )
          end
        end,
        timeout: 5000,
        queue: false
      )
    rescue
      e in RelationCatalog.Unavailable -> {:refused, e.__struct__}
    end
  end

  defp acl_count do
    F.q!(
      Admin,
      """
      SELECT count(*) FROM (
        SELECT a.grantee FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN LATERAL aclexplode(COALESCE(c.relacl,acldefault('r',c.relowner))) a
        WHERE n.nspname='public' AND n.nspname::text||'.'||c.relname::text=ANY($1::text[])
        UNION ALL
        SELECT a.grantee FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute t ON t.attrelid=c.oid
        CROSS JOIN LATERAL aclexplode(t.attacl) a
        WHERE t.attnum>0 AND n.nspname='public' AND n.nspname::text||'.'||c.relname::text=ANY($1::text[])
      ) x
      """,
      [RelationManifest.names()]
    ).rows
    |> hd()
    |> hd()
  end

  @tag :actual_create_relation_profile_pg_join
  test "actual_create_relation_profile_pg_join", c do
    assert check(c, :read) == {:ok, :relation_surface_verified}
    assert acl_count() == 138
    note("legacy_read_138_before_create_DDL")
    c = install_create!(c)
    assert acl_count() == 143
    assert check(c, :create) == {:ok, :relation_surface_verified}
    note("create_v4_exact_143")
    assert check(c, :read) == {:refused, RelationCatalog.Unavailable}
    note("legacy_read_refuses_creator_grants")

    role_rows =
      query(
        "SELECT oid::bigint,rolname::text,rolcanlogin,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolinherit,EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.roleid=r.oid OR m.member=r.oid),pg_has_role('browser_ordinary',r.oid,'MEMBER') FROM pg_roles r WHERE rolname='mixer_build_create'"
      ).rows

    [[oid, "mixer_build_create", true, false, false, false, false, false, false, false, false]] =
      role_rows

    assert oid > 0

    query(
      "CREATE ROLE relation_profile_peer NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT"
    )

    attrs = [
      {"login", "NOLOGIN", "LOGIN"},
      {"super", "SUPERUSER", "NOSUPERUSER"},
      {"bypass", "BYPASSRLS", "NOBYPASSRLS"},
      {"createdb", "CREATEDB", "NOCREATEDB"},
      {"createrole", "CREATEROLE", "NOCREATEROLE"},
      {"replication", "REPLICATION", "NOREPLICATION"},
      {"inherit", "INHERIT", "NOINHERIT"}
    ]

    mutations =
      Enum.map(attrs, fn {name, bad, good} ->
        {"role_" <> name, "ALTER ROLE mixer_build_create " <> bad,
         "ALTER ROLE mixer_build_create " <> good}
      end) ++
        [
          {"inbound_membership", "GRANT mixer_build_create TO relation_profile_peer",
           "REVOKE mixer_build_create FROM relation_profile_peer"},
          {"outbound_membership", "GRANT relation_profile_peer TO mixer_build_create",
           "REVOKE relation_profile_peer FROM mixer_build_create"},
          {"ordinary_reachability", "GRANT mixer_build_create TO browser_ordinary",
           "REVOKE mixer_build_create FROM browser_ordinary"},
          {"extra_UPDATE", "GRANT UPDATE ON public.mixer_authz_profiles TO mixer_build_create",
           "REVOKE UPDATE ON public.mixer_authz_profiles FROM mixer_build_create"},
          {"grantable_SELECT",
           "GRANT SELECT ON public.mixer_authz_profiles TO mixer_build_create WITH GRANT OPTION",
           "REVOKE GRANT OPTION FOR SELECT ON public.mixer_authz_profiles FROM mixer_build_create"},
          {"wrong_table", "GRANT SELECT ON public.mixer_browser_sessions TO mixer_build_create",
           "REVOKE SELECT ON public.mixer_browser_sessions FROM mixer_build_create"},
          {"column_SELECT",
           "GRANT SELECT(id) ON public.mixer_authz_profiles TO mixer_build_create",
           "REVOKE SELECT(id) ON public.mixer_authz_profiles FROM mixer_build_create"},
          {"missing_SELECT",
           "REVOKE SELECT ON public.mixer_authz_profiles FROM mixer_build_create",
           "GRANT SELECT ON public.mixer_authz_profiles TO mixer_build_create"}
        ]

    for {name, bad, restore} <- mutations do
      query(bad)

      try do
        assert check(c, :create) == {:refused, RelationCatalog.Unavailable}, name
      after
        query(restore)
      end

      assert check(c, :create) == {:ok, :relation_surface_verified}, name <> " recovery"
      note(name <> "_reject_and_recover")
    end

    query("DROP ROLE relation_profile_peer")
    assert acl_count() == 143

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "relation-profile.json"),
      Jason.encode!(%{
        name: "actual_create_relation_profile_pg_join",
        legacy_acl_rows: 138,
        create_acl_rows: 143,
        role_rows: role_rows,
        rejections: length(mutations),
        recoveries: length(mutations),
        old_read_preserved: true,
        full_application_started: false,
        Store_admit_called: false,
        runtime_storage_ready_claimed: false
      })
    )

    note("actual_create_relation_profile_pg_join")
  end
end
