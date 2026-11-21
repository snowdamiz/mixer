defmodule MixerHosted.Test.StagePromotionSigningFixture do
  @moduledoc false

  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.ArtifactCBOR
  alias MixerHosted.Releases.EnvironmentPromotion.Command.{Evidence, SourcePublication}
  alias MixerHosted.Releases.EnvironmentPromotion.Direction.Enrollment
  alias MixerHosted.Releases.Target

  @vector Path.expand("../../../services/protocol/testdata/signed-release-v3.json", __DIR__)

  def vector, do: @vector |> File.read!() |> Jason.decode!()

  # These synthetic fingerprints represent four separately enrolled hosts.
  # Ephemeral signing keys are confined to the test processes.
  def variant(vector, platform, environment, channel, sequence) do
    scope = %{vector["host"]["scope"] | "platform" => platform, "environment" => environment}
    runtime = digest(platform <> ":" <> environment)
    host = %{vector["host"] | "scope" => scope, "runtime" => runtime}
    [artifact_root, assignment_root] = vector["roots"]
    {artifact_root, artifact_key} = test_root(artifact_root, scope)
    {assignment_root, assignment_key} = test_root(assignment_root, scope)
    time = vector["verification_time_unix"] - sequence

    manifest = %{
      vector["signed_manifest"]["manifest"]
      | "scope" => scope,
        "runtime" => runtime,
        "key_id" => artifact_root["key_id"],
        "created_at_unix" => time
    }

    assignment = %{
      vector["signed_assignment"]["assignment"]
      | "scope" => scope,
        "runtime" => runtime,
        "channel" => channel,
        "sequence" => sequence,
        "key_id" => assignment_root["key_id"],
        "created_at_unix" => time
    }

    %{
      enrollment: enroll(host, channel, [artifact_root, assignment_root]),
      manifest: manifest,
      assignment: assignment,
      artifact_key: artifact_key,
      assignment_key: assignment_key
    }
    |> with_payload(Base.decode64!(vector["payload"]) <> platform)
  end

  def enroll(host, channel, roots) do
    scope = host["scope"]

    %Enrollment{
      target: %Target{
        scope: %Scope{
          organization_id: scope["organization"],
          project_id: scope["project"],
          application_id: scope["app"],
          environment_id: scope["environment"]
        },
        platform: scope["platform"],
        runtime_sha256: host["runtime"],
        channel: channel
      },
      host: host,
      roots: roots
    }
  end

  defp test_root(template, scope) do
    {public, private} = :crypto.generate_key(:eddsa, :ed25519)
    id = Enum.join([scope["environment"], scope["platform"], template["key_id"]], ".")
    {%{template | "scope" => scope, "key_id" => id, "public_key" => public}, private}
  end

  def with_payload(variant, payload) do
    size = byte_size(payload)

    manifest = %{
      variant.manifest
      | "payload_sha256" => digest(payload),
        "compressed_bytes" => size,
        "expanded_bytes" => size
    }

    variant |> Map.put(:payload, payload) |> Map.put(:manifest, manifest)
  end

  def publication(variant) do
    %SourcePublication{
      sequence: variant.assignment["sequence"],
      artifact_sha256: digest(cbor(variant.manifest)),
      evidence: evidence(variant)
    }
  end

  def evidence(variant) do
    artifact_digest = digest(cbor(variant.manifest))

    assignment = %{
      variant.assignment
      | "artifact_sha256" => artifact_digest,
        "release_id" => variant.manifest["release_id"],
        "runtime" => variant.manifest["runtime"]
    }

    %Evidence{
      signed_manifest_bytes:
        sign("manifest", "mixer.artifact.v3\0", variant.manifest, variant.artifact_key),
      signed_assignment_bytes:
        sign("assignment", "mixer.assignment.v3\0", assignment, variant.assignment_key),
      payload: variant.payload
    }
  end

  defp sign(field, domain, value, private) do
    signature = :crypto.sign(:eddsa, :none, domain <> cbor(value), [private, :ed25519])
    " \n" <> Jason.encode!(%{field => value, "signature" => Base.encode64(signature)}) <> "\t "
  end

  def digest(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  defp cbor(value) do
    {:ok, bytes} = ArtifactCBOR.encode(value)
    bytes
  end
end
