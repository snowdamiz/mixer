defmodule MixerHosted.BrowserAuth.Installation do
  @moduledoc "Restart-only browser installation. Configured production is not yet ready."
  alias MixerHosted.BrowserAuth.Config
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  @derive {Inspect, only: []}
  @enforce_keys [:runtime, :provider]
  defstruct @enforce_keys
  @opaque t :: :disabled | %__MODULE__{}

  @spec load!(map(), %HostedConfig{}) :: t()
  def load!(env, %HostedConfig{} = hosted) when is_map(env) do
    browser = Map.take(env, ~w(MIXER_BROWSER_AUTH_MODE MIXER_BROWSER_AUTH_CONFIG))

    case Config.load(browser, hosted.role, hosted.identity_startup) do
      {:ok, %Config{mode: :disabled}} -> :disabled
      {:ok, %Config{mode: :configured}} ->
        raise ArgumentError, "browser installation unavailable: production readiness"
      _ -> raise ArgumentError, "browser installation unavailable: configuration"
    end
  end

  def load!(_, _), do: raise(ArgumentError, "browser installation unavailable: configuration")

  if Mix.env() == :test do
    alias MixerHosted.BrowserAuth.RuntimeConfig
    @doc false
    @spec fixture!(RuntimeConfig.t(), %Config{}, MixerHosted.Identity.TrustSnapshot.t(), pid()) :: t()
    def fixture!(%RuntimeConfig{mode: :configured, admission_profile: :build_catalog_v3} = runtime,
          %Config{mode: :configured} = config,
          %MixerHosted.Identity.TrustSnapshot{} = snapshot, transport) when is_pid(transport) do
      {:ok, digest} = MixerHosted.BrowserAuth.ConfigurationDigest.digest(config)
      true = runtime.browser_config === config and runtime.configuration_digest === digest
      true = snapshot.profile.profile_id === config.profile_id
      true = snapshot.profile.issuer === config.issuer
      true = snapshot.profile.client_id === config.client_id
      true = snapshot.profile.audience === config.api_audience
      %__MODULE__{runtime: runtime, provider: {:fixture, config, snapshot, transport}}
    end
  end

  def valid?(:disabled, %HostedConfig{}), do: true

  if Mix.env() == :test do
    def valid?(%__MODULE__{runtime: runtime, provider: {:fixture, config, _, transport}},
          %HostedConfig{role: :api, identity_startup: identity, repo: repo}) do
      is_pid(transport) and runtime.mode === :configured and
        runtime.admission_profile === :build_catalog_v3 and runtime.browser_config === config and
        identity.mode === :configured and
        runtime.expected_roles.ordinary_runtime_login === repo[:username] and
        Enum.all?([:hostname, :port, :database, :ssl], fn key ->
          runtime.lifecycle_repo[key] === repo[key]
        end)
    end
  end

  def valid?(_, _), do: false

  if Mix.env() == :test do
    @doc false
    def identity_child(%__MODULE__{provider: {:fixture, _, _, _}}, options) do
      %{id: MixerHosted.Identity.KeyOwnerSupervisor,
        start: {MixerHosted.Identity.KeyOwnerSupervisor, :start_fixture, [options]},
        type: :supervisor}
    end
  end

  def identity_child(_, options), do: {MixerHosted.Identity.KeyOwnerSupervisor, options}
end
