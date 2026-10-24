defmodule MixerAtomicStoragePreflight.Codec do
  @moduledoc "Synthetic deterministic fixed-schema codec. No accepted product module is loaded."
  @u64 18_446_744_073_709_551_615
  def encode(value, limit \\ 16_384) when is_integer(limit) and limit in 1..65_536 do
    {_, _} = measure(value, 0, 4096, limit)
    encoded = enc(value)
    if byte_size(encoded) > limit, do: raise(ArgumentError, "encoded budget")
    encoded
  end

  defp measure(_, depth, _, _) when depth > 16, do: raise(ArgumentError, "depth")
  defp measure(_, _, nodes, _) when nodes < 1, do: raise(ArgumentError, "nodes")

  defp measure(value, depth, nodes, budget) do
    if budget < 1, do: raise(ArgumentError, "encoded budget")

    {header, children} =
      case value do
        nil ->
          {1, []}

        n when is_integer(n) and n in 0..@u64 ->
          {byte_size(head(0, n)), []}

        {:bytes, b} when is_binary(b) ->
          {byte_size(head(2, byte_size(b))) + byte_size(b), []}

        t when is_binary(t) ->
          if not String.valid?(t), do: raise(ArgumentError, "UTF8")
          {byte_size(head(3, byte_size(t))) + byte_size(t), []}

        a when is_list(a) and length(a) <= 256 ->
          {byte_size(head(4, length(a))), a}

        _ ->
          raise(ArgumentError, "unsupported type")
      end

    if header > budget, do: raise(ArgumentError, "encoded budget")

    Enum.reduce(children, {nodes - 1, budget - header}, fn child, {remaining, left} ->
      measure(child, depth + 1, remaining, left)
    end)
  end

  defp enc(nil), do: <<0xF6>>
  defp enc(n) when is_integer(n) and n in 0..@u64, do: head(0, n)
  defp enc({:bytes, b}) when is_binary(b), do: head(2, byte_size(b)) <> b

  defp enc(t) when is_binary(t) do
    if not String.valid?(t), do: raise(ArgumentError, "UTF8")
    head(3, byte_size(t)) <> t
  end

  defp enc(a) when is_list(a) and length(a) <= 256,
    do: head(4, length(a)) <> IO.iodata_to_binary(Enum.map(a, &enc/1))

  defp enc(_), do: raise(ArgumentError, "unsupported type")
  defp head(m, n) when n < 24, do: <<m * 32 + n>>
  defp head(m, n) when n <= 255, do: <<m * 32 + 24, n>>
  defp head(m, n) when n <= 65_535, do: <<m * 32 + 25, n::16>>
  defp head(m, n) when n <= 4_294_967_295, do: <<m * 32 + 26, n::32>>
  defp head(m, n), do: <<m * 32 + 27, n::64>>
  def hash(domain, b), do: :crypto.hash(:sha256, domain <> <<0>> <> b)
  def b(v), do: {:bytes, v}
  def hex(v), do: Base.encode16(v, case: :lower)
  def unhex(v), do: Base.decode16!(v, case: :lower)
  def uuid(v), do: v |> String.replace("-", "") |> unhex()

  # Independent Elixir typed decoder; no SQL validation function is consulted.
  @display_keys ~w(audit_schema id tenant actor decision target action reason request_id source_ip recorded_at previous_state current_state previous_hash request_hash hash)
  @roles ~w(owner administrator developer release_manager billing_manager viewer)
  @upload_roles ~w(owner administrator developer)
  @seconds 9_007_199_254_740_991
  @revision 9_223_372_036_854_775_807

  def from_display(d) do
    ensure(is_map(d) and Enum.sort(Map.keys(d)) == Enum.sort(@display_keys), "closed display")
    ensure(byte_size(postgres_display(d)) <= 32_768, "display budget")
    ensure(is_integer(d["audit_schema"]) and d["audit_schema"] == 1, "schema")
    ensure(d["action"] == "artifact.upload", "action")
    [o, p] = array!(d["tenant"], 2)
    id!(o); id!(p)
    [principal, kind, binding, profile, version, issuer, subject, client, credential, family, auth] = array!(d["actor"], 11)
    ensure(kind == "human", "class")
    [time, pr, ar, fr, orr, pjr, members] = array!(d["decision"], 7)
    [to, tp, app, env, platform, runtime, manifest] = array!(d["target"], 7)
    ensure(to == o and tp == p, "tenant/target")
    ensure(platform in ["ios", "android"], "platform")
    eid = uint!(d["id"], 1, @u64)
    completed = uint!(auth, 0, @seconds)
    decision = uint!(time, 0, @seconds)
    recorded = uint!(d["recorded_at"], 0, @seconds)
    ensure(completed >= decision - 45 and completed <= decision + 30 and recorded >= decision, "time")
    ensure(is_list(members) and length(members) in 1..64, "members")
    decoded_members = Enum.map(members, fn m ->
      [uuid, role, rev] = array!(m, 3)
      ensure(role in @roles, "role")
      [b(uuid!(uuid)), role, uint!(rev, 1, @revision)]
    end)
    member_ids = Enum.map(decoded_members, fn [{:bytes, id}, _, _] -> id end)
    ensure(member_ids == Enum.sort(Enum.uniq(member_ids)), "member order/unique")
    ensure(Enum.any?(decoded_members, fn [_, role, _] -> role in @upload_roles end), "upload ceiling")
    previous_hash = hex!(d["previous_hash"], if(eid == 1, do: 0, else: 32))
    hex!(d["hash"], 32)
    event = [
      1, eid, [o, p],
      [b(uuid!(principal)), kind, b(uuid!(binding)), text!(profile, 1, 128),
       uint!(version, 1, 2_147_483_647), b(hex!(issuer, 32)), b(hex!(subject, 32)),
       b(hex!(client, 32)), b(hex!(credential, 32)), b(uuid!(family)), completed],
      [decision, uint!(pr, 1, @revision), uint!(ar, 1, @revision), uint!(fr, 1, @revision),
       uint!(orr, 1, @revision), uint!(pjr, 1, @revision), decoded_members],
      [id!(to), id!(tp), id!(app), id!(env), platform, b(hex!(runtime, 32)), b(hex!(manifest, 32))],
      "artifact.upload", text!(d["reason"], 0, 512), b(uuid!(d["request_id"])), ip!(d["source_ip"]),
      recorded, b(hex!(d["previous_state"], 32)), b(hex!(d["current_state"], 32)),
      b(previous_hash), b(hex!(d["request_hash"], 32))
    ]
    ensure(byte_size(encode(event)) <= 16_384, "event budget")
    event
  rescue
    _ -> raise ArgumentError, "invalid typed display"
  end

  # Retained row oracle is deliberately separate from from_display's typed decoding.
  def validate_row!(%{organization: o, project: p, event_id: id, event_cbor: bytes,
      event_hash: hash, previous_hash: previous_hash, previous_state: previous_state,
      current_state: current_state, display_json: d, display_bytes: display_bytes}) do
    event = from_display(d)
    ensure(is_integer(id) and id in 1..@u64 and d["id"] == Integer.to_string(id), "row id")
    ensure(d["tenant"] == [o, p], "row tenant")
    ensure(bytes == encode(event) and hash == __MODULE__.hash("mixer.hosted.audit.v1", bytes), "row cbor/hash")
    ensure(d["hash"] == hex(hash) and d["previous_hash"] == hex(previous_hash) and
      d["previous_state"] == hex(previous_state) and d["current_state"] == hex(current_state), "row projections")
    ensure(is_binary(display_bytes) and byte_size(display_bytes) <= 32_768 and Jason.decode!(display_bytes) == d and display_bytes == postgres_display(d), "display bytes")
    if id == 1 do
      ensure(previous_hash == <<>> and previous_state == __MODULE__.hash("mixer.hosted.state.v1", encode([1, o, p])), "initial edge")
    end
    :ok
  end

  def postgres_display(v) when is_map(v) do
    "{" <> (v |> Map.to_list() |> Enum.sort_by(fn {k, _} -> {byte_size(k), k} end)
      |> Enum.map_join(", ", fn {k, value} -> Jason.encode!(k) <> ": " <> postgres_display(value) end)) <> "}"
  end
  def postgres_display(v) when is_list(v), do: "[" <> Enum.map_join(v, ", ", &postgres_display/1) <> "]"
  def postgres_display(v), do: Jason.encode!(v)

  defp ensure(true, _), do: :ok
  defp ensure(_, message), do: raise(ArgumentError, message)
  defp array!(v, n) do
    ensure(is_list(v) and length(v) == n, "array shape")
    v
  end
  defp text!(v, lo, hi) do
    ensure(is_binary(v) and String.valid?(v) and byte_size(v) >= lo and byte_size(v) <= hi, "text")
    v
  end
  defp uint!(v, lo, hi) do
    text!(v, 1, 20)
    ensure(Regex.match?(~r/\A(?:0|[1-9][0-9]*)\z/, v), "decimal")
    n = String.to_integer(v)
    ensure(n >= lo and n <= hi, "integer range")
    n
  end
  defp uuid!(v) do
    text!(v, 36, 36)
    ensure(Regex.match?(~r/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z/, v), "uuid")
    v |> String.replace("-", "") |> Base.decode16!(case: :lower)
  end
  defp hex!(v, n) do
    text!(v, n * 2, n * 2)
    ensure(Regex.match?(~r/\A[0-9a-f]*\z/, v), "hex")
    Base.decode16!(v, case: :lower)
  end
  defp id!(v) do
    text!(v, 1, 128)
    ensure(Regex.match?(~r/\A[A-Za-z0-9_.-]+\z/, v), "id")
    v
  end
  defp ip!(nil), do: nil
  defp ip!(v) do
    text!(v, 1, 45)
    {:ok, address} = :inet.parse_strict_address(String.to_charlist(v))
    ensure(address |> :inet.ntoa() |> to_string() == v, "canonical ip")
    v
  end
end
