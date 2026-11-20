defmodule MixerHosted.Releases.BrowserHead do
  @moduledoc false
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Protocol.{ArtifactV3Policy, AssignmentV3}
  alias MixerHosted.Releases.Target

  @artifact_key ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @head_key @artifact_key ++ ["channel"]

  def read(identity, %Target{} = target, repo \\ MixerHosted.Repo) do
    Authorization.with_authorized_transaction(
      identity,
      "release.read",
      target.scope,
      fn _ -> read_current(repo, target) end,
      repo
    )
  end

  defp read_current(repo, target) do
    scope = target.scope

    rows =
      Session.query!(
        repo,
        """
        SELECT h.sequence,p.signed_assignment_bytes,p.rollout_basis_points,p.artifact_sha256,a.payload_sha256
        FROM public.mixer_release_heads h
        LEFT JOIN public.mixer_release_publications p
          ON (#{columns("h", @head_key)},h.sequence) = (#{columns("p", @head_key)},p.sequence)
        LEFT JOIN LATERAL public.mixer_release_bound_artifact(
          #{columns("h", @head_key)},p.artifact_sha256
        ) a ON true
        WHERE (#{columns("h", @head_key)}) = ($1,$2,$3,$4,$5,$6,$7)
        """,
        [
          scope.organization_id,
          scope.project_id,
          scope.application_id,
          scope.environment_id,
          target.platform,
          target.runtime_sha256,
          target.channel
        ]
      ).rows

    case rows do
      [] ->
        {:error, :not_found}

      [[nil, nil, nil, nil, nil]] ->
        {:ok, %{kind: "empty", target: Target.wire(target)}}

      [[%Decimal{} = sequence, bytes, rollout, manifest_digest, payload_digest]] ->
        published(
          target,
          Decimal.to_integer(sequence),
          bytes,
          rollout,
          manifest_digest,
          payload_digest
        )

      _ ->
        {:error, :storage_unavailable}
    end
  end

  defp published(target, sequence, bytes, rollout, manifest_digest, payload_digest) do
    scope = Target.signed_scope(target)
    %Target{channel: channel, runtime_sha256: runtime} = target

    with {:ok,
          %AssignmentV3.Signed{
            assignment: %{
              "scope" => ^scope,
              "channel" => ^channel,
              "runtime" => ^runtime,
              "sequence" => ^sequence,
              "rollout_basis_points" => ^rollout,
              "artifact_sha256" => ^manifest_digest,
              "release_id" => release
            }
          }} <- AssignmentV3.decode_signed(bytes),
         true <- ArtifactV3Policy.digest?(payload_digest) do
      {:ok,
       %{
         kind: "published",
         target: Target.wire(target),
         release: %{
           releaseId: release,
           sequence: Integer.to_string(sequence),
           rolloutBasisPoints: rollout,
           manifestSha256: manifest_digest,
           payloadSha256: payload_digest
         }
       }}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp columns(alias_name, fields), do: Enum.map_join(fields, ",", &"#{alias_name}.#{&1}")
end
