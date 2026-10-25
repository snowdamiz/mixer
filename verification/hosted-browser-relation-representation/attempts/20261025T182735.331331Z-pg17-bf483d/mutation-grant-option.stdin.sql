BEGIN;
GRANT SELECT ON public.mixer_browser_sessions TO browser_writer WITH GRANT OPTION;
SET search_path=pg_catalog;
WITH targets AS (
 SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relname=ANY(ARRAY['mixer_browser_sessions','mixer_browser_session_vault','mixer_browser_oidc_attempts','mixer_browser_session_events','mixer_authz_profiles','mixer_authz_principals','mixer_authz_bindings','mixer_authz_families','mixer_authz_credentials'])
), boundary AS (SELECT oid FROM pg_constraint WHERE conrelid IN(SELECT oid FROM targets) OR confrelid IN(SELECT oid FROM targets)),
rels AS (
 SELECT n.nspname||'.'||c.relname AS relation, c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,r.rolname AS owner,c.relispartition,c.reloftype::text,c.relreplident,c.reloptions,
 EXISTS(SELECT 1 FROM pg_inherits i WHERE i.inhrelid=c.oid OR i.inhparent=c.oid) AS inheritance,
 EXISTS(SELECT 1 FROM pg_rewrite w WHERE w.ev_class=c.oid) AS rules,
 EXISTS(SELECT 1 FROM pg_foreign_table f WHERE f.ftrelid=c.oid) AS foreign_table,
 pg_get_expr(c.relpartbound,c.oid,false) AS partition_bound
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner
 WHERE c.oid IN(SELECT oid FROM targets) OR (c.relname LIKE 'mixer\_browser\_%' ESCAPE '\' AND c.relkind IN('r','p','v','m','f'))
 ORDER BY relation LIMIT 10
), cols AS (
 SELECT a.attrelid::regclass::text AS relation,a.attnum,a.attname,a.attisdropped,tn.nspname||'.'||t.typname AS type,a.atttypmod,a.attndims,a.attnotnull,a.attidentity,a.attgenerated,a.attislocal,a.attinhcount,a.atthasdef,pg_get_expr(d.adbin,d.adrelid,false) AS default_expr,a.atthasmissing,a.attmissingval::text,
 CASE WHEN a.attcollation=0 THEN NULL ELSE cn.nspname||'.'||co.collname END AS collation,
 co.collprovider,co.collisdeterministic,co.collencoding,co.collcollate,co.collctype,co.collversion
 FROM pg_attribute a JOIN pg_type t ON t.oid=a.atttypid JOIN pg_namespace tn ON tn.oid=t.typnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum LEFT JOIN pg_collation co ON co.oid=a.attcollation LEFT JOIN pg_namespace cn ON cn.oid=co.collnamespace
 WHERE a.attrelid IN(SELECT oid FROM targets) AND a.attnum>0 ORDER BY relation,a.attnum LIMIT 125
), cons AS (
 SELECT c.conrelid::regclass::text AS relation,c.conname,c.contype,c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.coninhcount,c.connoinherit,c.conparentid::text,c.contypid::text,
 CASE WHEN c.confrelid=0 THEN NULL ELSE c.confrelid::regclass::text END AS target,
 ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num,ord) JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num ORDER BY k.ord) AS columns,
 ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(num,ord) JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.num ORDER BY k.ord) AS target_columns,
 c.confmatchtype,c.confupdtype,c.confdeltype,
 CASE WHEN c.conindid=0 THEN NULL ELSE c.conindid::regclass::text END AS index,
 ARRAY(SELECT o.oid::regoperator::text FROM unnest(c.conpfeqop) WITH ORDINALITY x(id,ord) JOIN pg_operator o ON o.oid=x.id ORDER BY x.ord) AS pfeq,
 ARRAY(SELECT o.oid::regoperator::text FROM unnest(c.conppeqop) WITH ORDINALITY x(id,ord) JOIN pg_operator o ON o.oid=x.id ORDER BY x.ord) AS ppeq,
 ARRAY(SELECT o.oid::regoperator::text FROM unnest(c.conffeqop) WITH ORDINALITY x(id,ord) JOIN pg_operator o ON o.oid=x.id ORDER BY x.ord) AS ffeq,
 pg_get_expr(c.conbin,c.conrelid,false) AS expression,pg_get_constraintdef(c.oid,false) AS definition
 FROM pg_constraint c WHERE c.oid IN(SELECT oid FROM boundary) ORDER BY relation,c.contype,c.conname LIMIT 110
), indexes AS (
 SELECT i.indrelid::regclass::text AS relation,ci.relname AS name,ni.nspname AS namespace,ri.rolname AS owner,am.amname,i.indnatts,i.indnkeyatts,i.indisunique,i.indnullsnotdistinct,i.indisprimary,i.indisexclusion,i.indimmediate,i.indisclustered,i.indisvalid,i.indcheckxmin,i.indisready,i.indislive,i.indisreplident,
 ARRAY(SELECT a.attname FROM unnest(i.indkey::int2[]) WITH ORDINALITY x(num,ord) LEFT JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=x.num ORDER BY x.ord) AS columns,
 ARRAY(SELECT opn.nspname||'.'||op.opcname||':'||op.opcintype::regtype::text||':'||ofn.nspname||'.'||opf.opfname FROM unnest(i.indclass::oid[]) WITH ORDINALITY x(id,ord) JOIN pg_opclass op ON op.oid=x.id JOIN pg_namespace opn ON opn.oid=op.opcnamespace JOIN pg_opfamily opf ON opf.oid=op.opcfamily JOIN pg_namespace ofn ON ofn.oid=opf.opfnamespace ORDER BY x.ord) AS opclasses,
 ARRAY(SELECT CASE WHEN x.id=0 THEN NULL ELSE cn.nspname||'.'||co.collname END FROM unnest(i.indcollation::oid[]) WITH ORDINALITY x(id,ord) LEFT JOIN pg_collation co ON co.oid=x.id LEFT JOIN pg_namespace cn ON cn.oid=co.collnamespace ORDER BY x.ord) AS collations,
 i.indoption::text,pg_get_expr(i.indexprs,i.indrelid,false) AS expression,pg_get_expr(i.indpred,i.indrelid,false) AS predicate,
 ci.relispartition,ci.relpersistence,EXISTS(SELECT 1 FROM pg_inherits h WHERE h.inhrelid=i.indexrelid OR h.inhparent=i.indexrelid) AS inheritance,
 ARRAY(SELECT c.contype::text FROM pg_constraint c WHERE c.conindid=i.indexrelid AND c.conrelid=i.indrelid AND c.contype IN('p','u')) AS backing
 FROM pg_index i JOIN pg_class ci ON ci.oid=i.indexrelid JOIN pg_namespace ni ON ni.oid=ci.relnamespace JOIN pg_roles ri ON ri.oid=ci.relowner JOIN pg_am am ON am.oid=ci.relam
 WHERE i.indrelid IN(SELECT oid FROM targets) ORDER BY relation,ci.relname LIMIT 15
), triggers AS (
 SELECT t.tgrelid::regclass::text AS relation,t.tgname,t.tgisinternal,t.tgtype,t.tgenabled,t.tgfoid::regprocedure::text AS function,pn.nspname AS function_namespace,t.tgdeferrable,t.tginitdeferred,t.tgnargs,encode(t.tgargs,'hex') AS args,t.tgattr::text,pg_get_expr(t.tgqual,t.tgrelid,false) AS qual,t.tgoldtable,t.tgnewtable,t.tgparentid::text,
 CASE WHEN t.tgconstrrelid=0 THEN NULL ELSE t.tgconstrrelid::regclass::text END AS opposite,
 CASE WHEN t.tgconstrindid=0 THEN NULL ELSE t.tgconstrindid::regclass::text END AS index,
 c.conrelid::regclass::text AS constraint_relation,c.conname AS constraint_name,c.contype AS constraint_type,
 pg_get_constraintdef(c.oid,false) AS constraint_definition,pg_get_triggerdef(t.oid,false) AS definition
 FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace LEFT JOIN pg_constraint c ON c.oid=t.tgconstraint
 WHERE t.tgrelid IN(SELECT oid FROM targets) OR t.tgconstraint IN(SELECT oid FROM boundary)
 ORDER BY relation,t.tgname LIMIT 54
), policies AS (
 SELECT p.polrelid::regclass::text AS relation,p.polname,p.polcmd,p.polpermissive,
 ARRAY(SELECT CASE WHEN role=0 THEN 'PUBLIC' ELSE r.rolname END FROM unnest(p.polroles) WITH ORDINALITY k(role,ord) LEFT JOIN pg_roles r ON r.oid=k.role ORDER BY k.ord) AS roles,
 pg_get_expr(p.polqual,p.polrelid,false) AS using_expr,pg_get_expr(p.polwithcheck,p.polrelid,false) AS check_expr
 FROM pg_policy p WHERE p.polrelid IN(SELECT oid FROM targets) ORDER BY relation,p.polname LIMIT 33
), acl AS (
 SELECT c.oid::regclass::text AS relation, NULL::text AS column_name, c.relacl IS NULL AS acl_is_null, CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE g.rolname END AS grantee,r.rolname AS grantor,x.privilege_type,x.is_grantable
 FROM pg_class c CROSS JOIN LATERAL aclexplode(COALESCE(c.relacl,acldefault('r',c.relowner))) x LEFT JOIN pg_roles g ON g.oid=x.grantee JOIN pg_roles r ON r.oid=x.grantor WHERE c.oid IN(SELECT oid FROM targets)
 UNION ALL
 SELECT a.attrelid::regclass::text,a.attname,false,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE g.rolname END,r.rolname,x.privilege_type,x.is_grantable
 FROM pg_attribute a CROSS JOIN LATERAL aclexplode(a.attacl) x LEFT JOIN pg_roles g ON g.oid=x.grantee JOIN pg_roles r ON r.oid=x.grantor WHERE a.attrelid IN(SELECT oid FROM targets) AND a.attnum>0
), table_effective AS (
 SELECT role,c.oid::regclass::text AS relation,has_table_privilege(role,c.oid,'SELECT') AS sel,has_table_privilege(role,c.oid,'INSERT') AS ins,has_table_privilege(role,c.oid,'UPDATE') AS upd,has_table_privilege(role,c.oid,'DELETE') AS del,has_table_privilege(role,c.oid,'TRUNCATE') AS trunc,has_table_privilege(role,c.oid,'REFERENCES') AS refs,has_table_privilege(role,c.oid,'TRIGGER') AS trig ,has_table_privilege(role,c.oid,'MAINTAIN') AS maintain
 FROM unnest(ARRAY['browser_lifecycle','browser_writer','browser_ordinary']) role CROSS JOIN pg_class c WHERE c.oid IN(SELECT oid FROM targets) ORDER BY role,relation LIMIT 28
), column_effective AS (
 SELECT role,a.attrelid::regclass::text AS relation,a.attname,has_column_privilege(role,a.attrelid,a.attnum,'SELECT') AS sel,has_column_privilege(role,a.attrelid,a.attnum,'INSERT') AS ins,has_column_privilege(role,a.attrelid,a.attnum,'UPDATE') AS upd,has_column_privilege(role,a.attrelid,a.attnum,'REFERENCES') AS refs
 FROM unnest(ARRAY['browser_lifecycle','browser_writer','browser_ordinary']) role CROSS JOIN pg_attribute a WHERE a.attrelid IN(SELECT oid FROM targets) AND a.attnum>0 ORDER BY role,relation,a.attnum LIMIT 373
)
SELECT json_build_object(
 'relations',(SELECT json_agg(r) FROM rels r),
 'columns',(SELECT json_agg(c) FROM cols c),
 'constraints',(SELECT json_agg(c) FROM cons c),
 'indexes',(SELECT json_agg(i) FROM indexes i),
 'triggers',(SELECT json_agg(t) FROM triggers t),
 'policies',(SELECT json_agg(p) FROM policies p),
 'acl',(SELECT json_agg(a) FROM (SELECT * FROM acl ORDER BY relation,column_name,grantee,privilege_type LIMIT 513) a),
 'table_effective',(SELECT json_agg(e) FROM table_effective e),
 'column_effective',(SELECT json_agg(e) FROM column_effective e),
 'environment',(SELECT row_to_json(e) FROM (SELECT current_setting('server_version') AS server_version,current_setting('server_version_num') AS server_version_num,d.datcollate AS lc_collate,d.datctype AS lc_ctype,current_setting('server_encoding') AS encoding,current_setting('session_replication_role') AS replication_role,d.datlocprovider,d.datcollversion,pg_database_collation_actual_version(d.oid) AS actual_collation_version FROM pg_database d WHERE d.datname=current_database()) e)
);

ROLLBACK;