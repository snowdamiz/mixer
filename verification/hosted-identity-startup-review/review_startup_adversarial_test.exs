defmodule MixerHosted.Identity.ReviewStartupAdversarialTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Identity.StartupConfig

  defp object do
    %{
      "version" => 1,
      "generation" => 1,
      "binding" => "independent-review-marker",
      "profiles" => [
        %{
          "profile" => %{
            "profile_id" => "independent-review-marker",
            "profile_version" => 1,
            "issuer" => "https://issuer.independent.invalid/review",
            "audience" => "review-audience",
            "client_id" => "review-client",
            "identity_class" => "service",
            "enabled" => true
          },
          "jwks_endpoint" => %{
            "host" => "keys.independent.invalid",
            "port" => 443,
            "path" => "/review/keys"
          },
          "transport" => "hosted_https"
        }
      ],
      "resolvers" => ["127.0.0.1", "::1"]
    }
  end

  defp roots do
    [root | _] = :public_key.cacerts_get()

    case root do
      {:cert, der, _} -> [der]
      der -> [der]
    end
  end

  defp load(raw, ca \\ nil) do
    StartupConfig.load!(
      %{"MIXER_IDENTITY_MODE" => "configured", "MIXER_IDENTITY_CONFIG" => raw},
      :api,
      ca || roots()
    )
  end

  defp reject(raw, ca \\ nil, reason \\ "configuration") do
    assert_raise ArgumentError, "invalid identity startup: " <> reason, fn -> load(raw, ca) end
  end

  test "IR01 decoded duplicate detection applies at every configuration nesting level" do
    raw = Jason.encode!(object())
    # The spellings below differ in the JSON bytes but are identical after decoding.
    for {key, escaped} <- [
          {"generation", "generat\\u0069on"},
          {"binding", "b\\u0069nding"},
          {"profiles", "prof\\u0069les"},
          {"resolvers", "resolv\\u0065rs"},
          {"profile", "prof\\u0069le"},
          {"transport", "transp\\u006frt"},
          {"jwks_endpoint", "jwks_endpo\\u0069nt"},
          {"profile_id", "profile_\\u0069d"},
          {"issuer", "iss\\u0075er"},
          {"identity_class", "identity_cl\\u0061ss"},
          {"host", "h\\u006fst"},
          {"port", "p\\u006frt"},
          {"path", "p\\u0061th"}
        ] do
      # Insert a second, decoded-equivalent key with a null value before the original.
      needle = Jason.encode!(key) <> ":"

      injected =
        String.replace(raw, needle, "\"" <> escaped <> "\":null," <> needle, global: false)

      refute injected == raw
      reject(injected)
    end
  end

  test "IR02 complete closed objects prohibit fixture/module/discovery and TLS policy injection" do
    paths = [
      [],
      ["profiles", Access.at(0)],
      ["profiles", Access.at(0), "profile"],
      ["profiles", Access.at(0), "jwks_endpoint"]
    ]

    for key <- [
          "fixture",
          "module",
          "name",
          "worker_supervisor",
          "ca_roots",
          "verify",
          "snapshot",
          "discovery"
        ],
        path <- paths do
      modified =
        if path == [],
          do: Map.put(object(), key, "independent-private-marker"),
          else: update_in(object(), path, &Map.put(&1, key, "independent-private-marker"))

      reject(Jason.encode!(modified))
    end

    for {path, value} <- [
          {["profiles", Access.at(0), "transport"], "Elixir.MixerHosted.Identity.TLSFixture"},
          {["profiles", Access.at(0), "transport"], "fixture"},
          {["profiles", Access.at(0), "profile", "identity_class"], "Elixir.System"},
          {["profiles", Access.at(0), "jwks_endpoint", "host"], "keys.independent.invalid\n"},
          {["profiles", Access.at(0), "jwks_endpoint", "path"], "/keys#secret"},
          {["profiles", Access.at(0), "jwks_endpoint", "path"], "/%2e%2e/private"}
        ],
        do: reject(Jason.encode!(put_in(object(), path, value)))
  end

  test "IR03 numerics cannot coerce exponent or floating point integer forms" do
    raw = Jason.encode!(object())

    for {from, to} <- [
          {"\"version\":1", "\"version\":1e0"},
          {"\"generation\":1", "\"generation\":1.0"},
          {"\"generation\":1", "\"generation\":2147483648"},
          {"\"generation\":1", "\"generation\":-1"},
          {"\"generation\":1", "\"generation\":true"},
          {"\"profile_version\":1", "\"profile_version\":1e0"},
          {"\"port\":443", "\"port\":443e0"},
          {"\"port\":443", "\"port\":\"443\""}
        ] do
      injected = String.replace(raw, from, to)
      refute injected == raw
      reject(injected)
    end
  end

  test "IR04 resolver round trips reject alternate spelling zones ports and control characters" do
    for value <- [
          "127.000.000.001",
          "2130706433",
          "0x7f000001",
          "127.0.0.1 ",
          " 127.0.0.1",
          "127.0.0.1\n",
          "127.0.0.1\u0000",
          "[::1]",
          "::1%lo0",
          "::1:53 ",
          "2001:DB8::1",
          "2001:db8:0:0:0:0:0:1",
          "::ffff:7f00:1",
          "8.8.8.8/32",
          "８.８.８.８"
        ] do
      reject(Jason.encode!(Map.put(object(), "resolvers", [value])))
    end

    for values <- [["127.0.0.1"], ["0.0.0.0", "::"], ["10.0.0.1", "192.168.0.1", "::1"]] do
      settings = load(Jason.encode!(Map.put(object(), "resolvers", values)))

      assert Enum.map(settings.owner_options[:resolvers], fn {ip, 53} ->
               ip |> :inet.ntoa() |> List.to_string()
             end) == values
    end

    reject(Jason.encode!(Map.put(object(), "resolvers", ["::1", "::1"])))
  end

  test "IR05 limits count UTF8 bytes and bound profile identities without normalization" do
    raw = Jason.encode!(object())
    assert load(raw <> String.duplicate(" ", 65_536 - byte_size(raw))).mode == :configured
    reject(raw <> String.duplicate(" ", 65_537 - byte_size(raw)))
    # Multi-byte strings exceed accepted byte limits despite short character counts.
    for {field, size} <- [{"profile_id", 128}, {"audience", 256}, {"client_id", 256}] do
      value = String.duplicate("é", size)
      assert String.length(value) == size
      reject(Jason.encode!(put_in(object(), ["profiles", Access.at(0), "profile", field], value)))
    end

    entry = hd(object()["profiles"])
    reject(Jason.encode!(Map.put(object(), "profiles", [entry, entry])))
    reject(Jason.encode!(Map.put(object(), "binding", "INDEPENDENT-REVIEW-MARKER")))
  end

  test "IR06 raw trust values are omitted from Inspect and fixed errors" do
    settings = load(Jason.encode!(object()))
    text = inspect(settings, pretty: true, limit: :infinity, printable_limit: :infinity)
    assert text =~ "configured"

    for forbidden <- ["independent", "roots", "resolvers", "owner_options", "review-client"],
        do: refute(text =~ forbidden)

    for bad <- [
          "independent-private-marker",
          Jason.encode!(Map.put(object(), "private-marker", "independent-private-marker")),
          <<255, 254>>,
          "{\"secret\":\"independent-private-marker\"}"
        ] do
      error = assert_raise ArgumentError, fn -> load(bad) end
      assert Exception.message(error) == "invalid identity startup: configuration"
      refute Exception.message(error) =~ "independent"
    end

    reject(Jason.encode!(object()), ["independent-private-ca-marker"], "ca_roots")
  end

  test "IR07 invalid dynamic strings create no atoms after decoder warmup" do
    raw = Jason.encode!(object())
    load(raw)
    reject(Jason.encode!(Map.put(object(), "warmup", "warmup")))

    paths = [
      ["profiles", Access.at(0), "transport"],
      ["profiles", Access.at(0), "profile", "identity_class"]
    ]

    for path <- paths, do: reject(Jason.encode!(put_in(object(), path, "warmup")))
    before = :erlang.system_info(:atom_count)

    for n <- 1..300 do
      value = "untrusted-review-atom-#{n}"
      reject(Jason.encode!(Map.put(object(), value, value)))
      for path <- paths, do: reject(Jason.encode!(put_in(object(), path, value)))
    end

    after_count = :erlang.system_info(:atom_count)
    assert after_count == before
  end

  test "IR08 pure constructor rejects OTP combined certificate shapes while RuntimeConfig normalizes once" do
    [root] = roots()

    reject(
      Jason.encode!(object()),
      [{:cert, root, :public_key.pkix_decode_cert(root, :otp)}],
      "ca_roots"
    )

    for value <- [[], [root, nil], [root, <<48, 0>>], [<<>>]],
        do: reject(Jason.encode!(object()), value, "ca_roots")

    env = %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "db.independent.invalid",
      "MIXER_DATABASE_NAME" => "synthetic",
      "MIXER_DATABASE_USER" => "synthetic",
      "MIXER_DATABASE_PASSWORD" => "independent-private-marker",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("a", 64),
      "MIXER_IDENTITY_MODE" => "configured",
      "MIXER_IDENTITY_CONFIG" => Jason.encode!(object())
    }

    result = MixerHosted.RuntimeConfig.load!(env)
    assert result.repo[:ssl][:cacerts] == :public_key.cacerts_get()
    assert result.repo[:ssl][:verify] == :verify_peer
    assert Enum.all?(result.identity_startup.owner_options[:ca_roots], &is_binary/1)
    refute inspect(result) =~ "independent"
    refute inspect(result) =~ "private-marker"
  end

  test "IR09 disabled compatibility and explicit application entry point require validated settings" do
    for role <- [:api, :processor] do
      result = MixerHosted.Application.children(role, [])
      refute Enum.any?(result, &match?({MixerHosted.Identity.KeyOwnerSupervisor, _}, &1))

      for raw <- ["", "null", "independent-private-marker"] do
        assert_raise ArgumentError, "invalid identity startup: unexpected_configuration", fn ->
          StartupConfig.load!(%{"MIXER_IDENTITY_CONFIG" => raw}, role, [])
        end
      end
    end

    assert_raise ArgumentError, "invalid identity startup: role", fn ->
      StartupConfig.load!(
        %{
          "MIXER_IDENTITY_MODE" => "configured",
          "MIXER_IDENTITY_CONFIG" => "independent-private-marker"
        },
        :processor,
        roots()
      )
    end

    assert_raise FunctionClauseError, fn ->
      MixerHosted.Application.children(:processor, [], load(Jason.encode!(object())))
    end

    before = Application.get_env(:mixer_hosted, :identity_startup)
    Application.delete_env(:mixer_hosted, :identity_startup)

    on_exit(fn ->
      if before,
        do: Application.put_env(:mixer_hosted, :identity_startup, before),
        else: Application.delete_env(:mixer_hosted, :identity_startup)
    end)

    # Argument fetch happens before any Supervisor/Repo/Endpoint can be created.
    Application.put_env(:mixer_hosted, :role, :api)
    Application.put_env(:mixer_hosted, Oban, [])
    assert_raise ArgumentError, fn -> MixerHosted.Application.start(:normal, []) end
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil
    assert Process.whereis(MixerHosted.Identity.KeyOwner) == nil
  end
end
