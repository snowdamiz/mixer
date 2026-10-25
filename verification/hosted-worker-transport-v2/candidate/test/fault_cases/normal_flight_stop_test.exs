defmodule WorkerV2NormalFlightStopTest do
  use WorkerV2Case, async: false

  test "normal external Flight stop attests actual retirement before permit reuse", %{material: m} do
    fixture = fixture(m, {:notify, self()})
    {:ok, owner} = start(m, fixture)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request()
    {flight, old} = flight(owner)
    :erlang.suspend_process(old.connection)
    stopper = Task.async(fn -> GenServer.stop(flight, :normal) end)

    try do
      assert Task.yield(stopper, 25) == nil
    after
      resume(old.connection)
    end

    assert :ok = Task.await(stopper, 2_000)
    assert {:error, :uncertain} = Task.await(caller)
    assert retired?(old)
    clean(fixture, owner)
    refute :sys.get_state(WorkerTransport.RoleGuard).quarantined
    stop_clean(fixture, owner)
  end
end
