#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys,datetime
H=Path(__file__).resolve().parent
R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
B=R/'verification/swift-exact-reactor-after-grouped-index/baseline-manifest.json'
assert sha(B)=='3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f'
manifest=json.loads(B.read_text());assert len(manifest)==132
for name,digest in manifest.items():
 p=R/'vm'/name;assert sha(p)==digest,(name,'live source drift')
 for lane in ('baseline','source'):
  d=H/lane/name;d.parent.mkdir(parents=True,exist_ok=True);assert not d.exists();shutil.copyfile(p,d)
shutil.copyfile(B,H/'baseline-manifest.json')
save(H/'preparation.json',{'sourceRevision':'4a28261b333c28b4fce386f370a19b93e735c8d2','baselineClosure':sha(B),'copiedFiles':len(manifest),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'finite isolated host prototype only','liveSourceChanged':False,'networkNativeUIPhonesGitFullReactor':False,'ownership':['docs/swift-decode-plan-reuse-diagnosis.md','verification/swift-decode-plan-reuse-diagnosis/**']})
print('copied and verified',len(manifest),'files per lane')
