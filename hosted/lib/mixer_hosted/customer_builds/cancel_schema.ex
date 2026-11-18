defmodule MixerHosted.CustomerBuilds.CancelSchema do
  @moduledoc false
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Builds.OperationIntentSchema

  @name "mixer_customer_build_cancel_v1"
  @entry "public.#{@name}(text,text,text,text,text)"
  @external_resource Path.expand("../../../priv/unselected_build_cancel/cancel_body.sql", __DIR__)
  @body File.read!(@external_resource)

  def statements do
    [
      "CREATE FUNCTION #{@entry} RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $cancel$" <>
        @body <> "$cancel$",
      "REVOKE ALL ON FUNCTION #{@entry} FROM PUBLIC",
      "GRANT EXECUTE ON FUNCTION #{@entry} TO mixer_build_create"
    ]
  end

  def admit!(repo) do
    [safe] =
      Session.one!(
        repo,
        """
        SELECT count(*)=1 AND COALESCE(bool_and(
          p.oid=to_regprocedure($2) AND p.prosrc=$3 AND p.prosecdef
          AND p.provolatile='v' AND p.proparallel='u' AND p.prokind='f'
          AND NOT p.proretset AND NOT p.proisstrict AND NOT p.proleakproof
          AND p.pronargdefaults=0 AND p.prosupport=0 AND p.provariadic=0
          AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND p.prorettype='jsonb'::regtype AND l.lanname='plpgsql'
          AND o.rolname='browser_schema_owner' AND NOT (o.rolcanlogin OR o.rolsuper OR o.rolbypassrls)
          AND c.rolname='mixer_build_create' AND c.rolcanlogin
          AND NOT (c.rolsuper OR c.rolbypassrls OR c.rolinherit OR c.rolcreatedb OR c.rolcreaterole)
          AND NOT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=c.oid OR roleid=c.oid)
          AND has_function_privilege(c.oid,p.oid,'EXECUTE')
          AND NOT EXISTS (
            SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
            WHERE a.grantor<>p.proowner OR a.privilege_type<>'EXECUTE' OR a.is_grantable
               OR a.grantee NOT IN (p.proowner,c.oid)
          )
        ),false)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_roles o ON o.oid=p.proowner JOIN pg_language l ON l.oid=p.prolang
        JOIN pg_roles c ON c.rolname='mixer_build_create'
        WHERE n.nspname='public' AND p.proname=$1
        """,
        [@name, @entry, @body],
        :authorization_unavailable
      )

    query = fn sql, params -> Session.query!(repo, sql, params).rows end

    unless safe == true and OperationIntentSchema.compatible?(query, :required),
      do: repo.rollback(:authorization_unavailable)

    :ok
  end
end
