defmodule MixerHosted.BrowserAuth.Installation do
  @moduledoc "Restart-only browser installation from trusted process-launch settings."
  alias MixerHosted.BrowserAuth.{Config, RuntimeConfig, StartupSecrets, ProviderTrustConfig}
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  @derive {Inspect, only: []}
  @enforce_keys [:runtime, :provider]
  defstruct @enforce_keys ++ [:hosted, :browser, :secrets, :trust]
  @opaque t :: :disabled | %__MODULE__{}

  @spec load!(map(), %HostedConfig{}) :: t()
  def load!(env, %HostedConfig{} = hosted) when is_map(env) do
    browser = Map.take(env, ~w(MIXER_BROWSER_AUTH_MODE MIXER_BROWSER_AUTH_CONFIG))

    case Config.load(browser, hosted.role, hosted.identity_startup) do
      {:ok, %Config{mode: :disabled}} ->
        :disabled

      {:ok, %Config{mode: :configured} = config} ->
        with {:ok, secrets} <- StartupSecrets.load(env, config),
             {:ok, runtime} <-
               RuntimeConfig.new_with_build_catalog(
                 browser,
                 hosted,
                 secrets.lifecycle,
                 secrets.custody
               ),
             {:ok, trust} <- ProviderTrustConfig.new(config, hosted.identity_startup) do
          %__MODULE__{
            runtime: runtime,
            provider: {:configured, config, hosted.identity_startup},
            hosted: hosted,
            browser: browser,
            secrets: secrets,
            trust: trust
          }
        else
          _ -> raise ArgumentError, "browser installation unavailable: configuration"
        end

      _ ->
        raise ArgumentError, "browser installation unavailable: configuration"
    end
  end

  def load!(_, _), do: raise(ArgumentError, "browser installation unavailable: configuration")

  if Mix.env() == :test do
    @doc false
    @spec fixture!(RuntimeConfig.t(), %Config{}, MixerHosted.Identity.TrustSnapshot.t(), pid()) ::
            t()
    def fixture!(
          %RuntimeConfig{mode: :configured, admission_profile: :build_catalog_v3} = runtime,
          %Config{mode: :configured} = config,
          %MixerHosted.Identity.TrustSnapshot{} = snapshot,
          transport
        )
        when is_pid(transport) do
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
    def valid?(
          %__MODULE__{runtime: runtime, provider: {:fixture, config, _, transport}},
          %HostedConfig{role: :api, identity_startup: identity, repo: repo}
        ) do
      is_pid(transport) and runtime.mode === :configured and
        runtime.admission_profile === :build_catalog_v3 and runtime.browser_config === config and
        identity.mode === :configured and
        runtime.expected_roles.ordinary_runtime_login === repo[:username] and
        Enum.all?([:hostname, :port, :database, :ssl], fn key ->
          runtime.lifecycle_repo[key] === repo[key]
        end)
    end
  end

  def valid?(
        %__MODULE__{
          hosted: hosted,
          browser: browser,
          runtime: runtime,
          provider: {:configured, config, identity},
          secrets: %StartupSecrets{} = secrets,
          trust: trust
        },
        %HostedConfig{role: :api} = hosted
      ) do
    with true <- identity === hosted.identity_startup,
         true <- secrets.client_credential.reference === config.client_credential_ref,
         secret = secrets.client_credential.value,
         true <- is_binary(secret) and byte_size(secret) in 1..4096 and String.valid?(secret),
         true <- :binary.match(secret, [<<0>>, "\r", "\n"]) === :nomatch,
         {:ok, ^runtime} <-
           RuntimeConfig.new_with_build_catalog(
             browser,
             hosted,
             secrets.lifecycle,
             secrets.custody
           ),
         true <- runtime.browser_config === config,
         {:ok, ^trust} <- ProviderTrustConfig.new(config, identity) do
      true
    else
      _ -> false
    end
  rescue
    _ -> false
  catch
    _, _ -> false
  end

  def valid?(_, _), do: false

  @doc false
  def start_provider(
        %__MODULE__{provider: {:configured, config, identity}, secrets: secrets} = installation
      ) do
    if valid?(installation, installation.hosted),
      do:
        MixerHosted.BrowserAuth.ProviderOwner.start_link(
          {config, identity, secrets.client_credential.value}
        ),
      else: {:error, :browser_installation_unavailable}
  end

  @doc false
  def start_lifecycle_repo(%__MODULE__{} = installation) do
    if valid?(installation, installation.hosted),
      do: MixerHosted.BrowserAuth.LifecycleRepo.start_link(installation.runtime.lifecycle_repo),
      else: {:error, :browser_installation_unavailable}
  end

  if Mix.env() == :test do
    @doc false
    def identity_child(%__MODULE__{provider: {:fixture, _, _, _}}, options) do
      %{
        id: MixerHosted.Identity.KeyOwnerSupervisor,
        start: {MixerHosted.Identity.KeyOwnerSupervisor, :start_fixture, [options]},
        type: :supervisor
      }
    end
  end

  def identity_child(_, options), do: {MixerHosted.Identity.KeyOwnerSupervisor, options}
end
