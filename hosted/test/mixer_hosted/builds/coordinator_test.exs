defmodule MixerHosted.Builds.CoordinatorTest do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.Repo
  alias MixerHosted.Builds.{Admission, Coordinator, Dispatch, Storage}
  alias MixerHosted.Test.BuildDispatchFixture, as: Fixture
  alias Admission.{Lease, Reservation}
  @moduletag :database

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_coordinator_test",
       username: "mixer_fixture",
       pool_size: 8,
       ssl: false}
    )

    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")
    assert length(Ecto.Migrator.run(Repo, path, :up, all: true)) == 3
    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    start_supervised!(Fixture)
    :ok
  end

  setup do
    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_build_capacities, mixer_builds, oban_jobs"
    )

    Fixture.reset()
    previous = Application.get_env(:mixer_hosted, :build_dispatch)

    Application.put_env(:mixer_hosted, :build_dispatch,
      adapter: Fixture,
      lease_ttl_ms: 3_000,
      call_timeout_ms: 100,
      poll_ms: 1
    )

    on_exit(fn ->
      if previous == nil,
        do: Application.delete_env(:mixer_hosted, :build_dispatch),
        else: Application.put_env(:mixer_hosted, :build_dispatch, previous)
    end)

    :ok
  end

  defp spec,
    do: %{
      organization_id: "org-c",
      project_id: "project-c",
      application_id: "app-c",
      build_id: "build-c",
      platform: :android,
      source: %{kind: :revision, sha256: String.duplicate("a", 64), reference: "repo@immutable"},
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }

  defp scope,
    do: Map.take(spec(), [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp create(policy \\ %{max_attempts: 2, timeout_ms: 100_000, retry_backoff_ms: 0}) do
    assert {:ok, _} =
             Admission.configure_multi(
               Multi.new(),
               :capacity,
               Map.take(scope(), [:organization_id, :platform]),
               :new,
               1
             )
             |> Repo.transaction()

    assert {:ok, changes} =
             Storage.create_multi(
               Multi.new(),
               :create,
               spec(),
               policy,
               "coordinator-request",
               1,
               &Coordinator.new/1
             )
             |> Repo.transaction()

    changes[{:create, :job}]
  end

  defp latest_job, do: Repo.one!(from(j in Oban.Job, order_by: [desc: j.id], limit: 1))

  defp current do
    {:ok, current} = Storage.read(scope())
    current
  end

  defp expire_lease,
    do:
      Repo.query!(
        "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) - interval '1 second'"
      )

  defp running do
    created = create()
    assert :ok = Coordinator.perform(created)
    started = latest_job()
    assert started.args["kind"] == "start"
    expire_lease()
    {created, started}
  end

  defp cancel do
    c = current()

    assert {:ok, _} =
             Storage.cancel_multi(
               Multi.new(),
               :cancel,
               scope(),
               c.record.revision,
               "cancel-request",
               "operator requested",
               now_ms(),
               &Coordinator.new/1
             )
             |> Repo.transaction()

    latest_job()
  end

  defp now_ms do
    %{rows: [[now]]} =
      Repo.query!("SELECT floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint")

    now
  end

  defp failure(class \\ :infrastructure),
    do: %{
      outcome: :failed,
      class: class,
      code: if(class == :infrastructure, do: :worker_lost, else: :compiler_error),
      diagnostic_sha256: String.duplicate("f", 64)
    }

  defp held?, do: Repo.one!(Reservation).held
  defp operation, do: Fixture.snapshot().operations |> Map.keys() |> hd()

  test "strict closed arguments and unavailable default cannot reserve or dispatch" do
    created = create()

    for args <- [
          Map.put(created.args, "extra", true),
          Map.put(created.args, "revision", "0"),
          Map.put(created.args, "platform", "other"),
          Map.put(created.args, "kind", "shell")
        ] do
      assert {:cancel, :invalid_build_intent} = Coordinator.perform(%{created | args: args})
    end

    Application.delete_env(:mixer_hosted, :build_dispatch)
    assert {:error, :dispatch_unavailable} = Coordinator.perform(created)
    assert Repo.aggregate(Reservation, :count) == 0
    assert Fixture.snapshot().calls == []
  end

  test "exact job kind is bound to latest journal event and forged old scope cannot act" do
    created = create()

    for args <- [
          Map.put(created.args, "kind", "start"),
          Map.put(created.args, "build_record_id", Ecto.UUID.generate())
        ] do
      assert :ok = Coordinator.perform(%{created | args: args})
    end

    assert {:cancel, :build_not_found} =
             Coordinator.perform(%{
               created
               | args: Map.put(created.args, "project_id", "foreign")
             })

    assert Repo.aggregate(Reservation, :count) == 0
  end

  test "queued intent commits start and actual coordinator intent before external effects" do
    created = create()
    assert :ok = Coordinator.perform(created)
    assert current().build.state == :running
    assert latest_job().worker == "MixerHosted.Builds.Coordinator"
    assert Fixture.snapshot().calls == []
    assert held?()
    assert :ok = Coordinator.perform(created)
    assert Fixture.snapshot().calls == []
    assert {:snooze, 1} = Coordinator.perform(latest_job())
    assert Fixture.snapshot().creations == 1

    for call <- Fixture.snapshot().calls do
      assert call.visibility == %{state: :running, revision: 1, transaction?: false}
    end
  end

  test "yield expires coordination only, preserves capacity, fences old owner and rolls back atomically" do
    create()

    assert {:ok, %{claim: claimed}} =
             Admission.claim_multi(Multi.new(), :claim, scope(), "first", 30_000)
             |> Repo.transaction()

    before = Repo.one!(Lease)

    assert {:error, :later, :rollback, _} =
             Admission.yield_multi(Multi.new(), :yield, claimed.token)
             |> Multi.run(:later, fn _, _ -> {:error, :rollback} end)
             |> Repo.transaction()

    assert Repo.one!(Lease) == before and held?()

    assert {:ok, %{yield: yielded}} =
             Admission.yield_multi(Multi.new(), :yield, claimed.token) |> Repo.transaction()

    assert yielded.token == nil and yielded.reservation.held
    assert yielded.lease.owner_id == before.owner_id and yielded.lease.epoch == before.epoch
    assert DateTime.to_unix(yielded.lease.expires_at, :millisecond) == yielded.now_ms

    assert {:error, :yield, :stale_lease, _} =
             Admission.yield_multi(Multi.new(), :yield, claimed.token) |> Repo.transaction()

    assert {:ok, %{claim: taken}} =
             Admission.claim_multi(Multi.new(), :claim, scope(), "next", 30_000)
             |> Repo.transaction()

    assert taken.token.epoch == claimed.token.epoch + 1 and held?()

    assert {:error, :yield, :stale_lease, _} =
             Admission.yield_multi(Multi.new(), :yield, claimed.token) |> Repo.transaction()
  end

  test "crash after ensure and coordinator transfer query same operation without second execution" do
    {created, started} = running()
    Fixture.mode(:ensure_started, :raise_after)
    assert {:snooze, 1} = Coordinator.perform(started)
    first = Fixture.snapshot()
    request = List.last(first.calls).request
    lease = Repo.one!(Lease)
    assert first.creations == 1 and held?()
    assert :ok = Coordinator.perform(created)
    assert Fixture.snapshot().creations == 1
    expire_lease()
    assert {:snooze, 1} = Coordinator.perform(started)
    next = Fixture.snapshot()
    assert next.creations == 1 and map_size(next.operations) == 1
    assert Repo.one!(Lease).epoch == lease.epoch + 1
    assert List.last(next.calls).request.operation_id == request.operation_id
    assert List.last(next.calls).request.ref == request.ref
    assert {:error, :stale} = Fixture.ensure_started(request)
    assert held?()
  end

  test "callback timeout after external effect kills transport process and retains reservation" do
    {_, started} = running()
    Fixture.mode(:ensure_started, :timeout_after)
    before = System.monotonic_time(:millisecond)
    assert {:snooze, 1} = Coordinator.perform(started)
    assert System.monotonic_time(:millisecond) - before < 2_000
    assert held?() and Fixture.snapshot().creations == 1
    expire_lease()
    assert {:snooze, 1} = Coordinator.perform(started)
    assert Fixture.snapshot().creations == 1
  end

  test "abrupt coordinator death after modeled effect retains lease and redelivery cannot execute twice" do
    {_, started} = running()

    Application.put_env(:mixer_hosted, :build_dispatch,
      adapter: Fixture,
      lease_ttl_ms: 3_000,
      call_timeout_ms: 1_000,
      poll_ms: 1
    )

    Fixture.mode(:ensure_started, {:block_after, self()})
    {pid, monitor} = spawn_monitor(fn -> Coordinator.perform(started) end)
    assert_receive {:dispatch_blocked, transport}, 1_000
    transport_monitor = Process.monitor(transport)
    assert Fixture.snapshot().creations == 1 and held?()
    lease = Repo.one!(Lease)
    Process.exit(pid, :kill)
    assert_receive {:DOWN, ^monitor, :process, ^pid, :killed}, 1_000
    assert_receive {:DOWN, ^transport_monitor, :process, ^transport, :killed}, 1_000
    assert Repo.one!(Lease) == lease and held?()
    assert {:snooze, 1} = Coordinator.perform(started)
    assert Fixture.snapshot().creations == 1
    expire_lease()
    assert {:snooze, 1} = Coordinator.perform(started)
    assert Repo.one!(Lease).epoch == lease.epoch + 1
    assert Fixture.snapshot().creations == 1 and map_size(Fixture.snapshot().operations) == 1
  end

  test "unavailable and mismatched observations never release capacity" do
    {_, started} = running()

    for mode <- [:unavailable, :wrong_operation, :wrong_ref, :invalid_result] do
      Fixture.mode(:query, mode)
      assert {:snooze, 1} = Coordinator.perform(started)
      assert held?() and current().build.state == :running
      expire_lease()
    end

    assert Fixture.snapshot().creations == 0
  end

  test "cancellation stops absent operation with a durable tombstone and delayed ensure cannot reopen" do
    {_, started} = running()
    # Capture an earlier valid request before cancellation without starting work.
    Fixture.mode(:ensure_started, :unavailable)
    assert {:snooze, 1} = Coordinator.perform(started)
    old = List.last(Fixture.snapshot().calls).request
    cancelled = cancel()
    assert current().build.state == :cancelling and held?()
    assert :ok = Coordinator.perform(started)
    expire_lease()
    assert :ok = Coordinator.perform(cancelled)
    assert current().build.state == :cancelled and not held?()
    assert Fixture.snapshot().creations == 0
    assert {:error, :stale} = Fixture.ensure_started(old)
    newer = Enum.find(Fixture.snapshot().calls, &(&1.callback == :stop)).request

    newer = %{
      newer
      | guard: %{
          newer.guard
          | epoch: newer.guard.epoch + 1,
            expires_at: DateTime.add(DateTime.utc_now(), 3_000, :millisecond)
        }
    }

    assert {:ok, %Dispatch.Observation{status: {:stopped, _}}} = Fixture.ensure_started(newer)
    assert Fixture.snapshot().creations == 0
  end

  test "stop errors and lease expiry are uncertainty, not terminal evidence" do
    {_, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)
    cancelled = cancel()
    expire_lease()
    Fixture.mode(:stop, :unavailable)
    assert {:snooze, 1} = Coordinator.perform(cancelled)
    assert held?() and current().build.state == :cancelling
    expire_lease()
    assert held?()
    assert :ok = Coordinator.perform(cancelled)
    assert current().build.state == :cancelled and not held?()
    assert Fixture.snapshot().creations == 1
  end

  test "deadline is persisted as expiry before stop, while original worker fence is preserved" do
    created = create(%{max_attempts: 1, timeout_ms: 1, retry_backoff_ms: 0})
    assert :ok = Coordinator.perform(created)
    started = latest_job()
    ref = current().build.active_ref
    expire_lease()
    assert :ok = Coordinator.perform(started)
    assert current().build.state == :reconciling and held?()
    assert Fixture.snapshot().calls == []
    expired = latest_job()
    expire_lease()
    assert :ok = Coordinator.perform(expired)
    assert current().build.state == :timed_out and not held?()
    assert List.last(Fixture.snapshot().calls).request.ref == ref
    assert Fixture.snapshot().creations == 0
  end

  test "compiler failure releases definitively but cannot trigger automatic retry" do
    {_, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)
    Fixture.complete(operation(), failure(:compiler))
    expire_lease()
    assert :ok = Coordinator.perform(started)
    terminal = latest_job()
    assert current().build.state == :failed and not held?()
    assert :ok = Coordinator.perform(terminal)
    assert current().build.attempt == 1
    assert Fixture.snapshot().creations == 1
  end

  test "successful completion preserves complete artifact references and releases exactly once" do
    {_, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)

    artifacts =
      for kind <- [
            :unsigned_native_binary,
            :guest_artifact,
            :resource_inventory,
            :debug_symbols,
            :compatibility_report,
            :sbom,
            :provenance
          ] do
        %MixerHosted.Builds.Lifecycle.ArtifactRef{
          kind: kind,
          sha256: String.duplicate("e", 64),
          size_bytes: 128
        }
      end

    Fixture.complete(operation(), %{outcome: :succeeded, artifacts: artifacts})
    expire_lease()
    assert :ok = Coordinator.perform(started)
    assert current().build.state == :succeeded and not held?()
    assert current().build.artifacts == artifacts
    released = Repo.one!(Reservation)
    assert :ok = Coordinator.perform(started)
    assert :ok = Coordinator.perform(latest_job())
    assert Repo.one!(Reservation) == released
    assert current().build.attempt == 1 and Fixture.snapshot().creations == 1
  end

  test "bounded infrastructure retry follows release, rejects stale jobs and uses a new operation" do
    {created, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)
    Fixture.complete(operation(), failure())
    expire_lease()
    assert :ok = Coordinator.perform(started)
    assert not held?()
    assert :ok = Coordinator.perform(latest_job())
    assert current().build.state == :queued and current().build.attempt == 2
    assert :ok = Coordinator.perform(created)
    assert :ok = Coordinator.perform(started)
    assert Fixture.snapshot().creations == 1
    assert :ok = Coordinator.perform(latest_job())
    expire_lease()
    assert {:snooze, 1} = Coordinator.perform(latest_job())
    assert Fixture.snapshot().creations == 2
    Fixture.complete(operation_for_attempt(2), failure())
    expire_lease()
    assert :ok = Coordinator.perform(latest_job())
    assert :ok = Coordinator.perform(latest_job())
    assert current().build.attempt == 2 and current().build.state == :failed
  end

  defp operation_for_attempt(attempt) do
    {id, _} =
      Enum.find(Fixture.snapshot().operations, fn {_, op} -> op.ref.attempt == attempt end)

    id
  end

  test "released-attempt retry respects database backoff" do
    created = create(%{max_attempts: 2, timeout_ms: 100_000, retry_backoff_ms: 60_000})
    assert :ok = Coordinator.perform(created)
    expire_lease()
    started = latest_job()
    assert {:snooze, 1} = Coordinator.perform(started)
    Fixture.complete(operation(), failure())
    expire_lease()
    assert :ok = Coordinator.perform(started)
    c = current()
    assert not held?()
    assert {:snooze, 1} = Coordinator.perform(latest_job())

    assert {:error, :retry, :backoff_not_reached, _} =
             Admission.retry_multi(
               Multi.new(),
               :retry,
               scope(),
               c.record.revision,
               "retry-too-early",
               &Coordinator.new/1
             )
             |> Repo.transaction()

    assert current().record.revision == c.record.revision
    assert current().build.attempt == 1
  end

  test "released retry job insertion failure rolls back retry state and preserves release evidence" do
    {_, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)
    Fixture.complete(operation(), failure())
    expire_lease()
    assert :ok = Coordinator.perform(started)
    c = current()
    released = Repo.one!(Reservation)
    jobs = Repo.aggregate(Oban.Job, :count)

    Repo.query!(
      "ALTER TABLE oban_jobs ADD CONSTRAINT coordinator_reject_retry CHECK ((args->>'kind') <> 'retry')"
    )

    try do
      assert_raise Ecto.ConstraintError, fn -> Coordinator.perform(latest_job()) end
      assert current().record.revision == c.record.revision
      assert current().build.attempt == 1 and current().build.state == :failed
      assert Repo.one!(Reservation) == released and not held?()
      assert Repo.aggregate(Oban.Job, :count) == jobs
    after
      Repo.query!("ALTER TABLE oban_jobs DROP CONSTRAINT coordinator_reject_retry")
    end
  end

  test "later Multi failure rolls retry domain and job back together" do
    {_, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)
    Fixture.complete(operation(), failure())
    expire_lease()
    assert :ok = Coordinator.perform(started)
    c = current()
    jobs = Repo.aggregate(Oban.Job, :count)

    assert {:error, :later, :synthetic_failure, _} =
             Admission.retry_multi(
               Multi.new(),
               :retry,
               scope(),
               c.record.revision,
               "retry-then-rollback",
               &Coordinator.new/1
             )
             |> Multi.run(:later, fn _, _ -> {:error, :synthetic_failure} end)
             |> Repo.transaction()

    assert current().record.revision == c.record.revision
    assert current().build.attempt == 1 and not held?()
    assert Repo.aggregate(Oban.Job, :count) == jobs
  end

  test "guarded start and reservation roll back when atomic coordinator intent insertion fails" do
    created = create()

    Repo.query!(
      "ALTER TABLE oban_jobs ADD CONSTRAINT coordinator_reject_start CHECK ((args->>'kind') <> 'start')"
    )

    try do
      assert_raise Ecto.ConstraintError, fn -> Coordinator.perform(created) end
      assert current().record.revision == 0 and current().build.state == :queued
      assert Repo.aggregate(Reservation, :count) == 0
      assert Repo.aggregate(Lease, :count) == 0
      assert Repo.aggregate(Oban.Job, :count) == 1
      assert Fixture.snapshot().calls == []
    after
      Repo.query!("ALTER TABLE oban_jobs DROP CONSTRAINT coordinator_reject_start")
    end
  end

  test "released retry requires current revision and exact retained terminal evidence" do
    {_, started} = running()
    assert {:snooze, 1} = Coordinator.perform(started)
    c = current()

    assert {:error, {:retry, :admission}, :released_current_attempt_required, _} =
             Admission.retry_multi(
               Multi.new(),
               :retry,
               scope(),
               c.record.revision,
               "held-retry",
               &Coordinator.new/1
             )
             |> Repo.transaction()

    Fixture.complete(operation(), failure())
    expire_lease()
    assert :ok = Coordinator.perform(started)
    c = current()

    assert {:error, {:retry, :admission}, :released_current_attempt_required, _} =
             Admission.retry_multi(
               Multi.new(),
               :retry,
               scope(),
               c.record.revision - 1,
               "stale-retry",
               &Coordinator.new/1
             )
             |> Repo.transaction()

    Repo.query!("UPDATE mixer_build_reservations SET terminal_event_id = 'unproven'")

    assert {:error, {:retry, :admission}, :invalid_admission, _} =
             Admission.retry_multi(
               Multi.new(),
               :retry,
               scope(),
               c.record.revision,
               "unproven-retry",
               &Coordinator.new/1
             )
             |> Repo.transaction()

    assert current().build.attempt == 1
  end
end
