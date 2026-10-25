#!/usr/bin/env python3
"""Seal or read-only verify independent report and inputs; no selected imports."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REPORT = ROOT / 'docs/apple-passive-runtime-review.md'
EXCLUDED = {'handoff.json','handoff.sha256'}
def stable(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def ensure(value, message):
    if not value: raise ValueError(message)
def row(path):
    ensure(not any(s in str(path).lower() for s in ['catalog-inspector','authority-driver','worker-transport']), 'Excluded lane')
    info=path.lstat()
    ensure(path.resolve()==path and stat.S_ISREG(info.st_mode) and info.st_nlink==1,'Canonical single-link regular file required')
    raw=path.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}
def inventory():
    result={str(REPORT.relative_to(ROOT)):row(REPORT)}
    for path in sorted(BASE.rglob('*')):
        ensure(not any(part.startswith('review-owned-') for part in path.parts), 'Owned review scratch remains')
        if path.is_relative_to(BASE/'commands/seal') or path.is_relative_to(BASE/'commands/verify'): continue
        if path.is_file() and str(path.relative_to(BASE)) not in EXCLUDED:
            result[str(path.relative_to(ROOT))]=row(path)
    return result
def verify_inputs():
    bindings=json.loads((BASE/'input-bindings.json').read_bytes())
    ensure(len(bindings)==263,'Input inventory count differs')
    for name,expected in bindings.items(): ensure(row(ROOT/name)==expected,'Accepted input changed: '+name)
    result=json.loads((BASE/'result.json').read_bytes())
    ensure(result['status']=='source-and-host-runtime-preparation-accepted' and result['blockingFindings']==[]
           and result['independentMethodsRun']==9 and [result[k] for k in ['failures','errors','skipped']]==[0,0,0]
           and result['ownedScratchAbsent'] is True and result['inputsUnchanged'] is True,
           'Successful bounded review required')
    command=json.loads((BASE/'commands/controls/receipt.json').read_bytes())
    ensure(command['exitCode']==0 and command['timedOut'] is False and command['ownedProcessGroup']['state']=='absent',
           'Terminal host command required')
    ensure(result['reviewScriptSHA256']==row(BASE/'review.py')['sha256']==command['sourceSHA256'], 'Executed review source differs')
    for stream,expected in command['streams'].items():
        observed=row(BASE/'commands/controls'/ (stream+'.log'))
        ensure(observed['bytes']==expected['bytes'] and observed['sha256']==expected['sha256']
               and expected['eof'] is True and expected['readerFailed'] is False,'Command stream differs')
    return result

action=sys.argv[1]
ensure(action in {'seal','verify'},'Bound action required')
result=verify_inputs();path=BASE/'handoff.json'
if action=='seal':
    ensure(not path.exists(),'Preserve first handoff')
    members=inventory()
    value={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status':result['status'],'packetSHA256':result['packetSHA256'],
           'producerHandoffSHA256':result['producerHandoffSHA256'],'members':members,
           'memberTreeSHA256':sha(stable(members)),'independentHostMethods':9,'blockingFindings':[],
           'nativeExecuted':False,'nativeSelected':False,'futureRuntimeOriginalsSelected':False,
           'futureSupplementalJoinSelected':False,'physicalPhones':'disconnected-deferred','gaAccepted':False}
    path.write_bytes(stable(value));(BASE/'handoff.sha256').write_text(sha(path.read_bytes())+'  handoff.json\n')
else:
    value=json.loads(path.read_bytes())
    ensure(sha(stable(value['members']))==value['memberTreeSHA256'] and inventory()==value['members'],'Sealed inventory differs')
    ensure(value['packetSHA256']==result['packetSHA256'] and value['status']==result['status'],'Sealed decision differs')
print(json.dumps({'handoffSHA256':sha(path.read_bytes()),'members':len(value['members']),
                  'verifiedInputFiles':263,'status':value['status'],'nativeExecuted':False},sort_keys=True))
