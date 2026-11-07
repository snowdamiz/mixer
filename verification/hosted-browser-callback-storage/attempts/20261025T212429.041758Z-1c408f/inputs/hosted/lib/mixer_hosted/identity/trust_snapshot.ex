defmodule MixerHosted.Identity.TrustSnapshot do
  @moduledoc """
  Validated immutable configuration and public RSA verification keys.

  Construction validates the entire candidate before returning it. It does not
  fetch keys, activate a profile or replace a process's current configuration.
  The future adapter must atomically replace its active snapshot only after a
  successful construction, and must apply current profile disable/revision state
  on each protected request. Retaining an old value cannot extend its freshness.
  """

  alias MixerHosted.Identity.{BoundedJSON, Encoding}

  @profile_fields [
    :profile_id,
    :profile_version,
    :issuer,
    :audience,
    :client_id,
    :identity_class,
    :enabled
  ]
  @jwk_fields ~w(kty alg use key_ops kid n e)
  @enforce_keys [:profile, :keys, :fetched_at, :fresh_until]
  defstruct @enforce_keys

  @type profile :: %{
          profile_id: binary(),
          profile_version: pos_integer(),
          issuer: binary(),
          audience: binary(),
          client_id: binary(),
          identity_class: :human | :service,
          enabled: boolean()
        }
  @opaque t :: %__MODULE__{
            profile: profile(),
            keys: %{binary() => {JOSE.JWK.t(), pos_integer()}},
            fetched_at: non_neg_integer(),
            fresh_until: pos_integer()
          }

  @doc """
  Validates one exact profile and a raw JWKS JSON object of at most 256 KiB.

  Times are integer Unix seconds in 0..2^53-1. `fresh_until` is exclusive and
  must be later than `fetched_at`, by at most 300 seconds. This is a ceiling:
  the transport owner must also constrain it to authenticated HTTP freshness.
  """
  @spec new(profile(), binary(), integer(), integer()) ::
          {:ok, t()} | {:error, :invalid_trust_configuration}
  def new(profile, jwks_json, fetched_at, fresh_until) do
    with true <- valid_profile?(profile),
         true <- Encoding.numeric_date?(fetched_at),
         true <- Encoding.numeric_date?(fresh_until),
         true <- fresh_until > fetched_at and fresh_until - fetched_at <= 300,
         {:ok, %{"keys" => keys} = jwks} <- BoundedJSON.object(jwks_json, 262_144),
         true <- map_size(jwks) == 1 and is_list(keys) and length(keys) in 1..16,
         {:ok, validated_keys} <- keys(keys) do
      {:ok,
       %__MODULE__{
         profile: profile,
         keys: validated_keys,
         fetched_at: fetched_at,
         fresh_until: fresh_until
       }}
    else
      _ -> {:error, :invalid_trust_configuration}
    end
  rescue
    _ -> {:error, :invalid_trust_configuration}
  catch
    _, _ -> {:error, :invalid_trust_configuration}
  end

  @doc false
  def status(%__MODULE__{profile: %{enabled: false}}, _now), do: :disabled

  def status(%__MODULE__{fetched_at: fetched_at, fresh_until: fresh_until}, now) do
    if Encoding.numeric_date?(now) and now >= fetched_at and now < fresh_until,
      do: :fresh,
      else: :unavailable
  end

  def status(_, _), do: :unavailable

  @doc false
  def profile(%__MODULE__{profile: profile}), do: profile

  @doc false
  def key(%__MODULE__{keys: keys}, kid), do: Map.fetch(keys, kid)

  defp valid_profile?(profile) when is_map(profile) do
    Enum.sort(Map.keys(profile)) == Enum.sort(@profile_fields) and
      Encoding.bounded_string?(profile.profile_id, 128) and
      is_integer(profile.profile_version) and profile.profile_version in 1..2_147_483_647 and
      valid_issuer?(profile.issuer) and Encoding.bounded_string?(profile.audience, 256) and
      Encoding.bounded_string?(profile.client_id, 256) and
      profile.identity_class in [:human, :service] and is_boolean(profile.enabled)
  end

  defp valid_profile?(_), do: false

  defp valid_issuer?(issuer) do
    if Encoding.bounded_string?(issuer, 2_048) do
      case URI.new(issuer) do
        {:ok, %URI{scheme: "https", host: host, userinfo: nil, query: nil, fragment: nil}} ->
          is_binary(host) and byte_size(host) > 0

        _ ->
          false
      end
    else
      false
    end
  end

  defp keys(candidates) do
    Enum.reduce_while(candidates, {:ok, %{}}, fn candidate, {:ok, result} ->
      with {:ok, kid, key, size} <- key(candidate),
           false <- Map.has_key?(result, kid) do
        {:cont, {:ok, Map.put(result, kid, {key, size})}}
      else
        _ -> {:halt, :error}
      end
    end)
  end

  defp key(key) when is_map(key) do
    with true <- Enum.all?(Map.keys(key), &(&1 in @jwk_fields)),
         %{"kty" => "RSA", "alg" => "RS256", "use" => "sig", "kid" => kid} <- key,
         true <- Encoding.bounded_string?(kid, 128),
         true <- not Map.has_key?(key, "key_ops") or key["key_ops"] == ["verify"],
         {:ok, modulus} <- Encoding.decode64(key["n"], 512),
         true <- valid_modulus?(modulus),
         {:ok, <<1, 0, 1>>} <- Encoding.decode64(key["e"], 3) do
      {:ok, kid, JOSE.JWK.from_map(key), byte_size(modulus)}
    else
      _ -> :error
    end
  end

  defp key(_), do: :error

  defp valid_modulus?(<<first, _::binary>> = modulus) when first > 0 do
    bits = byte_size(modulus) * 8 - leading_zero_bits(first, 0)
    bits in 2_048..4_096 and Bitwise.band(:binary.last(modulus), 1) == 1
  end

  defp valid_modulus?(_), do: false
  defp leading_zero_bits(byte, count) when byte < 128, do: leading_zero_bits(byte * 2, count + 1)
  defp leading_zero_bits(_, count), do: count
end
