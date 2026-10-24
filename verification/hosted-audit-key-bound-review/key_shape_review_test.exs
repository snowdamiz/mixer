Code.require_file(Path.join(__DIR__, "original_upload_event.exs"))

defmodule MixerHosted.Audit.KeyBoundCorrectionReviewTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Audit.UploadEvent
  alias MixerHosted.Audit.OriginalUploadEventByReview, as: Original

  @error {:error, :invalid_audit_event}
  @row_keys ~w(organization project event_id event_cbor event_hash previous_hash previous_state current_state display_json display_bytes)a
  @display_keys ~w(audit_schema id tenant actor decision target action reason request_id source_ip recorded_at previous_state current_state previous_hash request_hash hash)
  @binary ~w(event_cbor event_hash previous_hash previous_state current_state display_bytes)

  defp independent do
    Path.join(__DIR__, "../independent_review/independent-vectors.json")
    |> File.read!()
    |> Jason.decode!()
  end

  defp row(raw) do
    Map.new(@row_keys, fn key ->
      name = Atom.to_string(key)
      value = Map.fetch!(raw, name)

      value =
        cond do
          is_map(value) and value["encoding"] == "hex" ->
            Base.decode16!(value["value"], case: :lower)

          name in @binary and is_binary(value) ->
            Base.decode16!(value, case: :lower)

          true ->
            value
        end

      {key, value}
    end)
  end

  defp golden, do: independent()["cases"] |> hd() |> Map.fetch!("row") |> row()

  defp predicates(map, keys) do
    old = map_size(map) == length(keys) and Enum.sort(Map.keys(map)) == Enum.sort(keys)
    new = map_size(map) == length(keys) and Enum.all?(keys, &Map.has_key?(map, &1))
    exact = MapSet.new(Map.keys(map)) == MapSet.new(keys)
    assert old == exact
    assert new == exact
    exact
  end

  test "fixed key membership is equivalent over finite heterogeneous closed shapes" do
    assert length(@row_keys) == 10 and length(Enum.uniq(@row_keys)) == 10
    assert length(@display_keys) == 16 and length(Enum.uniq(@display_keys)) == 16
    r = golden()
    d = r.display_json

    foreign = [
      nil,
      true,
      false,
      :foreign,
      0,
      1,
      1.0,
      -1,
      -1.0,
      <<1::1>>,
      <<255>>,
      "audit_schema" <> <<0>>,
      :audit_schema,
      self(),
      make_ref(),
      fn -> :ok end,
      [],
      [1 | :tail],
      {List.duplicate(:nested, 2_000)},
      %{deep: List.duplicate("key", 2_000)},
      :binary.copy("recorded_at", 100_000)
    ]

    for {good, keys, validate} <- [
          {d, @display_keys, &UploadEvent.decode/1},
          {r, @row_keys, &UploadEvent.validate_row/1}
        ] do
      assert predicates(good, keys)
      assert predicates(Map.new(Enum.reverse(Map.to_list(good))), keys)

      for key <- keys do
        assert not predicates(Map.delete(good, key), keys)
        assert validate.(Map.delete(good, key)) == @error

        for other <- foreign do
          assert not Map.has_key?(good, other)
          changed = good |> Map.delete(key) |> Map.put(other, :unexamined_value)
          assert map_size(changed) == length(keys)
          assert not predicates(changed, keys)
          assert validate.(changed) == @error
          assert not predicates(Map.put(good, other, :extra), keys)
          assert validate.(Map.put(good, other, :extra)) == @error
        end
      end
    end

    for size <- [0, 1, 9, 10, 11, 15, 16, 17, 32, 33, 10_000] do
      map = Map.new(1..max(size, 1), &{&1, nil}) |> Map.take(Enum.to_list(1..size//1))
      assert map_size(map) == size
      assert not predicates(map, @display_keys)
      assert not predicates(map, @row_keys)
      assert UploadEvent.decode(map) == @error
      assert UploadEvent.validate_row(map) == @error
    end

    # Erlang maps distinguish integer and float keys; neither can stand in for a
    # required string/atom, even when two numeric keys have equal numeric value.
    numeric = d |> Map.delete("id") |> Map.delete("reason") |> Map.put(1, nil) |> Map.put(1.0, nil)
    assert map_size(numeric) == 16
    assert not predicates(numeric, @display_keys)
    assert UploadEvent.decode(numeric) == @error

    IO.puts(Jason.encode!(%{
      review: "closed-key finite inventory",
      foreign_key_forms: length(foreign),
      exact_cardinality_single_replacements: (10 + 16) * length(foreign),
      missing_key_maps: 10 + 16,
      extra_key_maps: (10 + 16) * length(foreign),
      foreign_cardinalities: [0, 1, 9, 10, 11, 15, 16, 17, 32, 33, 10_000],
      numeric_integer_float_control: true
    }))
  end

  test "corrected and original outputs agree on every retained case and chain" do
    fixtures = Path.expand("../fixtures/audit", __DIR__)
    captured = File.read!(Path.join(fixtures, "retained-chains.json")) |> Jason.decode!()
    producer = File.read!(Path.join(fixtures, "coherent-vectors.json")) |> Jason.decode!()
    review = independent()

    for specimen <- producer["cases"] do
      assert UploadEvent.decode(specimen["display"]) == Original.decode(specimen["display"])
    end

    for specimen <- review["cases"] do
      r = row(specimen["row"])
      assert UploadEvent.decode(r.display_json) == Original.decode(r.display_json)
      assert UploadEvent.validate_row(r) == Original.validate_row(r)
    end

    for chain <- captured["chains"] do
      Enum.reduce(chain["rows"], nil, fn raw, previous ->
        current = row(raw)
        assert UploadEvent.decode(current.display_json) == Original.decode(current.display_json)
        assert UploadEvent.validate_row(current) == Original.validate_row(current)
        assert UploadEvent.validate_edge(current, previous) == Original.validate_edge(current, previous)
        current
      end)
    end

    for specimen <- review["edges"] do
      current = row(specimen["current"])
      previous = if specimen["previous"], do: row(specimen["previous"]), else: nil
      assert UploadEvent.validate_edge(current, previous) == Original.validate_edge(current, previous)
    end

    IO.puts(Jason.encode!(%{
      review: "original/corrected exact-output parity",
      producer_vectors: length(producer["cases"]),
      independent_coherent_cases: length(review["cases"]),
      captured_rows: Enum.sum(Enum.map(captured["chains"], &length(&1["rows"]))),
      captured_chains: length(captured["chains"]),
      independent_edges: length(review["edges"])
    }))
  end
end
