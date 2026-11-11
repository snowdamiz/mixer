defmodule MixerHostedWeb.CustomerBuildController do
  @moduledoc "Private, unmounted read boundary. No request-selected dependencies."
  @behaviour Plug
  import Plug.Conn
  alias MixerHostedWeb.Plugs.CustomerBuildRequest, as: Request
  def init([]), do: []

  def call(conn, []) do
    case Request.parse(conn) do
      {:ok, selection, next} ->
        respond(
          next,
          MixerHosted.CustomerBuilds.read(next.assigns[:verified_identity], selection)
        )

      _ ->
        respond(conn, {:error, :invalid_request})
    end
  rescue
    _ -> respond(conn, {:error, :authorization_unavailable})
  end

  defp respond(conn, {:ok, dto}) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_content_type("application/json")
    |> send_resp(200, Jason.encode!(%{build: dto}))
    |> halt()
  end

  defp respond(conn, {:error, reason}) do
    {status, code} =
      case reason do
        :invalid_request -> {400, "invalid_request"}
        :unauthenticated -> {401, "unauthenticated"}
        :permission_denied -> {403, "permission_denied"}
        :not_found -> {404, "not_found"}
        _ -> {503, "authorization_unavailable"}
      end

    conn =
      conn
      |> put_resp_header("cache-control", "no-store")
      |> put_resp_content_type("application/json")

    conn = if status == 503, do: put_resp_header(conn, "retry-after", "1"), else: conn
    conn |> send_resp(status, Jason.encode!(%{error: %{code: code}})) |> halt()
  end

  defp respond(conn, _), do: respond(conn, {:error, :authorization_unavailable})
end
