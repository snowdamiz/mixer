//! Data-only contract/layout model. No constructor, guard mint, header encoder,
//! selected-data producer, row bridge or product caller is implemented here.
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
struct InitialProfileBorrowV1<'a> {
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
    type_layout:[LocalTypeLayoutV1;__LAYOUT_ENTRY_COUNT__],
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
