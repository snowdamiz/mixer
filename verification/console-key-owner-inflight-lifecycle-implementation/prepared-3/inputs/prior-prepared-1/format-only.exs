# Separately root-released formatting pass. No product source is compiled/loaded.
true = System.version() == "1.20.4"
true = System.otp_release() == "29"
[evidence] = System.argv()

files = [
  "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
  "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs"
]

results = Enum.map(files, fn relative ->
  path = Path.join(__DIR__, "inputs/" <> relative)
  original = File.read!(path)
  formatted = (Code.format_string!(original, file: path) |> IO.iodata_to_binary()) <> "\n"
  output = Path.join(evidence, Path.basename(relative))
  File.write!(output, formatted)
  %{
    source: relative,
    source_sha256: Base.encode16(:crypto.hash(:sha256, original), case: :lower),
    output: Path.basename(relative),
    bytes: byte_size(formatted),
    sha256: Base.encode16(:crypto.hash(:sha256, formatted), case: :lower),
    changed: original != formatted
  }
end)

File.write!(Path.join(evidence, "formatting.json"), Jason.encode!(%{files: results}, pretty: true))
IO.inspect(results, label: "FORMATTING_ONLY")
