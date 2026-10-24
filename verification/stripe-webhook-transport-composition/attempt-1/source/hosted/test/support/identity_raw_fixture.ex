defmodule MixerHosted.Identity.RawFixture do
  @moduledoc false
  use GenServer
  def start_link(_), do: GenServer.start_link(__MODULE__, [])
  def info(pid), do: GenServer.call(pid, :info)

  def init(options) do
    Process.flag(:trap_exit, true)

    {:ok, listener} =
      :gen_tcp.listen(0, [:binary, ip: {127, 0, 0, 1}, active: false, reuseaddr: true])

    {:ok, {_, port}} = :inet.sockname(listener)
    owner = self()
    mode = Keyword.get(options, :mode, :stall)
    acceptor = spawn_link(fn -> accept(listener, owner, mode) end)

    {:ok,
     %{
       listener: listener,
       port: port,
       acceptor: acceptor,
       sockets: %{},
       accepted: 0,
       closed: 0,
       max_active: 0
     }}
  end

  defp accept(listener, owner, mode) do
    case :gen_tcp.accept(listener, 100) do
      {:ok, socket} ->
        pid =
          spawn_link(fn ->
            receive do
              :go -> watch(socket, owner, mode)
            end
          end)

        :ok = :gen_tcp.controlling_process(socket, pid)
        send(owner, {:accepted, pid, socket})
        send(pid, :go)
        accept(listener, owner, mode)

      {:error, :timeout} ->
        accept(listener, owner, mode)

      _ ->
        :ok
    end
  end

  defp watch(socket, owner, :plaintext) do
    :gen_tcp.send(socket, "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}")
    :gen_tcp.close(socket)
    send(owner, {:closed, self(), System.monotonic_time(:millisecond)})
  end

  defp watch(socket, owner, :stall), do: watch(socket, owner)

  defp watch(socket, owner) do
    case :gen_tcp.recv(socket, 0, 3_000) do
      {:ok, _client_hello} -> watch(socket, owner)
      {:error, :closed} -> send(owner, {:closed, self(), System.monotonic_time(:millisecond)})
      _ -> :ok
    end

    :gen_tcp.close(socket)
  end

  def handle_call(:info, _, s), do: {:reply, Map.drop(s, [:listener, :acceptor, :sockets]), s}

  def handle_info({:accepted, pid, socket}, s),
    do:
      {:noreply,
       %{
         s
         | accepted: s.accepted + 1,
           sockets: Map.put(s.sockets, pid, socket),
           max_active: max(s.max_active, map_size(s.sockets) + 1)
       }}

  def handle_info({:closed, pid, time}, s),
    do:
      {:noreply,
       s
       |> Map.put(:last_close_mono, time)
       |> Map.put(:closed, s.closed + 1)
       |> Map.put(:sockets, Map.delete(s.sockets, pid))}

  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}

  def terminate(_, s) do
    :gen_tcp.close(s.listener)
    Process.exit(s.acceptor, :kill)

    Enum.each(s.sockets, fn {pid, socket} ->
      :gen_tcp.close(socket)
      Process.exit(pid, :kill)
    end)
  end
end
