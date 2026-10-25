defmodule MixerHosted.Builds.WorkerTransportTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Dispatch, WorkerHTTPAdapter, WorkerTransport}
  alias MixerHosted.Test.{WorkerData, WorkerTLSFixture}

  setup_all do
    material = WorkerTLSFixture.material()
    unrelated = WorkerTLSFixture.material()
    assert material.key_dir_removed and unrelated.key_dir_removed
    {:ok, material: material, unrelated: unrelated}
  end

  setup do
    on_exit(fn -> if pid = Process.whereis(WorkerTransport), do: GenServer.stop(pid) end)
    :ok
  end

  defp start(m, mode \\ :normal, change \\ &Function.identity/1) do
    eventually(fn -> Process.whereis(WorkerTransport.RoleGuard) == nil end)
    {:ok, fixture} = WorkerTLSFixture.start_link({m, mode})
    c = change.(WorkerData.config(m.ca))

    {:ok, owner} =
      WorkerTransport.start_fixture(c, {127, 0, 0, 1}, WorkerTLSFixture.info(fixture).port)

    Process.unlink(owner)
    {fixture, owner, c}
  end

  defp eventually(fun, attempts \\ 200)

  defp eventually(fun, attempts) when attempts > 0 do
    if fun.(),
      do: :ok,
      else:
        (
          Process.sleep(10)
          eventually(fun, attempts - 1)
        )
  end

  defp eventually(_, 0), do: flunk("owned resource did not retire")

  defp clean(fixture, owner) do
    eventually(fn -> map_size(:sys.get_state(owner).flights) == 0 end)
    eventually(fn -> map_size(:sys.get_state(WorkerTransport.RoleGuard).flights) == 0 end)
    eventually(fn -> MapSet.size(WorkerTLSFixture.info(fixture).active) == 0 end)
    info = WorkerTLSFixture.info(fixture)
    assert info.accepted == info.closed
  end

  defp stop_owner(owner) do
    GenServer.stop(owner)
    eventually(fn -> Process.whereis(WorkerTransport.RoleGuard) == nil end)
  end

  test "unconfigured adapter is unavailable without touching network" do
    assert {:error, :unavailable} = WorkerHTTPAdapter.query(WorkerData.request())
  end

  test "actual verified TLS sends one fixed authenticated command and receives exact binding", %{
    material: m
  } do
    {fixture, owner, config} = start(m)

    for callback <- [:query, :ensure_started, :stop] do
      assert {:ok, %Dispatch.Observation{status: :absent}} =
               apply(WorkerHTTPAdapter, callback, [WorkerData.request()])
    end

    [{request, headers, _} | _] = WorkerTLSFixture.info(fixture).requests
    assert request["command"] == "stop"
    assert headers =~ "authorization: Bearer " <> config.token
    assert String.starts_with?(headers, "POST /internal/mixer-build-worker/v1 HTTP/1.1")
    clean(fixture, owner)
  end

  test "hostname rejection occurs before sending authorization", %{material: m} do
    {fixture, owner, _} =
      start(m, :normal, fn c -> put_in(c.endpoint.host, "wrong.fixture.invalid") end)

    assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
    assert WorkerTLSFixture.info(fixture).requests == []
    clean(fixture, owner)
  end

  test "untrusted CA rejection occurs before sending authorization", %{material: m, unrelated: u} do
    {fixture, owner, _} = start(m, :normal, fn c -> %{c | ca_roots: [u.ca]} end)
    assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
    assert WorkerTLSFixture.info(fixture).requests == []
    clean(fixture, owner)
  end

  test "response extra byte or pipelined response fails after complete declared body", %{
    material: m
  } do
    for extra <- ["x", "HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\nx"] do
      {fixture, owner, _} = start(m, {:raw, fn _, raw -> raw <> extra end})
      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      clean(fixture, owner)
      stop_owner(owner)
      GenServer.stop(fixture)
    end
  end

  test "all pre-Mint header and framing rejections close owned resources", %{material: m} do
    changes = [
      fn raw -> String.replace(raw, "HTTP/1.1 200 OK", "HTTP/1.1 302 Found") end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\ncontent-type: application/json"
        )
      end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\nTransfer-Encoding: chunked"
        )
      end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\nTrailer: x"
        )
      end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\nContent-Encoding: gzip"
        )
      end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\nX-Large: " <> String.duplicate("x", 2048)
        )
      end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\n" <> Enum.map_join(1..32, "\r\n", &"X-#{&1}: x")
        )
      end,
      fn raw -> String.replace(raw, "Content-Length: ", "Content-Length: 0") end,
      fn raw -> String.replace(raw, ~r/Content-Length: [0-9]+/, "Content-Length: 32769") end,
      fn raw ->
        String.replace(
          raw,
          "Content-Type: application/json",
          "Content-Type: application/json\r\n bad-fold: value"
        )
      end,
      fn raw -> "HTTP/1.1 100 Continue\r\n\r\n" <> raw end,
      fn raw -> String.replace(raw, "\r\n", "\n") end
    ]

    for change <- changes do
      {fixture, owner, _} = start(m, {:raw, fn _, raw -> change.(raw) end})
      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      clean(fixture, owner)
      stop_owner(owner)
      GenServer.stop(fixture)
    end
  end

  test "nonce mismatch and nested duplicate result cannot return observation", %{material: m} do
    for change <- [
          fn r -> Map.put(r, "request_id", String.duplicate("0", 32)) end,
          fn r -> put_in(r, ["guard", "epoch"], "1") end
        ] do
      {fixture, owner, _} =
        start(m, {:raw, fn request, _ -> WorkerTLSFixture.response(change.(request)) end})

      assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
      clean(fixture, owner)
      stop_owner(owner)
      GenServer.stop(fixture)
    end
  end

  @tag timeout: 10_000
  test "complete response without peer EOF consumes same deadline and fails", %{material: m} do
    {fixture, owner, _} = start(m, :no_eof)
    before = System.monotonic_time(:millisecond)
    assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
    elapsed = System.monotonic_time(:millisecond) - before
    assert elapsed >= 4_900 and elapsed < 5_750
    clean(fixture, owner)
  end

  test "caller death after authenticated request closes socket and retires permit", %{material: m} do
    {fixture, owner, _} = start(m, {:notify, self()})
    caller = spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_request, _}, 2_000
    Process.exit(caller, :kill)
    clean(fixture, owner)
  end

  test "transport owner death cancels independently monitored flights", %{material: m} do
    {fixture, owner, _} = start(m, {:notify, self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_request, _}, 2_000
    flights = Map.keys(:sys.get_state(owner).flights)
    Process.unlink(owner)
    Process.exit(owner, :kill)
    assert {:error, :uncertain} = Task.await(caller)
    eventually(fn -> Enum.all?(flights, &(not Process.alive?(&1))) end)
    eventually(fn -> MapSet.size(WorkerTLSFixture.info(fixture).active) == 0 end)
  end

  test "sixteen concurrent operations reject seventeenth without a socket", %{material: m} do
    {fixture, owner, _} = start(m, {:notify, self()})
    callers = for _ <- 1..16, do: spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    for _ <- 1..16, do: assert_receive({:worker_fixture_request, _}, 2_000)
    assert WorkerTLSFixture.info(fixture).accepted == 16
    before = System.monotonic_time(:millisecond)
    assert {:error, :unavailable} = WorkerHTTPAdapter.query(WorkerData.request())
    assert System.monotonic_time(:millisecond) - before < 100
    assert WorkerTLSFixture.info(fixture).accepted == 16
    Enum.each(callers, &Process.exit(&1, :kill))
    clean(fixture, owner)
  end

  test "segmented final body byte waits for byte and genuine EOF before Mint done", %{material: m} do
    {fixture, owner, _} = start(m, {:last_byte, self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_final_byte, handler}, 2_000
    ref = caller.ref
    refute_receive {^ref, _}, 50
    send(handler, :release_final_byte)
    assert {:ok, %Dispatch.Observation{status: :absent}} = Task.await(caller)
    clean(fixture, owner)
  end

  test "one-byte body still waits for actual peer EOF before rejecting invalid JSON", %{
    material: m
  } do
    {fixture, owner, _} = start(m, {:one_byte, self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_one_byte, handler}, 2_000
    ref = caller.ref
    refute_receive {^ref, _}, 50
    send(handler, :release_eof)
    assert {:error, :uncertain} = Task.await(caller)
    clean(fixture, owner)
  end

  test "caller death during TLS handshake retires registered raw socket and SSL process", %{
    material: m
  } do
    {fixture, owner, _} = start(m, {:handshake_barrier, self()})
    caller = spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_handshake, handler}, 2_000
    [flight] = Map.keys(:sys.get_state(owner).flights)
    tracked = :sys.get_state(flight)
    assert is_port(tracked.raw)
    Process.exit(caller, :kill)
    eventually(fn -> not Process.alive?(flight) end)
    assert Port.info(tracked.raw) == nil
    if is_pid(tracked.connection), do: refute(Process.alive?(tracked.connection))
    send(handler, :release_handshake)
    clean(fixture, owner)
    assert WorkerTLSFixture.info(fixture).requests == []
  end

  @tag timeout: 10_000
  test "TLS handshake stall uses total deadline and never sends credentials", %{material: m} do
    {fixture, owner, _} = start(m, {:handshake_barrier, self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_handshake, handler}, 2_000
    [flight] = Map.keys(:sys.get_state(owner).flights)
    tracked = :sys.get_state(flight)
    before = System.monotonic_time(:millisecond)
    assert {:error, :uncertain} = Task.await(caller, 5_750)
    assert System.monotonic_time(:millisecond) - before < 5_750
    assert Port.info(tracked.raw) == nil
    send(handler, :release_handshake)
    clean(fixture, owner)
    assert WorkerTLSFixture.info(fixture).requests == []
  end

  test "unexpected watchdog death quarantines admission until entire role disposal", %{
    material: m
  } do
    {fixture, owner, _} = start(m, {:notify, self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_request, _}, 2_000
    [flight] = Map.keys(:sys.get_state(owner).flights)
    tracked = :sys.get_state(flight)
    guard = Process.whereis(WorkerTransport.RoleGuard)

    try do
      Process.exit(flight, :kill)
      assert {:error, :uncertain} = Task.await(caller)
      eventually(fn -> :sys.get_state(guard).quarantined end)
      assert {:error, :unavailable} = WorkerHTTPAdapter.query(WorkerData.request())
      eventually(fn -> Port.info(tracked.raw) == nil and not Process.alive?(tracked.worker) end)

      if is_pid(tracked.connection),
        do: eventually(fn -> not Process.alive?(tracked.connection) end)

      GenServer.stop(owner)
      assert Process.alive?(guard)

      assert {:error, :unavailable} =
               WorkerTransport.start_fixture(
                 WorkerData.config(m.ca),
                 {127, 0, 0, 1},
                 WorkerTLSFixture.info(fixture).port
               )
    after
      # Test-only whole owned role disposal, after observing all owned handles.
      Process.exit(guard, :kill)
      if Process.alive?(tracked.worker), do: Process.exit(tracked.worker, :kill)
      if tracked.raw, do: :gen_tcp.close(tracked.raw)
    end
  end

  test "malformed result and configuration are not deliberately exposed to library sinks", %{
    material: m
  } do
    sentinel = "SYNTHETIC_PRIVATE_RESPONSE_SENTINEL"

    {fixture, owner, config} =
      start(
        m,
        {:raw,
         fn _, _ ->
           "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: #{byte_size(sentinel)}\r\nConnection: close\r\n\r\n" <>
             sentinel
         end}
      )

    logs =
      ExUnit.CaptureLog.capture_log(fn ->
        assert {:error, :uncertain} = WorkerHTTPAdapter.query(WorkerData.request())
        clean(fixture, owner)
      end)

    refute logs =~ sentinel
    refute logs =~ config.token
    refute inspect(:sys.get_state(owner)) =~ config.token
  end
end
