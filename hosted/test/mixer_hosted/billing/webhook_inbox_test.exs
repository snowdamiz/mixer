defmodule MixerHosted.Billing.WebhookInboxTest.Worker do
  use Oban.Worker, queue: :billing
  def perform(_job), do: :ok
end

defmodule MixerHosted.Billing.WebhookInboxTest.InvalidWorker do
  use Oban.Worker, queue: :billing
  def new(args, opts), do: super(args, Keyword.put(opts, :priority, -1))
  def perform(_job), do: :ok
end

defmodule MixerHosted.Billing.WebhookInboxTest.UniqueWorker do
  use Oban.Worker, queue: :billing, unique: [period: :infinity, fields: [:worker]]
  def perform(_job), do: :ok
end

defmodule MixerHosted.Billing.WebhookInboxTest.Controller do
  use Phoenix.Controller, formats: [:json]

  def accept(conn, _params) do
    alias MixerHosted.Billing.{RawWebhookCapture, WebhookInbox}
    config = Application.fetch_env!(:mixer_hosted, :billing_ingress_test_config)

    with {:ok, captured, conn} <- RawWebhookCapture.capture(conn) do
      case WebhookInbox.admit(captured, config) do
        {:ok, _, _} -> Plug.Conn.send_resp(conn, 200, "accepted")
        {:error, :invalid_signature} -> Plug.Conn.send_resp(conn, 400, "rejected")
        {:error, _} -> Plug.Conn.send_resp(conn, 503, "unavailable")
      end
    else
      {:error, _, conn} -> Plug.Conn.send_resp(conn, 400, "rejected")
    end
  end
end

defmodule MixerHosted.Billing.WebhookInboxTest.Router do
  use Phoenix.Router
  post("/api/v1/webhooks/stripe", MixerHosted.Billing.WebhookInboxTest.Controller, :accept)
end

defmodule MixerHosted.Billing.WebhookInboxTest do
  use ExUnit.Case, async: false
  @moduletag :database
  alias MixerHosted.Billing.{RawWebhookCapture, WebhookInbox}
  alias MixerHosted.Repo
  @secret "whsec_mixer_public_test_only_r325"

  setup_all do
    port = System.fetch_env!("MIXER_BILLING_DATABASE_PORT") |> String.to_integer()

    repo_config = [
      hostname: "127.0.0.1",
      port: port,
      database: "mixer_billing_r325",
      username: "mixer_fixture",
      pool_size: 8
    ]

    previous = Application.get_env(:mixer_hosted, Repo)
    Application.put_env(:mixer_hosted, Repo, repo_config)

    on_exit(fn ->
      if previous,
        do: Application.put_env(:mixer_hosted, Repo, previous),
        else: Application.delete_env(:mixer_hosted, Repo)
    end)

    start_supervised!({Repo, repo_config})
    Code.require_file("../../../priv/repo/migrations/20261024000000_add_oban.exs", __DIR__)
    Ecto.Migrator.up(Repo, 20_261_024_000_000, MixerHosted.Repo.Migrations.AddOban)

    Code.require_file(
      "../../../priv/repo/migrations/20261110000000_add_billing_webhook_inbox.exs",
      __DIR__
    )

    Ecto.Migrator.up(Repo, 20_261_110_000_000, MixerHosted.Repo.Migrations.AddBillingWebhookInbox)

    start_supervised!(
      {Oban, repo: Repo, queues: false, plugins: false, peer: false, testing: :manual}
    )

    :ok
  end

  setup do
    Repo.query!("TRUNCATE mixer_billing_webhook_inbox, oban_jobs")
    :ok
  end

  defp config do
    %{
      endpoint_id: "platform-test",
      account: nil,
      livemode: false,
      secrets: [@secret],
      worker: __MODULE__.Worker
    }
  end

  defp event(overrides \\ %{}) do
    Map.merge(
      %{
        "object" => "event",
        "id" => "evt_r325",
        "type" => "customer.subscription.updated",
        "created" => 1_700_000_000,
        "livemode" => false,
        "data" => %{"object" => %{"id" => "sub_r325", "object" => "subscription"}}
      },
      overrides
    )
  end

  defp capture(event, options \\ []) do
    body = if is_binary(event), do: event, else: Jason.encode!(event)
    timestamp = Keyword.get(options, :timestamp, System.system_time(:second))
    secret = Keyword.get(options, :secret, @secret)

    mac =
      :crypto.mac(:hmac, :sha256, secret, [to_string(timestamp), ".", body])
      |> Base.encode16(case: :lower)

    conn =
      Plug.Test.conn(:post, "/api/v1/webhooks/stripe", body)
      |> Plug.Conn.put_req_header("content-type", "application/json")
      |> Plug.Conn.put_req_header("content-length", to_string(byte_size(body)))
      |> Plug.Conn.put_req_header("stripe-signature", "t=#{timestamp},v1=#{mac}")

    assert {:ok, captured, _conn} = RawWebhookCapture.capture(conn)
    captured
  end

  defp counts do
    [
      Repo.query!("SELECT count(*) FROM mixer_billing_webhook_inbox").rows,
      Repo.query!("SELECT count(*) FROM oban_jobs").rows
    ]
  end

  test "real Plug bytes commit one durable event and one Oban job before success" do
    captured = capture(event())
    assert {:ok, :accepted, id} = WebhookInbox.admit(captured, config())
    assert counts() == [[[1]], [[1]]]

    assert %{rows: [["evt_r325", "customer.subscription.updated", "sub_r325", digest]]} =
             Repo.query!(
               "SELECT event_id, event_type, object_id, body_sha256 FROM mixer_billing_webhook_inbox"
             )

    assert digest == :crypto.hash(:sha256, captured.raw_body)

    assert %{rows: [[%{"inbox_id" => ^id}, "available", "billing"]]} =
             Repo.query!("SELECT args, state, queue FROM oban_jobs")

    assert {:ok, :duplicate, ^id} = WebhookInbox.admit(captured, config())
    assert counts() == [[[1]], [[1]]]
  end

  test "forged, altered, stale, malformed and wrong-scope requests have no side effects" do
    inputs = [
      capture(event(), secret: "whsec_wrong_endpoint_test_only"),
      %{capture(event()) | raw_body: Jason.encode!(event(%{"id" => "evt_changed"}))},
      capture(event(), timestamp: System.system_time(:second) - 301),
      capture("not json"),
      capture(event(%{"livemode" => true})),
      capture(event(%{"account" => "acct_other"})),
      capture(event(%{"type" => "unknown.event"})),
      capture(event(%{"data" => %{"object" => %{"id" => "sub_r325", "object" => "invoice"}}}))
    ]

    for captured <- inputs do
      assert {:error, _} = WebhookInbox.admit(captured, config())
      assert counts() == [[[0]], [[0]]]
    end
  end

  test "concurrent duplicate deliveries enqueue exactly once" do
    captured = capture(event())

    results =
      1..12
      |> Task.async_stream(fn _ -> WebhookInbox.admit(captured, config()) end,
        max_concurrency: 4,
        timeout: 5000
      )
      |> Enum.map(fn {:ok, value} -> value end)

    assert Enum.count(results, &match?({:ok, :accepted, _}, &1)) == 1
    assert Enum.count(results, &match?({:ok, :duplicate, _}, &1)) == 11
    assert counts() == [[[1]], [[1]]]
  end

  test "enqueue rejection rolls back inbox and permits a later honest retry" do
    captured = capture(event())

    assert {:error, :enqueue_failed} =
             WebhookInbox.admit(captured, %{config() | worker: __MODULE__.InvalidWorker})

    assert counts() == [[[0]], [[0]]]
    assert {:ok, :accepted, _} = WebhookInbox.admit(captured, config())
    assert counts() == [[[1]], [[1]]]
  end

  test "event id collisions cannot replace a committed event or enqueue another job" do
    assert {:ok, :accepted, _} = WebhookInbox.admit(capture(event()), config())

    assert {:error, :event_conflict} =
             WebhookInbox.admit(capture(event(%{"created" => 1_700_000_001})), config())

    assert counts() == [[[1]], [[1]]]
  end

  test "a worker uniqueness conflict cannot acknowledge a new inbox event without its own job" do
    config = %{config() | worker: __MODULE__.UniqueWorker}
    assert {:ok, :accepted, _} = WebhookInbox.admit(capture(event()), config)

    assert {:error, :enqueue_failed} =
             WebhookInbox.admit(capture(event(%{"id" => "evt_other"})), config)

    assert counts() == [[[1]], [[1]]]
  end

  test "ambiguous signed JSON is rejected before admission" do
    body = Jason.encode!(event())

    for prefix <- [~s("livemode":true,), ~s("id":"evt_other",)] do
      ambiguous = "{" <> prefix <> binary_part(body, 1, byte_size(body) - 1)
      assert {:error, :invalid_event} = WebhookInbox.admit(capture(ambiguous), config())
    end

    assert counts() == [[[0]], [[0]]]
  end

  test "Connect account and endpoint secrets are scoped independently" do
    captured = capture(event(%{"account" => "acct_bound"}))
    assert {:error, :wrong_scope} = WebhookInbox.admit(captured, config())
    assert {:ok, :accepted, _} = WebhookInbox.admit(captured, %{config() | account: "acct_bound"})

    assert {:ok, :accepted, _} =
             WebhookInbox.admit(captured, %{
               config()
               | account: "acct_bound",
                 endpoint_id: "other-endpoint"
             })

    assert counts() == [[[2]], [[2]]]
  end

  test "real loopback Phoenix route responds only after durable admission, and retries on enqueue failure" do
    Application.put_env(:mixer_hosted, :billing_ingress_test_config, config())
    on_exit(fn -> Application.delete_env(:mixer_hosted, :billing_ingress_test_config) end)

    pid =
      start_supervised!(
        {Bandit, plug: __MODULE__.Router, ip: {127, 0, 0, 1}, port: 0, startup_log: false}
      )

    {:ok, {_address, port}} = ThousandIsland.listener_info(pid)
    url = ~c"http://127.0.0.1:" ++ Integer.to_charlist(port) ++ ~c"/api/v1/webhooks/stripe"
    captured = capture(event())
    [signature] = captured.signature_header_values

    request =
      {url, [{~c"stripe-signature", String.to_charlist(signature)}], ~c"application/json",
       captured.raw_body}

    assert {:ok, {{_, 200, _}, _, ~c"accepted"}} =
             :httpc.request(:post, request, [timeout: 2000], [])

    assert counts() == [[[1]], [[1]]]

    assert {:ok, {{_, 200, _}, _, ~c"accepted"}} =
             :httpc.request(:post, request, [timeout: 2000], [])

    assert counts() == [[[1]], [[1]]]

    {url, headers, media_type, body} = request
    forged = {url, headers, media_type, body <> " "}
    assert {:ok, {{_, 400, _}, _, _}} = :httpc.request(:post, forged, [timeout: 2000], [])
    assert counts() == [[[1]], [[1]]]

    Application.put_env(:mixer_hosted, :billing_ingress_test_config, %{
      config()
      | worker: __MODULE__.InvalidWorker
    })

    next = capture(event(%{"id" => "evt_http_retry"}))
    [signature] = next.signature_header_values

    request =
      {url, [{~c"stripe-signature", String.to_charlist(signature)}], ~c"application/json",
       next.raw_body}

    assert {:ok, {{_, 503, _}, _, _}} = :httpc.request(:post, request, [timeout: 2000], [])
    assert counts() == [[[1]], [[1]]]
  end

  test "older events remain separate reconciliation triggers without applying stale billing state" do
    assert {:ok, :accepted, _} = WebhookInbox.admit(capture(event()), config())

    assert {:ok, :accepted, _} =
             WebhookInbox.admit(
               capture(event(%{"id" => "evt_older", "created" => 1_600_000_000})),
               config()
             )

    assert counts() == [[[2]], [[2]]]
  end

  test "unconfigured verifier and worker fail closed before database admission" do
    for config <- [%{config() | secrets: []}, %{config() | worker: NonexistentWorker}] do
      assert {:error, :verification_unavailable} = WebhookInbox.admit(capture(event()), config)
      assert counts() == [[[0]], [[0]]]
    end
  end

  test "an in-memory Oban engine cannot claim durable acceptance" do
    Oban.Testing.with_testing_mode(:inline, fn ->
      assert {:error, :verification_unavailable} = WebhookInbox.admit(capture(event()), config())
    end)

    assert counts() == [[[0]], [[0]]]
  end
end
