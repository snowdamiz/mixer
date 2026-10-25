defmodule WorkerV2WrongRetirementTest do
  use WorkerV2Case, async: false

  test "cleanup from an unadmitted caller cannot acknowledge another Flight", %{material: m} do
    fixture = fixture(m, {:notify, self()})
    {:ok, owner} = start(m, fixture)
    caller = spawn(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request()
    {flight, old} = flight(owner)
    guard = Process.whereis(WorkerTransport.RoleGuard)
    state = :sys.get_state(guard)
    entry = state.flights[flight]

    for {generation, token} <- [
          {state.generation, entry.token},
          {make_ref(), entry.token},
          {state.generation, make_ref()}
        ] do
      assert {:error, :unavailable} = GenServer.call(guard, {:retired, flight, generation, token})
      refute :sys.get_state(guard).flights[flight].retired
    end

    Process.exit(caller, :kill)
    eventually(fn -> not alive?(flight) and retired?(old) end)
    stop_clean(fixture, owner)
    assert marker() == :missing
  end
end
