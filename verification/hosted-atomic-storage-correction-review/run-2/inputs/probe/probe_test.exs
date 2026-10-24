ExUnit.start(autorun: false, seed: 0, max_cases: 1, timeout: 15_000, trace: true)
alias MixerAtomicStoragePreflight.{Repo, OtherRepo, AdminRepo, ProxyRepo}
{:ok, _} = Agent.start_link(fn -> %{} end, name: PreflightObservations)

config = [
  socket_dir: System.fetch_env!("MXAS_SOCKET"),
  username: "mxas_runtime",
  database: "atomic_preflight",
  pool_size: 1,
  timeout: 5_000,
  connect_timeout: 2_000,
  log: false
]

{:ok, _} = Repo.start_link(config)
{:ok, _} = OtherRepo.start_link(config)
{:ok, _} = AdminRepo.start_link(Keyword.put(config, :username, "preflight_owner"))

{:ok, proxy_pid} =
  ProxyRepo.start_link(Keyword.put(config, :socket_dir, System.fetch_env!("MXAS_PROXY")))

Process.unlink(proxy_pid)

defmodule MixerAtomicStoragePreflight.ReviewRaw do
  def query!(_ctx, sql, params), do: MixerAtomicStoragePreflight.Repo.query!(sql, params, log: false)
end

defmodule MixerAtomicStoragePreflight.ProbeTest do
  use ExUnit.Case, async: false

  alias MixerAtomicStoragePreflight.{
    Repo,
    OtherRepo,
    AdminRepo,
    ProxyRepo,
    Context,
    OtherContext,
    ProxyContext,
    Codec,
    Blob
  }

  @one "00000000-0000-0000-0000-000000000001"
  @two "00000000-0000-0000-0000-000000000002"
  @request "00000000-0000-0000-0000-000000000030"
  defp sql(q, p \\ []), do: AdminRepo.query!(q, p, log: false)
  defp scalar(q, p \\ []), do: sql(q, p).rows |> hd() |> hd()
  defp observe(k, v), do: Agent.update(PreflightObservations, &Map.put(&1, k, v))

  defp opts(o \\ []) do
    canonical = Keyword.get(o, :canonical, <<0>>)
    payload = Keyword.get(o, :payload, <<1>>)

    defaults = [
      actor: @one,
      key: "k",
      runtime: <<0::256>>,
      canonical: canonical,
      manifest: :crypto.hash(:sha256, canonical),
      signed: "{}",
      signature: <<0::512>>,
      payload_hash: :crypto.hash(:sha256, payload),
      payload_size: byte_size(payload),
      app: "a",
      environment: "e",
      platform: "ios",
      body: "body",
      reason: "",
      source_ip: nil,
      asserted_display: nil,
      expires: 10000
    ]

    Keyword.merge(defaults, o)
  end

  defp bind(ctx, mod, o) do
    values = [
      o[:actor],
      o[:app],
      o[:environment],
      o[:platform],
      Codec.hex(o[:runtime]),
      Codec.hex(o[:manifest]),
      if(is_nil(o[:expires]), do: nil, else: to_string(o[:expires]))
    ]

    mod.query!(
      ctx,
      "SELECT set_config('mixer_atomic.actor',$1,true),set_config('mixer_atomic.app',$2,true),set_config('mixer_atomic.environment',$3,true),set_config('mixer_atomic.platform',$4,true),set_config('mixer_atomic.runtime',$5,true),set_config('mixer_atomic.manifest',$6,true),set_config('mixer_atomic.expires',$7,true),set_config('mixer_atomic.action','artifact.upload',true)",
      values
    )
  end

  defp upload(ctx, o, mod \\ Context) do
    if mod != MixerAtomicStoragePreflight.ReviewRaw do
      for {v, lo, hi} <- [{o[:expires], 0, 9_007_199_254_740_991}, {o[:payload_size], 1, 4_194_304}, {Keyword.get(o, :input_authenticated_at, ctx.authentication_completed_at), 0, 9_007_199_254_740_991}] do
        if not is_integer(v) or v < lo or v > hi, do: raise(ArgumentError, "trusted integer input")
      end
    end
    deadline =
      DateTime.add(
        DateTime.utc_now(),
        ctx.deadline_ms - System.monotonic_time(:millisecond),
        :millisecond
      )

    hash =
      Keyword.get(
        o,
        :request_hash,
        :crypto.hash(:sha256, "POST /v3/private/artifacts" <> <<0>> <> o[:body])
      )

    args = [
      Keyword.get(o, :sql_backend, ctx.backend_pid),
      Keyword.get(o, :sql_xid, ctx.transaction_id),
      Keyword.get(o, :sql_database, ctx.database),
      Keyword.get(o, :runtime_role, ctx.db_role),
      Keyword.get(o, :nonce, ctx.nonce),
      Keyword.get(o, :deadline, deadline),
      Keyword.get(o, :input_actor, o[:actor]),
      if(is_nil(o[:expires]), do: nil, else: to_string(o[:expires])),
      o[:app],
      o[:environment],
      o[:platform],
      o[:runtime],
      o[:manifest],
      o[:canonical],
      o[:signed],
      o[:signature],
      o[:payload_hash],
      if(is_nil(o[:payload_size]), do: nil, else: to_string(o[:payload_size])),
      Keyword.get(o, :blob_ref, "sha256:" <> Codec.hex(o[:payload_hash])),
      o[:key],
      o[:body],
      hash,
      o[:reason],
      @request,
      o[:source_ip],
      o[:asserted_display],
      case Keyword.get(o, :input_authenticated_at, ctx.authentication_completed_at) do
        nil -> nil
        value -> to_string(value)
      end
    ]

    mod.query!(
      ctx,
      "SELECT x.* FROM mixer_hosted_release.upload_v1(ROW($1,$2,$3,$4,$5,$6,$7::text::uuid,$8::text::numeric,$27::text::numeric)::mixer_hosted_release.call_context,ROW('o','p',$9,$10,$11,$12,$13,$14,$15,$16,$17,$18::text::numeric,$19)::mixer_hosted_release.upload_input,ROW($20,'/v3/private/artifacts',$21,$22,$23,$24::text::uuid,$25,$26)::mixer_hosted_release.upload_request) AS x",
      args
    ).rows
    |> hd()
  end

  defp attempt(overrides \\ [], mod \\ Context) do
    o = opts(overrides)

    try do
      mod.enter(fn c ->
        bind(c, mod, o)
        upload(c, o, mod)
      end)
    rescue
      e -> {:rejected, inspect(e.__struct__), Exception.message(e)}
    end
  end

  defp counts do
    Enum.map(["artifacts", "audit_events", "idempotency"], fn t ->
      scalar("SELECT count(*) FROM mixer_hosted_release." <> t)
    end) ++ [scalar("SELECT last_event::text FROM mixer_hosted_release.tenant_heads")]
  end

  defp rejected(o, mod \\ Context) do
    assert {:rejected, _, _} = attempt(o, mod)
  end

  setup do
    sql(
      "TRUNCATE mixer_hosted_release.artifacts,mixer_hosted_release.audit_events,mixer_hosted_release.idempotency"
    )

    sql("UPDATE mixer_authz.fixture_policy SET role='developer',active=true,revision=1")
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    sql("UPDATE mixer_authz.fixture_fault SET boundary=''")

    sql(
      "UPDATE mixer_hosted_release.tenant_heads SET last_event=0,audit_hash=''::bytea,state_hash=mixer_hosted_release.hash_domain('mixer.hosted.state.v1',mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.t('o'),mixer_hosted_release.t('p')]))"
    )

    :ok
  end

  test "01 complete routine returns original bytes and runtime context survives definer transition" do
    assert {:ok, [201, body, id, false]} = attempt()
    assert Decimal.equal?(id, 1)

    assert body ==
             "{\"manifest_sha256\":\"" <>
               Codec.hex(:crypto.hash(:sha256, <<0>>)) <> "\",\"event_id\":\"1\"}"

    assert counts() == [1, 1, 1, "1"]
    assert {:ok, [201, ^body, ^id, true]} = attempt()
    assert counts() == [1, 1, 1, "1"]

    observe("legitimate_definer_transition", %{
      runtime: "mxas_runtime",
      writer: "mxas_writer",
      same_backend_xid_nonce: true,
      context_revalidated_after: true
    })
  end

  test "02 runtime direct INSERT UPDATE DELETE TRUNCATE all private domain tables denied" do
    for table <- ~w(artifacts audit_events idempotency tenant_heads),
        verb <- [
          "INSERT INTO #{table} DEFAULT VALUES",
          "UPDATE #{table} SET organization=organization",
          "DELETE FROM #{table}",
          "TRUNCATE #{table}"
        ] do
      statement = String.replace(verb, table, "mixer_hosted_release." <> table)
      assert_raise Postgrex.Error, fn -> Repo.query!(statement) end
    end

    assert counts() == [0, 0, 0, "0"]
  end

  test "03 FORCE RLS manifest exact safe roles and no owner resolver writer SET ROLE paths" do
    assert scalar(
             "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity"
           ) == 7

    assert sql(
             "SELECT rolname,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,rolcanlogin FROM pg_roles WHERE rolname LIKE 'mxas_%' ORDER BY rolname"
           ).rows
           |> Enum.all?(fn [_n, s, b, c, d, r, _l] -> not (s or b or c or d or r) end)

    for role <- ~w(mxas_schema mxas_resolver mxas_writer) do
      assert scalar("SELECT pg_has_role('mxas_runtime',$1,'MEMBER')", [role]) == false
      assert_raise Postgrex.Error, fn -> Repo.query!("SET ROLE " <> role) end
    end

    assert scalar("SELECT has_database_privilege('mxas_runtime',current_database(),'TEMP')") ==
             false

    assert scalar("SELECT has_schema_privilege('mxas_runtime','mixer_hosted_release','CREATE')") ==
             false

    assert scalar(
             "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') AND p.prosecdef"
           ) == 3

    assert Repo.query!("SELECT count(*) FROM mixer_hosted_release.artifacts").rows == [[0]]
    assert_raise Postgrex.Error, fn -> Repo.query!("SELECT * FROM mixer_authz.fixture_policy") end

    assert_raise Postgrex.Error, fn ->
      Repo.query!("SELECT * FROM mixer_hosted_release.idempotency")
    end
  end

  test "38 runtime has no other role memberships ownership or session authorization escape" do
    assert scalar(
             "SELECT count(*) FROM pg_roles WHERE rolname<>'mxas_runtime' AND pg_has_role('mxas_runtime',oid,'MEMBER')"
           ) == 0

    assert scalar("SELECT count(*) FROM pg_class WHERE relowner='mxas_runtime'::regrole") == 0
    assert scalar("SELECT count(*) FROM pg_proc WHERE proowner='mxas_runtime'::regrole") == 0
    assert scalar("SELECT count(*) FROM pg_namespace WHERE nspowner='mxas_runtime'::regrole") == 0
    assert scalar("SELECT count(*) FROM pg_database WHERE datdba='mxas_runtime'::regrole") == 0
    assert scalar("SELECT count(*) FROM pg_proc WHERE proowner='mxas_writer'::regrole") == 1
    assert scalar("SELECT pg_has_role('mxas_writer','mxas_schema','MEMBER')") == false
    assert_raise Postgrex.Error, fn -> Repo.query!("SET SESSION AUTHORIZATION mxas_schema") end

    catalog =
      sql(
        "SELECT n.nspname,p.proname,r.rolname,p.prosecdef,p.proconfig,p.proacl::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') ORDER BY n.nspname,p.proname"
      ).rows

    policies =
      sql(
        "SELECT schemaname,tablename,policyname,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname IN ('mixer_authz','mixer_hosted_release') ORDER BY schemaname,tablename,policyname"
      ).rows

    observe("catalog_manifest", %{
      functions: catalog,
      policies: policies,
      unreachable_other_runtime_roles: true
    })
  end

  test "04 forged actor rejects before any writes" do
    rejected(input_actor: @two)
    assert counts() == [0, 0, 0, "0"]
  end

  test "05 wrong signed target rejects" do
    o = opts()

    assert_raise Postgrex.Error, fn ->
      Context.enter(fn c ->
        bind(c, Context, o)
        upload(c, Keyword.put(o, :app, "other"))
      end)
    end

    assert counts() == [0, 0, 0, "0"]
  end

  test "06 wrong request hash rejects" do
    rejected(request_hash: <<0::256>>)
    assert counts() == [0, 0, 0, "0"]
  end

  test "07 asserted wrong audit display rejects" do
    rejected(asserted_display: %{"hash" => "forged"})
    assert counts() == [0, 0, 0, "0"]
  end

  test "08 wrong nonce runtime role backend fullxid database and stale transaction deny" do
    rejected(nonce: String.duplicate("f", 64))
    rejected(runtime_role: "mxas_writer")
    rejected(sql_backend: -1)
    rejected(sql_xid: "1")
    rejected(sql_database: "other")

    for {field, value} <- [backend_pid: -1, transaction_id: "1", database: "other"] do
      o = opts()

      assert_raise MixerAtomicStoragePreflight.Rejected, fn ->
        Context.enter(fn c ->
          bind(c, Context, o)
          upload(Map.put(c, field, value), o)
        end)
      end
    end

    assert {:ok, closed} = Context.enter(& &1)
    assert_raise MixerAtomicStoragePreflight.Rejected, fn -> upload(closed, opts()) end
    assert counts() == [0, 0, 0, "0"]
  end

  test "09 foreign session denied even when deliberately granted fixture EXECUTE" do
    {:ok, conn} =
      Postgrex.start_link(
        socket_dir: System.fetch_env!("MXAS_SOCKET"),
        username: "mxas_foreign",
        database: "atomic_preflight"
      )

    assert_raise Postgrex.Error, fn ->
      Postgrex.query!(conn, "SELECT mixer_hosted_release.upload_v1(NULL,NULL,NULL)", [])
    end

    GenServer.stop(conn)
  end

  test "10 current authorization before idempotent cached result" do
    assert {:ok, _} = attempt()

    sql(
      "UPDATE mixer_authz.fixture_policy SET active=false,revision=2 WHERE actor=$1::text::uuid",
      [@one]
    )

    rejected([])
    assert counts() == [1, 1, 1, "1"]
  end

  test "11 expiry before idempotency rejects even identical original key" do
    assert {:ok, _} = attempt(expires: 101)
    sql("UPDATE mixer_authz.fixture_clock SET now_s=101")
    rejected(expires: 101)
    assert counts() == [1, 1, 1, "1"]
  end

  test "12 principal action target and hash conflicts do not disclose cached bytes" do
    assert {:ok, _} = attempt()
    rejected(actor: @two)
    rejected(body: "different")
    sql("UPDATE mixer_hosted_release.idempotency SET action='release.publish'")
    rejected([])
    sql("UPDATE mixer_hosted_release.idempotency SET action='artifact.upload',target='00'::bytea")
    rejected([])
    assert counts() == [1, 1, 1, "1"]
  end

  test "13 new key identical artifact audits success with no state delta" do
    assert {:ok, _} = attempt()
    first = scalar("SELECT state_hash FROM mixer_hosted_release.tenant_heads")
    assert {:ok, [200, _, _, false]} = attempt(key: "new")
    assert counts() == [1, 2, 2, "2"]
    assert scalar("SELECT state_hash FROM mixer_hosted_release.tenant_heads") == first

    assert scalar(
             "SELECT previous_state=current_state FROM mixer_hosted_release.audit_events WHERE event_id=2"
           )
  end

  test "14 immutable conflict cannot append a success" do
    assert {:ok, _} = attempt()
    rejected(key: "new", signed: "{ }")
    assert counts() == [1, 1, 1, "1"]
  end

  test "15 rollback after every persistence boundary has no partial event or id gap" do
    for boundary <- ~w(artifact audit idempotency head) do
      sql("UPDATE mixer_authz.fixture_fault SET boundary=$1", [boundary])
      rejected([])
      assert counts() == [0, 0, 0, "0"]
    end

    sql("UPDATE mixer_authz.fixture_fault SET boundary=''")
    assert {:ok, [201, _, id, false]} = attempt()
    assert Decimal.equal?(id, 1)
  end

  test "16 initial head event hash display and previous links corruption deny" do
    sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash='01'::bytea")
    rejected([])
    sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash=''::bytea")
    assert {:ok, _} = attempt()

    original =
      sql(
        "SELECT event_cbor,event_hash,previous_hash,display_json,display_bytes FROM mixer_hosted_release.audit_events"
      ).rows
      |> hd()

    for mutation <- [
          "event_cbor='01'::bytea",
          "event_hash='01'::bytea",
          "previous_hash='01'::bytea",
          "display_json=jsonb_set(display_json,'{action}','\"forged\"'),display_bytes=convert_to(jsonb_set(display_json,'{action}','\"forged\"')::text,'UTF8')",
          "display_bytes='01'::bytea"
        ] do
      sql("UPDATE mixer_hosted_release.audit_events SET " <> mutation)
      rejected(key: "new")

      sql(
        "UPDATE mixer_hosted_release.audit_events SET event_cbor=$1,event_hash=$2,previous_hash=$3,display_json=$4,display_bytes=$5",
        original
      )
    end

    assert counts() == [1, 1, 1, "1"]
  end

  test "17 concurrent same key different principals has one success and one hidden conflict" do
    parent = self()

    holder =
      Task.async(fn ->
        AdminRepo.transaction(fn ->
          sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE")
          send(parent, :locked)

          receive do
            :release -> :ok
          end
        end)
      end)

    assert_receive :locked

    a =
      Task.async(fn ->
        send(parent, :started)
        attempt([], Context)
      end)

    b =
      Task.async(fn ->
        send(parent, :started)
        attempt([actor: @two], OtherContext)
      end)

    assert_receive :started
    assert_receive :started
    Process.sleep(70)
    send(holder.pid, :release)
    Task.await(holder)
    results = [Task.await(a), Task.await(b)]
    assert Enum.count(results, &match?({:ok, [201, _, _, false]}, &1)) == 1
    assert Enum.count(results, &match?({:rejected, _, _}, &1)) == 1
    assert counts() == [1, 1, 1, "1"]
    observe("different_principal_race", %{successes: 1, conflicts: 1, events: 1})
  end

  test "18 concurrent new keys identical artifact produce insert and unchanged success" do
    a = Task.async(fn -> attempt([key: "a"], Context) end)
    b = Task.async(fn -> attempt([key: "b"], OtherContext) end)
    results = [Task.await(a), Task.await(b)]

    assert Enum.sort(Enum.map(results, fn {:ok, [status, _, _, false]} -> status end)) == [
             200,
             201
           ]

    assert counts() == [1, 2, 2, "2"]

    assert scalar(
             "SELECT previous_state=current_state FROM mixer_hosted_release.audit_events WHERE event_id=2"
           )
  end

  test "19 lock timeout rolls back; postwait current policy revocation denies" do
    parent = self()

    holder =
      Task.async(fn ->
        AdminRepo.transaction(fn ->
          sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE")
          send(parent, :locked)

          receive do
            :release -> :ok
          after
            1000 -> :ok
          end
        end)
      end)

    assert_receive :locked
    start = System.monotonic_time(:millisecond)
    rejected([])
    elapsed = System.monotonic_time(:millisecond) - start
    assert elapsed >= 240 and elapsed < 1000
    send(holder.pid, :release)
    Task.await(holder)
    assert counts() == [0, 0, 0, "0"]
    observe("lock_timeout_ms", elapsed)
  end

  test "20 PostgreSQL commit acknowledgement dropped then database restart and exact retry" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "uncertain")
    {staged, reference} = Blob.stage(Blob.open(root), <<1>>)
    o = opts(blob_ref: reference)

    result =
      try do
        ProxyContext.enter(fn c ->
          bind(c, ProxyContext, o)
          r = upload(c, o, ProxyContext)
          File.write!(System.fetch_env!("MXAS_ARM"), "armed")
          r
        end)
      rescue
        e -> {:storage_unavailable, inspect(e.__struct__)}
      end

    assert match?({:storage_unavailable, _}, result) or result == {:error, :rollback}
    # Proxy drops only PostgreSQL's completed COMMIT reply; caller receives no success.
    assert counts() == [1, 1, 1, "1"]
    assert Blob.reconcile(staged, MapSet.new(), true) == staged
    assert Blob.read(Blob.open(root), reference) == <<1>>

    original =
      sql("SELECT status,response,event_id FROM mixer_hosted_release.idempotency").rows |> hd()

    {stop, 0} =
      System.cmd("pg_ctl", ["-D", System.fetch_env!("MXAS_PGDATA"), "stop", "-m", "fast", "-w"])

    {start, 0} =
      System.cmd("pg_ctl", [
        "-D",
        System.fetch_env!("MXAS_PGDATA"),
        "-l",
        System.fetch_env!("MXAS_PGLOG"),
        "-o",
        "-k #{System.fetch_env!("MXAS_SOCKET")} -c listen_addresses='' -c unix_socket_permissions=0700 -c max_connections=12 -c log_statement=none -c log_min_error_statement=panic",
        "start",
        "-w"
      ])

    Process.sleep(350)

    recovered =
      Enum.reduce_while(1..40, nil, fn _, _ ->
        case attempt() do
          {:ok, _} = success ->
            {:halt, success}

          {:rejected, "DBConnection.ConnectionError", _} ->
            Process.sleep(50)
            {:cont, nil}

          other ->
            {:halt, other}
        end
      end)

    assert {:ok, [status, body, event, true]} = recovered
    assert [status, body, event] == original
    assert Blob.read(Blob.open(root), reference) == <<1>>
    assert counts() == [1, 1, 1, "1"]

    observe("uncertain_commit_restart", %{
      client_result: inspect(result),
      stop_output: stop,
      start_output: start,
      exact_original_retry: true,
      no_duplicate_event: true
    })
  end

  test "21 six supported roles and closed supported actions only" do
    for {role, allowed} <- [
          {"owner", true},
          {"administrator", true},
          {"developer", true},
          {"release_manager", false},
          {"viewer", false},
          {"billing_manager", false},
          {"publisher", false}
        ] do
      sql("UPDATE mixer_authz.fixture_policy SET role=$1", [role])
      if allowed, do: assert(match?({:ok, _}, attempt(key: role))), else: rejected(key: role)
    end

    o = opts()

    assert_raise Postgrex.Error, fn ->
      Context.enter(fn c ->
        bind(c, Context, o)
        Context.query!(c, "SELECT set_config('mixer_atomic.action','release.publish',true)")
        upload(c, o)
      end)
    end
  end

  test "22 SQL and independent Elixir uint64 encoding hand vectors all widths" do
    for {n, h} <- [
          {0, "00"},
          {23, "17"},
          {24, "1818"},
          {255, "18ff"},
          {256, "190100"},
          {65535, "19ffff"},
          {65536, "1a00010000"},
          {4_294_967_295, "1affffffff"},
          {4_294_967_296, "1b0000000100000000"},
          {18_446_744_073_709_551_615, "1bffffffffffffffff"}
        ] do
      assert Codec.hex(Codec.encode(n)) == h

      assert scalar("SELECT encode(mixer_hosted_release.u($1::text::numeric),'hex')", [
               Integer.to_string(n)
             ]) == h
    end

    for n <- [-1, 18_446_744_073_709_551_616] do
      assert_raise ArgumentError, fn -> Codec.encode(n) end

      assert_raise Postgrex.Error, fn ->
        sql("SELECT mixer_hosted_release.u($1::text::numeric)", [Integer.to_string(n)])
      end
    end

    assert Codec.hex(Codec.encode([1, nil, Codec.b(<<>>), ""])) == "8401f64060"
  end

  test "23 every stored display field reconstructs identical audit bytes and standard hash" do
    assert {:ok, _} = attempt(reason: "line\n雪", source_ip: "127.0.0.1")

    [bytes, hash, d, display] =
      sql(
        "SELECT event_cbor,event_hash,display_json,display_bytes FROM mixer_hosted_release.audit_events"
      ).rows
      |> hd()

    assert Codec.encode(Codec.from_display(d)) == bytes
    assert Codec.hash("mixer.hosted.audit.v1", bytes) == hash
    assert Jason.decode!(display) == d
    assert Codec.unhex(d["hash"]) == hash

    observe("display_and_cbor", %{
      event_hex: Codec.hex(bytes),
      event_hash: Codec.hex(hash),
      display_bytes: display
    })
  end

  test "24 request body exact6MiB and over plus signed and canonical64KiB edges" do
    assert {:ok, _} = attempt(body: :binary.copy(" ", 6_291_456))
    rejected(key: "over", body: :binary.copy(" ", 6_291_457))

    assert {:ok, _} =
             attempt(key: "signedmax", canonical: <<1>>, signed: :binary.copy(" ", 65536))

    rejected(key: "signedover", canonical: <<2>>, signed: :binary.copy(" ", 65537))
    assert {:ok, _} = attempt(key: "cborlimit", canonical: :binary.copy(<<3>>, 65536))
    rejected(key: "cborover", canonical: :binary.copy(<<4>>, 65537))
  end

  test "25 reason512 UTF8 and key128 exact plus over" do
    assert {:ok, _} = attempt(key: String.duplicate("k", 128), reason: String.duplicate("é", 256))
    rejected(key: String.duplicate("k", 129))
    rejected(key: "next", reason: String.duplicate("é", 256) <> "a")
    rejected(key: "")
    rejected(key: "illegal space")
    rejected(key: "ip", source_ip: String.duplicate("1", 46))
  end

  test "26 payload metadata min max oneover and blob digest binding" do
    rejected(canonical: <<>>)
    rejected(signed: "")
    rejected(body: "")
    rejected(payload_size: 0)
    assert {:ok, _} = attempt(payload_size: 4_194_304)
    rejected(key: "maxplus", payload_size: 4_194_305)
    rejected(key: "blob", blob_ref: "sha256:" <> String.duplicate("f", 64))
    rejected(key: "sig", signature: <<0::504>>)
    rejected(key: "hash", manifest: <<0::256>>)
  end

  test "27 event id uint64 exhaustion fails closed no wrap or partial write" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.tenant_heads SET last_event=18446744073709551615")
    rejected(key: "next")
    assert counts() == [1, 1, 1, "18446744073709551615"]
  end

  test "28 fixed codec totalbytes boundary, no ambiguous maps floats negative booleans" do
    assert byte_size(Codec.encode(String.duplicate("a", 16381))) == 16384
    assert_raise ArgumentError, fn -> Codec.encode(String.duplicate("a", 16382)) end

    for v <- [%{}, true, false, -1, 1.5, {:bytes, 1}, <<255>>] do
      assert_raise ArgumentError, fn -> Codec.encode(v) end
    end
  end

  test "29 bounded local immutable blob stage reopen corruption and orphan cleanup" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "one")
    s = Blob.open(root)
    {s, ref} = Blob.stage(s, <<1>>)
    {same, ^ref} = Blob.stage(s, <<1>>)
    assert same == s
    assert Blob.open(root) == s
    assert Blob.read(s, ref) == <<1>>
    {s, orphan} = Blob.stage(s, <<2>>)
    assert Blob.reconcile(s, MapSet.new([ref]), true) == s
    s = Blob.reconcile(s, MapSet.new([ref]), false)
    assert s.count == 1
    assert_raise File.Error, fn -> Blob.read(s, orphan) end
    path = Path.join(root, String.replace_prefix(ref, "sha256:", ""))
    File.chmod!(path, 0o600)
    File.write!(path, <<3>>)
    assert_raise ArgumentError, fn -> Blob.open(root) end
    assert_raise ArgumentError, fn -> Blob.stage(s, <<1>>) end
  end

  test "30 local blob size count and total quota exact then oneover" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "quota")
    s = Blob.open(root)
    assert_raise ArgumentError, fn -> Blob.stage(s, <<>>) end
    assert_raise ArgumentError, fn -> Blob.stage(s, :binary.copy(<<0>>, 4_194_305)) end

    s =
      Enum.reduce(0..3, s, fn n, s ->
        {next, _} = Blob.stage(s, :binary.copy(<<n>>, 4_194_304))
        next
      end)

    assert s.bytes == 16_777_216
    assert Blob.open(root) == s
    assert_raise ArgumentError, fn -> Blob.stage(s, <<9>>) end
    root2 = Path.join(System.fetch_env!("MXAS_BLOBS"), "count")

    s =
      Enum.reduce(0..7, Blob.open(root2), fn n, s ->
        {next, _} = Blob.stage(s, <<n>>)
        next
      end)

    assert s.count == 8
    assert_raise ArgumentError, fn -> Blob.stage(s, <<9>>) end
  end

  test "31 closed codec depth nodes container and max output exact and oneover" do
    nested = Enum.reduce(1..16, 0, fn _, v -> [v] end)
    assert is_binary(Codec.encode(nested))
    assert_raise ArgumentError, fn -> Codec.encode([nested]) end
    assert is_binary(Codec.encode(List.duplicate(0, 256)))
    assert_raise ArgumentError, fn -> Codec.encode(List.duplicate(0, 257)) end
    # 1 outer + 15*(1+256) + 1 inner +239 leaves =4096 items.
    exact = List.duplicate(List.duplicate(0, 256), 15) ++ [List.duplicate(0, 239)]
    assert is_binary(Codec.encode(exact))

    assert_raise ArgumentError, fn ->
      Codec.encode(List.duplicate(List.duplicate(0, 256), 15) ++ [List.duplicate(0, 240)])
    end

    assert byte_size(Codec.encode(String.duplicate("a", 65533), 65536)) == 65536
    assert_raise ArgumentError, fn -> Codec.encode(String.duplicate("a", 65534), 65536) end
  end

  test "32 exact response bytes page row and encoded total bounds admission four then busy" do
    alias MixerAtomicStoragePreflight.Bounds
    assert byte_size(Bounds.response(:binary.copy("a", 4096))) == 4096
    assert_raise ArgumentError, fn -> Bounds.response(:binary.copy("a", 4097)) end
    assert byte_size(Bounds.body(:binary.copy("a", 6_291_456))) == 6_291_456
    assert_raise ArgumentError, fn -> Bounds.body(:binary.copy("a", 6_291_457)) end
    {hundred, _} = Bounds.page(List.duplicate("{}", 101), 100)
    assert length(hundred) == 100
    assert_raise ArgumentError, fn -> Bounds.page([], 101) end
    assert_raise ArgumentError, fn -> Bounds.page([], 0) end

    for n <- [32768, 32769] do
      row = "\"" <> String.duplicate("a", n - 2) <> "\""

      if n == 32768,
        do: assert(match?({[_], _}, Bounds.page([row], 1))),
        else: assert_raise(ArgumentError, fn -> Bounds.page([row], 1) end)
    end

    rows = List.duplicate("\"" <> String.duplicate("a", 32766) <> "\"", 100)
    {chosen, encoded} = Bounds.page(rows, 100)
    assert length(chosen) == 7
    assert byte_size(encoded) <= 262_144
    # Choose a small exact encoded ceiling; one byte less removes the row.
    row = "{}"
    reserved = byte_size("{\"events\":[],\"next\":null}") + 2 + 18
    assert match?({["{}"], _}, Bounds.page([row, row], 1, reserved))
    assert match?({[], _}, Bounds.page([row, row], 1, reserved - 1))
    {:ok, gate} = Bounds.admission_start()

    refs =
      Enum.map(1..4, fn _ ->
        {:ok, r} = Bounds.admit(gate)
        r
      end)

    assert Bounds.admit(gate) == :busy
    Bounds.release(gate, hd(refs))
    assert {:ok, _} = Bounds.admit(gate)
    Agent.stop(gate)
  end

  test "33 policy changes during blocking lock are freshly denied before cache" do
    assert {:ok, _} = attempt()
    parent = self()

    holder =
      Task.async(fn ->
        AdminRepo.transaction(fn ->
          sql("SELECT * FROM mixer_authz.fixture_policy WHERE actor=$1::text::uuid FOR UPDATE", [
            @one
          ])

          send(parent, :policy_locked)

          receive do
            :revoke ->
              sql(
                "UPDATE mixer_authz.fixture_policy SET active=false,revision=2 WHERE actor=$1::text::uuid",
                [@one]
              )
          end
        end)
      end)

    assert_receive :policy_locked

    waiting =
      Task.async(fn ->
        send(parent, :writer_starting)
        attempt()
      end)

    assert_receive :writer_starting
    Process.sleep(80)
    send(holder.pid, :revoke)
    Task.await(holder)
    assert {:rejected, _, _} = Task.await(waiting)
    assert counts() == [1, 1, 1, "1"]

    observe("post_lock_fresh_policy", %{
      cached_original_exists: true,
      waited_on_policy_writer: true,
      revoked_result_denied: true
    })
  end

  test "34 hand authored event state and exact display golden vectors" do
    golden = File.read!("golden-vectors.json") |> Jason.decode!()
    assert {:ok, _} = attempt()

    [cbor, event_hash, display, display_bytes] =
      sql(
        "SELECT event_cbor,event_hash,display_json,display_bytes FROM mixer_hosted_release.audit_events"
      ).rows
      |> hd()

    assert Codec.hex(cbor) == golden["event"]["cbor_hex"]
    assert Codec.hex(event_hash) == golden["event"]["sha256"]

    assert Codec.hash("mixer.hosted.audit.v1", Codec.unhex(golden["event"]["cbor_hex"])) ==
             event_hash

    assert Codec.hash("mixer.hosted.state.v1", Codec.unhex(golden["initial"]["cbor_hex"])) ==
             Codec.unhex(golden["initial"]["sha256"])

    assert Codec.hash("mixer.hosted.state.v1", Codec.unhex(golden["transition"]["cbor_hex"])) ==
             Codec.unhex(golden["transition"]["sha256"])

    assert scalar("SELECT encode(state_hash,'hex') FROM mixer_hosted_release.tenant_heads") ==
             golden["transition"]["sha256"]

    assert display == golden["expected_display"]
    assert display_bytes == golden["expected_display_bytes_utf8"]
    assert Codec.encode(Codec.from_display(display)) == cbor
  end

  test "35 SET ROLE self changes role setting and is rejected inside writer" do
    o = opts()

    assert_raise Postgrex.Error, fn ->
      Context.enter(fn c ->
        bind(c, Context, o)
        Context.query!(c, "SET LOCAL ROLE mxas_runtime")
        upload(c, o)
      end)
    end

    assert counts() == [0, 0, 0, "0"]
  end

  test "36 stage before locks failed transaction leaves bounded orphan; reopen partial crash fails closed" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "orphan")
    {s, ref} = Blob.stage(Blob.open(root), <<8>>)
    assert not Repo.in_transaction?()
    sql("UPDATE mixer_authz.fixture_fault SET boundary='audit'")
    rejected(payload: <<8>>, blob_ref: ref)
    assert counts() == [0, 0, 0, "0"]
    assert Blob.read(Blob.open(root), ref) == <<8>>
    assert Blob.reconcile(s, MapSet.new(), true).count == 1
    assert Blob.reconcile(s, MapSet.new(), false).count == 0
    # Simulated process death during exclusive file creation leaves incomplete immutable bytes.
    partial = Path.join(root, Codec.hex(:crypto.hash(:sha256, <<1, 2>>)))
    File.write!(partial, <<1>>)
    assert_raise ArgumentError, fn -> Blob.open(root) end
  end

  test "37 oversized on-disk blob rejects before allocation; stale handles cannot bypass quota" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "oversized")
    stale = Blob.open(root)
    {s, ref} = Blob.stage(stale, <<1>>)
    path = Path.join(root, String.replace_prefix(ref, "sha256:", ""))
    File.chmod!(path, 0o600)

    File.open!(path, [:write, :binary], fn f ->
      :file.position(f, 100_000_000)
      IO.binwrite(f, <<1>>)
    end)

    assert_raise ArgumentError, fn -> Blob.open(root) end
    assert_raise ArgumentError, fn -> Blob.read(s, ref) end
    assert_raise ArgumentError, fn -> Blob.stage(stale, <<1>>) end
    root2 = Path.join(System.fetch_env!("MXAS_BLOBS"), "stale")
    original = Blob.open(root2)
    for n <- 0..7, do: Blob.stage(original, <<n>>)
    assert_raise ArgumentError, fn -> Blob.stage(original, <<9>>) end
  end

  test "39 coherent terminal display CBOR and hash with wrong event ID cannot match head" do
    assert {:ok, _} = attempt()

    sql(
      "UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{id}','\"2\"')"
    )

    sql(
      "UPDATE mixer_hosted_release.audit_events SET event_cbor=set_byte(event_cbor,2,2),display_bytes=convert_to(display_json::text,'UTF8')"
    )

    sql(
      "UPDATE mixer_hosted_release.audit_events SET event_hash=mixer_hosted_release.hash_domain('mixer.hosted.audit.v1',event_cbor)"
    )

    sql(
      "UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{hash}',to_jsonb(encode(event_hash,'hex')))"
    )

    sql(
      "UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8')"
    )

    sql(
      "UPDATE mixer_hosted_release.tenant_heads SET audit_hash=(SELECT event_hash FROM mixer_hosted_release.audit_events)"
    )

    rejected(key: "new")
    assert counts() == [1, 1, 1, "1"]
  end

  test "40 coordinator authentication completion is transaction bound and retained exactly" do
    assert {:ok, _} = attempt()

    assert scalar("SELECT display_json->'actor'->>10 FROM mixer_hosted_release.audit_events") ==
             "99"

    for t <- [0, 100, 131, 9_007_199_254_740_992, -1] do
      rejected(key: "forged", input_authenticated_at: t)
    end

    o = opts()

    assert_raise MixerAtomicStoragePreflight.Rejected, fn ->
      Context.enter(fn c ->
        bind(c, Context, o)

        Context.query!(
          c,
          "SELECT set_config('mixer_atomic.authentication_completed_at','100',true)"
        )

        upload(c, o)
      end)
    end

    assert_raise MixerAtomicStoragePreflight.Rejected, fn ->
      Context.enter(fn c ->
        bind(c, Context, o)
        upload(%{c | authentication_completed_at: 100}, o)
      end)
    end

    # Valid exact completion remains checked against independently fresh DB time.
    sql("UPDATE mixer_authz.fixture_clock SET now_s=145")
    rejected(key: "stale")
    sql("UPDATE mixer_authz.fixture_clock SET now_s=68")
    rejected(key: "future")
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    rejected(key: "expired", expires: 99)
    assert counts() == [1, 1, 1, "1"]
  end

  test "41 authentication completion exact cross-clock bounds pass and one-over fails" do
    sql("UPDATE mixer_authz.fixture_clock SET now_s=144")
    assert {:ok, [201, _, _, false]} = attempt(key: "age45")
    sql("UPDATE mixer_authz.fixture_clock SET now_s=69")
    assert {:ok, [200, _, _, false]} = attempt(key: "future30")
    sql("UPDATE mixer_authz.fixture_clock SET now_s=145")
    rejected(key: "age46")
    sql("UPDATE mixer_authz.fixture_clock SET now_s=68")
    rejected(key: "future31")

    assert scalar(
             "SELECT count(*) FROM mixer_hosted_release.audit_events WHERE display_json->'actor'->>10='99'"
           ) == 2

    assert counts() == [1, 2, 2, "2"]
  end
  # Independently authored reviewer cases. Inserted into the frozen specimen's
  # existing test module solely to reuse its synthetic input/setup helpers.
  # "Observed limitation" cases preserve actual unsupported behavior explicitly;
  # their success must not be interpreted as product qualification.
  defp review_raw(c, o) do
    upload(c, o, MixerAtomicStoragePreflight.ReviewRaw)
  end

  defp review_raw_attempt(overrides) do
    o = opts(overrides)
    try do
      Context.enter(fn c ->
        bind(c, Context, o)
        review_raw(c, o)
      end)
    rescue
      e -> {:rejected, inspect(e.__struct__), Exception.message(e)}
    end
  end

  defp review_wait_for_runtime_lock do
    args = ["-h", System.fetch_env!("MXAS_SOCKET"), "-U", "preflight_owner", "-d", "atomic_preflight", "-At", "-c", "SELECT count(*) FROM pg_stat_activity WHERE usename='mxas_runtime' AND datname='atomic_preflight' AND wait_event_type='Lock' AND state='active' AND query LIKE '%mixer_hosted_release.upload_v1%'"]
    waiting = Enum.reduce_while(1..12, false, fn _, _ ->
      case System.cmd("psql", args, stderr_to_stdout: true) do
        {"1\n", 0} -> {:halt, true}
        _ -> Process.sleep(5); {:cont, false}
      end
    end)
    {waiting, args}
  end

  test "R01 null, fractional, NaN and unbounded completion fail closed in actual SQL" do
    for input <- [nil, "99.5", "NaN", "Infinity", "9007199254740992"] do
      assert {:rejected, _, _} = review_raw_attempt(input_authenticated_at: input)
      assert counts() == [0, 0, 0, "0"]
    end
    observe("review_completion_malformed", %{null_fraction_nan_infinity_overmax_rejected: true})
  end

  test "R02 zero is a numeric value rather than absence; stale zero is rejected" do
    assert {:rejected, _, _} = review_raw_attempt(input_authenticated_at: 0)
    sql("UPDATE mixer_authz.fixture_clock SET now_s=0")
    o = opts()
    assert {:ok, [201, _, _, false]} = Context.enter(fn c ->
      bind(c, Context, o)
      Repo.query!("SELECT set_config('mixer_atomic.authentication_completed_at','0',true)", [], log: false)
      changed = %{c | authentication_completed_at: 0}
      result = upload(changed, o)
      # Restore the outer invocation's original immutable field before its guard.
      Repo.query!("SELECT set_config('mixer_atomic.authentication_completed_at','99',true)", [], log: false)
      result
    end)
    assert scalar("SELECT display_json->'actor'->>10 FROM mixer_hosted_release.audit_events") == "0"
    observe("review_zero_completion", %{stale_zero_rejected: true, zero_is_valid_when_fresh_and_bound: true, trusted_raw_sql_fixture_only: true})
  end

  test "R03 corrected: SQL specimen rejects noninteger and NaN token expiry" do
    for {expiry, key} <- [{"10000.5", "fraction"}, {"NaN", "nan"}, {"9007199254740992", "over53"}] do
      assert {:rejected, _, _} = review_raw_attempt(expires: expiry, key: key)
      assert counts() == [0, 0, 0, "0"]
    end
    observe("review_expiry_validation_gap", %{fractional: "10000.5", nan: "NaN", over_integer53: "9007199254740992", all_rejected_by_corrected_specimen: true, required_product_fix: "validate finite integer expiry 0..2^53-1 before cast and inside SQL"})
  end

  test "R04 current expiry is reread after blocked head lock before cached result" do
    assert {:ok, _} = attempt(expires: 140)
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE")
        send(parent, :review_head_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_clock SET now_s=140")
        after
          1000 -> raise "review holder release absent"
        end
      end)
    end)
    assert_receive :review_head_locked
    waiter = Task.async(fn -> attempt(expires: 140) end)
    {waiting, argv} = review_wait_for_runtime_lock()
    send(holder.pid, :release)
    Task.await(holder)
    assert waiting
    assert {:rejected, _, _} = Task.await(waiter)
    assert counts() == [1, 1, 1, "1"]
    observe("review_expiry_after_wait", %{cached_result_denied_after_clock_advanced: true, actual_runtime_lock_wait_confirmed: waiting, psql_argv: argv, completion_still_within_age45: true})
  end

  test "R05 completion age is reread after blocked head lock before cached result" do
    assert {:ok, _} = attempt()
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE")
        send(parent, :review_age_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_clock SET now_s=145")
        after
          1000 -> raise "review holder release absent"
        end
      end)
    end)
    assert_receive :review_age_locked
    waiter = Task.async(fn -> attempt() end)
    {waiting, argv} = review_wait_for_runtime_lock()
    send(holder.pid, :release)
    Task.await(holder)
    assert waiting
    assert {:rejected, _, _} = Task.await(waiter)
    assert counts() == [1, 1, 1, "1"]
    observe("review_completion_after_wait", %{cached_result_denied_after_age46: true, actual_runtime_lock_wait_confirmed: waiting, psql_argv: argv, token_still_unexpired: true})
  end

  test "R06 corrected: malformed stored idempotent material fails closed" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.idempotency SET status=599,response=convert_to('altered','UTF8')")
    assert {:rejected, _, _} = attempt()
    assert counts() == [1, 1, 1, "1"]
    observe("review_idempotency_material_gap", %{changed_status_and_body_rejected: true, runtime_can_change_rows: false, product_constraints_and_linkage_pending: true})
  end

  test "R07 corrected: wrong existing idempotency event is rejected" do
    assert {:ok, _} = attempt(key: "first")
    assert {:ok, _} = attempt(key: "second")
    sql("UPDATE mixer_hosted_release.idempotency SET event_id=2 WHERE key='first'")
    assert {:rejected, _, _} = attempt(key: "first")
    assert counts() == [1, 2, 2, "2"]
    observe("review_idempotency_event_gap", %{response_event_id: "1", returned_event_id: "2", wrong_existing_event_rejected: true, immutable_runtime_rows: true})
  end

  test "R08 corrected: same-count missing nullable key and replacement are rejected" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=(display_json-'source_ip')||'{\"unexpected\":null}'::jsonb")
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8')")
    assert {:rejected, _, _} = attempt(key: "next")
    observe("review_closed_display_gap", %{same_count_extra_and_missing_null_rejected: true, known_partial_decoder_only: true})
  end

  test "R09 corrected: leading-zero decimal display spelling is rejected" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{actor,4}','\"01\"'::jsonb)")
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8')")
    assert {:rejected, _, _} = attempt(key: "next")
    observe("review_canonical_display_gap", %{leading_zero_integer_rejected: true, full_closed_decoder_pending: true})
  end

  test "R10 corrected: coherent wrong terminal predecessor is rejected" do
    assert {:ok, _} = attempt(key: "first")
    assert {:ok, _} = attempt(key: "second")
    sql("UPDATE mixer_hosted_release.audit_events SET previous_hash=decode(repeat('ab',32),'hex'),display_json=jsonb_set(display_json,'{previous_hash}',to_jsonb(repeat('ab',32))) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=mixer_hosted_release.event_from_display(display_json) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET event_hash=mixer_hosted_release.hash_domain('mixer.hosted.audit.v1',event_cbor) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{hash}',to_jsonb(encode(event_hash,'hex'))) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8') WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash=(SELECT event_hash FROM mixer_hosted_release.audit_events WHERE event_id=2)")
    assert {:rejected, _, _} = attempt(key: "third")
    observe("review_predecessor_edge_gap", %{coherent_wrong_predecessor_rejected: true, documented_historical_verification_pending: true})
  end

  test "R11 corrected: nonexistent artifact creation event violates same-tenant FK" do
    assert {:ok, _} = attempt()
    assert_raise Postgrex.Error, fn -> sql("UPDATE mixer_hosted_release.artifacts SET created_event=999") end
    assert {:ok, [200, _, _, false]} = attempt(key: "next")
    observe("review_artifact_creation_link_gap", %{nonexistent_creation_event_rejected_by_fk: true, complete_row_constraints_pending: true})
  end

  test "R12 private helper SQL identities owner ACL and type field ordering are captured" do
    rows = sql("SELECT p.oid::regprocedure::text,r.rolname,p.prosecdef,p.provolatile::text,p.proparallel::text,p.proleakproof,coalesce(p.proconfig,ARRAY[]::text[]),p.proacl::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') ORDER BY p.oid::regprocedure::text").rows
    for [identity, owner, definer, volatility, parallel, leak, config, _acl] <- rows do
      assert "search_path=pg_catalog" in config
      refute leak
      if definer do
        assert owner in ["mxas_resolver", "mxas_writer"]
        assert volatility == "v"
        assert parallel == "u"
        assert "row_security=on" in config
      else
        assert owner == "mxas_schema"
        assert volatility == "i"
        assert identity =~ "mixer_hosted_release."
      end
    end
    denied = for helper <- ["u(numeric)", "b(bytea)", "t(text)", "a(bytea[])", "hash_domain(text,bytea)", "target(mixer_hosted_release.upload_input)", "hx(text)", "event_from_display(jsonb)"] do
      allowed = scalar("SELECT has_function_privilege('mxas_runtime',$1,'EXECUTE')", ["mixer_hosted_release." <> helper])
      refute allowed
      helper
    end
    fields = sql("SELECT a.attnum,a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a JOIN pg_type t ON t.typrelid=a.attrelid JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='mixer_hosted_release' AND t.typname='call_context' AND a.attnum>0 ORDER BY a.attnum").rows
    assert List.last(fields) == [9, "authentication_completed_at", "numeric"]
    observe("review_actual_catalog", %{functions: rows, runtime_private_helpers_denied: denied, call_context_fields: fields, product_manifest_conceptual_names_are_not_this_DDL: true})
  end

  test "R13 independent randomized uint64 encodings agree with SQL and Elixir" do
    vectors = Jason.decode!(File.read!("review-uint64-vectors.json"))
    for %{"decimal" => n, "cbor_hex" => expected} <- vectors do
      assert scalar("SELECT encode(mixer_hosted_release.u($1::text::numeric),'hex')", [n]) == expected
      assert Codec.hex(Codec.encode(String.to_integer(n))) == expected
    end
    observe("review_uint64_independent", %{vector_count: length(vectors), exact_integer_python_reference: true})
  end

  test "R14 local corrupt object is never collected while outcome remains uncertain" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "review-corrupt-uncertain")
    {store, reference} = Blob.stage(Blob.open(root), "review-material")
    "sha256:" <> name = reference
    path = Path.join(root, name)
    File.chmod!(path, 0o600)
    File.write!(path, "altered")
    assert Blob.reconcile(store, MapSet.new(), true) == store
    assert File.exists?(path)
    assert_raise ArgumentError, fn -> Blob.open(root) end
    observe("review_blob_uncertainty", %{corruption_detected: true, uncertain_collection_preserved_file: true, offline_recovery_required: true})
  end

  test "R15 missing policy row rolls back without treating empty shared lock as success" do
    sql("DELETE FROM mixer_authz.fixture_policy WHERE actor=$1::text::uuid", [@one])
    assert {:rejected, _, _} = attempt()
    assert counts() == [0, 0, 0, "0"]
    sql("INSERT INTO mixer_authz.fixture_policy VALUES($1::text::uuid,'developer',true,1)", [@one])
    observe("review_missing_lock", %{missing_row_denied: true, no_partial_effects: true})
  end

  test "R16 every immutable artifact value is compared on new-key identical upload" do
    assert {:ok, _} = attempt()
    for {column, expression} <- [{"signed_document", "convert_to('{ }','UTF8')"}, {"signature", "decode(repeat('01',64),'hex')"}, {"payload_size", "2"}, {"blob_ref", "'sha256:'||repeat('01',32)"}] do
      original = scalar("SELECT " <> column <> " FROM mixer_hosted_release.artifacts")
      sql("UPDATE mixer_hosted_release.artifacts SET " <> column <> "=" <> expression)
      assert {:rejected, _, _} = attempt(key: "changed-" <> column)
      sql("UPDATE mixer_hosted_release.artifacts SET " <> column <> "=$1", [original])
    end
    assert counts() == [1, 1, 1, "1"]
    observe("review_material_compare", %{signed_signature_size_reference_corruption_rejected: true})
  end

  test "R17 composite numeric20 scale0 rounds invalid fractional input before a body guard" do
    sql("CREATE TYPE mixer_hosted_release.review_numeric_typmod AS (expires_at numeric(20,0),authentication_completed_at numeric(20,0))")
    rows = sql("SELECT (v).expires_at::text,(v).authentication_completed_at::text,trunc((v).expires_at)=(v).expires_at,trunc((v).authentication_completed_at)=(v).authentication_completed_at FROM (SELECT ROW(149.5::numeric,-0.1::numeric)::mixer_hosted_release.review_numeric_typmod AS v) s").rows
    assert rows == [["150", "0", true, true]]
    fields = sql("SELECT a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a JOIN pg_type t ON t.typrelid=a.attrelid JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='mixer_hosted_release' AND t.typname='review_numeric_typmod' AND a.attnum>0 ORDER BY a.attnum").rows
    observe("review_numeric_typmod_rounding", %{raw_inputs: ["149.5", "-0.1"], post_cast: rows, catalog_fields: fields, trunc_guard_after_cast_can_miss_invalid_input: true, product_recommendation: "unconstrained numeric context inputs plus explicit finite integer 0..2^53-1 guards"})
    sql("DROP TYPE mixer_hosted_release.review_numeric_typmod")
  end

  test "R18 unconstrained numeric entry guard rejects nonfinite fractional negative and overrange" do
    for {input, expected} <- [{nil, false}, {"NaN", false}, {"Infinity", false}, {"-Infinity", false}, {"-0.1", false}, {"99.5", false}, {"9007199254740992", false}, {"0", true}, {"9007199254740991", true}] do
      assert scalar("SELECT coalesce($1::text::numeric >= 0 AND $1::text::numeric <= 9007199254740991 AND trunc($1::text::numeric) = $1::text::numeric,false)", [input]) == expected
    end
    observe("review_finite_seconds_oracle", %{unconstrained_numeric_guard_checked: true, valid_zero_and_max: true, null_nonfinite_fraction_negative_overmax_rejected: true})
  end

  test "R19 corrected: expiry refreshed after confirmed late SQL wait before insert" do
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("LOCK TABLE mixer_authz.fixture_fault IN ACCESS EXCLUSIVE MODE")
        send(parent, :review_late_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_clock SET now_s=140")
        after
          1000 -> raise "review late holder release absent"
        end
      end)
    end)
    assert_receive :review_late_locked
    waiter = Task.async(fn -> attempt(expires: 140) end)
    args = ["-h", System.fetch_env!("MXAS_SOCKET"), "-U", "preflight_owner", "-d", "atomic_preflight", "-At", "-c", "SELECT count(*) FROM pg_locks WHERE relation='mixer_authz.fixture_fault'::regclass AND NOT granted"]
    blocked = Enum.reduce_while(1..15, false, fn _, _ ->
      case System.cmd("psql", args, stderr_to_stdout: true) do
        {"1\n", 0} -> {:halt, true}
        _ -> Process.sleep(5); {:cont, false}
      end
    end)
    send(holder.pid, :release)
    Task.await(holder)
    result = Task.await(waiter)
    assert blocked
    assert {:rejected, _, _} = result
    assert scalar("SELECT now_s::text FROM mixer_authz.fixture_clock") == "140"
    assert counts() == [0, 0, 0, "0"]
    observe("review_expiry_before_effect_gap", %{actual_relation_lock_wait_confirmed: true, lock_relation: "mixer_authz.fixture_fault", psql_argv: args, expiry: "140", clock_at_insert: "140", no_event_decision_persisted: true, inserted_after_expiry: false, completion_still_within_age45: true, product_fresh_time_before_persistence_required: true})
  end

  test "R20 policy is read after confirmed shared lock wait before cached result" do
    assert {:ok, _} = attempt()
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("SELECT * FROM mixer_authz.fixture_policy WHERE actor=$1::text::uuid FOR UPDATE", [@one])
        send(parent, :review_policy_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_policy SET active=false,revision=2 WHERE actor=$1::text::uuid", [@one])
        after
          1000 -> raise "review policy holder release absent"
        end
      end)
    end)
    assert_receive :review_policy_locked
    waiter = Task.async(fn -> attempt() end)
    {waiting, argv} = review_wait_for_runtime_lock()
    send(holder.pid, :release)
    Task.await(holder)
    assert waiting
    assert {:rejected, _, _} = Task.await(waiter)
    assert counts() == [1, 1, 1, "1"]
    observe("review_policy_after_wait", %{actual_runtime_lock_wait_confirmed: waiting, revoked_cached_result_denied: true, psql_argv: argv})
  end
  # AS01–AS07 correction cases. Independent rejection inputs and Python bytes live
  # in display-corpus.json, generated only from the selected readable contract.
  test "C01 actual unconstrained numeric catalog and every finite-integer input boundary" do
    for {type, field} <- [{"call_context", "expires_at"}, {"call_context", "authentication_completed_at"}, {"upload_input", "payload_size"}] do
      assert scalar("SELECT format_type(a.atttypid,a.atttypmod) FROM pg_attribute a JOIN pg_type t ON t.typrelid=a.attrelid JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='mixer_hosted_release' AND t.typname=$1 AND a.attname=$2", [type, field]) == "numeric"
    end
    malformed = [nil, "NaN", "Infinity", "-Infinity", "-0.1", "99.5", "-1"]
    cases = for {field, over} <- [expires: "9007199254740992", input_authenticated_at: "9007199254740992", payload_size: "4194305"], value <- malformed ++ [over] do
      assert {:rejected, _, _} = review_raw_attempt([{field, value}])
      assert counts() == [0, 0, 0, "0"]
      %{field: field, value: value}
    end
    assert {:rejected, _, _} = review_raw_attempt(payload_size: "0")
    assert {:rejected, _, _} = review_raw_attempt(expires: "0")
    assert {:ok, [201, _, _, false]} = review_raw_attempt(expires: "9007199254740991", payload_size: "4194304")
    # Application-side guards independently reject strings, decimals and nulls.
    for {field, value} <- [expires: "10000", expires: nil, payload_size: "1", payload_size: 1.5, input_authenticated_at: "99"] do
      assert {:rejected, _, _} = attempt([{field, value}, {:key, "trusted"}])
    end
    observe("corrected_numeric_inputs", %{catalog_unconstrained: true, raw_rejections: cases, exact_max_expiry_and_payload_success: true, application_guards: true})
  end

  test "C02 both independent display decoders reject all field-class mutations and preserve valid boundary bytes" do
    corpus = Jason.decode!(File.read!("display-corpus.json"))
    for %{"label" => label, "display" => d} <- corpus["invalid"] do
      assert_raise ArgumentError, fn -> Codec.from_display(d) end
      result = try do
        scalar("SELECT mixer_hosted_release.event_from_display($1)", [d])
      rescue
        _e in Postgrex.Error -> :rejected
      end
      assert result == :rejected, label
    end
    for %{"label" => label, "display" => d, "expected_cbor_hex" => expected} <- corpus["valid"] do
      encoded = Codec.encode(Codec.from_display(d))
      assert Codec.hex(encoded) == expected, label
      assert scalar("SELECT mixer_hosted_release.event_from_display($1)", [d]) == encoded, label
      assert scalar("SELECT convert_to($1::jsonb::text,'UTF8')", [d]) == Codec.postgres_display(d), label
    end
    observe("corrected_display_corpus", %{invalid: length(corpus["invalid"]), valid: length(corpus["valid"]), two_independent_decoders: true, independent_python_cbor_bytes: true, future_completion30_valid: true})
  end

  defp retained_row do
    columns = [:organization,:project,:event_id,:event_cbor,:event_hash,:previous_hash,:previous_state,:current_state,:display_json,:display_bytes]
    values = sql("SELECT organization,project,event_id::text,event_cbor,event_hash,previous_hash,previous_state,current_state,display_json,display_bytes FROM mixer_hosted_release.audit_events WHERE event_id=1").rows |> hd()
    values = List.update_at(values, 2, &String.to_integer/1)
    Map.new(Enum.zip(columns, values))
  end

  test "C03 both retained-row validators check every projection and exact PostgreSQL display bytes" do
    assert {:ok, _} = attempt(reason: "line\n雪", source_ip: "::1")
    row = retained_row()
    assert Codec.validate_row!(row) == :ok
    for {key,value} <- [organization: "wrong", project: "wrong", event_id: 2, event_cbor: <<1>>, event_cbor: :binary.copy(<<1>>,16_385),event_hash: <<1>>,previous_hash: <<1>>, previous_state: <<1>>,current_state: <<1>>,display_json: Map.put(row.display_json,"hash",String.duplicate("a",64)),display_bytes: Jason.encode!(row.display_json),display_bytes: :binary.copy("a",32_769)] do
      assert_raise ArgumentError, fn -> Codec.validate_row!(Map.put(row,key,value)) end
    end
    # SQL's same checks run on actual retained rows through the fixed mutation.
    original = sql("SELECT event_cbor,event_hash,previous_hash,previous_state,current_state,display_json,display_bytes FROM mixer_hosted_release.audit_events").rows |> hd()
    for mutation <- ["event_cbor=decode(repeat('00',16385),'hex')","display_bytes=decode(repeat('00',32769),'hex')","previous_state=decode(repeat('00',32),'hex')","current_state=decode(repeat('00',32),'hex')"] do
      sql("UPDATE mixer_hosted_release.audit_events SET "<>mutation)
      assert {:rejected,_,_}=attempt(key: "corruption")
      sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=$1,event_hash=$2,previous_hash=$3,previous_state=$4,current_state=$5,display_json=$6,display_bytes=$7",original)
    end
    observe("corrected_retained_row", %{all_projections_and_exact_display_bytes: true, oversized_retained_cbor_and_display_rejected: true})
  end

  test "C04 cached exact body status event and all associations fail closed" do
    assert {:ok,[201,original_body,event,false]}=attempt()
    original=sql("SELECT actor,action,target,request_hash,status,response,event_id FROM mixer_hosted_release.idempotency").rows |> hd()
    replacements = [
      "status=599", "status=200", "response=''::bytea", "response=convert_to(repeat('a',4097),'UTF8')", "response=convert_to('altered','UTF8')",
      "response=convert_to('{\"manifest_sha256\":\""<>String.duplicate("0",64)<>"\",\"event_id\":\"1\"}','UTF8')",
      "response=convert_to('{\"manifest_sha256\":\""<>Codec.hex(opts()[:manifest])<>"\",\"event_id\":\"01\"}','UTF8')",
      "event_id=1.5", "event_id=0", "event_id=-1", "event_id='NaN'::numeric", "event_id='Infinity'::numeric", "event_id=18446744073709551616", "actor='00000000-0000-0000-0000-000000000002'::uuid",
      "action='audit.read'", "target=decode('00','hex')", "request_hash=decode(repeat('00',32),'hex')"
    ]
    # Deliberately offline owner removes FK only for impossible malformed retained
    # IDs; it restores the exact original constraint before final catalog capture.
    sql("ALTER TABLE mixer_hosted_release.idempotency DROP CONSTRAINT idempotency_organization_project_event_id_fkey")
    try do
      for replacement <- replacements do
        sql("UPDATE mixer_hosted_release.idempotency SET "<>replacement)
        assert {:rejected,_,_}=attempt()
        assert counts()==[1,1,1,"1"]
        sql("UPDATE mixer_hosted_release.idempotency SET actor=$1,action=$2,target=$3,request_hash=$4,status=$5,response=$6,event_id=$7",original)
      end
    after
      sql("ALTER TABLE mixer_hosted_release.idempotency ADD CONSTRAINT idempotency_organization_project_event_id_fkey FOREIGN KEY(organization,project,event_id) REFERENCES mixer_hosted_release.audit_events(organization,project,event_id)")
    end
    # Refreshed eligible credential timestamps need not equal the original event.
    o=opts(expires: 20000)
    assert {:ok,[201,^original_body,^event,true]}=Context.enter(fn c ->
      bind(c,Context,o)
      Repo.query!("SELECT set_config('mixer_atomic.authentication_completed_at','100',true)",[],log: false)
      result=review_raw(%{c | authentication_completed_at: 100},o)
      Repo.query!("SELECT set_config('mixer_atomic.authentication_completed_at','99',true)",[],log: false)
      result
    end)
    assert {:ok,[200,later_body,later_event,false]}=attempt(key: "later")
    assert {:ok,[200,^later_body,^later_event,true]}=attempt(key: "later")
    observe("corrected_cached_material",%{mutations: length(replacements),refreshed_same_principal_replay: true,original_201_and_later_200_preserved: true})
  end

  test "C05 same-tenant cached event wrong actor target request and tenant are rejected" do
    assert {:ok,_}=attempt(key: "original")
    assert {:ok,_}=attempt(key: "other-actor",actor: @two)
    assert {:ok,_}=attempt(key: "other-request",body: "changed")
    assert {:ok,_}=attempt(key: "other-target",canonical: <<5>>)
    original=sql("SELECT status,response,event_id FROM mixer_hosted_release.idempotency WHERE key='original'").rows |> hd()
    for event <- [2,3,4] do
      sql("UPDATE mixer_hosted_release.idempotency SET status=200,event_id=$1::text::numeric,response=convert_to('{\"manifest_sha256\":\"'||$2||'\",\"event_id\":\"'||$1||'\"}','UTF8') WHERE key='original'",[to_string(event),Codec.hex(opts()[:manifest])])
      assert {:rejected,_,_}=attempt(key: "original")
    end
    sql("UPDATE mixer_hosted_release.idempotency SET status=$1,response=$2,event_id=$3 WHERE key='original'",original)
    assert_raise Postgrex.Error,fn -> sql("UPDATE mixer_hosted_release.idempotency SET organization='foreign' WHERE key='original'") end
    assert counts()==[2,4,4,"4"]
    observe("corrected_cached_event_associations",%{wrong_existing_actor_request_target: true,wrong_tenant_fk: true,no_disclosure_or_new_event: true})
  end

  test "C06 artifact creation FK actor exact target and actual transition are mandatory" do
    assert {:ok,_}=attempt(key: "first")
    assert {:ok,_}=attempt(key: "unchanged")
    assert {:ok,_}=attempt(key: "different",canonical: <<9>>)
    manifest=opts()[:manifest]
    for mutation <- ["created_event=2","created_event=3","created_actor='00000000-0000-0000-0000-000000000002'::uuid"] do
      sql("UPDATE mixer_hosted_release.artifacts SET "<>mutation<>" WHERE manifest=$1",[manifest])
      assert {:rejected,_,_}=attempt(key: "creation-check")
      assert {:rejected,_,_}=attempt(key: "first")
      sql("UPDATE mixer_hosted_release.artifacts SET created_event=1,created_actor=$2::text::uuid WHERE manifest=$1",[manifest,@one])
    end
    for mutation <- ["created_event=NULL","created_actor=NULL","created_event=999"] do
      assert_raise Postgrex.Error,fn -> sql("UPDATE mixer_hosted_release.artifacts SET "<>mutation<>" WHERE manifest=$1",[manifest]) end
    end
    sql("ALTER TABLE mixer_hosted_release.artifacts DROP CONSTRAINT artifact_creation_event")
    try do
      sql("UPDATE mixer_hosted_release.artifacts SET created_event=999 WHERE manifest=$1",[manifest])
      assert {:rejected,_,_}=attempt(key: "missing-creation")
      sql("UPDATE mixer_hosted_release.artifacts SET created_event=1 WHERE manifest=$1",[manifest])
    after
      sql("ALTER TABLE mixer_hosted_release.artifacts ADD CONSTRAINT artifact_creation_event FOREIGN KEY(organization,project,created_event) REFERENCES mixer_hosted_release.audit_events(organization,project,event_id) DEFERRABLE INITIALLY DEFERRED")
    end
    # Coherent owner edit to a creation transition (head event3 only validates
    # predecessor2); creation event1 is independently checked against Change1.
    original=sql("SELECT event_cbor,event_hash,current_state,display_json,display_bytes FROM mixer_hosted_release.audit_events WHERE event_id=1").rows |> hd()
    sql("UPDATE mixer_hosted_release.audit_events SET current_state=previous_state,display_json=jsonb_set(display_json,'{current_state}',to_jsonb(encode(previous_state,'hex'))) WHERE event_id=1")
    reencode(1)
    assert {:rejected,_,_}=attempt(key: "creation-state")
    sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=$1,event_hash=$2,current_state=$3,display_json=$4,display_bytes=$5 WHERE event_id=1",original)
    assert {:ok,[200,_,_,false]}=attempt(key: "restored")
    observe("corrected_artifact_creation",%{missing_null_nonexistent_existing_wrong_target_wrong_actor_and_transition_denied: true,deferred_same_tenant_fk: true,unchanged_success_retained: true})
  end

  defp reencode(id) do
    sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=mixer_hosted_release.event_from_display(display_json) WHERE event_id=$1::text::numeric",[to_string(id)])
    sql("UPDATE mixer_hosted_release.audit_events SET event_hash=mixer_hosted_release.hash_domain('mixer.hosted.audit.v1',event_cbor) WHERE event_id=$1::text::numeric",[to_string(id)])
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{hash}',to_jsonb(encode(event_hash,'hex'))) WHERE event_id=$1::text::numeric",[to_string(id)])
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8') WHERE event_id=$1::text::numeric",[to_string(id)])
  end

  test "C07 bounded adjacent edges reject missing predecessor wrong state and malformed predecessor" do
    for key <- ["first","second","third"], do: assert(match?({:ok,_},attempt(key: key)))
    before=counts()
    original=sql("SELECT event_cbor,event_hash,previous_state,display_json,display_bytes FROM mixer_hosted_release.audit_events WHERE event_id=3").rows |> hd()
    sql("UPDATE mixer_hosted_release.audit_events SET previous_state=decode(repeat('ab',32),'hex'),display_json=jsonb_set(display_json,'{previous_state}',to_jsonb(repeat('ab',32))) WHERE event_id=3")
    reencode(3)
    sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash=(SELECT event_hash FROM mixer_hosted_release.audit_events WHERE event_id=3)")
    assert {:rejected,_,_}=attempt(key: "state-edge")
    sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=$1,event_hash=$2,previous_state=$3,display_json=$4,display_bytes=$5 WHERE event_id=3",original)
    sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash=(SELECT event_hash FROM mixer_hosted_release.audit_events WHERE event_id=3)")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{actor,4}','\"01\"'::jsonb) WHERE event_id=2")
    assert {:rejected,_,_}=attempt(key: "invalid-predecessor")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{actor,4}','\"1\"'::jsonb) WHERE event_id=2")
    assert counts()==before
    sql("DELETE FROM mixer_hosted_release.idempotency WHERE key='second'")
    sql("DELETE FROM mixer_hosted_release.audit_events WHERE event_id=2")
    assert {:rejected,_,_}=attempt(key: "missing-predecessor")
    assert counts()==[1,2,2,"3"]
    observe("corrected_bounded_predecessor",%{wrong_state_missing_and_typed_predecessor_denied: true,no_whole_chain_walk: true,max_selected_rows_per_path_bounded: true})
  end

  defp correction_wait(relation, mode, overrides, clock, expected, pause_ms \\ 0) do
    before=counts();parent=self()
    holder=Task.async(fn -> AdminRepo.transaction(fn ->
      sql("LOCK TABLE "<>relation<>" IN "<>mode<>" MODE")
      send(parent,:correction_locked)
      receive do
        :release ->
          if pause_ms>0, do: Process.sleep(pause_ms)
          if clock, do: sql("UPDATE mixer_authz.fixture_clock SET now_s=$1::text::numeric",[to_string(clock)])
      after 1000 -> raise "correction lock release absent"
      end
    end) end)
    assert_receive :correction_locked
    waiter=Task.async(fn -> attempt(overrides) end)
    argv=["-h",System.fetch_env!("MXAS_SOCKET"),"-U","preflight_owner","-d","atomic_preflight","-At","-c","SELECT coalesce(json_agg(json_build_object('relation',l.relation::regclass::text,'mode',l.mode,'wait_event',a.wait_event,'wait_event_type',a.wait_event_type,'head_lock_granted',EXISTS(SELECT 1 FROM pg_locks held WHERE held.pid=l.pid AND held.granted AND held.relation='mixer_hosted_release.tenant_heads'::regclass AND held.mode='RowShareLock'),'policy_lock_granted',EXISTS(SELECT 1 FROM pg_locks held WHERE held.pid=l.pid AND held.granted AND held.relation='mixer_authz.fixture_policy'::regclass AND held.mode='RowShareLock')))::text,'[]') FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid WHERE NOT l.granted AND l.relation='"<>relation<>"'::regclass AND a.usename='mxas_runtime' AND a.query LIKE '%mixer_hosted_release.upload_v1%' OR false"]
    actual=Enum.reduce_while(1..15,[],fn _,_->
      case System.cmd("psql",argv,stderr_to_stdout: true) do
        {output,0}->
          rows=Jason.decode!(String.trim(output))
          if rows==[],do: (Process.sleep(5);{:cont,[]}),else: {:halt,rows}
        _ -> Process.sleep(5);{:cont,[]}
      end
    end)
    send(holder.pid,:release);Task.await(holder)
    result=Task.await(waiter)
    assert actual != []
    assert Enum.all?(actual, fn row -> row["head_lock_granted"] and row["policy_lock_granted"] and row["wait_event_type"] == "Lock" end)
    assert Enum.all?(actual, fn row -> row["mode"] == if(mode=="SHARE",do: "RowExclusiveLock",else: "AccessShareLock") end)
    if expected==:reject,do: assert(match?({:rejected,_,_},result)),else: assert(match?({:ok,_},result))
    if expected==:reject,do: assert(counts()==before)
    %{relation: relation,mode: mode,pg_observed_wait: actual,psql_argv: argv,clock_after: clock,outcome: expected,no_committed_changes: expected==:reject}
  end

  test "C08 actual late-read and cached-validation waits refresh exact expiry and age bounds" do
    assert {:ok,_}=attempt(expires: 140)
    cases=for {relation,clock,expected} <- [
      {"mixer_hosted_release.idempotency",140,:reject},
      {"mixer_hosted_release.artifacts",140,:reject},
      {"mixer_hosted_release.artifacts",145,:reject},
      {"mixer_hosted_release.artifacts",144,:success},
      {"mixer_hosted_release.artifacts",139,:success}
    ] do
      sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
      expiry=if clock>=144,do: 10000,else: 140
      correction_wait(relation,"ACCESS EXCLUSIVE",[expires: expiry],clock,expected)
    end
    assert counts()==[1,1,1,"1"]
    observe("corrected_late_read_waits",cases)
  end

  test "C09 actual DML waits rollback every mutation when expiry or freshness becomes invalid" do
    cases=for {relation,clock} <- [{"mixer_hosted_release.artifacts",140},{"mixer_hosted_release.audit_events",145},{"mixer_hosted_release.idempotency",140}] do
      sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
      expiry=if clock>=144,do: 10000,else: 140
      correction_wait(relation,"SHARE",[expires: expiry],clock,:reject)
    end
    assert counts()==[0,0,0,"0"]
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    control=correction_wait("mixer_hosted_release.idempotency","SHARE",[expires: 140],139,:success)
    assert counts()==[1,1,1,"1"]
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    age_control=correction_wait("mixer_hosted_release.audit_events","SHARE",[expires: 10000,key: "age45"],144,:success)
    assert counts()==[1,2,2,"2"]
    observe("corrected_dml_waits",%{rejections: cases,unexpired_success_control: control,exact_age45_success_control: age_control,post_dml_check_rolls_all_rows_back: true})
  end

  test "C10 final decision clock follows late read and original SQL deadline is never extended" do
    observed=correction_wait("mixer_authz.fixture_fault","ACCESS EXCLUSIVE",[],110,:success)
    assert scalar("SELECT display_json->'decision'->>0 FROM mixer_hosted_release.audit_events")=="110"
    assert scalar("SELECT display_json->>'recorded_at' FROM mixer_hosted_release.audit_events")=="110"
    deadline=DateTime.add(DateTime.utc_now(),180,:millisecond)
    rejected=correction_wait("mixer_hosted_release.artifacts","ACCESS EXCLUSIVE",[key: "deadline",deadline: deadline],nil,:reject,190)
    observe("corrected_final_clock_and_deadline",%{new_clock: observed,sql_original_deadline: rejected,decision_and_recorded: "110"})
  end

  test "C11 exact private helper identities and individual restrictive effective grants" do
    rows=sql("SELECT p.oid::regprocedure::text,p.prosecdef,r.rolname,pg_get_functiondef(p.oid),has_function_privilege('mxas_runtime',p.oid,'EXECUTE'),has_function_privilege('mxas_foreign',p.oid,'EXECUTE'),has_function_privilege('mxas_writer',p.oid,'EXECUTE') FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') ORDER BY 1").rows
    assert length(rows)==22
    for [identity,definer,owner,definition,runtime,foreign,writer] <- rows do
      refute definition =~ ~r/\bEXECUTE\b/i
      if String.contains?(identity,"upload_v1(") do
        assert definer and owner=="mxas_writer" and runtime and foreign and writer
      else
        refute foreign
        if String.starts_with?(identity,"mixer_hosted_release.") do
          refute definer;refute runtime
          assert owner=="mxas_schema" and writer
        end
      end
    end
    assert scalar("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') AND acl.grantee=0")==0
    fields=sql("SELECT t.typname,a.attnum,a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace JOIN pg_class c ON c.oid=t.typrelid JOIN pg_attribute a ON a.attrelid=t.typrelid WHERE n.nspname='mixer_hosted_release' AND c.relkind='c' AND a.attnum>0 ORDER BY t.typname,a.attnum").rows
    observe("corrected_catalog_grants",%{functions: Enum.map(rows,fn [identity,definer,owner,definition,runtime,foreign,writer]->%{identity: identity,definer: definer,owner: owner,definition_sha256: Codec.hex(:crypto.hash(:sha256,definition)),runtime_execute: runtime,fixture_foreign_execute: foreign,writer_execute: writer} end),composite_fields: fields,single_mutation: true,all_private_helpers_runtime_denied: true})
  end

  test "C12 invalid UTF8 and JSON numeric schema spelling fail closed independently" do
    base=Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    for d <- [Map.put(base,"reason",<<255>>),put_in(base,["actor",Access.at(3)],<<255>>),put_in(base,["target",Access.at(2)],<<255>>),Map.put(base,"source_ip",<<255>>)] do
      assert_raise ArgumentError,fn -> Codec.from_display(d) end
    end
    assert_raise Postgrex.Error,fn -> scalar("SELECT mixer_hosted_release.event_from_display(jsonb_set($1,'{reason}',to_jsonb(convert_from(decode('ff','hex'),'UTF8'))))",[base]) end
    for literal <- ["1.0","1.00","true","null","\"1\""] do
      assert_raise Postgrex.Error,fn -> scalar("SELECT mixer_hosted_release.event_from_display(jsonb_set($1,'{audit_schema}',$2::text::jsonb))",[base,literal]) end
    end
    normalized=scalar("SELECT jsonb_set($1,'{audit_schema}','1e0'::jsonb)",[base])
    assert is_integer(normalized["audit_schema"]) and normalized["audit_schema"]==1
    assert scalar("SELECT mixer_hosted_release.event_from_display($1)",[normalized])==Codec.encode(Codec.from_display(normalized))
    assert_raise ArgumentError,fn -> Codec.from_display(Map.put(base,"audit_schema",1.0)) end
    observe("corrected_utf8_and_schema_types",%{invalid_utf8: true,json_schema_retained_integer1_only: true,postgres_jsonb_normalizes_raw_exponent_1e0_to_integer1: true,raw_lexical_spelling_not_recoverable_at_jsonb_boundary: true,elixir_typed_float_rejected: true,root_clarification_preserves_failed_run5: true})
  end

  # Independently authored review additions. The producer's 73 cases and all
  # specimen implementation files remain unchanged in this reviewer copy.
  defp independent_sql_decode(d) do
    try do
      {:ok, scalar("SELECT mixer_hosted_release.event_from_display($1)", [d])}
    rescue
      e in Postgrex.Error -> {:rejected, e.postgres.code, e.postgres.message}
    end
  end

  defp independent_put(d, path, value), do: put_in(d, Enum.map(path, fn x -> if is_integer(x), do: Access.at(x), else: x end), value)

  test "I01 actual PostgreSQL and Elixir reject newline Unicode and control suffixes in canonical fields" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    paths = [["id"], ["actor",4], ["actor",10], ["decision",0], ["recorded_at"]] ++
      Enum.map(1..5, &["decision",&1]) ++ [["decision",6,0,2]] ++
      [["tenant",0],["tenant",1],["target",0],["target",1],["target",2],["target",3],
       ["actor",0],["actor",2],["actor",9],["request_id"],["decision",6,0,0],
       ["target",5],["target",6],["request_hash"],["source_ip"]]
    suffixes = ["\n", "\r", "\r\n", "\t", "\u000b", "\u0085", "\u00a0", "\u2028", "\u2029", "\u200b", "\u0301", "９"]
    results = for path <- paths, suffix <- suffixes do
      original = get_in(base, Enum.map(path, fn x -> if is_integer(x), do: Access.at(x), else: x end))
      original = if is_nil(original), do: "127.0.0.1", else: original
      d = independent_put(base,path,original <> suffix)
      elixir = try do Codec.from_display(d); :accepted rescue ArgumentError -> :rejected end
      pg = independent_sql_decode(d)
      %{path: path, suffix_hex: Codec.hex(suffix), elixir: elixir, postgres: if(elem(pg,0)==:ok,do: :accepted,else: :rejected)}
    end
    observe("independent_canonical_suffixes", results)
    assert Enum.all?(results, &(&1.elixir==:rejected and &1.postgres==:rejected))
  end

  test "I02 actual PostgreSQL display bytes agree for control Unicode and nonnormalized text" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    texts = Enum.map(1..31, &<<&1>>) ++ ["\"\\/", <<127>>, "\u0080", "\u0085", "\u00a0", "e\u0301", "é", "雪", "😀", "\u2028", "\u2029", "\u2060", "\ufeff", "\uffff"]
    results = for text <- texts do
      d = independent_put(Map.put(base,"reason",text),["actor",3],text)
      encoded = Codec.encode(Codec.from_display(d))
      {:ok, pg_encoded} = independent_sql_decode(d)
      pg_display = scalar("SELECT convert_to($1::jsonb::text,'UTF8')",[d])
      elixir_display = Codec.postgres_display(d)
      %{text_hex: Codec.hex(text), codecs_equal: pg_encoded==encoded, display_equal: pg_display==elixir_display,
        postgres_display_hex: Codec.hex(pg_display),elixir_display_hex: Codec.hex(elixir_display)}
    end
    observe("independent_unicode_display",results)
    assert Enum.all?(results, &(&1.codecs_equal and &1.display_equal))
  end

  test "I03 actual uploaded control and Unicode reasons retain exact row and replay bytes" do
    texts = ["\u000b", "\u000e", "\u001f", "\u2028\u2029", "e\u0301", "é", "😀", "\"\\/\b\f\n\r\t"]
    results = for {text,index} <- Enum.with_index(texts,1) do
      key = "unicode" <> to_string(index)
      assert {:ok,[status,body,event,false]} = attempt(key: key,reason: text)
      assert {:ok,[^status,^body,^event,true]} = attempt(key: key,reason: text)
      values = sql("SELECT organization,project,event_id::text,event_cbor,event_hash,previous_hash,previous_state,current_state,display_json,display_bytes FROM mixer_hosted_release.audit_events WHERE event_id=$1::text::numeric",[to_string(index)]).rows |> hd()
      row = Map.new(Enum.zip([:organization,:project,:event_id,:event_cbor,:event_hash,:previous_hash,:previous_state,:current_state,:display_json,:display_bytes],List.update_at(values,2,&String.to_integer/1)))
      elixir_row = try do Codec.validate_row!(row); :accepted rescue _ -> :rejected end
      sql_row = scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e WHERE event_id=$1::text::numeric",[to_string(index)])
      %{text_hex: Codec.hex(text),event: index,sql_row: sql_row,elixir_row: elixir_row,exact_replay: true}
    end
    observe("independent_uploaded_unicode",results)
    assert counts()==[1,8,8,"8"]
    assert Enum.all?(results,&(&1.sql_row and &1.elixir_row==:accepted))
  end

  test "I04 older cached event and nonfirst creation event validate their own predecessor" do
    assert {:ok,_}=attempt(key: "first")
    assert {:ok,_}=attempt(key: "second",canonical: <<2>>)
    assert {:ok,_}=attempt(key: "third",canonical: <<3>>)
    assert {:ok,_}=attempt(key: "cached-old")
    for i <- 5..8, do: assert(match?({:ok,_},attempt(key: "tail"<>to_string(i),canonical: <<i>>)))
    before=counts()
    original=scalar("SELECT display_json FROM mixer_hosted_release.audit_events WHERE event_id=3")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=display_json-'source_ip'||jsonb_build_object('replacement',null) WHERE event_id=3")
    assert {:rejected,_,_}=attempt(key: "cached-old")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=$1 WHERE event_id=3",[original])
    original=scalar("SELECT display_json FROM mixer_hosted_release.audit_events WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{actor,4}','\"01\"') WHERE event_id=2")
    assert {:rejected,_,_}=attempt(key: "creation-old",canonical: <<3>>)
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=$1 WHERE event_id=2",[original])
    assert counts()==before
    assert {:ok,[200,_,_,true]}=attempt(key: "cached-old")
    assert {:ok,[200,_,_,false]}=attempt(key: "creation-old",canonical: <<3>>)
    observe("independent_nonterminal_edges",%{head: 8,head_predecessor: 7,cached_event: 4,cached_predecessor: 3,creation_event: 3,creation_predecessor: 2,typed_corruption_denied: true,positive_restored: true})
  end

  test "I05 tiny fractional numeric inputs cannot disappear through the actual SQL input composites" do
    cases = for {field,values} <- [expires: ["10000.000000000000000000000000000001","9007199254740991.0000000001","-0.0000000000000000000000000001"],input_authenticated_at: ["99.0000000000000000000000000000001","-0.0000000000000000000000000001"],payload_size: ["1.0000000000000000000000000000001","4194304.0000000000000000000000001","0.9999999999999999999999999999999"]], value <- values do
      assert {:rejected,_,_}=review_raw_attempt([{field,value}])
      assert counts()==[0,0,0,"0"]
      %{field: field,value: value}
    end
    assert {:ok,[201,_,_,false]}=review_raw_attempt(expires: "10000.0000000000000000000000000000000",payload_size: "1.0000000000000000000000000000000")
    observe("independent_numeric_precision",%{fractional_rejections: cases,mathematically_integral_scale_control_accepted: true,input_catalog_preserves_scale: true})
  end

  test "I06 real clock relation wait cannot reuse prewait expiry or completion age" do
    expires=correction_wait("mixer_authz.fixture_clock","ACCESS EXCLUSIVE",[expires: 140],140,:reject)
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    stale=correction_wait("mixer_authz.fixture_clock","ACCESS EXCLUSIVE",[],145,:reject)
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    control=correction_wait("mixer_authz.fixture_clock","ACCESS EXCLUSIVE",[],144,:success)
    observe("independent_clock_read_waits",%{expiry: expires,stale46: stale,age45: control})
  end

  test "I07 cached validation late wait enforces original SQL deadline and future completion tolerance" do
    assert {:ok,_}=attempt()
    deadline=DateTime.add(DateTime.utc_now(),180,:millisecond)
    expired=correction_wait("mixer_hosted_release.artifacts","ACCESS EXCLUSIVE",[deadline: deadline],nil,:reject,190)
    future30=correction_wait("mixer_hosted_release.artifacts","ACCESS EXCLUSIVE",[],69,:success)
    sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
    future31=correction_wait("mixer_hosted_release.artifacts","ACCESS EXCLUSIVE",[],68,:reject)
    assert counts()==[1,1,1,"1"]
    observe("independent_cached_deadline_future",%{expired_original_deadline: expired,completion_future30: future30,completion_future31: future31})
  end

  test "I08 every actual private helper rejects direct runtime and foreign execution" do
    rows=sql("SELECT n.nspname,p.proname,ARRAY(SELECT format_type(x,null) FROM unnest(p.proargtypes::oid[]) x),p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='mixer_hosted_release' AND p.proname<>'upload_v1' ORDER BY 4").rows
    assert length(rows)==19
    foreign_opts=[socket_dir: System.fetch_env!("MXAS_SOCKET"),username: "mxas_foreign",database: "atomic_preflight",pool_size: 1,timeout: 5000,log: false]
    {:ok,foreign}=Postgrex.start_link(foreign_opts)
    results=try do
      for [schema,name,args,identity] <- rows do
        query="SELECT "<>schema<>"."<>name<>"("<>Enum.map_join(args,",", &("NULL::"<>&1))<>")"
        runtime=case Repo.query(query,[],log: false) do {:error,%Postgrex.Error{postgres: %{code: :insufficient_privilege}}}->true;_->false end
        denied=case Postgrex.query(foreign,query,[]) do {:error,%Postgrex.Error{postgres: %{code: :insufficient_privilege}}}->true;_->false end
        %{identity: identity,runtime_denied: runtime,foreign_denied: denied}
      end
    after
      GenServer.stop(foreign)
    end
    observe("independent_private_execute",results)
    assert Enum.all?(results,&(&1.runtime_denied and &1.foreign_denied))
  end

end

result = ExUnit.run()

summary = %{
  total: result.total,
  failures: result.failures,
  skipped: result.skipped,
  excluded: result.excluded
}

File.write!(
  System.fetch_env!("MXAS_RESULTS"),
  Jason.encode!(%{summary: summary, observations: Agent.get(PreflightObservations, & &1)},
    pretty: true
  )
)

System.halt(if result.failures == 0, do: 0, else: 1)
