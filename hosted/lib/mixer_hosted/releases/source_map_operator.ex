defmodule MixerHosted.Releases.SourceMapOperator do
  @moduledoc false

  alias MixerHosted.BrowserAuth.Installation
  alias MixerHosted.Identity.{ConfiguredVerifier, StartupConfig, VerifiedIdentity}
  alias MixerHosted.Protocol.ArtifactV3Policy
  alias MixerHosted.Releases.{SourceMaps, Target, WriterRepo}
  alias MixerHosted.RuntimeConfig

  def main(args, token) do
    with true <- SourceMaps.enabled?(),
         {:ok, supervisor} <- start_components() do
      try do
        run(args, token)
      after
        Supervisor.stop(supervisor)
      end
    else
      false -> {:error, :disabled}
      _ -> {:error, :operator_unavailable}
    end
  rescue
    _ -> {:error, :operator_unavailable}
  catch
    :exit, _ -> {:error, :operator_unavailable}
  end

  defp start_components do
    with {%RuntimeConfig{role: :api, identity_startup: identity}, installation} <-
           Application.get_env(:mixer_hosted, :startup),
         %StartupConfig{mode: :configured, owner_options: options} <- identity,
         [_ | _] <- Application.get_env(:mixer_hosted, WriterRepo),
         {:ok, _} <- Application.ensure_all_started(:postgrex),
         {:ok, _} <- Application.ensure_all_started(:ecto_sql),
         {:ok, _} <- Application.ensure_all_started(:jose),
         {:ok, _} <- Application.ensure_all_started(:ssl) do
      Supervisor.start_link(
        [Installation.identity_child(installation, options), WriterRepo],
        strategy: :one_for_one
      )
    end
  end

  defp run(args, token) do
    with {:ok, operation, sequence, digest, path} <- command(args),
         {:ok, identity} <- authenticate(token),
         %{target: %Target{} = target} <-
           Application.get_env(:mixer_hosted, :local_release_target) do
      execute(operation, identity, target, sequence, digest, path)
    else
      {:error, _} = error -> error
      _ -> {:error, :operator_unavailable}
    end
  end

  defp command(["retain", sequence, digest, path, deadline]) do
    with {:ok, deadline} <- positive_integer(deadline) do
      selection({:retain, deadline}, sequence, digest, path)
    end
  end

  defp command(["read", sequence, digest]), do: selection(:read, sequence, digest, nil)
  defp command(_), do: {:error, :invalid_request}

  defp selection(operation, sequence, digest, path) do
    with {:ok, sequence} <- positive_integer(sequence),
         true <- ArtifactV3Policy.digest?(digest) do
      {:ok, operation, sequence, digest, path}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp positive_integer(value) when is_binary(value) and byte_size(value) in 1..20 do
    with {number, ""} <- Integer.parse(value),
         true <- number > 0 and ArtifactV3Policy.uint?(number),
         ^value <- Integer.to_string(number) do
      {:ok, number}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp positive_integer(_), do: {:error, :invalid_request}

  defp authenticate(token) when is_binary(token) and byte_size(token) in 1..4_089 do
    case ConfiguredVerifier.authenticate(token, System.system_time(:second)) do
      {:ok, %VerifiedIdentity{identity_class: :human, scopes: scopes} = identity} ->
        if "mixer.release.publish" in scopes,
          do: {:ok, identity},
          else: {:error, :permission_denied}

      {:ok, _} ->
        {:error, :permission_denied}

      {:error, reason} ->
        {:error, reason}
    end
  end

  defp authenticate(_), do: {:error, :unauthenticated}

  defp execute({:retain, deadline}, identity, target, sequence, digest, path) do
    with {:ok, bytes} <- read_input(path) do
      SourceMaps.retain(identity, target, sequence, digest, deadline, bytes)
    end
  end

  defp execute(:read, identity, target, sequence, digest, nil) do
    SourceMaps.read(identity, target, sequence, digest)
  end

  defp read_input(path) do
    maximum = SourceMaps.maximum_bytes()

    with {:ok, %File.Stat{type: :regular, size: size}} when size in 1..maximum//1 <-
           File.lstat(path),
         {:ok, {:ok, bytes}} <-
           File.open(path, [:read, :raw, :binary], &:file.read(&1, maximum + 1)),
         true <- byte_size(bytes) in 1..maximum do
      {:ok, bytes}
    else
      _ -> {:error, :invalid_input_file}
    end
  end
end
