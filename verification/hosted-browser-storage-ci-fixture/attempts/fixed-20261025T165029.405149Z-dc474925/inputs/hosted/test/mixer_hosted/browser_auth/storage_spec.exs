Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.StorageTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.StorageSchema
  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  setup_all do
    Application.ensure_all_started(:ecto_sql)
    Application.ensure_all_started(:postgrex)
    Application.ensure_all_started(:jason)

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_storage",
      pool_size: 4,
      log: false
    ]

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

    for helper <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.q!(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO browser_ordinary"
          )

    # Ordinary API must not receive privileges on browser rows even by broad grant.
    for t <- ~w(sessions session_vault oidc_attempts session_events),
        do: F.q!(Admin, "REVOKE SELECT ON public.mixer_browser_#{t} FROM browser_ordinary")

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)"
    )

    F.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES('person-1','human',true,0,1)")

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_families VALUES('ordinary-family','humans',1,'person-1',true,0,NULL,1)"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_credentials VALUES('humans',1,'ordinary-jti','person-1','ordinary-family',true,0,NULL,1)"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES('org',true,'Organization')"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_projects(organization_id,id,active,display_name) VALUES('org','project',true,'Project')"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_memberships VALUES('membership','person-1','org',NULL,'all_projects','viewer',true,0,NULL,1)"
    )

    ordinary = F.connection!("browser_ordinary")
    assert directory_rows(ordinary) == [["org"]]
    # Migration is genuinely inert even to a future login until operator review.
    lifecycle = F.connection!()
    assert {:error, :insufficient_privilege} = F.call(lifecycle, :load, [F.random(), F.random()])
    F.provision!()
    assert directory_rows(ordinary) == [["org"]]
    GenServer.stop(ordinary)
    GenServer.stop(lifecycle)
    :ok
  end

  setup do
    conn = F.connection!()
    on_exit(fn -> if Process.alive?(conn), do: GenServer.stop(conn) end)
    %{conn: conn}
  end

  test "restricted lifecycle has execute only, separate nonlogin owner, FORCE RLS and immutable audit",
       %{conn: c} do
    b = F.bootstrap(c)

    assert {:ok, %{rows: [["browser_lifecycle", "browser_lifecycle"]]}} =
             Postgrex.query(c, "SELECT current_user,session_user", [])

    for table <- ~w(sessions session_vault oidc_attempts session_events) do
      assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
               Postgrex.query(c, "SELECT * FROM public.mixer_browser_#{table}", [])

      assert [[true, true, "browser_schema_owner"]] =
               F.q!(
                 Admin,
                 "SELECT relrowsecurity,relforcerowsecurity,pg_catalog.pg_get_userbyid(relowner) FROM pg_catalog.pg_class WHERE oid='public.mixer_browser_#{table}'::regclass"
               ).rows
    end

    for sql <- [
          "SET ROLE browser_writer",
          "UPDATE public.mixer_authz_profiles SET state_revision=state_revision+1",
          "UPDATE public.mixer_authz_credentials SET active=false",
          "SELECT public.mixer_browser_snapshot($1,NULL)"
        ] do
      params = if String.contains?(sql, "$1"), do: [b.id], else: []

      assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
               Postgrex.query(c, sql, params)
    end

    assert [[false, false, false]] =
             F.q!(
               Admin,
               "SELECT rolcanlogin,rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname='browser_writer'"
             ).rows

    assert [[true]] =
             F.q!(
               Admin,
               "SELECT bool_and(pg_catalog.pg_get_userbyid(proowner)='browser_writer' AND prosecdef AND proconfig @> ARRAY['search_path=pg_catalog','statement_timeout=5s','lock_timeout=500ms','idle_in_transaction_session_timeout=5s','bytea_output=hex']) FROM pg_catalog.pg_proc WHERE proname LIKE 'mixer_browser_%'"
             ).rows

    assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
             Postgrex.query(c, "DELETE FROM public.mixer_browser_session_events", [])
  end

  test "bootstrap recovery is stable, cross-browser/stale/config claims deny and provider error consumes once",
       %{conn: c} do
    b = F.bootstrap(c)
    assert {:ok, b.snapshot} == F.call(c, :load, [b.cookie, b.config])
    {b, a} = F.begin_login(c, b)
    other = F.bootstrap(c)

    assert {:error, :raise_exception} =
             F.call(c, :claim, [
               other.cookie,
               a.state,
               other.config,
               1,
               F.random(),
               F.now() + 30,
               F.request()
             ])

    assert {:error, :raise_exception} =
             F.call(c, :claim, [
               b.cookie,
               a.state,
               F.random(),
               b.revision,
               F.random(),
               F.now() + 30,
               F.request()
             ])

    assert {:error, :raise_exception} =
             F.call(c, :claim, [
               b.cookie,
               a.state,
               b.config,
               b.revision - 1,
               F.random(),
               F.now() + 30,
               F.request()
             ])

    assert {:ok, snapshot} =
             F.call(c, :provider_reject, [b.cookie, a.state, b.config, b.revision, F.request()])

    assert snapshot["attempt"]["status"] == "provider_rejected"
    assert snapshot["attempt"]["ciphertext"] == nil
    assert snapshot["browser"]["revision"] == b.revision

    assert {:error, :raise_exception} =
             F.call(c, :provider_reject, [b.cookie, a.state, b.config, b.revision, F.request()])

    assert [[0]] ==
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_authz_families WHERE id LIKE 'browser_%'"
             ).rows
  end

  test "begin supersedes claims; failure closes one-use claim without authority", %{conn: c} do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, _} = F.claim(c, b, a)
    {b, new_attempt} = F.begin_login(c, b)

    assert {:error, :raise_exception} =
             F.call(c, :fail_claim, [
               b.cookie,
               a.state,
               b.config,
               claim,
               "exchange_failed",
               F.request()
             ])

    {new_claim, _} = F.claim(c, b, new_attempt)

    assert {:ok, true} =
             F.call(c, :fail_claim, [
               b.cookie,
               new_attempt.state,
               b.config,
               new_claim,
               "exchange_failed",
               F.request()
             ])

    assert {:error, :raise_exception} =
             F.call(c, :fail_claim, [
               b.cookie,
               new_attempt.state,
               b.config,
               new_claim,
               "exchange_failed",
               F.request()
             ])

    assert [["superseded", nil], ["failed", nil]] ==
             F.q!(
               Admin,
               "SELECT status,ciphertext FROM public.mixer_browser_oidc_attempts WHERE browser_id=$1 ORDER BY browser_epoch",
               [b.id]
             ).rows
  end

  test "atomic activation rotates cookie, exact binding and reusable jti deny, logout revokes local token",
       %{conn: c} do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, _} = F.claim(c, b, a)
    bad = put_in(F.identity().subject, "unknown")
    assert {{:error, :raise_exception}, _, _, _, _} = F.activate(c, b, a, claim, bad)
    {result, active, family, i, _} = F.activate(c, b, a, claim)
    assert {:ok, snapshot} = result
    assert snapshot["browser"]["status"] == "active"
    assert snapshot["browser"]["credential_revision"] == 1
    assert {:ok, nil} = F.call(c, :load, [b.cookie, b.config])

    assert [[true, true, i.iat, i.exp]] ==
             F.q!(
               Admin,
               "SELECT c.active,f.active,c.not_before,c.expires_at FROM public.mixer_authz_credentials c JOIN public.mixer_authz_families f ON f.id=c.family_id WHERE c.reference=$1",
               [i.jti]
             ).rows

    assert {:ok, true} =
             F.call(c, :logout, [
               active.cookie,
               active.csrf,
               active.config,
               active.revision,
               F.request()
             ])

    assert {:ok, true} =
             F.call(c, :logout, [
               active.cookie,
               active.csrf,
               active.config,
               active.revision,
               F.request()
             ])

    assert [[false, 2, false, 2]] ==
             F.q!(
               Admin,
               "SELECT f.active,f.revision,c.active,c.revision FROM public.mixer_authz_families f JOIN public.mixer_authz_credentials c ON c.family_id=f.id WHERE f.id=$1",
               [family]
             ).rows

    second = F.bootstrap(c)
    {second, a2} = F.begin_login(c, second)
    {cl2, _} = F.claim(c, second, a2)
    assert {{:error, :unique_violation}, _, _, _, _} = F.activate(c, second, a2, cl2, i)

    assert [["claimed"]] ==
             F.q!(
               Admin,
               "SELECT status FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
               [a2.state]
             ).rows
  end

  test "current profile binding principal fences scope and family tombstones fail closed", %{
    conn: c
  } do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, _} = F.claim(c, b, a)

    for identity <- [
          Map.put(F.identity(), :profile_revision, 2),
          Map.put(F.identity(), :binding_revision, 2),
          Map.put(F.identity(), :principal_revision, 2),
          Map.put(F.identity(), :scopes, []),
          Map.put(F.identity(), :exp, F.now()),
          Map.put(F.identity(), :iat, 0)
        ] do
      if identity.iat == 0,
        do:
          F.q!(Admin, "UPDATE public.mixer_authz_principals SET not_before=1 WHERE id='person-1'")

      assert {{:error, :raise_exception}, _, _, _, _} = F.activate(c, b, a, claim, identity)

      if identity.iat == 0,
        do:
          F.q!(Admin, "UPDATE public.mixer_authz_principals SET not_before=0 WHERE id='person-1'")
    end

    for {table, column} <- [
          {"profiles", "id='humans' AND version=1"},
          {"bindings", "profile_id='humans' AND subject='subject-1'"},
          {"principals", "id='person-1'"}
        ] do
      F.q!(Admin, "UPDATE public.mixer_authz_#{table} SET active=false WHERE #{column}")
      assert {{:error, :raise_exception}, _, _, _, _} = F.activate(c, b, a, claim)
      F.q!(Admin, "UPDATE public.mixer_authz_#{table} SET active=true WHERE #{column}")
    end

    assert {{:error, :unique_violation}, _, collision, _, _} =
             F.activate(c, b, a, claim, F.identity("ordinary-jti"))

    assert [[0]] ==
             F.q!(Admin, "SELECT count(*) FROM public.mixer_authz_families WHERE id=$1", [
               collision
             ]).rows

    {{:ok, _}, active, family, _, _} = F.activate(c, b, a, claim)

    assert {:ok, true} =
             F.call(c, :logout, [
               active.cookie,
               active.csrf,
               active.config,
               active.revision,
               F.request()
             ])

    b2 = F.bootstrap(c)
    {b2, a2} = F.begin_login(c, b2)
    {claim2, _} = F.claim(c, b2, a2)
    i = F.identity()

    args = [
      b2.cookie,
      a2.state,
      b2.config,
      claim2,
      b2.revision,
      {:verified, i},
      F.random(),
      F.random(),
      F.token(),
      family,
      F.now() + 500,
      {:cipher, F.cipher()},
      F.request()
    ]

    assert {:error, :unique_violation} = F.call(c, :activate, args)

    assert [[0]] ==
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_authz_credentials WHERE reference=$1",
               [i.jti]
             ).rows
  end

  test "replacement retains old family until activation then revokes it atomically", %{conn: c} do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, _} = F.claim(c, b, a)
    {{:ok, _}, active, old_family, _, _} = F.activate(c, b, a, claim)
    {active, a2} = F.begin_login(c, active)
    {claim2, _} = F.claim(c, active, a2)

    assert [[true]] ==
             F.q!(Admin, "SELECT active FROM public.mixer_authz_families WHERE id=$1", [
               old_family
             ]).rows

    {{:ok, _}, _, new_family, _, _} = F.activate(c, active, a2, claim2)

    assert [[false, 2]] ==
             F.q!(Admin, "SELECT active,revision FROM public.mixer_authz_families WHERE id=$1", [
               old_family
             ]).rows

    assert [[true, 1]] ==
             F.q!(Admin, "SELECT active,revision FROM public.mixer_authz_families WHERE id=$1", [
               new_family
             ]).rows
  end

  test "duplicate replicas claim once and late result after logout cannot activate", %{conn: c} do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)

    task =
      Task.async(fn ->
        conn = F.connection!()

        result =
          F.call(conn, :claim, [
            b.cookie,
            a.state,
            b.config,
            b.revision,
            F.random(),
            F.now() + 30,
            F.request()
          ])

        GenServer.stop(conn)
        result
      end)

    own =
      F.call(c, :claim, [
        b.cookie,
        a.state,
        b.config,
        b.revision,
        F.random(),
        F.now() + 30,
        F.request()
      ])

    results = [own, Task.await(task)]
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :raise_exception}, &1)) == 1
    assert {:ok, true} = F.call(c, :logout, [b.cookie, b.csrf, b.config, b.revision, F.request()])
    assert {{:error, :raise_exception}, _, _, _, _} = F.activate(c, b, a, F.random())
  end

  test "audit rejection rolls back family credential vault browser and attempt", %{conn: c} do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, _} = F.claim(c, b, a)
    {_, values} = F.query(:load, [b.cookie, b.config])
    assert length(values) == 2
    {result, _, family, i, _args} = F.activate(c, b, a, claim)
    assert {:ok, _} = result
    # A fresh attempt uses a malformed server request ID to fail the final audit.
    new = F.bootstrap(c)
    {new, a2} = F.begin_login(c, new)
    {cl2, _} = F.claim(c, new, a2)

    args = [
      new.cookie,
      a2.state,
      new.config,
      cl2,
      new.revision,
      {:verified, F.identity()},
      F.random(),
      F.random(),
      F.token(),
      "browser_" <> F.token(),
      F.now() + 500,
      {:cipher, F.cipher()},
      "invalid"
    ]

    assert {:error, :check_violation} = F.call(c, :activate, args)

    assert [["claimed"]] ==
             F.q!(
               Admin,
               "SELECT status FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
               [a2.state]
             ).rows

    assert [["preauth", new.revision]] ==
             F.q!(
               Admin,
               "SELECT status,revision FROM public.mixer_browser_sessions WHERE id=$1",
               [new.id]
             ).rows

    # Confirm the prior successful activation did not confuse this rollback case.
    assert [[family, i.jti]] ==
             F.q!(
               Admin,
               "SELECT family_id,credential_ref FROM public.mixer_browser_sessions WHERE id=$1",
               [b.id]
             ).rows

    assert is_list(args)
  end

  test "exclusive expiry after lock wait and bounded targeted cleanup", %{conn: c} do
    deadline = F.now() + 2
    b = F.bootstrap(c, deadline)
    locker = F.connection!("browser_admin")
    Postgrex.query!(locker, "BEGIN", [])

    Postgrex.query!(
      locker,
      "SELECT 1 FROM public.mixer_browser_sessions WHERE id=$1 FOR UPDATE",
      [b.id]
    )

    task =
      Task.async(fn ->
        conn = F.connection!()
        result = F.call(conn, :load, [b.cookie, b.config])
        GenServer.stop(conn)
        result
      end)

    # Actual lock timeout is bounded and fails closed before the long expiry.
    assert {:error, :lock_not_available} = Task.await(task)
    Postgrex.query!(locker, "ROLLBACK", [])
    GenServer.stop(locker)
    Process.sleep(max((deadline - F.now()) * 1000 + 25, 25))
    assert {:ok, nil} = F.call(c, :load, [b.cookie, b.config])
    assert {:ok, true} = F.call(c, :expire, [b.id, b.revision, F.request()])
    assert {:ok, false} = F.call(c, :expire, [b.id, b.revision, F.request()])

    assert [["expired", nil]] ==
             F.q!(
               Admin,
               "SELECT b.status,v.ciphertext FROM public.mixer_browser_sessions b JOIN public.mixer_browser_session_vault v ON v.browser_id=b.id WHERE b.id=$1",
               [b.id]
             ).rows
  end

  test "operator identifier injection and reserved role names fail before SQL" do
    for role <- ["public", "pg_owned", "a;drop role x", "UPPER", "", String.duplicate("x", 64)] do
      assert_raise ArgumentError, fn ->
        StorageSchema.provisioning_statements(role, "browser_lifecycle")
      end
    end
  end

  test "fresh time after a successful lock wait denies attempt at exclusive expiry", %{conn: c} do
    b = F.bootstrap(c)
    deadline = F.now() + 2
    {b, a} = F.begin_login(c, b, deadline)
    Process.sleep(max(deadline * 1000 - System.system_time(:millisecond) - 180, 0))
    locker = F.connection!("browser_admin")
    Postgrex.query!(locker, "BEGIN", [])

    Postgrex.query!(
      locker,
      "SELECT 1 FROM public.mixer_browser_sessions WHERE id=$1 FOR UPDATE",
      [b.id]
    )

    task =
      Task.async(fn ->
        conn = F.connection!()

        r =
          F.call(conn, :claim, [
            b.cookie,
            a.state,
            b.config,
            b.revision,
            F.random(),
            deadline,
            F.request()
          ])

        GenServer.stop(conn)
        r
      end)

    Process.sleep(300)
    Postgrex.query!(locker, "COMMIT", [])
    GenServer.stop(locker)
    assert {:error, :raise_exception} = Task.await(task)

    assert [["pending"]] ==
             F.q!(
               Admin,
               "SELECT status FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
               [a.state]
             ).rows
  end

  test "ordinary admitted family SHARE serializes logout and replacement in both orders", %{
    conn: c
  } do
    for operation <- [:logout, :replace] do
      b = F.bootstrap(c)
      {b, a} = F.begin_login(c, b)
      {claim, _} = F.claim(c, b, a)
      {{:ok, _}, active, family, i, _} = F.activate(c, b, a, claim)

      old_values = %{
        "family_id" => family,
        "credential_ref" => i.jti,
        "token_issued_at" => Integer.to_string(i.iat),
        "token_expires_at" => Integer.to_string(i.exp)
      }

      ordinary = F.connection!("browser_ordinary")
      assert [["org"]] == directory_rows(ordinary, old_values)

      {active, replacement, cl} =
        if operation == :replace do
          {active, a2} = F.begin_login(c, active)
          {cl, _} = F.claim(c, active, a2)
          {active, a2, cl}
        else
          {active, nil, nil}
        end

      Postgrex.query!(ordinary, "BEGIN", [])
      configure(ordinary, old_values)

      for name <- ~w(profiles principals families credentials) do
        assert [[true]] ==
                 Postgrex.query!(ordinary, "SELECT public.mixer_authz_lock_#{name}()", []).rows
      end

      task =
        Task.async(fn ->
          conn = F.connection!()

          r =
            if operation == :logout,
              do:
                F.call(conn, :logout, [
                  active.cookie,
                  active.csrf,
                  active.config,
                  active.revision,
                  F.request()
                ]),
              else: elem(F.activate(conn, active, replacement, cl), 0)

          GenServer.stop(conn)
          r
        end)

      Process.sleep(100)
      assert Task.yield(task, 0) == nil

      assert [[true]] ==
               Postgrex.query!(
                 ordinary,
                 "SELECT active FROM public.mixer_authz_families WHERE id=$1",
                 [family]
               ).rows

      Postgrex.query!(ordinary, "COMMIT", [])
      assert {:ok, _} = Task.await(task)
      assert [] == directory_rows(ordinary, old_values)
      GenServer.stop(ordinary)
    end
  end

  test "missing audit and orphan events reject direct synthetic owner mutations", %{conn: c} do
    b = F.bootstrap(c)

    assert_raise Postgrex.Error, fn ->
      F.q!(Admin, "UPDATE public.mixer_browser_sessions SET revision=revision+1 WHERE id=$1", [
        b.id
      ])
    end

    assert [[1, 1]] ==
             F.q!(
               Admin,
               "SELECT revision,audit_sequence FROM public.mixer_browser_sessions WHERE id=$1",
               [b.id]
             ).rows

    assert_raise Postgrex.Error, fn ->
      F.q!(
        Admin,
        "INSERT INTO public.mixer_browser_session_events SELECT (pg_catalog.jsonb_populate_record(NULL::public.mixer_browser_session_events, pg_catalog.to_jsonb(e)||pg_catalog.jsonb_build_object('sequence',sequence+1))).* FROM public.mixer_browser_session_events e WHERE browser_id=$1",
        [b.id]
      )
    end

    assert [[1]] ==
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_browser_session_events WHERE browser_id=$1",
               [b.id]
             ).rows

    assert_raise Postgrex.Error, fn ->
      F.q!(
        Admin,
        "UPDATE public.mixer_browser_session_vault SET ciphertext=$2 WHERE browser_id=$1",
        [b.id, F.random()]
      )
    end

    {b, a} = F.begin_login(c, b)

    assert_raise Postgrex.Error, fn ->
      F.q!(
        Admin,
        "UPDATE public.mixer_browser_oidc_attempts SET status='provider_rejected',completion_reason='provider_rejected',key_id=NULL,iv=NULL,tag=NULL,ciphertext=NULL WHERE state_digest=$1",
        [a.state]
      )
    end

    assert [["pending"]] ==
             F.q!(
               Admin,
               "SELECT status FROM public.mixer_browser_oidc_attempts WHERE browser_id=$1",
               [b.id]
             ).rows

    admin = F.connection!("browser_admin")
    Postgrex.query!(admin, "SET ROLE browser_writer", [])

    for sql <- [
          "UPDATE public.mixer_authz_profiles SET state_revision=state_revision+1",
          "UPDATE public.mixer_authz_principals SET revision=revision+1",
          "UPDATE public.mixer_authz_credentials SET principal_id='person-1'",
          "UPDATE public.mixer_browser_oidc_attempts SET issuer='other'",
          "TRUNCATE public.mixer_browser_sessions"
        ] do
      assert {:error, %Postgrex.Error{}} = Postgrex.query(admin, sql, [])
    end

    GenServer.stop(admin)
  end

  test "ordinary role stays scoped and has no lifecycle, DML, column-DML or writer-role path" do
    conn = F.connection!("browser_ordinary")

    for table <- ~w(profiles principals bindings families credentials) do
      assert [[0]] ==
               Postgrex.query!(conn, "SELECT count(*) FROM public.mixer_authz_#{table}", []).rows
    end

    for sql <- [
          "SET ROLE browser_writer",
          "UPDATE public.mixer_authz_profiles SET state_revision=state_revision+1",
          "UPDATE public.mixer_authz_principals SET revision=revision+1",
          "UPDATE public.mixer_authz_families SET active=false",
          "UPDATE public.mixer_authz_credentials SET active=false",
          "INSERT INTO public.mixer_authz_families VALUES('forged','humans',1,'person-1',true,0,NULL,1)",
          "DELETE FROM public.mixer_authz_credentials"
        ] do
      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Postgrex.query(conn, sql, [])
    end

    assert {:error, :insufficient_privilege} = F.call(conn, :load, [F.random(), F.random()])
    assert [["org"]] == directory_rows(conn)
    GenServer.stop(conn)
  end

  test "ordinary directory fixture restores inherited JIT and unchanged bounds on commit and SQL rollback" do
    conn = F.connection!("browser_ordinary")
    initial = directory_settings(conn)
    [_, inherited_jit | _] = initial

    try do
      for jit <- ~w(on off) do
        Postgrex.query!(conn, "SELECT pg_catalog.set_config('jit',$1,false)", [jit])
        before = directory_settings(conn)
        assert [_, ^jit, "5s", "500ms", "5s"] = before
        assert [["org"]] == directory_rows(conn)
        assert before == directory_settings(conn)

        error =
          assert_raise Postgrex.Error, fn ->
            directory_rows(conn, %{"token_expires_at" => "invalid-integer"})
          end

        assert error.postgres.code == :invalid_text_representation
        assert before == directory_settings(conn)
        assert [["org"]] == directory_rows(conn)
      end
    after
      Postgrex.query!(conn, "SELECT pg_catalog.set_config('jit',$1,false)", [inherited_jit])
      assert initial == directory_settings(conn)
      GenServer.stop(conn)
    end
  end

  test "independent review rechecks bootstrap expiry after a rolled-back unique insertion wait" do
    locker = F.connection!()
    on_exit(fn -> if Process.alive?(locker), do: GenServer.stop(locker) end)
    Postgrex.query!(locker, "BEGIN", [])
    other = F.bootstrap(locker)
    deadline = F.now() + 2
    Process.sleep(max(deadline * 1000 - System.system_time(:millisecond) - 180, 0))
    parent = self()

    task =
      Task.async(fn ->
        conn = F.connection!()
        [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
        send(parent, {:review_bootstrap_pid, pid})

        result =
          F.call(conn, :bootstrap, [
            other.id,
            F.random(),
            F.token(),
            F.random(),
            F.random(),
            "humans",
            1,
            deadline,
            {:cipher, F.cipher()},
            F.request()
          ])

        GenServer.stop(conn)
        result
      end)

    assert_receive {:review_bootstrap_pid, pid}, 1_000
    Process.sleep(100)

    assert [["Lock", "transactionid"]] ==
             F.q!(
               Admin,
               "SELECT wait_event_type,wait_event FROM pg_catalog.pg_stat_activity WHERE pid=$1",
               [pid]
             ).rows

    Process.sleep(200)
    assert F.now() >= deadline
    Postgrex.query!(locker, "ROLLBACK", [])
    GenServer.stop(locker)
    assert {:error, :raise_exception} = Task.await(task)

    for table <- ~w(sessions session_vault oidc_attempts session_events) do
      column = if table == "sessions", do: "id", else: "browser_id"

      assert [[0]] ==
               F.q!(
                 Admin,
                 "SELECT count(*) FROM public.mixer_browser_#{table} WHERE #{column}=$1",
                 [other.id]
               ).rows
    end
  end

  test "independent review rechecks begin expiry after a rolled-back unique insertion wait", %{
    conn: c
  } do
    b = F.bootstrap(c)
    locker = F.connection!()
    on_exit(fn -> if Process.alive?(locker), do: GenServer.stop(locker) end)
    other = F.bootstrap(locker)
    Postgrex.query!(locker, "BEGIN", [])
    {_other, a} = F.begin_login(locker, other)
    deadline = F.now() + 2
    Process.sleep(max(deadline * 1000 - System.system_time(:millisecond) - 180, 0))
    parent = self()

    task =
      Task.async(fn ->
        conn = F.connection!()
        [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
        send(parent, {:review_begin_pid, pid})

        result =
          F.call(conn, :begin, [
            b.cookie,
            b.csrf,
            b.config,
            b.revision,
            {:attempt, %{a | expires: deadline}},
            {:cipher, F.cipher()},
            F.request()
          ])

        GenServer.stop(conn)
        result
      end)

    assert_receive {:review_begin_pid, pid}, 1_000
    Process.sleep(100)

    assert [["Lock", "transactionid"]] ==
             F.q!(
               Admin,
               "SELECT wait_event_type,wait_event FROM pg_catalog.pg_stat_activity WHERE pid=$1",
               [pid]
             ).rows

    Process.sleep(200)
    assert F.now() >= deadline
    Postgrex.query!(locker, "ROLLBACK", [])
    GenServer.stop(locker)
    assert {:error, :raise_exception} = Task.await(task)

    assert [[1, 1, 1]] ==
             F.q!(
               Admin,
               "SELECT b.revision,b.audit_sequence,v.vault_generation FROM public.mixer_browser_sessions b JOIN public.mixer_browser_session_vault v ON v.browser_id=b.id WHERE b.id=$1",
               [b.id]
             ).rows

    assert [[0]] ==
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_browser_oidc_attempts WHERE browser_id=$1",
               [b.id]
             ).rows
  end

  test "independent review rechecks activation expiry after a rolled-back unique cookie update wait",
       %{conn: c} do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    deadline = F.now() + 2
    {claim, _} = F.claim(c, b, a, deadline)
    locker = F.connection!()
    on_exit(fn -> if Process.alive?(locker), do: GenServer.stop(locker) end)
    Postgrex.query!(locker, "BEGIN", [])
    other = F.bootstrap(locker)
    identity = F.identity()
    family = "browser_" <> F.token()
    Process.sleep(max(deadline * 1000 - System.system_time(:millisecond) - 180, 0))
    parent = self()

    task =
      Task.async(fn ->
        conn = F.connection!()
        [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
        send(parent, {:review_activate_pid, pid})

        result =
          F.call(conn, :activate, [
            b.cookie,
            a.state,
            b.config,
            claim,
            b.revision,
            {:verified, identity},
            other.cookie,
            F.random(),
            F.token(),
            family,
            F.now() + 500,
            {:cipher, F.cipher()},
            F.request()
          ])

        GenServer.stop(conn)
        result
      end)

    assert_receive {:review_activate_pid, pid}, 1_000
    Process.sleep(100)

    assert [["Lock", "transactionid"]] ==
             F.q!(
               Admin,
               "SELECT wait_event_type,wait_event FROM pg_catalog.pg_stat_activity WHERE pid=$1",
               [pid]
             ).rows

    Process.sleep(200)
    assert F.now() >= deadline
    Postgrex.query!(locker, "ROLLBACK", [])
    GenServer.stop(locker)
    assert {:error, :raise_exception} = Task.await(task)

    assert [["claimed", 2, 3, 2]] ==
             F.q!(
               Admin,
               "SELECT a.status,b.revision,b.audit_sequence,v.vault_generation FROM public.mixer_browser_oidc_attempts a JOIN public.mixer_browser_sessions b ON b.id=a.browser_id JOIN public.mixer_browser_session_vault v ON v.browser_id=b.id WHERE a.state_digest=$1",
               [a.state]
             ).rows

    assert [[0]] ==
             F.q!(Admin, "SELECT count(*) FROM public.mixer_authz_families WHERE id=$1", [family]).rows

    assert [[0]] ==
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_authz_credentials WHERE reference=$1",
               [identity.jti]
             ).rows
  end

  for scopes <- [[nil], ["other.scope", nil]] do
    @review_scopes scopes
    test "independent review rejects activation scopes #{inspect(scopes)}", %{conn: c} do
      b = F.bootstrap(c)
      {b, a} = F.begin_login(c, b)
      {claim, _} = F.claim(c, b, a)

      assert {{:error, :raise_exception}, _, family, identity, _} =
               F.activate(c, b, a, claim, Map.put(F.identity(), :scopes, @review_scopes))

      assert [[0]] ==
               F.q!(Admin, "SELECT count(*) FROM public.mixer_authz_families WHERE id=$1", [
                 family
               ]).rows

      assert [[0]] ==
               F.q!(
                 Admin,
                 "SELECT count(*) FROM public.mixer_authz_credentials WHERE reference=$1",
                 [identity.jti]
               ).rows

      assert [["claimed", 2, 3]] ==
               F.q!(
                 Admin,
                 "SELECT a.status,b.revision,b.audit_sequence FROM public.mixer_browser_oidc_attempts a JOIN public.mixer_browser_sessions b ON b.id=a.browser_id WHERE a.state_digest=$1",
                 [a.state]
               ).rows
    end
  end

  test "catalog source manifest is exact and public execution is revoked" do
    manifest = StorageSchema.catalog_manifest()

    for {name, expected} <- manifest.functions do
      assert [[expected.source, expected.settings, "browser_writer"]] ==
               F.q!(
                 Admin,
                 "SELECT prosrc,proconfig,pg_catalog.pg_get_userbyid(proowner) FROM pg_catalog.pg_proc WHERE oid=('public.'||$1||'('||$2||')')::regprocedure",
                 [name, expected.signature]
               ).rows

      assert [[false]] ==
               F.q!(
                 Admin,
                 "SELECT pg_catalog.has_function_privilege('browser_ordinary',('public.'||$1||'('||$2||')')::regprocedure,'EXECUTE')",
                 [name, expected.signature]
               ).rows
    end
  end

  test "real SQL snapshots decode and reopen durable AEAD custody through independent connections",
       %{conn: c} do
    alias MixerHosted.BrowserAuth.{Vault, StoredSnapshot}
    {:ok, key} = Vault.key("fixture-v1", F.random())
    raw_csrf = F.token()
    csrf = :crypto.hash(:sha256, raw_csrf)
    id = F.random(16)
    cookie = F.random()
    config = F.random()
    generation = F.token()

    context = %{
      purpose: :preauth,
      browser_id: id,
      cookie_digest: cookie,
      csrf_digest: csrf,
      epoch: 1,
      revision: 1,
      generation: generation,
      vault_generation: 1,
      config_digest: config,
      profile_id: "humans",
      profile_version: 1,
      principal_id: nil,
      family_id: nil,
      credential_ref: nil,
      credential_revision: nil
    }

    {:ok, sealed} = Vault.seal(key, context, %Vault.Preauth{csrf: raw_csrf})
    cipher = fn sealed -> {:cipher, {sealed.key_id, sealed.iv, sealed.tag, sealed.ciphertext}} end

    assert {:ok, snapshot} =
             F.call(c, :bootstrap, [
               id,
               cookie,
               generation,
               csrf,
               config,
               "humans",
               1,
               F.now() + 250,
               cipher.(sealed),
               F.request()
             ])

    assert {:ok, decoded} = StoredSnapshot.decode(snapshot)
    assert decoded.session_envelope.context == context

    assert {:ok, %Vault.Preauth{csrf: ^raw_csrf}} =
             Vault.open(key, decoded.session_envelope.context, decoded.session_envelope.sealed)

    a = %{
      state: F.random(),
      nonce: F.random(),
      profile: "humans",
      issuer: "https://issuer.fixture",
      client: "console",
      redirect: "https://console.fixture/auth/callback",
      expires: F.now() + 150
    }

    verifier = F.token()

    attempt_context = %{
      purpose: :attempt,
      state_digest: a.state,
      browser_id: id,
      cookie_digest: cookie,
      epoch: 2,
      revision: 2,
      generation: generation,
      config_digest: config,
      profile_id: "humans",
      profile_version: 1,
      issuer: a.issuer,
      client_id: a.client,
      redirect_uri: a.redirect,
      expires_at: a.expires
    }

    {:ok, attempt_cipher} = Vault.seal(key, attempt_context, %Vault.Verifier{verifier: verifier})
    context = %{context | epoch: 2, revision: 2, vault_generation: 2}
    {:ok, sealed} = Vault.seal(key, context, %Vault.Preauth{csrf: raw_csrf})

    a =
      Map.put(
        a,
        :cipher,
        {attempt_cipher.key_id, attempt_cipher.iv, attempt_cipher.tag, attempt_cipher.ciphertext}
      )

    assert {:ok, snapshot} =
             F.call(c, :begin, [
               cookie,
               csrf,
               config,
               1,
               {:attempt, a},
               cipher.(sealed),
               F.request()
             ])

    assert {:ok, decoded} = StoredSnapshot.decode(snapshot)
    assert decoded.attempt_envelope.context == attempt_context

    assert {:ok, %Vault.Verifier{verifier: ^verifier}} =
             Vault.open(key, decoded.attempt_envelope.context, decoded.attempt_envelope.sealed)

    # Recovered verifier is in owner memory before durable claim erases it.
    claim = F.random()

    assert {:ok, snapshot} =
             F.call(c, :claim, [cookie, a.state, config, 2, claim, F.now() + 55, F.request()])

    assert {:ok, %StoredSnapshot{attempt_envelope: nil}} = StoredSnapshot.decode(snapshot)
    i = F.identity()
    new_cookie = F.random()
    new_raw_csrf = F.token()
    new_csrf = :crypto.hash(:sha256, new_raw_csrf)
    new_generation = F.token()
    family = "browser_" <> F.token()
    token = "synthetic-api-access-token"

    active = %{
      context
      | purpose: :active,
        cookie_digest: new_cookie,
        csrf_digest: new_csrf,
        epoch: 3,
        revision: 3,
        generation: new_generation,
        vault_generation: 3,
        principal_id: "person-1",
        family_id: family,
        credential_ref: i.jti,
        credential_revision: 1
    }

    {:ok, sealed} =
      Vault.seal(key, active, %Vault.Active{csrf: new_raw_csrf, access_token: token})

    assert {:ok, snapshot} =
             F.call(c, :activate, [
               cookie,
               a.state,
               config,
               claim,
               2,
               {:verified, i},
               new_cookie,
               new_csrf,
               new_generation,
               family,
               F.now() + 500,
               cipher.(sealed),
               F.request()
             ])

    assert {:ok, decoded} = StoredSnapshot.decode(snapshot)
    assert decoded.session_envelope.context == active

    assert {:ok, %Vault.Active{csrf: ^new_raw_csrf, access_token: ^token}} =
             Vault.open(key, decoded.session_envelope.context, decoded.session_envelope.sealed)

    restarted = F.connection!()
    Postgrex.query!(restarted, "SET bytea_output='escape'", [])
    assert {:ok, snapshot} = F.call(restarted, :load, [new_cookie, config])
    assert {:ok, decoded} = StoredSnapshot.decode(snapshot)
    assert decoded.attempt == nil

    assert {:ok, %Vault.Active{access_token: ^token}} =
             Vault.open(key, decoded.session_envelope.context, decoded.session_envelope.sealed)

    GenServer.stop(restarted)
    # Provider-error output is also accepted by the real typed decoder.
    other = F.bootstrap(c)
    {other, attempt} = F.begin_login(c, other)

    assert {:ok, rejected} =
             F.call(c, :provider_reject, [
               other.cookie,
               attempt.state,
               other.config,
               other.revision,
               F.request()
             ])

    assert {:ok, %StoredSnapshot{attempt_envelope: nil}} = StoredSnapshot.decode(rejected)
  end

  test "non-superuser operator ownership failure rolls back temporary grants and remains inert" do
    alias MixerHosted.BrowserAuth.StorageFixture.OperatorMigration

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_operator_storage",
      username: "browser_operator",
      pool_size: 2,
      log: false
    ]

    start_supervised!({OperatorMigration, settings})
    F.install!(OperatorMigration)
    {:ok, operator} = Postgrex.start_link(Keyword.put(settings, :pool_size, 1))
    Process.unlink(operator)
    plan = StorageSchema.provisioning_statements("browser_writer", "browser_lifecycle")
    assert ["BEGIN", admission, temporary_create | rest] = plan
    for sql <- ["BEGIN", admission, temporary_create], do: Postgrex.query!(operator, sql, [])

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Postgrex.query(operator, hd(rest), [])

    Postgrex.query!(operator, "ROLLBACK", [])

    assert [[false, true]] ==
             Postgrex.query!(
               operator,
               "SELECT pg_catalog.has_schema_privilege('browser_writer','public','CREATE'),pg_catalog.has_schema_privilege('browser_writer','public','USAGE')",
               []
             ).rows

    assert [[true]] ==
             Postgrex.query!(
               operator,
               "SELECT bool_and(pg_catalog.pg_get_userbyid(proowner)='browser_operator') FROM pg_catalog.pg_proc WHERE proname LIKE 'mixer_browser_%'",
               []
             ).rows

    assert [[0]] ==
             Postgrex.query!(
               operator,
               "SELECT count(*) FROM pg_catalog.pg_policies WHERE schemaname='public' AND policyname LIKE 'mixer_browser_%'",
               []
             ).rows

    assert [[false, false]] ==
             Postgrex.query!(
               operator,
               "SELECT pg_catalog.has_table_privilege('browser_writer','public.mixer_browser_sessions','INSERT'),pg_catalog.has_function_privilege('browser_lifecycle','public.mixer_browser_load(bytea,bytea)','EXECUTE')",
               []
             ).rows

    GenServer.stop(operator)
  end

  test "controlled rollback and reapply preserve ordinary directory and revoke writer authz grants" do
    ordinary = F.connection!("browser_ordinary")
    assert [["org"]] == directory_rows(ordinary)

    assert :ok =
             Ecto.Migrator.down(
               Migration,
               20_261_025_000_007,
               MixerHosted.Repo.Migrations.AddBrowserSessions,
               log: false
             )

    assert [["org"]] == directory_rows(ordinary)

    assert [[false, false, false]] ==
             F.q!(
               Admin,
               "SELECT pg_catalog.has_table_privilege('browser_writer','public.mixer_authz_families','SELECT'),pg_catalog.has_table_privilege('browser_writer','public.mixer_authz_families','INSERT'),pg_catalog.has_column_privilege('browser_writer','public.mixer_authz_profiles','state_revision','UPDATE')"
             ).rows

    assert :ok =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_007,
               MixerHosted.Repo.Migrations.AddBrowserSessions,
               log: false
             )

    F.provision!()
    assert [["org"]] == directory_rows(ordinary)
    GenServer.stop(ordinary)
  end

  defp directory_rows(conn, overrides \\ %{}) do
    before = directory_settings(conn)
    [backend, _jit, statement, lock, idle] = before
    Postgrex.query!(conn, "BEGIN", [])

    try do
      # Match the ordinary runtime's bounded transaction preparation without
      # changing this connection's inherited policy or any timeout.
      Postgrex.query!(conn, "SET LOCAL jit = off", [])
      assert [backend, "off", statement, lock, idle] == directory_settings(conn)
      configure(conn, overrides)

      rows =
        Postgrex.query!(conn, "SELECT id FROM public.mixer_authz_organizations ORDER BY id", []).rows

      Postgrex.query!(conn, "COMMIT", [])
      rows
    rescue
      error ->
        Postgrex.query!(conn, "ROLLBACK", [])
        reraise error, __STACKTRACE__
    after
      assert before == directory_settings(conn)
    end
  end

  defp directory_settings(conn) do
    Postgrex.query!(
      conn,
      "SELECT pg_catalog.pg_backend_pid(),pg_catalog.current_setting('jit'),pg_catalog.current_setting('statement_timeout'),pg_catalog.current_setting('lock_timeout'),pg_catalog.current_setting('idle_in_transaction_session_timeout')",
      []
    ).rows
    |> hd()
  end

  defp configure(conn, overrides) do
    values = %{
      "profile_id" => "humans",
      "profile_version" => "1",
      "issuer" => "https://issuer.fixture",
      "client_id" => "console",
      "identity_class" => "human",
      "principal_id" => "person-1",
      "subject" => "subject-1",
      "family_id" => "ordinary-family",
      "credential_ref" => "ordinary-jti",
      "directory_mode" => "organizations",
      "action" => "workspace.read",
      "required_scope" => "mixer.workspace.read",
      "phase" => "directory",
      "project_id" => "",
      "application_id" => "",
      "environment_id" => "",
      "organization_id" => "",
      "token_issued_at" => Integer.to_string(F.now() - 5),
      "token_expires_at" => Integer.to_string(F.now() + 300)
    }

    Enum.each(Map.merge(values, overrides), fn {key, value} ->
      Postgrex.query!(conn, "SELECT pg_catalog.set_config($1,$2,true)", [
        "mixer.authz." <> key,
        value
      ])
    end)

    :ok
  end
end
