defmodule MixerHosted.Releases.CLIRequest do
  @moduledoc false
  use Ecto.Schema

  @primary_key false
  @schema_prefix "public"
  schema "mixer_release_cli_requests" do
    field(:organization_id, :string)
    field(:project_id, :string)
    field(:application_id, :string)
    field(:environment_id, :string)
    field(:platform, :string)
    field(:runtime_sha256, :string)
    field(:channel, :string)
    field(:idempotency_key, :string)
    field(:request_sha256, :string)
    field(:principal_id, :string)
    field(:artifact_sha256, :string)
    field(:publication_sequence, :decimal)
  end
end
