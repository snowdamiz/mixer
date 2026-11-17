defmodule MixerHosted.Billing.ProcessorProfile do
  @moduledoc "Explicit billing-only execution profile; provisioning is deployment owned."
  def role, do: "mixer_billing_processor"

  def oban(concurrency) when is_integer(concurrency) and concurrency in 1..8 do
    [
      name: Oban,
      repo: MixerHosted.Repo,
      engine: Oban.Engines.Basic,
      insert_trigger: true,
      notifier: Oban.Notifiers.Postgres,
      queues: [billing_reconciliation: concurrency],
      plugins: [],
      peer: Oban.Peers.Database,
      stager: [interval: 1_000],
      shutdown_grace_period: 15_000
    ]
  end
end
