defmodule WorkerV2BeforeClearCrashTest do
  use WorkerV2Case, async: false

  test "guard death before marker clear never converts missing name to cleanup proof", %{
    material: m
  } do
    fixture = fixture(m)
    {:ok, owner} = start(m, fixture, %{before_marker_clear: self()})
    assert {:ok, _} = WorkerHTTPAdapter.query(WorkerData.request())
    clean(fixture, owner)
    original = marker()
    GenServer.stop(owner)
    assert_receive {:worker_v2_checkpoint, :before_marker_clear, guard, _, _}, 2_000
    assert marker() === original
    assert MapSet.size(WorkerTLSFixture.info(fixture).active) == 0
    Process.exit(guard, :kill)
    eventually(fn -> not alive?(guard) end)
    deny_replacement(m, fixture)
    assert marker() === original
    assert WorkerTLSFixture.info(fixture).accepted == 1
  end
end
