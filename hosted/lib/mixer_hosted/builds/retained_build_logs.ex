defmodule MixerHosted.Builds.RetainedBuildLogs do
  @moduledoc """
  Reads the local worker's public event projection after committed build admission.
  The retained root is operator-controlled and shared by the trusted local worker
  and API account. Raw command output and custody files are outside this interface.
  """
  alias MixerHosted.CustomerBuilds.Selection

  @max_bytes 2_048
  @max_stream_bytes 4_294_967_296
  @info [time: :posix]
  @phases ~w(compile link package)

  def read(operation, %Selection{} = selection) do
    with true <- Selection.digest?(operation),
         %{retained_root: root} when is_binary(root) <-
           MixerHosted.RuntimeConfig.native_settings(),
         {:ok, owner} <- retained_owner(root),
         {:ok, bytes} <- read_projection(Path.join(root, "customer-log-v1-" <> operation), owner),
         {:ok, events} <- events(bytes, operation, selection),
         {:ok, ^owner} <- retained_owner(root) do
      {:ok, events}
    else
      nil -> {:error, :not_found}
      {:error, :enoent} -> {:error, :not_found}
      _ -> {:error, :storage_unavailable}
    end
  end

  defp retained_owner(root) do
    with true <- root == Path.expand(root) and root != "/",
         {:ok, %File.Stat{type: :directory, uid: uid, mode: mode, inode: inode}} <-
           File.lstat(root),
         true <- Bitwise.band(mode, 0o7777) == 0o700,
         true <-
           root
           |> Path.split()
           |> Enum.scan(&Path.join(&2, &1))
           |> Enum.all?(&trusted_directory?(&1, uid)) do
      {:ok, {uid, inode}}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp trusted_directory?(path, owner) do
    case File.lstat(path) do
      {:ok, %File.Stat{type: :directory, uid: uid, mode: mode}} ->
        (uid == 0 or uid == owner) and Bitwise.band(mode, 0o022) == 0

      _ ->
        false
    end
  end

  defp read_projection(path, {owner, _}) do
    with {:ok, %File.Stat{type: :regular, uid: ^owner, links: 1, size: size, mode: mode} = seen}
         when size in 1..@max_bytes <- File.lstat(path, @info),
         true <- Bitwise.band(mode, 0o7777) == 0o400 do
      case File.open(path, [:read, :binary, :raw], fn io ->
             expected = stamp(seen)

             with {:ok, info} <- :file.read_file_info(io, @info),
                  ^expected <- stamp(File.Stat.from_record(info)),
                  {:ok, bytes} when byte_size(bytes) == size <- :file.read(io, size + 1),
                  {:ok, info} <- :file.read_file_info(io, @info),
                  ^expected <- stamp(File.Stat.from_record(info)),
                  {:ok, named} <- File.lstat(path, @info),
                  ^expected <- stamp(named) do
               {:ok, bytes}
             else
               _ -> {:error, :storage_unavailable}
             end
           end) do
        {:ok, {:ok, bytes}} -> {:ok, bytes}
        _ -> {:error, :storage_unavailable}
      end
    else
      {:error, :enoent} -> {:error, :enoent}
      _ -> {:error, :storage_unavailable}
    end
  end

  defp stamp(%File.Stat{} = stat), do: %File.Stat{stat | atime: nil, access: nil}

  defp events(bytes, operation, selection) do
    with {:ok,
          %{
            "version" => 1,
            "operationId" => ^operation,
            "sourceSha256" => source,
            "toolchainLockSha256" => lock,
            "buildDefinitionSha256" => definition,
            "cliExitCode" => cli_exit,
            "compiler" => compiler
          } = log}
         when map_size(log) == 7 and is_integer(cli_exit) and cli_exit in -255..255 <-
           Jason.decode(bytes),
         true <-
           {source, lock, definition} ==
             {selection.source_sha256, selection.toolchain_lock_sha256,
              selection.build_definition_sha256},
         {:ok, compiler_events} <- compiler_events(compiler) do
      {:ok, compiler_events ++ [%{event: "build_command_finished", exitCode: cli_exit}]}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp compiler_events(nil), do: {:ok, []}

  defp compiler_events(
         %{
           "exitCode" => exit,
           "stdoutBytes" => stdout,
           "stderrBytes" => stderr,
           "tailTruncated" => truncated,
           "phases" => phases
         } = compiler
       )
       when map_size(compiler) == 5 and is_integer(exit) and exit in -255..255 and
              is_integer(stdout) and stdout in 0..@max_stream_bytes and
              is_integer(stderr) and stderr in 0..@max_stream_bytes and is_boolean(truncated) and
              is_list(phases) do
    if phases == Enum.filter(@phases, &(&1 in phases)) do
      {:ok,
       [
         %{
           event: "compiler_finished",
           exitCode: exit,
           stdoutBytes: stdout,
           stderrBytes: stderr,
           tailTruncated: truncated,
           phases: phases
         }
       ]}
    else
      {:error, :storage_unavailable}
    end
  end

  defp compiler_events(_), do: {:error, :storage_unavailable}
end
