defmodule MixerHosted.Builds.DevelopmentDispatchTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{DevelopmentDispatch, Dispatch}
  alias MixerHosted.Builds.Dispatch.{Request, Observation}

  setup do
    previous = Application.fetch_env(:mixer_hosted, :development_dispatch)
    Application.delete_env(:mixer_hosted, :development_dispatch)

    on_exit(fn ->
      case previous do
        :error -> Application.delete_env(:mixer_hosted, :development_dispatch)
        {:ok, value} -> Application.put_env(:mixer_hosted, :development_dispatch, value)
      end
    end)

    request = %Request{
      operation_id: String.duplicate("a", 64),
      ref: %{fence: 1},
      spec: %{platform: :ios},
      deadline_ms: 1,
      guard: %{epoch: 1}
    }

    %{request: request}
  end

  test "loading transport installs no configuration or worker", %{request: r} do
    assert Application.fetch_env(:mixer_hosted, :development_dispatch) == :error

    for action <- [:query, :ensure_started, :stop] do
      assert apply(DevelopmentDispatch, action, [r]) == {:error, :unavailable}
    end

    assert Application.fetch_env(:mixer_hosted, :development_dispatch) == :error
  end

  test "incomplete explicit configuration refuses every action", %{request: r} do
    for config <- [nil, %{}, %{worker_id: "synthetic", token: "synthetic"}] do
      Application.put_env(:mixer_hosted, :development_dispatch, config)

      for action <- [:query, :ensure_started, :stop],
          do: assert(apply(DevelopmentDispatch, action, [r]) == {:error, :unavailable})
    end
  end

  test "invalid ports refuse every action without exiting", %{request: r} do
    for port <- [
          :invalid_port,
          :http,
          nil,
          true,
          -1,
          65_536,
          1_000_000,
          1.0,
          "1234",
          ~c"1234",
          %{},
          []
        ] do
      Application.put_env(:mixer_hosted, :development_dispatch, %{
        port: port,
        worker_id: "synthetic",
        token: "synthetic"
      })

      for action <- [:query, :ensure_started, :stop],
          do: assert(apply(DevelopmentDispatch, action, [r]) == {:error, :unavailable})
    end
  end

  test "malformed authentication inputs are rejected before connecting", %{request: r} do
    {:ok, listener} = :gen_tcp.listen(0, [:binary, active: false, ip: {127, 0, 0, 1}])

    try do
      {:ok, port} = :inet.port(listener)

      for {key, values} <- [
            worker_id: [nil, :worker, 7, [], %{}, "", <<255>>],
            token: [nil, :token, 7, [], %{}, "", <<255>>, "tökén"]
          ],
          value <- values do
        config = Map.put(%{port: port, worker_id: "synthetic", token: "synthetic"}, key, value)
        Application.put_env(:mixer_hosted, :development_dispatch, config)

        for action <- [:query, :ensure_started, :stop],
            do: assert(apply(DevelopmentDispatch, action, [r]) == {:error, :unavailable})
      end

      assert {:error, :timeout} = :gen_tcp.accept(listener, 20)
    after
      :gen_tcp.close(listener)
    end
  end

  test "valid explicit configuration exchanges all actions and closes each socket", %{request: r} do
    for action <- [:query, :ensure_started, :stop] do
      {:ok, listener} =
        :gen_tcp.listen(0, [:binary, active: false, packet: :line, ip: {127, 0, 0, 1}])

      try do
        {:ok, port} = :inet.port(listener)
        parent = self()

        {peer, monitor} =
          spawn_monitor(fn ->
            {:ok, socket} = :gen_tcp.accept(listener, 1_000)

            try do
              {:ok, bytes} = :gen_tcp.recv(socket, 0, 1_000)
              message = Jason.decode!(bytes)
              :ok = :gen_tcp.send(socket, "{\"status\":\"absent\"}\n")
              {:error, :closed} = :gen_tcp.recv(socket, 0, 1_000)
              send(parent, {:wire, self(), message})
            after
              :gen_tcp.close(socket)
            end
          end)

        Application.put_env(:mixer_hosted, :development_dispatch, %{
          port: port,
          worker_id: "worker-λ",
          token: "ascii-token-012345"
        })

        assert {:ok, observation} = apply(DevelopmentDispatch, action, [r])
        assert Dispatch.observation(r, {:ok, observation}) == {:ok, :absent}
        assert_receive {:wire, ^peer, message}
        assert message["action"] == Atom.to_string(action)
        assert message["worker_id"] == "worker-λ"
        assert message["token"] == "ascii-token-012345"

        assert message["request"] == %{
                 "operation_id" => r.operation_id,
                 "ref" => %{"fence" => 1},
                 "spec" => %{"platform" => "ios"},
                 "deadline_ms" => 1,
                 "guard" => %{"epoch" => 1}
               }

        assert_receive {:DOWN, ^monitor, :process, ^peer, :normal}
      after
        :gen_tcp.close(listener)
      end
    end
  end

  test "protocol observations retain exact operation and fence", %{request: r} do
    for status <- [
          :absent,
          :running,
          {:completed,
           %{
             outcome: :failed,
             class: :compiler,
             code: :compiler_error,
             diagnostic_sha256: String.duplicate("b", 64)
           }},
          {:stopped, String.duplicate("c", 64)}
        ] do
      observation = %Observation{operation_id: r.operation_id, ref: r.ref, status: status}
      assert Dispatch.observation(r, {:ok, observation}) == {:ok, status}

      assert Dispatch.observation(
               r,
               {:ok, %{observation | operation_id: String.duplicate("d", 64)}}
             ) == {:error, :invalid_observation}

      assert Dispatch.observation(r, {:ok, %{observation | ref: %{fence: 2}}}) ==
               {:error, :invalid_observation}
    end
  end

  test "protocol refuses malformed observations and preserves error categories", %{request: r} do
    for result <- [
          nil,
          {:ok, %{}},
          {:ok, %Observation{operation_id: r.operation_id, ref: r.ref, status: :succeeded}},
          {:error, :unexpected}
        ],
        do: assert(Dispatch.observation(r, result) == {:error, :invalid_observation})

    for error <- [:stale, :unavailable, :uncertain],
        do: assert(Dispatch.observation(r, {:error, error}) == {:error, error})
  end

  test "compiled application owns the complete reviewed migration priv" do
    priv = Application.app_dir(:mixer_hosted, "priv")
    assert {:ok, %{type: :symlink}} = File.lstat(priv)

    assert File.read_link!(priv) |> Path.expand(Path.dirname(priv)) ==
             Path.expand("../../../priv", __DIR__)

    migrations = Path.join(priv, "repo/migrations")
    assert Enum.sort(Enum.map(Path.wildcard(Path.join(migrations, "*.exs")), &Path.basename/1)) ==
             [
               "20261024000000_add_oban.exs",
               "20261025000000_add_build_journals.exs",
               "20261025000001_add_build_admission.exs",
               "20261025000002_add_build_aggregate_limits.exs",
               "20261025000003_add_customer_authorization.exs",
               "20261025000004_add_authorization_state_revisions.exs",
               "20261025000005_add_customer_artifact_storage.exs",
               "20261025000006_add_customer_workspace_discovery.exs",
               "20261025000007_add_browser_sessions.exs",
               "20261025000008_add_browser_activation_preparation.exs",
               "20261110000000_add_billing_webhook_inbox.exs",
               "20261110000001_add_billing_usage_ledger.exs",
               "20261116000000_add_billing_reconciliation.exs",
               "20261116000001_add_billing_organization_state.exs"
             ]
    assert :ok = MixerHosted.Test.Migrations.check_files!(migrations)
  end
end
