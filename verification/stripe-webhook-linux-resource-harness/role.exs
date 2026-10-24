# Private standalone role: no MixerHosted.Application, provider, database, or
# production route is started. Runtime mode is minted by the controller only.
Code.prepend_paths(Path.wildcard("/opt/mixer/release/lib/*/ebin"))

defmodule MixerHarness.Control do
  @on_load :load
  def load, do: :erlang.load_nif(~c"/opt/harness/control_nif", 0)
  def secure_role, do: :erlang.nif_error(:not_loaded)
  def receive_control, do: :erlang.nif_error(:not_loaded)
  def send_control(_), do: :erlang.nif_error(:not_loaded)
end

defmodule MixerHarness.State do
  use Agent
  def start do
    Agent.start_link(fn -> %{open: true, captures: 0, failures: 0, owners: [], expected: nil} end,
      name: __MODULE__)
  end
  def expected(body, signatures) do
    Agent.update(__MODULE__, &Map.put(&1, :expected,
      {byte_size(body), :crypto.hash(:sha256, body), signatures}))
  end
  def enter(pid) do
    Agent.get_and_update(__MODULE__, fn s ->
      {s.open, %{s | owners: Enum.uniq([pid | s.owners])}}
    end)
  end
  def captured(body, signatures) do
    Agent.update(__MODULE__, fn s ->
      exact = s.expected == {byte_size(body), :crypto.hash(:sha256, body), signatures}
      %{s | captures: s.captures + 1, failures: s.failures + if(exact, do: 0, else: 1)}
    end)
  end
  def snapshot, do: Agent.get(__MODULE__, &Map.take(&1, [:captures, :failures, :owners, :open]))
  def close, do: Agent.update(__MODULE__, &%{&1 | open: false})
end

defmodule MixerHarness.Plug do
  def init(opts), do: opts
  def call(conn, _) do
    if MixerHarness.State.enter(self()) do
      try do
        case MixerHosted.Billing.WebhookTransport.capture(conn) do
          {:ok, captured, latest} ->
            MixerHarness.State.captured(captured.raw_body, captured.signature_header_values)
            Plug.Conn.send_resp(latest, 418, "")
          {:error, _, latest} ->
            Plug.Conn.send_resp(latest, 400, "")
        end
      after
        MixerHosted.Billing.WebhookTransport.dispose()
      end
    else
      Plug.Conn.send_resp(conn, 503, "")
    end
  end
end

defmodule MixerHarness.Role do
  @implemented ~w(R03 R09 R10 R11 R12 R13 R15 R16 R17)
  def emit(event, values) do
    IO.binwrite(:stdio, Jason.encode!(Map.merge(%{schema: 1, event: event}, values)) <> "\n")
  end
  def assert(true), do: :ok
  def assert(_), do: exit(:private_check_failed)

  def main do
    # Exec may have reset dumpability. CORE=0, FSIZE=0 and the verified non-piped
    # collector protect the pre-NIF interval; only this call reasserts dumpable=0.
    {:ok, pre_init_dumpable} = MixerHarness.Control.secure_role()
    assert(pre_init_dumpable in [0, 1])
    generation = System.fetch_env!("MIXER_HARNESS_GENERATION")
    assert(byte_size(generation) == 32)
    assert(Enum.all?(:binary.bin_to_list(generation), &(&1 in ?0..?9 or &1 in ?a..?f)))
    mode = System.fetch_env!("MIXER_HARNESS_CASE")
    assert(mode in @implemented)
    # No raw notice/error report reaches stdio; external allowlist remains an
    # independent boundary. Suppression is not claimed to sanitize a callback.
    Logger.configure(level: :emergency)
    for app <- [:crypto, :ssl, :bandit], do: {:ok, _} = Application.ensure_all_started(app)
    {:ok, _} = MixerHarness.State.start()
    isolation!()
    emit("isolation", %{capabilities: 0, dumpable: 0, readOnlyRoot: 1,
      inheritedFDs: 4, roleNamespacePid: 2, preInitDumpable: pre_init_dumpable})
    {:ok, supervisor} = MixerHosted.Billing.WebhookTransport.start_link(MixerHarness.Plug)
    Process.unlink(supervisor)
    listener = Supervisor.which_children(supervisor)
      |> Enum.find_value(fn {id, pid, _, _} -> if match?({Bandit, _}, id), do: pid end)
    assert(is_pid(listener))
    {:ok, {_, port}} = ThousandIsland.listener_info(listener)
    :ok = MixerHarness.Control.send_control("ready " <> generation <> " " <> Integer.to_string(port))
    parent = self()
    spawn_link(fn -> driver(mode, port, parent) end)
    loop(generation, supervisor, System.monotonic_time(:millisecond))
  end

  def isolation! do
    status = File.read!("/proc/self/status")
    for key <- ["CapEff", "CapPrm", "CapInh", "CapAmb", "CapBnd"] do
      value = status |> String.split("\n") |> Enum.find(&String.starts_with?(&1, key <> ":"))
        |> String.split() |> List.last()
      assert(String.to_integer(value, 16) == 0)
    end
    assert(not File.exists?("/sys/fs/cgroup"))
    mounts = File.read!("/proc/self/mountinfo") |> String.split("\n", trim: true)
    root = Enum.find(mounts, fn line -> Enum.at(String.split(line), 4) == "/" end)
    assert("ro" in (Enum.at(String.split(root), 5) |> String.split(",")))
    proc = Enum.find(mounts, fn line -> Enum.at(String.split(line), 4) == "/proc" end)
    assert("ro" in (Enum.at(String.split(proc), 5) |> String.split(",")))
    routes = File.read!("/proc/net/route") |> String.split("\n", trim: true) |> tl()
    assert(Enum.all?(routes, fn line -> hd(String.split(line)) == "lo" end))
    routes6 = File.read!("/proc/net/ipv6_route") |> String.split("\n", trim: true)
    assert(Enum.all?(routes6, fn line -> List.last(String.split(line)) == "lo" end))
    interfaces = File.read!("/proc/net/dev") |> String.split("\n", trim: true) |> Enum.drop(2)
    assert(Enum.all?(interfaces, fn line -> String.starts_with?(String.trim(line), "lo:") end))
  end

  def loop(generation, supervisor, sampled) do
    now = System.monotonic_time(:millisecond)
    if now - sampled >= 20, do: sample()
    case MixerHarness.Control.receive_control() do
      :again ->
        receive do
          :driver_completed -> :ok
        after
          5 -> :ok
        end
        loop(generation, supervisor, if(now - sampled >= 20, do: now, else: sampled))
      {:ok, "stop " <> received} when received == generation ->
        MixerHarness.State.close()
        Supervisor.stop(supervisor, :normal, 1_000)
        :ok = MixerHarness.Control.send_control("stopped " <> generation <> " completed")
        System.halt(0)
      _ ->
        MixerHarness.State.close()
        Supervisor.stop(supervisor, :normal, 1_000)
        System.halt(1)
    end
  end

  def sample do
    values = Enum.reduce(Process.list(), {0, 0, 0}, fn pid, {heap, binary, mailbox} ->
      case Process.info(pid, [:total_heap_size, :binary, :message_queue_len]) do
        nil -> {heap, binary, mailbox}
        info ->
          # :binary metadata contains IDs/sizes/reference counts, not contents.
          bytes = Enum.reduce(info[:binary], 0, fn {_, size, _}, n -> n + size end)
          {heap + info[:total_heap_size], binary + bytes, mailbox + info[:message_queue_len]}
      end
    end)
    {heap, binary, mailbox} = values
    emit("sample", %{beamTotalBytes: :erlang.memory(:total), heapWords: heap,
      referencedBinaryBytes: binary, mailboxLength: mailbox, processes: :erlang.system_info(:process_count)})
  end

  def report(checks, failures \\ 0) do
    s = MixerHarness.State.snapshot()
    emit("case", %{checks: checks, failures: failures + s.failures,
      sentBytes: 0, ownersDown: Enum.count(s.owners, &(not Process.alive?(&1))), lateSuccesses: 0})
  end

  def driver("R03", _, parent) do
    assert(System.version() == "1.20.4")
    assert(:erlang.system_info(:version) == ~c"17.1")
    otp_file = Path.join([List.to_string(:code.root_dir()), "releases", "29", "OTP_VERSION"])
    assert(String.trim(File.read!(otp_file)) == "29.1.1")
    assert(:erlang.system_info(:schedulers) == 2)
    assert(:erlang.system_info(:schedulers_online) == 2)
    assert(:erlang.system_info(:dirty_cpu_schedulers) == 1)
    assert(:erlang.system_info(:dirty_io_schedulers) == 1)
    assert(:erlang.system_info(:thread_pool_size) == 2)
    assert(:erlang.system_info(:process_limit) == 32768)
    assert(:erlang.system_info(:port_limit) == 1024)
    assert(not Node.alive?())
    report(11)
    send(parent, :driver_completed)
  end
  def driver(mode, _, parent) when mode in ["R09", "R10", "R11", "R13"] do
    kind = %{"R09" => "cpu", "R10" => "tasks", "R11" => "fds", "R13" => "oom"}[mode]
    # FD3 is CLOEXEC before a port child is spawned. The child cannot become a
    # second control peer. C finite helpers inherit the same cgroup/namespace.
    {output, code} = System.cmd("/opt/harness/fault_helper", ["fault", kind], stderr_to_stdout: false)
    assert(code == 0)
    event = Jason.decode!(output)
    assert((Map.keys(event) |> Enum.sort()) == ~w(attempts elapsedNs event kind limitReached schema))
    assert(event["event"] == "fault" and event["schema"] == 1)
    assert(event["limitReached"] == 1)
    emit("fault", Map.new(~w(attempts elapsedNs kind limitReached), &{&1, event[&1]}))
    report(2)
    send(parent, :driver_completed)
  end
  def driver("R12", _, parent) do
    # Documentation-only destination ranges, in an already checked loopback-only
    # namespace. No provider, public endpoint, DNS resolver, or host route exists.
    for {family, address} <- [[:inet, {192, 0, 2, 1}], [:inet6, {0x2001, 0xDB8, 0, 0, 0, 0, 0, 1}]] do
      result = :gen_tcp.connect(address, 9, [family, :binary, active: false], 100)
      assert(match?({:error, _}, result))
      {:ok, udp} = :gen_udp.open(0, [family, :binary, active: false])
      assert(match?({:error, _}, :gen_udp.send(udp, address, 53, <<0::96>>)))
      :gen_udp.close(udp)
    end
    assert(not File.exists?("/etc/resolv.conf") or File.read!("/etc/resolv.conf") == "")
    assert(not File.exists?("/var/run/docker.sock"))
    report(4)
    send(parent, :driver_completed)
  end
  def driver("R15", _, parent) do
    # Controller freezes every observed cgroup task after this fixed marker;
    # only the external whole-cgroup kill can finish the disposal test.
    report(1)
    send(parent, :driver_completed)
  end
  def driver("R16", port, _) do
    body = "MIXER_BODY_SENTINEL"
    signature = "MIXER_SIGNATURE_SENTINEL"
    MixerHarness.State.expected(body, [signature])
    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 100)
    :ok = :gen_tcp.send(socket, ["POST /api/v1/webhooks/stripe HTTP/1.1\r\nHost: localhost\r\n",
      "Content-Type: application/json\r\nStripe-Signature: ", signature,
      "\r\nTransfer-Encoding: chunked\r\n\r\n", Integer.to_string(byte_size(body), 16), "\r\n", body,
      "\r\n0\r\nX-Private-Trailer: MIXER_TRAILER_SENTINEL\r\n\r\n"])
    # All three synthetic values remain live in this driver's heap when killed.
    Process.sleep(100)
    System.cmd("/opt/harness/fault_helper", ["fault", "crash"], stderr_to_stdout: false)
    :erlang.halt(:abort)
  end
  def driver("R17", _, _) do
    # Intentionally rejected by the controller. This is a negative-control
    # success only after whole-cgroup termination and zero retained raw bytes.
    IO.binwrite(:stdio, "MIXER_BODY_SENTINEL\n")
    Process.sleep(60_000)
  end
end

try do
  MixerHarness.Role.main()
rescue
  _ -> System.halt(1)
catch
  _, _ -> System.halt(1)
end
