#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for lane in ['baseline','candidate']:
    p=H/lane/'src/experimental_swift_reactor/cache_tests.rs'
    s=p.read_text();s=s[:s.index('// Independently authored review controls.')]+(H/'independent-controls.rs').read_text()
    if lane=='candidate':
        old='if ceiling == header + patch_bytes {\n            assert_eq!(stats.attempts, 2);'
        assert s.count(old)==1
        s=s.replace(old,old.replace('attempts, 2','attempts, 3'))
        s+=(H/'candidate-controls.rs').read_text()
        c=H/lane/'src/experimental_swift_reactor/cache.rs'
        c.write_text(c.read_text()+(H/'candidate-layout-controls.rs').read_text())
    p.write_text(s)
(H/'fixture-correction.json').write_text(json.dumps({'file':'candidate/src/experimental_swift_reactor/cache_tests.rs','helper':'review_exact_phase_and_header_admission_boundaries','assertion':'stats.attempts 2 -> 3 for successful zero-entry/zero-pin exact header + patch admission','reason':'actual patch, resident index and plan allocations','productionOrLimitsChanged':False,'originalFailure':'commands/candidate-exact-phase-original','candidateFileSHA256':sha(H/'candidate/src/experimental_swift_reactor/cache_tests.rs')},indent=2)+'\n')
