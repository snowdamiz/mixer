defmodule MixerHosted.Billing.WebhookTransportTest.ForbiddenAdapter do
  def get_http_protocol(_) do
    send(self(), :forbidden_adapter_read)
    raise "synthetic private adapter protocol"
  end

  def read_req_body(_, _) do
    send(self(), :forbidden_adapter_read)
    raise "synthetic private adapter body"
  end
end

defmodule MixerHosted.Billing.WebhookTransportTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Billing.WebhookTransport, as: Transport
  alias MixerHosted.Billing.WebhookTransport.Sinks

  defp report(overrides \\ %{}) do
    Map.merge(%{mixer_transport: 1, event: :webhook_transport, reason: :rejected, count: 1}, overrides)
  end

  test "safe counters reconstruct message and metadata without forwarding private fields" do
    original = %{
      level: :emergency,
      msg: {:report, report()},
      meta: %{body: "private body", signature: "private signature", pid: self(), file: "private path"},
      private: %{request: "private request"}
    }

    assert Sinks.filter(original, nil) == %{
             level: :notice,
             msg: {:report, %{event: :webhook_transport, reason: :rejected, count: 1}},
             meta: %{domain: [:mixer_private_transport]}
           }
  end

  test "raw messages and reports with additional private fields are dropped" do
    for message <- [
          {:string, "private request body"},
          {"private format ~p", ["private signature"]},
          {:report, %{body: "private body"}},
          {:report, Map.put(report(), :body, "private body")},
          {:report, Map.put(report(), :query, "private query")},
          {:report, Map.put(report(), :error, {RuntimeError, "private error"})},
          {:report, [mixer_transport: 1, event: :webhook_transport, reason: :rejected, count: 1]}
        ] do
      assert :stop == Sinks.filter(%{level: :error, msg: message, meta: %{body: "private"}}, nil)
    end
  end

  test "counters accept finite integer endpoints and reject unbounded or unknown schema" do
    for count <- [0, 2_147_483_647] do
      assert %{msg: {:report, %{count: ^count}}} =
               Sinks.filter(%{msg: {:report, report(%{count: count})}}, nil)
    end

    for changes <- [
          %{count: -1}, %{count: 2_147_483_648}, %{count: 1.0}, %{count: "1"},
          %{count: nil}, %{reason: "rejected"}, %{reason: :private_unknown},
          %{event: :request}, %{mixer_transport: 2}
        ] do
      assert :stop == Sinks.filter(%{msg: {:report, report(changes)}}, nil)
    end
  end

  test "filter does not invoke an arbitrary report callback" do
    callback = fn -> send(self(), :private_callback_invoked); "private body" end
    assert :stop == Sinks.filter(%{msg: {:report, callback}, meta: %{report_cb: callback}}, nil)
    refute_received :private_callback_invoked
  end

  test "ordinary application leaves private transport inactive" do
    assert Process.whereis(Transport.Owner) == nil
    assert Process.whereis(Transport.Sinks) == nil
    assert Process.whereis(Transport.Guards) == nil
  end

  test "absent role and permit fail before any request adapter call" do
    assert Process.whereis(Transport.Owner) == nil
    Process.delete({Transport, :permit})
    conn = %Plug.Conn{adapter: {__MODULE__.ForbiddenAdapter, %{body: "private body"}}}
    assert catch_exit(Transport.capture(conn)) == :private_transport_failure
    refute_received :forbidden_adapter_read
    assert Process.get({Transport, :permit}) == nil
  end

  test "forged process-local permit cannot authorize capture without the role" do
    assert Process.whereis(Transport.Owner) == nil
    Process.put({Transport, :permit}, {make_ref(), make_ref(), make_ref()})

    try do
      conn = %Plug.Conn{adapter: {__MODULE__.ForbiddenAdapter, %{body: "private body"}}}
      assert catch_exit(Transport.capture(conn)) == :private_transport_failure
      refute_received :forbidden_adapter_read
    after
      Process.delete({Transport, :permit})
    end
  end
end
