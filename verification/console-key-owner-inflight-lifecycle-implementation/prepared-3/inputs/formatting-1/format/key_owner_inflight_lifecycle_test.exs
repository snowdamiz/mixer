defmodule MixerHosted.Identity.KeyOwnerInflightLifecycleTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{
    Admission,
    ConfiguredVerifier,
    KeyOwner,
    KeyOwnerSupervisor,
    TLSFixture
  }

  defmodule Recorder do
    use GenServer

    def start_link(case_id, name), do: GenServer.start_link(__MODULE__, {case_id, name})
    def put(pid, key, value), do: GenServer.call(pid, {:put, key, value})
    def get(pid), do: GenServer.call(pid, :get)
    def track(pid, role, resource), do: GenServer.call(pid, {:track, role, resource})

    def init({case_id, name}) do
      {:ok,
       %{
         case_id: case_id,
         name: name,
         stage: "created",
         resources: %{},
         values: %{},
         observations: %{},
         raw_reply: %{
           kind: "unobserved",
           result: "unobserved",
           before_deadline: false,
           observed_at_ms: -1,
           pointer: "unobserved",
           owner_alive: false,
           table_alive: false
         },
         public_reply: "unobserved",
         fault_reason: "unobserved",
         deadline_margin_ms: -1,
         pointer_samples: [],
         cleanup_errors: [],
         cleanup: %{}
       }}
    end

    def handle_call({:put, key, value}, _, state), do: {:reply, :ok, Map.put(state, key, value)}
    def handle_call(:get, _, state), do: {:reply, state, state}

    def handle_call({:track, role, resource}, _, state)
        when is_pid(resource) or is_port(resource) do
      resources =
        Map.put_new_lazy(state.resources, resource, fn ->
          monitor =
            if is_pid(resource),
              do: Process.monitor(resource),
              else: :erlang.monitor(:port, resource)

          %{role: role, monitor: monitor, down: false, reason: "unobserved", down_ms: -1}
        end)

      {:reply, :ok, %{state | resources: resources}}
    end

    def handle_info({:DOWN, monitor, _, resource, reason}, state) do
      resources =
        case state.resources[resource] do
          %{monitor: ^monitor} = value ->
            Map.put(state.resources, resource, %{
              value
              | down: true,
                reason: inspect(reason, limit: 30),
                down_ms: System.monotonic_time(:millisecond)
            })

          _ ->
            state.resources
        end

      {:noreply, %{state | resources: resources}}
    end
  end

  @owners [__MODULE__.GracefulOwner, __MODULE__.WorkerDeathOwner]
  @entry %{
    profile: %{
      profile_id: "inflight",
      profile_version: 1,
      issuer: "https://issuer.fixture.invalid/oauth",
      audience: "mixer-api",
      client_id: "inflight-test",
      identity_class: :human,
      enabled: true
    },
    jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
    transport: :hosted_https
  }
  @facts [
    :tls_preconditions,
    :raw_explicit_reply,
    :fresh_denial,
    :raw_port_closed_while_held,
    :parent_stop_pending,
    :old_resources_down_at_stop,
    :owner_alive_at_raw_reply,
    :table_alive_at_raw_reply,
    :pointer_absent_at_raw_reply,
    :replacement_observed,
    :replacement_empty,
    :old_resources_down_before_replacement,
    :old_permit_rejected,
    :stale_lease_rejected,
    :public_denial,
    :callback_clean
  ]

  def owner_names, do: @owners
  defp now, do: System.system_time(:second)
  defp mono, do: System.monotonic_time(:millisecond)
  defp pointer(name), do: :persistent_term.get({Admission, name}, :absent)
  defp workers(name), do: Module.concat(name, FetchSupervisor)
  defp alive?(pid) when is_pid(pid), do: Process.alive?(pid)
  defp alive?(port) when is_port(port), do: Port.info(port) != nil
  defp alive?(_), do: false

  defp wait_until(fun, remaining \\ 100)
  defp wait_until(fun, 0), do: assert(fun.())

  defp wait_until(fun, remaining) do
    if fun.() do
      :ok
    else
      Process.sleep(5)
      wait_until(fun, remaining - 1)
    end
  end

  defp value(recorder, key, value) do
    state = Recorder.get(recorder)
    Recorder.put(recorder, :values, Map.put(state.values, key, value))
    value
  end

  defp fact(recorder, key, value) do
    state = Recorder.get(recorder)
    Recorder.put(recorder, :observations, Map.put(state.observations, key, value))
    value
  end

  defp track(recorder, role, resource) do
    if is_pid(resource) or is_port(resource), do: Recorder.track(recorder, role, resource)
    resource
  end

  # Test instrumentation follows the pinned OTP 29 sslsocket record. Product code
  # never reads it. Capture per-socket handlers/senders and the handle's raw port.
  defp socket_resources(recorder, role, socket) do
    assert is_tuple(socket) and tuple_size(socket) == 8 and elem(socket, 0) == :sslsocket
    for pid <- [elem(socket, 2), elem(socket, 3)], is_pid(pid), do: track(recorder, role, pid)
    ports(recorder, role, elem(socket, 1))
    socket
  end

  defp ports(recorder, role, port) when is_port(port), do: track(recorder, role, port)

  defp ports(recorder, role, tuple) when is_tuple(tuple),
    do: ports(recorder, role, Tuple.to_list(tuple))

  defp ports(recorder, role, list) when is_list(list),
    do: Enum.each(list, &ports(recorder, role, &1))

  defp ports(_, _, _), do: :ok

  defp sample_pointer(recorder, phase) do
    state = Recorder.get(recorder)
    current = pointer(state.name)
    old = state.values[:old]

    kind =
      cond do
        current == :absent ->
          "absent"

        old != nil and current == old.table ->
          "old"

        is_reference(current) and :ets.info(current, :owner) == Process.whereis(state.name) ->
          "current"

        true ->
          "other"
      end

    sample = %{phase: phase, at_ms: mono(), kind: kind, table: inspect(current)}
    Recorder.put(recorder, :pointer_samples, state.pointer_samples ++ [sample])
    current
  end

  defp start_case(case_id, name) do
    {:ok, recorder} = Recorder.start_link(case_id, name)
    Process.unlink(recorder)

    on_exit(fn ->
      try do
        cleanup(recorder)
      rescue
        exception ->
          cleanup_error(recorder, "cleanup collector raised: #{Exception.message(exception)}")
      catch
        kind, reason -> cleanup_error(recorder, "cleanup collector #{kind}: #{inspect(reason)}")
      end

      state = Recorder.get(recorder)
      :ok = GenServer.stop(recorder, :normal, 500)
      report = report(state, not Process.alive?(recorder))
      write_evidence(case_id <> "-observation.json", report)
      assert report.cleanup_errors == []

      assert Enum.all?(
               Map.drop(report.cleanup, [
                 :resume_result,
                 :component_stop_result,
                 :fixture_stop_result
               ]),
               fn {_, value} -> value == true end
             )

      assert report.cleanup.component_stop_result in [":ok", ":already_stopped"]
      assert report.cleanup.fixture_stop_result in [":ok", ":already_stopped"]
    end)

    assert Process.whereis(name) == nil and Process.whereis(workers(name)) == nil
    assert pointer(name) == :absent
    {:ok, fixture} = TLSFixture.start_link()
    Process.unlink(fixture)
    value(recorder, :fixture, track(recorder, :fixture, fixture))
    fixture_state = :sys.get_state(fixture)

    value(
      recorder,
      :listener,
      socket_resources(recorder, :listener_socket, fixture_state.listener)
    )

    value(recorder, :acceptor, track(recorder, :acceptor, fixture_state.acceptor))
    authority = GenServer.call(fixture, :authority)
    :ok = TLSFixture.configure(fixture, {:barrier, self(), TLSFixture.response("{\"keys\":[]}")})

    options = [
      name: name,
      manifest: [@entry],
      generation: 1,
      binding: "inflight",
      ca_roots: [authority.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      fixture: Map.take(authority, [:ip, :port])
    ]

    {:ok, component} = KeyOwnerSupervisor.start_fixture(options)
    Process.unlink(component)
    value(recorder, :component, track(recorder, :component, component))
    owner = value(recorder, :owner, track(recorder, :owner, Process.whereis(name)))
    old = value(recorder, :old, :sys.get_state(owner))
    value(recorder, :workers, track(recorder, :workers, Process.whereis(old.workers)))
    {:ok, probe_permit} = Admission.acquire(name, :configured)
    value(recorder, :permit, probe_permit)
    value(recorder, :options, options)
    parent = self()

    {raw, _monitor} =
      spawn_monitor(fn ->
        {:ok, permit} = Admission.acquire(name, :configured)
        send(parent, {:raw_permit, self(), permit})

        result =
          try do
            reply = GenServer.call(owner, {:checkout, permit, now()}, 2_200)
            %{kind: "reply", result: inspect(reply), before_deadline: false}
          catch
            :exit, reason ->
              %{kind: "exit", result: inspect(reason, limit: 30), before_deadline: false}
          end

        send(
          parent,
          {:raw_checkout, self(), result, mono(), pointer(name), Process.alive?(owner),
           :ets.info(old.table) != :undefined}
        )

        Admission.release(permit)
      end)

    value(recorder, :raw_caller, track(recorder, :raw_caller, raw))
    assert_receive {:raw_permit, ^raw, permit}, 500
    value(recorder, :raw_permit, permit)

    {public, _monitor} =
      spawn_monitor(fn ->
        result = ConfiguredVerifier.authenticate(name, :configured, "synthetic", now())
        send(parent, {:public_checkout, self(), result})
      end)

    value(recorder, :public_caller, track(recorder, :public_caller, public))
    assert_receive {:tls_response_ready, handler}, 700
    value(recorder, :server_handler, track(recorder, :server_handler, handler))
    server = :sys.get_state(fixture)
    assert map_size(server.sockets) == 1
    server_socket = Map.fetch!(server.sockets, handler)
    value(recorder, :server_socket, socket_resources(recorder, :server_socket, server_socket))
    assert [%{request: request, tls: tls}] = server.requests
    assert String.starts_with?(request, "GET /keys HTTP/1.1\r\n")
    assert tls[:sni_hostname] in ['jwks.fixture.invalid', "jwks.fixture.invalid"]
    assert tls[:protocol] in [:"tlsv1.2", :"tlsv1.3"]
    value(recorder, :tls_protocol, Atom.to_string(tls[:protocol]))

    wait_until(fn -> map_size(:sys.get_state(owner).waiters) == 2 end)
    state = :sys.get_state(owner)
    assert [{flight, _}] = Map.to_list(state.flights)
    value(recorder, :flight, track(recorder, :flight, flight))
    f = value(recorder, :flight_state, :sys.get_state(flight))
    assert is_pid(f.connection) and is_port(f.raw_socket) and f.socket != nil
    assert Enum.all?([f.connection, f.raw_socket, f.worker], &alive?/1)
    value(recorder, :worker, track(recorder, :worker, f.worker))
    value(recorder, :controller, track(recorder, :controller, f.connection))
    value(recorder, :raw_socket, track(recorder, :raw_socket, f.raw_socket))
    socket_resources(recorder, :client_socket, f.socket)
    value(recorder, :deadline, elem(hd(Map.to_list(state.flights)), 1).deadline)
    assert state.snapshots == %{} and map_size(state.waiters) == 2
    fact(recorder, :tls_preconditions, true)
    Recorder.put(recorder, :stage, "completed-tls-pending-jwks")
    recorder
  end

  defp hold_controller(recorder) do
    state = Recorder.get(recorder)
    :ok = :sys.suspend(state.values.controller, 300)
    value(recorder, :suspended, true)
    margin = state.values.deadline - mono()
    Recorder.put(recorder, :deadline_margin_ms, margin)
    assert margin >= 750
    sample_pointer(recorder, "before-trigger")
    Recorder.put(recorder, :stage, "controller-held-trigger-ready")
    state.values
  end

  defp raw_reply(recorder) do
    state = Recorder.get(recorder)
    raw = state.values.raw_caller
    assert_receive {:raw_checkout, ^raw, result, at, ptr, owner_alive, table_alive}, 600

    result =
      Map.merge(result, %{
        before_deadline: at < state.values.deadline,
        observed_at_ms: at,
        pointer: inspect(ptr),
        owner_alive: owner_alive,
        table_alive: table_alive
      })

    Recorder.put(recorder, :raw_reply, result)

    fact(
      recorder,
      :raw_explicit_reply,
      result.kind == "reply" and result.result == "{:error, :identity_unavailable}" and
        result.before_deadline
    )

    fact(recorder, :pointer_absent_at_raw_reply, ptr == :absent)
    fact(recorder, :owner_alive_at_raw_reply, owner_alive)
    fact(recorder, :table_alive_at_raw_reply, table_alive)
    sample_pointer(recorder, "raw-reply-observed")
  end

  defp release(recorder) do
    state = Recorder.get(recorder)
    controller = state.values[:controller]

    result =
      if alive?(controller) and state.values[:suspended] do
        try do
          :sys.resume(controller, 300)
        catch
          :exit, reason -> {:error, reason}
        end
      else
        :already_stopped
      end

    value(recorder, :resume_result, inspect(result))

    value(
      recorder,
      :resume_results,
      (Recorder.get(recorder).values[:resume_results] || []) ++ [inspect(result)]
    )

    if result not in [:ok, :already_stopped],
      do: cleanup_error(recorder, "controller resume failed: #{inspect(result)}")

    value(recorder, :suspended, false)

    if alive?(state.values[:server_handler]),
      do: send(state.values.server_handler, :release_response)

    value(recorder, :barrier_released, true)
  end

  defp public_reply(recorder) do
    state = Recorder.get(recorder)
    public = state.values.public_caller
    assert_receive {:public_checkout, ^public, result}, 2_500
    Recorder.put(recorder, :public_reply, inspect(result))
    fact(recorder, :public_denial, result == {:error, :identity_unavailable})
  end

  defp stop(pid) do
    if alive?(pid), do: GenServer.stop(pid, :normal, 1_000), else: :already_stopped
  catch
    :exit, reason -> {:error, reason}
  end

  defp cleanup(recorder) do
    release(recorder)
    state = Recorder.get(recorder)

    for role <- [:owner, :workers] do
      registered = Process.whereis(if role == :owner, do: state.name, else: workers(state.name))
      if is_pid(registered), do: track(recorder, role, registered)
    end

    component_result = stop(state.values[:component])

    if component_result not in [:ok, :already_stopped],
      do: cleanup_error(recorder, "component stop failed: #{inspect(component_result)}")

    fixture = state.values[:fixture]

    peer_closed =
      not alive?(fixture) or wait_observed(fn -> TLSFixture.info(fixture).closed == 1 end)

    if not peer_closed,
      do: cleanup_error(recorder, "server peer closure not observed before fixture stop")

    fixture_info =
      if alive?(state.values[:fixture]), do: TLSFixture.info(state.values.fixture), else: nil

    if fixture_info != nil, do: value(recorder, :fixture_info, fixture_info)
    fixture_result = stop(state.values[:fixture])

    if fixture_result not in [:ok, :already_stopped],
      do: cleanup_error(recorder, "fixture stop failed: #{inspect(fixture_result)}")

    state = Recorder.get(recorder)

    for key <- [:raw_caller, :public_caller, :stop_caller] do
      pid = state.values[key]
      if alive?(pid), do: Process.exit(pid, :kill)
    end

    # Only these exact recorded resources are observed; no VM/process inventory.
    all_gone =
      wait_observed(fn ->
        Enum.all?(Recorder.get(recorder).resources, fn {resource, _} -> not alive?(resource) end)
      end)

    all_down =
      wait_observed(fn ->
        Enum.all?(Recorder.get(recorder).resources, fn {_, resource} -> resource.down end)
      end)

    if not all_gone or not all_down,
      do: cleanup_error(recorder, "recorded owned resource remains or DOWN missing")

    state = Recorder.get(recorder)
    info = state.values[:fixture_info]

    Recorder.put(recorder, :cleanup, %{
      resume_result: state.values[:resume_result] || "unobserved",
      component_stop_result: inspect(component_result),
      fixture_stop_result: inspect(fixture_result),
      barrier_released: state.values[:barrier_released] == true,
      all_resources_down: Enum.all?(state.resources, fn {_, resource} -> resource.down end),
      current_admission_absent: pointer(state.name) == :absent,
      owner_absent: Process.whereis(state.name) == nil,
      workers_absent: Process.whereis(workers(state.name)) == nil,
      old_table_gone:
        state.values[:old] == nil or :ets.info(state.values.old.table) == :undefined,
      key_directory_removed: info != nil and info.key_dir_removed,
      fixture_peer_closed: info != nil and info.accepted == 1 and info.closed == 1
    })
  end

  defp wait_observed(fun, remaining \\ 100)
  defp wait_observed(fun, 0), do: fun.()

  defp wait_observed(fun, remaining) do
    if fun.() do
      true
    else
      Process.sleep(5)
      wait_observed(fun, remaining - 1)
    end
  catch
    :exit, _ -> false
  end

  defp cleanup_error(recorder, message) do
    state = Recorder.get(recorder)
    Recorder.put(recorder, :cleanup_errors, state.cleanup_errors ++ [message])
  end

  defp report(state, recorder_stopped) do
    cleanup_defaults = %{
      resume_result: "unobserved",
      component_stop_result: "unobserved",
      fixture_stop_result: "unobserved",
      barrier_released: false,
      all_resources_down: false,
      current_admission_absent: false,
      owner_absent: false,
      workers_absent: false,
      old_table_gone: false,
      key_directory_removed: false,
      fixture_peer_closed: false
    }

    %{
      schema: 1,
      case_id: state.case_id,
      stage: state.stage,
      deadline_margin_ms: state.deadline_margin_ms,
      tls_protocol: state.values[:tls_protocol] || "unobserved",
      raw_reply: state.raw_reply,
      resume_results: state.values[:resume_results] || [],
      public_reply: state.public_reply,
      fault_reason: state.fault_reason,
      cleanup_errors: state.cleanup_errors,
      observations: Map.new(@facts, &{&1, Map.get(state.observations, &1, false)}),
      pointer_samples: state.pointer_samples,
      resources:
        Enum.map(state.resources, fn {resource, entry} ->
          %{
            role: Atom.to_string(entry.role),
            id: inspect(resource),
            down: entry.down,
            reason: entry.reason,
            down_ms: entry.down_ms
          }
        end),
      cleanup:
        Map.put(Map.merge(cleanup_defaults, state.cleanup), :recorder_stopped, recorder_stopped)
    }
  end

  defp write_evidence(name, value) do
    case System.get_env("MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE") do
      nil -> :ok
      directory -> File.write!(Path.join(directory, name), Jason.encode!(value, pretty: true))
    end
  end

  test "KOL08-GRACEFUL ordinary parent shutdown drains a pending real TLS response" do
    recorder = start_case("KOL08-GRACEFUL", __MODULE__.GracefulOwner)

    try do
      values = hold_controller(recorder)
      parent = self()

      {stopper, _monitor} =
        spawn_monitor(fn ->
          result = Supervisor.stop(values.component, :normal, :infinity)
          send(parent, {:component_stopped, self(), result})
        end)

      value(recorder, :stop_caller, track(recorder, :stop_caller, stopper))
      raw_reply(recorder)
      wait_until(fn -> Port.info(values.raw_socket) == nil end)
      fact(recorder, :raw_port_closed_while_held, true)

      fact(
        recorder,
        :fresh_denial,
        Admission.acquire(__MODULE__.GracefulOwner, :configured) ==
          {:error, :identity_unavailable} and
          ConfiguredVerifier.authenticate(
            __MODULE__.GracefulOwner,
            :configured,
            "synthetic",
            now()
          ) == {:error, :identity_unavailable}
      )

      refute_receive {:component_stopped, ^stopper, _}, 50
      fact(recorder, :parent_stop_pending, alive?(stopper) and alive?(values.controller))
      Recorder.put(recorder, :stage, "graceful-drain-held")
      release(recorder)
      assert_receive {:component_stopped, ^stopper, :ok}, 1_000

      fact(
        recorder,
        :old_resources_down_at_stop,
        Enum.all?(
          [
            values.component,
            values.owner,
            values.workers,
            values.flight,
            values.worker,
            values.controller,
            values.raw_socket
          ],
          &(not alive?(&1))
        )
      )

      public_reply(recorder)

      for key <- [
            :raw_explicit_reply,
            :fresh_denial,
            :raw_port_closed_while_held,
            :parent_stop_pending,
            :old_resources_down_at_stop,
            :owner_alive_at_raw_reply,
            :table_alive_at_raw_reply,
            :pointer_absent_at_raw_reply,
            :public_denial
          ] do
        assert Recorder.get(recorder).observations[key], "missing graceful observation #{key}"
      end

      Recorder.put(recorder, :stage, "graceful-gate-passed")
    after
      cleanup(recorder)
    end
  end

  test "KOL09-KILL records the active-flight worker-supervisor death resource gate" do
    recorder = start_case("KOL09-KILL", __MODULE__.WorkerDeathOwner)

    try do
      values = hold_controller(recorder)
      owner_monitor = Process.monitor(values.owner)
      workers_monitor = Process.monitor(values.workers)
      Process.exit(values.workers, :kill)
      assert_receive {:DOWN, ^workers_monitor, :process, _, :killed}, 500
      raw_reply(recorder)
      assert_receive {:DOWN, ^owner_monitor, :process, _, reason}, 700
      Recorder.put(recorder, :fault_reason, inspect(reason, limit: 50))
      fact(recorder, :callback_clean, reason == :shutdown)

      wait_until(fn ->
        is_pid(Process.whereis(__MODULE__.WorkerDeathOwner)) and
          Process.whereis(__MODULE__.WorkerDeathOwner) != values.owner
      end)

      replacement = Process.whereis(__MODULE__.WorkerDeathOwner)
      current = :sys.get_state(replacement)
      track(recorder, :owner, replacement)
      track(recorder, :workers, Process.whereis(current.workers))

      fact(
        recorder,
        :replacement_observed,
        current.table != values.old.table and current.epoch != values.old.epoch
      )

      initially_empty =
        Enum.all?(
          [:snapshots, :attempts, :flights, :waiters, :admitted, :negatives],
          &(current[&1] == %{})
        ) and DynamicSupervisor.count_children(current.workers).active == 0

      fact(
        recorder,
        :old_resources_down_before_replacement,
        Enum.all?(
          [values.flight, values.worker, values.controller, values.raw_socket],
          &(not alive?(&1))
        )
      )

      assert sample_pointer(recorder, "replacement-while-old-controller-held") == current.table
      Recorder.put(recorder, :stage, "worker-death-order-witness-retained")
      release(recorder)
      public_reply(recorder)

      wait_until(fn ->
        Enum.all?(
          [values.flight, values.worker, values.controller, values.raw_socket],
          &(not alive?(&1))
        )
      end)

      after_drain = :sys.get_state(replacement)

      fact(
        recorder,
        :replacement_empty,
        initially_empty and
          Enum.all?(
            [:snapshots, :attempts, :flights, :waiters, :admitted, :negatives],
            &(after_drain[&1] == %{})
          )
      )

      fact(
        recorder,
        :old_permit_rejected,
        KeyOwner.checkout(__MODULE__.WorkerDeathOwner, values.permit, now()) ==
          {:error, :identity_unavailable}
      )

      lease = %KeyOwner.Lease{
        epoch: values.old.epoch,
        generation: values.old.generation,
        id: "inflight",
        snapshot_generation: make_ref(),
        snapshot: :synthetic_rejection_only,
        permit: values.permit
      }

      fact(
        recorder,
        :stale_lease_rejected,
        KeyOwner.finish(__MODULE__.WorkerDeathOwner, lease) == {:error, :identity_unavailable}
      )

      assert pointer(__MODULE__.WorkerDeathOwner) == current.table

      # Keep this adverse witness red until an independently reviewed correction
      # is justified by its actual callback reason and old-resource ordering.
      for key <- [
            :raw_explicit_reply,
            :replacement_observed,
            :replacement_empty,
            :old_resources_down_before_replacement,
            :callback_clean,
            :old_permit_rejected,
            :stale_lease_rejected,
            :public_denial
          ] do
        assert Recorder.get(recorder).observations[key],
               "failed active-flight resource gate #{key}"
      end

      Recorder.put(recorder, :stage, "worker-death-resource-gate-passed")
    after
      cleanup(recorder)
    end
  end
end
