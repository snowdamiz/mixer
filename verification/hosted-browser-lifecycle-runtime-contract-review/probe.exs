Code.require_file("hosted/lib/mixer_hosted/browser_auth/storage_schema.ex")

alias MixerHosted.BrowserAuth.StorageSchema

manifest = StorageSchema.catalog_manifest()
IO.puts("functions=#{map_size(manifest.functions)}")
IO.puts("public=#{map_size(StorageSchema.public_signatures())}")

for {name, args} <- Enum.sort(StorageSchema.public_signatures()) do
  result = if name in ~w(mixer_browser_fail_claim mixer_browser_logout mixer_browser_expire), do: "boolean", else: "jsonb"
  IO.puts("signature|#{name}|#{args}|#{result}")
end

for {name, function} <- Enum.sort(manifest.functions) do
  true = function.security_definer
  true = function.settings == ["search_path=pg_catalog", "statement_timeout=5s", "lock_timeout=500ms", "idle_in_transaction_session_timeout=5s", "bytea_output=hex"]
  true = byte_size(function.source) > 0
  IO.puts("manifest|#{name}|#{Base.encode16(:crypto.hash(:sha256, function.source), case: :lower)}")
end
