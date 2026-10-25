defmodule MixerHosted.BrowserAuth.ConfigTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.Config
  alias MixerHosted.Identity.StartupConfig

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

  def identity do
    %StartupConfig{
      mode: :configured,
      owner_options: [
        binding: "human-main",
        generation: 1,
        manifest: [
          %{
            profile: %{
              profile_id: "human-main",
              profile_version: 7,
              issuer: "https://identity.example.invalid/tenant",
              audience: "mixer-api",
              client_id: "mixer-console",
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

  def load(object \\ object(), identity \\ identity()) do
    Config.load(
      %{
        "MIXER_BROWSER_AUTH_MODE" => "configured",
        "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
      },
      :api,
      identity
    )
  end

  def config do
    {:ok, config} = load()
    config
  end

  test "default and explicit disabled modes start no capability on either role" do
    for role <- [:api, :processor], env <- [%{}, %{"MIXER_BROWSER_AUTH_MODE" => "disabled"}] do
      assert {:ok, %Config{mode: :disabled, issuer: nil}} = Config.load(env, role, nil)
    end
  end

  test "disabled rejects even empty or nil stray browser configuration" do
    for value <- [nil, "", "{}"], role <- [:api, :processor] do
      assert {:error, :unexpected_configuration} =
               Config.load(%{"MIXER_BROWSER_AUTH_CONFIG" => value}, role, identity())
    end
  end

  test "invalid modes roles and missing configured data fail closed" do
    for mode <- [nil, true, :configured, "", "CONFIGURED", "enabled"] do
      assert {:error, :invalid_mode} =
               Config.load(%{"MIXER_BROWSER_AUTH_MODE" => mode}, :api, identity())
    end

    assert {:error, :invalid_role} =
             Config.load(%{"MIXER_BROWSER_AUTH_MODE" => "configured"}, :processor, identity())

    assert {:error, :invalid_configuration} =
             Config.load(%{"MIXER_BROWSER_AUTH_MODE" => "configured"}, :api, identity())

    assert {:error, :invalid_configuration} = Config.load(%{}, :arbitrary, identity())
    assert {:error, :invalid_configuration} = Config.load([], :api, identity())
  end

  test "configured client preserves exact trusted binding and fixed policy" do
    assert {:ok, config} = load()
    assert config.mode == :configured
    assert config.profile_id == "human-main"
    assert config.profile_version == 7
    assert config.return_path == "/workspace"
    assert config.failure_path == "/login"
    assert config.redirect_uri == config.public_origin <> "/auth/callback"
    assert config.transaction_seconds == 300
    assert config.session_idle_seconds == 900
    assert config.client_auth_method == :client_secret_basic
    assert inspect(config) == "#MixerHosted.BrowserAuth.Config<mode: :configured, ...>"
  end

  test "every missing key and every extra client-controlled choice is rejected" do
    for key <- Map.keys(object()) do
      assert {:error, :invalid_configuration} = load(Map.delete(object(), key))
    end

    for key <-
          ~w(client_secret vault_key return_to return_routes return_path failure_path audience prompt tenant nonce state discovery_url cookie_policy timeouts) do
      assert {:error, :invalid_configuration} =
               load(Map.put(object(), key, "untrusted-sensitive-value"))
    end
  end

  test "duplicate and escaped-equivalent JSON keys are not collapsed" do
    raw = Jason.encode!(object())

    for suffix <- [~s(,"client_id":"other"}), ~s(,"client_\u0069d":"other"})] do
      duplicate = binary_part(raw, 0, byte_size(raw) - 1) <> suffix

      assert {:error, :invalid_configuration} =
               Config.load(
                 %{
                   "MIXER_BROWSER_AUTH_MODE" => "configured",
                   "MIXER_BROWSER_AUTH_CONFIG" => duplicate
                 },
                 :api,
                 identity()
               )
    end
  end

  test "configuration is bounded before JSON decode and rejects malformed payload types" do
    for raw <- [nil, 1, "[]", "{", <<255>>, String.duplicate(" ", 16_385)] do
      assert {:error, :invalid_configuration} =
               Config.load(
                 %{"MIXER_BROWSER_AUTH_MODE" => "configured", "MIXER_BROWSER_AUTH_CONFIG" => raw},
                 :api,
                 identity()
               )
    end
  end

  test "identity matching requires exact enabled bound human profile and integer version" do
    for {key, bad} <- [
          {"profile_id", "another"},
          {"profile_version", 8},
          {"profile_version", 7.0},
          {"issuer", "https://identity.example.invalid/other"},
          {"client_id", "other"},
          {"api_audience", "other"}
        ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, bad))
    end

    for identity <- [
          nil,
          %StartupConfig{mode: :disabled, owner_options: []},
          %{mode: :configured, owner_options: identity().owner_options}
        ] do
      assert {:error, :invalid_configuration} = load(object(), identity)
    end
  end

  test "disabled service malformed duplicate or differently bound trust entries cannot enable login" do
    original = identity()
    [entry] = original.owner_options[:manifest]

    for profile <- [
          Map.put(entry.profile, :enabled, false),
          Map.put(entry.profile, :identity_class, :service),
          Map.delete(entry.profile, :issuer)
        ] do
      options = Keyword.put(original.owner_options, :manifest, [%{entry | profile: profile}])

      assert {:error, :invalid_configuration} =
               load(object(), %{original | owner_options: options})
    end

    for options <- [
          Keyword.put(original.owner_options, :binding, "missing"),
          Keyword.put(original.owner_options, :manifest, [entry, entry]),
          [{:binding, "human-main"} | original.owner_options],
          []
        ] do
      assert {:error, :invalid_configuration} =
               load(object(), %{original | owner_options: options})
    end
  end

  test "origins reject credentials paths aliases alternate ports non-DNS and unsafe characters" do
    for bad <- [
          "http://console.example.invalid",
          "https://console.example.invalid/",
          "https://console.example.invalid:443",
          "https://console.example.invalid:444",
          "https://CONSOLE.example.invalid",
          "https://console.example.invalid.",
          "https://console.example.invalid?x",
          "https://console.example.invalid#x",
          "https://user@console.example.invalid",
          "https://127.0.0.1",
          "https://[::1]",
          "https://localhost",
          "https://console%2eexample.invalid",
          "https://console.example.invalid\r\n",
          "https://console..invalid"
        ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), "public_origin", bad))
    end
  end

  test "endpoints are literal canonical HTTPS paths without discovery query fragments or normalization" do
    for key <- ~w(authorization_endpoint token_endpoint id_token_jwks_endpoint),
        bad <- [
          "https://identity.example.invalid",
          "https://identity.example.invalid:443/token",
          "https://identity.example.invalid/token?client=x",
          "https://identity.example.invalid/token#x",
          "https://identity.example.invalid/a/../token",
          "https://identity.example.invalid//token",
          "https://identity.example.invalid/%74oken",
          "https://identity.example.invalid/token/",
          "https://identity.example.invalid\\token",
          "https://user:secret@identity.example.invalid/token",
          "https://-bad.example.invalid/token",
          123
        ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, bad))
    end
  end

  test "exact redirect cannot become an open redirect or alias" do
    for bad <- [
          "https://elsewhere.example.invalid/auth/callback",
          "/auth/callback",
          "https://console.example.invalid/auth/callback/",
          "https://console.example.invalid/auth/%63allback",
          "https://console.example.invalid:443/auth/callback",
          "https://console.example.invalid/auth/callback?return_to=https://evil.invalid"
        ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), "redirect_uri", bad))
    end
  end

  test "fixed scopes protocol modes version and confidential method cannot widen" do
    for {key, bad} <- [
          {"scope", "openid mixer.workspace.read offline_access"},
          {"scope", "mixer.workspace.read openid"},
          {"scope", ["openid", "mixer.workspace.read"]},
          {"response_mode", "form_post"},
          {"response_iss_required", false},
          {"version", 1.0},
          {"version", 2},
          {"client_auth_method", "none"},
          {"client_auth_method", "private_key_jwt"},
          {"client_auth_method", "client_secret_post"}
        ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, bad))
    end
  end

  test "secrets are references only and malformed references give fixed sanitized errors" do
    for {key, bad} <- [
          {"client_credential_ref", "raw-client-secret"},
          {"client_credential_ref", "secret://"},
          {"client_credential_ref", "secret://a/../b"},
          {"client_credential_ref", "secret://a?secret=raw"},
          {"client_credential_ref", "secret://a%2fb"},
          {"session_vault_ref", "secret://a"},
          {"session_vault_ref", "vault://a//b"},
          {"session_vault_ref", "vault://" <> String.duplicate("x", 250)}
        ] do
      assert {:error, :invalid_configuration} = load(Map.put(object(), key, bad))
    end

    refute inspect(config()) =~ "secret://"
    refute inspect(config()) =~ "identity.example"
  end
end
