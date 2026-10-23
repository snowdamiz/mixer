#!/usr/bin/env python3
"""Freeze LLDB driver and bind separate scheduling-only receipts to exact binaries."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shutil,subprocess,time,shlex
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--name',required=True);p.add_argument('--cases',default='post-store,setup-alias,bind-return,cancel-accepted,waiter-exhaustion,progress-token-exhaustion,progress-sequence-exhaustion,lifetime-exhaustion,gate-order');a=p.parse_args()
refpath=ROOT/a.reference;ref=json.loads(refpath.read_text());source=Path(ref['commands'][0]['cwd']);binary=source.parent/'Stage4HostTests'
logs=HERE/'runs'/('lldb-'+a.name);logs.mkdir(parents=True,exist_ok=False);driver=logs/'debugger_driver.py';shutil.copy2(HERE/'debugger_driver.py',driver);driver.chmod(0o444)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt={'reference':a.reference,'reference_sha256':sha(refpath),'source_tree_sha256':ref['source_tree_sha256'],'mode':ref['mode'],'scope':'Separate LLDB scheduling/failure instrumentation of actual frozen product-byte Debug/Release/TSan build. No result/receipt/fence writes. Post-store proof requires actual terminal store+unlock and same original presentation worker resumed before actual Task.value evidence. Mode-specific optimized-frame limitations remain failures.','commands':[],'inputs':{'driver':sha(driver),'launcher':sha(Path(__file__))},'artifacts':{str(binary.relative_to(ROOT)):sha(binary)}}
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
for path in source.parent.glob('*.dylib'):receipt['artifacts'][str(path.relative_to(ROOT))]=sha(path)
def save():(logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv):
    start=time.monotonic()
    try:r=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90);data,code=r.stdout,r.returncode
    except subprocess.TimeoutExpired as e:data,code=(e.stdout or b'')+b'\nTIMEOUT\n',124
    path=logs/(name+'.log');path.write_bytes(data);receipt['commands'].append({'name':name,'argv':argv,'cwd':str(ROOT),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit':code,'seconds':time.monotonic()-start,'log':str(path.relative_to(ROOT)),'sha256':sha(path)});save();print(name,code,flush=True)
    return code,data.decode(errors='replace')
run('lldb-version',['xcrun','lldb','--version'])
allpass=True
for scenario in a.cases.split(','):
    target=logs/(scenario+'.json')
    command='stage4-debugger '+' '.join(shlex.quote(str(v)) for v in [binary,scenario,target,source])
    code,data=run(scenario,['xcrun','lldb','--batch','-o','command script import '+str(driver),'-o',command])
    success=code==0 and 'LLDB_PASS '+scenario in data and target.exists() and json.loads(target.read_text())['result']=='passed'
    allpass=allpass and success
receipt['result']='all selected instrumented scheduling/failure proofs passed' if allpass else 'failed instrumented attempts retained; no broader pass'
receipt['evidence']={str(path.relative_to(ROOT)):sha(path) for path in logs.glob('*') if path.is_file() and path.name!='receipt.json'}
receipt['completed_utc']=datetime.now(timezone.utc).isoformat();save()
raise SystemExit(0 if allpass else 1)
