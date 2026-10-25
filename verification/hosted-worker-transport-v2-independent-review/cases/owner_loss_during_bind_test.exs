defmodule IndependentOwnerLossDuringBindTest do
 use WorkerV2Case, async: false
 test "owner loss during guard binding blocks startup until bound guard proves empty teardown", %{material: m} do
  fixture=fixture(m)
  {starter,_}=starter(m,fixture,%{guard_bound: self()})
  assert_receive {:worker_v2_checkpoint,:guard_bound,guard,generation,ref},2_000
  assert {:present,%{owner: owner,generation: ^generation,guard: ^guard}}=marker()
  Process.exit(owner,:kill)
  eventually(fn -> not alive?(owner) end)
  assert {:error,:unavailable}=start(m,fixture)
  assert WorkerTLSFixture.info(fixture).accepted==0
  send(guard,{:worker_v2_release,ref})
  assert_receive {:worker_v2_start_result,^starter,{:error,:unavailable}},2_000
  eventually(fn -> not alive?(guard) and marker()==:missing end)
  {:ok,replacement}=start(m,fixture)
  assert {:ok,_}=WorkerHTTPAdapter.query(WorkerData.request())
  stop_clean(fixture,replacement)
 end
end
