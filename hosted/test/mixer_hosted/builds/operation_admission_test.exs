defmodule MixerHosted.Test.OperationInput do
  alias MixerHosted.Builds.{Lifecycle, Dispatch}

  def request(key, opts \\ []) do
    now = System.system_time(:millisecond)

    spec = %{
      organization_id: "org-r520",
      project_id: "project-r520",
      application_id: "app-r520",
      build_id: key,
      platform: :android,
      source: %{kind: :revision, sha256: String.duplicate("a", 64), reference: "repo@immutable"},
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }

    {:ok, build} =
      Lifecycle.new(spec, %{max_attempts: 5, timeout_ms: 600_000, retry_backoff_ms: 0}, key, now)

    {:ok, ref} = Lifecycle.worker_ref(build)
    {:ok, build, :applied} = Lifecycle.transition(build, "start", %{type: :start, ref: ref}, now)
    build = %{build | deadline: Keyword.get(opts, :deadline, build.deadline)}

    Dispatch.request(%{
      build: build,
      record: %{id: "00000000-0000-4000-8000-000000000520", revision: 1},
      token: %{owner_id: "coordinator-r520", epoch: 1},
      lease: %{expires_at: DateTime.add(DateTime.utc_now(), 300, :second)}
    })
  end

  def guard(r, fields), do: %{r | guard: Map.merge(r.guard, fields)}
end

defmodule MixerHosted.Test.OperationRepo do
  alias MixerHosted.Repo
  defdelegate query(sql, params), to: Repo

  def run(sql) do
    case Repo.query(sql, []) do
      {:ok, %{rows: rows}} ->
        output =
          Enum.map_join(rows || [], "", fn row ->
            Enum.map_join(row, "|", fn
              nil -> ""
              v when is_binary(v) -> v
              v -> to_string(v)
            end) <> "\n"
          end)

        {output, 0}

      {:error, error} ->
        {inspect(error), 1}
    end
  end

  def lock(id) do
    owner = self()

    task =
      Task.async(fn ->
        Repo.transaction(fn ->
          Repo.query!(
            "SELECT pg_advisory_xact_lock(hashtextextended('mixer-build-admission:' || $1, 0))",
            [id]
          )

          send(owner, {:r520_locked, self()})

          receive do
            :unlock -> :ok
          after
            5_000 -> raise "lock release deadline"
          end
        end)
      end)

    receive do
      {:r520_locked, _} -> task
    after
      3_000 -> raise "lock acquisition deadline"
    end
  end

  def unlock(task) do
    send(task.pid, :unlock)
    {:ok, :ok} = Task.await(task, 8_000)
    :ok
  end
end

defmodule MixerHosted.Test.ForbiddenOperationSQL do
  def query(_, _), do: raise("invalid request reached SQL")
end

defmodule MixerHosted.Test.OperationAdmissionAbort do
  use Ecto.Migration

  def up do
    apply(MixerHosted.Repo.Migrations.AddPrivateBuildOperationAdmission, :up, [])
    flush()
    raise "R574 deliberate DDL transaction abort"
  end
end

defmodule MixerHosted.Builds.OperationAdmissionTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Dispatch, OperationAdmission}
  alias OperationAdmission, as: Store
  alias MixerHosted.Test.OperationRepo, as: Repo
  import MixerHosted.Test.OperationInput

  setup_all do
    config = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
      username: "mixer_fixture",
      database: "mixer_operation_admission_test",
      pool_size: 6,
      log: false
    ]

    start_supervised!({MixerHosted.Repo, config})

    migration =
      Path.expand(
        "../../../priv/unselected_operation_admission/20261110000498_add_private_build_operation_admission.exs",
        __DIR__
      )

    Code.require_file(migration)
    candidate = MixerHosted.Repo.Migrations.AddPrivateBuildOperationAdmission

    assert_raise RuntimeError, "R574 deliberate DDL transaction abort", fn ->
      Ecto.Migrator.up(
        MixerHosted.Repo,
        20_261_110_000_498,
        MixerHosted.Test.OperationAdmissionAbort,
        log: false
      )
    end

    assert [[nil]] ==
             MixerHosted.Repo.query!("SELECT to_regclass('mixer_build_operation_admissions')").rows

    assert [[0]] ==
             MixerHosted.Repo.query!(
               "SELECT count(*) FROM pg_proc WHERE proname IN ('mixer_build_operation_admit','mixer_build_operation_admissions_immutable')"
             ).rows

    assert [[0]] ==
             MixerHosted.Repo.query!("SELECT count(*) FROM schema_migrations WHERE version=$1", [
               20_261_110_000_498
             ]).rows

    assert :ok == Ecto.Migrator.up(MixerHosted.Repo, 20_261_110_000_498, candidate, log: false)

    assert :already_up ==
             Ecto.Migrator.up(MixerHosted.Repo, 20_261_110_000_498, candidate, log: false)

    assert_raise RuntimeError,
                 "permanent operation identities require an explicit retention migration decision",
                 fn ->
                   Ecto.Migrator.down(MixerHosted.Repo, 20_261_110_000_498, candidate, log: false)
                 end

    :ok
  end

  test "private migration stays outside the closed production twelve" do
    path = Path.expand("../../../priv/repo/migrations", __DIR__)
    assert :ok == MixerHosted.Test.Migrations.check_files!(path)
    assert length(MixerHosted.Test.Migrations.versions()) == 12
    refute 20_261_110_000_498 in MixerHosted.Test.Migrations.versions()
  end

  test "closed WorkerRef rejects extra and malformed values before all SQL actions" do
    r = request("permanent-boundaries")

    bad = [
      Map.put(r.ref, :extra, String.duplicate("x", 1_048_576)),
      Map.delete(r.ref, :fence),
      Map.from_struct(r.ref),
      Map.put(r.ref, :__struct__, MixerHosted.Builds.Lifecycle.Spec),
      %{r.ref | organization_id: <<255>>},
      %{r.ref | organization_id: String.duplicate("a", 129)},
      %{r.ref | organization_id: String.duplicate("é", 64) <> "a"},
      %{r.ref | fence: 0},
      %{r.ref | attempt: 6}
    ]

    for ref <- bad, action <- [:query, :ensure_admitted, :stop_intent] do
      assert {:error, :invalid_request} ==
               apply(Store, action, [MixerHosted.Test.ForbiddenOperationSQL, %{r | ref: ref}])
    end
  end

  test "real factory keeps exact boundary identities and typed private admission" do
    for {label, id} <- [
          {"ascii", String.duplicate("a", 128)},
          {"unicode", String.duplicate("é", 64)},
          {"quote", String.duplicate("\"", 128)},
          {"slash", String.duplicate("\\", 128)},
          {"tab", String.duplicate("\t", 128)},
          {"newline", String.duplicate("\n", 128)}
        ] do
      base = request("boundary-" <> label)
      now = System.system_time(:millisecond)
      spec = base.spec |> Map.from_struct() |> Map.put(:organization_id, id)

      {:ok, build} =
        MixerHosted.Builds.Lifecycle.new(
          spec,
          %{max_attempts: 5, timeout_ms: 600_000, retry_backoff_ms: 0},
          label,
          now
        )

      {:ok, ref} = MixerHosted.Builds.Lifecycle.worker_ref(build)

      {:ok, build, :applied} =
        MixerHosted.Builds.Lifecycle.transition(build, "start", %{type: :start, ref: ref}, now)

      r =
        Dispatch.request(%{
          build: build,
          record: %{id: base.guard.record_id, revision: base.guard.revision},
          token: %{owner_id: base.guard.owner_id, epoch: base.guard.epoch},
          lease: %{expires_at: base.guard.expires_at}
        })

      assert {:ok, %Store.Admission{decision: :admission_recorded}} =
               Store.ensure_admitted(Repo, r)

      assert [[stored_ref, stored_spec, deadline]] =
               MixerHosted.Repo.query!(
                 "SELECT original_ref,original_spec,deadline_ms FROM mixer_build_operation_admissions WHERE operation_id=$1",
                 [r.operation_id]
               ).rows

      assert stored_ref == :erlang.term_to_binary(r.ref, [:deterministic])
      assert stored_spec == :erlang.term_to_binary(r.spec, [:deterministic])
      assert deadline == r.deadline_ms
      assert {:error, :invalid_observation} == Dispatch.observation(r, Store.query(Repo, r))
    end
  end

  test "query binds immutable identity and watermark without worker or capacity evidence" do
    r = request("query")
    assert {:ok, value} = Store.query(Repo, r)
    assert value.state == :unadmitted and value.decision == :read
    assert {:error, :invalid_observation} = Dispatch.observation(r, {:ok, value})

    assert {:ok, %{decision: :admission_recorded, state: :admitted}} =
             Store.ensure_admitted(Repo, r)

    assert {:ok, %{decision: :admission_replay}} = Store.ensure_admitted(Repo, r)
    assert {:ok, %{state: :admitted}} = Store.query(Repo, r)
  end

  test "four concurrent identical requests admit exactly once and retain exact bytes" do
    r = request("same-key")
    tasks = for _ <- 1..4, do: Task.async(fn -> Store.ensure_admitted(Repo, r) end)

    decisions =
      Enum.map(tasks, fn t ->
        {:ok, v} = Task.await(t, 8_000)
        v.decision
      end)

    assert Enum.count(decisions, &(&1 == :admission_recorded)) == 1
    assert Enum.count(decisions, &(&1 == :admission_replay)) == 3
    ref = Base.encode16(:erlang.term_to_binary(r.ref, [:deterministic]), case: :lower)
    spec = Base.encode16(:erlang.term_to_binary(r.spec, [:deterministic]), case: :lower)
    expected = "#{ref}|#{spec}|#{r.deadline_ms}\n"

    assert {^expected, 0} =
             Repo.run(
               "SELECT encode(original_ref,'hex'), encode(original_spec,'hex'), deadline_ms FROM mixer_build_operation_admissions WHERE operation_id = '#{r.operation_id}'"
             )
  end

  test "concurrent conflicting immutable specs have one winner" do
    r = request("race-conflict")
    other = %{r | spec: %{r.spec | build_definition_sha256: String.duplicate("d", 64)}}

    results =
      [r, other]
      |> Enum.map(fn q -> Task.async(fn -> Store.ensure_admitted(Repo, q) end) end)
      |> Enum.map(&Task.await(&1, 8_000))

    assert Enum.count(results, &match?({:ok, %{decision: :admission_recorded}}, &1)) == 1
    assert Enum.count(results, &(&1 == {:error, :identity_conflict})) == 1
  end

  test "every immutable field including source and all tenant dimensions conflicts" do
    r = request("immutability")
    assert {:ok, _} = Store.ensure_admitted(Repo, r)

    changed = [
      %{r | deadline_ms: r.deadline_ms + 1},
      %{r | ref: %{r.ref | attempt: 2}},
      %{r | ref: %{r.ref | fence: 2}},
      %{r | spec: %{r.spec | source: %{r.spec.source | kind: :upload}}},
      %{r | spec: %{r.spec | source: %{r.spec.source | reference: "different"}}},
      %{r | spec: %{r.spec | source: %{r.spec.source | sha256: String.duplicate("d", 64)}}},
      %{r | spec: %{r.spec | toolchain_lock_sha256: String.duplicate("d", 64)}},
      guard(r, %{record_id: "00000000-0000-4000-8000-000000000499"})
    ]

    changed =
      changed ++
        for key <- [:organization_id, :project_id, :application_id, :build_id, :platform] do
          v = if key == :platform, do: :ios, else: "other"
          %{r | ref: Map.put(r.ref, key, v), spec: Map.put(r.spec, key, v)}
        end

    for q <- changed, do: assert({:error, :identity_conflict} = Store.query(Repo, q))

    for q <- changed do
      q = %{
        q
        | operation_id:
            :crypto.hash(:sha256, :erlang.term_to_binary(q)) |> Base.encode16(case: :lower)
      }

      assert {:ok, %{decision: :admission_recorded}} = Store.ensure_admitted(Repo, q)
    end
  end

  test "lexicographic epoch/revision ordering, same-epoch owner and query watermark" do
    r = request("ordering")
    high = guard(r, %{revision: 32})
    assert {:ok, _} = Store.query(Repo, high)
    assert {:error, :stale} = Store.ensure_admitted(Repo, r)
    assert {:error, :stale} = Store.stop_intent(Repo, r)
    assert {:error, :stale} = Store.query(Repo, guard(high, %{owner_id: "other"}))
    newer = guard(r, %{epoch: 2, revision: 0, owner_id: "new-owner"})
    assert {:ok, %{version: {2, 0}}} = Store.ensure_admitted(Repo, newer)
    assert {:error, :stale} = Store.query(Repo, high)
    assert {:ok, %{version: {2, 1}}} = Store.query(Repo, guard(newer, %{revision: 1}))
    assert {:error, :stale} = Store.stop_intent(Repo, newer)
  end

  test "expired lease cannot query, admit or stop even absent; deadline only blocks admission" do
    r =
      request("expired-lease")
      |> guard(%{expires_at: DateTime.add(DateTime.utc_now(), -1, :second)})

    for fun <- [&Store.query/2, &Store.ensure_admitted/2, &Store.stop_intent/2],
        do: assert({:error, :stale} = fun.(Repo, r))

    assert {"0\n", 0} =
             Repo.run(
               "SELECT count(*) FROM mixer_build_operation_admissions WHERE operation_id = '#{r.operation_id}'"
             )

    r = request("expired-deadline", deadline: 0)
    assert {:error, :deadline_expired} = Store.ensure_admitted(Repo, r)
    assert {:ok, %{state: :stop_intent}} = Store.stop_intent(Repo, r)
    assert {:ok, %{state: :stop_intent}} = Store.query(Repo, r)
  end

  test "lease and deadline are checked after waiting for the operation lock" do
    for kind <- [:lease, :deadline] do
      r = request("locked-#{kind}")
      port = Repo.lock(r.operation_id)

      r =
        if kind == :lease,
          do: guard(r, %{expires_at: DateTime.add(DateTime.utc_now(), 150, :millisecond)}),
          else: %{r | deadline_ms: System.system_time(:millisecond) + 150}

      task = Task.async(fn -> Store.ensure_admitted(Repo, r) end)
      # This bounded SQL wait expires the request while another connection owns its key.
      assert {_, 0} = Repo.run("SELECT pg_sleep(0.3)")
      :ok = Repo.unlock(port)
      expected = if kind == :lease, do: :stale, else: :deadline_expired
      assert {:error, ^expected} = Task.await(task, 8_000)
    end
  end

  test "stop before ensure is permanent, including a delayed higher-epoch ensure" do
    r = request("stop-first")
    assert {:ok, %{decision: :stop_recorded, state: :stop_intent}} = Store.stop_intent(Repo, r)
    assert {:ok, %{decision: :stop_replay}} = Store.stop_intent(Repo, r)

    assert {:ok, value} =
             Store.ensure_admitted(Repo, guard(r, %{epoch: 2, revision: 0, owner_id: "next"}))

    assert value.decision == :fenced and value.state == :stop_intent
    assert {:error, :invalid_observation} = Dispatch.observation(r, {:ok, value})
    assert {:error, :stale} = Store.ensure_admitted(Repo, r)
  end

  test "concurrent stop/ensure ends fenced regardless of serialization order" do
    r = request("stop-race")

    tasks = [
      Task.async(fn -> Store.ensure_admitted(Repo, r) end),
      Task.async(fn -> Store.stop_intent(Repo, r) end)
    ]

    assert Enum.all?(Enum.map(tasks, &Task.await(&1, 8_000)), &match?({:ok, _}, &1))
    assert {:ok, %{state: :stop_intent}} = Store.query(Repo, r)
    assert {:ok, %{decision: :fenced}} = Store.ensure_admitted(Repo, r)
  end

  test "caller rollback and abrupt DB-session death leave no admitted row" do
    r = request("rollback")

    assert {:error, :deliberate} =
             MixerHosted.Repo.transaction(fn ->
               assert {:ok, _} = Store.ensure_admitted(Repo, r)
               MixerHosted.Repo.rollback(:deliberate)
             end)

    assert {"0\n", 0} =
             Repo.run(
               "SELECT count(*) FROM mixer_build_operation_admissions WHERE operation_id = '#{r.operation_id}'"
             )

    assert {:ok, %{decision: :admission_recorded}} = Store.ensure_admitted(Repo, r)
    r = request("crash-before-commit")

    terminated =
      try do
        MixerHosted.Repo.transaction(fn ->
          assert {:ok, _} = Store.ensure_admitted(Repo, r)
          MixerHosted.Repo.query!("SELECT pg_terminate_backend(pg_backend_pid())")
        end)
      rescue
        error in Postgrex.Error -> {:terminated, error.postgres.code}
        error in DBConnection.ConnectionError -> {:terminated, error.message}
      end

    assert match?({:terminated, _}, terminated) or match?({:error, _}, terminated)

    assert {"0\n", 0} =
             Repo.run(
               "SELECT count(*) FROM mixer_build_operation_admissions WHERE operation_id = '#{r.operation_id}'"
             )
  end

  test "a caller crash after commit retries as replay and a lost stop response remains fenced" do
    for {key, fun} <- [
          {"durable-admission", &Store.ensure_admitted/2},
          {"durable-stop", &Store.stop_intent/2}
        ] do
      r = request(key, deadline: 9_000_000_000_000_000)

      {pid, monitor} =
        spawn_monitor(fn ->
          {:ok, _} = fun.(Repo, r)
          exit(:simulated_lost_response)
        end)

      assert_receive {:DOWN, ^monitor, :process, ^pid, :simulated_lost_response}
      expected = if key == "durable-stop", do: :stop_replay, else: :admission_replay
      assert {:ok, %{decision: ^expected}} = fun.(Repo, r)
    end
  end

  test "SQL backstops forbid immutable mutation, version regression, reopen and deletion" do
    r = request("sql-backstop")
    assert {:ok, _} = Store.stop_intent(Repo, r)

    for statement <- [
          "UPDATE mixer_build_operation_admissions SET original_spec = decode('00','hex')",
          "UPDATE mixer_build_operation_admissions SET lease_epoch = 0",
          "UPDATE mixer_build_operation_admissions SET admission_state = 'admitted'",
          "DELETE FROM mixer_build_operation_admissions"
        ] do
      {_, code} = Repo.run(statement <> " WHERE operation_id = '#{r.operation_id}'")
      assert code != 0
    end

    assert {:ok, %{state: :stop_intent}} = Store.query(Repo, r)
  end

  test "malformed trusted inputs fail closed without producing worker observations" do
    r = request("malformed")

    for q <- [
          %{r | guard: %{}},
          %{r | operation_id: "wrong"},
          %{r | spec: Map.from_struct(r.spec)},
          %{r | ref: %{r.ref | fence: 0}},
          %{r | deadline_ms: -1}
        ] do
      assert {:error, :invalid_request} = Store.ensure_admitted(Repo, q)
    end
  end
end
