defmodule WorkerV2GuardBindCrashTest do
  use WorkerV2Case, async: false

  test "guard death during startup after binding leaves exact marker quarantine", %{material: m} do
    fixture = fixture(m)
    {starter, monitor} = starter(m, fixture, %{guard_bound: self()})
    assert_receive {:worker_v2_checkpoint, :guard_bound, guard, generation, _}, 2_000
    assert {:present, %{guard: ^guard, generation: ^generation}} = marker()
    original = marker()
    Process.exit(guard, :kill)
    assert_receive {:worker_v2_start_result, ^starter, {:error, :unavailable}}, 2_000
    assert_receive {:DOWN, ^monitor, :process, ^starter, :normal}, 1_000
    deny_replacement(m, fixture)
    assert marker() === original
    assert WorkerTLSFixture.info(fixture).accepted == 0
  end
end
