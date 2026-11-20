defmodule MixerHosted.CustomerArtifacts.Topology do
  @moduledoc false
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.CustomerArtifacts.Schema
  @catalog_sha256 "ff576c90a10e0bc098f3c7b593640f508aa676a166b8e2123257501f50eb375e"

  def check!(repo) do
    [[role_safe]] =
      Session.query!(repo, """
      SELECT current_user=session_user
        AND NOT pg_catalog.has_schema_privilege(current_user,'public','CREATE')
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE pg_catalog.pg_has_role(current_user,r.oid,'MEMBER')
          AND (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR pg_catalog.substr(r.rolname::text,1,3)='pg_'))
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n, LATERAL pg_catalog.aclexplode(coalesce(n.nspacl,pg_catalog.acldefault('n',n.nspowner))) a WHERE n.nspname='public' AND a.grantee=0 AND a.privilege_type='CREATE')
      """).rows

    [[4, tables_safe]] =
      Session.query!(
        repo,
        """
        SELECT count(*),bool_and(c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity
          AND c.relowner=(SELECT relowner FROM pg_catalog.pg_class WHERE oid='public.mixer_customer_artifacts'::regclass)
          AND NOT o.rolcanlogin AND NOT o.rolsuper AND NOT o.rolbypassrls
          AND NOT pg_catalog.pg_has_role(current_user,o.oid,'MEMBER')
          AND pg_catalog.has_table_privilege(current_user,c.oid,'SELECT')
          AND NOT pg_catalog.has_table_privilege(current_user,c.oid,'DELETE,TRUNCATE,REFERENCES,TRIGGER')
          AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'REFERENCES')
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.aclexplode(coalesce(c.relacl,pg_catalog.acldefault('r',c.relowner))) a WHERE a.grantee=0)
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute att,LATERAL pg_catalog.aclexplode(att.attacl) acl WHERE att.attrelid=c.oid AND acl.grantee=0)
          AND CASE WHEN c.relname='mixer_customer_artifact_heads' THEN
            NOT pg_catalog.has_table_privilege(current_user,c.oid,'INSERT,UPDATE')
            AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'INSERT')
            AND (SELECT count(*)=3 AND bool_and(a.attname IN ('sequence','event_sha256','state_sha256')) FROM pg_catalog.pg_attribute a
              WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped AND pg_catalog.has_column_privilege(current_user,c.oid,a.attnum,'UPDATE'))
          ELSE pg_catalog.has_table_privilege(current_user,c.oid,'INSERT') AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'UPDATE') END)
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_roles o ON o.oid=c.relowner
        WHERE n.nspname='public' AND c.relname=ANY($1::text[])
        """,
        [Schema.tables()]
      ).rows

    functions_safe =
      Enum.all?(Schema.functions_sql(), fn {name, {_args, returns, volatility, definer, body}} ->
        case Session.query!(
               repo,
               """
               SELECT count(*),bool_and(p.prosrc=$2 AND p.prosecdef=$3 AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
                 AND p.provolatile=$4::"char" AND p.proowner=c.relowner
               AND p.prolang=(SELECT oid FROM pg_catalog.pg_language WHERE lanname='plpgsql') AND NOT p.proleakproof AND NOT p.proisstrict
               AND p.proparallel='u' AND p.prokind='f' AND p.provariadic=0 AND p.pronargdefaults=0 AND p.prosupport=0
               AND pg_catalog.regexp_replace(pg_catalog.pg_get_function_result(p.oid),'[[:space:]]','','g')=pg_catalog.regexp_replace($7,'[[:space:]]','','g')
                 AND NOT o.rolcanlogin AND NOT o.rolsuper AND NOT o.rolbypassrls AND NOT pg_catalog.pg_has_role(current_user,o.oid,'MEMBER')
                 AND pg_catalog.pg_get_function_identity_arguments(p.oid)=$5
                 AND pg_catalog.has_function_privilege(current_user,p.oid,'EXECUTE')=$6
                 AND NOT EXISTS (SELECT 1 FROM pg_catalog.aclexplode(coalesce(p.proacl,pg_catalog.acldefault('f',p.proowner))) a WHERE a.grantee=0))
               FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace JOIN pg_catalog.pg_roles o ON o.oid=p.proowner
                 CROSS JOIN pg_catalog.pg_class c
               WHERE n.nspname='public' AND p.proname=$1 AND c.oid='public.mixer_customer_artifacts'::regclass
               """,
               [
                 name,
                 "\n" <> body,
                 definer,
                 String.downcase(String.first(volatility)),
                 identity_arguments(name),
                 name in ~w(mixer_customer_allowed mixer_customer_artifact_metadata mixer_customer_key_exists),
                 returns
               ]
             ).rows do
          [[1, true]] -> true
          _ -> false
        end
      end)

    [[no_bypass]] =
      Session.query!(
        repo,
        """
        SELECT NOT EXISTS (
          SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND pg_catalog.substr(n.nspname,1,8)<>'pg_temp_'
            AND (p.prosecdef OR p.provolatile='v') AND pg_catalog.has_function_privilege(current_user,p.oid,'EXECUTE')
            AND NOT (n.nspname='public' AND p.proname=ANY($1::text[]))
        ) AND NOT EXISTS (
          SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND c.relkind IN ('v','m','f') AND (pg_catalog.has_table_privilege(current_user,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR pg_catalog.has_any_column_privilege(current_user,c.oid,'INSERT,UPDATE'))
        )
        """,
        [
          ~w(mixer_authz_lock_profiles mixer_authz_lock_principals mixer_authz_lock_families mixer_authz_lock_credentials mixer_authz_lock_organization_heads mixer_authz_lock_project_heads mixer_customer_artifact_metadata mixer_customer_key_exists)
        ]
      ).rows

    if role_safe and tables_safe and functions_safe and no_bypass and
         catalog_hash(repo) == @catalog_sha256,
       do: :ok,
       else: reject!(repo)
  end

  defp reject!(repo) do
    if MixerHosted.Authorization.Transaction.Context.active?() do
      # A deliberately invalid checkpoint uses Context's owner-process failure
      # latch. Catching the rollback cannot rescue prior callback writes.
      MixerHosted.Authorization.Transaction.Context.checkpoint!(nil, repo, "", nil)
    else
      repo.rollback(:authorization_unavailable)
    end
  end

  @doc false
  def catalog_hash(repo) do
    [[digest]] =
      Session.query!(
        repo,
        """
        SELECT encode(sha256(convert_to(jsonb_build_object(
          'columns',(SELECT jsonb_agg(jsonb_build_array(c.relname,a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_catalog.pg_get_expr(d.adbin,d.adrelid)) ORDER BY c.relname,a.attnum)
            FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid
            LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname='public' AND c.relname=ANY($1::text[]) AND a.attnum>0 AND NOT a.attisdropped),
          'constraints',(SELECT jsonb_agg(jsonb_build_array(c.relname,k.conname,k.contype,k.condeferrable,k.condeferred,k.convalidated,pg_catalog.pg_get_constraintdef(k.oid)) ORDER BY c.relname,k.conname)
            FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_class c ON c.oid=k.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY($1::text[])),
          'policies',(SELECT jsonb_agg(jsonb_build_array(c.relname,p.polname,p.polcmd,p.polpermissive,p.polroles,pg_catalog.pg_get_expr(p.polqual,p.polrelid),pg_catalog.pg_get_expr(p.polwithcheck,p.polrelid)) ORDER BY c.relname,p.polname)
            FROM pg_catalog.pg_policy p JOIN pg_catalog.pg_class c ON c.oid=p.polrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY($1::text[])),
          'triggers',(SELECT jsonb_agg(jsonb_build_array(c.relname,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_catalog.pg_get_triggerdef(t.oid)) ORDER BY c.relname,t.tgname)
            FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY($1::text[]) AND NOT t.tgisinternal)
        )::text,'UTF8')),'hex')
        """,
        [Schema.tables()]
      ).rows

    digest
  end

  defp identity_arguments(name) do
    {args, _, _, _, _} = Schema.functions_sql()[name]
    args |> String.split(",", trim: true) |> Enum.map(&String.trim/1) |> Enum.join(", ")
  end
end
