defmodule MixerHosted.Billing.ReconciliationWorker do
  @moduledoc "First-party billing reconciler. Explicit deployment selection is required."
  use Oban.Worker, queue: :billing_reconciliation, max_attempts: 8
  alias MixerHosted.Billing.Reconciliation

  @impl Oban.Worker
  def perform(%Oban.Job{args: %{"inbox_id" => id} = args}) when map_size(args) == 1 do
    case Ecto.UUID.cast(id) do
      {:ok, ^id} ->
        case Reconciliation.run(id) do
          {:ok, _} -> :ok
          {:retry, :claimed} -> {:snooze, 5}
          {:retry, reason} -> {:error, reason}
          {:refuse, reason} -> {:cancel, reason}
        end

      _ ->
        {:cancel, :invalid_args}
    end
  end

  def perform(%Oban.Job{}), do: {:cancel, :invalid_args}
end
