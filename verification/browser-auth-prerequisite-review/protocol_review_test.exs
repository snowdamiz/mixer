defmodule MixerHosted.BrowserAuth.IndependentReviewTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{Config, Protocol}
  alias MixerHosted.Identity.StartupConfig

  @issuer "https://identity.review.invalid/tenant"
  @origin "https://console.review.invalid"
  @token Base.url_encode64(:binary.copy(<<17>>, 32), padding: false)
  @other Base.url_encode64(:binary.copy(<<23>>, 32), padding: false)

  defp object do
    %{
      "version" => 1, "public_origin" => @origin, "profile_id" => "review-human",
      "profile_version" => 3, "issuer" => @issuer, "client_id" => "review-client",
      "api_audience" => "review-api", "authorization_endpoint" => "https://identity.review.invalid/authorize",
      "token_endpoint" => "https://identity.review.invalid/token",
      "id_token_jwks_endpoint" => "https://identity.review.invalid/id-keys",
      "redirect_uri" => @origin <> "/auth/callback", "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://review/client", "session_vault_ref" => "vault://review/session",
      "scope" => "openid mixer.workspace.read", "response_mode" => "query", "response_iss_required" => true
    }
  end

  defp identity do
    %StartupConfig{mode: :configured, owner_options: [binding: "review-human", generation: 1, manifest: [
      %{profile: %{profile_id: "review-human", profile_version: 3, issuer: @issuer, audience: "review-api",
         client_id: "review-client", identity_class: :human, enabled: true},
        jwks_endpoint: %{host: "identity.review.invalid", port: 443, path: "/api-keys"}, transport: :hosted_https}
    ]]}
  end

  defp load(value, trust \\ identity()) do
    Config.load(%{"MIXER_BROWSER_AUTH_MODE" => "configured", "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(value)}, :api, trust)
  end

  defp config do
    {:ok, config} = load(object())
    config
  end

  defp query(fields \\ [{"code", "synthetic"}]) do
    URI.encode_query([{"state", @token}, {"iss", @issuer}] ++ fields)
  end

  defp headers do
    [{"Cookie", "__Host-mixer-session=" <> @token}, {"Origin", @origin}, {"X-Mixer-CSRF", @other}]
  end

  test "bound identity values cannot be independently swapped or weakly compared" do
    for {key, value} <- [{"profile_id", "different"}, {"profile_version", 3.0}, {"issuer", @issuer <> "/"}, {"client_id", "different"}, {"api_audience", "different"}] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, value))
    end
  end

  test "malformed trust owner options and duplicate manifest bindings fail closed" do
    original = identity()
    for options <- [nil, %{}, [:invalid], [{:binding, "review-human"} | original.owner_options], Keyword.put(original.owner_options, :manifest, original.owner_options[:manifest] ++ original.owner_options[:manifest])] do
      assert {:error, :invalid_configuration} = load(object(), %{original | owner_options: options})
    end
  end

  test "endpoint alias matrix rejects noncanonical paths hosts and credential destinations" do
    for key <- ~w(authorization_endpoint token_endpoint id_token_jwks_endpoint), value <- [
      "https://127.1/token", "https://0x7f000001/token", "https://user:private@identity.review.invalid/token",
      "https://identity.review.invalid/a%2fb", "https://identity.review.invalid/a\\b", "https://identity.review.invalid/a//b",
      "https://identity.review.invalid/./a", "https://identity.review.invalid/a/..", "https://identity.review.invalid:443/token",
      "https://IDENTITY.review.invalid/token", "https://identity.review.invalid./token", "https://identity.review.invalid/token?x=1"
    ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, value))
    end
  end

  test "closed JSON rejects escaped duplicates and arbitrary return or secret fields" do
    raw = Jason.encode!(object())
    duplicate = String.trim_trailing(raw, "}") <> ~s(,"client_\u0069d":"private"})
    assert {:error, :invalid_configuration} = Config.load(%{"MIXER_BROWSER_AUTH_MODE" => "configured", "MIXER_BROWSER_AUTH_CONFIG" => duplicate}, :api, identity())
    for key <- ~w(client_secret vault_key return_to redirect_url discovery_endpoint session_idle_seconds) do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, "private"))
    end
    refute inspect(config()) =~ "private"
    refute inspect(config()) =~ "secret://"
  end

  test "all canonical token trailing bits round trip while alias encodings reject" do
    for byte <- 0..255 do
      token = Base.url_encode64(:binary.copy(<<byte>>, 32), padding: false)
      assert Protocol.token?(token)
      refute Protocol.token?(token <> "=")
    end
    prefix = binary_part(@token, 0, 42)
    {:ok, raw} = Base.url_decode64(@token, padding: false)
    aliases = for last <- ~c"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_", candidate = prefix <> <<last>>,
      Base.url_decode64(candidate, padding: false) == {:ok, raw}, do: candidate
    assert length(aliases) == 4
    assert Enum.count(aliases, &Protocol.token?/1) == 1
  end

  test "generated authorization request has a closed exact query and independent PKCE derivation" do
    verifier = Protocol.random_token()
    {:ok, url} = Protocol.authorization_url(config(), %{state: @token, nonce: @other, verifier: verifier})
    uri = URI.parse(url)
    assert uri.scheme == "https" and uri.host == "identity.review.invalid" and uri.path == "/authorize"
    fields = URI.decode_query(uri.query)
    assert Enum.sort(Map.keys(fields)) == ~w(client_id code_challenge code_challenge_method nonce redirect_uri response_mode response_type scope state)
    assert fields["code_challenge"] == Base.url_encode64(:crypto.hash(:sha256, verifier), padding: false)
    assert fields["state"] == @token and fields["nonce"] == @other
    assert fields["response_type"] == "code" and fields["code_challenge_method"] == "S256"
    refute Map.has_key?(fields, "verifier")
  end

  test "provider errors retain validated state issuer while discarding all arbitrary provider metadata" do
    for fields <- [[{"error", "access_denied"}], [{"error", "private-text"}, {"error_description", "private-secret"}, {"error_uri", "https://private.invalid?token=secret"}]] do
      assert {:ok, %{state: @token, issuer: @issuer, outcome: {:error, :provider_rejected}}} = Protocol.parse_callback(config(), query(fields))
    end
    refute inspect(Protocol.parse_callback(config(), query([{"error", "private-secret"}]))) =~ "private-secret"
  end

  test "callback permutations preserve exact semantics and encoded code is decoded only once" do
    fields = [{"state", @token}, {"iss", @issuer}, {"code", "%2F+&="}]
    for values <- [fields, Enum.reverse(fields), [Enum.at(fields, 1), Enum.at(fields, 2), Enum.at(fields, 0)]] do
      assert {:ok, %{state: @token, issuer: @issuer, outcome: {:code, "%2F+&="}}} = Protocol.parse_callback(config(), URI.encode_query(values))
    end
  end

  test "callbacks reject smuggled aliases duplicates issuer mismatches and mixed code errors" do
    for bad <- [
      query() <> "&state=" <> @token, query() <> "&%73tate=" <> @token,
      String.replace(query(), "state=", "%73tate="), String.replace(query(), @token, "%" <> Integer.to_string(:binary.first(@token), 16) <> binary_part(@token, 1, 42)),
      URI.encode_query([{"state", @token}, {"iss", @issuer <> "/"}, {"error", "access_denied"}]),
      query([{"code", "synthetic"}, {"error", "access_denied"}]), query([{"code", "synthetic"}, {"error_description", "private"}]),
      query([{"error", "access_denied"}]) <> "&", query() <> "&next=https://private.invalid", query([{"code", "%00"}]) |> String.replace("%2500", "%00")
    ] do
      assert {:error, :invalid_callback} = Protocol.parse_callback(config(), bad)
    end
  end

  test "callback body and boundary limits reject without returning partial transaction keys" do
    for body <- ["code=synthetic", nil, <<0>>] do
      assert {:error, :invalid_callback} = Protocol.parse_callback(config(), query(), body)
    end
    assert {:ok, %{outcome: {:code, _}}} = Protocol.parse_callback(config(), query([{"code", String.duplicate("a", 4096)}]))
    for fields <- [[{"code", String.duplicate("a", 4097)}], [{"error", String.duplicate("a", 129)}], [{"error", "denied"}, {"error_description", String.duplicate("a", 1025)}]] do
      assert {:error, :invalid_callback} = Protocol.parse_callback(config(), query(fields))
    end
  end

  test "raw header duplicates are rejected regardless of case and unrelated header location" do
    for pair <- [{"COOKIE", "__Host-mixer-session=" <> @token}, {"origin", @origin}, {"x-mixer-csrf", @other}, {"AUTHORIZATION", ""}] do
      assert {:error, :invalid_request} = Protocol.parse_session_cookie(headers() ++ [pair])
      assert {:error, :invalid_csrf} = Protocol.verify_csrf(config(), [pair | headers()], @other)
    end
    assert {:error, :invalid_request} = Protocol.parse_session_cookie([{"cookie", "__Host-mixer-session=" <> @token}, {"accept", "a"}, {"Accept", "b"}])
  end

  test "raw header structural control and aggregate bounds are enforced" do
    for bad <- [%{"cookie" => @token}, [{"cookie", @token} | :bad], [{"bad_name", "x"}], [{"cookie", "__Host-mixer-session=" <> @token <> "\r\n"}], [{"x", String.duplicate("a", 8193)}], for(i <- 1..65, do: {"x-#{i}", "a"})] do
      assert {:error, :invalid_request} = Protocol.parse_session_cookie(bad)
    end
    assert {:error, :invalid_request} = Protocol.parse_session_cookie([{"a", String.duplicate("x", 8192)}, {"b", String.duplicate("x", 8192)}])
  end

  test "cookie duplicate and alias spellings never resolve an alternate session" do
    assert {:ok, @token} = Protocol.parse_session_cookie([{"cookie", "noise=abc; __Host-mixer-session=" <> @token}])
    for value <- ["__Host-mixer-session=" <> @token <> "; __Host-mixer-session=" <> @other,
      "__Host-mixer-session=\"" <> @token <> "\"", "__Host-mixer-session=" <> @token <> "=",
      "__Host-mixer-session=" <> @token <> "; noise=a; noise=b", "__Host-mixer-session=" <> @token <> ";"] do
      assert {:error, :invalid_request} = Protocol.parse_session_cookie([{"cookie", value}])
    end
    assert {:ok, nil} = Protocol.parse_session_cookie([{"cookie", "__host-mixer-session=" <> @token}])
    assert {:error, :invalid_request} = Protocol.parse_session_cookie([{"cookie", "__Host%2dmixer-session=" <> @token}])
  end

  test "CSRF requires the exact origin current expected token and canonical session cookie" do
    assert :ok = Protocol.verify_csrf(config(), headers(), @other)
    for bad <- [List.keydelete(headers(), "Cookie", 0), List.keyreplace(headers(), "Origin", 0, {"Origin", @origin <> "/"}), List.keyreplace(headers(), "X-Mixer-CSRF", 0, {"X-Mixer-CSRF", @token}), [{"Cookie", "noise=a"} | tl(headers())]] do
      assert {:error, :invalid_csrf} = Protocol.verify_csrf(config(), bad, @other)
    end
  end

  test "cookie emission cannot widen lifetime domain path or expose a script-readable value" do
    for age <- [1, 300, 900] do
      assert {:ok, value} = Protocol.session_cookie(@token, age)
      assert value == "__Host-mixer-session=" <> @token <> "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=" <> Integer.to_string(age)
      refute value =~ "Domain="
    end
    for age <- [0, -1, 901, 300.0, "300"] do
      assert {:error, :invalid_request} = Protocol.session_cookie(@token, age)
    end
  end
end
