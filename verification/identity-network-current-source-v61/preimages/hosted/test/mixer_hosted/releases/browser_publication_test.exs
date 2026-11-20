Code.require_file("../browser_auth/storage_fixture.exs", __DIR__)

defmodule MixerHosted.Releases.BrowserPublicationTest.Uploader do
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Releases.BrowserPublicationTest do
  use ExUnit.Case, async: false
  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.Audit.CustomerArtifactEvent
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.BrowserAuth.{RuntimeOwner, Store, StoredSnapshot, Vault}
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.Identity.{ConfiguredVerifier, KeyOwner}
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR, AssignmentV3}
  alias MixerHosted.Releases.BrowserPublicationTest.Uploader
  alias MixerHosted.Releases.{DeliveryRepo, Target, WriterRepo}
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB
  alias MixerHosted.Test.StockReleaseCLI

  @head "/console-api/v1/release-head"
  @reason "Publish the local development release"
  @tenant %{organization_id: "org-a", project_id: "project-a"}
  @fixtures Path.expand("../../../../services/protocol/testdata", __DIR__)
  @max_sequence 18_446_744_073_709_551_615

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

  test "publishes the verified upload once and reads the exact tenant-scoped browser head" do
    c = prepare_release_fixture!("browser-publication")
    provision!()
    assert [[nil]] = DB.q!(Admin, "SELECT to_regclass('public.mixer_release_cli_requests')").rows

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

    assert %{num_rows: 1} =
             DB.q!(
               Admin,
               "UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='member-a'"
             )

    assert read!(c, no_publish_scope, target) == published
    assert read!(c, owner, target) == published
    assert {:error, :permission_denied} = publish(owner, target, bytes)

    assert %{num_rows: 1} =
             DB.q!(
               Admin,
               "UPDATE public.mixer_authz_memberships SET role='owner' WHERE id='member-a'"
             )

    assert_status(c, other, target, 404)
    assert_status(c, owner, %{target | scope: %{target.scope | environment_id: "staging"}}, 404)

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
    assert [[2]] = DB.q!(Admin, "SELECT count(*) FROM public.mixer_release_publications").rows
    leases_clean()
  end

  test "shares a head between browser and CLI publication and delivers only committed releases" do
    c = prepare_release_fixture!("public-delivery")
    provision!()
    provision_delivery!()
    provision_cli!()

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
    c = start!(c)
    assert %{phase: :storage_ready} = RuntimeOwner.status()
    assert [["browser_ordinary"]] = DB.q!(WriterRepo, "SELECT session_user").rows
    assert [["browser_ordinary"]] = DB.q!(MixerHosted.Repo, "SELECT session_user").rows

    first_digest = fixture["artifact_sha256"]
    first_envelope = Jason.encode!(Map.take(fixture, ~w(signed_manifest payload)))
    first = assignment |> Map.put("rollout_basis_points", fixture["cohort_bucket"] + 1)

    signed_first =
      sign_fixture("assignment", first) |> Jason.encode!(pretty: true) |> Kernel.<>("\n")

    second_manifest = %{
      fixture["signed_manifest"]["manifest"]
      | "release_id" => "fixture-v3-next"
    }

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
    assert_no_offer(c, offer_path)
    assert http(c, first_path, []).status == 404
    assert http(c, second_path, []).status == 404

    assert {:ok, %{artifact_sha256: ^first_digest}} =
             RuntimeOwner.publish_release(owner, target, signed_first, "delivery-first", @reason)

    first_sequence = Integer.to_string(first["sequence"])

    assert %{"release" => %{"sequence" => ^first_sequence, "manifestSha256" => ^first_digest}} =
             read!(c, owner, target)

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

    if cli = System.get_env("MIXER_TEST_RELEASE_CLI") do
      with_uploader!(c, config, fn ->
        StockReleaseCLI.publish!(cli, c.http_port, token, second_artifact, signed_second, second)
      end)
    else
      publish_path = cli_base <> "/channels/#{target.channel}/publish"
      body = ~s({"signed_assignment":#{signed_second}})
      assert %{status: 200, body: result} = cli_post(c, token, publish_path, "cli-second", body)

      assert %{"sequence" => sequence, "artifact_sha256" => ^second_digest} =
               Jason.decode!(result)

      assert sequence == second["sequence"]
    end

    second_sequence = Integer.to_string(second["sequence"])

    assert %{"release" => %{"sequence" => ^second_sequence, "manifestSha256" => ^second_digest}} =
             read!(c, owner, target)

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
      assert_delivery(restarted, offer_path, second_path, signed_second, second_envelope, config)
      assert http(restarted, first_path, []).body == first_envelope
      assert_no_offer(restarted, delivery_path(target, "excluded-installation"))
    after
      assert :ok = Application.stop(:mixer_hosted)
    end

    if path = System.get_env("MIXER_PUBLIC_DELIVERY_WIRE_PROOF") do
      File.write!(
        path,
        Jason.encode!(%{offer: offer, artifact: artifact, excluded: "excluded-installation"})
      )
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

  defp provision_cli! do
    version = 20_261_120_000_004
    module = MixerHosted.Repo.Migrations.AddLocalReleaseCLIRequests

    unless Code.ensure_loaded?(module),
      do: Code.require_file("priv/repo/migrations/#{version}_add_local_release_cli_requests.exs")

    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    DB.q!(Admin, "GRANT SELECT,INSERT ON public.mixer_release_cli_requests TO browser_ordinary")
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

    assert %{num_rows: 1} =
             DB.q!(
               Migration,
               """
               INSERT INTO public.mixer_release_heads
                 (organization_id,project_id,application_id,environment_id,platform,runtime_sha256,channel,writer_role)
               VALUES ('org-a','project-a','fieldlog','development',$1,$2,$3,'browser_ordinary')
               """,
               [target.platform, target.runtime_sha256, target.channel]
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

  defp read!(c, headers, target) do
    response = http(c, path(target), headers)
    assert response.status == 200
    assert response_header(response, "cache-control") == ["no-store"]
    Jason.decode!(response.body)
  end

  defp assert_status(c, headers, target, status) do
    response = http(c, path(target), headers)
    assert response.status == status
    assert %{"error" => %{"code" => "not_found"}} = Jason.decode!(response.body)
  end

  defp path(target) do
    @head <>
      "?" <>
      URI.encode_query(
        Map.merge(Map.from_struct(target.scope), %{
          platform: target.platform,
          runtime_fingerprint: target.runtime_sha256,
          channel: target.channel
        })
      )
  end

  defp string_keys(map), do: Map.new(map, fn {key, value} -> {Atom.to_string(key), value} end)
end
