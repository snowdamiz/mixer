defmodule WorkerV2MalformedMarkerTest do
  use WorkerV2Case, async: false

  test "an existing marker equal to an absence sentinel still denies startup", %{material: m} do
    fixture = fixture(m)
    :persistent_term.put({WorkerTransport, :ownership_v2}, :absent)
    deny_replacement(m, fixture)
    assert marker() == {:present, :absent}
    assert WorkerTLSFixture.info(fixture).accepted == 0
  end
end
