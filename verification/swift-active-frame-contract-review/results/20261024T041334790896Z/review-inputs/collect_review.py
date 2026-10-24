#!/usr/bin/env python3
"""Independent offline source/contract review packet. No native tools."""
import datetime, hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'results' / stamp
OUT.mkdir(parents=True)

def sha(data): return hashlib.sha256(data).hexdigest()
def closure():
    listed = subprocess.run(['rg','--files','vm'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.splitlines()
    paths = sorted(p for p in listed if p in ('vm/Cargo.toml','vm/Cargo.lock','vm/build.rs') or p.startswith(('vm/src/','vm/tests/')))
    rows = [{'path':p,'sha256':sha((ROOT/p).read_bytes()),'bytes':(ROOT/p).stat().st_size} for p in paths]
    return {'files':rows,'treeSHA256':sha(''.join(f"{r['sha256']}  {r['path']}\n" for r in rows).encode())}
commands=[]
def run(name, argv):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    finish=datetime.datetime.now(datetime.timezone.utc).isoformat()
    stdout=OUT/(name+'.stdout'); stderr=OUT/(name+'.stderr')
    stdout.write_text(result.stdout); stderr.write_text(result.stderr)
    commands.append({'name':name,'argv':argv,'cwd':str(ROOT),'startedUTC':start,'finishedUTC':finish,'exitCode':result.returncode,'stdout':str(stdout.relative_to(ROOT)),'stdoutSHA256':sha(stdout.read_bytes()),'stderr':str(stderr.relative_to(ROOT)),'stderrSHA256':sha(stderr.read_bytes())})
    return result
before=closure()
run('revision',['git','rev-parse','HEAD'])
run('status',['git','status','--short'])
run('rustc-version',['/opt/homebrew/opt/rustup/bin/rustc','--version','--verbose'])
run('cargo-version',['/opt/homebrew/opt/rustup/bin/cargo','--version'])
run('python-version',[sys.executable,'--version'])
run('platform',['uname','-a'])
source_paths=['AGENTS.md','docs/swift-executor-control-next-slice.md','docs/swift-executor-operations.md','docs/swift-executor-stage-contract.md','docs/swift-shared-executor-algorithm-contract.md','vm/src/experimental_swift_reactor/execution.rs','vm/src/experimental_swift_reactor/value_operations.rs','vm/src/experimental_swift_reactor/cache.rs','vm/src/experimental_swift_reactor/control.rs','vm/src/experimental/cache/borrowed.rs','vm/src/experimental/execution/mod.rs','vm/src/experimental/execution/borrowed.rs','vm/src/experimental_wasi/accounted.rs','verification/swift-control-macro-root-review/acceptance.json']
sources=[]
for path in source_paths:
    data=(ROOT/path).read_bytes(); dest=OUT/'source'/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    sources.append({'path':path,'sha256':sha(data),'bytes':len(data),'saved':str(dest.relative_to(ROOT))})
after=closure()
receipt={'schema':'mixer.swift-active-frame-contract-independent-source-review.v1','scope':'Host-only original source reasoning; no product implementation or runtime acceptance. Producer proposal review follows its freeze.','startedSource':before,'finishedSource':after,'sourceUnchanged':before==after,'sources':sources,'commands':commands,'computerUse':False,'nativeRuntime':False,'physicalRuntime':False,'gaAcceptance':False,'productSourceEdited':False}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(OUT.relative_to(ROOT))
if before!=after or any(c['exitCode'] for c in commands): sys.exit(1)
