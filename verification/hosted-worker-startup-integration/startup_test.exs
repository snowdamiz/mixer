defmodule MixerHosted.Test.StartupQueueProbe do
  use GenServer

  def start_link(observer), do: GenServer.start_link(__MODULE__, observer)

  def init(observer) do
    owner = Process.whereis(MixerHosted.Builds.WorkerTransport)
    guard = Process.whereis(MixerHosted.Builds.WorkerTransport.RoleGuard)

    if is_pid(owner) and is_pid(guard) do
      send(observer, {:queue_probe_started_after_transport, self(), owner, guard})
      {:ok, observer}
    else
      {:stop, :transport_not_ready}
    end
  end
end

defmodule MixerHosted.Builds.WorkerStartupIntegrationTest do
  use ExUnit.Case, async: false
  alias MixerHosted.{Application, RuntimeConfig}
  alias MixerHosted.Builds.{WorkerConfig, WorkerHTTPAdapter, WorkerTransport}
  alias MixerHosted.Identity.StartupConfig

  defp environment(role \\ "processor") do
    %{
      "MIXER_HOSTED_ROLE" => role,
      "MIXER_DATABASE_HOST" => "db.example.test",
      "MIXER_DATABASE_NAME" => "synthetic_startup",
      "MIXER_DATABASE_USER" => "synthetic_startup",
      "MIXER_DATABASE_PASSWORD" => "synthetic-database-secret",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-secret-", 8)
    }
  end

  defp configured_environment(role \\ "processor") do
    Map.merge(environment(role), %{
      "MIXER_BUILD_WORKER_MODE" => "configured",
      "MIXER_BUILD_WORKER_TOKEN" => Base.url_encode64(<<0::256>>, padding: false),
      "MIXER_BUILD_WORKER_CONFIG" =>
        Jason.encode!(%{
          version: 1,
          endpoint: %{
            host: "worker.example.test",
            port: 443,
            path: "/internal/mixer-build-worker/v1"
          },
          environment_id: "synthetic-environment",
          pool_id: "synthetic-pool",
          controller_id: "synthetic-controller",
          platforms: ["ios", "android"],
          resolvers: ["8.8.8.8"]
        })
    })
  end

  defp children(settings),
    do:
      Application.children(
        settings.role,
        settings.oban,
        settings.identity_startup,
        settings.build_worker_startup
      )

  defp eventually(fun, remaining \\ 100)
  defp eventually(fun, 0), do: assert(fun.())

  defp eventually(fun, remaining) do
    if fun.(),
      do: :ok,
      else:
        (
          Process.sleep(10)
          eventually(fun, remaining - 1)
        )
  end

  test "disabled API and processor expose no worker configuration or dispatcher" do
    for role <- ["api", "processor"] do
      settings = RuntimeConfig.load!(environment(role))
      assert settings.build_worker_startup === %WorkerConfig{}
      assert settings.build_dispatch === nil
      refute Enum.any?(children(settings), &match?({WorkerTransport, _}, &1))
    end
  end

  test "disabled mode rejects even empty or nil credential settings" do
    for role <- ["api", "processor"],
        key <- ["MIXER_BUILD_WORKER_TOKEN", "MIXER_BUILD_WORKER_CONFIG"],
        value <- [nil, "", "synthetic-secret"] do
      assert_raise ArgumentError, "invalid worker configuration", fn ->
        RuntimeConfig.load!(Map.put(environment(role), key, value))
      end
    end
  end

  test "API role cannot configure the build worker or receive its secret" do
    assert_raise ArgumentError, "invalid worker configuration", fn ->
      RuntimeConfig.load!(configured_environment("api"))
    end
  end

  test "processor gets validated CA roots and the fixed dispatch lifetime relationship" do
    settings = RuntimeConfig.load!(configured_environment())
    assert WorkerConfig.validated?(settings.build_worker_startup)
    assert settings.build_worker_startup.platforms == [:ios, :android]
    assert settings.build_worker_startup.ca_roots != []

    assert settings.build_dispatch == [
             adapter: WorkerHTTPAdapter,
             call_timeout_ms: 6_000,
             lease_ttl_ms: 30_000,
             poll_ms: 1_000
           ]

    assert settings.build_dispatch[:lease_ttl_ms] >= 3 * settings.build_dispatch[:call_timeout_ms]
    assert settings.endpoint == [server: false]
    refute inspect(settings) =~ "synthetic"
    refute inspect(settings.build_worker_startup) =~ settings.build_worker_startup.token
  end

  test "operator values cannot select another adapter or widen dispatch timeouts" do
    settings =
      configured_environment()
      |> Map.merge(%{
        "MIXER_BUILD_WORKER_ADAPTER" => "Elixir.Evil",
        "MIXER_BUILD_WORKER_TIMEOUT" => "999999",
        "MIXER_BUILD_WORKER_LEASE" => "1"
      })
      |> RuntimeConfig.load!()

    assert settings.build_dispatch == [
             adapter: WorkerHTTPAdapter,
             call_timeout_ms: 6_000,
             lease_ttl_ms: 30_000,
             poll_ms: 1_000
           ]
  end

  test "configured transport precedes processor queues and preserves temporary ownership" do
    settings = RuntimeConfig.load!(configured_environment())
    assert [MixerHosted.Repo, {WorkerTransport, worker}, {Oban, queues}] = children(settings)
    assert worker == settings.build_worker_startup
    assert queues == settings.oban
    assert Supervisor.child_spec({WorkerTransport, worker}, []).restart == :temporary
  end

  test "application plan rejects a configured worker on API and an identity owner on processor" do
    configured = RuntimeConfig.load!(configured_environment()).build_worker_startup

    assert_raise ArgumentError, fn ->
      Application.children(
        :api,
        [],
        %StartupConfig{mode: :disabled, owner_options: []},
        configured
      )
    end

    assert_raise ArgumentError, fn ->
      Application.children(
        :processor,
        [],
        %StartupConfig{mode: :configured, owner_options: []},
        configured
      )
    end
  end

  test "application plan rejects tampered disabled and configured worker objects" do
    identity = %StartupConfig{mode: :disabled, owner_options: []}
    configured = RuntimeConfig.load!(configured_environment()).build_worker_startup

    for worker <- [
          %WorkerConfig{token: "unexpected"},
          %{configured | token: "invalid"},
          %{configured | resolvers: [{{127, 0, 0, 1}, 53}]},
          %{configured | mode: :unknown}
        ] do
      for role <- [:api, :processor] do
        assert_raise ArgumentError, fn -> Application.children(role, [], identity, worker) end
      end
    end
  end

  test "legacy child planners remain explicitly disabled" do
    identity = %StartupConfig{mode: :disabled, owner_options: []}

    assert Application.children(:api, []) ==
             Application.children(:api, [], identity, %WorkerConfig{})

    assert Application.children(:processor, []) ==
             Application.children(:processor, [], identity, %WorkerConfig{})
  end

  test "real runtime configuration publishes startup and dispatch together" do
    env = configured_environment()
    prior = Map.new(env, fn {key, _} -> {key, System.get_env(key)} end)

    on_exit(fn ->
      Enum.each(prior, fn {key, value} ->
        if value == nil, do: System.delete_env(key), else: System.put_env(key, value)
      end)
    end)

    System.put_env(env)
    path = Path.join(__DIR__, "candidate/hosted/config/runtime.exs")
    values = Config.Reader.read!(path, env: :prod) |> Keyword.fetch!(:mixer_hosted)
    assert values[:role] == :processor
    assert WorkerConfig.validated?(values[:build_worker_startup])
    assert values[:build_dispatch][:adapter] == WorkerHTTPAdapter
    assert values[Oban][:queues][:builds] == 1
    assert values[MixerHostedWeb.Endpoint] == [server: false]
  end

  test "missing bound startup setting fails before any application children start" do
    prior = Elixir.Application.get_all_env(:mixer_hosted)

    on_exit(fn ->
      for {key, _} <- Elixir.Application.get_all_env(:mixer_hosted),
          do: Elixir.Application.delete_env(:mixer_hosted, key)

      for {key, value} <- prior, do: Elixir.Application.put_env(:mixer_hosted, key, value)
    end)

    Elixir.Application.put_env(:mixer_hosted, :role, :processor)
    Elixir.Application.put_env(:mixer_hosted, Oban, [])

    Elixir.Application.put_env(:mixer_hosted, :identity_startup, %StartupConfig{
      mode: :disabled,
      owner_options: []
    })

    Elixir.Application.delete_env(:mixer_hosted, :build_worker_startup)
    assert_raise ArgumentError, fn -> Application.start(:normal, []) end
    assert Process.whereis(WorkerTransport) == nil
    assert Process.whereis(MixerHosted.Supervisor) == nil
  end

  test "actual transport child starts before a queue probe and does not automatically restart" do
    settings = RuntimeConfig.load!(configured_environment())
    [_, transport_child, _] = children(settings)

    {:ok, supervisor} =
      Supervisor.start_link([transport_child, {MixerHosted.Test.StartupQueueProbe, self()}],
        strategy: :one_for_one
      )

    on_exit(fn -> if Process.alive?(supervisor), do: Supervisor.stop(supervisor) end)
    assert_receive {:queue_probe_started_after_transport, probe, owner, guard}
    assert Process.alive?(owner) and Process.alive?(guard)
    assert :sys.get_state(owner).flights == %{}
    assert :sys.get_state(guard).flights == %{}
    Process.exit(owner, :kill)

    eventually(fn ->
      Process.whereis(WorkerTransport) == nil and
        Process.whereis(WorkerTransport.RoleGuard) == nil
    end)

    assert Process.alive?(probe)

    assert [{MixerHosted.Test.StartupQueueProbe, ^probe, :worker, _}] =
             Supervisor.which_children(supervisor)

    assert {:error, :unavailable} = WorkerHTTPAdapter.query(%{})
    assert :persistent_term.get({WorkerTransport, :ownership_v2}, :absent) == :absent
    Supervisor.stop(supervisor)
  end
end
