defmodule StartupSecretsControls do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Config, StartupSecrets, RuntimeConfig, ProviderTrustConfig}
  alias MixerHosted.RuntimeConfig, as: HostedConfig
  @failure {:error, :session_unavailable}
  @var "MIXER_BROWSER_AUTH_SECRET_MATERIAL"

  defp fixtures do
    profile = %{
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => "https://identity.example.invalid/tenant",
      "audience" => "mixer-api",
      "client_id" => "mixer-console",
      "identity_class" => "human",
      "enabled" => true
    }

    identity = %{
      "version" => 1,
      "generation" => 1,
      "binding" => "human-main",
      "resolvers" => ["1.1.1.1"],
      "profiles" => [
        %{
          "profile" => profile,
          "jwks_endpoint" => %{
            "host" => "identity.example.invalid",
            "port" => 443,
            "path" => "/api/keys"
          },
          "transport" => "hosted_https"
        }
      ]
    }

    hosted =
      HostedConfig.load!(%{
        "MIXER_HOSTED_ROLE" => "api",
        "MIXER_DATABASE_HOST" => "ep-fixture.us-east-2.aws.neon.tech",
        "MIXER_DATABASE_NAME" => "mixer_fixture",
        "MIXER_DATABASE_USER" => "mixer_ordinary_fixture",
        "MIXER_DATABASE_PASSWORD" => "synthetic-ordinary-password",
        "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-secret-", 8),
        "MIXER_IDENTITY_MODE" => "configured",
        "MIXER_IDENTITY_CONFIG" => Jason.encode!(identity)
      })

    object = %{
      "version" => 1,
      "public_origin" => "https://console.example.invalid",
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => profile["issuer"],
      "client_id" => "mixer-console",
      "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://identity.example.invalid/authorize",
      "token_endpoint" => "https://identity.example.invalid/token",
      "id_token_jwks_endpoint" => "https://identity.example.invalid/oidc/keys",
      "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://mixer/client-v1",
      "session_vault_ref" => "vault://mixer/session-v1",
      "scope" => "openid mixer.workspace.read mixer.build.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }

    env = %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }

    {:ok, config} = Config.load(env, :api, hosted.identity_startup)

    material = %{
      "version" => 1,
      "client" => %{
        "reference" => object["client_credential_ref"],
        "value" => "synthetic-client-credential:+雪"
      },
      "session_vault" => %{
        "reference" => object["session_vault_ref"],
        "key_id" => "synthetic-v1",
        "key_base64" => Base.encode64(:binary.copy(<<71>>, 32))
      },
      "lifecycle" => %{
        "username" => "mixer_lifecycle_fixture",
        "password" => "synthetic-lifecycle-password",
        "writer_role" => "mixer_writer_fixture",
        "relation_owner" => "mixer_owner_fixture"
      }
    }

    {hosted, env, config, material}
  end

  defp load(config, material), do: StartupSecrets.load(%{@var => Jason.encode!(material)}, config)
  # Boolean assertions keep synthetic material out of failure diagnostics as well.
  defp check(value, label), do: assert(value === true, label)

  defp rejected(config, material),
    do: check(load(config, material) === @failure, "material must fail closed")

  test "actual loaded result composes with catalog RuntimeConfig and ProviderTrustConfig" do
    {hosted, env, config, material} = fixtures()
    {:ok, loaded} = load(config, material)

    {:ok, runtime} =
      RuntimeConfig.new_with_build_catalog(env, hosted, loaded.lifecycle, loaded.custody)

    {:ok, trust} = ProviderTrustConfig.new(runtime.browser_config, hosted.identity_startup)
    check(runtime.admission_profile === :build_catalog_v3, "catalog profile")
    check(runtime.custody === loaded.custody, "exact custody")

    check(
      runtime.lifecycle_repo[:password] === loaded.lifecycle.password,
      "exact lifecycle material"
    )

    check(
      loaded.client_credential === %{
        reference: config.client_credential_ref,
        value: material["client"]["value"]
      },
      "exact client material"
    )

    check(
      trust.configuration_digest === runtime.configuration_digest,
      "shared configuration binding"
    )

    check(Process.whereis(MixerHosted.BrowserAuth.ProviderTrustOwner) === nil, "no owner started")
    check(load(config, material) === {:ok, loaded}, "immutable deterministic mapping")
    bad_roles = %{loaded.lifecycle | username: hosted.repo[:username]}

    check(
      RuntimeConfig.new_with_build_catalog(env, hosted, bad_roles, loaded.custody) === @failure,
      "ordinary role separation at composition"
    )
  end

  test "reference bindings reject aliases stale versions and missing values" do
    {_, _, config, m} = fixtures()

    for section <- ["client", "session_vault"],
        ref <- [
          nil,
          "",
          "secret://mixer/client-v2",
          "vault://mixer/session-v2",
          "secret://mixer/./client-v1",
          "secret://mixer/client%2Dv1"
        ] do
      rejected(config, put_in(m, [section, "reference"], ref))
    end

    check(
      load(
        %{config | client_credential_ref: "alias"},
        put_in(m, ["client", "reference"], "alias")
      ) === @failure,
      "forged alias config"
    )
  end

  test "exact schemas and integer version at every boundary" do
    {_, _, config, m} = fixtures()
    for key <- Map.keys(m), do: rejected(config, Map.delete(m, key))
    rejected(config, Map.put(m, "extra", "synthetic"))
    for value <- [0, 2, 1.0, "1", nil], do: rejected(config, %{m | "version" => value})

    for section <- ["client", "session_vault", "lifecycle"] do
      for key <- Map.keys(m[section]),
          do: rejected(config, put_in(m, [section], Map.delete(m[section], key)))

      rejected(config, put_in(m, [section, "extra"], true))
      for value <- [nil, [], 1, "synthetic"], do: rejected(config, Map.put(m, section, value))
    end
  end

  test "bounded parser rejects duplicates escaped duplicates depth bytes and invalid UTF8" do
    {_, _, config, m} = fixtures()
    raw = Jason.encode!(m)
    duplicate = String.replace(raw, "\"version\":1", "\"version\":1,\"ver\\u0073ion\":1")

    nested_duplicate =
      String.replace(
        raw,
        "\"key_id\":\"synthetic-v1\"",
        "\"key_id\":\"synthetic-v1\",\"key_id\":\"synthetic-v1\""
      )

    for bad <- [
          duplicate,
          nested_duplicate,
          "{",
          "[]",
          "null",
          <<255>>,
          String.duplicate(" ", 16_385),
          "{\"a\":" <> String.duplicate("[", 18) <> "0" <> String.duplicate("]", 18) <> "}",
          Jason.encode!(Map.new(1..65, &{Integer.to_string(&1), 1}))
        ] do
      check(StartupSecrets.load(%{@var => bad}, config) === @failure, "bounded JSON failure")
    end
  end

  test "canonical base64 exact AES key bytes and vetted key IDs" do
    {_, _, config, m} = fixtures()
    encoded = m["session_vault"]["key_base64"]
    # Last base64 character f has nonzero unused bits but decodes like canonical c.
    noncanonical = binary_part(encoded, 0, 42) <> "f="

    for value <- [
          nil,
          "",
          String.trim_trailing(encoded, "="),
          noncanonical,
          encoded <> "\n",
          Base.encode64(:binary.copy(<<71>>, 31)),
          Base.encode64(:binary.copy(<<71>>, 33))
        ] do
      rejected(config, put_in(m, ["session_vault", "key_base64"], value))
    end

    for id <- [nil, "", "bad/key", String.duplicate("k", 129)],
        do: rejected(config, put_in(m, ["session_vault", "key_id"], id))
  end

  test "client bounds UTF8 and header delimiter rejection preserve safe exact bytes" do
    {_, _, config, m} = fixtures()

    for value <- [nil, "", String.duplicate("x", 4097), "a\rB", "a\nB", "a\0B"] do
      rejected(config, put_in(m, ["client", "value"], value))
    end

    for value <- ["x", String.duplicate("x", 4096), " :+雪"] do
      {:ok, loaded} = load(config, put_in(m, ["client", "value"], value))
      check(loaded.client_credential.value === value, "UTF8 byte preservation")
    end
  end

  test "lifecycle restricted roles unique identities and bounded password" do
    {_, _, config, m} = fixtures()

    for role <- ["username", "writer_role", "relation_owner"],
        value <- [
          nil,
          "",
          "public",
          "pg_owner",
          "Upper",
          "1bad",
          "bad-role",
          String.duplicate("a", 64)
        ] do
      rejected(config, put_in(m, ["lifecycle", role], value))
    end

    rejected(config, put_in(m, ["lifecycle", "writer_role"], m["lifecycle"]["username"]))

    for password <- [nil, "", String.duplicate("p", 4097)],
        do: rejected(config, put_in(m, ["lifecycle", "password"], password))
  end

  test "disabled absent invalid and alternate env inputs return only redacted failure" do
    {_, _, config, m} = fixtures()

    for env <- [
          nil,
          [],
          %{},
          %{"MIXER_BROWSER_AUTH_SECRETS" => Jason.encode!(m)},
          %{@var => nil},
          %{@var => m}
        ] do
      check(StartupSecrets.load(env, config) === @failure, "single exact env key")
    end

    for cfg <- [nil, %{}, %Config{}, %{config | mode: :disabled}] do
      check(
        StartupSecrets.load(%{@var => Jason.encode!(m)}, cfg) === @failure,
        "disabled no capabilities"
      )
    end

    {:ok, loaded} = load(config, m)

    for value <- [loaded, loaded.custody, loaded.custody.key] do
      text = inspect(value)

      check(
        not String.contains?(text, [
          m["client"]["value"],
          m["lifecycle"]["password"],
          m["session_vault"]["key_base64"],
          loaded.custody.key.bytes
        ]),
        "Inspect must redact"
      )
    end

    check(inspect(@failure) === "{:error, :session_unavailable}", "generic errors")
  end
end
