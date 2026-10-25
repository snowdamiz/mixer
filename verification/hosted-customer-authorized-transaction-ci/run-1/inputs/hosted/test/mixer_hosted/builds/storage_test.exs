defmodule MixerHosted.Builds.StorageTest do
  use ExUnit.Case, async: false
  alias Ecto.Multi
  alias MixerHosted.{Repo, Test.BuildIntentWorker}
  alias MixerHosted.Builds.{Lifecycle, Record, Storage}
  @moduletag :database

  setup_all do
    repo =
      start_supervised!(
        {Repo,
         [
           hostname: "127.0.0.1",
           port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
           database: "mixer_builds_test",
           username: "mixer_fixture",
           pool_size: 6,
           ssl: false
         ]}
      )

    assert is_pid(repo)
    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")

    assert [
             20_261_024_000_000,
             20_261_025_000_000,
             20_261_025_000_001,
             20_261_025_000_002,
             20_261_025_000_003,
             20_261_025_000_004
           ] =
             Ecto.Migrator.run(Repo, path, :up, all: true)

    assert [] = Ecto.Migrator.run(Repo, path, :up, all: true)

    Repo.query!(
      "CREATE TABLE build_intent_probe (build_record_id uuid NOT NULL, revision bigint NOT NULL)"
    )

    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    :ok
  end

  setup do
    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_build_capacities, mixer_builds, oban_jobs, build_intent_probe"
    )

    :ok
  end

  defp spec(overrides \\ %{}) do
    Map.merge(
      %{
        organization_id: "org-a",
        project_id: "project-a",
        application_id: "app-a",
        build_id: "build-a",
        platform: :ios,
        source: %{
          kind: :revision,
          sha256: String.duplicate("a", 64),
          reference: "repository@commit"
        },
        toolchain_lock_sha256: String.duplicate("b", 64),
        build_definition_sha256: String.duplicate("c", 64)
      },
      overrides
    )
  end

  defp policy, do: %{max_attempts: 3, timeout_ms: 100, retry_backoff_ms: 10}

  defp scope(s \\ spec()),
    do: Map.take(s, [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp job(intent), do: BuildIntentWorker.new(intent)

  defp create(s \\ spec(), key \\ "request-a", now \\ 1) do
    Multi.new()
    |> Storage.create_multi(:build, s, policy(), key, now, &job/1)
    |> Repo.transaction()
  end

  defp apply_event(revision, id, event, now, s \\ scope()) do
    Multi.new()
    |> Storage.transition_multi(:build, s, revision, id, event, now, &job/1)
    |> Repo.transaction()
  end

  defp count_jobs, do: Repo.aggregate(Oban.Job, :count)

  test "actual domain and Oban rows commit together, and the test-only consumer sees the intent" do
    assert {:ok, %{{:build, :job} => persisted, build: result}} = create()
    assert result.record.revision == 0
    assert result.build.state == :queued
    assert persisted.args == result.intent
    assert persisted.queue == "builds"
    assert result.intent["attempt"] == 1 and result.intent["fence"] == 1
    assert {:ok, %{build: build}} = Storage.read(scope())
    assert build == result.build
    assert %{success: 1, failure: 0} = Oban.drain_queue(queue: :builds)
    assert %{rows: [[1]]} = Repo.query!("SELECT count(*) FROM build_intent_probe")
    assert Repo.get!(Oban.Job, persisted.id).state == "completed"
  end

  test "every scope dimension is applied to reads and transitions" do
    assert {:ok, _} = create()

    for key <- [:organization_id, :project_id, :application_id, :build_id, :platform] do
      other = Map.put(scope(), key, if(key == :platform, do: :android, else: "other"))
      assert {:error, :not_found} = Storage.read(other)

      assert {:error, :build, :not_found, _} =
               apply_event(0, "cancel", %{type: :cancel, reason: "stop"}, 2, other)
    end

    assert {:error, :invalid_scope} = Storage.read(Map.put(scope(), :role, :owner))
    assert {:error, :invalid_scope} = Storage.read(Map.put(scope(), :platform, "ios"))
    assert count_jobs() == 1
  end

  test "duplicate creation preserves first time and returns current state without invoking the job factory" do
    assert {:ok, _} = create()
    assert {:ok, _} = apply_event(0, "cancel", %{type: :cancel, reason: "stop"}, 2)

    multi =
      Storage.create_multi(Multi.new(), :build, spec(), policy(), "request-a", 999, fn _ ->
        flunk("duplicate job")
      end)

    assert {:ok, %{{:build, :job} => nil, build: result}} = Repo.transaction(multi)
    assert result.outcome == :duplicate and result.build.state == :cancelled
    assert result.record.journal["creation"]["now_ms"] == 1
    assert result.record.revision == 1 and count_jobs() == 2
  end

  test "request identity conflicts and build identity conflicts never append jobs" do
    assert {:ok, _} = create()

    assert {:error, :build, :idempotency_conflict, _} =
             create(spec(%{build_definition_sha256: String.duplicate("d", 64)}))

    assert {:error, :build, :build_conflict, _} = create(spec(), "different-request")
    assert count_jobs() == 1
    assert {:ok, _} = create(spec(%{organization_id: "other-org"}))
    assert {:ok, _} = create(spec(%{platform: :android}))
  end

  test "concurrent duplicate creates converge on one record and one job" do
    tasks = for _ <- 1..4, do: Task.async(fn -> create() end)
    results = Enum.map(tasks, &Task.await(&1, 5_000))
    assert Enum.all?(results, &match?({:ok, _}, &1))
    assert Enum.count(results, fn {:ok, %{build: b}} -> b.outcome == :applied end) == 1
    assert Repo.aggregate(Record, :count) == 1 and count_jobs() == 1
  end

  test "new events require revision CAS, while exact redelivery is idempotent at an old revision" do
    assert {:ok, %{build: created}} = create()
    {:ok, ref} = Lifecycle.worker_ref(created.build)
    event = %{type: :start, ref: ref}
    assert {:ok, %{build: started}} = apply_event(0, "start", event, 2)
    assert started.record.revision == 1

    assert {:error, :build, :stale_revision, _} =
             apply_event(0, "different", %{type: :cancel, reason: "stop"}, 3)

    assert {:ok, %{build: duplicate}} = apply_event(0, "start", event, 0)
    assert duplicate.outcome == :duplicate and duplicate.build == started.build

    assert {:error, :build, :event_conflict, _} =
             apply_event(0, "start", %{type: :cancel, reason: "stop"}, 3)

    assert count_jobs() == 2
  end

  test "concurrent start and cancellation cannot both win one revision" do
    assert {:ok, %{build: created}} = create()
    {:ok, ref} = Lifecycle.worker_ref(created.build)
    a = Task.async(fn -> apply_event(0, "start", %{type: :start, ref: ref}, 2) end)
    b = Task.async(fn -> apply_event(0, "cancel", %{type: :cancel, reason: "stop"}, 2) end)
    results = [Task.await(a), Task.await(b)]
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :build, :stale_revision, _}, &1)) == 1
    assert {:ok, %{record: %{revision: 1}}} = Storage.read(scope())
    assert count_jobs() == 2
  end

  test "running cancellation keeps execution uncertain and the old active reference" do
    assert {:ok, %{build: created}} = create()
    {:ok, ref} = Lifecycle.worker_ref(created.build)
    assert {:ok, _} = apply_event(0, "start", %{type: :start, ref: ref}, 2)
    multi = Storage.cancel_multi(Multi.new(), :build, scope(), 1, "cancel", "stop", 3, &job/1)
    assert {:ok, %{build: result}} = Repo.transaction(multi)
    assert result.build.state == :cancelling and result.build.active_ref == ref
    assert result.build.fence > ref.fence
    assert {:ok, %{worker_completion_pending: true}} = Lifecycle.customer_status(result.build)

    assert {:ok, %{build: stopped}} =
             apply_event(
               2,
               "stopped",
               %{type: :stopped, ref: ref, diagnostic_sha256: String.duplicate("d", 64)},
               4
             )

    assert stopped.build.state == :cancelled and stopped.build.active_ref == nil
  end

  test "job validation failure and wrong scope binding roll back creation" do
    for factory <- [
          fn _ -> :invalid end,
          fn args -> job(Map.put(args, "project_id", "other")) end,
          fn args -> BuildIntentWorker.new(args, queue: :signing) end
        ] do
      multi = Storage.create_multi(Multi.new(), :build, spec(), policy(), "request-a", 1, factory)
      assert {:error, {:build, :job_changeset}, _, _} = Repo.transaction(multi)
      assert {:error, :not_found} = Storage.read(scope())
      assert count_jobs() == 0
    end
  end

  test "unique, replacement, historical jobs and insert callbacks cannot suppress or redirect intents" do
    factories = [
      fn args -> BuildIntentWorker.new(args, unique: [fields: [:worker]]) end,
      fn args -> BuildIntentWorker.new(args, replace: [:args]) end,
      fn args -> BuildIntentWorker.new(args, state: "completed") end,
      fn args -> BuildIntentWorker.new(args, attempt: 1) end,
      fn args -> job(args) |> Ecto.Changeset.put_change(:id, 42) end,
      fn args ->
        job(args)
        |> Ecto.Changeset.prepare_changes(fn cs -> Ecto.Changeset.put_change(cs, :args, %{}) end)
      end,
      fn args -> %{job(args) | repo_opts: [on_conflict: :nothing]} end,
      fn args ->
        cs = job(args)
        %{cs | data: Ecto.put_meta(cs.data, source: "other_jobs")}
      end
    ]

    for factory <- factories do
      multi = Storage.create_multi(Multi.new(), :build, spec(), policy(), "request-a", 1, factory)
      assert {:error, {:build, :job_changeset}, _, _} = Repo.transaction(multi)
      assert Repo.aggregate(Record, :count) == 0 and count_jobs() == 0
    end
  end

  test "job factory exception and later transaction failure roll back all earlier writes" do
    multi =
      Storage.create_multi(Multi.new(), :build, spec(), policy(), "request-a", 1, fn _ ->
        raise "factory failed"
      end)

    assert_raise RuntimeError, "factory failed", fn -> Repo.transaction(multi) end
    assert Repo.aggregate(Record, :count) == 0 and count_jobs() == 0

    multi =
      Storage.create_multi(Multi.new(), :build, spec(), policy(), "request-a", 1, &job/1)
      |> Multi.run(:later, fn _, _ -> {:error, :forced} end)

    assert {:error, :later, :forced, _} = Repo.transaction(multi)
    assert Repo.aggregate(Record, :count) == 0 and count_jobs() == 0
  end

  test "an earlier Oban insertion rolls back when a later build operation conflicts" do
    assert {:ok, _} = create()

    multi =
      Multi.new()
      |> Oban.insert(:earlier, job(%{"synthetic" => "earlier"}))
      |> Storage.create_multi(:build, spec(), policy(), "different-key", 1, &job/1)

    assert {:error, :build, :build_conflict, _} = Repo.transaction(multi)
    assert count_jobs() == 1
  end

  test "failed transition job insertion preserves prior journal, revision and job count" do
    assert {:ok, %{build: before}} = create()

    multi =
      Storage.cancel_multi(Multi.new(), :build, scope(), 0, "cancel", "stop", 2, fn _ -> :bad end)

    assert {:error, {:build, :job_changeset}, :invalid_job_changeset, _} = Repo.transaction(multi)
    assert {:ok, %{record: record, build: build}} = Storage.read(scope())
    assert record.journal == before.record.journal and record.revision == 0
    assert build == before.build and count_jobs() == 1
  end

  test "corrupt persisted journal or indexed scope disagreement fails closed" do
    assert {:ok, %{build: created}} = create()
    original = created.record.journal

    for corrupt <- [
          Map.put(original, "surprise", true),
          put_in(original, ["creation", "spec", "project_id"], "other")
        ] do
      Repo.update_all(Record, set: [journal: corrupt])
      assert {:error, :invalid_journal} = Storage.read(scope())

      assert {:error, :build, :invalid_journal, _} =
               apply_event(0, "cancel", %{type: :cancel, reason: "stop"}, 2)

      assert count_jobs() == 1
    end

    Repo.update_all(Record, set: [journal: original, revision: 1])
    assert {:error, :invalid_journal} = Storage.read(scope())
  end

  test "database round trip replays retry history and original source without process-local state" do
    assert {:ok, %{build: created}} = create()
    {:ok, ref} = Lifecycle.worker_ref(created.build)
    assert {:ok, _} = apply_event(0, "start", %{type: :start, ref: ref}, 2)

    failure = %{
      outcome: :failed,
      class: :infrastructure,
      code: :worker_lost,
      diagnostic_sha256: String.duplicate("d", 64)
    }

    assert {:ok, _} =
             apply_event(1, "complete", %{type: :completed, ref: ref, result: failure}, 3)

    assert {:ok, %{build: retry}} = apply_event(2, "retry", %{type: :retry}, 13)
    assert {:ok, loaded} = Task.async(fn -> Storage.read(scope()) end) |> Task.await()
    assert loaded.build == retry.build and loaded.build.attempt == 2
    assert loaded.build.spec == created.build.spec
    assert loaded.record.revision == 3 and count_jobs() == 4
  end
end
