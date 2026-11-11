defmodule R1026.Admin do
  use Ecto.Repo, otp_app: :r1026, adapter: Ecto.Adapters.Postgres
end

defmodule R1026.Migration do
  use Ecto.Repo, otp_app: :r1026, adapter: Ecto.Adapters.Postgres
end

defmodule R1026.Runtime do
  use Ecto.Repo, otp_app: :r1026, adapter: Ecto.Adapters.Postgres
end

defmodule R1026.Router do
  use Plug.Router
  plug(:match)
  plug(:dispatch)

  get "/v3/orgs/:organization_id/projects/:project_id/apps/:application_id/builds/:build_id/:platform" do
    MixerHostedWeb.CustomerBuildController.call(conn, [])
  end

  match _ do
    Plug.Conn.send_resp(conn, 404, "")
  end
end

defmodule R1026.CustomerBuildReadTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Builds.{Journal, Lifecycle}
  alias MixerHosted.CustomerBuilds.{Selection, Snapshot}
  alias MixerHosted.Authorization
  alias MixerHosted.Identity.VerifiedIdentity
  alias R1026.{Admin, Migration, Runtime}
  import Plug.Test
  import Plug.Conn

  defp sql(query, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, query, params, log: false)
  defp digest(n), do: String.duplicate(n, 64)

  defp selection do
    %{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "fieldlog",
      build_id: "build-a",
      platform: "ios",
      source_sha256: digest("a"),
      toolchain_lock_sha256: digest("b"),
      build_definition_sha256: digest("c")
    }
  end

  defp identity(changes \\ %{}) do
    now = System.system_time(:second)

    struct!(
      VerifiedIdentity,
      Map.merge(
        %{
          profile_id: "profile",
          profile_version: 1,
          issuer: "https: //issuer.example",
          subject: "subject",
          client_id: "client",
          credential_ref: "token",
          issued_at: now - 20,
          expires_at: now + 600,
          identity_class: :human,
          scopes: ~w(mixer.artifact.read mixer.audit.read mixer.workspace.read mixer.build.read)
        },
        changes
      )
    )
  end

  defp initial do
    s = selection()

    spec =
      s
      |> Map.take([:organization_id, :project_id, :application_id, :build_id])
      |> Map.merge(%{
        platform: :ios,
        source: %{kind: :revision, sha256: s.source_sha256, reference: "immutable-test-revision"},
        toolchain_lock_sha256: s.toolchain_lock_sha256,
        build_definition_sha256: s.build_definition_sha256
      })

    {:ok, journal, build} =
      Journal.new(spec, %{max_attempts: 2, timeout_ms: 100, retry_backoff_ms: 0}, "request-a", 0)

    {journal, build}
  end

  defp store({journal, _build}) do
    s = selection()
    sql("DELETE FROM public.mixer_builds")

    {:ok, initial_build} = Journal.restore(elem(initial(), 0))

    multi =
      MixerHosted.Builds.Storage.create_multi(
        Ecto.Multi.new(),
        :build,
        initial_build.spec,
        %{max_attempts: 2, timeout_ms: 100, retry_backoff_ms: 0},
        "request-a",
        0,
        &MixerHosted.Builds.Coordinator.new/1
      )

    {:ok, _} = Admin.transaction(multi)

    if journal != elem(initial(), 0) do
      sql("UPDATE public.mixer_builds SET journal=$1,revision=$2", [
        journal,
        length(journal["events"])
      ])
    end

    [row] =
      sql(
        "SELECT organization_id,project_id,application_id,build_id,platform,request_key,revision,journal FROM public.mixer_builds WHERE organization_id=$1 AND project_id=$2 AND application_id=$3 AND build_id=$4 AND platform=$5",
        [s.organization_id, s.project_id, s.application_id, s.build_id, s.platform]
      ).rows

    Enum.zip(
      ~w(organization_id project_id application_id build_id platform request_key revision journal)a,
      row
    )
    |> Map.new()
  end

  defp append({j, _b}, id, event, now) do
    {:ok, j, b, :applied} = Journal.append(j, id, event, now)
    {j, b}
  end

  defp request(s \\ selection(), query \\ nil, body \\ "") do
    {:ok, s} = Selection.new(s)

    query =
      query ||
        URI.encode_query(%{
          "source_sha256" => s.source_sha256,
          "toolchain_lock_sha256" => s.toolchain_lock_sha256,
          "build_definition_sha256" => s.build_definition_sha256
        })

    conn(:get, MixerHostedWeb.Plugs.CustomerBuildRequest.path(s) <> "?" <> query, body)
    |> assign(:verified_identity, identity())
  end

  setup_all do
    for app <- [:phoenix, :ecto_sql, :postgrex, :jason, :oban],
        do: Application.ensure_all_started(app)

    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("R1026_PG_PORT")),
      database: "mixer_customer_build_read",
      ssl: false,
      log: false,
      pool_size: 1
    ]

    start_supervised!({Admin, settings ++ [username: "r1026_admin"]})

    start_supervised!(
      {Migration,
       Keyword.put(settings, :pool_size, 2) ++
         [
           username: "r1026_admin",
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE r1026_owner", []) end
         ]}
    )

    start_supervised!({Runtime, settings ++ [username: "r1026_runtime"]})

    for {version, module, file} <- [
          {20_261_025_000_000, MixerHosted.Repo.Migrations.AddBuildJournals,
           "20261025000000_add_build_journals.exs"},
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization,
           "20261025000003_add_customer_authorization.exs"},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
           "20261025000004_add_authorization_state_revisions.exs"},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage,
           "20261025000005_add_customer_artifact_storage.exs"}
        ] do
      unless Code.ensure_loaded?(module),
        do: Code.require_file(Path.join("priv/repo/migrations", file))

      :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    :ok = Ecto.Migrator.up(Migration, 1, R1026.ObanMigration, log: false)
    sql(MixerHosted.CustomerBuilds.Schema.ddl())

    sql(
      "ALTER FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) OWNER TO r1026_owner"
    )

    sql(
      "REVOKE ALL ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) FROM PUBLIC"
    )

    sql(
      "GRANT EXECUTE ON FUNCTION public.mixer_customer_build_read_v1(text,text,text,text,text) TO r1026_runtime"
    )

    # Exact ordinary customer fixture grants: no build privilege, new action or RLS policy.
    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: sql("GRANT SELECT ON public.mixer_authz_#{table} TO r1026_runtime")

    for table <- ~w(profiles principals families credentials organization_heads project_heads),
        do: sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO r1026_runtime")

    for table <- ~w(artifacts audit_events idempotency),
        do: sql("GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO r1026_runtime")

    sql(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO r1026_runtime"
    )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          sql(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{MixerHosted.CustomerArtifacts.Schema.signatures()[name]}) TO r1026_runtime"
          )

    # Unchanged seed statements from the ordinary customer authorization fixture.
    for q <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https: //issuer.example','client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,2)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,'subject','human','person',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,3)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'token','person','family',true,0,NULL,4)",
          "INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true)",
          "INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true)",
          "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','fieldlog',true)",
          "INSERT INTO public.mixer_authz_organization_heads VALUES ('org-a',5)",
          "INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',6)",
          "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org-a','project-a','exact_project','developer',true,0,NULL,7)"
        ],
        do: sql(q)

    :ok
  end

  setup context do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("R1026_PG_PORT")),
      database: "mixer_customer_build_read",
      ssl: false,
      log: false,
      pool_size: 1
    ]

    saved =
      [{:mixer_hosted, MixerHosted.Repo}, {:r1026, Admin}]
      |> Enum.map(fn {app, key} -> {app, key, Application.fetch_env(app, key)} end)

    on_exit(fn ->
      Enum.each(saved, fn
        {app, key, {:ok, value}} -> Application.put_env(app, key, value)
        {app, key, :error} -> Application.delete_env(app, key)
      end)
    end)

    Application.put_env(:mixer_hosted, MixerHosted.Repo, settings ++ [username: "r1026_runtime"])
    Application.put_env(:r1026, Admin, settings ++ [username: "r1026_admin"])
    start_supervised!({MixerHosted.Repo, settings ++ [username: "r1026_runtime"]})
    {:ok, _} = Application.ensure_all_started(:oban)
    start_supervised!({Oban, repo: Admin, queues: false, plugins: false, testing: :manual})
    handler = {__MODULE__, self()}

    :ok =
      :telemetry.attach_many(
        handler,
        [[:mixer_hosted, :customer_builds, :transaction], [:mixer_hosted, :repo, :query]],
        fn event, _, meta, name ->
          active = Process.get({MixerHosted.CustomerBuilds.Context, :active})

          if event == [:mixer_hosted, :customer_builds, :transaction] do
            result =
              case meta.result do
                {:ok, %Postgrex.Result{command: command, connection_id: backend}} ->
                  %{command: command, backend: backend}

                _ ->
                  %{command: "unacknowledged"}
              end

            record =
              Map.merge(result, %{
                test: name,
                query: meta.query,
                caller: inspect(self()),
                deadline: active && active.deadline,
                marker: active && active.marker,
                monotonic_ms: System.monotonic_time(:millisecond)
              })

            File.write!(
              System.fetch_env!("R1072_TRANSACTION_EVIDENCE"),
              Jason.encode!(record) <> "\n",
              [:append]
            )
          end

          if active && event == [:mixer_hosted, :repo, :query] && meta.repo == MixerHosted.Repo &&
               meta.query == "SELECT pg_catalog.set_config($1, $2, true)" &&
               meta.params == ["mixer.authz.phase", "build_read"] do
            keys =
              ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase directory_mode)

            fields = Enum.map_join(keys, ",", &"current_setting('mixer.authz.#{&1}', true)")

            [[backend, xid, user, session | values]] =
              Ecto.Adapters.SQL.query!(
                MixerHosted.Repo,
                "SELECT pg_backend_pid(),pg_current_xact_id()::text,current_user::text,session_user::text," <>
                  fields,
                [],
                log: false,
                telemetry_event: nil,
                timeout: 5_000,
                queue: false
              ).rows

            record = %{
              type: "binding",
              test: name,
              backend: backend,
              xid: xid,
              user: user,
              session: session,
              caller: inspect(self()),
              deadline: active.deadline,
              marker: active.marker,
              monotonic_ms: System.monotonic_time(:millisecond),
              settings: Map.new(Enum.zip(keys, values))
            }

            File.write!(
              System.fetch_env!("R1072_TRANSACTION_EVIDENCE"),
              Jason.encode!(record) <> "\n",
              [:append]
            )
          end
        end,
        Atom.to_string(context.test)
      )

    on_exit(fn -> :telemetry.detach(handler) end)
    store(initial())
    :ok
  end

  test "unchanged current authorization transaction works for admitted audit, but cannot admit build.read" do
    target = %{organization_id: "org-a", project_id: "project-a"}

    assert {:ok, %{action: "audit.read"}} =
             Authorization.with_authorized_transaction(
               identity(),
               "audit.read",
               target,
               fn ctx -> {:ok, %{action: ctx.action}} end,
               Runtime
             )

    parent = self()

    assert {:error, :permission_denied} =
             Authorization.with_authorized_transaction(
               identity(),
               "build.read",
               Map.put(target, :application_id, "fieldlog"),
               fn _ ->
                 send(parent, :forbidden_callback)
                 {:ok, :leak}
               end,
               Runtime
             )

    refute_received :forbidden_callback

    assert {:ok, %{state: "queued"}} =
             MixerHosted.CustomerBuilds.read(identity(), selection())

    assert {:error, :unauthenticated} =
             MixerHosted.CustomerBuilds.read(identity(%{expires_at: 1}), selection())
  end

  test "restricted customer SQL cannot read named stored build or borrow artifact grant" do
    row = store(initial())
    assert row.revision == 0

    [[false, false, false, false, false, false]] =
      Ecto.Adapters.SQL.query!(
        Runtime,
        "SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,pg_catalog.has_table_privilege(current_user,'public.mixer_builds','SELECT') FROM pg_catalog.pg_roles WHERE rolname=current_user",
        []
      ).rows

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(
               Runtime,
               "SELECT journal FROM public.mixer_builds WHERE organization_id=$1 AND project_id=$2 AND application_id=$3 AND build_id=$4 AND platform=$5",
               ["org-a", "project-a", "fieldlog", "build-a", "ios"]
             )

    assert [[false, false]] =
             sql(
               "SELECT relrowsecurity,relforcerowsecurity FROM pg_catalog.pg_class WHERE oid='public.mixer_builds'::regclass"
             ).rows

    assert [[0]] =
             sql(
               "SELECT count(*) FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname='mixer_customer_build_read'"
             ).rows

    File.write!(
      System.fetch_env!("R1026_EVIDENCE"),
      Jason.encode!(%{
        named_build: "build-a",
        runtime: "r1026_runtime",
        sqlstate: "42501",
        build_select: false,
        build_rls: false,
        build_read_action: "permission_denied",
        admitted_control: "audit.read"
      }) <> "\n"
    )
  end

  test "actual stored journal projection preserves queued and all lifecycle states without aggregate success" do
    queued = initial()
    {_, b} = queued
    {:ok, ref} = Lifecycle.worker_ref(b)
    running = append(queued, "start", %{type: :start, ref: ref}, 1)
    cancelling = append(running, "cancel", %{type: :cancel, reason: "test"}, 2)
    reconciling = append(running, "expire", %{type: :expire, ref: ref}, 101)

    failure = %{
      outcome: :failed,
      class: :compiler,
      code: :compiler_error,
      diagnostic_sha256: digest("d")
    }

    failed = append(running, "failed", %{type: :completed, ref: ref, result: failure}, 2)

    cancelled =
      append(
        cancelling,
        "stopped",
        %{type: :stopped, ref: ref, diagnostic_sha256: digest("d")},
        3
      )

    timed_out = append(reconciling, "late", %{type: :completed, ref: ref, result: failure}, 102)

    kinds =
      ~w(unsigned_native_binary guest_artifact resource_inventory debug_symbols compatibility_report sbom provenance)a

    artifacts =
      Enum.map(kinds, &%Lifecycle.ArtifactRef{kind: &1, sha256: digest("d"), size_bytes: 1})

    succeeded =
      append(
        running,
        "success",
        %{type: :completed, ref: ref, result: %{outcome: :succeeded, artifacts: artifacts}},
        2
      )

    for {pair, state, pending} <- [
          {queued, "queued", false},
          {running, "running", true},
          {cancelling, "cancelling", true},
          {reconciling, "reconciling", true},
          {failed, "failed", false},
          {cancelled, "cancelled", false},
          {timed_out, "timed_out", false},
          {succeeded, "succeeded", false}
        ] do
      row = store(pair)
      assert {:ok, dto} = Snapshot.project(row, selection())
      assert dto.state == state
      assert dto.revision == length(elem(pair, 0)["events"])
      assert dto.workerCompletionPending == pending
      assert dto.attempt == 1 and dto.maxAttempts == 2
      if state in ["failed", "timed_out"], do: assert(dto.failureCode == "compiler_error")
      http = request() |> R1026.Router.call([])
      assert http.status == 200
      assert Jason.decode!(http.resp_body)["build"]["state"] == state
      refute http.resp_body =~ "aggregate"
    end
  end

  test "exact identity, row scope and revision are mandatory for data projection" do
    row = store(initial())

    for key <-
          ~w(organization_id project_id application_id build_id platform source_sha256 toolchain_lock_sha256 build_definition_sha256)a do
      changed =
        if key == :platform,
          do: "android",
          else:
            if(key in [:source_sha256, :toolchain_lock_sha256, :build_definition_sha256],
              do: digest("e"),
              else: "other"
            )

      assert {:error, :storage_unavailable} =
               Snapshot.project(row, Map.put(selection(), key, changed))
    end

    assert {:error, :storage_unavailable} = Snapshot.project(%{row | revision: 1}, selection())

    assert {:error, :storage_unavailable} =
             Snapshot.project(%{row | request_key: "other"}, selection())

    {j, b} = initial()
    {:ok, ref} = Lifecycle.worker_ref(b)
    {j, _} = append({j, b}, "start", %{type: :start, ref: ref}, 1)
    replay = %{j | "events" => j["events"] ++ j["events"]}

    assert {:error, :storage_unavailable} =
             Snapshot.project(%{row | revision: 2, journal: replay}, selection())

    assert {:ok, ^j, _, :duplicate} = Journal.append(j, "start", %{type: :start, ref: ref}, 999)
  end

  test "private Plug boundary rejects malformed inputs and sanitizes unavailable response" do
    good = request() |> R1026.Router.call([])
    assert good.status == 200
    assert Jason.decode!(good.resp_body)["build"]["state"] == "queued"
    assert get_resp_header(good, "cache-control") == ["no-store"]
    assert get_resp_header(good, "retry-after") == []

    bad_query = [
      "",
      "source_sha256=x",
      "source_sha256=#{digest("a")}&source_sha256=#{digest("a")}&build_definition_sha256=#{digest("c")}",
      "source_sha256=#{digest("a")}&toolchain_lock_sha256=#{digest("b")}&repo=Runtime",
      "source_sha256=#{digest("a")}&toolchain_lock_sha256=#{digest("b")}&%62uild_definition_sha256=#{digest("c")}"
    ]

    for q <- bad_query,
        do: assert((request(selection(), q) |> R1026.Router.call([])).status == 400)

    assert (request(selection(), nil, "{}") |> R1026.Router.call([])).status == 400

    for headers <- [
          [{"authorization", "Bearer one"}, {"authorization", "Bearer two"}],
          [{"content-encoding", "gzip"}],
          [{"content-length", "1"}],
          [{"idempotency-key", "write"}]
        ] do
      c = request()
      c = %{c | req_headers: headers ++ c.req_headers}
      assert R1026.Router.call(c, []).status == 400
    end

    missing = request() |> assign(:verified_identity, nil) |> R1026.Router.call([])
    assert missing.status == 401
  end

  test "current revocation boundaries remain enforced by unchanged admitted transaction" do
    for {table, column, key} <- [
          {"principals", "id", "person"},
          {"families", "id", "family"},
          {"credentials", "reference", "token"},
          {"memberships", "id", "member"}
        ] do
      sql(
        "UPDATE public.mixer_authz_#{table} SET active=false,revision=revision+1 WHERE #{column}=$1",
        [key]
      )

      assert {:error, reason} =
               Authorization.with_authorized_transaction(
                 identity(),
                 "audit.read",
                 %{organization_id: "org-a", project_id: "project-a"},
                 fn _ -> {:ok, :forbidden} end,
                 Runtime
               )

      assert reason in [:unauthenticated, :not_found]
      assert (request() |> R1026.Router.call([])).status in [401, 404]

      sql(
        "UPDATE public.mixer_authz_#{table} SET active=true,revision=revision+1 WHERE #{column}=$1",
        [key]
      )
    end

    for {table, revision} <- [{"profiles", "state_revision"}, {"bindings", "revision"}] do
      sql("UPDATE public.mixer_authz_#{table} SET active=false,#{revision}=#{revision}+1")
      assert {:error, reason} = MixerHosted.CustomerBuilds.read(identity(), selection())
      assert reason in [:unauthenticated, :not_found]
      assert (request() |> R1026.Router.call([])).status in [401, 404]
      sql("UPDATE public.mixer_authz_#{table} SET active=true,#{revision}=#{revision}+1")
    end
  end

  test "build purpose accepts each allowed human role, viewer needs no environment, billing alone denied" do
    assert sql("SELECT count(*) FROM public.mixer_authz_environments").rows == [[0]]

    for role <- ~w(owner administrator developer release_manager viewer) do
      sql("UPDATE public.mixer_authz_memberships SET role=$1,revision=revision+1", [role])
      assert {:ok, %{state: "queued"}} = MixerHosted.CustomerBuilds.read(identity(), selection())
    end

    sql("UPDATE public.mixer_authz_memberships SET role='billing_manager',revision=revision+1")
    assert {:error, :not_found} = MixerHosted.CustomerBuilds.read(identity(), selection())
    forged = request() |> put_req_header("x-role", "owner") |> put_req_header("x-tenant", "org-a")
    assert R1026.Router.call(forged, []).status == 404
    sql("UPDATE public.mixer_authz_memberships SET role='developer',revision=revision+1")

    assert {:error, :permission_denied} =
             MixerHosted.CustomerBuilds.read(
               identity(%{scopes: ["mixer.artifact.read"]}),
               selection()
             )

    assert {:error, :unauthenticated} = MixerHosted.CustomerBuilds.read(nil, selection())
  end

  test "actual customer read matches every stored selection dimension and performs no writes or enqueue" do
    before =
      sql(
        "SELECT (SELECT count(*) FROM oban_jobs),md5(string_agg(journal::text,',')) FROM mixer_builds"
      ).rows

    for key <-
          ~w(organization_id project_id application_id build_id platform source_sha256 toolchain_lock_sha256 build_definition_sha256)a do
      changed =
        cond do
          key == :platform -> "android"
          key in [:source_sha256, :toolchain_lock_sha256, :build_definition_sha256] -> digest("e")
          true -> "other"
        end

      assert {:error, reason} =
               MixerHosted.CustomerBuilds.read(identity(), Map.put(selection(), key, changed))

      assert reason in [:not_found, :unauthenticated]
    end

    assert (request() |> R1026.Router.call([])).status == 200

    assert sql(
             "SELECT (SELECT count(*) FROM oban_jobs),md5(string_agg(journal::text,',')) FROM mixer_builds"
           ).rows == before

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             MixerHosted.Repo.query("UPDATE public.mixer_builds SET revision=revision+1", [])

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             MixerHosted.Repo.query(
               "INSERT INTO oban_jobs(args,queue,worker) VALUES ('{}','builds','x')",
               []
             )
  end

  test "stored stale revision and forged journal cannot publish actual HTTP status" do
    sql("UPDATE mixer_builds SET revision=1")
    assert (request() |> R1026.Router.call([])).status == 503
    row = store(initial())
    {j, b} = initial()
    {:ok, ref} = Lifecycle.worker_ref(b)
    {j, _} = append({j, b}, "start", %{type: :start, ref: ref}, 1)
    j = %{j | "events" => j["events"] ++ j["events"]}
    sql("UPDATE mixer_builds SET journal=$1,revision=2", [j])
    assert (request() |> R1026.Router.call([])).status == 503
    refute row.revision != 0
  end

  test "post-COMMIT late publication fails closed after definite SQL acknowledgment" do
    handler = {__MODULE__, :late_commit}

    :ok =
      :telemetry.attach(
        handler,
        [:mixer_hosted, :customer_builds, :transaction],
        fn _, _, m, _ ->
          if m.query == "commit", do: Process.sleep(1100)
        end,
        nil
      )

    try do
      assert {:error, :authorization_unavailable} =
               MixerHosted.CustomerBuilds.read(
                 identity(%{expires_at: System.system_time(:second) + 1}),
                 selection()
               )
    after
      :telemetry.detach(handler)
    end

    assert {:ok, %{state: "queued"}} = MixerHosted.CustomerBuilds.read(identity(), selection())
  end
end
