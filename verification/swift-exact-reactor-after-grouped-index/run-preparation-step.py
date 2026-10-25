#!/usr/bin/env python3
"""Record one existing finite preparation step; this launcher cannot select a target."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''): h.update(part)
    return h.hexdigest()
def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('step', choices=('prepare','build','control-001','control-002','host-controls','proposal'))
step = parser.parse_args().step
action = {'control-001':'control','control-002':'control','proposal':'propose'}.get(step,step)
stem = HERE / step
assert not stem.with_suffix('.stdout').exists(), 'preserve every preparation attempt'
assert not stem.with_suffix('.stderr').exists()
directory = HERE / 'outer-preparation-commands' / step
assert not directory.exists()
directory.mkdir(parents=True)
spec = importlib.util.spec_from_file_location('fresh_preparation_driver', HERE / 'diagnostic.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
argv = [sys.executable, '-B', str((HERE / 'diagnostic.py').relative_to(ROOT)), action]
initial_commands = set((HERE / 'commands').glob('*/started.json')) if (HERE/'commands').exists() else set()
record = {'schema':1,'argv':argv,'cwd':str(ROOT),'scope':'preparation only; target not permitted by launcher',
          'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python':driver.identity(sys.executable),'pythonVersion':sys.version,
          'driverSHA256':sha(HERE/'diagnostic.py'),'launcherSHA256':sha(__file__),
          'timeoutSeconds':240,'started':False,'timedOut':False,'signalsSent':[]}
started = time.monotonic()
with stem.with_suffix('.stdout').open('xb') as out, stem.with_suffix('.stderr').open('xb') as err:
    child = subprocess.Popen(argv,cwd=ROOT,stdout=out,stderr=err,start_new_session=True)
    record.update(pid=child.pid,processGroup=child.pid,started=True)
    save(directory/'started.json',record)
    try: child.wait(timeout=240)
    except subprocess.TimeoutExpired: record['timedOut']=True
    observation = driver.observe_group(child.pid)
    record['groupBeforeCleanup'] = observation
    if record['timedOut'] or child.returncode != 0 or observation['state']!='absent':
        save(directory/'before-process-cleanup.json',record | {'exitCode':child.returncode,
             'stdout':driver.identity(stem.with_suffix('.stdout')),'stderr':driver.identity(stem.with_suffix('.stderr')),
             'failureEvidencePrecedesCleanup':True})
        groups = {child.pid}
        for path in set((HERE/'commands').glob('*/started.json')) - initial_commands:
            groups.add(json.loads(path.read_bytes())['processGroup'])
        for pgid in sorted(groups):
            if driver.observe_group(pgid)['state']=='absent': continue
            for sig in (signal.SIGTERM,signal.SIGKILL):
                try:
                    os.killpg(pgid,sig)
                    record['signalsSent'].append({'processGroup':pgid,'signal':sig.name})
                except ProcessLookupError: break
                end = time.monotonic()+5
                while time.monotonic()<end:
                    child.poll()
                    if driver.observe_group(pgid,end)['state']=='absent': break
                    time.sleep(0.05)
                if driver.observe_group(pgid,end)['state']=='absent': break
        child.poll()
record.update(exitCode=child.returncode,durationSeconds=time.monotonic()-started,
    finalGroupObservation=driver.observe_group(child.pid),
    stdout=driver.identity(stem.with_suffix('.stdout')),stderr=driver.identity(stem.with_suffix('.stderr')))
record['rawStreamEOFConfirmed'] = record['finalGroupObservation']['state']=='absent'
record['rawStreamEOFScope'] = 'regular handles closed; complete hash reads reached EOF after exact outer PGID absence'
record['passed'] = record['exitCode']==0 and not record['timedOut'] and record['rawStreamEOFConfirmed'] and not record['signalsSent']
save(directory/'receipt.json',record)
print(json.dumps({'step':step,'passed':record['passed'],'pid':record['pid'],'processGroup':record['processGroup'],
                  'exitCode':record['exitCode'],'targetAttempted':False,'receipt':str(directory/'receipt.json')}))
sys.exit(0 if record['passed'] else 1)
