ExUnit.start(autorun: false)

defmodule CaptureReview.Adapter do
  def get_http_protocol(state), do: state.protocol
  def read_req_body(state, options) do
    Process.put(:review_reads, [{self(), options} | Process.get(:review_reads, [])])
    [step | rest] = state.steps
    latest = %{state | steps: rest, index: state.index + 1}
    case step do
      {tag, bytes} when tag in [:ok, :more] -> {tag, bytes, latest}
      {:error, reason} -> {:error, reason}
      {:raise, message} -> raise message
    end
  end
end

defmodule CaptureReview.IndependentTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Billing.RawWebhookCapture, as: Capture
  @cap 1_048_576
  setup do
    Process.put(:review_reads, [])
    Process.delete(:capture_clock_sequence)
    Process.delete(:capture_clock_last)
    :ok
  end
  def conn(steps, declared \\ nil) do
    headers = [{"content-type", "application/json"}, {"stripe-signature", " exact original "}]
    headers = if declared, do: headers ++ [{"content-length", Integer.to_string(declared)}], else: headers
    %Plug.Conn{method: "POST", request_path: "/api/v1/webhooks/stripe", query_string: "",
      req_headers: headers, adapter: {CaptureReview.Adapter, %{protocol: :"HTTP/2", steps: steps, index: 0}}}
  end
  def reads, do: Enum.reverse(Process.get(:review_reads))
  def reject(c, reason) do
    assert {:error, ^reason, latest} = Capture.capture(c)
    assert latest.halted
    refute Map.has_key?(latest.private, :raw_webhook_capture)
    refute Map.has_key?(latest.assigns, :raw_webhook_capture)
    latest
  end

  test "independent 64-part corpus preserves every byte and reads on the caller" do
    body = :binary.copy(:binary.list_to_bin(Enum.to_list(0..255)), 4)
    for parts <- 1..64, empty_terminal <- [false, true] do
      Process.put(:review_reads, [])
      size = div(byte_size(body), parts)
      chunks = for i <- 0..(parts - 1), do: binary_part(body, i * size, if(i == parts - 1, do: byte_size(body) - i * size, else: size))
      steps = Enum.map(chunks, &{:more, &1})
      steps = if empty_terminal, do: steps ++ [{:ok, ""}], else: List.replace_at(steps, -1, {:ok, List.last(chunks)})
      if length(steps) > 64 do
        reject(conn(steps), :read_limit)
      else
        assert {:ok, %{raw_body: ^body, signature_header_values: [" exact original "]}, latest} = Capture.capture(conn(steps))
        assert elem(latest.adapter, 1).index == length(steps)
      end
      assert length(reads()) == min(64, length(steps))
      assert Enum.all?(reads(), fn {owner, opts} -> owner == self() and opts[:read_length] == opts[:length] and opts[:length] in 1..32768 and opts[:read_timeout] in 1..1000 end)
    end
  end

  test "aggregate cap and declaration terminal states obey an independent boundary table" do
    for size <- [1, 2, 32767, 32768, 32769, @cap - 1, @cap, @cap + 1],
        terminal <- [:ok, :more], declared <- [nil, size, size + 1] do
      Process.put(:review_reads, [])
      body = :binary.copy("x", size)
      c = conn([{terminal, body}, {:ok, ""}], declared)
      expected = cond do
        declared != nil and declared > @cap -> :too_large
        size > @cap -> :too_large
        terminal == :more and size == @cap -> :too_large
        terminal == :more and size == declared -> :length_mismatch
        declared != nil and size != declared -> :length_mismatch
        true -> :ok
      end
      if expected == :ok do
        assert {:ok, %{raw_body: ^body}, _} = Capture.capture(c)
      else
        reject(c, expected)
      end
      if declared != nil and declared > @cap, do: assert(reads() == [])
    end
  end

  test "last returned connection is retained and no later read occurs after opaque failure" do
    for prefix <- [1, 2, 63] do
      Process.put(:review_reads, [])
      c = conn(List.duplicate({:more, <<0, 255>>}, prefix) ++ [{:error, {:arbitrary, "review synthetic raw sentinel"}}, {:ok, "never"}])
      latest = reject(c, :transport_failure)
      assert elem(latest.adapter, 1).index == prefix
      assert length(reads()) == prefix + 1
    end
  end

  test "unavailable state does not consume the original adapter" do
    for state <- [:set, :set_chunked, :set_file, :sent, :chunked, :file, :upgraded] do
      reject(%{conn([{:ok, "a"}]) | state: state}, :unavailable_state)
    end
    reject(%{conn([{:ok, "a"}]) | halted: true}, :unavailable_state)
    assert reads() == []
  end

  test "all disallowed ASCII controls and nonASCII media metadata fail before reading" do
    for byte <- Enum.to_list(0..8) ++ Enum.to_list(10..31) ++ Enum.to_list(127..255) do
      c = conn([{:ok, "a"}])
      headers = [{"content-type", "application/json" <> <<byte>>}, {"stripe-signature", "x"}]
      reject(%{c | req_headers: headers}, :envelope)
    end
    assert reads() == []
  end

  test "signature metadata bytes survive without trimming or grammar repair" do
    for bytes <- [<<0>>, <<255>>, " x ", :binary.copy(<<0, 255>>, 2048)] do
      c = conn([{:ok, "a"}])
      headers = [{"content-type", "application/json"}, {"stripe-signature", bytes}]
      assert {:ok, %{signature_header_values: [^bytes]}, _} = Capture.capture(%{c | req_headers: headers})
    end
  end

  test "deadline budgets shrink and late final empty chunk cannot admit a prefix" do
    Process.put(:capture_clock_sequence, [0, 0, 1, 4999, 4999, 4999])
    assert {:ok, %{raw_body: "a"}, _} = Capture.capture(conn([{:more, "a"}, {:ok, ""}]))
    assert Enum.map(reads(), fn {_, opts} -> opts[:read_timeout] end) == [1000, 1]
    Process.put(:review_reads, [])
    Process.put(:capture_clock_sequence, [0, 0, 1, 4999, 5000])
    reject(conn([{:more, "a"}, {:ok, ""}]), :read_deadline)
    assert length(reads()) == 2
  end

  test "all forbidden framing headers and upgrade token positions fail before reading" do
    for {name, value} <- [{"expect", ""}, {"trailer", ""}, {"upgrade", ""}, {"te", ""},
          {"connection", "Upgrade, keep-alive"}, {"connection", "keep-alive,\tUPGRADE\t"},
          {"connection", "x, upgrade, y"}] do
      c = conn([{:ok, "a"}])
      reject(%{c | req_headers: c.req_headers ++ [{name, value}]}, :unsupported_framing)
    end
    assert reads() == []
  end
end

summary = ExUnit.run()
File.write!(Path.join(System.fetch_env!("CAPTURE_RESULT_DIR"), "independent-summary.json"), Jason.encode!(summary, pretty: true))
if summary.failures != 0, do: System.halt(1)
