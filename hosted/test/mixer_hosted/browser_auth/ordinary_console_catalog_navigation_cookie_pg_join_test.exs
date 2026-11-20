Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.OrdinaryConsoleCatalogNavigationCookiePGJoinTest do
  use ExUnit.Case, async: false
  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.Admin

  alias MixerHosted.BrowserAuth.{
    Installation,
    RuntimeOwner,
    LifecycleRepo,
    ProviderOwner,
    Store,
    Protocol
  }

  alias MixerHosted.CustomerArtifacts.{LocalUpload, UploadRepo}
  alias MixerHosted.Identity.KeyOwner
  alias MixerHosted.Releases.RuntimeProvisioning

  setup_all do
    Fixture.prepare!()
  end

  setup c do
    if c[:without_application] do
      :ok
    else
      c |> Fixture.start!() |> Map.take([:root, :http_port])
    end
  end

  @tag :ordinary_console_catalog_navigation_cookie_pg_join
  test "ordinary_console_catalog_navigation_cookie_pg_join", c do
    own_catalog_fixture!()
    create_build()
    capture_catalog_fixture!()

    F.q!(
      Admin,
      "INSERT INTO mixer_authz_applications VALUES('org-a','project-a','empty-app',true),('org-b','project-b','fieldlog',true)"
    )

    preauth = bootstrap_http(c)
    login = begin_http(c, preauth)
    activation = http(c, "/auth/callback?" <> login.query, login.headers)
    assert activation.status == 303
    cookie = response_cookie(activation)
    hs = headers(cookie)
    project = "organization_id=org-a&project_id=project-a"
    applications = http(c, "/console-api/v1/applications?" <> project, hs)
    assert applications.status == 200
    page = Jason.decode!(applications.body)

    assert page == %{
             "organizationId" => "org-a",
             "projectId" => "project-a",
             "applications" => [
               %{"applicationId" => "empty-app"},
               %{"applicationId" => "fieldlog"}
             ],
             "nextCursor" => nil
           }

    assert http(c, "/console-api/v1/build-catalog?" <> project <> "&application_id=empty-app", hs).body
           |> Jason.decode!() == %{
             "organizationId" => "org-a",
             "projectId" => "project-a",
             "applicationId" => "empty-app",
             "builds" => [],
             "nextCursor" => nil
           }

    catalog_path = "/console-api/v1/build-catalog?" <> project <> "&application_id=fieldlog"
    listed = http(c, catalog_path, hs)
    assert listed.status == 200
    [dto] = Jason.decode!(listed.body)["builds"]
    assert dto["state"] == "queued" and map_size(dto) == 14

    wire = [
      {"organizationId", :organization_id},
      {"projectId", :project_id},
      {"applicationId", :application_id},
      {"buildId", :build_id},
      {"platform", :platform},
      {"sourceSha256", :source_sha256},
      {"toolchainLockSha256", :toolchain_lock_sha256},
      {"buildDefinitionSha256", :build_definition_sha256}
    ]

    selected = Map.new(wire, fn {key, atom} -> {atom, Map.fetch!(dto, key)} end)
    assert {:ok, _} = MixerHosted.CustomerBuilds.Selection.new(selected)
    detail = http(c, build_path(selected), hs)
    assert detail.status == 200
    assert Jason.decode!(detail.body)["build"] == dto
    compiled_catalog_join(c, cookie, page, "queued", dto)

    [[journal]] =
      F.q!(
        Admin,
        "SELECT journal FROM mixer_builds WHERE organization_id='org-a' AND project_id='project-a' AND application_id='fieldlog' AND build_id='build-a' AND platform='ios'"
      ).rows

    assert {:ok, build} = MixerHosted.Builds.Journal.restore(journal)
    assert {:ok, ref} = MixerHosted.Builds.Lifecycle.worker_ref(build)

    assert {:ok, running, _, :applied} =
             MixerHosted.Builds.Journal.append(
               journal,
               "r1158-start",
               %{type: :start, ref: ref},
               1
             )

    assert {:ok, failed, _, :applied} =
             MixerHosted.Builds.Journal.append(
               running,
               "r1158-fail",
               %{
                 type: :completed,
                 ref: ref,
                 result: %{
                   outcome: :failed,
                   class: :compiler,
                   code: :compiler_error,
                   diagnostic_sha256: String.duplicate("d", 64)
                 }
               },
               2
             )

    F.q!(
      Admin,
      "UPDATE mixer_builds SET journal=$1,revision=2 WHERE organization_id='org-a' AND project_id='project-a' AND application_id='fieldlog' AND build_id='build-a' AND platform='ios'",
      [failed]
    )

    refreshed = http(c, build_path(selected), hs)
    assert refreshed.status == 200
    terminal = Jason.decode!(refreshed.body)["build"]

    assert terminal["state"] == "failed" and terminal["revision"] == 2 and
             terminal["failureCode"] == "compiler_error"

    [^terminal] = Jason.decode!(http(c, catalog_path, hs).body)["builds"]
    compiled_catalog_join(c, cookie, page, "terminal", terminal)

    assert http(c, "/console-api/v1/applications?organization_id=org-b&project_id=project-b", hs).status ==
             404

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(MixerHosted.Repo, "SELECT journal FROM mixer_builds", [])

    assert [] == F.q!(MixerHosted.Repo, "SELECT id FROM mixer_authz_applications").rows
    assert http(c, "/v3/build-catalog", hs).status == 404

    File.write!(
      System.fetch_env!("MIXER_BROWSER_CATALOG_EVIDENCE"),
      Jason.encode!(%{
        applications: page,
        catalog: dto,
        selected: selected,
        detail: Jason.decode!(detail.body),
        terminal: terminal,
        real_pkce: true,
        build_select: "42501",
        direct_application_rows: 0
      })
    )

    leases_clean()
  end

  @tag :without_application
  test "ordinary browser sessions admit only the exact installed uploader grants", c do
    refute Process.whereis(UploadRepo)
    assert bootstrap_http(Fixture.start!(c)).cookie != ""
    assert :ok = Application.stop(:mixer_hosted)

    {output, status} =
      System.cmd(
        "psql",
        ~w(-X -w -h 127.0.0.1 -U browser_admin -d browser_ordinary_installation_r1422 -v ON_ERROR_STOP=1) ++
          [
            "-p",
            to_string(F.port()),
            "-f",
            "../docs/operations/provision-local-artifact-uploader.sql"
          ],
        env: [{"PGSSLMODE", "disable"}],
        stderr_to_stdout: true
      )

    assert status == 0, output

    on_exit(fn ->
      F.q!(Admin, "DROP OWNED BY mixer_artifact_uploader")
      F.q!(Admin, "DROP ROLE mixer_artifact_uploader")
    end)

    F.q!(Admin, "CREATE ROLE mixer_release_delivery LOGIN NOINHERIT")
    on_exit(fn -> F.q!(Admin, "DROP ROLE mixer_release_delivery") end)

    c =
      put_in(c.hosted.endpoint[:http],
        ip: {127, 0, 0, 1},
        port: 0,
        http_2_options: [enabled: false]
      )

    vector = File.read!("../services/protocol/testdata/signed-release-v3.json") |> Jason.decode!()

    release_env = %{
      "MIXER_LOCAL_RELEASE_CONFIG" =>
        Jason.encode!(%{
          host: vector["host"],
          roots: vector["roots"],
          channel: vector["signed_assignment"]["assignment"]["channel"]
        }),
      "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD" => "fixture-reader"
    }

    {target, delivery} = release = RuntimeProvisioning.load!(release_env, c.hosted)
    Application.put_env(:mixer_hosted, :local_release_target, target)
    Application.put_env(:mixer_hosted, :local_release_delivery, delivery)

    enabled =
      LocalUpload.configure!(
        %{
          "MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED" => "true",
          "MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD" => "fixture-uploader"
        },
        c.hosted,
        release
      )

    running = Fixture.start!(%{c | hosted: enabled})

    assert {:ok, %{repo: UploadRepo}} = LocalUpload.configuration()

    assert [["mixer_artifact_uploader"]] ==
             F.q!(UploadRepo, "SELECT session_user::text").rows

    assert bootstrap_http(running).cookie != ""
    assert :ok = Application.stop(:mixer_hosted)

    default_off = %{c | hosted: LocalUpload.configure!(%{}, c.hosted, release)}
    running = Fixture.start!(default_off)
    assert :disabled = LocalUpload.configuration()
    refute Process.whereis(UploadRepo)
    assert bootstrap_http(running).cookie != ""
    assert :ok = Application.stop(:mixer_hosted)

    for {mutate, restore} <- [
          {"REVOKE SELECT ON public.mixer_authz_profiles FROM mixer_artifact_uploader",
           "GRANT SELECT ON public.mixer_authz_profiles TO mixer_artifact_uploader"},
          {"GRANT SELECT ON public.mixer_browser_sessions TO mixer_artifact_uploader",
           "REVOKE SELECT ON public.mixer_browser_sessions FROM mixer_artifact_uploader"},
          {"GRANT UPDATE (id) ON public.mixer_authz_profiles TO mixer_artifact_uploader",
           "REVOKE UPDATE (id) ON public.mixer_authz_profiles FROM mixer_artifact_uploader"},
          {"GRANT SELECT ON public.mixer_authz_profiles TO mixer_artifact_uploader WITH GRANT OPTION",
           "REVOKE GRANT OPTION FOR SELECT ON public.mixer_authz_profiles FROM mixer_artifact_uploader"},
          {"ALTER TABLE public.mixer_authz_profiles OWNER TO browser_admin",
           "ALTER TABLE public.mixer_authz_profiles OWNER TO browser_schema_owner"},
          {"ALTER ROLE mixer_artifact_uploader RENAME TO wrong_artifact_uploader",
           "ALTER ROLE wrong_artifact_uploader RENAME TO mixer_artifact_uploader"},
          {"ALTER ROLE mixer_artifact_uploader NOLOGIN",
           "ALTER ROLE mixer_artifact_uploader LOGIN"},
          {"ALTER ROLE mixer_artifact_uploader INHERIT",
           "ALTER ROLE mixer_artifact_uploader NOINHERIT"},
          {"ALTER ROLE mixer_artifact_uploader BYPASSRLS",
           "ALTER ROLE mixer_artifact_uploader NOBYPASSRLS"},
          {"GRANT mixer_release_delivery TO mixer_artifact_uploader",
           "REVOKE mixer_release_delivery FROM mixer_artifact_uploader"},
          {"GRANT mixer_artifact_uploader TO mixer_release_delivery",
           "REVOKE mixer_artifact_uploader FROM mixer_release_delivery"},
          {"GRANT CREATE ON SCHEMA public TO mixer_artifact_uploader",
           "REVOKE CREATE ON SCHEMA public FROM mixer_artifact_uploader"},
          {"ALTER ROLE mixer_artifact_uploader IN DATABASE browser_ordinary_installation_r1422 SET search_path TO public",
           "ALTER ROLE mixer_artifact_uploader IN DATABASE browser_ordinary_installation_r1422 RESET search_path"}
        ] do
      F.q!(Admin, mutate)

      try do
        refused = Fixture.start!(default_off)
        assert RuntimeOwner.status().phase == :unavailable, mutate
        response = http(refused, "/auth/session", [])
        assert response.status == 503, mutate
        assert response_header(response, "set-cookie") == [], mutate
        assert :ok = Application.stop(:mixer_hosted)
      after
        F.q!(Admin, restore)
      end
    end

    assert bootstrap_http(Fixture.start!(default_off)).cookie != ""
    leases_clean()
  end

  @tag :without_application
  test "ordinary disabled endpoint serves health and bearer but no browser owners or cookies",
       c do
    c = Fixture.start!(c, :disabled)

    for name <- [LifecycleRepo, ProviderOwner, RuntimeOwner, KeyOwner],
        do: assert(Process.whereis(name) == nil)

    for {method, path} <- [
          {"GET", "/auth/session"},
          {"HEAD", "/auth/session"},
          {"POST", "/auth/login"},
          {"GET", "/console-api/v1/applications"}
        ] do
      response = http(c, path, [], method)
      assert response.status == 404
      assert response_header(response, "cache-control") == ["no-store"]
      assert response_header(response, "set-cookie") == []
    end

    assert http(c, "/health/live", []).status == 200
    bearer = http(c, "/v3/orgs", [])
    assert bearer.status == 401
    assert response_header(bearer, "www-authenticate") == ["Bearer"]
    assert http(c, "/v3/private/artifacts", []).status == 404

    # Changing the application environment is not a supported enable operation.
    Application.put_env(:mixer_hosted, :startup, {c.hosted, c.installation})
    assert MixerHosted.Application.startup() == :error
    assert http(c, "/auth/session", []).status == 404
    assert Process.whereis(RuntimeOwner) == nil

    assert {:error, :restart_required} =
             MixerHosted.Application.config_change([startup: {c.hosted, c.installation}], [], [])
  end

  @tag :without_application
  test "processor, malformed and missing-material installations refuse before any children",
       c do
    assert_raise ArgumentError, "browser installation unavailable: configuration", fn ->
      Installation.load!(c.browser_env, c.hosted)
    end

    assert_raise ArgumentError, "browser installation unavailable: configuration", fn ->
      Installation.load!(%{"MIXER_BROWSER_AUTH_CONFIG" => "sensitive"}, c.hosted)
    end

    assert_raise ArgumentError, "browser installation unavailable: configuration", fn ->
      Installation.load!(c.browser_env, %{c.hosted | role: :processor})
    end

    assert Installation.load!(%{}, c.hosted) == :disabled
    refute inspect(c.installation) =~ "synthetic"
    refute inspect(c.installation) =~ "fixture/client"
    Fixture.configure!(%{c | hosted: %{c.hosted | role: :processor}}, c.installation)
    assert {:error, _} = Application.ensure_all_started(:mixer_hosted)

    for name <- [
          MixerHosted.Supervisor,
          MixerHosted.Repo,
          MixerHostedWeb.Endpoint,
          KeyOwner,
          LifecycleRepo,
          ProviderOwner,
          RuntimeOwner
        ],
        do: assert(Process.whereis(name) == nil)
  end

  test "ordinary mount preserves raw refusals and passes nonowned connections unchanged", c do
    baseline = F.q!(Admin, "SELECT count(*) FROM mixer_browser_sessions").rows

    for {method, path, hs, body} <- [
          {"HEAD", "/auth/session", [], ""},
          {"POST", "/auth/session", [], ""},
          {"GET", "/auth/login", [], ""},
          {"GET", "/auth/session?x=1&x=2", [], ""},
          {"GET", "/auth/session",
           [
             {"cookie", "__Host-mixer-session=" <> String.duplicate("a", 43)},
             {"cookie", "__Host-mixer-session=" <> String.duplicate("b", 43)}
           ], ""},
          {"GET", "/auth/session", [{"content-length", "1"}], "x"},
          {"GET",
           "/console-api/v1/applications?organization_id=org-a&project_id=project-a&project_id=project-b",
           [], ""},
          {"GET",
           "/console-api/v1/applications?organization_id=org-a&project_id=project-a&owner=caller",
           [], ""},
          {"GET", "/console-api/v1/applications?organization_id=org-a&project_id=%ZZ", [], ""},
          {"GET", "/auth/unknown", [], ""}
        ] do
      response = http(c, path, hs, method, body)
      assert response.status in [400, 404]
      assert response_header(response, "set-cookie") == []
    end

    assert F.q!(Admin, "SELECT count(*) FROM mixer_browser_sessions").rows == baseline
    conn = Plug.Test.conn("POST", "/v3/orgs?x=1&x=2", "unread")
    conn = %{conn | req_headers: [{"x-raw", "one"}, {"x-raw", "two"}]}
    assert MixerHostedWeb.BrowserLoginHTTP.call(conn, :ordinary) === conn
    assert http(c, "/health/live", []).status == 200
    assert http(c, "/v3/orgs", []).status == 401
    assert http(c, "/v3/orgs?access_token=raw", []).status == 400
    assert RuntimeOwner.status().phase == :storage_ready
  end

  test "actual permanent child termination tears down browser siblings without restarting the temporary group",
       c do
    assert RuntimeOwner.status().phase == :storage_ready

    {_, group, :supervisor, _} =
      List.keyfind(Supervisor.which_children(c.root), MixerHosted.BrowserAuth.Supervisor, 0)

    children = Supervisor.which_children(group)

    assert Enum.sort(Enum.map(children, &elem(&1, 0))) ==
             Enum.sort([LifecycleRepo, ProviderOwner, RuntimeOwner])

    watches = for {_, pid, _, _} <- children, do: {Process.monitor(pid), pid}
    group_watch = Process.monitor(group)
    owner = Process.whereis(RuntimeOwner)
    deadline = System.monotonic_time(:millisecond) + 5_000
    assert {:ok, lease} = GenServer.call(owner, {:reserve, deadline, System.system_time(:second)})
    assert :ok = RuntimeOwner.checkpoint(lease)
    assert :ok = GenServer.stop(Process.whereis(ProviderOwner), :normal)
    assert_receive {:DOWN, ^group_watch, :process, ^group, _}, 5_000

    for {watch, pid} <- watches do
      assert_receive {:DOWN, ^watch, :process, ^pid, _}, 5_000
    end

    assert List.keyfind(Supervisor.which_children(c.root), MixerHosted.BrowserAuth.Supervisor, 0) ==
             nil

    for name <- [LifecycleRepo, ProviderOwner, RuntimeOwner],
        do: assert(Process.whereis(name) == nil)

    assert Process.alive?(c.root)
    assert http(c, "/health/live", []).status == 200
    assert http(c, "/auth/session", []).status == 503
    assert {:error, %Store.Failure{}} = RuntimeOwner.checkpoint(lease)
    assert :ok = Application.stop(:mixer_hosted)
    recovered = Fixture.start!(c)
    assert recovered.root != c.root
    assert RuntimeOwner.status().phase == :storage_ready
    assert bootstrap_http(recovered).cookie != ""
    assert {:error, %Store.Failure{}} = RuntimeOwner.checkpoint(lease)
  end

  @tag :without_application
  test "runtime startup refusal unwinds lifecycle provider and ordinary siblings before Endpoint",
       c do
    bad = %{c.installation | runtime: %{c.runtime | custody: nil}}
    Fixture.configure!(c, bad)
    assert {:error, _} = Application.ensure_all_started(:mixer_hosted)

    for name <- [
          MixerHosted.Supervisor,
          MixerHosted.Repo,
          MixerHostedWeb.Endpoint,
          KeyOwner,
          LifecycleRepo,
          ProviderOwner,
          RuntimeOwner
        ],
        do: assert(Process.whereis(name) == nil)

    assert MixerHosted.Application.startup() == :error
  end

  test "external Repo replacement cannot renew the retained owner or its old lease", c do
    owner = Process.whereis(RuntimeOwner)
    deadline = System.monotonic_time(:millisecond) + 5_000
    assert {:ok, lease} = GenServer.call(owner, {:reserve, deadline, System.system_time(:second)})
    old_repo = Process.whereis(MixerHosted.Repo)
    assert :ok = Supervisor.terminate_child(c.root, MixerHosted.Repo)
    assert {:ok, replacement} = Supervisor.restart_child(c.root, MixerHosted.Repo)
    refute old_repo == replacement
    eventually(fn -> RuntimeOwner.status().phase == :unavailable end)
    assert Process.whereis(RuntimeOwner) == owner
    assert {:error, %Store.Failure{}} = RuntimeOwner.checkpoint(lease)
    status = RuntimeOwner.status()
    assert http(c, "/auth/session", []).status == 503
    assert RuntimeOwner.status() == status
  end

  test "expired lease and unknown outcome remain latched until explicit application restart", c do
    owner = Process.whereis(RuntimeOwner)

    assert {:ok, lease} =
             GenServer.call(
               owner,
               {:reserve, System.monotonic_time(:millisecond) + 30, System.system_time(:second)}
             )

    eventually(fn -> RuntimeOwner.status().phase == :unavailable end)
    assert {:error, %Store.Failure{}} = RuntimeOwner.checkpoint(lease)
    assert http(c, "/auth/session", []).status == 503
    assert :ok = Application.stop(:mixer_hosted)
    recovered = Fixture.start!(c)
    assert RuntimeOwner.status().phase == :storage_ready

    assert {:ok, fresh} =
             GenServer.call(
               Process.whereis(RuntimeOwner),
               {:reserve, System.monotonic_time(:millisecond) + 5_000,
                System.system_time(:second)}
             )

    failure =
      {:error, %Store.Failure{code: :session_unavailable, phase: :effect, outcome: :unknown}}

    assert :ok = GenServer.call(Process.whereis(RuntimeOwner), {:failed, fresh, failure})
    assert RuntimeOwner.status().phase == :unavailable
    assert {:error, %Store.Failure{}} = RuntimeOwner.checkpoint(fresh)
    assert http(recovered, "/auth/session", []).status == 503
  end

  test "provider ticket retains PID and generation fences across whole-Application restart", c do
    verifier = Protocol.random_token()
    {:ok, challenge} = Protocol.pkce_challenge(verifier)

    query =
      URI.encode_query(%{
        "client_id" => c.config.client_id,
        "redirect_uri" => c.config.redirect_uri,
        "code_challenge" => challenge,
        "nonce" => Protocol.random_token(),
        "scope" => c.config.scope
      })

    code = GenServer.call(c.provider, {:register, query})
    deadline = System.monotonic_time(:millisecond) + 5_000
    assert {:ok, _, _, ticket} = ProviderOwner.exchange(c.config, code, verifier, deadline)
    assert :ok = ProviderOwner.finish(ticket, c.config, deadline)
    old_provider = Process.whereis(ProviderOwner)
    assert :ok = Application.stop(:mixer_hosted)
    Fixture.start!(c)
    refute Process.whereis(ProviderOwner) == old_provider

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish(ticket, c.config, System.monotonic_time(:millisecond) + 5_000)
  end

  defp eventually(fun, tries \\ 100)
  defp eventually(fun, 0), do: assert(fun.())

  defp eventually(fun, tries) do
    if fun.(),
      do: :ok,
      else:
        (
          Process.sleep(10)
          eventually(fun, tries - 1)
        )
  end
end
