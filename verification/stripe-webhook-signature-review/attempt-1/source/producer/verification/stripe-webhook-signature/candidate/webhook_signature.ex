defmodule MixerHosted.Billing.WebhookSignature do
  @moduledoc """
  Bounded Stripe v1 signature and freshness verification over unchanged bytes.

  This pure boundary does not parse an event, deduplicate delivery, acknowledge
  HTTP, grant tenant permission or modify billing state. Callers must supply
  current endpoint-specific secrets and a trusted UTC clock on every call.
  """

  @max_time 253_402_300_799
  @tolerance 300
  @max_body 1_048_576
  @max_header 4_096
  @max_fields 32
  @max_signatures 8

  @spec verify(term(), term(), term(), term()) ::
          :ok | {:error, :invalid_signature | :verification_unavailable}
  def verify(body, headers, secrets, now) do
    if valid_secrets?(secrets) and is_integer(now) and now >= 0 and now <= @max_time do
      verify_configured(body, headers, secrets, now)
    else
      {:error, :verification_unavailable}
    end
  rescue
    # Crypto/toolchain failure must not become an authentication success.
    _ -> {:error, :verification_unavailable}
  catch
    _, _ -> {:error, :verification_unavailable}
  end

  defp valid_secrets?([one]), do: valid_secret?(one)
  defp valid_secrets?([one, two]), do: valid_secret?(one) and valid_secret?(two) and one != two
  defp valid_secrets?(_), do: false
  defp valid_secret?(secret), do: is_binary(secret) and byte_size(secret) in 16..256

  defp verify_configured(body, [header], secrets, now)
       when is_binary(body) and byte_size(body) in 1..@max_body and
              is_binary(header) and byte_size(header) in 1..@max_header do
    with true <- valid_header_bytes?(header),
         {:ok, timestamp_text, timestamp, signatures} <- parse_header(header),
         true <- abs(now - timestamp) <= @tolerance,
         true <- matches?(body, timestamp_text, signatures, secrets) do
      :ok
    else
      _ -> {:error, :invalid_signature}
    end
  end

  defp verify_configured(_, _, _, _), do: {:error, :invalid_signature}

  defp valid_header_bytes?(<<>>), do: true

  defp valid_header_bytes?(<<byte, rest::binary>>) when byte in 32..126 or byte == 9,
    do: valid_header_bytes?(rest)

  defp valid_header_bytes?(_), do: false

  defp parse_header(header) do
    fields = :binary.split(header, ",", [:global])

    if length(fields) <= @max_fields do
      case Enum.reduce_while(fields, {nil, []}, &parse_field/2) do
        {{text, timestamp}, signatures} when signatures != [] ->
          {:ok, text, timestamp, signatures}

        _ ->
          :error
      end
    else
      :error
    end
  end

  defp parse_field(field, {timestamp, signatures}) do
    case :binary.split(trim_field(field), "=") do
      ["t", text] when is_nil(timestamp) ->
        case timestamp(text) do
          {:ok, value} -> {:cont, {{text, value}, signatures}}
          :error -> {:halt, :error}
        end

      ["v1", signature] when byte_size(signature) == 64 ->
        case Base.decode16(signature, case: :mixed) do
          {:ok, bytes} when length(signatures) < @max_signatures ->
            {:cont, {timestamp, [bytes | signatures]}}

          _ ->
            {:halt, :error}
        end

      [name, value] when name not in ["t", "v1", ""] and value != "" ->
        {:cont, {timestamp, signatures}}

      _ ->
        {:halt, :error}
    end
  end

  defp trim_field(field) do
    trimmed = trim_start(field)
    trim_end(trimmed, byte_size(trimmed))
  end

  defp trim_start(<<byte, rest::binary>>) when byte in [32, 9], do: trim_start(rest)
  defp trim_start(field), do: field
  defp trim_end(_, 0), do: <<>>

  defp trim_end(field, size) do
    if :binary.at(field, size - 1) in [32, 9],
      do: trim_end(field, size - 1),
      else: binary_part(field, 0, size)
  end

  defp timestamp("0"), do: {:ok, 0}

  defp timestamp(<<first, rest::binary>> = text)
       when first in ?1..?9 and byte_size(text) <= 12 do
    if decimal?(rest) do
      value = :erlang.binary_to_integer(text)
      if value <= @max_time, do: {:ok, value}, else: :error
    else
      :error
    end
  end

  defp timestamp(_), do: :error
  defp decimal?(<<>>), do: true
  defp decimal?(<<digit, rest::binary>>) when digit in ?0..?9, do: decimal?(rest)
  defp decimal?(_), do: false

  defp matches?(body, timestamp, signatures, secrets) do
    Enum.reduce(secrets, false, fn secret, any_key ->
      expected = :crypto.mac(:hmac, :sha256, secret, [timestamp, ".", body])

      Enum.reduce(signatures, any_key, fn signature, matched ->
        equal = :crypto.hash_equals(expected, signature)
        equal or matched
      end)
    end)
  end
end
