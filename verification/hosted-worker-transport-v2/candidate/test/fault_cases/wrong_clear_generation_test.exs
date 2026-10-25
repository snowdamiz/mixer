defmodule WorkerV2WrongClearGenerationTest do
  use WorkerV2Case, async: false

  test "guard cannot clear a different generation marker during teardown", %{material: m} do
    fixture = fixture(m)
    {:ok, owner} = start(m, fixture, %{before_marker_clear: self()})
    assert {:ok, _} = WorkerHTTPAdapter.query(WorkerData.request())
    clean(fixture, owner)
    GenServer.stop(owner)
    assert_receive {:worker_v2_checkpoint, :before_marker_clear, guard, _, release}, 2_000
    {:present, old} = marker()
    replacement = %{old | generation: make_ref()}
    :persistent_term.put({WorkerTransport, :ownership_v2}, replacement)
    send(guard, {:worker_v2_release, release})
    eventually(fn -> :sys.get_state(guard).quarantined end)
    assert marker() === {:present, replacement}
    deny_replacement(m, fixture)
  end
end
