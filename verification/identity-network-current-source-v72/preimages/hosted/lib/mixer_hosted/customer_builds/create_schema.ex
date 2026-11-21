defmodule MixerHosted.CustomerBuilds.CreateSchema do
  @moduledoc "Additive development schema. Trusted provisioning only; no customer DDL."
  def guard do
    """
    current_setting('mixer.authz.action',true)='build.create'
    AND current_setting('mixer.authz.required_scope',true)='mixer.build.create'
    AND current_setting('mixer.authz.phase',true)='effect'
    AND COALESCE(current_setting('mixer.authz.environment_id',true),'')=''
    AND COALESCE(current_setting('mixer.authz.directory_mode',true),'')=''
    AND COALESCE(current_setting('mixer.authz.transaction_marker',true),'') ~ '^[0-9a-f]{64}$'
    AND current_setting('mixer.authz.token_expires_at',true)::bigint > extract(epoch FROM clock_timestamp())
    AND current_setting('mixer.authz.token_issued_at',true)::bigint <= extract(epoch FROM clock_timestamp())+30
    AND EXISTS(SELECT 1 FROM public.mixer_authz_profiles p
      JOIN public.mixer_authz_bindings b ON (b.profile_id,b.profile_version)=(p.id,p.version)
      JOIN public.mixer_authz_principals a ON a.id=b.principal_id
      JOIN public.mixer_authz_credentials c ON (c.profile_id,c.profile_version,c.principal_id)=(p.id,p.version,a.id)
      JOIN public.mixer_authz_families f ON f.id=c.family_id AND f.principal_id=a.id
      JOIN public.mixer_authz_memberships m ON m.principal_id=a.id
      JOIN public.mixer_authz_organizations o ON o.id=m.organization_id
      JOIN public.mixer_authz_projects pr ON pr.organization_id=o.id AND pr.id=current_setting('mixer.authz.project_id',true)
      JOIN public.mixer_authz_applications app ON (app.organization_id,app.project_id)=(o.id,pr.id) AND app.id=current_setting('mixer.authz.application_id',true)
      WHERE p.id=current_setting('mixer.authz.profile_id',true) AND p.version::text=current_setting('mixer.authz.profile_version',true)
      AND p.issuer=current_setting('mixer.authz.issuer',true) AND p.client_id=current_setting('mixer.authz.client_id',true)
      AND b.subject=current_setting('mixer.authz.subject',true) AND a.id=current_setting('mixer.authz.principal_id',true)
      AND c.reference=current_setting('mixer.authz.credential_ref',true) AND f.id=current_setting('mixer.authz.family_id',true)
      AND p.identity_class='human' AND b.identity_class='human' AND a.identity_class='human'
      AND p.active AND b.active AND a.active AND c.active AND f.active AND m.active AND o.active AND pr.active AND app.active
      AND o.id=current_setting('mixer.authz.organization_id',true)
      AND ((m.project_id IS NULL AND m.project_binding='all_projects') OR (m.project_id=pr.id AND m.project_binding='exact_project'))
      AND m.role IN ('owner','administrator','developer')
      AND greatest(a.not_before,c.not_before,f.not_before,m.not_before)<=extract(epoch FROM clock_timestamp())
      AND current_setting('mixer.authz.token_issued_at',true)::bigint>=greatest(a.not_before,c.not_before,f.not_before)
      AND (c.expires_at IS NULL OR c.expires_at>extract(epoch FROM clock_timestamp()))
      AND (f.expires_at IS NULL OR f.expires_at>extract(epoch FROM clock_timestamp()))
      AND (m.expires_at IS NULL OR m.expires_at>extract(epoch FROM clock_timestamp())))
    """
  end

  def statements do
    scope =
      "organization_id=current_setting('mixer.authz.organization_id',true) AND project_id=current_setting('mixer.authz.project_id',true) AND application_id=current_setting('mixer.authz.application_id',true)"

    g = "public.mixer_customer_build_create_guard()"

    [
      "CREATE FUNCTION public.mixer_customer_build_create_guard() RETURNS boolean LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $guard$SELECT " <>
        guard() <> "$guard$",
      "REVOKE ALL ON FUNCTION public.mixer_customer_build_create_guard() FROM PUBLIC",
      "GRANT EXECUTE ON FUNCTION public.mixer_customer_build_create_guard() TO mixer_build_create",
      "CREATE TABLE public.mixer_customer_build_inputs(organization_id text NOT NULL,project_id text NOT NULL,application_id text NOT NULL,platform text NOT NULL CHECK(platform IN ('ios','android')),input_id text NOT NULL,source_kind text NOT NULL CHECK(source_kind IN ('upload','revision')),source_reference text NOT NULL,source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),toolchain_lock_sha256 text NOT NULL CHECK(toolchain_lock_sha256 ~ '^[0-9a-f]{64}$'),build_definition_sha256 text NOT NULL CHECK(build_definition_sha256 ~ '^[0-9a-f]{64}$'),max_attempts integer NOT NULL CHECK(max_attempts BETWEEN 1 AND 20),timeout_ms bigint NOT NULL CHECK(timeout_ms>0),retry_backoff_ms bigint NOT NULL CHECK(retry_backoff_ms>=0),PRIMARY KEY(organization_id,project_id,application_id,platform,input_id),FOREIGN KEY(organization_id,project_id,application_id) REFERENCES public.mixer_authz_applications(organization_id,project_id,id))",
      "ALTER TABLE public.mixer_customer_build_inputs ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE public.mixer_customer_build_inputs FORCE ROW LEVEL SECURITY",
      "CREATE POLICY create_inputs_owner ON public.mixer_customer_build_inputs TO browser_schema_owner USING(true) WITH CHECK(true)",
      "CREATE POLICY create_inputs_read ON public.mixer_customer_build_inputs FOR SELECT TO mixer_build_create USING(" <>
        scope <> " AND " <> g <> ")",
      "GRANT SELECT ON public.mixer_customer_build_inputs TO mixer_build_create",
      "ALTER TABLE public.mixer_builds ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE public.mixer_builds FORCE ROW LEVEL SECURITY",
      "CREATE POLICY build_internal_owner ON public.mixer_builds TO browser_schema_owner USING(true) WITH CHECK(true)",
      "CREATE POLICY build_catalog_owner ON public.mixer_builds FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING(true)",
      "CREATE POLICY build_catalog_lock ON public.mixer_builds FOR UPDATE TO mixer_customer_build_catalog_definer_v1 USING(true) WITH CHECK(false)",
      "CREATE POLICY build_create_read ON public.mixer_builds FOR SELECT TO mixer_build_create USING(" <>
        scope <> " AND " <> g <> ")",
      "CREATE POLICY build_create_lock ON public.mixer_builds FOR UPDATE TO mixer_build_create USING(" <>
        scope <> " AND " <> g <> ") WITH CHECK(false)",
      "CREATE POLICY build_create_insert ON public.mixer_builds FOR INSERT TO mixer_build_create WITH CHECK(" <>
        scope <> " AND " <> g <> " AND revision=0)",
      "GRANT SELECT,INSERT,UPDATE ON public.mixer_builds TO mixer_build_create",
      "ALTER TABLE public.oban_jobs ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE public.oban_jobs FORCE ROW LEVEL SECURITY",
      "CREATE POLICY jobs_internal_owner ON public.oban_jobs TO browser_schema_owner USING(true) WITH CHECK(true)",
      "CREATE POLICY jobs_create_read ON public.oban_jobs FOR SELECT TO mixer_build_create USING(queue='builds' AND worker='MixerHosted.Builds.Coordinator' AND args->>'organization_id'=current_setting('mixer.authz.organization_id',true) AND args->>'project_id'=current_setting('mixer.authz.project_id',true) AND args->>'application_id'=current_setting('mixer.authz.application_id',true) AND " <>
        g <> ")",
      "CREATE POLICY jobs_create_insert ON public.oban_jobs FOR INSERT TO mixer_build_create WITH CHECK(queue='builds' AND worker='MixerHosted.Builds.Coordinator' AND state='available' AND attempt=0 AND " <>
        g <>
        " AND EXISTS(SELECT 1 FROM public.mixer_builds r WHERE r.id::text=args->>'build_record_id' AND r.revision=0 AND r.build_id=args->>'build_id' AND r.platform=args->>'platform' AND args->>'revision'='0' AND args->>'attempt'='1' AND args->>'fence'='1' AND args->>'kind'='created'))",
      "GRANT SELECT,INSERT ON public.oban_jobs TO mixer_build_create",
      "GRANT USAGE ON SEQUENCE public.oban_jobs_id_seq TO mixer_build_create"
    ]
  end

  defp policies!(repo, profile) do
    [original_search_path] =
      MixerHosted.Authorization.Postgres.Session.one!(
        repo,
        "SELECT pg_catalog.current_setting('search_path')",
        [],
        :authorization_unavailable
      )

    rows =
      try do
        MixerHosted.Authorization.Postgres.Session.query!(
          repo,
          "SELECT pg_catalog.set_config('search_path','pg_catalog',true)"
        )

        MixerHosted.Authorization.Postgres.Session.query!(repo, """
        SELECT c.relname::text,p.polname::text,p.polcmd::text,p.polpermissive,
          ARRAY(SELECT r.rolname::text FROM pg_roles r WHERE r.oid=ANY(p.polroles) ORDER BY r.rolname),
          pg_get_expr(p.polqual,p.polrelid,false),pg_get_expr(p.polwithcheck,p.polrelid,false)
        FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname IN ('mixer_builds','oban_jobs','mixer_customer_build_inputs')
        ORDER BY c.relname,p.polname LIMIT #{if profile == :builds_v1, do: 17, else: 12}
        """).rows
      after
        MixerHosted.Authorization.Postgres.Session.query!(
          repo,
          "SELECT pg_catalog.set_config('search_path',$1,true)",
          [original_search_path]
        )
      end

    if rows != expected_policies(profile), do: repo.rollback(:authorization_unavailable)
    :ok
  end

  @doc false
  def expected_policies(profile \\ nil) do
    extra =
      case profile do
        nil -> []
        :builds_v1 -> MixerHosted.Builds.ProcessorProfile.create_policies()
        _ -> raise ArgumentError, "unsupported installed processor profile"
      end

    (legacy_policies() ++ extra) |> Enum.sort_by(fn [t, n | _] -> {t, n} end)
  end

  defp legacy_policies do
    [
      [
        "mixer_builds",
        "build_catalog_lock",
        "w",
        true,
        ["mixer_customer_build_catalog_definer_v1"],
        "true",
        "false"
      ],
      [
        "mixer_builds",
        "build_catalog_owner",
        "r",
        true,
        ["mixer_customer_build_catalog_definer_v1"],
        "true",
        nil
      ],
      [
        "mixer_builds",
        "build_create_insert",
        "a",
        true,
        ["mixer_build_create"],
        nil,
        "((organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (project_id = current_setting('mixer.authz.project_id'::text, true)) AND (application_id = current_setting('mixer.authz.application_id'::text, true)) AND public.mixer_customer_build_create_guard() AND (revision = 0))"
      ],
      [
        "mixer_builds",
        "build_create_lock",
        "w",
        true,
        ["mixer_build_create"],
        "((organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (project_id = current_setting('mixer.authz.project_id'::text, true)) AND (application_id = current_setting('mixer.authz.application_id'::text, true)) AND public.mixer_customer_build_create_guard())",
        "false"
      ],
      [
        "mixer_builds",
        "build_create_read",
        "r",
        true,
        ["mixer_build_create"],
        "((organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (project_id = current_setting('mixer.authz.project_id'::text, true)) AND (application_id = current_setting('mixer.authz.application_id'::text, true)) AND public.mixer_customer_build_create_guard())",
        nil
      ],
      [
        "mixer_builds",
        "build_internal_owner",
        "*",
        true,
        ["browser_schema_owner"],
        "true",
        "true"
      ],
      [
        "mixer_customer_build_inputs",
        "create_inputs_owner",
        "*",
        true,
        ["browser_schema_owner"],
        "true",
        "true"
      ],
      [
        "mixer_customer_build_inputs",
        "create_inputs_read",
        "r",
        true,
        ["mixer_build_create"],
        "((organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (project_id = current_setting('mixer.authz.project_id'::text, true)) AND (application_id = current_setting('mixer.authz.application_id'::text, true)) AND public.mixer_customer_build_create_guard())",
        nil
      ],
      [
        "oban_jobs",
        "jobs_create_insert",
        "a",
        true,
        ["mixer_build_create"],
        nil,
        "((queue = 'builds'::text) AND (worker = 'MixerHosted.Builds.Coordinator'::text) AND (state = 'available'::public.oban_job_state) AND (attempt = 0) AND public.mixer_customer_build_create_guard() AND (EXISTS ( SELECT 1\n   FROM public.mixer_builds r\n  WHERE (((r.id)::text = (oban_jobs.args ->> 'build_record_id'::text)) AND (r.revision = 0) AND (r.build_id = (oban_jobs.args ->> 'build_id'::text)) AND (r.platform = (oban_jobs.args ->> 'platform'::text)) AND ((oban_jobs.args ->> 'revision'::text) = '0'::text) AND ((oban_jobs.args ->> 'attempt'::text) = '1'::text) AND ((oban_jobs.args ->> 'fence'::text) = '1'::text) AND ((oban_jobs.args ->> 'kind'::text) = 'created'::text)))))"
      ],
      [
        "oban_jobs",
        "jobs_create_read",
        "r",
        true,
        ["mixer_build_create"],
        "((queue = 'builds'::text) AND (worker = 'MixerHosted.Builds.Coordinator'::text) AND ((args ->> 'organization_id'::text) = current_setting('mixer.authz.organization_id'::text, true)) AND ((args ->> 'project_id'::text) = current_setting('mixer.authz.project_id'::text, true)) AND ((args ->> 'application_id'::text) = current_setting('mixer.authz.application_id'::text, true)) AND public.mixer_customer_build_create_guard())",
        nil
      ],
      ["oban_jobs", "jobs_internal_owner", "*", true, ["browser_schema_owner"], "true", "true"]
    ]
  end

  def compatibility!(repo, profile \\ nil) do
    policies!(repo, profile)

    [safe] =
      MixerHosted.Authorization.Postgres.Session.one!(
        repo,
        """
        SELECT
          (SELECT count(*)=1 AND bool_and(p.prosrc=$1 AND NOT p.prosecdef AND p.provolatile='v'
            AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
            AND l.lanname='sql' AND p.pronargs=0 AND p.prorettype='boolean'::regtype
            AND o.rolname='browser_schema_owner' AND NOT o.rolcanlogin AND NOT o.rolsuper AND NOT o.rolbypassrls
            AND NOT has_function_privilege('browser_ordinary',p.oid,'EXECUTE')
            AND has_function_privilege('mixer_build_create',p.oid,'EXECUTE'))
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang JOIN pg_roles o ON o.oid=p.proowner
            WHERE n.nspname='public' AND p.proname='mixer_customer_build_create_guard')
          AND (SELECT count(*)=3 AND bool_and(c.relrowsecurity AND c.relforcerowsecurity AND o.rolname='browser_schema_owner')
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles o ON o.oid=c.relowner
            WHERE n.nspname='public' AND c.relname IN ('mixer_builds','oban_jobs','mixer_customer_build_inputs'))
          AND (SELECT count(*)=1 AND bool_and(p.prosrc=$2 AND p.prosecdef AND o.rolname='browser_writer'
            AND NOT o.rolcanlogin AND NOT o.rolsuper AND NOT o.rolbypassrls
            AND NOT has_function_privilege('browser_ordinary',p.oid,'EXECUTE')
            AND has_function_privilege('mixer_build_create',p.oid,'EXECUTE'))
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles o ON o.oid=p.proowner
            WHERE n.nspname='public' AND p.proname='mixer_browser_create_active_load')
          AND NOT EXISTS(SELECT 1 FROM pg_policy p WHERE p.polrelid IN ('public.mixer_builds'::regclass,'public.oban_jobs'::regclass,'public.mixer_customer_build_inputs'::regclass) AND 0::oid=ANY(p.polroles))
          AND NOT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_create'))
        """,
        [
          "SELECT " <> guard(),
          MixerHosted.BrowserAuth.ActiveCreateSchema.manifest()[
            "mixer_browser_create_active_load"
          ].source
        ],
        :authorization_unavailable
      )

    if safe != true, do: repo.rollback(:authorization_unavailable)
    :ok
  end

  def admit!(repo, profile \\ nil) do
    compatibility!(repo, profile)

    [[true]] =
      MixerHosted.Authorization.Postgres.Session.query!(repo, """
      SELECT current_user='mixer_build_create' AND session_user=current_user AND
      (SELECT count(*)=3 AND bool_and(c.relrowsecurity AND c.relforcerowsecurity AND NOT pg_has_role(current_user,c.relowner,'MEMBER')) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN ('mixer_builds','oban_jobs','mixer_customer_build_inputs'))
      AND NOT has_table_privilege('browser_ordinary','public.mixer_builds','INSERT,UPDATE,DELETE')
      AND NOT has_table_privilege('browser_ordinary','public.oban_jobs','INSERT,UPDATE,DELETE')
      """).rows

    :ok
  end
end
