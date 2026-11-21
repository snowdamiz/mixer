defmodule MixerHosted.Builds.RetainedNativeArtifacts do
  @moduledoc """
  Read-only access to the opt-in worker's retained output tree. The root is
  operator-configured and the worker and Phoenix run under the same trusted
  local account. The operation ID and descriptor come from a verified worker
  observation or the authorized, committed build journal.
  """
  alias MixerHosted.Builds.Lifecycle
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  @native_kinds Lifecycle.native_artifact_kinds()
  @kinds Enum.map(@native_kinds, &Atom.to_string/1)
  @chunk_bytes 64 * 1024
  @ios_archive_magic "MXNATIVE1\n"
  @ios_metadata_limit 8 * 1024 * 1024

  def kinds, do: @kinds

  def verify(operation_id, artifacts), do: verify(operation_id, :ios, artifacts)

  def verify(operation_id, platform, artifacts) do
    if Lifecycle.native_artifacts?(platform, artifacts) and
         Enum.all?(artifacts, &verified?(operation_id, platform, &1)),
       do: :ok,
       else: {:error, :uncertain}
  end

  @doc """
  Establishes the shared capture digest for the exact retained iOS simulator
  development products of one completed operation.

  The caller supplies the operation ID and ordered artifact references from the
  same authorized, committed completion. Pass the returned digest and those
  references to `NativeDevelopmentAttestation.ExpectedBuild`. The caller owns
  authorization and keeping the completion current through any attachment.
  """
  @spec verify_ios_development(binary(), [%ArtifactRef{}]) ::
          {:ok, String.t()} | {:error, :invalid_retained_products}
  def verify_ios_development(operation_id, artifacts) do
    with true <- Lifecycle.native_artifacts?(:ios, artifacts),
         [app, symbols, inventory] <- artifacts,
         true <- inventory.size_bytes <= @ios_metadata_limit,
         {:ok, binding} <- archive_binding(operation_id, app),
         {:ok, ^binding} <- archive_binding(operation_id, symbols),
         {:ok, bytes} <- read(operation_id, :ios, inventory),
         {:ok,
          %{
            "version" => 1,
            "kind" => "resource_inventory",
            "bindingSHA256" => ^binding,
            "parentApp" => parent_app,
            "parentSymbols" => parent_symbols
          }} <- metadata(bytes),
         true <- parent_ref?(parent_app, app) and parent_ref?(parent_symbols, symbols) do
      {:ok, binding}
    else
      _ -> {:error, :invalid_retained_products}
    end
  end

  def read(operation_id, artifact), do: read(operation_id, :ios, artifact)

  def read(operation_id, platform, %ArtifactRef{kind: kind} = artifact)
      when platform in [:ios, :android] and kind in @native_kinds do
    cap = Lifecycle.native_artifact_max_bytes(platform, kind)

    with {:ok, path, size, digest} <- artifact_path(operation_id, artifact, cap),
         {:ok, {:ok, bytes}} when byte_size(bytes) == size <-
           File.open(path, [:read, :binary, :raw], &:file.read(&1, size + 1)),
         ^digest <- :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower) do
      {:ok, bytes}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  def read(_, _, _), do: {:error, :storage_unavailable}

  defp archive_binding(operation_id, artifact) do
    kind = Atom.to_string(artifact.kind)

    with {:ok, <<@ios_archive_magic, size::64, rest::binary>>} <-
           read(operation_id, :ios, artifact),
         true <- size in 1..@ios_metadata_limit and size <= byte_size(rest),
         {:ok, %{"version" => 1, "kind" => ^kind, "binding" => binding}} <-
           metadata(binary_part(rest, 0, size)),
         true <- hex?(binding) do
      {:ok, binding}
    else
      _ -> :error
    end
  end

  # Producer metadata can contain up to 10,000 entries. Decode within the byte
  # limit and require unambiguous keys in each object used for binding.
  defp metadata(bytes) do
    case Jason.decode(bytes, objects: :ordered_objects, strings: :copy) do
      {:ok, object} -> unique_object(object)
      _ -> :error
    end
  end

  defp unique_object(%Jason.OrderedObject{values: pairs}) do
    fields = Map.new(pairs)
    if map_size(fields) == length(pairs), do: {:ok, fields}, else: :error
  end

  defp unique_object(_), do: :error

  defp parent_ref?(object, artifact) do
    unique_object(object) ===
      {:ok,
       %{
         "kind" => Atom.to_string(artifact.kind),
         "sha256" => artifact.sha256,
         "sizeBytes" => artifact.size_bytes
       }}
  end

  defp verified?(operation_id, platform, artifact) do
    cap = Lifecycle.native_artifact_max_bytes(platform, artifact.kind)

    with {:ok, path, size, digest} <- artifact_path(operation_id, artifact, cap),
         {:ok, {:ok, ^digest}} <-
           File.open(
             path,
             [:read, :binary, :raw],
             &hash_file(&1, size, :crypto.hash_init(:sha256))
           ) do
      true
    else
      _ -> false
    end
  end

  defp hash_file(file, 0, hash) do
    case :file.read(file, 1) do
      :eof -> {:ok, hash |> :crypto.hash_final() |> Base.encode16(case: :lower)}
      _ -> :error
    end
  end

  defp hash_file(file, remaining, hash) do
    case :file.read(file, min(remaining, @chunk_bytes)) do
      {:ok, bytes} when byte_size(bytes) > 0 ->
        hash_file(file, remaining - byte_size(bytes), :crypto.hash_update(hash, bytes))

      _ ->
        :error
    end
  end

  defp artifact_path(operation_id, %ArtifactRef{sha256: digest, size_bytes: size}, cap)
       when is_integer(size) and size >= 1 and size <= cap do
    with true <- hex?(operation_id) and hex?(digest),
         %{retained_root: root} when is_binary(root) <-
           MixerHosted.RuntimeConfig.native_settings(),
         true <- root == Path.expand(root) and root != "/",
         {:ok, %File.Stat{type: :directory, uid: uid, mode: root_mode}} <- File.lstat(root),
         true <- Bitwise.band(root_mode, 0o077) == 0,
         true <- Enum.all?(Path.split(root) |> Enum.scan(&Path.join(&2, &1)), &directory?(&1)),
         operation = Path.join(root, operation_id),
         store = Path.join(operation, "native"),
         true <- directory?(operation) and directory?(store),
         path = Path.join(store, digest),
         {:ok, %File.Stat{type: :regular, size: ^size, uid: ^uid, links: 1, mode: mode}} <-
           File.lstat(path),
         true <- Bitwise.band(mode, 0o222) == 0 do
      {:ok, path, size, digest}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp artifact_path(_, _, _), do: {:error, :storage_unavailable}

  defp directory?(path), do: match?({:ok, %File.Stat{type: :directory}}, File.lstat(path))

  defp hex?(value),
    do: is_binary(value) and byte_size(value) == 64 and Regex.match?(~r/\A[0-9a-f]+\z/, value)
end
