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
      legacy_selection_controls!(c, auth, scope, descriptor, config)

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

    if live, do: browser_handoff!(live, c, scope, input)

    for _ <- 1..2 do
      selected = post(c, auth, @starters, payload)
      assert response_json!(selected, 200) == expected_receipt
      assert_input_row!(descriptor)
    end

    assert input_list(c, login(c), scope) == input_page(scope, [input])
    assert input_list(c, auth, other_project) == input_page(other_project, [])
    assert get(c, auth, @inputs, wrong_app).status == 404
    assert side_effect_rows() == baseline
    worker_admission = worker_accepts_persisted_input!(config, descriptor)

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

  @tag :android_starter
  test "Android starter selects one locked build input through the ordinary API", c do
    assert RuntimeOwner.status().phase == :storage_ready
    assert c.hosted.processor_profile == nil
    assert c.hosted.oban[:queues] == false

    auth = login(c)
    org = create(c, auth, "/console-api/v1/orgs", %{display_name: "Android starter owner"})
    scope = register_app(c, auth, org, "Android project")
    other = register_app(c, auth, org, "Other project")
    baseline = side_effect_rows()
    assert input_rows() == []
    assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)

    {descriptor, settings, scratch} = prepare_android_starter!(scope)
    %{"id" => id, "pin" => pin, "spec" => spec, "worker" => worker} = descriptor
    worker_pin = worker["configuration_sha256"]
    payload = Map.put(scope, :starter_id, id)

    assert post(c, auth, @starters, payload).status == 503
    [migration] = Path.wildcard("priv/local_android_source_selection/20261119000000_*.exs")
    [{module, _}] = Code.require_file(migration)
    assert :ok = Ecto.Migrator.up(Migration, 20_261_119_000_000, module, log: false)
    assert post(c, auth, @starters, payload).status == 404

    assert DB.q!(
             Migration,
             """
             INSERT INTO public.mixer_local_android_starters
               (organization_id, project_id, application_id, input_id, registration_pin,
                spec, worker_configuration_pin)
             VALUES ($1,$2,$3,$4,$5,$6,$7)
             """,
             [org, scope.project_id, scope.application_id, id, pin, spec, sha256("wrong worker")]
           ).num_rows == 1

    assert post(c, auth, @starters, payload).status == 404

    assert DB.q!(
             Migration,
             """
             UPDATE public.mixer_local_android_starters SET worker_configuration_pin=$2 WHERE input_id=$1
             """,
             [id, worker_pin]
           ).num_rows == 1

    assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", %{"id" => id})
    assert post(c, auth, @starters, Map.put(other, :starter_id, id)).status == 404
    assert post(c, auth, @starters, %{payload | starter_id: "unknown-starter"}).status == 404
    assert post(c, {elem(auth, 0), "invalid"}, @starters, payload).status == 403

    for field <- [:platform, :path, :command, :toolchain_lock_sha256] do
      assert post(c, auth, @starters, Map.put(payload, field, "untrusted")).status == 400
    end

    DB.q!(
      Admin,
      "UPDATE public.mixer_authz_memberships SET role='developer' WHERE organization_id=$1",
      [org]
    )

    try do
      assert post(c, auth, @starters, payload).status == 403
    after
      DB.q!(
        Admin,
        "UPDATE public.mixer_authz_memberships SET role='owner' WHERE organization_id=$1",
        [org]
      )
    end

    assert_sql_denied!(descriptor)
    assert input_rows() == []

    Application.put_env(:mixer_hosted, LocalStarter, %{
      settings
      | worker_sha256: sha256("wrong worker")
    })

    assert post(c, auth, @starters, payload).status == 404
    Application.put_env(:mixer_hosted, LocalStarter, settings)

    for relative <- [
          "export/mixer.lock",
          "export/Generated/MixerAndroid/android-build.py",
          "recipe.json",
          "mixer"
        ] do
      with_stale_file(Path.join(scratch, relative), fn ->
        assert post(c, auth, @starters, payload).status == 404
        assert input_rows() == []
      end)
    end

    input = %{
      "platform" => "android",
      "sourceInputId" => id,
      "sourceSha256" => spec["source"]["sha256"],
      "toolchainLockSha256" => spec["toolchain_lock_sha256"],
      "buildDefinitionSha256" => spec["build_definition_sha256"]
    }

    for _ <- 1..2 do
      assert response_json!(post(c, auth, @starters, payload), 200) ==
               Map.merge(public_scope(scope), input)

      assert_input_row!(descriptor)
    end

    assert input_list(c, login(c), scope) == input_page(scope, [input])
    assert input_list(c, auth, other) == input_page(other, [])
    assert side_effect_rows() == baseline

    DB.q!(
      Admin,
      "UPDATE public.mixer_customer_build_inputs SET source_reference='different' WHERE input_id=$1",
      [id]
    )

    assert post(c, auth, @starters, payload).status == 409
    assert [[_, _, _, "android", ^id, _, "different" | _]] = input_rows()

    DB.q!(
      Admin,
      "UPDATE public.mixer_customer_build_inputs SET source_reference=$2 WHERE input_id=$1",
      [id, spec["source"]["reference"]]
    )

    build =
      Map.merge(scope, %{
        platform: "android",
        source_input_id: id,
        source_sha256: input["sourceSha256"],
        toolchain_lock_sha256: input["toolchainLockSha256"],
        build_definition_sha256: input["buildDefinitionSha256"]
      })

    path = "/console-api/v1/builds"
    headers = [{"idempotency-key", "android-starter-build"}]
    assert post(c, auth, path, %{build | platform: "ios"}, headers).status == 404

    for field <- [:source_sha256, :toolchain_lock_sha256, :build_definition_sha256] do
      assert post(c, auth, path, Map.replace!(build, field, sha256("different")), headers).status ==
               409
    end

    assert %{"state" => "queued", "outcome" => "applied", "selection" => selection} =
             response_json!(post(c, auth, path, build, headers), 201)

    assert %{"state" => "queued", "selection" => ^selection} =
             response_json!(post(c, auth, path, build, headers), 200)

    assert Map.delete(selection, "build_id") ==
             build |> Map.delete(:source_input_id) |> stringify()

    effects = side_effect_rows()
    assert length(effects["mixer_builds"]) == 1
    assert length(effects["oban_jobs"]) == 1

    assert Map.drop(effects, ~w(mixer_builds oban_jobs)) ==
             Map.drop(baseline, ~w(mixer_builds oban_jobs))

    IO.puts(
      "ANDROID_STARTER_SELECTION " <>
        Jason.encode!(%{
          input: input,
          workerPin: worker_pin,
          source: spec["source"],
          fixture: "inert",
          queued: 1,
          jobs: 1,
          nativeStarts: 0
        })
    )
  end

  if System.get_env("MIXER_MANAGED_LINUX_PAIR25_STARTER_TEST") == "1" do
    @tag :managed_linux_pair25_starter
    test "managed Linux Starter authorizes and queues exactly one selected Pair25 input", c do
      auth = login(c)

      org =
        create(c, auth, "/console-api/v1/orgs", %{display_name: "Managed Linux Starter owner"})

      scope = register_app(c, auth, org, "Managed Linux project")
      other = register_app(c, auth, org, "Sibling project")
      viewer = %{organization_id: "org-a", project_id: "project-a", application_id: "fieldlog"}
      baseline = side_effect_rows()

      tree = sha256("Pair25 source")

      spec =
        Map.merge(stringify(scope), %{
          "platform" => "android",
          "source" => %{"kind" => "revision", "reference" => "starter-" <> tree, "sha256" => tree},
          "toolchain_lock_sha256" => sha256("Pair25 Linux lock"),
          "build_definition_sha256" => sha256("Pair25 Docker recipe")
        })

      profile = "managed-linux-pair25-v1"
      projection = sha256("Pair25 projection")
      driver = sha256("Pair25 rendered driver")

      manifest = %{
        "profile" => profile,
        "spec" => spec,
        "projection_sha256" => projection,
        "rendered_driver_sha256" => driver
      }

      raw = Jason.encode!(manifest)
      pin = sha256(raw)
      id = "starter-" <> pin
      payload = Map.put(scope, :starter_id, id)
      scratch = Path.join(System.tmp_dir!(), "managed-linux-starter")
      File.mkdir!(scratch)
      File.chmod!(scratch, 0o700)
      on_exit(fn -> remove_scratch!(scratch) end)
      path = Path.join(scratch, "manifest.json")
      write_read_only!(path, raw)

      env = %{
        "MIXER_LOCAL_STARTER_PROFILE" => profile,
        "MIXER_LOCAL_STARTER_ORGANIZATION" => org,
        "MIXER_LOCAL_STARTER_PROJECT" => scope.project_id,
        "MIXER_LOCAL_STARTER_APPLICATION" => scope.application_id,
        "MIXER_LOCAL_STARTER_REGISTRATION" => path,
        "MIXER_LOCAL_STARTER_SHA256" => pin
      }

      assert LocalStarter.runtime_config!(%{}) == nil

      for invalid <- [
            Map.delete(env, "MIXER_LOCAL_STARTER_PROFILE"),
            %{env | "MIXER_LOCAL_STARTER_PROFILE" => "unknown"},
            %{env | "MIXER_LOCAL_STARTER_REGISTRATION" => "relative.json"},
            Map.put(env, "MIXER_LOCAL_STARTER_WORKER_SHA256", sha256("unexpected worker"))
          ] do
        assert_raise ArgumentError, fn -> LocalStarter.runtime_config!(invalid) end
      end

      settings = LocalStarter.runtime_config!(env)
      Application.put_env(:mixer_hosted, LocalStarter, settings)
      on_exit(fn -> Application.delete_env(:mixer_hosted, LocalStarter) end)
      assert {:ok, %{id: ^id, pin: ^pin, spec: ^spec}} = LocalStarter.load(scope)

      duplicate = ~s({"profile":"#{profile}",) <> binary_part(raw, 1, byte_size(raw) - 1)

      for invalid <- [
            Jason.encode!(Map.put(manifest, "operation_id", "unexpected")),
            Jason.encode!(%{manifest | "rendered_driver_sha256" => "not-a-digest"}),
            Jason.encode!(%{manifest | "spec" => Map.put(spec, "build_id", "unexpected")}),
            Jason.encode!(put_in(manifest, ["spec", "source", "reference"], "different")),
            Jason.encode!(put_in(manifest, ["spec", "project_id"], other.project_id)),
            duplicate,
            raw <> String.duplicate(" ", 4096)
          ] do
        invalid_path = Path.join(scratch, "#{sha256(invalid)}.json")
        write_read_only!(invalid_path, invalid)

        Application.put_env(:mixer_hosted, LocalStarter, %{
          settings
          | path: invalid_path,
            sha256: sha256(invalid)
        })

        assert LocalStarter.load(scope) == {:error, :not_found}
      end

      symlink = Path.join(scratch, "linked.json")
      File.ln_s!(path, symlink)
      Application.put_env(:mixer_hosted, LocalStarter, %{settings | path: symlink})
      assert LocalStarter.load(scope) == {:error, :not_found}
      Application.put_env(:mixer_hosted, LocalStarter, settings)

      assert post(c, auth, @starters, payload).status == 503

      [migration] =
        Path.wildcard("priv/local_managed_linux_source_selection/20261120000000_*.exs")

      [{module, _}] = Code.require_file(migration)
      assert :ok = Ecto.Migrator.up(Migration, 20_261_120_000_000, module, log: false)

      unavailable = Map.put(public_scope(scope), "starter", nil)
      assert starter_list(c, auth, scope) == unavailable
      assert post(c, auth, @starters, payload).status == 404

      assert %{num_rows: 1} =
               DB.q!(
                 Migration,
                 """
                 INSERT INTO public.mixer_managed_linux_pair25_starters
                   (organization_id,project_id,application_id,input_id,registration_pin,spec,
                    projection_sha256,rendered_driver_sha256)
                 VALUES($1,$2,$3,$4,$5,$6,$7,$8)
                 """,
                 [org, scope.project_id, scope.application_id, id, pin, spec, projection, driver]
               )

      managed_catalog_mismatch!(c, auth, scope, payload, manifest, pin)

      assert starter_list(c, auth, scope) ==
               Map.put(public_scope(scope), "starter", %{"id" => id})

      assert starter_list(c, auth, other) == Map.put(public_scope(other), "starter", nil)
      assert post(c, auth, @starters, Map.put(other, :starter_id, id)).status == 404
      assert post(c, auth, @starters, Map.put(viewer, :starter_id, id)).status == 403
      assert post(c, auth, @starters, %{payload | starter_id: "unprovisioned"}).status == 404

      assert post(c, auth, @starters, Map.put(payload, :projection_sha256, projection)).status ==
               400

      assert post(c, {elem(auth, 0), String.duplicate("A", 43)}, @starters, payload).status == 403

      membership = "UPDATE public.mixer_authz_memberships SET role=$2 WHERE organization_id=$1"
      DB.q!(Admin, membership, [org, "developer"])
      assert post(c, auth, @starters, payload).status == 403
      DB.q!(Admin, membership, [org, "owner"])

      with_stale_file(path, fn ->
        assert starter_list(c, auth, scope) == unavailable
        assert post(c, auth, @starters, payload).status == 404
      end)

      call = "SELECT public.mixer_managed_linux_pair25_starter_v1($1,$2,$3,true,$4,$5)"
      params = [id, pin, spec, projection, driver]

      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Ecto.Adapters.SQL.query(MixerHosted.Repo, call, params)

      assert {:ok, %{rows: [["denied"]]}} = Ecto.Adapters.SQL.query(CreateRepo, call, params)

      assert {:ok, :conflict} =
               Admin.transaction(fn ->
                 DB.q!(
                   Admin,
                   """
                   SELECT pg_advisory_xact_lock(hashtextextended(
                     jsonb_build_array('mixer-local-starter-v1',$1::text,$2::text,$3::text)::text,0))
                   """,
                   [org, scope.project_id, scope.application_id]
                 )

                 assert post(c, auth, @starters, payload).status == 409
                 :conflict
               end)

      assert input_rows() == []
      assert side_effect_rows() == baseline

      selected = response_json!(post(c, auth, @starters, payload), 200)
      assert response_json!(post(c, auth, @starters, payload), 200) == selected
      assert_input_row!(%{"id" => id, "spec" => spec}, 1_200_000)

      assert selected ==
               Map.merge(public_scope(scope), %{
                 "platform" => "android",
                 "sourceInputId" => id,
                 "sourceSha256" => tree,
                 "toolchainLockSha256" => spec["toolchain_lock_sha256"],
                 "buildDefinitionSha256" => spec["build_definition_sha256"]
               })

      input = Map.drop(selected, Map.keys(public_scope(scope)))
      assert input_list(c, auth, scope) == input_page(scope, [input])
      assert input_list(c, auth, other) == input_page(other, [])

      update = "UPDATE public.mixer_customer_build_inputs SET timeout_ms=$2 WHERE input_id=$1"
      assert %{num_rows: 1} = DB.q!(Admin, update, [id, 1_800_000])
      assert post(c, auth, @starters, payload).status == 409
      assert_input_row!(%{"id" => id, "spec" => spec})
      assert %{num_rows: 1} = DB.q!(Admin, update, [id, 1_200_000])

      body = Map.new(selected, fn {key, value} -> {Macro.underscore(key), value} end)
      headers = [{"idempotency-key", "managed-linux-starter"}]
      builds = "/console-api/v1/builds"

      assert post(c, auth, builds, %{body | "source_sha256" => sha256("different")}, headers).status ==
               409

      assert %{
               "state" => "queued",
               "revision" => 0,
               "outcome" => "applied",
               "selection" => selection
             } =
               response_json!(post(c, auth, builds, body, headers), 201)

      assert %{"state" => "queued", "revision" => 0, "selection" => ^selection} =
               response_json!(post(c, auth, builds, body, headers), 200)

      assert Map.delete(selection, "build_id") == Map.delete(body, "source_input_id")
      assert_input_row!(%{"id" => id, "spec" => spec}, 1_200_000)

      effects = side_effect_rows()
      assert [[%{"build_id" => build_id, "revision" => 0}]] = effects["mixer_builds"]
      assert build_id == selection["build_id"]

      assert [
               [
                 %{
                   "queue" => "builds",
                   "state" => "available",
                   "args" => %{"build_id" => ^build_id}
                 }
               ]
             ] =
               effects["oban_jobs"]

      assert Map.drop(effects, ~w(mixer_builds oban_jobs)) ==
               Map.drop(baseline, ~w(mixer_builds oban_jobs))
    end

    defp managed_catalog_mismatch!(c, auth, scope, payload, manifest, pin) do
      unavailable = Map.put(public_scope(scope), "starter", nil)
      wrong_pin = sha256("different registration")

      change_pin = """
      UPDATE public.mixer_managed_linux_pair25_starters
      SET registration_pin=$2, input_id='starter-' || $2 WHERE registration_pin=$1
      """

      assert %{num_rows: 1} = DB.q!(Migration, change_pin, [pin, wrong_pin])
      assert starter_list(c, auth, scope) == unavailable
      assert post(c, auth, @starters, payload).status == 404
      assert %{num_rows: 1} = DB.q!(Migration, change_pin, [wrong_pin, pin])

      spec = manifest["spec"]

      for {column, wrong} <- [
            {"spec", %{spec | "toolchain_lock_sha256" => sha256("different lock")}},
            {"projection_sha256", sha256("different projection")},
            {"rendered_driver_sha256", sha256("different driver")}
          ] do
        sql =
          "UPDATE public.mixer_managed_linux_pair25_starters SET #{column}=$2 WHERE input_id=$1"

        assert %{num_rows: 1} = DB.q!(Migration, sql, [payload.starter_id, wrong])
        assert starter_list(c, auth, scope) == unavailable
        assert post(c, auth, @starters, payload).status == 404
        assert %{num_rows: 1} = DB.q!(Migration, sql, [payload.starter_id, manifest[column]])
      end
    end
  end

  defp prepare_android_starter!(scope) do
    scratch = Path.join(System.tmp_dir!(), "android-starter")
    File.mkdir!(scratch)
    File.chmod!(scratch, 0o700)
    on_exit(fn -> remove_scratch!(scratch) end)
    Application.delete_env(:mixer_hosted, LocalStarter)
    on_exit(fn -> Application.delete_env(:mixer_hosted, LocalStarter) end)

    tools = Path.expand("../tests/integration/free-project-starter")
    port = "41769"

    {startup_pin, 0} =
      System.cmd("python3", [
        "-B",
        Path.join(tools, "android-selection-fixture.py"),
        scratch,
        scope.organization_id,
        scope.project_id,
        scope.application_id,
        port
      ])

    path = Path.join(scratch, "descriptor.json")
    startup = Path.join(scratch, "worker.json")
    pin = String.trim(startup_pin)

    {output, 0} =
      System.cmd(
        "python3",
        [
          "-B",
          Path.join(tools, "prepare-starter.py"),
          "--from-worker",
          path,
          startup,
          pin,
          "local-android-selection-fixture",
          port
        ],
        stderr_to_stdout: true
      )

    descriptor = Jason.decode!(output)
    refute Map.has_key?(Jason.decode!(File.read!(path)), "token")
    assert descriptor["pin"] == sha256(File.read!(path))
    assert descriptor["worker"]["configuration_sha256"] == sha256(File.read!(startup))

    settings =
      LocalStarter.runtime_config!(%{
        "MIXER_LOCAL_STARTER_ORGANIZATION" => scope.organization_id,
        "MIXER_LOCAL_STARTER_PROJECT" => scope.project_id,
        "MIXER_LOCAL_STARTER_APPLICATION" => scope.application_id,
        "MIXER_LOCAL_STARTER_REGISTRATION" => path,
        "MIXER_LOCAL_STARTER_SHA256" => descriptor["pin"],
        "MIXER_LOCAL_STARTER_WORKER_SHA256" => pin
      })

    Application.put_env(:mixer_hosted, LocalStarter, settings)
    {descriptor, settings, scratch}
  end

  defp legacy_selection_controls!(c, auth, scope, current, config) do
    settings = Application.fetch_env!(:mixer_hosted, LocalStarter)
    legacy_dir = Path.join(Path.dirname(config), "legacy")
    File.mkdir!(legacy_dir)
    legacy_config = Path.join(legacy_dir, "registration.json")
    startup_path = Path.rootname(config) <> ".worker-startup.json"
    startup = Jason.decode!(File.read!(startup_path))
    descriptor = Jason.decode!(File.read!(config))
    recipe = Jason.decode!(File.read!(startup["registration"]["recipe"]))
    key = "starter_package_closure"

    legacy_recipe =
      recipe
      |> Map.delete(key)
      |> Map.update!("inputs", &Map.take(&1, ["mixer.lock"]))

    legacy_policy =
      startup["policy"] |> Map.delete(key) |> Map.put("inputs", legacy_recipe["inputs"])

    legacy_recipe_path = Path.join(legacy_dir, "legacy-recipe.json")
    recipe_bytes = Jason.encode!(legacy_recipe)
    write_read_only!(legacy_recipe_path, recipe_bytes)
    definition = sha256(recipe_bytes)
    legacy_spec = Map.put(current["spec"], "build_definition_sha256", definition)

    registration =
      startup["registration"]
      |> Map.merge(%{"recipe" => legacy_recipe_path, "spec" => legacy_spec})

    {:ok, listener} = :gen_tcp.listen(0, ip: {127, 0, 0, 1})
    {:ok, port} = :inet.port(listener)
    :ok = :gen_tcp.close(listener)
    refute port == startup["port"]

    startup =
      Map.merge(startup, %{
        "port" => port,
        "registration" => registration,
        "policy" => Map.put(legacy_policy, "recipe_sha256", definition)
      })

    startup_bytes = Jason.encode!(startup)
    startup_pin = sha256(startup_bytes)
    legacy_startup = Path.rootname(legacy_config) <> ".worker-startup.json"
    write_read_only!(legacy_startup, startup_bytes)

    worker =
      Map.merge(descriptor["worker"], %{"configuration_sha256" => startup_pin, "port" => port})

    bytes =
      startup
      |> Map.take(~w(tenant registration policy))
      |> Map.put("worker", worker)
      |> Jason.encode!()

    write_read_only!(legacy_config, bytes)
    pin = sha256(bytes)
    id = "starter-" <> pin
    legacy = %{"id" => id, "pin" => pin, "spec" => legacy_spec, "worker" => worker}
    payload = Map.put(scope, :starter_id, id)

    {operator_result, status} =
      System.cmd(
        "python3",
        [
          "-B",
          System.fetch_env!("MIXER_STARTER_PREPARE"),
          "--from-worker",
          Path.join(legacy_dir, "new-descriptor.json"),
          legacy_startup,
          startup_pin,
          worker["id"],
          to_string(worker["port"])
        ],
        stderr_to_stdout: true
      )

    assert status != 0
    assert operator_result =~ "starter package closure is required"

    try do
      replace_catalog!(legacy)

      Application.put_env(:mixer_hosted, LocalStarter, %{
        settings
        | path: legacy_config,
          sha256: pin,
          worker_sha256: startup_pin
      })

      assert {:ok, %{local_closure?: false}} = LocalStarter.load(scope)
      assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)
      assert post(c, auth, @starters, payload).status == 404
      assert input_rows() == []

      source = legacy_spec["source"]

      assert DB.q!(
               Admin,
               """
               INSERT INTO public.mixer_customer_build_inputs
                 (organization_id,project_id,application_id,platform,input_id,source_kind,source_reference,
                  source_sha256,toolchain_lock_sha256,build_definition_sha256,max_attempts,timeout_ms,retry_backoff_ms)
               VALUES ($1,$2,$3,'ios',$4,$5,$6,$7,$8,$9,1,1800000,0)
               """,
               [
                 scope.organization_id,
                 scope.project_id,
                 scope.application_id,
                 id,
                 source["kind"],
                 source["reference"],
                 source["sha256"],
                 legacy_spec["toolchain_lock_sha256"],
                 definition
               ]
             ).num_rows == 1

      assert starter_list(c, auth, scope) ==
               Map.put(public_scope(scope), "starter", %{"id" => id})

      assert %{"inputs" => [%{"sourceInputId" => ^id}]} = input_list(c, auth, scope)

      first = response_json!(post(c, auth, @starters, payload), 200)
      assert first["sourceInputId"] == id
      assert first == response_json!(post(c, auth, @starters, payload), 200)
      assert_input_row!(legacy)
      assert worker_accepts_persisted_input!(legacy_config, legacy)["starts"] == 0

      assert DB.q!(
               Admin,
               """
               UPDATE public.mixer_customer_build_inputs SET source_reference='different-reference'
               WHERE input_id=$1
               """,
               [id]
             ).num_rows == 1

      assert starter_list(c, auth, scope) == Map.put(public_scope(scope), "starter", nil)
      assert post(c, auth, @starters, payload).status == 409
      assert [[_, _, _, _, ^id, _, "different-reference" | _]] = input_rows()
    after
      DB.q!(Admin, "DELETE FROM public.mixer_customer_build_inputs WHERE input_id=$1", [id])
      replace_catalog!(current)
      Application.put_env(:mixer_hosted, LocalStarter, settings)
    end
  end

  defp replace_catalog!(%{"id" => id, "pin" => pin, "spec" => spec}) do
    assert DB.q!(
             Migration,
             "UPDATE public.mixer_local_starters SET input_id=$1, registration_pin=$2, spec=$3",
             [id, pin, spec]
           ).num_rows == 1
  end

  defp write_read_only!(path, bytes) do
    File.write!(path, bytes, [:exclusive])
    File.chmod!(path, 0o400)
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

  defp assert_sql_denied!(%{"id" => id, "pin" => pin, "spec" => spec, "worker" => worker}) do
    {execute, params} =
      case spec["platform"] do
        "android" ->
          {"SELECT public.mixer_local_android_starter_v1($1, $2, $3, true, $4)",
           [id, pin, spec, worker["configuration_sha256"]]}

        "ios" ->
          {"SELECT public.mixer_local_starter_v1($1, $2, $3, true)", [id, pin, spec]}
      end

    write = "UPDATE public.mixer_customer_build_inputs SET source_reference = 'outside-command'"

    privilege =
      "SELECT has_table_privilege(current_user,'public.mixer_customer_build_inputs','INSERT'), " <>
        "has_any_column_privilege(current_user,'public.mixer_customer_build_inputs','INSERT')"

    for repo <- [MixerHosted.Repo, CreateRepo] do
      assert {:ok, %{rows: [[false, false]]}} = Ecto.Adapters.SQL.query(repo, privilege, [])

      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Ecto.Adapters.SQL.query(repo, write, [])

      if spec["platform"] == "android" do
        for query <- [
              "SELECT worker_configuration_pin FROM public.mixer_local_android_starters",
              "INSERT INTO public.mixer_local_android_starters DEFAULT VALUES",
              "INSERT INTO public.mixer_customer_build_inputs DEFAULT VALUES"
            ] do
          assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
                   Ecto.Adapters.SQL.query(repo, query, [])
        end
      end
    end

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(MixerHosted.Repo, execute, params)

    assert {:ok, %{rows: [["denied"]]}} =
             Ecto.Adapters.SQL.query(CreateRepo, execute, params)
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

  defp assert_input_row!(%{"id" => id, "spec" => spec}, timeout_ms \\ 1_800_000) do
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
               timeout_ms,
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

  defp post(c, {cookie, csrf}, path, body, extra_headers \\ []) do
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
        ] ++ extra_headers,
      "POST",
      raw
    )
  end
end
