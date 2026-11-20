Code.require_file("test/mixer_hosted/browser_auth/customer_build_inputs_http_sql_test.exs")

defmodule MixerHosted.MixedCheckoutRecoveryHTTPTest do
  use MixerHosted.CustomerBuildInputsFixture, create: true
  alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner}

  @event [:mixer_hosted, :browser_auth, :store, :transaction]

  def observe(
        @event,
        _,
        %{repo: LifecycleRepo, query: "begin", result: {:ok, %Postgrex.Result{command: :begin}}},
        {parent, barrier}
      ) do
    if :ets.insert_new(barrier, {:admitted, self()}) do
      send(parent, {:admitted_begin, self()})

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
    send(parent, :refused_before_begin)
  end

  def observe(_, _, _, _), do: :ok

  @tag :mixed_lifecycle_contention
  test "an admitted build commits while a bounded wave of competing checkouts is refused", c do
    {cookie, csrf} = login(c)
    seed_input("fieldlog", "ios", "mixed-checkout-input")
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

    parent = self()
    barrier = :ets.new(:http_begin, [:public])
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
    admitted = Task.async(fn -> post(c, cookie, csrf, "mixed-live-admitted", body) end)

    try do
      assert_receive {:admitted_begin, _}, 1000

      assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
               DBConnection.get_connection_metrics(pool)

      responses =
        List.duplicate("mixed-live-refused", 4)
        |> Task.async_stream(fn key -> post(c, cookie, csrf, key, body) end,
          max_concurrency: 4,
          timeout: 2000
        )
        |> Enum.map(fn {:ok, response} -> response end)

      assert Enum.map(responses, & &1.status) == [503, 503, 503, 503]

      for response <- responses do
        assert response_header(response, "set-cookie") == []
        assert_receive :refused_before_begin
      end

      assert RuntimeOwner.status() == initial
      assert counts() == {[[0]], [[0]]}
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
    %{"selection" => admitted_selection} = Jason.decode!(response.body)
    assert counts() == {[[1]], [[1]]}

    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    assert %{"state" => "authenticated", "csrf_token" => ^csrf} = Jason.decode!(session.body)
    assert response_header(session, "set-cookie") == []

    replay = post(c, cookie, csrf, "mixed-live-admitted", body)
    assert replay.status == 200
    assert Jason.decode!(replay.body)["selection"] == admitted_selection

    retry = post(c, cookie, csrf, "mixed-live-refused", body)
    assert retry.status == 201
    %{"selection" => retried_selection} = Jason.decode!(retry.body)
    refute retried_selection["build_id"] == admitted_selection["build_id"]
    replay = post(c, cookie, csrf, "mixed-live-refused", body)
    assert replay.status == 200
    assert Jason.decode!(replay.body)["selection"] == retried_selection
    assert counts() == {[[2]], [[2]]}

    denied =
      http(c, list_path(%{organization_id: "org-b", project_id: "project-b"}), headers(cookie))

    assert denied.status == 404
    assert RuntimeOwner.status() == initial
    assert Process.whereis(RuntimeOwner) == owner
    assert Process.whereis(MixerHostedWeb.Endpoint) == endpoint
    leases_clean()

    IO.puts(
      "MIXED_CHECKOUT_READY " <>
        Jason.encode!(%{
          phases: [initial.phase, RuntimeOwner.status().phase],
          generation: initial.generation,
          httpPort: c.http_port,
          admittedStatus: response.status,
          refusedCount: 4,
          retryStatus: retry.status,
          builds: 2,
          jobs: 2
        })
    )
  end
end
