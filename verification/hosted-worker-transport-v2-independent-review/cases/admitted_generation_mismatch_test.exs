defmodule IndependentAdmittedGenerationMismatchTest do
 use WorkerV2Case, async: false
 test "the admitted Flight itself cannot retire with a different generation", %{material: m} do
  fixture=fixture(m,{:last_byte,self()})
  {:ok,owner}=start(m,fixture)
  caller=Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
  assert_receive {:worker_fixture_final_byte,handler},2_000
  {flight,old}=flight(owner)
  :sys.replace_state(flight,fn s -> %{s | generation: make_ref()} end)
  send(handler,:release_final_byte)
  assert {:error,:uncertain}=Task.await(caller,2_000)
  guard=Process.whereis(WorkerTransport.RoleGuard)
  eventually(fn -> not alive?(flight) and retired?(old) and :sys.get_state(guard).quarantined end)
  GenServer.stop(owner)
  deny_replacement(m,fixture)
  assert match?({:present,_},marker())
 end
end
