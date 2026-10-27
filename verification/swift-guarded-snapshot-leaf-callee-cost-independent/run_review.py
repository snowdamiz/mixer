#!/usr/bin/env python3
"""Record pure reviewer controls, retaining failed attempts without overwrite."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, platform, subprocess, sys, time, unittest
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
R=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def out(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
attempts=H/'attempts';attempts.mkdir(exist_ok=True)
index=1
while (attempts/f'{index:02d}').exists():index+=1
where=attempts/f'{index:02d}';where.mkdir()
(where/'reviewer-source.py').write_bytes((H/'audit.py').read_bytes())
(where/'runner-source.py').write_bytes(Path(__file__).read_bytes())
started=datetime.now(timezone.utc).isoformat();t=time.monotonic()
producer=R/'verification/swift-guarded-snapshot-leaf-callee-cost'
argv=[sys.executable,str(producer/'verify.py'),'--tests']
replay=subprocess.run(argv,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
(where/'producer.stdout').write_bytes(replay.stdout);(where/'producer.stderr').write_bytes(replay.stderr)
import audit
with (where/'independent.stdout').open('w') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(audit.IndependentReview))
receipt=dict(schema=1,command=[sys.executable,str(H/'run_review.py')],producer_replay_command=argv,
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-t,
    python_version=sys.version,platform=platform.platform(),source_tree_sha256=audit.TREE,
    source_identity_kind='immutable146composedmanifest; current Git HEAD neither queried nor substituted',
    reviewer_script_sha256=sha((H/'audit.py').read_bytes()),runner_script_sha256=sha(Path(__file__).read_bytes()),
    tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),producer_exit_code=replay.returncode,
    required_input_negative_cases=audit.IndependentReview.required_negatives,
    compiler_invoked=False,product_runtime=False,native_runtime=False,UI_or_capture=False,
    global_process_inventory=False,scope='pure Python independent frozen source/MIR/data/model checks and producer read-only replay',
    outputs={p.name:dict(bytes=len(p.read_bytes()),sha256=sha(p.read_bytes())) for p in where.iterdir() if p.is_file()})
out(where/'receipt.json',receipt)
print(json.dumps(dict(attempt=index,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                     producer_exit_code=replay.returncode,negative_cases=audit.IndependentReview.required_negatives,
                     elapsed_seconds=receipt['elapsed_seconds'])))
if not result.wasSuccessful() or replay.returncode:raise SystemExit(1)
