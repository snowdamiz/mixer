defmodule IndependentAfterClearNameWindowTest do
 use WorkerV2Case, async: false
 test "cleared marker with an old registered guard never overlaps two registered owners", %{material: m} do
  fixture=fixture(m)
  {:ok,owner}=start(m,fixture,%{after_marker_clear: self()})
  assert {:ok,_}=WorkerHTTPAdapter.query(WorkerData.request())
  clean(fixture,owner)
  GenServer.stop(owner)
  assert_receive {:worker_v2_checkpoint,:after_marker_clear,guard,_,ref},2_000
  assert marker()==:missing
  assert alive?(guard)
  for _ <- 1..24, do: assert({:error,:unavailable}==start(m,fixture))
  assert WorkerTLSFixture.info(fixture).accepted==1
  send(guard,{:worker_v2_release,ref})
  eventually(fn -> not alive?(guard) end)
  {:ok,replacement}=start(m,fixture)
  assert {:ok,_}=WorkerHTTPAdapter.query(WorkerData.request())
  stop_clean(fixture,replacement)
 end
end
