Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.ApplicationRegistrationProofTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.BrowserAuth.RuntimeOwner
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.Repo.Migrations.AddWorkspaceApplicationRegistration
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB

  @apps "/console-api/v1/applications"
  @test_app "example.proof.app"
  @registration_migration 20_261_118_000_011

  setup_all do
    c = prepare!(:workspace_builds)
    provision_workspace!()
    install_create_surface()

    c
    |> put_in(
      [:hosted, Access.key(:create_repo)],
      Keyword.put(c.hosted.repo, :username, "mixer_build_create")
    )
    |> start!()
  end

  @tag timeout: 120_000
  test "owner registers a durable application through ordinary browser HTTP", c do
    assert RuntimeOwner.status().phase == :storage_ready
    assert c.hosted.processor_profile == nil
    assert c.hosted.oban[:queues] == false

    auth = login(c)
    org = create(c, auth, "/console-api/v1/orgs", %{display_name: "Registration HTTP owner"})

    project =
      create(c, auth, "/console-api/v1/projects", %{
        organization_id: org,
        display_name: "Empty HTTP project"
      })

    scope = %{organization_id: org, project_id: project}

    assert applications(c, auth, scope) == []
    assert project_rows(scope) == []

    payload = Map.put(scope, :application_id, @test_app)
    invalid_csrf = String.duplicate("A", 43)
    assert post(c, {elem(auth, 0), invalid_csrf}, @apps, payload).status == 403
    assert post(c, auth, @apps, %{payload | application_id: "invalid\n"}).status == 400
    assert post(c, auth, @apps, %{payload | project_id: "project-a"}).status == 404
    assert post(c, auth, @apps, Map.put(payload, :principal_id, "person-1")).status == 400
    assert project_rows(scope) == []

    viewer = %{organization_id: "org-a", project_id: "project-a"}
    assert applications(c, auth, viewer) == [%{"applicationId" => "fieldlog"}]
    assert post(c, auth, @apps, Map.put(viewer, :application_id, @test_app)).status == 403
    assert project_rows(viewer) == [["fieldlog", true]]

    assert post(c, auth, @apps, %{payload | organization_id: "org-b", project_id: "project-b"}).status ==
             404

    first = post(c, auth, @apps, payload)
    assert first.status == 201
    assert response_header(first, "cache-control") == ["no-store"]
    assert Jason.decode!(first.body) == Map.new(payload, fn {k, v} -> {Atom.to_string(k), v} end)

    repeated = post(c, auth, @apps, payload)
    assert {repeated.status, repeated.body} == {first.status, first.body}

    assert post(c, auth, @apps, %{payload | application_id: "example.second.app"}).status == 409
    assert project_rows(scope) == [[@test_app, true]]

    assert revision(scope) == 2

    assert applications(c, login(c), scope) == [%{"applicationId" => @test_app}]

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(
               MixerHosted.Repo,
               "INSERT INTO public.mixer_authz_applications VALUES($1,$2,'outside-command',true)",
               [org, project]
             )

    race_project =
      create(c, auth, "/console-api/v1/projects", %{
        organization_id: org,
        display_name: "Concurrent registration project"
      })

    race_scope = %{scope | project_id: race_project}
    race_ids = ["example.race.one", "example.race.two"]
    sessions = [auth, login(c)]

    attempts =
      Enum.zip(sessions, race_ids)
      |> Task.async_stream(
        fn {session, id} ->
          {id, post(c, session, @apps, Map.put(race_scope, :application_id, id))}
        end,
        timeout: 15_000
      )
      |> Enum.map(fn {:ok, result} -> result end)

    assert Enum.sort(Enum.map(attempts, fn {_id, response} -> response.status end)) == [201, 409]

    [{winner, committed}] =
      Enum.filter(attempts, fn {_id, response} -> response.status == 201 end)

    assert project_rows(race_scope) == [[winner, true]]
    assert revision(race_scope) == 2
    repeated_race = post(c, auth, @apps, Map.put(race_scope, :application_id, winner))
    assert {repeated_race.status, repeated_race.body} == {201, committed.body}

    retired_project =
      create(c, auth, "/console-api/v1/projects", %{
        organization_id: org,
        display_name: "Reserved application ID project"
      })

    retired_scope = %{scope | project_id: retired_project}

    DB.q!(
      Admin,
      "INSERT INTO public.mixer_authz_applications VALUES($1,$2,'example.retired',false)",
      [
        org,
        retired_project
      ]
    )

    assert post(c, auth, @apps, Map.put(retired_scope, :application_id, "example.retired")).status ==
             409

    assert project_rows(retired_scope) == [["example.retired", false]]
    assert revision(retired_scope) == 1

    before = retained_rows()
    assert application_grants() == [[true, true, 2]]

    assert :ok =
             Ecto.Migrator.down(
               Admin,
               @registration_migration,
               AddWorkspaceApplicationRegistration,
               log: false
             )

    assert application_grants() == [[false, false, 0]]
    assert retained_rows() == before
    assert post(c, auth, @apps, payload).status == 503
    assert applications(c, auth, scope) == [%{"applicationId" => @test_app}]
    assert applications(c, auth, viewer) == [%{"applicationId" => "fieldlog"}]

    assert :ok =
             Ecto.Migrator.up(Admin, @registration_migration, AddWorkspaceApplicationRegistration,
               log: false
             )

    assert application_grants() == [[true, true, 2]]
    assert retained_rows() == before
    after_upgrade = post(c, auth, @apps, payload)
    assert {after_upgrade.status, after_upgrade.body} == {201, first.body}
    assert revision(scope) == 2

    for table <- ~w(mixer_builds oban_jobs mixer_customer_build_inputs),
        do: assert(DB.q!(Admin, "SELECT count(*) FROM public." <> table).rows == [[0]])
  end

  defp install_create_surface do
    case DB.q!(Admin, """
         SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication
         FROM pg_roles WHERE rolname='mixer_build_create'
         """).rows do
      [] ->
        DB.q!(Admin, """
        CREATE ROLE mixer_build_create LOGIN NOSUPERUSER NOBYPASSRLS
          NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION
        """)

      [[true, false, false, false, false, false, false]] ->
        :ok
    end

    DB.q!(Admin, "GRANT USAGE ON SCHEMA public TO mixer_build_create")

    tables =
      ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)

    relations = Enum.map_join(tables, ",", &("public.mixer_authz_" <> &1))
    DB.q!(Admin, "GRANT SELECT ON " <> relations <> " TO mixer_build_create")

    for helper <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          DB.q!(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO mixer_build_create"
          )

    for sql <-
          MixerHosted.CustomerBuilds.CreateSchema.statements() ++
            MixerHosted.BrowserAuth.ActiveCreateSchema.statements(),
        do: DB.q!(Migration, sql)

    signature =
      "public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence)"

    DB.q!(Admin, "GRANT CREATE ON SCHEMA public TO browser_writer")
    DB.q!(Admin, "ALTER FUNCTION #{signature} OWNER TO browser_writer")
    DB.q!(Admin, "REVOKE CREATE ON SCHEMA public FROM browser_writer")
    DB.q!(Admin, "GRANT EXECUTE ON FUNCTION #{signature} TO mixer_build_create")
  end

  defp login(c) do
    attempt = begin_http(c, bootstrap_http(c))
    callback = http(c, "/auth/callback?" <> attempt.query, attempt.headers)
    assert callback.status == 303
    cookie = response_cookie(callback)
    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    {cookie, Jason.decode!(session.body)["csrf_token"]}
  end

  defp create(c, auth, path, body) do
    result = post(c, auth, path, body)
    assert result.status == 201
    Jason.decode!(result.body)["id"]
  end

  defp post(c, {cookie, csrf}, path, body) do
    raw = Jason.encode!(body)

    http(
      c,
      path,
      headers(cookie) ++
        [
          {"origin", c.config.public_origin},
          {"x-mixer-csrf", csrf},
          {"content-type", "application/json"},
          {"content-length", Integer.to_string(byte_size(raw))}
        ],
      "POST",
      raw
    )
  end

  defp applications(c, {cookie, _csrf}, scope) do
    result = http(c, @apps <> "?" <> URI.encode_query(scope), headers(cookie))
    assert result.status == 200
    Jason.decode!(result.body)["applications"]
  end

  defp project_rows(scope) do
    DB.q!(
      Admin,
      "SELECT id,active FROM public.mixer_authz_applications WHERE organization_id=$1 AND project_id=$2 ORDER BY id",
      [scope.organization_id, scope.project_id]
    ).rows
  end

  defp revision(scope) do
    [[revision]] =
      DB.q!(
        Admin,
        "SELECT revision FROM mixer_authz_project_heads WHERE organization_id=$1 AND project_id=$2",
        [scope.organization_id, scope.project_id]
      ).rows

    revision
  end

  defp retained_rows do
    for table <-
          ~w(mixer_authz_organizations mixer_authz_projects mixer_authz_memberships mixer_authz_applications mixer_authz_organization_heads mixer_authz_project_heads) do
      DB.q!(Admin, "SELECT to_jsonb(r) FROM public." <> table <> " r ORDER BY to_jsonb(r)::text").rows
    end
  end

  defp application_grants do
    DB.q!(Admin, """
    SELECT has_table_privilege('mixer_workspace_writer','public.mixer_authz_applications','SELECT'),
           has_table_privilege('mixer_workspace_writer','public.mixer_authz_applications','INSERT'),
           (SELECT count(*) FROM pg_policies WHERE schemaname='public'
            AND tablename='mixer_authz_applications' AND policyname IN
              ('workspace_application_read','workspace_application_insert'))
    """).rows
  end
end
