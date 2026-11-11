defmodule MixerHosted.BrowserCommitProxySocketTest do
  use ExUnit.Case, async: false

  test "both live proxy TCP sockets use nodelay" do
    {:ok, listener} = :gen_tcp.listen(0, [:binary, active: false, ip: {127, 0, 0, 1}])
    on_exit(fn -> :gen_tcp.close(listener) end)
    {:ok, {_, backend_port}} = :inet.sockname(listener)
    proxy = start_supervised!({R932.PhaseCommitProxy, backend_port})
    proxy_port = GenServer.call(proxy, :port)
    {:ok, client} = :gen_tcp.connect({127, 0, 0, 1}, proxy_port, [:binary, active: false], 2000)
    on_exit(fn -> :gen_tcp.close(client) end)
    {:ok, backend} = :gen_tcp.accept(listener, 2000)
    on_exit(fn -> :gen_tcp.close(backend) end)
    {:ok, client_endpoint} = :inet.sockname(client)
    {:ok, backend_endpoint} = :inet.sockname(backend)
    acceptor = :sys.get_state(proxy).acceptor
    {:links, links} = Process.info(acceptor, :links)
    [worker] = Enum.filter(links, &(is_pid(&1) and &1 != proxy))
    worker_monitor = Process.monitor(worker)
    {:links, worker_links} = Process.info(worker, :links)
    sockets = Enum.filter(worker_links, &is_port/1)
    assert length(sockets) == 2

    options =
      Map.new(sockets, fn socket ->
        {:ok, peer} = :inet.peername(socket)
        role = if peer == client_endpoint, do: :frontend, else: :backend
        assert peer in [client_endpoint, backend_endpoint]
        {:ok, [nodelay: enabled]} = :inet.getopts(socket, [:nodelay])
        {role, enabled}
      end)

    try do
      assert options == %{frontend: true, backend: true}
      IO.inspect(options, label: "R1050_ACTUAL_SOCKET_OPTIONS")
    after
      # Complete the real proxy startup framing before orderly EOF cleanup.
      :ok = :gen_tcp.send(client, <<8::32, 196_608::32>>)
      {:ok, <<8::32, 196_608::32>>} = :gen_tcp.recv(backend, 8, 2000)
      :ok = :gen_tcp.close(client)
      assert_receive {:DOWN, ^worker_monitor, :process, ^worker, :normal}, 2000
      :ok = :gen_tcp.close(backend)
    end
  end
end
