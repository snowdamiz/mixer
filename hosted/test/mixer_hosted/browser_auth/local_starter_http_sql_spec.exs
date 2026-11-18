Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.LocalStarterHTTPSQLTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.BrowserAuth.{ActiveWorkspaceSchema, RuntimeOwner}
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.CustomerWorkspace.{SelfServiceSchema, SupportSchema}
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB

  alias MixerHosted.CustomerBuilds.{CreateRepo, LocalStarter}

  @apps "/console-api/v1/applications"
  @starters "/console-api/v1/source-starters"
  @inputs "/console-api/v1/build-inputs"
  @test_app "example.source.app"

  setup_all do
    c = prepare!(:workspace_builds)

    for version <- [
          20_261_025_000_001,
          20_261_025_000_002,
          20_261_116_000_001,
          20_261_117_000_000,
          20_261_118_000_000,
          20_261_118_000_002,
          20_261_118_000_010
        ],
        do: migrate(Migration, version)

    conn = DB.connection!("browser_admin")

    try do
      for sql <-
            SelfServiceSchema.provisioning_statements("browser_ordinary") ++
              ActiveWorkspaceSchema.provisioning_statements("browser_ordinary") do
        Postgrex.query!(conn, sql, [])
      end
    after
      GenServer.stop(conn)
    end

    DB.q!(
      Migration,
      "REVOKE EXECUTE ON FUNCTION public.mixer_billing_organization_sync() FROM PUBLIC"
    )

    DB.q!(Migration, SupportSchema.grant_statement("browser_ordinary"))
    migrate(Admin, 20_261_118_000_011)
    install_create_surface()

    [path] = Path.wildcard("priv/local_source_selection/20261118000012_*.exs")
    [{module, _}] = Code.require_file(path)
    assert :ok = Ecto.Migrator.up(Migration, 20_261_118_000_012, module, log: false)

    c
    |> put_in(
      [:hosted, Access.key(:create_repo)],
      Keyword.put(c.hosted.repo, :username, "mixer_build_create")
    )
    |> start!()
  end

  @tag timeout: 250_000
  test "owner selects the operator-pinned export through HTTP and commits exactly one input", c do
    assert RuntimeOwner.status().phase == :storage_ready
    assert c.hosted.processor_profile == nil
    assert c.hosted.oban[:queues] == false

    live = System.get_env("MIXER_STARTER_LIVE")
    auth = login(c)
    org = create(c, auth, "/console-api/v1/orgs", %{display_name: "Local starter HTTP owner"})
    scope = register_app(c, auth, org, "Starter project")
    other_project = register_app(c, auth, org, "Other project with the same app")
    wrong_app = %{scope | application_id: "example.other.app"}
    viewer = %{organization_id: "org-a", project_id: "project-a", application_id: "fieldlog"}

    baseline = side_effect_rows()
    assert baseline["mixer_builds"] == []
    assert baseline["oban_jobs"] == []
    assert baseline["mixer_build_reservations"] == []
    assert input_rows() == []
    assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)

    {export, descriptor, config, cli} = prepare_starter!(scope)
    %{"id" => id, "pin" => pin, "spec" => spec} = descriptor
    payload = Map.put(scope, :starter_id, id)

    assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)
    assert post(c, auth, @starters, payload).status == 404
    assert input_rows() == []

    assert DB.q!(
             Migration,
             """
             INSERT INTO public.mixer_local_starters
               (organization_id, project_id, application_id, input_id, registration_pin, spec)
             VALUES ($1, $2, $3, $4, $5, $6)
             """,
             [scope.organization_id, scope.project_id, scope.application_id, id, pin, spec]
           ).num_rows == 1

    assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", %{"id" => id})

    unless live do
      assert starter_list(c, auth, other_project) ==
               Map.put(public_scope(other_project), "starter", nil)

      assert get(c, auth, @starters, wrong_app).status == 404
      assert get(c, auth, @starters, viewer).status == 403

      for rejected_scope <- [other_project, wrong_app] do
        assert post(c, auth, @starters, Map.put(rejected_scope, :starter_id, id)).status == 404
      end

      assert post(c, auth, @starters, Map.put(viewer, :starter_id, id)).status == 403

      assert post(c, auth, @starters, %{payload | starter_id: "unprovisioned-starter"}).status ==
               404

      assert post(c, {elem(auth, 0), String.duplicate("A", 43)}, @starters, payload).status == 403

      for {key, value} <- [
            {:path, "/fixture/arbitrary-source"},
            {:source_sha256, String.duplicate("a", 64)},
            {:command, ["fixture-command"]}
          ] do
        assert post(c, auth, @starters, Map.put(payload, key, value)).status == 400
      end

      assert_sql_denied!(descriptor)
      assert input_rows() == []
      assert input_list(c, auth, scope) == input_page(scope, [])

      with_stale_file(Path.join(export, "mixer.lock"), fn ->
        assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)
        assert post(c, auth, @starters, payload).status == 404
        assert input_rows() == []
      end)

      with_stale_file(cli, fn ->
        assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)
        assert post(c, auth, @starters, payload).status == 404
        assert input_rows() == []
      end)

      with_replaced_registration(scope, export, config, cli, descriptor, fn replacement, status ->
        assert replacement["spec"]["source"]["sha256"] == spec["source"]["sha256"]
        refute replacement["id"] == id

        case status do
          :wrong_worker ->
            assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)

            assert post(c, auth, @starters, %{payload | starter_id: replacement["id"]}).status ==
                     404

          :current_worker ->
            assert starter_list(c, auth, scope) ==
                     Map.put(public_scope(scope), "starter", %{"id" => replacement["id"]})

            assert post(c, auth, @starters, payload).status == 404
        end

        assert input_rows() == []
      end)

      assert starter_list(c, auth, scope) ==
               Map.put(public_scope(scope), "starter", %{"id" => id})

      assert side_effect_rows() == baseline
    end

    input = %{
      "sourceInputId" => id,
      "platform" => spec["platform"],
      "sourceSha256" => spec["source"]["sha256"],
      "toolchainLockSha256" => spec["toolchain_lock_sha256"],
      "buildDefinitionSha256" => spec["build_definition_sha256"]
    }

    assert input["platform"] == "ios"
    expected_receipt = Map.merge(public_scope(scope), input)

    worker_admission =
      if live do
        browser_handoff!(live, c, scope, input)
        assert_input_row!(descriptor)
        assert input_list(c, login(c), scope) == input_page(scope, [input])
        worker_accepts_persisted_input!(config, descriptor)
      end

    for _ <- 1..2 do
      selected = post(c, auth, @starters, payload)
      assert response_json!(selected, 200) == expected_receipt
      assert_input_row!(descriptor)
    end

    assert input_list(c, login(c), scope) == input_page(scope, [input])
    assert input_list(c, auth, other_project) == input_page(other_project, [])
    assert get(c, auth, @inputs, wrong_app).status == 404
    assert side_effect_rows() == baseline

    IO.puts(
      "SOURCE_SELECTION_EVIDENCE " <>
        Jason.encode!(%{
          spec: spec,
          starterId: id,
          registrationPin: pin,
          worker: descriptor["worker"],
          workerAdmission: worker_admission,
          files: descriptor["files"],
          sourceBytes: descriptor["source_bytes"],
          persistedInputs: 1,
          buildRows: 0,
          obanJobs: 0,
          capacityReservations: 0,
          billingRowsUnchanged: true,
          mode: if(live, do: "browser-first", else: "http-controls")
        })
    )
  end

  defp register_app(c, auth, org, name) do
    project =
      create(c, auth, "/console-api/v1/projects", %{organization_id: org, display_name: name})

    scope = %{organization_id: org, project_id: project, application_id: @test_app}
    registered = post(c, auth, @apps, scope)
    assert response_json!(registered, 201) == stringify(scope)
    scope
  end

  defp prepare_starter!(scope) do
    proof_root = System.fetch_env!("MIXER_STARTER_PROOF_ROOT") |> Path.expand()
    fixture_export = System.fetch_env!("MIXER_STARTER_EXPORT")
    prepare_script = System.fetch_env!("MIXER_STARTER_PREPARE")
    cli = System.get_env("MIXER_STARTER_CLI", Path.join(proof_root, "cli-build/debug/mixer"))
    unique = Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false)
    scratch = Path.join(proof_root, "starter-proof-" <> unique)
    File.mkdir!(scratch)
    on_exit(fn -> remove_scratch!(scratch) end)
    File.chmod!(scratch, 0o700)

    export = Path.join(scratch, "exported-starter")
    File.cp_r!(fixture_export, export)
    config = Path.join(scratch, "registration.json")
    local_cli = Path.join(scratch, "mixer")
    File.cp!(cli, local_cli)
    File.chmod!(local_cli, 0o500)

    {output, status} =
      System.cmd(
        "python3",
        [
          prepare_script,
          config,
          export,
          local_cli,
          scope.organization_id,
          scope.project_id,
          scope.application_id
        ],
        env: [{"PYTHONDONTWRITEBYTECODE", "1"}],
        stderr_to_stdout: true
      )

    assert status == 0, output
    descriptor = Jason.decode!(output)
    assert %{"id" => id, "pin" => pin, "spec" => spec} = descriptor
    assert descriptor["files"] > 0
    assert %File.Stat{type: :regular, mode: mode} = File.lstat!(config)
    assert Bitwise.band(mode, 0o777) == 0o400
    assert pin == sha256(File.read!(config))
    assert id == "starter-" <> pin
    worker_startup = File.read!(Path.rootname(config) <> ".worker-startup.json")
    assert descriptor["worker"]["configuration_sha256"] == sha256(worker_startup)

    assert %{
             "worker_id" => worker_id,
             "port" => worker_port,
             "registration" => %{"spec" => ^spec}
           } =
             Jason.decode!(worker_startup)

    assert {descriptor["worker"]["id"], descriptor["worker"]["port"]} == {worker_id, worker_port}
    assert worker_id == System.fetch_env!("MIXER_STARTER_DISPATCH_ID")
    assert worker_port == String.to_integer(System.fetch_env!("MIXER_STARTER_DISPATCH_PORT"))
    refute Map.has_key?(Jason.decode!(File.read!(config)), "token")
    assert spec["source"]["reference"] == "starter-" <> spec["source"]["sha256"]
    assert Map.take(spec, Map.keys(stringify(scope))) == stringify(scope)
    assert spec["toolchain_lock_sha256"] == sha256(File.read!(Path.join(export, "mixer.lock")))
    recipe = Path.rootname(config) <> ".recipe.json"
    assert spec["build_definition_sha256"] == sha256(File.read!(recipe))

    previous = Application.fetch_env(:mixer_hosted, LocalStarter)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, LocalStarter, value)
        :error -> Application.delete_env(:mixer_hosted, LocalStarter)
      end
    end)

    settings =
      LocalStarter.runtime_config!(%{
        "MIXER_LOCAL_STARTER_ORGANIZATION" => scope.organization_id,
        "MIXER_LOCAL_STARTER_PROJECT" => scope.project_id,
        "MIXER_LOCAL_STARTER_APPLICATION" => scope.application_id,
        "MIXER_LOCAL_STARTER_REGISTRATION" => config,
        "MIXER_LOCAL_STARTER_SHA256" => pin,
        "MIXER_LOCAL_STARTER_WORKER_SHA256" => descriptor["worker"]["configuration_sha256"]
      })

    Application.put_env(:mixer_hosted, LocalStarter, settings)
    {export, descriptor, config, local_cli}
  end

  defp with_replaced_registration(scope, export, config, cli, original, exercise) do
    altered = Path.join(Path.dirname(config), "replacement.json")
    prepare = System.fetch_env!("MIXER_STARTER_PREPARE")

    {output, status} =
      System.cmd(
        "python3",
        [
          prepare,
          altered,
          export,
          cli,
          scope.organization_id,
          scope.project_id,
          scope.application_id
        ],
        env: [{"MIXER_STARTER_SOURCE_REFERENCE", "revised-source-reference"}],
        stderr_to_stdout: true
      )

    assert status == 0, output
    replacement = Jason.decode!(output)
    settings = Application.fetch_env!(:mixer_hosted, LocalStarter)

    update = fn value ->
      assert DB.q!(
               Migration,
               """
               UPDATE public.mixer_local_starters SET input_id=$1, registration_pin=$2, spec=$3
               """,
               [value["id"], value["pin"], value["spec"]]
             ).num_rows == 1
    end

    try do
      update.(replacement)

      Application.put_env(:mixer_hosted, LocalStarter, %{
        settings
        | path: altered,
          sha256: replacement["pin"]
      })

      exercise.(replacement, :wrong_worker)

      Application.put_env(:mixer_hosted, LocalStarter, %{
        Application.fetch_env!(:mixer_hosted, LocalStarter)
        | worker_sha256: replacement["worker"]["configuration_sha256"]
      })

      exercise.(replacement, :current_worker)
    after
      update.(original)
      Application.put_env(:mixer_hosted, LocalStarter, settings)
    end
  end

  defp remove_scratch!(directory) do
    File.chmod!(directory, 0o700)

    for name <- File.ls!(directory) do
      path = Path.join(directory, name)

      case File.lstat!(path).type do
        :directory -> remove_scratch!(path)
        _ -> File.rm!(path)
      end
    end

    File.rmdir!(directory)
  end

  defp sha256(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  defp with_stale_file(path, exercise) do
    mode = File.lstat!(path).mode |> Bitwise.band(0o777)
    original = File.read!(path)
    File.chmod!(path, 0o600)

    try do
      File.write!(path, original <> "\n")
      File.chmod!(path, mode)
      exercise.()
    after
      File.chmod!(path, 0o600)
      File.write!(path, original)
      File.chmod!(path, mode)
    end
  end

  defp assert_sql_denied!(%{"id" => id, "pin" => pin, "spec" => spec}) do
    execute = "SELECT public.mixer_local_starter_v1($1, $2, $3, true)"
    write = "UPDATE public.mixer_customer_build_inputs SET source_reference = 'outside-command'"

    privilege =
      "SELECT has_table_privilege(current_user,'public.mixer_customer_build_inputs','INSERT'), " <>
        "has_any_column_privilege(current_user,'public.mixer_customer_build_inputs','INSERT')"

    for repo <- [MixerHosted.Repo, CreateRepo] do
      assert {:ok, %{rows: [[false, false]]}} = Ecto.Adapters.SQL.query(repo, privilege, [])

      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Ecto.Adapters.SQL.query(repo, write, [])
    end

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(MixerHosted.Repo, execute, [id, pin, spec])

    assert {:ok, %{rows: [["denied"]]}} =
             Ecto.Adapters.SQL.query(CreateRepo, execute, [id, pin, spec])
  end

  defp input_rows do
    DB.q!(
      Admin,
      """
      SELECT organization_id, project_id, application_id, platform, input_id,
             source_kind, source_reference, source_sha256, toolchain_lock_sha256,
             build_definition_sha256, max_attempts, timeout_ms, retry_backoff_ms
      FROM public.mixer_customer_build_inputs
      """
    ).rows
  end

  defp worker_accepts_persisted_input!(config, descriptor) do
    [[org, project, app, platform, _, kind, reference, source, lock, definition, _, _, _]] =
      input_rows()

    persisted_spec = %{
      organization_id: org,
      project_id: project,
      application_id: app,
      platform: platform,
      source: %{kind: kind, reference: reference, sha256: source},
      toolchain_lock_sha256: lock,
      build_definition_sha256: definition
    }

    {output, 0} =
      System.cmd(
        "python3",
        [
          "-B",
          System.fetch_env!("MIXER_STARTER_WORKER_PROOF"),
          Path.rootname(config) <> ".worker-startup.json",
          descriptor["worker"]["configuration_sha256"],
          Jason.encode!(persisted_spec)
        ],
        stderr_to_stdout: true
      )

    evidence = Jason.decode!(output)
    assert %{"workerId" => id, "sourceSha256" => ^source, "starts" => 0} = evidence
    assert id == descriptor["worker"]["id"]
    evidence
  end

  defp assert_input_row!(%{"id" => id, "spec" => spec}) do
    assert input_rows() == [
             [
               spec["organization_id"],
               spec["project_id"],
               spec["application_id"],
               spec["platform"],
               id,
               spec["source"]["kind"],
               spec["source"]["reference"],
               spec["source"]["sha256"],
               spec["toolchain_lock_sha256"],
               spec["build_definition_sha256"],
               1,
               1_800_000,
               0
             ]
           ]
  end

  defp side_effect_rows do
    billing =
      DB.q!(
        Admin,
        """
        SELECT tablename::text FROM pg_tables
        WHERE schemaname = 'public' AND starts_with(tablename::text, 'mixer_billing_')
        ORDER BY tablename
        """
      ).rows
      |> List.flatten()

    assert "mixer_billing_organization_state" in billing

    Map.new(~w(mixer_builds oban_jobs mixer_build_reservations) ++ billing, fn table ->
      assert table =~ ~r/\A[a-z_]+\z/
      rows = DB.q!(Admin, "SELECT to_jsonb(t) FROM public.#{table} AS t ORDER BY 1").rows
      {table, rows}
    end)
  end

  defp public_scope(scope) do
    %{
      "organizationId" => scope.organization_id,
      "projectId" => scope.project_id,
      "applicationId" => scope.application_id
    }
  end

  defp stringify(map), do: Map.new(map, fn {key, value} -> {Atom.to_string(key), value} end)

  defp get(c, {cookie, _csrf}, path, scope) do
    http(c, path <> "?" <> URI.encode_query(scope), headers(cookie))
  end

  defp response_json!(response, status) do
    assert response.status == status, response.body
    assert response_header(response, "cache-control") == ["no-store"]
    Jason.decode!(response.body)
  end

  defp starter_list(c, auth, scope), do: response_json!(get(c, auth, @starters, scope), 200)
  defp input_list(c, auth, scope), do: response_json!(get(c, auth, @inputs, scope), 200)

  defp input_page(scope, inputs) do
    Map.merge(public_scope(scope), %{"inputs" => inputs, "nextCursor" => nil})
  end

  defp browser_handoff!(path, c, scope, input) do
    refute File.exists?(path)
    refute File.exists?(path <> ".complete")

    payload = %{
      phoenix: c.http_port,
      cookie: elem(login(c), 0),
      org: scope.organization_id,
      project: scope.project_id,
      app: scope.application_id,
      starterId: input["sourceInputId"],
      sourceSha256: input["sourceSha256"]
    }

    pending = path <> ".new"

    File.open!(pending, [:write, :exclusive], fn io ->
      on_exit(fn -> File.rm(pending) end)
      File.chmod!(pending, 0o600)
      assert :ok = IO.binwrite(io, Jason.encode!(payload))
    end)

    File.rename!(pending, path)
    on_exit(fn -> File.rm(path) end)
    wait_for_browser!(path <> ".complete", System.monotonic_time(:millisecond) + 180_000)
  end

  defp wait_for_browser!(marker, deadline) do
    unless File.regular?(marker) do
      assert System.monotonic_time(:millisecond) < deadline, "browser proof did not finish"
      Process.sleep(250)
      wait_for_browser!(marker, deadline)
    end
  end

  defp migrate(repo, version) do
    [path] = Path.wildcard("priv/repo/migrations/#{version}_*.exs")
    [{module, _}] = Code.require_file(path)
    assert :ok = Ecto.Migrator.up(repo, version, module, log: false)
  end

  defp install_create_surface do
    DB.q!(Admin, "GRANT USAGE ON SCHEMA public TO mixer_build_create")

    tables =
      ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)

    relations = Enum.map_join(tables, ",", &("public.mixer_authz_" <> &1))
    DB.q!(Admin, "GRANT SELECT ON " <> relations <> " TO mixer_build_create")

    for helper <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          DB.q!(
            Admin,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO mixer_build_create"
          )

    for sql <-
          MixerHosted.CustomerBuilds.CreateSchema.statements() ++
            MixerHosted.BrowserAuth.ActiveCreateSchema.statements(),
        do: DB.q!(Migration, sql)

    signature =
      "public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence)"

    DB.q!(Admin, "GRANT CREATE ON SCHEMA public TO browser_writer")
    DB.q!(Admin, "ALTER FUNCTION #{signature} OWNER TO browser_writer")
    DB.q!(Admin, "REVOKE CREATE ON SCHEMA public FROM browser_writer")
    DB.q!(Admin, "GRANT EXECUTE ON FUNCTION #{signature} TO mixer_build_create")
  end

  defp login(c) do
    attempt = begin_http(c, bootstrap_http(c))
    callback = http(c, "/auth/callback?" <> attempt.query, attempt.headers)
    assert callback.status == 303
    cookie = response_cookie(callback)
    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    {cookie, Jason.decode!(session.body)["csrf_token"]}
  end

  defp create(c, auth, path, body) do
    result = post(c, auth, path, body)
    response_json!(result, 201)["id"]
  end

  defp post(c, {cookie, csrf}, path, body) do
    raw = Jason.encode!(body)

    http(
      c,
      path,
      headers(cookie) ++
        [
          {"origin", c.config.public_origin},
          {"x-mixer-csrf", csrf},
          {"content-type", "application/json"},
          {"content-length", Integer.to_string(byte_size(raw))}
        ],
      "POST",
      raw
    )
  end
end
