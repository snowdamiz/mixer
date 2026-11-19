defmodule MixerHosted.Builds.NativeDevelopmentDispatchTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Dispatch, NativeDevelopmentDispatch, RetainedNativeArtifacts}
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
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

  test "preflight failure completes without querying native artifacts", %{request: request} do
    sha = String.duplicate("b", 64)
    reply = %{"status" => "preflight_failed", "diagnostic_sha256" => sha}

    for {action, callback} <- [
          {"query", &NativeDevelopmentDispatch.query_completion/1},
          {"ensure_started", &NativeDevelopmentDispatch.ensure_started/1}
        ] do
      with_peer(action, reply, fn ->
        assert {:ok,
                {:completed,
                 %{
                   outcome: :failed,
                   class: :unknown,
                   code: :unknown_failure,
                   diagnostic_sha256: ^sha
                 }}} =
                 Dispatch.observation(request, callback.(request))
      end)
    end

    with_peer("query", %{reply | "diagnostic_sha256" => "malformed"}, fn ->
      assert NativeDevelopmentDispatch.query_completion(request) == {:error, :uncertain}
    end)
  end

  test "an authenticated oversized native result is a definitive policy failure", %{
    request: request
  } do
    artifacts =
      Enum.map(~w(unsigned_native_binary debug_symbols resource_inventory), fn kind ->
        %{
          "kind" => kind,
          "sha256" => String.duplicate("a", 64),
          "sizeBytes" => if(kind == "unsigned_native_binary", do: 16 * 1024 * 1024 + 1, else: 10)
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

  test "bounded retained verification widens only the Android binary role", %{
    request: %{operation_id: operation}
  } do
    {tmp_dir, 0} = System.cmd("realpath", [System.tmp_dir!()])
    suffix = Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false)
    root = Path.join(String.trim_trailing(tmp_dir, "\n"), "mixer-retained-artifacts-#{suffix}")
    File.mkdir!(root)
    on_exit(fn -> File.rm_rf!(root) end)
    File.chmod!(root, 0o700)
    store = Path.join([root, operation, "native"])
    File.mkdir_p!(store)
    Application.put_env(:mixer_hosted, @key, %{retained_root: root})

    binary = sparse_artifact(store, :unsigned_native_binary, 1)
    symbols = sparse_artifact(store, :debug_symbols, 2)
    inventory = sparse_artifact(store, :resource_inventory, 3)
    ios_cap = sparse_artifact(store, :unsigned_native_binary, 16 * 1024 * 1024)
    apk = sparse_artifact(store, :unsigned_native_binary, 27_795_723)
    android_cap = sparse_artifact(store, :unsigned_native_binary, 32 * 1024 * 1024)
    over_cap = sparse_artifact(store, :unsigned_native_binary, 32 * 1024 * 1024 + 1)

    assert :ok = RetainedNativeArtifacts.verify(operation, [ios_cap, symbols, inventory])
    assert :ok = RetainedNativeArtifacts.verify(operation, :android, [apk, symbols, inventory])

    assert :ok =
             RetainedNativeArtifacts.verify(operation, :android, [android_cap, symbols, inventory])

    assert {:error, :uncertain} =
             RetainedNativeArtifacts.verify(operation, :android, [over_cap, symbols, inventory])

    assert {:error, :uncertain} =
             RetainedNativeArtifacts.verify(operation, :ios, [apk, symbols, inventory])

    assert {:error, :uncertain} =
             RetainedNativeArtifacts.verify(operation, :android, [
               binary,
               %{apk | kind: :debug_symbols},
               inventory
             ])

    assert {:error, :uncertain} =
             RetainedNativeArtifacts.verify(operation, :android, [apk, inventory, symbols])

    assert {:ok, <<0>>} = RetainedNativeArtifacts.read(operation, binary)
    assert {:error, :storage_unavailable} = RetainedNativeArtifacts.read(operation, apk)
  end

  defp sparse_artifact(store, kind, size) do
    path = Path.join(store, "fixture")

    File.open!(path, [:write, :binary, :raw], fn file ->
      {:ok, ^size} = :file.position(file, size)
      :ok = :file.truncate(file)
    end)

    digest =
      path
      |> File.stream!(64 * 1024)
      |> Enum.reduce(:crypto.hash_init(:sha256), &:crypto.hash_update(&2, &1))
      |> :crypto.hash_final()
      |> Base.encode16(case: :lower)

    destination = Path.join(store, digest)
    File.rename!(path, destination)
    File.chmod!(destination, 0o400)
    %ArtifactRef{kind: kind, size_bytes: size, sha256: digest}
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
