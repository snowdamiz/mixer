defmodule MixerHosted.BrowserAuth.ProviderTrustConfigTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest, Installation, ProviderTrustConfig}
  alias MixerHosted.Identity.{Manifest, StartupConfig}
  @moduletag :browser_provider_trust_constructor_admission
  @failure {:error, :invalid_provider_trust_configuration}

  defp roots do
    Enum.map(:public_key.cacerts_get(), fn
      {:cert, der, _} -> der
      der -> der
    end)
  end

  defp envelope do
    %{
      "version" => 1,
      "generation" => 11,
      "binding" => "human-main",
      "resolvers" => ["8.8.8.8"],
      "profiles" => [
        %{
          "profile" => %{
            "profile_id" => "human-main",
            "profile_version" => 7,
            "issuer" => "https://issuer.example.invalid/tenant",
            "client_id" => "browser-client",
            "audience" => "mixer-api",
            "identity_class" => "human",
            "enabled" => true
          },
          "jwks_endpoint" => %{
            "host" => "api-keys.example.invalid",
            "port" => 443,
            "path" => "/api/keys"
          },
          "transport" => "hosted_https"
        }
      ]
    }
  end

  defp identity(object \\ envelope()) do
    StartupConfig.load!(
      %{"MIXER_IDENTITY_MODE" => "configured", "MIXER_IDENTITY_CONFIG" => Jason.encode!(object)},
      :api,
      roots()
    )
  end

  defp object do
    %{
      "version" => 1,
      "public_origin" => "https://console.example.invalid",
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => "https://issuer.example.invalid/tenant",
      "client_id" => "browser-client",
      "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://issuer.example.invalid/authorize",
      "token_endpoint" => "https://issuer.example.invalid/token",
      "id_token_jwks_endpoint" => "https://browser-keys.example.invalid/oidc/keys",
      "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://mixer/client-v1",
      "session_vault_ref" => "vault://mixer/session-v1",
      "scope" => "openid mixer.workspace.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }
  end

  defp browser_env(object),
    do: %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }

  defp config do
    {:ok, config} = Config.load(browser_env(object()), :api, identity())
    config
  end

  defp options(identity, fun), do: %{identity | owner_options: fun.(identity.owner_options)}

  test "browser_provider_trust_constructor_admission derives separate exact browser trust settings" do
    source = identity()
    original = source
    config = config()
    assert {:ok, admitted} = ProviderTrustConfig.new(config, source)
    assert admitted.configuration_digest == elem(ConfigurationDigest.digest(config), 1)
    opts = admitted.owner_options
    assert opts[:name] == MixerHosted.BrowserAuth.ProviderTrustOwner
    assert opts[:binding] == "human-main" and opts[:generation] == 11
    assert opts[:resolvers] == source.owner_options[:resolvers]
    assert opts[:ca_roots] === source.owner_options[:ca_roots]
    assert [entry] = opts[:manifest]

    assert entry.jwks_endpoint == %{
             host: "browser-keys.example.invalid",
             port: 443,
             path: "/oidc/keys"
           }

    refute entry.jwks_endpoint == hd(source.owner_options[:manifest]).jwks_endpoint
    assert entry.profile == hd(source.owner_options[:manifest]).profile
    assert entry.transport == :hosted_https
    assert {:ok, _} = Manifest.validate(opts[:manifest])
    assert source === original
    assert Process.whereis(MixerHosted.BrowserAuth.ProviderTrustOwner) == nil
  end

  test "additional unrelated API profiles are not copied into browser trust" do
    env = envelope()
    [first] = env["profiles"]
    extra = put_in(first, ["profile", "profile_id"], "other-profile")
    source = identity(Map.put(env, "profiles", [first, extra]))
    assert {:ok, admitted} = ProviderTrustConfig.new(config(), source)
    assert length(admitted.owner_options[:manifest]) == 1
  end

  test "profile identity mismatches and stale versions fail closed" do
    for {field, value} <- [
          profile_id: "other",
          profile_version: 8,
          issuer: "https://other.example.invalid",
          client_id: "other",
          api_audience: "other"
        ] do
      assert @failure == ProviderTrustConfig.new(Map.put(config(), field, value), identity())
    end
  end

  test "disabled or service binding cannot become browser trust" do
    for {field, value} <- [{"enabled", false}, {"identity_class", "service"}] do
      env = envelope()
      [entry] = env["profiles"]
      entry = put_in(entry, ["profile", field], value)

      assert @failure ==
               ProviderTrustConfig.new(config(), identity(Map.put(env, "profiles", [entry])))
    end
  end

  test "forged browser endpoint is revalidated rather than treated as authority" do
    for endpoint <- [
          nil,
          "",
          "http://keys.example.invalid/keys",
          "https://127.0.0.1/keys",
          "https://keys.example.invalid:443/keys",
          "https://keys.example.invalid/../keys",
          "https://keys.example.invalid/keys?x=1"
        ] do
      assert @failure ==
               ProviderTrustConfig.new(%{config() | id_token_jwks_endpoint: endpoint}, identity())
    end
  end

  test "forged fixed browser policy and unknown struct fields are rejected" do
    for change <- [
          %{transaction_seconds: 301},
          %{response_iss_required: false},
          %{client_auth_method: :none},
          %{scope: "openid admin"},
          %{mode: :disabled},
          %{client_credential_ref: "raw-secret"},
          %{session_vault_ref: "raw-key"},
          %{extra: self()}
        ] do
      assert @failure == ProviderTrustConfig.new(Map.merge(config(), change), identity())
    end
  end

  test "unknown duplicate and owner selection startup options are rejected" do
    for change <- [
          fn x -> x ++ [name: self()] end,
          fn x -> x ++ [fixture: self()] end,
          fn x -> x ++ [generation: 11] end,
          fn x -> Keyword.delete(x, :ca_roots) end
        ] do
      assert @failure == ProviderTrustConfig.new(config(), options(identity(), change))
    end
  end

  test "forged generation resolver and CA values must pass actual StartupConfig" do
    for {key, value} <- [
          generation: 0,
          generation: 2_147_483_648,
          resolvers: [],
          resolvers: [{{8, 8, 8, 8}, 54}],
          resolvers: [{{999, 1, 1, 1}, 53}],
          resolvers: [{{8, 8, 8, 8}, 53}, {{8, 8, 8, 8}, 53}],
          ca_roots: [],
          ca_roots: ["not-a-certificate"]
        ] do
      source = options(identity(), &Keyword.put(&1, key, value))
      assert @failure == ProviderTrustConfig.new(config(), source)
    end
  end

  test "missing malformed extra-field and noncanonical startup structures fail closed" do
    for source <- [
          nil,
          %{},
          Map.from_struct(identity()),
          %{identity() | mode: :disabled},
          %{identity() | owner_options: %{}},
          Map.put(identity(), :unexpected, true),
          options(identity(), &Keyword.put(&1, :binding, "missing"))
        ] do
      assert @failure == ProviderTrustConfig.new(config(), source)
    end

    for browser <- [nil, %{}, Map.from_struct(config())],
        do: assert(@failure == ProviderTrustConfig.new(browser, identity()))
  end

  test "browser endpoint changes change the digest and exact selected manifest" do
    old = config()
    newer = %{old | id_token_jwks_endpoint: "https://another.example.invalid/keys"}
    assert {:ok, a} = ProviderTrustConfig.new(old, identity())
    assert {:ok, b} = ProviderTrustConfig.new(newer, identity())
    refute a.configuration_digest == b.configuration_digest
    assert hd(b.owner_options[:manifest]).jwks_endpoint.host == "another.example.invalid"
  end

  test "inspection redacts all configuration metadata" do
    assert {:ok, admitted} = ProviderTrustConfig.new(config(), identity())
    text = inspect(admitted)

    refute String.contains?(text, [
             "secret://",
             "vault://",
             "human-main",
             "browser-keys",
             "owner_options"
           ])
  end

  test "admitted trust settings require secret material and preserve disabled installation" do
    source = identity()
    config = config()
    assert {:ok, _} = ProviderTrustConfig.new(config, source)

    hosted = %MixerHosted.RuntimeConfig{
      role: :api,
      repo: [],
      oban: [],
      endpoint: [],
      database_connection_bound: 0,
      identity_startup: source
    }

    assert_raise ArgumentError, "browser installation unavailable: configuration", fn ->
      Installation.load!(browser_env(object()), hosted)
    end

    assert Installation.load!(%{}, hosted) == :disabled
    assert Process.whereis(MixerHosted.BrowserAuth.ProviderTrustOwner) == nil
  end
end
