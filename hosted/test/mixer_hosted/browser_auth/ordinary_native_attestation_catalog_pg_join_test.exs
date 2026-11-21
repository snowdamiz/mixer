defmodule MixerHosted.BrowserAuth.OrdinaryNativeAttestationCatalogPGJoinTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.BrowserAuth.RuntimeOwner
  alias MixerHosted.BrowserAuth.StorageFixture.{Admin, Migration}
  alias MixerHosted.Builds.ProcessorProfile
  alias MixerHosted.CustomerBuilds.{AttestationRepo, AttestationSchema, LocalAttestation}
  alias MixerHosted.CustomerWorkspace.SelfServiceSchema
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB

  @writer "mixer_native_attestation_writer"
  @authorization "public.mixer_authz_profiles"
  @heads "public.mixer_authz_project_heads"
  @lock "public.mixer_authz_lock_profiles()"
  @table "public.mixer_native_development_attestations"
  @entry "public.mixer_native_development_attestation_v1(text,text,text,text,jsonb,text,text,text,text,bytea)"
  @spki Base.encode64(
          Base.decode16!(
            "302a300506032b6570032100d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
            case: :lower
          )
        )

  setup_all do
    conn = DB.connection!("browser_admin", "postgres")

    try do
      if Postgrex.query!(conn, "SELECT 1 FROM pg_roles WHERE rolname='mixer_build_create'", []).rows ==
           [] do
        Postgrex.query!(conn, "CREATE ROLE mixer_build_create LOGIN NOINHERIT", [])

        on_exit(fn ->
          conn = DB.connection!("browser_admin", "postgres")

          try do
            Postgrex.query!(conn, "DROP ROLE mixer_build_create", [])
          after
            GenServer.stop(conn)
          end
        end)
      end
    after
      GenServer.stop(conn)
    end

    c = prepare!(:workspace_builds, "ordinary-native-attestation-catalog")
    provision_workspace!()
    provision_build_create!()

    put_in(c.hosted.create_repo, Keyword.put(c.hosted.repo, :username, "mixer_build_create"))
  end

  test "ordinary authenticated workspace and dedicated attestation writer share an exact catalog",
       c do
    install_processor_profile!()

    c =
      update_in(c.hosted, fn hosted ->
        %{hosted | native: %{retained_root: System.tmp_dir!()}, processor_profile: :builds_v1}
      end)

    default = start!(c)
    cookie = authenticated_cookie(default)
    assert :disabled = LocalAttestation.configuration()
    refute Process.whereis(AttestationRepo)

    install_writer!()
    assert http(default, "/auth/session", headers(cookie)).status == 503
    assert :ok = Application.stop(:mixer_hosted)

    endpoint =
      Keyword.put(c.hosted.endpoint, :http,
        ip: {127, 0, 0, 1},
        port: default.http_port,
        http_2_options: [enabled: false]
      )

    hosted =
      LocalAttestation.configure!(
        %{
          "MIXER_LOCAL_NATIVE_ATTESTATION_PASSWORD" => "synthetic-attestation-writer",
          "MIXER_LOCAL_NATIVE_ATTESTATION_PUBLIC_SPKI_BASE64" => @spki
        },
        %{c.hosted | endpoint: endpoint},
        :disabled
      )

    configured = %{c | hosted: hosted}
    assert_writer_and_session!(configured, default.http_port, cookie)

    install_uploader!()
    assert_writer_and_session!(configured, default.http_port)

    for {name, mutate, restore} <- refused_catalogs() do
      for sql <- List.wrap(mutate), do: DB.q!(Admin, sql)

      try do
        refused = start!(configured)
        assert RuntimeOwner.status().phase == :unavailable, name
        response = http(refused, "/auth/session", [])
        assert response.status == 503, name
        assert response_header(response, "set-cookie") == [], name
      after
        assert :ok = Application.stop(:mixer_hosted)
        for sql <- List.wrap(restore), do: DB.q!(Admin, sql)
      end
    end

    assert_writer_and_session!(configured, default.http_port)

    for relation <- ~w(mixer_builds mixer_build_reservations mixer_build_coordinator_leases
                       oban_jobs mixer_native_development_attestations) do
      assert DB.q!(Admin, "SELECT count(*) FROM public.#{relation}").rows == [[0]]
    end
  end

  defp authenticated_cookie(c) do
    attempt = begin_http(c, bootstrap_http(c))
    callback = http(c, "/auth/callback?" <> attempt.query, attempt.headers)
    assert callback.status == 303
    cookie = response_cookie(callback)
    session = http(c, "/auth/session", headers(cookie))
    assert session.status == 200
    assert Jason.decode!(session.body)["state"] == "authenticated"
    cookie
  end

  defp assert_writer_and_session!(c, expected_port, retained_cookie \\ nil) do
    running = start!(c)

    try do
      assert running.http_port == expected_port

      if retained_cookie do
        session = http(running, "/auth/session", headers(retained_cookie))
        assert session.status == 200
        assert Jason.decode!(session.body)["state"] == "authenticated"
      end

      assert RuntimeOwner.status().phase == :storage_ready
      cookie = authenticated_cookie(running)

      assert http(
               running,
               "/console-api/v1/applications?organization_id=org-a&project_id=project-a",
               headers(cookie)
             ).status == 200

      origin = "http://127.0.0.1:#{expected_port}"
      assert {:ok, %{origin: ^origin, public_spki_der: der}} = LocalAttestation.configuration()
      assert Base.encode64(der) == @spki
      assert DB.q!(AttestationRepo, "SELECT session_user::text").rows == [[@writer]]

      assert {:ok, :ok} =
               AttestationRepo.transaction(fn -> AttestationSchema.admit!(AttestationRepo) end)

      if retained_cookie do
        DB.q!(Admin, "GRANT SELECT ON public.mixer_builds TO #{@writer}")

        try do
          refused = http(running, "/auth/session", headers(cookie))
          assert refused.status == 503
          assert response_header(refused, "set-cookie") == []
        after
          DB.q!(Admin, "REVOKE SELECT ON public.mixer_builds FROM #{@writer}")
        end
      end
    after
      assert :ok = Application.stop(:mixer_hosted)
      refute Process.whereis(AttestationRepo)
    end
  end

  defp install_writer! do
    DB.q!(Admin, "CREATE ROLE #{@writer} LOGIN NOINHERIT PASSWORD 'synthetic-attestation-writer'")

    on_exit(fn ->
      DB.q!(Admin, "DROP OWNED BY #{@writer}")
      DB.q!(Admin, "DROP ROLE #{@writer}")
    end)

    [path] = Path.wildcard("priv/local_native_attestation/20261120000020_*.exs")
    [{module, _}] = Code.require_file(path)
    assert :ok = Ecto.Migrator.up(Migration, 20_261_120_000_020, module, log: false)

    relations =
      ~w(profiles principals bindings families credentials organizations projects applications
         environments organization_heads project_heads memberships)
      |> Enum.map_join(", ", &"public.mixer_authz_#{&1}")

    DB.q!(Migration, "GRANT USAGE ON SCHEMA public TO #{@writer}")
    DB.q!(Migration, "GRANT SELECT ON #{relations} TO #{@writer}")

    for lock <- ~w(profiles principals families credentials organization_heads project_heads),
        do:
          DB.q!(
            Migration,
            "GRANT EXECUTE ON FUNCTION public.mixer_authz_lock_#{lock}() TO #{@writer}"
          )

    DB.q!(Migration, AttestationSchema.fixture_grant_statement())
  end

  defp install_processor_profile! do
    for version <- [20_261_110_000_498, 20_261_110_000_499, 20_261_110_000_500] do
      [path] = Path.wildcard("priv/unselected_operation_admission/#{version}_*.exs")
      [{module, _}] = Code.require_file(path)
      assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
    end

    assert {:ok, :ok} =
             Admin.transaction(fn ->
               for sql <- ProcessorProfile.statements(:builds_v1) do
                 sql =
                   String.replace(
                     sql,
                     ~s(:"processor_database"),
                     "browser_ordinary_installation_r1422"
                   )

                 DB.q!(Admin, sql)
               end

               :ok
             end)

    for sql <- ProcessorProfile.operation_intent_statements(:durable_intent_v1),
        do: DB.q!(Admin, sql)

    for sql <- SelfServiceSchema.processor_policy_statements(), do: DB.q!(Migration, sql)

    on_exit(fn ->
      role = ProcessorProfile.role()
      locker = ProcessorProfile.locker()
      DB.q!(Admin, "DROP OWNED BY #{role}, #{locker}")
      DB.q!(Admin, "DROP ROLE #{role}, #{locker}")
    end)
  end

  defp install_uploader! do
    {output, status} =
      System.cmd(
        "psql",
        ~w(-X -w -h 127.0.0.1 -U browser_admin -d browser_ordinary_installation_r1422 -v ON_ERROR_STOP=1) ++
          [
            "-p",
            to_string(DB.port()),
            "-f",
            "../docs/operations/provision-local-artifact-uploader.sql"
          ],
        env: [{"PGSSLMODE", "disable"}],
        stderr_to_stdout: true
      )

    assert status == 0, output

    on_exit(fn ->
      DB.q!(Admin, "DROP OWNED BY mixer_artifact_uploader")
      DB.q!(Admin, "DROP ROLE mixer_artifact_uploader")
    end)
  end

  defp refused_catalogs do
    [
      {"missing protected grant", "REVOKE SELECT ON #{@authorization} FROM #{@writer}",
       "GRANT SELECT ON #{@authorization} TO #{@writer}"},
      {"wrong protected relation",
       [
         "REVOKE SELECT ON #{@authorization} FROM #{@writer}",
         "GRANT SELECT ON public.mixer_browser_sessions TO #{@writer}"
       ],
       [
         "REVOKE SELECT ON public.mixer_browser_sessions FROM #{@writer}",
         "GRANT SELECT ON #{@authorization} TO #{@writer}"
       ]},
      {"protected column ACL", "GRANT SELECT (id) ON #{@authorization} TO #{@writer}",
       "REVOKE SELECT (id) ON #{@authorization} FROM #{@writer}"},
      {"grantable select", "GRANT SELECT ON #{@authorization} TO #{@writer} WITH GRANT OPTION",
       "REVOKE GRANT OPTION FOR SELECT ON #{@authorization} FROM #{@writer}"},
      {"wrong role", "ALTER ROLE #{@writer} RENAME TO wrong_attestation_writer",
       "ALTER ROLE wrong_attestation_writer RENAME TO #{@writer}"},
      {"role lacks login", "ALTER ROLE #{@writer} NOLOGIN", "ALTER ROLE #{@writer} LOGIN"},
      {"role bypasses RLS", "ALTER ROLE #{@writer} BYPASSRLS",
       "ALTER ROLE #{@writer} NOBYPASSRLS"},
      {"writer holds membership", "GRANT browser_ordinary TO #{@writer}",
       "REVOKE browser_ordinary FROM #{@writer}"},
      {"writer has a member", "GRANT #{@writer} TO browser_ordinary",
       "REVOKE #{@writer} FROM browser_ordinary"},
      {"role overrides the search path", "ALTER ROLE #{@writer} SET search_path TO public",
       "ALTER ROLE #{@writer} RESET search_path"},
      {"missing scoped read", "REVOKE SELECT ON #{@heads} FROM #{@writer}",
       "GRANT SELECT ON #{@heads} TO #{@writer}"},
      {"extra scoped write", "GRANT UPDATE ON #{@heads} TO #{@writer}",
       "REVOKE UPDATE ON #{@heads} FROM #{@writer}"},
      {"maintain build relation", "GRANT MAINTAIN ON public.mixer_builds TO #{@writer}",
       "REVOKE MAINTAIN ON public.mixer_builds FROM #{@writer}"},
      {"missing attestation owner SELECT policy",
       "DROP POLICY attestation_owner_read ON #{@table}",
       "CREATE POLICY attestation_owner_read ON #{@table} FOR SELECT TO browser_schema_owner USING (true)"},
      {"altered attestation owner INSERT policy",
       "ALTER POLICY attestation_owner_insert ON #{@table} WITH CHECK (false)",
       "ALTER POLICY attestation_owner_insert ON #{@table} WITH CHECK (true)"},
      {"implicit attestation read", "GRANT SELECT ON #{@table} TO PUBLIC",
       "REVOKE SELECT ON #{@table} FROM PUBLIC"},
      {"implicit column read", "GRANT SELECT (revision) ON #{@heads} TO PUBLIC",
       "REVOKE SELECT (revision) ON #{@heads} FROM PUBLIC"},
      {"another login can invoke the attestation entry",
       "GRANT EXECUTE ON FUNCTION #{@entry} TO browser_ordinary",
       "REVOKE EXECUTE ON FUNCTION #{@entry} FROM browser_ordinary"},
      {"wrong schema usage",
       [
         "CREATE SCHEMA attestation_other",
         "GRANT USAGE ON SCHEMA attestation_other TO #{@writer}"
       ], "DROP SCHEMA attestation_other"},
      {"implicit wrong schema usage",
       ["CREATE SCHEMA attestation_other", "GRANT USAGE ON SCHEMA attestation_other TO PUBLIC"],
       "DROP SCHEMA attestation_other"},
      {"wrong database grant", "GRANT CONNECT ON DATABASE postgres TO #{@writer}",
       "REVOKE CONNECT ON DATABASE postgres FROM #{@writer}"},
      {"default grants",
       "ALTER DEFAULT PRIVILEGES FOR ROLE browser_schema_owner GRANT SELECT ON TABLES TO #{@writer}",
       "ALTER DEFAULT PRIVILEGES FOR ROLE browser_schema_owner REVOKE SELECT ON TABLES FROM #{@writer}"},
      {"grant from a nonowner",
       [
         "CREATE ROLE attestation_grantor NOLOGIN NOINHERIT",
         "REVOKE SELECT ON #{@heads} FROM #{@writer}",
         "GRANT SELECT ON #{@heads} TO attestation_grantor WITH GRANT OPTION",
         """
         DO $$ BEGIN
           SET LOCAL ROLE attestation_grantor;
           GRANT SELECT ON #{@heads} TO #{@writer};
         END $$
         """
       ],
       [
         "REVOKE SELECT ON #{@heads} FROM attestation_grantor CASCADE",
         "DROP ROLE attestation_grantor",
         "GRANT SELECT ON #{@heads} TO #{@writer}"
       ]},
      {"implicit lock execute",
       [
         "REVOKE EXECUTE ON FUNCTION #{@lock} FROM #{@writer}",
         "GRANT EXECUTE ON FUNCTION #{@lock} TO PUBLIC"
       ],
       [
         "REVOKE EXECUTE ON FUNCTION #{@lock} FROM PUBLIC",
         "GRANT EXECUTE ON FUNCTION #{@lock} TO #{@writer}"
       ]}
    ]
  end
end
