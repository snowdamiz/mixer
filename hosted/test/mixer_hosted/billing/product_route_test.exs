defmodule MixerHosted.Billing.ProductRouteTest.Worker do
  use Oban.Worker, queue: :billing

  def new(args, opts) do
    if owner = Application.get_env(:mixer_hosted, :billing_route_barrier) do
      send(owner, {:before_enqueue, self()})

      receive do
        :continue_enqueue -> :ok
      after
        2_000 -> raise "test barrier expired"
      end
    end

    super(args, opts)
  end

  def perform(_), do: :ok
end

defmodule MixerHosted.Billing.ProductRouteTest do
  use ExUnit.Case, async: false
  @moduletag :database
  alias MixerHosted.Repo
  @secret "whsec_r354_synthetic_local_only"

  setup_all do
    cfg = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TEST_DATABASE_PORT")),
      database: "mixer_billing_r354",
      username: "mixer_fixture",
      pool_size: 8
    ]

    Application.put_env(:mixer_hosted, Repo, cfg)
    start_supervised!({Repo, cfg})
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

    {:ok, independent} = Postgrex.start_link(cfg)
    # This is a dedicated test BEAM. The production transport refuses foreign
    # subscribers; do not weaken that admission contract to host the fixture.
    for handler <- :telemetry.list_handlers([]), do: :telemetry.detach(handler.id)
    Application.put_env(:mixer_hosted, :billing_webhook, config())
    {:ok, transport} = MixerHostedWeb.BillingWebhookEndpoint.start_link()
    Process.unlink(transport)

    on_exit(fn ->
      Supervisor.stop(transport)
      Application.delete_env(:mixer_hosted, :billing_webhook)
      Application.delete_env(:mixer_hosted, :billing_route_barrier)
    end)

    {_, listener, _, _} =
      Enum.find(Supervisor.which_children(transport), fn {_, _, _, modules} ->
        Bandit in modules
      end)

    {:ok, {_, port}} = ThousandIsland.listener_info(listener)
    {:ok, port: port, observer: independent}
  end

  setup do
    Repo.query!("TRUNCATE mixer_billing_webhook_inbox, oban_jobs")
    Application.put_env(:mixer_hosted, :billing_webhook, config())
    Application.delete_env(:mixer_hosted, :billing_route_barrier)
    :ok
  end

  defp config,
    do: %{
      endpoint_id: "platform-r354",
      account: nil,
      livemode: false,
      secrets: [@secret],
      worker: __MODULE__.Worker
    }

  defp body(id, extra \\ %{}),
    do:
      Jason.encode!(
        Map.merge(
          %{
            "object" => "event",
            "id" => id,
            "type" => "customer.subscription.updated",
            "created" => 1_700_000_000,
            "livemode" => false,
            "data" => %{"object" => %{"id" => "sub_synthetic", "object" => "subscription"}}
          },
          extra
        )
      )

  defp request(port, body, opts \\ []) do
    now = System.system_time(:second)
    secret = Keyword.get(opts, :secret, @secret)

    signature =
      :crypto.mac(:hmac, :sha256, secret, [to_string(now), ".", body])
      |> Base.encode16(case: :lower)

    path = Keyword.get(opts, :path, "/api/v1/webhooks/stripe")
    url = String.to_charlist("http://127.0.0.1:#{port}#{path}")

    {:ok, {{_, status, _}, _, _}} =
      :httpc.request(
        :post,
        {url, [{~c"stripe-signature", String.to_charlist("t=#{now},v1=#{signature}")}],
         ~c"application/json", body},
        [timeout: 4_000],
        []
      )

    status
  end

  defp counts(conn) do
    for table <- ["mixer_billing_webhook_inbox", "oban_jobs"] do
      Postgrex.query!(conn, "SELECT count(*) FROM " <> table, []).rows
    end
  end

  test "real product HTTP waits while writes are invisible, then acknowledges committed inbox and job",
       c do
    Application.put_env(:mixer_hosted, :billing_route_barrier, self())
    task = Task.async(fn -> request(c.port, body("evt_commit")) end)
    assert_receive {:before_enqueue, handler}, 2_000
    assert counts(c.observer) == [[[0]], [[0]]]
    assert Task.yield(task, 30) == nil
    send(handler, :continue_enqueue)
    assert Task.await(task, 4_000) == 200
    assert counts(c.observer) == [[[1]], [[1]]]

    assert %{rows: [[id, %{"inbox_id" => id}]]} =
             Postgrex.query!(
               c.observer,
               "SELECT i.id::text, j.args FROM mixer_billing_webhook_inbox i JOIN oban_jobs j ON j.args->>'inbox_id'=i.id::text",
               []
             )
  end

  test "duplicate and conflicting signed event identities preserve the committed original", c do
    payload = body("evt_replay")
    assert request(c.port, payload) == 200
    assert request(c.port, payload) == 200
    assert request(c.port, payload <> " ") == 409
    assert counts(c.observer) == [[[1]], [[1]]]
  end

  test "deferred failure at outer COMMIT gives no false 2xx and rolls back both writes", c do
    Repo.query!(
      "CREATE FUNCTION r354_refuse_commit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic deferred commit failure'; END $$"
    )

    Repo.query!(
      "CREATE CONSTRAINT TRIGGER r354_commit_failure AFTER INSERT ON mixer_billing_webhook_inbox DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION r354_refuse_commit()"
    )

    try do
      assert request(c.port, body("evt_rollback")) == 503
      assert counts(c.observer) == [[[0]], [[0]]]
    after
      Repo.query!("DROP TRIGGER r354_commit_failure ON mixer_billing_webhook_inbox")
      Repo.query!("DROP FUNCTION r354_refuse_commit()")
    end

    assert request(c.port, body("evt_rollback")) == 200
    assert counts(c.observer) == [[[1]], [[1]]]
  end

  test "forged signatures, trusted scope mismatches and query paths leave no effects", c do
    assert request(c.port, body("evt_bad"), secret: "whsec_incorrect_synthetic") == 400
    assert request(c.port, body("evt_bad", %{"account" => "acct_victim"})) == 400
    assert request(c.port, body("evt_bad", %{"livemode" => true})) == 400
    assert request(c.port, body("evt_bad"), path: "/api/v1/webhooks/stripe?org=victim") == 400
    assert counts(c.observer) == [[[0]], [[0]]]
  end

  test "missing and invalid configuration refuse without writes", c do
    for config <- [nil, %{}, %{config() | secrets: []}, %{config() | worker: NoSuchWorker}] do
      Application.put_env(:mixer_hosted, :billing_webhook, config)
      assert request(c.port, body("evt_disabled")) == 503
      assert request(c.port, "malformed request") == 503
      assert {:error, :billing_disabled} = MixerHostedWeb.BillingWebhookEndpoint.start_link()
      assert counts(c.observer) == [[[0]], [[0]]]
    end
  end

  test "ambient caller transaction refuses before transport capture or admission", c do
    assert {:ok, conn} =
             Repo.transaction(fn ->
               MixerHostedWeb.BillingWebhookController.accept(
                 Plug.Test.conn(:post, "/api/v1/webhooks/stripe", "private"),
                 %{}
               )
             end)

    assert conn.status == 503
    assert counts(c.observer) == [[[0]], [[0]]]
  end

  test "request metadata never changes the server endpoint binding", c do
    payload =
      body("evt_metadata", %{
        "metadata" => %{"organization_id" => "victim", "endpoint_id" => "victim"}
      })

    assert request(c.port, payload) == 200

    assert %{rows: [["platform-r354", nil, false]]} =
             Postgrex.query!(
               c.observer,
               "SELECT endpoint_id, account, livemode FROM mixer_billing_webhook_inbox",
               []
             )

    assert counts(c.observer) == [[[1]], [[1]]]
  end
end
