Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Application.ensure_all_started(:jose)

defmodule PreauthFixture.Admin do
  use Ecto.Repo, otp_app: :preauth_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule PreauthFixture do
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

  def release(lease), do: GenServer.call(RuntimeOwner, {:finish, lease, nil})

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
      record("fixed Repo actual startup options binding", fn ->
        assert(LifecycleRepo.bound?(lifecycle))
        assert(not LifecycleRepo.bound?(Keyword.put(lifecycle, :password, "different")))
        assert(not LifecycleRepo.bound?(Keyword.put(lifecycle, :pool_size, 3)))
      end)

      record("arbitrary caller cannot invoke startup admission", fn ->
        assert(
          Store.admit(runtime, System.monotonic_time(:millisecond) + 5000) ===
            Store.failure(:admission, :not_started)
        )
      end)

      record("startup admits fixed V2 function and relation conjunction", fn -> owner(runtime) end)

      telemetry_id = "preauth-query-redaction"
      parent = self()

      :ok =
        :telemetry.attach(
          telemetry_id,
          [:mixer_hosted, :browser_auth, :lifecycle_repo, :query],
          fn _event, _measurements, metadata, _config ->
            query = IO.iodata_to_binary(metadata.query)

            sensitive =
              String.contains?(query, "SELECT public.mixer_browser_bootstrap") or
                String.contains?(query, "SELECT public.mixer_browser_load")

            send(parent, {:query_telemetry, sensitive})
          end,
          nil
        )

      {:ok, preauth} = RuntimeOwner.bootstrap(@metadata)

      record("real bootstrap Vault StoredSnapshot committed preauth roundtrip", fn ->
        assert(match?(%PreauthDraft.Preauth{}, preauth))
        assert(Protocol.token?(preauth.cookie) and Protocol.token?(preauth.csrf))
        assert(preauth.source.session_envelope.context.purpose === :preauth)
        assert(count() === 1)
        {:ok, loaded} = RuntimeOwner.load(preauth.cookie)
        assert(loaded === preauth)
        assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
      end)

      record(
        "actual Ecto SQL telemetry emits catalogs but no sealed bootstrap or cookie load query",
        fn ->
          events =
            Stream.repeatedly(fn ->
              receive do
                {:query_telemetry, sensitive} -> sensitive
              after
                0 -> :done
              end
            end)
            |> Enum.take_while(&(&1 !== :done))

          assert(events != [] and Enum.all?(events, &(&1 === false)))
          :telemetry.detach(telemetry_id)
        end
      )

      record("private result and actual GenServer status redact source and credentials", fn ->
        printed =
          inspect(preauth) <>
            inspect(:sys.get_status(RuntimeOwner)) <>
            inspect(
              RuntimeOwner.format_status(%{
                state: :sys.get_state(RuntimeOwner),
                message: {:secret, preauth},
                reason: preauth,
                log: [preauth]
              })
            )

        for secret <- [
              preauth.cookie,
              preauth.csrf,
              "synthetic-local-only",
              config.session_vault_ref,
              config.issuer,
              custody.key.bytes,
              preauth.source.session_envelope.sealed.iv
            ] do
          assert(not String.contains?(printed, secret))
        end
      end)

      record("strict metadata and malformed cookie fail without durable writes", fn ->
        before = count()

        for metadata <- [
              %{},
              %{request_id: String.duplicate("A", 32)},
              %{request_id: @metadata.request_id, extra: true},
              nil
            ],
            do: unavailable(RuntimeOwner.bootstrap(metadata))

        for cookie <- [nil, "", String.duplicate("a", 42), %{}],
            do: unavailable(RuntimeOwner.load(cookie))

        assert(count() === before)
      end)

      record("absent canonical cookie returns no private session", fn ->
        assert(RuntimeOwner.load(Protocol.random_token()) === {:ok, nil})
      end)

      record("foreign ordinary context and ordinary transaction deny", fn ->
        before = count()
        Process.put({MixerHosted.Authorization.Transaction.Context, :active}, %{copied: true})

        try do
          unavailable(RuntimeOwner.bootstrap(@metadata))
        after
          Process.delete({MixerHosted.Authorization.Transaction.Context, :active})
        end

        assert(
          MixerHosted.Repo.transaction(fn -> unavailable(RuntimeOwner.bootstrap(@metadata)) end,
            log: false
          ) === {:ok, :ok}
        )

        assert(count() === before)
      end)

      record("foreign lifecycle transaction rejects nested Store work", fn ->
        before = count()

        assert(
          LifecycleRepo.transaction(fn -> unavailable(RuntimeOwner.bootstrap(@metadata)) end,
            log: false
          ) === {:ok, :ok}
        )

        assert(count() === before)
      end)

      record("actual pool2 exhaustion rejects promptly with queue false", fn ->
        parent = self()

        holders =
          for _ <- 1..2 do
            spawn(fn ->
              LifecycleRepo.checkout(
                fn ->
                  send(parent, {:holding, self()})

                  receive do
                    :release -> :ok
                  end
                end,
                timeout: 10000,
                queue: false
              )
            end)
          end

        for _ <- holders do
          receive do
            {:holding, _} -> :ok
          after
            2000 -> raise "pool hold failed"
          end
        end

        started = System.monotonic_time(:millisecond)
        result = RuntimeOwner.bootstrap(@metadata)
        elapsed = System.monotonic_time(:millisecond) - started
        unavailable(result)
        assert(elapsed < 1000)
        assert(match?({:error, %Store.Failure{outcome: :not_started}}, result))
        for holder <- holders, do: send(holder, :release)
        Process.sleep(30)
        assert(RuntimeOwner.status().phase === :storage_ready)
      end)

      record("actual owner cap32 immediate reject caller death release", fn ->
        parent = self()

        callers =
          for _ <- 1..32 do
            spawn(fn ->
              {:ok, lease} = lease()
              send(parent, {:leased, self(), lease})

              receive do
                :stop -> :ok
              end
            end)
          end

        leases =
          for _ <- callers do
            receive do
              {:leased, pid, lease} -> {pid, lease}
            after
              2500 -> raise "owner lease failed"
            end
          end

        unavailable(lease())
        assert(map_size(:sys.get_state(RuntimeOwner).operations) === 32)
        [{_, foreign} | _] = leases
        unavailable(RuntimeOwner.checkpoint(foreign))
        for caller <- callers, do: send(caller, :stop)
        Process.sleep(30)
        assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
        {:ok, own} = lease()
        assert(RuntimeOwner.checkpoint(own) === :ok)
        assert(release(own) === :ok)
        unavailable(RuntimeOwner.checkpoint(own))
        unavailable(RuntimeOwner.checkpoint(Map.from_struct(own)))
      end)

      record("expired original deadline rejects owner reserve without clock injection", fn ->
        unavailable(
          GenServer.call(
            RuntimeOwner,
            {:reserve, System.monotonic_time(:millisecond), System.system_time(:second)}
          )
        )

        unavailable(
          GenServer.call(
            RuntimeOwner,
            {:reserve, System.monotonic_time(:millisecond) + 6000, System.system_time(:second)}
          )
        )
      end)

      record("validly shaped stored cipher tamper fails after committed read", fn ->
        id = preauth.source.browser["id"]
        sealed = preauth.source.session_envelope.sealed

        sql(
          PreauthFixture.Admin,
          "UPDATE public.mixer_browser_session_vault SET tag=$1 WHERE browser_id=$2",
          [:binary.copy(<<99>>, 16), id]
        )

        result = RuntimeOwner.load(preauth.cookie)
        unavailable(result)
        assert(match?({:error, %Store.Failure{phase: :decode, outcome: :committed}}, result))

        sql(
          PreauthFixture.Admin,
          "UPDATE public.mixer_browser_session_vault SET tag=$1 WHERE browser_id=$2",
          [sealed.tag, id]
        )

        assert(RuntimeOwner.load(preauth.cookie) === {:ok, preauth})
      end)

      record("function pass alone cannot hide current relation privilege drift", fn ->
        sql(
          PreauthFixture.Admin,
          "GRANT SELECT ON public.mixer_browser_sessions TO browser_lifecycle"
        )

        try do
          assert(
            LifecycleRepo.transaction(
              fn ->
                policy()

                Catalog.check_function_surface!(
                  LifecycleRepo,
                  @roles,
                  System.monotonic_time(:millisecond) + 5000,
                  2
                )
              end,
              log: false
            ) === {:ok, :function_surface_verified}
          )

          unavailable(RuntimeOwner.bootstrap(@metadata))
          assert(RuntimeOwner.status().phase === :unavailable)
        after
          sql(
            PreauthFixture.Admin,
            "REVOKE SELECT ON public.mixer_browser_sessions FROM browser_lifecycle"
          )
        end

        owner(runtime)
      end)

      record("relation pass alone cannot hide current function settings drift", fn ->
        sql(
          PreauthFixture.Admin,
          "ALTER FUNCTION public.mixer_browser_load(bytea,bytea) SET jit=off"
        )

        try do
          assert(
            LifecycleRepo.transaction(
              fn ->
                policy()

                RelationCatalog.check_relation_surface!(
                  LifecycleRepo,
                  @roles,
                  System.monotonic_time(:millisecond) + 5000
                )
              end,
              log: false
            ) === {:ok, :relation_surface_verified}
          )

          unavailable(RuntimeOwner.load(preauth.cookie))
          assert(RuntimeOwner.status().phase === :unavailable)
        after
          sql(
            PreauthFixture.Admin,
            "ALTER FUNCTION public.mixer_browser_load(bytea,bytea) RESET jit"
          )
        end

        owner(runtime)
      end)

      record("exact candidate deferred PostgreSQL COMMIT rejection rolls back all writes", fn ->
        before = count()

        result =
          try do
            held_call(
              RelationCatalog,
              :check_relation_surface!,
              3,
              fn -> RuntimeOwner.bootstrap(@metadata) end,
              fn ->
                assert(count() === before)

                install_deferred(
                  "RAISE EXCEPTION 'fixture deferred failure' USING ERRCODE='23514'"
                )
              end
            )
          after
            remove_deferred()
          end

        unavailable(result)
        assert(match?({:error, %Store.Failure{phase: :commit, outcome: :rolled_back}}, result))
        assert(count() === before)
      end)

      record("absolute original deadline includes actual deferred COMMIT wait", fn ->
        before = count()
        started = System.monotonic_time(:millisecond)

        result =
          try do
            held_call(
              RelationCatalog,
              :check_relation_surface!,
              3,
              fn -> RuntimeOwner.bootstrap(@metadata) end,
              fn ->
                assert(count() === before)
                install_deferred("PERFORM pg_catalog.pg_sleep(7)")
              end
            )
          after
            remove_deferred()
          end

        elapsed = System.monotonic_time(:millisecond) - started
        unavailable(result)
        assert(elapsed >= 4500 and elapsed < 7000)
        assert(count() === before)
        assert(RuntimeOwner.status().phase === :unavailable)
        owner(runtime)
      end)

      record("default identity owner death denies new private publication", fn ->
        GenServer.stop(identity_pid)
        Process.sleep(20)
        assert(RuntimeOwner.status().phase === :unavailable)
        unavailable(RuntimeOwner.load(preauth.cookie))
        assert(count() === 1)
      end)

      IO.puts("selected_preauth_checks:" <> Integer.to_string(length(Process.get(:checks, []))))
    after
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

PreauthFixture.run()
