defmodule MixerHosted.Identity.FetchFlight do
  @moduledoc false
  use GenServer
  alias MixerHosted.Identity.{JWKSTransport, TrustSnapshot}
  def start_link(opts), do: GenServer.start_link(__MODULE__, opts)

  def child_spec(opts),
    do: %{
      id: make_ref(),
      start: {__MODULE__, :start_link, [opts]},
      restart: :temporary,
      shutdown: :infinity
    }

  def init(opts) do
    Process.flag(:trap_exit, true)
    %{owner: owner, entry: entry, deadline: deadline, configuration: configuration} = opts
    watcher = self()

    {worker, monitor} =
      :erlang.spawn_opt(
        fn ->
          Process.flag(:max_heap_size, %{size: 1_000_000, kill: true, error_logger: false})
          result = fetch(entry, deadline, configuration, watcher)

          result =
            with {:ok, candidate} <- result,
                 true <- System.monotonic_time(:millisecond) < deadline,
                 {:ok, snapshot} <-
                   TrustSnapshot.new(
                     entry.profile,
                     candidate.body,
                     candidate.fetched_at,
                     candidate.fresh_until
                   ),
                 now = System.monotonic_time(:millisecond),
                 true <- now < deadline and now < candidate.expires_mono do
              {:ok, snapshot, Map.delete(candidate, :body)}
            else
              _ -> {:error, :fetch_rejected}
            end

          send(watcher, {:candidate, self(), result})
        end,
        [:link, :monitor]
      )

    timer =
      Process.send_after(
        self(),
        :deadline,
        max(0, deadline - System.monotonic_time(:millisecond))
      )

    {:ok,
     %{
       owner: owner,
       worker: worker,
       monitor: monitor,
       timer: timer,
       socket: nil,
       raw_socket: nil,
       raw_monitor: nil,
       raw_closed: false,
       connection: nil,
       connection_monitor: nil,
       connection_down: false,
       worker_down: false,
       result: {:error, :fetch_rejected}
     }}
  end

  defp fetch(entry, d, c, w) do
    if Map.has_key?(c, :fixture) do
      fixture_fetch(entry, d, c, w)
    else
      JWKSTransport.fetch(entry, d, c, w)
    end
  end

  if Mix.env() == :test do
    defp fixture_fetch(entry, d, c, w) do
      %{ip: ip, port: port} = c.fixture
      JWKSTransport.fetch_fixture(entry, ip, port, d, c.ca_roots, w)
    end
  else
    defp fixture_fetch(_, _, _, _), do: {:error, :invalid_configuration}
  end

  def handle_info(
        {:register_raw_socket, worker, socket, ref},
        %{worker: worker, raw_socket: nil} = s
      )
      when is_port(socket) do
    if Port.info(socket, :connected) == {:connected, worker} do
      monitor = :erlang.monitor(:port, socket)
      send(worker, {ref, :ok})
      {:noreply, %{s | raw_socket: socket, raw_monitor: monitor}}
    else
      send(worker, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info(
        {:register_connection, worker, raw, connection, ref},
        %{worker: worker, raw_socket: raw, connection: nil} = s
      )
      when is_pid(connection) do
    if Port.info(raw, :connected) == {:connected, connection} do
      monitor = Process.monitor(connection)
      send(worker, {ref, :ok})
      {:noreply, %{s | connection: connection, connection_monitor: monitor}}
    else
      send(worker, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info({:register_socket, worker, socket, ref}, %{worker: worker} = s) do
    send(worker, {ref, :ok})
    {:noreply, %{s | socket: socket}}
  end

  def handle_info({:candidate, worker, result}, %{worker: worker} = s),
    do: {:noreply, %{s | result: result}}

  def handle_info(:cancel, s), do: handle_info(:deadline, s)

  def handle_info(:deadline, s) do
    Process.exit(s.worker, :kill)
    close_raw(s.raw_socket)
    close(s.socket)
    {:noreply, %{s | result: {:error, :deadline}}}
  end

  def handle_info({:DOWN, ref, :process, worker, _}, %{monitor: ref, worker: worker} = s) do
    Process.cancel_timer(s.timer)
    close_raw(s.raw_socket)
    close(s.socket)
    await_raw_closed(s)
    await_connection_down(s)
    send(s.owner, {:flight_result, self(), s.result})
    {:stop, :normal, %{s | raw_closed: true, connection_down: true, worker_down: true}}
  end

  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}

  def handle_info({:DOWN, ref, :port, socket, _}, %{raw_monitor: ref, raw_socket: socket} = s),
    do: {:noreply, %{s | raw_closed: true}}

  def handle_info(
        {:DOWN, ref, :process, pid, _},
        %{connection_monitor: ref, connection: pid} = s
      ),
      do: {:noreply, %{s | connection_down: true}}

  def terminate(_, s) do
    Process.cancel_timer(s.timer)
    Process.exit(s.worker, :kill)
    close_raw(s.raw_socket)
    close(s.socket)
    await_raw_closed(s)
    await_connection_down(s)

    unless s.worker_down do
      receive do
        {:DOWN, ref, :process, _, _} when ref == s.monitor -> :ok
      end
    end
  end

  defp close_raw(nil), do: :ok
  defp close_raw(socket), do: :gen_tcp.close(socket)
  defp await_raw_closed(%{raw_socket: nil}), do: :ok
  defp await_raw_closed(%{raw_closed: true}), do: :ok

  defp await_raw_closed(s) do
    # Slots cannot retire until the owned OS socket's port DOWN is observed.
    receive do
      {:DOWN, ref, :port, port, _} when ref == s.raw_monitor and port == s.raw_socket -> :ok
    end
  end

  defp await_connection_down(%{connection: nil}), do: :ok
  defp await_connection_down(%{connection_down: true}), do: :ok

  defp await_connection_down(s) do
    receive do
      {:DOWN, ref, :process, pid, _} when ref == s.connection_monitor and pid == s.connection ->
        :ok
    end
  end

  defp close(nil), do: :ok

  defp close(socket) do
    :ssl.close(socket, 100)
  catch
    _, _ -> :ok
  end
end
