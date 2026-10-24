# API feasibility probe only. No product endpoint, provider, database, or acknowledgment.
for app <- [:logger, :crypto, :ssl, :plug, :bandit, :mint, :jason] do
  {:ok, _} = Application.ensure_all_started(app)
end

for {app, version} <- [plug: ~c"1.20.3", bandit: ~c"1.13.1", thousand_island: ~c"1.6.0", mint: ~c"1.11.0"] do
  true = Application.spec(app, :vsn) == version
end

Code.compile_file(System.fetch_env!("TRANSPORT_CAPTURE_SOURCE"))

defmodule MixerTransportProbe.State do
  use Agent
  def start_link, do: Agent.start_link(fn -> %{mode: :whole_connection, events: [], connections: %{}, owners: [], guards: [], logs: [], filtered_logs: [], results: [], sockets: []} end, name: __MODULE__)
  def add(key, value), do: Agent.update(__MODULE__, &Map.update!(&1, key, fn values -> [value | values] end))
  def mode(value), do: Agent.update(__MODULE__, &Map.put(&1, :mode, value))
  def get(key), do: Agent.get(__MODULE__, &Map.fetch!(&1, key))
  def contains?(value, needle) when is_binary(value), do: :binary.match(value, needle) != :nomatch
  def contains?(value, needle) when is_map(value), do: contains?(Map.to_list(value), needle)
  def contains?(value, needle) when is_list(value), do: Enum.any?(value, &contains?(&1, needle))
  def contains?(value, needle) when is_tuple(value), do: contains?(Tuple.to_list(value), needle)
  def contains?(_, _), do: false
  def bits(value), do: %{body: contains?(value, "RAW_TRANSPORT_BODY_SENTINEL"), signature: contains?(value, "RAW_TRANSPORT_SIG_SENTINEL"), trailer: contains?(value, "RAW_TRANSPORT_TRAILER_SENTINEL")}
  def now, do: System.monotonic_time(:millisecond)

  def telemetry(event, measurements, metadata, _) do
    # The observer inspects event values only inside the emitting owner and retains booleans.
    add(:events, %{event: Enum.map(event, &Atom.to_string/1), measurements: bits(measurements), metadata: bits(metadata)})
    case event do
      [:thousand_island, :connection, :start] ->
        owner = self()
        span = metadata.telemetry_span_context
        started = System.convert_time_unit(measurements.monotonic_time, :native, :millisecond)
        Agent.update(__MODULE__, &put_in(&1, [:connections, span], owner))
        add(:owners, %{kind: :connection, pid: owner})
        mode = get(:mode)
        guard = spawn(fn ->
          monitor = Process.monitor(owner)
          timer = Process.send_after(self(), :expire, started + 500, abs: true)
          receive do
            {:DOWN, ^monitor, :process, ^owner, reason} ->
              Process.cancel_timer(timer)
              add(:results, %{kind: :connection_down, reason: inspect(reason), elapsed_ms: now() - started})
            :expire ->
              if mode == :whole_connection do
                Process.exit(owner, :kill)
                receive do
                  {:DOWN, ^monitor, :process, ^owner, reason} -> add(:results, %{kind: :watchdog_kill, reason: inspect(reason), elapsed_ms: now() - started})
                after 1_000 -> raise "owner did not exit"
                end
              else
                receive do
                  {:DOWN, ^monitor, :process, ^owner, reason} -> add(:results, %{kind: :connection_down, reason: inspect(reason), elapsed_ms: now() - started})
                after 1_000 -> raise "stream-only client was not cleaned"
                end
              end
          end
        end)
        add(:guards, guard)
      [:bandit, :request, :start] ->
        owner = self()
        conn_owner = Agent.get(__MODULE__, &Map.fetch!(&1.connections, metadata.connection_telemetry_span_context))
        protocol = Plug.Conn.get_http_protocol(metadata.conn)
        case_id = List.first(Plug.Conn.get_req_header(metadata.conn, "x-probe-case"))
        add(:owners, %{kind: :request, pid: owner, connection: conn_owner, protocol: protocol, case: case_id})
        if case_id == "h2-stream-only" do
          spawn(fn ->
            Process.sleep(100)
            Process.exit(owner, :kill)
          end)
        end
      _ -> :ok
    end
  end
end

defmodule MixerTransportProbe.LogHandler do
  def adding_handler(config), do: {:ok, config}
  def removing_handler(_), do: :ok
  def changing_config(_, _, config), do: {:ok, config}
  def log(event, config), do: MixerTransportProbe.State.add(config.config.key, %{level: event.level, bits: MixerTransportProbe.State.bits(event), domain: event.meta[:domain], safe: event.msg in [{:string, "transport_probe_safe"}, {:string, ~c"transport_probe_safe"}]})
  def filter(%{msg: {:string, message}, meta: %{domain: [:elixir, :mixer_transport_probe]}} = event, _) when message in ["transport_probe_safe", ~c"transport_probe_safe"], do: event
  def filter(_, _), do: :stop
end

defmodule MixerTransportProbe.Plug do
  require Logger
  def init(opts), do: opts
  def call(conn, _) do
    id = Plug.Conn.get_req_header(conn, "x-probe-case") |> List.first()
    MixerTransportProbe.State.add(:results, %{kind: :plug_enter, case: id})
    result = MixerHosted.Billing.RawWebhookCapture.capture(conn)
    case result do
      {:ok, captured, latest} ->
        MixerTransportProbe.State.add(:results, %{kind: :capture_return, case: id, bytes: byte_size(captured.raw_body), disposition: :captured})
        Logger.info("transport_probe_safe", domain: [:mixer_transport_probe])
        latest |> Plug.Conn.send_resp(418, "private probe") |> Plug.Conn.halt()
      {:error, reason, latest} ->
        MixerTransportProbe.State.add(:results, %{kind: :capture_return, case: id, disposition: reason})
        latest |> Plug.Conn.send_resp(400, "private probe") |> Plug.Conn.halt()
    end
  end
end

defmodule MixerTransportProbe.Client do
  alias MixerTransportProbe.State, as: S
  def headers(id, framing), do: "POST /api/v1/webhooks/stripe HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nStripe-Signature: RAW_TRANSPORT_SIG_SENTINEL\r\nX-Probe-Case: #{id}\r\n#{framing}\r\n"
  def h1(port, id, bytes) do
    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 1_000)
    started = S.now()
    try do
      :ok = :gen_tcp.send(socket, bytes)
      result = recv_h1(socket, [])
      recorded = %{end: result.end, response_base64: Base.encode64(result.response), response_bytes: byte_size(result.response)}
      S.add(:results, %{kind: :client, case: id, elapsed_ms: S.now() - started, result: recorded})
      result
    after
      :ok = :gen_tcp.close(socket)
      S.add(:sockets, %{case: id, closed: true})
    end
  end
  defp recv_h1(socket, acc) do
    case :gen_tcp.recv(socket, 0, 1_200) do
      {:ok, data} -> recv_h1(socket, [data | acc])
      {:error, reason} -> %{end: reason, response: IO.iodata_to_binary(Enum.reverse(acc))}
    end
  end
  def connect(port) do
    {:ok, conn} = Mint.HTTP2.connect(:http, "localhost", port, mode: :passive, transport_opts: [ip: {127, 0, 0, 1}, timeout: 1_000])
    {:ok, conn, _} = Mint.HTTP2.recv(conn, 0, 100)
    Process.put(:owned_mint, conn)
    conn
  end
  def request(conn, id) do
    {:ok, conn, ref} = Mint.HTTP2.request(conn, "POST", "/api/v1/webhooks/stripe", [{"content-type", "application/json"}, {"stripe-signature", "RAW_TRANSPORT_SIG_SENTINEL"}, {"x-probe-case", id}], :stream)
    Process.put(:owned_mint, conn)
    {conn, ref}
  end
  def send_body(conn, ref, bytes) do
    case Mint.HTTP2.stream_request_body(conn, ref, bytes) do
      {:ok, next} -> Process.put(:owned_mint, next); next
      {:error, next, _} -> Process.put(:owned_mint, next); next
    end
  end
  def recv_h2(conn, deadline, acc \\ []) do
    if S.now() >= deadline do
      {conn, Enum.reverse(acc), :bounded_wait}
    else
      case Mint.HTTP2.recv(conn, 0, max(deadline - S.now(), 1)) do
        {:ok, next, responses} ->
          Process.put(:owned_mint, next)
          next_acc = Enum.reverse(responses, acc)
          if Enum.any?(responses, &match?({:done, _}, &1)), do: {next, Enum.reverse(next_acc), :response_done}, else: recv_h2(next, deadline, next_acc)
        {:error, next, reason, responses} -> Process.put(:owned_mint, next); {next, Enum.reverse(Enum.reverse(responses, acc)), inspect(reason)}
      end
    end
  end
  def h2(port, id, mode) do
    conn = connect(port)
    started = S.now()
    try do
      {conn, ref} = request(conn, id)
      conn = send_body(conn, ref, "RAW_TRANSPORT_BODY_SENTINEL")
      conn = case mode do
        :trailers -> send_body(conn, ref, {:eof, [{"x-synthetic-trailer", "RAW_TRANSPORT_TRAILER_SENTINEL"}]})
        :drip -> Enum.reduce(1..5, conn, fn _, value -> Process.sleep(100); send_body(value, ref, "x") end)
        :stream_only -> conn
      end
      {conn, responses, ending} = recv_h2(conn, S.now() + if(mode == :stream_only, do: 300, else: 800))
      stream_only = if mode == :stream_only do
        true = Mint.HTTP2.open?(conn)
        {:ok, next, ping_ref} = Mint.HTTP2.ping(conn)
        Process.put(:owned_mint, next)
        {_, after_responses, _} = recv_h2(next, S.now() + 100)
        Enum.any?(after_responses, &match?({:pong, ^ping_ref}, &1))
      else
        nil
      end
      safe_responses = Enum.map(responses, fn
        {:status, _, status} -> %{type: :status, status: status}
        {:error, _, error} -> %{type: :error, reason: inspect(error)}
        response -> %{type: elem(response, 0)}
      end)
      result = %{kind: :client, case: id, elapsed_ms: S.now() - started, ending: ending, responses: safe_responses, connection_usable_after_stream_kill: stream_only}
      S.add(:results, result)
      result
    after
      {:ok, _} = Mint.HTTP2.close(Process.get(:owned_mint))
      Process.delete(:owned_mint)
      S.add(:sockets, %{case: id, closed: true})
    end
  end
end

alias MixerTransportProbe.{Client, State}
{:ok, _} = State.start_link()
events = [[:thousand_island, :connection, :start], [:thousand_island, :connection, :ready], [:thousand_island, :connection, :recv], [:thousand_island, :connection, :async_recv], [:bandit, :request, :start], [:bandit, :request, :stop], [:bandit, :request, :exception]]
:ok = :telemetry.attach_many("mixer-transport-contract-probe", events, &State.telemetry/4, nil)
:ok = :logger.add_handler(:mixer_transport_unfiltered, MixerTransportProbe.LogHandler, %{level: :all, config: %{key: :logs}})
:ok = :logger.add_handler(:mixer_transport_filtered, MixerTransportProbe.LogHandler, %{level: :all, config: %{key: :filtered_logs}, filters: [only_owned_schema: {&MixerTransportProbe.LogHandler.filter/2, nil}], filter_default: :stop})

{:ok, listener} = Bandit.start_link(plug: MixerTransportProbe.Plug, ip: {127, 0, 0, 1}, port: 0, startup_log: false, http_options: [log_protocol_errors: false, log_exceptions_with_status_codes: [], log_client_closures: false], http_1_options: [max_requests: 1, max_request_line_length: 512, max_header_length: 8_192, max_header_count: 32], http_2_options: [max_requests: 4, max_header_block_size: 16_384, default_local_settings: [max_concurrent_streams: 1, max_header_list_size: 16_384, max_frame_size: 16_384, initial_window_size: 32_768]], thousand_island_options: [num_acceptors: 1, num_connections: 4, read_timeout: 1_000, handshake_timeout: 1_000, shutdown_timeout: 1_000])
{:ok, {{127, 0, 0, 1}, port}} = ThousandIsland.listener_info(listener)
result_dir = System.fetch_env!("TRANSPORT_RESULT_DIR")
File.write!(Path.join(result_dir, "listener.json"), Jason.encode!(%{port: port, ip: "127.0.0.1", scheme: "http", protocol: "HTTP/1.1 and h2c", listener: inspect(listener)}))

try do
  %{end: :closed, response: ""} = Client.h1(port, "h1-header-stall", "POST /api/v1/webhooks/stripe HTTP/1.1\r\nX-Unfinished: RAW_TRANSPORT_SIG_SENTINEL")
  %{end: :closed} = Client.h1(port, "h2-preface-stall", "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n")
  %{end: :closed, response: ""} = Client.h1(port, "h1-body-stall", Client.headers("h1-body-stall", "Content-Length: 999\r\n") <> "RAW_TRANSPORT_BODY_SENTINEL")
  %{responses: []} = Client.h2(port, "h2-body-drip", :drip)
  %{response: h1_cl} = Client.h1(port, "h1-cl-success", Client.headers("h1-cl-success", "Content-Length: 27\r\n") <> "RAW_TRANSPORT_BODY_SENTINEL")
  true = String.contains?(h1_cl, " 418 ")
  %{response: h1_chunked} = Client.h1(port, "h1-chunked-success", Client.headers("h1-chunked-success", "Transfer-Encoding: chunked\r\n") <> "1b\r\nRAW_TRANSPORT_BODY_SENTINEL\r\n0\r\n\r\n")
  true = String.contains?(h1_chunked, " 418 ")
  %{responses: trailer_responses} = Client.h2(port, "h2-trailer-sink", :trailers)
  true = Enum.any?(trailer_responses, &(&1.type == :status and &1.status == 418))
  State.mode(:stream_only)
  %{responses: [], connection_usable_after_stream_kill: true} = Client.h2(port, "h2-stream-only", :stream_only)
after
  Supervisor.stop(listener, :normal, 2_000)
  Process.sleep(100)
  :ok = :telemetry.detach("mixer-transport-contract-probe")
  :ok = :logger.remove_handler(:mixer_transport_unfiltered)
  :ok = :logger.remove_handler(:mixer_transport_filtered)
  owners = State.get(:owners)
  guards = State.get(:guards)
  all_owners_down = Enum.all?(owners, &(not Process.alive?(&1.pid)))
  all_guards_down = Enum.all?(guards, &(not Process.alive?(&1)))
  refused = case :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 100) do
    {:error, :econnrefused} -> true
    {:ok, socket} -> :gen_tcp.close(socket); false
    _ -> false
  end
  cleanup = %{listener_down: not Process.alive?(listener), connection_and_stream_owners_down: all_owners_down, watchdogs_down: all_guards_down, port_refused: refused, telemetry_detached: true, owned_logger_handlers_removed: true, sockets: Enum.reverse(State.get(:sockets))}
  summary = %{cleanup: cleanup, results: Enum.reverse(State.get(:results)), owners: Enum.map(Enum.reverse(owners), fn value -> Map.new(value, fn {key, data} -> {key, if(is_pid(data), do: inspect(data), else: data)} end) end), telemetry: Enum.reverse(State.get(:events)), unfiltered_logs: Enum.reverse(State.get(:logs)), filtered_logs: Enum.reverse(State.get(:filtered_logs)), scope: "synthetic API probe; no product endpoint, verifier, provider, DB, Oban or 2xx"}
  File.write!(Path.join(result_dir, "probe.json"), Jason.encode!(summary, pretty: true))
  true = all_owners_down and all_guards_down and refused
end

results = State.get(:results)
true = Enum.count(results, &(&1.kind == :watchdog_kill)) == 4
false = Enum.any?(results, &(&1.kind == :capture_return and &1.case in ["h1-body-stall", "h2-body-drip", "h2-stream-only"]))
true = Enum.any?(State.get(:logs), & &1.bits.trailer)
false = Enum.any?(State.get(:filtered_logs), &(Enum.any?(Map.values(&1.bits), fn value -> value end)))
true = Enum.any?(State.get(:filtered_logs), & &1.safe)
IO.puts("PASS: 8 synthetic local transport probes; configured owned handler filters drop raw sentinel event; connection watchdog disposes H1/H2 owners; stream-only kill leaves H2 connection usable")
