Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.InitialAdmitQueueTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.RuntimeOwner
  alias MixerHosted.Test.InitialAdmitQueueFixture, as: Queue

  @moduletag :initial_admit_queue
  @moduletag timeout: 30_000

  setup_all do
    Queue.prepare!()
  end

  setup c do
    Queue.observe_transactions!()
    Queue.start_components!(c)
  end

  test "real initial admission queues until a held connection is released within its original deadline", c do
    [first, second] = Queue.hold_all!(c.holders)
    starter = Queue.start_owner!(c.owner_supervisor, c.runtime)
    assert_receive {:owner_start_attempt, started}, 1_000
    queued = Queue.queued_owner!()
    owner = queued.owner
    assert queued.metrics.checkout_queue_length == 1
    refute Task.yield(starter, 0)
    Queue.release!(first)
    assert {{:ok, ^owner}, ^started, finished} = Task.await(starter, 5_000)
    assert finished - started < 5_000
    assert RuntimeOwner.status() == %{phase: :storage_ready, generation: 1}
    assert_receive {:store_transaction, ^owner, "begin"}, 1_000
    assert_receive {:store_transaction, ^owner, "commit"}, 1_000
    Queue.release!(second)
    Queue.authenticated_ordinary_boundary!(c)
    assert RuntimeOwner.status() == %{phase: :storage_ready, generation: 1}
  end

  test "initial admission held through the original deadline stays unavailable after release without retry", c do
    held = Queue.hold_all!(c.holders)
    starter = Queue.start_owner!(c.owner_supervisor, c.runtime)
    assert_receive {:owner_start_attempt, started}, 1_000
    queued = Queue.queued_owner!()
    owner = queued.owner
    assert queued.metrics.checkout_queue_length == 1

    # Queue observation occurs after init established its existing absolute deadline.
    # Keeping both checkouts past observation + 5s cannot release one before that deadline.
    hold_until = queued.observed_at + 5_001
    Process.sleep(max(0, hold_until - System.monotonic_time(:millisecond)))
    assert {{:ok, ^owner}, ^started, finished} = Task.await(starter, 2_000)
    assert finished - started < 6_000
    unavailable = RuntimeOwner.status()
    assert unavailable == %{phase: :unavailable, generation: 1}
    assert Process.whereis(RuntimeOwner) == owner
    Enum.each(held, &Queue.release!/1)
    assert Queue.pool_metrics().checkout_queue_length == 0
    assert RuntimeOwner.status() == unavailable
    response = Queue.request("GET", "/auth/session")
    assert response.status == 503
    assert Plug.Conn.get_resp_header(response, "set-cookie") == []
    refute_receive {:store_transaction, ^owner, _}, 250
    assert Process.whereis(RuntimeOwner) == owner
    assert RuntimeOwner.status() == unavailable
    assert Queue.pool_metrics().checkout_queue_length == 0
  end
end
