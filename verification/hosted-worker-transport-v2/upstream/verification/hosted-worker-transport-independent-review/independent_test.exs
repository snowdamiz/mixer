defmodule IndependentWorkerClientTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Dispatch, WorkerConfig, WorkerHTTPAdapter, WorkerTransport, WorkerWire}
  alias MixerHosted.Test.{WorkerData, WorkerTLSFixture}
  @max 9_223_372_036_854_775_807

  setup_all do
    material = WorkerTLSFixture.material()
    assert material.key_dir_removed
    {:ok, material: material}
  end

  setup do
    eventually(fn -> Process.whereis(WorkerTransport) == nil and Process.whereis(WorkerTransport.RoleGuard) == nil end)
    :ok
  end

  defp eventually(f, n \\ 300)
  defp eventually(f, n) when n > 0 do
    if f.(), do: :ok, else: (Process.sleep(5); eventually(f, n - 1))
  end
  defp eventually(_, 0), do: flunk("independent owned resource did not retire")
  defp alive?(pid), do: is_pid(pid) and Process.alive?(pid)
  defp snapshot(pid) do
    :sys.get_state(pid, 500)
  catch
    _, _ -> nil
  end
  defp retired?(s), do: not alive?(s.worker) and Port.info(s.raw) == nil and not alive?(s.connection)
  defp resume(pid) do
    :erlang.resume_process(pid)
  catch
    _, _ -> :ok
  end

  defp start(m, behavior \\ fn socket, _, raw, _, _ -> :ssl.send(socket, raw) end) do
    {:ok, fixture} = IndependentWorkerTLS.start(m, self(), behavior)
    info = IndependentWorkerTLS.info(fixture)
    {:ok, owner} = WorkerTransport.start_fixture(WorkerData.config(m.ca), {127,0,0,1}, info.port)
    Process.unlink(owner)
    guard = Process.whereis(WorkerTransport.RoleGuard)
    on_exit(fn ->
      if alive?(owner), do: GenServer.stop(owner)
      if state = snapshot(guard) do
        flights = Map.keys(state.flights)
        Enum.each(flights, fn flight -> resume(flight); send(flight, :deadline) end)
        eventually(fn -> Enum.all?(flights, &(not alive?(&1))) end)
        if alive?(guard), do: Process.exit(guard, :kill)
      end
      if alive?(fixture) do
        eventually(fn -> map_size(IndependentWorkerTLS.info(fixture).active) == 0 end)
        before = IndependentWorkerTLS.info(fixture)
        assert before.accepted == before.retired
        GenServer.stop(fixture)
      end
    end)
    {fixture, owner, info.tag}
  end

  defp request(tag) do
    receive do
      {:request, ^tag, handler, value, headers, bytes} ->
        Process.put({:request_bytes, tag}, bytes)
        {handler, value, headers}
    after
      2_000 -> flunk("independent TLS fixture did not receive request")
    end
  end

  defp clean(fixture, owner) do
    eventually(fn -> map_size(:sys.get_state(owner).flights) == 0 end)
    eventually(fn -> map_size(:sys.get_state(WorkerTransport.RoleGuard).flights) == 0 end)
    eventually(fn -> map_size(IndependentWorkerTLS.info(fixture).active) == 0 end)
  end

  defp stop(fixture, owner) do
    clean(fixture, owner)
    GenServer.stop(owner)
    eventually(fn -> Process.whereis(WorkerTransport.RoleGuard) == nil end)
    GenServer.stop(fixture)
  end

  defp result(request, observation \\ %{"status" => "absent"}), do: request |> Map.drop(["spec", "deadline_ms"]) |> Map.put("observation", observation)
  defp note(file, value), do: File.write!(Path.join(__DIR__, file), Jason.encode!(value, pretty: true) <> "\n")

  test "fixed request headers, separate auth and fresh exact nonce response", %{material: m} do
    {fixture, owner, tag} = start(m)
    nonces = for command <- [:query, :ensure_started, :stop] do
      assert {:ok, %Dispatch.Observation{status: :absent}} = apply(WorkerHTTPAdapter, command, [WorkerData.request()])
      {_, value, headers} = request(tag)
      [first | rest] = String.split(headers, "\r\n")
      assert first == "POST /internal/mixer-build-worker/v1 HTTP/1.1"
      parsed = Map.new(rest, fn line -> [k,v] = String.split(line, ":", parts: 2); {String.downcase(k), String.trim(v)} end)
      # Finding control: the frozen implementation violates its seven-header contract.
      assert Enum.sort(Map.keys(parsed)) == Enum.sort(~w(host content-type accept accept-encoding connection content-length authorization user-agent))
      assert parsed["user-agent"] == "mint/1.11.0"
      File.write!(Path.join(__DIR__, "authenticated-request-#{command}.http"), Process.get({:request_bytes, tag}))
      assert parsed["authorization"] == "Bearer " <> WorkerData.config(m.ca).token
      assert parsed["host"] == "worker.fixture.invalid:#{IndependentWorkerTLS.info(fixture).port}"
      assert parsed["accept-encoding"] == "identity" and parsed["connection"] == "close"
      assert value["command"] == Atom.to_string(command)
      refute Jason.encode!(value) =~ WorkerData.config(m.ca).token
      value["request_id"]
    end
    assert length(Enum.uniq(nonces)) == 3
    clean(fixture, owner)
  end

  test "each authenticated response binding field and nested owner expires ref must echo", %{material: m} do
    changes = Enum.map(~w(version environment_id pool_id controller_id request_id command operation_id immutable_sha256), fn key -> fn r -> Map.put(r, key, "other") end end) ++ [
      fn r -> put_in(r, ["guard", "owner_id"], "other") end,
      fn r -> put_in(r, ["guard", "expires_at_us"], "1") end,
      fn r -> put_in(r, ["guard", "revision"], 4) end,
      fn r -> put_in(r, ["ref", "attempt"], 2) end,
      fn r -> put_in(r, ["ref", "fence"], @max) end
    ]
    for change <- changes do
      {fixture, owner, _} = start(m, fn socket, r, _, _, _ -> :ssl.send(socket, IndependentWorkerTLS.response_body(Jason.encode!(change.(result(r))))) end)
      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      stop(fixture, owner)
    end
  end

  test "independent strict HTTP parser controls reject alternate framing and field limits", %{material: m} do
    changes = [
      fn raw -> String.replace(raw, "HTTP/1.1 200 OK", "HTTP/1.0 200 OK") end,
      fn raw -> String.replace(raw, "HTTP/1.1 200 OK", "HTTP/1.1 200 O\tK") end,
      fn raw -> String.replace(raw, "Content-Type: application/json", "Content-Type: application/json; charset=utf-8") end,
      fn raw -> String.replace(raw, "Content-Type: application/json", "Content-Type: application/json\r\nCONTENT-LENGTH: 1") end,
      fn raw -> String.replace(raw, "Content-Length: ", "Content-Length: +") end,
      fn raw -> String.replace(raw, "Content-Length: ", "Content-Length: 0") end,
      fn raw -> String.replace(raw, ~r/Content-Length: [0-9]+/, "Content-Length: 32769") end,
      fn raw -> String.replace(raw, "Content-Type:", "Content-Type :") end,
      fn raw -> String.replace(raw, "Connection: close", "Connection: close\r\nUpgrade: websocket") end,
      fn raw -> String.replace(raw, "Connection: close", "Connection: close\r\nX-Null: a" <> <<0>> <> "b") end,
      fn raw -> String.replace(raw, "Connection: close", "Connection: close\r\nX-L: " <> String.duplicate("x", 2043)) end,
      fn raw -> String.replace(raw, "Connection: close", "Connection: close\r\n" <> Enum.map_join(1..30, "\r\n", &"x-#{&1}: x")) end,
      fn raw -> String.replace(raw, "Connection: close", "Connection: close\r\n" <> Enum.map_join(1..5, "\r\n", &"x-#{&1}: " <> String.duplicate("x", 1800))) end,
      fn raw -> "HTTP/1.1 103 Early Hints\r\n\r\n" <> raw end,
      fn raw -> String.replace(raw, "Content-Type: application/json", "Content-Type: application/json\r\nTransfer-Encoding: identity") end
    ]
    for change <- changes do
      {fixture, owner, _} = start(m, fn socket, _, raw, _, _ -> :ssl.send(socket, change.(raw)) end)
      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      stop(fixture, owner)
    end
  end

  test "response body limit includes whitespace and JSON lexing rejects duplicates depth and invalid UTF8", %{material: m} do
    for limit <- [32_768, 32_769] do
      {fixture, owner, _} = start(m, fn socket, r, _, _, _ ->
        body = Jason.encode!(result(r))
        :ssl.send(socket, IndependentWorkerTLS.response_body(body <> String.duplicate(" ", limit - byte_size(body))))
      end)
      observed = WorkerHTTPAdapter.query(WorkerData.request())
      if limit == 32_768, do: assert({:ok, %Dispatch.Observation{status: :absent}} = observed), else: assert(observed == {:error, :uncertain})
      stop(fixture, owner)
    end
    bodies = [
      fn r -> Jason.encode!(result(r)) |> String.replace("\"status\":\"absent\"", "\"status\":\"absent\",\"st\\u0061tus\":\"running\"") end,
      fn r -> Jason.encode!(result(r)) |> String.replace("\"version\":1", "\"version\":1e0") end,
      fn _ -> "{\"x\":" <> String.duplicate("[", 9) <> "0" <> String.duplicate("]", 9) <> "}" end,
      fn _ -> "{\"x\":\"" <> String.duplicate("a", 8193) <> "\"}" end,
      fn _ -> "{\"x\":[" <> Enum.map_join(1..513, ",", fn _ -> "0" end) <> "]}" end,
      fn _ -> "{\"x\":\"" <> <<255>> <> "\"}" end
    ]
    for body <- bodies do
      {fixture, owner, _} = start(m, fn socket, r, _, _, _ -> :ssl.send(socket, IndependentWorkerTLS.response_body(body.(r))) end)
      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      stop(fixture, owner)
    end
  end

  test "fragmented genuine EOF succeeds while delayed extra byte and truncated responses fail", %{material: m} do
    {fixture, owner, _} = start(m, fn socket, _, raw, _, _ ->
      Enum.each(:binary.bin_to_list(raw), fn byte -> :ok = :ssl.send(socket, <<byte>>) end)
    end)
    assert {:ok, %Dispatch.Observation{status: :absent}} = WorkerHTTPAdapter.query(WorkerData.request())
    stop(fixture, owner)
    for mode <- [:delayed_extra, :truncated_body, :truncated_header, :second_response] do
      {fixture, owner, _} = start(m, fn socket, _, raw, _, _ ->
        case mode do
          :delayed_extra -> :ssl.send(socket, raw); Process.sleep(100); :ssl.send(socket, "X")
          :truncated_body -> :ssl.send(socket, binary_part(raw, 0, byte_size(raw) - 1))
          :truncated_header -> :ssl.send(socket, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n")
          :second_response -> :ssl.send(socket, raw <> raw)
        end
      end)
      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      stop(fixture, owner)
    end
  end

  @tag timeout: 10_000
  test "progress across headers body and EOF never resets absolute five-second deadline", %{material: m} do
    {fixture, owner, _} = start(m, fn socket, _, raw, _, _ ->
      [headers, body] = String.split(raw, "\r\n\r\n", parts: 2)
      Process.sleep(1800)
      :ssl.send(socket, headers <> "\r\n\r\n")
      Process.sleep(1800)
      :ssl.send(socket, body)
      Process.sleep(1800)
    end)
    before = System.monotonic_time(:millisecond)
    assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
    elapsed = System.monotonic_time(:millisecond) - before
    assert elapsed >= 4_900 and elapsed < 5_750
    note("absolute-deadline.json", %{elapsed_ms: elapsed, staged_delays_ms: [1800,1800,1800], result: "uncertain", deadline_ms: 5000})
    clean(fixture, owner)
  end

  test "raw socket and SSL handler register before authenticated send and caller loss closes them", %{material: m} do
    {fixture, owner, tag} = start(m, :hold)
    caller = spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request(tag)
    [flight] = Map.keys(:sys.get_state(owner).flights)
    s = :sys.get_state(flight)
    assert is_port(s.raw) and is_pid(s.connection) and s.socket != nil
    assert Port.info(s.raw, :connected) == {:connected, s.connection}
    assert s.raw_down == false and s.connection_down == false and s.worker_down == false
    Process.exit(caller, :kill)
    eventually(fn -> not alive?(flight) and retired?(s) end)
    clean(fixture, owner)
  end

  test "handshake registered raw socket closes on caller death before credentials", %{material: m} do
    {fixture, owner, tag} = start(m, :handshake_barrier)
    caller = spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:handshake, ^tag, handler}, 2000
    [flight] = Map.keys(:sys.get_state(owner).flights)
    eventually(fn -> is_port(:sys.get_state(flight).raw) end)
    s = :sys.get_state(flight)
    assert s.socket == nil
    Process.exit(caller, :kill)
    eventually(fn -> not alive?(flight) and retired?(s) end)
    send(handler, :handshake)
    refute_receive {:request, ^tag, _, _, _, _}, 50
    clean(fixture, owner)
  end

  test "worker death retains permit while Flight is paused and retires after cleanup observation", %{material: m} do
    {fixture, owner, tag} = start(m, :hold)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request(tag)
    [flight] = Map.keys(:sys.get_state(owner).flights)
    s = :sys.get_state(flight)
    :erlang.suspend_process(flight)
    try do
      Process.exit(s.worker, :kill)
      Process.sleep(25)
      assert map_size(:sys.get_state(owner).flights) == 1
      assert map_size(:sys.get_state(WorkerTransport.RoleGuard).flights) == 1
    after
      resume(flight)
    end
    assert {:error, :uncertain} = Task.await(caller)
    eventually(fn -> retired?(s) end)
    clean(fixture, owner)
  end

  test "owner loss leaves RoleGuard closed until a paused Flight actually retires", %{material: m} do
    {fixture, owner, tag} = start(m, :hold)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request(tag)
    [flight] = Map.keys(:sys.get_state(owner).flights)
    s = :sys.get_state(flight)
    guard = Process.whereis(WorkerTransport.RoleGuard)
    :erlang.suspend_process(flight)
    try do
      Process.exit(owner, :kill)
      assert {:error, :uncertain} = Task.await(caller)
      eventually(fn -> :sys.get_state(guard).closed end)
      assert alive?(s.worker) and alive?(s.connection) and Port.info(s.raw) != nil
      assert {:error, :unavailable} = WorkerTransport.start_fixture(WorkerData.config(m.ca), {127,0,0,1}, IndependentWorkerTLS.info(fixture).port)
    after
      resume(flight)
    end
    eventually(fn -> not alive?(guard) and not alive?(flight) and retired?(s) end)
    eventually(fn -> map_size(IndependentWorkerTLS.info(fixture).active) == 0 end)
  end

  test "normal Flight system termination is accepted as permit retirement", %{material: m} do
    {fixture, owner, tag} = start(m, :hold)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request(tag)
    [flight] = Map.keys(:sys.get_state(owner).flights)
    s = :sys.get_state(flight)
    :erlang.suspend_process(s.connection)
    before = System.monotonic_time(:millisecond)
    stopper = Task.async(fn -> GenServer.stop(flight, :normal) end)
    blocked = Task.yield(stopper, 100) == nil
    resume(s.connection)
    assert :ok = Task.await(stopper, 2_000)
    after_stop = %{worker_alive: alive?(s.worker), ssl_handler_alive: alive?(s.connection), raw_open: Port.info(s.raw) != nil}
    assert {:error, :uncertain} = Task.await(caller)
    eventually(fn -> map_size(:sys.get_state(WorkerTransport.RoleGuard).flights) == 0 end)
    assert :sys.get_state(WorkerTransport.RoleGuard).quarantined == false
    note("normal-flight-stop.json", %{external_system_stop: "normal", blocked_while_ssl_handler_suspended_at_100_ms: blocked, ssl_handler_resumed_before_awaiting_stop: true, elapsed_ms: System.monotonic_time(:millisecond) - before, observations_immediately_after_stop: after_stop, role_quarantined: false, scope: "real-TLS-handler-suspended-before-normal-GenServer-stop"})
    eventually(fn -> retired?(s) end)
    clean(fixture, owner)
  end

  test "RoleGuard loss permits replacement role while paused old SSL flight remains live", %{material: m} do
    {fixture, owner, tag} = start(m, :hold)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request(tag)
    [flight] = Map.keys(:sys.get_state(owner).flights)
    old = :sys.get_state(flight)
    guard = Process.whereis(WorkerTransport.RoleGuard)
    :erlang.suspend_process(flight)
    try do
      Process.exit(guard, :kill)
      eventually(fn -> not alive?(guard) end)
      Process.exit(owner, :kill)
      assert {:error, :uncertain} = Task.await(caller)
      eventually(fn -> not alive?(owner) end)
      assert alive?(old.worker) and alive?(old.connection) and Port.info(old.raw) != nil
      {:ok, replacement} = WorkerTransport.start_fixture(WorkerData.config(m.ca), {127,0,0,1}, IndependentWorkerTLS.info(fixture).port)
      Process.unlink(replacement)
      new_guard = Process.whereis(WorkerTransport.RoleGuard)
      callers = for _ <- 1..16, do: spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
      try do
        for _ <- 1..16, do: request(tag)
        assert alive?(old.worker) and alive?(old.connection) and Port.info(old.raw) != nil
        info = IndependentWorkerTLS.info(fixture)
        assert map_size(info.active) == 17 and info.accepted == 17
        assert map_size(:sys.get_state(replacement).flights) == 16
        assert map_size(:sys.get_state(new_guard).flights) == 16
        note("guard-loss-reproduction.json", %{old_flight_paused: true, old_worker_alive: alive?(old.worker), old_ssl_handler_alive: alive?(old.connection), old_raw_open: Port.info(old.raw) != nil, replacement_role_accepted: true, replacement_flights: 16, live_server_tls_handlers: map_size(info.active), total_accepted_connections: info.accepted, expected_global_limit: 16, role_guard_killed: true, old_owner_killed: true, scope: "isolated-BEAM-internal-fault-injection-not-remote-input"})
      after
        Enum.each(callers, &Process.exit(&1, :kill))
        eventually(fn -> map_size(:sys.get_state(replacement).flights) == 0 end)
        eventually(fn -> map_size(:sys.get_state(new_guard).flights) == 0 end)
        GenServer.stop(replacement)
        eventually(fn -> not alive?(new_guard) end)
      end
    after
      resume(flight)
      send(flight, :deadline)
    end
    eventually(fn -> not alive?(flight) and retired?(old) end)
    eventually(fn -> map_size(IndependentWorkerTLS.info(fixture).active) == 0 end)
  end

  test "decimal exactness and configuration type boundaries fail closed", %{material: m} do
    assert {:ok, 0} = WorkerWire.decimal("0", 0, 32)
    assert {:ok, @max} = WorkerWire.decimal(Integer.to_string(@max), 1, @max)
    for v <- [nil, true, 1, 1.0, "", "00", "01", "+1", "-0", "-1", "1.0", "1e0", " 1", "1\n", "9223372036854775808", "99999999999999999999", <<255>>] do
      assert :error = WorkerWire.decimal(v, 1, @max)
    end
    env = WorkerData.environment()
    value = Jason.decode!(env["MIXER_BUILD_WORKER_CONFIG"])
    for changed <- [
      put_in(value, ["endpoint", "port"], 443.0), put_in(value, ["endpoint", "port"], "443"),
      put_in(value, ["endpoint", "host"], "Worker.fixture.invalid"), put_in(value, ["endpoint", "host"], "worker.fixture.invalid."),
      put_in(value, ["endpoint", "host"], "worker.fixture.invalid/path"), put_in(value, ["endpoint", "path"], "/internal/mixer-build-worker/v1?token=x"),
      Map.put(value, "version", 1.0), Map.put(value, "platforms", "ios"), Map.put(value, "resolvers", ["1.1.1.01"])
    ] do
      assert_raise ArgumentError, "invalid worker configuration", fn -> WorkerConfig.load!(Map.put(env, "MIXER_BUILD_WORKER_CONFIG", Jason.encode!(changed)), :processor, [m.ca]) end
    end
    for roots <- [[], [<<0>>], [String.duplicate("x", 65_537)], List.duplicate(m.ca, 257)] do
      assert_raise ArgumentError, "invalid worker configuration", fn -> WorkerConfig.load!(env, :processor, roots) end
    end
    for mutate <- [fn c -> %{c | endpoint: %{c.endpoint | port: 443.0}} end, fn c -> %{c | token: "bad"} end, fn c -> %{c | platforms: [:ios, :other]} end] do
      c = mutate.(WorkerData.config(m.ca))
      refute WorkerConfig.validated?(c)
      assert {:error, :unavailable} = WorkerTransport.start_fixture(c, {127,0,0,1}, 1)
    end
  end
end
