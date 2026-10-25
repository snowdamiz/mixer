Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule PreparationIndependentRepo do
  use Ecto.Repo, otp_app: :preparation_review, adapter: Ecto.Adapters.Postgres
end

defmodule PreparationIndependentReview do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{ActivationPreparationSchema, ActivationPreparation, Catalog}
  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias F.{Admin, Migration}
  @helper "public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)"
  @roles %{writer: "browser_writer", lifecycle_login: "browser_lifecycle", relation_owner: "browser_schema_owner", ordinary_runtime_login: "browser_ordinary"}

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: Application.ensure_all_started(app)
    common = [hostname: "127.0.0.1", port: F.port(), database: "browser_storage", log: false, pool_size: 1]
    start_supervised!({Admin, common ++ [username: "browser_admin"]})
    start_supervised!({Migration, Keyword.put(common, :pool_size, 2) ++ [username: "browser_admin", after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end]})
    F.install!()
    F.provision!()
    start_supervised!({PreparationIndependentRepo, common ++ [username: "browser_lifecycle", after_connect: fn c ->
      for s <- ["SET search_path=pg_catalog", "SET statement_timeout='5s'", "SET lock_timeout='500ms'", "SET idle_in_transaction_session_timeout='5s'", "SET jit=off", "SET bytea_output=hex"], do: Postgrex.query!(c, s, [])
    end]})
    Ecto.Adapters.SQL.query!(PreparationIndependentRepo, "SELECT 1", [], log: false)
    assert admit() == {:ok, :function_surface_verified}
    baseline = baseline()
    install()
    c = F.connection!()
    assert {:error, %{postgres: %{code: :insufficient_privilege}}} = call(c, [F.random(), F.random(), F.random(), F.random(), 1], evidence())
    GenServer.stop(c)
    upgrade()
    assert baseline() == baseline
    assert_raise Catalog.Unavailable, fn -> admit() end
    F.q!(Admin, "INSERT INTO public.mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)")
    F.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES('person-1','human',true,0,1)")
    F.q!(Admin, "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)")
    :ok
  end

  setup do
    c = F.connection!()
    a = F.connection!("browser_admin")
    Postgrex.query!(a, "SET session_replication_role=replica", [])
    b = F.bootstrap(c)
    {b, attempt} = F.begin_login(c, b)
    {claim, snapshot} = F.claim(c, b, attempt)
    on_exit(fn -> for conn <- [c, a], Process.alive?(conn), do: GenServer.stop(conn) end)
    %{c: c, admin: a, b: b, attempt: attempt, claim: claim, snapshot: snapshot}
  end

  test "exact projection is decoder compatible and contains the complete retained claimed snapshot", x do
    assert {:ok, %{rows: [[r]]}} = prepare(x)
    assert Enum.sort(Map.keys(r)) == Enum.sort(~w(version snapshot principal_id profile_revision binding_revision principal_revision))
    assert r["snapshot"] == x.snapshot
    assert r["snapshot"]["attempt"]["ciphertext"] == nil
    assert {:ok, decoded} = ActivationPreparation.decode(r)
    assert decoded.principal_id == "person-1"
    assert decoded.snapshot.attempt_envelope == nil
    assert decoded.snapshot.browser["cookie_digest"] == x.b.cookie
  end

  test "whole NULL composite cannot short circuit admission", x do
    assert_deny(raw_expression(x, "NULL::public.mixer_browser_access_evidence"), "browser session unavailable")
  end

  for field <- [:profile, :version, :issuer, :subject, :client, :jti, :iat, :exp, :scopes] do
    @field field
    test "NULL access #{@field} cannot short circuit admission", x do
      assert_deny(prepare(x, Map.put(evidence(), @field, nil)), "browser session unavailable")
    end
  end

  test "raw digest sizes and revision range fail closed", x do
    for idx <- 0..3, value <- [nil, <<>>, F.random(31), F.random(33)] do
      assert_deny(call(x.c, List.replace_at(args(x), idx, value), evidence()), "browser session unavailable")
    end
    for revision <- [nil, 0, -1, 9_007_199_254_740_992], do: assert_deny(call(x.c, List.replace_at(args(x), 4, revision), evidence()), "browser session unavailable")
  end

  test "raw malformed and oversized text never reaches onboarding", x do
    for {field, max} <- [profile: 128, issuer: 2048, subject: 256, client: 256, jti: 256], value <- ["", String.duplicate("x", max + 1), String.duplicate("é", max)] do
      assert_deny(prepare(x, Map.put(evidence(), field, value)), "browser session unavailable")
    end
    # PostgreSQL itself rejects NUL and invalid UTF8 on the wire before the helper.
    for value <- [<<0>>, <<255>>] do
      assert {:error, %{postgres: %{code: :character_not_in_repertoire}}} = prepare(x, %{evidence() | subject: value})
    end
  end

  test "numeric dates enforce nonnegative53 human lifetime skew and strict expiry", x do
    now = dbnow(x.admin)
    for changes <- [%{iat: -1}, %{iat: 9_007_199_254_740_992}, %{exp: -1}, %{exp: 9_007_199_254_740_992}, %{iat: now + 32}, %{iat: now, exp: now + 901}, %{iat: now, exp: now}, %{iat: 0, exp: 900}] do
      assert_deny(prepare(x, Map.merge(evidence(), changes)), "browser session unavailable")
    end
    assert MixerHosted.Identity.Encoding.numeric_date?(0)
    assert not MixerHosted.Identity.Encoding.numeric_date?(-1)
    assert {:ok, _} = prepare(x, %{evidence() | iat: dbnow(x.admin), exp: dbnow(x.admin) + 900})
  end

  test "scope words use the ASCII grammar without freezing the verifier allowlist", x do
    scopes = ["mixer.workspace.read", "!#$%&'()*+,-./:;<=>?@[]^_`{|}~"]
    assert {:ok, _} = prepare(x, %{evidence() | scopes: scopes})
    assert {:ok, _} = prepare(x, %{evidence() | scopes: ["mixer.workspace.read" | for(n <- 1..63, do: "s#{n}")]})
  end

  test "scope NULL empty duplicate overcount and invalid ASCII words deny", x do
    for scopes <- [nil, [], [nil], ["mixer.workspace.read", nil], ["mixer.workspace.read", ""], ["mixer.workspace.read", "mixer.workspace.read"], ["other"], ["mixer.workspace.read" | for(n <- 1..64, do: "s#{n}")]], do: assert_deny(prepare(x, %{evidence() | scopes: scopes}), "browser session unavailable")
    for bad <- ["a b", "a\t", "a\n", "a\r", "a\"", "a\\", "é", <<127>>], do: assert_deny(prepare(x, %{evidence() | scopes: ["mixer.workspace.read", bad]}), "browser session unavailable")
  end

  test "scope array dimensions and lower bounds cannot bypass admission", x do
    for expr <- ["ARRAY[['mixer.workspace.read']]::text[]", "'[0:0]={mixer.workspace.read}'::text[]", "'{}'::text[]"] do
      assert_deny(scope_expression(x, expr), "browser session unavailable")
    end
  end

  test "aggregate scope bytes include exactly one separator between words", x do
    maxword = 1024 - byte_size("mixer.workspace.read") - 1
    assert {:ok, _} = prepare(x, %{evidence() | scopes: ["mixer.workspace.read", String.duplicate("s", maxword)]})
    assert_deny(prepare(x, %{evidence() | scopes: ["mixer.workspace.read", String.duplicate("s", maxword + 1)]}), "browser session unavailable")
    assert_deny(prepare(x, %{evidence() | scopes: ["mixer.workspace.read", String.duplicate("s", 1025)]}), "browser session unavailable")
  end

  test "only a valid exact claim and active matching human profile may disclose missing binding", x do
    missing = %{evidence() | subject: "unbound"}
    assert_deny(prepare(x, missing), "browser onboarding required")
    assert_deny(call(x.c, List.replace_at(args(x), 3, F.random()), missing), "browser session unavailable")
    change(x, "mixer_authz_profiles", "id='humans'", "active", false, fn -> assert_deny(prepare(x, missing), "browser identity unavailable") end)
    assert_deny(prepare(x, %{missing | profile: "missing-profile"}), "browser session unavailable")
  end

  test "saved claim cookie state configuration revision profile issuer and client are exact", x do
    for index <- 0..3, do: assert_deny(call(x.c, List.replace_at(args(x), index, F.random()), evidence()), "browser session unavailable")
    assert_deny(call(x.c, List.replace_at(args(x), 4, x.b.revision + 1), evidence()), "browser session unavailable")
    for {field, value} <- [profile: "Humans", version: 2, issuer: "https://ISSUER.fixture", client: "Console"], do: assert_deny(prepare(x, Map.put(evidence(), field, value)), "browser session unavailable")
    for subject <- ["SUBJECT-1", "subject-1@issuer.fixture"], do: assert_deny(prepare(x, %{evidence() | subject: subject}), "browser onboarding required")
  end

  test "current profile binding principal and valid-after fences remain authoritative", x do
    for {table, key, column, value} <- [
      {"profiles", "id='humans'", "active", false}, {"profiles", "id='humans'", "issuer", "https://drift.fixture"}, {"profiles", "id='humans'", "client_id", "other"}, {"profiles", "id='humans'", "identity_class", "service"},
      {"bindings", "subject='subject-1'", "active", false}, {"bindings", "subject='subject-1'", "identity_class", "service"}, {"principals", "id='person-1'", "active", false}, {"principals", "id='person-1'", "identity_class", "service"}, {"principals", "id='person-1'", "not_before", F.now() + 10}, {"principals", "id='person-1'", "not_before", F.now() - 1}
    ] do
      change(x, "mixer_authz_" <> table, key, column, value, fn -> assert_deny(prepare(x), "browser identity unavailable") end)
    end
  end

  test "nullable stored flags and revisions deny instead of SQL NULL short circuit", x do
    for {table, predicate, column} <- [{"profiles", "id='humans'", "active"}, {"profiles", "id='humans'", "state_revision"}, {"bindings", "subject='subject-1'", "active"}, {"bindings", "subject='subject-1'", "revision"}, {"principals", "id='person-1'", "active"}, {"principals", "id='person-1'", "revision"}, {"principals", "id='person-1'", "not_before"}] do
      table = "mixer_authz_" <> table
      Postgrex.query!(x.admin, "ALTER TABLE public.#{table} ALTER COLUMN #{column} DROP NOT NULL", [])
      try do
        change(x, table, predicate, column, nil, fn -> assert_deny(prepare(x), "browser identity unavailable") end)
      after
        Postgrex.query!(x.admin, "ALTER TABLE public.#{table} ALTER COLUMN #{column} SET NOT NULL", [])
      end
    end
  end

  test "positive53 authorization revisions accept their maximum and reject overlarge metadata", x do
    for {table, key, column} <- [{"profiles", "id='humans'", "state_revision"}, {"bindings", "subject='subject-1'", "revision"}, {"principals", "id='person-1'", "revision"}] do
      change(x, "mixer_authz_" <> table, key, column, 9_007_199_254_740_991, fn ->
        assert {:ok, %{rows: [[r]]}} = prepare(x)
        assert {:ok, _} = ActivationPreparation.decode(r)
      end)
    end
  end

  test "read helper holds no row locks creates no table effects and permits canonical writers", x do
    tables = ~w(mixer_browser_sessions mixer_browser_session_vault mixer_browser_oidc_attempts mixer_browser_session_events mixer_authz_profiles mixer_authz_bindings mixer_authz_principals mixer_authz_families mixer_authz_credentials)
    before = Map.new(tables, &{&1, Postgrex.query!(x.admin, "SELECT to_jsonb(t)::text FROM public.#{&1} t ORDER BY to_jsonb(t)::text", []).rows})
    Postgrex.query!(x.c, "BEGIN", [])
    try do
      assert {:ok, _} = prepare(x)
      [[pid]] = Postgrex.query!(x.c, "SELECT pg_backend_pid()", []).rows
      assert [[0]] = Postgrex.query!(x.admin, "SELECT count(*) FROM pg_catalog.pg_locks WHERE pid=$1 AND (locktype='tuple' OR (relation IS NOT NULL AND mode <> 'AccessShareLock'))", [pid]).rows
      Postgrex.query!(x.admin, "BEGIN", [])
      for {table, predicate, vals} <- [{"mixer_browser_sessions", "id=$1", [x.b.id]}, {"mixer_browser_session_vault", "browser_id=$1", [x.b.id]}, {"mixer_browser_oidc_attempts", "state_digest=$1", [x.attempt.state]}, {"mixer_authz_profiles", "id='humans'", []}, {"mixer_authz_bindings", "subject='subject-1'", []}, {"mixer_authz_principals", "id='person-1'", []}], do: Postgrex.query!(x.admin, "SELECT * FROM public.#{table} WHERE #{predicate} FOR UPDATE NOWAIT", vals)
      Postgrex.query!(x.admin, "ROLLBACK", [])
      after_state = Map.new(tables, &{&1, Postgrex.query!(x.admin, "SELECT to_jsonb(t)::text FROM public.#{&1} t ORDER BY to_jsonb(t)::text", []).rows})
      assert before == after_state
    after
      Postgrex.query(x.c, "ROLLBACK", [])
      Postgrex.query(x.admin, "ROLLBACK", [])
    end
  end

  test "one MVCC statement never mixes browser vault attempt and authorization generations", x do
    generation = %{1 => F.token(), 2 => F.token()}
    # Concurrent commits deliberately update all six joined rows as one unit.
    writer = Task.async(fn ->
      c = F.connection!("browser_admin")
      Postgrex.query!(c, "SET session_replication_role=replica", [])
      try do
        for k <- 1..60 do
          n = rem(k, 2) + 1
          Postgrex.query!(c, "BEGIN", [])
          Postgrex.query!(c, "UPDATE public.mixer_browser_sessions SET generation=$2 WHERE id=$1", [x.b.id, generation[n]])
          Postgrex.query!(c, "UPDATE public.mixer_browser_oidc_attempts SET generation=$2 WHERE state_digest=$1", [x.attempt.state, generation[n]])
          Postgrex.query!(c, "UPDATE public.mixer_browser_session_vault SET key_id=$2 WHERE browser_id=$1", [x.b.id, "generation#{n}"])
          Postgrex.query!(c, "UPDATE public.mixer_authz_profiles SET state_revision=$1 WHERE id='humans'", [n])
          Postgrex.query!(c, "UPDATE public.mixer_authz_bindings SET revision=$1 WHERE subject='subject-1'", [n])
          Postgrex.query!(c, "UPDATE public.mixer_authz_principals SET revision=$1 WHERE id='person-1'", [n])
          Postgrex.query!(c, "COMMIT", [])
        end
      after
        GenServer.stop(c)
      end
    end)
    try do
      for _ <- 1..80 do
        assert {:ok, %{rows: [[r]]}} = prepare(x)
        n = r["profile_revision"]
        assert n == r["binding_revision"] and n == r["principal_revision"]
        b = r["snapshot"]["browser"]
        a = r["snapshot"]["attempt"]
        assert b["generation"] == a["generation"]
        if b["generation"] in Map.values(generation) do
          assert b["generation"] == generation[n]
          assert r["snapshot"]["vault"]["key_id"] == "generation#{n}"
        else
          assert n == 1
          assert b["generation"] == x.snapshot["browser"]["generation"]
        end
        assert {:ok, _} = ActivationPreparation.decode(r)
      end
      Task.await(writer, 5000)
    after
      if Process.alive?(writer.pid), do: Task.shutdown(writer, :brutal_kill)
      for {table, column} <- [{"profiles", "state_revision"}, {"bindings", "revision"}, {"principals", "revision"}], do: Postgrex.query!(x.admin, "UPDATE public.mixer_authz_#{table} SET #{column}=1", [])
    end
  end

  test "post-snapshot DB clock denies expiry after a genuine relation-lock wait", x do
    deadline = dbnow(x.admin) + 1
    Postgrex.query!(x.admin, "BEGIN", [])
    Postgrex.query!(x.admin, "LOCK TABLE public.mixer_authz_profiles IN ACCESS EXCLUSIVE MODE", [])
    try do
      Process.sleep(max(deadline * 1000 - System.system_time(:millisecond) - 150, 0))
      task = Task.async(fn ->
        c = F.connection!()
        try do
          call(c, args(x), %{evidence() | exp: deadline})
        after
          GenServer.stop(c)
        end
      end)
      Process.sleep(250)
      Postgrex.query!(x.admin, "ROLLBACK", [])
      assert_deny(Task.await(task, 2000), "browser session unavailable")
    after
      Postgrex.query(x.admin, "ROLLBACK", [])
    end
  end

  test "DB deadline equality denies before unknown binding disclosure", x do
    for kind <- [:browser, :attempt, :claim, :token] do
      n = dbnow(x.admin)
      changes = case kind do
        :browser -> {"mixer_browser_sessions", "id=$1", [x.b.id], "created_at=#{n-20},last_seen_at=#{n-1},idle_expires_at=#{n},absolute_expires_at=#{n}"}
        :attempt -> {"mixer_browser_oidc_attempts", "state_digest=$1", [x.attempt.state], "created_at=#{n-10},claimed_at=#{n-5},claim_expires_at=#{n},expires_at=#{n}"}
        :claim -> {"mixer_browser_oidc_attempts", "state_digest=$1", [x.attempt.state], "created_at=#{n-10},claimed_at=#{n-5},claim_expires_at=#{n}"}
        :token -> nil
      end
      if changes do
        {table, predicate, params, assignments} = changes
        [[old]] = Postgrex.query!(x.admin, "SELECT to_jsonb(t) FROM public.#{table} t WHERE #{predicate}", params).rows
        Postgrex.query!(x.admin, "UPDATE public.#{table} SET #{assignments} WHERE #{predicate}", params)
        try do
          assert_deny(prepare(x, %{evidence() | subject: "unknown"}), "browser session unavailable")
        after
          fields = if kind == :browser, do: ~w(created_at last_seen_at idle_expires_at absolute_expires_at), else: ~w(created_at claimed_at claim_expires_at expires_at)
          set = fields |> Enum.with_index(2) |> Enum.map_join(",", fn {field, i} -> field <> "=$" <> Integer.to_string(i) end)
          Postgrex.query!(x.admin, "UPDATE public.#{table} SET #{set} WHERE #{predicate}", params ++ Enum.map(fields, &old[&1]))
        end
      else
        assert_deny(prepare(x, %{evidence() | exp: n, subject: "unknown"}), "browser session unavailable")
      end
    end
  end

  test "stale preparation cannot survive principal profile or binding revision CAS", x do
    for {table, predicate, column} <- [{"profiles", "id='humans'", "state_revision"}, {"bindings", "subject='subject-1'", "revision"}, {"principals", "id='person-1'", "revision"}] do
      assert {:ok, %{rows: [[r]]}} = prepare(x)
      i = %{F.identity() | profile_revision: r["profile_revision"], binding_revision: r["binding_revision"], principal_revision: r["principal_revision"]}
      change(x, "mixer_authz_" <> table, predicate, column, 2, fn ->
        assert {{:error, :raise_exception}, _, _, _, _} = F.activate(x.c, x.b, x.attempt, x.claim, i)
      end)
    end
    assert {{:ok, _}, _, _, _, _} = F.activate(x.c, x.b, x.attempt, x.claim)
    assert_deny(prepare(x), "browser session unavailable")
  end

  test "uncommitted revocation does not block preparation but later activation denies", x do
    Postgrex.query!(x.admin, "BEGIN", [])
    Postgrex.query!(x.admin, "UPDATE public.mixer_authz_principals SET active=false,revision=2 WHERE id='person-1'", [])
    try do
      assert {:ok, _} = prepare(x)
      Postgrex.query!(x.admin, "COMMIT", [])
      assert {{:error, :raise_exception}, _, _, _, _} = F.activate(x.c, x.b, x.attempt, x.claim)
    after
      Postgrex.query(x.admin, "ROLLBACK", [])
      Postgrex.query!(x.admin, "UPDATE public.mixer_authz_principals SET active=true,revision=1 WHERE id='person-1'", [])
    end
  end

  test "ordinary PUBLIC login table access and role switching remain denied", x do
    ordinary = F.connection!("browser_ordinary")
    try do
      assert {:error, %{postgres: %{code: :insufficient_privilege}}} = call(ordinary, args(x), evidence())
      for table <- ~w(mixer_browser_sessions mixer_browser_session_vault mixer_browser_oidc_attempts mixer_authz_profiles mixer_authz_bindings mixer_authz_principals), do: assert({:error, %{postgres: %{code: :insufficient_privilege}}} = Postgrex.query(x.c, "SELECT * FROM public.#{table}", []))
      assert {:error, %{postgres: %{code: :insufficient_privilege}}} = Postgrex.query(x.c, "SET ROLE browser_writer", [])
      assert [[false, false]] = Postgrex.query!(x.admin, "SELECT EXISTS(SELECT 1 FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x WHERE p.oid='#{@helper}'::regprocedure AND x.grantee=0), EXISTS(SELECT 1 FROM pg_type t CROSS JOIN LATERAL aclexplode(t.typacl) x WHERE t.oid='public.mixer_browser_access_evidence'::regtype AND x.grantee=0)", []).rows
    after
      GenServer.stop(ordinary)
    end
  end

  test "additive manifest is exact singleton and decoder is a build tracked dependency", x do
    m = ActivationPreparationSchema.catalog_manifest()
    assert m.version == 2 and m.baseline_version == 1 and m.additive_only
    assert map_size(m.functions) == 1 and map_size(m.composites) == 1
    assert ActivationPreparationSchema.signatures() == ActivationPreparationSchema.public_signatures()
    assert map_size(ActivationPreparationSchema.signatures()) == 1
    f = m.functions["mixer_browser_prepare_activation"]
    assert [[f.source, f.settings, f.argument_names, true, "jsonb", "browser_writer"]] == Postgrex.query!(x.admin, "SELECT prosrc,proconfig,proargnames,prosecdef,pg_get_function_result(oid),pg_get_userbyid(proowner) FROM pg_proc WHERE oid='#{@helper}'::regprocedure", []).rows
    assert Enum.map(m.composites["mixer_browser_access_evidence"], &Tuple.to_list/1) == Postgrex.query!(x.admin, "SELECT attname::text,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=(SELECT typrelid FROM pg_type WHERE oid='public.mixer_browser_access_evidence'::regtype) AND attnum>0 ORDER BY attnum", []).rows
    decoder = Path.expand("hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex")
    assert m.decoder.source_sha256 == Base.encode16(:crypto.hash(:sha256, File.read!(decoder)), case: :lower)
    assert decoder in ActivationPreparationSchema.__info__(:attributes)[:external_resource]
    assert_raise Catalog.Unavailable, fn -> admit() end
  end

  test "upgrade rollback removes temporary CREATE ownership transfer and grants while down preserves baseline", x do
    b = baseline()
    uninstall(x.admin)
    assert baseline() == b
    assert admit() == {:ok, :function_surface_verified}
    install()
    plan = plan()
    try do
      for s <- Enum.take(plan, 7), do: Postgrex.query!(x.admin, s, [])
      assert [[true]] = Postgrex.query!(x.admin, "SELECT has_schema_privilege('browser_writer','public','CREATE')", []).rows
      assert {:error, _} = Postgrex.query(x.admin, "SELECT 1/0", [])
    after
      Postgrex.query!(x.admin, "ROLLBACK", [])
    end
    assert [[false, "browser_schema_owner", false]] = Postgrex.query!(x.admin, "SELECT has_schema_privilege('browser_writer','public','CREATE'),pg_get_userbyid(proowner),has_function_privilege('browser_lifecycle',oid,'EXECUTE') FROM pg_proc WHERE oid='#{@helper}'::regprocedure", []).rows
    upgrade()
    assert baseline() == b
    assert {:ok, _} = prepare(x)
  end

  test "upgrade rejects unsafe flags memberships reads CREATE owners and explicit name errors", x do
    b = baseline()
    uninstall(x.admin)
    install()
    try do
      for {set, reset} <- [
        {"GRANT CREATE ON SCHEMA public TO browser_writer", "REVOKE CREATE ON SCHEMA public FROM browser_writer"},
        {"ALTER ROLE browser_lifecycle INHERIT", "ALTER ROLE browser_lifecycle NOINHERIT"},
        {"ALTER ROLE browser_writer LOGIN", "ALTER ROLE browser_writer NOLOGIN"},
        {"ALTER ROLE browser_schema_owner BYPASSRLS", "ALTER ROLE browser_schema_owner NOBYPASSRLS"},
        {"GRANT browser_ordinary TO browser_writer", "REVOKE browser_ordinary FROM browser_writer"},
        {"GRANT SELECT(subject) ON public.mixer_authz_bindings TO browser_lifecycle", "REVOKE SELECT(subject) ON public.mixer_authz_bindings FROM browser_lifecycle"},
        {"ALTER FUNCTION #{@helper} OWNER TO browser_admin", "ALTER FUNCTION #{@helper} OWNER TO browser_schema_owner"},
        {"ALTER TYPE public.mixer_browser_access_evidence OWNER TO browser_admin", "ALTER TYPE public.mixer_browser_access_evidence OWNER TO browser_schema_owner"}
      ] do
        Postgrex.query!(x.admin, set, [])
        try do
          for s <- Enum.take(plan(), 4), do: Postgrex.query!(x.admin, s, [])
          assert {:error, %{postgres: %{code: :insufficient_privilege}}} = Postgrex.query(x.admin, Enum.at(plan(), 4), [])
        after
          Postgrex.query!(x.admin, "ROLLBACK", [])
          Postgrex.query!(x.admin, reset, [])
        end
      end
      for names <- [["browser_writer", "browser_writer", "browser_schema_owner"], ["public", "browser_lifecycle", "browser_schema_owner"], ["x;SELECT1", "browser_lifecycle", "browser_schema_owner"], ["pg_bad", "browser_lifecycle", "browser_schema_owner"], [nil, "browser_lifecycle", "browser_schema_owner"]], do: assert_raise(ArgumentError, fn -> apply(ActivationPreparationSchema, :provisioning_statements, names) end)
    after
      upgrade()
    end
    assert baseline() == b
  end

  # Deliberately records whether this upgrade-only plan rejects dirty addition
  # ACLs. The independent receipt must report this result, not infer readiness.
  test "dirty addition PUBLIC execution and usage must not survive upgrade", x do
    uninstall(x.admin)
    install()
    Postgrex.query!(x.admin, "GRANT EXECUTE ON FUNCTION #{@helper} TO PUBLIC", [])
    Postgrex.query!(x.admin, "GRANT USAGE ON TYPE public.mixer_browser_access_evidence TO PUBLIC", [])
    result = try do
      for s <- Enum.take(plan(), 4), do: Postgrex.query!(x.admin, s, [])
      Postgrex.query(x.admin, Enum.at(plan(), 4), [])
    after
      Postgrex.query!(x.admin, "ROLLBACK", [])
      Postgrex.query!(x.admin, "REVOKE EXECUTE ON FUNCTION #{@helper} FROM PUBLIC", [])
      Postgrex.query!(x.admin, "REVOKE USAGE ON TYPE public.mixer_browser_access_evidence FROM PUBLIC", [])
      upgrade()
    end
    assert {:error, %{postgres: %{code: :insufficient_privilege}}} = result
  end

  defp evidence, do: %{profile: "humans", version: 1, issuer: "https://issuer.fixture", subject: "subject-1", client: "console", jti: F.token(), iat: F.now()-5, exp: F.now()+500, scopes: ["mixer.workspace.read"]}
  defp args(x), do: [x.b.cookie, x.attempt.state, x.b.config, x.claim, x.b.revision]
  defp prepare(x, i \\ evidence()), do: call(x.c, args(x), i)
  defp call(c, args, i), do: Postgrex.query(c, "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,ROW($6,$7,$8,$9,$10,$11,$12,$13,$14)::public.mixer_browser_access_evidence)", args ++ [i.profile,i.version,i.issuer,i.subject,i.client,i.jti,i.iat,i.exp,i.scopes], timeout: 5000, queue: false)
  defp raw_expression(x, expr), do: Postgrex.query(x.c, "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,#{expr})", args(x))
  defp scope_expression(x, expr) do
    i=evidence()
    Postgrex.query(x.c, "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,ROW($6,$7,$8,$9,$10,$11,$12,$13,#{expr})::public.mixer_browser_access_evidence)", args(x) ++ [i.profile,i.version,i.issuer,i.subject,i.client,i.jti,i.iat,i.exp])
  end
  defp assert_deny(result, message), do: assert(match?({:error, %{postgres: %{code: :raise_exception, message: ^message}}}, result), inspect(result))
  defp dbnow(c), do: Postgrex.query!(c, "SELECT floor(extract(epoch FROM clock_timestamp()))::bigint", []).rows |> hd() |> hd()
  defp change(x, table, predicate, column, value, fun) do
    [[old]]=Postgrex.query!(x.admin, "SELECT #{column} FROM public.#{table} WHERE #{predicate}", []).rows
    Postgrex.query!(x.admin, "UPDATE public.#{table} SET #{column}=$1 WHERE #{predicate}", [value])
    try do
      fun.()
    after
      Postgrex.query!(x.admin, "UPDATE public.#{table} SET #{column}=$1 WHERE #{predicate}", [old])
    end
  end
  defp install do
    c=F.connection!("browser_admin")
    try do
      Postgrex.query!(c,"SET ROLE browser_schema_owner",[])
      for s <- ActivationPreparationSchema.statements(), do: Postgrex.query!(c,s,[])
    after
      GenServer.stop(c)
    end
  end
  defp plan, do: ActivationPreparationSchema.provisioning_statements("browser_writer","browser_lifecycle","browser_schema_owner")
  defp upgrade do
    c=F.connection!("browser_admin")
    try do
      for s <- plan(), do: Postgrex.query!(c,s,[])
    after
      Postgrex.query(c,"ROLLBACK",[])
      GenServer.stop(c)
    end
  end
  defp uninstall(c), do: Enum.each(ActivationPreparationSchema.rollback_statements(), &Postgrex.query!(c,&1,[]))
  defp admit, do: PreparationIndependentRepo.transaction(fn -> Catalog.check_function_surface!(PreparationIndependentRepo,@roles,System.monotonic_time(:millisecond)+5000) end,timeout: 5000,queue: false)
  defp baseline do
    Map.new([
      {"functions", "SELECT p.oid::bigint,p.proname::text,p.proowner::bigint,p.prosrc,p.proacl::text,p.proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND left(p.proname,14)='mixer_browser_' AND p.proname<>'mixer_browser_prepare_activation' ORDER BY p.oid"},
      {"types", "SELECT oid::bigint,typname::text,typowner::bigint,typacl::text FROM pg_type WHERE typname IN('mixer_browser_cipher','mixer_browser_attempt','mixer_browser_verified') ORDER BY oid"},
      {"relations", "SELECT c.oid::bigint,c.relowner::bigint,c.relacl::text,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.oid"},
      {"policies", "SELECT polrelid::bigint,polname::text,polroles::text,polqual::text,polwithcheck::text FROM pg_policy ORDER BY polrelid,polname"}
    ], fn {name,sql} -> {name,F.q!(Admin,sql).rows} end)
  end
end
