Code.require_file("application_registration_proof_test.exs", __DIR__)

defmodule MixerHosted.PrivacyHTTPTest do
  use ExUnit.Case, async: false
  require Logger

  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.BrowserAuth.{RuntimeOwner, StorageFixture.Admin}
  alias MixerHosted.Builds.{Dispatch, Journal, Lifecycle, Record}
  alias MixerHosted.Identity.StartupFixture
  alias MixerHosted.RuntimeConfig
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB

  @artifact_kinds ~w(unsigned_native_binary debug_symbols resource_inventory)a
  @log_control "privacy fixture stock Logger control"
  @events [
    [:bandit, :request, :start],
    [:bandit, :request, :stop],
    [:phoenix, :error_rendered],
    [:mixer_hosted, :repo, :query],
    [:mixer_hosted, :customer_builds, :transaction]
  ]

  setup_all do
    c = prepare!(:workspace_builds)
    provision_workspace!()
    MixerHosted.BrowserAuth.ApplicationRegistrationProofTest.install_create_surface()
    root = Path.join(System.fetch_env!("PRIVACY_SCRATCH"), "retained")
    File.mkdir!(root)
    File.chmod!(root, 0o700)

    assert c.hosted.native == nil
    mode = System.fetch_env!("PRIVACY_MODE")

    # The stock startup fixture chooses port 0 by replacing the whole HTTP list.
    # Restore the pinned runtime options before starting the ordinary listener.
    runtime_http = RuntimeConfig.load!(StartupFixture.foundation_env()).endpoint[:http]
    assert runtime_http[:http_2_options] == [enabled: false]
    owned_address = Keyword.take(c.hosted.endpoint[:http], [:ip, :port])
    assert owned_address == [ip: {127, 0, 0, 1}, port: 0]
    endpoint = Keyword.put(c.hosted.endpoint, :http, Keyword.merge(runtime_http, owned_address))
    c = put_in(c.hosted.endpoint, endpoint)

    hosted =
      if mode == "retained" do
        native =
          StartupFixture.foundation_env()
          |> Map.merge(%{
            "MIXER_PROCESSOR_PROFILE" => "builds_v1",
            "MIXER_HTTP_BIND" => "127.0.0.1",
            "MIXER_NATIVE_RETAINED_ROOT" => root
          })
          |> RuntimeConfig.load!()
          |> Map.fetch!(:native)

        %{c.hosted | native: native}
      else
        c.hosted
      end

    create_repo = Keyword.put(hosted.repo, :username, "mixer_build_create")
    c = start!(%{c | hosted: %{hosted | create_repo: create_repo}})
    assert RuntimeOwner.status().phase == :storage_ready

    assert Application.fetch_env!(:mixer_hosted, MixerHostedWeb.Endpoint)[:http][
             :http_2_options
           ] == [enabled: false]

    %{port: jwks_port} = GenServer.call(c.fixture, :authority)

    IO.puts(
      "PRIVACY_LISTENERS " <>
        Jason.encode!(%{phoenix: c.http_port, authorization: c.provider_port, jwks: jwks_port})
    )

    assert c.hosted.repo[:username] == "browser_ordinary"
    assert c.hosted.oban[:queues] == false

    assert DB.q!(MixerHosted.Repo, """
           SELECT current_user, rolsuper, rolbypassrls, rolinherit
           FROM pg_roles WHERE rolname=current_user
           """).rows == [["browser_ordinary", false, false, false]]

    Map.merge(c, %{mode: mode, retained: root})
  end

  @tag timeout: 40_000
  test "ordinary tenant reads, exports and diagnostics expose only admitted data", c do
    case_id = "9db83467-42d5-4873-90e0-a1a02a0044dc"

    a = seed(c, "a", "person-1", :native_succeeded)
    b = seed(c, "b", "privacy-person-b", :failed)
    initial_telemetry = stock_telemetry!()
    stock_logger = stock_logger!()
    a = Map.put(a, :auth, login(c, :ok))
    b = Map.put(b, :auth, login(c, :other_tenant))
    restricted = login(c, :no_build_scope)
    refute a.auth.cookie == b.auth.cookie
    invalid_query = "PRIVACY_QUERY_SECRET_SYNTHETIC"
    rejected_bearer = "PRIVACY_BEARER_SYNTHETIC"

    markers =
      Enum.reduce([a, b], %{"query_secret" => invalid_query, "bearer" => rejected_bearer}, fn t,
                                                                                              values ->
        values
        |> Map.merge(auth_markers(t.auth, t.label))
        |> Map.put("tenant_" <> t.label, t.org_name)
        |> Map.put("source_" <> t.label, t.source)
        |> Map.put("form_" <> t.label, t.form)
        |> Map.put("operation_" <> t.label, t.operation)
        |> Map.put("artifact_" <> t.label, t.artifact)
      end)
      |> Map.merge(auth_markers(restricted, "restricted"))

    File.write!(
      Path.join(System.fetch_env!("PRIVACY_SCRATCH"), "synthetic-markers.json"),
      Jason.encode!(markers),
      [:exclusive]
    )

    before_handlers = stock_telemetry!()
    :ok = :telemetry.attach_many(__MODULE__, @events, &__MODULE__.observe/4, {self(), markers})
    on_exit(fn -> :telemetry.detach(__MODULE__) end)

    Logger.warning(@log_control)
    Logger.flush()

    checks = run_http_checks(c, a, b, case_id, invalid_query, rejected_bearer)

    assert response(get(c, a, "/console-api/v1/builds", restricted), 403) == %{
             "error" => %{"code" => "permission_denied"}
           }

    leases_clean()

    assert :ok = :telemetry.detach(__MODULE__)
    after_handlers = stock_telemetry!()
    assert initial_telemetry == before_handlers
    assert Map.has_key?(after_handlers, "mixer_hosted.customer_builds.transaction")
    assert stock_logger!() == stock_logger
    Logger.flush()
    events = drain([])
    assert Enum.any?(events, &(&1.path == "/console-api/v1/builds" and &1.status == 200))
    assert Enum.any?(events, &(&1.path == "/console-api/v1/build-logs" and &1.status == 400))

    for event <- @events, do: assert(Enum.any?(events, &(&1.event == Enum.join(event, "."))))

    found = for event <- events, event.hits != [], do: event

    IO.puts(
      "PRIVACY_RESULT " <>
        Jason.encode!(%{
          mode: c.mode,
          checks: Map.put(checks, :missingBuildScope, 403),
          http2Enabled: false,
          stockTelemetry: %{before: before_handlers, after: after_handlers},
          stockLogger: stock_logger,
          observedEvents: Enum.frequencies_by(events, & &1.event),
          eventsWithMarkers: Enum.frequencies_by(found, & &1.event),
          telemetryExamples:
            Enum.uniq(found) |> Enum.sort_by(&{&1.event, &1.path, &1.status, &1.hits})
        })
    )
  end

  defp run_http_checks(c, a, b, case_id, invalid_query, rejected_bearer) do
    for {own, other} <- [{a, b}, {b, a}] do
      support = %{
        operation: "submit",
        organization_id: own.org,
        request_id: case_id,
        subject: "Synthetic privacy fixture",
        message: own.form
      }

      assert response(post(c, own.auth, "/console-api/v1/support-requests", support), 201)[
               "request"
             ]["message"] ==
               own.form

      list = response(http(c, "/console-api/v1/orgs", headers(own.auth.cookie)), 200)
      assert Jason.encode!(list) =~ own.org_name
      refute Jason.encode!(list) =~ other.org_name

      detail = response(get(c, own, "/console-api/v1/builds"), 200)["build"]
      assert detail["state"] == own.state
      assert detail["organizationId"] == own.org
      refute Jason.encode!(detail) =~ own.source
      refute Jason.encode!(detail) =~ own.operation

      denied = get(c, other, "/console-api/v1/builds", own.auth)
      assert response(denied, 404) == %{"error" => %{"code" => "not_found"}}

      exported = export(c, own.auth, own.org)

      assert response(exported, 200) == %{
               "organization" => %{"id" => own.org, "display_name" => own.org_name},
               "projects" =>
                 [%{"id" => own.project, "display_name" => own.project, "active" => true}] ++
                   Enum.map(
                     secondary_projects(own),
                     &%{"id" => &1, "display_name" => &1, "active" => true}
                   ),
               "memberships" => [
                 %{"principal_id" => own.principal, "role" => "owner", "active" => true}
               ]
             }

      absent_export = export(c, own.auth, "privacy-nonexistent")
      denied_export = export(c, own.auth, other.org)
      assert response(denied_export, 404) == response(absent_export, 404)
      assert denied_export.body == absent_export.body

      cross_logs = get(c, other, "/console-api/v1/build-logs", own.auth)
      assert response(cross_logs, 404) == %{"error" => %{"code" => "not_found"}}

      bad_query =
        get(c, own, "/console-api/v1/build-logs", own.auth, "&proof=" <> invalid_query)

      assert response(bad_query, 400)["error"]["code"] == "invalid_request"
      refute bad_query.body =~ invalid_query

      own_logs = get(c, own, "/console-api/v1/build-logs")

      if c.mode == "retained" do
        assert response(own_logs, 200)["buildLogs"]["events"] == own.events
        refute own_logs.body =~ own.source
        refute own_logs.body =~ own.operation
        refute own_logs.body =~ own.form

        original = File.read!(own.log_path)
        File.rm!(own.log_path)
        write_log(own.log_path, Map.put(Jason.decode!(original), "rawOutput", own.form))

        try do
          failed = get(c, own, "/console-api/v1/build-logs")

          assert response(failed, 503) == %{
                   "error" => %{"code" => "authorization_unavailable"}
                 }

          assert response_header(failed, "retry-after") == ["1"]
          refute failed.body =~ own.form
        after
          File.rm!(own.log_path)
          write_log(own.log_path, Jason.decode!(original))
        end
      else
        assert response(own_logs, 404) == %{"error" => %{"code" => "not_found"}}
      end
    end

    downloads =
      Map.new(@artifact_kinds, fn kind ->
        path = "/console-api/v1/build-artifacts/" <> to_string(kind)

        assert response(get(c, a, path, b.auth), 404) == %{
                 "error" => %{"code" => "not_found"}
               }

        result = get(c, a, path)

        if c.mode == "retained" do
          assert {result.status, result.body} == {200, artifact_bytes(a.label, kind)}
          assert response_header(result, "cache-control") == ["no-store"]

          assert response_header(result, "content-disposition") == [
                   ~s(attachment; filename="#{kind}")
                 ]

          assert response_header(result, "x-content-type-options") == ["nosniff"]
        else
          assert response(result, 503) == %{
                   "error" => %{"code" => "authorization_unavailable"}
                 }
        end

        {kind, %{owner: result.status, otherTenant: 404}}
      end)

    for path <- [
          "/metrics",
          "/telemetry",
          "/console-api/v1/source-maps",
          "/console-api/v1/crash-attachments"
        ] do
      assert http(c, path, []).status == 404
      assert http(c, path <> "?proof=" <> invalid_query, headers(a.auth.cookie)).status == 404
    end

    denied = http(c, "/v3/orgs", [{"authorization", "Bearer " <> rejected_bearer}])
    assert denied.status == 401
    refute denied.body =~ rejected_bearer
    assert DB.q!(Admin, "SELECT count(*) FROM oban_jobs").rows == [[0]]
    leases_clean()

    %{
      tenants: 2,
      ownSupport: [201, 201],
      ownOrganizationList: [200, 200],
      ownBuild: [200, 200],
      crossTenantBuild: [404, 404],
      ownExport: [200, 200],
      crossTenantExport: [404, 404],
      ownLogs: if(c.mode == "retained", do: [200, 200], else: [404, 404]),
      crossTenantLogs: [404, 404],
      malformedQuery: [400, 400],
      malformedProjection: if(c.mode == "retained", do: [503, 503], else: []),
      downloads: downloads,
      rejectedBearer: 401,
      absentRoutes: 8
    }
  end

  defp secondary_projects(%{label: "a"}) do
    for i <- 0..51, do: "r604-" <> String.pad_leading(to_string(i), 2, "0")
  end

  defp secondary_projects(_), do: []

  defp seed(c, label, principal, status) do
    org = "org-" <> label
    project = "project-" <> label
    org_name = "PRIVACY_TENANT_" <> String.upcase(label)
    source = "refs/heads/PRIVACY_SOURCE_" <> String.upcase(label)
    form = "PRIVACY_FORM_" <> String.upcase(label)

    assert DB.q!(Admin, "UPDATE mixer_authz_organizations SET display_name=$2 WHERE id=$1", [
             org,
             org_name
           ]).num_rows == 1

    assert DB.q!(
             Admin,
             "UPDATE mixer_authz_projects SET display_name=id WHERE organization_id=$1 AND id=$2",
             [org, project]
           ).num_rows == 1

    if label == "b" do
      DB.q!(Admin, "INSERT INTO mixer_authz_principals VALUES($1,'human',true,0,1)", [principal])

      DB.q!(
        Admin,
        "INSERT INTO mixer_authz_bindings VALUES('humans',1,'subject-2','human',$1,true,1)",
        [principal]
      )

      DB.q!(
        Admin,
        "INSERT INTO mixer_authz_memberships VALUES('member-b',$1,'org-b',NULL,'all_projects','owner',true,0,NULL,1)",
        [principal]
      )

      DB.q!(
        Admin,
        "INSERT INTO mixer_authz_applications VALUES('org-b','project-b','fieldlog',true)",
        []
      )
    else
      assert DB.q!(Admin, "UPDATE mixer_authz_memberships SET role='owner' WHERE id='member-a'").num_rows ==
               1
    end

    selection = %{
      organization_id: org,
      project_id: project,
      application_id: "fieldlog",
      build_id: "privacy-build-" <> label,
      platform: "ios",
      source_sha256: digest(source),
      toolchain_lock_sha256: digest("lock"),
      build_definition_sha256: digest("definition")
    }

    spec = selection |> Map.take(~w(organization_id project_id application_id build_id)a)

    spec =
      Map.merge(spec, %{
        platform: :ios,
        source: %{kind: :revision, reference: source, sha256: selection.source_sha256},
        toolchain_lock_sha256: selection.toolchain_lock_sha256,
        build_definition_sha256: selection.build_definition_sha256
      })

    {:ok, queued, build} =
      Journal.new(
        spec,
        %{max_attempts: 1, timeout_ms: 1000, retry_backoff_ms: 0},
        "request-" <> label,
        0
      )

    {:ok, ref} = Lifecycle.worker_ref(build)
    id = Ecto.UUID.generate()
    operation = Dispatch.operation_id(id, ref)
    artifact = "PRIVACY_ARTIFACT_" <> String.upcase(label)

    outcome =
      case status do
        :native_succeeded ->
          store = Path.join([c.retained, operation, "native"])
          File.mkdir_p!(store)

          artifacts =
            for kind <- @artifact_kinds do
              bytes = artifact_bytes(label, kind)

              hash = digest(bytes)
              write_log(Path.join(store, hash), bytes)
              %Lifecycle.ArtifactRef{kind: kind, size_bytes: byte_size(bytes), sha256: hash}
            end

          %{outcome: status, artifacts: artifacts}

        :failed ->
          %{
            outcome: :failed,
            class: :compiler,
            code: :compiler_error,
            diagnostic_sha256: digest(form)
          }
      end

    {:ok, running, _, :applied} =
      Journal.append(queued, "privacy-start", %{type: :start, ref: ref}, 1)

    {:ok, terminal, _, :applied} =
      Journal.append(running, "privacy-finish", %{type: :completed, ref: ref, result: outcome}, 2)

    now = DateTime.utc_now()

    record =
      Map.merge(
        Map.take(selection, ~w(organization_id project_id application_id build_id platform)a),
        %{
          id: id,
          request_key: "request-" <> label,
          inserted_at: now,
          updated_at: now,
          revision: length(terminal["events"]),
          journal: terminal
        }
      )

    assert {1, _} = Admin.insert_all(Record, [record], log: false)

    exit = if status == :failed, do: 65, else: 0

    compiler = %{
      exitCode: exit,
      stdoutBytes: 28,
      stderrBytes: exit,
      tailTruncated: false,
      phases: ["compile"]
    }

    log_path = Path.join(c.retained, "customer-log-v1-" <> operation)

    write_log(log_path, %{
      version: 1,
      operationId: operation,
      compiler: compiler,
      cliExitCode: exit,
      sourceSha256: selection.source_sha256,
      toolchainLockSha256: selection.toolchain_lock_sha256,
      buildDefinitionSha256: selection.build_definition_sha256
    })

    events = [
      Map.put(compiler, :event, "compiler_finished"),
      %{event: "build_command_finished", exitCode: exit}
    ]

    %{
      org: org,
      project: project,
      org_name: org_name,
      principal: principal,
      label: label,
      source: source,
      selection: selection,
      state: to_string(status),
      log_path: log_path,
      events: json(events),
      form: form,
      operation: operation,
      artifact: artifact
    }
  end

  defp artifact_bytes(label, kind),
    do: Jason.encode!(%{fixture: "PRIVACY_ARTIFACT_" <> String.upcase(label), kind: kind})

  defp write_log(path, bytes) when is_binary(bytes) do
    File.write!(path, bytes, [:exclusive])
    File.chmod!(path, 0o400)
  end

  defp write_log(path, value), do: write_log(path, Jason.encode!(value))
  defp digest(value), do: :crypto.hash(:sha256, value) |> Base.encode16(case: :lower)
  defp json(value), do: value |> Jason.encode!() |> Jason.decode!()

  defp login(c, provider_mode) do
    assert :ok = GenServer.call(c.provider, {:mode, provider_mode})
    pre = bootstrap_http(c)
    login = begin_http(c, pre)
    callback = http(c, "/auth/callback?" <> login.query, login.headers)
    assert callback.status == 303
    cookie = response_cookie(callback)
    body = response(http(c, "/auth/session", headers(cookie)), 200)
    assert body["state"] == "authenticated"

    %{
      cookie: cookie,
      csrf: body["csrf_token"],
      bootstrap: pre,
      callback: URI.decode_query(login.query)
    }
  end

  defp auth_markers(auth, label) do
    %{
      "cookie_" => auth.cookie,
      "csrf_" => auth.csrf,
      "bootstrap_cookie_" => auth.bootstrap.cookie,
      "bootstrap_csrf_" => auth.bootstrap.csrf,
      "oidc_code_" => auth.callback["code"],
      "oidc_state_" => auth.callback["state"]
    }
    |> Map.new(fn {key, value} -> {key <> label, value} end)
  end

  defp get(c, t, path), do: get(c, t, path, t.auth)

  defp get(c, t, path, auth, suffix \\ "") do
    http(c, path <> "?" <> URI.encode_query(t.selection) <> suffix, headers(auth.cookie))
  end

  defp export(c, auth, org),
    do:
      post(c, auth, "/console-api/v1/workspace-admin", %{
        operation: "export",
        organization_id: org
      })

  defp post(c, auth, path, body) do
    raw = Jason.encode!(body)

    http(
      c,
      path,
      headers(auth.cookie) ++
        [
          {"origin", c.config.public_origin},
          {"x-mixer-csrf", auth.csrf},
          {"content-type", "application/json"},
          {"content-length", Integer.to_string(byte_size(raw))}
        ],
      "POST",
      raw
    )
  end

  defp response(r, expected) do
    assert r.status == expected
    assert response_header(r, "cache-control") == ["no-store"]
    Jason.decode!(r.body)
  end

  defp stock_telemetry! do
    inventory =
      for %{id: id, event_name: event, function: fun, config: config} <-
            :telemetry.list_handlers([]) do
        info = Function.info(fun)
        {event, id, {info[:module], info[:name], info[:arity]}, config}
      end

    phoenix_events = %{
      [:phoenix, :endpoint, :start] => :phoenix_endpoint_start,
      [:phoenix, :endpoint, :stop] => :phoenix_endpoint_stop,
      [:phoenix, :router_dispatch, :start] => :phoenix_router_dispatch_start,
      [:phoenix, :error_rendered] => :phoenix_error_rendered,
      [:phoenix, :socket_connected] => :phoenix_socket_connected,
      [:phoenix, :socket_drain] => :phoenix_socket_drain,
      [:phoenix, :channel_joined] => :phoenix_channel_joined,
      [:phoenix, :channel_handled_in] => :phoenix_channel_handled_in
    }

    phoenix =
      for {event, name} <- phoenix_events do
        {event, {Phoenix.Logger, event}, {Phoenix.Logger, name, 4}, :ok}
      end

    browser_store =
      {[:mixer_hosted, :browser_auth, :store, :transaction],
       {MixerHosted.BrowserAuth.Store, :transaction_receipt},
       {MixerHosted.BrowserAuth.Store, :transaction_event, 4}, nil}

    # These callbacks keep transaction receipts in the calling process dictionary.
    read_receipts =
      for {surface, module} <- [
            {:customer_builds, MixerHosted.CustomerBuilds.Context},
            {:customer_build_catalog, MixerHosted.CustomerBuildCatalog.Context}
          ] do
        {[:mixer_hosted, surface, :transaction], {module, :receipt_handler},
         {module, :transaction_event, 4}, nil}
      end

    always = [browser_store | phoenix]
    assert always -- inventory == []
    assert inventory -- (always ++ read_receipts) == []

    Map.new(inventory, fn {event, _id, {module, name, arity}, _config} ->
      {Enum.join(event, "."), "#{inspect(module)}.#{name}/#{arity}"}
    end)
  end

  defp stock_logger! do
    assert Enum.sort(:logger.get_handler_ids()) == [:default, :ssl_handler]

    assert {:ok,
            %{
              module: :logger_std_h,
              level: :all,
              config: %{type: :standard_io},
              formatter: {Logger.Formatter, %Logger.Formatter{metadata: []}}
            }} = :logger.get_handler_config(:default)

    assert {:ok,
            %{
              module: :logger_std_h,
              level: :debug,
              filters: [filter_non_ssl: {filter, {:log, :sub, [:otp, :ssl]}}],
              filter_default: :stop,
              config: %{type: :standard_io},
              formatter: {:ssl_logger, %{}}
            }} = :logger.get_handler_config(:ssl_handler)

    assert filter == (&:logger_filters.domain/2)
    assert Logger.level() == :warning

    %{
      primaryLevel: "warning",
      handlers: %{
        default: %{sink: "standard_io", module: "logger_std_h", level: "all"},
        ssl_handler: %{
          sink: "standard_io",
          module: "logger_std_h",
          level: "debug",
          domain: "otp.ssl"
        }
      }
    }
  end

  def observe(event, measurements, meta, {pid, markers}) do
    conn = Map.get(meta, :conn)

    fields =
      if conn,
        do: Map.take(conn, ~w(req_headers query_string adapter resp_body)a),
        else: Map.take(meta, ~w(query params result)a)

    field_hits =
      for {field, value} <- fields,
          matches = hits(:erlang.term_to_binary(value), markers),
          matches != [],
          into: %{},
          do: {field, matches}

    seen = %{
      event: Enum.join(event, "."),
      path: conn && conn.request_path,
      status: conn && conn.status,
      hits: hits(:erlang.term_to_binary({measurements, meta}), markers),
      fields: field_hits
    }

    send(pid, {:privacy_event, seen})
  end

  defp hits(bytes, markers) do
    matches =
      for {label, value} <- markers, :binary.match(bytes, value) != :nomatch, do: to_string(label)

    Enum.sort(matches)
  end

  defp drain(acc) do
    receive do
      {:privacy_event, event} -> drain([event | acc])
    after
      150 -> Enum.reverse(acc)
    end
  end
end
