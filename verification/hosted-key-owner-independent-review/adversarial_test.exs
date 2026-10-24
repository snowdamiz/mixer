defmodule MixerHosted.Identity.IndependentAdapterOwner do
  use GenServer
  alias MixerHosted.Identity.{Admission, KeyOwner}
  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, name: opts.name)
  def init(opts) do
    table = Admission.new(opts.name, %{"independent" => opts.entry}, "independent")
    {:ok, Map.merge(opts, %{table: table, checkouts: 0, finishes: 0})}
  end
  def handle_call({:checkout, permit, _}, _, s) do
    lease = %KeyOwner.Lease{epoch: :epoch, generation: s.checkouts, id: "independent",
      snapshot_generation: :snapshot, snapshot: s.snapshot, permit: permit}
    {:reply, {:ok, lease}, %{s | checkouts: s.checkouts + 1}}
  end
  def handle_call({:finish, _}, _, s) do
    n = s.finishes + 1
    result = if s.mode == :one_race and n > 1, do: :ok, else: {:error, :retry_current}
    {:reply, result, %{s | finishes: n}}
  end
  def handle_call({:release, _}, _, s), do: {:reply, :ok, s}
  def terminate(_, s), do: Admission.close(s.name)
end

defmodule MixerHosted.Identity.IndependentAdversarialTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Identity.{Admission, BoundedTCP, ConfiguredVerifier, DNSFixture, DNSResolver,
    HTTPFreshness, HTTPWireGuard, JWKSTransport, KeyOwner, Manifest, TLSFixture, TrustSnapshot}
  @profile %{profile_id: "independent", profile_version: 1, issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api", client_id: "reviewed-client", identity_class: :human, enabled: true}
  @entry %{profile: @profile, jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"}, transport: :hosted_https}

  setup_all do
    Application.ensure_all_started(:jose)
    Application.ensure_all_started(:mint)
    fixture = start_supervised!(TLSFixture)
    authority = GenServer.call(fixture, :authority)
    key = JOSE.JWK.generate_key({:rsa, 2048})
    public = key |> JOSE.JWK.to_public() |> JOSE.JWK.to_map() |> elem(1) |> Map.merge(%{"kid" => "key1", "alg" => "RS256", "use" => "sig"})
    body = Jason.encode!(%{"keys" => [public]})
    {:ok, snapshot} = TrustSnapshot.new(@profile, body, now(), now() + 120)
    {:ok, Map.merge(authority, %{fixture: fixture, key: key, body: body, snapshot: snapshot})}
  end
  setup ctx do
    TLSFixture.configure(ctx.fixture, {:body, ctx.body})
    :ok
  end
  defp now, do: System.system_time(:second)
  defp deadline, do: System.monotonic_time(:millisecond) + 2_000
  defp token(ctx, changes \\ %{}, kid \\ "key1") do
    claims = Map.merge(%{"iss" => @profile.issuer, "aud" => @profile.audience, "sub" => "independent-subject",
      "client_id" => @profile.client_id, "iat" => now() - 1, "exp" => now() + 120, "jti" => "independent-credential"}, changes)
    JOSE.JWS.sign(ctx.key, Jason.encode!(claims), %{"alg" => "RS256", "typ" => "at+jwt", "kid" => kid}) |> JOSE.JWS.compact() |> elem(1)
  end
  defp owner(ctx) do
    name = IndependentActualOwner
    workers = IndependentActualOwner.Workers
    start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: workers}, id: workers)
    {:ok, pid} = KeyOwner.start_fixture(name: name, manifest: [@entry], generation: 1, binding: "independent",
      ca_roots: [ctx.ca], resolvers: [{{127,0,0,1},9}], worker_supervisor: workers, fixture: Map.take(ctx, [:ip, :port]))
    on_exit(fn -> if Process.alive?(pid), do: GenServer.stop(pid) end)
    {name, pid}
  end
  defp fetch(ctx), do: JWKSTransport.fetch_fixture(@entry, ctx.ip, ctx.port, deadline(), [ctx.ca], nil)

  test "I01 endpoint validation rejects aliases, textual IP forms and path authority escapes" do
    for host <- ["127.1", "2130706433", "0177.0.0.1", "0x7f000001", "[::1]", "::ffff:127.0.0.1", "JWKS.fixture.invalid", "jwks.fixture.invalid.", "-host.invalid", "a..invalid", "user@host.invalid", "a_1.invalid", "a/b.invalid", "é.invalid"] do
      assert {:error, :invalid_manifest} = Manifest.validate([put_in(@entry.jwks_endpoint.host, host)]), host
    end
    for path <- ["keys", "/%2e%2e/keys", "/./keys", "/a/../keys", "/keys?x=1", "/keys#x", "/a\\b", "/kéys", "/keys\r\nHost:x"] do
      assert {:error, :invalid_manifest} = Manifest.validate([put_in(@entry.jwks_endpoint.path, path)]), path
    end
    assert {:error, :invalid_manifest} = Manifest.validate([put_in(@entry.jwks_endpoint.port, 8443)])
    assert {:ok, _} = Manifest.validate([put_in(@entry.jwks_endpoint.path, "//keys")])
  end

  test "I02 adapter retries exactly once and fails closed on a second final-fence race", ctx do
    for {name, mode, expected} <- [{IndependentRetryOne, :one_race, :ok}, {IndependentRetryTwo, :always_race, :error}] do
      pid = start_supervised!({MixerHosted.Identity.IndependentAdapterOwner, %{name: name, mode: mode, entry: @entry, snapshot: ctx.snapshot}}, id: name)
      result = ConfiguredVerifier.authenticate(name, "independent", token(ctx), now())
      if expected == :ok, do: assert(match?({:ok, _}, result)), else: assert(result == {:error, :identity_unavailable})
      assert %{checkouts: 2, finishes: 2} = :sys.get_state(pid)
      assert :ets.info(:sys.get_state(pid).table, :size) == 1
    end
  end

  test "I03 actual lease rejects changed generation, forged permit and disabled binding", ctx do
    {name, _} = owner(ctx)
    assert {:ok, _} = ConfiguredVerifier.authenticate(name, "independent", token(ctx), now())
    {:ok, permit} = Admission.acquire(name, "independent")
    try do
      {:ok, lease} = KeyOwner.checkout(name, permit, now())
      assert :ok = KeyOwner.finish(name, lease)
      assert {:ok, 2} = KeyOwner.replace_manifest(name, 1, [@entry])
      assert {:error, :retry_current} = KeyOwner.finish(name, lease)
      {:ok, current} = KeyOwner.checkout(name, permit, now())
      assert :ok = KeyOwner.finish(name, current)
      assert {:error, :identity_unavailable} = KeyOwner.finish(name, %{current | permit: put_elem(permit, 6, make_ref())})
      assert {:ok, 3} = KeyOwner.replace_manifest(name, 2, [put_in(@entry.profile.enabled, false)])
      assert {:error, :unauthenticated} = KeyOwner.finish(name, current)
      assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(name, 3, [@entry])
      assert {:ok, 4} = KeyOwner.replace_manifest(name, 3, [put_in(@entry.profile.profile_version, 2)])
      assert {:error, :retry_current} = KeyOwner.finish(name, current)
    after
      KeyOwner.release(name, permit)
      Admission.release(permit)
    end
  end

  test "I04 expired tombstone and clock epoch cannot erase identity history or permit partial replacement", ctx do
    {name, pid} = owner(ctx)
    assert {:ok, 2} = KeyOwner.replace_manifest(name, 1, [])
    :sys.replace_state(pid, fn s -> %{s | tombstones: Map.new(s.tombstones, fn {id,t} -> {id, %{t | expires: System.monotonic_time(:millisecond)-1}} end), clock: {elem(s.clock,0)+10_000, elem(s.clock,1)}} end)
    before = :sys.get_state(pid)
    invalid = put_in(@entry.profile.client_id, "foreign-client") |> put_in([:profile,:profile_version], 2)
    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(name, 2, [put_in(@entry.profile.profile_id, "new"), invalid])
    after_state = :sys.get_state(pid)
    assert after_state.history == before.history
    assert after_state.entries == before.entries
    assert after_state.generation == 2
    assert after_state.epoch != before.epoch
    assert {:error, :invalid_manifest} = KeyOwner.replace_manifest(name, 2, [@entry])
    assert {:ok, 3} = KeyOwner.replace_manifest(name, 2, [put_in(@entry.profile.profile_version, 2)])
  end

  test "I05 frozen header-only refresh observation remains bounded and denies foreign issuer", ctx do
    {name, pid} = owner(ctx)
    assert {:ok, _} = ConfiguredVerifier.authenticate(name, "independent", token(ctx), now())
    assert {:error, :unauthenticated} = ConfiguredVerifier.authenticate(name, "independent", token(ctx, %{"iss" => "https://foreign.invalid"}, "foreign-kid"), now())
    s = :sys.get_state(pid)
    assert Map.has_key?(s.negatives["independent"], "foreign-kid")
    assert map_size(s.negatives["independent"]) == 1
    assert map_size(s.flights) == 0
    TLSFixture.configure(ctx.fixture, {:barrier, self(), TLSFixture.response(ctx.body)})
    :sys.replace_state(pid, fn s -> %{s | attempts: %{"independent" => System.monotonic_time(:millisecond)-30_001}} end)
    assert {:error, :unauthenticated} = ConfiguredVerifier.authenticate(name, "independent", token(ctx, %{"iss" => "https://foreign.invalid"}, "foreign-eligible"), now())
    assert_receive {:tls_response_ready, handler}, 1_000
    for i <- 1..130 do
      assert {:error, :unauthenticated} = ConfiguredVerifier.authenticate(name, "independent", token(ctx, %{"iss" => "https://foreign.invalid"}, "miss-#{i}"), now())
    end
    s = :sys.get_state(pid)
    assert map_size(s.flights) == 1
    assert map_size(s.negatives["independent"]) == 128
    refute Map.has_key?(s.negatives["independent"], "miss-1")
    preserved = s.negatives["independent"]["miss-130"]
    assert {:error, :unauthenticated} = ConfiguredVerifier.authenticate(name, "independent", token(ctx, %{}, "miss-130"), now())
    assert :sys.get_state(pid).negatives["independent"]["miss-130"] == preserved
    before = :sys.get_state(pid)
    assert {:error, :unauthenticated} = ConfiguredVerifier.authenticate(name, "independent", token(ctx, %{"iss" => "https://foreign.invalid"}), now())
    [_,payload,signature] = String.split(token(ctx),".")
    invalid_header = Base.url_encode64(Jason.encode!(%{"alg" => "HS256", "typ" => "at+jwt", "kid" => "invalid-header"}),padding: false)
    assert {:error, :unauthenticated} = ConfiguredVerifier.authenticate(name, "independent", invalid_header <> "." <> payload <> "." <> signature, now())
    assert {:error, :identity_unavailable} = ConfiguredVerifier.authenticate(name, "unknown-profile", token(ctx), now())
    after_controls = :sys.get_state(pid)
    assert after_controls.negatives == before.negatives
    assert after_controls.attempts == before.attempts
    assert after_controls.flights == before.flights
    send(handler,:release_response)
    eventually(fn -> map_size(:sys.get_state(pid).flights) == 0 end)
    assert :sys.get_state(pid).negatives == %{}
    IO.puts("I05 foreign issuer: unauthenticated; one eligible configured flight; 128 FIFO negatives; hit expiry unchanged; invalid-header, known-key foreign claims and unknown-profile controls unchanged; replacement cleared negatives")
  end

  test "I06 actual resolver accepts exactly eight CNAME hops and rejects the ninth and cross-family mixed answers" do
    dns = start_supervised!(DNSFixture)
    %{port: port} = DNSFixture.info(dns)
    resolvers = [{{127,0,0,1},port}]
    DNSFixture.configure(dns, {:chain, 7, false})
    assert {:ok, {8,8,8,8}} = DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())
    DNSFixture.configure(dns, {:chain, 8, false})
    assert {:error, :dns_rejected} = DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())
    DNSFixture.configure(dns, {:addresses, [{8,8,8,8}, {0,0,0,0,0,0xffff,0x7f00,1}]})
    assert {:error, :dns_rejected} = DNSResolver.resolve("jwks.fixture.invalid", resolvers, deadline())
  end

  test "I07 exact TLS path requires Mint and wire guard to agree on hostile chunk syntax", ctx do
    date = :httpd_util.rfc1123_date() |> List.to_string()
    head = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nDate: #{date}\r\nCache-Control: max-age=120\r\n\r\n"
    for suffix <- ["1;x=\r\na\r\n0\r\n\r\n", "1;x=\"unfinished\r\na\r\n0\r\n\r\n", "1;x=\0\r\na\r\n0\r\n\r\n", "1\r\na\r\n0\r\nX-Key: new\r\n\r\n"] do
      TLSFixture.configure(ctx.fixture, {:raw, head <> suffix})
      assert {:error, _} = fetch(ctx), inspect(suffix)
    end
  end

  test "I08 non-ASCII header whitespace rejects while ordinary OWS succeeds", ctx do
    valid = TLSFixture.response(ctx.body)
    for marker <- ["\u00a0", "\u2003", "\u0085", "\v", "\f"] do
      raw = String.replace(valid, "Content-Type: ", "Content-Type: " <> marker)
      TLSFixture.configure(ctx.fixture, {:raw, raw})
      assert {:error, _} = fetch(ctx), inspect(marker)
    end
    TLSFixture.configure(ctx.fixture, {:raw, String.replace(valid, "Content-Type: ", "Content-Type:\t ")})
    assert {:ok, %{body: body}} = fetch(ctx)
    assert body == ctx.body
  end

  test "I09 freshness never grows from positive Age response delay shorter Expires or wall reversal" do
    wall = div(System.system_time(:millisecond), 1_000)*1_000
    date = fn delta -> DateTime.from_unix!(div(wall,1_000)+delta) |> Calendar.strftime("%a, %d %b %Y %H:%M:%S GMT") end
    h = %{"date" => date.(0), "cache-control" => "max-age=300, s-maxage=90", "age" => "10", "expires" => date.(60)}
    assert {:ok, a} = HTTPFreshness.calculate(h, {wall,1_000}, {wall+1_001,2_001})
    assert a.expires_mono == 50_001
    assert a.fresh_until-a.fetched_at == 48
    assert {:error, :freshness_rejected} = HTTPFreshness.calculate(h, {wall,1_000}, {wall-1_001,1_001})
    for value <- ["max-age=120, MAX-AGE=90", "max-age=120, no-cache=\"set-cookie\"", "max-age=\"120\"", "s-maxage=120", "max-age=1"] do
      assert {:error, :freshness_rejected} = HTTPFreshness.calculate(h |> Map.delete("expires") |> Map.put("cache-control",value), {wall,1_000}, {wall+2_000,3_000})
    end
  end

  test "I10 real raw port is registered before use and every activation remains capped" do
    {:ok, listener} = :gen_tcp.listen(0, [:binary, ip: {127,0,0,1}, active: false])
    {:ok, {_,port}} = :inet.sockname(listener)
    parent = self()
    acceptor = spawn(fn -> {:ok, s} = :gen_tcp.accept(listener); send(parent, {:accepted,s}); receive do :stop -> :gen_tcp.close(s) end end)
    watcher = spawn(fn -> receive do {:register_raw_socket, worker, raw, ref} -> send(parent, {:registered, Port.info(raw,:connected)}); send(worker,{ref,:ok}) end end)
    try do
      BoundedTCP.with_watchdog(watcher, deadline(), fn ->
        {:ok, socket} = BoundedTCP.connect({127,0,0,1}, port, [:binary, active: 32767, buffer: 99_999], 1_000)
        assert_receive {:registered, {:connected, worker}}
        assert worker == self()
        assert :ok = BoundedTCP.setopts(socket, active: 32767)
        assert {:ok,[active: 1, buffer: 16_384]} = :inet.getopts(socket, [:active,:buffer])
        assert :ok = BoundedTCP.setopts(socket, buffer: 99_999, packet: 0)
        assert {:ok,[active: 1, buffer: 16_384]} = :inet.getopts(socket, [:active,:buffer])
        assert {:error,:einval} = BoundedTCP.setopts(socket, active: true)
        assert Port.info(socket) == nil
      end)
    after
      :gen_tcp.close(listener)
      send(acceptor,:stop)
      Process.exit(watcher,:kill)
    end
  end

  test "I11 isolated guard bounds every split point and accepts only its exact completed body" do
    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
    for i <- 0..byte_size(response) do
      {a,b} = :erlang.split_binary(response,i)
      assert {:ok,s} = HTTPWireGuard.feed(HTTPWireGuard.new(),a)
      assert {:ok,%{done: true, body_bytes: 2} = complete} = HTTPWireGuard.feed(s,b)
      assert {:error,:extra_response} = HTTPWireGuard.feed(complete,"x")
    end
    assert {:error,_} = HTTPWireGuard.feed(HTTPWireGuard.new(),String.replace(response,"Content-Length: 2","Content-Length: 2\r\ncontent-length: 2"))
  end

  test "I12 graceful supervisor shutdown keeps its held TLS controller beyond the ordinary five-second window", ctx do
    raw = start_supervised!(MixerHosted.Identity.RawFixture)
    name = IndependentShutdownOwner
    workers = IndependentShutdownOwner.Workers
    options = [name: name, manifest: [@entry], generation: 1, binding: "independent", ca_roots: [ctx.ca],
      resolvers: [{{127,0,0,1},9}], worker_supervisor: workers,
      fixture: %{ip: ctx.ip, port: MixerHosted.Identity.RawFixture.info(raw).port}]
    component = start_supervised!({MixerHosted.Identity.ComponentFixture, options})
    auth = Task.async(fn -> ConfiguredVerifier.authenticate(name,"independent",token(ctx),now()) end)
    eventually(fn -> map_size(:sys.get_state(name).flights) == 1 end)
    [{flight,_}] = Map.to_list(:sys.get_state(name).flights)
    eventually(fn -> is_pid(:sys.get_state(flight).connection) end)
    f = :sys.get_state(flight)
    :sys.suspend(f.connection)
    stopped = Task.async(fn -> Supervisor.stop(component,:normal,:infinity) end)
    try do
      eventually(fn -> Port.info(f.raw_socket) == nil and not Process.alive?(f.worker) end)
      Process.sleep(5_100)
      assert Process.alive?(component)
      assert Process.alive?(flight)
      assert Process.alive?(f.connection)
      assert Task.yield(stopped,0) == nil
      assert {:error,:identity_unavailable} = ConfiguredVerifier.authenticate(name,"independent",token(ctx),now())
    after
      if Process.alive?(f.connection), do: :sys.resume(f.connection)
    end
    assert :ok = Task.await(stopped,2_500)
    assert {:error,:identity_unavailable} = Task.await(auth,2_500)
    refute Process.alive?(f.connection)
    refute Process.alive?(flight)
    assert Port.info(f.raw_socket) == nil
    IO.puts("I12 graceful shutdown held more than 5100 ms after raw-port/worker cleanup, then completed only after controller DOWN; forced process/container termination remains outside this guarantee")
  end
  defp eventually(fun, n \\ 100)
  defp eventually(fun, 0), do: assert(fun.())
  defp eventually(fun, n), do: if(fun.(), do: :ok, else: (Process.sleep(10); eventually(fun,n-1)))
end
