defmodule MixerHosted.CustomerBuilds.Policy do
  @moduledoc "Private build-purpose checks. Evaluations and descriptions are never capabilities."
  alias MixerHosted.Identity.{Encoding, VerifiedIdentity}

  @fields ~w(profile_id profile_version issuer subject client_id credential_ref issued_at expires_at identity_class scopes)a
  @roles ~w(owner administrator developer release_manager viewer)

  def request(%VerifiedIdentity{} = i) when map_size(i) == 11 do
    now = System.system_time(:second)

    cond do
      Enum.sort(Map.keys(Map.from_struct(i))) != Enum.sort(@fields) or
        not Encoding.bounded_string?(i.profile_id, 128) or
        not (is_integer(i.profile_version) and i.profile_version in 1..2_147_483_647) or
        not Encoding.bounded_string?(i.issuer, 2048) or
        not Encoding.bounded_string?(i.subject, 256) or
        not Encoding.bounded_string?(i.client_id, 256) or
        not Encoding.bounded_string?(i.credential_ref, 256) or
        not Encoding.numeric_date?(i.issued_at) or not Encoding.numeric_date?(i.expires_at) or
        i.issued_at >= i.expires_at or i.expires_at <= now or i.issued_at > now + 30 or
        i.identity_class not in [:human, :service] or not scopes?(i.scopes, 32, MapSet.new()) ->
        {:error, :unauthenticated}

      i.identity_class != :human or "mixer.build.read" not in i.scopes ->
        {:error, :permission_denied}

      true ->
        :ok
    end
  end

  def request(_), do: {:error, :unauthenticated}

  def live?(i, e, now) do
    p = e["profile"]
    b = e["binding"]
    a = e["principal"]
    c = e["credential"]
    f = e["family"]
    members = e["memberships"]

    p["id"] == i.profile_id and p["version"] == i.profile_version and
      p["issuer"] == i.issuer and p["client_id"] == i.client_id and
      p["identity_class"] == "human" and p["active"] == true and
      b["profile_id"] == p["id"] and b["profile_version"] == p["version"] and
      b["subject"] == i.subject and b["active"] == true and b["identity_class"] == "human" and
      b["principal_id"] == a["id"] and a["active"] == true and a["identity_class"] == "human" and
      c["reference"] == i.credential_ref and c["profile_id"] == p["id"] and
      c["profile_version"] == p["version"] and c["principal_id"] == a["id"] and
      f["id"] == c["family_id"] and f["principal_id"] == a["id"] and
      f["profile_id"] == p["id"] and f["profile_version"] == p["version"] and
      Enum.all?([a, c, f], &live_row?(&1, i.issued_at, now)) and
      i.expires_at > now and i.issued_at <= now + 30 and
      is_list(members) and length(members) in 1..64 and
      Enum.any?(members, fn m -> m["role"] in @roles and live_row?(m, nil, now) end)
  rescue
    _ -> false
  end

  defp live_row?(r, issued, now),
    do:
      r["active"] == true and
        is_integer(r["not_before"]) and r["not_before"] <= now and
        (is_nil(issued) or r["not_before"] <= issued) and
        (is_nil(r["expires_at"]) or now < r["expires_at"])

  defp scopes?([], _, _), do: true

  defp scopes?([s | rest], n, seen) when n > 0,
    do:
      Encoding.bounded_string?(s, 256) and not MapSet.member?(seen, s) and
        scopes?(rest, n - 1, MapSet.put(seen, s))

  defp scopes?(_, _, _), do: false
end
