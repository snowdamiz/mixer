#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, subprocess, datetime
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent/'candidate3-final'
out.mkdir(exist_ok=True)
expected={
'vm/src/experimental_swift_reactor/control.rs':'c5e6eb2615b89feda7a8bfe89a856a52a4490f237b02257f520e521e51c39d06',
'vm/src/experimental/swift.rs':'8c9938306112b9288646baa68b7f7f29f487c77ef7c96dffb516516525533798',
'vm/src/experimental_swift_reactor/cache.rs':'ae72ef7d1c4ca9f7784adb5dc7fb7688e6db37bfe4313e335a7eca17e3030da0',
'vm/src/experimental_swift_reactor/cache_tests.rs':'b346de261e394719f5a4fd41693ba37d19d6e0ddcc948c4a21241322bcb859af',
'vm/src/experimental_swift_reactor/control_tests.rs':'9cd7a9cf60ba9f10feaba9535878d15673c7bc2ed3d9ae0a8ab0ad48bd55655d',
'vm/src/experimental_swift_reactor/execution.rs':'13c07bb5cce24e8c22c8d8b9ef4f94de0622891a3db9d50e70a8188e3c3b18aa',
'vm/src/experimental_swift_reactor/execution_tests.rs':'8615969f23ae7562c81802ddc410549e3622d0c1ad187e3ed5c8476323f5d8b2',
'docs/swift-executor-construction.md':'96b380dc36c4d711339f7376b378ebed9197386c81b95f664453979304b55795'}
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
