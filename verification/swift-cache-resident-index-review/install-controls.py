from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent
for kind in ('candidate','baseline'):
 p=H/'owned-scratch'/kind/'src/experimental_swift_reactor/cache_tests.rs'
 original=p.read_bytes(); extra=(H/'common-controls.rs').read_bytes()+((H/'candidate-controls.rs').read_bytes() if kind=='candidate' else b'\nfn independent_review_extra(_: &SwiftFunctionCache) {}\n')
 p.write_bytes(original+b'\n'+extra)
 (H/(kind+'-test-overlay.json')).write_text(json.dumps({'originalSHA256':hashlib.sha256(original).hexdigest(),'appendedSHA256':hashlib.sha256(extra).hexdigest(),'resultSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'changesProductionSource':False,'onlySourceChange':'src/experimental_swift_reactor/cache_tests.rs'},sort_keys=True,indent=2)+'\n')
