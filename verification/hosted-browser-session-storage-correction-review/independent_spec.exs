Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_fixture.exs")

defmodule MixerBrowserStorageCorrectionReview do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.StorageFixture, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  setup_all do
    for app <- [:ecto_sql, :postgrex, :jason], do: {:ok, _} = Application.ensure_all_started(app)
    Logger.configure(level: :warning)

    settings = [
      hostname: "127.0.0.1",
      port: F.port(),
      database: "browser_storage",
      pool_size: 4,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "browser_admin"]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "browser_admin",
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE browser_schema_owner", []) end
         ]}
    )

    F.install!()

    F.q!(
      Admin,
      "INSERT INTO mixer_authz_profiles VALUES('humans',1,'https://issuer.fixture','console','human',true,1)"
    )

    F.q!(Admin, "INSERT INTO mixer_authz_principals VALUES('person-1','human',true,0,1)")

    F.q!(
      Admin,
      "INSERT INTO mixer_authz_bindings VALUES('humans',1,'subject-1','human','person-1',true,1)"
    )

    F.provision!()
    :ok
  end

  setup do
    conn = connection()
    %{conn: conn}
  end

  test "NULL and absent required scopes deny without changing any durable table", %{conn: c} do
    for scopes <- [
          nil,
          [],
          [nil],
          [nil, nil],
          ["elsewhere", nil],
          ["mixer.workspace.read ", nil],
          ["MIXER.workspace.read"],
          List.duplicate("mixer.workspace.read", 65)
        ] do
      {b, a, claim} = claimed(c)
      identity = %{F.identity() | scopes: scopes}
      before = durable_state()
      assert {{:error, :raise_exception}, _, _, _, _} = F.activate(c, b, a, claim, identity)
      assert durable_state() == before
    end
  end

  test "required scope remains sufficient with NULL neighbors and at the 64-element bound", %{
    conn: c
  } do
    for scopes <- [
          [nil, "mixer.workspace.read"],
          ["mixer.workspace.read", nil],
          ["mixer.workspace.read" | List.duplicate(nil, 63)]
        ] do
      {b, a, claim} = claimed(c)

      assert {{:ok, result}, active, family, identity, _} =
               F.activate(c, b, a, claim, %{F.identity() | scopes: scopes})

      assert result["browser"]["status"] == "active"

      assert [[true, true]] ==
               F.q!(
                 Admin,
                 "SELECT f.active,c.active FROM mixer_authz_families f JOIN mixer_authz_credentials c ON c.family_id=f.id WHERE f.id=$1 AND c.reference=$2",
                 [family, identity.jti]
               ).rows

      assert {:ok, _} = F.call(c, :load, [active.cookie, active.config])
    end
  end

  test "bootstrap rechecks expiry after a different-ID unique cookie wait", %{conn: c} do
    locker = connection()
    Postgrex.query!(locker, "BEGIN", [])
    other = F.bootstrap(locker)
    before = durable_state()
    deadline = F.now() + 2
    align_before(deadline)

    args = [
      F.random(16),
      other.cookie,
      F.token(),
      F.random(),
      F.random(),
      "humans",
      1,
      deadline,
      {:cipher, F.cipher()},
      F.request()
    ]

    result = blocked_call(locker, deadline, :bootstrap, args, true)
    assert result == {:error, :raise_exception}
    assert durable_state() == before
    assert {:ok, nil} = F.call(c, :load, [other.cookie, other.config])
  end

  test "late begin restores an existing claimed attempt and every vault/audit byte", %{conn: c} do
    {b, _existing, _claim} = claimed(c)
    locker = connection()
    other = F.bootstrap(locker)
    Postgrex.query!(locker, "BEGIN", [])
    {_other, collision} = F.begin_login(locker, other)
    before = durable_state()
    deadline = F.now() + 2
    align_before(deadline)

    args = [
      b.cookie,
      b.csrf,
      b.config,
      b.revision,
      {:attempt, %{collision | expires: deadline}},
      {:cipher, F.cipher()},
      F.request()
    ]

    assert {:error, :raise_exception} = blocked_call(locker, deadline, :begin, args, true)
    assert durable_state() == before
  end

  test "expired replacement cookie wait rolls back revocation of the existing family", %{conn: c} do
    {b, a, claim} = claimed(c)
    assert {{:ok, _}, active, old_family, _, _} = F.activate(c, b, a, claim)
    {b, a} = F.begin_login(c, active)
    deadline = F.now() + 2
    {claim, _} = F.claim(c, b, a, deadline)
    locker = connection()
    Postgrex.query!(locker, "BEGIN", [])
    other = F.bootstrap(locker)
    identity = F.identity()
    family = "browser_" <> F.token()
    before = durable_state()
    align_before(deadline)
    args = activation_args(b, a, claim, identity, other.cookie, family)
    assert {:error, :raise_exception} = blocked_call(locker, deadline, :activate, args, true)
    assert durable_state() == before

    assert [[true, true]] ==
             F.q!(
               Admin,
               "SELECT f.active,c.active FROM mixer_authz_families f JOIN mixer_authz_credentials c ON c.family_id=f.id WHERE f.id=$1",
               [old_family]
             ).rows

    assert [[0]] ==
             F.q!(Admin, "SELECT count(*) FROM mixer_authz_families WHERE id=$1", [family]).rows

    assert [[0]] ==
             F.q!(Admin, "SELECT count(*) FROM mixer_authz_credentials WHERE reference=$1", [
               identity.jti
             ]).rows
  end

  test "identical unique-cookie wait succeeds when released before exclusive expiry", %{conn: c} do
    {b, a, claim} = claimed(c)
    locker = connection()
    Postgrex.query!(locker, "BEGIN", [])
    other = F.bootstrap(locker)
    identity = F.identity()
    family = "browser_" <> F.token()
    args = activation_args(b, a, claim, identity, other.cookie, family)
    assert {:ok, result} = blocked_call(locker, F.now() + 10, :activate, args, false)
    assert result["browser"]["status"] == "active"

    assert [["completed"]] ==
             F.q!(Admin, "SELECT status FROM mixer_browser_oidc_attempts WHERE state_digest=$1", [
               a.state
             ]).rows

    assert [[true]] ==
             F.q!(Admin, "SELECT active FROM mixer_authz_families WHERE id=$1", [family]).rows
  end

  defp claimed(c) do
    b = F.bootstrap(c)
    {b, a} = F.begin_login(c, b)
    {claim, _} = F.claim(c, b, a)
    {b, a, claim}
  end

  defp activation_args(b, a, claim, identity, cookie, family) do
    [
      b.cookie,
      a.state,
      b.config,
      claim,
      b.revision,
      {:verified, identity},
      cookie,
      F.random(),
      F.token(),
      family,
      F.now() + 500,
      {:cipher, F.cipher()},
      F.request()
    ]
  end

  defp connection do
    conn = F.connection!()
    on_exit(fn -> if Process.alive?(conn), do: GenServer.stop(conn) end)
    conn
  end

  defp durable_state do
    for table <-
          ~w(mixer_browser_sessions mixer_browser_session_vault mixer_browser_oidc_attempts mixer_browser_session_events mixer_authz_profiles mixer_authz_principals mixer_authz_bindings mixer_authz_families mixer_authz_credentials),
        into: %{} do
      {table,
       F.q!(
         Admin,
         "SELECT COALESCE(jsonb_agg(row_value ORDER BY row_value::text),'[]'::jsonb) FROM (SELECT to_jsonb(t) AS row_value FROM #{table} t) q"
       ).rows}
    end
  end

  defp align_before(deadline) do
    Process.sleep(max(deadline * 1_000 - System.system_time(:millisecond) - 200, 0))
  end

  defp blocked_call(locker, deadline, operation, args, expire?) do
    parent = self()
    [[blocker]] = Postgrex.query!(locker, "SELECT pg_backend_pid()", []).rows

    task =
      Task.async(fn ->
        conn = F.connection!()
        [[pid]] = Postgrex.query!(conn, "SELECT pg_backend_pid()", []).rows
        send(parent, {:backend, pid})

        try do
          F.call(conn, operation, args)
        after
          GenServer.stop(conn)
        end
      end)

    assert_receive {:backend, pid}, 1_000
    wait_for_lock(pid, blocker, System.monotonic_time(:millisecond) + 120)
    # The observed backend is inside the unique-index wait, past initial checks.
    assert F.now() < deadline

    if expire?,
      do: Process.sleep(max(deadline * 1_000 + 20 - System.system_time(:millisecond), 0))

    assert not expire? or F.now() >= deadline
    Postgrex.query!(locker, "ROLLBACK", [])
    GenServer.stop(locker)
    result = Task.await(task, 2_000)

    IO.puts(
      "unique_wait_control:" <>
        Jason.encode!(%{
          operation: operation,
          expired: expire?,
          backend_pid: pid,
          blocker_pid: blocker,
          exclusive_deadline: deadline,
          outcome: elem(result, 0)
        })
    )

    result
  end

  defp wait_for_lock(pid, blocker, timeout) do
    case F.q!(
           Admin,
           "SELECT wait_event_type,wait_event,pg_blocking_pids(pid) FROM pg_stat_activity WHERE pid=$1",
           [pid]
         ).rows do
      [["Lock", "transactionid", blockers]] ->
        assert blocker in blockers

      _ ->
        assert System.monotonic_time(:millisecond) < timeout
        Process.sleep(5)
        wait_for_lock(pid, blocker, timeout)
    end
  end
end
