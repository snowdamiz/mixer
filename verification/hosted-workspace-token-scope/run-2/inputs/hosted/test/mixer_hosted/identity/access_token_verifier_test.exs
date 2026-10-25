defmodule MixerHosted.Identity.AccessTokenVerifierTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{AccessTokenVerifier, TrustSnapshot, VerifiedIdentity}

  @now 1_800_000_000
  @profile %{
    profile_id: "synthetic-rfc9068-rs256-v1",
    profile_version: 1,
    issuer: "https://issuer.invalid/oauth",
    audience: "mixer-api",
    client_id: "registered-client",
    identity_class: :human,
    enabled: true
  }

  setup_all do
    {:ok, _} = Application.ensure_all_started(:jose)
    private = JOSE.JWK.generate_key({:rsa, 2_048})
    large_private = JOSE.JWK.generate_key({:rsa, 4_096})
    wrong_private = JOSE.JWK.generate_key({:rsa, 2_048})
    weak_private = JOSE.JWK.generate_key({:rsa, 1_024})
    public = public(private)

    {:ok,
     private: private,
     large_private: large_private,
     wrong_private: wrong_private,
     weak_private: weak_private,
     public: public,
     snapshot: snapshot([public]),
     header: %{"alg" => "RS256", "kid" => "test-rsa", "typ" => "at+jwt"},
     claims: %{
       "iss" => @profile.issuer,
       "aud" => @profile.audience,
       "sub" => "subject-1",
       "client_id" => @profile.client_id,
       "jti" => "credential-1",
       "iat" => @now - 1,
       "exp" => @now + 299,
       "scope" => "mixer.artifact.read mixer.artifact.upload mixer.audit.read"
     }}
  end

  defp public(private, kid \\ "test-rsa") do
    private
    |> JOSE.JWK.to_public()
    |> JOSE.JWK.to_map()
    |> elem(1)
    |> Map.merge(%{"kid" => kid, "alg" => "RS256", "use" => "sig", "key_ops" => ["verify"]})
  end

  defp snapshot(keys, profile \\ @profile, fetched_at \\ @now - 1, fresh_until \\ @now + 299) do
    {:ok, value} =
      TrustSnapshot.new(profile, Jason.encode!(%{"keys" => keys}), fetched_at, fresh_until)

    value
  end

  defp sign(context, claims \\ nil, header \\ nil) do
    JOSE.JWS.sign(context.private, json(claims || context.claims), header || context.header)
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  defp json(raw) when is_binary(raw), do: raw
  defp json(value), do: Jason.encode!(value)

  # Signing arbitrary original JSON bytes exercises policy independently of the
  # test serializer. The product uses JOSE, never this test-only raw signer.
  defp sign_raw(context, raw_header, raw_payload) do
    input =
      Base.url_encode64(raw_header, padding: false) <>
        "." <> Base.url_encode64(raw_payload, padding: false)

    {_, key} = JOSE.JWK.to_key(context.private)
    signature = :public_key.sign(input, :sha256, key)
    input <> "." <> Base.url_encode64(signature, padding: false)
  end

  defp reject(context, token) do
    assert AccessTokenVerifier.verify(token, @now, context.snapshot) == {:error, :unauthenticated}
  end

  defp invalid_snapshot(keys, profile \\ @profile) do
    assert TrustSnapshot.new(profile, json(%{"keys" => keys}), @now - 1, @now + 299) ==
             {:error, :invalid_trust_configuration}
  end

  test "real 2048/4096-bit RS256 signatures and both access-token type spellings", c do
    for key <- [c.private, c.large_private], typ <- ["at+jwt", "application/at+jwt"] do
      context = %{c | private: key}
      trust = snapshot([public(key)])
      token = sign(context, nil, %{c.header | "typ" => typ})
      assert {:ok, identity} = AccessTokenVerifier.verify(token, @now, trust)

      assert Map.from_struct(identity) == %{
               profile_id: @profile.profile_id,
               profile_version: 1,
               issuer: @profile.issuer,
               subject: "subject-1",
               client_id: @profile.client_id,
               credential_ref: "credential-1",
               issued_at: @now - 1,
               expires_at: @now + 299,
               identity_class: :human,
               scopes: ["mixer.artifact.read", "mixer.artifact.upload", "mixer.audit.read"]
             }

      assert %VerifiedIdentity{} = identity
    end
  end

  test "signature and payload changes, wrong key and noncanonical signature are rejected", c do
    [header, payload, signature] = :binary.split(sign(c), ".", [:global])

    changed =
      Jason.encode!(%{c.claims | "sub" => "attacker"}) |> Base.url_encode64(padding: false)

    reject(c, Enum.join([header, changed, signature], "."))
    <<first, rest::binary>> = Base.url_decode64!(signature, padding: false)

    changed_signature =
      Base.url_encode64(<<Bitwise.bxor(first, 1), rest::binary>>, padding: false)

    reject(c, Enum.join([header, payload, changed_signature], "."))
    reject(c, sign(%{c | private: c.wrong_private}))
    reject(c, Enum.join([header, payload, signature <> "="], "."))

    # A 2048-bit RSA signature ends with four unused base64 bits. Alter only
    # those bits: decoded bytes match, but the wire encoding is noncanonical.
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    last = :binary.last(signature)
    {index, 1} = :binary.match(alphabet, <<last>>)

    alternate =
      binary_part(signature, 0, byte_size(signature) - 1) <> <<:binary.at(alphabet, index + 1)>>

    assert Base.url_decode64!(alternate, padding: false) ==
             Base.url_decode64!(signature, padding: false)

    reject(c, Enum.join([header, payload, alternate], "."))
  end

  test "none and genuine unsupported RSA/HMAC/EC/EdDSA signatures cannot widen policy", c do
    none_header =
      Jason.encode!(%{c.header | "alg" => "none"}) |> Base.url_encode64(padding: false)

    payload = Jason.encode!(c.claims) |> Base.url_encode64(padding: false)
    reject(c, none_header <> "." <> payload <> ".")

    for alg <- ["RS512", "PS256"] do
      token = sign(c, nil, %{c.header | "alg" => alg})
      assert {true, _, _} = JOSE.JWS.verify_strict(c.private, [alg], token)
      reject(c, token)
    end

    {_, pem} = JOSE.JWK.to_pem(JOSE.JWK.from_map(c.public))
    hmac = JOSE.JWK.from_oct(pem)

    for {alg, key} <- [
          {"HS256", hmac},
          {"ES256", JOSE.JWK.generate_key({:ec, :secp256r1})},
          {"EdDSA", JOSE.JWK.generate_key({:okp, :Ed25519})}
        ] do
      token = sign(%{c | private: key}, nil, %{c.header | "alg" => alg})
      assert {true, _, _} = JOSE.JWS.verify_strict(key, [alg], token)
      reject(c, token)
    end

    refute JOSE.crypto_fallback()
    refute JOSE.unsecured_signing()
    assert JOSE.json_module() == :jose_json_jason
  end

  test "unsupported purpose, missing header and every extension are signed rejections", c do
    for typ <- ["JWT", "id+jwt", "application/jwt", "workload+jwt", "AT+JWT", nil, 1] do
      reject(c, sign_raw(c, json(%{c.header | "typ" => typ}), json(c.claims)))
    end

    for field <- ["alg", "typ", "kid"] do
      reject(c, sign_raw(c, json(Map.delete(c.header, field)), json(c.claims)))
    end

    for {field, value} <- [
          {"crit", ["unknown"]},
          {"b64", false},
          {"jku", "https://attacker.invalid/keys"},
          {"x5u", "https://attacker.invalid/cert"},
          {"jwk", c.public},
          {"x5c", ["cert"]},
          {"zip", "DEF"},
          {"cty", "JWT"},
          {"unknown", true}
        ] do
      reject(c, sign_raw(c, json(Map.put(c.header, field, value)), json(c.claims)))
    end

    for kid <- ["", :binary.copy("x", 129), nil, 1, ["test-rsa"]] do
      reject(c, sign_raw(c, json(%{c.header | "kid" => kid}), json(c.claims)))
    end
  end

  test "compact binary and decoded JSON bounds reject ambiguous formats", c do
    token = sign(c)
    [header, payload, signature] = :binary.split(token, ".", [:global])

    for bad <- [
          nil,
          123,
          [],
          %{},
          "",
          "a",
          "a.b",
          "a.b.c.d",
          token <> ".",
          " " <> token,
          token <> "\n",
          "Bearer " <> token,
          header <> ".." <> signature,
          header <> "=." <> payload <> "." <> signature,
          "☃.e30.e30",
          :binary.copy("x", 4_090),
          <<255>>,
          json(%{"protected" => header, "payload" => payload})
        ] do
      reject(c, bad)
    end

    for raw <- ["[]", "null", "1", "\"string\"", "{", <<123, 255, 125>>] do
      reject(c, sign_raw(c, json(c.header), raw))
      reject(c, sign_raw(c, raw, json(c.claims)))
    end

    reject(c, sign_raw(c, :binary.copy(" ", 2_049), json(c.claims)))
    reject(c, sign(c, Map.put(c.claims, "extra", :binary.copy("x", 3_073))))
  end

  test "duplicate and escaped-equivalent JSON names fail at every nested position", c do
    raw = json(c.claims)

    for extra <- [
          ~S("sub":"different"),
          ~S("s\u0075b":"different"),
          ~S("extra":{"x":1,"x":2}),
          ~S("extra":[{"x":1,"\u0078":2}]),
          ~S("extra":{"deep":[{"leaf":{"a":1,"a":2}}]})
        ] do
      duplicate = binary_part(raw, 0, byte_size(raw) - 1) <> "," <> extra <> "}"
      token = sign(c, duplicate)
      assert {true, ^duplicate, _} = JOSE.JWS.verify_strict(c.private, ["RS256"], token)
      reject(c, token)
    end

    for raw_header <- [
          ~S({"alg":"RS256","alg":"RS256","kid":"test-rsa","typ":"at+jwt"}),
          ~S({"alg":"RS256","\u0061lg":"RS256","kid":"test-rsa","typ":"at+jwt"})
        ] do
      reject(c, sign_raw(c, raw_header, raw))
    end

    # Escapes without ambiguity are legitimate, and original bytes are signed.
    escaped = String.replace(raw, "subject-1", ~S(subject-\u0031))

    assert {:ok, %{subject: "subject-1"}} =
             AccessTokenVerifier.verify(sign(c, escaped), @now, c.snapshot)
  end

  test "structure bounds apply also to unknown signed claims", c do
    for extra <- [
          Enum.to_list(1..65),
          Map.new(1..65, &{"field-#{&1}", 1}),
          Enum.reduce(1..17, "leaf", fn _, value -> %{"nested" => value} end)
        ] do
      reject(c, sign(c, Map.put(c.claims, "extra", extra)))
    end
  end

  test "required claims and exact issuer/client bindings are enforced", c do
    for field <- ~w(iss sub aud client_id iat exp jti) do
      reject(c, sign(c, Map.delete(c.claims, field)))
      reject(c, sign(c, Map.put(c.claims, field, nil)))
    end

    for {field, value} <- [
          {"iss", "https://other.invalid"},
          {"iss", @profile.issuer <> "/"},
          {"client_id", "another-client"},
          {"sub", 1},
          {"sub", ""},
          {"sub", :binary.copy("s", 257)},
          {"jti", false},
          {"jti", ""},
          {"jti", :binary.copy("j", 257)}
        ] do
      reject(c, sign(c, Map.put(c.claims, field, value)))
    end
  end

  test "audience accepts exact strings and unique bounded arrays", c do
    for audience <- [
          @profile.audience,
          ["other-api", @profile.audience],
          Enum.map(1..7, &"api-#{&1}") ++ [@profile.audience]
        ] do
      assert {:ok, _} =
               AccessTokenVerifier.verify(
                 sign(c, %{c.claims | "aud" => audience}),
                 @now,
                 c.snapshot
               )
    end

    for audience <- [
          "another-api",
          [],
          [@profile.audience, @profile.audience],
          [@profile.audience, nil],
          [@profile.audience, ""],
          [@profile.audience, :binary.copy("a", 257)],
          [@profile.audience | Enum.map(1..8, &"api-#{&1}")],
          %{"aud" => @profile.audience},
          1
        ] do
      reject(c, sign(c, %{c.claims | "aud" => audience}))
    end
  end

  test "scope is bounded OAuth syntax and only exact supported names survive", c do
    claims =
      Map.merge(c.claims, %{
        "scope" => "owner project:* mixer.artifact.read",
        "kind" => "service",
        "organization" => "victim",
        "project" => "victim",
        "roles" => ["owner"],
        "groups" => ["admins"]
      })

    assert {:ok, identity} = AccessTokenVerifier.verify(sign(c, claims), @now, c.snapshot)
    assert identity.scopes == ["mixer.artifact.read"]
    assert identity.identity_class == :human

    refute Enum.any?(
             [:organization, :project, :roles, :groups, :token, :claims, :permissions],
             &Map.has_key?(identity, &1)
           )

    for claims <- [Map.delete(c.claims, "scope"), %{c.claims | "scope" => "owner"}] do
      assert {:ok, %{scopes: []}} = AccessTokenVerifier.verify(sign(c, claims), @now, c.snapshot)
    end

    for scope <- [
          nil,
          [],
          "",
          " ",
          " owner",
          "owner ",
          "owner  other",
          "owner\tother",
          "owner\nother",
          "owner\\other",
          "owner\"other",
          "snow☃",
          "owner owner",
          :binary.copy("a", 1_025),
          Enum.map_join(1..33, " ", &"s#{&1}")
        ] do
      reject(c, sign(c, %{c.claims | "scope" => scope}))
    end

    assert {:ok, %{scopes: []}} =
             AccessTokenVerifier.verify(
               sign(c, %{c.claims | "scope" => :binary.copy("a", 1_024)}),
               @now,
               c.snapshot
             )

    assert {:ok, _} =
             AccessTokenVerifier.verify(
               sign(c, %{c.claims | "scope" => Enum.map_join(1..32, " ", &"s#{&1}")}),
               @now,
               c.snapshot
             )
  end

  test "signed workspace scope survives exactly without granting artifact or claimed roles", c do
    for scope <- ["mixer.workspace.read", "owner mixer.workspace.read project:*"] do
      claims =
        Map.merge(c.claims, %{"scope" => scope, "roles" => ["owner"], "organization" => "other"})

      assert {:ok, %VerifiedIdentity{scopes: ["mixer.workspace.read"]} = identity} =
               AccessTokenVerifier.verify(sign(c, claims), @now, c.snapshot)

      refute Map.has_key?(identity, :roles)
      refute Map.has_key?(identity, :organization)
    end

    for scope <- [
          "mixer.workspace",
          "mixer.workspace.read.extra",
          "mixer.workspace.*",
          "MIXER.workspace.read"
        ] do
      assert {:ok, %VerifiedIdentity{scopes: []}} =
               AccessTokenVerifier.verify(
                 sign(c, %{c.claims | "scope" => scope}),
                 @now,
                 c.snapshot
               )
    end

    all = "mixer.workspace.read " <> c.claims["scope"]

    assert {:ok, %VerifiedIdentity{scopes: scopes}} =
             AccessTokenVerifier.verify(sign(c, %{c.claims | "scope" => all}), @now, c.snapshot)

    assert scopes == [
             "mixer.artifact.read",
             "mixer.artifact.upload",
             "mixer.audit.read",
             "mixer.workspace.read"
           ]

    reject(c, sign(c, %{c.claims | "scope" => "mixer.workspace.read mixer.workspace.read"}))
  end

  test "expiry is exclusive, future skew is at most 30 and times are bounded integers", c do
    for patch <- [
          %{"iat" => @now - 1, "exp" => @now},
          %{"exp" => @now - 1},
          %{"iat" => @now + 31},
          %{"nbf" => @now + 31},
          %{"nbf" => c.claims["exp"]},
          %{"iat" => -1},
          %{"exp" => -1},
          %{"nbf" => -1},
          %{"iat" => 1.8e9},
          %{"exp" => "1800000300"},
          %{"nbf" => nil},
          %{"iat" => 9_007_199_254_740_992},
          %{"exp" => 9_007_199_254_740_992},
          %{"nbf" => 9_007_199_254_740_992},
          %{"iat" => @now + 1, "exp" => @now + 1}
        ] do
      reject(c, sign(c, Map.merge(c.claims, patch)))
    end

    for patch <- [%{"exp" => @now + 1}, %{"iat" => @now + 30}, %{"nbf" => @now + 30}] do
      assert {:ok, _} =
               AccessTokenVerifier.verify(sign(c, Map.merge(c.claims, patch)), @now, c.snapshot)
    end
  end

  test "configured human and service lifetimes have exact separate ceilings", c do
    for {kind, lifetime} <- [human: 900, service: 300] do
      trust = snapshot([c.public], %{@profile | identity_class: kind})
      valid = %{c.claims | "iat" => @now, "exp" => @now + lifetime}

      assert {:ok, %{identity_class: ^kind}} =
               AccessTokenVerifier.verify(sign(c, valid), @now, trust)

      assert {:error, :unauthenticated} =
               AccessTokenVerifier.verify(
                 sign(c, %{valid | "exp" => @now + lifetime + 1}),
                 @now,
                 trust
               )
    end
  end

  test "missing, stale or future-fetched trust is unavailable; authoritative disable denies", c do
    token = sign(c)

    for trust <- [
          nil,
          :unavailable,
          %{},
          snapshot([c.public], @profile, @now - 300, @now),
          snapshot([c.public], @profile, @now + 1, @now + 2)
        ] do
      assert AccessTokenVerifier.verify(token, @now, trust) == {:error, :identity_unavailable}
    end

    for bad_now <- [-1, nil, 1.8e9, 9_007_199_254_740_992] do
      assert AccessTokenVerifier.verify(token, bad_now, c.snapshot) ==
               {:error, :identity_unavailable}
    end

    disabled = snapshot([c.public], %{@profile | enabled: false})
    assert AccessTokenVerifier.verify(token, @now, disabled) == {:error, :unauthenticated}

    assert AccessTokenVerifier.verify(token, @now + 10_000, disabled) ==
             {:error, :unauthenticated}

    assert {:ok, _} = AccessTokenVerifier.verify(token, @now - 1, c.snapshot)
  end

  test "whole-snapshot validation rejects ambiguous private weak or unsupported keys", c do
    for key <- [
          Map.put(c.public, "unknown", "value"),
          Map.put(c.public, "key_ops", nil),
          Map.put(c.public, "key_ops", ["sign"]),
          Map.put(c.public, "key_ops", ["verify", "verify"]),
          Map.put(c.public, "alg", "HS256"),
          Map.put(c.public, "use", "enc"),
          Map.put(c.public, "kty", "oct"),
          Map.put(c.public, "kid", ""),
          Map.put(c.public, "kid", :binary.copy("k", 129)),
          public(c.weak_private),
          Map.put(c.public, "e", Base.url_encode64(<<3>>, padding: false)),
          Map.put(c.public, "n", c.public["n"] <> "="),
          Map.put(
            c.public,
            "n",
            Base.url_encode64(<<0>> <> Base.url_decode64!(c.public["n"], padding: false),
              padding: false
            )
          ),
          Map.put(c.public, "n", Base.url_encode64(:binary.copy(<<255>>, 513), padding: false)),
          nil,
          [],
          "key"
        ] do
      invalid_snapshot([key])
      invalid_snapshot([c.public, key])
    end

    for field <- ~w(d p q dp dq qi oth k x y crv x5c x5u jku jwk pem) do
      invalid_snapshot([Map.put(c.public, field, "private-or-alternate-material")])
    end

    {_, private_map} = JOSE.JWK.to_map(c.private)
    invalid_snapshot([Map.merge(c.public, private_map)])
    for field <- ~w(kty alg use kid n e), do: invalid_snapshot([Map.delete(c.public, field)])
    invalid_snapshot([])
    invalid_snapshot([c.public, c.public])
    invalid_snapshot(Enum.map(1..17, &Map.put(c.public, "kid", "key-#{&1}")))

    assert {:ok, _} =
             TrustSnapshot.new(
               @profile,
               json(%{"keys" => [Map.delete(c.public, "key_ops")]}),
               @now,
               @now + 300
             )

    assert {:ok, _} =
             TrustSnapshot.new(
               @profile,
               json(%{"keys" => Enum.map(1..16, &Map.put(c.public, "kid", "key-#{&1}"))}),
               @now,
               @now + 300
             )
  end

  test "raw JWKS bounds, duplicates including escaped names and invalid profiles reject atomically",
       c do
    jwks = json(%{"keys" => [c.public]})

    for raw <- [
          "[]",
          "null",
          "{",
          nil,
          [],
          :binary.copy(" ", 262_145),
          ~S({"keys":[],"\u006beys":[]}),
          String.replace(jwks, "\"kty\":\"RSA\"", ~S("kty":"RSA","\u006bty":"RSA")),
          json(%{"keys" => [c.public], "other" => true})
        ] do
      assert TrustSnapshot.new(@profile, raw, @now, @now + 300) ==
               {:error, :invalid_trust_configuration}
    end

    for patch <- [
          %{profile_id: ""},
          %{profile_id: :binary.copy("p", 129)},
          %{profile_version: 0},
          %{profile_version: 2_147_483_648},
          %{profile_version: 1.0},
          %{issuer: "http://issuer.invalid"},
          %{issuer: "https://user:pass@issuer.invalid"},
          %{issuer: "https://issuer.invalid?x=1"},
          %{issuer: "https://issuer.invalid#fragment"},
          %{audience: ""},
          %{client_id: ""},
          %{audience: :binary.copy("a", 257)},
          %{client_id: :binary.copy("c", 257)},
          %{identity_class: :admin},
          %{enabled: nil},
          %{unknown: true}
        ] do
      invalid_snapshot([c.public], Map.merge(@profile, patch))
    end

    for field <- Map.keys(@profile), do: invalid_snapshot([c.public], Map.delete(@profile, field))

    for {fetched, fresh} <- [
          {@now, @now},
          {@now, @now + 301},
          {-1, @now},
          {@now, -1},
          {@now, 1.8e9},
          {nil, @now},
          {@now, 9_007_199_254_740_992}
        ] do
      assert TrustSnapshot.new(@profile, jwks, fetched, fresh) ==
               {:error, :invalid_trust_configuration}
    end
  end

  test "snapshot replacement is explicit and successful removal immediately excludes old key",
       c do
    new_public = public(c.wrong_private, "rotated-rsa")
    overlap = snapshot([c.public, new_public])

    rotated_token =
      sign(%{c | private: c.wrong_private}, nil, %{c.header | "kid" => "rotated-rsa"})

    old_token = sign(c)
    assert {:ok, _} = AccessTokenVerifier.verify(old_token, @now, overlap)
    assert {:ok, _} = AccessTokenVerifier.verify(rotated_token, @now, overlap)
    replacement = snapshot([new_public], %{@profile | profile_version: 2})
    assert {:error, :unauthenticated} = AccessTokenVerifier.verify(old_token, @now, replacement)

    assert {:ok, %{profile_version: 2}} =
             AccessTokenVerifier.verify(rotated_token, @now, replacement)

    invalid_snapshot([new_public, new_public])
    # Rejected construction creates no replacement, and cannot extend the old
    # caller-held snapshot beyond its original bound.
    assert {:ok, _} = AccessTokenVerifier.verify(old_token, @now, overlap)

    assert {:error, :identity_unavailable} =
             AccessTokenVerifier.verify(old_token, @now + 299, overlap)

    reject(c, sign(c, nil, %{c.header | "kid" => "unknown-rsa"}))
  end
end
