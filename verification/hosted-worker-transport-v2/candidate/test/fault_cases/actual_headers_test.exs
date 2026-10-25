defmodule WorkerV2ActualHeadersTest do
  use WorkerV2Case, async: false

  test "actual TLS bytes have exactly the selected eight headers and bounded body for every command",
       %{material: m} do
    fixture = fixture(m)
    {:ok, owner} = start(m, fixture)
    config = WorkerData.config(m.ca)

    rows =
      for command <- [:query, :ensure_started, :stop] do
        assert {:ok, %Dispatch.Observation{status: :absent}} =
                 apply(WorkerHTTPAdapter, command, [WorkerData.request()])

        [wire | _] = WorkerTLSFixture.info(fixture).wire_requests
        [head, body] = String.split(wire, "\r\n\r\n", parts: 2)
        [line | fields] = String.split(head, "\r\n")
        assert line == "POST /internal/mixer-build-worker/v1 HTTP/1.1"

        pairs =
          Enum.map(fields, fn field ->
            [key, value] = String.split(field, ": ", parts: 2)
            {key, value}
          end)

        expected = [
          {"host", config.endpoint.host},
          {"content-type", "application/json"},
          {"accept", "application/json"},
          {"accept-encoding", "identity"},
          {"connection", "close"},
          {"authorization", "Bearer " <> config.token},
          {"content-length", Integer.to_string(byte_size(body))},
          {"user-agent", "mixer-worker/1"}
        ]

        assert pairs === expected

        assert length(pairs) == 8 and
                 length(Enum.uniq(Enum.map(pairs, fn {k, _} -> String.downcase(k) end))) == 8

        expected_head =
          line <>
            "\r\n" <>
            Enum.map_join(expected, "", fn {k, v} -> k <> ": " <> v <> "\r\n" end) <> "\r\n"

        assert wire === expected_head <> body
        assert byte_size(expected_head) <= 8_192
        assert byte_size(body) <= 16_384
        value = Jason.decode!(body)
        assert value["command"] == Atom.to_string(command)
        assert body === Jason.encode!(value)
        refute body =~ config.token
        assert value["source"] == nil

        path =
          Path.join([__DIR__, "..", "..", "..", "actual-request-#{command}.http"])
          |> Path.expand()

        File.write!(path, wire)

        %{
          command: command,
          headers: length(pairs),
          header_bytes: byte_size(expected_head),
          body_bytes: byte_size(body),
          user_agent: "mixer-worker/1",
          nonce: value["request_id"],
          exact_bytes_equal: true
        }
      end

    assert length(Enum.uniq(Enum.map(rows, & &1.nonce))) == 3

    note("actual-eight-header-observations", %{
      scope: "actual-client-to-synthetic-TLS-peer-bytes",
      commands: rows
    })

    stop_clean(fixture, owner)
  end
end
