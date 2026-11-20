defmodule MixerHosted.Releases.Head do
  @moduledoc false
  use Ecto.Schema

  @primary_key false
  @schema_prefix "public"
  schema "mixer_release_heads" do
    field(:organization_id, :string, primary_key: true)
    field(:project_id, :string, primary_key: true)
    field(:application_id, :string, primary_key: true)
    field(:environment_id, :string, primary_key: true)
    field(:platform, :string, primary_key: true)
    field(:runtime_sha256, :string, primary_key: true)
    field(:channel, :string, primary_key: true)
    field(:sequence, :decimal)
  end
end
