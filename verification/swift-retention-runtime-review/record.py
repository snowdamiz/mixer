#!/usr/bin/env python3
"""Record the read-only result audit; never run a target or restore products."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;R=ROOT/'verification/swift-retention-runtime'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=H/'command';out.mkdir(exist_ok=False)
script=H/'review.py';argv=[sys.executable,'-B',str(script)]
bound={'rootResultSealSHA256':sha(R/'seal.json'),'rootSummarySHA256':sha(R/'result-summary.json'),'reviewScriptSHA256':sha(script)}
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
with(out/'stdout').open('wb')as stdout,(out/'stderr').open('wb')as stderr:r=subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=30)
assert bound=={'rootResultSealSHA256':sha(R/'seal.json'),'rootSummarySHA256':sha(R/'result-summary.json'),'reviewScriptSHA256':sha(script)}
receipt={'schema':1,'argv':argv,'cwd':str(ROOT),'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':r.returncode,'inputs':bound,'boundInputsUnchanged':True,'stdoutSHA256':sha(out/'stdout'),'stderrSHA256':sha(out/'stderr'),'python':{'path':sys.executable,'sha256':sha(sys.executable),'version':sys.version},'scope':'Read-only retained-result assertions and exact-PGID ps observation; writes only inside this new review packet. No target, restore, compiler, native, network or product action.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'exitCode':r.returncode,'elapsedSeconds':receipt['elapsedSeconds']}));print((out/'stdout').read_text());print((out/'stderr').read_text());raise SystemExit(r.returncode)
