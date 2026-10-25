defmodule ConstructorReview.Fixtures do
  alias MixerHosted.BrowserAuth.{Config, Custody, RuntimeConfig}
  alias MixerHosted.RuntimeConfig, as: Hosted

  def object do
    %{
      "version" => 1,
      "public_origin" => "https://console.review.example",
      "profile_id" => "review-human",
      "profile_version" => 3,
      "issuer" => "https://identity.review.example",
      "client_id" => "review-client",
      "api_audience" => "review-api",
      "authorization_endpoint" => "https://identity.review.example/authorize",
      "token_endpoint" => "https://identity.review.example/token",
      "id_token_jwks_endpoint" => "https://identity.review.example/jwks",
      "redirect_uri" => "https://console.review.example/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://review/client",
      "session_vault_ref" => reference(),
      "scope" => "openid mixer.workspace.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }
  end

  def reference, do: "vault://review/session"
  def key_bytes, do: :binary.copy(<<177>>, 32)
  def key_id, do: "review-vault-key"

  def identity_object do
    %{
      "version" => 1,
      "generation" => 9,
      "binding" => "review-human",
      "profiles" => [
        %{
          "profile" => %{
            "profile_id" => "review-human",
            "profile_version" => 3,
            "issuer" => "https://identity.review.example",
            "audience" => "review-api",
            "client_id" => "review-client",
            "identity_class" => "human",
            "enabled" => true
          },
          "jwks_endpoint" => %{
            "host" => "identity.review.example",
            "port" => 443,
            "path" => "/jwks"
          },
          "transport" => "hosted_https"
        }
      ],
      "resolvers" => ["1.1.1.1"]
    }
  end

  def hosted_env do
    %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "ep-review.us-east-2.aws.neon.tech",
      "MIXER_DATABASE_NAME" => "review-database",
      "MIXER_DATABASE_USER" => "review_runtime",
      "MIXER_DATABASE_PASSWORD" => "synthetic-ordinary-secret",
      "MIXER_DATABASE_POOL_SIZE" => "8",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("review-secret-base", 5),
      "MIXER_IDENTITY_MODE" => "configured",
      "MIXER_IDENTITY_CONFIG" => Jason.encode!(identity_object())
    }
  end

  # This is the actual ordinary startup loader, called only for test setup. It
  # reads local OTP CA roots; no connection, owner, app, resolver or route starts.
  def hosted(overrides \\ %{}), do: Hosted.load!(Map.merge(hosted_env(), overrides))

  def browser(object \\ object()) do
    %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }
  end

  def lifecycle do
    %{
      username: "review_lifecycle",
      password: "synthetic-lifecycle-secret",
      writer_role: "review_writer",
      relation_owner: "review_owner"
    }
  end

  def material(ref \\ reference()),
    do: %{reference: ref, key_id: key_id(), key_bytes: key_bytes()}

  def custody do
    {:ok, custody} = Custody.new(reference(), material())
    custody
  end

  def configured(
        hosted \\ hosted(),
        browser \\ browser(),
        lifecycle \\ lifecycle(),
        custody \\ custody()
      ),
      do: RuntimeConfig.new(browser, hosted, lifecycle, custody)

  def repo(hosted, key, value), do: %{hosted | repo: Keyword.put(hosted.repo, key, value)}

  def ssl(hosted, key, value),
    do: repo(hosted, :ssl, Keyword.put(hosted.repo[:ssl], key, value))

  def identity(hosted, alter) do
    startup = hosted.identity_startup
    entries = startup.owner_options[:manifest]
    [entry] = entries
    replacement = alter.(entry)

    %{
      hosted
      | identity_startup: %{
          startup
          | owner_options: Keyword.put(startup.owner_options, :manifest, [replacement])
        }
    }
  end

  def ordinary_config(hosted, browser \\ browser()),
    do: Config.load(browser, hosted.role, hosted.identity_startup)
end

defmodule ConstructorReview.Probes do
  use ExUnit.Case, async: false
  alias ConstructorReview.Fixtures, as: F
  alias MixerHosted.BrowserAuth.{ConfigurationDigest, Custody, RuntimeConfig, Vault}
  alias MixerHosted.Identity.StartupConfig
  @error {:error, :session_unavailable}

  test "actual ordinary loader values bind browser config, roles, digest and retained TLS" do
    hosted = F.hosted()
    {:ok, config} = F.configured(hosted)
    {:ok, ordinary} = F.ordinary_config(hosted)
    assert config.browser_config === ordinary
    assert {:ok, config.configuration_digest} === ConfigurationDigest.digest(ordinary)

    assert config.expected_roles === %{
             lifecycle_login: "review_lifecycle",
             writer: "review_writer",
             relation_owner: "review_owner",
             ordinary_runtime_login: "review_runtime"
           }

    assert config.custody === F.custody()

    assert Enum.sort(Map.keys(config)) ===
             Enum.sort([
               :__struct__,
               :mode,
               :browser_config,
               :configuration_digest,
               :lifecycle_repo,
               :expected_roles,
               :custody
             ])

    assert config.lifecycle_repo[:ssl] === hosted.repo[:ssl]

    assert config.lifecycle_repo[:ssl][:customize_hostname_check][:match_fun] ===
             hosted.repo[:ssl][:customize_hostname_check][:match_fun]
  end

  test "derived connection has exactly fixed pool two, no queue and five second deadlines" do
    for pool <- [2, 8, 20] do
      hosted = F.hosted(%{"MIXER_DATABASE_POOL_SIZE" => Integer.to_string(pool)})
      {:ok, config} = F.configured(hosted)

      expected = [
        hostname: hosted.repo[:hostname],
        port: 5432,
        database: hosted.repo[:database],
        username: F.lifecycle().username,
        password: F.lifecycle().password,
        pool_size: 2,
        pool_count: 1,
        timeout: 5_000,
        connect_timeout: 5_000,
        queue: false,
        show_sensitive_data_on_connection_error: false,
        ssl: hosted.repo[:ssl]
      ]

      assert config.lifecycle_repo === expected
      assert hosted.database_connection_bound + config.lifecycle_repo[:pool_size] === pool + 3
    end
  end

  test "configured role comes from ordinary startup and processor cannot be cast as API" do
    processor =
      F.hosted_env()
      |> Map.put("MIXER_HOSTED_ROLE", "processor")
      |> Map.put("MIXER_IDENTITY_MODE", "disabled")
      |> Map.delete("MIXER_IDENTITY_CONFIG")
      |> MixerHosted.RuntimeConfig.load!()

    assert processor.role === :processor
    assert @error === F.configured(processor)
    assert @error === F.configured(%{F.hosted() | role: :processor})

    for role <- [nil, "api", :unknown, 1] do
      assert @error === F.configured(%{F.hosted() | role: role})
    end
  end

  test "actual disabled identity startup, mismatched binding and identity class deny" do
    disabled = StartupConfig.load!(%{}, :api, [])
    assert @error === F.configured(%{F.hosted() | identity_startup: disabled})

    for change <- [
          fn e -> put_in(e.profile.enabled, false) end,
          fn e -> put_in(e.profile.identity_class, :service) end,
          fn e -> put_in(e.profile.profile_version, 4) end,
          fn e -> put_in(e.profile.issuer, "https://other.review.example") end,
          fn e -> put_in(e.profile.client_id, "other-client") end,
          fn e -> put_in(e.profile.audience, "other-api") end,
          fn e -> put_in(e.profile.profile_id, "other-profile") end,
          fn e -> Map.put(e, :unknown, true) end,
          fn e -> %{e | jwks_endpoint: Map.put(e.jwks_endpoint, :unknown, true)} end
        ] do
      assert @error === F.configured(F.identity(F.hosted(), change))
    end

    startup = F.hosted().identity_startup
    duplicate = %{startup | owner_options: startup.owner_options ++ [binding: "other"]}
    assert @error === F.configured(%{F.hosted() | identity_startup: duplicate})
    assert @error === F.configured(%{F.hosted() | identity_startup: Map.from_struct(startup)})
  end

  test "browser environment is closed, string-keyed and duplicate JSON preserving" do
    hosted = F.hosted()

    for input <- [
          nil,
          [],
          [MIXER_BROWSER_AUTH_MODE: "configured"],
          Map.put(F.browser(), "UNKNOWN", "secret"),
          Map.put(F.browser(), :MIXER_BROWSER_AUTH_MODE, "configured"),
          Map.delete(F.browser(), "MIXER_BROWSER_AUTH_MODE"),
          Map.delete(F.browser(), "MIXER_BROWSER_AUTH_CONFIG"),
          Map.put(F.browser(), "MIXER_BROWSER_AUTH_MODE", :configured),
          Map.put(F.browser(), "MIXER_BROWSER_AUTH_CONFIG", %{}),
          Map.put(F.browser(), "MIXER_BROWSER_AUTH_CONFIG", <<255>>)
        ] do
      assert @error === F.configured(hosted, input)
    end

    raw = F.browser()["MIXER_BROWSER_AUTH_CONFIG"]
    duplicate = String.replace_prefix(raw, "{", ~s({"client_id":"other",))

    assert @error ===
             F.configured(hosted, Map.put(F.browser(), "MIXER_BROWSER_AUTH_CONFIG", duplicate))

    escaped = String.replace_prefix(raw, "{", ~s({"client\\u005fid":"other",))

    assert @error ===
             F.configured(hosted, Map.put(F.browser(), "MIXER_BROWSER_AUTH_CONFIG", escaped))
  end

  test "disabled accepts empty or explicit mode only and requires nil lifecycle and custody" do
    hosted = F.hosted()

    for env <- [%{}, %{"MIXER_BROWSER_AUTH_MODE" => "disabled"}] do
      assert {:ok, disabled} = RuntimeConfig.new(env, hosted, nil, nil)

      assert Map.from_struct(disabled) === %{
               mode: :disabled,
               browser_config: nil,
               configuration_digest: nil,
               lifecycle_repo: nil,
               expected_roles: nil,
               custody: nil
             }

      for lifecycle <- [%{}, F.lifecycle(), []] do
        assert @error === RuntimeConfig.new(env, hosted, lifecycle, nil)
      end

      for custody <- [%{}, F.custody(), []] do
        assert @error === RuntimeConfig.new(env, hosted, nil, custody)
      end
    end

    for env <- [
          %{"MIXER_BROWSER_AUTH_CONFIG" => nil},
          %{"MIXER_BROWSER_AUTH_MODE" => "disabled", "MIXER_BROWSER_AUTH_CONFIG" => nil},
          %{"MIXER_BROWSER_AUTH_MODE" => "disabled", "unknown" => true}
        ] do
      assert @error === RuntimeConfig.new(env, hosted, nil, nil)
    end
  end

  test "hosted struct is exact and no positional repo or identity config substitutes" do
    hosted = F.hosted()

    for value <- [
          nil,
          %{},
          Map.from_struct(hosted),
          hosted.repo,
          Map.put(hosted, :injected, true),
          Map.delete(hosted, :role),
          Map.delete(hosted, :repo),
          Map.delete(hosted, :identity_startup),
          Map.delete(hosted, :database_connection_bound)
        ] do
      assert @error === F.configured(value)
    end
  end

  test "lifecycle input is exact map with no overriding connection or callback knobs" do
    hosted = F.hosted()

    for value <-
          [nil, [], Map.to_list(F.lifecycle())] ++
            Enum.map(Map.keys(F.lifecycle()), &Map.delete(F.lifecycle(), &1)) ++
            Enum.map(
              [
                :hostname,
                :database,
                :port,
                :pool_size,
                :pool_count,
                :timeout,
                :queue,
                :ssl,
                :url,
                :resolver,
                :callback,
                :key_bytes,
                :credential_ref,
                :__struct__
              ],
              &Map.put(F.lifecycle(), &1, "forbidden")
            ) do
      assert @error === F.configured(hosted, F.browser(), value)
    end
  end

  test "all four role names use exact restricted grammar and are distinct pairwise" do
    hosted = F.hosted()
    roles = [:username, :writer_role, :relation_owner]

    invalid = [
      "",
      "public",
      "pg_admin",
      "Pg_admin",
      "Upper",
      "0name",
      "name-1",
      "name.x",
      "name\"",
      "name;select",
      "name name",
      "name\n",
      "name" <> <<0>>,
      <<255>>,
      nil,
      String.duplicate("a", 64)
    ]

    for key <- roles, value <- invalid do
      assert @error === F.configured(hosted, F.browser(), Map.put(F.lifecycle(), key, value))
    end

    for key <- roles do
      assert @error ===
               F.configured(
                 hosted,
                 F.browser(),
                 Map.put(F.lifecycle(), key, hosted.repo[:username])
               )
    end

    for {first, second} <- [
          {:username, :writer_role},
          {:username, :relation_owner},
          {:writer_role, :relation_owner}
        ] do
      assert @error ===
               F.configured(
                 hosted,
                 F.browser(),
                 Map.put(F.lifecycle(), first, Map.fetch!(F.lifecycle(), second))
               )
    end

    for name <- ["_", "a", "a0", String.duplicate("a", 63)] do
      assert {:ok, _} =
               F.configured(hosted, F.browser(), Map.put(F.lifecycle(), :writer_role, name))
    end

    for invalid_name <- invalid do
      assert @error === F.configured(F.repo(hosted, :username, invalid_name))
    end
  end

  test "opaque credentials and database retain ordinary byte bounds without text invention" do
    hosted = F.hosted()

    for value <- ["", nil, 2, [], String.duplicate("x", 4097)] do
      assert @error === F.configured(hosted, F.browser(), %{F.lifecycle() | password: value})

      for key <- [:database, :password] do
        assert @error === F.configured(F.repo(hosted, key, value))
      end
    end

    for value <- ["x", String.duplicate("x", 4096), <<0, 255, 254, 1>>] do
      assert {:ok, got} = F.configured(hosted, F.browser(), %{F.lifecycle() | password: value})
      assert got.lifecycle_repo[:password] === value

      for key <- [:database, :password] do
        assert {:ok, _} = F.configured(F.repo(hosted, key, value))
      end
    end
  end

  test "ordinary repo rejects open maps, missing unknown and duplicate keyword members" do
    hosted = F.hosted()

    for repo <-
          [nil, %{}, Map.new(hosted.repo), [{"hostname", "host"}]] ++
            Enum.map(Keyword.keys(hosted.repo), &Keyword.delete(hosted.repo, &1)) ++
            Enum.map(Keyword.keys(hosted.repo), &(hosted.repo ++ [{&1, hosted.repo[&1]}])) ++
            Enum.map(
              [
                :url,
                :socket,
                :parameters,
                :after_connect,
                :prepare,
                :queue,
                :pool,
                :database_host
              ],
              &(hosted.repo ++ [{&1, true}])
            ) do
      assert @error === F.configured(%{hosted | repo: repo})
    end
  end

  test "ordinary pool deadlines and sensitive-error policy cannot weaken" do
    hosted = F.hosted()

    changes = [
      port: 6432,
      port: "5432",
      port: 5432.0,
      pool_size: 1,
      pool_size: 21,
      pool_size: 8.0,
      pool_count: 2,
      timeout: 5_001,
      timeout: :infinity,
      connect_timeout: 5_001,
      queue_target: 51,
      queue_interval: 1_001,
      show_sensitive_data_on_connection_error: true
    ]

    for {key, value} <- changes, do: assert(@error === F.configured(F.repo(hosted, key, value)))

    for bound <- [nil, 8, 10, 9.0, -1] do
      assert @error === F.configured(%{hosted | database_connection_bound: bound})
    end
  end

  test "direct DNS host policy denies pooler, IPs, URI aliases, NUL and invalid UTF8" do
    hosted = F.hosted()

    for host <- [
          "",
          "localhost",
          "127.0.0.1",
          "1.2.3.4",
          "::1",
          "[::1]",
          "a-pooler.review.example",
          "a-pooler-x.review.example",
          "HOST.example",
          "https://host.example",
          "host.example:5432",
          "host.example.",
          "a..example",
          "-a.example",
          "a-.example",
          "a_b.example",
          "a.example" <> <<0>>,
          <<255, 46, 97>>,
          String.duplicate("a", 64) <> ".example",
          String.duplicate("a.", 127)
        ] do
      assert @error === F.configured(F.repo(hosted, :hostname, host))
    end

    for host <- ["a.example", "a-pool.review.example", String.duplicate("a", 63) <> ".example"] do
      adjusted =
        hosted
        |> F.repo(:hostname, host)
        |> F.ssl(:server_name_indication, String.to_charlist(host))

      assert {:ok, got} = F.configured(adjusted)
      assert got.lifecycle_repo[:hostname] === host
    end
  end

  test "TLS verifies exact SNI, roots, closed lists and loader matcher identity" do
    hosted = F.hosted()
    ssl = hosted.repo[:ssl]

    for bad_ssl <-
          [nil, false, true, Map.new(ssl)] ++
            Enum.map(Keyword.keys(ssl), &Keyword.delete(ssl, &1)) ++
            Enum.map(Keyword.keys(ssl), &(ssl ++ [{&1, ssl[&1]}])) ++
            [ssl ++ [depth: 0], ssl ++ [verify_fun: fn _, _, _ -> {:valid, nil} end]] do
      assert @error === F.configured(F.repo(hosted, :ssl, bad_ssl))
    end

    for value <- [:verify_none, nil, true],
        do: assert(@error === F.configured(F.ssl(hosted, :verify, value)))

    for value <- [hosted.repo[:hostname], ~c"other.example", [], false] do
      assert @error === F.configured(F.ssl(hosted, :server_name_indication, value))
    end

    matcher = ssl[:customize_hostname_check][:match_fun]

    for value <- [
          [],
          %{match_fun: matcher},
          [match_fun: matcher, match_fun: matcher],
          [match_fun: matcher, unknown: true],
          [match_fun: nil]
        ] do
      assert @error === F.configured(F.ssl(hosted, :customize_hostname_check, value))
    end
  end

  test "malicious TLS callback is never executed even when it could claim success" do
    hosted = F.hosted()
    marker = make_ref()

    callback = fn _, _ ->
      send(self(), marker)
      true
    end

    assert @error === F.configured(F.ssl(hosted, :customize_hostname_check, match_fun: callback))
    refute_received ^marker
    thrower = fn _, _ -> throw(:should_never_run) end
    assert @error === F.configured(F.ssl(hosted, :customize_hostname_check, match_fun: thrower))
    {:ok, got} = F.configured(hosted)

    assert got.lifecycle_repo[:ssl][:customize_hostname_check][:match_fun] ===
             hosted.repo[:ssl][:customize_hostname_check][:match_fun]
  end

  test "malformed, empty and mismatched decoded TLS roots deny without exception echo" do
    hosted = F.hosted()

    for roots <- [
          [],
          nil,
          false,
          [<<>>],
          [<<1, 2, 3>>],
          [:not_a_cert],
          ["-----BEGIN CERTIFICATE-----"],
          [{:cert, <<1>>, :bad}],
          [hd(hosted.repo[:ssl][:cacerts]), :bad]
        ] do
      assert @error === F.configured(F.ssl(hosted, :cacerts, roots))
    end

    first = hd(hosted.repo[:ssl][:cacerts])

    der =
      case first do
        {:cert, der, _} -> der
        der -> der
      end

    assert {:ok, _} = F.configured(F.ssl(hosted, :cacerts, [der]))
    decoded = :public_key.pkix_decode_cert(der, :otp)
    assert {:ok, _} = F.configured(F.ssl(hosted, :cacerts, [{:cert, der, decoded}]))

    assert @error ===
             F.configured(F.ssl(hosted, :cacerts, [{:cert, der, :different_decoded_certificate}]))
  end

  test "Custody material requires exact reference and exact three-key external map" do
    ref = F.reference()
    assert {:ok, custody} = Custody.new(ref, F.material())
    assert custody.reference === ref
    assert {:ok, custody.key} === Vault.key(F.key_id(), F.key_bytes())

    for value <-
          [
            nil,
            [],
            Map.to_list(F.material()),
            Map.from_struct(custody),
            Map.put(F.material(), :unknown, "secret"),
            Map.put(F.material(), :__struct__, Custody)
          ] ++
            Enum.map(Map.keys(F.material()), &Map.delete(F.material(), &1)) do
      assert @error === Custody.new(ref, value)
    end

    assert @error === Custody.new("vault://review/other", F.material())
    assert @error === Custody.new(ref, %{F.material() | reference: ref <> "-other"})
  end

  test "Custody canonical references enforce UTF8-free ASCII grammar and exact size" do
    for ref <- [
          nil,
          "",
          "vault://",
          "secret://review/session",
          "VAULT://review/session",
          "vault:///x",
          "vault://x/",
          "vault://x//y",
          "vault://x/.",
          "vault://x/..",
          "vault://x?a=b",
          "vault://x#f",
          "vault://x%2fy",
          "vault://x y",
          "vault://x@y",
          "vault://x" <> <<0>>,
          "vault://" <> <<255>>,
          "vault://é",
          "vault://" <> String.duplicate("a", 249)
        ] do
      assert @error === Custody.new(ref, F.material(ref))
    end

    for ref <- ["vault://a", "vault://a-b.c_d/X_Y-9", "vault://" <> String.duplicate("a", 248)] do
      assert {:ok, custody} = Custody.new(ref, F.material(ref))
      assert custody.reference === ref
    end
  end

  test "Custody uses actual Vault key bounds including 32 raw arbitrary bytes" do
    for id <- [nil, "", "a b", "a/1", "a" <> <<0>>, <<255>>, "é", String.duplicate("a", 129)] do
      assert @error === Custody.new(F.reference(), %{F.material() | key_id: id})
    end

    for bytes <- [nil, "", [], :binary.copy(<<1>>, 31), :binary.copy(<<1>>, 33)] do
      assert @error === Custody.new(F.reference(), %{F.material() | key_bytes: bytes})
    end

    for id <- ["a", "A-._9", String.duplicate("a", 128)],
        bytes <- [:binary.copy(<<0>>, 32), :binary.copy(<<255>>, 32)] do
      assert {:ok, got} =
               Custody.new(F.reference(), %{F.material() | key_id: id, key_bytes: bytes})

      assert got.key.bytes === bytes
    end
  end

  test "runtime revalidates exact Custody and Vault.Key closed shape and configured reference" do
    hosted = F.hosted()
    custody = F.custody()

    for value <- [
          nil,
          %{},
          Map.from_struct(custody),
          Map.put(custody, :extra, true),
          %{custody | reference: "vault://other/key"},
          %{custody | key: Map.from_struct(custody.key)},
          %{custody | key: Map.put(custody.key, :extra, true)},
          %{custody | key: %{custody.key | id: "bad key"}},
          %{custody | key: %{custody.key | bytes: <<1>>}}
        ] do
      assert @error === F.configured(hosted, F.browser(), F.lifecycle(), value)
    end
  end

  test "browser metadata NUL, invalid UTF8 and upper text bounds remain ordinary Config gates" do
    hosted = F.hosted()

    for {key, limit} <- [{"profile_id", 128}, {"client_id", 256}, {"api_audience", 256}],
        value <- ["", "x" <> <<0>>, String.duplicate("x", limit + 1)] do
      assert @error === F.configured(hosted, F.browser(Map.put(F.object(), key, value)))
    end

    raw = F.browser()["MIXER_BROWSER_AUTH_CONFIG"]

    assert @error ===
             F.configured(
               hosted,
               Map.put(F.browser(), "MIXER_BROWSER_AUTH_CONFIG", raw <> <<255>>)
             )

    assert @error ===
             F.configured(
               hosted,
               Map.put(F.browser(), "MIXER_BROWSER_AUTH_CONFIG", String.duplicate(" ", 16_385))
             )

    for key <- ["client_credential_ref", "session_vault_ref"] do
      assert @error ===
               F.configured(
                 hosted,
                 F.browser(Map.put(F.object(), key, "vault://" <> String.duplicate("a", 256)))
               )
    end
  end

  test "accepted configuration changes alter digest while credentials and raw key do not enter it" do
    hosted = F.hosted()
    {:ok, first} = F.configured(hosted)

    {:ok, second} =
      F.configured(hosted, F.browser(), %{F.lifecycle() | password: "different-synthetic-secret"})

    {:ok, key} =
      Custody.new(F.reference(), %{
        F.material()
        | key_id: "other-key",
          key_bytes: :binary.copy(<<5>>, 32)
      })

    {:ok, third} = F.configured(hosted, F.browser(), F.lifecycle(), key)
    assert first.configuration_digest === second.configuration_digest
    assert first.configuration_digest === third.configuration_digest

    changed =
      Map.put(F.object(), "public_origin", "https://other.review.example")
      |> Map.put("redirect_uri", "https://other.review.example/auth/callback")

    {:ok, fourth} = F.configured(hosted, F.browser(changed))
    refute first.configuration_digest === fourth.configuration_digest
    {:ok, canonical} = ConfigurationDigest.canonical_bytes(first.browser_config)

    for value <- [F.key_id(), F.key_bytes(), F.lifecycle().password, hosted.repo[:password]] do
      refute :binary.match(canonical, value) != :nomatch
    end
  end

  test "Inspect and every public error keep secrets, references, endpoints and identity absent" do
    hosted = F.hosted()
    {:ok, got} = F.configured(hosted)

    for output <- [
          inspect(got),
          inspect(F.custody()),
          inspect(F.custody().key),
          inspect(F.configured(F.ssl(hosted, :cacerts, ["synthetic-malformed-root"])))
        ] do
      for forbidden <- [
            F.reference(),
            F.key_id(),
            F.key_bytes(),
            F.lifecycle().password,
            hosted.repo[:password],
            hosted.repo[:hostname],
            F.object()["issuer"],
            F.object()["profile_id"],
            F.object()["client_credential_ref"],
            F.object()["client_id"]
          ] do
        refute String.contains?(output, forbidden)
      end
    end

    assert inspect(got) ===
             "#MixerHosted.BrowserAuth.RuntimeConfig<mode: :configured, lifecycle_connection_bound: 2>"

    {:ok, disabled} = RuntimeConfig.new(%{}, hosted, nil, nil)

    assert inspect(disabled) ===
             "#MixerHosted.BrowserAuth.RuntimeConfig<mode: :disabled, lifecycle_connection_bound: 0>"

    assert @error === F.configured(hosted, F.browser(), %{F.lifecycle() | password: nil})
  end

  test "constructors add no I/O or mutable effects beyond existing URI default-port reads" do
    hosted = F.hosted()
    browser = F.browser()
    lifecycle = F.lifecycle()
    custody = F.custody()
    assert {:ok, _} = F.configured(hosted, browser, lifecycle, custody)

    patterns = [
      {System, :get_env, :_},
      {System, :put_env, :_},
      {System, :delete_env, :_},
      {System, :cmd, :_},
      {Application, :get_env, :_},
      {Application, :fetch_env, :_},
      {Application, :fetch_env!, :_},
      {Application, :put_env, :_},
      {Application, :delete_env, :_},
      {Application, :start, :_},
      {Application, :ensure_all_started, :_},
      {:os, :getenv, :_},
      {:os, :putenv, :_},
      {:os, :cmd, :_},
      {:file, :_, :_},
      {:prim_file, :_, :_},
      {:gen_tcp, :_, :_},
      {:ssl, :_, :_},
      {:inet, :getaddr, :_},
      {:inet, :getaddrs, :_},
      {:inet, :gethostbyname, :_},
      {:ets, :_, :_},
      {:elixir_config, :get, :_},
      {:persistent_term, :_, :_},
      {:public_key, :cacerts_get, :_},
      {:crypto, :strong_rand_bytes, :_},
      {:erlang, :open_port, :_},
      {:erlang, :spawn, :_},
      {:erlang, :spawn_link, :_},
      {:erlang, :spawn_monitor, :_}
    ]

    Enum.each(patterns, fn {module, _, _} -> Code.ensure_loaded(module) end)
    owner = self()
    collector = spawn(fn -> collect(owner, []) end)
    Enum.each(patterns, &:erlang.trace_pattern(&1, [{:_, [], [{:message, {:caller}}]}], [:local]))
    :erlang.trace(self(), true, [:call, :arity, :procs, :ports, {:tracer, collector}])

    try do
      assert {:ok, _} = RuntimeConfig.new(browser, hosted, lifecycle, custody)
      assert {:ok, _} = RuntimeConfig.new(%{}, hosted, nil, nil)
      assert {:ok, _} = Custody.new(F.reference(), F.material())
      assert @error === RuntimeConfig.new(browser, hosted, %{}, nil)
      assert @error === Custody.new(F.reference(), %{})
    after
      :erlang.trace(self(), false, [:all])
      Enum.each(patterns, &:erlang.trace_pattern(&1, false, [:local]))
    end

    delivered = :erlang.trace_delivered(self())
    assert_receive {:trace_delivered, _, ^delivered}, 5_000
    send(collector, :finish)
    assert_receive {:constructor_effects, effects}, 5_000
    # Ordinary Config/Manifest call URI.new/1. Its default-port lookup consults
    # Elixir's pre-existing URI table; do not claim transitive zero global reads.
    expected = [
      {:call, {:ets, :lookup, 2}, {:elixir_config, :get, 2}},
      {:call, {:elixir_config, :get, 2}, {URI, :default_port, 1}}
    ]
    sanitized = Enum.map(effects, fn {:trace, _pid, kind, operation, caller} ->
      {kind, operation, caller}
    end)
    assert Enum.all?(sanitized, &(&1 in expected))
    assert Enum.count(sanitized, &(&1 === hd(expected))) === 12
    assert Enum.count(sanitized, &(&1 === List.last(expected))) === 12
  end

  defp collect(owner, effects) do
    receive do
      :finish -> send(owner, {:constructor_effects, Enum.reverse(effects)})
      # With :arity tracing no raw arguments or secret fields are retained.
      event -> collect(owner, [event | effects])
    end
  end
end

