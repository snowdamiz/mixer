defmodule MixerHosted.Builds.NativeDevelopmentAttestation do
  @moduledoc """
  Verifies the detached iOS simulator development envelope emitted by
  mixer-native-attest. Success reports evidence bound to one completed build.
  """

  alias MixerHosted.Builds.Lifecycle
  alias MixerHosted.CustomerBuilds.Selection
  alias MixerHosted.Protocol.ArtifactJSON

  @legacy_profile "mixer.native-build.ios-simulator.development.v1"
  @completion_profile "mixer.native-build.ios-simulator.development.v2"
  @envelope_limit 16_384
  @inventory_limit 8 * 1024 * 1024
  @max_int64 9_223_372_036_854_775_807

  # RFC 8410 Ed25519 SubjectPublicKeyInfo, with absent algorithm parameters.
  @ed25519_spki_prefix <<0x30, 0x2A, 0x30, 0x05, 0x06, 0x03, 0x2B, 0x65, 0x70, 0x03, 0x21, 0x00>>

  defmodule ExpectedBuild do
    @moduledoc """
    Server-authorized snapshot of the exact completed build.

    Use the configured origin, selection and completion from the current
    committed journal, and artifact references and shared capture binding
    established from retained native products. Obtain all fields independently
    of the envelope. The caller owns authority, retained-byte checks, and
    keeping this snapshot current through any later attachment. Set
    `worker_operation_id` for completion-bound verification. A nil operation
    verifies only historical v1 evidence and cannot authorize an attachment.
    """

    alias MixerHosted.Builds.Lifecycle.ArtifactRef

    @enforce_keys [
      :origin,
      :selection,
      :state,
      :worker_completion_pending,
      :journal_revision,
      :attempt,
      :native_binding_sha256,
      :artifacts
    ]
    defstruct @enforce_keys ++ [worker_operation_id: nil]

    @type t :: %__MODULE__{
            origin: String.t(),
            selection: %Selection{},
            state: :native_succeeded,
            worker_completion_pending: false,
            journal_revision: pos_integer(),
            attempt: pos_integer(),
            worker_operation_id: String.t() | nil,
            native_binding_sha256: String.t(),
            artifacts: [%ArtifactRef{}]
          }
  end

  @type rejection ::
          :invalid_expected_build
          | :invalid_trusted_key
          | :invalid_envelope
          | :invalid_signature
          | :build_binding_mismatch

  @doc """
  Verifies the retained envelope under the independently enrolled canonical
  Ed25519 public SPKI DER. Pass the server's current authorized build explicitly.
  """
  @spec verify(binary(), ExpectedBuild.t(), <<_::352>>) :: :ok | {:error, rejection()}
  def verify(envelope, expected_build, enrolled_public_spki_der) do
    with {:ok, expected} <- checked_build(expected_build),
         {:ok, public_key} <- ed25519_public_key(enrolled_public_spki_der),
         {:ok, statement, signature} <- decode_envelope(envelope),
         profile = profile(expected),
         :ok <- verify_signature(profile, statement, signature, public_key) do
      key_id = Base.encode16(:crypto.hash(:sha256, enrolled_public_spki_der), case: :lower)

      if statement == expected_statement(expected, profile, key_id),
        do: :ok,
        else: {:error, :build_binding_mismatch}
    end
  end

  @doc false
  def valid_public_spki?(value), do: match?({:ok, _}, ed25519_public_key(value))

  defp checked_build(
         %ExpectedBuild{
           origin: origin,
           selection: %Selection{platform: "ios"} = selection,
           state: :native_succeeded,
           worker_completion_pending: false,
           journal_revision: revision,
           attempt: attempt,
           worker_operation_id: operation,
           native_binding_sha256: binding,
           artifacts: [_, _, %Lifecycle.ArtifactRef{size_bytes: inventory_size}] = artifacts
         } = expected
       )
       when is_integer(revision) and revision in 2..@max_int64 and
              is_integer(attempt) and attempt in 1..@max_int64 do
    with true <- loopback_origin?(origin),
         {:ok, _} <- Selection.new(selection),
         true <- is_nil(operation) or Selection.digest?(operation),
         true <- Selection.digest?(binding),
         true <- Lifecycle.native_artifacts?(artifacts),
         true <- inventory_size <= @inventory_limit do
      {:ok, expected}
    else
      _ -> {:error, :invalid_expected_build}
    end
  end

  defp checked_build(_), do: {:error, :invalid_expected_build}

  defp loopback_origin?(<<"http://127.0.0.1:", port::binary>>)
       when byte_size(port) in 1..@envelope_limit do
    with true <- Regex.match?(~r/\A[0-9]+\z/, port),
         digits when byte_size(digits) in 1..5 <- String.trim_leading(port, "0") do
      String.to_integer(digits) <= 65_535
    else
      _ -> false
    end
  end

  defp loopback_origin?(_), do: false

  defp ed25519_public_key(<<@ed25519_spki_prefix, key::binary-size(32)>>), do: {:ok, key}
  defp ed25519_public_key(_), do: {:error, :invalid_trusted_key}

  defp decode_envelope(bytes) do
    with {:ok, %{"statement" => %{}, "signature" => encoded}, [{_, _, start, size}, _], _} <-
           ArtifactJSON.decode(bytes, @envelope_limit),
         <<_::binary-size(88)>> <- encoded,
         {:ok, <<_::binary-size(64)>> = signature} <- Base.decode64(encoded),
         ^encoded <- Base.encode64(signature),
         statement = binary_part(bytes, start, size),
         ^bytes <- ~s({"statement":#{statement},"signature":"#{encoded}"}) do
      {:ok, statement, signature}
    else
      _ -> {:error, :invalid_envelope}
    end
  end

  defp profile(%ExpectedBuild{worker_operation_id: nil}), do: @legacy_profile
  defp profile(%ExpectedBuild{}), do: @completion_profile

  defp verify_signature(profile, statement, signature, public_key) do
    message = profile <> <<0>> <> statement

    if :crypto.verify(:eddsa, :none, message, signature, [public_key, :ed25519]),
      do: :ok,
      else: {:error, :invalid_signature}
  end

  # Go marshals structs in declaration order. The validated ASCII values in
  # this profile need no JSON escapes in either encoder.
  defp expected_statement(expected, profile, key_id) do
    s = expected.selection

    Jason.OrderedObject.new(
      profile: profile,
      origin: expected.origin,
      keyId: key_id,
      selection:
        Jason.OrderedObject.new(
          organizationId: s.organization_id,
          projectId: s.project_id,
          applicationId: s.application_id,
          buildId: s.build_id,
          platform: s.platform,
          sourceSha256: s.source_sha256,
          toolchainLockSha256: s.toolchain_lock_sha256,
          buildDefinitionSha256: s.build_definition_sha256
        ),
      provenance: provenance(expected),
      subjects:
        Enum.map(expected.artifacts, fn artifact ->
          Jason.OrderedObject.new(
            kind: Atom.to_string(artifact.kind),
            sha256: artifact.sha256,
            sizeBytes: artifact.size_bytes
          )
        end)
    )
    |> Jason.encode!()
  end

  defp provenance(expected) do
    fields = [
      journalRevision: expected.journal_revision,
      attempt: expected.attempt,
      nativeBindingSha256: expected.native_binding_sha256
    ]

    fields =
      case expected.worker_operation_id do
        nil -> fields
        operation -> fields ++ [workerOperationId: operation]
      end

    Jason.OrderedObject.new(fields)
  end
end
