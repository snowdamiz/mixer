defmodule MixerHosted.Releases.RolloutHaltAudit do
  @moduledoc false

  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Protocol.ArtifactV3Policy
  alias MixerHosted.Repo
  alias MixerHosted.Releases.{Publication, Target}

  @maximum 18_446_744_073_709_551_615

  def configured_target do
    with {:ok, %{target: target, host: host}} <-
           Application.fetch_env(:mixer_hosted, :local_release_target),
         {:ok, ^target} <- Target.new(target),
         true <- ArtifactV3Policy.host?(host) and host["scope"] == Target.signed_scope(target),
         true <- host["runtime"] == target.runtime_sha256 do
      {:ok, target}
    else
      _ -> {:error, :not_found}
    end
  end

  def read(identity, project, target, after_sequence, limit)
      when is_integer(after_sequence) and after_sequence in 0..@maximum and
             is_integer(limit) and limit in 1..100 do
    Authorization.with_authorized_transaction(
      identity,
      "audit.read",
      project,
      fn context ->
        Context.effect!(context, Repo, "audit.read", project, fn _ ->
          with {:ok, ^target} <- configured_target(),
               page = page(target, after_sequence, limit),
               {:ok, ^target} <- configured_target() do
            {:ok, page}
          else
            _ -> {:error, :not_found}
          end
        end)
      end
    )
  end

  def read(_, _, _, _, _), do: {:error, :invalid_request}

  defp page(target, after_sequence, limit) do
    scope = target.scope

    rows =
      Session.query!(
        Repo,
        """
        SELECT sequence,previous_sequence,artifact_sha256,health_activated,
               health_pending,health_adverse_signals
        FROM public.mixer_release_audit_halts($1,$2,$3,$4,$5,$6,$7,$8,$9)
        ORDER BY sequence
        """,
        [
          scope.organization_id,
          scope.project_id,
          scope.application_id,
          scope.environment_id,
          target.platform,
          target.runtime_sha256,
          target.channel,
          Decimal.new(after_sequence),
          limit
        ]
      ).rows

    events =
      Enum.map(rows, fn [sequence, previous, digest, activated, pending, adverse] ->
        sample =
          Publication.halt_sample(
            %{
              sequence: sequence,
              previous_sequence: previous,
              artifact_sha256: digest,
              health_activated: activated,
              health_pending: pending,
              health_adverse_signals: adverse
            },
            target
          )

        %{
          id: sample.halt_sequence,
          action:
            "POST /v3/orgs/#{scope.organization_id}/projects/#{scope.project_id}/channels/#{target.channel}/halt",
          rollout_halt: sample
        }
      end)

    %{
      events: events,
      next_after_sequence: if(events == [], do: after_sequence, else: List.last(events).id)
    }
  end
end
