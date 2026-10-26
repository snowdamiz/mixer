#!/usr/bin/env python3
"""Verify selected immutable inputs and copy an explicit complete-source closure."""
from pathlib import Path
import hashlib,json,shutil,datetime
D=Path(__file__).resolve().parent; R=D.parents[1]
if (D/'seal.json').exists():raise SystemExit('Frozen packet is immutable')
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
inputs={
 'verification/android-editor-boundary-root-review/focus-history-selection.json':'3aaaf7d804a9ee531e05062b137ba869755fb8618fc0bc5ace0ca3c66d4384d4',
 'verification/android-editor-boundary-root-review/focus-history-amendment.md':'736476a269fae9a6745fbfbd5413a7ef231f57f9254c3279e41c2921d2088833',
 'verification/android-editor-boundary-root-review/cleanup-contract-selection.json':'89fa9296',
 'verification/android-editor-cleanup-contract-independent/required-addendum.md':'6e2dc0989eeb7c6c61a9c8f1c08934b0a637a0c2bf60ba2bc4ecf636593ea5bb',
 'verification/android-editor-boundary-root-review/replacement-amendment.md':'b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b',
 'verification/android-editor-boundary-root-review/replacement-dispatch-amendment.md':'eb35fe8f9c9d9ee093ad0f40d687fbd2b4fb4382dc32cd7a74acbcc98c5da6ff',
 'verification/android-editor-replacement-implementation/seal.json':'4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3',
 'verification/android-editor-replacement-independent/actual-review/findings-focus-history/seal.json':'a6d68fe3efd4d406b7817c73fc6307b2bb505dd07a168df900410246a5020885',
}
verified=[]
for name,digest in inputs.items():
 p=R/name;info=identity(p);assert info['sha256'].startswith(digest),(name,info)
 verified.append({'path':name,**info})
 if p.name=='seal.json':
  members=json.loads(p.read_text())['members']
  for row in members:
   assert identity(p.parent/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},row['path']
  verified[-1]['members_verified']=len(members)
 target=D/'inputs'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
base=R/'verification/android-editor-replacement-implementation'
for folder in ('source','host-leaves','tests','cross-source'):
 shutil.copytree(base/folder,D/folder)
descriptor=base/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
shutil.copy2(descriptor,D/'descriptor.json')
findings=R/'verification/android-editor-replacement-independent/actual-review/findings-focus-history'
shutil.copytree(findings,D/'historical/findings-focus-history')
for name in ('AdditionalReplacementControls.java','ReplacementReviewControls.java','DescriptorClosure.java'):
 shutil.copy2(findings/'controls'/name,D/'tests'/name)
save(D/'input-custody.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified':verified,'copy_scope':'Explicit source, authored Android/JNI leaves, producer tests, independent controls and immutable finding witnesses only; no frozen authoring generator imported/executed','native_or_capture_started_or_queried':False})
save(D/'baseline-source-map.json',{str(p.relative_to(D)):identity(p) for folder in ('source','host-leaves','tests','cross-source') for p in sorted((D/folder).rglob('*')) if p.is_file()})
print('verified inputs and copied explicit closure')
