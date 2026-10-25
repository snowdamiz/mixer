defmodule MixerAuthzIndependent.Admin do
  use Ecto.Repo, otp_app: :mixer_authz_independent, adapter: Ecto.Adapters.Postgres
end

defmodule MixerAuthzIndependent.Migrator do
  use Ecto.Repo, otp_app: :mixer_authz_independent, adapter: Ecto.Adapters.Postgres
end

defmodule MixerAuthzIndependent.Runtime do
  use Ecto.Repo, otp_app: :mixer_authz_independent, adapter: Ecto.Adapters.Postgres
end

defmodule MixerAuthzIndependent.Other do
  use Ecto.Repo, otp_app: :mixer_authz_independent, adapter: Ecto.Adapters.Postgres
end

defmodule MixerAuthzIndependent.Review do
  use ExUnit.Case, async: false
  alias MixerAuthzIndependent.{Admin, Migrator, Runtime, Other}
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.{Scope, Policy}
  alias MixerHosted.Authorization.Transaction.{Context, Snapshot}
  alias MixerHosted.Identity.VerifiedIdentity

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @locks ~w(profiles principals families credentials organization_heads project_heads)
  @key {Context, :active}
  @settings ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker)

  defp sql(s, p \\ []), do: Ecto.Adapters.SQL.query!(Admin, s, p, log: false)
  defp rt(s, p \\ []), do: Ecto.Adapters.SQL.query!(Runtime, s, p, log: false)
  defp now, do: System.system_time(:second)

  defp target,
    do: %Scope{
      organization_id: "review-org",
      project_id: "review-project",
      application_id: "review-app",
      environment_id: "review-env"
    }

  defp identity(attrs \\ %{}),
    do:
      struct!(
        VerifiedIdentity,
        Map.merge(
          %{
            profile_id: "review-profile",
            profile_version: 2,
            issuer: "https://independent.invalid",
            subject: "exact-subject",
            client_id: "independent-client",
            credential_ref: "review-token",
            issued_at: now() - 60,
            expires_at: now() + 600,
            identity_class: :human,
            scopes: ~w(mixer.artifact.read mixer.artifact.upload mixer.audit.read)
          },
          attrs
        )
      )

  defp run(
         cb \\ fn _ -> {:ok, :accepted} end,
         i \\ identity(),
         action \\ "artifact.read",
         t \\ target(),
         repo \\ Runtime
       ),
       do: Authorization.with_authorized_transaction(i, action, t, cb, repo)

  defp write, do: rt("INSERT INTO public.review_effects(value) VALUES ('written')")
  defp count, do: sql("SELECT count(*) FROM public.review_effects").rows |> hd() |> hd()

  defp swallowed(fun) do
    try do
      fun.()
    rescue
      _ -> :caught
    catch
      _, _ -> :caught
    end
  end

  defp wait_second(second) do
    if now() < second,
      do:
        (
          Process.sleep(10)
          wait_second(second)
        ),
      else: :ok
  end

  defp near_boundary do
    ms = System.system_time(:millisecond)
    Process.sleep(Integer.mod(780 - Integer.mod(ms, 1000), 1000))
  end

  defp wait_for_lock(deadline) do
    [[waiting]] =
      sql(
        "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE usename='review_runtime' AND wait_event_type='Lock')"
      ).rows

    if waiting,
      do: :ok,
      else:
        if(System.monotonic_time(:millisecond) < deadline,
          do:
            (
              Process.sleep(5)
              wait_for_lock(deadline)
            ),
          else: flunk("no actual PostgreSQL lock wait observed")
        )
  end

  setup_all do
    opts = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_AUTHZ_REVIEW_PORT")),
      database: "authz_review",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, opts ++ [username: "review_admin", pool_size: 3]})

    start_supervised!(
      {Migrator,
       opts ++
         [
           username: "review_admin",
           pool_size: 2,
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE review_owner", []) end
         ]}
    )

    start_supervised!({Runtime, opts ++ [username: "review_runtime", pool_size: 1]})
    start_supervised!({Other, opts ++ [username: "review_runtime", pool_size: 1]})

    assert :ok =
             Ecto.Migrator.up(
               Migrator,
               20_261_025_000_003,
               MixerHosted.Repo.Migrations.AddCustomerAuthorization,
               log: false
             )

    assert :ok =
             Ecto.Migrator.up(
               Migrator,
               20_261_025_000_004,
               MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
               log: false
             )

    for t <- @tables, do: sql("GRANT SELECT ON public.mixer_authz_#{t} TO review_runtime")

    for t <- @locks,
        do: sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{t}() TO review_runtime")

    sql("CREATE TABLE public.review_effects(value text NOT NULL)")
    sql("GRANT SELECT,INSERT ON public.review_effects TO review_runtime")
    :ok
  end

  setup do
    sql("TRUNCATE " <> Enum.map_join(@tables, ",", &"public.mixer_authz_#{&1}") <> " CASCADE")
    sql("TRUNCATE public.review_effects")

    sql(
      "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('review-profile',2,'https://independent.invalid','independent-client','human',true)"
    )

    sql("INSERT INTO public.mixer_authz_principals VALUES ('review-person','human',true,0,11)")

    sql(
      "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('review-profile',2,'exact-subject','human','review-person',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_families VALUES ('review-family','review-profile',2,'review-person',true,1,NULL,13)"
    )

    sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('review-profile',2,'review-token','review-person','review-family',true,2,NULL,17)"
    )

    sql("INSERT INTO public.mixer_authz_organizations VALUES ('review-org',true)")
    sql("INSERT INTO public.mixer_authz_projects VALUES ('review-org','review-project',true)")

    sql(
      "INSERT INTO public.mixer_authz_applications VALUES ('review-org','review-project','review-app',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_environments VALUES ('review-org','review-project','review-app','review-env',true)"
    )

    sql("INSERT INTO public.mixer_authz_organization_heads VALUES ('review-org',19)")
    sql("INSERT INTO public.mixer_authz_project_heads VALUES ('review-org','review-project',23)")

    sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('review-member','review-person','review-org','review-project','exact_project','developer',true,3,NULL,29)"
    )

    on_exit(fn ->
      refute Context.active?()

      assert [[""]] =
               rt("SELECT coalesce(current_setting('mixer.authz.transaction_marker',true),'')").rows

      assert [[0]] = rt("SELECT count(*) FROM public.mixer_authz_credentials").rows
    end)

    :ok
  end

  test "positive real SQL control preserves independently chosen raw provenance values" do
    sql("UPDATE public.mixer_authz_profiles SET state_revision=31")
    sql("UPDATE public.mixer_authz_bindings SET revision=37")
    i = identity()

    assert {:ok, s} =
             run(
               fn c ->
                 assert c.owner == self()
                 assert Runtime.in_transaction?()
                 assert [_, _, "review_runtime", "review_runtime" | _] = c.connection

                 fresh =
                   Context.effect!(c, Runtime, "artifact.read", target(), fn fresh ->
                     write()
                     fresh
                   end)

                 assert fresh.request_id == c.snapshot.request_id
                 {:ok, fresh}
               end,
               i
             )

    assert count() == 1

    assert {s.profile.state_revision, s.binding.revision, s.principal.revision, s.family.revision,
            s.credential.revision, s.organization_head.revision, s.project_head.revision,
            hd(s.memberships).revision} == {31, 37, 11, 13, 17, 19, 23, 29}

    assert {s.family.not_before, s.credential.not_before, hd(s.memberships).not_before} ==
             {1, 2, 3}

    assert s.identity.issued_at == i.issued_at and s.identity.expires_at == i.expires_at
    digest = :crypto.hash(:sha256, i.subject) |> Base.encode16(case: :lower)
    assert s.identity.subject_digest == digest and s.binding.subject_digest == digest
    refute Map.has_key?(s.identity, :subject)
  end

  test "every bounded failure malformed response and callback nonlocal return rolls back real SQL" do
    callbacks = [
      fn _ -> {:error, :conflict} end,
      fn _ -> {:error, :storage_unavailable} end,
      fn _ -> {:error, String.duplicate("private", 1000)} end,
      fn _ -> nil end,
      fn _ -> {:ok, :v, :extra} end,
      fn _ -> raise "review failure" end,
      fn _ -> throw(:review_throw) end,
      fn _ -> exit(:review_exit) end
    ]

    for cb <- callbacks do
      assert {:error, _} =
               run(fn c ->
                 write()
                 cb.(c)
               end)

      assert count() == 0
      refute Context.active?()
      assert {:ok, :accepted} = run()
    end
  end

  test "escaped local effect failures stay latched even when the outer callback rescues them" do
    observations =
      for {label, failure} <- [
            {:raise, fn -> raise "local effect failure" end},
            {:throw, fn -> throw(:local_effect_failure) end},
            {:exit, fn -> exit(:local_effect_failure) end},
            {:bounded_error, fn -> {:error, :conflict} end},
            {:unknown_error, fn -> {:error, :unbounded_secret_reason} end}
          ] do
        result =
          run(fn c ->
            swallowed(fn ->
              Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                write()
                failure.()
              end)
            end)

            {:ok, :rescued}
          end)

        persisted = count()
        sql("TRUNCATE public.review_effects")
        {label, result, persisted}
      end

    assert observations ==
             Enum.map(
               ~w(raise throw exit bounded_error unknown_error)a,
               &{&1, {:error, :authorization_unavailable}, 0}
             )

    assert {:error, :conflict} =
             run(fn c ->
               Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                 write()
                 {:error, :conflict}
               end)

               {:ok, :unexpected}
             end)

    assert count() == 0
  end

  test "full context changes and pure decisions fail before effect and cannot be rescued into commit" do
    for field <- Map.keys(Map.from_struct(struct(Context))) ++ [:extra] do
      assert {:error, :authorization_unavailable} =
               run(fn c ->
                 write()
                 bad = Map.put(c, field, :independent_forgery)

                 swallowed(fn ->
                   Context.effect!(bad, Runtime, "artifact.read", target(), fn _ ->
                     flunk("forged effect")
                   end)
                 end)

                 {:ok, :rescued}
               end)

      assert count() == 0
    end

    assert {:error, :authorization_unavailable} =
             run(fn _ ->
               write()

               swallowed(fn ->
                 Context.effect!(
                   struct(Policy.Decision),
                   Runtime,
                   "artifact.read",
                   target(),
                   fn _ -> flunk("pure decision effect") end
                 )
               end)

               {:ok, :rescued}
             end)

    assert count() == 0
  end

  test "every transaction-local authorization setting participates in live binding" do
    for setting <- @settings do
      assert {:error, :authorization_unavailable} =
               run(fn c ->
                 write()

                 rt("SELECT set_config($1,'independent-mutation',true)", [
                   "mixer.authz." <> setting
                 ])

                 swallowed(fn -> Context.checkpoint!(c, Runtime, "artifact.read", target()) end)
                 {:ok, :rescued}
               end)

      assert count() == 0
    end
  end

  test "real current role switch and dynamic repository switch invalidate authority" do
    assert {:error, :authorization_unavailable} =
             run(fn c ->
               write()
               rt("SET LOCAL ROLE review_alternate")

               Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                 flunk("role switched effect")
               end)

               {:ok, :unexpected}
             end)

    assert count() == 0

    assert {:error, :authorization_unavailable} =
             run(fn c ->
               write()
               old = Runtime.put_dynamic_repo(Other)

               try do
                 swallowed(fn -> Context.checkpoint!(c, Runtime, "artifact.read", target()) end)
               after
                 Runtime.put_dynamic_repo(old)
               end

               {:ok, :rescued}
             end)

    assert count() == 0
  end

  test "foreign process cannot borrow context and stale contexts cannot authorize later transactions" do
    assert {:ok, old} =
             run(fn c ->
               result =
                 Task.async(fn ->
                   swallowed(fn ->
                     Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                       flunk("child effect")
                     end)
                   end)
                 end)
                 |> Task.await()

               assert result == :caught
               {:ok, c}
             end)

    assert_raise Context.Invalid, fn ->
      Context.checkpoint!(old, Runtime, "artifact.read", target())
    end

    assert {:error, :authorization_unavailable} =
             run(fn _ ->
               write()
               Context.checkpoint!(old, Runtime, "artifact.read", target())
               {:ok, :unexpected}
             end)

    assert count() == 0
    refute Context.active?()
    assert {:ok, :accepted} = run()
  end

  test "manual transaction replacement with restored GUCs still fails the actual xid binding" do
    assert {:error, :authorization_unavailable} =
             run(fn c ->
               [_backend, old_xid, _current, _session | values] = c.connection
               rt("COMMIT")
               rt("BEGIN")

               for {key, value} <- Enum.zip(@settings, values),
                   do: rt("SELECT set_config($1,$2,true)", ["mixer.authz." <> key, value])

               assert [[new_xid]] = rt("SELECT pg_current_xact_id()::text").rows
               assert new_xid != old_xid

               Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                 flunk("replacement transaction effect")
               end)

               {:ok, :unexpected}
             end)

    assert count() == 0
  end

  test "outer and recursive transaction requests reject without disrupting a valid outer callback" do
    assert {:ok, {:error, :authorization_unavailable}} =
             Runtime.transaction(fn -> run(fn _ -> flunk("nested callback") end) end)

    assert {:ok, :outer} =
             run(fn _ ->
               assert {:error, :authorization_unavailable} =
                        run(fn _ -> flunk("recursive callback") end)

               write()
               {:ok, :outer}
             end)

    assert count() == 1
  end

  test "strict role ceiling and token scope intersection are observed against SQL memberships" do
    for role <- ~w(owner administrator developer release_manager billing_manager viewer),
        action <- ~w(artifact.read artifact.upload audit.read) do
      sql("UPDATE public.mixer_authz_memberships SET role=$1", [role])

      t =
        if action == "audit.read",
          do: %{target() | application_id: nil, environment_id: nil},
          else: target()

      allowed =
        if action == "artifact.upload",
          do: role in ~w(owner administrator developer),
          else: role != "billing_manager"

      result = run(fn _ -> {:ok, :allowed} end, identity(), action, t)
      assert result == if(allowed, do: {:ok, :allowed}, else: {:error, :permission_denied})
    end

    assert {:error, :permission_denied} =
             run(fn _ -> flunk("missing scope callback") end, identity(%{scopes: []}))

    assert {:error, :invalid_request} =
             run(fn _ -> flunk("wrong target callback") end, identity(), "audit.read")

    assert {:error, :permission_denied} =
             run(
               fn _ -> flunk("service identity callback") end,
               identity(%{identity_class: :service})
             )
  end

  test "profile binding family and credential raw windows or identity link changes fail closed" do
    for statement <- [
          "UPDATE public.mixer_authz_profiles SET active=false",
          "UPDATE public.mixer_authz_bindings SET active=false",
          "UPDATE public.mixer_authz_families SET active=false",
          "UPDATE public.mixer_authz_credentials SET active=false"
        ] do
      sql(statement)
      assert {:error, _} = run(fn _ -> flunk("inactive state callback") end)
      sql(String.replace(statement, "false", "true"))
    end

    for table <- ~w(families credentials) do
      sql("UPDATE public.mixer_authz_#{table} SET not_before=$1", [now() - 5])
      assert {:error, :unauthenticated} = run(fn _ -> flunk("old token callback") end)
      sql("UPDATE public.mixer_authz_#{table} SET not_before=0,expires_at=$1", [now()])
      assert {:error, :unauthenticated} = run(fn _ -> flunk("expired window callback") end)
      sql("UPDATE public.mixer_authz_#{table} SET expires_at=NULL")
    end

    for attrs <- [
          %{subject: "other"},
          %{credential_ref: "other"},
          %{profile_version: 3},
          %{client_id: "other"},
          %{issuer: "https://other.invalid"}
        ] do
      assert {:error, _} = run(fn _ -> flunk("identity mismatch callback") end, identity(attrs))
    end
  end

  test "locked revisions remain stable while a concurrent legitimate writer waits" do
    parent = self()

    assert {:ok, :stable} =
             run(fn c ->
               task =
                 Task.async(fn ->
                   send(parent, {:writer_started, self()})
                   sql("UPDATE public.mixer_authz_profiles SET state_revision=state_revision+1")
                 end)

               assert_receive {:writer_started, _}
               Process.sleep(50)

               assert [[true]] =
                        sql(
                          "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE usename='review_admin' AND wait_event_type='Lock')"
                        ).rows

               assert c.snapshot.profile.state_revision == 1

               assert Context.checkpoint!(c, Runtime, "artifact.read", target()).profile.state_revision ==
                        1

               send(parent, {:waiting_writer, task})
               {:ok, :stable}
             end)

    assert_receive {:waiting_writer, task}
    Task.await(task)
    assert {:ok, 2} = run(fn c -> {:ok, c.snapshot.profile.state_revision} end)
  end

  test "expired selected grant disappears and surviving complete membership is fresh before effect" do
    expiry = now() + 1
    sql("UPDATE public.mixer_authz_memberships SET expires_at=$1", [expiry])

    sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('survivor','review-person','review-org',NULL,'all_projects','viewer',true,0,NULL,41)"
    )

    assert {:ok, :survived} =
             run(fn c ->
               assert length(c.snapshot.memberships) == 2
               wait_second(expiry)

               fresh =
                 Context.effect!(c, Runtime, "artifact.read", target(), fn s ->
                   write()
                   s
                 end)

               assert Enum.map(fresh.memberships, &{&1.id, &1.revision, &1.role}) == [
                        {"survivor", 41, "viewer"}
                      ]

               assert length(c.snapshot.memberships) == 2
               {:ok, :survived}
             end)

    assert count() == 1
  end

  test "token expiry after actual row lock wait prevents callback after postlock refresh" do
    parent = self()

    locker =
      Task.async(fn ->
        Admin.transaction(fn ->
          sql("SELECT 1 FROM public.mixer_authz_profiles FOR UPDATE")
          send(parent, {:locked, self()})

          receive do
            :release -> :ok
          after
            3000 -> flunk("locker timeout")
          end
        end)
      end)

    assert_receive {:locked, locker_pid}
    near_boundary()
    i = identity(%{expires_at: now() + 1})
    task = Task.async(fn -> run(fn _ -> flunk("expired postlock callback") end, i) end)
    wait_for_lock(System.monotonic_time(:millisecond) + 200)
    wait_second(i.expires_at)
    send(locker_pid, :release)
    assert {:ok, :ok} = Task.await(locker)
    assert {:error, :unauthenticated} = Task.await(task)
    assert count() == 0
  end

  test "token expiry at preeffect prevents callback and final expiry rolls back earlier SQL" do
    i = identity(%{expires_at: now() + 1})

    assert {:error, :unauthenticated} =
             run(
               fn c ->
                 wait_second(i.expires_at)

                 Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                   flunk("expired effect")
                 end)

                 {:ok, :unexpected}
               end,
               i
             )

    i = identity(%{expires_at: now() + 1})

    assert {:error, :unauthenticated} =
             run(
               fn _ ->
                 write()
                 wait_second(i.expires_at)
                 {:ok, :would_commit}
               end,
               i
             )

    assert count() == 0
  end

  test "monotonic deadline applies to transaction while token remains live" do
    started = System.monotonic_time(:millisecond)

    assert {:error, :authorization_unavailable} =
             run(fn c ->
               write()
               Process.sleep(max(0, c.deadline - System.monotonic_time(:millisecond) + 20))
               {:ok, :would_commit}
             end)

    assert System.monotonic_time(:millisecond) - started >= 5000
    assert count() == 0
  end

  test "controlled previous wall reading regression fails closed and remains latched after catch" do
    assert {:error, :authorization_unavailable} =
             run(fn c ->
               write()
               state = Process.get(@key)
               Process.put(@key, %{state | last_time: now() + 1})

               swallowed(fn ->
                 Context.effect!(c, Runtime, "artifact.read", target(), fn _ ->
                   flunk("regressed effect")
                 end)
               end)

               {:ok, :rescued}
             end)

    assert count() == 0
  end

  test "snapshot strict projections reject raw revisions windows roles linkage and nested extensions" do
    assert {:ok, :checked} =
             run(fn c ->
               state = Process.get(@key)

               assert {:ok, d} =
                        Policy.evaluate(
                          c.identity,
                          c.action,
                          c.target,
                          state.evidence,
                          c.snapshot.checked_at
                        )

               s = c.snapshot
               assert Snapshot.valid?(s, c.identity, d)

               bad = [
                 Map.put(s, :extra, true),
                 Map.delete(s, :family),
                 put_in(s, [:profile, :state_revision], 0),
                 put_in(s, [:binding, :revision], -1),
                 put_in(s, [:binding, :subject_digest], String.duplicate("0", 64)),
                 put_in(s, [:family, :id], "unlinked"),
                 put_in(s, [:family, :profile_version], 99),
                 put_in(s, [:family, :not_before], c.identity.issued_at + 1),
                 put_in(s, [:credential, :expires_at], s.checked_at),
                 put_in(s, [:principal, :revision], 12),
                 put_in(s, [:organization_head, :revision], 20),
                 put_in(s, [:project_head, :revision], 24),
                 put_in(s, [:identity, :issued_at], 0),
                 put_in(s, [:identity, :subject], "secret"),
                 Map.put(s, :memberships, [Map.put(hd(s.memberships), :role, "unknown")]),
                 Map.put(s, :memberships, [Map.put(hd(s.memberships), :revision, 0)]),
                 Map.put(s, :memberships, [Map.put(hd(s.memberships), :extra, true)]),
                 Map.put(s, :memberships, List.duplicate(hd(s.memberships), 65))
               ]

               for b <- bad, do: refute(Snapshot.valid?(b, c.identity, d))
               {:ok, :checked}
             end)
  end

  test "revision migration applies baseline one bounds and changes no raw existing state" do
    assert [[1, true]] = sql("SELECT state_revision,active FROM public.mixer_authz_profiles").rows
    assert [[1, true]] = sql("SELECT revision,active FROM public.mixer_authz_bindings").rows

    for {table, column} <- [{"profiles", "state_revision"}, {"bindings", "revision"}],
        v <- [0, -1, 9_007_199_254_740_992] do
      assert_raise Postgrex.Error, fn ->
        sql("UPDATE public.mixer_authz_#{table} SET #{column}=$1", [v])
      end
    end

    assert {:ok, :accepted} = run()
  end

  test "unsafe runtime grants or privileged role reachability reject before callback" do
    for {grant, revoke} <- [
          {"GRANT UPDATE(active) ON public.mixer_authz_principals TO review_runtime",
           "REVOKE UPDATE(active) ON public.mixer_authz_principals FROM review_runtime"},
          {"GRANT review_owner TO review_runtime", "REVOKE review_owner FROM review_runtime"},
          {"GRANT pg_read_server_files TO review_alternate WITH INHERIT FALSE, SET TRUE",
           "REVOKE pg_read_server_files FROM review_alternate"}
        ] do
      sql(grant)

      try do
        assert {:error, :authorization_unavailable} =
                 run(fn _ -> flunk("unsafe runtime callback") end)
      after
        sql(revoke)
      end
    end

    assert {:error, :authorization_unavailable} =
             run(
               fn _ -> flunk("admin callback") end,
               identity(),
               "artifact.read",
               target(),
               Admin
             )

    assert {:ok, :accepted} = run()
  end
end
