#!/usr/bin/env python3
"""Actual DDL/session correction probes plus strict manifest transport controls."""
import copy,json,os,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
source=(HERE/'frozen/tests.py').read_text()
exec(compile(source[:source.index('def success(')],str(HERE/'frozen/tests.py'),'exec'),globals())
from inspector import inspect,normalize,validate,canonical,SESSION,LEGACY
EXPECTED=json.loads(pathlib.Path(os.environ['MIXER_AUTHZ_EXPECTED']).read_text())
(OUT/'observations').mkdir(exist_ok=True)
CAPTURES=[]
def capture(label):
    with DB('mixer_hosted_runtime') as runtime:raw=inspect(ADMIN,runtime)
    number=len(CAPTURES)+1;path=OUT/'observations'/f'{number:03d}.json'
    path.write_text(json.dumps({'label':label,'raw':raw,'normalized':normalize(raw)},sort_keys=True,indent=2)+'\n')
    CAPTURES.append({'label':label,'file':str(path.relative_to(OUT))})
    return raw
def rejected(raw):
    try:validate(raw,EXPECTED)
    except ValueError as exc:return str(exc)
    raise AssertionError('unexpected selected admission')
def restored():validate(capture('restored safe control'),EXPECTED)
def baseline():
    raw=capture('safe corrected baseline');validate(raw,EXPECTED)
    i,t=seed()
    with Flow(i,t) as f:f.lookup();f.lock();assert f.decide()['outcome']=='allowed'
    with DB('mixer_hosted_runtime') as db:
        deny(lambda:db.q("SET session_replication_role='replica'"))
        deny(lambda:db.q('ALTER SYSTEM SET row_security=off'))
        deny(lambda:db.q('SELECT * FROM mixer_authz.principals'))
    return {'selected_admission':True,'resolver_admits_safe_identity':True,'unsafe_SET_ALTER_SYSTEM_and_table_read_denied':True}
case('corrected baseline still admits and denies protected operations',baseline)
def ddl(label,sql,witness=None,old_gap=False):
    seed();before=json.loads(ADMIN.one(LEGACY));ADMIN.q('BEGIN')
    try:
        ADMIN.q(sql);raw=capture(label);error=rejected(raw)
        if old_gap:assert raw['legacy']==before,'historical gap must remain observable'
        details=witness() if witness else None
        return {'corrected_rejected':True,'rejection':error,'old_catalog_equal':raw['legacy']==before,'actual_ddl':True,'witness':details}
    finally:ADMIN.q('ROLLBACK');restored()
def lifecycle_witness():
    ADMIN.q("UPDATE mixer_authz.external_identity_bindings SET subject='changed-without-guard'")
    assert ADMIN.one('SELECT subject FROM mixer_authz.external_identity_bindings')=='changed-without-guard'
    return {'immutable_subject_update_succeeded_under_disabled_guard':True}
def fk_witness():
    ADMIN.q("INSERT INTO mixer_authz.external_identity_bindings VALUES('aaaaaaaa-0000-0000-0000-000000000002','absent-profile','https://absent.example','subject','client','human','aaaaaaaa-0000-0000-0000-000000000001')")
    return {'missing_profile_principal_fk_insert_succeeded_under_disabled_guards':True}
for label,sql,witness in [
 ('ASR01 disabled lifecycle guard','ALTER TABLE mixer_authz.external_identity_bindings DISABLE TRIGGER lifecycle_guard',lifecycle_witness),
 ('ASR01 disabled FK enforcement','ALTER TABLE mixer_authz.external_identity_bindings DISABLE TRIGGER ALL',fk_witness),
 ('ASR02 unlogged denial relation','ALTER TABLE mixer_authz.credential_denials SET UNLOGGED',None),
 ('ASR02 replica identity nothing','ALTER TABLE mixer_authz.credential_denials REPLICA IDENTITY NOTHING',None)]:
    case('corrected historical gap '+label,lambda l=label,s=sql,w=witness:ddl(l,s,w,True))
for label,sql in [
 ('force rls','ALTER TABLE mixer_authz.principals NO FORCE ROW LEVEL SECURITY'),
 ('public helper execute','GRANT EXECUTE ON FUNCTION mixer_authz.finite_uint(numeric,numeric,numeric) TO PUBLIC'),
 ('search path','ALTER FUNCTION mixer_authz.finite_uint(numeric,numeric,numeric) SET search_path=public'),
 ('runtime bypass','ALTER ROLE mixer_hosted_runtime BYPASSRLS'),
 ('owner chain','GRANT mixer_hosted_schema_owner TO mixer_hosted_runtime WITH INHERIT FALSE,SET TRUE'),
 ('schema create','GRANT CREATE ON SCHEMA mixer_authz TO mixer_hosted_runtime'),
 ('database temp','GRANT TEMP ON DATABASE authority_contract TO mixer_hosted_runtime'),
 ('unknown table','CREATE TABLE mixer_authz.unexpected(a integer)'),
 ('extra helper',"CREATE FUNCTION mixer_authz.backdoor() RETURNS integer LANGUAGE sql AS 'SELECT 1'"),
 ('unknown composite','CREATE TYPE mixer_authz.unexpected_type AS(a integer)'),
 ('policy predicate','ALTER POLICY resolver_select ON mixer_authz.principals USING(false)'),
 ('policy role','ALTER POLICY resolver_select ON mixer_authz.principals TO PUBLIC'),
 ('policy restrictive','DROP POLICY resolver_select ON mixer_authz.principals;CREATE POLICY resolver_select ON mixer_authz.principals AS RESTRICTIVE FOR SELECT TO mixer_hosted_authz_resolver USING(true)'),
 ('FK deferrability','ALTER TABLE mixer_authz.external_identity_bindings ALTER CONSTRAINT external_identity_bindings_principal_id_identity_class_fkey DEFERRABLE INITIALLY DEFERRED'),
 ('CHECK validation','ALTER TABLE mixer_authz.principals DROP CONSTRAINT principals_valid_after_check;ALTER TABLE mixer_authz.principals ADD CONSTRAINT principals_valid_after_check CHECK(valid_after BETWEEN 0 AND 9007199254740991) NOT VALID'),
 ('index predicate',"DROP INDEX mixer_authz.project_memberships_active_unique;CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status IN ('active','invited')"),
 ('trigger replica','ALTER TABLE mixer_authz.external_identity_bindings ENABLE REPLICA TRIGGER lifecycle_guard'),
 ('trigger always','ALTER TABLE mixer_authz.external_identity_bindings ENABLE ALWAYS TRIGGER lifecycle_guard'),
 ('dropped trigger','DROP TRIGGER lifecycle_guard ON mixer_authz.external_identity_bindings'),
 ('extra user trigger','CREATE TRIGGER extra_guard BEFORE UPDATE ON mixer_authz.external_identity_bindings FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle()'),
 ('replica identity full','ALTER TABLE mixer_authz.credential_denials REPLICA IDENTITY FULL'),
 ('missing relation','DROP TABLE mixer_authz.credential_denials CASCADE'),
 ('same-name non-table relation','DROP TABLE mixer_authz.credential_denials CASCADE;CREATE VIEW mixer_authz.credential_denials AS SELECT 1 AS unavailable'),
 ('extra view','CREATE VIEW mixer_authz.unexpected_view AS SELECT 1 AS a'),
 ('extra sequence','CREATE SEQUENCE mixer_authz.unexpected_sequence')]:
    case('corrected ordinary DDL '+label,lambda l=label,s=sql:ddl(l,s))
def internal_trigger():
    name=ADMIN.one("SELECT tgname FROM pg_trigger WHERE tgrelid='mixer_authz.external_identity_bindings'::regclass AND tgisinternal ORDER BY tgname LIMIT 1")
    return ddl('individual internal FK trigger disabled','ALTER TABLE mixer_authz.external_identity_bindings DISABLE TRIGGER "'+name+'"',old_gap=True)
case('corrected individual internal FK trigger disabled',internal_trigger)
def parameter(label,recipient,param='session_replication_role',privilege='SET',reachable=False):
    seed();before=json.loads(ADMIN.one(LEGACY));role='correction_parameter_carrier'
    if reachable:
        ADMIN.q('CREATE ROLE '+role+' NOLOGIN;GRANT '+role+' TO mixer_hosted_runtime WITH INHERIT FALSE,SET TRUE')
    try:
        ADMIN.q('GRANT '+privilege+' ON PARAMETER '+param+' TO '+recipient)
        raw=capture(label);error=rejected(raw)
        if not reachable:assert raw['legacy']==before
        rows=[r for r in raw['enforcement']['parameter_effective'] if r['parameter']==param and r['subject']==(role if reachable else 'mixer_hosted_runtime')]
        assert len(rows)==1 and rows[0]['set' if privilege=='SET' else 'alter_system']
        actual=None
        if privilege=='SET' and param=='session_replication_role':
            with DB('mixer_hosted_runtime') as db:
                if reachable:db.q('SET ROLE '+role)
                db.q("SET session_replication_role='replica'");assert db.one("SELECT current_setting('session_replication_role')")=='replica';actual='replica'
        if param=='correction.unregistered':assert not rows[0]['registered']
        return {'corrected_rejected':True,'rejection':error,'effective_privilege':rows[0],'actual_runtime_SET':actual,'ordinary_GRANT':True,'reachable_via_SET_ROLE':reachable}
    finally:
        ADMIN.q('REVOKE '+privilege+' ON PARAMETER '+param+' FROM '+recipient)
        if reachable:ADMIN.q('REVOKE '+role+' FROM mixer_hosted_runtime;DROP ROLE '+role)
        restored()
for label,recipient,param,privilege,reachable in [
 ('ASR03 direct dangerous SET','mixer_hosted_runtime','session_replication_role','SET',False),
 ('PUBLIC dangerous SET','PUBLIC','session_replication_role','SET',False),
 ('reachable NOINHERIT role dangerous SET','correction_parameter_carrier','session_replication_role','SET',True),
 ('second superuser safety parameter','mixer_hosted_runtime','allow_system_table_mods','SET',False),
 ('direct ALTER SYSTEM','mixer_hosted_runtime','row_security','ALTER SYSTEM',False),
 ('PUBLIC ALTER SYSTEM','PUBLIC','row_security','ALTER SYSTEM',False),
 ('reachable ALTER SYSTEM','correction_parameter_carrier','row_security','ALTER SYSTEM',True),
 ('unregistered parameter SET direct','mixer_hosted_runtime','correction.unregistered','SET',False),
 ('unregistered parameter ALTER SYSTEM PUBLIC','PUBLIC','correction.unregistered','ALTER SYSTEM',False)]:
    case('corrected parameter '+label,lambda l=label,r=recipient,p=param,v=privilege,b=reachable:parameter(l,r,p,v,b))
def startup(label,statement,reset,setting,value):
    seed()
    try:
        ADMIN.q(statement);raw=capture(label);error=rejected(raw)
        assert raw['fresh_session'][setting]==value,(raw['fresh_session'],setting,value)
        assert raw['enforcement']['startup_defaults'],raw
        return {'corrected_rejected':True,'rejection':error,'actual_fresh_runtime_setting':{setting:value},'applicable_startup_defaults_captured':True}
    finally:ADMIN.q(reset);restored()
for label,statement,reset,setting,value in [
 ('role row security','ALTER ROLE mixer_hosted_runtime SET row_security=off','ALTER ROLE mixer_hosted_runtime RESET row_security','row_security','off'),
 ('database row security','ALTER DATABASE authority_contract SET row_security=off','ALTER DATABASE authority_contract RESET row_security','row_security','off'),
 ('role database isolation',"ALTER ROLE mixer_hosted_runtime IN DATABASE authority_contract SET default_transaction_isolation='repeatable read'",'ALTER ROLE mixer_hosted_runtime IN DATABASE authority_contract RESET default_transaction_isolation','transaction_isolation','repeatable read'),
 ('database serializable',"ALTER DATABASE authority_contract SET default_transaction_isolation='serializable'",'ALTER DATABASE authority_contract RESET default_transaction_isolation','transaction_isolation','serializable'),
 ('role replication replica',"ALTER ROLE mixer_hosted_runtime SET session_replication_role='replica'",'ALTER ROLE mixer_hosted_runtime RESET session_replication_role','session_replication_role','replica'),
 ('database replication replica',"ALTER DATABASE authority_contract SET session_replication_role='replica'",'ALTER DATABASE authority_contract RESET session_replication_role','session_replication_role','replica'),
 ('role default effective role',"ALTER ROLE mixer_hosted_runtime SET role='mixer_hosted_runtime'",'ALTER ROLE mixer_hosted_runtime RESET role','role','mixer_hosted_runtime')]:
    case('corrected fresh startup '+label,lambda l=label,s=statement,r=reset,k=setting,v=value:startup(l,s,r,k,v))
def direct_session(setting,value):
    with DB('mixer_hosted_runtime') as db:
        db.q('SET '+setting+'='+lit(value));raw=inspect(ADMIN,db);error=rejected(raw)
        assert raw['fresh_session'][setting]==value
        return {'corrected_rejected':True,'actual_runtime_SETTING':setting,'value':value,'rejection':error}
for setting,value in [('row_security','off'),('default_transaction_isolation','serializable'),('role','mixer_hosted_runtime')]:
    case('corrected actual session '+setting,lambda s=setting,v=value:direct_session(s,v))
def invalid_index():
    seed();index='mixer_authz.project_memberships_active_unique'
    ADMIN.q('DROP INDEX '+index)
    try:
        ADMIN.q(f"INSERT INTO mixer_authz.project_memberships SELECT 'eeeeeeee-1111-1111-1111-111111111111',organization,project,principal_id,role,status,not_before,expires_at,revision,grant_evidence_sha256 FROM mixer_authz.project_memberships")
        deny(lambda:ADMIN.q("CREATE UNIQUE INDEX CONCURRENTLY project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status='active'"),'23505')
        raw=capture('ordinary failed concurrent required-index rebuild');error=rejected(raw)
        changed=[r for r in raw['enforcement']['indexes'] if r['identity']==index][0]
        assert not changed['valid'] and not changed['ready'] and changed['live']
        expected=[r for r in EXPECTED['enforcement']['indexes'] if r['identity']==index][0]
        assert changed['definition']==expected['definition']
        return {'corrected_rejected':True,'rejection':error,'ordinary_failed_concurrent_index_build':True,'same_required_index_identity_and_definition':True,'valid':changed['valid'],'ready':changed['ready'],'live':changed['live']}
    finally:
        # The unchanged lifecycle guard forbids hard DELETE. Synthetic seed
        # cleanup uses the same administrator TRUNCATE as the frozen harness.
        ADMIN.q('TRUNCATE mixer_authz.project_memberships')
        ADMIN.q('DROP INDEX IF EXISTS '+index)
        ADMIN.q("CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status='active'")
        restored()
case('corrected invalid unready required index via ordinary concurrent DDL',invalid_index)
def deferred_unique():
    return ddl('ordinary deferred unique index',
      'ALTER TABLE mixer_authz.principals ADD CONSTRAINT correction_deferred UNIQUE(principal_id) DEFERRABLE INITIALLY DEFERRED',
      lambda:{'actual_immediate_false':ADMIN.one("SELECT NOT indimmediate FROM pg_index WHERE indexrelid='mixer_authz.correction_deferred'::regclass")=='t'})
case('corrected non-immediate unique index via ordinary DDL',deferred_unique)
def overridden_default():
    try:
        ADMIN.q('ALTER DATABASE authority_contract SET row_security=off;ALTER ROLE mixer_hosted_runtime SET row_security=on')
        raw=capture('unsafe database default masked by role precedence');assert raw['fresh_session']['row_security']=='on';assert len(raw['enforcement']['startup_defaults'])==2
        return {'corrected_rejected':True,'rejection':rejected(raw),'actual_fresh_value_safe_but_unselected_defaults_still_reject':True}
    finally:ADMIN.q('ALTER DATABASE authority_contract RESET row_security;ALTER ROLE mixer_hosted_runtime RESET row_security');restored()
case('corrected startup default precedence does not hide drift',overridden_default)
def malformed(label,mutate):
    raw=capture('comparator transport control '+label);mutate(raw)
    return {'rejected':True,'rejection':rejected(raw),'model_input_control_only':True,'system_catalog_modified':False}
def delete_key(x):del x['enforcement']['triggers'][0]['enabled']
def extra_key(x):x['enforcement']['triggers'][0]['unknown']=True
def missing_entry(x):x['enforcement']['triggers'].pop()
def duplicate_entry(x):x['enforcement']['triggers'].append(copy.deepcopy(x['enforcement']['triggers'][0]))
def distinct_duplicate(x):
    row=copy.deepcopy(next(r for r in x['enforcement']['triggers'] if r['internal']));row['oid']+=100000;row['name']='new_generated_name';x['enforcement']['triggers'].append(row)
def bool_as_int(x):x['enforcement']['indexes'][0]['valid']=1
def unresolved(x):x['enforcement']['triggers'][0]['constraint_oid']=100000;x['enforcement']['triggers'][0]['constraint_identity']=None
for label,fn in [('missing key',delete_key),('unknown key',extra_key),('missing trigger',missing_entry),('same OID duplicate trigger',duplicate_entry),('distinct OID duplicate internal identity',distinct_duplicate),('malformed flag int',bool_as_int),('unresolved OID association',unresolved),('empty catalog',lambda x:x['enforcement']['relations'].clear()),('extra root key',lambda x:x.update(unexpected=True))]:
    case('strict comparator '+label,lambda l=label,f=fn:malformed(l,f))
def flags():
    raw=capture('comparator flag coverage');checked=[]
    for group,names in [('indexes',['valid','ready','live','immediate']),('constraints',['validated','deferrable','initially_deferred']),('triggers',['deferrable','initially_deferred'])]:
        for name in names:
            other=copy.deepcopy(raw);other['enforcement'][group][0][name]=not other['enforcement'][group][0][name];rejected(other);checked.append(group+'.'+name)
    return {'model_rejections':checked,'not_ordinary_DDL_runtime_receipts':['indexes.live=false'],'actual_invalid_index_test_separate':True}
case('strict comparator selected enforcement flags',flags)
restored();ADMIN.close()
summary={'total':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'failed':[x['name'] for x in RESULTS if not x['passed']],'skipped':0,'excluded':0,'captures':CAPTURES,'historical_gaps_preserved_by_separate_replay':5,'baseline_counts':{'relations':14,'constraints':89,'indexes':26,'triggers':74},'unexecuted_runtime_states':['index indisLive=false transient concurrent-drop state; inspector field and model rejection only'],'libpq_path':libpath,'libpq_version':version()}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='captures'}));sys.exit(0 if not summary['failed'] else 1)
