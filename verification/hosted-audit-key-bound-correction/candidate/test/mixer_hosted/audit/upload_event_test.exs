defmodule MixerHosted.Audit.UploadEventTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Audit.UploadEvent

  @fixture Path.expand("../../fixtures/audit/retained-chains.json", __DIR__)
  @keys ~w(organization project event_id event_cbor event_hash previous_hash previous_state current_state display_json display_bytes)a
  @error {:error, :invalid_audit_event}

  defp chains do
    @fixture
    |> File.read!()
    |> Jason.decode!()
    |> Map.fetch!("chains")
    |> Enum.map(fn chain ->
      Enum.map(chain["rows"], fn row ->
        Map.new(@keys, fn key ->
          value = Map.fetch!(row, Atom.to_string(key))

          value =
            case value do
              %{"encoding" => "hex", "value" => hex} -> Base.decode16!(hex, case: :lower)
              other -> other
            end

          {key, value}
        end)
      end)
    end)
  end

  defp row, do: chains() |> hd() |> hd()
  defp display, do: row().display_json

  defp replace_at(d, key, index, value),
    do: Map.update!(d, key, &List.replace_at(&1, index, value))

  test "independent coherent-hash vectors distinguish typed rejection from hash mismatch" do
    vectors =
      Path.expand("../../fixtures/audit/coherent-vectors.json", __DIR__)
      |> File.read!()
      |> Jason.decode!()
      |> Map.fetch!("cases")

    assert length(vectors) >= 80

    for v <- vectors do
      bytes = Base.decode16!(v["event_cbor_hex"], case: :lower)
      hash = :crypto.hash(:sha256, "mixer.hosted.audit.v1" <> <<0>> <> bytes)
      assert Base.encode16(hash, case: :lower) == v["display"]["hash"]

      if v["accepted"] do
        assert UploadEvent.decode(v["display"]) ==
                 {:ok,
                  %{
                    event_cbor: bytes,
                    event_hash: hash,
                    display_bytes: Base.decode16!(v["display_bytes_hex"], case: :lower)
                  }},
               v["label"]
      else
        assert UploadEvent.decode(v["display"]) == @error, v["label"]
      end
    end
  end

  test "185 captured real PostgreSQL rows retain exact bytes and all six adjacent chains" do
    all = chains()
    assert length(all) == 6
    assert Enum.sum(Enum.map(all, &length/1)) == 185

    for chain <- all do
      Enum.reduce(chain, nil, fn current, previous ->
        assert UploadEvent.validate_row(current) == :ok
        assert UploadEvent.validate_edge(current, previous) == :ok

        assert UploadEvent.decode(current.display_json) ==
                 {:ok,
                  %{
                    event_cbor: current.event_cbor,
                    event_hash: current.event_hash,
                    display_bytes: current.display_bytes
                  }}

        current
      end)
    end
  end

  test "display shape is closed and rejects source values before rendering" do
    d = display()

    for value <- [nil, true, [], 1, "secret", self(), %{}, Map.put(d, "unknown", 1)] do
      assert UploadEvent.decode(value) == @error
    end

    for key <- Map.keys(d) do
      assert UploadEvent.decode(Map.delete(d, key)) == @error
      assert UploadEvent.decode(Map.put(d, key, %{huge: List.duplicate("x", 10_000)})) == @error
    end

    assert UploadEvent.decode(Map.put(d, "reason", String.duplicate("x", 1_000_000))) == @error
    assert UploadEvent.decode(Map.put(d, "reason", [self() | self()])) == @error
  end

  test "fixed arrays, member lists and entry shapes are bounded and proper" do
    d = display()

    for key <- ["tenant", "actor", "decision", "target"],
        value <- [nil, %{}, ["x" | "improper"], List.duplicate("x", 100_000)] do
      assert UploadEvent.decode(Map.put(d, key, value)) == @error
    end

    member = d["decision"] |> Enum.at(6) |> hd()

    for value <- [
          [],
          [member | :bad],
          List.duplicate(member, 65),
          List.duplicate(member, 100_000),
          [["wrong"]],
          [%{}],
          [List.duplicate("x", 100_000)]
        ] do
      assert UploadEvent.decode(replace_at(d, "decision", 6, value)) == @error
    end
  end

  test "unsigned display fields retain decimal spelling and domain bounds" do
    d = display()

    fields =
      [{"id", nil}, {"recorded_at", nil}, {"actor", 4}, {"actor", 10}] ++
        Enum.map(0..5, &{"decision", &1})

    for {key, index} <- fields,
        value <- [
          nil,
          true,
          1,
          1.0,
          "",
          "-1",
          "+1",
          "01",
          "1.0",
          "1e0",
          "1\n",
          " 1",
          "NaN",
          "Infinity",
          "18446744073709551616"
        ] do
      changed =
        if is_nil(index), do: Map.put(d, key, value), else: replace_at(d, key, index, value)

      assert UploadEvent.decode(changed) == @error
    end

    for {key, index, value} <- [
          {"id", nil, "0"},
          {"recorded_at", nil, "9007199254740992"},
          {"actor", 4, "0"},
          {"actor", 4, "2147483648"},
          {"actor", 10, "9007199254740992"},
          {"decision", 1, "0"},
          {"decision", 2, "9223372036854775808"}
        ] do
      changed =
        if is_nil(index), do: Map.put(d, key, value), else: replace_at(d, key, index, value)

      assert UploadEvent.decode(changed) == @error
    end
  end

  test "UUID, hex, identity class, platform and role are closed" do
    d = display()

    for index <- [0, 2, 9],
        value <- [
          nil,
          "",
          "00000000000000000000000000000000AA",
          "00000000-0000-0000-0000-00000000000A",
          d["actor"] |> Enum.at(index) |> Kernel.<>("\n")
        ] do
      assert UploadEvent.decode(replace_at(d, "actor", index, value)) == @error
    end

    for index <- 5..8,
        value <- [
          nil,
          String.duplicate("A", 64),
          String.duplicate("0", 63),
          String.duplicate("g", 64)
        ] do
      assert UploadEvent.decode(replace_at(d, "actor", index, value)) == @error
    end

    for value <- ["service", "Human", nil],
        do: assert(UploadEvent.decode(replace_at(d, "actor", 1, value)) == @error)

    for value <- ["IOS", "web", nil],
        do: assert(UploadEvent.decode(replace_at(d, "target", 4, value)) == @error)

    member = d["decision"] |> Enum.at(6) |> hd()

    for role <- ["publisher", "Developer", "developer\n", "viewer", "billing_manager", nil] do
      changed = replace_at(d, "decision", 6, [List.replace_at(member, 1, role)])
      assert UploadEvent.decode(changed) == @error
    end

    assert UploadEvent.decode(replace_at(d, "decision", 6, [member, member])) == @error
  end

  test "UTF8 and source text limits reject malformed, NUL and oversized bytes" do
    d = display()

    for value <- [
          <<0>>,
          <<0xC0, 0xAF>>,
          <<0xED, 0xA0, 0x80>>,
          <<0xFF>>,
          String.duplicate("x", 513)
        ] do
      assert UploadEvent.decode(Map.put(d, "reason", value)) == @error
    end

    for value <- ["", <<0>>, <<0xFF>>, String.duplicate("x", 129)] do
      assert UploadEvent.decode(replace_at(d, "actor", 3, value)) == @error
    end

    for key <- ["tenant", "target"],
        index <- 0..1,
        value <- ["", "x/y", "x\n", "é", String.duplicate("x", 129)] do
      assert UploadEvent.decode(replace_at(d, key, index, value)) == @error
    end
  end

  test "audit schema action time relationships and IP spelling fail closed" do
    d = display()

    for value <- ["1", true, 1.0, 0, 2],
        do: assert(UploadEvent.decode(Map.put(d, "audit_schema", value)) == @error)

    for value <- [nil, "artifact.read", "artifact.upload\n"],
        do: assert(UploadEvent.decode(Map.put(d, "action", value)) == @error)

    for value <- ["127.000.0.1", "127.0.0.1/32", "2001:0DB8::1", "1.2.3", "name.invalid", <<0>>] do
      assert UploadEvent.decode(Map.put(d, "source_ip", value)) == @error
    end

    decision = String.to_integer(hd(d["decision"]))

    assert UploadEvent.decode(replace_at(d, "actor", 10, Integer.to_string(decision + 31))) ==
             @error

    assert UploadEvent.decode(replace_at(d, "actor", 10, Integer.to_string(decision - 46))) ==
             @error

    assert UploadEvent.decode(Map.put(d, "recorded_at", Integer.to_string(decision - 1))) ==
             @error
  end

  test "row hash, projection, encoding and exact display bytes cannot be substituted" do
    r = row()

    for key <- @keys do
      assert UploadEvent.validate_row(Map.delete(r, key)) == @error
      assert UploadEvent.validate_row(Map.put(r, key, nil)) == @error
    end

    assert UploadEvent.validate_row(Map.put(r, :extra, "x")) == @error

    for key <- [
          :event_cbor,
          :event_hash,
          :previous_hash,
          :previous_state,
          :current_state,
          :display_bytes
        ] do
      assert UploadEvent.validate_row(Map.update!(r, key, &(&1 <> <<0>>))) == @error
    end

    assert UploadEvent.validate_row(%{r | display_bytes: Jason.encode!(r.display_json)}) == @error
    assert UploadEvent.validate_row(%{r | event_id: 1.0}) == @error
    assert UploadEvent.validate_row(%{r | event_cbor: :binary.copy(<<0>>, 16_385)}) == @error
    assert UploadEvent.validate_row(%{r | display_bytes: :binary.copy(<<0>>, 32_769)}) == @error

    for key <- [:event_hash, :previous_hash, :previous_state, :current_state] do
      assert UploadEvent.validate_row(Map.put(r, key, :binary.copy(<<0>>, 1_000_000))) == @error
    end

    assert UploadEvent.decode(Map.put(r.display_json, "hash", String.duplicate("0", 64))) ==
             @error
  end

  test "only the immediate valid same-tenant predecessor is accepted" do
    [first, second, third | _] = hd(chains())
    assert UploadEvent.validate_edge(first, nil) == :ok
    assert UploadEvent.validate_edge(first, first) == @error
    assert UploadEvent.validate_edge(second, nil) == @error
    assert UploadEvent.validate_edge(third, first) == @error
    assert UploadEvent.validate_edge(second, second) == @error

    v =
      Path.expand("../../fixtures/audit/coherent-vectors.json", __DIR__)
      |> File.read!()
      |> Jason.decode!()
      |> Map.fetch!("cases")
      |> Enum.find(&(&1["label"] == "valid foreign tenant first row"))

    d = v["display"]

    foreign = %{
      first
      | organization: hd(d["tenant"]),
        project: Enum.at(d["tenant"], 1),
        display_json: d,
        event_cbor: Base.decode16!(v["event_cbor_hex"], case: :lower),
        event_hash: Base.decode16!(d["hash"], case: :lower),
        previous_state: Base.decode16!(d["previous_state"], case: :lower),
        display_bytes: Base.decode16!(v["display_bytes_hex"], case: :lower)
    }

    assert UploadEvent.validate_row(foreign) == :ok
    assert UploadEvent.validate_edge(second, foreign) == @error
    assert UploadEvent.validate_edge(second, %{first | event_hash: <<0::256>>}) == @error
    assert UploadEvent.validate_edge(nil, first) == @error
  end

  test "equivalent display spellings remain invalid retained bytes" do
    r = row()

    for changed <- [
          " " <> r.display_bytes,
          r.display_bytes <> "\n",
          String.replace(r.display_bytes, ": ", ":"),
          String.replace(r.display_bytes, ", ", ",")
        ] do
      assert Jason.decode!(changed) == r.display_json
      assert UploadEvent.validate_row(%{r | display_bytes: changed}) == @error
    end
  end

  test "exact-cardinality unknown keys reject without scanning their contents" do
    prefix = :binary.copy("x", 1_048_576)
    unknown_display = Map.new(0..15, &{prefix <> <<&1>>, nil})
    unknown_row = Map.new(0..9, &{prefix <> <<&1>>, nil})
    assert UploadEvent.decode(unknown_display) == @error
    assert UploadEvent.validate_row(unknown_row) == @error

    for foreign <- [prefix, :unknown, 1, 1.0, [], {}, %{}] do
      for key <- Map.keys(display()) do
        malformed = display() |> Map.delete(key) |> Map.put(foreign, nil)
        assert map_size(malformed) == 16
        assert UploadEvent.decode(malformed) == @error
      end

      for key <- @keys do
        malformed = row() |> Map.delete(key) |> Map.put(foreign, nil)
        assert map_size(malformed) == 10
        assert UploadEvent.validate_row(malformed) == @error
      end
    end
  end
end
