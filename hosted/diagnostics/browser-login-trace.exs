defmodule MixerBrowserLoginTrace do
  @moduledoc false
  @owner MixerHosted.BrowserAuth.RuntimeOwner
  @store MixerHosted.BrowserAuth.Store
  @proxy R932.PhaseCommitProxy
  @targets [
    {@owner, :begin_login, 4},
    {@owner, :prepare_begin, 3},
    {@owner, :publish, 2},
    {@owner, :finish_receipt, 3},
    {@store, :discover_begin, 1},
    {@store, :begin_login, 2},
    {@store, :transaction_event, 4},
    {@store, :receipt_outcome, 0},
    {MixerHosted.BrowserAuth.Catalog, :check_function_surface!, 4},
    {MixerHosted.BrowserAuth.ActiveCatalog, :check_function_surface!, 4},
    {MixerHosted.BrowserAuth.RelationCatalog, :check_relation_surface!, 3},
    {@proxy, :connection, 3},
    {:gen_tcp, :connect, 4}
  ]

  def start do
    parent = self()
    {pid, monitor} = spawn_monitor(fn -> init(parent) end)

    receive do
      {:r1018_ready, ^pid, session} ->
        Process.demonitor(monitor, [:flush])
        {pid, session}

      {:DOWN, ^monitor, :process, ^pid, _} ->
        raise "R1018 diagnostic startup failed"
    after
      2000 ->
        Process.exit(pid, :kill)
        raise "R1018 diagnostic startup timeout"
    end
  end

  def stop({pid, session}) do
    monitor = Process.monitor(pid)
    send(pid, {:r1018_stop, self()})

    receive do
      {:r1018_stopped, ^pid} -> :ok
      {:DOWN, ^monitor, :process, ^pid, _} -> :ok
    after
      1000 -> Process.exit(pid, :kill)
    end

    # Destroy just this session, including all its patterns, even on timeout.
    try do
      :trace.session_destroy(session)
    catch
      :error, :badarg -> :ok
    end

    receive do
      {:DOWN, ^monitor, :process, ^pid, _} -> :ok
    after
      1000 -> IO.puts("R1018 cleanup_monitor_timeout")
    end

    Process.demonitor(monitor, [:flush])
  end

  defp init(parent) do
    Enum.each(@targets, fn {m, _, _} -> Code.ensure_loaded!(m) end)
    root = Path.expand("..", __DIR__)

    sources =
      for name <- [
            "lib/mixer_hosted/browser_auth/runtime_owner.ex",
            "lib/mixer_hosted/browser_auth/store.ex",
            "lib/mixer_hosted/browser_auth/catalog.ex",
            "lib/mixer_hosted/browser_auth/active_catalog.ex",
            "lib/mixer_hosted/browser_auth/relation_catalog.ex",
            "lib/mixer_hosted_web/browser_login_http.ex",
            "test/support/browser_commit_proxy.ex",
            "test/mixer_hosted/browser_auth/private_login_http_test.exs"
          ],
          do: {name, digest(File.read!(Path.join(root, name)))}

    beams =
      for m <- Enum.uniq(Enum.map(@targets, &elem(&1, 0))) do
        {^m, bytes, _} = :code.get_object_code(m)
        {m, digest(bytes)}
      end

    st = %{
      armed: false,
      events: 0,
      bytes: 0,
      truncated: false,
      starts: %{},
      active: MapSet.new(),
      proxy: MapSet.new(),
      connects: MapSet.new(),
      port: String.to_integer(System.fetch_env!("MIXER_BROWSER_STORAGE_PORT"))
    }

    st =
      emit(
        st,
        {:identity, System.version(), System.otp_release(), :erlang.system_info(:version),
         sources, beams}
      )

    session = :trace.session_create(:r1018_browser_login, self(), [])

    Enum.each(@targets, fn mfa ->
      1 = :trace.function(session, mfa, [{:_, [], [{:exception_trace}]}], [:local])
    end)

    :trace.process(session, :all, true, [:call, :monotonic_timestamp])
    send(parent, {:r1018_ready, self(), session})
    loop(Map.put(st, :session, session))
  end

  defp loop(st) do
    receive do
      {:r1018_stop, parent} ->
        :trace.process(st.session, :all, false, [:call])
        delivered = :trace.delivered(st.session, :all)
        drain(st, parent, delivered)

      message ->
        loop(event(message, st))
    end
  end

  defp drain(st, parent, delivered) do
    receive do
      {:trace_delivered, :all, ^delivered} ->
        IO.puts(
          "R1018 " <> inspect({:summary, st.events, st.bytes, st.truncated}, limit: :infinity)
        )

        send(parent, {:r1018_stopped, self()})

      message ->
        drain(event(message, st), parent, delivered)
    after
      500 ->
        IO.puts("R1018 cleanup_delivery_timeout")
        send(parent, {:r1018_stopped, self()})
    end
  end

  defp event(_, %{truncated: true} = st), do: st

  defp event({:trace_ts, pid, :call, {m, f, args}, t}, st) do
    key = {pid, m, f, length(args)}

    cond do
      {m, f, length(args)} == {@proxy, :connection, 3} ->
        # Retain no socket, owner, role, or arbitrary argument in output.
        st = %{st | armed: true, proxy: MapSet.put(st.proxy, pid)}

        case args do
          [socket, port, _] when port == st.port -> socket(st, pid, :frontend, socket)
          _ -> st
        end

      {m, f, length(args)} == {:gen_tcp, :connect, 4} ->
        case args do
          [{127, 0, 0, 1}, port, _, _] when port == st.port ->
            if MapSet.member?(st.proxy, pid),
              do: %{st | connects: MapSet.put(st.connects, pid)},
              else: st

          _ ->
            st
        end

      st.armed and {m, f, length(args)} == {@owner, :begin_login, 4} ->
        st = %{st | active: MapSet.put(st.active, pid)}
        phase_call(st, key, t, args)

      MapSet.member?(st.active, pid) and {m, f, length(args)} in @targets ->
        phase_call(st, key, t, args)

      true ->
        st
    end
  end

  defp event({:trace_ts, pid, kind, {:gen_tcp, :connect, 4}, value, _}, st)
       when kind in [:return_from, :exception_from] do
    if MapSet.member?(st.connects, pid) do
      st = %{st | connects: MapSet.delete(st.connects, pid)}

      case value do
        {:ok, sock} -> socket(st, pid, :backend, sock)
        _ -> emit(st, {:socket, pid, :backend, :unavailable})
      end
    else
      st
    end
  end

  defp event({:trace_ts, pid, kind, {m, f, a}, value, t}, st)
       when kind in [:return_from, :exception_from] do
    key = {pid, m, f, a}

    case Map.pop(st.starts, key) do
      {nil, _} ->
        st

      {start, starts} ->
        us = System.convert_time_unit(t - start, :native, :microsecond)
        st = emit(%{st | starts: starts}, {kind, pid, m, f, a, us, summary(value)})

        if {m, f, a} == {@owner, :begin_login, 4},
          do: %{st | active: MapSet.delete(st.active, pid)},
          else: st
    end
  end

  defp event(_, st), do: st

  defp phase_call(st, {pid, m, f, a} = key, t, args) do
    st = emit(%{st | starts: Map.put(st.starts, key, t)}, {:call, pid, m, f, a})

    if {m, f, a} == {@store, :transaction_event, 4} do
      case args do
        [_, _, %{query: q, result: {:ok, %{command: c, connection_id: id}}}, _]
        when q in ["begin", "commit", "rollback"] and c in [:begin, :commit, :rollback] and
               is_integer(id) and id > 0 ->
          emit(st, {:receipt, pid, q, c, id})

        [_, _, %{query: q}, _] when q in ["begin", "commit", "rollback"] ->
          emit(st, {:receipt, pid, q, :unavailable})

        _ ->
          st
      end
    else
      st
    end
  end

  defp summary(
         {:error, %{__struct__: MixerHosted.BrowserAuth.Store.Failure, phase: p, outcome: o}}
       )
       when p in [:admission, :effect, :decode, :commit] and
              o in [:not_started, :committed, :rolled_back, :unknown],
       do: {:store_failure, p, o}

  defp summary({:ok, _}), do: :ok
  defp summary({:error, _}), do: :error

  defp summary(v)
       when v in [
              :ok,
              :committed,
              :rolled_back,
              :unknown,
              :function_surface_verified,
              :relation_surface_verified
            ],
       do: v

  defp summary(_), do: :redacted

  defp socket(st, pid, side, sock) do
    option =
      case :inet.getopts(sock, [:nodelay]) do
        {:ok, [nodelay: v]} when is_boolean(v) -> v
        _ -> :unavailable
      end

    emit(st, {:socket, pid, side, :nodelay, option})
  end

  defp emit(st, row) do
    line = "R1018 " <> inspect(row, limit: :infinity, printable_limit: :infinity) <> "\n"
    # Reserve space and an event for the fixed final summary.
    if st.events < 255 and st.bytes + byte_size(line) <= 32_512 do
      IO.write(line)
      %{st | events: st.events + 1, bytes: st.bytes + byte_size(line)}
    else
      :trace.process(st.session, :all, false, [:call])

      %{
        st
        | truncated: true,
          starts: %{},
          active: MapSet.new(),
          proxy: MapSet.new(),
          connects: MapSet.new()
      }
    end
  end

  defp digest(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
end

handle = MixerBrowserLoginTrace.start()
ExUnit.after_suite(fn _result -> MixerBrowserLoginTrace.stop(handle) end)
