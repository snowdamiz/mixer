defmodule MixerHosted.Releases.BrowserHead do
  @moduledoc false
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactV3Policy, AssignmentV3}
  alias MixerHosted.Releases.Target

  @artifact_key ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @head_key @artifact_key ++ ["channel"]

  def read(identity, %Target{} = target, repo \\ MixerHosted.Repo, view \\ :summary) do
    Authorization.with_authorized_transaction(
      identity,
      "release.read",
      target.scope,
      fn _ -> read_current(repo, target, view) end,
      repo
    )
  end

  defp read_current(repo, target, view) do
    scope = target.scope

    rows =
      Session.query!(repo, query(view), [
        scope.organization_id,
        scope.project_id,
        scope.application_id,
        scope.environment_id,
        target.platform,
        target.runtime_sha256,
        target.channel
      ]).rows

    case {view, rows} do
      {_, []} ->
        {:error, :not_found}

      {:summary, [[nil, nil, nil, nil, nil]]} ->
        {:ok, %{kind: "empty", target: Target.wire(target)}}

      {view, [[nil, nil, nil, nil, nil, nil, nil, nil]]} when view in [:details, :details_v2] ->
        {:ok, %{kind: "empty", target: Target.wire(target)}}

      {view, [[%Decimal{} = sequence, bytes, rollout, manifest_digest, payload_digest | rest]]} ->
        published(
          target,
          Decimal.to_integer(sequence),
          bytes,
          rollout,
          manifest_digest,
          payload_digest,
          {view, rest}
        )

      _ ->
        {:error, :storage_unavailable}
    end
  end

  defp query(:summary) do
    """
    SELECT h.sequence,p.signed_assignment_bytes,p.rollout_basis_points,p.artifact_sha256,a.payload_sha256
    FROM public.mixer_release_heads h
    LEFT JOIN public.mixer_release_publications p
      ON (#{columns("h", @head_key)},h.sequence) = (#{columns("p", @head_key)},p.sequence)
    LEFT JOIN LATERAL public.mixer_release_bound_artifact(
      #{columns("h", @head_key)},p.artifact_sha256
    ) a ON true
    WHERE (#{columns("h", @head_key)}) = ($1,$2,$3,$4,$5,$6,$7)
    """
  end

  defp query(view) when view in [:details, :details_v2],
    do: "SELECT * FROM public.mixer_release_head_details($1,$2,$3,$4,$5,$6,$7)"

  defp published(target, sequence, bytes, rollout, manifest_digest, payload_digest, metadata) do
    scope = Target.signed_scope(target)
    %Target{channel: channel, runtime_sha256: runtime} = target

    with {:ok,
          %AssignmentV3.Signed{
            assignment:
              %{
                "scope" => ^scope,
                "channel" => ^channel,
                "runtime" => ^runtime,
                "sequence" => ^sequence,
                "rollout_basis_points" => ^rollout,
                "artifact_sha256" => ^manifest_digest,
                "release_id" => release
              } = assignment
          }} <- AssignmentV3.decode_signed(bytes),
         true <- ArtifactV3Policy.digest?(payload_digest),
         {:ok, details} <- details(metadata, assignment, payload_digest) do
      release = %{
        releaseId: release,
        sequence: Integer.to_string(sequence),
        rolloutBasisPoints: rollout,
        manifestSha256: manifest_digest,
        payloadSha256: payload_digest
      }

      {:ok,
       %{
         kind: "published",
         target: Target.wire(target),
         release: Map.merge(release, details)
       }}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp details({:summary, []}, _, _), do: {:ok, %{}}

  defp details({view, [action, signed, canonical]}, assignment, payload_digest)
       when view in [:details, :details_v2] and
              action in ~w(publish promote stage_promote rollback halt) do
    %{
      "scope" => scope,
      "runtime" => runtime,
      "release_id" => release_id,
      "artifact_sha256" => artifact_digest,
      "key_id" => assignment_key_id
    } = assignment

    with {:ok,
          %{
            "scope" => ^scope,
            "runtime" => ^runtime,
            "release_id" => ^release_id,
            "payload_sha256" => ^payload_digest,
            "source_commit" => source_commit,
            "compressed_bytes" => payload_bytes,
            "key_id" => artifact_key_id,
            "capability_hashes" => hashes,
            "capability_grants" => %{"entries" => grants}
          }, ^canonical, _signature} <- ArtifactAdmission.decode_signed_manifest(signed),
         ^artifact_digest <- Base.encode16(:crypto.hash(:sha256, canonical), case: :lower) do
      permissions = Map.new(grants, &{&1["capability_id"], &1["permissions"]})

      capabilities =
        hashes
        |> Map.keys()
        |> Enum.sort()
        |> Enum.map(&%{id: &1, permissions: Map.get(permissions, &1)})

      {:ok,
       %{
         details: %{
           sourceCommit: source_commit,
           payloadBytes: payload_bytes,
           artifactKeyId: artifact_key_id,
           assignmentKeyId: assignment_key_id,
           action: wire_action(view, action),
           capabilities: capabilities
         }
       }}
    end
  end

  defp details(_, _, _), do: {:error, :storage_unavailable}

  defp wire_action(:details, "stage_promote"), do: "promote"
  defp wire_action(_, action), do: action

  defp columns(alias_name, fields), do: Enum.map_join(fields, ",", &"#{alias_name}.#{&1}")
end
