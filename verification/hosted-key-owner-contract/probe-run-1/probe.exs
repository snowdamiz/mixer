defmodule TransportFeasibilityProbe do
  def run do
    {:ok, _} = Application.ensure_all_started(:ssl)
    {:ok, _} = Application.ensure_all_started(:inets)
    port = System.fetch_env!("MIXER_PROBE_PORT") |> String.to_integer()
    ca = System.fetch_env!("MIXER_PROBE_CA") |> File.read!() |> :public_key.pem_decode()
    [{:Certificate, der, :not_encrypted}] = ca
    opts = [hostname: "jwks.contract.invalid", protocols: [:http1], mode: :passive,
      max_header_list_size: 10_240,
      transport_opts: [verify: :verify_peer, cacerts: [der], timeout: 1_000,
        send_timeout: 1_000, send_timeout_close: true,
        versions: [:"tlsv1.2", :"tlsv1.3"], recbuf: 16_384, buffer: 16_384]]

    {:ok, conn} = Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, opts)
    {:ok, conn, ref} = Mint.HTTP.request(conn, "GET", "/ok", [{"accept-encoding", "identity"}, {"connection", "close"}], nil)
    {conn, events} = until_done(conn, ref, [])
    true = {:status, ref, 200} in events
    "{}" = for {:data, ^ref, data} <- events, into: "", do: data
    {:ok, _} = Mint.HTTP.close(conn)
    IO.puts("PASS mint_pinned_ip_correct_hostname status=200 body_bytes=2")

    {:error, %Mint.TransportError{reason: {:tls_alert, {:bad_certificate, message}}}} =
      Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, Keyword.put(opts, :hostname, "wrong.contract.invalid"))
    true = String.contains?(to_string(message), "hostname_check_failed")
    IO.puts("PASS mint_wrong_hostname_rejected")

    [{:Certificate, wrong_der, :not_encrypted}] = System.fetch_env!("MIXER_PROBE_WRONG_CA") |> File.read!() |> :public_key.pem_decode()
    bad_opts = Keyword.update!(opts, :transport_opts, &Keyword.put(&1, :cacerts, [wrong_der]))
    {:error, %Mint.TransportError{reason: {:tls_alert, {:unknown_ca, _}}}} = Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, bad_opts)
    IO.puts("PASS mint_untrusted_chain_rejected")

    {:ok, conn} = Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, opts)
    {:ok, conn, ref} = Mint.HTTP.request(conn, "GET", "/large500", [], nil)
    {conn, events} = until_headers(conn, ref, [])
    true = {:status, ref, 500} in events
    {:ok, _} = Mint.HTTP.close(conn)
    IO.puts("PASS mint_non200_headers_available_before_completion data_bytes=#{data_bytes(events)}")

    {:ok, conn} = Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, opts)
    {:ok, conn, ref} = Mint.HTTP.request(conn, "GET", "/oversize200", [], nil)
    {conn, bytes} = until_over_limit(conn, ref, 0)
    IO.puts("OBSERVED mint_passive_limit_crossing_bytes=#{bytes}")
    true = bytes > 262_144 and bytes <= 393_216
    {:ok, _} = Mint.HTTP.close(conn)
    IO.puts("PASS mint_passive_oversize_stopped observed_data_bytes=#{bytes} retained_body_bytes=0")

    {:ok, conn} = Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, opts)
    {:ok, conn, _ref} = Mint.HTTP.request(conn, "GET", "/slow", [], nil)
    started = System.monotonic_time(:millisecond)
    {:error, conn, %Mint.TransportError{reason: :timeout}, []} = Mint.HTTP.recv(conn, 0, 2_000)
    true = Mint.HTTP.open?(conn)
    {:ok, conn} = Mint.HTTP.close(conn)
    false = Mint.HTTP.open?(conn)
    elapsed = System.monotonic_time(:millisecond) - started
    true = elapsed >= 1_900 and elapsed < 2_750
    IO.puts("PASS mint_recv_timeout_requires_close elapsed_ms=#{elapsed}")

    parent = self()
    {pid, monitor} = spawn_monitor(fn ->
      {:ok, conn} = Mint.HTTP.connect(:https, {127, 0, 0, 1}, port, opts)
      {:ok, conn, _} = Mint.HTTP.request(conn, "GET", "/kill", [], nil)
      send(parent, {:worker_ready, self()})
      Mint.HTTP.recv(conn, 0, 5_000)
    end)
    receive do {:worker_ready, ^pid} -> :ok after 1_500 -> raise "worker not ready" end
    Process.exit(pid, :kill)
    receive do {:DOWN, ^monitor, :process, ^pid, :killed} -> :ok after 1_500 -> raise "worker did not stop" end
    IO.puts("PASS mint_socket_owner_kill_down")

    {:ok, profile} = :inets.start(:httpc, [{:profile, :mixer_contract_probe}])
    :ok = :httpc.set_options([cookies: :disabled], profile)
    {:ok, [proxy: {:undefined, []}, https_proxy: {:undefined, []}]} = :httpc.get_options([:proxy, :https_proxy], profile)
    ssl = [verify: :verify_peer, cacerts: [der], server_name_indication: ~c"jwks.contract.invalid"]
    {:ok, request} = :httpc.request(:get,
      {~c"https://127.0.0.1:#{port}/httpc500", [{~c"host", ~c"jwks.contract.invalid:#{port}"}]},
      [ssl: ssl, autoredirect: false, autoretry: 0, timeout: 2_000, connect_timeout: 1_000],
      [sync: false, stream: {:self, :once}, max_body_size: 262_144, max_header_size: 10_240], profile)
    receive do
      {:http, {^request, {{_, 500, _}, _, body}}} ->
        true = byte_size(body) == 393_216
        IO.puts("PROVEN_LIMITATION httpc_non200_close_delimited_max_body_size=262144 delivered_body_bytes=#{byte_size(body)}")
      other -> raise "unexpected httpc result #{inspect(other, limit: 5)}"
    after 2_750 -> raise "httpc probe timeout" end
    :ok = :inets.stop(:httpc, profile)
    IO.puts("PASS probe_complete dedicated_httpc_profile_stopped=true")
  end

  defp until_done(conn, ref, events) do
    if {:done, ref} in events, do: {conn, events}, else: receive_more(conn, ref, events, &until_done/3)
  end
  defp until_headers(conn, ref, events) do
    if Enum.any?(events, &match?({:headers, ^ref, _}, &1)), do: {conn, events}, else: receive_more(conn, ref, events, &until_headers/3)
  end
  defp receive_more(conn, ref, events, next) do
    {:ok, conn, responses} = Mint.HTTP.recv(conn, 0, 1_000)
    next.(conn, ref, events ++ responses)
  end
  defp until_over_limit(conn, ref, total) do
    {:ok, conn, responses} = Mint.HTTP.recv(conn, 0, 1_000)
    bytes = total + data_bytes(responses)
    if bytes > 262_144, do: {conn, bytes}, else: until_over_limit(conn, ref, bytes)
  end
  defp data_bytes(events), do: Enum.reduce(events, 0, fn {:data, _, data}, n -> n + byte_size(data); _, n -> n end)
end

TransportFeasibilityProbe.run()
