#!/usr/bin/env python3
"""Run the root-authorized original cleanup once inside a bounded owned group."""
import datetime
import importlib.util
import json
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('existing_cleanup_driver',HERE/'diagnostic.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
def save(name,value):driver.save(name,value)
assert not (HERE/'cleanup-attempt-started.json').exists() and not (HERE/'cleanup.json').exists()
audit=driver.read(HERE/'pre-cleanup-audit.json')
assert audit['allOwnedGroupsAbsent'] and audit['consumingCleanupCurrentReservationsLiveAndTicketsZero']
assert audit['resultInputsArchivedBeforeCleanup']
assert driver.sha(HERE/'result-inputs/manifest.json')==audit['resultInputsManifestSHA256']
for row in audit['holderChecks']:
    path=Path(row['pathIdentity']['path']);stat=path.stat()
    assert not path.is_symlink()
    assert (stat.st_dev,stat.st_ino)==(row['pathIdentity']['device'],row['pathIdentity']['inode'])
for row in audit['ownedGroupObservations']:
    assert driver.observe_group(row['processGroup'])['state']=='absent'
assert driver.sha(HERE/'diagnostic.py')==driver.read(HERE/'root-selection.json')['driverSHA256']
argv=[sys.executable,'-B',str((HERE/'diagnostic.py').relative_to(ROOT)),'cleanup']
record={'schema':1,'argv':argv,'cwd':str(ROOT),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'python':driver.identity(sys.executable),'pythonVersion':sys.version,'driverSHA256':driver.sha(HERE/'diagnostic.py'),
    'launcherSHA256':driver.sha(__file__),'preCleanupAuditSHA256':driver.sha(HERE/'pre-cleanup-audit.json'),
    'scope':'existing owned cleanup only; no guest native target compile or other-project operation',
    'timeoutSeconds':90,'terminationGraceSeconds':5,'killWaitSeconds':5,'started':False,'timedOut':False,'signalsSent':[]}
start=time.monotonic()
with (HERE/'cleanup.stdout').open('xb') as out,(HERE/'cleanup.stderr').open('xb') as err:
    child=subprocess.Popen(argv,cwd=ROOT,stdout=out,stderr=err,start_new_session=True)
    record.update(pid=child.pid,processGroup=child.pid,started=True)
    save('cleanup-attempt-started.json',record)
    try:child.wait(timeout=90)
    except subprocess.TimeoutExpired:record['timedOut']=True
    observation=driver.observe_group(child.pid)
    record['groupBeforeCleanup']=observation
    if record['timedOut'] or child.returncode!=0 or observation['state']!='absent':
        save('cleanup-before-process-cleanup.json',record|{'exitCode':child.returncode,
            'stdout':driver.identity(HERE/'cleanup.stdout'),'stderr':driver.identity(HERE/'cleanup.stderr'),
            'failureEvidencePrecedesSignals':True})
    deadlines=[time.monotonic()+5,time.monotonic()+10]
    record['cleanupObservations']=[]
    if observation['state']!='absent':
        for sig,deadline in zip((signal.SIGTERM,signal.SIGKILL),deadlines):
            try:
                os.killpg(child.pid,sig);record['signalsSent'].append(sig.name)
            except ProcessLookupError:break
            except OSError as error:record['cleanupObservations'].append({'error':str(error),'errno':error.errno})
            while time.monotonic()<deadline:
                child.poll()
                if driver.observe_group(child.pid,deadline)['state']=='absent':break
                time.sleep(min(0.05,max(0,deadline-time.monotonic())))
            observation=driver.observe_group(child.pid,deadline)
            record['cleanupObservations'].append(observation)
            if observation['state']=='absent':break
        child.poll()
record.update(exitCode=child.returncode,durationSeconds=time.monotonic()-start,
    stdout=driver.identity(HERE/'cleanup.stdout'),stderr=driver.identity(HERE/'cleanup.stderr'),
    finalGroupObservation=driver.observe_group(child.pid))
record['rawStreamEOFConfirmed']=record['finalGroupObservation']['state']=='absent'
record['rawStreamEOFScope']='regular output handles closed; complete hash reads reached EOF after exact cleanup PGID absence'
record['passed']=record['exitCode']==0 and not record['timedOut'] and record['rawStreamEOFConfirmed'] and not record['signalsSent']
save('cleanup-command.json',record)
print(json.dumps({'cleanupCommandPassed':record['passed'],'pid':child.pid,'processGroup':child.pid,
    'scratchRemoved':not (HERE/'owned-scratch').exists(),'binaryRetainedGzip':(HERE/'bin/exact-tests.gz').exists(),
    'targetAttempts':1,'targetRerun':False}))
sys.exit(0 if record['passed'] else 1)
