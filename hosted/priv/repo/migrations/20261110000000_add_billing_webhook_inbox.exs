defmodule MixerHosted.Repo.Migrations.AddBillingWebhookInbox do
  use Ecto.Migration

  def change do
    create table(:mixer_billing_webhook_inbox, primary_key: false) do
      add(:id, :uuid, primary_key: true)
      add(:endpoint_id, :text, null: false)
      add(:account, :text)
      add(:livemode, :boolean, null: false)
      add(:event_id, :text, null: false)
      add(:event_type, :text, null: false)
      add(:event_created, :bigint, null: false)
      add(:object_id, :text, null: false)
      add(:body_sha256, :binary, null: false)
      timestamps(type: :utc_datetime_usec, updated_at: false)
    end

    create(unique_index(:mixer_billing_webhook_inbox, [:endpoint_id, :event_id]))
  end
end
