defmodule MixerInspectorIndependent.RuntimeRepo do
  use Ecto.Repo, otp_app: :mixer_catalog_inspector, adapter: Ecto.Adapters.Postgres
end

defmodule MixerInspectorIndependent.ObserverRepo do
  use Ecto.Repo, otp_app: :mixer_catalog_inspector, adapter: Ecto.Adapters.Postgres
end

defmodule MixerInspectorIndependent.ReviewTest do
  use ExUnit.Case, async: false
  alias MixerInspectorIndependent.{RuntimeRepo, ObserverRepo}
  alias MixerHosted.CatalogInspector
  alias MixerHosted.CatalogInspector.Raw

  def record(_event, _measurements, metadata, _) do
    if Keyword.get(metadata.options, :mixer_catalog_inspector, false) do
      result =
        case metadata.result do
          {:ok, %Postgrex.Result{rows: rows, connection_id: backend}} -> %{rows: rows, backend: backend}
          {:error, %Postgrex.Error{postgres: fields}} -> %{sqlstate: fields[:pg_code]}
          {:error, error} -> %{error_class: inspect(error.__struct__)}
        end

      item = %{query: metadata.query, params: metadata.params, result: result}
      Process.put(:review_trace, [item | Process.get(:review_trace, [])])
      if hook = Process.get(:review_hook), do: hook.(metadata)
    end
  end

  setup_all do
    socket = System.fetch_env!("MIXER_REVIEW_SOCKET")
    {:ok, _} = Application.ensure_all_started(:ecto_sql)
    {:ok, _} = Application.ensure_all_started(:postgrex)
    {:ok, admin} = Postgrex.start_link(socket_dir: socket, database: "authority_contract", username: System.fetch_env!("USER"))
    {:ok, runtime} = RuntimeRepo.start_link(socket_dir: socket, database: "authority_contract", username: "mixer_hosted_runtime", pool_size: 1, prepare: :unnamed, telemetry_prefix: [:independent, :runtime])
    {:ok, observer} = ObserverRepo.start_link(socket_dir: socket, database: "authority_contract", username: "catalog_inspector_observer", pool_size: 1, prepare: :unnamed, telemetry_prefix: [:independent, :observer])
    q(RuntimeRepo, "SELECT 1")
    q(ObserverRepo, "SELECT 1")
    :ok = :telemetry.attach_many("mixer-inspector-independent", [[:independent, :runtime, :query], [:independent, :observer, :query]], &__MODULE__.record/4, nil)

    on_exit(fn ->
      :telemetry.detach("mixer-inspector-independent")
      for pid <- [runtime, observer, admin], Process.alive?(pid), do: GenServer.stop(pid)
    end)

    %{admin: admin}
  end

  setup do
    Process.put(:review_trace, [])
    Process.delete(:review_hook)
    :ok
  end

  defp q(repo, sql), do: Ecto.Adapters.SQL.query!(repo, sql, [], timeout: 2000, log: false)
  defp admin(pid, sql), do: Postgrex.query!(pid, sql, [], timeout: 10_000)
  defp verify, do: CatalogInspector.verify(ObserverRepo, RuntimeRepo)
  defp success, do: {:ok, %{manifest_sha256: "a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395", snapshot_scope: :point_in_time}}
  defp trace, do: Process.get(:review_trace, []) |> Enum.reverse()
  defp path(name), do: Path.join(System.fetch_env!("MIXER_REVIEW_OUT"), name)
  defp save(name, value), do: File.write!(path(name <> ".json"), Jason.encode!(value, pretty: true))
  defp log_trace(name), do: File.write!(path(name <> "-trace.json.gz"), :zlib.gzip(Jason.encode!(trace())))
  defp baseline, do: System.fetch_env!("MIXER_REVIEW_INPUTS") |> Path.join("baseline.json.gz") |> File.read!() |> :zlib.gunzip() |> Raw.decode!()
  defp canonical_expected, do: File.read!("priv/observer-profile.json") |> Jason.decode!()

  defp settled(admin, pid, start, samples \\ []) do
    now = System.monotonic_time(:millisecond)
    rows = admin(admin, "SELECT state, xact_start IS NULL FROM pg_catalog.pg_stat_activity WHERE pid=#{pid}").rows
    samples = [%{elapsed_ms: now - start, rows: rows} | samples]

    if rows in [[], [["idle", true]]] do
      Enum.reverse(samples)
    else
      assert now - start < 1000
      Process.sleep(10)
      settled(admin, pid, start, samples)
    end
  end

  defp clean(admin, repo) do
    [[pid, iso, ro, search, lock, statement, idle]] = q(repo, "SELECT pg_catalog.pg_backend_pid(), pg_catalog.current_setting('transaction_isolation'), pg_catalog.current_setting('transaction_read_only'), pg_catalog.current_setting('search_path'), pg_catalog.current_setting('lock_timeout'), pg_catalog.current_setting('statement_timeout'), pg_catalog.current_setting('idle_in_transaction_session_timeout')").rows
    assert [iso, ro, search, lock, statement, idle] == ["read committed", "off", "\"$user\", public", "0", "0", "0"]
    assert admin(admin, "SELECT state, xact_start IS NULL FROM pg_catalog.pg_stat_activity WHERE pid=#{pid}").rows == [["idle", true]]
    %{backend: pid, transaction_closed: true, local_settings_restored: true}
  end

  test "baseline observes both fixed sessions and one bounded observer transaction", %{admin: admin} do
    try do
      original_runtime = q(RuntimeRepo, "SELECT pg_catalog.pg_backend_pid()").rows
      original_observer = q(ObserverRepo, "SELECT pg_catalog.pg_backend_pid()").rows
      assert verify() == success()
      captured = fn marker -> trace() |> Enum.find(&String.contains?(&1.query, marker)) |> get_in([:result, :rows]) |> hd() |> hd() |> Raw.decode!() end
      raw = %{"legacy" => captured.("'server_version'"), "enforcement" => captured.("'relations'"), "fresh_session" => captured.("'session_user',session_user")}
      assert Raw.normalize!(raw) === canonical_expected()
      File.write!(path("independent-baseline.json.gz"), :zlib.gzip(Jason.encode!(raw)))
      captures = Enum.filter(trace(), &String.starts_with?(&1.query, "WITH mixer_catalog_capture"))
      assert length(captures) == 4
      runtime_captures = Enum.filter(captures, &String.contains?(&1.query, "'session_user',session_user"))
      assert length(runtime_captures) == 2
      assert Enum.map(runtime_captures, & &1.result.backend) == List.duplicate(hd(hd(original_runtime)), 2)
      assert Enum.map(runtime_captures, & &1.result.rows) |> Enum.uniq() |> length() == 1
      observer_captures = captures -- runtime_captures
      assert Enum.map(observer_captures, & &1.result.backend) == List.duplicate(hd(hd(original_observer)), 2)
      states = Enum.filter(trace(), &String.starts_with?(&1.query, "SELECT pg_backend_pid(), session_user::text"))
      assert length(states) == 2
      assert Enum.all?(states, &(&1.result.rows == [[hd(hd(original_observer)), "catalog_inspector_observer", "catalog_inspector_observer", "none", "repeatable read", "on", "on", "origin"]]))
      counts = Enum.filter(trace(), &String.starts_with?(&1.query, "SELECT (SELECT count(*)"))
      assert [%{result: %{rows: [limits]}}] = counts
      assert length(limits) == 12 and Enum.all?(limits, &(&1 === true))
      assert String.contains?(hd(counts).query, "pg_catalog.pg_attribute LIMIT 262145")
      settings = for repo <- [RuntimeRepo, ObserverRepo], do: hd(hd(q(repo, "SELECT count(*) FROM pg_catalog.pg_settings").rows))
      assert settings == [358, 379]
      assert q(RuntimeRepo, "SELECT pg_catalog.pg_backend_pid()").rows == original_runtime
      assert q(ObserverRepo, "SELECT pg_catalog.pg_backend_pid()").rows == original_observer
      save("baseline", %{passed: true, visible_settings: settings, runtime_before_after: original_runtime, observer_before_after: original_observer, observer_transaction_states: Enum.map(states, & &1.result.rows), captures: length(captures), preflight_columns: length(limits), runtime_cleanup: clean(admin, RuntimeRepo), observer_cleanup: clean(admin, ObserverRepo)})
    after
      log_trace("baseline")
    end
  end

  test "observer transitive protected authority and standalone column privilege reject", %{admin: admin} do
    variants = [
      {"transitive protected owner", "GRANT mixer_hosted_schema_owner TO pg_read_all_settings WITH ADMIN FALSE, INHERIT TRUE, SET FALSE", "REVOKE mixer_hosted_schema_owner FROM pg_read_all_settings"},
      {"protected column SELECT", "GRANT SELECT (principal_id) ON mixer_authz.principals TO catalog_inspector_observer", "REVOKE SELECT (principal_id) ON mixer_authz.principals FROM catalog_inspector_observer"},
      {"unrelated schema CREATE", "GRANT CREATE ON SCHEMA inspector_padding TO catalog_inspector_observer", "REVOKE CREATE ON SCHEMA inspector_padding FROM catalog_inspector_observer"}
    ]

    try do
      outcomes = for {{label, change, restore}, index} <- Enum.with_index(variants) do
        admin(admin, change)
        result = try do
          assert verify() == {:error, :catalog_unavailable}
          assert not Enum.any?(trace(), &String.contains?(&1.query, "'server_version'"))
          clean(admin, ObserverRepo)
          log_trace("observer-capability-#{index}")
          :catalog_unavailable
        after
          admin(admin, restore)
        end
        Process.put(:review_trace, [])
        assert verify() == success()
        Process.put(:review_trace, [])
        %{label: label, result: result, restored_baseline: true}
      end
      save("observer-capabilities", %{passed: true, cases: outcomes})
    after
      log_trace("observer-capabilities")
    end
  end

  test "both held contexts reject nesting aliases catalog occupancy and catalog dynamic changes", %{admin: admin} do
    try do
      for repo <- [RuntimeRepo, ObserverRepo] do
        assert repo.checkout(fn -> verify() end) == {:error, :catalog_unavailable}
        assert repo.transaction(fn -> verify() end) == {:ok, {:error, :catalog_unavailable}}
      end
      assert trace() == []
      prior = ObserverRepo.get_dynamic_repo()
      try do
        ObserverRepo.put_dynamic_repo(RuntimeRepo)
        assert verify() == {:error, :catalog_unavailable}
      after
        ObserverRepo.put_dynamic_repo(prior)
      end
      owner = self()
      task = Task.async(fn -> ObserverRepo.checkout(fn -> send(owner, :observer_busy); receive do :release -> :ok end end, timeout: 3000) end)
      assert_receive :observer_busy, 1000
      start = System.monotonic_time(:millisecond)
      elapsed = try do
        assert verify() == {:error, :catalog_unavailable}
        elapsed = System.monotonic_time(:millisecond) - start
        assert elapsed < 1000
        assert not Enum.any?(trace(), &String.contains?(&1.query, "'server_version'"))
        elapsed
      after
        send(task.pid, :release)
        Task.await(task)
      end
      Process.put(:review_hook, fn metadata ->
        if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
          Process.delete(:review_hook)
          ObserverRepo.put_dynamic_repo(RuntimeRepo)
        end
      end)
      try do
        assert verify() == {:error, :catalog_unavailable}
      after
        Process.delete(:review_hook)
        ObserverRepo.put_dynamic_repo(prior)
      end
      assert verify() == success()
      save("contexts", %{passed: true, nested_context_rejections: 4, dynamic_alias_and_midflight_rejections: 2, occupied_catalog_elapsed_ms: elapsed, observer_cleanup: clean(admin, ObserverRepo), runtime_cleanup: clean(admin, RuntimeRepo)})
    after
      log_trace("contexts")
    end
  end

  test "raw lossy fields strict primitives Unicode ordering and exact parser limits remain closed" do
    base = baseline()
    internal = base["enforcement"]["triggers"] |> Enum.filter(& &1["internal"])
    [first, second | _] = internal |> Enum.group_by(& &1["relation_oid"]) |> Map.values() |> Enum.find(&(length(&1) >= 2))
    replace = fn row -> update_in(base, ["enforcement", "triggers"], &Enum.map(&1, fn t -> if t["oid"] == second["oid"], do: row, else: t end)) end
    duplicate = replace.(Map.put(second, "name", first["name"]))
    assert catch_throw(Raw.normalize!(duplicate)) == :malformed_catalog
    assert catch_throw(Raw.normalize!(replace.(Map.put(second, "definition", false)))) == :malformed_catalog
    renamed = replace.(Map.put(second, "name", "independently_renamed_internal"))
    assert Raw.normalize!(renamed) === Raw.normalize!(base)
    for bad <- [true, false, 0, -1, 4_294_967_296, 1.0] do
      raw = put_in(base, ["enforcement", "relations", Access.at(0), "oid"], bad)
      assert catch_throw(Raw.validate!(raw)) == :malformed_catalog
    end
    star = update_in(base, ["enforcement", "startup_defaults"], &(&1 ++ [%{"database_oid" => 1, "database" => "*", "role_oid" => 1, "role" => "*", "config" => ["application_name="]}]))
    assert Raw.validate!(star) == :ok
    assert Raw.normalize!(star) !== Raw.normalize!(base)
    assert Raw.validate!(put_in(star, ["enforcement", "startup_defaults", Access.at(-1), "database"], "ordinary")) == :ok
    bad_star = star |> put_in(["enforcement", "startup_defaults", Access.at(-1), "database_oid"], 0) |> put_in(["enforcement", "startup_defaults", Access.at(-1), "database"], "ordinary")
    assert catch_throw(Raw.validate!(bad_star)) == :malformed_catalog
    save("raw-domains", %{passed: true, duplicate_internal_raw_name_rejected_before_loss: true, internal_definition_type_rejected_before_loss: true, legal_internal_name_portable: true, invalid_oid_primitive_cases: 6, positive_oid_literal_star_valid: true, positive_oid_ordinary_text_valid: true, zero_oid_nonstar_rejected: true})
  end

  test "independent canonical vectors and decoder byte node depth key boundaries" do
    vectors = File.read!(System.fetch_env!("MIXER_REVIEW_VECTORS")) |> Jason.decode!()
    for item <- vectors, do: assert Raw.canonical(item["value"]) == item["canonical"]
    assert Raw.decode!(String.duplicate(" ", 4_194_303) <> "0") == 0
    assert catch_throw(Raw.decode!(String.duplicate(" ", 4_194_304) <> "0")) == :malformed_catalog
    assert Raw.decode!(String.duplicate("[", 32) <> "0" <> String.duplicate("]", 32)) != nil
    assert catch_throw(Raw.decode!(String.duplicate("[", 33) <> "0" <> String.duplicate("]", 33))) == :malformed_catalog
    exactly = List.duplicate(List.duplicate(0, 4096), 24) ++ [List.duplicate(0, 1670)]
    assert Raw.decode!(Jason.encode!(exactly)) == exactly
    over = List.update_at(exactly, 24, &([0 | &1]))
    assert catch_throw(Raw.decode!(Jason.encode!(over))) == :malformed_catalog
    for json <- ["{\"x\":1,\"\\u0078\":2}", "{\"x\":{\"\\u00e9\":1,\"é\":2}}", "{\"x\":\"\\udc00\"}", "{\"x\":1e400}", "{\"x\":1.0}"] do
      if json == "{\"x\":1.0}" do
        assert Raw.decode!(json) == %{"x" => 1.0}
        assert catch_throw(Raw.validate!(Raw.decode!(json))) == :malformed_catalog
      else
        assert catch_throw(Raw.decode!(json)) == :malformed_catalog
      end
    end
    save("raw-models", %{passed: true, canonical_vectors: length(vectors), max_decoded_nodes: 100_000, over_nodes_rejected: 100_001, byte_boundary: 4_194_304, depth_boundary: 32, escaped_duplicate_keys_rejected: true, raw_float_never_authorizes: true})
  end

  test "hostile path function and type shadows cannot spoof either real connection", %{admin: admin} do
    admin(admin, "CREATE SCHEMA independent_shadow")
    admin(admin, "GRANT USAGE ON SCHEMA independent_shadow TO mixer_hosted_runtime, catalog_inspector_observer")
    admin(admin, "CREATE DOMAIN independent_shadow.text AS pg_catalog.text CHECK (false)")
    admin(admin, "CREATE FUNCTION independent_shadow.current_setting(pg_catalog.text) RETURNS pg_catalog.text LANGUAGE sql AS $$ SELECT CASE $1 WHEN 'role' THEN 'none' WHEN 'session_replication_role' THEN 'origin' WHEN 'row_security' THEN 'on' WHEN 'transaction_read_only' THEN 'off' ELSE 'read committed' END $$")
    admin(admin, "CREATE FUNCTION independent_shadow.pg_backend_pid() RETURNS integer LANGUAGE sql AS $$ SELECT 42 $$")
    try do
      q(RuntimeRepo, "SET search_path=independent_shadow,pg_catalog")
      q(ObserverRepo, "SET search_path=independent_shadow,pg_catalog")
      q(RuntimeRepo, "SET row_security=off")
      assert q(RuntimeRepo, "SELECT current_setting('row_security'), pg_backend_pid()").rows == [["on", 42]]
      old = q(RuntimeRepo, File.read!("priv/session-original.sql")).rows |> hd() |> hd()
      assert old === canonical_expected()["fresh_session"]
      assert {:error, %Postgrex.Error{postgres: %{pg_code: "23514"}}} = Ecto.Adapters.SQL.query(RuntimeRepo, "SELECT 'domain_cast'::text", [], log: false)
      assert verify() == {:error, :catalog_mismatch}
      q(RuntimeRepo, "SET row_security=on")
      assert verify() == success()
      assert q(RuntimeRepo, "SELECT pg_catalog.pg_backend_pid()=42").rows == [[false]]
      save("hostile-path", %{passed: true, original_query_spoofed: true, unqualified_type_cast_sqlstate: "23514", real_unsafe_runtime_rejected: true, safe_hostile_runtime_and_observer_accepted: true})
    after
      q(RuntimeRepo, "RESET row_security")
      q(RuntimeRepo, "RESET search_path")
      q(ObserverRepo, "RESET search_path")
      admin(admin, "DROP SCHEMA independent_shadow CASCADE")
      log_trace("hostile-path")
    end
    assert verify() == success()
  end

  test "expired holder is quarantined while paused owned driver leaves original backend alive", %{admin: admin} do
    original = q(ObserverRepo, "SELECT pg_catalog.pg_backend_pid()").rows |> hd() |> hd()
    Process.put(:review_hook, fn metadata ->
      if String.starts_with?(metadata.query, "SELECT (SELECT count(*)") do
        Process.delete(:review_hook)
        holders = for {{Ecto.Adapters.SQL, _}, %DBConnection{pool_ref: ref}} <- Process.get(), do: elem(ref, 4)
        {holder, driver} = Enum.find_value(holders, fn holder ->
          [row] = :ets.lookup(holder, :conn)
          if elem(row, 3).connection_id == original, do: {holder, elem(row, 1)}
        end)
        Process.put(:review_holder, holder)
        Process.put(:review_driver, driver)
        :ok = :sys.suspend(driver)
        Process.sleep(5050)
      end
    end)
    start = System.monotonic_time(:millisecond)
    try do
      assert verify() == {:error, :catalog_unavailable}
      elapsed = System.monotonic_time(:millisecond) - start
      assert elapsed >= 5000 and elapsed < 8000
      holder = Process.get(:review_holder)
      assert :ets.info(holder) == :undefined
      state_at_return = admin(admin, "SELECT state, xact_start IS NULL FROM pg_catalog.pg_stat_activity WHERE pid=#{original}").rows
      assert state_at_return == [["idle in transaction", false]]
      attempt = Ecto.Adapters.SQL.query(ObserverRepo, "SELECT pg_catalog.pg_backend_pid()", [], queue: false, timeout: 100, log: false)
      assert {:error, %DBConnection.ConnectionError{}} = attempt
      :ok = :sys.resume(Process.get(:review_driver))
      Process.delete(:review_driver)
      samples = settled(admin, original, System.monotonic_time(:millisecond))
      Process.sleep(100)
      replacement = clean(admin, ObserverRepo)
      assert replacement.backend != original
      assert verify() == success()
      save("holder-quarantine", %{passed: true, elapsed_ms: elapsed, original_backend: original, original_state_at_unavailable: state_at_return, holder_deleted_before_unavailable_return: true, queue_false_cannot_reuse_paused_driver: true, original_pid_samples_after_resume: samples, replacement: replacement, replacement_received_new_full_verification: true, synchronous_backend_cleanup_on_return: false, cleanup_window_is_test_observation_only: true})
    after
      Process.delete(:review_hook)
      if driver = Process.delete(:review_driver), do: :sys.resume(driver)
      log_trace("holder-quarantine")
    end
  end
end
