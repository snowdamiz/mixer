# Selected runner only: requires transaction_test.exs for its ordinary fixture.
defmodule MixerHosted.Authorization.JitPolicySpec do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.TransactionFixture, as: F
  alias MixerHosted.Authorization.TransactionFixture.{Admin, Migration, Runtime}
  alias MixerHosted.CustomerWorkspace

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TRANSACTION_TEST_PORT")),
      database: "mixer_jit_policy",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "txn_fixture_admin", pool_size: 1]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "txn_fixture_admin",
           pool_size: 2,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE txn_authz_owner", []) end
         ]}
    )

    start_supervised!(
      {Runtime,
       settings ++
         [username: "txn_authz_runtime", pool_size: 1, telemetry_prefix: [:jit_policy_probe]]}
    )

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_006, MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery}
        ],
        do: assert(:ok = Ecto.Migrator.up(Migration, version, module, log: false))

    for table <- F.tables(),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{table} TO txn_authz_runtime")

    for table <- F.locks(),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO txn_authz_runtime"
          )

    F.sql("CREATE TABLE public.transaction_probe(id text NOT NULL)")
    F.sql("GRANT SELECT,INSERT ON public.transaction_probe TO txn_authz_runtime")
    :ok
  end

  setup do
    F.seed!()
    on_exit(fn -> assert F.clean?() end)
    :ok
  end

  test "identity preparation applies verified local JIT and retains all bounds under the restricted login" do
    checkout(fn ->
      for prior <- ["on", "off"] do
        F.runtime_sql("SET SESSION jit = #{prior}")
        before = settings()

        assert {:ok, :ready} =
                 Runtime.transaction(
                   fn ->
                     Session.prepare_identity!(Runtime, identity_key())

                     assert [[false, false, false, false, false, false, true]] =
                              F.runtime_sql("""
                              SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,
                                pg_has_role(current_user,'txn_authz_owner','MEMBER'),current_user=session_user
                              FROM pg_roles WHERE rolname=current_user
                              """).rows

                     assert ["off", "5s", "500ms", "5s", "read committed"] = settings()
                     :ready
                   end,
                   timeout: 5_000,
                   queue: false
                 )

        assert settings() == before
        record("identity-commit-#{prior}", %{before: before, after: settings()})
      end
    end)
  end

  test "artifact success restores both inherited JIT values and commits the protected effect" do
    checkout(fn ->
      for prior <- ["on", "off"] do
        F.runtime_sql("SET SESSION jit = #{prior}")
        before = settings()

        assert {:ok, :accepted} =
                 F.run(fn _ ->
                   assert hd(settings()) == "off"
                   F.probe!()
                   {:ok, :accepted}
                 end)

        assert settings() == before
        record("artifact-commit-#{prior}", %{before: before, after: settings()})
      end
    end)

    assert [[2]] = F.sql("SELECT count(*) FROM public.transaction_probe").rows
  end

  test "explicit callback rollback restores the inherited JIT policy and removes prior SQL" do
    checkout(fn ->
      for prior <- ["on", "off"] do
        F.runtime_sql("SET SESSION jit = #{prior}")
        before = settings()

        assert {:error, :conflict} =
                 F.run(fn _ ->
                   assert hd(settings()) == "off"
                   F.probe!()
                   {:error, :conflict}
                 end)

        assert F.empty_probe?()
        assert settings() == before
        record("artifact-rollback-#{prior}", %{before: before, after: settings()})
      end
    end)
  end

  test "SQL-error rollback restores JIT and keeps the connection reusable" do
    checkout(fn ->
      F.runtime_sql("SET SESSION jit = on")
      before = settings()

      assert {:error, :authorization_unavailable} =
               F.run(fn _ ->
                 F.probe!()
                 F.runtime_sql("SELECT 1/0")
                 {:ok, :unreachable}
               end)

      assert F.empty_probe?()
      assert settings() == before
      assert {:ok, :next} = F.run(fn _ -> {:ok, :next} end)
      assert settings() == before
      record("sql-error-rollback", %{before: before, after: settings()})
    end)
  end

  test "workspace success and missing identity rollback restore the same checked-out connection" do
    checkout(fn ->
      F.runtime_sql("SET SESSION jit = on")
      before = settings()

      assert {:ok, %{organizations: [%{id: "org"}], next_cursor: nil}} =
               CustomerWorkspace.organizations(
                 workspace_identity(),
                 %{limit: 50, cursor: nil},
                 Runtime
               )

      assert settings() == before

      assert {:error, :unauthenticated} =
               CustomerWorkspace.organizations(
                 workspace_identity(%{credential_ref: "missing"}),
                 %{limit: 50, cursor: nil},
                 Runtime
               )

      assert settings() == before
      record("workspace-commit-and-rollback", %{before: before, after: settings()})
    end)
  end

  test "effective JIT mismatch fails closed before identity or topology work for both owners" do
    owner = self()
    id = {__MODULE__, :mismatch, make_ref()}

    :ok =
      :telemetry.attach(
        id,
        [:jit_policy_probe, :query],
        fn _, _, metadata, _ ->
          if self() == owner and metadata.query == "SET LOCAL jit = off" do
            F.runtime_sql("SET LOCAL jit = on")
            send(owner, :changed_effective_jit)
          end

          if self() == owner and String.contains?(metadata.query, "current_user = session_user"),
            do: send(owner, :topology_reached)
        end,
        nil
      )

    try do
      checkout(fn ->
        F.runtime_sql("SET SESSION jit = on")
        before = settings()

        assert {:error, :authorization_unavailable} =
                 F.run(fn _ -> flunk("effect was admitted") end)

        assert_receive :changed_effective_jit
        refute_receive :topology_reached, 0
        assert settings() == before

        assert {:error, :authorization_unavailable} =
                 CustomerWorkspace.organizations(
                   workspace_identity(),
                   %{limit: 50, cursor: nil},
                   Runtime
                 )

        assert_receive :changed_effective_jit
        refute_receive :topology_reached, 0
        assert settings() == before
      end)
    after
      :telemetry.detach(id)
    end
  end

  test "unsafe runtime privileges still fail closed after local JIT preparation" do
    F.sql("ALTER ROLE txn_authz_runtime BYPASSRLS")

    try do
      assert {:error, :authorization_unavailable} =
               F.run(fn _ -> flunk("effect was admitted") end)

      assert {:error, :authorization_unavailable} =
               CustomerWorkspace.organizations(
                 workspace_identity(),
                 %{limit: 50, cursor: nil},
                 Runtime
               )
    after
      F.sql("ALTER ROLE txn_authz_runtime NOBYPASSRLS")
    end
  end

  test "preparation outside an owner transaction fails before changing session settings" do
    checkout(fn ->
      F.runtime_sql("SET SESSION jit = on")
      before = settings()

      assert_raise RuntimeError, "cannot call rollback outside of transaction", fn ->
        Session.prepare_identity!(Runtime, identity_key())
      end

      assert settings() == before
    end)
  end

  defp checkout(fun) do
    Runtime.checkout(fn ->
      try do
        fun.()
      after
        F.runtime_sql("RESET jit")
      end
    end)
  end

  defp identity_key, do: MixerHosted.Authorization.Policy.identity_key(F.identity())

  defp workspace_identity(changes \\ %{}),
    do: F.identity(Map.merge(%{scopes: ["mixer.workspace.read"]}, changes))

  defp settings do
    [row] =
      F.runtime_sql("""
      SELECT current_setting('jit'),current_setting('statement_timeout'),current_setting('lock_timeout'),
        current_setting('idle_in_transaction_session_timeout'),current_setting('transaction_isolation')
      """).rows

    row
  end

  defp record(name, data) do
    File.write!(
      System.fetch_env!("MIXER_JIT_POLICY_SETTINGS_RESULT"),
      Jason.encode!(Map.put(data, :case, name)) <> "\n",
      [:append]
    )
  end
end
