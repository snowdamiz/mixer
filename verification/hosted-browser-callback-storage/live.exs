Logger.configure(level: :emergency)
Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Application.ensure_all_started(:jose)

defmodule CallbackFixture.Admin do
  use Ecto.Repo, otp_app: :preauth_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule CallbackFixture do
  @compile {:no_warn_undefined, CallbackControls}
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest, Custody, LifecycleRepo}

  alias MixerHosted.BrowserAuth.{
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
      sql(CallbackFixture.Admin, "SELECT count(*) FROM public.mixer_browser_sessions").rows
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
    case System.get_env("CALLBACK_CASE") do
      nil -> record_selected(name, fun)
      selected -> if String.contains?(name, selected), do: record_selected(name, fun), else: :ok
    end
  end

  defp record_selected(name, fun) do
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
        checks =
          Process.get(:checks, []) ++
            [
              %{
                name: name,
                passed: false,
                error_class: Atom.to_string(error.__struct__),
                elapsed_ms: System.monotonic_time(:millisecond) - started
              }
            ]

        Process.put(:checks, checks)

        File.write!(
          Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "checks.json"),
          Jason.encode!(checks, pretty: true)
        )

        case error do
          %RuntimeError{message: message}
          when message in [
                 "bounded preauthentication assertion failed",
                 "operation completed before fence",
                 "selected hold not reached",
                 "selected result missing",
                 "owned owner death not confirmed"
               ] ->
            IO.puts("control boundary: " <> message)

          _ ->
            :ok
        end

        IO.puts("FAILED: " <> name <> " (redacted " <> Atom.to_string(error.__struct__) <> ")")
        raise "redacted callback control failure"
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
      CallbackFixture.Admin,
      "CREATE FUNCTION public.preauth_fixture_deferred() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN " <>
        body <> "; RETURN NEW; END $$"
    )

    sql(
      CallbackFixture.Admin,
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
        CallbackFixture.Admin,
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
    CallbackFixture.Admin.transaction(
      fn ->
        sql(
          CallbackFixture.Admin,
          "ALTER TABLE public.mixer_browser_session_vault DISABLE TRIGGER mixer_browser_integrity"
        )

        sql(
          CallbackFixture.Admin,
          "UPDATE public.mixer_browser_session_vault SET tag=$1 WHERE browser_id=$2",
          [tag, id]
        )

        sql(
          CallbackFixture.Admin,
          "ALTER TABLE public.mixer_browser_session_vault ENABLE TRIGGER mixer_browser_integrity"
        )
      end,
      log: false
    )
  end

  def remove_deferred do
    sql(
      CallbackFixture.Admin,
      "DROP TRIGGER IF EXISTS preauth_fixture_deferred ON public.mixer_browser_sessions"
    )

    sql(CallbackFixture.Admin, "DROP FUNCTION IF EXISTS public.preauth_fixture_deferred()")
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
      CallbackFixture.Admin.start_link(Keyword.put(common, :username, "browser_admin"))

    {:ok, workers} =
      DynamicSupervisor.start_link(strategy: :one_for_one, name: CallbackFixture.Workers)

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
      worker_supervisor: CallbackFixture.Workers
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
      CallbackControls.run(runtime, @metadata, identity_pid)
    after
      assert(DynamicSupervisor.which_children(workers) === [])

      for name <- [
            RuntimeOwner,
            KeyOwner,
            CallbackFixture.Workers,
            CallbackFixture.Admin,
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

Code.require_file("verification/hosted-browser-callback-storage/controls.exs")
CallbackFixture.run()
