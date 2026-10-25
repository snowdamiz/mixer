defmodule MixerHosted.Application do
  @moduledoc false
  use Application
  alias MixerHosted.Builds.{WorkerConfig, WorkerTransport}
  alias MixerHosted.Identity.{KeyOwnerSupervisor, StartupConfig}

  @impl true
  def start(_type, _args) do
    role = Application.fetch_env!(:mixer_hosted, :role)

    children =
      children(
        role,
        Application.fetch_env!(:mixer_hosted, Oban),
        Application.fetch_env!(:mixer_hosted, :identity_startup),
        Application.fetch_env!(:mixer_hosted, :build_worker_startup)
      )

    Supervisor.start_link(children, strategy: :one_for_one, name: MixerHosted.Supervisor)
  end

  @doc false
  def children(role, oban),
    do: children(role, oban, %StartupConfig{mode: :disabled, owner_options: []})

  @doc false
  def children(role, oban, identity), do: children(role, oban, identity, %WorkerConfig{})

  @doc false
  def children(:api, oban, %StartupConfig{mode: :disabled}, worker)
      when worker == %WorkerConfig{},
      do: [MixerHosted.Repo, {Oban, oban}, MixerHostedWeb.Endpoint]

  def children(:api, oban, %StartupConfig{mode: :configured, owner_options: options}, worker)
      when worker == %WorkerConfig{},
      do: [MixerHosted.Repo, {Oban, oban}, {KeyOwnerSupervisor, options}, MixerHostedWeb.Endpoint]

  def children(:processor, oban, %StartupConfig{mode: :disabled}, worker)
      when worker == %WorkerConfig{},
      do: [MixerHosted.Repo, {Oban, oban}]

  def children(:processor, oban, %StartupConfig{mode: :disabled}, %WorkerConfig{} = worker) do
    if WorkerConfig.validated?(worker) do
      # Queues start only after the transport; reverse shutdown drains queues first.
      # Preserve the transport's temporary child specification and VM quarantine.
      [MixerHosted.Repo, {WorkerTransport, worker}, {Oban, oban}]
    else
      raise ArgumentError, "invalid worker startup configuration"
    end
  end

  def children(_, _, _, _),
    do: raise(ArgumentError, "invalid hosted startup role configuration")

  @impl true
  def config_change(changed, _new, removed) do
    if Application.fetch_env!(:mixer_hosted, :role) == :api do
      MixerHostedWeb.Endpoint.config_change(changed, removed)
    end

    :ok
  end
end
