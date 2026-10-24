"""Finite read-only diagnostic capture on the still-owned emulator before cleanup."""
import hashlib
from pathlib import Path

LIMIT=1048576

def capture(execute,identity,process,adb,package,out,receipt,root):
    record={'scope':'owned emulator crash/main/system tail plus private fixture diagnostic only; no product cause inferred','captures':[],'maximumRetainedBytes':2*LIMIT+131072+8192,'beforeEmulatorCleanup':True}
    receipt['diagnostics']=record
    def run(name,argv,maximum):
        entry={'name':name,'argv':list(map(str,argv)),'maximumRetainedBytes':maximum}
        record['captures'].append(entry)
        try:
            result=execute(entry['argv'],cwd=root,timeout=15)
            # Retain tail for crash chronology, with explicit truncation metadata.
            retained=result.stdout[-maximum:];path=out/(name+'.log')
            with path.open('xb') as stream:stream.write(retained)
            entry.update({'exitCode':result.returncode,'output':path.name,'bytes':len(retained),'sha256':hashlib.sha256(retained).hexdigest(),'observedBytes':len(result.stdout),'truncated':len(result.stdout)>maximum,'ownedCommandGroupCleanup':result.groupCleanup})
            return result.returncode,retained
        except BaseException as failure:
            entry['failure']=repr(failure);return -1,b''
    if process is None or process.poll() is not None:
        record['status']='owned emulator already exited; only existing emulator.log available';return
    code,owned=run('diagnostic-owned-process',['ps','-p',str(process.pid),'-o','pid=,pgid=,command='],8192)
    if code or not identity(owned.decode(errors='replace').strip(),process.pid):
        record['status']='refused: exact owned process identity unavailable';return
    for name,arguments,maximum in (
        ('diagnostic-owned-crash-buffer',['logcat','-b','crash','-d','-v','threadtime','-t','128'],LIMIT),
        ('diagnostic-owned-logcat-tail',['logcat','-b','main','-b','system','-b','crash','-d','-v','threadtime','-t','384'],LIMIT),
        ('diagnostic-private-fixture',['exec-out','run-as',package,'cat','files/toggle-supplement-diagnostics.txt'],131072),
    ):
        run(name,adb+arguments if arguments[0]=='exec-out' else adb+['shell']+arguments,maximum)
    record['status']='finite captures attempted independently before owned cleanup'

def bind_fixture(record,instrument):
    import re
    declared=re.findall(rb'INSTRUMENTATION_RESULT: diagnosticSHA256=([0-9a-f]{64})',instrument)
    matches=[row for row in record['captures'] if row['name']=='diagnostic-private-fixture']
    verified=(len(matches)==1 and matches[0].get('exitCode')==0 and not matches[0].get('truncated',True) and declared==[matches[0]['sha256'].encode()])
    record['fixtureDiagnosticBindingVerified']=verified
    record['fixtureDiagnosticBindingScope']='SHA256 declared by private instrumentation and rehashed after finite run-as export'
    return verified
