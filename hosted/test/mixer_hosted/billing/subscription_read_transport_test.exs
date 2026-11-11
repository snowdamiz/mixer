defmodule MixerHosted.Billing.SubscriptionReadTransportTest do
  use ExUnit.Case, async: false
  import ExUnit.CaptureLog
  alias MixerHosted.Billing.{ObservedSubscription, SubscriptionReadTransport}
  alias MixerHosted.Billing.SubscriptionTLSFixture, as: TLS

  setup_all do
    {:ok, server} = TLS.start_link()
    Process.unlink(server)
    authority = GenServer.call(server, :authority)
    token = Base.url_encode64(:crypto.strong_rand_bytes(32), padding: false)

    c = %{
      origin: "https://api.stripe.com",
      api_version: "2026-10-28.endive",
      account: "acct_Synthetic546",
      livemode: false,
      secret_ref: "vault:billing546",
      ca_roots: [authority.ca],
      resolvers: [{{127, 0, 0, 1}, 53}],
      connect_ms: 500,
      read_ms: 500,
      deadline_ms: 1500
    }

    {:ok, handle} = SubscriptionReadTransport.new(c, fn _ -> {:ok, token} end)

    on_exit(fn ->
      info = TLS.info(server)
      owned_stopped = stop_fixture(server, info)
      assert owned_stopped

      if cleanup_path = System.get_env("MIXER_SUBSCRIPTION_TEST_CLEANUP") do
        File.write!(
          cleanup_path,
          Jason.encode!(%{
            fixture_stopped: not Process.alive?(server),
            owned_handlers_and_acceptor_stopped: owned_stopped,
            key_dir_removed: info.key_dir_removed,
            accepted: info.accepted,
            peer_closed: info.closed,
            active_at_cleanup: map_size(info.sockets),
            request_count: length(info.requests),
            scope: "fresh R546 loopback fixture only"
          })
        )
      end
    end)

    {:ok, server: server, port: authority.port, config: c, handle: handle, token: token}
  end

  defp stop_fixture(server, info) do
    owned = [info.acceptor | Map.keys(info.sockets)]
    monitors = Enum.map(owned, &{&1, Process.monitor(&1)})
    GenServer.stop(server)

    Enum.all?(monitors, fn {pid, monitor} ->
      receive do
        {:DOWN, ^monitor, :process, ^pid, _} -> true
      after
        1000 -> false
      end
    end)
  end

  defp body(changes \\ %{}) do
    Map.merge(
      %{
        "id" => "sub_Synthetic546",
        "object" => "subscription",
        "customer" => "cus_Synthetic546",
        "livemode" => false,
        "status" => "active"
      },
      changes
    )
    |> Jason.encode!()
  end

  defp read(c, handle \\ nil),
    do:
      SubscriptionReadTransport.read_fixture(
        handle || c.handle,
        "sub_Synthetic546",
        "cus_Synthetic546",
        {127, 0, 0, 1},
        c.port
      )

  defp raw(body, headers \\ "", status \\ "200 OK"),
    do:
      "HTTP/1.1 " <>
        status <>
        "\r\nContent-Type: application/json\r\nContent-Length: " <>
        Integer.to_string(byte_size(body)) <> "\r\n" <> headers <> "\r\n" <> body

  defp reject(c, payload) do
    TLS.configure(c.server, {:body, payload})
    assert {:error, _} = read(c)
  end

  test "fixed verified TLS GET returns only checked facts with no ordering or owning-account claim",
       c do
    TLS.configure(
      c.server,
      {:body,
       body(%{
         "created" => 999,
         "version" => 999,
         "account" => "acct_Untrusted",
         "metadata" => %{"tenant" => "untrusted"}
       })}
    )

    assert {:ok, observation} = read(c)

    assert observation == %ObservedSubscription{
             subscription_id: "sub_Synthetic546",
             customer_id: "cus_Synthetic546",
             livemode: false,
             status: "active"
           }

    assert Map.keys(Map.from_struct(observation)) |> Enum.sort() ==
             Enum.sort([:subscription_id, :customer_id, :livemode, :status, :ordering])

    assert observation.ordering == :ordering_unavailable
    [request | _] = TLS.info(c.server).requests
    # Use boolean assertions so a failure cannot print a credential-bearing HTTP request.
    proper_request =
      String.starts_with?(request.request, "GET /v1/subscriptions/sub_Synthetic546 HTTP/1.1\r\n") and
        String.contains?(request.request, "host: api.stripe.com") and
        String.contains?(request.request, "stripe-account: acct_Synthetic546\r\n") and
        String.contains?(request.request, "stripe-version: 2026-10-28.endive\r\n") and
        String.contains?(request.request, "authorization: Bearer " <> c.token <> "\r\n") and
        not String.contains?(request.request, "cookie:") and
        String.ends_with?(request.request, "\r\n\r\n")

    assert proper_request
    assert request.tls[:sni_hostname] == ~c"api.stripe.com"
  end

  test "all eight documented statuses and live-mode scope decode", c do
    for status <-
          ~w(incomplete incomplete_expired trialing active past_due canceled unpaid paused) do
      TLS.configure(c.server, {:body, body(%{"status" => status})})
      assert {:ok, %{status: ^status, ordering: :ordering_unavailable}} = read(c)
    end

    {:ok, live} =
      SubscriptionReadTransport.new(%{c.config | livemode: true}, fn _ -> {:ok, c.token} end)

    TLS.configure(c.server, {:body, body(%{"livemode" => true})})
    assert {:ok, %{livemode: true}} = read(c, live)
  end

  test "unknown statuses, wrong/malformed identities, object, mode and customer refuse over TLS",
       c do
    for fields <- [
          %{"status" => "new_unadmitted"},
          %{"status" => nil},
          %{"id" => "sub_Other"},
          %{"id" => 3},
          %{"customer" => "cus_Other"},
          %{"customer" => %{"id" => "cus_Synthetic546"}},
          %{"livemode" => true},
          %{"livemode" => 0},
          %{"object" => "customer"}
        ] do
      reject(c, body(fields))
    end

    reject(c, Jason.encode!(%{"id" => "sub_Synthetic546"}))
  end

  test "malformed UTF8, invalid/truncated JSON and duplicate decoded keys including ignored nested fields refuse",
       c do
    for payload <- [
          "{",
          "[]",
          "null",
          "true",
          "{}{}",
          <<255>>,
          "{\"status\":NaN}",
          String.replace(body(), "\"active\"", "\"active\",\"status\":\"unpaid\""),
          String.replace(body(), "\"active\"", "\"active\",\"st\\u0061tus\":\"unpaid\""),
          String.replace(body(), "{", "{\"unused\":{\"x\":1,\"x\":2},", global: false)
        ] do
      reject(c, payload)
    end
  end

  test "JSON depth, object members and collection bounds apply even to unused provider fields",
       c do
    reject(c, body(%{"unused" => Enum.reduce(1..20, 0, fn _, v -> [v] end)}))
    reject(c, body(%{"unused" => Enum.to_list(1..65)}))
    reject(c, body(Map.new(1..65, fn n -> {"unused#{n}", n} end)))
    TLS.configure(c.server, {:body, body(%{"unused" => "braces { [ ] } and escaped quote \""})})
    assert {:ok, _} = read(c)
  end

  test "fixed origin/version/config authority and ID path/query/userinfo injection are rejected before IO",
       c do
    before_count = TLS.info(c.server).accepted

    for id <- [
          "sub_",
          "sub_x/y",
          "sub_x?expand[]=customer",
          "sub_x#fragment",
          "sub_x%2F..",
          "sub_x@evil",
          "https://evil.test",
          "sub_x\r\nCookie: bad",
          "sub_é",
          "sub_" <> String.duplicate("x", 129)
        ] do
      assert {:error, :scope_rejected} =
               SubscriptionReadTransport.read_fixture(
                 c.handle,
                 id,
                 "cus_Synthetic546",
                 {127, 0, 0, 1},
                 c.port
               )
    end

    for delta <- [
          %{origin: "https://api.stripe.com@evil.test"},
          %{origin: "https://api.stripe.com?x=y"},
          %{origin: "http://api.stripe.com"},
          %{origin: "https://api.stripe.com/path"},
          %{api_version: "2026-10-28.endive\r\nX: bad"},
          %{account: "acct_x\r\nX: bad"},
          %{livemode: "false"},
          %{secret_ref: "ref\n"},
          %{deadline_ms: 5001},
          %{read_ms: 0},
          %{token: "payload-controlled"},
          %{tenant: "payload-controlled"},
          %{ca_roots: []}
        ] do
      assert {:error, :configuration_rejected} =
               SubscriptionReadTransport.new(Map.merge(c.config, delta), fn _ -> :error end)
    end

    assert {:error, :scope_rejected} =
             SubscriptionReadTransport.read(c.handle, %{"url" => "bad"}, "cus_Synthetic546")

    assert TLS.info(c.server).accepted == before_count
  end

  test "redirects and error bodies are refused with no second destination request", c do
    before_count = length(TLS.info(c.server).requests)

    for status <- [
          "301 Moved",
          "302 Found",
          "307 Temporary",
          "308 Permanent",
          "401 Unauthorized",
          "429 Limited",
          "500 Error"
        ] do
      TLS.configure(
        c.server,
        {:raw,
         raw(
           c.token,
           "Location: https://127.0.0.1:1/\r\nSet-Cookie: " <> c.token <> "\r\n",
           status
         )}
      )

      assert {:error, :response_rejected} = read(c)
    end

    assert length(TLS.info(c.server).requests) == before_count + 7
  end

  test "HTTP truncation, body/header/encoding/framing bounds reject", c do
    TLS.configure(
      c.server,
      {:truncated,
       "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{}"}
    )

    assert {:error, :response_rejected} = read(c)

    for response <- [
          raw(String.duplicate("x", 262_145)),
          raw(body(), "Content-Encoding: gzip\r\n"),
          raw(body(), "Content-Length: 1\r\n"),
          raw(body(), "Transfer-Encoding: chunked\r\n"),
          raw(body(), "X-Large: " <> String.duplicate("a", 10_241) <> "\r\n")
        ] do
      TLS.configure(c.server, {:raw, response})
      assert {:error, :response_rejected} = read(c)
    end
  end

  test "unknown CA and wrong hostname refuse before HTTP authorization is sent", c do
    {:ok, wrong} = MixerHosted.Identity.TLSFixture.start_link()
    Process.unlink(wrong)

    on_exit(fn ->
      assert stop_fixture(wrong, MixerHosted.Identity.TLSFixture.info(wrong))
    end)

    a = GenServer.call(wrong, :authority)

    {:ok, wrong_host} =
      SubscriptionReadTransport.new(%{c.config | ca_roots: [a.ca]}, fn _ -> {:ok, c.token} end)

    assert {:error, :tls_rejected} =
             SubscriptionReadTransport.read_fixture(
               wrong_host,
               "sub_Synthetic546",
               "cus_Synthetic546",
               {127, 0, 0, 1},
               a.port
             )

    assert MixerHosted.Identity.TLSFixture.info(wrong).requests == []

    {:ok, untrusted} =
      SubscriptionReadTransport.new(%{c.config | ca_roots: [a.ca]}, fn _ -> {:ok, c.token} end)

    before_count = length(TLS.info(c.server).requests)
    assert {:error, :tls_rejected} = read(c, untrusted)
    assert length(TLS.info(c.server).requests) == before_count
  end

  test "read timeout, TLS handshake timeout, total slow-drip deadline close owned sockets", c do
    TLS.configure(c.server, :stall)

    {:ok, short} =
      SubscriptionReadTransport.new(
        %{c.config | read_ms: 80, connect_ms: 80, deadline_ms: 180},
        fn _ -> {:ok, c.token} end
      )

    start = System.monotonic_time(:millisecond)
    assert {:error, :response_rejected} = read(c, short)
    assert System.monotonic_time(:millisecond) - start < 1000
    {:ok, raw_server} = MixerHosted.Identity.RawFixture.start_link(mode: :stall)
    Process.unlink(raw_server)

    on_exit(fn ->
      assert stop_fixture(raw_server, :sys.get_state(raw_server))
    end)

    a = MixerHosted.Identity.RawFixture.info(raw_server)

    assert {:error, :tls_rejected} =
             SubscriptionReadTransport.read_fixture(
               short,
               "sub_Synthetic546",
               "cus_Synthetic546",
               {127, 0, 0, 1},
               a.port
             )

    TLS.configure(c.server, {:drip, String.graphemes(raw(body())), 10})
    start = System.monotonic_time(:millisecond)
    assert {:error, :response_rejected} = read(c, short)
    assert System.monotonic_time(:millisecond) - start < 1000
  end

  test "trusted secret resolver is bounded; bad tokens/exceptions produce no secret-bearing logs or errors",
       c do
    parent = self()

    {:ok, stalled} =
      SubscriptionReadTransport.new(
        %{c.config | read_ms: 50, connect_ms: 50, deadline_ms: 50},
        fn _ ->
          send(parent, {:secret_reader, self()})

          receive do
            :never -> :error
          end
        end
      )

    assert {:error, :credential_unavailable} = read(c, stalled)
    assert_receive {:secret_reader, pid}
    refute Process.alive?(pid)
    before_count = TLS.info(c.server).accepted

    output =
      capture_log(fn ->
        for resolver <- [
              fn _ -> raise c.token end,
              fn _ -> throw(c.token) end,
              fn _ -> {:error, c.token} end,
              fn _ -> {:ok, c.token <> "\r\nCookie: bad"} end
            ] do
          {:ok, handle} = SubscriptionReadTransport.new(c.config, resolver)
          assert {:error, :credential_unavailable} = read(c, handle)
        end
      end)

    redacted = not String.contains?(output <> inspect(c.handle), c.token)
    assert redacted
    assert TLS.info(c.server).accepted == before_count
  end

  test "chunked and close-delimited HTTP carry checked facts; unsupported media/framing refuse",
       c do
    payload = body()

    TLS.configure(
      c.server,
      {:raw,
       "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n" <>
         Integer.to_string(byte_size(payload), 16) <> "\r\n" <> payload <> "\r\n0\r\n\r\n"}
    )

    assert {:ok, %{ordering: :ordering_unavailable}} = read(c)

    TLS.configure(
      c.server,
      {:truncated, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" <> payload}
    )

    assert {:ok, %{ordering: :ordering_unavailable}} = read(c)

    for header <- [
          "Content-Type: text/html\r\n",
          "Content-Type: application/json\r\nContent-Encoding: br\r\n",
          "Content-Type: application/json\r\nTransfer-Encoding: chunked\r\nTrailer: x-untrusted\r\n"
        ] do
      TLS.configure(c.server, {:raw, "HTTP/1.1 200 OK\r\n" <> header <> "\r\n" <> payload})
      assert {:error, :response_rejected} = read(c)
    end

    refute function_exported?(SubscriptionReadTransport, :read_subscription, 2)
  end
end
