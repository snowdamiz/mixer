#!/usr/bin/env python3
"""Measure existing foundation shapes only; no cache/executor target run."""
import hashlib, io, json, os, subprocess, tarfile, time
from pathlib import Path
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REV='3a1bb5a455973bde841a4b57993277fa2c054569'
sha=lambda data: hashlib.sha256(data).hexdigest()
raw=subprocess.check_output(['git','archive',REV,'vm'],cwd=ROOT)
(HERE/'layout-source.tar').write_bytes(raw)
source=HERE/'.build/layout/source'
source.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:tar.extractall(source,filter='data')
test=source/'vm/src/experimental_swift_reactor/control_tests.rs'
test.write_bytes(test.read_bytes()+(HERE/'layout_probe.rs').read_bytes())
manifest={str(p.relative_to(source)):sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
env=dict(os.environ)
env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH']
env['CARGO_TARGET_DIR']=str(HERE/'.build/layout/target')
records=[]
for mode in ['debug','release']:
    argv=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-swift-reactor','--lib']+(['--release'] if mode=='release' else [])+['experimental_swift_reactor::control::tests::review_final_tail_named_layouts','--','--exact','--nocapture']
    start=time.monotonic()
    p=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    data=p.stdout
    (HERE/(mode+'-layout.log')).write_bytes(data)
    assert p.returncode==0 and b'test result: ok. 1 passed; 0 failed;' in data,data.decode()
    records.append({'argv':argv,'cwd':str(source),'exit':p.returncode,'seconds':time.monotonic()-start,'log':mode+'-layout.log','sha256':sha(data)})
assert manifest=={str(p.relative_to(source)):sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'revision':REV,'source_archive_sha256':sha(raw),'source_tree_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'probe_sha256':sha((HERE/'layout_probe.rs').read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),'commands':records,'scope':'Named type size/alignment probe of committed control/accounted-WASI foundation only. No cache implementation acceptance, composed executor or target instantiation/execution.'}
(HERE/'layout-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
