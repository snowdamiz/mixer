defmodule MixerHosted.Authorization.ArtifactReadFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_artifact_read_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.ArtifactReadFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_artifact_read_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.ArtifactReadFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_artifact_read_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.ArtifactReadFixture do
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Authorization.ArtifactReadFixture.{Admin, Runtime}
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactCBOR

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @locks ~w(profiles principals families credentials organization_heads project_heads)
  @fixture Path.expand("../../../../services/protocol/testdata/signed-release-v3.json", __DIR__)
  def tables, do: @tables
  def locks, do: @locks
  def sql(sql, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, sql, params, log: false)

  def runtime_sql(sql, params \\ []),
    do: Ecto.Adapters.SQL.query!(Runtime, sql, params, log: false)

  def now, do: System.system_time(:second)
  def hash(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  def identity(changes \\ %{}) do
    struct!(
      VerifiedIdentity,
      Map.merge(
        %{
          profile_id: "profile",
          profile_version: 1,
          issuer: "https://issuer.example",
          subject: "subject",
          client_id: "client",
          credential_ref: "token",
          issued_at: now() - 20,
          expires_at: now() + 600,
          identity_class: :human,
          scopes: ["mixer.artifact.read"]
        },
        changes
      )
    )
  end

  def project, do: %Scope{organization_id: "org", project_id: "project"}
  def target, do: %{project() | application_id: "app", environment_id: "env"}

  def document(environment \\ "env") do
    original = @fixture |> File.read!() |> Jason.decode!()
    signed = original["signed_manifest"]

    scope = %{
      "organization" => "org",
      "project" => "project",
      "app" => "app",
      "environment" => environment,
      "platform" => "ios"
    }

    manifest = Map.put(signed["manifest"], "scope", scope)
    signed = Map.put(signed, "manifest", manifest)
    bytes = Jason.encode!(signed)
    {:ok, cbor} = ArtifactCBOR.encode(manifest)
    payload = Base.decode64!(original["payload"])

    envelope =
      "{\"signed_manifest\":" <>
        bytes <> ",\"payload\":" <> Jason.encode!(original["payload"]) <> "}"

    %{
      manifest: manifest,
      signed: signed,
      bytes: bytes,
      cbor: cbor,
      digest: hash(cbor),
      payload: payload,
      envelope: envelope,
      row: ["org", "project", "app", environment, "ios", manifest["runtime"], hash(cbor), bytes]
    }
  end

  def run(
        callback \\ fn _, _ -> {:ok, :accepted} end,
        identity \\ identity(),
        project \\ project(),
        digest \\ document().digest,
        repo \\ Runtime
      ),
      do: Authorization.with_artifact_read_transaction(identity, project, digest, callback, repo)

  def seed! do
    sql(
      "TRUNCATE " <>
        Enum.map_join(Enum.reverse(@tables), ",", &("public.mixer_authz_" <> &1)) <> " CASCADE"
    )

    sql("TRUNCATE public.read_scope_probe")

    sql(
      "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https://issuer.example','client','human',true)"
    )

    sql("INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,2)")

    sql(
      "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,'subject','human','person',true)"
    )

    sql(
      "INSERT INTO public.mixer_authz_families VALUES ('family','profile',1,'person',true,0,NULL,3)"
    )

    sql(
      "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,'token','person','family',true,0,NULL,4)"
    )

    sql("INSERT INTO public.mixer_authz_organizations VALUES ('org',true)")
    sql("INSERT INTO public.mixer_authz_projects VALUES ('org','project',true)")
    sql("INSERT INTO public.mixer_authz_applications VALUES ('org','project','app',true)")

    sql(
      "INSERT INTO public.mixer_authz_environments VALUES ('org','project','app','env',true),('org','project','app','other',true)"
    )

    sql("INSERT INTO public.mixer_authz_organization_heads VALUES ('org',5)")
    sql("INSERT INTO public.mixer_authz_project_heads VALUES ('org','project',6)")

    sql(
      "INSERT INTO public.mixer_authz_memberships VALUES ('member','person','org','project','exact_project','developer',true,0,NULL,7)"
    )

    # Synthetic admin fixture only: bypass mutation/deferred triggers when
    # creating rows. This is actual product schema/RLS/helper testing, never
    # evidence for upload chain integrity or signature admission.
    Admin.transaction(fn ->
      sql("SET LOCAL session_replication_role=replica")

      sql("INSERT INTO public.mixer_customer_artifact_heads VALUES ('org','project',0,'',$1)", [
        String.duplicate("0", 64)
      ])

      insert_document!(document())
      insert_document!(document("other"))
    end)

    :ok
  end

  def insert_document!(d) do
    sql(
      """
      INSERT INTO public.mixer_customer_artifacts(organization_id,project_id,application_id,environment_id,platform,
        runtime_sha256,manifest_sha256,payload_sha256,envelope_sha256,envelope_bytes,signed_manifest_bytes,
        canonical_manifest_cbor,signature,payload,creating_sequence)
      VALUES ('org','project','app',$1,'ios',$2,$3,$4,$5,$6,$7,$8,$9,$10,1)
      """,
      [
        d.manifest["scope"]["environment"],
        d.manifest["runtime"],
        d.digest,
        hash(d.payload),
        hash(d.envelope),
        d.envelope,
        d.bytes,
        d.cbor,
        Base.decode64!(d.signed["signature"]),
        d.payload
      ]
    )
  end

  def mutate!(sql, params \\ []) do
    Admin.transaction(fn ->
      sql("SET LOCAL session_replication_role=replica")
      sql(sql, params)
    end)
  end

  def clean? do
    not MixerHosted.Authorization.Transaction.Context.active?() and
      runtime_sql(
        "SELECT " <>
          Enum.map_join(
            ~w(transaction_marker phase token_issued_at token_expires_at required_scope),
            ",",
            &("coalesce(current_setting('mixer.authz." <> &1 <> "',true),'')")
          )
      ).rows == [["", "", "", "", ""]] and
      runtime_sql("SELECT count(*) FROM public.mixer_customer_artifacts").rows == [[0]]
  end

  def observe(id, callback) do
    :telemetry.attach(
      id,
      [:mixer_artifact_read_fixture, :repo, :query],
      fn _, _, metadata, _ -> callback.(metadata.query) end,
      nil
    )
  end

  def expire(i),
    do: Process.sleep(max(0, i.expires_at * 1_000 - System.system_time(:millisecond) + 10))
end

defmodule MixerHosted.Authorization.ArtifactReadTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization.{ArtifactRead, Policy}
  alias MixerHosted.Authorization.Postgres.{Evidence, Session}
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Authorization.ArtifactReadFixture, as: F
  alias MixerHosted.Authorization.ArtifactReadFixture.{Admin, Migration, Runtime}
  alias MixerHosted.CustomerArtifacts.PostgresStorage

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_ARTIFACT_READ_SCOPE_TEST_PORT")),
      database: "mixer_artifact_read_scope",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "read_scope_fixture_admin", pool_size: 4]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "read_scope_fixture_admin",
           pool_size: 2,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE read_scope_owner", []) end
         ]}
    )

    start_supervised!(
      {Runtime,
       settings ++
         [
           username: "read_scope_runtime",
           pool_size: 1,
           telemetry_prefix: [:mixer_artifact_read_fixture, :repo]
         ]}
    )

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage}
        ] do
      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    for table <- F.tables(),
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{table} TO read_scope_runtime")

    for table <- F.locks(),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO read_scope_runtime"
          )

    for table <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO read_scope_runtime")

    F.sql("GRANT SELECT ON public.mixer_customer_artifact_heads TO read_scope_runtime")

    F.sql(
      "GRANT UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO read_scope_runtime"
    )

    for {name, signature} <- MixerHosted.CustomerArtifacts.Schema.signatures(),
        name in ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do: F.sql("GRANT EXECUTE ON FUNCTION public.#{name}(#{signature}) TO read_scope_runtime")

    F.sql("CREATE TABLE public.read_scope_probe(id text NOT NULL)")
    F.sql("GRANT SELECT,INSERT ON public.read_scope_probe TO read_scope_runtime")

    IO.puts(
      "READ_SCOPE_CATALOG_SHA256=" <> MixerHosted.CustomerArtifacts.Topology.catalog_hash(Admin)
    )

    :ok
  end

  setup do
    F.seed!()
    on_exit(fn -> assert F.clean?() end)
    :ok
  end

  test "project metadata admission requires verified human read scope and never weakens artifact requests" do
    assert {:ok, project} = Policy.metadata_request(F.identity(), F.project(), F.now())
    assert project == F.project()

    assert {:error, :invalid_request} =
             Policy.request(F.identity(), "artifact.read", F.project(), F.now())

    assert {:error, :invalid_request} = Policy.metadata_request(F.identity(), F.target(), F.now())

    for i <- [
          nil,
          F.identity(%{identity_class: :service}),
          F.identity(%{expires_at: F.now()}),
          F.identity(%{scopes: ["mixer.audit.read"]})
        ] do
      assert {:error, _} =
               F.run(
                 fn _, _ -> flunk() end,
                 i,
                 F.project(),
                 F.document().digest,
                 MissingArtifactReadRepo
               )
    end

    for digest <- [nil, "", String.duplicate("A", 64), String.duplicate("0", 63)] do
      assert {:error, :invalid_request} =
               F.run(
                 fn _, _ -> flunk() end,
                 F.identity(),
                 F.project(),
                 digest,
                 MissingArtifactReadRepo
               )
    end
  end

  test "actual product metadata helper returns exact projection with empty app environment and no runtime private rows" do
    i = F.identity()

    assert {:ok, :stage} =
             Runtime.transaction(fn ->
               lookup = %{
                 identity: Policy.identity_key(i),
                 action: "artifact.read",
                 target: F.project()
               }

               linkage = Session.prepare!(Runtime, lookup)

               Session.context!(Runtime,
                 action: "artifact.read",
                 phase: "metadata",
                 required_scope: "mixer.artifact.read",
                 token_issued_at: Integer.to_string(i.issued_at),
                 token_expires_at: Integer.to_string(i.expires_at)
               )

               assert {:ok, _} =
                        Policy.metadata_evaluate(
                          i,
                          F.project(),
                          Evidence.load!(Runtime, lookup, linkage),
                          F.now()
                        )

               PostgresStorage.check_topology!(Runtime)

               assert [["", ""]] =
                        F.runtime_sql(
                          "SELECT current_setting('mixer.authz.application_id'),current_setting('mixer.authz.environment_id')"
                        ).rows

               result =
                 F.runtime_sql("SELECT * FROM public.mixer_customer_artifact_metadata($1)", [
                   F.document().digest
                 ])

               assert result.columns ==
                        ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 signed_manifest_bytes)

               assert result.rows == [F.document().row]

               assert [] ==
                        F.runtime_sql(
                          "SELECT envelope_bytes,payload FROM public.mixer_customer_artifacts"
                        ).rows

               assert [] == F.runtime_sql("SELECT * FROM public.mixer_customer_idempotency").rows
               assert [] == F.runtime_sql("SELECT * FROM public.mixer_customer_audit_events").rows
               refute Context.active?()
               :stage
             end)
  end

  test "facade derives full target and binds fresh effect snapshot and all four new settings" do
    i = F.identity()

    assert {:ok, {ctx, metadata}} =
             F.run(
               fn ctx, metadata ->
                 assert ctx.target == F.target() and ctx.snapshot.target == F.target()

                 assert metadata.target == F.target() and
                          metadata.manifest_sha256 == F.document().digest

                 refute Map.has_key?(metadata, :payload)
                 refute Map.has_key?(metadata, :envelope_bytes)

                 assert [
                          [
                            Integer.to_string(i.issued_at),
                            Integer.to_string(i.expires_at),
                            "mixer.artifact.read",
                            "effect"
                          ]
                        ] ==
                          F.runtime_sql(
                            "SELECT current_setting('mixer.authz.token_issued_at'),current_setting('mixer.authz.token_expires_at'),current_setting('mixer.authz.required_scope'),current_setting('mixer.authz.phase')"
                          ).rows

                 Context.effect!(ctx, Runtime, "artifact.read", metadata.target, fn _ ->
                   assert length(
                            F.runtime_sql("SELECT payload FROM public.mixer_customer_artifacts").rows
                          ) == 1
                 end)

                 {:ok, {ctx, metadata}}
               end,
               i
             )

    assert_raise Context.Invalid, fn ->
      Context.checkpoint!(ctx, Runtime, "artifact.read", metadata.target)
    end
  end

  test "each read role is evaluated using artifact read and billing cannot use visible metadata" do
    for role <- ~w(owner administrator developer release_manager viewer billing_manager) do
      F.sql("UPDATE public.mixer_authz_memberships SET role=$1", [role])

      expected =
        if role == "billing_manager", do: {:error, :permission_denied}, else: {:ok, :accepted}

      assert F.run() == expected
    end

    assert {:error, :permission_denied} =
             F.run(fn _, _ -> flunk() end, F.identity(%{scopes: ["mixer.artifact.upload"]}))
  end

  test "issuer credential membership and tenant rejection happen before metadata helper" do
    parent = self()

    F.observe(:read_rejection, fn query ->
      if String.contains?(query, "SELECT * FROM public.mixer_customer_artifact_metadata("),
        do: send(parent, :metadata)
    end)

    try do
      assert {:error, :unauthenticated} =
               F.run(fn _, _ -> flunk() end, F.identity(%{issuer: "https://wrong.example"}))

      F.sql("UPDATE public.mixer_authz_credentials SET active=false")
      assert {:error, :unauthenticated} = F.run()
      F.sql("UPDATE public.mixer_authz_credentials SET active=true")
      F.sql("UPDATE public.mixer_authz_memberships SET active=false")
      assert {:error, :not_found} = F.run()
      F.sql("UPDATE public.mixer_authz_memberships SET active=true")

      assert {:error, :not_found} =
               F.run(fn _, _ -> flunk() end, F.identity(), %{
                 F.project()
                 | organization_id: "foreign"
               })

      refute_receive :metadata
    after
      :telemetry.detach(:read_rejection)
    end
  end

  test "missing digest is not found and distinct environment digest derives its own exact target" do
    assert {:error, :not_found} =
             F.run(fn _, _ -> flunk() end, F.identity(), F.project(), String.duplicate("f", 64))

    assert {:ok, "other"} =
             F.run(
               fn ctx, m ->
                 assert ctx.target == %{F.target() | environment_id: "other"}
                 assert ctx.snapshot.target == m.target
                 {:ok, m.target.environment_id}
               end,
               F.identity(),
               F.project(),
               F.document("other").digest
             )

    F.sql("UPDATE public.mixer_authz_environments SET active=false WHERE id='other'")

    assert {:error, :not_found} =
             F.run(fn _, _ -> flunk() end, F.identity(), F.project(), F.document("other").digest)
  end

  test "metadata rejects every forged normalized column and closed malformed signed document" do
    d = F.document()
    assert {:ok, _} = ArtifactRead.decode_metadata(d.row, F.project(), d.digest)

    columns =
      ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 signed_manifest_bytes)

    assert {:ok, _} =
             ArtifactRead.decode_result(%{columns: columns, rows: [d.row]}, F.project(), d.digest)

    assert {:error, :not_found} =
             ArtifactRead.decode_result(%{columns: columns, rows: []}, F.project(), d.digest)

    for result <- [
          %{columns: columns, rows: [d.row, d.row]},
          %{columns: columns ++ ["payload"], rows: [d.row]},
          %{columns: Enum.reverse(columns), rows: [d.row]},
          %{columns: columns, rows: [d.row | :improper]},
          %{columns: columns, rows: [[]]}
        ] do
      assert {:error, :storage_unavailable} =
               ArtifactRead.decode_result(result, F.project(), d.digest)
    end

    for {offset, value} <- [
          {0, "foreign"},
          {1, "foreign"},
          {2, "other"},
          {3, "other"},
          {4, "android"},
          {5, String.duplicate("f", 64)},
          {6, String.duplicate("f", 64)},
          {7, "{}"},
          {7, String.duplicate(" ", 65537)}
        ] do
      assert {:error, :storage_unavailable} =
               ArtifactRead.decode_metadata(
                 List.replace_at(d.row, offset, value),
                 F.project(),
                 d.digest
               )
    end

    for signed <- [
          Map.put(d.signed, "extra", true),
          Map.put(d.signed, "signature", "AAAA"),
          Map.put(d.signed, "manifest", Map.put(d.manifest, "extra", true))
        ] do
      assert {:error, :storage_unavailable} =
               ArtifactRead.decode_metadata(
                 List.replace_at(d.row, 7, Jason.encode!(signed)),
                 F.project(),
                 d.digest
               )
    end

    assert {:error, :storage_unavailable} =
             ArtifactRead.decode_metadata(d.row ++ ["payload"], F.project(), d.digest)
  end

  test "actual corrupted metadata cannot reach callback" do
    F.mutate!(
      "UPDATE public.mixer_customer_artifacts SET runtime_sha256=$1 WHERE environment_id='env'",
      [String.duplicate("f", 64)]
    )

    assert {:error, :storage_unavailable} = F.run(fn _, _ -> flunk() end)
  end

  test "all four changed metadata effect settings latch failure and roll back earlier local SQL" do
    for {key, value} <- [
          {"token_issued_at", "0"},
          {"token_expires_at", "9007199254740991"},
          {"required_scope", "mixer.artifact.upload"},
          {"phase", "metadata"}
        ] do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx, m ->
                 F.runtime_sql("INSERT INTO public.read_scope_probe VALUES ('must_rollback')")
                 Session.context!(Runtime, [{key, value}])

                 try do
                   Context.checkpoint!(ctx, Runtime, "artifact.read", m.target)
                 catch
                   _, _ -> :caught
                 end

                 {:ok, :rescued}
               end)

      assert [[0]] == F.sql("SELECT count(*) FROM public.read_scope_probe").rows
    end
  end

  test "expiry immediately after actual metadata resolution rejects before callback" do
    i = F.identity(%{expires_at: F.now() + 1})

    F.observe(:read_expiry, fn query ->
      if String.starts_with?(query, "SELECT * FROM public.mixer_customer_artifact_metadata("),
        do: F.expire(i)
    end)

    try do
      assert {:error, :unauthenticated} = F.run(fn _, _ -> flunk() end, i)
    after
      :telemetry.detach(:read_expiry)
    end
  end

  test "expiry during actual six-lock admission is checked before metadata" do
    parent = self()

    writer =
      Task.async(fn ->
        Admin.transaction(fn ->
          F.sql("SELECT 1 FROM public.mixer_authz_profiles FOR UPDATE")
          send(parent, {:locked, self()})

          receive do
            :release -> :ok
          after
            2000 -> flunk("release timeout")
          end
        end)
      end)

    assert_receive {:locked, pid}
    Process.sleep(Integer.mod(820 - Integer.mod(System.system_time(:millisecond), 1000), 1000))
    i = F.identity(%{expires_at: F.now() + 1})

    worker =
      Task.async(fn ->
        Runtime.checkout(fn ->
          [[backend]] = F.runtime_sql("SELECT pg_backend_pid()").rows
          send(parent, {:backend, backend})
          F.run(fn _, _ -> flunk() end, i)
        end)
      end)

    assert_receive {:backend, backend}

    assert Enum.reduce_while(1..30, false, fn _, _ ->
             if F.sql("SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=$1", [
                  backend
                ]).rows == [[true]],
                do: {:halt, true},
                else:
                  (
                    Process.sleep(3)
                    {:cont, false}
                  )
           end)

    F.expire(i)
    send(pid, :release)
    assert {:ok, :ok} = Task.await(writer)
    assert {:error, :unauthenticated} = Task.await(worker)
  end

  test "final guard rolls back writes and revoked identity cannot receive a cached result" do
    i = F.identity(%{expires_at: F.now() + 1})

    assert {:error, :unauthenticated} =
             F.run(
               fn _, _ ->
                 F.runtime_sql("INSERT INTO public.read_scope_probe VALUES ('must_rollback')")
                 F.expire(i)
                 {:ok, :cached}
               end,
               i
             )

    assert [[0]] == F.sql("SELECT count(*) FROM public.read_scope_probe").rows
    F.sql("UPDATE public.mixer_authz_families SET active=false")
    assert {:error, :unauthenticated} = F.run(fn _, _ -> {:ok, :cached} end)
  end

  test "nested malformed failing callbacks preserve transaction discipline and cleanup" do
    assert {:ok, {:error, :authorization_unavailable}} = Runtime.transaction(fn -> F.run() end)

    for callback <- [
          fn _, _ -> :bad end,
          fn _, _ -> raise "private diagnostic" end,
          fn _, _ -> throw(:private) end,
          fn _, _ -> exit(:private) end,
          fn _, _ -> {:error, :unknown} end
        ] do
      assert {:error, :authorization_unavailable} = F.run(callback)
    end

    assert {:ok, :outer} =
             F.run(fn _, _ ->
               assert {:error, :authorization_unavailable} = F.run()
               {:ok, :outer}
             end)
  end

  test "helper definition tampering is rejected by exact topology before resolution" do
    original =
      F.sql(
        "SELECT pg_get_functiondef('public.mixer_customer_artifact_metadata(text)'::regprocedure)"
      ).rows
      |> hd()
      |> hd()

    try do
      F.sql(
        "CREATE OR REPLACE FUNCTION public.mixer_customer_artifact_metadata(digest text) RETURNS TABLE(organization_id text,project_id text,application_id text,environment_id text,platform text,runtime_sha256 text,manifest_sha256 text,signed_manifest_bytes bytea) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS 'BEGIN RETURN; END'"
      )

      assert {:error, :authorization_unavailable} = F.run(fn _, _ -> flunk() end)
    after
      F.sql(original)
    end
  end

  test "storage conflicts retain their bounded reasons and effect failures cannot be rescued" do
    for reason <- [:immutable_conflict, :idempotency_conflict] do
      assert {:error, ^reason} = F.run(fn _, _ -> {:error, reason} end)

      assert {:error, ^reason} =
               F.run(fn context, metadata ->
                 Context.effect!(context, Runtime, "artifact.read", metadata.target, fn _ ->
                   F.runtime_sql("INSERT INTO public.read_scope_probe VALUES ('must_rollback')")
                   {:error, reason}
                 end)
               end)

      assert {:error, :authorization_unavailable} =
               F.run(fn context, metadata ->
                 try do
                   Context.effect!(context, Runtime, "artifact.read", metadata.target, fn _ ->
                     F.runtime_sql("INSERT INTO public.read_scope_probe VALUES ('must_rollback')")
                     {:error, reason}
                   end)
                 catch
                   _, _ -> :caught
                 end

                 {:ok, :rescued}
               end)

      assert [[0]] == F.sql("SELECT count(*) FROM public.read_scope_probe").rows

      assert {:error, ^reason} =
               MixerHosted.Authorization.with_authorized_transaction(
                 F.identity(),
                 "artifact.read",
                 F.target(),
                 fn _ -> {:error, reason} end,
                 Runtime
               )
    end
  end
end
