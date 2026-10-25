defmodule MixerHosted.Builds.WorkerBaselineWatchdogTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Dispatch, WorkerHTTPAdapter, WorkerTransport}
  alias MixerHosted.Test.{WorkerData, WorkerTLSFixture}

  setup_all do
    material = WorkerTLSFixture.material()
    unrelated = WorkerTLSFixture.material()
    assert material.key_dir_removed and unrelated.key_dir_removed
    {:ok, material: material, unrelated: unrelated}
  end

  setup do
    on_exit(fn -> if pid = Process.whereis(WorkerTransport), do: GenServer.stop(pid) end)
    :ok
  end

  defp start(m, mode \\ :normal, change \\ &Function.identity/1) do
    eventually(fn -> Process.whereis(WorkerTransport.RoleGuard) == nil end)
    {:ok, fixture} = WorkerTLSFixture.start_link({m, mode})
    c = change.(WorkerData.config(m.ca))

    {:ok, owner} =
      WorkerTransport.start_fixture(c, {127, 0, 0, 1}, WorkerTLSFixture.info(fixture).port)

    Process.unlink(owner)
    {fixture, owner, c}
  end

  defp eventually(fun, attempts \\ 200)

  defp eventually(fun, attempts) when attempts > 0 do
    if fun.(),
      do: :ok,
      else:
        (
          Process.sleep(10)
          eventually(fun, attempts - 1)
        )
  end

  defp eventually(_, 0), do: flunk("owned resource did not retire")

  defp clean(fixture, owner) do
    eventually(fn -> map_size(:sys.get_state(owner).flights) == 0 end)
    eventually(fn -> map_size(:sys.get_state(WorkerTransport.RoleGuard).flights) == 0 end)
    eventually(fn -> MapSet.size(WorkerTLSFixture.info(fixture).active) == 0 end)
    info = WorkerTLSFixture.info(fixture)
    assert info.accepted == info.closed
  end

  defp stop_owner(owner) do
    GenServer.stop(owner)
    eventually(fn -> Process.whereis(WorkerTransport.RoleGuard) == nil end)
  end

  test "unexpected watchdog death quarantines admission until entire role disposal", %{
    material: m
  } do
    {fixture, owner, _} = start(m, {:notify, self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_request, _}, 2_000
    [flight] = Map.keys(:sys.get_state(owner).flights)
    tracked = :sys.get_state(flight)
    guard = Process.whereis(WorkerTransport.RoleGuard)

    try do
      Process.exit(flight, :kill)
      assert {:error, :uncertain} = Task.await(caller)
      eventually(fn -> :sys.get_state(guard).quarantined end)
      assert {:error, :unavailable} = WorkerHTTPAdapter.query(WorkerData.request())
      eventually(fn -> Port.info(tracked.raw) == nil and not Process.alive?(tracked.worker) end)

      if is_pid(tracked.connection),
        do: eventually(fn -> not Process.alive?(tracked.connection) end)

      GenServer.stop(owner)
      assert Process.alive?(guard)

      assert {:error, :unavailable} =
               WorkerTransport.start_fixture(
                 WorkerData.config(m.ca),
                 {127, 0, 0, 1},
                 WorkerTLSFixture.info(fixture).port
               )
    after
      # Test-only whole owned role disposal, after observing all owned handles.
      Process.exit(guard, :kill)
      if Process.alive?(tracked.worker), do: Process.exit(tracked.worker, :kill)
      if tracked.raw, do: :gen_tcp.close(tracked.raw)
    end
  end
end
