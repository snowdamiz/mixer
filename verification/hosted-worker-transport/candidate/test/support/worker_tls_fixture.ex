defmodule MixerHosted.Test.WorkerTLSFixture do
  @moduledoc false
  use GenServer

  def material do
    dir =
      Path.join(
        System.tmp_dir!(),
        "mixer-worker-tls-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      )

    File.mkdir!(dir)
    File.chmod!(dir, 0o700)

    material =
      try do
        {_, 0} =
          System.cmd(
            "openssl",
            [
              "req",
              "-x509",
              "-newkey",
              "ec",
              "-pkeyopt",
              "ec_paramgen_curve:P-256",
              "-nodes",
              "-keyout",
              dir <> "/ca.key",
              "-out",
              dir <> "/ca.pem",
              "-days",
              "1",
              "-subj",
              "/CN=Mixer Worker Synthetic CA"
            ], stderr_to_stdout: true)

        {_, 0} =
          System.cmd(
            "openssl",
            [
              "req",
              "-new",
              "-newkey",
              "ec",
              "-pkeyopt",
              "ec_paramgen_curve:P-256",
              "-nodes",
              "-keyout",
              dir <> "/key.pem",
              "-out",
              dir <> "/leaf.csr",
              "-subj",
              "/CN=worker.fixture.invalid"
            ], stderr_to_stdout: true)

        File.write!(
          dir <> "/leaf.ext",
          "subjectAltName=DNS:worker.fixture.invalid\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n"
        )

        {_, 0} =
          System.cmd(
            "openssl",
            [
              "x509",
              "-req",
              "-in",
              dir <> "/leaf.csr",
              "-CA",
              dir <> "/ca.pem",
              "-CAkey",
              dir <> "/ca.key",
              "-CAcreateserial",
              "-out",
              dir <> "/cert.pem",
              "-days",
              "1",
              "-extfile",
              dir <> "/leaf.ext"
            ], stderr_to_stdout: true)

        [{_, cert, _}] = :public_key.pem_decode(File.read!(dir <> "/cert.pem"))
        [{kind, key, _}] = :public_key.pem_decode(File.read!(dir <> "/key.pem"))
        [{_, ca, _}] = :public_key.pem_decode(File.read!(dir <> "/ca.pem"))
        %{cert: cert, ca: ca, key: {kind, key}}
      after
        File.rm_rf!(dir)
      end

    Map.put(material, :key_dir_removed, not File.exists?(dir))
  end

  def start_link({material, mode}), do: GenServer.start_link(__MODULE__, {material, mode})
  def info(pid), do: GenServer.call(pid, :info)

  def init({material, mode}) do
    Process.flag(:trap_exit, true)

    {:ok, listener} =
      :ssl.listen(0, [
        :binary,
        active: false,
        backlog: 128,
        ip: {127, 0, 0, 1},
        cert: material.cert,
        key: material.key,
        reuseaddr: true,
        versions: [:"tlsv1.2", :"tlsv1.3"],
        alpn_preferred_protocols: ["http/1.1"]
      ])

    {:ok, {_, port}} = :ssl.sockname(listener)
    owner = self()
    acceptor = spawn_link(fn -> accept(listener, owner, mode) end)

    {:ok,
     %{
       listener: listener,
       port: port,
       acceptor: acceptor,
       active: MapSet.new(),
       accepted: 0,
       closed: 0,
       requests: [],
       mode: mode
     }}
  end

  def handle_call(:info, _, s),
    do: {:reply, Map.take(s, [:port, :accepted, :closed, :requests, :active]), s}

  def handle_info({:accepted, pid}, s),
    do: {:noreply, %{s | accepted: s.accepted + 1, active: MapSet.put(s.active, pid)}}

  def handle_info({:request, request, headers, pid}, s),
    do: {:noreply, %{s | requests: [{request, headers, pid} | s.requests]}}

  def handle_info({:closed, pid}, s),
    do: {:noreply, %{s | closed: s.closed + 1, active: MapSet.delete(s.active, pid)}}

  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}

  def terminate(_, s) do
    :ssl.close(s.listener)
    Process.exit(s.acceptor, :kill)
    Enum.each(s.active, &Process.exit(&1, :kill))
  end

  defp accept(listener, owner, mode) do
    case :ssl.transport_accept(listener, 200) do
      {:ok, socket} ->
        pid =
          spawn_link(fn ->
            receive do
              :go -> serve(socket, owner, mode)
            end
          end)

        :ok = :ssl.controlling_process(socket, pid)
        send(owner, {:accepted, pid})
        send(pid, :go)
        accept(listener, owner, mode)

      {:error, :timeout} ->
        accept(listener, owner, mode)

      _ ->
        :ok
    end
  end

  defp serve(socket, owner, mode) do
    try do
      if match?({:handshake_barrier, _}, mode) do
        {:handshake_barrier, recipient} = mode
        send(recipient, {:worker_fixture_handshake, self()})

        receive do
          :release_handshake -> :ok
        after
          6_000 -> :ok
        end
      end

      with {:ok, socket} <- :ssl.handshake(socket, 6_000), {:ok, bytes} <- read(socket, "") do
        [headers, body] = String.split(bytes, "\r\n\r\n", parts: 2)
        request = Jason.decode!(body)
        send(owner, {:request, request, headers, self()})
        raw = response(request)

        case mode do
          :normal ->
            :ssl.send(socket, raw)

          :stall ->
            :ssl.recv(socket, 1, 6_000)

          :no_eof ->
            :ssl.send(socket, raw)
            :ssl.recv(socket, 1, 6_000)

          {:raw, fun} ->
            :ssl.send(socket, fun.(request, raw))

          {:drip, delay} ->
            Enum.each(:binary.bin_to_list(raw), fn byte ->
              :ssl.send(socket, <<byte>>)
              Process.sleep(delay)
            end)

          {:notify, recipient} ->
            send(recipient, {:worker_fixture_request, self()})
            :ssl.recv(socket, 1, 6_000)

          {:handshake_barrier, _} ->
            :ssl.send(socket, raw)

          {:last_byte, recipient} ->
            n = byte_size(raw) - 1
            <<prefix::binary-size(^n), last>> = raw
            :ssl.send(socket, prefix)
            send(recipient, {:worker_fixture_final_byte, self()})

            receive do
              :release_final_byte -> :ssl.send(socket, <<last>>)
            after
              6_000 -> :ok
            end

          {:one_byte, recipient} ->
            :ssl.send(
              socket,
              "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 1\r\nConnection: close\r\n\r\n0"
            )

            send(recipient, {:worker_fixture_one_byte, self()})

            receive do
              :release_eof -> :ok
            after
              6_000 -> :ok
            end
        end
      end
    after
      :ssl.close(socket)
      send(owner, {:closed, self()})
    end
  end

  defp read(socket, bytes) when byte_size(bytes) <= 24_576 do
    case :binary.split(bytes, "\r\n\r\n") do
      [headers, body] ->
        [_, length] = Regex.run(~r/\r\ncontent-length: ([0-9]+)/i, "\r\n" <> headers)

        if byte_size(body) == String.to_integer(length),
          do: {:ok, bytes},
          else: more(socket, bytes)

      _ ->
        more(socket, bytes)
    end
  end

  defp read(_, _), do: :error

  defp more(socket, bytes) do
    with {:ok, more} <- :ssl.recv(socket, 0, 6_000), do: read(socket, bytes <> more)
  end

  def response(request, observation \\ %{"status" => "absent"}) do
    body =
      request
      |> Map.drop(["spec", "deadline_ms"])
      |> Map.put("observation", observation)
      |> Jason.encode!()

    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: #{byte_size(body)}\r\nConnection: close\r\n\r\n" <>
      body
  end
end

defmodule MixerHosted.Test.WorkerData do
  alias MixerHosted.Builds.{Dispatch, Lifecycle, WorkerConfig}

  def request do
    ref = %Lifecycle.WorkerRef{
      organization_id: "org",
      project_id: "project",
      application_id: "app",
      build_id: "build",
      platform: :ios,
      attempt: 1,
      fence: 9_223_372_036_854_775_807
    }

    record = "12345678-1234-1234-1234-123456789abc"

    identity = [
      "mixer-build-operation-v1",
      record,
      ref.organization_id,
      ref.project_id,
      ref.application_id,
      ref.build_id,
      "ios",
      1,
      ref.fence
    ]

    id = :crypto.hash(:sha256, Jason.encode!(identity)) |> Base.encode16(case: :lower)

    %Dispatch.Request{
      operation_id: id,
      ref: ref,
      spec: %Lifecycle.Spec{
        organization_id: "org",
        project_id: "project",
        application_id: "app",
        build_id: "build",
        platform: :ios,
        source: %{
          kind: :revision,
          sha256: String.duplicate("1", 64),
          reference: "opaque-λ-\\\"-reference"
        },
        toolchain_lock_sha256: String.duplicate("2", 64),
        build_definition_sha256: String.duplicate("3", 64)
      },
      deadline_ms: 9_223_372_036_854_775_807,
      guard: %{
        record_id: record,
        revision: 4,
        owner_id: "coordinator",
        epoch: 9_223_372_036_854_775_807,
        expires_at:
          DateTime.from_unix!(System.system_time(:microsecond) + 30_000_123, :microsecond)
      }
    }
  end

  def environment do
    %{
      "MIXER_BUILD_WORKER_MODE" => "configured",
      "MIXER_BUILD_WORKER_TOKEN" => Base.url_encode64(:binary.copy(<<137>>, 32), padding: false),
      "MIXER_BUILD_WORKER_CONFIG" =>
        Jason.encode!(%{
          "version" => 1,
          "endpoint" => %{
            "host" => "worker.fixture.invalid",
            "port" => 443,
            "path" => "/internal/mixer-build-worker/v1"
          },
          "environment_id" => "development",
          "pool_id" => "native",
          "controller_id" => "controller-1",
          "platforms" => ["ios", "android"],
          "resolvers" => ["1.1.1.1"]
        })
    }
  end

  def config(root), do: WorkerConfig.load!(environment(), :processor, [root])
end
