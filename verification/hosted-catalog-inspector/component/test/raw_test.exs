defmodule MixerCatalogInspector.RawTest do
  use ExUnit.Case, async: false
  alias MixerHosted.CatalogInspector.Raw
  alias MixerCatalogInspector.Evidence

  defp input(name), do: Path.join(System.fetch_env!("MIXER_INSPECTOR_INPUTS"), name)
  defp baseline, do: input("baseline.json.gz") |> File.read!() |> :zlib.gunzip() |> Raw.decode!()
  defp expected, do: File.read!("priv/selected-expected.json") |> Jason.decode!()

  defp valid(fun) do
    fun.()
    true
  catch
    :malformed_catalog -> false
  end

  defp edit(_value, [], %{"op" => "set", "value" => replacement}), do: replacement
  defp edit(value, [key], %{"op" => "delete"}), do: Map.delete(value, key)

  defp edit(value, [key | tail], op) when is_map(value),
    do: Map.update(value, key, nil, &edit(&1, tail, op))

  defp edit(value, [index | tail], op) when is_list(value),
    do: List.update_at(value, index, &edit(&1, tail, op))

  defp apply_patch(base, operations), do: Enum.reduce(operations, base, &edit(&2, &1["path"], &1))

  test "all accepted raw-model matrices execute through independently authored Elixir validation" do
    base = baseline()
    trusted = expected()
    assert Raw.normalize!(base) === trusted

    cases =
      input("models.jsonl.gz") |> File.read!() |> :zlib.gunzip() |> String.split("\n", trim: true)

    observations =
      Enum.map(cases, fn line ->
        item = Jason.decode!(line)

        {raw_valid, selected} =
          try do
            patch = item["patch_base64"] |> Base.decode64!() |> Raw.decode!()
            raw = apply_patch(base, patch)
            rv = valid(fn -> Raw.validate!(raw) end)
            normalized = if rv, do: Raw.normalize!(raw), else: nil
            {rv, rv and normalized === trusted}
          catch
            :malformed_catalog -> {false, false}
          end

        assert raw_valid === item["raw_valid"],
               "raw model #{item["index"]}: #{inspect({raw_valid, item["raw_valid"]})}"

        assert selected === item["selected"],
               "selected model #{item["index"]}: #{inspect({selected, item["selected"]})}"

        %{index: item["index"], raw_valid: raw_valid, selected: selected, passed: true}
      end)

    Evidence.save("elixir-models.json", %{
      total: length(observations),
      passed: true,
      cases: observations
    })
  end

  test "strict transport rejects duplicate keys, parser abuse and finite resource overflows" do
    invalid = [
      "{\"name\":1,\"na\\u006de\":2}",
      "{\"x\":[{\"a\":{\"k\":1,\"k\":2}}]}",
      "{\"x\":NaN}",
      "{\"x\":Infinity}",
      "{\"x\":-Infinity}",
      "{\"x\":1e400}",
      "{\"x\":1,}",
      "{\"x\":01}",
      "{\"x\":+1}",
      "{\"x\":",
      "{\"x\":\"\u0001\"}",
      "{\"x\":\"\\ud800\"}",
      "{\"x\":\"" <> <<255>> <> "\"}",
      String.duplicate("[", 33) <> "0" <> String.duplicate("]", 33),
      Jason.encode!(List.duplicate(0, 4097)),
      Jason.encode!(Map.new(1..65, &{Integer.to_string(&1), 0})),
      Jason.encode!(String.duplicate("a", 1_048_577)),
      String.duplicate(" ", 4_194_305),
      Jason.encode!(List.duplicate(List.duplicate(0, 4096), 25))
    ]

    Enum.each(invalid, fn bytes ->
      assert catch_throw(Raw.decode!(bytes)) == :malformed_catalog
    end)

    assert Raw.decode!(String.duplicate("[", 32) <> "0" <> String.duplicate("]", 32)) != nil
    assert byte_size(Raw.decode!(Jason.encode!(String.duplicate("a", 1_048_576)))) == 1_048_576
    assert Raw.decode!("{\"value\":\"[{\\\"x\\\"}]\"}") == %{"value" => "[{\"x\"}]"}

    Evidence.save("transport-models.json", %{
      rejections: length(invalid),
      boundary_controls: 3,
      passed: true
    })
  end

  test "unknown model keys cannot create dynamic atoms" do
    base = baseline()

    for n <- 1..10 do
      name = "warm_catalog_unknown_#{n}"
      assert Raw.decode!(Jason.encode!(%{name => false})) == %{name => false}
      assert catch_throw(Raw.validate!(Map.put(base, name, nil))) == :malformed_catalog
      assert_raise ArgumentError, fn -> String.to_existing_atom(name) end
    end

    before_count = :erlang.system_info(:atom_count)

    names =
      Enum.map(
        1..250,
        &"catalog_inspector_unknown_atom_#{&1}_#{System.unique_integer([:positive])}"
      )

    for name <- names do
      bytes = Jason.encode!(%{name => false})
      assert Raw.decode!(bytes) == %{name => false}
      assert catch_throw(Raw.validate!(Map.put(base, name, nil))) == :malformed_catalog
      assert_raise ArgumentError, fn -> String.to_existing_atom(name) end
    end

    after_count = :erlang.system_info(:atom_count)
    assert after_count == before_count

    Evidence.save("atom-models.json", %{
      unknown_names: length(names),
      atoms_before: before_count,
      atoms_after: after_count,
      passed: true
    })
  end

  test "canonical bytes and portable array ordering match the selected Python oracle" do
    vectors = input("canonical-vectors.json") |> File.read!() |> Jason.decode!()
    for item <- vectors["scalars"], do: assert(Raw.canonical(item["value"]) == item["canonical"])
    raw = vectors["raw"]
    assert Raw.canonical(Raw.normalize!(raw)) == vectors["normalized_canonical"]

    Evidence.save("canonical-models.json", %{
      scalar_vectors: length(vectors["scalars"]),
      full_normalized_vector: 1,
      passed: true
    })
  end
end
