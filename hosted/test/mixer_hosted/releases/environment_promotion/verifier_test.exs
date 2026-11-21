defmodule MixerHosted.Releases.EnvironmentPromotion.VerifierTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Protocol.AssignmentV3
  alias MixerHosted.Releases.EnvironmentPromotion.{Command, Direction, Verifier}

  import MixerHosted.Test.StagePromotionSigningFixture

  setup do
    vector = vector()
    assert vector["test_only"]

    source = %{
      ios: variant(vector, "ios", "development", "internal", 7),
      android: variant(vector, "android", "development", "internal", 9)
    }

    destination = %{
      ios: variant(vector, "ios", "production", "stable", 3),
      android: variant(vector, "android", "production", "stable", 12)
    }

    direction = %Direction{
      source: Map.new(source, fn {platform, variant} -> {platform, variant.enrollment} end),
      destination:
        Map.new(destination, fn {platform, variant} -> {platform, variant.enrollment} end)
    }

    command = %Command{
      source: Map.new(source, fn {platform, variant} -> {platform, publication(variant)} end),
      destination:
        Map.new(destination, fn {platform, variant} -> {platform, evidence(variant)} end)
    }

    %{
      source: source,
      destination: destination,
      direction: direction,
      command: command,
      checkpoint: %{
        now: vector["verification_time_unix"],
        destination_last_sequences: %{ios: 0, android: 11}
      }
    }
  end

  test "verifies the four enrollments and retains the original bytes with different environment fingerprints",
       f do
    assert {:ok, verified} = verify(f)
    assert verified.source_commit == f.source.ios.manifest["source_commit"]
    assert verified.release_id == f.source.ios.manifest["release_id"]

    for platform <- [:ios, :android] do
      source = verified[platform].source
      destination = verified[platform].destination
      assert source.target === f.direction.source[platform].target
      assert destination.target === f.direction.destination[platform].target
      assert source.target.runtime_sha256 != destination.target.runtime_sha256

      # The wire documents deliberately include whitespace around the JSON.
      assert source.evidence === f.command.source[platform].evidence
      assert destination.evidence === f.command.destination[platform]
      assert source.evidence.signed_manifest_bytes != destination.evidence.signed_manifest_bytes
      assert source.evidence.payload === destination.evidence.payload
      assert source.assignment.signed_assignment_bytes === source.evidence.signed_assignment_bytes

      assert destination.assignment.signed_assignment_bytes ===
               destination.evidence.signed_assignment_bytes

      assert source.assignment.assignment["sequence"] === f.command.source[platform].sequence
    end

    assert verified.ios.source.evidence.payload != verified.android.source.evidence.payload
  end

  test "requires both platform entries and an exact target, host and root policy for each side",
       f do
    missing = Map.delete(f.command.destination, :android)
    extra = Map.put(f.command.source, :other, f.command.source.ios)
    assert {:error, :invalid_command} = verify(put_in(f.command.destination, missing))
    assert {:error, :invalid_command} = verify(put_in(f.command.source, extra))

    direction = f.direction

    for invalid <- [
          %{direction | destination: direction.source},
          put_in(direction.destination.android, direction.destination.ios),
          put_in(direction.destination.ios.host, direction.source.ios.host),
          put_in(direction.destination.android.roots, direction.source.android.roots),
          update_in(direction.destination.ios.roots, fn roots ->
            [hd(direction.source.ios.roots) | roots]
          end)
        ] do
      assert {:error, :invalid_direction} = verify(%{f | direction: invalid})
    end
  end

  test "rejects a reversed configured direction and mixed tenant or environment ancestry", f do
    reversed = %Direction{source: f.direction.destination, destination: f.direction.source}
    assert {:error, {:ios, :source, _}} = verify(%{f | direction: reversed})

    for {field, wrong} <- [
          {"organization", "other-org"},
          {"project", "other-project"},
          {"app", "other-app"},
          {"environment", "other-environment"}
        ] do
      changed = move_scope(f.destination.android, field, wrong)
      assert {:ok, _} = verify_variant(changed, f.checkpoint.now)

      changed_input = put_in(f.command.destination.android, evidence(changed))
      changed_direction = put_in(changed_input.direction.destination.android, changed.enrollment)
      assert {:error, :invalid_direction} = verify(changed_direction)

      # A fully valid substitute remains outside the configured enrollment.
      assert {:error, {:android, :destination, _}} = verify(changed_input)
    end

    changed_destination =
      Map.new(f.destination, fn {platform, variant} ->
        {platform, move_scope(variant, "app", "other-app").enrollment}
      end)

    assert {:error, :invalid_direction} =
             verify(put_in(f.direction.destination, changed_destination))
  end

  test "checks each signed manifest against its own exact enrolled fingerprint", f do
    for side <- [:source, :destination], platform <- [:ios, :android] do
      variant = f[side][platform]
      runtime = digest("other-runtime")
      host = %{variant.enrollment.host | "runtime" => runtime}
      changed = put_in(variant.manifest["runtime"], runtime)

      changed = %{
        changed
        | enrollment: enroll(host, variant.assignment["channel"], variant.enrollment.roots)
      }

      assert {:ok, _} = verify_variant(changed, f.checkpoint.now)

      changed_input =
        case side do
          :source -> put_in(f.command.source[platform], publication(changed))
          :destination -> put_in(f.command.destination[platform], evidence(changed))
        end

      assert {:error, {^platform, ^side, :artifact_rejected}} = verify(changed_input)
    end
  end

  test "requires independent destination artifact and assignment signing authority", f do
    destination = f.destination.ios
    source = f.source.ios

    wrong_artifact = %{destination | artifact_key: source.artifact_key}

    assert {:error, {:ios, :destination, :artifact_rejected}} =
             verify(put_in(f.command.destination.ios, evidence(wrong_artifact)))

    wrong_assignment = %{destination | assignment_key: source.assignment_key}

    assert {:error, {:ios, :destination, :assignment_signature}} =
             verify(put_in(f.command.destination.ios, evidence(wrong_assignment)))

    wrong_source_artifact = %{source | artifact_key: destination.artifact_key}

    assert {:error, {:ios, :source, :artifact_rejected}} =
             verify(put_in(f.command.source.ios, publication(wrong_source_artifact)))

    assert {:error, {:ios, :destination, _}} =
             verify(put_in(f.command.destination.ios, f.command.source.ios.evidence))

    expired =
      update_in(f.direction.destination.android.roots, fn [artifact, assignment] ->
        [%{artifact | "not_after_unix" => f.checkpoint.now}, assignment]
      end)

    assert {:error, {:android, :destination, :artifact_rejected}} = verify(expired)
  end

  test "rejects independently valid changes to the signed release contract or payload", f do
    destination = f.destination.ios

    manifest = destination.manifest

    for changed_manifest <- [
          %{manifest | "provenance_id" => "other-provenance"},
          %{manifest | "source_commit" => String.duplicate("c", 40)},
          %{manifest | "release_id" => "other-release"},
          %{manifest | "source_map_sha256" => digest("other-map")},
          put_in(manifest["limits"]["fuel"], 999),
          put_in(manifest["capability_grants"]["entries"], []),
          put_in(manifest["state_max"], 2)
        ] do
      changed = %{destination | manifest: changed_manifest}
      assert {:ok, _} = verify_variant(changed, f.checkpoint.now)

      assert {:error, {:ios, :manifest_content_mismatch}} =
               verify(put_in(f.command.destination.ios, evidence(changed)))
    end

    changed = with_payload(destination, :binary.copy(<<0>>, byte_size(destination.payload)))
    assert {:ok, _} = verify_variant(changed, f.checkpoint.now)

    assert {:error, {:ios, :payload_mismatch}} =
             verify(put_in(f.command.destination.ios, evidence(changed)))
  end

  test "requires the same signed source revision and release ID across both platforms", f do
    for {field, value} <- [
          {"source_commit", String.duplicate("b", 40)},
          {"release_id", "other-release"}
        ] do
      source = f.source.android
      source = put_in(source.manifest[field], value)
      destination = f.destination.android
      destination = put_in(destination.manifest[field], value)

      command = %{
        f.command
        | source: %{f.command.source | android: publication(source)},
          destination: %{f.command.destination | android: evidence(destination)}
      }

      assert {:ok, _} = verify_variant(source, f.checkpoint.now)
      assert {:ok, _} = verify_variant(destination, f.checkpoint.now)
      assert {:error, :release_group_mismatch} = verify(%{f | command: command})
    end
  end

  test "binds recorded source rows and uses each locked destination sequence", f do
    assert {:error, {:ios, :source, :publication_binding}} =
             verify(put_in(f.command.source.ios.sequence, 8))

    assert {:error, {:android, :source, :publication_binding}} =
             verify(put_in(f.command.source.android.artifact_sha256, digest("other-artifact")))

    for platform <- [:ios, :android] do
      sequence = f.destination[platform].assignment["sequence"]

      assert {:error, {^platform, :destination, :assignment_replay}} =
               verify(put_in(f.checkpoint.destination_last_sequences[platform], sequence))
    end

    assert {:error, :invalid_checkpoint} =
             verify(put_in(f.checkpoint.destination_last_sequences.ios, -1))
  end

  defp verify(f), do: Verifier.verify(f.command, f.direction, f.checkpoint)

  defp verify_variant(variant, now) do
    signed = evidence(variant)
    enrollment = variant.enrollment

    AssignmentV3.verify(
      signed.signed_assignment_bytes,
      signed,
      enrollment.roots,
      enrollment.host,
      %{
        channel: enrollment.target.channel,
        last_sequence: 0,
        now: now
      }
    )
  end

  defp move_scope(variant, field, value) do
    scope = Map.put(variant.manifest["scope"], field, value)
    host = %{variant.enrollment.host | "scope" => scope}
    roots = Enum.map(variant.enrollment.roots, &%{&1 | "scope" => scope})

    %{
      variant
      | enrollment: enroll(host, variant.assignment["channel"], roots),
        manifest: %{variant.manifest | "scope" => scope},
        assignment: %{variant.assignment | "scope" => scope}
    }
  end
end
