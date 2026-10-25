#!/usr/bin/env python3
"""Run the root-authorized existing cleanup once; never starts any target."""
import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('existing_cleanup_driver',HERE/'diagnostic.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
def save(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert not (HERE/'cleanup-attempt-started.json').exists() and not (HERE/'cleanup.json').exists()
audit=driver.read(HERE/'pre-cleanup-audit.json')
assert audit['allOwnedGroupsAbsent'] and audit['consumingCleanupCurrentReservationsLiveAndTicketsZero']
for row in audit['holderChecks']:
    path=Path(row['pathIdentity']['path']);stat=path.stat()
    assert (stat.st_dev,stat.st_ino)==(row['pathIdentity']['device'],row['pathIdentity']['inode'])
argv=[sys.executable,'-B',str((HERE/'diagnostic.py').relative_to(ROOT)),'cleanup']
record={'schema':1,'argv':argv,'cwd':str(ROOT),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':driver.identity(sys.executable),'pythonVersion':sys.version,'driverSHA256':driver.sha(HERE/'diagnostic.py'),'preCleanupAuditSHA256':driver.sha(HERE/'pre-cleanup-audit.json'),'scope':'existing owned cleanup only; no guest native or target execution','timeoutSeconds':90,'started':False,'timedOut':False,'signalsSent':[]}
start=time.monotonic()
with (HERE/'cleanup.stdout').open('xb') as out,(HERE/'cleanup.stderr').open('xb') as err:
    child=subprocess.Popen(argv,cwd=ROOT,stdout=out,stderr=err,start_new_session=True)
    record.update(pid=child.pid,processGroup=child.pid,started=True)
    save('cleanup-attempt-started.json',record)
    try:child.wait(timeout=90)
    except subprocess.TimeoutExpired:record['timedOut']=True
record.update(exitCode=child.returncode,durationSeconds=time.monotonic()-start,stdout=driver.identity(HERE/'cleanup.stdout'),stderr=driver.identity(HERE/'cleanup.stderr'),finalGroupObservation=driver.observe_group(child.pid))
record['rawStreamEOFConfirmed']=record['finalGroupObservation']['state']=='absent'
record['rawStreamEOFScope']='regular output handles closed; complete hash reads reached EOF after exact cleanup PGID absence'
record['passed']=record['exitCode']==0 and not record['timedOut'] and record['rawStreamEOFConfirmed']
save('cleanup-command.json',record)
print(json.dumps({'cleanupCommandPassed':record['passed'],'pid':child.pid,'processGroup':child.pid,'scratchRemoved':not (HERE/'owned-scratch').exists(),'binaryRetainedGzip':(HERE/'bin/exact-tests.gz').exists(),'targetAttempts':1,'targetRerun':False}))
sys.exit(0 if record['passed'] else 1)
