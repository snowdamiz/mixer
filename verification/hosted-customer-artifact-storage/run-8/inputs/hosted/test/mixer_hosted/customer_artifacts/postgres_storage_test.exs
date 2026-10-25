defmodule MixerHosted.CustomerArtifacts.StorageFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_artifact_storage_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifacts.StorageFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_artifact_storage_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifacts.StorageFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_artifact_storage_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerArtifacts.StorageFixture do
  alias MixerHosted.CustomerArtifacts.StorageFixture.{Admin, Runtime}
  alias MixerHosted.CustomerArtifacts.PostgresStorage, as: Store
  alias MixerHosted.Authorization
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
      Path.expand("../../../../services/protocol/testdata/signed-release-v3.json", __DIR__)
      |> File.read!()
      |> Jason.decode!()

    roots = Enum.map(f["roots"], &Map.update!(&1, "public_key", fn v -> Base.decode64!(v) end))
    bytes = Jason.encode!(Map.take(f, ~w(signed_manifest payload)))
    config = %{repo: Runtime, host: f["host"], roots: roots}
    {:ok, checked} = ArtifactAdmission.admit(bytes, config.host, config.roots, now())
    {checked, config}
  end

  def command(key \\ "first", reason \\ "test"),
    do: %{key: key, reason: reason, source_ip: "127.0.0.1"}

  def run(callback, i \\ identity(), a \\ "artifact.upload", t \\ target()),
    do: Authorization.with_authorized_transaction(i, a, t, callback, Runtime)

  def upload(key \\ "first", reason \\ "test", i \\ identity()) do
    {c, config} = data()
    run(fn ctx -> Store.upload(ctx, c, command(key, reason), config) end, i)
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

  def raw(mode) do
    {checked, _} = data()

    run(fn ctx ->
      [[sequence, previous_event, previous_state]] =
        runtime_sql(
          "SELECT sequence,event_sha256,state_sha256 FROM public.mixer_customer_artifact_heads FOR UPDATE"
        ).rows

      fresh =
        MixerHosted.Authorization.Transaction.Context.checkpoint!(
          ctx,
          Runtime,
          "artifact.upload",
          target()
        )

      artifact = %{
        organization_id: "org-a",
        project_id: "project-a",
        application_id: "fieldlog",
        environment_id: "development",
        platform: checked.target["platform"],
        runtime_sha256: checked.target["runtime"],
        manifest_sha256: checked.manifest_sha256,
        payload_sha256: checked.payload_sha256,
        envelope_sha256: sha(checked.envelope_bytes)
      }

      {:ok, event} =
        MixerHosted.Audit.CustomerArtifactEvent.build(
          ctx.identity,
          ctx.snapshot,
          fresh,
          artifact,
          %{
            sequence: sequence + 1,
            previous_state_sha256: previous_state,
            previous_event_sha256: previous_event,
            outcome: "created",
            reason: "raw",
            source_ip: nil
          }
        )

      display =
        case mode do
          :wrong_actor ->
            put_in(event.display, ["actor", Access.at(5)], String.duplicate("a", 64))

          :wrong_authorization ->
            put_in(event.display, ["authorization", Access.at(2), Access.at(0)], 99)

          _ ->
            event.display
        end

      fields =
        ~w(audit_schema sequence tenant actor authorization target action outcome reason request_id source_ip recorded_at previous_state_sha256 current_state_sha256 previous_event_sha256 request_sha256 envelope_sha256)

      {:ok, cbor} =
        MixerHosted.Protocol.ArtifactCBOR.encode(Enum.map(fields, &Map.fetch!(display, &1)))

      event_hash = sha("mixer.hosted.customer.audit.v2\0" <> cbor)
      display = Map.put(display, "event_sha256", event_hash)

      values = [
        "org-a",
        "project-a",
        "fieldlog",
        "development",
        artifact.platform,
        artifact.runtime_sha256,
        artifact.manifest_sha256,
        artifact.payload_sha256,
        artifact.envelope_sha256,
        checked.envelope_bytes,
        checked.signed_manifest_bytes,
        checked.canonical_manifest_cbor,
        checked.signature,
        checked.payload,
        sequence + 1
      ]

      values =
        case mode do
          :wrong_payload -> List.replace_at(values, 13, checked.payload <> "x")
          :wrong_signature -> List.replace_at(values, 12, <<0::512>>)
          :wrong_canonical -> List.replace_at(values, 11, checked.canonical_manifest_cbor <> "x")
          :wrong_signed_bytes -> List.replace_at(values, 10, checked.signed_manifest_bytes <> " ")
          :wrong_envelope -> List.replace_at(values, 9, checked.envelope_bytes <> " ")
          :wrong_manifest_hash -> List.replace_at(values, 6, String.duplicate("a", 64))
          :cross_tenant -> List.replace_at(values, 0, "foreign")
          _ -> values
        end

      unless mode in [:event_only, :dedup_only, :no_artifact] do
        insert(
          "mixer_customer_artifacts",
          ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 payload_sha256 envelope_sha256 envelope_bytes signed_manifest_bytes canonical_manifest_cbor signature payload creating_sequence),
          values
        )
      end

      unless mode in [:artifact_only, :dedup_only, :no_event] do
        insert(
          "mixer_customer_audit_events",
          ~w(organization_id project_id sequence manifest_sha256 audit_schema event_cbor event_sha256 previous_event_sha256 previous_state_sha256 current_state_sha256 display),
          [
            "org-a",
            "project-a",
            sequence + 1,
            artifact.manifest_sha256,
            2,
            if(mode == :wrong_event_cbor, do: <<128>>, else: cbor),
            event_hash,
            if(mode == :broken_predecessor, do: String.duplicate("a", 64), else: previous_event),
            previous_state,
            display["current_state_sha256"],
            if(mode == :wrong_projection,
              do: Map.put(display, "reason", "changed"),
              else: display
            )
          ]
        )
      end

      unless mode in [:artifact_only, :event_only, :no_dedup] do
        insert(
          "mixer_customer_idempotency",
          ~w(organization_id project_id key principal_id action application_id environment_id manifest_sha256 request_sha256 event_sequence status payload_sha256),
          [
            "org-a",
            "project-a",
            "raw",
            fresh.principal.id,
            "artifact.upload",
            "fieldlog",
            "development",
            artifact.manifest_sha256,
            display["request_sha256"],
            sequence + 1,
            201,
            artifact.payload_sha256
          ]
        )
      end

      unless mode in [:artifact_only, :event_only, :dedup_only, :no_head] do
        runtime_sql(
          "UPDATE public.mixer_customer_artifact_heads SET sequence=$1,event_sha256=$2,state_sha256=$3",
          [
            if(mode == :sequence_gap, do: sequence + 2, else: sequence + 1),
            event_hash,
            display["current_state_sha256"]
          ]
        )
      end

      {:ok, :raw}
    end)
  end

  defp insert(table, columns, values),
    do:
      runtime_sql(
        "INSERT INTO public.#{table} (#{Enum.join(columns, ",")}) VALUES (#{Enum.map_join(1..length(columns), ",", &"$#{&1}")})",
        values
      )

  defp sha(b), do: Base.encode16(:crypto.hash(:sha256, b), case: :lower)

  def counts,
    do:
      sql(
        "SELECT (SELECT count(*) FROM public.mixer_customer_artifacts),(SELECT count(*) FROM public.mixer_customer_audit_events),(SELECT count(*) FROM public.mixer_customer_idempotency),(SELECT sequence FROM public.mixer_customer_artifact_heads)"
      ).rows
end

defmodule MixerHosted.CustomerArtifacts.PostgresStorageTest do
  use ExUnit.Case, async: false
  @moduletag :customer_artifact_storage_db
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.CustomerArtifacts.{PostgresStorage, Schema, Topology}
  alias MixerHosted.CustomerArtifacts.StorageFixture, as: F
  alias MixerHosted.CustomerArtifacts.StorageFixture.{Admin, Migration, Runtime}
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR}

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_ARTIFACT_STORAGE_TEST_PORT")),
      database: "mixer_customer_artifact_storage",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "storage_fixture_admin", pool_size: 4]})

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

    for file <-
          ~w(20261025000003_add_customer_authorization.exs 20261025000004_add_authorization_state_revisions.exs 20261025000005_add_customer_artifact_storage.exs) do
      module =
        case file do
          "20261025000003_add_customer_authorization.exs" ->
            MixerHosted.Repo.Migrations.AddCustomerAuthorization

          "20261025000004_add_authorization_state_revisions.exs" ->
            MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions

          _ ->
            MixerHosted.Repo.Migrations.AddCustomerArtifactStorage
        end

      unless Code.ensure_loaded?(module),
        do: Code.require_file(Path.expand("../../../priv/repo/migrations/" <> file, __DIR__))
    end

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage}
        ] do
      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{table} TO storage_runtime")

    for table <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          F.sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO storage_runtime")

    for table <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO storage_runtime")

    F.sql(
      "GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO storage_runtime"
    )

    for name <-
          ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.#{name}(#{Schema.signatures()[name]}) TO storage_runtime"
          )

    IO.puts("STORAGE CATALOG SHA256 " <> Topology.catalog_hash(Admin))
    :ok
  end

  setup do
    F.seed!()
    :ok
  end

  test "create, fresh private read, immutable audit, own retry and new-key unchanged" do
    {c, config} = F.data()
    assert {:ok, %{status: 201, event_sequence: 1}} = F.upload()
    assert [[1, 1, 1, 1]] = F.counts()
    original = F.sql("SELECT * FROM public.mixer_customer_artifacts").rows
    assert {:ok, %{status: 201, event_sequence: 1}} = F.upload()
    assert [[1, 1, 1, 1]] = F.counts()

    {:ok, changed} =
      ArtifactAdmission.admit(c.envelope_bytes <> " ", config.host, config.roots, F.now())

    assert {:ok, %{status: 200, event_sequence: 2}} =
             F.run(fn ctx ->
               PostgresStorage.upload(ctx, changed, F.command("second"), config)
             end)

    assert original == F.sql("SELECT * FROM public.mixer_customer_artifacts").rows
    assert [[1, 2, 2, 2]] = F.counts()

    assert {:ok, %{envelope_bytes: bytes}} =
             F.run(
               fn ctx -> PostgresStorage.read(ctx, c.manifest_sha256, config) end,
               F.identity(),
               "artifact.read"
             )

    assert bytes == c.envelope_bytes

    assert {:ok, %{events: [created, unchanged], next_after_sequence: 2}} =
             F.run(
               fn ctx -> PostgresStorage.audit(ctx, 0, 100, config) end,
               F.identity(),
               "audit.read",
               F.project()
             )

    assert created["outcome"] == "created" and unchanged["outcome"] == "unchanged"
    assert unchanged["current_state_sha256"] == created["current_state_sha256"]

    assert {:ok, %{events: [^unchanged], next_after_sequence: 2}} =
             F.run(
               fn ctx -> PostgresStorage.audit(ctx, 1, 1, config) end,
               F.identity(),
               "audit.read",
               F.project()
             )
  end

  test "current principal exact request identity and revocation fence cached successes" do
    assert {:ok, _} = F.upload()
    assert {:error, :idempotency_conflict} = F.upload("first", "changed")
    other = F.identity(%{subject: "other-subject", credential_ref: "other-token"})
    assert {:error, :idempotency_conflict} = F.upload("first", "test", other)
    assert [[1, 1, 1, 1]] = F.counts()

    F.sql(
      "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'"
    )

    assert {:error, :unauthenticated} = F.upload()
    assert [[1, 1, 1, 1]] = F.counts()
  end

  test "pure lookalike changed context expiry and every forged Checked field reject" do
    {c, config} = F.data()
    assert_raise Context.Invalid, fn -> PostgresStorage.upload(%{}, c, F.command(), config) end

    for field <- Map.keys(Map.from_struct(c)) do
      assert {:error, _} =
               F.run(fn ctx ->
                 PostgresStorage.upload(ctx, Map.put(c, field, nil), F.command(), config)
               end)

      assert [[0, 0, 0, 0]] = F.counts()
    end

    assert {:error, _} =
             F.run(fn ctx ->
               PostgresStorage.upload(%{ctx | action: "artifact.read"}, c, F.command(), config)
             end)

    assert {:error, :unauthenticated} =
             F.upload("first", "test", F.identity(%{expires_at: F.now()}))
  end

  test "SQL CBOR independently matches Elixir bytes and enforces every bound" do
    {c, _} = F.data()

    values = [
      c.manifest,
      [2, "org-a", "project-a"],
      [
        true,
        false,
        23,
        24,
        255,
        256,
        65535,
        65536,
        4_294_967_295,
        4_294_967_296,
        18_446_744_073_709_551_615,
        "é",
        []
      ],
      %{"aa" => true, "b" => [1, 2]}
    ]

    for v <- values do
      {:ok, expected} = ArtifactCBOR.encode(v)
      assert [[^expected]] = F.sql("SELECT public.mixer_customer_cbor($1::jsonb)", [v]).rows
    end

    for v <- [
          List.duplicate(1, 257),
          List.duplicate(List.duplicate(1, 256), 17),
          String.duplicate("x", 65536),
          Enum.reduce(1..17, 0, fn _, x -> [x] end),
          nil,
          -1,
          1.5
        ] do
      assert_raise Postgrex.Error, fn ->
        F.sql("SELECT public.mixer_customer_cbor($1::jsonb)", [v])
      end
    end

    assert {:ok, _} = F.upload()

    [[display, cbor]] =
      F.sql("SELECT display,event_cbor FROM public.mixer_customer_audit_events").rows

    fields =
      ~w(audit_schema sequence tenant actor authorization target action outcome reason request_id source_ip recorded_at previous_state_sha256 current_state_sha256 previous_event_sha256 request_sha256 envelope_sha256)

    assert [[^cbor]] =
             F.sql("SELECT public.mixer_customer_cbor($1::jsonb)", [
               Enum.map(fields, &Map.fetch!(display, &1))
             ]).rows
  end

  test "runtime cannot mutate immutable rows provision heads mutate authz execute codec or become owner" do
    assert {:ok, _} = F.upload()

    for sql <- [
          "UPDATE public.mixer_customer_artifacts SET payload=payload",
          "DELETE FROM public.mixer_customer_audit_events",
          "TRUNCATE public.mixer_customer_idempotency",
          "INSERT INTO public.mixer_customer_artifact_heads VALUES ('org-a','project-a',0,'','x')",
          "UPDATE public.mixer_authz_memberships SET role='owner'",
          "SELECT public.mixer_customer_cbor('[]'::jsonb)",
          "SET ROLE storage_owner",
          "CREATE TABLE public.injected(id int)"
        ] do
      assert_raise Postgrex.Error, fn -> F.runtime_sql(sql) end
    end

    for table <- ~w(artifacts audit_events idempotency),
        do: assert(F.runtime_sql("SELECT * FROM public.mixer_customer_#{table}").rows == [])
  end

  test "head-only advancement and callback error exception roll back all storage" do
    {c, config} = F.data()

    assert {:error, _} =
             F.run(fn _ ->
               F.runtime_sql(
                 "UPDATE public.mixer_customer_artifact_heads SET sequence=1,event_sha256=repeat('a',64)"
               )

               {:ok, :attempted}
             end)

    assert [[0, 0, 0, 0]] = F.counts()

    assert {:error, :storage_unavailable} =
             F.run(fn ctx ->
               assert {:ok, _} = PostgresStorage.upload(ctx, c, F.command(), config)
               {:error, :storage_unavailable}
             end)

    assert [[0, 0, 0, 0]] = F.counts()

    assert {:error, _} =
             F.run(fn ctx ->
               assert {:ok, _} = PostgresStorage.upload(ctx, c, F.command(), config)
               raise "after write"
             end)

    assert [[0, 0, 0, 0]] = F.counts()
  end

  test "concurrent same key consumes one sequence and new-key unchanged operations serialize" do
    tasks = for _ <- 1..3, do: Task.async(fn -> F.upload() end)

    for task <- tasks,
        do: assert({:ok, %{status: 201, event_sequence: 1}} = Task.await(task, 10000))

    assert [[1, 1, 1, 1]] = F.counts()
    tasks = for n <- 1..3, do: Task.async(fn -> F.upload("next-#{n}") end)
    assert Enum.all?(Enum.map(tasks, &Task.await(&1, 10000)), &match?({:ok, %{status: 200}}, &1))
    assert [[1, 4, 4, 4]] = F.counts()
  end

  test "corrupt retained signed bytes and audit rows are unavailable" do
    {c, config} = F.data()
    assert {:ok, _} = F.upload()

    for table <- ~w(artifacts audit_events) do
      F.sql("ALTER TABLE public.mixer_customer_#{table} DISABLE TRIGGER customer_immutable")
      F.sql("ALTER TABLE public.mixer_customer_#{table} DISABLE TRIGGER customer_integrity")

      if table == "artifacts",
        do:
          F.sql(
            "UPDATE public.mixer_customer_artifacts SET signed_manifest_bytes=signed_manifest_bytes||decode('20','hex')"
          ),
        else: F.sql("UPDATE public.mixer_customer_audit_events SET event_cbor=decode('80','hex')")

      F.sql("ALTER TABLE public.mixer_customer_#{table} ENABLE TRIGGER customer_immutable")
      F.sql("ALTER TABLE public.mixer_customer_#{table} ENABLE TRIGGER customer_integrity")
    end

    assert {:error, :storage_unavailable} =
             F.run(
               fn ctx -> PostgresStorage.read(ctx, c.manifest_sha256, config) end,
               F.identity(),
               "artifact.read"
             )

    assert {:error, :storage_unavailable} =
             F.run(
               fn ctx -> PostgresStorage.audit(ctx, 0, 100, config) end,
               F.identity(),
               "audit.read",
               F.project()
             )
  end

  test "deferred SQL rejects incomplete writes changed retained fields forged projections actors and chain gaps" do
    for mode <-
          ~w(artifact_only event_only dedup_only no_artifact no_event no_dedup no_head wrong_payload wrong_signature wrong_canonical wrong_signed_bytes wrong_envelope wrong_manifest_hash cross_tenant wrong_event_cbor broken_predecessor wrong_projection wrong_actor wrong_authorization sequence_gap)a do
      assert {:error, _} = F.raw(mode), inspect(mode)
      assert [[0, 0, 0, 0]] = F.counts(), inspect(mode)
    end

    assert {:ok, :raw} = F.raw(:valid)
    assert [[1, 1, 1, 1]] = F.counts()
  end

  test "metadata phase helper exposes only signed metadata while direct byte selects remain hidden" do
    {_, config} = F.data()
    assert {:ok, _} = F.upload()

    assert {:ok, :private} =
             F.run(fn ctx ->
               MixerHosted.Authorization.Postgres.Session.context!(Runtime,
                 phase: "metadata",
                 action: "artifact.read",
                 required_scope: "mixer.artifact.read",
                 application_id: nil,
                 environment_id: nil
               )

               assert F.runtime_sql(
                        "SELECT envelope_bytes,payload FROM public.mixer_customer_artifacts"
                      ).rows == []

               result =
                 F.runtime_sql("SELECT * FROM public.mixer_customer_artifact_metadata($1)", [
                   elem(F.data(), 0).manifest_sha256
                 ])

               assert length(result.rows) == 1 and
                        result.columns ==
                          ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 signed_manifest_bytes)

               # The actual Context detects every staged-setting mutation. Restore exact
               # effect values before returning from this direct SQL metadata probe.
               MixerHosted.Authorization.Postgres.Session.context!(Runtime,
                 phase: "effect",
                 action: "artifact.upload",
                 required_scope: "mixer.artifact.upload",
                 application_id: ctx.target.application_id,
                 environment_id: ctx.target.environment_id
               )

               assert config.repo == Runtime
               {:ok, :private}
             end)
  end

  test "topology rejects broadened grants policies triggers helper body owner paths and extra write functions" do
    {c, config} = F.data()

    probes = [
      {"GRANT UPDATE(envelope_bytes) ON public.mixer_customer_artifacts TO storage_runtime",
       "REVOKE UPDATE(envelope_bytes) ON public.mixer_customer_artifacts FROM storage_runtime"},
      {"GRANT UPDATE ON public.mixer_customer_artifact_heads TO storage_runtime",
       "REVOKE UPDATE ON public.mixer_customer_artifact_heads FROM storage_runtime; GRANT UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO storage_runtime"},
      {"GRANT SELECT ON public.mixer_customer_artifacts TO PUBLIC",
       "REVOKE SELECT ON public.mixer_customer_artifacts FROM PUBLIC"},
      {"ALTER TABLE public.mixer_customer_artifacts DISABLE TRIGGER customer_integrity",
       "ALTER TABLE public.mixer_customer_artifacts ENABLE TRIGGER customer_integrity"},
      {"CREATE POLICY injected ON public.mixer_customer_artifacts FOR SELECT USING(true)",
       "DROP POLICY injected ON public.mixer_customer_artifacts"},
      {"GRANT storage_owner TO storage_runtime", "REVOKE storage_owner FROM storage_runtime"},
      {"GRANT CREATE ON SCHEMA public TO PUBLIC", "REVOKE CREATE ON SCHEMA public FROM PUBLIC"},
      {"CREATE FUNCTION public.injected() RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS 'BEGIN RETURN true; END'",
       "DROP FUNCTION public.injected()"}
    ]

    for {change, undo} <- probes do
      F.sql(change)

      try do
        assert {:error, :authorization_unavailable} =
                 F.run(fn ctx -> PostgresStorage.upload(ctx, c, F.command(), config) end),
               change
      after
        for statement <- String.split(undo, ";", trim: true), do: F.sql(statement)
      end
    end

    assert {:ok, _} = F.upload()
  end

  test "token and current-root expiry after domain head wait precede idempotency replay" do
    {c, config} = F.data()
    assert {:ok, _} = F.upload()

    for expiry <- [:token, :root] do
      # Begin near a second boundary; the held head remains below the 500ms
      # production lock timeout while expiry occurs before the lock is released.
      delay = Integer.mod(820 - Integer.mod(System.system_time(:millisecond), 1000), 1000)
      Process.sleep(delay)
      parent = self()

      holder =
        Task.async(fn ->
          Admin.transaction(fn ->
            F.sql("SELECT 1 FROM public.mixer_customer_artifact_heads FOR UPDATE")
            send(parent, :head_locked)
            Process.sleep(280)
          end)
        end)

      assert_receive :head_locked
      now = F.now()
      identity = if expiry == :token, do: F.identity(%{expires_at: now + 1}), else: F.identity()

      config =
        if expiry == :root,
          do: %{config | roots: Enum.map(config.roots, &Map.put(&1, "not_after_unix", now + 1))},
          else: config

      assert {:error, reason} =
               F.run(fn ctx -> PostgresStorage.upload(ctx, c, F.command(), config) end, identity)

      assert reason in [:unauthenticated, :storage_unavailable]
      Task.await(holder)
      assert [[1, 1, 1, 1]] = F.counts()
    end
  end

  test "revocation takes canonical conflicting locks and cached upload private reads cannot pass afterward" do
    {c, config} = F.data()
    parent = self()

    admitted =
      Task.async(fn ->
        F.run(fn ctx ->
          result = PostgresStorage.upload(ctx, c, F.command(), config)
          send(parent, :upload_admitted)

          receive do
            :commit -> result
          after
            2000 -> {:error, :storage_unavailable}
          end
        end)
      end)

    assert_receive :upload_admitted, 1000

    revoker =
      Task.async(fn ->
        Admin.transaction(fn ->
          for {table, predicate} <- [
                {"profiles", "id='profile'"},
                {"principals", "id='person'"},
                {"families", "id='family'"},
                {"credentials", "reference='token'"},
                {"organization_heads", "organization_id='org-a'"},
                {"project_heads", "organization_id='org-a' AND project_id='project-a'"}
              ],
              do: F.sql("SELECT 1 FROM public.mixer_authz_#{table} WHERE #{predicate} FOR UPDATE")

          F.sql(
            "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'"
          )
        end)
      end)

    assert Task.yield(revoker, 50) == nil
    send(admitted.pid, :commit)
    assert {:ok, %{status: 201}} = Task.await(admitted)
    assert {:ok, _} = Task.await(revoker)
    assert {:error, :unauthenticated} = F.upload()

    assert {:error, :unauthenticated} =
             F.run(
               fn ctx -> PostgresStorage.read(ctx, c.manifest_sha256, config) end,
               F.identity(),
               "artifact.read"
             )
  end

  test "format-only signed JSON preserves first bytes and refreshed credentials preserve original actor" do
    {c, config} = F.data()
    assert {:ok, _} = F.upload()
    original = F.sql("SELECT * FROM public.mixer_customer_artifacts").rows

    F.sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'fresh-token','person','family',true,0,NULL,8)"
    )

    assert {:ok, %{status: 201, event_sequence: 1}} =
             F.upload("first", "test", F.identity(%{credential_ref: "fresh-token"}))

    assert [[1, 1, 1, 1]] = F.counts()
    signed = c.signed_manifest_bytes |> Jason.decode!() |> Jason.encode!(pretty: true)

    bytes =
      "{\"signed_manifest\":" <>
        signed <> ",\"payload\":" <> Jason.encode!(Base.encode64(c.payload)) <> "}"

    {:ok, formatted} = ArtifactAdmission.admit(bytes, config.host, config.roots, F.now())
    other = F.identity(%{subject: "other-subject", credential_ref: "other-token"})

    assert {:ok, %{status: 200, event_sequence: 2}} =
             F.run(
               fn ctx ->
                 PostgresStorage.upload(ctx, formatted, F.command("other-key"), config)
               end,
               other
             )

    assert original == F.sql("SELECT * FROM public.mixer_customer_artifacts").rows

    assert [["person"], ["other"]] ==
             F.sql(
               "SELECT display->'actor'->>0 FROM public.mixer_customer_audit_events ORDER BY sequence"
             ).rows
  end

  test "missing head and rescued topology rejection latch the callback and roll back prior domain writes" do
    {c, config} = F.data()
    F.sql("DELETE FROM public.mixer_customer_artifact_heads")

    assert {:error, :storage_unavailable} =
             F.run(fn ctx -> PostgresStorage.upload(ctx, c, F.command(), config) end)

    F.seed!()

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

               {:ok, :rescued}
             end)

    assert [[0, 0, 0, 0]] = F.counts()
  end
end
