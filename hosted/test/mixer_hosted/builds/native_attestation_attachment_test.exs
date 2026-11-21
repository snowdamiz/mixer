defmodule MixerHosted.Builds.NativeAttestationAttachmentTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Builds.{Dispatch, Journal, Lifecycle}
  alias MixerHosted.Builds.Lifecycle.ArtifactRef
  alias MixerHosted.CustomerBuilds
  alias MixerHosted.CustomerBuilds.{AttestationRepo, AttestationSchema}
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Repo.Migrations

  defmodule Admin do
    use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
  end

  defmodule Migration do
    use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
  end

  @socket "MIXER_ATTESTATION_TEST_SOCKET"
  if !System.get_env(@socket),
    do: @moduletag(skip: "requires the disposable W12 PostgreSQL fixture")

  @moduletag :native_attestation_db
  @writer "mixer_native_attestation_writer"
  @admin "mixer_attestation_fixture_admin"
  @database "mixer_native_attestation_fixture"
  @origin "http://127.0.0.1:59709"
  @binding String.duplicate("4", 64)
  @table "public.mixer_native_development_attestations"
  @entry "public.mixer_native_development_attestation_v1(text,text,text,text,jsonb,text,text,text,text,bytea)"

  setup_all do
    socket = System.fetch_env!(@socket)
    assert Path.type(socket) == :absolute
    assert File.exists?(Path.join(socket, ".s.PGSQL.5432.lock"))

    opts = [socket_dir: socket, database: @database, log: false, pool_size: 2]
    start_supervised!({Admin, opts ++ [username: @admin]})
    assert sql("SELECT current_database(), inet_server_addr()::text").rows == [[@database, nil]]

    for {role, mode} <- [
          attestation_fixture_owner: "NOLOGIN",
          mixer_native_attestation_writer: "LOGIN",
          attestation_fixture_reader: "LOGIN"
        ] do
      sql("CREATE ROLE #{role} #{mode} NOSUPERUSER NOBYPASSRLS NOINHERIT")
    end

    start_supervised!(
      {Migration,
       opts ++
         [
           username: @admin,
           after_connect: fn conn ->
             Postgrex.query!(conn, "SET ROLE attestation_fixture_owner", [])
           end
         ]}
    )

    sql("GRANT USAGE,CREATE ON SCHEMA public TO attestation_fixture_owner")
    sql("GRANT USAGE ON SCHEMA public TO #{@writer},attestation_fixture_reader")

    for {version, module, name} <- [
          {20_261_025_000_000, Migrations.AddBuildJournals, "add_build_journals"},
          {20_261_025_000_001, Migrations.AddBuildAdmission, "add_build_admission"},
          {20_261_025_000_003, Migrations.AddCustomerAuthorization, "add_customer_authorization"},
          {20_261_025_000_004, Migrations.AddAuthorizationStateRevisions,
           "add_authorization_state_revisions"},
          {20_261_120_000_017, Migrations.AddNativeDevelopmentAttestations,
           "add_native_development_attestations"}
        ] do
      paths = Path.wildcard("priv/**/#{version}_#{name}.exs")
      [path] = paths
      unless Code.ensure_loaded?(module), do: Code.require_file(path)
      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    assert sql("SELECT has_function_privilege($1,$2,'EXECUTE')", [@writer, @entry]).rows == [
             [false]
           ]

    sql(AttestationSchema.fixture_grant_statement())

    for table <-
          ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships) do
      sql("GRANT SELECT ON public.mixer_authz_#{table} TO #{@writer}")
    end

    for helper <- ~w(profiles principals families credentials organization_heads project_heads) do
      sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{helper}() TO #{@writer}")
    end

    start_supervised!({AttestationRepo, opts ++ [username: @writer]})
    seed_identity!()
    %{socket: socket}
  end

  setup %{socket: socket, test: test} do
    build = "build-" <> String.slice(sha(Atom.to_string(test)), 0, 16)
    run_id = Base.encode16(:crypto.strong_rand_bytes(8), case: :lower)
    root = Path.join(socket, build <> "-" <> run_id)
    File.mkdir!(root)
    on_exit(fn -> File.rm_rf!(root) end)
    File.chmod!(root, 0o700)
    put_config(:native_development_dispatch, %{retained_root: root})

    {spki, key} = keypair()
    put_config(:native_development_attestation, %{origin: @origin, public_spki_der: spki})

    selection = %{
      organization_id: "org-a",
      project_id: "project",
      application_id: "app",
      build_id: build,
      platform: "ios",
      source_sha256: String.duplicate("1", 64),
      toolchain_lock_sha256: String.duplicate("2", 64),
      build_definition_sha256: String.duplicate("3", 64)
    }

    %{selection: selection, root: root, identity: identity(), spki: spki, key: key}
  end

  test "exact settled second attempt is appended once under concurrent replay", c do
    b = completed!(c.selection, retry: true)
    retain!(c.root, b.operation, b.products)
    envelope = envelope(c, b)

    results =
      [envelope, envelope]
      |> Task.async_stream(&attach(c, &1), max_concurrency: 2)
      |> Enum.map(fn {:ok, result} -> result end)

    assert Enum.sort(results) == [{:ok, :attached}, {:ok, :duplicate}]
    assert {:ok, :duplicate} = attach(c, envelope)
    assert stored(b) == [[5, 2, b.operation, @binding, sha(c.spki), @origin, envelope]]

    assert sql("SELECT revision,journal FROM public.mixer_builds WHERE id=$1", [b.id]).rows ==
             [[5, b.journal]]
  end

  test "read/create scope, expired credential, viewer and foreign tenants cannot attach", c do
    b = completed!(c.selection)
    foreign_selection = %{c.selection | organization_id: "org-b"}
    foreign = completed!(foreign_selection)
    retain!(c.root, b.operation, b.products)
    retain!(c.root, foreign.operation, foreign.products)

    assert {:error, :permission_denied} =
             attach(
               %{
                 c
                 | identity: %{c.identity | scopes: ["mixer.build.read", "mixer.build.create"]}
               },
               envelope(c, b)
             )

    assert {:error, :unauthenticated} =
             attach(
               %{c | identity: %{c.identity | expires_at: c.identity.issued_at + 1}},
               envelope(c, b)
             )

    assert {:error, :permission_denied} =
             attach(%{c | identity: identity("viewer")}, envelope(c, b))

    assert {:error, :not_found} =
             attach(%{c | selection: foreign_selection}, envelope(c, foreign))

    assert {:error, :artifact_invalid} = attach(c, envelope(c, foreign))
    assert stored(b) == []
    assert stored(foreign) == []
  end

  test "rejects changed statements, malformed bytes, wrong key and independently pinned origin",
       c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)
    {other_spki, other_key} = keypair()

    for invalid <- [
          "{",
          envelope(c, b) <> "\n",
          envelope(%{c | spki: other_spki, key: other_key}, b),
          envelope(c, b, origin: "http://127.0.0.1:59710"),
          envelope(c, b, revision: 3),
          envelope(c, b, attempt: 2),
          envelope(c, b, artifacts: Enum.reverse(b.artifacts))
        ] do
      assert {:error, :artifact_invalid} = attach(c, invalid)
      assert stored(b) == []
    end

    assert {:error, :invalid_request} = attach(c, :bad)
    assert {:error, :invalid_request} = attach(c, :binary.copy("x", 16_385))

    assert {:error, :not_found} =
             attach(
               %{c | selection: %{c.selection | source_sha256: sha("foreign")}},
               envelope(c, b)
             )

    assert {:error, :invalid_request} =
             attach(%{c | selection: %{c.selection | platform: "android"}}, envelope(c, b))

    assert stored(b) == []
  end

  test "requires released admission and both exact parents under the settled operation", c do
    b = completed!(c.selection, held: true)
    envelope = envelope(c, b)
    retain!(c.root, sha("foreign operation"), b.products)
    assert {:error, :not_found} = attach(c, envelope)
    assert stored(b) == []

    sql(
      "UPDATE public.mixer_build_reservations SET held=false,terminal_event_id='done' WHERE build_record_id=$1",
      [b.id]
    )

    sql(
      "UPDATE public.mixer_build_coordinator_leases SET owner_id=NULL,expires_at=NULL WHERE build_record_id=$1",
      [b.id]
    )

    assert {:error, :artifact_invalid} = attach(c, envelope)

    [app, symbols, inventory] = b.products
    retain!(c.root, b.operation, [app, inventory])
    assert {:error, :artifact_invalid} = attach(c, envelope)
    assert stored(b) == []

    retain!(c.root, b.operation, [symbols])
    assert {:ok, :attached} = attach(c, envelope)
  end

  test "a newly trusted but different valid envelope cannot replace the attached bytes", c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)
    original = envelope(c, b)
    assert {:ok, :attached} = attach(c, original)

    {new_spki, new_key} = keypair()

    Application.put_env(:mixer_hosted, :native_development_attestation, %{
      origin: @origin,
      public_spki_der: new_spki
    })

    changed = envelope(%{c | spki: new_spki, key: new_key}, b)
    assert changed != original
    assert {:error, :immutable_conflict} = attach(c, changed)
    assert stored(b) == [[2, 1, b.operation, @binding, sha(c.spki), @origin, original]]
  end

  test "a changed admission epoch or revoked membership after the first committed snapshot denies attachment",
       c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)
    envelope = envelope(c, b)

    after_snapshot_commit(
      fn ->
        sql(
          "UPDATE public.mixer_build_coordinator_leases SET epoch=epoch+1 WHERE build_record_id=$1",
          [b.id]
        )
      end,
      fn ->
        assert {:error, :conflict} = attach(c, envelope)
      end
    )

    assert stored(b) == []

    try do
      after_snapshot_commit(
        fn ->
          sql("UPDATE public.mixer_authz_memberships SET active=false WHERE id='developer'")
        end,
        fn ->
          assert {:error, :not_found} = attach(c, envelope)
        end
      )

      assert stored(b) == []
    after
      sql("UPDATE public.mixer_authz_memberships SET active=true WHERE id='developer'")
    end
  end

  test "a replacement record under the same customer selection cannot inherit the attachment",
       c do
    original = completed!(c.selection)
    retain!(c.root, original.operation, original.products)
    signed = envelope(c, original)

    after_snapshot_commit(
      fn ->
        sql("DELETE FROM public.mixer_build_coordinator_leases WHERE build_record_id=$1", [
          original.id
        ])

        sql("DELETE FROM public.mixer_build_reservations WHERE build_record_id=$1", [original.id])
        sql("DELETE FROM public.mixer_builds WHERE id=$1", [original.id])
        Process.put({__MODULE__, :replacement}, completed!(c.selection))
      end,
      fn -> assert {:error, :conflict} = attach(c, signed) end
    )

    replacement = Process.delete({__MODULE__, :replacement})
    assert replacement.operation != original.operation
    assert envelope(c, replacement) == signed
    assert stored(original) == []
    assert stored(replacement) == []
    assert {:error, :artifact_invalid} = attach(c, signed)
  end

  test "losing the write context after SQL inserts rolls back the entire attachment", c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)

    sql("""
    CREATE FUNCTION public.fixture_invalidate_context() RETURNS trigger LANGUAGE plpgsql AS $fn$
    BEGIN
      PERFORM set_config('mixer.authz.transaction_marker','',true);
      RETURN NEW;
    END
    $fn$
    """)

    sql(
      "CREATE TRIGGER fixture_invalidate_context AFTER INSERT ON #{@table} FOR EACH ROW EXECUTE FUNCTION public.fixture_invalidate_context()"
    )

    try do
      assert {:error, :authorization_unavailable} = attach(c, envelope(c, b))
      assert stored(b) == []
    after
      sql("DROP TRIGGER fixture_invalidate_context ON #{@table}")
      sql("DROP FUNCTION public.fixture_invalidate_context()")
    end

    assert {:ok, :attached} = attach(c, envelope(c, b))
  end

  test "only the fixture writer can call the function and it has no relation privileges", c do
    b = completed!(c.selection)
    retain!(c.root, b.operation, b.products)

    assert sql("SELECT has_function_privilege('attestation_fixture_reader',$1,'EXECUTE')", [
             @entry
           ]).rows ==
             [[false]]

    for sql_text <- [
          "SELECT * FROM #{@table}",
          "INSERT INTO #{@table} DEFAULT VALUES",
          "UPDATE #{@table} SET attempt=2",
          "DELETE FROM #{@table}",
          "SELECT * FROM public.mixer_builds",
          "SELECT * FROM public.mixer_build_reservations",
          "SELECT * FROM public.mixer_build_coordinator_leases"
        ] do
      assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
               Ecto.Adapters.SQL.query(AttestationRepo, sql_text, [], log: false)
    end

    assert Ecto.Adapters.SQL.query!(
             AttestationRepo,
             "SELECT public.mixer_native_development_attestation_v1('x','x','x','x',NULL,NULL,NULL,NULL,NULL,NULL)",
             [],
             log: false
           ).rows == [[nil]]

    sql("GRANT EXECUTE ON FUNCTION #{@entry} TO attestation_fixture_reader")

    try do
      assert {:error, :authorization_unavailable} = attach(c, envelope(c, b))
      assert stored(b) == []
    after
      sql("REVOKE EXECUTE ON FUNCTION #{@entry} FROM attestation_fixture_reader")
    end
  end

  defp completed!(s, opts \\ []) do
    products = products()

    artifacts =
      Enum.map(products, fn {kind, bytes} ->
        %ArtifactRef{kind: kind, sha256: sha(bytes), size_bytes: byte_size(bytes)}
      end)

    spec =
      s
      |> Map.delete(:source_sha256)
      |> Map.merge(%{
        platform: :ios,
        source: %{kind: :revision, sha256: s.source_sha256, reference: "pinned"}
      })

    key = "request-" <> s.build_id

    {:ok, journal, queued} =
      Journal.new(spec, %{max_attempts: 2, timeout_ms: 1_000, retry_backoff_ms: 0}, key, 0)

    {journal, queued} = if opts[:retry], do: retry(journal, queued), else: {journal, queued}
    {:ok, ref} = Lifecycle.worker_ref(queued)
    {:ok, journal, _, :applied} = Journal.append(journal, "start", %{type: :start, ref: ref}, 10)

    result = %{outcome: :native_succeeded, artifacts: artifacts}

    {:ok, journal, _, :applied} =
      Journal.append(journal, "done", %{type: :completed, ref: ref, result: result}, 11)

    revision = length(journal["events"])
    uuid = Ecto.UUID.generate()
    id = Ecto.UUID.dump!(uuid)
    held = opts[:held] || false

    sql(
      """
      INSERT INTO public.mixer_builds
        (id,organization_id,project_id,application_id,build_id,platform,request_key,revision,journal,inserted_at,updated_at)
      VALUES ($1,$2,$3,$4,$5,'ios',$6,$7,$8,now(),now())
      """,
      [id, s.organization_id, s.project_id, s.application_id, s.build_id, key, revision, journal]
    )

    sql(
      "INSERT INTO public.mixer_build_capacities VALUES ($1,'ios',4,0) ON CONFLICT DO NOTHING",
      [s.organization_id]
    )

    sql(
      """
      INSERT INTO public.mixer_build_reservations VALUES ($1,$2,'ios',$3,$4,$5,CASE WHEN $5 THEN NULL ELSE 'done' END)
      """,
      [id, s.organization_id, ref.attempt, ref.fence, held]
    )

    sql(
      """
      INSERT INTO public.mixer_build_coordinator_leases VALUES
        ($1,CASE WHEN $2 THEN 'fixture-worker' END,1,CASE WHEN $2 THEN timezone('UTC',now()) END)
      """,
      [id, held]
    )

    %{
      id: id,
      journal: journal,
      revision: revision,
      attempt: ref.attempt,
      operation: Dispatch.operation_id(uuid, ref),
      products: products,
      artifacts: artifacts,
      selection: s
    }
  end

  defp retry(journal, queued) do
    {:ok, ref} = Lifecycle.worker_ref(queued)
    {:ok, journal, _, :applied} = Journal.append(journal, "first", %{type: :start, ref: ref}, 1)

    failure = %{
      outcome: :failed,
      class: :infrastructure,
      code: :worker_lost,
      diagnostic_sha256: sha("first")
    }

    {:ok, journal, _, :applied} =
      Journal.append(journal, "failed", %{type: :completed, ref: ref, result: failure}, 2)

    {:ok, journal, queued, :applied} = Journal.append(journal, "retry", %{type: :retry}, 3)
    {journal, queued}
  end

  defp products do
    archive = fn kind ->
      header = Jason.encode!(%{version: 1, kind: Atom.to_string(kind), binding: @binding})
      {kind, <<"MXNATIVE1\n", byte_size(header)::64, header::binary, "archive">>}
    end

    app = archive.(:unsigned_native_binary)
    symbols = archive.(:debug_symbols)

    parent = fn {kind, bytes} ->
      %{kind: Atom.to_string(kind), sha256: sha(bytes), sizeBytes: byte_size(bytes)}
    end

    inventory =
      Jason.encode!(%{
        kind: "resource_inventory",
        version: 1,
        parentApp: parent.(app),
        parentSymbols: parent.(symbols),
        bindingSHA256: @binding
      })

    [app, symbols, {:resource_inventory, inventory}]
  end

  defp retain!(root, operation, products) do
    store = Path.join([root, operation, "native"])
    File.mkdir_p!(store)

    for {_kind, bytes} <- products do
      path = Path.join(store, sha(bytes))
      File.write!(path, bytes, [:exclusive])
      File.chmod!(path, 0o444)
    end
  end

  defp envelope(c, b, opts \\ []) do
    s = b.selection
    profile = "mixer.native-build.ios-simulator.development.v1"

    statement =
      Jason.OrderedObject.new(
        profile: profile,
        origin: Keyword.get(opts, :origin, @origin),
        keyId: sha(c.spki),
        selection:
          Jason.OrderedObject.new(
            organizationId: s.organization_id,
            projectId: s.project_id,
            applicationId: s.application_id,
            buildId: s.build_id,
            platform: s.platform,
            sourceSha256: s.source_sha256,
            toolchainLockSha256: s.toolchain_lock_sha256,
            buildDefinitionSha256: s.build_definition_sha256
          ),
        provenance:
          Jason.OrderedObject.new(
            journalRevision: Keyword.get(opts, :revision, b.revision),
            attempt: Keyword.get(opts, :attempt, b.attempt),
            nativeBindingSha256: @binding
          ),
        subjects:
          Enum.map(Keyword.get(opts, :artifacts, b.artifacts), fn a ->
            Jason.OrderedObject.new(
              kind: Atom.to_string(a.kind),
              sha256: a.sha256,
              sizeBytes: a.size_bytes
            )
          end)
      )
      |> Jason.encode!()

    sig = :crypto.sign(:eddsa, :none, profile <> <<0>> <> statement, [c.key, :ed25519])
    ~s({"statement":#{statement},"signature":"#{Base.encode64(sig)}"})
  end

  defp keypair do
    {pub, priv} = :crypto.generate_key(:eddsa, :ed25519)
    {Base.decode16!("302A300506032B6570032100") <> pub, priv}
  end

  defp sha(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)

  defp attach(c, envelope),
    do: CustomerBuilds.attach_native_development_attestation(c.identity, c.selection, envelope)

  defp stored(b) do
    sql(
      """
      SELECT journal_revision,attempt,worker_operation_id,native_binding_sha256,signer_key_sha256,
        signing_origin,envelope FROM #{@table} WHERE build_record_id=$1
      """,
      [b.id]
    ).rows
  end

  defp after_snapshot_commit(change, attach) do
    tag = make_ref()
    key = {__MODULE__, tag}
    owner = self()
    event = AttestationRepo.config()[:telemetry_prefix] ++ [:query]

    handler = fn _, _, metadata, _ ->
      if self() == owner and metadata.query == "commit" and !Process.get(key) do
        change.()
        Process.put(key, true)
      end
    end

    :ok = :telemetry.attach(tag, event, handler, nil)

    try do
      attach.()
      assert Process.get(key)
    after
      :telemetry.detach(tag)
      Process.delete(key)
    end
  end

  defp identity(subject \\ "developer") do
    now = System.system_time(:second)

    %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://fixture.example",
      subject: subject,
      client_id: "fixture",
      credential_ref: subject,
      issued_at: now - 20,
      expires_at: now + 300,
      identity_class: :human,
      scopes: ["mixer.build.attest"]
    }
  end

  defp seed_identity! do
    sql(
      "INSERT INTO public.mixer_authz_profiles (id,version,issuer,client_id,identity_class,active) VALUES ('profile',1,'https://fixture.example','fixture','human',true)"
    )

    for org <- ["org-a", "org-b"] do
      sql("INSERT INTO public.mixer_authz_organizations VALUES ($1,true)", [org])
      sql("INSERT INTO public.mixer_authz_projects VALUES ($1,'project',true)", [org])
      sql("INSERT INTO public.mixer_authz_applications VALUES ($1,'project','app',true)", [org])
      sql("INSERT INTO public.mixer_authz_organization_heads VALUES ($1,1)", [org])
      sql("INSERT INTO public.mixer_authz_project_heads VALUES ($1,'project',1)", [org])
    end

    for role <- ["developer", "viewer"] do
      sql("INSERT INTO public.mixer_authz_principals VALUES ($1,'human',true,0,1)", [role])

      sql(
        "INSERT INTO public.mixer_authz_bindings (profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('profile',1,$1,'human',$1,true)",
        [role]
      )

      sql("INSERT INTO public.mixer_authz_families VALUES ($1,'profile',1,$1,true,0,NULL,1)", [
        role
      ])

      sql(
        "INSERT INTO public.mixer_authz_credentials VALUES ('profile',1,$1,$1,$1,true,0,NULL,1)",
        [role]
      )

      sql(
        "INSERT INTO public.mixer_authz_memberships VALUES ($1,$1,'org-a','project','exact_project',$1,true,0,NULL,1)",
        [role]
      )
    end
  end

  defp put_config(name, value) do
    prior = Application.fetch_env(:mixer_hosted, name)
    Application.put_env(:mixer_hosted, name, value)

    on_exit(fn ->
      case prior do
        {:ok, config} -> Application.put_env(:mixer_hosted, name, config)
        :error -> Application.delete_env(:mixer_hosted, name)
      end
    end)
  end

  defp sql(statement, args \\ []),
    do: Ecto.Adapters.SQL.query!(Admin, statement, args, log: false)
end
