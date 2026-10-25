defmodule WorkerV2NormalReuseTest do
  use WorkerV2Case, async: false

  test "demonstrated normal cleanup clears exact generation and permits safe reuse", %{
    material: m
  } do
    fixture = fixture(m)
    {:ok, owner} = start(m, fixture)
    {:present, first} = marker()

    assert {:ok, %Dispatch.Observation{status: :absent}} =
             WorkerHTTPAdapter.query(WorkerData.request())

    stop_clean(fixture, owner)
    assert marker() == :missing
    {:ok, next} = start(m, fixture)
    {:present, second} = marker()
    refute first.generation === second.generation

    assert {:ok, %Dispatch.Observation{status: :absent}} =
             WorkerHTTPAdapter.query(WorkerData.request())

    stop_clean(fixture, next)
    assert WorkerTLSFixture.info(fixture).accepted == 2
  end
end
