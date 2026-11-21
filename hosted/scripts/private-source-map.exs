alias MixerHosted.Releases.SourceMapOperator

args = System.argv()
token = System.get_env("MIXER_RELEASE_TOKEN")

defmodule PrivateSourceMapTransfer do
  @maximum_bytes 4 * 1024 * 1024
  @maximum_deadline 9_007_199_254_740_991
  @chunk_bytes 64 * 1024
  @window_us 5_000_000

  def read(args, token) do
    # A Unix select notification reports readiness only. Completion backends
    # may perform queued writes without another call from this process.
    with %{io_backend: %{name: :unix_essio}} <- :socket.info(),
         fd when is_binary(fd) <- System.get_env("MIXER_PRIVATE_SOURCE_MAP_FD"),
         {fd, ""} when fd >= 3 <- Integer.parse(fd),
         {:ok, socket} <-
           :socket.open(fd, %{domain: :local, type: :stream, protocol: :default, dup: true}) do
      try do
        with {:ok, %{family: :local, path: ""}} <- :socket.peername(socket),
             {:ok, map} <- SourceMapOperator.main(args, token) do
          transfer(socket, map)
        else
          {:error, reason} when is_atom(reason) -> {:error, reason}
          _ -> {:error, :output_unavailable}
        end
      after
        :socket.close(socket)
      end
    else
      _ -> {:error, :output_unavailable}
    end
  end

  defp transfer(socket, %{bytes: bytes, retain_until: retention, valid_until: expiry})
       when retention in 1..@maximum_deadline and is_integer(expiry) and
              expiry >= 1 and expiry <= retention and
              byte_size(bytes) in 1..@maximum_bytes do
    expires_at = expiry * 1_000_000
    started_at = System.monotonic_time(:microsecond)
    deadline = started_at + min(@window_us, expires_at - System.system_time(:microsecond))
    remaining = fn -> remaining(expires_at, deadline) end
    header = <<retention::64, expiry::64, byte_size(bytes)::32>>

    with :ok <- send_step(socket, header, [], remaining),
         {:ok, timeout} <- remaining.(),
         {:ok, "A"} <- :socket.recv(socket, 1, [], timeout),
         :ok <- send_body(socket, bytes, remaining),
         {:ok, _} <- remaining.() do
      :ok
    else
      {:error, :not_found} -> {:error, :not_found}
      _ -> {:error, :output_unavailable}
    end
  end

  defp transfer(_, _), do: {:error, :output_unavailable}

  defp remaining(expires_at, deadline) do
    wall = expires_at - System.system_time(:microsecond)
    window = deadline - System.monotonic_time(:microsecond)

    cond do
      wall <= 0 -> {:error, :not_found}
      window <= 0 -> {:error, :output_unavailable}
      true -> {:ok, div(min(wall, window) + 999, 1_000)}
    end
  end

  defp send_body(socket, <<chunk::binary-size(@chunk_bytes), rest::binary>>, remaining) do
    with :ok <- send_step(socket, chunk, [], remaining),
         do: send_body(socket, rest, remaining)
  end

  defp send_body(_socket, <<>>, _remaining), do: :ok
  defp send_body(socket, bytes, remaining), do: send_step(socket, bytes, [], remaining)

  defp send_step(socket, bytes, flags_or_continuation, remaining) do
    with {:ok, _} <- remaining.() do
      case :socket.send(socket, bytes, flags_or_continuation, :nowait) do
        :ok -> :ok
        {:ok, rest} -> send_step(socket, rest, [], remaining)
        {:select, {select_info, rest}} -> await_writable(socket, rest, select_info, remaining)
        {:select, select_info} -> await_writable(socket, bytes, select_info, remaining)
        {:error, _} = error -> error
      end
    end
  end

  defp await_writable(socket, bytes, {:select_info, _, handle} = info, remaining) do
    with {:ok, timeout} <- remaining.() do
      receive do
        {:"$socket", ^socket, :select, ^handle} ->
          send_step(socket, bytes, info, remaining)

        {:"$socket", ^socket, :abort, {^handle, reason}} ->
          {:error, reason}
      after
        timeout ->
          :socket.cancel(socket, info)

          case remaining.() do
            {:error, _} = error -> error
            _ -> {:error, :output_unavailable}
          end
      end
    end
  end
end

result =
  case args do
    ["read", _, _] ->
      PrivateSourceMapTransfer.read(args, token)

    _ ->
      SourceMapOperator.main(args, token)
  end

case result do
  :ok ->
    :ok

  {:ok, deadline} ->
    IO.puts("retain_until=#{deadline}")

  {:error, reason}
  when reason in [
         :disabled,
         :invalid_request,
         :unauthenticated,
         :permission_denied,
         :not_found,
         :conflict,
         :storage_unavailable,
         :identity_unavailable,
         :authorization_unavailable,
         :invalid_input_file,
         :output_unavailable
       ] ->
    IO.puts(:stderr, Atom.to_string(reason))
    System.halt(1)

  _ ->
    IO.puts(:stderr, "operator_unavailable")
    System.halt(1)
end
