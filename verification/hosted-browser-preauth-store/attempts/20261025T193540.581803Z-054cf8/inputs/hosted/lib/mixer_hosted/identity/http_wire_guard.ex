defmodule MixerHosted.Identity.HTTPWireGuard do
  @moduledoc false
  @limit 262_144
  def new,
    do: %{
      phase: :status,
      line: "",
      headers: %{},
      header_bytes: 0,
      fields: 0,
      infos: 0,
      status: nil,
      body_bytes: 0,
      done: false
    }

  def feed(state, data), do: consume(state, data)
  defp consume(s, <<>>), do: {:ok, s}
  defp consume(%{done: true}, _), do: {:error, :extra_response}

  defp consume(%{phase: {:length, n}} = s, data) do
    take = min(n, byte_size(data))
    <<_::binary-size(^take), rest::binary>> = data

    if s.body_bytes + take > @limit,
      do: {:error, :body_limit},
      else:
        consume(
          %{s | phase: {:length, n - take}, body_bytes: s.body_bytes + take, done: n == take},
          rest
        )
  end

  defp consume(%{phase: :close} = s, data) do
    if s.body_bytes + byte_size(data) > @limit,
      do: {:error, :body_limit},
      else: {:ok, %{s | body_bytes: s.body_bytes + byte_size(data)}}
  end

  defp consume(%{phase: {:chunk, n}} = s, data) do
    take = min(n, byte_size(data))
    <<_::binary-size(^take), rest::binary>> = data

    if s.body_bytes + take > @limit,
      do: {:error, :body_limit},
      else:
        consume(
          %{
            s
            | phase: if(n == take, do: :chunk_crlf, else: {:chunk, n - take}),
              body_bytes: s.body_bytes + take
          },
          rest
        )
  end

  defp consume(s, data) do
    case :binary.match(data, "\n") do
      :nomatch ->
        if byte_size(s.line) + byte_size(data) > 10_240,
          do: {:error, :line_limit},
          else: {:ok, %{s | line: s.line <> data}}

      {i, 1} ->
        <<part::binary-size(^i), 10, rest::binary>> = data
        line = s.line <> part <> "\n"

        with true <- byte_size(line) <= 10_240 and String.ends_with?(line, "\r\n"),
             {:ok, s} <- line(%{s | line: ""}, binary_part(line, 0, byte_size(line) - 2)) do
          consume(s, rest)
        else
          _ -> {:error, :framing_rejected}
        end
    end
  end

  defp line(%{phase: :status} = s, line) do
    case line do
      <<"HTTP/1.1 ", a, b, c, " ", _::binary>> when a in ?0..?9 and b in ?0..?9 and c in ?0..?9 ->
        status = (a - ?0) * 100 + (b - ?0) * 10 + c - ?0

        cond do
          status in 100..199 and status != 101 and s.infos < 4 ->
            {:ok, %{s | phase: :headers, status: status, infos: s.infos + 1, headers: %{}}}

          status == 200 ->
            {:ok, %{s | phase: :headers, status: status, headers: %{}}}

          true ->
            {:error, :status_rejected}
        end

      _ ->
        {:error, :status_rejected}
    end
  end

  defp line(%{phase: :headers, status: status} = s, "") when status in 100..199,
    do: {:ok, %{s | phase: :status}}

  defp line(%{phase: :headers} = s, "") do
    h = s.headers

    with true <-
           h["content-type"] != nil and
             Regex.match?(
               ~r/^application\/(?:jwk-set\+json|json)(?:\s*;\s*charset=[Uu][Tt][Ff]-8)?$/,
               h["content-type"]
             ),
         true <- h["content-encoding"] in [nil, "identity"],
         true <- h["transfer-encoding"] in [nil, "chunked"],
         true <- h["trailer"] in [nil, ""],
         true <- not (h["transfer-encoding"] != nil and h["content-length"] != nil),
         {:ok, phase} <- framing(h) do
      {:ok, %{s | phase: phase, done: phase == {:length, 0}}}
    else
      _ -> {:error, :headers_rejected}
    end
  end

  defp line(%{phase: :headers} = s, line) do
    with [name, value] <- String.split(line, ":", parts: 2),
         true <- Regex.match?(~r/^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/, name),
         name = String.downcase(name),
         value = trim_ows(value),
         true <- Enum.all?(:binary.bin_to_list(value), &(&1 == 9 or &1 in 32..126)),
         false <- Map.has_key?(s.headers, name),
         true <- s.fields < 64 and s.header_bytes + byte_size(line) + 2 <= 10_240 do
      {:ok,
       %{
         s
         | headers: Map.put(s.headers, name, value),
           fields: s.fields + 1,
           header_bytes: s.header_bytes + byte_size(line) + 2
       }}
    else
      _ -> {:error, :headers_rejected}
    end
  end

  defp line(%{phase: :chunk_line} = s, line) do
    size = line |> String.split(";", parts: 2) |> hd()

    with true <- byte_size(size) in 1..8 and Regex.match?(~r/^[0-9a-fA-F]+$/, size),
         n = String.to_integer(size, 16),
         true <- n <= @limit - s.body_bytes do
      {:ok, %{s | phase: if(n == 0, do: :trailer, else: {:chunk, n})}}
    else
      _ -> {:error, :body_limit}
    end
  end

  defp line(%{phase: :chunk_crlf} = s, ""), do: {:ok, %{s | phase: :chunk_line}}
  defp line(%{phase: :trailer} = s, ""), do: {:ok, %{s | done: true}}
  defp line(_, _), do: {:error, :framing_rejected}
  defp trim_ows(<<byte, rest::binary>>) when byte in [9, 32], do: trim_ows(rest)
  defp trim_ows(value), do: trim_right_ows(value)
  defp trim_right_ows(<<>>), do: ""

  defp trim_right_ows(value) do
    n = byte_size(value) - 1
    if :binary.at(value, n) in [9, 32], do: trim_right_ows(binary_part(value, 0, n)), else: value
  end

  defp framing(%{"transfer-encoding" => "chunked"}), do: {:ok, :chunk_line}

  defp framing(%{"content-length" => s}) when byte_size(s) in 1..6 do
    if Regex.match?(~r/^[0-9]+$/, s) and String.to_integer(s) <= @limit,
      do: {:ok, {:length, String.to_integer(s)}},
      else: :error
  end

  defp framing(h), do: if(Map.has_key?(h, "content-length"), do: :error, else: {:ok, :close})
end
