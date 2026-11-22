# Fixture-only extensions to the pinned ordinary signed-in HTTP case.
defp v74_endpoint!(c) do
  port = String.to_integer(System.fetch_env!("L07_V74_API_PORT"))
  endpoint = Keyword.put(c.hosted.endpoint, :http,
    ip: {127, 0, 0, 1}, port: port, http_2_options: [enabled: false])
  put_in(c, [:hosted, Access.key(:endpoint)], endpoint)
end

defp v74_writer! do
  alias MixerHosted.CustomerBuilds.AttestationSchema

  writer = "mixer_native_attestation_writer"
  password = Base.encode16(:crypto.strong_rand_bytes(32), case: :lower)
  DB.q!(Admin, "CREATE ROLE #{writer} LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS PASSWORD '#{password}'")
  [path] = Path.wildcard("priv/local_native_attestation/20261120000020_*.exs")
  [{module, _}] = Code.require_file(path)
  assert :ok = Ecto.Migrator.up(Migration, 20_261_120_000_020, module, log: false)

  DB.q!(Migration, "GRANT USAGE ON SCHEMA public TO #{writer}")

  for name <- ~w(profiles principals bindings families credentials organizations projects
                 applications environments organization_heads project_heads memberships),
      do: DB.q!(Migration, "GRANT SELECT ON public.mixer_authz_#{name} TO #{writer}")

  for name <- ~w(profiles principals families credentials organization_heads project_heads),
      do: DB.q!(Migration, "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO #{writer}")

  DB.q!(Migration, AttestationSchema.fixture_grant_statement())
  password
end

defp v74_check_browser!(c, cookie) do
  response = http(c, "/auth/session", headers(cookie))
  pair25_publish!("v74.browser-before-writer", %{
    retainedSessionHTTP: response.status,
    authenticated: response.status == 200 and Jason.decode!(response.body)["state"] == "authenticated"
  })
end

defp v74_wait!(c, scope, build, deadline) do
  assert System.monotonic_time(:millisecond) < deadline

  cond do
    File.regular?(pair25_path("api.done")) ->
      :ok

    File.regular?(pair25_path("v74.enroll")) and not File.regular?(pair25_path("v74.attestation-ready")) ->
      v74_enroll!(c, scope, build)
      v74_wait!(c, scope, build, deadline)

    File.regular?(pair25_path("v74.refresh")) and not File.regular?(pair25_path("v74.readback-auth")) ->
      {cookie, csrf} = login(c)
      pair25_publish!("v74.readback-auth", %{cookie: cookie, csrf: csrf})
      v74_wait!(c, scope, build, deadline)

    true ->
      Process.sleep(50)
      v74_wait!(c, scope, build, deadline)
  end
end

defp v74_enroll!(c, scope, build) do
  alias MixerHosted.CustomerBuilds.{AttestationRepo, LocalAttestation}
  alias MixerHostedWeb.Endpoint

  spki = File.read!(pair25_path("v74.enroll"))
  port = c.http_port
  assert :ok = Application.stop(:mixer_hosted)
  assert Process.whereis(MixerHosted.Supervisor) == nil
  assert {:error, :econnrefused} = :gen_tcp.connect({127, 0, 0, 1}, port, [], 1_000)

  # The browser catalog admits writer grants only on the attestation-enabled listener.
  password = v74_writer!()
  hosted = LocalAttestation.configure!(
    %{
      "MIXER_LOCAL_NATIVE_ATTESTATION_PASSWORD" => password,
      "MIXER_LOCAL_NATIVE_ATTESTATION_PUBLIC_SPKI_BASE64" => spki
    },
    c.hosted,
    :disabled
  )

  c = start!(%{c | hosted: hosted})
  assert {:ok, {{127, 0, 0, 1}, ^port}} = Endpoint.server_info(:http)
  browser_storage_ready = RuntimeOwner.status().phase == :storage_ready
  assert {:ok, %{origin: origin, public_spki_der: der}} = LocalAttestation.configuration()
  assert origin == "http://127.0.0.1:#{port}" and Base.encode64(der) == spki
  assert %{rows: [["mixer_native_attestation_writer"]]} =
    DB.q!(AttestationRepo, "SELECT session_user")

  cookie = if browser_storage_ready, do: elem(login(c), 0)
  token = v74_bearer(c)
  pin_query = URI.encode_query(Map.take(build, [
    :source_sha256, :toolchain_lock_sha256, :build_definition_sha256
  ]))
  path =
    "/v3/orgs/#{scope.organization_id}/projects/#{scope.project_id}/apps/#{scope.application_id}" <>
      "/builds/v74-fixture-missing/ios/native-development-attestation?" <> pin_query

  # The current owner can reach the restricted lookup for an absent build.
  # A stock request with the same subject but missing scope must fail earlier.
  probe = fn bearer ->
    http(c, path, [
      {"authorization", "Bearer " <> bearer},
      {"content-type", "application/json"},
      {"content-length", "2"}
    ], "POST", "{}")
  end

  assert %{status: 404} = probe.(token)
  assert %{status: 403} = probe.(v74_bearer(c, "mixer.build.read"))
  assert %{rows: [[0]]} = DB.q!(Admin, "SELECT count(*) FROM public.mixer_native_development_attestations")

  if cookie && !System.get_env("L07_V74_PREFLIGHT") do
    directory = System.fetch_env!("L07_V74_CREDENTIALS")
    for {name, secret} <- [{"session", cookie}, {"bearer", token}] do
      path = Path.join(directory, name)
      File.write!(path, secret <> "\n", [:exclusive])
      File.chmod!(path, 0o600)
    end
  end

  lost_ack_control =
    if System.get_env("L07_V74_PREFLIGHT") == "1" and System.get_env("L07_V74_LOST_ACK") == "1",
      do: v74_lost_ack_control!(port, origin, path, token)

  pair25_publish!("v74.attestation-ready", %{
    origin: origin, spkiSHA256: sha256(der), role: "mixer_native_attestation_writer",
    missingBuildHTTP: 404, missingScopeHTTP: 403, rows: 0,
    browserStorageReady: browser_storage_ready, freshBrowserSession: is_binary(cookie),
    lostAckControl: lost_ack_control
  })
end

defp v74_lost_ack_control!(port, origin, target, token) do
  pair25_publish!("v74.lost-ack-arm.json", %{origin: origin, target: target})
  # A successful controller response to the exact stock route is required to
  # consume the arm. An unauthorized POST must still produce an HTTP response.
  assert <<"HTTP/1.1 401 ", _::binary>> = v74_raw_attach!(port, target, [])
  authorization = ["Authorization: Bearer ", token, "\r\n"]
  wrong_target = String.replace(target, "v74-fixture-missing/", "v74-fixture-missing-other/")
  assert <<"HTTP/1.1 404 ", _::binary>> = v74_raw_attach!(port, wrong_target, authorization)
  assert File.regular?(pair25_path("v74.lost-ack-arm.json"))
  assert <<>> = v74_raw_attach!(port, target, authorization)
  pair25_await_burst!("v74.lost-ack-result.json", System.monotonic_time(:millisecond) + 2_000)
  refute File.exists?(pair25_path("v74.lost-ack-arm.json"))
  assert File.regular?(pair25_path("v74.lost-ack-consumed.json"))

  assert <<"HTTP/1.1 404 ", _::binary>> =
    v74_raw_attach!(port, target, authorization)

  assert %{rows: [[0]]} = DB.q!(Admin, "SELECT count(*) FROM public.mixer_native_development_attestations")
  assert %{"origin" => ^origin, "target" => ^target, "selectedHTTP" => 404,
           "adapterWriteState" => "unsent", "writeShutdown" => true} = evidence =
    "v74.lost-ack-result.json" |> pair25_path() |> File.read!() |> Jason.decode!()

  Map.drop(evidence, ["origin", "target"])
  |> Map.merge(%{unauthenticatedHTTP: 401, responseBytes: 0, wrongTargetHTTP: 404, retryHTTP: 404, rows: 0})
end

defp v74_raw_attach!(port, target, authorization) do
  {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 2_000)

  try do
    :ok = :gen_tcp.send(socket, [
      "POST ", target, " HTTP/1.1\r\nHost: 127.0.0.1:", Integer.to_string(port),
      "\r\nConnection: close\r\nContent-Type: application/json\r\nContent-Length: 2\r\n",
      authorization, "\r\n{}"
    ])
    deadline = System.monotonic_time(:millisecond) + 4_000
    collect = fn again, acc ->
      assert byte_size(acc) <= 8_192
      remaining = deadline - System.monotonic_time(:millisecond)
      assert remaining > 0
      case :gen_tcp.recv(socket, 0, remaining) do
        {:ok, bytes} -> again.(again, acc <> bytes)
        {:error, :closed} -> acc
        {:error, reason} -> flunk("unexpected lost-ack control transport: #{inspect(reason)}")
      end
    end
    collect.(collect, <<>>)
  after
    :gen_tcp.close(socket)
  end
end

defp v74_bearer(c, scope \\ "mixer.build.attest") do
  # The same synthetic issuer and subject as login(c), with a fresh JWT ID.
  %{key: key, pair25_subject: "subject-1"} = :sys.get_state(c.provider)
  now = System.system_time(:second)
  reference = MixerHosted.BrowserAuth.Protocol.random_token()
  # The fixture issuer provisions a current credential for the same synthetic
  # principal as the browser login. Stock request authorization checks both rows.
  DB.q!(Admin, """
  INSERT INTO public.mixer_authz_families
    (id,profile_id,profile_version,principal_id,active,not_before,expires_at,revision)
    VALUES ($1,$2,$3,'person-1',true,0,NULL,1)
  """, [reference, c.config.profile_id, c.config.profile_version])
  DB.q!(Admin, """
  INSERT INTO public.mixer_authz_credentials
    (profile_id,profile_version,reference,principal_id,family_id,active,not_before,expires_at,revision)
    VALUES ($1,$2,$3,'person-1',$3,true,0,NULL,1)
  """, [c.config.profile_id, c.config.profile_version, reference])

  claims = %{
    "iss" => c.config.issuer, "aud" => c.config.api_audience, "sub" => "subject-1",
    "client_id" => c.config.client_id, "iat" => now - 1, "exp" => now + 600,
    "jti" => reference, "scope" => scope
  }

  JOSE.JWS.sign(key, Jason.encode!(claims), %{"alg" => "RS256", "typ" => "at+jwt", "kid" => "key1"})
  |> JOSE.JWS.compact()
  |> elem(1)
end
