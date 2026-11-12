defmodule MixerHosted.CustomerBuildCatalog.Schema do
  @moduledoc "UNSELECTED additive fixed SQL capabilities. Installation is private and explicit."
  def name(:applications), do: "mixer_customer_build_applications_v1"
  def name(:builds), do: "mixer_customer_build_catalog_v1"
  def signature(:applications), do: "text"
  def signature(:builds), do: "text,text"

  def body(:applications) do
    """
    DECLARE result jsonb; stamp bigint;
    BEGIN
      IF current_setting('mixer.authz.action',true) IS DISTINCT FROM 'build.read'
        OR current_setting('mixer.authz.required_scope',true) IS DISTINCT FROM 'mixer.build.read'
        OR COALESCE(current_setting('mixer.authz.environment_id',true),'') <> ''
        OR COALESCE(current_setting('mixer.authz.directory_mode',true),'') <> ''
        OR COALESCE(current_setting('mixer.authz.transaction_marker',true),'') !~ '^[0-9a-f]{64}$'
        OR current_setting('mixer.authz.phase',true) IS DISTINCT FROM 'build_catalog_applications'
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
      PERFORM 1 FROM public.mixer_authz_memberships WHERE
        principal_id=current_setting('mixer.authz.principal_id',true) AND
        organization_id=current_setting('mixer.authz.organization_id',true) AND
        ((project_binding='all_projects' AND project_id IS NULL) OR
         (project_binding='exact_project' AND project_id=current_setting('mixer.authz.project_id',true)))
        ORDER BY id COLLATE "C" LIMIT 65 FOR SHARE;
      PERFORM 1 FROM public.mixer_authz_applications r WHERE r.organization_id=current_setting('mixer.authz.organization_id',true) AND r.project_id=current_setting('mixer.authz.project_id',true) AND r.active AND ($1 IS NULL OR r.id COLLATE "C">$1 COLLATE "C") ORDER BY r.id COLLATE "C" LIMIT 26 FOR SHARE;
      stamp := floor(extract(epoch FROM clock_timestamp()))::bigint;
      SELECT jsonb_build_object('profile',to_jsonb(p),'binding',to_jsonb(b),
        'principal',to_jsonb(a),'credential',to_jsonb(c),'family',to_jsonb(f),
        'organization',to_jsonb(o),'project',to_jsonb(j),
        'organization_head',to_jsonb(oh),'project_head',to_jsonb(ph),
        'memberships',(SELECT jsonb_agg(to_jsonb(m) ORDER BY m.id COLLATE "C")
          FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND
          m.organization_id=o.id AND ((m.project_binding='all_projects' AND m.project_id IS NULL)
          OR (m.project_binding='exact_project' AND m.project_id=j.id))),
        'records','[]'::jsonb) INTO result
      FROM public.mixer_authz_profiles p
      JOIN public.mixer_authz_bindings b ON (b.profile_id,b.profile_version)=(p.id,p.version)
      JOIN public.mixer_authz_principals a ON a.id=b.principal_id
      JOIN public.mixer_authz_credentials c ON (c.profile_id,c.profile_version,c.principal_id)=(p.id,p.version,a.id)
      JOIN public.mixer_authz_families f ON (f.id,f.profile_id,f.profile_version,f.principal_id)=(c.family_id,p.id,p.version,a.id)
      JOIN public.mixer_authz_organizations o ON o.id=current_setting('mixer.authz.organization_id',true)
      JOIN public.mixer_authz_projects j ON j.organization_id=o.id AND j.id=current_setting('mixer.authz.project_id',true)
      JOIN public.mixer_authz_organization_heads oh ON oh.organization_id=o.id
      JOIN public.mixer_authz_project_heads ph ON (ph.organization_id,ph.project_id)=(o.id,j.id)
      WHERE p.id=current_setting('mixer.authz.profile_id',true)
        AND p.version::text=current_setting('mixer.authz.profile_version',true)
        AND p.issuer=current_setting('mixer.authz.issuer',true)
        AND p.client_id=current_setting('mixer.authz.client_id',true)
        AND p.identity_class='human' AND b.identity_class='human' AND a.identity_class='human'
        AND p.active AND b.active AND a.active AND c.active AND f.active
        AND o.active AND j.active
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
        AND (SELECT count(*) FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND m.organization_id=o.id) <= 64;
      IF result IS NULL THEN RETURN NULL; END IF;
      SELECT result || jsonb_build_object('records',COALESCE(jsonb_agg(to_jsonb(page) ORDER BY page.id COLLATE "C"),'[]'::jsonb)) INTO result
      FROM (SELECT r.* FROM public.mixer_authz_applications r WHERE r.organization_id=current_setting('mixer.authz.organization_id',true) AND r.project_id=current_setting('mixer.authz.project_id',true) AND r.active AND ($1 IS NULL OR r.id COLLATE "C">$1 COLLATE "C") ORDER BY r.id COLLATE "C" LIMIT 26) page;
      RETURN result;
    END
    """
  end

  def body(:builds) do
    """
    DECLARE result jsonb; stamp bigint;
    BEGIN
      IF current_setting('mixer.authz.action',true) IS DISTINCT FROM 'build.read'
        OR current_setting('mixer.authz.required_scope',true) IS DISTINCT FROM 'mixer.build.read'
        OR COALESCE(current_setting('mixer.authz.environment_id',true),'') <> ''
        OR COALESCE(current_setting('mixer.authz.directory_mode',true),'') <> ''
        OR COALESCE(current_setting('mixer.authz.transaction_marker',true),'') !~ '^[0-9a-f]{64}$'
        OR current_setting('mixer.authz.phase',true) IS DISTINCT FROM 'build_catalog_builds'
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
      PERFORM 1 FROM public.mixer_builds r WHERE r.organization_id=current_setting('mixer.authz.organization_id',true) AND r.project_id=current_setting('mixer.authz.project_id',true) AND r.application_id=current_setting('mixer.authz.application_id',true) AND (($1 IS NULL AND $2 IS NULL) OR (r.build_id COLLATE "C",r.platform COLLATE "C")>($1 COLLATE "C",$2 COLLATE "C")) ORDER BY r.build_id COLLATE "C",r.platform COLLATE "C" LIMIT 26 FOR SHARE;
      stamp := floor(extract(epoch FROM clock_timestamp()))::bigint;
      SELECT jsonb_build_object('profile',to_jsonb(p),'binding',to_jsonb(b),
        'principal',to_jsonb(a),'credential',to_jsonb(c),'family',to_jsonb(f),
        'organization',to_jsonb(o),'project',to_jsonb(j),'application',to_jsonb(app),
        'organization_head',to_jsonb(oh),'project_head',to_jsonb(ph),
        'memberships',(SELECT jsonb_agg(to_jsonb(m) ORDER BY m.id COLLATE "C")
          FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND
          m.organization_id=o.id AND ((m.project_binding='all_projects' AND m.project_id IS NULL)
          OR (m.project_binding='exact_project' AND m.project_id=j.id))),
        'records','[]'::jsonb) INTO result
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
        AND (SELECT count(*) FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND m.organization_id=o.id) <= 64;
      IF result IS NULL THEN RETURN NULL; END IF;
      SELECT result || jsonb_build_object('records',COALESCE(jsonb_agg(to_jsonb(page) ORDER BY page.build_id COLLATE "C",page.platform COLLATE "C"),'[]'::jsonb)) INTO result
      FROM (SELECT r.* FROM public.mixer_builds r WHERE r.organization_id=current_setting('mixer.authz.organization_id',true) AND r.project_id=current_setting('mixer.authz.project_id',true) AND r.application_id=current_setting('mixer.authz.application_id',true) AND (($1 IS NULL AND $2 IS NULL) OR (r.build_id COLLATE "C",r.platform COLLATE "C")>($1 COLLATE "C",$2 COLLATE "C")) ORDER BY r.build_id COLLATE "C",r.platform COLLATE "C" LIMIT 26) page;
      RETURN result;
    END
    """
  end

  def ddl(kind),
    do:
      "CREATE FUNCTION public.#{name(kind)}(#{signature(kind)}) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $catalog$" <>
        body(kind) <> "$catalog$;"

  def role, do: "mixer_customer_build_catalog_definer_v1"

  def policy_expression,
    do:
      "((current_setting('mixer.authz.phase'::text, true) = 'build_catalog_applications'::text) AND (current_setting('mixer.authz.action'::text, true) = 'build.read'::text) AND (current_setting('mixer.authz.required_scope'::text, true) = 'mixer.build.read'::text) AND (COALESCE(current_setting('mixer.authz.application_id'::text, true), ''::text) = ''::text) AND (COALESCE(current_setting('mixer.authz.environment_id'::text, true), ''::text) = ''::text) AND (COALESCE(current_setting('mixer.authz.directory_mode'::text, true), ''::text) = ''::text) AND (current_setting('mixer.authz.transaction_marker'::text, true) ~ '^[0-9a-f]{64}$'::text) AND (organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (project_id = current_setting('mixer.authz.project_id'::text, true)) AND active AND (EXISTS ( SELECT 1\n   FROM ((((((((mixer_authz_profiles p\n     JOIN mixer_authz_bindings b ON (((b.profile_id = p.id) AND (b.profile_version = p.version))))\n     JOIN mixer_authz_principals a ON ((a.id = b.principal_id)))\n     JOIN mixer_authz_credentials c ON (((c.profile_id = p.id) AND (c.profile_version = p.version) AND (c.principal_id = a.id))))\n     JOIN mixer_authz_families f ON (((f.id = c.family_id) AND (f.profile_id = p.id) AND (f.profile_version = p.version) AND (f.principal_id = a.id))))\n     JOIN mixer_authz_organizations o ON ((o.id = current_setting('mixer.authz.organization_id'::text, true))))\n     JOIN mixer_authz_projects j ON (((j.organization_id = o.id) AND (j.id = current_setting('mixer.authz.project_id'::text, true)))))\n     JOIN mixer_authz_organization_heads oh ON ((oh.organization_id = o.id)))\n     JOIN mixer_authz_project_heads ph ON (((ph.organization_id = o.id) AND (ph.project_id = j.id))))\n  WHERE ((p.id = current_setting('mixer.authz.profile_id'::text, true)) AND ((p.version)::text = current_setting('mixer.authz.profile_version'::text, true)) AND (p.issuer = current_setting('mixer.authz.issuer'::text, true)) AND (p.client_id = current_setting('mixer.authz.client_id'::text, true)) AND (p.identity_class = 'human'::text) AND (b.identity_class = 'human'::text) AND (a.identity_class = 'human'::text) AND p.active AND b.active AND a.active AND c.active AND f.active AND o.active AND j.active AND (b.subject = current_setting('mixer.authz.subject'::text, true)) AND (a.id = current_setting('mixer.authz.principal_id'::text, true)) AND (c.reference = current_setting('mixer.authz.credential_ref'::text, true)) AND (f.id = current_setting('mixer.authz.family_id'::text, true)) AND ((current_setting('mixer.authz.token_issued_at'::text, true))::bigint >= GREATEST(a.not_before, c.not_before, f.not_before)) AND ((current_setting('mixer.authz.token_issued_at'::text, true))::bigint <= ((floor(EXTRACT(epoch FROM statement_timestamp())))::bigint + 30)) AND ((current_setting('mixer.authz.token_expires_at'::text, true))::bigint > (floor(EXTRACT(epoch FROM statement_timestamp())))::bigint) AND (GREATEST(a.not_before, c.not_before, f.not_before) <= (floor(EXTRACT(epoch FROM statement_timestamp())))::bigint) AND ((c.expires_at IS NULL) OR (c.expires_at > (floor(EXTRACT(epoch FROM statement_timestamp())))::bigint)) AND ((f.expires_at IS NULL) OR (f.expires_at > (floor(EXTRACT(epoch FROM statement_timestamp())))::bigint)) AND (EXISTS ( SELECT 1\n           FROM mixer_authz_memberships m\n          WHERE ((m.principal_id = a.id) AND (m.organization_id = o.id) AND (((m.project_binding = 'all_projects'::text) AND (m.project_id IS NULL)) OR ((m.project_binding = 'exact_project'::text) AND (m.project_id = j.id))) AND (m.role = ANY (ARRAY['owner'::text, 'administrator'::text, 'developer'::text, 'release_manager'::text, 'viewer'::text])) AND m.active AND (m.not_before <= (floor(EXTRACT(epoch FROM statement_timestamp())))::bigint) AND ((m.expires_at IS NULL) OR (m.expires_at > (floor(EXTRACT(epoch FROM statement_timestamp())))::bigint))))) AND (( SELECT count(*) AS count\n           FROM mixer_authz_memberships m\n          WHERE ((m.principal_id = a.id) AND (m.organization_id = o.id))) <= 64)))))"

  def private_statements do
    prefix =
      "CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT;\nGRANT USAGE ON SCHEMA public TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_profiles TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_principals TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_bindings TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_families TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_credentials TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_organizations TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_projects TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_applications TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_organization_heads TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_project_heads TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT ON public.mixer_authz_memberships TO mixer_customer_build_catalog_definer_v1;\nGRANT UPDATE ON public.mixer_authz_bindings TO mixer_customer_build_catalog_definer_v1;\nGRANT UPDATE ON public.mixer_authz_organizations TO mixer_customer_build_catalog_definer_v1;\nGRANT UPDATE ON public.mixer_authz_projects TO mixer_customer_build_catalog_definer_v1;\nGRANT UPDATE ON public.mixer_authz_memberships TO mixer_customer_build_catalog_definer_v1;\nGRANT UPDATE ON public.mixer_authz_applications TO mixer_customer_build_catalog_definer_v1;\nGRANT SELECT, UPDATE ON public.mixer_builds TO mixer_customer_build_catalog_definer_v1;\nCREATE POLICY catalog_applications_read_v1 ON public.mixer_authz_applications FOR SELECT TO mixer_customer_build_catalog_definer_v1 USING (current_setting('mixer.authz.phase',true) = 'build_catalog_applications'\nAND current_setting('mixer.authz.action',true) = 'build.read'\nAND current_setting('mixer.authz.required_scope',true) = 'mixer.build.read'\nAND COALESCE(current_setting('mixer.authz.application_id',true),'') = ''\nAND COALESCE(current_setting('mixer.authz.environment_id',true),'') = ''\nAND COALESCE(current_setting('mixer.authz.directory_mode',true),'') = ''\nAND current_setting('mixer.authz.transaction_marker',true) ~ '^[0-9a-f]{64}$'\nAND organization_id = current_setting('mixer.authz.organization_id',true)\nAND project_id = current_setting('mixer.authz.project_id',true)\nAND active AND EXISTS (SELECT 1 FROM public.mixer_authz_profiles p\n      JOIN public.mixer_authz_bindings b ON (b.profile_id,b.profile_version)=(p.id,p.version)\n      JOIN public.mixer_authz_principals a ON a.id=b.principal_id\n      JOIN public.mixer_authz_credentials c ON (c.profile_id,c.profile_version,c.principal_id)=(p.id,p.version,a.id)\n      JOIN public.mixer_authz_families f ON (f.id,f.profile_id,f.profile_version,f.principal_id)=(c.family_id,p.id,p.version,a.id)\n      JOIN public.mixer_authz_organizations o ON o.id=current_setting('mixer.authz.organization_id',true)\n      JOIN public.mixer_authz_projects j ON j.organization_id=o.id AND j.id=current_setting('mixer.authz.project_id',true)\n      JOIN public.mixer_authz_organization_heads oh ON oh.organization_id=o.id\n      JOIN public.mixer_authz_project_heads ph ON (ph.organization_id,ph.project_id)=(o.id,j.id)\n      WHERE p.id=current_setting('mixer.authz.profile_id',true)\n        AND p.version::text=current_setting('mixer.authz.profile_version',true)\n        AND p.issuer=current_setting('mixer.authz.issuer',true)\n        AND p.client_id=current_setting('mixer.authz.client_id',true)\n        AND p.identity_class='human' AND b.identity_class='human' AND a.identity_class='human'\n        AND p.active AND b.active AND a.active AND c.active AND f.active\n        AND o.active AND j.active\n        AND b.subject=current_setting('mixer.authz.subject',true)\n        AND a.id=current_setting('mixer.authz.principal_id',true)\n        AND c.reference=current_setting('mixer.authz.credential_ref',true)\n        AND f.id=current_setting('mixer.authz.family_id',true)\n        AND current_setting('mixer.authz.token_issued_at',true)::bigint >= greatest(a.not_before,c.not_before,f.not_before)\n        AND current_setting('mixer.authz.token_issued_at',true)::bigint <= floor(extract(epoch FROM statement_timestamp()))::bigint+30\n        AND current_setting('mixer.authz.token_expires_at',true)::bigint > floor(extract(epoch FROM statement_timestamp()))::bigint\n        AND greatest(a.not_before,c.not_before,f.not_before) <= floor(extract(epoch FROM statement_timestamp()))::bigint\n        AND (c.expires_at IS NULL OR c.expires_at>floor(extract(epoch FROM statement_timestamp()))::bigint)\n        AND (f.expires_at IS NULL OR f.expires_at>floor(extract(epoch FROM statement_timestamp()))::bigint)\n        AND EXISTS (SELECT 1 FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id\n          AND m.organization_id=o.id AND ((m.project_binding='all_projects' AND m.project_id IS NULL)\n            OR (m.project_binding='exact_project' AND m.project_id=j.id))\n          AND m.role IN ('owner','administrator','developer','release_manager','viewer')\n          AND m.active AND m.not_before<=floor(extract(epoch FROM statement_timestamp()))::bigint AND (m.expires_at IS NULL OR m.expires_at>floor(extract(epoch FROM statement_timestamp()))::bigint))\n        AND (SELECT count(*) FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND m.organization_id=o.id) <= 64));\nCREATE POLICY catalog_applications_lock_v1 ON public.mixer_authz_applications FOR UPDATE TO mixer_customer_build_catalog_definer_v1 USING (current_setting('mixer.authz.phase',true) = 'build_catalog_applications'\nAND current_setting('mixer.authz.action',true) = 'build.read'\nAND current_setting('mixer.authz.required_scope',true) = 'mixer.build.read'\nAND COALESCE(current_setting('mixer.authz.application_id',true),'') = ''\nAND COALESCE(current_setting('mixer.authz.environment_id',true),'') = ''\nAND COALESCE(current_setting('mixer.authz.directory_mode',true),'') = ''\nAND current_setting('mixer.authz.transaction_marker',true) ~ '^[0-9a-f]{64}$'\nAND organization_id = current_setting('mixer.authz.organization_id',true)\nAND project_id = current_setting('mixer.authz.project_id',true)\nAND active AND EXISTS (SELECT 1 FROM public.mixer_authz_profiles p\n      JOIN public.mixer_authz_bindings b ON (b.profile_id,b.profile_version)=(p.id,p.version)\n      JOIN public.mixer_authz_principals a ON a.id=b.principal_id\n      JOIN public.mixer_authz_credentials c ON (c.profile_id,c.profile_version,c.principal_id)=(p.id,p.version,a.id)\n      JOIN public.mixer_authz_families f ON (f.id,f.profile_id,f.profile_version,f.principal_id)=(c.family_id,p.id,p.version,a.id)\n      JOIN public.mixer_authz_organizations o ON o.id=current_setting('mixer.authz.organization_id',true)\n      JOIN public.mixer_authz_projects j ON j.organization_id=o.id AND j.id=current_setting('mixer.authz.project_id',true)\n      JOIN public.mixer_authz_organization_heads oh ON oh.organization_id=o.id\n      JOIN public.mixer_authz_project_heads ph ON (ph.organization_id,ph.project_id)=(o.id,j.id)\n      WHERE p.id=current_setting('mixer.authz.profile_id',true)\n        AND p.version::text=current_setting('mixer.authz.profile_version',true)\n        AND p.issuer=current_setting('mixer.authz.issuer',true)\n        AND p.client_id=current_setting('mixer.authz.client_id',true)\n        AND p.identity_class='human' AND b.identity_class='human' AND a.identity_class='human'\n        AND p.active AND b.active AND a.active AND c.active AND f.active\n        AND o.active AND j.active\n        AND b.subject=current_setting('mixer.authz.subject',true)\n        AND a.id=current_setting('mixer.authz.principal_id',true)\n        AND c.reference=current_setting('mixer.authz.credential_ref',true)\n        AND f.id=current_setting('mixer.authz.family_id',true)\n        AND current_setting('mixer.authz.token_issued_at',true)::bigint >= greatest(a.not_before,c.not_before,f.not_before)\n        AND current_setting('mixer.authz.token_issued_at',true)::bigint <= floor(extract(epoch FROM statement_timestamp()))::bigint+30\n        AND current_setting('mixer.authz.token_expires_at',true)::bigint > floor(extract(epoch FROM statement_timestamp()))::bigint\n        AND greatest(a.not_before,c.not_before,f.not_before) <= floor(extract(epoch FROM statement_timestamp()))::bigint\n        AND (c.expires_at IS NULL OR c.expires_at>floor(extract(epoch FROM statement_timestamp()))::bigint)\n        AND (f.expires_at IS NULL OR f.expires_at>floor(extract(epoch FROM statement_timestamp()))::bigint)\n        AND EXISTS (SELECT 1 FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id\n          AND m.organization_id=o.id AND ((m.project_binding='all_projects' AND m.project_id IS NULL)\n            OR (m.project_binding='exact_project' AND m.project_id=j.id))\n          AND m.role IN ('owner','administrator','developer','release_manager','viewer')\n          AND m.active AND m.not_before<=floor(extract(epoch FROM statement_timestamp()))::bigint AND (m.expires_at IS NULL OR m.expires_at>floor(extract(epoch FROM statement_timestamp()))::bigint))\n        AND (SELECT count(*) FROM public.mixer_authz_memberships m WHERE m.principal_id=a.id AND m.organization_id=o.id) <= 64)) WITH CHECK (false);\n"

    statements =
      prefix |> String.split(";", trim: true) |> Enum.reject(&String.contains?(&1, "CREATE ROLE"))

    statements ++
      Enum.flat_map([:applications, :builds], fn kind ->
        f = "public.#{name(kind)}(#{signature(kind)})"

        [
          ddl(kind),
          "REVOKE ALL ON FUNCTION #{f} FROM PUBLIC",
          "ALTER FUNCTION #{f} OWNER TO #{role()}",
          "GRANT EXECUTE ON FUNCTION #{f} TO browser_ordinary"
        ]
      end)
  end

  @doc false
  def surface_contract do
    select =
      Enum.map(
        ~w(profiles principals bindings families credentials organizations projects applications organization_heads project_heads memberships),
        &("public.mixer_authz_" <> &1)
      ) ++ ["public.mixer_builds"]

    update =
      Enum.map(
        ~w(bindings organizations projects memberships applications),
        &("public.mixer_authz_" <> &1)
      ) ++ ["public.mixer_builds"]

    %{
      role: role(),
      functions:
        Enum.map([:applications, :builds], fn kind ->
          %{name: name(kind), signature: signature(kind), body: body(kind)}
        end),
      grants: Enum.map(select, &{&1, "SELECT"}) ++ Enum.map(update, &{&1, "UPDATE"}),
      policies: [
        %{name: "catalog_applications_read_v1", command: "r", check: nil},
        %{name: "catalog_applications_lock_v1", command: "w", check: "false"}
      ],
      policy_expression: lifecycle_policy_expression(),
      old_policies: [
        %{name: "scoped_read", command: "r", check: nil},
        %{name: "scoped_lock", command: "w", check: "false"}
      ],
      old_policy_expression: old_application_policy_expression()
    }
  end

  defp lifecycle_policy_expression do
    Enum.reduce(
      ~w(profiles principals bindings families credentials organizations projects applications organization_heads project_heads memberships),
      policy_expression(),
      fn suffix, expression ->
        name = "mixer_authz_" <> suffix
        String.replace(expression, name <> " ", "public." <> name <> " ")
      end
    )
  end

  defp old_application_policy_expression do
    "((organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (project_id = current_setting('mixer.authz.project_id'::text, true)) AND (id = current_setting('mixer.authz.application_id'::text, true)) AND (EXISTS ( SELECT 1\n   FROM public.mixer_authz_memberships m\n  WHERE ((m.principal_id = current_setting('mixer.authz.principal_id'::text, true)) AND (m.organization_id = current_setting('mixer.authz.organization_id'::text, true)) AND (((m.project_binding = 'all_projects'::text) AND (m.project_id IS NULL)) OR ((m.project_binding = 'exact_project'::text) AND (m.project_id = current_setting('mixer.authz.project_id'::text, true)))) AND m.active AND ((m.not_before)::numeric <= EXTRACT(epoch FROM statement_timestamp())) AND ((m.expires_at IS NULL) OR ((m.expires_at)::numeric > EXTRACT(epoch FROM statement_timestamp())))))))"
  end

  def admit!(repo, kind) do
    [safe] =
      MixerHosted.Authorization.Postgres.Session.one!(
        repo,
        """
        SELECT count(*)=1 AND bool_and(p.prosrc=$1 AND p.prosecdef AND p.provolatile='v'
          AND p.prorettype='jsonb'::regtype AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND pg_get_function_identity_arguments(p.oid)=$3
          AND owner.rolname=$4 AND NOT owner.rolcanlogin AND NOT owner.rolsuper AND NOT owner.rolbypassrls
          AND NOT owner.rolcreatedb AND NOT owner.rolcreaterole AND NOT owner.rolreplication AND NOT owner.rolinherit
          AND NOT pg_has_role(current_user,p.proowner,'MEMBER')
          AND has_function_privilege(current_user,p.oid,'EXECUTE')
          AND (SELECT count(*) FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) x)=2
          AND NOT EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) x
            WHERE x.privilege_type<>'EXECUTE' OR x.is_grantable OR x.grantee NOT IN (p.proowner,(SELECT oid FROM pg_roles WHERE rolname=current_user)))
          AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=owner.oid OR roleid=owner.oid)
          AND (SELECT count(*) FROM pg_proc WHERE proowner=owner.oid)=2
          AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relowner=owner.oid)
          AND NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner=owner.oid)
          AND NOT EXISTS (SELECT 1 FROM pg_database WHERE datdba=owner.oid)
          AND NOT has_schema_privilege(owner.oid,'public','CREATE')
          AND NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace
            WHERE ns.nspname='public' AND c.relkind IN ('r','p','v','m','S','f') AND (
              has_table_privilege(owner.oid,c.oid,'INSERT,DELETE,TRUNCATE,REFERENCES,TRIGGER')
              OR has_any_column_privilege(owner.oid,c.oid,'INSERT,REFERENCES')
              OR (has_table_privilege(owner.oid,c.oid,'SELECT') IS DISTINCT FROM (c.relname=ANY($6::text[])))
              OR (has_table_privilege(owner.oid,c.oid,'UPDATE') IS DISTINCT FROM (c.relname=ANY($7::text[])))
              OR (has_any_column_privilege(owner.oid,c.oid,'UPDATE') AND NOT c.relname=ANY($7::text[]))))
          AND NOT EXISTS (SELECT 1 FROM pg_proc other JOIN pg_namespace ns ON ns.oid=other.pronamespace
            WHERE ns.nspname='public' AND other.proowner<>owner.oid AND has_function_privilege(owner.oid,other.oid,'EXECUTE'))
          AND (SELECT count(*) FROM pg_policy x WHERE x.polrelid='public.mixer_authz_applications'::regclass
            AND x.polname IN ('catalog_applications_read_v1','catalog_applications_lock_v1')
            AND x.polpermissive AND x.polroles=ARRAY[owner.oid]
            AND pg_get_expr(x.polqual,x.polrelid)=$5
            AND ((x.polname='catalog_applications_read_v1' AND x.polcmd='r' AND x.polwithcheck IS NULL)
              OR (x.polname='catalog_applications_lock_v1' AND x.polcmd='w' AND pg_get_expr(x.polwithcheck,x.polrelid)='false')))=2)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles owner ON owner.oid=p.proowner
        WHERE n.nspname='public' AND p.proname=$2
        """,
        [
          body(kind),
          name(kind),
          String.replace(signature(kind), ",", ", "),
          role(),
          policy_expression(),
          Enum.map(
            ~w(profiles principals bindings families credentials organizations projects applications organization_heads project_heads memberships),
            &("mixer_authz_" <> &1)
          ) ++ ["mixer_builds"],
          Enum.map(
            ~w(bindings organizations projects memberships applications),
            &("mixer_authz_" <> &1)
          ) ++ ["mixer_builds"]
        ],
        :authorization_unavailable
      )

    if safe != true, do: repo.rollback(:authorization_unavailable)
    :ok
  end
end
