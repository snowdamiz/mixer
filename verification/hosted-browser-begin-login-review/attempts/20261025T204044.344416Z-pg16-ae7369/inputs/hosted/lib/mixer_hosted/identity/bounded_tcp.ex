defmodule MixerHosted.Identity.BoundedTCP do
  @moduledoc false
  import Kernel, except: [send: 2]
  # OTP's documented cb_info transport seam. Only this fetch's TCP sockets are
  # touched; no global SSL option is changed. Driver buffer is not OS recbuf.
  @buffer 16_384
  @context {__MODULE__, :context}
  def with_watchdog(watcher, deadline, fun) do
    previous = Process.get(@context)
    Process.put(@context, %{watcher: watcher, deadline: deadline, socket: nil})

    try do
      fun.()
    after
      if context = Process.get(@context), do: close_owned(context.socket)
      if previous, do: Process.put(@context, previous), else: Process.delete(@context)
    end
  end

  def connect(address, port, options, timeout) do
    options = Enum.reject(options, &match?({:active, _}, &1))
    options = Enum.reject(options, &match?({:buffer, _}, &1))

    case :gen_tcp.connect(
           address,
           port,
           [{:inet_backend, :inet} | options] ++ [active: false, buffer: @buffer],
           timeout
         ) do
      {:ok, socket} when is_port(socket) ->
        context = Process.get(@context)
        if context, do: Process.put(@context, %{context | socket: socket})

        with :ok <- setopts(socket, active: false), :ok <- register(socket, context) do
          {:ok, socket}
        else
          _ ->
            close_owned(socket)
            {:error, :econnaborted}
        end

      result ->
        result
    end
  end

  def setopts(socket, options) do
    activations = for {:active, value} <- options, do: value

    rest =
      Enum.reject(options, fn option ->
        match?({:active, _}, option) or match?({:buffer, _}, option)
      end)

    previous_active =
      case :inet.getopts(socket, [:active]) do
        {:ok, [active: a]} -> a
        _ -> :invalid
      end

    activation =
      case activations do
        [] when is_integer(previous_active) and previous_active > 0 -> 1
        [] -> previous_active
        [n] when is_integer(n) and n > 0 -> 1
        [n] when is_integer(n) and n <= 0 -> n
        [false] -> false
        [:once] -> :once
        _ -> :invalid
      end

    with true <- activation != :invalid,
         :ok <- :inet.setopts(socket, active: false),
         :ok <- :inet.setopts(socket, rest),
         :ok <- :inet.setopts(socket, buffer: @buffer),
         {:ok, [buffer: @buffer]} <- :inet.getopts(socket, [:buffer]),
         :ok <- :inet.setopts(socket, active: activation) do
      :ok
    else
      _ ->
        close_owned(socket)
        {:error, :einval}
    end
  end

  defp register(_socket, nil), do: {:error, :missing_fetch_context}
  defp register(_socket, %{watcher: nil}), do: :ok

  defp register(socket, %{watcher: watcher, deadline: deadline}) do
    ref = make_ref()
    Kernel.send(watcher, {:register_raw_socket, self(), socket, ref})

    receive do
      {^ref, :ok} -> :ok
    after
      max(0, deadline - System.monotonic_time(:millisecond)) -> {:error, :deadline}
    end
  end

  defp close_owned(nil), do: :ok
  defp close_owned(socket), do: :gen_tcp.close(socket)
  defdelegate send(socket, data), to: :gen_tcp
  defdelegate recv(socket, length, timeout), to: :gen_tcp

  def controlling_process(socket, pid) do
    with :ok <- :gen_tcp.controlling_process(socket, pid) do
      case Process.get(@context) do
        %{socket: ^socket, watcher: watcher, deadline: deadline} when is_pid(watcher) ->
          ref = make_ref()
          Kernel.send(watcher, {:register_connection, self(), socket, pid, ref})

          receive do
            {^ref, :ok} -> :ok
          after
            max(0, deadline - System.monotonic_time(:millisecond)) ->
              :gen_tcp.close(socket)
              {:error, :timeout}
          end

        _ ->
          :ok
      end
    end
  end

  defdelegate shutdown(socket, how), to: :gen_tcp
  defdelegate close(socket), to: :gen_tcp
  defdelegate getopts(socket, options), to: :inet
  defdelegate getstat(socket, options), to: :inet
  defdelegate peername(socket), to: :inet
  defdelegate sockname(socket), to: :inet
  defdelegate port(socket), to: :inet
end
