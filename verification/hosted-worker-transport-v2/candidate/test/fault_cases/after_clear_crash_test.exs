defmodule WorkerV2AfterClearCrashTest do
  use WorkerV2Case, async: false

  test "guard death after proven marker clear permits replacement only after old resources retired",
       %{material: m} do
    fixture = fixture(m, {:notify, self()})
    {:ok, owner} = start(m, fixture, %{after_marker_clear: self()})
    caller = spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request()
    {flight, old} = flight(owner)
    Process.exit(caller, :kill)
    eventually(fn -> not alive?(flight) and retired?(old) end)
    clean(fixture, owner)
    GenServer.stop(owner)
    assert_receive {:worker_v2_checkpoint, :after_marker_clear, guard, _, _}, 2_000
    assert marker() == :missing
    assert retired?(old)
    Process.exit(guard, :kill)
    eventually(fn -> not alive?(guard) end)
    {:ok, replacement} = start(m, fixture)
    callers = for _ <- 1..16, do: spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    for _ <- 1..16, do: request()
    info = WorkerTLSFixture.info(fixture)
    assert info.accepted == 17 and MapSet.size(info.active) == 16
    assert retired?(old)
    Enum.each(callers, &Process.exit(&1, :kill))
    stop_clean(fixture, replacement)
    assert marker() == :missing
  end
end
