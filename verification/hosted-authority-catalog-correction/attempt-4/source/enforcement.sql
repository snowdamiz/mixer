WITH runtime AS (SELECT oid FROM pg_roles WHERE rolname='mixer_hosted_runtime'),
subjects AS (
 SELECT rolname::text AS name FROM pg_roles,runtime WHERE pg_roles.oid=runtime.oid OR pg_has_role(runtime.oid,pg_roles.oid,'MEMBER')
), parameter_names AS (
 SELECT name,context,true AS registered FROM pg_settings
 UNION ALL SELECT parname,NULL,false FROM pg_parameter_acl WHERE NOT EXISTS(SELECT 1 FROM pg_settings WHERE name=parname)
)
SELECT jsonb_build_object(
 'relations',(SELECT coalesce(jsonb_agg(jsonb_build_object('oid',c.oid::bigint,'identity',format('%I.%I',n.nspname,c.relname),'kind',c.relkind,'persistence',c.relpersistence,'replica_identity',c.relreplident) ORDER BY c.relname),'[]') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='mixer_authz' AND c.relkind NOT IN ('i','I','c')),
 'constraints',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'oid',co.oid::bigint,'identity',format('%I.%I/%I',n.nspname,c.relname,co.conname),'relation',format('%I.%I',n.nspname,c.relname),'type',co.contype,
   'validated',co.convalidated,'deferrable',co.condeferrable,'initially_deferred',co.condeferred,'no_inherit',co.connoinherit,'local',co.conislocal,'inheritance_count',co.coninhcount,
   'parent_oid',co.conparentid::bigint,'parent_identity',(SELECT format('%I.%I/%I',pn.nspname,pc.relname,p.conname) FROM pg_constraint p JOIN pg_class pc ON pc.oid=p.conrelid JOIN pg_namespace pn ON pn.oid=pc.relnamespace WHERE p.oid=co.conparentid),
   'definition',pg_get_constraintdef(co.oid,true)) ORDER BY c.relname,co.conname),'[]') FROM pg_constraint co JOIN pg_class c ON c.oid=co.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='mixer_authz'),
 'indexes',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'oid',ic.oid::bigint,'identity',format('%I.%I',ins.nspname,ic.relname),'relation',format('%I.%I',n.nspname,c.relname),'valid',ix.indisvalid,'ready',ix.indisready,'live',ix.indislive,'immediate',ix.indimmediate,
   'unique',ix.indisunique,'primary',ix.indisprimary,'exclusion',ix.indisexclusion,'nulls_not_distinct',ix.indnullsnotdistinct,'definition',pg_get_indexdef(ix.indexrelid)) ORDER BY ic.relname),'[]') FROM pg_index ix JOIN pg_class c ON c.oid=ix.indrelid JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_class ic ON ic.oid=ix.indexrelid JOIN pg_namespace ins ON ins.oid=ic.relnamespace WHERE n.nspname='mixer_authz'),
 'triggers',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'oid',t.oid::bigint,'name',t.tgname,'relation_oid',t.tgrelid::bigint,'relation',format('%I.%I',n.nspname,c.relname),'function_oid',t.tgfoid::bigint,'function_identity',format('%I.%I(%s)',pn.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
   'enabled',t.tgenabled,'internal',t.tgisinternal,'event_timing_bits',t.tgtype,'deferrable',t.tgdeferrable,'initially_deferred',t.tginitdeferred,
   'constraint_oid',t.tgconstraint::bigint,'constraint_identity',(SELECT format('%I.%I/%I',cn.nspname,cc.relname,co.conname) FROM pg_constraint co JOIN pg_class cc ON cc.oid=co.conrelid JOIN pg_namespace cn ON cn.oid=cc.relnamespace WHERE co.oid=t.tgconstraint),
   'referenced_relation_oid',t.tgconstrrelid::bigint,'referenced_relation',(SELECT format('%I.%I',rn.nspname,rc.relname) FROM pg_class rc JOIN pg_namespace rn ON rn.oid=rc.relnamespace WHERE rc.oid=t.tgconstrrelid),
   'constraint_index_oid',t.tgconstrindid::bigint,'constraint_index',(SELECT format('%I.%I',rn.nspname,rc.relname) FROM pg_class rc JOIN pg_namespace rn ON rn.oid=rc.relnamespace WHERE rc.oid=t.tgconstrindid),
   'parent_oid',t.tgparentid::bigint,'parent_identity',(SELECT jsonb_build_object('relation',format('%I.%I',an.nspname,ac.relname),'name',pt.tgname) FROM pg_trigger pt JOIN pg_class ac ON ac.oid=pt.tgrelid JOIN pg_namespace an ON an.oid=ac.relnamespace WHERE pt.oid=t.tgparentid),
   'argument_count',t.tgnargs,'argument_hex',encode(t.tgargs,'hex'),'columns',t.tgattr::text,'when',pg_get_expr(t.tgqual,t.tgrelid::bigint,true),'old_table',t.tgoldtable,'new_table',t.tgnewtable,'definition',pg_get_triggerdef(t.oid,true)) ORDER BY c.relname,t.tgname),'[]') FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace WHERE n.nspname='mixer_authz'),
 'parameter_acl',(SELECT coalesce(jsonb_agg(jsonb_build_object('oid',pa.oid::bigint,'parameter',pa.parname,'acl',pa.paracl::text,
   'entries',(SELECT jsonb_agg(jsonb_build_object('grantor',pg_get_userbyid(a.grantor),'grantee',CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,'privilege',a.privilege_type,'grantable',a.is_grantable) ORDER BY a.grantee,a.privilege_type) FROM aclexplode(pa.paracl) a)) ORDER BY pa.parname),'[]') FROM pg_parameter_acl pa),
 'parameter_effective',(SELECT coalesce(jsonb_agg(jsonb_build_object('subject',s.name,'parameter',p.name,'context',p.context,'registered',p.registered,
   'selected_set',p.context IN ('superuser','superuser-backend') OR NOT p.registered,
   'set',has_parameter_privilege(s.name,p.name,'SET'),'alter_system',has_parameter_privilege(s.name,p.name,'ALTER SYSTEM')) ORDER BY s.name,p.name),'[]') FROM subjects s CROSS JOIN parameter_names p),
 'parameter_public',(SELECT coalesce(jsonb_agg(jsonb_build_object('parameter',p.name,'context',p.context,'registered',p.registered,'selected_set',p.context IN ('superuser','superuser-backend') OR NOT p.registered,'set',has_parameter_privilege('public',p.name,'SET'),'alter_system',has_parameter_privilege('public',p.name,'ALTER SYSTEM')) ORDER BY p.name),'[]') FROM parameter_names p),
 'role_config',(SELECT coalesce(jsonb_agg(jsonb_build_object('role',r.rolname,'config',r.rolconfig) ORDER BY r.rolname),'[]') FROM pg_roles r WHERE r.rolname IN(SELECT name FROM subjects)),
 'startup_defaults',(SELECT coalesce(jsonb_agg(jsonb_build_object('database_oid',ds.setdatabase::bigint,'database',CASE WHEN ds.setdatabase=0 THEN '*' ELSE db.datname END,'role_oid',ds.setrole::bigint,'role',CASE WHEN ds.setrole=0 THEN '*' ELSE r.rolname END,'config',ds.setconfig) ORDER BY coalesce(db.datname,''),coalesce(r.rolname,'')),'[]') FROM pg_db_role_setting ds LEFT JOIN pg_database db ON db.oid=ds.setdatabase LEFT JOIN pg_roles r ON r.oid=ds.setrole WHERE ds.setdatabase IN(0,(SELECT oid FROM pg_database WHERE datname=current_database())) AND (ds.setrole=0 OR r.rolname IN(SELECT name FROM subjects)))
);
