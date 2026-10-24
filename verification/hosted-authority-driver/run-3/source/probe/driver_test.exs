Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Application.ensure_all_started(:crypto)
Logger.configure(level: :critical)
{:ok, _} = Agent.start_link(fn -> %{queries: [], observations: %{}} end, name: DriverEvidence)

:telemetry.attach(
  "authority-driver-evidence",
  [:mixer_hosted, :repo, :query],
  fn _event, measure, meta, _ ->
    Agent.update(DriverEvidence, fn s ->
      %{
        s
        | queries: [
            %{
              query: meta.query,
              parameter_count: length(meta.params),
              total_time_native: measure.total_time
            }
            | s.queries
          ]
      }
    end)
  end,
  nil
)

config = [
  socket_dir: System.fetch_env!("DRIVER_SOCKET"),
  username: "mixer_hosted_runtime",
  database: "authority_contract",
  pool_size: 1,
  log: false,
  connect_timeout: 2_000
]

{:ok, repo} = MixerHosted.Repo.start_link(config)

{:ok, owner} =
  Postgrex.start_link(
    socket_dir: System.fetch_env!("DRIVER_SOCKET"),
    username: System.fetch_env!("USER"),
    database: "authority_contract",
    name: DriverFixtureOwner
  )

defmodule DriverTests do
  import ExUnit.Assertions
  alias MixerHosted.AuthorityDriver.{Coordinator, Envelope, Rejected, Transport}
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Repo
  @p "00000000-0000-0000-0000-000000000001"
  @b "00000000-0000-0000-0000-000000000002"
  @f "00000000-0000-0000-0000-000000000003"
  @m "00000000-0000-0000-0000-000000000004"
  def q(sql, params \\ []), do: Postgrex.query!(DriverFixtureOwner, sql, params, log: false)
  def scalar(sql, params \\ []), do: q(sql, params).rows |> hd() |> hd()
  def rq(sql, params \\ []), do: Repo.query!(sql, params, log: false)

  def seed(role \\ "developer", options \\ []) do
    tables =
      q("SELECT tablename FROM pg_tables WHERE schemaname='mixer_authz' ORDER BY tablename").rows
      |> Enum.map_join(",", fn [n] -> "mixer_authz." <> n end)

    q("TRUNCATE " <> tables <> " CASCADE")
    q("TRUNCATE driver_fixture.effects")
    now = System.system_time(:second)
    issued = Keyword.get(options, :issued, now - 10)
    expires = Keyword.get(options, :expires, now + 120)
    ref = Keyword.get(options, :ref, "credential-é\\exact")
    profile = Keyword.get(options, :profile, "profile")
    issuer = Keyword.get(options, :issuer, "https://issuer.example")
    client = Keyword.get(options, :client, "client")
    subject = Keyword.get(options, :subject, "subject")
    rev = Keyword.get(options, :revision, 1)

    q("INSERT INTO mixer_authz.identity_trust_profiles VALUES($1,1,true,$2,$3,'human',$4)", [
      profile,
      issuer,
      client,
      rev
    ])

    q("INSERT INTO mixer_authz.organizations VALUES('o','active',$1),('other','active',1)", [rev])

    q("INSERT INTO mixer_authz.principals VALUES($1,'human','active',0,$2,NULL)", [
      Ecto.UUID.dump!(@p),
      rev
    ])

    q("INSERT INTO mixer_authz.external_identity_bindings VALUES($1,$2,$3,$4,$5,'human',$6)", [
      Ecto.UUID.dump!(@b),
      profile,
      issuer,
      subject,
      client,
      Ecto.UUID.dump!(@p)
    ])

    q("INSERT INTO mixer_authz.credential_families VALUES($1,$2,$3,$4,'active',0,$5)", [
      Ecto.UUID.dump!(@f),
      Ecto.UUID.dump!(@b),
      Ecto.UUID.dump!(@p),
      profile,
      rev
    ])

    q("INSERT INTO mixer_authz.credential_references VALUES($1,$2,$3,$4,$5,$6,$7)", [
      Ecto.UUID.dump!(@b),
      :crypto.hash(:sha256, ref),
      Ecto.UUID.dump!(@f),
      Ecto.UUID.dump!(@p),
      profile,
      issued,
      expires
    ])

    q(
      "INSERT INTO mixer_authz.projects VALUES('o','p','active',$1),('o','q','active',1),('other','p','active',1)",
      [rev]
    )

    q("INSERT INTO mixer_authz.applications VALUES('o','p','app','active',1)")

    q(
      "INSERT INTO mixer_authz.environments VALUES('o','p','app','dev','active','development',1),('o','p','app','prod','active','production',1)"
    )

    q("INSERT INTO mixer_authz.organization_authorization_heads VALUES('o',$1),('other',1)", [rev])

    q(
      "INSERT INTO mixer_authz.project_authorization_heads VALUES('o','p',$1),('o','q',1),('other','p',1)",
      [rev]
    )

    q(
      "INSERT INTO mixer_authz.project_memberships VALUES($1,'o','p',$2,$3,'active',NULL,NULL,$4,$5)",
      [Ecto.UUID.dump!(@m), Ecto.UUID.dump!(@p), role, rev, :binary.copy(<<68>>, 32)]
    )

    {%Envelope{
       identity: %VerifiedIdentity{
         profile_id: profile,
         profile_version: 1,
         issuer: issuer,
         subject: subject,
         client_id: client,
         credential_ref: ref,
         issued_at: issued,
         expires_at: expires,
         identity_class: :human,
         scopes: ~w(mixer.artifact.read mixer.artifact.upload mixer.audit.read)
       },
       authentication_completed_at: now
     }, target()}
  end

  def target(action \\ "artifact.upload") do
    t = %{
      action: action,
      organization: "o",
      project: "p",
      app: "app",
      environment: "dev",
      platform: "ios",
      runtime_sha256: :binary.copy(<<34>>, 32),
      manifest_sha256: :binary.copy(<<51>>, 32)
    }

    if action == "audit.read",
      do: %{
        t
        | app: nil,
          environment: nil,
          platform: nil,
          runtime_sha256: nil,
          manifest_sha256: nil
      },
      else: t
  end

  def no_effects, do: assert(scalar("SELECT count(*) FROM driver_fixture.effects") == 0)

  def cleaned do
    assert Process.get(Coordinator.marker()) == nil

    for _ <- 1..50 do
      try do
        r =
          rq(
            "SELECT current_setting('mixer_authz.invocation_nonce',true),current_setting('mixer_authz.deadline',true),current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('transaction_isolation'),current_setting('role')"
          ).rows

        assert r in [
                 [[nil, nil, "0", "0", "read committed", "none"]],
                 [["", "", "0", "0", "read committed", "none"]]
               ]

        throw(:clean)
      rescue
        _ in DBConnection.ConnectionError -> Process.sleep(20)
      end
    end

    raise "no fresh runtime connection"
  catch
    :clean -> :ok
  end

  def rejected(fun) do
    try do
      case fun.() do
        {:error, _} -> :ok
        _ -> flunk("unexpected accepted invocation")
      end
    rescue
      _ in [Rejected, MatchError] -> :ok
    end

    no_effects()
    cleaned()
  end

  def observe(name, value),
    do: Agent.update(DriverEvidence, &put_in(&1, [:observations, name], value))

  def cases do
    roles =
      for role <- ~w(owner administrator developer release_manager billing_manager viewer),
          action <- ~w(artifact.read artifact.upload audit.read) do
        {"driver role/scope #{role} #{action}",
         fn ->
           {e, _} = seed(role)
           t = target(action)
           r = Coordinator.run(e, t, :effect)

           allowed =
             role in ~w(owner administrator developer) or
               (action != "artifact.upload" and role in ~w(release_manager viewer))

           if allowed,
             do:
               (
                 assert {:ok, c} = r
                 assert c.decision.outcome == "allowed"
                 assert scalar("SELECT count(*) FROM driver_fixture.effects") == 1
               ),
             else:
               (
                 assert r == {:error, {:denied, "forbidden"}}
                 no_effects()
               )
         end}
      end

    deny_states = [
      {"absent binding", fn e -> %{e | identity: %{e.identity | subject: "other"}} end, nil},
      {"disabled profile", & &1,
       "UPDATE mixer_authz.identity_trust_profiles SET enabled=false,revision=revision+1"},
      {"version", fn e -> %{e | identity: %{e.identity | profile_version: 2}} end, nil},
      {"disabled principal", & &1,
       "UPDATE mixer_authz.principals SET status='disabled',revision=revision+1"},
      {"revoked family", & &1,
       "UPDATE mixer_authz.credential_families SET status='revoked',revision=revision+1"},
      {"principal valid-after", & &1,
       "UPDATE mixer_authz.principals SET valid_after=9007199254740991,revision=revision+1"},
      {"family valid-after", & &1,
       "UPDATE mixer_authz.credential_families SET valid_after=9007199254740991,revision=revision+1"},
      {"credential denial", & &1,
       "INSERT INTO mixer_authz.credential_denials SELECT binding_id,jti_sha256,accepted_expires_at,accepted_issued_at,accepted_expires_at+30,1,'revoked' FROM mixer_authz.credential_references"},
      {"stale completion original",
       fn e -> %{e | authentication_completed_at: e.authentication_completed_at - 46} end, nil},
      {"future completion",
       fn e -> %{e | authentication_completed_at: e.authentication_completed_at + 31} end, nil},
      {"expired credential", fn e -> e end, :expired}
    ]

    states =
      for {name, change, sql} <- deny_states do
        {"driver current identity #{name}",
         fn ->
           {e, t} =
             if sql == :expired,
               do: seed("developer", expires: System.system_time(:second) - 1),
               else: seed()

           if is_binary(sql), do: q(sql)
           rejected(fn -> Coordinator.run(change.(e), t, :effect) end)
         end}
      end

    roles ++
      states ++
      [
        {"UTF8 exact SHA256 and wide integers complete roundtrip",
         fn ->
           {e, t} =
             seed("developer",
               profile: "profilé\\x",
               issuer: "https://例.example/\\",
               subject: "subject-λ\\",
               client: "clïent\\",
               issued: 0,
               expires: 9_007_199_254_740_991,
               revision: 9_223_372_036_854_775_806
             )

           assert {:ok, c} = Coordinator.run(e, t, :budget)
           assert c.identity.credential_sha256 == :crypto.hash(:sha256, e.identity.credential_ref)

           assert c.identity.expires_at == 9_007_199_254_740_991 and
                    c.admission.profile_revision == 9_223_372_036_854_775_806

           assert is_binary(c.transaction.full_xid) and
                    c.transaction.full_xid ==
                      Integer.to_string(String.to_integer(c.transaction.full_xid))

           assert c.decision.memberships == [
                    %{
                      lifecycle_id: Ecto.UUID.dump!(@m),
                      role: "developer",
                      revision: 9_223_372_036_854_775_806
                    }
                  ]

           observe(:transport, %{
             full_xid: c.transaction.full_xid,
             deadline_precision: elem(c.transaction.deadline.microsecond, 1),
             lock_timestamp_precision: elem(c.admission.lock_statement_at.microsecond, 1),
             wide_expiry: c.identity.expires_at,
             wide_revision: c.admission.profile_revision
           })
         end},
        {"malformed transport rejected before checkout and raw UTF8 bytes preserved",
         fn ->
           {e, t} = seed()
           before = length(Agent.get(DriverEvidence, & &1.queries))

           for ref <- [<<0>>, <<255>>, "", String.duplicate("x", 257)],
               do:
                 rejected(fn ->
                   Coordinator.run(
                     %{e | identity: %{e.identity | credential_ref: ref}},
                     t,
                     :effect
                   )
                 end)

           # cleanup queries are explicit; invalid transport never entered a transaction/function.
           new =
             Agent.get(DriverEvidence, & &1.queries)
             |> Enum.take(length(Agent.get(DriverEvidence, & &1.queries)) - before)

           refute Enum.any?(new, &String.contains?(&1.query, "lookup_admission"))

           rejected(fn ->
             Coordinator.run(%{e | identity: %{e.identity | scopes: ["unknown"]}}, t, :effect)
           end)

           rejected(fn -> Coordinator.run(e, %{t | action: "release.publish"}, :effect) end)
         end},
        {"scope intersection and ancestry denial no callback",
         fn ->
           {e, t} = seed()

           rejected(fn ->
             Coordinator.run(
               %{e | identity: %{e.identity | scopes: ["mixer.artifact.read"]}},
               t,
               :effect
             )
           end)

           for {table, where} <- [
                 {"organizations", "organization='o'"},
                 {"projects", "organization='o' AND project='p'"},
                 {"applications", "true"},
                 {"environments", "environment='dev'"}
               ] do
             {e, t} = seed()

             q(
               "UPDATE mixer_authz." <>
                 table <> " SET status='deleted',revision=revision+1 WHERE " <> where
             )

             rejected(fn -> Coordinator.run(e, t, :effect) end)
           end
         end},
        {"exact active immutable context foreign process Repo dynamic Repo nested target",
         fn ->
           {e, t} = seed()
           assert {:ok, _} = Coordinator.run(e, t, :tamper)
           no_effects()
           old = Repo.put_dynamic_repo(DriverFixtureOwner)

           try do
             assert_raise Rejected, fn -> Coordinator.run(e, t, :effect) end
           after
             Repo.put_dynamic_repo(old)
           end
         end},
        {"closed contexts commit rollback exception cleanup",
         fn ->
           {e, t} = seed()
           assert {:ok, c} = Coordinator.run(e, t)
           assert_raise Rejected, fn -> Coordinator.synthetic_effect!(c) end
           assert {:error, :fixture} = Coordinator.run(e, t, :rollback)
           r = Process.delete(:captured)
           assert_raise Rejected, fn -> Coordinator.synthetic_effect!(r) end

           assert_raise RuntimeError, "fixture exception", fn ->
             Coordinator.run(e, t, :exception)
           end

           r = Process.delete(:captured)
           assert_raise Rejected, fn -> Coordinator.synthetic_effect!(r) end
           no_effects()
           cleaned()
         end},
        {"raw COMMIT BEGIN restored nonce rejects full xid change",
         fn ->
           {e, t} = seed()
           rejected(fn -> Coordinator.run(e, t, :raw_rebegin) end)
         end},
        {"nonce changed rejects synthetic effect",
         fn ->
           {e, t} = seed()
           rejected(fn -> Coordinator.run(e, t, :nonce) end)
         end},
        {"callback overrun original monotonic deadline rolls back effect",
         fn ->
           {e, t} = seed()
           rejected(fn -> Coordinator.run(e, t, :overrun, 180) end)
         end},
        {"slow SQL remaining budget rolls back effect",
         fn ->
           {e, t} = seed()
           rejected(fn -> Coordinator.run(e, t, :slow_sql, 220) end)
         end},
        {"busy checkout queue false never callback",
         fn ->
           {e, t} = seed()
           parent = self()

           holder =
             Task.async(fn ->
               Repo.checkout(fn ->
                 send(parent, :held)

                 receive do
                   :release -> :ok
                 after
                   2_000 -> raise "holder timeout"
                 end
               end)
             end)

           assert_receive :held
           started = System.monotonic_time(:millisecond)

           try do
             assert_raise Rejected, fn -> Coordinator.run(e, t, :effect, 500) end
           after
             send(holder.pid, :release)
             Task.await(holder)
           end

           observe(:busy_checkout, %{elapsed_ms: System.monotonic_time(:millisecond) - started})
           no_effects()
         end},
        {"actual least privilege runtime denies owner writer and table access",
         fn ->
           for sql <- [
                 "SELECT * FROM mixer_authz.principals",
                 "SET ROLE mixer_hosted_schema_owner",
                 "SET ROLE mixer_hosted_authz_resolver",
                 "SET ROLE mixer_hosted_domain_writer",
                 "SELECT mixer_authz.recheck_current(NULL,NULL,NULL,NULL)",
                 "CREATE TEMP TABLE denied(a int)"
               ] do
             e = assert_raise Postgrex.Error, fn -> rq(sql) end
             assert e.postgres.pg_code == "42501"
           end

           assert [["mixer_hosted_runtime", "mixer_hosted_runtime", "none", false, false]] =
                    rq(
                      "SELECT session_user,current_user,current_setting('role'),rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
                    ).rows
         end}
      ] ++
      membership_cases() ++
      lock_cases() ++
      [{"six composite explicit scalar transport including witness and decision", &composites/0}]
  end

  def membership_cases do
    for kind <- [:count64, :count65, :duplicate, :future, :expired, :inclusive, :org_only] do
      {"driver membership #{kind}",
       fn ->
         {e, t} = seed()

         case kind do
           n when n in [:count64, :count65] ->
             q("DROP INDEX mixer_authz.project_memberships_active_unique")
             count = if n == :count64, do: 64, else: 65

             for x <- 1..(count - 1),
                 do:
                   q(
                     "INSERT INTO mixer_authz.project_memberships VALUES($1,'o','p',$2,'viewer','active',NULL,NULL,1,$3)",
                     [<<x::128>>, Ecto.UUID.dump!(@p), :binary.copy(<<68>>, 32)]
                   )

           :duplicate ->
             q(
               "INSERT INTO mixer_authz.organization_memberships VALUES($1,'o','organization_wide',$2,'viewer','active',NULL,NULL,1,$3)",
               [Ecto.UUID.dump!(@m), Ecto.UUID.dump!(@p), :binary.copy(<<68>>, 32)]
             )

           :future ->
             q(
               "UPDATE mixer_authz.project_memberships SET not_before=9007199254740990,revision=2"
             )

           :expired ->
             q("UPDATE mixer_authz.project_memberships SET expires_at=1,revision=2")

           :inclusive ->
             q(
               "UPDATE mixer_authz.project_memberships SET not_before=$1,expires_at=$2,revision=2",
               [System.system_time(:second), System.system_time(:second) + 30]
             )

           :org_only ->
             q("TRUNCATE mixer_authz.project_memberships")

             q(
               "INSERT INTO mixer_authz.organization_memberships VALUES($1,'o','organization_only',$2,'developer','active',NULL,NULL,1,$3)",
               [Ecto.UUID.dump!(@m), Ecto.UUID.dump!(@p), :binary.copy(<<68>>, 32)]
             )
         end

         try do
           r = Coordinator.run(e, t, :effect)

           if kind in [:count64, :inclusive] do
             assert {:ok, c} = r
             assert length(c.decision.memberships) == if(kind == :count64, do: 64, else: 1)
           else
             assert {:error, {:denied, outcome}} = r

             assert outcome ==
                      if(kind in [:count65, :duplicate],
                        do: "authorization_unavailable",
                        else: "not_found"
                      )

             no_effects()
           end
         after
           if kind in [:count64, :count65] do
             q("TRUNCATE mixer_authz.project_memberships")

             q(
               "CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status='active'"
             )
           end
         end
       end}
    end
  end

  def owner_connection do
    {:ok, p} =
      Postgrex.start_link(
        socket_dir: System.fetch_env!("DRIVER_SOCKET"),
        username: System.fetch_env!("USER"),
        database: "authority_contract"
      )

    p
  end

  def oq(p, sql, params \\ []), do: Postgrex.query!(p, sql, params, log: false)

  def wait(victim, blocker) do
    until = System.monotonic_time(:millisecond) + 1_000

    Stream.repeatedly(fn -> scalar("SELECT $1=ANY(pg_blocking_pids($2))", [blocker, victim]) end)
    |> Enum.reduce_while(nil, fn found, _ ->
      cond do
        found ->
          {:halt, :ok}

        System.monotonic_time(:millisecond) > until ->
          flunk("expected database wait absent")

        true ->
          Process.sleep(2)
          {:cont, nil}
      end
    end)
  end

  def lock_cases do
    stages = [
      {"identity_trust_profiles", "profile_id='profile'"},
      {"principals", "principal_id='#{@p}'"},
      {"credential_families", "family_id='#{@f}'"},
      {"organization_authorization_heads", "organization='o'"},
      {"project_authorization_heads", "organization='o' AND project='p'"}
    ]

    [
      {"five actual canonical lock waits observed through driver",
       fn ->
         {e, t} = seed()

         blockers =
           for {table, where} <- stages do
             p = owner_connection()
             oq(p, "BEGIN")
             oq(p, "SELECT 1 FROM mixer_authz." <> table <> " WHERE " <> where <> " FOR UPDATE")
             [[pid]] = oq(p, "SELECT pg_backend_pid()").rows
             {p, pid, table}
           end

         task = Task.async(fn -> Coordinator.run(e, t, :effect) end)

         try do
           victim = runtime_pid()

           for {p, pid, _table} <- blockers do
             wait(victim, pid)
             oq(p, "COMMIT")
           end

           assert {:ok, _} = Task.await(task, 3_000)

           observe(
             :five_waits,
             Enum.map(blockers, fn {_, pid, table} ->
               %{stage: table, blocking_pid: pid, wait_observed: true}
             end)
           )
         after
           for {p, _, _} <- blockers, do: GenServer.stop(p)
         end
       end},
      {"lock timeout 250ms rolls back and no callback",
       fn ->
         {e, t} = seed()
         p = owner_connection()
         oq(p, "BEGIN")

         oq(
           p,
           "SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE"
         )

         start = System.monotonic_time(:millisecond)

         try do
           rejected(fn -> Coordinator.run(e, t, :effect, 2_000) end)
           elapsed = System.monotonic_time(:millisecond) - start
           assert elapsed >= 220 and elapsed < 1_200
           observe(:lock_timeout, %{elapsed_ms: elapsed})
         after
           oq(p, "ROLLBACK")
           GenServer.stop(p)
         end
       end},
      {"revoker before admission commits current denial after confirmed wait",
       fn ->
         {e, t} = seed()
         p = owner_connection()
         oq(p, "BEGIN")

         oq(
           p,
           "SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE"
         )

         oq(p, "UPDATE mixer_authz.project_memberships SET status='revoked',revision=2")

         oq(
           p,
           "UPDATE mixer_authz.project_authorization_heads SET revision=2 WHERE organization='o' AND project='p'"
         )

         [[blocker]] = oq(p, "SELECT pg_backend_pid()").rows
         task = Task.async(fn -> Coordinator.run(e, t, :effect) end)

         try do
           victim = runtime_pid()
           wait(victim, blocker)
           oq(p, "COMMIT")
           assert {:error, {:denied, "not_found"}} = Task.await(task)
           no_effects()
           observe(:revoker_before, %{wait_observed: true})
         after
           GenServer.stop(p)
         end
       end},
      {"admission before revoker retains shared locks until commit",
       fn ->
         {e, t} = seed()
         parent = self()
         # Fixture process waits inside fixed callback only; no product asynchronous work.
         task =
           Task.async(fn ->
             Process.put(:hold_fixture, parent)
             Coordinator.run(e, t, :hold)
           end)

         assert_receive {:allowed, pid, context}, 1_000
         p = owner_connection()
         [[blocker]] = oq(p, "SELECT pg_backend_pid()").rows

         revoker =
           Task.async(fn ->
             oq(p, "BEGIN")

             oq(
               p,
               "UPDATE mixer_authz.project_authorization_heads SET revision=2 WHERE organization='o' AND project='p'"
             )

             oq(p, "UPDATE mixer_authz.project_memberships SET status='revoked',revision=2")
             oq(p, "COMMIT")
           end)

         try do
           wait(blocker, context.transaction.backend)
           send(pid, :release)
           assert {:ok, _} = Task.await(task)
           Task.await(revoker)
           assert scalar("SELECT count(*) FROM driver_fixture.effects") == 1
           observe(:revoker_after, %{wait_observed: true})
         after
           GenServer.stop(p)
         end
       end},
      {"fresh DB time after confirmed wait observes membership expiry",
       fn ->
         {e, t} = seed()
         boundary = System.system_time(:second) + 1
         q("UPDATE mixer_authz.project_memberships SET expires_at=$1,revision=2", [boundary])
         # Align within 80ms before the expiry so the actual wait stays under 250ms.
         while = fn rec ->
           if System.system_time(:millisecond) < boundary * 1_000 - 80,
             do:
               (
                 Process.sleep(5)
                 rec.(rec)
               ),
             else: :ok
         end

         while.(while)
         p = owner_connection()
         oq(p, "BEGIN")

         oq(
           p,
           "SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE"
         )

         [[blocker]] = oq(p, "SELECT pg_backend_pid()").rows
         task = Task.async(fn -> Coordinator.run(e, t, :effect) end)

         try do
           wait(runtime_pid(), blocker)
           Process.sleep(110)
           oq(p, "COMMIT")
           assert {:error, {:denied, "not_found"}} = Task.await(task)
           no_effects()
           observe(:fresh_time_wait, %{wait_observed: true, expiry: boundary})
         after
           GenServer.stop(p)
         end
       end}
    ]
  end

  def runtime_pid do
    until = System.monotonic_time(:millisecond) + 1_000

    Stream.repeatedly(fn ->
      q(
        "SELECT pid FROM pg_stat_activity WHERE usename='mixer_hosted_runtime' AND state='active'"
      ).rows
    end)
    |> Enum.reduce_while(nil, fn rows, _ ->
      case rows do
        [[pid]] ->
          {:halt, pid}

        _ ->
          if System.monotonic_time(:millisecond) > until, do: flunk("runtime pid not active")
          Process.sleep(2)
          {:cont, nil}
      end
    end)
  end

  def composites do
    {e, t} = seed()
    assert {:ok, c} = Coordinator.run(e, t)
    # Six actual named types, including decision and witness construction. UUID and int8
    # arrays are bound scalars, zipped in fixed SQL; no record string serializer.
    d = c.decision
    m = hd(d.memberships)

    sql =
      "SELECT (w).lifecycle_id,(w).role,(w).revision,(d).decision_at,(d).memberships FROM (SELECT ROW($1::uuid,$2::text,$3::int8)::mixer_authz.membership_witness_v1 w,ROW($4::text,$5::uuid,$6::uuid,$7::uuid,$8::numeric,$9::int8,$10::int8,$11::int8,$12::int8,$13::int8,ARRAY[ROW($1::uuid,$2::text,$3::int8)::mixer_authz.membership_witness_v1])::mixer_authz.decision_v1 d) z"

    [[id, role, revision, at, rows]] =
      rq(sql, [
        m.lifecycle_id,
        m.role,
        m.revision,
        d.outcome,
        d.principal_id,
        d.binding_id,
        d.family_id,
        Decimal.new(d.decision_at),
        d.profile_revision,
        d.principal_revision,
        d.family_revision,
        d.organization_revision,
        d.project_revision
      ]).rows

    assert [id, role, revision] == [m.lifecycle_id, m.role, m.revision]
    assert Decimal.equal?(at, Decimal.new(d.decision_at))
    assert rows == [{id, role, revision}]
    # Actual driver decodes composite arrays as tuples, but product path uses strict
    # flattened fields to avoid schema-dependent custom driver type registration.
    observe(:six_composites, %{
      witness_tuple_decoded: true,
      decision_numeric_exact: true,
      named_types: 6
    })
  end

  def run do
    q("CREATE SCHEMA driver_fixture")
    q("CREATE TABLE driver_fixture.effects(invocation text NOT NULL)")
    q("GRANT USAGE ON SCHEMA driver_fixture TO mixer_hosted_runtime")
    q("GRANT INSERT ON driver_fixture.effects TO mixer_hosted_runtime")

    results =
      Enum.map(cases(), fn {name, fun} ->
        start = System.monotonic_time(:millisecond)

        result =
          try do
            fun.()
            cleaned()
            %{name: name, passed: true}
          rescue
            e -> %{name: name, passed: false, error: Exception.format(:error, e, __STACKTRACE__)}
          catch
            kind, value -> %{name: name, passed: false, error: inspect({kind, value})}
          end

        Map.put(result, :elapsed_ms, System.monotonic_time(:millisecond) - start)
        |> tap(fn r -> IO.puts(Jason.encode!(r)) end)
      end)

    evidence = Agent.get(DriverEvidence, & &1)
    out = System.fetch_env!("DRIVER_OUT")

    File.write!(
      Path.join(out, "driver-tests.json"),
      Jason.encode!(
        %{
          results: results,
          passed: Enum.count(results, & &1.passed),
          total: length(results),
          observations: evidence.observations
        }, pretty: true)
    )

    File.write!(
      Path.join(out, "driver-queries.json"),
      Jason.encode!(Enum.reverse(evidence.queries), pretty: true)
    )

    if Enum.any?(results, &(!&1.passed)), do: System.halt(1)
  end
end

DriverTests.run()
Supervisor.stop(repo)
GenServer.stop(owner)
