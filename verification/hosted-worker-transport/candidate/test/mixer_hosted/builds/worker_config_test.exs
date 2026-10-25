defmodule MixerHosted.Builds.WorkerConfigTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Builds.WorkerConfig
  alias MixerHosted.Test.{WorkerData, WorkerTLSFixture}

  setup_all do
    material = WorkerTLSFixture.material()
    assert material.key_dir_removed
    {:ok, material: material}
  end

  test "disabled default rejects stray configuration or credentials" do
    assert %WorkerConfig{mode: :disabled} = WorkerConfig.load!(%{}, :processor, [])

    for key <- ["MIXER_BUILD_WORKER_CONFIG", "MIXER_BUILD_WORKER_TOKEN"] do
      assert_raise ArgumentError, "invalid worker configuration", fn ->
        WorkerConfig.load!(%{key => "stray"}, :processor, [])
      end
    end
  end

  test "configured credential is canonical, separate, and inspection redacted", %{material: m} do
    c = WorkerData.config(m.ca)
    assert c.mode == :configured
    refute inspect(c) =~ c.token
    refute inspect(c) =~ "ca_roots"

    assert_raise ArgumentError, "invalid worker configuration", fn ->
      WorkerConfig.load!(WorkerData.environment(), :api, [m.ca])
    end

    for token <- [
          nil,
          "",
          String.duplicate("a", 42),
          String.duplicate("a", 44),
          String.duplicate("!", 43)
        ] do
      assert_raise ArgumentError, "invalid worker configuration", fn ->
        WorkerConfig.load!(
          Map.put(WorkerData.environment(), "MIXER_BUILD_WORKER_TOKEN", token),
          :processor,
          [m.ca]
        )
      end
    end
  end

  test "endpoint, roots, resolver and closed config fail before network", %{material: m} do
    env = WorkerData.environment()
    v = Jason.decode!(env["MIXER_BUILD_WORKER_CONFIG"])

    for changed <- [
          Map.put(v, "extra", true),
          put_in(v, ["endpoint", "port"], 80),
          put_in(v, ["endpoint", "host"], "127.0.0.1"),
          put_in(v, ["endpoint", "path"], "/elsewhere"),
          Map.put(v, "resolvers", ["127.0.0.1"]),
          Map.put(v, "platforms", ["ios", "ios"])
        ] do
      assert_raise ArgumentError, "invalid worker configuration", fn ->
        WorkerConfig.load!(
          Map.put(env, "MIXER_BUILD_WORKER_CONFIG", Jason.encode!(changed)),
          :processor,
          [m.ca]
        )
      end
    end

    for roots <- [[], ["invalid"], List.duplicate(m.ca, 257)] do
      assert_raise ArgumentError, "invalid worker configuration", fn ->
        WorkerConfig.load!(env, :processor, roots)
      end
    end
  end
end
