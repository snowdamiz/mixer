defmodule MixerHostedWeb.CustomerWorkspaceAdminController do
  @moduledoc false
  import Plug.Conn
  alias MixerHosted.CustomerWorkspace.SelfService
  alias MixerHosted.Identity.BoundedJSON
  def init(operation), do: operation

  def call(conn, operation) do
    conn = put_resp_header(conn, "cache-control", "no-store")

    with true <- conn.query_string == "",
         [] <- get_req_header(conn, "x-http-method-override"),
         [] <- get_req_header(conn, "x-method-override"),
         [] <- get_req_header(conn, "content-encoding"),
         [] <- get_req_header(conn, "transfer-encoding"),
         {:ok, body, conn} <- body(conn, operation),
         true <- SelfService.valid_body?(Atom.to_string(operation), body) do
      case SelfService.execute(
             conn.assigns.verified_identity,
             Atom.to_string(operation),
             conn.path_params["organization_id"],
             conn.path_params["target_id"],
             body
           ) do
        {:ok, value} ->
          respond(
            conn,
            if(operation in [:create_organization, :create_project], do: 201, else: 200),
            value
          )

        {:error, :unauthenticated} ->
          respond(conn, 401, %{error: "unauthenticated"})

        {:error, :permission_denied} ->
          respond(conn, 403, %{error: "permission_denied"})

        {:error, :not_found} ->
          respond(conn, 404, %{error: "not_found"})

        {:error, :conflict} ->
          respond(conn, 409, %{error: "conflict"})

        {:error, :quota_exceeded} ->
          respond(conn, 429, %{error: "quota_exceeded"})

        _ ->
          respond(conn, 503, %{error: "authorization_unavailable"})
      end
    else
      _ -> respond(conn, 400, %{error: "invalid_request"})
    end
  rescue
    _ -> respond(conn, 503, %{error: "authorization_unavailable"})
  end

  defp body(conn, operation) when operation in [:usage, :export, :delete_project] do
    case read_body(conn, length: 0, read_length: 1, read_timeout: 1_000) do
      {:ok, "", conn} -> {:ok, %{}, conn}
      _ -> :error
    end
  end

  defp body(conn, _) do
    with ["application/json"] <- get_req_header(conn, "content-type"),
         {:ok, raw, conn} <- read_body(conn, length: 1024, read_length: 1024, read_timeout: 1_000),
         {:ok, body} <- BoundedJSON.object(raw, 1024),
         do: {:ok, body, conn}
  end

  defp respond(conn, status, value),
    do:
      conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(value))
end
