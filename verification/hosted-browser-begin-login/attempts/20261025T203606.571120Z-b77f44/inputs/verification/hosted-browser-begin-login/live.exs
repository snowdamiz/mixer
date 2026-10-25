Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Application.ensure_all_started(:jose)

defmodule PreauthFixture.Admin do
  use Ecto.Repo, otp_app: :preauth_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule PreauthFixture do
  @compile {:no_warn_undefined, BeginControls}
  alias MixerHosted.BrowserAuth.{Catalog, Config, ConfigurationDigest, Custody, LifecycleRepo}

  alias MixerHosted.BrowserAuth.{
    PreauthDraft,
    Protocol,
    RelationCatalog,
    RuntimeConfig,
    RuntimeOwner,
    Store
  }

  alias MixerHosted.Identity.{KeyOwner, StartupConfig}

  @roles %{
    lifecycle_login: "browser_lifecycle",
    writer: "browser_writer",
    relation_owner: "browser_schema_owner",
    ordinary_runtime_login: "browser_ordinary"
  }
  @metadata %{request_id: String.duplicate("a", 32)}

  def assert(true), do: :ok
  def assert(_), do: raise("bounded preauthentication assertion failed")

  def sql(repo, statement, params \\ []),
    do: Ecto.Adapters.SQL.query!(repo, statement, params, log: false)

  def count,
    do:
      sql(PreauthFixture.Admin, "SELECT count(*) FROM public.mixer_browser_sessions").rows
      |> hd()
      |> hd()

  def unavailable(
        {:error, %Store.Failure{code: :session_unavailable, phase: phase, outcome: outcome}}
      )
      when phase in [:admission, :effect, :decode, :commit] and
             outcome in [:not_started, :rolled_back, :committed, :unknown],
      do: :ok

  def unavailable(_), do: raise("expected closed private failure")

  def record(name, fun) do
    started = System.monotonic_time(:millisecond)

    try do
      fun.()

      checks =
        Process.get(:checks, []) ++
          [%{name: name, passed: true, elapsed_ms: System.monotonic_time(:millisecond) - started}]

      Process.put(:checks, checks)

      File.write!(
        Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "checks.json"),
        Jason.encode!(checks, pretty: true)
      )

      IO.puts("passed: " <> name)
    rescue
      error ->
        IO.puts("FAILED: " <> name)
        reraise error, __STACKTRACE__
    end
  end

  def owner(runtime) do
    if pid = Process.whereis(RuntimeOwner), do: GenServer.stop(pid)
    {:ok, pid} = RuntimeOwner.start_link(runtime)
    Process.unlink(pid)
    assert(RuntimeOwner.status() === %{phase: :storage_ready, generation: 1})
    pid
  end

  def lease do
    GenServer.call(
      RuntimeOwner,
      {:reserve, System.monotonic_time(:millisecond) + 5000, System.system_time(:second)}
    )
  end

  def release(lease), do: GenServer.call(RuntimeOwner, {:release, lease})

  def foreign_call(message) do
    parent = self()

    pid =
      spawn(fn ->
        send(parent, {:foreign_result, self(), GenServer.call(RuntimeOwner, message)})
      end)

    receive do
      {:foreign_result, ^pid, result} -> result
    after
      1500 -> raise "foreign owner call did not finish"
    end
  end

  def preserved(lease) do
    assert(RuntimeOwner.checkpoint(lease) === :ok)
    assert(:sys.get_state(RuntimeOwner).operations[lease.reference].lease === lease)
    assert(RuntimeOwner.status().phase === :storage_ready)
  end

  def policy do
    for statement <- [
          "SET LOCAL search_path=pg_catalog",
          "SET LOCAL jit=off",
          "SET LOCAL statement_timeout='5s'",
          "SET LOCAL lock_timeout='500ms'",
          "SET LOCAL idle_in_transaction_session_timeout='5s'",
          "SET LOCAL bytea_output=hex"
        ],
        do: sql(LifecycleRepo, statement)
  end

  # The exact production candidate is unchanged. A high-priority BEAM tracer
  # suspends only our request at an observed return checkpoint. The request's
  # owner call immediately after relation admission supplies a scheduling yield.
  # No traced arguments/return values are logged or serialized.
  def held_call(module, function, arity, operation, action) do
    parent = self()

    target =
      spawn(fn ->
        receive do
          :go -> send(parent, {:operation_result, self(), operation.()})
        end
      end)

    tracer =
      spawn(fn ->
        Process.flag(:priority, :high)

        receive do
          {:arm, ^target} ->
            receive do
              {:trace, ^target, :return_from, {^module, ^function, ^arity}, _private_result} ->
                :erlang.suspend_process(target)
                send(parent, {:held, self(), target})

                receive do
                  :resume -> :erlang.resume_process(target)
                end
            after
              8000 -> send(parent, {:trace_failed, self()})
            end
        end
      end)

    :erlang.trace_pattern({module, function, arity}, [{:_, [], [{:return_trace}]}], [:local])
    :erlang.trace(target, true, [:call, {:tracer, tracer}])
    send(tracer, {:arm, target})
    send(target, :go)

    try do
      receive do
        {:held, ^tracer, ^target} -> action.()
        {:trace_failed, ^tracer} -> raise "observed checkpoint not reached"
      after
        8500 -> raise "observed checkpoint timed out"
      end
    after
      send(tracer, :resume)
      :erlang.trace_pattern({module, function, arity}, false, [:local])
    end

    receive do
      {:operation_result, ^target, result} -> result
    after
      8500 -> raise "fixed operation timed out"
    end
  end

  def install_deferred(body) do
    sql(
      PreauthFixture.Admin,
      "CREATE FUNCTION public.preauth_fixture_deferred() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN " <>
        body <> "; RETURN NEW; END $$"
    )

    sql(
      PreauthFixture.Admin,
      "CREATE CONSTRAINT TRIGGER preauth_fixture_deferred AFTER INSERT ON public.mixer_browser_sessions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.preauth_fixture_deferred()"
    )
  end

  def settings_restored do
    # Fixture readiness only: rejected COMMIT disconnects a Postgrex connection.
    # Wait for the fixed pool to reconnect before taking both distinct slots;
    # this never retries a production Store operation.
    await_idle_pool(150)
    parent = self()

    holders =
      for _ <- 1..2 do
        spawn(fn ->
          LifecycleRepo.checkout(
            fn ->
              row =
                sql(
                  LifecycleRepo,
                  "SELECT pg_backend_pid(),current_setting('search_path'),current_setting('jit'),current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout'),current_setting('bytea_output')"
                ).rows
                |> hd()

              send(parent, {:settings, self(), row})

              receive do
                :release_settings -> :ok
              end
            end,
            queue: false,
            timeout: 3000
          )
        end)
      end

    rows =
      for _ <- holders do
        receive do
          {:settings, pid, row} -> {pid, row}
        after
          2000 -> raise "settings checkpoint missing"
        end
      end

    try do
      assert(length(Enum.uniq(Enum.map(rows, fn {_, row} -> hd(row) end))) === 2)

      for {_, [_backend, path, jit, statement, lock, idle, bytea]} <- rows do
        assert(
          path !== "pg_catalog" and jit === "on" and statement === "0" and lock === "0" and
            idle === "0" and bytea === "hex"
        )
      end
    after
      for holder <- holders, do: send(holder, :release_settings)
      await_idle_pool(150)
    end
  end

  def await_idle_pool(0), do: raise("fixed fixture pool did not reconnect")

  def await_idle_pool(left) do
    %{rows: [[count]]} =
      sql(
        PreauthFixture.Admin,
        "SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE usename='browser_lifecycle' AND state='idle'"
      )

    %{pid: pool} = Ecto.Adapter.lookup_meta(LifecycleRepo)
    ready = Enum.sum(Enum.map(DBConnection.get_connection_metrics(pool), & &1.ready_conn_count))

    if count == 2 and ready == 2 do
      :ok
    else
      Process.sleep(20)
      await_idle_pool(left - 1)
    end
  end

  def corrupt_tag(id, tag) do
    # Deliberate synthetic owner-level corruption, outside the runtime threat
    # boundary. Restore the exact enabled trigger before current admission.
    PreauthFixture.Admin.transaction(
      fn ->
        sql(
          PreauthFixture.Admin,
          "ALTER TABLE public.mixer_browser_session_vault DISABLE TRIGGER mixer_browser_integrity"
        )

        sql(
          PreauthFixture.Admin,
          "UPDATE public.mixer_browser_session_vault SET tag=$1 WHERE browser_id=$2",
          [tag, id]
        )

        sql(
          PreauthFixture.Admin,
          "ALTER TABLE public.mixer_browser_session_vault ENABLE TRIGGER mixer_browser_integrity"
        )
      end,
      log: false
    )
  end

  def remove_deferred do
    sql(
      PreauthFixture.Admin,
      "DROP TRIGGER IF EXISTS preauth_fixture_deferred ON public.mixer_browser_sessions"
    )

    sql(PreauthFixture.Admin, "DROP FUNCTION IF EXISTS public.preauth_fixture_deferred()")
  end

  def run do
    Process.flag(:trap_exit, true)

    common = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("PREAUTH_PORT")),
      database: "browser_storage",
      password: "synthetic-local-only",
      pool_size: 2,
      pool_count: 1,
      timeout: 5000,
      connect_timeout: 5000,
      queue: false,
      show_sensitive_data_on_connection_error: false,
      ssl: false
    ]

    ordinary = Keyword.put(common, :username, "browser_ordinary")
    lifecycle = Keyword.put(common, :username, "browser_lifecycle")
    Application.put_env(:mixer_hosted, MixerHosted.Repo, ordinary)
    {:ok, ordinary_pid} = MixerHosted.Repo.start_link()
    {:ok, lifecycle_pid} = LifecycleRepo.start_link(lifecycle)

    {:ok, admin_pid} =
      PreauthFixture.Admin.start_link(Keyword.put(common, :username, "browser_admin"))

    {:ok, workers} =
      DynamicSupervisor.start_link(strategy: :one_for_one, name: PreauthFixture.Workers)

    profile = %{
      profile_id: "human-main",
      profile_version: 7,
      issuer: "https://identity.example.invalid/tenant",
      audience: "mixer-api",
      client_id: "mixer-console",
      identity_class: :human,
      enabled: true
    }

    manifest = [
      %{
        profile: profile,
        jwks_endpoint: %{host: "identity.example.invalid", port: 443, path: "/keys"},
        transport: :hosted_https
      }
    ]

    root =
      case hd(:public_key.cacerts_get()) do
        {:cert, der, _} -> der
        der -> der
      end

    identity_options = [
      manifest: manifest,
      generation: 1,
      binding: profile.profile_id,
      ca_roots: [root],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: PreauthFixture.Workers
    ]

    {:ok, identity_pid} = KeyOwner.start_link(identity_options)
    Process.unlink(identity_pid)

    object = %{
      "version" => 1,
      "public_origin" => "https://console.example.invalid",
      "profile_id" => profile.profile_id,
      "profile_version" => profile.profile_version,
      "issuer" => profile.issuer,
      "client_id" => profile.client_id,
      "api_audience" => profile.audience,
      "authorization_endpoint" => "https://identity.example.invalid/authorize",
      "token_endpoint" => "https://identity.example.invalid/token",
      "id_token_jwks_endpoint" => "https://identity.example.invalid/keys",
      "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://mixer/oidc/client-v1",
      "session_vault_ref" => "vault://mixer/browser-v1",
      "scope" => "openid mixer.workspace.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }

    {:ok, config} =
      Config.load(
        %{
          "MIXER_BROWSER_AUTH_MODE" => "configured",
          "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
        },
        :api,
        %StartupConfig{mode: :configured, owner_options: identity_options}
      )

    {:ok, digest} = ConfigurationDigest.digest(config)

    {:ok, custody} =
      Custody.new(config.session_vault_ref, %{
        reference: config.session_vault_ref,
        key_id: "synthetic-key-v1",
        key_bytes: :binary.copy(<<77>>, 32)
      })

    # Explicit fixture exception: trusted manual value uses local random port and
    # ssl:false. No claim about RuntimeConfig.new/4 production TLS/5432 admission.
    runtime = %RuntimeConfig{
      mode: :configured,
      browser_config: config,
      configuration_digest: digest,
      lifecycle_repo: lifecycle,
      expected_roles: @roles,
      custody: custody
    }

    try do
      owner(runtime)
      alias MixerHosted.BrowserAuth.Vault
      metadata = @metadata
      {:ok, p} = RuntimeOwner.bootstrap(metadata)

      record(
        "fixed begin commits before private URL and exact OIDC state nonce S256 ciphertext agreement",
        fn ->
          before = p.source

          {:ok, result} =
            RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)

          assert(match?(%PreauthDraft.Authorization{}, result))
          u = URI.parse(result.url)
          q = URI.decode_query(u.query)

          assert(
            Map.keys(q) |> Enum.sort() ==
              ~w(client_id code_challenge code_challenge_method nonce redirect_uri response_mode response_type scope state)
          )

          assert(result.url |> byte_size() <= 8192)
          assert(u.scheme <> "://" <> u.host <> u.path === config.authorization_endpoint)

          assert(
            q["client_id"] === config.client_id and q["redirect_uri"] === config.redirect_uri
          )

          assert(q["response_type"] === "code" and q["response_mode"] === "query")

          assert(
            q["scope"] === "openid mixer.workspace.read" and q["code_challenge_method"] === "S256"
          )

          s = BeginControls.snapshot(p)

          assert(
            s.browser === %{before.browser | "epoch" => 2, "revision" => 2, "audit_sequence" => 2}
          )

          assert(s.attempt["state_digest"] === :crypto.hash(:sha256, q["state"]))
          assert(s.attempt["nonce_digest"] === :crypto.hash(:sha256, q["nonce"]))

          assert(
            result.expires_at === p.expires_at and s.attempt["expires_at"] === result.expires_at
          )

          {:ok, %Vault.Verifier{verifier: verifier}} =
            Vault.open(custody.key, s.attempt_envelope.context, s.attempt_envelope.sealed)

          {:ok, challenge} = Protocol.pkce_challenge(verifier)
          assert(q["code_challenge"] === challenge)
          assert(length(Enum.uniq([q["state"], q["nonce"], verifier])) === 3)

          {:ok, %Vault.Preauth{csrf: csrf}} =
            Vault.open(custody.key, s.session_envelope.context, s.session_envelope.sealed)

          assert(csrf === p.csrf)
          durable = Jason.encode!(BeginControls.durable())

          for secret <- [p.cookie, p.csrf, q["state"], q["nonce"], verifier],
              do: assert(not String.contains?(durable, secret))

          assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
          Process.put(:first_url, result.url)
        end
      )

      record(
        "pending replacement supersedes old cipher and publishes independent fresh request",
        fn ->
          old = BeginControls.snapshot(p)
          old_q = URI.parse(Process.get(:first_url)).query |> URI.decode_query()

          {:ok, result} =
            RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)

          q = URI.parse(result.url).query |> URI.decode_query()
          s = BeginControls.snapshot(p)
          assert(s.browser["epoch"] === 3 and s.browser["revision"] === 3)
          assert(s.session_envelope.context.vault_generation === 3)

          assert(
            q["state"] !== old_q["state"] and q["nonce"] !== old_q["nonce"] and
              q["code_challenge"] !== old_q["code_challenge"]
          )

          %{rows: [["superseded", "superseded", nil, nil, nil, nil]]} =
            sql(
              PreauthFixture.Admin,
              "SELECT status,completion_reason,key_id,iv,tag,ciphertext FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
              [old.attempt["state_digest"]]
            )
        end
      )

      record("ordinary load remains fail closed for valid pending source", fn ->
        before = BeginControls.durable()
        unavailable(RuntimeOwner.load(p.cookie))
        assert(BeginControls.durable() === before)
        assert(RuntimeOwner.status().phase === :storage_ready)
      end)

      record("raw supplied cookie must equal parsed header cookie before mutation", fn ->
        {:ok, other} = RuntimeOwner.bootstrap(metadata)
        before = BeginControls.durable()

        bad = [
          {"cookie", "__Host-mixer-session=" <> other.cookie},
          {"origin", config.public_origin},
          {"x-mixer-csrf", p.csrf}
        ]

        unavailable(RuntimeOwner.begin_login(p.cookie, bad, :workspace, metadata))
        assert(BeginControls.durable() === before)
      end)

      record(
        "duplicate raw headers cookie ambiguity bearer aliases and malformed input cause no mutation",
        fn ->
          h = BeginControls.headers(p)
          before = BeginControls.durable()

          for headers <- [
                h ++ [{"Origin", config.public_origin}],
                h ++ [{"X-Mixer-Csrf", p.csrf}],
                h ++ [{"Cookie", "x=y"}],
                h ++ [{"Authorization", "Bearer synthetic"}],
                Map.new(h),
                [
                  {"cookie",
                   "__Host-mixer-session=" <> p.cookie <> "; __Host-mixer-session=" <> p.cookie}
                ]
              ] do
            unavailable(RuntimeOwner.begin_login(p.cookie, headers, :workspace, metadata))
          end

          assert(BeginControls.durable() === before)
        end
      )

      record("exact Origin and recovered canonical CSRF checked without durable effects", fn ->
        before = BeginControls.durable()

        for h <- [
              BeginControls.headers(p, "https://console.example.invalid/"),
              BeginControls.headers(p, "https://other.example.invalid"),
              List.keyreplace(
                BeginControls.headers(p),
                "x-mixer-csrf",
                0,
                {"x-mixer-csrf", Protocol.random_token()}
              ),
              List.keydelete(BeginControls.headers(p), "origin", 0)
            ] do
          unavailable(RuntimeOwner.begin_login(p.cookie, h, :workspace, metadata))
        end

        assert(BeginControls.durable() === before)
      end)

      record("closed metadata return route and absent malformed cookie deny without write", fn ->
        before = BeginControls.durable()

        for m <- [
              %{},
              %{request_id: String.duplicate("A", 32)},
              %{request_id: metadata.request_id, extra: true},
              nil
            ],
            do:
              unavailable(
                RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, m)
              )

        for route <- [:login, "workspace", "/workspace", nil],
            do:
              unavailable(
                RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), route, metadata)
              )

        for cookie <- [nil, "", String.duplicate("a", 42), Protocol.random_token()],
            do:
              unavailable(
                RuntimeOwner.begin_login(cookie, BeginControls.headers(p), :workspace, metadata)
              )

        assert(BeginControls.durable() === before)
      end)

      record(
        "public result and internal drafts redact URL state verifier source and live owner status",
        fn ->
          {lease, s} = BeginControls.discover(p)
          d = BeginControls.draft(lease, s, p.csrf)

          {:ok, r} =
            RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)

          printed =
            inspect(d) <>
              inspect(r) <>
              inspect(%PreauthDraft.Publication{
                checked_wall: System.system_time(:second),
                expires_at: r.expires_at,
                value: r
              }) <> inspect(:sys.get_status(RuntimeOwner))

          for secret <- [r.url, d.state, d.nonce, d.verifier, p.cookie, p.csrf, custody.key.bytes],
              do: assert(not String.contains?(printed, secret))

          assert(release(lease) === :ok)
        end
      )

      record("bad or mismatched URL denied before mutating transaction", fn ->
        {lease, s} = BeginControls.discover(p)
        d = BeginControls.draft(lease, s, p.csrf)
        before = BeginControls.durable()

        for url <- [
              d.url <> "&extra=1",
              String.duplicate("x", 8193),
              "https://other.example.invalid/authorize"
            ],
            do: unavailable(Store.begin_login(%{d | url: url}, metadata))

        assert(BeginControls.durable() === before)
        assert(release(lease) === :ok)
      end)

      record(
        "all new session and verifier cipher fields authenticate before mutating effects",
        fn ->
          {lease, s} = BeginControls.discover(p)
          d = BeginControls.draft(lease, s, p.csrf)
          before = BeginControls.durable()

          for field <- [:key_id, :iv, :tag, :ciphertext] do
            bad =
              case field do
                :key_id -> "different-key"
                :iv -> :binary.copy(<<19>>, 12)
                :tag -> :binary.copy(<<19>>, 16)
                :ciphertext -> <<19>>
              end

            unavailable(Store.begin_login(%{d | sealed: Map.put(d.sealed, field, bad)}, metadata))

            unavailable(
              Store.begin_login(
                %{d | attempt_sealed: Map.put(d.attempt_sealed, field, bad)},
                metadata
              )
            )
          end

          assert(BeginControls.durable() === before)
          assert(release(lease) === :ok)
        end
      )

      record(
        "new attempt metadata and state nonce verifier substitutions fail before effects",
        fn ->
          {lease, s} = BeginControls.discover(p)
          d = BeginControls.draft(lease, s, p.csrf)
          before = BeginControls.durable()

          for {field, value} <- [
                state: Protocol.random_token(),
                nonce: Protocol.random_token(),
                verifier: Protocol.random_token(),
                csrf: Protocol.random_token()
              ] do
            unavailable(Store.begin_login(Map.put(d, field, value), metadata))
          end

          for {field, value} <- [
                issuer: "https://other.example.invalid",
                client_id: "different",
                redirect_uri: "https://other.example.invalid/auth/callback",
                epoch: d.attempt_context.epoch + 1,
                expires_at: d.attempt_context.expires_at + 1,
                profile_version: 8
              ] do
            unavailable(
              Store.begin_login(
                %{d | attempt_context: Map.put(d.attempt_context, field, value)},
                metadata
              )
            )
          end

          assert(BeginControls.durable() === before)
          assert(release(lease) === :ok)
        end
      )

      record(
        "all produced browser source fields compared before commit and rollback on mismatch",
        fn ->
          {lease, s} = BeginControls.discover(p)
          d = BeginControls.draft(lease, s, p.csrf)
          before = BeginControls.durable()

          for {field, value} <- [
                {"last_seen_at", s.browser["last_seen_at"] + 1},
                {"audit_sequence", s.browser["audit_sequence"] + 1},
                {"absolute_expires_at", s.browser["absolute_expires_at"] + 1},
                {"idle_expires_at", s.browser["idle_expires_at"] - 1}
              ] do
            altered = %{s | browser: Map.put(s.browser, field, value)}
            unavailable(Store.begin_login(%{d | source: altered}, metadata))
            assert(BeginControls.durable() === before)
          end

          assert(release(lease) === :ok)
        end
      )

      record("pending source verifier AEAD authentication fails closed with no mutation", fn ->
        {:ok, e} = RuntimeOwner.bootstrap(metadata)
        {lease, source} = BeginControls.discover(e)
        d = BeginControls.draft(lease, source, e.csrf)
        bad = %{d.attempt_sealed | tag: :binary.copy(<<9>>, 16)}
        _ = BeginControls.raw_begin(%{d | attempt_sealed: bad})
        assert(release(lease) === :ok)
        before = BeginControls.durable()

        unavailable(
          RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)
        )

        assert(BeginControls.durable() === before)
      end)

      record(
        "expired authenticated pending attempt can be superseded while browser stays live",
        fn ->
          {:ok, e} = RuntimeOwner.bootstrap(metadata)
          {lease, source} = BeginControls.discover(e)
          d = BeginControls.draft(lease, source, e.csrf)
          a = %{d.attempt_context | expires_at: System.system_time(:second) + 2}
          {:ok, cipher} = Vault.seal(custody.key, a, %Vault.Verifier{verifier: d.verifier})
          old = BeginControls.raw_begin(%{d | attempt_context: a, attempt_sealed: cipher})
          assert(release(lease) === :ok)
          Process.sleep(2100)
          assert(System.system_time(:second) >= a.expires_at)

          {:ok, _} =
            RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)

          %{rows: [["superseded", nil]]} =
            sql(
              PreauthFixture.Admin,
              "SELECT status,ciphertext FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
              [old.attempt["state_digest"]]
            )
        end
      )

      record("hidden claimed attempt is not projected and unchanged SQL supersedes it", fn ->
        {:ok, e} = RuntimeOwner.bootstrap(metadata)

        {:ok, _} =
          RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)

        s = BeginControls.snapshot(e)

        BeginControls.fixture_transaction(fn ->
          sql(
            LifecycleRepo,
            "SELECT public.mixer_browser_claim($1::bytea,$2::bytea,$3::bytea,$4::bigint,$5::bytea,$6::bigint,$7::text)",
            [
              s.browser["cookie_digest"],
              s.attempt["state_digest"],
              digest,
              s.browser["revision"],
              :crypto.strong_rand_bytes(32),
              System.system_time(:second) + 30,
              metadata.request_id
            ]
          )
        end)

        {lease, source} = BeginControls.discover(e)
        assert(is_nil(source.attempt) and is_nil(source.attempt_envelope))
        assert(release(lease) === :ok)

        {:ok, _} =
          RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)

        %{rows: [["superseded", nil]]} =
          sql(
            PreauthFixture.Admin,
            "SELECT status,ciphertext FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
            [s.attempt["state_digest"]]
          )
      end)

      record(
        "hidden provider terminal attempt is not projected and remains terminal after begin",
        fn ->
          {:ok, e} = RuntimeOwner.bootstrap(metadata)

          {:ok, _} =
            RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)

          s = BeginControls.snapshot(e)

          BeginControls.fixture_transaction(fn ->
            sql(
              LifecycleRepo,
              "SELECT public.mixer_browser_provider_reject($1::bytea,$2::bytea,$3::bytea,$4::bigint,$5::text)",
              [
                s.browser["cookie_digest"],
                s.attempt["state_digest"],
                digest,
                s.browser["revision"],
                metadata.request_id
              ]
            )
          end)

          {lease, source} = BeginControls.discover(e)
          assert(is_nil(source.attempt) and is_nil(source.attempt_envelope))
          assert(release(lease) === :ok)

          {:ok, _} =
            RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)

          %{rows: [["provider_rejected", nil]]} =
            sql(
              PreauthFixture.Admin,
              "SELECT status,ciphertext FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",
              [s.attempt["state_digest"]]
            )
        end
      )

      record(
        "browser exclusive expiry denies begin after committed discovery without new mutation",
        fn ->
          e = BeginControls.short_browser(runtime)
          Process.sleep(2100)
          assert(System.system_time(:second) >= e.expires_at)
          before = BeginControls.durable()

          unavailable(
            RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)
          )

          assert(BeginControls.durable() === before)
        end
      )

      record(
        "claim and provider rejection revision-stable audit races roll back begin without URL",
        fn ->
          for op <- [:claim, :reject] do
            {:ok, e} = RuntimeOwner.bootstrap(metadata)

            {:ok, _} =
              RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)

            current = BeginControls.snapshot(e)
            parent = self()

            r =
              BeginControls.held_n(
                Store,
                :discover_begin,
                1,
                1,
                fn ->
                  RuntimeOwner.begin_login(
                    e.cookie,
                    BeginControls.headers(e),
                    :workspace,
                    metadata
                  )
                end,
                fn ->
                  BeginControls.fixture_transaction(fn ->
                    case op do
                      :claim ->
                        sql(
                          LifecycleRepo,
                          "SELECT public.mixer_browser_claim($1::bytea,$2::bytea,$3::bytea,$4::bigint,$5::bytea,$6::bigint,$7::text)",
                          [
                            current.browser["cookie_digest"],
                            current.attempt["state_digest"],
                            digest,
                            current.browser["revision"],
                            :crypto.strong_rand_bytes(32),
                            System.system_time(:second) + 30,
                            metadata.request_id
                          ]
                        )

                      :reject ->
                        sql(
                          LifecycleRepo,
                          "SELECT public.mixer_browser_provider_reject($1::bytea,$2::bytea,$3::bytea,$4::bigint,$5::text)",
                          [
                            current.browser["cookie_digest"],
                            current.attempt["state_digest"],
                            digest,
                            current.browser["revision"],
                            metadata.request_id
                          ]
                        )
                    end
                  end)

                  send(parent, {:race_durable, BeginControls.durable()})
                end
              )

            unavailable(r)
            assert(match?({:error, %Store.Failure{phase: :decode, outcome: :rolled_back}}, r))

            receive do
              {:race_durable, after_race} -> assert(BeginControls.durable() === after_race)
            after
              1000 -> raise "race snapshot missing"
            end
          end
        end
      )

      record(
        "browser expiry after discovery COMMIT withholds URL and leaves durable source unchanged",
        fn ->
          e = BeginControls.short_browser(runtime)
          before = BeginControls.durable()

          r =
            BeginControls.held_n(
              Store,
              :discover_begin,
              1,
              1,
              fn ->
                RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)
              end,
              fn -> Process.sleep(2100) end
            )

          unavailable(r)
          assert(BeginControls.durable() === before)
        end
      )

      record(
        "same source revision concurrency has one URL winner one closed CAS loser and no retry",
        fn ->
          {:ok, c} = RuntimeOwner.bootstrap(metadata)
          results = BeginControls.concurrent(c, metadata) |> Enum.map(&elem(&1, 1))
          assert(Enum.count(results, &match?({:ok, %PreauthDraft.Authorization{}}, &1)) === 1)
          assert(Enum.count(results, &match?({:error, %Store.Failure{}}, &1)) === 1)
          s = BeginControls.snapshot(c)
          assert(s.browser["revision"] === 2 and s.browser["audit_sequence"] === 2)
          assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
        end
      )

      record("foreign caller cannot consume copied begin lease or invoke typed Store", fn ->
        {lease, s} = BeginControls.discover(p)
        d = BeginControls.draft(lease, s, p.csrf)
        before = BeginControls.durable()
        parent = self()

        pid =
          spawn(fn -> send(parent, {:foreign_begin, self(), Store.begin_login(d, metadata)}) end)

        receive do
          {:foreign_begin, ^pid, r} -> unavailable(r)
        after
          1500 -> raise "foreign begin missing"
        end

        preserved(lease)
        assert(BeginControls.durable() === before)
        assert(release(lease) === :ok)
      end)

      record(
        "shared publication receipt preserves bootstrap load nil and retained-caller cleanup",
        fn ->
          {:ok, e} = RuntimeOwner.bootstrap(metadata)
          assert(RuntimeOwner.load(e.cookie) === {:ok, e})
          assert(RuntimeOwner.load(Protocol.random_token()) === {:ok, nil})
          assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
        end
      )

      record(
        "successful finish releases permit but cannot publish URL after entry deadline",
        fn ->
          {:ok, e} = RuntimeOwner.bootstrap(metadata)
          before = BeginControls.snapshot(e)

          r =
            BeginControls.held_n(
              RuntimeOwner,
              :finish_receipt,
              3,
              1,
              fn ->
                RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)
              end,
              fn ->
                assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)

                assert(
                  BeginControls.snapshot(e).browser["revision"] === before.browser["revision"] + 1
                )

                Process.sleep(5100)
              end
            )

          unavailable(r)
          assert(match?({:error, %Store.Failure{phase: :commit, outcome: :committed}}, r))
          assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
        end
      )

      record(
        "successful finish cannot publish URL after exclusive browser or attempt expiry",
        fn ->
          e = BeginControls.short_browser(runtime)

          r =
            BeginControls.held_n(
              RuntimeOwner,
              :finish_receipt,
              3,
              1,
              fn ->
                RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)
              end,
              fn ->
                assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
                Process.sleep(2100)
              end
            )

          unavailable(r)
          assert(match?({:error, %Store.Failure{phase: :commit, outcome: :committed}}, r))
        end
      )

      record(
        "single original deadline includes encrypted discovery commit and pre-mutation work",
        fn ->
          before = BeginControls.durable()
          started = System.monotonic_time(:millisecond)

          r =
            BeginControls.held_n(
              Store,
              :discover_begin,
              1,
              1,
              fn ->
                RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)
              end,
              fn -> Process.sleep(5100) end
            )

          unavailable(r)
          assert(System.monotonic_time(:millisecond) - started >= 5000)
          assert(BeginControls.durable() === before)
          assert(RuntimeOwner.status().phase === :unavailable)
          owner(runtime)
        end
      )

      record(
        "deferred mutating COMMIT rejection returns no URL and restores exact durable source",
        fn ->
          before = BeginControls.durable()

          r =
            try do
              BeginControls.held_n(
                RelationCatalog,
                :check_relation_surface!,
                3,
                2,
                fn ->
                  RuntimeOwner.begin_login(
                    p.cookie,
                    BeginControls.headers(p),
                    :workspace,
                    metadata
                  )
                end,
                fn ->
                  BeginControls.install_deferred(
                    "RAISE EXCEPTION 'synthetic deferred denial' USING ERRCODE='23514'"
                  )
                end
              )
            after
              BeginControls.remove_deferred()
            end

          unavailable(r)
          assert(match?({:error, %Store.Failure{phase: :commit, outcome: :rolled_back}}, r))
          assert(BeginControls.durable() === before)
          settings_restored()
        end
      )

      record(
        "lost backend during mutating COMMIT is unknown clears readiness and never retries",
        fn ->
          before = BeginControls.durable()

          r =
            try do
              BeginControls.held_n(
                RelationCatalog,
                :check_relation_surface!,
                3,
                2,
                fn ->
                  RuntimeOwner.begin_login(
                    p.cookie,
                    BeginControls.headers(p),
                    :workspace,
                    metadata
                  )
                end,
                fn ->
                  BeginControls.install_deferred(
                    "PERFORM pg_catalog.pg_terminate_backend(pg_catalog.pg_backend_pid())"
                  )
                end
              )
            after
              BeginControls.remove_deferred()
            end

          unavailable(r)
          assert(match?({:error, %Store.Failure{phase: :commit, outcome: :unknown}}, r))
          assert(BeginControls.durable() === before)
          assert(RuntimeOwner.status().phase === :unavailable)
          settings_restored()
          owner(runtime)
        end
      )

      record("deferred mutating COMMIT wait uses the same five second entry deadline", fn ->
        before = BeginControls.durable()
        started = System.monotonic_time(:millisecond)

        r =
          try do
            BeginControls.held_n(
              RelationCatalog,
              :check_relation_surface!,
              3,
              2,
              fn ->
                RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)
              end,
              fn -> BeginControls.install_deferred("PERFORM pg_catalog.pg_sleep(7)") end
            )
          after
            BeginControls.remove_deferred()
          end

        unavailable(r)

        assert(
          System.monotonic_time(:millisecond) - started >= 4500 and
            System.monotonic_time(:millisecond) - started < 7000
        )

        assert(match?({:error, %Store.Failure{phase: :commit}}, r))
        assert(BeginControls.durable() === before)
        assert(RuntimeOwner.status().phase === :unavailable)
        settings_restored()
        owner(runtime)
      end)

      record(
        "known committed mutation with default identity PID loss withholds authorization URL",
        fn ->
          before = BeginControls.snapshot(p)

          r =
            BeginControls.held_n(
              LifecycleRepo,
              :transaction,
              2,
              2,
              fn ->
                RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)
              end,
              fn ->
                assert(
                  BeginControls.snapshot(p).browser["revision"] === before.browser["revision"] + 1
                )

                GenServer.stop(identity_pid)
              end
            )

          unavailable(r)
          assert(match?({:error, %Store.Failure{phase: :commit, outcome: :committed}}, r))
          assert(RuntimeOwner.status().phase === :unavailable)
          assert(BeginControls.snapshot(p).browser["revision"] === before.browser["revision"] + 1)
        end
      )

      {:ok, new_identity} = KeyOwner.start_link(identity_options)
      Process.unlink(new_identity)
      owner(runtime)

      record(
        "successful finish cannot publish URL after current default identity owner loss",
        fn ->
          {:ok, e} = RuntimeOwner.bootstrap(metadata)

          r =
            BeginControls.held_finish(
              fn ->
                RuntimeOwner.begin_login(e.cookie, BeginControls.headers(e), :workspace, metadata)
              end,
              fn ->
                GenServer.stop(new_identity)
              end
            )

          unavailable(r)
          assert(match?({:error, %Store.Failure{phase: :commit, outcome: :committed}}, r))
          assert(RuntimeOwner.status().phase === :unavailable)
        end
      )
    after
      assert(DynamicSupervisor.which_children(workers) === [])

      for name <- [
            RuntimeOwner,
            KeyOwner,
            PreauthFixture.Workers,
            PreauthFixture.Admin,
            LifecycleRepo,
            MixerHosted.Repo
          ] do
        if pid = Process.whereis(name), do: GenServer.stop(pid)
      end

      assert(
        Enum.all?([ordinary_pid, lifecycle_pid, admin_pid, workers], &(not Process.alive?(&1)))
      )

      assert(:ets.info(Module.concat(LifecycleRepo, Binding)) === :undefined)

      File.write!(
        Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "beam-cleanup.json"),
        Jason.encode!(%{
          fixed_owned_processes_absent: true,
          repo_binding_table_absent: true,
          no_provider_fetch_started: true
        })
      )
    end
  end
end

Code.require_file("verification/hosted-browser-begin-login/controls.exs")
PreauthFixture.run()
