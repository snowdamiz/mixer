#!/usr/bin/env python3
"""Record only the independent audit and producer read-only verifier."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;P=ROOT/'verification/swift-retention-target-preparation';F=ROOT/'verification/swift-cache-retention-review'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
inputs={'preparationSealSHA256':sha(P/'prepared-seal.json'),'finiteReviewSealSHA256':sha(F/'seal.json'),'copiedBuildManifestSHA256':sha(P/'copied-build-manifest.json'),'driverSHA256':sha(P/'diagnostic.py'),'packetLibrarySHA256':sha(P/'packetlib.py')}
for name,script in [('independent-audit',H/'review.py'),('read-only-packet-verifier',P/'verify.py')]:
    out=H/'commands'/name;out.mkdir(parents=True,exist_ok=False)
    argv=[sys.executable,'-B',str(script)];start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat();script_hash=sha(script)
    with(out/'stdout').open('wb')as stdout,(out/'stderr').open('wb')as stderr:r=subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=60)
    assert sha(script)==script_hash
    assert inputs=={'preparationSealSHA256':sha(P/'prepared-seal.json'),'finiteReviewSealSHA256':sha(F/'seal.json'),'copiedBuildManifestSHA256':sha(P/'copied-build-manifest.json'),'driverSHA256':sha(P/'diagnostic.py'),'packetLibrarySHA256':sha(P/'packetlib.py')}
    write(out/'receipt.json',{'schema':1,'argv':argv,'cwd':str(ROOT),'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':r.returncode,'scriptSHA256':script_hash,'stdoutSHA256':sha(out/'stdout'),'stderrSHA256':sha(out/'stderr'),'python':{'path':sys.executable,'sha256':sha(sys.executable),'version':sys.version},'inputs':inputs,'boundInputsUnchanged':True,'sourceRestored':False,'compilerOrGuestRun':False,'scope':'Independent preparation review. Read-only producer verification or writes to this new review path only; no restore, actual target, native, network or product change.'})
    print(json.dumps({'command':name,'exitCode':r.returncode,'elapsedSeconds':time.monotonic()-start}),flush=True);print((out/'stdout').read_text(),flush=True);print((out/'stderr').read_text()[-2000:],flush=True)
    if r.returncode:raise SystemExit(r.returncode)
