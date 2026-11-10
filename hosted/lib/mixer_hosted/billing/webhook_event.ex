defmodule MixerHosted.Billing.WebhookEvent do
  @moduledoc false
  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: false}
  schema "mixer_billing_webhook_inbox" do
    field(:endpoint_id, :string)
    field(:account, :string)
    field(:livemode, :boolean)
    field(:event_id, :string)
    field(:event_type, :string)
    field(:event_created, :integer)
    field(:object_id, :string)
    field(:body_sha256, :binary)
    timestamps(type: :utc_datetime_usec, updated_at: false)
  end
end
