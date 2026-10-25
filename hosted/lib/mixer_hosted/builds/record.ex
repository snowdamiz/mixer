defmodule MixerHosted.Builds.Record do
  @moduledoc false
  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: true}
  schema "mixer_builds" do
    field(:organization_id, :string)
    field(:project_id, :string)
    field(:application_id, :string)
    field(:build_id, :string)
    field(:platform, :string)
    field(:request_key, :string)
    field(:revision, :integer)
    field(:journal, :map)
    timestamps(type: :utc_datetime_usec)
  end
end
