Code.require_file("../test/mixer_hosted/browser_auth/storage_fixture.exs", __DIR__)

defmodule MixerHosted.OrdinaryBuildCancelPGTest do
  use ExUnit.Case, async: false
  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: F
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}

  alias MixerHosted.Builds.{
    Admission,
    Coordinator,
    Lifecycle,
    OperationIntentSchema,
    ProcessorProfile,
    Storage
  }

  alias MixerHosted.CustomerBuilds.CancelSchema

  @moduletag :owned_native_cancel_fixture
  @tag timeout: 110_000
  test "authenticated cancel waits for exact CLI/compiler closure and releases once" do
    root = System.fetch_env!("MIXER_CANCEL_FIXTURE")
    c = Fixture.prepare!(true)
    install_creator!()

    for {id, file, module} <- [
          {1, "add_build_admission", MixerHosted.Repo.Migrations.AddBuildAdmission},
          {2, "add_build_aggregate_limits", MixerHosted.Repo.Migrations.AddBuildAggregateLimits}
        ] do
      version = "2026102500000#{id}"
      Code.require_file("priv/repo/migrations/#{version}_#{file}.exs")
      assert :ok = Ecto.Migrator.up(Migration, String.to_integer(version), module, log: false)
    end

    for sql <- ProcessorProfile.statements(:builds_v1) do
      F.q!(
        Admin,
        String.replace(sql, ~s(:"processor_database"), ~s("browser_ordinary_installation_r1422"))
      )
    end

    create_repo = c.hosted.repo |> Keyword.put(:username, "mixer_build_create")

    c = %{
      c
      | hosted: %{
          c.hosted
          | create_repo: create_repo,
            processor_profile: :builds_v1,
            build_cancel: true
        }
    }

    Fixture.configure!(c, :fixture)
    assert_startup_refused!()

    for sql <- CancelSchema.statements(), do: F.q!(Migration, sql)

    assert {:error, :authorization_unavailable} =
             Admin.transaction(fn -> CancelSchema.admit!(Admin) end)

    assert_startup_refused!()
    install_operation_intent!()

    assert_startup_refused!()

    for sql <- ProcessorProfile.operation_intent_statements(:durable_intent_v1),
        do: F.q!(Migration, sql)

    assert {:ok, :ok} = Admin.transaction(fn -> CancelSchema.admit!(Admin) end)

    grant = "EXECUTE ON FUNCTION #{OperationIntentSchema.entry()}"
    F.q!(Admin, "REVOKE #{grant} FROM mixer_build_processor")
    assert_startup_refused!()
    F.q!(Migration, "GRANT #{grant} TO mixer_build_processor")

    cancel_grant =
      "EXECUTE ON FUNCTION public.mixer_customer_build_cancel_v1(text,text,text,text,text)"

    F.q!(Admin, "REVOKE #{cancel_grant} FROM mixer_build_create")
    assert_startup_refused!()
    F.q!(Migration, "GRANT #{cancel_grant} TO mixer_build_create")

    File.write!(
      Path.join(root, "boot-refusals.json"),
      Jason.encode!(%{
        missing_cancel_function: true,
        missing_operation_intent_migration: true,
        missing_processor_grant: true,
        revoked_processor_grant: true,
        revoked_cancel_grant: true,
        endpoint_started: false
      })
    )

    c = Fixture.start!(c)
    assert MixerHosted.BrowserAuth.RuntimeOwner.status().phase == :storage_ready
    preauth = bootstrap_http(c)
    b = begin_http(c, preauth)
    r = http(c, "/auth/callback?" <> b.query, b.headers)
    assert r.status == 303
    cookie = response_cookie(r)
    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    csrf = Jason.decode!(session.body)["csrf_token"]
    auth = headers(cookie) ++ [{"origin", c.config.public_origin}, {"x-mixer-csrf", csrf}]

    registration = json(Path.join(root, "registration.json"))
    key = registration["spec"]

    selection =
      Map.merge(build_selection(), %{
        build_id: "running-cancel",
        source_sha256: key["source"]["sha256"],
        toolchain_lock_sha256: key["toolchain_lock_sha256"],
        build_definition_sha256: key["build_definition_sha256"]
      })

    scope =
      Map.take(selection, [:organization_id, :project_id, :application_id, :build_id])
      |> Map.put(:platform, :ios)

    spec =
      Map.merge(scope, %{
        source: %{
          kind: :revision,
          sha256: selection.source_sha256,
          reference: key["source"]["reference"]
        },
        toolchain_lock_sha256: selection.toolchain_lock_sha256,
        build_definition_sha256: selection.build_definition_sha256
      })

    capacity =
      Ecto.Multi.new()
      |> Admission.configure_fleet_multi(:fleet, :new, 1)
      |> Admission.configure_fleet_platform_multi(
        :platform,
        Map.take(scope, [:platform]),
        :new,
        1
      )
      |> Admission.configure_organization_multi(
        :organization,
        Map.take(scope, [:organization_id]),
        :new,
        1
      )
      |> Admission.configure_multi(
        :scope,
        Map.take(scope, [:organization_id, :platform]),
        :new,
        1
      )

    assert {:ok, _} = Admin.transaction(capacity)

    query = &F.q!(Migration, &1)
    query.("CREATE TABLE public.cancel_release_observation (event text NOT NULL)")

    query.("""
    CREATE FUNCTION public.cancel_release_probe() RETURNS trigger LANGUAGE plpgsql
      SECURITY DEFINER SET search_path=pg_catalog AS $$
    BEGIN
      INSERT INTO public.cancel_release_observation VALUES (NEW.terminal_event_id);
      RETURN NULL;
    END
    $$
    """)

    query.("REVOKE ALL ON FUNCTION public.cancel_release_probe() FROM PUBLIC")

    query.("""
    CREATE TRIGGER cancel_release_probe AFTER UPDATE ON public.mixer_build_reservations
      FOR EACH ROW WHEN (OLD.held AND NOT NEW.held) EXECUTE FUNCTION public.cancel_release_probe()
    """)

    assert {:ok, _} = Admin.transaction(create(spec, System.system_time(:millisecond)))
    mark(root, "processor-start")

    try do
      assert %{"command" => ["/usr/bin/xcodebuild" | _]} =
               await(root, "xcode-running.json", 55_000)

      assert [[true, nil]] = reservation(scope.build_id)
      first = cancel(c, selection, auth)
      assert first.status == 202, first.body

      assert %{"outcome" => "applied", "build" => %{"state" => "cancelling"}} =
               Jason.decode!(first.body)

      wait_until(
        fn -> match?([[false, event]] when is_binary(event), reservation(scope.build_id)) end,
        32_000
      )

      duplicate = cancel(c, selection, auth)
      assert duplicate.status == 200

      assert %{"outcome" => "duplicate", "build" => %{"state" => "cancelled"}} =
               Jason.decode!(duplicate.body)

      assert [[false, terminal]] = reservation(scope.build_id)
      assert [[["start", "cancel", "stopped"]]] = events(scope.build_id)

      assert [[1]] =
               F.q!(
                 Admin,
                 "SELECT count(*) FROM oban_jobs WHERE args->>'build_id'='running-cancel' AND args->>'kind'='cancel'"
               ).rows

      assert String.ends_with?(terminal, ":stopped")
      assert [[^terminal]] = F.q!(Admin, "SELECT event FROM cancel_release_observation").rows

      completed = %{spec | build_id: "completed-first"}
      record_completion!(completed)
      late = cancel(c, %{selection | build_id: completed.build_id}, auth)
      assert late.status == 409, late.body
      assert [[["start", "completed"]]] = events(completed.build_id)

      File.write!(
        Path.join(root, "authenticated-result.json"),
        Jason.encode!(%{
          initial_http: first.status,
          duplicate_http: duplicate.status,
          reservation: [false, terminal],
          ordered_events: ["start", "cancel", "stopped"],
          cancel_jobs: 1,
          release_count: 1,
          completion_first_http: late.status
        })
      )
    after
      mark(root, "processor-stop")
      assert %{"exit" => 0, "group_absent" => true} = await(root, "processor-closed.json", 19_000)
    end
  end

  defp assert_startup_refused! do
    assert {:error, {:mixer_hosted, reason}} = Application.ensure_all_started(:mixer_hosted)
    assert inspect(reason) =~ "build_cancel_admission_refused"
    assert Process.whereis(MixerHosted.Supervisor) == nil
    assert Process.whereis(MixerHostedWeb.Endpoint) == nil
    assert Process.whereis(MixerHosted.CustomerBuilds.CreateRepo) == nil
  end

  defp install_creator! do
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

    for sql <- MixerHosted.CustomerBuilds.CreateSchema.statements(), do: F.q!(Migration, sql)
    for sql <- MixerHosted.BrowserAuth.ActiveCreateSchema.statements(), do: F.q!(Migration, sql)
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

    F.q!(Admin, "UPDATE mixer_authz_memberships SET role='developer' WHERE id='member-a'")
  end

  defp install_operation_intent! do
    migrations = [
      {498, "add_private_build_operation_admission",
       MixerHosted.Repo.Migrations.AddPrivateBuildOperationAdmission},
      {499, "revoke_public_build_operation_execute",
       MixerHosted.Repo.Migrations.RevokePublicBuildOperationExecute},
      {500, "add_fenced_build_operation_intent",
       MixerHosted.Repo.Migrations.AddFencedBuildOperationIntent}
    ]

    for {number, file, module} <- migrations do
      prefix = "20261110000" <> Integer.to_string(number)
      Code.require_file("priv/unselected_operation_admission/#{prefix}_#{file}.exs")
      assert :ok = Ecto.Migrator.up(Migration, String.to_integer(prefix), module, log: false)
    end
  end

  defp create(spec, now) do
    Storage.create_multi(
      Ecto.Multi.new(),
      :build,
      spec,
      %{max_attempts: 1, timeout_ms: 95_000, retry_backoff_ms: 0},
      spec.build_id,
      now,
      &Coordinator.new/1
    )
  end

  defp record_completion!(spec) do
    scope = Map.take(spec, [:organization_id, :project_id, :application_id, :build_id, :platform])
    now = System.system_time(:millisecond)

    multi =
      create(spec, now)
      |> Ecto.Multi.merge(fn %{build: %{build: build}} ->
        {:ok, ref} = Lifecycle.worker_ref(build)
        start = %{type: :start, ref: ref}

        complete = %{
          type: :completed,
          ref: ref,
          result: %{
            outcome: :failed,
            class: :compiler,
            code: :compiler_error,
            diagnostic_sha256: String.duplicate("a", 64)
          }
        }

        Ecto.Multi.new()
        |> Storage.transition_multi(
          :start,
          scope,
          0,
          "fixture-start",
          start,
          now,
          &Coordinator.new/1
        )
        |> Storage.transition_multi(
          :complete,
          scope,
          1,
          "fixture-completed",
          complete,
          now,
          &Coordinator.new/1
        )
      end)

    assert {:ok, _} = Admin.transaction(multi)
  end

  defp reservation(build_id) do
    F.q!(
      Admin,
      """
      SELECT held, terminal_event_id FROM mixer_build_reservations r
        JOIN mixer_builds b ON r.build_record_id=b.id WHERE b.build_id=$1
      """,
      [build_id]
    ).rows
  end

  defp events(build_id) do
    F.q!(
      Admin,
      """
      SELECT ARRAY(SELECT e->'event'->>'type' FROM jsonb_array_elements(journal->'events') e)
        FROM mixer_builds WHERE build_id=$1
      """,
      [build_id]
    ).rows
  end

  defp cancel(c, selection, auth),
    do: http(c, "/console-api/v1/builds/cancel?" <> URI.encode_query(selection), auth, "POST")

  defp mark(root, file), do: File.write!(Path.join(root, file), "")
  defp json(file), do: file |> File.read!() |> Jason.decode!()

  defp await(root, file, budget) do
    path = Path.join(root, file)
    wait_until(fn -> File.regular?(path) end, budget)
    json(path)
  end

  defp wait_until(check, budget) do
    deadline = System.monotonic_time(:millisecond) + budget
    poll(check, deadline)
  end

  defp poll(check, deadline) do
    cond do
      check.() ->
        :ok

      System.monotonic_time(:millisecond) >= deadline ->
        flunk("deadline waiting for fixture observation")

      true ->
        Process.sleep(25)
        poll(check, deadline)
    end
  end
end
