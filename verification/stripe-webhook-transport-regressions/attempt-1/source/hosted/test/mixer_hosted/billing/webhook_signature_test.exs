defmodule MixerWebhookSignatureTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Billing.WebhookSignature, as: Signature
  @secret "whsec_mixer_public_test_only_0001"
  @other "whsec_mixer_public_test_only_0002"
  @now 1_792_846_000
  @body ~s({"id":"evt_mixer_fixture","type":"test"})
  @invalid {:error, :invalid_signature}
  @unavailable {:error, :verification_unavailable}
  @vectors __DIR__
           |> Path.join("../../fixtures/billing/webhook-signature.json")
           |> File.read!()
           |> :json.decode()

  defp signature(body \\ @body, timestamp \\ @now, secret \\ @secret) do
    :crypto.mac(:hmac, :sha256, secret, [to_string(timestamp), ".", body])
    |> Base.encode16(case: :lower)
  end

  defp header(body \\ @body, timestamp \\ @now, secret \\ @secret),
    do: "t=#{timestamp},v1=#{signature(body, timestamp, secret)}"

  defp verify(body, headers, secrets \\ [@secret], now \\ @now),
    do: Signature.verify(body, headers, secrets, now)

  for vector <- @vectors do
    @vector vector
    test "independent Python vector: #{vector["name"]}" do
      vector = @vector

      body =
        if is_binary(vector["body_hex"]),
          do: Base.decode16!(vector["body_hex"], case: :lower),
          else: :binary.copy("x", vector["body_repeat_x"])

      assert Base.encode16(:crypto.hash(:sha256, body), case: :lower) == vector["body_sha256"]

      assert Signature.verify(
               body,
               ["t=#{vector["timestamp"]},v1=#{vector["signature"]}"],
               [Base.decode16!(vector["secret_hex"], case: :lower)],
               vector["timestamp"]
             ) == :ok
    end
  end

  test "every signed body byte is authenticated; normalized JSON is not equivalent" do
    original = header()

    for offset <- 0..(byte_size(@body) - 1) do
      <<before::binary-size(^offset), byte, after_bytes::binary>> = @body
      mutated = before <> <<Bitwise.bxor(byte, 1)>> <> after_bytes
      assert verify(mutated, [original]) == @invalid
    end

    for altered <- [@body <> "\n", " " <> @body, ~s({ "id":"evt_mixer_fixture","type":"test"})] do
      assert verify(altered, [original]) == @invalid
    end
  end

  test "timestamp mutation cannot reuse a signature; each signature byte matters" do
    signed = signature()
    assert verify(@body, ["t=#{@now + 1},v1=#{signed}"]) == @invalid

    for offset <- 0..63 do
      <<before::binary-size(^offset), byte, after_bytes::binary>> = signed
      replacement = if byte == ?a, do: ?b, else: ?a

      assert verify(@body, ["t=#{@now},v1=" <> before <> <<replacement>> <> after_bytes]) ==
               @invalid
    end
  end

  test "freshness includes both 300-second boundaries and rejects 301" do
    for delta <- [-300, 0, 300], do: assert(verify(@body, [header(@body, @now + delta)]) == :ok)
    for delta <- [-301, 301], do: assert(verify(@body, [header(@body, @now + delta)]) == @invalid)
  end

  test "fresh replay remains valid here and must be deduplicated by the future inbox" do
    assert verify(@body, [header()]) == :ok
    assert verify(@body, [header()]) == :ok
  end

  test "rotation and every signature position support either configured endpoint secret" do
    bogus = String.duplicate("0", 64)

    for key <- [@secret, @other], position <- 0..7 do
      signatures =
        List.replace_at(List.duplicate(bogus, 8), position, signature(@body, @now, key))

      headers = "t=#{@now}," <> Enum.map_join(signatures, ",", &("v1=" <> &1))
      assert verify(@body, [headers], [@secret, @other]) == :ok
      assert verify(@body, [headers], [@other, @secret]) == :ok
    end

    assert verify(@body, [header(@body, @now, @other)]) == @invalid
  end

  test "unknown schemes do not authenticate, and valid v1 ignores bounded extensions" do
    assert verify(@body, ["t=#{@now},v0=#{signature()}"]) == @invalid
    assert verify(@body, ["v0=opaque,v2=other," <> header() <> ",future=a=b"]) == :ok
    assert verify(@body, ["V1=#{signature()},t=#{@now}"]) == @invalid
    assert verify(@body, ["T=#{@now},v1=#{signature()}"]) == @invalid
  end

  test "signature hex case and field order are permitted, mixed ASCII boundary whitespace is stripped" do
    value = " \t \tv1=#{String.upcase(signature())}\t \t ,\t t=#{@now} \t "
    assert verify(@body, [value]) == :ok
  end

  test "timestamp is unique, required, canonical and in the supported range" do
    for stamp <- [
          "",
          "+#{@now}",
          "-1",
          "0#{@now}",
          "1.0",
          "1e9",
          " 1",
          "1 2",
          "253402300800",
          "9999999999999"
        ] do
      assert verify(@body, ["t=#{stamp},v1=#{signature()}"]) == @invalid
    end

    for value <- ["t=#{@now}," <> header(), header() <> ",t=#{@now + 1}", "v1=#{signature()}"] do
      assert verify(@body, [value]) == @invalid
    end
  end

  test "malformed recognized signature rejects the complete request despite a valid peer" do
    for value <- [
          "",
          "0",
          String.duplicate("0", 63),
          String.duplicate("0", 65),
          String.duplicate("g", 64),
          "#{signature()}=x"
        ] do
      assert verify(@body, [header() <> ",v1=#{value}"]) == @invalid
      assert verify(@body, ["v1=#{value}," <> header()]) == @invalid
    end
  end

  test "forbidden header bytes, empty fields and missing equals are rejected" do
    for byte <- Enum.to_list(0..8) ++ Enum.to_list(10..31) ++ Enum.to_list(127..255) do
      assert verify(@body, [header() <> ",future=" <> <<byte>>]) == @invalid
    end

    for value <- [
          header() <> ",",
          "," <> header(),
          header() <> ",,x=y",
          header() <> ", \t ",
          header() <> ",no_equals",
          header() <> ",=value",
          header() <> ",empty="
        ] do
      assert verify(@body, [value]) == @invalid
    end
  end

  test "exactly one bounded binary header occurrence is required" do
    for values <- [
          [],
          [header(), header()],
          header(),
          [nil],
          [123],
          [:signature],
          [[header()]],
          [header() | :improper],
          nil,
          %{}
        ] do
      assert verify(@body, values) == @invalid
    end

    prefix = header() <> ",extra="
    boundary = prefix <> String.duplicate("x", 4096 - byte_size(prefix))
    assert verify(@body, [boundary]) == :ok
    assert verify(@body, [boundary <> "x"]) == @invalid
    assert verify(@body, [""]) == @invalid
  end

  test "field and signature counts enforce exact finite boundaries" do
    boundary = header() <> String.duplicate(",x=y", 30)
    assert verify(@body, [boundary]) == :ok
    assert verify(@body, [boundary <> ",x=y"]) == @invalid
    eight = "t=#{@now}" <> String.duplicate(",v1=#{signature()}", 8)
    assert verify(@body, [eight]) == :ok
    assert verify(@body, [eight <> ",v1=#{signature()}"]) == @invalid
  end

  test "body bounds are byte based and reject improper input kinds" do
    for body <- ["", nil, [], [@body], 1, %{}, <<1::size(1)>>] do
      assert verify(body, [header()]) == @invalid
    end

    too_big = :binary.copy("x", 1_048_577)
    assert verify(too_big, [header(too_big)]) == @invalid
    assert verify("x", [header("x")]) == :ok
  end

  test "current caller configuration is mandatory, bounded and takes precedence over invalid input" do
    for secrets <- [
          [],
          [@secret, @secret],
          [@secret, @other, "third_secret_long"],
          @secret,
          [nil],
          [""],
          [String.duplicate("x", 15)],
          [String.duplicate("x", 257)],
          [@secret | :improper],
          nil
        ] do
      assert verify(@body, [header()], secrets) == @unavailable
      assert verify(nil, nil, secrets) == @unavailable
    end

    for size <- [16, 256] do
      secret = :binary.copy(<<0>>, size)
      assert verify(@body, [header(@body, @now, secret)], [secret]) == :ok
    end

    assert verify(@body, [header()], [@other]) == @invalid
    assert verify(@body, [header()], [@secret]) == :ok
  end

  test "trusted clock accepts only integral UTC seconds within the selected range" do
    for now <- [nil, -1, 253_402_300_800, @now * 1.0, "#{@now}", %{}] do
      assert verify(@body, [header()], [@secret], now) == @unavailable
    end
  end
end
