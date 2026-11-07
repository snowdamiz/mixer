defmodule MixerHosted.Identity.ConfiguredVerifier do
  @moduledoc "Configured identity adapter. The public behavior is bound to the explicitly started owner."
  @behaviour MixerHosted.Identity.Verifier
  alias MixerHosted.Identity.{
    AccessTokenVerifier,
    Admission,
    BoundedJSON,
    Encoding,
    KeyOwner,
    TrustSnapshot
  }

  @impl true
  def authenticate(token, now), do: authenticate(KeyOwner, :configured, token, now)
  @doc false
  def authenticate(owner, profile_id, token, now) do
    with {:ok, permit} <- Admission.acquire(owner, profile_id) do
      try do
        verify(owner, permit, token, now, 0)
      after
        KeyOwner.release(owner, permit)
        Admission.release(permit)
      end
    end
  end

  defp verify(owner, permit, token, now, retries) do
    with {:ok, lease} <- KeyOwner.checkout(owner, permit, now) do
      result =
        AccessTokenVerifier.verify(token, max(now, System.system_time(:second)), lease.snapshot)

      case result do
        {:ok, identity} ->
          case KeyOwner.finish(owner, lease) do
            :ok ->
              if identity.expires_at > System.system_time(:second),
                do: result,
                else: {:error, :unauthenticated}

            {:error, :retry_current} when retries == 0 ->
              verify(owner, permit, token, System.system_time(:second), 1)

            {:error, :retry_current} ->
              {:error, :identity_unavailable}

            error ->
              error
          end

        {:error, :unauthenticated} ->
          with {:ok, kid} <- header_kid(token),
               :error <- TrustSnapshot.key(lease.snapshot, kid) do
            KeyOwner.note_unknown(owner, lease, kid)
          end

          result

        error ->
          error
      end
    end
  end

  defp header_kid(token) when is_binary(token) and byte_size(token) <= 4_089 do
    with [h, _, _] <- :binary.split(token, ".", [:global]),
         {:ok, bytes} <- Encoding.decode64(h, 2_048),
         {:ok, header} <- BoundedJSON.object(bytes, 2_048),
         true <-
           map_size(header) == 3 and header["alg"] == "RS256" and
             header["typ"] in ["at+jwt", "application/at+jwt"] and
             Encoding.bounded_string?(header["kid"], 128) do
      {:ok, header["kid"]}
    else
      _ -> :error
    end
  end

  defp header_kid(_), do: :error
end
