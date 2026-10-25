defmodule MixerHosted.CustomerArtifacts.RouteBindingReviewRepo do
  def in_transaction? do
    send(self(), {:route_binding_review_repo, :in_transaction})
    false
  end

  def transaction(_callback, _options) do
    send(self(), {:route_binding_review_repo, :transaction})
    {:error, :storage_unavailable}
  end

  def rollback(reason) do
    send(self(), {:route_binding_review_repo, :rollback})
    throw({:unexpected_review_rollback, reason})
  end
end

defmodule MixerHosted.CustomerArtifacts.FacadeFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_artifact_facade_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifacts.FacadeFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_artifact_facade_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifacts.FacadeFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_artifact_facade_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifacts.FacadeFixture do
  alias MixerHosted.CustomerArtifacts.FacadeFixture.{Admin, Runtime}
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactAdmission
  def sql(sql, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, sql, params, log: false)

  def runtime_sql(sql, params \\ []),
    do: Ecto.Adapters.SQL.query!(Runtime, sql, params, log: false)

  def now, do: System.system_time(:second)

  def identity(changes \\ %{}),
    do:
      struct!(
        VerifiedIdentity,
        Map.merge(
          %{
            profile_id: "profile",
            profile_version: 1,
            issuer: "https: //issuer.example",
            subject: "subject",
            client_id: "client",
            credential_ref: "token",
            issued_at: now() - 20,
            expires_at: now() + 600,
            identity_class: :human,
            scopes: ~w(mixer.artifact.upload mixer.artifact.read mixer.audit.read)
          },
          changes
        )
      )

  def target,
    do: %Scope{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "fieldlog",
      environment_id: "development"
    }

  def project, do: %{target() | application_id: nil, environment_id: nil}

  def data do
    f =
      Path.expand("../../../services/protocol/testdata/signed-release-v3.json", __DIR__)
      |> File.read!()
      |> Jason.decode!()

    roots = Enum.map(f["roots"], &Map.update!(&1, "public_key", fn v -> Base.decode64!(v) end))
    bytes = Jason.encode!(Map.take(f, ~w(signed_manifest payload)))
    config = %{repo: Runtime, host: f["host"], roots: roots}
    {:ok, checked} = ArtifactAdmission.admit(bytes, config.host, config.roots, now())
    {checked, config}
  end

  def seed! do
    sql(
      "TRUNCATE public.mixer_customer_idempotency,public.mixer_customer_audit_events,public.mixer_customer_artifacts,public.mixer_customer_artifact_heads,public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_organizations CASCADE"
    )

    for query <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https: //issuer.example','client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,2),('other','human',true,0,2)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,'subject','human','person',true),('profile',1,'other-subject','human','other',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,3),('other-family','profile',1,'other',true,0,NULL,3)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'token','person','family',true,0,NULL,4),('profile',1,'other-token','other','other-family',true,0,NULL,4)",
          "INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true)",
          "INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true)",
          "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','fieldlog',true)",
          "INSERT INTO public.mixer_authz_environments VALUES ('org-a','project-a','fieldlog','development',true)",
          "INSERT INTO public.mixer_authz_organization_heads VALUES ('org-a',5)",
          "INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',6)",
          "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org-a','project-a','exact_project','developer',true,0,NULL,7),('other-member','other','org-a','project-a','exact_project','developer',true,0,NULL,7)"
        ],
        do: sql(query)

    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis("org-a", "project-a")

    sql("INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)", [
      genesis
    ])

    :ok
  end

  def counts,
    do:
      sql(
        "SELECT (SELECT count(*) FROM public.mixer_customer_artifacts),(SELECT count(*) FROM public.mixer_customer_audit_events),(SELECT count(*) FROM public.mixer_customer_idempotency),(SELECT sequence FROM public.mixer_customer_artifact_heads)"
      ).rows
end

defmodule MixerHosted.CustomerArtifactsTest do
  use ExUnit.Case, async: false
  @moduletag :customer_artifact_facade_db
  alias MixerHosted.CustomerArtifacts
  alias MixerHosted.CustomerArtifacts.Schema
  alias MixerHosted.CustomerArtifacts.FacadeFixture, as: F
  alias MixerHosted.CustomerArtifacts.FacadeFixture.{Admin, Migration, Runtime}

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_ARTIFACT_FACADE_TEST_PORT")),
      database: "mixer_customer_artifact_facade",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "facade_fixture_admin", pool_size: 4]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "facade_fixture_admin",
           pool_size: 2,
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE facade_owner", []) end
         ]}
    )

    start_supervised!({Runtime, settings ++ [username: "facade_runtime", pool_size: 4]})

    for {version, module, file} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization,
           "20261025000003_add_customer_authorization.exs"},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions,
           "20261025000004_add_authorization_state_revisions.exs"},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage,
           "20261025000005_add_customer_artifact_storage.exs"}
        ] do
      unless Code.ensure_loaded?(module),
        do: Code.require_file(Path.expand("../../priv/repo/migrations/" <> file, __DIR__))

      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    for name <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{name} TO facade_runtime")

    for name <- ~w(profiles principals families credentials organization_heads project_heads),
        do: F.sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{name}() TO facade_runtime")

    for name <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{name} TO facade_runtime")

    F.sql(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO facade_runtime"
    )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO facade_runtime"
          )

    :ok
  end

  setup do
    F.seed!()
    {checked, config} = F.data()
    previous = Application.fetch_env(:mixer_hosted, CustomerArtifacts)
    Application.put_env(:mixer_hosted, CustomerArtifacts, config)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, CustomerArtifacts, value)
        :error -> Application.delete_env(:mixer_hosted, CustomerArtifacts)
      end
    end)

    %{checked: checked, config: config}
  end

  defp route, do: %{organization_id: "org-a", project_id: "project-a"}
  defp metadata, do: %{reason: "upload from customer", source_ip: nil}

  defp upload(checked, key \\ "first", meta \\ metadata(), identity \\ F.identity()),
    do: CustomerArtifacts.upload(identity, route(), key, checked.envelope_bytes, meta)

  defp read(checked, identity \\ F.identity()),
    do: CustomerArtifacts.read(identity, route(), checked.manifest_sha256, metadata())

  defp audit(after_sequence \\ 0, limit \\ 100, identity \\ F.identity()),
    do: CustomerArtifacts.audit(identity, route(), after_sequence, limit, metadata())

  test "digest-addressed upload binds the route before any write or cached receipt", %{
    checked: checked
  } do
    put = fn digest, key ->
      CustomerArtifacts.upload_at(
        F.identity(),
        route(),
        digest,
        key,
        checked.envelope_bytes,
        metadata()
      )
    end

    wrong = String.duplicate("0", 64)
    refute wrong == checked.manifest_sha256
    assert {:error, :digest_mismatch} = put.(wrong, "route-key")
    assert F.counts() == [[0, 0, 0, 0]]
    assert {:ok, %{status: 201} = first} = put.(checked.manifest_sha256, "route-key")
    assert {:ok, ^first} = put.(checked.manifest_sha256, "route-key")
    assert {:error, :digest_mismatch} = put.(wrong, "route-key")
    assert F.counts() == [[1, 1, 1, 1]]
    assert {:ok, %{status: 200, event_sequence: 2}} = put.(checked.manifest_sha256, "new-key")
    assert F.counts() == [[1, 2, 2, 2]]
  end

  test "digest-addressed upload rejects invalid route digests without fallback", %{
    checked: checked
  } do
    for digest <- [nil, :any, "", String.duplicate("A", 64), checked.manifest_sha256 <> "0"] do
      assert {:error, :invalid_request} =
               CustomerArtifacts.upload_at(
                 F.identity(),
                 route(),
                 digest,
                 "route-key",
                 checked.envelope_bytes,
                 metadata()
               )

      assert F.counts() == [[0, 0, 0, 0]]
    end
  end

  test "digest-addressed upload preserves scope admission before artifact classification", %{
    checked: checked
  } do
    denied = F.identity(%{scopes: []})

    assert {:error, :permission_denied} =
             CustomerArtifacts.upload_at(
               denied,
               route(),
               checked.manifest_sha256,
               "route-key",
               "{}",
               metadata()
             )

    assert {:error, :artifact_invalid} =
             CustomerArtifacts.upload_at(
               F.identity(),
               route(),
               checked.manifest_sha256,
               "route-key",
               "{}",
               metadata()
             )

    assert {:error, :invalid_request} =
             CustomerArtifacts.upload(F.identity(), route(), "route-key", "{}", metadata())

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "public composition commits upload then resolves private bytes and exact audit", %{
    checked: checked
  } do
    assert {:ok, receipt} = upload(checked)

    assert receipt == %{
             status: 201,
             manifest_sha256: checked.manifest_sha256,
             payload_sha256: checked.payload_sha256,
             event_sequence: 1
           }

    refute Runtime.in_transaction?()
    assert F.counts() == [[1, 1, 1, 1]]

    assert {:ok, %{envelope_bytes: bytes, manifest_sha256: digest, payload_sha256: payload}} =
             read(checked)

    assert {bytes, digest, payload} ==
             {checked.envelope_bytes, checked.manifest_sha256, checked.payload_sha256}

    assert {:ok, %{events: [event], next_after_sequence: 1}} = audit()
    assert event["target"] |> Enum.take(4) == ["org-a", "project-a", "fieldlog", "development"]
    assert event["reason"] == metadata().reason
    assert event["source_ip"] == []
    assert byte_size(event["request_id"]) == 32
    assert {:ok, _} = Base.decode16(event["request_id"], case: :lower)
    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "same key preserves original receipt while changed reason conflicts", %{checked: checked} do
    assert {:ok, first} = upload(checked)
    assert {:ok, ^first} = upload(checked, "first", %{metadata() | source_ip: "::1"})

    assert {:error, :idempotency_conflict} =
             upload(checked, "first", %{metadata() | reason: "different"})

    assert {:ok, %{events: [event]}} = audit()
    assert event["source_ip"] == []
    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "new key keeps first bytes and creates a separate unchanged event", %{checked: checked} do
    assert {:ok, %{status: 201}} = upload(checked)

    assert {:ok, %{status: 200, event_sequence: 2}} =
             CustomerArtifacts.upload(
               F.identity(),
               route(),
               "second",
               checked.envelope_bytes <> " \n",
               metadata()
             )

    assert {:ok, %{envelope_bytes: bytes}} = read(checked)
    assert bytes == checked.envelope_bytes
    assert {:ok, %{events: [created], next_after_sequence: 1}} = audit(0, 1)
    assert {:ok, %{events: [unchanged], next_after_sequence: 2}} = audit(1, 1)
    assert created["outcome"] == "created" and unchanged["outcome"] == "unchanged"
    assert created["current_state_sha256"] == unchanged["current_state_sha256"]
    assert created["envelope_sha256"] != unchanged["envelope_sha256"]
    assert F.counts() == [[1, 2, 2, 2]]
  end

  test "another principal cannot replay a cached receipt", %{checked: checked} do
    assert {:ok, _} = upload(checked)
    other = F.identity(%{subject: "other-subject", credential_ref: "other-token"})
    assert {:error, :idempotency_conflict} = upload(checked, "first", metadata(), other)

    assert {:ok, %{status: 200, event_sequence: 2}} =
             upload(checked, "other-key", metadata(), other)

    assert {:ok, %{events: [first, second]}} = audit()
    assert hd(first["actor"]) == "person"
    assert hd(second["actor"]) == "other"
  end

  test "viewer can read and audit but cannot upload; billing role cannot read", %{
    checked: checked
  } do
    assert {:ok, _} = upload(checked)
    F.sql("UPDATE public.mixer_authz_memberships SET role='viewer' WHERE id='member'")
    assert {:ok, _} = read(checked)
    assert {:ok, _} = audit()
    assert {:error, :permission_denied} = upload(checked, "viewer")
    F.sql("UPDATE public.mixer_authz_memberships SET role='billing_manager' WHERE id='member'")
    assert {:error, :permission_denied} = read(checked)
    assert {:error, :permission_denied} = audit()
    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "revoked identity and expired membership fence every public operation", %{checked: checked} do
    for mutation <- [
          "UPDATE public.mixer_authz_profiles SET active=false",
          "UPDATE public.mixer_authz_principals SET active=false WHERE id='person'",
          "UPDATE public.mixer_authz_credentials SET active=false WHERE reference='token'",
          "UPDATE public.mixer_authz_families SET active=false WHERE id='family'",
          "UPDATE public.mixer_authz_memberships SET expires_at=1 WHERE id='member'"
        ] do
      F.seed!()
      assert {:ok, _} = upload(checked)
      F.sql(mutation)
      assert {:error, _} = upload(checked)
      assert {:error, _} = read(checked)
      assert {:error, _} = audit()
      assert F.counts() == [[1, 1, 1, 1]]
    end
  end

  test "identity and exact OAuth scopes reject before private body admission", %{checked: checked} do
    assert {:error, :unauthenticated} =
             CustomerArtifacts.upload(nil, route(), "first", :not_bytes, metadata())

    assert {:error, :unauthenticated} =
             upload(checked, "first", metadata(), F.identity(%{expires_at: F.now() - 1}))

    identity = F.identity(%{scopes: ["mixer.artifact.read.extra", "mixer.audit.read.extra"]})

    assert {:error, :permission_denied} =
             CustomerArtifacts.upload(identity, route(), "first", :not_bytes, metadata())

    assert {:error, :permission_denied} = read(checked, identity)
    assert {:error, :permission_denied} = audit(0, 100, identity)
    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "route cannot smuggle app environment actor or server configuration", %{checked: checked} do
    for bad <- [
          nil,
          %{},
          Map.put(route(), :application_id, "fieldlog"),
          Map.put(route(), :environment_id, "development"),
          Map.put(route(), :repo, Runtime),
          Map.put(route(), :actor, "person"),
          %{organization_id: "org-a", project_id: nil}
        ] do
      assert {:error, :invalid_request} =
               CustomerArtifacts.upload(
                 F.identity(),
                 bad,
                 "first",
                 checked.envelope_bytes,
                 metadata()
               )

      assert {:error, :invalid_request} =
               CustomerArtifacts.read(F.identity(), bad, checked.manifest_sha256, metadata())

      assert {:error, :invalid_request} =
               CustomerArtifacts.audit(F.identity(), bad, 0, 100, metadata())
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "unknown or malformed ingress metadata never reaches storage", %{checked: checked} do
    for bad <- [
          %{},
          Map.put(metadata(), :request_id, String.duplicate("a", 32)),
          Map.put(metadata(), :actor, "person"),
          Map.put(metadata(), :roots, []),
          %{metadata() | reason: String.duplicate("é", 257)},
          %{metadata() | reason: <<255>>},
          %{metadata() | source_ip: "127.000.0.1"},
          %{metadata() | source_ip: "2001:DB8::1"},
          %{metadata() | source_ip: "::1%lo0"},
          %{metadata() | source_ip: <<255>>}
        ] do
      assert {:error, :invalid_request} = upload(checked, "first", bad)

      assert {:error, :invalid_request} =
               CustomerArtifacts.read(F.identity(), route(), checked.manifest_sha256, bad)

      assert {:error, :invalid_request} =
               CustomerArtifacts.audit(F.identity(), route(), 0, 100, bad)
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "key and byte boundaries fail closed while exact valid bounds work", %{checked: checked} do
    for bad <- [nil, "", "key/other", "é", String.duplicate("x", 129)] do
      assert {:error, :invalid_request} = upload(checked, bad)
    end

    for bad <- [nil, "{}", <<255>>, :not_bytes, String.duplicate("x", 6_291_457)] do
      assert {:error, :invalid_request} =
               CustomerArtifacts.upload(F.identity(), route(), "first", bad, metadata())
    end

    meta = %{reason: String.duplicate("é", 256), source_ip: "2001:db8::1"}
    assert {:ok, _} = upload(checked, String.duplicate("x", 128), meta)
    assert {:ok, %{events: [event]}} = audit()
    assert event["reason"] == meta.reason and event["source_ip"] == [meta.source_ip]
    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "missing or malformed server configuration fails closed without a public override", %{
    checked: checked,
    config: config
  } do
    Application.delete_env(:mixer_hosted, CustomerArtifacts)
    assert {:error, :storage_unavailable} = upload(checked)

    for bad <- [
          nil,
          %{},
          %{config | repo: nil},
          %{config | repo: String},
          %{config | host: %{}},
          %{config | roots: []},
          Map.put(config, :clock, 1)
        ] do
      Application.put_env(:mixer_hosted, CustomerArtifacts, bad)
      assert {:error, :storage_unavailable} = upload(checked)
      assert {:error, :storage_unavailable} = read(checked)
      assert {:error, :storage_unavailable} = audit()
    end

    Application.put_env(:mixer_hosted, CustomerArtifacts, config)
    assert {:ok, _} = upload(checked)
  end

  test "current revoked roots and different host cannot return stored bytes", %{
    checked: checked,
    config: config
  } do
    assert {:ok, _} = upload(checked)
    revoked = %{config | roots: Enum.map(config.roots, &Map.put(&1, "revoked", true))}
    Application.put_env(:mixer_hosted, CustomerArtifacts, revoked)
    assert {:error, :storage_unavailable} = read(checked)
    assert {:error, :invalid_request} = upload(checked, "second")
    foreign = %{config | host: Map.put(config.host, "runtime", String.duplicate("a", 64))}
    Application.put_env(:mixer_hosted, CustomerArtifacts, foreign)
    assert {:error, :storage_unavailable} = read(checked)
    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "missing and foreign project reads expose no bytes", %{checked: checked} do
    assert {:error, :not_found} = read(checked)
    assert {:ok, _} = upload(checked)
    other = %{route() | project_id: "different"}

    assert {:error, :not_found} =
             CustomerArtifacts.read(F.identity(), other, checked.manifest_sha256, metadata())

    for digest <- [nil, "", String.duplicate("A", 64), String.duplicate("a", 65)] do
      assert {:error, :invalid_request} =
               CustomerArtifacts.read(F.identity(), route(), digest, metadata())
    end
  end

  test "audit cursor bounds and empty pages retain unambiguous continuation", %{checked: checked} do
    assert {:ok, %{events: [], next_after_sequence: 0}} = audit()

    for {after_sequence, limit} <- [
          {-1, 1},
          {9_007_199_254_740_992, 1},
          {0, 0},
          {0, 101},
          {1.0, 1},
          {0, nil}
        ] do
      assert {:error, :invalid_request} = audit(after_sequence, limit)
    end

    assert {:ok, _} = upload(checked)
    assert {:ok, %{events: [], next_after_sequence: 1}} = audit(1, 100)
  end

  test "concurrent same-key public requests commit one artifact event and receipt", %{
    checked: checked
  } do
    tasks = for _ <- 1..3, do: Task.async(fn -> upload(checked) end)
    values = Enum.map(tasks, &Task.await(&1, 15_000))
    assert [{:ok, receipt}] = Enum.uniq(values)
    assert receipt.status == 201 and receipt.event_sequence == 1
    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "independent: mismatched digest stops before every Repo transaction boundary", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    wrong = String.duplicate("f", 64)
    refute wrong == checked.manifest_sha256

    assert {:error, :digest_mismatch} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), wrong, "independent-key", checked.envelope_bytes, metadata()
             )

    refute_received {:route_binding_review_repo, _}

    assert {:error, :storage_unavailable} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert_received {:route_binding_review_repo, :in_transaction}
    assert_received {:route_binding_review_repo, :transaction}
    refute_received {:route_binding_review_repo, :rollback}
    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: structured expected values cannot select the unrestricted upload path", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    for expected <- [
          :any, {:at, checked.manifest_sha256}, {:any}, %{digest: checked.manifest_sha256},
          String.to_charlist(checked.manifest_sha256), 0, false, <<0>>, <<255>>,
          String.duplicate("0", 63), String.duplicate("g", 64)
        ] do
      assert {:error, :invalid_request} =
               CustomerArtifacts.upload_at(
                 F.identity(), route(), expected, "independent-key", checked.envelope_bytes,
                 metadata()
               )

      refute_received {:route_binding_review_repo, _}
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: denied identity and exact scope precede invalid-body classification", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    cases = [
      {nil, :unauthenticated},
      {F.identity(%{expires_at: F.now() - 1}), :unauthenticated},
      {F.identity(%{issued_at: F.now() + 120}), :unauthenticated},
      {F.identity(%{identity_class: :service}), :permission_denied},
      {F.identity(%{scopes: ["mixer.artifact.read"]}), :permission_denied},
      {F.identity(%{scopes: ["mixer.artifact.upload.extra"]}), :permission_denied},
      {F.identity(%{scopes: ["MIXER.ARTIFACT.UPLOAD"]}), :permission_denied}
    ]

    for {identity, error} <- cases do
      assert {:error, ^error} =
               CustomerArtifacts.upload_at(
                 identity, route(), checked.manifest_sha256, "independent-key", :not_bytes,
                 metadata()
               )

      refute_received {:route_binding_review_repo, _}
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: foreign project rejects before invalid-body classification", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    for foreign <- [Map.put(route(), :organization_id, "other"), Map.put(route(), :project_id, "other")] do
      assert {:error, :not_found} =
               CustomerArtifacts.upload_at(
                 F.identity(), foreign, checked.manifest_sha256, "independent-key", :not_bytes,
                 metadata()
               )

      refute_received {:route_binding_review_repo, _}
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: invalid signature stays artifact_invalid even when route also differs", %{
    checked: checked
  } do
    bad =
      checked.envelope_bytes
      |> Jason.decode!()
      |> put_in(["signed_manifest", "signature"], Base.encode64(:binary.copy(<<0>>, 64)))
      |> Jason.encode!()

    for expected <- [checked.manifest_sha256, String.duplicate("f", 64)] do
      assert {:error, :artifact_invalid} =
               CustomerArtifacts.upload_at(
                 F.identity(), route(), expected, "independent-key", bad, metadata()
               )
    end

    assert {:error, :invalid_request} =
             CustomerArtifacts.upload(F.identity(), route(), "independent-key", bad, metadata())

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: cached success never rescues invalid bytes or expected digest", %{
    checked: checked
  } do
    assert {:ok, %{status: 201}} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key",
               checked.envelope_bytes, metadata()
             )

    bad =
      checked.envelope_bytes
      |> Jason.decode!()
      |> put_in(["signed_manifest", "signature"], Base.encode64(:binary.copy(<<0>>, 64)))
      |> Jason.encode!()

    assert {:error, :artifact_invalid} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key", bad, metadata()
             )

    assert {:error, :invalid_request} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), {:at, checked.manifest_sha256}, "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert {:error, :digest_mismatch} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), String.duplicate("f", 64), "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "independent: unrestricted and addressed calls retain the same authorized receipt", %{
    checked: checked
  } do
    assert {:ok, %{status: 201} = first} =
             CustomerArtifacts.upload(
               F.identity(), route(), "independent-key", checked.envelope_bytes, metadata()
             )

    assert {:ok, ^first} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert F.counts() == [[1, 1, 1, 1]]

    assert {:ok, %{status: 200, event_sequence: 2}} =
             CustomerArtifacts.upload(
               F.identity(), route(), "independent-next", checked.envelope_bytes, metadata()
             )

    assert F.counts() == [[1, 2, 2, 2]]
  end

end
