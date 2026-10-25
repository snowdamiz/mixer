# Approved dependency-only probe. Start Elixir with only the pinned Jason ebin
# path, never mix, a project application, Mixer modules or a dependency script.
[fixture_path, output_path] = System.argv()
loaded_mixer = fn ->
  :code.all_loaded()
  |> Enum.filter(fn {module, _} -> String.starts_with?(Atom.to_string(module), "Elixir.Mixer") end)
end
[] = loaded_mixer.()
{:ok, app} = :file.consult(Path.join(:code.lib_dir(:jason, :ebin), "jason.app"))
[{:application, :jason, metadata}] = app
"1.4.5" = to_string(Keyword.fetch!(metadata, :vsn))
original = fixture_path |> File.read!() |> Jason.decode!() |> Map.fetch!("cases") |> hd() |> Map.fetch!("request")
hash = fn bytes -> :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower) end
codepoints = [7, 8, 9, 10, 11, 12, 13, 27, 0, 6, 14, 31, 32, 126, 127, 159, 160,
              0xD7FF, 0xE000, 0xFFFD, 0xFFFE, 0xFFFF, 0x10000, 0x10FFFF]
vectors = for cp <- codepoints do
  string = "a" <> <<cp::utf8>> <> "b"
  fence = 9_223_372_036_854_775_807
  ref = original["ref"] |> Map.put("organization_id", string) |> Map.put("fence", Integer.to_string(fence))
  source = original["spec"]["source"] |> Map.put("reference", string)
  spec = original["spec"] |> Map.put("organization_id", string) |> Map.put("source", source)
  operation_bytes = Jason.encode!(["mixer-build-operation-v1", original["guard"]["record_id"],
    ref["organization_id"], ref["project_id"], ref["application_id"], ref["build_id"], ref["platform"], ref["attempt"], fence])
  id = hash.(operation_bytes)
  binding_bytes = Jason.encode!(["mixer-worker-binding-v1", id, original["guard"]["record_id"],
    [ref["organization_id"], ref["project_id"], ref["application_id"], ref["build_id"], ref["platform"], ref["attempt"], ref["fence"]],
    [spec["organization_id"], spec["project_id"], spec["application_id"], spec["build_id"], spec["platform"], source["kind"], source["sha256"], source["reference"], spec["toolchain_lock_sha256"], spec["build_definition_sha256"]], original["deadline_ms"]])
  request = original |> Map.put("ref", ref) |> Map.put("spec", spec) |> Map.put("operation_id", id) |> Map.put("immutable_sha256", hash.(binding_bytes))
  %{codepoint: cp, printable: String.printable?(string), operation_json: operation_bytes,
    binding_json: binding_bytes, request: request}
end
[] = loaded_mixer.()
File.write!(output_path, Jason.encode!(%{schema: 1, source: "Jason-1.4.5-dependency-only", vectors: vectors}, pretty: true) <> "\n")
IO.puts(Jason.encode!(%{vectors: length(vectors), mixer_modules_loaded: 0, jason: "1.4.5", elixir: System.version(), otp: :erlang.system_info(:otp_release) |> to_string(), scope: "dependency-only-byte-and-printable-repertoire-probe"}))
