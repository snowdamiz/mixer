#!/usr/bin/env python3
"""Source custody and delta only; not a compiler or semantic authorization."""
from pathlib import Path
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-implementation'
ALLOWED={'src/experimental_swift_reactor/cache/initial_profile_v1.rs',
         'src/experimental_swift_reactor/retained_profile_loader_v1.rs'}
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(rows):return sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())
def rows(base):return [{'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(base.rglob('*')) if p.is_file()]
def write(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
old=json.loads((PRODUCER/'final-source-manifest.json').read_text())
current=rows(HERE/'source/vm');assert len(current)==old['member_count']==146
assert set(r['path'] for r in current)==set(r['path'] for r in old['members'])
before={r['path']:r for r in old['members']}
changed=[r['path'] for r in current if r!=before[r['path']]]
assert set(changed)==ALLOWED
host=rows(HERE/'source/host');assert len(host)==11;assert host==rows(PRODUCER/'source/host')
assert next(r for r in current if r['path'].endswith('/host_account_v1.rs'))==next(r for r in old['members'] if r['path'].endswith('/host_account_v1.rs'))
loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
anchor='// Actual private ownership core.'
assert (PRODUCER/'source/vm'/loader).read_text().split(anchor)[0]==(HERE/'source/vm'/loader).read_text().split(anchor)[0]
assert (HERE/'historical-independent/retirement_witness.inc.rs').read_text() in (HERE/'source/vm'/loader).read_text()
patch=[]
for name in changed:
    patch.extend(difflib.unified_diff((PRODUCER/'source/vm'/name).read_text().splitlines(keepends=True),(HERE/'source/vm'/name).read_text().splitlines(keepends=True),fromfile='frozen/'+name,tofile='correction/'+name))
(HERE/'source-delta.patch').write_text(''.join(patch))
write('source-manifest.json',{'schema':1,'member_count':146,'members':current,'tree_sha256':digest(current),'changed':changed})
write('host-manifest.json',{'schema':1,'member_count':11,'members':host,'tree_sha256':digest(host),'unchanged':True})
write('source-audit.json',{'schema':1,'kind':'source-custody-only','distribution_members':146,'support_members':11,'changed':changed,'host_account_unchanged':True,'loader_prefix_and_original_validators_unchanged':True,'exact_original_independent_desired_property_witness_embedded':True,'source_tree':digest(current),'host_tree':digest(host),'semantic_authorization':False,'compiler_execution':False,'native_fixture_execution':False})
print(json.dumps({'source146':digest(current),'host11':digest(host),'changed':changed}))
