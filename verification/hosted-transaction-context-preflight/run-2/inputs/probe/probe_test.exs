ExUnit.start(autorun: false, seed: 0, max_cases: 1, timeout: 8_000, trace: true)

alias MixerTransactionContextPreflight.{Repo, OtherRepo}
{:ok, _} = Agent.start_link(fn -> %{} end, name: PreflightObservations)
config = [socket_dir: System.fetch_env!("MXTC_SOCKET"), username: "preflight_owner",
          database: "context_preflight", pool_size: 1, timeout: 5_000,
          connect_timeout: 2_000, queue_target: 1_000, log: false]
{:ok, repo} = Repo.start_link(config)
{:ok, other_repo} = OtherRepo.start_link(config)
Repo.query!("CREATE TABLE effects (case_name text NOT NULL, value integer NOT NULL)")
Repo.query!("CREATE TABLE gate (id integer PRIMARY KEY, revision integer NOT NULL)")
Repo.query!("CREATE TABLE membership (id integer PRIMARY KEY, active boolean NOT NULL)")
Repo.query!("INSERT INTO gate VALUES (1, 1)")
Repo.query!("INSERT INTO membership VALUES (1, true)")

defmodule MixerTransactionContextPreflight.ProbeTest do
  use ExUnit.Case, async: false
  alias MixerTransactionContextPreflight.{Context, Rejected, Repo, OtherRepo}

  setup do
    Repo.put_dynamic_repo(Repo)
    Repo.query!("TRUNCATE effects")
    Repo.query!("UPDATE membership SET active = true WHERE id = 1")
    :ok
  end

  defp rejected(reason, fun) do
    error = assert_raise Rejected, fun
    assert error.reason == reason
    error
  end

  defp observation(name, value), do: Agent.update(PreflightObservations, &Map.put(&1, name, value))
  defp scalar(repo, sql, params \\ []), do: repo.query!(sql, params, log: false).rows |> hd() |> hd()
  defp no_effects, do: assert(scalar(OtherRepo, "SELECT count(*) FROM effects") == 0)
  defp now, do: System.monotonic_time(:millisecond)
  defp cleaned do
    settings = Repo.query!("SELECT current_setting($1, true), current_setting('statement_timeout'), current_setting('lock_timeout')", [Context.probe_nonce_guc()]).rows
    assert settings in [[[nil, "0", "0"]], [["", "0", "0"]]]
    assert Process.get(Context.probe_marker_key()) == nil
    settings
  end

  defp captured_failure(fun) do
    try do
      {:returned, fun.()}
    rescue
      error ->
        code = case error do
          %Postgrex.Error{postgres: %{code: code}} -> code
          _ -> nil
        end
        {:raised, inspect(error.__struct__), Exception.message(error), code}
    end
  end

  test "01 same transaction has stable actual SQL identity and decreasing statement budget" do
    assert {:ok, data} = Context.enter(fn context ->
      assert is_reference(context.invocation)
      assert context.repo == Repo and context.dynamic_repo == Repo
      first = Context.query!(context, "SELECT pg_backend_pid(), pg_current_xact_id()::text, current_database(), current_user").rows
      first_budget = scalar(Repo, "SELECT setting::int FROM pg_settings WHERE name = 'statement_timeout'")
      Process.sleep(35)
      second = Context.query!(context, "SELECT pg_backend_pid(), pg_current_xact_id()::text, current_database(), current_user").rows
      second_budget = scalar(Repo, "SELECT setting::int FROM pg_settings WHERE name = 'statement_timeout'")
      assert first == second
      assert first == [[context.backend_pid, context.transaction_id, "context_preflight", "preflight_owner"]]
      assert second_budget < first_budget
      assert scalar(Repo, "SHOW transaction_isolation") == "read committed"
      assert scalar(Repo, "SHOW lock_timeout") == "250ms"
      Context.query!(context, "INSERT INTO effects VALUES ('stable', 1)")
      %{identity: first, first_statement_budget_ms: first_budget, second_statement_budget_ms: second_budget}
    end)
    assert scalar(OtherRepo, "SELECT count(*) FROM effects") == 1
    observation("stable_identity_and_decreasing_budget", data)
  end

  test "02 same backend in a later transaction has a distinct full xid" do
    assert {:ok, first} = Context.enter(& &1)
    assert {:ok, second} = Context.enter(& &1)
    assert first.backend_pid == second.backend_pid
    refute first.transaction_id == second.transaction_id
    refute first.invocation == second.invocation
    observation("same_backend_new_transaction", %{backend_pid: first.backend_pid, old_xid: first.transaction_id, new_xid: second.transaction_id})
  end

  test "03 a context captured after commit is denied and the local marker is closed" do
    assert {:ok, context} = Context.enter(& &1)
    rejected(:inactive_invocation, fn -> Context.query!(context, "INSERT INTO effects VALUES ('closed', 1)") end)
    assert Process.get(Context.probe_marker_key()) == nil
    no_effects()
  end

  test "04 captured rollback context is denied" do
    assert {:error, :intentional} = Context.enter(fn context ->
      Process.put(:captured_rollback_context, context)
      Context.query!(context, "INSERT INTO effects VALUES ('rollback', 1)")
      Repo.rollback(:intentional)
    end)
    context = Process.delete(:captured_rollback_context)
    rejected(:inactive_invocation, fn -> Context.query!(context, "SELECT 1") end)
    no_effects()
  end

  test "05 spoofing the old marker and nonce in a new same-backend transaction is denied by xid" do
    assert {:ok, old} = Context.enter(& &1)
    assert {:ok, actual} = Repo.transaction(fn ->
      Process.put(Context.probe_marker_key(), old.invocation)
      try do
        Repo.query!("SELECT set_config($1, $2, true)", [Context.probe_nonce_guc(), old.nonce])
        [[pid, xid]] = Repo.query!("SELECT pg_backend_pid(), pg_current_xact_id()::text").rows
        assert pid == old.backend_pid
        refute xid == old.transaction_id
        rejected(:transaction_changed, fn -> Context.query!(old, "INSERT INTO effects VALUES ('spoof', 1)") end)
        %{backend_pid: pid, old_xid: old.transaction_id, actual_xid: xid, marker_and_nonce_spoofed: true}
      after
        Process.delete(Context.probe_marker_key())
      end
    end)
    no_effects()
    observation("spoofed_marker_still_denied_by_xid", actual)
  end

  test "06 context copied to another BEAM process is denied before any checkout" do
    assert {:ok, :ok} = Context.enter(fn context ->
      task = Task.async(fn ->
        error = assert_raise Rejected, fn -> Context.query!(context, "SELECT 1") end
        error.reason
      end)
      assert Task.await(task, 1_000) == :foreign_process
      :ok
    end)
  end

  test "07 arbitrary Repo and dynamic Repo identities are rejected" do
    assert {:ok, :ok} = Context.enter(fn context ->
      rejected(:fixed_repo, fn -> Context.query!(%{context | repo: OtherRepo}, "SELECT 1") end)
      rejected(:dynamic_repo, fn -> Context.query!(%{context | dynamic_repo: OtherRepo}, "SELECT 1") end)
      original = Repo.put_dynamic_repo(OtherRepo)
      try do
        rejected(:dynamic_repo, fn -> Context.query!(context, "SELECT 1") end)
      after
        Repo.put_dynamic_repo(original)
      end
      :ok
    end)
    original = Repo.put_dynamic_repo(OtherRepo)
    try do
      rejected(:entry_dynamic_repo, fn -> Context.enter(fn _ -> :unreachable end) end)
    after
      Repo.put_dynamic_repo(original)
    end
  end

  test "08 nested seam entry and entry within an existing Repo transaction are rejected" do
    assert {:ok, :ok} = Context.enter(fn context ->
      rejected(:nested_entry, fn -> Context.enter(fn _ -> :unreachable end) end)
      Context.query!(context, "SELECT 1")
      :ok
    end)
    assert {:ok, :ok} = Repo.transaction(fn ->
      rejected(:nested_entry, fn -> Context.enter(fn _ -> :unreachable end) end)
      :ok
    end)
  end

  test "09 absent malformed inactive and operation-mismatched contexts fail closed" do
    rejected(:invalid_context, fn -> Context.query!(nil, "SELECT 1") end)
    rejected(:invalid_context, fn -> Context.query!(%{owner: self()}, "SELECT 1") end)
    assert {:ok, :ok} = Context.enter(fn context ->
      rejected(:inactive_invocation, fn -> Context.query!(%{context | invocation: make_ref()}, "SELECT 1") end)
      rejected(:operation_target, fn -> Context.query!(context, "SELECT 1", [], :unsupported) end)
      rejected(:operation_target, fn -> Context.query!(context, "SELECT 1", [], :synthetic_write, {"other", "project"}) end)
      :ok
    end)
  end

  test "10 actual backend xid database and role are checked on every synthetic operation" do
    assert {:ok, :ok} = Context.enter(fn context ->
      rejected(:backend_changed, fn -> Context.query!(%{context | backend_pid: context.backend_pid + 1}, "SELECT 1") end)
      rejected(:transaction_changed, fn -> Context.query!(%{context | transaction_id: "0"}, "SELECT 1") end)
      rejected(:database_role_changed, fn -> Context.query!(%{context | database: "other"}, "SELECT 1") end)
      rejected(:database_role_changed, fn -> Context.query!(%{context | db_role: "other"}, "SELECT 1") end)
      :ok
    end)
  end

  test "11 a changed transaction-local nonce is rejected" do
    error = assert_raise Rejected, fn ->
      Context.enter(fn context ->
        Repo.query!("SELECT set_config($1, 'tampered', true)", [Context.probe_nonce_guc()])
        Context.query!(context, "INSERT INTO effects VALUES ('nonce', 1)")
      end)
    end
    assert error.reason == :nonce_changed
    no_effects()
    cleaned()
  end

  test "12 transaction-local nonce and budgets clean up after commit" do
    assert {:ok, :ok} = Context.enter(fn context ->
      assert scalar(Repo, "SELECT current_setting($1, true)", [Context.probe_nonce_guc()]) == context.nonce
      :ok
    end)
    observation("cleanup_after_commit", %{settings: cleaned()})
  end

  test "13 transaction-local nonce and budgets clean up after rollback" do
    assert {:error, :intentional} = Context.enter(fn _ -> Repo.rollback(:intentional) end)
    observation("cleanup_after_rollback", %{settings: cleaned()})
  end

  test "14 exception rolls back effects and closes SQL and process context" do
    assert_raise RuntimeError, "synthetic exception", fn ->
      Context.enter(fn context ->
        Context.query!(context, "INSERT INTO effects VALUES ('exception', 1)")
        raise "synthetic exception"
      end)
    end
    no_effects()
    observation("cleanup_after_exception", %{settings: cleaned()})
  end

  test "15 callback wait across application deadline rejects subsequent effect and rolls back earlier effect" do
    started = now()
    error = assert_raise Rejected, fn ->
      Context.enter(fn context ->
        Context.query!(context, "INSERT INTO effects VALUES ('app-before-deadline', 1)")
        Process.sleep(330)
        Context.query!(context, "INSERT INTO effects VALUES ('app-after-deadline', 2)")
      end, 180)
    end
    assert error.reason == :deadline_exceeded
    no_effects()
    assert Process.get(Context.probe_marker_key()) == nil
    observation("application_deadline_spans_callback_wait", %{elapsed_ms: now() - started, error: Atom.to_string(error.reason), partial_effect_rows: 0})
  end

  test "16 DBConnection absolute deadline disconnects during callback wait and denies raw subsequent write" do
    deadline = now() + 180
    outcome = captured_failure(fn ->
      Repo.transaction(fn ->
        Process.put(:deadline_backend, scalar(Repo, "SELECT pg_backend_pid()"))
        Repo.query!("INSERT INTO effects VALUES ('db-before-deadline', 1)")
        Process.sleep(330)
        Repo.query!("INSERT INTO effects VALUES ('db-after-deadline', 2)", [], timeout: 5_000)
      end, deadline: deadline, timeout: 1_000)
    end)
    old_pid = Process.delete(:deadline_backend)
    assert {:raised, "DBConnection.ConnectionError", message, nil} = outcome
    assert message =~ "connection is closed"
    assert scalar(OtherRepo, "SELECT count(*) FROM pg_stat_activity WHERE pid = $1", [old_pid]) == 0
    new_pid = scalar(Repo, "SELECT pg_backend_pid()")
    refute new_pid == old_pid
    no_effects()
    observation("raw_dbconnection_deadline_write", %{old_backend_pid: old_pid, new_backend_pid: new_pid, outcome: inspect(outcome), partial_effect_rows: 0})
  end

  test "17 DBConnection deadline also prevents commit when callback returns late without another query" do
    deadline = now() + 180
    outcome = captured_failure(fn ->
      Repo.transaction(fn ->
        Repo.query!("INSERT INTO effects VALUES ('late-return', 1)")
        Process.sleep(330)
        :late_success
      end, deadline: deadline, timeout: 1_000)
    end)
    refute match?({:returned, {:ok, _}}, outcome)
    no_effects()
    observation("raw_dbconnection_deadline_commit", %{outcome: inspect(outcome), partial_effect_rows: 0})
  end

  test "18 remaining statement budget or connection deadline aborts slow SQL without partial commit" do
    outcome = captured_failure(fn ->
      Context.enter(fn context ->
        Context.query!(context, "INSERT INTO effects VALUES ('before-slow-sql', 1)")
        Context.query!(context, "SELECT pg_sleep(0.8)")
      end, 220)
    end)
    assert match?({:raised, _, _, _}, outcome)
    assert elem(outcome, 1) in ["Postgrex.Error", "DBConnection.ConnectionError", "MixerTransactionContextPreflight.Rejected"]
    no_effects()
    observation("slow_sql_deadline", %{outcome: inspect(outcome), partial_effect_rows: 0})
  end

  test "19 blocked row lock uses 250ms lock timeout and rolls back all effects" do
    parent = self()
    writer = Task.async(fn ->
      OtherRepo.transaction(fn ->
        OtherRepo.query!("UPDATE gate SET revision = revision + 1 WHERE id = 1")
        send(parent, :lock_held)
        receive do
          :release -> :ok
        after
          4_000 -> raise "fixture release not received"
        end
      end, timeout: 5_000)
    end)
    assert_receive :lock_held, 1_000
    started = now()
    try do
      error = assert_raise Postgrex.Error, fn ->
        Context.enter(fn context ->
          Context.query!(context, "INSERT INTO effects VALUES ('before-lock', 1)")
          Context.query!(context, "UPDATE gate SET revision = revision + 1 WHERE id = 1")
        end, 2_000)
      end
      assert error.postgres.code == :lock_not_available
      elapsed = now() - started
      assert elapsed >= 220 and elapsed < 1_200
      observation("lock_timeout", %{elapsed_ms: elapsed, sqlstate: error.postgres.pg_code, partial_effect_rows: 0})
    after
      send(writer.pid, :release)
      assert {:ok, :ok} = Task.await(writer, 2_000)
    end
    no_effects()
  end

  test "20 separate READ COMMITTED statement after lock sees current committed membership" do
    parent = self()
    writer = Task.async(fn ->
      OtherRepo.transaction(fn ->
        OtherRepo.query!("UPDATE gate SET revision = revision + 1 WHERE id = 1")
        OtherRepo.query!("UPDATE membership SET active = false WHERE id = 1")
        send(parent, :membership_uncommitted)
        receive do
          :release -> :ok
        after
          4_000 -> raise "fixture release not received"
        end
      end, timeout: 5_000)
    end)
    assert_receive :membership_uncommitted, 1_000
    try do
      assert {:ok, data} = Context.enter(fn context ->
        [[true]] = Context.query!(context, "SELECT active FROM membership WHERE id = 1").rows
        Process.send_after(writer.pid, :release, 100)
        started = now()
        Context.query!(context, "SELECT id FROM gate WHERE id = 1 FOR SHARE")
        waited = now() - started
        assert waited >= 70
        [[false]] = Context.query!(context, "SELECT active FROM membership WHERE id = 1").rows
        %{initial_active: true, after_lock_active: false, lock_wait_ms: waited, isolation: scalar(Repo, "SHOW transaction_isolation")}
      end)
      observation("after_lock_read_committed_membership", data)
    after
      send(writer.pid, :release)
      assert {:ok, :ok} = Task.await(writer, 2_000)
    end
  end

  test "21 direct SQL COMMIT and BEGIN cannot preserve the old transaction identity" do
    error = assert_raise Rejected, fn ->
      Context.enter(fn context ->
        Repo.query!("COMMIT")
        Repo.query!("BEGIN")
        Repo.query!("SELECT set_config($1, $2, true)", [Context.probe_nonce_guc(), context.nonce])
        [[actual_xid]] = Repo.query!("SELECT pg_current_xact_id()::text").rows
        assert Repo.in_transaction?()
        refute actual_xid == context.transaction_id
        observation("direct_commit_begin", %{ecto_in_transaction: true, old_xid: context.transaction_id, actual_xid: actual_xid, nonce_restored: true})
        Context.query!(context, "INSERT INTO effects VALUES ('direct-rebegin', 1)")
      end)
    end
    assert error.reason == :transaction_changed
    no_effects()
    cleaned()
  end

  test "22 context nonce is absent outside an unrelated raw transaction" do
    assert {:ok, _} = Context.enter(& &1)
    assert {:ok, settings} = Repo.transaction(fn ->
      value = scalar(Repo, "SELECT current_setting($1, true)", [Context.probe_nonce_guc()])
      assert value in [nil, ""]
      value
    end)
    observation("unrelated_raw_transaction_nonce", %{value: settings})
  end

  test "23 callback cannot extend the original connection deadline by changing its context copy" do
    outcome = captured_failure(fn ->
      Context.enter(fn context ->
        Context.query!(context, "INSERT INTO effects VALUES ('before-extension', 1)")
        extended_copy = %{context | deadline_ms: now() + 5_000}
        Process.sleep(330)
        Context.query!(extended_copy, "INSERT INTO effects VALUES ('after-extension', 2)")
      end, 180)
    end)
    assert {:raised, "DBConnection.ConnectionError", _, nil} = outcome
    no_effects()
    assert Process.get(Context.probe_marker_key()) == nil
    observation("callback_cannot_extend_connection_deadline", %{outcome: inspect(outcome), partial_effect_rows: 0})
  end

  test "24 absolute deadline includes pool checkout waiting and callback never starts after expiry" do
    parent = self()
    holder = Task.async(fn ->
      Repo.transaction(fn ->
        Repo.query!("SELECT 1")
        send(parent, :pool_held)
        receive do
          :release -> :ok
        after
          4_000 -> raise "fixture release not received"
        end
      end, timeout: 5_000)
    end)
    assert_receive :pool_held, 1_000
    started = now()
    try do
      outcome = captured_failure(fn ->
        Context.enter(fn _ ->
          Process.put(:callback_unexpectedly_started, true)
          :unreachable
        end, 180)
      end)
      assert {:raised, "DBConnection.ConnectionError", _, nil} = outcome
      assert Process.get(:callback_unexpectedly_started) == nil
      elapsed = now() - started
      assert elapsed >= 150 and elapsed < 1_200
      observation("deadline_includes_checkout_wait", %{elapsed_ms: elapsed, callback_started: false, outcome: inspect(outcome)})
    after
      send(holder.pid, :release)
      assert {:ok, :ok} = Task.await(holder, 2_000)
    end
    no_effects()
  end
end

summary = try do
  summary = ExUnit.run()
  observations = Agent.get(PreflightObservations, & &1)
  versions = for app <- [:ecto, :ecto_sql, :postgrex, :db_connection, :decimal, :telemetry, :jason], into: %{} do
    {app, to_string(Application.spec(app, :vsn))}
  end
  File.write!(System.fetch_env!("MXTC_RESULTS"), Jason.encode!(%{summary: summary, dependency_versions: versions, observations: observations}, pretty: true) <> "\n")
  summary
after
  Supervisor.stop(repo, :normal, 2_000)
  Supervisor.stop(other_repo, :normal, 2_000)
end
if summary.failures > 0, do: System.halt(1)
