{:ok, _} = Application.ensure_all_started(:crypto)
true = function_exported?(:crypto, :mac, 4)
true = function_exported?(:crypto, :hash_equals, 2)
true = :crypto.hash_equals(<<0::256>>, <<0::256>>)
false = :crypto.hash_equals(<<0::256>>, <<1::256>>)
try do
  :crypto.hash_equals(<<0::256>>, <<0::248>>)
  raise "hash_equals unexpectedly accepted a length mismatch"
rescue
  ArgumentError -> :ok
end
32 = byte_size(:crypto.mac(:hmac, :sha256, "synthetic probe key", ["a", ".", <<0, 255>>]))
IO.puts("PASS: real OTP mac/4 and hash_equals/2 available; 32-byte SHA256 HMAC; equal/mismatch/length-error semantics")
IO.inspect(:crypto.info(), label: "crypto_info", limit: :infinity)
IO.inspect(:crypto.info_lib(), label: "crypto_library", limit: :infinity)
