#!/usr/bin/env python3
"""One isolated retry for our failed host-review-2 generated scratch; never touches native instances."""
import datetime
import json
from pathlib import Path
import shutil
import common
import run

def main():
    old=common.HERE/'host-review-2';work=old/'.build';out=common.HERE/'cleanup-host-review-2';out.mkdir()
    common.validate_seal(old)
    before=work.stat();identity=(before.st_dev,before.st_ino);files={str(p.relative_to(work)):{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in work.rglob('*') if p.is_file()}
    if work.is_symlink() or work.resolve()!=work or work.parent!=old or any(p.is_symlink() for p in work.rglob('*')):raise ValueError('unexpected owned host scratch')
    runner,_,_=run.load_runner();argv=['/usr/sbin/lsof','-nP','+D',str(work)];result=runner.execute(argv,cwd=common.ROOT,timeout=30);(out/'open-holders.log').write_bytes(result.stdout)
    if result.returncode!=1 or result.stdout or result.groupCleanup['after']:raise ValueError('holders found; preserve owned scratch')
    if identity!=(work.stat().st_dev,work.stat().st_ino) or files!={str(p.relative_to(work)):{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in work.rglob('*') if p.is_file()}:raise ValueError('owned scratch identity or contents drifted')
    shutil.rmtree(work)
    receipt={'schema':1,'status':'removed-owned-failed-host-review-scratch','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'nativeInstancesStarted':0,'physicalTargetsQueried':False,
        'path':str(work),'pathAbsent':not work.exists(),'priorFailureReceiptSHA256':common.sha(old/'receipt.json'),'historicalPreCleanupSealSHA256':common.sha(old/'artifact-seal.json'),
        'historicalSealScope':'host-review-2/artifact-seal.json preserves its failed-cleanup snapshot including generated scratch hashes; this retry removes only that scratch and does not rewrite the prior receipt/seal',
        'ownedDevice':identity[0],'ownedInode':identity[1],'removedFiles':len(files),'removedBytes':sum(v['bytes'] for v in files.values()),'removedMembership':files,
        'holderCheck':{'argv':argv,'cwd':str(common.ROOT),'exitCode':result.returncode,'output':'open-holders.log','sha256':common.sha(out/'open-holders.log'),'toolSHA256':common.sha(argv[0]),'ownedCommandGroupCleanup':result.groupCleanup}}
    common.save(out/'receipt.json',receipt);common.save(out/'artifact-seal.json',common.exact_seal(out));print(json.dumps({k:receipt[k] for k in ('status','pathAbsent','removedFiles','removedBytes')},sort_keys=True))

if __name__=='__main__':main()
