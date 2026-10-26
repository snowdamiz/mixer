"""Snapshot exact permitted pointers to a historical invocation; never execute them."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[1]
paths=['docs/swift-current-attribution-runtime-review.md','docs/swift-plan-cache-remaining-work-diagnosis.md','verification/swift-current-attribution-runtime-review/audit.py','verification/swift-current-attribution-runtime-review/receipt.json','verification/swift-current-attribution-runtime/root-selection.json','verification/swift-current-attribution-runtime/selected-command.json','verification/swift-current-attribution-runtime/commands/target-once/stdout']
rows=[]
for path in paths:
 raw=(R/path).read_bytes();q=P/'inputs'/path;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();q.write_bytes(raw)
 rows.append({'path':path,'snapshot':str(q.relative_to(P)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
body={'schema':1,'members':rows,'scope':'Historical accepted attribution invocation candidate only; no current invocation selection, execution or seal requalification','tree_sha256':hashlib.sha256(''.join(f"{r['path']}\t{r['bytes']}\t{r['sha256']}\n"for r in sorted(rows,key=lambda r:r['path'])).encode()).hexdigest()}
(P/'additional-inputs.json').write_text(json.dumps(body,indent=2,sort_keys=True)+'\n')
print(json.dumps({'additional_inputs':len(rows),'scope':body['scope']}))
