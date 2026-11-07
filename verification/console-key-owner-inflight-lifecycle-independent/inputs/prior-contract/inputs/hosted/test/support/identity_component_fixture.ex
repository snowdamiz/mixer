defmodule MixerHosted.Identity.ComponentFixture do
  @moduledoc false
  use Supervisor
  def start_link(options), do: Supervisor.start_link(__MODULE__, options)

  def init(options) do
    workers = Keyword.fetch!(options, :worker_supervisor)

    child = %{
      id: :fixture_owner,
      start: {MixerHosted.Identity.KeyOwner, :start_fixture, [options]},
      shutdown: :infinity
    }

    Supervisor.init([{DynamicSupervisor, strategy: :one_for_one, name: workers}, child],
      strategy: :one_for_all
    )
  end
end
