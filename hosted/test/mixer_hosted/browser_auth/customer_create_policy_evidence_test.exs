Code.require_file("customer_create_build_atomic_replay_pg_join_test.exs", __DIR__)

defmodule MixerHosted.CustomerCreatePolicyEvidenceTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.CustomerBuilds.{CreateRepo, CreateSchema}

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

    on_exit(fn ->
      assert System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT") == parent

      File.write!(
        Path.join(ev, "parent-restored.json"),
        Jason.encode!(%{
          parent: parent,
          actual: System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
        })
      )
    end)

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
    start_supervised!({CreateRepo, create})
    c
  end

  test "exact policy admission refuses catalog drift and restores", _c do
    rows =
      F.q!(Admin, """
      SELECT c.relname::text,p.polname::text,p.polcmd::text,p.polpermissive,
        ARRAY(SELECT r.rolname::text FROM pg_roles r WHERE r.oid=ANY(p.polroles) ORDER BY r.rolname),
        pg_get_expr(p.polqual,p.polrelid,false),pg_get_expr(p.polwithcheck,p.polrelid,false)
      FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relname IN ('mixer_builds','oban_jobs','mixer_customer_build_inputs')
      ORDER BY c.relname,p.polname
      """).rows

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "policy-rows.json"),
      Jason.encode!(rows)
    )

    assert {:ok, :ok} = CreateRepo.transaction(fn -> CreateSchema.admit!(CreateRepo) end)
    IO.puts("R2134_PASS baseline_admission")
    original = Enum.find(rows, fn [_, name | _] -> name == "build_create_lock" end) |> Enum.at(5)

    for {label, change, restore} <- [
          {"false_to_true", "ALTER POLICY build_create_lock ON mixer_builds WITH CHECK(true)",
           "ALTER POLICY build_create_lock ON mixer_builds WITH CHECK(false)"},
          {"using", "ALTER POLICY build_create_lock ON mixer_builds USING(true)",
           "ALTER POLICY build_create_lock ON mixer_builds USING(" <> original <> ")"},
          {"role", "ALTER POLICY build_create_lock ON mixer_builds TO browser_ordinary",
           "ALTER POLICY build_create_lock ON mixer_builds TO mixer_build_create"},
          {"missing", "DROP POLICY build_create_lock ON mixer_builds",
           "CREATE POLICY build_create_lock ON mixer_builds FOR UPDATE TO mixer_build_create USING(" <>
             original <> ") WITH CHECK(false)"},
          {"permissiveness",
           "DROP POLICY build_create_lock ON mixer_builds; CREATE POLICY build_create_lock ON mixer_builds AS RESTRICTIVE FOR UPDATE TO mixer_build_create USING(" <>
             original <> ") WITH CHECK(false)",
           "DROP POLICY build_create_lock ON mixer_builds; CREATE POLICY build_create_lock ON mixer_builds FOR UPDATE TO mixer_build_create USING(" <>
             original <> ") WITH CHECK(false)"},
          {"extra", "CREATE POLICY r2134_extra ON mixer_builds TO mixer_build_create USING(true)",
           "DROP POLICY r2134_extra ON mixer_builds"},
          {"command",
           "DROP POLICY build_create_lock ON mixer_builds; CREATE POLICY build_create_lock ON mixer_builds FOR ALL TO mixer_build_create USING(" <>
             original <> ") WITH CHECK(false)",
           "DROP POLICY build_create_lock ON mixer_builds; CREATE POLICY build_create_lock ON mixer_builds FOR UPDATE TO mixer_build_create USING(" <>
             original <> ") WITH CHECK(false)"}
        ] do
      Enum.each(String.split(change, "; "), &F.q!(Admin, &1))

      assert {:error, :authorization_unavailable} =
               CreateRepo.transaction(fn -> CreateSchema.admit!(CreateRepo) end)

      Enum.each(String.split(restore, "; "), &F.q!(Admin, &1))
      assert {:ok, :ok} = CreateRepo.transaction(fn -> CreateSchema.admit!(CreateRepo) end)
      IO.puts("R2134_PASS " <> label <> "_reject_restore")
    end
  end

  test "failed INSERT and nil rows preserve telemetry attachment without SQL" do
    event = CreateRepo.config()[:telemetry_prefix] ++ [:query]
    id = "r2134-handler"
    events = Enum.uniq([event, Admin.config()[:telemetry_prefix] ++ [:query]])

    :ok =
      :telemetry.attach_many(
        id,
        events,
        &MixerHosted.CustomerCreateBuildAtomicReplayPGJoinTest.observe/4,
        self()
      )

    on_exit(fn -> :telemetry.detach(id) end)
    audit_id = "r2224-query-audit"

    :ok =
      :telemetry.attach_many(
        audit_id,
        events,
        fn _, _, m, pid ->
          if Map.get(m, :repo) in [CreateRepo, Admin],
            do: send(pid, {:r2224_actual_query, Map.get(m, :query)})
        end,
        self()
      )

    on_exit(fn -> :telemetry.detach(audit_id) end)

    for m <- [
          %{},
          %{query: nil, result: nil},
          %{query: "BEGIN", result: {:ok, %{rows: nil}}},
          %{query: "SELECT 1", result: {:ok, %{rows: [[1]]}}},
          %{query: nil, source: "oban_jobs", result: {:error, :owned_failure}}
        ] do
      :ok = :telemetry.execute(event, %{}, m)
      assert Enum.any?(:telemetry.list_handlers(event), &(&1.id == id))
    end

    refute_receive {:job_insert_failed, _, _}, 0
    refute_receive {:r2224_actual_query, _}, 0
    # A nil metadata.repo failure remains safe: it must not query a reported repo.
    :ok =
      :telemetry.execute(event, %{}, %{
        query: ~s|INSERT INTO "public"."oban_jobs" ("id") VALUES ($1)|,
        result: {:error, :owned_failure}
      })

    assert_receive {:job_insert_failed, _, :unknown}
    refute_receive {:r2224_actual_query, _}, 0
    assert Enum.any?(:telemetry.list_handlers(event), &(&1.id == id))
    # The unadmitted create role is correctly refused by RLS before constraints.
    assert {:error, :rollback} =
             CreateRepo.transaction(fn ->
               assert {:error,
                       %Postgrex.Error{
                         postgres: %{code: :insufficient_privilege, pg_code: "42501"}
                       }} =
                        Ecto.Adapters.SQL.query(
                          CreateRepo,
                          ~s|INSERT INTO "public"."oban_jobs" (id) VALUES (0)|,
                          []
                        )

               assert_receive {:job_insert_failed, _, :insufficient_privilege}
               :failed_insert_observed
             end)

    # The existing admin fixture reaches the actual not-null constraint unchanged.
    assert {:error, :rollback} =
             Admin.transaction(fn ->
               assert {:error,
                       %Postgrex.Error{postgres: %{code: :not_null_violation, pg_code: "23502"}}} =
                        Ecto.Adapters.SQL.query(
                          Admin,
                          ~s|INSERT INTO "public"."oban_jobs" (id) VALUES (0)|,
                          []
                        )

               assert_receive {:job_insert_failed, _, :not_null_violation}
               :failed_insert_observed
             end)

    refute_receive {:job_insert_witness, _}, 0
    queries = observed_queries([])

    refute Enum.any?(
             queries,
             &String.starts_with?(String.upcase(IO.iodata_to_binary(&1)), "SELECT")
           )

    assert Enum.count(queries, &String.starts_with?(IO.iodata_to_binary(&1), "INSERT INTO")) == 2

    IO.puts(
      "R2224_OBSERVER_PASS nil_repo_unknown_no_SQL actual_CreateRepo_42501 actual_Admin_23502 both_rollback no_observer_SQL"
    )

    assert Enum.any?(:telemetry.list_handlers(event), &(&1.id == id))
    IO.puts("R2134_PASS failed_insert_nil_unrelated_handler_alive")
  end

  defp observed_queries(acc) do
    receive do
      {:r2224_actual_query, q} -> observed_queries([q | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end
end
