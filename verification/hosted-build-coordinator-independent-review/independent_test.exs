defmodule MixerHosted.BuildCoordinatorReview.Adapter do
  @moduledoc false
  use Agent
  alias MixerHosted.Builds.Dispatch

  def start_link(_),
    do: Agent.start_link(fn -> %{ops: %{}, calls: [], modes: %{}} end, name: __MODULE__)

  def reset, do: Agent.update(__MODULE__, fn _ -> %{ops: %{}, calls: [], modes: %{}} end)
  def mode(callback, value), do: Agent.update(__MODULE__, &put_in(&1, [:modes, callback], value))
  def snapshot, do: Agent.get(__MODULE__, & &1)
  def query(request), do: call(:query, request)
  def ensure_started(request), do: call(:ensure_started, request)
  def stop(request), do: call(:stop, request)

  def complete(operation_id, result) do
    Agent.update(__MODULE__, fn state ->
      update_in(state, [:ops, operation_id], &Map.put(&1, :status, {:completed, result}))
    end)
  end

  defp call(callback, request) do
    # This separate callback process must see the committed start and its job.
    visible =
      MixerHosted.Builds.Storage.read(
        Map.take(request.spec, [
          :organization_id,
          :project_id,
          :application_id,
          :build_id,
          :platform
        ])
      )

    %{rows: [[visible_jobs]]} =
      MixerHosted.Repo.query!(
        "SELECT count(*) FROM oban_jobs WHERE args->>'build_record_id' = $1 AND (args->>'revision')::integer = $2 AND worker = $3",
        [
          request.guard.record_id,
          request.guard.revision,
          Oban.Worker.to_string(MixerHosted.Builds.Coordinator)
        ]
      )

    mode =
      Agent.get_and_update(__MODULE__, fn state ->
        recorded = %{
          callback: callback,
          request: request,
          visible: visible,
          in_transaction: MixerHosted.Repo.in_transaction?(),
          visible_jobs: visible_jobs,
          callback_pid: self()
        }

        {Map.get(state.modes, callback),
         %{state | calls: state.calls ++ [recorded], modes: Map.delete(state.modes, callback)}}
      end)

    case mode do
      {:block, parent} ->
        send(parent, {:review_adapter_blocked, callback, self(), request})

        receive do
          :review_continue -> :ok
        after
          5_000 -> raise "independent adapter hold timed out"
        end

      _ ->
        :ok
    end

    result = Agent.get_and_update(__MODULE__, fn state -> effect(state, callback, request) end)

    case mode do
      :crash_after_effect -> raise "independent simulated crash after external effect"
      {:reply, reply} -> reply
      _ -> result
    end
  end

  defp effect(state, callback, request) do
    old = Map.get(state.ops, request.operation_id)
    guard = {request.guard.epoch, request.guard.revision}
    binding = {request.ref, request.spec, request.deadline_ms}

    cond do
      DateTime.compare(DateTime.utc_now(), request.guard.expires_at) != :lt ->
        {{:error, :stale}, state}

      old != nil and old.binding != binding ->
        {{:error, :uncertain}, state}

      old != nil and guard < old.guard ->
        {{:error, :stale}, state}

      true ->
        operation = old || %{binding: binding, guard: guard, status: :absent, creations: 0}
        operation = %{operation | guard: guard}

        operation =
          case {callback, operation.status} do
            {:ensure_started, :absent} ->
              %{operation | status: :running, creations: operation.creations + 1}

            {:stop, status} when status in [:absent, :running] ->
              %{operation | status: {:stopped, String.duplicate("d", 64)}}

            _ ->
              operation
          end

        observation =
          struct!(Dispatch.Observation,
            operation_id: request.operation_id,
            ref: request.ref,
            status: operation.status
          )

        {{:ok, observation}, put_in(state, [:ops, request.operation_id], operation)}
    end
  end
end

defmodule MixerHosted.BuildCoordinatorReview.Test do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.Repo
  alias MixerHosted.Builds.{Admission, Coordinator, Dispatch, Storage}
  alias MixerHosted.Builds.Admission.Reservation
  alias MixerHosted.BuildCoordinatorReview.Adapter
  @moduletag :database

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_coordinator_review_test",
       username: "mixer_fixture",
       pool_size: 10,
       ssl: false}
    )

    Ecto.Migrator.run(Repo, Application.app_dir(:mixer_hosted, "priv/repo/migrations"), :up,
      all: true
    )

    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    start_supervised!(Adapter)
    :ok
  end

  setup do
    previous = Application.fetch_env(:mixer_hosted, :build_dispatch)

    Application.put_env(:mixer_hosted, :build_dispatch,
      adapter: Adapter,
      lease_ttl_ms: 30_000,
      call_timeout_ms: 4_000,
      poll_ms: 10
    )

    on_exit(fn ->
      for call <- Adapter.snapshot().calls,
          call.callback_pid != self(),
          Process.alive?(call.callback_pid),
          do: Process.exit(call.callback_pid, :kill)

      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, :build_dispatch, value)
        :error -> Application.delete_env(:mixer_hosted, :build_dispatch)
      end
    end)

    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_builds, mixer_build_capacities, oban_jobs"
    )

    Adapter.reset()
    :ok
  end

  defp spec do
    %{
      organization_id: "review-org",
      project_id: "review-project",
      application_id: "review-app",
      build_id: "review-build",
      platform: :android,
      source: %{
        kind: :upload,
        sha256: String.duplicate("a", 64),
        reference: "immutable-review-upload"
      },
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }
  end

  defp scope,
    do: Map.take(spec(), [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp policy, do: %{max_attempts: 3, timeout_ms: 60_000, retry_backoff_ms: 0}

  defp configure do
    Admission.configure_multi(
      Multi.new(),
      :capacity,
      Map.take(scope(), [:organization_id, :platform]),
      :new,
      1
    )
    |> Repo.transaction()
  end

  defp create(p \\ policy()) do
    assert {:ok, _} = configure()

    assert {:ok, %{{:created, :job} => job}} =
             Storage.create_multi(
               Multi.new(),
               :created,
               spec(),
               p,
               "review-request",
               1,
               &Coordinator.new/1
             )
             |> Repo.transaction()

    job
  end

  defp latest_job, do: Repo.one!(from(j in Oban.Job, order_by: [desc: j.id], limit: 1))

  defp current do
    assert {:ok, current} = Storage.read(scope())
    current
  end

  defp jobs, do: Repo.aggregate(Oban.Job, :count)
  defp held, do: Repo.aggregate(from(r in Reservation, where: r.held), :count)

  defp expire_lease do
    Repo.query!(
      "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) - interval '1 second'"
    )
  end

  defp cancel do
    row = current()

    assert {:ok, %{{:cancelled, :job} => job}} =
             Storage.cancel_multi(
               Multi.new(),
               :cancelled,
               scope(),
               row.record.revision,
               "review-cancel",
               "independent cancellation",
               row.build.observed_at + 1,
               &Coordinator.new/1
             )
             |> Repo.transaction()

    job
  end

  defp start(p \\ policy()) do
    creation = create(p)
    Coordinator.perform(creation)
    assert current().build.state == :running
    {creation, latest_job()}
  end

  defp dispatch(p \\ policy()) do
    {creation, started} = start(p)
    Coordinator.perform(started)
    assert map_size(Adapter.snapshot().ops) == 1
    {creation, started, Adapter.snapshot().calls |> List.last() |> Map.fetch!(:request)}
  end

  defp failure(class \\ :infrastructure) do
    %{
      outcome: :failed,
      class: class,
      code: if(class == :compiler, do: :compiler_error, else: :worker_lost),
      diagnostic_sha256: String.duplicate("e", 64)
    }
  end

  test "current intent binds closed kind scope record attempt fence and revision before any effect" do
    job = create()

    bad = [
      Map.put(job.args, "kind", "start"),
      Map.put(job.args, "organization_id", "other-org"),
      Map.put(job.args, "build_record_id", Ecto.UUID.generate()),
      Map.put(job.args, "attempt", 2),
      Map.put(job.args, "fence", 2),
      Map.put(job.args, "revision", 1),
      Map.put(job.args, "adapter", "Elixir.MixerHosted.BuildCoordinatorReview.Adapter")
    ]

    for args <- bad, do: Coordinator.perform(%{job | args: args})
    assert current().record.revision == 0
    assert held() == 0 and jobs() == 1
    assert Adapter.snapshot().calls == []
  end

  test "start intent is committed before callbacks and historical creation cannot dispatch" do
    {creation, started} = start()
    assert Adapter.snapshot().calls == []
    job_count = jobs()
    Coordinator.perform(creation)
    assert jobs() == job_count and Adapter.snapshot().calls == []
    Coordinator.perform(started)
    assert Enum.map(Adapter.snapshot().calls, & &1.callback) == [:query, :ensure_started]

    for call <- Adapter.snapshot().calls do
      assert call.in_transaction == false
      assert call.visible_jobs > 0
      assert {:ok, %{build: %{state: :running}, record: %{revision: 1}}} = call.visible
      assert call.request.guard.revision == 1
      assert call.request.ref == current().build.active_ref
    end

    assert jobs() == 2 and held() == 1
  end

  test "crash after external ensure redelivery queries the same operation after lease takeover" do
    {_creation, started} = start()
    Adapter.mode(:ensure_started, :crash_after_effect)
    Coordinator.perform(started)
    [operation] = Map.values(Adapter.snapshot().ops)
    assert operation.creations == 1 and operation.status == :running
    first = Adapter.snapshot().calls |> List.last() |> Map.fetch!(:request)
    assert current().build.state == :running and held() == 1
    expire_lease()
    Coordinator.perform(started)
    [operation] = Map.values(Adapter.snapshot().ops)
    assert operation.creations == 1
    assert Enum.count(Adapter.snapshot().calls, &(&1.callback == :query)) >= 2
    last = Adapter.snapshot().calls |> List.last() |> Map.fetch!(:request)
    assert last.operation_id == first.operation_id and last.ref == first.ref
    assert last.guard.epoch > first.guard.epoch
  end

  test "stale ensure after cancellation cannot restart an absent-operation stop tombstone" do
    {_creation, started} = start()
    Adapter.mode(:ensure_started, {:block, self()})
    old = Task.async(fn -> Coordinator.perform(started) end)
    assert_receive {:review_adapter_blocked, :ensure_started, callback, old_request}, 2_000
    expire_lease()
    cancellation = cancel()
    Coordinator.perform(cancellation)
    assert current().build.state == :cancelled
    assert held() == 0
    [operation] = Map.values(Adapter.snapshot().ops)
    assert match?({:stopped, _}, operation.status) and operation.creations == 0
    send(callback, :review_continue)
    Task.await(old, 5_000)
    [operation] = Map.values(Adapter.snapshot().ops)
    assert match?({:stopped, _}, operation.status) and operation.creations == 0
    assert operation.guard > {old_request.guard.epoch, old_request.guard.revision}
    assert current().build.state == :cancelled and held() == 0
  end

  test "lease loss during terminal query cannot reconcile or release through an old token" do
    {_creation, started, request} = dispatch()
    Adapter.complete(request.operation_id, failure(:compiler))
    expire_lease()
    Adapter.mode(:query, {:block, self()})
    old = Task.async(fn -> Coordinator.perform(started) end)
    assert_receive {:review_adapter_blocked, :query, callback, _}, 2_000
    expire_lease()

    assert {:ok, _} =
             Admission.claim_multi(Multi.new(), :claim, scope(), "independent-new-owner", 30_000)
             |> Repo.transaction()

    send(callback, :review_continue)
    Task.await(old, 5_000)
    assert current().build.state == :running and held() == 1
    expire_lease()
    Coordinator.perform(started)
    assert current().build.state == :failed and held() == 0
    assert current().build.attempt == 1
  end

  test "wrong operation or worker observation and unknown statuses retain uncertainty" do
    {_creation, started} = start()

    fake = fn status ->
      struct!(Dispatch.Observation,
        operation_id: "wrong-operation",
        ref: current().build.active_ref,
        status: status
      )
    end

    Adapter.mode(:query, {:reply, {:ok, fake.(:running)}})
    Coordinator.perform(started)
    assert current().build.state == :running and held() == 1
    assert Enum.all?(Adapter.snapshot().calls, &(&1.callback == :query))
    expire_lease()
    request = Adapter.snapshot().calls |> List.last() |> Map.fetch!(:request)
    wrong_ref = %{request.ref | organization_id: "wrong-org"}

    Adapter.mode(
      :query,
      {:reply,
       {:ok,
        struct!(Dispatch.Observation,
          operation_id: request.operation_id,
          ref: wrong_ref,
          status: {:completed, failure(:compiler)}
        )}}
    )

    Coordinator.perform(started)
    assert current().build.state == :running and held() == 1
    expire_lease()

    Adapter.mode(
      :query,
      {:reply,
       {:ok,
        struct!(Dispatch.Observation,
          operation_id: request.operation_id,
          ref: request.ref,
          status: :unknown
        )}}
    )

    Coordinator.perform(started)
    assert current().build.state == :running and held() == 1
  end

  test "cancellation with uncertain stop retains capacity and never ensures again" do
    {_creation, _started, _request} = dispatch()
    expire_lease()
    cancellation = cancel()
    Adapter.mode(:stop, {:reply, {:error, :uncertain}})
    Coordinator.perform(cancellation)
    assert current().build.state == :cancelling and held() == 1
    ensures = Enum.count(Adapter.snapshot().calls, &(&1.callback == :ensure_started))
    expire_lease()
    Coordinator.perform(cancellation)
    assert current().build.state == :cancelled and held() == 0
    assert Enum.count(Adapter.snapshot().calls, &(&1.callback == :ensure_started)) == ensures
  end

  test "timeout persists reconciliation before stop and uncertain absent work remains occupied" do
    {_creation, started} = start(%{policy() | timeout_ms: 10, max_attempts: 1})

    receive do
    after
      20 -> :ok
    end

    Coordinator.perform(started)
    assert current().build.state == :reconciling and held() == 1
    assert Adapter.snapshot().calls == []
    expired = latest_job()
    Adapter.mode(:stop, {:reply, {:error, :uncertain}})
    Coordinator.perform(expired)
    assert current().build.state == :reconciling and held() == 1
    assert Enum.map(Adapter.snapshot().calls, & &1.callback) == [:query, :stop]

    assert Enum.all?(Adapter.snapshot().calls, fn call ->
             match?({:ok, %{build: %{state: :reconciling}}}, call.visible)
           end)

    Coordinator.perform(expired)
    assert current().build.state == :timed_out and held() == 0
    assert current().build.attempt == 1
    assert Enum.all?(Adapter.snapshot().calls, &(&1.callback != :ensure_started))
  end

  test "infrastructure retry changes attempt only after matching terminal evidence releases occupancy" do
    {creation, started, request} = dispatch()
    Adapter.complete(request.operation_id, failure())
    expire_lease()
    Coordinator.perform(started)
    # Retry may be the same reconciliation transaction or the current terminal intent.
    if current().build.attempt == 1, do: Coordinator.perform(latest_job())
    assert current().build.attempt == 2 and current().build.state == :queued
    assert held() == 0
    calls = Adapter.snapshot().calls
    count = jobs()
    Coordinator.perform(creation)
    Coordinator.perform(started)
    assert current().build.attempt == 2 and current().build.state == :queued
    assert held() == 0 and jobs() == count and Adapter.snapshot().calls == calls
    Coordinator.perform(latest_job())
    assert current().build.state == :running and current().build.attempt == 2
    assert held() == 1
    assert map_size(Adapter.snapshot().ops) == 1
  end

  test "compiler failures release the exact reservation without an automatic retry" do
    {creation, started, request} = dispatch()
    Adapter.complete(request.operation_id, failure(:compiler))
    expire_lease()
    Coordinator.perform(started)
    assert current().build.state == :failed and current().build.attempt == 1 and held() == 0
    count = jobs()
    calls = Adapter.snapshot().calls
    Coordinator.perform(latest_job())
    Coordinator.perform(creation)
    Coordinator.perform(started)
    assert current().build.state == :failed and current().build.attempt == 1
    assert jobs() == count and held() == 0 and Adapter.snapshot().calls == calls
  end

  test "guarded retry observes backoff and serializes competing terminal consumers" do
    {_creation, started, request} = dispatch(%{policy() | retry_backoff_ms: 1_000})
    Adapter.complete(request.operation_id, failure())
    expire_lease()
    Coordinator.perform(started)
    row = current()
    assert row.build.state == :failed and row.build.attempt == 1 and held() == 0

    attempt = fn id ->
      Admission.retry_multi(
        Multi.new(),
        :retry,
        scope(),
        row.record.revision,
        id,
        &Coordinator.new/1
      )
      |> Repo.transaction()
    end

    assert {:error, :retry, :backoff_not_reached, _} = attempt.("review-early-retry")
    assert current().record.revision == row.record.revision
    count = jobs()
    parent = self()

    tasks =
      for n <- 1..2 do
        Task.async(fn ->
          send(parent, {:review_retry_ready, self()})

          receive do
            :review_retry_go -> attempt.("review-racing-retry-#{n}")
          end
        end)
      end

    for _ <- tasks, do: assert_receive({:review_retry_ready, _}, 1_000)

    receive do
    after
      1_100 -> :ok
    end

    for task <- tasks, do: send(task.pid, :review_retry_go)
    results = Enum.map(tasks, &Task.await(&1, 5_000))
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1

    assert Enum.count(results, &match?({:error, _, :released_current_attempt_required, _}, &1)) ==
             1

    assert current().build.state == :queued and current().build.attempt == 2
    assert held() == 0 and jobs() == count + 1
  end

  test "coordinator process death leaves its lease live until takeover and cannot duplicate an in-flight ensure" do
    {_creation, started} = start()
    Adapter.mode(:ensure_started, {:block, self()})
    {runner, monitor} = spawn_monitor(fn -> Coordinator.perform(started) end)
    assert_receive {:review_adapter_blocked, :ensure_started, callback, old_request}, 2_000
    callback_monitor = Process.monitor(callback)
    Process.exit(runner, :kill)
    assert_receive {:DOWN, ^monitor, :process, ^runner, :killed}, 2_000
    assert_receive {:DOWN, ^callback_monitor, :process, ^callback, :killed}, 2_000

    assert %{rows: [[true]]} =
             Repo.query!(
               "SELECT owner_id IS NOT NULL AND expires_at > timezone('UTC', clock_timestamp()) FROM mixer_build_coordinator_leases"
             )

    calls = Adapter.snapshot().calls
    Coordinator.perform(started)
    assert Adapter.snapshot().calls == calls and held() == 1
    expire_lease()
    Coordinator.perform(started)
    # Local transport retirement is not an external worker-stop observation.
    [operation] = Map.values(Adapter.snapshot().ops)
    assert operation.creations == 1 and operation.status == :running
    assert operation.guard > {old_request.guard.epoch, old_request.guard.revision}
    assert current().build.state == :running and held() == 1
  end

  test "yield rollback retains ownership and a stale yield cannot expire a replacement owner" do
    create()

    assert {:ok, %{claim: old}} =
             Admission.claim_multi(Multi.new(), :claim, scope(), "review-old-owner", 30_000)
             |> Repo.transaction()

    abort =
      Admission.yield_multi(Multi.new(), :yield, old.token)
      |> Multi.run(:abort, fn _, _ -> {:error, :review_abort} end)

    assert {:error, :abort, :review_abort, _} = Repo.transaction(abort)

    assert {:ok, _} =
             Admission.renew_multi(Multi.new(), :renew, old.token, 30_000) |> Repo.transaction()

    expire_lease()

    assert {:ok, %{claim: replacement}} =
             Admission.claim_multi(Multi.new(), :claim, scope(), "review-new-owner", 30_000)
             |> Repo.transaction()

    assert {:error, :yield, :stale_lease, _} =
             Admission.yield_multi(Multi.new(), :yield, old.token) |> Repo.transaction()

    assert {:ok, %{renew: live}} =
             Admission.renew_multi(Multi.new(), :renew, replacement.token, 30_000)
             |> Repo.transaction()

    assert live.token.epoch > old.token.epoch and held() == 1

    assert {:ok, %{yield: yielded}} =
             Admission.yield_multi(Multi.new(), :yield, live.token) |> Repo.transaction()

    assert yielded.token == nil and held() == 1

    assert {:ok, %{claim: next}} =
             Admission.claim_multi(Multi.new(), :claim, scope(), "review-after-yield", 30_000)
             |> Repo.transaction()

    assert next.token.epoch == live.token.epoch + 1
  end

  test "a missing deployment adapter has no external execution capability" do
    job = create()
    Application.delete_env(:mixer_hosted, :build_dispatch)
    Coordinator.perform(job)
    assert Adapter.snapshot().calls == [] and map_size(Adapter.snapshot().ops) == 0
    assert current().build.attempt == 1
  end
end
