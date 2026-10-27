defmodule MixerHostedWeb.BrowserWorkspaceDispatcherCaptureAdapterTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.BrowserWorkspaceDispatcher.CaptureAdapter
  alias MixerHostedWeb.CustomerWorkspaceController, as: Controller

  # Explicitly synthetic trusted facade fixture using the existing controller's
  # trusted test seam. These are capture/controller receipts, never dispatcher,
  # configured verifier, ordinary Repo, database or session-success receipts.
  defmodule SyntheticTrustedFacade do
    def organizations(_identity, _page), do: Process.get(:synthetic_capture_result)
    def projects(_identity, _organization, _page), do: Process.get(:synthetic_capture_result)
  end

  defp synthetic_identity do
    %VerifiedIdentity{
      profile_id: "synthetic-profile", profile_version: 1,
      issuer: "https://synthetic.invalid", subject: "synthetic-subject",
      client_id: "synthetic-client", credential_ref: "synthetic-credential",
      issued_at: 1, expires_at: 2, identity_class: :human,
      scopes: ["mixer.workspace.read"]
    }
  end

  defp controller(result, operation \\ :organizations) do
    Process.put(:synthetic_capture_result, result)

    conn = %Plug.Conn{
      adapter: CaptureAdapter.new(), owner: nil,
      method: "GET", request_path: if(operation == :organizations, do: "/v3/orgs", else: "/v3/projects"),
      query_string: if(operation == :organizations, do: "limit=100", else: "organization_id=org&limit=100"),
      assigns: %{verified_identity: synthetic_identity()},
      resp_headers: [{"x-request-id", String.duplicate("a", 32)}]
    }

    Controller.call(conn, Controller.init(operation: operation, facade: SyntheticTrustedFacade))
  after
    Process.delete(:synthetic_capture_result)
  end

  test "initial state, empty read and one captured iodata response contain no transport" do
    assert {CaptureAdapter, %{sends: 0} = state} = CaptureAdapter.new()
    assert CaptureAdapter.read_req_body(state, []) == {:ok, "", state}
    headers = [{"content-type", "application/json; charset=utf-8"}]

    assert {:ok, "{}", captured} = CaptureAdapter.send_resp(state, 200, headers, ["{", ?}])
    assert captured == %{sends: 1, status: 200, headers: headers, body: "{}"}
    assert CaptureAdapter.read_req_body(captured, length: 1) == {:ok, "", captured}
    assert CaptureAdapter.get_peer_data(state) == %{address: {0, 0, 0, 0}, port: 0, ssl_cert: nil}
    assert CaptureAdapter.get_sock_data(state) == %{address: {0, 0, 0, 0}, port: 0}
    assert CaptureAdapter.get_ssl_data(state) == nil
    assert CaptureAdapter.get_http_protocol(state) == :local_capture
  end

  test "binary and nested iodata body cap admits exactly its boundary" do
    {_, state} = CaptureAdapter.new()
    body = String.duplicate("x", 262_144)
    assert {:ok, ^body, _} = CaptureAdapter.send_resp(state, 200, [], body)
    assert {:ok, ^body, _} = CaptureAdapter.send_resp(state, 200, [], [binary_part(body, 0, 131_072), [binary_part(body, 131_072, 131_072)]])

    for invalid <- [[body, "x"], [256], ["valid" | :invalid], :not_iodata] do
      assert_raise ArgumentError, "local response unavailable", fn ->
        CaptureAdapter.send_resp(state, 200, [], invalid)
      end
    end
  end

  test "second send and every unsupported response operation fail with a fixed reason" do
    {_, state} = CaptureAdapter.new()
    {:ok, _, captured} = CaptureAdapter.send_resp(state, 200, [], "{}")

    for callback <- [
          fn -> CaptureAdapter.send_resp(captured, 200, [], "private-marker") end,
          fn -> CaptureAdapter.send_file(state, 200, [], "/private-missing-file", 0, :all) end,
          fn -> CaptureAdapter.send_chunked(state, 200, []) end,
          fn -> CaptureAdapter.chunk(state, "private-marker") end,
          fn -> CaptureAdapter.upgrade(state, :private_protocol, :private_options) end,
          fn -> CaptureAdapter.inform(state, 103, []) end,
          fn -> CaptureAdapter.push(state, "/private-path", []) end
        ] do
      assert_raise ArgumentError, "local response unavailable", callback
    end
  end

  test "ordinary Plug send with owner nil preserves preexisting caller mailbox" do
    send(self(), {:plug_conn, :sent})
    send(self(), {:synthetic_capture_mailbox, :preserved})
    {:messages, before} = Process.info(self(), :messages)
    conn = Plug.Conn.send_resp(%Plug.Conn{adapter: CaptureAdapter.new(), owner: nil}, 200, "{}")
    assert conn.state == :sent
    assert Process.info(self(), :messages) == {:messages, before}
    assert_receive {:plug_conn, :sent}
    assert_receive {:synthetic_capture_mailbox, :preserved}
    refute_receive {:plug_conn, :sent}, 0
  end

  test "canonical controller accepts synthetic 65 and 100 row pages without a second decoder" do
    for count <- [65, 100] do
      rows = for n <- 1..count, do: %{id: "org-" <> String.pad_leading(Integer.to_string(n), 3, "0"), display_name: nil, organization_roles: []}
      page = %{organizations: rows, next_cursor: nil}
      conn = controller({:ok, page})
      assert conn.status == 200 and conn.state == :sent
      assert conn.resp_body == Jason.encode!(page)
      assert {CaptureAdapter, %{sends: 1, body: body}} = conn.adapter
      assert body == conn.resp_body
      assert length(Jason.decode!(body)["organizations"]) == count
      assert MixerHosted.Identity.BoundedJSON.object(body, 262_144) == :error
    end
  end

  test "canonical controller accepts a synthetic project page and rejects invalid rows" do
    row = %{organization_id: "org", id: "project", display_name: "Project", roles: ["viewer"]}
    page = %{projects: [row], next_cursor: nil}
    conn = controller({:ok, page}, :projects)
    assert conn.status == 200
    assert conn.resp_body == Jason.encode!(page)

    for invalid <- [Map.put(row, :organization_id, "other"), Map.put(row, :roles, []), Map.put(row, :secret, "private-marker")] do
      conn = controller({:ok, %{projects: [invalid], next_cursor: nil}}, :projects)
      assert conn.status == 503 and conn.state == :sent
      refute conn.resp_body =~ "private-marker"
      assert Plug.Conn.get_resp_header(conn, "retry-after") == ["1"]
    end
  end

  test "canonical controller denials keep fixed redacted bodies and headers" do
    for {reason, status} <- [{:unauthenticated, 401}, {:permission_denied, 403}, {:not_found, 404}, {:invalid_request, 400}, {:authorization_unavailable, 503}] do
      conn = controller({:error, reason})
      assert conn.status == status and conn.state == :sent
      assert Plug.Conn.get_resp_header(conn, "cache-control") == ["no-store"]
      assert Plug.Conn.get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
      assert Plug.Conn.get_resp_header(conn, "x-request-id") == [String.duplicate("a", 32)]
      assert byte_size(conn.resp_body) < 512
    end
  end
end
