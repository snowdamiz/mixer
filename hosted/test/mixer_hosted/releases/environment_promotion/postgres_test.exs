defmodule MixerHosted.Releases.EnvironmentPromotion.PostgresTest.Admin do
  use Ecto.Repo, otp_app: :mixer_stage_promotion_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.EnvironmentPromotion.PostgresTest.Migration do
  use Ecto.Repo, otp_app: :mixer_stage_promotion_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.EnvironmentPromotion.PostgresTest.Writer do
  use Ecto.Repo, otp_app: :mixer_stage_promotion_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.EnvironmentPromotion.PostgresTest.Uploader do
  use Ecto.Repo, otp_app: :mixer_stage_promotion_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.EnvironmentPromotion.PostgresTest do
  use ExUnit.Case, async: false

  alias MixerHosted.{Authorization, Releases, RuntimeConfig}
  alias MixerHosted.CustomerArtifacts.{PostgresStorage, Schema}
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactAdmission
  alias MixerHosted.Releases.BrowserHead
  alias MixerHosted.Releases.EnvironmentPromotion.Direction

  alias MixerHosted.Releases.EnvironmentPromotion.PostgresTest.{
    Admin,
    Migration,
    Uploader,
    Writer
  }

  import MixerHosted.Test.StagePromotionSigningFixture,
    only: [variant: 5, vector: 0, publication: 1]

  unless System.get_env("MIXER_STAGE_PROMOTION_SOCKET"), do: @moduletag(:skip)
  @moduletag capture_log: true

  @direction "dev-to-stage"
  @reason "Promote synthetic local release"
  @writer "stage_fixture_writer"
  @uploader "stage_fixture_uploader"
  @binding "public.mixer_stage_promotion_bindings"
  @publications "public.mixer_release_publications"
  @heads "public.mixer_release_heads"
  @enrollment "public.mixer_release_delivery_enrollments"
  @route "public.mixer_stage_promotion_directions"
  @jobs "mixer_release_jobs.oban_jobs"
  @migrations [
    {"repo/migrations", "20261025000003_add_customer_authorization"},
    {"repo/migrations", "20261025000004_add_authorization_state_revisions"},
    {"repo/migrations", "20261025000005_add_customer_artifact_storage"},
    {"repo/migrations", "20261120000001_add_local_release_ledger"},
    {"repo/migrations", "20261120000002_add_local_release_head_read"},
    {"local_release_delivery", "20261120000003_add_local_release_delivery"},
    {"repo/migrations", "20261120000004_add_local_release_cli_requests"},
    {"repo/migrations", "20261120000010_add_local_release_publication_action"},
    {"repo/migrations", "20261120000011_add_local_release_halt_health"},
    {"repo/migrations", "20261120000012_add_local_release_halt_audit"},
    {"repo/migrations", "20261120000013_add_local_release_head_details"},
    {"local_release_target_registry", "20261120000015_add_local_release_target_registry"},
    {"local_stage_promotion", "20261120000016_add_local_stage_promotion"}
  ]

  setup_all do
    options = [
      database: "postgres",
      socket_dir: System.fetch_env!("MIXER_STAGE_PROMOTION_SOCKET"),
      log: false,
      pool_size: 2,
      ssl: false
    ]

    start_supervised!({Admin, [username: "stage_fixture_admin"] ++ options})

    for statement <- [
          "CREATE ROLE stage_fixture_owner NOLOGIN NOINHERIT",
          "CREATE ROLE #{@writer} LOGIN NOINHERIT",
          "CREATE ROLE #{@uploader} LOGIN NOINHERIT",
          "CREATE ROLE mixer_release_delivery LOGIN NOINHERIT",
          "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
          "ALTER SCHEMA public OWNER TO stage_fixture_owner",
          "GRANT CREATE ON DATABASE postgres TO stage_fixture_owner"
        ],
        do: admin(statement)

    start_supervised!(
      {Migration,
       [
         username: "stage_fixture_admin",
         after_connect: fn connection ->
           Postgrex.query!(connection, "SET ROLE stage_fixture_owner", [])
         end
       ] ++ options}
    )

    start_supervised!({Writer, [username: @writer] ++ options})
    start_supervised!({Uploader, [username: @uploader] ++ options})

    for {dir, name} <- @migrations do
      if queue_enabled?() and dir == "local_release_target_registry",
        do: migrate!("local_release_jobs", "20261120000014_add_local_release_jobs")

      migrate!(dir, name)
    end

    assert [[queue_enabled?()]] ==
             admin("SELECT to_regclass('mixer_release_jobs.oban_jobs') IS NOT NULL").rows

    assert :error = MixerHosted.Application.startup()
    grant!()
    seed_authorization!()

    vector = vector()

    source = %{
      ios: variant(vector, "ios", "development", "internal", 7),
      android: variant(vector, "android", "development", "internal", 9)
    }

    destination = %{
      ios: variant(vector, "ios", "staging", "candidate", 3),
      android: variant(vector, "android", "staging", "candidate", 12)
    }

    direction = %Direction{
      source: Map.new(source, fn {platform, variant} -> {platform, variant.enrollment} end),
      destination:
        Map.new(destination, fn {platform, variant} -> {platform, variant.enrollment} end)
    }

    configure(:local_stage_promotion_directions, %{@direction => direction})
    provision_route!(direction)

    for variant <- Map.values(source) ++ Map.values(destination), do: upload!(variant)

    if queue_enabled?() do
      for variant <- Map.values(source) ++ Map.values(destination),
          do: enroll!(variant.enrollment.target)

      provision_queue!(options)
      start_queue_enabled_api!(options)
    end

    %{source: source, destination: destination, direction: direction}
  end

  setup %{source: source, destination: destination} do
    admin("""
    TRUNCATE #{@binding}, #{@enrollment}, #{@publications}, #{@heads},
             public.mixer_release_cli_requests
    """)

    if queue_enabled?(), do: admin("TRUNCATE #{@jobs}")

    for variant <- Map.values(source) ++ Map.values(destination),
        do: enroll!(variant.enrollment.target)

    for variant <- Map.values(source), do: assert({:ok, _} = publish(variant, "source"))

    %{
      sequences: %{ios: 7, android: 9},
      evidence: Map.new(destination, fn {p, v} -> {p, evidence(v)} end)
    }
  end

  test "commits both stages and exact replay ignores later head advances", f do
    assert {:ok, %{ios: %{sequence: 3}, android: %{sequence: 12}} = first} = promote(f)
    assert destination_heads() == [["android", "12"], ["ios", "3"]]
    assert_release_jobs([f.source, f.destination])

    expected_artifacts =
      for variants <- [f.source, f.destination],
          platform <- [:ios, :android],
          do: publication(variants[platform]).artifact_sha256

    assert [[fingerprint, "person", @reason | ^expected_artifacts]] =
             admin("""
             SELECT request_sha256,principal_id,reason,
                    source_ios_artifact_sha256,source_android_artifact_sha256,
                    destination_ios_artifact_sha256,destination_android_artifact_sha256 FROM #{@binding}
             """).rows

    assert byte_size(fingerprint) == 64

    for {platform, variant} <- f.destination do
      sequence = Integer.to_string(first[platform].sequence)
      browser_identity = %{identity() | scopes: ["mixer.workspace.read"]}

      assert {:ok, %{release: %{sequence: ^sequence, details: %{action: "promote"}}}} =
               BrowserHead.read(browser_identity, variant.enrollment.target, Writer, :details)
    end

    for {side, variants} <- [source: f.source, destination: f.destination],
        {platform, variant} <- variants do
      retained = evidence(variant)
      target = variant.enrollment.target
      action = if side == :source, do: "publish", else: "stage_promote"

      assert [
               [
                 action,
                 retained.signed_assignment_bytes,
                 retained.signed_manifest_bytes,
                 retained.payload
               ]
             ] ==
               admin(
                 """
                 SELECT p.action,p.signed_assignment_bytes,a.signed_manifest_bytes,a.payload
                 FROM #{@publications} p JOIN public.mixer_customer_artifacts a
                   USING (organization_id,project_id,application_id,environment_id,platform,runtime_sha256)
                 WHERE p.environment_id=$1 AND p.platform=$2 AND p.artifact_sha256=a.manifest_sha256
                 """,
                 [target.scope.environment_id, Atom.to_string(platform)]
               ).rows
    end

    assert {:ok, ^first} = promote(f)
    assert [[4, 1]] == counts()
    assert_release_jobs([f.source, f.destination])

    for variant <- Map.values(f.source) ++ Map.values(f.destination) do
      assert {:ok, %{sequence: 30}} = publish(advance(variant), "advance")
    end

    assert {:ok, ^first} = promote(f)
    assert destination_heads() == [["android", "30"], ["ios", "30"]]
    assert [[8, 1]] == counts()

    assert_release_jobs([
      f.source,
      f.destination,
      advanced_variants(f.source),
      advanced_variants(f.destination)
    ])

    assert {:error, :conflict} = promote(f, "different-key")
    assert {:error, :idempotency_conflict} = promote(f, "promote", "Changed reason")

    modified = update_in(f.evidence.ios.signed_assignment_bytes, &(&1 <> " "))
    assert {:error, :idempotency_conflict} = promote(modified)
    assert [[8, 1]] == counts()
  end

  test "rejects wrong source, scope, enrollment, environment and authority", f do
    assert {:error, :release_not_found} = promote(put_in(f.sequences.ios, 99))

    assert {:error, :assignment_rejected} =
             promote(put_in(f.evidence.ios, evidence(f.source.ios)))

    assert {:error, :unauthenticated} =
             promote(f, "promote", @reason, %{
               identity()
               | expires_at: System.system_time(:second) - 1
             })

    for {disable, restore, error} <- [
          {"UPDATE public.mixer_authz_environments SET active=false WHERE id='development'",
           "UPDATE public.mixer_authz_environments SET active=true WHERE id='development'",
           :invalid_promotion},
          {"UPDATE public.mixer_authz_environments SET active=false WHERE id='staging'",
           "UPDATE public.mixer_authz_environments SET active=true WHERE id='staging'",
           :not_found},
          {"UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='member'",
           "UPDATE public.mixer_authz_memberships SET role='release_manager' WHERE id='member'",
           :permission_denied},
          {"DELETE FROM #{@enrollment} WHERE environment_id='development' AND platform='ios'",
           nil, :invalid_promotion},
          {"UPDATE #{@route} SET active=false", "UPDATE #{@route} SET active=true",
           :invalid_promotion}
        ] do
      admin(disable)

      try do
        assert {:error, ^error} = promote(f)
        assert_empty_destination()
      after
        if restore, do: admin(restore), else: enroll_registry!(f.source.ios.enrollment.target)
      end
    end

    assert_empty_destination()
  end

  test "rechecks the current role and source environment after a destination head lock wait", f do
    for {revoke, restore} <- [
          {"UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='member'",
           "UPDATE public.mixer_authz_memberships SET role='release_manager' WHERE id='member'"},
          {"UPDATE public.mixer_authz_environments SET active=false WHERE id='development'",
           "UPDATE public.mixer_authz_environments SET active=true WHERE id='development'"}
        ] do
      reject_after_head_wait(f, revoke, restore)
    end
  end

  defp reject_after_head_wait(f, revoke, restore) do
    parent = self()

    lock =
      Task.async(fn ->
        Admin.transaction(fn ->
          admin(
            "SELECT 1 FROM #{@heads} WHERE environment_id='staging' AND platform='android' FOR UPDATE"
          )

          send(parent, :head_locked)

          receive do
            :release_head -> :ok
          after
            1_000 -> raise "fixture did not release the lock"
          end
        end)
      end)

    assert_receive :head_locked
    writer = Task.async(fn -> promote(f) end)

    try do
      await_head_wait(System.monotonic_time(:millisecond) + 300)
      admin(revoke)
    after
      send(lock.pid, :release_head)
    end

    try do
      assert {:ok, :ok} = Task.await(lock)
      assert {:error, _} = Task.await(writer)
      assert_empty_destination()
    after
      admin(restore)
    end
  end

  test "the writer cannot commit a stage publication without its binding", f do
    target = f.destination.ios.enrollment.target
    digest = publication(f.destination.ios).artifact_sha256
    assignment = f.evidence.ios.signed_assignment_bytes

    assert {:error, :authorization_unavailable} =
             Authorization.with_authorized_transaction(
               identity(),
               "release.publish",
               target.scope,
               fn _context ->
                 assert %{num_rows: 1} =
                          sql(
                            Writer,
                            """
                            INSERT INTO #{@publications} (
                              organization_id,project_id,application_id,environment_id,platform,runtime_sha256,
                              channel,sequence,artifact_sha256,signed_assignment_bytes,rollout_basis_points,
                              idempotency_key,reason,principal_id,action
                            ) VALUES ($1,$2,$3,$4,$5,$6,$7,3,$8,$9,10000,'orphan',$10,'person','stage_promote')
                            """,
                            coordinates(target) ++ [digest, assignment, @reason]
                          )

                 assert %{num_rows: 1} =
                          sql(
                            Writer,
                            """
                            UPDATE #{@heads} SET sequence=3 WHERE
                              (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel)
                                = ($1,$2,$3,$4,$5,$6,$7)
                            """,
                            coordinates(target)
                          )

                 {:ok, :append_without_binding}
               end,
               Writer
             )

    assert_empty_destination()
  end

  test "rolls back the first head advance when the second append fails", f do
    with_failure(
      "BEFORE INSERT ON #{@publications} FOR EACH ROW",
      """
      IF NEW.action='stage_promote' AND NEW.platform='ios' THEN
        IF EXISTS (SELECT 1 FROM #{@heads} WHERE environment_id='staging'
                    AND platform='android' AND sequence=12) THEN
          PERFORM nextval('public.stage_fixture_fault_seen');
        END IF;
        RAISE EXCEPTION 'fixture second append failed';
      END IF;
      RETURN NEW;
      """,
      @publications,
      fn ->
        assert {:error, :authorization_unavailable} = promote(f)
        assert [[true]] = admin("SELECT is_called FROM public.stage_fixture_fault_seen").rows
        assert_empty_destination()
      end
    )

    assert {:ok, _} = promote(f)
  end

  test "rolls back both advances and the binding on deferred commit failure", f do
    with_failure(
      "AFTER INSERT ON #{@binding} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW",
      """
      IF (SELECT count(*) FROM #{@heads} WHERE environment_id='staging'
            AND ((platform='android' AND sequence=12) OR (platform='ios' AND sequence=3))) = 2
        AND EXISTS (SELECT 1 FROM #{@binding} WHERE idempotency_key='promote')
        #{deferred_job_check()} THEN
        PERFORM nextval('public.stage_fixture_fault_seen');
      END IF;
      RAISE EXCEPTION 'fixture deferred stage commit failed';
      """,
      @binding,
      fn ->
        assert {:error, :authorization_unavailable} = promote(f)
        assert [[true]] = admin("SELECT is_called FROM public.stage_fixture_fault_seen").rows
        assert_empty_destination()
      end
    )

    assert {:ok, _} = promote(f)
    assert_release_jobs([f.source, f.destination])
  end

  @tag skip: System.get_env("MIXER_STAGE_PROMOTION_QUEUE") != "1"
  test "rolls back both advances when the second queue insert fails", f do
    with_failure(
      "BEFORE INSERT ON #{@jobs} FOR EACH ROW",
      """
      IF NEW.args->>'environment_id'='staging' AND NEW.args->>'platform'='ios' THEN
        IF (SELECT count(id) FROM #{@jobs})=1 AND
           (SELECT count(*) FROM #{@heads} WHERE environment_id='staging'
             AND sequence IS NOT NULL)=2 THEN
          PERFORM nextval('public.stage_fixture_fault_seen');
        END IF;
        RAISE EXCEPTION 'fixture second queue insert failed';
      END IF;
      RETURN NEW;
      """,
      @jobs,
      fn ->
        assert {:error, :authorization_unavailable} = promote(f)
        assert [[true]] = admin("SELECT is_called FROM public.stage_fixture_fault_seen").rows
        assert_empty_destination()
      end
    )

    assert {:ok, _} = promote(f)
    assert_release_jobs([f.source, f.destination])
  end

  defp deferred_job_check do
    if queue_enabled?() do
      "AND (SELECT count(id) FROM #{@jobs})=2"
    else
      ""
    end
  end

  defp advance(variant), do: put_in(variant.assignment["sequence"], 30)

  defp advanced_variants(variants),
    do: Map.new(variants, fn {platform, v} -> {platform, advance(v)} end)

  defp assert_release_jobs(groups) do
    if queue_enabled?() do
      expected =
        for group <- groups, {_, variant} <- group do
          keys = MixerHosted.Releases.Target.filter(variant.enrollment.target)

          Map.new(keys, fn {k, v} -> {Atom.to_string(k), v} end)
          |> Map.merge(%{"version" => 1, "sequence" => to_string(variant.assignment["sequence"])})
        end

      actual =
        admin("SELECT queue,worker,state::text,attempt,args FROM #{@jobs}").rows

      job = fn args ->
        ["releases", "MixerHosted.Releases.ReleaseJobs.Materialize", "available", 0, args]
      end

      assert Enum.frequencies(actual) == Enum.frequencies(Enum.map(expected, job))
    end
  end

  defp promote(f, key \\ "promote", reason \\ @reason, identity \\ identity()),
    do:
      Releases.promote_environment(
        identity,
        @direction,
        f.sequences,
        f.evidence,
        key,
        reason,
        Writer
      )

  defp publish(variant, key) do
    config = Map.from_struct(variant.enrollment)
    previous = Application.fetch_env(:mixer_hosted, :local_release_target)
    Application.put_env(:mixer_hosted, :local_release_target, config)

    try do
      signed = evidence(variant).signed_assignment_bytes

      Releases.publish(
        identity(),
        {:signed, config.target, signed, fn Writer -> :ok end},
        key,
        @reason,
        Writer
      )
    after
      restore_env(:local_release_target, previous)
    end
  end

  defp upload!(variant) do
    config = Map.from_struct(variant.enrollment)
    signed = evidence(variant)

    envelope =
      ~s({"signed_manifest":) <>
        signed.signed_manifest_bytes <>
        ~s(,"payload":") <> Base.encode64(signed.payload) <> ~s("})

    assert {:ok, artifact} =
             ArtifactAdmission.admit(
               envelope,
               config.host,
               config.roots,
               System.system_time(:second)
             )

    assert {:ok, %{status: 201}} =
             Authorization.with_authorized_transaction(
               %{identity() | scopes: ["mixer.artifact.upload"]},
               "artifact.upload",
               config.target.scope,
               &PostgresStorage.upload(
                 &1,
                 artifact,
                 %{key: config.target.runtime_sha256, reason: @reason, source_ip: nil},
                 Map.merge(Map.take(config, [:roots, :host]), %{repo: Uploader})
               ),
               Uploader
             )
  end

  defp evidence(variant) do
    # Artifact upload retains the signed object's JSON span inside the envelope.
    signed = MixerHosted.Test.StagePromotionSigningFixture.evidence(variant)
    %{signed | signed_manifest_bytes: String.trim(signed.signed_manifest_bytes)}
  end

  defp seed_authorization! do
    for {table, values} <- [
          {"profiles", "'fixture',1,'https://issuer.example','local','human',true,1"},
          {"principals", "'person','human',true,0,1"},
          {"bindings", "'fixture',1,'person','human','person',true,1"},
          {"families", "'family','fixture',1,'person',true,0,NULL,1"},
          {"credentials", "'fixture',1,'credential','person','family',true,0,NULL,1"},
          {"organizations", "'org-a',true"},
          {"projects", "'org-a','project-a',true"},
          {"applications", "'org-a','project-a','fieldlog',true"},
          {"environments", "'org-a','project-a','fieldlog','development',true"},
          {"environments", "'org-a','project-a','fieldlog','staging',true"},
          {"organization_heads", "'org-a',1"},
          {"project_heads", "'org-a','project-a',1"},
          {"memberships",
           "'member','person','org-a','project-a','exact_project','owner',true,0,NULL,1"}
        ],
        do: admin("INSERT INTO public.mixer_authz_#{table} VALUES (#{values})")

    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis("org-a", "project-a")

    admin(
      "INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)",
      [genesis]
    )
  end

  defp identity do
    now = System.system_time(:second)

    %VerifiedIdentity{
      profile_id: "fixture",
      profile_version: 1,
      issuer: "https://issuer.example",
      client_id: "local",
      subject: "person",
      credential_ref: "credential",
      identity_class: :human,
      issued_at: now - 10,
      expires_at: now + 120,
      scopes: ["mixer.release.publish"]
    }
  end

  defp provision_route!(direction) do
    runtimes =
      for side <- [:source, :destination],
          platform <- [:ios, :android],
          do: Map.fetch!(direction, side)[platform].target.runtime_sha256

    admin(
      """
      INSERT INTO #{@route} (
        direction_id, writer_role, organization_id, project_id, application_id,
        source_environment_id, destination_environment_id,
        source_ios_runtime_sha256, source_ios_channel,
        source_android_runtime_sha256, source_android_channel,
        destination_ios_runtime_sha256, destination_ios_channel,
        destination_android_runtime_sha256, destination_android_channel
      ) VALUES ($1,'#{@writer}','org-a','project-a','fieldlog','development','staging',
                $2,'internal',$3,'internal',$4,'candidate',$5,'candidate')
      """,
      [@direction | runtimes]
    )
  end

  defp enroll!(target) do
    admin(
      """
      INSERT INTO #{@heads} (organization_id,project_id,application_id,environment_id,
                             platform,runtime_sha256,channel,writer_role)
      VALUES ($1,$2,$3,$4,$5,$6,$7,'#{@writer}')
      """,
      coordinates(target)
    )

    enroll_registry!(target)
  end

  defp enroll_registry!(target) do
    admin(
      """
      INSERT INTO #{@enrollment} (reader_role,organization_id,project_id,application_id,
                                  environment_id,platform,runtime_sha256,channel)
      VALUES ('mixer_release_delivery',$1,$2,$3,$4,$5,$6,$7)
      """,
      coordinates(target)
    )
  end

  defp coordinates(target) do
    scope = target.scope

    [
      scope.organization_id,
      scope.project_id,
      scope.application_id,
      scope.environment_id,
      target.platform,
      target.runtime_sha256,
      target.channel
    ]
  end

  defp grant! do
    for name <- ~w(profiles principals bindings families credentials organizations projects
                   applications environments organization_heads project_heads memberships),
        do: admin("GRANT SELECT ON public.mixer_authz_#{name} TO #{@writer}, #{@uploader}")

    for name <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          admin(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO #{@writer}, #{@uploader}"
          )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          admin(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO #{@uploader}"
          )

    for name <- ~w(artifacts audit_events idempotency),
        do: admin("GRANT SELECT, INSERT ON public.mixer_customer_#{name} TO #{@uploader}")

    admin(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO #{@uploader}"
    )

    admin("GRANT SELECT,UPDATE(sequence) ON #{@heads} TO #{@writer}")
    admin("GRANT SELECT,INSERT ON public.mixer_release_cli_requests TO #{@writer}")

    admin("""
    GRANT SELECT, INSERT (
      organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,
      sequence,previous_sequence,artifact_sha256,signed_assignment_bytes,rollout_basis_points,
      idempotency_key,reason,principal_id,action
    ) ON #{@publications} TO #{@writer}
    """)

    admin("""
    GRANT SELECT, INSERT (
      direction_id,writer_role,organization_id,project_id,application_id,
      source_environment_id,destination_environment_id,
      source_ios_runtime_sha256,source_ios_channel,source_android_runtime_sha256,source_android_channel,
      destination_ios_runtime_sha256,destination_ios_channel,
      destination_android_runtime_sha256,destination_android_channel,
      idempotency_key,request_sha256,principal_id,reason,
      source_ios_sequence,source_ios_artifact_sha256,source_android_sequence,source_android_artifact_sha256,
      destination_ios_sequence,destination_ios_artifact_sha256,
      destination_android_sequence,destination_android_artifact_sha256
    ) ON #{@binding} TO #{@writer}
    """)

    admin("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_publish_allowed(text,text,text,text),
      public.mixer_release_read_allowed(text,text,text,text),
      public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text),
      public.mixer_release_head_details(text,text,text,text,text,text,text),
      public.mixer_stage_promotion_admit(text),
      public.mixer_stage_promotion_source(text,numeric,numeric) TO #{@writer}
    """)

    assert [[@writer, @writer, false, false]] =
             sql(Writer, """
             SELECT current_user::text,session_user::text,rolsuper,rolbypassrls
             FROM pg_roles WHERE rolname=current_user
             """).rows
  end

  defp await_head_wait(deadline) do
    case admin("""
         SELECT count(*) FROM pg_stat_activity
         WHERE usename='#{@writer}' AND wait_event_type='Lock'
           AND query LIKE '%mixer_release_heads%FOR UPDATE%'
         """).rows do
      [[1]] ->
        :ok

      [[0]] ->
        assert System.monotonic_time(:millisecond) < deadline, "writer did not wait on the head"
        Process.sleep(5)
        await_head_wait(deadline)
    end
  end

  defp with_failure(clause, body, table, check) do
    admin("CREATE SEQUENCE public.stage_fixture_fault_seen")
    admin("GRANT USAGE ON SEQUENCE public.stage_fixture_fault_seen TO #{@writer}")

    admin("""
    CREATE FUNCTION public.stage_fixture_fail() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog AS $body$
    BEGIN #{body} END
    $body$
    """)

    kind = if String.starts_with?(clause, "AFTER"), do: "CONSTRAINT ", else: ""

    admin(
      "CREATE #{kind}TRIGGER stage_fixture_fail #{clause} EXECUTE FUNCTION public.stage_fixture_fail()"
    )

    try do
      check.()
    after
      admin("DROP TRIGGER stage_fixture_fail ON #{table}")
      admin("DROP FUNCTION public.stage_fixture_fail()")
      admin("DROP SEQUENCE public.stage_fixture_fault_seen")
    end
  end

  defp configure(key, value) do
    previous = Application.fetch_env(:mixer_hosted, key)
    Application.put_env(:mixer_hosted, key, value)
    on_exit(fn -> restore_env(key, previous) end)
  end

  defp restore_env(key, {:ok, value}), do: Application.put_env(:mixer_hosted, key, value)
  defp restore_env(key, :error), do: Application.delete_env(:mixer_hosted, key)

  defp assert_empty_destination do
    assert destination_heads() == [["android", nil], ["ios", nil]]
    assert [[2, 0]] == counts()

    if queue_enabled?(),
      do:
        assert(
          [[2, 0]] ==
            admin("""
            SELECT count(*),count(*) FILTER (WHERE args->>'environment_id'='staging') FROM #{@jobs}
            """).rows
        )
  end

  defp queue_enabled?, do: System.get_env("MIXER_STAGE_PROMOTION_QUEUE") == "1"

  defp migrate!(dir, name) do
    [{module, _}] = Code.require_file(Path.join(["priv", dir, name <> ".exs"]))
    [version, _] = String.split(name, "_", parts: 2)
    assert :ok = Ecto.Migrator.up(Migration, String.to_integer(version), module, log: false)
  end

  defp provision_queue!(options) do
    assert {_, 0} =
             System.cmd(
               "psql",
               [
                 "-X",
                 "-q",
                 "-w",
                 "-h",
                 options[:socket_dir],
                 "-U",
                 "stage_fixture_admin",
                 "-d",
                 options[:database],
                 "-f",
                 "../docs/operations/provision-local-release-jobs.sql"
               ],
               stderr_to_stdout: true
             )
  end

  defp start_queue_enabled_api!(options) do
    config =
      RuntimeConfig.load!(%{
        "MIXER_HOSTED_ROLE" => "api",
        "MIXER_DATABASE_HOST" => "db.example.test",
        "MIXER_DATABASE_NAME" => options[:database],
        "MIXER_DATABASE_USER" => @writer,
        "MIXER_DATABASE_PASSWORD" => "local socket fixture",
        "MIXER_LOCAL_RELEASE_JOBS_ENABLED" => "true",
        "MIXER_SECRET_KEY_BASE" => String.duplicate("a", 64)
      })

    # The fixture API uses its disposable UNIX socket and does not open HTTP.
    config = %{config | repo: [username: @writer] ++ options, endpoint: [server: false]}
    startup = {config, :disabled}

    configure(:role, config.role)
    configure(:identity_startup, config.identity_startup)
    configure(MixerHosted.Repo, config.repo)
    configure(Oban, config.oban)
    configure(MixerHostedWeb.Endpoint, config.endpoint)
    configure(:startup, startup)

    start_supervised!(%{
      id: MixerHosted.Supervisor,
      start: {MixerHosted.Application, :start, [:normal, []]},
      type: :supervisor
    })

    assert {:ok, ^startup} = MixerHosted.Application.startup()
  end

  defp destination_heads,
    do:
      admin(
        "SELECT platform,sequence::text FROM #{@heads} WHERE environment_id='staging' ORDER BY platform"
      ).rows

  defp counts,
    do:
      admin("SELECT (SELECT count(*) FROM #{@publications}),(SELECT count(*) FROM #{@binding})").rows

  defp admin(query, params \\ []), do: sql(Admin, query, params)

  defp sql(repo, query, params \\ []),
    do: Ecto.Adapters.SQL.query!(repo, query, params, log: false)
end
