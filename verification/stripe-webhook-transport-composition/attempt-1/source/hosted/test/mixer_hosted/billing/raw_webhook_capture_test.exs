defmodule MixerHosted.Billing.RawWebhookCaptureTest.Adapter do
  def get_http_protocol(state), do: state.protocol

  def read_req_body(%{steps: [step | rest], index: index} = state, opts) do
    Process.put(:fake_calls, Process.get(:fake_calls, []) ++ [{index, opts}])
    next = %{state | steps: rest, index: index + 1}

    case step do
      {:raw, shape} ->
        shape

      {tag, bytes} when tag in [:ok, :more] ->
        {tag, bytes, next}

      {:error, reason} ->
        {:error, reason}

      {:raise, module} ->
        raise module, "synthetic transport exception"

      {:sleep, ms, tag, bytes} ->
        Process.sleep(ms)
        {tag, bytes, next}

      shape ->
        shape
    end
  end
end

defmodule MixerHosted.Billing.RawWebhookCaptureTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Billing.RawWebhookCapture, as: C
  @max 1_048_576
  setup do
    Process.delete(:capture_clock_sequence)
    Process.delete(:capture_clock_last)
    Process.put(:fake_calls, [])
    :ok
  end

  def conn(steps \\ [{:ok, "a"}], extra \\ []) do
    %Plug.Conn{
      method: "POST",
      request_path: "/api/v1/webhooks/stripe",
      query_string: "",
      req_headers:
        [{"content-type", "application/json"}, {"stripe-signature", "t=1,v1=literal"}] ++ extra,
      adapter:
        {MixerHosted.Billing.RawWebhookCaptureTest.Adapter,
         %{steps: steps, index: 0, protocol: :"HTTP/2"}}
    }
  end

  def rejected(conn, reason) do
    assert {:error, ^reason, latest} = C.capture(conn)
    assert latest.halted
    refute Map.has_key?(latest.private, :raw_webhook_capture)
    refute Map.has_key?(latest.assigns, :raw_webhook_capture)
    latest
  end

  test "exact bytes, original exposed singleton and newest connection survive" do
    bytes = <<0, 255, 13, 10, 195, 169, 92, 117, 48, 48, 54, 49>>
    c = conn([{:more, binary_part(bytes, 0, 4)}, {:ok, binary_part(bytes, 4, 8)}])

    c = %{
      c
      | req_headers: [{"content-type", "application/json"}, {"stripe-signature", " t=1,v1=A "}]
    }

    assert {:ok, %{raw_body: ^bytes, signature_header_values: [" t=1,v1=A "]}, result} =
             C.capture(c)

    assert elem(result.adapter, 1).index == 2
    assert Enum.map(Process.get(:fake_calls), &elem(&1, 0)) == [0, 1]
    assert result.assigns == %{} and result.private == %{}
  end

  test "reject fixed envelope variants before reads" do
    for c <- [
          %{conn() | method: "HEAD"},
          %{conn() | method: "GET"},
          %{conn() | request_path: "/api/v1/webhooks/stripe/"},
          %{conn() | request_path: "/api/v1/webhooks/%73tripe"},
          %{conn() | request_path: "/API/v1/webhooks/stripe"},
          %{conn() | query_string: "x=1"}
        ] do
      rejected(c, :envelope)
    end

    assert Process.get(:fake_calls) == []
  end

  test "metadata grammar permits only selected ASCII variants" do
    for ct <- ["application/json", " Application/JSON\t", "application/json ; CHARSET = utf-8\t"] do
      c = %{conn() | req_headers: [{"content-type", ct}, {"stripe-signature", "x"}]}
      assert {:ok, _, _} = C.capture(c)
    end

    for ct <- [
          "",
          "application/json,application/json",
          "application/json;charset=\"utf-8\"",
          "application/json;charset=utf-16",
          "application/json;x=y",
          "application/json;;",
          "application/json;charset=utf-8;charset=utf-8",
          "application/json\n",
          <<255>>,
          String.duplicate("a", 129)
        ] do
      rejected(
        %{conn() | req_headers: [{"content-type", ct}, {"stripe-signature", "x"}]},
        :envelope
      )
    end
  end

  test "duplicate missing oversized signatures and metadata reject without reading" do
    base = [{"content-type", "application/json"}]

    for sigs <- [
          [],
          [{"stripe-signature", ""}],
          [{"stripe-signature", String.duplicate("a", 4097)}],
          [{"stripe-signature", "a"}, {"stripe-signature", "b"}]
        ] do
      rejected(%{conn() | req_headers: base ++ sigs}, :envelope)
    end

    for extra <- [
          [{"content-type", "application/json"}],
          [{"content-encoding", "identity"}],
          [{"content-encoding", ""}]
        ] do
      rejected(conn([{:ok, "a"}], extra), :envelope)
    end

    for header <- ["trailer", "expect", "upgrade", "te"] do
      rejected(conn([{:ok, "a"}], [{header, ""}]), :unsupported_framing)
    end

    rejected(conn([{:ok, "a"}], [{"connection", "keep-alive, Upgrade"}]), :unsupported_framing)
    assert Process.get(:fake_calls) == []

    for sig <- ["a", "t=1,v1=x,garbage", String.duplicate("x", 4096)] do
      c = %{conn() | req_headers: base ++ [{"stripe-signature", sig}]}
      assert {:ok, %{signature_header_values: [^sig]}, _} = C.capture(c)
    end
  end

  test "framing is fixed across protocol versions" do
    for proto <- [:"HTTP/1.0", :"HTTP/3", :unknown] do
      {adapter, state} = conn().adapter
      rejected(%{conn() | adapter: {adapter, %{state | protocol: proto}}}, :unsupported_framing)
    end

    {adapter, state} = conn().adapter
    h1 = %{conn() | adapter: {adapter, %{state | protocol: :"HTTP/1.1"}}}
    rejected(h1, :unsupported_framing)

    assert {:ok, _, _} =
             C.capture(%{h1 | req_headers: h1.req_headers ++ [{"content-length", "1"}]})

    assert {:ok, _, _} =
             C.capture(%{h1 | req_headers: h1.req_headers ++ [{"transfer-encoding", "chunked"}]})

    rejected(conn([{:ok, "a"}], [{"transfer-encoding", "chunked"}]), :unsupported_framing)
  end

  test "canonical lengths have strict occurrence and byte grammar" do
    for length <- ["0", "01", "+1", "-1", " 1", "1 ", "1, 1", "99999999", "1x", ""] do
      rejected(conn([{:ok, "a"}], [{"content-length", length}]), :unsupported_framing)
    end

    rejected(conn([{:ok, "a"}], [{"content-length", "1048577"}]), :too_large)

    rejected(
      conn([{:ok, "a"}], [{"content-length", "1"}, {"content-length", "1"}]),
      :unsupported_framing
    )
  end

  test "actual returned byte count beats advisory target before retaining" do
    # 40KiB exceeds the 32KiB request but remains inside the aggregate cap.
    body = String.duplicate("a", 40_000)
    assert {:ok, %{raw_body: ^body}, _} = C.capture(conn([{:ok, body}]))
    assert [{0, opts}] = Process.get(:fake_calls)

    assert opts[:length] == 32_768 and opts[:read_length] == 32_768 and
             opts[:read_timeout] == 1_000

    rejected(conn([{:ok, String.duplicate("a", @max + 1)}]), :too_large)
    rejected(conn([{:ok, "ab"}], [{"content-length", "1"}]), :length_mismatch)
  end

  test "body min max more terminal and empty final boundaries" do
    rejected(conn([{:ok, ""}]), :empty)
    assert {:ok, _, _} = C.capture(conn([{:ok, String.duplicate("a", @max)}]))
    rejected(conn([{:more, String.duplicate("a", @max)}]), :too_large)
    rejected(conn([{:more, "a"}], [{"content-length", "1"}]), :length_mismatch)
    assert {:ok, %{raw_body: "a"}, _} = C.capture(conn([{:more, "a"}, {:ok, ""}]))
    rejected(conn([{:ok, "a"}], [{"content-length", "2"}]), :length_mismatch)
  end

  test "no progress and 64-call budget never drain a 65th read" do
    rejected(conn([{:more, ""}]), :no_progress)
    Process.put(:fake_calls, [])
    rejected(conn(List.duplicate({:more, "a"}, 64) ++ [{:ok, "a"}]), :read_limit)
    assert length(Process.get(:fake_calls)) == 64
    Process.put(:fake_calls, [])

    assert {:ok, %{raw_body: bytes}, _} =
             C.capture(conn(List.duplicate({:more, "a"}, 63) ++ [{:ok, "a"}]))

    assert byte_size(bytes) == 64 and length(Process.get(:fake_calls)) == 64
  end

  test "latest connection retained on opaque error without storing request reason" do
    c = conn([{:more, "a"}, {:error, {:synthetic, "BODY_SENTINEL"}}])
    latest = rejected(c, :transport_failure)
    assert elem(latest.adapter, 1).index == 1
    refute inspect(latest.assigns) =~ "BODY_SENTINEL"
  end

  test "documented nonbinary result fails closed, malformed Plug result raises" do
    rejected(conn([{:ok, ["not-binary"]}]), :unavailable_state)

    for shape <- [:wrong, {:ok, "a"}, {:ok, "a", :extra, :wrong}] do
      assert_raise CaseClauseError, fn -> C.capture(conn([{:raw, shape}])) end
    end

    assert_raise RuntimeError, "synthetic transport exception", fn ->
      C.capture(conn([{:raise, RuntimeError}]))
    end
  end

  test "production module excludes the test clock and ignores process clock spoofing" do
    {:ok, {_, [atoms: atoms]}} = :beam_lib.chunks(:code.which(C), [:atoms])

    refute Enum.any?(atoms, fn {_, atom} ->
             Atom.to_string(atom) == "Elixir.MixerRawCapture.TestClock"
           end)

    assert C.__info__(:functions) == [capture: 1]
    Process.put(:capture_clock_sequence, [0, 5000])
    assert {:ok, %{raw_body: "a"}, _} = C.capture(conn())
    assert Process.get(:capture_clock_sequence) == [0, 5000]
  end

  test "real late adapter result rejects without claiming hard cancellation" do
    started = System.monotonic_time(:millisecond)
    rejected(conn([{:sleep, 5_050, :ok, "a"}]), :read_deadline)
    assert System.monotonic_time(:millisecond) - started >= 5_050
    assert [{0, _}] = Process.get(:fake_calls)
  end

  test "captured unparsed bytes compose with the actual signature verifier" do
    body = <<0, 255, 13, 10, 123, 32, 125>>
    secret = "independent-test-secret"
    timestamp = 1_700_000_000
    mac = :crypto.mac(:hmac, :sha256, secret, Integer.to_string(timestamp) <> "." <> body)
    header = "t=#{timestamp},v1=#{Base.encode16(mac, case: :lower)}"
    original = conn([{:more, binary_part(body, 0, 2)}, {:ok, binary_part(body, 2, 5)}])

    original = %{
      original
      | req_headers: [{"content-type", "application/json"}, {"stripe-signature", header}]
    }

    assert {:ok, %{raw_body: captured, signature_header_values: headers}, _} = C.capture(original)
    assert captured == body and headers == [header]

    assert :ok =
             MixerHosted.Billing.WebhookSignature.verify(captured, headers, [secret], timestamp)

    assert {:error, :invalid_signature} =
             MixerHosted.Billing.WebhookSignature.verify(
               captured <> " ",
               headers,
               [secret],
               timestamp
             )
  end

  test "request and conn private fields cannot select clock and stale result cleared" do
    c = conn()

    c = %{
      c
      | private: %{clock: fn -> 0 end, raw_webhook_capture: "old"},
        assigns: %{raw_webhook_capture: "old"}
    }

    assert {:ok, _, latest} = C.capture(c)
    refute Map.has_key?(latest.private, :raw_webhook_capture)
    refute Map.has_key?(latest.assigns, :raw_webhook_capture)
  end
end
