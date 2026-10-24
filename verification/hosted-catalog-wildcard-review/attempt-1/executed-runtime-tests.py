#!/usr/bin/env python3
"""Targeted ordinary DDL in the driver's fresh owned socket-only PG cluster."""
import gzip,hashlib,json,os,pathlib,sys
sys.dont_write_bytecode=True
SOURCE=pathlib.Path(os.environ['MIXER_REVIEW_SOURCE']);sys.path.insert(0,str(SOURCE))
# Reuse only the byte-bound DB/helper prefix; execute none of the broad suite.
source=(SOURCE/'frozen/tests.py').read_text();exec(compile(source[:source.index('def success(')],str(SOURCE/'frozen/tests.py'),'exec'),globals())
from inspector import inspect,validate,normalize,decode,canonical
from raw_validation import validate_raw
EXPECTED=decode(pathlib.Path(os.environ['MIXER_AUTHZ_EXPECTED']).read_bytes());CAPTURES=[]
class DBAt(DB):
    def __init__(self,database,user=None):
        assert database in ['authority_contract','*'];self.user=user or getpass.getuser();self.c=connect(f"host={SOCK} dbname='{database}' user={self.user}".encode());assert status(self.c)==0
def capture(label,admitted=True,database='authority_contract'):
    with DBAt(database) as admin,DBAt(database,'mixer_hosted_runtime') as runtime:raw=inspect(admin,runtime)
    before=canonical(raw);validate_raw(raw)
    try:validate(raw,EXPECTED);actual=True;error=None
    except ValueError as exc:actual=False;error=str(exc)
    assert actual==admitted,(label,error);assert before==canonical(raw)
    b=(json.dumps({'label':label,'raw':raw,'normalized':normalize(raw)},sort_keys=True,indent=2)+'\n').encode();name=f'{len(CAPTURES)+1:03d}.json.gz';(OUT/name).write_bytes(gzip.compress(b,mtime=0))
    CAPTURES.append({'label':label,'path':name,'raw_json_sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'expected_raw_valid':True,'expected_selected_admission':admitted,'selected_error':error,'input_unchanged':True})
    return raw
def baseline():
    raw=capture('fresh padded selected baseline')
    prior=decode(gzip.decompress(pathlib.Path(os.environ['MIXER_WILDCARD_PRIOR']).read_bytes()))['raw']
    assert raw['enforcement']['relations'][0]['oid']!=prior['enforcement']['relations'][0]['oid']
    names=lambda x:sorted(t['name'] for t in x['enforcement']['triggers'] if t['internal'])
    assert names(raw)!=names(prior) and canonical(normalize(raw))==canonical(normalize(prior))
    return {'fresh_OIDs_and_internal_names':True,'selected_manifest_unchanged':True,'libpq_version':version()}
case('fresh selected baseline with portable generated names',baseline)
def quoted_shapes():
    rows=[];ADMIN.q('CREATE ROLE "*" NOLOGIN; GRANT "*" TO mixer_hosted_runtime')
    try:
        capture('quoted star reachable role without defaults',False)
        ADMIN.q('ALTER ROLE "*" SET application_name=wildcard_global')
        raw=capture('positive star role and zero database sentinel',False);row=next(x for x in raw['enforcement']['startup_defaults'] if x['role']=='*' and x['database_oid']==0);assert row['role_oid']>0 and row['database']=='*';rows.append(row)
        ADMIN.q('ALTER ROLE "*" IN DATABASE authority_contract SET application_name=wildcard_scoped')
        raw=capture('positive star role scoped to ordinary database',False);row=next(x for x in raw['enforcement']['startup_defaults'] if x['role']=='*' and x['database_oid']>0);assert row['role_oid']>0;rows.append(row)
        ADMIN.q('ALTER ROLE "*" RESET application_name; ALTER ROLE "*" IN DATABASE authority_contract RESET application_name')
        with DBAt('*') as admin:
            admin.q('ALTER DATABASE "*" SET application_name=wildcard_database')
            try:
                raw=capture('positive star database and zero role sentinel',False,'*');row=next(x for x in raw['enforcement']['startup_defaults'] if x['role_oid']==0);assert row['database_oid']>0 and row['database']=='*' and row['role']=='*';rows.append(row)
                admin.q('ALTER ROLE "*" IN DATABASE "*" SET application_name=wildcard_both')
                raw=capture('positive star database and positive star role',False,'*');row=next(x for x in raw['enforcement']['startup_defaults'] if x['role_oid']>0);assert row['database_oid']>0 and row['database']==row['role']=='*';rows.append(row)
            finally:admin.q('ALTER ROLE "*" IN DATABASE "*" RESET application_name; ALTER DATABASE "*" RESET application_name')
    finally:
        ADMIN.q('ALTER ROLE "*" RESET application_name; ALTER ROLE "*" IN DATABASE authority_contract RESET application_name; REVOKE "*" FROM mixer_hosted_runtime; DROP ROLE "*"')
    capture('safe restoration after quoted identifier shapes')
    return {'actual_startup_rows':rows,'raw_all_valid':True,'all_added_roles_defaults_fail_selected_comparison':True,'scope':'legal ordinary SQL observations of unselected shapes; no selected-safe behavior change'}
case('legal quoted role and database wildcard collisions',quoted_shapes)
def ordinary_drift():
    ADMIN.q('ALTER TABLE mixer_authz.applications DISABLE TRIGGER lifecycle_guard')
    try:capture('ordinary disabled lifecycle trigger drift',False)
    finally:ADMIN.q('ALTER TABLE mixer_authz.applications ENABLE TRIGGER lifecycle_guard')
    capture('restoration after ordinary trigger drift')
    ADMIN.q('ALTER ROLE mixer_hosted_runtime SET application_name=wildcard_ordinary')
    try:capture('ordinary role default drift',False)
    finally:ADMIN.q('ALTER ROLE mixer_hosted_runtime RESET application_name')
    capture('restoration after ordinary role default drift')
    return {'ordinary_trigger_and_role_default_drift_rejected':True}
case('ordinary catalog drift still rejects',ordinary_drift)
def trigger_names():
    raw=capture('selected trigger name baseline');triggers=raw['enforcement']['triggers'];a=next(t for t in triggers if t['internal'] and t['relation']=='mixer_authz.applications');b=next(t for t in triggers if t['internal'] and t['relation_oid']==a['relation_oid'] and t['oid']!=a['oid']);external=next(t for t in triggers if not t['internal'] and t['relation_oid']==a['relation_oid']);peer=next(t for t in triggers if t['relation_oid']!=a['relation_oid'])
    def ident(s):return '"'+s.replace('"','""')+'"'
    rejects=[]
    for label,target in [('internal/internal',b['name']),('internal/external',external['name'])]:
        sql='ALTER TRIGGER '+ident(a['name'])+' ON mixer_authz.applications RENAME TO '+ident(target)
        try:ADMIN.q(sql)
        except DBError as exc:assert exc.state=='42710',(label,exc.state);rejects.append({'mode':label,'sqlstate':exc.state,'error':str(exc)})
        else:raise AssertionError('actual duplicate trigger name accepted')
        capture('restoration after rejected '+label+' duplicate')
    sql='CREATE TRIGGER lifecycle_guard BEFORE UPDATE ON mixer_authz.applications FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle()'
    try:ADMIN.q(sql)
    except DBError as exc:assert exc.state=='42710';rejects.append({'mode':'external/external','sqlstate':exc.state,'error':str(exc)})
    else:raise AssertionError('duplicate external trigger name accepted')
    for label,name in [('same name on different relations',peer['name']),('different names on same relation','wildcard_unique_internal')]:
        assert not any(t['relation_oid']==a['relation_oid'] and t['name']==name for t in triggers)
        ADMIN.q('ALTER TRIGGER '+ident(a['name'])+' ON mixer_authz.applications RENAME TO '+ident(name))
        try:capture('portable actual '+label)
        finally:ADMIN.q('ALTER TRIGGER '+ident(name)+' ON mixer_authz.applications RENAME TO '+ident(a['name']))
    capture('restoration after trigger uniqueness probes')
    return {'actual_duplicate_name_rejections':rejects,'portable_name_controls':2,'raw_pair_constraint':'UNIQUE(tgrelid,tgname)','actual_database_bypass_demonstrated':False}
case('PostgreSQL enforces duplicate trigger names with portable controls',trigger_names)
case('final selected safe state',lambda:(capture('final selected safe state'),{'selected_safe':True})[1])
ADMIN.close()
summary={'schema':1,'total':len(RESULTS),'passed':sum(t['passed'] for t in RESULTS),'failed':[t['name'] for t in RESULTS if not t['passed']],'captures':CAPTURES,'safe_comparisons':sum(t['expected_selected_admission'] for t in CAPTURES),'selected_drift_rejections':sum(not t['expected_selected_admission'] for t in CAPTURES),'physical_or_native_runs':False}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));sys.exit(0 if not summary['failed'] else 1)
