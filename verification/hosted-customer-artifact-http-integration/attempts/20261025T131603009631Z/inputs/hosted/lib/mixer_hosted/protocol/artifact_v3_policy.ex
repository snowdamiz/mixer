defmodule MixerHosted.Protocol.ArtifactV3Policy do
  @moduledoc false
  @uint 18_446_744_073_709_551_615
  @http "network.http.v1"
  @storage "storage.keyValue.v1"
  @http_hash "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3"
  @storage_hash "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"
  @grant_hash "b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1"
  @manifest ~w(schema scope release_id source_commit provenance_id runtime protocol guest_abi ui_schema capability_hashes capability_grants state_min state_max payload_sha256 compressed_bytes expanded_bytes compression asset_hashes source_map_sha256 limits key_id created_at_unix)
  @host ~w(scope runtime protocol guest_abi ui_schema capability_hashes state_version max_payload_bytes limits)
  @root ~w(key_id public_key scope artifact assignment revoked not_before_unix not_after_unix)

  def uint?(n), do: is_integer(n) and n >= 0 and n <= @uint

  def exact?(map, fields),
    do:
      is_map(map) and not is_struct(map) and map_size(map) == length(fields) and
        Enum.all?(fields, &Map.has_key?(map, &1))

  def id?(s), do: is_binary(s) and byte_size(s) in 1..128 and ascii?(s, :id)
  def digest?(s), do: is_binary(s) and byte_size(s) == 64 and ascii?(s, :hex)

  def scope?(s) do
    exact?(s, ~w(organization project app environment platform)) and
      Enum.all?(~w(organization project app environment), &id?(s[&1])) and
      s["platform"] in ["ios", "android"]
  end

  def limits?(l) do
    exact?(l, ~w(memory_bytes fuel startup_milliseconds)) and
      range?(l["memory_bytes"], 1, 4_194_304) and range?(l["fuel"], 1, 1_000_000) and
      range?(l["startup_milliseconds"], 1, 60_000)
  end

  def capabilities?(m) do
    is_map(m) and not is_struct(m) and map_size(m) <= 2 and
      Enum.all?(m, fn {id, hash} ->
        (id == @http and hash == @http_hash) or (id == @storage and hash == @storage_hash)
      end)
  end

  def manifest?(m) do
    exact?(m, @manifest) and tuple?(m) and scope?(m["scope"]) and
      Enum.all?(~w(release_id provenance_id key_id), &id?(m[&1])) and
      is_binary(m["source_commit"]) and byte_size(m["source_commit"]) in [40, 64] and
      ascii?(m["source_commit"], :hex) and
      Enum.all?(~w(runtime payload_sha256 source_map_sha256), &digest?(m[&1])) and
      uint?(m["state_min"]) and uint?(m["state_max"]) and m["state_min"] <= m["state_max"] and
      range?(m["created_at_unix"], 1, @uint) and m["compression"] == "none" and
      range?(m["compressed_bytes"], 1, 4_194_304) and
      m["compressed_bytes"] === m["expanded_bytes"] and
      exact?(m["asset_hashes"], []) and capabilities?(m["capability_hashes"]) and
      limits?(m["limits"]) and grants?(m["capability_grants"], m["capability_hashes"])
  end

  def host?(h) do
    exact?(h, @host) and tuple?(h) and scope?(h["scope"]) and digest?(h["runtime"]) and
      capabilities?(h["capability_hashes"]) and uint?(h["state_version"]) and
      range?(h["max_payload_bytes"], 1, 4_194_304) and limits?(h["limits"])
  end

  def compatible?(m, h) do
    host?(h) and Enum.all?(~w(scope runtime capability_hashes), &(m[&1] == h[&1])) and
      h["state_version"] >= m["state_min"] and h["state_version"] <= m["state_max"] and
      m["expanded_bytes"] <= h["max_payload_bytes"] and
      Enum.all?(~w(memory_bytes fuel startup_milliseconds), &(m["limits"][&1] <= h["limits"][&1]))
  end

  def roots?(roots) do
    bounded_list?(roots, 128) and roots != [] and
      Enum.reduce_while(roots, MapSet.new(), fn root, seen ->
        if root?(root) and not MapSet.member?(seen, root["key_id"]),
          do: {:cont, MapSet.put(seen, root["key_id"])},
          else: {:halt, false}
      end) != false
  end

  def authority(roots, key, scope, now) do
    if uint?(now) and roots?(roots) do
      case Enum.find(roots, &(&1["key_id"] == key)) do
        %{"scope" => ^scope, "artifact" => true, "revoked" => false} = root ->
          if now >= root["not_before_unix"] and
               (root["not_after_unix"] == 0 or now < root["not_after_unix"]),
             do: {:ok, root["public_key"]},
             else: {:error, :root_policy}

        _ ->
          {:error, :root_policy}
      end
    else
      {:error, :root_policy}
    end
  end

  defp root?(r) do
    exact?(r, @root) and id?(r["key_id"]) and is_binary(r["public_key"]) and
      byte_size(r["public_key"]) == 32 and
      scope?(r["scope"]) and Enum.all?(~w(artifact assignment revoked), &is_boolean(r[&1])) and
      (r["artifact"] or r["assignment"]) and uint?(r["not_before_unix"]) and
      uint?(r["not_after_unix"]) and
      (r["not_after_unix"] == 0 or r["not_after_unix"] > r["not_before_unix"])
  end

  def grants?(g, hashes) do
    exact?(g, ~w(schema schema_sha256 entries)) and g["schema"] === 1 and
      g["schema_sha256"] == @grant_hash and
      bounded_list?(g["entries"], 2) and
      Enum.reduce_while(g["entries"], "", fn e, previous ->
        if grant?(e, hashes) and e["capability_id"] > previous,
          do: {:cont, e["capability_id"]},
          else: {:halt, false}
      end) != false
  end

  defp grant?(e, hashes) do
    exact?(e, ~w(capability_id schema_sha256 permissions origins methods namespaces)) and
      e["capability_id"] in [@http, @storage] and e["schema_sha256"] == hashes[e["capability_id"]] and
      e["schema_sha256"] == if(e["capability_id"] == @http, do: @http_hash, else: @storage_hash) and
      sorted?(e["permissions"], 1) and sorted?(e["origins"], 32) and sorted?(e["methods"], 6) and
      sorted?(e["namespaces"], 32) and
      grant_authority?(e)
  end

  defp grant_authority?(%{"capability_id" => @http} = e) do
    Enum.all?(e["permissions"], &(&1 == "network.https")) and e["namespaces"] == [] and
      Enum.all?(e["origins"], &valid_origin?/1) and
      Enum.all?(e["methods"], &(&1 in ~w(DELETE GET HEAD PATCH POST PUT)))
  end

  defp grant_authority?(e) do
    Enum.all?(e["permissions"], &(&1 == "storage.appPrivate")) and e["origins"] == [] and
      e["methods"] == [] and
      Enum.all?(e["namespaces"], &valid_namespace?/1)
  end

  def valid_namespace?(s), do: is_binary(s) and byte_size(s) in 1..64 and ascii?(s, :namespace)

  def valid_origin?("https://" <> rest = full) when byte_size(full) <= 267 do
    case :binary.split(rest, ":", [:global]) do
      [host] -> hostname?(host)
      [host, port] -> hostname?(host) and port?(port)
      _ -> false
    end
  end

  def valid_origin?(_), do: false

  defp hostname?(host) do
    byte_size(host) in 1..253 and
      Enum.all?(:binary.split(host, ".", [:global]), fn label ->
        byte_size(label) in 1..63 and :binary.first(label) != ?- and :binary.last(label) != ?- and
          ascii?(label, :hostname)
      end)
  end

  defp port?(p) do
    byte_size(p) in 1..5 and ascii?(p, :digit) and :binary.first(p) != ?0 and
      case Integer.parse(p) do
        {n, ""} -> n in 1..65_535 and n != 443
        _ -> false
      end
  end

  defp sorted?(values, maximum) do
    bounded_list?(values, maximum) and
      Enum.reduce_while(values, "", fn v, previous ->
        if is_binary(v) and byte_size(v) <= 4096 and v > previous and ascii?(v, :visible),
          do: {:cont, v},
          else: {:halt, false}
      end) != false
  end

  def bounded_list?(list, maximum), do: list_count(list, maximum)
  defp list_count([], _), do: true
  defp list_count([_ | rest], left) when left > 0, do: list_count(rest, left - 1)
  defp list_count(_, _), do: false
  defp range?(n, low, high), do: is_integer(n) and n >= low and n <= high

  defp tuple?(m),
    do:
      m["protocol"] === 3 and m["guest_abi"] === 2 and m["ui_schema"] === 1 and
        (not Map.has_key?(m, "schema") or m["schema"] === 3)

  defp ascii?(<<>>, _), do: true

  defp ascii?(<<c, rest::binary>>, mode) do
    letter = c in ?a..?z or c in ?A..?Z
    digit = c in ?0..?9

    allowed =
      case mode do
        :id -> letter or digit or c in [?_, ?., ?-]
        :hex -> digit or c in ?a..?f
        :namespace -> letter or digit or c in [?_, ?-]
        :hostname -> c in ?a..?z or digit or c == ?-
        :digit -> digit
        :visible -> c in 33..126
      end

    allowed and ascii?(rest, mode)
  end
end
