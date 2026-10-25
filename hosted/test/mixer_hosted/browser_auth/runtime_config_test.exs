defmodule MixerHosted.BrowserAuth.RuntimeConfigTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest, Custody, RuntimeConfig, Vault}
  alias MixerHosted.Identity.Manifest
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  @error {:error, :session_unavailable}

  defp object do
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

  defp browser_env(object \\ object()) do
    %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }
  end

  defp ordinary_env do
    identity = %{
      "version" => 1,
      "generation" => 1,
      "binding" => "human-main",
      "profiles" => [
        %{
          "profile" => %{
            "profile_id" => "human-main",
            "profile_version" => 7,
            "issuer" => object()["issuer"],
            "audience" => "mixer-api",
            "client_id" => "mixer-console",
            "identity_class" => "human",
            "enabled" => true
          },
          "jwks_endpoint" => %{
            "host" => "identity.example.invalid",
            "port" => 443,
            "path" => "/api/keys"
          },
          "transport" => "hosted_https"
        }
      ],
      "resolvers" => ["1.1.1.1"]
    }

    %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "ep-fixture.us-east-2.aws.neon.tech",
      "MIXER_DATABASE_NAME" => "mixer_fixture",
      "MIXER_DATABASE_USER" => "mixer_ordinary_fixture",
      "MIXER_DATABASE_PASSWORD" => "synthetic-ordinary-password",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-secret-", 8),
      "MIXER_IDENTITY_MODE" => "configured",
      "MIXER_IDENTITY_CONFIG" => Jason.encode!(identity)
    }
  end

  defp hosted, do: HostedConfig.load!(ordinary_env())

  defp lifecycle do
    %{
      username: "mixer_lifecycle_fixture",
      password: "synthetic-lifecycle-password",
      writer_role: "mixer_writer_fixture",
      relation_owner: "mixer_owner_fixture"
    }
  end

  defp custody do
    reference = object()["session_vault_ref"]

    {:ok, custody} =
      Custody.new(reference, %{
        reference: reference,
        key_id: "synthetic-runtime-key-v1",
        key_bytes: :binary.copy(<<71>>, 32)
      })

    custody
  end

  defp construct(hosted \\ hosted(), lifecycle \\ lifecycle(), custody \\ custody()) do
    RuntimeConfig.new(browser_env(), hosted, lifecycle, custody)
  end

  defp with_repo(hosted, key, value), do: %{hosted | repo: Keyword.put(hosted.repo, key, value)}

  defp with_ssl(hosted, key, value),
    do: with_repo(hosted, :ssl, Keyword.put(hosted.repo[:ssl], key, value))

  test "actual ordinary loader Config Manifest Digest and custody compose without startup wiring" do
    hosted = hosted()
    assert {:ok, _} = Manifest.validate(hosted.identity_startup.owner_options[:manifest])
    assert {:ok, config} = Config.load(browser_env(), hosted.role, hosted.identity_startup)
    assert {:ok, digest} = ConfigurationDigest.digest(config)
    assert {:ok, result} = construct(hosted)
    assert result.mode == :configured
    assert result.browser_config == config
    assert result.configuration_digest == digest
    assert byte_size(digest) == 32
    assert result.custody == custody()

    assert Enum.sort(Map.keys(result)) ==
             Enum.sort(
               ~w(__struct__ mode browser_config configuration_digest lifecycle_repo expected_roles custody)a
             )

    assert result.expected_roles == %{
             lifecycle_login: lifecycle().username,
             writer: lifecycle().writer_role,
             relation_owner: lifecycle().relation_owner,
             ordinary_runtime_login: hosted.repo[:username]
           }
  end

  test "dedicated connection derives exact host database and OTP verified TLS with fixed limits" do
    hosted = hosted()
    assert {:ok, result} = construct(hosted)
    repo = result.lifecycle_repo

    assert repo == [
             hostname: hosted.repo[:hostname],
             port: 5432,
             database: hosted.repo[:database],
             username: lifecycle().username,
             password: lifecycle().password,
             pool_size: 2,
             pool_count: 1,
             timeout: 5_000,
             connect_timeout: 5_000,
             queue: false,
             show_sensitive_data_on_connection_error: false,
             ssl: hosted.repo[:ssl]
           ]

    assert repo[:ssl][:customize_hostname_check][:match_fun] ===
             :public_key.pkix_verify_hostname_match_fun(:https)

    assert hosted.database_connection_bound + repo[:pool_size] == 11
    refute repo[:password] == hosted.repo[:password]
    refute Keyword.has_key?(repo, :url)
  end

  test "disabled default and explicit forms have no lifecycle or custody fields on either actual role" do
    for role <- ["api", "processor"] do
      env =
        ordinary_env()
        |> Map.put("MIXER_HOSTED_ROLE", role)
        |> Map.put("MIXER_IDENTITY_MODE", "disabled")
        |> Map.delete("MIXER_IDENTITY_CONFIG")

      hosted = HostedConfig.load!(env)

      for browser <- [%{}, %{"MIXER_BROWSER_AUTH_MODE" => "disabled"}] do
        assert {:ok, result} = RuntimeConfig.new(browser, hosted, nil, nil)
        assert result.mode == :disabled

        assert Enum.all?(Map.from_struct(result), fn {key, value} ->
                 key == :mode or is_nil(value)
               end)
      end
    end
  end

  test "disabled mode rejects stray material and even nil browser CONFIG" do
    hosted = hosted()

    for {lifecycle, custody} <- [{lifecycle(), nil}, {nil, custody()}, {%{}, nil}, {nil, %{}}] do
      assert RuntimeConfig.new(%{}, hosted, lifecycle, custody) == @error
    end

    for value <- [nil, "", "{}", browser_env()["MIXER_BROWSER_AUTH_CONFIG"]] do
      assert RuntimeConfig.new(%{"MIXER_BROWSER_AUTH_CONFIG" => value}, hosted, nil, nil) ==
               @error
    end
  end

  test "browser environment is closed exact string keys with no missing configured input" do
    hosted = hosted()

    for env <- [
          [],
          nil,
          %{"MIXER_BROWSER_AUTH_MODE" => "configured"},
          Map.delete(browser_env(), "MIXER_BROWSER_AUTH_MODE"),
          Map.put(browser_env(), "MIXER_DATABASE_HOST", "evil.invalid"),
          Map.put(browser_env(), :MIXER_BROWSER_AUTH_CONFIG, "{}"),
          Map.put(browser_env(), "resolver", fn -> raise "must not execute" end)
        ] do
      assert RuntimeConfig.new(env, hosted, lifecycle(), custody()) == @error
    end
  end

  test "actual processor role and invalid role cannot be recast as API" do
    hosted = hosted()

    for role <- [:processor, nil, :worker, "api"] do
      assert construct(%{hosted | role: role}) == @error
    end
  end

  test "ordinary startup struct shape is required and extra fields fail closed" do
    hosted = hosted()

    for value <- [nil, [], Map.from_struct(hosted), Map.put(hosted, :resolver, :injected)] do
      assert construct(value) == @error
    end

    for key <- Map.keys(Map.from_struct(hosted)) do
      assert construct(Map.delete(hosted, key)) == @error
    end
  end

  test "current configured identity matching is delegated to the real Config and Manifest" do
    hosted = hosted()
    startup = hosted.identity_startup
    [entry] = startup.owner_options[:manifest]

    for profile <- [
          %{entry.profile | enabled: false},
          %{entry.profile | identity_class: :service},
          %{entry.profile | profile_version: 8},
          %{entry.profile | client_id: "another-client"},
          %{entry.profile | issuer: "https://other.example.invalid"}
        ] do
      options = Keyword.put(startup.owner_options, :manifest, [%{entry | profile: profile}])

      assert construct(%{hosted | identity_startup: %{startup | owner_options: options}}) ==
               @error
    end

    for identity <- [nil, %{startup | mode: :disabled}, Map.from_struct(startup)] do
      assert construct(%{hosted | identity_startup: identity}) == @error
    end
  end

  test "browser configuration mutations fail closed or alter the existing digest as specified" do
    hosted = hosted()
    assert {:ok, base} = construct(hosted)

    for {key, value} <- [
          {"version", 2},
          {"profile_version", 7.0},
          {"profile_id", "other-profile"},
          {"public_origin", "https://console.example.invalid/"},
          {"scope", "openid mixer.workspace.read offline_access"},
          {"client_secret", "synthetic-forbidden"}
        ] do
      env = browser_env(Map.put(object(), key, value))
      assert RuntimeConfig.new(env, hosted, lifecycle(), custody()) == @error
    end

    env =
      browser_env(
        Map.put(object(), "token_endpoint", "https://identity.example.invalid/token-v2")
      )

    assert {:ok, changed} = RuntimeConfig.new(env, hosted, lifecycle(), custody())
    refute changed.configuration_digest == base.configuration_digest
  end

  test "lifecycle settings have exactly four keys and forbid host URL pools keys or hooks" do
    hosted = hosted()

    for key <- Map.keys(lifecycle()) do
      assert construct(hosted, Map.delete(lifecycle(), key)) == @error
    end

    for key <- [
          :hostname,
          :database,
          :port,
          :ssl,
          :url,
          :pool_size,
          :key_bytes,
          :resolver,
          :queue
        ] do
      assert construct(hosted, Map.put(lifecycle(), key, "synthetic-forbidden")) == @error
    end

    for input <- [
          nil,
          [],
          Map.to_list(lifecycle()),
          Map.new(lifecycle(), fn {k, v} -> {to_string(k), v} end)
        ] do
      assert construct(hosted, input) == @error
    end
  end

  test "all four role expectations use provisioning grammar and are pairwise distinct" do
    hosted = hosted()

    for name <- ["x", "_private9", String.duplicate("a", 63)] do
      assert {:ok, _} = construct(hosted, %{lifecycle() | username: name})
    end

    for name <- [
          nil,
          1,
          "",
          "public",
          "pg_read_all_data",
          "Uppercase",
          "9first",
          "role-name",
          "role name",
          "a" <> <<0>>,
          String.duplicate("a", 64)
        ] do
      for field <- [:username, :writer_role, :relation_owner] do
        assert construct(hosted, Map.put(lifecycle(), field, name)) == @error
      end

      assert construct(with_repo(hosted, :username, name)) == @error
    end

    for {left, right} <- [
          {:username, :writer_role},
          {:username, :relation_owner},
          {:writer_role, :relation_owner}
        ] do
      assert construct(hosted, Map.put(lifecycle(), left, lifecycle()[right])) == @error
    end

    for field <- [:username, :writer_role, :relation_owner] do
      assert construct(hosted, Map.put(lifecycle(), field, hosted.repo[:username])) == @error
    end
  end

  test "externally supplied lifecycle password follows the ordinary binary byte bound" do
    hosted = hosted()
    assert {:ok, _} = construct(hosted, %{lifecycle() | password: "x"})
    assert {:ok, _} = construct(hosted, %{lifecycle() | password: :binary.copy(<<255>>, 4096)})

    for password <- [nil, "", [], 1, String.duplicate("x", 4097)] do
      assert construct(hosted, %{lifecycle() | password: password}) == @error
    end
  end

  test "ordinary connection has no missing duplicate unknown or malformed options" do
    hosted = hosted()

    for {key, value} <- hosted.repo do
      assert construct(%{hosted | repo: Keyword.delete(hosted.repo, key)}) == @error
      assert construct(%{hosted | repo: [{key, value} | hosted.repo]}) == @error
    end

    for repo <- [nil, %{}, [], [{"hostname", "db.example.invalid"}], hosted.repo ++ [:bad]] do
      assert construct(%{hosted | repo: repo}) == @error
    end

    for key <- [
          :url,
          :socket,
          :socket_dir,
          :after_connect,
          :configure,
          :parameters,
          :queue,
          :types
        ] do
      assert construct(with_repo(hosted, key, :untrusted)) == @error
    end
  end

  test "ordinary fixed pool bounds timeouts and connection accounting are never silently repaired" do
    hosted = hosted()

    for {key, bad} <- [
          {:port, 5433},
          {:port, 5432.0},
          {:database, ""},
          {:database, String.duplicate("x", 4097)},
          {:password, nil},
          {:pool_size, 1},
          {:pool_size, 21},
          {:pool_size, 8.0},
          {:pool_count, 2},
          {:timeout, :infinity},
          {:timeout, 10_000},
          {:connect_timeout, 10_000},
          {:queue_target, 51},
          {:queue_interval, 2_000},
          {:show_sensitive_data_on_connection_error, true}
        ] do
      assert construct(with_repo(hosted, key, bad)) == @error
    end

    for bound <- [nil, 8, 10, 9.0] do
      assert construct(%{hosted | database_connection_bound: bound}) == @error
    end

    for pool <- [2, 20] do
      config = %{with_repo(hosted, :pool_size, pool) | database_connection_bound: pool + 1}
      assert {:ok, result} = construct(config)
      assert result.lifecycle_repo[:pool_size] == 2
    end
  end

  test "direct canonical DNS host policy rejects pooler URL IP and alias mutations" do
    hosted = hosted()

    for host <- [
          nil,
          "localhost",
          "127.0.0.1",
          "::1",
          "ep-fixture-pooler.us-east-2.aws.neon.tech",
          "https://db.example.invalid",
          "user:synthetic@db.example.invalid",
          "db.example.invalid?sslmode=disable",
          "DB.example.invalid",
          "db.example.invalid.",
          "db..example.invalid",
          "-db.example.invalid",
          "db-.example.invalid",
          "db.example.invalid\n",
          String.duplicate("a", 64) <> ".example.invalid"
        ] do
      # Update SNI too: rejection must be the host policy rather than only mismatch.
      config = with_repo(hosted, :hostname, host)

      config =
        if is_binary(host),
          do: with_ssl(config, :server_name_indication, String.to_charlist(host)),
          else: config

      assert construct(config) == @error
    end
  end

  test "TLS exact closed options reject weakening duplicate keys and extra callbacks" do
    hosted = hosted()
    ssl = hosted.repo[:ssl]

    for {key, value} <- ssl do
      assert construct(with_repo(hosted, :ssl, Keyword.delete(ssl, key))) == @error
      assert construct(with_repo(hosted, :ssl, [{key, value} | ssl])) == @error
    end

    for ssl <- [nil, false, true, %{}, [], ssl ++ [versions: [:"tlsv1.2"]]] do
      assert construct(with_repo(hosted, :ssl, ssl)) == @error
    end

    for {key, value} <- [
          {:verify, :verify_none},
          {:server_name_indication, ~c"other.example.invalid"},
          {:server_name_indication, :disable},
          {:cacerts, []},
          {:cacerts, ["synthetic-not-a-certificate"]},
          {:customize_hostname_check, []},
          {:customize_hostname_check, [match_fun: nil]},
          {:customize_hostname_check,
           [match_fun: :public_key.pkix_verify_hostname_match_fun(:https), wildcard: true]}
        ] do
      assert construct(with_ssl(hosted, key, value)) == @error
    end
  end

  test "TLS roots retain loader tuple or DER forms but reject corrupted cached decode" do
    hosted = hosted()
    [first | _] = hosted.repo[:ssl][:cacerts]

    der =
      case first do
        {:cert, der, _} -> der
        der -> der
      end

    assert {:ok, result} = construct(with_ssl(hosted, :cacerts, [der]))
    assert result.lifecycle_repo[:ssl][:cacerts] == [der]
    assert construct(with_ssl(hosted, :cacerts, [{:cert, der, :forged_decode}])) == @error
  end

  test "untrusted callback is never evaluated even when it claims the expected hostname behavior" do
    caller = self()

    hook = fn _, _ ->
      send(caller, :unexpected_tls_hook)
      true
    end

    hosted = hosted()

    for match_options <- [[match_fun: hook], [match_fun: hook, match_fun: hook]] do
      assert construct(with_ssl(hosted, :customize_hostname_check, match_options)) == @error
    end

    assert construct(
             with_repo(hosted, :after_connect, fn _ -> send(caller, :unexpected_tls_hook) end)
           ) == @error

    assert construct(hosted, Map.put(lifecycle(), :resolver, hook)) == @error
    refute_received :unexpected_tls_hook
  end

  test "custody reference key type key bounds and exact struct keys are revalidated" do
    hosted = hosted()
    original = custody()

    for candidate <- [
          nil,
          original.key,
          Map.from_struct(original),
          %{original | reference: "vault://mixer/other"},
          %{original | key: Map.from_struct(original.key)},
          %{original | key: %{original.key | bytes: "short"}},
          %{original | key: %{original.key | id: "invalid/key"}},
          Map.put(original, :resolver, :forbidden),
          %{original | key: Map.put(original.key, :fallback, :forbidden)}
        ] do
      assert construct(hosted, lifecycle(), candidate) == @error
    end
  end

  test "runtime key and configuration digest perform the actual existing Vault context binding" do
    assert {:ok, config} = construct()
    csrf = Base.url_encode64(:binary.copy(<<17>>, 32), padding: false)

    context = %{
      purpose: :preauth,
      browser_id: :binary.copy(<<11>>, 16),
      cookie_digest: :binary.copy(<<12>>, 32),
      csrf_digest: :crypto.hash(:sha256, csrf),
      epoch: 1,
      revision: 1,
      generation: Base.url_encode64(:binary.copy(<<13>>, 32), padding: false),
      vault_generation: 1,
      config_digest: config.configuration_digest,
      profile_id: config.browser_config.profile_id,
      profile_version: config.browser_config.profile_version,
      principal_id: nil,
      family_id: nil,
      credential_ref: nil,
      credential_revision: nil
    }

    envelope = %Vault.Preauth{csrf: csrf}
    assert {:ok, sealed} = Vault.seal(config.custody.key, context, envelope)
    assert {:ok, ^envelope} = Vault.open(config.custody.key, context, sealed)

    env =
      browser_env(
        Map.put(object(), "token_endpoint", "https://identity.example.invalid/token-v2")
      )

    assert {:ok, changed} = RuntimeConfig.new(env, hosted(), lifecycle(), custody())

    assert {:error, :vault_unavailable} =
             Vault.open(
               config.custody.key,
               %{context | config_digest: changed.configuration_digest},
               sealed
             )
  end

  test "Inspect reports only mode and added pool bound and errors echo no data" do
    assert {:ok, config} = construct()

    assert inspect(config) ==
             "#MixerHosted.BrowserAuth.RuntimeConfig<mode: :configured, lifecycle_connection_bound: 2>"

    for secret <- [
          "synthetic",
          "vault://",
          "secret://",
          "example.invalid",
          "human-main",
          "mixer_lifecycle_fixture",
          "mixer_fixture"
        ] do
      refute inspect(config) =~ secret
    end

    assert construct(hosted(), %{lifecycle() | password: ""}) == @error
    assert RuntimeConfig.new(%{}, hosted(), nil, "synthetic-secret") == @error
  end
end
