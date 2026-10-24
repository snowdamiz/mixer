defmodule MixerHosted.Identity.StartupConfigTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Identity.{StartupConfig, StartupFixture}

  setup_all do
    {:ok, roots: StartupFixture.standard_roots()}
  end

  defp reject(raw, roots, category \\ "configuration") do
    assert_raise ArgumentError, "invalid identity startup: " <> category, fn ->
      StartupConfig.load!(
        %{"MIXER_IDENTITY_MODE" => "configured", "MIXER_IDENTITY_CONFIG" => raw},
        :api,
        roots
      )
    end
  end

  test "IS01 explicit disabled default, role separation and stray configuration", %{roots: roots} do
    for role <- [:api, :processor], env <- [%{}, %{"MIXER_IDENTITY_MODE" => "disabled"}] do
      assert %StartupConfig{mode: :disabled, owner_options: []} =
               StartupConfig.load!(env, role, [])
    end

    for role <- [:api, :processor], mode <- [nil, "disabled"] do
      env = %{"MIXER_IDENTITY_CONFIG" => "sensitive-payload"}
      env = if mode, do: Map.put(env, "MIXER_IDENTITY_MODE", mode), else: env

      assert_raise ArgumentError, "invalid identity startup: unexpected_configuration", fn ->
        StartupConfig.load!(env, role, roots)
      end
    end

    for mode <- [nil, "", "Configured", :configured, 1] do
      assert_raise ArgumentError, "invalid identity startup: mode", fn ->
        StartupConfig.load!(%{"MIXER_IDENTITY_MODE" => mode}, :api, roots)
      end
    end

    assert_raise ArgumentError, "invalid identity startup: role", fn ->
      StartupConfig.load!(%{"MIXER_IDENTITY_MODE" => "configured"}, :processor, roots)
    end

    settings = MixerHosted.RuntimeConfig.load!(StartupFixture.foundation_env())
    assert settings.identity_startup.mode == :disabled

    for role <- [:api, :processor] do
      refute Enum.any?(MixerHosted.Application.children(role, settings.oban), fn
               {MixerHosted.Identity.KeyOwnerSupervisor, _} -> true
               _ -> false
             end)
    end
  end

  test "IS02 exact conversion both identity classes, boundaries and redacted Inspect", %{
    roots: roots
  } do
    for count <- [1, 8],
        class <- ["human", "service"],
        enabled <- [true, false],
        resolvers <- [["127.0.0.1"], ["8.8.8.8", "2001:4860:4860::8888", "::1"]] do
      entries =
        for n <- 1..count do
          StartupFixture.entry()
          |> put_in(["profile", "profile_id"], "sensitive-profile-#{n}")
          |> put_in(["profile", "identity_class"], class)
          |> put_in(["profile", "enabled"], enabled)
        end

      object =
        StartupFixture.envelope()
        |> Map.merge(%{
          "generation" => 2_147_483_647,
          "binding" => "sensitive-profile-1",
          "profiles" => entries,
          "resolvers" => resolvers
        })

      settings = StartupFixture.configuration(object, roots)
      assert settings.mode == :configured
      assert settings.owner_options[:generation] == 2_147_483_647
      assert length(settings.owner_options[:manifest]) == count

      assert hd(settings.owner_options[:manifest]).profile.identity_class ==
               if(class == "human", do: :human, else: :service)

      assert hd(settings.owner_options[:manifest]).profile.enabled == enabled
      assert Enum.all?(settings.owner_options[:resolvers], &(elem(&1, 1) == 53))
      refute inspect(settings) =~ "sensitive"
      refute inspect(settings) =~ "ca_roots"
    end

    raw = Jason.encode!(StartupFixture.envelope())

    assert StartupConfig.load!(
             %{
               "MIXER_IDENTITY_MODE" => "configured",
               "MIXER_IDENTITY_CONFIG" => raw <> String.duplicate(" ", 65_536 - byte_size(raw))
             },
             :api,
             roots
           ).mode == :configured

    reject(raw <> String.duplicate(" ", 65_537 - byte_size(raw)), roots)
  end

  test "IS02 RuntimeConfig binds configured settings from its single OTP CA source" do
    env =
      Map.merge(StartupFixture.foundation_env(), %{
        "MIXER_IDENTITY_MODE" => "configured",
        "MIXER_IDENTITY_CONFIG" => Jason.encode!(StartupFixture.envelope())
      })

    settings = MixerHosted.RuntimeConfig.load!(env)
    assert settings.identity_startup.mode == :configured
    assert settings.repo[:ssl][:cacerts] == :public_key.cacerts_get()
    assert settings.identity_startup.owner_options[:ca_roots] == StartupFixture.standard_roots()
    assert Enum.all?(settings.identity_startup.owner_options[:ca_roots], &is_binary/1)
    refute inspect(settings) =~ "startup-fixture"
    refute inspect(settings) =~ "synthetic"
  end

  test "IS02 malformed, duplicate and escaped duplicate members fail closed", %{roots: roots} do
    raw = Jason.encode!(StartupFixture.envelope())

    for value <- [
          nil,
          1,
          "",
          "[]",
          "null",
          "{",
          <<255>>,
          String.duplicate("[", 18) <>
            "0" <>
            String.duplicate("]", 18),
          String.replace(raw, "\"version\":1", "\"version\":1,\"version\":1"),
          String.replace(raw, "\"version\":1", "\"version\":1,\"vers\\u0069on\":1"),
          String.replace(raw, "\"enabled\":true", "\"enabled\":true,\"enabl\\u0065d\":true")
        ] do
      reject(value, roots)
    end
  end

  test "IS02 every envelope/profile/endpoint member is complete and closed", %{roots: roots} do
    object = StartupFixture.envelope()
    entry = StartupFixture.entry()
    reject(Jason.encode!(Map.put(object, "sensitive-extra", "sensitive-value")), roots)

    for key <- Map.keys(object), do: reject(Jason.encode!(Map.delete(object, key)), roots)

    for path <- [
          ["profiles", Access.at(0)],
          ["profiles", Access.at(0), "profile"],
          ["profiles", Access.at(0), "jwks_endpoint"]
        ] do
      value = get_in(object, path)
      reject(Jason.encode!(put_in(object, path, Map.put(value, "sensitive-extra", true))), roots)

      for key <- Map.keys(value),
          do: reject(Jason.encode!(put_in(object, path, Map.delete(value, key))), roots)
    end

    bad = [
      Map.put(object, "version", 1.0),
      Map.put(object, "version", 2),
      Map.put(object, "generation", 1.0),
      Map.put(object, "generation", 0),
      Map.put(object, "generation", 2_147_483_648),
      Map.put(object, "binding", "absent"),
      Map.put(object, "binding", 1),
      Map.put(object, "profiles", []),
      Map.put(object, "profiles", [entry, entry]),
      Map.put(object, "profiles", List.duplicate(entry, 9)),
      Map.put(object, "profiles", [%{}]),
      Map.put(object, "profiles", "bad"),
      put_in(object, ["profiles", Access.at(0), "transport"], "fixture"),
      put_in(object, ["profiles", Access.at(0), "profile", "identity_class"], "arbitrary-atom"),
      put_in(object, ["profiles", Access.at(0), "profile", "enabled"], "true"),
      put_in(object, ["profiles", Access.at(0), "profile", "profile_version"], 1.0),
      put_in(
        object,
        ["profiles", Access.at(0), "profile", "audience"],
        String.duplicate("a", 257)
      ),
      put_in(object, ["profiles", Access.at(0), "jwks_endpoint", "host"], "127.0.0.1"),
      put_in(object, ["profiles", Access.at(0), "jwks_endpoint", "port"], 443.0),
      put_in(object, ["profiles", Access.at(0), "jwks_endpoint", "port"], 8443),
      put_in(object, ["profiles", Access.at(0), "jwks_endpoint", "path"], "/keys?secret"),
      put_in(object, ["profiles", Access.at(0), "jwks_endpoint", "path"], "/a/../keys")
    ]

    for value <- bad, do: reject(Jason.encode!(value), roots)

    for resolvers <- [
          [],
          ["8.8.8.8", "8.8.8.8"],
          ["1.1.1.1", "8.8.8.8", "::1", "::2"],
          ["8.8.8.8:53"],
          ["dns.example"],
          ["127.1"],
          ["01.2.3.4"],
          ["2001:0db8::1"],
          ["::FFFF:8.8.8.8"],
          [1],
          "8.8.8.8"
        ] do
      reject(Jason.encode!(Map.put(object, "resolvers", resolvers)), roots)
    end
  end

  test "IS02 nonexistent, empty or invalid CA inputs are bounded categories", %{roots: roots} do
    raw = Jason.encode!(StartupFixture.envelope())

    for value <- [nil, [], "sensitive-cert", ["sensitive-cert"], [nil], roots ++ ["bad"]] do
      reject(raw, value, "ca_roots")
    end
  end
end
