Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.CustomerCreateBuildAtomicReplayPGJoinTest do
  use ExUnit.Case, async: false
  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.CustomerBuilds.CreateRepo

  setup_all do
    conn = F.connection!("browser_admin", "postgres")

    case Postgrex.query!(
           conn,
           "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname='mixer_customer_build_catalog_definer_v1'",
           []
         ).rows do
      [] ->
        Postgrex.query!(
          conn,
          "CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT",
          []
        )

      [[false, false, false, false, false, false, false]] ->
        :ok
    end

    GenServer.stop(conn)
    parent = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
    ev = Path.join(parent, "attempt-" <> Base.encode16(:crypto.strong_rand_bytes(6)))
    File.mkdir!(ev)
    System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", ev)

    on_exit(fn ->
      System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", parent)
      assert System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT") == parent
      File.write!(Path.join(ev, "parent-restored.json"), Jason.encode!(%{restored: true}))
    end)

    c = Fixture.prepare!(true)

    case F.q!(
           Admin,
           "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname='mixer_build_create'"
         ).rows do
      [] ->
        F.q!(
          Admin,
          "CREATE ROLE mixer_build_create LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION"
        )

      [[true, false, false, false, false, false, false]] ->
        :ok
    end

    F.q!(Admin, "GRANT USAGE ON SCHEMA public TO mixer_build_create")

    F.q!(
      Admin,
      "GRANT SELECT ON " <>
        Enum.map_join(
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
          ",",
          &("public.mixer_authz_" <> &1)
        ) <> " TO mixer_build_create"
    )

    for h <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.q!(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_" <>
              h <> "() TO mixer_build_create"
          )

    for sql <- MixerHosted.CustomerBuilds.CreateSchema.statements(), do: F.q!(Migration, sql)
    for sql <- MixerHosted.BrowserAuth.ActiveCreateSchema.statements(), do: F.q!(Migration, sql)
    F.q!(Admin, "GRANT CREATE ON SCHEMA public TO browser_writer")

    F.q!(
      Admin,
      "ALTER FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) OWNER TO browser_writer"
    )

    F.q!(Admin, "REVOKE CREATE ON SCHEMA public FROM browser_writer")

    F.q!(
      Admin,
      "GRANT EXECUTE ON FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) TO mixer_build_create"
    )

    F.q!(Admin, "UPDATE mixer_authz_memberships SET role='developer' WHERE id='member-a'")

    for {id, ref} <- [{"input-a", "immutable-input-a"}, {"input-b", "immutable-input-b"}] do
      F.q!(
        Admin,
        "INSERT INTO mixer_customer_build_inputs VALUES('org-a','project-a','fieldlog','ios',$1,'revision',$2,$3,$4,$5,2,10000,0)",
        [id, ref, String.duplicate("a", 64), String.duplicate("b", 64), String.duplicate("c", 64)]
      )
    end

    create =
      c.hosted.repo |> Keyword.put(:username, "mixer_build_create") |> Keyword.put(:pool_size, 4)

    c = Map.put(c, :hosted, %{c.hosted | create_repo: create})
    lock_discriminator!()
    c = Fixture.start!(c)
    assert MixerHosted.BrowserAuth.RuntimeOwner.status().phase == :storage_ready
    c
  end

  defp rollback_stop!(conn, label) do
    try do
      Postgrex.query!(conn, "ROLLBACK", [])
    after
      GenServer.stop(conn)
      safe_save("lock-cleanup.jsonl", %{label: label, connection_stopped: true})
    end
  end

  defp lock_discriminator! do
    holder = F.connection!("browser_admin")

    try do
      contender = F.connection!("browser_admin")

      try do
        Postgrex.query!(holder, "BEGIN", [])
        Postgrex.query!(holder, "LOCK TABLE oban_jobs IN SHARE MODE", [])
        Postgrex.query!(contender, "BEGIN", [])
        [[timeout]] = Postgrex.query!(contender, "SHOW lock_timeout", []).rows
        access = Postgrex.query!(contender, "SELECT 1 FROM oban_jobs LIMIT 0", [])
        started = System.monotonic_time(:millisecond)
        result = Postgrex.query(contender, "LOCK TABLE oban_jobs IN ROW EXCLUSIVE MODE", [])
        elapsed = System.monotonic_time(:millisecond) - started

        code =
          case result do
            {:error, %Postgrex.Error{postgres: %{code: code}}} -> code
            _ -> :unexpected
          end

        safe_save("lock-discriminator.jsonl", %{
          holder: "SHARE",
          read: "SELECT 1 FROM oban_jobs LIMIT 0",
          read_command: access.command,
          read_rows: access.rows,
          blocked: "ROW EXCLUSIVE",
          sqlstate: code,
          lock_timeout: timeout,
          elapsed_ms: elapsed
        })

        assert timeout == "500ms"
        assert access.command == :select and access.rows == []
        assert {:error, %Postgrex.Error{postgres: %{code: :lock_not_available}}} = result
        IO.puts("R2204_DISCRIMINATOR_PASS SHARE_AccessShare_SELECT_RowExclusive_55P03_500ms")
      after
        rollback_stop!(contender, "discriminator-contender")
      end
    after
      rollback_stop!(holder, "discriminator-holder")
    end
  end

  defp query_text(%{query: q}) when is_binary(q), do: q

  defp query_text(%{query: q}) when is_list(q) do
    try do
      IO.iodata_to_binary(q)
    rescue
      _ -> nil
    end
  end

  defp query_text(_), do: nil

  def job_insert_kind(m) when is_map(m) do
    q = query_text(m)

    job =
      is_binary(q) and
        (Map.get(m, :source) == "oban_jobs" or
           Regex.match?(~r/^INSERT INTO (?:"[^"]+"\.)?"oban_jobs"(?:\s|\()/, q))

    case {job, Map.get(m, :result)} do
      {true, {:ok, %{command: :insert, num_rows: 1}}} -> :insert
      {true, {:error, _}} -> :failed
      _ -> :ignore
    end
  end

  def job_insert_kind(_), do: :ignore

  defp safe_save(name, data) do
    output =
      Path.join(
        System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
        "customer-create-observer"
      )

    File.mkdir_p!(output)
    File.write!(Path.join(output, name), Jason.encode!(data) <> "\n", [:append])
  end

  def observe(event, _, m, pid) when is_map(m) do
    q = query_text(m)

    if Map.get(m, :repo) == CreateRepo and is_binary(q) and
         String.starts_with?(q, "SELECT pg_catalog.pg_backend_pid()"),
       do: send(pid, {:connection, self(), Map.get(m, :result)})

    repo = Map.get(m, :repo)
    result = Map.get(m, :result)

    if repo == CreateRepo and is_binary(q) and String.starts_with?(q, "INSERT INTO ") do
      case result do
        {:ok, %{command: command, num_rows: n}} ->
          safe_save("actual-inserts.jsonl", %{
            event: event,
            repo: inspect(repo),
            source: Map.get(m, :source),
            query: q,
            command: command,
            num_rows: n,
            in_transaction: repo.in_transaction?()
          })

        _ ->
          :ok
      end
    end

    case job_insert_kind(m) do
      :insert ->
        in_transaction =
          repo in [CreateRepo, MixerHosted.Repo, MixerHosted.BrowserAuth.LifecycleRepo] and
            repo.in_transaction?()

        if in_transaction do
          [[user, session, backend, xact]] =
            Ecto.Adapters.SQL.query!(
              repo,
              "SELECT current_user::text,session_user::text,pg_backend_pid(),pg_current_xact_id()::text",
              [],
              log: false,
              timeout: 1000,
              queue: false
            ).rows

          witness = %{
            event: event,
            repo: inspect(repo),
            source: Map.get(m, :source),
            query: q,
            command: :insert,
            num_rows: 1,
            current_user: user,
            session_user: session,
            backend: backend,
            xact: xact,
            in_transaction: in_transaction
          }

          safe_save("job-insert-witnesses.jsonl", witness)
          send(pid, {:job_insert_witness, witness})
          send(pid, {:job_insert, self(), backend, xact})

          if repo != CreateRepo or user != "mixer_build_create" or session != "mixer_build_create",
            do: send(pid, {:observer_defect, :wrong_repo_or_role})

          case :persistent_term.get({__MODULE__, :expire}, false) do
            false ->
              :ok

            expiry ->
              delay = max(0, expiry * 1000 - System.system_time(:millisecond) + 20)

              safe_save(
                "expiry-witness.jsonl",
                Map.merge(witness, %{
                  expiry_delay_ms: delay,
                  at_ms: System.system_time(:millisecond)
                })
              )

              Process.sleep(delay)
          end
        else
          safe_save("observer-defect.jsonl", %{
            event: event,
            repo: inspect(repo),
            source: Map.get(m, :source),
            query: q,
            command: :insert,
            num_rows: 1,
            in_transaction: in_transaction
          })

          send(pid, {:observer_defect, :not_in_reported_repo_transaction})
        end

      :failed ->
        {:error, error} = result

        code =
          case error do
            %{postgres: %{code: code}} -> code
            _ -> :unknown
          end

        safe_save("failed-job-inserts.jsonl", %{
          event: event,
          repo: inspect(repo),
          source: Map.get(m, :source),
          query: q,
          sqlstate: code
        })

        send(pid, {:job_insert_failed, self(), code})

      :ignore ->
        :ok
    end

    :ok
  end

  def observe(_, _, _, _), do: :ok

  test "observer_handles_nonquery_nil_failed_and_qualified_metadata" do
    event = CreateRepo.config()[:telemetry_prefix] ++ [:query]
    :ok = :telemetry.attach("r2168-safety", event, &__MODULE__.observe/4, self())
    on_exit(fn -> :telemetry.detach("r2168-safety") end)

    for m <- [
          %{},
          %{query: nil, result: nil},
          %{query: "SELECT 1", result: nil},
          %{query: nil, source: "oban_jobs", result: {:ok, %{command: :insert, num_rows: 1}}}
        ] do
      :ok = :telemetry.execute(event, %{}, m)
      assert job_insert_kind(m) == :ignore
    end

    for q <- [
          ~s|INSERT INTO "oban_jobs" ("args") VALUES ($1)|,
          ~s|INSERT INTO "public"."oban_jobs" ("args") VALUES ($1)|
        ] do
      assert job_insert_kind(%{
               query: q,
               source: "oban_jobs",
               result: {:ok, %{command: :insert, num_rows: 1}}
             }) == :insert

      assert job_insert_kind(%{
               query: q,
               source: nil,
               result: {:ok, %{command: :insert, num_rows: 1}}
             }) == :insert

      assert job_insert_kind(%{query: q, source: "oban_jobs", result: {:error, :owned_control}}) ==
               :failed

      assert job_insert_kind(%{
               query: q,
               source: "oban_jobs",
               result: {:ok, %{command: :select, num_rows: 1}}
             }) == :ignore

      assert job_insert_kind(%{
               query: q,
               source: "oban_jobs",
               result: {:ok, %{command: :insert, num_rows: 0}}
             }) == :ignore
    end

    assert Enum.any?(:telemetry.list_handlers(event), &(&1.id == "r2168-safety"))
    assert collect([]) == []
  end

  def trace_loop do
    receive do
      {:trace, pid, :exception_from, mfa, {kind, reason}} ->
        safe_save("concurrent-exceptions.jsonl", %{
          pid: inspect(pid),
          mfa: inspect(mfa),
          kind: kind,
          reason: inspect(reason, limit: 8, printable_limit: 300)
        })

        trace_loop()

      {:trace, pid, :return_from, mfa, {:error, reason}} ->
        safe_save("concurrent-errors.jsonl", %{
          pid: inspect(pid),
          mfa: inspect(mfa),
          reason: inspect(reason, limit: 8, printable_limit: 300)
        })

        trace_loop()

      {:trace, pid, :call, {MixerHosted.BrowserAuth.Store, :failure, args}} ->
        safe_save("concurrent-failures.jsonl", %{pid: inspect(pid), stage: inspect(args)})
        trace_loop()

      :stop ->
        :ok

      _ ->
        trace_loop()
    end
  end

  defp observer_alive! do
    assert Enum.any?(
             :telemetry.list_handlers(CreateRepo.config()[:telemetry_prefix] ++ [:query]),
             &(&1.id == "r2112-physical")
           )
  end

  defp login(c) do
    preauth = bootstrap_http(c)
    b = begin_http(c, preauth)
    r = http(c, "/auth/callback?" <> b.query, b.headers)
    assert r.status == 303
    cookie = response_cookie(r)
    r = http(c, "/auth/session", headers(cookie))
    assert r.status == 200
    {cookie, Jason.decode!(r.body)["csrf_token"]}
  end

  defp body(overrides \\ %{}) do
    Map.merge(
      %{
        organization_id: "org-a",
        project_id: "project-a",
        application_id: "fieldlog",
        platform: "ios",
        source_input_id: "input-a",
        source_sha256: String.duplicate("a", 64),
        toolchain_lock_sha256: String.duplicate("b", 64),
        build_definition_sha256: String.duplicate("c", 64)
      },
      overrides
    )
  end

  defp post(c, cookie, csrf, key, b \\ body(), extra \\ []) do
    raw = if is_binary(b), do: b, else: Jason.encode!(b)

    hs =
      headers(cookie) ++
        [
          {"origin", c.config.public_origin},
          {"x-mixer-csrf", csrf},
          {"content-type", "application/json"},
          {"content-length", Integer.to_string(byte_size(raw))},
          {"idempotency-key", key}
        ] ++ extra

    http(c, "/console-api/v1/builds", hs, "POST", raw)
  end

  defp counts,
    do:
      {F.q!(Admin, "SELECT count(*) FROM mixer_builds").rows,
       F.q!(Admin, "SELECT count(*) FROM oban_jobs").rows}

  defp note(name), do: IO.puts("R2112_CONTROL_PASS " <> name)

  @tag :authenticated_customer_create_build_atomic_replay_pg_join
  test "authenticated_customer_create_build_atomic_replay_pg_join", c do
    event = CreateRepo.config()[:telemetry_prefix] ++ [:query]

    :ok =
      :telemetry.attach_many(
        "r2112-physical",
        Enum.uniq([
          event,
          MixerHosted.Repo.config()[:telemetry_prefix] ++ [:query],
          MixerHosted.BrowserAuth.LifecycleRepo.config()[:telemetry_prefix] ++ [:query]
        ]),
        &__MODULE__.observe/4,
        self()
      )

    on_exit(fn ->
      :telemetry.detach("r2112-physical")
      :persistent_term.erase({__MODULE__, :expire})
    end)

    levent = MixerHosted.BrowserAuth.LifecycleRepo.config()[:telemetry_prefix] ++ [:query]

    :ok =
      :telemetry.attach(
        "r2126-first-refusal",
        levent,
        fn _, _, m, _ ->
          case m.result do
            {:ok, %{rows: rows}} when is_list(rows) ->
              if Enum.any?(rows, fn row -> false in row end), do: :ok

            {:error, e} ->
              IO.puts(
                "R2126_SQL_ERROR " <>
                  inspect(%{query: IO.iodata_to_binary(m.query), error: e}, limit: :infinity)
              )

            _ ->
              :ok
          end
        end,
        nil
      )

    on_exit(fn -> :telemetry.detach("r2126-first-refusal") end)

    [[function_count]] =
      F.q!(Admin, "SELECT count(*) FROM pg_proc WHERE left(proname::text,14)='mixer_browser_'").rows

    assert function_count == 21

    assert {:ok, :frozen_v2_refused} =
             MixerHosted.BrowserAuth.LifecycleRepo.transaction(fn ->
               assert_raise MixerHosted.BrowserAuth.ActiveCatalog.Unavailable, fn ->
                 MixerHosted.BrowserAuth.ActiveCatalog.check_function_surface!(
                   MixerHosted.BrowserAuth.LifecycleRepo,
                   c.runtime.expected_roles,
                   System.monotonic_time(:millisecond) + 5000,
                   2
                 )
               end

               :frozen_v2_refused
             end)

    IO.puts(
      "R2126_FROZEN_REFUSAL_PROOF ActiveCatalog.functions!/3: live21 expected20; exact v2 rejected"
    )

    {cookie, csrf} = login(c)
    assert counts() == {[[0]], [[0]]}
    r = post(c, cookie, csrf, "positive")
    assert r.status == 201, r.body
    result = Jason.decode!(r.body)
    assert Enum.sort(Map.keys(result)) == ~w(outcome revision selection state)
    assert result["state"] == "queued" and result["revision"] == 0
    assert counts() == {[[1]], [[1]]}
    [[id, journal]] = F.q!(Admin, "SELECT id::text,journal FROM mixer_builds").rows
    [[args, state]] = F.q!(Admin, "SELECT args,state::text FROM oban_jobs").rows

    assert args["build_record_id"] == id and args["revision"] == 0 and args["attempt"] == 1 and
             args["fence"] == 1 and args["kind"] == "created" and state == "available"

    assert {:ok, _} = MixerHosted.Builds.Journal.restore(journal)
    events = collect([])
    pairs = for {:connection, _, {:ok, %{rows: [[pid, xact | _]]}}} <- events, do: {pid, xact}
    assert length(pairs) >= 4
    assert length(Enum.uniq(pairs)) == 1
    job_pairs = for {:job_insert, _, pid, xact} <- events, do: {pid, xact}
    assert job_pairs == Enum.uniq(pairs)

    assert [{:job_insert_witness, witness}] =
             Enum.filter(events, &match?({:job_insert_witness, _}, &1))

    assert witness.repo == inspect(CreateRepo) and witness.in_transaction

    assert witness.current_user == "mixer_build_create" and
             witness.session_user == "mixer_build_create"

    refute Enum.any?(events, &match?({:observer_defect, _}, &1))
    observer_alive!()

    File.write!(
      Path.join(
        System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"),
        "physical-transaction.json"
      ),
      Jason.encode!(%{
        physical_connections: Enum.map(pairs, fn {pid, xact} -> [pid, xact] end),
        job_insert: witness
      })
    )

    note("actual_http_pkce_cookie_csrf_atomic_one_physical_transaction")
    r = post(c, cookie, csrf, "positive")
    assert r.status == 200 and Jason.decode!(r.body)["selection"] == result["selection"]
    tracer = spawn(&__MODULE__.trace_loop/0)

    modules = [
      MixerHosted.BrowserAuth.Store,
      MixerHosted.BrowserAuth.ActiveRead,
      MixerHosted.BrowserAuth.RuntimeOwner,
      MixerHosted.BrowserAuth.RelationCatalog,
      MixerHosted.BrowserAuth.ActiveCatalog,
      MixerHosted.BrowserAuth.BuildCatalogAdmission,
      MixerHosted.Identity.ConfiguredVerifier,
      MixerHosted.Identity.Admission,
      MixerHosted.Identity.KeyOwner,
      MixerHosted.Authorization,
      MixerHosted.CustomerBuilds.Create,
      MixerHosted.CustomerBuilds.CreateSchema
    ]

    for m <- modules,
        do: :erlang.trace_pattern({m, :_, :_}, [{:_, [], [{:exception_trace}]}], [:local])

    :erlang.trace(:all, true, [:call, {:tracer, tracer}])

    on_exit(fn ->
      :erlang.trace(:all, false, [:call])
      for m <- modules, do: :erlang.trace_pattern({m, :_, :_}, false, [:local])
      send(tracer, :stop)
    end)

    tasks = for _ <- 1..2, do: Task.async(fn -> post(c, cookie, csrf, "concurrent") end)

    statuses =
      tasks
      |> Enum.map(fn task ->
        response = Task.await(task, 7000)
        safe_save("concurrent-responses.jsonl", Map.take(response, [:status, :body]))
        response
      end)
      |> Enum.map(& &1.status)
      |> Enum.sort()

    assert statuses == [200, 201], inspect(statuses)
    assert counts() == {[[2]], [[2]]}
    note("exact_and_concurrent_replay")

    for b <- [
          body(%{source_sha256: String.duplicate("d", 64)}),
          body(%{source_input_id: "input-b"})
        ] do
      assert post(c, cookie, csrf, "positive", b).status == 409
    end

    assert post(c, cookie, csrf, "hidden", body(%{source_input_id: "missing"})).status == 404

    assert post(
             c,
             cookie,
             csrf,
             "hidden",
             body(%{organization_id: "org-b", project_id: "project-b"})
           ).status == 404

    note("changed_pin_idempotency_and_hidden_source_scope")

    for {badcsrf, extra} <- [
          {MixerHosted.BrowserAuth.Protocol.random_token(), []},
          {csrf, [{"origin", "https://wrong.invalid"}]},
          {csrf, [{"x-mixer-csrf", csrf}]}
        ] do
      assert post(c, cookie, badcsrf, "csrf-denied", body(), extra).status == 403
    end

    assert post(
             c,
             cookie,
             csrf,
             "bad-json",
             "{\"organization_id\":\"org-a\",\"organization_id\":\"org-a\"}"
           ).status == 400

    for role <- ~w(viewer billing_manager release_manager) do
      F.q!(Admin, "UPDATE mixer_authz_memberships SET role=$1 WHERE id='member-a'", [role])
      assert post(c, cookie, csrf, "denied-role").status == 403
    end

    F.q!(Admin, "UPDATE mixer_authz_memberships SET role='developer' WHERE id='member-a'")
    assert counts() == {[[2]], [[2]]}
    note("csrf_origin_duplicate_json_and_role_refusals")

    for sql <- [
          "INSERT INTO mixer_builds DEFAULT VALUES",
          "DELETE FROM mixer_builds",
          "INSERT INTO oban_jobs DEFAULT VALUES",
          "DELETE FROM oban_jobs"
        ] do
      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Ecto.Adapters.SQL.query(MixerHosted.Repo, sql, [])
    end

    note("ordinary_direct_dml_42501")

    read =
      http(c, "/console-api/v1/builds?" <> URI.encode_query(result["selection"]), headers(cookie))

    assert read.status == 200, read.body
    note("existing_get")
    # Exact owned admin lock blocks only the actual job INSERT; PostgreSQL's
    # unchanged500ms lock timeout refuses it and the outer transaction rolls back.
    conn = F.connection!("browser_admin")

    r =
      try do
        Postgrex.query!(conn, "BEGIN", [])
        Postgrex.query!(conn, "LOCK TABLE oban_jobs IN SHARE MODE", [])
        collect([])
        r = post(c, cookie, csrf, "rollback-job")
        failed_events = collect([])
        observer_alive!()
        assert Enum.any?(failed_events, &match?({:job_insert_failed, _, _}, &1))
        r
      after
        rollback_stop!(conn, "actual-job-insert-refusal")
      end

    assert r.status == 503, r.body
    assert counts() == {[[2]], [[2]]}
    note("actual_oban_insertion_error_rollback")
    r = post(c, cookie, csrf, "rollback-job")
    assert r.status == 201, r.body
    assert counts() == {[[3]], [[3]]}
    # A fresh PKCE identity expires after actual INSERT via test telemetry only.
    :ok = GenServer.call(c.provider, {:mode, :short})
    {short_cookie, short_csrf} = login(c)

    session =
      http(c, "/auth/session", headers(short_cookie)) |> Map.fetch!(:body) |> Jason.decode!()

    :persistent_term.put({__MODULE__, :expire}, session["expires_at"])
    collect([])
    r = post(c, short_cookie, short_csrf, "rollback-expiry")
    expiry_events = collect([])
    observer_alive!()

    assert [{:job_insert, _, expiry_pid, expiry_xact}] =
             Enum.filter(expiry_events, &match?({:job_insert, _, _, _}, &1))

    assert is_integer(expiry_pid) and is_binary(expiry_xact)

    expiry_pairs =
      for {:connection, _, {:ok, %{rows: [[pid, xact | _]]}}} <- expiry_events, do: {pid, xact}

    assert Enum.uniq(expiry_pairs) == [{expiry_pid, expiry_xact}]

    assert [{:job_insert_witness, expiry_witness}] =
             Enum.filter(expiry_events, &match?({:job_insert_witness, _}, &1))

    assert expiry_witness.repo == inspect(CreateRepo) and expiry_witness.in_transaction

    assert expiry_witness.current_user == "mixer_build_create" and
             expiry_witness.session_user == "mixer_build_create"

    refute Enum.any?(expiry_events, &match?({:observer_defect, _}, &1))
    :persistent_term.erase({__MODULE__, :expire})
    assert r.status in [401, 503], r.body
    assert counts() == {[[3]], [[3]]}
    note("post_job_insert_final_expiry_rollback")
    :ok = GenServer.call(c.provider, {:mode, :no_build_scope})
    {scope_cookie, scope_csrf} = login(c)
    assert post(c, scope_cookie, scope_csrf, "missing-create-scope").status == 403
    assert counts() == {[[3]], [[3]]}
    note("authenticated_missing_create_scope_cookie")
    F.q!(Admin, "UPDATE mixer_authz_credentials SET active=false")
    assert post(c, cookie, csrf, "revoked").status in [401, 503]
    assert counts() == {[[3]], [[3]]}
    note("revocation_no_effect")
    leases_clean()
  end

  defp collect(acc) do
    receive do
      e
      when elem(e, 0) in [
             :connection,
             :job_insert,
             :job_insert_failed,
             :job_insert_witness,
             :observer_defect
           ] ->
        collect([e | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end
end
