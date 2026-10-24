defmodule MixerCatalogInspector.RuntimeRepo do
  use Ecto.Repo, otp_app: :mixer_catalog_inspector, adapter: Ecto.Adapters.Postgres
end

defmodule MixerCatalogInspector.CatalogRepo do
  use Ecto.Repo, otp_app: :mixer_catalog_inspector, adapter: Ecto.Adapters.Postgres
end

defmodule MixerCatalogInspector.RuntimeTest do
  use ExUnit.Case, async: false
  alias MixerCatalogInspector.{Evidence, RuntimeRepo, CatalogRepo}
  alias MixerHosted.CatalogInspector
  alias MixerHosted.CatalogInspector.Raw

  def record(_event, _measurements, metadata, _config) do
    if Keyword.get(metadata.options, :mixer_catalog_inspector, false) do
      result =
        case metadata.result do
          {:ok, %Postgrex.Result{rows: rows, connection_id: backend}} ->
            %{rows: rows, backend: backend}

          {:error, %Postgrex.Error{postgres: fields}} ->
            %{error: inspect(fields), sqlstate: fields[:pg_code]}

          {:error, error} ->
            %{error: inspect(error)}
        end

      entry = %{query: metadata.query, params: metadata.params, result: result}
      Process.put(:catalog_trace, [entry | Process.get(:catalog_trace, [])])
      if hook = Process.get(:catalog_hook), do: hook.(metadata)
    end
  end

  setup_all do
    socket = System.fetch_env!("MIXER_INSPECTOR_SOCKET")
    {:ok, _} = Application.ensure_all_started(:ecto_sql)
    {:ok, _} = Application.ensure_all_started(:postgrex)

    {:ok, admin} =
      Postgrex.start_link(
        socket_dir: socket,
        database: "authority_contract",
        username: System.fetch_env!("USER")
      )

    {:ok, _repo} =
      RuntimeRepo.start_link(
        socket_dir: socket,
        database: "authority_contract",
        username: "mixer_hosted_runtime",
        pool_size: 1,
        prepare: :unnamed,
        telemetry_prefix: [:catalog_inspector, :runtime]
      )

    {:ok, _observer} =
      CatalogRepo.start_link(
        socket_dir: socket,
        database: "authority_contract",
        username: "catalog_inspector_observer",
        pool_size: 1,
        prepare: :unnamed,
        telemetry_prefix: [:catalog_inspector, :observer]
      )

    Ecto.Adapters.SQL.query!(RuntimeRepo, "SELECT 1", [], timeout: 2000, log: false)
    Ecto.Adapters.SQL.query!(CatalogRepo, "SELECT 1", [], timeout: 2000, log: false)

    :ok =
      :telemetry.attach_many(
        "mixer-catalog-inspector-test",
        [[:catalog_inspector, :runtime, :query], [:catalog_inspector, :observer, :query]],
        &__MODULE__.record/4,
        nil
      )

    on_exit(fn -> :telemetry.detach("mixer-catalog-inspector-test") end)
    %{admin: admin}
  end

  setup context do
    Process.put(:catalog_trace, [])
    Process.delete(:catalog_hook)
    name = context.test |> Atom.to_string() |> String.replace(~r/[^a-zA-Z0-9]+/, "-")
    on_exit(fn -> :ok end)
    {:ok, evidence_name: name}
  end

  defp q(admin, statements) when is_list(statements),
    do: statements |> Enum.map(&q(admin, &1)) |> List.last()

  defp q(admin, sql), do: Postgrex.query!(admin, sql, [], timeout: 10_000)

  defp observer(sql),
    do: Ecto.Adapters.SQL.query!(CatalogRepo, sql, [], timeout: 2000, log: false)

  defp runtime(sql), do: Ecto.Adapters.SQL.query!(RuntimeRepo, sql, [], timeout: 2000, log: false)
  defp verify, do: CatalogInspector.verify(CatalogRepo, RuntimeRepo)

  defp success,
    do:
      {:ok,
       %{
         manifest_sha256: "a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395",
         snapshot_scope: :point_in_time
       }}

  defp trace, do: Process.get(:catalog_trace, []) |> Enum.reverse()

  defp save_trace(name) do
    File.write!(Evidence.path(name <> ".json.gz"), :zlib.gzip(Jason.encode!(trace())))
  end

  defp closed!(admin) do
    [[backend, isolation, read_only, path, lock_timeout, statement_timeout, idle_timeout]] =
      observer(
        "SELECT pg_backend_pid(), current_setting('transaction_isolation'), current_setting('transaction_read_only'), current_setting('search_path'), current_setting('lock_timeout'), current_setting('statement_timeout'), current_setting('idle_in_transaction_session_timeout')"
      ).rows

    assert isolation == "read committed"
    assert read_only == "off"
    assert path == "\"$user\", public"
    assert lock_timeout == "0"
    assert statement_timeout == "0"
    assert idle_timeout == "0"

    assert q(admin, "SELECT state, xact_start IS NULL FROM pg_stat_activity WHERE pid=#{backend}").rows ==
             [["idle", true]]

    %{backend: backend, state: "idle", transaction_closed: true, local_settings_restored: true}
  end

  defp baseline_raw do
    legacy =
      trace()
      |> Enum.find(&String.contains?(&1.query, "'server_version'"))
      |> Map.fetch!(:result)
      |> Map.fetch!(:rows)
      |> hd()
      |> hd()
      |> Raw.decode!()

    enforcement =
      trace()
      |> Enum.find(&String.contains?(&1.query, "'relations'"))
      |> Map.fetch!(:result)
      |> Map.fetch!(:rows)
      |> hd()
      |> hd()
      |> Raw.decode!()

    session =
      trace()
      |> Enum.find(&String.contains?(&1.query, "'session_user',session_user"))
      |> Map.fetch!(:result)
      |> Map.fetch!(:rows)
      |> hd()
      |> hd()
      |> Raw.decode!()

    %{"legacy" => legacy, "enforcement" => enforcement, "fresh_session" => session}
  end

  defp settle_original!(admin, backend, remaining \\ 1000, samples \\ []) do
    state =
      q(admin, "SELECT state, xact_start IS NULL FROM pg_stat_activity WHERE pid=#{backend}").rows

    samples = [%{remaining_cleanup_ms: remaining, state: state} | samples]

    if state in [[], [["idle", true]]] do
      %{final_state: state, samples: Enum.reverse(samples), observed_original_cleanup: true}
    else
      assert remaining > 0, "original backend did not settle within separate cleanup budget"
      Process.sleep(10)
      settle_original!(admin, backend, remaining - 10, samples)
    end
  end

  test "separate observer and runtime reads accept the isolated profile with fresh portable OIDs",
       %{admin: admin, evidence_name: name} do
    try do
      assert verify() == success()
      raw = baseline_raw()
      expected = File.read!("priv/observer-profile.json") |> Jason.decode!()
      assert Raw.normalize!(raw) === expected

      original =
        System.fetch_env!("MIXER_INSPECTOR_INPUTS")
        |> Path.join("baseline.json.gz")
        |> File.read!()
        |> :zlib.gunzip()
        |> Raw.decode!()

      assert Enum.map(raw["enforcement"]["relations"], & &1["oid"]) !=
               Enum.map(original["enforcement"]["relations"], & &1["oid"])

      names = fn x -> for t <- x["enforcement"]["triggers"], t["internal"], do: t["name"] end
      assert names.(raw) != names.(original)
      File.write!(Evidence.path("baseline-capture.json.gz"), :zlib.gzip(Jason.encode!(raw)))
      rows = raw["enforcement"]
      counts = Map.new(~w(relations constraints indexes triggers), &{&1, length(rows[&1])})

      assert counts == %{
               "relations" => 14,
               "constraints" => 89,
               "indexes" => 26,
               "triggers" => 74
             }

      assert Enum.count(trace(), &String.starts_with?(&1.query, "SELECT (SELECT count(*)")) == 1

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        counts: counts,
        fresh_oids_and_names: true,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "ordinary drift rejects and both successful and failed calls close the original transaction",
       %{admin: admin, evidence_name: name} do
    try do
      original_backend = observer("SELECT pg_backend_pid()").rows
      q(admin, "ALTER TABLE mixer_authz.applications DISABLE TRIGGER lifecycle_guard")

      try do
        assert verify() == {:error, :catalog_mismatch}
        cleanup = closed!(admin)
        assert [[cleanup.backend]] == original_backend
      after
        q(admin, "ALTER TABLE mixer_authz.applications ENABLE TRIGGER lifecycle_guard")
      end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        mismatch_rejected: true,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "positive OID literal-star roles and defaults validate raw but selected comparison rejects",
       %{admin: admin, evidence_name: name} do
    try do
      q(admin, [
        "CREATE ROLE \"*\" NOLOGIN",
        "GRANT \"*\" TO mixer_hosted_runtime",
        "ALTER ROLE \"*\" SET application_name=inspector_star"
      ])

      try do
        assert verify() == {:error, :catalog_mismatch}
        raw = baseline_raw()
        assert :ok == Raw.validate!(raw)

        assert Enum.any?(
                 raw["enforcement"]["startup_defaults"],
                 &(&1["role"] == "*" and &1["role_oid"] > 0 and &1["database_oid"] == 0)
               )

        File.write!(Evidence.path("literal-star-capture.json.gz"), :zlib.gzip(Jason.encode!(raw)))
        closed!(admin)
      after
        q(admin, [
          "ALTER ROLE \"*\" RESET application_name",
          "REVOKE \"*\" FROM mixer_hosted_runtime",
          "DROP ROLE \"*\""
        ])
      end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        valid_raw_star: true,
        selected_rejection: true,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "nested transaction and checked-out calls reject without adopting their context", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      assert RuntimeRepo.transaction(fn -> verify() end) == {:ok, {:error, :catalog_unavailable}}
      assert RuntimeRepo.checkout(fn -> verify() end) == {:error, :catalog_unavailable}
      assert trace() == []
      Evidence.save(name <> "-outcome.json", %{passed: true, cleanup: closed!(admin)})
    after
      save_trace(name)
    end
  end

  test "queue false rejects pool occupancy promptly without starting inspection", %{
    admin: admin,
    evidence_name: name
  } do
    owner = self()

    task =
      Task.async(fn ->
        RuntimeRepo.checkout(
          fn ->
            send(owner, :occupied)

            receive do
              :release -> :ok
            end
          end, timeout: 3000)
      end)

    assert_receive :occupied, 1000
    started = System.monotonic_time(:millisecond)

    try do
      assert verify() == {:error, :catalog_unavailable}
      elapsed = System.monotonic_time(:millisecond) - started
      assert elapsed < 1000
      assert trace() == []
      send(task.pid, :release)
      Task.await(task)

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        elapsed_ms: elapsed,
        cleanup: closed!(admin)
      })
    after
      send(task.pid, :release)
      save_trace(name)
    end
  end

  test "unsafe fresh-session state rejects before BEGIN and is never repaired by inspector", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      runtime("SET row_security=off")

      try do
        assert verify() == {:error, :catalog_mismatch}
        assert length(trace()) == 1
        assert runtime("SHOW row_security").rows == [["off"]]
      after
        runtime("RESET row_security")
      end

      assert verify() == success()
      Evidence.save(name <> "-outcome.json", %{passed: true, cleanup: closed!(admin)})
    after
      save_trace(name)
    end
  end

  test "catalog lock timeout reports actual SQLSTATE and rolls back", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      q(admin, ["BEGIN", "LOCK TABLE pg_catalog.pg_auth_members IN ACCESS EXCLUSIVE MODE"])
      started = System.monotonic_time(:millisecond)

      try do
        assert verify() == {:error, :catalog_unavailable}
        elapsed = System.monotonic_time(:millisecond) - started
        assert elapsed >= 200 and elapsed < 2500
        assert Enum.any?(trace(), &(&1.result[:sqlstate] == "55P03"))
        cleanup = closed!(admin)

        Evidence.save(name <> "-outcome.json", %{
          passed: true,
          elapsed_ms: elapsed,
          sqlstate: "55P03",
          cleanup: cleanup
        })
      after
        q(admin, "ROLLBACK")
      end

      assert verify() == success()
    after
      save_trace(name)
    end
  end

  test "expired absolute deadline cannot return success and cleanup is observed separately", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      original = observer("SELECT pg_backend_pid()").rows |> hd() |> hd()

      Process.put(:catalog_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
          Process.delete(:catalog_hook)
          Process.sleep(5050)
        end
      end)

      started = System.monotonic_time(:millisecond)
      assert verify() == {:error, :catalog_unavailable}
      elapsed = System.monotonic_time(:millisecond) - started
      Process.delete(:catalog_hook)
      assert elapsed >= 5000 and elapsed < 8000
      original_state = settle_original!(admin, original)
      # Driver may retire a connection whose checkout deadline expired. Any
      # replacement is inspected anew; its existence cannot rescue this call.
      Process.sleep(100)
      cleanup = closed!(admin)

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        elapsed_ms: elapsed,
        original_backend: original,
        original_state: original_state,
        replacement: cleanup.backend != original,
        cleanup: cleanup
      })

      assert verify() == success()
    after
      Process.delete(:catalog_hook)
      save_trace(name)
    end
  end

  test "backend termination fails closed and a later connection requires fresh full verification",
       %{admin: admin, evidence_name: name} do
    try do
      original = observer("SELECT pg_backend_pid()").rows |> hd() |> hd()

      Process.put(:catalog_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
          Process.delete(:catalog_hook)
          q(admin, "SELECT pg_terminate_backend(#{original})")
        end
      end)

      assert verify() == {:error, :catalog_unavailable}
      Process.delete(:catalog_hook)
      assert q(admin, "SELECT 1 FROM pg_stat_activity WHERE pid=#{original}").rows == []
      Process.sleep(100)
      cleanup = closed!(admin)
      assert cleanup.backend != original
      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        retired_backend: original,
        cleanup: cleanup
      })
    after
      Process.delete(:catalog_hook)
      save_trace(name)
    end
  end

  test "server output envelope and raw string cap reject independently before comparison", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      observations =
        for {bytes, expected} <- [
              {1_048_577, :malformed_catalog},
              {4_194_305, :catalog_unavailable}
            ] do
          sql =
            "CREATE FUNCTION mixer_authz.inspector_oversized() RETURNS boolean LANGUAGE sql AS $bounded$ SELECT true /*" <>
              String.duplicate("x", bytes) <> "*/ $bounded$"

          File.write!(Evidence.path("oversize-#{bytes}.sql.gz"), :zlib.gzip(sql))
          q(admin, sql)
          q(admin, "REVOKE ALL ON FUNCTION mixer_authz.inspector_oversized() FROM PUBLIC")

          try do
            assert verify() == {:error, expected}
            closed!(admin)
            %{body_padding_bytes: bytes, expected: expected, passed: true}
          after
            q(admin, "DROP FUNCTION mixer_authz.inspector_oversized()")
          end
        end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        cases: observations,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "same read-only repeatable-read snapshot remains coherent across a concurrent committed catalog change",
       %{admin: admin, evidence_name: name} do
    try do
      Process.put(:catalog_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
          Process.delete(:catalog_hook)
          q(admin, "ALTER ROLE mixer_hosted_runtime SET application_name=inspector_concurrent")
        end
      end)

      try do
        # This is expected snapshot behavior, explicitly not concurrent-DDL
        # exclusion: publication must be coordinated separately by bootstrap.
        assert verify() == success()
        Process.delete(:catalog_hook)
        assert verify() == {:error, :catalog_mismatch}
        closed!(admin)
      after
        q(admin, "ALTER ROLE mixer_hosted_runtime RESET application_name")
      end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        snapshot_coherent: true,
        concurrent_ddl_protection: false,
        next_inspection_rejected: true,
        cleanup: closed!(admin)
      })
    after
      Process.delete(:catalog_hook)
      save_trace(name)
    end
  end

  test "profile ACL variants fail closed without widening runtime authority", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      variants = [
        {"observer CONNECT grant option",
         "GRANT CONNECT ON DATABASE authority_contract TO catalog_inspector_observer WITH GRANT OPTION",
         "REVOKE GRANT OPTION FOR CONNECT ON DATABASE authority_contract FROM catalog_inspector_observer"},
        {"observer TEMP",
         "GRANT TEMP ON DATABASE authority_contract TO catalog_inspector_observer",
         "REVOKE TEMP ON DATABASE authority_contract FROM catalog_inspector_observer"},
        {"observer CREATE",
         "GRANT CREATE ON DATABASE authority_contract TO catalog_inspector_observer",
         "REVOKE CREATE ON DATABASE authority_contract FROM catalog_inspector_observer"},
        {"PUBLIC CONNECT", "GRANT CONNECT ON DATABASE authority_contract TO PUBLIC",
         "REVOKE CONNECT ON DATABASE authority_contract FROM PUBLIC"},
        {"PUBLIC TEMP", "GRANT TEMP ON DATABASE authority_contract TO PUBLIC",
         "REVOKE TEMP ON DATABASE authority_contract FROM PUBLIC"},
        {"PUBLIC CREATE", "GRANT CREATE ON DATABASE authority_contract TO PUBLIC",
         "REVOKE CREATE ON DATABASE authority_contract FROM PUBLIC"},
        {"runtime CONNECT grant option",
         "GRANT CONNECT ON DATABASE authority_contract TO mixer_hosted_runtime WITH GRANT OPTION",
         "REVOKE GRANT OPTION FOR CONNECT ON DATABASE authority_contract FROM mixer_hosted_runtime"}
      ]

      outcomes =
        for {label, mutation, restoration} <- variants do
          q(admin, mutation)

          result =
            try do
              assert {:error, reason} = verify()
              assert reason in [:catalog_mismatch, :catalog_unavailable]
              closed!(admin)
              reason
            after
              q(admin, restoration)
            end

          assert verify() == success()
          %{label: label, result: result, passed: true}
        end

      q(admin, [
        "CREATE ROLE inspector_extra_connect NOLOGIN",
        "GRANT CONNECT ON DATABASE authority_contract TO inspector_extra_connect"
      ])

      try do
        assert verify() == {:error, :catalog_mismatch}
      after
        q(admin, [
          "REVOKE CONNECT ON DATABASE authority_contract FROM inspector_extra_connect",
          "DROP ROLE inspector_extra_connect"
        ])
      end

      assert verify() == success()

      assert {:error, %Postgrex.Error{postgres: %{pg_code: "42501"}}} =
               Ecto.Adapters.SQL.query(RuntimeRepo, "SET ROLE catalog_inspector_observer", [],
                 log: false
               )

      assert {:error, %Postgrex.Error{postgres: %{pg_code: "42501"}}} =
               Ecto.Adapters.SQL.query(RuntimeRepo, "SET ROLE mixer_hosted_schema_owner", [],
                 log: false
               )

      assert {:error, %Postgrex.Error{postgres: %{pg_code: "42501"}}} =
               Ecto.Adapters.SQL.query(RuntimeRepo, "SELECT * FROM mixer_authz.principals", [],
                 log: false
               )

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        variants: outcomes,
        extra_connect_rejected: true,
        runtime_privilege_denials: 3,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "observer capability membership option and ownership drift rejects before comparison", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      variants = [
        {"SUPERUSER", "ALTER ROLE catalog_inspector_observer SUPERUSER",
         "ALTER ROLE catalog_inspector_observer NOSUPERUSER"},
        {"BYPASSRLS", "ALTER ROLE catalog_inspector_observer BYPASSRLS",
         "ALTER ROLE catalog_inspector_observer NOBYPASSRLS"},
        {"CREATEDB", "ALTER ROLE catalog_inspector_observer CREATEDB",
         "ALTER ROLE catalog_inspector_observer NOCREATEDB"},
        {"CREATEROLE", "ALTER ROLE catalog_inspector_observer CREATEROLE",
         "ALTER ROLE catalog_inspector_observer NOCREATEROLE"},
        {"REPLICATION", "ALTER ROLE catalog_inspector_observer REPLICATION",
         "ALTER ROLE catalog_inspector_observer NOREPLICATION"},
        {"NOLOGIN", "ALTER ROLE catalog_inspector_observer NOLOGIN",
         "ALTER ROLE catalog_inspector_observer LOGIN"},
        {"NOINHERIT", "ALTER ROLE catalog_inspector_observer NOINHERIT",
         "ALTER ROLE catalog_inspector_observer INHERIT"},
        {"membership ADMIN",
         "GRANT pg_read_all_settings TO catalog_inspector_observer WITH ADMIN TRUE",
         "GRANT pg_read_all_settings TO catalog_inspector_observer WITH ADMIN FALSE"},
        {"membership SET",
         "GRANT pg_read_all_settings TO catalog_inspector_observer WITH SET TRUE",
         "GRANT pg_read_all_settings TO catalog_inspector_observer WITH SET FALSE"},
        {"membership INHERIT",
         "GRANT pg_read_all_settings TO catalog_inspector_observer WITH INHERIT FALSE",
         "GRANT pg_read_all_settings TO catalog_inspector_observer WITH INHERIT TRUE"},
        {"owned schema", "CREATE SCHEMA inspector_owned AUTHORIZATION catalog_inspector_observer",
         "DROP SCHEMA inspector_owned"},
        {"protected SELECT",
         "GRANT SELECT ON mixer_authz.principals TO catalog_inspector_observer",
         "REVOKE SELECT ON mixer_authz.principals FROM catalog_inspector_observer"}
      ]

      outcomes =
        for {label, mutation, restoration} <- variants do
          q(admin, mutation)

          try do
            assert verify() == {:error, :catalog_unavailable}
            closed!(admin)
          after
            q(admin, restoration)
          end

          assert verify() == success()
          %{label: label, passed: true}
        end

      q(admin, [
        "CREATE ROLE inspector_unknown_role NOLOGIN",
        "GRANT inspector_unknown_role TO catalog_inspector_observer WITH ADMIN FALSE, INHERIT TRUE, SET FALSE"
      ])

      try do
        assert verify() == {:error, :catalog_unavailable}
      after
        q(admin, [
          "REVOKE inspector_unknown_role FROM catalog_inspector_observer",
          "DROP ROLE inspector_unknown_role"
        ])
      end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        variants: outcomes,
        unknown_membership_rejected: true,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "runtime session changes and dynamic Repo confusion during observer inspection fail closed",
       %{admin: admin, evidence_name: name} do
    try do
      Process.put(:catalog_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
          Process.delete(:catalog_hook)
          runtime("SET row_security=off")
        end
      end)

      try do
        assert verify() == {:error, :catalog_mismatch}
      after
        Process.delete(:catalog_hook)
        runtime("RESET row_security")
      end

      closed!(admin)
      original = RuntimeRepo.get_dynamic_repo()

      Process.put(:catalog_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
          Process.delete(:catalog_hook)
          RuntimeRepo.put_dynamic_repo(CatalogRepo)
        end
      end)

      try do
        assert verify() == {:error, :catalog_unavailable}
      after
        Process.delete(:catalog_hook)
        RuntimeRepo.put_dynamic_repo(original)
      end

      assert CatalogInspector.verify(RuntimeRepo) == {:error, :catalog_unavailable}
      assert CatalogInspector.verify(CatalogRepo, CatalogRepo) == {:error, :catalog_unavailable}
      assert CatalogInspector.verify(RuntimeRepo, RuntimeRepo) == {:error, :catalog_unavailable}
      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        after_runtime_session_rejection: true,
        dynamic_confusion_rejected: true,
        same_repo_rejections: 2,
        cleanup: closed!(admin)
      })
    after
      Process.delete(:catalog_hook)
      save_trace(name)
    end
  end

  test "global cardinality preflight rejects without truncating selected observations", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      creation =
        "DO $bounded$ BEGIN FOR i IN 1..4096 LOOP EXECUTE 'CREATE ROLE inspector_count_' || i || ' NOLOGIN'; END LOOP; END $bounded$"

      removal =
        "DO $bounded$ BEGIN FOR i IN 1..4096 LOOP EXECUTE 'DROP ROLE inspector_count_' || i; END LOOP; END $bounded$"

      q(admin, creation)

      try do
        assert verify() == {:error, :catalog_unavailable}
        assert not Enum.any?(trace(), &String.contains?(&1.query, "'server_version'"))

        assert Enum.any?(trace(), fn t ->
                 String.starts_with?(t.query, "SELECT (SELECT count(*)") and
                   false in hd(t.result.rows)
               end)

        closed!(admin)
      after
        q(admin, removal)
      end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        added_roles: 4096,
        ceiling: 4096,
        full_capture_skipped_on_overflow: true,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end

  test "remaining statement timeout emits SQLSTATE57014 before any catalog acceptance", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      original = observer("SELECT pg_backend_pid()").rows |> hd() |> hd()
      q(admin, ["BEGIN", "LOCK TABLE pg_catalog.pg_auth_members IN ACCESS EXCLUSIVE MODE"])

      Process.put(:catalog_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT pg_backend_pid(), session_user::text") do
          Process.delete(:catalog_hook)
          Process.sleep(4850)
        end
      end)

      started = System.monotonic_time(:millisecond)

      try do
        assert verify() == {:error, :catalog_unavailable}
        assert Enum.any?(trace(), &(&1.result[:sqlstate] == "57014"))
      after
        Process.delete(:catalog_hook)
        q(admin, "ROLLBACK")
      end

      elapsed = System.monotonic_time(:millisecond) - started
      assert elapsed >= 4800 and elapsed < 8000
      original_state = settle_original!(admin, original)
      Process.sleep(100)
      cleanup = closed!(admin)
      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        elapsed_ms: elapsed,
        sqlstate: "57014",
        original_backend: original,
        original_state: original_state,
        cleanup: cleanup
      })
    after
      Process.delete(:catalog_hook)
      save_trace(name)
    end
  end

  test "qualified runtime queries resist hostile search_path function shadows", %{
    admin: admin,
    evidence_name: name
  } do
    try do
      q(admin, [
        "CREATE SCHEMA inspector_shadow",
        "GRANT USAGE ON SCHEMA inspector_shadow TO mixer_hosted_runtime",
        "CREATE FUNCTION inspector_shadow.current_setting(text) RETURNS text LANGUAGE sql AS $shadow$ SELECT CASE $1 WHEN 'role' THEN 'none' WHEN 'session_replication_role' THEN 'origin' WHEN 'row_security' THEN 'on' WHEN 'transaction_read_only' THEN 'off' ELSE 'read committed' END $shadow$",
        "CREATE FUNCTION inspector_shadow.current_database() RETURNS name LANGUAGE sql AS $shadow$ SELECT 'authority_contract'::name $shadow$",
        "CREATE FUNCTION inspector_shadow.pg_backend_pid() RETURNS integer LANGUAGE sql AS $shadow$ SELECT 42 $shadow$"
      ])

      try do
        runtime("SET search_path=inspector_shadow,pg_catalog")
        runtime("SET row_security=off")

        assert runtime("SELECT current_setting('row_security'), pg_backend_pid()").rows == [
                 ["on", 42]
               ]

        original = runtime(File.read!("priv/session-original.sql")).rows |> hd() |> hd()

        expected_session =
          File.read!("priv/selected-expected.json")
          |> Jason.decode!()
          |> Map.fetch!("fresh_session")

        assert original === expected_session
        assert verify() == {:error, :catalog_mismatch}
        runtime("SET row_security=on")
        assert verify() == success()
        assert runtime("SELECT pg_catalog.pg_backend_pid()=42").rows == [[false]]
      after
        runtime("RESET row_security")
        runtime("RESET search_path")
        q(admin, "DROP SCHEMA inspector_shadow CASCADE")
      end

      assert verify() == success()

      Evidence.save(name <> "-outcome.json", %{
        passed: true,
        original_unqualified_session_spoof_reproduced: true,
        qualified_session_rejected_true_unsafe_state: true,
        safe_state_with_hostile_path_accepted: true,
        actual_backend_not_spoofed: true,
        cleanup: closed!(admin)
      })
    after
      save_trace(name)
    end
  end
end
