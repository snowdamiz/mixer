defmodule MixerHosted.BrowserAuth.ConfigurationDigest do
  @moduledoc """
  Versioned configuration identity for durable browser attempts and encrypted custody.

  Call only with the trusted constructor-validated Config. This digest binds its
  exact settings; it does not validate provider trust, resolve secrets, or confer
  permission. Only secret references are present in Config, never secret values.
  """
  alias MixerHosted.BrowserAuth.Config
  alias MixerHosted.Identity.Encoding

  @domain "mixer.browser.configuration.v1\0"
  @fields ~w(mode public_origin profile_id profile_version issuer client_id api_audience
    authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri
    client_auth_method client_credential_ref session_vault_ref scope response_mode
    response_iss_required transaction_seconds session_idle_seconds return_path failure_path)a
  @strings [
    public_origin: 2048,
    profile_id: 128,
    issuer: 2048,
    client_id: 256,
    api_audience: 256,
    authorization_endpoint: 2048,
    token_endpoint: 2048,
    id_token_jwks_endpoint: 2048,
    redirect_uri: 2048,
    client_credential_ref: 256,
    session_vault_ref: 256
  ]
  @fixed [
    mode: :configured,
    client_auth_method: :client_secret_basic,
    scope: "openid mixer.workspace.read",
    response_mode: "query",
    response_iss_required: true,
    transaction_seconds: 300,
    session_idle_seconds: 900,
    return_path: "/workspace",
    failure_path: "/login"
  ]

  @doc "Returns the raw 32-byte SHA-256 digest used by SQL and AEAD context."
  def digest(config) do
    with {:ok, bytes} <- canonical_bytes(config) do
      {:ok, :crypto.hash(:sha256, bytes)}
    end
  rescue
    _ -> {:error, :invalid_configuration}
  end

  @doc "Closed ordered JSON pairs after a fixed domain; contains configuration metadata only."
  def canonical_bytes(%Config{} = config) do
    with true <- Enum.sort(Map.keys(config)) == Enum.sort([:__struct__ | @fields]),
         true <- Enum.all?(@fixed, fn {key, value} -> Map.fetch!(config, key) === value end),
         true <-
           is_integer(config.profile_version) and config.profile_version in 1..2_147_483_647,
         true <-
           Enum.all?(@strings, fn {key, limit} ->
             Encoding.bounded_string?(Map.fetch!(config, key), limit)
           end) do
      pairs = Enum.map(@fields, &[Atom.to_string(&1), wire_value(Map.fetch!(config, &1))])
      {:ok, @domain <> Jason.encode!([1, pairs])}
    else
      _ -> {:error, :invalid_configuration}
    end
  rescue
    _ -> {:error, :invalid_configuration}
  end

  def canonical_bytes(_), do: {:error, :invalid_configuration}
  defp wire_value(:configured), do: "configured"
  defp wire_value(:client_secret_basic), do: "client_secret_basic"
  defp wire_value(value), do: value
end
