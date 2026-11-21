defmodule MixerHostedWeb.NativeDevelopmentAttestationController do
  @moduledoc false
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.CustomerBuilds
  alias MixerHosted.CustomerBuilds.{LocalAttestation, Selection}
  alias MixerHostedWeb.Plugs.CustomerBuildRequest, as: Request

  @suffix "/native-development-attestation"
  @limit 16_384
  @errors %{
    invalid_request: 400,
    unauthenticated: 401,
    permission_denied: 403,
    not_found: 404,
    conflict: 409,
    immutable_conflict: 409,
    payload_too_large: 413,
    unsupported_media_type: 415,
    artifact_invalid: 422
  }

  @impl true
  def init(:attach), do: :attach

  @impl true
  def call(conn, :attach) do
    with :ok <- local_api(conn),
         {:ok, selection} <- selection(conn),
         :ok <- media(conn),
         {:ok, length} <- content_length(conn),
         {:ok, bytes, conn} <- body(conn, length) do
      respond(
        conn,
        CustomerBuilds.attach_native_development_attestation(
          conn.assigns.verified_identity,
          selection,
          bytes
        )
      )
    else
      {:error, reason} -> respond(conn, {:error, reason})
    end
  end

  defp local_api(conn) do
    with %{address: {127, _, _, _}} <- get_peer_data(conn),
         {:ok, _} <- LocalAttestation.configuration() do
      :ok
    else
      %{address: _} -> {:error, :permission_denied}
      _ -> {:error, :authorization_unavailable}
    end
  end

  defp selection(conn) do
    with {:ok, %Selection{platform: "ios"} = selection} <-
           Request.selection(conn.path_params, conn.query_string),
         true <- conn.request_path == Request.path(selection) <> @suffix do
      {:ok, selection}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp media(conn) do
    if get_req_header(conn, "content-type") == ["application/json"] and
         get_req_header(conn, "content-encoding") == [],
       do: :ok,
       else: {:error, :unsupported_media_type}
  end

  defp content_length(conn) do
    with [] <- get_req_header(conn, "transfer-encoding"),
         [raw] when byte_size(raw) in 1..20 <- get_req_header(conn, "content-length"),
         {length, ""} when length > 0 <- Integer.parse(raw),
         ^raw <- Integer.to_string(length) do
      if length <= @limit, do: {:ok, length}, else: {:error, :payload_too_large}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp body(conn, length) do
    case read_body(conn, length: @limit, read_length: length, read_timeout: 1_000) do
      {:ok, bytes, conn} when byte_size(bytes) == length -> {:ok, bytes, conn}
      {:more, _, _} -> {:error, :payload_too_large}
      _ -> {:error, :invalid_request}
    end
  end

  defp respond(conn, {:ok, :attached}), do: json(conn, 201, %{status: "attached"})
  defp respond(conn, {:ok, :duplicate}), do: json(conn, 200, %{status: "duplicate"})

  defp respond(conn, {:error, reason}) when is_map_key(@errors, reason),
    do: error(conn, @errors[reason], reason)

  defp respond(conn, _),
    do: conn |> put_resp_header("retry-after", "1") |> error(503, :authorization_unavailable)

  defp error(conn, status, code), do: json(conn, status, %{error: %{code: code}})

  defp json(conn, status, value) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(value))
  end
end
