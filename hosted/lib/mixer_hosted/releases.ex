defmodule MixerHosted.Releases do
  @moduledoc """
  Local v3 publication ledger for a single provisioned target.

  The browser seam verifies the exact stored artifact and signed assignment
  inside the fresh authorization transaction. The configured Repo connects as
  the provisioned restricted Phoenix writer.
  """

  import Ecto.Query, only: [from: 2]
  alias Ecto.Changeset
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Identity.{Encoding, VerifiedIdentity}
  alias MixerHosted.Protocol.{ArtifactV3Policy, AssignmentV3}
  alias MixerHosted.Releases.{Head, Publication, Target}

  @action "release.publish"
  @value_fields [:artifact_sha256, :signed_assignment_bytes, :rollout_basis_points]

  @type result :: %{
          sequence: pos_integer(),
          previous_sequence: pos_integer() | nil,
          artifact_sha256: String.t(),
          signed_assignment_bytes: binary(),
          rollout_basis_points: 0..10_000
        }

  @type signed_command :: {:signed, Target.t(), binary(), (module() -> :ok)}

  @spec publish(
          VerifiedIdentity.t(),
          signed_command(),
          String.t(),
          String.t(),
          module()
        ) ::
          {:ok, result()} | {:error, atom()}
  def publish(identity, command, key, reason, repo \\ MixerHosted.Repo)

  # The internal browser caller supplies the retained session check. The actual
  # host, channel and roots come from explicit trusted server provisioning.
  def publish(identity, {:signed, %Target{} = target, bytes, current!}, key, reason, repo)
      when is_binary(bytes) and is_function(current!, 1) do
    with {:ok, ^target} <- Target.new(target),
         true <- valid_metadata?(key, reason),
         {:ok, signed} <- AssignmentV3.decode_signed(bytes),
         {:ok, config} <- configured_target(target) do
      Authorization.with_authorized_transaction(
        identity,
        @action,
        target.scope,
        fn context ->
          publish_signed!(context, repo, target, signed, config, current!, key, reason)
        end,
        repo
      )
    else
      {:error, reason} = error when reason in [:not_found, :authorization_unavailable] -> error
      _ -> {:error, :invalid_request}
    end
  end

  def publish(_, _, _, _, _), do: {:error, :invalid_request}

  defp publish_signed!(context, repo, target, signed, config, current!, key, reason) do
    check_writer!(repo)
    filter = Target.filter(target)

    with %Head{} = head <- repo.one(from(h in Head, where: ^filter, lock: "FOR UPDATE")),
         {:ok, artifact} <- stored_artifact(repo, target, signed.assignment["artifact_sha256"]) do
      stored = repo.get_by(Publication, [{:idempotency_key, key} | filter])
      last = if is_nil(stored) and head.sequence, do: Decimal.to_integer(head.sequence), else: 0
      :ok = current!.(repo)
      fresh = Context.checkpoint!(context, repo, @action, target.scope)
      {:ok, ^config} = configured_target(target)

      case verify(signed, artifact, config, target, last, fresh.checked_at) do
        {:ok, signed} ->
          values = %{
            sequence: Decimal.new(signed.assignment["sequence"]),
            idempotency_key: key,
            reason: reason,
            principal_id: fresh.principal.id,
            artifact_sha256: signed.assignment["artifact_sha256"],
            signed_assignment_bytes: signed.signed_assignment_bytes,
            rollout_basis_points: signed.assignment["rollout_basis_points"]
          }

          result =
            if stored,
              do: replay(stored, values),
              else: append(repo, head, Map.new(filter), values)

          with {:ok, _} <- result do
            {:ok, ^config} = configured_target(target)
            now = Context.checkpoint!(context, repo, @action, target.scope).checked_at

            if now != fresh.checked_at,
              do: {:ok, ^signed} = verify(signed, artifact, config, target, last, now)

            :ok = current!.(repo)
            result
          end

        error ->
          error
      end
    else
      nil -> {:error, :not_found}
      error -> error
    end
  end

  defp configured_target(target) do
    case Application.fetch_env(:mixer_hosted, :local_release_target) do
      {:ok, %{target: ^target, host: host, roots: roots} = config} when map_size(config) == 3 ->
        if ArtifactV3Policy.host?(host) and host["scope"] == Target.signed_scope(target) and
             host["runtime"] == target.runtime_sha256 and ArtifactV3Policy.roots?(roots),
           do: {:ok, config},
           else: {:error, :authorization_unavailable}

      _ ->
        {:error, :not_found}
    end
  end

  defp stored_artifact(repo, target, digest) do
    %Target{scope: scope, platform: platform, runtime_sha256: runtime} = target

    case Session.query!(
           repo,
           """
           SELECT signed_manifest_bytes,payload,payload_sha256
           FROM public.mixer_release_bound_artifact($1,$2,$3,$4,$5,$6,$7,$8)
           """,
           [
             scope.organization_id,
             scope.project_id,
             scope.application_id,
             scope.environment_id,
             platform,
             runtime,
             target.channel,
             digest
           ]
         ).rows do
      [[manifest, payload, payload_digest]] ->
        if Base.encode16(:crypto.hash(:sha256, payload), case: :lower) == payload_digest do
          {:ok, %{signed_manifest_bytes: manifest, payload: payload}}
        else
          {:error, :storage_unavailable}
        end

      [] ->
        {:error, :not_found}
    end
  end

  defp verify(signed, artifact, config, target, last, now) do
    context = %{channel: target.channel, last_sequence: last, now: now}

    case AssignmentV3.verify(
           signed.signed_assignment_bytes,
           artifact,
           config.roots,
           config.host,
           context
         ) do
      {:ok, ^signed} = verified -> verified
      {:error, :assignment_replay} -> {:error, :conflict}
      {:error, :root_policy} -> {:error, :permission_denied}
      {:error, _} -> {:error, :invalid_request}
    end
  end

  defp append(repo, head, target, values) do
    if is_nil(head.sequence) or Decimal.gt?(values.sequence, head.sequence) do
      row =
        struct!(
          Publication,
          Map.merge(target, Map.put(values, :previous_sequence, head.sequence))
        )

      changeset =
        row
        |> Changeset.change()
        |> Changeset.foreign_key_constraint(:artifact_sha256,
          name: :mixer_release_exact_artifact
        )

      case repo.insert(changeset) do
        {:ok, stored} ->
          repo.update!(Changeset.change(head, sequence: stored.sequence))
          {:ok, result(stored)}

        {:error, %Changeset{errors: [artifact_sha256: _]}} ->
          {:error, :not_found}

        {:error, _} ->
          {:error, :storage_unavailable}
      end
    else
      {:error, :conflict}
    end
  end

  defp replay(stored, values) do
    # Numeric may round-trip with a different scale. Compare its value exactly.
    if Decimal.equal?(stored.sequence, values.sequence) and
         Map.take(stored, Map.keys(values) -- [:sequence]) === Map.delete(values, :sequence) do
      {:ok, result(stored)}
    else
      {:error, :idempotency_conflict}
    end
  end

  defp result(stored) do
    stored
    |> Map.take(@value_fields)
    |> Map.put(:sequence, Decimal.to_integer(stored.sequence))
    |> Map.put(
      :previous_sequence,
      stored.previous_sequence && Decimal.to_integer(stored.previous_sequence)
    )
  end

  defp valid_metadata?(key, reason) do
    is_binary(key) and byte_size(key) in 1..128 and
      Regex.match?(~r/\A[A-Za-z0-9_.:-]+\z/, key) and
      Encoding.bounded_string?(reason, 512) and :binary.match(reason, <<0>>) == :nomatch
  end

  defp check_writer!(repo) do
    [[count, safe?]] =
      Session.query!(repo, """
      SELECT count(*),bool_and(c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity
        AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
        AND NOT pg_catalog.pg_has_role(current_user,c.relowner,'MEMBER')
        AND NOT pg_catalog.has_schema_privilege(current_user,'public','CREATE')
        AND NOT pg_catalog.has_table_privilege(current_user,c.oid,'DELETE,TRUNCATE,REFERENCES,TRIGGER')
        AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'REFERENCES')
        AND CASE WHEN c.relname='mixer_release_heads' THEN
          NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'INSERT')
          AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0
              AND NOT a.attisdropped AND a.attname<>'sequence'
              AND pg_catalog.has_column_privilege(current_user,c.oid,a.attnum,'UPDATE'))
        ELSE NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'UPDATE')
          AND NOT pg_catalog.has_column_privilege(current_user,c.oid,'recorded_at','INSERT') END)
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
      WHERE c.oid IN ('public.mixer_release_heads'::regclass,'public.mixer_release_publications'::regclass)
      """).rows

    if count != 2 or not safe?, do: repo.rollback(:authorization_unavailable)
  end
end
