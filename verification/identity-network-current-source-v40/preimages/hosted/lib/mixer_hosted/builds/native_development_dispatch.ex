defmodule MixerHosted.Builds.NativeDevelopmentDispatch do
  @moduledoc """
  Opt-in loopback adapter for locally retained unsigned iOS Simulator outputs.

  The coordinator uses query_completion/1 under a durable, running lease.
  The worker revalidates its closed native checkpoint before reporting artifacts.
  """
  @behaviour MixerHosted.Builds.Dispatch
  alias MixerHosted.Builds.{Lifecycle, RetainedNativeArtifacts}
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  alias MixerHosted.Builds.Dispatch.{Observation, Request}

  @kinds Enum.map(Lifecycle.native_artifact_kinds(), &Atom.to_string/1)
  @max_artifact_bytes 256 * 1024 * 1024

  @impl true
  def query(request), do: observe("query", request)

  @impl true
  def ensure_started(request), do: observe("ensure_started", request)

  @impl true
  def stop(request), do: observe("stop", request)

  def query_completion(%Request{} = request) do
    with {:ok, %Observation{status: :running} = observation} <- query(request),
         {:ok, descriptors} <- native_artifacts(request),
         {:ok, result} <- native_result(request.operation_id, descriptors) do
      {:ok, %{observation | status: {:completed, result}}}
    end
  end

  defp native_result(operation_id, descriptors) do
    if Enum.any?(descriptors, &(&1["sizeBytes"] > Lifecycle.native_artifact_max_bytes())) do
      diagnostic = :crypto.hash(:sha256, "native_output_too_large:" <> operation_id)

      {:ok,
       %{
         outcome: :failed,
         class: :policy,
         code: :policy_rejection,
         diagnostic_sha256: Base.encode16(diagnostic, case: :lower)
       }}
    else
      artifacts =
        Enum.zip_with(descriptors, Lifecycle.native_artifact_kinds(), fn descriptor, kind ->
          %ArtifactRef{
            kind: kind,
            size_bytes: descriptor["sizeBytes"],
            sha256: descriptor["sha256"]
          }
        end)

      with true <- Lifecycle.native_artifacts?(artifacts),
           :ok <- RetainedNativeArtifacts.verify(operation_id, artifacts) do
        {:ok, %{outcome: :native_succeeded, artifacts: artifacts}}
      else
        _ -> {:error, :uncertain}
      end
    end
  end

  def native_artifacts(%Request{} = request) do
    with {:ok, %{"status" => "native_ready", "artifacts" => artifacts}} <-
           exchange("artifacts", request),
         true <- valid_artifacts?(artifacts) do
      {:ok, artifacts}
    else
      {:ok, _} -> {:error, :uncertain}
      false -> {:error, :uncertain}
      error -> error
    end
  end

  defp observe(action, %Request{} = request) do
    with {:ok, reply} <- exchange(action, request),
         {:ok, status} <- status(reply) do
      {:ok, %Observation{operation_id: request.operation_id, ref: request.ref, status: status}}
    end
  end

  defp exchange(action, request) do
    with %{port: port, worker_id: worker_id, token: token}
         when is_integer(port) and port in 1..65_535 and is_binary(worker_id) and
                byte_size(worker_id) > 0 and is_binary(token) and byte_size(token) >= 32 <-
           MixerHosted.RuntimeConfig.native_settings(),
         {:ok, socket} <-
           :gen_tcp.connect(
             {127, 0, 0, 1},
             port,
             [:binary, active: false, packet: :line, packet_size: 262_144],
             500
           ) do
      try do
        nonce = Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)

        body = Jason.encode!(%{action: action, request: normalize(request), worker_id: worker_id})
        mac = :crypto.mac(:hmac, :sha256, token, "request\n" <> nonce <> "\n" <> body)
        packet = Jason.encode!(%{nonce: nonce, body: body, mac: Base.encode16(mac, case: :lower)})

        with :ok <- :gen_tcp.send(socket, packet <> "\n"),
             {:ok, packet} <- :gen_tcp.recv(socket, 0, 1_000),
             {:ok, %{"body" => body, "mac" => mac}} <- Jason.decode(packet),
             true <- is_binary(body) and sha?(mac),
             expected = :crypto.mac(:hmac, :sha256, token, "response\n" <> nonce <> "\n" <> body),
             {:ok, signature} <- Base.decode16(mac, case: :lower),
             true <- Plug.Crypto.secure_compare(expected, signature),
             {:ok, reply} <- Jason.decode(body) do
          case reply do
            %{"error" => "stale"} -> {:error, :stale}
            %{"error" => "unavailable"} -> {:error, :unavailable}
            %{"error" => "uncertain"} -> {:error, :uncertain}
            _ -> {:ok, reply}
          end
        else
          _ -> {:error, :uncertain}
        end
      after
        :gen_tcp.close(socket)
      end
    else
      _ -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :uncertain}
  end

  defp status(%{"status" => "absent"}), do: {:ok, :absent}
  defp status(%{"status" => "running"}), do: {:ok, :running}

  defp status(%{"status" => "stopped", "diagnostic_sha256" => sha}) do
    if sha?(sha), do: {:ok, {:stopped, sha}}, else: {:error, :uncertain}
  end

  defp status(_), do: {:error, :uncertain}

  defp valid_artifacts?([_, _, _] = artifacts) do
    Enum.zip(artifacts, @kinds)
    |> Enum.all?(fn
      {%{"kind" => kind, "sizeBytes" => bytes, "sha256" => sha} = artifact, kind}
      when map_size(artifact) == 3 and is_integer(bytes) and bytes in 1..@max_artifact_bytes ->
        sha?(sha)

      _ ->
        false
    end)
  end

  defp valid_artifacts?(_), do: false

  defp sha?(value),
    do: is_binary(value) and byte_size(value) == 64 and Regex.match?(~r/\A[0-9a-f]+\z/, value)

  defp normalize(%DateTime{} = value), do: DateTime.to_unix(value, :millisecond)
  defp normalize(%_{} = value), do: value |> Map.from_struct() |> normalize()

  defp normalize(value) when is_map(value),
    do: Map.new(value, fn {key, item} -> {to_string(key), normalize(item)} end)

  defp normalize(value) when is_atom(value), do: Atom.to_string(value)
  defp normalize(value), do: value
end
