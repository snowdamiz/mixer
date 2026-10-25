defmodule MixerHostedWeb.Plugs.CustomerWorkspaceRequest do
  @moduledoc "Closed read-only workspace request admission after BearerIdentity."
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Identity.{BoundedJSON, VerifiedIdentity}

  @read_deadline_ms 15_000
  @maximum_reads 128

  @impl true
  def init(operation) when operation in [:organizations, :projects],
    do: init(operation: operation)

  def init(opts) when is_list(opts) do
    unless Keyword.keyword?(opts) and
             Enum.all?(Keyword.keys(opts), &(&1 in [:operation, :clock])) and
             length(Keyword.keys(opts)) == length(Enum.uniq(Keyword.keys(opts))) do
      raise ArgumentError, "invalid workspace request options"
    end

    operation = Keyword.get(opts, :operation)
    clock = Keyword.get(opts, :clock, {System, :monotonic_time, [:millisecond]})

    unless operation in [:organizations, :projects] and valid_clock?(clock),
      do: raise(ArgumentError, "invalid workspace request dependencies")

    %{operation: operation, clock: clock}
  end

  def init(_), do: raise(ArgumentError, "invalid workspace request options")

  defp valid_clock?({module, function, args})
       when is_atom(module) and is_atom(function) and is_list(args),
       do:
         match?({:module, ^module}, Code.ensure_compiled(module)) and
           function_exported?(module, function, length(args))

  defp valid_clock?(_), do: false

  @impl true
  def call(conn, %{operation: operation, clock: clock}) do
    conn = response_headers(conn)

    with :ok <- identity(conn.assigns[:verified_identity]),
         :ok <- method(conn.method),
         :ok <- path(conn.request_path, operation),
         {:ok, organization, page} <- query(conn.query_string, operation),
         :ok <- encoding(get_req_header(conn, "content-encoding")),
         :ok <- media(get_req_header(conn, "content-type")),
         {:ok, conn} <- empty_body(conn, clock) do
      assign(conn, :customer_workspace_request, %{organization_id: organization, page: page})
    else
      {:error, reason, conn} -> reject(conn, reason)
      {:error, reason} -> reject(conn, reason)
    end
  end

  defp identity(%VerifiedIdentity{identity_class: :human, scopes: scopes}) when is_list(scopes),
    do:
      if("mixer.workspace.read" in scopes,
        do: :ok,
        else: {:error, :permission_denied}
      )

  defp identity(%VerifiedIdentity{}), do: {:error, :permission_denied}
  defp identity(_), do: {:error, :unauthenticated}
  defp method(method) when method in ["GET", "HEAD"], do: :ok
  defp method(_), do: {:error, :not_found}
  defp path("/v3/orgs", :organizations), do: :ok
  defp path("/v3/projects", :projects), do: :ok
  defp path(_, _), do: {:error, :invalid_request}

  defp query(raw, operation) when is_binary(raw) and byte_size(raw) <= 8_192 do
    fields = if raw == "", do: [], else: :binary.split(raw, "&", [:global])
    maximum = if operation == :organizations, do: 2, else: 3

    if length(fields) <= maximum do
      fields
      |> Enum.reduce_while({:ok, %{}}, fn field, {:ok, result} ->
        with [name, value] <- :binary.split(field, "="),
             {:ok, name} <- decode(name),
             {:ok, value} <- decode(value),
             true <- name in ["organization_id", "limit", "cursor"],
             false <- Map.has_key?(result, name),
             true <- name != "" and value != "" do
          {:cont, {:ok, Map.put(result, name, value)}}
        else
          _ -> {:halt, {:error, :invalid_request}}
        end
      end)
      |> case do
        {:ok, fields} -> page(fields, operation)
        error -> error
      end
    else
      {:error, :invalid_request}
    end
  end

  defp query(_, _), do: {:error, :invalid_request}

  defp page(fields, operation) do
    organization = Map.get(fields, "organization_id")
    cursor = Map.get(fields, "cursor")

    with true <-
           (operation == :organizations and not Map.has_key?(fields, "organization_id")) or
             (operation == :projects and Scope.identifier?(organization)),
         {:ok, limit} <- limit(Map.get(fields, "limit")),
         true <-
           is_nil(cursor) or match?({:ok, _}, decode_cursor(cursor, operation, organization)) do
      {:ok, organization, %{limit: limit, cursor: cursor}}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp limit(nil), do: {:ok, 50}

  defp limit(<<first, rest::binary>> = value)
       when first in ?1..?9 and byte_size(value) <= 3 do
    if Enum.all?(:binary.bin_to_list(rest), &(&1 in ?0..?9)) do
      number = String.to_integer(value)
      if number <= 100, do: {:ok, number}, else: {:error, :invalid_request}
    else
      {:error, :invalid_request}
    end
  end

  defp limit(_), do: {:error, :invalid_request}

  # Unlike URI.decode_www_form/1 alone, this rejects malformed escapes before
  # an otherwise printable '%' can be accepted as part of a real tenant ID.
  defp decode(value) do
    with {:ok, bytes} <- decode_bytes(value, []),
         true <- String.valid?(bytes) do
      {:ok, bytes}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp decode_bytes(<<>>, bytes), do: {:ok, IO.iodata_to_binary(Enum.reverse(bytes))}

  defp decode_bytes(<<?%, high, low, rest::binary>>, bytes) do
    with h when is_integer(h) <- hex(high),
         l when is_integer(l) <- hex(low) do
      decode_bytes(rest, [h * 16 + l | bytes])
    else
      _ -> :error
    end
  end

  defp decode_bytes(<<?%, _::binary>>, _bytes), do: :error
  defp decode_bytes(<<?+, rest::binary>>, bytes), do: decode_bytes(rest, [32 | bytes])
  defp decode_bytes(<<byte, rest::binary>>, bytes), do: decode_bytes(rest, [byte | bytes])
  defp hex(byte) when byte in ?0..?9, do: byte - ?0
  defp hex(byte) when byte in ?A..?F, do: byte - ?A + 10
  defp hex(byte) when byte in ?a..?f, do: byte - ?a + 10
  defp hex(_), do: :invalid

  @doc false
  def decode_cursor(cursor, operation, organization)
      when is_binary(cursor) and byte_size(cursor) in 1..1400 do
    with true <-
           Enum.all?(:binary.bin_to_list(cursor), fn byte ->
             byte in ?A..?Z or byte in ?a..?z or byte in ?0..?9 or byte in [?_, ?-]
           end),
         {:ok, bytes} <- Base.url_decode64(cursor, padding: false),
         true <- byte_size(bytes) <= 1024,
         {:ok, value} <- BoundedJSON.object(bytes, 1024),
         true <- value["v"] === 1,
         true <- value["kind"] == Atom.to_string(operation),
         true <- Scope.identifier?(value["after"]),
         {:ok, pairs} <- cursor_pairs(value, operation, organization),
         canonical = Jason.encode!(%Jason.OrderedObject{values: pairs}),
         true <- Base.url_encode64(canonical, padding: false) == cursor do
      {:ok, value["after"]}
    else
      _ -> :error
    end
  rescue
    _ -> :error
  end

  def decode_cursor(_, _, _), do: :error

  defp cursor_pairs(value, :organizations, nil) when map_size(value) == 3,
    do: {:ok, [{"v", 1}, {"kind", "organizations"}, {"after", value["after"]}]}

  defp cursor_pairs(value, :projects, organization) when map_size(value) == 4 do
    if value["organization_id"] == organization and Scope.identifier?(organization),
      do:
        {:ok,
         [
           {"v", 1},
           {"kind", "projects"},
           {"organization_id", organization},
           {"after", value["after"]}
         ]},
      else: :error
  end

  defp cursor_pairs(_, _, _), do: :error
  defp encoding([]), do: :ok
  defp encoding(_), do: {:error, :unsupported_content_encoding}
  defp media([]), do: :ok
  defp media(["application/json"]), do: :ok
  defp media(_), do: {:error, :content_type}

  defp empty_body(conn, clock) do
    read_empty(conn, milliseconds(clock) + @read_deadline_ms, clock, 0)
  rescue
    _ -> {:error, :malformed_body, conn}
  catch
    :throw, _ -> {:error, :malformed_body, conn}
  end

  defp read_empty(conn, deadline, clock, count) do
    remaining = deadline - milliseconds(clock)

    if remaining <= 0 or count >= @maximum_reads do
      {:error, :malformed_body, conn}
    else
      case read_body(conn, length: 1, read_length: 65_536, read_timeout: remaining) do
        {tag, bytes, next} when tag in [:ok, :more] and is_binary(bytes) ->
          cond do
            bytes != "" -> {:error, :invalid_request, next}
            milliseconds(clock) >= deadline -> {:error, :malformed_body, next}
            tag == :ok -> {:ok, next}
            true -> read_empty(next, deadline, clock, count + 1)
          end

        _ ->
          {:error, :malformed_body, conn}
      end
    end
  end

  defp milliseconds({module, function, args}) do
    case apply(module, function, args) do
      value when is_integer(value) -> value
      _ -> raise ArgumentError, "invalid workspace monotonic clock"
    end
  end

  @doc false
  def response_headers(conn) do
    conn = %{
      conn
      | resp_headers:
          Enum.reject(conn.resp_headers, fn {name, _} ->
            name in ["www-authenticate", "retry-after", "content-type"]
          end)
    }

    conn = unique_header(conn, "cache-control", "no-store")

    case get_resp_header(conn, "x-request-id") do
      [id] when is_binary(id) and byte_size(id) in 20..200 ->
        if Enum.all?(
             :binary.bin_to_list(id),
             &(&1 in ?A..?Z or &1 in ?a..?z or &1 in ?0..?9 or &1 in [?-, ?., ?_, ?~, ?+, ?/, ?=])
           ),
           do: conn,
           else: unique_header(conn, "x-request-id", Plug.RequestId.generate())

      _ ->
        unique_header(conn, "x-request-id", Plug.RequestId.generate())
    end
  end

  defp unique_header(conn, name, value),
    do:
      %{conn | resp_headers: Enum.reject(conn.resp_headers, fn {key, _} -> key == name end)}
      |> put_resp_header(name, value)

  @doc false
  def reject(conn, reason) do
    {status, code, message} = error(reason)
    conn = response_headers(conn)
    conn = if status == 503, do: put_resp_header(conn, "retry-after", "1"), else: conn

    conn =
      if status == 401,
        do: put_resp_header(conn, "www-authenticate", ~s(Bearer error="invalid_token")),
        else: conn

    [id] = get_resp_header(conn, "x-request-id")

    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(%{error: %{code: code, message: message}, request_id: id}))
    |> halt()
  end

  defp error(:unauthenticated), do: {401, "unauthenticated", "Authentication required."}
  defp error(:permission_denied), do: {403, "permission_denied", "Permission denied."}
  defp error(:not_found), do: {404, "not_found", "Resource not found."}
  defp error(:invalid_request), do: {400, "invalid_request", "Invalid workspace request."}
  defp error(:content_type), do: {400, "content_type", "Content-Type must be application/json."}

  defp error(:unsupported_content_encoding),
    do: {415, "unsupported_content_encoding", "Content encoding is unsupported."}

  defp error(:malformed_body), do: {400, "malformed_body", "Unable to read request body."}

  defp error(_),
    do: {503, "authorization_unavailable", "Authorization unavailable. Retry shortly."}
end
