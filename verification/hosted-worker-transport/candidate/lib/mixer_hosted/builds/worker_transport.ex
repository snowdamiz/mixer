defmodule MixerHosted.Builds.WorkerTransport.RoleGuard do
  @moduledoc false
  use GenServer
  def start(owner), do: GenServer.start(__MODULE__, owner, name: __MODULE__)
  def launch(guard, owner, options), do: GenServer.call(guard, {:launch, owner, options}, 1_000)

  def init(owner),
    do:
      {:ok,
       %{
         owner: owner,
         monitor: Process.monitor(owner),
         closed: false,
         quarantined: false,
         flights: %{}
       }}

  def handle_call({:launch, owner, options}, _, %{owner: owner, closed: false} = s) do
    if map_size(s.flights) < 16 and Process.alive?(owner) do
      case MixerHosted.Builds.WorkerTransport.Flight.start(Map.put(options, :role_guard, self())) do
        {:ok, pid} ->
          {:reply, {:ok, pid}, %{s | flights: Map.put(s.flights, pid, Process.monitor(pid))}}

        _ ->
          {:reply, {:error, :unavailable}, s}
      end
    else
      {:reply, {:error, :unavailable}, s}
    end
  end

  def handle_call(_, _, s), do: {:reply, {:error, :unavailable}, s}

  def handle_info({:DOWN, ref, :process, owner, _}, %{owner: owner, monitor: ref} = s) do
    Enum.each(Map.keys(s.flights), &send(&1, :deadline))
    finish(%{s | closed: true})
  end

  def handle_info({:DOWN, ref, :process, pid, reason}, s) do
    if s.flights[pid] == ref do
      next = %{s | flights: Map.delete(s.flights, pid)}

      if reason == :normal do
        finish(next)
      else
        # Unknown watchdog death is not cleanup proof. Hold the role closed;
        # an operator must dispose the entire execution domain before restart.
        Enum.each(Map.keys(next.flights), &send(&1, :deadline))
        {:noreply, %{next | closed: true, quarantined: true}}
      end
    else
      {:noreply, s}
    end
  end

  def handle_info(_, s), do: {:noreply, s}

  defp finish(%{closed: true, quarantined: false, flights: flights} = s)
       when map_size(flights) == 0, do: {:stop, :normal, s}

  defp finish(s), do: {:noreply, s}
end

defmodule MixerHosted.Builds.WorkerTransport.Flight do
  @moduledoc false
  use GenServer
  alias MixerHosted.Builds.WorkerTransport
  def start(options), do: GenServer.start(__MODULE__, options)

  def init(options) do
    Process.flag(:trap_exit, true)
    watcher = self()

    {worker, monitor} =
      :erlang.spawn_opt(
        fn ->
          Process.flag(:max_heap_size, %{size: 262_144, kill: true, error_logger: false})
          result = WorkerTransport.exchange(options, watcher)
          send(watcher, {:candidate, self(), result})
        end,
        [:link, :monitor]
      )

    timer = Process.send_after(self(), :deadline, options.deadline, abs: true)

    {:ok,
     %{
       owner: options.owner,
       owner_ref: Process.monitor(options.owner),
       caller_ref: Process.monitor(options.caller),
       role_ref: Process.monitor(options.role_guard),
       worker: worker,
       worker_ref: monitor,
       worker_down: false,
       raw: nil,
       raw_ref: nil,
       raw_down: true,
       connection: nil,
       connection_ref: nil,
       connection_down: true,
       socket: nil,
       result: {:error, :uncertain},
       timer: timer,
       cancelled: false,
       deadline: options.deadline
     }}
  end

  def handle_info({:register_raw_socket, worker, raw, ref}, %{worker: worker, raw: nil} = s)
      when is_port(raw) do
    if not s.cancelled and Port.info(raw, :connected) == {:connected, worker} do
      monitor = :erlang.monitor(:port, raw)
      send(worker, {ref, :ok})
      {:noreply, %{s | raw: raw, raw_ref: monitor, raw_down: false}}
    else
      :gen_tcp.close(raw)
      send(worker, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info(
        {:register_connection, worker, raw, connection, ref},
        %{worker: worker, raw: raw, connection: nil} = s
      )
      when is_pid(connection) do
    if not s.cancelled and Port.info(raw, :connected) == {:connected, connection} do
      monitor = Process.monitor(connection)
      send(worker, {ref, :ok})
      {:noreply, %{s | connection: connection, connection_ref: monitor, connection_down: false}}
    else
      Process.exit(connection, :kill)
      send(worker, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info({:register_socket, worker, socket, ref}, %{worker: worker} = s) do
    if not s.cancelled do
      send(worker, {ref, :ok})
      {:noreply, %{s | socket: socket}}
    else
      close_ssl(socket)
      send(worker, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info({:candidate, worker, result}, %{worker: worker, cancelled: false} = s) do
    if System.monotonic_time(:millisecond) < s.deadline,
      do: {:noreply, %{s | result: result}},
      else: cancel(s)
  end

  def handle_info({:DOWN, ref, :process, worker, _}, %{worker_ref: ref, worker: worker} = s),
    do: finish(close_owned(%{s | worker_down: true}))

  def handle_info({:DOWN, ref, :port, raw, _}, %{raw_ref: ref, raw: raw} = s),
    do: finish(%{s | raw_down: true})

  def handle_info(
        {:DOWN, ref, :process, connection, _},
        %{connection_ref: ref, connection: connection} = s
      ),
      do: finish(%{s | connection_down: true})

  def handle_info({:DOWN, ref, :process, _, _}, s)
      when ref == s.owner_ref or ref == s.caller_ref or ref == s.role_ref,
      do: cancel(s)

  def handle_info(:deadline, s), do: cancel(s)
  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}
  def handle_info(_, s), do: {:noreply, s}

  defp cancel(s) do
    Process.exit(s.worker, :kill)
    finish(close_owned(%{s | result: {:error, :uncertain}, cancelled: true}))
  end

  defp close_owned(s) do
    if s.raw, do: :gen_tcp.close(s.raw)
    if s.socket, do: close_ssl(s.socket)
    if is_pid(s.connection) and not s.connection_down, do: Process.exit(s.connection, :kill)
    s
  end

  defp close_ssl(socket) do
    :ssl.close(socket, 100)
  catch
    _, _ -> :ok
  end

  defp finish(%{worker_down: true, raw_down: true, connection_down: true} = s) do
    Process.cancel_timer(s.timer)

    result =
      if System.monotonic_time(:millisecond) < s.deadline,
        do: s.result,
        else: {:error, :uncertain}

    send(s.owner, {:worker_transport_finished, self(), result})
    {:stop, :normal, s}
  end

  defp finish(s), do: {:noreply, s}

  def terminate(_, s) do
    Process.cancel_timer(s.timer)
    Process.exit(s.worker, :kill)
    close_owned(s)
    :ok
  end
end

defmodule MixerHosted.Builds.WorkerTransport do
  @moduledoc "Finite outbound TLS client. Explicit component startup; no default installation."
  use GenServer
  alias MixerHosted.Builds.{WorkerConfig, WorkerWire}
  alias MixerHosted.Identity.{BoundedTCP, DNSResolver}
  @lifetime 5_000
  @slots 16

  def start_link(%WorkerConfig{mode: :configured} = config),
    do: start_component(config, nil)

  def start_link(_), do: {:error, :unavailable}

  def child_spec(config),
    do: %{id: __MODULE__, start: {__MODULE__, :start_link, [config]}, restart: :temporary}

  if Mix.env() == :test do
    def start_fixture(%WorkerConfig{mode: :configured} = config, {127, 0, 0, 1} = ip, port)
        when is_integer(port) and port in 1..65_535,
        do: start_component(config, %{ip: ip, port: port})
  end

  defp start_component(config, fixture) do
    if WorkerConfig.validated?(config) and Process.whereis(__MODULE__.RoleGuard) == nil,
      do: GenServer.start_link(__MODULE__, {config, fixture}, name: __MODULE__),
      else: {:error, :unavailable}
  end

  def perform(command, request) when command in [:query, :ensure_started, :stop] do
    deadline = System.monotonic_time(:millisecond) + @lifetime

    try do
      GenServer.call(__MODULE__, {:perform, command, request, deadline}, 5_750)
    catch
      :exit, {:noproc, _} -> {:error, :unavailable}
      :exit, _ -> {:error, :uncertain}
    end
  end

  def perform(_, _), do: {:error, :uncertain}

  def init({config, fixture}) do
    case if(WorkerConfig.validated?(config),
           do: __MODULE__.RoleGuard.start(self()),
           else: {:error, :unavailable}
         ) do
      {:ok, guard} -> {:ok, %{config: config, fixture: fixture, flights: %{}, role_guard: guard}}
      _ -> {:stop, :unavailable}
    end
  end

  def handle_call({:perform, command, request, deadline}, from, s) do
    cond do
      map_size(s.flights) >= @slots ->
        {:reply, {:error, :unavailable}, s}

      remaining(deadline) == 0 ->
        {:reply, {:error, :uncertain}, s}

      true ->
        options = %{
          config: s.config,
          fixture: s.fixture,
          command: command,
          request: request,
          owner: self(),
          caller: elem(from, 0),
          deadline: deadline
        }

        case launch(s.role_guard, options) do
          {:ok, pid} ->
            ref = Process.monitor(pid)

            {:noreply,
             %{
               s
               | flights:
                   Map.put(s.flights, pid, %{ref: ref, from: from, result: {:error, :uncertain}})
             }}

          _ ->
            {:reply, {:error, :unavailable}, s}
        end
    end
  end

  def handle_call(_, _, s), do: {:reply, {:error, :uncertain}, s}

  def handle_info({:worker_transport_finished, pid, result}, s) do
    case Map.fetch(s.flights, pid) do
      {:ok, flight} ->
        {:noreply, %{s | flights: Map.put(s.flights, pid, %{flight | result: result})}}

      :error ->
        {:noreply, s}
    end
  end

  def handle_info({:DOWN, ref, :process, pid, _}, s) do
    case Map.fetch(s.flights, pid) do
      {:ok, %{ref: ^ref} = flight} ->
        GenServer.reply(flight.from, flight.result)
        {:noreply, %{s | flights: Map.delete(s.flights, pid)}}

      _ ->
        {:noreply, s}
    end
  end

  def handle_info(_, s), do: {:noreply, s}

  defp launch(guard, options) do
    __MODULE__.RoleGuard.launch(guard, self(), options)
  catch
    :exit, _ -> {:error, :unavailable}
  end

  @doc false
  def exchange(options, watcher) do
    c = options.config
    d = options.deadline

    with {:ok, body, expected} <- WorkerWire.encode(options.command, options.request, c),
         {:ok, ip, port} <- destination(c, options.fixture, d) do
      BoundedTCP.with_watchdog(watcher, d, fn ->
        connect(c, ip, port, body, expected, watcher, d)
      end)
    else
      _ -> {:error, :uncertain}
    end
  rescue
    _ -> {:error, :uncertain}
  catch
    _, _ -> {:error, :uncertain}
  end

  defp destination(c, nil, d) do
    with {:ok, ip} <- DNSResolver.resolve(c.endpoint.host, c.resolvers, d),
         do: {:ok, ip, c.endpoint.port}
  end

  if Mix.env() == :test do
    defp destination(_, %{ip: ip, port: port}, _), do: {:ok, ip, port}
  else
    defp destination(_, _, _), do: {:error, :uncertain}
  end

  defp connect(c, ip, port, body, expected, watcher, d) do
    options = [
      hostname: c.endpoint.host,
      protocols: [:http1],
      mode: :passive,
      max_header_list_size: 8_192,
      transport_opts: [
        cb_info: {BoundedTCP, :tcp, :tcp_closed, :tcp_error, :tcp_passive},
        verify: :verify_peer,
        cacerts: c.ca_roots,
        timeout: remaining(d),
        send_timeout: remaining(d),
        send_timeout_close: true,
        versions: [:"tlsv1.2", :"tlsv1.3"],
        recbuf: 16_384,
        buffer: 16_384,
        inet4: tuple_size(ip) == 4,
        inet6: tuple_size(ip) == 8,
        max_handshake_size: 65_536
      ]
    ]

    with true <- remaining(d) > 0, {:ok, conn} <- Mint.HTTP.connect(:https, ip, port, options) do
      socket = Mint.HTTP.get_socket(conn)

      try do
        with {:ok, {^ip, ^port}} <- :ssl.peername(socket),
             :ok <- register(watcher, socket, d),
             headers = [
               {"content-type", "application/json"},
               {"accept", "application/json"},
               {"accept-encoding", "identity"},
               {"connection", "close"},
               {"authorization", "Bearer " <> c.token}
             ],
             true <- header_bytes(headers, c.endpoint.host, body) <= 8_192,
             {:ok, conn, ref} <- Mint.HTTP.request(conn, "POST", c.endpoint.path, headers, body),
             {:ok, conn, envelope} <-
               read_headers(conn, ref, d, %{
                 phase: :status,
                 line: "",
                 total: 0,
                 fields: 0,
                 headers: %{},
                 done: false
               }),
             {:ok, conn, chunks} <- read_body(conn, ref, envelope.length, d, [], false),
             true <- remaining(d) > 0,
             result <- WorkerWire.decode(IO.iodata_to_binary(Enum.reverse(chunks)), expected),
             true <- remaining(d) > 0 do
          # Socket is already peer-closed; cleanup still owns and closes local handles.
          _ = conn
          result
        else
          _ -> {:error, :uncertain}
        end
      after
        Mint.HTTP.close(conn)
      end
    else
      _ -> {:error, :uncertain}
    end
  end

  defp header_bytes(headers, host, body),
    do:
      byte_size(host) + byte_size(Integer.to_string(byte_size(body))) + 64 +
        Enum.sum(Enum.map(headers, fn {k, v} -> byte_size(k) + byte_size(v) + 4 end))

  defp register(watcher, socket, d) do
    ref = make_ref()
    send(watcher, {:register_socket, self(), socket, ref})

    receive do
      {^ref, :ok} -> :ok
    after
      remaining(d) -> {:error, :uncertain}
    end
  end

  defp read_headers(conn, ref, d, state) do
    with true <- remaining(d) > 0,
         {:ok, byte} when byte_size(byte) == 1 <-
           :ssl.recv(Mint.HTTP.get_socket(conn), 1, remaining(d)),
         {:ok, next} <- envelope(state, byte),
         {:ok, conn, events} <- Mint.HTTP.stream(conn, {:ssl, Mint.HTTP.get_socket(conn), byte}),
         true <-
           Enum.all?(events, fn
             {:status, ^ref, 200} -> true
             {:headers, ^ref, _} -> true
             _ -> false
           end) do
      if next.done, do: {:ok, conn, next}, else: read_headers(conn, ref, d, next)
    else
      _ -> {:error, :uncertain}
    end
  end

  defp envelope(s, byte) do
    line = s.line <> byte

    cond do
      byte_size(line) > 2_048 or s.total + 1 > 8_192 ->
        :error

      byte == "\n" and not String.ends_with?(line, "\r\n") ->
        :error

      byte == "\n" ->
        text = binary_part(line, 0, byte_size(line) - 2)
        envelope_line(%{s | line: "", total: s.total + 1}, text)

      true ->
        {:ok, %{s | line: line, total: s.total + 1}}
    end
  end

  defp envelope_line(%{phase: :status} = s, line) do
    if Regex.match?(~r/\AHTTP\/1\.1 200 [\x20-\x7e]*\z/, line),
      do: {:ok, %{s | phase: :headers}},
      else: :error
  end

  defp envelope_line(s, "") do
    h = s.headers

    with "application/json" <- h["content-type"],
         {:ok, n} <- WorkerWire.decimal(h["content-length"], 1, 32_768),
         true <- h["content-encoding"] in [nil, "identity"],
         true <- Enum.all?(~w(transfer-encoding trailer upgrade), &(not Map.has_key?(h, &1))),
         do: {:ok, Map.put(%{s | done: true}, :length, n)},
         else: (_ -> :error)
  end

  defp envelope_line(s, line) do
    with true <- s.fields < 32,
         [name, value] <- String.split(line, ":", parts: 2),
         true <- Regex.match?(~r/\A[!#$%&'*+.^_`|~0-9A-Za-z-]+\z/, name),
         true <- Enum.all?(:binary.bin_to_list(value), &(&1 == 9 or &1 in 32..126)),
         name = String.downcase(name),
         false <- Map.has_key?(s.headers, name),
         do:
           {:ok,
            %{
              s
              | fields: s.fields + 1,
                headers: Map.put(s.headers, name, String.trim(value))
            }},
         else: (_ -> :error)
  end

  defp read_body(conn, ref, 1, d, chunks, false) do
    socket = Mint.HTTP.get_socket(conn)
    # Mint closes the local socket at request_done for Connection: close.
    # Hold the final approved byte until real peer EOF, then let Mint finish.
    with true <- remaining(d) > 0,
         {:ok, last} when byte_size(last) == 1 <- :ssl.recv(socket, 1, remaining(d)),
         {:error, :closed} <- :ssl.recv(socket, 1, remaining(d)),
         true <- remaining(d) > 0,
         {:ok, conn, events} <- Mint.HTTP.stream(conn, {:ssl, socket, last}),
         true <-
           Enum.all?(events, fn
             {:data, ^ref, _} -> true
             {:done, ^ref} -> true
             _ -> false
           end),
         true <- Enum.member?(events, {:done, ref}),
         ^last <- for({:data, ^ref, value} <- events, into: "", do: value),
         do: {:ok, conn, [:binary.copy(last) | chunks]},
         else: (_ -> {:error, :uncertain})
  end

  defp read_body(conn, ref, n, d, chunks, false) when n > 1 do
    count = min(n - 1, 4_096)

    with true <- remaining(d) > 0,
         {:ok, bytes} when byte_size(bytes) >= 1 and byte_size(bytes) <= count <-
           :ssl.recv(Mint.HTTP.get_socket(conn), count, remaining(d)),
         {:ok, conn, events} <- Mint.HTTP.stream(conn, {:ssl, Mint.HTTP.get_socket(conn), bytes}),
         true <-
           Enum.all?(events, fn
             {:data, ^ref, _} -> true
             _ -> false
           end),
         data = for({:data, ^ref, value} <- events, into: "", do: value),
         true <- data == bytes,
         do: read_body(conn, ref, n - byte_size(bytes), d, [:binary.copy(data) | chunks], false),
         else: (_ -> {:error, :uncertain})
  end

  defp read_body(_, _, _, _, _, _), do: {:error, :uncertain}
  defp remaining(d), do: max(0, d - System.monotonic_time(:millisecond))
end
