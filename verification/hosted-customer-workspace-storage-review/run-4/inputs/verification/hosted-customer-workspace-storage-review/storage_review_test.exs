defmodule MixerHosted.CustomerWorkspace.StorageReviewTest do
  use ExUnit.Case, async: false
  alias MixerHosted.CustomerWorkspace, as: Workspace
  alias MixerHosted.CustomerWorkspace.Fixture, as: F
  alias MixerHosted.CustomerWorkspace.Fixture.{Admin, Migration, Runtime}
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.Schema
  @page %{limit: 50, cursor: nil}

  setup_all do
    Logger.configure(level: :warning)

    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_WORKSPACE_TEST_PORT")),
      database: "mixer_customer_workspace_review",
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

    start_supervised!(
      {Runtime,
       settings ++
         [username: "workspace_runtime", pool_size: 4, telemetry_prefix: [:workspace_probe]]}
    )

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage},
          {20_261_025_000_006, MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery}
        ],
        do: assert(:ok = Ecto.Migrator.up(Migration, version, module, log: false))

    for name <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{name} TO workspace_runtime")

    for name <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO workspace_runtime"
          )

    F.sql(
      "CREATE TABLE public.workspace_commit_probe (id integer UNIQUE DEFERRABLE INITIALLY DEFERRED)"
    )

    F.sql("GRANT INSERT ON public.workspace_commit_probe TO workspace_runtime")

    for name <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{name} TO workspace_runtime")

    F.sql(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO workspace_runtime"
    )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO workspace_runtime"
          )

    :ok
  end

  setup do
    F.sql(
      "TRUNCATE public.mixer_customer_idempotency,public.mixer_customer_audit_events,public.mixer_customer_artifacts,public.mixer_customer_artifact_heads CASCADE"
    )

    F.seed!()
    :ok
  end

  defp orgs(page \\ @page, identity \\ F.identity()),
    do: Workspace.organizations(identity, page, Runtime)

  defp projects(page \\ @page, identity \\ F.identity()),
    do: Workspace.projects(identity, "org-a", page, Runtime)

  defp new_org(id, project, membership) do
    F.sql("INSERT INTO public.mixer_authz_organizations(id,active) VALUES ($1,true)", [id])

    F.sql(
      "INSERT INTO public.mixer_authz_projects(organization_id,id,active) VALUES ($1,$2,true)",
      [id, project]
    )

    F.sql("INSERT INTO public.mixer_authz_organization_heads VALUES ($1,1)", [id])
    F.sql("INSERT INTO public.mixer_authz_project_heads VALUES ($1,$2,1)", [id, project])
    F.member(membership, id, project, "exact_project", "viewer")
  end

  defp paused(fun) do
    parent = self()
    key = {__MODULE__, make_ref()}

    :telemetry.attach(
      key,
      [:workspace_probe, :query],
      fn _, _, metadata, _ ->
        if metadata.query == "SELECT 1" and Process.delete(:storage_review_pause) do
          send(parent, {:storage_review_paused, self()})

          receive do
            :release_storage_review -> :ok
          after
            3_000 -> raise "independent reader not released"
          end
        end
      end,
      nil
    )

    task =
      Task.async(fn ->
        Process.put(:storage_review_pause, true)
        fun.()
      end)

    assert_receive {:storage_review_paused, pid}, 2_000

    on_exit(fn ->
      :telemetry.detach(key)
      send(pid, :release_storage_review)
    end)

    {task, pid, key}
  end

  defp release({task, pid, key}) do
    send(pid, :release_storage_review)
    result = Task.await(task)
    :telemetry.detach(key)
    result
  end

  defp tuple_blocked?(table, condition, params) do
    error =
      assert_raise Postgrex.Error, fn ->
        Admin.transaction(fn ->
          F.sql("SELECT 1 FROM public.#{table} WHERE #{condition} FOR UPDATE NOWAIT", params)
        end)
      end

    assert error.postgres.code == :lock_not_available
    true
  end

  test "raw directory SELECT guards require every exact identity and context field and isolate actors" do
    for changes <- [
          [profile_id: "unknown"],
          [profile_version: "2"],
          [issuer: "foreign"],
          [client_id: "foreign"],
          [subject: "other"],
          [principal_id: "other"],
          [family_id: "other-family"],
          [credential_ref: "other-token"],
          [identity_class: "service"],
          [token_issued_at: Integer.to_string(F.now() + 60)],
          [token_expires_at: "1"],
          [action: "artifact.read"],
          [required_scope: "mixer.artifact.read"],
          [phase: "directory_lock"],
          [directory_mode: ""],
          [directory_mode: "other"],
          [organization_id: "org-b"],
          [project_id: "project-a"],
          [application_id: "app"],
          [environment_id: "env"]
        ] do
      assert {:ok, :ok} =
               Runtime.transaction(fn ->
                 F.context("organizations", changes)

                 for table <- ~w(organizations projects memberships) do
                   assert F.runtime("SELECT count(*) FROM public.mixer_authz_#{table}").rows == [
                            [0]
                          ],
                          inspect(changes)
                 end

                 :ok
               end)
    end

    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               F.context("projects")

               assert F.runtime("SELECT organization_id,id FROM public.mixer_authz_projects").rows ==
                        [["org-a", "project-a"]]

               assert F.runtime("SELECT id FROM public.mixer_authz_memberships").rows == [
                        ["member"]
                      ]

               for table <- ~w(artifacts audit_events idempotency artifact_heads),
                   do:
                     assert(
                       F.runtime("SELECT count(*) FROM public.mixer_customer_#{table}").rows == [
                         [0]
                       ]
                     )

               :ok
             end)

    assert {:ok, %{organizations: [%{id: "org-b"}]}} =
             orgs(@page, F.identity(%{subject: "other", credential_ref: "other-token"}))
  end

  test "migration6 adds only SELECT directory policies and preserves FORCE RLS owners ACL and fixed helpers" do
    assert F.sql(
             "SELECT tablename,cmd FROM pg_policies WHERE schemaname='public' AND policyname='directory_read' ORDER BY tablename"
           ).rows == [
             ["mixer_authz_memberships", "SELECT"],
             ["mixer_authz_organizations", "SELECT"],
             ["mixer_authz_projects", "SELECT"]
           ]

    assert [[12, true]] =
             F.sql("""
             SELECT count(*),bool_and(c.relrowsecurity AND c.relforcerowsecurity AND NOT o.rolcanlogin AND NOT o.rolsuper AND NOT o.rolbypassrls
               AND NOT EXISTS(SELECT 1 FROM aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a WHERE a.grantee=0)
               AND has_table_privilege('workspace_runtime',c.oid,'SELECT') AND NOT has_table_privilege('workspace_runtime',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
             FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles o ON o.oid=c.relowner
             WHERE n.nspname='public' AND c.relname LIKE 'mixer_authz_%' AND c.relkind='r'
             """).rows

    assert [[6, true]] =
             F.sql("""
             SELECT count(*),bool_and(p.prosecdef AND p.pronargs=0 AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
               AND NOT o.rolcanlogin AND NOT o.rolsuper AND NOT o.rolbypassrls
               AND NOT EXISTS(SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0)
               AND has_function_privilege('workspace_runtime',p.oid,'EXECUTE'))
             FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles o ON o.oid=p.proowner
             WHERE n.nspname='public' AND p.proname LIKE 'mixer_authz_lock_%'
             """).rows

    for statement <- [
          "INSERT INTO public.mixer_authz_organizations(id,active) VALUES ('new',true)",
          "UPDATE public.mixer_authz_memberships SET active=false",
          "DELETE FROM public.mixer_authz_projects"
        ] do
      error = assert_raise Postgrex.Error, fn -> F.runtime(statement) end
      assert error.postgres.code == :insufficient_privilege
    end
  end

  test "returned and lookahead organizations hold exact identity and tenant tuple locks through commit" do
    new_org("org-c", "witness-c", "member-c")
    hold = paused(fn -> orgs(%{limit: 1, cursor: nil}) end)

    for {table, condition, params} <- [
          {"mixer_authz_profiles", "id=$1 AND version=1", ["profile"]},
          {"mixer_authz_principals", "id=$1", ["person"]},
          {"mixer_authz_families", "id=$1", ["family"]},
          {"mixer_authz_credentials", "reference=$1", ["token"]},
          {"mixer_authz_organization_heads", "organization_id=$1", ["org-a"]},
          {"mixer_authz_organization_heads", "organization_id=$1", ["org-c"]},
          {"mixer_authz_project_heads", "organization_id=$1 AND project_id=$2",
           ["org-a", "project-a"]},
          {"mixer_authz_project_heads", "organization_id=$1 AND project_id=$2",
           ["org-c", "witness-c"]}
        ],
        do: assert(tuple_blocked?(table, condition, params))

    assert {:ok, [[1]]} =
             Admin.transaction(fn ->
               F.sql(
                 "SELECT 1 FROM public.mixer_authz_organization_heads WHERE organization_id='org-b' FOR UPDATE NOWAIT"
               ).rows
             end)

    assert {:ok, %{organizations: [%{id: "org-a"}], next_cursor: cursor}} = release(hold)
    assert is_binary(cursor)

    assert {:ok, [[1]]} =
             Admin.transaction(fn ->
               F.sql(
                 "SELECT 1 FROM public.mixer_authz_project_heads WHERE organization_id='org-c' FOR UPDATE NOWAIT"
               ).rows
             end)
  end

  test "maximum project page locks 101 candidates and one outside visibility witness without a global membership cap" do
    F.sql("DELETE FROM public.mixer_authz_memberships WHERE principal_id='person'")

    F.sql(
      "INSERT INTO public.mixer_authz_projects(organization_id,id,active) SELECT 'org-a','p-'||lpad(n::text,3,'0'),true FROM generate_series(1,105) n"
    )

    F.sql(
      "INSERT INTO public.mixer_authz_project_heads SELECT organization_id,id,1 FROM public.mixer_authz_projects WHERE id LIKE 'p-%'"
    )

    F.sql(
      "INSERT INTO public.mixer_authz_memberships SELECT 'm-'||id,'person',organization_id,id,'exact_project','viewer',true,0,NULL,1 FROM public.mixer_authz_projects WHERE id LIKE 'p-%'"
    )

    F.member("aaa-outside", "org-a", "project-b", "exact_project", "developer")
    hold = paused(fn -> projects(%{limit: 100, cursor: nil}) end)
    assert tuple_blocked?("mixer_authz_organization_heads", "organization_id=$1", ["org-a"])

    for n <- 1..101 do
      id = "p-" <> String.pad_leading(Integer.to_string(n), 3, "0")

      assert tuple_blocked?("mixer_authz_project_heads", "organization_id=$1 AND project_id=$2", [
               "org-a",
               id
             ])
    end

    assert tuple_blocked?("mixer_authz_project_heads", "organization_id=$1 AND project_id=$2", [
             "org-a",
             "project-b"
           ])

    assert {:ok, [[1]]} =
             Admin.transaction(fn ->
               F.sql(
                 "SELECT 1 FROM public.mixer_authz_project_heads WHERE organization_id='org-a' AND project_id='p-102' FOR UPDATE NOWAIT"
               ).rows
             end)

    assert {:ok, %{projects: rows, next_cursor: cursor}} = release(hold)
    assert length(rows) == 100 and is_binary(cursor)
    assert Enum.all?(rows, &(&1.roles == ["viewer"]))
  end

  test "fresh locked reread returns a name committed behind its selected organization head" do
    parent = self()

    writer =
      Task.async(fn ->
        F.held_writer(
          "organization_heads",
          "org-a",
          nil,
          fn ->
            F.sql(
              "UPDATE public.mixer_authz_organizations SET display_name=$1 WHERE id='org-a'",
              ["Fresh * 名称"]
            )
          end,
          parent
        )
      end)

    assert_receive {:writer_locked, pid}
    reader = Task.async(fn -> orgs() end)
    assert F.eventually(&F.reader_waiting?/0)
    send(pid, :commit)
    assert {:ok, _} = Task.await(writer)
    assert {:ok, %{organizations: [%{display_name: "Fresh * 名称"}]}} = Task.await(reader)
  end

  test "family expiration during actual selected head wait fails identity before disclosure" do
    phase = rem(System.system_time(:millisecond), 1000)
    Process.sleep(rem(650 - phase + 1000, 1000))
    expiry = F.now() + 1
    F.sql("UPDATE public.mixer_authz_families SET expires_at=$1 WHERE id='family'", [expiry])
    parent = self()

    writer =
      Task.async(fn ->
        F.held_writer("project_heads", "org-a", "project-a", fn -> :ok end, parent)
      end)

    assert_receive {:writer_locked, pid}
    reader = Task.async(fn -> orgs() end)
    assert F.eventually(&F.reader_waiting?/0)
    delay = expiry * 1000 - System.system_time(:millisecond) + 2
    if delay > 0, do: Process.sleep(delay)
    send(pid, :commit)
    assert {:ok, _} = Task.await(writer)
    assert {:error, :unauthenticated} = Task.await(reader)
  end

  test "revoked selected lookahead never authorizes a cursor or partial page" do
    new_org("org-c", "witness-c", "member-c")
    parent = self()

    writer =
      Task.async(fn ->
        F.held_writer(
          "organization_heads",
          "org-c",
          nil,
          fn ->
            F.sql("UPDATE public.mixer_authz_organizations SET active=false WHERE id='org-c'")
          end,
          parent
        )
      end)

    assert_receive {:writer_locked, pid}
    reader = Task.async(fn -> orgs(%{limit: 1, cursor: nil}) end)
    assert F.eventually(&F.reader_waiting?/0)
    send(pid, :commit)
    assert {:ok, _} = Task.await(writer)
    assert {:error, :authorization_unavailable} = Task.await(reader)

    assert {:ok, %{organizations: [%{id: "org-a"}], next_cursor: nil}} =
             orgs(%{limit: 1, cursor: nil})
  end

  test "directory facade owns its complete transaction and failure leaves context reusable" do
    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               assert {:error, :authorization_unavailable} = orgs()
               assert {:error, :authorization_unavailable} = projects()
               :ok
             end)

    Process.put({Runtime, :fault}, :commit_constraint)

    try do
      assert {:error, :authorization_unavailable} = orgs()
    after
      Process.delete({Runtime, :fault})
    end

    assert [[0]] = F.sql("SELECT count(*) FROM public.workspace_commit_probe").rows
    assert Process.get({MixerHosted.CustomerWorkspace.Storage, :active}) == nil
    refute Runtime.in_transaction?()
    refute MixerHosted.Authorization.Transaction.Context.active?()
    assert {:ok, %{projects: [%{id: "project-a"}]}} = projects()
  end

  test "ordinary signed artifact upload read audit and replay still work under migration6 while workspace roles grant no artifact authority" do
    f =
      Path.expand("../../services/protocol/testdata/signed-release-v3.json", __DIR__)
      |> File.read!()
      |> Jason.decode!()

    roots = Enum.map(f["roots"], &Map.update!(&1, "public_key", fn v -> Base.decode64!(v) end))
    host = f["host"]
    envelope = Jason.encode!(Map.take(f, ~w(signed_manifest payload)))
    {:ok, checked} = MixerHosted.Protocol.ArtifactAdmission.admit(envelope, host, roots, F.now())

    F.sql(
      "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','fieldlog',true)"
    )

    F.sql(
      "INSERT INTO public.mixer_authz_environments VALUES ('org-a','project-a','fieldlog','development',true)"
    )

    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis("org-a", "project-a")

    F.sql(
      "INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)",
      [genesis]
    )

    previous = Application.fetch_env(:mixer_hosted, CustomerArtifacts)

    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      repo: Runtime,
      host: host,
      roots: roots
    })

    on_exit(fn ->
      case previous do
        {:ok, v} -> Application.put_env(:mixer_hosted, CustomerArtifacts, v)
        :error -> Application.delete_env(:mixer_hosted, CustomerArtifacts)
      end
    end)

    route = %{organization_id: "org-a", project_id: "project-a"}
    meta = %{reason: "independent migration6 ordinary flow", source_ip: nil}

    identity =
      F.identity(%{
        scopes:
          ~w(mixer.artifact.upload mixer.artifact.read mixer.audit.read mixer.workspace.read)
      })

    assert {:ok, %{status: 201} = first} =
             CustomerArtifacts.upload(identity, route, "review-upload", envelope, meta)

    assert {:ok, ^first} =
             CustomerArtifacts.upload(identity, route, "review-upload", envelope, meta)

    assert {:ok, _} = CustomerArtifacts.read(identity, route, checked.manifest_sha256, meta)
    assert {:ok, _} = CustomerArtifacts.audit(identity, route, 0, 100, meta)

    assert [[1, 1, 1]] =
             F.sql(
               "SELECT (SELECT count(*) FROM public.mixer_customer_artifacts),(SELECT count(*) FROM public.mixer_customer_audit_events),(SELECT count(*) FROM public.mixer_customer_idempotency)"
             ).rows

    assert {:ok, :ok} =
             Runtime.transaction(fn ->
               F.context("projects")

               for table <- ~w(artifacts audit_events idempotency artifact_heads),
                   do:
                     assert(
                       F.runtime("SELECT count(*) FROM public.mixer_customer_#{table}").rows == [
                         [0]
                       ]
                     )

               :ok
             end)

    assert {:error, :permission_denied} =
             CustomerArtifacts.upload(F.identity(), route, "workspace-only", envelope, meta)

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='billing_manager',revision=revision+1 WHERE id='member'"
    )

    assert {:ok, %{projects: [%{roles: ["billing_manager"]}]}} = projects()

    assert {:error, :permission_denied} =
             CustomerArtifacts.upload(identity, route, "billing-denied", envelope, meta)

    assert {:error, :permission_denied} =
             CustomerArtifacts.read(identity, route, checked.manifest_sha256, meta)
  end
end
