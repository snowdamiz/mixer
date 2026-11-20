Code.require_file("test/mixer_hosted/browser_auth/customer_build_inputs_http_sql_test.exs")

defmodule MixerHosted.CombinedCheckoutReleaseTest do
  use MixerHosted.CustomerBuildInputsFixture, create: true
  alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner}

  @event [:mixer_hosted, :browser_auth, :store, :transaction]
  @admitted "combined-admitted"
  @refused "combined-refused"

  def observe(
        @event,
        _,
        %{repo: LifecycleRepo, query: "begin", result: {:ok, %Postgrex.Result{command: :begin}}},
        {parent, barrier}
      ) do
    if :ets.insert_new(barrier, {:admitted, self()}) do
      send(parent, :admitted_begin)

      receive do
        {:release_begin, ^barrier} -> :ok
      after
        4000 -> send(parent, :admitted_begin_timed_out)
      end
    end
  end

  def observe(
        @event,
        %{queue_time: time, total_time: time} = measurements,
        %{
          repo: LifecycleRepo,
          query: "begin",
          result:
            {:error,
             %DBConnection.ConnectionError{
               reason: :error,
               message: "connection not available and queuing is disabled"
             }}
        },
        {parent, _}
      )
      when is_integer(time) and time >= 0 and map_size(measurements) == 2 do
    send(parent, {:refused_before_begin, time})
  end

  def observe(_, _, _, _), do: :ok

  @tag :l07_combined_checkout_release
  test "signed release delivery holds during one authenticated build checkout refusal", c do
    IO.puts(
      "L07_LISTENERS " <>
        Jason.encode!(%{
          phoenix: c.http_port,
          issuer: c.provider_port,
          jwks: c.identity.owner_options[:fixture].port
        })
    )

    {cookie, csrf} = login(c)
    seed_input("fieldlog", "ios", "combined-input")

    F.q!(
      Admin,
      "INSERT INTO mixer_authz_applications VALUES('org-b','project-b','fieldlog',true)"
    )

    F.q!(
      Admin,
      """
      INSERT INTO mixer_customer_build_inputs
      SELECT 'org-b','project-b',application_id,platform,input_id,source_kind,
             source_reference,source_sha256,toolchain_lock_sha256,build_definition_sha256,
             max_attempts,timeout_ms,retry_backoff_ms
      FROM mixer_customer_build_inputs WHERE organization_id='org-a'
      """
    )

    assert [[false]] =
             F.q!(
               Admin,
               "SELECT EXISTS(SELECT 1 FROM mixer_authz_memberships WHERE principal_id='person-1' AND organization_id='org-b')"
             ).rows

    listed = http(c, list_path(), headers(cookie))
    assert listed.status == 200
    [input] = Jason.decode!(listed.body)["inputs"]
    body = create_body(input)
    assert counts() == {[[0]], [[0]]}

    initial = RuntimeOwner.status()
    assert initial.phase == :storage_ready
    owner = Process.whereis(RuntimeOwner)
    endpoint = Process.whereis(MixerHostedWeb.Endpoint)
    %{pid: pool} = Ecto.Adapter.lookup_meta(LifecycleRepo)

    assert [%{ready_conn_count: 2, checkout_queue_length: 0}] =
             DBConnection.get_connection_metrics(pool)

    baseline = release_snapshot()
    assert baseline.offer == File.read!(System.fetch_env!("L07_EXPECTED_OFFER"))
    assert baseline.artifact == File.read!(System.fetch_env!("L07_EXPECTED_ARTIFACT"))

    parent = self()
    barrier = :ets.new(:combined_begin, [:public])
    observer = make_ref()
    :ok = :telemetry.attach(observer, @event, &__MODULE__.observe/4, {parent, barrier})
    on_exit(fn -> :telemetry.detach(observer) end)

    holder =
      Task.async(fn ->
        LifecycleRepo.checkout(
          fn ->
            send(parent, :held_checkout)

            receive do
              :release_checkout -> :released
            after
              5000 -> raise "checkout fixture timed out"
            end
          end,
          queue: false,
          timeout: 6000
        )
      end)

    assert_receive :held_checkout, 1000
    admitted = Task.async(fn -> post(c, cookie, csrf, @admitted, body) end)

    {during, refused, queue_time} =
      try do
        assert_receive :admitted_begin, 1000

        assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
                 DBConnection.get_connection_metrics(pool)

        response = post(c, cookie, csrf, @refused, body)
        assert response.status == 503
        assert response_header(response, "set-cookie") == []
        assert_receive {:refused_before_begin, time}

        snapshot = release_snapshot()
        assert snapshot == baseline

        assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
                 DBConnection.get_connection_metrics(pool)

        assert Task.yield(admitted, 0) == nil
        refute_received :admitted_begin_timed_out
        assert RuntimeOwner.status() == initial
        assert counts() == {[[0]], [[0]]}
        rehearse_alert(response.status)
        IO.puts("L07_CHECKPOINT refused before BEGIN, signed bytes matched during checkout")
        {snapshot, response.status, time}
      after
        case :ets.lookup(barrier, :admitted) do
          [{:admitted, pid}] -> send(pid, {:release_begin, barrier})
          [] -> :ok
        end

        send(holder.pid, :release_checkout)
        assert Task.await(holder, 1000) == :released
      end

    response = Task.await(admitted, 3000)
    assert response.status == 201
    refute_received :admitted_begin_timed_out

    assert [%{ready_conn_count: 2, checkout_queue_length: 0}] =
             DBConnection.get_connection_metrics(pool)

    assert counts() == {[[1]], [[1]]}
    admitted_selection = Jason.decode!(response.body)["selection"]

    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    assert %{"state" => "authenticated", "csrf_token" => ^csrf} = Jason.decode!(session.body)
    assert response_header(session, "set-cookie") == []

    admitted_replay = post(c, cookie, csrf, @admitted, body)
    assert admitted_replay.status == 200
    assert Jason.decode!(admitted_replay.body)["selection"] == admitted_selection
    assert counts() == {[[1]], [[1]]}

    retry = post(c, cookie, csrf, @refused, body)
    assert retry.status == 201
    retried_selection = Jason.decode!(retry.body)["selection"]
    refute retried_selection["build_id"] == admitted_selection["build_id"]
    assert counts() == {[[2]], [[2]]}

    replay = post(c, cookie, csrf, @refused, body)
    assert replay.status == 200
    assert Jason.decode!(replay.body)["selection"] == retried_selection

    foreign = %{organization_id: "org-b", project_id: "project-b"}
    denied = http(c, list_path(foreign), headers(cookie))
    assert denied.status == 404
    denied_create = post(c, cookie, csrf, "combined-foreign", Map.merge(body, foreign))
    assert denied_create.status == 404
    assert counts() == {[[2]], [[2]]}

    builds =
      F.q!(
        Admin,
        "SELECT organization_id, project_id, build_id, id::text FROM mixer_builds ORDER BY build_id"
      ).rows

    jobs =
      F.q!(
        Admin,
        """
        SELECT queue, state, attempt, args->>'organization_id', args->>'project_id',
               args->>'build_id', args->>'build_record_id'
        FROM oban_jobs ORDER BY args->>'build_id'
        """
      ).rows

    assert Enum.map(builds, fn ["org-a", "project-a", build, id] ->
             ["builds", "available", 0, "org-a", "project-a", build, id]
           end) == jobs

    assert [] =
             F.q!(
               Admin,
               "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'mixer_billing_%'"
             ).rows

    assert c.hosted.role == :api
    assert c.hosted.oban[:queues] == false
    assert RuntimeOwner.status() == initial
    assert Process.whereis(RuntimeOwner) == owner
    assert Process.whereis(MixerHostedWeb.Endpoint) == endpoint
    assert {:ok, {{127, 0, 0, 1}, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    assert port == c.http_port
    leases_clean()

    recovered = release_snapshot()
    assert recovered == baseline

    IO.puts(
      "L07_COMBINED " <>
        Jason.encode!(%{
          phoenix_port: port,
          issuer_port: c.provider_port,
          jwks_port: c.identity.owner_options[:fixture].port,
          phase: initial.phase,
          generation: initial.generation,
          same_owner_listener_cookie_and_csrf: true,
          connected_idle_before_during_after: [2, 0, 2],
          builds_and_jobs_at_checkpoints: [[0, 0], [0, 0], [1, 1], [1, 1], [2, 2], [2, 2]],
          admitted_status: response.status,
          refused_status: refused,
          refused_before_begin_queue_time_native: queue_time,
          session_status: session.status,
          admitted_replay_status: admitted_replay.status,
          exact_key_retry_status: retry.status,
          retry_replay_status: replay.status,
          cross_membership_statuses: [denied.status, denied_create.status],
          jobs_one_per_build: true,
          billing_tables: 0,
          billing_jobs: 0,
          compiler_starts: 0,
          outstanding_lifecycle_leases: 0,
          signed_release: Enum.map([baseline, during, recovered], &snapshot_digests/1)
        })
    )
  end

  defp rehearse_alert(status) do
    if directory = System.get_env("L07_LOCAL_ALERT_DIR") do
      event = Jason.encode!(%{code: "build_checkout_unavailable", http_status: status})
      pending = Path.join(directory, "alert.tmp")
      File.write!(pending, event, [:exclusive])
      File.rename!(pending, Path.join(directory, "alert.json"))

      await_acknowledgment(
        Path.join(directory, "ack"),
        System.monotonic_time(:millisecond) + 1500
      )
    end
  end

  defp await_acknowledgment(path, deadline) do
    unless File.regular?(path) do
      assert System.monotonic_time(:millisecond) < deadline, "test alert acknowledgment timed out"
      Process.sleep(20)
      await_acknowledgment(path, deadline)
    end
  end

  defp release_snapshot do
    %{
      offer: release_get!("L07_RELEASE_OFFER_URL"),
      artifact: release_get!("L07_RELEASE_ARTIFACT_URL")
    }
  end

  defp release_get!(variable) do
    url = System.fetch_env!(variable) |> String.to_charlist()

    assert {:ok, {{_, 200, _}, _, bytes}} =
             :httpc.request(
               :get,
               {url, []},
               [autoredirect: false, connect_timeout: 750, timeout: 1000],
               body_format: :binary
             )

    bytes
  end

  defp snapshot_digests(snapshot) do
    Map.new(snapshot, fn {key, raw} ->
      {key,
       %{bytes: byte_size(raw), sha256: Base.encode16(:crypto.hash(:sha256, raw), case: :lower)}}
    end)
  end
end
