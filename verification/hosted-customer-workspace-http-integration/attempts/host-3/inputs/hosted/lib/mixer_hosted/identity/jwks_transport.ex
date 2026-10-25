defmodule MixerHosted.Identity.JWKSTransport do
  @moduledoc false
  alias MixerHosted.Identity.{BoundedTCP, DNSResolver, HTTPFreshness, HTTPWireGuard}

  @headers [
    {"accept", "application/jwk-set+json, application/json"},
    {"accept-encoding", "identity"},
    {"connection", "close"}
  ]
  def fetch(entry, deadline, configuration, watcher) do
    with {:ok, ip} <-
           DNSResolver.resolve(entry.jwks_endpoint.host, configuration.resolvers, deadline) do
      connect(entry, ip, entry.jwks_endpoint.port, deadline, configuration.ca_roots, watcher)
    end
  end

  # These functions do not exist in production BEAMs. Only fixture ports and
  # destination selection change; certificate/hostname validation stays enabled.
  if Mix.env() == :test do
    def fetch_fixture(entry, ip, port, deadline, roots, watcher),
      do: connect(entry, ip, port, deadline, roots, watcher)
  end

  defp connect(entry, ip, port, deadline, roots, watcher) do
    BoundedTCP.with_watchdog(watcher, deadline, fn ->
      do_connect(entry, ip, port, deadline, roots, watcher)
    end)
  end

  defp do_connect(entry, ip, port, deadline, roots, watcher) do
    host = entry.jwks_endpoint.host

    opts = [
      hostname: host,
      protocols: [:http1],
      mode: :passive,
      max_header_list_size: 10_240,
      transport_opts: [
        cb_info: {BoundedTCP, :tcp, :tcp_closed, :tcp_error, :tcp_passive},
        verify: :verify_peer,
        cacerts: roots,
        timeout: remaining(deadline),
        send_timeout: remaining(deadline),
        send_timeout_close: true,
        versions: [:"tlsv1.2", :"tlsv1.3"],
        recbuf: 16_384,
        buffer: 16_384,
        inet4: tuple_size(ip) == 4,
        inet6: tuple_size(ip) == 8,
        max_handshake_size: 65_536
      ]
    ]

    with {:ok, conn} <- Mint.HTTP.connect(:https, ip, port, opts) do
      socket = Mint.HTTP.get_socket(conn)

      try do
        with :ok <- register_socket(watcher, socket, deadline),
             {:ok, {^ip, ^port}} <- :ssl.peername(socket),
             request_clock = clock(),
             {:ok, conn, ref} <-
               Mint.HTTP.request(conn, "GET", entry.jwks_endpoint.path, @headers, nil),
             {:ok, body, wire, metrics} <-
               receive_loop(conn, ref, HTTPWireGuard.new(), [], 0, deadline, %{
                 max_batch: 0,
                 max_parser_buffer: 0,
                 max_mailbox: 0,
                 max_heap_bytes: 0
               }),
             response_clock = clock(),
             {:ok, freshness} <-
               HTTPFreshness.calculate(wire.headers, request_clock, response_clock),
             true <- remaining(deadline) > 0 do
          {:ok, Map.merge(freshness, %{body: body, metrics: metrics, peer: ip})}
        else
          {:error, reason} when is_atom(reason) -> {:error, reason}
          _ -> {:error, :transport_rejected}
        end
      after
        Mint.HTTP.close(conn)
      end
    else
      _ -> {:error, :tls_rejected}
    end
  rescue
    _ -> {:error, :transport_rejected}
  catch
    _, _ -> {:error, :transport_rejected}
  end

  defp register_socket(nil, _, _), do: :ok

  defp register_socket(watcher, socket, deadline) do
    ref = make_ref()
    send(watcher, {:register_socket, self(), socket, ref})

    receive do
      {^ref, :ok} -> :ok
    after
      remaining(deadline) -> {:error, :deadline}
    end
  end

  defp receive_loop(conn, ref, wire, chunks, size, deadline, metrics) do
    socket = Mint.HTTP.get_socket(conn)

    count =
      case wire.phase do
        {:length, n} when n > 0 -> min(n, 4_096)
        {:chunk, n} when n > 0 -> min(n, 4_096)
        :chunk_crlf -> 2
        _ -> 1
      end

    if remaining(deadline) > 0 do
      case :ssl.recv(socket, count, remaining(deadline)) do
        {:ok, data} when byte_size(data) <= count ->
          with {:ok, wire} <- HTTPWireGuard.feed(wire, data),
               {:ok, conn, events} <- Mint.HTTP.stream(conn, {:ssl, socket, data}),
               {:ok, chunks, size, done} <- events(events, ref, chunks, size) do
            metrics = measure(conn, metrics, byte_size(data))

            if done and wire.done,
              do: {:ok, IO.iodata_to_binary(Enum.reverse(chunks)), wire, metrics},
              else: receive_loop(conn, ref, wire, chunks, size, deadline, metrics)
          else
            {:error, reason} when is_atom(reason) -> {:error, reason}
            _ -> {:error, :response_rejected}
          end

        {:error, :closed} ->
          with :close <- wire.phase,
               {:ok, _, events} <- Mint.HTTP.stream(conn, {:ssl_closed, socket}),
               {:ok, chunks, _, true} <- events(events, ref, chunks, size) do
            {:ok, IO.iodata_to_binary(Enum.reverse(chunks)), wire, metrics}
          else
            _ -> {:error, :truncated_response}
          end

        {:error, :timeout} ->
          {:error, :deadline}

        _ ->
          {:error, :socket_error}
      end
    else
      {:error, :deadline}
    end
  end

  defp events(events, ref, chunks, size) do
    Enum.reduce_while(events, {:ok, chunks, size, false}, fn
      {:data, ^ref, data}, {:ok, chunks, size, done} when size + byte_size(data) <= 262_144 ->
        {:cont, {:ok, [:binary.copy(data) | chunks], size + byte_size(data), done}}

      {:done, ^ref}, {:ok, chunks, size, _} ->
        {:cont, {:ok, chunks, size, true}}

      {:status, ^ref, _}, acc ->
        {:cont, acc}

      {:headers, ^ref, _}, acc ->
        {:cont, acc}

      _, _ ->
        {:halt, {:error, :response_rejected}}
    end)
  end

  defp measure(conn, m, batch) do
    info = Process.info(self(), [:message_queue_len, :memory])

    %{
      m
      | max_batch: max(m.max_batch, batch),
        max_parser_buffer: max(m.max_parser_buffer, byte_size(conn.buffer)),
        max_mailbox: max(m.max_mailbox, info[:message_queue_len]),
        max_heap_bytes: max(m.max_heap_bytes, info[:memory])
    }
  end

  defp clock, do: {System.system_time(:millisecond), System.monotonic_time(:millisecond)}
  defp remaining(d), do: max(0, d - System.monotonic_time(:millisecond))
end
