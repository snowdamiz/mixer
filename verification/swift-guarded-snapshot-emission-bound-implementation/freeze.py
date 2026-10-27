#!/usr/bin/env python3
"""Freeze/check the compact unused emission candidate and bounded receipts."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
I='overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs'
H='overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
ROSTER=['README.md','prepare.py','run.py','verify.py','freeze.py','source-delta.patch',
 'source-manifest.json','input-custody.json','derivation.json','helper-type-layouts.json',
 'run-results.json','verification-results.json','rustc-version.txt','helper-source-roles.json',
 'host-input-reconstruction.json','final-commands.json','host/arithmetic.rs','host/source-types.rs',I,H]
for case in ['host-debug-compile','host-debug-run','host-optimized-compile','host-optimized-run',
             'host-negative-coefficient-compile','host-negative-coefficient-run',
             'metadata-debug','metadata-optimized','metadata-negative-type']:
 for name in ['receipt.json','stdout','stderr']:ROSTER.append('commands/'+case+'/'+name)
for case in ['host-debug','host-optimized','host-negative-coefficient','metadata-debug','metadata-optimized','metadata-negative-type']:
 ROSTER.append('commands/'+case+'/cleanup.json')
for case in ['metadata-debug','metadata-optimized']:
 ROSTER.append('commands/'+case+'/artifact.json')
for case in ['metadata-debug','metadata-optimized','metadata-negative-type']:
 ROSTER.append('commands/'+case+'.preimage.json')
def sha(raw):return hashlib.sha256(raw).hexdigest()
actual=sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()
              and p.name not in ('seal.json','freeze-receipt.json'))
assert actual==sorted(ROSTER),('unexpected/missing member',actual)
assert not (HERE/'owned-work').exists()
members=[]
for name in sorted(ROSTER):
 raw=(HERE/name).read_bytes();members.append({'path':name,'bytes':len(raw),'sha256':sha(raw)})
tree=sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())
seal={'schema':1,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),
 'members':members,'tree_sha256':tree,
 'scope':'Unused private checked emission arithmetic candidate over authority225/source144; isolated145 overlay with descriptor mismatch explicit; pure arithmetic Rust tests and metadata only; no product runtime/work/storage selection'}
if '--check' in sys.argv:assert json.loads((HERE/'seal.json').read_text())==seal
else:
 (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
 (HERE/'freeze-receipt.json').write_text(json.dumps({'schema':1,
   'seal_sha256':sha((HERE/'seal.json').read_bytes()),'member_count':len(members),'tree_sha256':tree,
   'WorkAuditPending_preserved':True,'actual_callsite_added':False,
   'operational_emission_selected':False,'owner_storage_recipe_edited':False,
   'loader_descriptor_binding_selected':False,'owned_scratch_removed':True},indent=2,sort_keys=True)+'\n')
print(json.dumps({'members_verified':len(members),'tree_sha256':tree,
 'seal_sha256':sha((HERE/'seal.json').read_bytes())},sort_keys=True))
