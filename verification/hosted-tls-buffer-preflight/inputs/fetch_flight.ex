defmodule MixerHosted.Identity.FetchFlight do
  @moduledoc false
  use GenServer
  alias MixerHosted.Identity.{JWKSTransport, TrustSnapshot}
  def start_link(opts), do: GenServer.start_link(__MODULE__, opts)

  def child_spec(opts),
    do: %{id: make_ref(), start: {__MODULE__, :start_link, [opts]}, restart: :temporary}

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

  def handle_info({:register_socket, worker, socket, ref}, %{worker: worker} = s) do
    send(worker, {ref, :ok})
    {:noreply, %{s | socket: socket}}
  end

  def handle_info({:candidate, worker, result}, %{worker: worker} = s),
    do: {:noreply, %{s | result: result}}

  def handle_info(:cancel, s), do: handle_info(:deadline, s)

  def handle_info(:deadline, s) do
    Process.exit(s.worker, :kill)
    close(s.socket)
    {:noreply, %{s | result: {:error, :deadline}}}
  end

  def handle_info({:DOWN, ref, :process, worker, _}, %{monitor: ref, worker: worker} = s) do
    Process.cancel_timer(s.timer)
    close(s.socket)
    send(s.owner, {:flight_result, self(), s.result})
    {:stop, :normal, s}
  end

  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}

  def terminate(_, s) do
    Process.cancel_timer(s.timer)
    Process.exit(s.worker, :kill)
    close(s.socket)

    receive do
      {:DOWN, ref, :process, _, _} when ref == s.monitor -> :ok
    after
      100 -> :ok
    end
  end

  defp close(nil), do: :ok

  defp close(socket) do
    :ssl.close(socket, 100)
  catch
    _, _ -> :ok
  end
end
