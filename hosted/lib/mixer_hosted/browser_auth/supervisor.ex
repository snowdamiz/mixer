defmodule MixerHosted.BrowserAuth.Supervisor do
  @moduledoc "One fail-stop browser lifetime. Recovery requires whole-application restart."
  use Supervisor

  def child_spec(installation) do
    %{
      id: __MODULE__,
      start: {__MODULE__, :start_link, [installation]},
      type: :supervisor,
      restart: :temporary
    }
  end

  def start_link(installation), do: Supervisor.start_link(__MODULE__, installation)

  @impl true
  def init(installation) do
    case children(installation) do
      {:ok, children} -> Supervisor.init(children, strategy: :one_for_all, max_restarts: 0)
      :error -> {:stop, :browser_installation_unavailable}
    end
  end

  alias MixerHosted.BrowserAuth.{Installation, LifecycleRepo, ProviderOwner, RuntimeOwner}

  defp children(%Installation{provider: {:configured, _, _}} = installation) do
    if Installation.valid?(installation, installation.hosted) do
      {:ok,
       [
         %{
           id: LifecycleRepo,
           start: {Installation, :start_lifecycle_repo, [installation]},
           restart: :permanent,
           type: :supervisor,
           shutdown: :infinity
         },
         %{
           id: MixerHosted.BrowserAuth.ProviderTrustOwner,
           start:
             {MixerHosted.Identity.KeyOwnerSupervisor, :start_link,
              [installation.trust.owner_options]},
           type: :supervisor,
           shutdown: :infinity
         },
         %{
           id: ProviderOwner,
           start: {Installation, :start_provider, [installation]},
           restart: :permanent
         },
         Supervisor.child_spec({RuntimeOwner, installation.runtime}, restart: :permanent)
       ]}
    else
      :error
    end
  end

  if Mix.env() == :test do
    defp children(%Installation{
           runtime: runtime,
           provider: {:fixture, config, snapshot, transport}
         }) do
      provider = %{
        id: ProviderOwner,
        start: {ProviderOwner, :start_fixture, [config, snapshot, transport]},
        restart: :permanent
      }

      {:ok,
       [
         Supervisor.child_spec({LifecycleRepo, runtime.lifecycle_repo}, restart: :permanent),
         provider,
         Supervisor.child_spec({RuntimeOwner, runtime}, restart: :permanent)
       ]}
    end
  end

  defp children(_), do: :error
end
