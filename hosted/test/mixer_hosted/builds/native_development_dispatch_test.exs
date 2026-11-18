defmodule MixerHosted.Builds.NativeDevelopmentDispatchTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Dispatch, Lifecycle, NativeDevelopmentDispatch}
  alias MixerHosted.Builds.Dispatch.Request

  @key :native_development_dispatch
  @secret String.duplicate("private-test-key", 4)

  setup do
    previous = Application.fetch_env(:mixer_hosted, @key)
    Application.delete_env(:mixer_hosted, @key)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, @key, value)
        :error -> Application.delete_env(:mixer_hosted, @key)
      end
    end)

    %{
      request: %Request{
        operation_id: String.duplicate("a", 64),
        ref: %{fence: 1},
        spec: %{platform: :ios},
        deadline_ms: 1,
        guard: %{epoch: 1}
      }
    }
  end

  test "dispatch is opt-in", %{request: request} do
    assert NativeDevelopmentDispatch.query(request) == {:error, :unavailable}
    assert NativeDevelopmentDispatch.native_artifacts(request) == {:error, :unavailable}
  end

  test "authenticates both directions and binds the coordinator observation", %{request: request} do
    with_peer("query", %{"status" => "running"}, fn ->
      assert Dispatch.observation(request, NativeDevelopmentDispatch.query(request)) ==
               {:ok, :running}
    end)
  end

  test "rejects forged or replayed observations", %{request: request} do
    with_peer(
      "stop",
      %{"status" => "stopped", "diagnostic_sha256" => String.duplicate("b", 64)},
      fn ->
        assert NativeDevelopmentDispatch.stop(request) == {:error, :uncertain}
      end,
      :wrong_nonce
    )
  end

  test "accepts exactly the three scoped artifact descriptors", %{request: request} do
    artifacts =
      Enum.map(~w(unsigned_native_binary debug_symbols resource_inventory), fn kind ->
        %{"kind" => kind, "sha256" => String.duplicate("a", 64), "sizeBytes" => 10}
      end)

    with_peer("artifacts", %{"status" => "native_ready", "artifacts" => artifacts}, fn ->
      assert NativeDevelopmentDispatch.native_artifacts(request) == {:ok, artifacts}
    end)

    with_peer(
      "artifacts",
      %{"status" => "native_ready", "artifacts" => List.duplicate(hd(artifacts), 3)},
      fn ->
        assert NativeDevelopmentDispatch.native_artifacts(request) == {:error, :uncertain}
      end
    )
  end

  test "an authenticated oversized native result is a definitive policy failure", %{
    request: request
  } do
    artifacts =
      Enum.map(~w(unsigned_native_binary debug_symbols resource_inventory), fn kind ->
        %{
          "kind" => kind,
          "sha256" => String.duplicate("a", 64),
          "sizeBytes" => Lifecycle.native_artifact_max_bytes() + 1
        }
      end)

    with_peers(
      [
        {"query", %{"status" => "running"}},
        {"artifacts", %{"status" => "native_ready", "artifacts" => artifacts}}
      ],
      fn ->
        assert {:ok, {:completed, %{outcome: :failed, class: :policy, code: :policy_rejection}}} =
                 Dispatch.observation(
                   request,
                   NativeDevelopmentDispatch.query_completion(request)
                 )
      end,
      :valid
    )
  end

  defp with_peer(action, reply, fun, signature \\ :valid) do
    with_peers([{action, reply}], fun, signature)
  end

  defp with_peers(replies, fun, signature) do
    {:ok, listener} =
      :gen_tcp.listen(0, [:binary, active: false, packet: :line, ip: {127, 0, 0, 1}])

    {:ok, port} = :inet.port(listener)

    Application.put_env(:mixer_hosted, @key, %{port: port, worker_id: "local", token: @secret})

    {pid, monitor} =
      spawn_monitor(fn ->
        for {action, reply} <- replies do
          {:ok, connection} = :gen_tcp.accept(listener, 1_000)
          {:ok, bytes} = :gen_tcp.recv(connection, 0, 1_000)
          %{"nonce" => nonce, "body" => body, "mac" => mac} = Jason.decode!(bytes)
          assert not String.contains?(bytes, @secret)
          assert mac == hmac("request", nonce, body)

          assert %{
                   "action" => ^action,
                   "worker_id" => "local",
                   "request" => %{"ref" => %{"fence" => 1}}
                 } =
                   Jason.decode!(body)

          body = Jason.encode!(reply)
          signing_nonce = if signature == :valid, do: nonce, else: String.duplicate("0", 32)
          mac = hmac("response", signing_nonce, body)
          :ok = :gen_tcp.send(connection, Jason.encode!(%{body: body, mac: mac}) <> "\n")
          :ok = :gen_tcp.close(connection)
        end
      end)

    try do
      fun.()
      assert_receive {:DOWN, ^monitor, :process, ^pid, :normal}
    after
      :gen_tcp.close(listener)
    end
  end

  defp hmac(direction, nonce, body) do
    :crypto.mac(:hmac, :sha256, @secret, direction <> "\n" <> nonce <> "\n" <> body)
    |> Base.encode16(case: :lower)
  end
end
