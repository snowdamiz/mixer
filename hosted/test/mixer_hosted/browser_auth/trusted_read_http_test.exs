Code.require_file("storage_fixture.exs", __DIR__)

defmodule R512.Provider do
  use GenServer
  alias MixerHosted.BrowserAuth.Protocol
  def start_link(opts), do: GenServer.start_link(__MODULE__, opts)
  def init(opts), do: {:ok, Map.merge(opts, %{codes: %{}, mode: :ok, count: 0})}

  def handle_call({:register, query}, _, s) do
    values = URI.decode_query(query)
    code = Protocol.random_token()
    {:reply, code, put_in(s.codes[code], values)}
  end

  def handle_call({:mode, mode}, _, s), do: {:reply, :ok, %{s | mode: mode}}
  def handle_call(:count, _, s), do: {:reply, s.count, s}

  def handle_call({:exchange, r}, _, s) do
    {v, codes} = Map.pop(s.codes, r.code)
    s = %{s | codes: codes, count: s.count + 1}

    valid =
      v !== nil and r.issuer === s.config.issuer and r.client_id === v["client_id"] and
        r.redirect_uri === v["redirect_uri"] and r.token_endpoint === s.config.token_endpoint and
        r.grant_type === "authorization_code" and r.client_auth_method === :client_secret_basic and
        r.client_credential_ref === s.config.client_credential_ref and
        Protocol.pkce_challenge(r.code_verifier) === {:ok, v["code_challenge"]}

    cond do
      not valid or s.mode === :pkce ->
        {:reply, {:error, :invalid_grant}, s}

      s.mode === :late ->
        Process.sleep(1100)
        {:reply, {:error, :late}, s}

      true ->
        now = System.system_time(:second)

        claims = %{
          "iss" => s.config.issuer,
          "aud" => s.config.api_audience,
          "sub" => "subject-1",
          "client_id" => s.config.client_id,
          "iat" => now - 1,
          "exp" => now + if(s.mode === :short, do: 2, else: 120),
          "jti" => Protocol.random_token(),
          "scope" => "mixer.workspace.read"
        }

        access = sign(s.key, claims, "at+jwt")
        <<half::binary-size(16), _::binary>> = :crypto.hash(:sha256, access)

        id = %{
          "iss" => s.config.issuer,
          "aud" => s.config.client_id,
          "sub" => "subject-1",
          "iat" => now - 1,
          "exp" =>
            now +
              case s.mode do
                :short -> 2
                :session_short -> 45
                _ -> 120
              end,
          "nonce" => v["nonce"],
          "at_hash" => Base.url_encode64(half, padding: false)
        }

        id =
          case s.mode do
            :nonce -> Map.put(id, "nonce", Protocol.random_token())
            :aud -> Map.put(id, "aud", "wrong-client")
            :issuer -> Map.put(id, "iss", "https://wrong.example.invalid")
            :link -> Map.put(id, "at_hash", Protocol.random_token())
            :azp -> id |> Map.put("aud", [s.config.client_id, "other"]) |> Map.put("azp", "other")
            :expired -> Map.put(id, "exp", now - 2)
            _ -> id
          end

        token = sign(if(s.mode === :signature, do: s.wrong_key, else: s.key), id, "JWT")
        if is_tuple(s.mode), do: send(elem(s.mode, 1), {:provider_exchange, self()})

        if is_tuple(s.mode) do
          receive do
            :continue -> :ok
          after
            1500 -> :ok
          end
        end

        {:reply,
         {:ok,
          Jason.encode!(%{
            "token_type" => "Bearer",
            "access_token" => access,
            "id_token" => token
          })}, s}
    end
  end

  defp sign(k, c, t),
    do:
      JOSE.JWS.sign(k, Jason.encode!(c), %{"alg" => "RS256", "typ" => t, "kid" => "key1"})
      |> JOSE.JWS.compact()
      |> elem(1)
end

defmodule R576.ReadTest do
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

  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.Identity.{KeyOwner, TLSFixture, TrustSnapshot}

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason, :jose, :mint, :ssl, :bandit],
        do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_storage",
      pool_size: 2,
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

    workers = start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: R512.Workers})

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
             worker_supervisor: R512.Workers,
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
      "scope" => "openid mixer.workspace.read",
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

    ordinary = Keyword.put(settings, :username, "browser_ordinary")
    previous_repo = Application.fetch_env(:mixer_hosted, MixerHosted.Repo)

    on_exit(fn ->
      case previous_repo do
        {:ok, value} -> Application.put_env(:mixer_hosted, MixerHosted.Repo, value)
        :error -> Application.delete_env(:mixer_hosted, MixerHosted.Repo)
      end
    end)

    Application.put_env(:mixer_hosted, MixerHosted.Repo, ordinary)
    start_supervised!({MixerHosted.Repo, ordinary})

    life = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_storage",
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
    now = System.system_time(:second)
    {:ok, snapshot} = TrustSnapshot.new(profile, jwks, now, now + 300)
    provider = start_supervised!({R512.Provider, %{key: key, wrong_key: wrong, config: config}})

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

    %{runtime: runtime, config: config, provider: provider, workers: workers, fixture: fixture}
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
        start: {MixerHostedWeb.BrowserHTTP.Server, :start_link, [[]]}
      })

    {:ok, {_, port}} = ThousandIsland.listener_info(server)
    %{http_port: port}
  end

  defp login(c) do
    {:ok, p} = RuntimeOwner.bootstrap(%{request_id: F.request()})

    headers = [
      {"cookie", "__Host-mixer-session=" <> p.cookie},
      {"origin", c.config.public_origin},
      {"x-mixer-csrf", p.csrf}
    ]

    {:ok, a} = RuntimeOwner.begin_login(p.cookie, headers, :workspace, %{request_id: F.request()})
    uri = URI.parse(a.url)
    code = GenServer.call(c.provider, {:register, uri.query})
    values = URI.decode_query(uri.query)

    query =
      URI.encode_query([{"state", values["state"]}, {"iss", c.config.issuer}, {"code", code}])

    %{preauth: p, headers: [{"cookie", "__Host-mixer-session=" <> p.cookie}], query: query}
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
        {:ok, b} -> again.(again, acc <> b)
        {:error, :closed} -> acc
        _ -> raise "closed HTTP transport failure"
      end
    end

    raw = collect.(collect, "")
    :gen_tcp.close(s)
    [head, body] = String.split(raw, "\r\n\r\n", parts: 2)
    [line | hs] = String.split(head, "\r\n")
    [_, code | _] = String.split(line, " ")
    %{status: String.to_integer(code), body: body, headers: hs}
  end

  defp active(c) do
    l = login(c)
    assert {:ok, r} = RuntimeOwner.callback(l.headers, l.query)
    {l, r}
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

  test "R612 independent authenticated DTO raw HTTP project isolation and secret refusal", c do
    {_l, r} = active(c)
    h = headers(r.cookie)
    {s, _i, exp} = expiry(c, r.cookie)

    assert {:ok, %Vault.Active{access_token: bearer}} =
             Vault.open(
               c.runtime.custody.key,
               s.session_envelope.context,
               s.session_envelope.sealed
             )

    assert {:ok, {:authenticated, csrf, _revision, generation, ^exp}, :unchanged} =
             RuntimeOwner.read_session(h)

    response = http(c, "/auth/session", h)
    assert response.status == 200

    assert Jason.decode!(response.body) == %{
             "state" => "authenticated",
             "csrf_token" => csrf,
             "generation" => generation,
             "expires_at" => exp
           }

    assert exp > System.system_time(:second)
    org = http(c, "/console-api/v1/orgs?limit=2", h)
    project = http(c, "/console-api/v1/projects?organization_id=org-a&limit=2", h)
    hidden = http(c, "/console-api/v1/projects?organization_id=org-b&limit=2", h)
    assert org.status == 200
    assert project.status == 200
    assert hidden.status in [403, 404]

    for item <- [response, org, project, hidden] do
      refute String.contains?(item.body, bearer)
      refute String.contains?(item.body, r.cookie)
      refute String.contains?(item.body, "Bearer ")
      refute Enum.any?(item.headers, &String.starts_with?(String.downcase(&1), "set-cookie:"))
      assert Enum.any?(item.headers, &(&1 == "cache-control: no-store"))
    end

    for path <- [
          "/console-api/v1/projects?organization_id=org-a&organization_id=org-b",
          "/console-api/v1/projects?organization_id=org-a&%6cimit=2",
          "/console-api/v1/projects?organization_id=org-a&limit=0",
          "/console-api/v1/projects?organization_id=org-a&limit=101",
          "/console-api/v1/projects?limit=2",
          "/console-api/v1/projects?organization_id=org-a&cursor=%FF",
          "/console-api/v1/orgs?limit=2&limit=3",
          "/auth/session?csrf_token=caller",
          "/auth/session?generation=caller",
          "/auth/session?expires_at=9999999999"
        ] do
      value = http(c, path, h)
      IO.puts("R612_QUERY " <> Jason.encode!(%{path: path, status: value.status}))
      assert value.status == 400
    end

    for hs <- [
          h ++ [{"Authorization", "Bearer " <> bearer}],
          h ++ [{"cOoKiE", "__Host-mixer-session=" <> r.cookie}],
          [
            {"cookie",
             "__Host-mixer-session=" <> r.cookie <> "; __Host-mixer-session=" <> r.cookie}
          ],
          h ++ [{"x-mixer-csrf", "a"}, {"X-Mixer-Csrf", "b"}],
          h ++ [{"origin", c.config.public_origin}, {"Origin", c.config.public_origin}]
        ] do
      assert http(c, "/auth/session", hs).status == 400
      assert http(c, "/console-api/v1/projects?organization_id=org-a", hs).status == 400
    end

    assert http(c, "/auth/session", h ++ [{"content-length", "1"}], "GET", "x").status == 400

    assert http(c, "/auth/session", h ++ [{"transfer-encoding", "chunked"}], "GET", "0\r\n\r\n").status ==
             400

    leases_clean()

    IO.puts(
      "R612_AUTHENTICATED exact_DTO=true expiry_admitted=true no_bearer_or_cookie_leak=true project_tenant_isolation=true duplicate_headers_queries_refused=true body_refused=true"
    )
  end

  test "R612 independent preauth no mutation methods routes or caller metadata", c do
    {:ok, p} = RuntimeOwner.bootstrap(%{request_id: F.request()})
    h = headers(p.cookie)
    before = GenServer.call(c.provider, :count)

    for method <- ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"] do
      assert http(c, "/auth/session", h, method).status == 404
      assert http(c, "/console-api/v1/projects?organization_id=org-a", h, method).status == 404
    end

    for path <- [
          "/auth/login",
          "/auth/callback",
          "/auth/logout",
          "/v3/projects",
          "/auth/session/",
          "/AUTH/session",
          "/auth/%73ession",
          "/console-api/v1/projects/"
        ] do
      assert http(c, path, h).status == 404
    end

    for path <- [
          "/auth/session",
          "/console-api/v1/orgs",
          "/console-api/v1/projects?organization_id=org-a"
        ] do
      assert http(c, path, [{"authorization", "Bearer caller"}]).status == 400
      denied = http(c, path, headers(Protocol.random_token()))
      IO.puts("R612_UNKNOWN_COOKIE " <> Jason.encode!(%{path: path, status: denied.status}))
      assert denied.status in if(path == "/auth/session", do: [503], else: [401, 503])
    end

    response =
      http(
        c,
        "/auth/session",
        h ++
          [
            {"x-mixer-csrf", Protocol.random_token()},
            {"x-mixer-generation", Protocol.random_token()}
          ]
      )

    assert response.status == 200
    assert Jason.decode!(response.body) == %{"state" => "unauthenticated", "csrf_token" => p.csrf}
    assert GenServer.call(c.provider, :count) == before
    assert {:ok, {:unauthenticated, csrf}, :unchanged} = RuntimeOwner.read_session(h)
    assert csrf == p.csrf
    leases_clean()

    IO.puts(
      "R612_PREAUTH fixed_methods_routes=true no_auth_mutation=true caller_metadata_not_trusted=true unknown_cookie_denied=true"
    )
  end

  test "R604 raw HTTP preserves duplicate admission and genuine preauth metadata", c do
    {:ok, p} = RuntimeOwner.bootstrap(%{request_id: F.request()})
    h = headers(p.cookie)
    r = http(c, "/auth/session", h)
    assert r.status == 200
    assert Jason.decode!(r.body) == %{"state" => "unauthenticated", "csrf_token" => p.csrf}
    assert Enum.any?(r.headers, &(&1 == "cache-control: no-store"))
    refute Enum.any?(r.headers, &String.starts_with?(&1, "set-cookie:"))

    for hs <- [[], headers(Protocol.random_token())],
        do: assert(http(c, "/auth/session", hs).status == 503)

    for hs <- [
          h ++ h,
          h ++ [{"authorization", "Bearer refused"}],
          h ++ [{"origin", "https://a.invalid"}, {"origin", "https://b.invalid"}],
          h ++ [{"cookie", "other=a"}],
          h ++ [{"x-large", String.duplicate("x", 8193)}],
          h ++ Enum.map(1..64, &{"x-#{&1}", "a"}),
          h ++ Enum.map(1..3, &{"x-large-#{&1}", String.duplicate("a", 6000)})
        ] do
      assert http(c, "/auth/session", hs).status in [400, 431]
    end

    for path <- [
          "/auth/session?expires_at=1",
          "/console-api/v1/orgs?limit=1&limit=2",
          "/console-api/v1/orgs?%6cimit=1",
          "/console-api/v1/orgs?limit=101",
          "/console-api/v1/projects?organization_id=org-a&request_id=caller",
          "/console-api/v1/orgs?cursor=%ZZ"
        ] do
      assert http(c, path, h).status == 400
    end

    for path <- ["/auth/login", "/auth/callback", "/auth/logout", "/v3/orgs"],
        do: assert(http(c, path, h).status == 404)

    assert http(c, "/auth/session", h, "POST").status == 404
    assert http(c, "/auth/session", h ++ [{"content-length", "1"}], "GET", "x").status == 400
    leases_clean()

    IO.puts(
      "R604_HTTP_RAW duplicates_cookie_authorization_origin=true header_bounds=true query_bounds=true no_mutation_routes=true no_random_metadata=true"
    )
  end

  test "R604 actual unchanged console client reads genuine synthetic callback over loopback", c do
    {_l, r} = active(c)
    {_, _, exp} = expiry(c, r.cookie)
    f = Path.join(System.tmp_dir!(), "mixer-browser-read-" <> Protocol.random_token() <> ".json")

    File.write!(
      f,
      Jason.encode!(%{
        origin: "http://127.0.0.1:#{c.http_port}",
        firstCookie: Protocol.random_token(),
        activeCookie: r.cookie,
        expires: exp
      })
    )

    File.chmod!(f, 0o600)

    try do
      {out, code} =
        System.cmd("node", [System.fetch_env!("MIXER_BROWSER_READ_NODE_DRIVER"), f],
          stderr_to_stdout: true
        )

      assert is_binary(out)
      assert code == 0

      IO.puts(
        "R604_ACTUAL_CLIENT session_retry=true org_50_plus_3=true project_50_plus_3=true genuine_signed_pkce_callback=true"
      )
    after
      File.rm!(f)
    end

    leases_clean()
  end

  test "R604 JSON expiry exactly follows admitted token credential and session bounds", c do
    {_l, r} = active(c)
    {s, i, exp} = expiry(c, r.cookie)

    assert {:ok, {:authenticated, _, _, _, ^exp}, :unchanged} =
             RuntimeOwner.read_session(headers(r.cookie))

    assert exp == i.expires_at
    assert Jason.decode!(http(c, "/auth/session", headers(r.cookie)).body)["expires_at"] == exp
    shorter = System.system_time(:second) + 60

    F.q!(Admin, "UPDATE public.mixer_authz_credentials SET expires_at=$1 WHERE reference=$2", [
      shorter,
      s.browser["credential_ref"]
    ])

    assert Jason.decode!(http(c, "/auth/session", headers(r.cookie)).body)["expires_at"] ==
             shorter

    # A real callback with a shorter signed ID-token expiry yields the tighter
    # browser deadline through the unchanged activation path and integrity guard.
    l = login(c)
    GenServer.call(c.provider, {:mode, :session_short})
    assert {:ok, session} = RuntimeOwner.callback(l.headers, l.query)
    {snapshot, identity, tight} = expiry(c, session.cookie)
    assert tight == snapshot.browser["idle_expires_at"] and tight < identity.expires_at

    assert Jason.decode!(http(c, "/auth/session", headers(session.cookie)).body)["expires_at"] ==
             tight

    assert {:ok, {:authenticated, _, _, _, ^tight}, :unchanged} =
             RuntimeOwner.read_session(headers(session.cookie))

    leases_clean()

    IO.puts(
      "R604_EXPIRY actual_json_equals_admitted=true token_tighter=true credential_tighter=true session_tighter=true"
    )
  end

  test "R604 revoked and stale cookies deny HTTP and runtime misconfiguration never succeeds",
       c do
    {l, r} = active(c)
    assert http(c, "/auth/session", headers(r.cookie)).status == 200
    assert http(c, "/auth/session", headers(l.preauth.cookie)).status == 503

    F.q!(
      Admin,
      "UPDATE public.mixer_authz_principals SET active=false,revision=revision+1 WHERE id='person-1'"
    )

    try do
      assert http(c, "/auth/session", headers(r.cookie)).status == 503
      assert http(c, "/console-api/v1/orgs", headers(r.cookie)).status == 503
    after
      F.q!(
        Admin,
        "UPDATE public.mixer_authz_principals SET active=true,revision=revision+1 WHERE id='person-1'"
      )
    end

    stop_supervised(RuntimeOwner)
    assert http(c, "/auth/session", headers(r.cookie)).status == 503

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

    assert http(c, "/auth/session", headers(r.cookie)).status == 503
    stop_supervised(RuntimeOwner)
    changed = %{c.config | token_endpoint: "https://issuer.fixture.invalid/changed"}
    {:ok, digest} = ConfigurationDigest.digest(changed)

    start_supervised!(
      {RuntimeOwner, %{c.runtime | browser_config: changed, configuration_digest: digest}}
    )

    assert http(c, "/auth/session", headers(r.cookie)).status == 503
    IO.puts("R604_HTTP_DENIAL revoked=true stale=true absent_disabled_changed_config=true")
  end

  defp finish_gate(parent) do
    fn state, event, _extra ->
      case event do
        {:in, {:"$gen_call", _, {:finish, _, _}}} ->
          send(parent, {:r604_finish_gate, self()})

          receive do
            :r604_continue -> :done
          after
            4000 -> :done
          end

        _ ->
          state
      end
    end
  end

  test "R604 expired publication remains withheld after admitted SQL success", c do
    l = login(c)
    GenServer.call(c.provider, {:mode, :short})
    assert {:ok, r} = RuntimeOwner.callback(l.headers, l.query)
    assert http(c, "/auth/session", headers(r.cookie)).status == 200
    assert :ok = :sys.install(RuntimeOwner, {finish_gate(self()), nil})
    task = Task.async(fn -> http(c, "/auth/session", headers(r.cookie)) end)
    assert_receive {:r604_finish_gate, owner}, 2000

    try do
      Process.sleep(2200)
    after
      send(owner, :r604_continue)
    end

    assert Task.await(task, 3000).status == 503
    assert http(c, "/auth/session", headers(r.cookie)).status == 503
    assert http(c, "/console-api/v1/orgs", headers(r.cookie)).status in [401, 503]
    leases_clean()
    IO.puts("R604_EXPIRY expired_http_refused=true")
  end

  test "R604 SQL admitted HTTP metadata refuses stale key generation publication", c do
    {_l, r} = active(c)
    assert :ok = :sys.install(RuntimeOwner, {finish_gate(self()), nil})
    task = Task.async(fn -> http(c, "/auth/session", headers(r.cookie)) end)
    assert_receive {:r604_finish_gate, owner}, 2000

    try do
      k = :sys.get_state(KeyOwner)
      assert {:ok, _} = KeyOwner.replace_manifest(KeyOwner, k.generation, Map.values(k.entries))
    after
      send(owner, :r604_continue)
    end

    assert Task.await(task, 3000).status == 503
    leases_clean()
    assert map_size(:sys.get_state(KeyOwner).admitted) == 0

    IO.puts(
      "R604_STALE_PUBLICATION key_generation_replaced=true sql_already_admitted=true http_dto_withheld=true"
    )
  end
end
