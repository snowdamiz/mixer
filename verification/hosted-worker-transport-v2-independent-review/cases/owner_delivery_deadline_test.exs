defmodule IndependentOwnerDeliveryDeadlineTest do
 use WorkerV2Case, async: false
 @tag timeout: 9_000
 test "owner cannot deliver an otherwise valid Flight result after its deadline", %{material: m} do
  fixture=fixture(m,{:last_byte,self()})
  {:ok,owner}=start(m,fixture)
  caller=Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
  assert_receive {:worker_fixture_final_byte,handler},2_000
  {flight,old}=flight(owner)
  :erlang.suspend_process(owner)
  try do
   send(handler,:release_final_byte)
   eventually(fn -> not alive?(flight) and retired?(old) end)
   queued=:erlang.process_info(owner,:messages)
   assert {:messages,messages}=queued
   assert Enum.any?(messages,&match?({:worker_transport_finished,^flight,{:ok,%Dispatch.Observation{status: :absent}}},&1))
   Process.sleep(max(0,old.deadline-System.monotonic_time(:millisecond)+80))
  after
   resume(owner)
  end
  result=Task.await(caller,1_000)
  completed=System.monotonic_time(:millisecond)
  File.write!(Path.join(__DIR__,"../owner-delivery-deadline-observation.json"),Jason.encode!(%{result: inspect(result),completed_after_deadline_ms: completed-old.deadline,resources_retired: retired?(old)},pretty: true))
  stop_clean(fixture,owner)
  assert result=={:error,:uncertain}
 end
end
