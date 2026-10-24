#!/usr/bin/env python3
"""Retain upstream F01-F07 finite synthetic controls; no native target commands."""
import importlib.util,json,os,shutil,sys,tempfile,traceback
from pathlib import Path
import build as common
HERE=common.HERE;ROOT=common.ROOT

def main():
    out=HERE/'upstream-controls-2';out.mkdir();work=Path(tempfile.mkdtemp(prefix='mixer-authored-toggle-controls-',dir='/private/tmp'));identity=work.stat()
    receipt={'schema':1,'startedUTC':common.now(),'scope':'upstream oracle/wrapper finite synthetic guards; native target NOT RUN','nativeCommands':0,'commands':[],'sourceBindings':{}}
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def command(name,argv,allowed=(0,)):
        start=common.now();argv=list(map(str,argv));r=common.owned.execute(argv,cwd=ROOT,env=env,timeout=180);p=out/(name+'.log');p.write_bytes(r.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(ROOT),'startedUTC':start,'finishedUTC':common.now(),'exitCode':r.returncode,'output':p.name,**common.bind(p),'ownedCommandGroupCleanup':r.groupCleanup});print(name+': exit '+str(r.returncode),flush=True)
        if r.returncode not in allowed:raise RuntimeError(name+' failed')
        return r.stdout
    try:
        for d in ['verification/android-pointer-oracle-repair','verification/android-pointer-timing-correction']:
            for p in sorted((ROOT/d).glob('*.py')):receipt['sourceBindings'][str(p.relative_to(ROOT))]=common.bind(p)
        command('upstream-oracle-packet',[sys.executable,'-B',ROOT/'verification/android-pointer-oracle-repair/check_packet.py'])
        command('upstream-review-packet',[sys.executable,'-B',ROOT/'verification/android-pointer-oracle-repair-review/check_review.py'])
        command('upstream-corrected-timing-controls',[sys.executable,'-B',ROOT/'verification/android-pointer-timing-correction/test_host.py','--work',work/'tests','--results',out/'test-results.json'])
        result=json.loads((out/'test-results.json').read_text())
        if result['status']!='passed' or result['executed']!=55 or result['nativeCommands']!=0:raise ValueError('exact 55 upstream controls required')
        for n,v in receipt['sourceBindings'].items():
            if common.bind(ROOT/n)!=v:raise ValueError('upstream guard changed')
        receipt['status']='passed-upstream-55-finite-synthetic-F01-F07-controls';receipt['testResults']=result
    except BaseException as failure:receipt['status']='failed-retained';receipt['failure']=repr(failure);(out/'failure.log').write_text(traceback.format_exc());raise
    finally:
        try:
            holders=command('scratch-open-holders',['/usr/sbin/lsof','-nP','+D',work],allowed=(1,))
            if holders:raise ValueError('scratch holder remains')
            st=work.stat()
            if work.is_symlink() or (st.st_dev,st.st_ino)!=(identity.st_dev,identity.st_ino):raise ValueError('ownership mismatch')
            files=[p for p in work.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in files);shutil.rmtree(work)
            receipt['cleanup']={'path':str(work),'ownedDevice':st.st_dev,'ownedInode':st.st_ino,'filesRemoved':len(files),'bytesRemoved':size,'absent':not work.exists()}
        finally:receipt['finishedUTC']=common.now();common.save(out/'receipt.json',receipt);common.save(out/'artifact-seal.json',common.seal(out))
if __name__=='__main__':main()
