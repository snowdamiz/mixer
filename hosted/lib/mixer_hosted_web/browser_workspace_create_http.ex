defmodule MixerHostedWeb.BrowserWorkspaceCreateHTTP do
  @moduledoc false
  import Plug.Conn
  alias MixerHosted.BrowserAuth.{RuntimeOwner, Store}
  alias MixerHosted.Identity.BoundedJSON

  @limit 4096

  def call(conn) do
    with true <- conn.query_string == "",
         [] <- get_req_header(conn, "x-http-method-override"),
         [] <- get_req_header(conn, "x-method-override"),
         [] <- get_req_header(conn, "content-encoding"),
         [] <- get_req_header(conn, "transfer-encoding"),
         [type] when type in ["application/json", "application/json; charset=utf-8"] <-
           get_req_header(conn, "content-type"),
         {:ok, raw, conn} <-
           read_body(conn, length: @limit, read_length: @limit + 1, read_timeout: 1000),
         true <-
           get_req_header(conn, "content-length") in [[], [Integer.to_string(byte_size(raw))]],
         {:ok, body} <- BoundedJSON.object(raw, @limit),
         {:ok, operation} <- operation(conn.request_path, body) do
      case RuntimeOwner.create_workspace(conn.req_headers, operation) do
        {:ok, value} -> respond(conn, 201, value)
        {:error, reason} -> refusal(conn, reason)
      end
    else
      {:more, _, conn} -> respond(conn, 413, error(:invalid_request))
      _ -> refusal(conn, :invalid_request)
    end
  rescue
    _ -> refusal(conn, :authorization_unavailable)
  end

  defp operation("/console-api/v1/orgs", %{"display_name" => name} = body)
       when map_size(body) == 1,
       do: {:ok, {:create_organization, name}}

  defp operation(
         "/console-api/v1/projects",
         %{"organization_id" => organization, "display_name" => name} = body
       )
       when map_size(body) == 2,
       do: {:ok, {:create_project, organization, name}}

  defp operation(_, _), do: :error

  defp refusal(conn, reason) do
    case reason do
      :invalid_request -> respond(conn, 400, error(reason))
      :unauthenticated -> respond(conn, 401, error(reason))
      :permission_denied -> respond(conn, 403, error(reason))
      :not_found -> respond(conn, 404, error(reason))
      r when r in [:quota_exceeded, :conflict] -> respond(conn, 409, error(r))
      %Store.Failure{} -> unavailable(conn)
      _ -> unavailable(conn)
    end
  end

  defp unavailable(conn) do
    conn
    |> put_resp_header("retry-after", "1")
    |> respond(503, error(:authorization_unavailable))
  end

  defp error(code), do: %{error: %{code: code, message: "Workspace request refused."}}

  defp respond(conn, status, value) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_header("content-type", "application/json; charset=utf-8")
    |> send_resp(status, Jason.encode!(value))
  end
end
