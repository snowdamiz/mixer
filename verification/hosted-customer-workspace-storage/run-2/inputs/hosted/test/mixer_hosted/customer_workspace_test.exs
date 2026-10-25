defmodule MixerHosted.CustomerWorkspace.Fixture.Admin do
  use Ecto.Repo, otp_app: :workspace_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerWorkspace.Fixture.Migration do
  use Ecto.Repo, otp_app: :workspace_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerWorkspace.Fixture.Runtime do
  use Ecto.Repo, otp_app: :workspace_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerWorkspace.Fixture do
  alias MixerHosted.CustomerWorkspace.Fixture.{Admin, Runtime}
  alias MixerHosted.Identity.VerifiedIdentity
  def sql(sql, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, sql, params, log: false)
  def runtime(sql, params \\ []), do: Ecto.Adapters.SQL.query!(Runtime, sql, params, log: false)
  def now, do: System.system_time(:second)

  def identity(changes \\ %{}) do
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
          scopes: ["mixer.workspace.read"]
        },
        changes
      )
    )
  end

  def seed! do
    sql(
      "TRUNCATE public.mixer_authz_profiles, public.mixer_authz_principals, public.mixer_authz_organizations CASCADE"
    )

    for statement <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https://issuer.example','client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,1),('other','human',true,0,1)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,'subject','human','person',true),('profile',1,'other','human','other',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,1),('other-family','profile',1,'other',true,0,NULL,1)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'token','person','family',true,0,NULL,1),('profile',1,'other-token','other','other-family',true,0,NULL,1)",
          "INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES ('org-a',true,'Team A'),('org-b',true,NULL),('org-inactive',false,'Inactive')",
          "INSERT INTO public.mixer_authz_projects(organization_id,id,active,display_name) VALUES ('org-a','project-a',true,'Project A'),('org-a','project-b',true,NULL),('org-a','project-inactive',false,'Inactive'),('org-b','project-a',true,'Foreign'),('org-inactive','project-a',true,'Inactive org')",
          "INSERT INTO public.mixer_authz_organization_heads SELECT id,1 FROM public.mixer_authz_organizations",
          "INSERT INTO public.mixer_authz_project_heads SELECT organization_id,id,1 FROM public.mixer_authz_projects"
        ],
        do: sql(statement)

    member("member", "org-a", "project-a", "exact_project", "developer")
    member("foreign", "org-b", "project-a", "exact_project", "owner", "other")
    :ok
  end

  def member(id, org, project, binding, role, actor \\ "person") do
    sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ($1,$2,$3,$4,$5,$6,true,0,NULL,1)",
      [id, actor, org, project, binding, role]
    )
  end

  def context(mode, changes \\ []) do
    MixerHosted.Authorization.Postgres.Session.prepare_identity!(
      Runtime,
      MixerHosted.Authorization.Policy.identity_key(identity())
    )

    MixerHosted.Authorization.Postgres.Session.context!(
      Runtime,
      Keyword.merge(
        [
          directory_mode: mode,
          organization_id: if(mode == "projects", do: "org-a", else: nil),
          project_id: nil,
          application_id: nil,
          environment_id: nil,
          action: "workspace.read",
          required_scope: "mixer.workspace.read",
          phase: "directory",
          token_issued_at: Integer.to_string(now() - 20),
          token_expires_at: Integer.to_string(now() + 600)
        ],
        changes
      )
    )
  end

  def held_writer(table, org, project, mutation, parent) do
    Admin.transaction(fn ->
      sql("SELECT 1 FROM public.mixer_authz_organizations WHERE id = $1 FOR SHARE", [org])

      condition =
        if table == "organization_heads",
          do: "organization_id = $1",
          else: "organization_id = $1 AND project_id = $2"

      params = if table == "organization_heads", do: [org], else: [org, project]
      sql("SELECT 1 FROM public.mixer_authz_#{table} WHERE #{condition} FOR UPDATE", params)
      send(parent, {:writer_locked, self()})

      receive do
        :commit -> mutation.()
      after
        2_000 -> raise "writer not released"
      end
    end)
  end

  def reader_waiting? do
    sql(
      "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE usename = 'workspace_runtime' AND wait_event_type = 'Lock')"
    ).rows == [[true]]
  end

  def eventually(fun, left \\ 100)
  def eventually(fun, 0), do: fun.()

  def eventually(fun, left),
    do:
      if(fun.(),
        do: true,
        else:
          (
            Process.sleep(5)
            eventually(fun, left - 1)
          )
      )
end

defmodule MixerHosted.CustomerWorkspaceTest do
  use ExUnit.Case, async: false
  alias MixerHosted.CustomerWorkspace, as: Workspace
  alias MixerHosted.CustomerWorkspace.Input
  alias MixerHosted.CustomerWorkspace.Fixture, as: F
  alias MixerHosted.CustomerWorkspace.Fixture.{Admin, Migration, Runtime}
  @page %{limit: 50, cursor: nil}

  setup_all do
    Logger.configure(level: :warning)

    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_WORKSPACE_TEST_PORT")),
      database: "mixer_customer_workspace",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "workspace_fixture_admin", pool_size: 6]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "workspace_fixture_admin",
           pool_size: 2,
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE workspace_owner", []) end
         ]}
    )

    start_supervised!({Runtime, settings ++ [username: "workspace_runtime", pool_size: 4]})

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_006, MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery}
        ],
        do: assert(:ok = Ecto.Migrator.up(Migration, version, module, log: false))

    # Observe additive rollback and reapply on the owned disposable database.
    assert :ok =
             Ecto.Migrator.down(
               Migration,
               20_261_025_000_006,
               MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery,
               log: false
             )

    assert [[0]] =
             F.sql(
               "SELECT count(*) FROM information_schema.columns WHERE table_name IN ('mixer_authz_organizations','mixer_authz_projects') AND column_name = 'display_name'"
             ).rows

    assert :ok =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_006,
               MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery,
               log: false
             )

    if path = System.get_env("MIXER_WORKSPACE_MIGRATION_RESULT"),
      do:
        File.write!(
          path,
          Jason.encode!(%{apply: true, rollback: true, reapply: true, disposable: true})
        )

    for name <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{name} TO workspace_runtime")

    for name <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO workspace_runtime"
          )

    :ok
  end

  setup do
    F.seed!()
    :ok
  end

  defp orgs(identity \\ F.identity(), page \\ @page),
    do: Workspace.organizations(identity, page, Runtime)

  defp projects(org \\ "org-a", identity \\ F.identity(), page \\ @page),
    do: Workspace.projects(identity, org, page, Runtime)

  test "all six roles and three explicit binding modes have precise discovery semantics" do
    for role <- ~w(owner administrator developer release_manager billing_manager viewer),
        binding <- ~w(organization_only all_projects exact_project) do
      F.sql("DELETE FROM public.mixer_authz_memberships WHERE principal_id = 'person'")
      project = if binding == "exact_project", do: "project-a", else: nil
      F.member("selected", "org-a", project, binding, role)
      assert {:ok, %{organizations: [org], next_cursor: nil}} = orgs()
      assert org.id == "org-a"
      assert org.organization_roles == if(binding == "exact_project", do: [], else: [role])
      assert {:ok, %{projects: result, next_cursor: nil}} = projects()

      assert Enum.map(result, & &1.id) == case(binding) do
        "organization_only" -> []
        "all_projects" -> ["project-a", "project-b"]
        "exact_project" -> ["project-a"]
      end

      assert Enum.all?(result, &(&1.roles == [role] and &1.organization_id == "org-a"))
    end
  end

  test "role summaries are sorted unique and exact-project roles remain project scoped" do
    F.member("owner", "org-a", nil, "organization_only", "owner")
    F.member("viewer", "org-a", nil, "all_projects", "viewer")
    F.member("dev-again", "org-a", "project-a", "exact_project", "developer")
    assert {:ok, %{organizations: [%{organization_roles: ["owner", "viewer"]}]}} = orgs()
    assert {:ok, %{projects: [a, b]}} = projects()
    assert a.roles == ["developer", "viewer"]
    assert b.roles == ["viewer"]
  end

  test "inactive exact project identifies its active organization without project visibility" do
    F.sql("UPDATE public.mixer_authz_projects SET active = false WHERE organization_id = 'org-a'")
    assert {:ok, %{organizations: [%{id: "org-a"}], next_cursor: nil}} = orgs()
    assert {:ok, %{projects: [], next_cursor: nil}} = projects()
    F.sql("UPDATE public.mixer_authz_organizations SET active = false WHERE id = 'org-a'")
    assert {:ok, %{organizations: []}} = orgs()
    assert {:error, :not_found} = projects()
  end

  test "foreign and missing organizations are indistinguishable and no membership yields empty directory" do
    assert {:error, :not_found} = projects("org-b")
    assert {:error, :not_found} = projects("missing")
    assert {:error, :not_found} = projects("org-inactive")
    F.sql("DELETE FROM public.mixer_authz_memberships WHERE principal_id = 'person'")
    assert {:ok, %{organizations: [], next_cursor: nil}} = orgs()
  end

  test "strict human identity and exact new token scope precede database work" do
    for scopes <- [[], ["mixer.artifact.read"], ["mixer.workspace.read.extra"], ["*"]],
        do: assert({:error, :permission_denied} = orgs(F.identity(%{scopes: scopes})))

    assert {:error, :permission_denied} = orgs(F.identity(%{identity_class: :service}))

    for i <- [
          Map.from_struct(F.identity()),
          Map.put(F.identity(), :extra, true),
          F.identity(%{expires_at: F.now()}),
          F.identity(%{issued_at: F.now() + 31}),
          F.identity(%{scopes: ["mixer.workspace.read", "mixer.workspace.read"]}),
          F.identity(%{scopes: ["mixer.workspace.read" | :bad]})
        ],
        do: assert({:error, :unauthenticated} = orgs(i))

    assert {:error, :permission_denied} =
             Workspace.organizations(F.identity(%{scopes: []}), @page, MissingRepo)
  end

  test "every current identity revoke fence rejects and unknown credentials never bootstrap" do
    for mutation <- [
          "UPDATE public.mixer_authz_profiles SET active = false",
          "UPDATE public.mixer_authz_bindings SET active = false",
          "UPDATE public.mixer_authz_principals SET active = false WHERE id = 'person'",
          "UPDATE public.mixer_authz_families SET active = false WHERE id = 'family'",
          "UPDATE public.mixer_authz_credentials SET active = false WHERE reference = 'token'",
          "UPDATE public.mixer_authz_principals SET not_before = extract(epoch FROM clock_timestamp())::bigint WHERE id = 'person'",
          "UPDATE public.mixer_authz_families SET not_before = extract(epoch FROM clock_timestamp())::bigint WHERE id = 'family'",
          "UPDATE public.mixer_authz_credentials SET not_before = extract(epoch FROM clock_timestamp())::bigint WHERE reference = 'token'",
          "UPDATE public.mixer_authz_families SET expires_at = 1 WHERE id = 'family'",
          "UPDATE public.mixer_authz_credentials SET expires_at = 1 WHERE reference = 'token'"
        ] do
      F.seed!()
      F.sql(mutation)
      assert {:error, :unauthenticated} = orgs(), mutation
    end

    F.seed!()

    for changes <- [
          %{credential_ref: "missing"},
          %{subject: "missing"},
          %{issuer: "https://foreign.example"},
          %{client_id: "foreign"},
          %{profile_version: 2},
          %{credential_ref: "other-token"}
        ],
        do: assert({:error, :unauthenticated} = orgs(F.identity(changes)))
  end

  test "expired, future and inactive memberships disclose no workspace" do
    for predicate <- ["active = false", "expires_at = 1", "not_before = 9007199254740990"] do
      F.seed!()
      F.sql("UPDATE public.mixer_authz_memberships SET #{predicate} WHERE id = 'member'")
      assert {:ok, %{organizations: []}} = orgs()
      assert {:error, :not_found} = projects()
    end
  end

  test "actual nullable names are preserved and malformed stored names fail closed" do
    assert {:ok, %{organizations: [%{display_name: "Team A"}]}} = orgs()
    F.member("all", "org-a", nil, "all_projects", "viewer")
    assert {:ok, %{projects: [%{display_name: "Project A"}, %{display_name: nil}]}} = projects()

    F.sql("UPDATE public.mixer_authz_organizations SET display_name = $1 WHERE id = 'org-a'", [
      "  Équipe *  "
    ])

    assert {:ok, %{organizations: [%{display_name: "  Équipe *  "}]}} = orgs()

    for name <- ["bad\nname", "bad" <> <<127>>, "bad" <> <<0xC2, 0x85>>] do
      F.sql("UPDATE public.mixer_authz_organizations SET display_name = $1 WHERE id = 'org-a'", [
        name
      ])

      assert {:error, :authorization_unavailable} = orgs()
    end

    assert_raise Postgrex.Error, fn ->
      F.sql("UPDATE public.mixer_authz_organizations SET display_name = '' WHERE id = 'org-a'")
    end
  end

  test "full Scope IDs and C collation survive multi-page organization and project discovery" do
    F.sql("DELETE FROM public.mixer_authz_memberships WHERE principal_id = 'person'")
    ids = [".", "..", "a/b", "a:b", "a+b", "a%b", "quote'\"", "équipe", "日本"]

    for {id, index} <- Enum.with_index(ids) do
      F.sql("INSERT INTO public.mixer_authz_organizations(id,active) VALUES ($1,true)", [id])
      F.sql("INSERT INTO public.mixer_authz_organization_heads VALUES ($1,1)", [id])

      F.sql(
        "INSERT INTO public.mixer_authz_projects(organization_id,id,active) VALUES ($1,$1,true)",
        [id]
      )

      F.sql("INSERT INTO public.mixer_authz_project_heads VALUES ($1,$1,1)", [id])
      F.member("m#{index}", id, nil, "all_projects", "viewer")
      assert {:ok, %{projects: [%{id: ^id, organization_id: ^id}]}} = projects(id)
    end

    assert walk_orgs(nil, []) == Enum.sort(ids)

    assert {:ok, %{organizations: [], next_cursor: nil}} =
             orgs(F.identity(), %{limit: 2, cursor: Input.cursor("organizations", nil, "􏿿")})
  end

  test "projects paginate independently and bind cursors to exact organization" do
    F.member("all", "org-a", nil, "all_projects", "viewer")

    assert {:ok, %{projects: [%{id: "project-a"}], next_cursor: cursor}} =
             projects("org-a", F.identity(), %{limit: 1, cursor: nil})

    assert is_binary(cursor)

    assert {:ok, %{projects: [%{id: "project-b"}], next_cursor: nil}} =
             projects("org-a", F.identity(), %{limit: 1, cursor: cursor})

    assert {:error, :invalid_request} =
             projects("org-b", F.identity(), %{limit: 1, cursor: cursor})

    assert {:error, :invalid_request} = orgs(F.identity(), %{limit: 1, cursor: cursor})
  end

  test "closed bounded pagination rejects noncanonical and duplicate cursor JSON" do
    for page <- [
          %{},
          %{limit: 1},
          %{limit: 1, cursor: nil, extra: true},
          %{limit: 0, cursor: nil},
          %{limit: 101, cursor: nil},
          %{limit: "1", cursor: nil},
          %{limit: 1.0, cursor: nil},
          %{limit: 1, cursor: ""},
          %{limit: 1, cursor: String.duplicate("A", 1401)}
        ],
        do: assert({:error, :invalid_request} = orgs(F.identity(), page))

    for raw <- [
          ~s({"v":1,"kind":"organizations","after":"x","extra":true}),
          ~s({"v":1,"kind":"organizations","after":"x","after":"y"}),
          ~s({"v":1,"kind":"organizations","after":"x","\\u0061fter":"y"}),
          ~s({"kind":"organizations","v":1,"after":"x"}),
          ~s({"v":1, "kind":"organizations","after":"x"}),
          ~s({"v":1,"kind":"organizations","after":"\\u0078"}),
          ~s({"v":2,"kind":"organizations","after":"x"}),
          ~s({"v":1,"kind":"organizations","after":"*"})
        ] do
      assert {:error, :invalid_request} =
               orgs(F.identity(), %{limit: 1, cursor: Base.url_encode64(raw, padding: false)})
    end

    canonical = Input.cursor("organizations", nil, "x")
    assert {:error, :invalid_request} = orgs(F.identity(), %{limit: 1, cursor: canonical <> "="})
    assert {:error, :invalid_request} = projects("*")
  end

  test "directory RLS is closed by mode action phase scope identity and ordinary resource context" do
    for changes <- [
          [directory_mode: "bad"],
          [action: "artifact.read"],
          [required_scope: "mixer.artifact.read"],
          [phase: "effect"],
          [token_expires_at: "1"],
          [project_id: "project-a"],
          [organization_id: "org-a"]
        ] do
      assert {:ok, :ok} =
               Runtime.transaction(fn ->
                 F.context("organizations", changes)
                 assert F.runtime("SELECT id FROM public.mixer_authz_organizations").rows == []
                 assert F.runtime("SELECT id FROM public.mixer_authz_memberships").rows == []
                 :ok
               end)
    end

    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               F.context("organizations")

               assert F.runtime("SELECT id FROM public.mixer_authz_organizations").rows == [
                        ["org-a"]
                      ]

               assert F.runtime("SELECT id FROM public.mixer_authz_projects").rows == []
               assert F.runtime("SELECT id FROM public.mixer_authz_applications").rows == []

               assert F.runtime("SELECT id FROM public.mixer_authz_memberships").rows == [
                        ["member"]
                      ]

               :ok
             end)

    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               F.context("")
               assert F.runtime("SELECT id FROM public.mixer_authz_organizations").rows == []
               assert {:error, :authorization_unavailable} = orgs()
               :ok
             end)

    assert F.runtime("SELECT current_setting('mixer.authz.directory_mode',true)").rows in [
             [[nil]],
             [[""]]
           ]

    assert {:ok, %{organizations: [_]}} = orgs()
  end

  test "runtime has no mutation or bypass authority and topology violations suppress results" do
    assert_raise Postgrex.Error, fn ->
      F.runtime("UPDATE public.mixer_authz_organizations SET active = false")
    end

    F.sql("GRANT UPDATE ON public.mixer_authz_organizations TO workspace_runtime")

    try do
      assert {:error, :authorization_unavailable} = orgs()
    after
      F.sql("REVOKE UPDATE ON public.mixer_authz_organizations FROM workspace_runtime")
    end

    F.sql("ALTER TABLE public.mixer_authz_projects NO FORCE ROW LEVEL SECURITY")

    try do
      assert {:error, :authorization_unavailable} = orgs()
    after
      F.sql("ALTER TABLE public.mixer_authz_projects FORCE ROW LEVEL SECURITY")
    end

    assert {:error, :authorization_unavailable} =
             Workspace.organizations(F.identity(), @page, Admin)
  end

  test "committed selected project revocation during final head wait is freshly seen" do
    parent = self()

    writer =
      Task.async(fn ->
        F.held_writer(
          "project_heads",
          "org-a",
          "project-a",
          fn ->
            F.sql("UPDATE public.mixer_authz_memberships SET active = false WHERE id = 'member'")
          end,
          parent
        )
      end)

    assert_receive {:writer_locked, pid}
    reader = Task.async(fn -> projects() end)
    assert F.eventually(&F.reader_waiting?/0)
    send(pid, :commit)
    assert {:ok, _} = Task.await(writer)
    assert {:error, :authorization_unavailable} = Task.await(reader)
    assert {:error, :not_found} = projects()
  end

  test "committed selected organization revocation during head wait is freshly seen" do
    F.member("all", "org-a", nil, "all_projects", "viewer")
    parent = self()

    writer =
      Task.async(fn ->
        F.held_writer(
          "organization_heads",
          "org-a",
          nil,
          fn ->
            F.sql("UPDATE public.mixer_authz_organizations SET active = false WHERE id = 'org-a'")
          end,
          parent
        )
      end)

    assert_receive {:writer_locked, pid}
    reader = Task.async(fn -> orgs() end)
    assert F.eventually(&F.reader_waiting?/0)
    send(pid, :commit)
    assert {:ok, _} = Task.await(writer)
    assert {:error, :authorization_unavailable} = Task.await(reader)
  end

  test "missing selected heads and read errors are unavailable and next call is clean" do
    F.sql(
      "DELETE FROM public.mixer_authz_project_heads WHERE organization_id = 'org-a' AND project_id = 'project-a'"
    )

    assert {:error, :authorization_unavailable} = orgs()
    F.sql("INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',1)")
    assert {:ok, %{organizations: [_]}} = orgs()
    F.sql("REVOKE SELECT ON public.mixer_authz_memberships FROM workspace_runtime")

    try do
      assert {:error, :authorization_unavailable} = orgs()
    after
      F.sql("GRANT SELECT ON public.mixer_authz_memberships TO workspace_runtime")
    end

    assert {:ok, %{organizations: [_]}} = orgs()
  end

  defp walk_orgs(cursor, acc) do
    assert {:ok, %{organizations: rows, next_cursor: next}} =
             orgs(F.identity(), %{limit: 2, cursor: cursor})

    result = acc ++ Enum.map(rows, & &1.id)
    if next, do: walk_orgs(next, result), else: result
  end
end
