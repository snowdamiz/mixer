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

    # JSONB normalizes 1e0 to integer 1 before the codec sees it. Its retained
    # decimal scales (1.0, 7.00) remain distinguishable and must fail closed.
    for json <- ["1.0", "[2, 3.0]", "{\"x\": 7.00}"] do
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

  test "exact runtime identity grants FORCE RLS and function closures have executable negative controls" do
    assert [["storage_runtime", "storage_runtime", false, false, false, false, false]] =
             F.rt(
               "SELECT current_user,session_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication FROM pg_catalog.pg_roles WHERE rolname=current_user"
             ).rows

    assert [[4, true]] =
             F.sql(
               "SELECT count(*),bool_and(relrowsecurity AND relforcerowsecurity) FROM pg_catalog.pg_class WHERE relname=ANY($1::text[])",
               [Schema.tables()]
             ).rows

    assert {:ok, _} = F.upload()
    for table <- Schema.tables(), do: assert(F.rt("SELECT * FROM public.#{table}").rows == [])

    for query <- [
          "UPDATE public.mixer_customer_artifacts SET envelope_bytes=envelope_bytes",
          "DELETE FROM public.mixer_customer_audit_events",
          "TRUNCATE public.mixer_customer_idempotency",
          "UPDATE public.mixer_customer_artifact_heads SET organization_id='elsewhere'",
          "INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'',repeat('a',64))",
          "UPDATE public.mixer_authz_memberships SET role='owner'",
          "SELECT public.mixer_customer_cbor('[]'::jsonb)",
          "SELECT public.mixer_customer_event_identity('{}'::jsonb)",
          "SET ROLE storage_owner",
          "CREATE TABLE public.review_injected(id int)"
        ] do
      assert_raise Postgrex.Error, fn -> F.rt(query) end
    end

    assert [[1, 1, 1, 1]] = F.counts()
  end

  test "topology rejects every independently perturbed boundary and accepts restoration" do
    controls = [
      {"ALTER TABLE public.mixer_customer_artifacts NO FORCE ROW LEVEL SECURITY",
       ["ALTER TABLE public.mixer_customer_artifacts FORCE ROW LEVEL SECURITY"]},
      {"GRANT INSERT(organization_id) ON public.mixer_customer_artifact_heads TO storage_runtime",
       [
         "REVOKE INSERT(organization_id) ON public.mixer_customer_artifact_heads FROM storage_runtime"
       ]},
      {"GRANT UPDATE(payload) ON public.mixer_customer_artifacts TO storage_runtime",
       ["REVOKE UPDATE(payload) ON public.mixer_customer_artifacts FROM storage_runtime"]},
      {"GRANT SELECT(payload) ON public.mixer_customer_artifacts TO PUBLIC",
       ["REVOKE SELECT(payload) ON public.mixer_customer_artifacts FROM PUBLIC"]},
      {"GRANT UPDATE(role) ON public.mixer_authz_memberships TO storage_runtime",
       ["REVOKE UPDATE(role) ON public.mixer_authz_memberships FROM storage_runtime"]},
      {"GRANT CREATE ON SCHEMA public TO storage_runtime",
       ["REVOKE CREATE ON SCHEMA public FROM storage_runtime"]},
      {"GRANT CREATE ON SCHEMA public TO PUBLIC", ["REVOKE CREATE ON SCHEMA public FROM PUBLIC"]},
      {"ALTER TABLE public.mixer_customer_audit_events DISABLE TRIGGER customer_integrity",
       ["ALTER TABLE public.mixer_customer_audit_events ENABLE TRIGGER customer_integrity"]},
      {"ALTER TABLE public.mixer_customer_artifacts DISABLE TRIGGER customer_immutable",
       ["ALTER TABLE public.mixer_customer_artifacts ENABLE TRIGGER customer_immutable"]},
      {"CREATE POLICY review_open ON public.mixer_customer_idempotency FOR SELECT USING (true)",
       ["DROP POLICY review_open ON public.mixer_customer_idempotency"]},
      {"ALTER FUNCTION public.mixer_customer_artifact_metadata(text) SECURITY INVOKER",
       ["ALTER FUNCTION public.mixer_customer_artifact_metadata(text) SECURITY DEFINER"]},
      {"ALTER FUNCTION public.mixer_customer_key_exists(text) SET search_path=public",
       ["ALTER FUNCTION public.mixer_customer_key_exists(text) SET search_path=pg_catalog"]},
      {"GRANT EXECUTE ON FUNCTION public.mixer_customer_cbor(jsonb) TO storage_runtime",
       ["REVOKE EXECUTE ON FUNCTION public.mixer_customer_cbor(jsonb) FROM storage_runtime"]},
      {"CREATE FUNCTION public.mixer_customer_key_exists(integer) RETURNS boolean LANGUAGE sql IMMUTABLE AS 'SELECT true'",
       ["DROP FUNCTION public.mixer_customer_key_exists(integer)"]},
      {"CREATE FUNCTION public.review_write() RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS 'BEGIN RETURN true; END'",
       ["DROP FUNCTION public.review_write()"]},
      {"CREATE VIEW public.review_view AS SELECT * FROM public.mixer_customer_artifacts",
       ["DROP VIEW public.review_view"]}
    ]

    for {change, undo} <- controls do
      F.sql(change)

      if String.starts_with?(change, "CREATE VIEW"),
        do: F.sql("GRANT UPDATE ON public.review_view TO storage_runtime")

      try do
        assert {:error, :authorization_unavailable} = F.upload(), change
      after
        Enum.each(undo, &F.sql/1)
      end
    end

    F.sql("CREATE ROLE review_bridge NOLOGIN NOINHERIT")
    F.sql("GRANT storage_owner TO review_bridge")
    F.sql("GRANT review_bridge TO storage_runtime")

    try do
      assert {:error, :authorization_unavailable} = F.upload()
    after
      F.sql("REVOKE review_bridge FROM storage_runtime")
      F.sql("DROP ROLE review_bridge")
    end

    assert {:ok, %{status: 201}} = F.upload()
  end

  test "deferred constraints reject partial writes forged retained bytes actor policy projection request and chain" do
    for mode <-
          ~w(artifact_only event_only dedup_only no_artifact no_event no_dedup no_head wrong_payload wrong_signed wrong_signature wrong_manifest wrong_actor wrong_revision wrong_membership broken_predecessor wrong_request projection gap)a do
      result = F.raw(mode)
      IO.inspect(result, label: "independent raw attack #{mode}")
      assert {:error, _} = result, inspect(mode)
      assert [[0, 0, 0, 0]] = F.counts(), inspect(mode)
    end

    assert {:ok, :direct} = F.raw(:valid)
  end

  test "extra artifact cannot borrow another manifest creating event after a valid write" do
    {c, config} = F.data()

    assert {:error, _} =
             F.run(fn ctx ->
               assert {:ok, _} = PostgresStorage.upload(ctx, c, F.command(), config)

               F.rt(
                 "INSERT INTO public.mixer_customer_artifacts SELECT organization_id,project_id,application_id,environment_id,platform,runtime_sha256,repeat('a',64),payload_sha256,envelope_sha256,envelope_bytes,signed_manifest_bytes,canonical_manifest_cbor,signature,payload,creating_sequence FROM public.mixer_customer_artifacts"
               )

               {:ok, :extra}
             end)

    assert [[0, 0, 0, 0]] = F.counts()
  end

  test "retry identity is exact principal and request while format-only new keys preserve original bytes" do
    {c, config} = F.data()
    assert {:ok, %{status: 201, event_sequence: 1}} = F.upload()
    original = F.sql("SELECT * FROM public.mixer_customer_artifacts").rows
    other = F.identity(%{subject: "review-other-subject", credential_ref: "review-other-token"})
    assert {:error, :idempotency_conflict} = F.upload("review-key", "independent review", other)
    assert {:error, :idempotency_conflict} = F.upload("review-key", "changed")

    F.sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('review-profile',1,'review-fresh','review-person','review-family',true,0,NULL,8)"
    )

    assert {:ok, %{status: 201, event_sequence: 1}} =
             F.upload(
               "review-key",
               "independent review",
               F.identity(%{credential_ref: "review-fresh"})
             )

    {:ok, formatted} =
      MixerHosted.Protocol.ArtifactAdmission.admit(
        c.envelope_bytes <> " \n",
        config.host,
        config.roots,
        F.now()
      )

    assert {:error, :idempotency_conflict} =
             F.run(fn ctx -> PostgresStorage.upload(ctx, formatted, F.command(), config) end)

    assert {:ok, %{status: 200, event_sequence: 2}} =
             F.run(
               fn ctx -> PostgresStorage.upload(ctx, formatted, F.command("second"), config) end,
               other
             )

    assert original == F.sql("SELECT * FROM public.mixer_customer_artifacts").rows

    assert [["review-person"], ["review-other"]] =
             F.sql(
               "SELECT display->'actor'->>0 FROM public.mixer_customer_audit_events ORDER BY sequence"
             ).rows

    assert [[1, 2, 2, 2]] = F.counts()
  end

  test "concurrent same-key and fresh-key commands serialize without gaps" do
    work = for _ <- 1..3, do: Task.async(fn -> F.upload() end)

    for task <- work,
        do: assert({:ok, %{status: 201, event_sequence: 1}} = Task.await(task, 10_000))

    work = for n <- 1..3, do: Task.async(fn -> F.upload("new-#{n}") end)

    sequences =
      Enum.map(work, fn task ->
        assert {:ok, %{status: 200, event_sequence: n}} = Task.await(task, 10_000)
        n
      end)

    assert Enum.sort(sequences) == [2, 3, 4]
    assert [[1, 4, 4, 4]] = F.counts()
    assert {:ok, %{events: events, next_after_sequence: 4}} = F.audit()
    assert Enum.map(events, & &1["sequence"]) == [1, 2, 3, 4]
  end

  test "metadata helper returns the eight-column projection and denies malformed authority without exposing bytes" do
    {c, _} = F.data()
    assert {:ok, _} = F.upload()

    assert {:ok, :metadata_test} =
             F.run(fn _ctx ->
               settings =
                 ~w(phase action required_scope application_id environment_id profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id principal_id family_id token_issued_at token_expires_at)

               saved =
                 Map.new(settings, fn k ->
                   [[value]] = F.rt("SELECT current_setting($1,true)", ["mixer.authz." <> k]).rows
                   {k, value}
                 end)

               put = fn k, v ->
                 F.rt("SELECT set_config($1,$2,true)", ["mixer.authz." <> k, v])
               end

               base =
                 Map.merge(saved, %{
                   "phase" => "metadata",
                   "action" => "artifact.read",
                   "required_scope" => "mixer.artifact.read",
                   "application_id" => "",
                   "environment_id" => ""
                 })

               Enum.each(base, fn {k, v} -> put.(k, v) end)

               result =
                 F.rt("SELECT * FROM public.mixer_customer_artifact_metadata($1)", [
                   c.manifest_sha256
                 ])

               assert result.columns ==
                        ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 signed_manifest_bytes)

               assert [["org-a", "project-a", "fieldlog", "development", _, _, _, signed]] =
                        result.rows

               assert signed == c.signed_manifest_bytes

               assert F.rt("SELECT envelope_bytes,payload FROM public.mixer_customer_artifacts").rows ==
                        []

               for {field, invalid} <- [
                     {"phase", "effect"},
                     {"action", "audit.read"},
                     {"required_scope", "mixer.artifact.upload"},
                     {"application_id", "fieldlog"},
                     {"environment_id", "development"},
                     {"profile_id", "foreign"},
                     {"issuer", "foreign"},
                     {"subject", "foreign"},
                     {"credential_ref", "foreign"},
                     {"principal_id", "review-other"},
                     {"family_id", "review-other-family"},
                     {"token_expires_at", Integer.to_string(F.now())},
                     {"token_issued_at", "01"},
                     {"project_id", "foreign"}
                   ] do
                 put.(field, invalid)

                 assert F.rt("SELECT * FROM public.mixer_customer_artifact_metadata($1)", [
                          c.manifest_sha256
                        ]).rows == [],
                        field

                 assert F.rt("SELECT envelope_bytes,payload FROM public.mixer_customer_artifacts").rows ==
                          [],
                        field

                 put.(field, base[field])
               end

               Enum.each(saved, fn {k, v} -> put.(k, v) end)
               {:ok, :metadata_test}
             end)
  end

  test "future principal start denies both metadata helper and direct runtime visibility" do
    {c, _} = F.data()
    assert {:ok, _} = F.upload()

    {:ok, settings} =
      F.run(fn _ ->
        keys =
          ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action token_issued_at token_expires_at required_scope phase)

        {:ok,
         Map.new(keys, fn k ->
           [[v]] = F.rt("SELECT current_setting($1,true)", ["mixer.authz." <> k]).rows
           {k, v}
         end)}
      end)

    F.sql(
      "UPDATE public.mixer_authz_principals SET not_before=$1,revision=revision+1 WHERE id='review-person'",
      [F.now() + 15]
    )

    assert {:ok, :denied} =
             Runtime.transaction(fn ->
               settings = Map.put(settings, "token_issued_at", Integer.to_string(F.now() + 20))

               Enum.each(settings, fn {k, v} ->
                 F.rt("SELECT set_config($1,$2,true)", ["mixer.authz." <> k, v])
               end)

               assert F.rt("SELECT envelope_bytes,payload FROM public.mixer_customer_artifacts").rows ==
                        []

               for {k, v} <- %{
                     "phase" => "metadata",
                     "action" => "artifact.read",
                     "required_scope" => "mixer.artifact.read",
                     "application_id" => "",
                     "environment_id" => ""
                   },
                   do: F.rt("SELECT set_config($1,$2,true)", ["mixer.authz." <> k, v])

               assert F.rt("SELECT * FROM public.mixer_customer_artifact_metadata($1)", [
                        c.manifest_sha256
                      ]).rows == []

               {:ok, :denied}
             end)
             |> then(fn {:ok, {:ok, x}} -> {:ok, x} end)
  end

  test "SQL codec agrees with known CBOR bytes and independent Elixir encoder at every bound" do
    for {value, hex} <- [
          {0, "00"},
          {23, "17"},
          {24, "1818"},
          {256, "190100"},
          {4_294_967_296, "1b0000000100000000"},
          {18_446_744_073_709_551_615, "1bffffffffffffffff"},
          {false, "f4"},
          {true, "f5"},
          {"é", "62c3a9"},
          {%{"aa" => 1, "b" => 2}, "a261620262616101"}
        ] do
      {:ok, expected} = ArtifactCBOR.encode(value)
      assert expected == Base.decode16!(hex, case: :mixed)
      assert [[^expected]] = F.sql("SELECT public.mixer_customer_cbor($1::jsonb)", [value]).rows
    end

    exact_items = List.duplicate(List.duplicate(1, 255), 15) ++ [List.duplicate(1, 254)]

    for value <- [
          exact_items,
          String.duplicate("x", 65_533),
          Enum.reduce(1..16, 0, fn _, acc -> [acc] end),
          Map.new(1..256, &{Integer.to_string(&1), &1})
        ] do
      {:ok, expected} = ArtifactCBOR.encode(value)
      assert [[^expected]] = F.sql("SELECT public.mixer_customer_cbor($1::jsonb)", [value]).rows
    end

    for value <- [
          nil,
          -1,
          0.5,
          18_446_744_073_709_551_616,
          List.duplicate(1, 257),
          List.duplicate(List.duplicate(1, 255), 16),
          String.duplicate("x", 65_534),
          Enum.reduce(1..17, 0, fn _, acc -> [acc] end),
          Map.new(1..257, &{Integer.to_string(&1), &1})
        ] do
      assert {:error, _} = ArtifactCBOR.encode(value)

      assert_raise Postgrex.Error, fn ->
        F.sql("SELECT public.mixer_customer_cbor($1::jsonb)", [value])
      end
    end
  end

  test "callback errors exceptions and caught storage failure latch roll back successful earlier writes" do
    {c, config} = F.data()

    for mode <- [:error, :raise, :caught] do
      assert {:error, _} =
               F.run(fn ctx ->
                 assert {:ok, _} = PostgresStorage.upload(ctx, c, F.command(), config)

                 case mode do
                   :error ->
                     {:error, :storage_unavailable}

                   :raise ->
                     raise "independent callback abort"

                   :caught ->
                     try do
                       PostgresStorage.upload(ctx, c, %{F.command() | key: ""}, config)
                     catch
                       _, _ -> :caught
                     end

                     {:ok, :caught}
                 end
               end)

      assert [[0, 0, 0, 0]] = F.counts(), inspect(mode)
    end

    assert {:error, :authorization_unavailable} =
             F.run(fn ctx ->
               assert {:ok, _} = PostgresStorage.upload(ctx, c, F.command(), config)
               F.sql("GRANT SELECT ON public.mixer_customer_artifacts TO PUBLIC")

               try do
                 try do
                   PostgresStorage.check_topology!(Runtime)
                 catch
                   _, _ -> :caught
                 end
               after
                 F.sql("REVOKE SELECT ON public.mixer_customer_artifacts FROM PUBLIC")
               end

               {:ok, :caught_topology}
             end)

    assert [[0, 0, 0, 0]] = F.counts()
  end

  test "current time and trust are checked after a measured domain head wait before retry return" do
    {c, config} = F.data()
    assert {:ok, _} = F.upload()

    for expiry <- [:token, :root] do
      Process.sleep(
        Integer.mod(780 - Integer.mod(System.system_time(:millisecond), 1_000), 1_000)
      )

      parent = self()

      holder =
        Task.async(fn ->
          Admin.transaction(fn ->
            F.sql("SELECT 1 FROM public.mixer_customer_artifact_heads FOR UPDATE")
            send(parent, :review_head_locked)
            Process.sleep(340)
          end)
        end)

      assert_receive :review_head_locked
      now = F.now()
      who = if expiry == :token, do: F.identity(%{expires_at: now + 1}), else: F.identity()

      trust =
        if expiry == :root,
          do: %{config | roots: Enum.map(config.roots, &Map.put(&1, "not_after_unix", now + 1))},
          else: config

      started = System.monotonic_time(:millisecond)
      result = F.run(fn ctx -> PostgresStorage.upload(ctx, c, F.command(), trust) end, who)
      elapsed = System.monotonic_time(:millisecond) - started
      IO.inspect(%{mode: expiry, elapsed_ms: elapsed, result: result}, label: "review head wait")
      assert {:error, reason} = result
      assert reason in [:unauthenticated, :storage_unavailable]
      assert elapsed >= 200
      Task.await(holder)
      assert [[1, 1, 1, 1]] = F.counts()
    end
  end

  test "revocation waits for admitted upload then fences cached upload and reads" do
    {c, config} = F.data()
    parent = self()

    admitted =
      Task.async(fn ->
        F.run(fn ctx ->
          result = PostgresStorage.upload(ctx, c, F.command(), config)
          send(parent, :review_admitted)

          receive do
            :commit -> result
          after
            2_000 -> {:error, :storage_unavailable}
          end
        end)
      end)

    assert_receive :review_admitted, 1_000

    revoker =
      Task.async(fn ->
        Admin.transaction(fn ->
          for {table, predicate} <- [
                {"profiles", "id='review-profile'"},
                {"principals", "id='review-person'"},
                {"families", "id='review-family'"},
                {"credentials", "reference='review-token'"},
                {"organization_heads", "organization_id='org-a'"},
                {"project_heads", "organization_id='org-a' AND project_id='project-a'"}
              ],
              do: F.sql("SELECT 1 FROM public.mixer_authz_#{table} WHERE #{predicate} FOR UPDATE")

          F.sql(
            "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='review-token'"
          )
        end)
      end)

    assert Task.yield(revoker, 50) == nil
    send(admitted.pid, :commit)
    assert {:ok, %{status: 201}} = Task.await(admitted)
    assert {:ok, _} = Task.await(revoker)
    assert {:error, :unauthenticated} = F.upload()
    assert {:error, :unauthenticated} = F.read()
  end

  test "private reads audit pages and retained row corruption fail closed" do
    {c, config} = F.data()
    assert {:ok, _} = F.upload()
    assert {:ok, %{status: 200}} = F.upload("second")
    assert {:ok, %{events: [_], next_after_sequence: 2}} = F.audit(1, 1)
    assert {:ok, %{events: [], next_after_sequence: 99}} = F.audit(99, 1)
    assert {:error, :invalid_request} = F.audit(0, 101)
    F.sql("ALTER TABLE public.mixer_customer_artifacts DISABLE TRIGGER customer_immutable")
    F.sql("ALTER TABLE public.mixer_customer_artifacts DISABLE TRIGGER customer_integrity")
    F.sql("UPDATE public.mixer_customer_artifacts SET payload=payload||decode('00','hex')")
    F.sql("ALTER TABLE public.mixer_customer_artifacts ENABLE TRIGGER customer_immutable")
    F.sql("ALTER TABLE public.mixer_customer_artifacts ENABLE TRIGGER customer_integrity")
    assert {:error, :storage_unavailable} = F.read()
    F.sql("ALTER TABLE public.mixer_customer_audit_events DISABLE TRIGGER customer_immutable")
    F.sql("ALTER TABLE public.mixer_customer_audit_events DISABLE TRIGGER customer_integrity")

    F.sql(
      "UPDATE public.mixer_customer_audit_events SET event_cbor=decode('80','hex') WHERE sequence=1"
    )

    F.sql("ALTER TABLE public.mixer_customer_audit_events ENABLE TRIGGER customer_immutable")
    F.sql("ALTER TABLE public.mixer_customer_audit_events ENABLE TRIGGER customer_integrity")
    assert {:error, :storage_unavailable} = F.audit(1, 1)

    assert {:error, :storage_unavailable} =
             F.run(
               fn ctx -> PostgresStorage.read(ctx, c.manifest_sha256, config) end,
               F.identity(),
               "artifact.read"
             )
  end

  test "benign pgordinary membership passes while predefined inheritance and disguised temp namespace fail" do
    F.sql("CREATE ROLE pgordinary_review NOLOGIN")
    F.sql("GRANT pgordinary_review TO storage_runtime")

    try do
      assert {:ok, _} = F.upload()
    after
      F.sql("REVOKE pgordinary_review FROM storage_runtime")
      F.sql("DROP ROLE pgordinary_review")
    end

    F.sql("CREATE ROLE review_pg_bridge NOLOGIN NOINHERIT")
    F.sql("GRANT pg_monitor TO review_pg_bridge")
    F.sql("GRANT review_pg_bridge TO storage_runtime")

    try do
      assert {:error, :authorization_unavailable} = F.upload()
    after
      F.sql("REVOKE review_pg_bridge FROM storage_runtime")
      F.sql("DROP ROLE review_pg_bridge")
    end

    F.sql("CREATE SCHEMA pgxtempyreview")
    F.sql("GRANT USAGE ON SCHEMA pgxtempyreview TO storage_runtime")

    F.sql(
      "CREATE FUNCTION pgxtempyreview.review_extra() RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS 'BEGIN RETURN true; END'"
    )

    try do
      assert {:error, :authorization_unavailable} = F.upload()
    after
      F.sql("DROP SCHEMA pgxtempyreview CASCADE")
    end

    assert {:ok, _} = F.upload()
  end

  test "function body exactness and creating event FK cannot be substituted" do
    [[original]] =
      F.sql(
        "SELECT pg_catalog.pg_get_functiondef('public.mixer_customer_key_exists(text)'::regprocedure)"
      ).rows

    F.sql(
      "CREATE OR REPLACE FUNCTION public.mixer_customer_key_exists(candidate text) RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS 'BEGIN RETURN true; END'"
    )

    try do
      assert {:error, :authorization_unavailable} = F.upload()
    after
      F.sql(original)
    end

    [[constraint]] =
      F.sql(
        "SELECT pg_catalog.pg_get_constraintdef(oid) FROM pg_catalog.pg_constraint WHERE conname='mixer_customer_artifacts_creating_event'"
      ).rows

    F.sql(
      "ALTER TABLE public.mixer_customer_artifacts DROP CONSTRAINT mixer_customer_artifacts_creating_event"
    )

    try do
      assert {:error, :authorization_unavailable} = F.upload()
    after
      F.sql(
        "ALTER TABLE public.mixer_customer_artifacts ADD CONSTRAINT mixer_customer_artifacts_creating_event " <>
          constraint
      )
    end

    assert {:ok, _} = F.upload()
  end

  test "missing audit predecessor fails closed despite unchanged topology" do
    assert {:ok, _} = F.upload()
    assert {:ok, _} = F.upload("second")

    assert {:ok, _} =
             Admin.transaction(fn ->
               F.sql("SET LOCAL session_replication_role=replica")
               F.sql("DELETE FROM public.mixer_customer_audit_events WHERE sequence=1")
             end)

    assert {:error, :storage_unavailable} = F.audit(1, 1)
    assert {:error, :storage_unavailable} = F.audit(0, 100)
  end

  test "forged Checked fields foreign process and escaped contexts confer no storage authority" do
    {c, config} = F.data()

    for field <- Map.keys(Map.from_struct(c)) do
      assert {:error, _} =
               F.run(fn ctx ->
                 PostgresStorage.upload(ctx, Map.put(c, field, nil), F.command(), config)
               end)

      assert [[0, 0, 0, 0]] = F.counts()
    end

    parent = self()

    assert {:ok, _} =
             F.run(fn ctx ->
               send(parent, {:escaped_context, ctx})

               child =
                 Task.async(fn ->
                   try do
                     PostgresStorage.upload(ctx, c, F.command(), config)
                   rescue
                     _ in MixerHosted.Authorization.Transaction.Context.Invalid -> :invalid
                   end
                 end)

               assert :invalid = Task.await(child)
               PostgresStorage.upload(ctx, c, F.command(), config)
             end)

    assert_receive {:escaped_context, ctx}

    assert_raise MixerHosted.Authorization.Transaction.Context.Invalid, fn ->
      PostgresStorage.read(ctx, c.manifest_sha256, config)
    end

    assert [[1, 1, 1, 1]] = F.counts()
  end

  test "an admitted private read holds revocation locks until return and later reads are denied" do
    assert {:ok, _} = F.upload()
    {c, config} = F.data()
    parent = self()

    reader =
      Task.async(fn ->
        F.run(
          fn ctx ->
            result = PostgresStorage.read(ctx, c.manifest_sha256, config)
            send(parent, :review_read_admitted)

            receive do
              :return -> result
            after
              2_000 -> {:error, :storage_unavailable}
            end
          end,
          F.identity(),
          "artifact.read"
        )
      end)

    assert_receive :review_read_admitted, 1_000

    revoke =
      Task.async(fn ->
        Admin.transaction(fn ->
          for {table, predicate} <- [
                {"profiles", "id='review-profile'"},
                {"principals", "id='review-person'"},
                {"families", "id='review-family'"},
                {"credentials", "reference='review-token'"},
                {"organization_heads", "organization_id='org-a'"},
                {"project_heads", "organization_id='org-a' AND project_id='project-a'"}
              ],
              do: F.sql("SELECT 1 FROM public.mixer_authz_#{table} WHERE #{predicate} FOR UPDATE")

          F.sql(
            "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='review-token'"
          )
        end)
      end)

    assert Task.yield(revoke, 50) == nil
    send(reader.pid, :return)
    assert {:ok, %{envelope_bytes: bytes}} = Task.await(reader)
    assert bytes == c.envelope_bytes
    assert {:ok, _} = Task.await(revoke)
    assert {:error, :unauthenticated} = F.read()
  end
end
