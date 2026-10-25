defmodule MixerHosted.Test.BuildIntentWorker do
  @moduledoc false
  use Oban.Worker, queue: :builds, max_attempts: 1

  # Test-only, no external effect or authority. Production has no build consumer.
  @impl true
  def perform(%Oban.Job{args: args}) do
    MixerHosted.Repo.query!(
      "INSERT INTO build_intent_probe (build_record_id, revision) VALUES ($1::uuid, $2)",
      [Ecto.UUID.dump!(args["build_record_id"]), args["revision"]]
    )

    :ok
  end
end
