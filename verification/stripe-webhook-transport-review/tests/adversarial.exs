ExUnit.start(autorun: false)

defmodule PrivateTransportEvidence do
  use Agent

  def start_link,
    do:
      Agent.start_link(fn -> %{mode: :normal, rows: [], logs: [], checks: [], calls: 0} end,
        name: __MODULE__
      )

  def mode(v), do: Agent.update(__MODULE__, &Map.put(&1, :mode, v))
  def mode, do: Agent.get(__MODULE__, & &1.mode)
  def add(k, v), do: Agent.update(__MODULE__, &Map.update!(&1, k, fn xs -> [v | xs] end))
  def call, do: Agent.update(__MODULE__, &Map.update!(&1, :calls, fn x -> x + 1 end))
  def get, do: Agent.get(__MODULE__, & &1)

  def bits(value) do
    text = inspect(value, limit: :infinity, printable_limit: :infinity)

    Enum.any?(
      [
        "BODY_SECRET_SENTINEL",
        "SIGNATURE_SECRET_SENTINEL",
        "TRAILER_SECRET_SENTINEL",
        "PATH_SECRET_SENTINEL",
        "QUERY_SECRET_SENTINEL",
        "OPAQUE_SECRET_SENTINEL"
      ],
      &String.contains?(text, &1)
    )
  end
end

defmodule PrivateTransportLogSink do
  def adding_handler(c), do: {:ok, c}
  def removing_handler(_), do: :ok
  def changing_config(_, _, c), do: {:ok, c}

  def log(event, _),
    do:
      PrivateTransportEvidence.add(:logs, %{
        raw: PrivateTransportEvidence.bits(event),
        event: %{
          level: event.level,
          msg:
            if(match?({:report, %{event: :webhook_transport}}, event.msg),
              do: elem(event.msg, 1),
              else: :arbitrary_drift_message
            ),
          meta: %{domain: :collector_observed}
        }
      })
end

defmodule PrivateTransportPlug do
  def init(opts), do: opts

  def call(conn, _) do
    mode = PrivateTransportEvidence.mode()
    if mode == :frozen, do: Process.sleep(6_000)

    try do
      case MixerHosted.Billing.WebhookTransport.capture(conn) do
        {:ok, captured, latest} ->
          PrivateTransportEvidence.call()
          # Synthetic verifier really runs; the count is attached to this call,
          # and captures exact argument hashes only in trusted test evidence.
          outcome =
            MixerHosted.Billing.WebhookSignature.verify(
              captured.raw_body,
              captured.signature_header_values,
              ["synthetic_private_transport_key_32_bytes"],
              1_700_000_000
            )

          PrivateTransportEvidence.add(:checks, %{
            body_bytes: byte_size(captured.raw_body),
            verifier: outcome == :ok
          })

          if mode == :blocked_response, do: Process.sleep(8_000)
          Plug.Conn.send_resp(latest, 418, "private transport") |> Plug.Conn.halt()

        {:error, _, latest} ->
          Plug.Conn.send_resp(latest, 400, "private transport") |> Plug.Conn.halt()
      end
    after
      MixerHosted.Billing.WebhookTransport.dispose()
    end
  end
end

defmodule PrivateTransportHelpers do
  alias MixerHosted.Billing.WebhookTransport, as: T
  alias T.Owner
  def now, do: System.monotonic_time(:millisecond)

  def role(fun) do
    Process.flag(:trap_exit, true)
    :ok = :logger.add_handler(:mixer_private_collector, PrivateTransportLogSink, %{level: :all})

    {:ok, role} =
      T.start_link(PrivateTransportPlug, %{mixer_private_collector: PrivateTransportLogSink})

    {_, listener, _, _} =
      Enum.find(Supervisor.which_children(role), fn {id, _, _, _} -> match?({Bandit, _}, id) end)

    {:ok, {{127, 0, 0, 1}, port}} = ThousandIsland.listener_info(listener)
    dir = System.fetch_env!("CAPTURE_RESULT_DIR")

    File.write!(
      Path.join(dir, "listener.json"),
      Jason.encode!(%{port: port, role: inspect(role)})
    )

    PrivateTransportEvidence.add(:rows, %{
      kind: :inventory,
      logger:
        Enum.map(:logger.get_handler_config(), fn h ->
          %{
            id: h.id,
            module: h.module,
            filters: Enum.map(h.filters, &elem(&1, 0)),
            formatter: if(is_tuple(h.formatter), do: elem(h.formatter, 0), else: :none)
          }
        end),
      telemetry: Enum.map(:telemetry.list_handlers([]), &%{id: &1.id, event: &1.event_name}),
      stdout: :default_logger_standard_io,
      stderr: :owned_child_merged_capture,
      exporters: :none
    })

    try do
      fun.(role, listener, port)
    after
      if Process.alive?(role), do: Supervisor.stop(role, :normal, 2_000)
      Process.sleep(50)
      :logger.remove_handler(:mixer_private_collector)
      # Failed bootstrap can attach a subscriber before init raises; no listener
      # was started, and the trusted test cleanup owns this identifier.
      :telemetry.detach("mixer-private-webhook-control")

      refused =
        case :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 100) do
          {:error, :econnrefused} ->
            true

          {:ok, s} ->
            :gen_tcp.close(s)
            false

          _ ->
            false
        end

      PrivateTransportEvidence.add(:rows, %{
        kind: :cleanup,
        role_down: not Process.alive?(role),
        port: port,
        refused: refused,
        guard_supervisor_down: is_nil(Process.whereis(T.Guards)),
        owner_down: is_nil(Process.whereis(Owner))
      })
    end
  end

  def tcp(port), do: :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 1_000)

  def head(length \\ "1"),
    do:
      "POST /api/v1/webhooks/stripe HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nStripe-Signature: SIGNATURE_SECRET_SENTINEL\r\nContent-Length: #{length}\r\n\r\n"

  def frame(type, flags, id, data),
    do: <<byte_size(data)::24, type::8, flags::8, 0::1, id::31, data::binary>>

  def preface, do: "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n" <> frame(4, 0, 0, <<>>)

  def block(extra \\ [], huffman \\ :never) do
    {encoded, _} =
      HPAX.encode(
        ([
           {":method", "POST"},
           {":scheme", "http"},
           {":authority", "localhost"},
           {":path", "/api/v1/webhooks/stripe"},
           {"content-type", "application/json"},
           {"stripe-signature", "SIGNATURE_SECRET_SENTINEL"}
         ] ++ extra)
        |> Enum.map(fn {k, v} -> {:no_store, k, v} end),
        HPAX.new(4096, huffman_encoding: huffman)
      )

    IO.iodata_to_binary(encoded)
  end

  def wait_socket(socket, deadline, bytes \\ 0) do
    if now() >= deadline do
      %{closed: false, bytes: bytes}
    else
      case :gen_tcp.recv(socket, 0, min(100, max(deadline - now(), 1))) do
        {:ok, data} -> wait_socket(socket, deadline, bytes + byte_size(data))
        {:error, :timeout} -> wait_socket(socket, deadline, bytes)
        {:error, reason} -> %{closed: reason in [:closed, :econnreset], bytes: bytes}
      end
    end
  end

  def settled do
    for _ <- 1..100, Owner.snapshot().connections != 0, do: Process.sleep(5)
    Owner.snapshot()
  end

  def metrics(label) do
    state = :sys.get_state(Owner)

    pids =
      Enum.uniq(
        Enum.flat_map(state.connections, fn {_, c} ->
          g = :sys.get_state(c.guard)
          [c.pid | g.requests]
        end)
      )

    values =
      for pid <- pids,
          info =
            Process.info(pid, [:memory, :heap_size, :total_heap_size, :message_queue_len, :binary]),
          info != nil do
        i = Map.new(info)

        %{
          pid: inspect(pid),
          memory_bytes: i.memory,
          heap_words: i.heap_size,
          total_heap_words: i.total_heap_size,
          mailbox: i.message_queue_len,
          binary_bytes: Enum.reduce(i.binary, 0, fn {_, bytes, _}, n -> bytes + n end)
        }
      end

    {rss, _} = System.cmd("ps", ["-o", "rss=", "-p", System.pid()])

    row = %{
      kind: :resources,
      label: label,
      processes: values,
      vm_rss_kib: String.to_integer(String.trim(rss)),
      vm_binary_bytes: :erlang.memory(:binary),
      vm_total_bytes: :erlang.memory(:total),
      hard_memory_ceiling: false
    }

    PrivateTransportEvidence.add(:rows, row)
    row
  end

  def synthetic(parent, deadline_delta, action) do
    span = make_ref()

    pid =
      spawn(fn ->
        started = now()
        :ok = Owner.register(self(), span, started)
        :ok = Owner.ready(self(), span, started)

        {:ok, permit} =
          Owner.request(self(), span, {PrivateTransportPlug, []}, now() - 5_000 + deadline_delta)

        send(parent, {:synthetic, self(), permit})

        receive do
          :go -> action.(permit)
        end
      end)

    {pid, span}
  end
end

{:ok, _} = PrivateTransportEvidence.start_link()

defmodule PrivateTransportTest do
  use ExUnit.Case, async: false
  import PrivateTransportHelpers
  alias MixerHosted.Billing.WebhookTransport, as: T
  alias T.{Owner, Sinks}

  setup do
    PrivateTransportEvidence.mode(:normal)
    :ok
  end

  test "P02 prePlug H1 headers and H2 preface CONTINUATION never refresh absolute stage" do
    role(fn _, _, port ->
      for {label, initial, drip} <- [
            {:h1_headers, "POST /api/v1/webhooks/stripe HTTP/1.1\r\nX: PATH_SECRET_SENTINEL",
             "x"},
            {:h2_preface, preface(), frame(6, 0, 0, <<0::64>>)},
            {:h2_continuation, preface() <> frame(1, 0, 1, block()), frame(9, 0, 1, <<>>)}
          ] do
        {:ok, s} = tcp(port)
        started = now()

        try do
          :ok = :gen_tcp.send(s, initial)

          dripper =
            Task.async(fn ->
              Enum.reduce_while(1..20, :ok, fn _, _ ->
                Process.sleep(100)

                case :gen_tcp.send(s, drip) do
                  :ok -> {:cont, :ok}
                  _ -> {:halt, :closed}
                end
              end)
            end)

          result = wait_socket(s, started + 1_500)
          elapsed = now() - started
          Task.await(dripper, 1_000)
          assert elapsed <= 1_100
          assert result.closed
          snapshot = settled()
          assert Enum.any?(snapshot.history, &(&1.reason == :expired and &1.overshoot_ms <= 100))

          PrivateTransportEvidence.add(:rows, %{
            kind: :stage,
            label: label,
            peer_observed_ms: elapsed,
            history: snapshot.history
          })
        after
          :gen_tcp.close(s)
        end
      end
    end)
  end

  test "P03 frozen H2 reader queued DATA and exact five-second disposal" do
    PrivateTransportEvidence.mode(:frozen)

    role(fn _, _, port ->
      {:ok, s} = tcp(port)
      started = now()

      try do
        :ok = :gen_tcp.send(s, preface() <> frame(1, 4, 1, block()))
        Process.sleep(50)

        :ok =
          :gen_tcp.send(
            s,
            Enum.map(1..64, fn _ -> frame(0, 0, 1, String.duplicate("x", 16_384)) end)
          )

        Process.sleep(100)

        samples =
          for _ <- 1..5 do
            row = metrics(:frozen_h2_1mib_queued)
            Process.sleep(10)
            row
          end

        sample =
          Enum.max_by(samples, fn row -> Enum.reduce(row.processes, 0, &(&1.mailbox + &2)) end)

        assert Enum.any?(sample.processes, &(&1.mailbox > 0))

        pinger =
          Task.async(fn ->
            Enum.reduce_while(1..60, :ok, fn _, _ ->
              Process.sleep(100)

              case :gen_tcp.send(s, frame(6, 0, 0, <<0::64>>)) do
                :ok -> {:cont, :ok}
                _ -> {:halt, :closed}
              end
            end)
          end)

        result = wait_socket(s, started + 5_600)
        peer_ms = now() - started
        Task.await(pinger, 1_000)
        assert result.closed
        snapshot = settled()
        assert snapshot.connections == 0 and snapshot.permits == 0
        assert Enum.any?(snapshot.history, &(&1.reason == :expired and &1.overshoot_ms <= 100))

        PrivateTransportEvidence.add(:rows, %{
          kind: :deadline,
          label: :frozen,
          peer_observed_ms: peer_ms,
          history: snapshot.history
        })
      after
        :gen_tcp.close(s)
      end
    end)
  end

  test "P03 outer seven seconds remains active after successful capture while response blocks" do
    PrivateTransportEvidence.mode(:blocked_response)

    role(fn _, _, port ->
      {:ok, s} = tcp(port)
      started = now()

      try do
        :ok = :gen_tcp.send(s, head() <> "a")
        result = wait_socket(s, started + 7_500)
        assert result.closed and result.bytes == 0
        snapshot = settled()
        assert Enum.any?(snapshot.history, &(&1.reason == :expired and &1.overshoot_ms <= 100))

        PrivateTransportEvidence.add(:rows, %{
          kind: :deadline,
          label: :outer_response,
          peer_observed_ms: now() - started,
          history: snapshot.history
        })
      after
        :gen_tcp.close(s)
      end
    end)
  end

  test "P04 permits are caller generation one-use and deadline bound including delayed guard" do
    role(fn _, _, _ ->
      parent = self()

      for mode <- [:replay, :generation, :unknown, :at_deadline, :after_deadline] do
        {pid, _} =
          synthetic(
            parent,
            if(mode in [:at_deadline, :after_deadline], do: 80, else: 500),
            fn permit ->
              begin = Owner.check(permit, :begin)

              if mode in [:at_deadline, :after_deadline],
                do: Process.sleep(if(mode == :at_deadline, do: 80, else: 100))

              argument =
                case mode do
                  :generation -> {make_ref(), elem(permit, 1), elem(permit, 2)}
                  :unknown -> {elem(permit, 0), elem(permit, 1), make_ref()}
                  _ -> permit
                end

              finish = Owner.check(argument, :finish)
              repeated = if mode == :replay, do: Owner.check(permit, :finish), else: nil
              send(parent, {:permit_result, mode, begin, finish, repeated})

              receive do
                :stop -> :ok
              after
                1_000 -> :ok
              end
            end
          )

        receive do
          {:synthetic, ^pid, permit} ->
            assert {:error, :caller} = Owner.check(permit, :begin)
        end

        # Caller mismatch disposes its connection; use a second independent
        # registered synthetic owner for each semantic assertion.
        Process.sleep(20)

        {pid, _} =
          synthetic(
            parent,
            if(mode in [:at_deadline, :after_deadline], do: 80, else: 500),
            fn permit ->
              begin = Owner.check(permit, :begin)

              if mode in [:at_deadline, :after_deadline],
                do: Process.sleep(if(mode == :at_deadline, do: 80, else: 100))

              argument =
                case mode do
                  :generation -> {make_ref(), elem(permit, 1), elem(permit, 2)}
                  :unknown -> {elem(permit, 0), elem(permit, 1), make_ref()}
                  _ -> permit
                end

              finish = Owner.check(argument, :finish)
              repeated = if mode == :replay, do: Owner.check(permit, :finish), else: nil
              send(parent, {:permit_result, mode, begin, finish, repeated})

              receive do
                :stop -> :ok
              after
                1_000 -> :ok
              end
            end
          )

        guard =
          receive do
            {:synthetic, ^pid, _} ->
              c = :sys.get_state(Owner).connections |> Map.values() |> Enum.find(&(&1.pid == pid))
              if mode in [:at_deadline, :after_deadline], do: :sys.suspend(c.guard)
              send(pid, :go)
              c.guard
          end

        receive do
          {:permit_result, ^mode, :ok, finish, repeated} ->
            if mode == :replay do
              assert match?({:ok, _}, finish) and repeated == {:error, :replay}
            else
              assert match?({:error, _}, finish)
            end

            PrivateTransportEvidence.add(:rows, %{
              kind: :permit,
              mode: mode,
              finish: inspect(finish),
              repeated: inspect(repeated)
            })
        after
          1_000 ->
            # At/after the exact timer, independent kill can win before check.
            refute Process.alive?(pid)

            PrivateTransportEvidence.add(:rows, %{
              kind: :permit,
              mode: mode,
              independent_kill_won: true
            })
        end

        if mode in [:at_deadline, :after_deadline] and Process.alive?(guard),
          do: :sys.resume(guard)

        if Process.alive?(pid), do: Process.exit(pid, :kill)
        settled()
      end
    end)
  end

  test "P07 P08 every owned telemetry and logger path discards arbitrary messages metadata reports" do
    role(fn _, _, _ ->
      before = length(PrivateTransportEvidence.get().logs)
      assert Sinks.valid?()

      for event <- [
            [:thousand_island, :connection, :recv],
            [:thousand_island, :connection, :async_recv],
            [:bandit, :request, :exception]
          ] do
        :telemetry.execute(
          event,
          %{data: "BODY_SECRET_SENTINEL", opaque: "OPAQUE_SECRET_SENTINEL"},
          %{
            conn: %{
              headers: "SIGNATURE_SECRET_SENTINEL",
              path: "PATH_SECRET_SENTINEL",
              query: "QUERY_SECRET_SENTINEL",
              trailers: "TRAILER_SECRET_SENTINEL"
            }
          }
        )
      end

      for message <- [
            "BODY_SECRET_SENTINEL",
            %{report: "OPAQUE_SECRET_SENTINEL"},
            %{
              mixer_transport: 1,
              event: :webhook_transport,
              reason: :admitted,
              count: 1,
              extra: "SIGNATURE_SECRET_SENTINEL"
            }
          ] do
        :logger.log(:error, message, %{
          domain: [:mixer_private_transport],
          raw: "TRAILER_SECRET_SENTINEL"
        })
      end

      :logger.log(
        :notice,
        %{mixer_transport: 1, event: :webhook_transport, reason: :admitted, count: 1},
        %{raw: "TRAILER_SECRET_SENTINEL"}
      )

      Sinks.record(:rejected)
      Process.sleep(30)

      refute Enum.any?(
               Enum.take(
                 PrivateTransportEvidence.get().logs,
                 length(PrivateTransportEvidence.get().logs) - before
               ),
               & &1.raw
             )

      assert Enum.any?(
               PrivateTransportEvidence.get().logs,
               &(&1.event.msg == %{event: :webhook_transport, reason: :rejected, count: 1})
             )
    end)
  end

  test "P09 owner guard listener and detached handler loss close role and registered owners" do
    for fault <- [:owner, :guard, :listener, :handler] do
      role(fn role, listener, port ->
        {:ok, s} = tcp(port)

        try do
          :ok = :gen_tcp.send(s, head("999") <> "a")
          Process.sleep(50)
          state = :sys.get_state(Owner)
          c = state.connections |> Map.values() |> hd()

          case fault do
            :owner -> Process.exit(Process.whereis(Owner), :kill)
            :guard -> Process.exit(c.guard, :kill)
            :listener -> Process.exit(listener, :kill)
            :handler -> :telemetry.detach("mixer-private-webhook-control")
          end

          result = wait_socket(s, now() + 500)
          assert result.closed
          Process.sleep(100)
          refute Process.alive?(role)
          refute Process.alive?(c.pid)

          PrivateTransportEvidence.add(:rows, %{
            kind: :failure_domain,
            fault: fault,
            role_down: true,
            connection_down: true
          })
        after
          :gen_tcp.close(s)
        end
      end)
    end
  end

  test "P09 bootstrap rejects raw subscriber and drift stops admission without undoing delivered bytes" do
    Process.flag(:trap_exit, true)

    :ok =
      :telemetry.attach(
        "unexpected-private-raw",
        [:thousand_island, :connection, :recv],
        fn _, m, _, _ ->
          PrivateTransportEvidence.add(:rows, %{
            kind: :privileged_raw_delivery,
            seen: PrivateTransportEvidence.bits(m)
          })
        end,
        nil
      )

    assert {:error, _} =
             T.start_link(PrivateTransportPlug, %{
               mixer_private_collector: PrivateTransportLogSink
             })

    :telemetry.detach("unexpected-private-raw")
    :telemetry.detach("mixer-private-webhook-control")

    role(fn role, _, _ ->
      :ok =
        :telemetry.attach(
          "unexpected-private-raw",
          [:thousand_island, :connection, :recv],
          fn _, m, _, _ ->
            PrivateTransportEvidence.add(:rows, %{
              kind: :privileged_raw_delivery,
              seen: PrivateTransportEvidence.bits(m)
            })
          end,
          nil
        )

      # Privileged code can execute an event immediately. Our first raw handler
      # would kill this emitter on drift, so perform in a disposable owner.
      p =
        spawn(fn ->
          :telemetry.execute(
            [:thousand_island, :connection, :recv],
            %{data: "BODY_SECRET_SENTINEL"},
            %{}
          )
        end)

      Process.sleep(100)
      refute Process.alive?(role)
      refute Process.alive?(p)
      :telemetry.detach("unexpected-private-raw")

      PrivateTransportEvidence.add(:rows, %{
        kind: :drift_boundary,
        already_delivered_bytes_reversible: false,
        prevention_claim: false
      })
    end)
  end

  test "P04 forged conn private fields do not mint a permit" do
    role(fn _, _, _ ->
      conn = %Plug.Conn{
        method: "POST",
        request_path: "/api/v1/webhooks/stripe",
        private: %{
          permit: {make_ref(), make_ref(), make_ref()},
          owner: self(),
          deadline: now() + 50_000
        }
      }

      assert {:error, :unavailable_state, %Plug.Conn{halted: true}} = T.capture(conn)
    end)
  end

  test "P09 malformed registration fails closed without telemetry automatic-detach reliance" do
    role(fn role, _, _ ->
      emitter =
        spawn(fn ->
          :telemetry.execute(
            [:bandit, :request, :start],
            %{monotonic_time: System.monotonic_time()},
            %{}
          )
        end)

      Process.sleep(100)
      refute Process.alive?(emitter)
      refute Process.alive?(role)

      PrivateTransportEvidence.add(:rows, %{
        kind: :registration_failure,
        emitter_down: true,
        role_down: true
      })
    end)
  end

  test "P09 removed collector filter detects drift but cannot undo privileged delivery" do
    role(fn role, _, _ ->
      :ok = :logger.remove_handler_filter(:mixer_private_collector, :mixer_private_schema)
      :logger.log(:error, "OPAQUE_SECRET_SENTINEL")
      Process.sleep(100)
      refute Process.alive?(role)
      assert Enum.any?(PrivateTransportEvidence.get().logs, & &1.raw)

      PrivateTransportEvidence.add(:rows, %{
        kind: :logger_privileged_drift,
        already_delivered_to_collector: true,
        prevention_claim: false
      })
    end)
  end

  test "P11 actual maximum H2 terminal DATA is captured under fixed profile" do
    role(fn _, _, port ->
      {:ok, s} = tcp(port)

      try do
        :ok =
          :gen_tcp.send(s, preface() <> frame(1, 4, 1, block([{"content-length", "1048576"}])))

        # Drain initial SETTINGS and subsequent WINDOW_UPDATEs between bounded
        # writes. This client sends real terminal DATA with END_STREAM.
        :gen_tcp.recv(s, 0, 200)

        for n <- 1..64 do
          :ok =
            :gen_tcp.send(
              s,
              frame(0, if(n == 64, do: 1, else: 0), 1, String.duplicate("x", 16_384))
            )

          if rem(n, 2) == 0 and n < 64, do: :gen_tcp.recv(s, 0, 100)
        end

        result = wait_socket(s, now() + 1_500)
        assert result.closed
        assert Enum.any?(PrivateTransportEvidence.get().checks, &(&1.body_bytes == 1_048_576))

        PrivateTransportEvidence.add(:rows, %{
          kind: :actual_max_h2,
          body_bytes: 1_048_576,
          captured: true
        })
      after
        :gen_tcp.close(s)
      end

      settled()
    end)
  end


  test "P09 bootstrap rejects an undeclared Logger sink" do
    Process.flag(:trap_exit, true)
    :ok = :logger.add_handler(:unexpected_private_sink, PrivateTransportLogSink, %{level: :all})
    try do
      assert {:error, _} = T.start_link(PrivateTransportPlug, %{mixer_private_collector: PrivateTransportLogSink})
      assert is_nil(Process.whereis(Owner))
      PrivateTransportEvidence.add(:rows, %{kind: :bootstrap_unknown_logger, rejected: true})
    after
      :logger.remove_handler(:unexpected_private_sink)
      :telemetry.detach("mixer-private-webhook-control")
    end
  end
  test "P10 sixteen live slots overflow and bounded parser frame hostility" do
    role(fn _, _, port ->
      sockets =
        for _ <- 1..16 do
          {:ok, s} = tcp(port)
          :gen_tcp.send(s, "POST /api/v1/webhooks/stripe HTTP/1.1\r\nX: ")
          s
        end

      try do
        Process.sleep(80)
        assert Owner.snapshot().connections == 16
        metrics(:sixteen_queued_headers)
        {:ok, extra} = tcp(port)

        try do
          :gen_tcp.send(extra, head() <> "a")
          result = wait_socket(extra, now() + 400)
          assert result.closed
          assert Owner.snapshot().peak == 16
        after
          :gen_tcp.close(extra)
        end
      after
        for s <- sockets, do: :gen_tcp.close(s)
      end

      settled()

      compressed = block([{"x-hostile", String.duplicate("a", 17_000)}], :always)
      assert byte_size(compressed) < 16_384
      PrivateTransportEvidence.add(:rows, %{kind: :header_compression, encoded_bytes: byte_size(compressed), value_bytes: 17_000})
      for {label, data} <- [
            {:h1_line, String.duplicate("X", 513) <> " / HTTP/1.1\r\n\r\n"},
            {:h1_header,
             "POST /api/v1/webhooks/stripe HTTP/1.1\r\nX: " <>
               String.duplicate("X", 8_193) <> "\r\n\r\n"},
            {:h2_oversize_frame, preface() <> frame(0, 0, 1, String.duplicate("X", 16_385))},
            {:h2_decompressed_headers,
             preface() <>
               frame(1, 4, 1, block([{"x-hostile", String.duplicate("a", 17_000)}], :always))}
          ] do
        {:ok, s} = tcp(port)

        try do
          :gen_tcp.send(s, data)
          metrics(label)
          assert wait_socket(s, now() + 1_500).closed
        after
          :gen_tcp.close(s)
        end

        settled()
      end
    end)
  end
end

summary = ExUnit.run()
state = PrivateTransportEvidence.get()
result = System.fetch_env!("CAPTURE_RESULT_DIR")

File.write!(
  Path.join(result, "adversarial.json"),
  Jason.encode!(
    %{
      summary: summary,
      rows: Enum.reverse(state.rows),
      logger_events: Enum.reverse(state.logs),
      actual_verifier_calls: state.calls,
      capture_checks: state.checks,
      hard_memory_ceiling: false
    }, pretty: true)
)

if summary.failures != 0, do: System.halt(1)
