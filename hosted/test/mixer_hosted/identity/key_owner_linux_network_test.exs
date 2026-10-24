defmodule MixerHosted.Identity.KeyOwnerLinuxNetworkTest do
  use ExUnit.Case, async: false

  @moduletag skip:
               not (:os.type() == {:unix, :linux} and
                      System.get_env("MIXER_ISOLATED_NETNS") == "1")
  alias MixerHosted.Identity.{DNSFixture, JWKSTransport, TLSFixture, TrustSnapshot}

  @profile %{
    profile_id: "isolated-linux-origin",
    profile_version: 1,
    issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api",
    client_id: "reviewed-client",
    identity_class: :human,
    enabled: true
  }
  @entry %{
    profile: @profile,
    jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
    transport: :hosted_https
  }
  # This file is run only by the network-none disposable Linux collector whose
  # private namespace owns8.8.8.8 on lo:1. It grants no product test exception.
  test "K03 production resolver/classifier pins public peer despite rebinding; private sink remains untouched" do
    assert :os.type() == {:unix, :linux}
    assert System.get_env("MIXER_ISOLATED_NETNS") == "1"
    public = start_supervised!({TLSFixture, [ip: {8, 8, 8, 8}, port: 443]}, id: :public)
    sink = start_supervised!({TLSFixture, [ip: {127, 0, 0, 1}, port: 443]}, id: :sink)
    dns = start_supervised!(DNSFixture)
    DNSFixture.configure(dns, {:rebind, [{8, 8, 8, 8}]})
    a = GenServer.call(public, :authority)

    key =
      JOSE.JWK.generate_key({:rsa, 2048})
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "network-key", "alg" => "RS256", "use" => "sig"})

    body = Jason.encode!(%{"keys" => [key]})
    TLSFixture.configure(public, {:body, body})
    config = %{ca_roots: [a.ca], resolvers: [{{127, 0, 0, 1}, DNSFixture.info(dns).port}]}

    assert {:ok, c} =
             JWKSTransport.fetch(@entry, System.monotonic_time(:millisecond) + 2_000, config, nil)

    assert c.peer == {8, 8, 8, 8}
    assert c.body == body
    assert {:ok, _} = TrustSnapshot.new(@profile, c.body, c.fetched_at, c.fresh_until)
    assert length(DNSFixture.info(dns).queries) == 2
    assert TLSFixture.info(public).accepted == 1
    assert TLSFixture.info(sink).accepted == 0
    # The same configured endpoint now resolves to loopback, so a new flight
    # rejects before a TCP/TLS connection. There is no destination fallback.
    assert {:error, :dns_rejected} =
             JWKSTransport.fetch(@entry, System.monotonic_time(:millisecond) + 2_000, config, nil)

    assert TLSFixture.info(sink).accepted == 0

    File.write!(
      Path.expand(
        "../../../../verification/hosted-key-owner-implementation/production-DNS-rebinding.json",
        __DIR__
      ),
      Jason.encode!(
        %{
          initialQueries: 2,
          authenticatedPeer: "8.8.8.8:443",
          publicConnections: 1,
          forbiddenSinkConnections: 0,
          newPrivateAnswerRejectedBeforeConnect: true,
          namespace: "disposable network-none Linux lo:1; no product resolver or loopback bypass"
        },
        pretty: true
      )
    )
  end
end
