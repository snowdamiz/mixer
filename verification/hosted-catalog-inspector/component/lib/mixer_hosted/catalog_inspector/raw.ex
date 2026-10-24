defmodule MixerHosted.CatalogInspector.Raw do
  @moduledoc false
  import Bitwise

  @domains_path Path.expand("../../../priv/domains.json", __DIR__)
  @external_resource @domains_path
  @descriptors Jason.decode!(File.read!(@domains_path))
  @groups @descriptors["groups"]
  @legacy @descriptors["legacy"]
  @session ~w(session_user current_user role database session_replication_role row_security default_transaction_isolation transaction_isolation transaction_read_only)
  @limits %{
    json_bytes: 4_194_304,
    string_bytes: 1_048_576,
    nodes: 100_000,
    depth: 32,
    array_items: 4096,
    object_keys: 64
  }

  def limits, do: @limits

  # Bound bytes and nesting before invoking a general JSON parser. This scan is
  # only a resource guard; Jason then validates the complete JSON grammar.
  def decode!(bytes) when is_binary(bytes) and byte_size(bytes) <= @limits.json_bytes do
    scan!(bytes, 0, false, false)
    value = Jason.decode!(bytes, keys: :strings, objects: :ordered_objects)
    {result, _} = materialize!(value, 0, @limits.nodes)
    result
  rescue
    _ -> malformed!()
  end

  def decode!(_), do: malformed!()

  defp scan!(<<>>, 0, false, false), do: :ok
  defp scan!(<<>>, _, _, _), do: malformed!()
  defp scan!(<<_, rest::binary>>, depth, true, true), do: scan!(rest, depth, true, false)
  defp scan!(<<92, rest::binary>>, depth, true, false), do: scan!(rest, depth, true, true)

  defp scan!(<<34, rest::binary>>, depth, quoted, false),
    do: scan!(rest, depth, not quoted, false)

  defp scan!(<<_, rest::binary>>, depth, true, false), do: scan!(rest, depth, true, false)

  defp scan!(<<c, rest::binary>>, depth, false, false) when c in [123, 91] do
    require!(depth < @limits.depth)
    scan!(rest, depth + 1, false, false)
  end

  defp scan!(<<c, rest::binary>>, depth, false, false) when c in [125, 93] do
    require!(depth > 0)
    scan!(rest, depth - 1, false, false)
  end

  defp scan!(<<_, rest::binary>>, depth, false, false), do: scan!(rest, depth, false, false)

  defp materialize!(value, depth, budget) do
    require!(budget > 0 and depth <= @limits.depth)
    budget = budget - 1

    case value do
      %Jason.OrderedObject{values: pairs} ->
        require!(length(pairs) <= @limits.object_keys)

        Enum.reduce(pairs, {%{}, budget}, fn {key, item}, {acc, left} ->
          text!(key, false, false)
          require!(not Map.has_key?(acc, key))
          {v, remain} = materialize!(item, depth + 1, left)
          {Map.put(acc, key, v), remain}
        end)

      items when is_list(items) ->
        require!(length(items) <= @limits.array_items)

        {reversed, left} =
          Enum.reduce(items, {[], budget}, fn item, {acc, left} ->
            {v, remain} = materialize!(item, depth + 1, left)
            {[v | acc], remain}
          end)

        {Enum.reverse(reversed), left}

      text when is_binary(text) ->
        text!(text, true, false)
        {text, budget}

      scalar when is_number(scalar) or is_boolean(scalar) or is_nil(scalar) ->
        {scalar, budget}

      _ ->
        malformed!()
    end
  end

  # Also guard native typed model inputs, which bypass JSON decoding in tests.
  defp envelope!(value, depth, budget) do
    require!(budget > 0 and depth <= @limits.depth)
    left = budget - 1

    cond do
      is_map(value) and not is_struct(value) ->
        require!(map_size(value) <= @limits.object_keys)

        Enum.reduce(value, left, fn {k, v}, n ->
          text!(k, false, false)
          envelope!(v, depth + 1, n)
        end)

      is_list(value) ->
        require!(length(value) <= @limits.array_items)
        Enum.reduce(value, left, &envelope!(&1, depth + 1, &2))

      is_binary(value) ->
        text!(value, true, false)
        left

      is_integer(value) or is_boolean(value) or is_nil(value) ->
        left

      true ->
        malformed!()
    end
  end

  def validate!(raw) do
    envelope!(raw, 0, @limits.nodes)
    keys!(raw, ~w(legacy enforcement fresh_session))
    object!(raw["legacy"], @legacy)
    keys!(raw["fresh_session"], @session)
    Enum.each(@session, &domain!(raw["fresh_session"][&1], "text"))
    enforcement = raw["enforcement"]
    keys!(enforcement, Map.keys(@groups))

    Enum.each(@groups, fn {group, fields} ->
      rows = enforcement[group]
      require!(is_list(rows))

      Enum.reduce(rows, {MapSet.new(), MapSet.new()}, fn row, {oids, names} ->
        object!(row, fields)
        if Map.has_key?(row, "oid"), do: require!(not MapSet.member?(oids, row["oid"]))
        oids = if Map.has_key?(row, "oid"), do: MapSet.put(oids, row["oid"]), else: oids

        if group in ["constraints", "triggers"],
          do: association!(row, "parent_oid", "parent_identity")

        names = if group == "triggers", do: trigger!(row, names), else: names

        if group == "startup_defaults" do
          Enum.each(~w(database role), fn field ->
            require!(row[field] != nil and (row[field <> "_oid"] != 0 or row[field] == "*"))
          end)
        end

        if group in ["parameter_effective", "parameter_public"] do
          require!(row["registered"] === (row["context"] != nil))
          selected = not row["registered"] or row["context"] in ["superuser", "superuser-backend"]
          require!(row["selected_set"] === selected)
        end

        {oids, names}
      end)
    end)

    :ok
  end

  defp trigger!(row, names) do
    key = {row["relation_oid"], row["name"]}
    require!(not MapSet.member?(names, key))

    Enum.each(
      [
        {"constraint_oid", "constraint_identity"},
        {"referenced_relation_oid", "referenced_relation"},
        {"constraint_index_oid", "constraint_index"}
      ],
      fn {oid, identity} -> association!(row, oid, identity) end
    )

    require!(not row["internal"] or row["constraint_identity"] != nil)
    bytes = Base.decode16!(row["argument_hex"], case: :lower)
    zeros = :binary.matches(bytes, <<0>>) |> length()
    require!(zeros == row["argument_count"] and (bytes == <<>> or :binary.last(bytes) == 0))
    MapSet.put(names, key)
  end

  defp association!(row, oid, identity), do: require!(row[oid] == 0 === is_nil(row[identity]))

  def normalize!(raw) do
    validate!(raw)

    enforcement =
      Map.new(raw["enforcement"], fn {group, rows} ->
        normalized =
          Enum.map(rows, fn row ->
            row =
              if group == "triggers" and row["internal"],
                do: Map.drop(row, ["name", "definition"]),
                else: row

            row =
              Map.reject(row, fn {key, _} -> key == "oid" or String.ends_with?(key, "_oid") end)

            if group == "parameter_acl" and is_list(row["entries"]),
              do: Map.update!(row, "entries", &sort/1),
              else: row
          end)

        {group, sort(normalized)}
      end)

    legacy = Map.update!(raw["legacy"], "memberships", &sort/1)
    %{raw | "legacy" => legacy, "enforcement" => enforcement}
  end

  # Python's selected comparator sorts on ensure_ascii=True JSON bytes.
  # Escape DEL and every non-ASCII scalar, including UTF16 surrogate pairs,
  # before sorting; native UTF8 ordering would change portable normalization.
  def canonical(value), do: value |> canonical_value() |> IO.iodata_to_binary()

  defp canonical_value(value) when is_binary(value) do
    escaped =
      for <<cp::utf8 <- value>> do
        cond do
          cp == 34 ->
            "\\\""

          cp == 92 ->
            "\\\\"

          cp == 8 ->
            "\\b"

          cp == 9 ->
            "\\t"

          cp == 10 ->
            "\\n"

          cp == 12 ->
            "\\f"

          cp == 13 ->
            "\\r"

          cp < 32 ->
            escape16(cp)

          cp < 127 ->
            <<cp>>

          cp <= 65_535 ->
            escape16(cp)

          true ->
            n = cp - 65_536
            escape16(55_296 + (n >>> 10)) <> escape16(56_320 + (n &&& 1023))
        end
      end

    ["\"", escaped, "\""]
  end

  defp canonical_value(value) when is_map(value) do
    pairs =
      value
      |> Enum.sort_by(&elem(&1, 0))
      |> Enum.map(fn {k, v} -> [canonical_value(k), ":", canonical_value(v)] end)

    ["{", Enum.intersperse(pairs, ","), "}"]
  end

  defp canonical_value(value) when is_list(value),
    do: ["[", value |> Enum.map(&canonical_value/1) |> Enum.intersperse(","), "]"]

  defp canonical_value(value) when is_integer(value), do: Integer.to_string(value)
  defp canonical_value(true), do: "true"
  defp canonical_value(false), do: "false"
  defp canonical_value(nil), do: "null"
  defp canonical_value(_), do: malformed!()

  defp escape16(cp),
    do: "\\u" <> (cp |> Integer.to_string(16) |> String.downcase() |> String.pad_leading(4, "0"))

  defp sort(rows), do: Enum.sort_by(rows, &canonical/1)

  defp object!(value, fields) do
    keys!(value, Map.keys(fields))
    Enum.each(fields, fn {field, descriptor} -> descriptor!(value[field], descriptor) end)
  end

  defp descriptor!(value, ["object", fields]), do: object!(value, fields)

  defp descriptor!(value, [kind, fields]) when kind in ["objects", "nullable_objects"] do
    if not (is_nil(value) and kind == "nullable_objects") do
      require!(is_list(value))
      Enum.each(value, &object!(&1, fields))
    end
  end

  defp descriptor!(value, [kind, item]) when kind in ["strings", "nullable_strings"] do
    if not (is_nil(value) and kind == "nullable_strings") do
      require!(is_list(value))
      Enum.each(value, &domain!(&1, item))
    end
  end

  defp descriptor!(value, domain), do: domain!(value, domain)

  defp domain!(nil, "nullable_" <> _), do: :ok
  defp domain!(value, "nullable_" <> name), do: domain!(value, name)
  defp domain!(value, "bool"), do: require!(is_boolean(value))

  defp domain!(value, name) when name in ["text", "identifier", "empty_text"],
    do: text!(value, name == "empty_text", name == "identifier")

  defp domain!(value, "positive_oid"), do: integer!(value, 1, 4_294_967_295)
  defp domain!(value, "optional_oid"), do: integer!(value, 0, 4_294_967_295)
  defp domain!(value, "int16"), do: integer!(value, 0, 32_767)

  defp domain!(value, name)
       when name in [
              "relation_kind",
              "constraint_type",
              "persistence",
              "replica_identity",
              "trigger_enable_mode"
            ] do
    allowed =
      %{
        "relation_kind" => "ripvImSftc",
        "constraint_type" => "cfnpxut",
        "persistence" => "put",
        "replica_identity" => "dnfi",
        "trigger_enable_mode" => "ODRA"
      }[name]

    require!(is_binary(value) and byte_size(value) == 1 and String.contains?(allowed, value))
  end

  defp domain!(value, "trigger_bits") do
    integer!(value, 0, 32_767)
    require!((value &&& bnot(127)) == 0 and (value &&& 60) != 0 and (value &&& 66) != 66)
    require!(not ((value &&& 1) != 0 and (value &&& 32) != 0))
    require!((value &&& 64) == 0 or ((value &&& 1) != 0 and (value &&& 32) == 0))
  end

  defp domain!(value, "hex") do
    text!(value, true, false)
    require!(rem(byte_size(value), 2) == 0 and Regex.match?(~r/\A[0-9a-f]*\z/, value))
  end

  defp domain!(value, "int2vector") do
    text!(value, true, false)

    if value != "" do
      require!(Regex.match?(~r/\A[1-9][0-9]*( [1-9][0-9]*)*\z/, value))

      Enum.each(String.split(value, " "), fn item ->
        require!(byte_size(item) <= 5)
        integer!(String.to_integer(item), 1, 32_767)
      end)
    end
  end

  defp domain!(value, "parent"),
    do: object!(value, %{"relation" => "text", "name" => "identifier"})

  defp domain!(value, "acl_entries") do
    require!(is_list(value))

    Enum.each(value, fn entry ->
      object!(entry, %{
        "grantor" => "text",
        "grantee" => "text",
        "privilege" => "text",
        "grantable" => "bool"
      })

      require!(entry["privilege"] in ["SET", "ALTER SYSTEM"])
    end)
  end

  defp domain!(value, "config") do
    require!(is_list(value))

    Enum.each(value, fn entry ->
      text!(entry, false, false)

      case :binary.match(entry, "=") do
        {pos, _} when pos > 0 -> :ok
        _ -> malformed!()
      end
    end)
  end

  defp domain!(_, _), do: malformed!()

  defp keys!(value, fields) do
    require!(is_map(value) and not is_struct(value) and map_size(value) == length(fields))
    Enum.each(fields, &require!(Map.has_key?(value, &1)))
  end

  defp integer!(value, lo, hi), do: require!(is_integer(value) and value >= lo and value <= hi)

  defp text!(value, empty, identifier) do
    require!(
      is_binary(value) and byte_size(value) <= @limits.string_bytes and (empty or value != "") and
        String.valid?(value)
    )

    require!(
      :binary.match(value, <<0>>) == :nomatch and (not identifier or byte_size(value) <= 63)
    )
  end

  defp require!(true), do: :ok
  defp require!(_), do: malformed!()
  defp malformed!, do: throw(:malformed_catalog)
end
