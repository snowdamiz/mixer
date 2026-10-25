defmodule MixerHosted.Builds.AggregateAdmissionTest do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.{Repo, Test.BuildIntentWorker}
  alias MixerHosted.Builds.{Admission, Lifecycle, Record, Storage}

  alias Admission.{
    Capacity,
    FleetCapacity,
    FleetPlatformCapacity,
    OrganizationCapacity,
    Lease,
    Reservation
  }

  @moduletag :database
  @aggregate_migration 20_261_025_000_002
  @max_int 9_223_372_036_854_775_807

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_aggregate_admission_test",
       username: "mixer_fixture",
       pool_size: 10,
       ssl: false}
    )

    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")
    assert length(Ecto.Migrator.run(Repo, path, :up, all: true)) == 9
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

  defp spec(overrides \\ %{}),
    do:
      Map.merge(
        %{
          organization_id: "org-a",
          project_id: "project-a",
          application_id: "app-a",
          build_id: "build-a",
          platform: :ios,
          source: %{kind: :revision, sha256: String.duplicate("a", 64), reference: "repo@commit"},
          toolchain_lock_sha256: String.duplicate("b", 64),
          build_definition_sha256: String.duplicate("c", 64)
        },
        overrides
      )

  defp scope(s),
    do: Map.take(s, [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp job(intent), do: BuildIntentWorker.new(intent)
  defp transact(multi), do: Repo.transaction(multi)

  defp create(s) do
    Storage.create_multi(
      Multi.new(),
      :created,
      s,
      %{max_attempts: 3, timeout_ms: 100_000, retry_backoff_ms: 0},
      "request-#{s.build_id}",
      1,
      &job/1
    )
    |> transact()
  end

  defp fleet(limit, revision \\ :new),
    do: Admission.configure_fleet_multi(Multi.new(), :config, revision, limit) |> transact()

  defp platform(p, limit, revision \\ :new),
    do:
      Admission.configure_fleet_platform_multi(
        Multi.new(),
        :config,
        %{platform: p},
        revision,
        limit
      )
      |> transact()

  defp organization(id, limit, revision \\ :new),
    do:
      Admission.configure_organization_multi(
        Multi.new(),
        :config,
        %{organization_id: id},
        revision,
        limit
      )
      |> transact()

  defp pair(s, limit, revision \\ :new),
    do:
      Admission.configure_multi(
        Multi.new(),
        :config,
        Map.take(s, [:organization_id, :platform]),
        revision,
        limit
      )
      |> transact()

  defp configured_multi(specs, limits) do
    limits = Map.merge(%{fleet: 10, platform: 10, organization: 10, pair: 10}, limits)
    multi = Admission.configure_fleet_multi(Multi.new(), :fleet, :new, limits.fleet)

    multi =
      for p <- Enum.uniq(Enum.map(specs, & &1.platform)), reduce: multi do
        multi ->
          Admission.configure_fleet_platform_multi(
            multi,
            {:platform, p},
            %{platform: p},
            :new,
            limits.platform
          )
      end

    multi =
      for id <- Enum.uniq(Enum.map(specs, & &1.organization_id)), reduce: multi do
        multi ->
          Admission.configure_organization_multi(
            multi,
            {:organization, id},
            %{organization_id: id},
            :new,
            limits.organization
          )
      end

    for s <- Enum.uniq_by(specs, &{&1.organization_id, &1.platform}), reduce: multi do
      multi ->
        Admission.configure_multi(
          multi,
          {:pair, s.organization_id, s.platform},
          Map.take(s, [:organization_id, :platform]),
          :new,
          limits.pair
        )
    end
  end

  defp configure_all(specs, limits \\ %{}), do: configured_multi(specs, limits) |> transact()

  defp claim(s, owner \\ "owner"),
    do: Admission.claim_multi(Multi.new(), :claim, scope(s), owner, 60_000) |> transact()

  defp transition(c, revision, id, event),
    do:
      Admission.transition_multi(Multi.new(), :build, c.token, revision, id, event, &job/1)
      |> transact()

  defp release(c, id),
    do: Admission.release_multi(Multi.new(), :release, c.token, id) |> transact()

  defp expire_leases,
    do:
      Repo.query!(
        "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) - interval '1 second'"
      )

  defp held_count, do: Repo.aggregate(from(r in Reservation, where: r.held), :count)

  defp capacity_snapshot,
    do:
      Enum.map(
        [FleetCapacity, FleetPlatformCapacity, OrganizationCapacity, Capacity],
        &Repo.all/1
      )

  defp start(c) do
    {:ok, ref} = Lifecycle.worker_ref(c.build)
    assert {:ok, _} = transition(c, 0, "start", %{type: :start, ref: ref})
    ref
  end

  defp parallel_claims(specs) do
    parent = self()

    tasks =
      for s <- specs do
        Task.async(fn ->
          send(parent, {:ready, self()})

          receive do
            :go -> claim(s, "owner-#{s.build_id}")
          end
        end)
      end

    for _ <- specs, do: assert_receive({:ready, _}, 1_000)
    for task <- tasks, do: send(task.pid, :go)
    Enum.map(tasks, &Task.await(&1, 10_000))
  end

  test "all four explicit limits are mandatory and migration defaults close new claims" do
    assert %{limit: 0, revision: 0, configured: false} = Repo.one!(FleetCapacity)

    assert Enum.all?(Repo.all(FleetPlatformCapacity), fn c ->
             c.limit == 0 and c.revision == 0 and not c.configured
           end)

    s = spec()
    assert {:ok, _} = create(s)
    assert {:ok, _} = pair(s, 5)
    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(s)
    assert {:error, :config, :capacity_unconfigured, _} = fleet(5, 0)
    assert {:ok, _} = fleet(5)
    assert {:error, :claim, :fleet_platform_capacity_unconfigured, _} = claim(s)
    assert {:ok, _} = platform(:ios, 5)
    assert {:error, :claim, :organization_capacity_unconfigured, _} = claim(s)
    assert {:ok, _} = organization(s.organization_id, 0)
    assert {:error, :claim, :organization_capacity_exhausted, _} = claim(s)
    assert held_count() == 0 and Repo.aggregate(Lease, :count) == 0
    assert {:ok, _} = organization(s.organization_id, 5, 0)
    assert {:ok, _} = claim(s)
    assert held_count() == 1
  end

  test "fleet total admits exactly the last slot across organizations and platform pools" do
    specs =
      for n <- 1..8,
          do:
            spec(%{
              organization_id: "org-#{n}",
              build_id: "fleet-#{n}",
              platform: if(rem(n, 2) == 0, do: :ios, else: :android)
            })

    assert {:ok, _} = configure_all(specs, %{fleet: 1})
    for s <- specs, do: assert({:ok, _} = create(s))
    results = parallel_claims(specs)
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :claim, :fleet_capacity_exhausted, _}, &1)) == 7
    assert held_count() == 1 and Repo.aggregate(Lease, :count) == 1
  end

  test "organization total admits one cross-platform attempt while another organization proceeds" do
    specs =
      for n <- 1..6,
          do:
            spec(%{build_id: "org-#{n}", platform: if(rem(n, 2) == 0, do: :ios, else: :android)})

    other = spec(%{organization_id: "org-b", build_id: "other"})
    assert {:ok, _} = configure_all([other | specs], %{organization: 1})
    for s <- [other | specs], do: assert({:ok, _} = create(s))
    results = parallel_claims(specs)
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1

    assert Enum.count(results, &match?({:error, :claim, :organization_capacity_exhausted, _}, &1)) ==
             5

    assert {:ok, _} = claim(other)
    assert held_count() == 2
  end

  test "fleet platform last slot spans organizations while the distinct Android pool proceeds" do
    ios =
      for n <- 1..6,
          do: spec(%{organization_id: "org-#{n}", build_id: "ios-#{n}"})

    android = spec(%{organization_id: "org-1", build_id: "android", platform: :android})
    assert {:ok, _} = configure_all([android | ios], %{platform: 1})
    for s <- [android | ios], do: assert({:ok, _} = create(s))
    results = parallel_claims(ios)
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1

    assert Enum.count(
             results,
             &match?({:error, :claim, :fleet_platform_capacity_exhausted, _}, &1)
           ) == 5

    assert {:ok, _} = claim(android)
    assert held_count() == 2
  end

  test "zero at each aggregate level pauses new work without treating missing configuration as unlimited" do
    s = spec()
    assert {:ok, _} = configure_all([s])
    assert {:ok, _} = create(s)
    assert {:ok, _} = fleet(0, 0)
    assert {:error, :claim, :fleet_capacity_exhausted, _} = claim(s)
    assert {:ok, _} = fleet(10, 1)
    assert {:ok, _} = platform(:ios, 0, 0)
    assert {:error, :claim, :fleet_platform_capacity_exhausted, _} = claim(s)
    assert {:ok, _} = platform(:ios, 10, 1)
    assert {:ok, _} = organization(s.organization_id, 0, 0)
    assert {:error, :claim, :organization_capacity_exhausted, _} = claim(s)
    assert held_count() == 0
  end

  test "all policy APIs use bounded exact CAS and one-time activation" do
    s = spec()

    apis = [
      fn revision, limit -> fleet(limit, revision) end,
      fn revision, limit -> platform(:ios, limit, revision) end,
      fn revision, limit -> organization(s.organization_id, limit, revision) end,
      fn revision, limit -> pair(s, limit, revision) end
    ]

    for api <- apis do
      assert {:error, :config, :capacity_unconfigured, _} = api.(0, 5)
      assert {:ok, %{config: %{revision: 0, limit: 10_000}}} = api.(:new, 10_000)
      assert {:error, :config, :capacity_exists, _} = api.(:new, 1)
      assert {:ok, %{config: %{revision: 1, limit: 0}}} = api.(0, 0)
      assert {:error, :config, :stale_capacity_revision, _} = api.(0, 5)

      for invalid <- [-1, 10_001, 1.0, nil, "5"] do
        assert {:error, :config, :invalid_capacity_policy, _} = api.(1, invalid)
      end

      for invalid <- [-1, @max_int, 1.0, nil, "0", :initial] do
        assert {:error, :config, :invalid_capacity_policy, _} = api.(invalid, 5)
      end
    end

    before = capacity_snapshot()

    for bad <- [%{}, %{platform: "ios"}, %{platform: :other}, %{platform: :ios, extra: true}, nil] do
      assert {:error, :bad, :invalid_scope, _} =
               Admission.configure_fleet_platform_multi(Multi.new(), :bad, bad, :new, 1)
               |> transact()
    end

    for bad <- [%{}, %{organization_id: ""}, %{organization_id: "a", extra: true}, nil] do
      assert {:error, :bad, :invalid_scope, _} =
               Admission.configure_organization_multi(Multi.new(), :bad, bad, :new, 1)
               |> transact()
    end

    assert capacity_snapshot() == before
  end

  test "concurrent fleet configuration CAS has one winner" do
    assert {:ok, _} = fleet(1)
    parent = self()

    tasks =
      for limit <- 2..7 do
        Task.async(fn ->
          send(parent, {:ready, self()})

          receive do
            :go -> fleet(limit, 0)
          end
        end)
      end

    for _ <- tasks, do: assert_receive({:ready, _}, 1_000)
    for t <- tasks, do: send(t.pid, :go)
    results = Enum.map(tasks, &Task.await(&1, 10_000))
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :config, :stale_capacity_revision, _}, &1)) == 5
    assert Repo.one!(FleetCapacity).revision == 1
  end

  test "unsupported transaction snapshots fail closed before configuration or held mutation" do
    s = spec()
    assert {:ok, _} = configure_all([s])
    assert {:ok, _} = create(s)
    assert {:ok, %{claim: c}} = claim(s)
    before = {capacity_snapshot(), Repo.one!(Reservation), Repo.one!(Lease)}

    for isolation <- ["REPEATABLE READ", "SERIALIZABLE", "READ UNCOMMITTED"] do
      prefix =
        Multi.run(Multi.new(), :isolation, fn repo, _ ->
          repo.query!("SET TRANSACTION ISOLATION LEVEL " <> isolation)
          {:ok, isolation}
        end)

      assert {:error, :claim, :unsupported_admission_isolation, _} =
               Admission.claim_multi(prefix, :claim, scope(s), "owner", 60_000) |> transact()

      assert {:error, :fleet, :unsupported_admission_isolation, _} =
               Admission.configure_fleet_multi(prefix, :fleet, 0, 0) |> transact()

      assert {:error, :pair, :unsupported_admission_isolation, _} =
               Admission.configure_multi(
                 prefix,
                 :pair,
                 Map.take(s, [:organization_id, :platform]),
                 0,
                 0
               )
               |> transact()

      assert {:error, :renew, :unsupported_admission_isolation, _} =
               Admission.renew_multi(prefix, :renew, c.token, 60_000) |> transact()
    end

    assert {capacity_snapshot(), Repo.one!(Reservation), Repo.one!(Lease)} == before
  end

  test "lowering all limits below held occupancy preserves uncertain workers and exact release" do
    s = spec()
    waiting = spec(%{build_id: "waiting", organization_id: "org-b", platform: :android})
    assert {:ok, _} = configure_all([s, waiting], %{fleet: 1})
    for value <- [s, waiting], do: assert({:ok, _} = create(value))
    assert {:ok, %{claim: a}} = claim(s)
    ref = start(a)
    assert {:ok, _} = transition(a, 1, "cancel", %{type: :cancel, reason: "stop"})
    assert {:ok, _} = fleet(0, 0)
    assert {:ok, _} = platform(:ios, 0, 0)
    assert {:ok, _} = organization(s.organization_id, 0, 0)
    assert {:ok, _} = pair(s, 0, 0)
    assert {:ok, %{claim: duplicate}} = claim(s)
    assert duplicate.token == a.token and duplicate.lease.expires_at == a.lease.expires_at
    assert {:ok, _} = Admission.renew_multi(Multi.new(), :renew, a.token, 60_000) |> transact()
    assert {:error, :release, :definitive_terminal_evidence_required, _} = release(a, "cancel")
    expire_leases()
    assert {:ok, %{claim: b}} = claim(s, "replacement")
    assert b.token.epoch == a.token.epoch + 1
    assert b.build.state == :cancelling and b.build.active_ref == ref and held_count() == 1
    assert {:error, :claim, :fleet_capacity_exhausted, _} = claim(waiting)
    assert {:error, :release, :stale_lease, _} = release(a, "stopped")

    assert {:ok, _} =
             transition(b, 2, "stopped", %{
               type: :stopped,
               ref: ref,
               diagnostic_sha256: String.duplicate("e", 64)
             })

    assert {:ok, _} = release(b, "stopped")
    assert held_count() == 0
    assert {:error, :claim, :fleet_capacity_exhausted, _} = claim(waiting)
    assert {:ok, _} = fleet(1, 1)
    assert {:ok, _} = claim(waiting)
    assert held_count() == 1
  end

  test "missing aggregate parent rows cannot prevent held reconciliation or manufacture another slot" do
    s = spec()
    waiting = spec(%{build_id: "waiting"})
    assert {:ok, _} = configure_all([s, waiting])
    for value <- [s, waiting], do: assert({:ok, _} = create(value))
    assert {:ok, %{claim: a}} = claim(s)
    ref = start(a)

    for schema <- [FleetCapacity, FleetPlatformCapacity, OrganizationCapacity],
        do: Repo.delete_all(schema)

    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(waiting)
    assert {:ok, _} = Admission.renew_multi(Multi.new(), :renew, a.token, 60_000) |> transact()
    assert {:ok, _} = Admission.yield_multi(Multi.new(), :yield, a.token) |> transact()
    assert {:ok, %{claim: b}} = claim(s, "new-owner")
    assert b.token.epoch == a.token.epoch + 1 and held_count() == 1

    assert {:ok, _} =
             transition(b, 1, "complete", %{
               type: :completed,
               ref: ref,
               result: %{
                 outcome: :failed,
                 class: :infrastructure,
                 code: :worker_lost,
                 diagnostic_sha256: String.duplicate("d", 64)
               }
             })

    assert {:ok, _} = release(b, "complete")
    assert held_count() == 0

    assert {:ok, _} =
             Admission.retry_multi(Multi.new(), :retry, scope(s), 2, "retry", &job/1)
             |> transact()

    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(s)
    assert Repo.one!(Reservation).attempt == 1
  end

  test "migration down and up preserves an existing held worker and closes only new admission" do
    s = spec()
    waiting = spec(%{build_id: "upgrade-waiting"})
    assert {:ok, _} = configure_all([s, waiting])
    for value <- [s, waiting], do: assert({:ok, _} = create(value))
    assert {:ok, %{claim: a}} = claim(s)
    ref = start(a)
    assert {:ok, _} = transition(a, 1, "cancel", %{type: :cancel, reason: "stop"})
    before = {Repo.one!(Reservation), Repo.one!(Lease), Repo.get!(Record, a.record.id)}
    path = Application.app_dir(:mixer_hosted, "priv/repo/migrations")

    assert [
             20_261_025_000_007,
             20_261_025_000_006,
             20_261_025_000_005,
             20_261_025_000_004,
             20_261_025_000_003,
             @aggregate_migration
           ] = Ecto.Migrator.run(Repo, path, :down, step: 6)

    assert %{rows: [[nil]]} =
             Repo.query!("SELECT to_regclass('public.mixer_build_fleet_capacity')::text")

    assert {Repo.one!(Reservation), Repo.one!(Lease), Repo.get!(Record, a.record.id)} == before

    assert [
             @aggregate_migration,
             20_261_025_000_003,
             20_261_025_000_004,
             20_261_025_000_005,
             20_261_025_000_006,
             20_261_025_000_007
           ] = Ecto.Migrator.run(Repo, path, :up, all: true)

    assert {Repo.one!(Reservation), Repo.one!(Lease), Repo.get!(Record, a.record.id)} == before
    assert %{configured: false, limit: 0, revision: 0} = Repo.one!(FleetCapacity)
    assert %{configured: false, limit: 0, revision: 0} = Repo.one!(OrganizationCapacity)
    assert {:error, :claim, :fleet_capacity_unconfigured, _} = claim(waiting)
    expire_leases()
    assert {:ok, %{claim: b}} = claim(s, "after-upgrade")
    assert b.build.active_ref == ref and held_count() == 1

    assert {:ok, _} =
             transition(b, 2, "stop-after-upgrade", %{
               type: :stopped,
               ref: ref,
               diagnostic_sha256: String.duplicate("e", 64)
             })

    assert {:ok, _} = release(b, "stop-after-upgrade")
    assert held_count() == 0
    assert {:ok, _} = fleet(1)
    assert {:ok, _} = platform(:ios, 1)
    assert {:ok, _} = organization(s.organization_id, 1)
    assert {:ok, _} = claim(waiting)
  end

  test "first configuration from completely missing parents serializes a waiting fresh claim" do
    s = spec()
    assert {:ok, _} = create(s)
    for schema <- [FleetCapacity, FleetPlatformCapacity], do: Repo.delete_all(schema)
    assert {:error, :claim, :scope_not_found_or_unconfigured, _} = claim(s)
    parent = self()

    configurator =
      Task.async(fn ->
        configured_multi([s], %{fleet: 1, platform: 1, organization: 1, pair: 1})
        |> Multi.run(:hold, fn _, _ ->
          send(parent, :configuration_locked)

          receive do
            :commit -> {:ok, :committed}
          end
        end)
        |> transact()
      end)

    assert_receive :configuration_locked

    waiter =
      Task.async(fn ->
        Multi.new()
        |> Multi.run(:began, fn repo, _ ->
          repo.query!("SELECT 1")
          send(parent, :claim_began)
          {:ok, :began}
        end)
        |> Admission.claim_multi(:claim, scope(s), "waiter", 60_000)
        |> Multi.run(:admitted, fn _, _ ->
          send(parent, :claim_admitted)
          {:ok, :admitted}
        end)
        |> transact()
      end)

    assert_receive :claim_began
    refute_receive :claim_admitted, 100
    send(configurator.pid, :commit)
    assert {:ok, _} = Task.await(configurator)
    assert {:ok, _} = Task.await(waiter)
    assert_receive :claim_admitted
    assert held_count() == 1
    assert Repo.one!(FleetCapacity).configured
  end

  test "recreating deleted parents counts existing workers before admitting a waiting organization" do
    a = spec()
    b = spec(%{organization_id: "org-b", build_id: "waiting", platform: :android})
    assert {:ok, _} = configure_all([a, b])
    for s <- [a, b], do: assert({:ok, _} = create(s))
    assert {:ok, %{claim: held}} = claim(a, "owner-#{a.build_id}")

    for schema <- [FleetCapacity, FleetPlatformCapacity, OrganizationCapacity],
        do: Repo.delete_all(schema)

    assert {:ok, _} =
             Multi.new()
             |> Admission.configure_fleet_multi(:fleet, :new, 1)
             |> Admission.configure_fleet_platform_multi(:ios, %{platform: :ios}, :new, 1)
             |> Admission.configure_fleet_platform_multi(:android, %{platform: :android}, :new, 1)
             |> Admission.configure_organization_multi(:a, %{organization_id: "org-a"}, :new, 1)
             |> Admission.configure_organization_multi(:b, %{organization_id: "org-b"}, :new, 1)
             |> transact()

    results = parallel_claims([a, b])
    assert [{:ok, %{claim: duplicate}}, {:error, :claim, :fleet_capacity_exhausted, _}] = results
    assert duplicate.token == held.token and held_count() == 1
  end

  test "configuration and claim in one Multi roll back every limit and occupancy on later failure" do
    s = spec()
    assert {:ok, _} = create(s)
    before = capacity_snapshot()

    assert {:error, :later, :forced, _} =
             configured_multi([s], %{fleet: 1, platform: 1, organization: 1, pair: 1})
             |> Admission.claim_multi(:claim, scope(s), "owner", 60_000)
             |> Multi.run(:later, fn _, _ -> {:error, :forced} end)
             |> transact()

    assert capacity_snapshot() == before
    assert held_count() == 0 and Repo.aggregate(Lease, :count) == 0
    assert {:ok, _} = configure_all([s], %{fleet: 1, platform: 1, organization: 1, pair: 1})
    assert {:ok, _} = claim(s)
  end

  test "configuration CAS failure rolls preceding aggregate changes back" do
    s = spec()
    assert {:ok, _} = configure_all([s])
    before = capacity_snapshot()

    assert {:error, :pair, :stale_capacity_revision, _} =
             Multi.new()
             |> Admission.configure_fleet_multi(:fleet, 0, 0)
             |> Admission.configure_fleet_platform_multi(:platform, %{platform: :ios}, 0, 0)
             |> Admission.configure_organization_multi(:org, %{organization_id: "org-a"}, 0, 0)
             |> Admission.configure_multi(:pair, Map.take(s, [:organization_id, :platform]), 1, 0)
             |> transact()

    assert capacity_snapshot() == before
  end

  test "claim and lifecycle insert failure returns the same last slot without changing limits" do
    s = spec()
    assert {:ok, _} = configure_all([s], %{fleet: 1, platform: 1, organization: 1, pair: 1})
    assert {:ok, %{created: original}} = create(s)
    before = capacity_snapshot()

    multi =
      Admission.claim_multi(Multi.new(), :claim, scope(s), "owner", 60_000)
      |> Multi.merge(fn %{claim: c} ->
        {:ok, ref} = Lifecycle.worker_ref(c.build)

        Admission.transition_multi(
          Multi.new(),
          :start,
          c.token,
          0,
          "start",
          %{type: :start, ref: ref},
          fn _ -> :invalid end
        )
      end)

    assert {:error, {:start, :job_changeset}, :invalid_job_changeset, _} = transact(multi)
    assert capacity_snapshot() == before
    assert Repo.get!(Record, original.record.id) == original.record
    assert held_count() == 0 and Repo.aggregate(Lease, :count) == 0
    assert Repo.aggregate(Oban.Job, :count) == 1
    assert {:ok, _} = claim(s)
  end

  test "guarded terminal release and all-limit shrink roll back together after a later failure" do
    s = spec()
    assert {:ok, _} = configure_all([s], %{fleet: 1, platform: 1, organization: 1, pair: 1})
    assert {:ok, _} = create(s)
    assert {:ok, %{claim: c}} = claim(s)
    before = {capacity_snapshot(), Repo.one!(Reservation), Repo.one!(Lease), Repo.one!(Record)}

    assert {:error, :later, :forced, _} =
             Multi.new()
             |> Admission.transition_multi(
               :cancel,
               c.token,
               0,
               "cancel",
               %{type: :cancel, reason: "stop"},
               &job/1
             )
             |> Admission.release_multi(:release, c.token, "cancel")
             |> Admission.configure_fleet_multi(:fleet, 0, 0)
             |> Admission.configure_fleet_platform_multi(:platform, %{platform: :ios}, 0, 0)
             |> Admission.configure_organization_multi(:org, %{organization_id: "org-a"}, 0, 0)
             |> Admission.configure_multi(:pair, Map.take(s, [:organization_id, :platform]), 0, 0)
             |> Multi.run(:later, fn _, _ -> {:error, :forced} end)
             |> transact()

    assert {capacity_snapshot(), Repo.one!(Reservation), Repo.one!(Lease), Repo.one!(Record)} ==
             before

    assert held_count() == 1 and Repo.aggregate(Oban.Job, :count) == 1
  end

  test "opposite configuration fragment orders after claims cannot deadlock" do
    a = spec()
    b = spec(%{organization_id: "org-b", build_id: "other", platform: :android})
    assert {:ok, _} = configure_all([a, b])
    for s <- [a, b], do: assert({:ok, _} = create(s))
    parent = self()

    tasks =
      for {s, other} <- [{a, b}, {b, a}] do
        Task.async(fn ->
          send(parent, {:ready, self()})

          receive do
            :go -> :ok
          end

          Admission.claim_multi(Multi.new(), :claim, scope(s), "owner", 60_000)
          |> Admission.configure_multi(
            :other_pair,
            Map.take(other, [:organization_id, :platform]),
            0,
            5
          )
          |> Admission.configure_organization_multi(
            :other_org,
            %{organization_id: other.organization_id},
            0,
            5
          )
          |> transact()
        end)
      end

    for _ <- tasks, do: assert_receive({:ready, _}, 1_000)
    for t <- tasks, do: send(t.pid, :go)
    for t <- tasks, do: assert({:ok, _} = Task.await(t, 10_000))
    assert held_count() == 2
  end

  test "database lease clock advances while waiting for the fleet row lock" do
    s = spec()
    assert {:ok, _} = configure_all([s])
    assert {:ok, _} = create(s)
    assert {:ok, %{claim: c}} = claim(s)
    parent = self()

    locker =
      Task.async(fn ->
        Repo.transaction(fn ->
          Repo.query!("SELECT * FROM mixer_build_fleet_capacity FOR UPDATE")
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
        |> Multi.run(:began, fn repo, _ ->
          repo.query!("SELECT 1")
          send(parent, :waiter_began)
          {:ok, :began}
        end)
        |> Admission.renew_multi(:renew, c.token, 60_000)
        |> transact()
      end)

    assert_receive :waiter_began
    send(locker.pid, :expire)
    assert {:ok, _} = Task.await(locker)
    assert {:error, :renew, :stale_lease, _} = Task.await(waiter)
    assert held_count() == 1
  end

  test "migration enforces aggregate identities, closed defaults, integer bounds and CAS exhaustion" do
    invalid = [
      "INSERT INTO mixer_build_fleet_capacity (id) VALUES ('other')",
      "INSERT INTO mixer_build_fleet_platform_capacities (platform) VALUES ('other')",
      "INSERT INTO mixer_build_organization_capacities (organization_id) VALUES ('')",
      "INSERT INTO mixer_build_organization_capacities (organization_id) VALUES (repeat('a', 129))",
      "UPDATE mixer_build_fleet_capacity SET \"limit\" = -1, configured = true",
      "UPDATE mixer_build_fleet_capacity SET \"limit\" = 10001, configured = true",
      "UPDATE mixer_build_fleet_capacity SET revision = -1",
      "UPDATE mixer_build_fleet_capacity SET \"limit\" = 1",
      "UPDATE mixer_build_fleet_capacity SET revision = 1",
      "UPDATE mixer_build_fleet_capacity SET configured = NULL",
      "UPDATE mixer_build_fleet_platform_capacities SET \"limit\" = 10001, configured = true",
      "INSERT INTO mixer_build_organization_capacities (organization_id, \"limit\", configured) VALUES ('bad', 10001, true)"
    ]

    for sql <- invalid do
      assert {:error, %Postgrex.Error{postgres: %{code: code}}} = Repo.query(sql)
      assert code in [:check_violation, :not_null_violation]
    end

    assert {:ok, _} = fleet(1)
    Repo.query!("UPDATE mixer_build_fleet_capacity SET revision = $1", [@max_int - 1])
    assert {:ok, %{config: %{revision: @max_int}}} = fleet(0, @max_int - 1)
    assert {:error, :config, :invalid_capacity_policy, _} = fleet(1, @max_int)
    assert Repo.one!(FleetCapacity).revision == @max_int

    assert {:error, %Postgrex.Error{postgres: %{code: :numeric_value_out_of_range}}} =
             Repo.query("UPDATE mixer_build_fleet_capacity SET revision = revision + 1")
  end
end
