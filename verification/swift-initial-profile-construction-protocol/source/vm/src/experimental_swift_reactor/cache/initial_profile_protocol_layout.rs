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
    type_layout:[LocalTypeLayoutV1;165],
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

pub(super) fn emit_layout_v1() {
    println!("TYPE\t1\t{}\t{}\t{}", "Result<Option<WasiUsage>, SwiftRunFailure>", std::mem::size_of::<Result<Option<WasiUsage>, SwiftRunFailure>>(), std::mem::align_of::<Result<Option<WasiUsage>, SwiftRunFailure>>());
    println!("TYPE\t2\t{}\t{}\t{}", "Option<Result<WasiUsage, SwiftRunFailure>>", std::mem::size_of::<Option<Result<WasiUsage, SwiftRunFailure>>>(), std::mem::align_of::<Option<Result<WasiUsage, SwiftRunFailure>>>());
    println!("TYPE\t3\t{}\t{}\t{}", "Result<WasiUsage, SwiftRunFailure>", std::mem::size_of::<Result<WasiUsage, SwiftRunFailure>>(), std::mem::align_of::<Result<WasiUsage, SwiftRunFailure>>());
    println!("TYPE\t4\t{}\t{}\t{}", "PermanentScalarInventory", std::mem::size_of::<PermanentScalarInventory>(), std::mem::align_of::<PermanentScalarInventory>());
    println!("TYPE\t5\t{}\t{}\t{}", "PermanentBorrowChainInventory", std::mem::size_of::<PermanentBorrowChainInventory>(), std::mem::align_of::<PermanentBorrowChainInventory>());
    println!("TYPE\t6\t{}\t{}\t{}", "Option<PinRecord>", std::mem::size_of::<Option<PinRecord>>(), std::mem::align_of::<Option<PinRecord>>());
    println!("TYPE\t7\t{}\t{}\t{}", "Option<&'static PinRecord>", std::mem::size_of::<Option<&'static PinRecord>>(), std::mem::align_of::<Option<&'static PinRecord>>());
    println!("TYPE\t8\t{}\t{}\t{}", "Option<&'static SwiftSlot>", std::mem::size_of::<Option<&'static SwiftSlot>>(), std::mem::align_of::<Option<&'static SwiftSlot>>());
    println!("TYPE\t9\t{}\t{}\t{}", "Option<&'static DecodedFunction>", std::mem::size_of::<Option<&'static DecodedFunction>>(), std::mem::align_of::<Option<&'static DecodedFunction>>());
    println!("TYPE\t10\t{}\t{}\t{}", "(&'static SwiftFunctionPin, &'static PinRecord)", std::mem::size_of::<(&'static SwiftFunctionPin, &'static PinRecord)>(), std::mem::align_of::<(&'static SwiftFunctionPin, &'static PinRecord)>());
    println!("TYPE\t11\t{}\t{}\t{}", "CacheParts<'static, SwiftMode>", std::mem::size_of::<CacheParts<'static, SwiftMode>>(), std::mem::align_of::<CacheParts<'static, SwiftMode>>());
    println!("TYPE\t12\t{}\t{}\t{}", "CacheViewParts<'static, SwiftMode>", std::mem::size_of::<CacheViewParts<'static, SwiftMode>>(), std::mem::align_of::<CacheViewParts<'static, SwiftMode>>());
    println!("TYPE\t13\t{}\t{}\t{}", "PinRecord", std::mem::size_of::<PinRecord>(), std::mem::align_of::<PinRecord>());
    println!("TYPE\t14\t{}\t{}\t{}", "Result<PinRecord, SwiftRunFailure>", std::mem::size_of::<Result<PinRecord, SwiftRunFailure>>(), std::mem::align_of::<Result<PinRecord, SwiftRunFailure>>());
    println!("TYPE\t15\t{}\t{}\t{}", "FunctionView<'static>", std::mem::size_of::<FunctionView<'static>>(), std::mem::align_of::<FunctionView<'static>>());
    println!("TYPE\t16\t{}\t{}\t{}", "Result<FunctionView<'static>, SwiftRunFailure>", std::mem::size_of::<Result<FunctionView<'static>, SwiftRunFailure>>(), std::mem::align_of::<Result<FunctionView<'static>, SwiftRunFailure>>());
    println!("TYPE\t17\t{}\t{}\t{}", "(SwiftRunFailure, SwiftFunctionPin)", std::mem::size_of::<(SwiftRunFailure, SwiftFunctionPin)>(), std::mem::align_of::<(SwiftRunFailure, SwiftFunctionPin)>());
    println!("TYPE\t18\t{}\t{}\t{}", "Result<(), (SwiftRunFailure, SwiftFunctionPin)>", std::mem::size_of::<Result<(), (SwiftRunFailure, SwiftFunctionPin)>>(), std::mem::align_of::<Result<(), (SwiftRunFailure, SwiftFunctionPin)>>());
    println!("TYPE\t19\t{}\t{}\t{}", "SwiftFunctionPin", std::mem::size_of::<SwiftFunctionPin>(), std::mem::align_of::<SwiftFunctionPin>());
    println!("TYPE\t20\t{}\t{}\t{}", "SwiftCacheUsage", std::mem::size_of::<SwiftCacheUsage>(), std::mem::align_of::<SwiftCacheUsage>());
    println!("TYPE\t21\t{}\t{}\t{}", "SwiftCacheIdentity", std::mem::size_of::<SwiftCacheIdentity>(), std::mem::align_of::<SwiftCacheIdentity>());
    println!("TYPE\t22\t{}\t{}\t{}", "Option<SwiftFunctionCache>", std::mem::size_of::<Option<SwiftFunctionCache>>(), std::mem::align_of::<Option<SwiftFunctionCache>>());
    println!("TYPE\t23\t{}\t{}\t{}", "SwiftFunctionCache", std::mem::size_of::<SwiftFunctionCache>(), std::mem::align_of::<SwiftFunctionCache>());
    println!("TYPE\t24\t{}\t{}\t{}", "Result<CacheCleanupTail<'static>, SwiftRunFailure>", std::mem::size_of::<Result<CacheCleanupTail<'static>, SwiftRunFailure>>(), std::mem::align_of::<Result<CacheCleanupTail<'static>, SwiftRunFailure>>());
    println!("TYPE\t25\t{}\t{}\t{}", "CacheCleanupTail<'static>", std::mem::size_of::<CacheCleanupTail<'static>>(), std::mem::align_of::<CacheCleanupTail<'static>>());
    println!("TYPE\t26\t{}\t{}\t{}", "Option<CacheCleanupTail<'static>>", std::mem::size_of::<Option<CacheCleanupTail<'static>>>(), std::mem::align_of::<Option<CacheCleanupTail<'static>>>());
    println!("TYPE\t27\t{}\t{}\t{}", "CleanupCompletionParts<'static>", std::mem::size_of::<CleanupCompletionParts<'static>>(), std::mem::align_of::<CleanupCompletionParts<'static>>());
    println!("TYPE\t28\t{}\t{}\t{}", "Option<SwiftResident>", std::mem::size_of::<Option<SwiftResident>>(), std::mem::align_of::<Option<SwiftResident>>());
    println!("TYPE\t29\t{}\t{}\t{}", "SwiftResident", std::mem::size_of::<SwiftResident>(), std::mem::align_of::<SwiftResident>());
    println!("TYPE\t30\t{}\t{}\t{}", "DecodedFunction", std::mem::size_of::<DecodedFunction>(), std::mem::align_of::<DecodedFunction>());
    println!("TYPE\t31\t{}\t{}\t{}", "Vec<SwiftSlot>", std::mem::size_of::<Vec<SwiftSlot>>(), std::mem::align_of::<Vec<SwiftSlot>>());
    println!("TYPE\t32\t{}\t{}\t{}", "Vec<PinRecord>", std::mem::size_of::<Vec<PinRecord>>(), std::mem::align_of::<Vec<PinRecord>>());
    println!("TYPE\t33\t{}\t{}\t{}", "Vec<decode::Patch>", std::mem::size_of::<Vec<decode::Patch>>(), std::mem::align_of::<Vec<decode::Patch>>());
    println!("TYPE\t34\t{}\t{}\t{}", "Vec<u8>", std::mem::size_of::<Vec<u8>>(), std::mem::align_of::<Vec<u8>>());
    println!("TYPE\t35\t{}\t{}\t{}", "Vec<Option<ScanPlan>>", std::mem::size_of::<Vec<Option<ScanPlan>>>(), std::mem::align_of::<Vec<Option<ScanPlan>>>());
    println!("TYPE\t36\t{}\t{}\t{}", "SwiftScratch<'static>", std::mem::size_of::<SwiftScratch<'static>>(), std::mem::align_of::<SwiftScratch<'static>>());
    println!("TYPE\t37\t{}\t{}\t{}", "Option<ReservationTicket>", std::mem::size_of::<Option<ReservationTicket>>(), std::mem::align_of::<Option<ReservationTicket>>());
    println!("TYPE\t38\t{}\t{}\t{}", "ReservationTicket", std::mem::size_of::<ReservationTicket>(), std::mem::align_of::<ReservationTicket>());
    println!("TYPE\t39\t{}\t{}\t{}", "CacheControl<'static>", std::mem::size_of::<CacheControl<'static>>(), std::mem::align_of::<CacheControl<'static>>());
    println!("TYPE\t40\t{}\t{}\t{}", "SwiftRunFailure", std::mem::size_of::<SwiftRunFailure>(), std::mem::align_of::<SwiftRunFailure>());
    println!("TYPE\t41\t{}\t{}\t{}", "Option<SwiftRunFailure>", std::mem::size_of::<Option<SwiftRunFailure>>(), std::mem::align_of::<Option<SwiftRunFailure>>());
    println!("TYPE\t42\t{}\t{}\t{}", "Result<(), SwiftRunFailure>", std::mem::size_of::<Result<(), SwiftRunFailure>>(), std::mem::align_of::<Result<(), SwiftRunFailure>>());
    println!("TYPE\t43\t{}\t{}\t{}", "SwiftRunUsage", std::mem::size_of::<SwiftRunUsage>(), std::mem::align_of::<SwiftRunUsage>());
    println!("TYPE\t44\t{}\t{}\t{}", "Option<WasiUsage>", std::mem::size_of::<Option<WasiUsage>>(), std::mem::align_of::<Option<WasiUsage>>());
    println!("TYPE\t45\t{}\t{}\t{}", "Fault", std::mem::size_of::<Fault>(), std::mem::align_of::<Fault>());
    println!("TYPE\t46\t{}\t{}\t{}", "Cursor", std::mem::size_of::<Cursor>(), std::mem::align_of::<Cursor>());
    println!("TYPE\t47\t{}\t{}\t{}", "SwiftReleaseFailure", std::mem::size_of::<SwiftReleaseFailure>(), std::mem::align_of::<SwiftReleaseFailure>());
    println!("TYPE\t48\t{}\t{}\t{}", "Result<(), SwiftReleaseFailure>", std::mem::size_of::<Result<(), SwiftReleaseFailure>>(), std::mem::align_of::<Result<(), SwiftReleaseFailure>>());
    println!("TYPE\t49\t{}\t{}\t{}", "ValidatedSwiftReactor", std::mem::size_of::<ValidatedSwiftReactor>(), std::mem::align_of::<ValidatedSwiftReactor>());
    println!("TYPE\t50\t{}\t{}\t{}", "Option<ScanPlan>", std::mem::size_of::<Option<ScanPlan>>(), std::mem::align_of::<Option<ScanPlan>>());
    println!("TYPE\t51\t{}\t{}\t{}", "Result<CacheConstructionPhase<'static>, SwiftRunFailure>", std::mem::size_of::<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>(), std::mem::align_of::<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>());
    println!("TYPE\t52\t{}\t{}\t{}", "Result<ReservationTicket, SwiftRunFailure>", std::mem::size_of::<Result<ReservationTicket, SwiftRunFailure>>(), std::mem::align_of::<Result<ReservationTicket, SwiftRunFailure>>());
    println!("TYPE\t53\t{}\t{}\t{}", "std::collections::TryReserveError", std::mem::size_of::<std::collections::TryReserveError>(), std::mem::align_of::<std::collections::TryReserveError>());
    println!("TYPE\t54\t{}\t{}\t{}", "Result<(), std::collections::TryReserveError>", std::mem::size_of::<Result<(), std::collections::TryReserveError>>(), std::mem::align_of::<Result<(), std::collections::TryReserveError>>());
    println!("TYPE\t55\t{}\t{}\t{}", "Result<u64, u64>", std::mem::size_of::<Result<u64, u64>>(), std::mem::align_of::<Result<u64, u64>>());
    println!("TYPE\t56\t{}\t{}\t{}", "Option<u64>", std::mem::size_of::<Option<u64>>(), std::mem::align_of::<Option<u64>>());
    println!("TYPE\t57\t{}\t{}\t{}", "Result<u64, SwiftRunFailure>", std::mem::size_of::<Result<u64, SwiftRunFailure>>(), std::mem::align_of::<Result<u64, SwiftRunFailure>>());
    println!("TYPE\t58\t{}\t{}\t{}", "ConstructionScalarInventory", std::mem::size_of::<ConstructionScalarInventory>(), std::mem::align_of::<ConstructionScalarInventory>());
    println!("TYPE\t59\t{}\t{}\t{}", "ConstructionBorrowChainInventory", std::mem::size_of::<ConstructionBorrowChainInventory>(), std::mem::align_of::<ConstructionBorrowChainInventory>());
    println!("TYPE\t60\t{}\t{}\t{}", "SwiftRunBudget", std::mem::size_of::<SwiftRunBudget>(), std::mem::align_of::<SwiftRunBudget>());
    println!("TYPE\t61\t{}\t{}\t{}", "(u64, SwiftCacheUsage)", std::mem::size_of::<(u64, SwiftCacheUsage)>(), std::mem::align_of::<(u64, SwiftCacheUsage)>());
    println!("TYPE\t62\t{}\t{}\t{}", "Result<(u64, SwiftCacheUsage), SwiftRunFailure>", std::mem::size_of::<Result<(u64, SwiftCacheUsage), SwiftRunFailure>>(), std::mem::align_of::<Result<(u64, SwiftCacheUsage), SwiftRunFailure>>());
    println!("TYPE\t63\t{}\t{}\t{}", "PreparedBounds", std::mem::size_of::<PreparedBounds>(), std::mem::align_of::<PreparedBounds>());
    println!("TYPE\t64\t{}\t{}\t{}", "CacheConstructionPhase<'static>", std::mem::size_of::<CacheConstructionPhase<'static>>(), std::mem::align_of::<CacheConstructionPhase<'static>>());
    println!("TYPE\t65\t{}\t{}\t{}", "Partial", std::mem::size_of::<Partial>(), std::mem::align_of::<Partial>());
    println!("TYPE\t66\t{}\t{}\t{}", "Result<SwiftFunctionCache, CacheConstructionFailure>", std::mem::size_of::<Result<SwiftFunctionCache, CacheConstructionFailure>>(), std::mem::align_of::<Result<SwiftFunctionCache, CacheConstructionFailure>>());
    println!("TYPE\t67\t{}\t{}\t{}", "CacheConstructionFailure", std::mem::size_of::<CacheConstructionFailure>(), std::mem::align_of::<CacheConstructionFailure>());
    println!("TYPE\t68\t{}\t{}\t{}", "ConstructionReturnSlot", std::mem::size_of::<ConstructionReturnSlot>(), std::mem::align_of::<ConstructionReturnSlot>());
    println!("TYPE\t69\t{}\t{}\t{}", "Option<AdoptedProof>", std::mem::size_of::<Option<AdoptedProof>>(), std::mem::align_of::<Option<AdoptedProof>>());
    println!("TYPE\t70\t{}\t{}\t{}", "PlanInventory", std::mem::size_of::<PlanInventory>(), std::mem::align_of::<PlanInventory>());
    println!("TYPE\t71\t{}\t{}\t{}", "Result<CacheOperationPhase<'static>, SwiftRunFailure>", std::mem::size_of::<Result<CacheOperationPhase<'static>, SwiftRunFailure>>(), std::mem::align_of::<Result<CacheOperationPhase<'static>, SwiftRunFailure>>());
    println!("TYPE\t72\t{}\t{}\t{}", "OperationScalarInventory", std::mem::size_of::<OperationScalarInventory>(), std::mem::align_of::<OperationScalarInventory>());
    println!("TYPE\t73\t{}\t{}\t{}", "ResidentIndexInventory", std::mem::size_of::<ResidentIndexInventory>(), std::mem::align_of::<ResidentIndexInventory>());
    println!("TYPE\t74\t{}\t{}\t{}", "ResidentMatch", std::mem::size_of::<ResidentMatch>(), std::mem::align_of::<ResidentMatch>());
    println!("TYPE\t75\t{}\t{}\t{}", "Option<ResidentMatch>", std::mem::size_of::<Option<ResidentMatch>>(), std::mem::align_of::<Option<ResidentMatch>>());
    println!("TYPE\t76\t{}\t{}\t{}", "OperationBorrowChainInventory", std::mem::size_of::<OperationBorrowChainInventory>(), std::mem::align_of::<OperationBorrowChainInventory>());
    println!("TYPE\t77\t{}\t{}\t{}", "(&'static SwiftPolicy<'static>,)", std::mem::size_of::<(&'static SwiftPolicy<'static>,)>(), std::mem::align_of::<(&'static SwiftPolicy<'static>,)>());
    println!("TYPE\t78\t{}\t{}\t{}", "Option<FunctionSpanView<'static>>", std::mem::size_of::<Option<FunctionSpanView<'static>>>(), std::mem::align_of::<Option<FunctionSpanView<'static>>>());
    println!("TYPE\t79\t{}\t{}\t{}", "Option<crate::experimental::descriptors::SignatureView<'static>>", std::mem::size_of::<Option<crate::experimental::descriptors::SignatureView<'static>>>(), std::mem::align_of::<Option<crate::experimental::descriptors::SignatureView<'static>>>());
    println!("TYPE\t80\t{}\t{}\t{}", "Option<&'static mut DecodedFunction>", std::mem::size_of::<Option<&'static mut DecodedFunction>>(), std::mem::align_of::<Option<&'static mut DecodedFunction>>());
    println!("TYPE\t81\t{}\t{}\t{}", "Option<&'static mut crate::experimental::cache::DecodedInstruction>", std::mem::size_of::<Option<&'static mut crate::experimental::cache::DecodedInstruction>>(), std::mem::align_of::<Option<&'static mut crate::experimental::cache::DecodedInstruction>>());
    println!("TYPE\t82\t{}\t{}\t{}", "[u8; 4]", std::mem::size_of::<[u8; 4]>(), std::mem::align_of::<[u8; 4]>());
    println!("TYPE\t83\t{}\t{}\t{}", "[u8; 8]", std::mem::size_of::<[u8; 8]>(), std::mem::align_of::<[u8; 8]>());
    println!("TYPE\t84\t{}\t{}\t{}", "Result<[u8; 4], std::array::TryFromSliceError>", std::mem::size_of::<Result<[u8; 4], std::array::TryFromSliceError>>(), std::mem::align_of::<Result<[u8; 4], std::array::TryFromSliceError>>());
    println!("TYPE\t85\t{}\t{}\t{}", "Result<[u8; 8], std::array::TryFromSliceError>", std::mem::size_of::<Result<[u8; 8], std::array::TryFromSliceError>>(), std::mem::align_of::<Result<[u8; 8], std::array::TryFromSliceError>>());
    println!("TYPE\t86\t{}\t{}\t{}", "(&'static mut SwiftMeter<'static, 'static>,)", std::mem::size_of::<(&'static mut SwiftMeter<'static, 'static>,)>(), std::mem::align_of::<(&'static mut SwiftMeter<'static, 'static>,)>());
    println!("TYPE\t87\t{}\t{}\t{}", "(&'static u32,)", std::mem::size_of::<(&'static u32,)>(), std::mem::align_of::<(&'static u32,)>());
    println!("TYPE\t88\t{}\t{}\t{}", "(&'static SwiftSlot, &'static CacheFields<'static, SwiftMode>)", std::mem::size_of::<(&'static SwiftSlot, &'static CacheFields<'static, SwiftMode>)>(), std::mem::align_of::<(&'static SwiftSlot, &'static CacheFields<'static, SwiftMode>)>());
    println!("TYPE\t89\t{}\t{}\t{}", "crate::experimental::descriptors::SignatureView<'static>", std::mem::size_of::<crate::experimental::descriptors::SignatureView<'static>>(), std::mem::align_of::<crate::experimental::descriptors::SignatureView<'static>>());
    println!("TYPE\t90\t{}\t{}\t{}", "Result<SwiftPolicy<'static>, SwiftRunFailure>", std::mem::size_of::<Result<SwiftPolicy<'static>, SwiftRunFailure>>(), std::mem::align_of::<Result<SwiftPolicy<'static>, SwiftRunFailure>>());
    println!("TYPE\t91\t{}\t{}\t{}", "Result<decode::Counts, SwiftRunFailure>", std::mem::size_of::<Result<decode::Counts, SwiftRunFailure>>(), std::mem::align_of::<Result<decode::Counts, SwiftRunFailure>>());
    println!("TYPE\t92\t{}\t{}\t{}", "Result<usize, SwiftRunFailure>", std::mem::size_of::<Result<usize, SwiftRunFailure>>(), std::mem::align_of::<Result<usize, SwiftRunFailure>>());
    println!("TYPE\t93\t{}\t{}\t{}", "Result<u8, SwiftRunFailure>", std::mem::size_of::<Result<u8, SwiftRunFailure>>(), std::mem::align_of::<Result<u8, SwiftRunFailure>>());
    println!("TYPE\t94\t{}\t{}\t{}", "Result<u32, SwiftRunFailure>", std::mem::size_of::<Result<u32, SwiftRunFailure>>(), std::mem::align_of::<Result<u32, SwiftRunFailure>>());
    println!("TYPE\t95\t{}\t{}\t{}", "Result<i64, SwiftRunFailure>", std::mem::size_of::<Result<i64, SwiftRunFailure>>(), std::mem::align_of::<Result<i64, SwiftRunFailure>>());
    println!("TYPE\t96\t{}\t{}\t{}", "Result<crate::Type, SwiftRunFailure>", std::mem::size_of::<Result<crate::Type, SwiftRunFailure>>(), std::mem::align_of::<Result<crate::Type, SwiftRunFailure>>());
    println!("TYPE\t97\t{}\t{}\t{}", "Result<&'static [u8], SwiftRunFailure>", std::mem::size_of::<Result<&'static [u8], SwiftRunFailure>>(), std::mem::align_of::<Result<&'static [u8], SwiftRunFailure>>());
    println!("TYPE\t98\t{}\t{}\t{}", "crate::Value", std::mem::size_of::<crate::Value>(), std::mem::align_of::<crate::Value>());
    println!("TYPE\t99\t{}\t{}\t{}", "crate::experimental::cache::Operation", std::mem::size_of::<crate::experimental::cache::Operation>(), std::mem::align_of::<crate::experimental::cache::Operation>());
    println!("TYPE\t100\t{}\t{}\t{}", "crate::experimental::cache::DecodedInstruction", std::mem::size_of::<crate::experimental::cache::DecodedInstruction>(), std::mem::align_of::<crate::experimental::cache::DecodedInstruction>());
    println!("TYPE\t101\t{}\t{}\t{}", "decode::Patch", std::mem::size_of::<decode::Patch>(), std::mem::align_of::<decode::Patch>());
    println!("TYPE\t102\t{}\t{}\t{}", "Vec<crate::Type>", std::mem::size_of::<Vec<crate::Type>>(), std::mem::align_of::<Vec<crate::Type>>());
    println!("TYPE\t103\t{}\t{}\t{}", "Vec<crate::experimental::cache::DecodedInstruction>", std::mem::size_of::<Vec<crate::experimental::cache::DecodedInstruction>>(), std::mem::align_of::<Vec<crate::experimental::cache::DecodedInstruction>>());
    println!("TYPE\t104\t{}\t{}\t{}", "Vec<u32>", std::mem::size_of::<Vec<u32>>(), std::mem::align_of::<Vec<u32>>());
    println!("TYPE\t105\t{}\t{}\t{}", "Result<Vec<crate::Type>, SwiftRunFailure>", std::mem::size_of::<Result<Vec<crate::Type>, SwiftRunFailure>>(), std::mem::align_of::<Result<Vec<crate::Type>, SwiftRunFailure>>());
    println!("TYPE\t106\t{}\t{}\t{}", "Result<Vec<crate::experimental::cache::DecodedInstruction>, SwiftRunFailure>", std::mem::size_of::<Result<Vec<crate::experimental::cache::DecodedInstruction>, SwiftRunFailure>>(), std::mem::align_of::<Result<Vec<crate::experimental::cache::DecodedInstruction>, SwiftRunFailure>>());
    println!("TYPE\t107\t{}\t{}\t{}", "Result<Vec<u32>, SwiftRunFailure>", std::mem::size_of::<Result<Vec<u32>, SwiftRunFailure>>(), std::mem::align_of::<Result<Vec<u32>, SwiftRunFailure>>());
    println!("TYPE\t108\t{}\t{}\t{}", "CacheOperationPhase<'static>", std::mem::size_of::<CacheOperationPhase<'static>>(), std::mem::align_of::<CacheOperationPhase<'static>>());
    println!("TYPE\t109\t{}\t{}\t{}", "CacheFields<'static, SwiftMode>", std::mem::size_of::<CacheFields<'static, SwiftMode>>(), std::mem::align_of::<CacheFields<'static, SwiftMode>>());
    println!("TYPE\t110\t{}\t{}\t{}", "SwiftMeter<'static, 'static>", std::mem::size_of::<SwiftMeter<'static, 'static>>(), std::mem::align_of::<SwiftMeter<'static, 'static>>());
    println!("TYPE\t111\t{}\t{}\t{}", "decode::Reader<'static>", std::mem::size_of::<decode::Reader<'static>>(), std::mem::align_of::<decode::Reader<'static>>());
    println!("TYPE\t112\t{}\t{}\t{}", "decode::PassParts<'static>", std::mem::size_of::<decode::PassParts<'static>>(), std::mem::align_of::<decode::PassParts<'static>>());
    println!("TYPE\t113\t{}\t{}\t{}", "decode::Counts", std::mem::size_of::<decode::Counts>(), std::mem::align_of::<decode::Counts>());
    println!("TYPE\t114\t{}\t{}\t{}", "SwiftPolicy<'static>", std::mem::size_of::<SwiftPolicy<'static>>(), std::mem::align_of::<SwiftPolicy<'static>>());
    println!("TYPE\t115\t{}\t{}\t{}", "[bool; 64]", std::mem::size_of::<[bool; 64]>(), std::mem::align_of::<[bool; 64]>());
    println!("TYPE\t116\t{}\t{}\t{}", "Result<SwiftResident, SwiftRunFailure>", std::mem::size_of::<Result<SwiftResident, SwiftRunFailure>>(), std::mem::align_of::<Result<SwiftResident, SwiftRunFailure>>());
    println!("TYPE\t117\t{}\t{}\t{}", "Result<DecodedFunction, SwiftRunFailure>", std::mem::size_of::<Result<DecodedFunction, SwiftRunFailure>>(), std::mem::align_of::<Result<DecodedFunction, SwiftRunFailure>>());
    println!("TYPE\t118\t{}\t{}\t{}", "Result<SwiftFunctionPin, SwiftRunFailure>", std::mem::size_of::<Result<SwiftFunctionPin, SwiftRunFailure>>(), std::mem::align_of::<Result<SwiftFunctionPin, SwiftRunFailure>>());
    println!("TYPE\t119\t{}\t{}\t{}", "OperationReturnSlot", std::mem::size_of::<OperationReturnSlot>(), std::mem::align_of::<OperationReturnSlot>());
    println!("TYPE\t120\t{}\t{}\t{}", "FunctionSpanView<'static>", std::mem::size_of::<FunctionSpanView<'static>>(), std::mem::align_of::<FunctionSpanView<'static>>());
    println!("TYPE\t121\t{}\t{}\t{}", "RuntimeControl", std::mem::size_of::<RuntimeControl>(), std::mem::align_of::<RuntimeControl>());
    println!("TYPE\t122\t{}\t{}\t{}", "AccountedWasi", std::mem::size_of::<AccountedWasi>(), std::mem::align_of::<AccountedWasi>());
    println!("TYPE\t123\t{}\t{}\t{}", "AdoptedProof", std::mem::size_of::<AdoptedProof>(), std::mem::align_of::<AdoptedProof>());
    println!("TYPE\t124\t{}\t{}\t{}", "SwiftSlot", std::mem::size_of::<SwiftSlot>(), std::mem::align_of::<SwiftSlot>());
    println!("TYPE\t125\t{}\t{}\t{}", "ScanPlan", std::mem::size_of::<ScanPlan>(), std::mem::align_of::<ScanPlan>());
    println!("TYPE\t126\t{}\t{}\t{}", "ProfileHeaderErrorV1", std::mem::size_of::<ProfileHeaderErrorV1>(), std::mem::align_of::<ProfileHeaderErrorV1>());
    println!("TYPE\t127\t{}\t{}\t{}", "InitialProfileScalarsV1", std::mem::size_of::<InitialProfileScalarsV1>(), std::mem::align_of::<InitialProfileScalarsV1>());
    println!("TYPE\t128\t{}\t{}\t{}", "UnverifiedProfileDigestBytesV1", std::mem::size_of::<UnverifiedProfileDigestBytesV1>(), std::mem::align_of::<UnverifiedProfileDigestBytesV1>());
    println!("TYPE\t129\t{}\t{}\t{}", "UnverifiedProfileHeaderV1", std::mem::size_of::<UnverifiedProfileHeaderV1>(), std::mem::align_of::<UnverifiedProfileHeaderV1>());
    println!("TYPE\t130\t{}\t{}\t{}", "InitialProfileBorrowV1<'static>", std::mem::size_of::<InitialProfileBorrowV1<'static>>(), std::mem::align_of::<InitialProfileBorrowV1<'static>>());
    println!("TYPE\t131\t{}\t{}\t{}", "ProfileAdmissionFailureV1", std::mem::size_of::<ProfileAdmissionFailureV1>(), std::mem::align_of::<ProfileAdmissionFailureV1>());
    println!("TYPE\t132\t{}\t{}\t{}", "InitialProfileConstructionOutcomeV1", std::mem::size_of::<InitialProfileConstructionOutcomeV1>(), std::mem::align_of::<InitialProfileConstructionOutcomeV1>());
    println!("TYPE\t133\t{}\t{}\t{}", "Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>", std::mem::size_of::<Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>>(), std::mem::align_of::<Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>>());
    println!("TYPE\t134\t{}\t{}\t{}", "ProfileRowsObservationV1", std::mem::size_of::<ProfileRowsObservationV1>(), std::mem::align_of::<ProfileRowsObservationV1>());
    println!("TYPE\t135\t{}\t{}\t{}", "ProfileAdapterErrorV1", std::mem::size_of::<ProfileAdapterErrorV1>(), std::mem::align_of::<ProfileAdapterErrorV1>());
    println!("TYPE\t136\t{}\t{}\t{}", "Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>", std::mem::size_of::<Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>>(), std::mem::align_of::<Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>>());
    println!("TYPE\t137\t{}\t{}\t{}", "Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>", std::mem::size_of::<Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>>(), std::mem::align_of::<Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>>());
    println!("TYPE\t138\t{}\t{}\t{}", "Result<InitialProfileBorrowV1<'static>, ProfileAdmissionFailureV1>", std::mem::size_of::<Result<InitialProfileBorrowV1<'static>, ProfileAdmissionFailureV1>>(), std::mem::align_of::<Result<InitialProfileBorrowV1<'static>, ProfileAdmissionFailureV1>>());
    println!("TYPE\t139\t{}\t{}\t{}", "Option<InitialProfileConstructionOutcomeV1>", std::mem::size_of::<Option<InitialProfileConstructionOutcomeV1>>(), std::mem::align_of::<Option<InitialProfileConstructionOutcomeV1>>());
    println!("TYPE\t140\t{}\t{}\t{}", "Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>", std::mem::size_of::<Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>>(), std::mem::align_of::<Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>>());
    println!("TYPE\t141\t{}\t{}\t{}", "(Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>, ConstructionReturnSlot)", std::mem::size_of::<(Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>, ConstructionReturnSlot)>(), std::mem::align_of::<(Option<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>, ConstructionReturnSlot)>());
    println!("TYPE\t142\t{}\t{}\t{}", "Option<CacheConstructionFailure>", std::mem::size_of::<Option<CacheConstructionFailure>>(), std::mem::align_of::<Option<CacheConstructionFailure>>());
    println!("TYPE\t143\t{}\t{}\t{}", "WrapperArgumentsV1<'static>", std::mem::size_of::<WrapperArgumentsV1<'static>>(), std::mem::align_of::<WrapperArgumentsV1<'static>>());
    println!("TYPE\t144\t{}\t{}\t{}", "WrapperPhaseStorageV1<'static>", std::mem::size_of::<WrapperPhaseStorageV1<'static>>(), std::mem::align_of::<WrapperPhaseStorageV1<'static>>());
    println!("TYPE\t145\t{}\t{}\t{}", "WrapperEmissionStorageV1<'static>", std::mem::size_of::<WrapperEmissionStorageV1<'static>>(), std::mem::align_of::<WrapperEmissionStorageV1<'static>>());
    println!("TYPE\t146\t{}\t{}\t{}", "WrapperCallerStorageV1", std::mem::size_of::<WrapperCallerStorageV1>(), std::mem::align_of::<WrapperCallerStorageV1>());
    println!("TYPE\t147\t{}\t{}\t{}", "WrapperMoveStorageV1", std::mem::size_of::<WrapperMoveStorageV1>(), std::mem::align_of::<WrapperMoveStorageV1>());
    println!("TYPE\t148\t{}\t{}\t{}", "SelectedInitialProfileV1", std::mem::size_of::<SelectedInitialProfileV1>(), std::mem::align_of::<SelectedInitialProfileV1>());
    println!("TYPE\t149\t{}\t{}\t{}", "SelectedLocalStructureV1", std::mem::size_of::<SelectedLocalStructureV1>(), std::mem::align_of::<SelectedLocalStructureV1>());
    println!("TYPE\t150\t{}\t{}\t{}", "LocalTypeLayoutV1", std::mem::size_of::<LocalTypeLayoutV1>(), std::mem::align_of::<LocalTypeLayoutV1>());
    println!("TYPE\t151\t{}\t{}\t{}", "File", std::mem::size_of::<File>(), std::mem::align_of::<File>());
    println!("TYPE\t152\t{}\t{}\t{}", "std::fs::Metadata", std::mem::size_of::<std::fs::Metadata>(), std::mem::align_of::<std::fs::Metadata>());
    println!("TYPE\t153\t{}\t{}\t{}", "std::io::Error", std::mem::size_of::<std::io::Error>(), std::mem::align_of::<std::io::Error>());
    println!("TYPE\t154\t{}\t{}\t{}", "Result<(), std::io::Error>", std::mem::size_of::<Result<(), std::io::Error>>(), std::mem::align_of::<Result<(), std::io::Error>>());
    println!("TYPE\t155\t{}\t{}\t{}", "Result<usize, std::io::Error>", std::mem::size_of::<Result<usize, std::io::Error>>(), std::mem::align_of::<Result<usize, std::io::Error>>());
    println!("TYPE\t156\t{}\t{}\t{}", "Result<u64, std::io::Error>", std::mem::size_of::<Result<u64, std::io::Error>>(), std::mem::align_of::<Result<u64, std::io::Error>>());
    println!("TYPE\t157\t{}\t{}\t{}", "Result<std::fs::Metadata, std::io::Error>", std::mem::size_of::<Result<std::fs::Metadata, std::io::Error>>(), std::mem::align_of::<Result<std::fs::Metadata, std::io::Error>>());
    println!("TYPE\t158\t{}\t{}\t{}", "[u8; 4096]", std::mem::size_of::<[u8; 4096]>(), std::mem::align_of::<[u8; 4096]>());
    println!("TYPE\t159\t{}\t{}\t{}", "[u8; 512]", std::mem::size_of::<[u8; 512]>(), std::mem::align_of::<[u8; 512]>());
    println!("TYPE\t160\t{}\t{}\t{}", "Option<AccountedWasi>", std::mem::size_of::<Option<AccountedWasi>>(), std::mem::align_of::<Option<AccountedWasi>>());
    println!("TYPE\t161\t{}\t{}\t{}", "&'static SelectedInitialProfileV1", std::mem::size_of::<&'static SelectedInitialProfileV1>(), std::mem::align_of::<&'static SelectedInitialProfileV1>());
    println!("TYPE\t162\t{}\t{}\t{}", "&'static mut Option<SwiftFunctionCache>", std::mem::size_of::<&'static mut Option<SwiftFunctionCache>>(), std::mem::align_of::<&'static mut Option<SwiftFunctionCache>>());
    println!("TYPE\t163\t{}\t{}\t{}", "&'static mut File", std::mem::size_of::<&'static mut File>(), std::mem::align_of::<&'static mut File>());
    println!("TYPE\t164\t{}\t{}\t{}", "u64", std::mem::size_of::<u64>(), std::mem::align_of::<u64>());
    println!("TYPE\t165\t{}\t{}\t{}", "usize", std::mem::size_of::<usize>(), std::mem::align_of::<usize>());
    println!("VALUE\tcache_cleanup_temporary_bytes\t{}", cache_cleanup_temporary_bytes().unwrap());
    println!("VALUE\tcache_header_bytes\t{}", cache_header_bytes().unwrap());
    println!("VALUE\tcache_construction_bytes\t{}", cache_construction_bytes().unwrap());
    println!("VALUE\tcache_operation_bytes\t{}", cache_operation_bytes().unwrap());
    println!("VALUE\tcache_fixed_64_slots_64_pins\t{}", cache_header_bytes().unwrap()+64*size_of::<SwiftSlot>()+64*size_of::<PinRecord>()+512*size_of::<decode::Patch>());
}
