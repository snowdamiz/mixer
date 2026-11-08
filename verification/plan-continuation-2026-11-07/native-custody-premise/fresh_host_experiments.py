"""Two conditional single-child discriminants; stop the campaign on any unknown."""
import hashlib, json, os, signal, sys, time
from pathlib import Path
import cleanup_control as c
OUT=Path(__file__).resolve().parent
HELD={40708,40709,40711,23663,20745,20770,20780,20817,20842,20851,20866,2424,2621,40802230894}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main():
    control=json.loads((OUT/'host-controls-optimized.json').read_text())
    if not(control['status']=='passed' and control['tests']==26 and control['lifecycleSHA256']==sha(OUT/'cleanup_control.py') and control['controllerSHA256']==sha(OUT/'run_native_probe.py')):raise RuntimeError('fake admission failed')
    target=OUT/'fresh-host-experiments.json'
    if target.exists():raise RuntimeError('no repeats')
    receipt={'status':'running','command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'hostUname':list(os.uname()),'controllerSHA256':sha(OUT/'run_native_probe.py'),'lifecycleSHA256':sha(OUT/'cleanup_control.py'),'driverSHA256':sha(__file__),'sourceRevision':'96f03ab65966a6374e958e780fa09a3eed814c0b','source101':'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca','experiments':[],'nativeAttempts':0,'heldGroupOperations':0}
    save(target,receipt)
    cases=[('natural-exit',"import os,time;os.close(1);time.sleep(.04);os.write(2,b'err')"),('live-termination',"import os,time;os.write(1,b'ready');time.sleep(2)")]
    for name,source in cases:
        logs=OUT/('fresh-'+name);logs.mkdir(exist_ok=False)
        scratch=logs/'scratch';scratch.mkdir()
        start=time.monotonic();manager=c.Commands(logs,dict(os.environ),deadline=start+4.5,cleanup_seconds=1,output_bytes=4*c.MIB,total_output_bytes=32*c.MIB)
        experiment={'name':name,'childSource':source,'childMaximumSeconds':2,'totalCleanupBoundSeconds':4.5,'hypothesis':('Reaping an already exited child removes the zombie-only ordering hazard; positive ESRCH remains required.' if name=='natural-exit' else 'This wrapper permits signalling a fresh owned live group; waiting for reap before absence probing avoids the exit window.'),'counterfactual':'Any wrapper permission denial or unknown custody halts this whole campaign, retains scratch, and admits no second experiment.', 'predicted':'terminal custody with independent reap, two EOFs and ESRCH; no EPERM'}
        # Persist each hypothesis BEFORE its child is launched.
        receipt['experiments'].append(experiment);save(target,receipt)
        try:
            item=manager.start(name,[sys.executable,'-B','-c',source],scratch,long_lived=True)
            if item['record']['pid'] in HELD:manager.unknown(item,'held-id-collision','no process operations allowed')
            if not manager.hold:
                if name=='natural-exit':
                    manager.pause(.15)
                else:
                    until=time.monotonic()+.5
                    while b'ready' not in item['buffers']['stdout'] and time.monotonic()<until:manager.pump(.01)
                    if b'ready' not in item['buffers']['stdout']:raise RuntimeError('live child readiness missing')
                manager.stop(item)
        except BaseException as error:
            experiment['error']=repr(error)
            if not manager.hold:
                for owned in manager.owned:
                    if owned['record']['state']=='RUNNING':manager.unknown(owned,'experiment-error',error);break
        if manager.hold:
            for owned in manager.owned:manager.persist(owned)
            experiment.update(records=manager.records,cleanup={'allTerminalCustody':False,'scratchRemoved':False,'hold':manager.hold},elapsedSeconds=time.monotonic()-start)
            receipt.update(status='UNKNOWN_HOLD_STOPPED',remainingExperiments='not launched')
            save(target,receipt)
            save(OUT/'new-custody-holds.json',{'groups':[r.get('owned_pgid') for r in manager.records if not r['terminal_custody']],'scratch':str(scratch),'hold':manager.hold,'noFurtherProcessActions':True})
            print(json.dumps({'status':receipt['status'],'hold':manager.hold,'records':manager.records}),flush=True)
            # Avoid Popen finalizers polling the held child at interpreter teardown.
            os._exit(2)
        cleanup=manager.cleanup(scratch)
        experiment.update(records=manager.records,cleanup=cleanup,elapsedSeconds=time.monotonic()-start)
        if not cleanup['allTerminalCustody'] or not cleanup['scratchRemoved'] or experiment['elapsedSeconds']>=5:
            receipt['status']='failed';save(target,receipt);return 1
        save(target,receipt)
    receipt['status']='passed';save(target,receipt)
    print(json.dumps({'status':'passed','experiments':len(receipt['experiments']),'pgids':[e['records'][0]['owned_pgid'] for e in receipt['experiments']],'allTerminalCustody':True}),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
