#!/usr/bin/env python3
"""New review oracles; reuses frozen libpq/Flow fixtures, never their verdicts."""
import ast, hashlib, json, os, pathlib, sys, threading, time, traceback
HERE=pathlib.Path(__file__).resolve().parent
source=(HERE/'replay/source/tests.py').read_text()
# Reuse only the upstream fixture/transport definitions before its first matrix.
exec(compile(source[:source.index('def success(')],str(HERE/'replay/source/tests.py'),'exec'),globals())
CAT=(HERE/'replay/source/catalog.sql').read_text()
def catalog(): return json.loads(ADMIN.one(CAT))
def check(name, fn): case(name,fn)
def malformed_time(field,value):
    i,t=seed();i[field]=value
    with Flow(i,t) as f: deny(f.lookup)
    return {'rejected_at_entry':True,'field':field,'value':value}
for time_field in ['issued_at','expires_at','authentication_completed_at']:
    for value in [None,'NaN','Infinity','-Infinity',-1,9007199254740992,1.5]:
        check('strict numeric '+time_field+' '+str(value),lambda f=time_field,v=value:malformed_time(f,v))
def typmod_evidence():
    fields=ADMIN.q("SELECT attname,format_type(atttypid,atttypmod),atttypmod FROM pg_attribute WHERE attrelid='mixer_authz.verified_identity_v1'::regclass AND attname IN ('issued_at','expires_at','authentication_completed_at') ORDER BY attnum")
    assert all(r[1:] == ['numeric','-1'] for r in fields),fields
    observed=ADMIN.q("SELECT 1.5::numeric::text,1.5::numeric(20,0)::text")
    assert observed==[['1.5','2']],observed
    return {'actual_input_fields':fields,'unconstrained_and_typmod_control':observed}
check('installed unconstrained numeric and rounding control',typmod_evidence)
def missing_inputs(which):
    i,t=seed()
    for key in list(i if which=='identity' else t):
        if which=='target' and key in ['app','environment','platform','runtime_sha256','manifest_sha256']: continue
        value=dict(i if which=='identity' else t);value[key]=None
        with Flow(value if which=='identity' else i,value if which=='target' else t) as f: deny(f.lookup)
    return {'all_required_fields_null_rejected':True}
check('required identity null fields',lambda:missing_inputs('identity'))
check('required target null fields',lambda:missing_inputs('target'))
def scope_shape(shape):
    i,t=seed()
    with Flow(i,t) as f:
        cols=['profile_id','profile_version','issuer','subject','client_id','credential_sha256','issued_at','expires_at','identity_class']
        args=[]
        for k in cols:
            args.append(f"({record('verified_identity_v1',i)}).{k}")
        args+=[shape,str(i['authentication_completed_at'])]
        identity='ROW('+','.join(args)+')::mixer_authz.verified_identity_v1'
        deny(lambda:f.db.q('SELECT mixer_authz.lookup_admission('+identity+','+record('target_v1',t)+','+record('transaction_identity_v1',f.x)+')'))
    return {'closed_shape':True,'shape':shape}
for shape in ["'[0:0]={mixer.artifact.upload}'::text[]","ARRAY[['mixer.artifact.upload']]::text[]","ARRAY['mixer.artifact.read','mixer.artifact.upload','mixer.audit.read','mixer.extra']::text[]"]:
    check('scope array shape '+shape,lambda s=shape:scope_shape(s))
def exact_cutoff():
    i,t=seed();ADMIN.q(f"UPDATE mixer_authz.principals SET valid_after={i['issued_at']},revision=2;UPDATE mixer_authz.credential_families SET valid_after={i['issued_at']},revision=2")
    with Flow(i,t) as f:f.lookup();f.lock();d=f.decide();assert d['outcome']=='allowed';return d
check('valid-after equality is inclusive',exact_cutoff)
def current_profile_version():
    i,t=seed();ADMIN.q("UPDATE mixer_authz.identity_trust_profiles SET enabled=false,revision=2;UPDATE mixer_authz.identity_trust_profiles SET enabled=true,current_version=2,revision=3")
    with Flow(i,t) as f:f.lookup();f.lock();deny(f.decide)
    i['profile_version']=2
    with Flow(i,t) as f:f.lookup();f.lock();d=f.decide();assert d['outcome']=='allowed';return d
check('higher-version reenable rejects old profile and admits current',current_profile_version)
def denial_stable_namespace():
    i,t=seed();ADMIN.q(f"INSERT INTO mixer_authz.external_identity_bindings VALUES('11111111-0000-0000-0000-000000000002','profile','https://issuer.example','other-subject','client','human','{P}');INSERT INTO mixer_authz.credential_families VALUES('11111111-0000-0000-0000-000000000003','11111111-0000-0000-0000-000000000002','{P}','profile','active',0,1);INSERT INTO mixer_authz.credential_references VALUES('11111111-0000-0000-0000-000000000002',decode('{'11'*32}','hex'),'11111111-0000-0000-0000-000000000003','{P}','profile',{i['issued_at']},{i['expires_at']});INSERT INTO mixer_authz.credential_denials SELECT binding_id,jti_sha256,accepted_expires_at,accepted_issued_at,accepted_expires_at+30,1,'incident' FROM mixer_authz.credential_references WHERE binding_id='11111111-0000-0000-0000-000000000002'")
    with Flow(i,t) as f:f.lookup();f.lock();assert f.decide()['outcome']=='allowed'
    i['subject']='other-subject'
    with Flow(i,t) as f:f.lookup();f.lock();deny(f.decide)
    return {'same_hash_distinct_binding_denial_does_not_cross_namespace':True}
check('credential digest denial namespace isolation',denial_stable_namespace)
def sql_context_reset(which):
    i,t=seed()
    with Flow(i,t) as f:
        f.lookup();f.lock()
        if which=='xid': f.db.q('COMMIT;BEGIN;SET TRANSACTION ISOLATION LEVEL READ COMMITTED');f.db.q("SELECT set_config('mixer_authz.invocation_nonce',repeat('a',64),true),set_config('mixer_authz.deadline',"+lit(f.x['deadline'])+",true)")
        elif which=='nonce': f.db.q("SELECT set_config('mixer_authz.invocation_nonce','',true)")
        elif which=='deadline': f.db.q("SELECT set_config('mixer_authz.deadline',(clock_timestamp()+interval '4 seconds')::text,true)")
        deny(f.decide)
    return {'old_context_rejected':True,'mutation':which}
for which in ['xid','nonce','deadline']:check('transaction reset '+which,lambda w=which:sql_context_reset(w))
def wait(victim,blocker):
    until=time.monotonic()+.18
    while time.monotonic()<until:
        if ADMIN.one(f'SELECT {blocker}=ANY(pg_blocking_pids({victim}))')=='t':return
        time.sleep(.002)
    raise AssertionError('expected database wait absent')
def crossed_age():
    while True:
        wall=float(ADMIN.one('SELECT extract(epoch FROM clock_timestamp())'))
        if .60<wall%1<.70:break
        time.sleep(.005)
    boundary=int(wall)+1;i,t=seed();i['authentication_completed_at']=boundary-46
    with Flow(i,t) as f:
        f.lookup();b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.project_authorization_heads WHERE organization='o' AND project='p' FOR UPDATE");pid=int(b.one('SELECT pg_backend_pid()'));errors=[]
        try:
            while float(ADMIN.one('SELECT extract(epoch FROM clock_timestamp())'))<boundary-.08:time.sleep(.002)
            def locking():
                try:f.lock()
                except Exception as e:errors.append(repr(e))
            th=threading.Thread(target=locking);th.start();wait(f.x['backend'],pid)
            while float(ADMIN.one('SELECT extract(epoch FROM clock_timestamp())'))<boundary+.01:time.sleep(.002)
            b.q('COMMIT');th.join(1);assert not errors,errors;deny(f.decide)
            return {'actual_database_wait':True,'age_before':45,'age_at_release':46,'boundary':boundary,'rejected':True}
        finally:b.close()
check('observed lock wait crosses completion age45 to46',crossed_age)
def canonical_reacquire_profile():
    i,t=seed()
    with Flow(i,t) as f:
        f.lookup();a=dict(f.a,profile_revision=1,principal_revision=1,family_revision=1,organization_revision=1,project_revision=1,lock_statement_at='2000-01-01T00:00:00+00:00')
        b=DB();b.q('BEGIN');b.q("SELECT 1 FROM mixer_authz.identity_trust_profiles WHERE profile_id='profile' FOR UPDATE");pid=int(b.one('SELECT pg_backend_pid()'));results=[];errors=[]
        try:
            def deciding():
                try:results.append(f.call('decide_current',a))
                except Exception as e:errors.append(repr(e))
            th=threading.Thread(target=deciding);th.start();wait(f.x['backend'],pid);b.q('COMMIT');th.join(1)
            assert not errors and results[0]['outcome']=='allowed',(errors,results)
            return {'forged_prior_witness':True,'actual_profile_lock_observed':True}
        finally:b.close()
check('decide reacquires first canonical profile lock',canonical_reacquire_profile)
def lifecycle_guard_blindspot():
    seed();baseline=catalog();ADMIN.q('BEGIN')
    try:
        ADMIN.q('ALTER TABLE mixer_authz.external_identity_bindings DISABLE TRIGGER lifecycle_guard')
        after=catalog();enabled=ADMIN.one("SELECT tgenabled FROM pg_trigger WHERE tgrelid='mixer_authz.external_identity_bindings'::regclass AND tgname='lifecycle_guard'")
        assert after==baseline,'catalog unexpectedly detects disabled trigger'
        ADMIN.q("UPDATE mixer_authz.external_identity_bindings SET subject='changed-without-guard'")
        subject=ADMIN.one('SELECT subject FROM mixer_authz.external_identity_bindings');assert subject=='changed-without-guard'
        return {'finding':'ASR01','producer_catalog_equal':True,'trigger_enabled_code':enabled,'immutable_subject_update_succeeded':True,'drift_rolled_back':True}
    finally:ADMIN.q('ROLLBACK')
check('FINDING catalog misses disabled lifecycle trigger',lifecycle_guard_blindspot)
def fk_guard_blindspot():
    seed();baseline=catalog();ADMIN.q('BEGIN')
    try:
        ADMIN.q('ALTER TABLE mixer_authz.external_identity_bindings DISABLE TRIGGER ALL')
        assert catalog()==baseline
        ADMIN.q("INSERT INTO mixer_authz.external_identity_bindings VALUES('aaaaaaaa-0000-0000-0000-000000000002','absent-profile','https://absent.example','subject','client','human','aaaaaaaa-0000-0000-0000-000000000001')")
        return {'finding':'ASR01','producer_catalog_equal':True,'absent_profile_principal_fks_bypassed':True,'drift_rolled_back':True}
    finally:ADMIN.q('ROLLBACK')
check('FINDING catalog misses disabled FK enforcement triggers',fk_guard_blindspot)
def durability_blindspot():
    seed();baseline=catalog();ADMIN.q('BEGIN')
    try:
        ADMIN.q('ALTER TABLE mixer_authz.credential_denials SET UNLOGGED')
        assert catalog()==baseline
        persistence=ADMIN.one("SELECT relpersistence FROM pg_class WHERE oid='mixer_authz.credential_denials'::regclass")
        assert persistence=='u'
        return {'finding':'ASR02','producer_catalog_equal':True,'relation_persistence':persistence,'revocation_denials_no_longer_crash_durable':True,'drift_rolled_back':True}
    finally:ADMIN.q('ROLLBACK')
check('FINDING catalog misses unlogged revocation denial table',durability_blindspot)
def replication_identity_blindspot():
    seed();baseline=catalog();ADMIN.q('BEGIN')
    try:
        ADMIN.q('ALTER TABLE mixer_authz.credential_denials REPLICA IDENTITY NOTHING')
        assert catalog()==baseline
        return {'finding':'ASR02','producer_catalog_equal':True,'actual_replica_identity':ADMIN.one("SELECT relreplident FROM pg_class WHERE oid='mixer_authz.credential_denials'::regclass"),'logical_replication_unqualified':True,'drift_rolled_back':True}
    finally:ADMIN.q('ROLLBACK')
check('FINDING catalog misses replica identity drift',replication_identity_blindspot)
def dangerous_parameter_grant():
    seed();baseline=catalog();ADMIN.q('BEGIN')
    try:
        ADMIN.q('GRANT SET ON PARAMETER session_replication_role TO mixer_hosted_runtime')
        assert catalog()==baseline
        assert ADMIN.one("SELECT has_parameter_privilege('mixer_hosted_runtime','session_replication_role','SET')")=='t'
        return {'finding':'ASR03','producer_catalog_equal':True,'runtime_parameter_set_effective':True,'current_direct_domain_dml_absent':True,'grant_rolled_back':True}
    finally:ADMIN.q('ROLLBACK')
check('FINDING catalog misses runtime trigger-bypass parameter grant',dangerous_parameter_grant)
def covered_drift(sql):
    baseline=catalog();ADMIN.q('BEGIN')
    try:
        ADMIN.q(sql);assert catalog()!=baseline
        return {'producer_catalog_detects_drift':True,'drift_rolled_back':True}
    finally:ADMIN.q('ROLLBACK')
for label,sql in [
    ('policy predicate',"ALTER POLICY resolver_select ON mixer_authz.principals USING(false)"),
    ('policy role',"ALTER POLICY resolver_select ON mixer_authz.principals TO PUBLIC"),
    ('policy restrictive',"DROP POLICY resolver_select ON mixer_authz.principals;CREATE POLICY resolver_select ON mixer_authz.principals AS RESTRICTIVE FOR SELECT TO mixer_hosted_authz_resolver USING(true)"),
    ('FK deferrability',"ALTER TABLE mixer_authz.external_identity_bindings ALTER CONSTRAINT external_identity_bindings_principal_id_identity_class_fkey DEFERRABLE INITIALLY DEFERRED"),
    ('CHECK validation',"ALTER TABLE mixer_authz.principals DROP CONSTRAINT principals_valid_after_check;ALTER TABLE mixer_authz.principals ADD CONSTRAINT principals_valid_after_check CHECK(valid_after BETWEEN 0 AND 9007199254740991) NOT VALID"),
    ('index predicate',"DROP INDEX mixer_authz.project_memberships_active_unique;CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status IN ('active','invited')")
]:check('manifest positive drift control '+label,lambda s=sql:covered_drift(s))
def independent_enforcement_catalog():
    baseline=json.loads(ADMIN.one("""SELECT jsonb_build_object(
      'relations',(SELECT jsonb_agg(jsonb_build_object('name',c.relname,'persistence',c.relpersistence,'replica_identity',c.relreplident) ORDER BY c.relname) FROM pg_class c WHERE c.relnamespace='mixer_authz'::regnamespace AND c.relkind='r'),
      'triggers',(SELECT jsonb_agg(jsonb_build_object('table',c.relname,'name',t.tgname,'enabled',t.tgenabled,'internal',t.tgisinternal,'constraint',t.tgconstraint::text,'deferrable',t.tgdeferrable,'initially_deferred',t.tginitdeferred) ORDER BY c.relname,t.tgname) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace='mixer_authz'::regnamespace),
      'constraints',(SELECT jsonb_agg(jsonb_build_object('table',c.conrelid::regclass::text,'name',c.conname,'validated',c.convalidated,'deferrable',c.condeferrable,'initially_deferred',c.condeferred) ORDER BY c.conrelid::regclass::text,c.conname) FROM pg_constraint c WHERE c.connamespace='mixer_authz'::regnamespace),
      'indexes',(SELECT jsonb_agg(jsonb_build_object('name',i.indexrelid::regclass::text,'valid',i.indisvalid,'ready',i.indisready,'live',i.indislive,'immediate',i.indimmediate) ORDER BY i.indexrelid::regclass::text) FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid WHERE c.relnamespace='mixer_authz'::regnamespace),
      'runtime_parameter_acl',(SELECT coalesce(jsonb_agg(jsonb_build_object('parameter',parname,'acl',paracl::text) ORDER BY parname),'[]'::jsonb) FROM pg_parameter_acl WHERE has_parameter_privilege('mixer_hosted_runtime',oid,'SET') OR has_parameter_privilege('mixer_hosted_runtime',oid,'ALTER SYSTEM')))
    """))
    assert all(r['persistence']=='p' and r['replica_identity']=='d' for r in baseline['relations'])
    assert all(t['enabled']=='O' for t in baseline['triggers'])
    assert all(c['validated'] and not c['deferrable'] and not c['initially_deferred'] for c in baseline['constraints'])
    assert all(i['valid'] and i['ready'] and i['live'] and i['immediate'] for i in baseline['indexes'])
    assert baseline['runtime_parameter_acl']==[]
    (OUT/'independent-enforcement-catalog.json').write_text(json.dumps(baseline,indent=2,sort_keys=True)+'\n')
    return {'baseline_constraints':len(baseline['constraints']),'baseline_indexes':len(baseline['indexes']),'baseline_including_internal_triggers':len(baseline['triggers']),'no_unsafe_baseline_flags_found':True,'producer_omits_explicit_flags':True}
check('independent baseline enforcement state and flags',independent_enforcement_catalog)
def current_role_catalog_controls():
    seed();baseline=catalog()
    with DB('mixer_hosted_runtime') as db:
        assert json.loads(db.one(CAT))==baseline
        for table in TABLES:
            for permission in ['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']:
                assert db.one("SELECT has_table_privilege(current_user,"+lit('mixer_authz.'+table)+','+lit(permission)+')')=='f'
    return {'runtime_same_catalog':True,'tables':len(TABLES),'direct_privileges_checked':98}
check('runtime all table privilege controls',current_role_catalog_controls)
ADMIN.close()
summary={'total':len(RESULTS),'passed':sum(x['passed'] for x in RESULTS),'failed':[x['name'] for x in RESULTS if not x['passed']],'skipped':0,'excluded':0,'findings':['ASR01','ASR02','ASR03'],'libpq_path':libpath,'libpq_version':version()}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));sys.exit(0 if not summary['failed'] else 1)
