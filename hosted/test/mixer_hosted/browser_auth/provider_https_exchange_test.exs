defmodule MixerHosted.BrowserAuth.ProviderHTTPSExchangeTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Config, ProviderHTTPS, ProviderTLSFixture}
  alias MixerHosted.Identity.{DNSResolver, GlobalAddress, StartupConfig}
  @moduletag :browser_provider_https_exchange_verified
  @secret "fixture secret:+&%é"
  @code "fixture code+&=é"
  @verifier String.duplicate("v", 43)
  @unavailable {:error, :provider_unavailable}

  setup do
    fixture = start_supervised!(ProviderTLSFixture)
    authority = GenServer.call(fixture, :authority)
    {config, identity} = configuration("jwks.fixture.invalid")
    expected = %{basic: "Basic " <> Base.encode64("client+%3A%2B%26%25%C3%A9:fixture+secret%3A%2B%26%25%C3%A9"),
      body: "grant_type=authorization_code&code=fixture+code%2B%26%3D%C3%A9&redirect_uri=https%3A%2F%2Fconsole.example.invalid%2Fauth%2Fcallback&code_verifier=" <> @verifier}
    :ok = ProviderTLSFixture.configure(fixture, {{:body, "{}"}, expected})
    {:ok, fixture: fixture, authority: authority, config: config, identity: identity, expected: expected}
  end

  test "browser_provider_https_exchange_verified: actual Mint TLS complete POST and bounded JSON", c do
    raw = ~s({"id_token":"synthetic-fixture-only"})
    configure(c, {:body, raw})
    accepted = exchange(c, 3000) == {:ok, raw}
    assert accepted
    info = closed(c)
    valid = length(info.requests) == 1 and hd(info.requests).semantics and
      hd(info.requests).tls[:sni_hostname] == ~c"jwks.fixture.invalid" and
      hd(info.requests).tls[:protocol] in [:"tlsv1.2", :"tlsv1.3"]
    assert valid
    assert info.closed == 1
  end

  test "exact 16384 bytes succeeds", c do
    raw = json(16384)
    configure(c, {:body, raw})
    accepted = exchange(c, 3000) == {:ok, raw}
    assert accepted
    closed(c)
  end

  test "unknown configuration and raw material shapes fail before connection", c do
    for config <- [nil, %Config{}, Map.put(c.config, :transport, :caller_selected),
      %{c.config | token_endpoint: "https://jwks.fixture.invalid:444/token"},
      %{c.config | redirect_uri: "https://other.invalid/auth/callback"}] do
      rejected = ProviderHTTPS.post_fixture(config, @secret, @code, @verifier, deadline(1000), c.identity,
        c.authority.port, [c.authority.ca]) == @unavailable
      assert rejected
    end
    for secret <- [nil, %{}, "", String.duplicate("x", 4097)] do
      rejected = ProviderHTTPS.post_fixture(c.config, secret, @code, @verifier, deadline(1000), c.identity,
        c.authority.port, [c.authority.ca]) == @unavailable
      assert rejected
    end
    assert ProviderTLSFixture.info(c.fixture).accepted == 0
  end

  test "fixture-only exact-reference lookup rejects unknown and mismatched references", c do
    assert fixture_secret("secret://unknown") == @unavailable
    assert fixture_secret(c.config.session_vault_ref) == @unavailable
    known = fixture_secret(c.config.client_credential_ref)
    known_reference = known == {:ok, @secret}
    assert known_reference
  end

  test "wrong CA rejects authenticated TLS", c do
    other = start_supervised!({ProviderTLSFixture, []}, id: :other_ca)
    authority = GenServer.call(other, :authority)
    rejected = exchange(c, 3000, [authority.ca]) == @unavailable
    assert rejected
    info = closed(c, false)
    assert info.requests == []
  end

  test "wrong hostname rejects authenticated TLS", c do
    {config, identity} = configuration("wrong.fixture.invalid")
    rejected = exchange(%{c | config: config, identity: identity}, 3000) == @unavailable
    assert rejected
    info = closed(c, false)
    assert info.requests == []
  end

  test "redirect is rejected at status before body", c do
    configure(c, {:raw, "HTTP/1.1 302 Found\r\nLocation: https://elsewhere.invalid/token\r\nContent-Length: 999999\r\n\r\n"})
    rejected = exchange(c, 2000) == @unavailable
    assert rejected
    closed(c)
  end

  test "non200 is rejected", c do
    configure(c, {:raw, "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n"})
    rejected = exchange(c, 2000) == @unavailable
    assert rejected
    closed(c)
  end

  test "compression is rejected before reading entity", c do
    configure(c, {:raw, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Encoding: gzip\r\nContent-Length: 100\r\n\r\n"})
    rejected = exchange(c, 2000) == @unavailable
    assert rejected
    closed(c)
  end

  test "ambiguous framing is rejected before reading entity", c do
    configure(c, {:raw, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nContent-Length: 1\r\n\r\n"})
    rejected = exchange(c, 2000) == @unavailable
    assert rejected
    closed(c)
  end

  test "unsupported close-delimited framing is rejected", c do
    configure(c, {:raw, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"})
    rejected = exchange(c, 2000) == @unavailable
    assert rejected
    closed(c)
  end

  test "16385 Content-Length is rejected before a stalled body", c do
    configure(c, {:raw, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 16385\r\n\r\n"})
    before = System.monotonic_time(:millisecond)
    rejected = exchange(c, 2500) == @unavailable
    assert rejected
    assert System.monotonic_time(:millisecond) - before < 2000
    closed(c)
  end

  test "streamed chunk overflow rejects 16385 before final byte is sent", c do
    raw = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n4000\r\n" <>
      json(16384) <> "\r\n1\r\n"
    configure(c, {:raw, raw})
    before = System.monotonic_time(:millisecond)
    rejected = exchange(c, 2500) == @unavailable
    assert rejected
    assert System.monotonic_time(:millisecond) - before < 2000
    closed(c)
  end

  test "bounded chunked JSON succeeds", c do
    configure(c, {:raw, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n\r\n"})
    accepted = exchange(c, 3000) == {:ok, "{}"}
    assert accepted
    closed(c)
  end

  test "stall consumes original deadline and closes owned socket", c do
    configure(c, :stall)
    before = System.monotonic_time(:millisecond)
    rejected = exchange(c, 800) == @unavailable
    assert rejected
    assert System.monotonic_time(:millisecond) - before < 2000
    closed(c)
  end

  test "drip cannot replenish original deadline", c do
    raw = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
    configure(c, {:drip, :binary.bin_to_list(raw) |> Enum.map(&<<&1>>), 20})
    before = System.monotonic_time(:millisecond)
    rejected = exchange(c, 800) == @unavailable
    assert rejected
    assert System.monotonic_time(:millisecond) - before < 2000
    closed(c)
  end

  test "expired deadline performs no socket IO", c do
    rejected = ProviderHTTPS.post_fixture(c.config, @secret, @code, @verifier, deadline(-1), c.identity,
      c.authority.port, [c.authority.ca]) == @unavailable
    assert rejected
    assert ProviderTLSFixture.info(c.fixture).accepted == 0
  end

  test "queued invocation preserves original absolute deadline", c do
    original = deadline(50)
    task = Task.async(fn ->
      receive do
        :go -> ProviderHTTPS.post_fixture(c.config, @secret, @code, @verifier, original, c.identity,
          c.authority.port, [c.authority.ca])
      after
        1000 -> :fixture_queue_timeout
      end
    end)
    Process.sleep(80)
    send(task.pid, :go)
    assert Task.await(task, 2000) == @unavailable
    assert ProviderTLSFixture.info(c.fixture).accepted == 0
  end

  test "ordinary production DNS rejection remains closed without fixture bypass", c do
    refute GlobalAddress.global?({127, 0, 0, 1})
    refute GlobalAddress.global?({10, 0, 0, 1})
    assert DNSResolver.resolve("jwks.fixture.invalid", [], deadline(-1)) == {:error, :dns_rejected}
    rejected = ProviderHTTPS.post(c.config, @secret, @code, @verifier, deadline(-1), c.identity) == @unavailable
    assert rejected
    assert ProviderTLSFixture.info(c.fixture).accepted == 0
  end

  defp configure(c, response), do: ProviderTLSFixture.configure(c.fixture, {response, c.expected})
  defp deadline(ms), do: System.monotonic_time(:millisecond) + ms
  defp exchange(c, ms, roots \\ nil) do
    {:ok, secret} = fixture_secret(c.config.client_credential_ref)
    ProviderHTTPS.post_fixture(c.config, secret, @code, @verifier, deadline(ms), c.identity,
      c.authority.port, roots || [c.authority.ca])
  end
  defp fixture_secret("secret://mixer/oidc/client-v1"), do: {:ok, @secret}
  defp fixture_secret(_), do: @unavailable
  defp json(n), do: ~s({"p":") <> String.duplicate("a", n - 8) <> ~s("})
  defp closed(c, require_eof \\ true, tries \\ 300) do
    info = ProviderTLSFixture.info(c.fixture)
    cond do
      info.accepted == 1 and info.sockets == %{} and
          (not require_eof or info.closed == 1) -> info
      tries == 0 -> flunk("provider fixture did not observe owned connection retirement")
      true -> Process.sleep(10); closed(c, require_eof, tries - 1)
    end
  end

  defp configuration(host) do
    issuer = "https://" <> host <> "/tenant"
    profile = %{profile_id: "human-main", profile_version: 7, issuer: issuer,
      audience: "mixer-api", client_id: "client :+&%é", identity_class: :human, enabled: true}
    identity = %StartupConfig{mode: :configured, owner_options: [binding: "human-main", generation: 1,
      manifest: [%{profile: profile, jwks_endpoint: %{host: host, port: 443, path: "/keys"}, transport: :hosted_https}],
      resolvers: [{{127, 0, 0, 1}, 53}]]}
    object = %{"version" => 1, "public_origin" => "https://console.example.invalid", "profile_id" => "human-main",
      "profile_version" => 7, "issuer" => issuer, "client_id" => profile.client_id, "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://" <> host <> "/authorize", "token_endpoint" => "https://" <> host <> "/token",
      "id_token_jwks_endpoint" => "https://" <> host <> "/keys", "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic", "client_credential_ref" => "secret://mixer/oidc/client-v1",
      "session_vault_ref" => "vault://mixer/browser-session-v1", "scope" => "openid mixer.workspace.read",
      "response_mode" => "query", "response_iss_required" => true}
    {:ok, config} = Config.load(%{"MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)}, :api, identity)
    {config, identity}
  end
end
