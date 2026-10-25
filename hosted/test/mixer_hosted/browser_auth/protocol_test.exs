defmodule MixerHosted.BrowserAuth.ProtocolTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{Config, ConfigTest, Protocol}

  @token Base.url_encode64(:binary.copy(<<1>>, 32), padding: false)
  @other Base.url_encode64(:binary.copy(<<2>>, 32), padding: false)
  @cookie "__Host-mixer-session"
  @issuer "https://identity.example.invalid/tenant"

  defp query(extra \\ [{"code", "synthetic-code"}]) do
    URI.encode_query([{"state", @token}, {"iss", @issuer}] ++ extra)
  end

  defp headers do
    [
      {"cookie", @cookie <> "=" <> @token},
      {"origin", "https://console.example.invalid"},
      {"x-mixer-csrf", @token}
    ]
  end

  test "platform CSPRNG yields fresh independent canonical 256-bit values" do
    values = for _ <- 1..256, do: Protocol.random_token()
    assert length(Enum.uniq(values)) == 256
    assert Enum.all?(values, &Protocol.token?/1)
    assert Enum.all?(values, &(byte_size(&1) == 43))

    assert Enum.all?(values, fn value ->
             {:ok, raw} = Base.url_decode64(value, padding: false)
             byte_size(raw) == 32
           end)
  end

  test "PKCE S256 implements the published RFC 7636 appendix B vector" do
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

    assert {:ok, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"} =
             Protocol.pkce_challenge(verifier)

    assert Protocol.digest(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
  end

  test "token and digest reject padding alphabets length types and noncanonical unused bits" do
    alias_value = binary_part(@token, 0, 42) <> "F"
    assert {:ok, decoded} = Base.url_decode64(@token, padding: false)
    assert {:ok, ^decoded} = Base.url_decode64(alias_value, padding: false)

    for invalid <- [
          alias_value,
          @token <> "=",
          String.duplicate("A", 42),
          String.duplicate("A", 44),
          String.duplicate("/", 43),
          String.duplicate("+", 43),
          "%41" <> binary_part(@token, 1, 42),
          nil,
          7,
          <<255>>
        ] do
      refute Protocol.token?(invalid)
      assert {:error, :invalid_token} = Protocol.digest(invalid)
      assert {:error, :invalid_token} = Protocol.pkce_challenge(invalid)
    end
  end

  test "lookup digest is SHA256 of canonical ASCII and itself canonical" do
    expected = :crypto.hash(:sha256, @token) |> Base.url_encode64(padding: false)
    assert expected == Protocol.digest(@token)
    assert Protocol.token?(expected)
    refute expected == @token
    refute Protocol.digest(@token) == Protocol.digest(@other)
  end

  test "authorization URL includes only fixed configured code query scope and S256 request" do
    values = %{state: @token, nonce: @other, verifier: @token}
    assert {:ok, url} = Protocol.authorization_url(ConfigTest.config(), values)
    uri = URI.parse(url)
    assert uri.scheme == "https"
    assert uri.host == "identity.example.invalid"
    assert uri.path == "/authorize"

    assert URI.decode_query(uri.query) == %{
             "response_type" => "code",
             "response_mode" => "query",
             "client_id" => "mixer-console",
             "redirect_uri" => "https://console.example.invalid/auth/callback",
             "scope" => "openid mixer.workspace.read",
             "state" => @token,
             "nonce" => @other,
             "code_challenge" => Protocol.digest(@token),
             "code_challenge_method" => "S256"
           }

    refute url =~ "client_secret"
    refute url =~ "secret://"
    refute url =~ "vault://"
    refute url =~ "code_verifier"
    refute url =~ "api_audience"
  end

  test "authorization rejects disabled mode malformed tokens and arbitrary provider choices" do
    valid = %{state: @token, nonce: @other, verifier: @token}
    assert {:error, :invalid_request} = Protocol.authorization_url(%Config{}, valid)

    assert {:error, :invalid_request} =
             Protocol.authorization_url(%Config{mode: :configured}, valid)

    for values <- [
          Map.delete(valid, :state),
          %{valid | nonce: "invalid"},
          %{valid | verifier: "invalid"},
          %{"state" => @token, "nonce" => @other, "verifier" => @token}
        ] do
      assert {:error, :invalid_request} = Protocol.authorization_url(ConfigTest.config(), values)
    end

    for choice <- [
          :scope,
          :issuer,
          :client_id,
          :return_to,
          :redirect_uri,
          :audience,
          :prompt,
          :response_type
        ] do
      assert {:error, :invalid_request} =
               Protocol.authorization_url(ConfigTest.config(), Map.put(valid, choice, "attacker"))
    end
  end

  test "session cookie has exact host custody attributes and bounded expiry" do
    for age <- [1, 300, 900] do
      assert {:ok,
              @cookie <>
                "=" <>
                @token <>
                "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=" <> Integer.to_string(age)} ==
               Protocol.session_cookie(@token, age)
    end

    assert Protocol.clear_cookie() ==
             @cookie <> "=; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=0"

    refute Protocol.clear_cookie() =~ "Domain"
  end

  test "cookie builder rejects unsafe values and overlong or noninteger lifetimes" do
    for age <- [0, -1, 901, 300.0, "300", nil] do
      assert {:error, :invalid_request} = Protocol.session_cookie(@token, age)
    end

    for token <- [@token <> "=", "x; Domain=evil.invalid", @token <> "\r\n", nil] do
      assert {:error, :invalid_token} = Protocol.session_cookie(token, 300)
    end
  end

  test "raw cookie parser accepts exactly one canonical credential with unrelated cookies" do
    assert {:ok, @token} = Protocol.parse_session_cookie(headers())

    assert {:ok, @token} =
             Protocol.parse_session_cookie([
               {"Cookie", "theme=dark; " <> @cookie <> "=" <> @token <> "; optional="}
             ])

    assert {:ok, nil} = Protocol.parse_session_cookie([])
    assert {:ok, nil} = Protocol.parse_session_cookie([{"cookie", "theme=dark"}])
  end

  test "duplicate split case-varied cookies and all Authorization headers reject" do
    for raw <- [
          [{"cookie", @cookie <> "=" <> @token <> "; " <> @cookie <> "=" <> @token}],
          [{"cookie", @cookie <> "=" <> @token}, {"Cookie", "theme=dark"}],
          [{"cookie", "theme=dark; theme=light"}]
        ] do
      assert {:error, :invalid_request} = Protocol.parse_session_cookie(raw)
    end

    for name <- ["authorization", "Authorization", "AUTHORIZATION"],
        value <- ["", "Bearer synthetic"] do
      assert {:error, :invalid_request} =
               Protocol.parse_session_cookie([{name, value} | headers()])
    end
  end

  test "cookie parser rejects encoded aliases whitespace tricks quoted values and invalid opaque tokens" do
    for cookie <- [
          @cookie <> " =" <> @token,
          @cookie <> "= " <> @token,
          @cookie <> "=\"" <> @token <> "\"",
          "__Host%2Dmixer-session=" <> @token,
          @cookie <> "=" <> @token <> "=",
          @cookie <> "=%41" <> binary_part(@token, 1, 42),
          @cookie <> "=",
          "",
          ";",
          "theme=dark;",
          "theme=dark, " <> @cookie <> "=" <> @token,
          @cookie <> "=" <> @token <> "\t"
        ] do
      assert {:error, :invalid_request} = Protocol.parse_session_cookie([{"cookie", cookie}])
    end
  end

  test "cookie and header count byte structure bounds stop malformed requests" do
    for raw <- [
          nil,
          %{"cookie" => @token},
          [{"Cookie", String.duplicate("a", 8193)}],
          [{String.duplicate("a", 129), "x"}],
          [{"Origin ", "x"}],
          [{"x", "a\r\nb"}],
          [{"x", <<255>>}],
          [{"x", nil}],
          ["bad"],
          Enum.map(1..65, &{"x-#{&1}", ""}),
          Enum.map(1..3, &{"x-#{&1}", String.duplicate("x", 8192)})
        ] do
      assert {:error, :invalid_request} = Protocol.parse_session_cookie(raw)
    end

    thirty_two = Enum.map_join(1..32, ";", &"c#{&1}=v")
    assert {:ok, nil} = Protocol.parse_session_cookie([{"cookie", thirty_two}])

    assert {:error, :invalid_request} =
             Protocol.parse_session_cookie([{"cookie", thirty_two <> ";extra=v"}])
  end

  test "same-origin synchronizer CSRF comparison admits only the canonical session token" do
    assert :ok = Protocol.verify_csrf(ConfigTest.config(), headers(), @token)
    upper = Enum.map(headers(), fn {key, value} -> {String.upcase(key), value} end)
    assert :ok = Protocol.verify_csrf(ConfigTest.config(), upper, @token)
    assert {:error, :invalid_csrf} = Protocol.verify_csrf(ConfigTest.config(), headers(), @other)
    assert {:error, :invalid_csrf} = Protocol.verify_csrf(%Config{}, headers(), @token)

    assert {:error, :invalid_csrf} =
             Protocol.verify_csrf(%Config{mode: :configured}, headers(), @token)
  end

  test "missing null foreign sibling alternate-port and aliased Origins fail CSRF" do
    for bad <- [
          "null",
          "",
          "https://sibling.example.invalid",
          "http://console.example.invalid",
          "https://console.example.invalid:443",
          "https://console.example.invalid/",
          "https://CONSOLE.example.invalid",
          "https://console.example.invalid https://evil.invalid"
        ] do
      changed = List.keyreplace(headers(), "origin", 0, {"origin", bad})
      assert {:error, :invalid_csrf} = Protocol.verify_csrf(ConfigTest.config(), changed, @token)
    end

    for name <- ["origin", "x-mixer-csrf", "cookie"] do
      assert {:error, :invalid_csrf} =
               Protocol.verify_csrf(
                 ConfigTest.config(),
                 List.keydelete(headers(), name, 0),
                 @token
               )
    end
  end

  test "duplicate origin CSRF and cookies are rejected even when their values agree" do
    for name <- ["origin", "x-mixer-csrf", "cookie"] do
      {^name, value} = List.keyfind(headers(), name, 0)

      assert {:error, :invalid_csrf} =
               Protocol.verify_csrf(
                 ConfigTest.config(),
                 [{String.upcase(name), value} | headers()],
                 @token
               )
    end

    assert {:error, :invalid_csrf} =
             Protocol.verify_csrf(
               ConfigTest.config(),
               [{"Authorization", ""} | headers()],
               @token
             )
  end

  test "CSRF rejects malformed expected and supplied tokens without coercion" do
    for bad <- [@token <> "=", nil, 43, String.duplicate("A", 42), String.duplicate("/", 43)] do
      assert {:error, :invalid_csrf} = Protocol.verify_csrf(ConfigTest.config(), headers(), bad)
      changed = List.keyreplace(headers(), "x-mixer-csrf", 0, {"x-mixer-csrf", bad})
      assert {:error, :invalid_csrf} = Protocol.verify_csrf(ConfigTest.config(), changed, @token)
    end
  end

  test "valid callback preserves state issuer and opaque code as unclaimed input" do
    assert {:ok, %{state: @token, issuer: @issuer, outcome: {:code, "synthetic-code"}}} =
             Protocol.parse_callback(ConfigTest.config(), query())

    encoded = query([{"code", "plus+slash/equals=percent%2F"}])

    assert {:ok, %{outcome: {:code, "plus+slash/equals=percent%2F"}}} =
             Protocol.parse_callback(ConfigTest.config(), encoded)
  end

  test "provider rejection retains claimable state and issuer but discards all provider text" do
    raw =
      query([
        {"error", "access_denied"},
        {"error_description", "private-provider-detail"},
        {"error_uri", "https://provider.invalid/sensitive"}
      ])

    assert {:ok, result} = Protocol.parse_callback(ConfigTest.config(), raw)
    assert result == %{state: @token, issuer: @issuer, outcome: {:error, :provider_rejected}}
    refute inspect(result) =~ "private-provider-detail"
    refute inspect(result) =~ "provider.invalid"

    assert {:ok, %{outcome: {:error, :provider_rejected}}} =
             Protocol.parse_callback(
               ConfigTest.config(),
               query([{"error", "unrecognized_provider_error"}])
             )
  end

  test "issuer mix-up fails before success or provider rejection can be trusted" do
    for outcome <- [[{"code", "code"}], [{"error", "access_denied"}]],
        issuer <- [
          "https://evil.invalid",
          @issuer <> "/",
          "https://IDENTITY.example.invalid/tenant",
          "https://identity.example.invalid:443/tenant",
          "https://identity.example.invalid/other"
        ] do
      raw = URI.encode_query([{"state", @token}, {"iss", issuer}] ++ outcome)
      assert {:error, :invalid_callback} = Protocol.parse_callback(ConfigTest.config(), raw)
    end
  end

  test "missing duplicate unknown and escaped-equivalent query keys reject" do
    for raw <- [
          "code=x",
          "state=" <> @token <> "&code=x",
          "iss=" <> URI.encode_www_form(@issuer) <> "&code=x",
          query() <> "&state=" <> @token,
          query() <> "&iss=" <> URI.encode_www_form(@issuer),
          query() <> "&code=second",
          query() <> "&%73tate=" <> @token,
          query() <> "&sta%74e=" <> @token,
          String.replace(query(), "state=", "%73tate="),
          query() <> "&return_to=/workspace",
          query() <> "&issuer=" <> @issuer,
          query() <> "&",
          "&" <> query()
        ] do
      assert {:error, :invalid_callback} = Protocol.parse_callback(ConfigTest.config(), raw)
    end
  end

  test "code and error or error-only metadata combinations reject" do
    for extra <- [
          [{"code", "c"}, {"error", "access_denied"}],
          [{"code", "c"}, {"error_description", "detail"}],
          [{"code", "c"}, {"error_uri", "https://provider.invalid"}],
          [{"error_description", "detail"}],
          [{"error_uri", "https://provider.invalid"}],
          [{"error", "denied"}, {"error", "denied"}],
          [{"code", ""}],
          [{"error", ""}],
          []
        ] do
      assert {:error, :invalid_callback} =
               Protocol.parse_callback(ConfigTest.config(), query(extra))
    end
  end

  test "state is canonical raw Base64URL and rejects alternate percent representations" do
    for state <- [
          @token <> "=",
          "",
          binary_part(@token, 0, 42) <> "F",
          "%41" <> binary_part(@token, 1, 42),
          "+" <> binary_part(@token, 1, 42),
          String.duplicate("A", 44)
        ] do
      raw = "state=" <> state <> "&iss=" <> URI.encode_www_form(@issuer) <> "&code=x"
      assert {:error, :invalid_callback} = Protocol.parse_callback(ConfigTest.config(), raw)
    end
  end

  test "malformed single-decode escapes controls fragments and separator aliases reject" do
    for code <- [
          "%",
          "%1",
          "%GG",
          "%00",
          "%0D%0A",
          "%7F",
          "%FF",
          <<255>>,
          "x#fragment",
          "x;error=denied",
          "x\"onload",
          "x<svg>"
        ] do
      raw = "state=" <> @token <> "&iss=" <> URI.encode_www_form(@issuer) <> "&code=" <> code
      assert {:error, :invalid_callback} = Protocol.parse_callback(ConfigTest.config(), raw)
    end

    assert {:ok, %{outcome: {:code, "%00"}}} =
             Protocol.parse_callback(ConfigTest.config(), query([{"code", "%00"}]))
  end

  test "callback bounds distinguish accepted exact limits from excess before decode" do
    assert {:ok, %{outcome: {:code, code}}} =
             Protocol.parse_callback(
               ConfigTest.config(),
               query([{"code", String.duplicate("c", 4096)}])
             )

    assert byte_size(code) == 4096

    for extra <- [
          [{"code", String.duplicate("c", 4097)}],
          [{"error", String.duplicate("e", 129)}],
          [{"error", "denied"}, {"error_description", String.duplicate("d", 1025)}],
          [{"error", "denied"}, {"error_uri", String.duplicate("u", 2049)}]
        ] do
      assert {:error, :invalid_callback} =
               Protocol.parse_callback(ConfigTest.config(), query(extra))
    end

    encoded_limit =
      "state=" <>
        @token <>
        "&iss=" <> URI.encode_www_form(@issuer) <> "&code=" <> String.duplicate("%41", 4096)

    assert byte_size(encoded_limit) > 8192

    assert {:error, :invalid_callback} =
             Protocol.parse_callback(ConfigTest.config(), encoded_limit)

    for raw <- [String.duplicate("a", 8193), String.duplicate("&", 8192), nil, 8192, ""] do
      assert {:error, :invalid_callback} = Protocol.parse_callback(ConfigTest.config(), raw)
    end
  end

  test "callback admits no body disabled capability or caller-selected destination" do
    for body <- [" ", "{}", "state=x", <<0>>, [], nil] do
      assert {:error, :invalid_callback} =
               Protocol.parse_callback(ConfigTest.config(), query(), body)
    end

    assert {:error, :invalid_callback} = Protocol.parse_callback(%Config{}, query())

    assert {:error, :invalid_callback} =
             Protocol.parse_callback(%Config{mode: :configured}, query())

    assert {:error, :invalid_callback} =
             Protocol.parse_callback(
               ConfigTest.config(),
               query() <> "&return_to=https://evil.invalid"
             )
  end
end
