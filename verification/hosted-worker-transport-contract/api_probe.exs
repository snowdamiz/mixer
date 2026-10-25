# Dependency API probe only. No MixerHosted module or application is loaded.
defmodule WorkerTransportDependencyProbe do
  def run do
    Application.ensure_all_started(:mint)
    Application.ensure_all_started(:jason)
    duplicate = Jason.decode!(~s({"status":"running","status":"stopped"}),
      objects: :ordered_objects, strings: :copy)
    true = Enum.count(duplicate.values, fn {key, _} -> key == "status" end) == 2
    %{"counter" => 9_223_372_036_854_775_807} =
      Jason.decode!(~s({"counter":9223372036854775807}))

    {:ok, listener} = :gen_tcp.listen(0, [:binary, active: false, ip: {127, 0, 0, 1}, reuseaddr: true])
    {:ok, {{127, 0, 0, 1}, port}} = :inet.sockname(listener)
    body = Jason.encode!(%{"version" => 1, "operation" => "query", "nonce" => "synthetic"})
    owner = self()
    server = spawn_monitor(fn -> serve(listener, body, owner) end)
    try do
      {:ok, conn} = Mint.HTTP.connect(:http, {127, 0, 0, 1}, port,
        hostname: "worker-probe.invalid", protocols: [:http1], mode: :passive,
        transport_opts: [timeout: 1_000, send_timeout: 1_000, active: false])
      try do
        {:ok, conn, reference} = Mint.HTTP.request(conn, "POST", "/internal/mixer-build-worker/v1",
          [{"content-type", "application/json"}, {"accept-encoding", "identity"}, {"connection", "close"}], body)
        {conn, events} = receive_response(conn, reference, [])
        true = Enum.member?(events, {:status, reference, 200})
        true = Enum.member?(events, {:done, reference})
        response = for {:data, ^reference, data} <- events, into: "", do: data
        %{"status" => "absent"} = Jason.decode!(response)
        {:ok, _} = Mint.HTTP.close(conn)
        receive do
          {:probe_server_closed, ^owner} -> :ok
        after
          1_000 -> raise "server did not observe peer closure"
        end
      after
        Mint.HTTP.close(conn)
      end
      {pid, monitor} = server
      receive do
        {:DOWN, ^monitor, :process, ^pid, :normal} -> :ok
        {:DOWN, ^monitor, :process, ^pid, reason} -> raise "server failure: #{inspect(reason)}"
      after
        1_000 -> raise "server leaked"
      end
      IO.puts(Jason.encode!(%{
        scope: "dependency-api-only-plaintext-loopback-not-worker-or-TLS-qualification",
        elixir: System.version(), otp: List.to_string(:erlang.system_info(:otp_release)),
        erts: List.to_string(:erlang.system_info(:version)),
        mint: List.to_string(Application.spec(:mint, :vsn)),
        jason: List.to_string(Application.spec(:jason, :vsn)),
        duplicate_keys_preserved: true, signed_int64_preserved: true,
        mint_passive_post_response_and_close: true,
        loaded_mixer_modules: Enum.count(:code.all_loaded(), fn {m, _} -> String.starts_with?(Atom.to_string(m), "Elixir.MixerHosted") end),
        cleanup: "owned listener closed; server exited; probe VM exits"
      }))
    after
      :gen_tcp.close(listener)
      {pid, _} = server
      if Process.alive?(pid), do: Process.exit(pid, :kill)
    end
  end

  defp serve(listener, body, owner) do
    {:ok, socket} = :gen_tcp.accept(listener, 1_000)
    try do
      request = read_request(socket, "", body)
      true = String.starts_with?(request, "POST /internal/mixer-build-worker/v1 HTTP/1.1\r\n")
      response = ~s({"status":"absent"})
      :ok = :gen_tcp.send(socket, ["HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ",
        Integer.to_string(byte_size(response)), "\r\nConnection: close\r\n\r\n", response])
      {:error, :closed} = :gen_tcp.recv(socket, 0, 1_000)
      send(owner, {:probe_server_closed, owner})
    after
      :gen_tcp.close(socket)
    end
  end

  defp read_request(socket, bytes, body) when byte_size(bytes) <= 8_192 do
    if String.ends_with?(bytes, "\r\n\r\n" <> body) do
      bytes
    else
      {:ok, more} = :gen_tcp.recv(socket, 0, 1_000)
      read_request(socket, bytes <> more, body)
    end
  end

  defp receive_response(conn, reference, accumulated) do
    {:ok, conn, events} = Mint.HTTP.recv(conn, 0, 1_000)
    all = accumulated ++ events
    if Enum.member?(events, {:done, reference}), do: {conn, all}, else: receive_response(conn, reference, all)
  end
end

WorkerTransportDependencyProbe.run()
