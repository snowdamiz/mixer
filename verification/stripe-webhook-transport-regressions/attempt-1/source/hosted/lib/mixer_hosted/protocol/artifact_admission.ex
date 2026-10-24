defmodule MixerHosted.Protocol.ArtifactAdmission do
  @moduledoc """
  Bounded v3 artifact storage admission against explicit current trust and host
  policy. Checked data confers no tenant permission, publication, validation,
  compiler eligibility or execution authority. Roots contain raw public bytes.
  """
  alias MixerHosted.Protocol.{ArtifactCBOR, ArtifactJSON, ArtifactV3Policy}
  @envelope_limit 6_291_456
  @signed_limit 65_536
  @payload_limit 4_194_304
  @domain "mixer.artifact.v3\0"

  defmodule Checked do
    @moduledoc "Immutable retained data; constructing this struct is not proof of admission."
    @enforce_keys [
      :envelope_bytes,
      :signed_manifest_bytes,
      :manifest,
      :canonical_manifest_cbor,
      :signature,
      :payload,
      :manifest_sha256,
      :payload_sha256,
      :target
    ]
    defstruct @enforce_keys
  end

  def admit(bytes, host, roots, now)
      when is_binary(bytes) and byte_size(bytes) <= @envelope_limit do
    with {:ok, spans, _} <- ArtifactJSON.preflight(bytes, @envelope_limit),
         {:ok, signed_bytes} <- signed_span(bytes, spans),
         {:ok, envelope, _, _} <- ArtifactJSON.decode(bytes, @envelope_limit),
         true <- ArtifactV3Policy.exact?(envelope, ~w(signed_manifest payload)),
         {:ok, payload} <- base64(envelope["payload"], 1, @payload_limit),
         {:ok, data} <- admit_signed(signed_bytes, payload, host, roots, now) do
      {:ok, struct!(Checked, Map.put(data, :envelope_bytes, bytes))}
    else
      false -> {:error, :envelope_shape}
      {:error, reason} -> {:error, reason}
      _ -> {:error, :envelope_shape}
    end
  end

  def admit(_, _, _, _), do: {:error, :envelope_limit}

  @doc "Checks an exact standalone signed document and raw payload; returns data, never an upload Checked record."
  def admit_signed(signed_bytes, payload, host, roots, now)
      when is_binary(signed_bytes) and byte_size(signed_bytes) <= @signed_limit and
             is_binary(payload) and byte_size(payload) in 1..@payload_limit do
    with true <- ArtifactV3Policy.uint?(now),
         {:ok, signed, _, _} <- ArtifactJSON.decode(signed_bytes, @signed_limit),
         true <- ArtifactV3Policy.exact?(signed, ~w(manifest signature)),
         manifest = signed["manifest"],
         true <- ArtifactV3Policy.manifest?(manifest),
         true <- ArtifactV3Policy.compatible?(manifest, host),
         {:ok, public_key} <-
           ArtifactV3Policy.authority(roots, manifest["key_id"], manifest["scope"], now),
         {:ok, signature} <- base64(signed["signature"], 64, 64),
         {:ok, cbor} <- ArtifactCBOR.encode(manifest),
         true <- :crypto.verify(:eddsa, :none, @domain <> cbor, signature, [public_key, :ed25519]),
         payload_hash = hash(payload),
         true <-
           byte_size(payload) == manifest["compressed_bytes"] and
             payload_hash == manifest["payload_sha256"] do
      digest = hash(cbor)

      {:ok,
       %{
         signed_manifest_bytes: signed_bytes,
         manifest: manifest,
         canonical_manifest_cbor: cbor,
         signature: signature,
         payload: payload,
         manifest_sha256: digest,
         payload_sha256: payload_hash,
         target:
           Map.merge(manifest["scope"], %{
             "runtime" => manifest["runtime"],
             "manifest_sha256" => digest
           })
       }}
    else
      _ -> {:error, :artifact_rejected}
    end
  end

  def admit_signed(_, _, _, _, _), do: {:error, :document_or_payload_limit}

  @doc "Reconstructs exact retained bytes under current policy and rejects any changed field."
  def recheck(%Checked{envelope_bytes: bytes} = checked, host, roots, now) do
    case admit(bytes, host, roots, now) do
      {:ok, ^checked} -> {:ok, checked}
      _ -> {:error, :recheck_rejected}
    end
  end

  def recheck(_, _, _, _), do: {:error, :recheck_rejected}

  defp signed_span(bytes, spans) do
    Enum.reduce_while(spans, {:error, :envelope_shape}, fn {key_start, key_size, start, size},
                                                           result ->
      case Jason.decode(binary_part(bytes, key_start, key_size)) do
        {:ok, "signed_manifest"} when size <= @signed_limit ->
          {:halt, {:ok, :binary.copy(binary_part(bytes, start, size))}}

        {:ok, "signed_manifest"} ->
          {:halt, {:error, :document_limit}}

        _ ->
          {:cont, result}
      end
    end)
  end

  defp base64(text, minimum, maximum) when is_binary(text) do
    size = byte_size(text)
    # Encoded bound and exact tail arithmetic precede decoding allocation.
    if size > 0 and rem(size, 4) == 0 and size <= 4 * div(maximum + 2, 3) do
      padding =
        cond do
          :binary.at(text, size - 2) == ?= and :binary.at(text, size - 1) == ?= -> 2
          :binary.at(text, size - 1) == ?= -> 1
          true -> 0
        end

      decoded_size = div(size, 4) * 3 - padding

      if decoded_size >= minimum and decoded_size <= maximum and
           alphabet?(text, size - padding, 0) and tail?(text, size - padding, padding) do
        case Base.decode64(text, padding: true) do
          {:ok, decoded} when byte_size(decoded) == decoded_size ->
            if Base.encode64(decoded) == text, do: {:ok, decoded}, else: {:error, :base64}

          _ ->
            {:error, :base64}
        end
      else
        {:error, :base64}
      end
    else
      {:error, :base64}
    end
  end

  defp base64(_, _, _), do: {:error, :base64}
  defp alphabet?(_, finish, finish), do: true

  defp alphabet?(text, finish, offset) do
    c = :binary.at(text, offset)

    (c in ?A..?Z or c in ?a..?z or c in ?0..?9 or c in [?+, ?/]) and
      alphabet?(text, finish, offset + 1)
  end

  defp tail?(_, _, 0), do: true

  defp tail?(text, finish, padding) do
    c = :binary.at(text, finish - 1)

    n =
      cond do
        c in ?A..?Z -> c - ?A
        c in ?a..?z -> c - ?a + 26
        c in ?0..?9 -> c - ?0 + 52
        c == ?+ -> 62
        c == ?/ -> 63
      end

    rem(n, if(padding == 2, do: 16, else: 4)) == 0
  end

  defp hash(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
end
