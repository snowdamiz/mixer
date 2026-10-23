#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,time,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--name',required=True);a=p.parse_args()
refpath=ROOT/a.reference;ref=json.loads(refpath.read_text());out=HERE/'.build'/('supplemental-'+a.name);out.mkdir(parents=True,exist_ok=False);logs=HERE/'runs'/('supplemental-'+a.name);logs.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=out/'SupplementalTests.swift';shutil.copy2(HERE/src.name,src);src.chmod(0o444)
receipt={'reference':a.reference,'reference_sha256':sha(refpath),'mode':ref['mode'],'source_tree_sha256':ref['source_tree_sha256'],'source_sha256':sha(src),'script_sha256':sha(Path(__file__)),'commands':[],'artifacts':{},'scope':'Additional original matrix schedules against exact actual Swift/C probe build. C wrappers forward once; only real native counter failures and actual return-boundary holds. No product replacement, Task/receipt/fence synthesis or device authority.'}
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
def save():(logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv):
    start=time.monotonic();r=subprocess.run([str(x) for x in argv],cwd=out,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    log=logs/(name+'.log');log.write_bytes(r.stdout);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(out),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit':r.returncode,'seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'sha256':sha(log)});save();print(name,r.returncode,flush=True)
    if r.returncode!=0 or b'WARNING: ThreadSanitizer' in r.stdout:print(r.stdout.decode(errors='replace'));raise RuntimeError(name)
    return r.stdout.decode(errors='replace')
try:
    run('swift-version',['xcrun','swiftc','--version'])
    argv=next(c['argv'] for c in ref['commands'] if c['name']=='harness-link');argv=[str(src) if v.endswith('/ProbeTests.swift') else v for v in argv]
    argv[argv.index('-emit-module-path')+1]=str(out/'SupplementalHostTests.swiftmodule');argv[argv.index('-o')+1]=str(out/'SupplementalHostTests')
    run('supplemental-link',argv)
    for case in ['c-endpoint-exhaustion','c-entry-exhaustion','fallback-before-fence','late-after-completion']:
        assert 'SUPPLEMENT_PASS '+case in run(case,[out/'SupplementalHostTests',case])
    receipt['artifacts'][str((out/'SupplementalHostTests').relative_to(ROOT))]=sha(out/'SupplementalHostTests');receipt['result']='all four additional original matrix schedules passed'
except BaseException as error:receipt['result']='failed supplemental attempt retained';receipt['error']=str(error);raise
finally:receipt['completed_utc']=datetime.now(timezone.utc).isoformat();save()
