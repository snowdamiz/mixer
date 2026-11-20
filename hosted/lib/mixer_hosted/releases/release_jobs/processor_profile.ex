defmodule MixerHosted.Releases.ReleaseJobs.ProcessorProfile do
  @moduledoc false

  def role, do: "mixer_release_processor"
  def prefix, do: "mixer_release_jobs"

  def oban(concurrency) when is_integer(concurrency) and concurrency in 1..8 do
    [
      name: Oban,
      repo: MixerHosted.Repo,
      engine: Oban.Engines.Basic,
      prefix: prefix(),
      insert_trigger: false,
      notifier: Oban.Notifiers.Isolated,
      queues: [releases: concurrency],
      plugins: [],
      peer: Oban.Peers.Database,
      stager: [interval: 1_000],
      shutdown_grace_period: 15_000
    ]
  end
end
