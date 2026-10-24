defmodule MixerHostedIndependentVerifierReviewTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{AccessTokenVerifier, TrustSnapshot, VerifiedIdentity}
  @now 1_000_000
  @profile %{
    profile_id: "review-profile",
    profile_version: 7,
    issuer: "https://issuer.example.test/tenant",
    audience: "mixer-api",
    client_id: "review-client",
    identity_class: :human,
    enabled: true
  }
  @header %{"alg" => "RS256", "typ" => "at+jwt", "kid" => "old"}
  @claims %{
    "iss" => @profile.issuer,
    "sub" => "subject-1",
    "aud" => @profile.audience,
    "client_id" => @profile.client_id,
    "iat" => @now,
    "exp" => @now + 60,
    "jti" => "credential-1"
  }

  setup_all do
    Application.put_env(:jose, :json_module, :jose_json_jason)
    Application.put_env(:jose, :crypto_fallback, false)
    Application.put_env(:jose, :unsecured_signing, false)
    {:ok, _} = Application.ensure_all_started(:jose)
    JOSE.json_module(:jose_json_jason)
    JOSE.crypto_fallback(false)
    JOSE.unsecured_signing(false)
    old = JOSE.JWK.generate_key({:rsa, 2048})
    next = JOSE.JWK.generate_key({:rsa, 2048})
    large = JOSE.JWK.generate_key({:rsa, 4096})
    IO.inspect(%{otp: :erlang.system_info(:otp_release), erts: :erlang.system_info(:version),
      elixir: System.version(), jose: Application.spec(:jose, :vsn),
      jason: Application.spec(:jason, :vsn), openssl: :crypto.info_lib(),
      json: JOSE.json_module(), fallback: JOSE.crypto_fallback(),
      unsecured: JOSE.unsecured_signing()}, label: "REVIEW CRYPTO RUNTIME")
    %{old: old, next: next, large: large, jwk: public(old, "old")}
  end

  defp public(key, kid) do
    {_, value} = JOSE.JWK.to_public_map(key)
    Map.merge(value, %{"kid" => kid, "alg" => "RS256", "use" => "sig"})
  end

  defp new(keys, profile \\ @profile, fetched \\ @now, until \\ @now + 300) do
    TrustSnapshot.new(profile, Jason.encode!(%{"keys" => keys}), fetched, until)
  end

  defp snapshot(context, profile \\ @profile) do
    {:ok, value} = new([context.jwk], profile)
    value
  end

  defp b64(value), do: Base.url_encode64(value, padding: false)
  defp json(value) when is_binary(value), do: value
  defp json(value), do: Jason.encode!(value)

  # Test-only compact framing preserves exact raw JSON, including deliberately
  # ambiguous headers. Signing itself uses JOSE's RS256 implementation.
  defp raw_sign(key, claims \\ @claims, header \\ @header) do
    input = b64(json(header)) <> "." <> b64(json(claims))
    signature = :jose_jws_alg_rsa_pkcs1_v1_5.sign(JOSE.JWK.to_record(key), input, :RS256)
    input <> "." <> b64(signature)
  end

  defp assert_accept(token, context, now \\ @now) do
    assert {:ok, %VerifiedIdentity{} = identity} = AccessTokenVerifier.verify(token, now, snapshot(context))
    identity
  end

  defp assert_deny(token, context, now \\ @now) do
    assert {:error, :unauthenticated} = AccessTokenVerifier.verify(token, now, snapshot(context))
  end

  test "real RSA endpoints, both access-token types and original JSON bytes", c do
    for {key, kid} <- [{c.old, "old"}, {c.large, "large"}], typ <- ["at+jwt", "application/at+jwt"] do
      context = %{c | jwk: public(key, kid)}
      header = %{@header | "kid" => kid, "typ" => typ}
      payload = " \n" <> Jason.encode!(@claims) <> "  "
      assert %VerifiedIdentity{profile_id: "review-profile", profile_version: 7,
        issuer: "https://issuer.example.test/tenant", subject: "subject-1",
        client_id: "review-client", credential_ref: "credential-1",
        issued_at: @now, expires_at: 1_000_060, identity_class: :human, scopes: []} =
          assert_accept(raw_sign(key, payload, header), context)
    end
  end

  test "validly signed escaped duplicate protected algorithm is denied", c do
    for header <- [~S({"alg":"RS256","\u0061lg":"RS256","typ":"at+jwt","kid":"old"}),
                   ~S({"alg":"RS256","typ":"at+jwt","kid":"old","kid":"old"})] do
      assert_deny(raw_sign(c.old, @claims, header), c)
    end
  end

  test "validly signed escaped identity and deeply nested ignored duplicates are denied", c do
    raw = Jason.encode!(@claims)
    for tail <- [~S(,"\u0073ub":"subject-1"}),
                 ~S(,"ignored":{"levels":[{"x":1,"\u0078":1}]}}),
                 ~S(,"ignored":[{"nested":{"roles":"owner","roles":"owner"}}]})] do
      assert_deny(raw_sign(c.old, String.trim_trailing(raw, "}") <> tail), c)
    end
  end

  test "malformed nonobject and structurally excessive signed JSON is denied", c do
    for value <- ["null", "[]", "17", "{", <<123, 34, 255, 34, 58, 49, 125>>,
                  Jason.encode!(Map.put(@claims, "nested", Enum.reduce(1..17, 0, fn _, v -> [v] end))),
                  Jason.encode!(Map.put(@claims, "array", Enum.to_list(1..65))),
                  Jason.encode!(Enum.reduce(1..58, @claims, fn i, a -> Map.put(a, "x#{i}", 0) end))] do
      assert_deny(raw_sign(c.old, value), c)
    end
  end

  test "JWT purpose and unsupported protected headers reject despite valid RSA signatures", c do
    for typ <- ["JWT", "id+jwt", "AT+JWT", "application/jwt", nil] do
      assert_deny(raw_sign(c.old, @claims, Map.put(@header, "typ", typ)), c)
    end
    for {name, value} <- [{"jku", "https://attacker.example.test/keys"}, {"x5u", "https://attacker.example.test/cert"},
                         {"crit", []}, {"b64", false}, {"jwk", c.jwk}, {"x5c", []}, {"zip", "DEF"}, {"extra", 1}] do
      assert_deny(raw_sign(c.old, @claims, Map.put(@header, name, value)), c)
    end
  end

  test "real nonallowlisted algorithm signatures and public-key-as-HMAC are denied", c do
    for algorithm <- ["RS512", "PS256"] do
      {_, token} = JOSE.JWS.sign(c.old, Jason.encode!(@claims), %{@header | "alg" => algorithm}) |> JOSE.JWS.compact()
      assert_deny(token, c)
    end
    {_, pem} = JOSE.JWK.to_public_pem(c.old)
    mac_key = JOSE.JWK.from_oct(pem)
    {_, token} = JOSE.JWS.sign(mac_key, Jason.encode!(@claims), %{@header | "alg" => "HS256"}) |> JOSE.JWS.compact()
    assert_deny(token, c)
    assert_deny(raw_sign(c.old, @claims, %{@header | "alg" => "none"}), c)
  end

  test "wrong key altered payload and altered signature are denied", c do
    assert_deny(raw_sign(c.next), c)
    token = raw_sign(c.old)
    [header, payload, signature] = String.split(token, ".")
    altered = b64(Jason.encode!(Map.put(@claims, "sub", "forged")))
    assert_deny(Enum.join([header, altered, signature], "."), c)
    {:ok, <<first, rest::binary>>} = Base.url_decode64(signature, padding: false)
    assert_deny(Enum.join([header, payload, b64(<<Bitwise.bxor(first, 1), rest::binary>>)], "."), c)
  end

  test "compact framing, canonical base64, bearer prefix and byte limits fail closed", c do
    token = raw_sign(c.old)
    [h, p, s] = String.split(token, ".")
    for invalid <- ["Bearer " <> token, token <> ".x", h <> "." <> p <> ".", "." <> p <> "." <> s,
                    h <> "." <> p <> "=." <> s, h <> "." <> p <> "." <> s <> "=",
                    String.replace(token, ".", "+", global: false), String.duplicate("a", 4090),
                    nil, 42, %{"token" => token}] do
      assert_deny(invalid, c)
    end
    # Flip only unused base64 trailing bits. Decoded bytes are identical, but the
    # alternate compact spelling must not acquire a second accepted identity.
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    last = :binary.last(s)
    {index, 1} = :binary.match(alphabet, <<last>>)
    alternate = binary_part(s, 0, byte_size(s) - 1) <> binary_part(alphabet, index + 1, 1)
    assert Base.url_decode64(alternate, padding: false) == Base.url_decode64(s, padding: false)
    assert_deny(Enum.join([h, p, alternate], "."), c)
  end

  test "signature exact modulus size, bounded kid and header/claim size are enforced", c do
    [h, p, s] = String.split(raw_sign(c.old), ".")
    {:ok, signature} = Base.url_decode64(s, padding: false)
    assert_deny(Enum.join([h, p, b64(<<0, signature::binary>>)], "."), c)
    assert_deny(raw_sign(c.old, @claims, %{@header | "kid" => String.duplicate("k", 129)}), c)
    assert_deny(raw_sign(c.old, String.duplicate(" ", 3073) <> Jason.encode!(@claims)), c)
    assert_deny(raw_sign(c.old, @claims, String.duplicate(" ", 2049) <> Jason.encode!(@header)), c)
  end

  test "required identity binding types and identifier bounds reject", c do
    for claim <- Map.keys(@claims) do
      assert_deny(raw_sign(c.old, Map.delete(@claims, claim)), c)
    end
    for {name, values} <- [{"iss", ["https://issuer.example.test/tenant/", "HTTPS://issuer.example.test/tenant", [@profile.issuer]]},
                          {"client_id", ["other", [@profile.client_id], nil]},
                          {"sub", ["", String.duplicate("x", 257), 1, ["subject-1"]]},
                          {"jti", ["", String.duplicate("x", 257), false, %{}]}], value <- values do
      assert_deny(raw_sign(c.old, Map.put(@claims, name, value)), c)
    end
    assert_accept(raw_sign(c.old, Map.merge(@claims, %{"sub" => String.duplicate("x", 256), "jti" => String.duplicate("y", 256)})), c)
  end

  test "audience arrays are unique bounded typed and contain configured API", c do
    assert_accept(raw_sign(c.old, Map.put(@claims, "aud", ["other", @profile.audience])), c)
    for audience <- [[], [@profile.audience, @profile.audience], [@profile.audience, 1],
                     [@profile.audience, ""], [@profile.audience, String.duplicate("x", 257)],
                     [@profile.audience | Enum.map(1..8, &"a#{&1}")], ["other"],
                     %{"aud" => @profile.audience}, true] do
      assert_deny(raw_sign(c.old, Map.put(@claims, "aud", audience)), c)
    end
  end

  test "numeric-date strings floats booleans negative and oversized integers reject", c do
    for claim <- ["iat", "exp", "nbf"], value <- ["1000000", 1_000_000.0, true, nil, -1, 9_007_199_254_740_992] do
      assert_deny(raw_sign(c.old, Map.put(@claims, claim, value)), c)
    end
    raw = Jason.encode!(@claims) |> String.replace("\"iat\":1000000", "\"iat\":1e6")
    assert_deny(raw_sign(c.old, raw), c)
  end

  test "human/service lifetime ceiling comes from configured class and exact exp is exclusive", c do
    assert_accept(raw_sign(c.old, %{@claims | "exp" => @now + 900}), c)
    assert_deny(raw_sign(c.old, %{@claims | "exp" => @now + 901}), c)
    service = snapshot(c, %{@profile | identity_class: :service})
    assert {:ok, %VerifiedIdentity{identity_class: :service}} =
      AccessTokenVerifier.verify(raw_sign(c.old, Map.merge(@claims, %{"exp" => @now + 300, "kind" => "human"})), @now, service)
    assert {:error, :unauthenticated} =
      AccessTokenVerifier.verify(raw_sign(c.old, %{@claims | "exp" => @now + 301}), @now, service)
    assert_deny(raw_sign(c.old), c, @now + 60)
    assert_deny(raw_sign(c.old, %{@claims | "iat" => @now + 60}), c)
  end

  test "future iat nbf skew accepts 30 and rejects 31 seconds", c do
    for claim <- ["iat", "nbf"] do
      assert_accept(raw_sign(c.old, Map.put(@claims, claim, @now + 30)), c)
      assert_deny(raw_sign(c.old, Map.put(@claims, claim, @now + 31)), c)
    end
    assert_deny(raw_sign(c.old, Map.put(@claims, "nbf", @now + 60)), c)
  end

  test "scope parsing narrows output and signed roles/tenant/kind cannot add authority", c do
    claims = Map.merge(@claims, %{"scope" => "owner mixer.audit.read project:* mixer.artifact.read",
      "roles" => ["owner"], "groups" => ["administrator"], "kind" => "service",
      "organization" => "forged-org", "project" => "forged-project"})
    identity = assert_accept(raw_sign(c.old, claims), c)
    assert identity.scopes == ["mixer.artifact.read", "mixer.audit.read"]
    assert identity.identity_class == :human
    assert Enum.sort(Map.keys(Map.from_struct(identity))) == Enum.sort([:profile_id, :profile_version,
      :issuer, :subject, :client_id, :credential_ref, :issued_at, :expires_at, :identity_class, :scopes])
    assert assert_accept(raw_sign(c.old, Map.put(@claims, "scope", "unknown")), c).scopes == []
  end

  test "scope type separators controls duplicates and cardinality bounds reject", c do
    for scope <- ["", "mixer.audit.read mixer.audit.read", " mixer.audit.read", "mixer.audit.read ",
                  "mixer.audit.read  other", "mixer.audit.read\tother", "bad\\scope", "bad\"scope", "é",
                  ["mixer.audit.read"], nil, true, String.duplicate("a", 1025),
                  Enum.map_join(1..33, " ", &"s#{&1}")] do
      assert_deny(raw_sign(c.old, Map.put(@claims, "scope", scope)), c)
    end
  end

  test "freshness state, missing trust, invalid now and disabled profile fail closed", c do
    token = raw_sign(c.old)
    for trust <- [nil, :unconfigured] do
      assert {:error, :identity_unavailable} = AccessTokenVerifier.verify(token, @now, trust)
    end
    {:ok, fresh} = new([c.jwk])
    for now <- [@now - 1, @now + 300, @now + 301, -1, 1.0, "1000000", nil] do
      assert {:error, :identity_unavailable} = AccessTokenVerifier.verify(token, now, fresh)
    end
    {:ok, disabled} = new([c.jwk], %{@profile | enabled: false})
    assert {:error, :unauthenticated} = AccessTokenVerifier.verify(token, @now, disabled)
    assert {:error, :unauthenticated} = AccessTokenVerifier.verify(token, @now + 301, disabled)
  end

  test "overlap rotation then removed-key denial does not try unrelated keys", c do
    next_jwk = public(c.next, "next")
    old_token = raw_sign(c.old)
    next_token = raw_sign(c.next, @claims, %{@header | "kid" => "next"})
    {:ok, overlap} = new([c.jwk, next_jwk])
    assert {:ok, _} = AccessTokenVerifier.verify(old_token, @now, overlap)
    assert {:ok, _} = AccessTokenVerifier.verify(next_token, @now, overlap)
    {:ok, removed} = new([next_jwk])
    assert {:error, :unauthenticated} = AccessTokenVerifier.verify(old_token, @now, removed)
    assert {:ok, _} = AccessTokenVerifier.verify(next_token, @now, removed)
    assert {:error, :unauthenticated} = AccessTokenVerifier.verify(raw_sign(c.old, @claims, %{@header | "kid" => "next"}), @now, removed)
  end

  test "profile is exact typed bounded and immutable when caller builds another value", c do
    for profile <- [Map.put(@profile, :extra, true), Map.delete(@profile, :enabled),
                    Map.put(@profile, :identity_class, "human"), Map.put(@profile, :enabled, 1),
                    Map.put(@profile, :profile_version, 0), Map.put(@profile, :profile_version, 1.0),
                    Map.put(@profile, :profile_version, 2_147_483_648),
                    Map.put(@profile, :issuer, "http://issuer.example.test"),
                    Map.put(@profile, :issuer, "https://user@issuer.example.test"),
                    Map.put(@profile, :issuer, "https://issuer.example.test?x=1"),
                    Map.put(@profile, :issuer, "https://issuer.example.test#fragment"),
                    Map.put(@profile, :profile_id, ""), Map.put(@profile, :audience, "")] do
      assert {:error, :invalid_trust_configuration} = new([c.jwk], profile)
    end
    old = snapshot(c)
    changed_profile = %{@profile | enabled: false, profile_version: 8}
    assert {:ok, _} = new([c.jwk], changed_profile)
    assert {:ok, %VerifiedIdentity{profile_version: 7}} = AccessTokenVerifier.verify(raw_sign(c.old), @now, old)
  end

  test "snapshot freshness range rejects scalar confusion overflow and ceiling violations", c do
    for {fetched, until} <- [{@now, @now}, {@now, @now - 1}, {@now, @now + 301},
                            {-1, 1}, {1.0, 2}, {1, 2.0}, {true, 2},
                            {9_007_199_254_740_991, 9_007_199_254_740_992}] do
      assert {:error, :invalid_trust_configuration} = new([c.jwk], @profile, fetched, until)
    end
    assert {:ok, _} = new([c.jwk], @profile, @now, @now + 1)
  end

  test "JWKS rejects duplicate decoded names root extensions scalars and too many keys", c do
    key_json = Jason.encode!(c.jwk)
    for raw <- [~s({"keys":[#{key_json}],"\u006beys":[#{key_json}]}),
                ~s({"keys":[#{String.trim_trailing(key_json, "}")},"\\u006bid":"old"}]}),
                "[]", "{\"keys\":null}", "{\"keys\":[1]}",
                Jason.encode!(%{"keys" => [c.jwk], "extra" => true}),
                Jason.encode!(%{"keys" => []}), String.duplicate(" ", 262_145)] do
      assert {:error, :invalid_trust_configuration} = TrustSnapshot.new(@profile, raw, @now, @now + 300)
    end
    assert {:error, :invalid_trust_configuration} = new([c.jwk, c.jwk])
    assert {:error, :invalid_trust_configuration} = new(Enum.map(1..17, &Map.put(c.jwk, "kid", "k#{&1}")))
    assert {:ok, _} = new(Enum.map(1..16, &Map.put(c.jwk, "kid", "k#{&1}")))
  end

  test "RSA metadata private fields key operations and canonical exponent reject", c do
    for {name, value} <- [{"kty", "oct"}, {"alg", "HS256"}, {"use", "enc"},
                         {"kid", ""}, {"kid", String.duplicate("x", 129)},
                         {"key_ops", "verify"}, {"key_ops", ["verify", "sign"]},
                         {"key_ops", ["verify", "verify"]}, {"key_ops", []},
                         {"d", "AQAB"}, {"p", "AQAB"}, {"oth", []}, {"x5c", []},
                         {"e", "Aw"}, {"e", 65537}, {"e", "AAEAAQ"}, {"e", "AQAB="}] do
      assert {:error, :invalid_trust_configuration} = new([Map.put(c.jwk, name, value)])
    end
    for name <- ["alg", "use", "kty", "kid", "n", "e"] do
      assert {:error, :invalid_trust_configuration} = new([Map.delete(c.jwk, name)])
    end
    assert {:ok, _} = new([Map.put(c.jwk, "key_ops", ["verify"])])
  end

  test "RSA modulus bounds minimal unsigned shape oddness and atomic candidate rejection", c do
    {:ok, modulus} = Base.url_decode64(c.jwk["n"], padding: false)
    <<_first, rest::binary>> = modulus
    prefix = binary_part(modulus, 0, byte_size(modulus) - 1)
    for n <- [b64(<<0, modulus::binary>>), b64(<<0x7F, rest::binary>>),
              b64(<<0x80, 0::size(4096), 1>>), b64(prefix <> <<0>>), "", 123, c.jwk["n"] <> "="] do
      bad = Map.put(c.jwk, "n", n)
      assert {:error, :invalid_trust_configuration} = new([bad])
      assert {:error, :invalid_trust_configuration} = new([c.jwk, Map.put(bad, "kid", "next")])
    end
    old = snapshot(c)
    assert {:ok, _} = AccessTokenVerifier.verify(raw_sign(c.old), @now, old)
  end
end
