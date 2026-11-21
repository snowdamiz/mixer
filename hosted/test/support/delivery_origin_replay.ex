defmodule MixerHosted.Test.DeliveryOriginReplay do
  @moduledoc false

  alias MixerHosted.Releases.{DeliveryExport, DeliveryPublishFence, WriterRepo}

  @request_limit 16_384
  @artifact_limit 6 * 1024 * 1024
  @assignment_limit 65_536
  @receive_ms 10_000
  @replay_ms 50_000

  def run!(scratch, target, fixture, halt, check_locks) do
    path = Path.join(scratch, "authority.sock")

    {:ok, listener} =
      :gen_tcp.listen(0,
        ifaddr: {:local, path},
        active: false,
        mode: :binary,
        packet: :line,
        packet_size: @request_limit,
        send_timeout: 2_000,
        send_timeout_close: true
      )

    try do
      File.chmod!(path, 0o600)
      File.write!(Path.join(scratch, "authority.ready"), "ready", [:exclusive])
      deadline = System.monotonic_time(:millisecond) + @replay_ms
      serve(listener, target, fixture, halt, check_locks, nil, deadline)
    after
      :ok = :gen_tcp.close(listener)
      File.rm!(path)
    end
  end

  defp serve(listener, target, fixture, halt, check_locks, export, deadline) do
    remaining = deadline - System.monotonic_time(:millisecond)
    true = remaining > 0
    {:ok, socket} = :gen_tcp.accept(listener, remaining)

    next =
      try do
        case :gen_tcp.recv(socket, 0, min(remaining, @receive_ms)) do
          {:ok, bytes} ->
            handle(Jason.decode!(bytes), socket, target, fixture, halt, check_locks, export)

          {:error, :closed} ->
            export
        end
      after
        :ok = :gen_tcp.close(socket)
      end

    if next != :done, do: serve(listener, target, fixture, halt, check_locks, next, deadline)
  end

  defp handle(%{"op" => "fixture"}, socket, _, fixture, _, _, export) do
    reply!(socket, fixture)
    export
  end

  defp handle(%{"op" => "read", "target" => coordinates}, socket, target, fixture, _, _, _) do
    case coordinates == fixture.target && DeliveryExport.current(target) do
      {:ok, export} ->
        true = byte_size(export.assignment_bytes) in 1..@assignment_limit

        reply!(
          socket,
          Map.put(authority(export), "assignment", Base.encode64(export.assignment_bytes))
        )

        export

      _ ->
        reply!(socket, nil)
        nil
    end
  end

  defp handle(
         %{"op" => "artifact", "authority" => expected, "artifact" => entry},
         socket,
         _,
         _,
         _,
         _,
         export
       ) do
    artifact =
      if export && authority(export) == expected do
        Enum.find(export.artifacts, &(artifact_ref(&1) == entry))
      end

    with %{envelope_bytes: bytes, envelope_sha256: digest} <- artifact,
         true <- byte_size(bytes) in 1..@artifact_limit,
         ^digest <- Base.encode16(:crypto.hash(:sha256, bytes), case: :lower) do
      reply!(socket, Base.encode64(bytes))
    else
      _ -> reply!(socket, nil)
    end

    export
  end

  defp handle(%{"op" => "fence", "authority" => expected}, socket, target, _, _, check, export) do
    result =
      if export && authority(export) == expected do
        DeliveryPublishFence.with_current(target, export, fn window ->
          check.(target)
          remaining = remaining_ms(window)

          if remaining > 0 do
            reply!(socket, %{grant_ms: remaining, valid_until_unix: window.valid_until_unix})

            with {:ok, ack} <- :gen_tcp.recv(socket, 0, remaining_ms(window)),
                 true <- remaining_ms(window) > 0 do
              case Jason.decode(ack) do
                {:ok, %{"result" => "applied"}} ->
                  :applied

                {:ok, %{"result" => result}}
                when result in ["retry", "unchanged", "expired", "stale"] ->
                  :conflict

                _ ->
                  :indeterminate
              end
            else
              _ -> :indeterminate
            end
          else
            :indeterminate
          end
        end)
      else
        {:error, :rejected}
      end

    # A lost peer acknowledgement can also close the socket before this reply.
    _ = reply(socket, %{result: fence_result(result)})
    export
  end

  defp handle(%{"op" => "halt"}, socket, _, _, halt, _, export) do
    halt.()
    reply!(socket, "halted")
    export
  end

  defp handle(%{"op" => "writer_ready"}, socket, _, _, _, _, export) do
    result =
      WriterRepo.query(
        "SELECT session_user::text, ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()",
        [],
        queue: false,
        timeout: 500,
        log: false
      )

    reply!(socket, match?({:ok, %{rows: [["mixer_replay_writer", true]]}}, result))
    export
  end

  defp handle(%{"op" => "done"}, socket, _, _, _, _, _) do
    reply!(socket, "done")
    :done
  end

  defp handle(_, socket, _, _, _, _, export) do
    reply!(socket, nil)
    export
  end

  defp authority(export) do
    %{
      "target" => export.target,
      "head" => Map.new(export.head, fn {key, value} -> {Atom.to_string(key), value} end),
      "artifacts" => Enum.map(export.artifacts, &artifact_ref/1),
      "valid_until_unix" => export.valid_until_unix
    }
  end

  defp artifact_ref(artifact) do
    %{
      "manifest_sha256" => artifact.manifest_sha256,
      "envelope_sha256" => artifact.envelope_sha256
    }
  end

  defp fence_result({:ok, :applied}), do: "applied"
  defp fence_result({:error, :conflict}), do: "retry"
  defp fence_result({:error, :rejected}), do: "stale"
  defp fence_result({:error, :indeterminate}), do: "indeterminate"
  defp fence_result({:error, _}), do: "unavailable"

  defp remaining_ms(window),
    do: max(0, window.deadline_monotonic_ms - System.monotonic_time(:millisecond))

  defp reply!(socket, value), do: :ok = reply(socket, value)
  defp reply(socket, value), do: :gen_tcp.send(socket, [Jason.encode_to_iodata!(value), "\n"])
end
