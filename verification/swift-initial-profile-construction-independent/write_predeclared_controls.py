#!/usr/bin/env python3
"""Materialize fixed independent review controls before candidate access."""
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def emit(n,d):
 p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 amendment=ROOT/'verification/swift-semantic-adapter-root-review/initial-profile-compile-placement-amendment.md'
 assert sha(amendment.read_bytes())=='fc367c1745e1c7b80d758ba1edd4d0df226053654d4dd054d284253033adc481'
 (OUT/'inputs/initial-profile-compile-placement-amendment.md').write_bytes(amendment.read_bytes())
 emit('placement-amendment-custody.json',{'schema':1,'path':str(amendment.relative_to(ROOT)),'sha256':sha(amendment.read_bytes()),'selection_unchanged':True})
 common='''let initial=super::InitialProfileBorrowV1 {
 cache: cache.as_ref().unwrap(), control: &*control, wasi: None,
 scalars: super::InitialProfileScalarsV1 { source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0 },
};
'''
 cases={
 'positive_contract.rs':'''// Compile this SAME file at both placements; the internal signature clause
// uses the explicitly recorded cfg only for the internal placement.
fn independent_positive_context() {
 let _=std::mem::size_of::<crate::experimental_swift_reactor::cache::SwiftFunctionCache>();
 let _=std::mem::size_of::<crate::experimental_swift_reactor::control::RuntimeControl>();
}
#[cfg(mixer_initial_profile_contract_internal)]
const _: fn(
 &mut Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
 &mut crate::experimental_swift_reactor::control::RuntimeControl,
 Option<&crate::experimental_wasi::accounted::AccountedWasi>,
 crate::experimental_swift_reactor::control::AdoptedProof,
 &super::SelectedInitialProfileV1, &super::UnverifiedProfileDigestBytesV1,
 &mut std::fs::File,
) -> super::InitialProfileConstructionOutcomeV1 = super::construct_with_initial_profile_v1;
''',
 'guard_literal_from_sibling.rs':'''// Sibling insertion MUST reject this intended private type/literal access (E0603).
use super::initial_profile_v1::{InitialProfileBorrowV1,InitialProfileScalarsV1};
fn independent_private_guard(cache:&crate::experimental_swift_reactor::cache::SwiftFunctionCache,control:&crate::experimental_swift_reactor::control::RuntimeControl) {
 let _=InitialProfileBorrowV1 {cache,control,wasi:None,scalars:InitialProfileScalarsV1 {source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0}};
}
''',
 'external_selection_literal.rs':'''// Sibling insertion MUST reject these intended private selected types.
use super::initial_profile_v1::{SelectedInitialProfileV1, SelectedLocalStructureV1};
fn independent_private_selection(budget:crate::experimental_swift_reactor::control::SwiftRunBudget,local:SelectedLocalStructureV1) {
 let _=SelectedInitialProfileV1 {budget,local};
}
''',
 'guard_escape.rs':'''fn independent_guard_escape<'a>(initial:&'a super::InitialProfileBorrowV1<'a>)-> &'static super::InitialProfileBorrowV1<'static> { initial }
''',
 'proof_escape.rs':'''fn independent_proof_escape(initial:&super::InitialProfileBorrowV1<'_>)-> &'static crate::experimental_swift_reactor::ValidatedSwiftReactor { initial.cache.proof() }
''',
 'cache_move.rs':'''fn independent_cache_move(cache:&mut Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,control:&mut crate::experimental_swift_reactor::control::RuntimeControl) {
'''+common+'''let _taken=cache.take(); std::hint::black_box(&initial);
}
''',
 'cache_mutation.rs':'''fn independent_cache_mutation(cache:&mut Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,control:&mut crate::experimental_swift_reactor::control::RuntimeControl) {
'''+common+'''let _=cache.as_mut().unwrap().prepare_operation(control,None,crate::experimental_swift_reactor::control::Cursor {stage:crate::experimental_swift_reactor::control::SwiftRunStage::Initialization,function:None,offset:None}); std::hint::black_box(&initial);
}
''',
 'control_mutation.rs':'''fn independent_control_mutation(cache:&mut Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,control:&mut crate::experimental_swift_reactor::control::RuntimeControl) {
'''+common+'''let _mutable=&mut *control; std::hint::black_box(&initial);
}
''',
 'row_foreign_snapshot.rs':'''fn independent_row_foreign(initial:&super::InitialProfileBorrowV1<'_>,foreign:&crate::experimental_swift_reactor::ValidatedSwiftReactor,out:&mut std::fs::File) {
 let _=super::write_initial_profile_rows_v1(initial,foreign,out);
}
''',
 'callback_reentry.rs':'''fn independent_callback_reentry(initial:&super::InitialProfileBorrowV1<'_>,out:&mut std::fs::File) {
 let _=super::write_initial_profile_rows_v1(initial,out,|| {});
}
'''}
 placements={
  'external':{'path':'src/experimental_swift_reactor/cache.rs','append':'\n#[cfg(test)] mod initial_profile_external_contract { include!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE")); }\n'},
  'internal':{'path':'src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs','append':'\ninclude!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE"));\n'}}
 roster=[]
 for name,source in cases.items():
  p=OUT/'predeclared-compile-cases'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
  mode='external' if name in ['guard_literal_from_sibling.rs','external_selection_literal.rs'] else 'internal'
  roster.append({'name':name,'path':str(p.relative_to(OUT)),'sha256':sha(p.read_bytes()),'placement':mode,'expected':'success at BOTH placement sites' if name=='positive_contract.rs' else 'intended private-type E0603' if mode=='external' else 'intended borrow/lifetime/type/arity diagnostic','executed':False})
 emit('compiler-matrix.json',{'schema':1,'status':'PREACCESS authored independent controls; unexecuted; not candidate distribution/support inputs','producer_roster_count':10,'required_positive_placements':['external','internal'],'independent_predeclared_sources':roster,'scratch_placements':placements,'internal_positive_extra_cfg':'--cfg mixer_initial_profile_contract_internal --check-cfg cfg(mixer_initial_profile_contract_internal)','requirements':['Verify exact 140 distribution members and 11 host-support sources before injection','Keep untouched frozen candidate and every compiler variant manifest separate','MIXER_INITIAL_PROFILE_COMPILE_CASE points only to one of ten exact hashed sources','Record every argv, env, feature, source manifest, delta, compiler identity, diagnostics and cleanup','Valid positive at BOTH sites with corresponding fixed argv','Reject missing-file, unresolved-import, malformed-syntax and unrelated-error pseudo failures','Negative proves only named privacy/borrow behavior; source/owner/order/accounting review remains required']})
 controls=[
 ('O1','SlotOccupied','Actual live cache in caller slot plus a consumed independently owned AdoptedProof; all selected/claims/File fields poison-readable only after this branch','tag1 retains exact adopted; no prepare/construct/complete/guard/header/rows; existing cache owner/nonce/shape/ledger/File unchanged; adopted refunded only by its own control'),
 ('O2','SelectionRefused','Each full17 record differs in exactly one actual selected/control budget field; canonical ceiling+1 independently; selected local one-literal mismatch','tag2 retains exact adopted, fixed code2 budget or code6 local; before prepare; do not infer comparison from header subset/min(entries,defined)'),
 ('O3','PreparationFailed','Actual foreign adopted owner, foreign WASI, expired deadline and construction-capacity rejection before phase exists','tag3 retains full original failure and adopted; original cursor/kind/code/resource/attempted/limit/at_failure/after_cleanup preserved; no phase completion'),
 ('O4a','ConstructionFailed+Ok','Actual prepartial owner-pair rejection and actual partial cancellation/capacity/work failure','tag4 full CacheConstructionFailure (Some adopted before partial; None after partial cleanup) and exact Ok completion; no extra proof cleanup for None'),
 ('O4b','ConstructionFailed+Err','Separately reviewed actual phase authority replacement fault after constructor failure; retain actual replaced authority','tag4 both independent full failures; None slots consumed exactly once; restore only original actual replaced authority for final owner cleanup'),
 ('O5','PhaseCompletionFailed','Real successful cache constructor followed by reviewed actual phase authority boundary failure','tag5 original completion failure; actual cache remains Some; no guard/header/rows; no wrapper refund; original cleanup tail consumes outcome/cache return storage once'),
 ('O6','HeaderRefused','Real constructed cache; explicit selected zero-slot/zero-pin budget or initial-state/B/local refusal via fixed test-only source fault','tag6 fixed profile error; cache retained; rows not attempted; only supported fixed error codes/stages/offsets'),
 ('O7','HeaderOwnerCheckFailed','Actual constructed cache; authentic foreign/missing/wrong owner header/buffer/WASI tickets with original replacement retained','tag7 full original runtime failure, never code3 substitution; cache retained; restore replaced ticket before cleanup'),
 ('O8a','HeaderEncoded+Ok','Finite actual official supported reactor through unchanged validation/adoption/constructor/complete; None and actual same-control WASI','tag8 exact512 header and exact accepted same-cache-proof rows/File; cache retained; guard ended before return; final actual cleanup zero owned external tickets'),
 ('O8b','HeaderEncoded+Err','Actual row File nonempty, nonzero offset, readonly empty file, nonregular; fixed source-reviewed writer schedules','tag8 exact header retained plus full original row error/progress/attempts; physical acknowledged prefix compared; no rollback/fsync/durability claim'),
 ('G1','Fresh sole guard','Inspect actual selected source public closure; actual test counters at prepare,construct,complete,guard,header,rows,operation/acquisition','Occupied/selection/prepare/construction/complete precedence; sole private struct literal only after successful actual construction+complete+all guard checks; no acquisition/prepare_operation/control admission/callback/reentry/guest/suspend'),
 ('G2','Chronology counterexample','Actual fresh constructor then pin imported absolute0 and complete the operation','Actual initial cache shape can survive failed acquisition, so current shape cannot establish freshness; wrapper source sole continuation must establish chronology'),
 ('B1','All17 budget drifts','Exact frozen test-budget-records full literals in named source, no Default/partial override','17 independent early refusals, all actual canonical ceilings checked; scalar-hidden drift refuses; zero unrelated limit not universally invalid'),
 ('B2','Entry boundaries','Explicit complete selected-entry-zero and entry-above-capacity records; actual constructors B<=cache capacity','Header can succeed for entry_limit0 or entry_limit>capacity; no clamp/artificial inequality; explicit cache-below-B preserves actual construction failure'),
 ('S1','All initial usage','Inspect actual fields including fixed_reserved and eleven remaining SwiftCacheUsage fields; control live entries/pins','All constructor defaults except exact fixed B; every peak/counter own active_pins0; not counters-only inference'),
 ('S2','Actual shape','Each slot/pin/patch/index/plan len/capacity; free pin nonce/entry; slot resident/pins/last_used; every plan/index; nonce1','Exact min(entries,defined), pins actual; slots/pins1..64; patch512/index192/plan512; safe defensive fault restoration before original cleanup'),
 ('S3','Authentic tickets','Header, three buffer, adopted source/metadata; correct actual control/WASI; wrong category/bytes/owner/missing/foreign','Actual owner checks and semantic category/byte checks all reviewed; no forged ticket/public bool shortcut; retain exact runtime failures'),
 ('S4','Cache B equality','Separate authentic unrelated Cache tickets0 and1; state/WASI owners permitted','0-byte Cache ticket permitted, positive ticket refuses Cache.current==B; own ticket cleaned by its original control; no all-control-zero rule'),
 ('L1','Fixed local structure','165 literal ordered complete types size AND alignment and id/reserved/schema/count/width/endian/formulas','Actual comparator against selected literals; all165 IDs/type names and fixed fields accounted; any one mismatch code6; no fresh expected measurement self-comparison/build authority'),
 ('H1','Exact header','Independent reactor29/67 expected512 bytes; claims bytes0..255; static8-byte magic; all named u64 LE fields','Exact byte comparison, all24 reserved scalar zeros, eight distinct32 claim slots, trailing128 zeros; pure no I/O/hash/path/cast/transmute'),
 ('H2','Arithmetic/boundaries','All4096 slot/pin pairs; supported policy/revision/import34/validated_bodies/type/defined limits; checked H/B/narrowing','Closed fixed refusal arithmetic/stage/offset; no overflow or min/clamp hiding; actual source extent/type derived from cache proof'),
 ('R1','Same proof bridge','Read actual two-argument guard+File function and accepted unchanged row source','Pass initial.cache.proof() only; independent owner/descriptor/scalars/rows/callback cannot substitute; no proof/reference escapes'),
 ('R2','Row File errors','Retained physical nonempty/offset/readonly/nonregular descriptors; safely source-injected metadata/position faults where no portable kernel route','Exact codes5/6/7/8 at stage3; failed writes code9/10/11/12 stage4; partial output_bytes/attempts/offset retained; source-only syscall cases labeled'),
 ('R3','Row write schedules','Accepted fixed loop actual File full/short/Interrupted/zero/error/overreport,32calls per block,late failure after completed block','Exact625blocks/4096byte requests/80000rows/20000calls bound; zero/error take precedence on32nd; no33rd; preserve partial prefix/header/cache'),
 ('A1','Actual source closure','Exact canonical132+acceptedrow2 plus6 selected new sources; only original cache module delta; exact host11','140+11 exact future-closure; no archived probe/instrumentation/frozen inspector/authority/rejectedWorker/broad harness; unchanged base functions/limits'),
 ('A2','Complete places/lifetimes','Actual wrapper args/phase/preparation/taken slots/constructor returns/inline outcome/moves/guard/scalars/header/rows/caller/outcome cleanup storage','Every live complete Result/Option/ref/owner/error/caller/callee/move measured against literal165; join union intervals with actual constructor bounds, no layout-only acceptance'),
 ('A3','Heap/source/work/I/O','Actual Vec extents/capacities/tickets + source validation/adoption limits + all loops+requested cumulative I/O + Metadata/File/error transfers','Close each bounded extent/work loop and interval under unchanged original budgets/reservations/deadline; prior11912/13904/450652288 totals not inherited capacity or debit'),
 ('A4','Cleanup boundary','Each owned outcome destructured; actual AdoptedProof foreign control; actual CacheCleanupTail.complete<T> consumes storage before refund','Early branches, Some/None rejected adopted, all constructed failures, final outcome move/storage included; no implicit Rust-drop refund, diagnostic replay, ledger repair or foreign refund'),
 ('E1','Evidence/cleanup','Rust1.99 aarch64-apple-darwin Debug+optimized exact named methods; finite <=60sec children/output limits; raw failures retained','Exact source tree/tool executable/version/cfg/target/argv/env/output/executable hashes; owned children reaped/TMP/compilerproducts removed; native/UI/capture/process inventory remain paused')]
 emit('predeclared-review-matrix.json',{'schema':1,'status':'PREACCESS; every candidate row PENDING until explicit frozen root release','acceptance_from_data_only_layout_or_abstract_model':False,'controls':[{'id':i,'subject':s,'stimulus_and_source_control':c,'required_observation':o,'candidate_status':'PENDING'} for i,s,c,o in controls],'native_or_runtime_or_GA_pass':False})
 emit('pending-boundary.json',{'schema':1,'candidate_access_authorized':False,'candidate_source_read':False,'candidate_tests_run':False,'candidate_acceptance':False,'preaccess_scope':'independent expected bytes, bounded old-source controls and concrete future review matrix','not_attempted':['native','simulator','emulator','device','UI','capture','process inventory','full suite','historical80000function target','frozen hosted catalog-inspector','authority-driver','rejectedWorkerV2','broad harness'],'next_action':'Freeze preaccess seal, report it, wait for explicit root frozen candidate release'})
 print(f'PREACCESS authored {len(controls)} concrete review rows, 10 independent compiler sources, 2 exact placement controls.')
if __name__=='__main__':main()
