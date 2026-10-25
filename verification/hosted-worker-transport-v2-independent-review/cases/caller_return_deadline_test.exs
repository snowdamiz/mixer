defmodule IndependentCallerReturnDeadlineTest do
 use WorkerV2Case, async: false
 @tag timeout: 9_000
 test "a suspended caller cannot return an already queued success after the absolute deadline", %{material: m} do
  fixture=fixture(m,{:last_byte,self()})
  {:ok,owner}=start(m,fixture)
  recipient=self()
  {caller,monitor}=spawn_monitor(fn ->
   result=WorkerHTTPAdapter.query(WorkerData.request())
   send(recipient,{:independent_caller_result,self(),result,System.monotonic_time(:millisecond)})
  end)
  assert_receive {:worker_fixture_final_byte,handler},2_000
  {flight,old}=flight(owner)
  :erlang.suspend_process(caller)
  try do
   send(handler,:release_final_byte)
   eventually(fn -> not alive?(flight) and retired?(old) and map_size(:sys.get_state(owner).flights)==0 end)
   {:messages,messages}=:erlang.process_info(caller,:messages)
   assert Enum.any?(messages,fn
    {_tag,{:ok,%Dispatch.Observation{status: :absent}}} -> true
    _ -> false
   end)
   Process.sleep(max(0,old.deadline-System.monotonic_time(:millisecond)+80))
  after
   resume(caller)
  end
  assert_receive {:independent_caller_result,^caller,result,completed},1_000
  assert_receive {:DOWN,^monitor,:process,^caller,:normal},1_000
  File.write!(Path.join(__DIR__,"../caller-return-deadline-observation.json"),Jason.encode!(%{result: inspect(result),completed_after_deadline_ms: completed-old.deadline,resources_retired: retired?(old)},pretty: true))
  stop_clean(fixture,owner)
  assert result=={:error,:uncertain}
 end
end
