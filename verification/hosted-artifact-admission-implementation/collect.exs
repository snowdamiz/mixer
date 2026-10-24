alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactJSON, ArtifactV3Policy, ArtifactCBOR}
[fixture_path, corpus_path, output] = System.argv()
sha = fn b -> Base.encode16(:crypto.hash(:sha256, b), case: :lower) end
fbytes = File.read!(fixture_path)
f = Jason.decode!(fbytes) |> Map.update!("roots", fn roots -> Enum.map(roots, &Map.update!(&1, "public_key", fn b -> Base.decode64!(b) end)) end)
cbytes = File.read!(corpus_path)
c = Jason.decode!(cbytes)
{:ok, spans, _} = ArtifactJSON.preflight(fbytes, 65_536)
{_, _, start, size} = Enum.find(spans, fn {start, size, _, _} -> Jason.decode!(binary_part(fbytes, start, size)) == "signed_manifest" end)
signed = binary_part(fbytes, start, size)
payload = Base.decode64!(f["payload"])
verify = fn b -> match?({:ok, _}, ArtifactAdmission.admit_signed(b, payload, f["host"], f["roots"], f["verification_time_unix"])) end
result = fn kind, name, input, expected, accepted -> %{kind: kind, name: name, inputSHA256: sha.(input), expected: expected, accepted: accepted} end
results = [result.("fixture", "signed_manifest", signed, true, verify.(signed))] ++
  Enum.map(c["cases"], fn v -> result.("manifest", v["name"], v["signed_manifest_json"], v["accepted"], verify.(v["signed_manifest_json"])) end) ++
  Enum.map(c["origin_cases"], fn v -> result.("origin", v["value"], v["value"], v["accepted"], ArtifactV3Policy.valid_origin?(v["value"])) end) ++
  Enum.map(c["namespace_cases"], fn v -> result.("namespace", v["value"], v["value"], v["accepted"], ArtifactV3Policy.valid_namespace?(v["value"])) end)
if Enum.any?(results, &(&1.expected != &1.accepted)), do: raise("corpus mismatch")
File.write!(Path.join(output, "elixir-results.json"), Jason.encode!(%{results: results, assignmentCasesOutOfScope: 36, fixtureFileSHA256: sha.(fbytes), corpusFileSHA256: sha.(cbytes)}, pretty: true))

# Observe isolated process heap/stack and referenced binaries; these are not RSS,
# global concurrency or transient allocation ceilings. Inputs exist before spawn.
observe = fn name, bytes, fun ->
  parent = self()
  ref = make_ref()
  {pid, monitor} = spawn_monitor(fn ->
    :erlang.garbage_collect()
    {:memory, before_mem} = Process.info(self(), :memory)
    {:reductions, before_red} = Process.info(self(), :reductions)
    start = System.monotonic_time(:microsecond)
    result = fun.(bytes)
    elapsed = System.monotonic_time(:microsecond) - start
    {:memory, after_mem} = Process.info(self(), :memory)
    {:reductions, after_red} = Process.info(self(), :reductions)
    {:binary, binaries} = Process.info(self(), :binary)
    status = case result do {:ok, _, stats} -> %{status: "lexically_admitted", stats: stats}; {:ok, _} -> %{status: "admitted"}; {:error, reason} -> %{status: "rejected", reason: reason} end
    send(parent, {ref, %{name: name, inputBytes: byte_size(bytes), inputSHA256: sha.(bytes), result: status, elapsedMicroseconds: elapsed, processMemoryBefore: before_mem, processMemoryAfter: after_mem, referencedBinaryBytesAfter: Enum.sum(for {_, size, _} <- binaries, do: size), reductions: after_red-before_red}})
  end)
  sample = fn recur, high ->
    high = case Process.info(pid, :memory) do {:memory, n} -> max(n, high); nil -> high end
    receive do
      {^ref, row} ->
        receive do {:DOWN, ^monitor, :process, ^pid, :normal} -> :ok end
        Map.put(row, :sampledProcessMemoryHigh, high)
      {:DOWN, ^monitor, :process, ^pid, reason} -> raise("observation failed: #{inspect(reason)}")
    after 1 -> recur.(recur, high)
    end
  end
  sample.(sample, 0)
end
preflight = fn bytes -> ArtifactJSON.preflight(bytes, 6_291_456) end
exact_items = Jason.encode!(List.duplicate(List.duplicate(0, 256), 15) ++ [List.duplicate(0, 239)])
large_string = Jason.encode!(%{"payload" => :binary.copy("A", 5_592_408)})
{public, private} = :crypto.generate_key(:eddsa, :ed25519)
large_payload = :binary.copy(<<42>>, 4_194_304)
m = f["signed_manifest"]["manifest"] |> Map.put("payload_sha256", sha.(large_payload)) |> Map.put("compressed_bytes", byte_size(large_payload)) |> Map.put("expanded_bytes", byte_size(large_payload))
{:ok, cbor} = ArtifactCBOR.encode(m)
signature = :crypto.sign(:eddsa, :none, "mixer.artifact.v3\0" <> cbor, [private, :ed25519])
large_envelope = Jason.encode!(%{"signed_manifest" => %{"manifest" => m, "signature" => Base.encode64(signature)}, "payload" => Base.encode64(large_payload)})
large_envelope = large_envelope <> String.duplicate(" ", 6_291_456-byte_size(large_envelope))
roots = [Map.put(hd(f["roots"]), "public_key", public)]
rows = [observe.("4096-structural-items", exact_items, preflight),
        observe.("4097-structural-items-rejected", Jason.encode!(List.duplicate(List.duplicate(0, 256), 15) ++ [List.duplicate(0, 240)]), preflight),
        observe.("long-bounded-string-linear-scan", large_string, preflight),
        observe.("100000-nesting-early-rejection", String.duplicate("[", 100_000) <> "0" <> String.duplicate("]", 100_000), preflight),
        observe.("60000-digit-early-rejection", String.duplicate("9", 60_000), preflight),
        observe.("6MiB-body-4MiB-payload-full-admission", large_envelope, fn b -> ArtifactAdmission.admit(b, f["host"], roots, f["verification_time_unix"]) end),
        observe.("6MiB-plus-one-byte-early-rejection", large_envelope <> " ", fn b -> ArtifactAdmission.admit(b, f["host"], roots, f["verification_time_unix"]) end)]
File.write!(Path.join(output, "parser-observations.json"), Jason.encode!(%{observations: rows, scope: "One isolated process per call; input already allocated before spawn. Sampled process memory is heap/stack and excludes referenced off-heap binaries, native crypto allocator and unsampled transients. No total RSS, allocation, concurrent-request or deployment ceiling is claimed. Runtime/memory observations are platform-specific evidence, not API guarantees. Ephemeral test private key exists only in this collector VM and is not written."}, pretty: true))
IO.puts("208 exact-input verdicts; 7 parser/admission observations; 36 assignment cases out of scope")
