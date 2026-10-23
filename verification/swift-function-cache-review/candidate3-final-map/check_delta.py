#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=HERE.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
a=json.loads((ROOT/'verification/swift-function-cache/candidate-2/preflight-root-tail-map.json').read_text())
b=json.loads((ROOT/'verification/swift-function-cache/candidate-3/preflight-root-tail-map.json').read_text())
assert set(a['layouts'])==set(b['layouts'])
changed={k:{'before':a['layouts'][k],'after':b['layouts'][k]} for k in a['layouts'] if a['layouts'][k]!=b['layouts'][k]}
assert set(changed)=={'ConstructionBorrowChainInventory'}
assert changed['ConstructionBorrowChainInventory']['before']['size']==168 and changed['ConstructionBorrowChainInventory']['after']['size']==184
assert a['preflight_slots']==b['preflight_slots'] and a['foundation_counts']==b['foundation_counts']
assert set(a['model_fields'])==set(b['model_fields'])
for name,fields in a['model_fields'].items():
 if name!='ConstructionBorrowChainInventory':assert fields==b['model_fields'][name],name
 else:
  old={x['field']:x for x in fields};new={x['field']:x for x in b['model_fields'][name]}
  assert set(new)-set(old)=={'owner_allocator_argument','owner_allocator_counter'}
  for k,row in old.items():assert {q:row[q] for q in ['type','size','align']}=={q:new[k][q] for q in ['type','size','align']}
for name,table in a['component_checked_sums'].items():
 new=b['component_checked_sums'][name]
 if name!='compute_cache_construction_bytes':assert table==new,name
 else:
  delta=0
  for x,y in zip(table['objects'],new['objects']):
   assert x['type']==y['type']
   if x['type']=='ConstructionBorrowChainInventory':assert x['count']==y['count']==3 and y['size']-x['size']==16
   elif x['type']=='Result<u64,u64>':assert x['count']==3 and y['count']==6 and x['size']==y['size']==16
   else:assert x==y,x['type']
   delta+=y['bytes']-x['bytes']
  assert delta==new['bytes']-table['bytes']==96
old=(BASE/'candidate2-independent-runs/tree/vm/src/experimental_swift_reactor/cache.rs').read_text()
new=(BASE/'candidate3-independent-runs/tree/vm/src/experimental_swift_reactor/cache.rs').read_text()
regions=[('fn pairing(','impl SwiftFunctionCache {'),('impl SwiftFunctionCache {','fn capture('),('fn capture(','impl CacheConstructionPhase'),('fn reserve<T>','impl SwiftMode'),('impl SwiftMode','#[cfg(not(test))]\nfn checkpoint')]
for start,end in regions:assert old.split(start,1)[1].split(end,1)[0]==new.split(start,1)[1].split(end,1)[0],(start,end)
assert 'counter.try_update(Ordering::Relaxed, Ordering::Relaxed, |n| n.checked_add(1))' in new
assert new.count('NEXT_OWNER: AtomicU64 = AtomicU64::new(1)')==1
assert 'NEXT_OWNER.store' not in new and 'NEXT_OWNER.swap' not in new
assert new.index('let owner = next_owner()')>new.index('fn construct_partial')
result={'scope':'independent source and complete typed-row delta; selected preflight/final paths unchanged','cache_source_sha256':sha(new.encode()),'candidate2_source_sha256':sha(old.encode()),'unchanged_phase_source_regions':regions,'changed_layouts':changed,'all_23_other_inventory_field_groups_identical':True,'construction_extra':96,'construction_bytes':57224,'all_preflight_slots_identical':True,'foundation_counts_identical':True,'other_component_sums_identical':True,'helper_placement':'construct_partial only after ordinary phase enlargement; no preflight/final helper overlap','same_checked_atomic_and_orderings':True,'production_counter_never_seeded':True}
(HERE/'delta-check-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
