Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.CustomerBuildInputsFixture do
  defmacro __using__(opts) do
    quote do
      use ExUnit.Case, async: false
      import MixerHosted.Test.OrdinaryBrowserStartupFixture
      alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
      alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
      alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
      @create_scope unquote(Keyword.fetch!(opts, :create))
      @retained_logs unquote(Keyword.get(opts, :retained_logs, false))
      setup_all do
        conn = F.connection!("browser_admin", "postgres")

        case Postgrex.query!(
               conn,
               "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname='mixer_customer_build_catalog_definer_v1'",
               []
             ).rows do
          [] ->
            Postgrex.query!(
              conn,
              "CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT",
              []
            )

          [[false, false, false, false, false, false, false]] ->
            :ok
        end

        GenServer.stop(conn)
        parent = System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT")
        ev = Path.join(parent, "attempt-" <> Base.encode16(:crypto.strong_rand_bytes(6)))
        File.mkdir!(ev)
        System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", ev)

        on_exit(fn ->
          System.put_env("MIXER_BROWSER_CATALOG_FIXTURE_ROOT", parent)
          assert System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT") == parent

          File.write!(
            Path.join(
              ev,
              "parent-restored-" <> inspect(__MODULE__) <> ".json"
            ),
            Jason.encode!(%{restored: true})
          )
        end)

        c = Fixture.prepare!(@create_scope)

        c =
          if @create_scope do
            case F.q!(
                   Admin,
                   "SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname='mixer_build_create'"
                 ).rows do
              [] ->
                F.q!(
                  Admin,
                  "CREATE ROLE mixer_build_create LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION"
                )

              [[true, false, false, false, false, false, false]] ->
                :ok
            end

            F.q!(Admin, "GRANT USAGE ON SCHEMA public TO mixer_build_create")

            F.q!(
              Admin,
              "GRANT SELECT ON " <>
                Enum.map_join(
                  ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
                  ",",
                  &("public.mixer_authz_" <> &1)
                ) <> " TO mixer_build_create"
            )

            for h <- ~w(profiles principals families credentials organization_heads project_heads),
                do:
                  F.q!(
                    Admin,
                    "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_" <>
                      h <> "() TO mixer_build_create"
                  )

            for sql <- MixerHosted.CustomerBuilds.CreateSchema.statements(),
                do: F.q!(Migration, sql)

            for sql <- MixerHosted.BrowserAuth.ActiveCreateSchema.statements(),
                do: F.q!(Migration, sql)

            F.q!(Admin, "GRANT CREATE ON SCHEMA public TO browser_writer")

            F.q!(
              Admin,
              "ALTER FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) OWNER TO browser_writer"
            )

            F.q!(Admin, "REVOKE CREATE ON SCHEMA public FROM browser_writer")

            F.q!(
              Admin,
              "GRANT EXECUTE ON FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) TO mixer_build_create"
            )

            create =
              c.hosted.repo
              |> Keyword.put(:username, "mixer_build_create")
              |> Keyword.put(:pool_size, 4)

            Map.put(c, :hosted, %{c.hosted | create_repo: create})
          else
            c
          end

        F.q!(Admin, "UPDATE mixer_authz_memberships SET role='developer' WHERE id='member-a'")

        c =
          if @retained_logs do
            # Evidence can live under a shared temporary directory, but retained logs need trusted ancestors.
            root = Path.join(System.user_home!(), "mixer-retained-logs-" <> Path.basename(ev))
            File.mkdir!(root)
            on_exit(fn -> File.rm_rf!(root) end)
            File.chmod!(root, 0o700)
            %{c | hosted: %{c.hosted | native: %{retained_root: root}}}
          else
            c
          end

        c = Fixture.start!(c)
        assert MixerHosted.BrowserAuth.RuntimeOwner.status().phase == :storage_ready
        c
      end

      defp login(c) do
        {cookie, csrf, _expires} = login_session(c)
        {cookie, csrf}
      end

      defp login_session(c) do
        preauth = bootstrap_http(c)
        b = begin_http(c, preauth)
        r = http(c, "/auth/callback?" <> b.query, b.headers)
        assert r.status == 303
        cookie = response_cookie(r)
        r = http(c, "/auth/session", headers(cookie))
        assert r.status == 200

        assert %{"state" => "authenticated", "csrf_token" => csrf, "expires_at" => expires} =
                 Jason.decode!(r.body)

        assert is_integer(expires)
        {cookie, csrf, expires}
      end

      defp list_path(overrides \\ %{}, cursor \\ nil) do
        scope =
          Map.merge(
            %{organization_id: "org-a", project_id: "project-a", application_id: "fieldlog"},
            overrides
          )

        fields = if cursor, do: Map.put(scope, :cursor, cursor), else: scope
        "/console-api/v1/build-inputs?" <> URI.encode_query(fields)
      end

      defp counts,
        do:
          {F.q!(Admin, "SELECT count(*) FROM mixer_builds").rows,
           F.q!(Admin, "SELECT count(*) FROM oban_jobs").rows}

      defp seed_input(app, platform, id) do
        F.q!(
          Admin,
          "INSERT INTO mixer_customer_build_inputs VALUES('org-a','project-a',$1,$2,$3,'revision','secret-reference-do-not-disclose',$4,$5,$6,2,10000,0)",
          [
            app,
            platform,
            id,
            String.duplicate("a", 64),
            String.duplicate("b", 64),
            String.duplicate("c", 64)
          ]
        )
      end

      defp create_body(row) do
        %{
          organization_id: "org-a",
          project_id: "project-a",
          application_id: "fieldlog",
          platform: row["platform"],
          source_input_id: row["sourceInputId"],
          source_sha256: row["sourceSha256"],
          toolchain_lock_sha256: row["toolchainLockSha256"],
          build_definition_sha256: row["buildDefinitionSha256"]
        }
      end

      defp post(c, cookie, csrf, key, body) do
        raw = Jason.encode!(body)

        http(
          c,
          "/console-api/v1/builds",
          headers(cookie) ++
            [
              {"origin", c.config.public_origin},
              {"x-mixer-csrf", csrf},
              {"content-type", "application/json"},
              {"content-length", Integer.to_string(byte_size(raw))},
              {"idempotency-key", key}
            ],
          "POST",
          raw
        )
      end

      defp note(name), do: IO.puts("R2210_PASS " <> name)
    end
  end
end

defmodule MixerHosted.CustomerBuildInputsHTTPSQLTest do
  use MixerHosted.CustomerBuildInputsFixture, create: true
  alias MixerHosted.CustomerBuilds.CreateRepo

  def observe(_, _, %{repo: CreateRepo, query: q, result: {:ok, result}}, pid)
      when is_binary(q) do
    if String.starts_with?(
         q,
         "SELECT platform,input_id,source_sha256,toolchain_lock_sha256,build_definition_sha256"
       ) do
      [[user, session]] =
        Ecto.Adapters.SQL.query!(CreateRepo, "SELECT current_user::text,session_user::text", [],
          log: false
        ).rows

      send(
        pid,
        {:listing_sql,
         %{
           query: q,
           rows: result.num_rows,
           user: user,
           session: session,
           in_transaction: CreateRepo.in_transaction?()
         }}
      )

      case :persistent_term.get({__MODULE__, :expire}, nil) do
        nil -> :ok
        expires -> Process.sleep(max(0, expires * 1000 - System.system_time(:millisecond) + 20))
      end
    end
  end

  def observe(_, _, _, _), do: :ok

  test "authenticated_console_create_selects_admitted_input_and_displays_queued_build", c do
    {cookie, csrf} = login(c)
    path = list_path()
    event = CreateRepo.config()[:telemetry_prefix] ++ [:query]
    :ok = :telemetry.attach("r2210-listing-sql", event, &__MODULE__.observe/4, self())

    on_exit(fn ->
      :telemetry.detach("r2210-listing-sql")
      :persistent_term.erase({__MODULE__, :expire})
    end)

    assert counts() == {[[0]], [[0]]}
    empty = http(c, path, headers(cookie))
    assert empty.status == 200, empty.body

    assert Jason.decode!(empty.body) == %{
             "organizationId" => "org-a",
             "projectId" => "project-a",
             "applicationId" => "fieldlog",
             "inputs" => [],
             "nextCursor" => nil
           }

    assert_receive {:listing_sql, %{rows: 0}}

    F.q!(
      Admin,
      "INSERT INTO mixer_authz_applications VALUES('org-a','project-a','sibling',true),('org-a','project-a','inactive',false),('org-b','project-b','fieldlog',true)"
    )

    seed_input("sibling", "ios", "secret-sibling")
    seed_input("inactive", "ios", "secret-inactive")

    F.q!(
      Admin,
      "INSERT INTO mixer_customer_build_inputs VALUES('org-b','project-b','fieldlog','ios','secret-tenant','revision','tenant-reference',$1,$2,$3,2,10000,0)",
      [String.duplicate("d", 64), String.duplicate("e", 64), String.duplicate("f", 64)]
    )

    expected =
      for n <- 1..27 do
        platform = if rem(n, 2) == 0, do: "ios", else: "android"
        id = "Input-" <> String.pad_leading(Integer.to_string(n), 2, "0")
        seed_input("fieldlog", platform, id)
        {platform, id}
      end
      |> Enum.sort()

    first = http(c, path, headers(cookie))
    assert first.status == 200, first.body
    assert response_header(first, "cache-control") == ["no-store"]
    data = Jason.decode!(first.body)

    assert Enum.sort(Map.keys(data)) ==
             ~w(applicationId inputs nextCursor organizationId projectId)

    assert length(data["inputs"]) == 25
    assert is_binary(data["nextCursor"])

    for row <- data["inputs"] do
      assert Enum.sort(Map.keys(row)) ==
               ~w(buildDefinitionSha256 platform sourceInputId sourceSha256 toolchainLockSha256)
    end

    assert_receive {:listing_sql, witness}

    assert witness.rows == 26 and witness.user == "mixer_build_create" and
             witness.session == "mixer_build_create" and witness.in_transaction

    assert String.contains?(witness.query, "LIMIT 26")

    assert String.contains?(
             witness.query,
             "ORDER BY platform COLLATE \"C\", input_id COLLATE \"C\""
           )

    second = http(c, list_path(%{}, data["nextCursor"]), headers(cookie))
    assert second.status == 200, second.body
    tail = Jason.decode!(second.body)
    assert tail["nextCursor"] == nil and length(tail["inputs"]) == 2
    assert_receive {:listing_sql, %{rows: 2, query: query}}
    assert String.contains?(query, "> ($4::text COLLATE \"C\", $5::text COLLATE \"C\")")
    actual = Enum.map(data["inputs"] ++ tail["inputs"], &{&1["platform"], &1["sourceInputId"]})
    assert actual == expected and length(Enum.uniq(actual)) == 27

    refute String.contains?(first.body <> second.body, [
             "secret-",
             "source_reference",
             "max_attempts",
             "timeout_ms",
             "cookie",
             "csrf",
             "credential",
             "policy",
             "debug"
           ])

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "sql-bounds.json"),
      Jason.encode!(%{
        first: witness,
        order: Enum.map(actual, &Tuple.to_list/1),
        page_sizes: [25, 2]
      })
    )

    note("actual_cookie_create_role_select26_fixed25_C_keyset_projection")

    for overrides <- [
          %{application_id: "sibling"},
          %{project_id: "project-b"},
          %{organization_id: "org-b"}
        ] do
      assert http(c, list_path(overrides, data["nextCursor"]), headers(cookie)).status == 400
    end

    for query <- [
          "&limit=26",
          "&application_id=fieldlog",
          "&cursor=%",
          "&cursor=" <> data["nextCursor"] <> "="
        ] do
      assert http(c, path <> query, headers(cookie)).status == 400
    end

    for extras <- [
          [{"x-http-method-override", "POST"}],
          [{"x-method-override", "POST"}],
          [{"content-encoding", "gzip"}]
        ] do
      assert http(c, path, headers(cookie) ++ extras).status == 400
    end

    assert http(c, path, headers(cookie) ++ [{"content-length", "1"}], "GET", "x").status == 400
    assert http(c, path, [{"authorization", "Bearer fabricated"}]).status == 400
    assert http(c, path, []).status == 401

    for overrides <- [
          %{application_id: "inactive"},
          %{application_id: "missing"},
          %{organization_id: "org-b", project_id: "project-b"}
        ] do
      assert http(c, list_path(overrides), headers(cookie)).status == 404
    end

    assert counts() == {[[0]], [[0]]}
    note("canonical_crossscope_cursor_body_override_bearer_hidden_refusals_no_effect")

    row = hd(data["inputs"])
    body = create_body(row)
    created = post(c, cookie, csrf, "selected-input", body)
    assert created.status == 201, created.body
    result = Jason.decode!(created.body)
    assert Enum.sort(Map.keys(result)) == ~w(outcome revision selection state)

    assert result["outcome"] == "applied" and result["state"] == "queued" and
             result["revision"] == 0

    assert counts() == {[[1]], [[1]]}

    exact =
      http(c, "/console-api/v1/builds?" <> URI.encode_query(result["selection"]), headers(cookie))

    assert exact.status == 200, exact.body
    detail = Jason.decode!(exact.body)
    assert detail["build"]["buildId"] == result["selection"]["build_id"]
    assert detail["build"]["applicationId"] == result["selection"]["application_id"]
    assert detail["build"]["platform"] == result["selection"]["platform"]
    assert detail["build"]["sourceSha256"] == result["selection"]["source_sha256"]
    assert detail["build"]["toolchainLockSha256"] == result["selection"]["toolchain_lock_sha256"]

    assert detail["build"]["buildDefinitionSha256"] ==
             result["selection"]["build_definition_sha256"]

    assert detail["build"]["state"] == "queued"
    duplicate = post(c, cookie, csrf, "selected-input", body)

    assert duplicate.status == 200 and
             Jason.decode!(duplicate.body)["selection"] == result["selection"]

    assert post(
             c,
             cookie,
             csrf,
             "changed-pin",
             Map.put(body, :source_sha256, String.duplicate("d", 64))
           ).status == 409

    assert post(c, cookie, csrf, "cross-app", Map.put(body, :application_id, "sibling")).status ==
             404

    assert post(c, cookie, "invalid", "csrf-refused", body).status == 403
    # Existing POST still works without an earlier listing and retains its exact wire.
    assert post(c, cookie, csrf, "no-list-required", body).status == 201
    assert counts() == {[[2]], [[2]]}
    note("GET_select_unchanged_POST201_exact_GETqueued_replay200_no_list_POST_control")

    for role <- ~w(owner administrator developer) do
      F.q!(Admin, "UPDATE mixer_authz_memberships SET role=$1 WHERE id='member-a'", [role])
      assert http(c, path, headers(cookie)).status == 200
    end

    for role <- ~w(viewer release_manager billing_manager) do
      F.q!(Admin, "UPDATE mixer_authz_memberships SET role=$1 WHERE id='member-a'", [role])
      denied = http(c, path, headers(cookie))

      assert denied.status == 403 and
               Jason.decode!(denied.body)["error"]["code"] == "permission_denied"

      assert post(c, cookie, csrf, "denied-role", body).status == 403
    end

    F.q!(Admin, "UPDATE mixer_authz_memberships SET role='developer' WHERE id='member-a'")
    :ok = GenServer.call(c.provider, {:mode, :no_build_scope})
    {scope_cookie, scope_csrf} = login(c)
    assert http(c, path, headers(scope_cookie)).status == 403
    assert post(c, scope_cookie, scope_csrf, "denied-scope", body).status == 403
    note("existing_roles_and_missing_create_scope_denied_each_request")

    # The registry accepts trusted IDs more broadly than the public CreateInput grammar.
    # A malformed trusted row, even when not customer supplied, must refuse the page.
    seed_input("fieldlog", "android", "bad id")
    malformed = http(c, path, headers(cookie))

    assert malformed.status == 503 and
             Jason.decode!(malformed.body)["error"]["code"] == "storage_unavailable"

    assert response_header(malformed, "retry-after") == ["1"]
    refute String.contains?(malformed.body, ["bad id", "SELECT", "secret-reference"])
    F.q!(Admin, "DELETE FROM mixer_customer_build_inputs WHERE input_id='bad id'")

    for {platform, id} <- Enum.take(expected, -2) do
      F.q!(
        Admin,
        "DELETE FROM mixer_customer_build_inputs WHERE application_id='fieldlog' AND platform=$1 AND input_id=$2",
        [platform, id]
      )
    end

    exactly = http(c, path, headers(cookie))
    assert exactly.status == 200
    exact_page = Jason.decode!(exactly.body)
    assert length(exact_page["inputs"]) == 25 and exact_page["nextCursor"] == nil
    note("malformed_trusted_row503_and_actual_exact25_no_cursor")

    :ok = GenServer.call(c.provider, {:mode, :short})
    {short_cookie, _, expires} = login_session(c)
    :persistent_term.put({__MODULE__, :expire}, expires)
    expired = http(c, path, headers(short_cookie))
    :persistent_term.erase({__MODULE__, :expire})
    assert expired.status == 503, expired.body
    assert Jason.decode!(expired.body)["error"]["code"] == "authorization_unavailable"

    refute String.contains?(expired.body, [
             "phase",
             "payload",
             "Store.Failure",
             "cookie",
             "SELECT"
           ])

    assert counts() == {[[2]], [[2]]}
    note("post_SELECT_expiry_guard_typed_failure503_no_effect")
    F.q!(Admin, "UPDATE mixer_authz_credentials SET active=false")
    revoked = http(c, path, headers(cookie))
    assert revoked.status in [401, 503], revoked.body
    assert counts() == {[[2]], [[2]]}
    note("revocation_retained_checks_no_effect")
    leases_clean()
  end
end

defmodule MixerHosted.CustomerBuildLogsHTTPSQLTest do
  use MixerHosted.CustomerBuildInputsFixture, create: true, retained_logs: true

  test "authenticated terminal logs expose only the exact committed attempt", c do
    {cookie, csrf} = login(c)
    urls = for platform <- ~w(ios android), do: assert_terminal_logs(c, cookie, csrf, platform)

    F.q!(Admin, "UPDATE mixer_authz_memberships SET active=false WHERE id='member-a'")
    for url <- urls, do: assert(http(c, url, headers(cookie)).status == 404)
    leases_clean()
  end

  defp assert_terminal_logs(c, cookie, csrf, platform) do
    alias MixerHosted.Builds.{Dispatch, Journal, Lifecycle}
    seed_input("fieldlog", platform, "log-input-" <> platform)

    inputs = Jason.decode!(http(c, list_path(), headers(cookie)).body)["inputs"]
    input = Enum.find(inputs, &(&1["platform"] == platform))
    created = post(c, cookie, csrf, "log-build-" <> platform, create_body(input))
    assert created.status == 201
    selection = Jason.decode!(created.body)["selection"]
    url = "/console-api/v1/build-logs?" <> URI.encode_query(selection)
    assert http(c, url, []).status == 401
    assert http(c, url, headers(cookie), "POST").status == 404
    assert http(c, url <> "&build_id=duplicate", headers(cookie)).status == 400
    assert http(c, url, headers(cookie) ++ [{"x-http-method-override", "POST"}]).status == 400

    [[id, queued]] =
      F.q!(Admin, "SELECT id::text,journal FROM mixer_builds WHERE platform=$1", [platform]).rows

    {:ok, build} = Journal.restore(queued)
    {:ok, ref} = Lifecycle.worker_ref(build)
    operation = Dispatch.operation_id(id, ref)
    path = Path.join(c.hosted.native.retained_root, "customer-log-v1-" <> operation)

    {command_key, event, phases} =
      case platform do
        "ios" -> {:compiler, "compiler_finished", ["compile"]}
        "android" -> {:androidDriver, "android_driver_finished", []}
      end

    diagnostics = %{
      exitCode: 65,
      stdoutBytes: 320,
      stderrBytes: 80,
      tailTruncated: false,
      phases: phases
    }

    payload = %{
      version: 1,
      operationId: operation,
      sourceSha256: selection["source_sha256"],
      toolchainLockSha256: selection["toolchain_lock_sha256"],
      buildDefinitionSha256: selection["build_definition_sha256"],
      cliExitCode: 1
    }

    payload = Map.put(payload, command_key, diagnostics)

    File.write!(path, Jason.encode!(payload))
    File.chmod!(path, 0o400)
    assert http(c, url, headers(cookie)).status == 404

    started_at = build.observed_at + 1

    {:ok, running, _, :applied} =
      Journal.append(queued, "log-start", %{type: :start, ref: ref}, started_at)

    result = %{
      outcome: :failed,
      class: :compiler,
      code: :compiler_error,
      diagnostic_sha256: String.duplicate("d", 64)
    }

    {:ok, finished, _, :applied} =
      Journal.append(
        running,
        "log-finished",
        %{type: :completed, ref: ref, result: result},
        started_at + 1
      )

    F.q!(Admin, "UPDATE mixer_builds SET journal=$1,revision=$2 WHERE platform=$3", [
      finished,
      length(finished["events"]),
      platform
    ])

    response = http(c, url, headers(cookie))
    assert response.status == 200, response.body
    assert response_header(response, "cache-control") == ["no-store"]
    assert %{"buildLogs" => logs} = Jason.decode!(response.body)
    assert %{"state" => "failed", "attempt" => 1, "platform" => ^platform} = logs
    assert logs["revision"] == length(finished["events"])

    assert logs["events"] == [
             %{
               "event" => event,
               "exitCode" => 65,
               "stdoutBytes" => 320,
               "stderrBytes" => 80,
               "tailTruncated" => false,
               "phases" => phases
             },
             %{"event" => "build_command_finished", "exitCode" => 1}
           ]

    refute response.body =~ operation
    refute response.body =~ "secret-reference-do-not-disclose"

    for {key, value} <- [
          {"organization_id", "org-b"},
          {"project_id", "project-b"},
          {"application_id", "other"},
          {"build_id", "other"},
          {"platform", if(platform == "ios", do: "android", else: "ios")},
          {"source_sha256", String.duplicate("e", 64)},
          {"toolchain_lock_sha256", String.duplicate("e", 64)},
          {"build_definition_sha256", String.duplicate("e", 64)}
        ] do
      query = selection |> Map.put(key, value) |> URI.encode_query()
      assert http(c, "/console-api/v1/build-logs?" <> query, headers(cookie)).status == 404
    end

    File.rm!(path)
    assert http(c, url, headers(cookie)).status == 404
    File.write!(path <> ".other", Jason.encode!(payload))
    File.ln_s!(path <> ".other", path)
    assert http(c, url, headers(cookie)).status == 503
    File.rm!(path)
    File.write!(path, Jason.encode!(Map.put(payload, :rawOutput, "private")))
    File.chmod!(path, 0o400)
    assert http(c, url, headers(cookie)).status == 503
    File.rm!(path)

    if platform == "android" do
      for invalid <- [
            Map.put(payload, command_key, %{diagnostics | phases: ["compile"]}),
            payload |> Map.delete(command_key) |> Map.put(:compiler, diagnostics)
          ] do
        File.write!(path, Jason.encode!(invalid))
        File.chmod!(path, 0o400)
        assert http(c, url, headers(cookie)).status == 503
        File.rm!(path)
      end

      valid = Jason.encode!(payload)

      for {size, status} <- [{2_048, 200}, {2_049, 503}] do
        File.write!(path, String.pad_trailing(valid, size))
        File.chmod!(path, 0o400)
        assert http(c, url, headers(cookie)).status == status
        File.rm!(path)
      end

      File.write!(path, Jason.encode!(Map.put(payload, command_key, nil)))
      File.chmod!(path, 0o400)
      response = http(c, url, headers(cookie))
      assert response.status == 200

      assert Jason.decode!(response.body)["buildLogs"]["events"] == [
               %{"event" => "build_command_finished", "exitCode" => 1}
             ]

      File.rm!(path)
    end

    File.write!(path, Jason.encode!(payload))
    File.chmod!(path, 0o400)
    url
  end
end

defmodule MixerHosted.CustomerBuildSessionRecoveryHTTPTest do
  use MixerHosted.CustomerBuildInputsFixture, create: true
  alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner}

  @recovery_event [:mixer_hosted, :browser_auth, :store, :transaction]

  def observe_recovery(
        @recovery_event,
        measurements,
        %{
          type: :ecto_sql_query,
          repo: LifecycleRepo,
          query: "begin",
          result:
            {:error,
             %DBConnection.ConnectionError{
               reason: :error,
               message: "connection not available and queuing is disabled"
             }}
        },
        parent
      ) do
    send(parent, {:checkout_refusal, Enum.sort(Map.keys(measurements))})
  end

  def observe_recovery(_, _, _, _), do: :ok

  test "ordinary authenticated builds recover when the lifecycle pool becomes available", c do
    {cookie, csrf} = login(c)
    seed_input("fieldlog", "ios", "recovery-input")
    listed = http(c, list_path(), headers(cookie))
    assert listed.status == 200
    [input] = Jason.decode!(listed.body)["inputs"]
    body = create_body(input)
    first = post(c, cookie, csrf, "l07-existing", body)
    assert first.status == 201
    first_selection = Jason.decode!(first.body)["selection"]
    assert counts() == {[[1]], [[1]]}

    status = RuntimeOwner.status()
    owner = Process.whereis(RuntimeOwner)
    endpoint = Process.whereis(MixerHostedWeb.Endpoint)
    %{pid: pool} = Ecto.Adapter.lookup_meta(LifecycleRepo)

    assert [%{ready_conn_count: 2, checkout_queue_length: 0}] =
             DBConnection.get_connection_metrics(pool)

    parent = self()
    observer = make_ref()
    :ok = :telemetry.attach(observer, @recovery_event, &__MODULE__.observe_recovery/4, parent)
    on_exit(fn -> :telemetry.detach(observer) end)

    holders =
      for _ <- 1..2 do
        Task.async(fn ->
          LifecycleRepo.checkout(
            fn ->
              send(parent, {:checkout_held, self()})

              receive do
                :release_checkout -> :released
              after
                10_000 -> raise "checkout fixture timed out"
              end
            end,
            queue: false,
            timeout: 12_000
          )
        end)
      end

    try do
      for holder <- holders do
        pid = holder.pid
        assert_receive {:checkout_held, ^pid}
      end

      assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
               DBConnection.get_connection_metrics(pool)

      responses =
        ["l07-existing", "l07-retry", "l07-existing", "l07-retry", "l07-retry"]
        |> Task.async_stream(fn key -> post(c, cookie, csrf, key, body) end,
          max_concurrency: 5,
          timeout: 8_000
        )
        |> Enum.map(fn {:ok, response} -> response end)

      for response <- responses do
        assert response.status == 503
        assert response_header(response, "set-cookie") == []
        assert_receive {:checkout_refusal, [:queue_time, :total_time]}
      end

      assert RuntimeOwner.status() == status
      assert counts() == {[[1]], [[1]]}
    after
      for holder <- holders, do: send(holder.pid, :release_checkout)
      for holder <- holders, do: assert(Task.await(holder, 2000) == :released)
    end

    assert [%{ready_conn_count: 2, checkout_queue_length: 0}] =
             DBConnection.get_connection_metrics(pool)

    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    assert %{"state" => "authenticated", "csrf_token" => ^csrf} = Jason.decode!(session.body)
    assert response_header(session, "set-cookie") == []

    original_replay = post(c, cookie, csrf, "l07-existing", body)
    assert original_replay.status == 200
    assert Jason.decode!(original_replay.body)["selection"] == first_selection
    assert counts() == {[[1]], [[1]]}

    retry = post(c, cookie, csrf, "l07-retry", body)
    assert retry.status == 201
    second_selection = Jason.decode!(retry.body)["selection"]
    refute second_selection["build_id"] == first_selection["build_id"]

    replay = post(c, cookie, csrf, "l07-retry", body)
    assert replay.status == 200
    assert Jason.decode!(replay.body)["selection"] == second_selection
    assert counts() == {[[2]], [[2]]}

    allowed =
      http(c, "/console-api/v1/builds?" <> URI.encode_query(second_selection), headers(cookie))

    assert allowed.status == 200
    assert Jason.decode!(allowed.body)["build"]["buildId"] == second_selection["build_id"]

    denied =
      http(c, list_path(%{organization_id: "org-b", project_id: "project-b"}), headers(cookie))

    assert denied.status == 404
    assert RuntimeOwner.status() == status
    assert Process.whereis(RuntimeOwner) == owner
    assert Process.whereis(MixerHostedWeb.Endpoint) == endpoint
    assert {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
    assert port == c.http_port
    leases_clean()
  end
end

defmodule MixerHosted.CustomerBuildInputsReadonlyHTTPTest do
  use MixerHosted.CustomerBuildInputsFixture, create: false

  test "configured readonly login remains readonly despite developer role", c do
    {cookie, csrf} = login(c)

    r = http(c, list_path(), headers(cookie))
    assert r.status == 403, r.body

    assert Process.whereis(MixerHosted.CustomerBuilds.CreateRepo) == nil
    assert Jason.decode!(r.body)["error"]["code"] == "permission_denied"

    body = %{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "fieldlog",
      platform: "ios",
      source_input_id: "readonly-input",
      source_sha256: String.duplicate("a", 64),
      toolchain_lock_sha256: String.duplicate("b", 64),
      build_definition_sha256: String.duplicate("c", 64)
    }

    refused = post(c, cookie, csrf, "readonly", body)
    assert refused.status == 403, refused.body
    assert Jason.decode!(refused.body)["error"]["code"] == "permission_denied"
    assert http(c, list_path(), []).status == 401
    anonymous_raw = Jason.encode!(body)

    assert http(
             c,
             "/console-api/v1/builds",
             [
               {"origin", c.config.public_origin},
               {"x-mixer-csrf", csrf},
               {"content-type", "application/json"},
               {"content-length", Integer.to_string(byte_size(anonymous_raw))},
               {"idempotency-key", "anonymous"}
             ],
             "POST",
             anonymous_raw
           ).status == 401

    raw = Jason.encode!(body)

    assert http(
             c,
             "/console-api/v1/builds",
             headers(cookie) ++
               [
                 {"origin", c.config.public_origin},
                 {"content-type", "application/json"},
                 {"content-length", Integer.to_string(byte_size(raw))},
                 {"idempotency-key", "missing-csrf"}
               ],
             "POST",
             raw
           ).status == 403

    assert post(c, cookie, "invalid", "wrong-csrf", body).status == 403
    :ok = GenServer.call(c.provider, {:mode, :short})
    {short_cookie, short_csrf, expires} = login_session(c)
    Process.sleep(max(0, expires * 1000 - System.system_time(:millisecond) + 20))
    expired_get = http(c, list_path(), headers(short_cookie))
    expired_post = post(c, short_cookie, short_csrf, "expired-readonly", body)
    assert expired_get.status in [401, 503], expired_get.body
    assert expired_post.status in [401, 503], expired_post.body
    assert counts() == {[[0]], [[0]]}
    leases_clean()

    File.write!(
      Path.join(System.fetch_env!("MIXER_BROWSER_CATALOG_FIXTURE_ROOT"), "readonly-proof.json"),
      Jason.encode!(%{
        get: r.status,
        post: refused.status,
        create_repo_absent: true,
        anonymous_get: 401,
        anonymous_post: 401,
        missing_csrf: 403,
        wrong_csrf: 403,
        expired_get: expired_get.status,
        expired_post: expired_post.status,
        builds: 0,
        jobs: 0,
        leases_clean: true
      })
    )

    note("readonly_configuration_scope_not_promoted")
    leases_clean()
  end
end
