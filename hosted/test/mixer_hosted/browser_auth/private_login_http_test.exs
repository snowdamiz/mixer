defmodule R942.ReceiptFault do
  def handle(_, _, %{query: "begin"}, :missing) do
    :telemetry.detach({MixerHosted.BrowserAuth.Store, :transaction_receipt})
  end

  def handle(_, _, _, _), do: :ok
end

Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserLoginHTTPTest do
  use ExUnit.Case, async: false

  alias MixerHosted.BrowserAuth.{
    RuntimeOwner,
    RuntimeConfig,
    Config,
    ConfigurationDigest,
    Custody,
    LifecycleRepo,
    ProviderOwner,
    ActivationPreparationSchema,
    Vault,
    StoredSnapshot,
    Protocol
  }

  alias R966.LoginFixture, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.Identity.{KeyOwner, TLSFixture, TrustSnapshot}

  setup_all do
    conn = F.connection!("browser_admin", "postgres")

    try do
      Postgrex.query!(
        conn,
        "CREATE DATABASE browser_login_storage OWNER browser_schema_owner",
        []
      )
    after
      GenServer.stop(conn)
    end

    on_exit(fn ->
      conn = F.connection!("browser_admin", "postgres")

      try do
        Postgrex.query!(conn, "DROP DATABASE browser_login_storage", [])
      after
        GenServer.stop(conn)
      end
    end)

    for app <- [:ecto_sql, :postgrex, :jason, :jose, :mint, :ssl, :bandit],
        do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_login_storage",
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

    workers = start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: R686.Workers})

    start_supervised!(%{
      id: KeyOwner,
      start:
        {KeyOwner, :start_fixture,
         [
           [
             name: KeyOwner,
             manifest: [entry],
             generation: 1,
             binding: "humans",
             ca_roots: [auth.ca],
             resolvers: [{{127, 0, 0, 1}, 9}],
             worker_supervisor: R686.Workers,
             fixture: Map.take(auth, [:ip, :port])
           ]
         ]},
      shutdown: :infinity
    })

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
      "scope" => "openid mixer.workspace.read mixer.build.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }

    identity = %MixerHosted.Identity.StartupConfig{
      mode: :configured,
      owner_options: [manifest: [entry], binding: "humans"]
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
      settings |> Keyword.put(:username, "browser_ordinary") |> Keyword.put(:pool_size, 1)

    previous_repo = Application.fetch_env(:mixer_hosted, MixerHosted.Repo)

    on_exit(fn ->
      case previous_repo do
        {:ok, value} -> Application.put_env(:mixer_hosted, MixerHosted.Repo, value)
        :error -> Application.delete_env(:mixer_hosted, MixerHosted.Repo)
      end
    end)

    Application.put_env(:mixer_hosted, MixerHosted.Repo, ordinary)
    start_supervised!({MixerHosted.Repo, ordinary})

    commit_proxy = start_supervised!({R932.PhaseCommitProxy, F.port()})

    life = [
      hostname: "127.0.0.1",
      port: GenServer.call(commit_proxy, :port),
      database: "browser_login_storage",
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

    start_supervised!({LifecycleRepo, life})

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

    assert {:ok, :function_surface_verified} =
             LifecycleRepo.transaction(
               fn ->
                 F.q!(LifecycleRepo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

                 for setting <- [
                       "search_path=pg_catalog",
                       "jit=off",
                       "statement_timeout='5s'",
                       "lock_timeout='500ms'",
                       "idle_in_transaction_session_timeout='5s'",
                       "bytea_output='hex'"
                     ],
                     do: F.q!(LifecycleRepo, "SET LOCAL " <> setting)

                 MixerHosted.BrowserAuth.Catalog.check_function_surface!(
                   LifecycleRepo,
                   runtime.expected_roles,
                   System.monotonic_time(:millisecond) + 5000,
                   2
                 )
               end,
               log: false
             )

    IO.puts("ORIGINAL_CATALOG exact_v2_before_addition=true")
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

    start_supervised!({Oban, repo: Admin, queues: false, plugins: false, testing: :manual})
    now = System.system_time(:second)
    {:ok, snapshot} = TrustSnapshot.new(profile, jwks, now, now + 300)
    provider = start_supervised!({R686.Provider, %{key: key, wrong_key: wrong, config: config}})

    start_supervised!(%{
      id: ProviderOwner,
      start: {ProviderOwner, :start_fixture, [config, snapshot, provider]}
    })

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

    %{
      runtime: runtime,
      config: config,
      provider: provider,
      workers: workers,
      fixture: fixture,
      commit_proxy: commit_proxy
    }
  end

  setup c do
    assert LifecycleRepo.bound?(c.runtime.lifecycle_repo)
    assert MixerHosted.Repo.config()[:username] === "browser_ordinary"
    start_supervised!({RuntimeOwner, c.runtime})
    assert RuntimeOwner.status().phase === :storage_ready
    GenServer.call(c.provider, {:mode, :ok})

    server =
      start_supervised!(%{
        id: :r604_http,
        start: {MixerHostedWeb.BrowserLoginHTTP.Server, :start_link, [[]]}
      })

    {:ok, {_, port}} = ThousandIsland.listener_info(server)

    authorization =
      start_supervised!(%{
        id: :authorization_http,
        start:
          {Bandit, :start_link,
           [
             [
               plug: {R686.AuthorizationHTTP, %{provider: c.provider, config: c.config}},
               ip: {127, 0, 0, 1},
               port: 0,
               startup_log: false
             ]
           ]}
      })

    {:ok, {_, provider_port}} = ThousandIsland.listener_info(authorization)
    %{http_port: port, provider_port: provider_port}
  end

  defp raw(cookie, c) do
    conn = F.connection!()

    {:ok, s} =
      F.call(conn, :load, [:crypto.hash(:sha256, cookie), c.runtime.configuration_digest])

    GenServer.stop(conn)
    s
  end

  defp headers(cookie), do: [{"cookie", "__Host-mixer-session=" <> cookie}]

  defp leases_clean do
    assert map_size(:sys.get_state(RuntimeOwner).operations) == 0
  end

  defp http(c, path, headers, method \\ "GET", body \\ "") do
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

  defp expiry(c, cookie) do
    assert {:ok, s} = StoredSnapshot.decode(raw(cookie, c))

    assert {:ok, %Vault.Active{access_token: token}} =
             Vault.open(
               c.runtime.custody.key,
               s.session_envelope.context,
               s.session_envelope.sealed
             )

    assert {:ok, i} =
             MixerHosted.Identity.ConfiguredVerifier.authenticate(
               KeyOwner,
               "humans",
               token,
               System.system_time(:second)
             )

    {s, i, min(i.expires_at, min(s.browser["idle_expires_at"], s.browser["absolute_expires_at"]))}
  end

  defp response_header(r, name) do
    prefix = name <> ": "
    for h <- r.headers, String.starts_with?(h, prefix), do: String.replace_prefix(h, prefix, "")
  end

  defp response_cookie(r) do
    [cookie] = response_header(r, "set-cookie")
    assert String.contains?(cookie, "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=")
    [pair | _] = String.split(cookie, ";")
    "__Host-mixer-session=" <> token = pair
    assert Protocol.token?(token)
    token
  end

  defp bootstrap_http(c) do
    r = http(c, "/auth/session", [])
    assert r.status == 200
    p = response_cookie(r)
    csrf = Jason.decode!(r.body)["csrf_token"]
    assert {:ok, loaded} = RuntimeOwner.load(p)
    assert loaded.cookie == p and loaded.csrf == csrf
    %{cookie: p, csrf: csrf}
  end

  defp begin_http(c, p) do
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

  defp compiled_build_read(c, selected, cookie, phase, wire) do
    [values] =
      F.q!(
        Admin,
        "SELECT organization_id,project_id,application_id,build_id,platform,request_key,revision,journal FROM public.mixer_builds"
      ).rows

    record =
      Map.new(
        Enum.zip(
          ~w(organization_id project_id application_id build_id platform request_key revision journal)a,
          values
        )
      )

    assert {:ok, projected} = MixerHosted.CustomerBuilds.Snapshot.project(record, selected)
    expected = projected |> Jason.encode!() |> Jason.decode!()
    assert expected === wire
    assert {:ok, restored} = MixerHosted.Builds.Journal.restore(record.journal)
    assert {:ok, status} = MixerHosted.Builds.Lifecycle.customer_status(restored)
    assert wire["attempt"] === status.attempt
    assert wire["maxAttempts"] === status.max_attempts
    assert wire["state"] === Atom.to_string(status.state)
    assert wire["revision"] === length(record.journal["events"])

    fixture =
      Path.join(
        System.tmp_dir!(),
        "browser-build-client-" <>
          Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false) <> ".json"
      )

    File.write!(
      fixture,
      Jason.encode!(%{port: c.http_port, cookie: cookie, dto: expected, phase: phase})
    )

    try do
      {out, code} =
        System.cmd("node", [System.fetch_env!("MIXER_BROWSER_BUILD_NODE_DRIVER"), fixture],
          stderr_to_stdout: true
        )

      assert code == 0, out
      assert out =~ ~s("status":"PASS"), out
    after
      File.rm!(fixture)
    end
  end

  defp compiled_catalog_join(c, cookie, page, phase, expected) do
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

  defp catalog_fixture_rows do
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

  defp own_catalog_fixture! do
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

  defp capture_catalog_fixture! do
    %{builds: [[id, "r1104-build", 0, _]], jobs: jobs} = catalog_fixture_rows()
    assert jobs != []
    assert Enum.all?(jobs, fn [_, args] -> args["build_record_id"] == id end)

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "owned-build.json"),
      Jason.encode!(%{build_id: id, job_ids: Enum.map(jobs, &hd/1)})
    )
  end

  defp build_selection do
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

  defp build_path(selection), do: "/console-api/v1/builds?" <> URI.encode_query(selection)

  defp create_build do
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

  # R1166 explicit private catalog authority installer; production migration set unchanged.
  setup_all c do
    observe = fn profile, expected ->
      runtime = %{c.runtime | admission_profile: profile}
      pid = start_supervised!({RuntimeOwner, runtime})
      assert RuntimeOwner.status().phase === expected
      result = RuntimeOwner.bootstrap(%{request_id: String.duplicate("a", 32)})

      if expected == :storage_ready do
        assert match?({:ok, _}, result), inspect(result)
      else
        assert match?({:error, _}, result), inspect(result)
      end

      assert Process.alive?(pid)
      stop_supervised!(RuntimeOwner)
      %{profile: profile, startup: expected, subsequent_store: inspect(elem(result, 0))}
    end

    baseline = [
      observe.(:browser_auth_v2, :storage_ready),
      observe.(:build_catalog_v3, :unavailable)
    ]

    for sql <- MixerHosted.CustomerBuildCatalog.Schema.private_statements(), do: F.q!(Admin, sql)

    installed = [
      observe.(:browser_auth_v2, :unavailable),
      observe.(:build_catalog_v3, :storage_ready)
    ]

    File.write!(
      Path.join(
        System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
        "four-startup-store-cases.json"
      ),
      Jason.encode!(%{baseline: baseline, installed: installed})
    )

    :ok
  end

  @tag :catalog_browser_current_surface_join
  @tag :r1158
  test "R1158 genuine PKCE application selection catalog queued detail terminal refresh", c do
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

  @tag :r1104
  test "R1104 genuine PKCE cookie admits exact queued and terminal build then closed refusals",
       c do
    selected = create_build()

    [[false, false, false]] =
      F.q!(
        MixerHosted.Repo,
        "SELECT rolsuper,rolbypassrls,has_table_privilege(current_user,'public.mixer_builds','SELECT') FROM pg_roles WHERE rolname=current_user"
      ).rows

    p = bootstrap_http(c)
    login = begin_http(c, p)
    response = http(c, "/auth/callback?" <> login.query, login.headers)
    assert response.status == 303
    cookie = response_cookie(response)
    hs = headers(cookie)
    assert cookie != p.cookie

    before =
      F.q!(
        Admin,
        "SELECT (SELECT count(*) FROM public.oban_jobs),(SELECT count(*) FROM public.mixer_builds)"
      ).rows

    r = http(c, build_path(selected), hs)
    assert r.status == 200, inspect(r)
    dto = Jason.decode!(r.body)["build"]
    assert map_size(dto) == 14
    assert dto["state"] == "queued" and dto["revision"] == 0

    for {wire, key} <- [
          {"organizationId", :organization_id},
          {"projectId", :project_id},
          {"applicationId", :application_id},
          {"buildId", :build_id},
          {"platform", :platform},
          {"sourceSha256", :source_sha256},
          {"toolchainLockSha256", :toolchain_lock_sha256},
          {"buildDefinitionSha256", :build_definition_sha256}
        ],
        do: assert(dto[wire] == selected[key])

    assert response_header(r, "cache-control") == ["no-store"]
    assert response_header(r, "set-cookie") == []
    assert [id] = response_header(r, "x-request-id")
    assert byte_size(id) == 32

    assert F.q!(
             Admin,
             "SELECT (SELECT count(*) FROM public.oban_jobs),(SELECT count(*) FROM public.mixer_builds)"
           ).rows == before

    leases_clean()

    File.write!(
      System.fetch_env!("R1104_POSITIVE"),
      Jason.encode!(%{
        queued: dto,
        rotated_cookie: true,
        actual_HTTP: true,
        ordinary_role: "browser_ordinary",
        direct_build_select: false,
        no_read_job_or_row_insert: true
      })
    )

    IO.puts("R1104_FIRST_GENUINE_HTTP_GATE_PASS queued exact DTO cookie-only")
    compiled_build_read(c, selected, cookie, "queued", dto)

    [[journal]] = F.q!(Admin, "SELECT journal FROM public.mixer_builds").rows
    assert {:ok, build} = MixerHosted.Builds.Journal.restore(journal)
    assert {:ok, ref} = MixerHosted.Builds.Lifecycle.worker_ref(build)

    assert {:ok, running, _, :applied} =
             MixerHosted.Builds.Journal.append(journal, "start", %{type: :start, ref: ref}, 1)

    assert {:ok, terminal, _, :applied} =
             MixerHosted.Builds.Journal.append(
               running,
               "fail",
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

    F.q!(Admin, "UPDATE public.mixer_builds SET journal=$1,revision=2", [terminal])
    result = http(c, build_path(selected), hs)
    assert result.status == 200
    assert Jason.decode!(result.body)["build"]["state"] == "failed"
    assert Jason.decode!(result.body)["build"]["failureCode"] == "compiler_error"
    compiled_build_read(c, selected, cookie, "terminal", Jason.decode!(result.body)["build"])
    assert http(c, "/auth/session", hs).status == 200
    assert http(c, "/console-api/v1/orgs?limit=1", hs).status == 200
    assert http(c, "/console-api/v1/projects?organization_id=org-a&limit=1", hs).status == 200

    for {key, value} <- [
          organization_id: "org-b",
          project_id: "project-b",
          application_id: "other",
          build_id: "other",
          platform: "android",
          source_sha256: String.duplicate("e", 64),
          toolchain_lock_sha256: String.duplicate("e", 64),
          build_definition_sha256: String.duplicate("e", 64)
        ] do
      bad = http(c, build_path(Map.put(selected, key, value)), hs)
      assert bad.status in [403, 404], inspect({key, bad})
      refute Map.has_key?(Jason.decode!(bad.body), "build")
    end

    path = build_path(selected)

    for bad <- [
          path <> "&build_id=build-a",
          path <> "&authority=true",
          String.replace(path, "build_id=build-a", "build_id=%GG"),
          String.replace(path, "build_id=build-a", "build_id=%2f"),
          String.replace(path, "build_id=build-a", "%62uild_id=build-a")
        ] do
      assert http(c, bad, hs).status == 400
    end

    assert http(c, path, hs ++ hs).status == 400
    assert http(c, path, hs ++ [{"authorization", "Bearer fake"}]).status == 400
    assert http(c, path, hs ++ [{"content-length", "1"}], "GET", "x").status == 400
    assert http(c, path, hs, "POST").status == 404

    assert http(c, "/v3/orgs/org-a/projects/project-a/apps/fieldlog/builds/build-a/ios", hs).status ==
             404

    F.q!(Admin, "UPDATE public.mixer_authz_memberships SET active=false WHERE id='member-a'")
    assert http(c, path, hs).status in [403, 404]
    F.q!(Admin, "UPDATE public.mixer_authz_memberships SET active=true WHERE id='member-a'")
    assert http(c, path, hs).status == 200
    F.q!(Admin, "UPDATE public.mixer_authz_credentials SET active=false")
    assert http(c, path, hs).status == 503
    F.q!(Admin, "UPDATE public.mixer_authz_credentials SET active=true")
    F.q!(Admin, "UPDATE public.mixer_authz_families SET active=false")
    assert http(c, path, hs).status == 503
    F.q!(Admin, "UPDATE public.mixer_authz_families SET active=true")
    assert http(c, path, hs).status == 200
    leases_clean()

    GenServer.call(c.provider, {:mode, :no_build_scope})
    next = bootstrap_http(c)
    second = begin_http(c, next)
    missing = http(c, "/auth/callback?" <> second.query, second.headers)
    assert missing.status == 303
    missing_cookie = response_cookie(missing)
    assert http(c, path, headers(missing_cookie)).status == 403
    assert http(c, "/auth/session", headers(missing_cookie)).status == 200
    GenServer.call(c.provider, {:mode, :ok})
    leases_clean()
    stop_supervised!(RuntimeOwner)
    assert http(c, path, hs).status == 503

    start_supervised!(
      {RuntimeOwner,
       %RuntimeConfig{
         mode: :disabled,
         browser_config: nil,
         configuration_digest: nil,
         lifecycle_repo: nil,
         expected_roles: nil,
         custody: nil
       }}
    )

    assert http(c, path, hs).status == 503

    File.write!(
      System.fetch_env!("R1104_CONTROLS"),
      Jason.encode!(%{
        terminal: true,
        eight_selection_refusals: true,
        raw_duplicates: true,
        malformed_query: true,
        no_build_scope: true,
        revoked_credential: true,
        revoked_family: true,
        revoked_membership: true,
        existing_reads: true,
        missing_disabled_runtime: true,
        leases_clean: true
      })
    )
  end

  test "raw HTTP bootstrap PKCE callback rotates cookie then unchanged client reads", c do
    p = bootstrap_http(c)
    l = begin_http(c, p)
    before = GenServer.call(c.provider, :count)
    r = http(c, "/auth/callback?" <> l.query, l.headers)
    assert r.status == 303
    assert response_header(r, "location") == ["/workspace"]
    active_cookie = response_cookie(r)
    refute active_cookie == p.cookie
    assert GenServer.call(c.provider, :count) == before + 1
    assert http(c, "/auth/session", headers(p.cookie)).status == 503
    {_, _, exp} = expiry(c, active_cookie)

    assert Jason.decode!(http(c, "/auth/session", headers(active_cookie)).body)["state"] ==
             "authenticated"

    f = Path.join(System.tmp_dir!(), "client.json")

    File.write!(
      f,
      Jason.encode!(%{
        origin: "http://127.0.0.1:#{c.http_port}",
        firstCookie: Protocol.random_token(),
        activeCookie: active_cookie,
        expires: exp
      })
    )

    File.chmod!(f, 0o600)

    try do
      {out, code} =
        System.cmd("node", [System.fetch_env!("MIXER_BROWSER_READ_NODE_DRIVER"), f],
          stderr_to_stdout: true
        )

      assert code == 0, out
      IO.puts("R686_CLIENT " <> out)
    after
      File.rm!(f)
    end

    replay = http(c, "/auth/callback?" <> l.query, l.headers)
    assert replay.status == 503
    assert response_header(replay, "set-cookie") == []
    assert GenServer.call(c.provider, :count) == before + 1
    leases_clean()

    IO.puts(
      "R686_HTTP valid_bootstrap_begin_callback=true committed_cookie_rotation=true replay_no_cookie=true unchanged_client=true"
    )
  end

  test "raw HTTP duplicates bodies origins arbitrary inputs and aliases fail closed", c do
    p = bootstrap_http(c)
    h = headers(p.cookie)
    hs = h ++ [{"origin", c.config.public_origin}, {"x-mixer-csrf", p.csrf}]
    before = GenServer.call(c.provider, :count)

    for bad <- [
          h,
          hs ++ h,
          hs ++ [{"Origin", c.config.public_origin}],
          hs ++ [{"X-Mixer-CSRF", p.csrf}],
          hs ++ [{"authorization", "Bearer refused"}],
          h ++ [{"origin", "https://evil.invalid"}, {"x-mixer-csrf", p.csrf}]
        ] do
      r = http(c, "/auth/login", bad, "POST")
      assert r.status == 503
      assert response_header(r, "set-cookie") == [] and response_header(r, "location") == []
    end

    for query <- [
          "?redirect_uri=https://evil.invalid",
          "?tenant=org-b",
          "?token=caller",
          "?return_to=/evil"
        ] do
      assert http(c, "/auth/login" <> query, hs, "POST").status == 503
    end

    assert http(c, "/auth/login", hs ++ [{"content-length", "1"}], "POST", "x").status == 503

    for path <- ["/auth/login/", "/auth/%6cogin", "/AUTH/login", "/auth/logout"] do
      assert http(c, path, hs, "POST").status == 404
    end

    l = begin_http(c, p)
    state = URI.decode_query(l.query)["state"]

    for query <- [
          l.query <> "&state=" <> state,
          l.query <> "&code=duplicate",
          l.query <> "&%73tate=" <> state,
          l.query <> "&tenant=org-b",
          String.replace(l.query, "state=" <> state, "state=" <> Protocol.random_token())
        ] do
      r = http(c, "/auth/callback?" <> query, h)
      assert r.status == 503
      assert response_header(r, "set-cookie") == []
    end

    assert http(c, "/auth/callback?" <> l.query, h ++ h).status == 503

    assert http(c, "/auth/callback?" <> l.query, h ++ [{"content-length", "1"}], "GET", "x").status ==
             503

    assert GenServer.call(c.provider, :count) == before
    assert http(c, "/auth/callback?" <> l.query, h).status == 303
    leases_clean()

    IO.puts(
      "R686_BOUNDARIES duplicate_headers_query=true csrf_origin=true aliases_caller_choices_body_refused=true"
    )
  end

  test "callback claim transaction rollback never publishes cookie", c do
    p = bootstrap_http(c)
    l = begin_http(c, p)
    provider_before = GenServer.call(c.provider, :count)

    pending = fn ->
      %{rows: rows} =
        F.q!(
          Admin,
          """
          SELECT b.epoch,b.revision,a.status,a.claim_digest IS NULL,a.claimed_at IS NULL
          FROM public.mixer_browser_sessions b
          JOIN public.mixer_browser_oidc_attempts a ON a.browser_id=b.id
          WHERE b.cookie_digest=$1
          """,
          [:crypto.hash(:sha256, p.cookie)]
        )

      rows
    end

    pending_before = pending.()
    assert [[2, 2, "pending", true, true]] = pending_before
    :ok = GenServer.call(c.commit_proxy, {:arm, self()})
    r = http(c, "/auth/callback?" <> l.query, l.headers)
    assert_receive {:activation_aborted, true}, 1000
    assert_receive :actual_commit_rolled_back, 1000
    assert r.status == 503
    assert response_header(r, "set-cookie") == [] and response_header(r, "location") == []
    assert {:ok, snapshot} = StoredSnapshot.decode(raw(p.cookie, c))
    assert snapshot.browser["status"] == "preauth"
    assert http(c, "/auth/session", headers(p.cookie)).status == 503
    assert pending.() == pending_before
    assert GenServer.call(c.provider, :count) == provider_before
    retry = http(c, "/auth/callback?" <> l.query, l.headers)
    assert retry.status == 303
    assert response_header(retry, "location") == ["/workspace"]
    active_cookie = response_cookie(retry)

    assert Jason.decode!(http(c, "/auth/session", headers(active_cookie)).body)["state"] ==
             "authenticated"

    assert GenServer.call(c.provider, :count) == provider_before + 1
    replay = http(c, "/auth/callback?" <> l.query, l.headers)
    assert replay.status == 503 and response_header(replay, "set-cookie") == []
    assert GenServer.call(c.provider, :count) == provider_before + 1

    IO.puts(
      "R686_COMMIT callback_claim_commit_rolled_back=true cookie_withheld=true preauth_row_retained=true pending_revision_retained=true zero_exchange_before_retry=true retry_committed_once=true further_replay_closed=true"
    )

    leases_clean()
  end

  test "bad signed nonce and disabled owner never publish callback cookies", c do
    p = bootstrap_http(c)
    l = begin_http(c, p)
    GenServer.call(c.provider, {:mode, :nonce})
    r = http(c, "/auth/callback?" <> l.query, l.headers)
    assert r.status == 503 and response_header(r, "set-cookie") == []
    stop_supervised(RuntimeOwner)
    assert http(c, "/auth/session", []).status == 503
    assert http(c, "/auth/callback?" <> l.query, l.headers).status == 503
    IO.puts("R686_FAILURE nonce_refused=true owner_absence_no_cookie=true")
  end

  defp independent_state(cookie) do
    %{rows: rows} =
      F.q!(
        Admin,
        """
        SELECT b.status,b.epoch,b.revision,
          (SELECT count(*) FROM public.mixer_browser_sessions WHERE status='active'),
          (SELECT count(*) FROM public.mixer_authz_families),
          (SELECT count(*) FROM public.mixer_authz_credentials)
        FROM public.mixer_browser_sessions b WHERE b.cookie_digest=$1
        """,
        [:crypto.hash(:sha256, cookie)]
      )

    rows
  end

  test "final activation COMMIT barrier withholds bytes until independently visible", c do
    p = bootstrap_http(c)
    l = begin_http(c, p)
    :ok = GenServer.call(c.commit_proxy, {:arm_activation, :barrier, self()})
    parent = self()

    task =
      Task.async(fn ->
        http(Map.put(c, :wire_observer, parent), "/auth/callback?" <> l.query, l.headers)
      end)

    assert_receive {:final_activation_commit, backend, :barrier},
                   2000,
                   "phase-aware final activation COMMIT not observed"

    assert_receive {:activation_barrier, proxy_worker, ^backend}, 1000

    [["preauth", _, _, active_before, families_before, credentials_before]] =
      independent_state(p.cookie)

    %{rows: [["browser_lifecycle", "browser_login_storage", false, false]]} =
      F.q!(
        Admin,
        "SELECT a.usename,a.datname,r.rolsuper,r.rolbypassrls FROM pg_catalog.pg_stat_activity a JOIN pg_catalog.pg_roles r ON r.rolname=a.usename WHERE a.pid=$1",
        [backend]
      )

    refute_receive {:http_bytes, _}, 100
    send(proxy_worker, :release_commit)
    assert_receive {:committed_barrier, reader}, 1000

    %{rows: [[active_after, families_after, credentials_after]]} =
      F.q!(
        Admin,
        "SELECT (SELECT count(*) FROM public.mixer_browser_sessions WHERE status='active'),(SELECT count(*) FROM public.mixer_authz_families),(SELECT count(*) FROM public.mixer_authz_credentials)"
      )

    assert active_after == active_before + 1
    assert families_after == families_before + 1 and credentials_after == credentials_before + 1
    assert independent_state(p.cookie) == []
    refute_receive {:http_bytes, _}, 100
    send(reader, :release_ack)
    r = Task.await(task, 2000)
    assert r.status == 303
    cookie = response_cookie(r)
    assert response_header(r, "location") == ["/workspace"]

    assert Jason.decode!(http(c, "/auth/session", headers(cookie)).body)["state"] ==
             "authenticated"

    File.write!(
      System.fetch_env!("R932_BARRIER_EVIDENCE"),
      Jason.encode!(%{
        phase:
          "mixer_browser_activate Execute + SELECT 1 CommandComplete then same-connection COMMIT",
        backend: backend,
        role: "browser_lifecycle",
        superuser: false,
        bypassrls: false,
        no_bytes_before_commit: true,
        no_bytes_before_ack: true,
        independently_visible_before_ack: true,
        truthful_cookie_and_read_after_ack: true
      })
    )

    leases_clean()
  end

  test "final activation actual COMMIT rollback must never publish activation", c do
    p = bootstrap_http(c)
    l = begin_http(c, p)
    before = independent_state(p.cookie)
    :ok = GenServer.call(c.commit_proxy, {:arm_activation, :abort, self()})
    r = http(c, "/auth/callback?" <> l.query, l.headers)
    assert_receive {:final_activation_commit, backend, :abort}, 1000
    assert_receive {:activation_aborted, true}, 1000
    assert_receive :actual_commit_rolled_back, 1000
    after_state = independent_state(p.cookie)

    %{rows: identity} =
      F.q!(
        Admin,
        "SELECT a.usename,a.datname,r.rolsuper,r.rolbypassrls FROM pg_catalog.pg_stat_activity a JOIN pg_catalog.pg_roles r ON r.rolname=a.usename WHERE a.pid=$1",
        [backend]
      )

    cookies = response_header(r, "set-cookie")

    read =
      if cookies == [],
        do: nil,
        else: http(c, "/auth/session", headers(response_cookie(r))).status

    evidence = %{
      phase:
        "mixer_browser_activate Execute + SELECT 1 CommandComplete then same-connection COMMIT",
      backend: backend,
      identity: identity,
      injected_ready_for_query: "E",
      actual_commit_command_complete: "ROLLBACK",
      independent_before: before,
      independent_after: after_state,
      http_status: r.status,
      active_cookie_header: cookies != [],
      workspace_redirect: response_header(r, "location") == ["/workspace"],
      published_cookie_session_status: read
    }

    File.write!(System.fetch_env!("R932_FAILURE_EVIDENCE"), Jason.encode!(evidence))
    IO.puts("R932_FINAL_COMMIT " <> Jason.encode!(evidence))
    assert after_state == before
    assert r.status == 503
    assert cookies == [] and response_header(r, "location") == []
    leases_clean()
  end

  defp assert_pool_idle do
    %{rows: [[0]]} =
      F.q!(Admin, """
      SELECT count(*) FROM pg_catalog.pg_stat_activity
      WHERE usename='browser_lifecycle' AND state LIKE 'idle in transaction%'
      """)

    assert %{rows: [[1]]} = F.q!(LifecycleRepo, "SELECT 1")
    refute LifecycleRepo.in_transaction?()
    refute LifecycleRepo.checked_out?()
  end

  test "confirmed receipt rejects missing duplicate mismatched and failed tags" do
    store = MixerHosted.BrowserAuth.Store
    event = [:mixer_hosted, :browser_auth, :store, :transaction]
    key = {store, :receipt}
    reference = make_ref()

    metadata = fn query, command, backend ->
      %{
        type: :ecto_sql_query,
        repo: LifecycleRepo,
        options: [store_transaction: {self(), reference}],
        query: query,
        result: {:ok, %Postgrex.Result{command: command, connection_id: backend}}
      }
    end

    observe = fn value -> store.transaction_event(event, %{}, value, nil) end
    reset = fn -> Process.put(key, {self(), reference, :await_begin}) end

    try do
      reset.()
      observe.(metadata.("commit", :commit, 1))
      assert elem(Process.get(key), 2) == :unknown
      reset.()
      observe.(metadata.("begin", :begin, 1))
      observe.(metadata.("commit", :commit, 2))
      assert elem(Process.get(key), 2) == :unknown
      reset.()
      observe.(metadata.("begin", :begin, 1))
      observe.(metadata.("commit", :commit, 1))
      assert elem(Process.get(key), 2) == :committed
      observe.(metadata.("commit", :commit, 1))
      assert elem(Process.get(key), 2) == :unknown
      reset.()
      observe.(metadata.("begin", :begin, 1))
      observe.(metadata.("commit", :rollback, 1))
      assert elem(Process.get(key), 2) == :rolled_back
      reset.()
      observe.(metadata.("begin", :begin, 1))

      observe.(
        Map.put(
          metadata.("commit", :commit, 1),
          :result,
          {:error, %DBConnection.ConnectionError{message: "fixture"}}
        )
      )

      assert elem(Process.get(key), 2) == :unknown

      for options <- [
            [store_transaction: {self(), make_ref()}],
            [store_transaction: {Process.whereis(RuntimeOwner), reference}],
            []
          ] do
        reset.()
        observe.(metadata.("begin", :begin, 1))
        observe.(Map.put(metadata.("commit", :commit, 1), :options, options))
        assert elem(Process.get(key), 2) == :unknown
      end
    after
      Process.delete(key)
    end

    assert Process.get(key) == nil
  end

  test "missing actual Store receipt withholds HTTP cookie and handler registration is bounded",
       c do
    store = MixerHosted.BrowserAuth.Store
    event = [:mixer_hosted, :browser_auth, :store, :transaction]
    handler = {store, :transaction_receipt}
    fault = {__MODULE__, :missing_receipt}
    original_status = RuntimeOwner.status()
    :ok = :telemetry.attach(fault, event, &R942.ReceiptFault.handle/4, :missing)

    try do
      r = http(c, "/auth/session", [])
      assert r.status == 503
      assert response_header(r, "set-cookie") == [] and response_header(r, "location") == []
    after
      :telemetry.detach(fault)
    end

    assert %{phase: :unavailable, generation: generation} = RuntimeOwner.status()
    assert generation == original_status.generation + 1
    r = http(c, "/auth/session", [])
    assert r.status == 503
    assert response_header(r, "set-cookie") == [] and response_header(r, "location") == []
    # Explicitly restore only the handler removed by the fixture; the owner stays unavailable.
    assert :ok =
             :telemetry.attach(
               handler,
               event,
               &MixerHosted.BrowserAuth.Store.transaction_event/4,
               nil
             )

    assert RuntimeOwner.status() == %{phase: :unavailable, generation: generation}
    matching = Enum.filter(:telemetry.list_handlers(event), &(&1.id == handler))
    assert [%{config: nil, function: fun}] = matching
    assert fun == (&MixerHosted.BrowserAuth.Store.transaction_event/4)
    assert_pool_idle()
    leases_clean()
  end

  test "pinned transaction explicit rollback SQL exception and nested admission release checkout",
       c do
    store = MixerHosted.BrowserAuth.Store

    assert {:error, :fixture} =
             LifecycleRepo.transaction(fn -> LifecycleRepo.rollback(:fixture) end, log: false)

    assert_raise Postgrex.Error, fn ->
      LifecycleRepo.transaction(fn -> F.q!(LifecycleRepo, "SELECT 1/0") end, log: false)
    end

    assert_pool_idle()
    parent = self()
    marker = make_ref()

    :sys.replace_state(RuntimeOwner, fn state ->
      result =
        LifecycleRepo.transaction(
          fn ->
            store.admit(c.runtime, System.monotonic_time(:millisecond) + 5000)
          end,
          log: false
        )

      send(parent, {marker, result, Process.get({store, :receipt})})
      state
    end)

    assert_receive {^marker,
                    {:ok,
                     {:error, %MixerHosted.BrowserAuth.Store.Failure{outcome: :not_started}}},
                    nil}

    # The ordinary default is still preauthentication; it cannot reach workspace.
    p = bootstrap_http(c)

    assert Jason.decode!(http(c, "/auth/session", headers(p.cookie)).body)["state"] ==
             "unauthenticated"

    assert_pool_idle()
    leases_clean()
  end

  test "actual transport loss before final COMMIT withholds activation and leaves no live transaction",
       c do
    p = bootstrap_http(c)
    l = begin_http(c, p)
    before = independent_state(p.cookie)
    :ok = GenServer.call(c.commit_proxy, {:arm_activation, :barrier, self()})
    task = Task.async(fn -> http(c, "/auth/callback?" <> l.query, l.headers) end)
    assert_receive {:final_activation_commit, backend, :barrier}, 2000
    assert_receive {:activation_barrier, worker, ^backend}, 1000

    assert %{rows: [[true]]} =
             F.q!(Admin, "SELECT pg_catalog.pg_terminate_backend($1)", [backend])

    send(worker, :release_commit)
    r = Task.await(task, 3000)
    assert r.status == 503
    assert response_header(r, "set-cookie") == [] and response_header(r, "location") == []
    assert independent_state(p.cookie) == before
    assert_pool_idle()
    leases_clean()

    IO.puts(
      "R942_TRANSPORT actual_terminated_final_backend=true no_cookie=true rows_unchanged=true pool_reusable=true"
    )
  end
end
