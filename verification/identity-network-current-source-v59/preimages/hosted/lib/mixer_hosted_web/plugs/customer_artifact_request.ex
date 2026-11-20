defmodule MixerHostedWeb.Plugs.CustomerArtifactRequest do
  @moduledoc """
  Closed transport admission after BearerIdentity and before customer artifact effects.

  The operation and monotonic clock are trusted Plug initialization inputs. HTTP
  fields never select dependencies, actor authority, or an audit request ID.
  """
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactJSON

  @maximum_body 6_291_456
  @maximum_cursor 9_007_199_254_740_991
  @read_length 65_536
  @maximum_reads 128
  @read_deadline_ms 15_000
  @scopes %{
    upload: "mixer.artifact.upload",
    read: "mixer.artifact.read",
    audit: "mixer.audit.read"
  }

  @impl true
  def init(operation) when operation in [:upload, :read, :audit],
    do: init(operation: operation)

  def init(opts) when is_list(opts) do
    unless Keyword.keyword?(opts) and Enum.all?(Keyword.keys(opts), &(&1 in [:operation, :clock])) and
             length(Keyword.keys(opts)) == length(Enum.uniq(Keyword.keys(opts))) do
      raise ArgumentError, "invalid customer artifact request options"
    end

    operation = Keyword.get(opts, :operation)
    clock = Keyword.get(opts, :clock, {System, :monotonic_time, [:millisecond]})

    unless operation in [:upload, :read, :audit] and valid_clock?(clock),
      do: raise(ArgumentError, "invalid customer artifact request dependencies")

    %{operation: operation, clock: clock}
  end

  def init(_), do: raise(ArgumentError, "invalid customer artifact request options")

  @impl true
  def call(conn, %{operation: operation, clock: clock}) do
    conn = response_headers(conn)

    with :ok <- identity(conn.assigns[:verified_identity], operation),
         :ok <- method(conn.method, operation),
         {:ok, route, digest} <- route(conn.path_params, operation),
         :ok <- canonical_path(conn.request_path, route, digest, operation),
         {:ok, page} <- query(conn.query_string, operation),
         :ok <- encoding(get_req_header(conn, "content-encoding")),
         :ok <- media(get_req_header(conn, "content-type"), operation),
         {:ok, key, reason} <- mutation_headers(conn, operation),
         {:ok, bytes, conn} <- body(conn, operation, clock),
         :ok <- envelope(bytes, operation) do
      assign(conn, :customer_artifact_request, %{
        route: route,
        digest: digest,
        key: key,
        bytes: bytes,
        page: page,
        metadata: %{reason: reason, source_ip: source_ip(conn.remote_ip)}
      })
    else
      {:error, reason, conn} -> reject(conn, reason)
      {:error, reason} -> reject(conn, reason)
    end
  end

  defp valid_clock?({module, function, args})
       when is_atom(module) and is_atom(function) and is_list(args),
       do: Code.ensure_loaded?(module) and function_exported?(module, function, length(args))

  defp valid_clock?(_), do: false

  defp identity(%VerifiedIdentity{identity_class: :human, scopes: scopes}, operation)
       when is_list(scopes) do
    if @scopes[operation] in scopes, do: :ok, else: {:error, :permission_denied}
  end

  defp identity(%VerifiedIdentity{}, _), do: {:error, :permission_denied}
  defp identity(_, _), do: {:error, :unauthenticated}
  defp method("PUT", :upload), do: :ok

  defp method(method, operation) when method in ["GET", "HEAD"] and operation in [:read, :audit],
    do: :ok

  defp method(_, _), do: {:error, :not_found}

  defp route(params, operation) when is_map(params) do
    organization = params["organization_id"]
    project = params["project_id"]
    digest = params["manifest_sha256"]

    if identifier?(organization) and identifier?(project) and
         (operation == :audit or digest?(digest)) do
      {:ok, %{organization_id: organization, project_id: project}, digest}
    else
      {:error, :invalid_request}
    end
  end

  defp route(_, _), do: {:error, :invalid_request}

  defp canonical_path(path, route, digest, operation)
       when is_binary(path) and byte_size(path) <= 512 do
    base = "/v3/orgs/" <> route.organization_id <> "/projects/" <> route.project_id
    expected = if operation == :audit, do: base <> "/audit", else: base <> "/artifacts/" <> digest
    if path == expected, do: :ok, else: {:error, :invalid_path}
  end

  defp canonical_path(_, _, _, _), do: {:error, :invalid_path}

  defp identifier?(value) when is_binary(value) and byte_size(value) in 1..128,
    do: identifier_bytes?(value)

  defp identifier?(_), do: false
  defp identifier_bytes?(<<>>), do: true

  defp identifier_bytes?(<<c, rest::binary>>)
       when c in ?A..?Z or c in ?a..?z or c in ?0..?9 or c in [?., ?_, ?-],
       do: identifier_bytes?(rest)

  defp identifier_bytes?(_), do: false

  defp digest?(value) when is_binary(value) and byte_size(value) == 64,
    do: Enum.all?(:binary.bin_to_list(value), &(&1 in ?0..?9 or &1 in ?a..?f))

  defp digest?(_), do: false

  defp query("", _operation), do: {:ok, %{after: 0, limit: 100}}

  defp query(query, :audit) when is_binary(query) and byte_size(query) <= 8_192 do
    fields = :binary.split(query, "&", [:global])

    if length(fields) <= 2 do
      Enum.reduce_while(fields, {:ok, %{}}, fn field, {:ok, page} ->
        case :binary.split(field, "=") do
          [name, value] -> query_field(name, value, page)
          [name] -> query_field(name, "", page)
        end
      end)
      |> case do
        {:ok, page} -> {:ok, Map.merge(%{after: 0, limit: 100}, page)}
        _ -> {:error, :invalid_request}
      end
    else
      {:error, :invalid_request}
    end
  end

  defp query(_, _), do: {:error, :invalid_request}

  defp query_field(raw_name, raw_value, page) do
    with {:ok, name} <- decode(raw_name),
         {:ok, value} <- decode(raw_value),
         key when key in [:after, :limit] <- query_key(name),
         false <- Map.has_key?(page, key),
         {:ok, value} <- decimal(value, key) do
      {:cont, {:ok, Map.put(page, key, value)}}
    else
      _ -> {:halt, {:error, :invalid_request}}
    end
  end

  defp decode(value) do
    # URI.decode_www_form/1 leaves malformed escapes unchanged. The decimal/key
    # checks then reject those bytes, while one decode exposes encoded duplicates.
    {:ok, URI.decode_www_form(value)}
  rescue
    _ -> {:error, :invalid_request}
  end

  defp query_key("after"), do: :after
  defp query_key("limit"), do: :limit
  defp query_key(_), do: :invalid
  defp decimal("", :after), do: {:ok, 0}
  defp decimal("", :limit), do: {:ok, 100}

  defp decimal(value, key) when byte_size(value) in 1..16 do
    if Enum.all?(:binary.bin_to_list(value), &(&1 in ?0..?9)) do
      number = String.to_integer(value)

      if (key == :after and number <= @maximum_cursor) or
           (key == :limit and number in 1..100),
         do: {:ok, number},
         else: {:error, :invalid_request}
    else
      {:error, :invalid_request}
    end
  end

  defp decimal(_, _), do: {:error, :invalid_request}

  defp encoding([]), do: :ok
  defp encoding(_), do: {:error, :unsupported_content_encoding}
  defp media(["application/json"], _), do: :ok
  defp media([], operation) when operation in [:read, :audit], do: :ok
  defp media(_, _), do: {:error, :content_type}

  defp mutation_headers(conn, :upload) do
    with [key] <- get_req_header(conn, "idempotency-key"),
         true <- identifier?(key) do
      case get_req_header(conn, "x-mixer-reason") do
        [] ->
          {:ok, key, "local development operation"}

        [""] ->
          {:ok, key, "local development operation"}

        [reason] when is_binary(reason) and byte_size(reason) <= 512 ->
          if String.valid?(reason), do: {:ok, key, reason}, else: {:error, :invalid_reason}

        _ ->
          {:error, :invalid_reason}
      end
    else
      _ -> {:error, :idempotency_required}
    end
  end

  defp mutation_headers(_, _), do: {:ok, nil, ""}

  defp body(conn, operation, clock) do
    maximum = if operation == :upload, do: @maximum_body, else: 0
    deadline = milliseconds(clock) + @read_deadline_ms
    read(conn, maximum, deadline, clock, [], 0, 0)
  rescue
    _ -> {:error, :malformed_body, conn}
  catch
    :throw, _ -> {:error, :malformed_body, conn}
  end

  defp read(conn, maximum, deadline, clock, chunks, size, count) do
    remaining = deadline - milliseconds(clock)

    if remaining <= 0 or count >= @maximum_reads do
      {:error, :malformed_body, conn}
    else
      result =
        read_body(conn,
          length: min(@read_length, maximum - size + 1),
          read_length: @read_length,
          read_timeout: remaining
        )

      case result do
        {tag, bytes, next} when tag in [:ok, :more] and is_binary(bytes) ->
          total = size + byte_size(bytes)

          cond do
            total > maximum ->
              reason = if maximum == 0, do: :invalid_request, else: :body_too_large
              {:error, reason, next}

            milliseconds(clock) >= deadline ->
              {:error, :malformed_body, next}

            tag == :ok ->
              {:ok, IO.iodata_to_binary(Enum.reverse([bytes | chunks])), next}

            true ->
              read(next, maximum, deadline, clock, [bytes | chunks], total, count + 1)
          end

        _ ->
          {:error, :malformed_body, conn}
      end
    end
  end

  defp milliseconds({module, function, args}) do
    case apply(module, function, args) do
      value when is_integer(value) -> value
      _ -> raise ArgumentError, "invalid monotonic clock"
    end
  end

  defp envelope(bytes, :upload) do
    case ArtifactJSON.decode(bytes, @maximum_body) do
      {:ok, value, _, _} when is_map(value) and map_size(value) == 2 ->
        if is_map(value["signed_manifest"]) and not is_struct(value["signed_manifest"]) and
             is_binary(value["payload"]), do: :ok, else: {:error, :invalid_json}

      _ ->
        {:error, :invalid_json}
    end
  end

  defp envelope(_, _), do: :ok

  defp source_ip(address) when is_tuple(address) do
    case :inet.ntoa(address) do
      value when is_list(value) -> to_string(value)
      _ -> nil
    end
  rescue
    _ -> nil
  end

  defp source_ip(_), do: nil

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
      [id] when is_binary(id) and byte_size(id) in 20..200 -> conn
      _ -> unique_header(conn, "x-request-id", Plug.RequestId.generate())
    end
  end

  @doc false
  def reject(conn, reason) do
    {status, code, message} = error(reason)
    conn = response_headers(conn)

    conn = %{
      conn
      | resp_headers:
          Enum.reject(conn.resp_headers, fn {name, _} ->
            name in ["www-authenticate", "retry-after", "content-type"]
          end)
    }

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

  defp unique_header(conn, name, value) do
    %{conn | resp_headers: Enum.reject(conn.resp_headers, fn {key, _} -> key == name end)}
    |> put_resp_header(name, value)
  end

  defp error(:unauthenticated), do: {401, "unauthenticated", "Authentication required."}
  defp error(:permission_denied), do: {403, "permission_denied", "Permission denied."}
  defp error(:not_found), do: {404, "not_found", "Resource not found."}

  defp error(:idempotency_required),
    do: {400, "idempotency_required", "A valid idempotency key is required."}

  defp error(:invalid_reason), do: {400, "invalid_reason", "Invalid operation reason."}
  defp error(:content_type), do: {400, "content_type", "Content-Type must be application/json."}

  defp error(:unsupported_content_encoding),
    do: {415, "unsupported_content_encoding", "Content encoding is unsupported."}

  defp error(:malformed_body), do: {400, "malformed_body", "Unable to read request body."}
  defp error(:body_too_large), do: {413, "body_too_large", "Request body exceeds the byte limit."}
  defp error(:invalid_json), do: {400, "invalid_json", "Invalid artifact JSON envelope."}
  defp error(:artifact_invalid), do: {422, "artifact_invalid", "Artifact admission rejected."}

  defp error(:digest_mismatch),
    do: {422, "digest_mismatch", "Artifact identity differs from route."}

  defp error(:immutable_conflict), do: {409, "immutable_conflict", "Immutable artifact conflict."}
  defp error(:idempotency_conflict), do: {409, "idempotency_conflict", "Idempotency conflict."}
  defp error(:conflict), do: {409, "conflict", "Operation conflict."}

  defp error(:authorization_unavailable),
    do: {503, "authorization_unavailable", "Authorization unavailable. Retry shortly."}

  defp error(:invalid_path), do: {400, "invalid_path", "Invalid artifact path."}
  defp error(:invalid_request), do: {400, "invalid_request", "Invalid artifact request."}
  defp error(_), do: {503, "storage_unavailable", "Artifact storage unavailable. Retry shortly."}
end
