ExUnit.start()

for {app, expected} <- [plug: ~c"1.20.3", bandit: ~c"1.13.1", thousand_island: ~c"1.6.0"] do
  Application.load(app)
  actual = Application.spec(app, :vsn)
  IO.puts("loaded #{app} #{actual}")
  if actual != expected, do: raise("unexpected loaded dependency version")
end

defmodule MixerRawContractProbe.Adapter do
  def read_req_body({result, recipient}, opts) do
    send(recipient, {:forwarded_opts, opts})
    result
  end
end

defmodule MixerRawContractProbeTest do
  use ExUnit.Case, async: false

  test "Plug preserves repeated signature values and exact value bytes" do
    conn = %Plug.Conn{req_headers: [{"stripe-signature", " t=1,v1=A "}, {"x", "x"}, {"stripe-signature", "t=2,v1=B"}]}
    assert Plug.Conn.get_req_header(conn, "stripe-signature") == [" t=1,v1=A ", "t=2,v1=B"]
  end

  test "Plug forwards options and does not enforce a returned byte ceiling" do
    conn = %Plug.Conn{adapter: {MixerRawContractProbe.Adapter, {{:ok, "oversized", :updated}, self()}}}
    assert {:ok, "oversized", updated} = Plug.Conn.read_body(conn, length: 1, read_length: 1, read_timeout: 1)
    assert updated.adapter == {MixerRawContractProbe.Adapter, :updated}
    assert_received {:forwarded_opts, [length: 1, read_length: 1, read_timeout: 1]}
  end

  test "Plug more return retains exact binary and new adapter state" do
    bytes = <<0, 255, 10, 13>>
    conn = %Plug.Conn{adapter: {MixerRawContractProbe.Adapter, {{:more, bytes, :next}, self()}}}
    assert {:more, ^bytes, %{adapter: {MixerRawContractProbe.Adapter, :next}}} = Plug.Conn.read_body(conn)
  end

  test "Plug error supplies no new connection" do
    conn = %Plug.Conn{adapter: {MixerRawContractProbe.Adapter, {{:error, :closed}, self()}}}
    assert Plug.Conn.read_body(conn) == {:error, :closed}
  end

  test "Bandit rejects identical duplicate Content-Length occurrences" do
    assert {:error, _} = Bandit.Headers.get_content_length([{"content-length", "3"}, {"content-length", "3"}])
  end

  test "Bandit accepts identical values in one Content-Length comma list" do
    assert Bandit.Headers.get_content_length([{"content-length", "3, 3"}]) == {:ok, 3}
    assert {:error, _} = Bandit.Headers.get_content_length([{"content-length", "3, 4"}])
  end

  test "Bandit does not permit Task to replace stream owner" do
    assert_raise RuntimeError, "Adapter functions must be called by stream owner", fn ->
      Bandit.Adapter.read_req_body(%Bandit.Adapter{owner_pid: nil}, [])
    end
  end

  test "pinned HTTP1 buffered identity body threads adapter transport" do
    socket = %Bandit.HTTP1.Socket{read_state: :headers_read, unread_content_length: 3, buffer: "abc"}
    assert {:more, first, next} = Bandit.HTTPTransport.read_data(socket, length: 2, read_length: 2, read_timeout: 1)
    assert IO.iodata_to_binary(first) == "ab"
    assert {:ok, last, %{read_state: :read}} = Bandit.HTTPTransport.read_data(next, length: 2, read_length: 2, read_timeout: 1)
    assert IO.iodata_to_binary(last) == "c"
  end

  test "pinned buffered chunked read can need one extra EOF read at exact length" do
    socket = %Bandit.HTTP1.Socket{read_state: :headers_read, body_encoding: "chunked", buffer: "3\r\nabc\r\n0\r\n\r\n"}
    assert {:more, first, next} = Bandit.HTTPTransport.read_data(socket, length: 3, read_length: 3, read_timeout: 1)
    assert IO.iodata_to_binary(first) == "abc"
    assert {:ok, "", %{read_state: :read}} = Bandit.HTTPTransport.read_data(next, length: 1, read_length: 1, read_timeout: 1)
  end
end
