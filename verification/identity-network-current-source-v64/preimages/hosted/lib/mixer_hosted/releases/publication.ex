defmodule MixerHosted.Releases.Publication do
  @moduledoc false
  use Ecto.Schema

  @primary_key false
  @schema_prefix "public"
  schema "mixer_release_publications" do
    field(:organization_id, :string, primary_key: true)
    field(:project_id, :string, primary_key: true)
    field(:application_id, :string, primary_key: true)
    field(:environment_id, :string, primary_key: true)
    field(:platform, :string, primary_key: true)
    field(:runtime_sha256, :string, primary_key: true)
    field(:channel, :string, primary_key: true)
    field(:sequence, :decimal, primary_key: true)
    field(:previous_sequence, :decimal)
    field(:action, :string)
    field(:artifact_sha256, :string)
    field(:signed_assignment_bytes, :binary)
    field(:rollout_basis_points, :integer)
    field(:idempotency_key, :string)
    field(:reason, :string)
    field(:principal_id, :string)
    field(:recorded_at, :utc_datetime_usec, read_after_writes: true)
  end
end
