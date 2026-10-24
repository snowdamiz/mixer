#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, subprocess, datetime
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent/'candidate2-api'
out.mkdir(exist_ok=True)
expected={
'vm/src/experimental_swift_reactor/execution.rs':'663c14a5609096f94758608ece9550e22c16a4d420a03d87abf930e383834ea6',
'vm/src/experimental_swift_reactor/execution_tests.rs':'8615969f23ae7562c81802ddc410549e3622d0c1ad187e3ed5c8476323f5d8b2',
'docs/swift-executor-construction.md':'3ed9ba64d3d76d629749810fdd4a8415628b38fa18f15c90bccbbc7b92c91f40'}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for name,digest in expected.items(): assert sha(root/name)==digest,(name,'freeze drift before copy')
files=[]
for folder in ['vm/src','vm/tests','vm/include']:
    files.extend(p for p in (root/folder).rglob('*') if p.is_file())
for name in ['vm/Cargo.toml','vm/Cargo.lock','AGENTS.md','docs/swift-executor-stage-contract.md','docs/swift-executor-construction.md','docs/swift-reactor-execution-stage-design.md','verification/swift-executor-stage-acceptance.json']:
    files.append(root/name)
rows=[]
for src in sorted(files):
    rel=src.relative_to(root)
    dst=out/'inputs'/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)
    assert sha(src)==sha(dst),(rel,'copy drift')
    rows.append({'path':str(rel),'sha256':sha(dst),'bytes':dst.stat().st_size})
for name,digest in expected.items(): assert sha(root/name)==digest,(name,'freeze drift after copy')
manifest={'schema':'mixer-swift-construction-independent-inputs-v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'dirty_state':subprocess.check_output(['git','status','--short'],cwd=root,text=True),'expected_frozen':expected,'files':rows,'tree_digest_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(out/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'input-diff.patch').write_text(subprocess.check_output(['git','diff','--','vm'],cwd=root,text=True))
print(json.dumps({'input_files':len(rows),'tree_digest_sha256':manifest['tree_digest_sha256'],'frozen_inputs_verified':True}))
