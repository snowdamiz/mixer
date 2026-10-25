#!/usr/bin/env python3
"""Instrument only the sealed scratch TEST provider to ignore cancellation."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
scratch=Path(json.loads((HERE/'bindings.json').read_text())['scratch'])
target=scratch/'hosted-worker-controller/test/worker.ts'
raw=target.read_text()
expected='this.resolveHold=resolve;signal.addEventListener("abort",()=>{this.resolveHold=null;reject(new Error("fixture_aborted"));},{once:true});'
assert raw.count(expected)==1
modified=raw.replace(expected,'this.resolveHold=resolve; // Independent fixture: deliberately ignores AbortSignal.')
(HERE/'noncooperative-worker.ts').write_text(modified)
target.write_text(modified)
report={'scope':'verification-fixture-only; frozen product source unchanged','original_test_worker_sha256':hashlib.sha256(raw.encode()).hexdigest(),'independent_test_worker_sha256':hashlib.sha256(modified.encode()).hexdigest(),'replacements':1,'change':'held synthetic launch promise remains pending after abort until explicit local release'}
(HERE/'noncooperative-fixture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
