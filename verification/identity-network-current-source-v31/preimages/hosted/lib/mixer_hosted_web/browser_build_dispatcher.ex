defmodule MixerHostedWeb.BrowserBuildDispatcher do
  @moduledoc "Private fixed composition for owner-retained access after active SQL admission."
  alias MixerHosted.CustomerBuilds
  alias MixerHosted.CustomerBuilds.Selection
  alias MixerHosted.Identity.ConfiguredVerifier

  def dispatch(token, input, %{request_id: request_id} = metadata)
      when is_binary(token) and byte_size(token) in 1..4089 and map_size(metadata) == 1 and
             is_binary(request_id) and byte_size(request_id) == 32 do
    with true <- Enum.all?(:binary.bin_to_list(request_id), &(&1 in ?0..?9 or &1 in ?a..?f)),
         {:ok, selection} <- Selection.new(input) do
      result =
        case ConfiguredVerifier.authenticate(token, System.system_time(:second)) do
          {:ok, identity} -> CustomerBuilds.read(identity, selection)
          {:error, :unauthenticated} -> {:error, :unauthenticated}
          _ -> {:error, :authorization_unavailable}
        end

      response(result, request_id)
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  def dispatch(_, _, _), do: {:error, :invalid_request}

  defp response({:ok, dto}, id), do: capture(200, %{build: dto}, id)

  defp response({:error, reason}, id) do
    {status, code} =
      case reason do
        :invalid_request -> {400, "invalid_request"}
        :unauthenticated -> {401, "unauthenticated"}
        :permission_denied -> {403, "permission_denied"}
        :not_found -> {404, "not_found"}
        _ -> {503, "authorization_unavailable"}
      end

    capture(status, %{error: %{code: code}}, id)
  end

  defp response(_, id), do: response({:error, :authorization_unavailable}, id)

  defp capture(status, value, id) do
    body = Jason.encode!(value)

    headers = [
      {"cache-control", "no-store"},
      {"content-type", "application/json; charset=utf-8"},
      {"x-request-id", id}
    ]

    headers = if status == 503, do: headers ++ [{"retry-after", "1"}], else: headers

    if byte_size(body) <= 262_144,
      do: {:ok, %{status: status, headers: headers, body: body}},
      else: {:error, :authorization_unavailable}
  end
end
