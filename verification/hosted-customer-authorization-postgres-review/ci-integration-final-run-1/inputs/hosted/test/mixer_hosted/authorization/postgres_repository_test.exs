defmodule MixerHosted.Authorization.PostgresFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_authz_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.PostgresFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_authz_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.PostgresFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_authz_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.PostgresFixture.Adapter do
  def with_evidence(lookup, callback) do
    MixerHosted.Authorization.PostgresRepository.with_evidence(
      lookup,
      callback,
      MixerHosted.Authorization.PostgresFixture.Runtime
    )
  end
end

defmodule MixerHosted.Authorization.PostgresFixture do
  alias MixerHosted.Authorization.{Policy, Repository, Scope, PostgresRepository}
  alias MixerHosted.Authorization.PostgresFixture.{Admin, Runtime, Adapter}
  alias MixerHosted.Identity.VerifiedIdentity

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @locks [
    {"profiles", "id = 'profile' AND version = 1"},
    {"principals", "id = 'person'"},
    {"families", "id = 'family'"},
    {"credentials", "profile_id = 'profile' AND profile_version = 1 AND reference = 'token'"},
    {"organization_heads", "organization_id = 'org-a'"},
    {"project_heads", "organization_id = 'org-a' AND project_id = 'project-a'"}
  ]

  def tables, do: @tables
  def locks, do: @locks
  def sql(sql, values \\ []), do: Ecto.Adapters.SQL.query!(Admin, sql, values, log: false)

  def runtime_sql(sql, values \\ []),
    do: Ecto.Adapters.SQL.query!(Runtime, sql, values, log: false)

  def now, do: System.system_time(:second)

  def identity(overrides \\ %{}) do
    struct!(
      VerifiedIdentity,
      Map.merge(
        %{
          profile_id: "profile",
          profile_version: 1,
          issuer: "https://issuer.example",
          subject: "subject",
          client_id: "client",
          credential_ref: "token",
          issued_at: now() - 20,
          expires_at: now() + 600,
          identity_class: :human,
          scopes: ["mixer.artifact.read", "mixer.artifact.upload", "mixer.audit.read"]
        },
        Map.new(overrides)
      )
    )
  end

  def target(overrides \\ %{}),
    do:
      struct!(
        Scope,
        Map.merge(
          %{
            organization_id: "org-a",
            project_id: "project-a",
            application_id: "app-a",
            environment_id: "env-a"
          },
          Map.new(overrides)
        )
      )

  def lookup(i \\ identity(), action \\ "artifact.read", t \\ target()),
    do: %{identity: Policy.identity_key(i), action: action, target: t}

  def evaluate(i \\ identity(), action \\ "artifact.read", t \\ target(), time \\ now()),
    do: Repository.evaluate(i, action, t, time, Adapter)

  def seed! do
    sql(
      "TRUNCATE " <>
        Enum.map_join(Enum.reverse(@tables), ",", &("public.mixer_authz_" <> &1)) <> " CASCADE"
    )

    sql(
      "INSERT INTO public.mixer_authz_profiles VALUES ('profile',1,'https://issuer.example','client','human',true), ('foreign-profile',1,'https://foreign.example','client','human',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,1), ('other-person','human',true,0,1), ('service','service',true,0,1)"
    )

    sql(
      "INSERT INTO public.mixer_authz_bindings VALUES ('profile',1,'subject','human','person',true), ('foreign-profile',1,'subject','human','other-person',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,1), ('other-family','foreign-profile',1,'other-person',true,0,NULL,1)"
    )

    sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'token','person','family',true,0,NULL,1), ('foreign-profile',1,'token','other-person','other-family',true,0,NULL,1)"
    )

    sql("INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true),('org-b',true)")

    sql(
      "INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true),('org-a','project-b',true),('org-b','project-a',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','app-a',true),('org-a','project-b','app-b',true),('org-b','project-a','app-a',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_environments VALUES ('org-a','project-a','app-a','env-a',true),('org-a','project-b','app-b','env-b',true),('org-b','project-a','app-a','env-a',true)"
    )

    sql("INSERT INTO public.mixer_authz_organization_heads VALUES ('org-a',1),('org-b',1)")

    sql(
      "INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',1),('org-a','project-b',1),('org-b','project-a',1)"
    )

    sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org-a','project-a','exact_project','developer',true,0,NULL,1),('foreign-member','other-person','org-b','project-a','exact_project','owner',true,0,NULL,1)"
    )

    :ok
  end

  def grant_context!(repo \\ Runtime, changes \\ []) do
    values = [
      profile_id: "profile",
      profile_version: "1",
      issuer: "https://issuer.example",
      subject: "subject",
      client_id: "client",
      identity_class: "human",
      credential_ref: "token",
      principal_id: "person",
      family_id: "family",
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "app-a",
      environment_id: "env-a"
    ]

    MixerHosted.Authorization.Postgres.Session.context!(repo, Keyword.merge(values, changes))
  end

  # Test-only administrator protocol. Earlier classes take shared locks; the
  # affected class takes the conflicting lock. No runtime mutation path exists.
  def writer(index, mutation, parent \\ nil, hold \\ false) do
    Admin.transaction(
      fn ->
        [[pid]] = sql("SELECT pg_backend_pid()").rows
        if parent, do: send(parent, {:writer_backend, self(), pid})

        @locks
        |> Enum.take(index + 1)
        |> Enum.with_index()
        |> Enum.each(fn {{table, predicate}, n} ->
          mode = if n == index, do: "UPDATE", else: "SHARE"
          sql("SELECT 1 FROM public.mixer_authz_#{table} WHERE #{predicate} FOR #{mode}")
        end)

        if parent, do: send(parent, {:writer_locked, self()})

        if hold do
          receive do
            :commit_writer -> :ok
          after
            2_000 -> raise "fixture writer release timed out"
          end
        end

        mutation.()
      end,
      timeout: 4_000
    )
  end

  def held_evaluation(parent) do
    i = identity()
    l = lookup(i)
    marker = make_ref()

    PostgresRepository.with_evidence(
      l,
      fn evidence ->
        [[pid]] = runtime_sql("SELECT pg_backend_pid()").rows
        send(parent, {:authorization_held, self(), pid})

        receive do
          :release_authorization -> :ok
        after
          2_000 -> raise "fixture authorization release timed out"
        end

        {:policy_evaluation, marker, Policy.evaluate(i, l.action, l.target, evidence, now())}
      end,
      Runtime
    )
  end

  def blocked?(backend) do
    sql("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = $1", [backend]).rows ==
      [[true]]
  end

  def eventually(fun, attempts \\ 100)
  def eventually(fun, 0), do: fun.()

  def eventually(fun, attempts) do
    if fun.(),
      do: true,
      else:
        (
          Process.sleep(10)
          eventually(fun, attempts - 1)
        )
  end
end

defmodule MixerHosted.Authorization.PostgresRepositoryTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization.{Policy, PostgresRepository}
  alias MixerHosted.Authorization.PostgresFixture, as: F
  alias MixerHosted.Authorization.PostgresFixture.{Admin, Migration, Runtime}

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
           pool_size: 2,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE mixer_authz_owner", []) end
         ]}
    )

    start_supervised!({Runtime, settings ++ [username: "mixer_authz_runtime", pool_size: 4]})

    unless Code.ensure_loaded?(MixerHosted.Repo.Migrations.AddCustomerAuthorization) do
      Code.require_file(
        Path.expand(
          "../../../priv/repo/migrations/20261025000003_add_customer_authorization.exs",
          __DIR__
        )
      )
    end

    assert :ok =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_003,
               MixerHosted.Repo.Migrations.AddCustomerAuthorization,
               log: false
             )

    assert :already_up =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_003,
               MixerHosted.Repo.Migrations.AddCustomerAuthorization,
               log: false
             )

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

  test "real runtime role produces the existing complete callback envelope and role projection" do
    assert {:ok, decision} = F.evaluate()
    assert decision.roles == ["developer"] and decision.membership_ids == ["member"]
    assert decision.target == F.target() and decision.credential_revision == 1

    marker = make_ref()

    assert {:policy_evaluation, ^marker, {:ok, _}} =
             PostgresRepository.with_evidence(
               F.lookup(),
               fn e ->
                 assert Runtime.in_transaction?()

                 assert [["read committed", "5s", "500ms"]] =
                          F.runtime_sql(
                            "SELECT current_setting('transaction_isolation'), current_setting('statement_timeout'), current_setting('lock_timeout')"
                          ).rows

                 {:policy_evaluation, marker,
                  Policy.evaluate(F.identity(), "artifact.read", F.target(), e, F.now())}
               end,
               Runtime
             )
  end

  test "all six human roles retain the exact three-action ceilings" do
    for role <- ~w(owner administrator developer release_manager billing_manager viewer),
        action <- ~w(artifact.read artifact.upload audit.read) do
      F.sql("UPDATE public.mixer_authz_memberships SET role = $1 WHERE id = 'member'", [role])

      target =
        if action == "audit.read",
          do: F.target(application_id: nil, environment_id: nil),
          else: F.target()

      allowed =
        role != "billing_manager" and
          (action != "artifact.upload" or role in ~w(owner administrator developer))

      result = F.evaluate(F.identity(), action, target)

      if allowed,
        do: assert({:ok, _} = result),
        else: assert(result == {:error, :permission_denied})
    end
  end

  test "scope intersection, unsupported actions, classes and future iat keep existing semantics" do
    assert {:error, :permission_denied} = F.evaluate(F.identity(%{scopes: []}))
    assert {:error, :permission_denied} = F.evaluate(F.identity(), "release.publish")
    assert {:error, :permission_denied} = F.evaluate(F.identity(%{identity_class: :service}))
    time = F.now()

    assert {:ok, _} =
             F.evaluate(F.identity(%{issued_at: time + 30}), "artifact.read", F.target(), time)

    assert {:error, :unauthenticated} =
             F.evaluate(F.identity(%{issued_at: time + 31}), "artifact.read", F.target(), time)

    assert {:error, :unauthenticated} =
             F.evaluate(F.identity(%{expires_at: time}), "artifact.read", F.target(), time)
  end

  test "exact identity linkage rejects foreign issuer subject client profile version and jti" do
    for change <- [
          %{issuer: "https://foreign.example"},
          %{subject: "unknown"},
          %{client_id: "foreign"},
          %{profile_id: "foreign-profile"},
          %{profile_version: 2},
          %{credential_ref: "unknown"}
        ] do
      assert {:error, :unauthenticated} = F.evaluate(F.identity(change))
    end
  end

  test "current profile binding principal family and credential state fail closed" do
    for {table, predicate} <- [
          {"profiles", "id='profile'"},
          {"bindings", "profile_id='profile'"},
          {"principals", "id='person'"},
          {"families", "id='family'"},
          {"credentials", "profile_id='profile'"}
        ] do
      F.sql("UPDATE public.mixer_authz_#{table} SET active=false WHERE #{predicate}")
      assert {:error, :unauthenticated} = F.evaluate()
      F.sql("UPDATE public.mixer_authz_#{table} SET active=true WHERE #{predicate}")
    end
  end

  test "family and credential validity windows intersect and enforce issued-at fences" do
    time = F.now()

    for table <- ["principals", "families", "credentials"] do
      F.sql("UPDATE public.mixer_authz_#{table} SET not_before=$1", [time - 10])
      assert {:error, :unauthenticated} = F.evaluate()
      F.sql("UPDATE public.mixer_authz_#{table} SET not_before=0")
    end

    for table <- ["families", "credentials"] do
      F.sql("UPDATE public.mixer_authz_#{table} SET expires_at=$1", [time])

      assert {:error, :unauthenticated} =
               F.evaluate(F.identity(), "artifact.read", F.target(), time)

      F.sql("UPDATE public.mixer_authz_#{table} SET expires_at=NULL")
    end
  end

  test "stored ancestry and every inactive parent reject mismatched targets" do
    for changes <- [
          [organization_id: "org-b"],
          [project_id: "project-b"],
          [application_id: "app-b"],
          [environment_id: "env-b"]
        ] do
      assert {:error, :not_found} =
               F.evaluate(F.identity(), "artifact.read", F.target(Map.new(changes)))
    end

    for {table, predicate} <- [
          {"organizations", "id='org-a'"},
          {"projects", "organization_id='org-a' AND id='project-a'"},
          {"applications", "organization_id='org-a' AND id='app-a'"},
          {"environments", "organization_id='org-a' AND id='env-a'"}
        ] do
      F.sql("UPDATE public.mixer_authz_#{table} SET active=false WHERE #{predicate}")
      assert {:error, :not_found} = F.evaluate()
      F.sql("UPDATE public.mixer_authz_#{table} SET active=true WHERE #{predicate}")
    end
  end

  test "organization_only is not visibility while all_projects is explicit and bounded" do
    F.sql(
      "UPDATE public.mixer_authz_memberships SET project_id=NULL, project_binding='organization_only' WHERE id='member'"
    )

    assert {:error, :not_found} = F.evaluate()

    F.sql(
      "UPDATE public.mixer_authz_memberships SET project_binding='all_projects' WHERE id='member'"
    )

    assert {:ok, _} = F.evaluate()

    assert {:ok, _} =
             F.evaluate(
               F.identity(),
               "artifact.read",
               F.target(%{
                 project_id: "project-b",
                 application_id: "app-b",
                 environment_id: "env-b"
               })
             )

    assert {:error, :not_found} =
             F.evaluate(F.identity(), "artifact.read", F.target(%{organization_id: "org-b"}))
  end

  test "64 exact matching lifecycle rows are accepted and 65 fail unavailable even if inactive" do
    F.sql("DELETE FROM public.mixer_authz_memberships WHERE id='member'")

    F.sql(
      "INSERT INTO public.mixer_authz_memberships SELECT 'm-' || n, 'person','org-a','project-a','exact_project','viewer',true,0,NULL,1 FROM generate_series(1,64) n"
    )

    assert {:ok, %{membership_ids: ids}} = F.evaluate()
    assert length(ids) == 64

    F.sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('overflow','person','org-a','project-a','exact_project','viewer',false,0,NULL,1)"
    )

    assert {:error, :authorization_unavailable} = F.evaluate()
  end

  test "membership lookup excludes unrelated project and organization-only population" do
    F.sql(
      "INSERT INTO public.mixer_authz_memberships SELECT 'unrelated-' || n,'person','org-a','project-b','exact_project','owner',true,0,NULL,1 FROM generate_series(1,100) n"
    )

    F.sql(
      "INSERT INTO public.mixer_authz_memberships SELECT 'org-only-' || n,'person','org-a',NULL,'organization_only','owner',true,0,NULL,1 FROM generate_series(1,100) n"
    )

    assert {:ok, %{membership_ids: ["member"]}} = F.evaluate()
  end

  test "revoked invited and expired memberships never produce target visibility" do
    time = F.now()

    for {field, value} <- [{"active", false}, {"not_before", time + 60}, {"expires_at", time}] do
      F.sql("UPDATE public.mixer_authz_memberships SET #{field}=$1 WHERE id='member'", [value])
      assert {:error, :not_found} = F.evaluate()

      F.sql(
        "UPDATE public.mixer_authz_memberships SET active=true, not_before=0, expires_at=NULL"
      )
    end
  end

  test "FORCE RLS applies to nonlogin helper owner and runtime has no direct row-lock or mutation authority" do
    assert [[false, false, false]] =
             F.sql(
               "SELECT rolcanlogin,rolsuper,rolbypassrls FROM pg_roles WHERE rolname='mixer_authz_owner'"
             ).rows

    assert [[0]] =
             Ecto.Adapters.SQL.query!(
               Migration,
               "SELECT count(*) FROM public.mixer_authz_profiles"
             ).rows

    assert [[false]] =
             Ecto.Adapters.SQL.query!(Migration, "SELECT public.mixer_authz_lock_profiles()").rows

    assert [[12]] =
             F.sql(
               "SELECT count(*) FROM pg_class WHERE relname LIKE 'mixer_authz_%' AND relkind='r' AND relrowsecurity AND relforcerowsecurity"
             ).rows

    assert_raise Postgrex.Error, fn ->
      F.runtime_sql("UPDATE public.mixer_authz_principals SET active=true")
    end

    assert_raise Postgrex.Error, fn ->
      F.runtime_sql("SELECT * FROM public.mixer_authz_profiles FOR SHARE")
    end

    assert_raise Postgrex.Error, fn -> F.runtime_sql("SET ROLE mixer_authz_owner") end

    assert_raise Postgrex.Error, fn ->
      F.runtime_sql("CREATE TABLE public.runtime_escalation(id int)")
    end

    assert {:ok, _} = F.evaluate()
  end

  test "missing context returns no identity policy membership or resource rows" do
    for table <- F.tables() do
      assert [[0]] = F.runtime_sql("SELECT count(*) FROM public.mixer_authz_#{table}").rows
    end

    for {table, _} <- F.locks(),
        do: assert([[false]] = F.runtime_sql("SELECT public.mixer_authz_lock_#{table}()").rows)
  end

  test "RLS ties derived principal to exact verified binding and tenant scope" do
    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               F.grant_context!()

               assert [["person"]] =
                        F.runtime_sql("SELECT id FROM public.mixer_authz_principals").rows

               assert [["member"]] =
                        F.runtime_sql("SELECT id FROM public.mixer_authz_memberships").rows

               assert [["org-a"]] =
                        F.runtime_sql("SELECT id FROM public.mixer_authz_organizations").rows

               F.grant_context!(Runtime, principal_id: "other-person")

               assert [[0]] =
                        F.runtime_sql("SELECT count(*) FROM public.mixer_authz_principals").rows

               assert [[0]] =
                        F.runtime_sql("SELECT count(*) FROM public.mixer_authz_memberships").rows

               F.grant_context!(Runtime, subject: "unknown")

               assert [[0]] =
                        F.runtime_sql("SELECT count(*) FROM public.mixer_authz_credentials").rows

               F.grant_context!(Runtime, issuer: "https://foreign.example")

               assert [[0]] =
                        F.runtime_sql("SELECT count(*) FROM public.mixer_authz_bindings").rows

               F.grant_context!(Runtime, organization_id: "org-b")

               assert [[0]] =
                        F.runtime_sql("SELECT count(*) FROM public.mixer_authz_memberships").rows

               :ok
             end)
  end

  test "runtime refuses owner elevated helper-owner and direct authorization DML grants" do
    assert {:error, :authorization_unavailable} =
             PostgresRepository.with_evidence(F.lookup(), & &1, Admin)

    assert {:error, :authorization_unavailable} =
             PostgresRepository.with_evidence(F.lookup(), & &1, Migration)

    for grant <- [
          "GRANT mixer_authz_owner TO mixer_authz_runtime",
          "GRANT UPDATE(active) ON public.mixer_authz_principals TO mixer_authz_runtime"
        ] do
      F.sql(grant)
      assert {:error, :authorization_unavailable} = F.evaluate()

      if String.starts_with?(grant, "GRANT mixer"),
        do: F.sql("REVOKE mixer_authz_owner FROM mixer_authz_runtime"),
        else:
          F.sql("REVOKE UPDATE(active) ON public.mixer_authz_principals FROM mixer_authz_runtime")
    end

    assert {:ok, _} = F.evaluate()
  end

  test "nested transactions malformed lookups and missing repositories fail closed" do
    assert {:ok, {:error, :authorization_unavailable}} =
             Runtime.transaction(fn ->
               PostgresRepository.with_evidence(
                 F.lookup(),
                 fn _ -> flunk("nested callback") end,
                 Runtime
               )
             end)

    for bad <- [
          nil,
          Map.put(F.lookup(), :role, "owner"),
          put_in(F.lookup(), [:identity, :role], "owner"),
          put_in(F.lookup(), [:identity, :identity_class], :service)
        ] do
      assert {:error, :authorization_unavailable} =
               PostgresRepository.with_evidence(bad, & &1, Runtime)
    end

    assert {:error, :authorization_unavailable} =
             PostgresRepository.with_evidence(F.lookup(), & &1, UnknownAuthorizationRepo)
  end

  test "every grantable predefined pg_ role rejects without exercising its capabilities" do
    roles =
      F.sql(
        "SELECT rolname::text FROM pg_roles WHERE substr(rolname::text,1,3)='pg_' AND rolname <> 'pg_database_owner' ORDER BY rolname"
      ).rows

    assert length(roles) >= 10

    for [role] <- roles do
      F.sql("GRANT #{role} TO mixer_authz_runtime")

      try do
        assert {:error, :authorization_unavailable} = F.evaluate()
      after
        F.sql("REVOKE #{role} FROM mixer_authz_runtime")
      end
    end

    assert {:ok, _} = F.evaluate()
  end

  test "indirect non-inherited predefined-role paths reject and an unprivileged membership remains allowed" do
    F.sql(
      "CREATE ROLE authz_indirect_fixture NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
    )

    F.sql("GRANT authz_indirect_fixture TO mixer_authz_runtime WITH INHERIT FALSE, SET TRUE")

    try do
      assert {:ok, _} = F.evaluate()

      for role <-
            ~w(pg_read_server_files pg_write_server_files pg_execute_server_program pg_monitor) do
        F.sql("GRANT #{role} TO authz_indirect_fixture WITH INHERIT FALSE, SET TRUE")

        try do
          assert [[true, false, true]] =
                   F.sql(
                     "SELECT pg_has_role('mixer_authz_runtime',$1,'MEMBER'), pg_has_role('mixer_authz_runtime',$1,'USAGE'), pg_has_role('mixer_authz_runtime',$1,'SET')",
                     [role]
                   ).rows

          assert {:error, :authorization_unavailable} = F.evaluate()
        after
          F.sql("REVOKE #{role} FROM authz_indirect_fixture")
        end
      end

      assert {:ok, _} = F.evaluate()
    after
      F.sql("REVOKE authz_indirect_fixture FROM mixer_authz_runtime")
      F.sql("DROP ROLE authz_indirect_fixture")
    end
  end

  test "callback errors roll back context and no context leaks through connection reuse" do
    for callback <- [
          fn _ -> raise "fixture error" end,
          fn _ -> throw(:fixture_error) end,
          fn _ -> Runtime.rollback(:forced) end
        ] do
      assert {:error, :authorization_unavailable} =
               PostgresRepository.with_evidence(F.lookup(), callback, Runtime)

      for _ <- 1..8 do
        assert [[0]] = F.runtime_sql("SELECT count(*) FROM public.mixer_authz_memberships").rows
      end
    end

    assert {:ok, _} = F.evaluate()
    assert [[0]] = F.runtime_sql("SELECT count(*) FROM public.mixer_authz_credentials").rows
  end

  test "all six canonical conflicting lock classes wait for an admitted lookup then revoke" do
    for {index, mutation, expected} <- revocations() do
      F.seed!()
      parent = self()
      authorization = Task.async(fn -> F.held_evaluation(parent) end)
      assert_receive {:authorization_held, _, _}, 2_000
      writer = Task.async(fn -> F.writer(index, mutation, parent) end)
      writer_pid = writer.pid
      assert_receive {:writer_backend, _, backend}, 2_000
      assert F.eventually(fn -> F.blocked?(backend) end)
      refute_receive {:writer_locked, ^writer_pid}, 10
      send(authorization.pid, :release_authorization)
      assert {:policy_evaluation, _, {:ok, _}} = Task.await(authorization)
      assert {:ok, _} = Task.await(writer)
      assert_receive {:writer_locked, ^writer_pid}, 1_000
      assert expected == F.evaluate()
    end
  end

  test "policy evaluation instant is captured by the caller and is not a fresh wall-clock check" do
    captured = F.now()
    identity = F.identity(%{expires_at: captured + 1})
    marker = make_ref()

    assert {:policy_evaluation, ^marker, {:ok, _}} =
             PostgresRepository.with_evidence(
               F.lookup(identity),
               fn evidence ->
                 assert F.eventually(fn -> F.now() >= identity.expires_at end, 150)

                 {:policy_evaluation, marker,
                  Policy.evaluate(identity, "artifact.read", F.target(), evidence, captured)}
               end,
               Runtime
             )

    assert {:error, :unauthenticated} = F.evaluate(identity)
  end

  test "all six reverse lock orderings read freshly committed revocation after their wait" do
    for {index, mutation, expected} <- revocations() do
      F.seed!()
      parent = self()
      writer = Task.async(fn -> F.writer(index, mutation, parent, true) end)
      assert_receive {:writer_backend, _, _}, 2_000
      assert_receive {:writer_locked, _}, 2_000

      authorization =
        Task.async(fn ->
          Runtime.checkout(fn ->
            [[pid]] = F.runtime_sql("SELECT pg_backend_pid()").rows
            send(parent, {:authorization_backend, pid})
            F.evaluate()
          end)
        end)

      assert_receive {:authorization_backend, backend}, 2_000
      assert F.eventually(fn -> F.blocked?(backend) end)
      send(writer.pid, :commit_writer)
      assert {:ok, _} = Task.await(writer)
      assert expected == Task.await(authorization)
    end
  end

  test "project membership provisioning serializes under the existing project head" do
    F.sql("UPDATE public.mixer_authz_memberships SET active=false WHERE id='member'")
    parent = self()

    writer =
      Task.async(fn ->
        F.writer(
          5,
          fn ->
            F.sql(
              "UPDATE public.mixer_authz_memberships SET active=true,revision=revision+1 WHERE id='member'"
            )

            F.sql(
              "UPDATE public.mixer_authz_project_heads SET revision=revision+1 WHERE organization_id='org-a' AND project_id='project-a'"
            )
          end,
          parent,
          true
        )
      end)

    assert_receive {:writer_locked, _}, 2_000
    authorization = Task.async(fn -> F.evaluate() end)
    reference = authorization.ref
    refute_receive {^reference, _}, 20
    send(writer.pid, :commit_writer)
    assert {:ok, _} = Task.await(writer)
    assert {:ok, %{project_revision: 2}} = Task.await(authorization)
  end

  test "500ms lock timeout returns unavailable and releases transaction context" do
    parent = self()
    writer = Task.async(fn -> F.writer(5, fn -> :ok end, parent, true) end)
    assert_receive {:writer_locked, _}, 2_000
    started = System.monotonic_time(:millisecond)
    assert {:error, :authorization_unavailable} = F.evaluate()
    elapsed = System.monotonic_time(:millisecond) - started
    assert elapsed >= 450 and elapsed < 1_500
    send(writer.pid, :commit_writer)
    assert {:ok, _} = Task.await(writer)
    assert [[0]] = F.runtime_sql("SELECT count(*) FROM public.mixer_authz_memberships").rows
    assert {:ok, _} = F.evaluate()
  end

  test "foreign-key role lifecycle and parent constraints reject malformed durable state" do
    for sql <- [
          "UPDATE public.mixer_authz_memberships SET role='publisher' WHERE id='member'",
          "UPDATE public.mixer_authz_memberships SET project_binding='all_projects' WHERE id='member'",
          "UPDATE public.mixer_authz_memberships SET project_id='missing' WHERE id='member'",
          "UPDATE public.mixer_authz_environments SET application_id='app-b' WHERE organization_id='org-a' AND project_id='project-a'",
          "UPDATE public.mixer_authz_credentials SET family_id='other-family' WHERE profile_id='profile'",
          "UPDATE public.mixer_authz_bindings SET principal_id='service' WHERE profile_id='profile'",
          "UPDATE public.mixer_authz_families SET expires_at=0 WHERE id='family'"
        ],
        do: assert_raise(Postgrex.Error, fn -> F.sql(sql) end)
  end

  defp revocations do
    [
      {0,
       fn -> F.sql("UPDATE public.mixer_authz_profiles SET active=false WHERE id='profile'") end,
       {:error, :unauthenticated}},
      {1,
       fn ->
         F.sql(
           "UPDATE public.mixer_authz_principals SET active=false,revision=revision+1 WHERE id='person'"
         )
       end, {:error, :unauthenticated}},
      {2,
       fn ->
         F.sql(
           "UPDATE public.mixer_authz_families SET active=false,revision=revision+1 WHERE id='family'"
         )
       end, {:error, :unauthenticated}},
      {3,
       fn ->
         F.sql(
           "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE profile_id='profile'"
         )
       end, {:error, :unauthenticated}},
      {4,
       fn ->
         F.sql(
           "UPDATE public.mixer_authz_memberships SET active=false,revision=revision+1 WHERE id='member'"
         )

         F.sql(
           "UPDATE public.mixer_authz_organization_heads SET revision=revision+1 WHERE organization_id='org-a'"
         )
       end, {:error, :not_found}},
      {5,
       fn ->
         F.sql(
           "UPDATE public.mixer_authz_memberships SET active=false,revision=revision+1 WHERE id='member'"
         )

         F.sql(
           "UPDATE public.mixer_authz_project_heads SET revision=revision+1 WHERE organization_id='org-a' AND project_id='project-a'"
         )
       end, {:error, :not_found}}
    ]
  end
end
