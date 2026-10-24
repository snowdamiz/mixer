#!/usr/bin/env python3
"""Remove only this lane's explicit Python compile cache after exact membership and empty-holder checks."""
import datetime
import json
from pathlib import Path
import sys
import common
import run


def main():
    out=common.HERE/'cleanup-generated-1';out.mkdir();runner,_,_=run.load_runner();cache=common.HERE/'__pycache__'
    result={'schema':1,'scope':'only explicit generated Python cache in this owned repair lane','command':[sys.executable,'-B',str(Path(__file__).relative_to(common.ROOT))],'scriptSHA256':common.sha(__file__),'pythonVersion':sys.version,'nativeRuntime':'NOT RUN','nativeInstancesStarted':0,'physicalTargetsQueried':False,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        if cache.is_symlink() or not cache.is_dir():raise ValueError('expected owned generated cache directory')
        identity=cache.stat();files={p.name:{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in cache.iterdir() if p.is_file() and not p.is_symlink()}
        if len(files)!=len(list(cache.iterdir())) or not files or any(not n.endswith('.pyc') or not (common.HERE/(n.split('.')[0]+'.py')).is_file() for n in files):raise ValueError('unexpected cache member')
        argv=['/usr/sbin/lsof','-nP','+D',str(cache)];completed=runner.execute(argv,cwd=common.ROOT,timeout=30);log=out/'open-holders.log';log.write_bytes(completed.stdout)
        result['holderCheck']={'argv':argv,'exitCode':completed.returncode,'output':log.name,'sha256':common.sha(log),'ownedCommandGroupCleanup':completed.groupCleanup}
        if completed.returncode!=1 or completed.stdout:raise ValueError('own generated cache held')
        if (cache.stat().st_dev,cache.stat().st_ino)!=(identity.st_dev,identity.st_ino):raise ValueError('owned generated cache identity changed')
        for name,value in files.items():
            path=cache/name
            if path.is_symlink() or {'bytes':path.stat().st_size,'sha256':common.sha(path)}!=value:raise ValueError('owned cache member changed')
        for name in files:(cache/name).unlink()
        cache.rmdir();result.update({'status':'removed-owned-generated-cache','removedFiles':files,'bytes':sum(v['bytes'] for v in files.values()),'pathAbsent':not cache.exists()})
    finally:
        result['finishedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();common.save(out/'receipt.json',result);common.save(out/'artifact-seal.json',common.exact_seal(out))
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
