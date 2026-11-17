defmodule MixerHosted.Billing.Reconciliation do
  @moduledoc false
  alias MixerHosted.Repo
  alias MixerHosted.Billing.{Bindings, ProviderRead, Entitlements}

  defmodule Claim do
    @moduledoc false
    @enforce_keys [:target, :token, :fence]
    defstruct @enforce_keys
    @type t :: %__MODULE__{}
  end

  @spec run(binary()) :: {:ok, atom()} | {:retry, atom()} | {:refuse, atom()}
  def run(id) do
    if activated?() and not Repo.in_transaction?() do
      case claim(id) do
        {:ok, %Claim{} = claim} ->
          case ProviderRead.fetch(claim.target) do
            {:ok, observation} -> commit(claim, observation)
            {:error, _} -> fail(claim)
          end

        result ->
          result
      end
    else
      {:retry, :processor_disabled}
    end
  rescue
    _ in [Postgrex.Error, DBConnection.ConnectionError] -> {:retry, :storage_unavailable}
  end

  defp activated? do
    match?(
      %{enabled: true, profile: :billing_v1},
      Application.get_env(:mixer_hosted, :billing_processor)
    )
  end

  defp claim(id) do
    transaction(fn ->
      case Repo.query!(
             "SELECT id FROM mixer_billing_webhook_inbox WHERE id=$1::text::uuid FOR UPDATE",
             [id]
           ).rows do
        [] -> {:refuse, :missing_inbox}
        [_] -> claim_existing(id)
      end
    end)
  end

  defp claim_existing(id) do
    Repo.query!(
      "INSERT INTO mixer_billing_reconciliations(inbox_id,state) VALUES($1::text::uuid,'pending') ON CONFLICT DO NOTHING",
      [id]
    )

    [[state]] =
      Repo.query!(
        "SELECT state FROM mixer_billing_reconciliations WHERE inbox_id=$1::text::uuid FOR UPDATE",
        [id]
      ).rows

    if state in ["blocked", "refused"] do
      {:ok, :already_recorded}
    else
      case Bindings.resolve(id) do
        {:ok, target} ->
          acquire(target)

        {:error, reason} ->
          Repo.query!(
            "UPDATE mixer_billing_reconciliations SET state='blocked',reason=$2 WHERE inbox_id=$1::text::uuid",
            [id, Atom.to_string(reason)]
          )

          {:ok, :blocked}
      end
    end
  end

  defp acquire(target) do
    Repo.query!(
      "INSERT INTO mixer_billing_subscription_claims(binding_id,subscription_id) VALUES($1::text::uuid,$2) ON CONFLICT DO NOTHING",
      [target.binding_id, target.subscription_id]
    )

    token = Ecto.UUID.generate()

    sql = """
    UPDATE mixer_billing_subscription_claims SET inbox_id=$3::text::uuid, token=$4::text::uuid,
      fence=fence+1, deadline=clock_timestamp()+interval '30 seconds'
    WHERE binding_id=$1::text::uuid AND subscription_id=$2
      AND (deadline IS NULL OR deadline<=clock_timestamp()) RETURNING fence
    """

    case Repo.query!(sql, [target.binding_id, target.subscription_id, target.inbox_id, token]).rows do
      [[fence]] ->
        Repo.query!(
          "UPDATE mixer_billing_reconciliations SET state='claimed',reason=NULL,token=$2::text::uuid,fence=$3 WHERE inbox_id=$1::text::uuid",
          [target.inbox_id, token, fence]
        )

        {:ok, %Claim{target: target, token: token, fence: fence}}

      [] ->
        {:retry, :claimed}
    end
  end

  defp locked?(%Claim{target: t, token: token, fence: fence}) do
    # Lock order matches T1: inbox, reconciliation, subscription, bindings.
    Repo.query!("SELECT id FROM mixer_billing_webhook_inbox WHERE id=$1::text::uuid FOR UPDATE", [
      t.inbox_id
    ])

    result =
      Repo.query!(
        "SELECT token::text,fence FROM mixer_billing_reconciliations WHERE inbox_id=$1::text::uuid FOR UPDATE",
        [t.inbox_id]
      ).rows

    lease =
      Repo.query!(
        "SELECT token::text,fence,inbox_id::text,deadline>clock_timestamp() FROM mixer_billing_subscription_claims WHERE binding_id=$1::text::uuid AND subscription_id=$2 FOR UPDATE",
        [t.binding_id, t.subscription_id]
      ).rows

    result == [[token, fence]] and lease == [[token, fence, t.inbox_id, true]]
  end

  defp commit(
         %Claim{target: target} = claim,
         %ProviderRead.Observation{target: target} = observation
       ) do
    transaction(fn ->
      with true <- activated?() and locked?(claim),
           {:ok, ^target} <- Bindings.resolve(target.inbox_id),
           true <-
             observation.value.subscription_id == target.subscription_id and
               observation.value.customer_id == target.customer_id and
               observation.value.livemode == target.livemode,
           {:blocked, :ordering_unavailable} <- Entitlements.decide(observation.value) do
        sql = """
        INSERT INTO mixer_billing_observations(inbox_id,binding_id,subscription_id,fence,
          organization_id,account,livemode,customer_id,status,response_sha256,provenance)
        VALUES($1::text::uuid,$2::text::uuid,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """

        Repo.query!(sql, [
          target.inbox_id,
          target.binding_id,
          target.subscription_id,
          claim.fence,
          target.organization_id,
          target.account,
          target.livemode,
          target.customer_id,
          observation.value.status,
          observation.response_sha256,
          %{
            endpoint_id: target.endpoint_id,
            credential_id: target.credential_id,
            versions: target.versions,
            origin: "https://api.stripe.com",
            api_version: "2026-10-28.endive",
            ordering: "ordering_unavailable",
            owning_account_proof: "trusted_provisioning_attestation"
          }
        ])

        Repo.query!(
          "UPDATE mixer_billing_reconciliations SET state='blocked',reason='ordering_unavailable' WHERE inbox_id=$1::text::uuid",
          [target.inbox_id]
        )

        release(claim)
        {:ok, :blocked}
      else
        _ -> Repo.rollback(:stale_or_revoked)
      end
    end)
  end

  defp fail(claim) do
    transaction(fn ->
      if locked?(claim) do
        Repo.query!(
          "UPDATE mixer_billing_reconciliations SET state='retry',reason='provider_unavailable' WHERE inbox_id=$1::text::uuid",
          [claim.target.inbox_id]
        )

        release(claim)
      end

      {:retry, :provider_unavailable}
    end)
  end

  defp release(%Claim{target: t}) do
    Repo.query!(
      "UPDATE mixer_billing_subscription_claims SET deadline=NULL,token=NULL WHERE binding_id=$1::text::uuid AND subscription_id=$2",
      [t.binding_id, t.subscription_id]
    )
  end

  defp transaction(fun) do
    case Repo.transaction(fun, timeout: 2_000) do
      {:ok, result} -> result
      {:error, reason} -> {:retry, reason}
    end
  end
end
