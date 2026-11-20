defmodule MixerHosted.Test.FieldLogReleasePacket do
  @moduledoc false
  import ExUnit.Assertions
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, AssignmentV3}

  @scope %{
    "organization" => "mixer-local",
    "project" => "fieldlog",
    "app" => "fieldlog",
    "environment" => "development",
    "platform" => "android"
  }
  @installation "1f0d30b5-6e05-4e49-b928-a40bc95cb7ce"
  @variants ~w(baseline reviewed)
  @layout [:publish, :publish, :rollback]

  def read!(delivery) do
    assert Path.basename(delivery) == "delivery-android"
    assert %File.Stat{type: :directory} = File.lstat!(delivery)
    assert %File.Stat{type: :directory} = File.lstat!(Path.join(delivery, "Installed"))

    pins =
      delivery
      |> Path.dirname()
      |> Path.join("materials.sha256.json")
      |> read_regular!(65_536)
      |> Jason.decode!()

    read = fn name, limit ->
      bytes = read_regular!(Path.join(delivery, name), limit)
      assert pins["delivery-android/" <> name] == sha(bytes), "Handoff hash differs: " <> name
      bytes
    end

    host = read.("host.json", 65_536) |> Jason.decode!()
    roots = read.("Installed/roots.json", 65_536) |> Jason.decode!()
    assert host["scope"] == @scope

    [baseline, reviewed] =
      for variant <- @variants do
        {read.("#{variant}.manifest.json", 65_536), read.("#{variant}.wasm", 4_194_304)}
      end

    phases =
      [baseline, reviewed, baseline]
      |> Enum.zip(@layout)
      |> Enum.with_index(1)
      |> Enum.map(fn {{{manifest, payload}, action}, sequence} ->
        %{
          manifest: manifest,
          payload: payload,
          action: action,
          signed: read.("sequence-#{sequence}.assignment.json", 65_536)
        }
      end)

    {%{"host" => host, "roots" => roots, "installation" => @installation}, phases}
  end

  def admit!(phases, %{host: host, roots: roots}) do
    now = System.system_time(:second)

    phases =
      phases
      |> Enum.with_index(1)
      |> Enum.map(fn {phase, sequence} ->
        # The production JSON span preserves the signed object from its opening to closing brace.
        for bytes <- [phase.manifest, phase.signed] do
          assert String.starts_with?(bytes, "{") and String.ends_with?(bytes, "}")
        end

        assert {:ok, artifact} =
                 ArtifactAdmission.admit_signed(phase.manifest, phase.payload, host, roots, now)

        assert {:ok, signed} =
                 AssignmentV3.verify(phase.signed, artifact, roots, host, %{
                   channel: "beta",
                   last_sequence: sequence - 1,
                   now: now
                 })

        assert signed.assignment["sequence"] == sequence
        assert signed.assignment["rollout_basis_points"] == 10_000

        envelope =
          ~s({"signed_manifest":) <>
            phase.manifest <>
            ~s(,"payload":") <> Base.encode64(phase.payload) <> ~s("})

        Map.merge(phase, %{
          assignment: signed.assignment,
          digest: artifact.manifest_sha256,
          payload_sha: artifact.payload_sha256,
          envelope: envelope
        })
      end)

    assert [baseline, reviewed, rollback] = phases
    assert baseline.digest != reviewed.digest and baseline.payload_sha != reviewed.payload_sha
    assert rollback.digest == baseline.digest
    phases
  end

  # The host control exercises the private handoff format using fresh test-only
  # material. Real replay reads the operator's existing signed files unchanged.
  def synthetic!(scratch, vector) do
    delivery = Path.join(scratch, "delivery-android")
    File.mkdir_p!(Path.join(delivery, "Installed"))
    {public, private} = :crypto.generate_key(:eddsa, :ed25519)
    host = %{vector["host"] | "scope" => @scope, "max_payload_bytes" => 10_540}

    root = %{
      hd(vector["roots"])
      | "scope" => @scope,
        "public_key" => Base.encode64(public),
        "assignment" => true
    }

    template = %{
      vector["signed_manifest"]["manifest"]
      | "scope" => @scope,
        "key_id" => root["key_id"]
    }

    bytes = Base.decode64!(vector["payload"])
    prefix = bytes <> :binary.copy(<<0>>, 10_539 - byte_size(bytes))

    {files, digests} =
      for {variant, wasm} <- Enum.zip(@variants, [prefix <> <<0>>, prefix <> <<1>>]),
          reduce: {%{}, %{}} do
        {files, digests} ->
          manifest = %{
            template
            | "release_id" => "fieldlog-control-" <> variant,
              "payload_sha256" => sha(wasm),
              "compressed_bytes" => byte_size(wasm),
              "expanded_bytes" => byte_size(wasm)
          }

          {:ok, cbor} = ArtifactCBOR.encode(manifest)

          files =
            Map.merge(files, %{
              "#{variant}.manifest.json" => sign("manifest", "artifact", manifest, private),
              "#{variant}.wasm" => wasm
            })

          {files, Map.put(digests, variant, {sha(cbor), manifest["release_id"]})}
      end

    files =
      ["baseline", "reviewed", "baseline"]
      |> Enum.with_index(1)
      |> Enum.reduce(files, fn {variant, sequence}, files ->
        {digest, release_id} = digests[variant]

        body = %{
          vector["signed_assignment"]["assignment"]
          | "scope" => @scope,
            "sequence" => sequence,
            "key_id" => root["key_id"],
            "release_id" => release_id,
            "artifact_sha256" => digest
        }

        Map.put(
          files,
          "sequence-#{sequence}.assignment.json",
          sign("assignment", "assignment", body, private)
        )
      end)
      |> Map.merge(%{
        "host.json" => Jason.encode!(host),
        "Installed/roots.json" => Jason.encode!([root])
      })

    pins =
      Map.new(files, fn {name, bytes} ->
        File.write!(Path.join(delivery, name), bytes, [:exclusive])
        {"delivery-android/" <> name, sha(bytes)}
      end)

    File.write!(Path.join(scratch, "materials.sha256.json"), Jason.encode!(pins), [:exclusive])
    delivery
  end

  defp sign(field, domain, body, private) do
    {:ok, cbor} = ArtifactCBOR.encode(body)
    signature = :crypto.sign(:eddsa, :none, "mixer.#{domain}.v3\0" <> cbor, [private, :ed25519])
    Jason.encode!(%{field => body, "signature" => Base.encode64(signature)})
  end

  defp read_regular!(path, limit) do
    assert %File.Stat{type: :regular, size: size} = File.lstat!(path)
    assert size in 1..limit, "Handoff input exceeds fixture bounds: " <> path
    bytes = File.read!(path)
    assert byte_size(bytes) == size
    bytes
  end

  defp sha(bytes), do: :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)
end
