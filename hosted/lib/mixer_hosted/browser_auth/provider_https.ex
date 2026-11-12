defmodule MixerHosted.BrowserAuth.ProviderHTTPS do
  @moduledoc false
  use GenServer
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest}
  alias MixerHosted.BrowserAuth.ProviderHTTPS.Wire
  alias MixerHosted.Identity.{BoundedTCP, DNSResolver, StartupConfig}
  @failure {:error, :provider_unavailable}
  @fields ~w(public_origin profile_id profile_version issuer client_id api_audience authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri client_credential_ref session_vault_ref scope response_mode response_iss_required)a

  # Internal IO only: receiving bytes establishes no credential provenance,
  # provider trust, permit, lease, or authority to activate browser login.
  def post(config, secret, code, verifier, deadline, %StartupConfig{} = identity)
      when is_integer(deadline) do
    run({config, secret, code, verifier, deadline, identity, :production})
  end

  def post(_, _, _, _, _, _), do: @failure

  if Mix.env() == :test do
    # Only loopback destination/port and fixture roots differ from production.
    def post_fixture(config, secret, code, verifier, deadline, identity, port, roots)
        when is_integer(deadline) and is_integer(port) and port in 1..65535 do
      run({config, secret, code, verifier, deadline, identity, {:fixture, port, roots}})
    end

    def post_fixture(_, _, _, _, _, _, _, _), do: @failure
  end

  defp run(args) do
    case GenServer.start(__MODULE__, {self(), args}) do
      {:ok, pid} -> GenServer.call(pid, :await, :infinity)
      _ -> @failure
    end
  catch
    :exit, _ -> @failure
  end

  def init({caller, {_, _, _, _, deadline, _, _} = args}) do
    Process.flag(:trap_exit, true)
    owner = self()

    {worker, monitor} =
      :erlang.spawn_opt(
        fn ->
          Process.flag(:max_heap_size, %{size: 1_000_000, kill: true, error_logger: false})
          send(owner, {:candidate, self(), exchange(args, owner)})
        end,
        [:link, :monitor]
      )

    {:ok,
     %{
       worker: worker,
       monitor: monitor,
       caller: Process.monitor(caller),
       deadline: deadline,
       timer: Process.send_after(self(), :deadline, remaining(deadline)),
       from: nil,
       raw: nil,
       raw_monitor: nil,
       connection: nil,
       connection_monitor: nil,
       socket: nil,
       raw_down: false,
       connection_down: false,
       result: @failure,
       completed: false
     }}
  end

  def handle_call(:await, from, %{completed: false} = s), do: {:noreply, %{s | from: from}}
  def handle_call(:await, _, s), do: {:stop, :normal, final(s), s}

  def handle_info({:register_raw_socket, w, socket, ref}, %{worker: w, raw: nil} = s) do
    if is_port(socket) and Port.info(socket, :connected) == {:connected, w} do
      monitor = :erlang.monitor(:port, socket)
      send(w, {ref, :ok})
      {:noreply, %{s | raw: socket, raw_monitor: monitor}}
    else
      send(w, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info(
        {:register_connection, w, raw, pid, ref},
        %{worker: w, raw: raw, connection: nil} = s
      ) do
    if is_pid(pid) and Port.info(raw, :connected) == {:connected, pid} do
      monitor = Process.monitor(pid)
      send(w, {ref, :ok})
      {:noreply, %{s | connection: pid, connection_monitor: monitor}}
    else
      send(w, {ref, :error})
      {:noreply, s}
    end
  end

  def handle_info({:register_socket, w, socket, ref}, %{worker: w} = s) do
    send(w, {ref, :ok})
    {:noreply, %{s | socket: socket}}
  end

  def handle_info({:candidate, w, result}, %{worker: w} = s),
    do: {:noreply, %{s | result: result}}

  def handle_info(:deadline, s) do
    Process.exit(s.worker, :kill)
    close(s)
    {:noreply, %{s | result: @failure}}
  end

  def handle_info({:DOWN, m, :process, _, _}, %{caller: m} = s) do
    Process.exit(s.worker, :kill)
    close(s)
    {:stop, :normal, s}
  end

  def handle_info({:DOWN, m, :process, w, _}, %{monitor: m, worker: w} = s) do
    Process.cancel_timer(s.timer)
    close(s)
    await_closed(s)
    s = %{s | completed: true}

    if s.from do
      GenServer.reply(s.from, final(s))
      {:stop, :normal, s}
    else
      {:noreply, s}
    end
  end

  def handle_info({:DOWN, m, :port, _, _}, %{raw_monitor: m} = s),
    do: {:noreply, %{s | raw_down: true}}

  def handle_info({:DOWN, m, :process, _, _}, %{connection_monitor: m} = s),
    do: {:noreply, %{s | connection_down: true}}

  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}
  def handle_info(_, s), do: {:noreply, s}

  def terminate(_, s) do
    Process.cancel_timer(s.timer)

    unless s.completed do
      Process.exit(s.worker, :kill)
      close(s)
      await_closed(s)
    end

    :ok
  end

  def format_status(status) do
    Map.new(status, fn {key, value} ->
      if key in [:state, :message, :reason, :log], do: {key, :redacted}, else: {key, value}
    end)
  end

  defp final(s), do: if(remaining(s.deadline) > 0, do: s.result, else: @failure)

  defp close(s) do
    if s.raw, do: :gen_tcp.close(s.raw)
    if s.socket, do: :ssl.close(s.socket, 0)
    :ok
  catch
    _, _ -> :ok
  end

  defp await_closed(s) do
    if not is_nil(s.raw_monitor) and not s.raw_down do
      receive do
        {:DOWN, ref, :port, _, _} when ref == s.raw_monitor -> :ok
      end
    end

    if not is_nil(s.connection_monitor) and not s.connection_down do
      receive do
        {:DOWN, ref, :process, _, _} when ref == s.connection_monitor -> :ok
      end
    end
  end

  defp exchange({config, secret, code, verifier, deadline, identity, destination}, watcher) do
    with true <- remaining(deadline) > 0,
         true <- is_binary(secret) and byte_size(secret) in 1..4096 and String.valid?(secret),
         true <- is_binary(code) and byte_size(code) in 1..4096 and String.valid?(code),
         true <-
           is_binary(verifier) and byte_size(verifier) in 43..128 and
             Regex.match?(~r/^[A-Za-z0-9._~-]+$/, verifier),
         {:ok, _} <- ConfigurationDigest.digest(config),
         object =
           Map.new(@fields, fn k -> {Atom.to_string(k), Map.fetch!(config, k)} end)
           |> Map.merge(%{"version" => 1, "client_auth_method" => "client_secret_basic"}),
         {:ok, ^config} <-
           Config.load(
             %{
               "MIXER_BROWSER_AUTH_MODE" => "configured",
               "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
             },
             :api,
             identity
           ),
         %URI{host: host, path: path, port: 443} <- URI.parse(config.token_endpoint),
         {:ok, ip, port, roots} <- destination(destination, host, identity, deadline),
         true <- remaining(deadline) > 0 do
      basic =
        Base.encode64(URI.encode_www_form(config.client_id) <> ":" <> URI.encode_www_form(secret))

      headers = [
        {"authorization", "Basic " <> basic},
        {"content-type", "application/x-www-form-urlencoded"},
        {"accept", "application/json"},
        {"accept-encoding", "identity"},
        {"connection", "close"}
      ]

      body =
        URI.encode_query([
          {"grant_type", "authorization_code"},
          {"code", code},
          {"redirect_uri", config.redirect_uri},
          {"code_verifier", verifier}
        ])

      BoundedTCP.with_watchdog(watcher, deadline, fn ->
        connect(host, path, ip, port, roots, headers, body, deadline, watcher)
      end)
    else
      _ -> @failure
    end
  rescue
    _ -> @failure
  catch
    _, _ -> @failure
  end

  defp destination(
         :production,
         host,
         %StartupConfig{mode: :configured, owner_options: opts},
         deadline
       ) do
    with resolvers when is_list(resolvers) and length(resolvers) in 1..3 <-
           Keyword.get(opts, :resolvers),
         {:ok, ip} <- DNSResolver.resolve(host, resolvers, deadline) do
      {:ok, ip, 443, :public_key.cacerts_get()}
    else
      _ -> @failure
    end
  end

  if Mix.env() == :test do
    defp destination({:fixture, port, roots}, _, _, _), do: {:ok, {127, 0, 0, 1}, port, roots}
  end

  defp destination(_, _, _, _), do: @failure

  defp connect(host, path, ip, port, roots, headers, body, deadline, watcher) do
    opts = [
      hostname: host,
      protocols: [:http1],
      mode: :passive,
      max_header_list_size: 10_240,
      transport_opts: [
        cb_info: {BoundedTCP, :tcp, :tcp_closed, :tcp_error, :tcp_passive},
        verify: :verify_peer,
        cacerts: roots,
        timeout: remaining(deadline),
        send_timeout: remaining(deadline),
        send_timeout_close: true,
        versions: [:"tlsv1.2", :"tlsv1.3"],
        recbuf: 16_384,
        buffer: 16_384,
        inet4: tuple_size(ip) == 4,
        inet6: tuple_size(ip) == 8,
        max_handshake_size: 65_536
      ]
    ]

    with true <- remaining(deadline) > 0,
         {:ok, conn} <- Mint.HTTP.connect(:https, ip, port, opts) do
      socket = Mint.HTTP.get_socket(conn)

      try do
        ref = make_ref()
        send(watcher, {:register_socket, self(), socket, ref})

        with :ok <-
               (receive do
                  {^ref, :ok} -> :ok
                after
                  remaining(deadline) -> :error
                end),
             true <- remaining(deadline) > 0,
             {:ok, {^ip, ^port}} <- :ssl.peername(socket),
             :ok <- :ssl.setopts(socket, send_timeout: remaining(deadline)),
             {:ok, conn, request} <- Mint.HTTP.request(conn, "POST", path, headers, body),
             {:ok, raw} <- read_response(conn, request, Wire.new(), [], 0, deadline),
             true <- remaining(deadline) > 0 do
          {:ok, raw}
        else
          _ -> @failure
        end
      after
        Mint.HTTP.close(conn)
      end
    else
      _ -> @failure
    end
  end

  defp read_response(conn, ref, wire, chunks, size, deadline) do
    count =
      case wire.phase do
        {:length, n} when n > 0 -> min(n, 4096)
        {:chunk, n} when n > 0 -> min(n, 4096)
        :chunk_crlf -> 2
        _ -> 1
      end

    socket = Mint.HTTP.get_socket(conn)

    with true <- remaining(deadline) > 0,
         {:ok, data} when byte_size(data) <= count <-
           :ssl.recv(socket, count, remaining(deadline)),
         {:ok, wire} <- Wire.feed(wire, data),
         {:ok, conn, events} <- Mint.HTTP.stream(conn, {:ssl, socket, data}),
         {:ok, chunks, size, done} <- events(events, ref, chunks, size) do
      if done and wire.done do
        {:ok, IO.iodata_to_binary(Enum.reverse(chunks))}
      else
        read_response(conn, ref, wire, chunks, size, deadline)
      end
    else
      _ -> @failure
    end
  end

  defp events(events, ref, chunks, size) do
    Enum.reduce_while(events, {:ok, chunks, size, false}, fn
      {:data, ^ref, data}, {:ok, chunks, size, done} when size + byte_size(data) <= 16_384 ->
        {:cont, {:ok, [:binary.copy(data) | chunks], size + byte_size(data), done}}

      {:done, ^ref}, {:ok, chunks, size, _} ->
        {:cont, {:ok, chunks, size, true}}

      {:status, ^ref, 200}, acc ->
        {:cont, acc}

      {:headers, ^ref, _}, acc ->
        {:cont, acc}

      _, _ ->
        {:halt, @failure}
    end)
  end

  defp remaining(deadline), do: max(0, deadline - System.monotonic_time(:millisecond))
end
