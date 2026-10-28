defmodule MixerHosted.Identity.TLSFixtureLifecycleControlTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.TLSFixture

  defp summary(info) do
    %{
      accepted: info.accepted,
      closed: info.closed,
      socket_count: map_size(info.sockets),
      request_count: length(info.requests),
      terminal_results: Map.get(info, :terminal_results, :unavailable)
    }
  end

  defp eventually(fixture, predicate, remaining \\ 250) do
    info = TLSFixture.info(fixture)

    cond do
      predicate.(info) ->
        info

      remaining == 0 ->
        flunk("fixture lifecycle observation: #{inspect(summary(info))}")

      true ->
        Process.sleep(10)
        eventually(fixture, predicate, remaining - 1)
    end
  end

  defp connect(fixture) do
    authority = GenServer.call(fixture, :authority)

    assert {:ok, socket} =
             :ssl.connect(
               authority.ip,
               authority.port,
               [
                 :binary,
                 active: false,
                 verify: :verify_peer,
                 cacerts: [authority.ca],
                 server_name_indication: ~c"jwks.fixture.invalid",
                 customize_hostname_check: [
                   match_fun: :public_key.pkix_verify_hostname_match_fun(:https)
                 ]
               ],
               2_000
             )

    assert :ok =
             :ssl.send(socket, "GET /keys HTTP/1.1\r\nHost: jwks.fixture.invalid\r\n\r\n")

    eventually(fixture, &(length(&1.requests) == 1))
    socket
  end

  test "stalled response stays silent and reports client EOF within the unchanged startup wait" do
    fixture = start_supervised!(TLSFixture)
    TLSFixture.configure(fixture, :stall)
    socket = connect(fixture)

    try do
      assert {:error, :timeout} = :ssl.recv(socket, 0, 100)
      assert TLSFixture.info(fixture).closed == 0
      assert :ok = :ssl.close(socket)
      info = eventually(fixture, &(&1.closed == 1))
      assert info.accepted == 1
      assert info.sockets == %{}

      assert info.terminal_results == [
               %{stage: :peer_close, outcome: :peer_closed, unexpected_bytes: 0}
             ]
    after
      :ssl.close(socket)
    end
  end

  test "an accepted TCP client that aborts before handshake records exactly one peer EOF" do
    fixture = start_supervised!(TLSFixture)
    authority = GenServer.call(fixture, :authority)
    assert {:ok, socket} = :gen_tcp.connect(authority.ip, authority.port, [:binary, active: false])

    try do
      eventually(fixture, &(&1.accepted == 1))
      assert :ok = :gen_tcp.close(socket)
      info = eventually(fixture, &(&1.closed == 1))
      assert info.accepted == 1
      assert info.requests == []
      assert info.sockets == %{}

      assert info.terminal_results == [
               %{stage: :handshake, outcome: :peer_closed, unexpected_bytes: 0}
             ]
    after
      :gen_tcp.close(socket)
    end
  end

  test "local receive timeout cleans the handler without counting a peer EOF" do
    fixture = start_supervised!(TLSFixture)
    TLSFixture.configure(fixture, :stall)
    socket = connect(fixture)

    try do
      # This control waits for the fixture's existing 3-second timeout. It does
      # not change the startup method's 250 x 10ms closure assertion.
      info = eventually(fixture, &(length(&1.terminal_results) == 1), 400)
      assert info.accepted == 1
      assert info.closed == 0
      assert info.sockets == %{}

      assert info.terminal_results == [
               %{stage: :peer_close, outcome: :timeout, unexpected_bytes: 0}
             ]
    after
      :ssl.close(socket)
    end
  end

  test "unexpected client data does not count as peer EOF or enter diagnostics" do
    fixture = start_supervised!(TLSFixture)
    TLSFixture.configure(fixture, :stall)
    socket = connect(fixture)

    try do
      assert :ok = :ssl.send(socket, "private-synthetic-payload")
      info = eventually(fixture, &(length(&1.terminal_results) == 1))
      assert info.accepted == 1
      assert info.closed == 0
      assert info.sockets == %{}

      assert info.terminal_results == [
               %{stage: :peer_close, outcome: :unexpected_data, unexpected_bytes: 25}
             ]

      refute inspect(info.terminal_results) =~ "private-synthetic-payload"
    after
      :ssl.close(socket)
    end
  end
end
