defmodule MixerHostedWeb.BrowserCreateHTTP do
  @moduledoc false
  import Plug.Conn
  alias MixerHosted.CustomerBuilds.CreateInput

  def call(conn) do
    lengths = get_req_header(conn, "content-length")

    with true <- conn.query_string == "",
         [] <- get_req_header(conn, "content-encoding"),
         [] <- get_req_header(conn, "transfer-encoding"),
         :ok <- csrf_shape(conn),
         [type] <- get_req_header(conn, "content-type"),
         true <- type in ["application/json", "application/json; charset=utf-8"],
         [key] <- get_req_header(conn, "idempotency-key"),
         true <- CreateInput.id?(key),
         :ok <- body_length(lengths),
         {:ok, raw, conn} <- read_body(conn, length: 4096, read_length: 4097, read_timeout: 1000),
         true <- lengths == [] or hd(lengths) == Integer.to_string(byte_size(raw)),
         {:ok, input} <- CreateInput.parse(raw),
         {:ok, r} <-
           MixerHosted.BrowserAuth.RuntimeOwner.create_build(conn.req_headers, input, key) do
      conn |> merge_resp_headers(r.headers) |> send_resp(r.status, r.body)
    else
      {:more, _, conn} ->
        refuse(conn, 413, :invalid_request)

      {:error, :too_large} ->
        refuse(conn, 413, :invalid_request)

      {:error, :permission_denied} ->
        refuse(conn, 403, :permission_denied)

      {:error, :unauthenticated} ->
        refuse(conn, 401, :unauthenticated)

      {:error, %MixerHosted.BrowserAuth.Store.Failure{}} ->
        refuse(conn, 503, :authorization_unavailable)

      _ ->
        refuse(conn, 400, :invalid_request)
    end
  rescue
    _ -> refuse(conn, 503, :authorization_unavailable)
  end

  defp body_length([]), do: :ok

  defp body_length([v]) when byte_size(v) in 1..20 do
    if Regex.match?(~r/^(0|[1-9][0-9]*)$/, v) do
      if String.to_integer(v) <= 4096, do: :ok, else: {:error, :too_large}
    else
      {:error, :invalid_request}
    end
  end

  defp body_length(_), do: {:error, :invalid_request}

  defp csrf_shape(conn) do
    case {get_req_header(conn, "origin"), get_req_header(conn, "x-mixer-csrf")} do
      {[origin], [csrf]} when is_binary(origin) ->
        if MixerHosted.BrowserAuth.Protocol.token?(csrf),
          do: :ok,
          else: {:error, :permission_denied}

      _ ->
        {:error, :permission_denied}
    end
  end

  defp refuse(conn, status, reason) do
    r = MixerHosted.BrowserAuth.ActiveCreate.render({:error, reason})
    conn |> merge_resp_headers(r.headers) |> send_resp(status, r.body)
  end
end
