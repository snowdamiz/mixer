defmodule ArtifactStorageReview.Admin do
  use Ecto.Repo, otp_app: :artifact_storage_review, adapter: Ecto.Adapters.Postgres
end

defmodule ArtifactStorageReview.Migration do
  use Ecto.Repo, otp_app: :artifact_storage_review, adapter: Ecto.Adapters.Postgres
end

defmodule ArtifactStorageReview.Runtime do
  use Ecto.Repo, otp_app: :artifact_storage_review, adapter: Ecto.Adapters.Postgres
end

defmodule ArtifactStorageReview.Fixture do
  alias ArtifactStorageReview.{Admin, Runtime}
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.CustomerArtifacts.PostgresStorage, as: Store
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR}
  alias MixerHosted.Audit.CustomerArtifactEvent, as: Event
  def sql(query, args \\ []), do: Ecto.Adapters.SQL.query!(Admin, query, args, log: false)
  def rt(query, args \\ []), do: Ecto.Adapters.SQL.query!(Runtime, query, args, log: false)
  def now, do: System.system_time(:second)
  def sha(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  def identity(changes \\ %{}) do
    struct!(
      VerifiedIdentity,
      Map.merge(
        %{
          profile_id: "review-profile",
          profile_version: 1,
          issuer: "https://review.example",
          subject: "review-subject",
          client_id: "review-client",
          credential_ref: "review-token",
          issued_at: now() - 10,
          expires_at: now() + 600,
          identity_class: :human,
          scopes: ~w(mixer.artifact.upload mixer.artifact.read mixer.audit.read)
        },
        changes
      )
    )
  end

  def target,
    do: %Scope{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "fieldlog",
      environment_id: "development"
    }

  def project, do: %{target() | application_id: nil, environment_id: nil}

  def data do
    fixture =
      File.read!(Path.join(File.cwd!(), "services/protocol/testdata/signed-release-v3.json"))
      |> Jason.decode!()

    config = %{
      repo: Runtime,
      host: fixture["host"],
      roots:
        Enum.map(fixture["roots"], &Map.update!(&1, "public_key", fn b -> Base.decode64!(b) end))
    }

    bytes = Jason.encode!(Map.take(fixture, ~w(signed_manifest payload)))
    {:ok, checked} = ArtifactAdmission.admit(bytes, config.host, config.roots, now())
    {checked, config}
  end

  def command(key \\ "review-key", reason \\ "independent review"),
    do: %{key: key, reason: reason, source_ip: nil}

  def run(fun, identity \\ identity(), action \\ "artifact.upload", target \\ target()),
    do: Authorization.with_authorized_transaction(identity, action, target, fun, Runtime)

  def upload(key \\ "review-key", reason \\ "independent review", who \\ identity()) do
    {checked, config} = data()
    run(fn ctx -> Store.upload(ctx, checked, command(key, reason), config) end, who)
  end

  def read(who \\ identity()) do
    {checked, config} = data()
    run(fn ctx -> Store.read(ctx, checked.manifest_sha256, config) end, who, "artifact.read")
  end

  def audit(after_sequence \\ 0, limit \\ 100) do
    {_, config} = data()

    run(
      fn ctx -> Store.audit(ctx, after_sequence, limit, config) end,
      identity(),
      "audit.read",
      project()
    )
  end

  def seed! do
    sql(
      "TRUNCATE public.mixer_customer_idempotency,public.mixer_customer_audit_events,public.mixer_customer_artifacts,public.mixer_customer_artifact_heads,public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_organizations CASCADE"
    )

    for query <- [
          "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('review-profile',1,'https://review.example','review-client','human',true)",
          "INSERT INTO public.mixer_authz_principals VALUES ('review-person','human',true,0,2),('review-other','human',true,0,2)",
          "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('review-profile',1,'review-subject','human','review-person',true),('review-profile',1,'review-other-subject','human','review-other',true)",
          "INSERT INTO public.mixer_authz_families VALUES ('review-family','review-profile',1,'review-person',true,0,NULL,3),('review-other-family','review-profile',1,'review-other',true,0,NULL,3)",
          "INSERT INTO public.mixer_authz_credentials VALUES ('review-profile',1,'review-token','review-person','review-family',true,0,NULL,4),('review-profile',1,'review-other-token','review-other','review-other-family',true,0,NULL,4)",
          "INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true)",
          "INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true)",
          "INSERT INTO public.mixer_authz_applications VALUES ('org-a','project-a','fieldlog',true)",
          "INSERT INTO public.mixer_authz_environments VALUES ('org-a','project-a','fieldlog','development',true)",
          "INSERT INTO public.mixer_authz_organization_heads VALUES ('org-a',5)",
          "INSERT INTO public.mixer_authz_project_heads VALUES ('org-a','project-a',6)",
          "INSERT INTO public.mixer_authz_memberships VALUES ('review-member','review-person','org-a','project-a','exact_project','developer',true,0,NULL,7),('review-other-member','review-other','org-a','project-a','exact_project','developer',true,0,NULL,7)"
        ],
        do: sql(query)

    {:ok, genesis} = Event.genesis("org-a", "project-a")

    sql("INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',$1)", [
      genesis
    ])
  end

  def counts,
    do:
      sql(
        "SELECT (SELECT count(*) FROM public.mixer_customer_artifacts),(SELECT count(*) FROM public.mixer_customer_audit_events),(SELECT count(*) FROM public.mixer_customer_idempotency),(SELECT sequence FROM public.mixer_customer_artifact_heads)"
      ).rows

  def insert(table, columns, values),
    do:
      rt(
        "INSERT INTO public.#{table}(#{Enum.join(columns, ",")}) VALUES(#{Enum.map_join(1..length(columns), ",", &"$#{&1}")})",
        values
      )

  # Construct a complete direct-SQL write and change exactly one invariant. The
  # independent test owns assembly and comparison; product Event only creates
  # the starting valid projection so attacks have a valid positive control.
  def raw(mode) do
    {c, _} = data()

    run(fn ctx ->
      [[n, previous_event, previous_state]] =
        rt(
          "SELECT sequence,event_sha256,state_sha256 FROM public.mixer_customer_artifact_heads FOR UPDATE"
        ).rows

      fresh = Context.checkpoint!(ctx, Runtime, "artifact.upload", target())

      artifact = %{
        organization_id: "org-a",
        project_id: "project-a",
        application_id: "fieldlog",
        environment_id: "development",
        platform: c.target["platform"],
        runtime_sha256: c.target["runtime"],
        manifest_sha256: c.manifest_sha256,
        payload_sha256: c.payload_sha256,
        envelope_sha256: sha(c.envelope_bytes)
      }

      {:ok, event} =
        Event.build(ctx.identity, ctx.snapshot, fresh, artifact, %{
          sequence: n + 1,
          previous_state_sha256: previous_state,
          previous_event_sha256: previous_event,
          outcome: "created",
          reason: "direct review",
          source_ip: nil
        })

      display =
        case mode do
          :string_schema ->
            Map.put(event.display, "audit_schema", "2")

          :wrong_actor ->
            put_in(event.display, ["actor", Access.at(8)], String.duplicate("b", 64))

          :wrong_revision ->
            put_in(event.display, ["authorization", Access.at(3), Access.at(0)], 999)

          :wrong_membership ->
            put_in(
              event.display,
              ["authorization", Access.at(10), Access.at(0), Access.at(1)],
              "owner"
            )

          :broken_predecessor ->
            Map.put(event.display, "previous_event_sha256", String.duplicate("c", 64))

          :wrong_request ->
            Map.put(event.display, "request_sha256", String.duplicate("d", 64))

          _ ->
            event.display
        end

      fields =
        ~w(audit_schema sequence tenant actor authorization target action outcome reason request_id source_ip recorded_at previous_state_sha256 current_state_sha256 previous_event_sha256 request_sha256 envelope_sha256)

      {:ok, cbor} = ArtifactCBOR.encode(Enum.map(fields, &Map.fetch!(display, &1)))
      digest = sha("mixer.hosted.customer.audit.v2\0" <> cbor)
      display = Map.put(display, "event_sha256", digest)

      bytes = [
        "org-a",
        "project-a",
        "fieldlog",
        "development",
        c.target["platform"],
        c.target["runtime"],
        c.manifest_sha256,
        c.payload_sha256,
        sha(c.envelope_bytes),
        c.envelope_bytes,
        c.signed_manifest_bytes,
        c.canonical_manifest_cbor,
        c.signature,
        c.payload,
        n + 1
      ]

      bytes =
        case mode do
          :wrong_payload -> List.update_at(bytes, 13, &(&1 <> "bad"))
          :wrong_signed -> List.update_at(bytes, 10, &(&1 <> " "))
          :wrong_signature -> List.replace_at(bytes, 12, <<0::512>>)
          :wrong_manifest -> List.replace_at(bytes, 6, String.duplicate("b", 64))
          _ -> bytes
        end

      unless mode in [:no_artifact, :event_only, :dedup_only],
        do:
          insert(
            "mixer_customer_artifacts",
            ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 payload_sha256 envelope_sha256 envelope_bytes signed_manifest_bytes canonical_manifest_cbor signature payload creating_sequence),
            bytes
          )

      unless mode in [:no_event, :artifact_only, :dedup_only],
        do:
          insert(
            "mixer_customer_audit_events",
            ~w(organization_id project_id sequence manifest_sha256 audit_schema event_cbor event_sha256 previous_event_sha256 previous_state_sha256 current_state_sha256 display),
            [
              "org-a",
              "project-a",
              n + 1,
              c.manifest_sha256,
              2,
              cbor,
              digest,
              display["previous_event_sha256"],
              previous_state,
              display["current_state_sha256"],
              if(mode == :projection, do: Map.put(display, "reason", "different"), else: display)
            ]
          )

      unless mode in [:no_dedup, :artifact_only, :event_only],
        do:
          insert(
            "mixer_customer_idempotency",
            ~w(organization_id project_id key principal_id action application_id environment_id manifest_sha256 request_sha256 event_sequence status payload_sha256),
            [
              "org-a",
              "project-a",
              "review-raw",
              fresh.principal.id,
              "artifact.upload",
              "fieldlog",
              "development",
              c.manifest_sha256,
              display["request_sha256"],
              n + 1,
              201,
              c.payload_sha256
            ]
          )

      unless mode in [:no_head, :artifact_only, :event_only, :dedup_only],
        do:
          rt(
            "UPDATE public.mixer_customer_artifact_heads SET sequence=$1,event_sha256=$2,state_sha256=$3",
            [if(mode == :gap, do: n + 2, else: n + 1), digest, display["current_state_sha256"]]
          )

      {:ok, :direct}
    end)
  end
end

defmodule ArtifactStorageReview.Test do
  use ExUnit.Case, async: false
  alias ArtifactStorageReview.{Admin, Migration, Runtime}
  alias ArtifactStorageReview.Fixture, as: F
  alias MixerHosted.CustomerArtifacts.{PostgresStorage, Schema, Topology}
  alias MixerHosted.Protocol.ArtifactCBOR

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_ARTIFACT_STORAGE_TEST_PORT")),
      database: "mixer_customer_artifact_storage",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "storage_fixture_admin", pool_size: 5]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "storage_fixture_admin",
           pool_size: 2,
           after_connect: fn c -> Postgrex.query!(c, "SET ROLE storage_owner", []) end
         ]}
    )

    start_supervised!({Runtime, settings ++ [username: "storage_runtime", pool_size: 4]})

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage}
        ],
        do: :ok = Ecto.Migrator.up(Migration, version, module, log: false)

    for t <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{t} TO storage_runtime")

    for t <- ~w(profiles principals families credentials organization_heads project_heads),
        do: F.sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{t}() TO storage_runtime")

    for t <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{t} TO storage_runtime")

    F.sql(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO storage_runtime"
    )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO storage_runtime"
          )

    IO.puts("REVIEW CATALOG " <> Topology.catalog_hash(Admin))
    :ok
  end

  setup do
    F.seed!()
    :ok
  end

  test "closed SQL event schema rejects string discriminator with coherent bytes and hash" do
    result = F.raw(:string_schema)
    IO.inspect(result, label: "string audit_schema direct SQL result")
    assert {:error, _} = result
    assert [[0, 0, 0, 0]] = F.counts()
  end

  test "SQL CBOR numeric grammar agrees with Elixir on integral decimal and exponent rejection" do
    assert {:error, _} = ArtifactCBOR.encode(1.0)

    for json <- ["1.0", "1e0", "[2, 3.0]", "{\"x\": 7.00}"] do
      assert_raise Postgrex.Error, fn ->
        F.sql("SELECT public.mixer_customer_cbor($1::text::jsonb)", [json])
      end
    end
  end

  test "direct SQL positive control is accepted and remains readable through protected API" do
    assert {:ok, :direct} = F.raw(:valid)
    assert [[1, 1, 1, 1]] = F.counts()
    assert {:ok, %{envelope_bytes: bytes}} = F.read()
    assert bytes == elem(F.data(), 0).envelope_bytes
    assert {:ok, %{events: [_], next_after_sequence: 1}} = F.audit()
  end
end
