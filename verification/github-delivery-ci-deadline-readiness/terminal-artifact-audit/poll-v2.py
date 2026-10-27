"""One fresh exact-run read-only snapshot; no phases, retries or CI mutations."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RUN = 40447941540
SHA = '606c42876855897c315ee279dcd38fabaeb561ad'
TREE = '6e7ef189ea796effb2099eff927436bd407a080b'
EXPECTED = {'swift','swift-capability-native','vm','services','android-owner-host','swift-cache-state-fixture'}
assert __debug__ and len(sys.argv) == 2 and sys.argv[1].isdigit()
index = int(sys.argv[1])
assert index > 0 and not (ROOT/'seal.json').exists()

def digest(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

release_raw = (ROOT.parent/'terminal-audit-script-release.json').read_bytes()
assert digest(release_raw)['sha256'] == '19f99be234f71440a0233df19e799ce2f25003383e845cb62c4d4a0744c83349'
release = json.loads(release_raw)
assert release['source_revision'] == SHA and release['source_tree'] == TREE and release['run_id'] == RUN
assert release['status'] == 'exact-scripts-released-conditional-on-terminal-six-jobs-64-steps-pass'
assert digest((ROOT/'preparation.json').read_bytes()) == release['preparation']
for row in release['execution_scripts']:
    assert digest((ROOT/row['path']).read_bytes()) == row['digest']
if index == 1:
    assert not (ROOT/'root-script-release.json').exists()
    (ROOT/'root-script-release.json').write_bytes(release_raw)
    previous = json.loads((ROOT.parent/'ci-jobs-5.command.json').read_bytes())['at']
else:
    prior = ROOT/f'poll-{index-1}-summary.json'
    if not prior.exists():
        assert index == 2
        prior = ROOT/'poll-1-evaluation.json'
    previous = json.loads(prior.read_bytes())['started_utc']
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
assert (datetime.datetime.fromisoformat(started)-datetime.datetime.fromisoformat(previous)).total_seconds() >= 60
assert not (ROOT/f'poll-{index}-summary.json').exists()

def group_exists(group):
    try:os.killpg(group,0)
    except ProcessLookupError:return False
    return True

def capture(label,endpoint):
    name=f'poll-{index}-{label}'
    assert not (ROOT/(name+'.command.json')).exists()
    argv=['gh','api',endpoint]
    at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick=time.monotonic()
    child=subprocess.Popen(argv,cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed_out=False;signals=[]
    try:out,err=child.communicate(timeout=25)
    except subprocess.TimeoutExpired:
        timed_out=True
        try:os.killpg(child.pid,signal.SIGKILL);signals.append('SIGKILL owned poll group after timeout')
        except ProcessLookupError:pass
        out,err=child.communicate(timeout=5)
    reaped=child.poll() is not None
    absent=not group_exists(child.pid)
    if not absent:
        try:os.killpg(child.pid,signal.SIGKILL);signals.append('SIGKILL remaining owned poll group')
        except ProcessLookupError:pass
        deadline=time.monotonic()+5
        while group_exists(child.pid) and time.monotonic()<deadline:time.sleep(.02)
        absent=not group_exists(child.pid)
    (ROOT/(name+'.stdout')).write_bytes(out);(ROOT/(name+'.stderr')).write_bytes(err)
    save(ROOT/(name+'.command.json'),{'started_utc':at,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(REPO),'exit_code':child.returncode,'timed_out':timed_out,'elapsed_seconds':time.monotonic()-tick,'child_timeout_seconds':25,'direct_child_pid':child.pid,'owned_process_group':child.pid,'direct_child_reaped':reaped,'owned_process_group_absent_after_reaping':absent,'cleanup_signals':signals,'stdout_file':name+'.stdout','stdout':digest(out),'stderr':digest(err),'source_revision':SHA,'source_tree':TREE,'python':sys.version,'poller':digest(Path(__file__).read_bytes()),'scope':'Fresh read-only exact-run CI status; scoped owned-group cleanup only; no phase, retry, process inventory or mutation'})
    assert child.returncode==0 and not timed_out and reaped and absent
    return json.loads(out)

run=capture('run',f'repos/snowdamiz/mixer/actions/runs/{RUN}')
jobs=capture('jobs',f'repos/snowdamiz/mixer/actions/runs/{RUN}/jobs?per_page=100')
assert run['id']==RUN and run['head_sha']==SHA and run['run_attempt']==1
assert run['event']=='push' and run['head_branch']=='main' and run['head_repository']['full_name']=='snowdamiz/mixer'
assert jobs['total_count']==len(jobs['jobs'])==6 and {j['name']for j in jobs['jobs']}==EXPECTED
assert all(j['head_sha']==SHA and j['run_attempt']==1 for j in jobs['jobs'])
steps=sum(len(j['steps'])for j in jobs['jobs'])
assert 0 < steps <= 64
terminal_failure=(run['status']=='completed' and run['conclusion']!='success') or any(j['status']=='completed' and j['conclusion']!='success'for j in jobs['jobs'])
passed=run['status']=='completed' and run['conclusion']=='success' and steps==64 and all(j['status']=='completed' and j['conclusion']=='success' and all(s['status']=='completed' and s['conclusion']=='success'for s in j['steps'])for j in jobs['jobs'])
summary={'started_utc':started,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':SHA,'source_tree':TREE,'run_id':RUN,'run_attempt':1,'run_status':run['status'],'run_conclusion':run['conclusion'],'all_six_jobs_and_64_steps_pass':passed,'terminal_failure':terminal_failure,'successful_jobs':sum(j['status']=='completed' and j['conclusion']=='success'for j in jobs['jobs']),'steps':steps,'jobs':[{'name':j['name'],'id':j['id'],'status':j['status'],'conclusion':j['conclusion'],'steps':len(j['steps'])}for j in jobs['jobs']],'release_sha256':digest(release_raw)['sha256'],'no_CI_retry_or_mutation':True}
save(ROOT/f'poll-{index}-summary.json',summary)
print(json.dumps(summary))
if terminal_failure:raise SystemExit(2)
