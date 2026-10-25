defmodule MixerHosted.Builds.AdmissionTest do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.{Repo, Test.BuildIntentWorker}
  alias MixerHosted.Builds.{Admission, Lifecycle, Record, Storage}
  alias Admission.{Capacity, Lease, Reservation}
  @moduletag :database

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_admission_test",
       username: "mixer_fixture",
       pool_size: 8,
       ssl: false}
    )

    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")
    assert length(Ecto.Migrator.run(Repo, path, :up, all: true)) == 4
    assert [] == Ecto.Migrator.run(Repo, path, :up, all: true)
    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    :ok
  end

  setup do
    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_build_capacities, mixer_build_organization_capacities, mixer_build_fleet_platform_capacities, mixer_build_fleet_capacity, mixer_builds, oban_jobs"
    )

    assert {:ok, _} =
             Multi.new()
             |> Admission.configure_fleet_multi(:fleet, :new, 10_000)
             |> Admission.configure_fleet_platform_multi(:ios, %{platform: :ios}, :new, 10_000)
             |> Admission.configure_fleet_platform_multi(
               :android,
               %{platform: :android},
               :new,
               10_000
             )
             |> Admission.configure_organization_multi(
               :org,
               %{organization_id: "org-a"},
               :new,
               10_000
             )
             |> Admission.configure_organization_multi(
               :other_org,
               %{organization_id: "other-org"},
               :new,
               10_000
             )
             |> Repo.transaction()

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

  defp scope(s \\ spec()),
    do: Map.take(s, [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp capacity_scope(s \\ scope()), do: Map.take(s, [:organization_id, :platform])
  defp policy, do: %{max_attempts: 3, timeout_ms: 100_000, retry_backoff_ms: 0}
  defp job(intent), do: BuildIntentWorker.new(intent)

  defp create(s \\ spec(), p \\ policy()) do
    Storage.create_multi(Multi.new(), :created, s, p, "request-#{s.build_id}", 1, &job/1)
    |> Repo.transaction()
  end

  defp configure(s \\ capacity_scope(), revision \\ :new, limit \\ 1) do
    Admission.configure_multi(Multi.new(), :capacity, s, revision, limit) |> Repo.transaction()
  end

  defp claim(s \\ scope(), owner \\ "coordinator-a", ttl \\ 60_000) do
    Admission.claim_multi(Multi.new(), :claim, s, owner, ttl) |> Repo.transaction()
  end

  defp renew(token, ttl \\ 60_000),
    do: Admission.renew_multi(Multi.new(), :renew, token, ttl) |> Repo.transaction()

  defp transition(token, revision, id, event, factory \\ &job/1) do
    Admission.transition_multi(Multi.new(), :build, token, revision, id, event, factory)
    |> Repo.transaction()
  end

  defp release(token, event),
    do: Admission.release_multi(Multi.new(), :release, token, event) |> Repo.transaction()

  defp start_claim(claimed) do
    {:ok, ref} = Lifecycle.worker_ref(claimed.build)

    assert {:ok, %{build: started}} =
             transition(claimed.token, claimed.record.revision, "start", %{type: :start, ref: ref})

    {started, ref}
  end

  defp expire_lease do
    Repo.query!(
      "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) - interval '1 second'"
    )
  end

  defp failed(ref),
    do: %{
      type: :completed,
      ref: ref,
      result: %{
        outcome: :failed,
        class: :infrastructure,
        code: :worker_lost,
        diagnostic_sha256: String.duplicate("d", 64)
      }
    }

  defp now_ms do
    %{rows: [[now]]} =
      Repo.query!("SELECT floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint")

    now
  end

  test "capacity requires explicit exact configuration with bounded limit and revision CAS" do
    assert {:ok, _} = create()
    assert {:error, :claim, :scope_not_found_or_unconfigured, _} = claim()
    assert {:ok, %{capacity: %{revision: 0, limit: 1}}} = configure()
    assert {:error, :capacity, :capacity_exists, _} = configure()
    assert {:ok, %{capacity: %{revision: 1, limit: 0}}} = configure(capacity_scope(), 0, 0)
    assert {:error, :capacity, :stale_capacity_revision, _} = configure(capacity_scope(), 0, 2)
    assert {:error, :claim, :capacity_exhausted, _} = claim()

    for limit <- [-1, 10_001, 1.0, nil] do
      assert {:error, :capacity, :invalid_capacity_policy, _} =
               configure(capacity_scope(), 1, limit)
    end

    assert Repo.aggregate(Capacity, :count) == 1
    assert Repo.aggregate(Reservation, :count) == 0
  end

  test "simultaneous claims across replicas cannot overbook the last slot" do
    assert {:ok, _} = configure()
    specs = for n <- 1..6, do: spec(%{build_id: "build-#{n}"})
    for s <- specs, do: assert({:ok, _} = create(s))
    parent = self()

    tasks =
      for s <- specs do
        Task.async(fn ->
          send(parent, {:ready, self()})

          receive do
            :go -> claim(scope(s), "owner-#{s.build_id}")
          end
        end)
      end

    for _ <- specs, do: assert_receive({:ready, _}, 1000)
    for task <- tasks, do: send(task.pid, :go)
    results = Enum.map(tasks, &Task.await(&1, 10_000))
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :claim, :capacity_exhausted, _}, &1)) == 5
    assert Repo.aggregate(from(r in Reservation, where: r.held), :count) == 1
    assert Repo.aggregate(Lease, :count) == 1
  end

  test "same org/platform shares across projects while other organizations/platforms are independent" do
    a = spec()
    b = spec(%{project_id: "other-project", application_id: "other-app", build_id: "other-build"})
    c = spec(%{organization_id: "other-org"})
    d = spec(%{platform: :android})
    for s <- [a, b, c, d], do: assert({:ok, _} = create(s))
    for s <- [a, c, d], do: assert({:ok, _} = configure(capacity_scope(scope(s))))
    assert {:ok, _} = claim(scope(a))
    assert {:error, :claim, :capacity_exhausted, _} = claim(scope(b))
    assert {:ok, _} = claim(scope(c))
    assert {:ok, _} = claim(scope(d))
    assert Repo.aggregate(Reservation, :count) == 3
  end

  test "shrinking below occupancy or pausing preserves existing reconciliation ownership" do
    assert {:ok, _} = configure(capacity_scope(), :new, 2)
    assert {:ok, _} = create()
    other = spec(%{build_id: "second"})
    assert {:ok, _} = create(other)
    assert {:ok, %{claim: a}} = claim()
    assert {:ok, _} = claim(scope(other))
    assert {:ok, _} = configure(capacity_scope(), 0, 0)
    assert {:ok, %{claim: duplicate}} = claim()
    assert duplicate.token == a.token and duplicate.lease.expires_at == a.lease.expires_at
    expire_lease()
    assert {:ok, %{claim: taken}} = claim(scope(), "replacement")
    assert taken.token.epoch == a.token.epoch + 1
    assert Repo.aggregate(from(r in Reservation, where: r.held), :count) == 2
  end

  test "live duplicate claims never extend leases; renewal is explicit and exclusively fenced" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    assert {:ok, %{claim: same}} = claim(scope(), "coordinator-a", 300_000)
    assert same.outcome == :duplicate and same.lease.expires_at == a.lease.expires_at
    assert {:error, :claim, :lease_held, _} = claim(scope(), "coordinator-b")
    assert {:ok, %{renew: renewed}} = renew(a.token, 300_000)
    assert renewed.token == a.token
    assert DateTime.compare(renewed.lease.expires_at, a.lease.expires_at) == :gt
    assert {:error, :renew, :stale_lease, _} = renew(%{a.token | epoch: a.token.epoch + 1})
    assert {:error, :renew, :stale_lease, _} = renew(%{a.token | owner_id: "coordinator-b"})
  end

  test "expired claims advance epoch even for the same holder and stale tokens cannot revive" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    expire_lease()
    assert {:error, :renew, :stale_lease, _} = renew(a.token)
    assert {:ok, %{claim: b}} = claim()
    assert b.token.epoch == a.token.epoch + 1
    assert {:error, :renew, :stale_lease, _} = renew(a.token)
    expire_lease()
    assert {:ok, %{claim: c}} = claim(scope(), "coordinator-c")
    assert c.token.epoch == b.token.epoch + 1
  end

  test "renew samples the database clock after waiting for the capacity lock" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    parent = self()

    locker =
      Task.async(fn ->
        Repo.transaction(fn ->
          Repo.query!("SELECT * FROM mixer_build_capacities FOR UPDATE")
          send(parent, :locked)

          receive do
            :expire -> :ok
          end

          assert %{rows: [[true]]} =
                   Repo.query!(
                     "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) + interval '200 milliseconds' RETURNING expires_at > timezone('UTC', clock_timestamp())"
                   )

          Repo.query!("SELECT pg_sleep(0.3)")
        end)
      end)

    assert_receive :locked

    waiter =
      Task.async(fn ->
        Multi.new()
        |> Multi.run(:started, fn repo, _ ->
          repo.query!("SELECT 1")
          send(parent, :waiter_started)
          {:ok, :started}
        end)
        |> Admission.renew_multi(:renew, a.token, 60_000)
        |> Repo.transaction()
      end)

    assert_receive :waiter_started
    send(locker.pid, :expire)
    assert {:ok, _} = Task.await(locker)
    assert {:error, :renew, :stale_lease, _} = Task.await(waiter)
  end

  test "lease timeout and cancellation retain occupancy until matching definitive termination" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    {_started, ref} = start_claim(a)

    assert {:ok, %{build: cancelled}} =
             transition(a.token, 1, "cancel", %{type: :cancel, reason: "stop"})

    assert cancelled.build.state == :cancelling

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(a.token, "cancel")

    expire_lease()
    assert {:ok, %{claim: b}} = claim(scope(), "coordinator-b")
    assert b.build.state == :cancelling and b.reservation.held
    other = spec(%{build_id: "waiting"})
    assert {:ok, _} = create(other)
    assert {:error, :claim, :capacity_exhausted, _} = claim(scope(other))

    assert {:error, {:build, :admission}, :stale_lease, _} =
             transition(a.token, 2, "stopped", %{
               type: :stopped,
               ref: ref,
               diagnostic_sha256: String.duplicate("e", 64)
             })

    assert {:ok, %{build: stopped}} =
             transition(b.token, 2, "stopped", %{
               type: :stopped,
               ref: ref,
               diagnostic_sha256: String.duplicate("e", 64)
             })

    assert stopped.build.state == :cancelled
    assert {:ok, %{release: released}} = release(b.token, "stopped")
    refute released.reservation.held
    assert {:ok, _} = claim(scope(other))
  end

  test "lifecycle deadline expiry stays reconciling and consumes its slot" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create(spec(), %{policy() | timeout_ms: 1})
    assert {:ok, %{claim: a}} = claim()
    {_started, ref} = start_claim(a)
    Repo.query!("SELECT pg_sleep(0.01)")
    assert {:ok, %{build: expired}} = transition(a.token, 1, "expire", %{type: :expire, ref: ref})
    assert expired.build.state == :reconciling

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(a.token, "expire")

    assert Repo.one!(Reservation).held
    assert {:ok, _} = transition(a.token, 2, "complete", failed(ref))
    assert {:ok, _} = release(a.token, "complete")
  end

  test "claim, guarded start and Oban insert roll back as one transaction on a bad job" do
    assert {:ok, _} = configure()
    assert {:ok, %{created: original}} = create()

    multi =
      Admission.claim_multi(Multi.new(), :claim, scope(), "owner", 60_000)
      |> Multi.merge(fn %{claim: a} ->
        {:ok, ref} = Lifecycle.worker_ref(a.build)

        Admission.transition_multi(
          Multi.new(),
          :build,
          a.token,
          0,
          "start",
          %{type: :start, ref: ref},
          fn _ -> :invalid end
        )
      end)

    assert {:error, {:build, :job_changeset}, :invalid_job_changeset, _} = Repo.transaction(multi)
    assert Repo.aggregate(Reservation, :count) == 0 and Repo.aggregate(Lease, :count) == 0
    assert {:ok, %{record: record}} = Storage.read(scope())
    assert record.journal == original.record.journal and Repo.aggregate(Oban.Job, :count) == 1
  end

  test "renewal plus guarded CAS, cancel, completion and later failures roll back atomically" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    {started, ref} = start_claim(a)

    multi =
      Admission.renew_multi(Multi.new(), :renew, a.token, 300_000)
      |> Admission.transition_multi(
        :build,
        a.token,
        0,
        "cancel",
        %{type: :cancel, reason: "stop"},
        &job/1
      )

    assert {:error, :build, :stale_revision, _} = Repo.transaction(multi)
    assert Repo.one!(Lease).expires_at == a.lease.expires_at

    assert {:error, {:build, :job_changeset}, :invalid_job_changeset, _} =
             transition(a.token, 1, "cancel", %{type: :cancel, reason: "stop"}, fn _ ->
               :invalid
             end)

    assert {:error, {:build, :job_changeset}, :invalid_job_changeset, _} =
             transition(a.token, 1, "complete", failed(ref), fn _ -> :invalid end)

    assert {:ok, %{record: record}} = Storage.read(scope())
    assert record.journal == started.record.journal

    multi =
      Admission.transition_multi(Multi.new(), :build, a.token, 1, "complete", failed(ref), &job/1)
      |> Admission.release_multi(:release, a.token, "complete")
      |> Multi.run(:later, fn _, _ -> {:error, :forced} end)

    assert {:error, :later, :forced, _} = Repo.transaction(multi)
    assert Repo.one!(Reservation).held and Repo.one!(Lease).owner_id == "coordinator-a"
    assert {:ok, %{record: record}} = Storage.read(scope())
    assert record.journal == started.record.journal and Repo.aggregate(Oban.Job, :count) == 2
  end

  test "terminal held records can be reclaimed; release/retry never recycles an old lease epoch" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    {_started, ref} = start_claim(a)
    assert {:ok, _} = transition(a.token, 1, "complete", failed(ref))

    assert {:error, {:build, :admission}, :invalid_guarded_event, _} =
             transition(a.token, 2, "retry", %{type: :retry})

    expire_lease()
    assert {:ok, %{claim: b}} = claim(scope(), "replacement")
    assert b.build.state == :failed and b.reservation.held

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(b.token, "start")

    assert {:ok, %{release: released}} = release(b.token, "complete")
    assert released.lease.epoch == b.lease.epoch and released.lease.owner_id == nil
    assert {:error, :claim, :not_queued, _} = claim()
    assert {:error, :renew, :stale_lease, _} = renew(b.token)

    assert {:ok, _} =
             Storage.transition_multi(
               Multi.new(),
               :retry,
               scope(),
               2,
               "retry",
               %{type: :retry},
               now_ms(),
               &job/1
             )
             |> Repo.transaction()

    assert {:ok, %{claim: c}} = claim()
    assert c.token.attempt == 2 and c.token.epoch == b.token.epoch + 1
    assert {:error, :renew, :stale_lease, _} = renew(a.token)
    assert {:error, :release, :stale_lease, _} = release(b.token, "complete")

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(c.token, "complete")
  end

  test "only a replayed never-started queued cancellation can free its admitted slot" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    assert {:ok, _} = transition(a.token, 0, "cancel", %{type: :cancel, reason: "stop"})

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(a.token, "unknown")

    expire_lease()
    assert {:ok, %{claim: b}} = claim(scope(), "new-owner")
    assert b.build.state == :cancelled and b.reservation.held
    assert {:ok, %{release: released}} = release(b.token, "cancel")
    refute released.reservation.held
  end

  test "unknown and malformed scopes, policies and tokens fail closed" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()

    for key <- [:organization_id, :project_id, :application_id, :build_id, :platform] do
      bad = Map.put(scope(), key, if(key == :platform, do: :android, else: "unknown"))
      assert {:error, :claim, :scope_not_found_or_unconfigured, _} = claim(bad)
      assert {:error, :renew, _, _} = renew(%{a.token | scope: bad})
    end

    for s <- [Map.put(scope(), :role, :owner), Map.put(scope(), :platform, "ios"), %{}, nil] do
      assert {:error, :claim, :invalid_scope, _} = claim(s)
    end

    for ttl <- [0, -1, 300_001, "1000", nil] do
      assert {:error, :claim, :invalid_lease_policy, _} = claim(scope(), "owner", ttl)
      assert {:error, :renew, :invalid_lease_policy, _} = renew(a.token, ttl)
    end

    for token <- [
          %{},
          Map.from_struct(a.token),
          %{a.token | record_id: "bad"},
          %{a.token | attempt: 6}
        ] do
      assert {:error, :renew, :invalid_lease_token, _} = renew(token)
    end

    assert {:error, :renew, :stale_lease, _} = renew(%{a.token | record_id: Ecto.UUID.generate()})
  end

  test "journal/index and reservation attempt/fence corruption cannot be admitted or renewed" do
    assert {:ok, _} = configure()
    assert {:ok, %{created: original}} = create()
    assert {:ok, %{claim: a}} = claim()
    journal = put_in(original.record.journal, ["creation", "spec", "project_id"], "different")
    Repo.update_all(Record, set: [journal: journal])
    assert {:error, :claim, :invalid_journal, _} = claim()
    assert {:error, :renew, :invalid_journal, _} = renew(a.token)
    Repo.update_all(Record, set: [journal: original.record.journal])
    Repo.update_all(Reservation, set: [attempt: 2])
    assert {:error, :claim, :invalid_admission, _} = claim()
    assert {:error, :renew, :invalid_admission, _} = renew(a.token)
    Repo.update_all(Reservation, set: [attempt: 1, worker_fence: 99])
    assert {:error, :claim, :invalid_admission, _} = claim()
  end

  test "a wrong worker reference cannot complete or release the held reservation" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    {_started, ref} = start_claim(a)

    assert {:error, :build, :stale_worker_ref, _} =
             transition(a.token, 1, "wrong", failed(%{ref | fence: ref.fence + 1}))

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(a.token, "wrong")

    assert Repo.one!(Reservation).held
  end

  test "corrupt release evidence blocks readmission and exhausted epochs cannot wrap" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: a}} = claim()
    {_started, ref} = start_claim(a)
    assert {:ok, _} = transition(a.token, 1, "complete", failed(ref))
    assert {:ok, _} = release(a.token, "complete")

    assert {:ok, _} =
             Storage.transition_multi(
               Multi.new(),
               :retry,
               scope(),
               2,
               "retry",
               %{type: :retry},
               now_ms(),
               &job/1
             )
             |> Repo.transaction()

    Repo.update_all(Reservation, set: [terminal_event_id: "start"])
    assert {:error, :claim, :invalid_admission, _} = claim()
    Repo.update_all(Reservation, set: [terminal_event_id: "complete"])
    Repo.update_all(Lease, set: [epoch: 9_223_372_036_854_775_807])
    assert {:error, :claim, :lease_epoch_exhausted, _} = claim()
    refute Repo.one!(Reservation).held
    assert Repo.one!(Lease).epoch == 9_223_372_036_854_775_807
  end
end
