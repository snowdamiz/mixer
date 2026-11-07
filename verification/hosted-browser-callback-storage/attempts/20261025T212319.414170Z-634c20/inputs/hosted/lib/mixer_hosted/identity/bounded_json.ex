defmodule MixerHosted.Identity.BoundedJSON do
  @moduledoc false

  # The byte limit is enforced before Jason allocates a decoded tree. Ordered
  # objects preserve decoded member names, including escaped-equivalent names.
  @spec object(binary(), pos_integer()) :: {:ok, map()} | :error
  def object(raw, limit) when is_binary(raw) and byte_size(raw) <= limit do
    with {:ok, %Jason.OrderedObject{} = object} <-
           Jason.decode(raw, objects: :ordered_objects, keys: :strings, strings: :copy),
         {:ok, value} <- unique(object, 0) do
      {:ok, value}
    else
      _ -> :error
    end
  rescue
    _ -> :error
  end

  def object(_, _), do: :error

  defp unique(_, depth) when depth > 16, do: :error

  defp unique(%Jason.OrderedObject{values: pairs}, depth) when length(pairs) <= 64 do
    Enum.reduce_while(pairs, {:ok, %{}}, fn {name, value}, {:ok, result} ->
      with false <- Map.has_key?(result, name),
           {:ok, value} <- unique(value, depth + 1) do
        {:cont, {:ok, Map.put(result, name, value)}}
      else
        _ -> {:halt, :error}
      end
    end)
  end

  defp unique(%Jason.OrderedObject{}, _), do: :error

  defp unique(values, depth) when is_list(values) and length(values) <= 64 do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, result} ->
      case unique(value, depth + 1) do
        {:ok, value} -> {:cont, {:ok, [value | result]}}
        :error -> {:halt, :error}
      end
    end)
    |> case do
      {:ok, result} -> {:ok, Enum.reverse(result)}
      :error -> :error
    end
  end

  defp unique(values, _) when is_list(values), do: :error
  defp unique(value, _), do: {:ok, value}
end
