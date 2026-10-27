#!/usr/bin/env python3
"""Run exactly one bounded pure Python checker and preserve its receipts."""
import datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    require_target=sys.argv[1:];allowed={'derive.py','test_provenance.py','check.py','test_correction.py','custody.py','prepare_contracts.py'}
    if not require_target or require_target[0] not in allowed:raise SystemExit('pure checker target required')
    require_not_frozen=not (D/'seal.json').exists()
    if not require_not_frozen:raise SystemExit('packet already frozen')
    logs=D/'commands';logs.mkdir(exist_ok=True);out=logs/f'attempt-{len(list(logs.glob("attempt-*")))+1:03d}';out.mkdir()
    scripts=[]
    for p in sorted(D.glob('*.py')):
        raw=p.read_bytes();scripts.append({'path':p.name,'bytes':len(raw),'sha256':sha(raw)});(out/('source-'+p.name)).write_bytes(raw)
    argv=[sys.executable,'-B',str(D/require_target[0]),*require_target[1:]];started=time.monotonic()
    child=subprocess.run(argv,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
    (out/'stdout').write_bytes(child.stdout);(out/'stderr').write_bytes(child.stderr)
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(R),'python_version':sys.version,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'script_members':scripts,'script_tree_sha256':sha(json.dumps(scripts,sort_keys=True,separators=(',',':')).encode()),'source_revision':'frozen-source146-exacttree-690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','exit_code':child.returncode,'elapsed_seconds':time.monotonic()-started,'stdout_sha256':sha(child.stdout),'stderr_sha256':sha(child.stderr),'owned_child_waited':True,'scope':'offline pinned source/typed compiler MIR data and pure checker tests only; no compiler/product/native/UI/capture/Git/root metadata/global process inventory','timeout_seconds':55,'PYTHONDONTWRITEBYTECODE':'1'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    sys.stdout.buffer.write(child.stdout);sys.stderr.buffer.write(child.stderr);raise SystemExit(child.returncode)
if __name__=='__main__':main()
