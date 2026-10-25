#!/usr/bin/env python3
"""Copy the sealed finite sources, adding only independent test instrumentation."""
from pathlib import Path
import hashlib, json, shutil
H=Path(__file__).resolve().parent
P=H.parent/'swift-decode-plan-reuse-diagnosis'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
assert sha(P/'seal.json')=='975085349286df4f467942eaf3f1704d8983fa3ea103277c60dea4e885af43c5'
for lane,original in [('baseline','baseline'),('candidate','source')]:
    shutil.copytree(P/original,H/lane)
    for p in (H/lane).rglob('*'):
        if p.is_file(): p.chmod(0o644)
    save(H/(lane+'-input-manifest.json'),{str(p.relative_to(H/lane)):sha(p) for p in sorted((H/lane).rglob('*')) if p.is_file()})
    cache=H/lane/'src/experimental_swift_reactor/cache.rs'
    with cache.open('a') as f: f.write((H/'layout-controls.rs').read_text().replace('REVIEW_CANDIDATE',str(lane=='candidate').lower()))
    tests=H/lane/'src/experimental_swift_reactor/cache_tests.rs'
    with tests.open('a') as f: f.write((H/'independent-controls.rs').read_text())
save(H/'selection.json',{'producerSealSHA256':sha(P/'seal.json'),'candidateProductionFile':'src/experimental_swift_reactor/cache.rs','candidateProductionSHA256':sha(P/'source/src/experimental_swift_reactor/cache.rs'),'baselineProductionSHA256':sha(P/'baseline/src/experimental_swift_reactor/cache.rs'),'sourceEdits':'append test-only independent layout module and tests; later separately recorded candidate fixture assertion only','liveIntegration':False,'fullRegression':False,'fullReactor':False})
print('copied exact sealed baseline/candidate plus review-only test appendices')
