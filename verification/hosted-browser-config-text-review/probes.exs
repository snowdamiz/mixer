defmodule MixerHosted.BrowserAuth.ConfigTextIndependentReview do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest}
  alias MixerHosted.Identity.{Manifest, StartupConfig}
  @metadata [{"profile_id", 128}, {"client_id", 256}, {"api_audience", 256}]

  def object do
    %{
      "version" => 1,
      "public_origin" => "https://console.example.invalid",
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => "https://identity.example.invalid/tenant",
      "client_id" => "mixer-console",
      "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://identity.example.invalid/authorize",
      "token_endpoint" => "https://identity.example.invalid/token",
      "id_token_jwks_endpoint" => "https://identity.example.invalid/oidc/keys",
      "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://mixer/oidc/client-v1",
      "session_vault_ref" => "vault://mixer/browser-session-v1",
      "scope" => "openid mixer.workspace.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }
  end

  def identity(object) do
    %StartupConfig{
      mode: :configured,
      owner_options: [
        binding: object["profile_id"],
        manifest: [
          %{
            profile: %{
              profile_id: object["profile_id"],
              profile_version: object["profile_version"],
              issuer: object["issuer"],
              audience: object["api_audience"],
              client_id: object["client_id"],
              identity_class: :human,
              enabled: true
            },
            jwks_endpoint: %{host: "identity.example.invalid", port: 443, path: "/api/keys"},
            transport: :hosted_https
          }
        ]
      ]
    }
  end

  def load(object), do: raw(Jason.encode!(object), identity(object))

  def raw(json, identity),
    do:
      Config.load(
        %{"MIXER_BROWSER_AUTH_MODE" => "configured", "MIXER_BROWSER_AUTH_CONFIG" => json},
        :api,
        identity
      )

  test "NUL at each end and the middle of exact byte bounds rejects even with a matching valid manifest" do
    for {key, limit} <- @metadata, position <- [0, div(limit, 2), limit - 1] do
      value =
        String.duplicate("a", position) <> <<0>> <> String.duplicate("z", limit - position - 1)

      object = Map.put(object(), key, value)
      i = identity(object)
      assert byte_size(value) == limit
      assert {:ok, _} = Manifest.validate(i.owner_options[:manifest])
      assert {:error, :invalid_configuration} = load(object)
    end
  end

  test "every admitted binary field rejects decoded NUL with fixed denial" do
    for {key, value} <- object(), is_binary(value), offset <- [0, byte_size(value)] do
      changed =
        Map.put(
          object(),
          key,
          binary_part(value, 0, offset) <>
            <<0>> <> binary_part(value, offset, byte_size(value) - offset)
        )

      assert {:error, :invalid_configuration} = load(changed)
    end
  end

  test "escaped metadata keys cannot bypass the check and duplicate aliases remain rejected" do
    object = Map.put(object(), "profile_id", "human\0main")
    json = object |> Jason.encode!() |> String.replace("\"profile_id\":", "\"profile\\u005fid\":")
    assert {:error, :invalid_configuration} = raw(json, identity(object))
    baseline = object()
    json = Jason.encode!(baseline)

    duplicate =
      "{\"profile\\u005fid\":\"human-main\"," <> binary_part(json, 1, byte_size(json) - 1)

    assert {:error, :invalid_configuration} = raw(duplicate, identity(baseline))
  end

  test "simultaneous valid Unicode endpoints preserve exact bytes and differ across normalization forms" do
    exact =
      Enum.reduce(@metadata, object(), fn {key, limit}, object ->
        Map.put(object, key, String.duplicate("😀", div(limit, 4)))
      end)

    assert {:ok, config} = load(exact)

    for {key, limit} <- @metadata do
      value = Map.fetch!(config, String.to_existing_atom(key))
      assert value === exact[key]
      assert byte_size(value) == limit
      assert {:error, :invalid_configuration} = load(Map.put(exact, key, value <> "x"))
    end

    for value <- ["é", "e\u0301", "漢字😀", "zero\u200dwidth\u2060", "x\t\r\n" <> <<1, 127>>] do
      current = Map.put(object(), "client_id", value)
      assert {:ok, c} = load(current)
      assert c.client_id === value
      assert {:ok, bytes} = ConfigurationDigest.canonical_bytes(c)
      assert {:ok, digest} = ConfigurationDigest.digest(c)
      path = System.fetch_env!("MIXER_CONFIG_TEXT_REVIEW_VECTORS")

      File.write!(
        path,
        Jason.encode!(%{
          config: Map.from_struct(c),
          canonical_hex: Base.encode16(bytes, case: :lower),
          digest_hex: Base.encode16(digest, case: :lower)
        }) <> "\n",
        [:append]
      )
    end

    {:ok, composed} = load(Map.put(object(), "client_id", "é"))
    {:ok, decomposed} = load(Map.put(object(), "client_id", "e\u0301"))
    assert ConfigurationDigest.digest(composed) != ConfigurationDigest.digest(decomposed)
  end

  test "metadata types and empty or overlong bytes never mint a configured value" do
    for {key, limit} <- @metadata,
        value <- [nil, true, 0, [], %{}, "", String.duplicate("a", limit + 1)] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, value))
    end
  end

  test "baseline serialization remains byte identical to independently fixed existing format" do
    assert {:ok, config} = load(object())
    assert {:ok, bytes} = ConfigurationDigest.canonical_bytes(config)
    assert byte_size(bytes) == 910

    assert Base.encode16(:crypto.hash(:sha256, bytes), case: :lower) ==
             "3116d5ef6ac718b3d2442df3648c60ab3fa1d640f73d429ed2b30490f1e2d7f3"

    File.write!(
      System.fetch_env!("MIXER_CONFIG_TEXT_REVIEW_VECTORS"),
      Jason.encode!(%{
        config: Map.from_struct(config),
        canonical_hex: Base.encode16(bytes, case: :lower),
        digest_hex: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
      }) <> "\n",
      [:append]
    )
  end
end
