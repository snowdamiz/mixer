defmodule MixerHosted.BrowserAuth.Protocol do
  @moduledoc """
  Bounded browser-login wire and cryptographic primitives; no provider or storage I/O.

  A parsed callback is unclaimed input. A durable owner must check and consume its
  state/browser epoch before exchanging a code or reporting provider rejection.
  Never log requests, generated URLs, cookies, tokens or returned callback values.
  """
  alias MixerHosted.BrowserAuth.Config
  @cookie "__Host-mixer-session"
  @query_keys ~w(state iss code error error_description error_uri)

  @doc "Generates 256 bits using OTP's CSPRNG; there is no caller-supplied random source."
  def random_token, do: :crypto.strong_rand_bytes(32) |> Base.url_encode64(padding: false)

  @doc "Accepts exactly canonical unpadded Base64URL encoding of 32 bytes."
  def token?(value) when is_binary(value) and byte_size(value) == 43 do
    case Base.url_decode64(value, padding: false) do
      {:ok, raw} when byte_size(raw) == 32 -> Base.url_encode64(raw, padding: false) == value
      _ -> false
    end
  end

  def token?(_), do: false

  @doc "SHA-256 lookup digest of a canonical token; plaintext custody is the caller's responsibility."
  def digest(value) do
    if token?(value),
      do: :crypto.hash(:sha256, value) |> Base.url_encode64(padding: false),
      else: {:error, :invalid_token}
  end

  def pkce_challenge(verifier) do
    case digest(verifier) do
      result when is_binary(result) -> {:ok, result}
      error -> error
    end
  end

  @doc "Builds only the fixed OIDC code/S256/query request; accepts no provider choices."
  def authorization_url(
        %Config{
          mode: :configured,
          authorization_endpoint: endpoint,
          client_id: client,
          redirect_uri: redirect
        } = config,
        values
      )
      when is_map(values) and is_binary(endpoint) and is_binary(client) and is_binary(redirect) do
    with true <- map_size(values) == 3,
         %{state: state, nonce: nonce, verifier: verifier} <- values,
         true <- token?(state) and token?(nonce),
         {:ok, challenge} <- pkce_challenge(verifier) do
      query =
        URI.encode_query([
          {"response_type", "code"},
          {"response_mode", "query"},
          {"client_id", config.client_id},
          {"redirect_uri", config.redirect_uri},
          {"scope", "openid mixer.workspace.read"},
          {"state", state},
          {"nonce", nonce},
          {"code_challenge", challenge},
          {"code_challenge_method", "S256"}
        ])

      {:ok, config.authorization_endpoint <> "?" <> query}
    else
      _ -> {:error, :invalid_request}
    end
  end

  def authorization_url(_, _), do: {:error, :invalid_request}

  @doc "max_age must already be capped to the admitted session deadline (pre-auth at most 300)."
  def session_cookie(token, max_age) when is_integer(max_age) and max_age in 1..900 do
    if token?(token),
      do:
        {:ok,
         @cookie <>
           "=" <>
           token <>
           "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=" <> Integer.to_string(max_age)},
      else: {:error, :invalid_token}
  end

  def session_cookie(_, _), do: {:error, :invalid_request}
  def clear_cookie, do: @cookie <> "=; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=0"

  @doc "Reads raw duplicate-preserving headers; rejects any Authorization header or cookie ambiguity."
  def parse_session_cookie(headers) do
    with {:ok, selected} <- headers(headers),
         {:ok, cookie} <- cookies(Map.get(selected, "cookie")) do
      {:ok, cookie}
    else
      _ -> {:error, :invalid_request}
    end
  end

  @doc "Validates exact Origin and a canonical synchronizer token using OTP constant-time comparison."
  def verify_csrf(%Config{mode: :configured, public_origin: origin}, raw_headers, expected)
      when is_binary(origin) do
    with true <- token?(expected),
         {:ok, selected} <- headers(raw_headers),
         ^origin <- Map.get(selected, "origin"),
         actual when is_binary(actual) <- Map.get(selected, "x-mixer-csrf"),
         true <- token?(actual),
         true <- :crypto.hash_equals(expected, actual),
         {:ok, cookie} when is_binary(cookie) <- cookies(Map.get(selected, "cookie")) do
      :ok
    else
      _ -> {:error, :invalid_csrf}
    end
  end

  def verify_csrf(_, _, _), do: {:error, :invalid_csrf}

  @doc "Parses only GET-query callback contents; caller must separately enforce method and exact route."
  def parse_callback(config, query, body \\ "")

  def parse_callback(%Config{mode: :configured, issuer: issuer}, query, "")
      when is_binary(issuer) and is_binary(query) and byte_size(query) in 1..8192 do
    with {:ok, fields} <- query_fields(query, %{}, 0),
         state when is_binary(state) <- fields["state"],
         true <- token?(state),
         ^issuer <- fields["iss"],
         {:ok, outcome} <- outcome(fields) do
      {:ok, %{state: state, issuer: issuer, outcome: outcome}}
    else
      _ -> {:error, :invalid_callback}
    end
  end

  def parse_callback(_, _, _), do: {:error, :invalid_callback}

  # At most 64 raw header pairs and 16 KiB are walked once. Sensitive header
  # names are case-insensitive; duplicates are rejected before any projection.
  defp headers(value), do: headers(value, %{}, 0, 0)
  defp headers([], selected, _, _), do: {:ok, selected}

  defp headers([{name, value} | rest], selected, count, bytes)
       when is_binary(name) and is_binary(value) and count < 64 and
              byte_size(name) in 1..128 and byte_size(value) <= 8192 do
    size = bytes + byte_size(name) + byte_size(value)

    with true <- size <= 16_384,
         true <- ascii?(name, &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 == ?-)),
         true <- ascii?(value, &(&1 in 32..126)),
         lower = String.downcase(name),
         false <- lower == "authorization",
         false <- Map.has_key?(selected, lower) do
      headers(rest, Map.put(selected, lower, value), count + 1, size)
    else
      _ -> :error
    end
  end

  defp headers(_, _, _, _), do: :error

  defp cookies(nil), do: {:ok, nil}
  defp cookies(value) when byte_size(value) in 1..8192, do: cookie_pairs(value, %{}, 0)
  defp cookies(_), do: :error

  defp cookie_pairs(raw, seen, count) when count < 32 do
    {pair, rest} = split_first(raw, ";")
    pair = String.trim(pair, " ")

    with {name, value} when is_binary(value) <- split_first(pair, "="),
         true <- name != "" and byte_size(name) <= 128,
         true <- ascii?(name, &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in ~c"-_")),
         false <- Map.has_key?(seen, name),
         true <- cookie_octets?(value),
         true <- name != @cookie or token?(value) do
      next = Map.put(seen, name, value)

      if rest == nil,
        do: {:ok, Map.get(next, @cookie)},
        else: cookie_pairs(rest, next, count + 1)
    else
      _ -> :error
    end
  end

  defp cookie_pairs(_, _, _), do: :error

  defp cookie_octets?(value),
    do:
      ascii?(
        value,
        &(&1 == 0x21 or &1 in 0x23..0x2B or &1 in 0x2D..0x3A or &1 in 0x3C..0x5B or
            &1 in 0x5D..0x7E)
      )

  # Raw key names are exact ASCII: encoded aliases never become a recognized
  # key. Values have exactly one bounded form decode. Canonical state additionally
  # forbids percent/plus encoding; issuer is compared byte-for-byte after decode.
  defp query_fields(raw, fields, count) when count < 6 do
    {pair, rest} = split_first(raw, "&")

    with {name, encoded} when is_binary(encoded) <- split_first(pair, "="),
         true <- name in @query_keys,
         false <- Map.has_key?(fields, name),
         true <- byte_size(encoded) <= encoded_limit(name),
         true <- name != "state" or token?(encoded),
         {:ok, decoded} <- form_decode(encoded, [], 0, decoded_limit(name)),
         true <- decoded != "" do
      next = Map.put(fields, name, decoded)

      if rest == nil,
        do: {:ok, next},
        else: query_fields(rest, next, count + 1)
    else
      _ -> :error
    end
  end

  defp query_fields(_, _, _), do: :error
  defp decoded_limit("state"), do: 43
  defp decoded_limit("code"), do: 4096
  defp decoded_limit("iss"), do: 2048
  defp decoded_limit("error"), do: 128
  defp decoded_limit("error_description"), do: 1024
  defp decoded_limit("error_uri"), do: 2048
  defp encoded_limit(name), do: decoded_limit(name) * 3

  defp form_decode(<<>>, acc, _, _), do: {:ok, acc |> Enum.reverse() |> :erlang.list_to_binary()}
  defp form_decode(_, _, count, limit) when count >= limit, do: :error

  defp form_decode(<<?%, a, b, rest::binary>>, acc, count, limit) do
    with x when is_integer(x) <- hex(a),
         y when is_integer(y) <- hex(b),
         byte = x * 16 + y,
         true <- byte in 32..126 do
      form_decode(rest, [byte | acc], count + 1, limit)
    else
      _ -> :error
    end
  end

  defp form_decode(<<?%, _::binary>>, _, _, _), do: :error

  defp form_decode(<<?+, rest::binary>>, acc, count, limit),
    do: form_decode(rest, [32 | acc], count + 1, limit)

  defp form_decode(<<byte, rest::binary>>, acc, count, limit)
       when byte in 0x21..0x7E and byte not in ~c"#;\\\"<>" do
    form_decode(rest, [byte | acc], count + 1, limit)
  end

  defp form_decode(_, _, _, _), do: :error
  defp hex(byte) when byte in ?0..?9, do: byte - ?0
  defp hex(byte) when byte in ?a..?f, do: byte - ?a + 10
  defp hex(byte) when byte in ?A..?F, do: byte - ?A + 10
  defp hex(_), do: :error

  defp outcome(%{"code" => code} = fields) when map_size(fields) == 3 do
    if Map.keys(fields) |> Enum.sort() == ~w(code iss state),
      do: {:ok, {:code, code}},
      else: :error
  end

  defp outcome(%{"error" => error} = fields) do
    if not Map.has_key?(fields, "code") and map_size(fields) in 3..5 and
         ascii?(error, &(&1 == 0x20 or &1 == 0x21 or &1 in 0x23..0x5B or &1 in 0x5D..0x7E)),
       do: {:ok, {:error, :provider_rejected}},
       else: :error
  end

  defp outcome(_), do: :error

  defp split_first(raw, separator) do
    case :binary.match(raw, separator) do
      {position, 1} ->
        {binary_part(raw, 0, position),
         binary_part(raw, position + 1, byte_size(raw) - position - 1)}

      :nomatch ->
        {raw, nil}
    end
  end

  defp ascii?(<<>>, _), do: true
  defp ascii?(<<byte, rest::binary>>, check), do: check.(byte) and ascii?(rest, check)
end
