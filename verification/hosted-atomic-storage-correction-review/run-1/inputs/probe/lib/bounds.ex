defmodule MixerAtomicStoragePreflight.Bounds do
  @moduledoc "Executable preimplementation budget specimen; no HTTP integration."
  def body(v) when is_binary(v) and byte_size(v) <= 6_291_456, do: v
  def body(_), do: raise(ArgumentError, "body")
  def response(v) when is_binary(v) and byte_size(v) <= 4096, do: v
  def response(_), do: raise(ArgumentError, "response")
  def page(rows, limit, byte_limit \\ 262_144)

  def page(rows, limit, byte_limit)
      when is_list(rows) and is_integer(limit) and limit in 1..100 and is_integer(byte_limit) and
             byte_limit in 1..262_144 do
    # Already verified immutable display objects; caller cannot supply arbitrary JSON.
    if Enum.any?(rows, &(byte_size(&1) > 32768)), do: raise(ArgumentError, "event display")

    {selected, _} =
      Enum.reduce_while(
        Enum.take(rows, limit),
        {[], byte_size("{\"events\":[],\"next\":null}")},
        fn row, {acc, size} ->
          # Reserve worst uint64 next cursor (22 quoted bytes), beyond null's four.
          next = size + byte_size(row) + if(acc == [], do: 0, else: 1)
          if next + 18 > byte_limit, do: {:halt, {acc, size}}, else: {:cont, {acc ++ [row], next}}
        end
      )

    next = if length(selected) < length(rows), do: "18446744073709551615", else: nil

    encoded =
      "{\"events\":[" <> Enum.join(selected, ",") <> "],\"next\":" <> Jason.encode!(next) <> "}"

    if byte_size(encoded) > byte_limit, do: raise(ArgumentError, "page budget")
    {selected, encoded}
  end

  def page(_, _, _), do: raise(ArgumentError, "page inputs")
  def admission_start, do: Agent.start_link(fn -> MapSet.new() end)

  def admit(pid) do
    Agent.get_and_update(pid, fn set ->
      if MapSet.size(set) < 4 do
        ref = make_ref()
        {{:ok, ref}, MapSet.put(set, ref)}
      else
        {:busy, set}
      end
    end)
  end

  def release(pid, ref), do: Agent.update(pid, &MapSet.delete(&1, ref))
end
