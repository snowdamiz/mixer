defmodule MixerHosted.Releases.PostgresTest.Admin do
  use Ecto.Repo, otp_app: :mixer_release_ledger_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.PostgresTest.Migration do
  use Ecto.Repo, otp_app: :mixer_release_ledger_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.PostgresTest.ArtifactWriter do
  use Ecto.Repo, otp_app: :mixer_release_ledger_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.PostgresTest.Writer do
  use Ecto.Repo, otp_app: :mixer_release_ledger_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.PostgresTest do
  use ExUnit.Case, async: false

  alias MixerHosted.{Authorization, Releases}
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.PostgresStorage
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.{ArtifactAdmission, AssignmentV3}
  alias MixerHosted.Releases.PostgresTest.{Admin, ArtifactWriter, Migration, Writer}
  alias MixerHosted.Releases.Target

  @fixtures Path.expand("../../../../services/protocol/testdata", __DIR__)
  @max_sequence 18_446_744_073_709_551_615

  @artifact_migrations [
    {20_261_025_000_003, "add_customer_authorization",
     MixerHosted.Repo.Migrations.AddCustomerAuthorization},
    {20_261_025_000_004, "add_authorization_state_revisions",
     MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
    {20_261_025_000_005, "add_customer_artifact_storage",
     MixerHosted.Repo.Migrations.AddCustomerArtifactStorage}
  ]
  @ledger_migration {20_261_120_000_001, "add_local_release_ledger",
                     MixerHosted.Repo.Migrations.AddLocalReleaseLedger}
  @head_migration {20_261_120_000_002, "add_local_release_head_read",
                   MixerHosted.Repo.Migrations.AddLocalReleaseHeadRead}
  @delivery_migration {20_261_120_000_003, "add_local_release_delivery",
                       MixerHosted.Repo.Migrations.AddLocalReleaseDelivery}
  @managed_linux_migration {20_261_120_000_000, "local_managed_linux_source_selection",
                            MixerHosted.DevelopmentMigrations.LocalManagedLinuxSourceSelection}

  setup_all do
    settings =
      [
        database: "mixer_local_release_ledger",
        port: String.to_integer(System.fetch_env!("MIXER_RELEASE_LEDGER_TEST_PORT")),
        pool_size: 2,
        ssl: false,
        log: false
      ] ++
        case System.get_env("MIXER_RELEASE_LEDGER_TEST_SOCKET") do
          nil -> [hostname: "127.0.0.1"]
          socket -> [socket_dir: socket]
        end

    start_supervised!({Admin, [username: "ledger_fixture_admin"] ++ settings})
    start_supervised!({Writer, [username: "ledger_runtime"] ++ settings})

    start_supervised!(
      {Migration,
       [
         username: "ledger_fixture_admin",
         after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE ledger_owner", []) end
       ] ++ settings}
    )

    sql(Admin, "CREATE ROLE ledger_artifact_runtime LOGIN NOINHERIT")
    start_supervised!({ArtifactWriter, [username: "ledger_artifact_runtime"] ++ settings})

    migrations = Path.expand("../../../priv/repo/migrations", __DIR__)
    assert :ok = MixerHosted.Test.Migrations.check_files!(migrations)

    for migration <- @artifact_migrations do
      {version, mod} = load_migration(migrations, migration)
      assert :ok = Ecto.Migrator.up(Migration, version, mod, log: false)
    end

    migrate_both_orders(migrations)

    {version, module} =
      load_migration(
        migrations,
        {20_261_120_000_010, "add_local_release_publication_action",
         MixerHosted.Repo.Migrations.AddLocalReleasePublicationAction}
      )

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)

    provision_authz()
    seed_tenant()

    fixture =
      Path.join(@fixtures, "signed-release-v3.json")
      |> File.read!()
      |> Jason.decode!()

    signed = fixture["signed_assignment"]
    assignment = signed["assignment"]

    roots =
      Enum.map(fixture["roots"], &Map.update!(&1, "public_key", fn v -> Base.decode64!(v) end))

    config = %{repo: ArtifactWriter, roots: roots, host: fixture["host"]}
    envelope = Jason.encode!(Map.take(fixture, ~w(signed_manifest payload)))
    {:ok, artifact} = ArtifactAdmission.admit(envelope, config.host, roots, now())

    scope = %Scope{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "fieldlog",
      environment_id: "development"
    }

    assert {:ok, %{status: 201}} =
             Authorization.with_authorized_transaction(
               identity(["mixer.artifact.upload"]),
               "artifact.upload",
               scope,
               fn ctx ->
                 PostgresStorage.upload(
                   ctx,
                   artifact,
                   %{key: "fixture", reason: "Fixture", source_ip: nil},
                   config
                 )
               end,
               ArtifactWriter
             )

    target = %Target{
      scope: scope,
      platform: assignment["scope"]["platform"],
      runtime_sha256: assignment["runtime"],
      channel: assignment["channel"]
    }

    cases = Path.join(@fixtures, "release-v3-cases.json") |> File.read!() |> Jason.decode!()
    signed_cases = Map.new(cases["assignment_cases"], &{&1["name"], &1["signed_assignment_json"]})

    [
      config: %{target: target, host: config.host, roots: roots},
      release: release_fixture(target, Jason.encode!(signed) <> "\n"),
      max_release: release_fixture(target, Map.fetch!(signed_cases, "sequence-#{@max_sequence}")),
      next_release: release_fixture(target, Map.fetch!(signed_cases, "sequence-8")),
      artifact: artifact
    ]
  end

  setup %{release: release, config: config} = tags do
    sql(Admin, "TRUNCATE public.mixer_release_heads, public.mixer_release_publications")
    target = release.target
    scope = %{target.scope | environment_id: Map.get(tags, :environment, "development")}
    target = %{target | scope: scope}

    config = %{
      config
      | target: target,
        host: %{config.host | "scope" => Target.signed_scope(target)}
    }

    previous = Application.fetch_env(:mixer_hosted, :local_release_target)
    Application.put_env(:mixer_hosted, :local_release_target, config)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, :local_release_target, value)
        :error -> Application.delete_env(:mixer_hosted, :local_release_target)
      end
    end)

    assert %{num_rows: 1} =
             sql(
               Migration,
               """
               INSERT INTO public.mixer_release_heads
                 (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,writer_role)
               VALUES ($1,$2,$3,$4,$5,$6,$7,'ledger_runtime')
               """,
               [
                 scope.organization_id,
                 scope.project_id,
                 scope.application_id,
                 scope.environment_id,
                 target.platform,
                 target.runtime_sha256,
                 target.channel
               ]
             )

    [release: %{release | target: target}, config: config]
  end

  test "publishes exact bytes once, retains the original replay after advancing to uint64 max",
       %{release: release, max_release: max_release, artifact: artifact} do
    assert {:ok, first} = publish(release)

    assert first == %{
             sequence: release.sequence,
             previous_sequence: nil,
             artifact_sha256: artifact.manifest_sha256,
             rollout_basis_points: release.rollout_basis_points,
             signed_assignment_bytes: release.signed_assignment_bytes
           }

    assert {:ok, ^first} = publish(release)
    assert {:error, :idempotency_conflict} = publish(release, "first", "Different reason")

    assert {:error, :idempotency_conflict} =
             publish(%{
               release
               | signed_assignment_bytes: release.signed_assignment_bytes <> " "
             })

    assert {:error, :conflict} = publish(release, "another")

    overflowing =
      release.signed_assignment_bytes
      |> Jason.decode!()
      |> put_in(["assignment", "sequence"], @max_sequence + 1)
      |> Jason.encode!()

    assert {:error, :invalid_request} =
             publish(%{release | signed_assignment_bytes: overflowing}, "overflow")

    assert {:ok, result} = publish(max_release, "max")
    assert result.sequence == @max_sequence
    assert result.previous_sequence == release.sequence
    assert result.signed_assignment_bytes == max_release.signed_assignment_bytes
    assert {:ok, ^first} = publish(release)
    assert {:ok, ^result} = publish(max_release, "max")

    assert [
             [first_db, nil, "first", "Initial publication", "person", first_bytes, %DateTime{}],
             [
               last_db,
               previous_db,
               "max",
               "Initial publication",
               "person",
               last_bytes,
               %DateTime{}
             ]
           ] =
             sql(Admin, """
             SELECT sequence,previous_sequence,idempotency_key,reason,principal_id,
               signed_assignment_bytes,recorded_at
             FROM public.mixer_release_publications ORDER BY sequence
             """).rows

    assert Decimal.to_integer(first_db) == first.sequence
    assert Decimal.equal?(previous_db, first_db)
    assert Decimal.to_integer(last_db) == result.sequence

    assert {first_bytes, last_bytes} ==
             {first.signed_assignment_bytes, result.signed_assignment_bytes}

    assert [[^last_db]] = sql(Admin, "SELECT sequence FROM public.mixer_release_heads").rows

    assert [[artifact.envelope_bytes, artifact.signed_manifest_bytes, artifact.payload]] ==
             sql(Admin, """
             SELECT envelope_bytes,signed_manifest_bytes,payload FROM public.mixer_customer_artifacts
             """).rows

    assert [[0]] = sql(Writer, "SELECT count(*) FROM public.mixer_release_publications").rows
    assert [[0]] = sql(Writer, "SELECT count(*) FROM public.mixer_release_heads").rows

    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(
               Writer,
               "UPDATE public.mixer_release_publications SET reason='changed'"
             )

    {version, _, mod} = @ledger_migration

    assert_raise Postgrex.Error, ~r/release ledger contains committed publications/, fn ->
      Ecto.Migrator.down(Migration, version, mod, log: false)
    end
  end

  test "serializes a concurrent first publication and its replay", %{release: release} do
    outcomes =
      [:caller_one, :caller_two]
      |> Task.async_stream(fn _ -> publish(release) end, max_concurrency: 2, timeout: 6_000)
      |> Enum.to_list()

    assert [{:ok, {:ok, first}}, {:ok, {:ok, replay}}] = outcomes
    assert replay == first
    assert [[1]] = sql(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
  end

  test "concurrent different requests for the same key commit exactly the winner",
       %{release: release, next_release: next_release} do
    requests = [
      {"First contender", release},
      {"Second contender", next_release}
    ]

    {:ok, tasks} =
      Admin.transaction(fn ->
        sql(Admin, "SELECT sequence FROM public.mixer_release_heads FOR UPDATE")

        tasks =
          Enum.map(requests, fn {reason, request} ->
            Task.async(fn -> {reason, request.sequence, publish(request, "race", reason)} end)
          end)

        await_contending_writers(System.monotonic_time(:millisecond) + 350)
        tasks
      end)

    outcomes = Task.await_many(tasks, 6_000)

    assert [{reason, sequence, {:ok, result}}] =
             Enum.filter(outcomes, &match?({_, _, {:ok, _}}, &1))

    assert [{_, _, {:error, :idempotency_conflict}}] =
             Enum.filter(outcomes, &match?({_, _, {:error, _}}, &1))

    assert result.sequence == sequence
    assert result.previous_sequence == nil

    assert [[^reason, stored, head]] =
             sql(Admin, """
             SELECT p.reason, p.sequence, h.sequence
             FROM public.mixer_release_publications p CROSS JOIN public.mixer_release_heads h
             WHERE p.idempotency_key = 'race'
             """).rows

    assert Decimal.to_integer(stored) == sequence
    assert Decimal.equal?(stored, head)
  end

  @tag environment: "staging"
  test "refuses an existing artifact from a different environment and refuses unregistered targets",
       %{release: release} do
    assert {:error, :not_found} = publish(release)
    target = release.target

    for other <- [
          %{target | channel: "stable"},
          %{target | platform: "android"},
          %{target | runtime_sha256: String.duplicate("a", 64)},
          %{target | scope: %{target.scope | environment_id: "development"}}
        ] do
      assert {:error, :not_found} = publish(%{release | target: other})
    end

    assert [[nil]] = sql(Admin, "SELECT sequence FROM public.mixer_release_heads").rows
    assert [[0]] = sql(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
    assert [[1]] = sql(Admin, "SELECT count(*) FROM public.mixer_customer_artifacts").rows
  end

  test "requires signed assignment bytes and publish permission", %{release: release} do
    operator = identity(["mixer.release.publish"])

    assert {:error, :invalid_request} =
             Releases.publish(operator, release, "first", "Caller fields", Writer)

    assert {:error, :invalid_request} = publish(release, "first", <<0>>)

    assert {:error, :invalid_request} =
             publish(%{release | signed_assignment_bytes: <<0, 255, 1>>})

    invalid_signature =
      release.signed_assignment_bytes
      |> Jason.decode!()
      |> Map.put("signature", Base.encode64(<<0::512>>))
      |> Jason.encode!()

    assert {:error, :invalid_request} =
             publish(%{release | signed_assignment_bytes: invalid_signature})

    assert {:error, :permission_denied} =
             Releases.publish(
               identity(["mixer.artifact.upload"]),
               signed_command(release),
               "first",
               "No scope",
               Writer
             )

    assert {:error, :permission_denied} =
             Releases.publish(
               identity(["mixer.release.publish"], "developer"),
               signed_command(release),
               "first",
               "No role",
               Writer
             )

    assert [[0]] = sql(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
  end

  test "accepts the exact console operator through the restricted publication interface",
       %{release: release} do
    sql(
      Admin,
      "UPDATE public.mixer_authz_memberships SET role='release_manager' WHERE id='member'"
    )

    try do
      operator = identity(["mixer.artifact.read", "mixer.release.publish"])
      target = release.target

      for scope <- [
            %{target.scope | application_id: "other"},
            %{target.scope | environment_id: "staging"}
          ] do
        wrong = %{release | target: %{target | scope: scope}}

        assert {:error, :not_found} =
                 Releases.publish(operator, signed_command(wrong), "console", "Local", Writer)
      end

      assert_empty_ledger()

      assert {:ok, publication} =
               Releases.publish(operator, signed_command(release), "console", "Local", Writer)

      assert publication.signed_assignment_bytes == release.signed_assignment_bytes

      assert [["person", "console"]] =
               sql(
                 Admin,
                 "SELECT principal_id,idempotency_key FROM public.mixer_release_publications"
               ).rows
    after
      sql(Admin, "UPDATE public.mixer_authz_memberships SET role='owner' WHERE id='member'")
    end
  end

  test "exact retries still require the current assignment signing role and time window",
       %{release: release, config: config} do
    assert {:ok, first} = publish(release)

    for override <- [
          %{"assignment" => false, "artifact" => true},
          %{"not_after_unix" => now()}
        ] do
      roots =
        Enum.map(config.roots, fn root ->
          if root["assignment"], do: Map.merge(root, override), else: root
        end)

      Application.put_env(:mixer_hosted, :local_release_target, %{config | roots: roots})

      assert {:error, :permission_denied} = publish(release)
    end

    Application.put_env(:mixer_hosted, :local_release_target, config)
    assert {:ok, ^first} = publish(release)
    assert [[1]] = sql(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
  end

  test "restricted SQL cannot commit with fabricated or mismatched authorization settings",
       %{release: release} do
    settings = writer_settings(release.target.scope)

    for tampered <- [
          # All settings the original RLS checked, including an existing principal.
          Keyword.take(
            settings,
            ~w(action phase organization_id project_id application_id environment_id principal_id)a
          ),
          Keyword.put(settings, :required_scope, "mixer.artifact.read"),
          Keyword.put(settings, :environment_id, "staging"),
          Keyword.put(settings, :credential_ref, "other"),
          Keyword.put(settings, :token_expires_at, "invalid"),
          Keyword.put(settings, :token_expires_at, Integer.to_string(now() - 1)),
          Keyword.merge(settings,
            subject: "developer",
            principal_id: "developer",
            credential_ref: "developer",
            family_id: "dev-family"
          )
        ] do
      assert_raw_publish_denied(release, tampered)
    end

    assert {:ok, _} = publish(release)
  end

  test "live readers see only the current publication and its artifact digest",
       %{release: release, max_release: max_release, artifact: artifact} do
    on_exit(fn ->
      sql(
        Admin,
        "UPDATE public.mixer_authz_memberships SET role='developer' WHERE id='dev-member'"
      )
    end)

    sql(Admin, "UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='dev-member'")

    settings =
      writer_settings(release.target.scope)
      |> Keyword.merge(
        action: "release.read",
        required_scope: "mixer.workspace.read",
        subject: "developer",
        principal_id: "developer",
        credential_ref: "developer",
        family_id: "dev-family"
      )

    in_sql_context(settings, fn ->
      assert [[nil]] = sql(Writer, "SELECT sequence FROM public.mixer_release_heads").rows
      assert [] = raw_artifact(release)

      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               raw_publication_insert(release, "developer", %{}, mode: :savepoint)
    end)

    assert {:ok, original} = publish(release)
    assert {:ok, _} = publish(max_release, "max")
    assert {:ok, ^original} = publish(release)

    in_sql_context(settings, fn ->
      assert [[sequence]] = sql(Writer, "SELECT sequence FROM public.mixer_release_heads").rows
      assert Decimal.to_integer(sequence) == @max_sequence

      assert [[^sequence, "max"]] =
               sql(
                 Writer,
                 "SELECT sequence,idempotency_key FROM public.mixer_release_publications"
               ).rows

      assert [[nil, nil, artifact.payload_sha256]] == raw_artifact(release)
      assert %{num_rows: 0} = sql(Writer, "UPDATE public.mixer_release_heads SET sequence=1")
    end)

    for invalid <- [
          Keyword.take(
            settings,
            ~w(action phase organization_id project_id application_id environment_id)a
          ),
          Keyword.put(settings, :required_scope, "mixer.release.publish"),
          Keyword.put(settings, :environment_id, "staging"),
          Keyword.put(settings, :credential_ref, "person"),
          Keyword.put(settings, :token_issued_at, Integer.to_string(now() + 120)),
          Keyword.put(settings, :token_expires_at, Integer.to_string(now() - 1)),
          Keyword.merge(settings,
            action: "release.publish",
            required_scope: "mixer.release.publish"
          )
        ] do
      in_sql_context(invalid, fn ->
        assert [] = sql(Writer, "SELECT sequence FROM public.mixer_release_heads").rows
        assert [] = sql(Writer, "SELECT sequence FROM public.mixer_release_publications").rows
        assert [] = raw_artifact(release)
      end)
    end

    for mutation <- [
          "UPDATE public.mixer_authz_credentials SET active=false WHERE reference='developer'",
          "UPDATE public.mixer_authz_memberships SET active=false WHERE id='dev-member'",
          "UPDATE public.mixer_authz_memberships SET project_id='other' WHERE id='dev-member'",
          "UPDATE public.mixer_authz_memberships SET role='billing_manager' WHERE id='dev-member'"
        ] do
      try do
        sql(Admin, mutation)

        in_sql_context(settings, fn ->
          assert [] = sql(Writer, "SELECT sequence FROM public.mixer_release_heads").rows
          assert [] = sql(Writer, "SELECT sequence FROM public.mixer_release_publications").rows
          assert [] = raw_artifact(release)
        end)
      after
        sql(
          Admin,
          "UPDATE public.mixer_authz_credentials SET active=true WHERE reference='developer'"
        )

        sql(Admin, """
        UPDATE public.mixer_authz_memberships
        SET active=true, project_id='project-a', role='viewer' WHERE id='dev-member'
        """)
      end
    end

    in_sql_context(writer_settings(release.target.scope), fn ->
      assert [[artifact.signed_manifest_bytes, artifact.payload, artifact.payload_sha256]] ==
               raw_artifact(release)
    end)
  end

  test "fully populated settings cannot replace active exact target and operator records",
       %{release: release} do
    settings = writer_settings(release.target.scope)

    for {table, condition} <- [
          {"mixer_authz_applications", "id='fieldlog'"},
          {"mixer_authz_environments", "id='development'"},
          {"mixer_authz_memberships", "id='member'"},
          {"mixer_authz_credentials", "reference='person'"}
        ] do
      assert %{num_rows: 1} =
               sql(Admin, "UPDATE public.#{table} SET active=false WHERE #{condition}")

      try do
        assert_raw_publish_denied(release, settings)
      after
        sql(Admin, "UPDATE public.#{table} SET active=true WHERE #{condition}")
      end
    end

    sql(Admin, "UPDATE public.mixer_authz_memberships SET project_id='other' WHERE id='member'")

    try do
      assert_raw_publish_denied(release, settings)
    after
      sql(
        Admin,
        "UPDATE public.mixer_authz_memberships SET project_id='project-a' WHERE id='member'"
      )
    end

    assert {:ok, _} = publish(release)
  end

  test "a valid operator cannot supply the database audit timestamp or another principal",
       %{release: release} do
    for {values, message} <- [
          {%{recorded_at: ~U[2000-01-01 00:00:00.000000Z]}, "permission denied for table"},
          {%{principal_id: "developer"}, "row-level security policy"}
        ] do
      assert {:error, :permission_denied} =
               Authorization.with_authorized_transaction(
                 identity(["mixer.release.publish"]),
                 "release.publish",
                 release.target.scope,
                 fn _context ->
                   assert {:error, %Postgrex.Error{postgres: error}} =
                            raw_publication_insert(release, "person", values)

                   assert error.code == :insufficient_privilege
                   assert error.message =~ message
                   {:error, :permission_denied}
                 end,
                 Writer
               )
    end

    assert_empty_ledger()

    sql(Admin, "GRANT INSERT(recorded_at) ON public.mixer_release_publications TO ledger_runtime")

    try do
      assert {:error, :authorization_unavailable} = publish(release)
    after
      sql(
        Admin,
        "REVOKE INSERT(recorded_at) ON public.mixer_release_publications FROM ledger_runtime"
      )
    end

    assert {:ok, _} = publish(release)
  end

  test "rolls back the append, audit, retry key and head on a deferred failure", %{
    release: release
  } do
    sql(Admin, """
    CREATE FUNCTION public.ledger_fixture_fail_commit() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
    BEGIN
      IF EXISTS (SELECT 1 FROM public.mixer_release_heads WHERE sequence=NEW.sequence) THEN
        RAISE EXCEPTION 'ledger fixture failure after head advance';
      END IF;
      RAISE EXCEPTION 'ledger fixture observed no head advance';
    END $body$
    """)

    sql(Admin, """
    CREATE CONSTRAINT TRIGGER ledger_fixture_fail_commit
    AFTER INSERT ON public.mixer_release_publications
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    EXECUTE FUNCTION public.ledger_fixture_fail_commit()
    """)

    try do
      assert {:error, :authorization_unavailable} = publish(release)
      assert [[nil]] = sql(Admin, "SELECT sequence FROM public.mixer_release_heads").rows
      assert [[0]] = sql(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
    after
      sql(Admin, "DROP TRIGGER ledger_fixture_fail_commit ON public.mixer_release_publications")
      sql(Admin, "DROP FUNCTION public.ledger_fixture_fail_commit()")
    end

    assert {:ok, %{previous_sequence: nil, sequence: sequence}} = publish(release)
    assert sequence == release.sequence
  end

  defp publish(release, key \\ "first", reason \\ "Initial publication"),
    do:
      Releases.publish(
        identity(["mixer.release.publish"]),
        signed_command(release),
        key,
        reason,
        Writer
      )

  defp signed_command(release),
    do: {:signed, release.target, release.signed_assignment_bytes, fn Writer -> :ok end}

  defp release_fixture(target, bytes) do
    {:ok, signed} = AssignmentV3.decode_signed(bytes)

    %{
      target: target,
      sequence: signed.assignment["sequence"],
      artifact_sha256: signed.assignment["artifact_sha256"],
      rollout_basis_points: signed.assignment["rollout_basis_points"],
      signed_assignment_bytes: bytes
    }
  end

  defp await_contending_writers(deadline) do
    sql(Admin, "SELECT pg_stat_clear_snapshot()")

    case sql(Admin, """
         SELECT count(*) FROM pg_stat_activity
         WHERE datname=current_database() AND usename='ledger_runtime'
           AND wait_event_type='Lock' AND cardinality(pg_blocking_pids(pid)) > 0
           AND query LIKE '%mixer_release_heads%FOR UPDATE%'
         """).rows do
      [[2]] ->
        :ok

      _ ->
        assert System.monotonic_time(:millisecond) < deadline,
               "both requests must reach the head lock"

        Process.sleep(5)
        await_contending_writers(deadline)
    end
  end

  defp writer_settings(scope) do
    Map.to_list(Map.from_struct(scope)) ++
      [
        action: "release.publish",
        required_scope: "mixer.release.publish",
        phase: "effect",
        identity_class: "human",
        directory_mode: "",
        transaction_marker: String.duplicate("a", 64),
        principal_id: "person",
        profile_id: "profile",
        profile_version: "1",
        issuer: "https://issuer.example",
        client_id: "client",
        subject: "person",
        credential_ref: "person",
        family_id: "family",
        token_issued_at: Integer.to_string(now() - 20),
        token_expires_at: Integer.to_string(now() + 600)
      ]
  end

  defp assert_raw_publish_denied(release, settings) do
    assert {:ok, :denied} =
             Writer.transaction(fn ->
               Session.context!(Writer, settings)

               assert [["ledger_runtime", "ledger_runtime", false, false]] =
                        sql(Writer, """
                        SELECT current_user::text, session_user::text, rolsuper, rolbypassrls
                        FROM pg_roles WHERE rolname=current_user
                        """).rows

               assert [[0]] = sql(Writer, "SELECT count(*) FROM public.mixer_release_heads").rows

               assert [[0]] =
                        sql(Writer, "SELECT count(*) FROM public.mixer_release_publications").rows

               assert [] = raw_artifact(release)

               assert %{num_rows: 0} =
                        sql(Writer, "UPDATE public.mixer_release_heads SET sequence=1")

               principal = Keyword.fetch!(settings, :principal_id)

               assert {:error, %Postgrex.Error{postgres: error}} =
                        raw_publication_insert(release, principal, %{}, mode: :savepoint)

               assert error.code == :insufficient_privilege
               assert error.message =~ "row-level security policy"
               :denied
             end)

    assert_empty_ledger()
  end

  defp in_sql_context(settings, callback) do
    assert {:ok, :checked} =
             Writer.transaction(fn ->
               Session.context!(Writer, settings)
               callback.()
               :checked
             end)
  end

  defp raw_artifact(release) do
    target = release.target
    scope = target.scope

    sql(
      Writer,
      "SELECT * FROM public.mixer_release_bound_artifact($1,$2,$3,$4,$5,$6,$7,$8)",
      [
        scope.organization_id,
        scope.project_id,
        scope.application_id,
        scope.environment_id,
        target.platform,
        target.runtime_sha256,
        target.channel,
        release.artifact_sha256
      ]
    ).rows
  end

  defp raw_publication_insert(release, principal, overrides, opts \\ []) do
    attributes =
      release.target
      |> Target.filter()
      |> Map.new()
      |> Map.merge(
        Map.take(release, [
          :artifact_sha256,
          :signed_assignment_bytes,
          :rollout_basis_points
        ])
      )
      |> Map.merge(%{
        sequence: Decimal.new(release.sequence),
        principal_id: principal,
        idempotency_key: "direct",
        reason: "SQL control"
      })
      |> Map.merge(overrides)
      |> Map.to_list()

    {columns, values} = Enum.unzip(attributes)
    bindings = Enum.map_join(1..length(values), ",", &"$#{&1}")

    Ecto.Adapters.SQL.query(
      Writer,
      "INSERT INTO public.mixer_release_publications (#{Enum.join(columns, ",")}) VALUES (#{bindings})",
      values,
      opts
    )
  end

  defp assert_empty_ledger do
    assert [[nil]] = sql(Admin, "SELECT sequence FROM public.mixer_release_heads").rows
    assert [[0]] = sql(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
  end

  defp migrate_both_orders(migrations) do
    # The managed Linux migration grants EXECUTE to the existing build writer.
    if sql(Admin, "SELECT 1 FROM pg_roles WHERE rolname='mixer_build_create'").rows == [] do
      sql(Admin, "CREATE ROLE mixer_build_create LOGIN NOINHERIT")
    end

    {ledger_version, ledger} = load_migration(migrations, @ledger_migration)
    {head_version, head} = load_migration(migrations, @head_migration)

    {delivery_version, delivery} =
      load_migration(
        Path.expand("../../../priv/local_release_delivery", __DIR__),
        @delivery_migration
      )

    {starter_version, starter} =
      load_migration(
        Path.expand("../../../priv/local_managed_linux_source_selection", __DIR__),
        @managed_linux_migration
      )

    assert :ok = Ecto.Migrator.up(Migration, ledger_version, ledger, log: false)
    assert :ok = Ecto.Migrator.up(Migration, head_version, head, log: false)
    assert :ok = Ecto.Migrator.up(Migration, delivery_version, delivery, log: false)
    assert :ok = Ecto.Migrator.up(Migration, starter_version, starter, log: false)
    versions = [starter_version, ledger_version, head_version, delivery_version]
    assert_migrations_present(versions)

    assert :ok = Ecto.Migrator.down(Migration, starter_version, starter, log: false)
    assert :ok = Ecto.Migrator.down(Migration, delivery_version, delivery, log: false)
    assert :ok = Ecto.Migrator.down(Migration, head_version, head, log: false)
    assert :ok = Ecto.Migrator.down(Migration, ledger_version, ledger, log: false)

    assert :ok = Ecto.Migrator.up(Migration, starter_version, starter, log: false)
    assert :ok = Ecto.Migrator.up(Migration, ledger_version, ledger, log: false)
    assert :ok = Ecto.Migrator.up(Migration, head_version, head, log: false)
    assert :ok = Ecto.Migrator.up(Migration, delivery_version, delivery, log: false)
    assert_migrations_present(versions)
  end

  defp load_migration(dir, {version, file, mod}) do
    path = Path.join(dir, "#{version}_#{file}.exs")
    assert File.regular?(path)
    unless Code.ensure_loaded?(mod), do: Code.require_file(path)
    {version, mod}
  end

  defp assert_migrations_present(versions) do
    expected = Enum.map(versions, &[&1])

    assert ^expected =
             sql(
               Admin,
               "SELECT version FROM public.schema_migrations WHERE version = ANY($1::bigint[]) ORDER BY version",
               [versions]
             ).rows

    assert [[true, true, true, true, true, true]] =
             sql(Admin, """
             SELECT to_regclass('public.mixer_managed_linux_pair25_starters') IS NOT NULL,
               to_regprocedure('public.mixer_managed_linux_pair25_starter_v1(text,text,jsonb,boolean,text,text)') IS NOT NULL,
               to_regclass('public.mixer_release_heads') IS NOT NULL,
               to_regclass('public.mixer_release_publications') IS NOT NULL,
               to_regprocedure('public.mixer_release_delivery_offer(text,text,text,text,text,text,text)') IS NOT NULL,
               to_regprocedure('public.mixer_release_delivery_artifact(text,text,text,text,text,text,text,text)') IS NOT NULL
             """).rows
  end

  defp provision_authz do
    for repo_role <- ~w(ledger_runtime ledger_artifact_runtime) do
      sql(Admin, "GRANT USAGE ON SCHEMA public TO #{repo_role}")

      for table <-
            ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
          do: sql(Admin, "GRANT SELECT ON public.mixer_authz_#{table} TO #{repo_role}")

      for table <- ~w(profiles principals families credentials organization_heads project_heads),
          do:
            sql(
              Admin,
              "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO #{repo_role}"
            )
    end

    for table <- ~w(artifacts audit_events idempotency),
        do:
          sql(
            Admin,
            "GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO ledger_artifact_runtime"
          )

    sql(Admin, """
    GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256)
    ON public.mixer_customer_artifact_heads TO ledger_artifact_runtime
    """)

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists) do
      sql(
        Admin,
        "GRANT EXECUTE ON FUNCTION public.#{name}(#{CustomerArtifacts.Schema.signatures()[name]}) TO ledger_artifact_runtime"
      )
    end

    sql(Admin, "GRANT SELECT,UPDATE(sequence) ON public.mixer_release_heads TO ledger_runtime")

    sql(Admin, """
    GRANT EXECUTE ON FUNCTION
      public.mixer_release_publish_allowed(text,text,text,text),
      public.mixer_release_read_allowed(text,text,text,text),
      public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text)
    TO ledger_runtime
    """)

    sql(Admin, """
    GRANT SELECT, INSERT (
      organization_id, project_id, application_id, environment_id, platform, runtime_sha256, channel,
      sequence, previous_sequence, artifact_sha256, signed_assignment_bytes, rollout_basis_points,
      idempotency_key, reason, principal_id
    ) ON public.mixer_release_publications TO ledger_runtime
    """)
  end

  defp seed_tenant do
    for statement <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https://issuer.example','client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,2),('developer','human',true,0,2)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,'person','human','person',true),('profile',1,'developer','human','developer',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,3),('dev-family','profile',1,'developer',true,0,NULL,3)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'person','person','family',true,0,NULL,4),('profile',1,'developer','developer','dev-family',true,0,NULL,4)",
          "INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true)",
          "INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true),('org-a','other',true)",
          "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','fieldlog',true)",
          "INSERT INTO public.mixer_authz_environments VALUES ('org-a','project-a','fieldlog','development',true),('org-a','project-a','fieldlog','staging',true)",
          "INSERT INTO public.mixer_authz_organization_heads VALUES ('org-a',5)",
          "INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',6)",
          "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org-a','project-a','exact_project','owner',true,0,NULL,7),('dev-member','developer','org-a','project-a','exact_project','developer',true,0,NULL,7)"
        ],
        do: sql(Admin, statement)

    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis("org-a", "project-a")

    sql(
      Admin,
      "INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)",
      [genesis]
    )
  end

  defp identity(scopes, subject \\ "person") do
    %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://issuer.example",
      subject: subject,
      client_id: "client",
      credential_ref: subject,
      issued_at: now() - 20,
      expires_at: now() + 600,
      identity_class: :human,
      scopes: scopes
    }
  end

  defp now, do: System.system_time(:second)
  defp sql(repo, statement, params \\ []), do: Ecto.Adapters.SQL.query!(repo, statement, params)
end
