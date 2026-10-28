defmodule MixerHosted.Identity.StartupLinuxNetworkTest do
  use ExUnit.Case, async: false

  @moduletag skip:
               not (:os.type() == {:unix, :linux} and
                      System.get_env("MIXER_ISOLATED_NETNS") == "1")
  alias MixerHosted.Identity.{
    Admission,
    ConfiguredVerifier,
    KeyOwner,
    StartupDNSFixture,
    StartupFixture,
    TLSFixture
  }

  defp eventually(fun, tries \\ 250)
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

  test "IS04 IS05 actual configured startup cold production DNS TLS admission and lifecycle" do
    prior = Application.get_all_env(:mixer_hosted)

    on_exit(fn ->
      Application.stop(:mixer_hosted)

      for {key, _} <- Application.get_all_env(:mixer_hosted),
          do: Application.delete_env(:mixer_hosted, key)

      for {key, value} <- prior, do: Application.put_env(:mixer_hosted, key, value)
    end)

    StartupFixture.prepare_database()
    server = start_supervised!({TLSFixture, ip: {8, 8, 8, 8}, port: 443})
    dns = start_supervised!(StartupDNSFixture)
    authority = GenServer.call(server, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "startup-key", "alg" => "RS256", "use" => "sig"})

    TLSFixture.configure(server, {:body, Jason.encode!(%{"keys" => [public]})})
    settings = StartupFixture.configuration(StartupFixture.envelope(), [authority.ca])
    assert settings.owner_options[:resolvers] == [{{127, 0, 0, 1}, 53}]
    StartupFixture.app_settings(settings)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    assert :sys.get_state(KeyOwner).snapshots == %{}
    assert GenServer.call(dns, :queries) == []
    assert TLSFixture.info(server).accepted == 0
    {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    url = ~c"http://127.0.0.1:" ++ Integer.to_charlist(port) ++ ~c"/health/live"
    assert {:ok, {{_, 200, _}, _, _}} = :httpc.request(:get, {url, []}, [timeout: 2_000], [])
    token = StartupFixture.token(key)
    now = System.system_time(:second)
    assert {:ok, identity} = ConfiguredVerifier.authenticate(token, now)
    assert identity.subject == "synthetic-startup-subject"
    assert identity.identity_class == :human
    assert length(GenServer.call(dns, :queries)) == 2
    assert TLSFixture.info(server).accepted == 1
    assert map_size(:sys.get_state(KeyOwner).snapshots) == 1
    eventually(fn -> TLSFixture.info(server).closed == 1 end)
    {:ok, permit} = Admission.acquire(KeyOwner, :configured)
    {:ok, lease} = KeyOwner.checkout(KeyOwner, permit, System.system_time(:second))
    old_epoch = :sys.get_state(KeyOwner).epoch
    assert :ok = Application.stop(:mixer_hosted)
    assert Process.whereis(KeyOwner) == nil
    assert {:error, :identity_unavailable} = ConfiguredVerifier.authenticate(token, now)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    assert :sys.get_state(KeyOwner).snapshots == %{}
    refute :sys.get_state(KeyOwner).epoch == old_epoch
    assert {:error, :identity_unavailable} = KeyOwner.finish(KeyOwner, lease)
    Admission.release(permit)
    assert {:ok, _} = ConfiguredVerifier.authenticate(token, System.system_time(:second))
    eventually(fn -> TLSFixture.info(server).closed == 2 end)
    assert :ok = Application.stop(:mixer_hosted)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)
    TLSFixture.configure(server, :stall)

    task =
      Task.async(fn -> ConfiguredVerifier.authenticate(token, System.system_time(:second)) end)

    eventually(fn -> TLSFixture.info(server).accepted == 3 end)
    assert :ok = Application.stop(:mixer_hosted)
    assert {:error, :identity_unavailable} = Task.await(task, 3_000)
    eventually(fn -> TLSFixture.info(server).closed == 3 end)
    assert TLSFixture.info(server).sockets == %{}
    assert Process.whereis(KeyOwner) == nil
    assert Process.whereis(Module.concat(KeyOwner, FetchSupervisor)) == nil
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil

    StartupFixture.evidence("startup-production-network.json", %{
      actualApplication: true,
      endpointLiveness: 200,
      namespace: "owned Linux network-none NET_ADMIN; 8.8.8.8 on lo:1",
      resolver: "127.0.0.1:53",
      destination: "8.8.8.8:443",
      startupDNSQueries: 0,
      startupConnections: 0,
      coldTokenAdmitted: true,
      coldDNSQueries: 2,
      coldConnections: 1,
      oldLeaseRejectedAfterRestart: true,
      restartColdAdmission: true,
      shutdownInflightCancelled: true,
      allThreeConnectionsClosed: true,
      fixtureKeyDirectoryRemoved: TLSFixture.info(server).key_dir_removed,
      publicAdapter: "ConfiguredVerifier.authenticate/2",
      productionPolicyBypasses: 0
    })
  end
end
