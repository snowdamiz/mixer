defmodule MixerHosted.Authorization.TransactionFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_transaction_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.TransactionFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_transaction_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.TransactionFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_transaction_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.TransactionFixture.Foreign do
  use Ecto.Repo, otp_app: :mixer_transaction_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.TransactionFixture do
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Authorization.TransactionFixture.{Admin, Runtime}
  alias MixerHosted.Identity.VerifiedIdentity

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @locks ~w(profiles principals families credentials organization_heads project_heads)
  def tables, do: @tables
  def locks, do: @locks
  def sql(sql, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, sql, params, log: false)

  def runtime_sql(sql, params \\ []),
    do: Ecto.Adapters.SQL.query!(Runtime, sql, params, log: false)

  def now, do: System.system_time(:second)

  def identity(changes \\ %{}) do
    struct!(
      VerifiedIdentity,
      Map.merge(
        %{
          profile_id: "profile",
          profile_version: 1,
          issuer: "https://issuer.example",
          subject: "subject",
          client_id: "client",
          credential_ref: "token",
          issued_at: now() - 20,
          expires_at: now() + 600,
          identity_class: :human,
          scopes: ["mixer.artifact.read", "mixer.artifact.upload", "mixer.audit.read"]
        },
        changes
      )
    )
  end

  def target(changes \\ %{}) do
    struct!(
      Scope,
      Map.merge(
        %{
          organization_id: "org",
          project_id: "project",
          application_id: "app",
          environment_id: "env"
        },
        changes
      )
    )
  end

  def run(
        callback \\ fn _ -> {:ok, :accepted} end,
        i \\ identity(),
        a \\ "artifact.read",
        t \\ target(),
        repo \\ Runtime
      ),
      do: Authorization.with_authorized_transaction(i, a, t, callback, repo)

  def seed! do
    sql(
      "TRUNCATE " <>
        Enum.map_join(Enum.reverse(@tables), ",", &("public.mixer_authz_" <> &1)) <> " CASCADE"
    )

    sql("TRUNCATE public.transaction_probe")

    sql(
      "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https://issuer.example','client','human',true)"
    )

    sql("INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,2)")

    sql(
      "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,'subject','human','person',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,3)"
    )

    sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'token','person','family',true,0,NULL,4)"
    )

    sql("INSERT INTO public.mixer_authz_organizations VALUES ('org',true)")
    sql("INSERT INTO public.mixer_authz_projects VALUES ('org','project',true)")
    sql("INSERT INTO public.mixer_authz_applications VALUES ('org','project','app',true)")
    sql("INSERT INTO public.mixer_authz_environments VALUES ('org','project','app','env',true)")
    sql("INSERT INTO public.mixer_authz_organization_heads VALUES ('org',5)")
    sql("INSERT INTO public.mixer_authz_project_heads VALUES ('org','project',6)")

    sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org','project','exact_project','developer',true,0,NULL,7)"
    )

    :ok
  end

  def probe!, do: runtime_sql("INSERT INTO public.transaction_probe(id) VALUES ('written')")
  def empty_probe?, do: sql("SELECT count(*) FROM public.transaction_probe").rows == [[0]]

  def clean? do
    not MixerHosted.Authorization.Transaction.Context.active?() and
      runtime_sql("SELECT coalesce(current_setting('mixer.authz.transaction_marker',true),'')").rows ==
        [[""]] and
      runtime_sql("SELECT count(*) FROM public.mixer_authz_credentials").rows == [[0]]
  end

  def await_expiry(i) do
    remaining = max(0, i.expires_at * 1_000 - System.system_time(:millisecond) + 10)
    Process.sleep(remaining)
  end

  def edge! do
    # Begin near the next wall-clock second so expiry during a sub-500ms lock
    # wait is deterministic without changing the production clock seam.
    delay = Integer.mod(820 - Integer.mod(System.system_time(:millisecond), 1_000), 1_000)
    Process.sleep(delay)
  end
end

defmodule MixerHosted.Authorization.TransactionTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Transaction.{Context, Snapshot}
  alias MixerHosted.Authorization.TransactionFixture, as: F
  alias MixerHosted.Authorization.TransactionFixture.{Admin, Migration, Runtime, Foreign}

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_TRANSACTION_TEST_PORT")),
      database: "mixer_customer_transaction",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "txn_fixture_admin", pool_size: 4]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "txn_fixture_admin",
           pool_size: 2,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE txn_authz_owner", []) end
         ]}
    )

    start_supervised!({Runtime, settings ++ [username: "txn_authz_runtime", pool_size: 2]})
    start_supervised!({Foreign, settings ++ [username: "txn_authz_runtime", pool_size: 1]})

    assert :ok =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_003,
               MixerHosted.Repo.Migrations.AddCustomerAuthorization,
               log: false
             )

    assert :ok =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_004,
               MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
               log: false
             )

    assert :already_up =
             Ecto.Migrator.up(
               Migration,
               20_261_025_000_004,
               MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
               log: false
             )

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

  test "owned local SQL transaction commits complete bounded snapshot and never accepts a pure decision" do
    i = F.identity()

    assert {:ok, snapshot} =
             F.run(
               fn ctx ->
                 assert Runtime.in_transaction?()

                 snapshot =
                   Context.effect!(ctx, Runtime, "artifact.read", F.target(), fn fresh ->
                     F.probe!()
                     fresh
                   end)

                 assert snapshot.profile.state_revision == 1
                 assert snapshot.binding.revision == 1
                 assert snapshot.principal.revision == 2
                 assert snapshot.family.revision == 3
                 assert snapshot.credential.revision == 4
                 assert snapshot.family.id == snapshot.credential.family_id
                 assert [member] = snapshot.memberships
                 assert member.revision == 7 and member.role == "developer"

                 assert snapshot.organization_head.revision == 5 and
                          snapshot.project_head.revision == 6

                 assert snapshot.identity.issued_at == i.issued_at
                 assert snapshot.identity.expires_at == i.expires_at
                 assert byte_size(snapshot.request_id) == 32
                 assert byte_size(snapshot.binding.subject_digest) == 64
                 refute Map.has_key?(snapshot.identity, :subject)
                 assert ctx.snapshot.request_id == snapshot.request_id
                 {:ok, snapshot}
               end,
               i
             )

    assert [["written"]] == F.sql("SELECT id FROM public.transaction_probe").rows
    assert snapshot.action == "artifact.read"

    assert_raise Context.Invalid, fn ->
      Context.checkpoint!(
        struct(MixerHosted.Authorization.Policy.Decision),
        Runtime,
        "artifact.read",
        F.target()
      )
    end
  end

  test "all roles retain their exact action ceilings and audit requires project-only scope" do
    for role <- ~w(owner administrator developer release_manager billing_manager viewer),
        action <- ~w(artifact.read artifact.upload audit.read) do
      F.sql("UPDATE public.mixer_authz_memberships SET role=$1", [role])

      target =
        if action == "audit.read",
          do: F.target(%{application_id: nil, environment_id: nil}),
          else: F.target()

      allowed =
        if action == "artifact.upload",
          do: role in ~w(owner administrator developer),
          else: role != "billing_manager"

      expected = if allowed, do: {:ok, :accepted}, else: {:error, :permission_denied}
      assert expected == F.run(fn _ -> {:ok, :accepted} end, F.identity(), action, target)
    end

    assert {:error, :invalid_request} = F.run(fn _ -> flunk() end, F.identity(), "audit.read")
  end

  test "invalid identity action target and nested invocation fail before a callback" do
    for {i, a, t} <- [
          {nil, "artifact.read", F.target()},
          {F.identity(), "publish", F.target()},
          {F.identity(), "artifact.read", %{organization_id: "org"}}
        ] do
      assert {:error, _} =
               Authorization.with_authorized_transaction(
                 i,
                 a,
                 t,
                 fn _ -> flunk() end,
                 MissingTransactionRepo
               )
    end

    assert {:ok, {:error, :authorization_unavailable}} =
             Runtime.transaction(fn -> F.run(fn _ -> flunk() end) end)

    assert {:ok, :outer} =
             F.run(fn _ ->
               assert {:error, :authorization_unavailable} = F.run(fn _ -> flunk() end)
               {:ok, :outer}
             end)
  end

  test "context rejects every changed field and latches rescued rollback attempts" do
    assert {:ok, original} = F.run(fn ctx -> {:ok, ctx} end)

    assert_raise Context.Invalid, fn ->
      Context.checkpoint!(original, Runtime, "artifact.read", F.target())
    end

    changes = [
      owner: self(),
      repo: Foreign,
      dynamic_repo: Foreign,
      connection: [],
      marker: "forged",
      identity: F.identity(%{subject: "forged"}),
      action: "artifact.upload",
      target: F.target(%{environment_id: "forged"}),
      snapshot: %{},
      admitted_at: 0,
      deadline: 0
    ]

    for {field, value} <- changes do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx ->
                 changed =
                   if field == :owner,
                     do: %{ctx | owner: spawn(fn -> :ok end)},
                     else: Map.put(ctx, field, value)

                 try do
                   Context.checkpoint!(changed, Runtime, "artifact.read", F.target())
                 catch
                   _, _ -> :caught
                 end

                 F.probe!()
                 {:ok, :rescued}
               end)

      assert F.empty_probe?()
    end

    assert {:error, :authorization_unavailable} =
             F.run(fn ctx ->
               try do
                 Context.checkpoint!(
                   Map.put(ctx, :role, "owner"),
                   Runtime,
                   "artifact.read",
                   F.target()
                 )
               catch
                 _, _ -> :caught
               end

               {:ok, :rescued}
             end)
  end

  test "wrong process foreign repo action target transaction marker and identity GUC reject" do
    assert {:ok, :owner} =
             F.run(fn ctx ->
               assert :rejected =
                        Task.async(fn ->
                          assert_raise Context.Invalid, fn ->
                            Context.checkpoint!(ctx, Runtime, "artifact.read", F.target())
                          end

                          :rejected
                        end)
                        |> Task.await()

               {:ok, :owner}
             end)

    for attempt <- [
          fn ctx -> Context.checkpoint!(ctx, Foreign, "artifact.read", F.target()) end,
          fn ctx -> Context.checkpoint!(ctx, Runtime, "artifact.upload", F.target()) end,
          fn ctx ->
            Context.checkpoint!(
              ctx,
              Runtime,
              "artifact.read",
              F.target(%{environment_id: "other"})
            )
          end,
          fn ctx ->
            F.runtime_sql("SELECT set_config('mixer.authz.transaction_marker','replaced',true)")
            Context.checkpoint!(ctx, Runtime, "artifact.read", F.target())
          end,
          fn ctx ->
            F.runtime_sql("SELECT set_config('mixer.authz.subject','replaced',true)")
            Context.checkpoint!(ctx, Runtime, "artifact.read", F.target())
          end
        ] do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx ->
                 attempt.(ctx)
                 {:ok, :unexpected}
               end)
    end

    assert {:error, :authorization_unavailable} =
             F.run(fn ctx ->
               previous = Runtime.put_dynamic_repo(Foreign)

               try do
                 Context.checkpoint!(ctx, Runtime, "artifact.read", F.target())
               after
                 Runtime.put_dynamic_repo(previous)
               end

               {:ok, :unexpected}
             end)
  end

  test "after rollback and another real transaction cannot reuse a captured context" do
    parent = self()

    assert {:error, :conflict} =
             F.run(fn ctx ->
               send(parent, {:old_context, ctx})
               {:error, :conflict}
             end)

    assert_receive {:old_context, old}

    assert_raise Context.Invalid, fn ->
      Context.checkpoint!(old, Runtime, "artifact.read", F.target())
    end

    assert {:error, :authorization_unavailable} =
             F.run(fn _ ->
               Context.checkpoint!(old, Runtime, "artifact.read", F.target())
               {:ok, :unexpected}
             end)

    assert {:ok, :accepted} = F.run()
  end

  test "every callback error malformed value exception throw and exit rolls back actual local SQL" do
    callbacks = [
      fn _ -> {:error, :conflict} end,
      fn _ -> {:error, :storage_unavailable} end,
      fn _ -> {:error, :secret_unbounded_reason} end,
      fn _ -> :ok end,
      fn _ -> {:ok, :x, :extra} end,
      fn _ -> raise "synthetic failure" end,
      fn _ -> throw(:synthetic_failure) end,
      fn _ -> exit(:synthetic_failure) end,
      fn _ -> Runtime.rollback(:authorization_unavailable) end
    ]

    for callback <- callbacks do
      assert {:error, _} =
               F.run(fn ctx ->
                 F.probe!()
                 callback.(ctx)
               end)

      assert F.empty_probe?()
      assert F.clean?()
    end

    assert {:ok, :accepted} = F.run()
  end

  test "expiry before effect blocks effect and final expiry rolls back an earlier local SQL write" do
    i = F.identity(%{expires_at: F.now() + 1})

    assert {:error, :unauthenticated} =
             F.run(
               fn ctx ->
                 F.await_expiry(i)

                 Context.effect!(ctx, Runtime, "artifact.read", F.target(), fn _ ->
                   flunk("expired effect")
                 end)

                 {:ok, :unexpected}
               end,
               i
             )

    assert F.empty_probe?()
    i = F.identity(%{expires_at: F.now() + 1})

    assert {:error, :unauthenticated} =
             F.run(
               fn ctx ->
                 Context.effect!(ctx, Runtime, "artifact.read", F.target(), fn _ -> F.probe!() end)

                 F.await_expiry(i)
                 {:ok, :would_commit}
               end,
               i
             )

    assert F.empty_probe?()
  end

  test "fresh time after an actual profile lock wait rejects a token expired during that wait" do
    parent = self()

    writer =
      Task.async(fn ->
        Admin.transaction(fn ->
          F.sql("SELECT 1 FROM public.mixer_authz_profiles FOR UPDATE")
          send(parent, {:locked, self()})

          receive do
            :release -> :ok
          after
            2_000 -> flunk("writer release timeout")
          end
        end)
      end)

    assert_receive {:locked, writer_pid}
    F.edge!()
    i = F.identity(%{expires_at: F.now() + 1})
    authorization = Task.async(fn -> F.run(fn _ -> flunk("expired callback") end, i) end)
    Process.sleep(250)
    send(writer_pid, :release)
    assert {:ok, :ok} = Task.await(writer)
    assert {:error, :unauthenticated} = Task.await(authorization)
    assert F.empty_probe?()
  end

  test "separate family token membership windows and profile binding state are retained and enforced" do
    for table <- ~w(profiles bindings principals families credentials) do
      F.sql("UPDATE public.mixer_authz_#{table} SET active=false")
      assert {:error, :unauthenticated} = F.run()
      F.sql("UPDATE public.mixer_authz_#{table} SET active=true")
    end

    for table <- ~w(families credentials) do
      F.sql("UPDATE public.mixer_authz_#{table} SET not_before=$1", [F.now() - 10])
      assert {:error, :unauthenticated} = F.run()
      F.sql("UPDATE public.mixer_authz_#{table} SET not_before=0,expires_at=$1", [F.now()])
      assert {:error, :unauthenticated} = F.run()
      F.sql("UPDATE public.mixer_authz_#{table} SET expires_at=NULL")
    end

    F.sql("UPDATE public.mixer_authz_memberships SET expires_at=$1", [F.now() + 1])

    assert {:error, _} =
             F.run(fn ctx ->
               Process.sleep(1_100)
               Context.checkpoint!(ctx, Runtime, "artifact.read", F.target())
               {:ok, :unexpected}
             end)
  end

  test "snapshot validation independently rejects extra missing changed nested and oversized data" do
    i = F.identity()

    assert {:ok, {s, d}} =
             F.run(
               fn ctx ->
                 # Policy is used here solely to independently exercise the closed data
                 # projection validator; the returned Decision is never domain authority.
                 e =
                   MixerHosted.Authorization.Postgres.Evidence.load!(
                     Runtime,
                     %{
                       identity: MixerHosted.Authorization.Policy.identity_key(i),
                       action: "artifact.read",
                       target: F.target()
                     },
                     %{principal_id: "person", family_id: "family"}
                   )

                 {:ok, d} =
                   MixerHosted.Authorization.Policy.evaluate(
                     i,
                     "artifact.read",
                     F.target(),
                     e,
                     ctx.snapshot.checked_at
                   )

                 {:ok, {ctx.snapshot, d}}
               end,
               i
             )

    assert Snapshot.valid?(s, i, d)

    for bad <- [
          Map.put(s, :extra, true),
          Map.delete(s, :family),
          put_in(s, [:profile, :state_revision], 0),
          put_in(s, [:binding, :subject_digest], "bad"),
          put_in(s, [:family, :id], "wrong"),
          put_in(s, [:family, :revision], 0),
          put_in(s, [:credential, :family_id], "wrong"),
          put_in(s, [:identity, :expires_at], 0),
          put_in(s, [:organization_head, :revision], 0),
          Map.put(s, :memberships, List.duplicate(hd(s.memberships), 65)),
          Map.put(s, :memberships, [hd(s.memberships) | :improper]),
          Map.put(s, :request_id, "unbounded"),
          put_in(s, [:profile, :extra], true)
        ] do
      refute Snapshot.valid?(bad, i, d)
    end
  end

  test "new revision baseline is one and constraints reject zero negative or excessive revisions" do
    assert [[1]] = F.sql("SELECT state_revision FROM public.mixer_authz_profiles").rows
    assert [[1]] = F.sql("SELECT revision FROM public.mixer_authz_bindings").rows

    for {table, column} <- [{"profiles", "state_revision"}, {"bindings", "revision"}],
        value <- [0, -1, 9_007_199_254_740_992] do
      assert_raise Postgrex.Error, fn ->
        F.sql("UPDATE public.mixer_authz_#{table} SET #{column}=$1", [value])
      end
    end

    assert {:ok, :accepted} = F.run()
  end

  test "direct privileged owner DML and indirect predefined roles fail the owned transaction" do
    for repo <- [Admin, Migration],
        do:
          assert(
            {:error, :authorization_unavailable} =
              F.run(fn _ -> flunk() end, F.identity(), "artifact.read", F.target(), repo)
          )

    for grant <- [
          "GRANT txn_authz_owner TO txn_authz_runtime",
          "GRANT UPDATE(active) ON public.mixer_authz_principals TO txn_authz_runtime"
        ] do
      F.sql(grant)

      try do
        assert {:error, :authorization_unavailable} = F.run()
      after
        if String.starts_with?(grant, "GRANT txn"),
          do: F.sql("REVOKE txn_authz_owner FROM txn_authz_runtime"),
          else:
            F.sql("REVOKE UPDATE(active) ON public.mixer_authz_principals FROM txn_authz_runtime")
      end
    end

    for [role] <-
          F.sql(
            "SELECT rolname::text FROM pg_roles WHERE substr(rolname::text,1,3)='pg_' AND rolname <> 'pg_database_owner' ORDER BY rolname"
          ).rows do
      F.sql("GRANT #{role} TO txn_authz_runtime")

      try do
        assert {:error, :authorization_unavailable} = F.run()
      after
        F.sql("REVOKE #{role} FROM txn_authz_runtime")
      end
    end

    F.sql("CREATE ROLE txn_indirect NOLOGIN NOINHERIT")
    F.sql("GRANT txn_indirect TO txn_authz_runtime WITH INHERIT FALSE, SET TRUE")

    try do
      assert {:ok, :accepted} = F.run()

      for role <-
            ~w(pg_read_server_files pg_write_server_files pg_execute_server_program pg_monitor) do
        F.sql("GRANT #{role} TO txn_indirect WITH INHERIT FALSE, SET TRUE")

        try do
          assert {:error, :authorization_unavailable} = F.run()
        after
          F.sql("REVOKE #{role} FROM txn_indirect")
        end
      end
    after
      F.sql("REVOKE txn_indirect FROM txn_authz_runtime")
      F.sql("DROP ROLE txn_indirect")
    end

    assert {:ok, :accepted} = F.run()
  end
end
