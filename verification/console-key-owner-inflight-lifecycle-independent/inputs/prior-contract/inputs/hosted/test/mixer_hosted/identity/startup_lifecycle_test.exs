defmodule MixerHosted.Identity.StartupLifecycleTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{
    ConfiguredVerifier,
    KeyOwner,
    KeyOwnerSupervisor,
    StartupConfig,
    StartupFixture
  }

  setup_all do
    StartupFixture.prepare_database()
    :ok
  end

  setup do
    prior = Application.get_all_env(:mixer_hosted)

    on_exit(fn ->
      Application.stop(:mixer_hosted)

      for {key, _} <- Application.get_all_env(:mixer_hosted),
          do: Application.delete_env(:mixer_hosted, key)

      for {key, value} <- prior, do: Application.put_env(:mixer_hosted, key, value)
    end)

    :ok
  end

  defp start(identity) do
    StartupFixture.app_settings(identity)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
  end

  defp liveness do
    {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    url = ~c"http://127.0.0.1:" ++ Integer.to_charlist(port) ++ ~c"/health/live"
    assert {:ok, {{_, 200, _}, _, body}} = :httpc.request(:get, {url, []}, [timeout: 2_000], [])
    assert Jason.decode!(body) == %{"status" => "alive"}
  end

  defp eventually(fun, tries \\ 100)
  defp eventually(fun, 0), do: assert(fun.())

  defp eventually(fun, tries) do
    if fun.(),
      do: :ok,
      else:
        (
          Process.sleep(10)
          eventually(fun, tries - 1)
        )
  end

  test "IS01 actual disabled startup has endpoint and no identity owner" do
    start(StartupConfig.load!(%{}, :api, []))
    assert Process.whereis(KeyOwner) == nil

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate("synthetic", System.system_time(:second))

    liveness()
  end

  test "IS01 actual disabled processor starts no endpoint or identity owner" do
    disabled = StartupConfig.load!(%{}, :processor, [])

    settings =
      MixerHosted.RuntimeConfig.load!(
        Map.put(StartupFixture.foundation_env(), "MIXER_HOSTED_ROLE", "processor")
      )

    StartupFixture.app_settings(disabled)
    Application.put_env(:mixer_hosted, :role, :processor)
    Application.put_env(:mixer_hosted, Oban, settings.oban)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    assert Process.whereis(KeyOwner) == nil
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil

    assert Enum.map(Oban.config().queues, fn {name, options} -> {name, options[:limit]} end) ==
             settings.oban[:queues]
  end

  test "IS03 actual configured application owns an empty bounded component before endpoint" do
    settings =
      StartupFixture.configuration(StartupFixture.envelope(), StartupFixture.standard_roots())

    [MixerHosted.Repo, {Oban, _}, {KeyOwnerSupervisor, _}, MixerHostedWeb.Endpoint] =
      MixerHosted.Application.children(:api, [], settings)

    start(settings)
    owner = Process.whereis(KeyOwner)
    assert is_pid(owner)
    root_children = Supervisor.which_children(MixerHosted.Supervisor)

    assert {KeyOwnerSupervisor, component, :supervisor, _} =
             List.keyfind(root_children, KeyOwnerSupervisor, 0)

    assert Enum.any?(Supervisor.which_children(component), fn {_, pid, _, _} -> pid == owner end)
    state = :sys.get_state(owner)

    for key <- [:snapshots, :attempts, :flights, :waiters, :admitted, :negatives],
        do: assert(state[key] == %{})

    assert DynamicSupervisor.count_children(state.workers).active == 0
    liveness()

    StartupFixture.evidence("startup-empty-state.json", %{
      actualApplication: true,
      endpointLiveness: 200,
      ownerRegistered: true,
      initialSnapshots: 0,
      initialAttempts: 0,
      initialFlights: 0,
      startupFetches: 0
    })
  end

  test "IS03 missing validated binding and invalid required owner prevent endpoint startup" do
    StartupFixture.app_settings(StartupConfig.load!(%{}, :api, []))
    Application.delete_env(:mixer_hosted, :identity_startup)
    assert {:error, _} = Application.ensure_all_started(:mixer_hosted)
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil
    assert Process.whereis(KeyOwner) == nil

    valid =
      StartupFixture.configuration(StartupFixture.envelope(), StartupFixture.standard_roots())

    # Existing production constructor must reject test-only transport options.
    bad = %{
      valid
      | owner_options: valid.owner_options ++ [fixture: %{ip: {127, 0, 0, 1}, port: 1}]
    }

    StartupFixture.app_settings(bad)
    assert {:error, _} = Application.ensure_all_started(:mixer_hosted)
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil
    assert Process.whereis(KeyOwner) == nil
  end

  test "IS04 disabled bound profile rejects via public adapter without any flight" do
    object =
      put_in(StartupFixture.envelope(), ["profiles", Access.at(0), "profile", "enabled"], false)

    start(StartupFixture.configuration(object, StartupFixture.standard_roots()))

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate("synthetic", System.system_time(:second))

    state = :sys.get_state(KeyOwner)
    assert state.attempts == %{}
    assert state.flights == %{}
    liveness()
  end

  test "IS05 actual owner supervision restarts empty and application shutdown removes authority" do
    settings =
      StartupFixture.configuration(StartupFixture.envelope(), StartupFixture.standard_roots())

    start(settings)
    owner = Process.whereis(KeyOwner)
    old_state = :sys.get_state(owner)
    old_workers = Process.whereis(old_state.workers)
    Process.exit(owner, :kill)
    eventually(fn -> is_pid(Process.whereis(KeyOwner)) and Process.whereis(KeyOwner) != owner end)
    state = :sys.get_state(KeyOwner)
    refute state.epoch == old_state.epoch
    assert state.snapshots == %{}
    assert Process.whereis(state.workers) != old_workers
    liveness()
    assert :ok = Application.stop(:mixer_hosted)
    assert Process.whereis(KeyOwner) == nil
    assert Process.whereis(state.workers) == nil
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate("synthetic", System.system_time(:second))

    start(settings)
    refute :sys.get_state(KeyOwner).epoch == state.epoch
    assert :sys.get_state(KeyOwner).snapshots == %{}

    StartupFixture.evidence("startup-lifecycle.json", %{
      actualApplication: true,
      ownerCrashRestart: true,
      workerSupervisorReplaced: true,
      newEpoch: true,
      shutdownAuthorityRemoved: true,
      restartEmpty: true
    })
  end
end
