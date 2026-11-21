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
  def artifact(
        repo,
        payload \\ "HTTP integration protocol payload, not executable guest code.",
        {public, private} \\ :crypto.generate_key(:eddsa, :ed25519),
        source_map \\ "http map"
      ) do
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
      "source_map_sha256" => sha(source_map),
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
  alias MixerHosted.Audit.CustomerArtifactEvent
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.{Schema, UploadRepo}
  alias MixerHosted.CustomerArtifactHTTPFixture, as: F
  alias MixerHosted.CustomerArtifactHTTPFixture.{Admin, Migration, Runtime}
  alias MixerHosted.Identity.{ConfiguredVerifier, KeyOwner, TLSFixture}
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.ArtifactCBOR
  alias MixerHosted.Releases.{DeliveryRepo, PublicDelivery, Target, WriterRepo}
  alias MixerHosted.Test.StockReleaseCLI

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
  @action_version 20_261_120_000_010
  @action_migration MixerHosted.Repo.Migrations.AddLocalReleasePublicationAction
  @health_version 20_261_120_000_011
  @health_migration MixerHosted.Repo.Migrations.AddLocalReleaseHaltHealth
  @halt_audit_version 20_261_120_000_012
  @halt_audit_migration MixerHosted.Repo.Migrations.AddLocalReleaseHaltAudit
  @tls_runtime System.get_env("MIXER_TEST_LOCAL_ARTIFACT_UPLOAD_TLS") == "1"

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
           pool_size: 2,
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

    if @tls_runtime do
      Code.require_file("priv/repo/migrations/20261024000000_add_oban.exs")

      assert :ok =
               Ecto.Migrator.up(
                 Migration,
                 20_261_024_000_000,
                 MixerHosted.Repo.Migrations.AddOban,
                 log: false
               )
    end

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

    F.sql("CREATE ROLE http_release_writer LOGIN NOINHERIT")

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
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil

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

    endpoint_supervisor =
      unless @tls_runtime do
        start_supervised!(%{
          id: :release_http_endpoint_supervisor,
          start: {Supervisor, :start_link, [[MixerHostedWeb.Endpoint], [strategy: :one_for_one]]}
        })
      end

    port = if endpoint_supervisor, do: endpoint_port!()
    tls_setup = TLSFixture.info(fixture)
    assert tls_setup.key_dir_removed

    on_exit(fn ->
      tls_info =
        if Process.alive?(fixture),
          do: TLSFixture.info(fixture),
          else: %{key_dir_removed: tls_setup.key_dir_removed, requests: []}

      for pid <- [endpoint_supervisor, owner, worker_pid, fixture], is_pid(pid) do
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
        bandit_stopped: Process.whereis(MixerHostedWeb.Endpoint) == nil,
        key_owner_stopped: not Process.alive?(owner),
        jwks_workers_stopped: not Process.alive?(worker_pid),
        tls_fixture_stopped: not Process.alive?(fixture),
        ephemeral_tls_key_directory_removed: tls_info.key_dir_removed,
        jwks_tls_request_count:
          if(Process.alive?(fixture), do: length(tls_info.requests), else: nil),
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

    %{
      endpoint_supervisor: endpoint_supervisor,
      key: key,
      tls_fixture: fixture,
      pg_settings: settings,
      operator_identity_options: Keyword.drop(opts, [:name, :worker_supervisor])
    }
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

    port = if context.endpoint_supervisor, do: endpoint_port!()
    Map.merge(context, %{port: port, checked: checked, token: token(context.key), config: config})
  end

  defp endpoint_port! do
    {:ok, {{127, 0, 0, 1}, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    port
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

      public_response =
        if body != "" and
             Enum.any?(
               header(response, "content-type"),
               &String.starts_with?(&1, "application/json")
             ),
           do: Jason.decode!(body)

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

  @tag :local_artifact_upload_tls
  @tag skip: not @tls_runtime
  test "normal runtime configuration joins the authenticated upload to restricted TLS storage",
       ctx do
    refute Process.whereis(MixerHostedWeb.Endpoint)
    Application.delete_env(:mixer_hosted, CustomerArtifacts)

    target = %Target{
      scope: %Scope{
        organization_id: "org-a",
        project_id: "project-a",
        application_id: "fieldlog",
        environment_id: "development"
      },
      platform: "ios",
      runtime_sha256: ctx.config.host["runtime"],
      channel: "dev"
    }

    provision_release_writer!(target, :delivery)
    migrate_release_actions!()
    grant_release_action!()
    migrate_halt_health!()
    migrate_halt_audit!()
    grant_halt_audit!()

    for script <- ~w(provision-local-release-reader.sql provision-local-artifact-uploader.sql) do
      assert {_, 0} =
               System.cmd(
                 "psql",
                 ~w(-X -w -h 127.0.0.1 -U http_artifact_fixture_admin -d mixer_customer_artifact_http -v ON_ERROR_STOP=1) ++
                   [
                     "-p",
                     to_string(ctx.pg_settings[:port]),
                     "-f",
                     "../docs/operations/" <> script
                   ],
                 env: [{"PGSSLMODE", "disable"}],
                 stderr_to_stdout: true
               )
    end

    passwords =
      for {key, login} <- [
            {"MIXER_DATABASE_PASSWORD", "http_release_writer"},
            {"MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD", "mixer_release_delivery"},
            {"MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD", "mixer_artifact_uploader"}
          ],
          into: %{} do
        password = Base.url_encode64(:crypto.strong_rand_bytes(24), padding: false)
        [[quoted]] = F.sql("SELECT pg_catalog.quote_literal($1::text)", [password]).rows
        F.sql("ALTER ROLE #{login} PASSWORD #{quoted}")
        {key, password}
      end

    config = %{
      host: ctx.config.host,
      channel: target.channel,
      roots:
        Enum.map(ctx.config.roots, &Map.update!(&1, "public_key", fn pk -> Base.encode64(pk) end))
    }

    {:ok, socket} = :gen_tcp.listen(0, ip: {127, 0, 0, 1}, reuseaddr: true)
    {:ok, port} = :inet.port(socket)
    :ok = :gen_tcp.close(socket)

    env =
      Map.merge(passwords, %{
        "MIXER_HOSTED_ROLE" => "api",
        "MIXER_DATABASE_HOST" => "127.0.0.1",
        "MIXER_DATABASE_NAME" => "mixer_customer_artifact_http",
        "MIXER_DATABASE_USER" => "http_release_writer",
        "MIXER_DATABASE_POOL_SIZE" => "2",
        "MIXER_HTTP_PORT" => to_string(port),
        "MIXER_SECRET_KEY_BASE" => String.duplicate("local-tls-fixture-", 4),
        "MIXER_LOCAL_RELEASE_CONFIG" => Jason.encode!(config),
        "MIXER_LOCAL_RELEASE_WRITER_ENABLED" => "true"
      })

    ctx = %{
      ctx
      | port: port,
        token: token(ctx.key, %{"scope" => @scopes <> " mixer.release.publish"})
    }

    db_port = ctx.pg_settings[:port]

    with_runtime(Map.put(env, "MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD", nil), db_port, fn ->
      refute Process.whereis(UploadRepo)
      await_repo(MixerHosted.Repo, System.monotonic_time(:millisecond) + 4_000)

      assert %{"events" => [], "next" => 0} =
               halt_audit(ctx, "audit with uploader disabled") |> json()

      error(
        request(
          ctx,
          "ordinary boot default off",
          "PUT",
          path(ctx),
          ctx.checked.envelope_bytes,
          upload_headers()
        ),
        503,
        "storage_unavailable"
      )

      assert F.counts() == [[0, 0, 0, 0]]
    end)

    with_runtime(
      Map.put(env, "MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED", "true"),
      db_port,
      fn ->
        assert {:ok, {%{database_connection_bound: 4}, :disabled}} =
                 MixerHosted.Application.startup()

        await_repo(MixerHosted.Repo, System.monotonic_time(:millisecond) + 4_000)

        assert %{"events" => [], "next" => 0} =
                 halt_audit(ctx, "audit with uploader enabled") |> json()

        assert [["mixer_artifact_uploader", true]] =
                 Ecto.Adapters.SQL.query!(
                   UploadRepo,
                   """
                   SELECT session_user::text, ssl FROM pg_catalog.pg_stat_ssl
                   WHERE pid = pg_catalog.pg_backend_pid()
                   """,
                   [],
                   log: false
                 ).rows

        assert [[1, true, false, false]] =
                 F.sql("""
                 SELECT count(*), bool_and(ssl),
                   bool_or(has_table_privilege(a.usename, 'public.mixer_release_heads', 'SELECT')),
                   bool_or(pg_has_role(a.usename, 'mixer_release_delivery', 'MEMBER'))
                 FROM pg_catalog.pg_stat_activity a
                 JOIN pg_catalog.pg_stat_ssl s USING (pid)
                 WHERE a.usename = 'mixer_artifact_uploader'
                 """).rows

        wrong_tenant = String.replace(path(ctx), "/project-a/", "/other-project/")

        error(
          request(
            ctx,
            "foreign tenant",
            "PUT",
            wrong_tenant,
            ctx.checked.envelope_bytes,
            upload_headers()
          ),
          404,
          "not_found"
        )

        tampered =
          String.replace(
            ctx.checked.envelope_bytes,
            Base.encode64(ctx.checked.payload),
            Base.encode64("changed")
          )

        error(
          request(ctx, "changed payload", "PUT", path(ctx), tampered, upload_headers()),
          422,
          "artifact_invalid"
        )

        assert F.counts() == [[0, 0, 0, 0]]

        for label <- ["runtime upload", "runtime replay"] do
          response =
            request(ctx, label, "PUT", path(ctx), ctx.checked.envelope_bytes, upload_headers())

          assert response.status == 201

          assert json(response) == %{
                   "artifact_sha256" => ctx.checked.manifest_sha256,
                   "immutable" => true
                 }

          assert F.counts() == [[1, 1, 1, 1]]
        end

        assert [[envelope, manifest, payload, signature, audit]] =
                 F.sql("""
                 SELECT a.envelope_bytes,a.signed_manifest_bytes,a.payload,a.signature,e.display
                 FROM public.mixer_customer_artifacts a
                 JOIN public.mixer_customer_audit_events e ON e.organization_id=a.organization_id
                   AND e.project_id=a.project_id AND e.sequence=a.creating_sequence
                 """).rows

        assert {envelope, manifest, payload, signature} ==
                 {ctx.checked.envelope_bytes, ctx.checked.signed_manifest_bytes,
                  ctx.checked.payload, ctx.checked.signature}

        assert %{
                 "actor" => ["person" | _],
                 "outcome" => "created",
                 "reason" => "HTTP fixture upload",
                 "source_ip" => ["127.0.0.1"]
               } = audit

        error(
          request(ctx, "no legacy artifact read", "GET", path(ctx)),
          503,
          "storage_unavailable"
        )

        validate =
          request(
            ctx,
            "writer sees the committed artifact",
            "POST",
            "/v3/orgs/org-a/projects/project-a/releases/validate",
            Jason.encode!(%{artifact_sha256: ctx.checked.manifest_sha256}),
            upload_headers()
          )

        assert validate.status == 200
        assert %{"protocol_valid" => true} = json(validate)
      end
    )

    refute Process.whereis(UploadRepo)
    refute Process.whereis(MixerHostedWeb.Endpoint)
    assert {:ok, socket} = :gen_tcp.listen(port, ip: {127, 0, 0, 1}, reuseaddr: true)
    :ok = :gen_tcp.close(socket)
  end

  defp with_runtime(env, db_port, check) do
    previous_env = Map.new(env, fn {key, _} -> {key, System.get_env(key)} end)
    previous_config = Application.get_all_env(:mixer_hosted)
    apply_env(env)

    try do
      config = Config.Reader.read!("config/config.exs", env: :prod)
      runtime = Config.Reader.read!("config/runtime.exs", env: :prod)

      settings = Config.Reader.merge(config, runtime) |> Keyword.fetch!(:mixer_hosted)
      Application.put_all_env(mixer_hosted: fixture_db_port(settings, db_port))

      assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
      check.()
    after
      if Process.whereis(MixerHosted.Supervisor), do: :ok = Application.stop(:mixer_hosted)

      for {key, _} <- Application.get_all_env(:mixer_hosted),
          do: Application.delete_env(:mixer_hosted, key)

      Application.put_all_env(mixer_hosted: previous_config)
      apply_env(previous_env)
    end
  end

  # Use an owned ephemeral PostgreSQL port when the normal port is occupied.
  # This fixture adjusts only the database port after evaluating runtime.exs.
  defp fixture_db_port(settings, port) do
    rebind = fn repo ->
      assert repo[:port] == 5432
      Keyword.replace!(repo, :port, port)
    end

    settings
    |> Keyword.update!(MixerHosted.Repo, rebind)
    |> Keyword.update!(WriterRepo, rebind)
    |> Keyword.update!(:local_release_delivery, &Map.update!(&1, :repo, rebind))
    |> Keyword.update!(:startup, fn {hosted, :disabled} ->
      upload =
        if upload = hosted.artifact_upload do
          %{
            upload
            | repo: rebind.(upload.repo),
              delivery: Map.update!(upload.delivery, :repo, rebind)
          }
        end

      {%{hosted | repo: rebind.(hosted.repo), artifact_upload: upload}, :disabled}
    end)
  end

  defp apply_env(env) do
    for {key, value} <- env do
      if value, do: System.put_env(key, value), else: System.delete_env(key)
    end
  end

  test "stock local publish over Bandit preserves validation and exact authorized retries", ctx do
    {checked, config} = F.artifact(Runtime, <<0, 97, 115, 109, 1, 0, 0, 0>>)
    {publisher, draft, private} = release_fixture!(ctx, checked, config)
    migrate_release_actions!()
    grant_release_action!()
    digest = checked.manifest_sha256

    base = "/v3/orgs/org-a/projects/project-a"
    validate = base <> "/releases/validate"
    publish = base <> "/channels/dev/publish"
    validation = "{\n  \"artifact_sha256\" : \"#{digest}\"\n}\n"
    signed = sign_assignment(draft, private)
    first = ~s({"signed_assignment":#{signed}})
    key = cli_key("POST", publish, first)
    validation_key = cli_key("POST", validate, validation)

    for {path, body} <- [{validate, validation}, {publish, first}] do
      headers = cli_headers(cli_key("POST", path, body))

      for invalid <- [nil, token(ctx.key, %{"exp" => F.now() - 1})] do
        publisher
        |> request("invalid bearer", "POST", path, body, headers, token: invalid)
        |> error(401, "unauthenticated")
      end

      publisher
      |> request("scope missing", "POST", path, body, headers, token: ctx.token)
      |> error(403, "role_denied")

      publisher
      |> request(
        "other tenant",
        "POST",
        String.replace(path, "project-a", "project-b"),
        body,
        headers
      )
      |> error(403, "scope_denied")
    end

    assert release_counts() == [[0, 0, nil]]

    publisher
    |> request(
      "validate before upload",
      "POST",
      validate,
      validation,
      cli_headers(validation_key)
    )
    |> error(404, "not_found")

    publisher
    |> request("publish before validation", "POST", publish, first, cli_headers(key))
    |> error(422, "not_validated")

    assert release_counts() == [[0, 0, nil]]

    if cli = System.get_env("MIXER_TEST_RELEASE_CLI") do
      for _ <- 1..2,
          do:
            StockReleaseCLI.publish!(cli, publisher.port, publisher.token, checked, signed, draft)

      assert F.counts() == [[1, 1, 1, 1]]
      assert release_counts() == [[2, 1, Decimal.new(1)]]
    else
      upload =
        ~s({"signed_manifest":#{checked.signed_manifest_bytes},"payload":"#{Base.encode64(checked.payload)}"})

      upload_path = path(publisher)
      upload_key = cli_key("PUT", upload_path, upload)

      assert %{status: 201} =
               request(
                 publisher,
                 "stock upload body",
                 "PUT",
                 upload_path,
                 upload,
                 cli_headers(upload_key)
               )

      publisher
      |> request(
        "retained upload still requires validation",
        "POST",
        publish,
        first,
        cli_headers(key)
      )
      |> error(422, "not_validated")
    end

    expect_validation = %{
      "artifact_sha256" => digest,
      "protocol_valid" => true,
      "compiler_eligibility_verified" => false,
      "policy_approved" => false,
      "mobile_qualified" => false
    }

    validated =
      request(
        publisher,
        "stock validate",
        "POST",
        validate,
        validation,
        cli_headers(validation_key)
      )

    assert validated.status == 200
    assert json(validated) == expect_validation

    first_result = %{
      "artifact_sha256" => digest,
      "sequence" => 1,
      "rollout_basis_points" => 2_500,
      "delivery" => "local_only"
    }

    published = request(publisher, "first publish", "POST", publish, first, cli_headers(key))
    assert published.status == 200
    assert json(published) == first_result

    [[original_policy]] =
      F.sql("""
      SELECT pg_get_expr(polwithcheck, polrelid) FROM pg_policy
      WHERE polrelid = 'public.mixer_release_cli_requests'::regclass
        AND polname = 'release_cli_append'
      """).rows

    F.sql(
      "ALTER POLICY release_cli_append ON public.mixer_release_cli_requests WITH CHECK (true)"
    )

    try do
      publisher
      |> request("mutated receipt policy", "POST", publish, first, cli_headers(key))
      |> error(503, "authorization_unavailable")
    after
      F.sql("""
      ALTER POLICY release_cli_append ON public.mixer_release_cli_requests
      WITH CHECK (#{original_policy})
      """)
    end

    assert release_counts() == [[2, 1, Decimal.new(1)]]

    second = ~s({"signed_assignment":#{sign_assignment(%{draft | "sequence" => 2}, private)}})
    second_key = cli_key("POST", publish, second)

    for {body, reused, label} <- [
          {first <> " ", key, "different outer bytes"},
          {second, key, "different signed assignment"},
          {first, validation_key, "key reused across operations"}
        ] do
      publisher
      |> request(label, "POST", publish, body, cli_headers(reused))
      |> error(409, "idempotency_conflict")
    end

    tampered =
      ~s({"signed_assignment":#{sign_assignment(%{draft | "sequence" => 2}, elem(:crypto.generate_key(:eddsa, :ed25519), 1))}})

    publisher
    |> request("invalid signature", "POST", publish, tampered, cli_headers(second_key))
    |> error(409, "assignment_rejected")

    next = request(publisher, "advance head", "POST", publish, second, cli_headers(second_key))
    assert next.status == 200
    assert json(next) == %{first_result | "sequence" => 2}

    replayed =
      request(publisher, "exact retry behind head", "POST", publish, first, cli_headers(key))

    assert replayed.status == 200
    assert json(replayed) == first_result

    publisher
    |> request("stale sequence with new key", "POST", publish, first, cli_headers("new-key"))
    |> error(409, "assignment_rejected")

    F.sql(
      "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'"
    )

    publisher
    |> request("revoked credential cannot replay", "POST", publish, first, cli_headers(key))
    |> error(401, "unauthenticated")

    assert release_counts() == [[3, 2, Decimal.new(2)]]

    assert [[^signed]] =
             F.sql(
               "SELECT signed_assignment_bytes FROM public.mixer_release_publications WHERE sequence=1"
             ).rows
  end

  @tag :private_source_map
  @tag timeout: 90_000
  test "the local operator retains exact bytes for current owners of a signed publication", ctx do
    {tmp_dir, 0} = System.cmd("realpath", [System.tmp_dir!()])
    template = Path.join(String.trim_trailing(tmp_dir, "\n"), "mixer-private-source-map.XXXXXXXX")
    {dir, 0} = System.cmd("mktemp", ["-d", template])
    dir = String.trim_trailing(dir, "\n")
    on_exit(fn -> File.rm_rf!(dir) end)

    marker = "mixer-disposable-private-source-marker"
    map = " {\"sources\":[\"" <> marker <> "\"]}\n"
    input = Path.join(dir, "input")
    output = Path.join(dir, "output")
    File.write!(input, map)

    {checked, config} =
      F.artifact(
        Runtime,
        <<0, 97, 115, 109, 1, 0, 0, 0>>,
        :crypto.generate_key(:eddsa, :ed25519),
        map
      )

    {publisher, draft, private} = release_fixture!(ctx, checked, config, :delivery)
    migrate_release_actions!()
    grant_release_action!()
    start_release_delivery!(ctx.pg_settings)
    provision_source_map_retention!()
    F.sql("ALTER ROLE http_release_writer SET log_parameter_max_length = 0")
    F.sql("ALTER ROLE http_release_writer SET log_parameter_max_length_on_error = 0")
    F.sql("ALTER ROLE http_release_writer SET log_error_verbosity = 'terse'")

    digest = checked.manifest_sha256
    runtime = draft["runtime"]
    base = "/v3/orgs/org-a/projects/project-a"
    read = ["read", "1", digest, output]
    retain = fn deadline -> ["retain", "1", digest, input, to_string(deadline)] end
    operator = fn args -> source_map_command(publisher, marker, args) end

    events = [:recv, :async_recv, :send, :send_error]
    handler = {__MODULE__, :source_map_http_observation}
    test = self()

    :ok =
      :telemetry.attach_many(
        handler,
        Enum.map(events, &[:thousand_island, :connection, &1]),
        fn event, measurements, metadata, _ ->
          send(test, {:observed_http, List.last(event)})

          if private_marker?(measurements, metadata, marker),
            do: send(test, :map_on_http)
        end,
        nil
      )

    on_exit(fn -> :telemetry.detach(handler) end)

    map_path =
      base <>
        "/apps/fieldlog/environments/development/platforms/ios/runtimes/" <>
        runtime <> "/channels/dev/releases/1/source-map/" <> digest

    signed = sign_assignment(%{draft | "rollout_basis_points" => 10_000}, private)

    offer_path =
      "/v3/updates?" <>
        URI.encode_query(
          Map.merge(draft["scope"], %{
            "runtime" => runtime,
            "channel" => "dev",
            "installation" => "source-map-test"
          })
        )

    artifact_path = "/v3/artifacts/" <> digest <> "?organization=org-a&project=project-a"

    stage_release!(publisher, checked)
    assert {"not_found\n", 1} = operator.(retain.(F.now() + 120))
    assert %{status: 200} = release_request(publisher, base <> "/channels/dev/publish", signed)

    url = String.to_charlist("http://127.0.0.1:#{publisher.port}" <> map_path)
    headers = [{~c"authorization", String.to_charlist("Bearer " <> publisher.token)}]

    for {method, request} <- [
          {:get, {url, headers}},
          {:put, {url, headers, ~c"application/octet-stream", ""}}
        ] do
      assert :error =
               Phoenix.Router.route_info(
                 MixerHostedWeb.Router,
                 String.upcase(to_string(method)),
                 map_path,
                 "localhost"
               )

      assert {:ok, {{_, 404, _}, _, _}} = :httpc.request(method, request, [timeout: 4_000], [])
    end

    assert %{status: 200, body: offer} =
             request(publisher, "public offer before retention", "GET", offer_path, "", [],
               token: nil
             )

    assert %{status: 200, body: original} =
             request(publisher, "public artifact before retention", "GET", artifact_path, "", [],
               token: nil
             )

    assert original ==
             ~s({"signed_manifest":#{checked.signed_manifest_bytes},"payload":"#{Base.encode64(checked.payload)}"})

    assert {"disabled\n", 1} = source_map_command(publisher, marker, read, false)
    assert {"unauthenticated\n", 1} = source_map_command(%{publisher | token: nil}, marker, read)
    assert {"permission_denied\n", 1} = source_map_command(ctx, marker, read)
    assert {"not_found\n", 1} = operator.(List.replace_at(read, 1, "2"))
    assert {"not_found\n", 1} = operator.(List.replace_at(read, 2, F.sha("other artifact")))
    refute File.exists?(output)

    File.write!(input, map <> " ")
    assert {"invalid_request\n", 1} = operator.(retain.(F.now() + 120))
    File.write!(input, map)
    assert {"invalid_request\n", 1} = operator.(retain.(F.now() - 1))

    F.sql("ALTER ROLE http_release_writer SET log_parameter_max_length = -1")
    assert {"storage_unavailable\n", 1} = operator.(retain.(F.now() + 120))
    F.sql("ALTER ROLE http_release_writer SET log_parameter_max_length = 0")
    F.sql("ALTER ROLE http_release_writer SET log_error_verbosity = 'default'")
    assert {"storage_unavailable\n", 1} = operator.(retain.(F.now() + 120))
    F.sql("ALTER ROLE http_release_writer SET log_error_verbosity = 'terse'")
    assert [[0]] = F.sql("SELECT count(*) FROM public.mixer_release_source_maps").rows

    deadline = F.now() + 20
    success = {"retain_until=#{deadline}\n", 0}
    assert ^success = operator.(retain.(deadline))
    assert ^success = operator.(retain.(deadline))
    assert {"conflict\n", 1} = operator.(retain.(deadline + 600))

    assert [[^deadline, "person", ^digest, map_digest]] =
             F.sql("""
             SELECT retain_until, retained_by, artifact_sha256, encode(sha256(map_bytes), 'hex')
             FROM public.mixer_release_source_maps
             """).rows

    assert map_digest == F.sha(map)

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='release_manager',revision=revision+1 WHERE id='member'"
    )

    assert {"permission_denied\n", 1} = operator.(read)
    assert {"permission_denied\n", 1} = operator.(retain.(deadline))
    refute File.exists?(output)

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='owner',revision=revision+1 WHERE id='member'"
    )

    assert [[false, false, false, false]] =
             F.sql("""
             SELECT has_table_privilege('mixer_release_delivery','public.mixer_release_source_maps','SELECT'),
                    has_table_privilege('http_artifact_runtime','public.mixer_release_source_maps','SELECT'),
                    has_table_privilege('http_release_writer','public.mixer_release_source_maps','UPDATE'),
                    has_table_privilege('http_release_writer','public.mixer_release_source_maps','DELETE')
             """).rows

    assert {"0\n", 0} = purge_maps(ctx)

    grant_deadline = deadline - 1

    F.sql(
      "UPDATE public.mixer_authz_memberships SET expires_at=$1,revision=revision+1 WHERE id='member'",
      [grant_deadline]
    )

    assert ^success = source_map_command(publisher, marker, read, true, grant_deadline)

    F.sql(
      "UPDATE public.mixer_authz_memberships SET expires_at=NULL,revision=revision+1 WHERE id='member'"
    )

    if File.read!(output) != map, do: flunk("source-map read changed the signed bytes")
    assert Bitwise.band(File.stat!(output).mode, 0o777) == 0o600
    assert {"output_unavailable\n", 1} = operator.(read)
    if File.read!(output) != map, do: flunk("the read overwrote its destination")

    if :os.type() == {:unix, :darwin} do
      acl_dir = Path.join(dir, "inherited-acl")
      File.mkdir!(acl_dir)
      File.chmod!(acl_dir, 0o700)

      {"", 0} =
        System.cmd("/bin/chmod", ["+a", "everyone allow read,file_inherit,only_inherit", acl_dir])

      probe = Path.join(acl_dir, "empty-probe")
      File.touch!(probe)
      File.chmod!(probe, 0o600)
      {listing, 0} = System.cmd("/bin/ls", ["-le", probe])
      assert Bitwise.band(File.stat!(acl_dir).mode, 0o777) == 0o700
      assert Bitwise.band(File.stat!(probe).mode, 0o777) == 0o600
      assert File.stat!(probe).size == 0
      assert Regex.match?(~r/everyone .*inherited.*read/, listing)
      File.rm!(probe)

      refused = Path.join(acl_dir, "refused")
      assert {"output_unavailable\n", 1} = operator.(List.replace_at(read, 3, refused))
      assert File.ls!(acl_dir) == []
    end

    Process.sleep(max(0, deadline * 1000 - System.system_time(:millisecond)))
    expired_read = List.replace_at(read, 3, Path.join(dir, "expired"))
    assert {"not_found\n", 1} = operator.(expired_read)
    refute File.exists?(List.last(expired_read))
    assert {"not_found\n", 1} = operator.(retain.(F.now() + 120))

    assert {:ok, :ok} =
             Admin.transaction(fn ->
               F.sql("LOCK TABLE public.mixer_release_source_maps IN ACCESS EXCLUSIVE MODE")
               started = System.monotonic_time(:millisecond)
               assert {message, 3} = purge_maps(ctx)
               assert String.contains?(message, "55P03")
               assert System.monotonic_time(:millisecond) - started < 4_000

               assert [[true]] =
                        F.sql(
                          "SELECT map_bytes IS NOT NULL FROM public.mixer_release_source_maps"
                        ).rows

               :ok
             end)

    assert {"1\n", 0} = purge_maps(ctx)
    assert {"0\n", 0} = purge_maps(ctx)

    assert [[^deadline, nil]] =
             F.sql("SELECT retain_until, map_bytes FROM public.mixer_release_source_maps").rows

    assert {"not_found\n", 1} = operator.(retain.(F.now() + 120))

    assert %{status: 200, body: ^offer} =
             request(publisher, "unchanged public offer", "GET", offer_path, "", [], token: nil)

    assert %{status: 200, body: ^original} =
             request(publisher, "unchanged public artifact", "GET", artifact_path, "", [],
               token: nil
             )

    assert_received {:observed_http, :async_recv}
    assert_received {:observed_http, :send}
    refute_received :map_on_http
  end

  defp private_marker?(measurements, metadata, marker) do
    data = :erlang.term_to_binary({measurements, metadata})
    pieces = Map.get(measurements, :data, [])

    :binary.match(data, marker) != :nomatch or
      :binary.match(IO.iodata_to_binary(pieces), marker) != :nomatch
  end

  defp source_map_command(ctx, marker, args, enabled \\ true, expected_valid_until \\ nil) do
    %{target: target, host: host, roots: roots} =
      Application.fetch_env!(:mixer_hosted, :local_release_target)

    config = %{
      host: host,
      channel: target.channel,
      roots: Enum.map(roots, &Map.update!(&1, "public_key", fn key -> Base.encode64(key) end))
    }

    env = [
      {"MIX_ENV", "test"},
      {"MIXER_HOSTED_ROLE", "api"},
      {"MIXER_IDENTITY_MODE", "disabled"},
      {"MIXER_IDENTITY_CONFIG", nil},
      {"MIXER_DATABASE_HOST", "127.0.0.1"},
      {"MIXER_DATABASE_NAME", ctx.pg_settings[:database]},
      {"MIXER_DATABASE_USER", "http_release_writer"},
      {"MIXER_DATABASE_PASSWORD", "unused-disposable-trust-fixture"},
      {"MIXER_SECRET_KEY_BASE", String.duplicate("private-map-fixture-", 4)},
      {"MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD", "unused-disposable-reader-fixture"},
      {"MIXER_LOCAL_RELEASE_CONFIG", Jason.encode!(config)},
      {"MIXER_LOCAL_RELEASE_WRITER_ENABLED", "true"},
      {"MIXER_LOCAL_SOURCE_MAP_RETENTION_ENABLED", to_string(enabled)},
      {"MIXER_RELEASE_TOKEN", ctx.token}
    ]

    {roots, options} = Keyword.pop!(ctx.operator_identity_options, :ca_roots)
    encoded_roots = Enum.map(roots, &Base.encode64/1)

    bootstrap =
      quote do
        settings = Config.Reader.read!("config/runtime.exs", env: :dev)[:mixer_hosted]
        {hosted, :disabled} = Keyword.fetch!(settings, :startup)

        # Connect the normal operator to this test's disposable database and TLS JWKS authority.
        identity = %MixerHosted.Identity.StartupConfig{
          mode: :configured,
          owner_options:
            Keyword.put(
              unquote(Macro.escape(options)),
              :ca_roots,
              Enum.map(unquote(encoded_roots), &Base.decode64!/1)
            )
        }

        installation = %MixerHosted.BrowserAuth.Installation{
          runtime: nil,
          provider: {:fixture, nil, nil, nil}
        }

        repo =
          Keyword.merge(Keyword.fetch!(settings, MixerHosted.Releases.WriterRepo),
            port: unquote(ctx.pg_settings[:port]),
            ssl: false,
            telemetry_prefix: [:source_map_operator_repo]
          )

        settings =
          Keyword.merge(settings,
            startup: {%{hosted | identity_startup: identity}, installation}
          )
          |> Keyword.put(MixerHosted.Releases.WriterRepo, repo)

        Application.put_all_env(mixer_hosted: settings)
        {:ok, _} = Application.ensure_all_started(:telemetry)
        Logger.configure(level: :warning)

        :ok =
          :telemetry.attach(
            "private-map-listener-observation",
            [:thousand_island, :listener, :start],
            fn _, _, _, _ -> IO.puts(:stderr, "unexpected HTTP listener") end,
            nil
          )

        :ok =
          :telemetry.attach(
            "private-map-observation",
            [:source_map_operator_repo, :query],
            fn _, measurements, metadata, _ ->
              if String.contains?(metadata.query, "mixer_release_source_maps") or
                   :binary.match(
                     :erlang.term_to_binary({measurements, metadata}),
                     unquote(marker)
                   ) !=
                     :nomatch do
                IO.puts(:stderr, "unexpected private query telemetry")
              end
            end,
            nil
          )
      end

    mix = [
      "run",
      "--no-start",
      "--no-compile",
      "--eval",
      Macro.to_string(bootstrap),
      "--require",
      "scripts/private-source-map.exs",
      "--"
    ]

    {command, argv} =
      case args do
        ["read" | _] ->
          driver = ~S'''
          import json, runpy, sys
          operator = runpy.run_path("priv/local_source_map_retention/private_output.py")
          expected = json.loads(sys.argv[2])
          if expected is not None:
              publish = operator["publish"]
              def check_cutoff(path, payload, deadline, valid_until):
                  if valid_until != expected:
                      raise RuntimeError("publisher did not receive the owner grant cutoff")
                  return publish(path, payload, deadline, valid_until)
              operator["main"].__globals__["publish"] = check_cutoff
          sys.exit(operator["main"](sys.argv[3:], ("mix", *json.loads(sys.argv[1]))))
          '''

          {"python3",
           [
             "-I",
             "-S",
             "-B",
             "-c",
             driver,
             Jason.encode!(mix),
             Jason.encode!(expected_valid_until)
             | args
           ]}

        _ ->
          {"mix", mix ++ args}
      end

    {output, status} = System.cmd(command, argv, env: env, stderr_to_stdout: true)

    if :binary.match(output, marker) != :nomatch, do: flunk("operator printed the private map")
    {output, status}
  end

  defp purge_maps(ctx) do
    System.cmd(
      "psql",
      ~w(-X -w -qAt -h 127.0.0.1 -U http_artifact_fixture_admin -d mixer_customer_artifact_http
        -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -p) ++
        [
          to_string(ctx.pg_settings[:port]),
          "-f",
          "priv/local_source_map_retention/purge_expired.sql"
        ],
      env: [{"PGSSLMODE", "disable"}],
      stderr_to_stdout: true
    )
  end

  defp provision_source_map_retention! do
    path = "priv/local_source_map_retention/20261120000022_add_local_source_map_retention.exs"
    version = 20_261_120_000_022
    module = MixerHosted.Repo.Migrations.AddLocalSourceMapRetention
    Code.require_file(path)
    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)

    F.sql("GRANT SELECT, INSERT ON public.mixer_release_source_maps TO http_release_writer")

    F.sql("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_source_map_allowed(text,text,text,text,text,text,text,numeric,text)
    TO http_release_writer
    """)

    on_exit(fn ->
      F.sql("TRUNCATE public.mixer_release_source_maps")
      assert :ok = Ecto.Migrator.down(Migration, version, module, log: false)
    end)
  end

  test "signed promotion and rollback use the locked head and replay immutable results", ctx do
    signer = :crypto.generate_key(:eddsa, :ed25519)
    {first, config} = F.artifact(Runtime, "first release payload", signer)
    {second, _} = F.artifact(Runtime, "second release payload", signer)
    {publisher, draft, private} = release_fixture!(ctx, first, config)
    a = first.manifest_sha256
    b = second.manifest_sha256
    reason = "Restore the previous release after an adverse signal"
    publish = "/v3/orgs/org-a/projects/project-a/channels/dev/publish"
    promote = "/v3/orgs/org-a/projects/project-a/channels/dev/promote"
    rollback = "/v3/orgs/org-a/projects/project-a/channels/dev/rollback"

    initial = sign_assignment(draft, private)

    expanded =
      %{draft | "sequence" => 2, "rollout_basis_points" => 7_500}
      |> sign_assignment(private)
      |> String.replace_prefix("{", "{\n ")

    newer = sign_assignment(%{draft | "sequence" => 3, "artifact_sha256" => b}, private)
    restored = sign_assignment(%{draft | "sequence" => 4}, private)
    final = sign_assignment(%{draft | "sequence" => 5, "rollout_basis_points" => 5_000}, private)

    release_request(publisher, promote, expanded) |> error(422, "not_validated")
    stage_release!(publisher, first)
    stage_release!(publisher, second)
    artifacts = retained_artifacts()

    release_request(publisher, promote, expanded) |> error(409, "invalid_promotion")

    release_request(publisher, rollback, restored, reason: reason)
    |> error(409, "invalid_rollback")

    assert release_counts() == [[2, 0, nil]]

    assert %{status: 200} = release_request(publisher, publish, initial)

    assert [[^initial]] =
             F.sql("SELECT signed_assignment_bytes FROM public.mixer_release_publications").rows

    assert release_counts() == [[3, 1, Decimal.new(1)]]

    migrate_release_actions!()
    assert release_action_grants() == [[true, false, false, false, false]]

    assert [[^initial, "publish"]] =
             F.sql("SELECT signed_assignment_bytes,action FROM public.mixer_release_publications").rows

    assert %{status: 200} = release_request(publisher, publish, initial)

    release_request(publisher, promote, expanded) |> error(503, "authorization_unavailable")
    assert release_counts() == [[3, 1, Decimal.new(1)]]

    grant_release_action!()
    assert release_action_grants() == [[true, true, false, false, false]]

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='viewer',revision=revision+1 WHERE id='member'"
    )

    try do
      release_request(publisher, promote, expanded) |> error(403, "role_denied")
      assert release_counts() == [[3, 1, Decimal.new(1)]]
    after
      F.sql(
        "UPDATE public.mixer_authz_memberships SET role='owner',revision=revision+1 WHERE id='member'"
      )
    end

    invalid = [
      {"equal cohort", %{"rollout_basis_points" => 2_500}, "invalid_promotion", 409},
      {"smaller cohort", %{"rollout_basis_points" => 2_400}, "invalid_promotion", 409},
      {"different artifact", %{"artifact_sha256" => b}, "invalid_promotion", 409},
      {"wrong app", %{"scope" => %{draft["scope"] | "app" => "other-app"}}, "scope_denied", 403},
      {"wrong environment", %{"scope" => %{draft["scope"] | "environment" => "staging"}},
       "scope_denied", 403},
      {"wrong platform", %{"scope" => %{draft["scope"] | "platform" => "android"}},
       "scope_denied", 403},
      {"wrong runtime", %{"runtime" => F.sha("wrong runtime")}, "unknown_runtime", 422},
      {"wrong signed channel", %{"channel" => "stable"}, "assignment_rejected", 409}
    ]

    for {label, fields, code, status} <- invalid do
      signed = sign_assignment(Map.merge(%{draft | "sequence" => 2}, fields), private)
      release_request(publisher, promote, signed, label: label) |> error(status, code)
    end

    {_, wrong_key} = :crypto.generate_key(:eddsa, :ed25519)
    forged = sign_assignment(%{draft | "sequence" => 2}, wrong_key)
    release_request(publisher, promote, forged) |> error(409, "assignment_rejected")
    release_request(publisher, rollback, newer, reason: reason) |> error(409, "invalid_rollback")

    release_request(%{publisher | token: ctx.token}, promote, expanded)
    |> error(403, "role_denied")

    if cli = System.get_env("MIXER_TEST_RELEASE_CLI") do
      assert {output, 1} =
               stock_transition(publisher, cli, "rollback", newer, b, ["--reason", reason])

      assert output =~ "HTTP 409 (invalid_rollback)"

      assert {output, 1} =
               stock_transition(publisher, cli, "promote", forged, a, ["--rollout", "25"])

      assert output =~ "HTTP 409 (assignment_rejected)"
    end

    assert release_counts() == [[3, 1, Decimal.new(1)]]

    assert_release_action!(publisher, promote, expanded, a, 2, 7_500)
    assert %{status: 200} = release_request(publisher, publish, newer)

    release_request(publisher, rollback, sign_assignment(%{draft | "sequence" => 4}, wrong_key),
      reason: reason
    )
    |> error(409, "assignment_rejected")

    assert_release_action!(publisher, rollback, restored, a, 4, 2_500, reason)

    F.sql("""
    CREATE FUNCTION public.fixture_reject_release_publication() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'fixture deferred publication failure'; END
    $$
    """)

    F.sql("""
    CREATE CONSTRAINT TRIGGER fixture_reject_release_publication
    AFTER INSERT ON public.mixer_release_publications
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    EXECUTE FUNCTION public.fixture_reject_release_publication()
    """)

    try do
      release_request(publisher, promote, final) |> error(503, "authorization_unavailable")
      assert release_counts() == [[6, 4, Decimal.new(4)]]
    after
      F.sql(
        "DROP TRIGGER fixture_reject_release_publication ON public.mixer_release_publications"
      )

      F.sql("DROP FUNCTION public.fixture_reject_release_publication()")
    end

    # Postgrex discards the connection on an error returned by COMMIT.
    await_repo(WriterRepo, System.monotonic_time(:millisecond) + 4_000)
    assert_release_action!(publisher, promote, final, a, 5, 5_000)
    assert_release_action!(publisher, promote, expanded, a, 2, 7_500)
    assert_release_action!(publisher, rollback, restored, a, 4, 2_500, reason)

    ledger = release_journal()
    assert release_counts() == [[7, 5, Decimal.new(5)]]
    config = Application.fetch_env!(:mixer_hosted, :local_release_target)

    revoked =
      Enum.map(config.roots, fn root ->
        if root["assignment"], do: %{root | "revoked" => true}, else: root
      end)

    Application.put_env(:mixer_hosted, :local_release_target, %{config | roots: revoked})

    try do
      release_request(publisher, publish, initial) |> error(409, "assignment_rejected")

      if cli = System.get_env("MIXER_TEST_RELEASE_CLI") do
        for {action, signed, options} <- [
              {"promote", expanded, ["--rollout", "75"]},
              {"rollback", restored, ["--reason", reason]}
            ] do
          assert {output, 1} = stock_transition(publisher, cli, action, signed, a, options)
          assert output =~ "HTTP 409 (assignment_rejected)"
        end
      else
        release_request(publisher, promote, expanded) |> error(409, "assignment_rejected")

        release_request(publisher, rollback, restored, reason: reason)
        |> error(409, "assignment_rejected")
      end

      assert release_journal() == ledger
      assert release_counts() == [[7, 5, Decimal.new(5)]]
    after
      Application.put_env(:mixer_hosted, :local_release_target, config)
    end

    key = release_key(rollback, restored, reason)

    assert {:ok, identity} = ConfiguredVerifier.authenticate(publisher.token, F.now())
    %{target: target} = Application.fetch_env!(:mixer_hosted, :local_release_target)

    assert {:error, :idempotency_conflict} =
             MixerHosted.Releases.publish(
               identity,
               {:signed, target, restored, fn _ -> :ok end},
               key,
               reason,
               WriterRepo
             )

    release_request(publisher, rollback, restored, key: key, reason: "A changed reason")
    |> error(409, "idempotency_conflict")

    release_request(publisher, promote, restored, key: key, reason: reason)
    |> error(409, "idempotency_conflict")

    release_request(publisher, rollback, restored, key: "fresh-stale-key", reason: reason)
    |> error(409, "assignment_rejected")

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='owner',revision=revision+1 WHERE id='other-member'"
    )

    other = %{
      publisher
      | token:
          token(ctx.key, %{
            "sub" => "other-subject",
            "jti" => "other-token",
            "scope" => @scopes <> " mixer.release.publish"
          })
    }

    release_request(other, rollback, restored, reason: reason)
    |> error(409, "idempotency_conflict")

    F.sql(
      "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'"
    )

    release_request(publisher, rollback, restored, reason: reason)
    |> error(401, "unauthenticated")

    assert release_counts() == [[7, 5, Decimal.new(5)]]
    assert retained_artifacts() == artifacts
    assert F.counts() == [[2, 2, 2, 2]]

    default = "local development operation"

    expected = [
      [Decimal.new(1), nil, "publish", a, 2_500, initial, default],
      [Decimal.new(2), Decimal.new(1), "promote", a, 7_500, expanded, default],
      [Decimal.new(3), Decimal.new(2), "publish", b, 2_500, newer, default],
      [Decimal.new(4), Decimal.new(3), "rollback", a, 2_500, restored, reason],
      [Decimal.new(5), Decimal.new(4), "promote", a, 5_000, final, default]
    ]

    assert release_journal() == expected

    assert [[^key]] =
             F.sql(
               "SELECT idempotency_key FROM public.mixer_release_publications WHERE action='rollback'"
             ).rows
  end

  @tag :release_halt_db
  test "health halt commits an immutable sample and stops offers across API restart", ctx do
    {checked, config} = F.artifact(Runtime)
    {publisher, draft, private} = release_fixture!(ctx, checked, config, :delivery)
    digest = checked.manifest_sha256
    base = "/v3/orgs/org-a/projects/project-a/channels/dev/"
    halt_path = base <> "halt"
    observed = 9_223_372_036_854_775_808
    max = 18_446_744_073_709_551_615

    health = %{
      "sequence" => observed,
      "activated" => max,
      "pending" => 0,
      "adverse_signals" => max
    }

    initial =
      sign_assignment(
        %{draft | "sequence" => observed, "rollout_basis_points" => 10_000},
        private
      )

    halt_draft = %{draft | "sequence" => observed + 1, "rollout_basis_points" => 0}
    signed = sign_assignment(halt_draft, private)
    # Use the exact Swift JSONFile formatting so both callers share one receipt.
    body =
      ~s({"health":{\n  "activated" : #{max},\n  "adverse_signals" : #{max},\n  "pending" : 0,\n  "sequence" : #{observed}\n}\n,"signed_assignment":#{signed}})

    key = cli_key("POST", halt_path, body)

    submit = fn body, key ->
      request(publisher, "halt", "POST", halt_path, body, cli_headers(key))
    end

    migrate_release_actions!()
    grant_release_action!()
    start_release_delivery!(ctx.pg_settings)
    stage_release!(publisher, checked)

    assert %{status: 200} =
             request(
               publisher,
               "second artifact audit event",
               "PUT",
               path(publisher),
               checked.envelope_bytes,
               cli_headers("another-upload")
             )

    assert %{status: 200, body: legacy_audit} =
             request(publisher, "original audit", "GET", audit_path())

    assert %{"events" => [first, second], "next" => 2} = Jason.decode!(legacy_audit)
    assert {:ok, prior} = CustomerArtifactEvent.decode(first)
    assert {:ok, latest} = CustomerArtifactEvent.decode(second)
    assert :ok = CustomerArtifactEvent.validate_edge(prior, nil)
    assert :ok = CustomerArtifactEvent.validate_edge(latest, prior)

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='release_manager',revision=revision+1 WHERE id='member'"
    )

    assert %{status: 200} = release_request(publisher, base <> "publish", initial)
    before_upgrade = release_journal()
    assert release_counts() == [[2, 1, Decimal.new(observed)]]

    migrate_halt_health!()
    assert release_journal() == before_upgrade
    migrate_halt_audit!()

    audit_repo =
      {MixerHosted.Repo, ctx.pg_settings ++ [username: "http_release_writer", pool_size: 1]}

    start_supervised!(audit_repo)
    assert halt_audit(publisher, "audit without function grant").status == 503

    grant_halt_audit!()

    assert [[false, false]] =
             F.sql("""
             SELECT has_function_privilege('http_artifact_runtime', p.oid, 'EXECUTE'),
                    has_function_privilege('mixer_release_delivery', p.oid, 'EXECUTE')
             FROM pg_proc p WHERE p.oid =
               'public.mixer_release_audit_halts(text,text,text,text,text,text,text,numeric,integer)'::regprocedure
             """).rows

    assert %{"events" => [], "next" => 0} = halt_audit(publisher, "before halt") |> json()

    assert [[nil, nil, nil]] =
             F.sql("""
             SELECT health_activated,health_pending,health_adverse_signals
             FROM public.mixer_release_publications
             """).rows

    assert %{status: 200} = release_request(publisher, base <> "publish", initial)

    submit.(body, key) |> error(503, "authorization_unavailable")

    F.sql("""
    GRANT INSERT (health_activated,health_pending,health_adverse_signals)
      ON public.mixer_release_publications TO http_release_writer
    """)

    offer_path =
      "/v3/updates?" <>
        URI.encode_query(
          Map.merge(draft["scope"], %{
            "runtime" => draft["runtime"],
            "channel" => draft["channel"],
            "installation" => "local"
          })
        )

    public_artifact = "/v3/artifacts/" <> digest <> "?organization=org-a&project=project-a"

    assert %{status: 200} =
             offer = request(publisher, "initial offer", "GET", offer_path, "", [], token: nil)

    assert json(offer)["signed_assignment"] == Jason.decode!(initial)

    assert %{status: 200, body: envelope} =
             request(publisher, "initial artifact", "GET", public_artifact, "", [], token: nil)

    for malformed <- [
          halt_body(signed, Map.delete(health, "pending")),
          halt_body(signed, Map.put(health, "pending", nil)),
          halt_body(signed, Map.put(health, "pending", -1)),
          halt_body(signed, Map.put(health, "pending", max + 1)),
          halt_body(signed, Map.put(health, "pending", 1.0)),
          halt_body(signed, Map.put(health, "extra", 1)),
          String.replace(halt_body(signed, health), ~s("pending":0), ~s("pending":0,"pending":0)),
          String.replace_prefix(body, "{", ~s({"extra":0,))
        ] do
      submit.(malformed, key) |> error(400, "invalid_json")
    end

    submit.(body <> String.duplicate(" ", 128 * 1024), key) |> error(413, "body_too_large")
    submit.(halt_body(signed, %{health | "sequence" => 0}), key) |> error(422, "invalid_health")

    submit.(halt_body(signed, %{health | "adverse_signals" => 0}), key)
    |> error(422, "invalid_health")

    submit.(halt_body(signed, %{health | "sequence" => observed - 1}), key)
    |> error(409, "stale_rollout")

    nonzero = sign_assignment(%{halt_draft | "rollout_basis_points" => 1}, private)
    wrong_channel = sign_assignment(%{halt_draft | "channel" => "stable"}, private)
    wrong_artifact = sign_assignment(%{halt_draft | "artifact_sha256" => F.sha("other")}, private)
    wrong_runtime = sign_assignment(%{halt_draft | "runtime" => F.sha("other runtime")}, private)

    wrong_scope =
      sign_assignment(%{halt_draft | "scope" => %{draft["scope"] | "app" => "other"}}, private)

    wrong_release = sign_assignment(%{halt_draft | "release_id" => "other-release"}, private)
    reused_sequence = sign_assignment(%{halt_draft | "sequence" => observed}, private)
    forged = sign_assignment(halt_draft, elem(:crypto.generate_key(:eddsa, :ed25519), 1))

    for {assignment, status, code} <- [
          {nonzero, 422, "invalid_halt"},
          {wrong_channel, 422, "invalid_halt"},
          {wrong_artifact, 409, "stale_rollout"},
          {wrong_runtime, 422, "unknown_runtime"},
          {wrong_scope, 403, "scope_denied"},
          {wrong_release, 409, "assignment_rejected"},
          {reused_sequence, 409, "assignment_rejected"},
          {forged, 409, "assignment_rejected"}
        ] do
      submit.(halt_body(assignment, health), key) |> error(status, code)
    end

    request(
      publisher,
      "foreign tenant",
      "POST",
      String.replace(halt_path, "project-a", "project-b"),
      body,
      cli_headers(key)
    )
    |> error(403, "scope_denied")

    request(ctx, "bearer lacks release scope", "POST", halt_path, body, cli_headers(key))
    |> error(403, "role_denied")

    assert release_counts() == [[2, 1, Decimal.new(observed)]]

    F.sql("""
    CREATE FUNCTION public.fixture_reject_health_halt() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'fixture deferred halt failure'; END
    $$
    """)

    F.sql("""
    CREATE CONSTRAINT TRIGGER fixture_reject_health_halt
    AFTER INSERT ON public.mixer_release_publications
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    WHEN (NEW.action = 'halt') EXECUTE FUNCTION public.fixture_reject_health_halt()
    """)

    try do
      submit.(body, key) |> error(503, "authorization_unavailable")
      assert release_counts() == [[2, 1, Decimal.new(observed)]]

      assert %{"events" => [], "next" => 0} =
               halt_audit(publisher, "audit after commit rollback") |> json()
    after
      F.sql("DROP TRIGGER fixture_reject_health_halt ON public.mixer_release_publications")
      F.sql("DROP FUNCTION public.fixture_reject_health_halt()")
    end

    await_repo(WriterRepo, System.monotonic_time(:millisecond) + 4_000)

    # Expiry of artifact signing authority must not block a current assignment key.
    release_config = Application.fetch_env!(:mixer_hosted, :local_release_target)
    [artifact_root, assignment_root] = release_config.roots
    expired = %{artifact_root | "not_after_unix" => F.now()}

    Application.put_env(:mixer_hosted, :local_release_target, %{
      release_config
      | roots: [expired, assignment_root]
    })

    expected = %{
      "scope" => draft["scope"],
      "runtime" => draft["runtime"],
      "channel" => "dev",
      "artifact_sha256" => digest,
      "halt_sequence" => observed + 1,
      "health" => health
    }

    cli = System.get_env("MIXER_TEST_RELEASE_CLI")
    if cli, do: assert_stock_halt!(publisher, cli, signed, digest, expected)
    assert %{status: 200, body: reply} = submit.(body, key)
    assert Jason.decode!(reply) == expected
    Application.put_env(:mixer_hosted, :local_release_target, release_config)

    assert %{status: 200, body: halt_audit_body} =
             halt_audit(publisher, "operator audit after replay")

    assert Jason.decode!(halt_audit_body) == %{
             "events" => [
               %{
                 "id" => observed + 1,
                 "action" => "POST " <> halt_path,
                 "rollout_halt" => expected
               }
             ],
             "next" => observed + 1
           }

    assert %{status: 200, body: ^halt_audit_body} =
             halt_audit(publisher, "halt page from unsigned cursor", "&after=#{observed}&limit=1")

    for cursor <- [observed + 1, max] do
      assert %{"events" => [], "next" => ^cursor} =
               halt_audit(publisher, "terminal halt page", "&after=#{cursor}") |> json()
    end

    for query <- ["&after=#{max + 1}", "&view=rollout_halt", "&limit=101"] do
      halt_audit(publisher, "invalid halt page", query) |> error(400, "invalid_request")
    end

    assert %{status: 200, body: ^legacy_audit} =
             request(publisher, "artifact audit unchanged after halt", "GET", audit_path())

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='viewer',revision=revision+1 WHERE id='other-member'"
    )

    reader = %{
      publisher
      | token:
          token(ctx.key, %{
            "sub" => "other-subject",
            "jti" => "other-token",
            "scope" => "mixer.audit.read"
          })
    }

    if evidence = System.get_env("MIXER_ARTIFACT_HTTP_EVIDENCE"),
      do: File.write!(Path.join(evidence, "halt-audit-response.json"), halt_audit_body)

    assert %{status: 200, body: ^halt_audit_body} = halt_audit(reader, "viewer audit-only scope")

    other_target = %{release_config.target | channel: "stable"}

    Application.put_env(:mixer_hosted, :local_release_target, %{
      release_config
      | target: other_target
    })

    try do
      assert %{"events" => [], "next" => 0} =
               halt_audit(reader, "different configured channel") |> json()
    after
      Application.put_env(:mixer_hosted, :local_release_target, release_config)
    end

    assert %{status: 200, body: ^legacy_audit} =
             request(reader, "viewer artifact chain", "GET", audit_path())

    request(reader, "audit scope cannot read artifact", "GET", path(publisher))
    |> error(403, "permission_denied")

    request(reader, "viewer cannot halt", "POST", halt_path, body, cli_headers(key))
    |> error(403, "role_denied")

    wrong_scope = %{publisher | token: token(ctx.key, %{"scope" => "mixer.release.publish"})}
    halt_audit(wrong_scope, "publish scope cannot read audit") |> error(403, "permission_denied")

    request(
      reader,
      "halt audit other tenant",
      "GET",
      String.replace(audit_path(), "org-a", "org-b") <> "?view=rollout_halt"
    )
    |> error(404, "not_found")

    request(
      reader,
      "halt audit other project",
      "GET",
      String.replace(audit_path(), "project-a", "project-b") <> "?view=rollout_halt"
    )
    |> error(404, "not_found")

    # Even the permitted SQL role gets no rows without a live audit context.
    assert [] =
             Ecto.Adapters.SQL.query!(
               MixerHosted.Repo,
               """
               SELECT * FROM public.mixer_release_audit_halts(
                 'org-a','project-a','fieldlog','development',$1,$2,'dev',0,100)
               """,
               [draft["scope"]["platform"], draft["runtime"]],
               log: false
             ).rows

    assert [[previous, activated, pending, adverse, ^signed, request_hash]] =
             F.sql("""
             SELECT p.previous_sequence::text, p.health_activated::text, p.health_pending::text,
                    p.health_adverse_signals::text, p.signed_assignment_bytes, r.request_sha256
             FROM public.mixer_release_publications p
             JOIN public.mixer_release_cli_requests r
               ON r.idempotency_key=p.idempotency_key AND r.publication_sequence=p.sequence
             WHERE p.action='halt'
             """).rows

    assert [previous, activated, pending, adverse] ==
             Enum.map([observed, max, 0, max], &to_string/1)

    assert request_hash ==
             F.sha("POST " <> halt_path <> "\0local development operation\0" <> body)

    assert release_counts() == [[3, 2, Decimal.new(observed + 1)]]
    assert_no_offer!(publisher, offer_path)

    assert %{status: 200, body: ^envelope} =
             request(publisher, "historical artifact after halt", "GET", public_artifact, "", [],
               token: nil
             )

    :ok = Supervisor.terminate_child(ctx.endpoint_supervisor, MixerHostedWeb.Endpoint)
    stop_supervised!(WriterRepo)
    stop_supervised!(DeliveryRepo)
    stop_supervised!(MixerHosted.Repo)
    start_release_writer!(ctx.pg_settings)
    start_release_delivery!(ctx.pg_settings)
    start_supervised!(audit_repo)
    assert {:ok, _} = Supervisor.restart_child(ctx.endpoint_supervisor, MixerHostedWeb.Endpoint)
    publisher = %{publisher | port: endpoint_port!()}
    reader = %{reader | port: publisher.port}
    assert_no_offer!(publisher, offer_path)
    if cli, do: assert_stock_halt!(publisher, cli, signed, digest, expected)

    submit = fn bytes, key ->
      request(publisher, "halt after restart", "POST", halt_path, bytes, cli_headers(key))
    end

    assert %{status: 200, body: ^reply} = submit.(body, key)
    assert %{status: 200, body: ^halt_audit_body} = halt_audit(reader, "halt audit after restart")

    assert %{status: 200, body: ^legacy_audit} =
             request(reader, "artifact audit after restart", "GET", audit_path())

    assert %{"events" => [^second], "next" => 2} =
             request(
               reader,
               "artifact cursor after restart",
               "GET",
               audit_path() <> "?after=1&limit=1"
             )
             |> json()

    submit.(halt_body(signed, %{health | "pending" => 2}), key)
    |> error(409, "idempotency_conflict")

    submit.(body <> " ", key) |> error(409, "idempotency_conflict")
    second_halt = sign_assignment(%{halt_draft | "sequence" => observed + 2}, private)

    submit.(halt_body(second_halt, %{health | "sequence" => observed + 1}), "already-halted")
    |> error(409, "stale_rollout")

    resumed =
      sign_assignment(
        %{draft | "sequence" => observed + 2, "rollout_basis_points" => 10_000},
        private
      )

    assert_release_action!(publisher, base <> "promote", resumed, digest, observed + 2, 10_000)

    assert %{status: 200} =
             offer = request(publisher, "resumed offer", "GET", offer_path, "", [], token: nil)

    assert json(offer)["signed_assignment"] == Jason.decode!(resumed)
    assert %{status: 200, body: ^reply} = submit.(body, key)
    if cli, do: assert_stock_halt!(publisher, cli, signed, digest, expected)
    submit.(body, "fresh-stale") |> error(409, "stale_rollout")

    assert %{status: 200, body: ^halt_audit_body} =
             halt_audit(reader, "halt audit after promotion and replay")

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='viewer',revision=revision+1 WHERE id='member'"
    )

    submit.(body, key) |> error(403, "role_denied")

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='owner',revision=revision+1 WHERE id='member'"
    )

    revoked = %{assignment_root | "revoked" => true}

    Application.put_env(:mixer_hosted, :local_release_target, %{
      release_config
      | roots: [artifact_root, revoked]
    })

    submit.(body, key) |> error(409, "assignment_rejected")
    assert release_counts() == [[4, 3, Decimal.new(observed + 2)]]

    assert_raise Postgrex.Error, ~r/release ledger contains committed health halts/, fn ->
      Ecto.Migrator.down(Migration, @health_version, @health_migration, log: false)
    end
  end

  defp halt_audit(ctx, label, query \\ ""),
    do: request(ctx, label, "GET", audit_path() <> "?view=rollout_halt" <> query)

  defp migrate_halt_health! do
    unless Code.ensure_loaded?(@health_migration),
      do:
        Code.require_file(
          "priv/repo/migrations/#{@health_version}_add_local_release_halt_health.exs"
        )

    assert :ok = Ecto.Migrator.up(Migration, @health_version, @health_migration, log: false)
  end

  defp migrate_halt_audit! do
    unless Code.ensure_loaded?(@halt_audit_migration),
      do:
        Code.require_file(
          "priv/repo/migrations/#{@halt_audit_version}_add_local_release_halt_audit.exs"
        )

    assert :ok =
             Ecto.Migrator.up(Migration, @halt_audit_version, @halt_audit_migration, log: false)
  end

  defp grant_halt_audit! do
    F.sql("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_audit_halts(text,text,text,text,text,text,text,numeric,integer)
      TO http_release_writer
    """)
  end

  defp halt_body(signed, health) do
    ~s({"health":#{Jason.encode!(health)},"signed_assignment":#{signed}})
  end

  defp assert_no_offer!(publisher, offer_path) do
    assert %{status: 204, body: ""} =
             request(publisher, "halted offer", "GET", offer_path, "", [], token: nil)
  end

  defp assert_stock_halt!(publisher, cli, signed, digest, receipt) do
    path = Path.join(System.fetch_env!("MIXER_TEST_RELEASE_CANDIDATE"), "halt-health.json")
    File.mkdir_p!(Path.dirname(path))
    File.write!(path, Jason.encode!(receipt["health"]))

    assert {output, 0} =
             stock_transition(publisher, cli, "halt", signed, digest, [
               "--health",
               path,
               "--channel",
               "dev"
             ])

    assert Jason.decode!(output) == %{
             "status" => "ok",
             "action" => "halt",
             "artifact_sha256" => digest,
             "sequence" => receipt["halt_sequence"],
             "rollout_basis_points" => 0,
             "health" => receipt["health"],
             "delivery" => "local_only"
           }
  end

  defp start_release_delivery!(settings) do
    env = :local_release_delivery
    login = "mixer_release_delivery"

    F.sql(
      "DO $$ BEGIN CREATE ROLE #{login} LOGIN NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    F.sql("GRANT USAGE ON SCHEMA public TO #{login}")

    F.sql("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_delivery_offer(text,text,text,text,text,text,text),
      public.mixer_release_delivery_artifact(text,text,text,text,text,text,text,text) TO #{login}
    """)

    config = Application.fetch_env!(:mixer_hosted, :local_release_target)

    Application.put_env(
      :mixer_hosted,
      env,
      Map.put(config, :repo, settings ++ [username: login, pool_size: 1])
    )

    on_exit(fn -> Application.delete_env(:mixer_hosted, env) end)

    for child <- PublicDelivery.children(http: [ip: {127, 0, 0, 1}]) do
      start_supervised!(child)
    end

    assert [[^login]] =
             Ecto.Adapters.SQL.query!(DeliveryRepo, "SELECT current_user", [], log: false).rows
  end

  defp release_fixture!(ctx, checked, config, delivery \\ :disabled) do
    %{manifest: manifest, manifest_sha256: digest} = checked
    scope = manifest["scope"]

    target = %Target{
      scope: %Scope{
        organization_id: scope["organization"],
        project_id: scope["project"],
        application_id: scope["app"],
        environment_id: scope["environment"]
      },
      platform: scope["platform"],
      runtime_sha256: manifest["runtime"],
      channel: "dev"
    }

    {public, private} = :crypto.generate_key(:eddsa, :ed25519)
    [root] = config.roots

    assignment_root = %{
      root
      | "key_id" => "cli-assignment",
        "public_key" => public,
        "artifact" => false,
        "assignment" => true
    }

    provision_release_writer!(target, delivery)
    start_release_writer!(ctx.pg_settings)
    Application.put_env(:mixer_hosted, CustomerArtifacts, config)

    Application.put_env(:mixer_hosted, :local_release_target, %{
      target: target,
      host: config.host,
      roots: [root, assignment_root]
    })

    on_exit(fn -> Application.delete_env(:mixer_hosted, :local_release_target) end)

    publisher = %{
      ctx
      | token: token(ctx.key, %{"scope" => @scopes <> " mixer.release.publish"}),
        checked: checked
    }

    draft = %{
      "schema" => 3,
      "scope" => scope,
      "channel" => target.channel,
      "cohort" => "sha256-v1",
      "rollout_basis_points" => 2_500,
      "sequence" => 1,
      "release_id" => manifest["release_id"],
      "artifact_sha256" => digest,
      "runtime" => target.runtime_sha256,
      "key_id" => assignment_root["key_id"],
      "created_at_unix" => F.now()
    }

    {publisher, draft, private}
  end

  defp provision_release_writer!(target, delivery) do
    if delivery == :delivery do
      Code.require_file(
        "priv/local_release_delivery/20261120000003_add_local_release_delivery.exs"
      )
    end

    for {version, module, file} <- [
          {20_261_120_000_001, MixerHosted.Repo.Migrations.AddLocalReleaseLedger,
           "add_local_release_ledger"},
          {20_261_120_000_002, MixerHosted.Repo.Migrations.AddLocalReleaseHeadRead,
           "add_local_release_head_read"},
          {20_261_120_000_004, MixerHosted.Repo.Migrations.AddLocalReleaseCLIRequests,
           "add_local_release_cli_requests"}
        ] do
      if version == 20_261_120_000_004 and delivery == :delivery do
        assert Ecto.Migrator.up(
                 Migration,
                 20_261_120_000_003,
                 MixerHosted.Repo.Migrations.AddLocalReleaseDelivery,
                 log: false
               ) in [:ok, :already_up]
      end

      unless Code.ensure_loaded?(module),
        do: Code.require_file("priv/repo/migrations/#{version}_#{file}.exs")

      assert Ecto.Migrator.up(Migration, version, module, log: false) in [:ok, :already_up]
    end

    unless Code.ensure_loaded?(@action_migration),
      do:
        Code.require_file(
          "priv/repo/migrations/#{@action_version}_add_local_release_publication_action.exs"
        )

    if Code.ensure_loaded?(@halt_audit_migration) do
      assert Ecto.Migrator.down(Migration, @halt_audit_version, @halt_audit_migration, log: false) in [
               :ok,
               :already_down
             ]
    end

    if Code.ensure_loaded?(@health_migration) do
      assert Ecto.Migrator.down(Migration, @health_version, @health_migration, log: false) in [
               :ok,
               :already_down
             ]
    end

    assert Ecto.Migrator.down(Migration, @action_version, @action_migration, log: false) in [
             :ok,
             :already_down
           ]

    F.sql("GRANT USAGE ON SCHEMA public TO http_release_writer")

    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{table} TO http_release_writer")

    for action <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{action}() TO http_release_writer"
          )

    F.sql("GRANT SELECT,UPDATE(sequence) ON public.mixer_release_heads TO http_release_writer")

    F.sql("""
    GRANT SELECT,INSERT (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,
      channel,sequence,previous_sequence,artifact_sha256,signed_assignment_bytes,rollout_basis_points,
      idempotency_key,reason,principal_id) ON public.mixer_release_publications TO http_release_writer
    """)

    F.sql("GRANT SELECT,INSERT ON public.mixer_release_cli_requests TO http_release_writer")

    F.sql("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_publish_allowed(text,text,text,text),
      public.mixer_release_read_allowed(text,text,text,text),
      public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text) TO http_release_writer
    """)

    F.sql(
      "UPDATE public.mixer_authz_memberships SET role='owner',revision=revision+1 WHERE id='member'"
    )

    Ecto.Adapters.SQL.query!(
      Migration,
      """
      INSERT INTO public.mixer_release_heads
        (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,writer_role)
      VALUES ('org-a','project-a','fieldlog','development',$1,$2,$3,'http_release_writer')
      """,
      [target.platform, target.runtime_sha256, target.channel],
      log: false
    )
  end

  defp start_release_writer!(settings) do
    refute Process.whereis(WriterRepo)

    Application.put_env(
      :mixer_hosted,
      WriterRepo,
      settings ++ [username: "http_release_writer", pool_size: 1]
    )

    on_exit(fn -> Application.delete_env(:mixer_hosted, WriterRepo) end)
    assert [child] = WriterRepo.children(http: [ip: {127, 0, 0, 1}])
    start_supervised!(child)

    assert [["http_release_writer"]] =
             Ecto.Adapters.SQL.query!(WriterRepo, "SELECT current_user", [], log: false).rows
  end

  defp migrate_release_actions! do
    assert :ok = Ecto.Migrator.up(Migration, @action_version, @action_migration, log: false)
  end

  defp grant_release_action! do
    F.sql("GRANT INSERT (action) ON public.mixer_release_publications TO http_release_writer")
  end

  defp release_action_grants do
    F.sql("""
    SELECT has_column_privilege('http_release_writer', 'public.mixer_release_publications', 'action', 'SELECT'),
           has_column_privilege('http_release_writer', 'public.mixer_release_publications', 'action', 'INSERT'),
           has_column_privilege('http_release_writer', 'public.mixer_release_publications', 'recorded_at', 'INSERT'),
           has_any_column_privilege('http_release_writer', 'public.mixer_release_publications', 'UPDATE'),
           has_table_privilege('http_release_writer', 'public.mixer_release_publications', 'INSERT')
    """).rows
  end

  defp release_journal do
    F.sql("""
    SELECT p.sequence,p.previous_sequence,p.action,p.artifact_sha256,p.rollout_basis_points,
      p.signed_assignment_bytes,p.reason
    FROM public.mixer_release_publications p
    JOIN public.mixer_release_cli_requests r ON p.idempotency_key=r.idempotency_key
      AND p.sequence=r.publication_sequence AND p.artifact_sha256=r.artifact_sha256
      AND p.principal_id=r.principal_id
    ORDER BY p.sequence
    """).rows
  end

  defp cli_key(method, path, bytes),
    do: cli_key(method, path, bytes, nil)

  defp cli_key(method, path, bytes, reason),
    do: F.sha("mixer-local-release-v3\0#{method}\0#{path}\0#{reason}\0" <> bytes)

  defp cli_headers(key), do: [{"content-type", "application/json"}, {"idempotency-key", key}]

  defp assignment_body(signed), do: ~s({"signed_assignment":#{signed}})

  defp release_key(path, signed, reason),
    do: cli_key("POST", path, assignment_body(signed), reason)

  defp release_request(ctx, path, signed, opts \\ []) do
    reason = opts[:reason]
    headers = cli_headers(opts[:key] || release_key(path, signed, reason))
    headers = if reason, do: [{"x-mixer-reason", reason} | headers], else: headers

    request(
      ctx,
      opts[:label] || Path.basename(path),
      "POST",
      path,
      assignment_body(signed),
      headers
    )
  end

  defp stage_release!(publisher, artifact) do
    upload =
      ~s({"signed_manifest":#{artifact.signed_manifest_bytes},"payload":"#{Base.encode64(artifact.payload)}"})

    upload_path = path(%{publisher | checked: artifact})

    assert %{status: 201} =
             request(
               publisher,
               "upload retained candidate",
               "PUT",
               upload_path,
               upload,
               cli_headers(cli_key("PUT", upload_path, upload))
             )

    validate = "/v3/orgs/org-a/projects/project-a/releases/validate"
    body = Jason.encode!(%{"artifact_sha256" => artifact.manifest_sha256})

    assert %{status: 200} =
             request(
               publisher,
               "validate retained candidate",
               "POST",
               validate,
               body,
               cli_headers(cli_key("POST", validate, body))
             )
  end

  defp retained_artifacts do
    F.sql("""
    SELECT manifest_sha256,signed_manifest_bytes,payload
    FROM public.mixer_customer_artifacts ORDER BY manifest_sha256
    """).rows
  end

  defp assert_release_action!(ctx, path, signed, digest, sequence, rollout, reason \\ nil) do
    expected = %{
      "artifact_sha256" => digest,
      "sequence" => sequence,
      "rollout_basis_points" => rollout,
      "delivery" => "local_only"
    }

    if cli = System.get_env("MIXER_TEST_RELEASE_CLI") do
      action = Path.basename(path)

      options =
        if reason, do: ["--reason", reason], else: ["--rollout", to_string(div(rollout, 100))]

      assert {output, 0} = stock_transition(ctx, cli, action, signed, digest, options)
      assert Jason.decode!(output) == Map.merge(expected, %{"status" => "ok", "action" => action})
    else
      actual = release_request(ctx, path, signed, reason: reason)
      assert actual.status == 200
      assert json(actual) == expected
    end
  end

  defp stock_transition(ctx, cli, action, signed, digest, options) do
    dir = System.fetch_env!("MIXER_TEST_RELEASE_CANDIDATE")
    File.mkdir_p!(dir)
    assignment = Path.join(dir, "signed-transition.json")
    File.write!(assignment, signed)
    stock_update(ctx, cli, [action, digest, "--assignment", assignment] ++ options)
  end

  defp sign_assignment(assignment, key) do
    {:ok, cbor} = ArtifactCBOR.encode(assignment)
    signature = :crypto.sign(:eddsa, :none, "mixer.assignment.v3\0" <> cbor, [key, :ed25519])
    Jason.encode!(%{"assignment" => assignment, "signature" => Base.encode64(signature)})
  end

  defp release_counts do
    F.sql("""
    SELECT (SELECT count(*) FROM public.mixer_release_cli_requests),
           (SELECT count(*) FROM public.mixer_release_publications),
           (SELECT sequence FROM public.mixer_release_heads)
    """).rows
  end

  defp stock_update(ctx, cli, args) do
    System.cmd(
      cli,
      ["update" | args] ++ ["--organization", "org-a", "--project", "project-a"],
      env: [
        {"MIXER_RELEASE_ORIGIN", "http://127.0.0.1:#{ctx.port}"},
        {"MIXER_RELEASE_TOKEN", ctx.token}
      ],
      stderr_to_stdout: true
    )
  end

  test "real default bearer verifier and PostgreSQL create retry read audit and wire HEAD", ctx do
    requests_before = TLSFixture.info(ctx.tls_fixture).requests

    error(
      request(
        ctx,
        "missing bearer does not fetch JWKS",
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

    assert TLSFixture.info(ctx.tls_fixture).requests == requests_before

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
    transport = TLSFixture.info(ctx.tls_fixture)
    assert transport.requests != []

    if directory = System.get_env("MIXER_ARTIFACT_HTTP_EVIDENCE") do
      File.write!(
        Path.join(directory, "identity-transport.json"),
        Jason.encode!(
          %{
            request_count: length(transport.requests),
            ephemeral_tls_key_directory_removed: transport.key_dir_removed,
            requests:
              Enum.map(transport.requests, fn entry ->
                %{
                  request_line: entry.request |> String.split("\r\n") |> hd(),
                  sni: to_string(entry.tls[:sni_hostname])
                }
              end)
          },
          pretty: true
        )
      )
    end

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

    oversized = String.duplicate(" ", 6_291_456) <> "x"

    error(
      request(ctx, "raw document exceeds six MiB", "PUT", path(ctx), oversized, upload_headers()),
      413,
      "body_too_large"
    )

    assert F.counts() == [[0, 0, 0, 0]]
    empty = request(ctx, "empty audit defaults", "GET", audit_path() <> "?after=&limit=")
    assert empty.status == 200 and json(empty) == %{"events" => [], "next" => 0}
  end

  test "percent escaped raw path aliases reject before artifact mutation", ctx do
    <<first, rest::binary>> = ctx.checked.manifest_sha256
    escaped_digest = "%" <> Base.encode16(<<first>>, case: :upper) <> rest

    aliases = [
      {"encoded static route", String.replace(path(ctx), "/v3/", "/%76%33/")},
      {"encoded tenant identifier", String.replace(path(ctx), "/org-a/", "/org%2Da/")},
      {"encoded digest nibble",
       String.replace(path(ctx), ctx.checked.manifest_sha256, escaped_digest)}
    ]

    for {label, target} <- aliases do
      error(
        request(ctx, label, "PUT", target, ctx.checked.envelope_bytes, upload_headers()),
        400,
        "invalid_path"
      )

      assert F.counts() == [[0, 0, 0, 0]]
    end
  end

  defp await_repo(repo, deadline) do
    case Ecto.Adapters.SQL.query(repo, "SELECT 1", [], log: false, queue: false, timeout: 100) do
      {:ok, _} ->
        :ok

      _ ->
        if System.monotonic_time(:millisecond) >= deadline,
          do: flunk("#{inspect(repo)} did not reconnect")

        Process.sleep(25)
        await_repo(repo, deadline)
    end
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
          for table <- ~w(artifacts audit_events idempotency) do
            if String.starts_with?(metadata.query, "INSERT INTO public.mixer_customer_#{table} ") do
              rows =
                case metadata.result do
                  {:ok, %{num_rows: count}} -> count
                  _ -> :failed
                end

              send(parent, {:write_stage, table, rows})
            end
          end

          if String.starts_with?(
               metadata.query,
               "UPDATE public.mixer_customer_artifact_heads SET "
             ) do
            rows =
              case metadata.result do
                {:ok, %{num_rows: count}} -> count
                _ -> :failed
              end

            send(parent, {:write_stage, "artifact_heads", rows})
          end

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

    for table <- ~w(artifacts audit_events idempotency artifact_heads),
        do: assert_receive({:write_stage, ^table, 1}, 2000)

    assert_receive {:post_write_backend_terminated, [[true]]}, 2000

    if directory = System.get_env("MIXER_ARTIFACT_HTTP_EVIDENCE") do
      File.write!(
        Path.join(directory, "transaction-boundary.json"),
        Jason.encode!(
          %{
            completed_local_writes: %{
              artifacts: 1,
              audit_events: 1,
              idempotency: 1,
              artifact_heads: 1
            },
            constraints_checked_before_backend_termination: true,
            backend_termination_confirmed: true,
            response_status: failed.status,
            committed_counts_after_failure: F.counts()
          },
          pretty: true
        )
      )
    end

    error(failed, 503, "authorization_unavailable")
    assert F.counts() == [[0, 0, 0, 0]]
    await_repo(Runtime, System.monotonic_time(:millisecond) + 4_000)

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
