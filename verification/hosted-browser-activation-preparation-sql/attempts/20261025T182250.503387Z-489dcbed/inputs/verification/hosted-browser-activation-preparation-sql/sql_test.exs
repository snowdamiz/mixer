Code.require_file("../../hosted/test/mixer_hosted/browser_auth/storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.PreparationSQL.Probe do
  use Ecto.Repo, otp_app: :preparation_sql, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.BrowserAuth.PreparationSQLTest do
  use ExUnit.Case, async: false

  alias MixerHosted.BrowserAuth.{
    ActivationPreparation,
    ActivationPreparationSchema,
    Catalog,
    StorageSchema
  }

  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.BrowserAuth.PreparationSQL.Probe

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @tables ~w(mixer_browser_sessions mixer_browser_session_vault mixer_browser_oidc_attempts mixer_browser_session_events mixer_authz_profiles mixer_authz_bindings mixer_authz_principals mixer_authz_families mixer_authz_credentials)

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_storage",
      pool_size: 1,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "browser_admin"]})

    start_supervised!(
      {Migration,
       Keyword.put(settings, :pool_size, 2) ++
         [
           username: "browser_admin",
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end
         ]}
    )

    start_supervised!(
      {Probe,
       settings ++
         [
           username: "browser_lifecycle",
           after_connect: fn c ->
             for sql <- [
                   "SET statement_timeout='5s'",
                   "SET lock_timeout='500ms'",
                   "SET idle_in_transaction_session_timeout='5s'",
                   "SET jit=off",
                   "SET search_path=pg_catalog",
                   "SET bytea_output=hex"
                 ],
                 do: Postgrex.query!(c, sql, [])
           end
         ]}
    )

    F.install!()

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)"
    )

    F.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES('person-1','human',true,0,1)")

    F.q!(
      Admin,
      "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)"
    )

    F.provision!()
    assert {:ok, :function_surface_verified} = admission()
    baseline = baseline_surface()
    install!()
    c = F.connection!()

    try do
      assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
               raw_prepare(c, F.random(), F.random(), F.random(), F.random(), 1, evidence())
    after
      GenServer.stop(c)
    end

    upgrade!()
    assert baseline_surface() == baseline
    assert_raise Catalog.Unavailable, fn -> admission() end

    File.write!(
      Path.join(
        System.fetch_env!("MIXER_ACTIVATION_PREPARATION_OUTPUT"),
        "baseline-admission.json"
      ),
      Jason.encode!(%{
        before: "function_surface_verified",
        inert_install_denied: true,
        after: "unavailable",
        baseline_functions: 18,
        baseline_composites: 3,
        unchanged_baseline_surface: true
      })
    )

    :ok
  end

  setup do
    c = F.connection!()
    admin = F.connection!("browser_admin")
    Postgrex.query!(admin, "SET session_replication_role=replica", [])

    on_exit(fn ->
      for conn <- [c, admin], do: if(Process.alive?(conn), do: GenServer.stop(conn))
    end)

    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, claimed} = F.claim(c, b, a)
    %{c: c, admin: admin, b: b, a: a, claim: claim, claimed: claimed}
  end

  test "exact six-field projection preserves the complete claimed snapshot and erased cipher",
       x do
    assert {:ok, %{rows: [[result]]}} = prepare(x)

    assert Enum.sort(Map.keys(result)) ==
             Enum.sort(
               ~w(version snapshot principal_id profile_revision binding_revision principal_revision)
             )

    assert result == %{
             "version" => 1,
             "snapshot" => x.claimed,
             "principal_id" => "person-1",
             "profile_revision" => 1,
             "binding_revision" => 1,
             "principal_revision" => 1
           }

    assert {:ok, decoded} = ActivationPreparation.decode(result)
    assert decoded.snapshot.attempt["status"] == "claimed"
    assert decoded.snapshot.attempt_envelope == nil
    assert decoded.snapshot.browser["cookie_digest"] == x.b.cookie
  end

  test "preparation grants no table reads, writer switching, ordinary execution or PUBLIC capability",
       x do
    for table <- @tables do
      assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
               Postgrex.query(x.c, "SELECT * FROM public.#{table} LIMIT 1", [])
    end

    assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
             Postgrex.query(x.c, "SET ROLE browser_writer", [])

    ordinary = F.connection!("browser_ordinary")

    try do
      assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
               raw_prepare(
                 ordinary,
                 x.b.cookie,
                 x.a.state,
                 x.b.config,
                 x.claim,
                 x.b.revision,
                 evidence()
               )
    after
      GenServer.stop(ordinary)
    end

    assert [[false, false]] =
             F.q!(
               Admin,
               "SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_proc p CROSS JOIN LATERAL pg_catalog.aclexplode(p.proacl) a WHERE p.oid='public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)'::regprocedure AND a.grantee=0), EXISTS(SELECT 1 FROM pg_catalog.pg_type t CROSS JOIN LATERAL pg_catalog.aclexplode(t.typacl) a WHERE t.oid='public.mixer_browser_access_evidence'::regtype AND a.grantee=0)"
             ).rows
  end

  test "reads create no effects or row locks and do not block canonical row writers", x do
    before = table_state()
    Postgrex.query!(x.c, "BEGIN", [])

    try do
      assert {:ok, _} = prepare(x)
      assert {:ok, %{rows: [[pid]]}} = Postgrex.query(x.c, "SELECT pg_backend_pid()", [])

      assert [[0]] =
               F.q!(
                 Admin,
                 "SELECT count(*) FROM pg_catalog.pg_locks WHERE pid=$1 AND (locktype='tuple' OR mode IN('RowShareLock','RowExclusiveLock','ExclusiveLock') AND relation IS NOT NULL)",
                 [pid]
               ).rows

      Postgrex.query!(x.admin, "BEGIN", [])

      for {table, predicate, values} <- [
            {"mixer_browser_sessions", "id=$1", [x.b.id]},
            {"mixer_browser_session_vault", "browser_id=$1", [x.b.id]},
            {"mixer_browser_oidc_attempts", "state_digest=$1", [x.a.state]},
            {"mixer_authz_profiles", "id='humans'", []},
            {"mixer_authz_bindings", "subject='subject-1'", []},
            {"mixer_authz_principals", "id='person-1'", []}
          ] do
        assert {:ok, _} =
                 Postgrex.query(
                   x.admin,
                   "SELECT * FROM public.#{table} WHERE #{predicate} FOR UPDATE NOWAIT",
                   values
                 )
      end

      Postgrex.query!(x.admin, "ROLLBACK", [])
    after
      Postgrex.query!(x.c, "ROLLBACK", [])
    end

    assert table_state() == before
  end

  for key <- [:profile, :version, :issuer, :subject, :client, :jti, :iat, :exp, :scopes] do
    @key key
    test "NULL access evidence #{key} fails closed before binding disclosure", x do
      deny(prepare(x, Map.put(evidence(), @key, nil)), "browser session unavailable")
    end
  end

  test "NULL composite and all missing or malformed claim/config/revision keys deny", x do
    assert {:error, %{postgres: %{message: "browser session unavailable"}}} =
             Postgrex.query(
               x.c,
               "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,NULL::public.mixer_browser_access_evidence)",
               [x.b.cookie, x.a.state, x.b.config, x.claim, x.b.revision]
             )

    base = [x.b.cookie, x.a.state, x.b.config, x.claim, x.b.revision]

    for index <- 0..4,
        value <-
          if(index == 4,
            do: [nil, 0, -1, 9_007_199_254_740_992],
            else: [nil, <<>>, F.random(31), F.random()]
          ) do
      [cookie, state, config, claim, revision] = List.replace_at(base, index, value)

      deny(
        raw_prepare(x.c, cookie, state, config, claim, revision, evidence()),
        "browser session unavailable"
      )
    end
  end

  test "text bounds are byte-based, including UTF8 and exact maximum verifier fields", x do
    for {key, max} <- [profile: 128, issuer: 2048, subject: 256, client: 256, jti: 256],
        value <- ["", String.duplicate("a", max + 1), String.duplicate("é", div(max, 2) + 1)] do
      deny(prepare(x, Map.put(evidence(), key, value)), "browser session unavailable")
    end

    assert {:ok, _} = prepare(x, %{evidence() | jti: String.duplicate("j", 256)})
    deny(prepare(x, %{evidence() | version: 0}), "browser session unavailable")
    deny(prepare(x, %{evidence() | version: -1}), "browser session unavailable")

    assert {:error, %{postgres: %{code: :character_not_in_repertoire}}} =
             prepare(x, %{evidence() | subject: "a" <> <<0>> <> "b"})
  end

  test "scope NULLs, empty words, ASCII grammar, duplicates, cardinality and aggregate bounds deny",
       x do
    for scopes <- [
          [],
          [nil],
          ["mixer.workspace.read", nil],
          ["other"],
          ["mixer.workspace.read", ""],
          ["mixer.workspace.read", "two words"],
          ["mixer.workspace.read", "é"],
          ["mixer.workspace.read", "q\""],
          ["mixer.workspace.read", "back\\slash"],
          ["mixer.workspace.read", "mixer.workspace.read"],
          ["mixer.workspace.read", String.duplicate("x", 1025)],
          ["mixer.workspace.read", String.duplicate("x", 1004)],
          ["mixer.workspace.read" | Enum.map(1..64, &"scope#{&1}")]
        ] do
      deny(prepare(x, %{evidence() | scopes: scopes}), "browser session unavailable")
    end

    assert {:ok, _} =
             prepare(x, %{
               evidence()
               | scopes: [
                   "mixer.workspace.read",
                   "mixer.audit.read",
                   "mixer.artifact.read",
                   "mixer.artifact.upload"
                 ]
             })

    assert {:ok, _} =
             prepare(x, %{
               evidence()
               | scopes: ["mixer.workspace.read", String.duplicate("x", 1003)]
             })

    assert {:ok, _} =
             prepare(x, %{
               evidence()
               | scopes: ["mixer.workspace.read" | Enum.map(1..63, &"s#{&1}")]
             })

    for expression <- [
          "'[0:0]={mixer.workspace.read}'::text[]",
          "ARRAY[['mixer.workspace.read']]::text[]"
        ] do
      deny(prepare_scope_expression(x, expression), "browser session unavailable")
    end
  end

  test "numeric dates permit zero and reject overflow, future skew, equality and human lifetime excess",
       x do
    n = F.now()

    for {key, value} <- [
          iat: -1,
          iat: 9_007_199_254_740_992,
          exp: -1,
          exp: 9_007_199_254_740_992,
          iat: n + 31,
          exp: n,
          exp: n - 1,
          exp: evidence().iat + 901
        ] do
      deny(prepare(x, Map.put(evidence(), key, value)), "browser session unavailable")
    end

    assert {:ok, _} = prepare(x, %{evidence() | iat: n + 30, exp: n + 600})
    assert {:ok, _} = prepare(x, %{evidence() | iat: n, exp: n + 900})
    # Zero is an admitted NumericDate, but cannot describe a currently live
    # human token with a <=900 second lifetime at this real database time.
    deny(prepare(x, %{evidence() | iat: 0, exp: 900}), "browser session unavailable")
  end

  test "unknown binding is disclosed only after exact live same-browser claim and matching human profile",
       x do
    unknown = %{evidence() | subject: "never-bound"}
    deny(prepare(x, unknown), "browser onboarding required")

    deny(
      raw_prepare(x.c, x.b.cookie, x.a.state, x.b.config, F.random(), x.b.revision, unknown),
      "browser session unavailable"
    )

    other = F.bootstrap(x.c)

    deny(
      raw_prepare(x.c, other.cookie, x.a.state, other.config, x.claim, other.revision, unknown),
      "browser session unavailable"
    )

    drift(x, "mixer_authz_profiles", "id='humans'", [], "active", false, fn ->
      deny(prepare(x, unknown), "browser identity unavailable")
    end)

    assert [[0]] =
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_authz_bindings WHERE subject='never-bound'"
             ).rows
  end

  test "pending, consumed, foreign and drifted claim linkage all deny", x do
    for {column, value} <- [
          {"status", "pending"},
          {"browser_epoch", x.b.revision + 1},
          {"browser_revision", x.b.revision + 1},
          {"browser_id", F.random(16)},
          {"cookie_digest", F.random()},
          {"config_digest", F.random()},
          {"generation", F.token()},
          {"claim_digest", F.random()},
          {"profile_id", "other"},
          {"profile_version", 2},
          {"issuer", "https://other.fixture"},
          {"client_id", "other"},
          {"redirect_uri", ""}
        ] do
      if column == "status" do
        # A legal consumed tombstone avoids weakening the ordinary CHECKs.
        drift_sql(
          x,
          "UPDATE public.mixer_browser_oidc_attempts SET status='failed',completion_reason='session_failed' WHERE state_digest=$1",
          [x.a.state],
          "UPDATE public.mixer_browser_oidc_attempts SET status='claimed',completion_reason=NULL WHERE state_digest=$1",
          [x.a.state],
          fn -> deny(prepare(x), "browser session unavailable") end
        )
      else
        if column == "redirect_uri" do
          # The table's ordinary bound already rejects an empty saved redirect.
          assert {:error, %{postgres: %{code: :check_violation}}} =
                   Postgrex.query(
                     x.admin,
                     "UPDATE public.mixer_browser_oidc_attempts SET redirect_uri='' WHERE state_digest=$1",
                     [x.a.state]
                   )
        else
          drift(
            x,
            "mixer_browser_oidc_attempts",
            "state_digest=$1",
            [x.a.state],
            column,
            value,
            fn -> deny(prepare(x), "browser session unavailable") end
          )
        end
      end
    end

    {b, a} = F.begin_login(x.c, F.bootstrap(x.c))

    deny(
      raw_prepare(x.c, b.cookie, a.state, b.config, F.random(), b.revision, evidence()),
      "browser session unavailable"
    )
  end

  test "browser and vault linkage/config/revision drift fails closed", x do
    for {table, column, value} <- [
          {"mixer_browser_sessions", "config_digest", F.random()},
          {"mixer_browser_sessions", "generation", F.token()},
          {"mixer_browser_sessions", "expected_profile_id", "other"},
          {"mixer_browser_sessions", "expected_profile_version", 2},
          {"mixer_browser_session_vault", "epoch", x.b.revision + 1},
          {"mixer_browser_session_vault", "session_revision", x.b.revision + 1},
          {"mixer_browser_session_vault", "envelope_kind", "active"}
        ] do
      predicate = if table == "mixer_browser_sessions", do: "id=$1", else: "browser_id=$1"

      drift(x, table, predicate, [x.b.id], column, value, fn ->
        deny(prepare(x), "browser session unavailable")
      end)
    end
  end

  test "profile, binding and principal current fences fail closed", x do
    for {table, predicate, column, value} <- [
          {"mixer_authz_profiles", "id='humans'", "active", false},
          {"mixer_authz_profiles", "id='humans'", "issuer", "https://other.fixture"},
          {"mixer_authz_profiles", "id='humans'", "client_id", "other"},
          {"mixer_authz_bindings", "subject='subject-1'", "active", false},
          {"mixer_authz_principals", "id='person-1'", "active", false},
          {"mixer_authz_principals", "id='person-1'", "not_before", F.now() + 1},
          {"mixer_authz_principals", "id='person-1'", "not_before", evidence().iat + 1}
        ] do
      drift(x, table, predicate, [], column, value, fn ->
        deny(prepare(x), "browser identity unavailable")
      end)
    end

    # Switching every related identity class preserves FKs yet still denies.
    drift_sql(
      x,
      "UPDATE public.mixer_authz_profiles SET identity_class='service' WHERE id='humans'",
      [],
      "UPDATE public.mixer_authz_profiles SET identity_class='human' WHERE id='humans'",
      [],
      fn -> deny(prepare(x), "browser identity unavailable") end
    )
  end

  test "NULL stored security fields fail closed even in a deliberately weakened test-only schema",
       x do
    for {table, key, params, column, error} <- [
          {"mixer_browser_sessions", "id=$1", [x.b.id], "absolute_expires_at",
           "browser session unavailable"},
          {"mixer_browser_sessions", "id=$1", [x.b.id], "idle_expires_at",
           "browser session unavailable"},
          {"mixer_browser_session_vault", "browser_id=$1", [x.b.id], "vault_generation",
           "browser session unavailable"},
          {"mixer_browser_oidc_attempts", "state_digest=$1", [x.a.state], "expires_at",
           "browser session unavailable"},
          {"mixer_browser_oidc_attempts", "state_digest=$1", [x.a.state], "claim_expires_at",
           "browser session unavailable"},
          {"mixer_authz_profiles", "id='humans'", [], "state_revision",
           "browser identity unavailable"},
          {"mixer_authz_bindings", "subject='subject-1'", [], "revision",
           "browser identity unavailable"},
          {"mixer_authz_principals", "id='person-1'", [], "revision",
           "browser identity unavailable"},
          {"mixer_authz_principals", "id='person-1'", [], "not_before",
           "browser identity unavailable"}
        ] do
      null_drift(x, table, key, params, column, fn -> deny(prepare(x), error) end)
    end
  end

  test "NULL linkage, status, identity class and activity fields cannot bypass SQL boolean checks",
       x do
    for {table, key, params, columns, error} <- [
          {"mixer_browser_sessions", "id=$1", [x.b.id],
           ~w(status epoch generation config_digest expected_profile_id expected_profile_version),
           "browser session unavailable"},
          {"mixer_browser_session_vault", "browser_id=$1", [x.b.id],
           ~w(epoch session_revision envelope_kind ciphertext_version),
           "browser session unavailable"},
          {"mixer_browser_oidc_attempts", "state_digest=$1", [x.a.state],
           ~w(status browser_epoch browser_revision cookie_digest generation config_digest claim_digest claimed_at profile_id profile_version issuer client_id redirect_uri return_route),
           "browser session unavailable"},
          {"mixer_authz_profiles", "id='humans'", [], ~w(active identity_class issuer client_id),
           "browser identity unavailable"},
          {"mixer_authz_bindings", "subject='subject-1'", [],
           ~w(active identity_class principal_id), "browser identity unavailable"},
          {"mixer_authz_principals", "id='person-1'", [], ~w(active identity_class),
           "browser identity unavailable"}
        ],
        column <- columns do
      null_drift(x, table, key, params, column, fn -> deny(prepare(x), error) end)
    end
  end

  test "missing profile or principal denies without identity creation", x do
    for {table, predicate} <- [
          {"mixer_authz_profiles", "id='humans'"},
          {"mixer_authz_principals", "id='person-1'"}
        ] do
      [[row]] =
        Postgrex.query!(
          x.admin,
          "SELECT to_jsonb(t) FROM public.#{table} t WHERE #{predicate}",
          []
        ).rows

      Postgrex.query!(x.admin, "DELETE FROM public.#{table} WHERE #{predicate}", [])

      try do
        deny(prepare(x), "browser identity unavailable")

        assert [[0]] =
                 Postgrex.query!(
                   x.admin,
                   "SELECT count(*) FROM public.#{table} WHERE #{predicate}",
                   []
                 ).rows
      after
        Postgrex.query!(
          x.admin,
          "INSERT INTO public.#{table} SELECT (pg_catalog.jsonb_populate_record(NULL::public.#{table},$1)).*",
          [row]
        )
      end
    end
  end

  test "STRICT bounded projection denies duplicate tuples even after test-only unique-key weakening",
       x do
    [[original]] =
      Postgrex.query!(
        x.admin,
        "SELECT ctid::text FROM public.mixer_authz_bindings WHERE subject='subject-1'",
        []
      ).rows

    Postgrex.query!(
      x.admin,
      "ALTER TABLE public.mixer_authz_bindings DROP CONSTRAINT mixer_authz_bindings_pkey",
      []
    )

    try do
      Postgrex.query!(
        x.admin,
        "INSERT INTO public.mixer_authz_bindings SELECT * FROM public.mixer_authz_bindings WHERE subject='subject-1'",
        []
      )

      deny(prepare(x), "browser session unavailable")
    after
      Postgrex.query!(
        x.admin,
        "DELETE FROM public.mixer_authz_bindings WHERE subject='subject-1' AND ctid<>$1::text::tid",
        [original]
      )

      Postgrex.query!(
        x.admin,
        "ALTER TABLE public.mixer_authz_bindings ADD CONSTRAINT mixer_authz_bindings_pkey PRIMARY KEY(profile_id,profile_version,subject)",
        []
      )
    end

    assert {:ok, _} = prepare(x)
  end

  test "expired claim denies before missing-binding disclosure at deadline equality", x do
    deadline = F.now() + 1

    drift_sql(
      x,
      "UPDATE public.mixer_browser_oidc_attempts SET claim_expires_at=$2 WHERE state_digest=$1",
      [x.a.state, deadline],
      "UPDATE public.mixer_browser_oidc_attempts SET claim_expires_at=$2 WHERE state_digest=$1",
      [x.a.state, x.claimed["attempt"]["claim_expires_at"]],
      fn ->
        Process.sleep(max(deadline * 1000 - System.system_time(:millisecond), 0))
        deny(prepare(x, %{evidence() | subject: "never-bound"}), "browser session unavailable")
      end
    )
  end

  test "fresh post-projection time rejects token expiring during a relation lock wait", x do
    deadline = F.now() + 1
    Postgrex.query!(x.admin, "BEGIN", [])

    Postgrex.query!(
      x.admin,
      "LOCK TABLE public.mixer_authz_profiles IN ACCESS EXCLUSIVE MODE",
      []
    )

    try do
      Process.sleep(max(deadline * 1000 - System.system_time(:millisecond) - 170, 0))

      task =
        Task.async(fn ->
          conn = F.connection!()

          try do
            raw_prepare(conn, x.b.cookie, x.a.state, x.b.config, x.claim, x.b.revision, %{
              evidence()
              | exp: deadline
            })
          after
            GenServer.stop(conn)
          end
        end)

      Process.sleep(240)
      Postgrex.query!(x.admin, "ROLLBACK", [])
      deny(Task.await(task, 2000), "browser session unavailable")
    after
      Postgrex.query!(x.admin, "ROLLBACK", [])
    end
  end

  test "preparation revisions do not authorize activation after intervening principal, binding or profile drift",
       x do
    for {table, key, revision} <- [
          {"mixer_authz_profiles", "id='humans'", "state_revision"},
          {"mixer_authz_bindings", "subject='subject-1'", "revision"},
          {"mixer_authz_principals", "id='person-1'", "revision"}
        ] do
      assert {:ok, %{rows: [[projection]]}} = prepare(x)

      i = %{
        F.identity()
        | profile_revision: projection["profile_revision"],
          binding_revision: projection["binding_revision"],
          principal_revision: projection["principal_revision"]
      }

      drift(x, table, key, [], revision, 2, fn ->
        assert {{:error, :raise_exception}, _, _, _, _} = F.activate(x.c, x.b, x.a, x.claim, i)
        assert {:ok, %{rows: [[fresh]]}} = prepare(x)
        assert fresh != projection
      end)
    end

    assert {:ok, %{rows: [[projection]]}} = prepare(x)

    i = %{
      F.identity()
      | profile_revision: projection["profile_revision"],
        binding_revision: projection["binding_revision"],
        principal_revision: projection["principal_revision"]
    }

    assert {{:ok, active}, _, _, _, _} = F.activate(x.c, x.b, x.a, x.claim, i)
    assert active["browser"]["status"] == "active"
    deny(prepare(x), "browser session unavailable")
  end

  test "read snapshot sees committed old state without waiting for uncommitted principal revocation; activate subsequently denies",
       x do
    Postgrex.query!(x.admin, "BEGIN", [])

    Postgrex.query!(
      x.admin,
      "UPDATE public.mixer_authz_principals SET active=false,revision=2 WHERE id='person-1'",
      []
    )

    try do
      assert {:ok, %{rows: [[projection]]}} = prepare(x)
      Postgrex.query!(x.admin, "COMMIT", [])
      i = %{F.identity() | principal_revision: projection["principal_revision"]}
      assert {{:error, :raise_exception}, _, _, _, _} = F.activate(x.c, x.b, x.a, x.claim, i)
    after
      Postgrex.query!(x.admin, "ROLLBACK", [])

      Postgrex.query!(
        x.admin,
        "UPDATE public.mixer_authz_principals SET active=true,revision=1 WHERE id='person-1'",
        []
      )
    end
  end

  test "positive53 metadata upper bounds survive projection and decode", x do
    max = 9_007_199_254_740_991

    drift(x, "mixer_authz_profiles", "id='humans'", [], "state_revision", max, fn ->
      drift(x, "mixer_authz_bindings", "subject='subject-1'", [], "revision", max, fn ->
        drift(x, "mixer_authz_principals", "id='person-1'", [], "revision", max, fn ->
          assert {:ok, %{rows: [[projection]]}} = prepare(x)

          assert {:ok,
                  %ActivationPreparation{
                    profile_revision: ^max,
                    binding_revision: ^max,
                    principal_revision: ^max
                  }} = ActivationPreparation.decode(projection)
        end)
      end)
    end)
  end

  test "additive manifest binds exact installed source, settings, signature, type fields and decoder",
       _x do
    m = ActivationPreparationSchema.catalog_manifest()
    assert m.version == 2 and m.baseline_version == 1 and m.additive_only
    assert map_size(m.functions) == 1 and map_size(m.composites) == 1
    assert map_size(StorageSchema.signatures()) == 18
    helper = m.functions["mixer_browser_prepare_activation"]

    assert [
             [
               helper.source,
               helper.settings,
               true,
               "browser_writer",
               "jsonb",
               helper.argument_names
             ]
           ] ==
             F.q!(
               Admin,
               "SELECT prosrc,proconfig,prosecdef,pg_get_userbyid(proowner),pg_get_function_result(oid),proargnames FROM pg_catalog.pg_proc WHERE oid='public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)'::regprocedure"
             ).rows

    fields =
      F.q!(
        Admin,
        "SELECT a.attname::text,format_type(a.atttypid,a.atttypmod) FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_type t ON t.typrelid=a.attrelid WHERE t.oid='public.mixer_browser_access_evidence'::regtype AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum"
      ).rows

    assert fields ==
             Enum.map(m.composites["mixer_browser_access_evidence"], fn {name, type} ->
               [name, type]
             end)

    source =
      Path.expand("../../hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex", __DIR__)
      |> File.read!()

    assert m.decoder.source_sha256 == Base.encode16(:crypto.hash(:sha256, source), case: :lower)
    assert_raise Catalog.Unavailable, fn -> admission() end
  end

  test "upgrade failure rolls back temporary CREATE, ownership and grants; down/reapply preserves every baseline object",
       x do
    baseline = baseline_surface()

    for sql <- ActivationPreparationSchema.rollback_statements(),
        do: Postgrex.query!(x.admin, sql, [])

    assert baseline_surface() == baseline
    assert {:ok, :function_surface_verified} = admission()
    install!()

    plan =
      ActivationPreparationSchema.provisioning_statements(
        "browser_writer",
        "browser_lifecycle",
        "browser_schema_owner"
      )

    # Fail immediately after CREATE grant and ownership transfer, before revoke.
    for sql <- Enum.take(plan, 7), do: Postgrex.query!(x.admin, sql, [])
    assert {:error, _} = Postgrex.query(x.admin, "SELECT 1/0", [])
    Postgrex.query!(x.admin, "ROLLBACK", [])

    assert [[false, "browser_schema_owner", false]] =
             F.q!(
               Admin,
               "SELECT has_schema_privilege('browser_writer','public','CREATE'),pg_get_userbyid(proowner),has_function_privilege('browser_lifecycle',oid,'EXECUTE') FROM pg_catalog.pg_proc WHERE oid='public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)'::regprocedure"
             ).rows

    upgrade!()
    assert baseline_surface() == baseline

    assert [[false, "browser_writer"]] =
             F.q!(
               Admin,
               "SELECT has_schema_privilege('browser_writer','public','CREATE'),pg_get_userbyid(proowner) FROM pg_catalog.pg_proc WHERE oid='public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence)'::regprocedure"
             ).rows

    assert {:ok, _} = prepare(x)
  end

  test "upgrade preflight rejects dirty role privilege topology without changing baseline", x do
    baseline = baseline_surface()
    # Already-provisioned extension is deliberately not replayable.
    plan =
      ActivationPreparationSchema.provisioning_statements(
        "browser_writer",
        "browser_lifecycle",
        "browser_schema_owner"
      )

    for sql <- Enum.take(plan, 4), do: Postgrex.query!(x.admin, sql, [])

    assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
             Postgrex.query(x.admin, Enum.at(plan, 4), [])

    Postgrex.query!(x.admin, "ROLLBACK", [])
    assert baseline_surface() == baseline

    for names <- [
          {"browser_writer", "browser_writer", "browser_schema_owner"},
          {"public", "browser_lifecycle", "browser_schema_owner"},
          {"pg_bad", "browser_lifecycle", "browser_schema_owner"},
          {"a;DROP ROLE x", "browser_lifecycle", "browser_schema_owner"}
        ] do
      assert_raise ArgumentError, fn ->
        apply(ActivationPreparationSchema, :provisioning_statements, Tuple.to_list(names))
      end
    end
  end

  test "one statement snapshot cannot mix revisions from concurrently committed authorization generations",
       x do
    parent = self()

    writer =
      Task.async(fn ->
        c = F.connection!("browser_admin")
        Postgrex.query!(c, "SET session_replication_role=replica", [])
        send(parent, :revision_writer_ready)

        receive do
          :run -> :ok
        end

        try do
          for n <- 1..50 do
            revision = if rem(n, 2) == 0, do: 1, else: 2
            Postgrex.query!(c, "BEGIN", [])

            Postgrex.query!(
              c,
              "UPDATE public.mixer_authz_profiles SET state_revision=$1 WHERE id='humans'",
              [revision]
            )

            Postgrex.query!(
              c,
              "UPDATE public.mixer_authz_bindings SET revision=$1 WHERE subject='subject-1'",
              [revision]
            )

            Postgrex.query!(
              c,
              "UPDATE public.mixer_authz_principals SET revision=$1 WHERE id='person-1'",
              [revision]
            )

            Postgrex.query!(c, "COMMIT", [])
          end
        after
          GenServer.stop(c)
        end
      end)

    assert_receive :revision_writer_ready
    send(writer.pid, :run)

    try do
      for _ <- 1..60 do
        assert {:ok, %{rows: [[projection]]}} = prepare(x)
        assert projection["profile_revision"] in [1, 2]
        assert projection["profile_revision"] == projection["binding_revision"]
        assert projection["binding_revision"] == projection["principal_revision"]
        assert projection["snapshot"] == x.claimed
      end

      Task.await(writer, 5000)
    after
      if Process.alive?(writer.pid), do: Task.shutdown(writer, :brutal_kill)

      for {table, column} <- [
            {"profiles", "state_revision"},
            {"bindings", "revision"},
            {"principals", "revision"}
          ],
          do: Postgrex.query!(x.admin, "UPDATE public.mixer_authz_#{table} SET #{column}=1", [])
    end
  end

  for deadline_kind <- [:absolute, :idle, :attempt] do
    @deadline_kind deadline_kind
    test "#{deadline_kind} expiry equality denies a valid same-browser claim before unknown binding disclosure",
         x do
      deadline = F.now() + 1

      {sql, restore, params, original} =
        case @deadline_kind do
          :absolute ->
            {"UPDATE public.mixer_browser_sessions SET idle_expires_at=$2,absolute_expires_at=$2 WHERE id=$1",
             "UPDATE public.mixer_browser_sessions SET idle_expires_at=$2,absolute_expires_at=$2 WHERE id=$1",
             [x.b.id, deadline], [x.b.id, x.claimed["browser"]["absolute_expires_at"]]}

          :idle ->
            {"UPDATE public.mixer_browser_sessions SET idle_expires_at=$2 WHERE id=$1",
             "UPDATE public.mixer_browser_sessions SET idle_expires_at=$2 WHERE id=$1",
             [x.b.id, deadline], [x.b.id, x.claimed["browser"]["idle_expires_at"]]}

          :attempt ->
            {"UPDATE public.mixer_browser_oidc_attempts SET expires_at=$2 WHERE state_digest=$1",
             "UPDATE public.mixer_browser_oidc_attempts SET expires_at=$2 WHERE state_digest=$1",
             [x.a.state, deadline], [x.a.state, x.claimed["attempt"]["expires_at"]]}
        end

      # The ordinary attempt CHECK also binds claim_expires_at <= expires_at.
      # This test isolates the attempt expiry guard by lowering only expires_at;
      # remove/restore its dependent CHECK in this disposable test database.
      checks =
        if @deadline_kind == :attempt,
          do:
            Postgrex.query!(
              x.admin,
              "SELECT conname::text,pg_get_constraintdef(oid) FROM pg_catalog.pg_constraint WHERE conrelid='public.mixer_browser_oidc_attempts'::regclass AND contype='c' AND pg_get_constraintdef(oid) LIKE '%claim_expires_at%'",
              []
            ).rows,
          else: []

      for [name, _] <- checks,
          do:
            Postgrex.query!(
              x.admin,
              "ALTER TABLE public.mixer_browser_oidc_attempts DROP CONSTRAINT #{name}",
              []
            )

      try do
        drift_sql(x, sql, params, restore, original, fn ->
          Process.sleep(max(deadline * 1000 - System.system_time(:millisecond), 0))
          deny(prepare(x, %{evidence() | subject: "never-bound"}), "browser session unavailable")
        end)
      after
        for [name, definition] <- checks,
            do:
              Postgrex.query!(
                x.admin,
                "ALTER TABLE public.mixer_browser_oidc_attempts ADD CONSTRAINT #{name} #{definition}",
                []
              )
      end
    end
  end

  test "maximum stored text and profile version bounds produce a decoder-compatible projection",
       x do
    profile = String.duplicate("p", 128)
    principal = String.duplicate("h", 128)
    subject = String.duplicate("s", 256)

    issuer =
      "https://issuer.fixture/" <>
        String.duplicate("a", 2048 - byte_size("https://issuer.fixture/"))

    client = String.duplicate("c", 256)
    version = 2_147_483_647

    F.q!(Admin, "INSERT INTO public.mixer_authz_profiles VALUES($1,$2,$3,$4,'human',true,1)", [
      profile,
      version,
      issuer,
      client
    ])

    F.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES($1,'human',true,0,1)", [
      principal
    ])

    F.q!(Admin, "INSERT INTO public.mixer_authz_bindings VALUES($1,$2,$3,'human',$4,true,1)", [
      profile,
      version,
      subject,
      principal
    ])

    b = %{id: F.random(16), cookie: F.random(), config: F.random(), csrf: F.random(), revision: 1}

    assert {:ok, _} =
             F.call(x.c, :bootstrap, [
               b.id,
               b.cookie,
               F.token(),
               b.csrf,
               b.config,
               profile,
               version,
               F.now() + 250,
               {:cipher, F.cipher()},
               F.request()
             ])

    a = %{
      state: F.random(),
      nonce: F.random(),
      profile: profile,
      issuer: issuer,
      client: client,
      redirect:
        "https://console.fixture/" <>
          String.duplicate("r", 2048 - byte_size("https://console.fixture/")),
      expires: F.now() + 150,
      cipher: F.cipher()
    }

    {sql, values} =
      F.query(:begin, [
        b.cookie,
        b.csrf,
        b.config,
        1,
        {:attempt, a},
        {:cipher, F.cipher()},
        F.request()
      ])

    assert {:ok, _} = Postgrex.query(x.c, sql, List.replace_at(values, 7, version))
    b = %{b | revision: 2}
    {claim, _} = F.claim(x.c, b, a)

    i = %{
      evidence()
      | profile: profile,
        version: version,
        subject: subject,
        issuer: issuer,
        client: client,
        jti: String.duplicate("j", 256)
    }

    assert {:ok, %{rows: [[result]]}} =
             raw_prepare(x.c, b.cookie, a.state, b.config, claim, b.revision, i)

    assert result["principal_id"] == principal
    assert {:ok, _} = ActivationPreparation.decode(result)
  end

  test "inactive or wrong-class bindings and principals cannot become onboarding or provisional authority",
       x do
    for {table, predicate, column, value} <- [
          {"mixer_authz_bindings", "subject='subject-1'", "identity_class", "service"},
          {"mixer_authz_principals", "id='person-1'", "identity_class", "service"}
        ] do
      drift(x, table, predicate, [], column, value, fn ->
        deny(prepare(x), "browser identity unavailable")
      end)
    end

    assert [[0]] =
             F.q!(
               Admin,
               "SELECT count(*) FROM public.mixer_authz_bindings WHERE subject IN('SUBJECT-1','subject-1@issuer.fixture')"
             ).rows

    for subject <- ["SUBJECT-1", "subject-1@issuer.fixture"],
        do: deny(prepare(x, %{evidence() | subject: subject}), "browser onboarding required")
  end

  test "upgrade preflight rejects pre-existing CREATE, unsafe flags, memberships, login reads and wrong type owner",
       x do
    baseline = baseline_surface()

    for sql <- ActivationPreparationSchema.rollback_statements(),
        do: Postgrex.query!(x.admin, sql, [])

    install!()

    plan =
      ActivationPreparationSchema.provisioning_statements(
        "browser_writer",
        "browser_lifecycle",
        "browser_schema_owner"
      )

    for {change, restore} <- [
          {"GRANT CREATE ON SCHEMA public TO browser_writer",
           "REVOKE CREATE ON SCHEMA public FROM browser_writer"},
          {"ALTER ROLE browser_writer INHERIT", "ALTER ROLE browser_writer NOINHERIT"},
          {"ALTER ROLE browser_lifecycle BYPASSRLS", "ALTER ROLE browser_lifecycle NOBYPASSRLS"},
          {"ALTER ROLE browser_schema_owner LOGIN", "ALTER ROLE browser_schema_owner NOLOGIN"},
          {"GRANT browser_ordinary TO browser_writer",
           "REVOKE browser_ordinary FROM browser_writer"},
          {"GRANT SELECT ON public.mixer_authz_profiles TO browser_lifecycle",
           "REVOKE SELECT ON public.mixer_authz_profiles FROM browser_lifecycle"},
          {"ALTER TYPE public.mixer_browser_access_evidence OWNER TO browser_admin",
           "ALTER TYPE public.mixer_browser_access_evidence OWNER TO browser_schema_owner"}
        ] do
      Postgrex.query!(x.admin, change, [])

      try do
        for sql <- Enum.take(plan, 4), do: Postgrex.query!(x.admin, sql, [])

        assert {:error, %{postgres: %{code: :insufficient_privilege}}} =
                 Postgrex.query(x.admin, Enum.at(plan, 4), [])
      after
        Postgrex.query!(x.admin, "ROLLBACK", [])
        Postgrex.query!(x.admin, restore, [])
      end
    end

    upgrade!()
    assert baseline_surface() == baseline
    assert {:ok, _} = prepare(x)
  end

  defp evidence do
    Map.put(F.identity(), :version, 1)
  end

  defp prepare(x, i \\ evidence()),
    do: raw_prepare(x.c, x.b.cookie, x.a.state, x.b.config, x.claim, x.b.revision, i)

  defp raw_prepare(c, cookie, state, config, claim, revision, i) do
    Postgrex.query(
      c,
      "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,ROW($6,$7,$8,$9,$10,$11,$12,$13,$14)::public.mixer_browser_access_evidence)",
      [
        cookie,
        state,
        config,
        claim,
        revision,
        i.profile,
        i.version,
        i.issuer,
        i.subject,
        i.client,
        i.jti,
        i.iat,
        i.exp,
        i.scopes
      ],
      timeout: 5000,
      queue: false
    )
  end

  defp prepare_scope_expression(x, expression) do
    i = evidence()

    Postgrex.query(
      x.c,
      "SELECT public.mixer_browser_prepare_activation($1,$2,$3,$4,$5,ROW($6,$7,$8,$9,$10,$11,$12,$13,#{expression})::public.mixer_browser_access_evidence)",
      [
        x.b.cookie,
        x.a.state,
        x.b.config,
        x.claim,
        x.b.revision,
        i.profile,
        i.version,
        i.issuer,
        i.subject,
        i.client,
        i.jti,
        i.iat,
        i.exp
      ]
    )
  end

  defp deny(result, message),
    do:
      assert(
        match?({:error, %{postgres: %{code: :raise_exception, message: ^message}}}, result),
        inspect(result)
      )

  defp install! do
    c = F.connection!("browser_admin")

    try do
      Postgrex.query!(c, "SET ROLE browser_schema_owner", [])
      for sql <- ActivationPreparationSchema.statements(), do: Postgrex.query!(c, sql, [])
    after
      GenServer.stop(c)
    end
  end

  defp upgrade! do
    c = F.connection!("browser_admin")

    try do
      for sql <-
            ActivationPreparationSchema.provisioning_statements(
              "browser_writer",
              "browser_lifecycle",
              "browser_schema_owner"
            ),
          do: Postgrex.query!(c, sql, [])
    after
      Postgrex.query(c, "ROLLBACK", [])
      GenServer.stop(c)
    end
  end

  defp admission,
    do:
      Probe.transaction(
        fn ->
          Catalog.check_function_surface!(
            Probe,
            @roles,
            System.monotonic_time(:millisecond) + 5000
          )
        end,
        timeout: 5000,
        queue: false
      )

  defp baseline_surface do
    %{
      functions:
        F.q!(
          Admin,
          "SELECT p.proname::text,p.oid::bigint,p.proowner::bigint,p.proacl::text,p.prosrc,p.proconfig FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND left(p.proname::text,14)='mixer_browser_' AND p.proname<>'mixer_browser_prepare_activation' ORDER BY p.oid"
        ).rows,
      types:
        F.q!(
          Admin,
          "SELECT typname::text,typowner::bigint,typacl::text FROM pg_catalog.pg_type WHERE typname IN('mixer_browser_cipher','mixer_browser_attempt','mixer_browser_verified') ORDER BY typname"
        ).rows,
      tables:
        F.q!(
          Admin,
          "SELECT c.relname::text,c.relowner::bigint,c.relacl::text FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname"
        ).rows,
      policies:
        F.q!(
          Admin,
          "SELECT polrelid::bigint,polname::text,polroles::text,polqual::text,polwithcheck::text FROM pg_catalog.pg_policy ORDER BY polrelid,polname"
        ).rows
    }
  end

  defp table_state,
    do:
      Map.new(@tables, fn table ->
        {table,
         F.q!(Admin, "SELECT to_jsonb(t)::text FROM public.#{table} t ORDER BY to_jsonb(t)::text").rows}
      end)

  defp drift(x, table, predicate, params, column, value, fun) do
    [[old]] =
      Postgrex.query!(x.admin, "SELECT #{column} FROM public.#{table} WHERE #{predicate}", params).rows

    n = length(params) + 1

    Postgrex.query!(
      x.admin,
      "UPDATE public.#{table} SET #{column}=$#{n} WHERE #{predicate}",
      params ++ [value]
    )

    try do
      fun.()
    after
      Postgrex.query!(
        x.admin,
        "UPDATE public.#{table} SET #{column}=$#{n} WHERE #{predicate}",
        params ++ [old]
      )
    end
  end

  defp drift_sql(x, sql, params, restore, restore_params, fun) do
    Postgrex.query!(x.admin, sql, params)

    try do
      fun.()
    after
      Postgrex.query!(x.admin, restore, restore_params)
    end
  end

  defp null_drift(x, table, predicate, params, column, fun) do
    [[not_null]] =
      Postgrex.query!(
        x.admin,
        "SELECT attnotnull FROM pg_catalog.pg_attribute WHERE attrelid=$1::text::regclass AND attname=$2",
        ["public." <> table, column]
      ).rows

    checks =
      Postgrex.query!(
        x.admin,
        "SELECT c.conname::text,pg_get_constraintdef(c.oid) FROM pg_catalog.pg_constraint c JOIN pg_catalog.pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey) WHERE c.conrelid=$1::text::regclass AND c.contype='c' AND a.attname=$2",
        ["public." <> table, column]
      ).rows

    for [name, _definition] <- checks,
        do: Postgrex.query!(x.admin, "ALTER TABLE public.#{table} DROP CONSTRAINT #{name}", [])

    if not_null,
      do:
        Postgrex.query!(
          x.admin,
          "ALTER TABLE public.#{table} ALTER COLUMN #{column} DROP NOT NULL",
          []
        )

    try do
      drift(x, table, predicate, params, column, nil, fun)
    after
      for [name, definition] <- checks,
          do:
            Postgrex.query!(
              x.admin,
              "ALTER TABLE public.#{table} ADD CONSTRAINT #{name} #{definition}",
              []
            )

      if not_null,
        do:
          Postgrex.query!(
            x.admin,
            "ALTER TABLE public.#{table} ALTER COLUMN #{column} SET NOT NULL",
            []
          )
    end
  end
end
