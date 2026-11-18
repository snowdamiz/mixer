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
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
output = a.output.absolute(); output.mkdir(parents=True, exist_ok=False)
commands = []
receipt = {'schema':1, 'status':'running', 'scope':'real isolated local PostgreSQL transactional/RLS and release backup/restore tests; no hosted/GA claim', 'commands':commands, 'mockDatabase':False}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def require_group_gone(pgid):
    deadline = time.monotonic() + 2
    while True:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f'process group {pgid} is still present')
        time.sleep(0.05)

def run(name,args,env=None,timeout=180):
    args=[str(x) for x in args]; start=time.monotonic()
    item={'name':name,'command':args,'exitCode':None,'custody':'unproven','executableSHA256':digest(args[0])}; commands.append(item)
    try:
        with (output/(name+'.stdout')).open('xb') as out, (output/(name+'.stderr')).open('xb') as err:
            worker = subprocess.Popen(args, cwd=ROOT, env=env, stdout=out, stderr=err, start_new_session=True)
            item['processGroup'] = worker.pid
            item['exitCode'] = worker.wait(timeout=timeout)
        if item['exitCode'] < 0:
            raise RuntimeError(f"{name} was terminated by signal {-item['exitCode']}")
        require_group_gone(worker.pid)
        item['custody'] = 'terminal'
        if item['exitCode']:
            raise RuntimeError(name+' failed; see captured logs')
    except subprocess.TimeoutExpired:
        item['timedOut']=True;raise
    finally:
        item['elapsedSeconds']=round(time.monotonic()-start,3)
        if item['custody'] == 'terminal':
            for stream in ['stdout','stderr']:
                path=output/(name+'.'+stream)
                item[stream]={'path':path.name,'bytes':path.stat().st_size,'sha256':digest(path)}
    return (output/(name+'.stdout')).read_text()

def interrupted(signum, _frame):
    raise SystemExit(128 + signum)

def stop_cluster():
    pidfile = data/'postmaster.pid'
    pid = int(pidfile.read_text().splitlines()[0])
    receipt['postmasterProcessGroup'] = pid
    if pid <= 1 or os.getpgid(pid) != pid:
        raise RuntimeError('could not confirm the private postmaster process group')
    run('stop',[tools['pg_ctl'],'-D',data,'-m','immediate','-w','stop'],env=env,timeout=30)
    require_group_gone(pid)
    receipt['postmasterGroupGone'] = True
    if pidfile.exists() or any(sockets.iterdir()):
        raise RuntimeError('private PostgreSQL PID file or socket remains after stop')
    receipt['privateSocketDirectoryEmpty'] = True

tools = {}
for tool in ['initdb','pg_ctl','postgres','psql','pg_dump','pg_restore','go']:
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
env={k:v for k,v in os.environ.items() if not k.startswith(('PG','DYLD_','LD_','MIXER_TEST_'))}
signal.signal(signal.SIGTERM, interrupted)
started = False
try:
    receipt['postgresVersion']=run('postgres-version',[tools['postgres'],'--version']).strip()
    receipt['psqlVersion']=run('psql-version',[tools['psql'],'--version']).strip()
    for tool in ['pg_dump','pg_restore']:
        receipt['tools'][tool]['version']=run(tool+'-version',[tools[tool],'--version']).strip()
    receipt['goVersion']=run('go-version',[tools['go'],'version']).strip()
    selected_go=Path(run('go-root',[tools['go'],'env','GOROOT']).strip())/'bin/go'
    receipt['selectedGoToolchain']={'path':str(selected_go),'sha256':digest(selected_go)}
    run('initialize',[tools['initdb'],'-D',data,'-U','mixer_migration_owner','--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8'],env=env)
    run('start',[tools['pg_ctl'],'-D',data,'-l',output/'postgres.log','-o',f"-k {sockets} -c port=5432 -c listen_addresses='' -c fsync=on -c full_page_writes=on",'-w','start'],env=env)
    started=True
    env.update(MIXER_TEST_POSTGRES_OWNER=f'host={sockets} port=5432 dbname=postgres user=mixer_migration_owner sslmode=disable',
               MIXER_TEST_POSTGRES_DATA_DIRECTORY=str(data),MIXER_TEST_PG_CTL=tools['pg_ctl'],MIXER_TEST_POSTGRES_LOG=str(output/'postgres.log'),
               MIXER_TEST_PG_DUMP=tools['pg_dump'],MIXER_TEST_PG_RESTORE=tools['pg_restore'])
    run('real-postgres-tests',[tools['go'],'test','-race','-tags=postgres_integration','./release','-run','^TestPostgres','-count=1','-v'],env=env,timeout=180)
    receipt['status']='passed'
    receipt['tests']='real PostgreSQL HTTP multi-instance concurrency, tenant/RBAC/RLS, immutability, unknown schema/runtime-role refusal, bounded query deadline, pre/post publication commit interruption, actual immediate database restart, and signed release backup/restore into a fresh database'
    receipt['limitations']=['Private Unix-socket test authentication is limited to this test cluster.',
        'Local config bearer authority remains bootstrap-only; no identity provider, organization onboarding or hosted auth qualification.',
        'Backup/restore used two fresh databases in the same disposable cluster with existing cluster-level roles and test service configuration. A single small fixture establishes local correctness, not operational RPO/RTO.',
        'Pending outbox records are not dispatched. No multi-zone, CDN, operational, mobile OTA, physical-device or GA evidence.']
except BaseException as e:
    receipt['status'] = 'failed'
    receipt['failure'] = f'{type(e).__name__}: {e}'
    last = commands[-1] if commands else {}
    # A failed cluster command can have detached PostgreSQL workers even after
    # its own group exits. Preserve all state when that custody is unresolved.
    if (not isinstance(e, Exception) or last.get('custody') == 'unproven'
            or last.get('name') in ('initialize', 'start', 'real-postgres-tests')):
        receipt['retentionReason'] = 'cluster command failed or was interrupted before cleanup was proven safe'
    raise
finally:
    receipt['privateClusterRemoved'] = False
    try:
        if 'retentionReason' not in receipt:
            if started:
                stop_cluster()
            shutil.rmtree(cluster)
            receipt['privateClusterRemoved'] = True
    except BaseException as e:
        receipt['status'] = 'failed'
        receipt['cleanupFailure'] = f'{type(e).__name__}: {e}'
        receipt['retentionReason'] = 'cluster shutdown or cleanup was not confirmed'
        if not isinstance(e, Exception):
            raise
    finally:
        if not receipt['privateClusterRemoved']:
            receipt['retainedPrivateClusterDirectory'] = str(cluster)
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if receipt['status']!='passed':
    raise SystemExit(1)
print(json.dumps(receipt,indent=2))
