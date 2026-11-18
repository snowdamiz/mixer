defmodule R836.Adapter do
  alias MixerHosted.Builds.Dispatch.Observation

  def query(request) do
    case Application.fetch_env!(:mixer_hosted, :r836_control) do
      {:block, owner} ->
        send(owner, {:r836_query_blocked, self(), request})

        receive do
          :r836_continue -> observation(request, :absent)
        after
          5_000 -> raise "R836 query barrier timed out"
        end

      {:observe, owner} ->
        send(owner, {:r836_callback, :query, request})
        observation(request, :absent)
    end
  end

  def ensure_started(request) do
    {_, owner} = Application.fetch_env!(:mixer_hosted, :r836_control)
    send(owner, {:r836_callback, :ensure_started, request})
    {:error, :uncertain}
  end

  def stop(_), do: raise("R836 must not model worker termination")

  defp observation(request, status),
    do: {:ok, %Observation{operation_id: request.operation_id, ref: request.ref, status: status}}
end

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
    r836_install_audit()
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

  defp r836_install_audit do
    Repo.query!("""
    CREATE TABLE r836_dml_audit (
      seq bigserial PRIMARY KEY, relation text NOT NULL, action text NOT NULL,
      record_id text NOT NULL, xid bigint NOT NULL, backend integer NOT NULL,
      body jsonb NOT NULL
    )
    """)

    Repo.query!("""
    CREATE FUNCTION r836_capture_dml() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      INSERT INTO r836_dml_audit(relation, action, record_id, xid, backend, body)
      VALUES (TG_TABLE_NAME, TG_OP,
        CASE WHEN TG_TABLE_NAME = 'mixer_build_operation_admissions'
          THEN to_jsonb(NEW)->>'record_id' ELSE to_jsonb(NEW)->>'build_record_id' END,
        txid_current(), pg_backend_pid(), to_jsonb(NEW));
      RETURN NEW;
    END $$
    """)

    for table <- ["mixer_build_operation_admissions", "mixer_build_coordinator_leases"] do
      Repo.query!(
        "CREATE TRIGGER r836_audit AFTER INSERT OR UPDATE ON #{table} FOR EACH ROW EXECUTE FUNCTION r836_capture_dml()"
      )
    end
  end

  defp r836_settings do
    keys = [:build_operation_intent, :build_dispatch, :r836_control]
    previous = for key <- keys, do: {key, Application.fetch_env(:mixer_hosted, key)}

    on_exit(fn ->
      Enum.each(previous, fn {key, value} -> r836_restore(key, value) end)
      for {key, value} <- previous, do: assert(Application.fetch_env(:mixer_hosted, key) == value)
    end)

    Application.put_env(:mixer_hosted, :build_dispatch,
      adapter: R836.Adapter,
      lease_ttl_ms: 30_000,
      call_timeout_ms: 5_000,
      poll_ms: 1
    )

    Application.put_env(:mixer_hosted, :r836_control, {:observe, self()})
    previous
  end

  defp r836_restore(key, {:ok, value}), do: Application.put_env(:mixer_hosted, key, value)
  defp r836_restore(key, :error), do: Application.delete_env(:mixer_hosted, key)

  defp r836_private_rows do
    Repo.query!(
      "SELECT row_to_json(a)::text FROM mixer_build_operation_admissions a ORDER BY operation_id"
    ).rows
  end

  defp r836_intent_audit do
    Repo.query!(
      "SELECT seq, action, record_id, xid, backend, body::text FROM r836_dml_audit WHERE relation='mixer_build_operation_admissions' ORDER BY seq"
    ).rows
  end

  defp r836_audit_for(id) do
    Repo.query!(
      "SELECT relation, action, xid, backend, body::text FROM r836_dml_audit WHERE record_id=$1 ORDER BY seq",
      [id]
    ).rows
  end

  defp r836_wait_blocked(blocker, remaining \\ 200)

  defp r836_wait_blocked(_, 0),
    do: flunk("second refresh did not block on the exact owned DB mutex")

  defp r836_wait_blocked(blocker, remaining) do
    rows =
      Repo.query!(
        "SELECT pid, wait_event_type, wait_event, query FROM pg_stat_activity WHERE $1::int = ANY(pg_blocking_pids(pid)) AND query = 'SELECT pg_advisory_xact_lock(1296648258, 1)'",
        [blocker]
      ).rows

    case rows do
      [[_, "Lock", "advisory", _] = row] ->
        row

      [[pid, nil, nil, "SELECT pg_advisory_xact_lock(1296648258, 1)"]]
      when is_integer(pid) and pid > 0 ->
        Process.sleep(10)
        r836_wait_blocked(blocker, remaining - 1)

      [] ->
        Process.sleep(10)
        r836_wait_blocked(blocker, remaining - 1)

      other ->
        flunk("unexpected blocking evidence: #{inspect(other)}")
    end
  end

  test "R836 selected in-flight second refresh retains snapshot after removal then new absent invocation preserves intent" do
    previous = r836_settings()
    Application.put_env(:mixer_hosted, :build_operation_intent, :durable_intent_v1)
    job = running("r836-lifetime")
    Application.put_env(:mixer_hosted, :r836_control, {:block, self()})
    task = Task.async(fn -> Coordinator.perform(job) end)
    assert_receive {:r836_query_blocked, callback, request}, 3_000
    assert row("r836-lifetime") == "admitted"
    prior_row = r836_private_rows()
    first_audit = r836_intent_audit()
    owner = self()

    lock =
      Task.async(fn ->
        Repo.transaction(fn ->
          Repo.query!("SELECT pg_advisory_xact_lock(1296648258, 1)")
          [[backend]] = Repo.query!("SELECT pg_backend_pid()").rows
          send(owner, {:r836_mutex_owned, self(), backend})

          receive do
            :r836_release -> :released
          after
            4_000 -> raise "R836 mutex release deadline"
          end
        end)
      end)

    assert_receive {:r836_mutex_owned, lock_pid, backend}, 2_000

    try do
      send(callback, :r836_continue)
      r836_wait_blocked(backend)
      Application.delete_env(:mixer_hosted, :build_operation_intent)
      assert Application.fetch_env(:mixer_hosted, :build_operation_intent) == :error
      send(lock_pid, :r836_release)
      assert {:ok, :released} = Task.await(lock, 5_000)
      assert {:snooze, 1} = Task.await(task, 5_000)
      assert_receive {:r836_callback, :ensure_started, second}, 2_000
      assert second.operation_id == request.operation_id
      assert second.ref == request.ref and second.spec == request.spec
      assert second.deadline_ms == request.deadline_ms
      assert second.guard.owner_id == request.guard.owner_id
      assert second.guard.epoch == request.guard.epoch
      after_audit = r836_intent_audit()
      assert length(after_audit) == length(first_audit) + 1
      assert [_, "UPDATE", id, xid, sql_backend, encoded] = List.last(after_audit)
      assert id == request.guard.record_id
      body = Jason.decode!(encoded)
      assert body["operation_id"] == request.operation_id
      assert body["owner_id"] == request.guard.owner_id
      assert body["lease_epoch"] == request.guard.epoch
      assert body["journal_revision"] == request.guard.revision
      assert body["admission_state"] == "admitted"

      matching =
        Enum.filter(r836_audit_for(id), fn [relation, _, tx, pid, _] ->
          relation == "mixer_build_coordinator_leases" and tx == xid and pid == sql_backend
        end)

      assert [[_, "UPDATE", ^xid, ^sql_backend, lease_json]] = matching
      lease = Jason.decode!(lease_json)
      assert lease["owner_id"] == body["owner_id"] and lease["epoch"] == body["lease_epoch"]
      assert r836_private_rows() != prior_row
      retained = r836_private_rows()
      retained_audit = r836_intent_audit()
      Application.put_env(:mixer_hosted, :r836_control, {:observe, self()})
      assert {:snooze, 1} = Coordinator.perform(job)
      assert_receive {:r836_callback, :query, absent_query}, 2_000
      assert_receive {:r836_callback, :ensure_started, absent_ensure}, 2_000
      assert absent_query.operation_id == request.operation_id
      assert absent_ensure.operation_id == request.operation_id
      assert r836_private_rows() == retained
      assert r836_intent_audit() == retained_audit
    after
      send(lock.pid, :r836_release)
      send(callback, :r836_continue)
      Enum.each(previous, fn {key, value} -> r836_restore(key, value) end)
    end
  end

  test "R836 fresh absent invocation uses both original refreshes without private DML" do
    previous = r836_settings()

    try do
      Application.delete_env(:mixer_hosted, :build_operation_intent)
      job = running("r836-fresh-absent")
      before_rows = r836_private_rows()
      before_dml = r836_intent_audit()
      assert {:snooze, 1} = Coordinator.perform(job)
      assert_receive {:r836_callback, :query, query}, 2_000
      assert_receive {:r836_callback, :ensure_started, ensure}, 2_000
      assert query.operation_id == ensure.operation_id
      assert row("r836-fresh-absent") == nil
      assert r836_private_rows() == before_rows
      assert r836_intent_audit() == before_dml
    after
      Enum.each(previous, fn {key, value} -> r836_restore(key, value) end)
    end
  end

  test "R836 malformed present selection refuses before lease renewal or callback" do
    previous = r836_settings()

    try do
      Application.delete_env(:mixer_hosted, :build_operation_intent)
      job = running("r836-malformed")
      id = current("r836-malformed").record.id
      before_rows = r836_private_rows()
      before_dml = r836_intent_audit()
      before_lease = Repo.get!(Admission.Lease, id)

      for value <- [
            nil,
            false,
            "durable_intent_v1",
            :unsupported,
            [],
            %{mode: :durable_intent_v1}
          ] do
        Application.put_env(:mixer_hosted, :build_operation_intent, value)
        assert {:error, :invalid_operation_intent_configuration} = Coordinator.perform(job)
        assert Repo.get!(Admission.Lease, id) == before_lease
        assert r836_private_rows() == before_rows
        assert r836_intent_audit() == before_dml
      end

      refute_receive {:r836_callback, _, _}, 50
    after
      Enum.each(previous, fn {key, value} -> r836_restore(key, value) end)
    end
  end
end
