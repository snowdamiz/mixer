defmodule MixerBrowserVaultDigestIndependentReview do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest, Vault}
  alias Vault.{Active, Preauth, Sealed, Verifier}
  @error {:error, :vault_unavailable}
  @fixture Jason.decode!(File.read!(System.fetch_env!("BROWSER_REVIEW_FIXTURE")))
  @raw ~w(browser_id cookie_digest csrf_digest config_digest state_digest)
  @fields ~w(mode public_origin profile_id profile_version issuer client_id api_audience authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri client_auth_method client_credential_ref session_vault_ref scope response_mode response_iss_required transaction_seconds session_idle_seconds return_path failure_path)

  defp key do
    {:ok, key} = Vault.key(@fixture["key"]["id"], Base.decode64!(@fixture["key"]["bytes"]))
    key
  end

  defp context(purpose) do
    @fixture["contexts"]
    |> Enum.find(&(&1["purpose"] == purpose))
    |> Map.new(fn {k, v} ->
      value =
        cond do
          k in @raw -> Base.decode64!(v)
          k == "purpose" -> String.to_existing_atom(v)
          true -> v
        end

      {String.to_existing_atom(k), value}
    end)
  end

  defp plaintext("preauth"), do: %Preauth{csrf: @fixture["csrf"]}

  defp plaintext("active"),
    do: %Active{csrf: @fixture["csrf"], access_token: @fixture["access_token"]}

  defp plaintext("attempt"), do: %Verifier{verifier: @fixture["verifier"]}

  defp sealed(values) do
    %Sealed{
      version: values["version"],
      key_id: values["key_id"],
      iv: Base.decode64!(values["iv"]),
      tag: Base.decode64!(values["tag"]),
      ciphertext: Base.decode64!(values["ciphertext"])
    }
  end

  defp config(values) do
    values
    |> Map.new(fn {k, v} ->
      {String.to_existing_atom(k),
       if(k in ["mode", "client_auth_method"], do: String.to_existing_atom(v), else: v)}
    end)
    |> then(&struct!(Config, &1))
  end

  defp base_config, do: config(hd(@fixture["configs"])["values"])
  defp flip(<<head, tail::binary>>), do: <<Bitwise.bxor(head, 1), tail::binary>>

  defp constructor(values) do
    object =
      values
      |> Map.drop(~w(mode transaction_seconds session_idle_seconds return_path failure_path))
      |> Map.put("version", 1)

    identity = %MixerHosted.Identity.StartupConfig{
      mode: :configured,
      owner_options: [
        binding: values["profile_id"],
        manifest: [
          %{
            profile: %{
              profile_id: values["profile_id"],
              profile_version: values["profile_version"],
              issuer: values["issuer"],
              client_id: values["client_id"],
              audience: values["api_audience"],
              identity_class: :human,
              enabled: true
            },
            jwks_endpoint: %{host: "id.example.test", port: 443, path: "/keys"},
            transport: :hosted_https
          }
        ]
      ]
    }

    Config.load(
      %{
        "MIXER_BROWSER_AUTH_MODE" => "configured",
        "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
      },
      :api,
      identity
    )
  end

  test "all current Config fields exactly match independent Node JSON bytes and SHA256" do
    assert {:ok, constructed} = constructor(hd(@fixture["configs"])["values"])
    assert constructed == base_config()

    assert Enum.sort(Enum.map(Map.keys(Map.from_struct(base_config())), &Atom.to_string/1)) ==
             Enum.sort(@fields)

    for vector <- @fixture["configs"] do
      assert {:ok, bytes} = ConfigurationDigest.canonical_bytes(config(vector["values"]))
      assert bytes == Base.decode64!(vector["canonical"]), vector["name"]
      assert {:ok, digest} = ConfigurationDigest.digest(config(vector["values"]))
      assert Base.encode16(digest, case: :lower) == vector["sha256"], vector["name"]
    end
  end

  test "trusted configuration digest and SQL-compatible Vault text have distinct boundaries" do
    # This records an integration limitation, not permission to use these values in SQL.
    for name <- ~w(profile_id client_id api_audience) do
      values = Map.put(hd(@fixture["configs"])["values"], name, "bounded" <> <<0>> <> "text")
      assert {:ok, loaded} = constructor(values)
      assert {:ok, _} = ConfigurationDigest.digest(loaded)

      if name in ~w(profile_id client_id) do
        assert Vault.associated_data(
                 key().id,
                 Map.put(context("attempt"), String.to_existing_atom(name), values[name])
               ) == @error
      end
    end
  end

  test "every admitted varying Config scalar changes the fence" do
    c = base_config()
    {:ok, original} = ConfigurationDigest.digest(c)

    for field <-
          ~w(public_origin profile_id issuer client_id api_audience authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri client_credential_ref session_vault_ref)a do
      assert {:ok, changed} = ConfigurationDigest.digest(Map.update!(c, field, &(&1 <> "z")))
      refute changed == original
    end

    assert {:ok, changed} = ConfigurationDigest.digest(%{c | profile_version: 2_147_483_647})
    refute changed == original
  end

  test "Config scalar bounds apply to every variable and fixed policy rejects every future choice" do
    c = base_config()

    for {field, limit} <- [
          public_origin: 2048,
          profile_id: 128,
          issuer: 2048,
          client_id: 256,
          api_audience: 256,
          authorization_endpoint: 2048,
          token_endpoint: 2048,
          id_token_jwks_endpoint: 2048,
          redirect_uri: 2048,
          client_credential_ref: 256,
          session_vault_ref: 256
        ] do
      for value <- [nil, "", 1, 1.0, false, [], %{}, <<255>>, String.duplicate("x", limit + 1)] do
        assert {:error, :invalid_configuration} =
                 ConfigurationDigest.digest(Map.put(c, field, value))
      end

      assert {:ok, _} =
               ConfigurationDigest.digest(Map.put(c, field, String.duplicate("x", limit)))

      assert {:error, :invalid_configuration} =
               ConfigurationDigest.digest(
                 Map.put(c, field, String.duplicate("é", div(limit, 2) + 1))
               )
    end

    for field <-
          ~w(mode client_auth_method scope response_mode response_iss_required transaction_seconds session_idle_seconds return_path failure_path)a,
        value <- [nil, false, true, "future", :future, 1, 300.0, 900.0] do
      if Map.fetch!(c, field) !== value do
        assert {:error, :invalid_configuration} =
                 ConfigurationDigest.digest(Map.put(c, field, value))
      end
    end

    for value <- [nil, false, -1, 0, 7.0, "7", 2_147_483_648] do
      assert {:error, :invalid_configuration} =
               ConfigurationDigest.digest(%{c | profile_version: value})
    end
  end

  test "Config denies every missing field and unknown plaintext-secret or future field" do
    c = base_config()

    for field <- Map.keys(c),
        do:
          assert(
            ConfigurationDigest.digest(Map.delete(c, field)) == {:error, :invalid_configuration}
          )

    for field <- [:client_secret, :vault_key, :future, "mode"],
        do:
          assert(
            ConfigurationDigest.digest(Map.put(c, field, "private-sentinel")) ==
              {:error, :invalid_configuration}
          )

    for value <- [nil, [], %{}, %Config{}, Map.from_struct(c)],
        do: assert(ConfigurationDigest.canonical_bytes(value) == {:error, :invalid_configuration})
  end

  test "independent Node AAD and exact typed encryption interoperate in all three purposes" do
    for vector <- @fixture["vectors"] do
      purpose = vector["purpose"]
      c = context(purpose)
      assert {:ok, aad} = Vault.associated_data(key().id, c)
      assert aad == Base.decode64!(vector["aad"])
      assert {:ok, value} = Vault.open(key(), c, sealed(vector["sealed"]))
      assert value == plaintext(purpose)
    end
  end

  test "independently authenticated malformed plaintext always denies without parser exceptions" do
    for vector <- @fixture["malformed"] do
      assert Vault.open(key(), context(vector["purpose"]), sealed(vector["sealed"])) == @error,
             "authenticated malformed vector #{inspect(vector)}"
    end
  end

  test "every context scalar substitution missing field and extra field denies" do
    for purpose <- ~w(preauth active attempt) do
      c = context(purpose)
      {:ok, encrypted} = Vault.seal(key(), c, plaintext(purpose))

      for {field, value} <- c do
        changed =
          cond do
            field == :purpose -> :future
            field == :generation -> Base.url_encode64(:binary.copy(<<133>>, 32), padding: false)
            is_integer(value) -> value + 1
            is_binary(value) -> flip(value)
            true -> "foreign"
          end

        assert Vault.open(key(), Map.put(c, field, changed), encrypted) == @error,
               "#{purpose}.#{field}"

        assert Vault.open(key(), Map.delete(c, field), encrypted) == @error
      end

      assert Vault.open(key(), Map.put(c, :future, "private-sentinel"), encrypted) == @error

      for other <- ~w(preauth active attempt),
          other != purpose,
          do: assert(Vault.open(key(), context(other), encrypted) == @error)
    end
  end

  test "keys metadata and all sealed-byte substitutions deny with one error" do
    c = context("active")
    {:ok, value} = Vault.seal(key(), c, plaintext("active"))
    {:ok, other_id} = Vault.key("other-key", key().bytes)
    {:ok, other_bytes} = Vault.key(key().id, flip(key().bytes))
    assert Vault.open(other_id, c, %{value | key_id: other_id.id}) == @error
    assert Vault.open(other_bytes, c, value) == @error

    for bad <- [
          %{value | version: 2},
          %{value | version: 1.0},
          %{value | key_id: "foreign"},
          %{value | iv: flip(value.iv)},
          %{value | tag: flip(value.tag)},
          %{value | ciphertext: flip(value.ciphertext)},
          %{value | tag: binary_part(value.tag, 0, 12)},
          %{value | iv: binary_part(value.iv, 0, 11)},
          %{value | ciphertext: value.ciphertext <> <<0>>},
          %{value | ciphertext: ""},
          %{value | ciphertext: :binary.copy(<<0>>, 8193)},
          Map.from_struct(value),
          Map.put(value, :extra, "private-sentinel")
        ] do
      assert Vault.open(key(), c, bad) == @error
    end
  end

  test "all64 final base64url characters admit only16 canonical trailing-bit values" do
    alphabet = ~c"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

    for {last, index} <- Enum.with_index(alphabet) do
      token = String.duplicate("A", 42) <> <<last>>
      canonical = rem(index, 4) == 0
      active = %{context("active") | csrf_digest: :crypto.hash(:sha256, token)}
      result = Vault.seal(key(), active, %Active{csrf: token, access_token: "bearer=="})
      verifier = Vault.seal(key(), context("attempt"), %Verifier{verifier: token})

      generation =
        Vault.seal(key(), %{context("preauth") | generation: token}, plaintext("preauth"))

      assert match?({:ok, _}, result) == canonical
      assert match?({:ok, _}, verifier) == canonical
      assert match?({:ok, _}, generation) == canonical
    end
  end

  test "every durable integer enforces SQL profile or positive53 bounds" do
    for purpose <- ~w(preauth active attempt) do
      c = context(purpose)

      for {field, value} <- c, is_integer(value) do
        limit = if field == :profile_version, do: 2_147_483_647, else: 9_007_199_254_740_991
        assert {:ok, _} = Vault.seal(key(), Map.put(c, field, limit), plaintext(purpose))

        for bad <- [-1, 0, 1.0, true, "1", limit + 1] do
          assert Vault.seal(key(), Map.put(c, field, bad), plaintext(purpose)) == @error
        end
      end
    end
  end

  test "every raw and UTF8 context field has its own closed byte bound" do
    for purpose <- ~w(preauth active attempt) do
      c = context(purpose)

      for {field, value} <- c, Atom.to_string(field) in @raw do
        for bad <- [
              binary_part(value, 0, byte_size(value) - 1),
              value <> <<0>>,
              Base.encode64(value)
            ] do
          assert Vault.seal(key(), Map.put(c, field, bad), plaintext(purpose)) == @error
        end
      end

      text_fields =
        [profile_id: 128] ++
          case purpose do
            "active" -> [principal_id: 128, family_id: 128, credential_ref: 256]
            "attempt" -> [issuer: 2048, client_id: 256, redirect_uri: 2048]
            _ -> []
          end

      for {field, limit} <- text_fields do
        assert {:ok, _} =
                 Vault.seal(
                   key(),
                   Map.put(c, field, String.duplicate("é", div(limit, 2))),
                   plaintext(purpose)
                 )

        for bad <- ["", <<255>>, "NUL" <> <<0>>, String.duplicate("x", limit + 1)] do
          assert Vault.seal(key(), Map.put(c, field, bad), plaintext(purpose)) == @error
        end
      end
    end

    c = context("active")

    assert {:ok, left} =
             Vault.associated_data(key().id, %{c | principal_id: "a", family_id: "bc"})

    assert {:ok, right} =
             Vault.associated_data(key().id, %{c | principal_id: "ab", family_id: "c"})

    refute left == right
    assert {:ok, composed} = Vault.associated_data(key().id, %{c | principal_id: "é"})
    assert {:ok, decomposed} = Vault.associated_data(key().id, %{c | principal_id: "e\u0301"})
    refute composed == decomposed

    assert Vault.associated_data(key().id, c) ==
             Vault.associated_data(key().id, Map.new(Enum.reverse(Map.to_list(c))))
  end

  test "bearer syntax and key material have exact byte boundaries" do
    c = context("active")

    for token <- ["a", "AZaz09._~+/-===", String.duplicate("x", 4089)] do
      p = %Active{csrf: @fixture["csrf"], access_token: token}
      assert {:ok, encrypted} = Vault.seal(key(), c, p)
      assert {:ok, ^p} = Vault.open(key(), c, encrypted)
    end

    for token <- ["", "=", "a=b", "a\rb", "a\tb", "a?b", <<255>>, String.duplicate("x", 4090)],
        do:
          assert(
            Vault.seal(key(), c, %Active{csrf: @fixture["csrf"], access_token: token}) == @error
          )

    assert {:ok, _} = Vault.key(String.duplicate("a", 128), key().bytes)

    for id <- ["", "a/", "é", "a\n", String.duplicate("a", 129)],
        do: assert(Vault.key(id, key().bytes) == @error)

    for size <- [0, 16, 31, 33, 64],
        do: assert(Vault.key(key().id, :binary.copy(<<1>>, size)) == @error)
  end

  test "every public operation contains malformed values and hides private error contents" do
    for bad <- [nil, true, 1, 1.0, :bad, [], [1], {}, %{}, <<255>>, "private/sentinel"] do
      assert Vault.key(bad, bad) == @error
      assert Vault.associated_data(key().id, bad) == @error
      assert Vault.associated_data(bad, context("active")) == @error
      assert Vault.seal(bad, context("active"), plaintext("active")) == @error
      assert Vault.seal(key(), bad, plaintext("active")) == @error
      assert Vault.seal(key(), context("active"), bad) == @error
      assert Vault.open(key(), context("active"), bad) == @error
    end

    for purpose <- ~w(preauth active attempt),
        field <- Map.keys(context(purpose)),
        bad <- [nil, [], %{}, <<255>>, "private-sentinel", 0, 1.0] do
      changed = Map.put(context(purpose), field, bad)
      result = Vault.associated_data(key().id, changed)
      assert result == @error or match?({:ok, _}, result)
      assert Vault.open(key(), changed, nil) == @error
    end
  end

  test "public encrypt API has no nonce override and128 sampled IVs are distinct" do
    assert Vault.__info__(:functions) == [associated_data: 2, key: 2, open: 3, seal: 3]

    values =
      for index <- 0..127 do
        purpose = Enum.at(~w(preauth active attempt), rem(index, 3))
        assert {:ok, value} = Vault.seal(key(), context(purpose), plaintext(purpose))
        assert byte_size(value.iv) == 12 and byte_size(value.tag) == 16
        value.iv
      end

    assert MapSet.size(MapSet.new(values)) == 128
  end

  test "Inspect of nested secret structs stays redacted and Config exposes mode only" do
    {:ok, value} = Vault.seal(key(), context("active"), plaintext("active"))

    rendered =
      inspect([key(), value, plaintext("active"), plaintext("attempt"), plaintext("preauth")])

    for secret <- [
          @fixture["csrf"],
          @fixture["access_token"],
          @fixture["verifier"],
          key().id,
          inspect(key().bytes),
          inspect(value.iv),
          inspect(value.tag),
          inspect(value.ciphertext)
        ] do
      refute String.contains?(rendered, secret)
    end

    assert inspect(base_config()) == "#MixerHosted.BrowserAuth.Config<mode: :configured, ...>"
  end
end

fixture = Jason.decode!(File.read!(System.fetch_env!("BROWSER_REVIEW_FIXTURE")))

vectors =
  Enum.map(~w(preauth active attempt), fn purpose ->
    raw = Enum.find(fixture["contexts"], &(&1["purpose"] == purpose))

    context =
      Map.new(raw, fn {name, value} ->
        value =
          cond do
            name in ~w(browser_id cookie_digest csrf_digest config_digest state_digest) ->
              Base.decode64!(value)

            name == "purpose" ->
              String.to_existing_atom(value)

            true ->
              value
          end

        {String.to_existing_atom(name), value}
      end)

    {:ok, key} =
      MixerHosted.BrowserAuth.Vault.key(
        fixture["key"]["id"],
        Base.decode64!(fixture["key"]["bytes"])
      )

    plain =
      case purpose do
        "preauth" ->
          %MixerHosted.BrowserAuth.Vault.Preauth{csrf: fixture["csrf"]}

        "active" ->
          %MixerHosted.BrowserAuth.Vault.Active{
            csrf: fixture["csrf"],
            access_token: fixture["access_token"]
          }

        "attempt" ->
          %MixerHosted.BrowserAuth.Vault.Verifier{verifier: fixture["verifier"]}
      end

    {:ok, encrypted} = MixerHosted.BrowserAuth.Vault.seal(key, context, plain)
    {:ok, aad} = MixerHosted.BrowserAuth.Vault.associated_data(key.id, context)

    %{
      purpose: purpose,
      aad: Base.encode64(aad),
      sealed: %{
        version: encrypted.version,
        key_id: encrypted.key_id,
        iv: Base.encode64(encrypted.iv),
        tag: Base.encode64(encrypted.tag),
        ciphertext: Base.encode64(encrypted.ciphertext)
      }
    }
  end)

File.write!(System.fetch_env!("BROWSER_REVIEW_OUTPUT"), Jason.encode!(vectors))
