defmodule MixerHosted.Builds.DevelopmentDispatch do
  @moduledoc """
  Explicit development-only transport to a separately authorized local worker.
  No worker or configuration is installed by loading this module. The worker
  performs all source resolution and compiler execution outside the BEAM.
  Configuration requires an integer port in 0..65535, a nonempty UTF-8 worker_id
  and a nonempty ASCII token, matching the worker's string authentication inputs.
  """
  @behaviour MixerHosted.Builds.Dispatch
  alias MixerHosted.Builds.Dispatch.{Request, Observation}

  @impl true
  def query(request), do: invoke("query", request)
  @impl true
  def ensure_started(request), do: invoke("ensure_started", request)
  @impl true
  def stop(request), do: invoke("stop", request)

  defp invoke(action, %Request{} = request) do
    with {:ok, %{port: port, worker_id: worker, token: token}} <- configuration(),
         {:ok, socket} <-
           :gen_tcp.connect(
             {127, 0, 0, 1},
             port,
             [:binary, active: false, packet: :line, packet_size: 262_144],
             500
           ) do
      try do
        payload = %{action: action, worker_id: worker, token: token, request: normalize(request)}

        with :ok <- :gen_tcp.send(socket, Jason.encode!(payload) <> "\n"),
             {:ok, bytes} <- :gen_tcp.recv(socket, 0, 1_000),
             {:ok, reply} <- Jason.decode(bytes) do
          observation(request, reply)
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

  defp configuration do
    with {:ok, %{port: port, worker_id: worker, token: token} = config}
         when is_integer(port) and port >= 0 and port <= 65_535 and
                is_binary(worker) and byte_size(worker) > 0 and
                is_binary(token) and byte_size(token) > 0 <-
           Application.fetch_env(:mixer_hosted, :development_dispatch),
         true <- String.valid?(worker) and Enum.all?(:binary.bin_to_list(token), &(&1 < 128)) do
      {:ok, config}
    else
      _ -> {:error, :unavailable}
    end
  end

  defp observation(request, %{"status" => status}) when status in ["absent", "running"],
    do:
      {:ok,
       %Observation{
         operation_id: request.operation_id,
         ref: request.ref,
         status: if(status == "absent", do: :absent, else: :running)
       }}

  defp observation(request, %{"status" => "completed", "diagnostic_sha256" => digest})
       when is_binary(digest) and byte_size(digest) == 64,
       do:
         {:ok,
          %Observation{
            operation_id: request.operation_id,
            ref: request.ref,
            status:
              {:completed,
               %{
                 outcome: :failed,
                 class: :compiler,
                 code: :compiler_error,
                 diagnostic_sha256: digest
               }}
          }}

  defp observation(request, %{"status" => "stopped", "diagnostic_sha256" => digest})
       when is_binary(digest) and byte_size(digest) == 64,
       do:
         {:ok,
          %Observation{
            operation_id: request.operation_id,
            ref: request.ref,
            status: {:stopped, digest}
          }}

  defp observation(_, %{"error" => "stale"}), do: {:error, :stale}
  defp observation(_, %{"error" => "unavailable"}), do: {:error, :unavailable}
  defp observation(_, _), do: {:error, :uncertain}

  defp normalize(%DateTime{} = value), do: DateTime.to_unix(value, :millisecond)
  defp normalize(%_{} = value), do: value |> Map.from_struct() |> normalize()

  defp normalize(value) when is_map(value),
    do: Map.new(value, fn {key, item} -> {to_string(key), normalize(item)} end)

  defp normalize(value) when is_atom(value), do: Atom.to_string(value)
  defp normalize(value), do: value
end
