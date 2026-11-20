defmodule MixerHosted.Protocol.AssignmentV3Test do
  use ExUnit.Case, async: true

  alias MixerHosted.Protocol.{ArtifactJSON, AssignmentV3}

  @fixtures Path.expand("../../../../services/protocol/testdata", __DIR__)
  @max_uint 18_446_744_073_709_551_615

  setup do
    bytes = File.read!(Path.join(@fixtures, "signed-release-v3.json"))
    {:ok, vector, spans, _} = ArtifactJSON.decode(bytes, 65_536)
    assert vector["test_only"]

    %{
      assignment_bytes: signed_bytes(bytes, spans, "signed_assignment"),
      artifact: %{
        signed_manifest_bytes: signed_bytes(bytes, spans, "signed_manifest"),
        payload: Base.decode64!(vector["payload"])
      },
      host: vector["host"],
      roots:
        Enum.map(
          vector["roots"],
          &Map.update!(&1, "public_key", fn key -> Base.decode64!(key) end)
        ),
      context: %{
        channel: "beta",
        last_sequence: vector["last_sequence"],
        now: vector["verification_time_unix"]
      },
      vector: vector
    }
  end

  test "preserves the exact signed document, assignment fields, signature and canonical CBOR",
       f do
    assert {:ok, signed} = AssignmentV3.decode_signed(f.assignment_bytes)
    assert signed.signed_assignment_bytes == f.assignment_bytes
    assert signed.assignment == f.vector["signed_assignment"]["assignment"]
    assert signed.signature == Base.decode64!(f.vector["signed_assignment"]["signature"])

    assert Base.encode16(signed.canonical_assignment_cbor, case: :lower) ==
             f.vector["assignment_cbor_hex"]

    assert Base.encode16("mixer.assignment.v3\0" <> signed.canonical_assignment_cbor,
             case: :lower
           ) ==
             f.vector["assignment_message_hex"]

    assert {:ok, ^signed} = verify(f)
  end

  test "consumes the unchanged public signed acceptance and refusal corpus", f do
    corpus = @fixtures |> Path.join("release-v3-cases.json") |> File.read!() |> Jason.decode!()
    assert corpus["test_only"]
    assert length(corpus["assignment_cases"]) == 36

    for entry <- corpus["assignment_cases"] do
      result = verify(%{f | assignment_bytes: entry["signed_assignment_json"]})

      # The corpus checks delivery to an installation. A ledger must also admit a halt.
      expected = entry["accepted"] or entry["name"] == "zero-rollout"
      assert match?({:ok, _}, result) == expected, entry["name"]

      if entry["name"] == "zero-rollout" do
        assert {:ok, %{assignment: %{"rollout_basis_points" => 0}}} = result
      end
    end
  end

  test "verifies the public max-uint64 sequence above a persisted high-water mark", f do
    cases =
      @fixtures |> Path.join("release-v3-cases.json") |> File.read!() |> Jason.decode!()

    entry =
      Enum.find(cases["assignment_cases"], &(&1["name"] == "sequence-18446744073709551615"))

    bytes = entry["signed_assignment_json"]
    assert {:ok, %{assignment: %{"sequence" => @max_uint}}} = AssignmentV3.decode_signed(bytes)
    f = %{f | assignment_bytes: bytes, context: %{f.context | last_sequence: @max_uint - 1}}

    assert {:ok, %{assignment: %{"sequence" => @max_uint}}} = verify(f)
    assert {:error, :assignment_replay} = verify(put_in(f.context.last_sequence, @max_uint))

    for invalid <- [-1, @max_uint + 1, "0", 0.0] do
      assert {:error, :invalid_context} = verify(put_in(f.context.last_sequence, invalid))
    end
  end

  test "rejects ambiguous signed transport before verification", f do
    raw = f.vector["signed_assignment"]
    padded = Base.encode64(<<0::512>>)
    noncanonical_tail = binary_part(padded, 0, 85) <> "B=="

    for invalid <- [
          nil,
          [],
          String.trim_trailing(padded, "="),
          noncanonical_tail,
          Base.url_encode64(:binary.copy(<<255>>, 64)),
          String.replace_prefix(padded, "AA", "\r\n"),
          Base.encode64(<<0::504>>)
        ] do
      assert {:error, _} =
               raw
               |> Map.put("signature", invalid)
               |> Jason.encode!()
               |> AssignmentV3.decode_signed()
    end

    oversized_sequence =
      String.replace(
        f.assignment_bytes,
        ~r/"sequence"\s*:\s*7/,
        "\"sequence\":18446744073709551616"
      )

    duplicate_scope =
      String.replace(
        f.assignment_bytes,
        "\"organization\":",
        "\"org\\u0061nization\":\"duplicate\",\"organization\":"
      )

    for invalid <- [
          oversized_sequence,
          duplicate_scope,
          f.assignment_bytes <> "{}",
          raw |> put_in(["assignment", "expires_at_unix"], 1) |> Jason.encode!(),
          Jason.encode!(Map.put(raw, "extra", true))
        ] do
      assert {:error, _} = AssignmentV3.decode_signed(invalid)
    end
  end

  test "requires current and unambiguous assignment authority", f do
    [artifact, assignment] = f.roots
    now = f.context.now

    for changed <- [
          %{assignment | "assignment" => false, "artifact" => true},
          %{assignment | "revoked" => true},
          %{assignment | "not_before_unix" => now + 1},
          %{assignment | "not_after_unix" => now},
          %{assignment | "scope" => %{assignment["scope"] | "app" => "another"}},
          %{assignment | "public_key" => artifact["public_key"]}
        ] do
      assert {:error, _} = verify(%{f | roots: [artifact, changed]})
    end

    for roots <- [
          [artifact],
          [artifact, assignment, assignment],
          [artifact, assignment | :invalid]
        ] do
      assert {:error, :root_policy} = verify(%{f | roots: roots})
    end

    bounded = %{assignment | "not_before_unix" => now, "not_after_unix" => now + 1}
    assert {:ok, _} = verify(%{f | roots: [artifact, bounded]})
  end

  test "rechecks the signed artifact, exact payload and installed host under current policy", f do
    [artifact, assignment] = f.roots
    expired = %{artifact | "not_after_unix" => f.context.now}
    assert {:error, :artifact_rejected} = verify(%{f | roots: [expired, assignment]})

    assert {:error, :artifact_rejected} = verify(put_in(f.host["state_version"], @max_uint))
    assert {:error, :assignment_binding} = verify(put_in(f.context.channel, "other"))

    <<first, rest::binary>> = f.artifact.payload

    assert {:error, :artifact_rejected} =
             verify(put_in(f.artifact.payload, <<rem(first + 1, 256), rest::binary>>))

    signed = %{f.vector["signed_manifest"] | "signature" => Base.encode64(<<0::512>>)}

    assert {:error, :artifact_rejected} =
             verify(put_in(f.artifact.signed_manifest_bytes, Jason.encode!(signed)))
  end

  defp verify(f),
    do: AssignmentV3.verify(f.assignment_bytes, f.artifact, f.roots, f.host, f.context)

  defp signed_bytes(bytes, spans, field) do
    {_, _, start, size} =
      Enum.find(spans, fn {key_start, key_size, _, _} ->
        Jason.decode!(binary_part(bytes, key_start, key_size)) == field
      end)

    binary_part(bytes, start, size)
  end
end
