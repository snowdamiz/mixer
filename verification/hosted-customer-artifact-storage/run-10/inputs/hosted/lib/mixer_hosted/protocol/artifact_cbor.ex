defmodule MixerHosted.Protocol.ArtifactCBOR do
  @moduledoc """
  Bounded deterministic encoding for Mixer's artifact data model.

  Supports UTF-8 text, unsigned 64-bit integers, booleans, proper lists and
  text-keyed maps. It preserves text bytes and sorts encoded map keys bytewise,
  using RFC 8949 section 4.2.1. This is an encoder, not schema validation,
  signature verification or release authorization.

  Output is at most 65,536 bytes. Containers have at most 256 entries; the
  complete value has at most 4,096 items including map keys and containers.
  The root is depth zero; children at depth 16 are the last permitted level.
  A caller can lower the byte budget, but cannot raise any of these limits.
  These bound work and encoded output, not total BEAM process memory or the
  caller's already allocated input. No JSON decoding occurs here.
  """

  @max_bytes 65_536
  @max_entries 256
  @max_items 4_096
  @max_depth 16
  @max_uint 18_446_744_073_709_551_615

  @type value :: boolean() | non_neg_integer() | String.t() | [value()] | %{String.t() => value()}
  @type error :: :invalid_value | :limit_exceeded

  @spec encode(value(), pos_integer()) :: {:ok, binary()} | {:error, error()}
  def encode(value, max_bytes \\ @max_bytes)

  def encode(value, max_bytes) when is_integer(max_bytes) and max_bytes in 1..@max_bytes do
    with {:ok, encoded, _budget} <- encode_value(value, 0, {max_bytes, @max_items}) do
      {:ok, IO.iodata_to_binary(encoded)}
    end
  end

  def encode(_, _), do: {:error, :invalid_value}

  defp encode_value(_, depth, {_, items}) when depth > @max_depth or items == 0,
    do: {:error, :limit_exceeded}

  defp encode_value(value, depth, {bytes, items}),
    do: encode_kind(value, depth, {bytes, items - 1})

  defp encode_kind(false, _, budget), do: emit(<<0xF4>>, budget)
  defp encode_kind(true, _, budget), do: emit(<<0xF5>>, budget)

  defp encode_kind(value, _, budget) when is_integer(value) and value in 0..@max_uint,
    do: emit(head(0, value), budget)

  defp encode_kind(value, _, budget) when is_binary(value) do
    prefix = head(3, byte_size(value))

    with {:ok, remaining} <- debit(budget, byte_size(prefix) + byte_size(value)) do
      if String.valid?(value),
        do: {:ok, [prefix, value], remaining},
        else: {:error, :invalid_value}
    end
  end

  defp encode_kind(value, depth, budget) when is_list(value) do
    with {:ok, count} <- bounded_length(value, 0),
         {:ok, prefix, remaining} <- emit(head(4, count), budget),
         {:ok, elements, remaining} <- encode_elements(value, depth + 1, remaining, []) do
      {:ok, [prefix | elements], remaining}
    end
  end

  defp encode_kind(value, _, _) when is_struct(value), do: {:error, :invalid_value}

  defp encode_kind(value, _, _) when is_map(value) and map_size(value) > @max_entries,
    do: {:error, :limit_exceeded}

  defp encode_kind(value, depth, budget) when is_map(value) do
    with {:ok, prefix, remaining} <- emit(head(5, map_size(value)), budget),
         {:ok, pairs, remaining} <- encode_keys(Map.to_list(value), depth + 1, remaining, []),
         {:ok, elements, remaining} <-
           encode_pairs(Enum.sort_by(pairs, &elem(&1, 0)), depth + 1, remaining, []) do
      {:ok, [prefix | elements], remaining}
    end
  end

  defp encode_kind(_, _, _), do: {:error, :invalid_value}

  # Inspect at most 257 cons cells, including rejection of an oversized list.
  defp bounded_length([], count), do: {:ok, count}
  defp bounded_length([_ | _], @max_entries), do: {:error, :limit_exceeded}
  defp bounded_length([_ | rest], count), do: bounded_length(rest, count + 1)
  defp bounded_length(_, _), do: {:error, :invalid_value}

  defp encode_elements([], _, budget, acc), do: {:ok, Enum.reverse(acc), budget}

  defp encode_elements([value | rest], depth, budget, acc) do
    with {:ok, encoded, remaining} <- encode_value(value, depth, budget) do
      encode_elements(rest, depth, remaining, [encoded | acc])
    end
  end

  defp encode_keys([], _, budget, acc), do: {:ok, acc, budget}

  defp encode_keys([{key, value} | rest], depth, budget, acc) when is_binary(key) do
    with {:ok, encoded, remaining} <- encode_value(key, depth, budget) do
      encode_keys(rest, depth, remaining, [{IO.iodata_to_binary(encoded), value} | acc])
    end
  end

  defp encode_keys(_, _, _, _), do: {:error, :invalid_value}

  defp encode_pairs([], _, budget, acc), do: {:ok, Enum.reverse(acc), budget}

  defp encode_pairs([{key, value} | rest], depth, budget, acc) do
    with {:ok, encoded, remaining} <- encode_value(value, depth, budget) do
      encode_pairs(rest, depth, remaining, [[key, encoded] | acc])
    end
  end

  defp emit(encoded, budget) do
    with {:ok, remaining} <- debit(budget, byte_size(encoded)) do
      {:ok, encoded, remaining}
    end
  end

  defp debit({bytes, items}, size) when size <= bytes, do: {:ok, {bytes - size, items}}
  defp debit(_, _), do: {:error, :limit_exceeded}

  defp head(major, size) when size < 24, do: <<major::3, size::5>>
  defp head(major, size) when size <= 0xFF, do: <<major::3, 24::5, size::8>>
  defp head(major, size) when size <= 0xFFFF, do: <<major::3, 25::5, size::16>>
  defp head(major, size) when size <= 0xFFFFFFFF, do: <<major::3, 26::5, size::32>>
  defp head(major, size), do: <<major::3, 27::5, size::64>>
end
