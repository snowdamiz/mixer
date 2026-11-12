defmodule MixerHosted.BrowserAuth.ProviderTrustConfig do
  @moduledoc """
  Pure restart-scoped settings for the separate browser ID-token trust owner.

  Reuses the existing startup and browser configuration constructors. This value
  neither authenticates its caller nor establishes configuration provenance. Only
  the trusted installation path may eventually consume it. It starts no owner,
  fetches no keys, resolves no secrets and grants no production admission.
  """
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest}
  alias MixerHosted.Identity.{Manifest, StartupConfig}

  @derive {Inspect, only: []}
  @enforce_keys [:configuration_digest, :owner_options]
  defstruct @enforce_keys
  @opaque t :: %__MODULE__{configuration_digest: binary(), owner_options: keyword()}
  @owner MixerHosted.BrowserAuth.ProviderTrustOwner
  @startup_keys ~w(binding ca_roots generation manifest resolvers)a
  @browser_fields ~w(public_origin profile_id profile_version issuer client_id api_audience
    authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri
    client_credential_ref session_vault_ref scope response_mode response_iss_required)a
  @failure {:error, :invalid_provider_trust_configuration}

  @spec new(%Config{}, %StartupConfig{}) ::
          {:ok, t()} | {:error, :invalid_provider_trust_configuration}
  def new(%Config{} = config, %StartupConfig{} = identity) do
    with {:ok, digest} <- ConfigurationDigest.digest(config),
         {:ok, ^identity} <- validated_identity(identity),
         {:ok, ^config} <- Config.load(browser_env(config), :api, identity),
         {:ok, entries} <- Manifest.validate(identity.owner_options[:manifest]),
         %{profile: profile} <- Map.fetch!(entries, config.profile_id),
         %URI{host: host, port: 443, path: path} <- URI.parse(config.id_token_jwks_endpoint),
         entry = %{
           profile: profile,
           jwks_endpoint: %{host: host, port: 443, path: path},
           transport: :hosted_https
         },
         {:ok, _} <- Manifest.validate([entry]) do
      {:ok,
       %__MODULE__{
         configuration_digest: digest,
         owner_options: [
           name: @owner,
           manifest: [entry],
           binding: config.profile_id,
           generation: identity.owner_options[:generation],
           resolvers: identity.owner_options[:resolvers],
           ca_roots: identity.owner_options[:ca_roots]
         ]
       }}
    else
      _ -> @failure
    end
  rescue
    _ -> @failure
  end

  def new(_, _), do: @failure

  defp validated_identity(%StartupConfig{mode: :configured, owner_options: options}) do
    with true <- Keyword.keyword?(options),
         true <- Enum.sort(Keyword.keys(options)) == Enum.sort(@startup_keys),
         {:ok, _} <- Manifest.validate(options[:manifest]),
         resolvers when is_list(resolvers) and length(resolvers) in 1..3 <- options[:resolvers] do
      object = %{
        "version" => 1,
        "generation" => options[:generation],
        "binding" => options[:binding],
        "profiles" => options[:manifest],
        "resolvers" => Enum.map(resolvers, &resolver_address/1)
      }

      {:ok,
       StartupConfig.load!(
         %{
           "MIXER_IDENTITY_MODE" => "configured",
           "MIXER_IDENTITY_CONFIG" => Jason.encode!(object)
         },
         :api,
         options[:ca_roots]
       )}
    else
      _ -> @failure
    end
  end

  defp validated_identity(_), do: @failure

  defp resolver_address({address, 53}), do: address |> :inet.ntoa() |> List.to_string()

  defp browser_env(config) do
    object =
      Map.new(@browser_fields, fn key -> {Atom.to_string(key), Map.fetch!(config, key)} end)
      |> Map.merge(%{"version" => 1, "client_auth_method" => "client_secret_basic"})

    %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }
  end
end
