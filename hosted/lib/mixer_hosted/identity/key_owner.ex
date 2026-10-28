defmodule MixerHosted.Identity.KeyOwner do
  @moduledoc "Owns configured trust generations, bounded refresh flights and final verification fences."
  use GenServer
  alias MixerHosted.Identity.{Admission, Encoding, FetchFlight, Manifest, TrustSnapshot}

  defmodule Lease do
    @moduledoc false
    @enforce_keys [:epoch, :generation, :id, :snapshot_generation, :snapshot, :permit]
    defstruct @enforce_keys
  end

  @allowed ~w(name manifest generation binding ca_roots resolvers worker_supervisor)a
  def start_link(options),
    do: GenServer.start_link(__MODULE__, options, name: Keyword.get(options, :name, __MODULE__))

  def child_spec(options),
    do: %{id: __MODULE__, start: {__MODULE__, :start_link, [options]}, shutdown: :infinity}

  if Mix.env() == :test do
    def start_fixture(options),
      do:
        GenServer.start_link(__MODULE__, {:fixture, options},
          name: Keyword.fetch!(options, :name)
        )
  end

  def release(owner, permit), do: safe_call(owner, {:release, permit}, 2_200)
  def checkout(owner, permit, now), do: safe_call(owner, {:checkout, permit, now}, 2_200)
  def finish(owner, lease), do: safe_call(owner, {:finish, lease}, 2_200)

  def note_unknown(owner, lease, kid),
    do: safe_call(owner, {:unknown, lease, kid, System.monotonic_time(:millisecond)}, 2_200)

  def replace_manifest(owner, expected, candidate),
    do: safe_call(owner, {:replace, expected, candidate}, 2_200)

  defp safe_call(owner, message, timeout) do
    GenServer.call(owner, message, timeout)
  catch
    :exit, _ -> {:error, :identity_unavailable}
  end

  if Mix.env() == :test do
    def init({:fixture, options}),
      do: initialize(Keyword.delete(options, :fixture), Keyword.fetch!(options, :fixture))
  end

  def init(options), do: initialize(options, nil)

  defp initialize(options, fixture) do
    Process.flag(:trap_exit, true)

    with true <- Keyword.keyword?(options) and Enum.all?(Keyword.keys(options), &(&1 in @allowed)),
         {:ok, entries} <- Manifest.validate(Keyword.get(options, :manifest)),
         binding when is_binary(binding) <- Keyword.get(options, :binding),
         true <- Map.has_key?(entries, binding),
         roots when is_list(roots) and roots != [] <- Keyword.get(options, :ca_roots),
         true <- Enum.all?(roots, &ca_root?/1),
         resolvers when is_list(resolvers) and resolvers != [] and length(resolvers) <= 3 <-
           Keyword.get(options, :resolvers),
         true <- Enum.all?(resolvers, &resolver?/1),
         generation when is_integer(generation) and generation > 0 <-
           Keyword.get(options, :generation),
         workers when is_atom(workers) <- Keyword.get(options, :worker_supervisor) do
      name = Keyword.get(options, :name, __MODULE__)
      table = Admission.new(name, entries, binding)
      config = %{ca_roots: roots, resolvers: resolvers}
      config = if fixture, do: Map.put(config, :fixture, fixture), else: config
      Process.send_after(self(), :reap, 1_000)

      {:ok,
       %{
         name: name,
         entries: entries,
         history: Map.new(entries, fn {id, entry} -> {id, %{entry: entry, retired: false}} end),
         binding: binding,
         generation: generation,
         epoch: make_ref(),
         table: table,
         configuration: config,
         workers: workers,
         snapshots: %{},
         attempts: %{},
         tombstones: %{},
         flights: %{},
         waiters: %{},
         admitted: %{},
         negatives: %{},
         sequence: 0,
         clock: clock(),
         clock_valid: true
       }}
    else
      _ -> {:stop, :invalid_identity_configuration}
    end
  end

  defp ca_root?(der) when is_binary(der) do
    :public_key.pkix_decode_cert(der, :otp)
    true
  rescue
    _ -> false
  end

  defp ca_root?(_), do: false

  defp resolver?({ip, port}),
    do: is_tuple(ip) and tuple_size(ip) in [4, 8] and is_integer(port) and port in 1..65535

  defp resolver?(_), do: false

  def handle_call({:checkout, permit, now}, from, s) do
    s = sample_clock(s)
    caller = elem(from, 0)

    if Admission.valid?(permit, s.table, caller) do
      id = elem(permit, 3)
      {s, _} = monitor_permit(s, permit, caller)

      cond do
        s.entries[id] == nil or not s.entries[id].profile.enabled ->
          {:reply, {:error, :unauthenticated}, s}

        not Encoding.numeric_date?(now) or abs(now * 1_000 - elem(s.clock, 0)) > 1_000 ->
          {:reply, {:error, :identity_unavailable}, s}

        fresh?(s, id, now) ->
          {:reply, {:ok, lease(s, id, permit)}, s}

        true ->
          case ensure_flight(s, id, elem(permit, 5), :required) do
            {:ok, s, pid, deadline} ->
              timer =
                Process.send_after(
                  self(),
                  {:waiter_timeout, permit},
                  max(0, deadline - elem(s.clock, 1))
                )

              {:noreply,
               put_in(s.waiters[permit], %{
                 from: from,
                 id: id,
                 flight: pid,
                 timer: timer,
                 now: now
               })}

            {:error, s} ->
              {:reply, {:error, :identity_unavailable}, s}
          end
      end
    else
      {:reply, {:error, :identity_unavailable}, s}
    end
  end

  def handle_call({:finish, %Lease{} = l}, from, s) do
    s = sample_clock(s)

    result =
      cond do
        not Admission.valid?(l.permit, s.table, elem(from, 0)) ->
          {:error, :identity_unavailable}

        s.entries[l.id] == nil or not s.entries[l.id].profile.enabled ->
          {:error, :unauthenticated}

        not current?(s, l) ->
          {:error, :retry_current}

        not fresh?(s, l.id, div(elem(s.clock, 0), 1_000)) ->
          {:error, :identity_unavailable}

        true ->
          :ok
      end

    {:reply, result, s}
  end

  def handle_call({:unknown, %Lease{} = l, kid, requested}, from, s) do
    s = sample_clock(s)

    if Admission.valid?(l.permit, s.table, elem(from, 0)) and current?(s, l) and
         Encoding.bounded_string?(kid, 128) and
         fresh?(s, l.id, div(elem(s.clock, 0), 1_000)) and
         TrustSnapshot.key(l.snapshot, kid) == :error do
      now = elem(s.clock, 1)
      neg = Map.get(s.negatives, l.id, %{}) |> Map.reject(fn {_, v} -> v.expires <= now end)

      if Map.has_key?(neg, kid) do
        {:reply, :ok, put_in(s.negatives[l.id], neg)}
      else
        neg =
          if map_size(neg) >= 128 do
            {old, _} = Enum.min_by(neg, fn {k, v} -> {v.sequence, k} end)
            Map.delete(neg, old)
          else
            neg
          end

        seq = s.sequence + 1

        neg =
          Map.put(neg, kid, %{
            sequence: seq,
            generation: l.snapshot_generation,
            expires: min(now + 30_000, s.snapshots[l.id].expires_mono)
          })

        s = %{s | sequence: seq, negatives: Map.put(s.negatives, l.id, neg)}

        s =
          case ensure_flight(s, l.id, requested, :background) do
            {:ok, s, _, _} -> s
            {:error, s} -> s
          end

        {:reply, :ok, s}
      end
    else
      {:reply, :ok, s}
    end
  end

  def handle_call({:replace, expected, candidate}, _from, s) do
    s = sample_clock(s)
    now = elem(s.clock, 1)
    tombs = Map.reject(s.tombstones, fn {_, v} -> v.expires <= now end)

    with true <- expected == s.generation,
         {:ok, entries} <- Manifest.validate(candidate),
         true <- Manifest.transition(s.history, entries),
         history =
           Map.new(s.history, fn {id, value} ->
             {id, %{value | retired: not Map.has_key?(entries, id)}}
           end),
         history =
           Map.merge(
             history,
             Map.new(entries, fn {id, entry} -> {id, %{entry: entry, retired: false}} end)
           ),
         true <- map_size(history) <= 16,
         removed = Map.drop(s.entries, Map.keys(entries)),
         tombs =
           Enum.reduce(removed, tombs, fn {id, entry}, acc ->
             Map.put(acc, id, %{entry: entry, expires: now + 30_000})
           end),
         tombs = Map.drop(tombs, Map.keys(entries)),
         true <- map_size(tombs) + map_size(entries) <= 16 do
      changed = for {id, e} <- s.entries, entries[id] != e, do: id

      Enum.each(s.flights, fn {pid, f} -> if f.id in changed, do: send(pid, :cancel) end)

      snapshots = Map.drop(s.snapshots, changed)
      neg = Map.drop(s.negatives, changed)
      attempts = Map.take(s.attempts, Map.keys(entries) ++ Map.keys(tombs))

      Admission.configure(
        s.table,
        Map.merge(entries, Map.new(tombs, fn {id, v} -> {id, v.entry} end)),
        s.binding
      )

      {:reply, {:ok, s.generation + 1},
       %{
         s
         | entries: entries,
           history: history,
           generation: s.generation + 1,
           tombstones: tombs,
           snapshots: snapshots,
           negatives: neg,
           attempts: attempts
       }}
    else
      _ -> {:reply, {:error, :invalid_manifest}, s}
    end
  end

  def handle_call({:release, permit}, from, s) do
    if Admission.valid?(permit, s.table, elem(from, 0)),
      do: {:reply, :ok, drop_permit(s, permit)},
      else: {:reply, :ok, s}
  end

  def handle_call(_, _, s), do: {:reply, {:error, :identity_unavailable}, s}

  defp monitor_permit(s, permit, pid) do
    if s.admitted[permit] do
      {s, s.admitted[permit]}
    else
      ref = Process.monitor(pid)
      {%{s | admitted: Map.put(s.admitted, permit, ref)}, ref}
    end
  end

  defp ensure_flight(s, id, admitted, mode) do
    case Enum.find(s.flights, fn {_, f} -> f.id == id end) do
      {pid, f} ->
        {:ok, s, pid, f.deadline}

      nil ->
        now = elem(s.clock, 1)

        if map_size(s.flights) < 4 and admitted + 2_000 > now and
             now - Map.get(s.attempts, id, now - 30_000) >= 30_000 do
          deadline = admitted + 2_000

          opts = %{
            owner: self(),
            entry: s.entries[id],
            deadline: deadline,
            configuration: s.configuration
          }

          s = put_in(s.attempts[id], now)

          case DynamicSupervisor.start_child(s.workers, {FetchFlight, opts}) do
            {:ok, pid} ->
              ref = Process.monitor(pid)

              f = %{
                id: id,
                generation: s.generation,
                epoch: s.epoch,
                entry: s.entries[id],
                deadline: deadline,
                monitor: ref,
                result: nil,
                mode: mode
              }

              {:ok, put_in(s.flights[pid], f), pid, deadline}

            _ ->
              {:error, s}
          end
        else
          {:error, s}
        end
    end
  end

  def handle_info({:flight_result, pid, result}, s) do
    if s.flights[pid], do: {:noreply, put_in(s.flights[pid].result, result)}, else: {:noreply, s}
  end

  def handle_info({:DOWN, ref, :process, pid, _}, s) do
    cond do
      s.flights[pid] && s.flights[pid].monitor == ref ->
        s = sample_clock(s)
        f = s.flights[pid]
        s = publish(s, f)
        s = %{s | flights: Map.delete(s.flights, pid)}
        {done, rest} = Enum.split_with(s.waiters, fn {_, w} -> w.flight == pid end)

        Enum.each(done, fn {permit, w} ->
          Process.cancel_timer(w.timer)

          result =
            cond do
              s.entries[w.id] == nil or not s.entries[w.id].profile.enabled ->
                {:error, :unauthenticated}

              fresh?(s, w.id, div(elem(s.clock, 0), 1_000)) ->
                {:ok, lease(s, w.id, permit)}

              true ->
                {:error, :identity_unavailable}
            end

          GenServer.reply(w.from, result)
        end)

        {:noreply, %{s | waiters: Map.new(rest)}}

      true ->
        permits = for {permit, r} <- s.admitted, r == ref, do: permit
        s = Enum.reduce(permits, s, fn p, acc -> drop_permit(acc, p) end)
        {:noreply, s}
    end
  end

  def handle_info({:waiter_timeout, permit}, s) do
    case s.waiters[permit] do
      nil ->
        {:noreply, s}

      w ->
        error =
          if s.entries[w.id] == nil or not s.entries[w.id].profile.enabled,
            do: :unauthenticated,
            else: :identity_unavailable

        GenServer.reply(w.from, {:error, error})
        send(w.flight, :cancel)
        {:noreply, %{s | waiters: Map.delete(s.waiters, permit)}}
    end
  end

  def handle_info(:reap, s) do
    Admission.reap(s.table)
    released = for {p, _} <- s.admitted, not Admission.valid?(p, s.table, elem(p, 4)), do: p
    s = Enum.reduce(released, s, &drop_permit(&2, &1))
    Process.send_after(self(), :reap, 1_000)
    {:noreply, s}
  end

  def handle_info(_, s), do: {:noreply, s}

  defp drop_permit(s, p) do
    if s.admitted[p], do: Process.demonitor(s.admitted[p], [:flush])
    Admission.release(p)
    waiter = s.waiters[p]
    if waiter, do: Process.cancel_timer(waiter.timer)
    s = %{s | admitted: Map.delete(s.admitted, p), waiters: Map.delete(s.waiters, p)}

    if ((waiter != nil and s.flights[waiter.flight] != nil) &&
          s.flights[waiter.flight].mode == :required) and
         not Enum.any?(s.waiters, fn {_, w} -> w.flight == waiter.flight end),
       do: send(waiter.flight, :cancel)

    s
  end

  defp publish(s, %{result: {:ok, snapshot, meta}} = f) do
    now = elem(s.clock, 1)

    if s.clock_valid and now < f.deadline and now < meta.expires_mono and
         f.generation == s.generation and f.epoch == s.epoch and s.entries[f.id] == f.entry and
         f.entry.profile.enabled do
      generation = make_ref()
      record = %{snapshot: snapshot, generation: generation, expires_mono: meta.expires_mono}

      %{
        s
        | snapshots: Map.put(s.snapshots, f.id, record),
          negatives: Map.delete(s.negatives, f.id)
      }
    else
      s
    end
  end

  defp publish(s, _), do: s

  defp lease(s, id, permit),
    do: %Lease{
      epoch: s.epoch,
      generation: s.generation,
      id: id,
      snapshot_generation: s.snapshots[id].generation,
      snapshot: s.snapshots[id].snapshot,
      permit: permit
    }

  defp current?(s, l),
    do:
      l.epoch == s.epoch and l.generation == s.generation and s.snapshots[l.id] != nil and
        s.snapshots[l.id].generation == l.snapshot_generation

  defp fresh?(s, id, now),
    do:
      s.clock_valid and s.snapshots[id] != nil and elem(s.clock, 1) < s.snapshots[id].expires_mono and
        TrustSnapshot.status(s.snapshots[id].snapshot, now) == :fresh

  defp sample_clock(s) do
    {wall, mono} = now = clock()
    {old_wall, old_mono} = s.clock
    stable = mono >= old_mono and abs(wall - old_wall - (mono - old_mono)) <= 1_000

    if stable do
      %{s | clock: now, clock_valid: true}
    else
      Enum.each(s.flights, fn {pid, _} -> send(pid, :cancel) end)

      %{
        s
        | clock: now,
          clock_valid: false,
          snapshots: %{},
          negatives: %{},
          epoch: make_ref()
      }
    end
  end

  defp clock, do: {System.system_time(:millisecond), System.monotonic_time(:millisecond)}

  def terminate(_, s) do
    Admission.close(s.name, s.table)

    Enum.each(s.waiters, fn {_, w} -> GenServer.reply(w.from, {:error, :identity_unavailable}) end)

    workers = s.workers

    Enum.each(s.flights, fn {pid, f} ->
      try do
        DynamicSupervisor.terminate_child(workers, pid)
      catch
        :exit, {:noproc, {GenServer, :call, [^workers, {:terminate_child, ^pid}, :infinity]}} ->
          :ok
      end

      # A dead worker supervisor cannot acknowledge cleanup. The exact flight's
      # existing monitor still gates owner exit and one_for_all replacement.
      receive do
        {:DOWN, ref, :process, ^pid, _} when ref == f.monitor -> :ok
      end
    end)
  end
end
