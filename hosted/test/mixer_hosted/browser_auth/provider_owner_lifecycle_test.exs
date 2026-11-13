defmodule MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport do
  use GenServer
  def start_link(parent), do: GenServer.start_link(__MODULE__, parent)
  def init(parent), do: {:ok, %{parent: parent, mode: :ok, pending: %{}}}
  def handle_call({:mode, mode}, _, s), do: {:reply, :ok, %{s | mode: mode}}

  def handle_call({:exchange, request}, from, s) do
    send(s.parent, {:actual_transport, elem(from, 0), request})

    case s.mode do
      :ok -> {:reply, {:ok, "raw-token-response"}, s}
      :error -> {:reply, {:error, :transport_refused}, s}
      :defer -> {:noreply, put_in(s.pending[elem(from, 0)], from)}
    end
  end

  def handle_call({:complete, worker}, _, s) do
    {from, rest} = Map.pop(s.pending, worker)
    if from, do: GenServer.reply(from, {:ok, "late-token-response"})
    {:reply, :ok, %{s | pending: rest}}
  end
end

defmodule MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest do
  use ExUnit.Case, async: false

  alias MixerHosted.BrowserAuth.{
    Config,
    Installation,
    ProviderOwner,
    ProviderTrustConfig
  }

  alias MixerHosted.Identity.{
    Admission,
    KeyOwner,
    KeyOwnerSupervisor,
    Manifest,
    StartupConfig,
    TLSFixture,
    TrustSnapshot
  }

  @owner MixerHosted.BrowserAuth.ProviderTrustOwner
  @workers Module.concat(@owner, FetchSupervisor)
  defp save(name, value) do
    case System.get_env("MIXER_PROVIDER_LIFECYCLE_EVIDENCE") do
      nil ->
        :ok

      destination ->
        prefix = Process.get(:case_name, "lifecycle")

        File.write!(
          Path.join(destination, prefix <> "-" <> name),
          Jason.encode!(value, pretty: true)
        )
    end
  end

  defp wait_until(fun, end_at) do
    if fun.(),
      do: :ok,
      else:
        if(System.monotonic_time(:millisecond) < end_at,
          do:
            (
              Process.sleep(10)
              wait_until(fun, end_at)
            ),
          else: flunk("bounded lifecycle observation expired")
        )
  end

  defp jwks(kid) do
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => kid, "alg" => "RS256", "use" => "sig"})

    Jason.encode!(%{"keys" => [public]})
  end

  defp raw(body, age) do
    date = :httpd_util.rfc1123_date() |> List.to_string()

    "HTTP/1.1 200 OK\r\nDate: #{date}\r\nCache-Control: max-age=#{age}\r\nContent-Type: application/jwk-set+json\r\nContent-Length: #{byte_size(body)}\r\n\r\n#{body}"
  end

  defp identity(roots) do
    object = %{
      "version" => 1,
      "generation" => 11,
      "binding" => "human-main",
      "resolvers" => ["8.8.8.8"],
      "profiles" => [
        %{
          "profile" => %{
            "profile_id" => "human-main",
            "profile_version" => 7,
            "issuer" => "https://issuer.example.invalid/tenant",
            "client_id" => "browser-client",
            "audience" => "mixer-api",
            "identity_class" => "human",
            "enabled" => true
          },
          "jwks_endpoint" => %{
            "host" => "jwks.fixture.invalid",
            "port" => 443,
            "path" => "/api/keys"
          },
          "transport" => "hosted_https"
        }
      ]
    }

    StartupConfig.load!(
      %{"MIXER_IDENTITY_MODE" => "configured", "MIXER_IDENTITY_CONFIG" => Jason.encode!(object)},
      :api,
      roots
    )
  end

  defp browser_env do
    object = %{
      "version" => 1,
      "public_origin" => "https://console.example.invalid",
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => "https://issuer.example.invalid/tenant",
      "client_id" => "browser-client",
      "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://issuer.example.invalid/authorize",
      "token_endpoint" => "https://issuer.example.invalid/token",
      "id_token_jwks_endpoint" => "https://jwks.fixture.invalid/browser/keys",
      "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://fixture/client-v1",
      "session_vault_ref" => "vault://fixture/session-v1",
      "scope" => "openid mixer.workspace.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }

    %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }
  end

  defp full_capacity(owner) do
    permits =
      for _ <- 1..16 do
        assert {:ok, permit} = Admission.acquire(owner, :configured)
        permit
      end

    assert {:error, :identity_unavailable} = Admission.acquire(owner, :configured)
    Enum.each(permits, fn permit -> assert :ok = KeyOwner.release(owner, permit) end)
  end

  defp deadline, do: System.monotonic_time(:millisecond) + 4_000

  defp exchange(config, d \\ nil),
    do: ProviderOwner.exchange(config, "fixture-code", "fixture-verifier", d || deadline())

  defp slots(table),
    do:
      Enum.filter(:ets.tab2list(table), fn
        {key, _, _} -> is_tuple(key) and elem(key, 0) == :slot
        _ -> false
      end)

  defp empty(table),
    do: wait_until(fn -> slots(table) == [] end, System.monotonic_time(:millisecond) + 1_000)

  defp start_provider(config, transport) do
    pid =
      start_supervised!(%{
        id: :provider,
        start: {ProviderOwner, :start_trust_fixture, [config, transport]},
        restart: :temporary
      })

    :erlang.trace(pid, true, [:call, {:tracer, self()}])
    pid
  end

  defp async_exchange(config, d) do
    parent = self()

    spawn_monitor(fn ->
      send(parent, {:exchange_result, self(), exchange(config, d)})

      receive do
        :done -> :ok
      end
    end)
  end

  test "browser_provider_trust_owner_lease_generation_fencing" do
    :erlang.trace_pattern({KeyOwner, :release, 2}, true, [:local])
    on_exit(fn -> :erlang.trace_pattern({KeyOwner, :release, 2}, false, [:local]) end)
    fixture = start_supervised!({TLSFixture, []})
    %{ip: ip, port: port, ca: ca} = GenServer.call(fixture, :authority)
    source = identity([ca])
    assert {:ok, config} = Config.load(browser_env(), :api, source)
    assert {:ok, settings} = ProviderTrustConfig.new(config, source)
    assert settings.owner_options[:name] === @owner
    manifest = settings.owner_options[:manifest]
    assert {:ok, _} = Manifest.validate(manifest)

    browser =
      start_supervised!(%{
        id: :browser_component,
        start:
          {KeyOwnerSupervisor, :start_fixture,
           [settings.owner_options ++ [fixture: %{ip: ip, port: port}]]},
        type: :supervisor,
        shutdown: :infinity
      })

    original = Process.whereis(@owner)
    workers = Process.whereis(@workers)

    transport =
      start_supervised!({MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport, self()})

    :ok = TLSFixture.configure(fixture, {:raw, raw(jwks("browser-only"), 120)})
    assert {:ok, probe} = Admission.acquire(@owner, :configured)
    table = elem(probe, 0)
    assert :ok = KeyOwner.release(original, probe)
    provider = start_provider(config, transport)

    on_exit(fn ->
      save("beam-cleanup.json", %{
        provider_dead: not Process.alive?(provider),
        original_owner_dead: not Process.alive?(original),
        workers_dead: not Process.alive?(workers),
        browser_supervisor_dead: not Process.alive?(browser),
        transport_dead: not Process.alive?(transport),
        tls_dead: not Process.alive?(fixture),
        owner_name_absent: Process.whereis(@owner) == nil,
        provider_name_absent: Process.whereis(ProviderOwner) == nil,
        worker_name_absent: Process.whereis(@workers) == nil,
        original_table_deleted: :ets.info(table) == :undefined
      })

      refute Process.alive?(provider)
      refute Process.alive?(workers)
      assert :ets.info(table) == :undefined
      assert Process.whereis(@owner) == nil and Process.whereis(ProviderOwner) == nil
    end)

    assert {:ok, "raw-token-response", snapshot, ticket} = exchange(config)
    assert {:ok, _} = TrustSnapshot.key(snapshot, "browser-only")
    assert_receive {:actual_transport, worker, request}
    assert Process.alive?(worker)
    assert request.code == "fixture-code" and request.code_verifier == "fixture-verifier"
    assert length(slots(table)) == 2

    other_permits =
      for _ <- 1..15 do
        assert {:ok, permit} = Admission.acquire(@owner, :configured)
        permit
      end

    assert {:error, :identity_unavailable} = Admission.acquire(@owner, :configured)
    Enum.each(other_permits, fn permit -> assert :ok = KeyOwner.release(original, permit) end)
    assert Enum.all?(slots(table), fn {_, pid, _} -> pid == worker end)
    # Wrong caller, config and ticket do not consume the legitimate ticket.
    parent = self()

    {wrong, wrong_ref} =
      spawn_monitor(fn ->
        send(parent, {:wrong_finish, ProviderOwner.finish(ticket, config, deadline())})
      end)

    assert_receive {:wrong_finish, {:error, :provider_unavailable}}
    assert_receive {:DOWN, ^wrong_ref, :process, ^wrong, :normal}

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish(ticket, %{config | client_id: "other-client"}, deadline())

    {pid, gen, digest, _} = ticket

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish({pid, gen, digest, make_ref()}, config, deadline())

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish({pid, make_ref(), digest, elem(ticket, 3)}, config, deadline())

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish({pid, gen, "wrong-digest", elem(ticket, 3)}, config, deadline())

    assert length(slots(table)) == 2
    assert :ok = ProviderOwner.finish(ticket, config, deadline())
    assert {:error, :provider_unavailable} = ProviderOwner.finish(ticket, config, deadline())
    empty(table)
    full_capacity(@owner)

    assert {:ok, _, _, generation_ticket} = exchange(config)
    assert {:ok, 12} = KeyOwner.replace_manifest(original, 11, manifest)

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish(generation_ticket, config, deadline())

    empty(table)
    assert {:ok, _, _, fresh_ticket} = exchange(config)
    assert :ok = ProviderOwner.finish(fresh_ticket, config, deadline())
    empty(table)

    # Deadline cleanup consumes an issued lease without caller cooperation.
    assert {:ok, _, _, expired} = exchange(config, System.monotonic_time(:millisecond) + 150)
    Process.sleep(180)
    assert {:error, :provider_unavailable} = ProviderOwner.finish(expired, config, deadline())
    empty(table)

    :ok = GenServer.call(transport, {:mode, :error})
    assert {:error, :provider_unavailable} = exchange(config)
    empty(table)
    :ok = GenServer.call(transport, {:mode, :defer})
    # Clear transport observation messages from earlier completed calls.
    drain_transport()
    {late, late_ref} = async_exchange(config, System.monotonic_time(:millisecond) + 200)
    assert_receive {:actual_transport, late_worker, _}, 1_000
    late_monitor = Process.monitor(late_worker)
    assert_receive {:exchange_result, ^late, {:error, :provider_unavailable}}, 1_000
    assert_receive {:DOWN, ^late_monitor, :process, ^late_worker, _}, 1_000
    :ok = GenServer.call(transport, {:complete, late_worker})
    empty(table)
    send(late, :done)
    assert_receive {:DOWN, ^late_ref, :process, ^late, :normal}

    {cancel, cancel_ref} = async_exchange(config, deadline())
    assert_receive {:actual_transport, cancel_worker, _}, 1_000
    cancel_monitor = Process.monitor(cancel_worker)
    Process.exit(cancel, :kill)
    assert_receive {:DOWN, ^cancel_ref, :process, ^cancel, :killed}
    assert_receive {:DOWN, ^cancel_monitor, :process, ^cancel_worker, _}, 1_000
    empty(table)
    :ok = GenServer.call(transport, {:complete, cancel_worker})

    :ok = GenServer.call(transport, {:mode, :ok})
    assert {:ok, _, _, old_owner_ticket} = exchange(config)
    assert :ok = Supervisor.terminate_child(browser, KeyOwner)
    refute Process.alive?(original)
    assert :ets.info(table) == :undefined
    assert {:ok, replacement} = Supervisor.restart_child(browser, KeyOwner)
    assert replacement != original
    :ok = TLSFixture.configure(fixture, {:raw, raw(jwks("replacement-only"), 3)})

    assert {:error, :provider_unavailable} =
             ProviderOwner.finish(old_owner_ticket, config, deadline())

    assert {:ok, replacement_probe} = Admission.acquire(@owner, :configured)
    replacement_table = elem(replacement_probe, 0)
    assert :ok = KeyOwner.release(replacement, replacement_probe)
    assert {:ok, _, replacement_snapshot, stale} = exchange(config)
    assert {:ok, _} = TrustSnapshot.key(replacement_snapshot, "replacement-only")

    Process.sleep(
      max(0, replacement_snapshot.fresh_until * 1_000 - System.system_time(:millisecond)) + 30
    )

    assert {:error, :provider_unavailable} = ProviderOwner.finish(stale, config, deadline())
    empty(replacement_table)
    full_capacity(@owner)
    assert DynamicSupervisor.count_children(@workers).active == 0

    # Provider termination reaps its exact transport worker and releases its lease.
    # Restart with a new real KeyOwner to refresh expired keys, not owner-state edits.
    assert :ok = Supervisor.terminate_child(browser, KeyOwner)
    assert {:ok, final_owner} = Supervisor.restart_child(browser, KeyOwner)
    :ok = TLSFixture.configure(fixture, {:raw, raw(jwks("final-only"), 120)})
    assert {:ok, final_probe} = Admission.acquire(@owner, :configured)
    final_table = elem(final_probe, 0)
    assert :ok = KeyOwner.release(final_owner, final_probe)
    :ok = GenServer.call(transport, {:mode, :defer})
    drain_transport()
    {stopping, stopping_ref} = async_exchange(config, deadline())
    assert_receive {:actual_transport, stopping_worker, _}, 2_500
    stopping_monitor = Process.monitor(stopping_worker)
    assert :ok = stop_supervised(:provider)
    assert_receive {:DOWN, ^stopping_monitor, :process, ^stopping_worker, _}, 1_000
    assert_receive {:exchange_result, ^stopping, {:error, :provider_unavailable}}, 1_000
    send(stopping, :done)
    assert_receive {:DOWN, ^stopping_ref, :process, ^stopping, :normal}
    empty(final_table)
    full_capacity(@owner)
    :ok = GenServer.call(transport, {:complete, stopping_worker})

    # Existing static fixture uses an actual snapshot captured above, byte-identical contract.
    :ok = GenServer.call(transport, {:mode, :ok})

    static =
      start_supervised!(%{
        id: :static_provider,
        start: {ProviderOwner, :start_fixture, [config, snapshot, transport]},
        restart: :temporary
      })

    assert {:ok, "raw-token-response", ^snapshot, static_ticket} = exchange(config)
    assert tuple_size(static_ticket) == 3
    assert :ok = ProviderOwner.finish(static_ticket, config, deadline())
    assert :ok = stop_supervised(:static_provider)
    refute Process.alive?(static)

    unconfigured =
      start_supervised!(%{
        id: :unconfigured,
        start: {ProviderOwner, :start_link, [:unconfigured]},
        restart: :temporary
      })

    assert {:error, :provider_unconfigured} = exchange(config)
    assert :ok = stop_supervised(:unconfigured)
    refute Process.alive?(unconfigured)

    hosted = %MixerHosted.RuntimeConfig{
      role: :api,
      repo: [],
      oban: [],
      endpoint: [],
      database_connection_bound: 0,
      identity_startup: source
    }

    assert_raise ArgumentError, "browser installation unavailable: configuration", fn ->
      Installation.load!(browser_env(), hosted)
    end

    assert Installation.load!(%{}, hosted) == :disabled

    delivery_ref = :erlang.trace_delivered(:all)
    assert_receive {:trace_delivered, :all, ^delivery_ref}, 1_000
    releases = collect_releases([])
    assert length(releases) == 0
    nonces = Enum.map(releases, fn {_owner, permit} -> elem(permit, 6) end)
    assert length(Enum.uniq(nonces)) == length(nonces)
    assert Enum.all?(releases, fn {owner, _} -> owner in [original, replacement, final_owner] end)

    wait_until(
      fn ->
        info = TLSFixture.info(fixture)
        info.accepted == info.closed and map_size(info.sockets) == 0
      end,
      System.monotonic_time(:millisecond) + 1_000
    )

    info = TLSFixture.info(fixture)
    requests = Enum.reverse(info.requests)
    assert length(requests) == 3

    assert Enum.all?(requests, fn r ->
             String.starts_with?(r.request, "GET /browser/keys HTTP/1.1\r\n")
           end)

    assert :ok = stop_supervised(:browser_component)
    assert :ok = stop_supervised(MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport)
    assert :ok = stop_supervised(TLSFixture)
    assert :ets.info(replacement_table) == :undefined and :ets.info(final_table) == :undefined
    refute Process.alive?(final_owner)

    save("integration-observations.json", %{
      name: "browser_provider_trust_owner_lease_generation_fencing",
      actual_exchange: true,
      original_pid_fence: true,
      generation_fence: true,
      snapshot_expiry_fence: true,
      deadline_expiry: true,
      wrong_attempts_preserve_legitimate_ticket: true,
      actual_worker_permit_caller: true,
      reclamation: "real KeyOwner caller monitor DOWN; no explicit release",
      release_count: length(releases),
      unique_original_permit_nonces: length(nonces),
      exact_worker_DOWN_required: true,
      worker_death_observed: true,
      transport_error: true,
      late_completion: true,
      caller_death_cancellation: true,
      provider_termination: true,
      static_fixture_regression: true,
      production_refusal_unchanged: true,
      permit_tables_deleted: true,
      zero_key_fetch_workers: true,
      requests: length(requests),
      peers_closed: info.closed
    })
  end

  defp drain_transport do
    receive do
      {:actual_transport, _, _} -> drain_transport()
    after
      0 -> :ok
    end
  end

  defp collect_releases(acc) do
    receive do
      {:trace, _, :call, {KeyOwner, :release, [owner, permit]}} ->
        collect_releases([{owner, permit} | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end

  test "real_reaper_cannot_reclaim_live_expired_transport_or_issued_worker" do
    fixture = start_supervised!({TLSFixture, []})
    %{ip: ip, port: port, ca: ca} = GenServer.call(fixture, :authority)
    source = identity([ca])
    assert {:ok, config} = Config.load(browser_env(), :api, source)
    assert {:ok, settings} = ProviderTrustConfig.new(config, source)

    browser =
      start_supervised!(%{
        id: :browser_component,
        start:
          {KeyOwnerSupervisor, :start_fixture,
           [settings.owner_options ++ [fixture: %{ip: ip, port: port}]]},
        type: :supervisor,
        shutdown: :infinity
      })

    owner = Process.whereis(@owner)
    fetch = Process.whereis(@workers)

    transport =
      start_supervised!({MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport, self()})

    :ok = TLSFixture.configure(fixture, {:raw, raw(jwks("browser-only"), 120)})
    assert {:ok, probe} = Admission.acquire(@owner, :configured)
    table = elem(probe, 0)
    assert :ok = KeyOwner.release(owner, probe)
    provider = start_provider(config, transport)
    assert {:ok, _, _, warm} = exchange(config)
    assert_receive {:actual_transport, warm_worker, _}
    assert Process.alive?(warm_worker)
    assert :ok = ProviderOwner.finish(warm, config, deadline())
    refute Process.alive?(warm_worker)
    empty(table)
    :ok = GenServer.call(transport, {:mode, :defer})
    original_deadline = System.monotonic_time(:millisecond) + 700
    callers = for _ <- 1..16, do: async_exchange(config, original_deadline)

    old =
      for _ <- 1..16 do
        assert_receive {:actual_transport, worker, _}, 1_000
        assert {:links, links} = Process.info(worker, :links)
        assert provider in links
        {worker, Process.monitor(worker)}
      end

    assert length(slots(table)) == 32

    assert Enum.all?(slots(table), fn {_, pid, _} -> Enum.any?(old, fn {w, _} -> w == pid end) end)

    # Public runtime suspension keeps actual admitted workers live across expiry;
    # no lease, ETS row, owner state, or authority identity is modified.
    Enum.each(old, fn {w, _} -> true = :erlang.suspend_process(w) end)
    pr = Process.monitor(provider)
    Process.exit(provider, :kill)
    assert_receive {:DOWN, ^pr, :process, ^provider, :killed}, 1_000

    replacement =
      start_supervised!(%{
        id: :replacement,
        start: {ProviderOwner, :start_trust_fixture, [config, transport]},
        restart: :temporary
      })

    send(owner, :reap)
    :sys.get_state(owner)
    assert Enum.all?(old, fn {w, _} -> Process.alive?(w) end)
    assert length(slots(table)) == 32
    assert {:error, :identity_unavailable} = Admission.acquire(@owner, :configured)
    assert {:error, :provider_unavailable} = exchange(config)
    # Cross the original deadline while the real transport processes remain alive.
    Process.sleep(max(0, original_deadline - System.monotonic_time(:millisecond)) + 30)
    send(owner, :reap)
    :sys.get_state(owner)
    assert Enum.all?(old, fn {w, _} -> Process.alive?(w) end)
    assert length(slots(table)) == 32
    assert {:error, :identity_unavailable} = Admission.acquire(@owner, :configured)

    save("reaper-observations.json", %{
      old_live_after_provider_DOWN: 16,
      old_live_after_original_deadline: 16,
      reaper_kept_32_slots: true,
      replacement_refused_while_old_live: true,
      expiry_eviction_of_live_workers: false,
      actual_worker_owns_permit: true,
      exact_owner_pid: inspect(owner),
      original_deadline: original_deadline
    })

    Enum.each(old, fn {w, _} -> true = :erlang.resume_process(w) end)
    Enum.each(old, fn {w, m} -> assert_receive {:DOWN, ^m, :process, ^w, _}, 1_000 end)

    Enum.each(callers, fn {c, m} ->
      assert_receive {:exchange_result, ^c, {:error, :provider_unavailable}}, 1_000
      send(c, :done)
      assert_receive {:DOWN, ^m, :process, ^c, :normal}, 1_000
    end)

    empty(table)
    second_callers = for _ <- 1..16, do: async_exchange(config, deadline())

    second =
      for _ <- 1..16 do
        assert_receive {:actual_transport, w, _}, 1_000
        assert Enum.all?(old, fn {p, _} -> not Process.alive?(p) end)
        {w, Process.monitor(w)}
      end

    assert length(slots(table)) == 32
    assert {:error, :identity_unavailable} = Admission.acquire(@owner, :configured)
    assert Enum.count(old ++ second, fn {w, _} -> Process.alive?(w) end) == 16
    # Abnormal exact worker death leaves the provider and unrelated work alive.
    [{broken, bm} | rest] = second
    Process.exit(broken, :kill)
    assert_receive {:DOWN, ^bm, :process, ^broken, :killed}, 1_000
    assert Process.alive?(owner) and Process.alive?(replacement)
    assert Enum.all?(rest, fn {w, _} -> Process.alive?(w) end)
    Enum.each(rest, fn {w, _} -> :ok = GenServer.call(transport, {:complete, w}) end)

    outcomes =
      Enum.map(second_callers, fn {c, m} ->
        receive do
          {:exchange_result, ^c, result} -> {c, m, result}
        after
          1_000 -> flunk("missing replacement result")
        end
      end)

    assert Enum.count(outcomes, fn {_, _, r} -> match?({:ok, _, _, _}, r) end) == 15
    assert Enum.count(outcomes, fn {_, _, r} -> r == {:error, :provider_unavailable} end) == 1
    send(owner, :reap)
    :sys.get_state(owner)
    wait_until(fn -> length(slots(table)) == 30 end, System.monotonic_time(:millisecond) + 1_000)
    assert length(slots(table)) == 30
    assert Enum.all?(rest, fn {w, _} -> Process.alive?(w) end)
    assert Enum.all?(slots(table), fn {_, p, _} -> Enum.any?(rest, fn {w, _} -> p == w end) end)
    # Issued tickets still reserve capacity, and provider death cleans them up.
    rr = Process.monitor(replacement)
    Process.exit(replacement, :kill)
    assert_receive {:DOWN, ^rr, :process, ^replacement, :killed}, 1_000
    Enum.each(rest, fn {w, m} -> assert_receive {:DOWN, ^m, :process, ^w, _}, 1_000 end)

    Enum.each(outcomes, fn {c, m, _} ->
      send(c, :done)
      assert_receive {:DOWN, ^m, :process, ^c, :normal}, 1_000
    end)

    empty(table)
    full_capacity(@owner)
    assert DynamicSupervisor.count_children(@workers).active == 0
    assert :ok = stop_supervised(:browser_component)
    assert :ok = stop_supervised(MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport)
    assert :ok = stop_supervised(TLSFixture)

    cleanup = %{
      all_32_exact_worker_DOWN: true,
      all_32_caller_DOWN: true,
      full_capacity_restored: true,
      table_deleted: :ets.info(table) == :undefined,
      owner_dead: not Process.alive?(owner),
      fetch_dead: not Process.alive?(fetch),
      browser_dead: not Process.alive?(browser),
      transport_dead: not Process.alive?(transport),
      fixture_dead: not Process.alive?(fixture),
      names_absent: Process.whereis(@owner) == nil and Process.whereis(ProviderOwner) == nil
    }

    save("crash-cleanup.json", cleanup)
    assert Enum.all?(Map.values(cleanup))

    save("issued-observations.json", %{
      issued_workers: 15,
      issued_permits: 15,
      issued_reaper_preserved_capacity: true,
      abnormal_worker_death: true,
      unrelated_workers_survived: true,
      explicit_release_before_terminal: false,
      max_simultaneous_transport_workers: 16
    })
  end

  test "provider_and_KeyOwner_replacement_must_not_admit_overlapping_actual_transport_workers" do
    replacement_case(:provider_and_keyowner)
  end

  test "KeyOwner_only_replacement_with_live_provider_must_join_old_transport_workers" do
    replacement_case(:keyowner_only)
  end

  defp replacement_case(mode) do
    Process.put(:case_name, Atom.to_string(mode))
    fixture = start_supervised!({TLSFixture, []})
    %{ip: ip, port: port, ca: ca} = GenServer.call(fixture, :authority)
    source = identity([ca])
    assert {:ok, config} = Config.load(browser_env(), :api, source)
    assert {:ok, settings} = ProviderTrustConfig.new(config, source)

    browser =
      start_supervised!(%{
        id: :browser_component,
        start:
          {KeyOwnerSupervisor, :start_fixture,
           [settings.owner_options ++ [fixture: %{ip: ip, port: port}]]},
        type: :supervisor,
        shutdown: :infinity
      })

    owner = Process.whereis(@owner)
    fetch = Process.whereis(@workers)

    transport =
      start_supervised!({MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport, self()})

    :ok = TLSFixture.configure(fixture, {:raw, raw(jwks("cross-owner"), 120)})
    assert {:ok, probe} = Admission.acquire(@owner, :configured)
    table = elem(probe, 0)
    assert :ok = KeyOwner.release(owner, probe)
    provider = start_provider(config, transport)
    assert {:ok, _, _, warm} = exchange(config)
    assert_receive {:actual_transport, warm_worker, _}
    assert :ok = ProviderOwner.finish(warm, config, deadline())
    refute Process.alive?(warm_worker)
    empty(table)
    :ok = GenServer.call(transport, {:mode, :defer})
    original_deadline = deadline()
    callers = for _ <- 1..16, do: async_exchange(config, original_deadline)

    old =
      for _ <- 1..16 do
        assert_receive {:actual_transport, w, _}, 1_000
        {w, Process.monitor(w)}
      end

    assert length(slots(table)) == 32

    assert MapSet.new(
             for {_, pid, :worker, [Task]} <- DynamicSupervisor.which_children(fetch), do: pid
           ) == MapSet.new(Enum.map(old, &elem(&1, 0)))

    assert Enum.all?(old, fn {w, _} ->
             {:links, links} = Process.info(w, :links)
             fetch in links and provider in links
           end)

    if mode == :provider_and_keyowner do
      pr = Process.monitor(provider)
      Process.exit(provider, :kill)
      assert_receive {:DOWN, ^pr, :process, ^provider, :killed}, 1_000
    else
      assert Process.alive?(provider)
    end

    assert Enum.all?(old, fn {w, _} -> Process.alive?(w) end)
    # No worker suspension: each real admitted worker remains blocked in the
    # actual raw GenServer.call with its original, unextended deadline.
    owner_ref = Process.monitor(owner)
    Process.exit(owner, :kill)
    assert_receive {:DOWN, ^owner_ref, :process, ^owner, :killed}, 1_000

    wait_until(
      fn ->
        p = Process.whereis(@owner)
        is_pid(p) and p != owner
      end,
      System.monotonic_time(:millisecond) + 1_000
    )

    replacement_owner = Process.whereis(@owner)
    # initialization barrier before admission/table use
    :sys.get_state(replacement_owner)
    replacement_fetch = Process.whereis(@workers)
    assert replacement_fetch != fetch
    refute Process.alive?(fetch)
    # Observe every exact old worker DOWN before any replacement permit is acquired.
    old_down =
      Enum.map(old, fn {w, m} ->
        assert_receive {:DOWN, ^m, :process, ^w, reason}, 1_000
        %{pid: inspect(w), reason: inspect(reason)}
      end)

    assert Enum.all?(old, fn {w, _} -> not Process.alive?(w) end)
    old_live_before_replacement_admission = Enum.count(old, fn {w, _} -> Process.alive?(w) end)
    assert old_live_before_replacement_admission == 0
    assert :ets.info(table) == :undefined
    assert {:ok, replacement_probe} = Admission.acquire(@owner, :configured)
    replacement_table = elem(replacement_probe, 0)
    assert replacement_table != table
    assert :ok = KeyOwner.release(replacement_owner, replacement_probe)

    replacement =
      if mode == :provider_and_keyowner do
        start_supervised!(%{
          id: :replacement,
          start: {ProviderOwner, :start_trust_fixture, [config, transport]},
          restart: :temporary
        })
      else
        assert Process.alive?(provider)
        assert Process.whereis(ProviderOwner) === provider
        provider
      end

    # Both generations use the original unchanged budget.
    new_callers = for _ <- 1..16, do: async_exchange(config, original_deadline)

    new =
      for _ <- 1..16 do
        assert_receive {:actual_transport, w, _}, 1_000
        {w, Process.monitor(w)}
      end

    assert length(slots(replacement_table)) == 32
    assert {:error, :identity_unavailable} = Admission.acquire(@owner, :configured)
    old_live = Enum.count(old, fn {w, _} -> Process.alive?(w) end)
    new_live = Enum.count(new, fn {w, _} -> Process.alive?(w) end)
    state = :sys.get_state(transport)

    active_exact =
      Enum.count(old ++ new, fn {w, _} -> Process.alive?(w) and Map.has_key?(state.pending, w) end)

    assert Process.alive?(replacement_owner) and Process.alive?(replacement)

    assert MapSet.new(
             for {_, pid, :worker, [Task]} <- DynamicSupervisor.which_children(replacement_fetch),
                 do: pid
           ) == MapSet.new(Enum.map(new, &elem(&1, 0)))

    remaining_original = original_deadline - System.monotonic_time(:millisecond)
    assert remaining_original > 0

    assert Enum.all?(:sys.get_state(replacement).tickets, fn {_, entry} ->
             entry.owner === replacement_owner and entry.deadline === original_deadline
           end)

    observations = %{
      case: mode,
      old_worker_DOWN_before_replacement_admission: old_down,
      old_live_before_replacement_admission: old_live_before_replacement_admission,
      original_fetch: inspect(fetch),
      replacement_fetch: inspect(replacement_fetch),
      raw_workers_verified_Task_children: true,
      same_provider_survived:
        mode == :keyowner_only and provider === replacement and Process.alive?(provider),
      capacity: 16,
      old_transport_workers_alive: old_live,
      replacement_transport_workers_alive: new_live,
      simultaneous_actual_transport_workers: active_exact,
      old_provider: inspect(provider),
      replacement_provider: inspect(replacement),
      original_KeyOwner: inspect(owner),
      replacement_KeyOwner: inspect(replacement_owner),
      original_table: inspect(table),
      replacement_table: inspect(replacement_table),
      original_table_deleted: :ets.info(table) == :undefined,
      actual_old_workers: Enum.map(old, fn {w, _} -> inspect(w) end),
      actual_new_workers: Enum.map(new, fn {w, _} -> inspect(w) end),
      old_worker_current_functions:
        Enum.map(old, fn {w, _} -> inspect(Process.info(w, :current_function)) end),
      old_workers_suspended: false,
      remaining_original_deadline_ms: remaining_original,
      new_table_slot_rows: length(slots(replacement_table)),
      overflow_refused_at_new_owner_capacity: true,
      replacement_admission_succeeded_while_old_actual_workers_alive:
        old_live > 0 and new_live == 16,
      original_deadlines_unextended: true,
      external_provider_traffic: false
    }

    save("cross-owner-observations.json", observations)
    IO.puts("CROSS_KEYOWNER_ACTUAL " <> Jason.encode!(observations))
    # Collect exact product cleanup before the desired-property assertion.
    Enum.each(new, fn {w, _} -> Process.exit(w, :kill) end)
    Enum.each(new, fn {w, m} -> assert_receive {:DOWN, ^m, :process, ^w, :killed}, 1_000 end)

    Enum.each(callers ++ new_callers, fn {c, m} ->
      assert_receive {:exchange_result, ^c, {:error, :provider_unavailable}}, 1_000
      send(c, :done)
      assert_receive {:DOWN, ^m, :process, ^c, :normal}, 1_000
    end)

    empty(replacement_table)
    full_capacity(@owner)
    assert DynamicSupervisor.count_children(@workers).active == 0

    assert :ok =
             stop_supervised(
               if(mode == :provider_and_keyowner, do: :replacement, else: :provider)
             )

    wait_until(
      fn ->
        info = TLSFixture.info(fixture)
        info.accepted == info.closed and map_size(info.sockets) == 0
      end,
      System.monotonic_time(:millisecond) + 1_000
    )

    info = TLSFixture.info(fixture)
    assert info.accepted == 2 and info.closed == 2
    assert :ok = stop_supervised(:browser_component)
    assert :ok = stop_supervised(MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport)
    assert :ok = stop_supervised(TLSFixture)

    cleanup = %{
      all_32_exact_worker_DOWN: true,
      all_32_caller_DOWN: true,
      full_capacity_restored: true,
      original_owner_dead: not Process.alive?(owner),
      replacement_owner_dead: not Process.alive?(replacement_owner),
      original_fetch_dead: not Process.alive?(fetch),
      replacement_fetch_dead: not Process.alive?(replacement_fetch),
      providers_dead: not Process.alive?(provider) and not Process.alive?(replacement),
      browser_dead: not Process.alive?(browser),
      transport_dead: not Process.alive?(transport),
      fixture_dead: not Process.alive?(fixture),
      both_tables_deleted:
        :ets.info(table) == :undefined and :ets.info(replacement_table) == :undefined,
      loopback_TLS_peers_closed: info.accepted == info.closed,
      all_32_exact_workers_dead: Enum.all?(old ++ new, fn {w, _} -> not Process.alive?(w) end),
      names_absent:
        Process.whereis(@owner) == nil and Process.whereis(@workers) == nil and
          Process.whereis(ProviderOwner) == nil
    }

    save("cross-owner-cleanup.json", cleanup)
    assert Enum.all?(Map.values(cleanup))
    assert old_live == 0 and new_live == 16

    assert active_exact <= 16,
           "capacity16 must cover actual old+replacement transport workers across KeyOwner replacement; observed #{active_exact}"
  end

  test "pinned_start_child_refuses_supervisor_death_and_stale_owner_before_admission" do
    Enum.each([:supervisor_dies, :owner_dies], &startup_case/1)
  end

  defp startup_case(mode) do
    Process.put(:case_name, Atom.to_string(mode))
    fixture = start_supervised!({TLSFixture, []})
    %{ip: ip, port: port, ca: ca} = GenServer.call(fixture, :authority)
    source = identity([ca])
    assert {:ok, config} = Config.load(browser_env(), :api, source)
    assert {:ok, settings} = ProviderTrustConfig.new(config, source)

    browser =
      start_supervised!(%{
        id: :browser_component,
        start:
          {KeyOwnerSupervisor, :start_fixture,
           [settings.owner_options ++ [fixture: %{ip: ip, port: port}]]},
        type: :supervisor,
        shutdown: :infinity
      })

    owner = Process.whereis(@owner)
    owner_state = :sys.get_state(owner)
    table = owner_state.table
    fetch = Process.whereis(@workers)

    transport =
      start_supervised!({MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport, self()})

    :ok = TLSFixture.configure(fixture, {:raw, raw(jwks("startup"), 120)})
    provider = start_provider(config, transport)
    :erlang.trace(fetch, true, [:procs, {:tracer, self()}])
    :ok = :sys.suspend(browser)
    :ok = :sys.suspend(fetch)

    try do
      d = deadline()
      {caller, cm} = async_exchange(config, d)

      wait_until(
        fn ->
          {:messages, messages} = Process.info(fetch, :messages)

          Enum.any?(messages, fn
            {:"$gen_call", {pid, _}, {:start_child, _}} -> pid == provider
            _ -> false
          end)
        end,
        System.monotonic_time(:millisecond) + 1_000
      )

      assert slots(table) == []
      target = if mode == :supervisor_dies, do: fetch, else: owner
      tm = Process.monitor(target)
      Process.exit(target, :kill)
      assert_receive {:DOWN, ^tm, :process, ^target, :killed}, 1_000

      worker =
        if mode == :owner_dies do
          :ok = :sys.resume(fetch)
          assert_receive {:trace, ^fetch, :spawn, spawned, _}, 1_000
          wm = Process.monitor(spawned)
          assert_receive {:DOWN, ^wm, :process, ^spawned, _}, 1_000
          refute Process.alive?(spawned)
          assert DynamicSupervisor.count_children(fetch).active == 0
          assert :ets.info(table) == :undefined
          spawned
        else
          assert Process.alive?(owner)
          assert slots(table) == []
          nil
        end

      assert_receive {:exchange_result, ^caller, {:error, :provider_unavailable}}, 1_000
      send(caller, :done)
      assert_receive {:DOWN, ^cm, :process, ^caller, :normal}, 1_000
      assert Process.alive?(provider)
      assert :sys.get_state(provider).tickets == %{}
      refute_receive {:actual_transport, _, _}, 30
      assert :ok = :sys.resume(browser)

      wait_until(
        fn ->
          p = Process.whereis(@owner)
          is_pid(p) and p != owner
        end,
        System.monotonic_time(:millisecond) + 1_000
      )

      replacement = Process.whereis(@owner)
      new_table = :sys.get_state(replacement).table
      replacement_fetch = Process.whereis(@workers)
      assert replacement_fetch != fetch
      refute Process.alive?(fetch)
      refute Process.alive?(owner)
      assert slots(new_table) == []
      assert {:ok, _, _, ticket} = exchange(config, d)
      assert_receive {:actual_transport, new_worker, _}, 1_000
      wm = Process.monitor(new_worker)
      assert :ok = ProviderOwner.finish(ticket, config, d)
      assert_receive {:DOWN, ^wm, :process, ^new_worker, _}, 1_000
      refute Process.alive?(new_worker)
      empty(new_table)
      full_capacity(@owner)
      assert DynamicSupervisor.count_children(replacement_fetch).active == 0
      assert :ok = stop_supervised(:provider)

      wait_until(
        fn ->
          i = TLSFixture.info(fixture)
          i.accepted == i.closed and map_size(i.sockets) == 0
        end,
        System.monotonic_time(:millisecond) + 1_000
      )

      info = TLSFixture.info(fixture)
      assert info.accepted == 1 and info.closed == 1
      assert :ok = stop_supervised(:browser_component)

      assert :ok =
               stop_supervised(MixerHosted.BrowserAuth.ProviderOwnerLifecycleTest.RawTransport)

      assert :ok = stop_supervised(TLSFixture)

      cleanup = %{
        provider_dead: not Process.alive?(provider),
        browser_dead: not Process.alive?(browser),
        old_owner_dead: not Process.alive?(owner),
        new_owner_dead: not Process.alive?(replacement),
        old_fetch_dead: not Process.alive?(fetch),
        new_fetch_dead: not Process.alive?(replacement_fetch),
        transport_dead: not Process.alive?(transport),
        fixture_dead: not Process.alive?(fixture),
        both_tables_deleted:
          :ets.info(table) == :undefined and :ets.info(new_table) == :undefined,
        no_names:
          Process.whereis(@owner) == nil and Process.whereis(@workers) == nil and
            Process.whereis(ProviderOwner) == nil,
        exact_workers_dead:
          not Process.alive?(new_worker) and (worker == nil or not Process.alive?(worker)),
        loopback_closed: info.accepted == info.closed
      }

      save("startup-observations.json", %{
        mode: mode,
        queued_start_child_pinned_provider: inspect(provider),
        pinned_owner: inspect(owner),
        pinned_fetch: inspect(fetch),
        stale_worker: inspect(worker),
        stale_worker_DOWN: mode == :owner_dies,
        provider_survived: true,
        no_raw_request_before_restart: true,
        no_live_permit_released: true,
        replacement_exchange_and_finish: true,
        temporary_children_not_restarted: true,
        original_deadline_unextended: true,
        cleanup: cleanup
      })

      assert Enum.all?(Map.values(cleanup))
    after
      if Process.alive?(browser), do: :sys.resume(browser)
      if Process.alive?(fetch), do: :sys.resume(fetch)
    end
  end
end
