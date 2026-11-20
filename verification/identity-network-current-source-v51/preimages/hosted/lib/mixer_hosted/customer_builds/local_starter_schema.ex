defmodule MixerHosted.CustomerBuilds.LocalStarterSchema do
  @moduledoc "Optional private catalog and fixed writer for a trusted local starter."
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.CustomerBuilds.CreateSchema
  @function "public.mixer_local_starter_v1(text,text,jsonb,boolean)"

  def body do
    """
    DECLARE starter record; existing record;
      org text := current_setting('mixer.authz.organization_id',true);
      project text := current_setting('mixer.authz.project_id',true);
      app text := current_setting('mixer.authz.application_id',true);
    BEGIN
      IF $4 IS NULL OR session_user <> 'mixer_build_create'
        OR (#{CreateSchema.guard()}) IS DISTINCT FROM true
        OR NOT EXISTS (
          SELECT 1 FROM public.mixer_authz_memberships
          WHERE organization_id=org AND principal_id=current_setting('mixer.authz.principal_id',true)
            AND project_id IS NULL AND project_binding='all_projects' AND role='owner' AND active
            AND not_before<=extract(epoch FROM clock_timestamp())
            AND (expires_at IS NULL OR expires_at>extract(epoch FROM clock_timestamp()))
        )
      THEN RETURN 'denied'; END IF;

      SELECT * INTO starter FROM public.mixer_local_starters
        WHERE (organization_id,project_id,application_id)=(org,project,app)
          AND input_id=$1 AND registration_pin=$2 AND spec=$3
        FOR SHARE;
      IF NOT FOUND THEN RETURN 'missing'; END IF;
      IF NOT $4 THEN RETURN 'available'; END IF;

      -- Serialize first selection within an app without upgrading the existing
      -- authorization locks. Runtime roles have no direct input write grant.
      IF NOT pg_try_advisory_xact_lock(hashtextextended(
        jsonb_build_array('mixer-local-starter-v1',org,project,app)::text,0
      )) THEN RETURN 'conflict'; END IF;

      SELECT platform,input_id,source_kind,source_reference,source_sha256,
        toolchain_lock_sha256,build_definition_sha256,max_attempts,timeout_ms,retry_backoff_ms
        INTO existing FROM public.mixer_customer_build_inputs
        WHERE (organization_id,project_id,application_id)=(org,project,app);
      IF FOUND THEN
        IF existing IS DISTINCT FROM ROW('ios'::text,$1,$3#>>'{source,kind}',
           $3#>>'{source,reference}',$3#>>'{source,sha256}',$3->>'toolchain_lock_sha256',
           $3->>'build_definition_sha256',1,1800000::bigint,0::bigint)
          OR (SELECT count(*) FROM public.mixer_customer_build_inputs
             WHERE (organization_id,project_id,application_id)=(org,project,app))<>1
        THEN RETURN 'conflict'; END IF;
        RETURN 'selected';
      END IF;

      INSERT INTO public.mixer_customer_build_inputs
        (organization_id,project_id,application_id,platform,input_id,source_kind,source_reference,
         source_sha256,toolchain_lock_sha256,build_definition_sha256,max_attempts,timeout_ms,retry_backoff_ms)
      VALUES (org,project,app,'ios',$1,$3#>>'{source,kind}',$3#>>'{source,reference}',
        $3#>>'{source,sha256}',$3->>'toolchain_lock_sha256',$3->>'build_definition_sha256',1,1800000,0);
      RETURN 'selected';
    END
    """
  end

  def statements do
    [
      """
      CREATE TABLE public.mixer_local_starters(
        organization_id text NOT NULL, project_id text NOT NULL, application_id text NOT NULL,
        input_id text NOT NULL, registration_pin text NOT NULL CHECK(registration_pin ~ '^[0-9a-f]{64}$'),
        spec jsonb NOT NULL CHECK(jsonb_typeof(spec)='object'),
        PRIMARY KEY (organization_id,project_id,application_id),
        FOREIGN KEY (organization_id,project_id,application_id)
          REFERENCES public.mixer_authz_applications(organization_id,project_id,id))
      """,
      "REVOKE ALL ON public.mixer_local_starters FROM PUBLIC",
      """
      CREATE FUNCTION #{@function} RETURNS text LANGUAGE plpgsql VOLATILE
      SECURITY DEFINER SET search_path=pg_catalog AS $starter$#{body()}$starter$
      """,
      "REVOKE ALL ON FUNCTION #{@function} FROM PUBLIC",
      "GRANT EXECUTE ON FUNCTION #{@function} TO mixer_build_create"
    ]
  end

  def admit!(repo) do
    [true] =
      Session.one!(
        repo,
        """
        SELECT count(*)=1 AND bool_and(
          p.prosrc=$1 AND p.prosecdef AND p.provolatile='v' AND p.prorettype='text'::regtype
          AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND p.prolang=(SELECT oid FROM pg_language WHERE lanname='plpgsql')
          AND owner.rolname='browser_schema_owner' AND NOT owner.rolcanlogin
          AND NOT owner.rolsuper AND NOT owner.rolbypassrls
          AND NOT pg_has_role(current_user,p.proowner,'MEMBER')
          AND (SELECT count(*) FROM aclexplode(p.proacl))=2
          AND NOT EXISTS(SELECT 1 FROM aclexplode(p.proacl) a WHERE a.is_grantable OR
            a.privilege_type<>'EXECUTE' OR a.grantee NOT IN
            (p.proowner,(SELECT oid FROM pg_roles WHERE rolname='mixer_build_create')))
          AND has_function_privilege(current_user,p.oid,'EXECUTE')
          AND NOT has_function_privilege('browser_ordinary',p.oid,'EXECUTE')
          AND EXISTS (SELECT 1 FROM pg_class r
          WHERE r.oid='public.mixer_local_starters'::regclass
            AND r.relkind='r' AND r.relpersistence='p' AND r.relowner=p.proowner)
        AND NOT has_table_privilege(current_user,'public.mixer_local_starters','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          AND NOT has_table_privilege('browser_ordinary','public.mixer_local_starters','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          AND NOT has_any_column_privilege(current_user,'public.mixer_local_starters','SELECT,INSERT,UPDATE,REFERENCES')
          AND NOT has_any_column_privilege('browser_ordinary','public.mixer_local_starters','SELECT,INSERT,UPDATE,REFERENCES')
          AND NOT has_any_column_privilege(current_user,'public.mixer_customer_build_inputs','INSERT,UPDATE,REFERENCES')
          AND NOT has_any_column_privilege('browser_ordinary','public.mixer_customer_build_inputs','INSERT,UPDATE,REFERENCES')
          AND NOT has_table_privilege(current_user,'public.mixer_customer_build_inputs','DELETE,TRUNCATE,REFERENCES,TRIGGER')
          AND NOT has_table_privilege('browser_ordinary','public.mixer_customer_build_inputs','DELETE,TRUNCATE,REFERENCES,TRIGGER'))
        FROM pg_proc p JOIN pg_roles owner ON owner.oid=p.proowner
        WHERE p.oid=to_regprocedure($2)
        """,
        [body(), @function],
        :authorization_unavailable
      )

    :ok
  end
end
