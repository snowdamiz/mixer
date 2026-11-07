#!/usr/bin/env python3
"""Independent frozen Unit A replay on one exact identity-owned PG16 container."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

REPO = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PRODUCER = REPO / 'verification/hosted-browser-callback-storage'
EXPECTED = '0a5c39cf33240c0be778f9fb654a9adf0d8d4a1150d5176ce1d9fbae5480b70a'
SELECTED = PRODUCER / 'attempts/20261025T213600.582572Z-58a09c'
ROOT = SELECTED / 'inputs'
DEPENDENCIES = SELECTED / 'dependencies'
IMAGE = 'sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97'
DEPS = ['telemetry','decimal','db_connection','ecto','ecto_sql','postgrex','jason','oban','jose','mint','hpax']
IDENTITY = ['encoding','bounded_json','trust_snapshot','manifest','startup_config','admission','global_address','http_freshness','http_wire_guard','dns_resolver','bounded_tcp','jwks_transport','fetch_flight','key_owner']
BROWSER = ['vault','stored_snapshot','config','configuration_digest','custody','runtime_config','storage_schema','activation_preparation','activation_preparation_schema','catalog_manifest','catalog_manifest_v2','catalog','relation_manifest','relation_catalog','preauth_draft','lifecycle_repo','callback_draft','store','runtime_owner','protocol']
SOURCES = (['hosted/lib/mixer_hosted/identity/'+p+'.ex' for p in IDENTITY] + ['hosted/lib/mixer_hosted/'+p+'.ex' for p in ['runtime_config','repo']] + ['hosted/lib/mixer_hosted/browser_auth/'+p+'.ex' for p in BROWSER] + ['hosted/lib/mixer_hosted/customer_artifacts/schema.ex'])

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(d): return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def verify_packet():
    handoff_path = PRODUCER/'handoff.json'
    assert sha(handoff_path) == EXPECTED
    h = json.loads(handoff_path.read_bytes())
    checks = {'handoff_sha256':EXPECTED,'members':0,'preserved_receipts':0,'preserved_outputs':0,'selected_sources':0,'selected_dependency_binaries':0,'selected_dependency_sources':0}
    for rel,digest in h['members'].items():
        assert sha(REPO/rel)==digest
        checks['members']+=1
    for attempt in h['preserved_attempts']:
        p=REPO/attempt['receipt']
        assert sha(p)==attempt['sha256']
        receipt=json.loads(p.read_bytes())
        assert all(receipt['cleanup'].values())
        for rel,digest in receipt['outputs'].items():
            assert sha(p.parent/rel)==digest
            checks['preserved_outputs']+=1
        checks['preserved_receipts']+=1
    assert sha(SELECTED/'receipt.json')==h['selected_receipt_sha256']
    r=json.loads((SELECTED/'receipt.json').read_bytes())
    for key,subroot,countkey in [('sources',ROOT,'selected_sources'),('dependencies',DEPENDENCIES,'selected_dependency_binaries'),('dependency_sources',DEPENDENCIES,'selected_dependency_sources')]:
        assert r[key]==r[key+'_after']
        for rel,digest in r[key].items():
            assert sha(subroot/rel)==digest
            assert sha(REPO/rel)==digest
            checks[countkey]+=1
    assert tree(r['sources'])==h['source_tree_sha256']==r['source_tree_sha256']
    assert tree(r['dependencies'])==r['dependency_tree_sha256']
    assert tree(r['dependency_sources'])==r['dependency_source_tree_sha256']
    assert r['success'] and all(r['cleanup'].values())
    for key,count in [('checks',35),('preauth_regression_checks',30),('begin_regression_checks',30)]:
        assert len(r[key])==count and all(c['passed'] for c in r[key])
    return h,r,checks

def main():
    out=BASE/'attempts'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-pg16-'+uuid.uuid4().hex[:6])
    out.mkdir(parents=True)
    scratch=Path(tempfile.mkdtemp(prefix='mixer-callback-independent-'))
    scratch_identity=(scratch.stat().st_dev,scratch.stat().st_ino)
    name='mixer-callback-review-'+uuid.uuid4().hex[:12]
    receipt={'schema':1,'scope':'Frozen Unit A selected ordinary-source independent PG16 replay plus separate reviewer controls. Manual local non-TLS random-port fixture; no Application/Neon/ClaimOwner/provider/HTTP/native qualification.','commands':[],'owned_scratch':str(scratch),'scratch_device_inode':scratch_identity,'owned_container_name':name,'cleanup':{},'agent':{'model':'gpt-6.1-sol','reasoning_effort':'xhigh','context':'fresh bounded independent Unit A review'}}
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL','TMPDIR']}
    env.update(ERL_FLAGS='+S 2:2 +SDcpu 1 +SDio 1',MIX_ENV='test',ERL_CRASH_DUMP=str(scratch/'erl.dump'),PREAUTH_OUTPUT=str(out))
    created=False
    container_id=None
    selected={}
    dependencies={}
    def run(label,argv,data=None,check=True,timeout=55,cwd=ROOT):
        argv=list(map(str,argv))
        command={'label':label,'argv':argv,'cwd':str(cwd),'timeout_seconds':timeout}
        receipt['commands'].append(command)
        proc=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.PIPE if data is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        command['owned_process_group']=proc.pid
        try:
            stdout,stderr=proc.communicate(data.encode() if isinstance(data,str) else data,timeout=timeout)
            command['timed_out']=False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL)
            stdout,stderr=proc.communicate(timeout=5)
            command['timed_out']=True
        (out/(label+'.stdout')).write_bytes(stdout)
        (out/(label+'.stderr')).write_bytes(stderr)
        command['exit']=proc.returncode
        command['owned_process_reaped']=proc.poll() is not None
        print(label+': exit '+str(proc.returncode),flush=True)
        if check and (proc.returncode or command['timed_out']): raise RuntimeError(label+' failed')
        return proc.returncode,stdout.decode()
    try:
        h,r,checks=verify_packet()
        receipt['packet_verification']=checks
        receipt['producer_receipt_sha256']=sha(SELECTED/'receipt.json')
        receipt['producer_source_revision']=r['revision']
        receipt['producer_git_tree']=r['git_tree']
        receipt['source_tree_sha256']=r['source_tree_sha256']
        selected=r['sources']
        dependencies=r['dependencies']|r['dependency_sources']
        receipt['sources']=selected
        receipt['dependency_binaries']=r['dependencies']
        receipt['dependency_sources']=r['dependency_sources']
        for rel in selected:
            target=out/'inputs'/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/rel,target)
        for rel in dependencies:
            target=out/'dependencies'/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(DEPENDENCIES/rel,target)
        receipt['review_sources']={str(p.relative_to(REPO)):sha(p) for p in BASE.iterdir() if p.is_file()}
        for rel in receipt['review_sources']:
            target=out/'inputs'/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(REPO/rel,target)
        for label,argv in [('revision',['git','rev-parse','HEAD']),('git-tree',['git','rev-parse','HEAD^{tree}']),('elixir-version',['elixir','--version']),('mix-version',['mix','--version']),('python-version',['python3','--version']),('git-version',['git','--version']),('docker-version',['docker','--version'])]:
            _,value=run(label,argv,cwd=REPO)
            if label=='revision': receipt['root_revision_context_only']=value.strip()
            if label=='git-tree': receipt['root_git_tree_context_only']=value.strip()
        run('image-identity',['docker','image','inspect',IMAGE,'--format','{{.Id}} {{.Os}} {{.Architecture}} {{json .RepoDigests}}'])
        formatting=['hosted/lib/mixer_hosted/browser_auth/'+p+'.ex' for p in ['callback_draft','store']]+['verification/hosted-browser-callback-storage/'+p+'.exs' for p in ['live','controls']]
        for p in formatting: shutil.copy2(ROOT/p,scratch/Path(p).name)
        run('mix-format',['mix','format','--check-formatted']+[Path(p).name for p in formatting],cwd=scratch)
        workspace=scratch/'workspace'
        for rel in set(selected)|set(dependencies):
            target=workspace/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2((ROOT if rel in selected else DEPENDENCIES)/rel,target)
        receipt['unified_compile_workspace_content_sha256']=tree({rel:sha(workspace/rel) for rel in sorted(set(selected)|set(dependencies))})
        depdirs=[DEPENDENCIES/'hosted/_build/test/lib'/d/'ebin' for d in DEPS]
        args=['elixir']+[a for d in depdirs for a in ['-pa',d]]
        ebin=scratch/'ebin'
        ebin.mkdir()
        compile_code='Mix.start(); Mix.env(:test); case Kernel.ParallelCompiler.compile_to_path(tl(System.argv()),hd(System.argv()),warnings_as_errors: true, return_diagnostics: true) do {:ok,_,%{compile_warnings: [], runtime_warnings: []}} -> :ok; _ -> System.halt(1) end'
        run('selected-compile',args+['-e',compile_code,ebin]+SOURCES,cwd=workspace)
        shutil.copytree(ebin,out/'product-ebin')
        receipt['compiled_product_binaries']={str(p.relative_to(out)):sha(p) for p in (out/'product-ebin').iterdir() if p.is_file()}
        run('postgres-create',['docker','create','--name',name,'--publish','127.0.0.1::5432','--env','POSTGRES_USER=browser_admin','--env','POSTGRES_HOST_AUTH_METHOD=trust','--env','POSTGRES_INITDB_ARGS=--no-locale --encoding=UTF8',IMAGE,'-c','timezone=UTC','-c','log_statement=none','-c','log_min_messages=panic','-c','log_min_error_statement=panic','-c','log_parameter_max_length_on_error=0'])
        created=True
        _,value=run('postgres-created-identity',['docker','inspect',name,'--format','{{.Id}} {{.Image}}'])
        container_id,image_id=value.strip().split()
        assert len(container_id)==64 and image_id==IMAGE
        receipt['owned_container_id']=container_id
        run('postgres-start',['docker','start',name])
        for index in range(40):
            status,_=run('postgres-ready-%02d'%index,['docker','exec',name,'pg_isready','-U','browser_admin'],check=False,timeout=5)
            if status==0: break
            time.sleep(0.2)
        else: raise RuntimeError('owned postgres not ready')
        _,value=run('postgres-port',['docker','port',name,'5432/tcp'])
        env['PREAUTH_PORT']=value.strip().rsplit(':',1)[1]
        receipt['port']=int(env['PREAUTH_PORT'])
        psql=['docker','exec','-i',name,'psql','-X','-q','-A','-t','-U','browser_admin','-d','postgres','-v','ON_ERROR_STOP=1']
        _,value=run('postgres-version',psql,data="SELECT version(),current_setting('server_version_num'),datcollate,datctype FROM pg_database WHERE datname=current_database();")
        assert '|16' in value and '|C|C' in value
        roles=[('browser_schema_owner','NOLOGIN'),('browser_writer','NOLOGIN'),('browser_lifecycle','LOGIN'),('browser_ordinary','LOGIN')]
        run('roles',psql,data=';'.join('CREATE ROLE '+r+' '+login+' NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION' for r,login in roles)+';')
        run('database',psql,data='CREATE DATABASE browser_storage OWNER browser_schema_owner;')
        elixir=args+['-pa',ebin]
        run('install',elixir+[ROOT/'verification/hosted-browser-begin-login/install.exs'])
        for label,script,count,bound in [('preauth-regression','hosted-browser-preauth-store/live.exs',30,55),('begin-regression','hosted-browser-begin-login/live.exs',30,55),('callback-replay','hosted-browser-callback-storage/live.exs',35,110)]:
            run(label,elixir+[ROOT/'verification'/script],timeout=bound)
            results=json.loads((out/'checks.json').read_bytes())
            cleanup=json.loads((out/'beam-cleanup.json').read_bytes())
            assert len(results)==count and all(c['passed'] for c in results) and all(cleanup.values())
            receipt[label]={'checks':results,'beam_cleanup':cleanup}
            shutil.move(out/'checks.json',out/(label+'-checks.json'))
            shutil.move(out/'beam-cleanup.json',out/(label+'-beam-cleanup.json'))
        run('independent-controls',elixir+[BASE/'runtime_review.exs'],timeout=55)
        receipt['independent_controls']=json.loads((out/'review-checks.json').read_bytes())
        receipt['independent_beam_cleanup']=json.loads((out/'beam-cleanup.json').read_bytes())
        assert all(receipt['independent_beam_cleanup'].values())
        receipt['execution_completed']=True
    except Exception as error:
        receipt['failure_class']=type(error).__name__
        if isinstance(error,RuntimeError) and str(error).endswith(' failed'): receipt['failed_command']=str(error)[:-7]
    finally:
        if created:
            _,current=run('postgres-cleanup-identity',['docker','inspect',name,'--format','{{.Id}} {{.Image}}'],check=False,timeout=10)
            identity=current.strip().split()
            exact=container_id is not None and identity==[container_id,IMAGE]
            receipt['cleanup']['owned_container_identity_preserved']=exact
            if exact:
                run('postgres-logs',['docker','logs',name],check=False,timeout=10)
                run('postgres-stop',['docker','stop','--time','2',name],check=False,timeout=10)
                run('postgres-remove',['docker','rm','--volumes',name],check=False,timeout=10)
            status,stdout=run('owned-container-absent',['docker','inspect',name],check=False,timeout=10)
            diagnostic=(out/'owned-container-absent.stderr').read_text()
            receipt['cleanup']['owned_container_absent']=status==1 and json.loads(stdout)==[] and name in diagnostic and ('No such object' in diagnostic or 'No such container' in diagnostic)
        else:
            receipt['cleanup']['owned_container_absent']=True
            receipt['cleanup']['owned_container_identity_preserved']=True
        exact=scratch.exists() and (scratch.stat().st_dev,scratch.stat().st_ino)==scratch_identity
        receipt['cleanup']['owned_scratch_identity_preserved']=exact
        if exact: shutil.rmtree(scratch)
        receipt['cleanup']['owned_scratch_absent']=not scratch.exists()
        receipt['cleanup']['owned_command_processes_reaped']=all(c.get('owned_process_reaped') for c in receipt['commands'])
        receipt['cleanup']['no_native_capture_ui_phone_provider_or_unrelated_process_discovery']=True
        receipt['source_changes']=[p for p,h in selected.items() if sha(ROOT/p)!=h or sha(REPO/p)!=h]
        receipt['dependency_changes']=[p for p,h in dependencies.items() if sha(DEPENDENCIES/p)!=h]
        for name2,key in [('review-checks.json','independent_controls'),('beam-cleanup.json','independent_beam_cleanup')]:
            if (out/name2).is_file(): receipt[key]=json.loads((out/name2).read_bytes())
        receipt['outputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='receipt.json' and 'inputs' not in p.relative_to(out).parts and 'dependencies' not in p.relative_to(out).parts}
        receipt['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat()
        receipt['valid_execution_receipt']=receipt.get('execution_completed',False) and all(receipt['cleanup'].values()) and not receipt['source_changes'] and not receipt['dependency_changes']
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        print(out.relative_to(REPO),flush=True)
        print(json.dumps({k:receipt.get(k) for k in ['valid_execution_receipt','failure_class','failed_command','cleanup']}),flush=True)
    return 0 if receipt['valid_execution_receipt'] else 1

if __name__=='__main__': raise SystemExit(main())
