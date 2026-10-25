defmodule MixerHostedWeb.CustomerArtifactTransportTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.CustomerArtifactController, as: Controller
  alias MixerHostedWeb.Plugs.{BearerIdentity, CustomerArtifactRequest}

  @digest String.duplicate("a", 64)
  @path "/v3/orgs/org-a/projects/project-a/artifacts/#{@digest}"
  @body " {\"payload\":\"cGF5bG9hZA==\", \"signed_manifest\":{}}\n"
  @maximum 6_291_456

  defmodule Verifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, now) do
      send(self(), {:verified, token, now})
      Process.get(:artifact_transport_identity)
    end
  end

  defmodule Facade do
    def upload_at(identity, route, digest, key, bytes, metadata) do
      send(self(), {:upload, identity, route, digest, key, bytes, metadata})

      result(
        {:ok,
         %{status: 201, manifest_sha256: digest, payload_sha256: "internal", event_sequence: 99}}
      )
    end

    def read(identity, route, digest, metadata) do
      send(self(), {:read, identity, route, digest, metadata})

      result(
        {:ok,
         %{
           manifest_sha256: digest,
           envelope_bytes: " {\"retained\":true}\n",
           payload_sha256: "private"
         }}
      )
    end

    def audit(identity, route, after_sequence, limit, metadata) do
      send(self(), {:audit, identity, route, after_sequence, limit, metadata})
      result({:ok, %{events: [], next_after_sequence: after_sequence}})
    end

    defp result(default) do
      case Process.get(:artifact_transport_result, default) do
        :raise -> raise("private database credential")
        :throw -> throw("private provider response")
        other -> other
      end
    end
  end

  defmodule Adapter do
    def read_req_body(%{inner: inner, mode: mode} = state, opts) do
      send(self(), {:body_read, opts})

      case mode do
        :raise ->
          raise("private request bytes")

        :throw ->
          throw("private request bytes")

        :error ->
          {:error, :timeout}

        :empty_more ->
          {:more, "", state}

        :deadline ->
          Process.put(:artifact_transport_milliseconds, 15_000)
          {:ok, "", state}

        :chunks ->
          length = min(Keyword.fetch!(opts, :length), 7)
          {tag, bytes, inner} = Plug.Adapters.Test.Conn.read_req_body(inner, length: length)
          {tag, bytes, %{state | inner: inner}}

        _ ->
          {tag, bytes, inner} = Plug.Adapters.Test.Conn.read_req_body(inner, opts)
          {tag, bytes, %{state | inner: inner}}
      end
    end

    def send_resp(state, status, headers, body) do
      {:ok, body, inner} = Plug.Adapters.Test.Conn.send_resp(state.inner, status, headers, body)
      {:ok, body, %{state | inner: inner}}
    end
  end

  def unix_seconds, do: 1_800_000_000
  def milliseconds, do: Process.get(:artifact_transport_milliseconds, 0)

  setup do
    Process.put(:artifact_transport_milliseconds, 0)
    Process.put(:artifact_transport_identity, {:ok, identity()})
    :ok
  end

  defp identity(scopes \\ ["mixer.artifact.upload", "mixer.artifact.read", "mixer.audit.read"]) do
    %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://identity.invalid",
      subject: "subject",
      client_id: "client",
      credential_ref: "credential",
      issued_at: unix_seconds() - 1,
      expires_at: unix_seconds() + 100,
      identity_class: :human,
      scopes: scopes
    }
  end

  defp request(operation \\ :upload, opts \\ []) do
    method = Keyword.get(opts, :method, if(operation == :upload, do: :put, else: :get))

    path =
      Keyword.get(
        opts,
        :path,
        if(operation == :audit, do: "/v3/orgs/org-a/projects/project-a/audit", else: @path)
      )

    query = Keyword.get(opts, :query, "")
    body = Keyword.get(opts, :body, if(operation == :upload, do: @body, else: ""))

    headers =
      Keyword.get(opts, :headers, [
        {"authorization", "Bearer opaque.Token"},
        {"content-type", "application/json"},
        {"idempotency-key", "upload-1"}
      ])

    conn = conn(method, path <> if(query == "", do: "", else: "?" <> query), body)
    {_, inner} = conn.adapter

    %{
      conn
      | req_headers: headers,
        path_params: %{
          "organization_id" => "org-a",
          "project_id" => "project-a",
          "manifest_sha256" => @digest
        },
        adapter: {Adapter, %{inner: inner, mode: Keyword.get(opts, :mode, :normal)}}
    }
  end

  defp run(conn, operation \\ :upload) do
    bearer = BearerIdentity.init(verifier: Verifier, clock: {__MODULE__, :unix_seconds, []})

    controller =
      Controller.init(
        operation: operation,
        facade: Facade,
        clock: {__MODULE__, :milliseconds, []}
      )

    conn = BearerIdentity.call(conn, bearer)
    if conn.halted, do: conn, else: Controller.call(conn, controller)
  end

  defp assert_error(conn, status, code) do
    assert conn.status == status
    assert conn.halted
    assert get_resp_header(conn, "cache-control") == ["no-store"]
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
    assert get_resp_header(conn, "retry-after") == if(status == 503, do: ["1"], else: [])

    assert %{"error" => %{"code" => ^code, "message" => message}, "request_id" => id} =
             Jason.decode!(conn.resp_body)

    assert get_resp_header(conn, "x-request-id") == [id]
    assert byte_size(message) < 100 and byte_size(conn.resp_body) < 512
    refute conn.resp_body =~ "private"
    conn
  end

  defp no_facade do
    refute_received {:upload, _, _, _, _, _, _}
    refute_received {:read, _, _, _, _}
    refute_received {:audit, _, _, _, _, _}
  end

  test "authentication failure precedes body reads and parameter parsing" do
    conn = request(:upload, headers: [], body: "not json") |> run()
    assert_error(conn, 401, "unauthenticated")
    assert %Plug.Conn.Unfetched{} = conn.query_params
    assert %Plug.Conn.Unfetched{} = conn.body_params
    refute_received {:body_read, _}
    refute_received {:verified, _, _}
    no_facade()
  end

  test "each exact operation scope precedes query, header and body admission" do
    for operation <- [:upload, :read, :audit] do
      Process.put(
        :artifact_transport_identity,
        {:ok, identity(["mixer.artifact.*", "mixer.audit.write"])}
      )

      request(operation, query: "unknown=1", body: "secret")
      |> run(operation)
      |> assert_error(403, "permission_denied")

      assert_received {:verified, "opaque.Token", _}
      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "service identities and forged plain maps cannot reach domain effects" do
    Process.put(:artifact_transport_identity, {:ok, %{identity() | identity_class: :service}})
    request() |> run() |> assert_error(403, "permission_denied")
    refute_received {:body_read, _}
    Process.put(:artifact_transport_identity, {:ok, Map.from_struct(identity())})
    request() |> run() |> assert_error(503, "identity_unavailable")
    refute_received {:body_read, _}
    no_facade()
  end

  test "upload passes only closed route, exact bytes and socket metadata then maps created result" do
    headers = [
      {"authorization", "Bearer opaque.Token"},
      {"content-type", "application/json"},
      {"idempotency-key", "upload_1.A-"},
      {"x-mixer-reason", "  preserve reason  "},
      {"forwarded", "for=203.0.113.55"},
      {"x-forwarded-for", "203.0.113.56"},
      {"cf-connecting-ip", "203.0.113.57"},
      {"x-mixer-actor", "admin"},
      {"x-mixer-request-id", "chosen-audit-id"}
    ]

    conn =
      %{request(:upload, headers: headers) | remote_ip: {0x2001, 0xDB8, 0, 0, 0, 0, 0, 1}}
      |> run()

    assert conn.status == 201
    assert Jason.decode!(conn.resp_body) == %{"artifact_sha256" => @digest, "immutable" => true}

    assert_received {:upload, %VerifiedIdentity{},
                     %{organization_id: "org-a", project_id: "project-a"}, @digest, "upload_1.A-",
                     @body, %{reason: "  preserve reason  ", source_ip: "2001:db8::1"}}

    assert %Plug.Conn.Unfetched{} = conn.body_params
    assert %Plug.Conn.Unfetched{} = conn.query_params
    assert get_resp_header(conn, "cache-control") == ["no-store"]
    assert_received {:verified, _, _}
    assert_received {:body_read, opts}
    assert Keyword.fetch!(opts, :read_timeout) == 15_000
    assert Keyword.fetch!(opts, :read_length) == 65_536
  end

  test "authorized retry retains facade original 201 or 200 status" do
    for status <- [201, 200] do
      Process.put(:artifact_transport_result, {:ok, %{status: status, manifest_sha256: @digest}})
      conn = request() |> run()
      assert conn.status == status
      assert Jason.decode!(conn.resp_body) == %{"artifact_sha256" => @digest, "immutable" => true}
    end
  end

  test "reason absent and empty use exact legacy default; UTF8 boundary preserved" do
    base = [
      {"authorization", "Bearer opaque.Token"},
      {"content-type", "application/json"},
      {"idempotency-key", "key"}
    ]

    for reason <- [nil, "", String.duplicate("é", 256)] do
      headers = if reason == nil, do: base, else: base ++ [{"x-mixer-reason", reason}]
      assert (request(:upload, headers: headers) |> run()).status == 201
      expected = if reason in [nil, ""], do: "local development operation", else: reason
      assert_received {:upload, _, _, _, _, _, %{reason: ^expected, source_ip: "127.0.0.1"}}
    end
  end

  test "duplicate, oversized or invalid UTF8 mutation reason rejects before body" do
    base = [
      {"authorization", "Bearer opaque.Token"},
      {"content-type", "application/json"},
      {"idempotency-key", "key"}
    ]

    for values <- [["same", "same"], [String.duplicate("a", 513)], [<<255>>]] do
      headers = base ++ Enum.map(values, &{"x-mixer-reason", &1})
      request(:upload, headers: headers) |> run() |> assert_error(400, "invalid_reason")
      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "idempotency key enforces unique ASCII 1..128 bytes without colon" do
    base = [{"authorization", "Bearer opaque.Token"}, {"content-type", "application/json"}]

    for values <- [
          [],
          [""],
          ["same", "same"],
          ["one,two"],
          ["a:b"],
          ["é"],
          ["a b"],
          [String.duplicate("a", 129)]
        ] do
      request(:upload, headers: base ++ Enum.map(values, &{"idempotency-key", &1}))
      |> run()
      |> assert_error(400, "idempotency_required")

      refute_received {:body_read, _}
      no_facade()
    end

    assert (request(:upload, headers: base ++ [{"idempotency-key", String.duplicate("a", 128)}])
            |> run()).status == 201
  end

  test "upload requires unique exact application/json before body work" do
    base = [{"authorization", "Bearer opaque.Token"}, {"idempotency-key", "key"}]

    for values <- [
          [],
          ["text/plain"],
          ["application/json; charset=utf-8"],
          ["Application/JSON"],
          ["application/json,application/json"]
        ] do
      request(:upload, headers: base ++ Enum.map(values, &{"content-type", &1}))
      |> run()
      |> assert_error(400, "content_type")

      refute_received {:body_read, _}
      no_facade()
    end

    request(:upload,
      headers:
        base ++ [{"content-type", "application/json"}, {"content-type", "application/json"}]
    )
    |> run()
    |> assert_error(400, "invalid_request")

    refute_received {:body_read, _}
  end

  test "any declared Content-Encoding including duplicate or identity is unsupported" do
    for values <- [["gzip"], ["identity"], [""], ["gzip", "gzip"]] do
      conn = request()

      conn = %{
        conn
        | req_headers: conn.req_headers ++ Enum.map(values, &{"content-encoding", &1})
      }

      conn |> run() |> assert_error(415, "unsupported_content_encoding")
      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "route IDs and digest are bounded closed ASCII fields" do
    for field <- ["organization_id", "project_id"],
        value <- ["", "é", "a:b", "a/b", "a%2Fb", "*", String.duplicate("a", 129)] do
      conn = request()

      %{conn | path_params: Map.put(conn.path_params, field, value)}
      |> run()
      |> assert_error(400, "invalid_request")

      refute_received {:body_read, _}
      no_facade()
    end

    for digest <- [
          String.duplicate("A", 64),
          String.duplicate("a", 63),
          String.duplicate("a", 65),
          String.duplicate("g", 64)
        ] do
      conn = request()

      %{conn | path_params: Map.put(conn.path_params, "manifest_sha256", digest)}
      |> run()
      |> assert_error(400, "invalid_request")

      refute_received {:body_read, _}
      no_facade()
    end

    conn = request()

    assert (%{
              conn
              | path_params: Map.put(conn.path_params, "project_id", String.duplicate("a", 128))
            }
            |> run()).status == 201
  end

  test "upload and artifact read reject any query before body reads" do
    for operation <- [:upload, :read], query <- ["x=1", "after=", "=", "&"] do
      request(operation, query: query) |> run(operation) |> assert_error(400, "invalid_request")
      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "audit defaults absent and empty values and accepts bounded one-decode decimals" do
    for {query, after_sequence, limit} <- [
          {"", 0, 100},
          {"after=&limit=", 0, 100},
          {"after&limit", 0, 100},
          {"after=9007199254740991&limit=1", 9_007_199_254_740_991, 1},
          {"%61fter=%30%30%31&limit=0100", 1, 100}
        ] do
      conn = request(:audit, query: query) |> run(:audit)
      assert conn.status == 200
      assert Jason.decode!(conn.resp_body) == %{"events" => [], "next" => after_sequence}
      assert_received {:audit, _, _, ^after_sequence, ^limit, %{reason: ""}}
      assert %Plug.Conn.Unfetched{} = conn.query_params
    end
  end

  test "audit rejects duplicate unknown malformed or overflow values" do
    for query <- [
          "after=1&after=2",
          "%61fter=1&after=1",
          "limit=1&limit=1",
          "unknown=1",
          "after[]=1",
          "after=+1",
          "after=-1",
          "after=1.0",
          "after=%201",
          "after=9007199254740992",
          "after=00000000000000000",
          "limit=0",
          "limit=101",
          "limit=1e2",
          "after=%",
          "after=%ff",
          "after=%2531",
          "after=1&&limit=1",
          "after=1&",
          "=1"
        ] do
      request(:audit, query: query) |> run(:audit) |> assert_error(400, "invalid_request")
      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "read and audit ignore mutation reason and untrusted actor metadata" do
    for operation <- [:read, :audit] do
      headers = [
        {"authorization", "Bearer opaque.Token"},
        {"x-mixer-reason", <<255>>},
        {"x-mixer-reason", "ignored"},
        {"x-mixer-actor", "owner"}
      ]

      assert (request(operation, headers: headers) |> run(operation)).status == 200

      if operation == :read,
        do: assert_received({:read, _, _, _, %{reason: "", source_ip: "127.0.0.1"}}),
        else: assert_received({:audit, _, _, _, _, %{reason: "", source_ip: "127.0.0.1"}})
    end
  end

  test "read emits original retained bytes with JSON media and no internal columns" do
    conn = request(:read) |> run(:read)
    assert conn.status == 200
    assert conn.resp_body == " {\"retained\":true}\n"
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
    assert get_resp_header(conn, "cache-control") == ["no-store"]
  end

  test "audit preserves validated schema2 events without legacy actor fabrication" do
    event = %{"audit_schema" => 2, "actor" => %{"principal_id" => "principal"}, "sequence" => 7}
    Process.put(:artifact_transport_result, {:ok, %{events: [event], next_after_sequence: 7}})
    conn = request(:audit) |> run(:audit)
    assert Jason.decode!(conn.resp_body) == %{"events" => [event], "next" => 7}
  end

  test "GET and HEAD require empty actual body regardless of absent or zero Content-Length" do
    for operation <- [:read, :audit], method <- [:get, :head] do
      conn =
        request(operation,
          method: method,
          body: "x",
          headers: [{"authorization", "Bearer opaque.Token"}, {"content-length", "0"}]
        )

      # Keep GET at the adapter for JSON error assertions; HEAD wire stripping has
      # a separate assertion below and the real Bandit lane verifies sockets.
      {adapter, state} = conn.adapter
      conn = %{conn | adapter: {adapter, %{state | inner: %{state.inner | method: "GET"}}}}
      conn |> run(operation) |> assert_error(400, "invalid_request")
      no_facade()
    end
  end

  test "GET media is absent or single exact JSON after scope" do
    for operation <- [:read, :audit] do
      conn =
        request(operation,
          headers: [{"authorization", "Bearer opaque.Token"}, {"content-type", "text/plain"}]
        )

      conn |> run(operation) |> assert_error(400, "content_type")
      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "body bytes at inclusive maximum pass unchanged and one byte over fails before facade" do
    padding = @maximum - byte_size(@body)
    maximum = @body <> String.duplicate(" ", padding)
    assert (request(:upload, body: maximum) |> run()).status == 201
    assert_received {:upload, _, _, _, _, ^maximum, _}
    request(:upload, body: maximum <> " ") |> run() |> assert_error(413, "body_too_large")
    no_facade()
  end

  test "partial body chunks preserve original byte order" do
    assert (request(:upload, mode: :chunks) |> run()).status == 201
    assert_received {:upload, _, _, _, _, @body, _}
  end

  test "read failures exceptions fixed deadline and chunk count reject with bounded errors" do
    for mode <- [:error, :raise, :throw, :deadline, :empty_more] do
      Process.put(:artifact_transport_milliseconds, 0)
      request(:upload, mode: mode) |> run() |> assert_error(400, "malformed_body")
      no_facade()
    end

    reads = collect_reads([])
    assert length(reads) == 132
    assert Enum.all?(reads, &(Keyword.fetch!(&1, :read_timeout) <= 15_000))
  end

  defp collect_reads(acc) do
    receive do
      {:body_read, opts} -> collect_reads([opts | acc])
    after
      0 -> acc
    end
  end

  test "invalid syntax duplicate keys UTF8 unknown and non-object envelopes are invalid_json400" do
    for bytes <- [
          "",
          "{}",
          "[]",
          "{} {}",
          ~s({"signed_manifest":[],"payload":"x"}),
          ~s({"signed_manifest":{},"payload":[]}),
          ~s({"signed_manifest":null,"payload":"x"}),
          ~s({"signed_manifest":{},"payload":null}),
          "{\"signed_manifest\":{},\"payload\":\"x\",\"extra\":true}",
          "{\"signed_manifest\":{},\"payload\":\"x\",\"payload\":\"x\"}",
          "{\"signed_manifest\":{\"x\":1,\"x\":1},\"payload\":\"x\"}",
          "{\"signed_manifest\":{},\"payload\":\"" <> <<255>> <> "\"}"
        ] do
      request(:upload, body: bytes) |> run() |> assert_error(400, "invalid_json")
      no_facade()
    end
  end

  test "facade errors map generic statuses and never leak private details" do
    for {reason, status, code} <- [
          {:invalid_request, 400, "invalid_request"},
          {:unauthenticated, 401, "unauthenticated"},
          {:permission_denied, 403, "permission_denied"},
          {:not_found, 404, "not_found"},
          {:immutable_conflict, 409, "immutable_conflict"},
          {:idempotency_conflict, 409, "idempotency_conflict"},
          {:conflict, 409, "conflict"},
          {:artifact_invalid, 422, "artifact_invalid"},
          {:digest_mismatch, 422, "digest_mismatch"},
          {:authorization_unavailable, 503, "authorization_unavailable"},
          {:storage_unavailable, 503, "storage_unavailable"},
          {{:secret, "private database credential"}, 503, "storage_unavailable"}
        ] do
      Process.put(:artifact_transport_result, {:error, reason})
      request() |> run() |> assert_error(status, code)
      assert_received {:upload, _, _, _, _, _, _}
    end

    for result <- [
          :raise,
          :throw,
          :unexpected,
          {:ok, %{status: 201, manifest_sha256: String.duplicate("b", 64)}}
        ] do
      Process.put(:artifact_transport_result, result)
      request() |> run() |> assert_error(503, "storage_unavailable")
    end
  end

  test "error metadata removes duplicate stale challenge and retry advice" do
    Process.put(:artifact_transport_result, {:error, :permission_denied})
    conn = request()

    conn = %{
      conn
      | resp_headers: [
          {"cache-control", "public"},
          {"cache-control", "max-age=999"},
          {"retry-after", "123"},
          {"retry-after", "321"},
          {"www-authenticate", "Basic"},
          {"x-request-id", "bad"},
          {"x-request-id", "also-bad"}
        ]
    }

    conn = conn |> run() |> assert_error(403, "permission_denied")
    assert get_resp_header(conn, "www-authenticate") == []
  end

  test "successful responses clear stale challenge retry and duplicate content types" do
    conn = request()

    conn = %{
      conn
      | resp_headers: [
          {"content-type", "text/plain"},
          {"content-type", "image/png"},
          {"retry-after", "999"},
          {"retry-after", "888"},
          {"www-authenticate", "Basic"},
          {"www-authenticate", "Digest"}
        ]
    }

    conn = run(conn)
    assert conn.status == 201
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
    assert get_resp_header(conn, "www-authenticate") == []
    assert get_resp_header(conn, "retry-after") == []
    assert get_resp_header(conn, "cache-control") == ["no-store"]
  end

  test "production router protects only supported paths with existing bearer defaults" do
    for {method, path} <- [
          {:put, @path},
          {:get, @path},
          {:get, "/v3/orgs/org-a/projects/project-a/audit"}
        ] do
      conn = request(:upload, method: method, path: path, headers: [])

      conn
      |> MixerHostedWeb.Router.call(MixerHostedWeb.Router.init([]))
      |> assert_error(401, "unauthenticated")

      refute_received {:body_read, _}
      no_facade()
    end

    for {method, path} <- [
          {:post, @path},
          {:get, "/v3/orgs/org-a/projects/project-a/artifacts"},
          {:get, @path <> "/extra"}
        ] do
      assert_raise Phoenix.Router.NoRouteError, fn ->
        request(:read, method: method, path: path)
        |> MixerHostedWeb.Router.call(MixerHostedWeb.Router.init([]))
      end

      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "HEAD through Plug.Head retains action authorization and adapter strips body" do
    conn = request(:read, method: :head) |> Plug.Head.call(Plug.Head.init([])) |> run(:read)
    assert conn.status == 200
    assert conn.resp_body == ""
    assert_received {:read, _, _, @digest, _}
    assert get_resp_header(conn, "cache-control") == ["no-store"]
    Process.put(:artifact_transport_identity, {:ok, identity([])})
    conn = request(:read, method: :head) |> Plug.Head.call(Plug.Head.init([])) |> run(:read)
    assert conn.status == 403
    assert conn.resp_body == ""
    no_facade()
  end

  test "init seams reject untrusted shapes and unknown dependency choices" do
    for options <- [
          [operation: :upload, facade: Facade, facade: Facade],
          [operation: :upload, facade: "module"],
          [operation: :upload, facade: Facade, repo: Facade],
          [operation: :unknown, facade: Facade]
        ] do
      assert_raise ArgumentError, fn -> Controller.init(options) end
    end

    assert_raise ArgumentError, fn ->
      CustomerArtifactRequest.init(operation: :upload, clock: {String, :not_a_clock, []})
    end

    assert Controller.init(:upload).facade == MixerHosted.CustomerArtifacts
  end
end
