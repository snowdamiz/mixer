defmodule IndependentAckTimeoutTest do
 use WorkerV2Case, async: false
 @tag timeout: 5_000
 test "retirement acknowledgment timeout remains uncertain despite later valid acknowledgment", %{material: m} do
  fixture=fixture(m,{:last_byte,self()})
  {:ok,owner}=start(m,fixture,%{before_retirement_ack: self()})
  caller=Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
  assert_receive {:worker_fixture_final_byte,handler},2_000
  {flight,old}=flight(owner)
  send(handler,:release_final_byte)
  assert_receive {:worker_v2_checkpoint,:before_retirement_ack,guard,_,ref},2_000
  assert retired?(old)
  Process.sleep(1_100)
  assert {:error,:uncertain}=Task.await(caller,500)
  refute alive?(flight)
  assert match?({:present,_},marker())
  GenServer.stop(owner)
  assert {:error,:unavailable}=start(m,fixture)
  send(guard,{:worker_v2_release,ref})
  eventually(fn -> marker()==:missing and not alive?(guard) end)
  {:ok,replacement}=start(m,fixture)
  assert {:ok,_}=WorkerHTTPAdapter.query(WorkerData.request())
  stop_clean(fixture,replacement)
 end
end
