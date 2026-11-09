#!/usr/bin/env python3
"""Fresh finite custody campaign. This supervisor never runs product operations."""
from pathlib import Path
import hashlib, importlib.util, json, os, stat, sys, time
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
BASE=Path('verification/plan-continuation-2026-11-07')
CAND=ROOT/BASE/'source113-sparse-closure-fix-r2'
CONTROL=ROOT/BASE/'native-custody-premise/cleanup_control.py'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
PIN='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(v,m):
    if not v:raise RuntimeError(m)
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def collect(mode):
    lane='source113-sparse-closure-fix-r2' if mode!='baseline' else 'source113-ci-binding-prepare-r1'
    here=OUT/'scratch'/(mode+'-final-inputs')/('checkout-fixed' if mode!='baseline' else 'checkout-baseline')/BASE/lane
    names=[mode+'-result.json',mode+'-postflight-pins.json','sparse-closure-'+mode+'.json','review-tests-result.json'] if mode!='baseline' else ['baseline-counterexample.json','completion-result.json']
    for name in names:
        source=here/name
        if source.is_file():(OUT/(mode+'-ownership.json' if name=='review-tests-result.json' else name)).write_bytes(source.read_bytes())
def main():
    need(not (OUT/'execution.json').exists(),'One-use campaign already started')
    # Filesystem-only shell preflight was persisted before this transport.
    for line in (OUT/'admission-sha256.txt').read_text().splitlines():
        digest,path=line.split(None,1);need(sha(Path(path))==digest,'Prelaunch pin differs '+path)
    need(sha(CONTROL)==PIN and sha(PYTHON)=='e401ac7a95cda75dee34a0cfe1e4faf0a6df1a501cf67887f177fb78cd4eb60a','Controller/python pin')
    for line in (OUT/'admission-identities.txt').read_text().splitlines():
        device,inode,uid,path=line.split(' ',3);p=Path(path);s=p.lstat()
        need((s.st_dev,s.st_ino,s.st_uid)==(int(device),int(inode),int(uid)) and stat.S_ISDIR(s.st_mode),'Directory identity drift')
    epoch=float((OUT/'admission-epoch.txt').read_text());now=time.monotonic()
    remaining=240-(time.time()-epoch);need(0<remaining<=240,'Prelaunch deadline expired')
    active=now+remaining;cleanup=active+60
    plan=[{'label':m,'argv':[str(PYTHON),'-I','-B','-S',*(['-O'] if m=='optimized' else []),str(OUT/'payload.py'),m],'cwd':str(OUT)} for m in ('normal','optimized','baseline')]
    save('launch-plan.json',{'campaign_epoch':epoch,'active_deadline_monotonic':active,'cleanup_deadline_monotonic':cleanup,'maximum_children':3,'planned_children':3,'extra_slot':'None; three commands only, stop on first error.','per_command_seconds':110,'per_command_output':8388608,'aggregate_output':67108864,'argv':plan,'python':str(PYTHON),'python_sha256':sha(PYTHON),'controller_sha256':PIN,'retained_failed_scratch':True,'provider_absence_proven':False})
    spec=importlib.util.spec_from_file_location('unchanged_pinned_custodian',CONTROL);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'scratch/tmp'))
    c=module.Commands(OUT/'commands',env,deadline=cleanup,output_bytes=8388608,total_output_bytes=67108864,cleanup_seconds=60)
    result={'status':'RUNNING','source_revision':'924b155f9d319bb9bbee2b4e082960706edbfb25 plus accepted CLI25 uncommitted','campaign_epoch':epoch,'active_deadline_monotonic':active,'cleanup_deadline_monotonic':cleanup,'controller_sha256':PIN,'managed_children':[],'primary_provider_absence_proven':False}
    save('execution.json',result);error=None
    try:
        for action in plan:
            need(time.monotonic()<active and len(c.records)<3,'Finite admission closed')
            save('next-command.json',action)
            c.run(action['label'],action['argv'],action['cwd'],timeout=min(110,active-time.monotonic()))
            record=c.records[-1];record['descriptors_closed']=all(getattr(c.owned[-1]['process'],n).closed for n in ('stdout','stderr'));c.flush()
            collect(action['label']);result['managed_children'].append(record);save('execution.json',result)
        need((OUT/'completion-result.json').is_file(),'No combined review outcome')
    except BaseException as e:error=repr(e)
    if error or c.hold or c.limit:
        # Never call cleanup on failure. UNKNOWN closes every further operation.
        clean={'allTerminalCustody':not c.hold and all(r['terminal_custody'] for r in c.records),'scratchRemoved':False,'scratchRetained':True,'aggregateBytes':c.used_output}
        if c.hold:save('HOLD.json',{'status':'UNKNOWN','hold':c.hold,'retained_scratch':str(OUT/'scratch'),'no_further_process_operations':True})
    else:clean=c.cleanup(OUT/'scratch')
    passed=not error and not c.hold and not c.limit and clean['allTerminalCustody'] and clean['scratchRemoved']
    result.update(status='PASS_EXACT_SOURCE_REVIEW' if passed else 'FAILED',error=error,commands=c.records,cleanup=clean,hold=c.hold,limit=c.limit,elapsed_since_admission=time.time()-epoch)
    save('execution.json',result)
    print(json.dumps({k:result[k] for k in ('status','error','cleanup','hold','limit','elapsed_since_admission')}),flush=True)
    return 0 if passed else 1
if __name__=='__main__':sys.exit(main())
