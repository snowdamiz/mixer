from pathlib import Path
import json,hashlib,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'seal.json').exists(),'Do not overwrite a frozen packet seal'
bindings={}
for name in ['docs/swift-control-invocation-contract.md','docs/swift-control-accounting-candidate-2.md','docs/swift-control-candidate-2-review.md','verification/swift-control-invocation-root-review/contract.json','verification/swift-control-invocation-root-review/accounting-scope-interpretation.json','verification/swift-control-invocation-root-review/candidate-2-acceptance.json','verification/swift-control-accounting-candidate-2/seal.json','verification/swift-control-accounting-candidate-2/inventory-schema.json']:
 bindings[name]=sha(ROOT/name)
files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json'}
seal=dict(schema=1,status='frozen-producer-packet-pending-independent-behavior-review',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,documentSHA256=sha(ROOT/'docs/swift-control-behavior-implementation.md'),priorBindings=bindings,implementationAccepted=False,gaAcceptance=False)
(HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
print('sealed',len(files),'files')
