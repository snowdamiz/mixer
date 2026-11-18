Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.WorkspaceSupportHTTPTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.BrowserAuth.{ActiveWorkspaceSchema, RuntimeOwner}
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.CustomerWorkspace.{SelfServiceSchema, SupportSchema}
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB

  @endpoint "/console-api/v1/support-requests"
  @id "4055a728-2588-408c-9952-29920c07ba67"

  setup_all do
    c = prepare!(:workspace_manage)
    path = Path.expand("../../../priv/repo/migrations", __DIR__)

    for version <- [
          20_261_025_000_001,
          20_261_025_000_002,
          20_261_116_000_001,
          20_261_117_000_000,
          20_261_118_000_000,
          20_261_118_000_002,
          20_261_118_000_010
        ] do
      [file] = Path.wildcard(Path.join(path, "#{version}_*.exs"))
      [{module, _}] = Code.require_file(file)
      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    conn = DB.connection!("browser_admin")

    try do
      for sql <-
            SelfServiceSchema.provisioning_statements("browser_ordinary") ++
              ActiveWorkspaceSchema.provisioning_statements("browser_ordinary") do
        Postgrex.query!(conn, sql, [])
      end
    after
      GenServer.stop(conn)
    end

    DB.q!(
      Migration,
      "REVOKE EXECUTE ON FUNCTION public.mixer_billing_organization_sync() FROM PUBLIC"
    )

    DB.q!(Migration, SupportSchema.grant_statement("browser_ordinary"))
    start!(c)
  end

  test "a free member can create, recover and reread a request within the member's tenant", c do
    assert RuntimeOwner.status().phase == :storage_ready
    assert c.hosted.processor_profile == nil
    preauth = bootstrap_http(c)
    login = begin_http(c, preauth)
    response = http(c, "/auth/callback?" <> login.query, login.headers)
    assert response.status == 303
    cookie = response_cookie(response)
    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    identity = {cookie, Jason.decode!(session.body)["csrf_token"]}

    org_response = post(c, identity, "/console-api/v1/orgs", %{display_name: "Support test"})
    assert org_response.status == 201
    assert %{"id" => org, "plan" => "free"} = Jason.decode!(org_response.body)

    assert DB.q!(
             Admin,
             "SELECT active FROM mixer_billing_organization_state WHERE organization_id=$1",
             [org]
           ).rows == [[true]]

    body = %{
      operation: "submit",
      organization_id: org,
      request_id: @id,
      subject: "Build fails after import",
      message: "Steps:\nImport a project and open the build form."
    }

    usage =
      post(c, identity, "/console-api/v1/workspace-admin", %{
        operation: "usage",
        organization_id: org
      })

    assert usage.status == 200
    assert %{"plan" => "free", "builds" => 0} = Jason.decode!(usage.body)

    list = %{operation: "list", organization_id: org}
    assert post(c, {"bad-cookie", elem(identity, 1)}, @endpoint, body).status in [400, 401]
    assert post(c, {cookie, String.duplicate("B", 43)}, @endpoint, body).status == 403
    assert post(c, identity, @endpoint, Map.put(body, :principal_id, "other")).status == 400

    assert post(c, identity, @endpoint, %{body | message: String.duplicate("é", 901)}).status ==
             400

    assert post(c, identity, @endpoint, %{body | organization_id: "org-b"}).status == 404
    assert post(c, identity, @endpoint, %{list | organization_id: "org-b"}).status == 404
    assert post(c, identity, @endpoint, %{list | organization_id: "missing"}).status == 404

    created = post(c, identity, @endpoint, body)
    assert created.status == 201
    assert response_header(created, "cache-control") == ["no-store"]

    assert %{"organization_id" => ^org, "request" => %{"id" => @id} = row} =
             Jason.decode!(created.body)

    assert row["message"] == body.message
    assert post(c, identity, @endpoint, body).body == created.body
    assert post(c, identity, @endpoint, %{body | subject: "Different subject"}).status == 409

    assert DB.q!(
             Admin,
             "SELECT organization_id, principal_id, request_id FROM mixer_support_requests"
           ).rows ==
             [[org, "person-1", @id]]

    DB.q!(Admin, "INSERT INTO mixer_authz_principals VALUES('person-2','human',true,0,1)")

    DB.q!(
      Admin,
      "INSERT INTO mixer_authz_memberships VALUES('member-other','person-2',$1,NULL,'all_projects','developer',true,0,NULL,1)",
      [org]
    )

    DB.q!(
      Admin,
      """
      INSERT INTO mixer_support_requests (organization_id,principal_id,request_id,subject,message)
      VALUES ($1,'person-2',$2,'Another member','Private'),('org-b','person-1',$2,'Another tenant','Private')
      """,
      [org, @id]
    )

    history = post(c, identity, @endpoint, list)
    assert history.status == 200
    assert %{"organization_id" => ^org, "requests" => [^row]} = Jason.decode!(history.body)

    empty = post(c, identity, @endpoint, %{list | organization_id: "org-a"})
    assert empty.status == 200
    assert %{"requests" => []} = Jason.decode!(empty.body)
    assert post(c, identity, @endpoint, %{body | organization_id: "org-a"}).status == 201

    DB.q!(Admin, "UPDATE mixer_authz_memberships SET active=false WHERE id='member-a'")
    assert post(c, identity, @endpoint, %{list | organization_id: "org-a"}).status == 404
    assert post(c, identity, @endpoint, %{body | organization_id: "org-a"}).status == 404

    assert DB.q!(Admin, "SELECT count(*) FROM mixer_support_requests").rows == [[4]]
    assert DB.q!(Admin, "SELECT count(*) FROM oban_jobs").rows == [[0]]
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
end
