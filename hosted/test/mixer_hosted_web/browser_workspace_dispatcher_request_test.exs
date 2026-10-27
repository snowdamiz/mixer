defmodule MixerHostedWeb.BrowserWorkspaceDispatcherRequestTest do
  use ExUnit.Case, async: true
  alias MixerHosted.CustomerWorkspace.Input
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.BrowserWorkspaceDispatcher.{CaptureAdapter, Request}
  alias MixerHostedWeb.Plugs.CustomerWorkspaceRequest

  defmodule Page do
    defstruct limit: 50, cursor: nil
  end

  # Deliberately synthetic trusted transport fixture; no token was verified and
  # no identity owner or ordinary Repo authorization is exercised by these tests.
  defp synthetic_identity do
    %VerifiedIdentity{
      profile_id: "synthetic-profile",
      profile_version: 1,
      issuer: "https://synthetic.invalid",
      subject: "synthetic-subject",
      client_id: "synthetic-client",
      credential_ref: "synthetic-credential",
      issued_at: 1,
      expires_at: 2,
      identity_class: :human,
      scopes: ["mixer.workspace.read"]
    }
  end

  defp admit(request) do
    conn = %Plug.Conn{
      adapter: CaptureAdapter.new(),
      request_path: request.path,
      method: "GET",
      query_string: request.query,
      assigns: %{verified_identity: synthetic_identity()},
      resp_headers: [{"x-request-id", String.duplicate("a", 32)}]
    }

    CustomerWorkspaceRequest.call(conn, CustomerWorkspaceRequest.init(request.operation))
  end

  test "fixed organization path and decimal limit include both bounds and large page sizes" do
    for limit <- [1, 65, 100] do
      assert {:ok, %{operation: :organizations, path: "/v3/orgs", query: query} = request} =
               Request.new({:organizations, %{limit: limit, cursor: nil}})

      assert query == "limit=#{limit}"
      conn = admit(request)
      refute conn.halted

      assert conn.assigns.customer_workspace_request == %{
               organization_id: nil,
               page: %{limit: limit, cursor: nil}
             }
    end
  end

  test "exact hostile IDs are encoded once and roundtrip through canonical request admission" do
    for organization <- [" ", " org ", "a+b&c=d%2F?#/", "租户 café", String.duplicate("z", 128)] do
      cursor = Input.cursor("projects", organization, " after+&%/租 ")

      assert {:ok, request} =
               Request.new({:projects, organization, %{limit: 100, cursor: cursor}})

      assert request == %{
               operation: :projects,
               path: "/v3/projects",
               query:
                 "organization_id=" <>
                   URI.encode_www_form(organization) <>
                   "&limit=100&cursor=" <> URI.encode_www_form(cursor)
             }

      assert byte_size(request.query) <= 8_192
      conn = admit(request)
      refute conn.halted

      assert conn.assigns.customer_workspace_request == %{
               organization_id: organization,
               page: %{limit: 100, cursor: cursor}
             }
    end
  end

  test "canonical organization cursor is serialized unchanged and decoded again by transport" do
    cursor = Input.cursor("organizations", nil, "org+ &%/租")
    assert {:ok, request} = Request.new({:organizations, %{limit: 1, cursor: cursor}})
    assert request.query == "limit=1&cursor=" <> URI.encode_www_form(cursor)
    conn = admit(request)
    refute conn.halted
    assert conn.assigns.customer_workspace_request.page.cursor == cursor

    assert CustomerWorkspaceRequest.decode_cursor(cursor, :organizations, nil) ==
             {:ok, "org+ &%/租"}
  end

  test "request and page shapes are closed" do
    page = %{limit: 50, cursor: nil}

    for value <- [
          nil,
          :organizations,
          [:organizations, page],
          {:unknown, page},
          {:organizations, page, %{}},
          {:projects, page},
          {:organizations, %{limit: 50}},
          {:organizations, %{cursor: nil}},
          {:organizations, %{"limit" => 50, "cursor" => nil}},
          {:organizations, Map.put(page, :after, "org")},
          {:organizations, %Page{}},
          {:organizations, %{limit: 0, cursor: nil}},
          {:organizations, %{limit: 101, cursor: nil}},
          {:organizations, %{limit: 1.0, cursor: nil}},
          {:organizations, %{limit: "1", cursor: nil}},
          {:organizations, %{limit: 50, cursor: ""}},
          {:organizations, %{limit: 50, cursor: "not-canonical"}},
          {:organizations, %{limit: 50, cursor: String.duplicate("x", 1401)}}
        ] do
      assert Request.new(value) == {:error, :invalid_request}
    end
  end

  test "organization identifiers reject invalid bytes without normalization" do
    for organization <- [
          nil,
          :org,
          "",
          "*",
          "line\nfeed",
          <<0>>,
          <<255>>,
          String.duplicate("x", 129)
        ] do
      assert Request.new({:projects, organization, %{limit: 50, cursor: nil}}) ==
               {:error, :invalid_request}
    end
  end

  test "cursor cannot cross an operation or exact organization" do
    organizations = Input.cursor("organizations", nil, "after")
    projects = Input.cursor("projects", "org", "after")

    for value <- [
          {:projects, "org", %{limit: 50, cursor: organizations}},
          {:organizations, %{limit: 50, cursor: projects}},
          {:projects, "org ", %{limit: 50, cursor: projects}},
          {:projects, "other", %{limit: 50, cursor: projects}}
        ] do
      assert Request.new(value) == {:error, :invalid_request}
    end
  end
end
