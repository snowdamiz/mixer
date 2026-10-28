defmodule MixerHosted.Billing.RawWebhookCaptureHTTP2Test do
  use ExUnit.Case, async: false
  alias MixerHosted.HTTP2WireFixture, as: F
  @moduletag timeout: 26_000
  @cap 1_048_576

  setup_all do
    # One shared deadline covers all five methods/seven subcases, including teardown.
    %{http2_budget: F.budget()}
  end

  test "B1 actual HTTP/2 batching can return more than the requested 32 KiB", context do
    F.run(context.http2_budget, "B1-batching", :capture, fn ->
      body = body(40_001)
      prefix = for n <- 0..31, do: {binary_part(body, n, 1), false}

      tail = [
        {binary_part(body, 32, 16_384), false},
        {binary_part(body, 16_416, 16_384), false},
        {binary_part(body, 32_800, 7_201), true}
      ]

      F.send_data(prefix ++ tail)
      F.fence()
      F.release()
      result = F.result()
      assert_capture(result, body)
      oversized = Enum.any?(F.reads(), &(&1.bytes > 32_768))
      assert oversized, "the mandatory real over-target batching witness was not observed"
      assert_reads(32_768)
      assert F.bytes_sent() == 40_001
      F.fence()
    end)
  end

  test "B2 paced no-length HTTP/2 input admits exactly the application byte cap", context do
    F.run(context.http2_budget, "B2-exact-cap", :capture, fn ->
      body = body(@cap)
      F.release()
      paced(body, 32, true)
      result = F.result()
      assert_capture(result, body)
      assert F.bytes_sent() == @cap
      assert length(F.reads()) == 32
      assert Enum.all?(F.reads(), &(&1.bytes == 32_768))
      assert List.last(F.reads()).tag == :ok
      assert_reads(32_768)
      F.fence()
    end)
  end

  test "B3 a sent cap-plus-one input is refused and its halted stream is disposed", context do
    F.run(context.http2_budget, "B3-cap-plus-one", :capture, fn ->
      body = body(@cap + 1)
      F.release()
      paced(body, 31, false)
      offset = 31 * 32_768

      F.send_data([
        {binary_part(body, offset, 16_384), false},
        {binary_part(body, offset + 16_384, 16_384), false},
        {binary_part(body, @cap, 1), true}
      ])

      result = F.result()
      assert result.kind == :capture and result.tag == :error
      assert result.reason == :too_large and result.halted
      refute Map.has_key?(result, :body)
      assert F.bytes_sent() == @cap + 1
      assert_reads(32_768)
      # This can refuse at a nonterminal cap; it need not consume the final extra byte.
      F.fence()
    end)
  end

  test "D1 nonprogress controls preserve the package public read deadline", context do
    for profile <- [:settings, :window_update] do
      F.run(context.http2_budget, "D1-#{profile}", :package_read, fn ->
        result = F.nonprogress(profile)
        assert result.kind == :package_read and result.tag == :more
        assert result.bytes == 0
        refute result.halted
        assert [%{tag: :more, bytes: 0, length: 32_768, read_timeout: 1_000}] = F.reads()
      end)
    end
  end

  test "D2 Mixer refuses the timed public empty-more result as no_progress", context do
    for profile <- [:settings, :window_update] do
      F.run(context.http2_budget, "D2-#{profile}", :capture, fn ->
        result = F.nonprogress(profile)
        assert result.kind == :capture and result.tag == :error
        assert result.reason == :no_progress and result.halted
        refute Map.has_key?(result, :body)
        assert [%{tag: :more, bytes: 0, length: 32_768, read_timeout: 1_000}] = F.reads()
        # The one-second public read and Mixer's five-second admission deadline differ.
      end)
    end
  end

  defp paced(body, count, end_last) do
    for index <- 1..count do
      offset = (index - 1) * 32_768

      F.send_data([
        {binary_part(body, offset, 16_384), false},
        {binary_part(body, offset + 16_384, 16_384), end_last and index == count}
      ])

      read = F.wait_reads(index)
      assert read.bytes == 32_768
      assert read.tag == if(end_last and index == count, do: :ok, else: :more)
    end
  end

  defp assert_capture(result, expected) do
    assert result.kind == :capture and result.tag == :ok
    refute result.halted
    assert result.elapsed < 5_000
    # Bounded diagnostics: never let ExUnit pretty-print either large body.
    identical = result.body == expected
    assert identical, "captured body bytes differ"
    assert result.signatures == [F.signature()]
  end

  defp assert_reads(target) do
    reads = F.reads()
    assert length(reads) in 1..64

    assert Enum.all?(reads, fn read ->
             read.length == target and read.read_length == target and
               read.read_timeout in 1..1_000 and read.finished >= read.started
           end)
  end

  defp body(size) do
    seed = <<0, 255, 13, 10, 195, 169, 92, 34, 123, 125, 120, 121, 122, 49, 50, 51>>
    binary_part(:binary.copy(seed, div(size + 15, 16)), 0, size)
  end
end
