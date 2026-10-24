# Fault injection is confined to this disposable BEAM process. No service or
# installed library file is changed; the production candidate is unmodified.
Code.require_file("candidate/webhook_signature.ex", __DIR__)
[mode] = System.argv()
true = mode in ["error", "throw", "exit", "comparison"]
vector = __DIR__ |> Path.join("vectors.json") |> File.read!() |> :json.decode() |> hd()
body = Base.decode16!(vector["body_hex"], case: :lower)
secret = Base.decode16!(vector["secret_hex"], case: :lower)
header = "t=#{vector["timestamp"]},v1=#{vector["signature"]}"
:ok = MixerHosted.Billing.WebhookSignature.verify(body, [header], [secret], vector["timestamp"])

# Load a test-only crypto module in this child VM after exercising real crypto.
true = :code.unstick_mod(:crypto)
:code.purge(:crypto)
true = :code.delete(:crypto)
System.put_env("MIXER_SIGNATURE_FAULT", mode)

Code.compile_string("""
defmodule :crypto do
  def mac(:hmac, :sha256, _secret, _message) do
    case System.fetch_env!("MIXER_SIGNATURE_FAULT") do
      "error" -> raise "synthetic crypto unavailable"
      "throw" -> throw(:synthetic_crypto_unavailable)
      "exit" -> exit(:synthetic_crypto_unavailable)
      "comparison" -> <<0::256>>
    end
  end
  def hash_equals(_, _), do: raise("synthetic comparison unavailable")
end
""")

{:error, :verification_unavailable} =
  MixerHosted.Billing.WebhookSignature.verify(body, [header], [secret], vector["timestamp"])

{:error, :invalid_signature} =
  MixerHosted.Billing.WebhookSignature.verify(body, [], [secret], vector["timestamp"])

IO.puts(
  "PASS: #{mode} injection fails closed in isolated child VM; ordinary invalid input unchanged"
)
