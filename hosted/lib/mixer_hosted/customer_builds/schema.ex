defmodule MixerHosted.CustomerBuilds.Schema do
  @moduledoc "Private unselected additive SQL capability; never alters frozen catalog admission."
  @signature "text,text,text,text,text"
  def signature, do: @signature

  def body do
    """
    DECLARE result jsonb; stamp bigint;
    BEGIN
      IF current_setting('mixer.authz.action',true) IS DISTINCT FROM 'build.read'
        OR current_setting('mixer.authz.required_scope',true) IS DISTINCT FROM 'mixer.build.read'
        OR COALESCE(current_setting('mixer.authz.environment_id',true),'') <> ''
        OR COALESCE(current_setting('mixer.authz.directory_mode',true),'') <> ''
        OR COALESCE(current_setting('mixer.authz.transaction_marker',true),'') !~ '^[0-9a-f]{64}$'
        OR current_setting('mixer.authz.phase',true) IS DISTINCT FROM 'build_read'
      THEN RETURN NULL; END IF;
      PERFORM 1 FROM public.mixer_authz_bindings WHERE
        profile_id=current_setting('mixer.authz.profile_id',true) AND
        profile_version::text=current_setting('mixer.authz.profile_version',true) AND
        subject=current_setting('mixer.authz.subject',true) FOR SHARE;
      PERFORM 1 FROM public.mixer_authz_organizations WHERE
        id=current_setting('mixer.authz.organization_id',true) FOR SHARE;
      PERFORM 1 FROM public.mixer_authz_projects WHERE
        organization_id=current_setting('mixer.authz.organization_id',true) AND
        id=current_setting('mixer.authz.project_id',true) FOR SHARE;
      PERFORM 1 FROM public.mixer_authz_applications WHERE
        organization_id=current_setting('mixer.authz.organization_id',true) AND
        project_id=current_setting('mixer.authz.project_id',true) AND
        id=current_setting('mixer.authz.application_id',true) FOR SHARE;
      PERFORM 1 FROM public.mixer_authz_memberships WHERE
        principal_id=current_setting('mixer.authz.principal_id',true) AND
        organization_id=current_setting('mixer.authz.organization_id',true) AND
        ((project_binding='all_projects' AND project_id IS NULL) OR
         (project_binding='exact_project' AND project_id=current_setting('mixer.authz.project_id',true)))
        ORDER BY id COLLATE "C" LIMIT 65 FOR SHARE;
      PERFORM 1 FROM public.mixer_builds WHERE
        organization_id=current_setting('mixer.authz.organization_id',true) AND
        project_id=current_setting('mixer.authz.project_id',true) AND
        application_id=current_setting('mixer.authz.application_id',true) AND
        build_id=$1 AND platform=$2 FOR SHARE;
      stamp := floor(extract(epoch FROM clock_timestamp()))::bigint;
      SELECT jsonb_build_object('profile',to_jsonb(p),'binding',to_jsonb(b),
        'principal',to_jsonb(a),'credential',to_jsonb(c),'family',to_jsonb(f),
        'organization',to_jsonb(o),'project',to_jsonb(j),'application',to_jsonb(app),
        'organization_head',to_jsonb(oh),'project_head',to_jsonb(ph),
        'memberships',(SELECT jsonb_agg(to_jsonb(m) ORDER BY m.id COLLATE "C")
          FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND
          m.organization_id=o.id AND ((m.project_binding='all_projects' AND m.project_id IS NULL)
          OR (m.project_binding='exact_project' AND m.project_id=j.id))),
        'record',to_jsonb(r)) INTO result
      FROM public.mixer_authz_profiles p
      JOIN public.mixer_authz_bindings b ON (b.profile_id,b.profile_version)=(p.id,p.version)
      JOIN public.mixer_authz_principals a ON a.id=b.principal_id
      JOIN public.mixer_authz_credentials c ON (c.profile_id,c.profile_version,c.principal_id)=(p.id,p.version,a.id)
      JOIN public.mixer_authz_families f ON (f.id,f.profile_id,f.profile_version,f.principal_id)=(c.family_id,p.id,p.version,a.id)
      JOIN public.mixer_authz_organizations o ON o.id=current_setting('mixer.authz.organization_id',true)
      JOIN public.mixer_authz_projects j ON j.organization_id=o.id AND j.id=current_setting('mixer.authz.project_id',true)
      JOIN public.mixer_authz_applications app ON (app.organization_id,app.project_id)=(o.id,j.id)
        AND app.id=current_setting('mixer.authz.application_id',true)
      JOIN public.mixer_authz_organization_heads oh ON oh.organization_id=o.id
      JOIN public.mixer_authz_project_heads ph ON (ph.organization_id,ph.project_id)=(o.id,j.id)
      JOIN public.mixer_builds r ON (r.organization_id,r.project_id,r.application_id)=(o.id,j.id,app.id)
      WHERE p.id=current_setting('mixer.authz.profile_id',true)
        AND p.version::text=current_setting('mixer.authz.profile_version',true)
        AND p.issuer=current_setting('mixer.authz.issuer',true)
        AND p.client_id=current_setting('mixer.authz.client_id',true)
        AND p.identity_class='human' AND b.identity_class='human' AND a.identity_class='human'
        AND p.active AND b.active AND a.active AND c.active AND f.active
        AND o.active AND j.active AND app.active
        AND b.subject=current_setting('mixer.authz.subject',true)
        AND a.id=current_setting('mixer.authz.principal_id',true)
        AND c.reference=current_setting('mixer.authz.credential_ref',true)
        AND f.id=current_setting('mixer.authz.family_id',true)
        AND current_setting('mixer.authz.token_issued_at',true)::bigint >= greatest(a.not_before,c.not_before,f.not_before)
        AND current_setting('mixer.authz.token_issued_at',true)::bigint <= stamp+30
        AND current_setting('mixer.authz.token_expires_at',true)::bigint > stamp
        AND greatest(a.not_before,c.not_before,f.not_before) <= stamp
        AND (c.expires_at IS NULL OR c.expires_at>stamp)
        AND (f.expires_at IS NULL OR f.expires_at>stamp)
        AND EXISTS (SELECT 1 FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id
          AND m.organization_id=o.id AND ((m.project_binding='all_projects' AND m.project_id IS NULL)
            OR (m.project_binding='exact_project' AND m.project_id=j.id))
          AND m.role IN ('owner','administrator','developer','release_manager','viewer')
          AND m.active AND m.not_before<=stamp AND (m.expires_at IS NULL OR m.expires_at>stamp))
        AND (SELECT count(*) FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND m.organization_id=o.id) <= 64
        AND r.build_id=$1 AND r.platform=$2
        AND r.journal#>>'{creation,spec,source,sha256}'=$3
        AND r.journal#>>'{creation,spec,toolchain_lock_sha256}'=$4
        AND r.journal#>>'{creation,spec,build_definition_sha256}'=$5;
      RETURN result;
    END
    """
  end

  def ddl do
    "CREATE FUNCTION public.mixer_customer_build_read_v1(#{@signature}) RETURNS jsonb " <>
      "LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $build$" <>
      body() <> "$build$;"
  end

  def admit!(repo) do
    [safe] =
      MixerHosted.Authorization.Postgres.Session.one!(
        repo,
        """
        SELECT count(*)=1 AND bool_and(p.prosrc=$1 AND p.prosecdef AND p.provolatile='v'
          AND p.prorettype='jsonb'::regtype AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND pg_get_function_identity_arguments(p.oid)='text, text, text, text, text'
          AND NOT owner.rolcanlogin AND NOT owner.rolsuper AND NOT owner.rolbypassrls
          AND NOT pg_has_role(current_user,p.proowner,'MEMBER')
          AND has_function_privilege(current_user,p.oid,'EXECUTE')
          AND NOT EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) x
            WHERE x.grantee=0 AND x.privilege_type='EXECUTE'))
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_roles owner ON owner.oid=p.proowner
        WHERE n.nspname='public' AND p.proname='mixer_customer_build_read_v1'
        """,
        [body()],
        :authorization_unavailable
      )

    if safe != true, do: repo.rollback(:authorization_unavailable)
    :ok
  end
end
