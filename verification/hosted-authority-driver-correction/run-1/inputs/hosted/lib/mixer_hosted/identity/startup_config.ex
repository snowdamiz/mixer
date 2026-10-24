defmodule MixerHosted.Identity.StartupConfig do
  @moduledoc "Validated, restart-scoped operator identity settings."
  alias MixerHosted.Identity.{BoundedJSON, Manifest}
  @derive {Inspect, only: [:mode]}
  @enforce_keys [:mode, :owner_options]
  defstruct @enforce_keys
  @envelope ~w(version generation binding profiles resolvers)
  @entry ~w(profile jwks_endpoint transport)
  @profile ~w(profile_id profile_version issuer audience client_id identity_class enabled)
  @endpoint ~w(host port path)

  # Roots are supplied by RuntimeConfig from OTP, never the environment. Keeping
  # the constructor pure also allows isolated synthetic-CA startup verification.
  def load!(env, role, roots) when is_map(env) and role in [:api, :processor] do
    case Map.get(env, "MIXER_IDENTITY_MODE", "disabled") do
      "disabled" ->
        if Map.has_key?(env, "MIXER_IDENTITY_CONFIG"), do: invalid!(:unexpected_configuration)
        %__MODULE__{mode: :disabled, owner_options: []}

      "configured" when role == :api ->
        configured!(Map.get(env, "MIXER_IDENTITY_CONFIG"), roots)

      "configured" ->
        invalid!(:role)

      _ ->
        invalid!(:mode)
    end
  end

  defp configured!(raw, roots) do
    with {:ok, object} <- BoundedJSON.object(raw, 65_536),
         true <- exact?(object, @envelope),
         1 <- object["version"],
         generation when is_integer(generation) and generation in 1..2_147_483_647 <-
           object["generation"],
         profiles when is_list(profiles) and length(profiles) in 1..8 <- object["profiles"],
         {:ok, entries} <- convert_all(profiles, &entry/1),
         {:ok, manifest} <- Manifest.validate(entries),
         binding when is_binary(binding) <- object["binding"],
         true <- Map.has_key?(manifest, binding),
         addresses when is_list(addresses) and length(addresses) in 1..3 <- object["resolvers"],
         true <- length(Enum.uniq(addresses)) == length(addresses),
         {:ok, resolvers} <- convert_all(addresses, &resolver/1) do
      if not valid_roots?(roots), do: invalid!(:ca_roots)

      %__MODULE__{
        mode: :configured,
        owner_options: [
          manifest: entries,
          generation: generation,
          binding: binding,
          resolvers: resolvers,
          ca_roots: roots
        ]
      }
    else
      _ -> invalid!(:configuration)
    end
  end

  defp entry(value) when is_map(value) do
    with true <- exact?(value, @entry),
         p when is_map(p) <- value["profile"],
         true <- exact?(p, @profile),
         endpoint when is_map(endpoint) <- value["jwks_endpoint"],
         true <- exact?(endpoint, @endpoint),
         :hosted_https <- transport(value["transport"]),
         class when class in [:human, :service] <- identity_class(p["identity_class"]) do
      {:ok,
       %{
         profile: %{
           profile_id: p["profile_id"],
           profile_version: p["profile_version"],
           issuer: p["issuer"],
           audience: p["audience"],
           client_id: p["client_id"],
           identity_class: class,
           enabled: p["enabled"]
         },
         jwks_endpoint: %{
           host: endpoint["host"],
           port: endpoint["port"],
           path: endpoint["path"]
         },
         transport: :hosted_https
       }}
    else
      _ -> :error
    end
  end

  defp entry(_), do: :error
  defp transport("hosted_https"), do: :hosted_https
  defp transport(_), do: :error
  defp identity_class("human"), do: :human
  defp identity_class("service"), do: :service
  defp identity_class(_), do: :error

  defp resolver(value) when is_binary(value) and byte_size(value) in 1..45 do
    with {:ok, address} <- :inet.parse_address(String.to_charlist(value)),
         true <- tuple_size(address) in [4, 8],
         ^value <- address |> :inet.ntoa() |> List.to_string() do
      {:ok, {address, 53}}
    else
      _ -> :error
    end
  end

  defp resolver(_), do: :error
  defp exact?(map, keys), do: Enum.sort(Map.keys(map)) == Enum.sort(keys)

  defp convert_all(values, convert) do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, result} ->
      case convert.(value) do
        {:ok, converted} -> {:cont, {:ok, [converted | result]}}
        _ -> {:halt, :error}
      end
    end)
    |> case do
      {:ok, result} -> {:ok, Enum.reverse(result)}
      :error -> :error
    end
  end

  defp valid_roots?(roots) when is_list(roots) and roots != [] do
    Enum.all?(roots, fn
      der when is_binary(der) ->
        try do
          :public_key.pkix_decode_cert(der, :otp)
          true
        rescue
          _ -> false
        end

      _ ->
        false
    end)
  end

  defp valid_roots?(_), do: false
  defp invalid!(:mode), do: raise(ArgumentError, "invalid identity startup: mode")
  defp invalid!(:role), do: raise(ArgumentError, "invalid identity startup: role")

  defp invalid!(:configuration),
    do: raise(ArgumentError, "invalid identity startup: configuration")

  defp invalid!(:ca_roots), do: raise(ArgumentError, "invalid identity startup: ca_roots")

  defp invalid!(:unexpected_configuration),
    do: raise(ArgumentError, "invalid identity startup: unexpected_configuration")
end
