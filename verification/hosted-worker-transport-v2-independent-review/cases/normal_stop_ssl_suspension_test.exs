defmodule IndependentNormalStopSSLSuspensionTest do
 use WorkerV2Case, async: false
 test "normal Flight stop cannot release its permit before the exact SSL handler retires", %{material: m} do
  fixture=fixture(m,{:notify,self()})
  {:ok,owner}=start(m,fixture)
  caller=Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
  request()
  {flight,old}=flight(owner)
  :erlang.suspend_process(old.connection)
  stopper=Task.async(fn -> GenServer.stop(flight,:normal,2_000) end)
  try do
   Process.sleep(80)
   assert Task.yield(stopper,0)==nil
   guard=Process.whereis(WorkerTransport.RoleGuard)
   assert Map.has_key?(:sys.get_state(guard).flights,flight)
  after
   resume(old.connection)
  end
  assert :ok=Task.await(stopper,2_000)
  assert {:error,:uncertain}=Task.await(caller,2_000)
  assert retired?(old)
  stop_clean(fixture,owner)
 end
end
