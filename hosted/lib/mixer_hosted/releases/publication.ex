defmodule MixerHosted.Releases.Publication do
  @moduledoc false
  use Ecto.Schema
  alias MixerHosted.Releases.Target

  @health_fields [
    health_activated: "activated",
    health_pending: "pending",
    health_adverse_signals: "adverse_signals"
  ]

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
    field(:health_activated, :decimal, load_in_query: false)
    field(:health_pending, :decimal, load_in_query: false)
    field(:health_adverse_signals, :decimal, load_in_query: false)
  end

  def health_fields, do: @health_fields

  def health(stored) do
    Map.new(@health_fields, fn {field, key} ->
      {key, Decimal.to_integer(Map.fetch!(stored, field))}
    end)
    |> Map.put("sequence", Decimal.to_integer(stored.previous_sequence))
  end

  def halt_sample(stored, target) do
    %{
      scope: Target.signed_scope(target),
      runtime: target.runtime_sha256,
      channel: target.channel,
      artifact_sha256: stored.artifact_sha256,
      halt_sequence: Decimal.to_integer(stored.sequence),
      health: health(stored)
    }
  end
end
