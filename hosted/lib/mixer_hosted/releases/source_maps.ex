defmodule MixerHosted.Releases.SourceMaps do
  @moduledoc """
  Opt-in owner access to the exact map of a committed local v3 publication.
  Map bytes and the first consent deadline are immutable.
  """
  alias MixerHosted.{Authorization, Releases}
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Protocol.ArtifactV3Policy
  alias MixerHosted.Releases.{Target, WriterRepo}

  @action "release.publish"
  @maximum_bytes 4 * 1024 * 1024
  @table "public.mixer_release_source_maps"
  @target ~w(organization_id project_id application_id environment_id platform runtime_sha256 channel)a
  @key @target ++ [:sequence, :artifact_sha256]
  @where Enum.with_index(@key, 1) |> Enum.map_join(" AND ", fn {name, n} -> "#{name}=$#{n}" end)

  def maximum_bytes, do: @maximum_bytes

  def enabled?, do: Application.get_env(:mixer_hosted, :local_source_map_retention) === true

  def retain(identity, target, sequence, digest, retain_until, bytes)
      when is_integer(retain_until) and retain_until in 1..9_007_199_254_740_991 and
             is_binary(bytes) and byte_size(bytes) in 1..@maximum_bytes do
    result =
      access(identity, target, sequence, digest, fn params, hash, fresh ->
        if retain_until <= fresh.checked_at or sha256(bytes) != hash do
          {:error, :invalid_request}
        else
          query!(
            """
            INSERT INTO #{@table} (#{Enum.join(@key, ", ")}, retained_by, retain_until, map_bytes)
            SELECT $1,$2,$3,$4,$5,$6,$7,$8::numeric,$9,$10,$11::bigint,$12
            WHERE $11 > floor(extract(epoch FROM statement_timestamp()))
            ON CONFLICT DO NOTHING
            """,
            params ++ [fresh.principal.id, retain_until, bytes]
          )

          case query!("SELECT retain_until FROM #{@table} WHERE #{@where}", params).rows do
            [[^retain_until]] -> {:ok, retain_until, retain_until}
            [[_]] -> {:error, :conflict}
            [] -> {:error, :not_found}
          end
        end
      end)

    with {:ok, {deadline, _valid_until}} <- result, do: {:ok, deadline}
  end

  def retain(_, _, _, _, _, _), do: {:error, :invalid_request}

  def read(identity, target, sequence, digest) do
    result =
      access(identity, target, sequence, digest, fn params, hash, _fresh ->
        case query!("SELECT retain_until, map_bytes FROM #{@table} WHERE #{@where}", params).rows do
          [[deadline, bytes]] ->
            if sha256(bytes) == hash do
              {:ok, %{bytes: bytes, retain_until: deadline}, deadline}
            else
              {:error, :storage_unavailable}
            end

          [] ->
            {:error, :not_found}
        end
      end)

    with {:ok, {map, valid_until}} <- result, do: {:ok, Map.put(map, :valid_until, valid_until)}
  end

  defp access(identity, target, sequence, digest, operation) do
    with true <- enabled?(),
         {:ok, ^target} <- Target.new(target),
         true <- ArtifactV3Policy.uint?(sequence) and sequence > 0,
         true <- ArtifactV3Policy.digest?(digest) do
      fields = Map.new(Target.filter(target))
      params = Enum.map(@target, &Map.fetch!(fields, &1))
      params = params ++ [Decimal.new(sequence), digest]

      result =
        Authorization.with_authorized_transaction(
          identity,
          @action,
          target.scope,
          fn context ->
            access_locked(context, target, sequence, digest, params, operation)
          end,
          WriterRepo
        )

      case result do
        {:error, :assignment_rejected} -> {:error, :not_found}
        other -> other
      end
    else
      _ -> {:error, :not_found}
    end
  end

  defp access_locked(context, target, sequence, digest, params, operation) do
    fresh = owner_checkpoint(context, target)

    with {:ok, hash} <-
           Releases.published_source_map_digest(
             WriterRepo,
             target,
             sequence,
             digest,
             fresh.checked_at
           ),
         :ok <- private_query_settings(),
         {:ok, result, retain_until} <- operation.(params, hash, fresh),
         final = owner_checkpoint(context, target),
         {:ok, ^hash} <-
           Releases.published_source_map_digest(
             WriterRepo,
             target,
             sequence,
             digest,
             final.checked_at
           ),
         true <- enabled?() do
      valid_until = expiry(final, retain_until)
      {:ok, {result, valid_until}, {:valid_during, 0, valid_until}}
    else
      {:error, _} = error -> error
      _ -> {:error, :not_found}
    end
  end

  defp owner_checkpoint(context, target) do
    fresh = Context.checkpoint!(context, WriterRepo, @action, target.scope)

    if Enum.any?(fresh.memberships, &(&1.role == "owner")),
      do: fresh,
      else: WriterRepo.rollback(:permission_denied)
  end

  defp expiry(fresh, retain_until) do
    # Any eligible owner grant authorizes the operation. A grant without an
    # expiry leaves the retention deadline as the only additional time fence.
    owner_expiry =
      fresh.memberships
      |> Enum.filter(&(&1.role == "owner"))
      |> Enum.map(&(&1.expires_at || retain_until))
      |> Enum.max()

    [
      retain_until,
      owner_expiry,
      fresh.identity.expires_at,
      fresh.credential.expires_at || retain_until,
      fresh.family.expires_at || retain_until
    ]
    |> Enum.min()
  end

  defp private_query_settings do
    case query!(
           """
           SELECT current_setting('log_parameter_max_length'),
                  current_setting('log_parameter_max_length_on_error'),
                  current_setting('log_error_verbosity')
           """,
           []
         ).rows do
      [["0", "0", "terse"]] -> :ok
      _ -> {:error, :storage_unavailable}
    end
  end

  defp query!(sql, params) do
    Ecto.Adapters.SQL.query!(WriterRepo, sql, params,
      log: false,
      telemetry_event: nil,
      timeout: 5_000,
      queue: false
    )
  end

  defp sha256(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
end
