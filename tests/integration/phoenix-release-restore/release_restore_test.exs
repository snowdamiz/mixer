Code.require_file("mixer_hosted/releases/configured_release_replay_test.exs", __DIR__)

defmodule MixerHosted.Releases.RestoreTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture,
    only: [http: 3, http: 5, response_header: 2]

  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.{LocalUpload, Topology, UploadRepo}
  alias MixerHosted.Identity.{KeyOwner, KeyOwnerSupervisor, StartupFixture, TLSFixture}
  alias MixerHosted.Releases.{DeliveryRepo, RuntimeProvisioning, Target, WriterRepo}
  alias MixerHosted.Releases.ConfiguredReleaseReplayTest, as: Fixture
  alias MixerHosted.Test.{ConfiguredReleaseReplayRepo, FieldLogReleasePacket}

  @admin "mixer_replay_admin"
  @uploader_password "synthetic-replay-uploader"
  @scopes "mixer.artifact.upload mixer.release.publish mixer.artifact.read mixer.audit.read"
  @vector Path.expand("../../services/protocol/testdata/signed-release-v3.json", __DIR__)

  @tag timeout: 60_000
  test "a frozen release journal and artifact snapshot survive a separate cluster" do
    work = System.fetch_env!("RELEASE_RESTORE_ROOT")
    source? = System.fetch_env!("RELEASE_RESTORE_PHASE") == "source"
    delivery = Path.join(work, "delivery-android")

    if source? do
      vector = @vector |> File.read!() |> Jason.decode!()
      assert FieldLogReleasePacket.synthetic!(work, vector) == delivery
    end

    {packet, phases} = FieldLogReleasePacket.read!(delivery)
    {config, startup} = configure!(packet)
    [published, private, _rollback] = FieldLogReleasePacket.admit!(phases, config)
    target = config.target
    assert Target.signed_scope(target) == published.assignment["scope"]
    assert published.assignment["sequence"] == 1

    if source? do
      Fixture.provision!(target)
      Fixture.provision_uploader!(@uploader_password)
      seed_outsider!()
    end

    {tokens, jwks_port} = identity!(work, source?)
    assert {:ok, _} = Application.ensure_all_started(:mixer_hosted)

    {port, reads, checks, summary, snapshot_digest} =
      try do
        assert MixerHosted.Application.startup() == {:ok, {startup, :disabled}}
        assert startup.oban[:queues] == []
        assert {:ok, {{127, 0, 0, 1}, port}} = MixerHostedWeb.Endpoint.server_info(:http)
        record_port!("phoenix", port)
        client = %{http_port: port}
        assert %{status: 200} = http(client, "/health/live", [])
        assert_logins!()
        assert Topology.catalog_matches?(UploadRepo)

        tenant = "/v3/orgs/#{target.scope.organization_id}/projects/#{target.scope.project_id}"
        publish = tenant <> "/channels/beta/publish"
        validate = tenant <> "/releases/validate"
        assignment_body = ~s({"signed_assignment":) <> published.signed <> "}"
        validation_body = Jason.encode!(%{artifact_sha256: published.digest})

        offer_fields =
          Map.merge(Target.signed_scope(target), %{
            "channel" => target.channel,
            "runtime" => target.runtime_sha256,
            "installation" => packet["installation"]
          })

        offer = "/v3/updates?" <> URI.encode_query(offer_fields)
        artifact = artifact_path(target, published.digest)

        if source? do
          empty!(http(client, offer, []))
          refused!(http(client, artifact, []), 404, "not_found")

          uploads = upload!(client, tenant, tokens.owner, [published, private])
          empty!(http(client, offer, []))
          refused!(http(client, artifact, []), 404, "not_found")
          refused!(http(client, artifact_path(target, private.digest), []), 404, "not_found")
          File.write!(Path.join(work, "uploads.json"), Jason.encode!(uploads), [:exclusive])
        end

        before = if not source?, do: snapshot!(work)

        unless source? do
          assert upload!(client, tenant, tokens.owner, [published, private]) ==
                   Jason.decode!(File.read!(Path.join(work, "uploads.json")))
        end

        assert %{status: 200, body: validation} =
                 mutate(client, "POST", validate, tokens.owner, "validate", validation_body)

        assert %{"artifact_sha256" => digest, "protocol_valid" => true} =
                 Jason.decode!(validation)

        assert digest == published.digest

        assert %{status: 200, body: publication} =
                 mutate(client, "POST", publish, tokens.owner, "publish", assignment_body)

        assert Jason.decode!(publication) == %{
                 "artifact_sha256" => published.digest,
                 "rollout_basis_points" => 10_000,
                 "sequence" => 1,
                 "delivery" => "local_only"
               }

        if source? do
          assert %{status: 200, body: ^publication} =
                   mutate(client, "POST", publish, tokens.owner, "publish", assignment_body)
        end

        after_retry = snapshot!(work)
        if not source?, do: assert(before == after_retry)

        assert %{status: 200, body: offer_bytes} = offer_response = http(client, offer, [])

        assert %{status: 200, body: envelope_bytes} =
                 artifact_response = http(client, artifact, [])

        assert response_header(offer_response, "cache-control") == ["no-store"]
        assert response_header(artifact_response, "cache-control") == ["no-store"]

        assert offer_bytes ==
                 ~s({"signed_assignment":) <>
                   published.signed <>
                   ~s(,"artifact_url":) <> Jason.encode!(artifact) <> "}"

        assert envelope_bytes == published.envelope

        # Compare the signed manifest slice and decoded payload separately as
        # well as the complete HTTP response bodies.
        assert {:ok, envelope, spans, _} =
                 MixerHosted.Protocol.ArtifactJSON.decode(envelope_bytes, 6_291_456)

        assert {_, _, start, length} =
                 Enum.find(spans, fn {key_start, key_size, _, _} ->
                   Jason.decode!(binary_part(envelope_bytes, key_start, key_size)) ==
                     "signed_manifest"
                 end)

        assert binary_part(envelope_bytes, start, length) == published.manifest
        assert Base.decode64!(envelope["payload"]) == published.payload

        checks =
          refusals!(
            client,
            target,
            offer_fields,
            tokens,
            publish,
            assignment_body,
            published,
            private
          )

        private_reads = private_reads!(client, tenant, tokens, config, published, private)

        bodies =
          Map.merge(private_reads, %{
            offer: offer_bytes,
            envelope: envelope_bytes,
            validation: validation,
            publication: publication
          })

        for {name, bytes} <- bodies do
          path = Path.join(work, Atom.to_string(name) <> ".http")

          if source?,
            do: File.write!(path, bytes, [:exclusive]),
            else: assert(File.read!(path) == bytes)
        end

        assert snapshot!(work) == after_retry
        rows = assert_rows!(after_retry, target, published, private)
        assert TLSFixture.info(Process.whereis(:release_restore_jwks)).accepted > 0

        reads =
          bodies
          |> Map.merge(%{manifest: published.manifest, payload: published.payload})
          |> Map.new(fn {name, bytes} ->
            {name, %{bytes: byte_size(bytes), sha256: sha(bytes)}}
          end)

        {port, reads, checks, rows, sha(after_retry)}
      after
        assert :ok = Application.stop(:mixer_hosted)
      end

    stop_supervised!(KeyOwnerSupervisor)
    stop_supervised!(TLSFixture)

    for name <- [
          MixerHosted.Repo,
          WriterRepo,
          DeliveryRepo,
          UploadRepo,
          Oban,
          MixerHosted.Supervisor,
          MixerHostedWeb.Endpoint,
          KeyOwner,
          :release_restore_jwks
        ] do
      refute Process.whereis(name)
    end

    IO.puts(
      "RESTORE_PHASE " <>
        Jason.encode!(%{
          phoenixPort: port,
          jwksPort: jwks_port,
          listenersStopped: true,
          queuesDisabled: true,
          http: reads,
          refusals: Map.merge(checks, %{outsiderArtifactRead: 404, outsiderAuditRead: 404}),
          requestKeyReplay:
            if(source?, do: ["publish"], else: ["upload (both)", "validate", "publish"]),
          rows: summary,
          snapshotSHA256: snapshot_digest
        })
    )
  end

  defp configure!(packet) do
    work = System.fetch_env!("RELEASE_RESTORE_ROOT")
    assert :ok = :public_key.cacerts_load(Path.join(work, "tls/ca.pem"))

    env = %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "127.0.0.1",
      "MIXER_DATABASE_NAME" => System.fetch_env!("PGDATABASE"),
      "MIXER_DATABASE_USER" => "mixer_replay_writer",
      "MIXER_DATABASE_PASSWORD" => "synthetic-replay-writer",
      "MIXER_DATABASE_POOL_SIZE" => "2",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("release-restore-fixture-", 4),
      "MIXER_LOCAL_RELEASE_CONFIG" =>
        Jason.encode!(Map.put(Map.take(packet, ~w(host roots)), "channel", "beta")),
      "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD" => "synthetic-replay-reader",
      "MIXER_LOCAL_RELEASE_WRITER_ENABLED" => "true",
      "MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED" => "true",
      "MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD" => @uploader_password
    }

    # Use only owned dynamic ports. The stock runtime's release config and
    # repository factory derive their other settings from this startup.
    hosted = MixerHosted.RuntimeConfig.load!(env)
    hosted = put_in(hosted.repo[:port], String.to_integer(System.fetch_env!("PGPORT")))
    hosted = put_in(hosted.endpoint[:http][:port], 0)
    {target, delivery} = release = RuntimeProvisioning.load!(env, hosted)
    hosted = LocalUpload.configure!(env, hosted, release)
    writer = RuntimeProvisioning.writer_options!(env, hosted, release)

    for {key, value} <-
          [
            startup: {hosted, :disabled},
            role: hosted.role,
            identity_startup: hosted.identity_startup,
            local_release_target: target,
            local_release_delivery: delivery
          ] ++
            [
              {MixerHosted.Repo, hosted.repo},
              {Oban, hosted.oban},
              {MixerHostedWeb.Endpoint,
               Keyword.merge(
                 Application.fetch_env!(:mixer_hosted, MixerHostedWeb.Endpoint),
                 hosted.endpoint
               )},
              {WriterRepo, writer}
            ] do
      Application.put_env(:mixer_hosted, key, value)
    end

    {target, hosted}
  end

  defp identity!(work, source?) do
    # Use the existing test-only loopback destination selection. The ordinary
    # router still uses ConfiguredVerifier and validates the signed bearer.
    {:ok, _} = Application.ensure_all_started(:jose)
    tls = start_supervised!({TLSFixture, []})
    Process.register(tls, :release_restore_jwks)
    %{ca: ca, ip: ip, port: port} = GenServer.call(tls, :authority)
    record_port!("jwks", port)
    material = Path.join(work, "bearers.json")

    {public, tokens} =
      if source? do
        key = JOSE.JWK.generate_key({:rsa, 2048})
        {_, public} = key |> JOSE.JWK.to_public() |> JOSE.JWK.to_map()

        tokens = %{
          owner: bearer(key, "replay-subject", "replay-token", @scopes),
          outsider: bearer(key, "other-subject", "other-token", @scopes),
          limited: bearer(key, "replay-subject", "replay-token", "mixer.artifact.upload")
        }

        File.write!(material, Jason.encode!([public, tokens]), [:exclusive])
        {public, tokens}
      else
        [public, %{"owner" => owner, "outsider" => outsider, "limited" => limited}] =
          Jason.decode!(File.read!(material))

        {public, %{owner: owner, outsider: outsider, limited: limited}}
      end

    jwk = Map.merge(public, %{"kid" => "restore-key", "alg" => "RS256", "use" => "sig"})
    TLSFixture.configure(tls, {:body, Jason.encode!(%{"keys" => [jwk]})})
    settings = StartupFixture.configuration(StartupFixture.envelope(), [ca])

    start_supervised!(%{
      id: KeyOwnerSupervisor,
      start:
        {KeyOwnerSupervisor, :start_fixture,
         [settings.owner_options ++ [fixture: %{ip: ip, port: port}]]},
      type: :supervisor
    })

    {tokens, port}
  end

  defp record_port!(name, port) do
    File.write!(System.fetch_env!("RELEASE_RESTORE_PORTS"), "#{name} #{port}\n", [:append])
  end

  defp bearer(key, subject, credential, scope) do
    now = System.system_time(:second)
    profile = StartupFixture.entry()["profile"]

    claims = %{
      "iss" => profile["issuer"],
      "aud" => profile["audience"],
      "client_id" => profile["client_id"],
      "sub" => subject,
      "jti" => credential,
      "scope" => scope,
      "iat" => now - 1,
      "exp" => now + 600
    }

    {_, token} =
      key
      |> JOSE.JWS.sign(Jason.encode!(claims), %{
        "alg" => "RS256",
        "typ" => "at+jwt",
        "kid" => "restore-key"
      })
      |> JOSE.JWS.compact()

    token
  end

  defp seed_outsider! do
    Fixture.with_repo(@admin, fn ->
      for statement <- [
            "INSERT INTO public.mixer_authz_principals VALUES ('other-owner','human',true,0,1)",
            "INSERT INTO public.mixer_authz_bindings VALUES ('startup-fixture',1,'other-subject','human','other-owner',true,1)",
            "INSERT INTO public.mixer_authz_families VALUES ('other-family','startup-fixture',1,'other-owner',true,0,NULL,1)",
            "INSERT INTO public.mixer_authz_credentials VALUES ('startup-fixture',1,'other-token','other-owner','other-family',true,0,NULL,1)",
            "INSERT INTO public.mixer_authz_organizations VALUES ('other-tenant',true)",
            "INSERT INTO public.mixer_authz_projects VALUES ('other-tenant','fieldlog',true)",
            "INSERT INTO public.mixer_authz_organization_heads VALUES ('other-tenant',1)",
            "INSERT INTO public.mixer_authz_project_heads VALUES ('other-tenant','fieldlog',1)",
            "INSERT INTO public.mixer_authz_memberships VALUES ('other-member','other-owner','other-tenant','fieldlog','exact_project','owner',true,0,NULL,1)"
          ] do
        Ecto.Adapters.SQL.query!(ConfiguredReleaseReplayRepo, statement, [], log: false)
      end
    end)
  end

  defp assert_logins! do
    for {repo, role, artifact_read, release_read} <- [
          {WriterRepo, "mixer_replay_writer", false, true},
          {DeliveryRepo, "mixer_release_delivery", false, false},
          {UploadRepo, "mixer_artifact_uploader", true, false}
        ] do
      assert Ecto.Adapters.SQL.query!(
               repo,
               """
               SELECT session_user::text, ssl, rolsuper, rolbypassrls, rolinherit,
                 has_any_column_privilege(current_user,'public.mixer_customer_artifacts','SELECT'),
                 has_table_privilege(current_user,'public.mixer_release_publications','SELECT')
               FROM pg_stat_ssl, pg_roles WHERE pid=pg_backend_pid() AND rolname=current_user
               """,
               [],
               log: false
             ).rows == [
               [role, true, false, false, false, artifact_read, release_read]
             ]
    end
  end

  defp upload!(client, tenant, token, phases) do
    for phase <- phases do
      assert %{status: 201, body: body} =
               mutate(
                 client,
                 "PUT",
                 tenant <> "/artifacts/" <> phase.digest,
                 token,
                 "upload-" <> phase.digest,
                 phase.envelope
               )

      assert Jason.decode!(body) == %{"artifact_sha256" => phase.digest, "immutable" => true}
      body
    end
  end

  defp private_reads!(client, tenant, tokens, config, published, private) do
    # The loopback uploader is configured at startup. Scoped GETs use the
    # existing trusted artifact facade configuration and the same restricted pool.
    refute Application.get_env(:mixer_hosted, CustomerArtifacts)

    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      repo: UploadRepo,
      host: config.host,
      roots: config.roots
    })

    owner = [{"authorization", "Bearer " <> tokens.owner}]
    outsider = [{"authorization", "Bearer " <> tokens.outsider}]

    try do
      [published_bytes, private_bytes] =
        for phase <- [published, private] do
          path = tenant <> "/artifacts/" <> phase.digest
          assert %{status: 200, body: bytes} = response = http(client, path, owner)
          assert response_header(response, "cache-control") == ["no-store"]
          assert bytes == phase.envelope
          refused!(http(client, path, outsider), 404, "not_found")
          bytes
        end

      audit = tenant <> "/audit"
      assert %{status: 200, body: audit_bytes} = response = http(client, audit, owner)
      assert response_header(response, "cache-control") == ["no-store"]

      assert %{"events" => [%{"sequence" => 1}, %{"sequence" => 2}], "next" => 2} =
               Jason.decode!(audit_bytes)

      refused!(http(client, audit, outsider), 404, "not_found")
      %{ownerPublished: published_bytes, ownerPrivate: private_bytes, ownerAudit: audit_bytes}
    after
      Application.delete_env(:mixer_hosted, CustomerArtifacts)
    end
  end

  defp refusals!(client, target, offer_fields, tokens, publish, body, published, private) do
    other_offer = offer_fields |> Map.put("organization", "other-tenant") |> URI.encode_query()
    empty!(http(client, "/v3/updates?" <> other_offer, []))
    wrong_channel = offer_fields |> Map.put("channel", "stable") |> URI.encode_query()
    empty!(http(client, "/v3/updates?" <> wrong_channel, []))

    refused!(
      http(client, "/v3/updates?" <> wrong_channel <> "&channel=beta", []),
      400,
      "invalid_query"
    )

    absent =
      http(client, artifact_path(target, String.duplicate("0", 64)), [])
      |> refused!(404, "not_found")

    assert absent ==
             http(client, artifact_path(target, private.digest), []) |> refused!(404, "not_found")

    foreign =
      "/v3/artifacts/" <> published.digest <> "?organization=other-tenant&project=fieldlog"

    assert absent == http(client, foreign, []) |> refused!(404, "not_found")

    private_route =
      "/v3/orgs/" <>
        target.scope.organization_id <>
        "/projects/" <>
        target.scope.project_id <> "/artifacts/" <> private.digest

    refused!(http(client, private_route, []), 401, "unauthenticated")
    refused!(mutate(client, "POST", publish, nil, "publish", body), 401, "unauthenticated")
    refused!(mutate(client, "POST", publish, tokens.limited, "publish", body), 403, "role_denied")

    refused!(
      mutate(client, "POST", publish, tokens.outsider, "publish", body),
      403,
      "scope_denied"
    )

    foreign_publish =
      String.replace(publish, "/orgs/" <> target.scope.organization_id, "/orgs/other-tenant")

    refused!(
      mutate(client, "POST", foreign_publish, tokens.owner, "publish", body),
      403,
      "scope_denied"
    )

    refused!(
      mutate(client, "POST", publish, tokens.owner, "publish", body <> " "),
      409,
      "idempotency_conflict"
    )

    %{
      otherTenantOffer: 204,
      wrongChannel: 204,
      duplicateQuery: 400,
      crossTenantArtifact: 404,
      unpublishedArtifact: 404,
      unauthenticatedPrivateRead: 401,
      unauthenticatedPublish: 401,
      insufficientScope: 403,
      outsiderPublish: 403,
      wrongTenantPublish: 403,
      changedRetry: 409
    }
  end

  defp assert_rows!(snapshot, target, published, private) do
    rows = Jason.decode!(snapshot)

    assert [
             %{
               "sequence" => 1,
               "channel" => "beta",
               "organization_id" => org,
               "project_id" => project,
               "writer_role" => "mixer_replay_writer"
             }
           ] = rows["heads"]

    assert {org, project} == {target.scope.organization_id, target.scope.project_id}

    assert [
             %{
               "sequence" => 1,
               "artifact_sha256" => digest,
               "principal_id" => "replay-owner",
               "action" => "publish",
               "idempotency_key" => "publish"
             } = publication
           ] = rows["publications"]

    assert digest == published.digest
    assert publication["signed_assignment_bytes"] == bytea(published.signed)

    assert [publish, validate] = Enum.sort_by(rows["requests"], & &1["idempotency_key"])

    for {request, key, sequence} <- [{publish, "publish", 1}, {validate, "validate", nil}] do
      assert %{
               "idempotency_key" => ^key,
               "publication_sequence" => ^sequence,
               "artifact_sha256" => ^digest,
               "principal_id" => "replay-owner"
             } = request
    end

    assert [%{"sequence" => 2}] = rows["artifactHeads"]
    assert length(rows["artifacts"]) == 2
    assert length(rows["audit"]) == 2
    assert length(rows["artifactReplay"]) == 2

    artifacts =
      for {phase, sequence} <- [{published, 1}, {private, 2}] do
        digest = phase.digest
        key = "upload-" <> digest

        assert %{"manifest_sha256" => ^digest, "creating_sequence" => ^sequence} =
                 artifact =
                 Enum.find(rows["artifacts"], &(&1["manifest_sha256"] == digest))

        assert artifact["envelope_bytes"] == bytea(phase.envelope)
        assert artifact["payload"] == bytea(phase.payload)
        assert artifact["payload_sha256"] == phase.payload_sha

        assert %{"sequence" => ^sequence, "manifest_sha256" => ^digest} =
                 audit =
                 Enum.find(rows["audit"], &(&1["sequence"] == sequence))

        assert %{
                 "action" => "artifact.upload",
                 "outcome" => "created",
                 "actor" => ["replay-owner" | _]
               } =
                 audit["display"]

        assert %{
                 "key" => ^key,
                 "event_sequence" => ^sequence,
                 "principal_id" => "replay-owner",
                 "manifest_sha256" => ^digest,
                 "action" => "artifact.upload",
                 "status" => 201
               } =
                 replay =
                 Enum.find(rows["artifactReplay"], &(&1["key"] == key))

        assert replay["request_sha256"] == audit["display"]["request_sha256"]

        %{
          digest: digest,
          sequence: sequence,
          uploadKey: key,
          auditSHA256: audit["event_sha256"],
          requestSHA256: replay["request_sha256"],
          payloadSHA256: phase.payload_sha
        }
      end

    %{
      target: Target.signed_scope(target),
      activeSequence: 1,
      publication:
        Map.take(
          publication,
          ~w(sequence previous_sequence artifact_sha256 principal_id action idempotency_key)
        ),
      requests:
        Enum.map(
          [publish, validate],
          &Map.take(&1, ~w(idempotency_key request_sha256 publication_sequence))
        ),
      artifacts: artifacts
    }
  end

  defp snapshot!(work) do
    Fixture.with_repo(@admin, fn ->
      %{rows: [[snapshot]]} =
        Ecto.Adapters.SQL.query!(
          ConfiguredReleaseReplayRepo,
          File.read!(Path.join(work, "snapshot.sql")),
          [],
          log: false
        )

      snapshot
    end)
  end

  defp mutate(client, method, path, token, key, body) do
    bearer = if token, do: [{"authorization", "Bearer " <> token}], else: []

    http(
      client,
      path,
      bearer ++
        [
          {"content-type", "application/json"},
          {"content-length", Integer.to_string(byte_size(body))},
          {"idempotency-key", key},
          {"x-mixer-reason", "Synthetic release restore"}
        ],
      method,
      body
    )
  end

  defp artifact_path(target, digest) do
    query =
      URI.encode_query(
        organization: target.scope.organization_id,
        project: target.scope.project_id
      )

    "/v3/artifacts/" <> digest <> "?" <> query
  end

  defp empty!(response) do
    assert %{status: 204, body: ""} = response
    assert response_header(response, "cache-control") == ["no-store"]
  end

  defp refused!(response, status, code) do
    assert %{status: ^status, body: body} = response
    assert %{"error" => %{"code" => ^code}} = Jason.decode!(body)
    assert response_header(response, "cache-control") == ["no-store"]
    body
  end

  defp bytea(bytes), do: "\\x" <> Base.encode16(bytes, case: :lower)
  defp sha(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
end
