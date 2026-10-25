from pathlib import Path
import hashlib,json,difflib
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
base=json.loads((H/'baseline-manifest.json').read_text())
source={n:sha(H/'source'/n) for n in base};baseline={n:sha(H/'baseline'/n) for n in base}
save(H/'source-manifest.json',source);save(H/'baseline-control-manifest.json',baseline)
changed=[n for n in base if source[n]!=base[n]];assert changed==['src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
assert [n for n in base if baseline[n]!=base[n]]==['src/experimental_swift_reactor/cache_tests.rs']
patch=[]
for n in changed:patch.extend(difflib.unified_diff((R/'vm'/n).read_text().splitlines(True),(H/'source'/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(H/'candidate.patch').write_text(''.join(patch))
inputs=['docs/swift-cache-work-attribution-result.md','docs/swift-cache-resident-index.md','verification/swift-exact-reactor-after-grouped-index/result.md','verification/swift-exact-reactor-after-grouped-index/result-seal.json','mixer-product-plan.md','AGENTS.md']
bindings={n:sha(R/n) for n in inputs}
assert bindings['verification/swift-exact-reactor-after-grouped-index/result-seal.json']=='91c71f2c6b6520e141b9226f7675a4578d0d37865aa1dfcfafc9e4dad31acb8c'
save(H/'input-bindings.json',bindings)
save(H/'source-selection.json',{'scope':'isolated finite prototype only; not live acceptance','rootRequestedRevision':'4a28261b333c28b4fce386f370a19b93e735c8d2','original132FileClosure':sha(H/'baseline-manifest.json'),'prototype132FileClosure':sha(H/'source-manifest.json'),'baselineControl132FileClosure':sha(H/'baseline-control-manifest.json'),'changedFiles':changed,'liveSourceUnchanged':all(sha(R/'vm'/n)==v for n,v in base.items()),'budgetFileUnchanged':source['src/experimental_swift_reactor/control.rs']==base['src/experimental_swift_reactor/control.rs'],'allOther130FilesUnchanged':all(source[n]==base[n] for n in base if n not in changed),'rootAccountingReview':'pending','independentReview':'pending'})
print(json.dumps(json.loads((H/'source-selection.json').read_text()),indent=2))
