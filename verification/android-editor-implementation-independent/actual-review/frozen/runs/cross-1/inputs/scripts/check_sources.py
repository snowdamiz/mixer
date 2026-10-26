#!/usr/bin/env python3
"""Custody/descriptor checks supplement executable controls; never native or release authorization."""
from pathlib import Path
import json,hashlib,re,datetime
D=Path(__file__).resolve().parents[1];R=D.parents[1]
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
origins=json.loads((D/'source-origins.json').read_text());canonical=[];unchanged=[];changed=[]
allowed={'NativeAppearanceViewsV2.java','NativeRenderer.java','NativeCoordinatorV2.java'}
for name,row in origins.items():
 assert ident(R/name)['sha256']==row['sha256'],('canonical changed',name)
 canonical.append(name)
 if row['copy'].startswith('source/'):
  actual=ident(D/row['copy']);base=Path(name).name
  if base not in allowed:assert actual['sha256']==row['sha256'],('unselected subject changed',name);unchanged.append(base)
  else:changed.append(base)
old=(R/'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java').read_text()
expected=old.replace('return active || cancellation || fence.rendererReportActive;','return active || cancellation || fence.rendererReportActive || renderer.editorDisposalBusyV2();').replace('        if (disposed) return;\n        disposed = true;','        if (disposed || busyForOwnerDisposal()) return;\n        disposed = true;')
assert (D/'source/NativeCoordinatorV2.java').read_text()==expected

def method(text,signature):
 start=text.index(signature);opening=text.index('{',start);depth=1;i=opening+1
 while depth:
  if text[i]=='{':depth+=1
  if text[i]=='}':depth-=1
  i+=1
 return text[start:i]
old=(R/'native/android/app/src/dev/mixer/android/NativeRenderer.java').read_text();new=(D/'source/NativeRenderer.java').read_text()
critical={}
for signature in ['void finishV2(Candidate c,AttachmentJournal journal)','private void requireV2Live()']:
 a,b=method(old,signature),method(new,signature);assert a==b;critical[signature]=hashlib.sha256(a.encode()).hexdigest()
seals=[]
for folder,digest in [('android-editor-cleanup-contract','060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7'),('android-editor-cleanup-contract-independent','ecdc6bd94e2c49b501c2d1dbf69323b8abb3d830c78c689acc39435a31d273c0')]:
 base=R/'verification'/folder;p=base/'seal.json';assert ident(p)['sha256']==digest;j=json.loads(p.read_text())
 for row in j['members']:assert ident(base/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},row['path']
 seals.append({'seal':str(p.relative_to(R)),**ident(p),'verified_members':len(j['members'])})
assert ident(D/'inputs/verification/android-editor-boundary-root-review/cleanup-contract-selection.json')['sha256']=='89fa92964745eaa306e3e2578aeae822a0cd0224c987f06c7b62edecdf8a292e'
assert ident(D/'cross-source/NativeBridge.java')==ident(R/'native/android/app/src/dev/mixer/android/NativeBridge.java')
assert ident(D/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json')==ident(R/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json')
# Compare compiled symbol descriptors, not source spellings.
def descriptors(text):
 lines=text.splitlines();found=set();name=None
 for line in lines:
  if line.strip().startswith('public ') and '(' in line:
   name=line[:line.index('(')].split()[-1]
  elif line.strip().startswith('descriptor:') and name:
   found.add((name,line.split('descriptor:',1)[1].strip()));name=None
 return found
cross=D/'runs/cross-2';official=descriptors((cross/'sdk-descriptors.stdout').read_text());candidate=descriptors((cross/'descriptors.stdout').read_text())
expected={(row['name'],row['descriptor']) for row in json.loads((D/'inputs/verification/android-inputconnection-authority-audit/method-inventory.json').read_text())['methods']}
assert official==expected,('SDK inventory drift',official^expected)
assert expected<=candidate,('missing candidate descriptors',expected-candidate)
source_rows={str(p.relative_to(D)):ident(p) for p in sorted((D/'source').glob('*.java'))}
for p,row in source_rows.items():assert ident(cross/'inputs'/p)==row,('cross source stale',p)
tree=hashlib.sha256(''.join(p+'\0'+row['sha256']+'\n' for p,row in source_rows.items()).encode()).hexdigest()
save(D/'source-check.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'custody and symbol descriptor checks only; executable host controls are separate','canonical_inputs_unchanged':len(canonical),'copied_production_unchanged':unchanged,'allowed_copied_changes':sorted(changed),'new_subject':'source/NativeEditorConnectionV2.java','coordinator_exact_two_edits':True,'critical_bodies_byte_identical':critical,'seals':seals,'official_descriptors':len(expected),'all_candidate_descriptors_present':True,'source_tree_digest':tree,'source_rows':source_rows,'native_or_release_authorization':False})
print('PASS source custody, exact two coordinator edits, unchanged owner/core/SDK guards/finish, 38 compiled descriptors')
