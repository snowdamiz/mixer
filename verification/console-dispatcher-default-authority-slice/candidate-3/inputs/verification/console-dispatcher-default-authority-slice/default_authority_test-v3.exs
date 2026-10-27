defmodule MixerHosted.DispatcherDefaultAuthorityFixture.Admin do
  use Ecto.Repo, otp_app: :dispatcher_default_authority_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.DispatcherDefaultAuthorityFixture.Migration do
  use Ecto.Repo, otp_app: :dispatcher_default_authority_fixture, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHostedWeb.DispatcherDefaultAuthorityTest do
  use ExUnit.Case, async: false

  alias MixerHosted.DispatcherDefaultAuthorityFixture.{Admin, Migration}
  alias MixerHosted.Identity.{Admission, ConfiguredVerifier, KeyOwner, TLSFixture, VerifiedIdentity}
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Repo
  alias MixerHostedWeb.BrowserWorkspaceDispatcher, as: Dispatcher

  @profile %{
    profile_id: "dispatcher-default-profile",
    profile_version: 1,
    issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api",
    client_id: "reviewed-client",
    identity_class: :human,
    enabled: true
  }
  @metadata %{request_id: "0123456789abcdef0123456789abcdef"}
  @page %{limit: 50, cursor: nil}
  @workers MixerHosted.DispatcherDefaultAuthorityFixture.Workers
  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @settings ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase directory_mode)

  setup_all do
    assert Process.whereis(Repo) == nil
    assert Process.whereis(KeyOwner) == nil
    assert :persistent_term.get({Admission, KeyOwner}, :absent) == :absent
    refute List.keymember?(Application.started_applications(), :mixer_hosted, 0)

    for app <- [:ecto_sql, :postgrex, :jose, :mint, :ssl],
        do: assert(match?({:ok, _}, Application.ensure_all_started(app)))

    settings = [
      hostname: "127.0.0.1",
      port: String.to_integer(System.fetch_env!("MIXER_DISPATCHER_DEFAULT_TEST_PORT")),
      database: "mixer_dispatcher_default_authority",
      ssl: false,
      log: false
    ]

    admin = start_supervised!({Admin, settings ++ [username: "dispatcher_default_admin", pool_size: 2]}, restart: :temporary)

    migration =
      start_supervised!(
        {Migration,
         settings ++
           [
             username: "dispatcher_default_admin",
             pool_size: 2,
             after_connect: fn connection ->
               Postgrex.query!(connection, "SET ROLE dispatcher_default_owner", [])
             end
           ]},
        restart: :temporary
      )

    for {version, module} <- [
          {20_261_025_000_003, MixerHosted.Repo.Migrations.AddCustomerAuthorization},
          {20_261_025_000_004, MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
          {20_261_025_000_006, MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery}
        ],
        do: assert(:ok == Ecto.Migrator.up(Migration, version, module, log: false))

    for table <- @tables,
        do: sql("GRANT SELECT ON public.mixer_authz_#{table} TO dispatcher_default_runtime")

    for table <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          sql(
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{table}() TO dispatcher_default_runtime"
          )

    repo =
      start_supervised!(
        {Repo,
         settings ++
           [
             username: "dispatcher_default_runtime",
             pool_size: 1,
             telemetry_prefix: [:dispatcher_default_authority]
           ]},
        restart: :temporary
      )

    assert [["dispatcher_default_runtime", "dispatcher_default_runtime", false, false, false, false, false]] ==
             Ecto.Adapters.SQL.query!(
               Repo,
               "SELECT current_user,session_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,pg_has_role(current_user,'dispatcher_default_owner','member') FROM pg_roles WHERE rolname=current_user",
               [],
               log: false
             ).rows

    assert [[13, true, true, true]] ==
             sql(
               "SELECT count(*),bool_and(relrowsecurity),bool_and(relforcerowsecurity),bool_and(pg_get_userbyid(relowner)='dispatcher_default_owner') FROM pg_class WHERE relnamespace='public'::regnamespace AND relname = ANY($1::text[])",
               [Enum.map(@tables, &("mixer_authz_" <> &1))]
             ).rows

    fixture = start_supervised!(TLSFixture, restart: :temporary)
    authority = GenServer.call(fixture, :authority)
    assert authority.ip == {127, 0, 0, 1}
    write_json("component-start.json", %{fixture_tls_port: authority.port, ephemeral_tls_key_directory_removed: TLSFixture.info(fixture).key_dir_removed})
    key = JOSE.JWK.generate_key({:rsa, 2048})
    wrong_key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "dispatcher-default-key", "alg" => "RS256", "use" => "sig"})

    :ok = TLSFixture.configure(fixture, {:body, Jason.encode!(%{"keys" => [public]})})
    workers = start_supervised!({DynamicSupervisor, strategy: :one_for_one, name: @workers}, restart: :temporary)

    options = [
      name: KeyOwner,
      manifest: [
        %{
          profile: @profile,
          jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
          transport: :hosted_https
        }
      ],
      generation: 1,
      binding: @profile.profile_id,
      ca_roots: [authority.ca],
      resolvers: [{{127, 0, 0, 1}, 9}],
      worker_supervisor: @workers,
      fixture: Map.take(authority, [:ip, :port])
    ]

    owner = start_supervised!(%{id: KeyOwner, start: {KeyOwner, :start_fixture, [options]}, restart: :temporary, shutdown: 2_000})
    assert {:ok, %VerifiedIdentity{}} = ConfiguredVerifier.authenticate(token(key), now())
    initial_tls_info = TLSFixture.info(fixture)

    on_exit(:default_authority_cleanup, fn ->
      info = if Process.alive?(fixture), do: TLSFixture.info(fixture), else: initial_tls_info

      for pid <- [owner, workers, fixture, repo, migration, admin],
          do: if(Process.alive?(pid), do: GenServer.stop(pid, :normal, 2_000))

      cleanup = %{
        owned_components_stopped: Enum.all?([owner, workers, fixture, repo, migration, admin], &(not Process.alive?(&1))),
        default_owner_absent: Process.whereis(KeyOwner) == nil,
        default_repo_absent: Process.whereis(Repo) == nil,
        admission_absent: :persistent_term.get({Admission, KeyOwner}, :absent) == :absent,
        fixture_tls_port: authority.port,
        ephemeral_tls_key_directory_removed: info.key_dir_removed,
        jwks_tls_requests: length(info.requests)
      }

      write_json("component-cleanup.json", cleanup)
      assert cleanup.owned_components_stopped
      assert cleanup.default_owner_absent and cleanup.default_repo_absent and cleanup.admission_absent
      assert cleanup.ephemeral_tls_key_directory_removed
      assert cleanup.jwks_tls_requests >= 1
    end)

    %{key: key, wrong_key: wrong_key, tls_fixture: fixture}
  end

  setup context do
    seed!()
    assert Repo.get_dynamic_repo() === Repo
    assert clean?()
    handler = {__MODULE__, make_ref()}
    :ok = :telemetry.attach(handler, [:dispatcher_default_authority, :query], &__MODULE__.observe_query/4, self())
    on_exit(fn -> :telemetry.detach(handler) end)
    %{token: token(context.key)}
  end

  # Read-only observation of the canonical storage connection check. The event
  # carries only booleans and the public requested tenant, never identity bytes.
  def observe_query(_event, _measurements, %{repo: Repo, query: query, result: {:ok, %{rows: [[pid, transaction, user, session_user | settings]]}}}, owner) do
    if String.starts_with?(query, "SELECT pg_backend_pid(), pg_current_xact_id()::text, current_user::text, session_user::text,") do
      marker = Enum.at(settings, 14)
      ordinary = length(settings) == 20 and Enum.at(settings, 0) == @profile.profile_id and
        Enum.at(settings, 5) == "human" and Enum.at(settings, 13) == "workspace.read" and
        is_binary(marker) and byte_size(marker) == 64 and Enum.at(settings, 17) == "mixer.workspace.read" and
        Enum.at(settings, 18) == "directory"

      send(owner, {:default_repo_transaction_probe, %{
        runtime_role: user == "dispatcher_default_runtime" and session_user == "dispatcher_default_runtime",
        transaction: Repo.in_transaction?() and is_integer(pid) and is_binary(transaction) and transaction != "",
        ordinary_context: ordinary,
        mode: Enum.at(settings, 19),
        organization: Enum.at(settings, 7)
      }})
    end
  end

  def observe_query(_event, _measurements, _metadata, _owner), do: :ok

  test "DA01 actual fixed defaults project only currently authorized database rows", context do
    assert {:ok, %VerifiedIdentity{profile_id: "dispatcher-default-profile", subject: "subject"}} =
             ConfiguredVerifier.authenticate(context.token, now())

    assert %{"organizations" => [%{"id" => "org-a", "display_name" => "  Team * A  ", "organization_roles" => []}], "next_cursor" => nil} =
             dispatch(context.token, {:organizations, @page}, 200)

    assert %{"projects" => [
               %{"organization_id" => "org-a", "id" => "project-a", "display_name" => "Project A", "roles" => ["developer"]},
               %{"organization_id" => "org-a", "id" => "project-b", "display_name" => nil, "roles" => ["viewer"]}
             ], "next_cursor" => nil} = dispatch(context.token, {:projects, "org-a", @page}, 200)

    assert error_code(dispatch(context.token, {:projects, "org-b", @page}, 404)) == "not_found"
    assert error_code(dispatch(context.token, {:projects, "missing", @page}, 404)) == "not_found"
    assert TLSFixture.info(context.tls_fixture).requests != []
    assert clean?()
  end

  test "DA02 real database pages preserve canonical cursors and exact organization bytes", context do
    first = dispatch(context.token, {:projects, "org-a", %{limit: 1, cursor: nil}}, 200)
    assert [%{"id" => "project-a"}] = first["projects"]
    assert first["next_cursor"] == Base.url_encode64(~s({"v":1,"kind":"projects","organization_id":"org-a","after":"project-a"}), padding: false)
    assert %{"projects" => [%{"id" => "project-b"}], "next_cursor" => nil} =
             dispatch(context.token, {:projects, "org-a", %{limit: 1, cursor: first["next_cursor"]}}, 200)

    organization = "team + % / é"
    sql("INSERT INTO public.mixer_authz_organizations VALUES ($1,true,$2)", [organization, "Exact team"])
    sql("INSERT INTO public.mixer_authz_organization_heads VALUES ($1,1)", [organization])
    sql("INSERT INTO public.mixer_authz_projects VALUES ($1,'project-a',true,'Exact project')", [organization])
    sql("INSERT INTO public.mixer_authz_project_heads VALUES ($1,'project-a',1)", [organization])
    member("exact", organization, "project-a", "developer")
    assert %{"projects" => [%{"organization_id" => ^organization, "display_name" => "Exact project"}]} =
             dispatch(context.token, {:projects, organization, @page}, 200)
    assert Dispatcher.dispatch(context.token, {:projects, organization, %{limit: 1, cursor: first["next_cursor"]}}, @metadata) == {:error, :invalid_request}
    assert clean?()
  end

  test "DA03 fixed default verifier rejects invalid signature audience expiry and workspace scope", context do
    for rejected <- [
          token(context.wrong_key),
          token(context.key, %{"aud" => "foreign-api"}),
          token(context.key, %{"iat" => now() - 120, "exp" => now() - 1})
        ] do
      assert error_code(dispatch(rejected, {:organizations, @page}, 401)) == "unauthenticated"
    end

    assert error_code(dispatch(token(context.key, %{"scope" => "mixer.artifact.read"}), {:organizations, @page}, 403)) == "permission_denied"
    assert %{"organizations" => [_]} = dispatch(context.token, {:organizations, @page}, 200)
    assert clean?()
  end

  test "DA04 same valid bearer observes committed role change and membership revocation", context do
    assert %{"projects" => [%{"roles" => ["developer"]}, _]} =
             dispatch(context.token, {:projects, "org-a", @page}, 200)

    mutate_membership!("UPDATE public.mixer_authz_memberships SET role='viewer',revision=revision+1 WHERE id='member-a'")
    assert %{"projects" => [%{"roles" => ["viewer"]}, _]} =
             dispatch(context.token, {:projects, "org-a", @page}, 200)

    mutate_membership!("UPDATE public.mixer_authz_memberships SET active=false,revision=revision+1 WHERE principal_id='person'")
    assert {:ok, %VerifiedIdentity{}} = ConfiguredVerifier.authenticate(context.token, now())
    assert %{"organizations" => [], "next_cursor" => nil} = dispatch(context.token, {:organizations, @page}, 200)
    assert error_code(dispatch(context.token, {:projects, "org-a", @page}, 404)) == "not_found"
    assert clean?()
  end

  test "DA05 current database identity state fences a still cryptographically valid bearer", context do
    for mutation <- [
          "UPDATE public.mixer_authz_profiles SET active=false,state_revision=state_revision+1 WHERE id='dispatcher-default-profile'",
          "UPDATE public.mixer_authz_bindings SET active=false,revision=revision+1 WHERE subject='subject'",
          "UPDATE public.mixer_authz_principals SET active=false,revision=revision+1 WHERE id='person'",
          "UPDATE public.mixer_authz_families SET active=false,revision=revision+1 WHERE id='family'",
          "UPDATE public.mixer_authz_credentials SET active=false,revision=revision+1 WHERE reference='token'",
          "UPDATE public.mixer_authz_credentials SET expires_at=extract(epoch FROM clock_timestamp())::bigint-1,revision=revision+1 WHERE reference='token'"
        ] do
      seed!()
      assert %{"organizations" => [_]} = dispatch(context.token, {:organizations, @page}, 200)
      assert {:ok, :ok} = Admin.transaction(fn -> sql(mutation); :ok end)
      assert {:ok, %VerifiedIdentity{}} = ConfiguredVerifier.authenticate(context.token, now())
      assert error_code(dispatch(context.token, {:organizations, @page}, 401)) == "unauthenticated"
      assert clean?()
    end
  end

  test "DA06 restricted default Repo exposes no workspace rows or mutation authority outside request context", context do
    assert %{"organizations" => [_]} = dispatch(context.token, {:organizations, @page}, 200)
    assert [[0]] == Ecto.Adapters.SQL.query!(Repo, "SELECT count(*) FROM public.mixer_authz_organizations", [], log: false).rows
    assert {:error, %Postgrex.Error{postgres: %{code: :insufficient_privilege}}} =
             Ecto.Adapters.SQL.query(Repo, "UPDATE public.mixer_authz_memberships SET active=false", [], log: false)
    assert clean?()
    assert %{"projects" => [_, _]} = dispatch(context.token, {:projects, "org-a", @page}, 200)
    assert clean?()
  end

  test "DA07 fixed dispatcher refuses a caller transaction or changed dynamic Repo without repairing it", context do
    assert {:ok, "authorization_unavailable"} =
             Repo.transaction(fn ->
               assert Repo.in_transaction?()
               error_code(dispatch(context.token, {:organizations, @page}, 503))
             end)

    assert clean?()
    Repo.put_dynamic_repo(:dispatcher_deliberately_wrong_repo)

    try do
      assert Dispatcher.dispatch(context.token, {:organizations, @page}, @metadata) ==
               {:error, :authorization_unavailable}
      assert Repo.get_dynamic_repo() === :dispatcher_deliberately_wrong_repo
    after
      Repo.put_dynamic_repo(Repo)
    end

    assert %{"organizations" => [_]} = dispatch(context.token, {:organizations, @page}, 200)
    assert clean?()
  end

  defp now, do: System.system_time(:second)
  defp sql(query, params \\ []), do: Ecto.Adapters.SQL.query!(Admin, query, params, log: false)

  defp clean? do
    Repo.get_dynamic_repo() === Repo and not Repo.in_transaction?() and not Context.active?() and
      Process.get({MixerHosted.CustomerWorkspace.Storage, :active}) == nil and gucs_clean?()
  end

  defp gucs_clean? do
    fields = Enum.map_join(@settings, ",", &"COALESCE(current_setting('mixer.authz.#{&1}',true),'')")
    Ecto.Adapters.SQL.query!(Repo, "SELECT " <> fields, [], log: false).rows == [List.duplicate("", 20)]
  end

  defp token(key, changes \\ %{}) do
    claims = Map.merge(%{
      "iss" => @profile.issuer, "aud" => @profile.audience, "sub" => "subject",
      "client_id" => @profile.client_id, "iat" => now() - 2, "exp" => now() + 600,
      "jti" => "token", "scope" => "mixer.workspace.read"
    }, changes)

    JOSE.JWS.sign(key, Jason.encode!(claims), %{"alg" => "RS256", "typ" => "at+jwt", "kid" => "dispatcher-default-key"})
    |> JOSE.JWS.compact()
    |> elem(1)
  end

  defp dispatch(token, request, expected_status) do
    drain_probes()
    assert {:ok, %{status: ^expected_status, headers: headers, body: body} = projection} =
             Dispatcher.dispatch(token, request, @metadata)
    expected = [
      {"cache-control", "no-store"},
      {"content-type", "application/json; charset=utf-8"},
      {"x-request-id", @metadata.request_id}
    ]
    optional = case expected_status do
      401 -> [{"www-authenticate", ~s(Bearer error="invalid_token")}]
      503 -> [{"retry-after", "1"}]
      _ -> []
    end
    assert Enum.sort(Map.keys(projection)) == [:body, :headers, :status]
    assert headers == expected ++ optional
    assert byte_size(body) <= 262_144
    json = Jason.decode!(body)
    if expected_status == 200 do
      kind = elem(request, 0) |> Atom.to_string()
      organization = if kind == "organizations", do: "", else: elem(request, 1)
      assert_receive {:default_repo_transaction_probe, %{runtime_role: true, transaction: true, ordinary_context: true, mode: ^kind, organization: ^organization}}, 100
      assert Enum.sort(Map.keys(json)) == Enum.sort([kind, "next_cursor"])
      row_keys = if kind == "organizations", do: ~w(id display_name organization_roles), else: ~w(organization_id id display_name roles)
      assert Enum.all?(json[kind], &(Enum.sort(Map.keys(&1)) == Enum.sort(row_keys)))
    end
    if expected_status != 200 do
      assert Enum.sort(Map.keys(json)) == ["error", "request_id"]
      assert Enum.sort(Map.keys(json["error"])) == ["code", "message"]
      assert json["request_id"] == @metadata.request_id
      fixed_message = case expected_status do
        401 -> "Authentication required."
        403 -> "Permission denied."
        404 -> "Resource not found."
        503 -> "Authorization unavailable. Retry shortly."
      end
      assert json["error"]["message"] == fixed_message
    end
    unless Repo.in_transaction?(), do: assert(clean?())
    json
  end

  defp drain_probes do
    receive do
      {:default_repo_transaction_probe, _} -> drain_probes()
    after
      0 -> :ok
    end
  end

  defp error_code(json), do: json["error"]["code"]

  defp seed! do
    sql("TRUNCATE public.mixer_authz_profiles,public.mixer_authz_principals,public.mixer_authz_organizations CASCADE")
    sql("INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES ($1,1,$2,$3,'human',true)", [@profile.profile_id, @profile.issuer, @profile.client_id])
    sql("INSERT INTO public.mixer_authz_principals VALUES ('person','human',true,0,1),('other','human',true,0,1)")
    sql("INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES ($1,1,'subject','human','person',true),($1,1,'other-subject','human','other',true)", [@profile.profile_id])
    sql("INSERT INTO public.mixer_authz_families VALUES ('family',$1,1,'person',true,0,NULL,1),('other-family',$1,1,'other',true,0,NULL,1)", [@profile.profile_id])
    sql("INSERT INTO public.mixer_authz_credentials VALUES ($1,1,'token','person','family',true,0,NULL,1),($1,1,'other-token','other','other-family',true,0,NULL,1)", [@profile.profile_id])
    sql("INSERT INTO public.mixer_authz_organizations VALUES ('org-a',true,'  Team * A  '),('org-b',true,'Foreign team'),('org-inactive',false,'Inactive team')")
    sql("INSERT INTO public.mixer_authz_projects VALUES ('org-a','project-a',true,'Project A'),('org-a','project-b',true,NULL),('org-a','project-inactive',false,'Inactive'),('org-b','project-a',true,'Foreign project')")
    sql("INSERT INTO public.mixer_authz_organization_heads SELECT id,1 FROM public.mixer_authz_organizations")
    sql("INSERT INTO public.mixer_authz_project_heads SELECT organization_id,id,1 FROM public.mixer_authz_projects")
    member("member-a", "org-a", "project-a", "developer")
    member("member-b", "org-a", "project-b", "viewer")
    member("foreign", "org-b", "project-a", "owner", "other")
    :ok
  end

  defp member(id, organization, project, role, principal \\ "person"),
    do: sql("INSERT INTO public.mixer_authz_memberships VALUES ($1,$2,$3,$4,'exact_project',$5,true,0,NULL,1)", [id, principal, organization, project, role])

  defp mutate_membership!(query) do
    assert {:ok, :ok} = Admin.transaction(fn ->
      sql("SELECT 1 FROM public.mixer_authz_organization_heads WHERE organization_id='org-a' FOR UPDATE")
      sql("SELECT 1 FROM public.mixer_authz_project_heads WHERE organization_id='org-a' ORDER BY project_id FOR UPDATE")
      sql(query)
      :ok
    end)
  end

  defp write_json(name, value),
    do: File.write!(Path.join(System.fetch_env!("MIXER_DISPATCHER_DEFAULT_EVIDENCE"), name), Jason.encode!(value, pretty: true))
end
