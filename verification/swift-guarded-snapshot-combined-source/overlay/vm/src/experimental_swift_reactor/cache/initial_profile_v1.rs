//! Private one-shot fresh-construction profile. Opaque claims grant no authority.
#![allow(dead_code)]
use super::*;
use super::super::diagnostic_profile::{ProfileAdapterErrorV1, ProfileRowsObservationV1};
use std::fs::File;

const CONSTRUCTION_CURSOR_V1: Cursor = Cursor {
    stage: SwiftRunStage::Initialization, function: None, offset: None,
};

#[repr(C)]
struct ProfileHeaderErrorV1 { code:u32, stage:u32, offset:u64 }
#[repr(C)]
struct InitialProfileScalarsV1 {
    source_extent:u64, type_count:u64, slot_limit:u64, pin_limit:u64,
    initial_nonce:u64, cache_base:u64, cache_capacity:u64, entry_limit:u64,
}
#[repr(C)]
pub(in crate::experimental_swift_reactor) struct UnverifiedProfileDigestBytesV1 {
    baseline:[u8;32], candidate:[u8;32], original_input:[u8;32], event_schema:[u8;32],
    profile_adapter_binary:[u8;32], layout_receipt:[u8;32], original_validated_snapshot:[u8;32], profile_row_body:[u8;32],
}
#[repr(transparent)]
struct UnverifiedProfileHeaderV1 { bytes:[u8;512] }
pub(crate) struct InitialProfileBorrowV1<'a> {
    cache:&'a SwiftFunctionCache, control:&'a RuntimeControl, wasi:Option<&'a AccountedWasi>,
    scalars:InitialProfileScalarsV1,
}
#[repr(u32)]
enum ProfileAdmissionFailureV1 {
    Refused(ProfileHeaderErrorV1)=1,
    Runtime(SwiftRunFailure)=2,
}
/// The cache owner never moves into this result. Constructed branches retain
/// it in caller cache_out. All original failure/proof payloads remain inline.
#[repr(u32)]
#[must_use = "Retain the real cache slot and consume returned proof owners through their original control cleanup"]
enum InitialProfileConstructionOutcomeV1 {
    SlotOccupied { adopted:AdoptedProof }=1,
    SelectionRefused { error:ProfileHeaderErrorV1, adopted:AdoptedProof }=2,
    PreparationFailed { failure:SwiftRunFailure, adopted:AdoptedProof }=3,
    ConstructionFailed { failure:CacheConstructionFailure, completion:Result<(),SwiftRunFailure> }=4,
    PhaseCompletionFailed { failure:SwiftRunFailure }=5,
    HeaderRefused { error:ProfileHeaderErrorV1 }=6,
    HeaderOwnerCheckFailed { failure:SwiftRunFailure }=7,
    HeaderEncoded { header:UnverifiedProfileHeaderV1, rows:Result<ProfileRowsObservationV1,ProfileAdapterErrorV1> }=8,
}
#[repr(C)]
struct LocalTypeLayoutV1 { id:u32, reserved:u32, bytes:u64, alignment:u64 }
#[repr(C)]
struct SelectedLocalStructureV1 {
    schema:u32, entries:u32, word_bytes:u32, little_endian:u32,
    header_bytes:u64, row_bytes:u64, rows:u64,
    header_words:u32, digest_slots:u32, digest_bytes:u32, trailing_zero_bytes:u32,
    outcome_variant_schema:u32, header_error_schema:u32,
    cache_cleanup_bytes:u64, cache_header_bytes:u64,
    cache_construction_bytes:u64, cache_operation_bytes:u64,
    selected_slots_max:u64, selected_pins:u64, cache_fixed_at_selected_maxslots:u64,
    type_layout:[LocalTypeLayoutV1;201],
}
#[repr(C)]
struct SelectedInitialProfileV1 { budget:SwiftRunBudget, local:SelectedLocalStructureV1 }

// Named conservative layout places for later lifetime/accounting review.
// These are measurements, not a granted reservation or proven simultaneous set.
struct WrapperArgumentsV1<'a> {
    cache_out:&'a mut Option<SwiftFunctionCache>, control:&'a mut RuntimeControl,
    wasi:Option<&'a AccountedWasi>, adopted:AdoptedProof,
    selected:&'a SelectedInitialProfileV1, claims:&'a UnverifiedProfileDigestBytesV1, row_output:&'a mut File,
}
struct WrapperPhaseStorageV1<'a> {
    preparation:Option<Result<CacheConstructionPhase<'a>,SwiftRunFailure>>,
    phase:Option<CacheConstructionPhase<'a>>, original_return:ConstructionReturnSlot,
    construction_failure:Option<CacheConstructionFailure>, cache_transfer:Option<SwiftFunctionCache>,
    completion:Result<(),SwiftRunFailure>,
}
struct WrapperEmissionStorageV1<'a> {
    guard:Option<InitialProfileBorrowV1<'a>>,
    guard_result:Result<InitialProfileBorrowV1<'a>,ProfileAdmissionFailureV1>,
    scalar_result:Result<InitialProfileScalarsV1,ProfileHeaderErrorV1>,
    header_result:Result<UnverifiedProfileHeaderV1,ProfileHeaderErrorV1>,
    row_result:Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>,
    result:Option<InitialProfileConstructionOutcomeV1>,
}
struct WrapperCallerStorageV1 {
    cache_out:Option<SwiftFunctionCache>, control:RuntimeControl,
    wasi:Option<AccountedWasi>, adopted_input:Option<AdoptedProof>,
    result:Option<InitialProfileConstructionOutcomeV1>, row_output:File,
    selected:SelectedInitialProfileV1, claims:UnverifiedProfileDigestBytesV1,
}
struct WrapperMoveStorageV1 {
    adopted_argument:AdoptedProof, adopted_rejected:Option<AdoptedProof>,
    constructed_cache:SwiftFunctionCache, cache_option_transfer:Option<SwiftFunctionCache>,
    constructor_return:Result<SwiftFunctionCache,CacheConstructionFailure>,
    construction_failure:CacheConstructionFailure,
    completion_return:Result<(),SwiftRunFailure>,
    final_return:InitialProfileConstructionOutcomeV1,
    caller_return:Option<InitialProfileConstructionOutcomeV1>,
}

// Before prepare, all wrapper ingress and retained output/return places must
// already have a foundation floor; a later cache phase cannot grant it back.
pub(super) const WRAPPER_SOURCE_PLACES_V1: usize =
    size_of::<WrapperArgumentsV1<'static>>() + size_of::<WrapperPhaseStorageV1<'static>>()
    + size_of::<WrapperEmissionStorageV1<'static>>() + size_of::<WrapperCallerStorageV1>()
    + size_of::<WrapperMoveStorageV1>();

#[cfg(test)]
pub(super) fn test_selected_initial_outcome_v1(
    selected: super::super::retained_profile_loader_v1::SelectedValidatedProfileV1, case: &str,
) { tests::selected_owner_outcome_v1(selected,case); }

mod header;
mod selected;
mod local_structure;
#[cfg(any(test,mixer_initial_profile_component_host,mixer_snapshot_encoder_host))] mod tests;
#[cfg(any(test,mixer_initial_profile_component_host))] mod compile_contracts;
use header::*;
use selected::selected_initial_profile_v1;
use local_structure::compare_local_structure_v1;

fn profile_error(code:u32,stage:u32,offset:u64)->ProfileHeaderErrorV1 {
    ProfileHeaderErrorV1 { code,stage,offset }
}
fn construct_with_initial_profile_v1(
    cache_out:&mut Option<SwiftFunctionCache>, control:&mut RuntimeControl,
    wasi:Option<&AccountedWasi>, adopted:AdoptedProof,
    selected:&SelectedInitialProfileV1, claims:&UnverifiedProfileDigestBytesV1,
    row_output:&mut File,
)->InitialProfileConstructionOutcomeV1 {
    construct_profile_core_v1(cache_out,control,wasi,adopted,selected,claims,row_output,OriginalBranchV1)
}
fn construct_profile_core_v1<B:ClosedBranchV1>(
    cache_out:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,
    wasi:Option<&AccountedWasi>,adopted:AdoptedProof,
    selected:&SelectedInitialProfileV1,claims:&UnverifiedProfileDigestBytesV1,
    row_output:&mut File,mut branch:B,
)->B::Output {
    if cache_out.is_some() { return branch.early(InitialProfileConstructionOutcomeV1::SlotOccupied { adopted }); }
    if let Err(error)=compare_budget_v1(control.budget(),selected.budget)
        .and_then(|()|compare_local_structure_v1(&selected.local)) {
        return branch.early(InitialProfileConstructionOutcomeV1::SelectionRefused { error,adopted });
    }
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::boundary(1,control,None);
    let mut preparation=Some(SwiftFunctionCache::prepare(control,wasi,&adopted,CONSTRUCTION_CURSOR_V1));
    let mut phase=match preparation.take().expect("actual prepare return") {
        Ok(phase)=>phase,
        Err(failure)=>return branch.early(InitialProfileConstructionOutcomeV1::PreparationFailed { failure,adopted }),
    };
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::phase_boundary(&mut phase);
    let mut original_return:ConstructionReturnSlot=Some(phase.construct(adopted));
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::completion_boundary(&mut phase);
    match original_return.take().expect("actual constructor return") {
        Err(failure)=>{
            let completion=phase.complete((preparation,original_return));
            return branch.early(InitialProfileConstructionOutcomeV1::ConstructionFailed { failure,completion });
        },
        Ok(cache)=>*cache_out=Some(cache),
    }
    if let Err(failure)=phase.complete((preparation,original_return)) {
        return branch.early(InitialProfileConstructionOutcomeV1::PhaseCompletionFailed { failure });
    }
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::boundary(2,control,cache_out.as_mut());
    let cache=cache_out.as_ref().expect("constructed owner remains in caller slot");
    let scalars=match inspect_initial_v1(cache,control,wasi) {
        Ok(scalars)=>scalars,
        Err(ProfileAdmissionFailureV1::Refused(error))=>return branch.early(InitialProfileConstructionOutcomeV1::HeaderRefused { error }),
        Err(ProfileAdmissionFailureV1::Runtime(failure))=>return branch.early(InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed { failure }),
    };
    let (access,mut storage)=branch.begin(cache,control,wasi);
    let (primary,attempt)='guarded: {
        // Sole guard literal. The access owns the exclusive borrow in both states.
        let initial=InitialProfileBorrowV1 { cache,control:access.shared_control(),wasi,scalars };
        #[cfg(any(test,mixer_snapshot_encoder_host))]
        branch.original_encoder_observer(&initial);
        let attempt=branch.export(&initial,&mut storage,row_output);
        #[cfg(any(test,mixer_initial_profile_component_host))] tests::mark(3);
        let header=match encode_profile_header_v1(&initial,claims) {
            Ok(header)=>header,
            Err(error)=>break 'guarded (InitialProfileConstructionOutcomeV1::HeaderRefused {error},attempt),
        };
        #[cfg(any(test,mixer_initial_profile_component_host))] tests::mark(4);
        let rows=write_initial_profile_rows_v1(&initial,row_output);
        (InitialProfileConstructionOutcomeV1::HeaderEncoded {header,rows},attempt)
    }; // Every guard/view/cursor/block borrow has ended.
    branch.finish(primary,attempt,access,storage)
}
fn write_initial_profile_rows_v1(initial:&InitialProfileBorrowV1<'_>,output:&mut File)
    ->Result<ProfileRowsObservationV1,ProfileAdapterErrorV1> {
    super::super::diagnostic_profile::write_profile_row_body_v1(initial.cache.proof(),output)
}
fn compare_budget_v1(actual:SwiftRunBudget,expected:SwiftRunBudget)->Result<(),ProfileHeaderErrorV1> {
    // Compare complete17 records; ceilings remain separately enforced even in
    // test-only alternative full selections.
    if actual!=expected { return Err(profile_error(2,1,0)); }
    let ceiling=selected_initial_profile_v1().budget;
    macro_rules! ceiling { ($($field:ident),+) => { $(if actual.$field>ceiling.$field {return Err(profile_error(2,1,0));})+ }; }
    ceiling!(source_bytes,metadata_bytes,cache_bytes,cache_entry_bytes,cache_entries,active_pins,cache_work,
        frames,values,controls,memory_pages,state_bytes,combined_bytes,instruction_fuel,execution_work,host_calls,deadline_ms);
    Ok(())
}
fn inspect_initial_v1(cache:&SwiftFunctionCache,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>)
    ->Result<InitialProfileScalarsV1,ProfileAdmissionFailureV1> {
    use ProfileAdmissionFailureV1::{Refused,Runtime};
    cache.check_owner(control,wasi,CONSTRUCTION_CURSOR_V1).map_err(Runtime)?;
    let observation=wasi.map(AccountedWasi::usage);
    control.check_adopted_owner(&cache.adopted,CONSTRUCTION_CURSOR_V1,observation).map_err(Runtime)?;
    let header=cache.header.as_ref().ok_or_else(||Refused(profile_error(3,1,0)))?;
    if !header.matches_layout(SwiftReservationCategory::Cache,cache_header_bytes().ok_or_else(||Refused(profile_error(8,3,80)))?) {
        return Err(Refused(profile_error(3,1,0)));
    }
    let budget=control.budget();
    let o=cache.proof().observations();
    let total=o.imported_functions.checked_add(o.defined_functions).ok_or_else(||Refused(profile_error(8,1,32)))?;
    if ValidatedSwiftReactor::VALIDATOR_REVISION!=1 || SwiftFunctionCache::DECODER_REVISION!=1
        || cache.proof().policy_identity()!="swift-reactor-experiment-v1" || o.imported_functions!=34
        || o.validated_bodies!=o.defined_functions || o.types>u32::MAX as usize || total>80000 {
        return Err(Refused(profile_error(1,1,0)));
    }
    let entries=budget.cache_entries.min(o.defined_functions);
    if !(1..=64).contains(&entries) || !(1..=64).contains(&budget.active_pins)
        || cache.slots.len()!=entries || cache.slots.capacity()!=entries
        || cache.pins.len()!=budget.active_pins || cache.pins.capacity()!=budget.active_pins {
        return Err(Refused(profile_error(5,2,0)));
    }
    for (ticket,bytes) in cache.buffers.iter().zip([
        entries.checked_mul(size_of::<SwiftSlot>()),budget.active_pins.checked_mul(size_of::<PinRecord>()),
        PATCH_CAPACITY.checked_mul(size_of::<decode::Patch>())]) {
        let bytes=bytes.ok_or_else(||Refused(profile_error(8,3,80)))?;
        let ticket=ticket.as_ref().ok_or_else(||Refused(profile_error(3,1,0)))?;
        control.check_reservation_owner(ticket,CONSTRUCTION_CURSOR_V1,observation).map_err(Runtime)?;
        if !ticket.matches_layout(SwiftReservationCategory::Cache,bytes) { return Err(Refused(profile_error(3,1,0))); }
    }
    let fixed=cache_header_bytes().and_then(|n|entries.checked_mul(size_of::<SwiftSlot>()).and_then(|v|n.checked_add(v)))
        .and_then(|n|budget.active_pins.checked_mul(size_of::<PinRecord>()).and_then(|v|n.checked_add(v)))
        .and_then(|n|PATCH_CAPACITY.checked_mul(size_of::<decode::Patch>()).and_then(|v|n.checked_add(v)))
        .ok_or_else(||Refused(profile_error(8,3,80)))?;
    let usage=control.usage(observation);
    if cache.owner==0 {return Err(Refused(profile_error(3,1,0)));}
    if cache.next_nonce!=1 || cache.usage!=(SwiftCacheUsage {fixed_reserved:cache.usage.fixed_reserved,..SwiftCacheUsage::default()})
        || cache.slots.iter().any(|s|s.resident.is_some() || s.pins!=0 || s.last_used!=0)
        || cache.pins.iter().any(|p|p.nonce!=0 || p.entry!=0)
        || cache.patches.len()!=PATCH_CAPACITY || cache.patches.capacity()!=PATCH_CAPACITY
        || cache.index.len()!=RESIDENT_INDEX_BYTES || cache.index.capacity()!=RESIDENT_INDEX_BYTES
        || cache.index.iter().any(|v|*v!=0)
        || cache.plans.len()!=PLAN_CAPACITY || cache.plans.capacity()!=PLAN_CAPACITY
        || cache.plans.iter().any(Option::is_some)
        || usage.live.cache_entries!=SwiftReservationUsage::default() || usage.live.active_pins!=SwiftReservationUsage::default() {
        return Err(Refused(profile_error(4,2,0)));
    }
    if fixed>budget.cache_bytes || cache.usage.fixed_reserved!=fixed || usage.reservations.cache.current!=fixed {
        return Err(Refused(profile_error(7,3,80)));
    }
    let convert=|n:usize,offset|u64::try_from(n).map_err(|_|Refused(profile_error(8,3,offset)));
    Ok(InitialProfileScalarsV1 {
        source_extent:convert(cache.proof().source().len(),40)?,type_count:convert(o.types,48)?,
        slot_limit:convert(entries,56)?,pin_limit:convert(budget.active_pins,64)?,initial_nonce:cache.next_nonce,
        cache_base:convert(fixed,80)?,cache_capacity:convert(budget.cache_bytes,88)?,entry_limit:convert(budget.cache_entry_bytes,96)?,
    })
}

impl InitialProfileBorrowV1<'_> {
 pub(crate) fn snapshot_proof_v2(&self)->&ValidatedSwiftReactor{self.cache.proof()}
 pub(crate) fn snapshot_selected_v2(&self)->Option<&super::super::retained_profile_loader_v1::LoaderProvenanceV1>{self.cache.adopted.selected_provenance()}
 pub(crate) fn snapshot_runtime_v2(&self,out:&mut[u8;512])->Result<(),()> {
  out.fill(0);out[..8].copy_from_slice(b"MIXRTB01");let b=self.control.budget();
  let s=&self.scalars;let wasi=self.wasi.map(AccountedWasi::snapshot_configuration_v2);
  let convert=|n:usize|u64::try_from(n).map_err(|_|());
  let limits=[convert(b.source_bytes)?,convert(b.metadata_bytes)?,convert(b.cache_bytes)?,convert(b.cache_entry_bytes)?,
   convert(b.cache_entries)?,convert(b.active_pins)?,b.cache_work,convert(b.frames)?,convert(b.values)?,convert(b.controls)?,
   u64::from(b.memory_pages),convert(b.state_bytes)?,convert(b.combined_bytes)?,b.instruction_fuel,b.execution_work,b.host_calls,b.deadline_ms];
  for(i,n)in [1,512,u64::from(wasi.is_some()),self.cache.owner].iter().enumerate(){out[8+i*8..16+i*8].copy_from_slice(&n.to_le_bytes());}
  for(i,n)in limits.iter().enumerate(){out[40+i*8..48+i*8].copy_from_slice(&n.to_le_bytes());}
  if let Some((w,g))=wasi{
   for(i,n)in [w.calls,w.transfer_bytes,w.work,u64::from(w.one_transfer_bytes),u64::from(w.iovecs),u64::from(w.log_bytes),w.deadline_ms,
    u64::from(g.secure_random),u64::from(g.realtime),u64::from(g.monotonic),u64::from(g.stdout),u64::from(g.stderr)].iter().enumerate(){out[176+i*8..184+i*8].copy_from_slice(&n.to_le_bytes());}
  }
  for(i,n)in [s.source_extent,s.type_count,s.slot_limit,s.pin_limit,s.initial_nonce,s.cache_base,s.cache_capacity,s.entry_limit].iter().enumerate(){out[272+i*8..280+i*8].copy_from_slice(&n.to_le_bytes());}
  Ok(())
 }
}
#[cfg(any(test,mixer_snapshot_encoder_host))]use tests::snapshot_encoder_host;


use super::super::control::{SnapshotAdmissionErrorV1 as AError,SnapshotStopV1 as Stop};
use crate::experimental::swift::snapshot_encoder_v2::{borrow_snapshot_v2,SnapshotEncodeErrorV2,SnapshotCursorV2,SnapshotViewV2,SnapshotBlockV2};
use std::io::{self,Write,Seek};
use std::os::unix::fs::MetadataExt;

mod branch_seal_v1 { pub(super) trait Closed {} }
struct OriginalBranchV1;
struct SnapshotBranchV1<'f> { output:&'f mut File }
impl branch_seal_v1::Closed for OriginalBranchV1 {}
impl branch_seal_v1::Closed for SnapshotBranchV1<'_> {}
trait SharedControlV1 {fn shared_control(&self)->&RuntimeControl;}
struct OriginalAccessV1<'c>(&'c mut RuntimeControl);
impl SharedControlV1 for OriginalAccessV1<'_>{fn shared_control(&self)->&RuntimeControl{self.0}}
trait ClosedBranchV1:branch_seal_v1::Closed {
    type Output;
    type Attempt;
    type Storage;
    type Access<'c>:SharedControlV1;
    fn early(self,primary:InitialProfileConstructionOutcomeV1)->Self::Output;
    fn begin<'c>(&self,cache:&SwiftFunctionCache,control:&'c mut RuntimeControl,wasi:Option<&AccountedWasi>)->(Self::Access<'c>,Self::Storage);
    fn export(&mut self,initial:&InitialProfileBorrowV1<'_>,storage:&mut Self::Storage,rows:&File)->Self::Attempt;
    fn finish(self,primary:InitialProfileConstructionOutcomeV1,attempt:Self::Attempt,access:Self::Access<'_>,storage:Self::Storage)->Self::Output;
    #[cfg(any(test,mixer_snapshot_encoder_host))]
    fn original_encoder_observer(&self,_:&InitialProfileBorrowV1<'_>){}
}
impl ClosedBranchV1 for OriginalBranchV1 {
    type Output=InitialProfileConstructionOutcomeV1;
    type Attempt=();type Storage=();type Access<'c>=OriginalAccessV1<'c>;
    fn early(self,primary:Self::Output)->Self::Output{primary}
    fn begin<'c>(&self,_:&SwiftFunctionCache,control:&'c mut RuntimeControl,_:Option<&AccountedWasi>)->(Self::Access<'c>,()){
        (OriginalAccessV1(control),())
    }
    fn export(&mut self,_:&InitialProfileBorrowV1<'_>,_:&mut (),_:&File){}
    fn finish(self,primary:Self::Output,_:(),access:Self::Access<'_>,_:())->Self::Output{drop(access);primary}
    #[cfg(any(test,mixer_snapshot_encoder_host))]
    fn original_encoder_observer(&self,initial:&InitialProfileBorrowV1<'_>){snapshot_encoder_host::observe_v2(initial);}
}
impl ClosedBranchV1 for SnapshotBranchV1<'_> {
    type Output=SnapshotOuterV1;type Attempt=SnapshotAttemptV1;
    type Storage=SnapshotPhaseStorageV1;type Access<'c>=SnapshotAccessV1<'c>;
    fn early(self,primary:InitialProfileConstructionOutcomeV1)->Self::Output{
        SnapshotOuterV1 {primary,export:SnapshotAttemptV1::NotReached,phase_completion:Ok(())}
    }
    fn begin<'c>(&self,cache:&SwiftFunctionCache,control:&'c mut RuntimeControl,wasi:Option<&AccountedWasi>)->(Self::Access<'c>,Self::Storage){
        begin_snapshot_access_v1(cache,control,wasi)
    }
    fn export(&mut self,initial:&InitialProfileBorrowV1<'_>,storage:&mut Self::Storage,rows:&File)->Self::Attempt{
        match (&storage.plan,&mut storage.transfer) {
            (Some(plan),Some(transfer))=>write_snapshot_v1(initial,plan,transfer,rows,self.output),
            (None,None)=>SnapshotAttemptV1::AdmissionRefused(storage.refusal.expect("actual refusal")),
            _=>unreachable!("private phase slots paired at admission"),
        }
    }
    fn finish(self,primary:InitialProfileConstructionOutcomeV1,export:Self::Attempt,access:Self::Access<'_>,storage:Self::Storage)->Self::Output{
        let phase_completion=access.complete(storage);
        SnapshotOuterV1 {primary,export,phase_completion}
    }
}

enum SnapshotAccessV1<'c> {
    Admitted {control:&'c mut RuntimeControl,retained:usize,wasi:Option<crate::experimental_wasi::WasiUsage>},
    Refused {control:&'c mut RuntimeControl,error:AError},
}
impl SharedControlV1 for SnapshotAccessV1<'_>{
    fn shared_control(&self)->&RuntimeControl{match self{Self::Admitted{control,..}|Self::Refused{control,..}=>control}}
}
impl SnapshotAccessV1<'_> {
    fn complete(self,storage:SnapshotPhaseStorageV1)->Result<(),SwiftRunFailure>{
        match self{
            Self::Admitted{control,retained,wasi}=>control.end_construction_phase_with_wasi(storage,retained,wasi),
            Self::Refused{control:_,error:_}=>{drop(storage);Ok(())},
        }
    }
}
struct SnapshotShapeV1 {counts:[u64;9],extent:u64,blocks:u64,records:u64,words:u64}
struct SnapshotPlanV1 {shape:SnapshotShapeV1,planning:u64,emission:u64}
struct SnapshotPhaseStorageV1 {plan:Option<SnapshotPlanV1>,transfer:Option<[u8;4096]>,refusal:Option<AError>}
fn checked_add_v1(a:u64,b:u64)->Result<u64,AError>{a.checked_add(b).ok_or(AError::Arithmetic)}
fn checked_mul_v1(a:u64,b:u64)->Result<u64,AError>{a.checked_mul(b).ok_or(AError::Arithmetic)}
fn snapshot_shape_v1(counts:[usize;9])->Result<SnapshotShapeV1,AError>{
    const CAPS:[u64;9]=[67108864,512,8192,34,79966,8192,4096,4096,4096];
    const WIDTHS:[u64;9]=[0,3,1,5,3,4,4,4,4];
    let mut converted=[0u64;9];let mut words=0;let mut records=0;
    for i in 0..9 {
        let n=u64::try_from(counts[i]).map_err(|_|AError::Arithmetic)?;
        if n>CAPS[i]{return Err(AError::Layout);}
        converted[i]=n;
        if i!=0 {records=checked_add_v1(records,n)?;words=checked_add_v1(words,checked_mul_v1(n,WIDTHS[i])?)?;}
    }
    let extent=checked_add_v1(checked_add_v1(2560,converted[0])?,checked_mul_v1(8,words)?)?;
    let blocks=checked_add_v1(extent/4096,u64::from(extent%4096!=0))?;
    Ok(SnapshotShapeV1 {counts:converted,extent,blocks,records,words})
}
// Additive unused candidate; WorkAuditPending below is unchanged.
mod emission_bound_v1;

fn proposed_emission_work_v1(_shape:&SnapshotShapeV1)->Result<u64,AError>{
    // Deliberate compile-time preparation stop. The old P/R record rationale
    // does not cover repeated record_word validation/directory search. Root is
    // obtaining a separate source action audit. No rounded placeholder debits
    // can accidentally admit this source if called before that review.
    Err(AError::WorkAuditPending)
}
fn begin_snapshot_access_v1<'c>(cache:&SwiftFunctionCache,control:&'c mut RuntimeControl,wasi:Option<&AccountedWasi>)
    ->(SnapshotAccessV1<'c>,SnapshotPhaseStorageV1){
    let decision=(||{
        cache.snapshot_pair_v1(control,wasi)?;
        let additional=SNAPSHOT_PHASE_PLACES_V1;
        control.snapshot_storage_preflight_v1(additional)?;
        let planning=16384u64; // Original fixed planning contract; audit pending.
        control.snapshot_debit_v1(planning)?;
        let shape=snapshot_shape_v1(cache.proof().snapshot_counts_v1())?;
        let emission=proposed_emission_work_v1(&shape)?;
        control.snapshot_debit_v1(emission)?;
        let retained=control.snapshot_commit_storage_v1(additional)?;
        Ok::<_,AError>((retained,shape,planning,emission))
    })();
    match decision{
        Ok((retained,shape,planning,emission))=>{
            let wasi=wasi.map(AccountedWasi::usage); // Pairing completed above.
            let storage=SnapshotPhaseStorageV1 {plan:Some(SnapshotPlanV1{shape,planning,emission}),transfer:Some([0;4096]),refusal:None};
            (SnapshotAccessV1::Admitted{control,retained,wasi},storage)
        },
        Err(error)=>(SnapshotAccessV1::Refused{control,error},SnapshotPhaseStorageV1{plan:None,transfer:None,refusal:Some(error)}),
    }
}

#[derive(Clone,Copy)]
struct SnapshotProgressV1 {bytes:u64,calls:u64,block:u64,attempt:u32,requested:u64}
enum SnapshotCauseV1 {Stop(Stop),Encode(SnapshotEncodeErrorV2),Shape,NotRegular,NotEmpty,Alias,Position,Io,Zero,Overreported,Attempts,Arithmetic}
struct SnapshotExportErrorV1 {cause:SnapshotCauseV1,stage:u32,progress:SnapshotProgressV1,io:Option<io::Error>,post_stop:Option<Stop>}
struct SnapshotObservationV1 {bytes:u64,calls:u64,planning:u64,emission:u64}
enum SnapshotAttemptV1 {NotReached,AdmissionRefused(AError),Completed(SnapshotObservationV1),Failed(SnapshotExportErrorV1)}
#[must_use="Retain original primary, export and phase completion separately"]
pub(in crate::experimental_swift_reactor) struct SnapshotOuterV1 {
    primary:InitialProfileConstructionOutcomeV1,export:SnapshotAttemptV1,phase_completion:Result<(),SwiftRunFailure>,
}
struct SnapshotWriterV1<'g> {initial:&'g InitialProfileBorrowV1<'g>,progress:SnapshotProgressV1}
impl SnapshotWriterV1<'_> {
    fn error(&self,cause:SnapshotCauseV1,stage:u32,io:Option<io::Error>,post_stop:Option<Stop>)->SnapshotExportErrorV1{
        SnapshotExportErrorV1 {cause,stage,progress:self.progress,io,post_stop}
    }
    fn stop(&self,stage:u32)->Result<(),SnapshotExportErrorV1>{
        self.initial.control.snapshot_observe_stop_v1().map_err(|stop|self.error(SnapshotCauseV1::Stop(stop),stage,None,None))
    }
    fn io_result<T>(&self,result:io::Result<T>,stage:u32)->Result<T,SnapshotExportErrorV1>{
        let post_stop=self.initial.control.snapshot_observe_stop_v1().err();
        match result {
            Err(error)=>Err(self.error(SnapshotCauseV1::Io,stage,Some(error),post_stop)),
            Ok(value)=>match post_stop {Some(stop)=>Err(self.error(SnapshotCauseV1::Stop(stop),stage,None,None)),None=>Ok(value)},
        }
    }
    fn encode_result<T>(&self,result:Result<T,SnapshotEncodeErrorV2>,stage:u32)->Result<T,SnapshotExportErrorV1>{
        let post_stop=self.initial.control.snapshot_observe_stop_v1().err();
        match result {
            Err(error)=>Err(self.error(SnapshotCauseV1::Encode(error),stage,None,post_stop)),
            Ok(value)=>match post_stop{Some(stop)=>Err(self.error(SnapshotCauseV1::Stop(stop),stage,None,None)),None=>Ok(value)},
        }
    }
}
fn write_snapshot_v1(initial:&InitialProfileBorrowV1<'_>,plan:&SnapshotPlanV1,transfer:&mut[u8;4096],rows:&File,output:&mut File)->SnapshotAttemptV1{
    let mut writer=SnapshotWriterV1 {initial,progress:SnapshotProgressV1{bytes:0,calls:0,block:0,attempt:0,requested:0}};
    let result=(||{
        writer.stop(1)?;
        let view=writer.encode_result(borrow_snapshot_v2(initial),1)?;
        writer.stop(2)?;
        let mut cursor=writer.encode_result(view.into_cursor(),2)?;
        // This checks actual guard data before any metadata/seek/write call.
        let actual=initial.cache.proof().snapshot_counts_v1();
        let mut same=true;
        for i in 0..9 {same &= u64::try_from(actual[i]).ok()==Some(plan.shape.counts[i]);}
        if !same || cursor.encoded_extent()!=plan.shape.extent{return Err(writer.error(SnapshotCauseV1::Shape,3,None,None));}
        writer.stop(4)?;
        let metadata=writer.io_result(output.metadata(),4)?;
        writer.stop(5)?;
        let row_metadata=writer.io_result(rows.metadata(),5)?;
        if !metadata.is_file(){return Err(writer.error(SnapshotCauseV1::NotRegular,6,None,None));}
        if metadata.dev()==row_metadata.dev() && metadata.ino()==row_metadata.ino(){return Err(writer.error(SnapshotCauseV1::Alias,6,None,None));}
        if metadata.len()!=0{return Err(writer.error(SnapshotCauseV1::NotEmpty,6,None,None));}
        writer.stop(7)?;
        let position=writer.io_result(output.stream_position(),7)?;
        if position!=0{return Err(writer.error(SnapshotCauseV1::Position,7,None,None));}
        loop {
            writer.stop(8)?;transfer.fill(0);writer.stop(8)?;
            writer.stop(9)?;
            let block=writer.encode_result(cursor.next_block(transfer),9)?
                .ok_or_else(||writer.error(SnapshotCauseV1::Shape,9,None,None))?;
            if block.offset()!=writer.progress.bytes{return Err(writer.error(SnapshotCauseV1::Shape,9,None,None));}
            let mut acknowledged=0usize;
            let mut interrupted=None;
            for attempt in 1..=32u32 {
                writer.progress.attempt=attempt;
                let requested=&block.bytes()[acknowledged..];
                writer.progress.requested=u64::try_from(requested.len()).map_err(|_|writer.error(SnapshotCauseV1::Arithmetic,10,None,None))?;
                writer.stop(10)?;
                writer.progress.calls=writer.progress.calls.checked_add(1).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,10,None,None))?;
                // Exactly one native write per attempt, including Interrupted.
                let returned=output.write(requested);
                let post_stop=initial.control.snapshot_observe_stop_v1().err();
                match returned {
                    Ok(n) if n>0 && n<=requested.len()=>{
                        acknowledged=acknowledged.checked_add(n).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,10,None,post_stop))?;
                        writer.progress.bytes=writer.progress.bytes.checked_add(n as u64).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,10,None,post_stop))?;
                        // Acknowledged bytes survive cancellation inside write.
                        if let Some(stop)=post_stop{return Err(writer.error(SnapshotCauseV1::Stop(stop),10,None,None));}
                        if acknowledged==block.bytes().len(){break;}
                    },
                    Ok(0)=>return Err(writer.error(SnapshotCauseV1::Zero,10,None,post_stop)),
                    Ok(_)=>return Err(writer.error(SnapshotCauseV1::Overreported,10,None,post_stop)),
                    Err(error) if error.kind()==io::ErrorKind::Interrupted=>{
                        if post_stop.is_some(){return Err(writer.error(SnapshotCauseV1::Io,10,Some(error),post_stop));}
                        interrupted=Some(error);
                    },
                    Err(error)=>return Err(writer.error(SnapshotCauseV1::Io,10,Some(error),post_stop)),
                }
                if attempt==32{return Err(writer.error(SnapshotCauseV1::Attempts,10,interrupted.take(),None));}
            }
            if acknowledged!=block.bytes().len(){return Err(writer.error(SnapshotCauseV1::Attempts,10,interrupted,None));}
            let final_block=block.is_final();
            drop(block);
            writer.progress.block=writer.progress.block.checked_add(1).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,11,None,None))?;
            writer.stop(11)?;
            if final_block{break;}
        }
        if writer.progress.bytes!=plan.shape.extent || cursor.emitted_extent()!=plan.shape.extent || writer.progress.block!=plan.shape.blocks{
            return Err(writer.error(SnapshotCauseV1::Shape,12,None,None));
        }
        writer.stop(12)?;
        let observation=SnapshotObservationV1 {bytes:writer.progress.bytes,calls:writer.progress.calls,planning:plan.planning,emission:plan.emission};
        writer.stop(12)?;
        Ok(observation)
    })();
    match result{Ok(observation)=>SnapshotAttemptV1::Completed(observation),Err(error)=>SnapshotAttemptV1::Failed(error)}
}

pub(in crate::experimental_swift_reactor) struct SnapshotPrimaryRetirementV1 {
    variant:u32,primary:Option<SwiftRunFailure>,header_error:Option<ProfileHeaderErrorV1>,
    header:Option<UnverifiedProfileHeaderV1>,rows:Option<Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>>,
    construction_completion:Option<Result<(),SwiftRunFailure>>,adopted_retirement:Result<(),SwiftRunFailure>,
    export:SnapshotAttemptV1,phase_completion:Result<(),SwiftRunFailure>,
}
impl SnapshotOuterV1 {
    pub(in crate::experimental_swift_reactor) fn retire_v1(self,control:&mut RuntimeControl,wasi:Option<crate::experimental_wasi::WasiUsage>)->SnapshotPrimaryRetirementV1{
        let Self{primary,export,phase_completion}=self;
        let (variant,primary,header_error,header,rows,construction_completion,adopted)=match primary {
            InitialProfileConstructionOutcomeV1::SlotOccupied{adopted}=>(1,None,None,None,None,None,Some(adopted)),
            InitialProfileConstructionOutcomeV1::SelectionRefused{error,adopted}=>(2,None,Some(error),None,None,None,Some(adopted)),
            InitialProfileConstructionOutcomeV1::PreparationFailed{failure,adopted}=>(3,Some(failure),None,None,None,None,Some(adopted)),
            InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,completion}=>(4,Some(failure.failure),None,None,None,Some(completion),failure.rejected_adopted),
            InitialProfileConstructionOutcomeV1::PhaseCompletionFailed{failure}=>(5,Some(failure),None,None,None,None,None),
            InitialProfileConstructionOutcomeV1::HeaderRefused{error}=>(6,None,Some(error),None,None,None,None),
            InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed{failure}=>(7,Some(failure),None,None,None,None,None),
            InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>(8,None,None,Some(header),Some(rows),None,None),
        };
        let adopted_retirement=match adopted{Some(adopted)=>control.drop_proof_with_wasi(adopted,wasi),None=>Ok(())};
        SnapshotPrimaryRetirementV1 {variant,primary,header_error,header,rows,construction_completion,adopted_retirement,export,phase_completion}
    }
}

pub(super) fn construct_snapshot_owned_v1(owners:super::super::control::SnapshotScopeBorrowV1<'_>,claims:&UnverifiedProfileDigestBytesV1,rows:&mut File,snapshot:&mut File)->SnapshotOuterV1{
    let (cache,control,wasi,adopted)=owners.into_parts();
    construct_profile_core_v1(cache,control,wasi,adopted,&selected_initial_profile_v1(),claims,rows,SnapshotBranchV1{output:snapshot})
}

struct SnapshotFoundationPlacesV1<'a> {
    branch:SnapshotBranchV1<'a>,access:SnapshotAccessV1<'a>,access_return:SnapshotAccessV1<'a>,access_option:Option<SnapshotAccessV1<'a>>,
    decision:Result<(usize,SnapshotShapeV1,u64,u64),AError>,shape:SnapshotShapeV1,shape_return:Result<SnapshotShapeV1,AError>,
    storage:SnapshotPhaseStorageV1,storage_return:SnapshotPhaseStorageV1,storage_move:SnapshotPhaseStorageV1,
    attempts:[SnapshotAttemptV1;4],outers:[SnapshotOuterV1;4],outer_option:Option<SnapshotOuterV1>,
    completions:[Result<(),SwiftRunFailure>;4],originals:[InitialProfileConstructionOutcomeV1;2],
    retirement:SnapshotPrimaryRetirementV1,retirement_return:SnapshotPrimaryRetirementV1,
    admission_errors:[AError;4],stop:[Stop;4],borrows:[usize;32],counts:[[u64;9];3],
}
struct SnapshotPhasePlacesV1<'g> {
    plan:SnapshotPlanV1,plan_move:SnapshotPlanV1,
    storage:SnapshotPhaseStorageV1,storage_drop:SnapshotPhaseStorageV1,
    views:[SnapshotViewV2<'g>;3],view_result:Result<SnapshotViewV2<'g>,SnapshotEncodeErrorV2>,
    cursors:[SnapshotCursorV2<'g>;3],cursor_result:Result<SnapshotCursorV2<'g>,SnapshotEncodeErrorV2>,
    blocks:[Option<SnapshotBlockV2<'g>>;3],block_result:Result<Option<SnapshotBlockV2<'g>>,SnapshotEncodeErrorV2>,
    writer:SnapshotWriterV1<'g>,writer_move:SnapshotWriterV1<'g>,
    metadata:[std::fs::Metadata;2],metadata_returns:[Result<std::fs::Metadata,io::Error>;2],
    positions:[Result<u64,io::Error>;2],write_return:Result<usize,io::Error>,
    io_errors:[Option<io::Error>;4],export_errors:[SnapshotExportErrorV1;4],
    observations:[SnapshotObservationV1;3],progress:[SnapshotProgressV1;4],
    shape_counts:[usize;9],identities:[u64;4],counters:[usize;32],
}
pub(super) const SNAPSHOT_FOUNDATION_PLACES_V1:usize=size_of::<SnapshotFoundationPlacesV1<'static>>();
const SNAPSHOT_PHASE_PLACES_V1:usize=super::super::control::SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;
#[cfg(mixer_snapshot_composition_layout)]
#[no_mangle]
pub static MIXER_COMPOSITION_INITIAL_LAYOUTS_V1:[usize;36]=[
 size_of::<OriginalAccessV1<'static>>(),std::mem::align_of::<OriginalAccessV1<'static>>(),
 size_of::<SnapshotAccessV1<'static>>(),std::mem::align_of::<SnapshotAccessV1<'static>>(),
 size_of::<SnapshotShapeV1>(),std::mem::align_of::<SnapshotShapeV1>(),
 size_of::<SnapshotPlanV1>(),std::mem::align_of::<SnapshotPlanV1>(),
 size_of::<SnapshotPhaseStorageV1>(),std::mem::align_of::<SnapshotPhaseStorageV1>(),
 size_of::<SnapshotProgressV1>(),std::mem::align_of::<SnapshotProgressV1>(),
 size_of::<SnapshotCauseV1>(),std::mem::align_of::<SnapshotCauseV1>(),
 size_of::<SnapshotExportErrorV1>(),std::mem::align_of::<SnapshotExportErrorV1>(),
 size_of::<SnapshotAttemptV1>(),std::mem::align_of::<SnapshotAttemptV1>(),
 size_of::<SnapshotOuterV1>(),std::mem::align_of::<SnapshotOuterV1>(),
 size_of::<SnapshotPrimaryRetirementV1>(),std::mem::align_of::<SnapshotPrimaryRetirementV1>(),
 size_of::<SnapshotFoundationPlacesV1<'static>>(),std::mem::align_of::<SnapshotFoundationPlacesV1<'static>>(),
 size_of::<SnapshotPhasePlacesV1<'static>>(),std::mem::align_of::<SnapshotPhasePlacesV1<'static>>(),
 size_of::<InitialProfileConstructionOutcomeV1>(),std::mem::align_of::<InitialProfileConstructionOutcomeV1>(),
 size_of::<InitialProfileBorrowV1<'static>>(),std::mem::align_of::<InitialProfileBorrowV1<'static>>(),
 size_of::<Result<SnapshotOuterV1,SwiftRunFailure>>(),std::mem::align_of::<Result<SnapshotOuterV1,SwiftRunFailure>>(),
 size_of::<OriginalBranchV1>(),std::mem::align_of::<OriginalBranchV1>(),
 size_of::<SnapshotBranchV1<'static>>(),std::mem::align_of::<SnapshotBranchV1<'static>>(),
];


// Compiled in unit mode, deliberately has no test/CLI/export dispatch. A later
// root-selected fresh host can invoke this after exact floor/work/stop release.
#[cfg(test)]
mod future_genuine_composition_v1 {
    use super::*;
    use crate::{Cancellation,experimental_swift_reactor::retained_profile_loader_v1::SelectedValidatedProfileV1};
    use crate::experimental_wasi::{WasiBudget,WasiGrants};
    use std::time::Instant;
    use std::fs::OpenOptions;
    pub(super) fn selected_owned_files_v1(
        selected:SelectedValidatedProfileV1,directory:&std::path::Path,
        wasi:Option<(WasiBudget,WasiGrants)>,
    ){
        // The loader-produced opaque carrier is mandatory. No proof/digest/bool
        // can turn the fixture into authentic selected ingress.
        let mut scope=match selected.into_snapshot_scope_v1(
            selected_initial_profile_v1().budget,Instant::now(),Cancellation::default()){
            Ok(scope)=>scope,
            Err(failure)=>panic!("genuine selected ingress failed: {:?}; retirement {:?}",failure.primary,failure.retirement),
        };
        if let Some((budget,grants))=wasi {
            let attachment=scope.attach_wasi_v1(grants,budget,Instant::now());
            assert!(attachment.construction.is_ok());assert!(attachment.completion.is_ok());
        }
        let mut rows=OpenOptions::new().read(true).write(true).create_new(true).open(directory.join("fresh-primary.rows")).unwrap();
        let mut snapshot=OpenOptions::new().read(true).write(true).create_new(true).open(directory.join("fresh-selected.mixsnb02")).unwrap();
        let claims=UnverifiedProfileDigestBytesV1 {baseline:[1;32],candidate:[2;32],original_input:[3;32],event_schema:[4;32],
            profile_adapter_binary:[5;32],layout_receipt:[6;32],original_validated_snapshot:[7;32],profile_row_body:[8;32]};
        let run=scope.construct_v1(&claims,&mut rows,&mut snapshot);
        let outer=run.outer_v1();
        match &outer.primary {
            InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows:Ok(_)}=>{
                assert_eq!(&header.bytes[..8],b"MIXPRF01");
                std::fs::write(directory.join("fresh-primary.header"),header.bytes).unwrap();
            },_=>panic!("original successful primary was not preserved"),
        }
        match &outer.export {
            SnapshotAttemptV1::Completed(observation)=>{
                assert!(observation.bytes>=2560);assert!(observation.calls>0);
                assert_eq!(snapshot.metadata().unwrap().len(),observation.bytes);
            },_=>panic!("future positive requires separately accepted debit/floor; no success from preparation"),
        }
        assert!(outer.phase_completion.is_ok());
        let finish=run.finish_v1();
        assert!(finish.primary_retirement.adopted_retirement.is_ok());
        assert!(finish.scope_adopted_retirement.is_ok());
        assert!(finish.wasi_retirement.is_ok());
        // Current conservative finalizer is explicitly not healthy cleanup.
        assert_eq!(finish.usage.cleanup_invariant,Some(super::super::super::control::SwiftCleanupInvariant::ConstructionBound));
        assert!(finish.usage.reservations.construction.current>0);
        assert!(finish.usage.reservations.live_tickets>0);
        // File close/custody and release qualification remain the fresh host's
        // independent responsibility; these borrows end at this fixture return.
    }
}
