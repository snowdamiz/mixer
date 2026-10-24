defmodule MixerHosted.Review.AdversarialTest do
  use ExUnit.Case, async: false
  alias MixerHosted.{Repo, RuntimeConfig}

  defp env(role \\ "api") do
    %{
      "MIXER_HOSTED_ROLE" => role,
      "MIXER_DATABASE_HOST" => "fixture.example.test",
      "MIXER_DATABASE_NAME" => "mixer_foundation_test",
      "MIXER_DATABASE_USER" => "mixer_fixture",
      "MIXER_DATABASE_PASSWORD" => "REVIEW_SYNTHETIC_DATABASE_SECRET",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("REVIEW_SYNTHETIC_HTTP_SECRET", 4)
    }
  end

  defp repo do
    [hostname: "127.0.0.1", port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
     database: "mixer_foundation_test", username: "mixer_fixture", pool_size: 2, ssl: false]
  end

  defp boot(role) do
    config = RuntimeConfig.load!(env(role))
    Application.put_env(:mixer_hosted, :role, config.role)
    Application.put_env(:mixer_hosted, Repo, repo())
    Application.put_env(:mixer_hosted, Oban, config.oban)
    endpoint = Application.get_env(:mixer_hosted, MixerHostedWeb.Endpoint)
    |> Keyword.merge(config.endpoint)
    |> Keyword.put(:http, ip: {127, 0, 0, 1}, port: 0)
    Application.put_env(:mixer_hosted, MixerHostedWeb.Endpoint, endpoint)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    on_exit(fn -> Application.stop(:mixer_hosted) end)
    config
  end

  setup_all do
    {:ok, process} = Repo.start_link(repo())
    path = Path.join(File.cwd!(), "priv/repo/migrations")
    assert ["20261024000000_add_oban.exs"] = File.ls!(path)
    assert [20_261_024_000_000] = Ecto.Migrator.run(Repo, path, :up, all: true)
    assert [] = Ecto.Migrator.run(Repo, path, :up, all: true)
    Supervisor.stop(process)
    :ok
  end

  test "normal runtime configuration fails before boot when identity of process role is absent" do
    error = assert_raise ArgumentError, fn ->
      Config.Reader.read!("config/runtime.exs", env: :prod)
    end
    assert Exception.message(error) == "invalid or missing hosted setting: MIXER_HOSTED_ROLE"
    assert Process.whereis(Repo) == nil
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil
  end

  test "maxima are finite and invalid secret-bearing configuration never echoes values" do
    config = env("processor")
    |> Map.put("MIXER_DATABASE_POOL_SIZE", "20")
    |> Map.put("MIXER_QUEUE_BUILDS_CONCURRENCY", "8")
    |> RuntimeConfig.load!()
    assert config.database_connection_bound == 21
    assert config.oban[:queues][:builds] == 8
    assert Keyword.keys(config.oban[:queues]) == [:builds, :signing, :submissions, :releases, :telemetry, :billing]
    refute inspect(config) =~ "REVIEW_SYNTHETIC"

    for {key, value} <- [
      {"MIXER_DATABASE_PASSWORD", String.duplicate("REVIEW_SYNTHETIC", 400)},
      {"MIXER_SECRET_KEY_BASE", "REVIEW_SYNTHETIC_SHORT"},
      {"MIXER_DATABASE_HOST", "REVIEW_SYNTHETIC_SECRET@fixture.example"},
      {"MIXER_DATABASE_HOST", "fixture.example.test\r\nREVIEW_SYNTHETIC"},
      {"MIXER_HTTP_PORT", "-1"},
      {"MIXER_HTTP_PORT", "1\n"},
      {"MIXER_DATABASE_POOL_SIZE", "999999999999999999999999"}
    ] do
      exception = assert_raise ArgumentError, fn -> RuntimeConfig.load!(Map.put(env(), key, value)) end
      assert Exception.message(exception) == "invalid or missing hosted setting: " <> key
      refute Exception.message(exception) =~ "REVIEW_SYNTHETIC"
    end

    processor = env("processor") |> Map.delete("MIXER_SECRET_KEY_BASE") |> RuntimeConfig.load!()
    assert processor.endpoint == [server: false]
  end

  test "real HTTP exposes only liveness and never reflects supplied credentials" do
    boot("api")
    {:ok, {_address, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    base = "http://127.0.0.1:" <> Integer.to_string(port)
    headers = [{~c"authorization", ~c"Bearer REVIEW_SYNTHETIC_HTTP_CREDENTIAL"}]

    for path <- ["/health/ready", "/admin", "/metrics", "/live/websocket",
                 "/v1/updates", "/v3/updates", "/v3/orgs/a/projects/b/artifacts/abc"] do
      assert {:ok, {{_, 404, _}, _, body}} = :httpc.request(:get, {String.to_charlist(base <> path), headers}, [timeout: 2_000], [])
      assert Jason.decode!(body) == %{"error" => %{"message" => "Not Found"}}
      refute to_string(body) =~ "REVIEW_SYNTHETIC"
    end

    assert {:ok, {{_, 404, _}, _, body}} = :httpc.request(:post,
      {String.to_charlist(base <> "/health/live"), headers, ~c"application/json", ~c"{}"}, [timeout: 2_000], [])
    refute to_string(body) =~ "REVIEW_SYNTHETIC"
    assert {:ok, {{_, 200, _}, response_headers, []}} = :httpc.request(:head,
      {String.to_charlist(base <> "/health/live"), headers}, [timeout: 2_000], [])
    assert {~c"cache-control", ~c"no-store"} in response_headers
    assert {:ok, {{_, 200, _}, _, live}} = :httpc.request(:get,
      {String.to_charlist(base <> "/health/live?token=REVIEW_SYNTHETIC_QUERY"), headers}, [timeout: 2_000], [])
    assert Jason.decode!(live) == %{"status" => "alive"}
  end

  test "API never stages a due job and uses at most configured pool plus notifier" do
    boot("api")
    assert {:ok, job} = %{"probe" => "review-api-only"}
      |> MixerHosted.Test.ProbeWorker.new(schedule_in: 1) |> Oban.insert()
    Process.sleep(1_300)
    assert Repo.get!(Oban.Job, job.id).state == "scheduled"
    assert Oban.check_queue(queue: :releases) == nil
    assert Oban.config().peer == {Oban.Peers.Isolated, [leader?: false]}
    %{rows: [[count]]} = Repo.query!("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
    assert count <= 3
    IO.puts("REVIEW_API_DATABASE_CONNECTIONS=" <> Integer.to_string(count))
  end

  test "processor has no listener and bounded database connections" do
    boot("processor")
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil
    assert Oban.config().peer |> elem(0) == Oban.Peers.Database
    %{rows: [[count]]} = Repo.query!("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
    assert count <= 3
    IO.puts("REVIEW_PROCESSOR_DATABASE_CONNECTIONS=" <> Integer.to_string(count))
  end
end
