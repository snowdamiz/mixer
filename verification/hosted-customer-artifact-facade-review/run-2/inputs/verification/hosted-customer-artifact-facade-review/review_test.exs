ExUnit.start(seed: 0, max_cases: 1)
Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Application.ensure_all_started(:jason)

defmodule FacadeReview.Admin do
  use Ecto.Repo, otp_app: :facade_review, adapter: Ecto.Adapters.Postgres
end

defmodule FacadeReview.Owner do
  use Ecto.Repo, otp_app: :facade_review, adapter: Ecto.Adapters.Postgres
end

defmodule FacadeReview.Runtime do
  use Ecto.Repo, otp_app: :facade_review, adapter: Ecto.Adapters.Postgres

  # Test-only trusted Repo hook: enqueue a real deferred FK failure after the
  # complete authorization callback returns. No ordinary product code changes.
  def prepare_transaction(fun, opts) when is_function(fun, 0) do
    wrapped = fn ->
      value = fun.()

      if Process.get(:facade_review_fail_commit) do
        send(self(), {:facade_review_callback_complete, value})
        Ecto.Adapters.SQL.query!(__MODULE__, "INSERT INTO public.review_commit_child VALUES (1)", [])
      end

      value
    end

    {wrapped, opts}
  end
end

defmodule FacadeReview do
  use ExUnit.Case, async: false
  alias MixerHosted.CustomerArtifacts, as: API
  alias MixerHosted.CustomerArtifacts.Schema
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.{ArtifactAdmission, ArtifactCBOR}
  alias FacadeReview.{Admin, Owner, Runtime}

  def sql(query, args \\ []), do: Ecto.Adapters.SQL.query!(Admin, query, args, log: false)
  def route, do: %{organization_id: "review-org", project_id: "review-project"}
  def meta, do: %{reason: "independent boundary probe", source_ip: "2001:db8::1234"}
  def now, do: System.system_time(:second)

  def identity(changes \\ %{}) do
    struct!(VerifiedIdentity, Map.merge(%{
      profile_id: "review-profile", profile_version: 1, issuer: "https://identity.review.invalid",
      subject: "review-subject", client_id: "review-client", credential_ref: "review-token",
      issued_at: now() - 10, expires_at: now() + 600, identity_class: :human,
      scopes: ~w(mixer.artifact.upload mixer.artifact.read mixer.audit.read)
    }, changes))
  end

  def signed_data(platform \\ "android", app \\ "notes", environment \\ "review") do
    fixture = Path.join(System.fetch_env!("FACADE_REVIEW_INPUTS"), "services/protocol/testdata/signed-release-v3.json") |> File.read!() |> Jason.decode!()
    {public, private} = :crypto.generate_key(:eddsa, :ed25519)
    scope = %{"organization" => "review-org", "project" => "review-project", "app" => app, "environment" => environment, "platform" => platform}
    manifest = fixture["signed_manifest"]["manifest"] |> Map.put("scope", scope) |> Map.put("key_id", "independent-review-key") |> Map.put("release_id", "independent-review-release")
    host = Map.put(fixture["host"], "scope", scope)
    {:ok, cbor} = ArtifactCBOR.encode(manifest)
    signature = :crypto.sign(:eddsa, :none, "mixer.artifact.v3\0" <> cbor, [private, :ed25519]) |> Base.encode64()
    bytes = Jason.encode!(%{"signed_manifest" => %{"manifest" => manifest, "signature" => signature}, "payload" => fixture["payload"]})
    roots = [%{"key_id" => "independent-review-key", "public_key" => public, "scope" => scope, "artifact" => true, "assignment" => false, "revoked" => false, "not_before_unix" => 0, "not_after_unix" => 0}]
    config = %{repo: Runtime, host: host, roots: roots}
    {:ok, checked} = ArtifactAdmission.admit(bytes, host, roots, now())
    {checked, config}
  end

  def upload(checked, key \\ "review-key", id \\ identity(), metadata \\ meta()), do: API.upload(id, route(), key, checked.envelope_bytes, metadata)
  def read(checked, id \\ identity()), do: API.read(id, route(), checked.manifest_sha256, meta())
  def audit(id \\ identity()), do: API.audit(id, route(), 0, 100, meta())
  def count, do: sql("SELECT (SELECT count(*) FROM public.mixer_customer_artifacts),(SELECT count(*) FROM public.mixer_customer_audit_events),(SELECT count(*) FROM public.mixer_customer_idempotency)").rows

  setup_all do
    settings = [hostname: "127.0.0.1", port: String.to_integer(System.fetch_env!("FACADE_REVIEW_PORT")), database: "facade_review", ssl: false, log: false]
    start_supervised!({Admin, settings ++ [username: "review_admin", pool_size: 3]})
    start_supervised!({Owner, settings ++ [username: "review_admin", pool_size: 2, after_connect: fn connection -> Postgrex.query!(connection, "SET ROLE review_owner", []) end]})
    start_supervised!({Runtime, settings ++ [username: "review_runtime", pool_size: 4]})
    for {version, module} <- [{20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization}, {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions}, {20_261_025_000_005, MixerHosted.Repo.Migrations.AddCustomerArtifactStorage}] do
      assert :ok = Ecto.Migrator.up(Owner, version, module, log: false)
    end
    for table <- ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships), do: sql("GRANT SELECT ON public.mixer_authz_#{table} TO review_runtime")
    for table <- ~w(profiles principals families credentials organization_heads project_heads), do: sql("GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO review_runtime")
    for table <- ~w(artifacts audit_events idempotency), do: sql("GRANT SELECT,INSERT ON public.mixer_customer_#{table} TO review_runtime")
    sql("GRANT SELECT,UPDATE(sequence,event_sha256,state_sha256) ON public.mixer_customer_artifact_heads TO review_runtime")
    for function <- ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists), do: sql("GRANT EXECUTE ON FUNCTION public.#{function}(#{Schema.signatures()[function]}) TO review_runtime")
    sql("CREATE TABLE public.review_commit_parent(id integer PRIMARY KEY)")
    sql("CREATE TABLE public.review_commit_child(parent_id integer REFERENCES public.review_commit_parent(id) DEFERRABLE INITIALLY DEFERRED)")
    sql("GRANT INSERT ON public.review_commit_child TO review_runtime")
    :ok
  end

  setup do
    sql("TRUNCATE public.mixer_customer_idempotency,public.mixer_customer_audit_events,public.mixer_customer_artifacts,public.mixer_customer_artifact_heads,public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_organizations CASCADE")
    for statement <- [
      "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ('review-profile',1,'https://identity.review.invalid','review-client','human',true)",
      "INSERT INTO public.mixer_authz_principals VALUES ('review-person','human',true,0,2),('review-other','human',true,0,2)",
      "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ('review-profile',1,'review-subject','human','review-person',true),('review-profile',1,'review-other-subject','human','review-other',true)",
      "INSERT INTO public.mixer_authz_families VALUES ('review-family','review-profile',1,'review-person',true,0,NULL,3),('review-other-family','review-profile',1,'review-other',true,0,NULL,3)",
      "INSERT INTO public.mixer_authz_credentials VALUES ('review-profile',1,'review-token','review-person','review-family',true,0,NULL,4),('review-profile',1,'review-other-token','review-other','review-other-family',true,0,NULL,4)",
      "INSERT INTO public.mixer_authz_organizations VALUES ('review-org',true)",
      "INSERT INTO public.mixer_authz_projects VALUES ('review-org','review-project',true)",
      "INSERT INTO public.mixer_authz_applications VALUES ('review-org','review-project','notes',true),('review-org','review-project','other-app',true)",
      "INSERT INTO public.mixer_authz_environments VALUES ('review-org','review-project','notes','review',true),('review-org','review-project','other-app','other-env',true)",
      "INSERT INTO public.mixer_authz_organization_heads VALUES ('review-org',5)",
      "INSERT INTO public.mixer_authz_project_heads VALUES ('review-org','review-project',6)",
      "INSERT INTO public.mixer_authz_memberships VALUES ('review-member','review-person','review-org','review-project','exact_project','developer',true,0,NULL,7),('review-other-member','review-other','review-org','review-project','exact_project','developer',true,0,NULL,7)"
    ], do: sql(statement)
    {:ok, genesis} = MixerHosted.Audit.CustomerArtifactEvent.genesis("review-org", "review-project")
    sql("INSERT INTO public.mixer_customer_artifact_heads VALUES ('review-org','review-project',0,'',$1)", [genesis])
    {checked, config} = signed_data()
    Application.put_env(:mixer_hosted, API, config)
    on_exit(fn -> Application.delete_env(:mixer_hosted, API) end)
    %{checked: checked, config: config}
  end

  test "independently signed Android non-FieldLog target stores reads and audits exact bytes", %{checked: checked} do
    assert {:ok, receipt} = upload(checked)
    assert receipt == %{status: 201, manifest_sha256: checked.manifest_sha256, payload_sha256: checked.payload_sha256, event_sequence: 1}
    refute Runtime.in_transaction?()
    refute MixerHosted.Authorization.Transaction.Context.active?()
    assert {:ok, %{envelope_bytes: bytes}} = read(checked)
    assert bytes == checked.envelope_bytes
    assert {:ok, %{events: [event], next_after_sequence: 1}} = audit()
    assert event["target"] |> Enum.take(5) == ["review-org", "review-project", "notes", "review", "android"]
    assert hd(event["actor"]) == "review-person"
    assert event["source_ip"] == [meta().source_ip]
    assert byte_size(event["request_id"]) == 32
    assert count() == [[1, 1, 1]]
  end

  test "identity shape and exact scope are checked before malformed body admission", %{checked: checked} do
    for bad <- [nil, %{}, Map.from_struct(identity()), Map.put(identity(), :repo, Runtime), identity(%{expires_at: now()}), identity(%{scopes: ["mixer.artifact.upload", "mixer.artifact.upload"]})] do
      assert {:error, :unauthenticated} = API.upload(bad, route(), "key", :poison_body, meta())
      assert {:error, :unauthenticated} = read(checked, bad)
      assert {:error, :unauthenticated} = audit(bad)
    end
    no_exact = identity(%{scopes: ~w(mixer.artifact.upload.other mixer.artifact.read.other mixer.audit.read.other)})
    assert {:error, :permission_denied} = API.upload(no_exact, route(), "key", :poison_body, meta())
    assert {:error, :permission_denied} = read(checked, no_exact)
    assert {:error, :permission_denied} = audit(no_exact)
    assert count() == [[0, 0, 0]]
  end

  test "closed route and metadata reject all authority and identity injection keys", %{checked: checked} do
    for field <- [:repo, :clock, :roots, :host, :request_id, :actor, :callback, :identity, :application_id, :environment_id] do
      assert {:error, :invalid_request} = API.upload(identity(), Map.put(route(), field, Runtime), "key", checked.envelope_bytes, meta())
      assert {:error, :invalid_request} = API.read(identity(), Map.put(route(), field, Runtime), checked.manifest_sha256, meta())
      assert {:error, :invalid_request} = API.audit(identity(), Map.put(route(), field, Runtime), 0, 1, meta())
      assert {:error, :invalid_request} = upload(checked, "key", identity(), Map.put(meta(), field, Runtime))
      assert {:error, :invalid_request} = API.read(identity(), route(), checked.manifest_sha256, Map.put(meta(), field, Runtime))
      assert {:error, :invalid_request} = API.audit(identity(), route(), 0, 1, Map.put(meta(), field, Runtime))
    end
    assert count() == [[0, 0, 0]]
  end

  test "canonical addresses and UTF8 byte bounds apply across operations", %{checked: checked} do
    for metadata <- [%{meta() | reason: <<255>>}, %{meta() | reason: String.duplicate("é", 257)}, %{meta() | source_ip: "2001:0db8::1234"}, %{meta() | source_ip: "2001:DB8::1234"}, %{meta() | source_ip: "127.01.2.3"}, %{meta() | source_ip: "127.0.0.1:443"}, %{meta() | source_ip: {127, 0, 0, 1}}, %{meta() | source_ip: <<255>>}] do
      assert {:error, :invalid_request} = upload(checked, "key", identity(), metadata)
      assert {:error, :invalid_request} = API.read(identity(), route(), checked.manifest_sha256, metadata)
      assert {:error, :invalid_request} = API.audit(identity(), route(), 0, 1, metadata)
    end
    assert {:ok, _} = upload(checked, String.duplicate("K", 128), identity(), %{reason: String.duplicate("é", 256), source_ip: "127.0.0.1"})
  end

  test "staged read refuses current host app environment platform and runtime mismatches", %{checked: checked, config: config} do
    assert {:ok, _} = upload(checked)
    for host <- [put_in(config.host, ["scope", "app"], "other-app"), put_in(config.host, ["scope", "environment"], "other-env"), put_in(config.host, ["scope", "platform"], "ios"), Map.put(config.host, "runtime", String.duplicate("1", 64))] do
      Application.put_env(:mixer_hosted, API, %{config | host: host})
      assert {:error, :storage_unavailable} = read(checked)
    end
    Application.put_env(:mixer_hosted, API, config)
    assert {:ok, _} = read(checked)
  end

  test "a separately signed alternate actual app environment is resolved without caller fields" do
    {alternate, config} = signed_data("ios", "other-app", "other-env")
    Application.put_env(:mixer_hosted, API, config)
    assert {:ok, _} = upload(alternate)
    assert {:ok, %{envelope_bytes: bytes}} = read(alternate)
    assert bytes == alternate.envelope_bytes
    assert {:ok, %{events: [event]}} = audit()
    assert event["target"] |> Enum.take(5) == ["review-org", "review-project", "other-app", "other-env", "ios"]
  end

  test "fresh authority applies to same-key retry and changed current roots", %{checked: checked, config: config} do
    assert {:ok, first} = upload(checked)
    assert {:ok, ^first} = upload(checked)
    sql("UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='review-token'")
    assert {:error, :unauthenticated} = upload(checked)
    assert {:error, :unauthenticated} = read(checked)
    assert {:error, :unauthenticated} = audit()
    sql("UPDATE public.mixer_authz_credentials SET active=true,revision=revision+1 WHERE reference='review-token'")
    Application.put_env(:mixer_hosted, API, %{config | roots: Enum.map(config.roots, &Map.put(&1, "revoked", true))})
    assert {:error, :invalid_request} = upload(checked)
    assert {:error, :storage_unavailable} = read(checked)
    assert count() == [[1, 1, 1]]
  end

  test "same-key principal request binding and concurrent retry do not duplicate events", %{checked: checked} do
    tasks = for _ <- 1..3, do: Task.async(fn -> upload(checked) end)
    assert [{:ok, first}] = tasks |> Enum.map(&Task.await(&1, 10_000)) |> Enum.uniq()
    other = identity(%{subject: "review-other-subject", credential_ref: "review-other-token"})
    assert {:error, :idempotency_conflict} = upload(checked, "review-key", other)
    assert {:error, :idempotency_conflict} = upload(checked, "review-key", identity(), %{meta() | reason: "changed"})
    assert {:ok, ^first} = upload(checked, "review-key", identity(), %{meta() | source_ip: nil})
    assert count() == [[1, 1, 1]]
  end

  test "real PostgreSQL COMMIT failure cannot escape as public success", %{checked: checked} do
    Process.put(:facade_review_fail_commit, true)
    try do
      assert {:error, :authorization_unavailable} = upload(checked)
      assert_received {:facade_review_callback_complete, {:ok, {:ok, %{status: 201}}}}
    after
      Process.delete(:facade_review_fail_commit)
    end
    refute Runtime.in_transaction?()
    refute MixerHosted.Authorization.Transaction.Context.active?()
    assert count() == [[0, 0, 0]]
    assert {:ok, _} = upload(checked)
    assert count() == [[1, 1, 1]]
  end

  test "signature corruption and signed foreign project never produce effects", %{checked: checked, config: config} do
    object = Jason.decode!(checked.envelope_bytes)
    corrupt = put_in(object, ["signed_manifest", "signature"], Base.encode64(<<0::512>>)) |> Jason.encode!()
    assert {:error, :invalid_request} = API.upload(identity(), route(), "key", corrupt, meta())
    bad_config = %{config | host: put_in(config.host, ["scope", "project"], "foreign-project")}
    Application.put_env(:mixer_hosted, API, bad_config)
    assert {:error, :not_found} = upload(checked)
    assert {:error, :not_found} = read(checked)
    assert {:error, :not_found} = audit()
    assert count() == [[0, 0, 0]]
  end

  test "missing and malformed server configuration have closed returns", %{checked: checked, config: config} do
    Application.delete_env(:mixer_hosted, API)
    assert {:error, :storage_unavailable} = upload(checked)
    assert {:error, :storage_unavailable} = read(checked)
    assert {:error, :storage_unavailable} = audit()
    for invalid <- [%{config | repo: nil}, %{config | repo: String}, Map.put(config, :clock, fn -> 0 end), %{config | roots: []}, %{config | host: %{}}] do
      Application.put_env(:mixer_hosted, API, invalid)
      assert {:error, :storage_unavailable} = upload(checked)
      assert {:error, :storage_unavailable} = read(checked)
      assert {:error, :storage_unavailable} = audit()
    end
  end

  test "audit pages and manifest digest are bounded and reads add no upload events", %{checked: checked} do
    assert {:ok, _} = upload(checked)
    assert {:ok, _} = read(checked)
    assert {:ok, %{events: [], next_after_sequence: 9_007_199_254_740_991}} = API.audit(identity(), route(), 9_007_199_254_740_991, 100, meta())
    for {cursor, limit} <- [{-1, 1}, {9_007_199_254_740_992, 1}, {0, 0}, {0, 101}, {0.0, 1}, {nil, 1}], do: assert({:error, :invalid_request} == API.audit(identity(), route(), cursor, limit, meta()))
    for digest <- [String.upcase(checked.manifest_sha256), String.duplicate("a", 65), <<255>>, nil], do: assert({:error, :invalid_request} == API.read(identity(), route(), digest, meta()))
    assert count() == [[1, 1, 1]]
  end
end
