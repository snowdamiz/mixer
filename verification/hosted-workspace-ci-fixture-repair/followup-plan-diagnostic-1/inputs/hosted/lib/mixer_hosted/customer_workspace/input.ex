defmodule MixerHosted.CustomerWorkspace.Input do
  @moduledoc false
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Identity.{BoundedJSON, Encoding, VerifiedIdentity}

  @fields ~w(profile_id profile_version issuer subject client_id credential_ref issued_at expires_at identity_class scopes)a

  def identity(%VerifiedIdentity{} = i) when map_size(i) == 11 do
    now = System.system_time(:second)

    cond do
      Enum.sort(Map.keys(Map.from_struct(i))) != Enum.sort(@fields) or
        not Encoding.bounded_string?(i.profile_id, 128) or
        not (is_integer(i.profile_version) and i.profile_version in 1..2_147_483_647) or
        not Encoding.bounded_string?(i.issuer, 2048) or
        not Encoding.bounded_string?(i.subject, 256) or
        not Encoding.bounded_string?(i.client_id, 256) or
        not Encoding.bounded_string?(i.credential_ref, 256) or
        not Encoding.numeric_date?(i.issued_at) or
        not Encoding.numeric_date?(i.expires_at) or i.issued_at >= i.expires_at or
        i.expires_at <= now or i.issued_at > now + 30 or
        i.identity_class not in [:human, :service] or not scopes?(i.scopes, 32, MapSet.new()) ->
        {:error, :unauthenticated}

      i.identity_class != :human or "mixer.workspace.read" not in i.scopes ->
        {:error, :permission_denied}

      true ->
        :ok
    end
  end

  def identity(_), do: {:error, :unauthenticated}

  def page(%{limit: limit, cursor: cursor} = page, kind, organization)
      when not is_struct(page) and map_size(page) == 2 and is_integer(limit) and limit in 1..100 do
    case decode(cursor, kind, organization) do
      {:ok, after_id} -> {:ok, %{limit: limit, after: after_id}}
      _ -> {:error, :invalid_request}
    end
  end

  def page(_, _, _), do: {:error, :invalid_request}

  def cursor(kind, organization, after_id) do
    pairs =
      if kind == "organizations",
        do: [{"v", 1}, {"kind", kind}, {"after", after_id}],
        else: [{"v", 1}, {"kind", kind}, {"organization_id", organization}, {"after", after_id}]

    %Jason.OrderedObject{values: pairs}
    |> Jason.encode!()
    |> Base.url_encode64(padding: false)
  end

  def display_name?(nil), do: true

  def display_name?(name),
    do:
      is_binary(name) and byte_size(name) in 1..256 and String.valid?(name) and
        String.printable?(name) and
        Enum.all?(String.to_charlist(name), &(&1 >= 32 and &1 not in 127..159))

  defp decode(nil, _, _), do: {:ok, nil}

  defp decode(encoded, kind, organization)
       when is_binary(encoded) and byte_size(encoded) in 1..1400 do
    with {:ok, raw} <- Base.url_decode64(encoded, padding: false),
         true <- byte_size(raw) <= 1024,
         {:ok, object} <- BoundedJSON.object(raw, 1024),
         true <- valid_cursor?(object, kind, organization),
         ^encoded <- cursor(kind, organization, object["after"]) do
      {:ok, object["after"]}
    else
      _ -> :error
    end
  end

  defp decode(_, _, _), do: :error

  defp valid_cursor?(
         %{"v" => 1, "kind" => "organizations", "after" => after_id} = value,
         "organizations",
         nil
       ),
       do: map_size(value) == 3 and Scope.identifier?(after_id)

  defp valid_cursor?(
         %{"v" => 1, "kind" => "projects", "organization_id" => org, "after" => after_id} = value,
         "projects",
         organization
       ),
       do: map_size(value) == 4 and org == organization and Scope.identifier?(after_id)

  defp valid_cursor?(_, _, _), do: false

  defp scopes?([], _, _), do: true

  defp scopes?([value | rest], left, seen) when left > 0,
    do:
      Encoding.bounded_string?(value, 256) and not MapSet.member?(seen, value) and
        scopes?(rest, left - 1, MapSet.put(seen, value))

  defp scopes?(_, _, _), do: false
end
