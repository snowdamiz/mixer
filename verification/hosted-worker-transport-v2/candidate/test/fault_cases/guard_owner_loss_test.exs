defmodule WorkerV2GuardOwnerLossTest do
  use WorkerV2Case, async: false

  test "guard and owner loss cannot reopen capacity over a suspended authenticated Flight", %{
    material: m
  } do
    fixture = fixture(m, {:notify, self()})
    {:ok, owner} = start(m, fixture)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request()
    {flight, old} = flight(owner)
    guard = Process.whereis(WorkerTransport.RoleGuard)
    original = marker()
    :erlang.suspend_process(flight)

    try do
      Process.exit(guard, :kill)
      eventually(fn -> not alive?(guard) end)
      Process.exit(owner, :kill)
      assert {:error, :uncertain} = Task.await(caller)
      eventually(fn -> not alive?(owner) end)
      assert alive?(old.worker) and alive?(old.connection) and Port.info(old.raw) != nil
      assert marker() === original
      for _ <- 1..16, do: deny_replacement(m, fixture)
      info = WorkerTLSFixture.info(fixture)
      assert info.accepted == 1 and length(info.requests) == 1 and MapSet.size(info.active) == 1

      note("guard-loss-repair", %{
        suspended_old_flight: true,
        old_worker_alive: alive?(old.worker),
        old_ssl_alive: alive?(old.connection),
        old_raw_open: Port.info(old.raw) != nil,
        attempted_replacements: 16,
        replacement_denied: true,
        actual_authenticated_requests: length(info.requests),
        active_tls_handlers: MapSet.size(info.active),
        marker_preserved: true
      })
    after
      resume(flight)
      send(flight, :deadline)
    end

    eventually(fn -> not alive?(flight) and retired?(old) end)
    eventually(fn -> MapSet.size(WorkerTLSFixture.info(fixture).active) == 0 end)
    assert marker() === original
    deny_replacement(m, fixture)
  end
end
