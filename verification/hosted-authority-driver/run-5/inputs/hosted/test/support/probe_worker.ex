defmodule MixerHosted.Test.ProbeWorker do
  @moduledoc false
  use Oban.Worker, queue: :releases, max_attempts: 1

  @impl true
  def perform(%Oban.Job{args: %{"probe" => probe}}) do
    MixerHosted.Repo.query!(
      "INSERT INTO foundation_probe (id, effect) VALUES ($1, true) ON CONFLICT (id) DO UPDATE SET effect = true",
      [probe]
    )

    :ok
  end
end
