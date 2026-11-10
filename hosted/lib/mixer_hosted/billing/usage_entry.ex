defmodule MixerHosted.Billing.UsageEntry do
  @moduledoc false
  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: false}
  schema "mixer_billing_usage_entries" do
    field(:tenant_id, :string)
    field(:metric, :string)
    field(:platform, :string)
    field(:period_start, :integer)
    field(:period_end, :integer)
    field(:source, :string)
    field(:source_key, :string)
    field(:units, :integer)
    field(:correction_of, :binary_id)
    timestamps(type: :utc_datetime_usec, updated_at: false)
  end

  @type t :: %__MODULE__{}
end
