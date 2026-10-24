[source, mode] = System.argv()
Code.require_file(source)
secret = "review_synthetic_endpoint_key_01"
body = "synthetic late-fault review"
timestamp = 1_792_846_000
signature = :crypto.mac(:hmac, :sha256, secret, [Integer.to_string(timestamp), ".", body]) |> Base.encode16(case: :lower)
:ok = MixerHosted.Billing.WebhookSignature.verify(body, ["t=#{timestamp},v1=#{signature}"], [secret], timestamp)
true = mode in ["late_mac", "late_compare", "late_throw", "late_exit", "schedule"]
true = :code.unstick_mod(:crypto)
:code.purge(:crypto)
true = :code.delete(:crypto)
Process.put(:review_mode, mode)

Code.compile_string("""
defmodule :crypto do
  def mac(:hmac, :sha256, _key, _data) do
    count = Process.get(:review_macs, 0) + 1
    Process.put(:review_macs, count)
    if Process.get(:review_mode) == "late_mac" and count == 2 do
      raise "synthetic failure after earlier signature match"
    end
    <<0::256>>
  end
  def hash_equals(a, b) do
    count = Process.get(:review_compares, 0) + 1
    Process.put(:review_compares, count)
    case {Process.get(:review_mode), count} do
      {"late_compare", 16} -> raise "synthetic comparison failure after earlier match"
      {"late_throw", 2} -> throw(:synthetic_late_throw)
      {"late_exit", 2} -> exit(:synthetic_late_exit)
      _ -> a == b
    end
  end
end
""")

header = "t=#{timestamp}," <> Enum.map_join(1..8, ",", fn _ -> "v1=" <> String.duplicate("0", 64) end)
observed = MixerHosted.Billing.WebhookSignature.verify(body, [header], [secret, secret <> "2"], timestamp)
expected = if mode == "schedule", do: :ok, else: {:error, :verification_unavailable}
^expected = observed
if mode == "schedule" do
  2 = Process.get(:review_macs)
  16 = Process.get(:review_compares)
end
{:error, :invalid_signature} = MixerHosted.Billing.WebhookSignature.verify(body, [], [secret], timestamp)
IO.puts("PASS: #{mode}; result=#{inspect(observed)}; macs=#{Process.get(:review_macs)}; comparisons=#{Process.get(:review_compares)}; isolated control-flow/fault probe only")
