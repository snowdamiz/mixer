defmodule MixerFixedWorkspaceDispatcherIndependentTest do
  use ExUnit.Case, async: false
  alias MixerHosted.CustomerWorkspace.Input
  alias MixerHosted.Identity.{Admission, KeyOwner, VerifiedIdentity}
  alias MixerHosted.Repo
  alias MixerHostedWeb.BrowserWorkspaceDispatcher, as: Dispatcher
  alias MixerHostedWeb.BrowserWorkspaceDispatcher.{CaptureAdapter, Request}
  alias MixerHostedWeb.CustomerWorkspaceController
  alias MixerHostedWeb.Plugs.CustomerWorkspaceRequest

  @id "00112233445566778899aabbccddeeff"
  @metadata %{request_id: @id}
  @organizations {:organizations, %{limit: 100, cursor: nil}}

  # Trusted synthetic transport/facade fixture only. No token is verified and no
  # default dispatcher success, current identity or Repo authority is qualified.
  defmodule SyntheticTrustedFacade do
    def organizations(_, _), do: result()
    def projects(_, _, _), do: result()

    defp result do
      case Process.get({__MODULE__, :result}) do
        {:raise, marker} -> raise ArgumentError, marker
        {:throw, marker} -> throw(marker)
        result -> result
      end
    end
  end

  setup do
    assert Process.whereis(KeyOwner) == nil
    assert Process.whereis(Repo) == nil
    assert :persistent_term.get({Admission, KeyOwner}, :absent) == :absent
    assert Repo.get_dynamic_repo() === Repo
    :ok
  end

  defp synthetic_identity do
    %VerifiedIdentity{
      profile_id: "synthetic-only", profile_version: 1,
      issuer: "https://synthetic.invalid", subject: "synthetic-only",
      client_id: "synthetic-only", credential_ref: "synthetic-only",
      issued_at: 1, expires_at: 2, identity_class: :human,
      scopes: ["mixer.workspace.read"]
    }
  end

  defp synthetic_conn(request) do
    %Plug.Conn{
      adapter: CaptureAdapter.new(), owner: nil, method: "GET",
      request_path: request.path, query_string: request.query,
      assigns: %{verified_identity: synthetic_identity()},
      resp_headers: [{"x-request-id", @id}]
    }
  end

  defp synthetic_controller(request, result) do
    Process.put({SyntheticTrustedFacade, :result}, result)
    try do
      CustomerWorkspaceController.call(
        synthetic_conn(request),
        CustomerWorkspaceController.init(operation: request.operation, facade: SyntheticTrustedFacade)
      )
    after
      Process.delete({SyntheticTrustedFacade, :result})
    end
  end

  test "I01 distinct normalization and percent spellings retain exact tenant bytes" do
    ids = ["é", "e\u0301", "%2F", "%2f", "%252F", "+", " ", "a=b&limit=1#?", String.duplicate("é", 64)]
    for organization <- ids do
      cursor = Input.cursor("projects", organization, "after%2F+&=")
      assert {:ok, request} = Request.new({:projects, organization, %{limit: 100, cursor: cursor}})
      assert request.path == "/v3/projects"
      assert length(:binary.split(request.query, "&", [:global])) == 3
      conn = CustomerWorkspaceRequest.call(synthetic_conn(request), CustomerWorkspaceRequest.init(:projects))
      refute conn.halted
      assert conn.assigns.customer_workspace_request == %{organization_id: organization, page: %{limit: 100, cursor: cursor}}
      assert {:ok, ^request} = Request.new({:projects, organization, %{limit: 100, cursor: cursor}})
    end

    cursor = Input.cursor("projects", "é", "after")
    assert Request.new({:projects, "e\u0301", %{limit: 100, cursor: cursor}}) == {:error, :invalid_request}
  end

  test "I02 semantically similar cursor JSON is rejected unless exactly canonical" do
    canonical = Input.cursor("organizations", nil, "after")
    assert {:ok, _} = Request.new({:organizations, %{limit: 1, cursor: canonical}})
    raw_variants = [
      ~s({"kind":"organizations","v":1,"after":"after"}),
      ~s({"v":1, "kind":"organizations","after":"after"}),
      ~s({"v":1.0,"kind":"organizations","after":"after"}),
      ~s({"v":1,"kind":"organizations","after":"after","extra":false}),
      ~s({"v":1,"kind":"organizations","after":"after","after":"after"}),
      ~s({"v":1,"kind":"organizations","after":"\\u0061fter"})
    ]
    variants = Enum.map(raw_variants, &Base.url_encode64(&1, padding: false)) ++ [canonical <> "=", canonical <> " "]
    for cursor <- variants do
      assert Input.page(%{limit: 1, cursor: cursor}, "organizations", nil) == {:error, :invalid_request}
      assert Request.new({:organizations, %{limit: 1, cursor: cursor}}) == {:error, :invalid_request}
    end
  end

  test "I03 internal adapter state must contain exactly the initial zero count" do
    malformed = [%{}, %{sends: 0, body: "synthetic-secret"}, %{sends: 0.0}, %{sends: "0"}, %{sends: -1}, %{sends: 2}, [sends: 0], nil]
    for state <- malformed do
      assert_raise ArgumentError, "local response unavailable", fn -> CaptureAdapter.send_resp(state, 200, [], "{}") end
    end
    {CaptureAdapter, state} = CaptureAdapter.new()
    assert {:ok, "", ^state} = CaptureAdapter.read_req_body(state, length: 0)
    assert {:ok, "{}", %{sends: 1}} = CaptureAdapter.send_resp(state, 200, [], "{}")
  end

  test "I04 nested and improper binary iodata has an exact opaque byte boundary" do
    {CaptureAdapter, state} = CaptureAdapter.new()
    opaque = <<255>> <> :binary.copy(<<0>>, 262_143)
    nested = Enum.reduce(1..32, opaque, fn _, value -> [value] end)
    assert {:ok, ^opaque, captured} = CaptureAdapter.send_resp(state, 200, [], [nested | <<>>])
    assert captured.body === opaque
    for body <- [[-1], [1.0], [%{}], [<<1::size(1)>>], [opaque | <<0>>]] do
      assert_raise ArgumentError, "local response unavailable", fn -> CaptureAdapter.send_resp(state, 200, [], body) end
    end
    assert_raise ArgumentError, "local response unavailable", fn -> CaptureAdapter.send_resp(captured, 200, [], "synthetic-secret") end
  end

  test "I05 canonical bearer padding and leading spaces remain canonical plug decisions" do
    for token <- ["A", "A=", "A==", "  A", "A+/._~-"] do
      assert {:ok, %{status: 503, headers: headers}} = Dispatcher.dispatch(token, @organizations, @metadata)
      assert headers == [{"cache-control", "no-store"}, {"content-type", "application/json; charset=utf-8"}, {"x-request-id", @id}, {"retry-after", "1"}]
    end
    for token <- ["=", "==", "A=B", "A= B", "A\t", "A\r\n", <<0>>] do
      assert {:ok, %{status: 400, body: body}} = Dispatcher.dispatch(token, @organizations, @metadata)
      assert Jason.decode!(body) == %{"error" => %{"code" => "invalid_request", "message" => "Invalid authentication request."}, "request_id" => @id}
    end
  end

  test "I06 failure precedence preserves caller dictionary and mailbox across sequences" do
    previous = Repo.put_dynamic_repo(:independent_synthetic_wrong_repo)
    Process.put(:independent_private_marker, {self(), "synthetic-secret"})
    send(self(), {:plug_conn, :sent})
    send(self(), {:independent_private_marker, make_ref()})
    {:messages, before_mailbox} = Process.info(self(), :messages)
    before_marker = Process.get(:independent_private_marker)
    try do
      for _ <- 1..3 do
        assert Dispatcher.dispatch("A", @organizations, %{request_id: @id, repo: Repo}) == {:error, :invalid_request}
        assert Dispatcher.dispatch("A", {:organizations, %{limit: 100, cursor: nil, after: "synthetic-secret"}}, @metadata) == {:error, :invalid_request}
        assert Dispatcher.dispatch("A", @organizations, @metadata) == {:error, :authorization_unavailable}
        assert Repo.get_dynamic_repo() === :independent_synthetic_wrong_repo
        assert Process.get(:independent_private_marker) === before_marker
        assert Process.info(self(), :messages) === {:messages, before_mailbox}
      end
    after
      Repo.put_dynamic_repo(previous)
      Process.delete(:independent_private_marker)
    end
  end

  test "I07 synthetic trusted facade errors and thrown exceptions have fixed redacted representation" do
    assert {:ok, request} = Request.new(@organizations)
    expected = %{"error" => %{"code" => "authorization_unavailable", "message" => "Authorization unavailable. Retry shortly."}, "request_id" => @id}
    for result <- [{:raise, "synthetic-private-exception"}, {:throw, {:synthetic, "synthetic-private-throw"}}, {:error, {:synthetic, "synthetic-private-reason"}}, {:synthetic, "synthetic-private-result"}] do
      conn = synthetic_controller(request, result)
      assert conn.status == 503 and conn.state == :sent
      assert Jason.decode!(conn.resp_body) == expected
      assert Plug.Conn.get_resp_header(conn, "retry-after") == ["1"]
      refute conn.resp_body =~ "synthetic-private"
    end
  end

  test "I08 synthetic trusted facade project page supports 100 Unicode rows and a bound canonical cursor" do
    organization = "tenant+%2Fé"
    rows = for n <- 1..100 do
      %{organization_id: organization, id: String.pad_leading(Integer.to_string(n), 3, "0") <> String.duplicate("é", 62), display_name: String.duplicate("é", 128), roles: ["viewer"]}
    end
    cursor = Input.cursor("projects", organization, List.last(rows).id)
    page = %{projects: rows, next_cursor: cursor}
    assert {:ok, request} = Request.new({:projects, organization, %{limit: 100, cursor: nil}})
    conn = synthetic_controller(request, {:ok, page})
    assert conn.status == 200 and conn.state == :sent
    assert conn.resp_body === Jason.encode!(page)
    assert {CaptureAdapter, %{sends: 1, body: body}} = conn.adapter
    assert body === conn.resp_body
    assert length(Jason.decode!(body)["projects"]) == 100
    assert CustomerWorkspaceRequest.decode_cursor(cursor, :projects, organization) == {:ok, List.last(rows).id}
    assert byte_size(body) <= 262_144
  end
end
