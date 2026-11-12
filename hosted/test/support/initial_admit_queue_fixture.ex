defmodule MixerHosted.Test.InitialAdmitQueueFixture do
  @moduledoc false
  import ExUnit.Assertions
  import ExUnit.Callbacks
  alias MixerHosted.BrowserAuth.{Installation, LifecycleRepo, ProviderOwner, RuntimeOwner}
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Ordinary

  def prepare! do
    previous = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
    isolated = Path.join(previous, "initial-admit-queue-r1494")
    File.mkdir!(isolated)
    on_exit(fn -> System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", previous) end)
    System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", isolated)
    Ordinary.prepare!()
  end

  def start_components!(c) do
    Ordinary.configure!(c, :fixture)
    start_supervised!({MixerHosted.Repo, c.hosted.repo})
    start_supervised!(Installation.identity_child(c.installation, c.identity.owner_options))
    start_supervised!({LifecycleRepo, c.runtime.lifecycle_repo})
    {:fixture, config, snapshot, transport} = c.installation.provider

    start_supervised!(%{
      id: ProviderOwner,
      start: {ProviderOwner, :start_fixture, [config, snapshot, transport]}
    })

    holders = start_supervised!({Task.Supervisor, []})

    owner_supervisor =
      start_supervised!({DynamicSupervisor, strategy: :one_for_one})

    assert LifecycleRepo.bound?(c.runtime.lifecycle_repo)
    assert pool_metrics().checkout_queue_length == 0
    %{holders: holders, owner_supervisor: owner_supervisor}
  end

  def hold_all!(supervisor) do
    observer = self()

    tasks =
      for _ <- 1..2 do
        Task.Supervisor.async_nolink(supervisor, fn ->
          LifecycleRepo.checkout(
            fn ->
              %{rows: [[backend]]} =
                Ecto.Adapters.SQL.query!(LifecycleRepo, "SELECT pg_backend_pid()", [], log: false)

              send(observer, {:lifecycle_held, self(), backend})

              receive do
                :release_lifecycle -> :released
              after
                15_000 -> raise "lifecycle holder release was not received"
              end
            end,
            timeout: 15_000,
            queue: true
          )
        end)
      end

    backends =
      for task <- tasks do
        pid = task.pid
        assert_receive {:lifecycle_held, ^pid, backend}, 5_000
        backend
      end

    assert length(Enum.uniq(backends)) == 2
    assert pool_metrics().ready_conn_count == 0
    assert pool_metrics().checkout_queue_length == 0
    tasks
  end

  def start_owner!(supervisor, runtime) do
    observer = self()

    Task.async(fn ->
      started = System.monotonic_time(:millisecond)
      send(observer, {:owner_start_attempt, started})

      result =
        DynamicSupervisor.start_child(supervisor, %{
          id: RuntimeOwner,
          start: {RuntimeOwner, :start_link, [runtime]},
          restart: :temporary
        })

      {result, started, System.monotonic_time(:millisecond)}
    end)
  end

  def queued_owner! do
    until = System.monotonic_time(:millisecond) + 2_000
    await_queue!(until)
  end

  defp await_queue!(until) do
    metrics = pool_metrics()
    owner = Process.whereis(RuntimeOwner)

    if is_pid(owner) and metrics.ready_conn_count == 0 and metrics.checkout_queue_length == 1 do
      %{owner: owner, observed_at: System.monotonic_time(:millisecond), metrics: metrics}
    else
      assert System.monotonic_time(:millisecond) < until,
             "real owner never entered the actual lifecycle checkout queue: #{inspect(metrics)}"

      Process.sleep(5)
      await_queue!(until)
    end
  end

  def pool_metrics do
    pool = Ecto.Adapter.lookup_meta(LifecycleRepo).pid
    [metrics] = DBConnection.get_connection_metrics(pool)
    metrics
  end

  def release!(task) do
    send(task.pid, :release_lifecycle)
    assert Task.await(task, 2_000) == :released
  end

  def observe_transactions! do
    table = :ets.new(__MODULE__, [:set, :public])
    :ets.insert(table, {:control, 0, false, false})
    id = {__MODULE__, make_ref()}

    :ok =
      :telemetry.attach(
        id,
        [:mixer_hosted, :browser_auth, :store, :transaction],
        &__MODULE__.transaction_event/4,
        {self(), table}
      )

    on_exit(fn -> :telemetry.detach(id) end)
    table
  end

  def transaction_event(
        [:mixer_hosted, :browser_auth, :store, :transaction],
        _,
        metadata,
        {observer, table}
      ) do
    # Telemetry runs synchronously in the emitting caller. Retain only closed classes.
    try do
      emitted_at_ms = System.monotonic_time(:millisecond)
      index = :ets.update_counter(table, :control, {2, 1, 64, 64})

      if index <= 63 do
        true =
          :ets.insert_new(
            table,
            {index, self(), emitted_at_ms, query_class(metadata), result_class(metadata)}
          )
      else
        :ets.update_element(table, :control, {3, true})
      end
    rescue
      _ -> mark_history_failed(table)
    catch
      _, _ -> mark_history_failed(table)
    end

    case metadata do
      %{query: query} when query in ["begin", "commit"] ->
        send(observer, {:store_transaction, self(), query})

      _ ->
        :ok
    end

    :ok
  end

  def transaction_event(_, _, _, _), do: :ok

  defp mark_history_failed(table) do
    try do
      :ets.update_element(table, :control, {4, true})
    rescue
      _ -> :ok
    catch
      _, _ -> :ok
    end
  end

  defp query_class(%{query: query}) when query in ["begin", "commit", "rollback"], do: query
  defp query_class(_), do: "other"

  defp result_class(%{result: {:error, %DBConnection.ConnectionError{}}}),
    do: :db_connection_error

  defp result_class(%{result: {:error, %Postgrex.Error{}}}), do: :postgrex_error
  defp result_class(%{result: {:error, _}}), do: :other_error

  defp result_class(%{result: {:ok, %Postgrex.Result{command: command, connection_id: id}}})
       when is_integer(id) and id > 0 do
    case command do
      :begin -> :begin_ack
      :commit -> :commit_ack
      :rollback -> :rollback_ack
      _ -> :unknown
    end
  end

  defp result_class(_), do: :unknown

  def transaction_history!(table, owner) do
    records =
      table
      |> :ets.match_object({:_, owner, :_, :_, :_})
      |> Enum.sort()
      |> Enum.map(fn {index, caller, emitted_at_ms, query, result_class} ->
        %{
          index: index,
          owner_matches: caller == owner,
          emitted_at_ms: emitted_at_ms,
          query: query,
          result_class: result_class
        }
      end)

    %{
      records: records,
      saturated: :ets.lookup_element(table, :control, 3),
      write_failed: :ets.lookup_element(table, :control, 4),
      observed_at_ms: System.monotonic_time(:millisecond)
    }
  end

  def persist_transaction_history!(before_release, after_release, release_started_at_ms) do
    path =
      System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
      |> Path.join("proof/initial-admit-deadline-transaction-history-r1530.json")

    evidence = %{
      schema: 1,
      event: ["mixer_hosted", "browser_auth", "store", "transaction"],
      record_limit: 63,
      table_row_limit: 64,
      expected_first_result_class: :db_connection_error,
      before_release: before_release,
      release_started_at_ms: release_started_at_ms,
      after_release: after_release
    }

    File.write!(path, Jason.encode!(evidence))
    :ok
  end

  def request(method, path, headers \\ []) do
    conn = Plug.Test.conn(method, path, "")
    MixerHostedWeb.BrowserLoginHTTP.call(%{conn | req_headers: headers}, [])
  end

  def cookie!(conn) do
    [value] = Plug.Conn.get_resp_header(conn, "set-cookie")
    [pair | _] = String.split(value, ";")
    "__Host-mixer-session=" <> cookie = pair
    assert MixerHosted.BrowserAuth.Protocol.token?(cookie)
    cookie
  end

  def authenticated_ordinary_boundary!(c) do
    preauth = request("GET", "/auth/session")
    assert preauth.status == 200
    cookie = cookie!(preauth)
    csrf = Jason.decode!(preauth.resp_body)["csrf_token"]

    headers =
      Ordinary.headers(cookie) ++
        [{"origin", c.config.public_origin}, {"x-mixer-csrf", csrf}]

    login = request("POST", "/auth/login", headers)
    assert login.status == 303
    [location] = Plug.Conn.get_resp_header(login, "location")
    uri = URI.parse(location)
    provider = Ordinary.http(%{http_port: c.provider_port}, "/authorize?" <> uri.query, [])
    assert provider.status == 302
    [callback] = Ordinary.response_header(provider, "location")

    activation =
      request("GET", "/auth/callback?" <> URI.parse(callback).query, Ordinary.headers(cookie))

    assert activation.status == 303
    active = cookie!(activation)

    result =
      request(
        "GET",
        "/console-api/v1/applications?organization_id=org-a&project_id=project-a",
        Ordinary.headers(active)
      )

    assert result.status == 200

    assert Jason.decode!(result.resp_body) == %{
             "organizationId" => "org-a",
             "projectId" => "project-a",
             "applications" => [%{"applicationId" => "fieldlog"}],
             "nextCursor" => nil
           }

    Ordinary.leases_clean()
  end
end
