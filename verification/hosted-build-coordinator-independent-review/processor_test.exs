defmodule MixerHosted.BuildCoordinatorProcessorReview.Adapter do
  @moduledoc false
  use Agent
  alias MixerHosted.Builds.Dispatch.Observation

  def start_link(test_pid),
    do:
      Agent.start_link(fn -> %{test_pid: test_pid, operation: nil, calls: []} end,
        name: __MODULE__
      )

  def query(request), do: callback(:query, request)
  def ensure_started(request), do: callback(:ensure_started, request)
  def stop(_), do: {:error, :unavailable}

  defp callback(kind, request) do
    alias MixerHosted.{Repo, Builds.Storage}

    {:ok, visible} =
      Storage.read(
        Map.take(request.spec, [
          :organization_id,
          :project_id,
          :application_id,
          :build_id,
          :platform
        ])
      )

    %{rows: jobs} =
      Repo.query!("SELECT id, worker, state, attempt, args->>'kind' FROM oban_jobs ORDER BY id")

    evidence = %{
      build_state: visible.build.state,
      revision: visible.record.revision,
      in_transaction: Repo.in_transaction?(),
      jobs: jobs
    }

    {parent, status} =
      Agent.get_and_update(__MODULE__, fn state ->
        operation = if kind == :ensure_started, do: request.operation_id, else: state.operation
        status = if operation == nil, do: :absent, else: :running
        {{state.test_pid, status}, %{state | operation: operation, calls: state.calls ++ [kind]}}
      end)

    send(parent, {:processor_review_callback, kind, self(), request, evidence})
    {:ok, %Observation{operation_id: request.operation_id, ref: request.ref, status: status}}
  end
end

defmodule MixerHosted.BuildCoordinatorProcessorReview.Test do
  use ExUnit.Case, async: false
  import Ecto.Query
  alias Ecto.Multi
  alias MixerHosted.Repo
  alias MixerHosted.Builds.{Admission, Coordinator, Storage}
  alias MixerHosted.Builds.Admission.Reservation
  alias MixerHosted.BuildCoordinatorProcessorReview.Adapter
  @moduletag :database

  setup_all do
    previous = Application.fetch_env(:mixer_hosted, Repo)

    options = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
      database: "mixer_coordinator_review_test",
      username: "mixer_fixture",
      pool_size: 10,
      ssl: false
    ]

    # The notifier opens a separate connection through Repo.config/0. Keep its
    # configuration identical to the actual Ecto query pool, then restore it.
    Application.put_env(:mixer_hosted, Repo, options)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, Repo, value)
        :error -> Application.delete_env(:mixer_hosted, Repo)
      end
    end)

    start_supervised!({Repo, options})

    Ecto.Migrator.run(Repo, Application.app_dir(:mixer_hosted, "priv/repo/migrations"), :up,
      all: true
    )

    :ok
  end

  defp await_notification(probe, left \\ 100) do
    assert :ok = Oban.Notifier.notify(:gossip, %{processor_review_probe: probe})

    receive do
      {:notification, :gossip, %{"processor_review_probe" => ^probe}} -> :ok
    after
      20 ->
        if left > 0,
          do: await_notification(probe, left - 1),
          else: flunk("Postgres notifier did not round-trip the startup probe")
    end
  end

  defp await(fun, left \\ 250) do
    case fun.() do
      {:ok, value} ->
        value

      _ when left > 0 ->
        receive do
        after
          20 -> await(fun, left - 1)
        end

      value ->
        flunk("processor state did not converge: #{inspect(value)}")
    end
  end

  test "asynchronous Oban processor consumes production Coordinator intents then persists snooze" do
    Repo.query!(
      "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_builds, mixer_build_capacities, oban_jobs"
    )

    previous = Application.fetch_env(:mixer_hosted, :build_dispatch)

    Application.put_env(:mixer_hosted, :build_dispatch,
      adapter: Adapter,
      lease_ttl_ms: 30_000,
      call_timeout_ms: 1_000,
      poll_ms: 60_000
    )

    start_supervised!({Adapter, self()})

    oban =
      start_supervised!(
        {Oban,
         repo: Repo,
         queues: [builds: [limit: 1, paused: true]],
         plugins: false,
         testing: :disabled,
         peer: {Oban.Peers.Isolated, leader?: true},
         stager: {Oban.Stager, interval: 20},
         shutdown_grace_period: 1_000}
      )

    try do
      assert Oban.config().testing == :disabled

      assert Keyword.fetch!(Oban.Repo.config(Oban.config()), :database) ==
               "mixer_coordinator_review_test"

      assert :ok = Oban.Notifier.listen(:gossip)
      assert :ok = await_notification(Ecto.UUID.generate())
      assert :ok = Oban.Notifier.unlisten(:gossip)
      assert %{paused: true, running: []} = Oban.check_queue(queue: :builds)

      spec = %{
        organization_id: "processor-review-org",
        project_id: "processor-review-project",
        application_id: "processor-review-app",
        build_id: "processor-review-build",
        platform: :android,
        source: %{
          kind: :revision,
          sha256: String.duplicate("1", 64),
          reference: "processor-immutable-revision"
        },
        toolchain_lock_sha256: String.duplicate("2", 64),
        build_definition_sha256: String.duplicate("3", 64)
      }

      scope =
        Map.take(spec, [:organization_id, :project_id, :application_id, :build_id, :platform])

      assert {:ok, _} =
               Admission.configure_multi(
                 Multi.new(),
                 :capacity,
                 Map.take(scope, [:organization_id, :platform]),
                 :new,
                 1
               )
               |> Repo.transaction()

      assert {:ok, %{{:creation, :job} => created}} =
               Storage.create_multi(
                 Multi.new(),
                 :creation,
                 spec,
                 %{max_attempts: 1, timeout_ms: 60_000, retry_backoff_ms: 0},
                 "processor-review-request",
                 1,
                 &Coordinator.new/1
               )
               |> Repo.transaction()

      assert created.worker == Oban.Worker.to_string(Coordinator)
      assert Repo.get!(Oban.Job, created.id).state == "available"
      assert Repo.get!(Oban.Job, created.id).attempt == 0
      assert :ok = Oban.resume_queue(queue: :builds)

      assert_receive {:processor_review_callback, :query, query_pid, request, visible}, 5_000

      assert_receive {:processor_review_callback, :ensure_started, ensure_pid, same_request,
                      ensure_visible},
                     5_000

      assert query_pid != self() and ensure_pid != self()
      assert visible.build_state == :running and visible.revision == 1
      assert visible.in_transaction == false and ensure_visible.in_transaction == false
      assert same_request.operation_id == request.operation_id and same_request.ref == request.ref

      assert Enum.any?(visible.jobs, fn [id, worker, state, attempt, kind] ->
               id == created.id and worker == Oban.Worker.to_string(Coordinator) and
                 state == "completed" and attempt == 1 and kind == "created"
             end)

      [[successor_id, _, "executing", 1, "start"]] =
        Enum.filter(visible.jobs, fn [_, _, _, _, kind] -> kind == "start" end)

      assert String.starts_with?(request.guard.owner_id, "oban:#{successor_id}:")

      snoozed =
        await(fn ->
          case Repo.get!(Oban.Job, successor_id) do
            %{state: "scheduled", attempt: 0} = job -> {:ok, job}
            job -> {:waiting, job.state}
          end
        end)

      assert snoozed.worker == Oban.Worker.to_string(Coordinator)
      assert snoozed.meta["snoozed"] == 1
      assert snoozed.args["kind"] == "start" and snoozed.args["revision"] == 1
      assert DateTime.compare(snoozed.scheduled_at, snoozed.attempted_at) == :gt
      assert Repo.aggregate(from(r in Reservation, where: r.held), :count) == 1

      assert %{rows: [[true]]} =
               Repo.query!(
                 "SELECT expires_at <= timezone('UTC', clock_timestamp()) FROM mixer_build_coordinator_leases"
               )

      assert {:ok, %{build: %{state: :running, attempt: 1}}} = Storage.read(scope)
      assert Enum.all?(Repo.all(Oban.Job), &(&1.worker == Oban.Worker.to_string(Coordinator)))
      assert :ok = Oban.pause_queue(queue: :builds)

      await(fn ->
        if match?(%{paused: true, running: []}, Oban.check_queue(queue: :builds)),
          do: {:ok, :paused},
          else: :waiting
      end)

      IO.inspect(
        %{
          mode: :asynchronous_oban_processor,
          testing: :disabled,
          creation: %{id: created.id, state: Repo.get!(Oban.Job, created.id).state, attempt: 1},
          successor: %{id: successor_id, state: snoozed.state, attempt: snoozed.attempt},
          worker: snoozed.worker,
          held_reservations: 1,
          callbacks: [:query, :ensure_started]
        },
        label: "independent_coordinator_processor_proof"
      )
    after
      try do
        IO.inspect(
          %{
            jobs:
              Enum.map(
                Repo.all(from(j in Oban.Job, order_by: j.id)),
                &Map.take(&1, [
                  :id,
                  :worker,
                  :state,
                  :args,
                  :attempt,
                  :attempted_at,
                  :scheduled_at,
                  :completed_at,
                  :errors,
                  :meta
                ])
              ),
            queue: Oban.check_queue(queue: :builds),
            notifier_status: Oban.Notifier.status(),
            repository_connection:
              Repo.config() |> Keyword.take([:hostname, :port, :database, :username]) |> Map.new(),
            notifier_connection:
              Oban.Repo.config(Oban.config())
              |> Keyword.take([:hostname, :port, :database, :username])
              |> Map.new(),
            database: Repo.query!("SELECT current_database(), current_setting('TimeZone')").rows,
            adapter: Agent.get(Adapter, & &1)
          },
          label: "independent_coordinator_processor_before_cleanup",
          limit: :infinity,
          printable_limit: :infinity
        )
      after
        stopped = stop_supervised(Oban)

        Repo.query!(
          "TRUNCATE mixer_build_coordinator_leases, mixer_build_reservations, mixer_builds, mixer_build_capacities, oban_jobs"
        )

        case previous do
          {:ok, value} -> Application.put_env(:mixer_hosted, :build_dispatch, value)
          :error -> Application.delete_env(:mixer_hosted, :build_dispatch)
        end

        IO.puts(
          "independent_coordinator_processor_cleanup: owned Oban supervisor stopped; dedicated database rows cleared"
        )

        assert stopped == :ok
        refute Process.alive?(oban)
      end
    end
  end
end
