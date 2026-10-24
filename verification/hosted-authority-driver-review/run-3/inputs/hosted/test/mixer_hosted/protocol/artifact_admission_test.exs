defmodule MixerHosted.Protocol.ArtifactAdmissionTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, ArtifactJSON, ArtifactV3Policy}
  @fixtures Path.expand("../../../../services/protocol/testdata", __DIR__)
  @fixture Path.join(@fixtures, "signed-release-v3.json")
  @corpus Path.join(@fixtures, "release-v3-cases.json")
  @domain "mixer.artifact.v3\0"

  defp fixture do
    f = @fixture |> File.read!() |> Jason.decode!()

    Map.update!(f, "roots", fn roots ->
      Enum.map(roots, &Map.update!(&1, "public_key", fn b -> Base.decode64!(b) end))
    end)
  end

  defp signed_bytes do
    bytes = File.read!(@fixture)
    {:ok, spans, _} = ArtifactJSON.preflight(bytes, 65_536)

    {_, _, start, size} =
      Enum.find(spans, fn {start, size, _, _} ->
        Jason.decode!(binary_part(bytes, start, size)) == "signed_manifest"
      end)

    binary_part(bytes, start, size)
  end

  defp envelope(signed, payload),
    do:
      "{\"signed_manifest\":" <>
        signed <> ",\"payload\":" <> Jason.encode!(Base.encode64(payload)) <> "}"

  defp payload(f), do: Base.decode64!(f["payload"])

  defp admit(bytes, f),
    do: ArtifactAdmission.admit(bytes, f["host"], f["roots"], f["verification_time_unix"])

  defp standalone(bytes, f),
    do:
      ArtifactAdmission.admit_signed(
        bytes,
        payload(f),
        f["host"],
        f["roots"],
        f["verification_time_unix"]
      )

  defp sha(b), do: Base.encode16(:crypto.hash(:sha256, b), case: :lower)

  # Ephemeral private keys remain in this test process and are never retained.
  defp ephemeral(f) do
    {public, private} = :crypto.generate_key(:eddsa, :ed25519)
    root = hd(f["roots"]) |> Map.put("public_key", public)
    {Map.put(f, "roots", [root]), private}
  end

  defp sign(manifest, private, domain \\ @domain) do
    {:ok, cbor} = ArtifactCBOR.encode(manifest)
    signature = :crypto.sign(:eddsa, :none, domain <> cbor, [private, :ed25519])
    Jason.encode!(%{"manifest" => manifest, "signature" => Base.encode64(signature)})
  end

  test "exact original fixture bytes, CBOR, preimage and digest, with a checked signed target" do
    f = fixture()
    bytes = envelope(signed_bytes(), payload(f))
    assert {:ok, checked} = admit(bytes, f)
    assert checked.envelope_bytes == bytes
    assert checked.signed_manifest_bytes == signed_bytes()
    assert Base.encode16(checked.canonical_manifest_cbor, case: :lower) == f["manifest_cbor_hex"]

    assert Base.encode16(@domain <> checked.canonical_manifest_cbor, case: :lower) ==
             f["manifest_message_hex"]

    assert checked.manifest_sha256 == f["artifact_sha256"]

    assert checked.target ==
             Map.merge(f["host"]["scope"], %{
               "runtime" => f["host"]["runtime"],
               "manifest_sha256" => f["artifact_sha256"]
             })

    assert {:ok, ^checked} =
             ArtifactAdmission.recheck(
               checked,
               f["host"],
               f["roots"],
               f["verification_time_unix"]
             )
  end

  test "154 unchanged original signed manifest cases and 39 origin plus 14 namespace cases" do
    f = fixture()
    corpus = @corpus |> File.read!() |> Jason.decode!()
    assert length(corpus["cases"]) == 154
    assert length(corpus["origin_cases"]) == 39
    assert length(corpus["namespace_cases"]) == 14
    assert length(corpus["assignment_cases"]) == 36

    Enum.each(corpus["cases"], fn c ->
      assert match?({:ok, _}, standalone(c["signed_manifest_json"], f)) == c["accepted"],
             c["name"]
    end)

    Enum.each(corpus["origin_cases"], fn c ->
      assert ArtifactV3Policy.valid_origin?(c["value"]) == c["accepted"], c["value"]
    end)

    Enum.each(corpus["namespace_cases"], fn c ->
      assert ArtifactV3Policy.valid_namespace?(c["value"]) == c["accepted"], c["value"]
    end)
  end

  test "every closed manifest, scope, limits, descriptor and entry field rejects missing, extra, case and null" do
    f = fixture()
    manifest = f["signed_manifest"]["manifest"]

    paths = [
      [],
      ["scope"],
      ["limits"],
      ["capability_grants"],
      ["capability_grants", "entries", Access.at(0)]
    ]

    Enum.each(paths, fn path ->
      value = if path == [], do: manifest, else: get_in(manifest, path)

      Enum.each(Map.keys(value), fn key ->
        wrong_type =
          cond do
            is_map(value[key]) -> []
            is_list(value[key]) -> %{}
            is_binary(value[key]) -> 1
            is_integer(value[key]) -> "1"
          end

        for replacement <- [
              Map.put(value, key, wrong_type),
              Map.delete(value, key),
              Map.put(value, key, nil),
              Map.put(value, String.upcase(key), value[key]),
              Map.put(value, "unknown", true)
            ] do
          changed = if path == [], do: replacement, else: put_in(manifest, path, replacement)
          refute ArtifactV3Policy.manifest?(changed), inspect({path, key})
        end
      end)
    end)

    for key <-
          ~w(schema protocol guest_abi ui_schema state_min state_max compressed_bytes expanded_bytes created_at_unix) do
      for bad <- [-1, 3.0, "1", nil, true, 18_446_744_073_709_551_616] do
        refute ArtifactV3Policy.manifest?(Map.put(manifest, key, bad)), key
      end
    end
  end

  test "ordered duplicate detection and lexical closed numeric and Unicode rejection" do
    for bytes <- [
          "{\"a\":1,\"a\":2}",
          "{\"a\":1,\"\\u0061\":2}",
          "{\"x\":{\"a\":1,\"a\":2}}",
          "{\"a\":null}",
          "{\"a\":1.0}",
          "{\"a\":1e0}",
          "{\"a\":-0}",
          "{\"a\":01}",
          "{\"a\":18446744073709551616}",
          "{\"a\":\"\\uD800\"}",
          "{\"a\":\"\\uDC00\"}",
          "{\"a\":\"\\x12\"}",
          <<?{, ?", ?a, ?", ?:, ?", 255, ?", ?}>>,
          "{}{}",
          "[1,]",
          "{\"a\":1,}"
        ] do
      assert {:error, _} = ArtifactJSON.decode(bytes, 65_536)
    end

    assert {:ok, %{"a" => 18_446_744_073_709_551_615}, _, _} =
             ArtifactJSON.decode("{\"a\":18446744073709551615}", 65_536)

    assert {:ok, %{"a" => "😀"}, _, _} = ArtifactJSON.decode("{\"a\":\"\\ud83d\\ude00\"}", 65_536)
    assert {:ok, _, _, _} = ArtifactJSON.decode("{\"a\":9007199254740993}", 65_536)
  end

  test "lexical structural boundaries count before decoder collection allocation" do
    nested = String.duplicate("[", 16) <> "0" <> String.duplicate("]", 16)
    assert {:ok, _, %{max_depth: 16}} = ArtifactJSON.preflight(nested, 65_536)
    assert {:error, _} = ArtifactJSON.preflight("[" <> nested <> "]", 65_536)
    assert {:ok, _, _} = ArtifactJSON.preflight(Jason.encode!(List.duplicate(0, 256)), 65_536)
    assert {:error, _} = ArtifactJSON.preflight(Jason.encode!(List.duplicate(0, 257)), 65_536)
    exact = List.duplicate(List.duplicate(0, 256), 15) ++ [List.duplicate(0, 239)]
    assert {:ok, _, %{items: 4096}} = ArtifactJSON.preflight(Jason.encode!(exact), 65_536)

    assert {:error, _} =
             ArtifactJSON.preflight(
               Jason.encode!(List.replace_at(exact, 15, List.duplicate(0, 240))),
               65_536
             )

    object = for n <- 1..256, into: %{}, do: {Integer.to_string(n), 0}
    assert {:ok, _, _} = ArtifactJSON.preflight(Jason.encode!(object), 65_536)
    assert {:error, _} = ArtifactJSON.preflight(Jason.encode!(Map.put(object, "257", 0)), 65_536)
  end

  test "standalone, embedded signed bytes, payload and whole-envelope exact and one-over bounds" do
    f = fixture()
    signed = signed_bytes()
    standalone_exact = String.duplicate(" ", 65_536 - byte_size(signed)) <> signed
    assert {:ok, data} = standalone(standalone_exact, f)
    assert data.signed_manifest_bytes == standalone_exact
    refute Map.has_key?(data, :envelope_bytes)
    assert {:error, _} = standalone(" " <> standalone_exact, f)

    embedded_exact =
      "{" <>
        String.duplicate(" ", 65_536 - byte_size(signed)) <>
        binary_part(signed, 1, byte_size(signed) - 1)

    assert {:ok, checked} = admit(envelope(embedded_exact, payload(f)), f)
    assert byte_size(checked.signed_manifest_bytes) == 65_536

    assert {:error, _} =
             admit(
               envelope(
                 "{ " <> binary_part(embedded_exact, 1, byte_size(embedded_exact) - 1),
                 payload(f)
               ),
               f
             )

    {f, private} = ephemeral(f)
    payload = :binary.copy(<<42>>, 4_194_304)

    m =
      f["signed_manifest"]["manifest"]
      |> Map.put("payload_sha256", sha(payload))
      |> Map.put("compressed_bytes", byte_size(payload))
      |> Map.put("expanded_bytes", byte_size(payload))

    bytes = envelope(sign(m, private), payload)
    exact = bytes <> String.duplicate(" ", 6_291_456 - byte_size(bytes))
    assert byte_size(exact) == 6_291_456
    assert {:ok, checked} = admit(exact, f)
    assert byte_size(checked.payload) == 4_194_304
    assert {:error, :envelope_limit} = admit(exact <> " ", f)
    assert {:error, _} = admit(envelope(sign(m, private), payload <> "x"), f)
    assert {:error, _} = admit(envelope(sign(m, private), ""), f)
    one = "x"

    m =
      m
      |> Map.put("payload_sha256", sha(one))
      |> Map.put("compressed_bytes", 1)
      |> Map.put("expanded_bytes", 1)

    assert {:ok, _} = admit(envelope(sign(m, private), one), f)
  end

  test "envelope and signed outer fields are closed and canonical padded base64 is checked before decode" do
    f = fixture()
    signed = signed_bytes()
    p64 = Base.encode64(payload(f))
    bytes = envelope(signed, payload(f))

    for bad <- [
          "{}",
          "[]",
          "null",
          bytes <> "{}",
          String.replace(bytes, "\"payload\":", "\"Payload\":"),
          String.replace(bytes, "\"payload\":", "\"extra\":0,\"payload\":"),
          String.replace(bytes, "\"payload\":", "\"payload\":\"eA==\",\"payload\":"),
          String.replace(bytes, "\"payload\":", "\"\\u0070ayload\":\"eA==\",\"payload\":"),
          String.replace(bytes, Jason.encode!(p64), "null"),
          String.replace(bytes, Jason.encode!(p64), "[]")
        ] do
      assert {:error, _} = admit(bad, f)
    end

    for invalid <- [
          "eA",
          "eA=",
          "eB==",
          "eA==\n",
          "eA--",
          "eA__",
          "eA===",
          "=AAA",
          "AA=A",
          "",
          "A"
        ] do
      assert {:error, _} =
               admit(
                 "{\"signed_manifest\":" <>
                   signed <> ",\"payload\":" <> Jason.encode!(invalid) <> "}",
                 f
               )
    end

    sm = f["signed_manifest"]

    for bad <- [
          Map.delete(sm, "signature"),
          Map.put(sm, "Signature", sm["signature"]),
          Map.put(sm, "extra", 1),
          Map.put(sm, "signature", nil),
          Map.put(sm, "signature", "AAAA")
        ] do
      assert {:error, _} = standalone(Jason.encode!(bad), f)
    end

    # Canonical tail-bit changes must reject even if Base.decode64 accepts them.
    text = sm["signature"]
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    <<last>> = binary_part(text, 85, 1)
    {index, _} = :binary.match(alphabet, <<last>>)
    invalid = binary_part(text, 0, 85) <> binary_part(alphabet, index + 1, 1) <> "=="
    assert {:error, _} = standalone(Jason.encode!(Map.put(sm, "signature", invalid)), f)
  end

  test "full host and root policies, uint64 exactness, wrong signature and current-policy recheck" do
    f = fixture()
    bytes = envelope(signed_bytes(), payload(f))
    assert {:ok, checked} = admit(bytes, f)
    root = hd(f["roots"])
    now = f["verification_time_unix"]

    root_changes = [
      {"key_id", "another"},
      {"public_key", <<0::256>>},
      {"public_key", <<0>>},
      {"public_key", root["public_key"] <> "x"},
      {"artifact", false},
      {"revoked", true},
      {"artifact", "true"},
      {"assignment", 0},
      {"revoked", nil},
      {"not_before_unix", now + 1},
      {"not_after_unix", now},
      {"not_before_unix", -1},
      {"not_after_unix", 18_446_744_073_709_551_616},
      {"scope", Map.put(root["scope"], "project", "other")}
    ]

    Enum.each(root_changes, fn {key, value} ->
      roots = [Map.put(root, key, value)]
      assert {:error, _} = ArtifactAdmission.admit(bytes, f["host"], roots, now), key
      assert {:error, _} = ArtifactAdmission.recheck(checked, f["host"], roots, now), key
    end)

    for roots <- [
          [],
          List.duplicate(root, 129),
          [root, root],
          [root, Map.put(root, "key_id", "other") |> Map.put("public_key", "bad")],
          [Map.put(root, "not_before_unix", 5) |> Map.put("not_after_unix", 5)]
        ] do
      assert {:error, _} = ArtifactAdmission.admit(bytes, f["host"], roots, now)
    end

    for key <- Map.keys(root) do
      assert {:error, _} = ArtifactAdmission.admit(bytes, f["host"], [Map.delete(root, key)], now)
    end

    valid_window = [root |> Map.put("not_before_unix", now) |> Map.put("not_after_unix", now + 1)]
    assert {:ok, _} = ArtifactAdmission.admit(bytes, f["host"], valid_window, now)
    assert {:error, _} = ArtifactAdmission.recheck(checked, f["host"], valid_window, now + 1)

    for bad <- [-1, 1.0, nil, 18_446_744_073_709_551_616] do
      assert {:error, _} = ArtifactAdmission.admit(bytes, f["host"], f["roots"], bad)
    end

    h = f["host"]

    for {key, value} <- [
          {"protocol", 2},
          {"protocol", 3.0},
          {"guest_abi", 1},
          {"ui_schema", 2},
          {"runtime", String.duplicate("0", 64)},
          {"scope", Map.put(h["scope"], "app", "other")},
          {"state_version", 2},
          {"state_version", -1},
          {"capability_hashes", %{}},
          {"capability_hashes", nil},
          {"max_payload_bytes", 1},
          {"max_payload_bytes", 4_194_305},
          {"limits", Map.put(h["limits"], "fuel", 1)},
          {"limits", Map.put(h["limits"], "memory_bytes", 0)}
        ] do
      assert {:error, _} =
               ArtifactAdmission.recheck(checked, Map.put(h, key, value), f["roots"], now),
             key
    end

    for key <- Map.keys(h) do
      assert {:error, _} = ArtifactAdmission.recheck(checked, Map.delete(h, key), f["roots"], now)
    end

    {ef, private} = ephemeral(f)
    m = ef["signed_manifest"]["manifest"]
    assert {:error, _} = admit(envelope(sign(m, private, "mixer.artifact.v2\0"), payload(f)), ef)
    assert {:error, _} = admit(envelope(sign(m, private), payload(f) <> "x"), ef)

    assert {:error, _} =
             admit(envelope(sign(m, private), :binary.copy("x", byte_size(payload(f)))), ef)

    wide =
      m
      |> Map.put("state_min", 9_007_199_254_740_993)
      |> Map.put("state_max", 18_446_744_073_709_551_615)
      |> Map.put("created_at_unix", 18_446_744_073_709_551_615)

    wide_host = Map.put(ef["host"], "state_version", 9_007_199_254_740_993)

    assert {:ok, _} =
             ArtifactAdmission.admit(
               envelope(sign(wide, private), payload(f)),
               wide_host,
               ef["roots"],
               now
             )

    for key <- Map.keys(Map.from_struct(checked)) do
      changed = Map.put(checked, key, nil)
      assert {:error, _} = ArtifactAdmission.recheck(changed, h, f["roots"], now), inspect(key)
    end

    assert {:error, _} = ArtifactAdmission.recheck(%{valid: true}, h, f["roots"], now)
  end

  test "semantic grant, asset, compression and signed resource rejection does not rely on signatures" do
    m = fixture()["signed_manifest"]["manifest"]

    for {key, value} <- [
          {"schema", 2},
          {"source_commit", String.duplicate("A", 40)},
          {"source_map_sha256", String.duplicate("A", 64)},
          {"compression", "gzip"},
          {"asset_hashes", %{"asset" => String.duplicate("a", 64)}},
          {"state_min", 2},
          {"capability_hashes", %{"other" => String.duplicate("a", 64)}},
          {"compressed_bytes", 4_194_305},
          {"limits", Map.put(m["limits"], "fuel", 1_000_001)},
          {"created_at_unix", 0}
        ] do
      refute ArtifactV3Policy.manifest?(Map.put(m, key, value)), key
    end

    descriptor = m["capability_grants"]

    for entries <- [
          Enum.reverse(descriptor["entries"]),
          [hd(descriptor["entries"]), hd(descriptor["entries"])],
          nil
        ] do
      refute ArtifactV3Policy.manifest?(
               Map.put(m, "capability_grants", Map.put(descriptor, "entries", entries))
             )
    end

    empty = Map.put(descriptor, "entries", [])
    assert ArtifactV3Policy.manifest?(Map.put(m, "capability_grants", empty))
  end
end
