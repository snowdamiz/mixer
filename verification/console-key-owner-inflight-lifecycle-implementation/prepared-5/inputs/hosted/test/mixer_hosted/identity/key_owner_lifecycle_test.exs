defmodule MixerHosted.Identity.KeyOwnerLifecycleTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{Admission, ConfiguredVerifier, KeyOwner, KeyOwnerSupervisor}

  @owners [
    __MODULE__.KOL01Owner,
    __MODULE__.KOL02Owner,
    __MODULE__.KOL03Owner,
    __MODULE__.KOL05Owner,
    __MODULE__.KOL06Owner,
    __MODULE__.KOL07Owner
  ]
  @admission_name __MODULE__.KOL04Admission
  @binding "lifecycle-disabled"
  @entry %{
    profile: %{
      profile_id: @binding,
      profile_version: 1,
      issuer: "https://issuer.lifecycle.invalid/oauth",
      audience: "mixer-api",
      client_id: "lifecycle-test",
      identity_class: :human,
      enabled: false
    },
    jwks_endpoint: %{host: "jwks.lifecycle.invalid", port: 443, path: "/keys"},
    transport: :hosted_https
  }
  @empty [:snapshots, :attempts, :flights, :waiters, :admitted, :negatives]

  # The standalone runner inspects only these exact test-owned registrations.
  def owner_names, do: @owners
  def admission_names, do: [@admission_name | @owners]

  setup_all do
    root =
      case System.get_env("MIXER_KEY_OWNER_LIFECYCLE_ROOT_PEM") do
        nil ->
          :public_key.cacerts_get()
          |> Enum.map(fn
            {:cert, der, _} -> der
            der -> der
          end)
          |> hd()

        path ->
          [{:Certificate, der, :not_encrypted}] = :public_key.pem_decode(File.read!(path))
          der
      end

    assert is_binary(root)
    {:ok, root: root}
  end

  defp workers(name), do: Module.concat(name, FetchSupervisor)
  defp pointer(name), do: :persistent_term.get({Admission, name}, :absent)
  defp now, do: System.system_time(:second)

  defp options(name, root) do
    [
      name: name,
      manifest: [@entry],
      generation: 1,
      binding: @binding,
      ca_roots: [root],
      resolvers: [{{127, 0, 0, 1}, 9}]
    ]
  end

  defp evidence(name, observation) do
    case System.get_env("MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE") do
      nil -> :ok
      directory -> File.write!(Path.join(directory, name <> ".json"), Jason.encode!(observation))
    end
  end

  defp resume_owned(pid) do
    if Process.alive?(pid), do: :sys.resume(pid, 500), else: :already_stopped
  catch
    :exit, reason -> {:error, inspect(reason)}
  end

  defp stop_owned(pid) do
    if Process.alive?(pid), do: Supervisor.stop(pid, :normal, 1_000), else: :already_stopped
  catch
    :exit, reason -> {:error, inspect(reason)}
  end

  defp reap_caller(pid, monitor) do
    if Process.alive?(pid) do
      Process.exit(pid, :kill)

      assert_receive {:DOWN, ^monitor, :process, ^pid, _reason}, 1_000
    end

    Process.demonitor(monitor, [:flush])
    refute Process.alive?(pid)
  end

  defp component(name, root) do
    assert Process.whereis(name) == nil
    assert Process.whereis(workers(name)) == nil
    assert pointer(name) == :absent
    {:ok, pid} = KeyOwnerSupervisor.start_link(options(name, root))
    Process.unlink(pid)

    # Register exact-PID recovery before any test assertion or suspension.
    on_exit(fn ->
      resumed = resume_owned(pid)

      owned_children =
        Enum.filter([Process.whereis(name), Process.whereis(workers(name))], &is_pid/1)

      stopped = stop_owned(pid)

      observation = %{
        component_stopped: not Process.alive?(pid),
        observed_exact_children_stopped: Enum.all?(owned_children, &(not Process.alive?(&1))),
        owner_absent: Process.whereis(name) == nil,
        workers_absent: Process.whereis(workers(name)) == nil,
        admission_absent: pointer(name) == :absent,
        resume_result: inspect(resumed),
        stop_result: inspect(stopped)
      }

      evidence(Atom.to_string(name) <> "-cleanup", observation)
      assert observation.component_stopped
      assert observation.observed_exact_children_stopped
      assert observation.owner_absent
      assert observation.workers_absent
      assert observation.admission_absent
      assert stopped in [:ok, :already_stopped]
    end)

    {pid, Process.whereis(name), :sys.get_state(name)}
  end

  defp wait_until(fun, remaining \\ 100)
  defp wait_until(fun, 0), do: assert(fun.())

  defp wait_until(fun, remaining) do
    if fun.() do
      :ok
    else
      Process.sleep(10)
      wait_until(fun, remaining - 1)
    end
  end

  defp assert_empty(state) do
    for key <- @empty, do: assert(state[key] == %{})
    assert DynamicSupervisor.count_children(state.workers).active == 0
  end

  defp stale_lease(state, permit) do
    # Rejection-only value: disabled profiles never acquire an authenticated lease.
    %KeyOwner.Lease{
      epoch: state.epoch,
      generation: state.generation,
      id: @binding,
      snapshot_generation: make_ref(),
      snapshot: nil,
      permit: permit
    }
  end

  defp assert_stopped(component, name, owner, state) do
    worker_pid = Process.whereis(state.workers)
    assert is_pid(worker_pid)
    assert :ok = Supervisor.stop(component, :normal, 1_000)
    refute Process.alive?(owner)
    refute Process.alive?(worker_pid)
    assert Process.whereis(name) == nil
    assert Process.whereis(state.workers) == nil
    assert :ets.info(state.table) == :undefined
    assert pointer(name) == :absent
    assert {:error, :identity_unavailable} = Admission.acquire(name, :configured)

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate(name, :configured, "synthetic", now())
  end

  test "KOL01 ordinary parent shutdown clears its exact admission", %{root: root} do
    name = __MODULE__.KOL01Owner
    {component, owner, state} = component(name, root)
    assert Process.info(owner, :trap_exit) == {:trap_exit, true}
    assert :ets.info(state.table, :owner) == owner
    assert pointer(name) == state.table
    assert_empty(state)
    assert {:ok, permit} = Admission.acquire(name, :configured)
    assert :ok = Admission.release(permit)

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(name, :configured, "synthetic", now())

    assert_empty(:sys.get_state(owner))
    assert_stopped(component, name, owner, state)
  end

  test "KOL02 explicit child termination and restart reject old permits", %{root: root} do
    name = __MODULE__.KOL02Owner
    {component, owner, old} = component(name, root)
    workers = Process.whereis(old.workers)
    assert {:ok, old_permit} = Admission.acquire(name, :configured)
    old_lease = stale_lease(old, old_permit)
    assert :ok = Supervisor.terminate_child(component, KeyOwner)
    refute Process.alive?(owner)
    assert Process.whereis(name) == nil
    assert Process.whereis(old.workers) == workers
    assert :ets.info(old.table) == :undefined
    assert pointer(name) == :absent
    assert {:ok, replacement} = Supervisor.restart_child(component, KeyOwner)
    current = :sys.get_state(replacement)
    refute replacement == owner
    refute current.table == old.table
    refute current.epoch == old.epoch
    assert_empty(current)
    assert pointer(name) == current.table
    assert {:ok, permit} = Admission.acquire(name, :configured)
    assert {:error, :identity_unavailable} = KeyOwner.checkout(name, old_permit, now())
    assert {:error, :identity_unavailable} = KeyOwner.finish(name, old_lease)
    assert :ok = KeyOwner.release(name, old_permit)
    assert :ok = Admission.release(old_permit)
    assert Admission.valid?(permit, current.table, self())
    assert :ok = Admission.release(permit)
    assert_stopped(component, name, replacement, current)
  end

  test "KOL03 forced death fails closed across the suspended restart barrier", %{root: root} do
    name = __MODULE__.KOL03Owner
    {component, owner, old} = component(name, root)
    old_workers = Process.whereis(old.workers)
    assert {:ok, permit} = Admission.acquire(name, :configured)
    lease = stale_lease(old, permit)
    monitor = Process.monitor(owner)
    assert :ok = :sys.suspend(component, 500)

    try do
      Process.exit(owner, :kill)
      assert_receive {:DOWN, ^monitor, :process, ^owner, :killed}, 1_000
      assert :ets.info(old.table) == :undefined
      assert pointer(name) == old.table
      assert Process.whereis(name) == nil
      assert Process.whereis(old.workers) == old_workers
      assert {:error, :identity_unavailable} = Admission.acquire(name, :configured)

      assert {:error, :identity_unavailable} =
               ConfiguredVerifier.authenticate(name, :configured, "synthetic", now())

      assert {:error, :identity_unavailable} = KeyOwner.finish(name, lease)
    after
      assert :ok = resume_owned(component)
      Process.demonitor(monitor, [:flush])
    end

    wait_until(fn ->
      replacement = Process.whereis(name)

      is_pid(replacement) and replacement != owner and
        Process.whereis(old.workers) != old_workers
    end)

    replacement = Process.whereis(name)
    current = :sys.get_state(replacement)
    refute current.table == old.table
    refute current.epoch == old.epoch
    assert_empty(current)
    assert pointer(name) == current.table
    assert {:error, :identity_unavailable} = KeyOwner.checkout(name, permit, now())
    assert {:error, :identity_unavailable} = KeyOwner.finish(name, lease)
    assert :ok = Admission.release(permit)
    assert_stopped(component, name, replacement, current)
  end

  test "KOL04 close requires the current table and its creator" do
    name = @admission_name
    assert pointer(name) == :absent
    old = Admission.new(name, %{@binding => @entry}, @binding)
    current = Admission.new(name, %{@binding => @entry}, @binding)

    try do
      refute Admission.close(name, old)
      assert pointer(name) == current
      parent = self()
      reply = make_ref()

      {caller, monitor} =
        spawn_monitor(fn -> send(parent, {reply, Admission.close(name, current)}) end)

      try do
        assert_receive {^reply, false}, 1_000
        assert_receive {:DOWN, ^monitor, :process, ^caller, :normal}, 1_000
      after
        reap_caller(caller, monitor)
      end

      assert pointer(name) == current
      assert :ets.delete(old)
      refute Admission.close(name, old)
      assert pointer(name) == current
      assert Admission.close(name, current)
      refute Admission.close(name, current)
      assert pointer(name) == :absent
      assert :ets.info(current, :owner) == self()
      refute function_exported?(Admission, :close, 1)
    after
      # These are exact test-created tables; no unconditional registry erasure.
      Admission.close(name, current)
      for table <- [old, current], :ets.info(table, :owner) == self(), do: :ets.delete(table)

      observation = %{
        admission_absent: pointer(name) == :absent,
        exact_tables_deleted: Enum.all?([old, current], &(:ets.info(&1) == :undefined))
      }

      evidence("KOL04-cleanup", observation)
      assert observation.admission_absent
      assert observation.exact_tables_deleted
    end
  end

  test "KOL05 duplicate registered start preserves the first table", %{root: root} do
    name = __MODULE__.KOL05Owner
    {component, owner, state} = component(name, root)

    assert {:error, {:already_started, ^owner}} =
             KeyOwner.start_link(
               Keyword.put(options(name, root), :worker_supervisor, state.workers)
             )

    assert Process.whereis(name) == owner
    assert pointer(name) == state.table
    assert :ets.info(state.table, :owner) == owner
    assert :sys.get_state(owner).epoch == state.epoch
    assert_empty(:sys.get_state(owner))
    assert_stopped(component, name, owner, state)
  end

  test "KOL06 invalid ordinary startup never publishes admission", %{root: root} do
    name = __MODULE__.KOL06Owner

    on_exit(fn ->
      wait_until(fn -> Process.whereis(name) == nil and Process.whereis(workers(name)) == nil end)

      observation = %{
        owner_absent: Process.whereis(name) == nil,
        workers_absent: Process.whereis(workers(name)) == nil,
        admission_absent: pointer(name) == :absent
      }

      evidence("KOL06-cleanup", observation)

      assert observation.owner_absent and observation.workers_absent and
               observation.admission_absent
    end)

    for invalid <- [
          Keyword.put(options(name, root), :manifest, []),
          Keyword.put(options(name, root), :binding, "missing"),
          Keyword.put(options(name, root), :ca_roots, [])
        ] do
      parent = self()
      reply = make_ref()

      {caller, monitor} =
        spawn_monitor(fn ->
          Process.flag(:trap_exit, true)
          result = KeyOwnerSupervisor.start_link(invalid)

          # Unexpected success is still stopped by its exact owner before reporting.
          if match?({:ok, _}, result), do: Supervisor.stop(elem(result, 1), :normal, 1_000)
          send(parent, {reply, result})
        end)

      try do
        assert_receive {^reply,
                        {:error,
                         {:shutdown,
                          {:failed_to_start_child, KeyOwner, :invalid_identity_configuration}}}},
                       1_000

        assert_receive {:DOWN, ^monitor, :process, ^caller, :normal}, 1_000
      after
        reap_caller(caller, monitor)
      end

      assert Process.whereis(name) == nil
      assert Process.whereis(workers(name)) == nil
      assert pointer(name) == :absent
    end
  end

  test "KOL07 worker supervisor death restarts both empty children", %{root: root} do
    name = __MODULE__.KOL07Owner
    {component, owner, old} = component(name, root)
    old_workers = Process.whereis(old.workers)
    assert_empty(old)
    assert {:ok, permit} = Admission.acquire(name, :configured)
    lease = stale_lease(old, permit)
    owner_monitor = Process.monitor(owner)
    workers_monitor = Process.monitor(old_workers)
    Process.exit(old_workers, :kill)
    assert_receive {:DOWN, ^workers_monitor, :process, ^old_workers, :killed}, 1_000
    assert_receive {:DOWN, ^owner_monitor, :process, ^owner, :shutdown}, 1_000
    wait_until(fn -> is_pid(Process.whereis(name)) and Process.whereis(name) != owner end)
    replacement = Process.whereis(name)
    current = :sys.get_state(replacement)
    refute Process.whereis(current.workers) == old_workers
    refute current.table == old.table
    refute current.epoch == old.epoch
    assert :ets.info(old.table) == :undefined
    assert pointer(name) == current.table
    assert_empty(current)
    assert {:error, :identity_unavailable} = KeyOwner.checkout(name, permit, now())
    assert {:error, :identity_unavailable} = KeyOwner.finish(name, lease)
    assert :ok = Admission.release(permit)
    assert_stopped(component, name, replacement, current)
  end
end
