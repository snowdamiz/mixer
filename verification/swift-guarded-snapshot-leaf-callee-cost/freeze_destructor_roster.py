from pathlib import Path
import collections,gzip,hashlib,json,re
H=Path(__file__).resolve().parent;R=H.parents[1];P=H/'constructor-destructor-roster'
sha=lambda b:hashlib.sha256(b).hexdigest()
def out(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
if (P/'seal.json').exists():raise SystemExit('already frozen')
P.mkdir(exist_ok=True)
archive=(R/'verification/swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz').read_bytes();raw=gzip.decompress(archive)
assert sha(archive)=='03b5265c5ae85b3a444f847f1b65af8f31e9fee7697845d6f9699ddf2d8e87e7' and sha(raw)=='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2'
s=raw.decode();bodies=[];rows=[]
for m in re.finditer(r'^fn .*$',s,re.M):
 h=m[0]
 selected=('>::cleanup(_1: experimental_swift_reactor::cache::Partial' in h or '>::construct(_1: &mut experimental_swift_reactor::cache::CacheConstructionPhase' in h or '>::construct_partial(' in h and 'experimental_swift_reactor::cache::CacheConstructionPhase' in h or h.startswith('fn construct_profile_core_v1(') or '>::complete(_1: experimental_swift_reactor::cache::CacheConstructionPhase' in h)
 if not selected:continue
 end=re.search(r'^}\n',s[m.start():],re.M);b=s[m.start():m.start()+end.end()];bodies.append(b)
 args=h.split('(',1)[1].rsplit(') -> ',1)[0];roles=dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',args)+re.findall(r'let (?:mut )?(_\d+): (.*);',b));sites=[]
 for line,code in enumerate(b.splitlines(),1):
  z=re.search(r'\bdrop\((_\d+)\)',code)
  if z:sites.append(dict(line=line,kind='raw-MIR-drop',operand=z[1],compiler_type=roles[z[1]],code=code.strip()))
  z=re.search(r'std::mem::drop::<(.+)>\(',code)
  if z:sites.append(dict(line=line,kind='explicit-std-drop',compiler_type=z[1],code=code.strip()))
  if 'drop_reserved::<' in code or 'drop_proof_with_wasi(' in code:sites.append(dict(line=line,kind='authored-drop-forwarding',code=code.strip()))
 rows.append(dict(header=h,MIR_sha256=sha(b.encode()),body_max_occurrences=1,sites=sites))
assert len(rows)==5
ledger=json.loads((H/'callee-ledger.json').read_text());cuts=ledger['constructor_applicability']['typed_internal_destructor_cuts']
out(P/'roster.json',dict(schema=1,source_tree_sha256=ledger['source_tree_sha256'],whole_MIR_sha256=sha(raw),whole_MIR_archive_sha256=sha(archive),unit='typed destructor invocations; actual body price imported from separate payload/resource interface',constructor_cut='accepted_constructor_region',body_occurrences=rows,typed_cuts=cuts,Partial_type='crate::experimental_swift_reactor::cache::Partial',Partial_fields=dict(adopted='Option<AdoptedProof>',slots='Vec<SwiftSlot>',pins='Vec<crate::experimental::cache::PinRecord>',patches='Vec<crate::experimental::cache::decode::Patch>',index='Vec<u8>',plans='Vec<Option<crate::experimental_swift_reactor::cache::ScanPlan>>',buffers='[Option<ReservationTicket>; 3]',header='Option<ReservationTicket>'),partial_count_derivation=dict(cleanup_raw_self=2,cleanup_drop_reserved_self=1,construct_raw_partial=2),each_vector_count_derivation=dict(cleanup_actual_vector_destructor=1,construct_raw_unwind_vector=1),adopted_count_derivation=dict(cleanup_raw_unwind=1,construct_raw_adopted=2,construct_profile_core_raw_adopted=1),semantic_empty_phase_return_carriers='preparation and original_return have both been taken before either phase.complete call; the tuple contains None values, not an owned cache/proof',inline_only_phase_storage='SnapshotPhaseStorage contains only plan/shape/scalars, Option<[u8;4096]> and Copy admission error; SnapshotAccess/SnapshotBranch contain borrows/Copy errors; no resource payload body imported',all_written_alternatives_not_simultaneous_owners=True,no_payload_destructor_body_priced_here=True,actual_runtime=False))
(P/'selected-constructor.mir').write_text('\n'.join(bodies))
(P/'README.md').write_text('Frozen source146 constructor internal destructor frontier. The scalar source envelope prices drop events only. These positive typed destructor interfaces preserve actual resource destruction separately. Multiplicities are conservative sums of written normal/unwind sites in five bodies, each occurring at most once in the closed fresh-constructor route. They do not infer simultaneous owners or twice-destroyed live storage. Actual payload body pricing belongs to the separate resource lane. No compiler/product/native/UI process ran.\n')
ms=[dict(path=str(p.relative_to(P)),bytes=len(p.read_bytes()),sha256=sha(p.read_bytes())) for p in sorted(P.rglob('*')) if p.is_file()]
out(P/'seal.json',dict(schema=1,member_count=len(ms),members=ms,tree_sha256=sha(json.dumps(ms,sort_keys=True,separators=(',',':')).encode()),scope='frozen-constructor-typed-destructor-frontier-only'))
print(json.dumps(dict(path=str(P.relative_to(R)),seal_sha256=sha((P/'seal.json').read_bytes()),members=len(ms),bytes=sum(m['bytes'] for m in ms))))
