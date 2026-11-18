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

  def kinds, do: @kinds

  def verify(operation_id, artifacts) do
    if Enum.all?(artifacts, &match?({:ok, _}, read(operation_id, &1))),
      do: :ok,
      else: {:error, :uncertain}
  end

  def read(operation_id, %ArtifactRef{sha256: digest, size_bytes: size})
      when is_integer(size) and size in 1..@max_bytes do
    with true <- hex?(operation_id) and hex?(digest),
         %{retained_root: root} when is_binary(root) <-
           Application.get_env(:mixer_hosted, :native_development_dispatch),
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
         true <- Bitwise.band(mode, 0o222) == 0,
         {:ok, {:ok, bytes}} when byte_size(bytes) == size <-
           File.open(path, [:read, :binary, :raw], &:file.read(&1, size + 1)),
         ^digest <- :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower) do
      {:ok, bytes}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  def read(_, _), do: {:error, :storage_unavailable}

  defp directory?(path), do: match?({:ok, %File.Stat{type: :directory}}, File.lstat(path))

  defp hex?(value),
    do: is_binary(value) and byte_size(value) == 64 and Regex.match?(~r/\A[0-9a-f]+\z/, value)
end
