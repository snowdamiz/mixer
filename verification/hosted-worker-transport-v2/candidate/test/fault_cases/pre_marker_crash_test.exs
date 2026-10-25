defmodule WorkerV2PreMarkerCrashTest do
  use WorkerV2Case, async: false

  test "owner death before marker installation has no effect and allows reuse", %{material: m} do
    fixture = fixture(m)
    {starter, monitor} = starter(m, fixture, %{owner_registered: self()})
    assert_receive {:worker_v2_checkpoint, :owner_registered, owner, _, _}, 2_000
    assert marker() == :missing
    Process.exit(owner, :kill)
    assert_receive {:worker_v2_start_result, ^starter, {:error, :unavailable}}, 2_000
    assert_receive {:DOWN, ^monitor, :process, ^starter, :normal}, 1_000
    assert WorkerTLSFixture.info(fixture).accepted == 0
    {:ok, next} = start(m, fixture)
    stop_clean(fixture, next)
  end
end
