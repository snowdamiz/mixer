ExUnit.start(autorun: false)

defmodule MixerRawCapture.WireState do
  use Agent

  def start_link,
    do: Agent.start_link(fn -> %{events: [], telemetry: [], logs: []} end, name: __MODULE__)

  def add(key, value),
    do: Agent.update(__MODULE__, &Map.update!(&1, key, fn list -> [value | list] end))

  def get(key), do: Agent.get(__MODULE__, &Map.fetch!(&1, key)) |> Enum.reverse()

  def telemetry(event, measurements, meta, _config) do
    add(:telemetry, %{
      event: Enum.map(event, &Atom.to_string/1),
      bodySeen: contains_binary?([measurements, meta], "RAW_BODY_SENTINEL"),
      signatureSeen: contains_binary?([measurements, meta], "RAW_SIG_SENTINEL"),
      trailerSeen: contains_binary?([measurements, meta], "RAW_TRAILER_SENTINEL"),
      measurementBodySeen: contains_binary?(measurements, "RAW_BODY_SENTINEL"),
      measurementSignatureSeen: contains_binary?(measurements, "RAW_SIG_SENTINEL"),
      measurementTrailerSeen: contains_binary?(measurements, "RAW_TRAILER_SENTINEL"),
      metadataBodySeen: contains_binary?(meta, "RAW_BODY_SENTINEL"),
      metadataSignatureSeen: contains_binary?(meta, "RAW_SIG_SENTINEL"),
      metadataTrailerSeen: contains_binary?(meta, "RAW_TRAILER_SENTINEL")
    })
  end

  # Match bytes directly: inspect/1 may print framed binary DATA as integers.
  defp contains_binary?(value, needle) when is_binary(value),
    do: :binary.match(value, needle) != :nomatch

  defp contains_binary?(value, needle) when is_map(value),
    do: value |> Map.to_list() |> Enum.any?(&contains_binary?(&1, needle))

  defp contains_binary?(value, needle) when is_list(value),
    do: Enum.any?(value, &contains_binary?(&1, needle))

  defp contains_binary?(value, needle) when is_tuple(value),
    do: value |> Tuple.to_list() |> Enum.any?(&contains_binary?(&1, needle))

  defp contains_binary?(_, _), do: false
end

defmodule MixerRawCapture.LoggerHandler do
  def adding_handler(config), do: {:ok, config}
  def removing_handler(_), do: :ok
  def changing_config(_old, _new, config), do: {:ok, config}

  def log(event, _config) do
    text = inspect(event, limit: :infinity, printable_limit: :infinity)

    MixerRawCapture.WireState.add(:logs, %{
      level: Atom.to_string(event.level),
      bodySeen: String.contains?(text, "RAW_BODY_SENTINEL"),
      signatureSeen: String.contains?(text, "RAW_SIG_SENTINEL"),
      trailerSeen: String.contains?(text, "RAW_TRAILER_SENTINEL")
    })
  end
end

defmodule MixerRawCapture.CountingAdapter do
  def get_http_protocol({adapter, state}), do: adapter.get_http_protocol(state)

  def read_req_body({adapter, state}, opts) do
    Process.put(:wire_reads, Process.get(:wire_reads, 0) + 1)

    case adapter.read_req_body(state, opts) do
      {tag, body, next} when tag in [:ok, :more] ->
        Process.put(:wire_results, [
          %{
            tag: Atom.to_string(tag),
            bytes: byte_size(body),
            target: opts[:length],
            timeout: opts[:read_timeout]
          }
          | Process.get(:wire_results, [])
        ])

        {tag, body, {adapter, next}}

      other ->
        other
    end
  end
end

defmodule MixerRawCapture.PrivatePlug do
  alias MixerHosted.Billing.RawWebhookCapture
  @secret "synthetic_capture_key_at_least_32_bytes"
  @now 1_700_000_000
  def init(opts), do: opts

  def call(conn, _opts) do
    id = Plug.Conn.get_req_header(conn, "x-capture-test") |> List.first()
    signatures = Plug.Conn.get_req_header(conn, "stripe-signature")
    Process.put(:wire_reads, 0)
    Process.put(:wire_verifier_calls, 0)
    Process.put(:wire_results, [])
    original = conn.adapter
    wrapped = %{conn | adapter: {MixerRawCapture.CountingAdapter, original}}
    started = System.monotonic_time(:millisecond)

    try do
      case RawWebhookCapture.capture(wrapped) do
        {:ok, captured, latest} ->
          Process.put(:wire_verifier_calls, Process.get(:wire_verifier_calls) + 1)

          verified =
            MixerHosted.Billing.WebhookSignature.verify(
              captured.raw_body,
              captured.signature_header_values,
              [@secret],
              @now
            )

          record(id, started, %{
            outcome: "captured",
            bodySHA256: Base.encode16(:crypto.hash(:sha256, captured.raw_body), case: :lower),
            bodyBytes: byte_size(captured.raw_body),
            signatureValues: captured.signature_header_values,
            verifier: if(verified == :ok, do: "ok", else: "invalid"),
            domainCalls: 0,
            exposedSignatureValues: signatures
          })

          respond(latest, 418)

        {:error, reason, latest} ->
          record(id, started, %{
            outcome: "capture-rejected",
            reason: Atom.to_string(reason),
            domainCalls: 0,
            exposedSignatureValues: signatures,
            halted: latest.halted
          })

          respond(latest, 400)
      end
    rescue
      exception ->
        record(id, started, %{
          outcome: "raised",
          exceptionModule: Atom.to_string(exception.__struct__),
          domainCalls: 0,
          exposedSignatureValues: signatures
        })

        reraise exception, __STACKTRACE__
    end
  end

  defp record(id, started, result) do
    MixerRawCapture.WireState.add(
      :events,
      Map.merge(result, %{
        id: id,
        verifierCalls: Process.get(:wire_verifier_calls, 0),
        reads: Process.get(:wire_reads),
        readResults: Enum.reverse(Process.get(:wire_results)),
        elapsedMs: System.monotonic_time(:millisecond) - started
      })
    )
  end

  defp respond(%{adapter: {MixerRawCapture.CountingAdapter, original}} = conn, status) do
    conn = %{conn | adapter: original}

    conn =
      if Plug.Conn.get_http_protocol(conn) == :"HTTP/1.1",
        do: Plug.Conn.put_resp_header(conn, "connection", "close"),
        else: conn

    conn |> Plug.Conn.send_resp(status, "private-capture-test") |> Plug.Conn.halt()
  end
end

defmodule MixerRawCapture.WireHelpers do
  @secret "synthetic_capture_key_at_least_32_bytes"
  @now 1_700_000_000
  def sign(body) do
    "t=#{@now},v1=" <>
      Base.encode16(:crypto.mac(:hmac, :sha256, @secret, Integer.to_string(@now) <> "." <> body),
        case: :lower
      )
  end

  def headers(body), do: [{"Content-Type", "application/json"}, {"Stripe-Signature", sign(body)}]

  def replace(headers, name, values) do
    Enum.reject(headers, fn {key, _} -> String.downcase(key) == String.downcase(name) end) ++
      Enum.map(values, &{name, &1})
  end

  def event(id), do: Enum.find(MixerRawCapture.WireState.get(:events), &(&1.id == id))

  def tcp(port, id, body, options \\ []) do
    headers = Keyword.get(options, :headers, headers(body))

    framing =
      Keyword.get(options, :framing, [{"Content-Length", Integer.to_string(byte_size(body))}])

    method = Keyword.get(options, :method, "POST")
    path = Keyword.get(options, :path, "/api/v1/webhooks/stripe")
    version = Keyword.get(options, :version, "HTTP/1.1")

    head =
      "#{method} #{path} #{version}\r\nHost: localhost\r\nX-Capture-Test: #{id}\r\nConnection: close\r\n" <>
        Enum.map_join(headers ++ framing, "", fn {key, value} ->
          key <> ": " <> value <> "\r\n"
        end) <> "\r\n"

    started = System.monotonic_time(:millisecond)
    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 1_000)

    try do
      :ok = :gen_tcp.send(socket, head)
      parts = Keyword.get(options, :parts, [{0, body}])

      for {pause, bytes} <- parts do
        if pause > 0, do: Process.sleep(pause)
        # A deliberately rejected request may close before a late send.
        _ = :gen_tcp.send(socket, bytes)
      end

      if Keyword.get(options, :half_close, false), do: :gen_tcp.shutdown(socket, :write)
      {response, ended} = receive_all(socket, System.monotonic_time(:millisecond) + 8_000, "")

      statuses =
        Regex.scan(~r/HTTP\/1\.[01] ([0-9]{3})/, response, capture: :all_but_first)
        |> List.flatten()
        |> Enum.map(&String.to_integer/1)

      result = %{
        id: id,
        transport: "raw-tcp-http1",
        statuses: statuses,
        serverEnd: Atom.to_string(ended),
        elapsedMs: System.monotonic_time(:millisecond) - started,
        event: event(id)
      }

      MixerRawCapture.WireState.add(:clients, result)
      result
    after
      :gen_tcp.close(socket)
      MixerRawCapture.WireState.add(:socketCleanup, %{id: id, kind: "tcp", closed: true})
    end
  end

  defp receive_all(socket, deadline, acc) do
    remaining = deadline - System.monotonic_time(:millisecond)

    if remaining <= 0 do
      {acc, :harness_deadline}
    else
      case :gen_tcp.recv(socket, 0, min(remaining, 1_000)) do
        {:ok, bytes} -> receive_all(socket, deadline, acc <> bytes)
        {:error, :timeout} -> receive_all(socket, deadline, acc)
        {:error, reason} -> {acc, reason}
      end
    end
  end

  def h2(port, id, body, options \\ []) do
    headers =
      Keyword.get(options, :headers, headers(body))
      |> Enum.map(fn {k, v} -> {String.downcase(k), v} end)

    headers = headers ++ [{"x-capture-test", id}] ++ Keyword.get(options, :framing, [])

    {:ok, conn} =
      Mint.HTTP2.connect(:http, "localhost", port,
        mode: :passive,
        transport_opts: [ip: {127, 0, 0, 1}, timeout: 1_000]
      )

    Process.put(:owned_mint, conn)
    started = System.monotonic_time(:millisecond)

    try do
      {:ok, conn, ref} =
        Mint.HTTP2.request(
          conn,
          Keyword.get(options, :method, "POST"),
          Keyword.get(options, :path, "/api/v1/webhooks/stripe"),
          headers,
          :stream
        )

      Process.put(:owned_mint, conn)

      conn =
        Enum.reduce(Keyword.get(options, :parts, [{0, body}]), conn, fn {pause, bytes}, c ->
          if pause > 0, do: Process.sleep(pause)
          # WINDOW_UPDATE handshakes are pumped before large chunks.
          c =
            if Mint.HTTP2.get_window_size(c, :connection) < byte_size(bytes) or
                 Mint.HTTP2.get_window_size(c, {:request, ref}) < byte_size(bytes),
               do: pump(c),
               else: c

          case Mint.HTTP2.stream_request_body(c, ref, bytes) do
            {:ok, n} ->
              Process.put(:owned_mint, n)
              n

            {:error, n, _} ->
              Process.put(:owned_mint, n)
              n
          end
        end)

      eof = Keyword.get(options, :eof, :eof)

      conn =
        if Keyword.get(options, :finish, true) do
          case Mint.HTTP2.stream_request_body(conn, ref, eof) do
            {:ok, n} -> n
            {:error, n, _} -> n
          end
        else
          conn
        end

      Process.put(:owned_mint, conn)

      {conn, responses, ended} =
        h2_receive(conn, ref, System.monotonic_time(:millisecond) + 8_000, [])

      Process.put(:owned_mint, conn)
      statuses = for {:status, ^ref, status} <- responses, do: status

      result = %{
        id: id,
        transport: "mint-h2c",
        statuses: statuses,
        serverEnd: Atom.to_string(ended),
        elapsedMs: System.monotonic_time(:millisecond) - started,
        event: event(id),
        streamErrors: Enum.count(responses, fn r -> elem(r, 0) == :error end)
      }

      MixerRawCapture.WireState.add(:clients, result)
      result
    after
      Mint.HTTP2.close(Process.get(:owned_mint))
      Process.delete(:owned_mint)
      MixerRawCapture.WireState.add(:socketCleanup, %{id: id, kind: "mint-h2c", closed: true})
    end
  end

  defp pump(conn) do
    case Mint.HTTP2.recv(conn, 0, 1_000) do
      {:ok, n, _} -> n
      {:error, n, _, _} -> n
    end
  end

  defp h2_receive(conn, ref, deadline, acc) do
    remaining = deadline - System.monotonic_time(:millisecond)

    cond do
      Enum.any?(acc, fn r -> r == {:done, ref} or (elem(r, 0) == :error and elem(r, 1) == ref) end) ->
        {conn, acc, :stream_done_or_reset}

      remaining <= 0 ->
        {conn, acc, :harness_deadline}

      true ->
        case Mint.HTTP2.recv(conn, 0, min(remaining, 1_000)) do
          {:ok, n, responses} ->
            h2_receive(n, ref, deadline, acc ++ responses)

          {:error, n, %Mint.TransportError{reason: :timeout}, responses} ->
            h2_receive(n, ref, deadline, acc ++ responses)

          {:error, n, _reason, responses} ->
            {n, acc ++ responses, :connection_error}
        end
    end
  end
end

{:ok, _} = MixerRawCapture.WireState.start_link()
# Additional keys are initialized before any request/logging handler can run.
Agent.update(MixerRawCapture.WireState, &Map.merge(&1, %{clients: [], socketCleanup: []}))
:ok = :logger.add_handler(:capture_synthetic_probe, MixerRawCapture.LoggerHandler, %{level: :all})

:ok =
  :telemetry.attach_many(
    "capture-synthetic-probe",
    [
      [:thousand_island, :connection, :recv],
      [:bandit, :request, :start],
      [:bandit, :request, :stop]
    ],
    &MixerRawCapture.WireState.telemetry/4,
    nil
  )

{:ok, listener} =
  Bandit.start_link(
    plug: MixerRawCapture.PrivatePlug,
    ip: {127, 0, 0, 1},
    port: 0,
    startup_log: false,
    thousand_island_options: [num_acceptors: 1, read_timeout: 2_000]
  )

{:ok, {{127, 0, 0, 1}, port}} = ThousandIsland.listener_info(listener)

File.write!(
  Path.join(System.fetch_env!("CAPTURE_RESULT_DIR"), "listener.json"),
  Jason.encode!(
    %{
      pid: inspect(listener),
      beamOSPid: System.pid(),
      port: port,
      ip: "127.0.0.1",
      owned: true,
      profile: 1
    },
    pretty: true
  )
)

Application.put_env(:mixer_raw_capture_candidate, :wire_port, port)

defmodule MixerRawCapture.WireTest do
  use ExUnit.Case, async: false
  import MixerRawCapture.WireHelpers
  def port, do: Application.fetch_env!(:mixer_raw_capture_candidate, :wire_port)

  def accepted(result, body, verify \\ "ok") do
    assert result.statuses == [418], inspect(result)
    assert result.event.outcome == "captured", inspect(result)
    assert result.event.bodySHA256 == Base.encode16(:crypto.hash(:sha256, body), case: :lower)
    assert result.event.bodyBytes == byte_size(body)
    assert result.event.signatureValues == result.event.exposedSignatureValues
    assert result.event.verifier == verify
    assert result.event.verifierCalls == 1 and result.event.domainCalls == 0
  end

  def rejected(result, before_read \\ false) do
    refute Enum.any?(result.statuses, &(&1 in 200..299)), inspect(result)
    refute result.serverEnd == "harness_deadline", inspect(result)

    if result.event do
      refute result.event.outcome == "captured", inspect(result)
      assert result.event.verifierCalls == 0 and result.event.domainCalls == 0
      if before_read, do: assert(result.event.reads == 0, inspect(result))
    end
  end

  test "H1 exact body bytes and unchanged signature boundary" do
    for {id, body} <- [
          {"h1-json", ~s({"a":1})},
          {"h1-newline", "{ \r\n\"a\": 1\n}\r\n"},
          {"h1-utf8", ~s({"é":"😺"})},
          {"h1-escape", ~S({"x":"\u00e9"})},
          {"h1-binary", <<0, 255, 13, 10, 195, 169>>}
        ] do
      accepted(tcp(port(), id, body), body)
    end

    original = ~s({"a":"é"})

    for {id, body} <- [
          {"h1-mut-space", ~s({ "a":"é"})},
          {"h1-mut-newline", original <> "\n"},
          {"h1-mut-escape", ~S({"a":"\u00e9"})}
        ] do
      accepted(tcp(port(), id, body, headers: headers(original)), body, "invalid")
    end
  end

  test "H1 raw method and path envelope rejects before body read" do
    for {id, opts} <- [
          {"h1-head", [method: "HEAD"]},
          {"h1-get", [method: "GET"]},
          {"h1-slash", [path: "/api/v1/webhooks/stripe/"]},
          {"h1-query", [path: "/api/v1/webhooks/stripe?x=1"]},
          {"h1-percent", [path: "/api/v1/webhooks/%73tripe"]},
          {"h1-case", [path: "/API/v1/webhooks/stripe"]},
          {"h1-10", [version: "HTTP/1.0"]}
        ] do
      rejected(tcp(port(), id, "a", opts), true)
    end
  end

  test "H1 content metadata exact variants and rejected duplicates" do
    for {id, ct} <- [
          {"h1-ct-ascii", "Application/JSON"},
          {"h1-ct-charset", "application/json ; CHARSET = utf-8"}
        ] do
      accepted(tcp(port(), id, "a", headers: replace(headers("a"), "Content-Type", [ct])), "a")
    end

    bad = [
      [],
      [""],
      ["text/json"],
      ["application/json, application/json"],
      ["application/json;charset=latin1"],
      ["application/json;charset=\"utf-8\""],
      ["application/json;x=y"],
      ["application/json;charset=utf-8;charset=utf-8"],
      ["application/json", "application/json"],
      [String.duplicate("a", 129)]
    ]

    for {values, n} <- Enum.with_index(bad) do
      rejected(
        tcp(port(), "h1-ct-bad-#{n}", "a",
          headers: replace(headers("a"), "Content-Type", values)
        ),
        true
      )
    end

    for {header, value, n} <- [
          {"Content-Encoding", "identity", 1},
          {"Content-Encoding", "gzip", 2},
          {"Content-Encoding", "", 3},
          {"Expect", "100-continue", 4},
          {"Trailer", "x-future", 5},
          {"Upgrade", "websocket", 6}
        ] do
      rejected(tcp(port(), "h1-meta-#{n}", "a", headers: headers("a") ++ [{header, value}]), true)
    end
  end

  test "H1 signature occurrences remain separate with exact exposed values" do
    for {values, n} <- Enum.with_index([[], [""], ["one", "two"], [String.duplicate("x", 4097)]]) do
      result =
        tcp(port(), "h1-sig-bad-#{n}", "a",
          headers: replace(headers("a"), "Stripe-Signature", values)
        )

      rejected(result, true)

      if result.event,
        do: assert(Enum.sort(result.event.exposedSignatureValues) == Enum.sort(values))
    end

    for {value, n} <- Enum.with_index(["x", "t=1,v1=a,other=b", String.duplicate("x", 4096)]) do
      result =
        tcp(port(), "h1-sig-limit-#{n}", "a",
          headers: replace(headers("a"), "sTrIpE-sIgNaTuRe", [value])
        )

      accepted(result, "a", "invalid")
      assert result.event.signatureValues == [value]
    end

    result =
      tcp(port(), "h1-sig-mixed-duplicate", "a",
        headers: [
          {"Content-Type", "application/json"},
          {"Stripe-Signature", "one"},
          {"sTrIpE-sIgNaTuRe", "two"}
        ]
      )

    rejected(result, true)
    assert Enum.sort(result.event.exposedSignatureValues) == ["one", "two"]
  end

  test "H1 canonical and framework-rejected content length" do
    accepted(tcp(port(), "h1-length-one", "a"), "a")

    for {framing, n} <-
          Enum.with_index([
            [],
            [{"Content-Length", "0"}],
            [{"Content-Length", "01"}],
            [{"Content-Length", "+1"}],
            [{"Content-Length", "-1"}],
            [{"Content-Length", "1, 1"}],
            [{"Content-Length", "1"}, {"Content-Length", "1"}],
            [{"Content-Length", "1"}, {"Content-Length", "2"}],
            [{"Content-Length", "999999999999999999999999"}],
            [{"Content-Length", "1048577"}]
          ]) do
      rejected(tcp(port(), "h1-length-bad-#{n}", "a", framing: framing), true)
    end

    rejected(
      tcp(port(), "h1-length-early-eof", "a",
        framing: [{"Content-Length", "2"}],
        half_close: true
      )
    )
  end

  test "H1 normal chunked boundaries extensions and invisible trailers" do
    body = "RAW_BODY_SENTINEL\r\n{" <> "\"x\":\"é\"}"

    wire =
      "3;local=x\r\n" <>
        binary_part(body, 0, 3) <>
        "\r\n" <>
        Integer.to_string(byte_size(body) - 3, 16) <>
        "\r\n" <> binary_part(body, 3, byte_size(body) - 3) <> "\r\n0\r\n\r\n"

    accepted(
      tcp(port(), "h1-chunked", body,
        framing: [{"Transfer-Encoding", "chunked"}],
        parts: [{0, wire}]
      ),
      body
    )

    trailer =
      Integer.to_string(byte_size(body), 16) <>
        "\r\n" <> body <> "\r\n0\r\nx-synthetic: RAW_TRAILER_SENTINEL\r\n\r\n"

    accepted(
      tcp(port(), "h1-undeclared-trailer", body,
        framing: [{"Transfer-Encoding", "chunked"}],
        parts: [{0, trailer}]
      ),
      body
    )

    for {framing, n} <-
          Enum.with_index([
            [{"Content-Length", "1"}, {"Transfer-Encoding", "chunked"}],
            [{"Transfer-Encoding", "chunked"}, {"Transfer-Encoding", "chunked"}],
            [{"Transfer-Encoding", "identity"}],
            [{"Transfer-Encoding", "gzip"}],
            [{"Transfer-Encoding", "gzip, chunked"}]
          ]) do
      rejected(tcp(port(), "h1-framing-bad-#{n}", "a", framing: framing), true)
    end

    for {wire, n} <- Enum.with_index(["z\r\na\r\n0\r\n\r\n", "4\r\nab", "1\r\na\r\n0\r\n"]) do
      rejected(
        tcp(port(), "h1-chunk-malformed-#{n}", "a",
          framing: [{"Transfer-Encoding", "chunked"}],
          parts: [{0, wire}],
          half_close: true
        )
      )
    end
  end

  test "H1 real maximum and streaming ceiling" do
    max = String.duplicate("a", 1_048_576)
    accepted(tcp(port(), "h1-max-cl", max), max)
    wire = Integer.to_string(byte_size(max), 16) <> "\r\n" <> max <> "\r\n0\r\n\r\n"

    result =
      tcp(port(), "h1-max-chunked", max,
        framing: [{"Transfer-Encoding", "chunked"}],
        parts: [{0, wire}]
      )

    rejected(result)
    assert result.event.reason == "too_large"
    over = max <> "a"
    wire = Integer.to_string(byte_size(over), 16) <> "\r\n" <> over <> "\r\n0\r\n\r\n"

    rejected(
      tcp(port(), "h1-over-chunked", over,
        framing: [{"Transfer-Encoding", "chunked"}],
        parts: [{0, wire}]
      )
    )
  end

  test "H1 failure close prevents pipelined second request and body timeout" do
    second =
      "POST /api/v1/webhooks/stripe HTTP/1.1\r\nHost: localhost\r\nX-Capture-Test: forbidden-pipeline\r\nContent-Length: 1\r\nContent-Type: application/json\r\nStripe-Signature: x\r\n\r\na"

    result =
      tcp(port(), "h1-pipeline", "a",
        headers: replace(headers("a"), "Stripe-Signature", []),
        parts: [{0, "a" <> second}]
      )

    rejected(result, true)
    assert length(result.statuses) <= 1 and event("forbidden-pipeline") == nil
    result = tcp(port(), "h1-no-body", "a", parts: [])
    rejected(result)
    assert result.event.reads == 1
    result = tcp(port(), "h1-slow-gap", "ab", parts: [{0, "a"}, {1_200, "b"}])
    rejected(result)
  end

  test "HTTP2 actual DATA END_STREAM exact body and coalesced target overshoot" do
    body = "RAW_BODY_SENTINEL_" <> String.duplicate("a", 44_983)

    accepted(
      h2(port(), "h2-exact", body,
        parts: [
          {0, binary_part(body, 0, 16_384)},
          {0, binary_part(body, 16_384, 16_384)},
          {0, binary_part(body, 32_768, byte_size(body) - 32_768)}
        ]
      ),
      body
    )

    accepted(h2(port(), "h2-with-length", "a", framing: [{"content-length", "1"}]), "a")
    accepted(h2(port(), "h2-small-split", "abc", parts: [{0, "a"}, {30, "b"}, {30, "c"}]), "abc")
  end

  test "HTTP2 metadata duplicate signature and length failures" do
    for {values, n} <- Enum.with_index([[], [""], ["one", "two"], [String.duplicate("x", 4097)]]) do
      result =
        h2(port(), "h2-sig-bad-#{n}", "a",
          headers: replace(headers("a"), "Stripe-Signature", values)
        )

      rejected(result, true)

      if result.event,
        do: assert(Enum.sort(result.event.exposedSignatureValues) == Enum.sort(values))
    end

    for {header, value, n} <- [
          {"content-encoding", "identity", 1},
          {"expect", "100-continue", 2},
          {"trailer", "x-future", 3},
          {"te", "trailers", 4}
        ] do
      rejected(
        h2(port(), "h2-meta-bad-#{n}", "a", headers: headers("a") ++ [{header, value}]),
        true
      )
    end

    for {length, n} <- Enum.with_index(["0", "01", "1, 1", "1048577"]) do
      rejected(h2(port(), "h2-length-bad-#{n}", "a", framing: [{"content-length", length}]), true)
    end

    rejected(h2(port(), "h2-length-short", "a", framing: [{"content-length", "2"}]))
    rejected(h2(port(), "h2-length-over", "ab", framing: [{"content-length", "1"}]))

    rejected(
      h2(port(), "h2-length-dupe", "a",
        framing: [{"content-length", "1"}, {"content-length", "1"}]
      ),
      true
    )

    rejected(
      h2(port(), "h2-ct-dupe", "a",
        headers: headers("a") ++ [{"content-type", "application/json"}]
      ),
      true
    )

    rejected(h2(port(), "h2-method", "a", method: "HEAD"), true)
    rejected(h2(port(), "h2-path", "a", path: "/api/v1/webhooks/stripe?x=1"), true)
  end

  test "HTTP2 exact signature limits metadata variants and empty DATA" do
    for {value, n} <- Enum.with_index(["x", "t=1,v1=a,other=b", String.duplicate("x", 4096)]) do
      accepted(
        h2(port(), "h2-sig-limit-#{n}", "a",
          headers: replace(headers("a"), "Stripe-Signature", [value])
        ),
        "a",
        "invalid"
      )
    end

    for {ct, n} <- Enum.with_index(["Application/JSON", "application/json ; CHARSET = utf-8"]) do
      accepted(
        h2(port(), "h2-ct-valid-#{n}", "a", headers: replace(headers("a"), "Content-Type", [ct])),
        "a"
      )
    end

    for {ct, n} <-
          Enum.with_index([
            "",
            "application/json, application/json",
            "application/json;charset=utf-16",
            "application/json;x=y"
          ]) do
      rejected(
        h2(port(), "h2-ct-invalid-#{n}", "a",
          headers: replace(headers("a"), "Content-Type", [ct])
        ),
        true
      )
    end

    rejected(h2(port(), "h2-empty", ""))
    rejected(h2(port(), "h2-no-data", "a", parts: [], finish: false))
    slow = h2(port(), "h2-slow-gap", "ab", parts: [{0, "a"}, {1_200, "b"}])
    accepted(slow, "ab")
    assert slow.event.reads == 2
  end

  test "HTTP2 undeclared trailer log exposure observed with synthetic sentinel" do
    body = "RAW_BODY_SENTINEL"
    # An opaque signature sentinel is accepted by capture but fails verification.
    hdr = replace(headers(body), "Stripe-Signature", ["RAW_SIG_SENTINEL"])

    accepted(
      h2(port(), "h2-trailer", body,
        headers: hdr,
        eof: {:eof, [{"x-synthetic", "RAW_TRAILER_SENTINEL"}]}
      ),
      body,
      "invalid"
    )

    accepted(tcp(port(), "h1-telemetry-sentinel", body, headers: hdr), body, "invalid")
    Process.sleep(20)
    assert Enum.any?(MixerRawCapture.WireState.get(:logs), & &1.trailerSeen)
    assert Enum.any?(MixerRawCapture.WireState.get(:telemetry), & &1.bodySeen)
    assert Enum.any?(MixerRawCapture.WireState.get(:telemetry), & &1.signatureSeen)

    assert Enum.any?(MixerRawCapture.WireState.get(:telemetry), fn entry ->
             entry.event == ["thousand_island", "connection", "recv"] and
               entry.measurementBodySeen
           end)

    assert Enum.any?(MixerRawCapture.WireState.get(:telemetry), fn entry ->
             entry.event == ["thousand_island", "connection", "recv"] and
               entry.measurementSignatureSeen
           end)
  end

  test "HTTP2 successive DATA receives exceed success deadline without hard cancellation" do
    body = String.duplicate("a", 55)
    parts = List.duplicate({100, "a"}, 55)
    result = h2(port(), "h2-late-success", body, parts: parts)
    rejected(result)
    assert result.event.outcome == "capture-rejected" and result.event.reason == "read_deadline"
    assert result.event.elapsedMs >= 5_000
    # This demonstrates late-result refusal, and directly disproves claiming
    # five-second forced cancellation from this component alone.
  end
end

try do
  summary = ExUnit.run()
  Process.sleep(40)
  result = System.fetch_env!("CAPTURE_RESULT_DIR")

  for key <- [:events, :clients, :telemetry, :logs, :socketCleanup] do
    File.write!(
      Path.join(result, "#{key}.json"),
      Jason.encode!(MixerRawCapture.WireState.get(key), pretty: true)
    )
  end

  File.write!(Path.join(result, "wire-summary.json"), Jason.encode!(summary, pretty: true))
  if summary.failures != 0, do: Process.put(:wire_failed, true)
after
  :telemetry.detach("capture-synthetic-probe")
  :logger.remove_handler(:capture_synthetic_probe)
  :ok = ThousandIsland.stop(listener, 1_000)

  closed =
    case :gen_tcp.connect({127, 0, 0, 1}, port, [:binary, active: false], 100) do
      {:error, :econnrefused} ->
        true

      {:ok, socket} ->
        :gen_tcp.close(socket)
        false

      _ ->
        false
    end

  File.write!(
    Path.join(System.fetch_env!("CAPTURE_RESULT_DIR"), "listener-cleanup.json"),
    Jason.encode!(
      %{
        listenerStopped: not Process.alive?(listener),
        port: port,
        connectRefused: closed,
        telemetryDetached: true,
        loggerHandlerRemoved: true
      },
      pretty: true
    )
  )
end

if Process.get(:wire_failed), do: System.halt(1)

