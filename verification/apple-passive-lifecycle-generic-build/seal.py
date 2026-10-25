#!/usr/bin/env python3
"""Seal this lane only after the read-only evidence audit succeeds."""
import datetime
import sys
from common import *
from verify import audit, inventory, REPORT

def main():
    assert not (BASE/'handoff.json').exists() and not (BASE/'handoff.sha256').exists()
    result = audit()
    (BASE/'seal-receipt.json').write_bytes(canonical({'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(BASE/'seal.py')],'cwd':str(ROOT),'python':sys.version,'verifier':binding(BASE/'verify.py'),'common':binding(BASE/'common.py'),'report':binding(REPORT),'readOnlyPreSealAudit':result,'nativeExecuted':False,'runtimeSelected':False,'gaAccepted':False}))
    members=inventory()
    h={'schema':1,'scope':'Passive lifecycle observer exact sources and one fresh generic iOS Simulator app/runner build attempt only','sourceRevisionReportedByRoot':REVISION,'rootSelectionSHA256':binding(ROOT/SELECTION)['sha256'],'selectedSourceArchiveSHA256':PINS[SOURCE],'members':members,'memberTreeSHA256':sha(canonical(members)),'audit':result,'nativeExecuted':False,'nativeAccepted':False,'runtimeSelected':False,'futureRuntimeIngestionAccepted':False,'originalOraclePassed':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    raw=canonical(h)
    (BASE/'handoff.json').write_bytes(raw)
    (BASE/'handoff.sha256').write_text(sha(raw)+'  handoff.json\n')
    print(json.dumps({'handoffSHA256':sha(raw),'sealedMembers':len(members),**result},indent=2,sort_keys=True))

if __name__ == '__main__': main()
