defmodule IndependentMalformedFalseTest do
 use WorkerV2Case, async: false
 test "stored malformed marker denies replacement without a reset", %{material: m} do
  fixture=fixture(m)
  marker_value=false
  :persistent_term.put({WorkerTransport,:ownership_v2},marker_value)
  for _ <- 1..24, do: assert({:error,:unavailable}==start(m,fixture))
  assert {:present,^marker_value}=marker()
  assert WorkerTLSFixture.info(fixture).accepted==0
 end
end
