Code.require_file("../browser_auth/storage_fixture.exs", __DIR__)

defmodule MixerHosted.Releases.BrowserPublicationTest.Uploader do
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.BrowserPublicationTest do
  use ExUnit.Case, async: false
  import MixerHosted.Test.OrdinaryBrowserStartupFixture

  import MixerHosted.Test.StagePromotionSigningFixture,
    only: [variant: 5, vector: 0, publication: 1]

  alias MixerHosted.Audit.CustomerArtifactEvent
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner, Store, StoredSnapshot, Vault}
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.Identity.{ConfiguredVerifier, KeyOwner}
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, AssignmentV3}
  alias MixerHosted.Releases.BrowserPublicationTest.Uploader
  alias MixerHosted.Releases.EnvironmentPromotion.Direction
  alias MixerHosted.Releases.ReleaseJobs.ProcessorAdmission
  alias MixerHosted.Releases.{DeliveryRepo, RuntimeProvisioning, Target, WriterRepo}
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB
  alias MixerHosted.Test.StockReleaseCLI

  @head "/console-api/v1/release-head"
  @reason "Publish the local development release"
  @tenant %{organization_id: "org-a", project_id: "project-a"}
  @fixtures Path.expand("../../../../services/protocol/testdata", __DIR__)
  @max_sequence 18_446_744_073_709_551_615
  @promotion_direction "dev-to-stage"
  @promotion_path "/v3/orgs/org-a/projects/project-a/apps/fieldlog/release-promotions/" <>
                    @promotion_direction

  test "public delivery refuses a second listener in the effective endpoint settings" do
    hosted =
      MixerHosted.RuntimeConfig.load!(%{
        "MIXER_HOSTED_ROLE" => "api",
        "MIXER_DATABASE_HOST" => "db.fixture.example",
        "MIXER_DATABASE_NAME" => "mixer_fixture",
        "MIXER_DATABASE_USER" => "mixer_fixture",
        "MIXER_DATABASE_PASSWORD" => "synthetic-database-secret",
        "MIXER_SECRET_KEY_BASE" => String.duplicate("fixture-", 8)
      })

    fixture = @fixtures |> Path.join("signed-release-v3.json") |> File.read!() |> Jason.decode!()
    assignment = fixture["signed_assignment"]["assignment"]

    target = %Target{
      scope:
        struct!(
          Scope,
          Map.merge(@tenant, %{application_id: "fieldlog", environment_id: "development"})
        ),
      platform: "ios",
      runtime_sha256: assignment["runtime"],
      channel: assignment["channel"]
    }

    roots =
      Enum.map(fixture["roots"], &Map.update!(&1, "public_key", fn v -> Base.decode64!(v) end))

    reader = [username: "mixer_release_delivery"]

    replace_config!(:local_release_delivery, %{
      target: target,
      host: fixture["host"],
      roots: roots,
      repo: reader
    })

    replace_config!(MixerHostedWeb.Endpoint, hosted.endpoint)
    assert {DeliveryRepo, reader} in MixerHosted.Application.children({hosted, :disabled})

    Application.put_env(
      :mixer_hosted,
      MixerHostedWeb.Endpoint,
      Keyword.put(hosted.endpoint, :https, ip: {0, 0, 0, 0}, port: 8443)
    )

    assert_raise ArgumentError, "local release delivery requires a loopback HTTP listener", fn ->
      MixerHosted.Application.children({hosted, :disabled})
    end
  end

  test "CLI-only publication refuses HTTPS in the effective endpoint settings" do
    hosted =
      MixerHosted.RuntimeConfig.load!(%{
        "MIXER_HOSTED_ROLE" => "api",
        "MIXER_DATABASE_HOST" => "db.fixture.example",
        "MIXER_DATABASE_NAME" => "mixer_fixture",
        "MIXER_DATABASE_USER" => "mixer_fixture",
        "MIXER_DATABASE_PASSWORD" => "synthetic-database-secret",
        "MIXER_SECRET_KEY_BASE" => String.duplicate("fixture-", 8)
      })

    replace_config!(WriterRepo, username: "browser_ordinary", database: "mixer_fixture")
    replace_config!(MixerHostedWeb.Endpoint, hosted.endpoint)
    assert WriterRepo in MixerHosted.Application.children({hosted, :disabled})

    Application.put_env(
      :mixer_hosted,
      MixerHostedWeb.Endpoint,
      Keyword.put(hosted.endpoint, :https, ip: {0, 0, 0, 0}, port: 8443)
    )

    assert_raise ArgumentError,
                 "local release writer requires a loopback HTTP listener and Repo options",
                 fn -> MixerHosted.Application.children({hosted, :disabled}) end
  end

  test "authenticated browser HTTP reads a release head with stage promotion installed" do
    c = prepare_release_fixture!("browser-publication-with-stage-promotion")
    provision!()
    provision_delivery!()
    provision_cli!()
    provision_actions!()
    provision_halt_audit!()
    provision_details!()

    provision_stage_promotion!()

    variant = variant(vector(), "ios", "development", "internal", 7)

    target = variant.enrollment.target
    replace_config!(:local_release_target, Map.from_struct(variant.enrollment))
    seed_target!(target)
    c = start!(c)
    assert %{phase: :storage_ready} = RuntimeOwner.status()
    owner = login(c)
    other = login(c, :other_tenant)

    assert %{"kind" => "empty", "target" => wire} = read!(c, owner, target)
    assert wire == string_keys(Target.wire(target))
    assert_status(c, other, target, 404)

    DB.q!(Admin, "ALTER TABLE public.mixer_stage_promotion_bindings DISABLE TRIGGER ALL")
    response = http(c, path(target), owner)
    assert response.status == 503
    assert %{"error" => %{"code" => "authorization_unavailable"}} = Jason.decode!(response.body)
  end

  @tag capture_log: true
  test "authenticates and atomically promotes both staged destinations over loopback HTTP" do
    c = prepare_release_fixture!("http-stage-promotion")
    provision!()
    provision_delivery!()
    provision_cli!()
    provision_actions!()
    provision_halt_audit!()
    provision_details!()

    vector = vector()
    source_ios = variant(vector, "ios", "development", "internal", 7)

    source = %{
      ios: put_in(source_ios.assignment["rollout_basis_points"], 1_000),
      android: variant(vector, "android", "development", "internal", 9)
    }

    destination = %{
      ios: variant(vector, "ios", "staging", "candidate", 3),
      android: variant(vector, "android", "staging", "candidate", 12)
    }

    direction = %Direction{
      source: Map.new(source, fn {platform, value} -> {platform, value.enrollment} end),
      destination: Map.new(destination, fn {platform, value} -> {platform, value.enrollment} end)
    }

    seed_target!(source.ios.enrollment.target)
    provision_release_jobs!()
    provision_stage_promotion!()

    for value <- [source.android, destination.ios, destination.android],
        do: seed_head!(value.enrollment.target)

    c = put_in(c.hosted.local_release_jobs, true)

    env = %{
      "MIXER_LOCAL_RELEASE_CONFIG" => Jason.encode!(release_provisioning(source.ios.enrollment)),
      "MIXER_LOCAL_RELEASE_TARGET_REGISTRY" =>
        Jason.encode!(
          Enum.map([source.android, destination.ios, destination.android], fn value ->
            release_provisioning(value.enrollment)
          end)
        ),
      "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD" => "fixture-stage-delivery",
      "MIXER_LOCAL_RELEASE_WRITER_ENABLED" => "true",
      "MIXER_LOCAL_STAGE_PROMOTION_DIRECTIONS" =>
        Jason.encode!([
          %{
            direction_id: @promotion_direction,
            source:
              Map.new(direction.source, fn {platform, entry} ->
                {platform, Target.wire(entry.target)}
              end),
            destination:
              Map.new(direction.destination, fn {platform, entry} ->
                {platform, Target.wire(entry.target)}
              end)
          }
        ])
    }

    {default, _delivery} = provisioning = RuntimeProvisioning.load!(env, c.hosted)
    writer = RuntimeProvisioning.writer_options!(env, c.hosted, provisioning)
    directions = RuntimeProvisioning.stage_promotion_directions!(env, provisioning, writer)
    assert directions == %{@promotion_direction => direction}

    seed_stage_direction!(direction)
    replace_config!(WriterRepo, writer)
    replace_config!(:local_release_target, default)
    replace_config!(:local_stage_promotion_directions, directions)
    c = start!(c)
    assert %{phase: :storage_ready} = RuntimeOwner.status()

    owner = login(c)
    upload_identity = upload_identity!(c, login(c, :artifact_uploader))
    no_publish_scope = access_token!(c, login(c, :no_build_scope))
    other_tenant = access_token!(c, login(c, :other_tenant))
    token = access_token!(c, owner)

    for {name, value} <- [
          {"source-ios", source.ios},
          {"source-android", source.android},
          {"destination-ios", destination.ios},
          {"destination-android", destination.android}
        ] do
      staged = publication(value)
      evidence = staged.evidence

      envelope =
        Jason.encode!(%{
          signed_manifest: Jason.Fragment.new(evidence.signed_manifest_bytes),
          payload: Base.encode64(evidence.payload)
        })

      config = Map.from_struct(value.enrollment)

      assert {:ok, %{status: 201}} =
               upload!(c, upload_identity, config, staged.artifact_sha256, envelope, name)
    end

    for {platform, value} <- source do
      signed = publication(value)
      config = Map.from_struct(value.enrollment)
      Application.put_env(:mixer_hosted, :local_release_target, config)

      assert {:ok, %{sequence: sequence}} =
               RuntimeOwner.publish_release(
                 owner,
                 config.target,
                 signed.evidence.signed_assignment_bytes,
                 "source-" <> Atom.to_string(platform),
                 @reason
               )

      assert sequence == signed.sequence
    end

    Application.put_env(:mixer_hosted, :local_release_target, default)
    ios = spaced_assignment(destination.ios)
    android = spaced_assignment(destination.android)
    body = promotion_body(ios, android)

    idempotency_key =
      :crypto.hash(
        :sha256,
        Enum.join(["mixer-local-release-v3", "POST", @promotion_path, @reason, body], <<0>>)
      )
      |> Base.encode16(case: :lower)

    request =
      &promotion_post(
        c,
        token,
        @promotion_path,
        &1,
        [{"x-mixer-reason", @reason}],
        idempotency_key
      )

    unauthorized = &promotion_post(c, &1, @promotion_path, body)

    assert promotion_post(c, token, @promotion_path <> "-unenrolled", body).status == 404

    assert unauthorized.(nil).status == 401
    assert unauthorized.(no_publish_scope).status == 403
    assert unauthorized.(other_tenant).status == 404

    for {part, wrong} <- [
          {"org-a", "org-b"},
          {"project-a", "project-b"},
          {"fieldlog", "other-app"}
        ] do
      path = String.replace(@promotion_path, part, wrong)
      assert promotion_post(c, token, path, body).status == 404
    end

    assert promotion_post(c, token, @promotion_path <> "?ignored=1", body).status == 404
    assert promotion_post(c, token, @promotion_path, body, []).status == 400

    assert promotion_post(c, token, @promotion_path, body, [
             {"x-mixer-reason", @reason},
             {"x-mixer-reason", @reason}
           ]).status == 400

    for invalid_body <- [
          promotion_body(ios, android, "0"),
          promotion_body(ios, android, ~s("7")),
          promotion_body(ios, android, "7.0"),
          promotion_body(ios, android, Integer.to_string(@max_sequence + 1)),
          promotion_body(ios, android, "7", ~s(,"payload":"unrequested")),
          promotion_body(ios, android, "7", ~s(,"source_ios_sequence":7)),
          promotion_body(ios, android, "7", ~S(,"source_ios_sequenc\u0065":7)),
          promotion_body(
            String.replace_prefix(ios, "{", "{" <> String.duplicate(" ", 65_536)),
            android
          )
        ] do
      assert request.(invalid_body).status == 400
    end

    assert request.(body <> String.duplicate(" ", 160 * 1024)).status == 413
    assert request.(promotion_body(ios, android, Integer.to_string(@max_sequence))).status == 404
    assert request.(promotion_body(ios, "{}")).status == 409
    assert request.(promotion_body(ios, ios)).status == 409

    unstaged =
      destination.android
      |> MixerHosted.Test.StagePromotionSigningFixture.with_payload("different staged digest")
      |> spaced_assignment()

    assert request.(promotion_body(ios, unstaged)).status == 404
    assert_empty_stage_promotion!()

    for value <- Map.values(destination) do
      target = value.enrollment.target

      assert read!(c, owner, target, :details_v2) == %{
               "kind" => "empty",
               "target" => string_keys(Target.wire(target))
             }
    end

    assert_failed_job_commit!(fn ->
      assert request.(body).status == 503
      assert_empty_stage_promotion!()
    end)

    expected = %{
      "ios" => promotion_receipt(destination.ios),
      "android" => promotion_receipt(destination.android),
      "delivery" => "local_only"
    }

    if cli = System.get_env("MIXER_TEST_RELEASE_CLI") do
      receipts =
        Map.merge(expected, %{
          "status" => "ok",
          "action" => "promote-environment",
          "direction_id" => @promotion_direction
        })

      for _ <- 1..2 do
        StockReleaseCLI.promote_environment!(
          cli,
          c.http_port,
          token,
          %{
            direction: @promotion_direction,
            reason: @reason,
            ios: %{source_sequence: 7, assignment: ios},
            android: %{source_sequence: 9, assignment: android}
          },
          receipts
        )
      end
    end

    response = retry_release_write(fn -> request.(body) end, 2)
    assert response.status == 200
    assert response_header(response, "cache-control") == ["no-store"]
    response_payload = Jason.decode!(response.body)

    assert response_payload == expected

    assert %{status: 200, body: replay} = request.(body)
    assert Jason.decode!(replay) == response_payload

    changed = String.replace_prefix(ios, "{", "{ ")
    assert %{status: 409, body: conflict} = request.(promotion_body(changed, android))
    assert %{"error" => %{"code" => "idempotency_conflict"}} = Jason.decode!(conflict)

    assert [
             ["android", ^android, @reason, "stage_promote"],
             ["ios", ^ios, @reason, "stage_promote"]
           ] =
             DB.q!(Admin, """
             SELECT platform,signed_assignment_bytes,reason,action
             FROM public.mixer_release_publications
             WHERE environment_id='staging' ORDER BY platform
             """).rows

    assert [[1, 2]] =
             DB.q!(Admin, """
             SELECT (SELECT count(*) FROM public.mixer_stage_promotion_bindings),
                    (SELECT count(*) FROM mixer_release_jobs.oban_jobs WHERE args->>'environment_id'='staging')
             """).rows

    other = login(c, :other_tenant)

    for value <- Map.values(destination) do
      target = value.enrollment.target
      signed = publication(value)
      promoted = read!(c, owner, target, :details_v2)

      assert %{"kind" => "published", "target" => wire, "release" => release} = promoted
      assert wire == string_keys(Target.wire(target))
      assert release["sequence"] == Integer.to_string(signed.sequence)
      assert release["manifestSha256"] == signed.artifact_sha256
      assert release["details"]["sourceCommit"] == value.manifest["source_commit"]
      assert release["details"]["action"] == "stage_promote"

      assert read!(c, owner, target) == update_in(promoted["release"], &Map.delete(&1, "details"))

      assert read!(c, owner, target, :details) ==
               put_in(promoted["release"]["details"]["action"], "promote")

      assert_status(c, other, target, 404, :details_v2)
      assert http(c, path(target, :details_v2), []).status == 401
      assert http(c, path(target, :details_v2) <> "&view=details", owner).status == 400

      for wrong <- [
            %{target | platform: if(target.platform == "ios", do: "android", else: "ios")},
            %{target | scope: %{target.scope | environment_id: "development"}},
            %{target | channel: "unregistered"}
          ],
          do: assert_status(c, owner, wrong, 404, :details_v2)
    end

    variant = source.ios
    target = variant.enrollment.target
    assert_details_privileges!(target)
    original = publication(variant)

    expansion =
      update_in(variant.assignment, fn assignment ->
        %{assignment | "sequence" => 8, "rollout_basis_points" => 2_000}
      end)

    cli_base = "/v3/orgs/org-a/projects/project-a"
    validation = Jason.encode!(%{artifact_sha256: original.artifact_sha256})

    assert %{status: 200} =
             cli_post(c, token, cli_base <> "/releases/validate", "validate", validation)

    assert %{status: 200} =
             cli_post(
               c,
               token,
               cli_base <> "/channels/internal/promote",
               "rollout-expansion",
               ~s({"signed_assignment":#{spaced_assignment(expansion)}})
             )

    assert %{
             "release" => %{
               "sequence" => "8",
               "rolloutBasisPoints" => 2_000,
               "details" => %{"action" => "promote"}
             }
           } =
             expanded = read!(c, owner, target, :details_v2)

    assert read!(c, owner, target, :details) == expanded
  end

  test "publishes the verified upload once and reads the exact tenant-scoped browser head" do
    c = prepare_release_fixture!("browser-publication")
    provision!()
    provision_actions!()
    provision_halt_audit!()
    provision_details!()

    assert [[nil, nil]] =
             DB.q!(Admin, """
             SELECT to_regclass('public.mixer_release_cli_requests'),
                    to_regclass('public.mixer_stage_promotion_bindings')
             """).rows

    fixture = @fixtures |> Path.join("signed-release-v3.json") |> File.read!() |> Jason.decode!()

    signed = fixture["signed_assignment"]
    assignment = signed["assignment"]
    bytes = Jason.encode!(signed) <> "\n"
    manifest_sha256 = assignment["artifact_sha256"]
    payload = Base.decode64!(fixture["payload"])
    payload_sha256 = Base.encode16(:crypto.hash(:sha256, payload), case: :lower)

    roots =
      Enum.map(fixture["roots"], &Map.update!(&1, "public_key", fn v -> Base.decode64!(v) end))

    target = %Target{
      scope:
        struct!(
          Scope,
          Map.merge(@tenant, %{application_id: "fieldlog", environment_id: "development"})
        ),
      platform: "ios",
      runtime_sha256: assignment["runtime"],
      channel: assignment["channel"]
    }

    config = %{host: fixture["host"], roots: roots, target: target}
    replace_config!(:local_release_target, config)

    seed_target!(target)
    c = start!(c)
    assert %{phase: :storage_ready} = RuntimeOwner.status()
    assert http(c, "/v3/updates", []).status == 404
    assert http(c, "/v3/artifacts/" <> manifest_sha256, []).status == 404
    refute Process.whereis(DeliveryRepo)

    preauth = bootstrap_http(c)
    assert {:error, :unauthenticated} = publish(headers(preauth.cookie), target, bytes)

    owner = login(c)
    other = login(c, :other_tenant)
    uploader = login(c, :artifact_uploader)
    no_publish_scope = login(c, :no_build_scope)
    GenServer.call(c.provider, {:mode, :ok})

    assert %{"kind" => "empty", "target" => wire} = read!(c, owner, target)
    assert wire == string_keys(Target.wire(target))
    assert read!(c, owner, target, :details) == read!(c, owner, target)
    assert_status(c, other, target, 404)
    assert_status(c, owner, %{target | scope: %{target.scope | environment_id: "staging"}}, 404)
    assert_status(c, owner, %{target | channel: "different"}, 404)
    assert_status(c, owner, %{target | platform: "android"}, 404)
    assert_status(c, owner, %{target | runtime_sha256: String.duplicate("a", 64)}, 404)

    assert_status(
      c,
      owner,
      %{target | scope: %{target.scope | organization_id: "org-b", project_id: "project-b"}},
      404
    )

    assert http(c, path(target) <> "&channel=beta", owner).status == 400
    assert http(c, path(target), owner, "POST").status == 404
    assert http(c, path(target) <> "&view=summary", owner).status == 400
    assert http(c, path(target, :details) <> "&view=details", owner).status == 400
    assert http(c, path(target, :details) <> "&sequence=1", owner).status == 400
    assert http(c, path(target, :details), headers(preauth.cookie)).status == 401

    assert {:error, :not_found} = publish(owner, target, bytes)
    assert {:error, :permission_denied} = publish(no_publish_scope, target, bytes)
    assert {:error, :not_found} = publish(other, target, bytes)
    assert [[0]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows

    identity = upload_identity!(c, uploader)
    envelope = Jason.encode!(Map.take(fixture, ~w(signed_manifest payload)))

    assert {:ok,
            %{status: 201, manifest_sha256: ^manifest_sha256, payload_sha256: ^payload_sha256}} =
             upload!(c, identity, config, manifest_sha256, envelope)

    assert [[^manifest_sha256, ^payload_sha256, ^envelope, ^payload]] =
             DB.q!(Admin, """
             SELECT manifest_sha256,payload_sha256,envelope_bytes,payload FROM public.mixer_customer_artifacts
             """).rows

    wrong_channel = put_in(signed, ["assignment", "channel"], "stable") |> Jason.encode!()
    wrong_signature = Map.put(signed, "signature", Base.encode64(<<0::512>>)) |> Jason.encode!()
    assert {:error, :invalid_request} = publish(owner, target, wrong_channel)
    assert {:error, :invalid_request} = publish(owner, target, wrong_signature)
    assert {:error, :not_found} = publish(owner, %{target | platform: "android"}, bytes)

    revoked =
      Enum.map(roots, fn root ->
        if root["assignment"], do: Map.put(root, "revoked", true), else: root
      end)

    Application.put_env(:mixer_hosted, :local_release_target, %{config | roots: revoked})
    assert {:error, :permission_denied} = publish(owner, target, bytes)
    Application.put_env(:mixer_hosted, :local_release_target, config)
    assert %{"kind" => "empty", "target" => ^wire} = read!(c, owner, target)
    assert [[0]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows

    assert_stale_publication_denied(c, login(c), target, bytes)
    assert %{"kind" => "empty", "target" => ^wire} = read!(c, owner, target)

    assert {:ok, first} = publish(owner, target, bytes)

    assert first == %{
             sequence: assignment["sequence"],
             previous_sequence: nil,
             rollout_basis_points: assignment["rollout_basis_points"],
             artifact_sha256: manifest_sha256,
             signed_assignment_bytes: bytes
           }

    assert {:ok, ^first} = publish(owner, target, bytes)

    assert {:error, :conflict} =
             RuntimeOwner.publish_release(owner, target, bytes, "another-key", @reason)

    assert {:error, :idempotency_conflict} =
             RuntimeOwner.publish_release(owner, target, bytes, "initial", "Changed reason")

    published = %{
      "kind" => "published",
      "target" => wire,
      "release" => %{
        "releaseId" => assignment["release_id"],
        "sequence" => Integer.to_string(assignment["sequence"]),
        "rolloutBasisPoints" => assignment["rollout_basis_points"],
        "manifestSha256" => manifest_sha256,
        "payloadSha256" => payload_sha256
      }
    }

    assert read!(c, owner, target) == published

    expected = %{
      "sourceCommit" => String.duplicate("a", 40),
      "payloadBytes" => byte_size(payload),
      "artifactKeyId" => "fixture-v3-artifact",
      "assignmentKeyId" => "fixture-v3-assignment",
      "action" => "publish",
      "capabilities" => [
        %{"id" => "network.http.v1", "permissions" => ["network.https"]},
        %{"id" => "storage.keyValue.v1", "permissions" => ["storage.appPrivate"]}
      ]
    }

    detailed = put_in(published, ["release", "details"], expected)
    assert read!(c, owner, target, :details) == detailed
    assert_details_privileges!(target)
    assert_invalid_details_refused!(c, owner, target, manifest_sha256)
    assert read!(c, owner, target, :details) == detailed

    assert %{num_rows: 1} =
             DB.q!(
               Admin,
               "UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='member-a'"
             )

    assert read!(c, no_publish_scope, target) == published
    assert read!(c, owner, target) == published
    assert read!(c, no_publish_scope, target, :details) == detailed
    assert read!(c, owner, target, :details) == detailed
    assert {:error, :permission_denied} = publish(owner, target, bytes)

    assert %{num_rows: 1} =
             DB.q!(
               Admin,
               "UPDATE public.mixer_authz_memberships SET role='owner' WHERE id='member-a'"
             )

    assert_status(c, other, target, 404)
    assert_status(c, owner, %{target | scope: %{target.scope | environment_id: "staging"}}, 404)

    for {headers, denied} <- [
          {other, target},
          {owner, %{target | scope: %{target.scope | environment_id: "staging"}}},
          {owner, %{target | channel: "different"}},
          {owner, %{target | platform: "android"}},
          {owner, %{target | runtime_sha256: String.duplicate("a", 64)}},
          {owner,
           %{target | scope: %{target.scope | organization_id: "org-b", project_id: "project-b"}}}
        ],
        do: assert_status(c, headers, denied, 404, :details)

    assert [[sequence, ^bytes, "person-1", "initial"]] =
             DB.q!(
               Admin,
               "SELECT sequence,signed_assignment_bytes,principal_id,idempotency_key FROM public.mixer_release_publications"
             ).rows

    assert Decimal.to_integer(sequence) == assignment["sequence"]
    assert [[^sequence]] = DB.q!(Admin, "SELECT sequence FROM public.mixer_release_heads").rows

    corpus = @fixtures |> Path.join("release-v3-cases.json") |> File.read!() |> Jason.decode!()

    %{"signed_assignment_json" => max_bytes} =
      Enum.find(corpus["assignment_cases"], &(&1["name"] == "sequence-#{@max_sequence}"))

    assert {:ok,
            %{
              sequence: @max_sequence,
              previous_sequence: previous,
              signed_assignment_bytes: ^max_bytes
            }} = RuntimeOwner.publish_release(owner, target, max_bytes, "max-sequence", @reason)

    assert previous == assignment["sequence"]
    assert {:ok, ^first} = publish(owner, target, bytes)

    assert read!(c, owner, target) ==
             put_in(published, ["release", "sequence"], Integer.to_string(@max_sequence))

    assert [[maximum, ^sequence, ^max_bytes]] =
             DB.q!(Admin, """
             SELECT h.sequence,p.previous_sequence,p.signed_assignment_bytes
             FROM public.mixer_release_heads h
             JOIN public.mixer_release_publications p ON p.sequence=h.sequence
             """).rows

    assert Decimal.to_integer(maximum) == @max_sequence
    credential = upload_identity!(c, owner).credential_ref

    assert %{num_rows: 1} =
             DB.q!(
               Admin,
               "UPDATE public.mixer_authz_credentials SET active=false WHERE reference=$1",
               [
                 credential
               ]
             )

    assert {:error, %Store.Failure{}} = publish(owner, target, bytes)
    revoked = http(c, path(target, :details), owner)
    assert revoked.status in [401, 404, 503]
    refute revoked.body =~ expected["artifactKeyId"]
    assert [[2]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
    leases_clean()
  end

  test "shares a head between browser and CLI publication and delivers only committed releases" do
    exercise_publication!(false)
  end

  test "commits browser and CLI release jobs atomically and drains them with HTTP idle" do
    exercise_publication!(true)
  end

  defp exercise_publication!(jobs?) do
    fixture = if jobs?, do: "public-delivery-jobs", else: "public-delivery"
    c = prepare_release_fixture!(fixture)
    provision!()
    provision_delivery!()
    provision_cli!()
    provision_actions!()
    provision_halt_audit!()
    provision_details!()

    DB.q!(
      Admin,
      "GRANT INSERT (action) ON public.mixer_release_publications TO browser_ordinary"
    )

    fixture = @fixtures |> Path.join("signed-release-v3.json") |> File.read!() |> Jason.decode!()
    %{"host" => host, "roots" => encoded_roots, "installation" => installation} = fixture

    roots =
      Enum.map(encoded_roots, &Map.update!(&1, "public_key", fn key -> Base.decode64!(key) end))

    assignment = fixture["signed_assignment"]["assignment"]

    target = %Target{
      scope:
        struct!(
          Scope,
          Map.merge(@tenant, %{application_id: "fieldlog", environment_id: "development"})
        ),
      platform: "ios",
      runtime_sha256: assignment["runtime"],
      channel: assignment["channel"]
    }

    config = %{target: target, host: host, roots: roots}

    delivery =
      Map.put(
        config,
        :repo,
        Keyword.merge(c.hosted.repo, username: "mixer_release_delivery", pool_size: 1)
      )

    replace_config!(:local_release_target, config)
    replace_config!(:local_release_delivery, delivery)
    replace_config!(WriterRepo, c.hosted.repo)
    seed_target!(target)
    if jobs?, do: provision_release_jobs!()
    c = put_in(c.hosted.local_release_jobs, jobs?)
    c = start!(c)
    assert %{phase: :storage_ready} = RuntimeOwner.status()
    assert [["browser_ordinary"]] = DB.q!(WriterRepo, "SELECT session_user").rows
    assert [["browser_ordinary"]] = DB.q!(MixerHosted.Repo, "SELECT session_user").rows

    assert [[true, false, false, false]] =
             DB.q!(Admin, """
             SELECT has_function_privilege('browser_ordinary', p.oid, 'EXECUTE'),
                    has_function_privilege('browser_lifecycle', p.oid, 'EXECUTE'),
                    has_function_privilege('browser_writer', p.oid, 'EXECUTE'),
                    has_function_privilege('mixer_release_delivery', p.oid, 'EXECUTE')
             FROM pg_proc p WHERE p.oid =
               'public.mixer_release_audit_halts(text,text,text,text,text,text,text,numeric,integer)'::regprocedure
             """).rows

    first_digest = fixture["artifact_sha256"]
    first_envelope = Jason.encode!(Map.take(fixture, ~w(signed_manifest payload)))
    first = assignment |> Map.put("rollout_basis_points", fixture["cohort_bucket"] + 1)

    signed_first =
      sign_fixture("assignment", first) |> Jason.encode!(pretty: true) |> Kernel.<>("\n")

    second_manifest =
      fixture["signed_manifest"]["manifest"]
      |> Map.merge(%{
        "release_id" => "fixture-v3-next",
        "source_commit" => String.duplicate("b", 64)
      })
      |> update_in(["capability_grants", "entries"], fn [network, _storage] ->
        [Map.put(network, "permissions", [])]
      end)

    second_envelope =
      Jason.encode!(%{
        "signed_manifest" => sign_fixture("artifact", second_manifest),
        "payload" => fixture["payload"]
      })

    assert {:ok, %{manifest_sha256: second_digest} = second_artifact} =
             ArtifactAdmission.admit(second_envelope, host, roots, System.system_time(:second))

    second = %{
      first
      | "sequence" => first["sequence"] + 1,
        "rollout_basis_points" => 1_500,
        "release_id" => second_manifest["release_id"],
        "artifact_sha256" => second_digest
    }

    signed_second = sign_fixture("assignment", second) |> Jason.encode!()

    offer_path = delivery_path(target, installation)
    first_path = delivered_artifact_path(first_digest)
    second_path = delivered_artifact_path(second_digest)
    assert_no_offer(c, offer_path)
    assert http(c, first_path, []).status == 404
    assert http(c, offer_path, [], "POST").status == 404
    owner = login(c, :release_cli)
    uploader = login(c, :artifact_uploader)
    :ok = GenServer.call(c.provider, {:mode, :ok})
    identity = upload_identity!(c, uploader)

    assert {:ok, %{status: 201}} =
             upload!(c, identity, config, first_digest, first_envelope, "delivery-first")

    assert {:ok, %{status: 201}} =
             upload!(c, identity, config, second_digest, second_envelope, "delivery-second")

    assert %{"kind" => "empty"} = read!(c, owner, target)
    assert %{"kind" => "empty"} = read!(c, owner, target, :details)
    assert_no_offer(c, offer_path)
    assert http(c, first_path, []).status == 404
    assert http(c, second_path, []).status == 404

    assert {:ok, %{artifact_sha256: ^first_digest}} =
             RuntimeOwner.publish_release(owner, target, signed_first, "delivery-first", @reason)

    first_sequence = Integer.to_string(first["sequence"])

    if jobs? do
      assert_queued_publications!(target, [first_sequence])

      assert {:ok, %{artifact_sha256: ^first_digest}} =
               RuntimeOwner.publish_release(
                 owner,
                 target,
                 signed_first,
                 "delivery-first",
                 @reason
               )

      assert_queued_publications!(target, [first_sequence])
    end

    assert %{"release" => %{"sequence" => ^first_sequence, "manifestSha256" => ^first_digest}} =
             read!(c, owner, target)

    first_head = read!(c, owner, target, :details)

    assert %{
             "release" => %{
               "manifestSha256" => ^first_digest,
               "details" => %{"action" => "publish"}
             }
           } = first_head

    {offer, artifact} =
      assert_delivery(c, offer_path, first_path, signed_first, first_envelope, config)

    assert_no_offer(c, delivery_path(target, "excluded-installation"))

    assert_no_offer(
      c,
      delivery_path(%{target | runtime_sha256: String.duplicate("a", 64)}, installation)
    )

    assert_no_offer(c, delivery_path(%{target | channel: "stable"}, installation))

    assert_no_offer(
      c,
      delivery_path(%{target | scope: %{target.scope | organization_id: "org-b"}}, installation)
    )

    assert http(c, first_path |> String.replace("org-a", "org-b"), []).status == 404
    assert http(c, first_path |> String.replace("project-a", "project-b"), []).status == 404
    assert http(c, second_path, []).status == 404
    assert http(c, offer_path <> "&installation=duplicate", []).status == 400
    assert http(c, first_path <> "&%70roject=project-b", []).status == 400
    assert http(c, first_path <> "&unexpected=field", []).status == 400

    # The public trust configuration is independent of the writer's roots.
    revoked =
      Enum.map(roots, fn root ->
        if root["assignment"], do: %{root | "revoked" => true}, else: root
      end)

    Application.put_env(:mixer_hosted, :local_release_delivery, %{delivery | roots: revoked})
    assert_no_offer(c, offer_path)
    assert http(c, first_path, []).body == first_envelope
    assert Application.fetch_env!(:mixer_hosted, :local_release_target) == config

    revoked =
      Enum.map(roots, fn root ->
        if root["artifact"], do: %{root | "revoked" => true}, else: root
      end)

    Application.put_env(:mixer_hosted, :local_release_delivery, %{delivery | roots: revoked})
    assert_no_offer(c, offer_path)
    assert http(c, first_path, []).status == 404
    Application.put_env(:mixer_hosted, :local_release_delivery, delivery)
    assert_reader_authority!(target, first_digest)

    token = access_token!(c, owner)
    cli_base = "/v3/orgs/org-a/projects/project-a"
    validate = cli_base <> "/releases/validate"
    validation = Jason.encode!(%{artifact_sha256: second_digest})

    assert %{status: 409, body: conflict} =
             cli_post(c, token, validate, "delivery-first", validation)

    assert %{"error" => %{"code" => "idempotency_conflict"}} = Jason.decode!(conflict)
    assert %{status: 200} = cli_post(c, token, validate, "cli-validated-second", validation)

    assert {:error, :idempotency_conflict} =
             RuntimeOwner.publish_release(
               owner,
               target,
               signed_second,
               "cli-validated-second",
               @reason
             )

    assert %{"release" => %{"sequence" => ^first_sequence}} = read!(c, owner, target)
    assert [[1]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_cli_requests").rows

    cli = if !jobs?, do: System.get_env("MIXER_TEST_RELEASE_CLI")

    if cli do
      with_uploader!(c, config, fn ->
        StockReleaseCLI.publish!(cli, c.http_port, token, second_artifact, signed_second, second)
      end)
    else
      publish_path = cli_base <> "/channels/#{target.channel}/publish"
      body = ~s({"signed_assignment":#{signed_second}})
      publish_second = fn -> cli_post(c, token, publish_path, "cli-second", body) end

      if jobs? do
        assert_failed_publication = fn ->
          assert %{status: 503} = publish_second.()

          assert [[head]] = DB.q!(Admin, "SELECT sequence FROM public.mixer_release_heads").rows
          assert Decimal.to_string(head) == first_sequence
          assert_delivery(c, offer_path, first_path, signed_first, first_envelope, config)

          assert [[1]] =
                   DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows

          assert [[1]] =
                   DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_cli_requests").rows

          assert_queued_publications!(target, [first_sequence])
        end

        DB.q!(
          Admin,
          "REVOKE INSERT (queue) ON mixer_release_jobs.oban_jobs FROM browser_ordinary"
        )

        try do
          assert_failed_publication.()
        after
          DB.q!(Admin, "GRANT INSERT (queue) ON mixer_release_jobs.oban_jobs TO browser_ordinary")
        end

        assert_failed_job_commit!(assert_failed_publication)
        assert %{"release" => %{"sequence" => ^first_sequence}} = read!(c, owner, target)
      end

      assert %{status: 200, body: result} =
               if(jobs?, do: retry_release_write(publish_second, 2), else: publish_second.())

      if jobs? do
        assert %{status: 200, body: ^result} = publish_second.()
      end

      assert %{"sequence" => sequence, "artifact_sha256" => ^second_digest} =
               Jason.decode!(result)

      assert sequence == second["sequence"]
    end

    second_sequence = Integer.to_string(second["sequence"])
    if jobs?, do: assert_queued_publications!(target, [first_sequence, second_sequence])

    assert %{"release" => %{"sequence" => ^second_sequence, "manifestSha256" => ^second_digest}} =
             read!(c, owner, target)

    assert %{
             "release" => %{
               "sequence" => ^second_sequence,
               "manifestSha256" => ^second_digest,
               "details" => %{
                 "sourceCommit" => source,
                 "action" => "publish",
                 "capabilities" => [
                   %{"id" => "network.http.v1", "permissions" => []},
                   %{"id" => "storage.keyValue.v1", "permissions" => nil}
                 ]
               }
             }
           } = read!(c, owner, target, :details)

    assert source == second_manifest["source_commit"]

    assert_delivery(c, offer_path, second_path, signed_second, second_envelope, config)
    assert http(c, first_path, []).body == first_envelope
    assert [[2]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
    leases_clean()

    assert :ok = Application.stop(:mixer_hosted)
    refute Process.whereis(DeliveryRepo)
    refute Process.whereis(WriterRepo)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)

    try do
      {:ok, {_, port}} = MixerHostedWeb.Endpoint.server_info(:http)
      restarted = %{c | http_port: port}
      assert [[1]] = DB.q!(DeliveryRepo, "SELECT 1").rows
      assert_retry_checkpoint_stops_at_cutoff()
      assert_browser_read_refusal_preserves_owner(restarted, owner)
      assert_browser_reads_wait_for_checkout(restarted, owner, target, second_sequence)
      assert_delivery(restarted, offer_path, second_path, signed_second, second_envelope, config)
      assert http(restarted, first_path, []).body == first_envelope
      assert_no_offer(restarted, delivery_path(target, "excluded-installation"))

      rollback_path = cli_base <> "/channels/#{target.channel}/rollback"
      rollback_sequence = if jobs?, do: @max_sequence, else: second["sequence"] + 1
      rollback = %{first | "sequence" => rollback_sequence}
      signed_rollback = sign_fixture("assignment", rollback) |> Jason.encode!()
      rollback_body = ~s({"signed_assignment":#{signed_rollback}})

      assert %{status: 422, body: unvalidated} =
               cli_post(
                 restarted,
                 token,
                 rollback_path,
                 "browser-artifact-rollback",
                 rollback_body
               )

      assert %{"error" => %{"code" => "not_validated"}} = Jason.decode!(unvalidated)
      assert [[2]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows

      first_validation = Jason.encode!(%{artifact_sha256: first_digest})

      assert %{status: 200} =
               cli_post(restarted, token, validate, "validate-browser-artifact", first_validation)

      assert %{status: 200, body: result} =
               cli_post(
                 restarted,
                 token,
                 rollback_path,
                 "browser-artifact-rollback",
                 rollback_body
               )

      assert %{"sequence" => sequence, "artifact_sha256" => ^first_digest} = Jason.decode!(result)
      assert sequence == rollback["sequence"]

      assert [[^signed_rollback, "rollback"]] =
               DB.q!(Admin, """
               SELECT p.signed_assignment_bytes,p.action
               FROM public.mixer_release_publications p
               JOIN public.mixer_release_heads h USING
                 (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,sequence)
               """).rows

      rolled_back =
        first_head
        |> put_in(["release", "sequence"], Integer.to_string(sequence))
        |> put_in(["release", "details", "action"], "rollback")

      assert read!(restarted, owner, target, :details) == rolled_back

      assert_delivery(restarted, offer_path, first_path, signed_rollback, first_envelope, config)

      if jobs? do
        assert_queued_publications!(target, [
          first_sequence,
          second_sequence,
          Integer.to_string(rollback_sequence)
        ])
      end
    after
      assert :ok = Application.stop(:mixer_hosted)
    end

    if jobs?, do: assert_release_processor_drains!(c)

    path = if !jobs?, do: System.get_env("MIXER_PUBLIC_DELIVERY_WIRE_PROOF")

    if path do
      File.write!(
        path,
        Jason.encode!(%{offer: offer, artifact: artifact, excluded: "excluded-installation"})
      )
    end
  end

  defp assert_queued_publications!(target, sequences) do
    fields = Map.new(Target.filter(target), fn {key, value} -> {Atom.to_string(key), value} end)

    expected =
      Enum.map(sequences, fn sequence ->
        [
          "releases",
          "MixerHosted.Releases.ReleaseJobs.Materialize",
          Map.merge(fields, %{"version" => 1, "sequence" => sequence}),
          "available",
          0
        ]
      end)

    assert DB.q!(Admin, """
           SELECT queue,worker,args,state::text,attempt
           FROM mixer_release_jobs.oban_jobs ORDER BY id
           """).rows == expected

    assert [[0]] =
             DB.q!(Admin, "SELECT count(*) FROM mixer_release_jobs.offer_materializations").rows
  end

  defp assert_failed_job_commit!(assert_failure) do
    DB.q!(Admin, """
    CREATE FUNCTION mixer_release_jobs.fixture_fail_commit() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
    BEGIN
      RAISE EXCEPTION 'fixture commit failure after release enqueue';
    END $body$
    """)

    DB.q!(Admin, """
    CREATE CONSTRAINT TRIGGER release_job_fixture_fail_commit
    AFTER INSERT ON mixer_release_jobs.oban_jobs
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    EXECUTE FUNCTION mixer_release_jobs.fixture_fail_commit()
    """)

    try do
      assert_failure.()
    after
      DB.q!(Admin, "DROP TRIGGER release_job_fixture_fail_commit ON mixer_release_jobs.oban_jobs")
      DB.q!(Admin, "DROP FUNCTION mixer_release_jobs.fixture_fail_commit()")
    end
  end

  defp retry_release_write(request, retries) do
    case request.() do
      %{status: 503, body: body} = refusal when retries > 0 ->
        assert response_header(refusal, "retry-after") == ["1"]
        assert %{"error" => %{"code" => "authorization_unavailable"}} = Jason.decode!(body)
        Process.sleep(1_000)
        retry_release_write(request, retries - 1)

      result ->
        result
    end
  end

  defp assert_release_processor_drains!(c) do
    hosted =
      MixerHosted.Identity.StartupFixture.foundation_env()
      |> Map.merge(%{
        "MIXER_HOSTED_ROLE" => "processor",
        "MIXER_PROCESSOR_PROFILE" => "releases_v1",
        "MIXER_DATABASE_USER" => "mixer_release_processor"
      })
      |> Map.delete("MIXER_SECRET_KEY_BASE")
      |> MixerHosted.RuntimeConfig.load!()

    connection = Keyword.take(c.hosted.repo, [:hostname, :port, :database, :ssl])
    hosted = %{hosted | repo: Keyword.merge(hosted.repo, connection)}
    abandoned_job = materialize_abandoned_job!(connection[:database])
    {exhausted_job, exhausted_attempt} = abandon_final_release_attempt!()
    assert_release_processor_admission!(connection[:database])
    configure!(%{c | hosted: hosted}, :disabled)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)

    try do
      refute Process.whereis(MixerHostedWeb.Endpoint)
      refute Process.whereis(WriterRepo)
      refute Process.whereis(DeliveryRepo)
      assert [["mixer_release_processor"]] = DB.q!(MixerHosted.Repo, "SELECT session_user").rows

      await_release_jobs!(
        [["completed"], ["completed"], ["discarded"]],
        System.monotonic_time(:millisecond) + 10_000
      )

      assert [[2]] =
               DB.q!(Admin, "SELECT count(*) FROM mixer_release_jobs.offer_materializations").rows

      retry_args = ["-v", "release_job_id=#{exhausted_job}"]
      retry_result = release_jobs_sql!("retry-local-release-job.sql", retry_args)
      assert retry_result == "#{exhausted_job}|#{exhausted_attempt}|#{exhausted_attempt + 1}"
      assert release_jobs_sql!("retry-local-release-job.sql", retry_args) == ""

      await_release_jobs!(
        [["completed"], ["completed"], ["completed"]],
        System.monotonic_time(:millisecond) + 5_000
      )

      assert [[3]] =
               DB.q!(Admin, """
               SELECT count(*) FROM mixer_release_jobs.offer_materializations m
               JOIN public.mixer_release_publications p USING
                 (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,sequence)
               WHERE m.signed_assignment_bytes = p.signed_assignment_bytes
                 AND m.artifact_sha256 = p.artifact_sha256
                 AND m.rollout_basis_points = p.rollout_basis_points
                 AND m.action = p.action
               """).rows

      assert [[3, 1, 1, 1]] =
               DB.q!(
                 Admin,
                 """
                 SELECT count(*), count(*) FILTER (WHERE attempt=1),
                        count(*) FILTER (WHERE id=$1 AND attempt=2),
                        count(*) FILTER (WHERE id=$2 AND attempt=$3)
                 FROM mixer_release_jobs.oban_jobs WHERE state='completed'
                 """,
                 [abandoned_job, exhausted_job, exhausted_attempt + 1]
               ).rows
    after
      assert :ok = Application.stop(:mixer_hosted)
    end
  end

  defp materialize_abandoned_job!(database) do
    assert [[job_id]] =
             DB.q!(Admin, """
             UPDATE mixer_release_jobs.oban_jobs
             SET state='executing', attempt=1, attempted_at=now() - interval '6 minutes'
             WHERE id=(SELECT min(id) FROM mixer_release_jobs.oban_jobs)
             RETURNING id
             """).rows

    conn = DB.connection!("mixer_release_processor", database)

    try do
      assert %{rows: [["ok"]]} =
               Postgrex.query!(
                 conn,
                 "SELECT mixer_release_jobs.materialize_v1($1::bigint,$2::integer)",
                 [job_id, 1]
               )
    after
      GenServer.stop(conn)
    end

    assert [[1]] =
             DB.q!(Admin, "SELECT count(*) FROM mixer_release_jobs.offer_materializations").rows

    job_id
  end

  defp abandon_final_release_attempt! do
    assert [[job_id, attempt]] =
             DB.q!(Admin, """
             UPDATE mixer_release_jobs.oban_jobs
             SET state='executing', attempt=max_attempts, attempted_at=now() - interval '6 minutes'
             WHERE id=(SELECT max(id) FROM mixer_release_jobs.oban_jobs)
             RETURNING id, attempt
             """).rows

    {job_id, attempt}
  end

  defp assert_release_processor_admission!(database) do
    conn = DB.connection!("mixer_release_processor", database)

    try do
      assert :ok = ProcessorAdmission.after_connect(conn)

      assert_release_grant_refused!(conn, "oban_peers", "TRUNCATE")
      assert_release_grant_refused!(conn, "oban_jobs", "SELECT", true)
      assert_release_grant_refused!(conn, "oban_jobs", "UPDATE (state)", true)

      assert [[version]] = DB.q!(Admin, "SHOW server_version_num").rows

      if String.to_integer(version) >= 170_000 do
        for table <- ["oban_jobs", "oban_peers"] do
          assert_release_grant_refused!(conn, table, "MAINTAIN")
        end
      end
    after
      GenServer.stop(conn)
    end
  end

  defp assert_release_grant_refused!(conn, table, privilege, grantable \\ false) do
    relation = "mixer_release_jobs.#{table}"
    grant_option = if grantable, do: " WITH GRANT OPTION", else: ""
    revoke_option = if grantable, do: "GRANT OPTION FOR ", else: ""

    DB.q!(Admin, "GRANT #{privilege} ON #{relation} TO mixer_release_processor#{grant_option}")

    try do
      assert_raise RuntimeError, "release processor admission refused", fn ->
        ProcessorAdmission.after_connect(conn)
      end
    after
      DB.q!(
        Admin,
        "REVOKE #{revoke_option}#{privilege} ON #{relation} FROM mixer_release_processor"
      )
    end

    assert :ok = ProcessorAdmission.after_connect(conn)
  end

  defp await_release_jobs!(expected, deadline) do
    unless DB.q!(Admin, "SELECT state::text FROM mixer_release_jobs.oban_jobs ORDER BY id").rows ==
             expected do
      assert System.monotonic_time(:millisecond) < deadline,
             "release jobs did not reach #{inspect(expected)}"

      Process.sleep(25)
      await_release_jobs!(expected, deadline)
    end
  end

  defp assert_retry_checkpoint_stops_at_cutoff do
    owner = Process.whereis(RuntimeOwner)
    initial = RuntimeOwner.status()
    deadline = System.monotonic_time(:millisecond) + 5_000
    assert {:ok, lease} = GenServer.call(owner, {:reserve, deadline, System.system_time(:second)})

    try do
      :ok = :sys.suspend(owner)

      try do
        start = System.monotonic_time(:millisecond)
        assert {:error, %Store.Failure{}} = RuntimeOwner.checkpoint(lease, start + 50)
        assert System.monotonic_time(:millisecond) - start < 500
      after
        :ok = :sys.resume(owner)
      end

      assert :ok = RuntimeOwner.checkpoint(lease)
      assert RuntimeOwner.status() == initial
    after
      assert :ok = GenServer.call(owner, {:release, lease})
    end
  end

  defp assert_browser_reads_wait_for_checkout(c, owner, target, expected_sequence) do
    {session, head} =
      with_occupied_checkouts(fn pool ->
        session = Task.async(fn -> http(c, "/auth/session", owner) end)
        head = Task.async(fn -> http(c, path(target), owner) end)
        await_browser_reads(pool, System.monotonic_time(:millisecond) + 250)
        {session, head}
      end)

    assert %{status: 200, body: session_body} = Task.await(session, 3_000)
    assert %{"state" => "authenticated"} = Jason.decode!(session_body)
    assert %{status: 200, body: head_body} = Task.await(head, 3_000)
    assert %{"release" => %{"sequence" => ^expected_sequence}} = Jason.decode!(head_body)
  end

  defp assert_browser_read_refusal_preserves_owner(c, owner) do
    initial = RuntimeOwner.status()
    assert %{phase: :storage_ready} = initial

    with_occupied_checkouts(fn pool ->
      start = System.monotonic_time(:millisecond)
      assert http(c, "/auth/session", owner).status == 503
      assert System.monotonic_time(:millisecond) - start < 1_500

      assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
               DBConnection.get_connection_metrics(pool)

      assert RuntimeOwner.status() == initial
    end)

    assert %{status: 200, body: body} = http(c, "/auth/session", owner)
    assert %{"state" => "authenticated"} = Jason.decode!(body)
  end

  defp with_occupied_checkouts(operation) do
    parent = self()
    %{pid: pool} = Ecto.Adapter.lookup_meta(LifecycleRepo)

    holders =
      for _ <- 1..2 do
        Task.async(fn ->
          LifecycleRepo.checkout(
            fn ->
              send(parent, {:checkout_held, self()})

              receive do
                :release_checkout -> :released
              after
                2_000 -> raise "browser read checkout control expired"
              end
            end,
            timeout: 3_000
          )
        end)
      end

    try do
      for holder <- holders do
        pid = holder.pid
        assert_receive {:checkout_held, ^pid}, 1_000
      end

      operation.(pool)
    after
      for holder <- holders, do: send(holder.pid, :release_checkout)
      for holder <- holders, do: assert(Task.await(holder, 1_000) == :released)
    end
  end

  defp await_browser_reads(pool, deadline) do
    assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
             DBConnection.get_connection_metrics(pool)

    if map_size(:sys.get_state(RuntimeOwner).operations) != 2 do
      assert System.monotonic_time(:millisecond) < deadline,
             "both browser reads must wait for the lifecycle checkout"

      Process.sleep(5)
      await_browser_reads(pool, deadline)
    end
  end

  defp prepare_release_fixture!(name) do
    key = "MIXER_BROWSER_CATALOG_FIXTURE_ROOT"
    parent = System.fetch_env!(key)
    root = Path.join(parent, name)
    File.mkdir!(root)
    System.put_env(key, root)
    on_exit(fn -> System.put_env(key, parent) end)

    prepare!(:release_operator)
  end

  defp assert_delivery(c, offer_path, artifact_path, signed, envelope, config) do
    offer = http(c, offer_path, [])
    assert offer.status == 200
    assert response_header(offer, "cache-control") == ["no-store"]

    assert Jason.decode!(offer.body) == %{
             "signed_assignment" => Jason.decode!(signed),
             "artifact_url" => artifact_path
           }

    assert :binary.matches(offer.body, signed) |> length() == 1
    artifact = http(c, artifact_path, [])
    assert artifact.status == 200
    assert response_header(artifact, "cache-control") == ["no-store"]
    assert artifact.body == envelope

    %{"signed_manifest" => manifest, "payload" => payload} = Jason.decode!(artifact.body)

    context = %{
      channel: config.target.channel,
      last_sequence: 0,
      now: System.system_time(:second)
    }

    assert {:ok, _} =
             AssignmentV3.verify(
               signed,
               %{
                 signed_manifest_bytes: Jason.encode!(manifest),
                 payload: Base.decode64!(payload)
               },
               config.roots,
               config.host,
               context
             )

    {offer.body, artifact.body}
  end

  defp assert_no_offer(c, path) do
    result = http(c, path, [])
    assert result.status == 204
    assert result.body == ""
    assert response_header(result, "cache-control") == ["no-store"]
  end

  defp delivery_path(target, installation) do
    query =
      target
      |> Target.signed_scope()
      |> Map.merge(%{
        "runtime" => target.runtime_sha256,
        "channel" => target.channel,
        "installation" => installation
      })
      |> URI.encode_query()

    "/v3/updates?" <> query
  end

  defp delivered_artifact_path(digest),
    do: "/v3/artifacts/#{digest}?organization=org-a&project=project-a"

  # Uses the public TEST ONLY seeds from services/protocol/testdata/generate-v3.go.
  defp sign_fixture(role, document) do
    seed =
      :crypto.hash(:sha256, "Mixer publicly reproducible TEST ONLY release-v3 fixture / " <> role)

    {:ok, cbor} = ArtifactCBOR.encode(document)
    signature = :crypto.sign(:eddsa, :none, "mixer.#{role}.v3\0" <> cbor, [seed, :ed25519])
    field = if role == "artifact", do: "manifest", else: role
    %{field => document, "signature" => Base.encode64(signature)}
  end

  defp provision_stage_promotion! do
    for {dir, name, module} <- [
          {"local_release_target_registry", "20261120000015_add_local_release_target_registry",
           MixerHosted.Repo.Migrations.AddLocalReleaseTargetRegistry},
          {"local_stage_promotion", "20261120000016_add_local_stage_promotion",
           MixerHosted.Repo.Migrations.AddLocalStagePromotion}
        ] do
      unless Code.ensure_loaded?(module), do: Code.require_file("priv/#{dir}/#{name}.exs")
      [version, _] = String.split(name, "_", parts: 2)
      assert :ok = Ecto.Migrator.up(Migration, String.to_integer(version), module, log: false)
    end
  end

  defp seed_stage_direction!(direction) do
    DB.q!(Admin, """
    GRANT INSERT (action) ON public.mixer_release_publications TO browser_ordinary
    """)

    DB.q!(Admin, """
    GRANT SELECT, INSERT (
      direction_id,writer_role,organization_id,project_id,application_id,
      source_environment_id,destination_environment_id,
      source_ios_runtime_sha256,source_ios_channel,source_android_runtime_sha256,source_android_channel,
      destination_ios_runtime_sha256,destination_ios_channel,destination_android_runtime_sha256,destination_android_channel,
      idempotency_key,request_sha256,principal_id,reason,
      source_ios_sequence,source_ios_artifact_sha256,source_android_sequence,source_android_artifact_sha256,
      destination_ios_sequence,destination_ios_artifact_sha256,
      destination_android_sequence,destination_android_artifact_sha256
    ) ON public.mixer_stage_promotion_bindings TO browser_ordinary
    """)

    DB.q!(Admin, """
    GRANT EXECUTE ON FUNCTION
      public.mixer_stage_promotion_admit(text),
      public.mixer_stage_promotion_source(text,numeric,numeric) TO browser_ordinary
    """)

    targets =
      for side <- [:source, :destination],
          platform <- [:ios, :android],
          do: Map.fetch!(direction, side)[platform].target

    for target <- targets do
      DB.q!(
        Admin,
        """
        INSERT INTO public.mixer_release_delivery_enrollments
          (reader_role,organization_id,project_id,application_id,environment_id,
           platform,runtime_sha256,channel)
        VALUES ('mixer_release_delivery','org-a','project-a','fieldlog',$1,$2,$3,$4)
        """,
        [target.scope.environment_id, target.platform, target.runtime_sha256, target.channel]
      )
    end

    DB.q!(
      Admin,
      """
      INSERT INTO public.mixer_stage_promotion_directions (
        direction_id,writer_role,organization_id,project_id,application_id,
        source_environment_id,destination_environment_id,
        source_ios_runtime_sha256,source_ios_channel,source_android_runtime_sha256,source_android_channel,
        destination_ios_runtime_sha256,destination_ios_channel,destination_android_runtime_sha256,destination_android_channel
      ) VALUES ($1,'browser_ordinary','org-a','project-a','fieldlog','development','staging',
                $2,'internal',$3,'internal',$4,'candidate',$5,'candidate')
      """,
      [@promotion_direction | Enum.map(targets, & &1.runtime_sha256)]
    )
  end

  defp assert_empty_stage_promotion! do
    assert [[0, 0, 0, 0]] =
             DB.q!(Admin, """
             SELECT (SELECT count(*) FROM public.mixer_release_heads
                     WHERE environment_id='staging' AND sequence IS NOT NULL),
                    (SELECT count(*) FROM public.mixer_release_publications WHERE environment_id='staging'),
                    (SELECT count(*) FROM public.mixer_stage_promotion_bindings),
                    (SELECT count(*) FROM mixer_release_jobs.oban_jobs WHERE args->>'environment_id'='staging')
             """).rows
  end

  defp spaced_assignment(variant) do
    variant
    |> publication()
    |> Map.fetch!(:evidence)
    |> Map.fetch!(:signed_assignment_bytes)
    |> Jason.decode!()
    |> Jason.encode!(pretty: true)
  end

  defp promotion_body(ios, android, source_ios_sequence \\ "7", extra \\ "") do
    ~s({"source_ios_sequence":) <>
      source_ios_sequence <>
      ~s(,"source_android_sequence":9,"ios_signed_assignment":) <>
      ios <>
      ~s(,"android_signed_assignment":) <> android <> extra <> "}"
  end

  defp promotion_receipt(variant) do
    %{
      "artifact_sha256" => publication(variant).artifact_sha256,
      "rollout_basis_points" => variant.assignment["rollout_basis_points"],
      "sequence" => variant.assignment["sequence"]
    }
  end

  defp release_provisioning(enrollment) do
    %{
      host: enrollment.host,
      channel: enrollment.target.channel,
      roots:
        Enum.map(
          enrollment.roots,
          &Map.update!(&1, "public_key", fn key -> Base.encode64(key) end)
        )
    }
  end

  defp promotion_post(
         c,
         token,
         path,
         bytes,
         metadata \\ [{"x-mixer-reason", @reason}],
         key \\ "http-promote"
       ) do
    authorization = if token, do: [{"authorization", "Bearer " <> token}], else: []

    http(
      c,
      path,
      authorization ++
        metadata ++
        [
          {"content-type", "application/json"},
          {"idempotency-key", key},
          {"content-length", Integer.to_string(byte_size(bytes))}
        ],
      "POST",
      bytes
    )
  end

  defp provision_delivery! do
    version = 20_261_120_000_003
    module = MixerHosted.Repo.Migrations.AddLocalReleaseDelivery

    unless Code.ensure_loaded?(module),
      do:
        Code.require_file("priv/local_release_delivery/#{version}_add_local_release_delivery.exs")

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)

    DB.q!(Admin, "CREATE ROLE mixer_release_delivery LOGIN NOINHERIT")

    on_exit(fn ->
      conn = DB.connection!("browser_admin")

      try do
        Postgrex.query!(conn, "DROP OWNED BY mixer_release_delivery", [])
        Postgrex.query!(conn, "DROP ROLE mixer_release_delivery", [])
      after
        GenServer.stop(conn)
      end
    end)

    DB.q!(Admin, "GRANT USAGE ON SCHEMA public TO mixer_release_delivery")

    DB.q!(
      Admin,
      "GRANT EXECUTE ON FUNCTION public.mixer_release_delivery_offer(text,text,text,text,text,text,text) TO mixer_release_delivery"
    )

    DB.q!(
      Admin,
      "GRANT EXECUTE ON FUNCTION public.mixer_release_delivery_artifact(text,text,text,text,text,text,text,text) TO mixer_release_delivery"
    )
  end

  defp provision_release_jobs! do
    version = 20_261_120_000_014
    module = MixerHosted.Repo.Migrations.AddLocalReleaseJobs

    unless Code.ensure_loaded?(module),
      do: Code.require_file("priv/local_release_jobs/#{version}_add_local_release_jobs.exs")

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)

    database = Admin.config() |> Keyword.fetch!(:database)

    on_exit(fn ->
      conn = DB.connection!("browser_admin", database)

      try do
        Postgrex.query!(conn, "DROP OWNED BY mixer_release_processor", [])
        Postgrex.query!(conn, "DROP ROLE mixer_release_processor", [])
      after
        GenServer.stop(conn)
      end
    end)

    assert release_jobs_sql!("provision-local-release-jobs.sql") == ""
  end

  defp release_jobs_sql!(name, options \\ []) do
    database = Admin.config() |> Keyword.fetch!(:database)

    {output, status} =
      System.cmd(
        "psql",
        [
          "-X",
          "-q",
          "-At",
          "-w",
          "-h",
          "127.0.0.1",
          "-p",
          to_string(DB.port()),
          "-U",
          "browser_admin",
          "-d",
          database
        ] ++ options ++ ["-f", "../docs/operations/#{name}"],
        stderr_to_stdout: true
      )

    assert status == 0, output
    String.trim(output)
  end

  defp provision_cli! do
    version = 20_261_120_000_004
    module = MixerHosted.Repo.Migrations.AddLocalReleaseCLIRequests

    unless Code.ensure_loaded?(module),
      do: Code.require_file("priv/repo/migrations/#{version}_add_local_release_cli_requests.exs")

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    DB.q!(Admin, "GRANT SELECT,INSERT ON public.mixer_release_cli_requests TO browser_ordinary")
  end

  defp provision_actions! do
    version = 20_261_120_000_010
    module = MixerHosted.Repo.Migrations.AddLocalReleasePublicationAction

    unless Code.ensure_loaded?(module),
      do:
        Code.require_file(
          "priv/repo/migrations/#{version}_add_local_release_publication_action.exs"
        )

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
  end

  defp provision_halt_audit! do
    for {version, filename, module} <- [
          {20_261_120_000_011, "add_local_release_halt_health",
           MixerHosted.Repo.Migrations.AddLocalReleaseHaltHealth},
          {20_261_120_000_012, "add_local_release_halt_audit",
           MixerHosted.Repo.Migrations.AddLocalReleaseHaltAudit}
        ] do
      unless Code.ensure_loaded?(module),
        do: Code.require_file("priv/repo/migrations/#{version}_#{filename}.exs")

      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    DB.q!(Admin, """
    GRANT EXECUTE ON FUNCTION public.mixer_release_audit_halts(text,text,text,text,text,text,text,numeric,integer)
      TO browser_ordinary
    """)
  end

  defp provision_details! do
    version = 20_261_120_000_013
    module = MixerHosted.Repo.Migrations.AddLocalReleaseHeadDetails

    unless Code.ensure_loaded?(module),
      do: Code.require_file("priv/repo/migrations/#{version}_add_local_release_head_details.exs")

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)

    DB.q!(Admin, """
    GRANT EXECUTE ON FUNCTION public.mixer_release_head_details(text,text,text,text,text,text,text)
      TO browser_ordinary
    """)
  end

  defp assert_details_privileges!(target) do
    assert [["browser_schema_owner", true, true, false, false, false, false]] =
             DB.q!(Admin, """
             SELECT pg_get_userbyid(p.proowner), p.prosecdef,
                    has_function_privilege('browser_ordinary', p.oid, 'EXECUTE'),
                    has_function_privilege('browser_lifecycle', p.oid, 'EXECUTE'),
                    has_function_privilege('browser_writer', p.oid, 'EXECUTE'),
                    has_any_column_privilege('browser_ordinary', 'public.mixer_customer_artifacts', 'SELECT'),
                    EXISTS (SELECT 1 FROM aclexplode(p.proacl) WHERE grantee=0)
             FROM pg_proc p WHERE p.oid =
               'public.mixer_release_head_details(text,text,text,text,text,text,text)'::regprocedure
             """).rows

    ordinary = DB.connection!("browser_ordinary")

    try do
      assert [] =
               Postgrex.query!(
                 ordinary,
                 "SELECT * FROM public.mixer_release_head_details($1,$2,$3,$4,$5,$6,$7)",
                 [
                   "org-a",
                   "project-a",
                   "fieldlog",
                   "development",
                   target.platform,
                   target.runtime_sha256,
                   target.channel
                 ]
               ).rows
    after
      GenServer.stop(ordinary)
    end
  end

  defp assert_invalid_details_refused!(c, owner, target, digest) do
    [[signed, canonical, payload_digest]] =
      DB.q!(
        Admin,
        """
        SELECT signed_manifest_bytes,canonical_manifest_cbor,payload_sha256
        FROM public.mixer_customer_artifacts WHERE manifest_sha256=$1
        """,
        [digest]
      ).rows

    replace = fn document, cbor, payload_hash ->
      assert {:ok, :ok} =
               Admin.transaction(fn ->
                 # Fault injection confined to this disposable cluster's exact committed artifact.
                 DB.q!(Admin, "SET LOCAL session_replication_role = replica")

                 assert %{num_rows: 1} =
                          DB.q!(
                            Admin,
                            """
                            UPDATE public.mixer_customer_artifacts
                            SET signed_manifest_bytes=$1,canonical_manifest_cbor=$2,payload_sha256=$3
                            WHERE organization_id='org-a' AND project_id='project-a' AND manifest_sha256=$4
                            """,
                            [document, cbor, payload_hash, digest]
                          )

                 :ok
               end)
    end

    try do
      for {document, cbor, payload_hash} <- [
            {"{}", canonical, payload_digest},
            {signed, canonical <> <<0>>, payload_digest},
            {signed, canonical, String.duplicate("0", 64)}
          ] do
        replace.(document, cbor, payload_hash)
        response = http(c, path(target, :details), owner)
        assert response.status == 503

        assert %{"error" => %{"code" => "authorization_unavailable"}} =
                 Jason.decode!(response.body)
      end
    after
      replace.(signed, canonical, payload_digest)
    end
  end

  defp cli_post(c, token, path, key, bytes) do
    http(
      c,
      path,
      [
        {"authorization", "Bearer " <> token},
        {"content-type", "application/json"},
        {"idempotency-key", key},
        {"content-length", Integer.to_string(byte_size(bytes))}
      ],
      "POST",
      bytes
    )
  end

  defp assert_reader_authority!(target, digest) do
    reader = DB.connection!("mixer_release_delivery")
    writer = DB.connection!("browser_ordinary")

    args = [
      target.scope.organization_id,
      target.scope.project_id,
      target.scope.application_id,
      target.scope.environment_id,
      target.platform,
      target.runtime_sha256,
      target.channel
    ]

    artifact = "SELECT * FROM public.mixer_release_delivery_artifact($1,$2,$3,$4,$5,$6,$7,$8)"

    try do
      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Postgrex.query(writer, artifact, args ++ [digest])

      for sql <- [
            "SELECT envelope_bytes FROM public.mixer_customer_artifacts",
            "UPDATE public.mixer_release_heads SET sequence=99",
            "DELETE FROM public.mixer_release_publications"
          ] do
        assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
                 Postgrex.query(reader, sql, [])
      end

      Postgrex.query!(reader, "BEGIN", [])

      Postgrex.query!(
        reader,
        """
        SET LOCAL mixer.authz.action = 'prior-action';
        """,
        []
      )

      Postgrex.query!(reader, "SET LOCAL mixer.authz.phase = 'prior-phase'", [])
      Postgrex.query!(reader, "SET LOCAL mixer.authz.organization_id = 'prior-org'", [])
      Postgrex.query!(reader, "SET LOCAL mixer.authz.project_id = 'prior-project'", [])
      assert Postgrex.query!(reader, artifact, ["org-b" | tl(args)] ++ [digest]).rows == []
      assert [[_, _, _]] = Postgrex.query!(reader, artifact, args ++ [digest]).rows

      assert [["prior-action", "prior-phase", "prior-org", "prior-project"]] =
               Postgrex.query!(
                 reader,
                 """
                 SELECT current_setting('mixer.authz.action',true),
                        current_setting('mixer.authz.phase',true),
                        current_setting('mixer.authz.organization_id',true),
                        current_setting('mixer.authz.project_id',true)
                 """,
                 []
               ).rows

      Postgrex.query!(reader, "ROLLBACK", [])
    after
      GenServer.stop(reader)
      GenServer.stop(writer)
    end
  end

  defp assert_stale_publication_denied(c, session, target, bytes) do
    [{"cookie", "__Host-mixer-session=" <> cookie}] = session
    {:ok, snapshot} = StoredSnapshot.decode(raw(cookie, c))
    browser_id = snapshot.browser["id"]
    blocker = DB.connection!("browser_admin")

    request =
      try do
        Postgrex.query!(blocker, "BEGIN", [])

        assert %{num_rows: 1} =
                 Postgrex.query!(
                   blocker,
                   "SELECT 1 FROM public.mixer_release_heads FOR UPDATE",
                   []
                 )

        task = Task.async(fn -> publish(session, target, bytes) end)
        await_publication_lock(System.monotonic_time(:millisecond) + 2_000)

        # Inject storage tampering into this fixture without an application transition.
        Postgrex.query!(blocker, "SET LOCAL session_replication_role = replica", [])

        assert %{num_rows: 1} =
                 Postgrex.query!(
                   blocker,
                   """
                   UPDATE public.mixer_browser_session_vault
                   SET tag=set_byte(tag,0,get_byte(tag,0) # 1)
                   WHERE browser_id=$1
                   """,
                   [browser_id]
                 )

        Postgrex.query!(blocker, "COMMIT", [])
        task
      after
        GenServer.stop(blocker)
      end

    assert {:error, :authorization_unavailable} = Task.await(request, 5_000)
    assert [[0]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
  end

  defp await_publication_lock(deadline) do
    case DB.q!(Admin, """
         SELECT count(*) FROM pg_stat_activity
         WHERE datname=current_database() AND usename='browser_ordinary'
           AND wait_event_type='Lock' AND cardinality(pg_blocking_pids(pid)) > 0
           AND query LIKE '%mixer_release_heads%FOR UPDATE%'
         """).rows do
      [[1]] ->
        :ok

      _ ->
        assert System.monotonic_time(:millisecond) < deadline,
               "the admitted browser publication must reach the database head lock"

        Process.sleep(5)
        await_publication_lock(deadline)
    end
  end

  defp provision! do
    for {version, filename, module} <- [
          {20_261_120_000_001, "add_local_release_ledger",
           MixerHosted.Repo.Migrations.AddLocalReleaseLedger},
          {20_261_120_000_002, "add_local_release_head_read",
           MixerHosted.Repo.Migrations.AddLocalReleaseHeadRead}
        ] do
      unless Code.ensure_loaded?(module),
        do: Code.require_file("priv/repo/migrations/#{version}_#{filename}.exs")

      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    DB.q!(
      Admin,
      "GRANT SELECT,UPDATE(sequence) ON public.mixer_release_heads TO browser_ordinary"
    )

    DB.q!(Admin, """
    GRANT SELECT, INSERT (
      organization_id, project_id, application_id, environment_id, platform, runtime_sha256, channel,
      sequence, previous_sequence, artifact_sha256, signed_assignment_bytes, rollout_basis_points,
      idempotency_key, reason, principal_id
    ) ON public.mixer_release_publications TO browser_ordinary
    """)

    DB.q!(Admin, """
    GRANT EXECUTE ON FUNCTION
      public.mixer_release_publish_allowed(text,text,text,text),
      public.mixer_release_read_allowed(text,text,text,text),
      public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text)
    TO browser_ordinary
    """)

    DB.q!(
      Admin,
      "GRANT EXECUTE ON FUNCTION public.mixer_browser_current_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) TO browser_ordinary"
    )
  end

  # Stage through the artifact authorization/storage path. Its isolated role
  # retires before the browser resumes its protected ACL checks.
  defp upload!(c, identity, config, digest, envelope, key \\ "uploaded-once") do
    with_uploader!(c, config, fn ->
      CustomerArtifacts.upload_at(identity, @tenant, digest, key, envelope, %{
        reason: "Stage the exact maintained signed artifact",
        source_ip: nil
      })
    end)
  end

  defp with_uploader!(c, config, operation) do
    DB.q!(Admin, "CREATE ROLE release_fixture_uploader LOGIN NOINHERIT")

    try do
      DB.q!(Admin, "GRANT USAGE ON SCHEMA public TO release_fixture_uploader")

      for table <-
            ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
          do:
            DB.q!(
              Admin,
              "GRANT SELECT ON public.mixer_authz_#{table} TO release_fixture_uploader"
            )

      for helper <- ~w(profiles principals families credentials organization_heads project_heads),
          do:
            DB.q!(
              Admin,
              "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO release_fixture_uploader"
            )

      for table <- ~w(artifacts audit_events idempotency),
          do:
            DB.q!(
              Admin,
              "GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO release_fixture_uploader"
            )

      DB.q!(
        Admin,
        "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO release_fixture_uploader"
      )

      for name <-
            ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists) do
        DB.q!(
          Admin,
          "GRANT EXECUTE ON FUNCTION public.#{name}(#{CustomerArtifacts.Schema.signatures()[name]}) TO release_fixture_uploader"
        )
      end

      settings = Keyword.merge(c.hosted.repo, username: "release_fixture_uploader", pool_size: 1)
      start_supervised!({Uploader, settings})
      DB.q!(Uploader, "SELECT 1")

      replace_config!(
        CustomerArtifacts,
        config |> Map.delete(:target) |> Map.put(:repo, Uploader)
      )

      operation.()
    after
      if Process.whereis(Uploader), do: stop_supervised!(Uploader)
      DB.q!(Admin, "DROP OWNED BY release_fixture_uploader")
      DB.q!(Admin, "DROP ROLE release_fixture_uploader")
    end
  end

  defp seed_target!(target) do
    for sql <- [
          "UPDATE public.mixer_authz_memberships SET role='owner' WHERE id='member-a'",
          "INSERT INTO public.mixer_authz_principals VALUES('person-2','human',true,0,1)",
          "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-2','human','person-2',true,1)",
          "INSERT INTO public.mixer_authz_memberships VALUES('member-b','person-2','org-b',NULL,'all_projects','owner',true,0,NULL,1)",
          "INSERT INTO public.mixer_authz_applications VALUES('org-b','project-b','fieldlog',true)",
          """
          INSERT INTO public.mixer_authz_environments (organization_id,project_id,application_id,id,active)
          VALUES ('org-a','project-a','fieldlog','development',true),
                 ('org-a','project-a','fieldlog','staging',true),
                 ('org-b','project-b','fieldlog','development',true)
          """
        ],
        do: DB.q!(Admin, sql)

    {:ok, genesis} = CustomerArtifactEvent.genesis("org-a", "project-a")

    DB.q!(
      Admin,
      "INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)",
      [genesis]
    )

    seed_head!(target)
  end

  defp seed_head!(target) do
    assert %{num_rows: 1} =
             DB.q!(
               Migration,
               """
               INSERT INTO public.mixer_release_heads
                 (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,writer_role)
               VALUES ('org-a','project-a','fieldlog',$1,$2,$3,$4,'browser_ordinary')
               """,
               [
                 target.scope.environment_id,
                 target.platform,
                 target.runtime_sha256,
                 target.channel
               ]
             )
  end

  defp replace_config!(key, value) do
    previous = Application.fetch_env(:mixer_hosted, key)
    Application.put_env(:mixer_hosted, key, value)

    on_exit(fn ->
      case previous do
        {:ok, existing} -> Application.put_env(:mixer_hosted, key, existing)
        :error -> Application.delete_env(:mixer_hosted, key)
      end
    end)
  end

  defp login(c, mode \\ :ok) do
    :ok = GenServer.call(c.provider, {:mode, mode})
    flow = begin_http(c, bootstrap_http(c))
    response = http(c, "/auth/callback?" <> flow.query, flow.headers)
    assert response.status == 303
    session_headers = headers(response_cookie(response))
    session = http(c, "/auth/session", session_headers)
    assert session.status == 200
    assert %{"state" => "authenticated"} = Jason.decode!(session.body)
    session_headers
  end

  defp access_token!(c, [{"cookie", "__Host-mixer-session=" <> cookie}]) do
    {:ok, snapshot} = StoredSnapshot.decode(raw(cookie, c))
    %{context: context, sealed: sealed} = snapshot.session_envelope
    {:ok, %Vault.Active{access_token: token}} = Vault.open(c.runtime.custody.key, context, sealed)
    token
  end

  defp upload_identity!(c, headers) do
    token = access_token!(c, headers)

    assert {:ok, identity} =
             ConfiguredVerifier.authenticate(
               KeyOwner,
               c.config.profile_id,
               token,
               System.system_time(:second)
             )

    identity
  end

  defp publish(headers, target, bytes),
    do: RuntimeOwner.publish_release(headers, target, bytes, "initial", @reason)

  defp read!(c, headers, target, view \\ :summary) do
    response = http(c, path(target, view), headers)
    assert response.status == 200
    assert response_header(response, "cache-control") == ["no-store"]
    Jason.decode!(response.body)
  end

  defp assert_status(c, headers, target, status, view \\ :summary) do
    response = http(c, path(target, view), headers)
    assert response.status == status
    assert %{"error" => %{"code" => "not_found"}} = Jason.decode!(response.body)
  end

  defp path(target, view \\ :summary) do
    @head <>
      "?" <>
      URI.encode_query(
        Map.merge(Map.from_struct(target.scope), %{
          platform: target.platform,
          runtime_fingerprint: target.runtime_sha256,
          channel: target.channel
        })
      ) <> view_query(view)
  end

  defp view_query(:summary), do: ""
  defp view_query(:details), do: "&view=details"
  defp view_query(:details_v2), do: "&view=details-v2"

  defp string_keys(map), do: Map.new(map, fn {key, value} -> {Atom.to_string(key), value} end)
end
