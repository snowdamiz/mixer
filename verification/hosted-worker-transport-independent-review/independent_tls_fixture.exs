defmodule IndependentWorkerTLS do
  use GenServer
  def start(material, recipient, behavior), do: GenServer.start(__MODULE__, {material, recipient, behavior})
  def info(pid), do: GenServer.call(pid, :info)
  def response(request, observation \\ %{"status" => "absent"}) do
    request |> Map.drop(["spec", "deadline_ms"]) |> Map.put("observation", observation) |> Jason.encode!() |> response_body()
  end
  def response_body(body, extra_headers \\ ""), do: "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: #{byte_size(body)}\r\nConnection: close\r\n" <> extra_headers <> "\r\n" <> body
  def init({m, recipient, behavior}) do
    Process.flag(:trap_exit, true)
    {:ok, listener} = :ssl.listen(0, [:binary, active: false, backlog: 64, ip: {127,0,0,1}, cert: m.cert, key: m.key, reuseaddr: true, versions: [:"tlsv1.2", :"tlsv1.3"], alpn_preferred_protocols: ["http/1.1"]])
    {:ok, {_, port}} = :ssl.sockname(listener)
    owner = self()
    tag = make_ref()
    acceptor = spawn_link(fn -> accept(listener, owner, recipient, behavior, tag) end)
    {:ok, %{listener: listener, port: port, acceptor: acceptor, tag: tag, active: %{}, accepted: 0, retired: 0}}
  end
  def handle_call(:info, _, s), do: {:reply, Map.take(s, [:port, :tag, :active, :accepted, :retired]), s}
  def handle_info({:accepted, handler}, s), do: {:noreply, %{s | accepted: s.accepted + 1, active: Map.put(s.active, handler, Process.monitor(handler))}}
  def handle_info({:DOWN, ref, :process, pid, _}, s) do
    if s.active[pid] == ref, do: {:noreply, %{s | active: Map.delete(s.active, pid), retired: s.retired + 1}}, else: {:noreply, s}
  end
  def handle_info(_, s), do: {:noreply, s}
  def terminate(_, s) do
    :ssl.close(s.listener)
    Process.exit(s.acceptor, :kill)
    Enum.each(Map.keys(s.active), &Process.exit(&1, :kill))
  end
  defp accept(listener, owner, recipient, behavior, tag) do
    case :ssl.transport_accept(listener, 200) do
      {:ok, socket} ->
        handler = spawn_link(fn -> receive do :go -> serve(socket, recipient, behavior, tag) end end)
        :ok = :ssl.controlling_process(socket, handler)
        send(owner, {:accepted, handler})
        send(handler, :go)
        accept(listener, owner, recipient, behavior, tag)
      {:error, :timeout} -> accept(listener, owner, recipient, behavior, tag)
      _ -> :ok
    end
  end
  defp serve(socket, recipient, behavior, tag) do
    try do
      if behavior == :handshake_barrier do
        send(recipient, {:handshake, tag, self()})
        receive do :handshake -> :ok after 6_000 -> :ok end
      end
      with {:ok, socket} <- :ssl.handshake(socket, 6_000), {:ok, headers, body} <- request(socket, "") do
        value = Jason.decode!(body)
        send(recipient, {:request, tag, self(), value, headers, headers <> "\r\n\r\n" <> body})
        raw = response(value)
        case behavior do
          :hold -> :ssl.recv(socket, 1, 6_000)
          :handshake_barrier -> :ssl.send(socket, raw)
          fun when is_function(fun, 5) -> fun.(socket, value, raw, recipient, tag)
        end
      end
    after
      :ssl.close(socket)
    end
  end
  defp request(socket, bytes) when byte_size(bytes) <= 24_576 do
    case :binary.split(bytes, "\r\n\r\n") do
      [headers, body] ->
        [_, length] = Regex.run(~r/\r\ncontent-length: ([0-9]+)\r?\n/i, headers <> "\r\n")
        if byte_size(body) == String.to_integer(length), do: {:ok, headers, body}, else: more(socket, bytes)
      _ -> more(socket, bytes)
    end
  end
  defp request(_, _), do: :error
  defp more(socket, bytes) do
    case :ssl.recv(socket, 0, 6_000) do
      {:ok, chunk} -> request(socket, bytes <> chunk)
      _ -> :error
    end
  end
end
