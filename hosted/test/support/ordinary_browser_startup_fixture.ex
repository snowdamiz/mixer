defmodule MixerHosted.Test.OrdinaryBrowserStartupFixture do
  @moduledoc "Test-compiled loopback graph proof only; not ordinary TLS/provider admission."
  import ExUnit.Assertions
  import ExUnit.Callbacks

  alias MixerHosted.BrowserAuth.{
    RuntimeOwner,
    RuntimeConfig,
    Config,
    ConfigurationDigest,
    Custody,
    LifecycleRepo,
    Installation,
    ActivationPreparationSchema,
    Protocol
  }

  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.Identity.{KeyOwner, TLSFixture, TrustSnapshot}

  @root_names [
    MixerHosted.Supervisor,
    MixerHosted.Repo,
    MixerHostedWeb.Endpoint,
    Oban,
    KeyOwner,
    Module.concat(KeyOwner, FetchSupervisor),
    LifecycleRepo,
    MixerHosted.BrowserAuth.ProviderOwner,
    RuntimeOwner
  ]
  @all_names @root_names ++ [Admin, Migration]

  def refuse_names!(names) do
    for name <- names do
      if Process.whereis(name),
        do: raise("ordinary fixture refuses occupied name: #{inspect(name)}")
    end
  end

  defp prepare_evidence! do
    prior =
      for key <- ~w(MIXER_BROWSER_CATALOG_FIXTURE_ROOT MIXER_BROWSER_CATALOG_EVIDENCE),
          do: {key, System.fetch_env(key)}

    root = Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "ordinary-r1422")
    :ok = File.mkdir(root)
    File.mkdir!(Path.join(root, "proof"))

    on_exit(fn ->
      for {key, value} <- prior do
        case value do
          {:ok, value} -> System.put_env(key, value)
          :error -> System.delete_env(key)
        end
      end
    end)

    System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", root)
    System.put_env("MIXER_BROWSER_CATALOG_EVIDENCE", Path.join(root, "positive.json"))
  end

  def configure!(c, installation) do
    refuse_names!(@root_names)
    prior = Application.get_all_env(:mixer_hosted)

    on_exit(fn ->
      for {key, _} <- Application.get_all_env(:mixer_hosted),
          do: Application.delete_env(:mixer_hosted, key)

      for {key, value} <- prior, do: Application.put_env(:mixer_hosted, key, value)
    end)

    installation = if installation == :fixture, do: c.installation, else: installation

    hosted =
      if installation == :disabled,
        do: %{
          c.hosted
          | identity_startup: %MixerHosted.Identity.StartupConfig{
              mode: :disabled,
              owner_options: []
            }
        },
        else: c.hosted

    Application.put_env(:mixer_hosted, :startup, {hosted, installation})
    Application.put_env(:mixer_hosted, :role, hosted.role)
    Application.put_env(:mixer_hosted, :identity_startup, hosted.identity_startup)
    Application.put_env(:mixer_hosted, MixerHosted.Repo, hosted.repo)
    Application.put_env(:mixer_hosted, Oban, hosted.oban)
    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, hosted.endpoint)
    {hosted, installation}
  end

  def start!(c, installation \\ :fixture) do
    installation = if installation == :fixture, do: c.installation, else: installation
    configure!(c, installation)
    result = Application.ensure_all_started(:mixer_hosted)
    root = Process.whereis(MixerHosted.Supervisor)

    on_exit(fn ->
      assert Process.whereis(MixerHosted.Supervisor) in [nil, root]

      if is_pid(root) and Process.whereis(MixerHosted.Supervisor) == root,
        do: assert(:ok == Application.stop(:mixer_hosted))

      for name <- @root_names, do: assert(Process.whereis(name) == nil)
    end)

    assert {:ok, _} = result
    {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    Map.merge(c, %{http_port: port, root: root})
  end

  def prepare!(create \\ false) do
    refuse_names!(@all_names)
    prepare_evidence!()
    conn = F.connection!("browser_admin", "postgres")

    try do
      Postgrex.query!(
        conn,
        "CREATE DATABASE browser_ordinary_installation_r1422 OWNER browser_schema_owner",
        []
      )
    after
      GenServer.stop(conn)
    end

    on_exit(fn ->
      conn = F.connection!("browser_admin", "postgres")

      try do
        Postgrex.query!(conn, "DROP DATABASE browser_ordinary_installation_r1422", [])
      after
        GenServer.stop(conn)
      end
    end)

    for app <- [:ecto_sql, :postgrex, :jason, :jose, :mint, :ssl, :bandit],
        do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_ordinary_installation_r1422",
      pool_size: 2,
      log: false
    ]

    previous_admin = Application.fetch_env(:browser_storage_fixture, Admin)

    on_exit(fn ->
      case previous_admin do
        {:ok, value} -> Application.put_env(:browser_storage_fixture, Admin, value)
        :error -> Application.delete_env(:browser_storage_fixture, Admin)
      end
    end)

    Application.put_env(:browser_storage_fixture, Admin, settings ++ [username: "browser_admin"])

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

    for table <- ~w(sessions session_vault oidc_attempts session_events),
        do: F.q!(Admin, "REVOKE SELECT ON public.mixer_browser_#{table} FROM browser_ordinary")

    for sql <- ActivationPreparationSchema.statements(), do: F.q!(Migration, sql)
    F.provision!()
    conn = F.connection!("browser_admin")

    for sql <-
          ActivationPreparationSchema.provisioning_statements(
            "browser_writer",
            "browser_lifecycle",
            "browser_schema_owner"
          ),
        do: Postgrex.query!(conn, sql, [])

    GenServer.stop(conn)

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture.invalid','console','human',true,1)"
    )

    F.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES('person-1','human',true,0,1)")

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)"
    )

    fixture = start_supervised!(TLSFixture)
    auth = GenServer.call(fixture, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})
    wrong = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "key1", "alg" => "RS256", "use" => "sig"})

    jwks = Jason.encode!(%{"keys" => [public]})
    TLSFixture.configure(fixture, {:body, jwks})

    profile = %{
      profile_id: "humans",
      profile_version: 1,
      issuer: "https://issuer.fixture.invalid",
      audience: "mixer-api",
      client_id: "console",
      identity_class: :human,
      enabled: true
    }

    entry = %{
      profile: profile,
      jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
      transport: :hosted_https
    }

    object = %{
      "version" => 1,
      "public_origin" => "https://console.fixture.invalid",
      "profile_id" => "humans",
      "profile_version" => 1,
      "issuer" => profile.issuer,
      "client_id" => "console",
      "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://issuer.fixture.invalid/authorize",
      "token_endpoint" => "https://issuer.fixture.invalid/token",
      "id_token_jwks_endpoint" => "https://issuer.fixture.invalid/oidc/keys",
      "redirect_uri" => "https://console.fixture.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://fixture/client",
      "session_vault_ref" => "vault://fixture/browser",
      "scope" =>
        if(create,
          do: "openid mixer.workspace.read mixer.build.read mixer.build.create",
          else: "openid mixer.workspace.read mixer.build.read"
        ),
      "response_mode" => "query",
      "response_iss_required" => true
    }

    identity = %MixerHosted.Identity.StartupConfig{
      mode: :configured,
      owner_options: [
        manifest: [entry],
        generation: 1,
        binding: "humans",
        ca_roots: [auth.ca],
        resolvers: [{{127, 0, 0, 1}, 9}],
        fixture: Map.take(auth, [:ip, :port])
      ]
    }

    {:ok, config} =
      Config.load(
        %{
          "MIXER_BROWSER_AUTH_MODE" => "configured",
          "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
        },
        :api,
        identity
      )

    {:ok, digest} = ConfigurationDigest.digest(config)

    {:ok, custody} =
      Custody.new(config.session_vault_ref, %{
        reference: config.session_vault_ref,
        key_id: "r512",
        key_bytes: :crypto.strong_rand_bytes(32)
      })

    ordinary =
      settings
      |> Keyword.put(:username, "browser_ordinary")
      |> Keyword.put(:pool_size, 1)
      |> Keyword.put(:ssl, false)

    life = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_ordinary_installation_r1422",
      username: "browser_lifecycle",
      password: "synthetic",
      pool_size: 2,
      pool_count: 1,
      timeout: 5000,
      connect_timeout: 5000,
      queue: false,
      show_sensitive_data_on_connection_error: false,
      ssl: false
    ]

    runtime = %RuntimeConfig{
      admission_profile: :build_catalog_v3,
      mode: :configured,
      browser_config: config,
      configuration_digest: digest,
      lifecycle_repo: life,
      expected_roles: %{
        lifecycle_login: "browser_lifecycle",
        writer: "browser_writer",
        relation_owner: "browser_schema_owner",
        ordinary_runtime_login: "browser_ordinary"
      },
      custody: custody
    }

    for sql <- MixerHosted.BrowserAuth.ActiveReadSchema.statements(), do: F.q!(Migration, sql)
    conn = F.connection!("browser_admin")

    for sql <- MixerHosted.BrowserAuth.ActiveReadSchema.provisioning_statements(),
        do: Postgrex.query!(conn, sql, [])

    GenServer.stop(conn)

    unless Code.ensure_loaded?(MixerHosted.Repo.Migrations.AddBuildJournals),
      do: Code.require_file("priv/repo/migrations/20261025000000_add_build_journals.exs")

    :ok =
      Ecto.Migrator.up(
        Migration,
        20_261_025_000_000,
        MixerHosted.Repo.Migrations.AddBuildJournals,
        log: false
      )

    :ok = Ecto.Migrator.up(Migration, 1, R1026.ObanMigration, log: false)
    F.q!(Migration, MixerHosted.CustomerBuilds.Schema.ddl())

    F.q!(
      Migration,
      "REVOKE ALL ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) FROM PUBLIC"
    )

    F.q!(
      Migration,
      "GRANT EXECUTE ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) TO browser_ordinary"
    )

    now = System.system_time(:second)
    {:ok, snapshot} = TrustSnapshot.new(profile, jwks, now, now + 300)
    provider = start_supervised!({R686.Provider, %{key: key, wrong_key: wrong, config: config}})

    {:ok, :ok} =
      Migration.transaction(fn ->
        Enum.each(MixerHosted.CustomerArtifacts.Schema.statements(), &F.q!(Migration, &1))
      end)

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES('org-a',true,'Visible'),('org-b',true,'Hidden')"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_projects(organization_id,id,active,display_name) VALUES('org-a','project-a',true,'Project A'),('org-b','project-b',true,'Project B')"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_applications VALUES('org-a','project-a','fieldlog',true)"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_memberships VALUES('member-a','person-1','org-a',NULL,'all_projects','viewer',true,0,NULL,1)"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_organization_heads SELECT id,1 FROM public.mixer_authz_organizations"
    )

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_project_heads SELECT organization_id,id,1 FROM public.mixer_authz_projects"
    )

    for n <- 0..51 do
      id = "r604-" <> String.pad_leading(Integer.to_string(n), 2, "0")

      F.q!(
        Admin,
        "INSERT INTO public.mixer_authz_organizations(id,active,display_name) VALUES($1,true,$1)",
        [id]
      )

      F.q!(Admin, "INSERT INTO public.mixer_authz_organization_heads VALUES($1,1)", [id])

      F.q!(
        Admin,
        "INSERT INTO public.mixer_authz_memberships VALUES($1,'person-1',$2,NULL,'all_projects','viewer',true,0,NULL,1)",
        ["member-" <> id, id]
      )

      F.q!(
        Admin,
        "INSERT INTO public.mixer_authz_projects(organization_id,id,active,display_name) VALUES('org-a',$1,true,$1)",
        [id]
      )

      F.q!(Admin, "INSERT INTO public.mixer_authz_project_heads VALUES('org-a',$1,1)", [id])
    end

    authorization =
      start_supervised!(%{
        id: :ordinary_fixture_authorization,
        start:
          {Bandit, :start_link,
           [
             [
               plug: {R686.AuthorizationHTTP, %{provider: provider, config: config}},
               ip: {127, 0, 0, 1},
               port: 0,
               startup_log: false
             ]
           ]}
      })

    {:ok, {_, provider_port}} = ThousandIsland.listener_info(authorization)

    for sql <- MixerHosted.CustomerBuildCatalog.Schema.private_statements(), do: F.q!(Admin, sql)

    base = MixerHosted.RuntimeConfig.load!(MixerHosted.Identity.StartupFixture.foundation_env())

    endpoint =
      Application.fetch_env!(:mixer_hosted, MixerHostedWeb.Endpoint)
      |> Keyword.merge(base.endpoint)
      |> Keyword.put(:http, ip: {127, 0, 0, 1}, port: 0)

    hosted = %{
      base
      | repo: ordinary,
        endpoint: endpoint,
        identity_startup: identity,
        oban: [
          repo: Admin,
          queues: false,
          plugins: false,
          peer: false,
          insert_trigger: false,
          testing: :manual
        ]
    }

    installation = Installation.fixture!(runtime, config, snapshot, provider)

    %{
      runtime: runtime,
      config: config,
      provider: provider,
      fixture: fixture,
      identity: identity,
      hosted: hosted,
      installation: installation,
      provider_port: provider_port,
      browser_env: %{
        "MIXER_BROWSER_AUTH_MODE" => "configured",
        "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
      }
    }
  end

  def raw(cookie, c) do
    conn = F.connection!()

    {:ok, s} =
      F.call(conn, :load, [:crypto.hash(:sha256, cookie), c.runtime.configuration_digest])

    GenServer.stop(conn)
    s
  end

  def headers(cookie), do: [{"cookie", "__Host-mixer-session=" <> cookie}]

  def leases_clean do
    assert map_size(:sys.get_state(RuntimeOwner).operations) == 0
  end

  def http(c, path, headers, method \\ "GET", body \\ "") do
    {:ok, s} = :gen_tcp.connect({127, 0, 0, 1}, c.http_port, [:binary, active: false], 2000)

    request = [
      method,
      " ",
      path,
      " HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n",
      Enum.map(headers, fn {k, v} -> [k, ": ", v, "\r\n"] end),
      "\r\n",
      body
    ]

    :ok = :gen_tcp.send(s, request)

    collect = fn again, acc ->
      case :gen_tcp.recv(s, 0, 7000) do
        {:ok, b} ->
          if c[:wire_observer], do: send(c.wire_observer, {:http_bytes, byte_size(b)})
          again.(again, acc <> b)

        {:error, :closed} ->
          acc

        _ ->
          raise "closed HTTP transport failure"
      end
    end

    raw = collect.(collect, "")
    :gen_tcp.close(s)
    [head, body] = String.split(raw, "\r\n\r\n", parts: 2)
    [line | hs] = String.split(head, "\r\n")
    [_, code | _] = String.split(line, " ")
    %{status: String.to_integer(code), body: body, headers: hs}
  end

  def response_header(r, name) do
    prefix = name <> ": "
    for h <- r.headers, String.starts_with?(h, prefix), do: String.replace_prefix(h, prefix, "")
  end

  def response_cookie(r) do
    [cookie] = response_header(r, "set-cookie")
    assert String.contains?(cookie, "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=")
    [pair | _] = String.split(cookie, ";")
    "__Host-mixer-session=" <> token = pair
    assert Protocol.token?(token)
    token
  end

  def bootstrap_http(c) do
    r = http(c, "/auth/session", [])
    assert r.status == 200
    p = response_cookie(r)
    csrf = Jason.decode!(r.body)["csrf_token"]
    assert {:ok, loaded} = RuntimeOwner.load(p)
    assert loaded.cookie == p and loaded.csrf == csrf
    %{cookie: p, csrf: csrf}
  end

  def begin_http(c, p) do
    hs = headers(p.cookie) ++ [{"origin", c.config.public_origin}, {"x-mixer-csrf", p.csrf}]
    r = http(c, "/auth/login", hs, "POST")
    assert r.status == 303
    assert response_header(r, "set-cookie") == []
    [location] = response_header(r, "location")
    uri = URI.parse(location)
    assert uri.scheme <> "://" <> uri.host <> uri.path == c.config.authorization_endpoint
    v = URI.decode_query(uri.query)
    assert v["response_type"] == "code" and v["response_mode"] == "query"
    assert v["redirect_uri"] == c.config.redirect_uri
    assert v["client_id"] == c.config.client_id and v["code_challenge_method"] == "S256"
    assert Protocol.token?(v["state"]) and Protocol.token?(v["nonce"])
    # The synthetic provider receives only the HTTP-produced authorization query.
    provider_response = http(%{http_port: c.provider_port}, "/authorize?" <> uri.query, [])
    assert provider_response.status == 302
    [callback] = response_header(provider_response, "location")
    assert String.starts_with?(callback, c.config.redirect_uri <> "?")
    query = URI.parse(callback).query
    %{headers: headers(p.cookie), query: query, cookie: p.cookie}
  end

  def compiled_catalog_join(c, cookie, page, phase, expected) do
    root = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")

    fixture =
      Path.join(
        System.tmp_dir!(),
        "mixer-catalog-" <>
          Integer.to_string(System.unique_integer([:positive])) <> "-" <> phase <> ".json"
      )

    output = Path.join(root, "compiled-" <> phase <> ".json")

    File.write!(
      fixture,
      Jason.encode!(%{
        url: "http://127.0.0.1:#{c.http_port}",
        publicOrigin: c.config.public_origin,
        cookie: cookie,
        project: Map.take(page, ["organizationId", "projectId"]),
        phase: phase,
        output: output,
        previous: Path.join(root, "compiled-queued.json")
      })
    )

    try do
      {out, code} =
        System.cmd(
          System.find_executable("node") || raise("node unavailable"),
          [System.fetch_env!("MIXER_BROWSER_CATALOG_NODE_DRIVER"), fixture],
          stderr_to_stdout: true
        )

      File.write!(Path.join(root, "node-" <> phase <> ".stdout"), out)
      assert code == 0, out
      result = output |> File.read!() |> Jason.decode!()
      assert result["status"] == "PASS"
      assert result["dto"] == expected
      assert map_size(result["selection"]) == 8
    after
      File.rm!(fixture)
    end
  end

  def catalog_fixture_rows do
    builds =
      F.q!(
        Admin,
        "SELECT id::text, request_key, revision, journal FROM mixer_builds WHERE organization_id='org-a' AND project_id='project-a' AND application_id='fieldlog' AND build_id='build-a' AND platform='ios'"
      ).rows

    jobs =
      F.q!(
        Admin,
        "SELECT id, args FROM oban_jobs WHERE args->>'organization_id'='org-a' AND args->>'project_id'='project-a' AND args->>'application_id'='fieldlog' AND args->>'build_id'='build-a' AND args->>'platform'='ios' ORDER BY id"
      ).rows

    %{builds: builds, jobs: jobs}
  end

  def own_catalog_fixture! do
    assert catalog_fixture_rows() == %{builds: [], jobs: []}

    assert [] ==
             F.q!(
               Admin,
               "SELECT id FROM mixer_authz_applications WHERE (organization_id='org-a' AND project_id='project-a' AND id='empty-app') OR (organization_id='org-b' AND project_id='project-b' AND id='fieldlog')"
             ).rows

    root = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
    owner = Path.join(root, "owned-build.json")
    File.write!(Path.join(root, "prior-absence.json"), Jason.encode!(catalog_fixture_rows()))

    on_exit(fn ->
      if File.exists?(owner) do
        %{"build_id" => id, "job_ids" => jobs} = owner |> File.read!() |> Jason.decode!()
        rows = catalog_fixture_rows()

        assert Enum.all?(rows.builds, fn [actual, key, _, _] ->
                 actual == id and key == "r1104-build"
               end)

        assert Enum.all?(rows.jobs, fn [job, args] ->
                 job in jobs and args["build_record_id"] == id
               end)

        {:ok, cleaned} =
          Admin.transaction(fn ->
            deleted_jobs =
              F.q!(
                Admin,
                "DELETE FROM oban_jobs WHERE id=ANY($1::bigint[]) AND args->>'build_record_id'=$2 RETURNING id",
                [jobs, id]
              ).rows

            deleted_build =
              F.q!(
                Admin,
                "DELETE FROM mixer_builds WHERE id=$1::uuid AND request_key='r1104-build' AND organization_id='org-a' AND project_id='project-a' AND application_id='fieldlog' AND build_id='build-a' AND platform='ios' RETURNING id::text",
                [Ecto.UUID.dump!(id)]
              ).rows

            assert deleted_build == [[id]]
            assert Enum.sort(List.flatten(deleted_jobs)) == Enum.sort(jobs)

            apps =
              F.q!(
                Admin,
                "DELETE FROM mixer_authz_applications WHERE (organization_id='org-a' AND project_id='project-a' AND id='empty-app') OR (organization_id='org-b' AND project_id='project-b' AND id='fieldlog') RETURNING organization_id,project_id,id"
              ).rows

            %{
              build_id: id,
              job_ids: jobs,
              removed_applications: apps,
              terminal_before_cleanup: rows
            }
          end)

        assert catalog_fixture_rows() == %{builds: [], jobs: []}
        File.write!(Path.join(root, "fixture-cleanup.json"), Jason.encode!(cleaned))
      end
    end)
  end

  def capture_catalog_fixture! do
    %{builds: [[id, "r1104-build", 0, _]], jobs: jobs} = catalog_fixture_rows()
    assert jobs != []
    assert Enum.all?(jobs, fn [_, args] -> args["build_record_id"] == id end)

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "owned-build.json"),
      Jason.encode!(%{build_id: id, job_ids: Enum.map(jobs, &hd/1)})
    )
  end

  def build_selection do
    %{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "fieldlog",
      build_id: "build-a",
      platform: "ios",
      source_sha256: String.duplicate("a", 64),
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }
  end

  def build_path(selection), do: "/console-api/v1/builds?" <> URI.encode_query(selection)

  def create_build do
    s = build_selection()

    spec =
      Map.take(s, [:organization_id, :project_id, :application_id, :build_id])
      |> Map.merge(%{
        platform: :ios,
        source: %{kind: :revision, sha256: s.source_sha256, reference: "immutable-test-revision"},
        toolchain_lock_sha256: s.toolchain_lock_sha256,
        build_definition_sha256: s.build_definition_sha256
      })

    multi =
      MixerHosted.Builds.Storage.create_multi(
        Ecto.Multi.new(),
        :build,
        spec,
        %{max_attempts: 2, timeout_ms: 100, retry_backoff_ms: 0},
        "r1104-build",
        0,
        &MixerHosted.Builds.Coordinator.new/1
      )

    assert {:ok, _} = Admin.transaction(multi)
    s
  end
end

defmodule MixerHosted.Test.OrdinaryBrowserStartupFixture.Database do
  alias MixerHosted.BrowserAuth.StorageFixture, as: Original
  defdelegate port(), to: Original
  defdelegate q!(repo, sql, params \\ []), to: Original
  defdelegate call(conn, name, args), to: Original
  def install!, do: Original.install!()

  def connection!(role \\ "browser_lifecycle", database \\ "browser_ordinary_installation_r1422") do
    {:ok, conn} =
      Postgrex.start_link(
        hostname: "127.0.0.1",
        port: port(),
        username: role,
        database: database,
        ssl: false,
        backoff_type: :stop
      )

    Process.unlink(conn)
    Postgrex.query!(conn, "SET statement_timeout='5s'", [])
    Postgrex.query!(conn, "SET lock_timeout='500ms'", [])
    Postgrex.query!(conn, "SET idle_in_transaction_session_timeout='5s'", [])
    conn
  end

  def provision! do
    conn = connection!("browser_admin")

    try do
      for sql <-
            MixerHosted.BrowserAuth.StorageSchema.provisioning_statements(
              "browser_writer",
              "browser_lifecycle"
            ),
          do: Postgrex.query!(conn, sql, [])
    after
      GenServer.stop(conn)
    end
  end
end
