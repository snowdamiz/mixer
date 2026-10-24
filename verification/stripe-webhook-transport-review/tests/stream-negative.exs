# Deliberately omit the transport owner/guard to isolate the stream-only negative
# control. This listener is never counted as composed-profile qualification.
defmodule MixerPrivateNegative do
  use Agent

  def start_link,
    do: Agent.start_link(fn -> %{connections: %{}, requests: []} end, name: __MODULE__)

  def callback([:thousand_island, :connection, :start], _, metadata, _) do
    pid = self()
    Agent.update(__MODULE__, &put_in(&1, [:connections, metadata.telemetry_span_context], pid))
  end

  def callback([:bandit, :request, :start], _, metadata, _) do
    pid = self()

    Agent.update(
      __MODULE__,
      &Map.update!(&1, :requests, fn xs ->
        [{pid, metadata.connection_telemetry_span_context} | xs]
      end)
    )
  end

  def init(opts), do: opts

  def call(conn, _) do
    MixerHosted.Billing.RawWebhookCapture.capture(conn)
    Plug.Conn.send_resp(conn, 418, "negative control")
  end
end

{:ok, _} = MixerPrivateNegative.start_link()

for h <- :logger.get_handler_config() do
  :ok =
    :logger.set_handler_config(h.id, :formatter, {:logger_formatter, %{template: [:msg, ~c"\n"]}})

  :ok =
    :logger.add_handler_filter(
      h.id,
      :mixer_negative_schema,
      {&MixerHosted.Billing.WebhookTransport.Sinks.filter/2, nil}
    )
end

:ok =
  :telemetry.attach_many(
    "mixer-stream-negative",
    [[:thousand_island, :connection, :start], [:bandit, :request, :start]],
    &MixerPrivateNegative.callback/4,
    nil
  )

{:ok, listener} =
  Bandit.start_link(
    plug: MixerPrivateNegative,
    ip: {127, 0, 0, 1},
    port: 0,
    startup_log: false,
    http_options: [
      log_protocol_errors: false,
      log_client_closures: false,
      log_exceptions_with_status_codes: []
    ],
    http_1_options: [max_requests: 1, log_unknown_messages: false],
    http_2_options: [max_requests: 1, default_local_settings: [max_concurrent_streams: 1]],
    thousand_island_options: [
      num_acceptors: 1,
      num_connections: 16,
      max_connections_retry_count: 0,
      read_timeout: 1_000,
      handshake_timeout: 1_000
    ]
  )

{:ok, {{127, 0, 0, 1}, port}} = ThousandIsland.listener_info(listener)
result = System.fetch_env!("CAPTURE_RESULT_DIR")

File.write!(
  Path.join(result, "listener.json"),
  Jason.encode!(%{port: port, negative_control_only: true})
)

{:ok, conn} =
  Mint.HTTP2.connect(:http, "localhost", port,
    mode: :passive,
    transport_opts: [ip: {127, 0, 0, 1}, timeout: 1_000]
  )

Process.put(:negative_mint, conn)

try do
  {:ok, conn, _} = Mint.HTTP2.recv(conn, 0, 100)

  {:ok, conn, ref} =
    Mint.HTTP2.request(
      conn,
      "POST",
      "/api/v1/webhooks/stripe",
      [{"content-type", "application/json"}, {"stripe-signature", "x"}],
      :stream
    )

  {:ok, conn} = Mint.HTTP2.stream_request_body(conn, ref, "x")
  Process.put(:negative_mint, conn)
  Process.sleep(50)
  state = Agent.get(MixerPrivateNegative, & &1)
  [{stream, span}] = state.requests
  connection = state.connections[span]
  monitor = Process.monitor(stream)
  Process.exit(stream, :kill)

  receive do
    {:DOWN, ^monitor, :process, ^stream, _} -> :ok
  after
    500 -> raise "stream did not exit"
  end

  {conn, prior} =
    case Mint.HTTP2.recv(conn, 0, 200) do
      {:ok, n, responses} -> {n, responses}
      {:error, n, %Mint.TransportError{reason: :timeout}, responses} -> {n, responses}
    end

  true = prior == []
  true = Process.alive?(connection)
  {:ok, conn, ping} = Mint.HTTP2.ping(conn)
  {:ok, conn, responses} = Mint.HTTP2.recv(conn, 0, 500)
  Process.put(:negative_mint, conn)
  true = Enum.any?(responses, &match?({:pong, ^ping}, &1))

  File.write!(
    Path.join(result, "negative.json"),
    Jason.encode!(
      %{
        stream_down: true,
        connection_alive_after_stream_only_kill: true,
        no_response_or_reset_in_200ms: true,
        pong: true,
        guard_intentionally_absent: true,
        composed_profile_qualification: false
      }, pretty: true)
  )
after
  Mint.HTTP2.close(Process.get(:negative_mint))
  Process.delete(:negative_mint)
  ThousandIsland.stop(listener, 1_000)
  Process.sleep(50)
  :telemetry.detach("mixer-stream-negative")

  owners =
    Agent.get(
      MixerPrivateNegative,
      &(Map.values(&1.connections) ++ Enum.map(&1.requests, fn {pid, _} -> pid end))
    )

  true = Enum.all?(owners, &(not Process.alive?(&1)))

  File.write!(
    Path.join(result, "cleanup.json"),
    Jason.encode!(
      %{
        all_owners_down: true,
        listener_down: not Process.alive?(listener),
        telemetry_detached: true,
        socket_closed: true,
        sink_filters_remain_until_vm_exit: true
      }, pretty: true)
  )
end

IO.puts(
  "PASS stream-only negative: stream DOWN, no response/reset, connection alive, PING/PONG; explicit cleanup"
)
