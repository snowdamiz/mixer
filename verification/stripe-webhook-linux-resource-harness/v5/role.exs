# Private R14 phase fixture. The phase is a trusted launcher mode, never HTTP.
Code.prepend_paths(Path.wildcard("/opt/mixer/release/lib/*/ebin"))

defmodule MixerHarness.Control do
  @on_load :load
  def load, do: :erlang.load_nif(~c"/opt/harness/control_nif", 0)
  def secure_role, do: :erlang.nif_error(:not_loaded)
  def receive_control, do: :erlang.nif_error(:not_loaded)
  def send_control(_), do: :erlang.nif_error(:not_loaded)
end

defmodule MixerHarness.Phase do
  use Agent
  @phases ~w(idle h1_body h2_reader_frozen blocked_response)
  @body "MIXER_BODY_SENTINEL"
  @signature "MIXER_SIGNATURE_SENTINEL"
  def phase_names, do: @phases
  def body, do: @body
  def signature, do: @signature
  def start(phase) when phase in @phases do
    Agent.start_link(fn -> %{phase: phase, open: true, owners: [], activeOwners: [], captures: 0,
      responseChunks: 0, responseFinished: false, failures: 0} end, name: __MODULE__)
  end
  def snapshot, do: Agent.get(__MODULE__, & &1)
  def enter(owner) do
    Agent.get_and_update(__MODULE__, fn state ->
      {{state.open, state.phase}, %{state | owners: Enum.uniq([owner | state.owners]),
        activeOwners: Enum.uniq([owner | state.activeOwners])}}
    end)
  end
  def leave(owner), do: Agent.update(__MODULE__, &%{&1 | activeOwners: List.delete(&1.activeOwners, owner)})
  def captured(body, signatures) do
    exact = body == @body and signatures == [@signature]
    Agent.update(__MODULE__, &%{&1 | captures: &1.captures + 1,
      failures: &1.failures + if(exact, do: 0, else: 1)})
  end
  def chunked do
    Agent.update(__MODULE__, &%{&1 | responseChunks: &1.responseChunks + 1})
  end
  def response_finished, do: Agent.update(__MODULE__, &%{&1 | responseFinished: true})
  def close do
    Agent.get_and_update(__MODULE__, fn state -> {state, %{state | open: false}} end)
  end
end

defmodule MixerHarness.PhasePlug do
  def init(opts), do: opts
  def call(conn, _) do
    case MixerHarness.Phase.enter(self()) do
      {true, phase} ->
        try do
          case MixerHosted.Billing.WebhookTransport.capture(conn) do
            {:ok, captured, latest} ->
              MixerHarness.Phase.captured(captured.raw_body, captured.signature_header_values)
              if phase == "blocked_response", do: blocked_response(latest),
                else: Plug.Conn.send_resp(latest, 418, "")
            {:error, _, latest} -> Plug.Conn.send_resp(latest, 400, "")
          end
        after
          MixerHosted.Billing.WebhookTransport.dispose()
          MixerHarness.Phase.leave(self())
        end
      _ -> Plug.Conn.send_resp(conn, 503, "")
    end
  end
  defp blocked_response(conn) do
    conn = Plug.Conn.send_chunked(conn, 418)
    chunk = :binary.copy(<<0x61>>, 16_384)
    result = Enum.reduce_while(1..1_024, conn, fn _, current ->
      case Plug.Conn.chunk(current, chunk) do
        {:ok, next} ->
          MixerHarness.Phase.chunked()
          {:cont, next}
        {:error, _} -> {:halt, current}
      end
    end)
    MixerHarness.Phase.response_finished()
    result
  end
end

defmodule MixerHarness.PhaseRole do
  @phases ~w(idle h1_body h2_reader_frozen blocked_response)
  def check(true), do: :ok
  def check(_), do: exit(:phase_unavailable)
  def emit(event, counters) do
    IO.binwrite(:stdio, Jason.encode!(Map.merge(%{schema: 1, event: event}, counters)) <> "\n")
  end
  defp relative_ns(start), do: System.monotonic_time(:nanosecond) - start
  defp hook(stage) do
    selected = System.fetch_env!("MIXER_HARNESS_FAULT_STAGE")
    if selected == stage do
      # The closed numeric stage mapping is compiled in the controller contract.
      stage_id = %{"role_nif_secured" => 21, "role_transport_started" => 22,
        "role_phase_armed" => 23, "role_ready_sent" => 24}[stage]
      emit("lifecycle", %{stage: stage_id, reached: 1, injected: 1})
      System.halt(79)
    end
  end
  def main do
    {:ok, pre_dumpable} = MixerHarness.Control.secure_role()
    Logger.configure(level: :emergency)
    for app <- [:crypto, :ssl, :bandit], do: {:ok, _} = Application.ensure_all_started(app)
    phase = System.fetch_env!("MIXER_HARNESS_PHASE")
    check(phase in @phases)
    generation = System.fetch_env!("MIXER_HARNESS_GENERATION")
    check(byte_size(generation) == 32 and Enum.all?(:binary.bin_to_list(generation),
      &(&1 in ?0..?9 or &1 in ?a..?f)))
    hook("role_nif_secured")
    isolation!()
    emit("isolation", %{capabilities: 0, dumpable: 0, readOnlyRoot: 1,
      inheritedFDs: 4, roleNamespacePid: 2, preInitDumpable: pre_dumpable})
    {:ok, _} = MixerHarness.Phase.start(phase)
    {:ok, supervisor} = MixerHosted.Billing.WebhookTransport.start_link(MixerHarness.PhasePlug)
    Process.unlink(supervisor)
    listener = Supervisor.which_children(supervisor)
      |> Enum.find_value(fn {id, pid, _, _} -> if match?({Bandit, _}, id), do: pid end)
    {:ok, {_, port}} = ThousandIsland.listener_info(listener)
    hook("role_transport_started")
    start = System.monotonic_time(:nanosecond)
    fixture = arm(phase, port)
    check(MixerHarness.Phase.snapshot().failures == 0)
    phase_id = Enum.find_index(@phases, &(&1 == phase)) + 1
    emit("phase_armed", %{phase: phase_id, owners: length(fixture.owners),
      readerSuspended: if(phase == "h2_reader_frozen", do: 1, else: 0),
      responseBlocked: if(phase == "blocked_response", do: 1, else: 0),
      queuedMessages: fixture.queuedMessages, queuedSocketBytes: fixture.queuedSocketBytes, wireSentBytes: fixture.sentBytes,
      roleRelativeNs: relative_ns(start), preInitDumpable: pre_dumpable})
    hook("role_phase_armed")
    role = self()
    # Pinned Elixir1.20.4 System.trap_signal semantics: the custom trap precedes
    # default handling. Its fixed bounded acknowledgement prevents returning to
    # default VM shutdown before this private role completes its observations.
    {:ok, :mixer_private_term} = System.trap_signal(:sigterm, :mixer_private_term, fn ->
      callback_start = System.monotonic_time(:nanosecond)
      send(role, {:mixer_private_term, self()})
      completed = receive do
        :mixer_private_term_complete -> 1
      after
        1_000 -> 0
      end
      emit("term_callback", %{phase: phase_id, completed: completed,
        elapsedNs: System.monotonic_time(:nanosecond) - callback_start})
      send(role, :mixer_private_term_callback_observed)
      :ok
    end)
    :ok = MixerHarness.Control.send_control("ready " <> generation <> " " <> Integer.to_string(port))
    hook("role_ready_sent")
    # The controller closes the gate with stop, then sends actual owned TERM.
    emit("case", %{checks: 1, failures: 0, sentBytes: fixture.sentBytes,
      ownersDown: 0, lateSuccesses: 0})
    stop_loop(generation, supervisor, fixture, phase, phase_id, start, System.monotonic_time(:millisecond))
  end

  defp isolation! do
    status = File.read!("/proc/self/status") |> String.split("\n", trim: true)
    for key <- ["CapEff", "CapPrm", "CapInh", "CapAmb", "CapBnd"] do
      row = Enum.find(status, &String.starts_with?(&1, key <> ":"))
      check((row |> String.split() |> List.last() |> String.to_integer(16)) == 0)
    end
    check(not File.exists?("/sys/fs/cgroup"))
    mounts = File.read!("/proc/self/mountinfo") |> String.split("\n", trim: true)
    for target <- ["/", "/proc"] do
      row = Enum.find(mounts, &(Enum.at(String.split(&1), 4) == target))
      check("ro" in (row |> String.split() |> Enum.at(5) |> String.split(",")))
    end
    tmp = Enum.find(mounts, &(Enum.at(String.split(&1), 4) == "/tmp"))
    check(String.contains?(tmp, " - tmpfs "))
    super_options = tmp |> String.split(" - ") |> List.last() |> String.split() |> List.last() |> String.split(",")
    check("size=8192k" in super_options or "size=8388608" in super_options)
    interfaces = File.read!("/proc/net/dev") |> String.split("\n", trim: true) |> Enum.drop(2)
    check(Enum.all?(interfaces, &(String.starts_with?(String.trim(&1), "lo:"))))
    routes = File.read!("/proc/net/route") |> String.split("\n", trim: true) |> tl()
    check(Enum.all?(routes, &(hd(String.split(&1)) == "lo")))
    routes6 = File.read!("/proc/net/ipv6_route") |> String.split("\n", trim: true)
    check(Enum.all?(routes6, &(List.last(String.split(&1)) == "lo")))
  end

  defp connect(port) do
    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, port,
      [:binary, active: false, nodelay: true, recbuf: 1_024,
       send_timeout: 200, send_timeout_close: true], 200)
    socket
  end
  defp h1(body, length) do
    ["POST /api/v1/webhooks/stripe HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n",
      "Stripe-Signature: ", MixerHarness.Phase.signature(), "\r\nContent-Length: ",
      Integer.to_string(length), "\r\n\r\n", body] |> IO.iodata_to_binary()
  end
  defp h2_frame(type, flags, stream, data) do
    <<byte_size(data)::24, type::8, flags::8, 0::1, stream::31, data::binary>>
  end
  defp h2_headers do
    headers = [{":method", "POST"}, {":scheme", "http"}, {":authority", "localhost"},
      {":path", "/api/v1/webhooks/stripe"}, {"content-type", "application/json"},
      {"stripe-signature", MixerHarness.Phase.signature()}, {"content-length", "1048576"}]
    {encoded, _} = HPAX.encode(Enum.map(headers, fn {k, v} -> {:no_store, k, v} end),
      HPAX.new(4096, huffman_encoding: :never))
    IO.iodata_to_binary(encoded)
  end
  defp owners do
    Enum.filter(MixerHarness.Phase.snapshot().activeOwners, &Process.alive?/1)
  end
  defp wait_until(fun, deadline) do
    case fun.() do
      {:ok, value} -> value
      _ ->
        check(System.monotonic_time(:millisecond) < deadline)
        Process.sleep(5)
        wait_until(fun, deadline)
    end
  end
  defp wait_owner do
    wait_until(fn -> case owners() do [pid] -> {:ok, pid}; _ -> :wait end end,
      System.monotonic_time(:millisecond) + 400)
  end
  defp arm("idle", _) do
    check(owners() == [] and MixerHarness.Phase.snapshot().captures == 0)
    %{owners: [], sockets: [], queuedMessages: 0, queuedSocketBytes: 0, sentBytes: 0}
  end
  defp arm("h1_body", port) do
    socket = connect(port)
    wire = h1("a", 1_048_576)
    :ok = :gen_tcp.send(socket, wire)
    owner = wait_owner()
    check(MixerHarness.Phase.snapshot().captures == 0)
    check(Process.alive?(owner))
    %{owners: [owner], sockets: [socket], queuedMessages: 0, queuedSocketBytes: 0, sentBytes: byte_size(wire)}
  end
  defp arm("h2_reader_frozen", port) do
    socket = connect(port)
    preface = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n" <>
      h2_frame(4, 0, 0, <<>>) <> h2_frame(1, 4, 1, h2_headers())
    :ok = :gen_tcp.send(socket, preface)
    owner = wait_owner()
    true = :erlang.suspend_process(owner)
    data = :binary.copy(<<0x61>>, 16_384)
    frame = h2_frame(0, 0, 1, data)
    for _ <- 1..64, do: :ok = :gen_tcp.send(socket, frame)
    for n <- 1..8, do: :ok = :gen_tcp.send(socket, h2_frame(6, 0, 0, <<n::64>>))
    check(Process.info(owner, :status) == {:status, :suspended})
    queued = wait_until(fn ->
      case Process.info(owner, :message_queue_len) do
        {:message_queue_len, n} when n > 0 -> {:ok, n}
        _ -> :wait
      end
    end, System.monotonic_time(:millisecond) + 200)
    check(MixerHarness.Phase.snapshot().captures == 0)
    %{owners: [owner], sockets: [socket], queuedMessages: queued, queuedSocketBytes: 0,
      sentBytes: byte_size(preface) + 64 * byte_size(frame) + 8 * 17}
  end
  defp arm("blocked_response", port) do
    socket = connect(port)
    wire = h1(MixerHarness.Phase.body(), byte_size(MixerHarness.Phase.body()))
    :ok = :gen_tcp.send(socket, wire)
    owner = wait_owner()
    deadline = System.monotonic_time(:millisecond) + 1_200
    {chunks, queue} = blocked(owner, port, deadline, nil)
    check(chunks < 1_024 and MixerHarness.Phase.snapshot().captures == 1)
    %{owners: [owner], sockets: [socket], queuedMessages: 0, queuedSocketBytes: queue,
      sentBytes: byte_size(wire) + chunks * 16_384, serverPort: port, armedChunks: chunks}
  end
  defp blocked(owner, port, deadline, previous) do
    check(System.monotonic_time(:millisecond) < deadline and Process.alive?(owner))
    state = MixerHarness.Phase.snapshot()
    queue = tcp_send_queue(port)
    waiting = Process.info(owner, :status) == {:status, :waiting}
    now = System.monotonic_time(:millisecond)
    if waiting and queue > 0 and not state.responseFinished do
      case previous do
        {chunks, since} when chunks == state.responseChunks and now - since >= 200 -> {chunks, queue}
        {chunks, _} when chunks == state.responseChunks ->
          Process.sleep(10)
          blocked(owner, port, deadline, previous)
        _ ->
          Process.sleep(10)
          blocked(owner, port, deadline, {state.responseChunks, now})
      end
    else
      Process.sleep(10)
      blocked(owner, port, deadline, nil)
    end
  end
  defp tcp_send_queue(port) do
    File.read!("/proc/net/tcp") |> String.split("\n", trim: true) |> tl()
      |> Enum.reduce(0, fn row, sum ->
        fields = String.split(row)
        [_, hex_port] = Enum.at(fields, 1) |> String.split(":")
        if String.to_integer(hex_port, 16) == port do
          [tx, _] = Enum.at(fields, 4) |> String.split(":")
          sum + String.to_integer(tx, 16)
        else
          sum
        end
      end)
  end
  defp sample do
    {heap, binary, mailbox} = Enum.reduce(Process.list(), {0, 0, 0}, fn pid, {h, b, m} ->
      case Process.info(pid, [:total_heap_size, :binary, :message_queue_len]) do
        nil -> {h, b, m}
        info ->
          bytes = Enum.reduce(info[:binary], 0, fn {_, size, _}, n -> n + size end)
          {h + info[:total_heap_size], b + bytes, m + info[:message_queue_len]}
      end
    end)
    emit("sample", %{beamTotalBytes: :erlang.memory(:total), heapWords: heap,
      referencedBinaryBytes: binary, mailboxLength: mailbox, processes: :erlang.system_info(:process_count)})
  end
  defp still_armed?("idle", _, _), do: MixerHarness.Phase.snapshot().captures == 0 and owners() == []
  defp still_armed?("h1_body", fixture, _) do
    Enum.all?(fixture.owners, &(&1 in owners() and Process.info(&1, :status) == {:status, :waiting})) and
      MixerHarness.Phase.snapshot().captures == 0
  end
  defp still_armed?("h2_reader_frozen", fixture, _) do
    Enum.all?(fixture.owners, fn owner ->
      owner in owners() and Process.info(owner, :status) == {:status, :suspended} and
        case Process.info(owner, :message_queue_len) do {:message_queue_len, n} -> n > 0; _ -> false end
    end) and
      MixerHarness.Phase.snapshot().captures == 0
  end
  defp still_armed?("blocked_response", fixture, _) do
    state = MixerHarness.Phase.snapshot()
    Enum.all?(fixture.owners, &(&1 in owners() and Process.info(&1, :status) == {:status, :waiting})) and
      state.captures == 1 and not state.responseFinished and state.responseChunks == fixture.armedChunks and
      tcp_send_queue(fixture.serverPort) > 0
  end
  defp stop_loop(generation, supervisor, fixture, phase, phase_id, start, last_sample) do
    now = System.monotonic_time(:millisecond)
    if now - last_sample >= 20, do: sample()
    case MixerHarness.Control.receive_control() do
      :again ->
        Process.sleep(2)
        stop_loop(generation, supervisor, fixture, phase, phase_id, start,
          if(now - last_sample >= 20, do: now, else: last_sample))
      {:ok, "stop " <> received} when received == generation ->
        alive_at_gate = Enum.count(fixture.owners, &Process.alive?/1)
        armed_at_gate = still_armed?(phase, fixture, phase_id)
        before = MixerHarness.Phase.close()
        gate_ns = relative_ns(start)
        emit("phase_gate", %{phase: phase_id, gateClosed: 1, gateClosedNs: gate_ns,
          ownersAliveAtGate: alive_at_gate, phaseArmedAtGate: if(armed_at_gate, do: 1, else: 0),
          capturesAtGate: before.captures})
        # Do not kill owners, stop transport or send stopped before actual TERM.
        await_term(generation, supervisor, fixture, phase, phase_id, start, before, gate_ns,
          System.monotonic_time(:millisecond) + 1_000)
      _ -> System.halt(1)
    end
  end
  defp await_term(generation, supervisor, fixture, phase, phase_id, start, before, gate_ns, deadline) do
    check(System.monotonic_time(:millisecond) < deadline)
    receive do
      {:mixer_private_term, callback} when is_pid(callback) ->
        check(callback == Process.whereis(:erl_signal_server))
        term_ns = relative_ns(start)
        alive_at_term = Enum.count(fixture.owners, &Process.alive?/1)
        armed_at_term = still_armed?(phase, fixture, phase_id)
        check(not MixerHarness.Phase.snapshot().open)
        monitors = Enum.map(fixture.owners, &{Process.monitor(&1), &1})
        for owner <- fixture.owners, do: Process.exit(owner, :kill)
        kill_ns = relative_ns(start)
        Supervisor.stop(supervisor, :normal, 600)
        down = Enum.count(monitors, fn {ref, _} ->
          receive do {:DOWN, ^ref, :process, _, _} -> true after 100 -> false end
        end)
        closed = Enum.count(fixture.sockets, &observe_peer_closed?(&1, 33_554_432,
          System.monotonic_time(:millisecond) + 200))
        after_stop = MixerHarness.Phase.snapshot()
        emit("phase_result", %{phase: phase_id, gateClosed: if(after_stop.open, do: 0, else: 1),
          gateClosedNs: gate_ns, killRequestedNs: kill_ns, ownersExpected: length(fixture.owners),
          ownersDown: down, peersExpected: length(fixture.sockets), peersClosed: closed,
          capturesBeforeStop: before.captures, capturesAfterStop: after_stop.captures,
          captureFailures: after_stop.failures, observedStopNs: relative_ns(start),
          ownersAliveAtTerm: alive_at_term, phaseArmedAtTerm: if(armed_at_term, do: 1, else: 0),
          termObservedCount: 1, termObservedNs: term_ns})
        :ok = MixerHarness.Control.send_control("stopped " <> generation <> " completed")
        send(callback, :mixer_private_term_complete)
        receive do :mixer_private_term_callback_observed -> :ok after 100 -> System.halt(1) end
        System.halt(0)
      _ -> System.halt(1)
    after
      2 ->
        sample()
        await_term(generation, supervisor, fixture, phase, phase_id, start, before, gate_ns, deadline)
    end
  end
  defp observe_peer_closed?(socket, remaining, deadline) do
    # Backpressure has already been observed and original owners killed. A
    # bounded client-only receive window now permits observing real FIN/RST
    # without retaining response data. Server policy and stop deadline stay fixed.
    case :inet.setopts(socket, recbuf: 1_048_576) do
      :ok -> peer_closed?(socket, remaining, deadline)
      _ -> :gen_tcp.close(socket); false
    end
  end
  defp peer_closed?(socket, remaining, deadline) do
    if remaining > 0 and System.monotonic_time(:millisecond) < deadline do
      case :gen_tcp.recv(socket, 0, 10) do
        {:error, reason} when reason in [:closed, :econnreset] -> :gen_tcp.close(socket); true
        {:error, :timeout} -> peer_closed?(socket, remaining, deadline)
        {:ok, bytes} -> peer_closed?(socket, remaining - byte_size(bytes), deadline)
        _ -> :gen_tcp.close(socket); false
      end
    else
      :gen_tcp.close(socket)
      false
    end
  end
end

try do
  MixerHarness.PhaseRole.main()
rescue
  _ -> System.halt(1)
catch
  :exit, :phase_unavailable -> System.halt(78)
  _, _ -> System.halt(1)
end
