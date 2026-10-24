defmodule MixerHosted.Identity.KeyOwnerTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{
    Admission,
    ConfiguredVerifier,
    DNSFixture,
    DNSResolver,
    GlobalAddress,
    HTTPFreshness,
    JWKSTransport,
    KeyOwner,
    Manifest,
    TLSFixture,
    TrustSnapshot
  }

  @profile %{
    profile_id: "fixture",
    profile_version: 1,
    issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api",
    client_id: "reviewed-client",
    identity_class: :human,
    enabled: true
  }
  @entry %{
    profile: @profile,
    jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
    transport: :hosted_https
  }
  setup_all do
    Application.ensure_all_started(:jose)
    Application.ensure_all_started(:mint)
    fixture = start_supervised!(TLSFixture)
    authority = GenServer.call(fixture, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "key1", "alg" => "RS256", "use" => "sig"})

    {:ok,
     Map.merge(authority, %{
       fixture: fixture,
       key: key,
       public: public,
       body: Jason.encode!(%{"keys" => [public]})
     })}
  end

  setup ctx do
    TLSFixture.configure(ctx.fixture, {:body, ctx.body})
    :ok
  end

  # The collector opts into run-local observations. Ordinary mix test must not
  # overwrite previously accepted evidence in the source checkout.
  defp write_evidence(name, bytes) do
    case System.get_env("MIXER_TEST_IDENTITY_EVIDENCE") do
      nil -> :ok
      directory -> File.write!(Path.join(directory, name), bytes)
    end
  end

  defp now, do: System.system_time(:second)
  defp deadline, do: System.monotonic_time(:millisecond) + 2_000

  defp fetch(ctx, entry \\ @entry),
    do: JWKSTransport.fetch_fixture(entry, ctx.ip, ctx.port, deadline(), [ctx.ca], nil)

  defp start_owner(ctx, name \\ TestKeyOwner, entries \\ [@entry]) do
    workers = Module.concat(name, Workers)
    start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: workers}, id: workers)

    opts = [
      name: name,
      manifest: entries,
      generation: 1,
      binding: "fixture",
      ca_roots: [ctx.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: workers,
      fixture: Map.take(ctx, [:ip, :port])
    ]

    {:ok, pid} = KeyOwner.start_fixture(opts)
    on_exit(fn -> if Process.alive?(pid), do: GenServer.stop(pid) end)
    {name, pid}
  end

  defp token(ctx, kid \\ "key1") do
    claims = %{
      "iss" => @profile.issuer,
      "aud" => @profile.audience,
      "sub" => "fixture-subject",
      "client_id" => @profile.client_id,
      "iat" => now() - 1,
      "exp" => now() + 120,
      "jti" => "fixture-credential"
    }

    JOSE.JWS.sign(ctx.key, Jason.encode!(claims), %{
      "alg" => "RS256",
      "typ" => "at+jwt",
      "kid" => kid
    })
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  test "K01 manifest limits and immutable identity transitions", ctx do
    assert {:ok, _} = Manifest.validate([@entry])
    assert {:error, _} = Manifest.validate(List.duplicate(@entry, 2))

    assert {:error, _} =
             Manifest.validate(for i <- 1..9, do: put_in(@entry.profile.profile_id, "p#{i}"))

    for bad <- [
          put_in(@entry.jwks_endpoint.host, "127.0.0.1"),
          put_in(@entry.jwks_endpoint.path, "/a/../keys"),
          put_in(@entry.jwks_endpoint.path, "/keys?x=1"),
          Map.update!(@entry, :profile, &Map.put(&1, :extra, true))
        ] do
      assert {:error, _} = Manifest.validate([bad])
    end

    assert {:error, _} =
             TrustSnapshot.new(
               @profile,
               Jason.encode!(%{
                 "keys" => for(i <- 1..17, do: Map.put(ctx.public, "kid", "k#{i}"))
               }),
               now(),
               now() + 120
             )

    {owner, pid} = start_owner(ctx)
    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert {:error, :invalid_manifest} =
             KeyOwner.replace_manifest(owner, 1, [put_in(@entry.profile.client_id, "different")])

    assert :sys.get_state(pid).generation == 1
    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, [put_in(@entry.profile.enabled, false)])

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(owner, 2, [@entry])
  end

  test "K02 real TLS pins peer Host path SNI; CA and hostname fail", ctx do
    assert {:ok, candidate} = fetch(ctx)
    assert candidate.peer == ctx.ip
    request = TLSFixture.info(ctx.fixture).requests |> hd()
    assert request.request =~ "GET /keys HTTP/1.1\r\n"
    assert String.downcase(request.request) =~ "host: jwks.fixture.invalid:#{ctx.port}\r\n"
    assert request.tls[:sni_hostname] == ~c"jwks.fixture.invalid"
    refute String.downcase(request.request) =~ "authorization:"
    refute String.downcase(request.request) =~ "cookie:"
    assert {:error, _} = fetch(ctx, put_in(@entry.jwks_endpoint.host, "wrong.fixture.invalid"))

    assert {:error, _} =
             JWKSTransport.fetch_fixture(
               @entry,
               ctx.ip,
               ctx.port,
               deadline(),
               :public_key.cacerts_get(),
               nil
             )

    assert TLSFixture.info(ctx.fixture).key_dir_removed
  end

  test "K02b real IPv6 and expired/future/downgrade certificates", ctx do
    ipv6 = start_supervised!({TLSFixture, [ip: {0, 0, 0, 0, 0, 0, 0, 1}]}, id: :ipv6)
    a = GenServer.call(ipv6, :authority)
    TLSFixture.configure(ipv6, {:body, ctx.body})
    assert {:ok, c} = JWKSTransport.fetch_fixture(@entry, a.ip, a.port, deadline(), [a.ca], nil)
    assert c.peer == a.ip

    for validity <- [:future, :expired] do
      fixture = start_supervised!({TLSFixture, [validity: validity]}, id: validity)
      a = GenServer.call(fixture, :authority)

      assert {:error, _} =
               JWKSTransport.fetch_fixture(@entry, a.ip, a.port, deadline(), [a.ca], nil)

      assert TLSFixture.info(fixture).requests == []
    end

    badchain = start_supervised!({TLSFixture, [tampered_signature: true]}, id: :badchain)
    bad = GenServer.call(badchain, :authority)

    assert {:error, _} =
             JWKSTransport.fetch_fixture(@entry, bad.ip, bad.port, deadline(), [bad.ca], nil)

    assert TLSFixture.info(badchain).requests == []

    plaintext =
      start_supervised!({MixerHosted.Identity.RawFixture, [mode: :plaintext]}, id: :plaintext)

    assert {:error, _} =
             JWKSTransport.fetch_fixture(
               @entry,
               ctx.ip,
               MixerHosted.Identity.RawFixture.info(plaintext).port,
               deadline(),
               [ctx.ca],
               nil
             )

    obsolete = start_supervised!({TLSFixture, [versions: [:"tlsv1.1"]]}, id: :obsolete)
    a = GenServer.call(obsolete, :authority)

    assert {:error, _} =
             JWKSTransport.fetch_fixture(@entry, a.ip, a.port, deadline(), [a.ca], nil)

    assert TLSFixture.info(obsolete).requests == []
  end

  test "K03 actual DNS rejects mixed/special addresses, chain overflow, truncation, delays" do
    dns = start_supervised!(DNSFixture)
    resolvers = [{{127, 0, 0, 1}, DNSFixture.info(dns).port}]

    assert {:ok, {8, 8, 8, 8}} =
             DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())

    for ip <- [
          {127, 0, 0, 1},
          {10, 1, 1, 1},
          {169, 254, 169, 254},
          {192, 0, 2, 1},
          {0, 0, 0, 0, 0, 0xFFFF, 0x7F00, 1},
          {0xFC00, 0, 0, 0, 0, 0, 0, 1},
          {0x2002, 0, 0, 0, 0, 0, 0, 1},
          {0x3FFF, 0, 0, 0, 0, 0, 0, 1}
        ] do
      refute GlobalAddress.global?(ip)
      DNSFixture.configure(dns, {:addresses, [{8, 8, 8, 8}, ip]})

      assert {:error, :dns_rejected} =
               DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())
    end

    for mode <- [
          {:addresses, for(i <- 1..17, do: {8, 8, 8, i})},
          {:chain, 9, false},
          {:chain, 2, true},
          :truncated
        ] do
      DNSFixture.configure(dns, mode)
      assert {:error, _} = DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())
    end

    DNSFixture.configure(dns, {:delay, 2_500})
    start = System.monotonic_time(:millisecond)
    assert {:error, _} = DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())
    assert System.monotonic_time(:millisecond) - start < 2_300
  end

  test "K04 rejected statuses never follow redirects or retain error bodies", ctx do
    sink = start_supervised!(TLSFixture, id: :sink)
    target = GenServer.call(sink, :authority)

    for status <- [301, 302, 307, 308, 304, 206, 401, 429, 500] do
      raw =
        "HTTP/1.1 #{status} Rejected\r\nLocation: https://jwks.fixture.invalid:#{target.port}/sink\r\nSet-Cookie: secret=never\r\n\r\n" <>
          String.duplicate("x", 393_216)

      TLSFixture.configure(ctx.fixture, {:raw, raw})
      assert {:error, _} = fetch(ctx)
    end

    assert TLSFixture.info(sink).accepted == 0
    TLSFixture.configure(ctx.fixture, {:body, ctx.body})
    assert {:ok, _} = fetch(ctx)

    req =
      TLSFixture.info(ctx.fixture).requests |> hd() |> Map.fetch!(:request) |> String.downcase()

    for secret <- ["cookie:", "proxy-authorization:", "forwarded"], do: refute(req =~ secret)
  end

  test "K05 four actual TLS workers exact boundary and hostile framing", ctx do
    body = ctx.body <> String.duplicate(" ", 262_144 - byte_size(ctx.body))
    TLSFixture.configure(ctx.fixture, {:body, body})
    start = System.monotonic_time(:millisecond)

    results =
      1..4
      |> Task.async_stream(fn _ -> fetch(ctx) end, max_concurrency: 4, timeout: 3_000)
      |> Enum.map(fn {:ok, r} -> r end)

    elapsed = System.monotonic_time(:millisecond) - start

    for result <- results do
      assert {:ok, c} = result
      assert byte_size(c.body) == 262_144
      assert {:ok, _} = TrustSnapshot.new(@profile, c.body, c.fetched_at, c.fresh_until)
      assert c.metrics.max_batch <= 16_384
      assert c.metrics.max_parser_buffer <= 10_240
      assert c.metrics.max_mailbox <= 4
      assert c.metrics.max_heap_bytes < 8_000_000
    end

    assert elapsed < 2_000

    metrics = %{
      case: "four-real-TLS-exact-262144-byte-JWKS",
      elapsed_ms: elapsed,
      workers: 4,
      results: Enum.map(results, fn {:ok, c} -> c.metrics end)
    }

    write_evidence(
      "transport-metrics.json",
      Jason.encode!(metrics, pretty: true)
    )

    TLSFixture.configure(ctx.fixture, {:body, body <> " "})
    assert {:error, _} = fetch(ctx)
    date = :httpd_util.rfc1123_date() |> List.to_string()

    base =
      "HTTP/1.1 200 OK\r\nDate: #{date}\r\nCache-Control: max-age=120\r\nContent-Type: application/json\r\n"

    for raw <- [
          String.replace(TLSFixture.response(ctx.body), "Date: ", "Date: " <> <<0xC2, 0xA0>>),
          base <> "Transfer-Encoding: chunked\r\n\r\n40001\r\n" <> body <> " \r\n0\r\n\r\n",
          base <> "\r\n" <> body <> " ",
          base <> "Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}",
          base <> "Content-Length: 2\r\nTransfer-Encoding: chunked\r\n\r\n{}",
          base <> "Content-Encoding: gzip\r\nContent-Length: 2\r\n\r\n{}",
          base <> "Transfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\nDate: #{date}\r\n\r\n",
          base <> "Content-Length: 5\r\n\r\n{}",
          base <> "X-Huge: " <> String.duplicate("a", 10_241) <> "\r\n\r\n",
          String.duplicate("HTTP/1.1 100 Continue\r\n\r\n", 5) <> TLSFixture.response(ctx.body)
        ] do
      TLSFixture.configure(ctx.fixture, {:raw, raw})
      assert {:error, _} = fetch(ctx)
    end
  end

  test "K05b four full chunked candidates and client TLS resource observations", ctx do
    body = ctx.body <> String.duplicate(" ", 262_144 - byte_size(ctx.body))

    headers =
      TLSFixture.response("")
      |> String.split("\r\n\r\n")
      |> hd()
      |> String.replace("Content-Length: 0", "Transfer-Encoding: chunked")

    raw = headers <> "\r\n\r\n40000\r\n" <> body <> "\r\n0\r\n\r\n"
    TLSFixture.configure(ctx.fixture, {:raw, raw})
    probe = start_supervised!(MixerHosted.Identity.SocketProbe)
    start = System.monotonic_time(:millisecond)

    results =
      Task.async_stream(
        1..4,
        fn _ ->
          JWKSTransport.fetch_fixture(@entry, ctx.ip, ctx.port, deadline(), [ctx.ca], probe)
        end,
        max_concurrency: 4,
        timeout: 3_000
      )
      |> Enum.map(fn {:ok, r} -> r end)

    elapsed = System.monotonic_time(:millisecond) - start
    assert elapsed < 2_000

    for result <- results do
      assert {:ok, c} = result
      assert c.body == body
      assert {:ok, _} = TrustSnapshot.new(@profile, c.body, c.fetched_at, c.fresh_until)
    end

    eventually(fn -> MixerHosted.Identity.SocketProbe.info(probe).closed == 4 end)
    observation = MixerHosted.Identity.SocketProbe.info(probe)
    assert observation.max_active <= 4
    assert observation.max_ssl_memory < 8_000_000
    assert observation.max_ssl_binary_bytes < 4_000_000
    assert observation.max_ssl_mailbox < 64

    write_evidence(
      "chunked-TLS-resources.json",
      Jason.encode!(
        Map.merge(observation, %{
          elapsed_ms: elapsed,
          scope:
            "OTP29 client connection-handler and payload-sender process samples; binary references conservatively summed per process"
        }),
        pretty: true
      )
    )
  end

  test "K05f four full candidates validate publish and fence inside original deadline", ctx do
    body = ctx.body <> String.duplicate(" ", 262_144 - byte_size(ctx.body))
    TLSFixture.configure(ctx.fixture, {:body, body})
    entries = [@entry | for(i <- 1..3, do: put_in(@entry.profile.profile_id, "p#{i}"))]
    {owner, pid} = start_owner(ctx, TestKeyOwner, entries)
    credential = token(ctx)
    started = System.monotonic_time(:millisecond)

    results =
      Task.async_stream(
        entries,
        fn entry ->
          ConfiguredVerifier.authenticate(owner, entry.profile.profile_id, credential, now())
        end,
        max_concurrency: 4,
        timeout: 3_000
      )
      |> Enum.map(fn {:ok, result} -> result end)

    elapsed = System.monotonic_time(:millisecond) - started
    assert Enum.all?(results, &match?({:ok, _}, &1))
    assert elapsed < 2_000
    assert map_size(:sys.get_state(pid).snapshots) == 4
    assert map_size(:sys.get_state(pid).flights) == 0

    write_evidence(
      "owner-four-full-candidate-publication.json",
      Jason.encode!(
        %{
          profiles: 4,
          bytesPerJWKS: 262_144,
          elapsedMilliseconds: elapsed,
          scope:
            "actual TLS fetch, full JWKS validation, owner publication, JOSE token verification and final fence"
        },
        pretty: true
      )
    )
  end

  test "K05c one-byte chunks and oversized chunk lines are bounded by the original deadline",
       ctx do
    date = :httpd_util.rfc1123_date() |> List.to_string()

    headers =
      "HTTP/1.1 200 OK\r\nDate: #{date}\r\nCache-Control: max-age=120\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n"

    for payload <- [
          String.duplicate("1\r\n \r\n", 262_145) <> "0\r\n\r\n",
          String.duplicate("f", 10_241) <> "\r\n",
          "1;" <> String.duplicate("x", 10_241) <> "\r\n"
        ] do
      TLSFixture.configure(ctx.fixture, {:raw, headers <> payload})
      start = System.monotonic_time(:millisecond)
      assert {:error, _} = fetch(ctx)
      assert System.monotonic_time(:millisecond) - start < 2_300
    end
  end

  test "K05d four hostile fast error streams leave bounded TLS buffers and closed sockets", ctx do
    raw =
      "HTTP/1.1 500 Error\r\nContent-Type: application/json\r\n\r\n" <>
        String.duplicate("x", 8_388_608)

    TLSFixture.configure(ctx.fixture, {:raw, raw})
    probe = start_supervised!(MixerHosted.Identity.SocketProbe)

    results =
      Task.async_stream(
        1..4,
        fn _ ->
          JWKSTransport.fetch_fixture(@entry, ctx.ip, ctx.port, deadline(), [ctx.ca], probe)
        end,
        max_concurrency: 4,
        timeout: 3_000
      )
      |> Enum.map(fn {:ok, r} -> r end)

    assert Enum.all?(results, &match?({:error, _}, &1))
    eventually(fn -> MixerHosted.Identity.SocketProbe.info(probe).closed == 4 end)
    observation = MixerHosted.Identity.SocketProbe.info(probe)

    write_evidence(
      "hostile-fast-TLS-resources.json",
      Jason.encode!(
        Map.put(
          observation,
          :scope,
          "four actual 8MiB close-delimited500 responses; sampled exact client OTP29 SSL processes"
        ),
        pretty: true
      )
    )

    assert observation.max_active <= 4
    assert observation.max_ssl_memory < 8_000_000
    assert observation.max_ssl_binary_bytes < 4_000_000
    assert observation.max_ssl_mailbox < 128
  end

  test "K05e four suspended consumers preserve the declared TLS resource budget", ctx do
    raw =
      "HTTP/1.1 500 Error\r\nContent-Type: application/json\r\n\r\n" <>
        String.duplicate("x", 8_388_608)

    TLSFixture.configure(ctx.fixture, {:barrier, self(), raw})
    probe = start_supervised!(MixerHosted.Identity.SocketProbe)

    tasks =
      for _ <- 1..4,
          do:
            Task.async(fn ->
              JWKSTransport.fetch_fixture(@entry, ctx.ip, ctx.port, deadline(), [ctx.ca], probe)
            end)

    servers =
      for _ <- 1..4 do
        assert_receive {:tls_response_ready, pid}, 1_000
        pid
      end

    clients = Map.keys(:sys.get_state(probe).sockets)
    assert length(clients) == 4

    try do
      Enum.each(clients, &:erlang.suspend_process/1)
      Enum.each(servers, &send(&1, :release_response))
      Process.sleep(25)
      observation = MixerHosted.Identity.SocketProbe.info(probe)

      write_evidence(
        "suspended-consumer-TLS-resources.json",
        Jason.encode!(observation, pretty: true)
      )

      assert observation.max_ssl_binary_bytes < 4_000_000
      assert observation.max_ssl_memory < 8_000_000
      assert observation.max_ssl_mailbox < 128
    after
      Enum.each(clients, fn pid -> if Process.alive?(pid), do: :erlang.resume_process(pid) end)
    end

    assert Enum.all?(tasks, fn task -> match?({:error, _}, Task.await(task, 2_500)) end)
    eventually(fn -> MixerHosted.Identity.SocketProbe.info(probe).closed == 4 end)
  end

  test "K06 exact shorter freshness and paired clock rejection" do
    wall = System.system_time(:second) * 1_000

    date = Calendar.strftime(DateTime.from_unix!(div(wall, 1000)), "%a, %d %b %Y %H:%M:%S GMT")
    h = %{"date" => date, "cache-control" => "max-age=120, s-maxage=90", "age" => "10"}
    assert {:ok, f} = HTTPFreshness.calculate(h, {wall, 1_000}, {wall + 1_500, 2_500})
    assert f.fresh_until - f.fetched_at == 78
    assert f.expires_mono == 80_500

    for headers <- [
          %{},
          %{h | "cache-control" => "max-age=0"},
          %{h | "cache-control" => "no-store, max-age=20"},
          %{h | "cache-control" => "no-cache, max-age=20"},
          %{h | "cache-control" => "max-age=20, max-age=30"},
          Map.put(h, "vary", "*"),
          %{h | "date" => "not-a-date"},
          %{h | "age" => "-1"}
        ] do
      assert {:error, _} = HTTPFreshness.calculate(headers, {wall, 1_000}, {wall, 1_000})
    end

    short =
      Calendar.strftime(DateTime.from_unix!(div(wall, 1_000) + 20), "%a, %d %b %Y %H:%M:%S GMT")

    assert {:ok, shorter} =
             HTTPFreshness.calculate(Map.put(h, "expires", short), {wall, 1_000}, {wall, 1_000})

    assert shorter.fresh_until - shorter.fetched_at == 10

    future =
      Calendar.strftime(DateTime.from_unix!(div(wall, 1_000) + 31), "%a, %d %b %Y %H:%M:%S GMT")

    assert {:error, _} =
             HTTPFreshness.calculate(Map.put(h, "date", future), {wall, 1_000}, {wall, 1_000})

    assert {:error, _} = HTTPFreshness.calculate(h, {wall, 1_000}, {wall + 10_000, 1_001})
  end

  test "K07 watchdog deadline releases owned worker and waiters", ctx do
    TLSFixture.configure(ctx.fixture, :stall)
    {owner, pid} = start_owner(ctx)
    start = System.monotonic_time(:millisecond)

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert (System.monotonic_time(:millisecond) - start) in 1_900..2_300
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert :sys.get_state(pid).waiters == %{}

    assert :ets.select_count(:sys.get_state(pid).table, [{{{:slot, :_, :_}, :_, :_}, [], [true]}]) ==
             0
  end

  test "K07b header/body/drip stalls use one absolute deadline and close clients", ctx do
    probe = start_supervised!(MixerHosted.Identity.SocketProbe)
    parts = ["HTTP/1.1 200 OK\r\n", TLSFixture.response(ctx.body) |> String.slice(0..-10//1)]

    for raw <- parts do
      TLSFixture.configure(ctx.fixture, {:raw, raw})
      start = System.monotonic_time(:millisecond)

      assert {:error, _} =
               JWKSTransport.fetch_fixture(@entry, ctx.ip, ctx.port, deadline(), [ctx.ca], probe)

      assert (System.monotonic_time(:millisecond) - start) in 1_900..2_300
    end

    TLSFixture.configure(
      ctx.fixture,
      {:drip, ["HTTP/1.1 200 OK\r\n", "Date: ", "Sat, ", "24 Oct "], 700}
    )

    start = System.monotonic_time(:millisecond)

    assert {:error, _} =
             JWKSTransport.fetch_fixture(@entry, ctx.ip, ctx.port, deadline(), [ctx.ca], probe)

    assert (System.monotonic_time(:millisecond) - start) in 1_900..2_300
  end

  test "K07c owner disable cancels active fetch and never installs late candidate", ctx do
    TLSFixture.configure(ctx.fixture, {:drip, ["HTTP/1.1 200 OK\r\n", ""], 1_000})
    {owner, pid} = start_owner(ctx)

    task =
      Task.async(fn -> ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now()) end)

    eventually(fn -> map_size(:sys.get_state(pid).flights) == 1 end)
    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, [put_in(@entry.profile.enabled, false)])
    assert {:error, :unauthenticated} = Task.await(task, 2_500)
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert :sys.get_state(pid).snapshots == %{}
  end

  test "K08 cold storm single flight, admission and FIFO negative cache", ctx do
    TLSFixture.configure(ctx.fixture, {:drip, ["", TLSFixture.response(ctx.body)], 100})
    {owner, pid} = start_owner(ctx)
    before = TLSFixture.info(ctx.fixture).accepted

    credential = token(ctx)

    results =
      1..100
      |> Task.async_stream(
        fn _ -> ConfiguredVerifier.authenticate(owner, "fixture", credential, now()) end,
        max_concurrency: 100,
        timeout: 3_000
      )
      |> Enum.map(fn {:ok, r} -> r end)

    assert Enum.any?(results, &match?({:ok, _}, &1))
    assert Enum.all?(results, &(match?({:ok, _}, &1) or &1 == {:error, :identity_unavailable}))
    assert TLSFixture.info(ctx.fixture).accepted - before == 1

    for i <- 1..140,
        do:
          assert(
            {:error, :unauthenticated} ==
              ConfiguredVerifier.authenticate(owner, "fixture", token(ctx, "unknown#{i}"), now())
          )

    s = :sys.get_state(pid)
    assert map_size(s.negatives["fixture"]) == 128
    refute Map.has_key?(s.negatives["fixture"], "unknown1")
    first = s.negatives["fixture"]["unknown140"]

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx, "unknown140"), now())

    assert :sys.get_state(pid).negatives["fixture"]["unknown140"] == first
    assert TLSFixture.info(ctx.fixture).accepted - before == 1

    [header, payload, _] = String.split(token(ctx), ".")

    forged =
      header <>
        "." <> payload <> "." <> Base.url_encode64(:crypto.strong_rand_bytes(256), padding: false)

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", forged, now())

    assert TLSFixture.info(ctx.fixture).accepted - before == 1

    permits =
      for _ <- 1..16 do
        {:ok, p} = Admission.acquire(owner, "fixture")
        p
      end

    assert {:error, :identity_unavailable} = Admission.acquire(owner, "fixture")
    Enum.each(permits, &Admission.release/1)
  end

  test "K08b eight configured profiles cannot open a fifth owned flight", ctx do
    TLSFixture.configure(ctx.fixture, :stall)
    entries = [@entry | for(i <- 1..7, do: put_in(@entry.profile.profile_id, "p#{i}"))]
    {owner, pid} = start_owner(ctx, TestKeyOwner, entries)

    tasks =
      for e <- entries,
          do:
            Task.async(fn ->
              ConfiguredVerifier.authenticate(owner, e.profile.profile_id, token(ctx), now())
            end)

    eventually(fn -> map_size(:sys.get_state(pid).flights) == 4 end)

    for _ <- 1..20 do
      assert map_size(:sys.get_state(pid).flights) <= 4
      Process.sleep(10)
    end

    assert Enum.all?(tasks, fn t -> Task.await(t, 2_500) == {:error, :identity_unavailable} end)
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert DynamicSupervisor.count_children(:sys.get_state(pid).workers).active == 0

    permits =
      for entry <- entries, _ <- 1..16 do
        {:ok, permit} = Admission.acquire(owner, entry.profile.profile_id)
        permit
      end

    assert length(permits) == 128
    assert {:error, :identity_unavailable} = Admission.acquire(owner, "fixture")
    Enum.each(permits, &Admission.release/1)
  end

  test "K07e slow handshake sockets close before flight admission can reuse slots", ctx do
    fixture = start_supervised!(MixerHosted.Identity.RawFixture)
    port = MixerHosted.Identity.RawFixture.info(fixture).port
    fixture_ctx = %{ctx | port: port}
    entries = [@entry | for(i <- 1..7, do: put_in(@entry.profile.profile_id, "p#{i}"))]
    {owner, pid} = start_owner(fixture_ctx, TestKeyOwner, entries)

    tasks =
      for e <- Enum.take(entries, 4),
          do:
            Task.async(fn ->
              ConfiguredVerifier.authenticate(owner, e.profile.profile_id, token(ctx), now())
            end)

    eventually(fn -> MixerHosted.Identity.RawFixture.info(fixture).accepted == 4 end)
    assert MixerHosted.Identity.RawFixture.info(fixture).max_active == 4
    ports = for {flight, _} <- :sys.get_state(pid).flights, do: :sys.get_state(flight).raw_socket
    assert length(ports) == 4 and Enum.all?(ports, &is_port/1)
    assert Enum.all?(tasks, fn t -> Task.await(t, 2_500) == {:error, :identity_unavailable} end)
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    # Local owned TCP port DOWN is authoritative; peer EOF observation can lag
    # due to scheduling. Require local closure before any new admission, then
    # collect the independently observed remote EOF before opening the next test.
    assert Enum.all?(ports, &(Port.info(&1) == nil))
    eventually(fn -> MixerHosted.Identity.RawFixture.info(fixture).closed == 4 end)
    closed_before_reuse = MixerHosted.Identity.RawFixture.info(fixture).closed
    next = Task.async(fn -> ConfiguredVerifier.authenticate(owner, "p4", token(ctx), now()) end)
    eventually(fn -> MixerHosted.Identity.RawFixture.info(fixture).accepted == 5 end)
    assert closed_before_reuse == 4
    assert MixerHosted.Identity.RawFixture.info(fixture).max_active <= 4
    assert {:error, :identity_unavailable} = Task.await(next, 2_500)
    eventually(fn -> MixerHosted.Identity.RawFixture.info(fixture).closed == 5 end)

    write_evidence(
      "handshake-cleanup.json",
      Jason.encode!(
        Map.merge(MixerHosted.Identity.RawFixture.info(fixture), %{
          closedBeforeReuse: closed_before_reuse,
          localPortsClosedBeforeReuse: true,
          scope:
            "actual TCP sink stalled TLS handshake, server-observed EOF before fifth admission"
        }),
        pretty: true
      )
    )
  end

  test "K07f delayed TLS handler cleanup holds all four slots until connection DOWN", ctx do
    raw = start_supervised!(MixerHosted.Identity.RawFixture)
    port = MixerHosted.Identity.RawFixture.info(raw).port
    entries = [@entry | for(i <- 1..4, do: put_in(@entry.profile.profile_id, "p#{i}"))]
    {owner, pid} = start_owner(%{ctx | port: port}, TestKeyOwner, entries)

    tasks =
      for e <- Enum.take(entries, 4),
          do:
            Task.async(fn ->
              ConfiguredVerifier.authenticate(owner, e.profile.profile_id, token(ctx), now())
            end)

    eventually(fn -> MixerHosted.Identity.RawFixture.info(raw).accepted == 4 end)

    eventually(fn ->
      Enum.all?(:sys.get_state(pid).flights, fn {flight, _} ->
        is_pid(:sys.get_state(flight).connection)
      end)
    end)

    flights = for {flight, _} <- :sys.get_state(pid).flights, do: :sys.get_state(flight)
    handlers = Enum.map(flights, & &1.connection)

    try do
      Enum.each(handlers, &:sys.suspend/1)
      Enum.each(flights, &Process.exit(&1.worker, :kill))
      eventually(fn -> Enum.all?(flights, &(Port.info(&1.raw_socket) == nil)) end)
      assert map_size(:sys.get_state(pid).flights) == 4

      assert {:error, :identity_unavailable} =
               ConfiguredVerifier.authenticate(owner, "p4", token(ctx), now())

      assert MixerHosted.Identity.RawFixture.info(raw).accepted == 4
      assert Enum.all?(handlers, &Process.alive?/1)
    after
      Enum.each(handlers, fn handler -> if Process.alive?(handler), do: :sys.resume(handler) end)
    end

    assert Enum.all?(tasks, fn task ->
             Task.await(task, 2_500) == {:error, :identity_unavailable}
           end)

    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert Enum.all?(handlers, &(not Process.alive?(&1)))
    eventually(fn -> MixerHosted.Identity.RawFixture.info(raw).closed == 4 end)
  end

  test "K07g owner shutdown waits for suspended TLS controller cleanup", ctx do
    raw = start_supervised!(MixerHosted.Identity.RawFixture)
    {owner, pid} = start_owner(%{ctx | port: MixerHosted.Identity.RawFixture.info(raw).port})

    task =
      Task.async(fn -> ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now()) end)

    eventually(fn -> MixerHosted.Identity.RawFixture.info(raw).accepted == 1 end)
    [{flight, _}] = Map.to_list(:sys.get_state(pid).flights)
    eventually(fn -> is_pid(:sys.get_state(flight).connection) end)
    f = :sys.get_state(flight)
    :sys.suspend(f.connection)
    stopped = Task.async(fn -> GenServer.stop(pid, :normal, :infinity) end)

    try do
      eventually(fn -> Port.info(f.raw_socket) == nil end)
      assert Task.yield(stopped, 50) == nil
      assert Process.alive?(f.connection)

      assert {:error, :identity_unavailable} =
               ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())
    after
      if Process.alive?(f.connection), do: :sys.resume(f.connection)
    end

    assert :ok = Task.await(stopped, 2_500)
    assert {:error, :identity_unavailable} = Task.await(task, 2_500)
    refute Process.alive?(f.connection)
    refute Process.alive?(f.worker)
    assert Port.info(f.raw_socket) == nil
  end

  test "K07h supervised owner crash cannot restart component before old controllers DOWN", ctx do
    raw = start_supervised!(MixerHosted.Identity.RawFixture)
    entries = [@entry | for(i <- 1..4, do: put_in(@entry.profile.profile_id, "p#{i}"))]
    owner = CrashKeyOwner
    workers = CrashKeyOwner.Workers

    options = [
      name: owner,
      manifest: entries,
      generation: 1,
      binding: "fixture",
      ca_roots: [ctx.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: workers,
      fixture: %{ip: ctx.ip, port: MixerHosted.Identity.RawFixture.info(raw).port}
    ]

    start_supervised!({MixerHosted.Identity.ComponentFixture, options})
    old = Process.whereis(owner)

    tasks =
      for entry <- Enum.take(entries, 4),
          do:
            Task.async(fn ->
              ConfiguredVerifier.authenticate(owner, entry.profile.profile_id, token(ctx), now())
            end)

    eventually(fn -> MixerHosted.Identity.RawFixture.info(raw).accepted == 4 end)

    eventually(fn ->
      Enum.all?(:sys.get_state(old).flights, fn {flight, _} ->
        is_pid(:sys.get_state(flight).connection)
      end)
    end)

    flights = for {flight, _} <- :sys.get_state(old).flights, do: :sys.get_state(flight)
    handlers = Enum.map(flights, & &1.connection)
    Enum.each(handlers, &:sys.suspend/1)
    Process.exit(old, :kill)

    try do
      eventually(fn -> Enum.all?(flights, &(Port.info(&1.raw_socket) == nil)) end)
      Process.sleep(50)
      assert Process.whereis(owner) == nil
      assert Enum.all?(handlers, &Process.alive?/1)

      assert {:error, :identity_unavailable} =
               ConfiguredVerifier.authenticate(owner, "p4", token(ctx), now())

      assert MixerHosted.Identity.RawFixture.info(raw).accepted == 4
    after
      Enum.each(handlers, fn handler -> if Process.alive?(handler), do: :sys.resume(handler) end)
    end

    eventually(fn -> is_pid(Process.whereis(owner)) and Process.whereis(owner) != old end)
    assert Enum.all?(handlers, &(not Process.alive?(&1)))
    assert Enum.all?(flights, &(not Process.alive?(&1.worker)))

    assert Enum.all?(tasks, fn task ->
             Task.await(task, 2_500) == {:error, :identity_unavailable}
           end)

    eventually(fn -> MixerHosted.Identity.RawFixture.info(raw).closed == 4 end)

    write_evidence(
      "crash-restart-cleanup.json",
      Jason.encode!(
        %{
          oldControllersDownBeforeRestart: true,
          oldWorkersDownBeforeRestart: true,
          oldRawPortsDownBeforeRestart: true,
          admissionDeniedDuringCleanup: true,
          connections: 4
        },
        pretty: true
      )
    )
  end

  test "K07d caller death and owner queue time retire slots within original deadline", ctx do
    TLSFixture.configure(ctx.fixture, :stall)
    {owner, pid} = start_owner(ctx)
    task = spawn(fn -> ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now()) end)
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 1 end)
    Process.exit(task, :kill)
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert :sys.get_state(pid).admitted == %{}
    :sys.replace_state(pid, fn s -> %{s | attempts: %{}} end)
    :sys.suspend(pid)
    parent = self()
    start = System.monotonic_time(:millisecond)

    task =
      Task.async(fn ->
        send(parent, :started)
        ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())
      end)

    assert_receive :started
    Process.sleep(1_200)
    :sys.resume(pid)
    assert {:error, :identity_unavailable} = Task.await(task, 2_500)
    assert System.monotonic_time(:millisecond) - start < 2_350
  end

  test "K09 actual HTTPS rotation and invalid-candidate retention", ctx do
    {owner, pid} = start_owner(ctx)
    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())
    old = :sys.get_state(pid).snapshots["fixture"]

    :sys.replace_state(pid, fn s ->
      put_in(s.attempts["fixture"], System.monotonic_time(:millisecond) - 30_001)
    end)

    new = Map.put(ctx.public, "kid", "new")
    TLSFixture.configure(ctx.fixture, {:body, Jason.encode!(%{"keys" => [ctx.public, new]})})

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx, "new"), now())

    eventually(fn -> :sys.get_state(pid).snapshots["fixture"].generation != old.generation end)

    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())
    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx, "new"), now())
    {:ok, permit} = Admission.acquire(owner, "fixture")
    {:ok, lease} = KeyOwner.checkout(owner, permit, now())
    overlap = :sys.get_state(pid).snapshots["fixture"]

    :sys.replace_state(pid, fn state ->
      put_in(state.attempts["fixture"], System.monotonic_time(:millisecond) - 30_001)
    end)

    TLSFixture.configure(ctx.fixture, {:body, Jason.encode!(%{"keys" => [new]})})

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(
               owner,
               "fixture",
               token(ctx, "refresh-removal"),
               now()
             )

    eventually(fn ->
      :sys.get_state(pid).snapshots["fixture"].generation != overlap.generation
    end)

    assert {:error, :retry_current} = KeyOwner.finish(owner, lease)
    KeyOwner.release(owner, permit)

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx, "new"), now())
    original = :sys.get_state(pid).snapshots["fixture"]

    :sys.replace_state(pid, fn s ->
      put_in(s.attempts["fixture"], System.monotonic_time(:millisecond) - 30_001)
    end)

    TLSFixture.configure(ctx.fixture, {:body, Jason.encode!(%{"keys" => [new, new]})})

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx, "third"), now())

    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert :sys.get_state(pid).snapshots["fixture"] == original
  end

  test "K01b all-or-nothing versioned replacement and bounded churn tombstones", ctx do
    {owner, pid} = start_owner(ctx)

    entries =
      for i <- 0..7,
          do: put_in(@entry.profile.profile_id, if(i == 0, do: "fixture", else: "a#{i}"))

    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, entries)
    assert {:ok, 3} = KeyOwner.replace_manifest(owner, 2, [])
    replacement = for i <- 1..8, do: put_in(@entry.profile.profile_id, "b#{i}")
    assert {:ok, 4} = KeyOwner.replace_manifest(owner, 3, replacement)
    assert {:ok, 5} = KeyOwner.replace_manifest(owner, 4, [])
    assert map_size(:sys.get_state(pid).tombstones) == 16

    assert {:error, :invalid_manifest} =
             KeyOwner.replace_manifest(owner, 5, [put_in(@entry.profile.profile_id, "overflow")])

    assert :sys.get_state(pid).generation == 5
    assert map_size(:sys.get_state(pid).history) == 16
    original = :sys.get_state(pid).history
    :sys.replace_state(pid, fn state -> %{state | tombstones: %{}} end)

    assert {:error, :invalid_manifest} =
             KeyOwner.replace_manifest(owner, 5, [
               put_in(@entry.profile.profile_id, "seventeenth-after-expiry")
             ])

    assert :sys.get_state(pid).history == original
    assert :sys.get_state(pid).entries == %{}
    # Emergency disable/re-enable keeps cooldown even though a new version is cold.
    assert {:ok, 6} =
             KeyOwner.replace_manifest(owner, 5, [put_in(@entry.profile.profile_version, 2)])

    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(owner, 6, [@entry])
  end

  test "K08c remove re-add retains failure cooldown and rejects old immutable identity", ctx do
    TLSFixture.configure(ctx.fixture, {:raw, "HTTP/1.1 500 Rejected\r\n\r\n"})
    {owner, pid} = start_owner(ctx)
    before = TLSFixture.info(ctx.fixture).accepted

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    attempted = :sys.get_state(pid).attempts["fixture"]
    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, [])

    assert {:error, :invalid_manifest} =
             KeyOwner.replace_manifest(owner, 2, [
               put_in(@entry.profile.issuer, "https://other.invalid")
             ])

    assert {:ok, 3} =
             KeyOwner.replace_manifest(owner, 2, [put_in(@entry.profile.profile_version, 2)])

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert :sys.get_state(pid).attempts["fixture"] == attempted
    assert TLSFixture.info(ctx.fixture).accepted == before + 1
  end

  test "K01 lifetime identity history survives expired cooldown tombstones", ctx do
    {owner, pid} = start_owner(ctx)
    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, [])

    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(owner, 2, [@entry])

    :sys.replace_state(pid, fn state ->
      %{
        state
        | tombstones:
            Map.new(state.tombstones, fn {id, value} ->
              {id, %{value | expires: System.monotonic_time(:millisecond) - 1}}
            end),
          attempts: %{}
      }
    end)

    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(owner, 2, [@entry])

    for candidate <- [
          put_in(@entry.profile.issuer, "https://reinterpreted.invalid"),
          put_in(@entry.profile.client_id, "reinterpreted"),
          put_in(@entry.profile.identity_class, :service)
        ] do
      assert {:error, :invalid_manifest} =
               KeyOwner.replace_manifest(owner, 2, [put_in(candidate.profile.profile_version, 2)])
    end

    assert {:ok, 3} =
             KeyOwner.replace_manifest(owner, 2, [put_in(@entry.profile.profile_version, 2)])

    assert {:ok, 4} = KeyOwner.replace_manifest(owner, 3, [])
    :sys.replace_state(pid, fn state -> %{state | tombstones: %{}} end)
    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(owner, 4, [@entry])

    assert {:error, :invalid_manifest} =
             KeyOwner.replace_manifest(owner, 4, [put_in(@entry.profile.profile_version, 2)])

    assert {:ok, 5} =
             KeyOwner.replace_manifest(owner, 4, [put_in(@entry.profile.profile_version, 3)])

    history = :sys.get_state(pid).history
    assert map_size(history) == 1
    assert history["fixture"].entry.profile.profile_version == 3
    refute history["fixture"].retired
    bytes = byte_size(:erlang.term_to_binary(history))
    assert bytes < 10_000

    write_evidence(
      "history-metadata-size.json",
      Jason.encode!(
        %{
          exampleRecords: 1,
          externalTermBytes: bytes,
          maximumRecords: 16,
          maximumUnsharedConfiguredStringBytesPerRecord: 5_117,
          derivedMaximumStringBytesAllRecords: 81_872,
          containsKeysOrSnapshots: false
        },
        pretty: true
      )
    )
  end

  test "K10 serialized fence across disable removal and clock discontinuity", ctx do
    {owner, pid} = start_owner(ctx)
    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())
    {:ok, permit} = Admission.acquire(owner, "fixture")
    {:ok, lease} = KeyOwner.checkout(owner, permit, now())
    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, [put_in(@entry.profile.enabled, false)])
    assert {:error, :unauthenticated} = KeyOwner.finish(owner, lease)
    assert {:ok, 3} = KeyOwner.replace_manifest(owner, 2, [])
    assert {:error, :unauthenticated} = KeyOwner.finish(owner, lease)
    KeyOwner.release(owner, permit)

    :sys.replace_state(pid, fn s ->
      %{s | clock: {elem(s.clock, 0) + 10_000, elem(s.clock, 1)}}
    end)

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert :sys.get_state(pid).snapshots == %{}
  end

  test "K10b clock faults retire leases without changing reviewed manifest generation", ctx do
    {owner, pid} = start_owner(ctx)
    assert {:ok, _} = ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())
    {:ok, permit} = Admission.acquire(owner, "fixture")
    {:ok, lease} = KeyOwner.checkout(owner, permit, now())

    saved_history = :sys.get_state(pid).history

    :sys.replace_state(pid, fn s ->
      %{s | clock: {elem(s.clock, 0) + 10_000, elem(s.clock, 1)}}
    end)

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    assert :sys.get_state(pid).snapshots == %{}
    assert :sys.get_state(pid).history == saved_history
    send(pid, :reap)
    assert :sys.get_state(pid).history == saved_history
    assert :sys.get_state(pid).generation == 1
    assert :sys.get_state(pid).epoch != lease.epoch
    assert {:error, :retry_current} = KeyOwner.finish(owner, lease)
    assert {:ok, 2} = KeyOwner.replace_manifest(owner, 1, [put_in(@entry.profile.enabled, false)])

    assert {:error, :unauthenticated} =
             ConfiguredVerifier.authenticate(owner, "fixture", token(ctx), now())

    KeyOwner.release(owner, permit)
  end

  test "K11 production constructor rejects injection and missing roots", ctx do
    opts = [
      name: InvalidOwner,
      manifest: [@entry],
      generation: 1,
      binding: "fixture",
      ca_roots: [ctx.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: Unused
    ]

    Process.flag(:trap_exit, true)

    assert {:error, :invalid_identity_configuration} =
             KeyOwner.start_link(opts ++ [fixture: %{ip: ctx.ip, port: ctx.port}])

    assert {:error, :invalid_identity_configuration} =
             KeyOwner.start_link(Keyword.put(opts, :ca_roots, []))

    assert {:error, :identity_unavailable} =
             ConfiguredVerifier.authenticate(AbsentOwner, "fixture", token(ctx), now())
  end

  defp eventually(fun, n \\ 100)
  defp eventually(fun, 0), do: assert(fun.())

  defp eventually(fun, n),
    do:
      if(fun.(),
        do: :ok,
        else:
          (
            Process.sleep(10)
            eventually(fun, n - 1)
          )
      )
end
