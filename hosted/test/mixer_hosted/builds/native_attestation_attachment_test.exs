defmodule MixerHosted.Builds.NativeAttestationAttachmentTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Builds.{Dispatch, Journal, Lifecycle, RetainedNativeArtifacts}
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  alias MixerHosted.CustomerBuilds
  alias MixerHosted.CustomerBuilds.{AttestationRepo, AttestationSchema, LocalAttestation, Schema}
  alias MixerHosted.Identity.{KeyOwnerSupervisor, TLSFixture}
  alias MixerHosted.Repo
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Repo.Migrations
  alias MixerHosted.RuntimeConfig
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Wire
  alias MixerHostedWeb.Endpoint

  defmodule Admin do
    use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
  end

  defmodule Migration do
    use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
  end

  defmodule SignerFixture do
    import Plug.Conn

    def init(opts), do: opts

    def call(conn, %{token: token, identity: identity}) do
      conn = fetch_cookies(conn)

      with "GET" <- conn.method,
           ^token <- conn.req_cookies["__Host-mixer-session"],
           {:ok, selection} <- MixerHostedWeb.BrowserBuildRequest.parse(conn.query_string),
           {:ok, media, body} <- read(conn.request_path, identity, selection) do
        conn
        |> put_resp_header("cache-control", "no-store")
        |> put_resp_header("content-type", media)
        |> send_resp(200, body)
      else
        _ -> send_resp(conn, 404, "")
      end
    end

    defp read("/console-api/v1/build-attestation-completion", identity, selection) do
      with {:ok, dto} <- CustomerBuilds.read(identity, selection, :attestation_completion) do
        {:ok, "application/json; charset=utf-8", Jason.encode!(%{build: dto})}
      end
    end

    defp read("/console-api/v1/build-artifacts/" <> kind, identity, selection) do
      with {:ok, {:retained_native, operation, artifact}} <-
             CustomerBuilds.read(identity, selection, kind),
           {:ok, bytes} <- RetainedNativeArtifacts.read(operation, artifact) do
        {:ok, "application/octet-stream", bytes}
      end
    end

    defp read(_, _, _), do: {:error, :not_found}
  end

  @socket "MIXER_ATTESTATION_TEST_SOCKET"
  if !System.get_env(@socket),
    do: @moduletag(skip: "requires the disposable W12 PostgreSQL fixture")

  @moduletag :native_attestation_db
  @writer "mixer_native_attestation_writer"
  @reader "attestation_fixture_reader"
  @go_signer "MIXER_ATTESTATION_TEST_GO_SIGNER"
  @admin "mixer_attestation_fixture_admin"
  @database "mixer_native_attestation_fixture"
  @origin "http://127.0.0.1:59709"
  @binding String.duplicate("4", 64)
  @table "public.mixer_native_development_attestations"
  @entry "public.mixer_native_development_attestation_v1(text,text,text,text,jsonb,text,text,text,text,bytea)"

  setup_all do
    socket = System.fetch_env!(@socket)
    assert Path.type(socket) == :absolute
    assert File.exists?(Path.join(socket, ".s.PGSQL.5432.lock"))

    opts = [socket_dir: socket, database: @database, log: false, pool_size: 2]
    start_supervised!({Admin, opts ++ [username: @admin]})
    assert sql("SELECT current_database(), inet_server_addr()::text").rows == [[@database, nil]]

    for {role, mode} <- [
          attestation_fixture_owner: "NOLOGIN",
          mixer_native_attestation_writer: "LOGIN",
          attestation_fixture_reader: "LOGIN"
        ] do
      sql("CREATE ROLE #{role} #{mode} NOSUPERUSER NOBYPASSRLS NOINHERIT")
    end

    start_supervised!(
      {Migration,
       opts ++
         [
           username: @admin,
           after_connect: fn conn ->
             Postgrex.query!(conn, "SET ROLE attestation_fixture_owner", [])
           end
         ]}
    )

    sql("GRANT USAGE,CREATE ON SCHEMA public TO attestation_fixture_owner")
    sql("GRANT USAGE ON SCHEMA public TO #{@writer},attestation_fixture_reader")

    for {version, module, name} <- [
          {20_261_024_000_000, Migrations.AddOban, "add_oban"},
          {20_261_025_000_000, Migrations.AddBuildJournals, "add_build_journals"},
          {20_261_025_000_001, Migrations.AddBuildAdmission, "add_build_admission"},
          {20_261_025_000_003, Migrations.AddCustomerAuthorization, "add_customer_authorization"},
          {20_261_025_000_004, Migrations.AddAuthorizationStateRevisions,
           "add_authorization_state_revisions"},
          {20_261_120_000_020, Migrations.AddNativeDevelopmentAttestations,
           "add_native_development_attestations"}
        ] do
      paths = Path.wildcard("priv/**/#{version}_#{name}.exs")
      [path] = paths
      unless Code.ensure_loaded?(module), do: Code.require_file(path)
      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    assert sql("SELECT has_function_privilege($1,$2,'EXECUTE')", [@writer, @entry]).rows == [
             [false]
           ]

    sql(AttestationSchema.fixture_grant_statement())

    read_entry = "public.mixer_customer_build_read_v1(#{Schema.signature()})"
    Ecto.Adapters.SQL.query!(Migration, Schema.ddl(), [], log: false)
    sql("REVOKE EXECUTE ON FUNCTION #{read_entry} FROM PUBLIC")
    sql("GRANT EXECUTE ON FUNCTION #{read_entry} TO #{@reader}")

    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships) do
      sql("GRANT SELECT ON public.mixer_authz_#{table} TO #{@writer},#{@reader}")
    end

    for helper <- ~w(profiles principals families credentials organization_heads project_heads) do
      sql(
        "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO #{@writer},#{@reader}"
      )
    end

    seed_identity!()
    %{socket: socket, repo_opts: opts}
  end

  setup %{socket: socket, test: test, repo_opts: opts} = context do
    build = "build-" <> String.slice(sha(Atom.to_string(test)), 0, 16)
    run_id = Base.encode16(:crypto.strong_rand_bytes(8), case: :lower)
    root = Path.join(socket, build <> "-" <> run_id)
    File.mkdir!(root)
    on_exit(fn -> File.rm_rf!(root) end)
    File.chmod!(root, 0o700)
    {spki, key} = keypair()

    unless context[:ordinary_http] do
      start_supervised!({AttestationRepo, opts ++ [username: @writer]})
      assert_login!(AttestationRepo, @writer)
      put_config(:native_development_dispatch, %{retained_root: root})
      put_config(:native_development_attestation, %{origin: @origin, public_spki_der: spki})
    end

    selection = %{
      organization_id: "org-a",
      project_id: "project",
      application_id: "app",
      build_id: build,
      platform: "ios",
      source_sha256: String.duplicate("1", 64),
      toolchain_lock_sha256: String.duplicate("2", 64),
      build_definition_sha256: String.duplicate("3", 64)
    }

    %{selection: selection, root: root, identity: identity(), spki: spki, key: key}
  end

  test "exact settled second attempt is appended once under concurrent replay", c do
    b = completed!(c.selection, retry: true)
    retain!(c.root, b.operation, b.products)
    envelope = envelope(c, b)

    results =
      [envelope, envelope]
      |> Task.async_stream(&attach(c, &1), max_concurrency: 2)
      |> Enum.map(fn {:ok, result} -> result end)

    assert Enum.sort(results) == [{:ok, :attached}, {:ok, :duplicate}]
    assert {:ok, :duplicate} = attach(c, envelope)
    assert stored(b) == [[5, 2, b.operation, @binding, sha(c.spki), @origin, envelope]]

    assert sql("SELECT revision,journal FROM public.mixer_builds WHERE id=$1", [b.id]).rows ==
             [[5, b.journal]]
  end

  unless System.get_env(@go_signer), do: @tag(skip: "requires the compiled Go signer")

  test "Go signs the authorized worker operation and PostgreSQL attachment verifies it", c do
    b = completed!(c.selection, retry: true)
    retain!(c.root, b.operation, b.products)
    {port, _path, signed} = go_sign!(c, b)
    origin = "http://127.0.0.1:#{port}"

    Application.put_env(:mixer_hosted, :native_development_attestation, %{
      origin: origin,
      public_spki_der: c.spki
    })

    assert {:ok, :attached} = attach(c, signed)
    assert {:ok, :duplicate} = attach(c, signed)
    assert stored(b) == [[5, 2, b.operation, @binding, sha(c.spki), origin, signed]]
  end

  @tag :ordinary_http
  unless System.get_env(@go_signer), do: @tag(skip: "requires the compiled Go attestation CLI")

  test "stock Go attach sends the same signed envelope twice through the ordinary v3 writer", c do
    b = completed!(c.selection, retry: true)
    retain!(c.root, b.operation, b.products)
    put_config(:native_development_dispatch, %{retained_root: c.root})
    {port, path, signed} = go_sign!(c, b)
    origin = "http://127.0.0.1:#{port}"

    jwt = start_bearer_fixture!(c.identity)
    token = bearer(jwt, c.identity, "mixer.build.attest")
    public_path = Path.join(c.root, "trusted-public.pem")

    write_private_file!(
      public_path,
      :public_key.pem_encode([{:SubjectPublicKeyInfo, c.spki, :not_encrypted}])
    )

    start_http_api!(c, port, c.spki)
    assert_login!(Repo, @reader)
    assert_login!(AttestationRepo, @writer)
    assert writer_count() == 1
    assert stored(b) == []

    assert {"attached\n", 0} = go_attest(c, "attach", origin, public_path, token)
    assert stored(b) == [[5, 2, b.operation, @binding, sha(c.spki), origin, signed]]
    assert {"duplicate\n", 0} = go_attest(c, "attach", origin, public_path, token)
    assert stored(b) == [[5, 2, b.operation, @binding, sha(c.spki), origin, signed]]
    assert File.read!(path) == signed

    assert sql("SELECT revision,journal FROM public.mixer_builds WHERE id=$1", [b.id]).rows ==
             [[5, b.journal]]

    stop_http_api!(port)
  end

  defp go_sign!(c, b) do
    start_supervised!({Repo, c.repo_opts ++ [username: @reader]})
    assert_login!(Repo, @reader)
    identity = %{c.identity | scopes: ["mixer.build.read"]}

    assert {:ok, %{state: "native_succeeded", artifacts: [_, _, _]} = legacy_detail} =
             CustomerBuilds.read(identity, c.selection)

    refute Map.has_key?(legacy_detail, :workerOperationId)

    token = Base.url_encode64(:crypto.strong_rand_bytes(32), padding: false)
    plug = {SignerFixture, %{token: token, identity: identity}}

    listener =
      start_supervised!(
        {Bandit, plug: plug, ip: {127, 0, 0, 1}, port: 0, startup_log: false},
        id: SignerFixture
      )

    {:ok, {{127, 0, 0, 1}, port}} = ThousandIsland.listener_info(listener)
    origin = "http://127.0.0.1:#{port}"

    key_path = Path.join(c.root, "test-key.pem")
    der = Base.decode16!("302E020100300506032B657004220420") <> c.key

    write_private_file!(
      key_path,
      :public_key.pem_encode([{:PrivateKeyInfo, der, :not_encrypted}])
    )

    assert {output, 0} = go_attest(c, "sign", origin, key_path, token)
    File.rm!(key_path)
    stop_supervised!(SignerFixture)
    stop_supervised!(Repo)

    name = String.trim(output)
    assert Path.basename(name) == name
    path = Path.join(c.root, name)
    signed = File.read!(path)

    assert %{
             "statement" => %{
               "profile" => "mixer.native-build.ios-simulator.development.v2",
               "provenance" => %{"workerOperationId" => operation}
             }
           } = Jason.decode!(signed)

    assert operation == b.operation
    {port, path, signed}
  end

  defp go_attest(c, command, origin, key_path, token) do
    token_path = Path.join(c.root, "go-token")
    write_private_file!(token_path, token <> "\n")

    try do
      System.cmd(
        "/bin/sh",
        [
          "-c",
          ~s(input=$1; shift; exec "$@" < "$input"),
          "fixture",
          token_path,
          System.fetch_env!(@go_signer),
          command,
          "-origin",
          origin,
          "-selection",
          URI.encode_query(c.selection),
          "-state",
          c.root,
          "-key",
          key_path
        ],
        stderr_to_stdout: true
      )
    after
      File.rm!(token_path)
    end
  end

  @tag :ordinary_http
  test "ordinary v3 human HTTP attaches the exact current V2 envelope once", c do
    port = http_port!()
    origin = "http://127.0.0.1:#{port}"
    jwt = start_bearer_fixture!(c.identity)

    prior = completed!(c.selection, retry: true)
    stale = envelope(c, prior, origin: origin)
    remove_build!(prior)
    b = completed!(c.selection, retry: true)
    assert prior.operation != b.operation
    assert prior.journal == b.journal
    retain!(c.root, b.operation, b.products)

    tenant = completed!(%{c.selection | organization_id: "org-b"}, retry: true)
    retain!(c.root, tenant.operation, tenant.products)
    signed = envelope(c, b, origin: origin)
    token = bearer(jwt, c.identity, "mixer.build.attest")

    start_http_api!(c, port, c.spki)

    assert {:ok, %{origin: ^origin, public_spki_der: spki}} = LocalAttestation.configuration()
    assert spki == c.spki
    assert_login!(AttestationRepo, @writer)
    assert writer_count() == 1

    assert_http(401, "unauthenticated", post(port, c.selection, signed, nil))

    assert_http(
      403,
      "permission_denied",
      post(port, c.selection, signed, bearer(jwt, c.identity, "mixer.build.read"))
    )

    assert_http(
      404,
      "not_found",
      post(port, tenant.selection, envelope(c, tenant, origin: origin), token)
    )

    assert_http(
      404,
      "not_found",
      post(port, %{c.selection | source_sha256: String.duplicate("0", 64)}, signed, token)
    )

    assert_http(
      400,
      "invalid_request",
      post(port, %{c.selection | platform: "android"}, signed, token)
    )

    assert_http(
      415,
      "unsupported_media_type",
      post(port, c.selection, signed, token, "application/json; charset=utf-8")
    )

    assert_http(422, "artifact_invalid", post(port, c.selection, stale, token))

    assert_http(
      422,
      "artifact_invalid",
      post(port, c.selection, :binary.copy(" ", 16_384), token)
    )

    assert_http(
      413,
      "payload_too_large",
      post(port, c.selection, :binary.copy(" ", 16_385), token)
    )

    assert stored(prior) == []
    assert stored(tenant) == []
    assert stored(b) == []
    assert_http(201, "attached", post(port, c.selection, signed, token))
    assert_http(200, "duplicate", post(port, c.selection, signed, token))

    stop_http_api!(port)
    {new_spki, new_key} = keypair()
    start_http_api!(c, port, new_spki)
    assert_login!(AttestationRepo, @writer)
    changed = envelope(%{c | spki: new_spki, key: new_key}, b, origin: origin)
    assert_http(409, "immutable_conflict", post(port, c.selection, changed, token))

    stop_http_api!(port)
    start_http_api!(c, port, nil)
    assert LocalAttestation.configuration() == :disabled
    assert Process.whereis(AttestationRepo) == nil
    assert writer_count() == 0
    assert_http(503, "authorization_unavailable", post(port, c.selection, signed, token))

    assert stored(b) == [[5, 2, b.operation, @binding, sha(c.spki), origin, signed]]
    assert stored(tenant) == []

    assert sql("SELECT revision,journal FROM public.mixer_builds WHERE id=$1", [b.id]).rows ==
             [[5, b.journal]]

    [[row_id, digest, size]] =
      sql(
        "SELECT build_record_id::text,encode(sha256(envelope),'hex'),octet_length(envelope) FROM #{@table} WHERE build_record_id=$1",
        [b.id]
      ).rows

    assert row_id == Ecto.UUID.load!(b.id)
    assert digest == sha(signed)
    assert size == byte_size(signed)
    stop_http_api!(port)

    IO.puts(
      "W12_L05_ATTESTATION_HTTP " <>
        Jason.encode!(%{
          build_record_id: row_id,
          worker_operation_id: b.operation,
          envelope_sha256: digest,
          envelope_bytes: size,
          http_port: port
        })
    )
  end

  defp start_bearer_fixture!(identity) do
    fixture = start_supervised!(TLSFixture)
    authority = GenServer.call(fixture, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "attestation-http-fixture", "alg" => "RS256", "use" => "sig"})

    TLSFixture.configure(fixture, {:body, Jason.encode!(%{"keys" => [public]})})

    profile =
      identity
      |> Map.take([:profile_id, :profile_version, :issuer, :client_id, :identity_class])
      |> Map.merge(%{audience: "mixer-attestation-http-fixture", enabled: true})

    entry = %{
      profile: profile,
      jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
      transport: :hosted_https
    }

    opts = [
      manifest: [entry],
      generation: 1,
      binding: identity.profile_id,
      ca_roots: [authority.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      fixture: Map.take(authority, [:ip, :port])
    ]

    start_supervised!(%{
      id: KeyOwnerSupervisor,
      start: {KeyOwnerSupervisor, :start_fixture, [opts]}
    })

    key
  end

  defp bearer(key, identity, scope) do
    claims = %{
      "iss" => identity.issuer,
      "aud" => "mixer-attestation-http-fixture",
      "sub" => identity.subject,
      "client_id" => identity.client_id,
      "iat" => identity.issued_at,
      "exp" => identity.expires_at,
      "jti" => identity.credential_ref,
      "scope" => scope
    }

    JOSE.JWS.sign(key, Jason.encode!(claims), %{
      "alg" => "RS256",
      "typ" => "at+jwt",
      "kid" => "attestation-http-fixture"
    })
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  defp start_http_api!(c, port, spki) do
    env = %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_PROCESSOR_PROFILE" => "builds_v1",
      "MIXER_DATABASE_HOST" => "db.fixture.invalid",
      "MIXER_DATABASE_NAME" => @database,
      "MIXER_DATABASE_USER" => @reader,
      "MIXER_DATABASE_PASSWORD" => "synthetic-reader",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-http-fixture-", 4),
      "MIXER_NATIVE_RETAINED_ROOT" => c.root,
      "MIXER_HTTP_PORT" => Integer.to_string(port)
    }

    writer_env =
      if spki,
        do: %{
          "MIXER_LOCAL_NATIVE_ATTESTATION_PASSWORD" => "synthetic-writer",
          "MIXER_LOCAL_NATIVE_ATTESTATION_PUBLIC_SPKI_BASE64" => Base.encode64(spki)
        },
        else: %{}

    hosted = RuntimeConfig.load!(env)

    repo =
      hosted.repo
      |> Keyword.drop([:hostname, :port])
      |> Keyword.merge(c.repo_opts)
      |> Keyword.put(:ssl, false)

    hosted = LocalAttestation.configure!(writer_env, %{hosted | repo: repo}, :disabled)
    endpoint = Keyword.merge(Application.fetch_env!(:mixer_hosted, Endpoint), hosted.endpoint)

    for {name, value} <- [
          {:startup, {hosted, :disabled}},
          {:role, hosted.role},
          {:identity_startup, hosted.identity_startup},
          {Repo, hosted.repo},
          {Oban, hosted.oban},
          {Endpoint, endpoint}
        ],
        do: put_config(name, value)

    on_exit(fn ->
      if Process.whereis(MixerHosted.Supervisor), do: stop_http_api!(port)
    end)

    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    assert Endpoint.server_info(:http) == {:ok, {{127, 0, 0, 1}, port}}
  end

  defp stop_http_api!(port) do
    assert :ok = Application.stop(:mixer_hosted)
    assert Process.whereis(AttestationRepo) == nil
    assert {:error, :econnrefused} = :gen_tcp.connect({127, 0, 0, 1}, port, [], 1_000)
  end

  defp http_port! do
    {:ok, reservation} = :gen_tcp.listen(0, ip: {127, 0, 0, 1})
    {:ok, port} = :inet.port(reservation)
    :ok = :gen_tcp.close(reservation)
    port
  end

  defp post(port, selection, bytes, token, media \\ "application/json") do
    s = selection

    path =
      "/v3/orgs/#{s.organization_id}/projects/#{s.project_id}/apps/#{s.application_id}/builds/#{s.build_id}/#{s.platform}/native-development-attestation"

    query =
      URI.encode_query(
        Map.take(s, [:source_sha256, :toolchain_lock_sha256, :build_definition_sha256])
      )

    headers = [{"content-type", media}, {"content-length", Integer.to_string(byte_size(bytes))}]
    headers = if token, do: [{"authorization", "Bearer " <> token} | headers], else: headers
    Wire.http(%{http_port: port}, path <> "?" <> query, headers, "POST", bytes)
  end

  defp assert_http(status, value, result) do
    assert result.status == status
    assert Wire.response_header(result, "cache-control") == ["no-store"]
    assert Wire.response_header(result, "content-type") == ["application/json; charset=utf-8"]
    body = Jason.decode!(result.body)
    if status == 503, do: assert(Wire.response_header(result, "retry-after") == ["1"])

    case status do
      success when success in [200, 201] ->
        assert body == %{"status" => value}

      401 ->
        assert %{"error" => %{"code" => ^value}} = body
        assert Wire.response_header(result, "www-authenticate") == ["Bearer"]

      _ ->
        assert body == %{"error" => %{"code" => value}}
    end
  end

  defp assert_login!(repo, role) do
    assert %{rows: [[^role]]} =
             Ecto.Adapters.SQL.query!(repo, "SELECT session_user", [], log: false)
  end

  defp writer_count do
    [[count]] =
      sql("SELECT count(*) FROM pg_stat_activity WHERE datname=$1 AND usename=$2", [
        @database,
        @writer
      ]).rows

    count
  end

  defp write_private_file!(path, content) do
    File.open!(path, [:write, :exclusive], fn file ->
      File.chmod!(path, 0o600)
      IO.binwrite(file, content)
    end)
  end

  test "read/create scope, expired credential, viewer and foreign tenants cannot attach", c do
    b = completed!(c.selection)
    foreign_selection = %{c.selection | organization_id: "org-b"}
    foreign = completed!(foreign_selection)
    retain!(c.root, b.operation, b.products)
    retain!(c.root, foreign.operation, foreign.products)

    assert {:error, :permission_denied} =
             attach(
               %{
                 c
                 | identity: %{c.identity | scopes: ["mixer.build.read", "mixer.build.create"]}
               },
               envelope(c, b)
             )

    assert {:error, :unauthenticated} =
             attach(
               %{c | identity: %{c.identity | expires_at: c.identity.issued_at + 1}},
               envelope(c, b)
             )

    assert {:error, :permission_denied} =
             attach(%{c | identity: identity("viewer")}, envelope(c, b))

    assert {:error, :not_found} =
             attach(%{c | selection: foreign_selection}, envelope(c, foreign))

    assert {:error, :artifact_invalid} = attach(c, envelope(c, foreign))
    assert stored(b) == []
    assert stored(foreign) == []
  end

  test "rejects changed statements, malformed bytes, wrong key and independently pinned origin",
       c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)
    {other_spki, other_key} = keypair()

    for invalid <- [
          "{",
          envelope(c, b) <> "\n",
          envelope(%{c | spki: other_spki, key: other_key}, b),
          envelope(c, b, origin: "http://127.0.0.1:59710"),
          envelope(c, b, revision: 3),
          envelope(c, b, attempt: 2),
          envelope(c, b, operation: sha("different operation")),
          envelope(c, b, operation: nil),
          envelope(c, b, version: 1),
          envelope(c, b, artifacts: Enum.reverse(b.artifacts))
        ] do
      assert {:error, :artifact_invalid} = attach(c, invalid)
      assert stored(b) == []
    end

    assert {:error, :invalid_request} = attach(c, :bad)
    assert {:error, :invalid_request} = attach(c, :binary.copy("x", 16_385))

    assert {:error, :not_found} =
             attach(
               %{c | selection: %{c.selection | source_sha256: sha("foreign")}},
               envelope(c, b)
             )

    assert {:error, :invalid_request} =
             attach(%{c | selection: %{c.selection | platform: "android"}}, envelope(c, b))

    assert stored(b) == []
  end

  test "requires released admission and both exact parents under the settled operation", c do
    b = completed!(c.selection, held: true)
    envelope = envelope(c, b)
    retain!(c.root, sha("foreign operation"), b.products)
    assert {:error, :not_found} = attach(c, envelope)
    assert stored(b) == []

    sql(
      "UPDATE public.mixer_build_reservations SET held=false,terminal_event_id='done' WHERE build_record_id=$1",
      [b.id]
    )

    sql(
      "UPDATE public.mixer_build_coordinator_leases SET owner_id=NULL,expires_at=NULL WHERE build_record_id=$1",
      [b.id]
    )

    assert {:error, :artifact_invalid} = attach(c, envelope)

    [app, symbols, inventory] = b.products
    retain!(c.root, b.operation, [app, inventory])
    assert {:error, :artifact_invalid} = attach(c, envelope)
    assert stored(b) == []

    retain!(c.root, b.operation, [symbols])
    assert {:ok, :attached} = attach(c, envelope)
  end

  test "a newly trusted but different valid envelope cannot replace the attached bytes", c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)
    original = envelope(c, b)
    assert {:ok, :attached} = attach(c, original)

    {new_spki, new_key} = keypair()

    Application.put_env(:mixer_hosted, :native_development_attestation, %{
      origin: @origin,
      public_spki_der: new_spki
    })

    changed = envelope(%{c | spki: new_spki, key: new_key}, b)
    assert changed != original
    assert {:error, :immutable_conflict} = attach(c, changed)
    assert stored(b) == [[2, 1, b.operation, @binding, sha(c.spki), @origin, original]]
  end

  test "a changed admission epoch or revoked membership after the first committed snapshot denies attachment",
       c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)
    envelope = envelope(c, b)

    after_snapshot_commit(
      fn ->
        sql(
          "UPDATE public.mixer_build_coordinator_leases SET epoch=epoch+1 WHERE build_record_id=$1",
          [b.id]
        )
      end,
      fn ->
        assert {:error, :conflict} = attach(c, envelope)
      end
    )

    assert stored(b) == []

    try do
      after_snapshot_commit(
        fn ->
          sql("UPDATE public.mixer_authz_memberships SET active=false WHERE id='developer'")
        end,
        fn ->
          assert {:error, :not_found} = attach(c, envelope)
        end
      )

      assert stored(b) == []
    after
      sql("UPDATE public.mixer_authz_memberships SET active=true WHERE id='developer'")
    end
  end

  test "a replacement record under the same customer selection cannot inherit the attachment",
       c do
    original = completed!(c.selection)
    retain!(c.root, original.operation, original.products)
    signed = envelope(c, original)

    after_snapshot_commit(
      fn ->
        remove_build!(original)
        replacement = completed!(c.selection)
        retain!(c.root, replacement.operation, replacement.products)
        Process.put({__MODULE__, :replacement}, replacement)
      end,
      fn -> assert {:error, :conflict} = attach(c, signed) end
    )

    replacement = Process.delete({__MODULE__, :replacement})
    assert replacement.operation != original.operation
    assert replacement.artifacts == original.artifacts
    assert replacement.products == original.products
    assert replacement.journal == original.journal
    assert envelope(c, replacement, version: 1) == envelope(c, original, version: 1)
    assert stored(original) == []
    assert stored(replacement) == []

    assert {:error, :artifact_invalid} = attach(c, signed)
    assert {:error, :artifact_invalid} = attach(c, envelope(c, original, version: 1))
    assert stored(replacement) == []

    fresh = envelope(c, replacement)
    assert {:ok, :attached} = attach(c, fresh)
    assert {:ok, :duplicate} = attach(c, fresh)

    assert stored(replacement) == [
             [2, 1, replacement.operation, @binding, sha(c.spki), @origin, fresh]
           ]
  end

  defp remove_build!(build) do
    sql("DELETE FROM public.mixer_build_coordinator_leases WHERE build_record_id=$1", [build.id])
    sql("DELETE FROM public.mixer_build_reservations WHERE build_record_id=$1", [build.id])
    sql("DELETE FROM public.mixer_builds WHERE id=$1", [build.id])
  end

  test "losing the write context after SQL inserts rolls back the entire attachment", c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)

    sql("""
    CREATE FUNCTION public.fixture_invalidate_context() RETURNS trigger LANGUAGE plpgsql AS $fn$
    BEGIN
      PERFORM set_config('mixer.authz.transaction_marker','',true);
      RETURN NEW;
    END
    $fn$
    """)

    sql(
      "CREATE TRIGGER fixture_invalidate_context AFTER INSERT ON #{@table} FOR EACH ROW EXECUTE FUNCTION public.fixture_invalidate_context()"
    )

    try do
      assert {:error, :authorization_unavailable} = attach(c, envelope(c, b))
      assert stored(b) == []
    after
      sql("DROP TRIGGER fixture_invalidate_context ON #{@table}")
      sql("DROP FUNCTION public.fixture_invalidate_context()")
    end

    assert {:ok, :attached} = attach(c, envelope(c, b))
  end

  test "only the fixture writer can call the function and it has no relation privileges", c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)

    assert sql("SELECT has_function_privilege('attestation_fixture_reader',$1,'EXECUTE')", [
             @entry
           ]).rows ==
             [[false]]

    for sql_text <- [
          "SELECT * FROM #{@table}",
          "INSERT INTO #{@table} DEFAULT VALUES",
          "UPDATE #{@table} SET attempt=2",
          "DELETE FROM #{@table}",
          "SELECT * FROM public.mixer_builds",
          "SELECT * FROM public.mixer_build_reservations",
          "SELECT * FROM public.mixer_build_coordinator_leases"
        ] do
      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Ecto.Adapters.SQL.query(AttestationRepo, sql_text, [], log: false)
    end

    assert Ecto.Adapters.SQL.query!(
             AttestationRepo,
             "SELECT public.mixer_native_development_attestation_v1('x','x','x','x',NULL,NULL,NULL,NULL,NULL,NULL)",
             [],
             log: false
           ).rows == [[nil]]

    signed = envelope(c, b)

    for role <- [@reader, "PUBLIC"] do
      sql("GRANT EXECUTE ON FUNCTION #{@entry} TO #{role}")

      try do
        assert executes?(@writer)
        assert executes?(@reader)
        assert {:error, :authorization_unavailable} = attach(c, signed)
        assert stored(b) == []
      after
        sql("REVOKE EXECUTE ON FUNCTION #{@entry} FROM #{role}")
      end
    end

    sql("REVOKE EXECUTE ON FUNCTION #{@entry} FROM #{@writer}")

    try do
      refute executes?(@writer)
      assert {:error, :authorization_unavailable} = attach(c, signed)
      assert stored(b) == []
    after
      sql(AttestationSchema.fixture_grant_statement())
    end

    [[definition]] = sql("SELECT pg_get_functiondef($1::text::regprocedure)", [@entry]).rows

    assert {:ok, _} =
             Migration.transaction(fn ->
               for statement <- ["DROP FUNCTION #{@entry}", definition] do
                 Ecto.Adapters.SQL.query!(Migration, statement, [], log: false)
               end
             end)

    try do
      assert [[true]] =
               sql("SELECT proacl IS NULL FROM pg_proc WHERE oid=$1::text::regprocedure", [@entry]).rows

      assert executes?(@writer)
      assert executes?(@reader)
      assert {:error, :authorization_unavailable} = attach(c, signed)
      assert stored(b) == []
    after
      sql("REVOKE EXECUTE ON FUNCTION #{@entry} FROM PUBLIC")
      sql(AttestationSchema.fixture_grant_statement())
    end

    assert {:ok, :attached} = attach(c, signed)
  end

  test "admission requires the migration's exact owner row-level security policies" do
    read = "attestation_owner_read ON #{@table}"
    insert = "attestation_owner_insert ON #{@table}"
    extra = "attestation_veto ON #{@table}"
    owner = "attestation_fixture_owner"

    admit = fn ->
      AttestationRepo.transaction(fn -> AttestationSchema.admit!(AttestationRepo) end)
    end

    assert {:ok, :ok} = admit.()

    mutations = [
      {"DROP POLICY #{read}", "CREATE POLICY #{read} FOR SELECT TO #{owner} USING (true)"},
      {"DROP POLICY #{insert}",
       "CREATE POLICY #{insert} FOR INSERT TO #{owner} WITH CHECK (true)"},
      {"ALTER POLICY #{read} USING (false)", "ALTER POLICY #{read} USING (true)"},
      {"ALTER POLICY #{insert} WITH CHECK (false)", "ALTER POLICY #{insert} WITH CHECK (true)"},
      {"ALTER POLICY #{read} TO PUBLIC", "ALTER POLICY #{read} TO #{owner}"},
      {"CREATE POLICY #{extra} AS RESTRICTIVE FOR INSERT TO PUBLIC WITH CHECK (false)",
       "DROP POLICY #{extra}"}
    ]

    outcomes =
      for {change, restore} <- mutations do
        sql(change)

        try do
          {change, admit.()}
        after
          sql(restore)
        end
      end

    assert Enum.reject(outcomes, fn {_, result} ->
             result == {:ok, {:error, :authorization_unavailable}}
           end) == []

    assert {:ok, :ok} = admit.()
  end

  defp executes?(role) do
    [[result]] = sql("SELECT has_function_privilege($1,$2,'EXECUTE')", [role, @entry]).rows
    result
  end

  defp completed!(s, opts \\ []) do
    products = products()

    artifacts =
      Enum.map(products, fn {kind, bytes} ->
        %ArtifactRef{kind: kind, sha256: sha(bytes), size_bytes: byte_size(bytes)}
      end)

    spec =
      s
      |> Map.delete(:source_sha256)
      |> Map.merge(%{
        platform: :ios,
        source: %{kind: :revision, sha256: s.source_sha256, reference: "pinned"}
      })

    key = "request-" <> s.build_id

    {:ok, journal, queued} =
      Journal.new(spec, %{max_attempts: 2, timeout_ms: 1_000, retry_backoff_ms: 0}, key, 0)

    {journal, queued} = if opts[:retry], do: retry(journal, queued), else: {journal, queued}
    {:ok, ref} = Lifecycle.worker_ref(queued)
    {:ok, journal, _, :applied} = Journal.append(journal, "start", %{type: :start, ref: ref}, 10)

    result = %{outcome: :native_succeeded, artifacts: artifacts}

    {:ok, journal, _, :applied} =
      Journal.append(journal, "done", %{type: :completed, ref: ref, result: result}, 11)

    revision = length(journal["events"])
    uuid = Ecto.UUID.generate()
    id = Ecto.UUID.dump!(uuid)
    held = opts[:held] || false

    sql(
      """
      INSERT INTO public.mixer_builds
        (id,organization_id,project_id,application_id,build_id,platform,request_key,revision,journal,inserted_at,updated_at)
      VALUES ($1,$2,$3,$4,$5,'ios',$6,$7,$8,now(),now())
      """,
      [id, s.organization_id, s.project_id, s.application_id, s.build_id, key, revision, journal]
    )

    sql(
      "INSERT INTO public.mixer_build_capacities VALUES ($1,'ios',4,0) ON CONFLICT DO NOTHING",
      [s.organization_id]
    )

    sql(
      """
      INSERT INTO public.mixer_build_reservations VALUES ($1,$2,'ios',$3,$4,$5,CASE WHEN $5 THEN NULL ELSE 'done' END)
      """,
      [id, s.organization_id, ref.attempt, ref.fence, held]
    )

    sql(
      """
      INSERT INTO public.mixer_build_coordinator_leases VALUES
        ($1,CASE WHEN $2 THEN 'fixture-worker' END,1,CASE WHEN $2 THEN timezone('UTC',now()) END)
      """,
      [id, held]
    )

    %{
      id: id,
      journal: journal,
      revision: revision,
      attempt: ref.attempt,
      operation: Dispatch.operation_id(uuid, ref),
      products: products,
      artifacts: artifacts,
      selection: s
    }
  end

  defp retry(journal, queued) do
    {:ok, ref} = Lifecycle.worker_ref(queued)
    {:ok, journal, _, :applied} = Journal.append(journal, "first", %{type: :start, ref: ref}, 1)

    failure = %{
      outcome: :failed,
      class: :infrastructure,
      code: :worker_lost,
      diagnostic_sha256: sha("first")
    }

    {:ok, journal, _, :applied} =
      Journal.append(journal, "failed", %{type: :completed, ref: ref, result: failure}, 2)

    {:ok, journal, queued, :applied} = Journal.append(journal, "retry", %{type: :retry}, 3)
    {journal, queued}
  end

  defp products do
    archive = fn kind ->
      header = Jason.encode!(%{version: 1, kind: Atom.to_string(kind), binding: @binding})
      {kind, <<"MXNATIVE1\n", byte_size(header)::64, header::binary, "archive">>}
    end

    app = archive.(:unsigned_native_binary)
    symbols = archive.(:debug_symbols)

    parent = fn {kind, bytes} ->
      %{kind: Atom.to_string(kind), sha256: sha(bytes), sizeBytes: byte_size(bytes)}
    end

    inventory =
      Jason.encode!(%{
        kind: "resource_inventory",
        version: 1,
        parentApp: parent.(app),
        parentSymbols: parent.(symbols),
        bindingSHA256: @binding
      })

    [app, symbols, {:resource_inventory, inventory}]
  end

  defp retain!(root, operation, products) do
    store = Path.join([root, operation, "native"])
    File.mkdir_p!(store)

    for {_kind, bytes} <- products do
      path = Path.join(store, sha(bytes))
      File.write!(path, bytes, [:exclusive])
      File.chmod!(path, 0o444)
    end
  end

  defp envelope(c, b, opts \\ []) do
    s = b.selection
    version = Keyword.get(opts, :version, 2)
    profile = "mixer.native-build.ios-simulator.development.v#{version}"

    provenance = [
      journalRevision: Keyword.get(opts, :revision, b.revision),
      attempt: Keyword.get(opts, :attempt, b.attempt),
      nativeBindingSha256: @binding
    ]

    operation = Keyword.get(opts, :operation, b.operation)

    provenance =
      if version == 2 and is_binary(operation),
        do: provenance ++ [workerOperationId: operation],
        else: provenance

    statement =
      Jason.OrderedObject.new(
        profile: profile,
        origin: Keyword.get(opts, :origin, @origin),
        keyId: sha(c.spki),
        selection:
          Jason.OrderedObject.new(
            organizationId: s.organization_id,
            projectId: s.project_id,
            applicationId: s.application_id,
            buildId: s.build_id,
            platform: s.platform,
            sourceSha256: s.source_sha256,
            toolchainLockSha256: s.toolchain_lock_sha256,
            buildDefinitionSha256: s.build_definition_sha256
          ),
        provenance: Jason.OrderedObject.new(provenance),
        subjects:
          Enum.map(Keyword.get(opts, :artifacts, b.artifacts), fn a ->
            Jason.OrderedObject.new(
              kind: Atom.to_string(a.kind),
              sha256: a.sha256,
              sizeBytes: a.size_bytes
            )
          end)
      )
      |> Jason.encode!()

    sig = :crypto.sign(:eddsa, :none, profile <> <<0>> <> statement, [c.key, :ed25519])
    ~s({"statement":#{statement},"signature":"#{Base.encode64(sig)}"})
  end

  defp keypair do
    {pub, priv} = :crypto.generate_key(:eddsa, :ed25519)
    {Base.decode16!("302A300506032B6570032100") <> pub, priv}
  end

  defp sha(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  defp attach(c, envelope),
    do: CustomerBuilds.attach_native_development_attestation(c.identity, c.selection, envelope)

  defp stored(b) do
    sql(
      """
      SELECT journal_revision,attempt,worker_operation_id,native_binding_sha256,signer_key_sha256,
        signing_origin,envelope FROM #{@table} WHERE build_record_id=$1
      """,
      [b.id]
    ).rows
  end

  defp after_snapshot_commit(change, attach) do
    tag = make_ref()
    key = {__MODULE__, tag}
    owner = self()
    event = AttestationRepo.config()[:telemetry_prefix] ++ [:query]

    handler = fn _, _, metadata, _ ->
      if self() == owner and metadata.query == "commit" and !Process.get(key) do
        change.()
        Process.put(key, true)
      end
    end

    :ok = :telemetry.attach(tag, event, handler, nil)

    try do
      attach.()
      assert Process.get(key)
    after
      :telemetry.detach(tag)
      Process.delete(key)
    end
  end

  defp identity(subject \\ "developer") do
    now = System.system_time(:second)

    %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://fixture.example",
      subject: subject,
      client_id: "fixture",
      credential_ref: subject,
      issued_at: now - 20,
      expires_at: now + 300,
      identity_class: :human,
      scopes: ["mixer.build.attest"]
    }
  end

  defp seed_identity! do
    sql(
      "INSERT INTO public.mixer_authz_profiles (id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https://fixture.example','fixture','human',true)"
    )

    for org <- ["org-a", "org-b"] do
      sql("INSERT INTO public.mixer_authz_organizations VALUES ($1,true)", [org])
      sql("INSERT INTO public.mixer_authz_projects VALUES ($1,'project',true)", [org])
      sql("INSERT INTO public.mixer_authz_applications VALUES ($1,'project','app',true)", [org])
      sql("INSERT INTO public.mixer_authz_organization_heads VALUES ($1,1)", [org])
      sql("INSERT INTO public.mixer_authz_project_heads VALUES ($1,'project',1)", [org])
    end

    for role <- ["developer", "viewer"] do
      sql("INSERT INTO public.mixer_authz_principals VALUES ($1,'human',true,0,1)", [role])

      sql(
        "INSERT INTO public.mixer_authz_bindings (profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,$1,'human',$1,true)",
        [role]
      )

      sql("INSERT INTO public.mixer_authz_families VALUES ($1,'profile',1,$1,true,0,NULL,1)", [
        role
      ])

      sql(
        "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,$1,$1,$1,true,0,NULL,1)",
        [role]
      )

      sql(
        "INSERT INTO public.mixer_authz_memberships VALUES ($1,$1,'org-a','project','exact_project',$1,true,0,NULL,1)",
        [role]
      )
    end
  end

  defp put_config(name, value) do
    prior = Application.fetch_env(:mixer_hosted, name)
    Application.put_env(:mixer_hosted, name, value)

    on_exit(fn ->
      case prior do
        {:ok, config} -> Application.put_env(:mixer_hosted, name, config)
        :error -> Application.delete_env(:mixer_hosted, name)
      end
    end)
  end

  defp sql(statement, args \\ []),
    do: Ecto.Adapters.SQL.query!(Admin, statement, args, log: false)
end
