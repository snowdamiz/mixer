defmodule MixerHosted.Test.ConfiguredReleaseReplayRepo do
  use Ecto.Repo, otp_app: :mixer_configured_release_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.ConfiguredReleaseReplayTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture, only: [http: 3, http: 5]
  alias MixerHosted.{Authorization, CustomerArtifacts, Releases}
  alias MixerHosted.CustomerArtifacts.{PostgresStorage, Schema, UploadRepo}

  alias MixerHosted.Identity.{
    ConfiguredVerifier,
    KeyOwner,
    StartupDNSFixture,
    StartupFixture,
    TLSFixture,
    VerifiedIdentity
  }

  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR}

  alias MixerHosted.Releases.{
    DeliveryExport,
    DeliveryPublishFence,
    DeliveryRepo,
    Target,
    WriterRepo
  }

  alias MixerHosted.Test.ConfiguredReleaseReplayRepo, as: FixtureRepo
  alias MixerHosted.Test.FieldLogReleasePacket
  alias MixerHostedWeb.LocalReleaseController

  @mode System.get_env("MIXER_RELEASE_FIXTURE_MODE")
  @fieldlog? @mode in ["fieldlog", "fieldlog-control"]
  @fence? @mode == "delivery-publish-fence"
  @multi_target? @mode in ["target-registry", "delivery-export"] or @fence?
  @stock_scopes "mixer.artifact.upload mixer.release.publish"
  @rollback_reason "Restore the signed FieldLog calculation baseline"
  @vector Path.expand("../../../../services/protocol/testdata/signed-release-v3.json", __DIR__)
  @principal "replay-owner"
  @subject "replay-subject"
  @credential "replay-token"
  @writer "mixer_replay_writer"
  @android_writer "mixer_replay_android_writer"
  @processor "mixer_release_processor"
  @reader "mixer_release_delivery"
  @stage "mixer_replay_stage"
  @uploader "mixer_artifact_uploader"
  @validate "/v3/orgs/org-a/projects/project-a/releases/validate"
  @publish "/v3/orgs/org-a/projects/project-a/channels/beta/publish"
  @coordinates ~w(organization_id project_id application_id environment_id platform runtime_sha256 channel)
  @columns Enum.join(@coordinates, ",")
  @bindings "$1,$2,$3,$4,$5,$6,$7"
  @export_reader "public.mixer_release_delivery_export(text,text,text,text,text,text,text)"
  @snapshot_reader "public.mixer_release_delivery_snapshot(text,text,text,text,text,text,text)"
  @publish_fence "public.mixer_release_delivery_lock_current(text,text,text,text,text,text,text)"
  @max_sequence 18_446_744_073_709_551_615

  @tag skip:
         @mode not in ["linux", "startup-only", "stock-cli", "stock-cli-startup"] and
           not @fieldlog?
  @tag timeout: if(@mode == "fieldlog", do: 1_700_000, else: 360_000)
  test "one ordinary API boot replays a signed local release through configured identity" do
    linux? = @mode in ["linux", "stock-cli", "fieldlog"]
    stock_cli? = @fieldlog? or @mode in ["stock-cli", "stock-cli-startup"]
    if linux?, do: assert_isolated_network!()
    if @mode in ["stock-cli", "fieldlog"], do: assert_isolated_pid!()

    vector = @vector |> File.read!() |> Jason.decode!()

    {vector, phases} =
      if @fieldlog? do
        delivery = System.fetch_env!("MIXER_RELEASE_FIELDLOG_PACKET")

        delivery =
          if @mode == "fieldlog-control" and delivery == "",
            do: FieldLogReleasePacket.synthetic!(scratch(), vector),
            else: delivery

        FieldLogReleasePacket.read!(delivery)
      else
        {vector, []}
      end

    signed = vector["signed_assignment"]
    first_signed = if @fieldlog?, do: Jason.decode!(hd(phases).signed), else: signed
    assignment = first_signed["assignment"]
    digest = assignment["artifact_sha256"]
    envelope = Jason.encode!(Map.take(vector, ~w(signed_manifest payload)))
    signed_bytes = Jason.encode!(signed)
    uploader_password = if stock_cli?, do: Base.encode16(:crypto.strong_rand_bytes(32))
    {dns, tls, key} = if linux?, do: start_issuer!(), else: {nil, nil, nil}
    load_runtime!(vector, assignment, tls, uploader_password)

    %{target: target} = config = Application.fetch_env!(:mixer_hosted, :local_release_target)
    assert Target.signed_scope(target) == assignment["scope"]

    assert target.runtime_sha256 == assignment["runtime"] and
             target.channel == assignment["channel"]

    phases = if @fieldlog?, do: FieldLogReleasePacket.admit!(phases, config), else: phases
    provision!(target)

    if stock_cli? do
      provision_uploader!(uploader_password)
    else
      stage!(config, digest, envelope)
    end

    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)

    try do
      assert {:ok, {%{identity_startup: %{mode: :configured, owner_options: opts}}, :disabled}} =
               MixerHosted.Application.startup()

      refute Keyword.has_key?(opts, :fixture)
      assert opts[:resolvers] == [{{127, 0, 0, 1}, 53}]
      assert :sys.get_state(KeyOwner).snapshots == %{}

      if linux?,
        do: assert(GenServer.call(dns, :queries) == [] and TLSFixture.info(tls).accepted == 0)

      assert {:ok, {{127, 0, 0, 1}, port}} = MixerHostedWeb.Endpoint.server_info(:http)
      client = %{http_port: port}
      assert %{status: 200} = http(client, "/health/live", [])

      for {repo, role} <- [{WriterRepo, @writer}, {DeliveryRepo, @reader}] do
        assert [[^role, true, false]] =
                 Ecto.Adapters.SQL.query!(repo, """
                 SELECT session_user::text, ssl,
                    has_any_column_privilege(current_user,'public.mixer_customer_artifacts','SELECT')
                 FROM pg_stat_ssl WHERE pid=pg_backend_pid()
                 """).rows
      end

      assert %{status: 401} =
               post(client, tenant_path(target) <> "/releases/validate", [], "validate", %{
                 artifact_sha256: digest
               })

      offer_query =
        Target.signed_scope(target)
        |> Map.merge(%{
          "runtime" => target.runtime_sha256,
          "channel" => target.channel,
          "installation" => vector["installation"]
        })
        |> URI.encode_query()

      offer_path = "/v3/updates?" <> offer_query
      artifact_path = artifact_path(target, digest)
      assert %{status: 204, body: ""} = http(client, offer_path, [])
      assert %{status: 404} = http(client, artifact_path, [])
      assert_ledger!([[nil]], [])
      if stock_cli?, do: assert_empty_upload!()
      if stock_cli?, do: assert_uploader!()

      if @mode == "stock-cli-startup", do: assert_relay_transport!(port)

      if @fieldlog? do
        run_fieldlog!(client, offer_path, target, phases, key)

        if linux? do
          # The maintained issuer may refresh during a device readback pause.
          query_types =
            for {~c"jwks.fixture.invalid", type} <- GenServer.call(dns, :queries), do: type

          assert :a in query_types and :aaaa in query_types
          assert %{accepted: count, requests: requests} = TLSFixture.info(tls)
          assert count > 0 and length(requests) == count
          assert Enum.all?(requests, &String.starts_with?(&1.request, "GET /keys HTTP/1.1\r\n"))
        end
      end

      if @mode == "stock-cli" do
        manifest = Jason.encode!(vector["signed_manifest"])

        expected_envelope =
          ~s({"signed_manifest":) <>
            manifest <>
            ~s(,"payload":) <>
            Jason.encode!(vector["payload"]) <> "}"

        cli_input = %{
          token: token(key, @stock_scopes, 300),
          manifest: manifest,
          assignment: signed_bytes,
          payload: vector["payload"]
        }

        expect_stock_cli!(port, cli_input, assignment)
        assert_cold_fetch!(dns, tls)
        assert_stock_cli_rows!(assignment, vector, expected_envelope, signed_bytes)
        assert_delivery!(client, offer_path, artifact_path, signed_bytes, expected_envelope)
        assert %{accepted: 1} = TLSFixture.info(tls)
      end

      if @mode == "linux" do
        token = token(key)
        headers = [{"authorization", "Bearer " <> token}]

        # The real release request is the first token use and must do the cold fetch.
        assert %{status: 200, body: validation} =
                 post(client, @validate, headers, "validate", %{artifact_sha256: digest})

        assert %{"artifact_sha256" => ^digest, "protocol_valid" => true} =
                 Jason.decode!(validation)

        assert_ledger!([[nil]], [])

        assert {:ok,
                %VerifiedIdentity{
                  profile_id: "startup-fixture",
                  subject: @subject,
                  credential_ref: @credential,
                  identity_class: :human,
                  scopes: ["mixer.release.publish"]
                }} =
                 ConfiguredVerifier.authenticate(token, System.system_time(:second))

        assert_cold_fetch!(dns, tls)

        assert %{status: 200, body: published} =
                 post(client, @publish, headers, "publish", %{signed_assignment: signed})

        %{"sequence" => sequence, "rollout_basis_points" => rollout} = assignment

        assert Jason.decode!(published) == %{
                 "sequence" => sequence,
                 "rollout_basis_points" => rollout,
                 "artifact_sha256" => digest,
                 "delivery" => "local_only"
               }

        assert %{status: 200, body: ^published} =
                 post(client, @publish, headers, "publish", %{signed_assignment: signed})

        sequence_text = Integer.to_string(sequence)

        assert_ledger!([[sequence_text]], [
          [sequence_text, digest, signed_bytes, @principal, "publish"]
        ])

        assert_delivery!(client, offer_path, artifact_path, signed_bytes, envelope)
        assert %{accepted: 1} = TLSFixture.info(tls)
      end
    after
      assert :ok = Application.stop(:mixer_hosted)
    end

    for name <- [
          MixerHosted.Supervisor,
          MixerHosted.Repo,
          MixerHostedWeb.Endpoint,
          KeyOwner,
          WriterRepo,
          DeliveryRepo,
          UploadRepo
        ],
        do: refute(Process.whereis(name))

    if linux? do
      for {fixture, pid} <- [{StartupDNSFixture, dns}, {TLSFixture, tls}] do
        stop_supervised!(fixture)
        refute Process.alive?(pid)
      end
    end

    IO.puts("Configured release replay completed in #{@mode} mode.")
  end

  defp assert_isolated_pid! do
    parent = System.fetch_env!("MIXER_RELEASE_PARENT_PIDNS")
    assert parent =~ ~r/\Apid:\[\d+\]\z/
    refute File.read_link!("/proc/self/ns/pid") == parent
  end

  @tag skip: @mode != "target-registry"
  @tag timeout: 60_000
  test "release jobs and signed delivery coexist in either migration order" do
    vector = @vector |> File.read!() |> Jason.decode!()
    assignment = vector["signed_assignment"]["assignment"]
    order = System.fetch_env!("MIXER_RELEASE_QUEUE_ORDER")
    default_scope = vector["host"]["scope"]
    {default_document, default_key} = signed_scope(vector, default_scope)
    android_scope = %{default_scope | "platform" => "android"}
    other_scope = %{default_scope | "organization" => "org-b"}
    {android_document, android_key} = signed_scope(vector, android_scope)
    {other_document, other_key} = signed_scope(vector, other_scope)

    env =
      load_runtime!(default_document, assignment, nil, nil, %{
        "MIXER_LOCAL_RELEASE_TARGET_REGISTRY" =>
          Jason.encode!([android_document, other_document]),
        "MIXER_LOCAL_RELEASE_JOBS_ENABLED" => "true"
      })

    processor =
      Map.take(env, ~w(MIXER_DATABASE_HOST MIXER_DATABASE_NAME))
      |> Map.merge(%{
        "MIXER_HOSTED_ROLE" => "processor",
        "MIXER_PROCESSOR_PROFILE" => "releases_v1",
        "MIXER_DATABASE_USER" => @processor,
        "MIXER_DATABASE_PASSWORD" => "synthetic-replay-processor"
      })

    %{target: default} =
      default_config = Application.fetch_env!(:mixer_hosted, :local_release_target)

    delivery = Application.fetch_env!(:mixer_hosted, :local_release_delivery)

    android =
      Enum.find_value(delivery.registry, fn {_, entry} ->
        entry.host["scope"] == android_scope && entry
      end)

    other =
      Enum.find_value(delivery.registry, fn {_, entry} ->
        entry.host["scope"] == other_scope && entry
      end)

    provision!(default)

    queue = migration("local_release_jobs", "20261120000014_add_local_release_jobs.exs")

    registry =
      migration(
        "local_release_target_registry",
        "20261120000015_add_local_release_target_registry.exs"
      )

    with_repo("mixer_replay_admin", fn ->
      sql!("GRANT CREATE ON DATABASE postgres TO mixer_replay_owner")
    end)

    with_ledger_owner(fn ->
      for file <- [
            "20261120000012_add_local_release_halt_audit.exs",
            "20261120000013_add_local_release_head_details.exs"
          ],
          do: assert(:ok == migrate(:up, migration("repo/migrations", file)))
    end)

    default_row = signed_release(vector, default_config, default_key, 7)
    next = signed_release(vector, default_config, default_key, 8)
    rollback_assignment = default_row.signed |> Jason.decode!() |> Map.fetch!("assignment")
    rollback_assignment = %{rollback_assignment | "sequence" => 9}

    rollback =
      default_row
      |> Map.merge(%{sequence: 9, action: :rollback})
      |> Map.put(
        :signed,
        Jason.encode!(sign_fixture("assignment", "assignment", rollback_assignment, default_key))
      )

    [first, current, staged] =
      for sequence <- [6, 8, 9], do: signed_release(vector, android, android_key, sequence)

    cross = signed_release(vector, other, other_key, 8)
    owner = fixture_identity()
    other_owner = fixture_identity("other-subject", "other-credential")

    stage!(default_config, default_row.digest, default_row.envelope)

    retained =
      case order do
        "queue-first" ->
          with_ledger_owner(fn ->
            assert :ok = migrate(:up, queue)
            # Reproduce the sequence-only index of the originally installed 000014.
            sql!("DROP INDEX IF EXISTS mixer_release_jobs.release_job_publication_reference")

            sql!("""
            CREATE UNIQUE INDEX IF NOT EXISTS release_job_publication_sequence
            ON mixer_release_jobs.oban_jobs ((args ->> 'sequence'))
            WHERE queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'
            """)
          end)

          provision_queue!()
          with_registry_http!(fn _ -> publish_and_replay!(default, default_row, owner) end)
          drain_queue!(processor, [{default, default_row}])

          snapshot = retained_queue!()
          assert [[_, %{"sequence" => "7"}, "completed", 1]] = elem(snapshot, 0)
          assert [[_, _, _]] = elem(snapshot, 1)
          assert_failed_queue_upgrade!(registry, snapshot)
          snapshot

        "registry-first" ->
          publish_fixture!(default, default_row, owner, @principal)
          {[], []}
      end

    with_registry_http!(fn client ->
      assert %{status: 204} = http(client, offer_path(default), [])
      assert %{status: 404} = http(client, artifact_path(default, default_row.digest), [])

      Application.put_env(:mixer_hosted, :local_release_delivery, Map.delete(delivery, :registry))
      assert_offer!(client, default, default_row, artifact_path(default, default_row.digest))
      Application.put_env(:mixer_hosted, :local_release_delivery, delivery)
    end)

    with_ledger_owner(fn ->
      assert :ok = migrate(:up, registry)

      if order == "registry-first" do
        assert :ok = migrate(:up, queue)
        assert :ok = migrate(:down, queue)

        assert [[true, true, nil]] =
                 sql!("""
                 SELECT to_regclass('public.mixer_release_delivery_enrollments') IS NOT NULL,
                        to_regnamespace('mixer_release_jobs') IS NOT NULL,
                        to_regclass('mixer_release_jobs.oban_jobs')
                 """).rows

        assert :ok = migrate(:up, queue)
      end

      assert [[nil, nil, true]] =
               sql!("""
               SELECT to_regclass('public.mixer_release_one_local_target'),
                      to_regclass('mixer_release_jobs.release_job_publication_sequence'),
                      to_regclass('mixer_release_jobs.release_job_publication_reference') IS NOT NULL
               """).rows
    end)

    assert retained_queue!() == retained
    provision_registry!(default, android.target, other.target)
    provision_queue!()

    for {config, release, identity, principal, publish?} <- [
          {android, first, owner, @principal, true},
          {android, current, owner, @principal, false},
          {android, staged, owner, @principal, false},
          {other, cross, other_owner, "other-owner", true}
        ] do
      stage!(config, release.digest, release.envelope, identity, "stage-" <> release.digest)

      if publish? do
        writer = if config.target == android.target, do: @android_writer, else: @writer
        publish_fixture!(config.target, release, identity, principal, writer)
      end
    end

    stage!(default_config, next.digest, next.envelope, owner, "stage-next")

    with_registry_http!(fn _ ->
      publish_and_replay!(default, next, owner)
      publish_and_replay!(default, rollback, owner)
    end)

    with_release_runtime!(
      Map.merge(env, %{
        "MIXER_DATABASE_USER" => @android_writer,
        "MIXER_DATABASE_PASSWORD" => "synthetic-replay-android-writer",
        "MIXER_LOCAL_RELEASE_CONFIG" => Jason.encode!(android_document),
        "MIXER_LOCAL_RELEASE_TARGET_REGISTRY" => Jason.encode!([default_document, other_document])
      }),
      fn ->
        with_registry_http!(fn _ ->
          publish_and_replay!(android.target, current, owner, @android_writer)
        end)
      end
    )

    {jobs, _} = retained_queue!()
    same_sequence = Enum.filter(jobs, fn [_, args, _, _] -> args["sequence"] == "8" end)

    assert [
             [default_id, default_args, "available", 0],
             [android_id, android_args, "available", 0]
           ] =
             same_sequence

    refute default_id == android_id
    assert default_args == queue_reference(default, next)
    assert android_args == queue_reference(android.target, current)
    expected = [{default, next}, {default, rollback}, {android.target, current}]
    expected = if order == "queue-first", do: [{default, default_row} | expected], else: expected
    assert length(jobs) == length(expected)
    repaired_attempt = retry_discarded_job!(android_id)
    drain_queue!(processor, expected)

    with_ledger_owner(fn ->
      assert_raise Postgrex.Error, ~r/release jobs storage contains retained work/, fn ->
        migrate(:down, queue)
      end
    end)

    {completed, offers} = retained_queue!()
    {initial_jobs, initial_offers} = retained
    assert length(completed) == length(expected) and length(offers) == length(expected)
    assert Enum.take(completed, length(initial_jobs)) == initial_jobs
    assert initial_offers -- offers == []
    assert [default_id, default_args, "completed", 1] in completed
    assert [android_id, android_args, "completed", repaired_attempt] in completed

    with_repo(@writer, fn ->
      assert {:ok, []} ==
               Authorization.with_authorized_transaction(
                 owner,
                 "release.publish",
                 default.scope,
                 fn _ ->
                   rows =
                     sql!(
                       """
                       SELECT sequence FROM public.mixer_release_heads
                       WHERE (#{@columns}) = (#{@bindings})
                       """,
                       coordinates(other.target)
                     ).rows

                   {:ok, rows}
                 end,
                 FixtureRepo
               )
    end)

    with_registry_http!(fn client ->
      assert_offer!(client, default, rollback, artifact_path(default, rollback.digest))

      assert %{status: 200, body: previous} =
               http(client, artifact_path(default, next.digest), [])

      assert previous == next.envelope

      assert_offer!(
        client,
        android.target,
        current,
        exact_artifact(android.target, current.digest)
      )

      assert %{status: 200, body: historical} =
               http(client, exact_artifact(android.target, first.digest), [])

      assert historical == first.envelope

      assert %{status: 204, body: ""} = http(client, offer_path(other.target), [])
      assert %{status: 404} = http(client, exact_artifact(other.target, cross.digest), [])
      assert %{status: 404} = http(client, exact_artifact(android.target, cross.digest), [])
      assert %{status: 404} = http(client, exact_artifact(android.target, staged.digest), [])

      assert %{status: 404} =
               http(
                 client,
                 exact_artifact(%{android.target | channel: "other"}, current.digest),
                 []
               )

      assert %{status: 404} = http(client, artifact_path(default, current.digest), [])

      assert %{status: 400} =
               http(client, artifact_path(default, current.digest) <> "&platform=android", [])

      assert %{status: 400} =
               http(
                 client,
                 String.replace(
                   exact_artifact(android.target, current.digest),
                   "environment=development",
                   "plat%66orm=android"
                 ),
                 []
               )

      assert_sql_delivery_denied!(other.target, cross.digest)
      assert [] = delivery_sql!(:artifact, coordinates(android.target) ++ [staged.digest])

      # Revocation is visible through the restricted SQL login on the next read.
      with_repo("mixer_replay_admin", fn ->
        assert %{num_rows: 1} =
                 sql!(
                   """
                   DELETE FROM public.mixer_release_delivery_enrollments
                   WHERE reader_role = '#{@reader}' AND (#{@columns}) = (#{@bindings})
                   """,
                   coordinates(android.target)
                 )
      end)

      assert_sql_delivery_denied!(android.target, first.digest)
      assert %{status: 204} = http(client, offer_path(android.target), [])
      assert %{status: 404} = http(client, exact_artifact(android.target, first.digest), [])
      enroll!(android.target)

      revoked =
        update_in(delivery, [:registry, android.target, :roots], fn roots ->
          Enum.map(roots, &Map.put(&1, "revoked", true))
        end)

      Application.put_env(:mixer_hosted, :local_release_delivery, revoked)
      assert [[%Decimal{}, _, _, _, _, _]] = delivery_sql!(:offer, coordinates(android.target))
      assert %{status: 204} = http(client, offer_path(android.target), [])
      assert %{status: 404} = http(client, exact_artifact(android.target, first.digest), [])
      assert %{status: 200} = http(client, artifact_path(default, default_row.digest), [])
    end)

    IO.puts(
      "Verified #{order} with distinct sequence-8 jobs #{default_id} and #{android_id}, exact replay, " <>
        "immutable projections, signed rollback, operator repair, schema rollback, and delivery revocation."
    )

    IO.puts("Historical HTTP envelope SHA-256 #{sha256(first.envelope)}")
  end

  @tag skip: @mode != "delivery-export" and not @fence?
  @tag timeout: 60_000
  test "private export retains bounded trusted history across a head change, promotion and halt" do
    vector = @vector |> File.read!() |> Jason.decode!()
    scope = vector["host"]["scope"]
    {document, artifact_key} = signed_scope(vector, scope)
    {history_document, history_key} = signed_scope(vector, scope)
    {android_document, android_key} = signed_scope(vector, %{scope | "platform" => "android"})
    {other_document, other_key} = signed_scope(vector, %{scope | "organization" => "org-b"})
    now = System.system_time(:second)
    history_expiry = now + 300
    artifact_expiry = now + 600
    assignment_expiry = now + 1_200
    [artifact_root] = document["roots"]
    artifact_root = %{artifact_root | "not_after_unix" => artifact_expiry}

    history_root = %{
      hd(history_document["roots"])
      | "key_id" => "export-history",
        "not_after_unix" => history_expiry
    }

    {public, assignment_key} = :crypto.generate_key(:eddsa, :ed25519)

    assignment_root = %{
      artifact_root
      | "key_id" => "export-assignment",
        "artifact" => false,
        "public_key" => Base.encode64(public),
        "not_after_unix" => assignment_expiry
    }

    document = %{document | "roots" => [artifact_root, assignment_root, history_root]}
    canary_document = %{document | "channel" => "canary"}

    load_runtime!(document, vector["signed_assignment"]["assignment"], nil, nil, %{
      "MIXER_LOCAL_RELEASE_TARGET_REGISTRY" =>
        Jason.encode!([android_document, other_document, canary_document])
    })

    %{target: target, roots: [artifact_root, assignment_root, history_root]} =
      config = Application.fetch_env!(:mixer_hosted, :local_release_target)

    delivery = Application.fetch_env!(:mixer_hosted, :local_release_delivery)

    {android, android_config} =
      Enum.find(delivery.registry, fn {t, _} -> t.platform == "android" end)

    {other, other_config} =
      Enum.find(delivery.registry, fn {t, _} -> t.scope.organization_id == "org-b" end)

    canary = %{target | channel: "canary"}
    canary_config = Map.fetch!(delivery.registry, canary)

    provision!(target)

    with_repo("mixer_replay_admin", fn ->
      sql!("GRANT CREATE ON DATABASE postgres TO mixer_replay_owner")
    end)

    with_ledger_owner(fn ->
      for {dir, file} <- [
            {"local_release_target_registry",
             "20261120000015_add_local_release_target_registry.exs"},
            {"local_release_delivery_export",
             "20261120000017_add_local_release_delivery_export.exs"},
            {"local_release_delivery_snapshot",
             "20261120000018_add_local_release_delivery_snapshot.exs"}
          ] do
        assert :ok = migrate(:up, migration(dir, file))
      end

      assert [[false, false, false, false]] =
               sql!("""
               SELECT has_function_privilege('#{@reader}','#{@export_reader}','EXECUTE'),
                      has_function_privilege('#{@writer}','#{@export_reader}','EXECUTE'),
                      has_function_privilege('#{@reader}','#{@snapshot_reader}','EXECUTE'),
                      has_function_privilege('#{@writer}','#{@snapshot_reader}','EXECUTE')
               """).rows

      sql!("GRANT EXECUTE ON FUNCTION #{@snapshot_reader} TO #{@reader}")
    end)

    provision_registry!(target, android, other)

    with_repo("mixer_replay_admin", fn -> seed_head!(canary) end)
    enroll!(canary)

    initial = signed_release(vector, %{config | roots: [history_root]}, history_key, 7)
    intermediate = signed_release(vector, config, artifact_key, 8)

    zero_offer =
      vector
      |> signed_release(config, artifact_key, 9)
      |> resign_export(assignment_root, assignment_key, 9, 0)

    current = signed_release(vector, config, artifact_key, @max_sequence - 2)
    staged = signed_release(vector, config, artifact_key, 100)
    cross = signed_release(vector, other_config, other_key, current.sequence)

    inconsistent =
      vector
      |> signed_release(android_config, android_key, current.sequence)
      |> resign_export(hd(android_config.roots), android_key, current.sequence, 42)

    owner = fixture_identity()
    other_owner = fixture_identity("other-subject", "other-credential")
    stage!(config, initial.digest, initial.envelope, owner, "export-initial")
    stage!(config, intermediate.digest, intermediate.envelope, owner, "export-intermediate")
    stage!(config, zero_offer.digest, zero_offer.envelope, owner, "export-zero-offer")
    stage!(config, current.digest, current.envelope, owner, "export-current")
    stage!(config, staged.digest, staged.envelope, owner, "export-staged-only")
    stage!(other_config, cross.digest, cross.envelope, other_owner, "export-cross")

    stage!(
      android_config,
      inconsistent.digest,
      inconsistent.envelope,
      owner,
      "export-inconsistent"
    )

    publish_fixture!(other, cross, other_owner, "other-owner")

    current = resign_export(current, assignment_root, assignment_key, current.sequence, 7_319)

    with_registry_http!(fn _ ->
      assert {:error, :not_found} = DeliveryExport.current(android)
      assert {:error, :not_found} = DeliveryExport.current(other)
      assert {:error, :not_found} = DeliveryExport.current(%{target | channel: "wrong"})
      assert {:error, :not_found} = DeliveryExport.current(target)

      # The lower-level SQL fixture records 10000 for an assignment signed for 42.
      publish_fixture!(android, inconsistent, owner, @principal, @android_writer)
      assert {:error, :rejected} = DeliveryExport.current(android)

      publish_fixture!(target, initial, owner, @principal, @writer, fn ->
        assert {:error, :not_found} = DeliveryExport.current(target)
      end)

      initial_artifact = export_artifact(initial)
      intermediate_artifact = export_artifact(intermediate)
      current_artifact = export_artifact(current)

      assert {:ok, %{head: %{sequence: "7"}, artifacts: [^initial_artifact]} = prior_export} =
               DeliveryExport.current(target)

      publish_fixture!(target, intermediate, owner, @principal, @writer, fn ->
        assert {:ok, %{head: %{sequence: "7"}, artifacts: [^initial_artifact]}} =
                 DeliveryExport.current(target)
      end)

      assert {:ok,
              %{head: %{sequence: "8"}, artifacts: [^intermediate_artifact, ^initial_artifact]}} =
               DeliveryExport.current(target)

      publish_and_replay!(target, zero_offer, owner)

      assert {:ok,
              %{
                head: %{sequence: "9", enabled: false},
                artifact: nil,
                artifacts: [^intermediate_artifact, ^initial_artifact]
              }} = DeliveryExport.current(target)

      assert_history_window!(vector, canary_config, artifact_key, owner)
      publish_and_replay!(target, current, owner)

      assert {:ok, export} = DeliveryExport.current(target)
      assert export.target == wire_target(target)

      assert export.head == %{
               sequence: Integer.to_string(current.sequence),
               assignment_sha256: sha256(current.signed),
               artifact_sha256: current.digest,
               rollout_basis_points: 7_319,
               enabled: true
             }

      assert export.assignment_bytes == current.signed

      assert export.artifact == current_artifact
      assert export.artifacts == [current_artifact, intermediate_artifact, initial_artifact]
      assert export.valid_until_unix == history_expiry

      if @fence?,
        do: assert_publish_fence!(target, android, other, export, prior_export, delivery)

      promotion =
        current
        |> resign_export(assignment_root, assignment_key, @max_sequence - 1, 9_000)
        |> Map.merge(%{sequence: @max_sequence - 1, action: :promote})

      publish_and_replay!(target, promotion, owner)

      assert {:ok, promoted} = DeliveryExport.current(target)
      assert promoted.head.sequence == Integer.to_string(@max_sequence - 1)
      assert promoted.head.rollout_basis_points == 9_000
      assert promoted.assignment_bytes == promotion.signed
      assert promoted.artifact == current_artifact
      assert promoted.artifacts == export.artifacts
      assert promoted.valid_until_unix == history_expiry

      for inactive <- [
            %{history_root | "not_after_unix" => now},
            %{history_root | "revoked" => true},
            %{history_root | "public_key" => artifact_root["public_key"]}
          ] do
        Application.put_env(:mixer_hosted, :local_release_delivery, %{
          delivery
          | roots: [artifact_root, assignment_root, inactive]
        })

        assert {:ok, filtered} = DeliveryExport.current(target)
        assert filtered.artifacts == [current_artifact, intermediate_artifact]
        assert filtered.valid_until_unix == artifact_expiry

        if @fence?, do: assert_fence_refused!(target, promoted, :rejected)
      end

      for inactive <- [
            %{assignment_root | "not_before_unix" => now + 600},
            %{assignment_root | "not_after_unix" => now},
            %{assignment_root | "revoked" => true}
          ] do
        Application.put_env(:mixer_hosted, :local_release_delivery, %{
          delivery
          | roots: [artifact_root, inactive, history_root]
        })

        assert {:error, :rejected} = DeliveryExport.current(target)
        if @fence?, do: assert_fence_refused!(target, promoted, :rejected)
      end

      roots = [%{artifact_root | "not_after_unix" => now}, assignment_root, history_root]
      Application.put_env(:mixer_hosted, :local_release_delivery, %{delivery | roots: roots})
      Application.put_env(:mixer_hosted, :local_release_target, %{config | roots: roots})
      assert {:error, :rejected} = DeliveryExport.current(target)

      halt = resign_export(promotion, assignment_root, assignment_key, @max_sequence, 0)

      health = %{
        "sequence" => promotion.sequence,
        "activated" => 3,
        "pending" => 2,
        "adverse_signals" => 1
      }

      route = {scope["organization"], scope["project"], target.channel}

      assert {:ok, %{sequence: @max_sequence}} =
               Releases.cli(
                 owner,
                 route,
                 {:halt, halt.signed, health},
                 "export-halt",
                 sha256(halt.signed),
                 "Halt the incomplete rollout"
               )

      assert {:ok, stopped} = DeliveryExport.current(target)
      assert stopped.target == export.target
      assert stopped.assignment_bytes == halt.signed
      assert stopped.artifact == nil
      assert stopped.artifacts == [initial_artifact]
      assert stopped.valid_until_unix == history_expiry

      if @fence? do
        assert_fence_refused!(target, promoted, :rejected)

        assert {:ok, :applied} =
                 DeliveryPublishFence.with_current(target, stopped, fn window ->
                   assert window.valid_until_unix == history_expiry
                   :applied
                 end)
      end

      assert stopped.head == %{
               sequence: Integer.to_string(@max_sequence),
               assignment_sha256: sha256(halt.signed),
               artifact_sha256: current.digest,
               rollout_basis_points: 0,
               enabled: false
             }

      Application.put_env(:mixer_hosted, :local_release_delivery, delivery)
      assert {:ok, trusted_halt} = DeliveryExport.current(target)
      assert trusted_halt.artifact == nil
      assert trusted_halt.artifacts == export.artifacts

      expired_history = %{history_root | "not_after_unix" => now}
      roots = [hd(roots), assignment_root, expired_history]
      Application.put_env(:mixer_hosted, :local_release_delivery, %{delivery | roots: roots})

      assert {:ok, %{artifacts: [], valid_until_unix: ^assignment_expiry}} =
               DeliveryExport.current(target)

      roots = [hd(roots), %{assignment_root | "revoked" => true}, expired_history]
      Application.put_env(:mixer_hosted, :local_release_delivery, %{delivery | roots: roots})
      assert {:error, :rejected} = DeliveryExport.current(target)

      if @fence? do
        assert_fence_refused!(target, trusted_halt, :rejected)
        Application.put_env(:mixer_hosted, :local_release_delivery, delivery)
        assert_fence_database_loss!(target, trusted_halt)
      end
    end)
  end

  defp assert_publish_fence!(target, android, other, export, prior, delivery) do
    assert {:ok, ^export} = DeliveryExport.current(target)
    assert_fence_refused!(target, export, :unavailable)

    with_ledger_owner(fn ->
      assert :ok =
               migrate(
                 :up,
                 migration(
                   "local_release_delivery_export",
                   "20261120000019_add_local_release_delivery_publish_fence.exs"
                 )
               )

      assert [[false, false, false, false, false]] =
               sql!("""
               SELECT has_function_privilege('#{@reader}','#{@publish_fence}','EXECUTE'),
                      has_function_privilege('#{@writer}','#{@publish_fence}','EXECUTE'),
                      has_table_privilege('#{@reader}','public.mixer_release_heads','SELECT'),
                      has_table_privilege('#{@reader}','public.mixer_release_heads','UPDATE'),
                      has_table_privilege('#{@reader}','public.mixer_release_delivery_enrollments','UPDATE')
               """).rows

      assert_fence_refused!(target, export, :unavailable)
      sql!("GRANT EXECUTE ON FUNCTION #{@publish_fence} TO #{@reader}")
    end)

    assert {:ok, ^export} = DeliveryExport.current(target)
    assert_fence_refused!(target, prior, :rejected)

    assert_fence_refused!(
      target,
      %{export | valid_until_unix: export.valid_until_unix + 1},
      :rejected
    )

    assert_fence_refused!(other, export, :not_found)
    assert_fence_refused!(%{target | channel: "wrong"}, export, :not_found)

    assert {:error, :unavailable} = DeliveryExport.current_in_transaction(target)

    assert {:ok, :checked} =
             DeliveryRepo.transaction(fn ->
               assert {:error, :unavailable} = DeliveryExport.current(target)
               assert_fence_refused!(target, export, :unavailable)
               :checked
             end)

    heads = "public.mixer_release_heads"
    enrollments = "public.mixer_release_delivery_enrollments"

    with_repo("mixer_replay_admin", fn ->
      for table <- [heads, enrollments] do
        assert {:ok, :checked} =
                 FixtureRepo.transaction(fn ->
                   assert %{num_rows: 1} = fixture_lock!(table, target)
                   assert_fence_refused!(target, export, :busy)
                   :checked
                 end)
      end

      {:ok, pointer} = Agent.start_link(fn -> nil end)

      try do
        cas = fn window ->
          assert window.valid_until_unix == export.valid_until_unix
          assert System.monotonic_time(:millisecond) < window.deadline_monotonic_ms

          for table <- [heads, enrollments] do
            assert {:error, %Postgrex.Error{postgres: %{code: :lock_not_available}}} =
                     Ecto.Adapters.SQL.query(
                       FixtureRepo,
                       fixture_lock_query(table),
                       coordinates(target),
                       log: false
                     )

            assert %{num_rows: 1} = fixture_lock!(table, android)
          end

          Agent.get_and_update(pointer, fn
            nil -> {:applied, export.head}
            current -> {:conflict, current}
          end)
        end

        assert {:ok, :applied} = DeliveryPublishFence.with_current(target, export, cas)
        assert {:error, :conflict} = DeliveryPublishFence.with_current(target, export, cas)
        assert Agent.get(pointer, & &1) == export.head
      after
        Agent.stop(pointer)
      end

      caller = self()

      assert {:error, :indeterminate} =
               DeliveryPublishFence.with_current(target, export, fn _ ->
                 send(caller, {:stalled_cas, self()})

                 receive do
                   :finish -> :applied
                 end
               end)

      assert_received {:stalled_cas, pid}
      refute Process.alive?(pid)
      assert %{num_rows: 1} = fixture_lock!(heads, target)
      assert %{num_rows: 1} = fixture_lock!(enrollments, target)

      assert %{num_rows: 1} =
               sql!(
                 "DELETE FROM #{enrollments} WHERE (#{@columns}) = (#{@bindings})",
                 coordinates(target)
               )

      assert_fence_refused!(target, export, :not_found)
    end)

    enroll!(target)

    try do
      assert {:error, :indeterminate} =
               DeliveryPublishFence.with_current(target, export, fn _ ->
                 roots = Enum.map(delivery.roots, &Map.put(&1, "revoked", true))

                 Application.put_env(:mixer_hosted, :local_release_delivery, %{
                   delivery
                   | roots: roots
                 })

                 :applied
               end)

      assert_fence_refused!(target, export, :rejected)
    after
      Application.put_env(:mixer_hosted, :local_release_delivery, delivery)
    end
  end

  defp assert_fence_database_loss!(target, export) do
    with_repo("mixer_replay_admin", fn ->
      assert {:error, :indeterminate} =
               DeliveryPublishFence.with_current(target, export, fn _ ->
                 assert [[true]] =
                          sql!("""
                          SELECT pg_terminate_backend(pid, 250)
                          FROM pg_stat_activity
                          WHERE usename='#{@reader}' AND state='idle in transaction'
                          """).rows

                 :applied
               end)
    end)

    # The runner owns this cluster and still owns its filesystem cleanup.
    assert {_, 0} =
             System.cmd(
               "pg_ctl",
               ["-D", Path.join(scratch(), "db"), "-w", "-t", "10", "-m", "fast", "stop"],
               stderr_to_stdout: true
             )

    assert_fence_refused!(target, export, :unavailable)
  end

  defp assert_fence_refused!(target, export, reason) do
    caller = self()
    marker = make_ref()

    assert {:error, ^reason} =
             DeliveryPublishFence.with_current(target, export, fn _ ->
               send(caller, marker)
               :applied
             end)

    refute_received ^marker
  end

  defp fixture_lock!(table, target), do: sql!(fixture_lock_query(table), coordinates(target))

  defp fixture_lock_query(table) do
    "SELECT 1 FROM #{table} WHERE (#{@columns}) = (#{@bindings}) FOR UPDATE NOWAIT"
  end

  defp assert_history_window!(vector, config, key, owner) do
    releases =
      for sequence <- 1..33 do
        release = signed_release(vector, config, key, sequence)
        stage!(config, release.digest, release.envelope, owner, "export-canary-#{sequence}")
        publish_fixture!(config.target, release, owner, @principal)
        release
      end

    [latest | older] = Enum.reverse(releases)
    expected = Enum.map([latest | Enum.take(older, 31)], &export_artifact/1)

    assert {:ok, %{head: %{sequence: "33"}, artifacts: ^expected}} =
             DeliveryExport.current(config.target)

    repeated =
      latest
      |> resign_export(hd(config.roots), key, 34, 10_000)
      |> Map.put(:sequence, 34)

    publish_fixture!(config.target, repeated, owner, @principal)

    deduplicated = Enum.take(expected, 31)

    assert {:ok, %{head: %{sequence: "34"}, artifacts: ^deduplicated}} =
             DeliveryExport.current(config.target)
  end

  defp export_artifact(release) do
    %{
      manifest_sha256: release.digest,
      envelope_sha256: sha256(release.envelope),
      envelope_bytes: release.envelope
    }
  end

  defp resign_export(release, root, key, sequence, rollout) do
    %{"assignment" => assignment} = Jason.decode!(release.signed)

    assignment = %{
      assignment
      | "key_id" => root["key_id"],
        "sequence" => sequence,
        "rollout_basis_points" => rollout
    }

    %{release | signed: Jason.encode!(sign_fixture("assignment", "assignment", assignment, key))}
  end

  defp publish_and_replay!(target, release, identity, writer \\ @writer) do
    assert [[^writer, true]] =
             WriterRepo.query!("""
             SELECT session_user::text, ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()
             """).rows

    route = {target.scope.organization_id, target.scope.project_id, target.channel}
    reason = "Publish a signed release in the registry fixture"
    action = Map.get(release, :action, :publish)
    key = "#{action}-#{release.sequence}"

    assert {:ok, _} =
             Releases.cli(
               identity,
               put_elem(route, 2, nil),
               {:validate, release.digest},
               "validate-#{release.sequence}",
               sha256("validate:" <> release.digest),
               reason
             )

    command = {action, release.signed, nil}
    hash = sha256(release.signed)
    assert {:ok, published} = Releases.cli(identity, route, command, key, hash, reason)

    assert %{sequence: release.sequence, signed_assignment_bytes: release.signed} ==
             Map.take(published, [:sequence, :signed_assignment_bytes])

    assert {:ok, ^published} = Releases.cli(identity, route, command, key, hash, reason)
  end

  defp queue_reference(target, release) do
    Map.new(Enum.zip(@coordinates, coordinates(target)))
    |> Map.merge(%{"version" => 1, "sequence" => Integer.to_string(release.sequence)})
  end

  defp provision_queue! do
    assert "" == release_jobs_sql!("provision-local-release-jobs.sql")

    with_repo("mixer_replay_admin", fn ->
      sql!("ALTER ROLE #{@processor} PASSWORD 'synthetic-replay-processor'")
    end)
  end

  defp retry_discarded_job!(job_id) do
    max_attempts =
      with_repo("mixer_replay_admin", fn ->
        [[max_attempts]] =
          sql!(
            """
            UPDATE mixer_release_jobs.oban_jobs
            SET state='discarded', attempt=max_attempts, discarded_at=now()
            WHERE id=$1 AND state='available'
            RETURNING max_attempts
            """,
            [job_id]
          ).rows

        max_attempts
      end)

    args = ["-v", "release_job_id=#{job_id}"]

    assert release_jobs_sql!("retry-local-release-job.sql", args) ==
             "#{job_id}|#{max_attempts}|#{max_attempts + 1}"

    assert "" == release_jobs_sql!("retry-local-release-job.sql", args)
    max_attempts + 1
  end

  defp release_jobs_sql!(name, args \\ []) do
    {output, status} =
      System.cmd(
        "psql",
        [
          "-X",
          "-q",
          "-At",
          "-w",
          "-h",
          scratch(),
          "-U",
          "mixer_replay_admin",
          "-d",
          "postgres"
        ] ++ args ++ ["-f", "../docs/operations/#{name}"],
        stderr_to_stdout: true
      )

    assert status == 0, output
    String.trim(output)
  end

  defp with_ledger_owner(run) do
    with_repo("mixer_replay_admin", run,
      after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE mixer_replay_owner", []) end
    )
  end

  defp retained_queue! do
    with_repo("mixer_replay_admin", fn ->
      {
        sql!("SELECT id,args,state::text,attempt FROM mixer_release_jobs.oban_jobs ORDER BY id").rows,
        sql!(
          "SELECT platform,sequence::text,signed_assignment_bytes FROM mixer_release_jobs.offer_materializations ORDER BY platform,sequence"
        ).rows
      }
    end)
  end

  defp assert_failed_queue_upgrade!(registry, {jobs, [[_, _, signed]]}) do
    with_repo("mixer_replay_admin", fn ->
      assert %{num_rows: 1} =
               sql!(
                 "UPDATE mixer_release_jobs.offer_materializations SET signed_assignment_bytes=$1",
                 [signed <> <<0>>]
               )
    end)

    invalid = retained_queue!()

    with_ledger_owner(fn ->
      assert_raise Postgrex.Error,
                   ~r/retained release queue work does not match the immutable ledger/,
                   fn ->
                     migrate(:up, registry)
                   end

      assert [[true, true, nil, nil]] =
               sql!("""
               SELECT to_regclass('public.mixer_release_one_local_target') IS NOT NULL,
                      to_regclass('mixer_release_jobs.release_job_publication_sequence') IS NOT NULL,
                      to_regclass('mixer_release_jobs.release_job_publication_reference'),
                      to_regclass('public.mixer_release_delivery_enrollments')
               """).rows
    end)

    assert retained_queue!() == invalid

    with_repo("mixer_replay_admin", fn ->
      assert %{num_rows: 1} =
               sql!(
                 "UPDATE mixer_release_jobs.offer_materializations SET signed_assignment_bytes=$1",
                 [signed]
               )
    end)

    assert {^jobs, [[_, _, ^signed]]} = retained_queue!()
  end

  defp drain_queue!(processor, expected) do
    with_release_runtime!(
      processor,
      fn ->
        assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)

        try do
          assert [[@processor, true]] =
                   MixerHosted.Repo.query!("""
                   SELECT session_user::text, ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()
                   """).rows

          with_repo("mixer_replay_admin", fn ->
            await_completed!(length(expected), System.monotonic_time(:millisecond) + 8_000)

            rows =
              sql!("""
              SELECT #{Enum.map_join(@coordinates, ",", &"m.#{&1}")}, m.sequence::text,
                     m.signed_assignment_bytes,m.artifact_sha256,m.rollout_basis_points,m.action
              FROM mixer_release_jobs.offer_materializations m
              JOIN public.mixer_release_publications p USING (#{@columns},sequence)
              WHERE (m.signed_assignment_bytes,m.artifact_sha256,m.rollout_basis_points,m.action)
                  = (p.signed_assignment_bytes,p.artifact_sha256,p.rollout_basis_points,p.action)
              """).rows

            assert MapSet.new(rows) ==
                     MapSet.new(expected, fn {target, release} ->
                       coordinates(target) ++
                         [
                           Integer.to_string(release.sequence),
                           release.signed,
                           release.digest,
                           10000,
                           Atom.to_string(Map.get(release, :action, :publish))
                         ]
                     end)
          end)
        after
          :ok = Application.stop(:mixer_hosted)
        end
      end
    )
  end

  defp await_completed!(count, deadline) do
    rows = sql!("SELECT state::text FROM mixer_release_jobs.oban_jobs ORDER BY id").rows

    unless rows == List.duplicate(["completed"], count) do
      assert System.monotonic_time(:millisecond) < deadline,
             "Release jobs failed to drain: #{inspect(rows)}"

      Process.sleep(50)
      await_completed!(count, deadline)
    end
  end

  defp with_release_runtime!(env, run) do
    prior = Application.get_all_env(:mixer_hosted)

    try do
      if env["MIXER_HOSTED_ROLE"] == "processor" do
        for key <- [:local_release_target, :local_release_delivery, WriterRepo],
            do: Application.delete_env(:mixer_hosted, key)
      end

      apply_runtime!(env)
      run.()
    after
      restore_runtime!(prior)
    end
  end

  defp with_registry_http!(run) do
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)

    try do
      assert {:ok, {{127, 0, 0, 1}, port}} = MixerHostedWeb.Endpoint.server_info(:http)
      client = %{http_port: port}
      assert %{status: 200} = http(client, "/health/live", [])

      assert [[@reader, true]] =
               Ecto.Adapters.SQL.query!(DeliveryRepo, """
               SELECT session_user, ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()
               """).rows

      run.(client)
    after
      :ok = Application.stop(:mixer_hosted)
    end

    assert {:ok, socket} = :gen_tcp.listen(47301, ip: {127, 0, 0, 1}, reuseaddr: true)
    :ok = :gen_tcp.close(socket)
  end

  defp provision_registry!(default, android, other) do
    with_repo("mixer_replay_admin", fn ->
      seed_head!(android, @android_writer)
      seed_identity!("other-owner", "other-subject", "other-credential", "other-family")
      seed_scope!(other, "other-owner", "other-membership")
      seed_head!(other)

      assert [[false, false, false, false]] =
               sql!("""
               SELECT has_table_privilege('#{@reader}','public.mixer_release_delivery_enrollments','SELECT'),
                      has_table_privilege('#{@reader}','public.mixer_release_delivery_enrollments','INSERT'),
                      has_table_privilege('#{@reader}','public.mixer_release_publications','SELECT'),
                      has_table_privilege('#{@writer}','public.mixer_release_delivery_enrollments','INSERT')
               """).rows
    end)

    enroll!(default)
    enroll!(android)
  end

  defp enroll!(target) do
    with_repo(
      "mixer_replay_admin",
      fn ->
        sql!(
          """
          INSERT INTO public.mixer_release_delivery_enrollments (reader_role,#{@columns})
          VALUES ('#{@reader}',#{@bindings})
          """,
          coordinates(target)
        )
      end,
      after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE mixer_replay_owner", []) end
    )
  end

  defp publish_fixture!(
         target,
         release,
         identity,
         principal,
         writer \\ @writer,
         before_commit \\ fn -> :ok end
       ) do
    with_repo(writer, fn ->
      assert {:ok, :published} =
               Authorization.with_authorized_transaction(
                 identity,
                 "release.publish",
                 target.scope,
                 fn _ ->
                   args = coordinates(target)

                   assert [[previous]] =
                            sql!(
                              """
                              SELECT sequence FROM public.mixer_release_heads
                              WHERE (#{@columns}) = (#{@bindings}) FOR UPDATE
                              """,
                              args
                            ).rows

                   sequence = Decimal.new(release.sequence)

                   sql!(
                     """
                     INSERT INTO public.mixer_release_publications (#{@columns},sequence,
                       previous_sequence,artifact_sha256,signed_assignment_bytes,
                       rollout_basis_points,idempotency_key,reason,principal_id)
                     VALUES (#{@bindings},$8,$9,$10,$11,10000,$12,'Synthetic fixture publication',$13)
                     """,
                     args ++
                       [
                         sequence,
                         previous,
                         release.digest,
                         release.signed,
                         "sequence-#{release.sequence}",
                         principal
                       ]
                   )

                   assert %{num_rows: 1} =
                            sql!(
                              """
                              UPDATE public.mixer_release_heads SET sequence=$8
                              WHERE (#{@columns}) = (#{@bindings})
                              """,
                              args ++ [sequence]
                            )

                   before_commit.()
                   {:ok, :published}
                 end,
                 FixtureRepo
               )
    end)
  end

  defp fixture_identity(subject \\ @subject, credential \\ @credential) do
    now = System.system_time(:second)

    %VerifiedIdentity{
      profile_id: "startup-fixture",
      profile_version: 1,
      issuer: StartupFixture.entry()["profile"]["issuer"],
      subject: subject,
      credential_ref: credential,
      client_id: "reviewed-client",
      identity_class: :human,
      issued_at: now - 1,
      expires_at: now + 120,
      scopes: String.split(@stock_scopes)
    }
  end

  defp signed_scope(vector, scope) do
    {public, private} = :crypto.generate_key(:eddsa, :ed25519)

    root = %{
      hd(vector["roots"])
      | "scope" => scope,
        "public_key" => Base.encode64(public),
        "assignment" => true
    }

    {%{"host" => %{vector["host"] | "scope" => scope}, "channel" => "beta", "roots" => [root]},
     private}
  end

  defp signed_release(vector, config, key, sequence) do
    root = hd(config.roots)
    now = System.system_time(:second)

    manifest = %{
      vector["signed_manifest"]["manifest"]
      | "scope" => root["scope"],
        "key_id" => root["key_id"],
        "release_id" => "synthetic-#{sequence}",
        "created_at_unix" => now
    }

    {:ok, cbor} = ArtifactCBOR.encode(manifest)
    digest = sha256(cbor)
    signed_manifest = sign_fixture("manifest", "artifact", manifest, key)

    offer = %{
      vector["signed_assignment"]["assignment"]
      | "scope" => root["scope"],
        "key_id" => root["key_id"],
        "channel" => config.target.channel,
        "sequence" => sequence,
        "release_id" => manifest["release_id"],
        "artifact_sha256" => digest,
        "created_at_unix" => now
    }

    %{
      sequence: sequence,
      digest: digest,
      envelope:
        Jason.encode!(%{"signed_manifest" => signed_manifest, "payload" => vector["payload"]}),
      signed: Jason.encode!(sign_fixture("assignment", "assignment", offer, key))
    }
  end

  defp sign_fixture(field, domain, body, key) do
    {:ok, cbor} = ArtifactCBOR.encode(body)
    signature = :crypto.sign(:eddsa, :none, "mixer.#{domain}.v3\0" <> cbor, [key, :ed25519])
    %{field => body, "signature" => Base.encode64(signature)}
  end

  defp coordinates(target) do
    filter = Target.filter(target)
    Enum.map(@coordinates, &Keyword.fetch!(filter, String.to_existing_atom(&1)))
  end

  defp offer_path(target),
    do:
      "/v3/updates?" <>
        URI.encode_query(Map.put(wire_target(target), "installation", "fixture-installation"))

  defp exact_artifact(target, digest),
    do: "/v3/artifacts/#{digest}?" <> URI.encode_query(wire_target(target))

  defp wire_target(target),
    do:
      Map.merge(Target.signed_scope(target), %{
        "runtime" => target.runtime_sha256,
        "channel" => target.channel
      })

  defp assert_offer!(client, target, release, expected_url) do
    assert %{status: 200, body: body} = http(client, offer_path(target), [])

    assert body ==
             ~s({"signed_assignment":) <>
               release.signed <> ~s(,"artifact_url":) <> Jason.encode!(expected_url) <> "}"

    assert %{status: 200, body: bytes} = http(client, expected_url, [])
    assert bytes == release.envelope
  end

  defp assert_sql_delivery_denied!(target, digest) do
    assert [] = delivery_sql!(:offer, coordinates(target))
    assert [] = delivery_sql!(:artifact, coordinates(target) ++ [digest])
  end

  defp delivery_sql!(kind, args) do
    bindings = if kind == :offer, do: @bindings, else: @bindings <> ",$8"

    Ecto.Adapters.SQL.query!(
      DeliveryRepo,
      "SELECT * FROM public.mixer_release_delivery_#{kind}(#{bindings})",
      args
    ).rows
  end

  defp assert_isolated_network! do
    assert :os.type() == {:unix, :linux}
    parent = System.fetch_env!("MIXER_RELEASE_PARENT_NETNS")
    assert parent =~ ~r/\Anet:\[\d+\]\z/
    refute File.read_link!("/proc/self/ns/net") == parent

    assert [%{"ifname" => "lo"}] = ip!(["link", "show"])

    assert [%{"ifname" => "lo", "flags" => flags, "addr_info" => addresses}] =
             ip!(["-4", "address", "show"])

    assert "UP" in flags
    assert Enum.any?(addresses, &(&1["local"] == "8.8.8.8" and &1["prefixlen"] == 32))

    for family <- ["-4", "-6"], route <- ip!([family, "route", "show", "table", "all"]) do
      assert route["dev"] == "lo" and route["dst"] != "default"
    end
  end

  defp ip!(args) do
    assert {json, 0} = System.cmd("ip", ["-j" | args])
    Jason.decode!(json)
  end

  defp start_issuer! do
    tls = start_supervised!({TLSFixture, ip: {8, 8, 8, 8}, port: 443})
    dns = start_supervised!(StartupDNSFixture)
    key = JOSE.JWK.generate_key({:rsa, 2048})
    {_, public} = key |> JOSE.JWK.to_public() |> JOSE.JWK.to_map()
    jwk = Map.merge(public, %{"kid" => "startup-key", "alg" => "RS256", "use" => "sig"})
    TLSFixture.configure(tls, {:body, Jason.encode!(%{"keys" => [jwk]})})
    {dns, tls, key}
  end

  defp assert_cold_fetch!(dns, tls) do
    query_types =
      for {~c"jwks.fixture.invalid", type} <- GenServer.call(dns, :queries), do: type

    assert Enum.sort(query_types) == [:a, :aaaa]

    assert %{accepted: 1, key_dir_removed: true, requests: [%{request: request}]} =
             TLSFixture.info(tls)

    assert String.starts_with?(request, "GET /keys HTTP/1.1\r\n")
  end

  defp assert_delivery!(client, offer_path, artifact_path, signed_bytes, envelope) do
    offer =
      ~s({"signed_assignment":) <>
        signed_bytes <>
        ~s(,"artifact_url":) <>
        Jason.encode!(artifact_path) <> "}"

    assert %{status: 200, body: ^offer} = http(client, offer_path, [])
    assert %{status: 200, body: ^envelope} = http(client, artifact_path, [])

    assert %{status: 204} =
             http(client, String.replace(offer_path, "channel=beta", "channel=stable"), [])
  end

  defp expect_stock_cli!(port, input, assignment) do
    with_cli_relay!(port, fn _path ->
      expect_cli!(scratch(), input, assignment, "publish", fn ->
        IO.puts("Stock CLI ready at #{scratch()}. Waiting up to 240 seconds.")
      end)
    end)
  end

  defp expect_cli!(directory, input, assignment, action, ready) do
    bootstrap = Path.join(directory, "cli-input.json")
    result = Path.join(directory, "cli-result.json")
    bytes = Jason.encode!(input) <> "\n"
    assert byte_size(bytes) <= 131_072

    try do
      File.write!(bootstrap, bytes, [:exclusive])
      ready.()

      expected = %{
        "status" => "ok",
        "action" => action,
        "artifact_sha256" => assignment["artifact_sha256"],
        "sequence" => assignment["sequence"],
        "rollout_basis_points" => assignment["rollout_basis_points"],
        "delivery" => "local_only"
      }

      wait_for_result!(result, System.monotonic_time(:millisecond) + 240_000)

      assert {:ok, %{"first" => ^expected, "replay" => ^expected}} =
               result |> File.read!() |> Jason.decode()
    after
      assert File.rm(bootstrap) in [:ok, {:error, :enoent}]
    end
  end

  defp run_fieldlog!(%{http_port: port} = client, offer_path, target, phases, key) do
    with_cli_relay!(port, fn socket ->
      for phase <- phases do
        sequence = phase.assignment["sequence"]
        past = Enum.take(phases, sequence)
        directory = Path.join(scratch(), "phase-#{sequence}")

        if @mode == "fieldlog" do
          File.mkdir!(directory)

          input = %{
            token: token(key, @stock_scopes, 300),
            manifest: phase.manifest,
            payload: Base.encode64(phase.payload),
            assignment: phase.signed
          }

          expect_cli!(directory, input, phase.assignment, Atom.to_string(phase.action), fn ->
            IO.puts(
              "FieldLog CLI ready phase=#{sequence} scratch=#{scratch()} action=#{phase.action}"
            )
          end)
        else
          control_phase!(target, phase, List.last(phases))
        end

        assert_fieldlog_rows!(target, past)

        assert_delivery!(
          client,
          offer_path,
          artifact_path(target, phase.digest),
          phase.signed,
          phase.envelope
        )

        for artifact <- Enum.uniq_by(phases, & &1.digest), artifact.digest != phase.digest do
          path = artifact_path(target, artifact.digest)

          if Enum.any?(past, &(&1.digest == artifact.digest)) do
            assert %{status: 200, body: body} = http(client, path, [])
            assert body == artifact.envelope
          else
            assert %{status: 404} = http(client, path, [])
          end
        end

        path = String.replace(offer_path, "platform=android", "platform=ios")
        assert %{status: 204, body: ""} = http(client, path, [])

        if @mode == "fieldlog-control" do
          assert {phase.envelope, 0} ==
                   relay_curl(socket, artifact_path(target, phase.digest))
        end

        if @mode == "fieldlog" do
          IO.puts("FieldLog Android ready phase=#{sequence} digest=#{phase.digest}")
          ack = Path.join(directory, "android-ack")
          wait_for_result!(ack, System.monotonic_time(:millisecond) + 300_000)
          assert File.read!(ack) == "#{sequence}\n"
        end
      end
    end)
  end

  defp control_phase!(target, phase, rollback) do
    # Begin at the verified-identity boundary. Configured JWKS and real stock
    # CLI transport are exercised by the isolated Linux mode.
    now = System.system_time(:second)

    identity = %VerifiedIdentity{
      profile_id: "startup-fixture",
      profile_version: 1,
      issuer: StartupFixture.entry()["profile"]["issuer"],
      subject: @subject,
      credential_ref: @credential,
      client_id: "reviewed-client",
      identity_class: :human,
      issued_at: now - 1,
      expires_at: now + 120,
      scopes: String.split(@stock_scopes)
    }

    if phase.action == :publish do
      scope = target.scope
      tenant = %{organization_id: scope.organization_id, project_id: scope.project_id}

      upload_key =
        cli_key("PUT", tenant_path(target) <> "/artifacts/" <> phase.digest, phase.envelope)

      for _ <- 1..2 do
        assert {:ok, %{status: 201}} =
                 CustomerArtifacts.upload_at(
                   identity,
                   tenant,
                   phase.digest,
                   upload_key,
                   phase.envelope,
                   %{reason: "local development operation", source_ip: "127.0.0.1"}
                 )

        assert %{status: 200} =
                 control_request(
                   target,
                   identity,
                   :validate,
                   Jason.encode!(%{artifact_sha256: phase.digest})
                 )
      end

      if phase.assignment["sequence"] == 1 do
        assert %{status: 409, resp_body: body} =
                 control_request(target, identity, :rollback, assignment_body(rollback))

        assert %{"error" => %{"code" => "invalid_rollback"}} = Jason.decode!(body)
        assert_ledger!([[nil]], [])
      end
    end

    expected = %{
      "artifact_sha256" => phase.digest,
      "sequence" => phase.assignment["sequence"],
      "rollout_basis_points" => phase.assignment["rollout_basis_points"],
      "delivery" => "local_only"
    }

    for _ <- 1..2 do
      assert %{status: 200, resp_body: body} =
               control_request(target, identity, phase.action, assignment_body(phase))

      assert Jason.decode!(body) == expected
    end
  end

  defp control_request(target, identity, action, body) do
    scope = target.scope
    path = tenant_path(target)
    params = %{"organization_id" => scope.organization_id, "project_id" => scope.project_id}

    {path, params} =
      if action == :validate,
        do: {path <> "/releases/validate", params},
        else:
          {path <> "/channels/#{target.channel}/#{action}",
           Map.put(params, "channel", target.channel)}

    reason = if action == :rollback, do: @rollback_reason, else: ""
    key = cli_key("POST", path, body, reason)

    conn =
      Plug.Test.conn("POST", path, body)
      |> Map.put(:path_params, params)
      |> Plug.Conn.assign(:verified_identity, identity)
      |> Plug.Conn.put_req_header("content-type", "application/json")
      |> Plug.Conn.put_req_header("idempotency-key", key)

    conn =
      if reason == "", do: conn, else: Plug.Conn.put_req_header(conn, "x-mixer-reason", reason)

    LocalReleaseController.call(conn, LocalReleaseController.init(action))
  end

  defp assert_fieldlog_rows!(target, phases) do
    phase = List.last(phases)
    published = Enum.filter(phases, &(&1.action == :publish))
    sequence = Integer.to_string(phase.assignment["sequence"])

    assert_ledger!(
      [[sequence]],
      Enum.map(phases, fn row ->
        [
          Integer.to_string(row.assignment["sequence"]),
          row.digest,
          row.signed,
          @principal,
          Atom.to_string(row.action)
        ]
      end)
    )

    with_repo("mixer_replay_admin", fn ->
      assert sql!("SELECT sequence FROM public.mixer_customer_artifact_heads").rows ==
               [[length(published)]]

      assert sql!("""
             SELECT manifest_sha256, payload_sha256, envelope_bytes, payload, creating_sequence
             FROM public.mixer_customer_artifacts ORDER BY creating_sequence
             """).rows ==
               Enum.with_index(published, 1)
               |> Enum.map(fn {row, index} ->
                 [row.digest, row.payload_sha, row.envelope, row.payload, index]
               end)

      credential = sha256(["mixer.hosted.customer.credential_ref.v2", 0, @credential])

      expected_audit =
        Enum.map(published, &[&1.digest, @principal, credential, "artifact.upload", "created"])

      assert sql!("""
             SELECT manifest_sha256, display->'actor'->>0, display->'actor'->>8,
               display->>'action', display->>'outcome'
             FROM public.mixer_customer_audit_events ORDER BY sequence
             """).rows == expected_audit

      assert sql!("SELECT count(*) FROM public.mixer_customer_idempotency").rows == [
               [length(published)]
             ]

      expected_requests =
        Enum.map(published, &[@principal, &1.digest, nil]) ++
          Enum.map(phases, &[@principal, &1.digest, Integer.to_string(&1.assignment["sequence"])])

      assert sql!("""
             SELECT principal_id, artifact_sha256, publication_sequence::text
             FROM public.mixer_release_cli_requests
             """).rows
             |> Enum.sort() == Enum.sort(expected_requests)

      expected_keys =
        Enum.map(phases, fn row ->
          reason = if row.action == :rollback, do: @rollback_reason, else: ""
          path = tenant_path(target) <> "/channels/#{target.channel}/#{row.action}"
          [cli_key("POST", path, assignment_body(row), reason)]
        end)

      assert sql!(
               "SELECT idempotency_key FROM public.mixer_release_publications ORDER BY sequence"
             ).rows ==
               expected_keys
    end)
  end

  defp assignment_body(phase), do: ~s({"signed_assignment":) <> phase.signed <> "}"

  defp artifact_path(target, digest) do
    tenant =
      URI.encode_query(
        organization: target.scope.organization_id,
        project: target.scope.project_id
      )

    "/v3/artifacts/#{digest}?" <> tenant
  end

  defp tenant_path(target),
    do: "/v3/orgs/#{target.scope.organization_id}/projects/#{target.scope.project_id}"

  defp assert_relay_transport!(port) do
    with_cli_relay!(port, fn path ->
      for _ <- 1..2 do
        assert {"200", 0} =
                 relay_curl(path, "/health/live", [
                   "--output",
                   "/dev/null",
                   "--write-out",
                   "%{http_code}"
                 ])
      end
    end)
  end

  defp relay_curl(socket, path, options \\ []) do
    System.cmd("curl", [
      "--silent",
      "--show-error",
      "--fail",
      "--noproxy",
      "*",
      "--max-time",
      "5",
      "--unix-socket",
      socket
      | options ++ ["http://127.0.0.1" <> path]
    ])
  end

  defp with_cli_relay!(port, operation) do
    path = Path.join(scratch(), "cli.sock")
    supervisor = start_supervised!(Task.Supervisor)
    opts = [:binary, active: false, send_timeout: 2000, send_timeout_close: true]
    {:ok, listener} = :gen_tcp.listen(0, opts ++ [ifaddr: {:local, path}])

    try do
      File.chmod!(path, 0o600)

      {:ok, _} =
        Task.Supervisor.start_child(supervisor, fn ->
          relay_accept(supervisor, listener, port, opts)
        end)

      operation.(path)
    after
      :ok = :gen_tcp.close(listener)
      stop_supervised!(Task.Supervisor)
      refute Process.alive?(supervisor)
      File.rm!(path)
    end
  end

  defp wait_for_result!(path, deadline) do
    case File.lstat(path) do
      {:ok, %File.Stat{type: :regular, size: size}} when size in 1..8192 ->
        :ok

      {:error, :enoent} ->
        assert System.monotonic_time(:millisecond) < deadline, "Stock CLI result timed out"
        Process.sleep(100)
        wait_for_result!(path, deadline)

      _ ->
        flunk("Invalid or incomplete stock CLI result")
    end
  end

  defp relay_accept(supervisor, listener, port, opts) do
    case :gen_tcp.accept(listener) do
      {:ok, incoming} ->
        with {:ok, owner} <-
               Task.Supervisor.start_child(supervisor, fn -> relay_connect(port, opts) end),
             :ok <- :gen_tcp.controlling_process(incoming, owner) do
          send(owner, {:socket, incoming})
        else
          _ -> :gen_tcp.close(incoming)
        end

        relay_accept(supervisor, listener, port, opts)

      {:error, :closed} ->
        :ok
    end
  end

  defp relay_connect(port, opts) do
    receive do
      {:socket, incoming} ->
        with {:ok, outgoing} <- :gen_tcp.connect({127, 0, 0, 1}, port, opts, 2000),
             :ok <- :inet.setopts(incoming, active: :once),
             :ok <- :inet.setopts(outgoing, active: :once) do
          relay(incoming, outgoing)
        end
    after
      2000 -> :ok
    end
  end

  defp relay(left, right) do
    receive do
      {:tcp, from, bytes} when from in [left, right] ->
        to = if from == left, do: right, else: left

        with :ok <- :gen_tcp.send(to, bytes),
             :ok <- :inet.setopts(from, active: :once) do
          relay(left, right)
        end

      {:tcp_closed, _} ->
        :ok

      {:tcp_error, _, _} ->
        :ok
    after
      45_000 -> :ok
    end
  end

  defp token(key, scope \\ "mixer.release.publish", lifetime \\ 120) do
    claims = %{
      "iss" => StartupFixture.entry()["profile"]["issuer"],
      "aud" => "mixer-api",
      "client_id" => "reviewed-client",
      "sub" => @subject,
      "jti" => @credential,
      "iat" => System.system_time(:second) - 1,
      "exp" => System.system_time(:second) + lifetime,
      "scope" => scope
    }

    {_, compact} =
      key
      |> JOSE.JWS.sign(Jason.encode!(claims), %{
        "alg" => "RS256",
        "typ" => "at+jwt",
        "kid" => "startup-key"
      })
      |> JOSE.JWS.compact()

    compact
  end

  defp load_runtime!(vector, assignment, tls, uploader_password, extra_env \\ %{}) do
    pem = File.read!(Path.join(scratch(), "ca.pem"))

    jwks_ca =
      if tls, do: [{:Certificate, GenServer.call(tls, :authority).ca, :not_encrypted}], else: []

    ca_path = Path.join(scratch(), "trust.pem")
    File.write!(ca_path, pem <> :public_key.pem_encode(jwks_ca))
    assert :ok = :public_key.cacerts_load(ca_path)

    env = %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "127.0.0.1",
      "MIXER_DATABASE_NAME" => "postgres",
      "MIXER_DATABASE_USER" => @writer,
      "MIXER_DATABASE_PASSWORD" => "synthetic-replay-writer",
      "MIXER_DATABASE_POOL_SIZE" => "2",
      "MIXER_HTTP_BIND" => "127.0.0.1",
      "MIXER_HTTP_PORT" => "47301",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-replay-", 5),
      "MIXER_IDENTITY_MODE" => "configured",
      "MIXER_IDENTITY_CONFIG" => Jason.encode!(StartupFixture.envelope()),
      "MIXER_LOCAL_RELEASE_CONFIG" =>
        Jason.encode!(Map.put(Map.take(vector, ~w(host roots)), "channel", assignment["channel"])),
      "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD" => "synthetic-replay-reader",
      "MIXER_LOCAL_RELEASE_WRITER_ENABLED" => "true"
    }

    env =
      if uploader_password do
        Map.merge(env, %{
          "MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED" => "true",
          "MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD" => uploader_password
        })
      else
        env
      end

    env = Map.merge(env, extra_env)
    prior = Application.get_all_env(:mixer_hosted)
    apply_runtime!(env)

    on_exit(fn ->
      restore_runtime!(prior)
      :public_key.cacerts_clear()
    end)

    env
  end

  defp apply_runtime!(env) do
    prior = Application.get_all_env(:mixer_hosted)
    System.put_env(env)

    try do
      runtime = Config.Reader.read!("config/runtime.exs", env: :prod)
      Application.put_all_env(Config.Reader.merge([mixer_hosted: prior], runtime))
    after
      Enum.each(Map.keys(env), &System.delete_env/1)
    end
  end

  defp restore_runtime!(prior) do
    for {key, _} <- Application.get_all_env(:mixer_hosted),
        do: Application.delete_env(:mixer_hosted, key)

    Application.put_all_env(mixer_hosted: prior)
  end

  defp provision!(target) do
    with_repo("mixer_replay_admin", fn ->
      if @multi_target? do
        sql!(
          "CREATE ROLE #{@android_writer} LOGIN NOINHERIT PASSWORD 'synthetic-replay-android-writer'"
        )
      end

      for sql <- [
            "CREATE ROLE mixer_replay_owner NOLOGIN NOINHERIT",
            "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
            "ALTER SCHEMA public OWNER TO mixer_replay_owner",
            "CREATE ROLE #{@writer} LOGIN NOINHERIT PASSWORD 'synthetic-replay-writer'",
            "CREATE ROLE #{@reader} LOGIN NOINHERIT PASSWORD 'synthetic-replay-reader'",
            "CREATE ROLE #{@stage} LOGIN NOINHERIT"
          ],
          do: sql!(sql)
    end)

    with_repo(
      "mixer_replay_admin",
      fn ->
        migrations = [
          {"repo/migrations", "20261024000000_add_oban.exs"},
          {"repo/migrations", "20261025000003_add_customer_authorization.exs"},
          {"repo/migrations", "20261025000004_add_authorization_state_revisions.exs"},
          {"repo/migrations", "20261025000005_add_customer_artifact_storage.exs"},
          {"repo/migrations", "20261120000001_add_local_release_ledger.exs"},
          {"repo/migrations", "20261120000002_add_local_release_head_read.exs"},
          {"local_release_delivery", "20261120000003_add_local_release_delivery.exs"},
          {"repo/migrations", "20261120000004_add_local_release_cli_requests.exs"},
          {"repo/migrations", "20261120000010_add_local_release_publication_action.exs"},
          {"repo/migrations", "20261120000011_add_local_release_halt_health.exs"}
        ]

        for {dir, file} <- migrations, do: assert(:ok == migrate(:up, migration(dir, file)))

        grant!()
      end,
      after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE mixer_replay_owner", []) end
    )

    with_repo("mixer_replay_admin", fn -> seed!(target) end)
  end

  defp migration(dir, file) do
    [{module, _}] = Code.require_file(Path.join(["priv", dir, file]))
    [version, _] = String.split(file, "_", parts: 2)
    {String.to_integer(version), module}
  end

  defp migrate(direction, {version, module}),
    do: apply(Ecto.Migrator, direction, [FixtureRepo, version, module, [log: false]])

  defp provision_uploader!(password) do
    assert {_, 0} =
             System.cmd("psql", [
               "-X",
               "-q",
               "-w",
               "-v",
               "ON_ERROR_STOP=1",
               "-h",
               scratch(),
               "-U",
               "mixer_replay_admin",
               "-d",
               "postgres",
               "-f",
               "../docs/operations/provision-local-artifact-uploader.sql"
             ])

    with_repo("mixer_replay_admin", fn ->
      # The password contains only hex digits and travels over the private admin socket.
      case Ecto.Adapters.SQL.query(
             FixtureRepo,
             "ALTER ROLE #{@uploader} PASSWORD '#{password}'",
             [],
             log: false
           ) do
        {:ok, _} -> :ok
        {:error, _} -> flunk("Could not set the fixture uploader password")
      end
    end)
  end

  defp assert_uploader! do
    assert [[@uploader, true, false]] =
             Ecto.Adapters.SQL.query!(UploadRepo, """
             SELECT session_user::text, ssl,
               has_table_privilege(current_user,'public.mixer_release_publications','INSERT')
             FROM pg_stat_ssl WHERE pid=pg_backend_pid()
             """).rows

    assert {:ok, :ok} =
             UploadRepo.transaction(fn -> PostgresStorage.check_topology!(UploadRepo) end)
  end

  defp assert_empty_upload! do
    with_repo("mixer_replay_admin", fn ->
      assert sql!("SELECT sequence FROM public.mixer_customer_artifact_heads").rows == [[0]]

      for table <-
            ~w(mixer_customer_artifacts mixer_customer_audit_events mixer_customer_idempotency mixer_release_cli_requests),
          do: assert(sql!("SELECT 1 FROM public.#{table} LIMIT 1").rows == [])
    end)
  end

  defp assert_stock_cli_rows!(assignment, vector, envelope, signed_bytes) do
    digest = vector["artifact_sha256"]
    payload = Base.decode64!(vector["payload"])
    payload_sha = vector["signed_manifest"]["manifest"]["payload_sha256"]
    credential_sha = sha256(["mixer.hosted.customer.credential_ref.v2", 0, @credential])
    sequence = Integer.to_string(assignment["sequence"])
    upload_path = "/v3/orgs/org-a/projects/project-a/artifacts/" <> digest
    upload_key = cli_key("PUT", upload_path, envelope)
    publish_key = cli_key("POST", @publish, [~s({"signed_assignment":), signed_bytes, "}"])

    assert_ledger!([[sequence]], [[sequence, digest, signed_bytes, @principal, "publish"]])

    with_repo("mixer_replay_admin", fn ->
      assert sql!("SELECT sequence FROM public.mixer_customer_artifact_heads").rows == [[1]]

      assert sql!("""
             SELECT manifest_sha256, payload_sha256, envelope_bytes, payload, creating_sequence
             FROM public.mixer_customer_artifacts
             """).rows == [[digest, payload_sha, envelope, payload, 1]]

      assert [[1, ^digest, @principal, ^credential_sha, "artifact.upload", "created", request]] =
               sql!("""
               SELECT sequence, manifest_sha256, display->'actor'->>0, display->'actor'->>8,
                 display->>'action', display->>'outcome', display->>'request_sha256'
               FROM public.mixer_customer_audit_events
               """).rows

      assert sql!("""
             SELECT key, principal_id, action, manifest_sha256, payload_sha256, event_sequence,
               status, request_sha256
             FROM public.mixer_customer_idempotency
             """).rows == [
               [upload_key, @principal, "artifact.upload", digest, payload_sha, 1, 201, request]
             ]

      assert sql!("""
             SELECT principal_id, artifact_sha256, publication_sequence::text
             FROM public.mixer_release_cli_requests ORDER BY publication_sequence NULLS FIRST
             """).rows == [[@principal, digest, nil], [@principal, digest, sequence]]

      assert sql!("SELECT idempotency_key FROM public.mixer_release_publications").rows ==
               [[publish_key]]
    end)
  end

  defp cli_key(method, path, body, reason \\ ""),
    do: sha256(["mixer-local-release-v3", 0, method, 0, path, 0, reason, 0, body])

  defp sha256(bytes), do: :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)

  defp seed!(target) do
    profile = StartupFixture.entry()["profile"]

    sql!(
      "INSERT INTO public.mixer_authz_profiles VALUES ($1,1,$2,$3,'human',true,1)",
      [profile["profile_id"], profile["issuer"], profile["client_id"]]
    )

    seed_identity!(@principal, @subject, @credential, "replay-family")
    seed_scope!(target, @principal, "replay-member")
    seed_head!(target)
  end

  defp seed_identity!(principal, subject, credential, family) do
    sql!("INSERT INTO public.mixer_authz_principals VALUES ($1,'human',true,0,1)", [principal])

    sql!(
      "INSERT INTO public.mixer_authz_bindings VALUES ('startup-fixture',1,$1,'human',$2,true,1)",
      [subject, principal]
    )

    sql!(
      "INSERT INTO public.mixer_authz_families VALUES ($1,'startup-fixture',1,$2,true,0,NULL,1)",
      [family, principal]
    )

    sql!(
      "INSERT INTO public.mixer_authz_credentials VALUES ('startup-fixture',1,$1,$2,$3,true,0,NULL,1)",
      [credential, principal, family]
    )
  end

  defp seed_scope!(target, principal, membership) do
    %{organization_id: org, project_id: project, application_id: app, environment_id: env} =
      target.scope

    for {table, values, args} <- [
          {"organizations", "$1,true", [org]},
          {"projects", "$1,$2,true", [org, project]},
          {"applications", "$1,$2,$3,true", [org, project, app]},
          {"environments", "$1,$2,$3,$4,true", [org, project, app, env]},
          {"organization_heads", "$1,1", [org]},
          {"project_heads", "$1,$2,1", [org, project]},
          {"memberships", "$1,$2,$3,$4,'exact_project','owner',true,0,NULL,1",
           [membership, principal, org, project]}
        ],
        do: sql!("INSERT INTO public.mixer_authz_#{table} VALUES (#{values})", args)

    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis(org, project)

    sql!(
      "INSERT INTO public.mixer_customer_artifact_heads VALUES ($1,$2,0,'',$3)",
      [org, project, genesis]
    )
  end

  defp seed_head!(target, writer \\ @writer) do
    sql!(
      """
      INSERT INTO public.mixer_release_heads
        (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,writer_role)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
      """,
      coordinates(target) ++ [writer]
    )
  end

  defp grant! do
    writers = if @multi_target?, do: "#{@writer}, #{@android_writer}", else: @writer
    sql!("GRANT USAGE ON SCHEMA public TO #{writers}, #{@reader}, #{@stage}")

    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: sql!("GRANT SELECT ON public.mixer_authz_#{table} TO #{writers}, #{@stage}")

    for helper <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          sql!(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO #{writers}, #{@stage}"
          )

    for table <- ~w(artifacts audit_events idempotency),
        do: sql!("GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO #{@stage}")

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          sql!(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO #{@stage}"
          )

    sql!(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO #{@stage}"
    )

    sql!("GRANT SELECT,UPDATE(sequence) ON public.mixer_release_heads TO #{writers}")
    sql!("GRANT SELECT,INSERT ON public.mixer_release_cli_requests TO #{writers}")

    sql!("""
    GRANT SELECT, INSERT (
      organization_id, project_id, application_id, environment_id, platform, runtime_sha256, channel,
      sequence, previous_sequence, artifact_sha256, signed_assignment_bytes, rollout_basis_points,
      idempotency_key, reason, principal_id, action,
      health_activated, health_pending, health_adverse_signals
    ) ON public.mixer_release_publications TO #{writers}
    """)

    sql!("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_publish_allowed(text,text,text,text),
      public.mixer_release_read_allowed(text,text,text,text),
      public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text) TO #{writers}
    """)

    sql!("""
    GRANT EXECUTE ON FUNCTION public.mixer_release_delivery_offer(text,text,text,text,text,text,text),
      public.mixer_release_delivery_artifact(text,text,text,text,text,text,text,text) TO #{@reader}
    """)
  end

  # Feed the existing storage path through a fixture-only SQL login before boot.
  defp stage!(config, digest, envelope, identity \\ fixture_identity(), key \\ "stage") do
    %{target: target, host: host, roots: roots} = config
    now = System.system_time(:second)

    assert {:ok, %{manifest_sha256: ^digest} = artifact} =
             ArtifactAdmission.admit(envelope, host, roots, now)

    with_repo(@stage, fn ->
      config = %{repo: FixtureRepo, host: host, roots: roots}
      command = %{key: key, reason: "Stage synthetic signed release", source_ip: nil}

      assert {:ok, %{status: 201}} =
               Authorization.with_authorized_transaction(
                 identity,
                 "artifact.upload",
                 target.scope,
                 &PostgresStorage.upload(&1, artifact, command, config),
                 FixtureRepo
               )
    end)
  end

  defp post(client, path, bearer, key, command) do
    body = Jason.encode!(command)

    headers =
      bearer ++
        [
          {"content-type", "application/json"},
          {"content-length", Integer.to_string(byte_size(body))},
          {"idempotency-key", key},
          {"x-mixer-reason", "Replay synthetic signed release"}
        ]

    http(client, path, headers, "POST", body)
  end

  defp assert_ledger!(heads, publications) do
    with_repo("mixer_replay_admin", fn ->
      assert sql!("SELECT sequence::text FROM public.mixer_release_heads").rows == heads

      assert sql!(
               "SELECT sequence::text, artifact_sha256, signed_assignment_bytes, principal_id, action FROM public.mixer_release_publications ORDER BY sequence"
             ).rows == publications
    end)
  end

  defp scratch, do: System.fetch_env!("MIXER_RELEASE_FIXTURE_SCRATCH")

  defp with_repo(user, operation, options \\ []) do
    settings = [
      username: user,
      database: "postgres",
      socket_dir: scratch(),
      ssl: false,
      pool_size: 2,
      log: false
    ]

    {:ok, repo} = FixtureRepo.start_link(settings ++ options)

    try do
      assert [[1]] = sql!("SELECT 1").rows
      operation.()
    after
      Supervisor.stop(repo)
    end
  end

  defp sql!(sql, params \\ []), do: Ecto.Adapters.SQL.query!(FixtureRepo, sql, params, log: false)
end
