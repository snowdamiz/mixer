defmodule MixerHosted.CustomerArtifactHTTPFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_artifact_http_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifactHTTPFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_artifact_http_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifactHTTPFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_artifact_http_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifactHTTPFixture do
  alias MixerHosted.CustomerArtifactHTTPFixture.Admin
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR}

  def sql(query, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, query, params, log: false)
  def sha(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
  def now, do: System.system_time(:second)

  def seed! do
    sql(
      "TRUNCATE public.mixer_customer_idempotency,public.mixer_customer_audit_events,public.mixer_customer_artifacts,public.mixer_customer_artifact_heads,public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_organizations CASCADE"
    )

    for query <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('http-profile',1,'https://issuer.fixture.invalid/oauth','reviewed-client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,2),('other','human',true,0,2)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('http-profile',1,'subject','human','person',true),('http-profile',1,'other-subject','human','other',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('family','http-profile',1,'person',true,0,NULL,3),('other-family','http-profile',1,'other',true,0,NULL,3)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('http-profile',1,'token','person','family',true,0,NULL,4),('http-profile',1,'other-token','other','other-family',true,0,NULL,4)",
          "INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true)",
          "INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true)",
          "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','fieldlog',true)",
          "INSERT INTO public.mixer_authz_environments VALUES ('org-a','project-a','fieldlog','development',true)",
          "INSERT INTO public.mixer_authz_organization_heads VALUES ('org-a',5)",
          "INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',6)",
          "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org-a','project-a','exact_project','developer',true,0,NULL,7),('other-member','other','org-a','project-a','exact_project','developer',true,0,NULL,7)"
        ],
        do: sql(query)

    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis("org-a", "project-a")

    sql("INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)", [
      genesis
    ])

    :ok
  end

  def counts do
    sql(
      "SELECT (SELECT count(*) FROM public.mixer_customer_artifacts),(SELECT count(*) FROM public.mixer_customer_audit_events),(SELECT count(*) FROM public.mixer_customer_idempotency),(SELECT sequence FROM public.mixer_customer_artifact_heads)"
    ).rows
  end

  # The shape is owned test input. Both private keys are freshly generated and
  # remain in memory; no fixture key is a production trust root.
  def artifact(repo) do
    payload = "HTTP integration protocol payload, not executable guest code."

    scope = %{
      "organization" => "org-a",
      "project" => "project-a",
      "app" => "fieldlog",
      "environment" => "development",
      "platform" => "ios"
    }

    limits = %{"memory_bytes" => 65_536, "fuel" => 100_000, "startup_milliseconds" => 1000}
    runtime = sha("HTTP integration runtime")

    manifest = %{
      "schema" => 3,
      "scope" => scope,
      "release_id" => "http-release",
      "source_commit" => String.duplicate("a", 40),
      "provenance_id" => "http-provenance",
      "runtime" => runtime,
      "protocol" => 3,
      "guest_abi" => 2,
      "ui_schema" => 1,
      "capability_hashes" => %{},
      "capability_grants" => %{
        "schema" => 1,
        "schema_sha256" => "b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1",
        "entries" => []
      },
      "state_min" => 1,
      "state_max" => 1,
      "payload_sha256" => sha(payload),
      "compressed_bytes" => byte_size(payload),
      "expanded_bytes" => byte_size(payload),
      "compression" => "none",
      "asset_hashes" => %{},
      "source_map_sha256" => sha("http map"),
      "limits" => limits,
      "key_id" => "http-artifact-key",
      "created_at_unix" => now()
    }

    host = %{
      "scope" => scope,
      "runtime" => runtime,
      "protocol" => 3,
      "guest_abi" => 2,
      "ui_schema" => 1,
      "capability_hashes" => %{},
      "state_version" => 1,
      "max_payload_bytes" => 4_194_304,
      "limits" => limits
    }

    {public, private} = :crypto.generate_key(:eddsa, :ed25519)

    roots = [
      %{
        "key_id" => "http-artifact-key",
        "public_key" => public,
        "scope" => scope,
        "artifact" => true,
        "assignment" => false,
        "revoked" => false,
        "not_before_unix" => now() - 60,
        "not_after_unix" => now() + 3600
      }
    ]

    {:ok, cbor} = ArtifactCBOR.encode(manifest)
    signature = :crypto.sign(:eddsa, :none, "mixer.artifact.v3\0" <> cbor, [private, :ed25519])

    bytes =
      " \n" <>
        Jason.encode!(%{
          "signed_manifest" => %{"manifest" => manifest, "signature" => Base.encode64(signature)},
          "payload" => Base.encode64(payload)
        }) <> "\n "

    config = %{repo: repo, host: host, roots: roots}
    {:ok, checked} = ArtifactAdmission.admit(bytes, host, roots, now())
    {checked, config}
  end

  def record(value) do
    if directory = System.get_env("MIXER_ARTIFACT_HTTP_EVIDENCE") do
      File.write!(Path.join(directory, "requests.jsonl"), Jason.encode!(value) <> "\n", [:append])
    end
  end
end

defmodule MixerHostedWeb.CustomerArtifactHTTPIntegrationTest do
  use ExUnit.Case, async: false
  @moduletag :customer_artifact_http_db
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.Schema
  alias MixerHosted.CustomerArtifactHTTPFixture, as: F
  alias MixerHosted.CustomerArtifactHTTPFixture.{Admin, Migration, Runtime}
  alias MixerHosted.Identity.{ConfiguredVerifier, KeyOwner, TLSFixture}

  @profile %{
    profile_id: "http-profile",
    profile_version: 1,
    issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api",
    client_id: "reviewed-client",
    identity_class: :human,
    enabled: true
  }
  @scopes "mixer.artifact.upload mixer.artifact.read mixer.audit.read"

  setup_all do
    for app <- [:phoenix, :bandit, :ecto_sql, :postgrex, :jose, :mint, :ssl],
        do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_ARTIFACT_HTTP_TEST_PORT")),
      database: "mixer_customer_artifact_http",
      ssl: false,
      log: false
    ]

    start_supervised!(
      {Admin, settings ++ [username: "http_artifact_fixture_admin", pool_size: 3]}
    )

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "http_artifact_fixture_admin",
           pool_size: 1,
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE http_artifact_owner", []) end
         ]}
    )

    start_supervised!(
      {Runtime,
       settings ++
         [
           username: "http_artifact_runtime",
           pool_size: 1,
           telemetry_prefix: [:mixer_http_artifact_runtime],
           parameters: [application_name: "mixer-http-artifact-runtime"]
         ]}
    )

    for {version, module, file} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization,
           "20261025000003_add_customer_authorization.exs"},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
           "20261025000004_add_authorization_state_revisions.exs"},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage,
           "20261025000005_add_customer_artifact_storage.exs"}
        ] do
      unless Code.ensure_loaded?(module),
        do: Code.require_file(Path.expand("../../priv/repo/migrations/" <> file, __DIR__))

      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    for name <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{name} TO http_artifact_runtime")

    for name <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO http_artifact_runtime"
          )

    for name <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{name} TO http_artifact_runtime")

    F.sql(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO http_artifact_runtime"
    )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO http_artifact_runtime"
          )

    fixture = start_supervised!(TLSFixture)
    authority = GenServer.call(fixture, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "http-key", "alg" => "RS256", "use" => "sig"})

    TLSFixture.configure(fixture, {:body, Jason.encode!(%{"keys" => [public]})})
    workers = MixerHosted.CustomerArtifactHTTPFixture.KeyWorkers
    worker_pid = start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: workers})
    assert Process.whereis(KeyOwner) == nil

    entry = %{
      profile: @profile,
      jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
      transport: :hosted_https
    }

    opts = [
      name: KeyOwner,
      manifest: [entry],
      generation: 1,
      binding: @profile.profile_id,
      ca_roots: [authority.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: workers,
      fixture: Map.take(authority, [:ip, :port])
    ]

    owner = start_supervised!(%{id: KeyOwner, start: {KeyOwner, :start_fixture, [opts]}})
    endpoint_previous = Application.fetch_env(:mixer_hosted, MixerHostedWeb.Endpoint)

    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint,
      adapter: Bandit.PhoenixAdapter,
      server: true,
      http: [ip: {127, 0, 0, 1}, port: 0],
      secret_key_base: String.duplicate("synthetic-endpoint-fixture-", 4),
      render_errors: [formats: [json: MixerHostedWeb.ErrorJSON], layout: false],
      debug_errors: false
    )

    bandit = start_supervised!(MixerHostedWeb.Endpoint)
    {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    tls_setup = TLSFixture.info(fixture)
    assert tls_setup.key_dir_removed

    on_exit(fn ->
      tls_info =
        if Process.alive?(fixture),
          do: TLSFixture.info(fixture),
          else: %{key_dir_removed: tls_setup.key_dir_removed, requests: []}

      for pid <- [bandit, owner, worker_pid, fixture] do
        if Process.alive?(pid) do
          try do
            GenServer.stop(pid, :normal, 5_000)
          catch
            :exit, _ -> :ok
          end
        end
      end

      case endpoint_previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, value)
        :error -> Application.delete_env(:mixer_hosted, MixerHostedWeb.Endpoint)
      end

      cleanup = %{
        bandit_stopped: not Process.alive?(bandit),
        key_owner_stopped: not Process.alive?(owner),
        jwks_workers_stopped: not Process.alive?(worker_pid),
        tls_fixture_stopped: not Process.alive?(fixture),
        ephemeral_tls_key_directory_removed: tls_info.key_dir_removed,
        jwks_tls_request_count: length(tls_info.requests),
        bandit_port: port,
        tls_port: authority.port
      }

      if directory = System.get_env("MIXER_ARTIFACT_HTTP_EVIDENCE"),
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
    {checked, config} = F.artifact(Runtime)
    previous = Application.fetch_env(:mixer_hosted, CustomerArtifacts)
    Application.put_env(:mixer_hosted, CustomerArtifacts, config)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, CustomerArtifacts, value)
        :error -> Application.delete_env(:mixer_hosted, CustomerArtifacts)
      end
    end)

    Map.merge(context, %{checked: checked, token: token(context.key), config: config})
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
          "scope" => @scopes
        },
        claims
      )

    JOSE.JWS.sign(key, Jason.encode!(values), %{
      "alg" => "RS256",
      "typ" => "at+jwt",
      "kid" => "http-key"
    })
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  defp path(ctx),
    do: "/v3/orgs/org-a/projects/project-a/artifacts/" <> ctx.checked.manifest_sha256

  defp audit_path, do: "/v3/orgs/org-a/projects/project-a/audit"

  defp upload_headers,
    do: [
      {"content-type", "application/json"},
      {"idempotency-key", "first"},
      {"x-mixer-reason", "HTTP fixture upload"}
    ]

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
      Enum.map(authentication ++ framing ++ headers, fn {name, value} ->
        [name, ": ", value, "\r\n"]
      end),
      "\r\n",
      bytes
    ]

    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, ctx.port, [:binary, active: false], 2000)

    try do
      :ok = :gen_tcp.send(socket, wire)
      raw = receive_response(socket, "", Keyword.get(opts, :timeout, 4000))
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
      assert [request_id] = header(response, "x-request-id")
      assert byte_size(request_id) in 20..200
      public_response = if body == "", do: nil, else: Jason.decode!(body)

      F.record(%{
        label: label,
        request: %{
          method: method,
          path: path,
          body_bytes: byte_size(bytes),
          body_sha256: F.sha(bytes),
          header_names: Enum.map(headers, &elem(&1, 0)),
          bearer_present: authentication != []
        },
        response: %{
          status: response.status,
          headers: Map.new(response_headers),
          body_bytes: byte_size(body),
          body_sha256: F.sha(body),
          json: public_response
        },
        table_counts_after: F.counts()
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
      other -> flunk("HTTP response did not complete: #{inspect(other)}")
    end
  end

  defp header(response, key), do: for({^key, value} <- response.headers, do: value)
  defp json(response), do: Jason.decode!(response.body)

  defp error(response, status, code) do
    assert response.status == status

    assert %{"error" => %{"code" => ^code, "message" => message}, "request_id" => id} =
             json(response)

    assert Map.keys(json(response)) |> Enum.sort() == ["error", "request_id"]
    assert is_binary(message) and byte_size(message) <= 200
    assert header(response, "x-request-id") == [id]
    assert header(response, "retry-after") == if(status == 503, do: ["1"], else: [])
  end

  test "real default bearer verifier and PostgreSQL create retry read audit and wire HEAD", ctx do
    assert TLSFixture.info(ctx.tls_fixture).requests == []

    error(
      request(
        ctx,
        "cold missing bearer does not fetch JWKS",
        "PUT",
        path(ctx),
        "",
        [{"content-length", "100000"} | upload_headers()],
        token: nil,
        timeout: 1000
      ),
      401,
      "unauthenticated"
    )

    assert TLSFixture.info(ctx.tls_fixture).requests == []

    created =
      request(
        ctx,
        "create",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes,
        upload_headers() ++
          [{"x-forwarded-for", "198.51.100.7"}, {"x-request-id", String.duplicate("caller", 6)}]
      )

    assert created.status == 201
    assert TLSFixture.info(ctx.tls_fixture).requests != []
    assert {:ok, identity} = ConfiguredVerifier.authenticate(ctx.token, F.now())
    assert identity.subject == "subject"

    assert json(created) == %{
             "artifact_sha256" => ctx.checked.manifest_sha256,
             "immutable" => true
           }

    assert F.counts() == [[1, 1, 1, 1]]

    retry =
      request(
        ctx,
        "authorized same-key retry",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes,
        upload_headers()
      )

    assert {retry.status, retry.body} == {created.status, created.body}
    assert F.counts() == [[1, 1, 1, 1]]

    new_key =
      List.keyreplace(upload_headers(), "idempotency-key", 0, {"idempotency-key", "second"})

    unchanged =
      request(
        ctx,
        "new-key identical artifact",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes <> " \n",
        new_key
      )

    assert unchanged.status == 200
    assert json(unchanged) == json(created)
    assert F.counts() == [[1, 2, 2, 2]]

    read =
      request(ctx, "private exact retained bytes", "GET", path(ctx), "", [
        {"x-mixer-reason", String.duplicate("ignored", 100)}
      ])

    assert read.status == 200 and read.body == ctx.checked.envelope_bytes
    assert header(read, "content-type") == ["application/json; charset=utf-8"]
    audit = request(ctx, "schema-2 audit first page", "GET", audit_path() <> "?after=&limit=1")
    assert %{"events" => [first], "next" => 1} = json(audit)
    assert first["audit_schema"] == 2 and first["sequence"] == 1
    assert first["outcome"] == "created" and first["reason"] == "HTTP fixture upload"
    assert first["source_ip"] == ["127.0.0.1"]
    assert byte_size(first["request_id"]) == 32
    refute first["request_id"] == String.duplicate("caller", 6)
    assert hd(first["actor"]) == "person"
    second = request(ctx, "schema-2 audit second page", "GET", audit_path() <> "?after=1&limit=1")
    assert %{"events" => [event], "next" => 2} = json(second)
    assert event["outcome"] == "unchanged"
    assert first["current_state_sha256"] == event["current_state_sha256"]

    assert %{"events" => [], "next" => 2} =
             request(ctx, "audit terminal page", "GET", audit_path() <> "?after=2") |> json()

    for {label, target, status, token} <- [
          {"HEAD artifact", path(ctx), 200, ctx.token},
          {"HEAD audit", audit_path(), 200, ctx.token},
          {"HEAD authentication failure", path(ctx), 401, nil}
        ] do
      head = request(ctx, label, "HEAD", target, "", [], token: token)
      assert head.status == status and head.body == ""
    end

    assert F.counts() == [[1, 2, 2, 2]]
  end

  test "authentication and exact token scope reject before a withheld body", ctx do
    incomplete = [{"content-length", "100000"} | upload_headers()]

    error(
      request(ctx, "missing bearer before body", "PUT", path(ctx), "", incomplete,
        token: nil,
        timeout: 1000
      ),
      401,
      "unauthenticated"
    )

    denied = token(ctx.key, %{"scope" => "mixer.artifact.upload.extra"})

    error(
      request(ctx, "scope before withheld body", "PUT", path(ctx), "", incomplete,
        token: denied,
        timeout: 1000
      ),
      403,
      "permission_denied"
    )

    invalid = token(ctx.key, %{"exp" => F.now() - 1})

    error(
      request(ctx, "expired RS256 bearer", "PUT", path(ctx), "{}", upload_headers(),
        token: invalid
      ),
      401,
      "unauthenticated"
    )

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "digest mismatch never writes or returns an existing cached receipt", ctx do
    wrong =
      String.replace_suffix(path(ctx), ctx.checked.manifest_sha256, String.duplicate("0", 64))

    error(
      request(
        ctx,
        "digest mismatch before create",
        "PUT",
        wrong,
        ctx.checked.envelope_bytes,
        upload_headers()
      ),
      422,
      "digest_mismatch"
    )

    assert F.counts() == [[0, 0, 0, 0]]

    assert request(
             ctx,
             "create after mismatch uses same unreserved key",
             "PUT",
             path(ctx),
             ctx.checked.envelope_bytes,
             upload_headers()
           ).status == 201

    error(
      request(
        ctx,
        "digest mismatch before cached retry",
        "PUT",
        wrong,
        ctx.checked.envelope_bytes,
        upload_headers()
      ),
      422,
      "digest_mismatch"
    )

    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "current roles and credential revocation fence cached upload and private reads", ctx do
    assert request(
             ctx,
             "create before role changes",
             "PUT",
             path(ctx),
             ctx.checked.envelope_bytes,
             upload_headers()
           ).status == 201

    F.sql("UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='member'")
    assert request(ctx, "viewer private read", "GET", path(ctx)).status == 200
    assert request(ctx, "viewer audit", "GET", audit_path()).status == 200

    error(
      request(
        ctx,
        "viewer cannot replay upload",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes,
        upload_headers()
      ),
      403,
      "permission_denied"
    )

    F.sql("UPDATE public.mixer_authz_memberships SET role='billing_manager' WHERE id='member'")
    error(request(ctx, "billing manager cannot read", "GET", path(ctx)), 403, "permission_denied")
    F.sql("UPDATE public.mixer_authz_memberships SET role='developer' WHERE id='member'")

    F.sql(
      "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'"
    )

    for {label, method, target, bytes, headers} <- [
          {"revoked cached upload", "PUT", path(ctx), ctx.checked.envelope_bytes,
           upload_headers()},
          {"revoked private read", "GET", path(ctx), "", []},
          {"revoked audit", "GET", audit_path(), "", []}
        ] do
      error(request(ctx, label, method, target, bytes, headers), 401, "unauthenticated")
    end

    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "tenant invisibility and principal-bound keys expose no cached success", ctx do
    assert request(
             ctx,
             "create for principal binding",
             "PUT",
             path(ctx),
             ctx.checked.envelope_bytes,
             upload_headers()
           ).status == 201

    other = token(ctx.key, %{"sub" => "other-subject", "jti" => "other-token"})

    error(
      request(
        ctx,
        "other principal same key",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes,
        upload_headers(),
        token: other
      ),
      409,
      "idempotency_conflict"
    )

    other_tenant = String.replace(path(ctx), "/org-a/", "/org-b/")
    error(request(ctx, "foreign tenant private read", "GET", other_tenant), 404, "not_found")
    F.sql("UPDATE public.mixer_authz_memberships SET active=false WHERE id='member'")
    error(request(ctx, "removed membership private read", "GET", path(ctx)), 404, "not_found")

    error(
      request(
        ctx,
        "removed membership cached upload",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes,
        upload_headers()
      ),
      404,
      "not_found"
    )

    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "wire transport rejects malformed media encodings query and closed envelope without writes",
       ctx do
    for {label, method, target, bytes, headers, status, code} <- [
          {"empty content encoding", "PUT", path(ctx), "{}",
           upload_headers() ++ [{"content-encoding", ""}], 415, "unsupported_content_encoding"},
          {"nonexact media", "PUT", path(ctx), "{}",
           List.keyreplace(
             upload_headers(),
             "content-type",
             0,
             {"content-type", "application/json; charset=utf-8"}
           ), 400, "content_type"},
          {"duplicate JSON keys", "PUT", path(ctx),
           "{\"signed_manifest\":{},\"payload\":\"x\",\"payload\":\"x\"}", upload_headers(), 400,
           "invalid_json"},
          {"extra envelope field", "PUT", path(ctx),
           "{\"signed_manifest\":{},\"payload\":\"x\",\"extra\":true}", upload_headers(), 400,
           "invalid_json"},
          {"signed admission failure", "PUT", path(ctx),
           "{\"signed_manifest\":{},\"payload\":\"eA==\"}", upload_headers(), 422,
           "artifact_invalid"},
          {"duplicate query", "GET", audit_path() <> "?after=0&after=1", "", [], 400,
           "invalid_request"},
          {"unknown query", "GET", audit_path() <> "?unknown=1", "", [], 400, "invalid_request"},
          {"cursor overflow", "GET", audit_path() <> "?after=9007199254740992", "", [], 400,
           "invalid_request"},
          {"read body", "GET", path(ctx), "x", [], 400, "invalid_request"},
          {"chunked read body", "GET", path(ctx), "1\r\nx\r\n0\r\n\r\n",
           [{"transfer-encoding", "chunked"}], 400, "invalid_request"}
        ] do
      error(request(ctx, label, method, target, bytes, headers), status, code)
      assert F.counts() == [[0, 0, 0, 0]]
    end

    empty = request(ctx, "empty audit defaults", "GET", audit_path() <> "?after=&limit=")
    assert empty.status == 200 and json(empty) == %{"events" => [], "next" => 0}
  end

  test "database failure after writes and deferred checks returns no success and rolls back",
       ctx do
    handler = "http-artifact-precommit-failure"
    parent = self()

    :ok =
      :telemetry.attach(
        handler,
        [:mixer_http_artifact_runtime, :query],
        fn _, _, metadata, _ ->
          if metadata.query == "SET CONSTRAINTS ALL DEFERRED" do
            :telemetry.detach(handler)

            rows =
              F.sql(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name='mixer-http-artifact-runtime' AND state='idle in transaction'"
              ).rows

            send(parent, {:post_write_backend_terminated, rows})
          end
        end,
        nil
      )

    on_exit(fn -> :telemetry.detach(handler) end)

    failed =
      request(
        ctx,
        "post-write pre-commit backend failure",
        "PUT",
        path(ctx),
        ctx.checked.envelope_bytes,
        upload_headers()
      )

    assert_receive {:post_write_backend_terminated, [[true]]}, 2000
    error(failed, 503, "authorization_unavailable")
    assert F.counts() == [[0, 0, 0, 0]]

    assert request(
             ctx,
             "retry after rollback reuses unreserved key",
             "PUT",
             path(ctx),
             ctx.checked.envelope_bytes,
             upload_headers()
           ).status == 201

    assert F.counts() == [[1, 1, 1, 1]]
  end
end
