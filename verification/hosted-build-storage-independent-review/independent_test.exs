defmodule MixerHosted.BuildStorageReview.Worker do
  use Oban.Worker, queue: :builds, max_attempts: 1

  @impl true
  def perform(_job), do: :ok
end

defmodule MixerHosted.BuildStorageReview.Test do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.{Repo, BuildStorageReview.Worker}
  alias MixerHosted.Builds.{Lifecycle, Record, Storage}
  @moduletag :database

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_builds_review_test",
       username: "mixer_fixture",
       pool_size: 6,
       ssl: false}
    )

    Ecto.Migrator.run(Repo, Application.app_dir(:mixer_hosted, "priv/repo/migrations"), :up,
      all: true
    )

    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    :ok
  end

  setup do
    Repo.query!("TRUNCATE mixer_builds, oban_jobs")
    :ok
  end

  defp spec(overrides \\ %{}) do
    Map.merge(
      %{
        organization_id: "review-org",
        project_id: "review-project",
        application_id: "review-app",
        build_id: "review-build",
        platform: :ios,
        source: %{kind: :upload, sha256: String.duplicate("a", 64), reference: "private-upload"},
        toolchain_lock_sha256: String.duplicate("b", 64),
        build_definition_sha256: String.duplicate("c", 64)
      },
      overrides
    )
  end

  defp policy, do: %{max_attempts: 3, timeout_ms: 100, retry_backoff_ms: 10}
  defp scope(s \\ spec()), do: Map.take(s, [:organization_id, :project_id, :application_id, :build_id, :platform])
  defp job(intent), do: Worker.new(intent)

  defp creation(s \\ spec(), key \\ "review-request", factory \\ &job/1) do
    Storage.create_multi(Multi.new(), :decision, s, policy(), key, 1, factory)
    |> Repo.transaction()
  end

  defp event(revision, id, payload, time, factory \\ &job/1) do
    Storage.transition_multi(Multi.new(), :decision, scope(), revision, id, payload, time, factory)
    |> Repo.transaction()
  end

  defp jobs, do: Repo.all(from(j in Oban.Job, order_by: j.id))

  defp race(first, second) do
    owner = self()

    tasks =
      for operation <- [first, second] do
        Task.async(fn ->
          send(owner, {:ready, self()})
          receive do
            :go -> operation.()
          end
        end)
      end

    for _ <- tasks, do: assert_receive({:ready, _pid}, 2_000)
    for task <- tasks, do: send(task.pid, :go)
    Enum.map(tasks, &Task.await(&1, 10_000))
  end

  test "conflicting concurrent requests cannot acquire one request key for two build identities" do
    results = race(fn -> creation() end, fn -> creation(spec(%{build_id: "different-build"})) end)
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :decision, :idempotency_conflict, _}, &1)) == 1
    assert Repo.aggregate(Record, :count) == 1
    assert length(jobs()) == 1

    [{:ok, %{decision: accepted}}] = Enum.filter(results, &match?({:ok, _}, &1))
    [persisted] = jobs()
    assert persisted.args["build_record_id"] == accepted.record.id
    assert persisted.args["build_id"] == accepted.build.spec.build_id
  end

  test "one build identity under concurrent different request keys has one immutable winner" do
    results = race(fn -> creation(spec(), "key-one") end, fn -> creation(spec(), "key-two") end)
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :decision, :build_conflict, _}, &1)) == 1
    assert Repo.aggregate(Record, :count) == 1
    assert length(jobs()) == 1
  end

  test "same event ID with concurrent different payloads reports conflict, not stale success" do
    assert {:ok, %{decision: created}} = creation()
    {:ok, ref} = Lifecycle.worker_ref(created.build)

    results =
      race(
        fn -> event(0, "contended", %{type: :start, ref: ref}, 2) end,
        fn -> event(0, "contended", %{type: :cancel, reason: "review cancellation"}, 2) end
      )

    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :decision, :event_conflict, _}, &1)) == 1
    assert {:ok, %{record: record}} = Storage.read(scope())
    assert record.revision == 1 and length(record.journal["events"]) == 1
    assert length(jobs()) == 2
  end

  test "concurrent exact event redelivery adds one revision and never invokes duplicate factories" do
    assert {:ok, _} = creation()
    payload = %{type: :cancel, reason: "stop once"}
    results = race(fn -> event(0, "same", payload, 2) end, fn -> event(0, "same", payload, 3) end)
    assert Enum.all?(results, &match?({:ok, _}, &1))
    assert Enum.count(results, fn {:ok, %{decision: result}} -> result.outcome == :applied end) == 1
    assert Enum.count(results, fn {:ok, %{decision: result}} -> result.outcome == :duplicate end) == 1

    assert {:ok, %{{:decision, :job} => nil, decision: duplicate}} =
             event(0, "same", payload, nil, fn _ -> flunk("duplicate factory ran") end)

    assert duplicate.record.revision == 1 and duplicate.build.state == :cancelled
    assert length(jobs()) == 2
  end

  test "a scheduled fresh intent persists exactly once and duplicate creation cannot reschedule it" do
    at = DateTime.utc_now() |> DateTime.add(120, :second)
    scheduled = fn intent -> Worker.new(intent, scheduled_at: at, max_attempts: 7, priority: 2) end
    assert {:ok, %{{:decision, :job} => inserted, decision: created}} = creation(spec(), "scheduled", scheduled)
    assert inserted.state == "scheduled" and inserted.scheduled_at == at
    assert inserted.attempt == 0 and inserted.max_attempts == 7 and inserted.priority == 2
    assert inserted.args == created.intent and inserted.conflict? == false
    assert {:ok, %{decision: duplicate}} = creation(spec(), "scheduled", fn _ -> flunk("rescheduled duplicate") end)
    assert duplicate.outcome == :duplicate
    [persisted] = jobs()
    assert persisted.id == inserted.id and persisted.scheduled_at == at
    assert persisted.completed_at == nil and persisted.attempted_at == nil
  end

  test "callback and surrounding Multi failures leave an existing journal and prior jobs unchanged" do
    assert {:ok, %{decision: before}} = creation()
    initial_jobs = jobs()
    payload = %{type: :cancel, reason: "rollback"}

    assert_raise RuntimeError, "independent factory failure", fn ->
      event(0, "exception", payload, 2, fn _ -> raise "independent factory failure" end)
    end

    multi =
      Storage.cancel_multi(Multi.new(), :decision, scope(), 0, "later-failure", "stop", 2, &job/1)
      |> Multi.run(:reject_after_job, fn _, _ -> {:error, :review_failure} end)

    assert {:error, :reject_after_job, :review_failure, _} = Repo.transaction(multi)

    multi =
      Multi.new()
      |> Oban.insert(:prior_job, Worker.new(%{"review" => "prior"}))
      |> Storage.transition_multi(:decision, scope(), 1, "stale", payload, 2, &job/1)

    assert {:error, :decision, :stale_revision, _} = Repo.transaction(multi)
    assert {:ok, %{record: record, build: build}} = Storage.read(scope())
    assert record == before.record and build == before.build and jobs() == initial_jobs
  end

  test "every indexed scope field and indexed request key is checked against replayed creation" do
    assert {:ok, %{decision: created}} = creation()

    for field <- [:organization_id, :project_id, :application_id, :build_id, :platform] do
      replacement = if field == :platform, do: "android", else: "changed-index"
      Repo.update_all(Record, set: [{field, replacement}])
      changed_scope = Map.put(scope(), field, if(field == :platform, do: :android, else: replacement))
      assert {:error, :invalid_journal} = Storage.read(changed_scope)

      multi = Storage.cancel_multi(Multi.new(), :decision, changed_scope, 0, "bad-index", "stop", 2, &job/1)
      assert {:error, :decision, :invalid_journal, _} = Repo.transaction(multi)
      Repo.update_all(Record, set: [{field, Map.fetch!(created.record, field)}])
    end

    Repo.update_all(Record, set: [request_key: "changed-key"])
    assert {:error, :invalid_journal} = Storage.read(scope())
    Repo.update_all(Record, set: [request_key: created.record.request_key])
    assert {:ok, %{build: build}} = Storage.read(scope())
    assert build == created.build and length(jobs()) == 1
  end

  test "matching event count does not hide repeated, reordered or backwards-time journal rows" do
    assert {:ok, %{decision: created}} = creation()
    {:ok, ref} = Lifecycle.worker_ref(created.build)
    assert {:ok, _} = event(0, "start", %{type: :start, ref: ref}, 2)
    assert {:ok, %{decision: cancelled}} = event(1, "cancel", %{type: :cancel, reason: "stop"}, 3)
    original = cancelled.record.journal
    [started, cancellation] = original["events"]

    corruptions = [
      %{original | "events" => [started, started]},
      %{original | "events" => [cancellation, started]},
      %{original | "events" => [started, %{cancellation | "now_ms" => 1}]},
      put_in(original, ["creation", "request_key"], "different-request")
    ]

    for corrupt <- corruptions do
      Repo.update_all(Record, set: [journal: corrupt])
      assert {:error, :invalid_journal} = Storage.read(scope())
      assert {:error, :decision, :invalid_journal, _} = event(2, "new", %{type: :cancel, reason: "stop"}, 4)
      assert length(jobs()) == 3
    end

    Repo.update_all(Record, set: [journal: original])
    assert {:ok, %{build: build}} = Storage.read(scope())
    assert build == cancelled.build and build.active_ref == ref
  end

  test "late duplicate after retry returns latest success without reopening an old attempt" do
    assert {:ok, %{decision: created}} = creation()
    {:ok, first_ref} = Lifecycle.worker_ref(created.build)
    first_start = %{type: :start, ref: first_ref}
    assert {:ok, _} = event(0, "start-one", first_start, 2)

    failed = %{
      type: :completed,
      ref: first_ref,
      result: %{
        outcome: :failed,
        class: :infrastructure,
        code: :worker_lost,
        diagnostic_sha256: String.duplicate("d", 64)
      }
    }

    assert {:ok, _} = event(1, "failed-one", failed, 3)
    assert {:ok, %{decision: retried}} = event(2, "retry-two", %{type: :retry}, 13)
    {:ok, second_ref} = Lifecycle.worker_ref(retried.build)
    assert {:ok, _} = event(3, "start-two", %{type: :start, ref: second_ref}, 14)

    artifacts =
      for kind <- [:unsigned_native_binary, :guest_artifact, :resource_inventory, :debug_symbols, :compatibility_report, :sbom, :provenance] do
        %Lifecycle.ArtifactRef{kind: kind, sha256: String.duplicate("e", 64), size_bytes: 64}
      end

    assert {:ok, %{decision: succeeded}} =
             event(4, "success-two", %{type: :completed, ref: second_ref, result: %{outcome: :succeeded, artifacts: artifacts}}, 15)

    assert {:ok, %{decision: duplicate}} =
             event(0, "start-one", first_start, nil, fn _ -> flunk("historical duplicate factory ran") end)

    assert duplicate.build == succeeded.build and duplicate.record == succeeded.record
    assert duplicate.build.state == :succeeded and duplicate.build.attempt == 2
    assert duplicate.record.revision == 5 and length(jobs()) == 6
  end
end
