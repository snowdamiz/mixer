defmodule MixerHosted.Releases.EnvironmentPromotion.Verifier do
  @moduledoc """
  Verifies the signed evidence for a dual-platform environment promotion.

  The authorized transaction resolves the operator-configured direction, locks
  both destination heads, and loads the source publications and their stored
  artifacts by the exact enrolled source targets. Pass that snapshot together
  with the authorization checkpoint's Unix time and each locked destination
  sequence (zero for an empty head). Recorded source sequences and digests
  must agree with the verified assignments.

  A successful result carries evidence and decoded data for this invocation.
  Callers must keep the authorization, registry and head checks and the
  resulting writes within the same transaction.
  """

  alias MixerHosted.Protocol.{ArtifactAdmission, AssignmentV3, ArtifactV3Policy}
  alias MixerHosted.Releases.EnvironmentPromotion.{Command, Direction}
  alias MixerHosted.Releases.EnvironmentPromotion.Command.{Evidence, SourcePublication}
  alias MixerHosted.Releases.EnvironmentPromotion.Direction.Enrollment
  alias MixerHosted.Releases.Target

  @type checkpoint :: %{
          now: AssignmentV3.uint64(),
          destination_last_sequences: Command.platforms(AssignmentV3.uint64())
        }
  @type evidence :: %{
          target: Target.t(),
          evidence: Evidence.t(),
          assignment: AssignmentV3.Signed.t(),
          validity_window: validity_window()
        }
  @type validity_window :: {AssignmentV3.uint64(), AssignmentV3.uint64() | nil}
  @type result :: %{
          source_commit: String.t(),
          release_id: String.t(),
          validity_window: validity_window(),
          ios: %{source: evidence(), destination: evidence()},
          android: %{source: evidence(), destination: evidence()}
        }
  @type platform :: :ios | :android
  @type failure ::
          :invalid_command
          | :invalid_direction
          | :invalid_checkpoint
          | :release_group_mismatch
          | {platform(), :manifest_content_mismatch | :payload_mismatch}
          | {platform(), :source | :destination, atom()}

  @spec verify(Command.t(), Direction.t(), checkpoint()) :: {:ok, result()} | {:error, failure()}
  def verify(
        %Command{source: source, destination: destination} = command,
        %Direction{} = direction,
        %{now: now, destination_last_sequences: sequences}
      ) do
    with :ok <- check_command(source, destination),
         :ok <- check_direction(direction),
         :ok <- check_checkpoint(now, sequences),
         {:ok, ios, {commit, release_id} = group} <-
           verify_platform(:ios, command, direction, sequences.ios, now),
         {:ok, android, android_group} <-
           verify_platform(:android, command, direction, sequences.android, now),
         :ok <- require_match(group, android_group, :release_group_mismatch) do
      window =
        [ios.source, ios.destination, android.source, android.destination]
        |> Enum.map(& &1.validity_window)
        |> intersect_windows()

      {:ok,
       %{
         source_commit: commit,
         release_id: release_id,
         ios: ios,
         android: android,
         validity_window: window
       }}
    end
  end

  def verify(%Command{}, %Direction{}, _), do: {:error, :invalid_checkpoint}
  def verify(%Command{}, _, _), do: {:error, :invalid_direction}
  def verify(_, _, _), do: {:error, :invalid_command}

  defp check_command(
         %{ios: %SourcePublication{}, android: %SourcePublication{}} = source,
         %{ios: %Evidence{}, android: %Evidence{}} = destination
       )
       when map_size(source) == 2 and map_size(destination) == 2,
       do: :ok

  defp check_command(_, _), do: {:error, :invalid_command}

  defp check_direction(%Direction{
         source: %{ios: si, android: sa} = source,
         destination: %{ios: di, android: da} = destination
       })
       when map_size(source) == 2 and map_size(destination) == 2 do
    with {:ok, source_scope} <- enrolled_scope(si, "ios"),
         {:ok, ^source_scope} <- enrolled_scope(sa, "android"),
         {:ok, destination_scope} <- enrolled_scope(di, "ios"),
         {:ok, ^destination_scope} <- enrolled_scope(da, "android"),
         true <-
           %{source_scope | environment_id: destination_scope.environment_id} ===
             destination_scope,
         true <- source_scope.environment_id != destination_scope.environment_id do
      :ok
    else
      _ -> {:error, :invalid_direction}
    end
  end

  defp check_direction(_), do: {:error, :invalid_direction}

  defp enrolled_scope(
         %Enrollment{target: %Target{platform: platform} = target, host: host, roots: roots},
         platform
       ) do
    with {:ok, ^target} <- Target.new(target),
         scope = Target.signed_scope(target),
         true <- ArtifactV3Policy.host?(host),
         true <- host["scope"] === scope and host["runtime"] === target.runtime_sha256,
         true <- ArtifactV3Policy.roots?(roots),
         true <- Enum.all?(roots, &(&1["scope"] === scope)) do
      {:ok, target.scope}
    else
      _ -> {:error, :invalid_enrollment}
    end
  end

  defp enrolled_scope(_, _), do: {:error, :invalid_enrollment}

  defp check_checkpoint(now, %{ios: ios, android: android} = sequences)
       when map_size(sequences) == 2 do
    if Enum.all?([now, ios, android], &ArtifactV3Policy.uint?/1),
      do: :ok,
      else: {:error, :invalid_checkpoint}
  end

  defp check_checkpoint(_, _), do: {:error, :invalid_checkpoint}

  defp verify_platform(platform, command, direction, last_sequence, now) do
    with {:ok, source, source_manifest} <-
           verify_source(command.source[platform], direction.source[platform], now)
           |> locate_error(platform, :source),
         {:ok, destination, destination_manifest} <-
           verify_evidence(
             command.destination[platform],
             direction.destination[platform],
             last_sequence,
             now
           )
           |> locate_error(platform, :destination),
         :ok <-
           require_match(
             source.evidence.payload,
             destination.evidence.payload,
             {platform, :payload_mismatch}
           ),
         :ok <-
           require_match(
             release_content(source_manifest),
             release_content(destination_manifest),
             {platform, :manifest_content_mismatch}
           ) do
      group = {source_manifest["source_commit"], source_manifest["release_id"]}
      {:ok, %{source: source, destination: destination}, group}
    end
  end

  defp verify_source(
         %SourcePublication{sequence: sequence, artifact_sha256: digest, evidence: evidence},
         enrollment,
         now
       ) do
    # Source evidence comes from a selected committed row. Its sequence is
    # matched to that row, while destination evidence must advance its head.
    with {:ok, checked, manifest} <- verify_evidence(evidence, enrollment, 0, now),
         %{"sequence" => ^sequence, "artifact_sha256" => ^digest} <- checked.assignment.assignment do
      {:ok, checked, manifest}
    else
      %{} -> {:error, :publication_binding}
      {:error, _} = error -> error
    end
  end

  defp verify_source(_, _, _), do: {:error, :invalid_evidence}

  defp verify_evidence(
         %Evidence{
           signed_assignment_bytes: assignment_bytes,
           signed_manifest_bytes: manifest_bytes
         } = evidence,
         %Enrollment{target: target, host: host, roots: roots},
         last_sequence,
         now
       ) do
    # AssignmentV3 also verifies and binds the artifact. Read the closed
    # manifest from those same bytes for the cross-environment comparison.
    with {:ok, signed} <-
           AssignmentV3.verify(assignment_bytes, evidence, roots, host, %{
             channel: target.channel,
             last_sequence: last_sequence,
             now: now
           }),
         {:ok, manifest, _, _} <- ArtifactAdmission.decode_signed_manifest(manifest_bytes) do
      # Successful verification selected these unique roots from the same enrollment.
      windows =
        for key <- [signed.assignment["key_id"], manifest["key_id"]] do
          root = Enum.find(roots, &(&1["key_id"] == key))
          expiry = root["not_after_unix"]
          {root["not_before_unix"], if(expiry == 0, do: nil, else: expiry)}
        end

      {:ok,
       %{
         target: target,
         evidence: evidence,
         assignment: signed,
         validity_window: intersect_windows(windows)
       }, manifest}
    end
  end

  defp verify_evidence(_, _, _, _), do: {:error, :invalid_evidence}

  defp intersect_windows(windows) do
    start = windows |> Enum.map(&elem(&1, 0)) |> Enum.max()
    expiries = for {_, expiry} <- windows, expiry != nil, do: expiry
    {start, Enum.min(expiries, fn -> nil end)}
  end

  defp release_content(manifest) do
    # The native fingerprint includes application.environment. Each runtime
    # has already been checked against its own enrolled host.
    manifest
    |> Map.drop(~w(runtime key_id created_at_unix))
    |> Map.update!("scope", &Map.delete(&1, "environment"))
  end

  defp require_match(left, right, _) when left === right, do: :ok
  defp require_match(_, _, reason), do: {:error, reason}

  defp locate_error({:error, reason}, platform, side), do: {:error, {platform, side, reason}}
  defp locate_error(result, _, _), do: result
end
