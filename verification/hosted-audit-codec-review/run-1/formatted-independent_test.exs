defmodule MixerHosted.Audit.IndependentUploadEventReviewTest do
  use ExUnit.Case, async: false
  import ExUnit.CaptureIO
  import ExUnit.CaptureLog
  alias MixerHosted.Audit.UploadEvent

  @error {:error, :invalid_audit_event}
  @fixture Path.expand("independent-vectors.json", __DIR__)
  @binary ~w(event_cbor event_hash previous_hash previous_state current_state display_bytes)

  defp vectors, do: @fixture |> File.read!() |> Jason.decode!()

  defp row(nil), do: nil

  defp row(raw) do
    Map.new(raw, fn {key, value} ->
      {String.to_existing_atom(key),
       if(key in @binary, do: Base.decode16!(value, case: :lower), else: value)}
    end)
  end

  defp golden, do: vectors()["cases"] |> hd() |> Map.fetch!("row") |> row()

  test "independent typed-first bytes and coherent malformed display cases" do
    for specimen <- vectors()["cases"] do
      r = row(specimen["row"])
      expected_hash = :crypto.hash(:sha256, "mixer.hosted.audit.v1" <> <<0>> <> r.event_cbor)
      assert r.event_hash == expected_hash, specimen["label"]

      # The hash field's uppercase spelling case intentionally changes only spelling.
      assert String.downcase(r.display_json["hash"]) == Base.encode16(expected_hash, case: :lower)

      expected =
        if specimen["accepted"] do
          {:ok,
           %{event_cbor: r.event_cbor, event_hash: expected_hash, display_bytes: r.display_bytes}}
        else
          @error
        end

      assert UploadEvent.decode(r.display_json) == expected, specimen["label"]
      expected_row = if specimen["row_accepted"], do: :ok, else: @error
      assert UploadEvent.validate_row(r) == expected_row, specimen["label"]
    end
  end

  test "separately valid rows isolate predecessor and tenant conditions" do
    for specimen <- vectors()["edges"] do
      current = row(specimen["current"])
      previous = row(specimen["previous"])
      assert UploadEvent.validate_row(current) == :ok, specimen["label"]
      if previous, do: assert(UploadEvent.validate_row(previous) == :ok, specimen["label"])
      expected = if specimen["accepted"], do: :ok, else: @error
      assert UploadEvent.validate_edge(current, previous) == expected, specimen["label"]
    end
  end

  test "semantically equal alternate JSON bytes fail exact retention" do
    r = golden()
    escaped = String.replace(r.display_bytes, "é", "\\u00e9")
    escaped = String.replace(escaped, "水", "\\u6c34")
    slash = String.replace(r.display_bytes, "/", "\\/")
    order = Jason.encode!(r.display_json)

    for alternate <- [escaped, slash, order, r.display_bytes <> "\n"] do
      assert alternate != r.display_bytes
      assert Jason.decode!(alternate) == r.display_json
      assert UploadEvent.validate_row(%{r | display_bytes: alternate}) == @error
    end
  end

  test "invalid input emits neither diagnostics nor source values" do
    r = golden()
    secret = "REVIEW_SOURCE_VALUE_MUST_NOT_BE_REPORTED"

    assert capture_log(fn ->
             assert capture_io(fn ->
                      assert capture_io(:stderr, fn ->
                               for malformed <- [
                                     Map.put(r.display_json, "reason", secret <> <<0>>),
                                     Map.put(r.display_json, "reason", <<0xFF>>),
                                     Map.put(r.display_json, "actor", [secret | self()]),
                                     Map.put(
                                       r.display_json,
                                       "decision",
                                       List.duplicate(secret, 100_000)
                                     )
                                   ] do
                                 assert UploadEvent.decode(malformed) == @error
                               end

                               assert UploadEvent.validate_row(%{r | event_hash: secret}) ==
                                        @error

                               assert UploadEvent.validate_edge(secret, r) == @error
                             end) == ""
                    end) == ""
           end) == ""
  end

  test "closed key sets reject replacement keys and atom names" do
    r = golden()
    d = r.display_json
    replaced = d |> Map.delete("source_ip") |> Map.put("replacement", nil)
    assert map_size(replaced) == 16
    assert UploadEvent.decode(replaced) == @error
    atomized = Map.new(d, fn {k, v} -> {String.to_atom(k), v} end)
    assert UploadEvent.decode(atomized) == @error
    string_row = Map.new(r, fn {k, v} -> {Atom.to_string(k), v} end)
    assert UploadEvent.validate_row(string_row) == @error
  end

  test "artifact encoder retains its prior null and byte-string rejection" do
    alias MixerHosted.Protocol.ArtifactCBOR
    assert ArtifactCBOR.encode(nil) == {:error, :invalid_value}
    assert ArtifactCBOR.encode({:bytes, <<1, 2>>}) == {:error, :invalid_value}
    assert ArtifactCBOR.encode([nil]) == {:error, :invalid_value}
  end
end
