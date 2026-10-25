defmodule WorkerV2NormalDownWithoutAttestationTest do
  use WorkerV2Case, async: false

  test "normal DOWN alone without admitted cleanup attestation quarantines", %{material: m} do
    fixture = fixture(m, {:notify, self()})
    {:ok, owner} = start(m, fixture)
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    request()
    {flight, old} = flight(owner)
    # Internal fault injection suppresses the cleanup callback; not a product input.
    :sys.replace_state(flight, fn state -> %{state | cleanup_attested: true} end)
    assert :ok = GenServer.stop(flight, :normal)
    assert {:error, :uncertain} = Task.await(caller)
    eventually(fn -> :sys.get_state(WorkerTransport.RoleGuard).quarantined end)
    eventually(fn -> retired?(old) end)
    GenServer.stop(owner)
    assert match?({:present, _}, marker())
    deny_replacement(m, fixture)
  end
end
