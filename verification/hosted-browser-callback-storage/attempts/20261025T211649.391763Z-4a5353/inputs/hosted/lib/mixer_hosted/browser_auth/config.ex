defmodule MixerHosted.BrowserAuth.Config do
  @moduledoc """
  Pure, restart-scoped confidential browser-client configuration.

  This constructor neither starts login nor resolves credentials. The separate
  identity startup configuration must already admit the exact active human
  profile. Raw client secrets and vault keys are never accepted configuration.
  """
  alias MixerHosted.Identity.{BoundedJSON, Encoding, Manifest, StartupConfig}

  @derive {Inspect, only: [:mode]}
  defstruct mode: :disabled,
            public_origin: nil,
            profile_id: nil,
            profile_version: nil,
            issuer: nil,
            client_id: nil,
            api_audience: nil,
            authorization_endpoint: nil,
            token_endpoint: nil,
            id_token_jwks_endpoint: nil,
            redirect_uri: nil,
            client_auth_method: nil,
            client_credential_ref: nil,
            session_vault_ref: nil,
            scope: "openid mixer.workspace.read",
            response_mode: "query",
            response_iss_required: true,
            transaction_seconds: 300,
            session_idle_seconds: 900,
            return_path: "/workspace",
            failure_path: "/login"

  @fields ~w(version public_origin profile_id profile_version issuer client_id api_audience
    authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri
    client_auth_method client_credential_ref session_vault_ref scope response_mode
    response_iss_required)

  @doc "Loads only MIXER_BROWSER_AUTH_MODE and MIXER_BROWSER_AUTH_CONFIG; no environment reads."
  def load(env, role, identity) when is_map(env) and role in [:api, :processor] do
    case Map.get(env, "MIXER_BROWSER_AUTH_MODE", "disabled") do
      "disabled" ->
        if Map.has_key?(env, "MIXER_BROWSER_AUTH_CONFIG"),
          do: {:error, :unexpected_configuration},
          else: {:ok, %__MODULE__{}}

      "configured" when role == :api ->
        configured(Map.get(env, "MIXER_BROWSER_AUTH_CONFIG"), identity)

      "configured" ->
        {:error, :invalid_role}

      _ ->
        {:error, :invalid_mode}
    end
  end

  def load(_, _, _), do: {:error, :invalid_configuration}

  defp configured(raw, identity) do
    with {:ok, object} <- BoundedJSON.object(raw, 16_384),
         true <- map_size(object) == length(@fields),
         true <- Enum.all?(@fields, &Map.has_key?(object, &1)),
         1 <- object["version"],
         true <- metadata_text?(object["profile_id"], 128),
         true <- metadata_text?(object["client_id"], 256),
         true <- metadata_text?(object["api_audience"], 256),
         true <- canonical_url?(object["public_origin"], :origin),
         true <- canonical_url?(object["issuer"], :issuer),
         true <-
           Enum.all?(
             ~w(authorization_endpoint token_endpoint id_token_jwks_endpoint),
             &canonical_url?(object[&1], :endpoint)
           ),
         true <- object["redirect_uri"] == object["public_origin"] <> "/auth/callback",
         "client_secret_basic" <- object["client_auth_method"],
         true <- reference?(object["client_credential_ref"], "secret://"),
         true <- reference?(object["session_vault_ref"], "vault://"),
         "openid mixer.workspace.read" <- object["scope"],
         "query" <- object["response_mode"],
         true <- object["response_iss_required"],
         :ok <- match_identity(object, identity) do
      {:ok,
       %__MODULE__{
         mode: :configured,
         public_origin: object["public_origin"],
         profile_id: object["profile_id"],
         profile_version: object["profile_version"],
         issuer: object["issuer"],
         client_id: object["client_id"],
         api_audience: object["api_audience"],
         authorization_endpoint: object["authorization_endpoint"],
         token_endpoint: object["token_endpoint"],
         id_token_jwks_endpoint: object["id_token_jwks_endpoint"],
         redirect_uri: object["redirect_uri"],
         client_auth_method: :client_secret_basic,
         client_credential_ref: object["client_credential_ref"],
         session_vault_ref: object["session_vault_ref"]
       }}
    else
      _ -> {:error, :invalid_configuration}
    end
  end

  defp match_identity(object, %StartupConfig{mode: :configured, owner_options: options}) do
    with true <- Keyword.keyword?(options),
         true <- length(options) <= 8,
         true <- length(Keyword.keys(options)) == length(Enum.uniq(Keyword.keys(options))),
         entries when is_list(entries) <- Keyword.get(options, :manifest),
         {:ok, manifest} <- Manifest.validate(entries),
         binding when is_binary(binding) <- Keyword.get(options, :binding),
         %{profile: profile} <- Map.get(manifest, binding),
         true <- profile.enabled and profile.identity_class == :human,
         true <- object["profile_id"] == binding,
         true <- object["profile_version"] === profile.profile_version,
         true <- object["issuer"] == profile.issuer,
         true <- object["client_id"] == profile.client_id,
         true <- object["api_audience"] == profile.audience do
      :ok
    else
      _ -> :error
    end
  end

  defp match_identity(_, _), do: :error

  # Keep trust-matched browser metadata compatible with PostgreSQL/Vault text.
  # Preserve exact UTF-8 bytes, but reject NUL before construction.
  defp metadata_text?(value, limit),
    do: Encoding.bounded_string?(value, limit) and :binary.match(value, <<0>>) == :nomatch

  # A deliberately narrow canonical deployment form: lower-case DNS host, HTTPS
  # default port, literal safe paths, no userinfo/query/fragment, no URI aliases.
  # Endpoint addresses remain trusted operator inputs; a later network adapter
  # must independently qualify DNS, peer-address, TLS and response bounds.
  defp canonical_url?(value, kind) when is_binary(value) and byte_size(value) in 1..2048 do
    with {:ok,
          %URI{
            scheme: "https",
            host: host,
            port: 443,
            userinfo: nil,
            query: nil,
            fragment: nil,
            path: path
          }} <- URI.new(value),
         true <- host?(host),
         true <- path?(path, kind) do
      value == "https://" <> host <> (path || "")
    else
      _ -> false
    end
  end

  defp canonical_url?(_, _), do: false
  defp path?(nil, kind), do: kind in [:origin, :issuer]
  defp path?(_, :origin), do: false
  defp path?("/", kind), do: kind in [:issuer, :endpoint]

  defp path?("/" <> rest, _) do
    byte_size(rest) > 0 and
      Enum.all?(:binary.split(rest, "/", [:global]), fn segment ->
        segment != "" and segment not in [".", ".."] and
          ascii?(segment, &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in ~c"-._~"))
      end)
  end

  defp path?(_, _), do: false

  defp host?(value) when is_binary(value) and byte_size(value) in 1..253 do
    labels = :binary.split(value, ".", [:global])

    length(labels) >= 2 and
      match?({:error, _}, :inet.parse_address(String.to_charlist(value))) and
      Enum.all?(labels, fn label ->
        byte_size(label) in 1..63 and not String.starts_with?(label, "-") and
          not String.ends_with?(label, "-") and
          ascii?(label, &(&1 in ?a..?z or &1 in ?0..?9 or &1 == ?-))
      end)
  end

  defp host?(_), do: false

  defp reference?(value, prefix) when is_binary(value) and byte_size(value) <= 256 do
    if String.starts_with?(value, prefix) do
      rest = binary_part(value, byte_size(prefix), byte_size(value) - byte_size(prefix))

      rest != "" and
        Enum.all?(:binary.split(rest, "/", [:global]), fn segment ->
          segment != "" and segment not in [".", ".."] and
            ascii?(segment, &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in ~c"-._"))
        end)
    else
      false
    end
  end

  defp reference?(_, _), do: false

  defp ascii?(<<>>, _), do: true
  defp ascii?(<<byte, rest::binary>>, check), do: check.(byte) and ascii?(rest, check)
end
