from pathlib import Path
import hashlib,importlib.util,json,os,sys,time
OUT=Path(__file__).resolve().parent
P=json.loads((OUT/'prelaunch.json').read_text())
def need(v,m):
 if not v:raise RuntimeError(m)
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
need(not (OUT/'receipt.json').exists(),'one use')
for r in P['pins']:need(sha(r['path'])==r['sha256'] and Path(r['path']).stat().st_size==r['bytes'],'pin '+r['path'])
need(sha(P['custodian'])=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df','custodian')
start=float((OUT/'epoch.txt').read_text());left=120-(time.time()-start);need(0<left<=120,'deadline')
active=time.monotonic()+left;cleanup=active+30
save('launch-plan.json',dict(P,activeDeadline=active,cleanupDeadline=cleanup,version=sys.version))
s=importlib.util.spec_from_file_location('pinned_custodian',P['custodian']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=m.Commands(OUT/'commands',dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'scratch/tmp')),deadline=cleanup,output_bytes=8388608,total_output_bytes=67108864,cleanup_seconds=30)
r={'status':'RUNNING','sourceDigest':P['sourceDigest'],'primaryProviderAbsenceProven':False};save('receipt.json',r);error=None
try:
 for a in P['actions']:
  need(len(c.records)<4 and time.monotonic()<active,'closed')
  save('next-command.json',a)
  c.run(a['label'],a['argv'],a['cwd'],timeout=min(25,active-time.monotonic()))
  c.records[-1]['descriptors_closed']=all(getattr(c.owned[-1]['process'],n).closed for n in ('stdout','stderr'));c.flush()
 for pin in P['pins']:need(sha(pin['path'])==pin['sha256'],'postflight '+pin['path'])
except BaseException as e:error=repr(e)
if error or c.hold or c.limit:clean={'allTerminalCustody':not c.hold and all(x['terminal_custody'] for x in c.records),'scratchRetained':True}
else:clean=c.cleanup(OUT/'scratch')
r.update(status='PASSED_INSTALLED_SOURCE113_BINDINGS' if not error and not c.hold and not c.limit and clean.get('scratchRemoved') else 'FAILED',error=error,commands=c.records,hold=c.hold,limit=c.limit,cleanup=clean,elapsedSeconds=time.time()-start)
save('receipt.json',r)
if c.hold:save('HOLD.json',{'hold':c.hold,'scratch':str(OUT/'scratch'),'noFurtherOperations':True})
print(json.dumps({k:r[k] for k in ('status','error','hold','limit','cleanup','elapsedSeconds')}),flush=True)
sys.exit(0 if r['status']=='PASSED_INSTALLED_SOURCE113_BINDINGS' else 1)
