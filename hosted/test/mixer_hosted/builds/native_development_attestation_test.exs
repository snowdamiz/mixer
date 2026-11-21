defmodule MixerHosted.Builds.NativeDevelopmentAttestationTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  alias MixerHosted.Builds.NativeDevelopmentAttestation, as: Attestation
  alias MixerHosted.Builds.NativeDevelopmentAttestation.ExpectedBuild
  alias MixerHosted.CustomerBuilds.Selection

  @external_resource Path.join(__DIR__, "fixtures/native_development_attestation_v1.json")
  @envelope File.read!(@external_resource)
  @spki Base.decode64!("MCowBQYDK2VwAyEAbI5vs7Y5erKiaXLud7/FaVIkaFMUitB0ZFID9nt/wHE=")
  @other_spki Base.decode64!("MCowBQYDK2VwAyEAFm5EoEbjk9o3lwLh5j/Q1wDfmeUp+3VXMmQNbJqcjdA=")
  @alternate_signature "hvto+/1AE7JgVTNUbeqxYJSRa8RYKcprsIhsVeNfQvj9vEtoP6xXgWXp+SjjNmzN20Rwytx1BrBgLE7YXD5AAw=="
  @other_domain_signature "YJAb2M/Y3q2WS+OQzqALW0h+PraMVU88o7UgEhIDgq0sjrql9OweGTB+wHfK8KvKm993CJvr3deYmJQM2uBxAQ=="
  @wrong_id_signature "I7s+XbDNcPgMSavZkRePyx8dikxElAShVyub5c7xMD4mH9dp52OXtHNXtayi+cOXUqwRruxq9XBjJdNpIMhQCg=="

  # Expected inputs come from the synthetic build serving the Go signer.
  # This setup deliberately does not decode the retained Go envelope.
  setup do
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

    build = %ExpectedBuild{
      origin: "http://127.0.0.1:59709",
      selection: selection,
      state: :native_succeeded,
      worker_completion_pending: false,
      journal_revision: 2,
      attempt: 1,
      native_binding_sha256: String.duplicate("4", 64),
      artifacts: [
        %ArtifactRef{
          kind: :unsigned_native_binary,
          sha256: "2509e594ee9097ea6dc8ada9a38f0641a3cc3da9538424f03525dce4b9980ba9",
          size_bytes: 155
        },
        %ArtifactRef{
          kind: :debug_symbols,
          sha256: "5b026774909cc7336defaf782ac8c9072e7749af5c46347ee29a0b700230a7d3",
          size_bytes: 146
        },
        %ArtifactRef{
          kind: :resource_inventory,
          sha256: "d4905ce130e1a0fca2a6f2cfc3124b8cbfbc4c1f90449a26e3b9d414fac65823",
          size_bytes: 395
        }
      ]
    }

    %{build: build}
  end

  test "verifies the exact retained Go v1 envelope under its independently pinned SPKI", %{
    build: build
  } do
    assert :ok = Attestation.verify(@envelope, build, @spki)
  end

  test "requires the enrolled Ed25519 key and its Go SPKI digest", %{build: build} do
    assert {:error, :invalid_signature} = Attestation.verify(@envelope, build, @other_spki)
    assert {:error, :invalid_trusted_key} = Attestation.verify(@envelope, build, @spki <> <<0>>)

    wrong_id =
      @envelope
      |> String.replace(sha256(@spki), sha256(@other_spki), global: false)
      |> replace_signature(@wrong_id_signature)

    assert {:error, :build_binding_mismatch} = Attestation.verify(wrong_id, build, @spki)
  end

  test "binds the complete selection independently of the signed selection", %{build: build} do
    changes = [
      organization_id: "other-org",
      project_id: "other-project",
      application_id: "other-app",
      build_id: "other-build",
      source_sha256: String.duplicate("5", 64),
      toolchain_lock_sha256: String.duplicate("6", 64),
      build_definition_sha256: String.duplicate("7", 64)
    ]

    for {field, value} <- changes do
      other = %{build | selection: struct!(build.selection, [{field, value}])}

      assert {:error, :build_binding_mismatch} = Attestation.verify(@envelope, other, @spki),
             inspect(field)
    end
  end

  test "binds the origin, journal revision, attempt, and retained capture", %{build: build} do
    changes = [
      origin: "http://127.0.0.1:1",
      journal_revision: 3,
      attempt: 2,
      native_binding_sha256: String.duplicate("8", 64)
    ]

    for {field, value} <- changes do
      other = struct!(build, [{field, value}])

      assert {:error, :build_binding_mismatch} = Attestation.verify(@envelope, other, @spki),
             inspect(field)
    end
  end

  test "binds each retained artifact length and digest", %{build: build} do
    for {ref, index} <- Enum.with_index(build.artifacts),
        change <- [sha256: String.duplicate("a", 64), size_bytes: ref.size_bytes + 1] do
      artifacts = List.update_at(build.artifacts, index, &struct!(&1, [change]))
      other = %{build | artifacts: artifacts}
      assert {:error, :build_binding_mismatch} = Attestation.verify(@envelope, other, @spki)
    end
  end

  test "requires a completed iOS build with the exact native artifact kinds", %{build: build} do
    [app, symbols, inventory] = build.artifacts

    for invalid <- [
          Map.from_struct(build),
          %{build | selection: %{build.selection | platform: "android"}},
          %{build | state: :running},
          %{build | worker_completion_pending: true},
          %{build | journal_revision: 1},
          %{build | attempt: 0},
          %{build | origin: build.origin <> "/"},
          %{build | artifacts: [app, app, inventory]},
          %{build | artifacts: [app, symbols]},
          %{build | artifacts: [app, symbols, %{inventory | size_bytes: 8 * 1024 * 1024 + 1}]}
        ] do
      assert {:error, :invalid_expected_build} = Attestation.verify(@envelope, invalid, @spki)
    end
  end

  test "authenticates the raw statement using the v1 domain", %{build: build} do
    invalid_signature = replace_signature(@envelope, Base.encode64(:binary.copy(<<0>>, 64)))
    wrong_domain = replace_signature(@envelope, @other_domain_signature)

    alternate_spelling =
      String.replace(@envelope, "local-org", "local\\u002dorg", global: false)

    for invalid <- [invalid_signature, wrong_domain, alternate_spelling] do
      assert {:error, :invalid_signature} = Attestation.verify(invalid, build, @spki)
    end

    # The separately signed alternate has the same decoded values, but the
    # retained statement must also match the bytes Go reconstructs.
    correctly_signed = replace_signature(alternate_spelling, @alternate_signature)
    assert {:error, :build_binding_mismatch} = Attestation.verify(correctly_signed, build, @spki)
  end

  test "rejects malformed, ambiguous and oversized envelopes", %{build: build} do
    for invalid <- [
          nil,
          "",
          "{}",
          "[" <> @envelope <> "]",
          @envelope <> "\n",
          " " <> @envelope,
          @envelope <> String.duplicate(" ", 16_384),
          String.replace(@envelope, "local-org", <<255>>, global: false),
          String.replace(@envelope, ~s("statement":), ~s("statement":{},"statement":),
            global: false
          ),
          String.replace(@envelope, ~s("origin":), ~S("orig\u0069n":"","origin":), global: false),
          String.replace(@envelope, ~s("statement":), ~S("statem\u0065nt":), global: false),
          String.replace(@envelope, ~s("attempt":1), ~s("attempt":1.0), global: false),
          replace_signature(@envelope, "invalid"),
          String.replace(@envelope, ~s(=="}), ~s("}), global: false),
          ~s({"statement":#{String.duplicate("[", 17)}0#{String.duplicate("]", 17)},"signature":""})
        ] do
      assert {:error, :invalid_envelope} = Attestation.verify(invalid, build, @spki)
    end
  end

  defp sha256(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  defp replace_signature(envelope, signature) do
    [prefix, _] = :binary.split(envelope, ~s(,"signature":))
    prefix <> ~s(,"signature":"#{signature}"})
  end
end
