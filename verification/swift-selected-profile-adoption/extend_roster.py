#!/usr/bin/env python3
"""Append measured roster identities with refusing placeholders before measurement."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
S=ROOT/'source/vm/src/experimental_swift_reactor'
roster=json.loads((ROOT/'appended-layout-types.json').read_text())
# The explicit test encoding is field-by-field little endian, never object bytes.
roster.append({'id':201,'name':'FullProvenanceEncoding','definition_site_type':'[u8;496]'})
(ROOT/'appended-layout-types.json').write_text(json.dumps(roster,indent=2)+'\n')
def edit(name,old,new):
 p=S/name;s=p.read_text();assert s.count(old)==1,(name,old[:60],s.count(old));p.write_text(s.replace(old,new))
edit('retained_profile_loader_v1.rs','ADOPTION_LAYOUTS_V1: [(&str,usize,usize); 35]','ADOPTION_LAYOUTS_V1: [(&str,usize,usize); 36]')
edit('retained_profile_loader_v1.rs','    ("AdoptionCleanupPlacesV1",super::control::ADOPTION_CLEANUP_BYTES_V1,super::control::ADOPTION_CLEANUP_ALIGNMENT_V1),','    ("AdoptionCleanupPlacesV1",super::control::ADOPTION_CLEANUP_BYTES_V1,super::control::ADOPTION_CLEANUP_ALIGNMENT_V1),\n    ("FullProvenanceEncoding",std::mem::size_of::<[u8;496]>(),std::mem::align_of::<[u8;496]>()),')
edit('cache/initial_profile_v1.rs','type_layout:[LocalTypeLayoutV1;165]','type_layout:[LocalTypeLayoutV1;201]')
edit('cache/initial_profile_v1/local_structure.rs','selected.entries!=165','selected.entries!=201')
edit('cache/initial_profile_v1/local_structure.rs',' Ok(())\n}', ''' for (index,(_,bytes,alignment)) in super::super::super::retained_profile_loader_v1::ADOPTION_LAYOUTS_V1.iter().enumerate() {
  let entry=&selected.type_layout[165+index];
  if entry.id!=(166+index) as u32 || entry.reserved!=0 || entry.bytes!=*bytes as u64 || entry.alignment!=*alignment as u64 {return Err(refuse());}
 }
 Ok(())
}''')
for name in ['cache/initial_profile_v1/selected.rs','cache/initial_profile_v1/tests.rs']:
 edit(name,'  entries:165,','  entries:201,')
 suffix=''.join(f'   LocalTypeLayoutV1 {{id:{e["id"]},reserved:0,bytes:0,alignment:0}}, // prospective: {e["name"]}\n' for e in roster)
 edit(name,'   LocalTypeLayoutV1 {id:165,reserved:0,bytes:8,alignment:8},','   LocalTypeLayoutV1 {id:165,reserved:0,bytes:8,alignment:8},\n'+suffix)
edit('cache/initial_profile_v1/tests.rs',' row!(165,usize);',''' row!(165,usize);
 for (index,(name,bytes,alignment)) in super::super::super::retained_profile_loader_v1::ADOPTION_LAYOUTS_V1.iter().enumerate() {
  println!("TYPE\\t{}\\t{}\\t{}\\t{}",166+index,name,bytes,alignment);
 }''')
edit('cache/initial_profile_v1.rs','\nmod header;', '''
// Before prepare, all wrapper ingress and retained output/return places must
// already have a foundation floor; a later cache phase cannot grant it back.
pub(super) const WRAPPER_SOURCE_PLACES_V1: usize =
    size_of::<WrapperArgumentsV1<'static>>() + size_of::<WrapperPhaseStorageV1<'static>>()
    + size_of::<WrapperEmissionStorageV1<'static>>() + size_of::<WrapperCallerStorageV1>()
    + size_of::<WrapperMoveStorageV1>();

mod header;''')
edit('cache.rs','mod initial_profile_v1;','''mod initial_profile_v1;
pub(super) const INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1: usize = initial_profile_v1::WRAPPER_SOURCE_PLACES_V1;
#[cfg(test)]
pub(super) fn test_selected_initial_outcome_v1(
    selected: super::retained_profile_loader_v1::SelectedValidatedProfileV1, case: &str,
) { initial_profile_v1::tests::selected_owner_outcome_v1(selected,case); }''')
edit('control.rs','let terms: [(usize, usize); 12]','let terms: [(usize, usize); 13]')
edit('control.rs','        (1, ADOPTION_CLEANUP_BYTES_V1),','        (1, ADOPTION_CLEANUP_BYTES_V1),\n        (1, super::cache::INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1),')
# Production-independent source layout probe calls the exact reporting method;
# unit and host report actual layouts before the existing selected comparison.
print('original165 IDs retained; appended36 identities placeholder-refuse until measured; wrapper floor composed')
