defmodule MixerHosted.Protocol.ArtifactJSON do
  @moduledoc false
  @max_uint 18_446_744_073_709_551_615

  # This walk precedes Jason. It retains only bounded outer spans, never a
  # character list, and counts keys, values and containers before descending.
  def decode(bytes, maximum)
      when is_binary(bytes) and is_integer(maximum) and maximum in 1..6_291_456 and
             byte_size(bytes) <= maximum do
    with {:ok, spans, stats} <- preflight(bytes, maximum),
         {:ok, ordered} <- Jason.decode(bytes, objects: :ordered_objects, strings: :copy),
         {:ok, value} <- unique(ordered) do
      {:ok, value, spans, stats}
    else
      _ -> {:error, :invalid_json}
    end
  end

  def decode(_, _), do: {:error, :document_limit}

  def preflight(bytes, maximum)
      when is_binary(bytes) and is_integer(maximum) and maximum in 1..6_291_456 and
             byte_size(bytes) <= maximum do
    try do
      {finish, items, spans, deepest} = value(bytes, ws(bytes, 0), 0, 0, 0)
      if ws(bytes, finish) != byte_size(bytes), do: fail()
      {:ok, spans, %{items: items, max_depth: deepest, input_bytes: byte_size(bytes)}}
    catch
      :invalid -> {:error, :invalid_json}
    end
  end

  def preflight(_, _), do: {:error, :document_limit}

  defp value(bytes, offset, depth, items, deepest) do
    if depth > 16 or items >= 4096, do: fail()
    items = items + 1
    deepest = max(deepest, depth)

    case at(bytes, offset) do
      ?{ -> object(bytes, ws(bytes, offset + 1), depth, items, 0, [], deepest)
      ?[ -> array(bytes, ws(bytes, offset + 1), depth, items, 0, deepest)
      ?" -> {string(bytes, offset + 1), items, [], deepest}
      ?t -> {literal(bytes, offset, "true"), items, [], deepest}
      ?f -> {literal(bytes, offset, "false"), items, [], deepest}
      digit when digit in ?0..?9 -> {number(bytes, offset, 0, 0), items, [], deepest}
      _ -> fail()
    end
  end

  defp object(bytes, offset, depth, items, count, spans, deepest) do
    if at(bytes, offset) == ?} do
      {offset + 1, items, Enum.reverse(spans), deepest}
    else
      member(bytes, offset, depth, items, count, spans, deepest)
    end
  end

  defp member(bytes, offset, depth, items, count, spans, deepest) do
    if count >= 256 or items >= 4096 or at(bytes, offset) != ?", do: fail()
    key_end = string(bytes, offset + 1)
    colon = ws(bytes, key_end)
    if at(bytes, colon) != ?:, do: fail()
    start = ws(bytes, colon + 1)
    {finish, items, _, deepest} = value(bytes, start, depth + 1, items + 1, deepest)

    spans =
      if depth == 0, do: [{offset, key_end - offset, start, finish - start} | spans], else: spans

    next = ws(bytes, finish)

    case at(bytes, next) do
      ?} -> {next + 1, items, Enum.reverse(spans), deepest}
      ?, -> member(bytes, ws(bytes, next + 1), depth, items, count + 1, spans, deepest)
      _ -> fail()
    end
  end

  defp array(bytes, offset, depth, items, count, deepest) do
    if at(bytes, offset) == ?] do
      {offset + 1, items, [], deepest}
    else
      element(bytes, offset, depth, items, count, deepest)
    end
  end

  defp element(bytes, offset, depth, items, count, deepest) do
    if count >= 256, do: fail()
    {finish, items, _, deepest} = value(bytes, offset, depth + 1, items, deepest)
    next = ws(bytes, finish)

    case at(bytes, next) do
      ?] -> {next + 1, items, [], deepest}
      ?, -> element(bytes, ws(bytes, next + 1), depth, items, count + 1, deepest)
      _ -> fail()
    end
  end

  defp string(bytes, offset) do
    case at(bytes, offset) do
      ?" -> offset + 1
      ?\\ -> escape(bytes, offset + 1)
      c when is_integer(c) and c >= 32 -> string(bytes, offset + 1)
      _ -> fail()
    end
  end

  defp escape(bytes, offset) do
    case at(bytes, offset) do
      c when c in [?", ?\\, ?/, ?b, ?f, ?n, ?r, ?t] ->
        string(bytes, offset + 1)

      ?u ->
        Enum.each(1..4, fn n -> if not hex?(at(bytes, offset + n)), do: fail() end)
        string(bytes, offset + 5)

      _ ->
        fail()
    end
  end

  defp hex?(c), do: c in ?0..?9 or c in ?a..?f or c in ?A..?F

  defp number(bytes, offset, value, count) do
    case at(bytes, offset) do
      c when c in ?0..?9 ->
        if count >= 20 or (count > 0 and value == 0), do: fail()
        next = value * 10 + c - ?0
        if next > @max_uint, do: fail()
        number(bytes, offset + 1, next, count + 1)

      _ ->
        offset
    end
  end

  defp literal(bytes, offset, text) do
    size = byte_size(text)
    if offset + size > byte_size(bytes) or binary_part(bytes, offset, size) != text, do: fail()
    offset + size
  end

  defp ws(bytes, offset) do
    if at(bytes, offset) in [32, 9, 10, 13], do: ws(bytes, offset + 1), else: offset
  end

  defp at(bytes, offset) when offset < byte_size(bytes), do: :binary.at(bytes, offset)
  defp at(_, _), do: nil
  defp fail, do: throw(:invalid)

  defp unique(%Jason.OrderedObject{values: pairs}) do
    Enum.reduce_while(pairs, {:ok, %{}}, fn {key, value}, {:ok, result} ->
      if Map.has_key?(result, key) do
        {:halt, {:error, :duplicate}}
      else
        case unique(value) do
          {:ok, checked} -> {:cont, {:ok, Map.put(result, key, checked)}}
          error -> {:halt, error}
        end
      end
    end)
  end

  defp unique(values) when is_list(values) do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, result} ->
      case unique(value) do
        {:ok, checked} -> {:cont, {:ok, [checked | result]}}
        error -> {:halt, error}
      end
    end)
    |> case do
      {:ok, checked} -> {:ok, Enum.reverse(checked)}
      error -> error
    end
  end

  defp unique(value) when is_binary(value) or is_integer(value) or is_boolean(value),
    do: {:ok, value}

  defp unique(_), do: {:error, :type}
end
