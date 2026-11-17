defmodule MixerHosted.Application do
  @moduledoc false
  use Application
  @behaviour Supervisor
  alias MixerHosted.BrowserAuth.Installation
  alias MixerHosted.Identity.StartupConfig
  alias MixerHosted.RuntimeConfig
  @boot Module.concat(__MODULE__, Boot)

  @impl true
  def start(_type, _args) do
    startup = Application.fetch_env!(:mixer_hosted, :startup)

    unless projections_match?(startup),
      do: raise(ArgumentError, "hosted startup requires restart")

    Supervisor.start_link(__MODULE__, startup, name: MixerHosted.Supervisor)
  end

  @impl true
  def init(startup) do
    children = children(startup)
    :ets.new(@boot, [:named_table, :protected, :set])
    :ets.insert(@boot, {:startup, startup})

    strategy =
      case startup do
        {%RuntimeConfig{role: :processor}, :disabled} -> :rest_for_one
        _ -> :one_for_one
      end

    Supervisor.init(children, strategy: strategy)
  end

  @doc false
  @spec children({%RuntimeConfig{}, Installation.t()}) :: [
          Supervisor.child_spec() | module() | tuple()
        ]
  def children({%RuntimeConfig{} = hosted, installation}) do
    unless Installation.valid?(installation, hosted),
      do: raise(ArgumentError, "browser installation unavailable: configuration")

    create_children =
      if is_list(hosted.create_repo),
        do: [{MixerHosted.CustomerBuilds.CreateRepo, hosted.create_repo}],
        else: []

    base = [MixerHosted.Repo] ++ create_children ++ [{Oban, hosted.oban}]

    case {hosted.role, hosted.identity_startup} do
      {:processor, %StartupConfig{mode: :disabled}} when installation == :disabled ->
        true = hosted.processor_profile == :builds_v1
        true = hosted.create_repo == nil
        true = hosted.repo[:username] == MixerHosted.Builds.ProcessorProfile.role()

        true =
          hosted.repo[:after_connect] ==
            {MixerHosted.Builds.ProcessorAdmission, :after_connect, []}

        true = Keyword.keys(hosted.oban[:queues]) == [:builds]
        true = hosted.oban[:engine] == Oban.Engines.Basic
        true = hosted.oban[:name] == Oban

        true =
          hosted.oban ==
            MixerHosted.Builds.ProcessorProfile.oban(
              Keyword.fetch!(hosted.oban[:queues], :builds)
            )

        [
          MixerHosted.Repo,
          {MixerHosted.Builds.ProcessorAdmission, :builds_v1},
          {Oban, hosted.oban}
        ]

      {:api, %StartupConfig{} = identity} ->
        identity_children =
          case identity do
            %StartupConfig{mode: :disabled} ->
              []

            %StartupConfig{mode: :configured, owner_options: options} ->
              [Installation.identity_child(installation, options)]
          end

        browser_children =
          if installation == :disabled,
            do: [],
            else: [{MixerHosted.BrowserAuth.Supervisor, installation}]

        base ++ identity_children ++ browser_children ++ [MixerHostedWeb.Endpoint]

      _ ->
        raise ArgumentError, "hosted startup unavailable"
    end
  end

  def children(_), do: raise(ArgumentError, "hosted startup unavailable")

  @doc false
  @spec startup() :: {:ok, {%RuntimeConfig{}, Installation.t()}} | :error
  def startup do
    with owner when is_pid(owner) <- Process.whereis(MixerHosted.Supervisor),
         true <- :ets.info(@boot, :owner) === owner,
         [{:startup, startup}] <- :ets.lookup(@boot, :startup),
         true <- Application.get_env(:mixer_hosted, :startup) === startup,
         true <- projections_match?(startup) do
      {:ok, startup}
    else
      _ -> :error
    end
  rescue
    _ -> :error
  end

  defp projections_match?({%RuntimeConfig{} = hosted, _}) do
    Application.fetch_env(:mixer_hosted, :role) === {:ok, hosted.role} and
      Application.fetch_env(:mixer_hosted, :identity_startup) === {:ok, hosted.identity_startup} and
      Application.fetch_env(:mixer_hosted, MixerHosted.Repo) === {:ok, hosted.repo} and
      Application.fetch_env(:mixer_hosted, Oban) === {:ok, hosted.oban} and
      Enum.all?(hosted.endpoint, fn {key, value} ->
        Application.get_env(:mixer_hosted, MixerHostedWeb.Endpoint, [])[key] === value
      end)
  end

  defp projections_match?(_), do: false

  @impl true
  def config_change(changed, new, removed) do
    restart_keys = [
      :startup,
      :role,
      :identity_startup,
      MixerHosted.Repo,
      Oban,
      MixerHostedWeb.Endpoint
    ]

    if Enum.any?(Keyword.keys(changed) ++ Keyword.keys(new) ++ removed, &(&1 in restart_keys)) do
      {:error, :restart_required}
    else
      case startup() do
        {:ok, {%RuntimeConfig{role: :api}, _}} ->
          MixerHostedWeb.Endpoint.config_change(changed, removed)
          :ok

        {:ok, _} ->
          :ok

        :error ->
          {:error, :restart_required}
      end
    end
  end
end
