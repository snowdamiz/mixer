defmodule MixerHosted.CustomerBuilds.CreateInputTest do
  use ExUnit.Case, async: true
  alias MixerHosted.CustomerBuilds.CreateInput

  defp fields do
    %{
      organization_id: "org",
      project_id: "project",
      application_id: "app",
      platform: :ios,
      source_input_id: "input",
      source_sha256: String.duplicate("a", 64),
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }
  end

  test "closed eight fields and strict platform and digest admission" do
    assert {:ok, i} = CreateInput.new(fields())
    assert {:ok, ^i} = CreateInput.new(i)

    for v <- [
          Map.put(fields(), :repo, MixerHosted.Repo),
          Map.delete(fields(), :source_input_id),
          %{fields() | platform: "ios"},
          %{fields() | source_sha256: String.duplicate("A", 64)}
        ] do
      assert CreateInput.new(v) == {:error, :invalid_request}
    end

    raw = Jason.encode!(%{fields() | platform: "ios"})
    assert {:ok, ^i} = CreateInput.parse(raw)

    assert CreateInput.parse("{\"platform\":\"ios\",\"platform\":\"android\"}") ==
             {:error, :invalid_request}

    assert CreateInput.parse(String.duplicate("x", 4097)) == {:error, :invalid_request}
  end

  test "server build identity is stable, platform scoped and length prefixed" do
    {:ok, i} = CreateInput.new(fields())
    b = CreateInput.build_id(i, "key")
    assert b == CreateInput.build_id(i, "key")
    assert String.length(b) == 70
    refute b == CreateInput.build_id(%{i | platform: :android}, "key")

    refute CreateInput.build_id(%{i | organization_id: "a", project_id: "bc"}, "key") ==
             CreateInput.build_id(%{i | organization_id: "ab", project_id: "c"}, "key")

    refute b == CreateInput.build_id(i, "other-key")
  end
end
