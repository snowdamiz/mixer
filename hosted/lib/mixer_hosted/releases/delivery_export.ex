defmodule MixerHosted.Releases.DeliveryExport do
  @moduledoc """
  Private input for a future delivery lease writer.

  Read the exact enrolled head and recent published artifacts from one
  PostgreSQL statement snapshot. A zero rollout supplies the signed
  assignment and may retain artifacts for clients with earlier assignments.
  The exclusive validity bound is a Unix second, or nil when all required
  roots have open-ended validity.
  The caller still needs to bound and fence lease issuance and pointer updates.
  """

  alias MixerHosted.Protocol.{ArtifactAdmission, AssignmentV3}
  alias MixerHosted.Releases.{DeliveryRepo, PublicDelivery, Target}

  @query """
  SELECT sequence,previous_sequence,action,rollout,manifest_digest,assignment,
         canonical_manifest,envelope,envelope_digest,payload_digest
  FROM public.mixer_release_delivery_snapshot($1,$2,$3,$4,$5,$6,$7)
  ORDER BY history_sequence DESC NULLS FIRST
  """
  @coordinates ~w(organization project app environment platform runtime channel)
  @artifact_limit 32

  def current(%Target{} = target), do: project(target, :standalone)
  def current(_), do: {:error, :not_found}

  # This entry point reads the projection on the caller's connection. The
  # caller must separately hold any authority needed for an external write.
  @doc false
  def current_in_transaction(%Target{} = target), do: project(target, :in_transaction)

  defp project(target, mode) do
    with {:ok, config} <- PublicDelivery.configuration(),
         {:ok, entry} <- PublicDelivery.select(config, target),
         coordinates = wire_target(target),
         true <- connection_mode?(mode),
         {:ok, head, history} <- read(coordinates) do
      now = System.system_time(:second)

      with {:ok, export} <- verify_head(entry, head, now),
           {:ok, export} <- admit_history(entry, export, history, now),
           {:ok, ^config} <- PublicDelivery.configuration(),
           checked_at = System.system_time(:second),
           true <- checked_at >= now,
           true <- is_nil(export.valid_until_unix) or checked_at < export.valid_until_unix do
        {:ok, Map.put(export, :target, coordinates)}
      else
        _ -> {:error, :rejected}
      end
    else
      :disabled -> {:error, :unavailable}
      false -> {:error, :unavailable}
      :error -> {:error, :not_found}
      {:error, _} = error -> error
    end
  end

  defp connection_mode?(:standalone), do: not DeliveryRepo.checked_out?()
  defp connection_mode?(:in_transaction), do: DeliveryRepo.in_transaction?()

  defp wire_target(target) do
    Map.merge(Target.signed_scope(target), %{
      "runtime" => target.runtime_sha256,
      "channel" => target.channel
    })
  end

  defp read(coordinates) do
    args = Enum.map(@coordinates, &Map.fetch!(coordinates, &1))

    case Ecto.Adapters.SQL.query(DeliveryRepo, @query, args,
           timeout: 5_000,
           queue: false,
           log: false
         ) do
      {:ok, %{rows: [[sequence | _] = head | history]}}
      when is_binary(sequence) and length(history) <= @artifact_limit ->
        {:ok, head, history}

      {:ok, %{rows: []}} ->
        {:error, :not_found}

      _ ->
        {:error, :unavailable}
    end
  end

  defp verify_head(
         %{target: target, roots: roots, host: host},
         [
           sequence,
           previous,
           action,
           rollout,
           digest,
           bytes,
           canonical,
           envelope,
           envelope_digest,
           payload_digest
         ],
         now
       ) do
    context = %{channel: target.channel, last_sequence: 0, now: now}

    with ^envelope_digest <- sha256(envelope),
         {:ok, artifact} <- ArtifactAdmission.decode_envelope(envelope),
         {:ok, manifest, ^canonical, _} <-
           ArtifactAdmission.decode_signed_manifest(artifact.signed_manifest_bytes),
         ^digest <- sha256(canonical),
         %{"payload_sha256" => ^payload_digest} <- manifest,
         {:ok, signed} <-
           verify_assignment(action, previous, bytes, artifact, roots, host, context),
         %{
           "sequence" => signed_sequence,
           "rollout_basis_points" => ^rollout,
           "artifact_sha256" => ^digest
         } <- signed.assignment,
         ^sequence <- Integer.to_string(signed_sequence) do
      enabled = rollout > 0
      assignment_key = signed.assignment["key_id"]

      key_ids =
        if action == "halt", do: [assignment_key], else: [assignment_key, manifest["key_id"]]

      {:ok,
       %{
         head: %{
           sequence: sequence,
           assignment_sha256: sha256(bytes),
           artifact_sha256: digest,
           rollout_basis_points: rollout,
           enabled: enabled
         },
         assignment_bytes: bytes,
         artifact:
           if(enabled,
             do: artifact_entry(digest, envelope_digest, envelope)
           ),
         valid_until_unix: validity_limit(roots, key_ids)
       }}
    end
  end

  defp admit_history(%{host: host, roots: roots}, export, history, now) do
    {historical, keys} =
      Enum.reduce(history, {[], []}, fn
        [nil, nil, nil, nil, digest, nil, canonical, envelope, envelope_digest, payload_digest],
        {artifacts, keys} = acc ->
          with ^envelope_digest <- sha256(envelope),
               {:ok,
                %{
                  manifest_sha256: ^digest,
                  canonical_manifest_cbor: ^canonical,
                  payload_sha256: ^payload_digest,
                  manifest: %{"key_id" => key}
                }} <- ArtifactAdmission.admit(envelope, host, roots, now) do
            {[artifact_entry(digest, envelope_digest, envelope) | artifacts], [key | keys]}
          else
            _ -> acc
          end
      end)

    artifacts = List.wrap(export.artifact) ++ Enum.reverse(historical)

    if length(artifacts) <= @artifact_limit do
      deadline = earliest_deadline(export.valid_until_unix, validity_limit(roots, keys))
      {:ok, Map.merge(export, %{artifacts: artifacts, valid_until_unix: deadline})}
    else
      {:error, :rejected}
    end
  end

  defp artifact_entry(digest, envelope_digest, envelope) do
    %{manifest_sha256: digest, envelope_sha256: envelope_digest, envelope_bytes: envelope}
  end

  defp earliest_deadline(nil, other), do: other
  defp earliest_deadline(other, nil), do: other
  defp earliest_deadline(first, second), do: min(first, second)

  defp verify_assignment("halt", previous, bytes, artifact, roots, host, context)
       when is_binary(previous) do
    with {last, ""} <- Integer.parse(previous) do
      AssignmentV3.verify_halt(bytes, artifact, roots, host, %{context | last_sequence: last})
    end
  end

  defp verify_assignment(action, _, bytes, artifact, roots, host, context)
       when action in ["publish", "promote", "rollback", "stage_promote"],
       do: AssignmentV3.verify(bytes, artifact, roots, host, context)

  defp verify_assignment(_, _, _, _, _, _, _), do: {:error, :invalid_action}

  defp validity_limit(roots, ids) do
    roots
    |> Enum.flat_map(fn %{"key_id" => id, "not_after_unix" => expiry} ->
      if id in ids and expiry > 0, do: [expiry], else: []
    end)
    |> Enum.min(fn -> nil end)
  end

  defp sha256(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
end
