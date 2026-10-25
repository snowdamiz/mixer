defmodule WorkerV2ConcurrentStartTest do
  use WorkerV2Case, async: false

  test "concurrent startup admits exactly one generation and safe cleanup allows another", %{
    material: m
  } do
    fixture = fixture(m)

    for _round <- 1..2 do
      starters = for _ <- 1..24, do: starter(m, fixture, %{})

      results =
        for {pid, _} <- starters do
          receive do
            {:worker_v2_start_result, ^pid, result} -> result
          after
            2_000 -> flunk("startup did not settle")
          end
        end

      assert [{:ok, owner}] = Enum.filter(results, &match?({:ok, _}, &1))
      assert Enum.count(results, &(&1 == {:error, :unavailable})) == 23
      assert {:present, %{owner: ^owner, guard: guard}} = marker()
      assert guard == Process.whereis(WorkerTransport.RoleGuard)

      for {pid, ref} <- starters,
          do: assert_receive({:DOWN, ^ref, :process, ^pid, :normal}, 1_000)

      assert {:ok, _} = WorkerHTTPAdapter.query(WorkerData.request())
      stop_clean(fixture, owner)
    end
  end
end
