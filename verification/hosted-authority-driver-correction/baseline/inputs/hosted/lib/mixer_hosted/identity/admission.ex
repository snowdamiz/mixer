defmodule MixerHosted.Identity.Admission do
  @moduledoc false
  # Reservations occur in ETS before the first message to the owner. Fixed slots
  # bound both a profile and this owner/process; no spawn occurs on overflow.
  def new(owner, entries, binding) do
    table = :ets.new(__MODULE__, [:set, :public, read_concurrency: true, write_concurrency: true])
    :ets.insert(table, {:configuration, Enum.uniq([binding | Map.keys(entries)]), binding})
    :persistent_term.put({__MODULE__, owner}, table)
    table
  end

  def configure(table, entries, binding),
    do: :ets.insert(table, {:configuration, Enum.uniq([binding | Map.keys(entries)]), binding})

  def acquire(owner, profile) do
    table = :persistent_term.get({__MODULE__, owner}, nil)
    admitted = System.monotonic_time(:millisecond)
    nonce = make_ref()

    with true <- table != nil,
         [{:configuration, ids, binding}] <- :ets.lookup(table, :configuration),
         id = if(profile == :configured, do: binding, else: profile),
         true <- id in ids,
         {:ok, g} <- reserve(table, :global, 128, nonce) do
      case reserve(table, id, 16, nonce) do
        {:ok, p} ->
          {:ok, {table, g, p, id, self(), admitted, nonce}}

        :error ->
          :ets.delete(table, g)
          {:error, :identity_unavailable}
      end
    else
      _ -> {:error, :identity_unavailable}
    end
  rescue
    ArgumentError -> {:error, :identity_unavailable}
  end

  defp reserve(table, id, n, nonce) do
    Enum.reduce_while(1..n, :error, fn i, _ ->
      k = {:slot, id, i}
      if :ets.insert_new(table, {k, self(), nonce}), do: {:halt, {:ok, k}}, else: {:cont, :error}
    end)
  end

  def valid?({t, g, p, id, pid, _admitted, nonce}, t, caller) do
    pid == caller and :ets.lookup(t, g) == [{g, pid, nonce}] and
      :ets.lookup(t, p) == [{p, pid, nonce}] and
      elem(p, 1) == id
  end

  def valid?(_, _, _), do: false

  def release({t, g, p, _, pid, _, nonce}) do
    for key <- [g, p] do
      :ets.delete_object(t, {key, pid, nonce})
    end

    :ok
  rescue
    ArgumentError -> :ok
  end

  def reap(table) do
    for {k, pid, nonce} <- :ets.tab2list(table),
        is_tuple(k),
        elem(k, 0) == :slot,
        not Process.alive?(pid),
        do: :ets.delete_object(table, {k, pid, nonce})
  end

  def close(owner), do: :persistent_term.erase({__MODULE__, owner})
end
