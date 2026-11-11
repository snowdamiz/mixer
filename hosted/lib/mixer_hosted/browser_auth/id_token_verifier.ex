defmodule MixerHosted.BrowserAuth.IDTokenVerifier do
  @moduledoc "Strict bounded RS256 OIDC verification. Trust comes from the configured provider owner."
  alias MixerHosted.Identity.{BoundedJSON, Encoding, TrustSnapshot}
  alias MixerHosted.BrowserAuth.Protocol

  def verify(id, access, nonce_digest, config, snapshot, now) do
    with :fresh <- TrustSnapshot.status(snapshot, now),
         p = TrustSnapshot.profile(snapshot),
         true <-
           p.enabled and p.identity_class === :human and
             p.profile_id === config.profile_id and p.profile_version === config.profile_version and
             p.issuer === config.issuer and p.client_id === config.client_id,
         true <-
           is_binary(id) and byte_size(id) in 1..8192 and is_binary(access) and
             byte_size(access) in 1..4089,
         [h, c, s] <- :binary.split(id, ".", [:global]),
         {:ok, hb} <- Encoding.decode64(h, 2048),
         {:ok, cb} <- Encoding.decode64(c, 4096),
         {:ok, sig} <- Encoding.decode64(s, 512),
         {:ok, header} <- BoundedJSON.object(hb, 2048),
         true <- Enum.sort(Map.keys(header)) in [~w(alg kid), ~w(alg kid typ)],
         "RS256" <- header["alg"],
         true <- not Map.has_key?(header, "typ") or header["typ"] === "JWT",
         {:ok, {key, size}} <- TrustSnapshot.key(snapshot, header["kid"]),
         true <- byte_size(sig) === size,
         {true, ^cb, _} <- JOSE.JWS.verify_strict(key, ["RS256"], id),
         {:ok, claims} <- BoundedJSON.object(cb, 4096),
         true <- claims["iss"] === config.issuer,
         true <- Encoding.bounded_string?(claims["sub"], 256),
         true <- audience?(claims["aud"], config.client_id),
         true <- azp?(claims, config.client_id),
         true <- Protocol.token?(claims["nonce"]),
         true <- :crypto.hash_equals(:crypto.hash(:sha256, claims["nonce"]), nonce_digest),
         true <- dates?(claims, now),
         <<half::binary-size(16), _::binary>> = :crypto.hash(:sha256, access),
         expected = Base.url_encode64(half, padding: false),
         true <- is_binary(claims["at_hash"]) and :crypto.hash_equals(expected, claims["at_hash"]) do
      {:ok, %{subject: claims["sub"], expires_at: claims["exp"]}}
    else
      _ -> {:error, :unauthenticated}
    end
  rescue
    _ -> {:error, :unauthenticated}
  catch
    _, _ -> {:error, :unauthenticated}
  end

  defp audience?(a, client) when is_binary(a), do: a === client

  defp audience?(a, client) when is_list(a),
    do:
      length(a) in 1..8 and client in a and
        Enum.uniq(a) === a and Enum.all?(a, &Encoding.bounded_string?(&1, 256))

  defp audience?(_, _), do: false
  defp azp?(%{"azp" => azp}, client), do: azp === client
  defp azp?(%{"aud" => a}, _) when is_list(a), do: length(a) === 1
  defp azp?(_, _), do: true

  defp dates?(c, now) do
    i = c["iat"]
    e = c["exp"]

    Encoding.numeric_date?(i) and Encoding.numeric_date?(e) and i < e and
      e - i <= 900 and i <= now + 30 and now < e and
      (not Map.has_key?(c, "nbf") or
         (Encoding.numeric_date?(c["nbf"]) and c["nbf"] < e and c["nbf"] <= now + 30))
  end
end
