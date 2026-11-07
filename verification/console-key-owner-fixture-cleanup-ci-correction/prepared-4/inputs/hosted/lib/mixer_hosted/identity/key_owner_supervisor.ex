defmodule MixerHosted.Identity.KeyOwnerSupervisor do
  @moduledoc "Explicitly configured private identity component; it starts no provider implicitly."
  use Supervisor
  alias MixerHosted.Identity.KeyOwner
  def start_link(options), do: Supervisor.start_link(__MODULE__, options)

  def init(options) do
    name = Keyword.get(options, :name, KeyOwner)
    workers = Module.concat(name, FetchSupervisor)

    children = [
      {DynamicSupervisor, strategy: :one_for_one, name: workers},
      {KeyOwner, Keyword.put(options, :worker_supervisor, workers)}
    ]

    Supervisor.init(children, strategy: :one_for_all, max_restarts: 3, max_seconds: 5)
  end
end
