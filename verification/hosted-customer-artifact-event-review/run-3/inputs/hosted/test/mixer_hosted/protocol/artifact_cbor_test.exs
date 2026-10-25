defmodule MixerHosted.Protocol.ArtifactCBORTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Protocol.ArtifactCBOR

  @vector Path.expand("../../../../services/protocol/testdata/signed-release-v3.json", __DIR__)

  test "unsigned integer transitions use the shortest supported representation" do
    for {value, hex} <- [
          {0, "00"},
          {23, "17"},
          {24, "1818"},
          {255, "18ff"},
          {256, "190100"},
          {65_535, "19ffff"},
          {65_536, "1a00010000"},
          {4_294_967_295, "1affffffff"},
          {4_294_967_296, "1b0000000100000000"},
          {18_446_744_073_709_551_615, "1bffffffffffffffff"}
        ] do
      assert_hex(value, hex)
    end
  end

  test "text counts UTF-8 bytes and never normalizes Unicode" do
    for {value, hex} <- [
          {"", "60"},
          {"a", "6161"},
          {"IETF", "6449455446"},
          {"\u00fc", "62c3bc"},
          {"水", "63e6b0b4"},
          {"\u{1f600}", "64f09f9880"},
          {"\u00e9", "62c3a9"},
          {"e\u0301", "6365cc81"},
          {"\u0000", "6100"}
        ] do
      assert_hex(value, hex)
    end

    for {count, prefix} <- [
          {23, <<0x77>>},
          {24, <<0x78, 24>>},
          {255, <<0x78, 255>>},
          {256, <<0x79, 1, 0>>}
        ] do
      value = String.duplicate("a", count)
      assert ArtifactCBOR.encode(value) == {:ok, prefix <> value}
    end
  end

  test "booleans, definite arrays and text maps preserve the artifact subset" do
    assert_hex(false, "f4")
    assert_hex(true, "f5")
    assert_hex([], "80")
    assert_hex(%{}, "a0")
    assert_hex([1, [2, 3], [4, 5]], "8301820203820405")
    assert_hex(%{"a" => 1, "b" => [2, 3]}, "a26161016162820203")
    assert_hex(~c"abc", "83186118621863")
  end

  test "map ordering compares complete encoded text keys rather than source text" do
    # Source-text lexical order would put aa before b. UTF-8 and empty keys
    # exercise encoded lengths; canonically equivalent strings remain distinct.
    assert_hex(%{"aa" => 2, "b" => 1}, "a261620162616102")

    assert_hex(
      %{"z" => 1, "é" => 2, "e\u0301" => 3, "" => 0},
      "a46000617a0162c3a9026365cc8103"
    )

    pairs = [{"aa", 2}, {"b", 1}, {"", 0}, {"nested", %{"xx" => false, "c" => true}}]

    assert ArtifactCBOR.encode(Map.new(pairs)) ==
             ArtifactCBOR.encode(Map.new(Enum.reverse(pairs)))
  end

  test "the existing signed v3 artifact, assignment and grant vector is byte exact" do
    vector = @vector |> File.read!() |> Jason.decode!()
    assert vector["test_only"] == true

    for {name, body, domain, root_index} <- [
          {"manifest", "manifest", "mixer.artifact.v3\0", 0},
          {"assignment", "assignment", "mixer.assignment.v3\0", 1}
        ] do
      signed = vector["signed_" <> name]
      assert {:ok, encoded} = ArtifactCBOR.encode(signed[body])
      assert Base.encode16(encoded, case: :lower) == vector[name <> "_cbor_hex"]
      preimage = domain <> encoded
      assert Base.encode16(preimage, case: :lower) == vector[name <> "_message_hex"]

      public_key =
        vector["roots"] |> Enum.at(root_index) |> Map.fetch!("public_key") |> Base.decode64!()

      signature = Base.decode64!(signed["signature"])
      assert :crypto.verify(:eddsa, :none, preimage, signature, [public_key, :ed25519])
      refute :crypto.verify(:eddsa, :none, preimage <> <<0>>, signature, [public_key, :ed25519])

      if name == "manifest" do
        digest = :crypto.hash(:sha256, encoded) |> Base.encode16(case: :lower)
        assert digest == vector["artifact_sha256"]
      end
    end

    assert {:ok, grants} = ArtifactCBOR.encode(vector["grant_descriptor"])
    assert Base.encode16(grants, case: :lower) == vector["grant_descriptor_cbor_hex"]
    descriptor_hash = :crypto.hash(:sha256, grants) |> Base.encode16(case: :lower)

    assert descriptor_hash ==
             vector["signed_manifest"]["manifest"]["capability_grants"]["schema_sha256"]
  end

  test "unsupported types and nontext keys fail without implicit conversion" do
    for value <- [
          nil,
          -1,
          18_446_744_073_709_551_616,
          1.0,
          :unknown,
          {:bytes, <<1>>},
          <<1::1>>,
          self(),
          make_ref(),
          fn -> :ok end,
          %URI{},
          %{:a => 1},
          %{1 => "a"},
          %{false => 1},
          %{"nested" => %{a: 1}},
          [1 | 2]
        ] do
      assert ArtifactCBOR.encode(value) == {:error, :invalid_value}
    end
  end

  test "malformed UTF-8 fails in values and keys" do
    for invalid <- [
          <<0xFF>>,
          <<0xC0, 0xAF>>,
          <<0xE2, 0x82>>,
          <<0xED, 0xA0, 0x80>>,
          <<0xF4, 0x90, 0x80, 0x80>>
        ] do
      assert ArtifactCBOR.encode(invalid) == {:error, :invalid_value}
      assert ArtifactCBOR.encode(%{invalid => 1}) == {:error, :invalid_value}
      assert ArtifactCBOR.encode([invalid]) == {:error, :invalid_value}
    end
  end

  test "byte budget includes every prefix and all nested key and value bytes" do
    assert ArtifactCBOR.encode("", 1) == {:ok, <<0x60>>}
    assert ArtifactCBOR.encode("a", 1) == {:error, :limit_exceeded}
    assert ArtifactCBOR.encode([0], 2) == {:ok, <<0x81, 0>>}
    assert ArtifactCBOR.encode([0], 1) == {:error, :limit_exceeded}
    assert ArtifactCBOR.encode(%{"a" => 0}, 4) == {:ok, <<0xA1, 0x61, ?a, 0>>}
    assert ArtifactCBOR.encode(%{"a" => 0}, 3) == {:error, :limit_exceeded}

    nested = %{"key" => [false, %{"value" => 24}]}
    {:ok, encoded} = ArtifactCBOR.encode(nested)
    assert ArtifactCBOR.encode(nested, byte_size(encoded)) == {:ok, encoded}
    assert ArtifactCBOR.encode(nested, byte_size(encoded) - 1) == {:error, :limit_exceeded}

    assert {:ok, maximum} = ArtifactCBOR.encode(String.duplicate("a", 65_533))
    assert byte_size(maximum) == 65_536
    assert ArtifactCBOR.encode(String.duplicate("a", 65_534)) == {:error, :limit_exceeded}
    assert ArtifactCBOR.encode(%{String.duplicate("a", 65_533) => 0}) == {:error, :limit_exceeded}

    for limit <- [0, -1, 65_537, 1.0, nil, :unlimited] do
      assert ArtifactCBOR.encode(0, limit) == {:error, :invalid_value}
    end
  end

  test "per-container bounds apply before traversal and never truncate inputs" do
    assert {:ok, _} = ArtifactCBOR.encode(List.duplicate(0, 256))
    assert ArtifactCBOR.encode(List.duplicate(0, 257)) == {:error, :limit_exceeded}
    assert ArtifactCBOR.encode(List.duplicate(0, 100_000)) == {:error, :limit_exceeded}
    map = Map.new(1..256, &{Integer.to_string(&1), 0})
    assert {:ok, _} = ArtifactCBOR.encode(map)
    assert ArtifactCBOR.encode(Map.put(map, "overflow", 0)) == {:error, :limit_exceeded}
  end

  test "global item budget includes containers and map keys" do
    rows = List.duplicate(List.duplicate(false, 256), 15)
    exact = rows ++ [List.duplicate(false, 239)]
    assert {:ok, _} = ArtifactCBOR.encode(exact)
    assert ArtifactCBOR.encode(rows ++ [List.duplicate(false, 240)]) == {:error, :limit_exceeded}

    map = Map.new(1..119, &{Integer.to_string(&1), false})
    assert {:ok, _} = ArtifactCBOR.encode(rows ++ [map, false])
    assert ArtifactCBOR.encode(rows ++ [map, false, false]) == {:error, :limit_exceeded}
  end

  test "depth budget bounds both arrays and maps" do
    arrays = Enum.reduce(1..16, 0, fn _, value -> [value] end)
    maps = Enum.reduce(1..16, 0, fn _, value -> %{"key" => value} end)
    assert {:ok, _} = ArtifactCBOR.encode(arrays)
    assert {:ok, _} = ArtifactCBOR.encode(maps)
    assert ArtifactCBOR.encode([arrays]) == {:error, :limit_exceeded}
    assert ArtifactCBOR.encode(%{"key" => maps}) == {:error, :limit_exceeded}
  end

  defp assert_hex(value, hex) do
    assert {:ok, encoded} = ArtifactCBOR.encode(value)
    assert Base.encode16(encoded, case: :lower) == hex
  end
end
