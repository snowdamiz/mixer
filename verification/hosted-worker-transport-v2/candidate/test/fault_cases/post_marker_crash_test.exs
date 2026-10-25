defmodule WorkerV2PostMarkerCrashTest do
  use WorkerV2Case, async: false

  test "owner death after marker installation before guard leaves VM quarantine", %{material: m} do
    fixture = fixture(m)
    {starter, monitor} = starter(m, fixture, %{marker_installed: self()})
    assert_receive {:worker_v2_checkpoint, :marker_installed, owner, generation, _}, 2_000
    assert {:present, %{owner: ^owner, generation: ^generation, guard: nil}} = marker()
    original = marker()
    Process.exit(owner, :kill)
    assert_receive {:worker_v2_start_result, ^starter, {:error, :unavailable}}, 2_000
    assert_receive {:DOWN, ^monitor, :process, ^starter, :normal}, 1_000
    deny_replacement(m, fixture)
    assert marker() === original
    assert WorkerTLSFixture.info(fixture).accepted == 0
  end
end
