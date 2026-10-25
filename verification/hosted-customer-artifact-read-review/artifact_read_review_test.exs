defmodule MixerHosted.Authorization.ArtifactReadReviewFixture.Admin do
  use Ecto.Repo, otp_app: :mixer_artifact_read_review_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.ArtifactReadReviewFixture.Migration do
  use Ecto.Repo, otp_app: :mixer_artifact_read_review_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.ArtifactReadReviewFixture.Runtime do
  use Ecto.Repo, otp_app: :mixer_artifact_read_review_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.Authorization.ArtifactReadReviewFixture do
  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Authorization.ArtifactReadReviewFixture.{Admin, Runtime}
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactCBOR

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @locks ~w(profiles principals families credentials organization_heads project_heads)
  @fixture Path.join(
             System.fetch_env!("MIXER_ARTIFACT_READ_REVIEW_INPUTS"),
             "services/protocol/testdata/signed-release-v3.json"
           )
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

    sql("TRUNCATE public.read_review_probe")

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
      [:mixer_artifact_read_review_fixture, :repo, :query],
      fn _, _, metadata, _ -> callback.(metadata.query) end,
      nil
    )
  end

  def expire(i),
    do: Process.sleep(max(0, i.expires_at * 1_000 - System.system_time(:millisecond) + 10))
end

defmodule MixerHosted.Authorization.ArtifactReadReviewTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization.{ArtifactRead, Policy}
  alias MixerHosted.Authorization.Postgres.{Evidence, Session}
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Authorization.ArtifactReadReviewFixture, as: F
  alias MixerHosted.Authorization.ArtifactReadReviewFixture.{Admin, Migration, Runtime}
  alias MixerHosted.CustomerArtifacts.PostgresStorage

  setup_all do
    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_ARTIFACT_READ_REVIEW_TEST_PORT")),
      database: "mixer_artifact_read_review",
      ssl: false,
      log: false
    ]

    start_supervised!({Admin, settings ++ [username: "read_review_fixture_admin", pool_size: 4]})

    start_supervised!(
      {Migration,
       settings ++
         [
           username: "read_review_fixture_admin",
           pool_size: 2,
           after_connect: fn conn -> Postgrex.query!(conn, "SET ROLE read_review_owner", []) end
         ]}
    )

    start_supervised!(
      {Runtime,
       settings ++
         [
           username: "read_review_runtime",
           pool_size: 1,
           telemetry_prefix: [:mixer_artifact_read_review_fixture, :repo]
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
        do: F.sql("GRANT SELECT ON public.mixer_authz_#{table} TO read_review_runtime")

    for table <- F.locks(),
        do:
          F.sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO read_review_runtime"
          )

    for table <- ~w(artifacts audit_events idempotency),
        do: F.sql("GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO read_review_runtime")

    F.sql("GRANT SELECT ON public.mixer_customer_artifact_heads TO read_review_runtime")

    F.sql(
      "GRANT UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO read_review_runtime"
    )

    for {name, signature} <- MixerHosted.CustomerArtifacts.Schema.signatures(),
        name in ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
        do: F.sql("GRANT EXECUTE ON FUNCTION public.#{name}(#{signature}) TO read_review_runtime")

    F.sql("CREATE TABLE public.read_review_probe(id text NOT NULL)")
    F.sql("GRANT SELECT,INSERT ON public.read_review_probe TO read_review_runtime")

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

  test "read-only OAuth scope resolves metadata without audit authority" do
    i = F.identity()
    assert i.scopes == ["mixer.artifact.read"]

    assert {:ok, :read} =
             F.run(
               fn ctx, metadata ->
                 assert ctx.action == "artifact.read"
                 assert ctx.snapshot.identity.scopes == ["mixer.artifact.read"]
                 assert metadata.target == F.target()
                 {:ok, :read}
               end,
               i
             )

    assert {:error, :permission_denied} =
             MixerHosted.Authorization.with_authorized_transaction(
               i,
               "audit.read",
               F.project(),
               fn _ -> flunk("audit scope was borrowed") end,
               Runtime
             )
  end

  test "all incomplete full or extra-field project requests fail before repo access" do
    for target <- [
          %MixerHosted.Authorization.Scope{organization_id: "org"},
          F.target(),
          %{F.project() | application_id: "app"},
          Map.put(Map.from_struct(F.project()), :extra, "value"),
          %{"organization_id" => "org", "project_id" => "project"},
          Map.put(F.project(), :extra, true),
          nil
        ] do
      assert {:error, :invalid_request} =
               F.run(
                 fn _, _ -> flunk() end,
                 F.identity(),
                 target,
                 F.document().digest,
                 MissingReadReviewRepo
               )
    end

    for i <- [
          nil,
          Map.from_struct(F.identity()),
          Map.put(F.identity(), :extra, true),
          F.identity(%{scopes: ["mixer.artifact.read" | :improper]}),
          F.identity(%{scopes: ["mixer.artifact.read", "mixer.artifact.read"]}),
          F.identity(%{issued_at: F.now() + 31}),
          F.identity(%{expires_at: F.now()})
        ] do
      assert {:error, :unauthenticated} =
               F.run(
                 fn _, _ -> flunk() end,
                 i,
                 F.project(),
                 F.document().digest,
                 MissingReadReviewRepo
               )
    end

    assert {:error, :permission_denied} =
             F.run(
               fn _, _ -> flunk() end,
               F.identity(%{scopes: ["mixer.audit.read"]}),
               %{F.project() | project_id: "hidden"},
               F.document().digest,
               MissingReadReviewRepo
             )
  end

  test "organization-only scope cannot see project but explicit all-projects reader can" do
    F.sql(
      "UPDATE public.mixer_authz_memberships SET project_id=NULL,project_binding='organization_only',role='viewer'"
    )

    assert {:error, :not_found} = F.run(fn _, _ -> flunk() end)
    F.sql("UPDATE public.mixer_authz_memberships SET project_binding='all_projects'")
    assert {:ok, :accepted} = F.run()
    F.sql("UPDATE public.mixer_authz_memberships SET role='billing_manager'")
    assert {:error, :permission_denied} = F.run(fn _, _ -> flunk() end)
  end

  test "committed identity role and ancestry changes during observed profile lock are current before metadata" do
    for {sql, expected} <- [
          {"UPDATE public.mixer_authz_profiles SET active=false", :unauthenticated},
          {"UPDATE public.mixer_authz_bindings SET active=false", :unauthenticated},
          {"UPDATE public.mixer_authz_principals SET active=false", :unauthenticated},
          {"UPDATE public.mixer_authz_credentials SET active=false", :unauthenticated},
          {"UPDATE public.mixer_authz_families SET active=false", :unauthenticated},
          {"UPDATE public.mixer_authz_memberships SET role='billing_manager'",
           :permission_denied},
          {"UPDATE public.mixer_authz_memberships SET active=false", :not_found},
          {"UPDATE public.mixer_authz_organizations SET active=false", :not_found},
          {"UPDATE public.mixer_authz_projects SET active=false", :not_found}
        ] do
      F.seed!()
      parent = self()

      F.observe(:review_lock_metadata, fn query ->
        if String.starts_with?(query, "SELECT * FROM public.mixer_customer_artifact_metadata("),
          do: send(parent, :unexpected_metadata)
      end)

      writer =
        Task.async(fn ->
          Admin.transaction(fn ->
            F.sql("SELECT 1 FROM public.mixer_authz_profiles FOR UPDATE")
            send(parent, {:writer_locked, self()})

            receive do
              :commit_change -> F.sql(sql)
            after
              2_000 -> flunk("review writer not released")
            end
          end)
        end)

      assert_receive {:writer_locked, pid}

      worker =
        Task.async(fn ->
          Runtime.checkout(fn ->
            [[backend]] = F.runtime_sql("SELECT pg_backend_pid()").rows
            send(parent, {:review_backend, backend})
            F.run(fn _, _ -> flunk("changed authority reached callback") end)
          end)
        end)

      try do
        assert_receive {:review_backend, backend}
        assert_lock_wait!(backend)
        send(pid, :commit_change)
        assert {:ok, _} = Task.await(writer)
        assert {:error, ^expected} = Task.await(worker)
        refute_receive :unexpected_metadata, 0
      after
        send(pid, :commit_change)
        :telemetry.detach(:review_lock_metadata)
      end
    end
  end

  test "inactive derived application and environment never become full contexts" do
    for table <- ~w(applications environments) do
      F.seed!()
      F.sql("UPDATE public.mixer_authz_#{table} SET active=false")
      assert {:error, :not_found} = F.run(fn _, _ -> flunk() end)
    end
  end

  test "credential family and membership expiry during metadata resolution reject callback" do
    for {table, expected} <- [
          {"credentials", :unauthenticated},
          {"families", :unauthenticated},
          {"memberships", :not_found}
        ] do
      F.seed!()
      finish = F.now() + 1
      F.sql("UPDATE public.mixer_authz_#{table} SET expires_at=$1", [finish])

      F.observe(:review_window_metadata, fn query ->
        if String.starts_with?(query, "SELECT * FROM public.mixer_customer_artifact_metadata("),
          do: F.expire(%{expires_at: finish})
      end)

      try do
        assert {:error, ^expected} = F.run(fn _, _ -> flunk() end)
      after
        :telemetry.detach(:review_window_metadata)
      end
    end
  end

  test "metadata phase helper rejects wrong exact action scope windows and nonempty derived settings" do
    for changes <- [
          [phase: "effect"],
          [action: "audit.read"],
          [required_scope: "mixer.audit.read"],
          [application_id: "app"],
          [environment_id: "env"],
          [token_expires_at: "0"],
          [token_issued_at: "0001"],
          [token_expires_at: "9007199254740992"],
          [token_issued_at: Integer.to_string(F.now() + 31)],
          [identity_class: "service"],
          [issuer: "https://foreign.example"],
          [client_id: "foreign"],
          [subject: "foreign"],
          [principal_id: "foreign"],
          [family_id: "foreign"],
          [credential_ref: "foreign"]
        ] do
      assert {:ok, :closed} =
               Runtime.transaction(fn ->
                 prepare_metadata!()
                 Session.context!(Runtime, changes)

                 assert [] ==
                          F.runtime_sql(
                            "SELECT * FROM public.mixer_customer_artifact_metadata($1)",
                            [F.document().digest]
                          ).rows

                 assert [] ==
                          F.runtime_sql(
                            "SELECT envelope_bytes,payload FROM public.mixer_customer_artifacts"
                          ).rows

                 :closed
               end)
    end
  end

  test "metadata stage SQL contains no payload envelope or runtime base-table read" do
    parent = self()
    F.observe(:review_query_phase, fn query -> send(parent, {:review_query, query}) end)

    try do
      assert {:ok, :accepted} = F.run()
      queries = drain_queries([])

      {before, after_metadata} =
        Enum.split_while(
          queries,
          &(not String.starts_with?(&1, "SELECT * FROM public.mixer_customer_artifact_metadata("))
        )

      assert [metadata | _] = after_metadata
      assert metadata == "SELECT * FROM public.mixer_customer_artifact_metadata($1)"
      assert Enum.count(queries, &(&1 == metadata)) == 1

      for q <- before do
        refute String.contains?(q, "FROM public.mixer_customer_artifacts")
        refute String.contains?(q, "SELECT envelope_bytes")
        refute String.contains?(q, "SELECT payload")
      end
    after
      :telemetry.detach(:review_query_phase)
    end
  end

  test "strict signed JSON duplicates unknown keys surrogate and canonical signature spellings fail" do
    d = F.document()
    signed = Jason.encode!(d.signed)
    sig = d.signed["signature"]

    malformed = [
      "{\"manifest\":{},\"manifest\":" <>
        Jason.encode!(d.manifest) <> ",\"signature\":" <> Jason.encode!(sig) <> "}",
      "{\"manifest\":" <>
        Jason.encode!(d.manifest) <>
        ",\"signature\":" <> Jason.encode!(sig) <> ",\"signature\":" <> Jason.encode!(sig) <> "}",
      String.replace(signed, "\"signature\":", "\"unknown\":0,\"signature\":"),
      signed <> "true",
      "\"\\ud800\"",
      <<255, 0, 1>>,
      Jason.encode!(%{d.signed | "signature" => String.trim_trailing(sig, "=")}),
      Jason.encode!(%{d.signed | "signature" => String.duplicate("A", 87) <> "="})
    ]

    for bytes <- malformed do
      assert {:error, :storage_unavailable} =
               ArtifactRead.decode_metadata(
                 List.replace_at(d.row, 7, bytes),
                 F.project(),
                 d.digest
               )
    end

    assert {:error, :storage_unavailable} =
             ArtifactRead.decode_metadata(d.row, F.project(), String.duplicate("f", 64))

    assert {:error, :storage_unavailable} =
             ArtifactRead.decode_result(
               %{
                 columns:
                   ~w(organization_id project_id application_id environment_id platform runtime_sha256 manifest_sha256 signed_manifest_bytes),
                 rows: [d.row, d.row]
               },
               F.project(),
               d.digest
             )
  end

  test "permuted signed JSON retains one canonical CBOR and unchanged manifest digest" do
    d = F.document()

    bytes =
      "{ \"signature\" : " <>
        Jason.encode!(d.signed["signature"]) <>
        ", \"manifest\" : " <> Jason.encode!(d.manifest) <> " }"

    assert {:ok, metadata} =
             ArtifactRead.decode_metadata(List.replace_at(d.row, 7, bytes), F.project(), d.digest)

    assert metadata.canonical_manifest_cbor == d.cbor
    assert metadata.manifest_sha256 == F.hash(d.cbor)
    assert metadata.signed_manifest_bytes == bytes

    assert Map.keys(metadata) |> Enum.sort() ==
             Enum.sort([
               :target,
               :platform,
               :runtime_sha256,
               :manifest_sha256,
               :signed_manifest_bytes,
               :canonical_manifest_cbor,
               :manifest
             ])
  end

  test "every exact GUC fingerprint field detects tampering and rolls earlier SQL back" do
    for key <-
          ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase) do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx, metadata ->
                 F.runtime_sql("INSERT INTO public.read_review_probe VALUES ('must_rollback')")
                 Session.context!(Runtime, [{key, "tampered"}])

                 try do
                   Context.checkpoint!(ctx, Runtime, "artifact.read", metadata.target)
                 catch
                   _, _ -> :caught
                 end

                 {:ok, :rescued}
               end)

      assert [[0]] == F.sql("SELECT count(*) FROM public.read_review_probe").rows
    end
  end

  test "forged context and substituted action or target latch rollback" do
    for attempt <- [:context, :target, :action] do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx, metadata ->
                 F.runtime_sql("INSERT INTO public.read_review_probe VALUES ('must_rollback')")
                 candidate = if attempt == :context, do: %{ctx | marker: "forged"}, else: ctx

                 target =
                   if attempt == :target,
                     do: %{metadata.target | environment_id: "other"},
                     else: metadata.target

                 action = if attempt == :action, do: "audit.read", else: "artifact.read"

                 try do
                   Context.checkpoint!(candidate, Runtime, action, target)
                 catch
                   _, _ -> :caught
                 end

                 {:ok, :rescued}
               end)

      assert [[0]] == F.sql("SELECT count(*) FROM public.read_review_probe").rows
    end
  end

  test "cross-process and retained contexts never grant authority while valid owner continues" do
    assert {:ok, {ctx, metadata}} =
             F.run(fn ctx, metadata ->
               assert :rejected =
                        Task.async(fn ->
                          try do
                            Context.checkpoint!(ctx, Runtime, "artifact.read", metadata.target)
                            :accepted
                          rescue
                            Context.Invalid -> :rejected
                          end
                        end)
                        |> Task.await()

               assert {:error, :authorization_unavailable} = F.run()
               assert %{} = Context.checkpoint!(ctx, Runtime, "artifact.read", metadata.target)
               {:ok, {ctx, metadata}}
             end)

    assert_raise Context.Invalid, fn ->
      Context.checkpoint!(ctx, Runtime, "artifact.read", metadata.target)
    end

    assert {:error, :authorization_unavailable} =
             F.run(fn _, _ ->
               Context.checkpoint!(ctx, Runtime, "artifact.read", metadata.target)
               {:ok, :reused}
             end)
  end

  test "escaped effect exceptions throw exit malformed callbacks and unknown errors cannot be rescued into commit" do
    for effect <- [
          fn _ -> raise "private diagnostic" end,
          fn _ -> throw(:private) end,
          fn _ -> exit(:private) end,
          fn _ -> {:error, :unknown} end,
          :not_a_function
        ] do
      assert {:error, :authorization_unavailable} =
               F.run(fn ctx, metadata ->
                 F.runtime_sql("INSERT INTO public.read_review_probe VALUES ('must_rollback')")

                 try do
                   Context.effect!(ctx, Runtime, "artifact.read", metadata.target, effect)
                 catch
                   _, _ -> :caught
                 end

                 {:ok, :rescued}
               end)

      assert [[0]] == F.sql("SELECT count(*) FROM public.read_review_probe").rows
    end
  end

  test "monotonic deadline after metadata resolution fails before callback" do
    F.observe(:review_deadline_metadata, fn query ->
      if String.starts_with?(query, "SELECT * FROM public.mixer_customer_artifact_metadata("),
        do: Process.sleep(5_050)
    end)

    try do
      assert {:error, :authorization_unavailable} =
               F.run(fn _, _ -> flunk("expired deadline callback") end)
    after
      :telemetry.detach(:review_deadline_metadata)
    end
  end

  test "final independent deadline prevents cached callback success committing" do
    assert {:error, :authorization_unavailable} =
             F.run(fn _, _ ->
               F.runtime_sql("INSERT INTO public.read_review_probe VALUES ('must_rollback')")
               Process.sleep(5_050)
               {:ok, :cached}
             end)

    assert [[0]] == F.sql("SELECT count(*) FROM public.read_review_probe").rows
  end

  test "successful completion leaves no context settings private rows or transaction for connection reuse" do
    assert {:ok, :accepted} = F.run()
    assert F.clean?()
    refute Runtime.in_transaction?()
    assert {:ok, :accepted} = F.run()
  end

  defp assert_lock_wait!(backend) do
    assert Enum.reduce_while(1..70, false, fn _, _ ->
             case F.sql("SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=$1", [
                    backend
                  ]).rows do
               [[true]] ->
                 {:halt, true}

               _ ->
                 Process.sleep(2)
                 {:cont, false}
             end
           end)
  end

  defp prepare_metadata! do
    i = F.identity()
    lookup = %{identity: Policy.identity_key(i), action: "artifact.read", target: F.project()}
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
  end

  defp drain_queries(acc) do
    receive do
      {:review_query, q} -> drain_queries([q | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end
end
