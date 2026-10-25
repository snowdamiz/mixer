defmodule MixerHosted.Identity.AccessTokenVerifier do
  @moduledoc """
  Pure RFC 9068 / RS256 access-token verification using one validated snapshot.

  The input is a compact JWS without an HTTP `Bearer ` prefix, at most 4089
  bytes. No token field selects configuration, a URL, a network request or a
  broader algorithm. A future HTTP adapter must enforce a single authorization
  header and the 4096-byte bound including the prefix.

  This helper owns no active trust pointer, refresh, cache or provider lifecycle.
  It cannot enforce a later disable/revision if a caller deliberately supplies
  an older snapshot. A configured adapter must supply current trust on every
  request and implement the `Verifier.authenticate/2` behavior separately.
  """

  alias MixerHosted.Identity.{BoundedJSON, Encoding, TrustSnapshot, VerifiedIdentity}

  @scopes ["mixer.artifact.read", "mixer.artifact.upload", "mixer.audit.read"]

  @spec verify(binary(), integer(), TrustSnapshot.t() | nil) ::
          {:ok, VerifiedIdentity.t()} | {:error, :unauthenticated | :identity_unavailable}
  def verify(compact_token, now, snapshot) do
    case TrustSnapshot.status(snapshot, now) do
      :fresh -> verify_fresh(compact_token, now, snapshot)
      :disabled -> {:error, :unauthenticated}
      :unavailable -> {:error, :identity_unavailable}
    end
  end

  defp verify_fresh(compact_token, now, snapshot) do
    with true <- is_binary(compact_token) and byte_size(compact_token) <= 4_089,
         [header_segment, payload_segment, signature_segment] <-
           :binary.split(compact_token, ".", [:global]),
         {:ok, header_bytes} <- Encoding.decode64(header_segment, 2_048),
         {:ok, payload_bytes} <- Encoding.decode64(payload_segment, 3_072),
         {:ok, signature} <- Encoding.decode64(signature_segment, 512),
         {:ok, header} <- BoundedJSON.object(header_bytes, 2_048),
         true <- valid_header?(header),
         {:ok, claims} <- BoundedJSON.object(payload_bytes, 3_072),
         {:ok, {key, signature_size}} <- TrustSnapshot.key(snapshot, header["kid"]),
         true <- byte_size(signature) == signature_size,
         {true, ^payload_bytes, _jws} <-
           JOSE.JWS.verify_strict(key, ["RS256"], compact_token),
         profile = TrustSnapshot.profile(snapshot),
         true <- valid_claims?(claims, profile, now),
         {:ok, scopes} <- scopes(claims) do
      {:ok,
       %VerifiedIdentity{
         profile_id: profile.profile_id,
         profile_version: profile.profile_version,
         issuer: profile.issuer,
         subject: claims["sub"],
         client_id: profile.client_id,
         credential_ref: claims["jti"],
         issued_at: claims["iat"],
         expires_at: claims["exp"],
         identity_class: profile.identity_class,
         scopes: scopes
       }}
    else
      _ -> {:error, :unauthenticated}
    end
  rescue
    _ -> {:error, :unauthenticated}
  catch
    _, _ -> {:error, :unauthenticated}
  end

  defp valid_header?(header) do
    map_size(header) == 3 and header["alg"] == "RS256" and
      header["typ"] in ["at+jwt", "application/at+jwt"] and
      Encoding.bounded_string?(header["kid"], 128)
  end

  defp valid_claims?(claims, profile, now) do
    issued = claims["iat"]
    expiry = claims["exp"]
    maximum_lifetime = if profile.identity_class == :human, do: 900, else: 300

    claims["iss"] == profile.issuer and claims["client_id"] == profile.client_id and
      Encoding.bounded_string?(claims["sub"], 256) and
      Encoding.bounded_string?(claims["jti"], 256) and
      valid_audience?(claims["aud"], profile.audience) and
      Encoding.numeric_date?(issued) and Encoding.numeric_date?(expiry) and
      issued < expiry and expiry - issued <= maximum_lifetime and expiry > now and
      issued <= now + 30 and valid_not_before?(claims, expiry, now)
  end

  defp valid_audience?(audience, expected) when is_binary(audience), do: audience == expected

  defp valid_audience?(audiences, expected) when is_list(audiences) do
    length(audiences) in 1..8 and expected in audiences and
      Enum.all?(audiences, &Encoding.bounded_string?(&1, 256)) and
      Enum.uniq(audiences) == audiences
  end

  defp valid_audience?(_, _), do: false

  defp valid_not_before?(%{"nbf" => not_before}, expiry, now) do
    Encoding.numeric_date?(not_before) and not_before < expiry and not_before <= now + 30
  end

  defp valid_not_before?(_, _, _), do: true

  defp scopes(%{"scope" => value}) when is_binary(value) and byte_size(value) in 1..1_024 do
    words = :binary.split(value, " ", [:global])

    if length(words) <= 32 and Enum.all?(words, &scope_word?/1) and
         Enum.uniq(words) == words do
      {:ok, Enum.filter(@scopes, &(&1 in words))}
    else
      :error
    end
  end

  defp scopes(claims) do
    if Map.has_key?(claims, "scope"), do: :error, else: {:ok, []}
  end

  defp scope_word?(<<>>), do: false

  defp scope_word?(word) do
    Enum.all?(:binary.bin_to_list(word), &(&1 == 33 or &1 in 35..91 or &1 in 93..126))
  end
end
