SET search_path=pg_catalog;
WITH targets AS (
 SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relname=ANY(ARRAY['mixer_browser_sessions','mixer_browser_session_vault','mixer_browser_oidc_attempts','mixer_browser_session_events','mixer_authz_profiles','mixer_authz_principals','mixer_authz_bindings','mixer_authz_families','mixer_authz_credentials'])
), fks AS (
 SELECT c.* FROM pg_constraint c WHERE contype='f' AND (conrelid IN(SELECT oid FROM targets) OR confrelid IN(SELECT oid FROM targets))
), links AS (
 SELECT c.oid::text AS constraint_oid,c.conrelid::regclass::text AS child,c.confrelid::regclass::text AS parent,
 c.conindid::text AS index_oid,cardinality(c.conkey) AS key_count,
 (SELECT count(*) FROM pg_trigger t WHERE t.tgconstraint=c.oid) AS trigger_count,
 (SELECT count(*) FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE t.tgconstraint=c.oid AND t.tgisinternal AND t.tgenabled='O' AND t.tgconstrindid=c.conindid
  AND ((p.proname='RI_FKey_check_ins' AND t.tgtype=5 AND t.tgrelid=c.conrelid AND t.tgconstrrelid=c.confrelid)
    OR (p.proname='RI_FKey_check_upd' AND t.tgtype=17 AND t.tgrelid=c.conrelid AND t.tgconstrrelid=c.confrelid)
    OR (p.proname='RI_FKey_noaction_del' AND t.tgtype=9 AND t.tgrelid=c.confrelid AND t.tgconstrrelid=c.conrelid)
    OR (p.proname='RI_FKey_noaction_upd' AND t.tgtype=17 AND t.tgrelid=c.confrelid AND t.tgconstrrelid=c.conrelid))
  AND n.nspname='pg_catalog' AND p.pronargs=0 AND p.prorettype='trigger'::regtype) AS linked_count,
 (SELECT count(*) FROM unnest(c.conpfeqop||c.conppeqop||c.conffeqop) x) AS operator_count,
 (SELECT bool_and(n.nspname='pg_catalog' AND o.oprname='=' AND o.oprleft=o.oprright
  AND o.oprleft IN('text'::regtype,'bytea'::regtype,'int4'::regtype,'int8'::regtype))
  FROM unnest(c.conpfeqop||c.conppeqop||c.conffeqop) x JOIN pg_operator o ON o.oid=x JOIN pg_namespace n ON n.oid=o.oprnamespace) AS builtin_operators
 FROM fks c ORDER BY c.conrelid,c.oid LIMIT 13
), functions AS (
 SELECT DISTINCT p.oid::text AS function_oid,n.nspname AS namespace,p.proname AS name,p.prosrc,
 p.pronargs=0 AS noarg,p.prorettype='trigger'::regtype AS returns_trigger,p.prosecdef AS security_definer,r.rolname AS owner
 FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner
 WHERE t.tgrelid IN(SELECT oid FROM targets) AND NOT t.tgisinternal
 ORDER BY name LIMIT 5
)
SELECT json_build_object('foreign_keys',(SELECT json_agg(l) FROM links l),'user_functions',(SELECT json_agg(f) FROM functions f));
