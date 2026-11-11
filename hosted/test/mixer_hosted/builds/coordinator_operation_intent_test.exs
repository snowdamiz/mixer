defmodule MixerHosted.Test.CoordinatorIntentSQLForbidden do
  def query(_, _), do: raise("malformed WorkerRef reached SQL")
end

defmodule MixerHosted.Test.CoordinatorIntentUncertainAdapter do
  # Fixture transport does not model a worker or return worker observations.
  def query(_), do: {:error, :unavailable}
  def ensure_started(_), do: raise("fixture must not execute")
  def stop(_), do: raise("fixture must not terminate")
end

defmodule MixerHosted.Builds.CoordinatorOperationIntentTest do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.Repo

  alias MixerHosted.Builds.{
    Admission,
    Coordinator,
    Dispatch,
    OperationAdmission,
    OperationIntent,
    Storage
  }

  setup_all do
    config = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
      username: "mixer_fixture",
      database: "mixer_coordinator_intent_test",
      pool_size: 3,
      ssl: false,
      log: false
    ]

    previous_repo = Application.fetch_env(:mixer_hosted, Repo)
    previous_dispatch = Application.fetch_env(:mixer_hosted, :build_dispatch)
    previous_selection = Application.fetch_env(:mixer_hosted, :build_operation_intent)

    on_exit(fn ->
      for {key, previous} <- [
            {Repo, previous_repo},
            {:build_dispatch, previous_dispatch},
            {:build_operation_intent, previous_selection}
          ] do
        case previous do
          {:ok, value} -> Application.put_env(:mixer_hosted, key, value)
          :error -> Application.delete_env(:mixer_hosted, key)
        end
      end
    end)

    Application.put_env(:mixer_hosted, Repo, config)
    start_supervised!({Repo, config})

    MixerHosted.Test.Migrations.up!(
      Repo,
      Application.app_dir(:mixer_hosted, "priv/repo/migrations")
    )

    Application.put_env(:mixer_hosted, :build_operation_intent, :durable_intent_v1)

    path =
      Application.app_dir(
        :mixer_hosted,
        "priv/unselected_operation_admission/20261110000498_add_private_build_operation_admission.exs"
      )

    Code.require_file(path)
    mod = MixerHosted.Repo.Migrations.AddPrivateBuildOperationAdmission
    :ok = Ecto.Migrator.up(Repo, 20_261_110_000_498, mod, log: false)
    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})

    Application.put_env(:mixer_hosted, :build_dispatch,
      adapter: MixerHosted.Test.CoordinatorIntentUncertainAdapter,
      lease_ttl_ms: 3_000,
      call_timeout_ms: 100,
      poll_ms: 1
    )

    # The discriminator runs before any semantic test; no fake coordinator.
    job = running("provenance")
    owner = self()
    tracer = spawn(fn -> trace_loop(owner) end)
    Code.ensure_loaded!(MixerHosted.Builds.OperationIntent)
    1 = :erlang.trace_pattern({Coordinator, :refresh, 3}, true, [:local])
    1 = :erlang.trace_pattern({OperationIntent, :record_multi, 3}, true, [:local])
    1 = :erlang.trace(self(), true, [:call, {:tracer, tracer}])
    assert {:snooze, 1} = Coordinator.perform(job)
    :erlang.trace(self(), false, [:call])
    assert_receive {:trace, refresh_pid, :call, {Coordinator, :refresh, [_, _, _]}}, 2_000

    assert_receive {:trace, join_pid, :call,
                    {OperationIntent, :record_multi,
                     [_, :operation_intent, %{outcome: :renewed} = _traced_context]}},
                   2_000

    assert refresh_pid == self() and join_pid == self()
    :erlang.trace_pattern({Coordinator, :refresh, 3}, false, [:local])
    :erlang.trace_pattern({OperationIntent, :record_multi, 3}, false, [:local])
    send(tracer, :stop)
    assert row("provenance") == "admitted"
    :ok
  end

  defp trace_loop(owner) do
    receive do
      :stop ->
        :ok

      msg ->
        send(owner, msg)
        trace_loop(owner)
    end
  end

  defp spec(key),
    do: %{
      organization_id: "org-r704",
      project_id: "project-r704",
      application_id: "app-r704",
      build_id: key,
      platform: :android,
      source: %{kind: :revision, sha256: String.duplicate("a", 64), reference: "repo@immutable"},
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }

  defp scope(key),
    do:
      Map.take(spec(key), [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp current(key) do
    {:ok, c} = Storage.read(scope(key))
    c
  end

  defp latest(key),
    do:
      Repo.one!(
        from(j in Oban.Job,
          where: fragment("?->>'build_id'", j.args) == ^key,
          order_by: [desc: j.id],
          limit: 1
        )
      )

  defp running(key, timeout_ms \\ 100_000) do
    # Named keys isolate rows; high capacity only avoids unrelated fixtures contending.
    for multi <- [
          Admission.configure_fleet_multi(Multi.new(), :fleet, :new, 100),
          Admission.configure_fleet_platform_multi(
            Multi.new(),
            :platform,
            %{platform: :android},
            :new,
            100
          ),
          Admission.configure_organization_multi(
            Multi.new(),
            :org,
            %{organization_id: "org-r704"},
            :new,
            100
          ),
          Admission.configure_multi(
            Multi.new(),
            :capacity,
            %{organization_id: "org-r704", platform: :android},
            :new,
            100
          )
        ] do
      Repo.transaction(multi)
    end

    assert {:ok, changes} =
             Storage.create_multi(
               Multi.new(),
               :create,
               spec(key),
               %{max_attempts: 2, timeout_ms: timeout_ms, retry_backoff_ms: 0},
               key,
               System.system_time(:millisecond),
               &Coordinator.new/1
             )
             |> Repo.transaction()

    assert :ok = Coordinator.perform(changes[{:create, :job}])

    Repo.query!(
      "UPDATE mixer_build_coordinator_leases SET expires_at = clock_timestamp() - interval '1 second' WHERE build_record_id=$1::text::uuid",
      [current(key).record.id]
    )

    latest(key)
  end

  defp row(key) do
    case Repo.query!(
           "SELECT admission_state FROM mixer_build_operation_admissions WHERE record_id=$1::text::uuid",
           [current(key).record.id]
         ).rows do
      [[state]] -> state
      [] -> nil
    end
  end

  defp cancel(key) do
    c = current(key)

    assert {:ok, _} =
             Storage.cancel_multi(
               Multi.new(),
               :cancel,
               scope(key),
               c.record.revision,
               "cancel-" <> key,
               "requested",
               System.system_time(:millisecond),
               &Coordinator.new/1
             )
             |> Repo.transaction()

    latest(key)
  end

  defp context(key) do
    assert {:ok, %{claim: c}} =
             Admission.claim_multi(Multi.new(), :claim, scope(key), "r704-direct", 3_000)
             |> Repo.transaction()

    assert {:ok, %{renew: renewed}} =
             Admission.renew_multi(Multi.new(), :renew, c.token, 3_000) |> Repo.transaction()

    renewed
  end

  test "real guarded refresh writes admission and repeating coordinator is idempotent" do
    job = running("running")
    assert {:snooze, 1} = Coordinator.perform(job)
    assert row("running") == "admitted"
    assert {:snooze, 1} = Coordinator.perform(job)

    assert [[1]] =
             Repo.query!(
               "SELECT count(*) FROM mixer_build_operation_admissions WHERE record_id=$1::text::uuid",
               [current("running").record.id]
             ).rows
  end

  test "real stop-first refresh is permanent and stale coordinator cannot resurrect" do
    started = running("stop-first")
    stopped = cancel("stop-first")
    assert {:snooze, 1} = Coordinator.perform(stopped)
    assert row("stop-first") == "stop_intent"
    assert :ok = Coordinator.perform(started)
    c = context("stop-first")

    assert {:ok, %{decision: :fenced, state: :stop_intent}} =
             OperationAdmission.ensure_admitted(Repo, Dispatch.request(c))

    assert row("stop-first") == "stop_intent"
  end

  test "outer Multi failure rolls back real renewal plus intent" do
    running("rollback")
    c = context("rollback")

    assert {:error, :abort, :deliberate, _} =
             Admission.renew_multi(Multi.new(), :renew, c.token, 3_000)
             |> Multi.merge(fn %{renew: renewed} ->
               OperationIntent.record_multi(Multi.new(), :intent, renewed)
             end)
             |> Multi.run(:abort, fn _, _ -> {:error, :deliberate} end)
             |> Repo.transaction()

    assert row("rollback") == nil
  end

  test "real deadline transition refresh records reconciliation stop intent" do
    started = running("reconciling", 1)
    Repo.query!("SELECT pg_sleep(0.01)")
    assert :ok = Coordinator.perform(started)
    assert current("reconciling").build.state == :reconciling
    expire = latest("reconciling")
    assert expire.args["kind"] == "expire"
    assert {:snooze, 1} = Coordinator.perform(expire)
    assert row("reconciling") == "stop_intent"
  end

  test "malformed extended WorkerRef reaches no SQL" do
    running("malformed")
    c = context("malformed")
    bad = %{c | build: %{c.build | active_ref: Map.put(c.build.active_ref, :extra, true)}}

    assert [{:intent, {:run, fun}}] =
             Multi.to_list(OperationIntent.record_multi(Multi.new(), :intent, bad))

    assert {:error, _} = fun.(MixerHosted.Test.CoordinatorIntentSQLForbidden, %{})
  end

  test "exact immutable tenant and worker fences are retained" do
    running("fences")
    c = context("fences")
    request = Dispatch.request(c)

    assert {:ok, %{intent: %{state: :admitted}}} =
             OperationIntent.record_multi(Multi.new(), :intent, c) |> Repo.transaction()

    for modified <- [
          %{request | ref: %{request.ref | fence: request.ref.fence + 1}},
          %{
            request
            | ref: %{request.ref | organization_id: "other"},
              spec: %{request.spec | organization_id: "other"}
          }
        ] do
      assert {:error, :identity_conflict} = OperationAdmission.query(Repo, modified)
    end

    assert {:ok, %{decision: :admission_replay}} =
             OperationAdmission.ensure_admitted(Repo, request)
  end

  test "R718 stale job revisions never cross the renewed join" do
    job = running("r718-version")

    for version <- [job.args["revision"] - 1, job.args["revision"] + 1] do
      assert :ok = Coordinator.perform(%{job | args: Map.put(job.args, "revision", version)})
      assert row("r718-version") == nil
    end

    assert {:snooze, 1} = Coordinator.perform(job)
    assert row("r718-version") == "admitted"
  end

  test "R718 lease replacement rejects old token before admission" do
    running("r718-lease")
    old = context("r718-lease")

    Repo.query!(
      "UPDATE mixer_build_coordinator_leases SET expires_at = clock_timestamp() - interval '1 second' WHERE build_record_id=$1::text::uuid",
      [old.record.id]
    )

    assert {:ok, %{claim: successor}} =
             Admission.claim_multi(
               Multi.new(),
               :claim,
               scope("r718-lease"),
               "r718-successor",
               3_000
             )
             |> Repo.transaction()

    assert successor.token.epoch > old.token.epoch
    assert successor.build.active_ref == old.build.active_ref

    assert {:error, :renew, :stale_lease, _} =
             Admission.renew_multi(Multi.new(), :renew, old.token, 3_000)
             |> Multi.merge(fn %{renew: renewed} ->
               OperationIntent.record_multi(Multi.new(), :intent, renewed)
             end)
             |> Repo.transaction()

    assert row("r718-lease") == nil

    assert {:ok, %{intent: %{state: :admitted}}} =
             Admission.renew_multi(Multi.new(), :renew, successor.token, 3_000)
             |> Multi.merge(fn %{renew: renewed} ->
               OperationIntent.record_multi(Multi.new(), :intent, renewed)
             end)
             |> Repo.transaction()
  end

  test "R718 stop before admission survives a newer epoch ensure" do
    running("r718-stop")
    first = context("r718-stop")
    delayed = Dispatch.request(first)

    assert {:ok, _} =
             Admission.yield_multi(Multi.new(), :yield, first.token) |> Repo.transaction()

    stopped = cancel("r718-stop")
    assert {:snooze, 1} = Coordinator.perform(stopped)
    assert row("r718-stop") == "stop_intent"
    successor = context("r718-stop")
    assert successor.token.epoch > first.token.epoch

    assert {:ok, %{decision: :fenced, state: :stop_intent}} =
             OperationAdmission.ensure_admitted(Repo, Dispatch.request(successor))

    assert {:error, :stale} = OperationAdmission.ensure_admitted(Repo, delayed)
    assert row("r718-stop") == "stop_intent"
    assert successor.reservation.held
  end

  test "R718 concurrent real Coordinator replay retains one immutable operation" do
    job = running("r718-concurrent")
    before = current("r718-concurrent")

    tasks =
      for _ <- 1..4 do
        Task.async(fn ->
          receive do
            :go -> Coordinator.perform(job)
          after
            5_000 -> raise "barrier timeout"
          end
        end)
      end

    Enum.each(tasks, &send(&1.pid, :go))
    for task <- tasks, do: assert({:snooze, 1} == Task.await(task, 10_000))

    assert [[1, "admitted"]] =
             Repo.query!(
               "SELECT count(*), min(admission_state) FROM mixer_build_operation_admissions WHERE record_id=$1::text::uuid",
               [before.record.id]
             ).rows

    assert current("r718-concurrent").build.active_ref == before.build.active_ref

    assert [[true]] =
             Repo.query!(
               "SELECT held FROM mixer_build_reservations WHERE build_record_id=$1::text::uuid",
               [before.record.id]
             ).rows
  end

  test "R718 outer rollback restores prior admission and lease after stop join" do
    job = running("r718-existing-rollback")
    assert {:snooze, 1} = Coordinator.perform(job)
    cancel("r718-existing-rollback")
    c = context("r718-existing-rollback")
    assert c.build.state == :cancelling

    query =
      "SELECT admission_state, lease_epoch, journal_revision, owner_id, updated_at FROM mixer_build_operation_admissions WHERE record_id=$1::text::uuid"

    before = Repo.query!(query, [c.record.id]).rows
    assert [["admitted" | _]] = before

    assert {:error, :abort, :r718_rollback, _} =
             Admission.renew_multi(Multi.new(), :renew, c.token, 10_000)
             |> Multi.merge(fn %{renew: renewed} ->
               OperationIntent.record_multi(Multi.new(), :intent, renewed)
             end)
             |> Multi.run(:abort, fn _, %{intent: decision} ->
               assert decision.state == :stop_intent
               {:error, :r718_rollback}
             end)
             |> Repo.transaction()

    assert Repo.query!(query, [c.record.id]).rows == before
    lease = Repo.get!(Admission.Lease, c.record.id)
    assert lease.expires_at == c.lease.expires_at
  end
end
