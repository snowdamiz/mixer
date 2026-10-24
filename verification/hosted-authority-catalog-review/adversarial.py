#!/usr/bin/env python3
"""Independent bounded probes; source is copied before execution."""
import copy,gzip,hashlib,json,os,pathlib,sys,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=pathlib.Path(os.environ['MIXER_REVIEW_SOURCE'])
source=(SOURCE/'frozen/tests.py').read_text()
exec(compile(source[:source.index('def success(')],str(SOURCE/'frozen/tests.py'),'exec'),globals())
sys.path.insert(0,str(SOURCE))
from inspector import inspect,normalize,validate,decode,canonical,SESSION
EXPECTED=decode(pathlib.Path(os.environ['MIXER_AUTHZ_EXPECTED']).read_text())
CAPTURES=[];FINDINGS=[]
(OUT/'observations').mkdir(exist_ok=True)
def capture(label,raw):
    entry={'label':label,'raw':raw}
    try:entry['normalized']=normalize(raw)
    except Exception as exc:entry['normalization_error']=repr(exc)
    b=(json.dumps(entry,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    path=OUT/'observations'/f'{len(CAPTURES)+1:03d}.json.gz'
    path.write_bytes(gzip.compress(b,mtime=0))
    CAPTURES.append({'label':label,'path':str(path.relative_to(OUT)),'raw_json_sha256':hashlib.sha256(b).hexdigest()})
    return raw
def observe(label):
    with DB('mixer_hosted_runtime') as runtime:raw=inspect(ADMIN,runtime)
    return capture(label,raw)
def rejects(raw):
    try:validate(raw,EXPECTED)
    except ValueError as exc:return str(exc)
    raise AssertionError('unexpected admission')
def safe(label='safe restoration'):
    raw=observe(label);validate(raw,EXPECTED);return raw
def ddl(label,sql,accept=False,witness=None):
    seed();ADMIN.q('BEGIN')
    try:
        ADMIN.q(sql);raw=observe(label)
        if accept:validate(raw,EXPECTED);reason=None
        else:reason=rejects(raw)
        return {'actual_ddl':sql,'expected_admission':accept,'rejection':reason,'witness':witness(raw) if witness else None}
    finally:ADMIN.q('ROLLBACK');safe()

def fresh_identity():
    admin_pid=ADMIN.one('SELECT pg_backend_pid()');pids=[]
    for _ in range(3):
        with DB('mixer_hosted_runtime') as runtime:
            identity=json.loads(runtime.one("SELECT json_build_object('pid',pg_backend_pid(),'session',session_user,'effective',current_user,'database',current_database(),'socket_connection',inet_server_addr() IS NULL,'role',current_setting('role'))"))
            assert identity['session']==identity['effective']=='mixer_hosted_runtime'
            assert identity['database']=='authority_contract' and identity['socket_connection'] and identity['role']=='none'
            assert str(identity['pid'])!=admin_pid and identity['pid'] not in pids;pids.append(identity['pid'])
            validate(capture('fresh actual runtime connection',inspect(ADMIN,runtime)),EXPECTED)
    return {'admin_pid':int(admin_pid),'separate_fresh_runtime_pids':pids,'not_SET_ROLE_admin_emulation':True}
case('fresh runtime connections have distinct backend and exact identity',fresh_identity)

def portable_fk_rename():
    name=ADMIN.one("SELECT tgname FROM pg_trigger WHERE tgrelid='mixer_authz.external_identity_bindings'::regclass AND tgisinternal ORDER BY tgname LIMIT 1")
    def witness(raw):
        assert any(t['name']=='review_renamed_internal_fk' for t in raw['enforcement']['triggers'])
        deny(lambda:ADMIN.q("INSERT INTO mixer_authz.external_identity_bindings VALUES('aaaaaaaa-1234-1234-1234-aaaaaaaaaaaa','missing','https://invalid.example','missing','client','human','aaaaaaaa-1234-1234-1234-bbbbbbbbbbbb')"),'23503')
        return {'renamed_internal_trigger_preserved':True,'real_FK_violation_denied':True}
    return ddl('internal FK trigger rename preserves selected semantics','ALTER TRIGGER "'+name+'" ON mixer_authz.external_identity_bindings RENAME TO review_renamed_internal_fk',True,witness)
case('internal generated trigger name may change without hiding enforcement',portable_fk_rename)

def fk_recreate():
    constraint='external_identity_bindings_principal_id_identity_class_fkey'
    definition=ADMIN.one("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='mixer_authz.external_identity_bindings'::regclass AND conname="+lit(constraint))
    return ddl('same FK recreated with different actual OIDs',f'ALTER TABLE mixer_authz.external_identity_bindings DROP CONSTRAINT {constraint};ALTER TABLE mixer_authz.external_identity_bindings ADD CONSTRAINT {constraint} {definition}',True)
case('same FK recreated under new OIDs retains semantic identity',fk_recreate)

def extra_fk():
    definition=ADMIN.one("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='mixer_authz.external_identity_bindings'::regclass AND conname='external_identity_bindings_principal_id_identity_class_fkey'")
    def witness(raw):
        assert len(raw['enforcement']['constraints'])==90 and len(raw['enforcement']['triggers'])==78
        return {'constraints':90,'triggers':78,'actual_extra_internal_triggers':4}
    return ddl('duplicate semantic FK adds four retained internal triggers','ALTER TABLE mixer_authz.external_identity_bindings ADD CONSTRAINT review_duplicate_fk '+definition,witness=witness)
case('actual duplicate FK multiplicity rejects',extra_fk)

def internal_always():
    name=ADMIN.one("SELECT tgname FROM pg_trigger WHERE tgrelid='mixer_authz.external_identity_bindings'::regclass AND tgisinternal ORDER BY tgname DESC LIMIT 1")
    return ddl('internal FK ALWAYS enable mode changes selected enforcement','ALTER TABLE mixer_authz.external_identity_bindings ENABLE ALWAYS TRIGGER "'+name+'"')
case('internal trigger ALWAYS mode rejects',internal_always)

def lifecycle_when():
    def witness(raw):
        assert next(t for t in raw['enforcement']['triggers'] if t['relation']=='mixer_authz.external_identity_bindings' and t['name']=='lifecycle_guard')['when'] is not None
        ADMIN.q("UPDATE mixer_authz.external_identity_bindings SET subject='unsafe-when-bypass'")
        assert ADMIN.one('SELECT subject FROM mixer_authz.external_identity_bindings')=='unsafe-when-bypass'
        return {'actual_immutable_subject_bypass':True,'unsafe_predicate_rejected':True}
    return ddl('lifecycle WHEN predicate bypass',"DROP TRIGGER lifecycle_guard ON mixer_authz.external_identity_bindings;CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.external_identity_bindings FOR EACH ROW WHEN(false) EXECUTE FUNCTION mixer_authz.guard_lifecycle()",witness=witness)
case('actual lifecycle WHEN predicate bypass rejects',lifecycle_when)
case('renamed user lifecycle trigger rejects',lambda:ddl('user lifecycle name drift','ALTER TRIGGER lifecycle_guard ON mixer_authz.external_identity_bindings RENAME TO review_lifecycle_guard'))
case('lifecycle event semantics changed to insert rejects',lambda:ddl('lifecycle event bits changed','DROP TRIGGER lifecycle_guard ON mixer_authz.external_identity_bindings;CREATE TRIGGER lifecycle_guard BEFORE INSERT ON mixer_authz.external_identity_bindings FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle()'))
case('extra deferred constraint trigger rejects',lambda:ddl('extra deferred constraint trigger','CREATE CONSTRAINT TRIGGER review_deferred_guard AFTER UPDATE ON mixer_authz.principals DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle()'))
case('actual FK deferrable initially immediate rejects',lambda:ddl('FK immediate deferrability','ALTER TABLE mixer_authz.external_identity_bindings ALTER CONSTRAINT external_identity_bindings_principal_id_identity_class_fkey DEFERRABLE INITIALLY IMMEDIATE'))
case('index null uniqueness semantics rejects',lambda:ddl('NULLS NOT DISTINCT selected index','DROP INDEX mixer_authz.project_memberships_active_unique;CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) NULLS NOT DISTINCT WHERE status=\'active\''))
case('replica identity USING INDEX rejects',lambda:ddl('replica identity using primary index','ALTER TABLE mixer_authz.credential_denials REPLICA IDENTITY USING INDEX credential_denials_pkey'))

def grant_chain():
    seed()
    try:
        ADMIN.q('CREATE ROLE review_grant_outer NOLOGIN;CREATE ROLE review_grant_inner NOLOGIN;GRANT review_grant_outer TO mixer_hosted_runtime WITH INHERIT FALSE,SET TRUE;GRANT review_grant_inner TO review_grant_outer WITH INHERIT FALSE,SET TRUE;GRANT SET ON PARAMETER session_replication_role TO review_grant_inner WITH GRANT OPTION')
        raw=observe('two-hop SET ROLE parameter authority')
        error=rejects(raw)
        row=next(r for r in raw['enforcement']['parameter_effective'] if r['subject']=='review_grant_inner' and r['parameter']=='session_replication_role');assert row['set']
        with DB('mixer_hosted_runtime') as runtime:
            runtime.q('SET ROLE review_grant_inner;SET session_replication_role=replica')
            assert runtime.one("SELECT current_setting('session_replication_role')")=='replica'
        return {'rejection':error,'actual_two_hop_SET_ROLE_dangerous_SET':True,'grant_option':True}
    finally:
        ADMIN.q('REVOKE SET ON PARAMETER session_replication_role FROM review_grant_inner;REVOKE review_grant_outer FROM mixer_hosted_runtime;REVOKE review_grant_inner FROM review_grant_outer;DROP ROLE review_grant_outer;DROP ROLE review_grant_inner');safe()
case('two-hop reachable SET ROLE parameter grant rejects',grant_chain)

def all_roles_default():
    try:
        ADMIN.q('ALTER ROLE ALL IN DATABASE authority_contract SET session_replication_role=replica')
        raw=observe('all roles in current database unsafe default');error=rejects(raw)
        assert raw['fresh_session']['session_replication_role']=='replica'
        assert any(d['database']=='authority_contract' and d['role']=='*' for d in raw['enforcement']['startup_defaults'])
        return {'rejection':error,'actual_all_roles_startup_replica':True}
    finally:ADMIN.q('ALTER ROLE ALL IN DATABASE authority_contract RESET session_replication_role');safe()
case('ALTER ROLE ALL IN DATABASE unsafe fresh default rejects',all_roles_default)

def highest_precedence_default():
    try:
        ADMIN.q('ALTER DATABASE authority_contract SET row_security=on;ALTER ROLE mixer_hosted_runtime SET row_security=on;ALTER ROLE mixer_hosted_runtime IN DATABASE authority_contract SET row_security=off')
        raw=observe('unsafe role database overrides safe role and database');error=rejects(raw)
        assert raw['fresh_session']['row_security']=='off' and len(raw['enforcement']['startup_defaults'])==3
        return {'rejection':error,'fresh_row_security':'off','captured_default_rows':3}
    finally:ADMIN.q('ALTER ROLE mixer_hosted_runtime IN DATABASE authority_contract RESET row_security;ALTER ROLE mixer_hosted_runtime RESET row_security;ALTER DATABASE authority_contract RESET row_security');safe()
case('highest startup precedence unsafe value rejects',highest_precedence_default)

def unrelated_default_control():
    ADMIN.q('CREATE ROLE review_unrelated NOLOGIN')
    ADMIN.q('CREATE DATABASE review_unrelated_database')
    try:
        ADMIN.q('ALTER ROLE review_unrelated SET row_security=off;ALTER DATABASE review_unrelated_database SET row_security=off;ALTER ROLE mixer_hosted_runtime IN DATABASE review_unrelated_database SET row_security=off')
        raw=safe('unrelated role and different-database defaults remain outside applicable scope')
        assert raw['enforcement']['startup_defaults']==[]
        return {'unrelated_unsafe_defaults_excluded':True,'actual_runtime_safe':True}
    finally:
        ADMIN.q('ALTER ROLE review_unrelated RESET row_security;ALTER ROLE mixer_hosted_runtime IN DATABASE review_unrelated_database RESET row_security')
        ADMIN.q('DROP DATABASE review_unrelated_database')
        ADMIN.q('DROP ROLE review_unrelated');safe()
case('unrelated defaults do not contaminate applicable selection',unrelated_default_control)

def session_identity_change():
    with DB() as connection:
        connection.q('SET ROLE mixer_hosted_runtime');raw=capture('admin SET ROLE emulation is not runtime session identity',inspect(ADMIN,connection));error=rejects(raw)
        assert raw['fresh_session']['current_user']=='mixer_hosted_runtime' and raw['fresh_session']['session_user']!='mixer_hosted_runtime'
        return {'rejection':error,'session_user':raw['fresh_session']['session_user'],'current_user':raw['fresh_session']['current_user']}
case('admin SET ROLE cannot substitute for fresh runtime login',session_identity_change)

def actual_session_isolation():
    with DB('mixer_hosted_runtime') as runtime:
        runtime.q('BEGIN ISOLATION LEVEL REPEATABLE READ');raw=capture('current transaction isolation differs from safe default',inspect(ADMIN,runtime));error=rejects(raw)
        assert raw['fresh_session']['default_transaction_isolation']=='read committed' and raw['fresh_session']['transaction_isolation']=='repeatable read'
        runtime.q('ROLLBACK');return {'rejection':error,'different_actual_isolation_captured':True}
case('actual transaction isolation rejects even with safe default',actual_session_isolation)

def read_only_default():
    try:
        ADMIN.q('ALTER ROLE mixer_hosted_runtime IN DATABASE authority_contract SET default_transaction_read_only=on')
        raw=observe('fresh default read only');error=rejects(raw);assert raw['fresh_session']['transaction_read_only']=='on'
        return {'rejection':error,'actual_fresh_read_only':True}
    finally:ADMIN.q('ALTER ROLE mixer_hosted_runtime IN DATABASE authority_contract RESET default_transaction_read_only');safe()
case('fresh runtime read-only default rejects',read_only_default)

def malformed_ignored():
    raw=safe('raw comparator model source');results=[]
    for group,field,value in [('triggers','name',None),('triggers','name',{}),('triggers','definition',None),('triggers','definition',{}),('triggers','oid',4294967296),('triggers','relation_oid',4294967296),('triggers','constraint_oid',4294967296),('relations','oid',4294967296),('constraints','oid',4294967296),('indexes','oid',4294967296)]:
        other=copy.deepcopy(raw);row=next(r for r in other['enforcement'][group] if r.get('internal',True));row[field]=value
        capture('malformed ignored raw field '+group+'.'+field+' '+json.dumps(value),other)
        try:validate(other,EXPECTED);admitted=True
        except ValueError:admitted=False
        results.append({'group':group,'field':field,'value':value,'admitted':admitted})
    assert all(x['admitted'] for x in results),results
    FINDINGS.append({'id':'ACR01','severity':'medium','contract':'malformed raw entries must fail closed before normalization','reproductions':results,'ordinary_postgresql_runtime_bypass':False})
    return {'confirmed_raw_comparator_gap':True,'reproductions':results,'model_input_only':True,'not_security_pass':True}
case('FINDING malformed internal fields and impossible OIDs are erased before validation',malformed_ignored)

def transport_negatives():
    raw=safe('strict transport rejection source');results=[]
    for label,mutate in [
      ('negative ignored OID',lambda x:x['enforcement']['triggers'][0].update(oid=-1)),
      ('boolean ignored OID',lambda x:x['enforcement']['triggers'][0].update(oid=True)),
      ('missing ignored internal field',lambda x:next(r for r in x['enforcement']['triggers'] if r['internal']).pop('name')),
      ('duplicate effective parameter',lambda x:x['enforcement']['parameter_effective'].append(copy.deepcopy(x['enforcement']['parameter_effective'][0]))),
      ('missing fresh identity',lambda x:x['fresh_session'].pop('session_user')),
      ('additional raw trigger field',lambda x:x['enforcement']['triggers'][0].update(review_extra='unknown')),
      ('internal event type scalar changed',lambda x:next(r for r in x['enforcement']['triggers'] if r['internal']).update(event_timing_bits='9')),
      ('internal constraint identity object',lambda x:next(r for r in x['enforcement']['triggers'] if r['internal']).update(constraint_identity={}))]:
        other=copy.deepcopy(raw);mutate(other);error=rejects(capture('strict negative '+label,other));results.append({'label':label,'rejection':error})
    return {'model_rejections':results}
case('independent strict transport negatives reject',transport_negatives)
safe('final safe restored state');ADMIN.close()
summary={'schema':1,'total':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'failed':[x['name'] for x in RESULTS if not x['passed']],'captures':CAPTURES,'findings':FINDINGS,'finding_reproductions_are_not_security_passes':True,'scope':'standalone selected properties only; point-in-time inspection; no concurrent privileged DDL prevention, product startup, combined schema, HTTP/provider/native or GA acceptance'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='captures'},indent=2))
sys.exit(0 if not summary['failed'] else 1)
