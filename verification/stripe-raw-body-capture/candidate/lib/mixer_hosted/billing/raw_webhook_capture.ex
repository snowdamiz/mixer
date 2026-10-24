defmodule MixerHosted.Billing.RawWebhookCapture do
  @moduledoc """
  Private, first-consumer exact-byte capture. This module sends no response,
  verifies no signature, and authorizes no event. Every error connection is
  halted and unusable; the caller must dispose of its connection/stream.

  Success deadlines reject late admission, not forcibly terminate adapter work.
  The optional clock implementation is compiled only into the isolated test
  artifact; production compilation has no request-selectable clock or options.
  """
  @max_body 1_048_576
  @read_target 32_768
  @max_reads 64
  @success_ms 5_000
  @read_ms 1_000

  @type reason ::
          :envelope
          | :unsupported_framing
          | :too_large
          | :empty
          | :length_mismatch
          | :read_limit
          | :no_progress
          | :read_deadline
          | :transport_failure
          | :unavailable_state
  @spec capture(Plug.Conn.t()) ::
          {:ok, %{raw_body: binary(), signature_header_values: [binary()]}, Plug.Conn.t()}
          | {:error, reason(), Plug.Conn.t()}
  def capture(%Plug.Conn{} = conn) do
    deadline = now_ms() + @success_ms
    # This component never stores captured bytes on conn. Remove its own prior
    # result slot defensively; it cannot undo another consumer's prior reads.
    conn = %{
      conn
      | private: Map.delete(conn.private, :raw_webhook_capture),
        assigns: Map.delete(conn.assigns, :raw_webhook_capture)
    }

    with {:ok, declared, headers} <- envelope(conn) do
      read(conn, declared, headers, deadline, 0, 0, [])
    else
      {:error, reason} -> failure(reason, conn)
    end
  end

  defp envelope(conn) do
    cond do
      conn.halted or conn.state != :unset ->
        {:error, :unavailable_state}

      conn.method != "POST" or conn.request_path != "/api/v1/webhooks/stripe" or
          conn.query_string != "" ->
        {:error, :envelope}

      headers(conn, "content-encoding") != [] ->
        {:error, :envelope}

      Enum.any?(["trailer", "expect", "upgrade", "te"], &(headers(conn, &1) != [])) ->
        {:error, :unsupported_framing}

      Enum.any?(headers(conn, "connection"), &upgrade?/1) ->
        {:error, :unsupported_framing}

      not media_type?(headers(conn, "content-type")) ->
        {:error, :envelope}

      not signature?(headers(conn, "stripe-signature")) ->
        {:error, :envelope}

      true ->
        with {:ok, declared} <-
               framing(
                 Plug.Conn.get_http_protocol(conn),
                 headers(conn, "content-length"),
                 headers(conn, "transfer-encoding")
               ) do
          {:ok, declared, headers(conn, "stripe-signature")}
        end
    end
  end

  defp headers(conn, name), do: Plug.Conn.get_req_header(conn, name)
  defp signature?([value]) when is_binary(value), do: byte_size(value) in 1..4_096
  defp signature?(_), do: false

  defp upgrade?(value),
    do: value |> :binary.split(",", [:global]) |> Enum.any?(&(token(&1) == "upgrade"))

  defp media_type?([value]) when is_binary(value) and byte_size(value) in 1..128 do
    if ascii?(value) do
      case :binary.split(value, ";", [:global]) do
        [type] ->
          token(type) == "application/json"

        [type, parameter] ->
          token(type) == "application/json" and
            case :binary.split(parameter, "=", [:global]) do
              [name, charset] -> token(name) == "charset" and token(charset) == "utf-8"
              _ -> false
            end

        _ ->
          false
      end
    else
      false
    end
  end

  defp media_type?(_), do: false
  defp ascii?(<<>>), do: true
  defp ascii?(<<byte, rest::binary>>) when byte in 32..126 or byte == 9, do: ascii?(rest)
  defp ascii?(_), do: false
  defp token(value), do: value |> trim_left() |> trim_right() |> String.downcase(:ascii)
  defp trim_left(<<byte, rest::binary>>) when byte in [32, 9], do: trim_left(rest)
  defp trim_left(value), do: value
  defp trim_right(<<>>), do: ""

  defp trim_right(value) do
    if :binary.last(value) in [32, 9],
      do: trim_right(binary_part(value, 0, byte_size(value) - 1)),
      else: value
  end

  defp framing(:"HTTP/1.1", [length], []), do: canonical_length(length)

  defp framing(:"HTTP/1.1", [], [transfer]) do
    if token(transfer) == "chunked", do: {:ok, nil}, else: {:error, :unsupported_framing}
  end

  defp framing(:"HTTP/2", [], []), do: {:ok, nil}
  defp framing(:"HTTP/2", [length], []), do: canonical_length(length)
  defp framing(_, _, _), do: {:error, :unsupported_framing}

  defp canonical_length(<<first, _::binary>> = value)
       when first in ?1..?9 and byte_size(value) <= 7 do
    if digits?(value) do
      length = :erlang.binary_to_integer(value)
      if length <= @max_body, do: {:ok, length}, else: {:error, :too_large}
    else
      {:error, :unsupported_framing}
    end
  end

  defp canonical_length(_), do: {:error, :unsupported_framing}
  defp digits?(<<>>), do: true
  defp digits?(<<byte, rest::binary>>) when byte in ?0..?9, do: digits?(rest)
  defp digits?(_), do: false

  defp read(conn, declared, headers, deadline, calls, size, chunks) do
    remaining_ms = deadline - now_ms()

    remaining =
      min(@max_body - size, if(is_nil(declared), do: @max_body - size, else: declared - size))

    cond do
      remaining_ms <= 0 ->
        failure(:read_deadline, conn)

      calls >= @max_reads ->
        failure(:read_limit, conn)

      remaining <= 0 ->
        failure(:too_large, conn)

      true ->
        target = min(@read_target, remaining)

        result =
          Plug.Conn.read_body(conn,
            length: target,
            read_length: target,
            read_timeout: min(@read_ms, remaining_ms)
          )

        # Transport exceptions propagate unchanged to framework handling. Never
        # inspect/log arbitrary reasons or convert a raised read into success.
        case result do
          {tag, chunk, %Plug.Conn{} = latest} when tag in [:ok, :more] and is_binary(chunk) ->
            accept(tag, chunk, latest, declared, headers, deadline, calls + 1, size, chunks)

          {:error, _opaque_reason} ->
            failure(:transport_failure, conn)

          _ ->
            failure(:unavailable_state, conn)
        end
    end
  end

  defp accept(tag, chunk, conn, declared, headers, deadline, calls, size, chunks) do
    bytes = byte_size(chunk)
    total = size + bytes

    cond do
      now_ms() >= deadline ->
        failure(:read_deadline, conn)

      bytes > @max_body - size ->
        failure(:too_large, conn)

      not is_nil(declared) and bytes > declared - size ->
        failure(:length_mismatch, conn)

      tag == :more and bytes == 0 ->
        failure(:no_progress, conn)

      tag == :more and total == @max_body ->
        failure(:too_large, conn)

      tag == :more and total == declared ->
        failure(:length_mismatch, conn)

      tag == :more ->
        read(conn, declared, headers, deadline, calls, total, [chunk | chunks])

      total == 0 ->
        failure(:empty, conn)

      not is_nil(declared) and total != declared ->
        failure(:length_mismatch, conn)

      true ->
        body = IO.iodata_to_binary(Enum.reverse([chunk | chunks]))
        # Flattening is part of admission and cannot bypass the success deadline.
        if now_ms() < deadline do
          {:ok, %{raw_body: body, signature_header_values: headers}, conn}
        else
          failure(:read_deadline, conn)
        end
    end
  end

  defp failure(reason, conn), do: {:error, reason, Plug.Conn.halt(conn)}

  if Application.compile_env(:mixer_raw_capture_candidate, :test_build, false) do
    defp now_ms, do: MixerRawCapture.TestClock.now_ms()
  else
    defp now_ms, do: System.monotonic_time(:millisecond)
  end
end

