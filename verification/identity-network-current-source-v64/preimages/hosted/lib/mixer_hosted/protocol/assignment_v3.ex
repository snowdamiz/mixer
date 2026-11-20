defmodule MixerHosted.Protocol.AssignmentV3 do
  @moduledoc """
  Decodes and verifies standalone signed v3 assignments for a release ledger.

  Both entry points preserve the exact signed JSON document. Signatures cover
  canonical CBOR of the inner assignment with the v3 assignment domain.
  """

  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, ArtifactJSON, ArtifactV3Policy}

  @document_limit 65_536
  @domain "mixer.assignment.v3\0"
  @assignment_fields ~w(schema scope channel cohort rollout_basis_points sequence release_id artifact_sha256 runtime key_id created_at_unix)

  defmodule Signed do
    @moduledoc "Decoded signed data. The struct itself carries no proof of verification."
    @enforce_keys [:signed_assignment_bytes, :assignment, :canonical_assignment_cbor, :signature]
    defstruct @enforce_keys

    @type t :: %__MODULE__{
            signed_assignment_bytes: binary(),
            assignment: %{String.t() => ArtifactCBOR.value()},
            canonical_assignment_cbor: binary(),
            signature: <<_::512>>
          }
  end

  @type uint64 :: 0..18_446_744_073_709_551_615
  @type artifact :: %{
          required(:signed_manifest_bytes) => binary(),
          required(:payload) => binary()
        }
  @type context :: %{
          required(:channel) => String.t(),
          required(:last_sequence) => uint64(),
          required(:now) => uint64()
        }

  @doc "Checks the closed v3 wire shape and retains raw JSON, canonical CBOR and signature bytes."
  @spec decode_signed(binary()) :: {:ok, Signed.t()} | {:error, atom()}
  def decode_signed(bytes) do
    with {:ok, envelope, _, _} <- ArtifactJSON.decode(bytes, @document_limit),
         true <- ArtifactV3Policy.exact?(envelope, ~w(assignment signature)),
         assignment = envelope["assignment"],
         true <- valid_assignment?(assignment),
         {:ok, signature} <- decode_signature(envelope["signature"]),
         {:ok, cbor} <- ArtifactCBOR.encode(assignment) do
      {:ok,
       %Signed{
         signed_assignment_bytes: :binary.copy(bytes),
         assignment: assignment,
         canonical_assignment_cbor: cbor,
         signature: signature
       }}
    else
      false -> {:error, :invalid_assignment}
      {:error, _} = error -> error
    end
  end

  @doc """
  Verifies assignment bytes against a signed manifest and raw payload.

  Pass a trusted installed host, configured roots with raw Ed25519 public
  keys, and the expected channel, current Unix time in seconds, and prior
  sequence for that scope, runtime and channel. Use zero for an empty head.
  The caller owns the atomic check and advance of the persisted sequence.

  Current signing-root validity uses inclusive start and exclusive expiry.
  The signed creation time is audit data. Installation cohort selection
  happens at delivery, so a signed zero-rollout assignment can halt a channel.
  """
  @spec verify(binary(), artifact(), [map()], map(), context()) ::
          {:ok, Signed.t()} | {:error, atom()}
  def verify(
        bytes,
        %{signed_manifest_bytes: manifest_bytes, payload: payload},
        roots,
        host,
        %{channel: channel, last_sequence: last, now: now}
      ) do
    with :ok <- check_context(channel, last, now),
         {:ok, signed} <- decode_signed(bytes),
         :ok <- check_head(signed.assignment, channel, last),
         :ok <- authenticate(signed, roots, now),
         {:ok, artifact} <-
           ArtifactAdmission.admit_signed(manifest_bytes, payload, host, roots, now),
         true <- binds_artifact?(signed.assignment, artifact) do
      {:ok, signed}
    else
      false -> {:error, :assignment_binding}
      {:error, _} = error -> error
    end
  end

  def verify(_, _, _, _, _), do: {:error, :invalid_context}

  defp valid_assignment?(assignment) do
    ArtifactV3Policy.exact?(assignment, @assignment_fields) and
      assignment["schema"] === 3 and
      ArtifactV3Policy.scope?(assignment["scope"]) and
      assignment["cohort"] == "sha256-v1" and
      ArtifactV3Policy.uint?(assignment["rollout_basis_points"]) and
      assignment["rollout_basis_points"] <= 10_000 and
      Enum.all?(~w(sequence created_at_unix), fn field ->
        ArtifactV3Policy.uint?(assignment[field]) and assignment[field] > 0
      end) and
      Enum.all?(~w(channel release_id key_id), &ArtifactV3Policy.id?(assignment[&1])) and
      Enum.all?(~w(artifact_sha256 runtime), &ArtifactV3Policy.digest?(assignment[&1]))
  end

  defp decode_signature(text) when is_binary(text) and byte_size(text) == 88 do
    with {:ok, <<_::512>> = signature} <- Base.decode64(text),
         ^text <- Base.encode64(signature) do
      {:ok, signature}
    else
      _ -> {:error, :signature_encoding}
    end
  end

  defp decode_signature(_), do: {:error, :signature_encoding}

  defp check_context(channel, last, now) do
    if ArtifactV3Policy.id?(channel) and ArtifactV3Policy.uint?(last) and
         ArtifactV3Policy.uint?(now),
       do: :ok,
       else: {:error, :invalid_context}
  end

  defp check_head(%{"channel" => channel, "sequence" => sequence}, channel, last) do
    if sequence > last, do: :ok, else: {:error, :assignment_replay}
  end

  defp check_head(_, _, _), do: {:error, :assignment_binding}

  defp authenticate(signed, roots, now) do
    %{"key_id" => key_id, "scope" => scope} = signed.assignment

    with {:ok, key} <- assignment_key(roots, key_id, scope, now),
         true <-
           :crypto.verify(
             :eddsa,
             :none,
             @domain <> signed.canonical_assignment_cbor,
             signed.signature,
             [key, :ed25519]
           ) do
      :ok
    else
      false -> {:error, :assignment_signature}
      {:error, _} = error -> error
    end
  end

  defp assignment_key(roots, key_id, scope, now) do
    with true <- ArtifactV3Policy.roots?(roots),
         %{
           "scope" => ^scope,
           "assignment" => true,
           "revoked" => false,
           "not_before_unix" => start,
           "not_after_unix" => expiry,
           "public_key" => key
         }
         when start <= now and (expiry == 0 or now < expiry) <-
           Enum.find(roots, &(&1["key_id"] == key_id)) do
      {:ok, key}
    else
      _ -> {:error, :root_policy}
    end
  end

  defp binds_artifact?(assignment, %{manifest: manifest, manifest_sha256: digest}) do
    assignment["artifact_sha256"] == digest and
      Enum.all?(~w(scope runtime release_id), &(assignment[&1] == manifest[&1]))
  end
end
