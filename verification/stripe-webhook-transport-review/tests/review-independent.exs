ExUnit.start(autorun: false)

defmodule ReviewEvidence do
  use Agent
  def start_link, do: Agent.start_link(fn -> %{rows: [], logs: [], captures: [], calls: 0, returns: 0, mode: :normal} end, name: __MODULE__)
  def add(k, v), do: Agent.update(__MODULE__, &Map.update!(&1, k, fn xs -> [v | xs] end))
  def inc(k), do: Agent.update(__MODULE__, &Map.update!(&1, k, fn n -> n + 1 end))
  def mode(v), do: Agent.update(__MODULE__, &Map.put(&1, :mode, v))
  def get, do: Agent.get(__MODULE__, & &1)
  def raw?(v) when is_binary(v), do: :binary.match(v, "REVIEW_PRIVATE_") != :nomatch
  def raw?(v) when is_map(v), do: raw?(Map.to_list(v))
  def raw?(v) when is_tuple(v), do: raw?(Tuple.to_list(v))
  def raw?(v) when is_list(v), do: Enum.any?(v, &raw?/1)
  def raw?(_), do: false
end

defmodule ReviewSink do
  def adding_handler(c), do: {:ok, c}
  def removing_handler(_), do: :ok
  def changing_config(_, _, c), do: {:ok, c}
  def log(e, _), do: ReviewEvidence.add(:logs, %{raw: ReviewEvidence.raw?(e), event: e})
end

defmodule ReviewPlug do
  def init(o), do: o
  def call(conn, _) do
    try do
      case MixerHosted.Billing.WebhookTransport.capture(conn) do
        {:ok, c, latest} ->
          ReviewEvidence.inc(:calls)
          result = MixerHosted.Billing.WebhookSignature.verify(c.raw_body, c.signature_header_values, ["review_synthetic_private_key_32_bytes"], 1_700_000_000)
          ReviewEvidence.add(:captures, %{owner: inspect(self()), bytes: byte_size(c.raw_body), sha256: Base.encode16(:crypto.hash(:sha256, c.raw_body), case: :lower), original_signature_values: c.signature_header_values, verifier_result: inspect(result)})
          if ReviewEvidence.get().mode == :held_response, do: Process.sleep(8_000)
          Plug.Conn.send_resp(latest, 418, "review-private-response") |> Plug.Conn.halt()
        {:error, _, latest} -> Plug.Conn.send_resp(latest, 400, "review-private-response") |> Plug.Conn.halt()
      end
    after
      MixerHosted.Billing.WebhookTransport.dispose()
    end
  end
end

defmodule ReviewHelpers do
  alias MixerHosted.Billing.WebhookTransport, as: T
  alias T.Owner
  def now, do: System.monotonic_time(:millisecond)
  def wait_until(fun, ms \\ 500) do
    end_at = now() + ms
    loop = fn loop ->
      if fun.(), do: true, else: if(now() >= end_at, do: false, else: (Process.sleep(2); loop.(loop)))
    end
    loop.(loop)
  end
  def frame(t, f, id, data), do: <<byte_size(data)::24, t, f, 0::1, id::31, data::binary>>
  def settings(values), do: frame(4, 0, 0, for({id, v} <- values, into: <<>>, do: <<id::16, v::32>>))
  def preface, do: "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n" <> settings([])
  def headers(extra \\ []) do
    {block, _} = HPAX.encode(Enum.map([
      {":method", "POST"}, {":scheme", "http"}, {":authority", "localhost"},
      {":path", "/api/v1/webhooks/stripe"}, {"content-type", "application/json"},
      {"stripe-signature", "REVIEW_PRIVATE_SIGNATURE"}
    ] ++ extra, fn {k, v} -> {:no_store, k, v} end), HPAX.new(4096, huffman_encoding: :never))
    IO.iodata_to_binary(block)
  end
  def tcp(port), do: :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 1_000)
  def close_read(s, limit) do
    start = now()
    loop = fn loop, bytes ->
      if now() >= start + limit do
        %{closed: false, bytes: bytes, elapsed_ms: now() - start}
      else
        case :gen_tcp.recv(s, 0, min(50, max(start + limit - now(), 1))) do
          {:ok, b} -> loop.(loop, bytes + byte_size(b))
          {:error, :timeout} -> loop.(loop, bytes)
          {:error, r} -> %{closed: r in [:closed, :econnreset], reason: r, bytes: bytes, elapsed_ms: now() - start}
        end
      end
    end
    loop.(loop, 0)
  end
  def active_connection do
    true = wait_until(fn -> map_size(:sys.get_state(Owner).connections) == 1 end)
    c = :sys.get_state(Owner).connections |> Map.values() |> hd()
    true = wait_until(fn -> :sys.get_state(c.guard).requests != [] end)
    readers = :sys.get_state(c.guard).requests
    for pid <- Enum.uniq([c.pid | readers]), do: Process.put({:review_monitor, pid}, Process.monitor(pid))
    {c, readers}
  end
  def role(fun) do
    Process.flag(:trap_exit, true)
    ReviewEvidence.mode(:normal)
    :ok = :logger.add_handler(:review_collector, ReviewSink, %{level: :all})
    {:ok, role} = T.start_link(ReviewPlug, %{review_collector: ReviewSink})
    {_, listener, _, _} = Enum.find(Supervisor.which_children(role), fn {id, _, _, _} -> match?({Bandit, _}, id) end)
    {:ok, {{127, 0, 0, 1}, port}} = ThousandIsland.listener_info(listener)
    dir = Path.join(System.fetch_env!("CAPTURE_RESULT_DIR"), "listeners/#{port}")
    File.mkdir_p!(dir)
    File.write!(Path.join(dir, "listener.json"), Jason.encode!(%{port: port}))
    config = T.Sinks.inventory()
    ReviewEvidence.add(:rows, %{kind: :inventory, logger: Enum.map(config.logger, fn h -> %{id: h.id, module: h.module, filters: Enum.map(h.filters, fn {id, {fun, arg}} -> %{id: id, fun: inspect(fun), argument: inspect(arg)} end), formatter: inspect(h.formatter), config: inspect(Map.get(h, :config))} end), primary: inspect(config.primary), telemetry: Enum.map(config.telemetry, fn h -> %{id: h.id, event: h.event_name, callback: inspect(h.function), config: inspect(h.config)} end), stdout: :logger_std_h_standard_io, stderr: :merged_child_output, exporters: []})
    try do
      fun.(role, listener, port)
    after
      if Process.alive?(role) do
        try do
          Supervisor.stop(role, :normal, 2_000)
        catch
          :exit, _ -> true = wait_until(fn -> not Process.alive?(role) end, 2_000)
        end
      end
      Process.sleep(30)
      # Filters intentionally remain on all surviving handlers after role death.
      remaining = :logger.get_handler_config()
      filters_retained = Enum.all?(remaining, &Keyword.has_key?(&1.filters, :mixer_private_schema))
      :logger.log(:error, %{report: "REVIEW_PRIVATE_TEARDOWN"}, %{domain: [:otp, :ssl], secret: "REVIEW_PRIVATE_METADATA"})
      Process.sleep(10)
      refused = case tcp(port) do
        {:error, :econnrefused} -> true
        {:ok, s} -> :gen_tcp.close(s); false
        _ -> false
      end
      ReviewEvidence.add(:rows, %{kind: :cleanup, port: port, role_down: not Process.alive?(role), owner_down: is_nil(Process.whereis(Owner)), guard_supervisor_down: is_nil(Process.whereis(T.Guards)), port_refused: refused, filters_retained: filters_retained})
      :logger.remove_handler(:review_collector)
      :telemetry.detach("mixer-private-webhook-control")
    end
  end
  def monitor_down(pids) do
    refs = for pid <- Enum.uniq(pids), do: {pid, Process.delete({:review_monitor, pid}) || Process.monitor(pid)}
    for {pid, ref} <- refs do
      receive do
        {:DOWN, ^ref, :process, ^pid, reason} -> %{pid: inspect(pid), down: true, reason: inspect(reason)}
      after 600 -> %{pid: inspect(pid), down: false}
      end
    end
  end
end

{:ok, _} = ReviewEvidence.start_link()
tracer = spawn(fn ->
  loop = fn loop ->
    receive do
      {:trace, _, :return_from, {MixerHosted.Billing.WebhookSignature, :verify, 4}, r} when r in [:ok, {:error, :invalid_signature}, {:error, :verification_unavailable}] -> ReviewEvidence.inc(:returns); loop.(loop)
      :stop -> :ok
    end
  end
  loop.(loop)
end)
:erlang.trace_pattern({MixerHosted.Billing.WebhookSignature, :verify, 4}, [{:_, [], [{:return_trace}, {:message, false}]}], [:local])
:erlang.trace(:all, true, [:call, {:tracer, tracer}])

defmodule ReviewIndependentTest do
  use ExUnit.Case, async: false
  import ReviewHelpers
  alias MixerHosted.Billing.WebhookTransport, as: T
  alias T.{Owner, Sinks}

  test "finite SETTINGS valid extrema preserve capture and original signature" do
    role(fn _, _, port ->
      for {label, values} <- [
        {:all_min, [{1, 0}, {2, 0}, {3, 0}, {4, 0}, {5, 16_384}, {6, 0}]},
        {:all_max, [{1, 4_294_967_295}, {2, 1}, {3, 4_294_967_295}, {4, 2_147_483_647}, {5, 16_777_215}, {6, 4_294_967_295}]},
        {:unknown_and_duplicate, [{4, 0}, {4, 65_535}, {65_535, 4_294_967_295}]}
      ] do
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          :ok = :gen_tcp.send(s, preface() <> settings(values) <> settings([{4, 65_535}]) <> frame(1, 4, 1, headers()) <> frame(0, 1, 1, "REVIEW_PRIVATE_BODY"))
          peer = close_read(s, 1_300)
          assert peer.closed
          assert ReviewEvidence.get().calls == before + 1
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :settings_valid, label: label, values: Enum.map(values, fn {a, b} -> [a, b] end), peer: peer, verifier_delta: 1})
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "finite invalid SETTINGS and WINDOW_UPDATE cases reject before verifier" do
    role(fn _, _, port ->
      cases = [
        {:settings_enable_push_2, settings([{2, 2}])},
        {:settings_initial_window_overflow, settings([{4, 2_147_483_648}])},
        {:settings_frame_below_min, settings([{5, 16_383}])},
        {:settings_frame_above_max, settings([{5, 16_777_216}])},
        {:settings_ack_payload, frame(4, 1, 0, <<1::16, 0::32>>)},
        {:settings_nonzero_stream, frame(4, 0, 1, <<>>)},
        {:settings_bad_length, frame(4, 0, 0, <<1>>)},
        {:window_zero_connection, frame(8, 0, 0, <<0::32>>)},
        {:window_zero_stream, frame(8, 0, 1, <<0::32>>)},
        {:window_bad_length, frame(8, 0, 0, <<1>>)},
        {:window_connection_overflow, frame(8, 0, 0, <<2_147_483_647::32>>)}
      ]
      for {label, payload} <- cases do
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          :ok = :gen_tcp.send(s, preface() <> payload)
          peer = close_read(s, 1_300)
          assert peer.closed
          assert ReviewEvidence.get().calls == before
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :protocol_rejection, label: label, peer: peer, verifier_delta: 0})
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "request SETTINGS window shrink and expansion preserve the one original capture" do
    role(fn _, _, port ->
      {:ok, s} = tcp(port)
      before = ReviewEvidence.get().calls
      try do
        :ok = :gen_tcp.send(s, preface() <> frame(1, 4, 1, headers()))
        {c, readers} = active_connection()
        transitions = [
          [{1, 0}, {4, 0}, {3, 0}, {6, 0}],
          [{1, 4_294_967_295}, {4, 2_147_483_647}, {3, 4_294_967_295}, {5, 16_777_215}, {6, 4_294_967_295}],
          [{1, 0}, {4, 0}],
          [{1, 4_096}, {4, 65_535}, {5, 16_384}]
        ]
        for values <- transitions, do: :ok = :gen_tcp.send(s, settings(values))
        assert ReviewEvidence.get().calls == before
        :ok = :gen_tcp.send(s, frame(0, 1, 1, "REVIEW_PRIVATE_BODY"))
        peer = close_read(s, 1_300)
        assert peer.closed
        assert ReviewEvidence.get().calls == before + 1
        deaths = monitor_down([c.pid | readers])
        assert Enum.all?(deaths, & &1.down)
        assert wait_until(fn -> Owner.snapshot().connections == 0 end)
        ReviewEvidence.add(:rows, %{kind: :settings_request_transitions, transition_count: length(transitions), peer: peer, deaths: deaths, verifier_delta: 1})
      after :gen_tcp.close(s)
      end
    end)
  end

  test "header count and fragmented encoded block overflow reject before verifier" do
    role(fn _, _, port ->
      long = headers([{"x-uncompressed", String.duplicate("x", 16_385)}])
      <<part::binary-size(16_000), rest::binary>> = long
      for {label, payload} <- [
        {:h1_header_count, "POST /api/v1/webhooks/stripe HTTP/1.1\r\nHost: localhost\r\n" <> Enum.map_join(1..33, "", &"X-Count-#{&1}: x\r\n") <> "Content-Length: 1\r\nContent-Type: application/json\r\nStripe-Signature: REVIEW_PRIVATE_SIGNATURE\r\n\r\nx"},
        {:h2_encoded_fragment_limit, preface() <> frame(1, 0, 1, part) <> frame(9, 4, 1, rest)}
      ] do
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          :ok = :gen_tcp.send(s, payload)
          peer = close_read(s, 1_300)
          assert peer.closed and ReviewEvidence.get().calls == before
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :header_limit, label: label, encoded_header_bytes: if(label == :h2_encoded_fragment_limit, do: byte_size(long), else: nil), peer: peer, verifier_delta: 0})
        after :gen_tcp.close(s)
        end
      end
    end)
  end

  test "actual H2 zero response window remains under absolute outer guard" do
    role(fn _, _, port ->
      {:ok, s} = tcp(port)
      before = ReviewEvidence.get().calls
      start = now()
      try do
        :ok = :gen_tcp.send(s, preface() <> settings([{4, 0}]) <> frame(1, 4, 1, headers()) <> frame(0, 1, 1, "REVIEW_PRIVATE_BODY"))
        {c, readers} = active_connection()
        assert wait_until(fn -> ReviewEvidence.get().calls == before + 1 end)
        assert Process.alive?(c.pid) and Enum.all?(readers, &Process.alive?/1)
        pinger = Task.async(fn ->
          Enum.reduce_while(1..80, :ok, fn _, _ ->
            Process.sleep(100)
            case :gen_tcp.send(s, frame(6, 0, 0, <<0::64>>)) do
              :ok -> {:cont, :ok}
              _ -> {:halt, :closed}
            end
          end)
        end)
        peer = close_read(s, 7_300)
        elapsed = now() - start
        Task.await(pinger, 1_000)
        assert peer.closed
        assert elapsed >= 7_000 and elapsed <= 7_100
        deaths = monitor_down([c.pid | readers])
        assert Enum.all?(deaths, & &1.down)
        assert wait_until(fn -> Owner.snapshot().connections == 0 end)
        history = Owner.snapshot().history
        assert Enum.any?(history, &(&1.reason == :expired and &1.overshoot_ms <= 100))
        ReviewEvidence.add(:rows, %{kind: :actual_window_block, peer: peer, total_peer_ms: elapsed, deaths: deaths, history: history, verifier_delta: 1})
      after
        :gen_tcp.close(s)
      end
    end)
  end

  test "window update extremes during request and update flood cannot extend capture" do
    role(fn _, _, port ->
      for {label, payload} <- [
        {:stream_send_window_overflow, frame(8, 0, 1, <<2_147_483_647::32>>)},
        {:connection_window_valid_max, frame(8, 0, 0, <<2_147_418_112::32>>)},
        {:settings_and_window_flood, IO.iodata_to_binary(for _ <- 1..64, do: settings([{4, 65_535}]) <> frame(8, 0, 0, <<1::32>>) <> frame(8, 0, 1, <<1::32>>))}
      ] do
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        start = now()
        try do
          :ok = :gen_tcp.send(s, preface() <> frame(1, 4, 1, headers()))
          {c, readers} = active_connection()
          :gen_tcp.send(s, payload)
          peer = close_read(s, 5_300)
          assert peer.closed and now() - start <= 5_100
          assert ReviewEvidence.get().calls == before
          deaths = monitor_down([c.pid | readers])
          assert Enum.all?(deaths, & &1.down)
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :window_request, label: label, peer: peer, total_peer_ms: now() - start, deaths: deaths, verifier_delta: 0})
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "new stream before completion after capture and after peer reset closes all original owners" do
    role(fn _, _, port ->
      for mode <- [:before_completion, :after_capture, :after_reset] do
        ReviewEvidence.mode(if(mode == :after_capture, do: :held_response, else: :normal))
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          first = preface() <> frame(1, 4, 1, headers()) <> if(mode == :after_capture, do: frame(0, 1, 1, "REVIEW_PRIVATE_BODY"), else: "")
          :ok = :gen_tcp.send(s, first)
          {c, readers} = active_connection()
          if mode == :after_capture, do: assert(wait_until(fn -> ReviewEvidence.get().calls == before + 1 end))
          reset = if mode == :after_reset, do: frame(3, 0, 1, <<8::32>>), else: ""
          :gen_tcp.send(s, reset <> frame(1, 4, 3, headers()) <> frame(0, 1, 3, "REVIEW_PRIVATE_SECOND_BODY"))
          peer = close_read(s, 600)
          assert peer.closed
          assert ReviewEvidence.get().calls == before + if(mode == :after_capture, do: 1, else: 0)
          deaths = monitor_down([c.pid | readers])
          assert Enum.all?(deaths, & &1.down)
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :second_stream, mode: mode, peer: peer, deaths: deaths, verifier_delta: if(mode == :after_capture, do: 1, else: 0)})
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "post-response bytes and simultaneous streams never produce second verifier" do
    role(fn _, _, port ->
      for mode <- [:simultaneous, :post_response] do
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          first = preface() <> frame(1, 4, 1, headers()) <> frame(0, 1, 1, "REVIEW_PRIVATE_BODY")
          peer = if mode == :simultaneous do
            :gen_tcp.send(s, first <> frame(1, 4, 3, headers()) <> frame(0, 1, 3, "REVIEW_PRIVATE_SECOND_BODY"))
            close_read(s, 1_300)
          else
            :ok = :gen_tcp.send(s, first)
            observed = close_read(s, 1_000)
            assert observed.closed
            send_result = :gen_tcp.send(s, frame(1, 4, 3, headers()) <> frame(0, 1, 3, "REVIEW_PRIVATE_SECOND_BODY"))
            ReviewEvidence.add(:rows, %{kind: :post_eof_write, send_result: inspect(send_result), eof_preceded_write: true})
            observed
          end
          assert peer.closed
          delta = ReviewEvidence.get().calls - before
          assert delta in 0..1
          if mode == :post_response, do: assert(delta == 1)
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :second_stream_race, mode: mode, peer: peer, verifier_delta: delta})
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "RST_STREAM flood disposes connection and all original readers" do
    role(fn _, _, port ->
      for mode <- [:active_stream, :idle_new_stream] do
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          :ok = :gen_tcp.send(s, preface() <> frame(1, 4, 1, headers()))
          {c, readers} = active_connection()
          frames = for i <- 1..64, do: frame(3, 0, if(mode == :active_stream, do: 1, else: 1 + 2 * i), <<8::32>>)
          :gen_tcp.send(s, frames)
          peer = close_read(s, 600)
          assert peer.closed and ReviewEvidence.get().calls == before
          deaths = monitor_down([c.pid | readers])
          assert Enum.all?(deaths, & &1.down)
          assert wait_until(fn -> Owner.snapshot().connections == 0 end)
          ReviewEvidence.add(:rows, %{kind: :reset_flood, mode: mode, frames_sent: 64, peer: peer, deaths: deaths, verifier_delta: 0, rate_limiter_isolated: false})
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "H2 request owner guard and registry loss each close true connection and stream" do
    for fault <- [:reader, :guard, :owner] do
      role(fn role, _, port ->
        {:ok, s} = tcp(port)
        before = ReviewEvidence.get().calls
        try do
          :ok = :gen_tcp.send(s, preface() <> frame(1, 4, 1, headers()))
          {c, readers} = active_connection()
          target = case fault do
            :reader -> hd(readers)
            :guard -> c.guard
            :owner -> Process.whereis(Owner)
          end
          Process.exit(target, :kill)
          peer = close_read(s, 600)
          assert peer.closed
          deaths = monitor_down([c.pid | readers])
          assert Enum.all?(deaths, & &1.down)
          assert ReviewEvidence.get().calls == before
          if fault != :reader, do: assert(wait_until(fn -> not Process.alive?(role) end))
          ReviewEvidence.add(:rows, %{kind: :h2_failure_domain, fault: fault, peer: peer, deaths: deaths, role_down: not Process.alive?(role), verifier_delta: 0})
        after
          :gen_tcp.close(s)
        end
      end)
    end
  end

  test "all owned sink paths reject raw inputs before and after failure teardown" do
    role(fn _, _, port ->
      for event <- [[:thousand_island, :connection, :recv], [:thousand_island, :connection, :async_recv], [:bandit, :request, :exception]] do
        :telemetry.execute(event, %{data: "REVIEW_PRIVATE_BODY", opaque: "REVIEW_PRIVATE_ERROR"}, %{conn: %{path: "REVIEW_PRIVATE_PATH", query: "REVIEW_PRIVATE_QUERY", headers: "REVIEW_PRIVATE_SIGNATURE", trailers: "REVIEW_PRIVATE_TRAILER"}})
      end
      for domain <- [[:mixer_private_transport], [:otp, :ssl], [:otp, :sasl], [:bandit]] do
        :logger.log(:error, "REVIEW_PRIVATE_MESSAGE", %{domain: domain, secret: "REVIEW_PRIVATE_METADATA"})
        :logger.log(:error, %{report: "REVIEW_PRIVATE_REPORT"}, %{domain: domain})
        :logger.log(:notice, %{mixer_transport: 1, event: :webhook_transport, reason: :rejected, count: 1}, %{domain: domain, secret: "REVIEW_PRIVATE_METADATA"})
      end
      crashing = spawn(fn -> raise "REVIEW_PRIVATE_CRASH" end)
      assert Enum.all?(monitor_down([crashing]), & &1.down)
      # Real ignored H2 trailers, malformed pre-Plug parser and arbitrary frame warning.
      for payload <- [
        preface() <> frame(1, 4, 1, headers()) <> frame(0, 0, 1, "REVIEW_PRIVATE_BODY") <> frame(1, 5, 1, elem(HPAX.encode([{:no_store, "x-private-trailer", "REVIEW_PRIVATE_TRAILER"}], HPAX.new(4096)), 0) |> IO.iodata_to_binary()),
        "REVIEW_PRIVATE_BAD_METHOD /REVIEW_PRIVATE_PATH?REVIEW_PRIVATE_QUERY HTTP/1.1\r\nREVIEW_PRIVATE_HEADER\r\n\r\n",
        preface() <> frame(255, 0, 0, "REVIEW_PRIVATE_UNKNOWN_FRAME")
      ] do
        {:ok, s} = tcp(port)
        try do
          :gen_tcp.send(s, payload)
          assert close_read(s, 1_300).closed
        after :gen_tcp.close(s)
        end
        assert wait_until(fn -> Owner.snapshot().connections == 0 end)
      end
      Sinks.record(:rejected)
      Process.sleep(50)
      assert Enum.any?(ReviewEvidence.get().logs, &match?(%{msg: {:report, %{reason: :rejected}}}, &1.event))
      refute Enum.any?(ReviewEvidence.get().logs, & &1.raw)
      ReviewEvidence.add(:rows, %{kind: :privacy, raw_collector_leaks: 0, safe_counter_observed: true, ordinary_crash_and_framework_warnings: true})
    end)
    refute Enum.any?(ReviewEvidence.get().logs, & &1.raw)
  end

  test "pre expiry replay expired and delayed guard permit boundaries" do
    role(fn _, _, _ ->
      parent = self()
      for mode <- [:pre_expiry, :begin_twice, :expired_begin, :expired_finish, :delayed_finish, :connection_generation] do
        span = make_ref()
        pid = spawn(fn ->
          :ok = Owner.register(self(), span, now())
          :ok = Owner.ready(self(), span, now())
          {:ok, permit} = Owner.request(self(), span, {ReviewPlug, []}, now() - 5_000 + 150)
          send(parent, {:minted, self(), permit})
          receive do
            {:go, deadline} ->
              first = if mode == :expired_begin, do: nil, else: Owner.check(permit, :begin)
              if mode in [:expired_begin, :expired_finish], do: wait_until(fn -> now() >= deadline end, 300)
              result = case mode do
                :begin_twice -> Owner.check(permit, :begin)
                :expired_begin -> Owner.check(permit, :begin)
                :connection_generation -> Owner.check({elem(permit, 0), make_ref(), elem(permit, 2)}, :finish)
                _ -> Owner.check(permit, :finish)
              end
              send(parent, {:checked, self(), mode, first, result, now(), deadline})
              Process.sleep(1_000)
          end
        end)
        Process.put({:review_monitor, pid}, Process.monitor(pid))
        permit = receive do {:minted, ^pid, permit} -> permit after 500 -> flunk("permit not minted") end
        c = :sys.get_state(Owner).connections[span]
        deadline = :sys.get_state(Owner).permits[elem(permit, 2)].deadline
        if mode in [:expired_begin, :expired_finish, :delayed_finish], do: :sys.suspend(c.guard)
        send(pid, {:go, deadline})
        if mode == :delayed_finish do
          assert wait_until(fn -> now() >= deadline end, 300)
          :sys.resume(c.guard)
        end
        receive do
          {:checked, ^pid, ^mode, first, result, checked, ^deadline} ->
            if mode == :pre_expiry, do: assert(match?({:ok, _}, result) and checked < deadline), else: assert(match?({:error, _}, result))
            ReviewEvidence.add(:rows, %{kind: :permit_boundary, mode: mode, first: inspect(first), result: inspect(result), checked_ms: checked, deadline: deadline, checked_at_or_after_deadline: checked >= deadline})
        after 700 ->
          assert not Process.alive?(pid)
          ReviewEvidence.add(:rows, %{kind: :permit_boundary, mode: mode, independent_kill_won: true})
        end
        if mode in [:expired_begin, :expired_finish] and Process.alive?(c.guard), do: :sys.resume(c.guard)
        if Process.alive?(pid), do: Process.exit(pid, :kill)
        assert Enum.all?(monitor_down([pid]), & &1.down)
        assert wait_until(fn -> Owner.snapshot().connections == 0 end)
      end
    end)
  end
end

summary = ExUnit.run()
:erlang.trace(:all, false, [:call])
:erlang.trace_pattern({MixerHosted.Billing.WebhookSignature, :verify, 4}, false, [:local])
Process.sleep(30)
send(tracer, :stop)
state = ReviewEvidence.get()
result = %{summary: summary, rows: Enum.reverse(state.rows), logger_events: Enum.map(Enum.reverse(state.logs), fn x -> %{raw: x.raw, event: inspect(x.event, limit: :infinity, printable_limit: :infinity)} end), captures: Enum.reverse(state.captures), inline_verifier_calls: state.calls, actual_verifier_returns: state.returns, trace_call_arguments_suppressed: true, arbitrary_privileged_sink_prevention_claim: false, os_memory_ceiling_claim: false}
File.write!(Path.join(System.fetch_env!("CAPTURE_RESULT_DIR"), "review-independent.json"), Jason.encode!(result, pretty: true))
if summary.failures != 0 or state.calls != state.returns or Enum.any?(state.logs, & &1.raw), do: System.halt(1)
