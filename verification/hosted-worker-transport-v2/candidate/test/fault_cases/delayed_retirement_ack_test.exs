defmodule WorkerV2DelayedRetirementAckTest do
  use WorkerV2Case, async: false
  @tag timeout: 10_000
  test "cleanup acknowledgment after the absolute deadline cannot return a valid observation", %{
    material: m
  } do
    fixture = fixture(m, {:last_byte, self()})
    {:ok, owner} = start(m, fixture, %{before_retirement_ack: self()})
    caller = Task.async(fn -> WorkerHTTPAdapter.query(WorkerData.request()) end)
    assert_receive {:worker_fixture_final_byte, handler}, 2_000
    {flight, old} = flight(owner)
    deadline = old.deadline
    Process.sleep(max(0, deadline - System.monotonic_time(:millisecond) - 450))
    send(handler, :release_final_byte)
    assert_receive {:worker_v2_checkpoint, :before_retirement_ack, guard, _, ref}, 1_000
    assert retired?(old)
    before_ack = System.monotonic_time(:millisecond)
    assert before_ack < deadline
    Process.sleep(max(0, deadline - System.monotonic_time(:millisecond) + 50))
    send(guard, {:worker_v2_release, ref})
    result = Task.await(caller, 1_000)
    completed = System.monotonic_time(:millisecond)

    note("delayed-retirement-ack", %{
      acknowledgment_started_before_deadline: before_ack < deadline,
      acknowledgment_released_after_deadline: completed >= deadline,
      completed_after_deadline_ms: completed - deadline,
      observed_result: inspect(result),
      resources_retired_before_acknowledgment: retired?(old)
    })

    assert result == {:error, :uncertain}
    eventually(fn -> not alive?(flight) end)
    stop_clean(fixture, owner)
    assert marker() == :missing
  end
end
