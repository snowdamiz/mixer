defmodule MixerHosted.Identity.Manifest do
  @moduledoc false
  alias MixerHosted.Identity.Encoding
  @fields ~w(profile_id profile_version issuer audience client_id identity_class enabled)a
  def validate(entries) when is_list(entries) and length(entries) <= 8 do
    with true <- Enum.all?(entries, &entry?/1),
         ids = Enum.map(entries, & &1.profile.profile_id),
         true <- length(Enum.uniq(ids)) == length(ids) do
      {:ok, Map.new(entries, &{&1.profile.profile_id, &1})}
    else
      _ -> {:error, :invalid_manifest}
    end
  end

  def validate(_), do: {:error, :invalid_manifest}

  defp entry?(
         %{
           profile: p,
           jwks_endpoint: %{host: h, port: 443, path: path} = ep,
           transport: :hosted_https
         } = e
       ) do
    map_size(e) == 3 and map_size(ep) == 3 and profile?(p) and host?(h) and path?(path)
  end

  defp entry?(_), do: false

  defp profile?(p) when is_map(p) do
    Enum.sort(Map.keys(p)) == Enum.sort(@fields) and Encoding.bounded_string?(p.profile_id, 128) and
      is_integer(p.profile_version) and p.profile_version in 1..2_147_483_647 and
      issuer?(p.issuer) and Encoding.bounded_string?(p.audience, 256) and
      Encoding.bounded_string?(p.client_id, 256) and
      p.identity_class in [:human, :service] and is_boolean(p.enabled)
  end

  defp profile?(_), do: false

  defp issuer?(s) when is_binary(s) and byte_size(s) in 1..2048 do
    case URI.new(s) do
      {:ok, %URI{scheme: "https", host: h, userinfo: nil, query: nil, fragment: nil}} ->
        is_binary(h) and h != ""

      _ ->
        false
    end
  end

  defp issuer?(_), do: false

  defp host?(s) when is_binary(s) and byte_size(s) in 1..253 do
    labels = String.split(s, ".")

    match?({:error, _}, :inet.parse_address(String.to_charlist(s))) and
      Enum.all?(labels, fn l ->
        byte_size(l) in 1..63 and Regex.match?(~r/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/, l)
      end)
  end

  defp host?(_), do: false

  defp path?(s) when is_binary(s) and byte_size(s) in 1..2048 do
    String.starts_with?(s, "/") and Regex.match?(~r/^[A-Za-z0-9_~.\/-]+$/, s) and
      not Enum.any?(String.split(s, "/"), &(&1 in [".", ".."]))
  end

  defp path?(_), do: false

  def transition(history, new) do
    Enum.all?(new, fn {id, e} ->
      case history[id] do
        nil ->
          true

        %{entry: prior, retired: retired} ->
          a = prior.profile
          b = e.profile

          immutable =
            Map.take(a, [:issuer, :client_id, :identity_class]) ==
              Map.take(b, [:issuer, :client_id, :identity_class])

          unchanged = prior == e

          disable =
            a.enabled and not b.enabled and a.profile_version == b.profile_version and
              Map.put(a, :enabled, false) == b and prior.jwks_endpoint == e.jwks_endpoint

          needs_new_version = retired or (not a.enabled and b.enabled)

          immutable and
            if(needs_new_version,
              do: b.profile_version > a.profile_version,
              else: unchanged or disable or b.profile_version > a.profile_version
            )
      end
    end)
  end
end
