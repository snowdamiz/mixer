#!/usr/bin/env python3
"""Read-only verification of the separately frozen ownership clarification."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=json.loads((HERE/'ownership-addendum-seal.json').read_text())
for row in s['members']:
 p=ROOT/row['path'];assert p.is_relative_to(HERE)
 b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],p
original=(HERE/'seal.json').read_bytes()
assert hashlib.sha256(original).hexdigest()==s['original_independent_seal_sha256']
selected=(ROOT/'verification/swift-cache-state-g6-complete/ledger.py').read_text()
proposed=(ROOT/'verification/swift-cache-state-byte-index-proposal/source_checks.py').read_text()
assert "with t.site(538,'merge caller-only boundary'):" in selected
assert "t.thin('c','merge received c');" in selected
assert "merge received-unit statement continuation; implicit unit/callee return owned G4" in selected
assert 'merge_arg_thin merge_param_thin merge_call' in proposed
assert 'merge_unit_return merge_unit_received' in proposed
assert 'add_row(rows,"G3","merge_view",view("merge_view",True,True))' in proposed
print(json.dumps({'ownership_addendum_seal_sha256':hashlib.sha256((HERE/'ownership-addendum-seal.json').read_bytes()).hexdigest(),
 'all_addendum_members_verified':True,'member_count':len(s['members']),
 'original_independent_seal_unchanged':True,'selected_G6_and_proposed_G3_owner_bindings_verified':True,
 'compiler_or_product_execution':False},indent=2))
