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
struct UnverifiedProfileDigestBytesV1 {
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
    if cache_out.is_some() { return InitialProfileConstructionOutcomeV1::SlotOccupied { adopted }; }
    if let Err(error)=compare_budget_v1(control.budget(),selected.budget)
        .and_then(|()|compare_local_structure_v1(&selected.local)) {
        return InitialProfileConstructionOutcomeV1::SelectionRefused { error,adopted };
    }
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::boundary(1,control,None);
    let mut preparation=Some(SwiftFunctionCache::prepare(control,wasi,&adopted,CONSTRUCTION_CURSOR_V1));
    let mut phase=match preparation.take().expect("actual prepare return") {
        Ok(phase)=>phase,
        Err(failure)=>return InitialProfileConstructionOutcomeV1::PreparationFailed { failure,adopted },
    };
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::phase_boundary(&mut phase);
    let mut original_return:ConstructionReturnSlot=Some(phase.construct(adopted));
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::completion_boundary(&mut phase);
    match original_return.take().expect("actual constructor return") {
        Err(failure)=>{
            let completion=phase.complete((preparation,original_return));
            return InitialProfileConstructionOutcomeV1::ConstructionFailed { failure,completion };
        },
        Ok(cache)=>*cache_out=Some(cache),
    }
    if let Err(failure)=phase.complete((preparation,original_return)) {
        return InitialProfileConstructionOutcomeV1::PhaseCompletionFailed { failure };
    }
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::boundary(2,control,cache_out.as_mut());
    let cache=cache_out.as_ref().expect("constructed owner remains in caller slot");
    let scalars=match inspect_initial_v1(cache,control,wasi) {
        Ok(scalars)=>scalars,
        Err(ProfileAdmissionFailureV1::Refused(error))=>return InitialProfileConstructionOutcomeV1::HeaderRefused { error },
        Err(ProfileAdmissionFailureV1::Runtime(failure))=>return InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed { failure },
    };
    // Sole guard literal. No prepare/acquisition/callback/reentry follows it.
    let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };
    #[cfg(any(test,mixer_snapshot_encoder_host))]
    snapshot_encoder_host::observe_v2(&initial);
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::mark(3);
    let header=match encode_profile_header_v1(&initial,claims) {
        Ok(header)=>header,
        Err(error)=>return InitialProfileConstructionOutcomeV1::HeaderRefused { error },
    };
    #[cfg(any(test,mixer_initial_profile_component_host))] tests::mark(4);
    let rows=write_initial_profile_rows_v1(&initial,row_output);
    InitialProfileConstructionOutcomeV1::HeaderEncoded { header,rows }
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
