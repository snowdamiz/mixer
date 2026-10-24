defmodule MixerHosted.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    role = Application.fetch_env!(:mixer_hosted, :role)
    children = children(role, Application.fetch_env!(:mixer_hosted, Oban))
    Supervisor.start_link(children, strategy: :one_for_one, name: MixerHosted.Supervisor)
  end

  @doc false
  def children(:api, oban), do: [MixerHosted.Repo, {Oban, oban}, MixerHostedWeb.Endpoint]
  def children(:processor, oban), do: [MixerHosted.Repo, {Oban, oban}]

  @impl true
  def config_change(changed, _new, removed) do
    if Application.fetch_env!(:mixer_hosted, :role) == :api do
      MixerHostedWeb.Endpoint.config_change(changed, removed)
    end

    :ok
  end
end
