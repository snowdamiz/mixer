defmodule MixerHosted.Builds.RetainedNativeArtifacts do
  @moduledoc """
  Read-only access to the opt-in worker's retained output tree. The root is
  operator-configured and the worker and Phoenix run under the same trusted
  local account. The operation ID and descriptor come from a verified worker
  observation or the authorized, committed build journal.
  """
  alias MixerHosted.Builds.Lifecycle
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  @kinds Enum.map(Lifecycle.native_artifact_kinds(), &Atom.to_string/1)
  @max_bytes Lifecycle.native_artifact_max_bytes()
  @chunk_bytes 64 * 1024

  def kinds, do: @kinds

  def verify(operation_id, artifacts) do
    if Enum.all?(artifacts, &verified?(operation_id, &1)),
      do: :ok,
      else: {:error, :uncertain}
  end

  def read(operation_id, artifact) do
    with {:ok, path, size, digest} <- artifact_path(operation_id, artifact),
         {:ok, {:ok, bytes}} when byte_size(bytes) == size <-
           File.open(path, [:read, :binary, :raw], &:file.read(&1, size + 1)),
         ^digest <- :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower) do
      {:ok, bytes}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp verified?(operation_id, artifact) do
    with {:ok, path, size, digest} <- artifact_path(operation_id, artifact),
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

  defp artifact_path(operation_id, %ArtifactRef{sha256: digest, size_bytes: size})
       when is_integer(size) and size in 1..@max_bytes do
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

  defp artifact_path(_, _), do: {:error, :storage_unavailable}

  defp directory?(path), do: match?({:ok, %File.Stat{type: :directory}}, File.lstat(path))

  defp hex?(value),
    do: is_binary(value) and byte_size(value) == 64 and Regex.match?(~r/\A[0-9a-f]+\z/, value)
end
