defmodule MixerHosted.Identity.KeyOwnerSupervisor do
  @moduledoc "Explicitly configured private identity component; it starts no provider implicitly."
  use Supervisor
  alias MixerHosted.Identity.KeyOwner
  def start_link(options), do: Supervisor.start_link(__MODULE__, options)

  if Mix.env() == :test do
    def start_fixture(options), do: Supervisor.start_link(__MODULE__, {:fixture, options})
    def init({:fixture, options}), do: initialize(options, :start_fixture)
  end

  def init(options), do: initialize(options, :start_link)

  defp initialize(options, owner_start) do
    name = Keyword.get(options, :name, KeyOwner)
    workers = Module.concat(name, FetchSupervisor)
    owner_options = Keyword.put(options, :worker_supervisor, workers)
    owner = KeyOwner.child_spec(owner_options)
    owner = %{owner | start: {KeyOwner, owner_start, [owner_options]}}

    children = [
      {DynamicSupervisor, strategy: :one_for_one, name: workers},
      owner
    ]

    Supervisor.init(children, strategy: :one_for_all, max_restarts: 3, max_seconds: 5)
  end
end
