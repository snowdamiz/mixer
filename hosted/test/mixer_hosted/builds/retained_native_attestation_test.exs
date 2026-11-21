defmodule MixerHosted.Builds.RetainedNativeAttestationTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Builds.{NativeDevelopmentAttestation, RetainedNativeArtifacts}
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  alias MixerHosted.Builds.NativeDevelopmentAttestation.ExpectedBuild
  alias MixerHosted.CustomerBuilds.Selection

  @external_resource Path.join(__DIR__, "fixtures/native_development_attestation_v1.json")
  @envelope File.read!(@external_resource)
  @public_spki Base.decode64!("MCowBQYDK2VwAyEAbI5vs7Y5erKiaXLud7/FaVIkaFMUitB0ZFID9nt/wHE=")
  @operation String.duplicate("a", 64)
  @other_operation String.duplicate("b", 64)
  @binding String.duplicate("4", 64)
  @other_binding String.duplicate("5", 64)
  @magic "MXNATIVE1\n"
  @config_key :native_development_dispatch

  @moduletag :tmp_dir
  setup %{tmp_dir: root} do
    File.chmod!(root, 0o700)
    previous = Application.fetch_env(:mixer_hosted, @config_key)
    Application.put_env(:mixer_hosted, @config_key, %{retained_root: root})

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, @config_key, value)
        :error -> Application.delete_env(:mixer_hosted, @config_key)
      end
    end)

    %{root: root}
  end

  test "retained Go signer products establish the capture used by the pure verifier", %{
    root: root
  } do
    refs = retain(root, @operation, products())
    assert {:ok, binding} = RetainedNativeArtifacts.verify_ios_development(@operation, refs)
    assert binding == @binding

    {:ok, selection} =
      Selection.new(%{
        organization_id: "local-org",
        project_id: "local-project",
        application_id: "local-app",
        build_id: "local-build",
        platform: "ios",
        source_sha256: String.duplicate("1", 64),
        toolchain_lock_sha256: String.duplicate("2", 64),
        build_definition_sha256: String.duplicate("3", 64)
      })

    assert :ok =
             NativeDevelopmentAttestation.verify(
               @envelope,
               %ExpectedBuild{
                 origin: "http://127.0.0.1:59709",
                 selection: selection,
                 state: :native_succeeded,
                 worker_completion_pending: false,
                 journal_revision: 2,
                 attempt: 1,
                 native_binding_sha256: binding,
                 artifacts: refs
               },
               @public_spki
             )
  end

  test "each product must resolve under the supplied operation even if present elsewhere", %{
    root: root
  } do
    [app, symbols, inventory] = products()
    refs = retain(root, @other_operation, [app, symbols, inventory])

    assert {:ok, @binding} =
             RetainedNativeArtifacts.verify_ios_development(@other_operation, refs)

    assert_invalid(@operation, refs)
    assert_invalid("../#{@other_operation}", refs)
    retain(root, @operation, [app, inventory])
    assert_invalid(@operation, refs)

    retain(root, @operation, [symbols])
    assert {:ok, @binding} = RetainedNativeArtifacts.verify_ios_development(@operation, refs)
    assert_invalid(@operation, Enum.reverse(refs))
    assert_invalid(@operation, tl(refs))
  end

  test "refuses mixed archives and foreign inventories even when all exact bytes are retained", %{
    root: root
  } do
    [app, symbols, inventory] = products()
    [foreign_app, foreign_symbols, foreign_inventory] = products(@other_binding)

    [app_ref, symbols_ref, inv_ref, foreign_app_ref, foreign_symbols_ref, foreign_inv_ref] =
      retain(root, @operation, [
        app,
        symbols,
        inventory,
        foreign_app,
        foreign_symbols,
        foreign_inventory
      ])

    assert_invalid(@operation, [app_ref, foreign_symbols_ref, inv_ref])
    assert_invalid(@operation, [app_ref, symbols_ref, foreign_inv_ref])
    assert_invalid(@operation, [foreign_app_ref, foreign_symbols_ref, inv_ref])

    assert {:ok, @other_binding} =
             RetainedNativeArtifacts.verify_ios_development(@operation, [
               foreign_app_ref,
               foreign_symbols_ref,
               foreign_inv_ref
             ])
  end

  test "requires both exact inventory parent triples under the same capture", %{root: root} do
    [app, symbols, _] = products()
    [app_ref, symbols_ref] = retain(root, @operation, [app, symbols])
    correct = inventory_fields(app, symbols, @binding)

    for key <- ["parentApp", "parentSymbols"],
        {field, value} <- [
          {"kind", "resource_inventory"},
          {"sha256", String.duplicate("7", 64)},
          {"sizeBytes", 1},
          {"sizeBytes", correct[key]["sizeBytes"] / 1},
          {"ownedPath", "/unexpected"}
        ] do
      bytes = correct |> Map.update!(key, &Map.put(&1, field, value)) |> Jason.encode!()
      [bad_ref] = retain(root, @operation, [{:resource_inventory, bytes}])
      assert_invalid(@operation, [app_ref, symbols_ref, bad_ref])
    end

    bytes =
      Jason.encode!(correct)
      |> String.replace(~s("parentApp":{), ~s("parentApp":{"kind":"unsigned_native_binary",))

    [duplicate_parent] = retain(root, @operation, [{:resource_inventory, bytes}])
    assert_invalid(@operation, [app_ref, symbols_ref, duplicate_parent])
  end

  test "checks length and digest for all three products, including the archive payload", %{
    root: root
  } do
    products = products()
    refs = retain(root, @operation, products)

    for {{{_, bytes}, ref}, index} <- Enum.with_index(Enum.zip(products, refs)) do
      path = retained_path(root, @operation, ref)
      offset = byte_size(bytes) - 1
      <<prefix::binary-size(^offset), last>> = bytes
      tampered = <<prefix::binary, Bitwise.bxor(last, 1)>>
      replace(path, tampered)
      assert_invalid(@operation, refs)
      replace(path, bytes <> <<0>>)
      assert_invalid(@operation, refs)
      replace(path, bytes)

      assert_invalid(
        @operation,
        List.replace_at(refs, index, %{ref | size_bytes: ref.size_bytes + 1})
      )
    end

    assert {:ok, @binding} = RetainedNativeArtifacts.verify_ios_development(@operation, refs)
  end

  test "bounds the metadata and rejects ambiguous or malformed archive headers", %{root: root} do
    [app, symbols, inventory] = products()
    [app_ref, symbols_ref] = retain(root, @operation, [app, symbols])
    limit = 8 * 1024 * 1024
    source_inventory = elem(inventory, 1)

    oversized_inventory =
      source_inventory <> :binary.copy(" ", limit + 1 - byte_size(source_inventory))

    [inventory_ref] = retain(root, @operation, [{:resource_inventory, oversized_inventory}])
    assert_invalid(@operation, [app_ref, symbols_ref, inventory_ref])

    header = ~s({"version":1,"kind":"unsigned_native_binary","binding":"#{@binding}"})
    oversized_header = header <> :binary.copy(" ", limit + 1 - byte_size(header))

    for malformed <- [
          <<@magic, 0::64>>,
          <<@magic, 1000::64, "{}">>,
          archive_bytes(oversized_header),
          archive_bytes(~s({"version":1,"kind":"debug_symbols","binding":"#{@binding}"})),
          archive_bytes(
            ~s({"version":1,"kind":"unsigned_native_binary","binding":"#{@binding}","binding":"#{@binding}"})
          )
        ] do
      bad_app = {:unsigned_native_binary, malformed}

      bad_inventory =
        {:resource_inventory, Jason.encode!(inventory_fields(bad_app, symbols, @binding))}

      [bad_app_ref, bad_inventory_ref] = retain(root, @operation, [bad_app, bad_inventory])
      assert_invalid(@operation, [bad_app_ref, symbols_ref, bad_inventory_ref])
    end
  end

  test "accepts producer metadata with large entry arrays", %{root: root} do
    entries =
      for index <- 1..300 do
        %{"path" => "resource-#{index}", "mode" => 0o444, "sha256" => sha256("")}
      end

    app =
      {:unsigned_native_binary,
       archive_bytes(
         Jason.encode!(%{
           "version" => 1,
           "kind" => "unsigned_native_binary",
           "binding" => @binding,
           "entries" => entries
         })
       )}

    symbols = archive(:debug_symbols, @binding)

    inventory =
      inventory_fields(app, symbols, @binding)
      |> Map.put("entries", entries)
      |> Jason.encode!()

    refs = retain(root, @operation, [app, symbols, {:resource_inventory, inventory}])
    assert {:ok, @binding} = RetainedNativeArtifacts.verify_ios_development(@operation, refs)
  end

  defp assert_invalid(operation, refs) do
    assert {:error, :invalid_retained_products} =
             RetainedNativeArtifacts.verify_ios_development(operation, refs)
  end

  # Reconstruct the synthetic products from Go's newBuildFixture. The signed
  # envelope and its public SPKI come from the separately retained Go run.
  defp products(binding \\ @binding) do
    app = archive(:unsigned_native_binary, binding)
    symbols = archive(:debug_symbols, binding)

    ordered =
      Jason.OrderedObject.new(
        version: 1,
        kind: "resource_inventory",
        parentApp: ordered_ref(app),
        parentSymbols: ordered_ref(symbols),
        bindingSHA256: binding
      )

    [app, symbols, {:resource_inventory, Jason.encode!(ordered)}]
  end

  defp archive(kind, binding) do
    header =
      Jason.OrderedObject.new(binding: binding, kind: Atom.to_string(kind), version: 1)
      |> Jason.encode!()

    {kind, archive_bytes(header)}
  end

  defp archive_bytes(header),
    do: <<@magic, byte_size(header)::64, header::binary, "archive payload">>

  defp inventory_fields(app, symbols, binding) do
    %{
      "version" => 1,
      "kind" => "resource_inventory",
      "parentApp" => Map.new(ordered_ref(app).values),
      "parentSymbols" => Map.new(ordered_ref(symbols).values),
      "bindingSHA256" => binding
    }
  end

  defp ordered_ref({kind, bytes}) do
    Jason.OrderedObject.new([
      {"kind", Atom.to_string(kind)},
      {"sha256", sha256(bytes)},
      {"sizeBytes", byte_size(bytes)}
    ])
  end

  defp retain(root, operation, products) do
    File.mkdir_p!(Path.join([root, operation, "native"]))

    Enum.map(products, fn {kind, bytes} ->
      ref = %ArtifactRef{kind: kind, sha256: sha256(bytes), size_bytes: byte_size(bytes)}
      path = retained_path(root, operation, ref)
      File.write!(path, bytes, [:exclusive])
      File.chmod!(path, 0o444)
      ref
    end)
  end

  defp retained_path(root, operation, ref), do: Path.join([root, operation, "native", ref.sha256])

  defp replace(path, bytes) do
    File.chmod!(path, 0o600)
    File.write!(path, bytes)
    File.chmod!(path, 0o444)
  end

  defp sha256(bytes), do: :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)
end
