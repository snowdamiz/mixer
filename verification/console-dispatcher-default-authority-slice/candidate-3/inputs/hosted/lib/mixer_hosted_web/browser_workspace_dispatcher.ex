defmodule MixerHostedWeb.BrowserWorkspaceDispatcher do
  @moduledoc """
  Private fixed GET composition for a future trusted browser-session caller.

  A captured response is not an authenticated session or reusable authority.
  The caller must supply a server-held access token and a fresh server-generated
  request ID; input shape validation cannot establish their provenance.
  """

  alias MixerHosted.Repo
  alias MixerHostedWeb.BrowserWorkspaceDispatcher.{CaptureAdapter, Request}
  alias MixerHostedWeb.CustomerWorkspaceController
  alias MixerHostedWeb.Plugs.BearerIdentity

  @statuses [200, 400, 401, 403, 404, 415, 503]
  @challenges ["Bearer", ~s(Bearer error="invalid_token"), ~s(Bearer error="invalid_request")]

  @spec dispatch(term(), term(), term()) ::
          {:ok, %{status: integer(), headers: [{binary(), binary()}], body: binary()}}
          | {:error, :invalid_request | :authorization_unavailable}
  def dispatch(token, workspace_request, metadata) do
    with true <- is_binary(token) and byte_size(token) in 1..4_089,
         {:ok, request_id} <- request_id(metadata),
         {:ok, request} <- Request.new(workspace_request) do
      dispatch_request(token, request, request_id)
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp request_id(%{request_id: id} = metadata)
       when not is_struct(metadata) and map_size(metadata) == 1 and is_binary(id) and
              byte_size(id) == 32 do
    if Enum.all?(:binary.bin_to_list(id), &(&1 in ?0..?9 or &1 in ?a..?f)),
      do: {:ok, id},
      else: {:error, :invalid_request}
  end

  defp request_id(_), do: {:error, :invalid_request}

  defp dispatch_request(token, request, request_id) do
    if Repo.get_dynamic_repo() === Repo do
      conn = %Plug.Conn{
        adapter: CaptureAdapter.new(),
        owner: nil,
        method: "GET",
        request_path: request.path,
        path_info: ["v3", if(request.operation == :organizations, do: "orgs", else: "projects")],
        query_string: request.query,
        req_headers: [{"authorization", "Bearer " <> token}],
        resp_headers: [{"x-request-id", request_id}]
      }

      conn = BearerIdentity.call(conn, BearerIdentity.init([]))

      conn =
        if conn.halted,
          do: conn,
          else:
            CustomerWorkspaceController.call(
              conn,
              CustomerWorkspaceController.init(request.operation)
            )

      if Repo.get_dynamic_repo() === Repo,
        do: project(conn, request_id),
        else: {:error, :authorization_unavailable}
    else
      {:error, :authorization_unavailable}
    end
  end

  defp project(
         %Plug.Conn{
           adapter: {CaptureAdapter, %{sends: 1, status: status, headers: headers, body: body}},
           state: :sent,
           status: status,
           resp_headers: headers,
           resp_body: body,
           resp_cookies: cookies
         },
         request_id
       )
       when status in @statuses and is_binary(body) and byte_size(body) <= 262_144 and
              is_map(cookies) and map_size(cookies) == 0 do
    with {:ok, headers} <- project_headers(headers, status, request_id) do
      {:ok, %{status: status, headers: headers, body: body}}
    end
  end

  defp project(_, _), do: {:error, :authorization_unavailable}

  defp project_headers(headers, status, request_id) do
    required = [
      {"cache-control", "no-store"},
      {"content-type", "application/json; charset=utf-8"},
      {"x-request-id", request_id}
    ]

    # Equality of sorted complete lists rejects duplicates and all extra headers,
    # while the return order is independent of Plug's prepended header order.
    optional =
      case {status, headers} do
        {503, _} -> [{"retry-after", "1"}]
        {code, values} when code in [400, 401] -> challenge(values, code)
        _ -> []
      end

    if is_list(optional) and is_list(headers) and length(headers) <= 4 and
         Enum.sort(headers) === Enum.sort(required ++ optional),
       do: {:ok, required ++ optional},
       else: {:error, :authorization_unavailable}
  end

  defp challenge(headers, status) when is_list(headers) do
    case for({"www-authenticate", value} <- headers, do: value) do
      [value] when value in @challenges -> [{"www-authenticate", value}]
      [] when status == 400 -> []
      _ -> :invalid
    end
  end

  defp challenge(_, _), do: :invalid
end
