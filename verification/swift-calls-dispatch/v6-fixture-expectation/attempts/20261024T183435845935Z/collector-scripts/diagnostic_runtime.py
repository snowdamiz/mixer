"""Fixture development only. Accounting pending: no acceptance credit."""
import collect as c
code,attempt,out,err=c.run(['cargo','test','--lib','--no-run','--offline','--locked','--features','experimental-swift-reactor','--message-format=json-render-diagnostics'],label='UNQUALIFIED-diagnostic-swift-debug',post={'target':'mixer_vm','prefixes':['swift_dispatch_cd'+str(i).zfill(2)+'_' for i in range(1,25)],'args':['swift_dispatch_','--nocapture','--test-threads=1']})
c.save(c.HERE/'diagnostic-runtime-last.json',{'attempt':str(attempt.relative_to(c.HERE)),'exitCode':code,'accountingAccepted':False,'runtimeAccepted':False,'purpose':'Unqualified isolated fixture development only'})
raise SystemExit(code)
