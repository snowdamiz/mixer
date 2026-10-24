defmodule CaptureReview.AdditionalWireTest do
  use ExUnit.Case, async: false
  import MixerRawCapture.WireHelpers
  def port, do: Application.fetch_env!(:mixer_raw_capture_candidate, :wire_port)

  test "independent H1 content length and chunk framing preserve delimiters as data" do
    body = <<0, 255, 13, 10>> <> "0\r\n\r\n2;anything\r\n" <> :binary.copy(<<195, 169>>, 501)
    MixerRawCapture.WireTest.accepted(tcp(port(), "review-h1-split", body,
      parts: [{0, binary_part(body, 0, 5)}, {10, binary_part(body, 5, byte_size(body) - 5)}]), body)
    first = binary_part(body, 0, 7)
    last = binary_part(body, 7, byte_size(body) - 7)
    wire = "7;review=one\r\n" <> first <> "\r\n" <> Integer.to_string(byte_size(last), 16) <> ";review=two\r\n" <> last <> "\r\n0\r\n\r\n"
    MixerRawCapture.WireTest.accepted(tcp(port(), "review-h1-chunk-delimiters", body,
      framing: [{"Transfer-Encoding", "chunked"}], parts: [{0, wire}]), body)
  end

  test "independent HTTP2 60001 byte explicit length split passes exact body to actual verifier" do
    body = :binary.copy(<<0, 255, 13, 10, 195, 169>>, 10000) <> <<0>>
    parts = for {offset, size} <- [{0, 16384}, {16384, 16384}, {32768, 16384}, {49152, 10849}], do: {0, binary_part(body, offset, size)}
    MixerRawCapture.WireTest.accepted(h2(port(), "review-h2-declared-split", body,
      framing: [{"content-length", "60001"}], parts: parts), body)
  end

  test "identical repeated signature occurrences still reject on both transports before reads" do
    sig = sign("a")
    headers = [{"content-type", "application/json"}, {"stripe-signature", sig}, {"stripe-signature", sig}]
    for {id, result} <- [{"review-h1-identical-sigs", tcp(port(), "review-h1-identical-sigs", "a", headers: headers)},
        {"review-h2-identical-sigs", h2(port(), "review-h2-identical-sigs", "a", headers: headers)}] do
      MixerRawCapture.WireTest.rejected(result, true)
      assert result.event.id == id
      assert result.event.exposedSignatureValues == [sig, sig]
    end
  end
end
