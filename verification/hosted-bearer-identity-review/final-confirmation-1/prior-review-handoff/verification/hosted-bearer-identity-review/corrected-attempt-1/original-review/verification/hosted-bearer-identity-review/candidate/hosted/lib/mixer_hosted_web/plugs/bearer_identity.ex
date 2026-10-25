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

    unless is_atom(verifier) and Code.ensure_loaded?(verifier) and
             function_exported?(verifier, :authenticate, 2) and valid_clock?(clock) do
      raise ArgumentError, "invalid bearer identity dependencies"
    end

    %{verifier: verifier, clock: clock}
  end

  defp valid_clock?({module, function, args})
       when is_atom(module) and is_atom(function) and is_list(args) do
    Code.ensure_loaded?(module) and function_exported?(module, function, length(args))
  end

  defp valid_clock?(_), do: false

  @impl true
  def call(conn, %{verifier: verifier, clock: clock}) do
    conn =
      %{conn | assigns: Map.delete(conn.assigns, :verified_identity)}
      |> put_resp_header("cache-control", "no-store")
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
    case Plug.Conn.Utils.content_type(value) do
      {:ok, "application", "x-www-form-urlencoded", _params} -> :invalid
      {:ok, _, _, _params} -> :ok
      _ -> :invalid
    end
  end

  defp content_type_policy(_), do: :invalid

  defp request_id(conn) do
    id =
      case get_resp_header(conn, "x-request-id") do
        [id] when is_binary(id) and byte_size(id) in 20..200 ->
          if safe_request_id?(id), do: id, else: Plug.RequestId.generate()

        _ ->
          Plug.RequestId.generate()
      end

    put_resp_header(conn, "x-request-id", id)
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

    conn = conn |> delete_resp_header("www-authenticate") |> delete_resp_header("retry-after")
    conn = if challenge, do: put_resp_header(conn, "www-authenticate", challenge), else: conn
    conn = if status == 503, do: put_resp_header(conn, "retry-after", "1"), else: conn
    [id] = get_resp_header(conn, "x-request-id")

    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(%{error: %{code: code, message: message}, request_id: id}))
    |> halt()
  end
end
