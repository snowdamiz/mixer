#!/usr/bin/env python3
"""Freeze input custody and prepare a data-only Rust host layout proposal."""
from pathlib import Path
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREP = ROOT / 'verification/swift-profile-header-preparation'
INDEPENDENT = ROOT / 'verification/swift-profile-header-contract-independent'

def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(p, j): p.write_text(json.dumps(j, indent=2, sort_keys=True)+'\n')
def member(p, rel):
    b=p.read_bytes(); return {'path':str(rel),'bytes':len(b),'sha256':sha(b)}
def seal_check(base, expected):
    b=(base/'seal.json').read_bytes(); assert sha(b)==expected
    j=json.loads(b)
    for m in j['members']:
        p=base/m['path']; assert member(p,m['path'])==m
    assert sum(m['bytes'] for m in j['members'])==j['total_bytes']
    assert len(j['members'])==j['member_count']
    return {'path':str(base.relative_to(ROOT)), 'seal_sha256':sha(b),
            'members_verified':j['member_count'],'bytes_verified':j['total_bytes']}

def main():
    custody={'schema':1,'scope':'Exact frozen inputs; source hashes are authority; no implementation acceptance'}
    custody['preparation']=seal_check(PREP,'aee8ffbe028f9fe3084a62a81fe0946dc6a21cc132e16d83915917cf6657515f')
    custody['independent']=seal_check(INDEPENDENT,'3addafb44d2be614b7d859c8a329775ab7e7651d6078202686abc0430f2e5821')
    assigned={
      'profile-header-amendment-selection.json':'31be99a2e0382267db3eb4722b322aec60369aeaaa3b54b323254aee37791b30',
      'profile-header-selected-amendments.md':'f69ded16e8bf3608fb87cf2a971733cd1f32d1a6652876d801f10253c03051a7',
      'selected-host-budget.json':'d02b60e1d7a8eba90963e78fe666345898ebc0cac431ca2efc554ae02f8800b3',
      'profile-adapter-acceptance.json':'ee3ef423db5e404b58ab86c1e1123a81113e542c6af8b691e37f5932b3e42381'}
    custody['root_inputs']=[]
    for name,h in assigned.items():
        p=ROOT/'verification/swift-semantic-adapter-root-review'/name
        b=p.read_bytes(); assert sha(b)==h
        q=OUT/'inputs/root'/name; q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
        custody['root_inputs'].append(member(q,q.relative_to(OUT)))
    for name in ['contract.json','proposed-contract.md','test-plan.md','source-review.md','closure-comparison.json']:
        q=OUT/'inputs/preparation'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PREP/name,q)
    for name in ['review.md','continuation-shape.md','required-amendments.json']:
        q=OUT/'inputs/independent'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(INDEPENDENT/name,q)
    comparison=json.loads((PREP/'closure-comparison.json').read_text())
    source=OUT/'source/vm'
    if source.exists(): shutil.rmtree(source)  # Sole owned generated source copy.
    source.mkdir(parents=True,exist_ok=True)
    baseline=[]
    for m in comparison['canonical_members']:
        src=PREP/'inputs/vm'/m['path'];assert member(src,m['path'])==m
        q=source/m['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(src.read_bytes());baseline.append(m)
    rowbase=PREP/'inputs/verification/swift-cache-state-profile-adapter/source/vm'
    rowmembers={m['path']:m for m in comparison['row_source_members']}
    for name in comparison['row_added']+comparison['row_changed']:
        src=rowbase/name;assert member(src,name)==rowmembers[name]
        q=source/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(src.read_bytes())
    custody['canonical']=baseline
    custody['row_additions_and_module_delta']=[rowmembers[n] for n in comparison['row_added']+comparison['row_changed']]
    custody['unmerged_archived_instrumentation']=comparison['completion_changed']
    custody['base_distribution_count']=134
    write_json(OUT/'input-custody.json',custody)
    base=[member(p,p.relative_to(source)) for p in sorted(source.rglob('*')) if p.is_file()]
    write_json(OUT/'base-source-manifest.json',{'schema':1,'members':base,'member_count':len(base)})
    assert len(base)==134
    cachepath=source/'src/experimental_swift_reactor/cache.rs'
    cache=cachepath.read_text()
    # This lexical extraction names existing complete types only. rustc measures
    # the types; no syntax inspection supplies a runtime/owner/OTA decision.
    region=cache[cache.index('const fn compute_cache_cleanup_temporary_bytes'):cache.index('// Whole existing foundation slots')]
    types=[];start=0
    while True:
        at=region.find('size_of::<',start)
        if at<0:break
        i=at+len('size_of::<');j=i;depth=1
        while depth:
            if region[j]=='<':depth+=1
            if region[j]=='>':depth-=1
            j+=1
        t=' '.join(region[i:j-1].split());start=j
        if t not in types:types.append(t)
    extra=[
      'RuntimeControl','AccountedWasi','AdoptedProof','ValidatedSwiftReactor','SwiftSlot','PinRecord','decode::Patch','ScanPlan',
      'Option<ScanPlan>','ReservationTicket','SwiftRunBudget','ProfileHeaderErrorV1','InitialProfileScalarsV1',
      'UnverifiedProfileDigestBytesV1','UnverifiedProfileHeaderV1',"InitialProfileBorrowV1<'static>",
      'ProfileAdmissionFailureV1','InitialProfileConstructionOutcomeV1',
      'Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>','ProfileRowsObservationV1','ProfileAdapterErrorV1',
      'Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>',
      'Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>',
      "Result<InitialProfileBorrowV1<'static>, ProfileAdmissionFailureV1>",
      'Option<InitialProfileConstructionOutcomeV1>',
      "Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>",
      "(Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>, ConstructionReturnSlot)",
      'Option<CacheConstructionFailure>',"WrapperArgumentsV1<'static>","WrapperPhaseStorageV1<'static>",
      "WrapperEmissionStorageV1<'static>",'WrapperCallerStorageV1','WrapperMoveStorageV1',
      'SelectedInitialProfileV1','SelectedLocalStructureV1','LocalTypeLayoutV1',
      'File','std::fs::Metadata','std::io::Error','Result<(), std::io::Error>',
      'Result<usize, std::io::Error>','Result<u64, std::io::Error>',
      'Result<std::fs::Metadata, std::io::Error>','[u8; 4096]','[u8; 512]',
      'Option<AdoptedProof>','Option<AccountedWasi>',"&'static SelectedInitialProfileV1",
      "&'static mut Option<SwiftFunctionCache>","&'static mut File",'u64','usize']
    for t in extra:
        if t not in types:types.append(t)
    model=(OUT/'protocol-types.rs').read_text().replace('__LAYOUT_ENTRY_COUNT__',str(len(types)))
    lines=['pub(super) fn emit_layout_v1() {']
    for i,t in enumerate(types,1):
        lines.append(f'    println!("TYPE\\t{i}\\t{{}}\\t{{}}\\t{{}}", {json.dumps(t)}, std::mem::size_of::<{t}>(), std::mem::align_of::<{t}>());')
    for name,expr in [('cache_cleanup_temporary_bytes','cache_cleanup_temporary_bytes().unwrap()'),('cache_header_bytes','cache_header_bytes().unwrap()'),('cache_construction_bytes','cache_construction_bytes().unwrap()'),('cache_operation_bytes','cache_operation_bytes().unwrap()'),('cache_fixed_64_slots_64_pins','cache_header_bytes().unwrap()+64*size_of::<SwiftSlot>()+64*size_of::<PinRecord>()+512*size_of::<decode::Patch>()')]:
        lines.append(f'    println!("VALUE\\t{name}\\t{{}}", {expr});')
    lines.append('}')
    model+='\n'+'\n'.join(lines)+'\n'
    path=source/'src/experimental_swift_reactor/cache/initial_profile_protocol_layout.rs';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(model)
    cachepath.write_text(cache+'\n// Isolated data-only host layout model; no product construction path.\n#[cfg(mixer_initial_profile_layout_probe)]\n#[path = "cache/initial_profile_protocol_layout.rs"]\nmod initial_profile_protocol_layout;\n#[cfg(mixer_initial_profile_layout_probe)]\npub(super) fn emit_initial_profile_layout_v1() { initial_profile_protocol_layout::emit_layout_v1(); }\n')
    mod=source/'src/experimental_swift_reactor/mod.rs'
    mod.write_text(mod.read_text()+'\n#[cfg(mixer_initial_profile_layout_probe)]\npub(crate) fn emit_initial_profile_layout_v1() { cache::emit_initial_profile_layout_v1(); }\n')
    lib=source/'src/lib.rs';lib.write_text(lib.read_text()+'\n#[cfg(mixer_initial_profile_layout_probe)]\npub fn emit_initial_profile_layout_v1() { experimental_swift_reactor::emit_initial_profile_layout_v1(); }\n')
    binpath=source/'src/bin/initial-profile-layout-probe.rs';binpath.parent.mkdir(parents=True,exist_ok=True);binpath.write_text('fn main() { mixer_vm::emit_initial_profile_layout_v1(); }\n')
    final=[member(p,p.relative_to(source)) for p in sorted(source.rglob('*')) if p.is_file()]
    write_json(OUT/'probe-source-manifest.json',{'schema':1,'member_count':len(final),'members':final,
        'tree_definition':'SHA256 sorted full relative string path TAB bytes TAB sha256 LF',
        'tree_sha256':sha(''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in sorted(final,key=lambda m:m['path'])).encode()),
        'scope':'Isolated data-only layout model; not product implementation or integration',
        'modified_from_base':['src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/mod.rs','src/lib.rs'],
        'added_to_base':['src/experimental_swift_reactor/cache/initial_profile_protocol_layout.rs','src/bin/initial-profile-layout-probe.rs']})
    write_json(OUT/'local-layout-type-index.json',{'schema':1,'entry_count':len(types),'types':[{'id':i,'type':t} for i,t in enumerate(types,1)]})
    print(f'verified preparation200 + independent35; fresh canonical132 + row2; probe={len(final)} members; {len(types)} complete type measurements selected for proposal')

if __name__=='__main__':main()
