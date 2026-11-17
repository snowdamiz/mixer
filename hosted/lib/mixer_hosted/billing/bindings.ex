defmodule MixerHosted.Billing.Bindings do
  @moduledoc false
  alias MixerHosted.Repo

  defmodule Target do
    @moduledoc false
    @enforce_keys [
      :inbox_id,
      :endpoint_id,
      :account,
      :livemode,
      :credential_id,
      :secret_ref,
      :organization_id,
      :customer_id,
      :subscription_id,
      :binding_id,
      :versions
    ]
    defstruct @enforce_keys
    @type t :: %__MODULE__{}
  end

  @spec resolve(binary()) :: {:ok, Target.t()} | {:error, :relationship_unavailable}
  def resolve(id) do
    sql = """
    SELECT i.id::text, e.id, c.account, c.livemode, c.id::text, c.secret_ref,
      b.organization_id, b.customer_id, l.subscription_id, b.id::text,
      ARRAY[e.revision::text,c.revision::text,b.revision::text,l.revision::text,
            e.xmin::text,c.xmin::text,b.xmin::text,l.xmin::text,o.xmin::text || ':' || o.revision::text],
      i.body_sha256
    FROM mixer_billing_webhook_inbox i
    JOIN mixer_billing_endpoints e ON e.id=i.endpoint_id
      AND e.event_account IS NOT DISTINCT FROM i.account AND e.livemode=i.livemode
    JOIN mixer_billing_credentials c ON c.id=e.credential_id AND c.livemode=e.livemode
    JOIN mixer_billing_customer_bindings b ON b.endpoint_id=e.id
    JOIN mixer_billing_organization_state o ON o.organization_id=b.organization_id
    JOIN mixer_billing_resource_links l ON l.binding_id=b.id AND l.object_id=i.object_id
      AND l.kind=CASE WHEN i.event_type LIKE 'customer.subscription.%' THEN 'subscription'
                      WHEN i.event_type LIKE 'invoice.%' THEN 'invoice'
                      WHEN i.event_type LIKE 'checkout.session.%' THEN 'checkout.session' END
    WHERE i.id=$1::text::uuid AND e.active AND c.active AND b.active AND l.active AND o.active
      AND c.attestation IS NOT NULL
      AND (e.event_account IS NULL OR e.event_account=c.account)
    FOR SHARE OF e,c,b,l,o
    """

    case Repo.query!(sql, [id]).rows do
      [
        [
          inbox,
          endpoint,
          account,
          mode,
          credential,
          secret,
          org,
          customer,
          sub,
          binding,
          versions,
          digest
        ]
      ] ->
        {:ok,
         %Target{
           inbox_id: inbox,
           endpoint_id: endpoint,
           account: account,
           livemode: mode,
           credential_id: credential,
           secret_ref: secret,
           organization_id: org,
           customer_id: customer,
           subscription_id: sub,
           binding_id: binding,
           versions: versions ++ [Base.encode16(digest)]
         }}

      _ ->
        {:error, :relationship_unavailable}
    end
  end
end
