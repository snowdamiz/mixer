#!/usr/bin/env python3
"""Real PostgreSQL integration in a new private Unix-socket-only test cluster.

Never connects to a configured/user database, never alters installed clusters.
Only this runner-created data directory is initialized, restarted and removed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
output = a.output.absolute(); output.mkdir(parents=True, exist_ok=False)
commands = []
receipt = {'schema':1, 'status':'running', 'scope':'real isolated local PostgreSQL transactional/RLS tests; no hosted/GA claim', 'commands':commands, 'mockDatabase':False}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def run(name,args,env=None,timeout=180):
    args=[str(x) for x in args]; start=time.monotonic()
    item={'name':name,'command':args,'exitCode':None,'executableSHA256':digest(args[0])}; commands.append(item)
    try:
        with (output/(name+'.stdout')).open('xb') as out, (output/(name+'.stderr')).open('xb') as err:
            result=subprocess.run(args,cwd=ROOT,env=env,stdout=out,stderr=err,timeout=timeout)
            item['exitCode']=result.returncode
        if result.returncode: raise RuntimeError(name+' failed; see captured logs')
    except subprocess.TimeoutExpired:
        item['timedOut']=True;raise
    finally:
        item['elapsedSeconds']=round(time.monotonic()-start,3)
        for stream in ['stdout','stderr']:
            path=output/(name+'.'+stream)
            item[stream]={'path':path.name,'bytes':path.stat().st_size,'sha256':digest(path)}
    return (output/(name+'.stdout')).read_text()

tools = {}
for tool in ['initdb','pg_ctl','postgres','psql','go']:
    value=shutil.which(tool)
    if not value: raise SystemExit('Missing local tool: '+tool)
    tools[tool]=str(Path(value).absolute())
receipt['tools']={key:{'path':value,'sha256':digest(value)} for key,value in tools.items()}
inputs=sorted([*ROOT.rglob('*.go'),*ROOT.glob('release/migrations/*.sql'),ROOT/'go.mod',ROOT/'go.sum',Path(__file__)])
receipt['sourceSHA256']={str(path.relative_to(ROOT)):digest(path) for path in inputs}
cluster = Path(tempfile.mkdtemp(prefix='mixer-pg-'))
cluster.chmod(0o700)
data=cluster/'data'; sockets=cluster/'socket'; sockets.mkdir(mode=0o700)
(cluster/'mixer-test-cluster').write_text('original-mixer-postgres-tests\n')
started=False
try:
    receipt['postgresVersion']=run('postgres-version',[tools['postgres'],'--version']).strip()
    receipt['psqlVersion']=run('psql-version',[tools['psql'],'--version']).strip()
    receipt['goVersion']=run('go-version',[tools['go'],'version']).strip()
    selected_go=Path(run('go-root',[tools['go'],'env','GOROOT']).strip())/'bin/go'
    receipt['selectedGoToolchain']={'path':str(selected_go),'sha256':digest(selected_go)}
    run('initialize',[tools['initdb'],'-D',data,'-U','mixer_migration_owner','--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8'])
    run('start',[tools['pg_ctl'],'-D',data,'-l',output/'postgres.log','-o',f"-k {sockets} -c listen_addresses='' -c fsync=on -c full_page_writes=on",'-w','start'])
    started=True
    env={k:v for k,v in os.environ.items() if not k.startswith(('PG','DYLD_','LD_','MIXER_TEST_'))}
    env.update(MIXER_TEST_POSTGRES_OWNER=f'host={sockets} port=5432 dbname=postgres user=mixer_migration_owner sslmode=disable',
               MIXER_TEST_POSTGRES_DATA_DIRECTORY=str(data),MIXER_TEST_PG_CTL=tools['pg_ctl'],MIXER_TEST_POSTGRES_LOG=str(output/'postgres.log'))
    run('real-postgres-tests',[tools['go'],'test','-race','-tags=postgres_integration','./release','-run','^TestPostgres','-count=1','-v'],env=env,timeout=180)
    receipt['status']='passed'
    receipt['tests']='real PostgreSQL HTTP multi-instance concurrency, tenant/RBAC/RLS, immutability, unknown schema/runtime-role refusal, bounded query deadline, pre/post publication commit interruption and actual immediate database restart'
    receipt['limitations']=['Private Unix-socket test authentication is limited to this deleted test cluster. No production database credentials were created or altered.',
        'Local config bearer authority remains bootstrap-only; no identity provider, organization onboarding or hosted auth qualification.',
        'Pending outbox records are not dispatched. No backup/restore, multi-zone, CDN, operational, mobile OTA, physical-device or GA evidence.']
except Exception as e:
    receipt['status']='failed';receipt['failure']=str(e);raise
finally:
    if started or (data/'postmaster.pid').exists():
        try: run('stop',[tools['pg_ctl'],'-D',data,'-m','immediate','-w','stop'],timeout=30)
        except Exception as e: receipt['cleanupFailure']=str(e);receipt['status']='failed'
    # Preserve server diagnostics, never retain database/user test state.
    if not (data/'postmaster.pid').exists():
        shutil.rmtree(cluster)
    else:
        receipt['retainedPrivateClusterDirectory']=str(cluster)
    receipt['privateClusterRemoved']=not cluster.exists()
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if receipt['status']!='passed':
    raise SystemExit(1)
print(json.dumps(receipt,indent=2))
