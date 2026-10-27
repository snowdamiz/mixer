#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
D=Path(__file__).resolve().parent
R=D.parents[1]
original=json.loads((R/'verification/swift-guarded-snapshot-loader-work-source146/compiler-receipt.json').read_text())
compiler=Path(original['argv'][0]);raw=compiler.read_bytes()
assert hashlib.sha256(raw).hexdigest()==original['compiler_sha256']
product=(R/'verification/swift-guarded-snapshot-funding-implementation/source/vm/src/execute.rs').read_text()
assert '#[derive(Clone, Default)]\npub struct Cancellation(Arc<AtomicBool>);' in product
assert '#[derive(Clone, Default)]\npub struct Cancellation(Arc<AtomicBool>);' in (D/'cancellation-backing-probe.rs').read_text()
(D/'probe-tmp').mkdir(exist_ok=True)
command=[str(compiler),'--crate-name','mixer_cancellation_backing_probe','--edition=2021','--target','aarch64-apple-darwin','--crate-type','rlib','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','-Zprint-type-sizes',str(D/'cancellation-backing-probe.rs'),'--emit=llvm-ir='+str(D/'cancellation-backing-probe.ll')]
environment={'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':original['environment']['SDKROOT'],'TMPDIR':str(D/'probe-tmp')}
start=time.monotonic();process=subprocess.Popen(command,cwd=D,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed_out=False
try:stdout,stderr=process.communicate(timeout=60)
except subprocess.TimeoutExpired:
    timed_out=True;os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
(D/'probe.stdout').write_bytes(stdout);(D/'probe.stderr').write_bytes(stderr)
ir=D/'cancellation-backing-probe.ll'
record=dict(command=command,environment=environment,compiler_sha256=hashlib.sha256(raw).hexdigest(),compiler_version_bound_by_immutable_receipt=original['compiler_version'],source_sha256=hashlib.sha256((D/'cancellation-backing-probe.rs').read_bytes()).hexdigest(),product_fragment_equivalence=True,exit_code=process.returncode,timed_out=timed_out,timeout_seconds=60,elapsed_seconds=time.monotonic()-start,direct_child_waited=True,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest(),IR_sha256=hashlib.sha256(ir.read_bytes()).hexdigest() if ir.exists() else None,executable_created=False,product_or_probe_executed=False,scope='one authorized standalone exact1.99 production LLVM-IR compile-only Arc backing/clone probe; no fixture or whole-product compile/run')
(D/'probe-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
assert process.returncode==0 and not timed_out,stderr.decode()
print(json.dumps(dict(exit_code=process.returncode,IR_bytes=ir.stat().st_size,stdout_bytes=len(stdout),stderr_bytes=len(stderr),executed=False)))
