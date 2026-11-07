defmodule MixerHosted.Identity.SocketProbe do
  @moduledoc false
  use GenServer
  # Test instrumentation is intentionally tied to the installed OTP29 sslsocket
  # record for measurement only; no product code reads that opaque record.
  def start_link(_), do: GenServer.start_link(__MODULE__, [])
  def info(pid), do: GenServer.call(pid, :info)

  def init(_) do
    Process.send_after(self(), :sample, 1)

    {:ok,
     %{
       sockets: %{},
       seen: 0,
       closed: 0,
       max_active: 0,
       max_ssl_memory: 0,
       max_ssl_binary_bytes: 0,
       max_ssl_mailbox: 0,
       max_socket_recbuf: 0,
       max_transport_buffer: 0
     }}
  end

  def handle_info({:register_raw_socket, worker, _socket, ref}, s) do
    send(worker, {ref, :ok})
    {:noreply, s}
  end

  def handle_info({:register_connection, worker, _raw, _pid, ref}, s) do
    send(worker, {ref, :ok})
    {:noreply, s}
  end

  def handle_info({:register_socket, worker, socket, ref}, s) do
    Process.monitor(worker)
    send(worker, {ref, :ok})

    s = %{
      s
      | sockets: Map.put(s.sockets, worker, socket),
        seen: s.seen + 1,
        max_active: max(s.max_active, map_size(s.sockets) + 1)
    }

    {:noreply, sample(s)}
  end

  def handle_info(:sample, s) do
    Process.send_after(self(), :sample, 1)
    {:noreply, sample(s)}
  end

  def handle_info({:DOWN, _, :process, worker, _}, s) do
    socket = s.sockets[worker]

    closed =
      case :ssl.peername(socket) do
        {:error, _} -> 1
        _ -> 0
      end

    {:noreply, %{s | sockets: Map.delete(s.sockets, worker), closed: s.closed + closed}}
  end

  def handle_call(:info, _, s), do: {:reply, Map.delete(sample(s), :sockets), s}

  defp sample(s) do
    Enum.reduce(s.sockets, s, fn {_, socket}, acc ->
      pids = [elem(socket, 2), elem(socket, 3)]

      acc =
        Enum.reduce(pids, acc, fn pid, a ->
          case Process.info(pid, [:memory, :binary, :message_queue_len]) do
            nil ->
              a

            info ->
              bytes = Enum.reduce(info[:binary], 0, fn {_, n, _}, total -> total + n end)

              %{
                a
                | max_ssl_memory: max(a.max_ssl_memory, info[:memory]),
                  max_ssl_binary_bytes: max(a.max_ssl_binary_bytes, bytes),
                  max_ssl_mailbox: max(a.max_ssl_mailbox, info[:message_queue_len])
              }
          end
        end)

      recbuf =
        case :ssl.getopts(socket, [:recbuf]) do
          {:ok, [recbuf: n]} -> n
          _ -> 0
        end

      buffer =
        case :inet.getopts(elem(socket, 1), [:buffer]) do
          {:ok, [buffer: n]} -> n
          _ -> 0
        end

      %{
        acc
        | max_socket_recbuf: max(acc.max_socket_recbuf, recbuf),
          max_transport_buffer: max(acc.max_transport_buffer, buffer)
      }
    end)
  rescue
    _ -> s
  end
end
