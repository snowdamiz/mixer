defmodule MixerHosted.Authorization.PostgresIndependentReviewTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Authorization.{Policy, PostgresRepository}
  alias MixerHosted.Authorization.PostgresFixture, as: F
  alias MixerHosted.Authorization.PostgresFixture.{Admin, Migration, Runtime}

  @context ~w(profile_id profile_version issuer subject client_id identity_class credential_ref principal_id family_id organization_id project_id application_id environment_id)

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_AUTHZ_TEST_PORT")),
      database: "mixer_authz_test",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "authz_fixture_admin", pool_size: 6]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "authz_fixture_admin",
           pool_size: 1,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE mixer_authz_owner", []) end
         ]}
    )

    # One connection gives a deterministic pooled-connection reuse assertion.
    start_supervised!({Runtime, settings ++ [username: "mixer_authz_runtime", pool_size: 1]})

    assert Ecto.Migrator.up(
             Migration,
             20_261_025_000_003,
             MixerHosted.Repo.Migrations.AddCustomerAuthorization,
             log: false
           ) in [:ok, :already_up]

    for table <- F.tables(),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{table} TO mixer_authz_runtime")

    for {table, _} <- F.locks(),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO mixer_authz_runtime"
          )

    :ok
  end

  setup do
    F.seed!()
    :ok
  end

  test "catalog confirms exact fixed lock helper ownership ACL RLS and runtime SELECT-only grants" do
    rows =
      F.sql("""
      SELECT p.proname, l.lanname, p.prosecdef, p.pronargs,
        pg_catalog.format_type(p.prorettype,NULL), p.proconfig,
        r.rolcanlogin, r.rolsuper, r.rolbypassrls,
        pg_catalog.pg_get_functiondef(p.oid),
        NOT EXISTS (SELECT 1 FROM pg_catalog.aclexplode(p.proacl) a WHERE a.grantee=0),
        pg_catalog.has_function_privilege('mixer_authz_runtime',p.oid,'EXECUTE')
      FROM pg_catalog.pg_proc p
      JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
      JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
      JOIN pg_catalog.pg_language l ON l.oid=p.prolang
      WHERE n.nspname='public' AND p.proname LIKE 'mixer_authz_lock_%'
      ORDER BY p.proname
      """).rows

    assert length(rows) == 6

    for [
          name,
          language,
          definer,
          arity,
          result,
          config,
          login,
          superuser,
          bypass,
          source,
          no_public,
          runtime_execute
        ] <- rows do
      assert language == "plpgsql" and definer and arity == 0 and result == "boolean"
      assert config == ["search_path=pg_catalog"]
      refute login or superuser or bypass
      assert no_public and runtime_execute
      assert source =~ "FROM public.mixer_authz_"
      assert source =~ "FOR SHARE"
      refute source =~ "EXECUTE "
      refute source =~ "INSERT "
      refute source =~ "UPDATE "
      refute source =~ "DELETE "
      assert name in Enum.map(F.locks(), fn {table, _} -> "mixer_authz_lock_" <> table end)
    end

    for table <- F.tables() do
      assert [[true, true, true, false, false]] =
               F.sql(
                 """
                 SELECT c.relrowsecurity,c.relforcerowsecurity,
                   pg_catalog.has_table_privilege('mixer_authz_runtime',c.oid,'SELECT'),
                   pg_catalog.has_table_privilege('mixer_authz_runtime',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),
                   pg_catalog.has_any_column_privilege('mixer_authz_runtime',c.oid,'INSERT,UPDATE,REFERENCES')
                 FROM pg_catalog.pg_class c WHERE c.oid=$1::regclass
                 """,
                 ["public.mixer_authz_" <> table]
               ).rows
    end
  end

  test "every exact identity GUC mismatch hides binding principal memberships and resource ancestry" do
    for change <- [
          [profile_id: "missing"],
          [profile_version: "2"],
          [issuer: "https://wrong.example"],
          [subject: "missing"],
          [client_id: "wrong"],
          [identity_class: "service"],
          [principal_id: "other-person"]
        ] do
      assert {:ok, :ok} =
               Runtime.transaction(fn ->
                 F.grant_context!(Runtime, change)

                 for table <-
                       ~w(principals memberships organizations projects applications environments) do
                   assert [[0]] =
                            F.runtime_sql("SELECT count(*) FROM public.mixer_authz_#{table}").rows
                 end

                 :ok
               end)
    end
  end

  test "direct runtime DML truncate row locks and unscoped helper calls never escalate" do
    for statement <- [
          "INSERT INTO public.mixer_authz_organizations VALUES ('injected',true)",
          "DELETE FROM public.mixer_authz_memberships",
          "TRUNCATE public.mixer_authz_memberships",
          "UPDATE public.mixer_authz_principals SET active=true",
          "SELECT * FROM public.mixer_authz_profiles FOR UPDATE",
          "SELECT * FROM public.mixer_authz_profiles FOR SHARE",
          "SET ROLE mixer_authz_owner",
          "ALTER TABLE public.mixer_authz_principals DISABLE ROW LEVEL SECURITY"
        ] do
      assert_raise Postgrex.Error, fn -> F.runtime_sql(statement) end
    end

    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               F.grant_context!(Runtime, subject: "unknown")

               for {table, _} <- F.locks(), table != "profiles" do
                 assert [[false]] =
                          F.runtime_sql("SELECT public.mixer_authz_lock_#{table}()").rows
               end

               :ok
             end)

    assert {:ok, _} = F.evaluate()
  end

  test "registered jti cannot select a credential or family owned by another bound principal" do
    F.sql(
      "INSERT INTO public.mixer_authz_families VALUES ('review-family','profile',1,'other-person',true,0,NULL,1)"
    )

    F.sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'review-token','other-person','review-family',true,0,NULL,1)"
    )

    assert {:error, :unauthenticated} =
             F.evaluate(F.identity(%{credential_ref: "review-token"}))

    assert {:error, :unauthenticated} =
             F.evaluate(F.identity(%{profile_id: "foreign-profile"}))

    assert {:ok, _} = F.evaluate()
  end

  test "family and credential evidence intersects fences and expiry without a synthetic revision" do
    time = F.now()

    F.sql("UPDATE public.mixer_authz_families SET not_before=$1,expires_at=$2,revision=7", [
      time - 20,
      time + 120
    ])

    F.sql("UPDATE public.mixer_authz_credentials SET not_before=$1,expires_at=$2,revision=11", [
      time - 10,
      time + 240
    ])

    i = F.identity(%{issued_at: time - 10})

    assert {:observed, ^time} =
             PostgresRepository.with_evidence(
               F.lookup(i),
               fn evidence ->
                 assert evidence.credential.not_before == time - 10
                 assert evidence.credential.expires_at == time + 120
                 assert evidence.credential.revision == 11
                 assert {:ok, _} = Policy.evaluate(i, "artifact.read", F.target(), evidence, time)
                 {:observed, time}
               end,
               Runtime
             )

    assert {:error, :unauthenticated} = F.evaluate(F.identity(%{issued_at: time - 11}))
  end

  test "65th exact-target lifecycle entry fails closed even when its role contributes no read permission" do
    F.sql(
      "INSERT INTO public.mixer_authz_memberships SELECT 'review-' || n,'person','org-a','project-a','exact_project','billing_manager',false,0,NULL,1 FROM generate_series(1,63) n"
    )

    assert {:ok, %{membership_ids: ["member"]}} = F.evaluate()

    F.sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('review-overflow','person','org-a','project-a','exact_project','billing_manager',false,0,NULL,1)"
    )

    assert {:error, :authorization_unavailable} = F.evaluate()
  end

  test "a real inserted membership and changed head are read after a project-head wait" do
    F.sql("DELETE FROM public.mixer_authz_memberships WHERE id='member'")
    parent = self()

    writer =
      Task.async(fn ->
        F.writer(
          5,
          fn ->
            F.sql(
              "INSERT INTO public.mixer_authz_memberships VALUES ('review-new','person','org-a','project-a','exact_project','viewer',true,0,NULL,1)"
            )

            F.sql(
              "UPDATE public.mixer_authz_project_heads SET revision=2 WHERE organization_id='org-a' AND project_id='project-a'"
            )
          end,
          parent,
          true
        )
      end)

    assert_receive {:writer_locked, _}, 2_000
    authorization = waiting_evaluation(parent)
    assert_receive {:review_backend, backend}, 1_000
    assert F.eventually(fn -> F.blocked?(backend) end)
    send(writer.pid, :commit_writer)
    assert {:ok, _} = Task.await(writer)

    assert {:ok, %{membership_ids: ["review-new"], roles: ["viewer"], project_revision: 2}} =
             Task.await(authorization)
  end

  test "physical membership removal after a head wait is not a stale positive snapshot" do
    parent = self()

    writer =
      Task.async(fn ->
        F.writer(
          4,
          fn ->
            F.sql("DELETE FROM public.mixer_authz_memberships WHERE id='member'")

            F.sql(
              "UPDATE public.mixer_authz_organization_heads SET revision=2 WHERE organization_id='org-a'"
            )
          end,
          parent,
          true
        )
      end)

    assert_receive {:writer_locked, _}, 2_000
    authorization = waiting_evaluation(parent)
    assert_receive {:review_backend, backend}, 1_000
    assert F.eventually(fn -> F.blocked?(backend) end)
    send(writer.pid, :commit_writer)
    assert {:ok, _} = Task.await(writer)
    assert {:error, :not_found} = Task.await(authorization)
  end

  test "fresh family valid-after fence committed during a lock wait rejects old issuance" do
    i = F.identity()
    parent = self()

    writer =
      Task.async(fn ->
        F.writer(
          2,
          fn ->
            F.sql(
              "UPDATE public.mixer_authz_families SET not_before=$1,revision=2 WHERE id='family'",
              [i.issued_at + 1]
            )
          end,
          parent,
          true
        )
      end)

    assert_receive {:writer_locked, _}, 2_000
    authorization = waiting_evaluation(parent, i)
    assert_receive {:review_backend, backend}, 1_000
    assert F.eventually(fn -> F.blocked?(backend) end)
    send(writer.pid, :commit_writer)
    assert {:ok, _} = Task.await(writer)
    assert {:error, :unauthenticated} = Task.await(authorization)
  end

  test "callback failure releases locks and every GUC on the same pooled connection" do
    [[before_pid]] = F.runtime_sql("SELECT pg_backend_pid()").rows

    for callback <- [
          fn _ -> raise "independent review error" end,
          fn _ -> throw(:independent_review_throw) end,
          fn _ -> exit(:independent_review_exit) end,
          fn _ -> F.runtime_sql("SELECT 1/0") end
        ] do
      assert {:error, :authorization_unavailable} =
               PostgresRepository.with_evidence(F.lookup(), callback, Runtime)

      assert [[^before_pid]] = F.runtime_sql("SELECT pg_backend_pid()").rows
      assert_clean_context()
      assert {:ok, _} = F.writer(5, fn -> :ok end)
    end

    assert {:ok, _} = F.evaluate()
    assert_clean_context()
  end

  test "queue false rejects immediately when its single runtime connection is already checked out" do
    parent = self()

    holder =
      Task.async(fn ->
        Runtime.checkout(fn ->
          send(parent, :review_checked_out)

          receive do
            :review_release_checkout -> :ok
          after
            2_000 -> raise "review checkout holder timed out"
          end
        end)
      end)

    assert_receive :review_checked_out, 1_000
    started = System.monotonic_time(:millisecond)

    assert {:error, :authorization_unavailable} =
             PostgresRepository.with_evidence(
               F.lookup(),
               fn _ -> flunk("queued callback") end,
               Runtime
             )

    assert System.monotonic_time(:millisecond) - started < 250
    send(holder.pid, :review_release_checkout)
    assert :ok = Task.await(holder)
    assert {:ok, _} = F.evaluate()
  end

  test "runtime refuses an indirect owner role chain then recovers after revocation" do
    F.sql("CREATE ROLE mixer_authz_review_bridge NOLOGIN NOSUPERUSER NOBYPASSRLS")
    F.sql("GRANT mixer_authz_owner TO mixer_authz_review_bridge")
    F.sql("GRANT mixer_authz_review_bridge TO mixer_authz_runtime")

    try do
      assert {:error, :authorization_unavailable} = F.evaluate()
    after
      F.sql("REVOKE mixer_authz_review_bridge FROM mixer_authz_runtime")
      F.sql("DROP ROLE mixer_authz_review_bridge")
    end

    assert {:ok, _} = F.evaluate()
  end

  test "PUBLIC helper execute wrong search_path and login owner each fail runtime admission" do
    for {mutation, restore} <- [
          {"GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_profiles() TO PUBLIC",
           "REVOKE EXECUTE ON FUNCTION public.mixer_authz_lock_profiles() FROM PUBLIC"},
          {"ALTER FUNCTION public.mixer_authz_lock_profiles() SET search_path = public",
           "ALTER FUNCTION public.mixer_authz_lock_profiles() SET search_path = pg_catalog"},
          {"ALTER ROLE mixer_authz_owner LOGIN", "ALTER ROLE mixer_authz_owner NOLOGIN"}
        ] do
      F.sql(mutation)

      try do
        assert {:error, :authorization_unavailable} = F.evaluate()
      after
        F.sql(restore)
      end

      assert {:ok, _} = F.evaluate()
    end
  end

  @tag timeout: 10_000
  test "total transaction timeout rolls back a callback that outlives five seconds" do
    started = System.monotonic_time(:millisecond)

    assert {:error, :authorization_unavailable} =
             PostgresRepository.with_evidence(
               F.lookup(),
               fn _ ->
                 Process.sleep(5_300)
                 {:should_never_escape, :timeout}
               end,
               Runtime
             )

    elapsed = System.monotonic_time(:millisecond) - started
    assert elapsed >= 5_000 and elapsed < 8_000
    assert F.eventually(fn -> match?({:ok, _}, F.evaluate()) end)
    assert_clean_context()
    assert {:ok, _} = F.writer(5, fn -> :ok end)
  end

  test "credential and family expiry during a real wait retain captured-time policy semantics" do
    # Arrange a fractional-second boundary so expiry occurs while the request is
    # waiting, comfortably within the fixed 500ms lock timeout. No policy grace
    # or altered TTL is introduced: the callback still owns its captured instant.
    assert F.eventually(fn -> rem(System.system_time(:millisecond), 1_000) in 650..720 end, 160)
    captured = F.now()
    expiry = captured + 1
    i = F.identity()

    F.sql("UPDATE public.mixer_authz_credentials SET expires_at=$1 WHERE profile_id='profile'", [
      expiry
    ])

    F.sql("UPDATE public.mixer_authz_families SET expires_at=$1 WHERE id='family'", [expiry])
    parent = self()
    writer = Task.async(fn -> F.writer(5, fn -> :ok end, parent, true) end)
    assert_receive {:writer_locked, _}, 1_000
    assert F.now() < expiry
    authorization = waiting_evaluation(parent, i, captured)
    assert_receive {:review_backend, backend}, 1_000
    assert F.eventually(fn -> F.blocked?(backend) end)
    assert F.eventually(fn -> F.now() >= expiry end, 60)
    send(writer.pid, :commit_writer)
    assert {:ok, _} = Task.await(writer)
    assert {:ok, %{evaluated_at: ^captured}} = Task.await(authorization)
    assert {:error, :unauthenticated} = F.evaluate(i)
  end

  defp waiting_evaluation(parent, identity \\ F.identity(), time \\ F.now()) do
    Task.async(fn ->
      Runtime.checkout(fn ->
        [[backend]] = F.runtime_sql("SELECT pg_backend_pid()").rows
        send(parent, {:review_backend, backend})
        F.evaluate(identity, "artifact.read", F.target(), time)
      end)
    end)
  end

  defp assert_clean_context do
    for key <- @context do
      assert [[value]] =
               F.runtime_sql("SELECT pg_catalog.current_setting($1,true)", ["mixer.authz." <> key]).rows

      assert value in [nil, ""]
    end

    assert [[0]] = F.runtime_sql("SELECT count(*) FROM public.mixer_authz_memberships").rows
  end
end
