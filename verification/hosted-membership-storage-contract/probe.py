#!/usr/bin/env python3
"""One owned Unix-socket PostgreSQL cluster; evidence is a pattern probe only."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / ('run-' + str(1 + len(list(HERE.glob('run-*')))))
OUT.mkdir(exist_ok=False)
commands, cases = [], []
bindir = pathlib.Path(subprocess.check_output(['pg_config','--bindir'],text=True).strip())
base = pathlib.Path(tempfile.mkdtemp(prefix='mixer-authz-',dir='/private/tmp')).resolve()
data, sock = base/'data', base/'socket'
sock.mkdir()

def run(argv, *, input=None, ok=True):
    start = time.monotonic()
    p = subprocess.run([str(x) for x in argv],input=input,text=True,capture_output=True,timeout=15)
    commands.append(dict(argv=[str(x) for x in argv],stdin=input,exit=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=round(time.monotonic()-start,4)))
    if ok and p.returncode:
        raise AssertionError(commands[-1])
    return p

def sql(q, role='probe_runtime', ok=True):
    return run([bindir/'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose','-h',sock,'-U',role,'-d','postgres'],input=q,ok=ok)

def expect(name,q,expected=None,error=None,role='probe_runtime'):
    p=sql(q,role,ok=error is None)
    assert (p.returncode and error in p.stderr) if error else (p.stdout.strip()==expected), (name,p.stdout,p.stderr)
    cases.append(dict(name=name,status='passed',expected_sqlstate=error,observed=p.stdout.strip(),stderr=p.stderr))

def held(q):
    argv=[str(bindir/'psql'),'-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-h',str(sock),'-U','bootstrap','-d','postgres']
    p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    p.stdin.write('BEGIN;\n'+q+'\n\\echo PROBE_READY\n');p.stdin.flush()
    output=[]
    while True:
        line=p.stdout.readline()
        if not line: raise AssertionError('holder exited before ready')
        output.append(line)
        if line.strip()=='PROBE_READY': break
    return p,argv,output,q

def release(h):
    p,argv,output,q=h
    tail,err=p.communicate('COMMIT;\n',timeout=5)
    commands.append(dict(argv=argv,stdin='BEGIN;\n'+q+'\n\\echo PROBE_READY\nCOMMIT;',exit=p.returncode,stdout=''.join(output)+tail,stderr=err))
    assert p.returncode==0

context="SELECT set_config('probe.principal','p',true),set_config('probe.org','a',true),set_config('probe.project','p',true),set_config('probe.action','artifact.read',true);"
guard="""SELECT EXISTS(SELECT 1 FROM pg_roles r WHERE (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolname IN ('probe_owner','probe_resolver','pg_read_all_data','pg_write_all_data','pg_read_server_files','pg_write_server_files','pg_execute_server_program')) AND pg_has_role(current_user,r.oid,'MEMBER'));"""
started=False
try:
    run([bindir/'postgres','--version'])
    run([bindir/'psql','--version'])
    run(['python3','--version'])
    run(['git','-C',ROOT,'rev-parse','HEAD'])
    run([bindir/'initdb','-D',data,'-U','bootstrap','-A','trust','--no-locale','-E','UTF8'])
    run([bindir/'pg_ctl','-D',data,'-l',base/'postgres.log','-o',f"-k {sock} -c listen_addresses='' -c unix_socket_permissions=0700 -c max_connections=12",'start','-w'])
    started=True
    sql((HERE/'probe.sql').read_text(),'bootstrap')
    expect('recursive_rls_is_rejected','SELECT * FROM probe_auth.recursive_members;',error='42P17')
    expect('select_only_cannot_for_share','SELECT probe_auth.lock_chain();',error='42501')
    sql("DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['profiles','principals','families','org_heads','project_heads'] LOOP EXECUTE format('GRANT UPDATE(revision) ON probe_auth.%I TO probe_resolver', t); END LOOP; END $$;",'bootstrap')
    expect('column_grant_without_update_rls_cannot_lock','SELECT probe_auth.lock_chain();',error='P0002')
    sql("DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['profiles','principals','families','org_heads','project_heads'] LOOP EXECUTE format('CREATE POLICY resolver_lock ON probe_auth.%I FOR UPDATE TO probe_resolver USING (true) WITH CHECK (true)', t); END LOOP; END $$;",'bootstrap')
    expect('column_grant_and_update_policy_permit_share_lock','BEGIN; SELECT probe_auth.lock_chain(); COMMIT;',expected='5')
    expect('runtime_cannot_read_policy_rows','SELECT * FROM probe_auth.memberships;',error='42501')
    expect('runtime_cannot_mutate_policy','UPDATE probe_auth.principals SET active=false;',error='42501')
    expect('missing_context_denies','SELECT count(*) FROM probe_domain.artifacts;',expected='0')
    expect('publisher_guc_is_not_authority',"BEGIN; SET LOCAL mixer.role='publisher'; SELECT count(*) FROM probe_domain.artifacts; COMMIT;",expected='0')
    expect('exact_scope_policy_without_recursive_rls','BEGIN; '+context+' SELECT string_agg(digest,\',\') FROM probe_domain.artifacts; COMMIT;',expected='p|a|p|artifact.read\ndigest-a')
    expect('wrong_action_denies','BEGIN; '+context+" SELECT set_config('probe.action','release.publish',true); SELECT count(*) FROM probe_domain.artifacts; COMMIT;",expected='p|a|p|artifact.read\nrelease.publish\n0')
    expect('runtime_guard_accepts_narrow_role',guard,expected='f')
    expect('runtime_guard_rejects_bypass',guard,expected='t',role='probe_bypass')
    expect('runtime_guard_rejects_noinherit_owner_chain',guard,expected='t',role='probe_chain')
    expect('runtime_cannot_set_resolver','SET ROLE probe_resolver;',error='42501')
    h=held('SET LOCAL ROLE probe_runtime; SELECT probe_auth.lock_chain();')
    argv=[str(bindir/'psql'),'-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-h',str(sock),'-U','bootstrap','-d','postgres']
    writer=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    writer.stdin.write("SET lock_timeout='2s'; UPDATE probe_auth.families SET active=false,revision=revision+1 WHERE id='p';\n"); writer.stdin.close(); writer.stdin=None
    time.sleep(.15)
    assert writer.poll() is None, 'revocation must wait for admitted share lock'
    release(h)
    stdout,stderr=writer.communicate(timeout=5)
    assert writer.returncode==0,stderr
    commands.append(dict(argv=argv,stdin='UPDATE families after reader share locks',stdout=stdout,stderr=stderr,exit=writer.returncode))
    cases.append(dict(name='revocation_waits_for_reader_then_commits',status='passed'))
    expect('post_revoke_fresh_policy_denies','BEGIN; '+context+' SELECT probe_auth.lock_chain(); SELECT count(*) FROM probe_domain.artifacts; COMMIT;',expected='p|a|p|artifact.read\n5\n0')
    sql("UPDATE probe_auth.families SET active=true,revision=revision+1 WHERE id='p';",'bootstrap')
    h=held("UPDATE probe_auth.families SET active=false,revision=revision+1 WHERE id='p';")
    expect('lock_timeout_rolls_back',"BEGIN; SET LOCAL lock_timeout='100ms'; SELECT probe_auth.lock_chain(); COMMIT;",error='55P03')
    reader=subprocess.Popen([*argv[:-4],'-U','probe_runtime','-d','postgres'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    reader.stdin.write('BEGIN; '+context+' SELECT probe_auth.lock_chain(); SELECT count(*) FROM probe_domain.artifacts; COMMIT;\n');reader.stdin.close();reader.stdin=None
    time.sleep(.15)
    assert reader.poll() is None,'reader must wait for writer'
    release(h)
    stdout,stderr=reader.communicate(timeout=5)
    assert reader.returncode==0 and stdout.strip().endswith('0'),(stdout,stderr)
    commands.append(dict(argv=[*argv[:-4],'-U','probe_runtime','-d','postgres'],stdin='BEGIN; '+context+' SELECT probe_auth.lock_chain(); SELECT count(*) FROM probe_domain.artifacts; COMMIT;',stdout=stdout,stderr=stderr,exit=reader.returncode))
    cases.append(dict(name='writer_first_reader_waits_then_reads_revocation',status='passed'))
    expect('transaction_local_context_clears_on_reuse','BEGIN; '+context+' ROLLBACK; SELECT count(*) FROM probe_domain.artifacts;',expected='p|a|p|artifact.read\n0')
finally:
    stopped = run([bindir/'pg_ctl','-D',data,'stop','-m','immediate','-w'],ok=False) if started else None
    if (base/'postgres.log').exists(): shutil.copyfile(base/'postgres.log',OUT/'postgres.log')
    cleanup=dict(owned_base=str(base),postgres_stopped=bool(stopped and stopped.returncode==0),socket_removed=False,other_clusters_touched=False)
    if not started or cleanup['postgres_stopped']:
        shutil.rmtree(base);cleanup['socket_removed']=not base.exists()
    (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'probe.py',HERE/'probe.sql',ROOT/'AGENTS.md',ROOT/'mixer-product-plan.md',ROOT/'docs/hosted-identity-contract.md',ROOT/'docs/hosted-token-verifier.md',ROOT/'verification/hosted-identity-contract/root-acceptance.json',ROOT/'verification/hosted-token-verifier-root-review/acceptance.json']}
    (OUT/'receipt.json').write_text(json.dumps(dict(schema=1,scope='Disposable PostgreSQL privilege/RLS/lock pattern probe only; not hosted authorization, HTTP, provider, migration or GA evidence',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),inputs=inputs,cases=cases,cleanup=cleanup),indent=2)+'\n')
print(json.dumps(dict(cases=len(cases),cleanup=cleanup)))
