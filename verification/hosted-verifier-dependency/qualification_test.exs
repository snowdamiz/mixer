# Standalone dependency qualification, not hosted product code or a provider receipt.
ExUnit.start(seed: 0)
JOSE.crypto_fallback(false)
JOSE.unsecured_signing(false)
JOSE.json_module(:jose_json_jason)

defmodule DependencyQualification.VerifiedIdentity do
  @enforce_keys [:profile_id, :profile_version, :issuer, :subject, :client_id, :credential_ref,
                 :issued_at, :expires_at, :identity_class, :scopes]
  defstruct @enforce_keys
end

defmodule DependencyQualification do
  @moduledoc false
  @issuer "https://issuer.invalid"
  @audience "mixer-api"
  @client "registered-client"
  @scopes ["mixer.artifact.read", "mixer.artifact.upload", "mixer.audit.read"]

  def verify(token, keys, now) do
    try do
      # HTTP owner separately bounds the full "Bearer " authorization value at 4096.
      ensure(is_binary(token) and byte_size(token) <= 4_089, :size)
      [header_segment, payload_segment, signature_segment] = String.split(token, ".")
      header = header_segment |> decode64(2_048) |> json()
      payload = decode64(payload_segment, 3_072)
      _signature = decode64(signature_segment, 512)
      ensure(Map.keys(header) |> Enum.all?(&(&1 in ["alg", "kid", "typ"])), :header)
      ensure(header["alg"] == "RS256", :algorithm)
      ensure(header["typ"] in ["at+jwt", "application/at+jwt"], :purpose)
      bounded_string(header["kid"], 128)
      claims = json(payload)
      ensure(is_list(keys) and length(keys) in 1..16, :key_set)
      ensure(Enum.uniq_by(keys, & &1["kid"]) == keys, :ambiguous_key)
      Enum.each(keys, &validate_key/1)
      selected = Enum.filter(keys, &(&1["kid"] == header["kid"]))
      ensure(length(selected) == 1, :unknown_key)
      [key] = selected
      validate_key(key)
      {true, ^payload, _jws} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(key), ["RS256"], token)
      validate_claims(claims, now)
      scopes = scope(claims["scope"])
      {:ok, struct!(DependencyQualification.VerifiedIdentity,
        profile_id: "synthetic-rfc9068-rs256-v1", profile_version: 1,
        issuer: @issuer, subject: claims["sub"], client_id: @client,
        credential_ref: claims["jti"], issued_at: claims["iat"],
        expires_at: claims["exp"], identity_class: :human, scopes: scopes)}
    rescue
      _ -> {:error, :unauthenticated}
    catch
      {:reject, reason} -> {:error, reason}
    end
  end

  def json(raw) do
    ensure(is_binary(raw) and byte_size(raw) <= 12_288, :json_size)
    decoded = Jason.decode!(raw, objects: :ordered_objects, keys: :strings, strings: :copy)
    ensure(match?(%Jason.OrderedObject{}, decoded), :json_object)
    unique(decoded, 0)
  end

  defp unique(%Jason.OrderedObject{values: pairs}, depth) do
    ensure(depth <= 16 and length(pairs) <= 64, :json_complexity)
    names = Enum.map(pairs, &elem(&1, 0))
    ensure(length(Enum.uniq(names)) == length(names), :duplicate_json_member)
    Map.new(pairs, fn {key, value} -> {key, unique(value, depth + 1)} end)
  end
  defp unique(list, depth) when is_list(list) do
    ensure(depth <= 16 and length(list) <= 64, :json_complexity)
    Enum.map(list, &unique(&1, depth + 1))
  end
  defp unique(value, _), do: value

  defp decode64(segment, max) do
    ensure(is_binary(segment) and byte_size(segment) > 0, :base64)
    decoded = Base.url_decode64!(segment, padding: false)
    ensure(byte_size(decoded) <= max and Base.url_encode64(decoded, padding: false) == segment,
      :base64)
    decoded
  end

  defp validate_key(key) do
    bounded_string(key["kid"], 128)
    ensure(key["kty"] == "RSA" and key["alg"] == "RS256" and key["use"] == "sig", :key_type)
    ensure(key["key_ops"] in [nil, ["verify"]], :key_ops)
    ensure(Map.keys(key) |> Enum.all?(&(&1 in ["kty", "alg", "use", "key_ops", "kid", "n", "e"])),
      :key_fields)
    modulus = decode64(key["n"], 512)
    ensure(byte_size(modulus) in 256..512 and :binary.first(modulus) >= 128, :rsa_size)
    ensure(decode64(key["e"], 4) == <<1, 0, 1>>, :rsa_exponent)
  end

  defp validate_claims(claims, now) do
    ensure(claims["iss"] == @issuer and claims["client_id"] == @client, :issuer_client)
    bounded_string(claims["sub"], 256)
    bounded_string(claims["jti"], 256)
    audience = claims["aud"]
    ensure(audience == @audience or
      (is_list(audience) and length(audience) in 1..8 and @audience in audience and
       Enum.all?(audience, &(is_binary(&1) and byte_size(&1) in 1..256)) and
       Enum.uniq(audience) == audience), :audience)
    issued = claims["iat"]
    expiry = claims["exp"]
    ensure(is_integer(issued) and is_integer(expiry), :time_type)
    ensure(issued >= 0 and issued < expiry and expiry - issued <= 600, :lifetime)
    ensure(expiry > now and issued <= now + 30, :time)
    if Map.has_key?(claims, "nbf") do
      not_before = claims["nbf"]
      ensure(is_integer(not_before) and not_before >= 0 and not_before < expiry and
             not_before <= now + 30, :not_before)
    end
  end

  defp scope(nil), do: []
  defp scope(value) do
    ensure(is_binary(value) and byte_size(value) in 1..1_024, :scope)
    words = String.split(value, " ")
    ensure(length(words) <= 32 and Enum.all?(words, fn word ->
      byte_size(word) > 0 and Enum.all?(:binary.bin_to_list(word), &(&1 == 33 or &1 in 35..91 or &1 in 93..126))
    end), :scope)
    Enum.filter(@scopes, &(&1 in words))
  end

  defp bounded_string(value, max) do
    ensure(is_binary(value) and byte_size(value) in 1..max and String.valid?(value), :string)
  end
  defp ensure(true, _), do: :ok
  defp ensure(_, reason), do: throw({:reject, reason})
end

defmodule DependencyQualificationTest do
  use ExUnit.Case, async: false
  alias DependencyQualification, as: Q
  @now 1_800_000_000

  setup_all do
    private = JOSE.JWK.generate_key({:rsa, 2_048})
    {:ok, private: private, public: public(private),
      header: %{"alg" => "RS256", "kid" => "synthetic-rsa", "typ" => "at+jwt"},
      claims: %{"iss" => "https://issuer.invalid", "aud" => "mixer-api", "sub" => "subject-1",
        "client_id" => "registered-client", "iat" => @now - 1, "exp" => @now + 299,
        "jti" => "token-1", "scope" => "mixer.artifact.read mixer.artifact.upload mixer.audit.read"}}
  end

  defp public(private) do
    private |> JOSE.JWK.to_public() |> JOSE.JWK.to_map() |> elem(1)
    |> Map.merge(%{"kid" => "synthetic-rsa", "alg" => "RS256", "use" => "sig", "key_ops" => ["verify"]})
  end
  defp sign(context, claims \\ nil, header \\ nil) do
    raw_payload = if is_binary(claims), do: claims, else: Jason.encode!(claims || context.claims)
    JOSE.JWS.sign(context.private, raw_payload, header || context.header)
    |> JOSE.JWS.compact() |> elem(1)
  end
  defp sign_raw_header(context, header) do
    input = Base.url_encode64(header, padding: false) <> "." <>
      Base.url_encode64(Jason.encode!(context.claims), padding: false)
    {_modules, private_key} = JOSE.JWK.to_key(context.private)
    signature = :public_key.sign(input, :sha256, private_key)
    input <> "." <> Base.url_encode64(signature, padding: false)
  end
  defp reject(token, public), do: assert(match?({:error, _}, Q.verify(token, [public], @now)))

  test "RS256 signature and both RFC9068 type spellings succeed with bounded identity", c do
    for typ <- ["at+jwt", "application/at+jwt"] do
      assert {:ok, identity} = Q.verify(sign(c, nil, %{c.header | "typ" => typ}), [c.public], @now)
      assert identity.subject == "subject-1"
      assert identity.identity_class == :human
      assert identity.profile_id == "synthetic-rfc9068-rs256-v1"
      assert identity.profile_version == 1
      assert identity.credential_ref == "token-1"
      refute Enum.any?([:organization, :project, :role, :permissions, :claims, :token],
        &Map.has_key?(identity, &1))
    end
  end

  test "forged authority claims are ignored and identity class is configured", c do
    claims = Map.merge(c.claims, %{"organization" => "victim", "project" => "victim", "roles" => ["owner"],
      "kind" => "service", "scope" => "owner project:* mixer.artifact.read"})
    assert {:ok, identity} = Q.verify(sign(c, claims), [c.public], @now)
    assert identity.identity_class == :human
    assert identity.scopes == ["mixer.artifact.read"]
  end

  test "missing scope supplies no grants", c do
    assert {:ok, identity} = Q.verify(sign(c, Map.delete(c.claims, "scope")), [c.public], @now)
    assert identity.scopes == []
  end

  test "tampered payload and signature fail", c do
    [header, payload, signature] = String.split(sign(c), ".")
    changed = Jason.encode!(%{c.claims | "sub" => "attacker"}) |> Base.url_encode64(padding: false)
    reject(Enum.join([header, changed, signature], "."), c.public)
    raw_sig = Base.url_decode64!(signature, padding: false)
    <<byte, rest::binary>> = raw_sig
    altered = Base.url_encode64(<<Bitwise.bxor(byte, 1), rest::binary>>, padding: false)
    reject(Enum.join([header, payload, altered], "."), c.public)
  end

  test "wrong RSA key and wrong key type fail", c do
    token = sign(c)
    reject(token, public(JOSE.JWK.generate_key({:rsa, 2_048})))
    ec = JOSE.JWK.generate_key({:ec, :secp256r1}) |> JOSE.JWK.to_public() |> JOSE.JWK.to_map() |> elem(1)
    reject(token, Map.merge(ec, Map.take(c.public, ["kid", "alg", "use"])))
  end

  test "none and token-selected algorithms cannot widen RS256 profile", c do
    none = Base.url_encode64(Jason.encode!(%{c.header | "alg" => "none"}), padding: false) <> "." <>
      Base.url_encode64(Jason.encode!(c.claims), padding: false) <> "."
    reject(none, c.public)
    for alg <- ["RS512", "PS256"] do
      token = sign(c, nil, %{c.header | "alg" => alg})
      assert {true, _, _} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(c.public), [alg], token)
      reject(token, c.public)
    end
  end

  test "HMAC using public RSA PEM cannot become an RSA verifier", c do
    pem = JOSE.JWK.from_map(c.public) |> JOSE.JWK.to_pem() |> elem(1)
    oct = JOSE.JWK.from_oct(pem)
    token = JOSE.JWS.sign(oct, Jason.encode!(c.claims), %{c.header | "alg" => "HS256"})
      |> JOSE.JWS.compact() |> elem(1)
    assert {true, _, _} = JOSE.JWS.verify_strict(oct, ["HS256"], token)
    assert {false, _, _} = JOSE.JWS.verify_strict(oct, ["RS256"], token)
    reject(token, c.public)
  end

  test "native EC and EdDSA verify as library capabilities but fail fixed profile", c do
    for {alg, spec} <- [{"ES256", {:ec, :secp256r1}}, {"EdDSA", {:okp, :Ed25519}}] do
      private = JOSE.JWK.generate_key(spec)
      token = JOSE.JWS.sign(private, Jason.encode!(c.claims), %{c.header | "alg" => alg})
        |> JOSE.JWS.compact() |> elem(1)
      assert {true, _, _} = JOSE.JWS.verify_strict(JOSE.JWK.to_public(private), [alg], token)
      reject(token, c.public)
    end
    refute JOSE.crypto_fallback()
  end

  test "unknown and duplicate kids fail rather than trying every key", c do
    reject(sign(c, nil, %{c.header | "kid" => "unregistered"}), c.public)
    assert {:error, :ambiguous_key} = Q.verify(sign(c), [c.public, c.public], @now)
    assert {:error, :key_set} = Q.verify(sign(c), List.duplicate(c.public, 17), @now)
  end

  test "JWK metadata, weak RSA and private material fail closed", c do
    for patch <- [%{"alg" => "HS256"}, %{"use" => "enc"}, %{"key_ops" => ["sign"]},
                  %{"e" => "Aw"}, %{"d" => "forbidden"}, %{"x5u" => "https://attacker.invalid"},
                  %{"n" => Base.url_encode64(:binary.copy(<<255>>, 128), padding: false)}] do
      reject(sign(c), Map.merge(c.public, patch))
    end
  end

  test "RSA supported maximum works; genuinely signed 1024-bit RSA is rejected", c do
    for {bits, outcome} <- [{4_096, :accept}, {1_024, :reject}] do
      private = JOSE.JWK.generate_key({:rsa, bits})
      key = public(private)
      token = sign(%{c | private: private})
      assert {true, _, _} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(key), ["RS256"], token)
      case outcome do
        :accept -> assert {:ok, _} = Q.verify(token, [key], @now)
        :reject -> assert {:error, :rsa_size} = Q.verify(token, [key], @now)
      end
    end
  end

  test "raw strict signature verification accepts claims it does not validate", c do
    claims = %{c.claims | "iss" => "https://wrong.invalid", "exp" => @now}
    token = sign(c, claims)
    assert {true, payload, _} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(c.public), ["RS256"], token)
    assert Jason.decode!(payload)["exp"] == @now
    reject(token, c.public)
  end

  test "exact issuer, audience, registered client, required claims and time bounds", c do
    for field <- ["iss", "aud", "sub", "client_id", "iat", "exp", "jti"] do
      reject(sign(c, Map.delete(c.claims, field)), c.public)
    end
    for patch <- [%{"iss" => "https://issuer.invalid/"}, %{"client_id" => "other-client"},
      %{"aud" => "other-api"}, %{"aud" => ["mixer-api", "mixer-api"]}, %{"sub" => ""},
      %{"jti" => ""}, %{"iat" => @now + 31}, %{"nbf" => @now + 31},
      %{"exp" => @now}, %{"exp" => @now - 1}, %{"exp" => @now + 600},
      %{"iat" => 1.8e9}, %{"exp" => "1800000300"}] do
      reject(sign(c, Map.merge(c.claims, patch)), c.public)
    end
    assert {:ok, _} = Q.verify(sign(c, %{c.claims | "aud" => ["other-api", "mixer-api"]}), [c.public], @now)
    assert {:ok, _} = Q.verify(sign(c, Map.put(c.claims, "nbf", @now + 30)), [c.public], @now)
  end

  test "ID token and workload token purpose substitution fails", c do
    for typ <- ["JWT", "id+jwt", "github-actions+jwt", "AT+JWT", nil] do
      reject(sign(c, nil, Map.put(c.header, "typ", typ)), c.public)
    end
  end

  test "signed unsupported critical and key URL headers are rejected by preflight", c do
    for patch <- [%{"crit" => ["custom"], "custom" => true}, %{"crit" => []},
      %{"jku" => "https://attacker.invalid/keys"}, %{"x5u" => "https://attacker.invalid/cert"},
      %{"jwk" => c.public}, %{"x5c" => ["ignored"]}, %{"zip" => "DEF"}] do
      token = sign(c, nil, Map.merge(c.header, patch))
      assert {true, _, _} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(c.public), ["RS256"], token)
      assert {:error, :header} = Q.verify(token, [c.public], @now)
    end
  end

  test "duplicate and escaped-equivalent JSON names remain detectable before maps", c do
    for raw <- [~s({"sub":"first","sub":"last"}),
      ~S({"sub":"first","\u0073ub":"last"}),
      ~S({"extra":{"a":1,"\u0061":2}})] do
      token = sign(c, raw)
      assert {true, ^raw, _} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(c.public), ["RS256"], token)
      assert {:error, :duplicate_json_member} = Q.verify(token, [c.public], @now)
    end
    assert Jason.decode!(~s({"sub":"first","sub":"last"}))["sub"] == "first"
    for repeated_alg <- ["RS256", "HS256"] do
      raw = ~S({"alg":"RS256","\u0061lg":") <> repeated_alg <>
        ~S(","kid":"synthetic-rsa","typ":"at+jwt"})
      token = sign_raw_header(c, raw)
      assert {true, _, _} = JOSE.JWS.verify_strict(JOSE.JWK.from_map(c.public), ["RS256"], token)
      assert {:error, :duplicate_json_member} = Q.verify(token, [c.public], @now)
    end
  end

  test "same ordered JSON strategy rejects escaped duplicate JWKS members" do
    raw = ~S({"keys":[{"kid":"a","\u006bid":"b","kty":"RSA"}]})
    assert catch_throw(Q.json(raw)) == {:reject, :duplicate_json_member}
  end

  test "atomic key snapshot validation rejects even unselected malformed keys", c do
    invalid = %{c.public | "kid" => "other", "use" => "enc"}
    assert {:error, :key_type} = Q.verify(sign(c), [c.public, invalid], @now)
    replacement = public(JOSE.JWK.generate_key({:rsa, 2_048})) |> Map.put("kid", "new-key")
    assert {:ok, _} = Q.verify(sign(c), [c.public, replacement], @now)
    assert {:error, :unknown_key} = Q.verify(sign(c), [replacement], @now)
  end

  test "malformed JSON and unsupported JSON roots fail with valid signatures", c do
    for raw <- ["{", "[]", "null", "true", ~S({"sub":"\uD800"}), <<123, 34, 255, 34, 58, 49, 125>>] do
      reject(sign(c, raw), c.public)
    end
    reject(sign_raw_header(c, "{"), c.public)
    reject(sign_raw_header(c, "[]"), c.public)
  end

  test "bounded canonical compact form excludes padding, detached and JSON serialization", c do
    token = sign(c)
    [header, payload, signature] = String.split(token, ".")
    for invalid <- ["", "x", "a.b", "a.b.c.d", token <> ".", header <> "=." <> payload <> "." <> signature,
      header <> ".." <> signature, " " <> token, token <> "\n", "☃.e30.e30",
      Jason.encode!(%{"protected" => header, "payload" => payload, "signature" => signature}),
      :binary.copy("x", 4_090)] do
      reject(invalid, c.public)
    end
    unencoded = sign(c, nil, Map.put(c.header, "b64", false))
    reject(unencoded, c.public)
  end

  test "oversized and structurally excessive JSON is rejected", c do
    reject(sign(c, Map.put(c.claims, "extra", :binary.copy("a", 12_289))), c.public)
    nested = Enum.reduce(1..18, "leaf", fn _, value -> %{"a" => value} end)
    reject(sign(c, Map.put(c.claims, "extra", nested)), c.public)
    reject(sign(c, Map.put(c.claims, "extra", Enum.to_list(1..65))), c.public)
    reject(sign(c, Map.put(c.claims, "scope", "mixer.artifact.read  owner")), c.public)
  end
end
