defmodule MixerHostedWeb.BrowserWorkspaceDispatcherTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Identity.{Admission, KeyOwner}
  alias MixerHosted.Repo
  alias MixerHostedWeb.BrowserWorkspaceDispatcher, as: Dispatcher

  @request {:organizations, %{limit: 50, cursor: nil}}
  @id "0123456789abcdef0123456789abcdef"
  @metadata %{request_id: @id}

  defmodule Metadata do
    defstruct request_id: "0123456789abcdef0123456789abcdef"
  end

  setup do
    # Refuse a configured owner or live admission table. An earlier synchronous
    # test may leave a dead ETS reference after its owning process exits.
    assert Process.whereis(KeyOwner) == nil

    case :persistent_term.get({Admission, KeyOwner}, :absent) do
      :absent ->
        :ok

      table when is_reference(table) ->
        assert :ets.info(table) == :undefined

      _ ->
        flunk("identity admission must be absent or a dead ETS reference")
    end

    assert Admission.acquire(KeyOwner, :configured) == {:error, :identity_unavailable}
    assert Repo.get_dynamic_repo() === Repo
    :ok
  end

  test "public API has exactly three mandatory arguments and no injection option" do
    assert Code.ensure_loaded?(Dispatcher)
    assert function_exported?(Dispatcher, :dispatch, 3)
    refute function_exported?(Dispatcher, :dispatch, 2)
    refute function_exported?(Dispatcher, :dispatch, 4)

    assert Dispatcher.dispatch(
             "opaque.Token",
             @request,
             Map.put(@metadata, :verifier, __MODULE__)
           ) == {:error, :invalid_request}

    assert Dispatcher.dispatch(
             "opaque.Token",
             {:organizations, %{limit: 50, cursor: nil, repo: Repo}},
             @metadata
           ) == {:error, :invalid_request}
  end

  test "closed token, request and metadata shapes fail locally even with a wrong Repo" do
    previous = Repo.put_dynamic_repo(:synthetic_wrong_repo)

    try do
      for token <- [nil, :token, [], %{}, "", String.duplicate("x", 4090)] do
        assert Dispatcher.dispatch(token, @request, @metadata) == {:error, :invalid_request}
      end

      for metadata <- [
            nil,
            [],
            %{},
            %{"request_id" => @id},
            %Metadata{},
            %{request_id: @id, extra: true},
            %{request_id: String.upcase(@id)},
            %{request_id: String.duplicate("a", 31)},
            %{request_id: String.duplicate("a", 33)},
            %{request_id: String.duplicate("g", 32)},
            %{request_id: <<255::size(256)>>}
          ] do
        assert Dispatcher.dispatch("opaque.Token", @request, metadata) ==
                 {:error, :invalid_request}
      end

      assert Dispatcher.dispatch(
               "opaque.Token",
               {:projects, "*", %{limit: 50, cursor: nil}},
               @metadata
             ) == {:error, :invalid_request}

      assert Repo.get_dynamic_repo() === :synthetic_wrong_repo
    after
      Repo.put_dynamic_repo(previous)
    end
  end

  test "a preselected dynamic Repo is refused and never reset" do
    previous = Repo.put_dynamic_repo(self())

    try do
      assert Dispatcher.dispatch("opaque.Token", @request, @metadata) ==
               {:error, :authorization_unavailable}

      assert Repo.get_dynamic_repo() === self()
    after
      Repo.put_dynamic_repo(previous)
    end
  end

  test "fixed default missing registered owner gives ordinary redacted 503 without Repo startup" do
    assert Process.whereis(Repo) == nil

    for token <- ["opaque.Token", "SYNTHETIC.private.error.marker", String.duplicate("x", 4089)] do
      assert {:ok, response} = Dispatcher.dispatch(token, @request, @metadata)
      assert Map.keys(response) |> Enum.sort() == [:body, :headers, :status]
      assert response.status == 503

      assert response.headers == [
               {"cache-control", "no-store"},
               {"content-type", "application/json; charset=utf-8"},
               {"x-request-id", @id},
               {"retry-after", "1"}
             ]

      assert Jason.decode!(response.body) == %{
               "error" => %{
                 "code" => "identity_unavailable",
                 "message" => "Identity verification unavailable. Retry shortly."
               },
               "request_id" => @id
             }

      refute response.body =~ token
      refute response.body =~ "private"
      assert byte_size(response.body) < 512
      assert Process.whereis(Repo) == nil
      assert Repo.get_dynamic_repo() === Repo
    end
  end

  test "bounded malformed token grammar belongs to canonical BearerIdentity" do
    for token <- ["Bearer opaque.Token", "Cookie=private-marker", "bad\ntoken", "x y", <<255>>] do
      assert {:ok, response} = Dispatcher.dispatch(token, @request, @metadata)
      assert response.status == 400

      assert response.headers == [
               {"cache-control", "no-store"},
               {"content-type", "application/json; charset=utf-8"},
               {"x-request-id", @id},
               {"www-authenticate", ~s(Bearer error="invalid_request")}
             ]

      assert Jason.decode!(response.body)["error"]["code"] == "invalid_request"
      refute response.body =~ "private-marker"
    end
  end

  test "both operations preserve the server request ID and caller process state/mailbox" do
    send(self(), {:plug_conn, :sent})
    send(self(), {:synthetic_dispatcher_mailbox, :preserved})
    Process.put(:synthetic_dispatcher_context, :preserved)
    Process.put({MixerHosted.CustomerWorkspace.Storage, :active}, :synthetic_active_storage)

    Process.put(
      {MixerHosted.Authorization.Transaction.Context, :active},
      :synthetic_active_context
    )

    {:messages, before} = Process.info(self(), :messages)

    try do
      for request <- [@request, {:projects, " org+&%/租 ", %{limit: 100, cursor: nil}}] do
        assert {:ok, %{status: 503, headers: headers}} =
                 Dispatcher.dispatch("opaque.Token", request, @metadata)

        assert List.keyfind(headers, "x-request-id", 0) == {"x-request-id", @id}
        assert Process.info(self(), :messages) == {:messages, before}
        assert Process.get(:synthetic_dispatcher_context) == :preserved

        assert Process.get({MixerHosted.CustomerWorkspace.Storage, :active}) ==
                 :synthetic_active_storage

        assert Process.get({MixerHosted.Authorization.Transaction.Context, :active}) ==
                 :synthetic_active_context
      end
    after
      Process.delete(:synthetic_dispatcher_context)
      Process.delete({MixerHosted.CustomerWorkspace.Storage, :active})
      Process.delete({MixerHosted.Authorization.Transaction.Context, :active})
    end

    assert_receive {:plug_conn, :sent}
    assert_receive {:synthetic_dispatcher_mailbox, :preserved}
    refute_receive {:plug_conn, :sent}, 0
  end
end
