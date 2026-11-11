defmodule MixerHostedWeb.BrowserLoginHTTP do
  @moduledoc "Private opt-in browser login adapter. Never mounted by the application."
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.BrowserAuth.{CallbackLifecycle, PreauthDraft, Protocol, RuntimeOwner}

  def init([]), do: []

  def call(conn, []) do
    case {conn.method, conn.request_path} do
      {"GET", "/auth/session"} ->
        with {:ok, nil} <- Protocol.parse_session_cookie(conn.req_headers),
             true <- conn.query_string == "",
             {:ok, conn} <- empty_body(conn) do
          bootstrap(conn)
        else
          {:ok, cookie} when is_binary(cookie) -> MixerHostedWeb.BrowserHTTP.call(conn, [])
          _ -> error(conn, 400)
        end

      {"POST", "/auth/login"} ->
        with true <- conn.query_string == "",
             {:ok, cookie} when is_binary(cookie) <-
               Protocol.parse_session_cookie(conn.req_headers),
             {:ok, conn} <- empty_body(conn),
             {:ok, %PreauthDraft.Authorization{url: url, expires_at: expires}} <-
               RuntimeOwner.begin_login(cookie, conn.req_headers, :workspace, metadata()),
             true <- expires > System.system_time(:second) do
          redirect(conn, url)
        else
          _ -> error(conn, 503)
        end

      {"GET", "/auth/callback"} ->
        with {:ok, _} <- Protocol.parse_session_cookie(conn.req_headers),
             {:ok, conn} <- empty_body(conn),
             {:ok, %CallbackLifecycle.Result{cookie: cookie, expires_at: expires}} <-
               RuntimeOwner.callback(conn.req_headers, conn.query_string),
             {:ok, value} <- cookie(cookie, expires, 900) do
          conn |> put_resp_header("set-cookie", value) |> redirect("/workspace")
        else
          _ -> error(conn, 503)
        end

      _ ->
        MixerHostedWeb.BrowserHTTP.call(conn, [])
    end
  rescue
    _ -> error(conn, 503)
  catch
    _, _ -> error(conn, 503)
  end

  defp bootstrap(conn) do
    with {:ok, %PreauthDraft.Preauth{cookie: cookie, csrf: csrf, expires_at: expires}} <-
           RuntimeOwner.bootstrap(metadata()),
         {:ok, value} <- cookie(cookie, expires, 300) do
      conn
      |> put_resp_header("set-cookie", value)
      |> json(200, %{state: "unauthenticated", csrf_token: csrf})
    else
      _ -> error(conn, 503)
    end
  end

  defp cookie(token, expires, cap),
    do: Protocol.session_cookie(token, min(cap, expires - System.system_time(:second)))

  defp metadata, do: %{request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)}

  defp empty_body(conn) do
    if Enum.any?(conn.req_headers, fn {k, v} ->
         k == "transfer-encoding" or (k == "content-length" and v != "0")
       end) do
      :error
    else
      case read_body(conn, length: 0, read_length: 1, read_timeout: 1_000) do
        {:ok, "", conn} -> {:ok, conn}
        _ -> :error
      end
    end
  end

  defp redirect(conn, location) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_header("referrer-policy", "no-referrer")
    |> put_resp_header("location", location)
    |> send_resp(303, "")
  end

  defp error(conn, status) do
    conn
    |> delete_resp_header("set-cookie")
    |> delete_resp_header("location")
    |> json(status, %{
      error: %{code: "authorization_unavailable", message: "Browser request refused."}
    })
  end

  defp json(conn, status, value) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_header("content-type", "application/json; charset=utf-8")
    |> send_resp(status, Jason.encode!(value))
  end
end

defmodule MixerHostedWeb.BrowserLoginHTTP.Server do
  @moduledoc "Explicit private loopback-only HTTP/1 listener for synthetic development."
  def start_link([]) do
    Bandit.start_link(
      plug: MixerHostedWeb.BrowserLoginHTTP,
      ip: {127, 0, 0, 1},
      port: 0,
      startup_log: false,
      http_2_options: [enabled: false],
      websocket_options: [enabled: false],
      http_1_options: [
        max_header_count: 64,
        max_header_length: 8_320,
        max_request_line_length: 8_384
      ]
    )
  end
end
