defmodule R932.PhaseCommitProxy do
  @moduledoc false
  use GenServer
  def start_link(port), do: GenServer.start_link(__MODULE__, port)

  def init(port) do
    {:ok, listener} =
      :gen_tcp.listen(0, [
        :binary,
        active: false,
        nodelay: true,
        ip: {127, 0, 0, 1},
        reuseaddr: true
      ])

    {:ok, {_, proxy_port}} = :inet.sockname(listener)
    owner = self()
    acceptor = spawn_link(fn -> accept(listener, port, owner) end)
    {:ok, %{listener: listener, acceptor: acceptor, port: proxy_port, armed: nil}}
  end

  def handle_call(:port, _, s), do: {:reply, s.port, s}
  def handle_call({:arm, parent}, _, s), do: {:reply, :ok, %{s | armed: {2, parent}}}

  def handle_call({:arm_activation, mode, parent}, _, s),
    do: {:reply, :ok, %{s | armed: {:activation, mode, parent}}}

  def handle_call({:commit, true, backend}, _, %{armed: {:activation, mode, parent}} = s) do
    send(parent, {:final_activation_commit, backend, mode})
    {:reply, {mode, parent}, %{s | armed: nil}}
  end

  def handle_call({:commit, _, _}, from, s), do: handle_call(:commit, from, s)

  def handle_call(:commit, _, %{armed: {1, parent}} = s),
    do: {:reply, {:abort, parent}, %{s | armed: nil}}

  def handle_call(:commit, _, %{armed: {n, p}} = s) when is_integer(n),
    do: {:reply, :forward, %{s | armed: {n - 1, p}}}

  def handle_call(:commit, _, s), do: {:reply, :forward, s}

  def terminate(_, s) do
    :gen_tcp.close(s.listener)
    Process.exit(s.acceptor, :shutdown)
  end

  defp accept(listener, port, owner) do
    case :gen_tcp.accept(listener) do
      {:ok, client} ->
        worker =
          spawn_link(fn ->
            receive do
              :go -> connection(client, port, owner)
            end
          end)

        :ok = :gen_tcp.controlling_process(client, worker)
        send(worker, :go)
        accept(listener, port, owner)

      _ ->
        :ok
    end
  end

  defp connection(client, port, owner) do
    {:ok, backend} =
      :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false, nodelay: true], 2000)

    {:ok, <<len::32>>} = :gen_tcp.recv(client, 4, 5000)
    {:ok, startup} = :gen_tcp.recv(client, len - 4, 5000)
    :ok = :gen_tcp.send(backend, [<<len::32>>, startup])
    table = :ets.new(:proxy_connection, [:public])
    reader = spawn_link(fn -> backend(backend, client, table) end)

    try do
      frontend(client, backend, owner, table)
    after
      Process.unlink(reader)
      Process.exit(reader, :shutdown)
      :gen_tcp.close(client)
      :gen_tcp.close(backend)
    end
  end

  defp frame(socket) do
    with {:ok, <<tag, len::32>>} <- :gen_tcp.recv(socket, 5, 10000),
         true <- len >= 4 and len <= 1_048_576,
         {:ok, payload} <- payload(socket, len - 4),
         do: {:ok, tag, payload}
  end

  defp payload(_, 0), do: {:ok, ""}
  defp payload(socket, size), do: :gen_tcp.recv(socket, size, 10000)

  defp send_frame(socket, tag, payload),
    do: :gen_tcp.send(socket, <<tag, byte_size(payload) + 4::32, payload::binary>>)

  defp frontend(client, backend, owner, table) do
    case frame(client) do
      {:ok, ?Q, "COMMIT" <> _ = payload} ->
        activated = :ets.lookup(table, :activation_executed) == [{:activation_executed, true}]

        backend_id =
          case :ets.lookup(table, :backend_id) do
            [{:backend_id, id}] -> id
            [] -> nil
          end

        case GenServer.call(owner, {:commit, activated, backend_id}) do
          {:abort, parent} ->
            :ets.insert(table, {:abort, payload, parent})
            send_frame(backend, ?Q, "SELECT 1/0\0")

          {:barrier, parent} ->
            :ets.insert(table, {:ack_barrier, parent})
            send(parent, {:activation_barrier, self(), backend_id})

            receive do
              :release_commit -> send_frame(backend, ?Q, payload)
            after
              1500 -> raise "final activation barrier not released"
            end

          :forward ->
            send_frame(backend, ?Q, payload)
        end

        frontend(client, backend, owner, table)

      {:ok, ?P, payload} ->
        [statement, sql | _] = :binary.split(payload, <<0>>, [:global])
        # Match only the actual activation function, never prepare_activation.
        :ets.insert(
          table,
          {{:statement, statement},
           String.starts_with?(sql, "SELECT public.mixer_browser_activate(")}
        )

        send_frame(backend, ?P, payload)
        frontend(client, backend, owner, table)

      {:ok, ?B, payload} ->
        [portal, statement | _] = :binary.split(payload, <<0>>, [:global])
        active = :ets.lookup(table, {:statement, statement}) == [{{:statement, statement}, true}]
        :ets.insert(table, {{:portal, portal}, active})
        send_frame(backend, ?B, payload)
        frontend(client, backend, owner, table)

      {:ok, ?E, payload} ->
        [portal | _] = :binary.split(payload, <<0>>, [:global])
        active = :ets.lookup(table, {:portal, portal}) == [{{:portal, portal}, true}]
        if active, do: :ets.insert(table, {:activation_executing, true})
        send_frame(backend, ?E, payload)
        frontend(client, backend, owner, table)

      {:ok, tag, payload} ->
        send_frame(backend, tag, payload)
        frontend(client, backend, owner, table)

      _ ->
        :ok
    end
  end

  defp backend(socket, client, table) do
    case frame(socket) do
      {:ok, tag, payload} ->
        if tag == ?K do
          <<id::32, _key::32>> = payload
          :ets.insert(table, {:backend_id, id})
        end

        if tag == ?C and payload == "SELECT 1\0" and
             :ets.lookup(table, :activation_executing) == [{:activation_executing, true}] do
          :ets.delete(table, :activation_executing)
          :ets.insert(table, {:activation_executed, true})
        end

        if tag == ?Z and payload == "I", do: :ets.delete(table, :activation_executed)

        case {:ets.lookup(table, :ack_barrier), tag, payload} do
          {[{:ack_barrier, parent}], ?C, "COMMIT\0"} ->
            :ets.delete(table, :ack_barrier)
            send(parent, {:committed_barrier, self()})

            receive do
              :release_ack -> :ok
            after
              1500 -> raise "activation acknowledgement not released"
            end

          _ ->
            :ok
        end

        case :ets.lookup(table, :abort) do
          [{:abort, commit, parent}] ->
            if tag == ?Z do
              send(parent, {:activation_aborted, payload == "E"})
              :ets.delete(table, :abort)
              :ets.insert(table, {:commit_probe, parent})
              send_frame(socket, ?Q, commit)
            end

          [] ->
            case {:ets.lookup(table, :commit_probe), tag, payload} do
              {[{:commit_probe, parent}], ?C, "ROLLBACK\0"} ->
                send(parent, :actual_commit_rolled_back)
                :ets.delete(table, :commit_probe)

              _ ->
                :ok
            end

            send_frame(client, tag, payload)
        end

        backend(socket, client, table)

      _ ->
        :gen_tcp.close(client)
    end
  end
end
