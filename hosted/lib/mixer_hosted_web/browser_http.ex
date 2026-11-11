defmodule MixerHostedWeb.BrowserHTTP do
  @moduledoc "Private fixed browser reads. Explicit listener only; no default application mount."
  @behaviour Plug
  alias MixerHosted.BrowserAuth.{Protocol, RuntimeOwner}
  alias MixerHostedWeb.BrowserWorkspaceDispatcher.Request
  import Plug.Conn

  def init([]), do: []

  def call(conn, []) do
    with true <- conn.method == "GET",
         true <-
           conn.request_path in [
             "/auth/session",
             "/console-api/v1/orgs",
             "/console-api/v1/projects",
             "/console-api/v1/builds"
           ],
         {:ok, _} <- Protocol.parse_session_cookie(conn.req_headers),
         false <-
           Enum.any?(conn.req_headers, fn {k, v} ->
             k == "transfer-encoding" or (k == "content-length" and v != "0")
           end),
         {:ok, "", conn} <- read_body(conn, length: 0, read_length: 1, read_timeout: 1_000) do
      dispatch(conn)
    else
      _ ->
        error(
          conn,
          if(
            conn.method == "GET" and
              conn.request_path in [
                "/auth/session",
                "/console-api/v1/orgs",
                "/console-api/v1/projects",
                "/console-api/v1/builds"
              ],
            do: 400,
            else: 404
          )
        )
    end
  rescue
    _ -> error(conn, 503)
  catch
    _, _ -> error(conn, 503)
  end

  defp dispatch(%{request_path: "/auth/session", query_string: ""} = conn) do
    case RuntimeOwner.read_session(conn.req_headers) do
      {:ok, {:unauthenticated, csrf}, :unchanged} ->
        if Protocol.token?(csrf),
          do: json(conn, 200, %{state: "unauthenticated", csrf_token: csrf}),
          else: error(conn, 503)

      {:ok, {:authenticated, csrf, revision, generation, expires}, :unchanged}
      when is_integer(revision) and revision >= 0 and is_integer(expires) ->
        if Protocol.token?(csrf) and Protocol.token?(generation) and
             expires > System.system_time(:second),
           do:
             json(conn, 200, %{
               state: "authenticated",
               csrf_token: csrf,
               generation: generation,
               expires_at: expires
             }),
           else: error(conn, 503)

      {:error, :invalid_request} ->
        error(conn, 400)

      _ ->
        error(conn, 503)
    end
  end

  defp dispatch(%{request_path: "/auth/session"} = conn), do: error(conn, 400)

  defp dispatch(%{request_path: "/console-api/v1/builds"} = conn) do
    with {:ok, selection} <- MixerHostedWeb.BrowserBuildRequest.parse(conn.query_string) do
      case RuntimeOwner.read_build(conn.req_headers, selection) do
        {:ok, %{status: status, headers: headers, body: body}} ->
          conn |> merge_resp_headers(headers) |> send_resp(status, body)

        {:error, :invalid_request} ->
          error(conn, 400)

        {:error, :unauthenticated} ->
          error(conn, 401)

        _ ->
          error(conn, 503)
      end
    else
      _ -> error(conn, 400)
    end
  end

  defp dispatch(conn) do
    with {:ok, request} <- query(conn.request_path, conn.query_string),
         {:ok, _} <- Request.new(request) do
      case RuntimeOwner.read_workspace(conn.req_headers, request) do
        {:ok, %{status: status, headers: headers, body: body}} ->
          conn |> merge_resp_headers(headers) |> send_resp(status, body)

        {:error, :invalid_request} ->
          error(conn, 400)

        {:error, :unauthenticated} ->
          error(conn, 401)

        _ ->
          error(conn, 503)
      end
    else
      _ -> error(conn, 400)
    end
  end

  defp query(path, raw) when byte_size(raw) <= 8_192 do
    allowed =
      if path == "/console-api/v1/projects",
        do: ~w(organization_id limit cursor),
        else: ~w(limit cursor)

    pairs = if raw == "", do: [], else: String.split(raw, "&")

    with true <- length(pairs) <= length(allowed),
         {:ok, fields} <-
           Enum.reduce_while(pairs, {:ok, %{}}, fn pair, {:ok, acc} ->
             case String.split(pair, "=", parts: 2) do
               [k, v] ->
                 if k in allowed and not Map.has_key?(acc, k) and v != "" and
                      not Regex.match?(~r/%(?![0-9a-fA-F]{2})/, v) do
                   {:cont, {:ok, Map.put(acc, k, URI.decode_www_form(v))}}
                 else
                   {:halt, :error}
                 end

               _ ->
                 {:halt, :error}
             end
           end),
         limit = Map.get(fields, "limit", "50"),
         true <-
           byte_size(limit) in 1..3 and Enum.all?(:binary.bin_to_list(limit), &(&1 in ?0..?9)),
         {limit, ""} <- Integer.parse(limit),
         page = %{limit: limit, cursor: fields["cursor"]} do
      {:ok,
       if(path == "/console-api/v1/orgs",
         do: {:organizations, page},
         else: {:projects, fields["organization_id"], page}
       )}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp query(_, _), do: {:error, :invalid_request}

  defp error(conn, status) do
    code =
      case status do
        400 -> "invalid_request"
        401 -> "unauthenticated"
        404 -> "not_found"
        _ -> "authorization_unavailable"
      end

    conn = if status == 503, do: put_resp_header(conn, "retry-after", "1"), else: conn
    json(conn, status, %{error: %{code: code, message: "Browser request refused."}})
  end

  defp json(conn, status, value) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> put_resp_header("content-type", "application/json; charset=utf-8")
    |> send_resp(status, Jason.encode!(value))
  end
end

defmodule MixerHostedWeb.BrowserHTTP.Server do
  @moduledoc "Explicit private loopback HTTP/1 listener; no arbitrary plug, host or route configuration."
  def start_link([]) do
    Bandit.start_link(
      plug: MixerHostedWeb.BrowserHTTP,
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
