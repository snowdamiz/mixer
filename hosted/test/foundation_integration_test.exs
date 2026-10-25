defmodule MixerHosted.FoundationIntegrationTest do
  use ExUnit.Case, async: false
  alias MixerHosted.{Repo, RuntimeConfig}
  alias MixerHosted.Test.ProbeWorker
  @moduletag :database

  defp local_repo do
    [
      hostname: "127.0.0.1",
      port: System.fetch_env!("MIXER_TEST_DATABASE_PORT") |> String.to_integer(),
      database: "mixer_foundation_test",
      username: "mixer_fixture",
      pool_size: 2,
      ssl: false
    ]
  end

  defp settings(role) do
    RuntimeConfig.load!(%{
      "MIXER_HOSTED_ROLE" => role,
      "MIXER_DATABASE_HOST" => "db.example.test",
      "MIXER_DATABASE_NAME" => "mixer_foundation_test",
      "MIXER_DATABASE_USER" => "mixer_fixture",
      "MIXER_DATABASE_PASSWORD" => "synthetic",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-", 8)
    })
  end

  defp boot(role) do
    settings = settings(role)
    Application.put_env(:mixer_hosted, :role, settings.role)
    Application.put_env(:mixer_hosted, :identity_startup, settings.identity_startup)
    Application.put_env(:mixer_hosted, Repo, local_repo())
    Application.put_env(:mixer_hosted, Oban, settings.oban)

    endpoint =
      Application.get_env(:mixer_hosted, MixerHostedWeb.Endpoint)
      |> Keyword.merge(settings.endpoint)
      |> Keyword.put(:http, ip: {127, 0, 0, 1}, port: 0)

    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, endpoint)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
  end

  setup_all do
    {:ok, repo} = Repo.start_link(local_repo())
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
      "CREATE TABLE foundation_probe (id text PRIMARY KEY, effect boolean NOT NULL DEFAULT false)"
    )

    Supervisor.stop(repo)
    :ok
  end

  setup do
    boot("api")
    Repo.query!("TRUNCATE foundation_probe, oban_jobs")
    on_exit(fn -> Application.stop(:mixer_hosted) end)
    :ok
  end

  test "real Bandit serves liveness, hides unknown routes, and never dispatches API jobs" do
    {:ok, {_address, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    url = ~c"http://127.0.0.1:" ++ Integer.to_charlist(port)

    assert {:ok, {{_, 200, _}, headers, body}} =
             :httpc.request(:get, {url ++ ~c"/health/live", []}, [timeout: 2_000], [])

    assert Jason.decode!(body) == %{"status" => "alive"}
    assert {~c"cache-control", ~c"no-store"} in headers

    assert {:ok, {{_, 404, _}, _, body}} =
             :httpc.request(:get, {url ++ ~c"/v3/private/artifacts", []}, [timeout: 2_000], [])

    assert Jason.decode!(body) == %{"error" => %{"message" => "Not Found"}}
    assert {:ok, job} = %{"probe" => "api-only"} |> ProbeWorker.new() |> Oban.insert()
    assert Oban.config().queues == []
    assert Oban.config().peer == {Oban.Peers.Isolated, [leader?: false]}
    assert Oban.check_queue(queue: :releases) == nil
    assert Repo.get!(Oban.Job, job.id).state == "available"
    assert %{rows: [[0]]} = Repo.query!("SELECT count(*) FROM foundation_probe")
  end

  test "Ecto Multi commits a domain fixture and a persisted job together" do
    multi =
      Ecto.Multi.new()
      |> Ecto.Multi.run(:domain, fn repo, _ ->
        {:ok, repo.query!("INSERT INTO foundation_probe (id) VALUES ($1)", ["commit"])}
      end)
      |> Oban.insert(:job, ProbeWorker.new(%{"probe" => "commit"}))

    assert {:ok, %{job: job}} = Repo.transaction(multi)
    assert Repo.get!(Oban.Job, job.id).args == %{"probe" => "commit"}

    assert %{rows: [[false]]} =
             Repo.query!("SELECT effect FROM foundation_probe WHERE id = 'commit'")
  end

  test "Ecto Multi rolls back the already inserted job and domain fixture" do
    multi =
      Ecto.Multi.new()
      |> Ecto.Multi.run(:domain, fn repo, _ ->
        {:ok, repo.query!("INSERT INTO foundation_probe (id) VALUES ($1)", ["rollback"])}
      end)
      |> Oban.insert(:job, ProbeWorker.new(%{"probe" => "rollback"}))
      |> Ecto.Multi.run(:reject, fn _repo, _changes -> {:error, :forced_fixture_failure} end)

    assert {:error, :reject, :forced_fixture_failure, %{job: _}} = Repo.transaction(multi)
    assert %{rows: [[0]]} = Repo.query!("SELECT count(*) FROM foundation_probe")
    assert %{rows: [[0]]} = Repo.query!("SELECT count(*) FROM oban_jobs")
  end

  test "processor completes a delayed job without any HTTP endpoint or request" do
    Application.stop(:mixer_hosted)
    boot("processor")
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil

    assert {:ok, job} =
             %{"probe" => "delayed"} |> ProbeWorker.new(schedule_in: 1) |> Oban.insert()

    eventually(fn -> Repo.get!(Oban.Job, job.id).state == "completed" end)

    assert %{rows: [[true]]} =
             Repo.query!("SELECT effect FROM foundation_probe WHERE id = 'delayed'")
  end

  defp eventually(check) do
    deadline = System.monotonic_time(:millisecond) + 8_000
    poll(check, deadline)
  end

  defp poll(check, deadline) do
    unless check.() do
      assert System.monotonic_time(:millisecond) < deadline,
             "job did not complete before deadline"

      Process.sleep(20)
      poll(check, deadline)
    end
  end
end
