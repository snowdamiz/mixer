#!/usr/bin/env python3
"""Freeze only this independent review after a recorded pure read-only replay."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,platform,subprocess,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def out(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
if (H/'seal.json').exists():raise SystemExit('already frozen')
folder=H/'commands/replay';folder.mkdir(parents=True,exist_ok=False)
argv=[sys.executable,str(H/'verify.py')]
started=datetime.now(timezone.utc).isoformat();t=time.monotonic()
result=subprocess.run(argv,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
(folder/'stdout').write_bytes(result.stdout);(folder/'stderr').write_bytes(result.stderr)
out(folder/'receipt.json',dict(schema=1,command=argv,started_at=started,
    finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-t,
    exit_code=result.returncode,python_version=sys.version,platform=platform.platform(),
    source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
    scope='pure frozen source/MIR/native-data/model reconstruction; no compiler or product/runtime/native/UI/capture',
    output_bindings={name:dict(bytes=len(raw),sha256=sha(raw)) for name,raw in [('stdout',result.stdout),('stderr',result.stderr)]},
    reviewer_tree_before_receipt=[dict(path=str(p.relative_to(H)),bytes=len(p.read_bytes()),sha256=sha(p.read_bytes()))
        for p in sorted(H.rglob('*')) if p.is_file() and not p.is_relative_to(folder)]))
if result.returncode:raise SystemExit(result.returncode)
members=[dict(path=str(p.relative_to(H)),bytes=len(p.read_bytes()),sha256=sha(p.read_bytes()))
    for p in sorted(H.rglob('*')) if p.is_file()]
out(H/'seal.json',dict(schema=1,status='independent-reviewed-bounded-callee-interface-with-native-and-capture-amendment',
    source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
    member_count=len(members),members=members,
    tree_sha256=sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),
    complete_host_quote=False,operational_grant=False,native_or_GA_qualified=False))
print(json.dumps(dict(path=str(H.relative_to(R)),seal_sha256=sha((H/'seal.json').read_bytes()),
    members=len(members),bytes=sum(m['bytes'] for m in members),
    native_binding_receipt_sha256=sha((H/'native-binding-receipt.json').read_bytes()),
    conditional_callee_interface_sha256=sha((H/'bound-cost-interface.json').read_bytes()))))
