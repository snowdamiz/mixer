defmodule MixerHostedWeb.CustomerArtifactIndependentReviewTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.CustomerArtifactController, as: Controller
  alias MixerHostedWeb.Plugs.{BearerIdentity, CustomerArtifactRequest}
  @digest String.duplicate("a", 64)
  @path "/v3/orgs/org-a/projects/project-a/artifacts/#{@digest}"
  @body ~s({"signed_manifest":{},"payload":"eA=="})
  @maximum 6_291_456

  defmodule Verifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, _now) do
      send(self(), {:review_verify, token})
      Process.get(:review_identity)
    end
  end

  defmodule Facade do
    def upload_at(_identity, route, digest, key, bytes, metadata) do
      send(self(), {:review_facade, :upload, route, digest, key, bytes, metadata})
      result({:ok, %{status: 201, manifest_sha256: digest}})
    end

    def read(_identity, route, digest, metadata) do
      send(self(), {:review_facade, :read, route, digest, metadata})
      result({:ok, %{manifest_sha256: digest, envelope_bytes: " exact retained bytes\n"}})
    end

    def audit(_identity, route, after_sequence, limit, metadata) do
      send(self(), {:review_facade, :audit, route, after_sequence, limit, metadata})
      result({:ok, %{events: [], next_after_sequence: after_sequence}})
    end

    defp result(default) do
      case Process.get(:review_result, default) do
        :raise -> raise("REVIEW_PRIVATE_DATABASE_SECRET")
        :throw -> throw("REVIEW_PRIVATE_PROVIDER_BODY")
        other -> other
      end
    end
  end

  defmodule IncompleteFacade do
    def upload_at(_, _, _, _, _, _), do: :unexpected
  end

  defmodule Adapter do
    def read_req_body(state, options) do
      send(self(), {:review_body_read, options})

      case Process.get(:review_reads, :normal) do
        :normal ->
          {tag, bytes, inner} = Plug.Adapters.Test.Conn.read_req_body(state.inner, options)
          {tag, bytes, %{state | inner: inner}}

        :raise ->
          raise("REVIEW_PRIVATE_RAW_BODY")

        :throw ->
          throw("REVIEW_PRIVATE_RAW_BODY")

        [{tag, bytes, advance} | remaining] ->
          Process.put(:review_reads, remaining)
          Process.put(:review_clock, Process.get(:review_clock, 0) + advance)
          {tag, bytes, state}

        [] ->
          {:error, :closed}
      end
    end

    def send_resp(state, status, headers, bytes) do
      {:ok, bytes, inner} = Plug.Adapters.Test.Conn.send_resp(state.inner, status, headers, bytes)
      {:ok, bytes, %{state | inner: inner}}
    end
  end

  def seconds, do: 1_800_000_000

  def milliseconds do
    case Process.get(:review_clock, 0) do
      :raise -> raise("REVIEW_PRIVATE_CLOCK")
      :throw -> throw("REVIEW_PRIVATE_CLOCK")
      value -> value
    end
  end

  setup do
    Process.put(:review_clock, 0)
    Process.put(:review_reads, :normal)
    Process.put(:review_identity, {:ok, identity()})
    :ok
  end

  defp identity(scopes \\ ~w(mixer.artifact.upload mixer.artifact.read mixer.audit.read)) do
    %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://review.invalid",
      subject: "subject",
      client_id: "client",
      credential_ref: "token",
      issued_at: seconds() - 1,
      expires_at: seconds() + 100,
      identity_class: :human,
      scopes: scopes
    }
  end

  defp request(operation \\ :upload, options \\ []) do
    path =
      Keyword.get(
        options,
        :path,
        if(operation == :audit, do: "/v3/orgs/org-a/projects/project-a/audit", else: @path)
      )

    method = Keyword.get(options, :method, if(operation == :upload, do: :put, else: :get))
    body = Keyword.get(options, :body, if(operation == :upload, do: @body, else: ""))
    query = Keyword.get(options, :query, "")
    conn = conn(method, path <> if(query == "", do: "", else: "?" <> query), body)
    {_, inner} = conn.adapter

    %{
      conn
      | adapter: {Adapter, %{inner: inner}},
        path_params: %{
          "organization_id" => "org-a",
          "project_id" => "project-a",
          "manifest_sha256" => @digest
        },
        req_headers:
          Keyword.get(options, :headers, [
            {"authorization", "Bearer review.Token"},
            {"content-type", "application/json"},
            {"idempotency-key", "review-key"}
          ])
    }
  end

  defp run(conn, operation \\ :upload) do
    conn =
      BearerIdentity.call(
        conn,
        BearerIdentity.init(
          verifier: Verifier,
          clock: {__MODULE__, :seconds, []}
        )
      )

    if conn.halted,
      do: conn,
      else:
        Controller.call(
          conn,
          Controller.init(
            operation: operation,
            facade: Facade,
            clock: {__MODULE__, :milliseconds, []}
          )
        )
  end

  defp error(conn, status, code) do
    assert conn.status == status
    assert conn.halted
    assert get_resp_header(conn, "cache-control") == ["no-store"]
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
    assert get_resp_header(conn, "retry-after") == if(status == 503, do: ["1"], else: [])

    assert %{"error" => %{"code" => ^code, "message" => message}, "request_id" => id} =
             Jason.decode!(conn.resp_body)

    assert get_resp_header(conn, "x-request-id") == [id]
    assert byte_size(message) < 100 and byte_size(conn.resp_body) < 512
    refute conn.resp_body =~ "REVIEW_PRIVATE"
    conn
  end

  defp no_effects do
    refute_received {:review_facade, _, _, _, _, _, _}
    refute_received {:review_facade, _, _, _, _, _}
    refute_received {:review_facade, _, _, _, _}
  end

  test "independent credential and action denial precedes even a throwing body adapter" do
    Process.put(:review_reads, :throw)
    request(:upload, headers: []) |> run() |> error(401, "unauthenticated")
    refute_received {:review_verify, _}
    refute_received {:review_body_read, _}

    for operation <- [:upload, :read, :audit] do
      Process.put(:review_identity, {:ok, identity([])})
      request(operation) |> run(operation) |> error(403, "permission_denied")
      assert_received {:review_verify, "review.Token"}
      refute_received {:review_body_read, _}
      no_effects()
    end
  end

  test "independent encoded alternative credentials reject before verification and body" do
    for query <- ["%61ccess_token=x", "access_token%5Bx%5D=x", "x=1&access_token=x"] do
      request(:upload, query: query) |> run() |> error(400, "invalid_request")
      refute_received {:review_verify, _}
      refute_received {:review_body_read, _}
      no_effects()
    end
  end

  test "independent escaped duplicate and closed-shape aliases never reach the facade" do
    for bytes <- [
          ~S({"signed_manifest":{},"payload":"x","\u0070ayload":"x"}),
          ~S({"signed_manifest":{"a":1,"\u0061":2},"payload":"x"}),
          ~s({"Signed_Manifest":{},"payload":"x"}),
          ~s({"signed_manifest":{},"Payload":"x"}),
          ~s({"signed_manifest":{},"payload":"x","actor":"owner"})
        ] do
      request(:upload, body: bytes) |> run() |> error(400, "invalid_json")
      no_effects()
    end
  end

  test "independent declared encoding and media ambiguity reject before body" do
    base = [{"authorization", "Bearer review.Token"}, {"idempotency-key", "review-key"}]

    for headers <- [
          base ++ [{"content-type", "application/json"}, {"content-encoding", ""}],
          base ++ [{"content-type", "application/json"}, {"content-encoding", "identity"}],
          base ++ [{"content-type", "application/json"}, {"content-encoding", "gzip"}]
        ] do
      request(:upload, headers: headers) |> run() |> error(415, "unsupported_content_encoding")
      refute_received {:review_body_read, _}
      no_effects()
    end

    request(:upload,
      headers:
        base ++ [{"content-type", "application/json"}, {"content-type", "application/json"}]
    )
    |> run()
    |> error(400, "invalid_request")

    refute_received {:review_body_read, _}
    no_effects()
  end

  test "independent pagination rejects decoded duplicates double-decode aliases and unknown names" do
    for query <- [
          "after=1&%61fter=2",
          "%6cimit=1&limit=2",
          "%2561fter=1",
          "after=%2531",
          "after%5Bx%5D=1",
          "after=1&actor=owner",
          "after=+1",
          "limit=1%26after=2",
          "after=9007199254740992"
        ] do
      request(:audit, query: query) |> run(:audit) |> error(400, "invalid_request")
      refute_received {:review_body_read, _}
      no_effects()
    end

    assert (request(:audit, query: "after=&limit=") |> run(:audit)).status == 200
    assert_received {:review_facade, :audit, _, 0, 100, %{reason: ""}}
  end

  test "independent fixed deadline decreases across chunks and excludes final deadline byte" do
    <<first::binary-size(5), second::binary-size(5), final::binary>> = @body
    Process.put(:review_reads, [{:more, first, 1000}, {:more, second, 1000}, {:ok, final, 1}])
    assert (request() |> run()).status == 201
    assert_received {:review_body_read, one}
    assert_received {:review_body_read, two}
    assert_received {:review_body_read, three}

    assert Enum.map([one, two, three], &Keyword.fetch!(&1, :read_timeout)) == [
             15000,
             14000,
             13000
           ]

    assert_received {:review_facade, :upload, _, _, _, @body, _}
    Process.put(:review_clock, 0)
    Process.put(:review_reads, [{:ok, @body, 15000}])
    request() |> run() |> error(400, "malformed_body")
    no_effects()
  end

  test "independent cumulative overflow rejects adapters delivering more than requested" do
    valid = @body <> String.duplicate(" ", @maximum - byte_size(@body))
    Process.put(:review_reads, [{:ok, valid, 0}])
    assert (request() |> run()).status == 201
    assert_received {:review_facade, :upload, _, _, _, ^valid, _}
    Process.put(:review_reads, [{:ok, valid <> " ", 0}])
    request() |> run() |> error(413, "body_too_large")
    no_effects()
  end

  test "independent GET body cannot hide behind absent or zero Content-Length" do
    for operation <- [:read, :audit] do
      Process.put(:review_reads, [{:ok, "x", 0}])
      conn = request(operation)
      conn = %{conn | req_headers: [{"content-length", "0"} | conn.req_headers]}
      conn |> run(operation) |> error(400, "invalid_request")
      no_effects()
    end
  end

  test "independent body and clock exceptions or throws remain generic failures" do
    for mode <- [:raise, :throw] do
      Process.put(:review_reads, mode)
      request() |> run() |> error(400, "malformed_body")
      no_effects()
      Process.put(:review_reads, :normal)
      Process.put(:review_clock, mode)
      request() |> run() |> error(400, "malformed_body")
      no_effects()
      Process.put(:review_clock, 0)
    end
  end

  test "independent all operations preserve failed facade commit exceptions and throws as503" do
    for operation <- [:upload, :read, :audit],
        result <- [
          {:error, :storage_unavailable},
          {:error, :authorization_unavailable},
          :raise,
          :throw,
          {:error, {:commit_uncertain, "REVIEW_PRIVATE"}}
        ] do
      Process.put(:review_result, result)

      code =
        if result == {:error, :authorization_unavailable},
          do: "authorization_unavailable",
          else: "storage_unavailable"

      request(operation) |> run(operation) |> error(503, code)
    end
  end

  test "independent safe response metadata is canonical across success and failure" do
    for operation <- [:upload, :read, :audit],
        result <- [:default, {:error, :storage_unavailable}] do
      if result == :default,
        do: Process.delete(:review_result),
        else: Process.put(:review_result, result)

      conn = request(operation)

      conn = %{
        conn
        | resp_headers: [
            {"cache-control", "public"},
            {"cache-control", "max-age=999"},
            {"content-type", "text/html"},
            {"content-type", "image/png"},
            {"retry-after", "999"},
            {"www-authenticate", "Basic"},
            {"x-request-id", "unsafe response id 00000"}
          ]
      }

      conn = run(conn, operation)

      assert conn.status ==
               if(result == :default and operation == :upload,
                 do: 201,
                 else: if(result == :default, do: 200, else: 503)
               )

      assert get_resp_header(conn, "cache-control") == ["no-store"]
      assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
      assert get_resp_header(conn, "www-authenticate") == []
      assert get_resp_header(conn, "retry-after") == if(result == :default, do: [], else: ["1"])
      [id] = get_resp_header(conn, "x-request-id")
      refute id =~ " "
    end
  end

  test "independent HTTP assertions never select trusted init dependencies or actor metadata" do
    for options <- [
          [operation: :upload, facade: IncompleteFacade],
          [operation: :upload, facade: Facade, clock: "header"],
          [operation: :upload, facade: Facade, clock: {String, :not_exported, []}],
          [operation: :upload, facade: Facade, repo: Facade],
          [operation: :upload, operation: :read, facade: Facade]
        ] do
      assert_raise ArgumentError, fn -> Controller.init(options) end
    end

    assert_raise ArgumentError, fn ->
      CustomerArtifactRequest.init(operation: :upload, roots: [])
    end

    conn = request()

    conn = %{
      conn
      | req_headers: [
          {"x-mixer-facade", "evil"},
          {"x-mixer-actor", "owner"},
          {"x-mixer-roots", "evil"},
          {"cf-connecting-ip", "1.2.3.4"},
          {"x-forwarded-for", "1.2.3.4"} | conn.req_headers
        ],
        remote_ip: {0, 0, 0, 0, 0, 0, 0, 1}
    }

    assert run(conn).status == 201

    assert_received {:review_facade, :upload,
                     %{organization_id: "org-a", project_id: "project-a"}, _, _, _,
                     %{source_ip: "::1", reason: "local development operation"}}
  end

  test "independent actual Router preparation must not turn encoded or normalized aliases into mutations" do
    paths = [
      String.replace(@path, "/v3/", "/%763/"),
      String.replace(@path, "org-a", "org%2Da"),
      String.replace(@path, "project-a", "project%2Da"),
      String.replace(@path, @digest, String.duplicate("%61", 64)),
      String.replace(@path, "/projects/", "//projects/")
    ]

    results =
      Enum.map(paths, fn path ->
        routed =
          request(:upload, path: path, headers: [])
          |> MixerHostedWeb.Router.call(MixerHostedWeb.Router.init([]))

        assert routed.status == 401
        conn = request(:upload, path: path)
        conn = %{conn | path_params: routed.path_params}
        {path, run(conn).status}
      end)

    IO.inspect(results, label: "independent actual-router alias observations")
    assert Enum.all?(results, fn {_path, status} -> status in [400, 404] end)
  end
end
