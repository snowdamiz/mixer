"""Freeze own evidence only, or verify all frozen members without mutations."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def encoded(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def main():
    check='--check' in sys.argv
    if not check:
        assert not (D/'seal.json').exists(),'already frozen'
        assert not (D/'compiler-owned-work').exists()
        started=time.monotonic();argv=[sys.executable,'-B',str(D/'review.py'),'--check'];env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
        p=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=30)
        (D/'freeze-check.stdout').write_bytes(p.stdout);(D/'freeze-check.stderr').write_bytes(p.stderr)
        rec=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(R),environment=env,python_version=sys.version,python_executable=sys.executable,
          python_executable_sha256=sha(Path(sys.executable).read_bytes()),git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
          elapsed_seconds=time.monotonic()-started,exit_code=p.returncode,stdout_sha256=sha(p.stdout),stderr_sha256=sha(p.stderr),compiler=False,product_runtime=False,global_process_inventory=False)
        (D/'freeze-command.json').write_bytes(encoded(rec));assert p.returncode==0,p.stderr.decode()
    members=[]
    for p in sorted(D.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file() and p.name!='seal.json':
            assert '__pycache__' not in p.parts and p.suffix!='.pyc',str(p)
            b=p.read_bytes();members.append(dict(path=str(p.relative_to(D)),bytes=len(b),sha256=sha(b)))
    seal=dict(schema=1,status='frozen-native-open-constructor-interface-candidate-pending-independent-review-and-root-selection',
      member_count=len(members),member_bytes=sum(r['bytes'] for r in members),tree_sha256=sha(canonical(members)),members=members,
      source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',actual_immutable_caller_or_executable_bound=False,
      actual_root_pricing_authority_grant=False,product_runtime=False,native_runtime='paused',GA_verified=False)
    data=encoded(seal)
    if check:assert (D/'seal.json').read_bytes()==data,'frozen member set or digest differs'
    else:(D/'seal.json').write_bytes(data)
    print(json.dumps(dict(seal_sha256=sha(data),members=len(members),bytes=seal['member_bytes'],checked=check)))
if __name__=='__main__':main()
