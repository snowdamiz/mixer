#!/usr/bin/env python3
"""Custody and compiled descriptors supplement actual-source execution, not release authority."""
from pathlib import Path
import datetime,hashlib,json,sys
D=Path(__file__).resolve().parents[1];R=D.parents[1];B=R/'verification/android-editor-implementation'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def verified_seal(base,expected):
 p=base/'seal.json';assert ident(p)['sha256']==expected,('seal changed',str(p))
 rows=json.loads(p.read_text())['members']
 for row in rows:assert ident(base/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},('sealed member changed',str(base/row['path']))
 return {'path':str(p.relative_to(R)),**ident(p),'verified_members':len(rows),'verified_bytes':sum(r['bytes'] for r in rows)}
seals=[]
for base,digest in [
 (B,'99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd'),
 (R/'verification/android-editor-cleanup-contract','060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7'),
 (R/'verification/android-editor-cleanup-contract-independent','ecdc6bd94e2c49b501c2d1dbf69323b8abb3d830c78c689acc39435a31d273c0'),
 (D/'inputs/verification/android-editor-implementation-independent/replacement-preaccess','89fef50e796ef1e1952301be04554e09404f2d00a3d6926a73dacfed0554728a'),
 (D/'historical/findings-1','f6d6c1be1278a8e40d4bedd8bfc55d64d32ce002b53e745fa099b0322268fbf2')]:seals.append(verified_seal(base,digest))
selected={
 'cleanup-contract-selection.json':'89fa92964745eaa306e3e2578aeae822a0cd0224c987f06c7b62edecdf8a292e',
 'replacement-amendment.md':'b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b',
 'replacement-dispatch-amendment.md':'eb35fe8f9c9d9ee093ad0f40d687fbd2b4fb4382dc32cd7a74acbcc98c5da6ff'}
for name,digest in selected.items():
 rel=Path('verification/android-editor-boundary-root-review')/name
 assert ident(D/'inputs'/rel)['sha256']==digest
 assert ident(R/rel)['sha256']==digest
origins=json.loads((B/'source-origins.json').read_text());canonical=[]
for name,row in origins.items():
 if row['copy'].startswith('source/'):
  assert ident(R/name)['sha256']==row['sha256'],('canonical Android source changed',name)
  canonical.append(name)
unchanged=[];changes=[]
for p in sorted((D/'source').glob('*.java')):
 if ident(p)==ident(B/'source'/p.name):unchanged.append(p.name)
 else:changes.append(p.name)
assert changes==['NativeAppearanceViewsV2.java','NativeRenderer.java'],changes
# The original copied coordinator already had exactly its two selected disposal guard edits.
assert ident(D/'source/NativeCoordinatorV2.java')==ident(B/'source/NativeCoordinatorV2.java')
assert ident(D/'cross-source/NativeBridge.java')==ident(B/'cross-source/NativeBridge.java')==ident(R/'native/android/app/src/dev/mixer/android/NativeBridge.java')
assert ident(D/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json')==ident(R/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json')
def method(s,signature):
 start=s.index(signature);o=s.index('{',start);depth=1;i=o+1
 while depth:
  if s[i]=='{':depth+=1
  if s[i]=='}':depth-=1
  i+=1
 return s[start:i]
critical={};a=(B/'source/NativeRenderer.java').read_text();b=(D/'source/NativeRenderer.java').read_text()
for signature in ('void finishV2(Candidate c,AttachmentJournal journal)','private void requireV2Live()'):
 old,new=method(a,signature),method(b,signature);assert old==new;critical[signature]=hashlib.sha256(old.encode()).hexdigest()
cross=D/'runs/cross-2';host=D/'runs/host-8'
for p in (D/'source').glob('*.java'):
 assert ident(p)==ident(cross/'inputs/source'/p.name)==ident(host/'inputs/source'/p.name),('stale executable input',p.name)
for folder in ('host-leaves','tests','cross-source'):
 for p in (D/folder).rglob('*'):
  if p.is_file():assert ident(p)==ident(host/'inputs'/p.relative_to(D)),('stale host closure',str(p))
def descriptors(s):
 found=set();name=None
 for line in s.splitlines():
  if line.strip().startswith('public ') and '(' in line:name=line[:line.index('(')].split()[-1]
  elif line.strip().startswith('descriptor:') and name:found.add((name,line.split('descriptor:',1)[1].strip()));name=None
 return found
inventory=json.loads((D/'inputs/verification/android-inputconnection-authority-audit/method-inventory.json').read_text())
expected={(r['name'],r['descriptor']) for r in inventory['methods']}
official=descriptors((cross/'sdk-descriptors.stdout').read_text());actual=descriptors((cross/'descriptors.stdout').read_text())
assert official==expected and len(expected)==38,('SDK descriptor drift',official^expected)
assert expected<=actual,('missing compiled adapter descriptor',expected-actual)
oldgroups=[line for line in (B/'runs/host-13/host.stdout').read_text().splitlines() if line.startswith('PASS ')][:38]
newgroups=[line for line in (host/'host.stdout').read_text().splitlines() if line.startswith('PASS ')][:38]
assert oldgroups==newgroups,('prior 38 group inventory changed',set(oldgroups)^set(newgroups))
rows={str(p.relative_to(D)):ident(p) for p in sorted((D/'source').glob('*.java'))}
tree=hashlib.sha256(''.join(k+'\0'+v['sha256']+'\n' for k,v in rows.items()).encode()).hexdigest()
save(D/'source-check.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'custody, exact unchanged bodies and compiled descriptor inventory only; actual-source execution is separate','seals':seals,'selected_inputs':selected,'canonical_Android_source_unchanged':canonical,'derivative_changed_from_original':changes,'derivative_unchanged_from_original':unchanged,'coordinator_unchanged_from_original_selected_two_guards':True,'critical_bodies_byte_identical':critical,'official_InputConnection_descriptors':len(expected),'all_candidate_descriptors_present':True,'prior_38_control_group_inventory_preserved':True,'final_host':'runs/host-8','final_cross':'runs/cross-2','product_source_tree_digest':tree,'product_source':rows,'native_or_release_authorization':False})
print('PASS original packet and selected seals immutable; source custody, unchanged owner/core/coordinator/SDK guards/finish; 38 compiled descriptors and prior groups')
