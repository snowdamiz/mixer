from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;R=H.parent.parent
refs=['AGENTS.md','docs/swift-cache-resident-index-contract.md','verification/swift-cache-resident-index-root-selection/selection.json','docs/swift-cache-work-attribution-result.md','verification/swift-cache-work-attribution-root-selection/result-binding.json','THIRD_PARTY.yml']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/refs[2])=='9f4d69cd9c4dcb858b336837bf0c66ea9ba9acb4895b5d07b62846cbdda05af9'
result={n:{'bytes':(R/n).stat().st_size,'sha256':sha(R/n)} for n in refs}
(H/'input-bindings.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({'boundInputMembers':len(result),'priorDriversImportedOrExecuted':False,'productionLimitsChanged':False,'dependenciesAdded':False}))
