defmodule MixerHosted.AggregateAdmissionReview.Worker do
  use Oban.Worker, queue: :builds, max_attempts: 1
  @impl Oban.Worker
  def perform(_job), do: :ok
end

defmodule MixerHosted.AggregateAdmissionReview.Test do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.Repo
  alias MixerHosted.Builds.{Admission, Lifecycle, Record, Storage}
  alias MixerHosted.AggregateAdmissionReview.Worker

  alias Admission.{
    Capacity,
    FleetCapacity,
    FleetPlatformCapacity,
    OrganizationCapacity,
    Lease,
    Reservation
  }

  @moduletag :database
  @migration 20_261_025_000_002
  @tables [
    Record,
    Reservation,
    Lease,
    Capacity,
    FleetCapacity,
    FleetPlatformCapacity,
    OrganizationCapacity,
    Oban.Job
  ]

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_aggregate_admission_review_test",
       username: "mixer_fixture",
       pool_size: 12,
       ssl: false}
    )

    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")

    assert [20_261_024_000_000, 20_261_025_000_000, 20_261_025_000_001, @migration] ==
             Ecto.Migrator.run(Repo, path, :up, all: true)

    assert [] == Ecto.Migrator.run(Repo, path, :up, all: true)
    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    :ok
  end

  setup do
    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_build_capacities, mixer_build_organization_capacities, mixer_build_fleet_platform_capacities, mixer_build_fleet_capacity, mixer_builds, oban_jobs"
    )

    Repo.query!("INSERT INTO mixer_build_fleet_capacity (id) VALUES ('fleet')")

    Repo.query!(
      "INSERT INTO mixer_build_fleet_platform_capacities (platform) VALUES ('ios'), ('android')"
    )

    :ok
  end

  defp spec(id, org, platform) do
    %{
      organization_id: org,
      project_id: "project-#{id}",
      application_id: "app-#{id}",
      build_id: id,
      platform: platform,
      source: %{
        kind: :revision,
        sha256: String.duplicate("d", 64),
        reference: "independent/review@revision"
      },
      toolchain_lock_sha256: String.duplicate("e", 64),
      build_definition_sha256: String.duplicate("f", 64)
    }
  end

  defp scope(s),
    do: Map.take(s, [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp pair_scope(s), do: Map.take(s, [:organization_id, :platform])
  defp job(intent), do: Worker.new(intent)
  defp tx(multi), do: Repo.transaction(multi)

  defp create(s) do
    Storage.create_multi(
      Multi.new(),
      :created,
      s,
      %{max_attempts: 3, timeout_ms: 300_000, retry_backoff_ms: 0},
      "review-#{s.build_id}",
      1,
      &job/1
    )
    |> tx()
  end

  defp claim_multi(s, owner),
    do: Admission.claim_multi(Multi.new(), :claim, scope(s), owner, 60_000)

  defp claim(s, owner \\ "review-owner"), do: claim_multi(s, owner) |> tx()
  defp held, do: Repo.all(from(r in Reservation, where: r.held))

  defp snapshot,
    do: Enum.map(@tables, fn schema -> {schema, Repo.all(schema) |> Enum.sort_by(&inspect/1)} end)

  defp config(specs, limits \\ %{}) do
    limits = Map.merge(%{fleet: 20, platform: 20, organization: 20, pair: 20}, limits)
    multi = Admission.configure_fleet_multi(Multi.new(), :fleet, :new, limits.fleet)

    multi =
      Enum.reduce(Enum.uniq_by(specs, & &1.platform), multi, fn s, m ->
        Admission.configure_fleet_platform_multi(
          m,
          {:platform, s.platform},
          %{platform: s.platform},
          :new,
          limits.platform
        )
      end)

    multi =
      Enum.reduce(Enum.uniq_by(specs, & &1.organization_id), multi, fn s, m ->
        Admission.configure_organization_multi(
          m,
          {:org, s.organization_id},
          %{organization_id: s.organization_id},
          :new,
          limits.organization
        )
      end)

    Enum.reduce(Enum.uniq_by(specs, &{&1.organization_id, &1.platform}), multi, fn s, m ->
      Admission.configure_multi(
        m,
        {:pair, s.organization_id, s.platform},
        pair_scope(s),
        :new,
        limits.pair
      )
    end)
  end

  defp cancel_release(c) do
    Multi.new()
    |> Admission.transition_multi(
      :cancel,
      c.token,
      c.record.revision,
      "review-cancel",
      %{type: :cancel, reason: "independent review"},
      &job/1
    )
    |> Admission.release_multi(:release, c.token, "review-cancel")
  end

  # All synchronization is confirmed by server lock state, not a task launch delay.
  defp announced(multi, parent, tag) do
    Multi.run(Multi.new(), :review_backend, fn repo, _ ->
      %{rows: [[pid]]} = repo.query!("SELECT pg_backend_pid()")
      send(parent, {tag, pid})
      {:ok, pid}
    end)
    |> Multi.append(multi)
  end

  defp wait_for_mutex(pid, attempts \\ 200)

  defp wait_for_mutex(_pid, 0),
    do: flunk("backend did not wait on the specified two-int transaction advisory mutex")

  defp wait_for_mutex(pid, attempts) do
    %{rows: [[waiting]]} =
      Repo.query!(
        "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid = $1 AND locktype = 'advisory' AND classid = 1296648258 AND objid = 1 AND objsubid = 2 AND NOT granted)",
        [pid]
      )

    if waiting do
      :ok
    else
      Process.sleep(10)
      wait_for_mutex(pid, attempts - 1)
    end
  end

  defp assert_no_admission_relation_locks(pid) do
    %{rows: [[count]]} =
      Repo.query!(
        "SELECT count(*) FROM pg_locks l JOIN pg_class c ON c.oid = l.relation WHERE l.pid = $1 AND l.granted AND c.relname IN ('mixer_build_fleet_capacity', 'mixer_build_fleet_platform_capacities', 'mixer_build_organization_capacities', 'mixer_build_capacities', 'mixer_builds', 'mixer_build_reservations', 'mixer_build_coordinator_leases')",
        [pid]
      )

    assert count == 0
  end

  defp mutex_holder do
    parent = self()

    task =
      Task.async(fn ->
        Repo.transaction(fn ->
          Repo.query!("SELECT pg_advisory_xact_lock(1296648258, 1)")
          send(parent, :review_mutex_held)

          receive do
            :unlock -> :unlocked
          after
            8_000 -> Repo.rollback(:review_holder_timeout)
          end
        end)
      end)

    assert_receive :review_mutex_held, 2_000
    task
  end

  defp hold(multi, parent, tag) do
    Multi.run(multi, :review_hold, fn _, changes ->
      send(parent, {tag, changes})

      receive do
        :commit -> {:ok, :commit}
        :rollback -> {:error, :review_rollback}
      after
        8_000 -> {:error, :review_hold_timeout}
      end
    end)
  end

  defp contenders(specs) do
    parent = self()

    tasks =
      Enum.map(specs, fn s ->
        Task.async(fn ->
          send(parent, {:review_ready, self()})

          receive do
            :go -> {s, claim(s, "owner-#{s.build_id}")}
          after
            5_000 -> flunk("review contender was not released")
          end
        end)
      end)

    for _ <- tasks, do: assert_receive({:review_ready, _}, 2_000)
    Enum.each(tasks, &send(&1.pid, :go))
    Enum.map(tasks, &Task.await(&1, 15_000))
  end

  test "every valid Admission fragment waits on the fixed mutex before any admission relation lock" do
    a = spec("held", "org-a", :ios)
    b = spec("fresh", "org-b", :android)
    assert {:ok, _} = config([a, b]) |> tx()
    for s <- [a, b], do: assert({:ok, _} = create(s))
    assert {:ok, %{claim: c}} = claim(a)
    before = snapshot()

    operations = [
      Admission.configure_fleet_multi(Multi.new(), :operation, 0, 10),
      Admission.configure_fleet_platform_multi(Multi.new(), :operation, %{platform: :ios}, 0, 10),
      Admission.configure_organization_multi(
        Multi.new(),
        :operation,
        %{organization_id: "org-a"},
        0,
        10
      ),
      Admission.configure_multi(Multi.new(), :operation, pair_scope(a), 0, 10),
      claim_multi(a, "review-owner"),
      claim_multi(b, "fresh-owner"),
      Admission.renew_multi(Multi.new(), :operation, c.token, 60_000),
      Admission.yield_multi(Multi.new(), :operation, c.token),
      Admission.transition_multi(
        Multi.new(),
        :operation,
        c.token,
        0,
        "uncommitted-cancel",
        %{type: :cancel, reason: "review"},
        &job/1
      ),
      Admission.release_multi(Multi.new(), :operation, c.token, "missing-terminal-event"),
      Admission.retry_multi(Multi.new(), :operation, scope(a), 0, "retry-held", &job/1)
    ]

    for operation <- operations do
      locker = mutex_holder()
      parent = self()

      waiter =
        Task.async(fn ->
          operation
          |> announced(parent, :review_waiter)
          |> Multi.run(:review_abort, fn _, _ -> {:error, :review_rollback} end)
          |> tx()
        end)

      try do
        assert_receive {:review_waiter, pid}, 2_000
        wait_for_mutex(pid)
        assert_no_admission_relation_locks(pid)
        assert Task.yield(waiter, 0) == nil
      after
        send(locker.pid, :unlock)
      end

      assert {:ok, :unlocked} = Task.await(locker, 10_000)
      assert match?({:error, _, _, _}, Task.await(waiter, 10_000))
      assert snapshot() == before
    end
  end

  test "READ COMMITTED contender sees a reservation committed after its earlier count snapshot" do
    a = spec("first", "org-a", :ios)
    b = spec("second", "org-b", :android)
    assert {:ok, _} = config([a, b], %{fleet: 1}) |> tx()
    for s <- [a, b], do: assert({:ok, _} = create(s))
    parent = self()

    first =
      Task.async(fn -> claim_multi(a, "first") |> hold(parent, :review_first_claim) |> tx() end)

    assert_receive {:review_first_claim, %{claim: first_claim}}, 2_000
    assert held() == []

    second =
      Task.async(fn ->
        Multi.run(Multi.new(), :earlier_count, fn repo, _ ->
          %{rows: [[0, "read committed", pid]]} =
            repo.query!(
              "SELECT (SELECT count(*) FROM mixer_build_reservations WHERE held), current_setting('transaction_isolation'), pg_backend_pid()"
            )

          send(parent, {:review_second_pid, pid})
          {:ok, 0}
        end)
        |> Multi.append(claim_multi(b, "second"))
        |> tx()
      end)

    try do
      assert_receive {:review_second_pid, pid}, 2_000
      wait_for_mutex(pid)
    after
      send(first.pid, :commit)
    end

    assert {:ok, _} = Task.await(first, 10_000)

    assert {:error, :claim, :fleet_capacity_exhausted, %{earlier_count: 0}} =
             Task.await(second, 10_000)

    assert [r] = held()
    assert r.build_record_id == first_claim.record.id
    assert Repo.aggregate(Lease, :count) == 1
  end

  test "unsupported snapshots reject before waiting on the mutex and leave existing ownership unchanged" do
    a = spec("isolation", "org", :ios)
    assert {:ok, _} = config([a]) |> tx()
    assert {:ok, _} = create(a)
    assert {:ok, %{claim: c}} = claim(a)
    before = snapshot()

    for isolation <- ["REPEATABLE READ", "SERIALIZABLE", "READ UNCOMMITTED"] do
      locker = mutex_holder()

      waiter =
        Task.async(fn ->
          Multi.run(Multi.new(), :isolation, fn repo, _ ->
            repo.query!("SET TRANSACTION ISOLATION LEVEL " <> isolation)
            repo.query!("SELECT count(*) FROM mixer_build_reservations")
            {:ok, isolation}
          end)
          |> Admission.renew_multi(:renew, c.token, 60_000)
          |> tx()
        end)

      try do
        assert {:ok, {:error, :renew, :unsupported_admission_isolation, _}} =
                 Task.yield(waiter, 2_000)

        assert snapshot() == before
      after
        send(locker.pid, :unlock)
      end

      assert {:ok, :unlocked} = Task.await(locker, 10_000)
    end
  end

  test "a rolled back release does not expose its slot to a real waiting cross-platform contender" do
    a = spec("old", "org-a", :ios)
    b = spec("waiting", "org-b", :android)
    assert {:ok, _} = config([a, b], %{fleet: 1}) |> tx()
    for s <- [a, b], do: assert({:ok, _} = create(s))
    assert {:ok, %{claim: c}} = claim(a)
    before = snapshot()
    parent = self()
    releasing = Task.async(fn -> cancel_release(c) |> hold(parent, :review_released) |> tx() end)
    assert_receive {:review_released, %{release: %{outcome: :released}}}, 2_000

    waiting =
      Task.async(fn ->
        claim_multi(b, "waiting") |> announced(parent, :review_waiting_release) |> tx()
      end)

    try do
      assert_receive {:review_waiting_release, pid}, 2_000
      wait_for_mutex(pid)
      assert Enum.count(held()) == 1
    after
      send(releasing.pid, :rollback)
    end

    assert {:error, :review_hold, :review_rollback, _} = Task.await(releasing, 10_000)
    assert {:error, :claim, :fleet_capacity_exhausted, _} = Task.await(waiting, 10_000)
    assert snapshot() == before
    assert {:ok, %{claim: duplicate}} = claim(a)
    assert duplicate.token == c.token
  end

  test "release and another organization claim compose atomically at the single fleet slot" do
    a = spec("released", "org-a", :ios)
    b = spec("replacement", "org-b", :android)
    assert {:ok, _} = config([a, b], %{fleet: 1}) |> tx()
    for s <- [a, b], do: assert({:ok, _} = create(s))
    assert {:ok, %{claim: c}} = claim(a)

    assert {:ok, %{release: %{token: nil}, replacement: replacement}} =
             cancel_release(c)
             |> Admission.claim_multi(:replacement, scope(b), "replacement", 60_000)
             |> Admission.configure_fleet_multi(:shrink, 0, 0)
             |> tx()

    assert [r] = held()
    assert r.build_record_id == replacement.record.id
    assert {:ok, %{claim: duplicate}} = claim(b, "replacement")
    assert duplicate.token == replacement.token
    assert Repo.one!(FleetCapacity).limit == 0

    assert {:error, :renew, :stale_lease, _} =
             Admission.renew_multi(Multi.new(), :renew, c.token, 60_000) |> tx()

    assert Repo.aggregate(Oban.Job, :count) == 3
  end

  test "rolled back first activation leaves no phantom revision and a mutex waiter activates once" do
    actions = [
      fn -> Admission.configure_fleet_multi(Multi.new(), :config, :new, 3) end,
      fn ->
        Admission.configure_fleet_platform_multi(Multi.new(), :config, %{platform: :ios}, :new, 3)
      end,
      fn ->
        Admission.configure_organization_multi(
          Multi.new(),
          :config,
          %{organization_id: "new-org"},
          :new,
          3
        )
      end
    ]

    for action <- actions do
      parent = self()
      first = Task.async(fn -> action.() |> hold(parent, :review_activation) |> tx() end)

      assert_receive {:review_activation, %{config: %{revision: 0, limit: 3, configured: true}}},
                     2_000

      second =
        Task.async(fn -> action.() |> announced(parent, :review_activation_waiter) |> tx() end)

      try do
        assert_receive {:review_activation_waiter, pid}, 2_000
        wait_for_mutex(pid)
      after
        send(first.pid, :rollback)
      end

      assert {:error, :review_hold, :review_rollback, _} = Task.await(first, 10_000)

      assert {:ok, %{config: %{revision: 0, limit: 3, configured: true}}} =
               Task.await(second, 10_000)

      assert {:error, :config, :capacity_exists, _} = action.() |> tx()
    end
  end

  test "fresh admission remains closed for each absent policy and rejected claims leak no reservation or lease" do
    a = spec("closed", "org", :ios)
    assert {:ok, _} = create(a)
    assert {:error, :claim, :scope_not_found_or_unconfigured, _} = claim(a)

    assert {:ok, _} =
             Admission.configure_multi(Multi.new(), :pair, pair_scope(a), :new, 1) |> tx()

    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(a)
    assert {:ok, _} = Admission.configure_fleet_multi(Multi.new(), :fleet, :new, 1) |> tx()
    assert {:error, :claim, :fleet_platform_capacity_unconfigured, _} = claim(a)

    assert {:ok, _} =
             Admission.configure_fleet_platform_multi(
               Multi.new(),
               :platform,
               %{platform: :ios},
               :new,
               1
             )
             |> tx()

    assert {:error, :claim, :organization_capacity_unconfigured, _} = claim(a)

    assert {:ok, _} =
             Admission.configure_organization_multi(
               Multi.new(),
               :org,
               %{organization_id: "org"},
               :new,
               1
             )
             |> tx()

    assert Repo.aggregate(Reservation, :count) == 0
    assert Repo.aggregate(Lease, :count) == 0

    for {schema, error} <- [
          {FleetCapacity, :fleet_capacity_unconfigured},
          {FleetPlatformCapacity, :fleet_platform_capacity_unconfigured},
          {OrganizationCapacity, :organization_capacity_unconfigured}
        ] do
      # The SQL change is synthetic damage, not a supported production deletion API.
      previous = Repo.all(schema)
      Repo.delete_all(schema)
      assert {:error, :claim, ^error, _} = claim(a)

      for row <- previous do
        Repo.insert!(
          Ecto.Changeset.change(struct(schema), Map.from_struct(row) |> Map.delete(:__meta__))
        )
      end

      assert held() == []
      assert Repo.aggregate(Lease, :count) == 0
    end

    assert {:ok, _} = claim(a)
    assert length(held()) == 1
  end

  test "overlapping fleet platform organization and pair quotas hold across eighteen independent transactions" do
    specs =
      for org <- ["org-a", "org-b", "org-c"],
          p <- [:ios, :android],
          n <- 1..3,
          do: spec("#{org}-#{p}-#{n}", org, p)

    limits = %{fleet: 7, platform: 20, organization: 3, pair: 2}
    assert {:ok, _} = config(specs, limits) |> tx()

    assert {:ok, _} =
             Admission.configure_fleet_platform_multi(Multi.new(), :ios, %{platform: :ios}, 0, 4)
             |> tx()

    assert {:ok, _} =
             Admission.configure_fleet_platform_multi(
               Multi.new(),
               :android,
               %{platform: :android},
               0,
               3
             )
             |> tx()

    for s <- specs, do: assert({:ok, _} = create(s))
    results = contenders(specs)
    winners = for {s, {:ok, %{claim: c}}} <- results, do: {s, c}
    assert length(winners) == 7
    assert length(held()) == 7
    assert Enum.frequencies_by(held(), & &1.platform) == %{"ios" => 4, "android" => 3}
    assert Enum.all?(Enum.frequencies_by(held(), & &1.organization_id), fn {_, n} -> n <= 3 end)

    assert Enum.all?(Enum.frequencies_by(held(), &{&1.organization_id, &1.platform}), fn {_, n} ->
             n <= 2
           end)

    assert MapSet.new(Enum.map(held(), & &1.build_record_id)) ==
             MapSet.new(Enum.map(winners, fn {_, c} -> c.record.id end))

    for {s, c} <- winners do
      assert {:ok, %{claim: duplicate}} = claim(s, "owner-#{s.build_id}")
      assert duplicate.token == c.token
    end

    assert length(held()) == 7
    assert Repo.aggregate(Lease, :count) == 7
  end

  test "all-limit shrink and missing aggregate rows retain a started worker through fenced stop and release" do
    a = spec("uncertain", "org-a", :ios)
    b = spec("new", "org-b", :android)
    assert {:ok, _} = config([a, b], %{fleet: 1}) |> tx()
    for s <- [a, b], do: assert({:ok, _} = create(s))
    assert {:ok, %{claim: c}} = claim(a)
    assert {:ok, ref} = Lifecycle.worker_ref(c.build)

    assert {:ok, _} =
             Admission.transition_multi(
               Multi.new(),
               :start,
               c.token,
               0,
               "started",
               %{type: :start, ref: ref},
               &job/1
             )
             |> tx()

    assert {:ok, _} =
             Multi.new()
             |> Admission.configure_fleet_multi(:fleet, 0, 0)
             |> Admission.configure_fleet_platform_multi(:platform, %{platform: :ios}, 0, 0)
             |> Admission.configure_organization_multi(:org, %{organization_id: "org-a"}, 0, 0)
             |> Admission.configure_multi(:pair, pair_scope(a), 0, 0)
             |> Admission.transition_multi(
               :cancel,
               c.token,
               1,
               "cancel-started",
               %{type: :cancel, reason: "stop"},
               &job/1
             )
             |> Admission.yield_multi(:yield, c.token)
             |> tx()

    for schema <- [FleetCapacity, FleetPlatformCapacity, OrganizationCapacity],
        do: Repo.delete_all(schema)

    assert {:ok, %{claim: replacement}} = claim(a, "reconciler")
    assert replacement.token.epoch == c.token.epoch + 1
    assert replacement.build.active_ref == ref

    assert {:error, :release, :stale_lease, _} =
             Admission.release_multi(Multi.new(), :release, c.token, "cancel-started") |> tx()

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             Admission.release_multi(Multi.new(), :release, replacement.token, "cancel-started")
             |> tx()

    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(b)
    assert length(held()) == 1

    assert {:ok, _} =
             Admission.transition_multi(
               Multi.new(),
               :stop,
               replacement.token,
               2,
               "definitive-stop",
               %{type: :stopped, ref: ref, diagnostic_sha256: String.duplicate("a", 64)},
               &job/1
             )
             |> Admission.release_multi(:release, replacement.token, "definitive-stop")
             |> tx()

    assert held() == []
    assert Repo.one!(Reservation).worker_fence == ref.fence
    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(b)
  end

  test "migration rebuilds one closed organization placeholder per distinct pair owner without changing worker data" do
    a = spec("upgrade-held", "org-a", :ios)
    a2 = spec("upgrade-other-pool", "org-a", :android)
    b = spec("upgrade-released", "org-b", :ios)
    idle = spec("upgrade-no-build", "org-idle", :android)
    assert {:ok, _} = config([a, a2, b, idle]) |> tx()
    for s <- [a, b], do: assert({:ok, _} = create(s))
    assert {:ok, %{claim: c}} = claim(a)
    assert {:ok, ref} = Lifecycle.worker_ref(c.build)

    assert {:ok, _} =
             Admission.transition_multi(
               Multi.new(),
               :start,
               c.token,
               0,
               "upgrade-start",
               %{type: :start, ref: ref},
               &job/1
             )
             |> tx()

    assert {:ok, %{claim: released}} = claim(b)
    assert {:ok, _} = cancel_release(released) |> tx()
    retained = [Record, Reservation, Lease, Capacity, Oban.Job]
    before = Enum.map(retained, fn t -> Repo.all(t) |> Enum.sort_by(&inspect/1) end)
    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")
    assert [@migration] == Ecto.Migrator.run(Repo, path, :down, step: 1)
    assert [@migration] == Ecto.Migrator.run(Repo, path, :up, all: true)
    assert before == Enum.map(retained, fn t -> Repo.all(t) |> Enum.sort_by(&inspect/1) end)

    assert Enum.sort(Enum.map(Repo.all(OrganizationCapacity), & &1.organization_id)) == [
             "org-a",
             "org-b",
             "org-idle"
           ]

    for schema <- [FleetCapacity, FleetPlatformCapacity, OrganizationCapacity],
        row <- Repo.all(schema),
        do: assert(row.limit == 0 and row.revision == 0 and row.configured == false)

    assert length(held()) == 1
    assert {:ok, _} = Admission.yield_multi(Multi.new(), :yield, c.token) |> tx()
    assert {:ok, %{claim: reclaimed}} = claim(a, "after-migration")
    assert reclaimed.build.active_ref == ref
    assert reclaimed.token.epoch == c.token.epoch + 1
    assert reclaimed.reservation.worker_fence == c.reservation.worker_fence
    assert {:error, :claim, :not_queued, _} = claim(b)
  end

  test "organization and platform CAS conflicts roll back preceding cross-scope changes exactly" do
    a = spec("cas", "org-a", :ios)
    assert {:ok, _} = config([a]) |> tx()
    before = snapshot()

    assert {:error, :stale_org, :stale_capacity_revision, _} =
             Multi.new()
             |> Admission.configure_fleet_platform_multi(:platform, %{platform: :ios}, 0, 1)
             |> Admission.configure_fleet_multi(:fleet, 0, 1)
             |> Admission.configure_organization_multi(
               :stale_org,
               %{organization_id: "org-a"},
               1,
               1
             )
             |> tx()

    assert snapshot() == before

    assert {:error, :stale_platform, :stale_capacity_revision, _} =
             Multi.new()
             |> Admission.configure_organization_multi(:org, %{organization_id: "org-a"}, 0, 1)
             |> Admission.configure_multi(:pair, pair_scope(a), 0, 1)
             |> Admission.configure_fleet_platform_multi(:stale_platform, %{platform: :ios}, 1, 1)
             |> tx()

    assert snapshot() == before
  end
end
