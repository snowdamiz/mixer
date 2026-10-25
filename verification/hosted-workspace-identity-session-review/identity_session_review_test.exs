defmodule MixerHosted.Authorization.IdentitySessionIndependentReviewTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Authorization.{Policy, Postgres.Session}
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Authorization.TransactionFixture, as: F
  alias MixerHosted.Authorization.TransactionFixture.{Admin, Runtime}

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TRANSACTION_TEST_PORT")),
      database: "mixer_customer_transaction",
      ssl: false,
      log: false
    ]

    # The preceding, separately executed baseline has installed only migrations
    # 003/004 in this owned disposable database. No workspace producer is loaded.
    start_supervised!({Admin, settings ++ [username: "txn_fixture_admin", pool_size: 4]})
    start_supervised!({Runtime, settings ++ [username: "txn_authz_runtime", pool_size: 1]})
    :ok
  end

  setup do
    F.seed!()
    on_exit(fn -> assert F.clean?() end)
    :ok
  end

  defp prepared_task(parent) do
    Task.async(fn ->
      Runtime.transaction(fn ->
        linkage = Session.prepare_identity!(Runtime, Policy.identity_key(F.identity()))
        [[backend]] = F.runtime_sql("SELECT pg_backend_pid()").rows
        send(parent, {:prepared, self(), backend, linkage})

        receive do
          :release -> linkage
        after
          3_000 -> flunk("independent prepared reader release timeout")
        end
      end)
    end)
  end

  defp wait_for_lock!(backend) do
    assert Enum.reduce_while(1..100, false, fn _, _ ->
             if F.sql("SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=$1", [
                  backend
                ]).rows == [[true]] do
               {:halt, true}
             else
               Process.sleep(2)
               {:cont, false}
             end
           end),
           "backend must observably wait on a real PostgreSQL lock"
  end

  test "identity helper locks all four identity rows while tenant heads are concurrently locked" do
    parent = self()

    head_writer =
      Task.async(fn ->
        Admin.transaction(fn ->
          F.sql("SELECT 1 FROM public.mixer_authz_organization_heads FOR UPDATE")
          F.sql("SELECT 1 FROM public.mixer_authz_project_heads FOR UPDATE")
          send(parent, {:heads_locked, self()})

          receive do
            :release -> :ok
          after
            3_000 -> flunk("independent head writer release timeout")
          end
        end)
      end)

    assert_receive {:heads_locked, head_pid}, 1_000
    reader = prepared_task(parent)

    try do
      assert_receive {:prepared, reader_pid, backend, linkage}, 1_000
      assert linkage == %{principal_id: "person", family_id: "family"}

      actual =
        F.sql(
          """
          SELECT c.relname::text FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
          WHERE l.pid=$1 AND l.mode='RowShareLock' AND c.relkind='r' AND c.relname LIKE 'mixer_authz_%'
          ORDER BY c.relname COLLATE "C"
          """,
          [backend]
        ).rows
        |> List.flatten()

      assert actual ==
               ~w(mixer_authz_credentials mixer_authz_families mixer_authz_principals mixer_authz_profiles)

      # Relation lock observations are supplemented by actual NOWAIT conflicts
      # against each exact identity row, independently proving tuple locking.
      for table <- ~w(profiles principals families credentials) do
        error =
          assert_raise Postgrex.Error, fn ->
            Admin.transaction(fn ->
              F.sql("SELECT 1 FROM public.mixer_authz_#{table} FOR UPDATE NOWAIT")
            end)
          end

        assert error.postgres.code == :lock_not_available
      end

      send(reader_pid, :release)
      assert {:ok, ^linkage} = Task.await(reader, 1_000)
    after
      send(reader.pid, :release)
      send(head_pid, :release)
      Task.await(head_writer, 1_000)
    end
  end

  test "credential revocation waits for identity helper and the next artifact request denies" do
    parent = self()
    reader = prepared_task(parent)
    assert_receive {:prepared, reader_pid, _, _}, 1_000

    writer =
      Task.async(fn ->
        Admin.transaction(fn ->
          for table <- ~w(profiles principals families),
              do: F.sql("SELECT 1 FROM public.mixer_authz_#{table} FOR SHARE")

          [[backend]] = F.sql("SELECT pg_backend_pid()").rows
          send(parent, {:writer_backend, backend})
          F.sql("SELECT 1 FROM public.mixer_authz_credentials FOR UPDATE")
          F.sql("UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1")
        end)
      end)

    try do
      assert_receive {:writer_backend, backend}, 1_000
      wait_for_lock!(backend)
      assert Task.yield(writer, 0) == nil
      send(reader_pid, :release)
      assert {:ok, %{principal_id: "person", family_id: "family"}} = Task.await(reader, 1_000)
      assert {:ok, _} = Task.await(writer, 1_000)

      assert {:error, :unauthenticated} =
               F.run(fn _ -> flunk("revoked credential reached artifact callback") end)
    after
      send(reader.pid, :release)
    end
  end

  test "identity helper waits for earlier credential revocation but linkage itself never asserts active state" do
    parent = self()

    writer =
      Task.async(fn ->
        Admin.transaction(fn ->
          for table <- ~w(profiles principals families),
              do: F.sql("SELECT 1 FROM public.mixer_authz_#{table} FOR SHARE")

          F.sql("SELECT 1 FROM public.mixer_authz_credentials FOR UPDATE")
          F.sql("UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1")
          send(parent, {:revocation_locked, self()})

          receive do
            :release -> :ok
          after
            3_000 -> flunk("independent revocation release timeout")
          end
        end)
      end)

    assert_receive {:revocation_locked, writer_pid}, 1_000

    reader =
      Task.async(fn ->
        Runtime.transaction(fn ->
          [[backend]] = F.runtime_sql("SELECT pg_backend_pid()").rows
          send(parent, {:reader_backend, backend})
          linkage = Session.prepare_identity!(Runtime, Policy.identity_key(F.identity()))
          refute Context.active?()

          assert [[false]] ==
                   F.runtime_sql("SELECT active FROM public.mixer_authz_credentials").rows

          linkage
        end)
      end)

    try do
      assert_receive {:reader_backend, backend}, 1_000
      wait_for_lock!(backend)
      send(writer_pid, :release)
      assert {:ok, :ok} = Task.await(writer, 1_000)
      assert {:ok, %{principal_id: "person", family_id: "family"}} = Task.await(reader, 1_000)
      assert {:error, :unauthenticated} = F.run(fn _ -> flunk("revoked artifact callback") end)
    after
      send(writer.pid, :release)
    end
  end

  test "a reused connection inherited directory selection cannot widen an ordinary artifact context" do
    keys = ~w(organization_id project_id application_id environment_id directory_mode)

    assert {:ok, :exact_artifact} =
             Runtime.checkout(fn ->
               for key <- keys,
                   do:
                     F.runtime_sql("SELECT set_config($1,'stale-directory',false)", [
                       "mixer.authz." <> key
                     ])

               try do
                 F.run(fn ctx ->
                   assert [["org", "project", "app", "env", ""]] ==
                            F.runtime_sql("""
                            SELECT current_setting('mixer.authz.organization_id'),current_setting('mixer.authz.project_id'),
                              current_setting('mixer.authz.application_id'),current_setting('mixer.authz.environment_id'),
                              current_setting('mixer.authz.directory_mode')
                            """).rows

                   Context.effect!(ctx, Runtime, "artifact.read", F.target(), fn _ ->
                     F.probe!()
                   end)

                   {:ok, :exact_artifact}
                 end)
               after
                 for key <- keys,
                     do: F.runtime_sql("SELECT set_config($1,'',false)", ["mixer.authz." <> key])
               end
             end)

    assert [["written"]] == F.sql("SELECT id FROM public.transaction_probe").rows
  end

  test "directory mode checkpoint failure stays latched even after mode restoration" do
    for mode <- ~w(organizations projects) do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx ->
                 Context.effect!(ctx, Runtime, "artifact.read", F.target(), fn _ -> F.probe!() end)

                 Session.context!(Runtime, directory_mode: mode)

                 try do
                   Context.checkpoint!(ctx, Runtime, "artifact.read", F.target())
                   flunk("changed directory mode unexpectedly survived checkpoint")
                 catch
                   :throw, _ -> :caught_rollback
                 end

                 Session.context!(Runtime, directory_mode: nil)
                 {:ok, :must_not_commit}
               end)

      assert F.empty_probe?()
    end
  end

  test "returned identity linkage and an earlier artifact context cannot authorize a directory transaction effect" do
    assert {:ok, old} = F.run(fn ctx -> {:ok, ctx} end)

    assert {:ok, :no_authority} =
             Runtime.transaction(fn ->
               linkage = Session.prepare_identity!(Runtime, Policy.identity_key(F.identity()))
               Session.context!(Runtime, directory_mode: "organizations")
               refute Context.active?()

               for attempted <- [linkage, old] do
                 assert_raise Context.Invalid, fn ->
                   Context.effect!(attempted, Runtime, "artifact.read", F.target(), fn _ ->
                     F.probe!()
                   end)
                 end
               end

               :no_authority
             end)

    assert F.empty_probe?()
  end
end
