defmodule MixerHosted.BuildAdmissionReview.Worker do
  use Oban.Worker, queue: :builds, max_attempts: 1
  @impl true
  def perform(_job), do: :ok
end

defmodule MixerHosted.BuildAdmissionReview.Test do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.{Repo, BuildAdmissionReview.Worker}
  alias MixerHosted.Builds.{Admission, Lifecycle, Storage}
  alias MixerHosted.Builds.Admission.{Capacity, Lease, Reservation}
  @moduletag :database

  setup_all do
    start_supervised!(
      {Repo,
       hostname: "127.0.0.1",
       port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
       database: "mixer_admission_review_test",
       username: "mixer_fixture",
       pool_size: 8,
       ssl: false}
    )

    Ecto.Migrator.run(Repo, Application.app_dir(:mixer_hosted, "priv/repo/migrations"), :up,
      all: true
    )

    start_supervised!({Oban, repo: Repo, queues: false, plugins: false, testing: :manual})
    :ok
  end

  setup do
    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_builds, mixer_build_capacities, oban_jobs"
    )

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

  defp scope(s),
    do: Map.take(s, [:organization_id, :project_id, :application_id, :build_id, :platform])

  defp cap_scope(s), do: Map.take(s, [:organization_id, :platform])
  defp job(intent), do: Worker.new(intent)
  defp run(multi), do: Repo.transaction(multi)
  defp data(row), do: row |> Map.from_struct() |> Map.delete(:__meta__)

  defp configure(s \\ spec(), limit \\ 1, revision \\ :new) do
    Admission.configure_multi(Multi.new(), :capacity, cap_scope(s), revision, limit) |> run()
  end

  defp create(s \\ spec(), policy \\ %{max_attempts: 3, timeout_ms: 60_000, retry_backoff_ms: 0}) do
    Storage.create_multi(Multi.new(), :decision, s, policy, "request-" <> s.build_id, 1, &job/1)
    |> run()
  end

  defp claim(s \\ spec(), owner \\ "owner-one", ttl \\ 60_000) do
    Admission.claim_multi(Multi.new(), :claim, scope(s), owner, ttl) |> run()
  end

  defp renew(token, ttl \\ 60_000),
    do: Admission.renew_multi(Multi.new(), :renew, token, ttl) |> run()

  defp release(token, id), do: Admission.release_multi(Multi.new(), :release, token, id) |> run()

  defp event(token, revision, id, payload, factory \\ &job/1) do
    Admission.transition_multi(Multi.new(), :decision, token, revision, id, payload, factory)
    |> run()
  end

  defp start(token, build, id \\ "start") do
    {:ok, ref} = Lifecycle.worker_ref(build)
    assert {:ok, %{decision: decision}} = event(token, 0, id, %{type: :start, ref: ref})
    {decision, ref}
  end

  defp stopped(ref), do: %{type: :stopped, ref: ref, diagnostic_sha256: String.duplicate("d", 64)}
  defp jobs, do: Repo.aggregate(Oban.Job, :count)
  defp held, do: Repo.aggregate(from(r in Reservation, where: r.held), :count)

  defp expire_lease(id) do
    Repo.query!(
      "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) - interval '1 second' WHERE build_record_id = $1",
      [Ecto.UUID.dump!(id)]
    )
  end

  defp race(operations) do
    owner = self()

    tasks =
      Enum.map(operations, fn operation ->
        Task.async(fn ->
          send(owner, {:ready, self()})

          receive do
            :go -> operation.()
          end
        end)
      end)

    for _ <- tasks, do: assert_receive({:ready, _}, 2_000)
    for task <- tasks, do: send(task.pid, :go)
    Enum.map(tasks, &Task.await(&1, 10_000))
  end

  test "one shared organization/platform slot wins across concurrent project and application scopes" do
    second =
      spec(%{project_id: "other-project", application_id: "other-app", build_id: "other-build"})

    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, _} = create(second)
    results = race([fn -> claim() end, fn -> claim(second, "owner-two") end])
    assert Enum.count(results, &match?({:ok, _}, &1)) == 1
    assert Enum.count(results, &match?({:error, :claim, :capacity_exhausted, _}, &1)) == 1
    assert held() == 1
    assert Repo.aggregate(Lease, :count) == 1
    assert jobs() == 2

    for s <- [spec(%{platform: :android}), spec(%{organization_id: "other-org"})] do
      assert {:ok, _} = configure(s)
      assert {:ok, _} = create(s)
      assert {:ok, _} = claim(s)
    end

    assert held() == 3
  end

  test "shrinking capacity never evicts held work and stale capacity CAS cannot increase it" do
    second = spec(%{build_id: "second"})
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, _} = create(second)
    assert {:ok, %{claim: first}} = claim()
    assert {:ok, %{capacity: %Capacity{revision: 1, limit: 0}}} = configure(spec(), 0, 0)
    assert {:error, :capacity, :stale_capacity_revision, _} = configure(spec(), 100, 0)
    assert {:ok, %{claim: duplicate}} = claim()
    assert duplicate.token == first.token and data(duplicate.lease) == data(first.lease)
    assert {:error, :claim, :capacity_exhausted, _} = claim(second)
    assert held() == 1
  end

  test "expired ownership transfers fence old tokens while retaining one active execution reservation" do
    assert {:ok, _} = configure()
    assert {:ok, %{decision: created}} = create()
    assert {:ok, %{claim: first}} = claim()
    {_running, ref} = start(first.token, created.build)
    assert {:error, :claim, :lease_held, _} = claim(spec(), "owner-two")
    expire_lease(first.record.id)
    assert {:error, :renew, :stale_lease, _} = renew(first.token)

    assert {:error, {:decision, :admission}, :stale_lease, _} =
             event(first.token, 0, "start", %{type: :start, ref: ref})

    assert {:ok, %{claim: second}} = claim(spec(), "owner-two")
    assert second.token.epoch == first.token.epoch + 1
    assert data(second.reservation) == data(first.reservation) and second.build.active_ref == ref
    assert held() == 1 and Repo.aggregate(Lease, :count) == 1
    assert {:error, :renew, :stale_lease, _} = renew(first.token)
    assert {:ok, %{renew: renewed}} = renew(second.token)
    assert renewed.token == second.token
  end

  test "guard rechecks expiry with database time after a real capacity row lock wait" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: claimed}} = claim()
    owner = self()

    {:ok, {task, proof}} =
      Repo.transaction(fn ->
        Repo.query!(
          "SELECT organization_id FROM mixer_build_capacities WHERE organization_id = $1 AND platform = 'ios' FOR UPDATE",
          [spec().organization_id]
        )

        Repo.query!(
          "UPDATE mixer_build_coordinator_leases SET expires_at = timezone('UTC', clock_timestamp()) + interval '200 milliseconds' WHERE build_record_id = $1",
          [Ecto.UUID.dump!(claimed.record.id)]
        )

        fixture_expiry_ms = Repo.one!(Lease).expires_at |> DateTime.to_unix(:millisecond)

        task =
          Task.async(fn ->
            Multi.new()
            |> Multi.run(:begun, fn _, _ ->
              %{rows: [[at]]} =
                Repo.query!("SELECT floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint")

              send(owner, {:begun, self(), at})
              {:ok, :begun}
            end)
            |> Admission.renew_multi(:renew, claimed.token, 60_000)
            |> run()
          end)

        assert_receive {:begun, _, transaction_begun_ms}, 2_000
        assert transaction_begun_ms < fixture_expiry_ms
        Repo.query!("SELECT pg_sleep(0.35)")

        %{rows: [[before_unlock_ms]]} =
          Repo.query!("SELECT floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint")

        assert before_unlock_ms > fixture_expiry_ms

        {task,
         %{
           transaction_begun_ms: transaction_begun_ms,
           fixture_expiry_ms: fixture_expiry_ms,
           before_unlock_ms: before_unlock_ms
         }}
      end)

    assert {:error, :renew, :stale_lease, _} = Task.await(task, 10_000)
    IO.inspect(proof, label: "independent_post_lock_expiry_proof")
    assert held() == 1
  end

  test "claim starts its TTL after lock acquisition rather than transaction start" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    owner = self()

    {:ok, {task, before_unlock_ms}} =
      Repo.transaction(fn ->
        Repo.query!(
          "SELECT organization_id FROM mixer_build_capacities WHERE organization_id = $1 AND platform = 'ios' FOR UPDATE",
          [spec().organization_id]
        )

        task =
          Task.async(fn ->
            Multi.new()
            |> Multi.run(:begun, fn _, _ ->
              send(owner, {:begun, self()})
              {:ok, :begun}
            end)
            |> Admission.claim_multi(:claim, scope(spec()), "post-lock", 10_000)
            |> run()
          end)

        assert_receive {:begun, _}, 2_000
        Repo.query!("SELECT pg_sleep(0.1)")

        %{rows: [[at]]} =
          Repo.query!("SELECT floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint")

        {task, at}
      end)

    assert {:ok, %{claim: claimed}} = Task.await(task, 10_000)
    assert claimed.now_ms >= before_unlock_ms
    assert DateTime.to_unix(claimed.lease.expires_at, :millisecond) == claimed.now_ms + 10_000
  end

  test "every token binding and closed shape is checked before any guarded mutation" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: claimed}} = claim()
    token = claimed.token

    invalid = [
      %{token | record_id: Ecto.UUID.generate()},
      %{token | attempt: token.attempt + 1},
      %{token | owner_id: "other-owner"},
      %{token | epoch: token.epoch + 1},
      %{token | scope: %{token.scope | project_id: "other-project"}},
      %{token | scope: %{token.scope | platform: "ios"}},
      Map.put(token, :extra, true),
      Map.from_struct(token)
    ]

    for value <- invalid, do: assert(match?({:error, :renew, _, _}, renew(value)))
    assert {:ok, %{record: record}} = Storage.read(scope(spec()))
    assert record.revision == 0 and jobs() == 1 and held() == 1
  end

  test "surrounding Multi and invalid job binding roll back admission journal and jobs together" do
    assert {:ok, _} = configure()
    assert {:ok, %{decision: created}} = create()

    multi =
      Admission.claim_multi(Multi.new(), :claim, scope(spec()), "rollback-owner", 60_000)
      |> Multi.run(:reject, fn _, _ -> {:error, :review_rejection} end)

    assert {:error, :reject, :review_rejection, _} = run(multi)
    assert held() == 0 and Repo.aggregate(Lease, :count) == 0
    assert {:ok, %{claim: claimed}} = claim()
    {:ok, ref} = Lifecycle.worker_ref(created.build)
    payload = %{type: :start, ref: ref}

    multi =
      Admission.transition_multi(
        Multi.new(),
        :decision,
        claimed.token,
        0,
        "rollback-start",
        payload,
        &job/1
      )
      |> Multi.run(:reject, fn _, _ -> {:error, :review_rejection} end)

    assert {:error, :reject, :review_rejection, _} = run(multi)
    invalid_factory = fn intent -> Worker.new(Map.put(intent, "owner_id", "forged")) end

    assert {:error, {:decision, :job_changeset}, :invalid_job_binding, _} =
             event(claimed.token, 0, "bad-job", payload, invalid_factory)

    assert {:ok, %{record: record, build: build}} = Storage.read(scope(spec()))
    assert record.revision == 0 and build.state == :queued and jobs() == 1 and held() == 1
  end

  test "running cancellation and timeout cannot release until matching definite stop" do
    for {suffix, request} <- [{"cancel", :cancel}, {"expire", :expire}] do
      s = spec(%{organization_id: "review-" <> suffix})
      assert {:ok, _} = configure(s)

      assert {:ok, %{decision: created}} =
               create(s, %{max_attempts: 3, timeout_ms: 1, retry_backoff_ms: 0})

      assert {:ok, %{claim: claimed}} = claim(s)
      {_running, ref} = start(claimed.token, created.build)
      Repo.query!("SELECT pg_sleep(0.01)")

      payload =
        if request == :cancel,
          do: %{type: :cancel, reason: "review"},
          else: %{type: :expire, ref: ref}

      assert {:ok, %{decision: uncertain}} = event(claimed.token, 1, suffix, payload)
      assert uncertain.build.active_ref == ref

      assert {:error, :release, :definitive_terminal_evidence_required, _} =
               release(claimed.token, suffix)

      assert {:error, {:decision, :admission}, :invalid_guarded_event, _} =
               event(claimed.token, 2, "premature-retry", %{type: :retry})

      assert {:ok, %{decision: terminal}} = event(claimed.token, 2, "stopped", stopped(ref))
      assert terminal.build.active_ref == nil
      assert {:ok, %{release: released}} = release(claimed.token, "stopped")
      refute released.reservation.held
      assert {:error, :renew, :stale_lease, _} = renew(claimed.token)
    end

    assert held() == 0
  end

  test "never-started queued cancellation releases only its exact accepted cancellation" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: claimed}} = claim()

    assert {:ok, %{decision: cancelled}} =
             event(claimed.token, 0, "queued-cancel", %{type: :cancel, reason: "before dispatch"})

    assert cancelled.build.started_at == nil and cancelled.build.active_ref == nil

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(claimed.token, "missing")

    assert {:ok, %{release: released}} = release(claimed.token, "queued-cancel")
    refute released.reservation.held
    assert {:error, :claim, :not_queued, _} = claim()
  end

  test "release history retains epochs and old terminal events cannot free the next attempt" do
    assert {:ok, _} = configure()
    assert {:ok, %{decision: created}} = create()
    assert {:ok, %{claim: first}} = claim()
    {_running, first_ref} = start(first.token, created.build)
    assert {:ok, %{decision: terminal}} = event(first.token, 1, "stop-one", stopped(first_ref))
    assert {:ok, _} = release(first.token, "stop-one")

    multi =
      Storage.transition_multi(
        Multi.new(),
        :decision,
        scope(spec()),
        2,
        "retry-two",
        %{type: :retry},
        terminal.build.observed_at,
        &job/1
      )

    assert {:ok, %{decision: retried}} = run(multi)
    assert {:ok, %{claim: second}} = claim()
    assert second.token.epoch == first.token.epoch + 1 and second.token.attempt == 2
    assert {:error, :renew, :stale_lease, _} = renew(first.token)
    {:ok, ref} = Lifecycle.worker_ref(retried.build)
    assert {:ok, _} = event(second.token, 3, "start-two", %{type: :start, ref: ref})
    assert {:ok, _} = event(second.token, 4, "stop-two", stopped(ref))

    assert {:error, :release, :definitive_terminal_evidence_required, _} =
             release(second.token, "stop-one")

    assert held() == 1
    assert {:ok, _} = release(second.token, "stop-two")
    assert held() == 0 and Repo.aggregate(Reservation, :count) == 1
    [lease] = Repo.all(Lease)
    assert lease.epoch == second.token.epoch and lease.owner_id == nil and lease.expires_at == nil
  end

  test "database constraints reject malformed NULL pairs and moved occupancy" do
    assert {:ok, _} = configure()
    assert {:ok, _} = create()
    assert {:ok, %{claim: claimed}} = claim()
    id = Ecto.UUID.dump!(claimed.record.id)

    for sql <- [
          "UPDATE mixer_build_reservations SET held = false, terminal_event_id = NULL WHERE build_record_id = $1",
          "UPDATE mixer_build_coordinator_leases SET owner_id = NULL WHERE build_record_id = $1",
          "UPDATE mixer_build_coordinator_leases SET epoch = 0 WHERE build_record_id = $1"
        ] do
      assert {:error, %Postgrex.Error{postgres: %{code: :check_violation}}} =
               Repo.query(sql, [id])
    end

    other = spec(%{organization_id: "other-org"})
    assert {:ok, _} = configure(other)

    assert {:error, %Postgrex.Error{postgres: %{code: :foreign_key_violation}}} =
             Repo.query(
               "UPDATE mixer_build_reservations SET organization_id = 'other-org' WHERE build_record_id = $1",
               [id]
             )

    assert {:ok, %{renew: renewed}} = renew(claimed.token)
    assert renewed.reservation.held and held() == 1
  end
end
