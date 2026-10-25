defmodule MixerHosted.BrowserAuth.VaultTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.Vault
  alias Vault.{Active, Key, Preauth, Sealed, Verifier}
  @error {:error, :vault_unavailable}
  @csrf Base.url_encode64(:binary.copy(<<11>>, 32), padding: false)
  @verifier Base.url_encode64(:binary.copy(<<12>>, 32), padding: false)
  @generation Base.url_encode64(:binary.copy(<<13>>, 32), padding: false)

  defp key do
    {:ok, key} = Vault.key("session-key-v1", :binary.copy(<<42>>, 32))
    key
  end

  defp session(purpose \\ :preauth) do
    base = %{
      purpose: purpose,
      browser_id: :binary.copy(<<1>>, 16),
      cookie_digest: :binary.copy(<<2>>, 32),
      csrf_digest: :crypto.hash(:sha256, @csrf),
      epoch: 1,
      revision: 2,
      generation: @generation,
      vault_generation: 3,
      config_digest: :binary.copy(<<4>>, 32),
      profile_id: "human-main",
      profile_version: 7,
      principal_id: nil,
      family_id: nil,
      credential_ref: nil,
      credential_revision: nil
    }

    if purpose == :active do
      Map.merge(base, %{
        principal_id: "person-1",
        family_id: "browser_" <> @generation,
        credential_ref: "external-jti-1",
        credential_revision: 5
      })
    else
      base
    end
  end

  defp attempt do
    Map.take(session(), [
      :browser_id,
      :cookie_digest,
      :epoch,
      :revision,
      :generation,
      :config_digest,
      :profile_id,
      :profile_version
    ])
    |> Map.merge(%{
      purpose: :attempt,
      state_digest: :binary.copy(<<5>>, 32),
      issuer: "https://id.example.test",
      client_id: "console-client",
      redirect_uri: "https://console.example.test/auth/callback",
      expires_at: 123_456
    })
  end

  defp plaintext(:preauth), do: %Preauth{csrf: @csrf}
  defp plaintext(:active), do: %Active{csrf: @csrf, access_token: "header.payload.signature"}
  defp plaintext(:attempt), do: %Verifier{verifier: @verifier}
  defp context(:attempt), do: attempt()
  defp context(purpose), do: session(purpose)

  defp flip(<<first, rest::binary>>), do: <<Bitwise.bxor(first, 1), rest::binary>>
  defp lp(bytes), do: <<byte_size(bytes)::unsigned-big-32, bytes::binary>>
  defp u64(value), do: <<value::unsigned-big-64>>

  # Test-only standard platform encryption permits authenticated malformed payloads.
  # The production module exposes no nonce injection or raw plaintext encrypt API.
  defp authenticated(context, raw) do
    key = key()
    {:ok, aad} = Vault.associated_data(key.id, context)
    iv = :binary.copy(<<9>>, 12)

    {ciphertext, tag} =
      :crypto.crypto_one_time_aead(:aes_256_gcm, key.bytes, iv, raw, aad, 16, true)

    %Sealed{version: 1, key_id: key.id, iv: iv, tag: tag, ciphertext: ciphertext}
  end

  test "exact externally supplied 256-bit key and bounded identifier" do
    assert {:ok, %Key{}} = Vault.key("a._-09AZ", :binary.copy(<<0>>, 32))
    assert {:ok, %Key{}} = Vault.key(String.duplicate("a", 128), :binary.copy(<<0>>, 32))

    for id <- [nil, "", "a/b", "secret://key", "bad\n", "é", String.duplicate("a", 129)],
        do: assert(Vault.key(id, :binary.copy(<<0>>, 32)) == @error)

    for bytes <- [nil, [], "", :binary.copy(<<0>>, 31), :binary.copy(<<0>>, 33)],
        do: assert(Vault.key("key-1", bytes) == @error)
  end

  test "preauth, active and verifier envelopes round trip independently" do
    for purpose <- [:preauth, :active, :attempt] do
      assert {:ok, sealed} = Vault.seal(key(), context(purpose), plaintext(purpose))
      assert sealed.version == 1
      assert byte_size(sealed.iv) == 12
      assert byte_size(sealed.tag) == 16
      assert byte_size(sealed.ciphertext) <= 8192
      assert {:ok, result} = Vault.open(key(), context(purpose), sealed)
      assert result == plaintext(purpose)
      refute :binary.match(sealed.ciphertext, @csrf) != :nomatch
    end
  end

  test "every encryption generates an independent IV including different purposes" do
    values =
      for index <- 1..96 do
        purpose = Enum.at([:preauth, :active, :attempt], rem(index, 3))
        {:ok, sealed} = Vault.seal(key(), context(purpose), plaintext(purpose))
        sealed.iv
      end

    assert length(Enum.uniq(values)) == 96
    refute function_exported?(Vault, :seal, 4)
  end

  test "raw 32-byte digests differ from wire canonical43 and browser ID is exactly16 bytes" do
    for field <- [:cookie_digest, :csrf_digest, :config_digest] do
      assert Vault.seal(key(), Map.put(session(), field, @generation), plaintext(:preauth)) ==
               @error
    end

    assert Vault.seal(key(), Map.put(session(), :browser_id, @generation), plaintext(:preauth)) ==
             @error

    assert Vault.seal(key(), Map.put(attempt(), :state_digest, @generation), plaintext(:attempt)) ==
             @error
  end

  test "AAD is independently specified length-prefixed and ordered for preauth" do
    c = session()

    expected =
      "mixer.browser.vault.v1\0" <>
        IO.iodata_to_binary(
          Enum.map(
            [
              <<1>>,
              "session-key-v1",
              <<1>>,
              c.browser_id,
              c.cookie_digest,
              c.csrf_digest,
              u64(c.epoch),
              u64(c.revision),
              c.generation,
              u64(c.vault_generation),
              c.config_digest,
              c.profile_id,
              u64(c.profile_version),
              <<0>>
            ],
            &lp/1
          )
        )

    assert Vault.associated_data("session-key-v1", c) == {:ok, expected}
  end

  test "AAD is independently specified for active exact linkage and attempt" do
    c = session(:active)

    expected =
      "mixer.browser.vault.v1\0" <>
        IO.iodata_to_binary(
          Enum.map(
            [
              <<1>>,
              "session-key-v1",
              <<2>>,
              c.browser_id,
              c.cookie_digest,
              c.csrf_digest,
              u64(c.epoch),
              u64(c.revision),
              c.generation,
              u64(c.vault_generation),
              c.config_digest,
              c.profile_id,
              u64(c.profile_version),
              <<1>>,
              c.principal_id,
              c.family_id,
              c.credential_ref,
              u64(c.credential_revision)
            ],
            &lp/1
          )
        )

    assert Vault.associated_data("session-key-v1", c) == {:ok, expected}
    c = attempt()

    expected =
      "mixer.browser.attempt.v1\0" <>
        IO.iodata_to_binary(
          Enum.map(
            [
              <<1>>,
              "session-key-v1",
              <<3>>,
              c.state_digest,
              c.browser_id,
              c.cookie_digest,
              u64(c.epoch),
              u64(c.revision),
              c.generation,
              c.config_digest,
              c.profile_id,
              u64(c.profile_version),
              c.issuer,
              c.client_id,
              c.redirect_uri,
              u64(c.expires_at)
            ],
            &lp/1
          )
        )

    assert Vault.associated_data("session-key-v1", c) == {:ok, expected}
  end

  test "every current session field including authz linkage is authenticated" do
    for purpose <- [:preauth, :active] do
      c = context(purpose)
      {:ok, sealed} = Vault.seal(key(), c, plaintext(purpose))

      for {field, value} <- c, field != :purpose do
        changed =
          case value do
            nil ->
              "foreign"

            value when is_integer(value) ->
              value + 1

            _value when field == :generation ->
              Base.url_encode64(:binary.copy(<<14>>, 32), padding: false)

            value when is_binary(value) ->
              flip(value)
          end

        assert Vault.open(key(), Map.put(c, field, changed), sealed) == @error,
               "changed field: #{field}"
      end

      other = if purpose == :preauth, do: :active, else: :preauth
      assert Vault.open(key(), context(other), sealed) == @error
    end
  end

  test "every current attempt field is authenticated" do
    c = attempt()
    {:ok, sealed} = Vault.seal(key(), c, plaintext(:attempt))

    for {field, value} <- c, field != :purpose do
      changed =
        case value do
          value when is_integer(value) ->
            value + 1

          _value when field == :generation ->
            Base.url_encode64(:binary.copy(<<15>>, 32), padding: false)

          value when is_binary(value) ->
            flip(value)
        end

      assert Vault.open(key(), Map.put(c, field, changed), sealed) == @error,
             "changed field: #{field}"
    end

    assert Vault.open(key(), session(), sealed) == @error
    {:ok, session_sealed} = Vault.seal(key(), session(), plaintext(:preauth))
    assert Vault.open(key(), attempt(), session_sealed) == @error
  end

  test "wrong key material and key version including same bytes under another ID deny" do
    {:ok, sealed} = Vault.seal(key(), session(), plaintext(:preauth))
    {:ok, other_material} = Vault.key(key().id, :binary.copy(<<43>>, 32))
    {:ok, other_version} = Vault.key("session-key-v2", key().bytes)
    assert Vault.open(other_material, session(), sealed) == @error
    assert Vault.open(other_version, session(), sealed) == @error
    assert Vault.open(other_version, session(), %{sealed | key_id: other_version.id}) == @error
  end

  test "ciphertext IV and full16-byte tag are authenticated" do
    {:ok, sealed} = Vault.seal(key(), session(), plaintext(:preauth))

    for tampered <- [
          %{sealed | iv: flip(sealed.iv)},
          %{sealed | tag: flip(sealed.tag)},
          %{sealed | ciphertext: flip(sealed.ciphertext)}
        ] do
      assert Vault.open(key(), session(), tampered) == @error
    end

    assert Vault.open(key(), session(), %{sealed | tag: binary_part(sealed.tag, 0, 15)}) == @error
    assert Vault.open(key(), session(), %{sealed | iv: sealed.iv <> <<0>>}) == @error

    assert Vault.open(key(), session(), %{sealed | ciphertext: sealed.ciphertext <> <<0>>}) ==
             @error
  end

  test "unknown or malformed stored fields and ciphertext bounds deny" do
    {:ok, sealed} = Vault.seal(key(), session(), plaintext(:preauth))

    for field <- [:version, :key_id, :iv, :tag, :ciphertext], value <- [nil, 0, [], %{}] do
      assert Vault.open(key(), session(), Map.put(sealed, field, value)) == @error
    end

    for value <- [
          nil,
          %{},
          Map.from_struct(sealed),
          Map.put(sealed, :extra, "secret"),
          %{sealed | version: 2},
          %{sealed | ciphertext: ""},
          %{sealed | ciphertext: :binary.copy(<<0>>, 8193)}
        ] do
      assert Vault.open(key(), session(), value) == @error
    end
  end

  test "closed context rejects unknown missing string and malformed keys" do
    for purpose <- [:preauth, :active, :attempt] do
      c = context(purpose)

      for field <- Map.keys(c) do
        assert Vault.seal(key(), Map.delete(c, field), plaintext(purpose)) == @error
      end

      for value <- [
            nil,
            [],
            Map.put(c, :extra, true),
            Map.new(c, fn {k, v} -> {Atom.to_string(k), v} end)
          ] do
        assert Vault.seal(key(), value, plaintext(purpose)) == @error
      end
    end
  end

  test "positive bounded integers and SQL profile version compatibility" do
    for purpose <- [:preauth, :active, :attempt] do
      c = context(purpose)
      fields = Enum.filter(Map.keys(c), &is_integer(c[&1]))

      for field <- fields, value <- [-1, 0, 1.0, "1", 9_007_199_254_740_992] do
        assert Vault.seal(key(), Map.put(c, field, value), plaintext(purpose)) == @error
      end

      assert Vault.seal(key(), Map.put(c, :profile_version, 2_147_483_648), plaintext(purpose)) ==
               @error
    end

    c = %{session() | epoch: 9_007_199_254_740_991, profile_version: 2_147_483_647}
    assert {:ok, _} = Vault.seal(key(), c, plaintext(:preauth))
  end

  test "identity bounds use exact UTF8 with no NUL and preserve byte distinctions" do
    c = session(:active)

    for {field, limit} <- [
          profile_id: 128,
          principal_id: 128,
          family_id: 128,
          credential_ref: 256
        ] do
      assert {:ok, _} =
               Vault.seal(
                 key(),
                 Map.put(c, field, String.duplicate("a", limit)),
                 plaintext(:active)
               )

      for value <- ["", <<255>>, "a\0b", String.duplicate("a", limit + 1)] do
        assert Vault.seal(key(), Map.put(c, field, value), plaintext(:active)) == @error
      end
    end

    for {field, limit} <- [issuer: 2048, client_id: 256, redirect_uri: 2048] do
      assert {:ok, _} =
               Vault.seal(
                 key(),
                 Map.put(attempt(), field, String.duplicate("a", limit)),
                 plaintext(:attempt)
               )

      assert Vault.seal(
               key(),
               Map.put(attempt(), field, String.duplicate("a", limit + 1)),
               plaintext(:attempt)
             ) == @error
    end

    {:ok, first} = Vault.associated_data(key().id, %{c | principal_id: "ab", family_id: "c"})
    {:ok, second} = Vault.associated_data(key().id, %{c | principal_id: "a", family_id: "bc"})
    refute first == second
  end

  test "preauth must have no linkage and active requires complete linkage" do
    for field <- [:principal_id, :family_id, :credential_ref, :credential_revision] do
      assert Vault.seal(
               key(),
               Map.put(session(), field, session(:active)[field]),
               plaintext(:preauth)
             ) == @error

      assert Vault.seal(key(), Map.put(session(:active), field, nil), plaintext(:active)) ==
               @error
    end
  end

  test "typed envelopes reject other kinds arbitrary maps extra fields refresh and ID tokens" do
    for purpose <- [:preauth, :active, :attempt] do
      for other <- [:preauth, :active, :attempt], purpose != other do
        assert Vault.seal(key(), context(purpose), plaintext(other)) == @error
      end

      for bad <- [
            nil,
            [],
            Map.from_struct(plaintext(purpose)),
            Map.put(plaintext(purpose), :refresh_token, "private"),
            Map.put(plaintext(purpose), :id_token, "private")
          ] do
        assert Vault.seal(key(), context(purpose), bad) == @error
      end
    end
  end

  test "CSRF must match canonical32-byte token and independent digest both directions" do
    for csrf <- [
          nil,
          "",
          String.duplicate("A", 42),
          String.duplicate("A", 44),
          String.duplicate("A", 42) <> "B",
          @verifier
        ] do
      assert Vault.seal(key(), session(), %Preauth{csrf: csrf}) == @error
    end

    raw = <<1, 43::unsigned-big-32, @verifier::binary>>
    assert Vault.open(key(), session(), authenticated(session(), raw)) == @error
    raw = <<1, 43::unsigned-big-32, String.duplicate("A", 42) <> "B"::binary>>
    assert Vault.open(key(), session(), authenticated(session(), raw)) == @error
  end

  test "PKCE verifier and generation reject noncanonical aliases" do
    for value <- [nil, "", String.duplicate("A", 42) <> "B", @verifier <> "="] do
      assert Vault.seal(key(), attempt(), %Verifier{verifier: value}) == @error
      assert Vault.seal(key(), %{session() | generation: value}, plaintext(:preauth)) == @error
    end
  end

  test "access token bounded at4089 bytes and never acts as authentication" do
    c = session(:active)

    assert {:ok, sealed} =
             Vault.seal(key(), c, %Active{csrf: @csrf, access_token: String.duplicate("a", 4089)})

    assert byte_size(sealed.ciphertext) == 4141
    assert {:ok, %Active{access_token: token}} = Vault.open(key(), c, sealed)
    assert byte_size(token) == 4089
    assert {:ok, _} = Vault.seal(key(), c, %Active{csrf: @csrf, access_token: "AZaz09._~+/-=="})

    for token <- [nil, "", String.duplicate("a", 4090), "a b", "a\nb", "a?b", "a=b", "=", <<255>>] do
      assert Vault.seal(key(), c, %Active{csrf: @csrf, access_token: token}) == @error
    end
  end

  test "authenticated unknown kind trailing bytes and incorrect length encodings deny" do
    values = [
      <<>>,
      <<0>>,
      <<4>>,
      <<1, 0, 0, 0, 0>>,
      <<1, 0, 0, 0, 44, @csrf::binary>>,
      <<1, 0, 0, 0, 43, @csrf::binary, 0>>,
      <<3, 0, 0, 0, 43, @verifier::binary>>,
      <<1, 0, 0, 0, 43, @csrf::binary, 0, 0, 0, 1, 1>>
    ]

    for value <- values do
      assert Vault.open(key(), session(), authenticated(session(), value)) == @error
    end

    active = <<2, 0, 0, 0, 43, @csrf::binary, 0, 0, 0, 1, ?a>>

    assert Vault.open(key(), session(:active), authenticated(session(:active), active <> <<0>>)) ==
             @error

    assert Vault.open(
             key(),
             session(:active),
             authenticated(session(:active), <<2, 0, 0, 0, 43, @csrf::binary, 0xFFFFFFFF::32>>)
           ) == @error

    assert Vault.open(
             key(),
             attempt(),
             authenticated(attempt(), <<3, 0, 0, 0, 43, @verifier::binary, 0>>)
           ) == @error
  end

  test "oversized but authenticated plaintext remains unavailable" do
    raw = <<2, 43::32, @csrf::binary, 4090::32, String.duplicate("a", 4090)::binary>>
    assert Vault.open(key(), session(:active), authenticated(session(:active), raw)) == @error

    assert Vault.open(key(), session(), authenticated(session(), :binary.copy(<<1>>, 8192))) ==
             @error
  end

  test "Inspect hides key plaintext ciphertext IV and tag even nested" do
    {:ok, sealed} = Vault.seal(key(), session(), plaintext(:preauth))
    assert inspect(key()) == "#MixerHosted.BrowserAuth.Vault.Key<...>"
    assert inspect(plaintext(:preauth)) == "#MixerHosted.BrowserAuth.Vault.Preauth<...>"
    assert inspect(plaintext(:active)) == "#MixerHosted.BrowserAuth.Vault.Active<...>"
    assert inspect(plaintext(:attempt)) == "#MixerHosted.BrowserAuth.Vault.Verifier<...>"
    rendered = inspect(%{key: key(), values: [plaintext(:active), plaintext(:attempt), sealed]})

    for private <- [
          @csrf,
          @verifier,
          "header.payload.signature",
          "session-key-v1",
          inspect(sealed.iv),
          inspect(sealed.tag)
        ],
        do: refute(String.contains?(rendered, private))
  end

  test "all public malformed key errors are fixed without private text" do
    for bad <- [
          nil,
          %{},
          Map.from_struct(key()),
          Map.put(key(), :extra, "private"),
          %{key() | bytes: "private"}
        ] do
      assert Vault.seal(bad, session(), plaintext(:preauth)) == @error
      assert Vault.open(bad, session(), nil) == @error
    end

    assert Vault.associated_data("private/unsafe", session()) == @error
  end

  test "platform AES256GCM known answer zero key IV and128-bit plaintext" do
    {ciphertext, tag} =
      :crypto.crypto_one_time_aead(:aes_256_gcm, <<0::256>>, <<0::96>>, <<0::128>>, "", 16, true)

    assert Base.encode16(ciphertext, case: :lower) == "cea7403d4d606b6e074ec5d3baf39d18"
    assert Base.encode16(tag, case: :lower) == "d0d1c8a799996bf0265b98b5d48ab919"

    assert :crypto.crypto_one_time_aead(
             :aes_256_gcm,
             <<0::256>>,
             <<0::96>>,
             ciphertext,
             "",
             tag,
             false
           ) == <<0::128>>
  end

  test "official NIST AES256GCM example4 authenticates nonempty plaintext and AAD" do
    key =
      Base.decode16!("feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308",
        case: :lower
      )

    iv = Base.decode16!("cafebabefacedbaddecaf888", case: :lower)

    aad =
      Base.decode16!(
        "3ad77bb40d7a3660a89ecaf32466ef97f5d3d58503b9699de785895a96fdbaaf43b1cd7f598ece23881b00e3ed0306887b0c785e27e8ad3f8223207104725dd4",
        case: :lower
      )

    plaintext =
      Base.decode16!(
        "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255",
        case: :lower
      )

    ciphertext =
      Base.decode16!(
        "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662898015ad",
        case: :lower
      )

    tag = Base.decode16!("c06d76f31930fef37acae23ed465ae62", case: :lower)

    assert :crypto.crypto_one_time_aead(:aes_256_gcm, key, iv, plaintext, aad, 16, true) ==
             {ciphertext, tag}

    assert :crypto.crypto_one_time_aead(:aes_256_gcm, key, iv, ciphertext, aad, tag, false) ==
             plaintext

    assert :crypto.crypto_one_time_aead(:aes_256_gcm, key, iv, ciphertext, flip(aad), tag, false) ==
             :error
  end
end
