defmodule MixerHostedWeb.CustomerWorkspaceTransportTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.CustomerWorkspaceController, as: Controller
  alias MixerHostedWeb.Plugs.{BearerIdentity, CustomerWorkspaceRequest}

  defmodule Verifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, now) do
      send(self(), {:verified, token, now})
      Process.get(:workspace_transport_identity)
    end
  end

  defmodule Facade do
    def organizations(identity, page) do
      send(self(), {:organizations, identity, page})

      result(
        {:ok,
         %{
           organizations: [%{id: "org", display_name: nil, organization_roles: []}],
           next_cursor: nil
         }}
      )
    end

    def projects(identity, organization, page) do
      send(self(), {:projects, identity, organization, page})

      result(
        {:ok,
         %{
           projects: [
             %{
               organization_id: organization,
               id: "project",
               display_name: "Real Project",
               roles: ["billing_manager"]
             }
           ],
           next_cursor: nil
         }}
      )
    end

    defp result(default) do
      case Process.get(:workspace_transport_result, default) do
        :raise -> raise "private database credential"
        :throw -> throw("private provider response")
        other -> other
      end
    end
  end

  defmodule Adapter do
    def read_req_body(%{inner: inner, mode: mode} = state, opts) do
      send(self(), {:body_read, opts})
      Process.put(:workspace_transport_reads, Process.get(:workspace_transport_reads, 0) + 1)

      case mode do
        :raise ->
          raise "private body bytes"

        :throw ->
          throw("private body bytes")

        :error ->
          {:error, :timeout}

        :empty_more ->
          {:more, "", state}

        :deadline ->
          Process.put(:workspace_transport_milliseconds, 15_000)
          {:ok, "", state}

        :stream ->
          {:more, "x", state}

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

  defmodule FixtureController do
    def init(operation), do: operation

    def call(conn, operation) do
      Controller.call(
        conn,
        Controller.init(
          operation: operation,
          facade: Facade,
          clock: {MixerHostedWeb.CustomerWorkspaceTransportTest, :milliseconds, []}
        )
      )
    end
  end

  defmodule FixtureClock do
    def unix_seconds, do: 1_800_000_000
  end

  defmodule FixtureRouter do
    use Phoenix.Router

    pipeline :identity do
      plug(BearerIdentity, verifier: Verifier, clock: {FixtureClock, :unix_seconds, []})
    end

    scope "/v3" do
      pipe_through(:identity)
      get("/orgs", FixtureController, :organizations)
      get("/projects", FixtureController, :projects)
    end
  end

  def unix_seconds, do: 1_800_000_000
  def milliseconds, do: Process.get(:workspace_transport_milliseconds, 0)

  setup do
    Process.put(:workspace_transport_milliseconds, 0)
    Process.put(:workspace_transport_reads, 0)
    Process.put(:workspace_transport_identity, {:ok, identity()})
    :ok
  end

  defp identity(scopes \\ ["mixer.workspace.read"]) do
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

  defp request(operation \\ :organizations, opts \\ []) do
    path =
      Keyword.get(
        opts,
        :path,
        if(operation == :organizations, do: "/v3/orgs", else: "/v3/projects")
      )

    query =
      Keyword.get(opts, :query, if(operation == :projects, do: "organization_id=org", else: ""))

    conn =
      conn(
        Keyword.get(opts, :method, :get),
        path <> if(query == "", do: "", else: "?" <> query),
        Keyword.get(opts, :body, "")
      )

    {_, inner} = conn.adapter

    %{
      conn
      | req_headers: Keyword.get(opts, :headers, [{"authorization", "Bearer opaque.Token"}]),
        adapter: {Adapter, %{inner: inner, mode: Keyword.get(opts, :mode, :normal)}}
    }
  end

  defp run(conn, operation \\ :organizations) do
    conn =
      BearerIdentity.call(
        conn,
        BearerIdentity.init(verifier: Verifier, clock: {__MODULE__, :unix_seconds, []})
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
    refute_received {:organizations, _, _}
    refute_received {:projects, _, _, _}
  end

  defp cursor(operation, after_id, organization \\ nil) do
    pairs = [{"v", 1}, {"kind", Atom.to_string(operation)}]

    pairs =
      if operation == :projects, do: pairs ++ [{"organization_id", organization}], else: pairs

    Jason.encode!(%Jason.OrderedObject{values: pairs ++ [{"after", after_id}]})
    |> Base.url_encode64(padding: false)
  end

  test "missing authentication precedes parameters and body" do
    for operation <- [:organizations, :projects] do
      conn = request(operation, headers: [], body: "private") |> run(operation)
      assert_error(conn, 401, "unauthenticated")
      assert %Plug.Conn.Unfetched{} = conn.query_params
      assert %Plug.Conn.Unfetched{} = conn.body_params
      refute_received {:body_read, _}
      refute_received {:verified, _, _}
      no_facade()
    end
  end

  test "exact human scope precedes path query media and body" do
    for operation <- [:organizations, :projects],
        scopes <- [[], ["mixer.workspace.*"], ["mixer.artifact.read", "mixer.audit.read"]] do
      Process.put(:workspace_transport_identity, {:ok, identity(scopes)})

      request(operation, path: "/aliased", query: "unknown=1", body: "private")
      |> run(operation)
      |> assert_error(403, "permission_denied")

      assert_received {:verified, "opaque.Token", _}
      refute_received {:body_read, _}
      no_facade()
    end

    Process.put(:workspace_transport_identity, {:ok, %{identity() | identity_class: :service}})
    request() |> run() |> assert_error(403, "permission_denied")
    Process.put(:workspace_transport_identity, {:ok, Map.from_struct(identity())})
    request() |> run() |> assert_error(503, "identity_unavailable")
    no_facade()
  end

  test "only fixed exact paths and read methods reach a facade" do
    for {operation, path} <- [
          {:organizations, "/v3/orgs/"},
          {:organizations, "/%763/orgs"},
          {:organizations, "/v3//orgs"},
          {:projects, "/v3/orgs/org/projects"},
          {:projects, "/v3/%70rojects"}
        ] do
      request(operation, path: path) |> run(operation) |> assert_error(400, "invalid_request")
      refute_received {:body_read, _}
      no_facade()
    end

    for method <- [:post, :put, :delete, :options] do
      request(:organizations, method: method) |> run() |> assert_error(404, "not_found")
      no_facade()
    end
  end

  test "organization and project defaults pass only identity and closed page fields" do
    assert (request() |> run()).status == 200
    assert_received {:organizations, %VerifiedIdentity{}, %{limit: 50, cursor: nil}}
    assert (request(:projects) |> run(:projects)).status == 200
    assert_received {:projects, %VerifiedIdentity{}, "org", %{limit: 50, cursor: nil}}
    assert_received {:body_read, opts}
    assert opts == [length: 1, read_length: 65_536, read_timeout: 15_000]
  end

  test "full Scope identifiers survive one query decode including dot segments and literal percent" do
    for organization <- [
          ".",
          "..",
          "org/project",
          "org:one",
          "équipe",
          "a+b",
          "%",
          "%2F",
          "\"quoted\"",
          String.duplicate("é", 64)
        ] do
      query = "organization_id=" <> URI.encode_www_form(organization)
      conn = request(:projects, query: query) |> run(:projects)
      assert conn.status == 200
      assert_received {:projects, _, ^organization, %{limit: 50, cursor: nil}}
      assert %Plug.Conn.Unfetched{} = conn.query_params
      assert %Plug.Conn.Unfetched{} = conn.body_params
    end
  end

  test "malformed percent escapes reject even when undecoded text is a printable tenant ID" do
    for raw <- [
          "%",
          "%2",
          "%GG",
          "org%2G",
          "%ff",
          "%c3",
          "%00",
          "%1f",
          "%7f",
          "%C2%80",
          "*",
          String.duplicate("a", 129)
        ] do
      request(:projects, query: "organization_id=" <> raw)
      |> run(:projects)
      |> assert_error(400, "invalid_request")

      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "query fields are unique closed and nonempty after exactly one decode" do
    for query <- [
          "organization_id=org&organization_id=org",
          "%6frganization_id=org&organization_id=org",
          "organization_id=org&%6cimit=1&limit=2",
          "organization_id=org&unknown=1",
          "organization_id=org&limit=1&cursor=x&extra=1",
          "organization_id=",
          "organization_id",
          "organization_id[]=org",
          "organization_id=org&",
          "&organization_id=org",
          "organization_id=org&&limit=1",
          "=org",
          "organization_id=org&%GG=1",
          "organization_id=org&cursor=",
          "organization_id=org&cursor",
          "organization_id=org&repo=Chosen",
          "organization_id=org&actor=owner",
          "organization_id=org&principal=person",
          "organization_id=org&clock=0",
          "organization_id=org&limit=%2531",
          String.duplicate("x", 8193)
        ] do
      request(:projects, query: query) |> run(:projects) |> assert_error(400, "invalid_request")
      refute_received {:body_read, _}
      no_facade()
    end

    request(:projects, query: "") |> run(:projects) |> assert_error(400, "invalid_request")

    request(:organizations, query: "organization_id=org")
    |> run()
    |> assert_error(400, "invalid_request")

    no_facade()
  end

  test "limit accepts only the new bounded canonical decimal form" do
    for raw <- [
          "0",
          "101",
          "01",
          "0001",
          "",
          "-1",
          "+1",
          "1.0",
          "1e2",
          "%201",
          "1%20",
          "%",
          "%31%G0"
        ] do
      request(:organizations, query: "limit=" <> raw)
      |> run()
      |> assert_error(400, "invalid_request")

      refute_received {:body_read, _}
      no_facade()
    end

    for {raw, expected} <- [{"1", 1}, {"100", 100}, {"%31", 1}] do
      assert (request(:organizations, query: "limit=" <> raw) |> run()).status == 200
      assert_received {:organizations, _, %{limit: ^expected, cursor: nil}}
    end
  end

  test "canonical cursors bind version collection and exact organization" do
    for {operation, organization} <- [{:organizations, nil}, {:projects, "org"}] do
      value = cursor(operation, "prior/id", organization)

      query =
        "cursor=" <> value <> if(operation == :projects, do: "&organization_id=org", else: "")

      assert (request(operation, query: query) |> run(operation)).status == 200

      if operation == :organizations,
        do: assert_received({:organizations, _, %{limit: 50, cursor: ^value}}),
        else: assert_received({:projects, _, "org", %{limit: 50, cursor: ^value}})
    end
  end

  test "cursor malformed noncanonical duplicate-key or wrong-tenant forms reject before body" do
    documents = [
      "{}",
      "[]",
      ~s({"v":1,"kind":"projects","organization_id":"org","after":"a","extra":1}),
      ~s({"v":1,"kind":"projects","organization_id":"other","after":"a"}),
      ~s({"v":2,"kind":"projects","organization_id":"org","after":"a"}),
      ~s({"v":1.0,"kind":"projects","organization_id":"org","after":"a"}),
      ~s({"kind":"projects","v":1,"organization_id":"org","after":"a"}),
      ~s({ "v":1,"kind":"projects","organization_id":"org","after":"a"}),
      ~s({"v":1,"kind":"projects","organization_id":"org","after":"a","after":"b"}),
      ~S({"v":1,"kind":"projects","organization_id":"org","after":"a","af\u0074er":"b"}),
      ~s({"v":1,"kind":"organizations","after":"a"}),
      String.duplicate(" ", 1025)
    ]

    values =
      Enum.map(documents, &Base.url_encode64(&1, padding: false)) ++
        ["a=", "a+", "a/", "a", String.duplicate("a", 1401)]

    for value <- values do
      request(:projects, query: "organization_id=org&cursor=" <> URI.encode_www_form(value))
      |> run(:projects)
      |> assert_error(400, "invalid_request")

      refute_received {:body_read, _}
      no_facade()
    end
  end

  test "media is absent or one exact JSON value and encodings are always denied" do
    base = [{"authorization", "Bearer opaque.Token"}]

    for values <- [
          ["text/plain"],
          ["application/json; charset=utf-8"],
          ["Application/JSON"],
          ["application/json", "application/json"],
          ["application/json,application/json"]
        ] do
      conn =
        request(:organizations, headers: base ++ Enum.map(values, &{"content-type", &1})) |> run()

      assert conn.status == 400
      refute_received {:body_read, _}
      no_facade()
    end

    for values <- [["gzip"], ["identity"], [""], ["gzip", "gzip"]] do
      request(:organizations, headers: base ++ Enum.map(values, &{"content-encoding", &1}))
      |> run()
      |> assert_error(415, "unsupported_content_encoding")

      refute_received {:body_read, _}
      no_facade()
    end

    assert (request(:organizations, headers: base ++ [{"content-type", "application/json"}])
            |> run()).status == 200
  end

  test "nonempty and streaming bodies reject irrespective of declared length" do
    for {body, mode} <- [{"x", :normal}, {"", :stream}] do
      request(:organizations,
        body: body,
        mode: mode,
        headers: [{"authorization", "Bearer opaque.Token"}, {"content-length", "0"}]
      )
      |> run()
      |> assert_error(400, "invalid_request")

      assert_received {:body_read, _}
      no_facade()
    end
  end

  test "body failures deadline and empty-more loops have finite bounded failure" do
    for mode <- [:raise, :throw, :error, :deadline, :empty_more] do
      Process.put(:workspace_transport_milliseconds, 0)
      Process.put(:workspace_transport_reads, 0)
      request(:organizations, mode: mode) |> run() |> assert_error(400, "malformed_body")
      assert Process.get(:workspace_transport_reads) <= 128
      if mode == :empty_more, do: assert(Process.get(:workspace_transport_reads) == 128)
      no_facade()
    end
  end

  test "success exposes only closed current workspace labels roles and opaque cursor" do
    value = cursor(:organizations, "org")

    Process.put(
      :workspace_transport_result,
      {:ok,
       %{
         organizations: [
           %{
             id: "org",
             display_name: "A * Team",
             organization_roles: ["administrator", "billing_manager"]
           }
         ],
         next_cursor: value
       }}
    )

    conn = request() |> run()
    assert conn.status == 200

    assert Jason.decode!(conn.resp_body) == %{
             "organizations" => [
               %{
                 "id" => "org",
                 "display_name" => "A * Team",
                 "organization_roles" => ["administrator", "billing_manager"]
               }
             ],
             "next_cursor" => value
           }

    assert get_resp_header(conn, "cache-control") == ["no-store"]
  end

  test "empty pages and all six exact roles remain representable" do
    for operation <- [:organizations, :projects] do
      Process.put(:workspace_transport_result, {:ok, %{operation => [], :next_cursor => nil}})
      assert (request(operation) |> run(operation)).status == 200
    end

    for role <- ~w(owner administrator developer release_manager billing_manager viewer) do
      Process.put(
        :workspace_transport_result,
        {:ok,
         %{
           projects: [%{organization_id: "org", id: "project", display_name: nil, roles: [role]}],
           next_cursor: nil
         }}
      )

      assert (request(:projects) |> run(:projects)).status == 200
    end
  end

  test "malformed facade output never leaks names internal fields roles or foreign tenant data" do
    good = %{organization_id: "org", id: "project", display_name: nil, roles: ["viewer"]}

    rows = [
      Map.put(good, :organization_id, "foreign"),
      Map.put(good, :display_name, ""),
      Map.put(good, :display_name, "private\nname"),
      Map.put(good, :display_name, String.duplicate("a", 257)),
      Map.put(good, :display_name, <<255>>),
      Map.put(good, :roles, []),
      Map.put(good, :roles, ["owner", "owner"]),
      Map.put(good, :roles, ["viewer", "owner"]),
      Map.put(good, :roles, ["superuser"]),
      Map.put(good, :private, "private credential")
    ]

    results =
      Enum.map(rows, &{:ok, %{projects: [&1], next_cursor: nil}}) ++
        [
          {:ok, %{projects: [good, good], next_cursor: nil}},
          {:ok, %{projects: [good], next_cursor: "private"}},
          {:ok, %{projects: [], next_cursor: cursor(:projects, "project", "org")}},
          {:ok, %{projects: [good], next_cursor: cursor(:projects, "other", "org")}},
          {:ok, %{projects: [good], next_cursor: nil, private: "private"}},
          {:ok, %{projects: [good, %{good | id: "second"}], next_cursor: nil}}
        ]

    for result <- results do
      Process.put(:workspace_transport_result, result)

      request(:projects, query: "organization_id=org&limit=1")
      |> run(:projects)
      |> assert_error(503, "authorization_unavailable")

      assert_received {:projects, _, "org", _}
    end
  end

  test "facade bounded errors and unexpected failures preserve generic response policy" do
    for {reason, status, code} <- [
          {:unauthenticated, 401, "unauthenticated"},
          {:permission_denied, 403, "permission_denied"},
          {:not_found, 404, "not_found"},
          {:invalid_request, 400, "invalid_request"},
          {:authorization_unavailable, 503, "authorization_unavailable"}
        ] do
      Process.put(:workspace_transport_result, {:error, reason})
      request() |> run() |> assert_error(status, code)
    end

    for result <- [:raise, :throw, :malformed, {:error, "private"}] do
      Process.put(:workspace_transport_result, result)
      request() |> run() |> assert_error(503, "authorization_unavailable")
    end
  end

  test "duplicate stale response headers are sanitized on success and failure" do
    conn = request()

    conn = %{
      conn
      | resp_headers: [
          {"cache-control", "public"},
          {"cache-control", "max-age=1"},
          {"www-authenticate", "stale"},
          {"retry-after", "99"},
          {"content-type", "private"},
          {"x-request-id", "bad"},
          {"x-request-id", "duplicate"}
        ]
    }

    conn = run(conn)
    assert conn.status == 200
    assert get_resp_header(conn, "cache-control") == ["no-store"]
    assert get_resp_header(conn, "www-authenticate") == []
    assert get_resp_header(conn, "retry-after") == []
    assert [_] = get_resp_header(conn, "x-request-id")
  end

  test "trusted initialization rejects request-selectable or malformed dependencies" do
    for opts <- [
          [operation: :organizations, repo: Chosen],
          [operation: :organizations, operation: :projects],
          [operation: :other],
          [operation: :organizations, clock: :invalid]
        ] do
      assert_raise ArgumentError, fn -> CustomerWorkspaceRequest.init(opts) end
    end

    for opts <- [
          [operation: :organizations, facade: Facade, repo: Chosen],
          [operation: :organizations, facade: MissingFacade],
          [operation: :organizations, facade: Facade, facade: Facade],
          [operation: :organizations, facade: Facade, clock: :invalid]
        ] do
      assert_raise ArgumentError, fn -> Controller.init(opts) end
    end
  end

  test "HEAD uses the same admission and facade but this adapter is not a socket body-suppression receipt" do
    conn = request(:projects, method: :head) |> run(:projects)
    assert conn.status == 200
    assert conn.resp_body == ""
    assert_received {:projects, _, "org", %{limit: 50, cursor: nil}}
    assert_received {:body_read, _}
    Process.put(:workspace_transport_identity, {:ok, identity([])})

    denied = request(:projects, method: :head, body: "private") |> run(:projects)
    assert denied.status == 403 and denied.halted
    assert denied.resp_body == ""
    assert get_resp_header(denied, "cache-control") == ["no-store"]
    assert get_resp_header(denied, "content-type") == ["application/json; charset=utf-8"]
    refute_received {:body_read, _}
    no_facade()
  end

  test "actual Phoenix fixture route matching precedes request admission" do
    for operation <- [:organizations, :projects] do
      response = request(operation) |> FixtureRouter.call(FixtureRouter.init([]))
      assert response.status == 200
    end
  end

  test "production router's two directory paths reject missing bearer before body or configured facade" do
    for operation <- [:organizations, :projects] do
      response =
        request(operation, headers: [], body: "private")
        |> MixerHostedWeb.Router.call(MixerHostedWeb.Router.init([]))

      assert_error(response, 401, "unauthenticated")
      refute_received {:body_read, _}
      no_facade()
    end
  end
end
