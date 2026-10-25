defmodule MixerHosted.BrowserAuth.ConfigurationDigestTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest}
  alias MixerHosted.BrowserAuth.ConfigTest, as: Fixture

  test "constructor configuration has deterministic versioned bytes and a raw SHA256 identity" do
    config = Fixture.config()
    assert {:ok, bytes} = ConfigurationDigest.canonical_bytes(config)
    assert <<"mixer.browser.configuration.v1", 0, json::binary>> = bytes
    assert [1, pairs] = Jason.decode!(json)
    assert length(pairs) == 21

    assert Enum.map(pairs, &hd/1) ==
             ~w(mode public_origin profile_id profile_version issuer client_id api_audience authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri client_auth_method client_credential_ref session_vault_ref scope response_mode response_iss_required transaction_seconds session_idle_seconds return_path failure_path)

    assert ["profile_version", 7] in pairs
    assert ["response_iss_required", true] in pairs
    assert ["client_auth_method", "client_secret_basic"] in pairs
    assert {:ok, digest} = ConfigurationDigest.digest(config)
    assert byte_size(digest) == 32
    assert digest == :crypto.hash(:sha256, bytes)
    assert {:ok, ^digest} = ConfigurationDigest.digest(Fixture.config())
  end

  test "every admitted variable changes the configuration fence without normalization" do
    config = Fixture.config()
    assert {:ok, baseline} = ConfigurationDigest.digest(config)

    for field <-
          ~w(public_origin profile_id issuer client_id api_audience authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri client_credential_ref session_vault_ref)a do
      # Fingerprinting binds exact trusted values. Config.load remains the URL/trust validator.
      assert {:ok, other} = ConfigurationDigest.digest(Map.update!(config, field, &(&1 <> "x")))
      assert other != baseline
    end

    assert {:ok, other} = ConfigurationDigest.digest(%{config | profile_version: 8})
    assert other != baseline
    assert {:ok, left} = ConfigurationDigest.digest(%{config | client_id: "é"})
    assert {:ok, right} = ConfigurationDigest.digest(%{config | client_id: "e\u0301"})
    assert left != right
  end

  test "JSON configuration input order and map construction order cannot change identity" do
    object = Fixture.object()

    raw =
      "{" <>
        Enum.map_join(Enum.reverse(Enum.sort(object)), ",", fn {k, v} ->
          Jason.encode!(k) <> ":" <> Jason.encode!(v)
        end) <> "}"

    assert {:ok, config} =
             Config.load(
               %{"MIXER_BROWSER_AUTH_MODE" => "configured", "MIXER_BROWSER_AUTH_CONFIG" => raw},
               :api,
               Fixture.identity()
             )

    assert ConfigurationDigest.digest(config) == ConfigurationDigest.digest(Fixture.config())
    rebuilt = config |> Map.to_list() |> Enum.reverse() |> Map.new()
    assert ConfigurationDigest.digest(rebuilt) == ConfigurationDigest.digest(config)
  end

  test "disabled, unknown fields and future policy choices do not mint a current digest" do
    config = Fixture.config()

    for value <- [
          nil,
          %{},
          %Config{},
          Map.put(config, :client_secret, "private"),
          Map.delete(config, :scope)
        ] do
      assert {:error, :invalid_configuration} = ConfigurationDigest.digest(value)
    end

    for {key, value} <- [
          mode: :disabled,
          client_auth_method: :none,
          scope: "openid",
          response_mode: "form_post",
          response_iss_required: false,
          transaction_seconds: 301,
          session_idle_seconds: 901,
          return_path: "/elsewhere",
          failure_path: "/elsewhere"
        ] do
      assert {:error, :invalid_configuration} =
               ConfigurationDigest.digest(Map.put(config, key, value))
    end
  end

  test "malformed scalar values fail with a fixed error before serialization" do
    config = Fixture.config()

    for value <- [nil, "", 1, %{}, [], <<255>>, String.duplicate("x", 2049)] do
      assert {:error, :invalid_configuration} =
               ConfigurationDigest.digest(%{config | issuer: value})
    end

    for value <- [0, -1, 1.5, "7", 2_147_483_648] do
      assert {:error, :invalid_configuration} =
               ConfigurationDigest.digest(%{config | profile_version: value})
    end

    assert {:error, :invalid_configuration} =
             ConfigurationDigest.digest(%{config | client_id: String.duplicate("a", 257)})
  end

  test "length boundaries and separate fields remain distinct and bounded" do
    config = %{
      Fixture.config()
      | profile_id: String.duplicate("a", 128),
        client_id: String.duplicate("b", 256),
        issuer: String.duplicate("c", 2048)
    }

    assert {:ok, bytes} = ConfigurationDigest.canonical_bytes(config)
    assert byte_size(bytes) < 16_384

    assert {:ok, left} =
             ConfigurationDigest.digest(%{config | client_id: "a", api_audience: "bc"})

    assert {:ok, right} =
             ConfigurationDigest.digest(%{config | client_id: "ab", api_audience: "c"})

    assert left != right

    assert {:error, :invalid_configuration} =
             ConfigurationDigest.digest(%{config | profile_id: config.profile_id <> "a"})
  end
end
