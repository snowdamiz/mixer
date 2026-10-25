defmodule MixerHostedWeb.Plugs.BearerIdentity do
  @moduledoc """
  Header-only identity admission for a JSON-oriented protected HTTP pipeline.

  This plug assigns only `:verified_identity`; it grants no application authority.
  It never reads a request body, fetches parameters, or converts cookies to tokens.
  See `docs/hosted-bearer-identity-transport.md` for the bounded query/form policy.

  `:verifier` (a `MixerHosted.Identity.Verifier` module) and `:clock` (a zero-input
  MFA) are trusted pipeline configuration, validated by `init/1`. The production
  defaults are `ConfiguredVerifier` and the actual Unix clock. HTTP input cannot
  select either dependency.
  """

  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.Identity.{ConfiguredVerifier, VerifiedIdentity}

  @impl true
  def init(opts) do
    unless Keyword.keyword?(opts) and
             Enum.all?(Keyword.keys(opts), &(&1 in [:verifier, :clock])) and
             length(Keyword.keys(opts)) == length(Enum.uniq(Keyword.keys(opts))) do
      raise ArgumentError, "invalid bearer identity options"
    end

    verifier = Keyword.get(opts, :verifier, ConfiguredVerifier)
    clock = Keyword.get(opts, :clock, {System, :system_time, [:second]})

    unless is_atom(verifier) and compiled?(verifier) and
             function_exported?(verifier, :authenticate, 2) and valid_clock?(clock) do
      raise ArgumentError, "invalid bearer identity dependencies"
    end

    %{verifier: verifier, clock: clock}
  end

  defp valid_clock?({module, function, args})
       when is_atom(module) and is_atom(function) and is_list(args) do
    compiled?(module) and function_exported?(module, function, length(args))
  end

  defp valid_clock?(_), do: false

  # Plug calls init/1 while compiling its router. A sibling application module
  # may still be compiling; waiting records that dependency without weakening
  # the export checks or accepting a missing configured implementation.
  defp compiled?(module), do: match?({:module, ^module}, Code.ensure_compiled(module))

  @impl true
  def call(conn, %{verifier: verifier, clock: clock}) do
    conn =
      %{conn | assigns: Map.delete(conn.assigns, :verified_identity)}
      |> put_unique_resp_header("cache-control", "no-store")
      |> request_id()

    with :ok <- query_policy(conn.query_string),
         :ok <- content_type_policy(get_req_header(conn, "content-type")),
         {:ok, token} <- credential(get_req_header(conn, "authorization")) do
      case authenticate(verifier, clock, token) do
        {:ok, %VerifiedIdentity{} = identity} -> assign(conn, :verified_identity, identity)
        {:error, :unauthenticated} -> reject(conn, :invalid_token)
        _ -> reject(conn, :identity_unavailable)
      end
    else
      :missing -> reject(conn, :missing)
      _ -> reject(conn, :invalid_request)
    end
  end

  defp authenticate(verifier, {module, function, args}, token) do
    now = apply(module, function, args)

    if is_integer(now) and now in 0..9_007_199_254_740_991,
      do: verifier.authenticate(token, now),
      else: {:error, :identity_unavailable}
  rescue
    _exception -> {:error, :identity_unavailable}
  catch
    :throw, _reason -> {:error, :identity_unavailable}
  end

  defp credential([]), do: :missing

  defp credential([value]) when is_binary(value) and byte_size(value) <= 4_096 do
    case value do
      <<scheme::binary-size(6), " ", rest::binary>> ->
        token = skip_spaces(rest)

        if downcase_ascii(scheme) == "bearer" and byte_size(token) <= 4_089 and
             token?(token, false),
           do: {:ok, token},
           else: :invalid

      _ ->
        :invalid
    end
  end

  defp credential(_), do: :invalid
  defp skip_spaces(<<" ", rest::binary>>), do: skip_spaces(rest)
  defp skip_spaces(rest), do: rest

  defp token?(<<>>, seen), do: seen
  defp token?(<<?=, rest::binary>>, true), do: padding?(rest)

  defp token?(<<char, rest::binary>>, _seen)
       when char in ?A..?Z or char in ?a..?z or char in ?0..?9 or
              char in [?-, ?., ?_, ?~, ?+, ?/],
       do: token?(rest, true)

  defp token?(_, _), do: false
  defp padding?(<<>>), do: true
  defp padding?(<<?=, rest::binary>>), do: padding?(rest)
  defp padding?(_), do: false

  defp downcase_ascii(value) do
    for <<char <- value>>, into: <<>> do
      if char in ?A..?Z, do: <<char + 32>>, else: <<char>>
    end
  end

  # Only names are decoded, without constructing a query parameter map. All
  # scans and decoded names are bounded before reaching the verifier.
  defp query_policy(query) when is_binary(query) and byte_size(query) <= 8_192,
    do: query_fields(query, 0)

  defp query_policy(_), do: :invalid
  defp query_fields(<<>>, _count), do: :ok
  defp query_fields(_query, 128), do: :invalid

  defp query_fields(query, count) do
    {field, rest} =
      case :binary.split(query, "&") do
        [field] -> {field, ""}
        [field, rest] -> {field, rest}
      end

    name = hd(:binary.split(field, "="))

    with {:ok, name} <- query_name(name, [], 0),
         true <- String.valid?(name),
         false <- name == "access_token" or String.starts_with?(name, "access_token[") do
      query_fields(rest, count + 1)
    else
      _ -> :invalid
    end
  end

  defp query_name(<<>>, acc, _size), do: {:ok, acc |> Enum.reverse() |> :erlang.list_to_binary()}
  defp query_name(_name, _acc, 256), do: :invalid

  defp query_name(<<?%, high, low, rest::binary>>, acc, size) do
    with h when is_integer(h) <- hex(high),
         l when is_integer(l) <- hex(low),
         byte = h * 16 + l,
         true <- byte >= 32 and byte != 127 do
      query_name(rest, [byte | acc], size + 1)
    else
      _ -> :invalid
    end
  end

  defp query_name(<<?%, _::binary>>, _acc, _size), do: :invalid
  defp query_name(<<?+, rest::binary>>, acc, size), do: query_name(rest, [32 | acc], size + 1)

  defp query_name(<<byte, rest::binary>>, acc, size) when byte >= 32 and byte != 127,
    do: query_name(rest, [byte | acc], size + 1)

  defp query_name(_, _, _), do: :invalid
  defp hex(char) when char in ?0..?9, do: char - ?0
  defp hex(char) when char in ?A..?F, do: char - ?A + 10
  defp hex(char) when char in ?a..?f, do: char - ?a + 10
  defp hex(_), do: :invalid

  defp content_type_policy([]), do: :ok

  defp content_type_policy([value]) when is_binary(value) and byte_size(value) <= 1_024 do
    # Plug deliberately drops malformed parameters. Validate the entire bounded
    # suffix before using its media-type result, including legal quoted commas.
    parameters =
      case :binary.split(value, ";") do
        [_media] -> ""
        [_media, rest] -> ";" <> rest
      end

    if header_bytes?(value) and parameters?(parameters) do
      case Plug.Conn.Utils.content_type(value) do
        {:ok, "application", "x-www-form-urlencoded", _params} -> :invalid
        {:ok, type, subtype, _params} when type != "" and subtype != "" -> :ok
        _ -> :invalid
      end
    else
      :invalid
    end
  end

  defp content_type_policy(_), do: :invalid

  defp header_bytes?(<<>>), do: true

  defp header_bytes?(<<byte, rest::binary>>) when byte == 9 or byte in 32..126 or byte >= 128,
    do: header_bytes?(rest)

  defp header_bytes?(_), do: false

  defp skip_ows(<<byte, rest::binary>>) when byte in [9, 32], do: skip_ows(rest)
  defp skip_ows(rest), do: rest

  defp parameters?(value), do: parameter_tail?(skip_ows(value))
  defp parameter_tail?(<<>>), do: true

  defp parameter_tail?(<<?;, rest::binary>>) do
    case skip_ows(rest) do
      <<>> ->
        true

      <<?;, _::binary>> = rest ->
        parameter_tail?(rest)

      rest ->
        with {:ok, <<?=, rest::binary>>} <- parameter_token(rest, false),
             {:ok, rest} <- parameter_value(rest) do
          parameters?(rest)
        else
          _ -> false
        end
    end
  end

  defp parameter_tail?(_), do: false

  defp parameter_token(<<byte, rest::binary>>, _seen)
       when byte in ?A..?Z or byte in ?a..?z or byte in ?0..?9 or
              byte in [?!, ?#, ?$, ?%, ?&, ?', ?*, ?+, ?-, ?., ?^, ?_, ?`, ?|, ?~],
       do: parameter_token(rest, true)

  defp parameter_token(rest, true), do: {:ok, rest}
  defp parameter_token(_, false), do: :invalid

  defp parameter_value(<<?", rest::binary>>), do: quoted_parameter(rest)
  defp parameter_value(rest), do: parameter_token(rest, false)
  defp quoted_parameter(<<?", rest::binary>>), do: {:ok, rest}

  defp quoted_parameter(<<?\\, byte, rest::binary>>)
       when byte == 9 or byte in 32..126 or byte >= 128,
       do: quoted_parameter(rest)

  defp quoted_parameter(<<byte, rest::binary>>)
       when byte in [9, 32, 33] or byte in 35..91 or byte in 93..126 or byte >= 128,
       do: quoted_parameter(rest)

  defp quoted_parameter(_), do: :invalid

  # Plug's single-header helpers replace/delete only the first occurrence.
  defp delete_all_resp_headers(conn, key),
    do: %{conn | resp_headers: Enum.reject(conn.resp_headers, fn {name, _} -> name == key end)}

  defp put_unique_resp_header(conn, key, value),
    do: conn |> delete_all_resp_headers(key) |> put_resp_header(key, value)

  defp request_id(conn) do
    id =
      case get_resp_header(conn, "x-request-id") do
        [id] when is_binary(id) and byte_size(id) in 20..200 ->
          if safe_request_id?(id), do: id, else: Plug.RequestId.generate()

        _ ->
          Plug.RequestId.generate()
      end

    put_unique_resp_header(conn, "x-request-id", id)
  end

  defp safe_request_id?(id) do
    Enum.all?(:binary.bin_to_list(id), fn char ->
      char in ?A..?Z or char in ?a..?z or char in ?0..?9 or char in [?-, ?., ?_, ?~, ?+, ?/, ?=]
    end)
  end

  defp reject(conn, reason) do
    {status, code, message, challenge} =
      case reason do
        :missing ->
          {401, "unauthenticated", "Authentication required.", "Bearer"}

        :invalid_token ->
          {401, "unauthenticated", "Authentication required.", ~s(Bearer error="invalid_token")}

        :invalid_request ->
          {400, "invalid_request", "Invalid authentication request.",
           ~s(Bearer error="invalid_request")}

        :identity_unavailable ->
          {503, "identity_unavailable", "Identity verification unavailable. Retry shortly.", nil}
      end

    conn =
      conn
      |> delete_all_resp_headers("www-authenticate")
      |> delete_all_resp_headers("retry-after")

    conn = if challenge, do: put_resp_header(conn, "www-authenticate", challenge), else: conn
    conn = if status == 503, do: put_resp_header(conn, "retry-after", "1"), else: conn
    [id] = get_resp_header(conn, "x-request-id")

    conn
    |> delete_all_resp_headers("content-type")
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(%{error: %{code: code, message: message}, request_id: id}))
    |> halt()
  end
end
