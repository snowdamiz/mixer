defmodule IndependentAcknowledgedAbnormalDownTest do
 use WorkerV2Case, async: false
 test "cleanup attestation cannot authorize abnormal Flight DOWN", %{material: m} do
  fixture=fixture(m,{:last_byte,self()})
  {:ok,owner}=start(m,fixture,%{before_retirement_ack: self()})
  caller=Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
  assert_receive {:worker_fixture_final_byte,handler},2_000
  {flight,old}=flight(owner)
  send(handler,:release_final_byte)
  assert_receive {:worker_v2_checkpoint,:before_retirement_ack,guard,_,ref},2_000
  assert retired?(old)
  :erlang.suspend_process(flight)
  try do
   send(guard,{:worker_v2_release,ref})
   eventually(fn -> :sys.get_state(guard).flights[flight].retired end)
   Process.exit(flight,:kill)
  after
   resume(flight)
  end
  assert {:error,:uncertain}=Task.await(caller,2_000)
  eventually(fn -> :sys.get_state(guard).quarantined end)
  GenServer.stop(owner)
  assert match?({:present,_},marker())
  deny_replacement(m,fixture)
 end
end
