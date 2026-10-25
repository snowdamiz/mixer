defmodule MixerHosted.CustomerWorkspaceHTTPFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_workspace_http_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerWorkspaceHTTPFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_workspace_http_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerWorkspaceHTTPFixture do
  alias MixerHosted.CustomerWorkspaceHTTPFixture.Admin
  def sql(query, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, query, params, log: false)
  def now, do: System.system_time(:second)
  def sha(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  def seed! do
    sql(
      "TRUNCATE public.mixer_authz_profiles, public.mixer_authz_principals, public.mixer_authz_organizations CASCADE"
    )

    for statement <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('workspace-http-profile',1,'https://issuer.fixture.invalid/oauth','reviewed-client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,1),('other','human',true,0,1)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('workspace-http-profile',1,'subject','human','person',true),('workspace-http-profile',1,'other-subject','human','other',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('family','workspace-http-profile',1,'person',true,0,NULL,1),('other-family','workspace-http-profile',1,'other',true,0,NULL,1)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('workspace-http-profile',1,'token','person','family',true,0,NULL,1),('workspace-http-profile',1,'other-token','other','other-family',true,0,NULL,1)"
        ],
        do: sql(statement)

    organization("org-a", "  Team * A  ")
    organization("org-b", "Private Other Team")
    organization("org-inactive", "Inactive", false)
    project("org-a", "project-a", "Project A")
    project("org-a", "project-b", nil)
    project("org-a", "project-inactive", "Inactive", false)
    project("org-b", "project-a", "Private Foreign Project")
    member("member", "org-a", "project-a", "exact_project", "developer")
    member("foreign", "org-b", "project-a", "exact_project", "owner", "other")
    :ok
  end

  def organization(id, name \\ nil, active \\ true) do
    sql(
      "INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES ($1,$2,$3)",
      [id, active, name]
    )

    sql("INSERT INTO public.mixer_authz_organization_heads VALUES ($1,1)", [id])
  end

  def project(org, id, name \\ nil, active \\ true) do
    sql(
      "INSERT INTO public.mixer_authz_projects(organization_id,id,active,display_name) VALUES ($1,$2,$3,$4)",
      [org, id, active, name]
    )

    sql("INSERT INTO public.mixer_authz_project_heads VALUES ($1,$2,1)", [org, id])
  end

  def member(id, org, project, binding, role, actor \\ "person") do
    sql("INSERT INTO public.mixer_authz_memberships VALUES ($1,$2,$3,$4,$5,$6,true,0,NULL,1)", [
      id,
      actor,
      org,
      project,
      binding,
      role
    ])
  end

  def mutate(org, project, query, params \\ []) do
    Admin.transaction(fn ->
      sql(
        "SELECT 1 FROM public.mixer_authz_organization_heads WHERE organization_id=$1 FOR UPDATE",
        [org]
      )

      if project,
        do:
          sql(
            "SELECT 1 FROM public.mixer_authz_project_heads WHERE organization_id=$1 AND project_id=$2 FOR UPDATE",
            [org, project]
          )

      sql(query, params)
    end)
  end

  def record(value) do
    if directory = System.get_env("MIXER_WORKSPACE_HTTP_EVIDENCE"),
      do:
        File.write!(Path.join(directory, "requests.jsonl"), Jason.encode!(value) <> "\n", [
          :append
        ])
  end
end

defmodule MixerHostedWeb.CustomerWorkspaceHTTPIntegrationTest do
  use ExUnit.Case, async: false
  alias MixerHosted.CustomerWorkspaceHTTPFixture, as: F
  alias MixerHosted.CustomerWorkspaceHTTPFixture.{Admin, Migration}
  alias MixerHosted.Identity.{ConfiguredVerifier, KeyOwner, TLSFixture}

  @profile %{
    profile_id: "workspace-http-profile",
    profile_version: 1,
    issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api",
    client_id: "reviewed-client",
    identity_class: :human,
    enabled: true
  }

  setup_all do
    for app <- [:phoenix, :bandit, :ecto_sql, :postgrex, :jose, :mint, :ssl],
        do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_WORKSPACE_HTTP_TEST_PORT")),
      database: "mixer_customer_workspace_http",
      ssl: false,
      log: false
    ]

    start_supervised!(
      {Admin, settings ++ [username: "workspace_http_fixture_admin", pool_size: 3]}
    )

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "workspace_http_fixture_admin",
           pool_size: 2,
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE workspace_http_owner", []) end
         ]}
    )

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_006, MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery}
        ],
        do: assert(:ok = Ecto.Migrator.up(Migration, version, module, log: false))

    for name <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{name} TO workspace_http_runtime")

    for name <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO workspace_http_runtime"
          )

    assert Process.whereis(MixerHosted.Repo) == nil
    assert Process.whereis(KeyOwner) == nil
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil

    repo =
      start_supervised!(
        {MixerHosted.Repo,
         settings ++
           [
             username: "workspace_http_runtime",
             pool_size: 2,
             telemetry_prefix: [:workspace_http_default_repo],
             parameters: [application_name: "mixer-workspace-http-runtime"]
           ]}
      )

    assert [["workspace_http_runtime", false, false, false]] =
             Ecto.Adapters.SQL.query!(
               MixerHosted.Repo,
               "SELECT current_user,rolsuper,rolbypassrls,rolcreaterole FROM pg_roles WHERE rolname=current_user",
               [],
               log: false
             ).rows

    fixture = start_supervised!(TLSFixture)
    authority = GenServer.call(fixture, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "workspace-http-key", "alg" => "RS256", "use" => "sig"})

    TLSFixture.configure(fixture, {:body, Jason.encode!(%{"keys" => [public]})})
    workers = MixerHosted.CustomerWorkspaceHTTPFixture.KeyWorkers
    worker_pid = start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: workers})

    opts = [
      name: KeyOwner,
      manifest: [
        %{
          profile: @profile,
          jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
          transport: :hosted_https
        }
      ],
      generation: 1,
      binding: @profile.profile_id,
      ca_roots: [authority.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: workers,
      fixture: Map.take(authority, [:ip, :port])
    ]

    owner = start_supervised!(%{id: KeyOwner, start: {KeyOwner, :start_fixture, [opts]}})
    previous = Application.fetch_env(:mixer_hosted, MixerHostedWeb.Endpoint)

    on_exit(:workspace_endpoint_environment, fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, value)
        :error -> Application.delete_env(:mixer_hosted, MixerHostedWeb.Endpoint)
      end
    end)

    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint,
      adapter: Bandit.PhoenixAdapter,
      server: true,
      http: [ip: {127, 0, 0, 1}, port: 0],
      secret_key_base: String.duplicate("synthetic-workspace-fixture-", 4),
      render_errors: [formats: [json: MixerHostedWeb.ErrorJSON], layout: false],
      debug_errors: false
    )

    bandit = start_supervised!(MixerHostedWeb.Endpoint)
    {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    tls_setup = TLSFixture.info(fixture)

    on_exit(fn ->
      tls_info = if Process.alive?(fixture), do: TLSFixture.info(fixture), else: tls_setup

      for pid <- [bandit, owner, worker_pid, fixture, repo] do
        if Process.alive?(pid) do
          try do
            GenServer.stop(pid, :normal, 5_000)
          catch
            :exit, _ -> :ok
          end
        end
      end

      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, value)
        :error -> Application.delete_env(:mixer_hosted, MixerHostedWeb.Endpoint)
      end

      cleanup = %{
        bandit_stopped: not Process.alive?(bandit),
        key_owner_stopped: not Process.alive?(owner),
        jwks_workers_stopped: not Process.alive?(worker_pid),
        tls_fixture_stopped: not Process.alive?(fixture),
        repo_stopped: not Process.alive?(repo),
        application_env_restored:
          Application.fetch_env(:mixer_hosted, MixerHostedWeb.Endpoint) == previous,
        ephemeral_tls_key_directory_removed: tls_info.key_dir_removed,
        jwks_tls_request_count:
          if(Process.alive?(fixture), do: length(tls_info.requests), else: nil),
        bandit_port: port,
        tls_port: authority.port
      }

      if directory = System.get_env("MIXER_WORKSPACE_HTTP_EVIDENCE"),
        do:
          File.write!(
            Path.join(directory, "http-cleanup.json"),
            Jason.encode!(cleanup, pretty: true)
          )
    end)

    %{port: port, key: key, tls_fixture: fixture}
  end

  setup context do
    F.seed!()
    %{token: token(context.key)}
  end

  defp token(key, claims \\ %{}) do
    values =
      Map.merge(
        %{
          "iss" => @profile.issuer,
          "aud" => @profile.audience,
          "sub" => "subject",
          "client_id" => @profile.client_id,
          "iat" => F.now() - 2,
          "exp" => F.now() + 600,
          "jti" => "token",
          "scope" => "mixer.workspace.read"
        },
        claims
      )

    JOSE.JWS.sign(key, Jason.encode!(values), %{
      "alg" => "RS256",
      "typ" => "at+jwt",
      "kid" => "workspace-http-key"
    })
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  defp projects(org, extra \\ ""),
    do: "/v3/projects?organization_id=" <> URI.encode_www_form(org) <> extra

  defp header(r, name), do: for({^name, value} <- r.headers, do: value)
  defp json(r), do: Jason.decode!(r.body)

  defp request(ctx, label, method, path, bytes \\ "", headers \\ [], opts \\ []) do
    authentication =
      case Keyword.get(opts, :token, ctx.token) do
        nil -> []
        token -> [{"authorization", "Bearer " <> token}]
      end

    framing =
      if Enum.any?(headers, fn {name, _} -> name in ["content-length", "transfer-encoding"] end),
        do: [],
        else: [{"content-length", Integer.to_string(byte_size(bytes))}]

    wire = [
      method,
      " ",
      path,
      " HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n",
      Enum.map(authentication ++ framing ++ headers, fn {k, v} -> [k, ": ", v, "\r\n"] end),
      "\r\n",
      bytes
    ]

    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, ctx.port, [:binary, active: false], 2_000)

    try do
      started = System.monotonic_time(:millisecond)
      :ok = :gen_tcp.send(socket, wire)
      raw = receive_response(socket, "", Keyword.get(opts, :timeout, 4_000))
      [head, body] = :binary.split(raw, "\r\n\r\n")
      [status_line | lines] = :binary.split(head, "\r\n", [:global])
      [_, status | _] = String.split(status_line, " ")

      response_headers =
        Enum.map(lines, fn line ->
          [name, value] = :binary.split(line, ":")
          {String.downcase(name), String.trim(value)}
        end)

      response = %{status: String.to_integer(status), headers: response_headers, body: body}
      assert header(response, "cache-control") == ["no-store"]
      assert [id] = header(response, "x-request-id")
      assert byte_size(id) in 20..200
      assert header(response, "content-type") == ["application/json; charset=utf-8"]
      assert header(response, "retry-after") == if(response.status == 503, do: ["1"], else: [])
      if method == "HEAD", do: assert(body == "")

      F.record(%{
        label: label,
        request: %{
          method: method,
          path: path,
          sent_body_bytes: byte_size(bytes),
          header_names: Enum.map(headers, &elem(&1, 0)),
          bearer_present: authentication != []
        },
        response: %{
          status: response.status,
          headers: Enum.map(response_headers, fn {name, value} -> [name, value] end),
          body_bytes: byte_size(body),
          body_sha256: F.sha(body),
          json: if(body == "", do: nil, else: Jason.decode!(body))
        },
        elapsed_ms: System.monotonic_time(:millisecond) - started,
        connection_closed: true
      })

      response
    after
      :gen_tcp.close(socket)
    end
  end

  defp receive_response(socket, bytes, timeout) do
    case :gen_tcp.recv(socket, 0, timeout) do
      {:ok, next} -> receive_response(socket, bytes <> next, timeout)
      {:error, :closed} -> bytes
      other -> flunk("HTTP response did not close: #{inspect(other)}")
    end
  end

  defp error(r, status, code) do
    assert r.status == status
    value = json(r)
    assert Map.keys(value) |> Enum.sort() == ["error", "request_id"]
    assert %{"error" => %{"code" => ^code, "message" => message}, "request_id" => id} = value
    assert Map.keys(value["error"]) |> Enum.sort() == ["code", "message"]
    assert is_binary(message) and byte_size(message) <= 200
    assert header(r, "x-request-id") == [id]
  end

  test "production default verifier and scope reject before withheld bodies", ctx do
    before = length(TLSFixture.info(ctx.tls_fixture).requests)

    for path <- ["/v3/orgs", projects("org-a")] do
      error(
        request(
          ctx,
          "missing bearer before withheld body",
          "GET",
          path,
          "",
          [{"content-length", "100000"}],
          token: nil,
          timeout: 1_000
        ),
        401,
        "unauthenticated"
      )
    end

    assert length(TLSFixture.info(ctx.tls_fixture).requests) == before
    denied = token(ctx.key, %{"scope" => "mixer.artifact.read mixer.audit.read"})

    for path <- ["/v3/orgs", projects("org-a")] do
      error(
        request(
          ctx,
          "scope before withheld body",
          "GET",
          path,
          "",
          [{"content-length", "100000"}],
          token: denied,
          timeout: 1_000
        ),
        403,
        "permission_denied"
      )
    end

    assert {:ok, identity} = ConfiguredVerifier.authenticate(ctx.token, F.now())
    assert identity.subject == "subject"
    assert identity.scopes == ["mixer.workspace.read"]

    for path <- [
          "/v3/orgs/org-a/projects/project-a/artifacts/" <> String.duplicate("a", 64),
          "/v3/orgs/org-a/projects/project-a/audit"
        ] do
      error(
        request(
          ctx,
          "workspace scope grants no artifact or audit authority before withheld body",
          "GET",
          path,
          "",
          [{"content-length", "100000"}], timeout: 1_000),
        403,
        "permission_denied"
      )
    end

    transport = TLSFixture.info(ctx.tls_fixture)
    assert transport.requests != []
    assert transport.key_dir_removed

    if directory = System.get_env("MIXER_WORKSPACE_HTTP_EVIDENCE") do
      File.write!(
        Path.join(directory, "identity-transport.json"),
        Jason.encode!(
          %{
            synthetic_rs256_jwks: true,
            named_default_key_owner: true,
            request_count: length(transport.requests),
            requests:
              Enum.map(transport.requests, fn entry ->
                %{
                  request_line: entry.request |> String.split("\r\n") |> hd(),
                  sni: to_string(entry.tls[:sni_hostname])
                }
              end),
            ephemeral_tls_key_directory_removed: transport.key_dir_removed
          },
          pretty: true
        )
      )
    end
  end

  test "closed current names roles default repo and HEAD wire suppression", ctx do
    org = request(ctx, "organization exact preserved display name", "GET", "/v3/orgs")

    assert json(org) == %{
             "organizations" => [
               %{"id" => "org-a", "display_name" => "  Team * A  ", "organization_roles" => []}
             ],
             "next_cursor" => nil
           }

    result = request(ctx, "project current explicit role", "GET", projects("org-a"))

    assert json(result) == %{
             "projects" => [
               %{
                 "organization_id" => "org-a",
                 "id" => "project-a",
                 "display_name" => "Project A",
                 "roles" => ["developer"]
               }
             ],
             "next_cursor" => nil
           }

    for path <- ["/v3/orgs", projects("org-a")] do
      assert request(ctx, "HEAD committed success", "HEAD", path).status == 200
      assert request(ctx, "HEAD missing bearer", "HEAD", path, "", [], token: nil).status == 401
    end

    assert request(ctx, "HEAD invisible org", "HEAD", projects("org-b")).status == 404
  end

  test "query carries full Scope identifiers and real null names without path normalization",
       ctx do
    ids = [".", "..", "org/one", "org:雪", "a+b", "percent%id", "with space"]

    for {org, n} <- Enum.with_index(ids) do
      F.organization(org)
      F.project(org, "project/..雪+%:#{n}")
      F.member("full-#{n}", org, nil, "all_projects", "billing_manager")
      result = request(ctx, "full identifier round trip #{n}", "GET", projects(org))

      assert json(result) == %{
               "projects" => [
                 %{
                   "organization_id" => org,
                   "id" => "project/..雪+%:#{n}",
                   "display_name" => nil,
                   "roles" => ["billing_manager"]
                 }
               ],
               "next_cursor" => nil
             }
    end

    page = json(request(ctx, "full identifiers organization rows", "GET", "/v3/orgs"))
    assert Enum.map(page["organizations"], & &1["id"]) == Enum.sort(["org-a" | ids])

    error(
      request(ctx, "literal plus is a form space", "GET", "/v3/projects?organization_id=a+b"),
      404,
      "not_found"
    )
  end

  test "organization and project pagination remains private and fresh", ctx do
    for org <- ["org-c", "org-d"] do
      F.organization(org)
      F.member("member-#{org}", org, nil, "organization_only", "viewer")
    end

    first = json(request(ctx, "organization first page", "GET", "/v3/orgs?limit=1"))
    assert Enum.map(first["organizations"], & &1["id"]) == ["org-a"]
    assert is_binary(first["next_cursor"])

    F.mutate(
      "org-c",
      nil,
      "UPDATE public.mixer_authz_memberships SET active=false,revision=revision+1 WHERE id='member-org-c'"
    )

    second =
      json(
        request(
          ctx,
          "next page freshly omits committed revocation",
          "GET",
          "/v3/orgs?limit=1&cursor=" <> first["next_cursor"]
        )
      )

    assert Enum.map(second["organizations"], & &1["id"]) == ["org-d"]
    assert second["next_cursor"] == nil
    F.member("all", "org-a", nil, "all_projects", "viewer")
    project_first = json(request(ctx, "project first page", "GET", projects("org-a", "&limit=1")))
    assert Enum.map(project_first["projects"], & &1["id"]) == ["project-a"]

    project_second =
      json(
        request(
          ctx,
          "project second page",
          "GET",
          projects("org-a", "&limit=1&cursor=" <> project_first["next_cursor"])
        )
      )

    assert Enum.map(project_second["projects"], & &1["id"]) == ["project-b"]
    assert project_second["next_cursor"] == nil

    for org <- ["org-b", "org-inactive", "missing"] do
      error(
        request(ctx, "generic invisible inactive missing", "GET", projects(org)),
        404,
        "not_found"
      )
    end

    error(
      request(
        ctx,
        "cross organization cursor denied",
        "GET",
        projects("org-b", "&cursor=" <> project_first["next_cursor"])
      ),
      400,
      "invalid_request"
    )
  end

  test "organization versus exact project roles never broaden project visibility", ctx do
    F.member("organization-owner", "org-a", nil, "organization_only", "owner")
    F.member("organization-billing", "org-a", nil, "organization_only", "billing_manager")
    F.member("all-viewer", "org-a", nil, "all_projects", "viewer")
    F.member("project-admin", "org-a", "project-a", "exact_project", "administrator")
    F.member("project-release", "org-a", "project-a", "exact_project", "release_manager")
    page = json(request(ctx, "organization role provenance", "GET", "/v3/orgs"))

    assert hd(page["organizations"])["organization_roles"] == [
             "billing_manager",
             "owner",
             "viewer"
           ]

    page = json(request(ctx, "project effective role union", "GET", projects("org-a")))

    assert Enum.map(page["projects"], &{&1["id"], &1["roles"]}) == [
             {"project-a", ["administrator", "developer", "release_manager", "viewer"]},
             {"project-b", ["viewer"]}
           ]

    F.organization("org-empty")
    F.member("organization-only", "org-empty", nil, "organization_only", "owner")

    assert json(
             request(ctx, "organization only no project authority", "GET", projects("org-empty"))
           ) == %{"projects" => [], "next_cursor" => nil}

    F.sql(
      "DELETE FROM public.mixer_authz_memberships WHERE id IN ('member','all-viewer','project-admin','project-release')"
    )

    assert json(
             request(ctx, "organization owner does not cover projects", "GET", projects("org-a"))
           ) == %{"projects" => [], "next_cursor" => nil}
  end

  test "committed membership credential and label updates never reuse positive authority", ctx do
    assert request(ctx, "before membership revocation", "GET", projects("org-a")).status == 200

    F.mutate(
      "org-a",
      "project-a",
      "UPDATE public.mixer_authz_memberships SET active=false,revision=revision+1 WHERE id='member'"
    )

    error(
      request(ctx, "after committed membership revocation", "GET", projects("org-a")),
      404,
      "not_found"
    )

    assert json(request(ctx, "organization after membership revocation", "GET", "/v3/orgs")) == %{
             "organizations" => [],
             "next_cursor" => nil
           }

    F.mutate(
      "org-a",
      "project-a",
      "UPDATE public.mixer_authz_memberships SET active=true,revision=revision+1 WHERE id='member'"
    )

    F.mutate(
      "org-a",
      "project-a",
      "UPDATE public.mixer_authz_projects SET display_name=NULL WHERE organization_id='org-a' AND id='project-a'"
    )

    assert hd(json(request(ctx, "fresh stored null label", "GET", projects("org-a")))["projects"])[
             "display_name"
           ] == nil

    F.sql(
      "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'"
    )

    error(request(ctx, "current credential revoked", "GET", "/v3/orgs"), 401, "unauthenticated")
    assert request(ctx, "HEAD current credential revoked", "HEAD", "/v3/orgs").status == 401
  end

  test "malformed duplicate and alternative token queries reject before withheld body", ctx do
    cases = [
      {"/v3/orgs?limit=1&limit=2", "invalid_request"},
      {"/v3/orgs?limit=01", "invalid_request"},
      {"/v3/orgs?limit=", "invalid_request"},
      {"/v3/orgs?limit=101", "invalid_request"},
      {"/v3/orgs?organization_id=org-a", "invalid_request"},
      {"/v3/orgs?limit%5B%5D=1", "invalid_request"},
      {"/v3/orgs?limit=1&", "invalid_request"},
      {"/v3/projects", "invalid_request"},
      {"/v3/projects?organization_id=org-a&organization_id=org-b", "invalid_request"},
      {"/v3/projects?organization_id=percent%id", "invalid_request"},
      {"/v3/projects?organization_id=%FF", "invalid_request"},
      {"/v3/projects?organization_id=org-a&cursor=abc=", "invalid_request"},
      {"/v3/orgs?access_token=private", "invalid_request"}
    ]

    for {path, code} <- cases,
        do:
          error(
            request(
              ctx,
              "bad query before withheld body",
              "GET",
              path,
              "",
              [{"content-length", "100000"}],
              timeout: 1_000
            ),
            400,
            code
          )

    for path <- ["/v3/%6Frgs", "/v3/%70rojects?organization_id=org-a"],
        do:
          error(request(ctx, "encoded path alias rejected", "GET", path), 400, "invalid_request")
  end

  test "nonempty streaming and encoded bodies reject without interpretation", ctx do
    error(request(ctx, "nonempty GET body", "GET", "/v3/orgs", "private"), 400, "invalid_request")

    error(
      request(ctx, "chunked nonempty body", "GET", "/v3/orgs", "1\r\nx\r\n0\r\n\r\n", [
        {"transfer-encoding", "chunked"}
      ]),
      400,
      "invalid_request"
    )

    error(
      request(
        ctx,
        "content encoding before withheld body",
        "GET",
        "/v3/orgs",
        "",
        [{"content-length", "100000"}, {"content-encoding", "gzip"}],
        timeout: 1_000
      ),
      415,
      "unsupported_content_encoding"
    )

    error(
      request(
        ctx,
        "unexpected media before withheld body",
        "GET",
        "/v3/orgs",
        "",
        [{"content-length", "100000"}, {"content-type", "text/plain"}],
        timeout: 1_000
      ),
      400,
      "content_type"
    )

    assert request(ctx, "exact optional JSON media", "GET", "/v3/orgs", "", [
             {"content-type", "application/json"}
           ]).status == 200
  end

  test "bad current metadata and missing head fail closed with generic unavailable", ctx do
    F.mutate(
      "org-a",
      nil,
      "UPDATE public.mixer_authz_organizations SET display_name='private' || chr(10) || 'name' WHERE id='org-a'"
    )

    error(
      request(ctx, "invalid stored name fails closed", "GET", "/v3/orgs"),
      503,
      "authorization_unavailable"
    )

    F.mutate(
      "org-a",
      nil,
      "UPDATE public.mixer_authz_organizations SET display_name=NULL WHERE id='org-a'"
    )

    F.sql(
      "DELETE FROM public.mixer_authz_project_heads WHERE organization_id='org-a' AND project_id='project-a'"
    )

    error(
      request(ctx, "missing selected project head", "GET", projects("org-a")),
      503,
      "authorization_unavailable"
    )

    assert request(ctx, "HEAD unavailable no wire body", "HEAD", projects("org-a")).status == 503
  end

  test "actual default repository backend loss after final local read discloses no page", ctx do
    handler = "workspace-http-before-commit"
    parent = self()

    :ok =
      :telemetry.attach(
        handler,
        [:workspace_http_default_repo, :query],
        fn _, _, metadata, _ ->
          if metadata.query == "SELECT 1" do
            :telemetry.detach(handler)

            rows =
              F.sql(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name='mixer-workspace-http-runtime' AND state='idle in transaction'"
              ).rows

            send(parent, {:workspace_backend_terminated, rows})
          end
        end,
        nil
      )

    on_exit(fn -> :telemetry.detach(handler) end)
    failed = request(ctx, "default Repo precommit backend loss", "GET", projects("org-a"))
    assert_receive {:workspace_backend_terminated, [[true]]}, 2_000
    error(failed, 503, "authorization_unavailable")
    assert not String.contains?(failed.body, "Project A")

    if directory = System.get_env("MIXER_WORKSPACE_HTTP_EVIDENCE") do
      File.write!(
        Path.join(directory, "transaction-boundary.json"),
        Jason.encode!(
          %{
            actual_default_repo: true,
            final_local_read_completed: true,
            backend_terminated_before_commit: true,
            response_status: failed.status,
            page_rows_disclosed: false
          },
          pretty: true
        )
      )
    end

    assert request(ctx, "fresh retry after backend loss", "GET", projects("org-a")).status == 200
  end

  test "actual compiled console client joins the production Phoenix directory", ctx do
    ids = [".", "..", "org/雪+%"]

    for {org, n} <- Enum.with_index(ids) do
      F.organization(org)
      F.project(org, "project/雪+%")
      F.member("node-#{n}", org, nil, "all_projects", "billing_manager")
    end

    driver = System.fetch_env!("MIXER_WORKSPACE_HTTP_NODE_DRIVER")

    {out, status} =
      System.cmd("node", [driver, "http://127.0.0.1:#{ctx.port}"],
        env: [{"MIXER_WORKSPACE_EPHEMERAL_BEARER", ctx.token}],
        stderr_to_stdout: true
      )

    assert status == 0, out
    result = Jason.decode!(out)
    assert result["status"] == "passed"
    assert result["full_identifier_projects"] == length(ids)

    if directory = System.get_env("MIXER_WORKSPACE_HTTP_EVIDENCE"),
      do:
        File.write!(
          Path.join(directory, "node-client-join.json"),
          Jason.encode!(result, pretty: true)
        )
  end
end
