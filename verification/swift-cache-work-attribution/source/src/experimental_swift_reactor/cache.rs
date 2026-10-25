//! Private, proof-preserving cache. No instantiation or execution entry point.
#![allow(dead_code)]
#![allow(clippy::result_large_err)]
use super::control::*;
use super::ValidatedSwiftReactor;
use crate::experimental::cache::{
    borrowed::*, decode, CacheFailureKind, DecodedFunction, FunctionView, PinRecord,
};
use crate::experimental::descriptors::FunctionSpanView;
use crate::experimental_wasi::{accounted::AccountedWasi, WasiUsage};
use std::mem::{size_of, take};
use std::sync::atomic::{AtomicU64, Ordering};

const PATCH_CAPACITY: usize = 512;
static NEXT_OWNER: AtomicU64 = AtomicU64::new(1);
// The same checked increment and orderings are used by the production owner
// allocator and the isolated test counter. The global counter is never seeded.
fn allocate_owner(counter: &AtomicU64) -> Result<u64, u64> {
    counter.try_update(Ordering::Relaxed, Ordering::Relaxed, |n| n.checked_add(1))
}
#[cfg(not(test))]
fn next_owner() -> Result<u64, u64> {
    allocate_owner(&NEXT_OWNER)
}
#[cfg(test)]
thread_local! {
    static TEST_OWNER_ENABLED: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
    static TEST_OWNER_COUNTER: AtomicU64 = const { AtomicU64::new(1) };
}
#[cfg(test)]
fn next_owner() -> Result<u64, u64> {
    TEST_OWNER_ENABLED.with(|enabled| {
        if enabled.get() {
            TEST_OWNER_COUNTER.with(allocate_owner)
        } else {
            allocate_owner(&NEXT_OWNER)
        }
    })
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct SwiftCacheUsage {
    pub fixed_reserved: usize,
    pub resident_bytes: usize,
    pub pinned_bytes: usize,
    pub construction_bytes: usize,
    pub peak_resident_bytes: usize,
    pub peak_pinned_bytes: usize,
    pub peak_construction_bytes: usize,
    pub active_pins: usize,
    pub hits: u64,
    pub misses: u64,
    pub decodes: u64,
    pub evictions: u64,
}
statistics!(SwiftCacheUsage);
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SwiftCacheIdentity {
    pub owner: u64,
    pub validator_revision: u32,
    pub decoder_revision: u32,
    pub policy: &'static str,
}
#[derive(Debug)]
pub(crate) struct SwiftFunctionPin {
    owner: u64,
    slot: usize,
    nonce: u64,
}
impl PinToken for SwiftFunctionPin {
    fn new(owner: u64, slot: usize, nonce: u64) -> Self {
        Self { owner, slot, nonce }
    }
    fn owner(&self) -> u64 {
        self.owner
    }
    fn slot(&self) -> usize {
        self.slot
    }
    fn nonce(&self) -> u64 {
        self.nonce
    }
}
pub(crate) struct SwiftReleaseFailure {
    pub failure: SwiftRunFailure,
    pin: SwiftFunctionPin,
}
impl SwiftReleaseFailure {
    pub(crate) fn into_pin(self) -> SwiftFunctionPin {
        self.pin
    }
}
pub(crate) struct SwiftResident {
    decoded: DecodedFunction,
    ticket: ReservationTicket,
}
pub(crate) struct SwiftSlot {
    resident: Option<SwiftResident>,
    pins: usize,
    last_used: u64,
}
impl CacheSlot for SwiftSlot {
    type Resident = SwiftResident;
    fn entry(&self) -> Option<&DecodedFunction> {
        self.resident.as_ref().map(|r| &r.decoded)
    }
    fn take(&mut self) -> Option<SwiftResident> {
        self.resident.take()
    }
    fn set(&mut self, r: SwiftResident) {
        self.resident = Some(r);
    }
    fn pins(&self) -> usize {
        self.pins
    }
    fn set_pins(&mut self, n: usize) {
        self.pins = n;
    }
    fn last_used(&self) -> u64 {
        self.last_used
    }
    fn set_last_used(&mut self, n: u64) {
        self.last_used = n;
    }
}
pub(crate) struct SwiftFunctionCache {
    adopted: AdoptedProof,
    usage: SwiftCacheUsage,
    owner: u64,
    next_nonce: u64,
    slots: Vec<SwiftSlot>,
    pins: Vec<PinRecord>,
    patches: Vec<decode::Patch>,
    buffers: [Option<ReservationTicket>; 3],
    header: Option<ReservationTicket>,
}
/// A wrapper exists only after the existing construction ticket is enlarged.
pub(crate) struct CacheControl<'a> {
    control: &'a mut RuntimeControl,
    wasi: Option<&'a AccountedWasi>,
    cursor: Cursor,
}
pub(crate) struct CacheConstructionPhase<'a> {
    control: CacheControl<'a>,
    previous_bound: usize,
    constructed: bool,
}
pub(crate) struct CacheOperationPhase<'a> {
    control: CacheControl<'a>,
    previous_bound: usize,
}
// Caller-owned return slots are explicitly consumed by phase completion. Their
// concrete Option/Result shapes are reserved before either phase exists.
type ConstructionReturnSlot = Option<Result<SwiftFunctionCache, CacheConstructionFailure>>;
type OperationReturnSlot = Option<Result<SwiftFunctionPin, SwiftRunFailure>>;
pub(crate) struct CacheConstructionFailure {
    pub failure: SwiftRunFailure,
    pub rejected_adopted: Option<AdoptedProof>,
}
#[must_use = "The cache header remains charged until the caller drops its return/owner storage through complete"]
pub(crate) struct CacheCleanupTail<'a> {
    control: &'a mut RuntimeControl,
    wasi: Option<&'a AccountedWasi>,
    header: Option<ReservationTicket>,
    failure: Option<SwiftRunFailure>,
}
struct Partial {
    adopted: Option<AdoptedProof>,
    slots: Vec<SwiftSlot>,
    pins: Vec<PinRecord>,
    patches: Vec<decode::Patch>,
    buffers: [Option<ReservationTicket>; 3],
    header: Option<ReservationTicket>,
}
impl Partial {
    fn new(adopted: AdoptedProof) -> Self {
        Self {
            adopted: Some(adopted),
            slots: Vec::new(),
            pins: Vec::new(),
            patches: Vec::new(),
            buffers: std::array::from_fn(|_| None),
            header: None,
        }
    }
    fn cleanup(mut self, control: &mut CacheControl<'_>) {
        if let Some(ticket) = self.buffers[0].take() {
            let _ = control.drop_reserved(take(&mut self.slots), ticket);
        }
        if let Some(ticket) = self.buffers[1].take() {
            let _ = control.drop_reserved(take(&mut self.pins), ticket);
        }
        if let Some(ticket) = self.buffers[2].take() {
            let _ = control.drop_reserved(take(&mut self.patches), ticket);
        }
        if let Some(adopted) = self.adopted.take() {
            let observation = control.observation();
            let _ = control.control.drop_proof_with_wasi(adopted, observation);
        }
        if let Some(header) = self.header.take() {
            let _ = control.drop_reserved(self, header);
        }
    }
}
// Each inventory field names an actual scalar, borrow or iterator binding in
// the nonrecursive private call chains. Three inventories conservatively cover
// source, argument/return and caller transfers; no bytes inside a live owner are
// reused. These model types are measured, including their own alignment.
struct ConstructionBorrowChainInventory {
    prepare_control: &'static mut RuntimeControl,
    prepare_wasi: Option<&'static AccountedWasi>,
    prepare_adopted: &'static AdoptedProof,
    construct_phase: &'static mut CacheConstructionPhase<'static>,
    construct_partial_phase: &'static mut CacheConstructionPhase<'static>,
    construct_partial_partial: &'static mut Partial,
    partial_cleanup_partial: &'static mut Partial,
    partial_cleanup_control: &'static mut CacheControl<'static>,
    reserve_slots_values: &'static mut Vec<SwiftSlot>,
    reserve_slots_control: &'static mut CacheControl<'static>,
    reserve_pins_values: &'static mut Vec<PinRecord>,
    reserve_pins_control: &'static mut CacheControl<'static>,
    reserve_patches_values: &'static mut Vec<decode::Patch>,
    reserve_patches_control: &'static mut CacheControl<'static>,
    control_check_receiver: &'static mut CacheControl<'static>,
    control_work_receiver: &'static mut CacheControl<'static>,
    control_error_receiver: &'static mut CacheControl<'static>,
    control_admit_receiver: &'static mut CacheControl<'static>,
    control_exact_receiver: &'static mut CacheControl<'static>,
    control_drop_reserved_receiver: &'static mut CacheControl<'static>,
    control_observation_receiver: &'static mut CacheControl<'static>,
    owner_allocator_argument: &'static AtomicU64,
    owner_allocator_counter: &'static AtomicU64,
}
struct PermanentBorrowChainInventory {
    cache_view_cache: &'static SwiftFunctionCache,
    cache_view_pin: &'static SwiftFunctionPin,
    cache_view_control: &'static mut RuntimeControl,
    cache_view_wasi: Option<&'static AccountedWasi>,
    cache_release_cache: &'static mut SwiftFunctionCache,
    cache_release_control: &'static mut RuntimeControl,
    cache_release_wasi: Option<&'static AccountedWasi>,
    generic_view_pin: &'static SwiftFunctionPin,
    generic_view_meter: &'static mut CacheControl<'static>,
    generic_release_operation: &'static mut CacheControl<'static>,
    checked_record_pin: &'static SwiftFunctionPin,
    checked_record_meter: &'static mut CacheControl<'static>,
    control_check_header_receiver: &'static mut CacheControl<'static>,
    control_invalid_receiver: &'static mut CacheControl<'static>,
    control_error_receiver: &'static mut CacheControl<'static>,
    control_release_pin_receiver: &'static mut CacheControl<'static>,
    control_remove_live_receiver: &'static mut CacheControl<'static>,
    control_observation_receiver: &'static mut CacheControl<'static>,
    slot_entry_receiver: &'static SwiftSlot,
    slot_pins_receiver: &'static SwiftSlot,
    slot_set_pins_receiver: &'static mut SwiftSlot,
    usage_release_receiver: &'static mut SwiftCacheUsage,
    cleanup_owner: &'static mut Option<SwiftFunctionCache>,
    cleanup_control: &'static mut RuntimeControl,
    cleanup_wasi: Option<&'static AccountedWasi>,
    capture_failure: &'static mut Option<SwiftRunFailure>,
    tail_complete_outcome: &'static mut Option<SwiftRunFailure>,
}
struct ConstructionScalarInventory {
    previous_bound: usize,
    bound: usize,
    bound_add: usize,

    header: usize,
    entries: usize,
    slots_bytes: usize,
    pins_bytes: usize,
    patches_bytes: usize,
    fixed_reserved: usize,
    requested: usize,
    observed: usize,
    bytes: usize,
    owner: u64,
    owner_candidate: u64,
    work: u64,
    repeated: bool,
    slots_range: std::ops::Range<usize>,
    pins_range: std::ops::Range<usize>,
    patches_range: std::ops::Range<usize>,
    buffers_range: std::ops::Range<usize>,
    control: &'static mut RuntimeControl,
    wasi: Option<&'static AccountedWasi>,
    adopted: &'static AdoptedProof,
    partial: &'static mut Partial,
    wrapper: &'static mut CacheControl<'static>,
    slots: &'static mut Vec<SwiftSlot>,
    pins: &'static mut Vec<PinRecord>,
    patches: &'static mut Vec<decode::Patch>,
}
struct OperationScalarInventory {
    function: u32,
    checked_nonce: u64,
    pin_slot_search: Option<usize>,
    pin_slot: usize,
    hit: Option<usize>,
    index: usize,
    hits: u64,
    misses: u64,
    next_decodes: u64,
    bytes: usize,
    base: usize,
    capacity: usize,
    remaining: usize,
    empty: Option<usize>,
    oldest: Option<usize>,
    victim: usize,
    evictions: u64,
    victim_bytes: usize,
    publish_index: usize,
    requested: usize,
    observed: usize,
    depth: usize,
    parameters: usize,
    groups: usize,
    local_count: usize,
    local_type: crate::Type,
    offset: usize,
    opcode: u8,
    instruction_index: usize,
    ended: bool,
    block_result: Option<crate::Type>,
    block_kind: crate::experimental::cache::ControlKind,
    alternative: usize,
    branch_count: usize,
    first_target: usize,
    target: u32,
    indirect_type: u32,
    extended_opcode: u32,
    reader_take_bytes: &'static [u8],
    eviction_selected: &'static bool,
    take_count: usize,
    take_end: usize,
    byte: u8,
    uint_value: u32,
    uint_index: u32,
    signed_bits: u32,
    signed_maximum: u32,
    signed_value: u64,
    signed_index: u32,
    signed_byte: u8,
    signed_part: u8,
    signed_used: u32,
    signed_positive: u8,
    signed_negative: u8,
    signed_shift: u32,
    work: u64,
    attempted: u64,
    limit: u64,
    count_product: usize,
    code_product: usize,
    target_product: usize,
    checked_total: usize,
    pin_search: std::iter::Enumerate<std::slice::Iter<'static, PinRecord>>,
    hit_search: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    empty_search: std::slice::Iter<'static, SwiftSlot>,
    victim_search: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    eviction_count: std::slice::Iter<'static, bool>,
    eviction_apply: std::iter::Take<std::iter::Enumerate<std::slice::Iter<'static, bool>>>,
    patch_reset: std::slice::IterMut<'static, decode::Patch>,
    parameter_range: std::ops::Range<usize>,
    group_range: std::ops::Range<usize>,
    local_range: std::ops::Range<usize>,
    branch_range: std::ops::Range<usize>,
    uint_range: std::ops::Range<u32>,
    signed_range: std::ops::Range<u32>,
    snapshot: &'static ValidatedSwiftReactor,
    body: &'static [u8],
    policy: &'static SwiftPolicy<'static>,
    parts: &'static mut CacheFields<'static, SwiftMode>,
    meter: &'static mut SwiftMeter<'static, 'static>,
    operation: &'static mut CacheControl<'static>,
    scratch: &'static mut [decode::Patch],
    output: Option<&'static mut DecodedFunction>,
    locals: &'static mut Vec<crate::Type>,
    instructions: &'static mut Vec<crate::experimental::cache::DecodedInstruction>,
    targets: &'static mut Vec<u32>,
}
// Helper-specific fields distinguish every nested reborrow. This is the full
// nonrecursive union of the scan/build/reader/allocation/control wrapper chains;
// mutually exclusive scan/build and reader arms are deliberately both reserved.
struct OperationBorrowChainInventory {
    pin_operation: &'static mut CacheControl<'static>,
    pin_acquired_parts: &'static mut CacheFields<'static, SwiftMode>,
    pin_acquired_meter: &'static mut SwiftMeter<'static, 'static>,
    mode_meter_usage: &'static mut SwiftCacheUsage,
    mode_meter_operation: &'static mut CacheControl<'static>,
    mode_scan_snapshot: &'static ValidatedSwiftReactor,
    mode_scan_body: FunctionSpanView<'static>,
    mode_scan_scratch: &'static mut &'static mut [decode::Patch],
    mode_scan_meter: &'static mut SwiftMeter<'static, 'static>,
    mode_build_snapshot: &'static ValidatedSwiftReactor,
    mode_build_body: FunctionSpanView<'static>,
    mode_build_scratch: &'static mut &'static mut [decode::Patch],
    mode_build_meter: &'static mut SwiftMeter<'static, 'static>,
    build_payload_snapshot: &'static ValidatedSwiftReactor,
    build_payload_body: FunctionSpanView<'static>,
    build_payload_scratch: &'static mut &'static mut [decode::Patch],
    build_payload_meter: &'static mut SwiftMeter<'static, 'static>,
    decode_scan_body: &'static [u8],
    decode_scan_policy: &'static SwiftPolicy<'static>,
    decode_scan_meter: &'static mut SwiftMeter<'static, 'static>,
    decode_build_body: &'static [u8],
    decode_build_policy: &'static SwiftPolicy<'static>,
    decode_build_meter: &'static mut SwiftMeter<'static, 'static>,
    reader_take_filter_capture: &'static &'static mut decode::Reader<'static>,
    reader_take_filter_argument: &'static usize,
    locals_filter_policy_capture: &'static &'static SwiftPolicy<'static>,
    locals_filter_argument: &'static usize,
    locals_is_some_and_policy_capture: &'static &'static SwiftPolicy<'static>,
    locals_is_some_and_argument: usize,
    reader_byte_reader: &'static mut decode::Reader<'static>,
    reader_byte_meter: &'static mut SwiftMeter<'static, 'static>,
    reader_take_reader: &'static mut decode::Reader<'static>,
    reader_take_meter: &'static mut SwiftMeter<'static, 'static>,
    reader_uint_reader: &'static mut decode::Reader<'static>,
    reader_uint_meter: &'static mut SwiftMeter<'static, 'static>,
    reader_signed_reader: &'static mut decode::Reader<'static>,
    reader_signed_meter: &'static mut SwiftMeter<'static, 'static>,
    reader_type_reader: &'static mut decode::Reader<'static>,
    reader_type_meter: &'static mut SwiftMeter<'static, 'static>,
    reader_zero_reader: &'static mut decode::Reader<'static>,
    reader_zero_meter: &'static mut SwiftMeter<'static, 'static>,
    push_local_values: &'static mut Vec<crate::Type>,
    push_local_meter: &'static mut SwiftMeter<'static, 'static>,
    allocate_local_meter: &'static mut SwiftMeter<'static, 'static>,
    push_instruction_values: &'static mut Vec<crate::experimental::cache::DecodedInstruction>,
    push_instruction_meter: &'static mut SwiftMeter<'static, 'static>,
    allocate_instruction_meter: &'static mut SwiftMeter<'static, 'static>,
    push_target_values: &'static mut Vec<u32>,
    push_target_meter: &'static mut SwiftMeter<'static, 'static>,
    allocate_target_meter: &'static mut SwiftMeter<'static, 'static>,
    reset_patches: &'static mut [decode::Patch],
    reset_meter: &'static mut SwiftMeter<'static, 'static>,
    policy_snapshot: &'static ValidatedSwiftReactor,
    policy_body: FunctionSpanView<'static>,
    policy_meter: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_error_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_check_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_work_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_set_offset_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_exact_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_base_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_capacity_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_entry_capacity_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_construction_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_work_used_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_acquire_pin_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_abandon_pin_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_detailed_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_usage_receiver: &'static mut SwiftMeter<'static, 'static>,
    swift_meter_usage_mut_receiver: &'static mut SwiftMeter<'static, 'static>,
    control_error_receiver: &'static mut CacheControl<'static>,
    control_check_receiver: &'static mut CacheControl<'static>,
    control_work_receiver: &'static mut CacheControl<'static>,
    control_admit_receiver: &'static mut CacheControl<'static>,
    control_exact_receiver: &'static mut CacheControl<'static>,
    control_drop_reserved_receiver: &'static mut CacheControl<'static>,
    control_remove_live_receiver: &'static mut CacheControl<'static>,
    control_check_header_receiver: &'static mut CacheControl<'static>,
    snapshot_function_receiver: &'static ValidatedSwiftReactor,
    snapshot_signature_receiver: &'static ValidatedSwiftReactor,
    snapshot_source_receiver: &'static ValidatedSwiftReactor,
    snapshot_policy_receiver: &'static ValidatedSwiftReactor,
    policy_floats_receiver: &'static SwiftPolicy<'static>,
    policy_tables_receiver: &'static SwiftPolicy<'static>,
    policy_source_extent_receiver: &'static SwiftPolicy<'static>,
    policy_parameters_receiver: &'static SwiftPolicy<'static>,
    policy_parameters_limit_receiver: &'static SwiftPolicy<'static>,
    policy_local_groups_receiver: &'static SwiftPolicy<'static>,
    policy_total_locals_receiver: &'static SwiftPolicy<'static>,
    policy_instructions_receiver: &'static SwiftPolicy<'static>,
    policy_control_depth_receiver: &'static SwiftPolicy<'static>,
    policy_counts_parameters_receiver: &'static SwiftPolicy<'static>,
    statistics_decoded_receiver: &'static mut SwiftCacheUsage,
    statistics_pin_receiver: &'static mut SwiftCacheUsage,
    statistics_evicted_receiver: &'static mut SwiftCacheUsage,
    mode_build_counts: decode::Counts,
    build_payload_counts: decode::Counts,
    decode_build_counts: decode::Counts,
    counts_bytes_counts: decode::Counts,
}
struct PermanentScalarInventory {
    owner: &'static mut Option<SwiftFunctionCache>,
    control: &'static mut RuntimeControl,
    wasi: Option<&'static AccountedWasi>,
    cache: &'static SwiftFunctionCache,
    pin: &'static SwiftFunctionPin,
    record: PinRecord,
    slot: &'static mut SwiftSlot,
    pin_record: &'static mut PinRecord,
    pins_iter: std::slice::IterMut<'static, PinRecord>,
    slots_iter: std::slice::IterMut<'static, SwiftSlot>,
    buffers_range: std::ops::Range<usize>,
    buffer_index: usize,
    bytes: usize,
    last_pin: bool,
    control_wrapper: &'static mut CacheControl<'static>,
    outcome: &'static mut Option<SwiftRunFailure>,
    borrowed_parts: CleanupCompletionParts<'static>,
}
#[derive(Clone, Copy)]
struct PreparedBounds {
    previous: usize,
    enlarged: usize,
}
// Preflight return variants have identical measured layout. The two whole
// RuntimeControl transfer slots are assigned to these groups during prepare;
// the actual control owner is in slot1. No control/adopted move or final tail
// completion overlaps these helper frames. All root leaf-failure/usage slots
// remain available, and the helper ends before ordinary-phase enlargement.
struct PreflightSetupInventory {
    prepare_control: &'static mut RuntimeControl,
    prepare_wasi: Option<&'static AccountedWasi>,
    prepare_adopted: Option<&'static AdoptedProof>,
    prepare_cache: Option<&'static SwiftFunctionCache>,
    prepare_cursor: Cursor,
    helper_control: &'static mut RuntimeControl,
    helper_wasi: Option<&'static AccountedWasi>,
    helper_adopted: Option<&'static AdoptedProof>,
    helper_cache: Option<&'static SwiftFunctionCache>,
    helper_cursor: Cursor,
    pairing_control: &'static mut RuntimeControl,
    pairing_wasi: Option<&'static AccountedWasi>,
    pairing_cursor: Cursor,
    pairing_closure_control: &'static mut RuntimeControl,
    pairing_closure_wasi: &'static AccountedWasi,
    pairing_closure_cursor: &'static Cursor,
    header_borrow: Option<&'static ReservationTicket>,
    failure_closure_control: &'static mut RuntimeControl,
    failure_closure_observation: &'static Option<WasiUsage>,
    failure_closure_cursor: &'static Cursor,
    bound_closure_previous: &'static usize,
    bound_closure_argument: usize,
    layout_failure_control: &'static mut RuntimeControl,
    layout_failure_observation: Option<WasiUsage>,
    layout_failure_cursor: Cursor,
    checkpoint_control: &'static RuntimeControl,
    checkpoint_cursor: Cursor,
}
struct PreflightOwnerInventory {
    checked_usage_self: &'static AccountedWasi,
    checked_usage_control: &'static mut RuntimeControl,
    checked_usage_cursor: Cursor,
    checked_usage_header: &'static ReservationTicket,
    checked_usage_then_self: &'static AccountedWasi,
    wasi_usage_self: &'static AccountedWasi,
    context_usage_self: &'static crate::experimental_wasi::WasiContext,
    reservation_matches_self: &'static RuntimeControl,
    reservation_matches_ticket: &'static ReservationTicket,
    adopted_owner_self: &'static mut RuntimeControl,
    adopted_owner_adopted: &'static AdoptedProof,
    adopted_owner_cursor: Cursor,
    reservation_owner_self: &'static mut RuntimeControl,
    reservation_owner_ticket: &'static ReservationTicket,
    reservation_owner_cursor: Cursor,
    reservation_violation: Option<(SwiftCleanupInvariant, &'static str)>,
    reservation_match_option: Option<(SwiftCleanupInvariant, &'static str)>,
    reservation_match_tuple: (SwiftCleanupInvariant, &'static str),
    reservation_insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    reservation_insert_argument: SwiftCleanupInvariant,
    reservation_invariant: SwiftCleanupInvariant,
    reservation_code: &'static str,
    reservation_inserted: &'static mut SwiftCleanupInvariant,
    category_self: &'static SwiftReservations,
    category_argument: SwiftReservationCategory,
    category_result: &'static SwiftReservationUsage,
    header_option_receiver: &'static Option<ReservationTicket>,
    header_option_return: Option<&'static ReservationTicket>,
    reservation_matches_result: bool,
    then_receiver: bool,
    adopted_source_borrow: &'static ReservationTicket,
    adopted_metadata_borrow: &'static ReservationTicket,
}
struct PreflightPrimitiveInventory {
    fail_self: &'static mut RuntimeControl,
    fail_cursor: Cursor,
    fault_source: Fault,
    fault_transfer: Fault,
    fault_kind: SwiftRunFailureKind,
    fault_code: &'static str,
    usage_self: &'static RuntimeControl,
    usage_now: std::time::Instant,
    elapsed_receiver: &'static std::time::Instant,
    elapsed_earlier: std::time::Instant,
    elapsed_duration: std::time::Duration,
    overshoot_receiver: &'static std::time::Instant,
    overshoot_earlier: std::time::Instant,
    overshoot_duration: std::time::Duration,
    micros_duration: std::time::Duration,
    micros_u128: u128,
    micros_conversion: Result<u64, std::num::TryFromIntError>,
    elapsed_return: u64,
    overshoot_return: u64,
}
struct PreflightEnlargeInventory {
    enlarge_self: &'static mut RuntimeControl,
    enlarge_bytes: usize,
    enlarge_cursor: Cursor,
    old: usize,
    construction_option_receiver: &'static Option<ReservationTicket>,
    construction_option_return: Option<&'static ReservationTicket>,
    map_ticket: &'static ReservationTicket,
    map_bytes: usize,
    map_option: Option<usize>,
    old_option_receiver: Option<usize>,
    missing_closure_control: &'static mut &'static mut RuntimeControl,
    missing_closure_cursor: &'static Cursor,
    missing_closure_wasi: &'static Option<WasiUsage>,
    check_self: &'static mut RuntimeControl,
    check_cursor: Cursor,
    cancel_self: &'static crate::Cancellation,
    cancelled: bool,
    check_now: std::time::Instant,
    check_left: &'static std::time::Instant,
    check_right: &'static std::time::Instant,
    expired: bool,
    bytes_self: &'static mut RuntimeControl,
    bytes_category: SwiftReservationCategory,
    bytes_amount: usize,
    bytes_cursor: Cursor,
    category_next: Option<usize>,
    category_limit: usize,
    combined_next: Option<usize>,
    category_kind: SwiftRunFailureKind,
    limit_self: &'static RuntimeControl,
    limit_category: SwiftReservationCategory,
    limit_return: usize,
    category_self: &'static SwiftReservations,
    category_argument: SwiftReservationCategory,
    category_return: &'static SwiftReservationUsage,
    category_predicate_limit: &'static usize,
    category_predicate_n: usize,
    category_predicate_option: Option<usize>,
    combined_predicate_limit: &'static usize,
    combined_predicate_n: usize,
    combined_predicate_option: Option<usize>,
    map_or_default: u64,
    map_or_n: usize,
    map_or_return: u64,
    map_or_option: Option<usize>,
    limit_fault: Fault,
    limit_resource: SwiftRunResource,
    limit_attempted: u64,
    limit_ceiling: u64,
    next_category: usize,
    next_combined: usize,
    next_pair: (usize, usize),
    commit_self: &'static mut RuntimeControl,
    commit_category: SwiftReservationCategory,
    commit_category_next: usize,
    commit_combined_next: usize,
    category_mut_self: &'static mut SwiftReservations,
    category_mut_argument: SwiftReservationCategory,
    category_mut_return: &'static mut SwiftReservationUsage,
    construction_mut_option: Option<&'static mut ReservationTicket>,
    construction_mut_ticket: &'static mut ReservationTicket,
}
// Root leaf scalar/borrow phases are mutually exclusive API call chains.
// Failure/usage/ticket/optional-WASI values use their separate foundation classes.
struct RootAdmissionExtraInventory {
    admit_self: &'static mut RuntimeControl,
    admit_category: SwiftReservationCategory,
    admit_bytes: usize,
    admit_cursor: Cursor,
    entry_self: &'static mut RuntimeControl,
    entry_bytes: usize,
    entry_cursor: Cursor,
    ticket_count: usize,
    ticket_attempted: u64,
    entry_limit: usize,
}
struct RootAdmissionBoundaryInventory {
    bytes_and_check: PreflightEnlargeInventory,
    primitive: PreflightPrimitiveInventory,
    entry_and_ticket: RootAdmissionExtraInventory,
}
struct RootOwnerBoundaryInventory {
    owner: PreflightOwnerInventory,
    primitive: PreflightPrimitiveInventory,
}
struct RootWorkLiveInventory {
    work_self: &'static mut RuntimeControl,
    component: Work,
    credits: u64,
    work_cursor: Cursor,
    used: u64,
    work_limit: u64,
    work_resource: SwiftRunResource,
    work_tuple: (u64, u64, SwiftRunResource),
    work_next: Option<u64>,
    work_filter_input: Option<u64>,
    work_filter_output: Option<u64>,
    work_pattern: u64,
    work_filter_limit: &'static u64,
    work_filter_value: &'static u64,
    add_self: &'static mut RuntimeControl,
    add_resource: Live,
    add_amount: usize,
    add_cursor: Cursor,
    live_parts_self: &'static RuntimeControl,
    live_parts_resource: Live,
    live_tuple: (
        SwiftReservationUsage,
        usize,
        SwiftRunResource,
        SwiftRunFailureKind,
    ),
    live_usage: SwiftReservationUsage,
    live_limit: usize,
    live_diagnostic: SwiftRunResource,
    live_kind: SwiftRunFailureKind,
    live_next: Option<usize>,
    live_filter_input: Option<usize>,
    live_filter_output: Option<usize>,
    live_pattern: usize,
    live_filter_limit: &'static usize,
    live_filter_value: &'static usize,
    live_map_or_input: Option<usize>,
    live_map_or_value: usize,
    live_map_or_return: u64,
    live_mut_self: &'static mut RuntimeControl,
    live_mut_resource: Live,
    live_mut_return: &'static mut SwiftReservationUsage,
    live_usage_borrow: &'static mut SwiftReservationUsage,
    remove_self: &'static mut RuntimeControl,
    remove_resource: Live,
    remove_amount: usize,
    remove_tuple: (
        SwiftReservationUsage,
        usize,
        SwiftRunResource,
        SwiftRunFailureKind,
    ),
    remove_usage: SwiftReservationUsage,
    remove_next: Option<usize>,
    remove_pattern: usize,
    exact_self: &'static mut RuntimeControl,
    requested: usize,
    observed: usize,
    exact_cursor: Cursor,
    exact_fault: Fault,
    observed_option: Option<usize>,
}
struct RootWorkLiveBoundaryInventory {
    work_live_exact: RootWorkLiveInventory,
    check: PreflightEnlargeInventory,
    primitive: PreflightPrimitiveInventory,
}
// remove_live does not call check/preflight_bytes. Its underflow branch keeps
// the remove caller live while cleanup_fault inserts the invariant and fails.
// This is a separate complete union member, never a switch to refund's member.
struct RootRemoveLiveInventory {
    remove_self: &'static mut RuntimeControl,
    remove_resource: Live,
    remove_amount: usize,
    live_parts_self: &'static RuntimeControl,
    live_parts_resource: Live,
    live_tuple: (
        SwiftReservationUsage,
        usize,
        SwiftRunResource,
        SwiftRunFailureKind,
    ),
    usage: SwiftReservationUsage,
    next: Option<usize>,
    next_pattern: usize,
    live_mut_self: &'static mut RuntimeControl,
    live_mut_resource: Live,
    live_mut_return: &'static mut SwiftReservationUsage,
    cleanup_fault_self: &'static mut RuntimeControl,
    cleanup_invariant: SwiftCleanupInvariant,
    cleanup_code: &'static str,
    cleanup_cursor: Cursor,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    inserted: &'static mut SwiftCleanupInvariant,
}
struct RootRemoveLiveBoundaryInventory {
    remove_and_cleanup_fault: RootRemoveLiveInventory,
    primitive: PreflightPrimitiveInventory,
}
struct RootRefundInventory {
    drop_self: &'static mut RuntimeControl,
    refund_self: &'static mut RuntimeControl,
    category: Option<usize>,
    combined: Option<usize>,
    count: Option<usize>,
    option_match: (Option<usize>, Option<usize>, Option<usize>),
    category_pattern: usize,
    combined_pattern: usize,
    count_pattern: usize,
    category_self: &'static SwiftReservations,
    category_argument: SwiftReservationCategory,
    category_return: &'static SwiftReservationUsage,
    category_mut_self: &'static mut SwiftReservations,
    category_mut_argument: SwiftReservationCategory,
    category_mut_return: &'static mut SwiftReservationUsage,
    cleanup_fault_self: &'static mut RuntimeControl,
    cleanup_invariant: SwiftCleanupInvariant,
    cleanup_code: &'static str,
    cleanup_cursor: Cursor,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    inserted: &'static mut SwiftCleanupInvariant,
    record_self: &'static mut RuntimeControl,
    record_failure: &'static mut SwiftRunFailure,
    record_failure_option: Option<&'static mut SwiftRunFailure>,
    complete_outcome: &'static mut Option<SwiftRunFailure>,
}
struct RootPhaseEndInventory {
    end_self: &'static mut RuntimeControl,
    end_bytes: usize,
    construction_receiver: &'static Option<ReservationTicket>,
    construction_return: Option<&'static ReservationTicket>,
    construction_ticket: &'static ReservationTicket,
    floor: usize,
    difference: usize,
    category: Option<usize>,
    combined: Option<usize>,
    option_match: (Option<usize>, Option<usize>),
    category_pattern: usize,
    combined_pattern: usize,
    construction_mut_option: Option<&'static mut ReservationTicket>,
    construction_mut_ticket: &'static mut ReservationTicket,
    foundation_items: [(usize, usize); 7],
    foundation_iterator: std::array::IntoIter<(usize, usize), 7>,
    foundation_sum: usize,
    foundation_count: usize,
    foundation_bytes: usize,
    foundation_product: Option<usize>,
    foundation_next: Option<usize>,
}
struct RootRefundBoundaryInventory {
    refund: RootRefundInventory,
    phase_end: RootPhaseEndInventory,
    primitive: PreflightPrimitiveInventory,
}
union RootLeafInventory {
    admission: std::mem::ManuallyDrop<RootAdmissionBoundaryInventory>,
    owner: std::mem::ManuallyDrop<RootOwnerBoundaryInventory>,
    work_live: std::mem::ManuallyDrop<RootWorkLiveBoundaryInventory>,
    remove_live: std::mem::ManuallyDrop<RootRemoveLiveBoundaryInventory>,
    refund: std::mem::ManuallyDrop<RootRefundBoundaryInventory>,
}
struct CompletionBorrowInventory {
    returned_parts: CleanupCompletionParts<'static>,
    outcome: &'static mut Option<SwiftRunFailure>,
    phase_control: &'static mut RuntimeControl,
    phase_wasi: Option<&'static AccountedWasi>,
    phase_previous: usize,
    construction_phase: CacheConstructionPhase<'static>,
    operation_phase: CacheOperationPhase<'static>,
}
struct PreflightGroupA {
    layout_fault: Fault,
    result: Result<PreparedBounds, SwiftRunFailure>,
    observation: Option<WasiUsage>,
    cursor: Cursor,
    control: &'static mut RuntimeControl,
    wasi: Option<&'static AccountedWasi>,
    adopted: Option<&'static AdoptedProof>,
    cache: Option<&'static SwiftFunctionCache>,
    previous: usize,
    enlarged: usize,
}
struct PreflightGroupB {
    function_return_option: Option<usize>,
    and_then_receiver: Option<usize>,
    and_then_return: Option<usize>,
    ok_or_receiver: Option<usize>,
    return_transfer: Result<PreparedBounds, SwiftRunFailure>,
    usage_return: SwiftRunUsage,
}
macro_rules! sum_named {
    (&[$(($count:expr, $size:expr $(,)?)),* $(,)?]) => {{
        let mut sum = 0usize;
        $(
            let Some(product) = ($count as usize).checked_mul($size) else { return None; };
            let Some(next) = sum.checked_add(product) else { return None; };
            sum = next;
        )*
        Some(sum)
    }};
}
/// Permanent envelope: simultaneous *named Rust objects*, not stack/RSS claims.
/// Cache/header owner storage and every return/drop transfer remain covered until
/// CacheCleanupTail::complete has consumed the caller's empty owner/Result slots.
const fn compute_cache_cleanup_temporary_bytes() -> Option<usize> {
    sum_named!(&[
        (3, size_of::<Result<Option<WasiUsage>, SwiftRunFailure>>()),
        (3, size_of::<Option<Result<WasiUsage, SwiftRunFailure>>>()),
        (3, size_of::<Result<WasiUsage, SwiftRunFailure>>()),
        (3, size_of::<PermanentScalarInventory>()),
        (3, size_of::<PermanentBorrowChainInventory>()),
        (3, size_of::<Option<PinRecord>>()),
        (3, size_of::<Option<&'static PinRecord>>()),
        (3, size_of::<Option<&'static SwiftSlot>>()),
        (3, size_of::<Option<&'static DecodedFunction>>()),
        (
            3,
            size_of::<(&'static SwiftFunctionPin, &'static PinRecord)>()
        ),
        (3, size_of::<CacheParts<'static, SwiftMode>>()),
        (1, size_of::<CacheViewParts<'static, SwiftMode>>()),
        (3, size_of::<PinRecord>()),
        (3, size_of::<Result<PinRecord, SwiftRunFailure>>()),
        (3, size_of::<FunctionView<'static>>()),
        (
            3,
            size_of::<Result<FunctionView<'static>, SwiftRunFailure>>()
        ),
        (3, size_of::<(SwiftRunFailure, SwiftFunctionPin)>()),
        (
            3,
            size_of::<Result<(), (SwiftRunFailure, SwiftFunctionPin)>>()
        ),
        (1, size_of::<SwiftFunctionPin>()),
        (1, size_of::<SwiftCacheUsage>()),
        (3, size_of::<SwiftCacheIdentity>()),
        (3, size_of::<Option<SwiftFunctionCache>>()), // caller slot, take return, active owner move
        (2, size_of::<SwiftFunctionCache>()), // taken binding and field-destructure transfer
        (
            3,
            size_of::<Result<CacheCleanupTail<'static>, SwiftRunFailure>>(),
        ), // callee return, branch, caller result
        (3, size_of::<CacheCleanupTail<'static>>()), // created, return, caller tail
        (2, size_of::<Option<CacheCleanupTail<'static>>>()),
        (3, size_of::<CleanupCompletionParts<'static>>()),
        (3, size_of::<Option<SwiftResident>>()), // slot take and drop transfer
        (3, size_of::<SwiftResident>()),
        (3, size_of::<DecodedFunction>()),
        (4, size_of::<Vec<SwiftSlot>>()),
        (4, size_of::<Vec<PinRecord>>()),
        (4, size_of::<Vec<decode::Patch>>()),
        (6, size_of::<Option<ReservationTicket>>()),
        (6, size_of::<ReservationTicket>()),
        (3, size_of::<CacheControl<'static>>()),
        (2, size_of::<CacheViewParts<'static, SwiftMode>>()),
        (4, size_of::<SwiftRunFailure>()),
        (4, size_of::<Option<SwiftRunFailure>>()),
        (4, size_of::<Result<(), SwiftRunFailure>>()),
        (4, size_of::<SwiftRunUsage>()),
        (6, size_of::<Option<WasiUsage>>()),
        (2, size_of::<Fault>()),
        (3, size_of::<Cursor>()),
        (2, size_of::<SwiftReleaseFailure>()),
        (2, size_of::<Result<(), SwiftReleaseFailure>>()),
        (2, size_of::<SwiftFunctionPin>()),
        (2, size_of::<SwiftCacheUsage>()),
    ])
}
const fn compute_cache_header_bytes() -> Option<usize> {
    let Some(exclusive) =
        size_of::<SwiftFunctionCache>().checked_sub(size_of::<ValidatedSwiftReactor>())
    else {
        return None;
    };
    let Some(cleanup) = compute_cache_cleanup_temporary_bytes() else {
        return None;
    };
    exclusive.checked_add(cleanup)
}
const fn compute_cache_construction_bytes() -> Option<usize> {
    sum_named!(&[
        (3, size_of::<Result<Option<WasiUsage>, SwiftRunFailure>>()),
        (3, size_of::<Option<Result<WasiUsage, SwiftRunFailure>>>()),
        (3, size_of::<Result<WasiUsage, SwiftRunFailure>>()),
        (
            3,
            size_of::<Result<CacheConstructionPhase<'static>, SwiftRunFailure>>()
        ),
        (3, size_of::<Result<ReservationTicket, SwiftRunFailure>>()),
        (3, size_of::<std::collections::TryReserveError>()),
        (
            3,
            size_of::<Result<(), std::collections::TryReserveError>>()
        ),
        // Atomic-call result, allocator return, selector expression/return,
        // constructor adapter receiver and outward result transfer.
        (6, size_of::<Result<u64, u64>>()),
        (3, size_of::<Option<u64>>()),
        (3, size_of::<Result<u64, SwiftRunFailure>>()),
        (3, size_of::<ConstructionScalarInventory>()),
        (3, size_of::<ConstructionBorrowChainInventory>()),
        (3, size_of::<SwiftRunBudget>()),
        (3, size_of::<(u64, SwiftCacheUsage)>()),
        (
            3,
            size_of::<Result<(u64, SwiftCacheUsage), SwiftRunFailure>>()
        ),
        (3, size_of::<PreparedBounds>()),
        (3, size_of::<CacheConstructionPhase<'static>>()),
        (3, size_of::<Partial>()),
        (3, size_of::<SwiftFunctionCache>()),
        (
            3,
            size_of::<Result<SwiftFunctionCache, CacheConstructionFailure>>(),
        ),
        (3, size_of::<CacheConstructionFailure>()),
        (2, size_of::<ConstructionReturnSlot>()),
        (2, size_of::<Option<AdoptedProof>>()),
        (4, size_of::<Option<ReservationTicket>>()),
        (4, size_of::<ReservationTicket>()),
        (2, size_of::<SwiftCacheUsage>()),
        (3, size_of::<CacheControl<'static>>()),
        (3, size_of::<Cursor>()),
        (2, size_of::<Fault>()),
        (4, size_of::<SwiftRunFailure>()),
        (4, size_of::<Result<(), SwiftRunFailure>>()),
        (4, size_of::<Option<WasiUsage>>()),
        (3, size_of::<Vec<SwiftSlot>>()),
        (3, size_of::<Vec<PinRecord>>()),
        (3, size_of::<Vec<decode::Patch>>()),
    ])
}
const fn compute_cache_operation_bytes() -> Option<usize> {
    sum_named!(&[
        (3, size_of::<Result<Option<WasiUsage>, SwiftRunFailure>>()),
        (3, size_of::<Option<Result<WasiUsage, SwiftRunFailure>>>()),
        (3, size_of::<Result<WasiUsage, SwiftRunFailure>>()),
        (
            3,
            size_of::<Result<CacheOperationPhase<'static>, SwiftRunFailure>>()
        ),
        (3, size_of::<Result<ReservationTicket, SwiftRunFailure>>()),
        (3, size_of::<std::collections::TryReserveError>()),
        (
            3,
            size_of::<Result<(), std::collections::TryReserveError>>()
        ),
        (3, size_of::<OperationScalarInventory>()),
        (3, size_of::<OperationBorrowChainInventory>()),
        (3, size_of::<(&'static SwiftPolicy<'static>,)>()),
        (3, size_of::<Option<FunctionSpanView<'static>>>()),
        (
            3,
            size_of::<Option<crate::experimental::descriptors::SignatureView<'static>>>()
        ),
        (3, size_of::<Option<&'static SwiftSlot>>()),
        (3, size_of::<Option<&'static DecodedFunction>>()),
        (3, size_of::<Option<&'static mut DecodedFunction>>()),
        (
            3,
            size_of::<Option<&'static mut crate::experimental::cache::DecodedInstruction>>()
        ),
        (3, size_of::<[u8; 4]>()),
        (3, size_of::<[u8; 8]>()),
        (
            3,
            size_of::<Result<[u8; 4], std::array::TryFromSliceError>>()
        ),
        (
            3,
            size_of::<Result<[u8; 8], std::array::TryFromSliceError>>()
        ),
        (3, size_of::<(&'static mut SwiftMeter<'static, 'static>,)>()),
        (3, size_of::<(&'static u32,)>()),
        (
            3,
            size_of::<(&'static SwiftSlot, &'static CacheFields<'static, SwiftMode>)>()
        ),
        (3, size_of::<SwiftRunBudget>()),
        (3, size_of::<PreparedBounds>()),
        (
            3,
            size_of::<crate::experimental::descriptors::SignatureView<'static>>()
        ),
        (
            3,
            size_of::<Result<SwiftPolicy<'static>, SwiftRunFailure>>()
        ),
        (3, size_of::<Result<decode::Counts, SwiftRunFailure>>()),
        (3, size_of::<Result<usize, SwiftRunFailure>>()),
        (3, size_of::<Result<u8, SwiftRunFailure>>()),
        (3, size_of::<Result<u32, SwiftRunFailure>>()),
        (3, size_of::<Result<i64, SwiftRunFailure>>()),
        (3, size_of::<Result<crate::Type, SwiftRunFailure>>()),
        (3, size_of::<Result<&'static [u8], SwiftRunFailure>>()),
        (3, size_of::<crate::Value>()),
        (3, size_of::<crate::experimental::cache::Operation>()),
        (
            3,
            size_of::<crate::experimental::cache::DecodedInstruction>()
        ),
        (2, size_of::<decode::Patch>()),
        (3, size_of::<Vec<crate::Type>>()),
        (
            3,
            size_of::<Vec<crate::experimental::cache::DecodedInstruction>>()
        ),
        (3, size_of::<Vec<u32>>()),
        (3, size_of::<Result<Vec<crate::Type>, SwiftRunFailure>>()),
        (
            3,
            size_of::<Result<Vec<crate::experimental::cache::DecodedInstruction>, SwiftRunFailure>>(
            )
        ),
        (3, size_of::<Result<Vec<u32>, SwiftRunFailure>>()),
        (3, size_of::<CacheOperationPhase<'static>>()),
        (3, size_of::<CacheControl<'static>>()),
        (3, size_of::<CacheParts<'static, SwiftMode>>()),
        (3, size_of::<CacheFields<'static, SwiftMode>>()),
        (3, size_of::<SwiftMeter<'static, 'static>>()),
        (2, size_of::<decode::Reader<'static>>()),
        (2, size_of::<decode::PassParts<'static>>()),
        (4, size_of::<decode::Counts>()),
        (2, size_of::<SwiftPolicy<'static>>()),
        (1, size_of::<[bool; 64]>()),
        (3, size_of::<DecodedFunction>()),
        (3, size_of::<SwiftResident>()),
        (3, size_of::<Result<SwiftResident, SwiftRunFailure>>()),
        (3, size_of::<Result<DecodedFunction, SwiftRunFailure>>()),
        (3, size_of::<Result<SwiftFunctionPin, SwiftRunFailure>>()),
        (2, size_of::<OperationReturnSlot>()),
        (4, size_of::<ReservationTicket>()),
        (4, size_of::<Option<WasiUsage>>()),
        (4, size_of::<SwiftRunFailure>()),
        (4, size_of::<SwiftRunUsage>()),
        (3, size_of::<Cursor>()),
        (2, size_of::<Fault>()),
        (3, size_of::<FunctionSpanView<'static>>()),
    ])
}
// Whole existing foundation slots, used only while prepare borrows intact
// owners. Each group owns a complete slot; no unused bytes inside another
// group/owner are counted. These roles end before construct or final cleanup.
const _: () = {
    assert!(size_of::<RootLeafInventory>() <= size_of::<RuntimeControl>());
    assert!(size_of::<CompletionBorrowInventory>() <= size_of::<RuntimeControl>());
    assert!(size_of::<PreflightGroupA>() <= size_of::<RuntimeControl>());
    assert!(size_of::<PreflightGroupB>() <= size_of::<RuntimeControl>());
    assert!(size_of::<PreflightSetupInventory>() <= size_of::<ValidatedSwiftReactor>());
    assert!(size_of::<PreflightOwnerInventory>() <= size_of::<ValidatedSwiftReactor>());
    assert!(size_of::<PreflightPrimitiveInventory>() <= size_of::<AdoptedProof>());
    assert!(size_of::<PreflightEnlargeInventory>() <= size_of::<AdoptedProof>());
};
// Explicit const evaluation: these size calculations never create runtime tables or fold frames.
const CACHE_CLEANUP_TEMPORARY_BYTES: Option<usize> = compute_cache_cleanup_temporary_bytes();
pub(crate) fn cache_cleanup_temporary_bytes() -> Option<usize> {
    CACHE_CLEANUP_TEMPORARY_BYTES
}
const CACHE_HEADER_BYTES: Option<usize> = compute_cache_header_bytes();
pub(crate) fn cache_header_bytes() -> Option<usize> {
    CACHE_HEADER_BYTES
}
const CACHE_CONSTRUCTION_BYTES: Option<usize> = compute_cache_construction_bytes();
pub(crate) fn cache_construction_bytes() -> Option<usize> {
    CACHE_CONSTRUCTION_BYTES
}
const CACHE_OPERATION_BYTES: Option<usize> = compute_cache_operation_bytes();
pub(crate) fn cache_operation_bytes() -> Option<usize> {
    CACHE_OPERATION_BYTES
}
fn pairing(
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
    cursor: Cursor,
) -> Result<Option<WasiUsage>, SwiftRunFailure> {
    wasi.map(|w| w.checked_usage(control, cursor)).transpose()
}
fn layout_failure(
    control: &mut RuntimeControl,
    wasi: Option<WasiUsage>,
    cursor: Cursor,
) -> SwiftRunFailure {
    control.fail(
        cursor,
        Fault::new(
            SwiftRunFailureKind::Invariant,
            "swift_cache_layout_overflow",
        ),
        wasi,
    )
}
impl CacheControl<'_> {
    fn observation(&self) -> Option<WasiUsage> {
        self.wasi.map(AccountedWasi::usage)
    }
    fn error(&mut self, kind: CacheFailureKind, code: &'static str) -> SwiftRunFailure {
        let kind = match kind {
            CacheFailureKind::AllocationFailure => SwiftRunFailureKind::Allocation,
            CacheFailureKind::DecoderMismatch => SwiftRunFailureKind::DecoderMismatch,
            CacheFailureKind::WorkExhausted => SwiftRunFailureKind::WorkExhausted,
            CacheFailureKind::InvalidFunction
            | CacheFailureKind::InvalidPin
            | CacheFailureKind::NonceExhausted
            | CacheFailureKind::IdentityExhausted => SwiftRunFailureKind::Invariant,
            CacheFailureKind::PinExhausted => SwiftRunFailureKind::PinLimit,
            _ => SwiftRunFailureKind::ResourceExhausted,
        };
        self.control
            .fail(self.cursor, Fault::new(kind, code), self.observation())
    }
    fn check(&mut self) -> Result<(), SwiftRunFailure> {
        checkpoint(self.control, self.cursor);
        self.control
            .check_with_wasi(self.cursor, self.observation())
    }
    fn work(&mut self, n: u64) -> Result<(), SwiftRunFailure> {
        checkpoint(self.control, self.cursor);
        let result = self.control
            .work_with_wasi(Work::Cache, n, self.cursor, self.observation());
        #[cfg(test)]
        super::cache_tests::attribution_work(n, self.cursor, &result);
        result
    }
    fn admit(&mut self, bytes: usize) -> Result<ReservationTicket, SwiftRunFailure> {
        checkpoint(self.control, self.cursor);
        self.control.admit_with_wasi(
            SwiftReservationCategory::Cache,
            bytes,
            self.cursor,
            self.observation(),
        )
    }
    fn exact(&mut self, requested: usize, observed: usize) -> Result<(), SwiftRunFailure> {
        checkpoint(self.control, self.cursor);
        self.control.exact_capacity_with_wasi(
            requested,
            capacity_observation(observed),
            self.cursor,
            self.observation(),
        )
    }
    fn drop_reserved<T>(
        &mut self,
        storage: T,
        ticket: ReservationTicket,
    ) -> Result<(), SwiftRunFailure> {
        self.control
            .drop_reserved_with_wasi(storage, ticket, self.observation())
    }
    fn remove_live(&mut self, kind: Live) -> Result<(), SwiftRunFailure> {
        self.control
            .remove_live_with_wasi(kind, 1, self.observation())
    }
    fn check_header(&mut self, cache: &SwiftFunctionCache) -> Result<(), SwiftRunFailure> {
        pairing(self.control, self.wasi, self.cursor)?;
        let Some(header) = cache.header.as_ref() else {
            return Err(self.error(CacheFailureKind::InvalidPin, "swift_cache_missing_header"));
        };
        self.control
            .check_reservation_owner(header, self.cursor, self.observation())
    }
}
impl PinDiagnostic<SwiftRunFailure> for CacheControl<'_> {
    fn invalid(&mut self, code: &'static str) -> SwiftRunFailure {
        self.error(CacheFailureKind::InvalidPin, code)
    }
}
impl ReleaseControl<SwiftRunFailure> for CacheControl<'_> {
    fn release_pin(&mut self) -> Result<(), SwiftRunFailure> {
        self.remove_live(Live::ActivePins)
    }
}
fn construction_preflight(
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
    adopted: &AdoptedProof,
    cursor: Cursor,
) -> Result<PreparedBounds, SwiftRunFailure> {
    let observation = pairing(control, wasi, cursor)?;
    control.check_adopted_owner(adopted, cursor, observation)?;
    let previous_bound = control.usage(observation).reservations.construction.current;
    let enlarged = cache_construction_bytes()
        .and_then(|n| previous_bound.checked_add(n))
        .ok_or_else(|| layout_failure(control, observation, cursor))?;
    Ok(PreparedBounds {
        previous: previous_bound,
        enlarged,
    })
}
fn operation_preflight(
    cache: &SwiftFunctionCache,
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
    cursor: Cursor,
) -> Result<PreparedBounds, SwiftRunFailure> {
    let observation = pairing(control, wasi, cursor)?;
    let header = cache
        .header
        .as_ref()
        .ok_or_else(|| layout_failure(control, observation, cursor))?;
    control.check_reservation_owner(header, cursor, observation)?;
    let previous = control.usage(observation).reservations.construction.current;
    let enlarged = cache_operation_bytes()
        .and_then(|n| previous.checked_add(n))
        .ok_or_else(|| layout_failure(control, observation, cursor))?;
    Ok(PreparedBounds { previous, enlarged })
}
impl SwiftFunctionCache {
    pub(crate) const DECODER_REVISION: u32 = 1;
    pub(crate) fn prepare<'a>(
        control: &'a mut RuntimeControl,
        wasi: Option<&'a AccountedWasi>,
        adopted: &AdoptedProof,
        cursor: Cursor,
    ) -> Result<CacheConstructionPhase<'a>, SwiftRunFailure> {
        #[cfg(test)]
        super::cache_tests::attribution_site(0);
        test_step(CacheStep::Constructor);
        let PreparedBounds {
            previous: previous_bound,
            enlarged: bound,
        } = construction_preflight(control, wasi, adopted, cursor)?;
        let observation = wasi.map(AccountedWasi::usage);
        checkpoint(control, cursor);
        control.enlarge_construction_with_wasi(bound, cursor, observation)?;
        Ok(CacheConstructionPhase {
            control: CacheControl {
                control,
                wasi,
                cursor,
            },
            previous_bound,
            constructed: false,
        })
    }
    pub(crate) fn proof(&self) -> &ValidatedSwiftReactor {
        self.adopted.proof()
    }
    /// Borrow-only provenance preflight for composed construction and cleanup.
    /// Deliberately performs no ordinary checkpoint, admission, or work debit.
    /// The caller accounts for these temporary borrows before invoking it.
    #[allow(dead_code)] // Consumed by the separately qualified private executor.
    pub(crate) fn check_owner(
        &self,
        control: &mut RuntimeControl,
        wasi: Option<&AccountedWasi>,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        CacheControl {
            control,
            wasi,
            cursor,
        }
        .check_header(self)
    }
    pub(crate) fn usage(&self) -> SwiftCacheUsage {
        self.usage
    }
    pub(crate) fn identity(&self) -> SwiftCacheIdentity {
        SwiftCacheIdentity {
            owner: self.owner,
            validator_revision: ValidatedSwiftReactor::VALIDATOR_REVISION,
            decoder_revision: Self::DECODER_REVISION,
            policy: self.proof().policy_identity(),
        }
    }
    pub(crate) fn prepare_operation<'a>(
        &self,
        control: &'a mut RuntimeControl,
        wasi: Option<&'a AccountedWasi>,
        cursor: Cursor,
    ) -> Result<CacheOperationPhase<'a>, SwiftRunFailure> {
        test_step(CacheStep::Lookup);
        let PreparedBounds {
            previous: previous_bound,
            enlarged: bound,
        } = operation_preflight(self, control, wasi, cursor)?;
        let observation = wasi.map(AccountedWasi::usage);
        checkpoint(control, cursor);
        control.enlarge_construction_with_wasi(bound, cursor, observation)?;
        Ok(CacheOperationPhase {
            control: CacheControl {
                control,
                wasi,
                cursor,
            },
            previous_bound,
        })
    }
    pub(crate) fn view<'a>(
        &'a self,
        pin: &SwiftFunctionPin,
        control: &mut RuntimeControl,
        wasi: Option<&AccountedWasi>,
    ) -> Result<FunctionView<'a>, SwiftRunFailure> {
        let mut operation = CacheControl {
            control,
            wasi,
            cursor: cache_cursor(),
        };
        operation.check_header(self)?;
        view::<SwiftMode>(
            CacheViewParts {
                slots: &self.slots,
                pins: &self.pins,
                owner: self.owner,
            },
            pin,
            &mut operation,
        )
    }
    pub(crate) fn release(
        &mut self,
        pin: SwiftFunctionPin,
        control: &mut RuntimeControl,
        wasi: Option<&AccountedWasi>,
    ) -> Result<(), SwiftReleaseFailure> {
        let mut operation = CacheControl {
            control,
            wasi,
            cursor: cache_cursor(),
        };
        if let Err(failure) = operation.check_header(self) {
            return Err(SwiftReleaseFailure { failure, pin });
        }
        release::<SwiftMode>(
            CacheParts {
                snapshot: self.adopted.proof(),
                slots: &mut self.slots,
                pins: &mut self.pins,
                owner: self.owner,
                next_nonce: &mut self.next_nonce,
                usage: &mut self.usage,
                scratch: &mut self.patches,
            },
            pin,
            &mut operation,
        )
        .map_err(|(failure, pin)| SwiftReleaseFailure { failure, pin })
    }
    pub(crate) fn cleanup<'a>(
        owned: &mut Option<Self>,
        control: &'a mut RuntimeControl,
        wasi: Option<&'a AccountedWasi>,
    ) -> Result<CacheCleanupTail<'a>, SwiftRunFailure> {
        let cursor = Cursor {
            stage: SwiftRunStage::Cleanup,
            function: None,
            offset: None,
        };
        let observation = pairing(control, wasi, cursor)?;
        let cache = owned
            .as_ref()
            .ok_or_else(|| layout_failure(control, observation, cursor))?;
        let header = cache
            .header
            .as_ref()
            .ok_or_else(|| layout_failure(control, observation, cursor))?;
        control.check_reservation_owner(header, cursor, observation)?;
        // No owner has moved until every provenance check above succeeded.
        let mut cache = owned.take().expect("preflight retained owner");
        let mut failure = None;
        for record in &mut cache.pins {
            if record.nonce != 0 {
                *record = PinRecord::default();
                capture(
                    &mut failure,
                    control.remove_live_with_wasi(
                        Live::ActivePins,
                        1,
                        wasi.map(AccountedWasi::usage),
                    ),
                );
            }
        }
        for slot in &mut cache.slots {
            slot.pins = 0;
            if let Some(resident) = slot.resident.take() {
                capture(
                    &mut failure,
                    control.drop_reserved_with_wasi(
                        resident.decoded,
                        resident.ticket,
                        wasi.map(AccountedWasi::usage),
                    ),
                );
                capture(
                    &mut failure,
                    control.remove_live_with_wasi(
                        Live::CacheEntries,
                        1,
                        wasi.map(AccountedWasi::usage),
                    ),
                );
            }
        }
        if let Some(ticket) = cache.buffers[0].take() {
            capture(
                &mut failure,
                control.drop_reserved_with_wasi(
                    take(&mut cache.slots),
                    ticket,
                    wasi.map(AccountedWasi::usage),
                ),
            );
        }
        if let Some(ticket) = cache.buffers[1].take() {
            capture(
                &mut failure,
                control.drop_reserved_with_wasi(
                    take(&mut cache.pins),
                    ticket,
                    wasi.map(AccountedWasi::usage),
                ),
            );
        }
        if let Some(ticket) = cache.buffers[2].take() {
            capture(
                &mut failure,
                control.drop_reserved_with_wasi(
                    take(&mut cache.patches),
                    ticket,
                    wasi.map(AccountedWasi::usage),
                ),
            );
        }
        let SwiftFunctionCache {
            adopted, header, ..
        } = cache;
        capture(
            &mut failure,
            control.drop_proof_with_wasi(adopted, wasi.map(AccountedWasi::usage)),
        );
        if failure.is_none() {
            failure = control.record_cleanup(wasi.map(AccountedWasi::usage));
        }
        Ok(CacheCleanupTail {
            control,
            wasi,
            header,
            failure,
        })
    }
}
fn capture(first: &mut Option<SwiftRunFailure>, result: Result<(), SwiftRunFailure>) {
    if let Err(failure) = result {
        if first.is_none() {
            *first = Some(failure);
        }
    }
}
type CleanupCompletionParts<'a> = (
    &'a mut RuntimeControl,
    Option<&'a AccountedWasi>,
    Option<ReservationTicket>,
);
/// This helper frame (including the original tail and its failure) has ended
/// before complete begins the observed refund. It returns only small borrows
/// and the same ticket; no possible-cache owner or failure wrapper survives.
fn drop_cleanup_return_storage<'a, T>(
    tail: CacheCleanupTail<'a>,
    storage: T,
) -> CleanupCompletionParts<'a> {
    let CacheCleanupTail {
        control,
        wasi,
        header,
        failure,
    } = tail;
    drop((storage, failure));
    (control, wasi, header)
}
impl CacheCleanupTail<'_> {
    pub(crate) fn complete<T>(
        self,
        returned_phase_storage: T,
        outcome: &mut Option<SwiftRunFailure>,
    ) {
        let (control, wasi, header) = drop_cleanup_return_storage(self, returned_phase_storage);
        if let Some(ticket) = header {
            let _ = control.drop_reserved_with_wasi((), ticket, wasi.map(AccountedWasi::usage));
        }
        *outcome = control.record_cleanup(wasi.map(AccountedWasi::usage));
    }
}
impl CacheConstructionPhase<'_> {
    pub(crate) fn construct(
        &mut self,
        adopted: AdoptedProof,
    ) -> Result<SwiftFunctionCache, CacheConstructionFailure> {
        let check = pairing(self.control.control, self.control.wasi, self.control.cursor).and_then(
            |observation| {
                self.control
                    .control
                    .check_adopted_owner(&adopted, self.control.cursor, observation)
            },
        );
        if let Err(failure) = check {
            self.constructed = true;
            return Err(CacheConstructionFailure {
                failure,
                rejected_adopted: Some(adopted),
            });
        }
        let repeated = std::mem::replace(&mut self.constructed, true);
        if repeated {
            let failure = self
                .control
                .error(CacheFailureKind::InvalidPin, "swift_cache_construct_once");
            return Err(CacheConstructionFailure {
                failure,
                rejected_adopted: Some(adopted),
            });
        }
        let mut partial = Partial::new(adopted);
        let result = self.construct_partial(&mut partial);
        match result {
            Ok((owner, usage)) => Ok(SwiftFunctionCache {
                adopted: partial.adopted.take().expect("whole adopted owner"),
                usage,
                owner,
                next_nonce: 1,
                slots: take(&mut partial.slots),
                pins: take(&mut partial.pins),
                patches: take(&mut partial.patches),
                buffers: std::mem::replace(&mut partial.buffers, std::array::from_fn(|_| None)),
                header: partial.header.take(),
            }),
            Err(failure) => {
                partial.cleanup(&mut self.control);
                Err(CacheConstructionFailure {
                    failure,
                    rejected_adopted: None,
                })
            }
        }
    }
    fn construct_partial(
        &mut self,
        partial: &mut Partial,
    ) -> Result<(u64, SwiftCacheUsage), SwiftRunFailure> {
        self.control.check()?;
        let header = cache_header_bytes().ok_or_else(|| {
            self.control
                .error(CacheFailureKind::Capacity, "swift_cache_layout_overflow")
        })?;
        partial.header = Some(self.control.admit(header)?);
        let budget = self.control.control.budget();
        let entries = budget.cache_entries.min(
            partial
                .adopted
                .as_ref()
                .expect("proof")
                .proof()
                .defined_function_count(),
        );
        let buffer_bytes = entries.checked_mul(size_of::<SwiftSlot>()).ok_or_else(|| {
            self.control
                .error(CacheFailureKind::Capacity, "swift_cache_layout_overflow")
        })?;
        partial.buffers[0] = Some(self.control.admit(buffer_bytes)?);
        reserve(&mut partial.slots, entries, &mut self.control)?;
        for _ in 0..entries {
            self.control.work(1)?;
            partial.slots.push(SwiftSlot {
                resident: None,
                pins: 0,
                last_used: 0,
            });
        }
        let buffer_bytes = budget
            .active_pins
            .checked_mul(size_of::<PinRecord>())
            .ok_or_else(|| {
                self.control
                    .error(CacheFailureKind::Capacity, "swift_cache_layout_overflow")
            })?;
        partial.buffers[1] = Some(self.control.admit(buffer_bytes)?);
        reserve(&mut partial.pins, budget.active_pins, &mut self.control)?;
        for _ in 0..budget.active_pins {
            self.control.work(1)?;
            partial.pins.push(PinRecord::default());
        }
        let buffer_bytes = PATCH_CAPACITY
            .checked_mul(size_of::<decode::Patch>())
            .ok_or_else(|| {
                self.control
                    .error(CacheFailureKind::Capacity, "swift_cache_layout_overflow")
            })?;
        partial.buffers[2] = Some(self.control.admit(buffer_bytes)?);
        reserve(&mut partial.patches, PATCH_CAPACITY, &mut self.control)?;
        for _ in 0..PATCH_CAPACITY {
            self.control.work(1)?;
            partial.patches.push(decode::EMPTY_PATCH);
        }
        self.control.check()?;
        let owner = next_owner().map_err(|_| {
            self.control.error(
                CacheFailureKind::IdentityExhausted,
                "swift_cache_owner_exhausted",
            )
        })?;
        let fixed_reserved = header
            + entries * size_of::<SwiftSlot>()
            + budget.active_pins * size_of::<PinRecord>()
            + PATCH_CAPACITY * size_of::<decode::Patch>();
        Ok((
            owner,
            SwiftCacheUsage {
                fixed_reserved,
                ..SwiftCacheUsage::default()
            },
        ))
    }
    pub(crate) fn complete<T>(self, returned_phase_storage: T) -> Result<(), SwiftRunFailure> {
        let Self {
            control: CacheControl { control, wasi, .. },
            previous_bound,
            ..
        } = self;
        control.end_construction_phase_with_wasi(
            returned_phase_storage,
            previous_bound,
            wasi.map(AccountedWasi::usage),
        )
    }
}
fn reserve<T>(
    values: &mut Vec<T>,
    requested: usize,
    control: &mut CacheControl<'_>,
) -> Result<(), SwiftRunFailure> {
    control.check()?;
    values.try_reserve_exact(requested).map_err(|_| {
        control.error(
            CacheFailureKind::AllocationFailure,
            "swift_cache_allocation",
        )
    })?;
    control.exact(requested, values.capacity())?;
    control.check()
}
impl CacheOperationPhase<'_> {
    pub(crate) fn pin(
        &mut self,
        cache: &mut SwiftFunctionCache,
        function: u32,
    ) -> Result<SwiftFunctionPin, SwiftRunFailure> {
        self.control.check_header(cache)?;
        pin::<SwiftMode>(
            CacheParts {
                snapshot: cache.adopted.proof(),
                slots: &mut cache.slots,
                pins: &mut cache.pins,
                owner: cache.owner,
                next_nonce: &mut cache.next_nonce,
                usage: &mut cache.usage,
                scratch: &mut cache.patches,
            },
            function,
            &mut self.control,
        )
    }
    pub(crate) fn complete<T>(self, returned_phase_storage: T) -> Result<(), SwiftRunFailure> {
        let Self {
            control: CacheControl { control, wasi, .. },
            previous_bound,
        } = self;
        control.end_construction_phase_with_wasi(
            returned_phase_storage,
            previous_bound,
            wasi.map(AccountedWasi::usage),
        )
    }
}
pub(crate) fn cache_cursor() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Cache,
        function: None,
        offset: None,
    }
}
pub(crate) struct SwiftMode;
impl sealed::Mode for SwiftMode {}
pub(crate) struct SwiftMeter<'a, 'op> {
    operation: &'a mut CacheControl<'op>,
    usage: &'a mut SwiftCacheUsage,
}
impl sealed::Meter for SwiftMeter<'_, '_> {}
impl DecodeMeter for SwiftMeter<'_, '_> {
    #[cfg(test)]
    fn diagnostic_site(&mut self, site: u8) { super::cache_tests::attribution_site(site); }
    #[cfg(test)]
    fn diagnostic_lookup_done(&mut self, hit: bool) { super::cache_tests::attribution_lookup_done(hit); }
    #[cfg(test)]
    fn diagnostic_decode_completed(&mut self, function: u32) { super::cache_tests::attribution_decode_completed(function); }
    type Failure = SwiftRunFailure;
    fn error(&mut self, kind: CacheFailureKind, code: &'static str) -> SwiftRunFailure {
        self.operation.error(kind, code)
    }
    fn check(&mut self) -> Result<(), SwiftRunFailure> {
        self.operation.check()
    }
    fn work(&mut self, n: u64) -> Result<(), SwiftRunFailure> {
        self.operation.work(n)
    }
    fn set_offset(&mut self, offset: usize) {
        self.operation.cursor.offset = Some(offset);
    }
    fn step(&mut self, step: CacheStep) {
        test_step(step);
    }
    fn exact_capacity(&mut self, requested: usize, observed: usize) -> Result<(), SwiftRunFailure> {
        self.operation.exact(requested, observed)
    }
}
impl AlgorithmMeter for SwiftMeter<'_, '_> {
    type Usage = SwiftCacheUsage;
    fn usage(&self) -> &SwiftCacheUsage {
        self.usage
    }
    fn usage_mut(&mut self) -> &mut SwiftCacheUsage {
        self.usage
    }
    fn detailed(
        &mut self,
        kind: CacheFailureKind,
        code: &'static str,
        attempted: u64,
        limit: u64,
    ) -> SwiftRunFailure {
        let mut fault = Fault::new(SwiftRunFailureKind::ResourceExhausted, code);
        fault.attempted = attempted;
        fault.limit = limit;
        fault.resource = Some(if kind == CacheFailureKind::EntryOversize {
            SwiftRunResource::CacheEntryBytes
        } else {
            SwiftRunResource::Reservation(SwiftReservationCategory::Cache)
        });
        self.operation
            .control
            .fail(self.operation.cursor, fault, self.operation.observation())
    }
    fn base(&self) -> usize {
        self.operation
            .control
            .usage(self.operation.observation())
            .reservations
            .cache
            .current
            - self.usage.resident_bytes
    }
    fn capacity(&self) -> usize {
        self.operation.control.budget().cache_bytes
    }
    fn entry_capacity(&self) -> usize {
        self.operation.control.budget().cache_entry_bytes
    }
    fn construction(&mut self, bytes: usize) -> Result<(), SwiftRunFailure> {
        self.usage.construction_bytes = bytes;
        self.usage.peak_construction_bytes = self.usage.peak_construction_bytes.max(bytes);
        Ok(())
    }
    fn work_used(&self) -> u64 {
        self.operation
            .control
            .usage(self.operation.observation())
            .cache_work
    }
    fn acquire_pin(&mut self) -> Result<(), SwiftRunFailure> {
        checkpoint(self.operation.control, self.operation.cursor);
        self.operation.control.add_live_with_wasi(
            Live::ActivePins,
            1,
            self.operation.cursor,
            self.operation.observation(),
        )
    }
    fn abandon_pin(&mut self) {
        let _ = self.operation.remove_live(Live::ActivePins);
    }
}
fn policy<'a>(
    snapshot: &'a ValidatedSwiftReactor,
    body: FunctionSpanView<'_>,
    meter: &mut SwiftMeter<'_, '_>,
) -> Result<SwiftPolicy<'a>, SwiftRunFailure> {
    // Descriptor/signature lookup costs one extra Swift credit per pass.
    meter.work(1)?;
    let parameters = snapshot
        .signature(body.absolute_index)
        .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_signature"))?
        .params
        .len();
    Ok(SwiftPolicy {
        policy: snapshot.policy(),
        extent: SnapshotView::source(snapshot).len(),
        parameters,
    })
}
fn reset(
    patches: &mut [decode::Patch],
    meter: &mut SwiftMeter<'_, '_>,
) -> Result<(), SwiftRunFailure> {
    if patches.len() != PATCH_CAPACITY {
        return Err(meter.error(
            CacheFailureKind::DecoderMismatch,
            "swift_cache_patch_capacity",
        ));
    }
    // Both passes start at depth zero and fully initialize each active slot
    // before reading it. Keep initialized reserved storage and the ordinary
    // cancellation/deadline boundary check; inactive slots need no clearing.
    #[cfg(test)]
    super::cache_tests::elision_dirty_before_boundary(patches);
    meter.check()
}
impl CacheMode for SwiftMode {
    type Snapshot = ValidatedSwiftReactor;
    type Slot = SwiftSlot;
    type Resident = SwiftResident;
    type Pin = SwiftFunctionPin;
    type Usage = SwiftCacheUsage;
    type Failure = SwiftRunFailure;
    type Operation<'a> = CacheControl<'a>;
    type Meter<'a, 'op>
        = SwiftMeter<'a, 'op>
    where
        'op: 'a;
    type Scratch<'a> = &'a mut [decode::Patch];
    fn meter<'a, 'op>(
        usage: &'a mut SwiftCacheUsage,
        operation: &'a mut CacheControl<'op>,
        function: u32,
    ) -> SwiftMeter<'a, 'op>
    where
        'op: 'a,
    {
        #[cfg(test)]
        super::cache_tests::attribution_begin(function);
        operation.cursor = Cursor {
            stage: SwiftRunStage::Cache,
            function: Some(function),
            offset: Some(0),
        };
        SwiftMeter { operation, usage }
    }
    fn scan(
        snapshot: &ValidatedSwiftReactor,
        body: FunctionSpanView<'_>,
        scratch: &mut &mut [decode::Patch],
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<decode::Counts, SwiftRunFailure> {
        #[cfg(test)]
        meter.diagnostic_site(4);
        let policy = policy(snapshot, body, meter)?;
        meter.step(CacheStep::ScanReset);
        reset(scratch, meter)?;
        meter.step(CacheStep::Scan);
        let mut depth = 0;
        let mut counts = decode::Counts::default();
        #[cfg(test)]
        meter.diagnostic_site(5);
        decode::scan_borrowed(
            body.body,
            body.body_offset,
            &policy,
            meter,
            decode::PassParts {
                controls: scratch,
                depth: &mut depth,
                counts: &mut counts,
            },
            None,
        )
    }
    fn build(
        snapshot: &ValidatedSwiftReactor,
        body: FunctionSpanView<'_>,
        counts: decode::Counts,
        scratch: &mut &mut [decode::Patch],
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<SwiftResident, SwiftRunFailure> {
        let bytes = counts.bytes(meter)?;
        checkpoint(meter.operation.control, meter.operation.cursor);
        let ticket = meter.operation.control.admit_cache_entry_with_wasi(
            bytes,
            meter.operation.cursor,
            meter.operation.observation(),
        )?;
        checkpoint(meter.operation.control, meter.operation.cursor);
        if let Err(error) = meter.operation.control.add_live_with_wasi(
            Live::CacheEntries,
            1,
            meter.operation.cursor,
            meter.operation.observation(),
        ) {
            let _ = meter.operation.drop_reserved((), ticket);
            return Err(error);
        }
        let result = Self::build_payload(snapshot, body, counts, scratch, meter);
        match result {
            Ok(decoded) => Ok(SwiftResident { decoded, ticket }),
            Err(error) => {
                let _ = meter.operation.drop_reserved((), ticket);
                let _ = meter.operation.remove_live(Live::CacheEntries);
                Err(error)
            }
        }
    }
    fn drop_entry(
        entry: SwiftResident,
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<(), SwiftRunFailure> {
        let dropped = meter.operation.drop_reserved(entry.decoded, entry.ticket);
        let removed = meter.operation.remove_live(Live::CacheEntries);
        dropped.and(removed)
    }
}
impl SwiftMode {
    fn build_payload(
        snapshot: &ValidatedSwiftReactor,
        body: FunctionSpanView<'_>,
        counts: decode::Counts,
        scratch: &mut &mut [decode::Patch],
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<DecodedFunction, SwiftRunFailure> {
        #[cfg(test)]
        meter.diagnostic_site(9);
        let policy = policy(snapshot, body, meter)?;
        meter.step(CacheStep::BuildReset);
        reset(scratch, meter)?;
        meter.step(CacheStep::Build);
        let mut depth = 0;
        let mut actual = decode::Counts::default();
        #[cfg(test)]
        meter.diagnostic_site(10);
        decode::build_borrowed(
            body.body,
            body.body_offset,
            body.type_index,
            body.absolute_index,
            &policy,
            counts,
            meter,
            decode::PassParts {
                controls: scratch,
                depth: &mut depth,
                counts: &mut actual,
            },
        )
    }
}
#[cfg(not(test))]
fn checkpoint(_: &RuntimeControl, _: Cursor) {}
#[cfg(not(test))]
fn capacity_observation(observed: usize) -> usize {
    observed
}
#[cfg(test)]
fn checkpoint(control: &RuntimeControl, cursor: Cursor) {
    super::cache_tests::checkpoint(control, cursor);
}
#[cfg(test)]
fn capacity_observation(observed: usize) -> usize {
    super::cache_tests::capacity_observation(observed)
}

#[cfg(not(test))]
fn test_step(_: CacheStep) {}
#[cfg(test)]
fn test_step(step: CacheStep) {
    super::cache_tests::step(step);
}
#[cfg(test)]
pub(super) mod inspection {
    use super::*;
    // Test-only snapshots of the actual owner, never stored in production state.
    pub fn elision_pin_parts(pin: &SwiftFunctionPin) -> [u64; 2] {
        [pin.slot as u64, pin.nonce]
    }
    pub fn elision_slots(cache: &SwiftFunctionCache) -> Vec<[u64; 4]> {
        cache
            .slots
            .iter()
            .enumerate()
            .map(|(index, slot)| {
                let function = slot
                    .resident
                    .as_ref()
                    .map(|r| r.decoded.function as u64)
                    .unwrap_or(u64::MAX);
                let rank = cache
                    .slots
                    .iter()
                    .filter(|other| other.resident.is_some() && other.last_used < slot.last_used)
                    .count();
                [index as u64, function, slot.pins as u64, rank as u64]
            })
            .collect()
    }
    pub fn elision_times(cache: &SwiftFunctionCache) -> Vec<u64> {
        cache.slots.iter().map(|slot| slot.last_used).collect()
    }
    pub fn elision_dirty_owner(cache: &mut SwiftFunctionCache) {
        super::super::cache_tests::elision_seed_patches(&mut cache.patches);
    }
    pub fn elision_malformed(cache: &mut SwiftFunctionCache, body: &[u8]) -> [&'static str; 2] {
        super::super::cache_tests::elision_seed_patches(&mut cache.patches);
        let limits = crate::Limits::default();
        let policy = crate::experimental::cache::borrowed::FrozenPolicy {
            limits: &limits,
            extent: body.len(),
        };
        let mut depth = 0;
        let mut counts = decode::Counts::default();
        let scan = decode::scan_borrowed(
            body,
            0,
            &policy,
            &mut super::super::cache_tests::ElisionScratchMeter,
            decode::PassParts {
                controls: &mut cache.patches,
                depth: &mut depth,
                counts: &mut counts,
            },
            None,
        )
        .err()
        .expect("malformed scan must fail");
        // Independent generous exact capacities from a valid finite body;
        // malformed syntax must fail before count/build agreement is reached.
        const VALID: &[u8] = &[0, 1, 1, 1, 1, 1, 1, 1, 1, 0x0b];
        depth = 0;
        counts = decode::Counts::default();
        let expected = decode::scan_borrowed(
            VALID,
            0,
            &policy,
            &mut super::super::cache_tests::ElisionScratchMeter,
            decode::PassParts {
                controls: &mut cache.patches,
                depth: &mut depth,
                counts: &mut counts,
            },
            None,
        )
        .unwrap();
        super::super::cache_tests::elision_seed_patches(&mut cache.patches);
        depth = 0;
        counts = decode::Counts::default();
        let build = decode::build_borrowed(
            body,
            0,
            0,
            34,
            &policy,
            expected,
            &mut super::super::cache_tests::ElisionScratchMeter,
            decode::PassParts {
                controls: &mut cache.patches,
                depth: &mut depth,
                counts: &mut counts,
            },
        )
        .err()
        .expect("malformed build must fail");
        [scan, build]
    }
    /// Swaps actual header authority, preserving the replaced original token.
    pub fn replace_header(
        cache: &mut SwiftFunctionCache,
        ticket: Option<ReservationTicket>,
    ) -> Option<ReservationTicket> {
        std::mem::replace(&mut cache.header, ticket)
    }
    /// A derived pre-effect completion fault at the actual original phase.
    /// No ticket or ledger changes; the original restoration API rejects zero.
    pub fn replace_operation_restore_bound(
        phase: &mut CacheOperationPhase<'_>,
        bound: usize,
    ) -> usize {
        std::mem::replace(&mut phase.previous_bound, bound)
    }
    pub fn with_owner_counter<T>(seed: u64, body: impl FnOnce() -> T) -> T {
        struct RestoreOwnerCounter(u64);
        impl Drop for RestoreOwnerCounter {
            fn drop(&mut self) {
                TEST_OWNER_COUNTER.with(|counter| counter.store(self.0, Ordering::Relaxed));
                TEST_OWNER_ENABLED.with(|enabled| enabled.set(false));
            }
        }
        TEST_OWNER_ENABLED.with(|enabled| assert!(!enabled.get(), "nested owner test counter"));
        let previous = TEST_OWNER_COUNTER.with(|counter| counter.swap(seed, Ordering::Relaxed));
        let restore = RestoreOwnerCounter(previous);
        TEST_OWNER_ENABLED.with(|enabled| enabled.set(true));
        let result = body();
        drop(restore);
        result
    }
    pub fn owner_counter() -> u64 {
        TEST_OWNER_COUNTER.with(|counter| counter.load(Ordering::Relaxed))
    }
    pub fn owner_override_active() -> bool {
        TEST_OWNER_ENABLED.with(std::cell::Cell::get)
    }
    pub fn latch_terminal(
        phase: &mut CacheOperationPhase<'_>,
        kind: SwiftRunFailureKind,
    ) -> SwiftRunFailure {
        let observation = phase.control.observation();
        phase.control.control.fail(
            phase.control.cursor,
            Fault::new(kind, "swift_cache_test_terminal_latch"),
            observation,
        )
    }
    pub fn operation_usage(phase: &CacheOperationPhase<'_>) -> SwiftRunUsage {
        phase.control.control.usage(phase.control.observation())
    }
    pub fn set_nonce(cache: &mut SwiftFunctionCache, n: u64) {
        cache.next_nonce = n;
    }
    pub fn stale(pin: &SwiftFunctionPin) -> SwiftFunctionPin {
        SwiftFunctionPin {
            owner: pin.owner,
            slot: pin.slot,
            nonce: pin.nonce,
        }
    }
    pub fn replace_entry_ticket(
        cache: &mut SwiftFunctionCache,
        ticket: ReservationTicket,
    ) -> ReservationTicket {
        std::mem::replace(
            &mut cache
                .slots
                .iter_mut()
                .find_map(|s| s.resident.as_mut())
                .expect("resident")
                .ticket,
            ticket,
        )
    }
    pub fn count_build_mismatch(
        cache: &mut SwiftFunctionCache,
        control: &mut RuntimeControl,
    ) -> SwiftRunFailure {
        let mut phase = cache
            .prepare_operation(control, None, cache_cursor())
            .unwrap();
        let body = cache.adopted.proof().function(34).unwrap();
        let mut meter = SwiftMode::meter(&mut cache.usage, &mut phase.control, 34);
        let counts = SwiftMode::scan(
            cache.adopted.proof(),
            body,
            &mut cache.patches.as_mut_slice(),
            &mut meter,
        )
        .unwrap();
        let result = SwiftMode::build(
            cache.adopted.proof(),
            body,
            counts.test_changed_instructions(),
            &mut cache.patches.as_mut_slice(),
            &mut meter,
        );
        let failure = result.err().expect("internal mismatch must fail");
        phase.complete(()).unwrap();
        failure
    }
    pub fn replace_tail_header(
        tail: &mut CacheCleanupTail<'_>,
        ticket: ReservationTicket,
    ) -> ReservationTicket {
        std::mem::replace(tail.header.as_mut().unwrap(), ticket)
    }
    pub fn construction_current(phase: &CacheConstructionPhase<'_>) -> usize {
        phase
            .control
            .control
            .usage(phase.control.observation())
            .reservations
            .construction
            .current
    }
    pub fn operation_current(phase: &CacheOperationPhase<'_>) -> usize {
        phase
            .control
            .control
            .usage(phase.control.observation())
            .reservations
            .construction
            .current
    }
    pub fn tail_construction(tail: &CacheCleanupTail<'_>) -> usize {
        tail.control
            .usage(tail.wasi.map(AccountedWasi::usage))
            .reservations
            .construction
            .current
    }
    pub fn preflight_chain_bytes() -> usize {
        size_of::<PreflightSetupInventory>()
            + size_of::<PreflightOwnerInventory>()
            + size_of::<PreflightPrimitiveInventory>()
            + size_of::<PreflightEnlargeInventory>()
    }
    pub fn assert_preflight_inventory() {
        println!("preflight result shapes prepared={} map={} transposed={} checked_wasi={} owner_check={}",
            size_of::<Result<PreparedBounds, SwiftRunFailure>>(),
            size_of::<Option<Result<WasiUsage, SwiftRunFailure>>>(),
            size_of::<Result<Option<WasiUsage>, SwiftRunFailure>>(),
            size_of::<Result<WasiUsage, SwiftRunFailure>>(),
            size_of::<Result<(), SwiftRunFailure>>());
        // Each whole control-transfer slot is disjoint from the actual owner
        // and from final owned control consumption / cleanup completion.
        println!(
            "preflight groups setup={} owner={} primitive={} enlarge={}",
            size_of::<PreflightSetupInventory>(),
            size_of::<PreflightOwnerInventory>(),
            size_of::<PreflightPrimitiveInventory>(),
            size_of::<PreflightEnlargeInventory>()
        );
        println!(
            "preflight helper-chain bytes={}",
            size_of::<PreflightSetupInventory>()
                + size_of::<PreflightOwnerInventory>()
                + size_of::<PreflightPrimitiveInventory>()
                + size_of::<PreflightEnlargeInventory>()
        );
        println!(
            "preflight groups A={} B={} control={}",
            size_of::<PreflightGroupA>(),
            size_of::<PreflightGroupB>(),
            size_of::<RuntimeControl>()
        );
        assert!(size_of::<PreflightSetupInventory>() <= size_of::<ValidatedSwiftReactor>());
        assert!(size_of::<PreflightOwnerInventory>() <= size_of::<ValidatedSwiftReactor>());
        assert!(size_of::<PreflightPrimitiveInventory>() <= size_of::<AdoptedProof>());
        assert!(size_of::<PreflightEnlargeInventory>() <= size_of::<AdoptedProof>());
        assert!(size_of::<PreflightGroupA>() <= size_of::<RuntimeControl>());
        assert!(size_of::<PreflightGroupB>() <= size_of::<RuntimeControl>());
        assert_eq!(
            size_of::<Result<PreparedBounds, SwiftRunFailure>>(),
            size_of::<Option<Result<WasiUsage, SwiftRunFailure>>>()
        );
        assert_eq!(
            size_of::<Result<PreparedBounds, SwiftRunFailure>>(),
            size_of::<Result<(usize, usize), SwiftRunFailure>>()
        );
        assert_eq!(
            size_of::<Result<PreparedBounds, SwiftRunFailure>>(),
            size_of::<Result<Option<WasiUsage>, SwiftRunFailure>>()
        );
        assert_eq!(
            size_of::<Result<PreparedBounds, SwiftRunFailure>>(),
            size_of::<Result<WasiUsage, SwiftRunFailure>>()
        );
        assert_eq!(
            size_of::<Result<PreparedBounds, SwiftRunFailure>>(),
            size_of::<Result<(), SwiftRunFailure>>()
        );
    }
    pub fn print_layouts() {
        use std::mem::{align_of, offset_of};
        macro_rules! row {
            ($t:ty) => {
                println!(
                    "layout {} {} {}",
                    stringify!($t),
                    size_of::<$t>(),
                    align_of::<$t>()
                );
            };
        }
        row!(Result<Option<WasiUsage>, SwiftRunFailure>);
        row!(Option<Result<WasiUsage, SwiftRunFailure>>);
        row!(Result<WasiUsage, SwiftRunFailure>);
        row!(PermanentScalarInventory);
        row!(PermanentBorrowChainInventory);
        row!(Option<PinRecord>);
        row!(Option<&'static PinRecord>);
        row!(Option<&'static SwiftSlot>);
        row!(Option<&'static DecodedFunction>);
        row!((&'static SwiftFunctionPin, &'static PinRecord));
        row!(CacheParts<'static, SwiftMode>);
        row!(CacheViewParts<'static, SwiftMode>);
        row!(PinRecord);
        row!(Result<PinRecord, SwiftRunFailure>);
        row!(FunctionView<'static>);
        row!(Result<FunctionView<'static>, SwiftRunFailure>);
        row!((SwiftRunFailure, SwiftFunctionPin));
        row!(Result<(), (SwiftRunFailure, SwiftFunctionPin)>);
        row!(SwiftFunctionPin);
        row!(SwiftCacheUsage);
        row!(SwiftCacheIdentity);
        row!(Option<SwiftFunctionCache>);
        row!(SwiftFunctionCache);
        row!(Result<CacheCleanupTail<'static>, SwiftRunFailure>);
        row!(CacheCleanupTail<'static>);
        row!(Option<CacheCleanupTail<'static>>);
        row!(CleanupCompletionParts<'static>);
        row!(Option<SwiftResident>);
        row!(SwiftResident);
        row!(DecodedFunction);
        row!(Vec<SwiftSlot>);
        row!(Vec<PinRecord>);
        row!(Vec<decode::Patch>);
        row!(Option<ReservationTicket>);
        row!(ReservationTicket);
        row!(CacheControl<'static>);
        row!(SwiftRunFailure);
        row!(Option<SwiftRunFailure>);
        row!(Result<(), SwiftRunFailure>);
        row!(SwiftRunUsage);
        row!(WasiUsage);
        row!(Option<WasiUsage>);
        row!(Fault);
        row!(Cursor);
        row!(SwiftReleaseFailure);
        row!(Result<(), SwiftReleaseFailure>);
        row!(ValidatedSwiftReactor);
        row!(Result<CacheConstructionPhase<'static>, SwiftRunFailure>);
        row!(Result<ReservationTicket, SwiftRunFailure>);
        row!(std::collections::TryReserveError);
        row!(Result<(), std::collections::TryReserveError>);
        row!(Result<u64, u64>);
        row!(Option<u64>);
        row!(Result<u64, SwiftRunFailure>);
        row!(ConstructionScalarInventory);
        row!(ConstructionBorrowChainInventory);
        row!(SwiftRunBudget);
        row!((u64, SwiftCacheUsage));
        row!(Result<(u64, SwiftCacheUsage), SwiftRunFailure>);
        row!(PreparedBounds);
        row!(CacheConstructionPhase<'static>);
        row!(Partial);
        row!(Result<SwiftFunctionCache, CacheConstructionFailure>);
        row!(CacheConstructionFailure);
        row!(ConstructionReturnSlot);
        row!(Option<AdoptedProof>);
        row!(Result<CacheOperationPhase<'static>, SwiftRunFailure>);
        row!(OperationScalarInventory);
        row!(OperationBorrowChainInventory);
        row!((&'static SwiftPolicy<'static>,));
        row!(Option<FunctionSpanView<'static>>);
        row!(Option<crate::experimental::descriptors::SignatureView<'static>>);
        row!(Option<&'static mut DecodedFunction>);
        row!(Option<&'static mut crate::experimental::cache::DecodedInstruction>);
        row!(&'static [u8; 4]);
        row!(&'static [u8; 8]);
        row!([u8; 4]);
        row!([u8; 8]);
        row!(Result<[u8; 4], std::array::TryFromSliceError>);
        row!(Result<[u8; 8], std::array::TryFromSliceError>);
        row!((&'static mut SwiftMeter<'static, 'static>,));
        row!((&'static u32,));
        row!((&'static SwiftSlot, &'static CacheFields<'static, SwiftMode>));
        row!(crate::experimental::descriptors::SignatureView<'static>);
        row!(Result<SwiftPolicy<'static>, SwiftRunFailure>);
        row!(Result<decode::Counts, SwiftRunFailure>);
        row!(Result<usize, SwiftRunFailure>);
        row!(Result<u8, SwiftRunFailure>);
        row!(Result<u32, SwiftRunFailure>);
        row!(Result<i64, SwiftRunFailure>);
        row!(Result<crate::Type, SwiftRunFailure>);
        row!(Result<&'static [u8], SwiftRunFailure>);
        row!(crate::Value);
        row!(crate::experimental::cache::Operation);
        row!(crate::experimental::cache::DecodedInstruction);
        row!(decode::Patch);
        row!(Vec<crate::Type>);
        row!(Vec<crate::experimental::cache::DecodedInstruction>);
        row!(Vec<u32>);
        row!(Result<Vec<crate::Type>, SwiftRunFailure>);
        row!(Result<Vec<crate::experimental::cache::DecodedInstruction>, SwiftRunFailure>);
        row!(Result<Vec<u32>, SwiftRunFailure>);
        row!(CacheOperationPhase<'static>);
        row!(CacheFields<'static, SwiftMode>);
        row!(SwiftMeter<'static, 'static>);
        row!(decode::Reader<'static>);
        row!(decode::PassParts<'static>);
        row!(decode::Counts);
        row!(SwiftPolicy<'static>);
        row!([bool; 64]);
        row!(Result<SwiftResident, SwiftRunFailure>);
        row!(Result<DecodedFunction, SwiftRunFailure>);
        row!(Result<SwiftFunctionPin, SwiftRunFailure>);
        row!(OperationReturnSlot);
        row!(FunctionSpanView<'static>);
        row!(RootLeafInventory);
        row!(RuntimeControl);
        row!(CompletionBorrowInventory);
        row!(PreflightGroupA);
        row!(PreflightGroupB);
        row!(PreflightSetupInventory);
        row!(PreflightOwnerInventory);
        row!(PreflightPrimitiveInventory);
        row!(AdoptedProof);
        row!(PreflightEnlargeInventory);
        row!(SwiftSlot);
        row!(Result<PreparedBounds, SwiftRunFailure>);
        row!(Result<(usize, usize), SwiftRunFailure>);
        row!(RootAdmissionExtraInventory);
        row!(RootAdmissionBoundaryInventory);
        row!(RootOwnerBoundaryInventory);
        row!(RootWorkLiveInventory);
        row!(RootWorkLiveBoundaryInventory);
        row!(RootRemoveLiveInventory);
        row!(RootRemoveLiveBoundaryInventory);
        row!(RootRefundInventory);
        row!(RootPhaseEndInventory);
        row!(RootRefundBoundaryInventory);
        macro_rules! field {
            ($model:ty, $field:ident, $t:ty) => {
                println!(
                    "model {} {} {} {} {} {}",
                    stringify!($model),
                    stringify!($field),
                    stringify!($t),
                    size_of::<$t>(),
                    align_of::<$t>(),
                    offset_of!($model, $field)
                );
            };
        }
        field!(
            ConstructionBorrowChainInventory,
            prepare_control,
            &'static mut RuntimeControl
        );
        field!(
            ConstructionBorrowChainInventory,
            prepare_wasi,
            Option<&'static AccountedWasi>
        );
        field!(
            ConstructionBorrowChainInventory,
            prepare_adopted,
            &'static AdoptedProof
        );
        field!(
            ConstructionBorrowChainInventory,
            construct_phase,
            &'static mut CacheConstructionPhase<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            construct_partial_phase,
            &'static mut CacheConstructionPhase<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            construct_partial_partial,
            &'static mut Partial
        );
        field!(
            ConstructionBorrowChainInventory,
            partial_cleanup_partial,
            &'static mut Partial
        );
        field!(
            ConstructionBorrowChainInventory,
            partial_cleanup_control,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            reserve_slots_values,
            &'static mut Vec<SwiftSlot>
        );
        field!(
            ConstructionBorrowChainInventory,
            reserve_slots_control,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            reserve_pins_values,
            &'static mut Vec<PinRecord>
        );
        field!(
            ConstructionBorrowChainInventory,
            reserve_pins_control,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            reserve_patches_values,
            &'static mut Vec<decode::Patch>
        );
        field!(
            ConstructionBorrowChainInventory,
            reserve_patches_control,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_check_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_work_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_error_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_admit_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_exact_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_drop_reserved_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            control_observation_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionBorrowChainInventory,
            owner_allocator_argument,
            &'static AtomicU64
        );
        field!(
            ConstructionBorrowChainInventory,
            owner_allocator_counter,
            &'static AtomicU64
        );
        field!(
            PermanentBorrowChainInventory,
            cache_view_cache,
            &'static SwiftFunctionCache
        );
        field!(
            PermanentBorrowChainInventory,
            cache_view_pin,
            &'static SwiftFunctionPin
        );
        field!(
            PermanentBorrowChainInventory,
            cache_view_control,
            &'static mut RuntimeControl
        );
        field!(
            PermanentBorrowChainInventory,
            cache_view_wasi,
            Option<&'static AccountedWasi>
        );
        field!(
            PermanentBorrowChainInventory,
            cache_release_cache,
            &'static mut SwiftFunctionCache
        );
        field!(
            PermanentBorrowChainInventory,
            cache_release_control,
            &'static mut RuntimeControl
        );
        field!(
            PermanentBorrowChainInventory,
            cache_release_wasi,
            Option<&'static AccountedWasi>
        );
        field!(
            PermanentBorrowChainInventory,
            generic_view_pin,
            &'static SwiftFunctionPin
        );
        field!(
            PermanentBorrowChainInventory,
            generic_view_meter,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            generic_release_operation,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            checked_record_pin,
            &'static SwiftFunctionPin
        );
        field!(
            PermanentBorrowChainInventory,
            checked_record_meter,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            control_check_header_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            control_invalid_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            control_error_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            control_release_pin_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            control_remove_live_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            control_observation_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentBorrowChainInventory,
            slot_entry_receiver,
            &'static SwiftSlot
        );
        field!(
            PermanentBorrowChainInventory,
            slot_pins_receiver,
            &'static SwiftSlot
        );
        field!(
            PermanentBorrowChainInventory,
            slot_set_pins_receiver,
            &'static mut SwiftSlot
        );
        field!(
            PermanentBorrowChainInventory,
            usage_release_receiver,
            &'static mut SwiftCacheUsage
        );
        field!(
            PermanentBorrowChainInventory,
            cleanup_owner,
            &'static mut Option<SwiftFunctionCache>
        );
        field!(
            PermanentBorrowChainInventory,
            cleanup_control,
            &'static mut RuntimeControl
        );
        field!(
            PermanentBorrowChainInventory,
            cleanup_wasi,
            Option<&'static AccountedWasi>
        );
        field!(
            PermanentBorrowChainInventory,
            capture_failure,
            &'static mut Option<SwiftRunFailure>
        );
        field!(
            PermanentBorrowChainInventory,
            tail_complete_outcome,
            &'static mut Option<SwiftRunFailure>
        );
        field!(ConstructionScalarInventory, previous_bound, usize);
        field!(ConstructionScalarInventory, bound, usize);
        field!(ConstructionScalarInventory, bound_add, usize);
        field!(ConstructionScalarInventory, header, usize);
        field!(ConstructionScalarInventory, entries, usize);
        field!(ConstructionScalarInventory, slots_bytes, usize);
        field!(ConstructionScalarInventory, pins_bytes, usize);
        field!(ConstructionScalarInventory, patches_bytes, usize);
        field!(ConstructionScalarInventory, fixed_reserved, usize);
        field!(ConstructionScalarInventory, requested, usize);
        field!(ConstructionScalarInventory, observed, usize);
        field!(ConstructionScalarInventory, bytes, usize);
        field!(ConstructionScalarInventory, owner, u64);
        field!(ConstructionScalarInventory, owner_candidate, u64);
        field!(ConstructionScalarInventory, work, u64);
        field!(ConstructionScalarInventory, repeated, bool);
        field!(
            ConstructionScalarInventory,
            slots_range,
            std::ops::Range<usize>
        );
        field!(
            ConstructionScalarInventory,
            pins_range,
            std::ops::Range<usize>
        );
        field!(
            ConstructionScalarInventory,
            patches_range,
            std::ops::Range<usize>
        );
        field!(
            ConstructionScalarInventory,
            buffers_range,
            std::ops::Range<usize>
        );
        field!(
            ConstructionScalarInventory,
            control,
            &'static mut RuntimeControl
        );
        field!(
            ConstructionScalarInventory,
            wasi,
            Option<&'static AccountedWasi>
        );
        field!(ConstructionScalarInventory, adopted, &'static AdoptedProof);
        field!(ConstructionScalarInventory, partial, &'static mut Partial);
        field!(
            ConstructionScalarInventory,
            wrapper,
            &'static mut CacheControl<'static>
        );
        field!(
            ConstructionScalarInventory,
            slots,
            &'static mut Vec<SwiftSlot>
        );
        field!(
            ConstructionScalarInventory,
            pins,
            &'static mut Vec<PinRecord>
        );
        field!(
            ConstructionScalarInventory,
            patches,
            &'static mut Vec<decode::Patch>
        );
        field!(OperationScalarInventory, function, u32);
        field!(OperationScalarInventory, checked_nonce, u64);
        field!(OperationScalarInventory, pin_slot_search, Option<usize>);
        field!(OperationScalarInventory, pin_slot, usize);
        field!(OperationScalarInventory, hit, Option<usize>);
        field!(OperationScalarInventory, index, usize);
        field!(OperationScalarInventory, hits, u64);
        field!(OperationScalarInventory, misses, u64);
        field!(OperationScalarInventory, next_decodes, u64);
        field!(OperationScalarInventory, bytes, usize);
        field!(OperationScalarInventory, base, usize);
        field!(OperationScalarInventory, capacity, usize);
        field!(OperationScalarInventory, remaining, usize);
        field!(OperationScalarInventory, empty, Option<usize>);
        field!(OperationScalarInventory, oldest, Option<usize>);
        field!(OperationScalarInventory, victim, usize);
        field!(OperationScalarInventory, evictions, u64);
        field!(OperationScalarInventory, victim_bytes, usize);
        field!(OperationScalarInventory, publish_index, usize);
        field!(OperationScalarInventory, requested, usize);
        field!(OperationScalarInventory, observed, usize);
        field!(OperationScalarInventory, depth, usize);
        field!(OperationScalarInventory, parameters, usize);
        field!(OperationScalarInventory, groups, usize);
        field!(OperationScalarInventory, local_count, usize);
        field!(OperationScalarInventory, local_type, crate::Type);
        field!(OperationScalarInventory, offset, usize);
        field!(OperationScalarInventory, opcode, u8);
        field!(OperationScalarInventory, instruction_index, usize);
        field!(OperationScalarInventory, ended, bool);
        field!(OperationScalarInventory, block_result, Option<crate::Type>);
        field!(
            OperationScalarInventory,
            block_kind,
            crate::experimental::cache::ControlKind
        );
        field!(OperationScalarInventory, alternative, usize);
        field!(OperationScalarInventory, branch_count, usize);
        field!(OperationScalarInventory, first_target, usize);
        field!(OperationScalarInventory, target, u32);
        field!(OperationScalarInventory, indirect_type, u32);
        field!(OperationScalarInventory, extended_opcode, u32);
        field!(OperationScalarInventory, reader_take_bytes, &'static [u8]);
        field!(OperationScalarInventory, eviction_selected, &'static bool);
        field!(OperationScalarInventory, take_count, usize);
        field!(OperationScalarInventory, take_end, usize);
        field!(OperationScalarInventory, byte, u8);
        field!(OperationScalarInventory, uint_value, u32);
        field!(OperationScalarInventory, uint_index, u32);
        field!(OperationScalarInventory, signed_bits, u32);
        field!(OperationScalarInventory, signed_maximum, u32);
        field!(OperationScalarInventory, signed_value, u64);
        field!(OperationScalarInventory, signed_index, u32);
        field!(OperationScalarInventory, signed_byte, u8);
        field!(OperationScalarInventory, signed_part, u8);
        field!(OperationScalarInventory, signed_used, u32);
        field!(OperationScalarInventory, signed_positive, u8);
        field!(OperationScalarInventory, signed_negative, u8);
        field!(OperationScalarInventory, signed_shift, u32);
        field!(OperationScalarInventory, work, u64);
        field!(OperationScalarInventory, attempted, u64);
        field!(OperationScalarInventory, limit, u64);
        field!(OperationScalarInventory, count_product, usize);
        field!(OperationScalarInventory, code_product, usize);
        field!(OperationScalarInventory, target_product, usize);
        field!(OperationScalarInventory, checked_total, usize);
        field!(
            OperationScalarInventory,
            pin_search,
            std::iter::Enumerate<std::slice::Iter<'static, PinRecord>>
        );
        field!(
            OperationScalarInventory,
            hit_search,
            std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>
        );
        field!(
            OperationScalarInventory,
            empty_search,
            std::slice::Iter<'static, SwiftSlot>
        );
        field!(
            OperationScalarInventory,
            victim_search,
            std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>
        );
        field!(
            OperationScalarInventory,
            eviction_count,
            std::slice::Iter<'static, bool>
        );
        field!(
            OperationScalarInventory,
            eviction_apply,
            std::iter::Take<std::iter::Enumerate<std::slice::Iter<'static, bool>>>
        );
        field!(
            OperationScalarInventory,
            patch_reset,
            std::slice::IterMut<'static, decode::Patch>
        );
        field!(
            OperationScalarInventory,
            parameter_range,
            std::ops::Range<usize>
        );
        field!(
            OperationScalarInventory,
            group_range,
            std::ops::Range<usize>
        );
        field!(
            OperationScalarInventory,
            local_range,
            std::ops::Range<usize>
        );
        field!(
            OperationScalarInventory,
            branch_range,
            std::ops::Range<usize>
        );
        field!(OperationScalarInventory, uint_range, std::ops::Range<u32>);
        field!(OperationScalarInventory, signed_range, std::ops::Range<u32>);
        field!(
            OperationScalarInventory,
            snapshot,
            &'static ValidatedSwiftReactor
        );
        field!(OperationScalarInventory, body, &'static [u8]);
        field!(
            OperationScalarInventory,
            policy,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationScalarInventory,
            parts,
            &'static mut CacheFields<'static, SwiftMode>
        );
        field!(
            OperationScalarInventory,
            meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationScalarInventory,
            operation,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationScalarInventory,
            scratch,
            &'static mut [decode::Patch]
        );
        field!(
            OperationScalarInventory,
            output,
            Option<&'static mut DecodedFunction>
        );
        field!(
            OperationScalarInventory,
            locals,
            &'static mut Vec<crate::Type>
        );
        field!(
            OperationScalarInventory,
            instructions,
            &'static mut Vec<crate::experimental::cache::DecodedInstruction>
        );
        field!(OperationScalarInventory, targets, &'static mut Vec<u32>);
        field!(
            OperationBorrowChainInventory,
            pin_operation,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            pin_acquired_parts,
            &'static mut CacheFields<'static, SwiftMode>
        );
        field!(
            OperationBorrowChainInventory,
            pin_acquired_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            mode_meter_usage,
            &'static mut SwiftCacheUsage
        );
        field!(
            OperationBorrowChainInventory,
            mode_meter_operation,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            mode_scan_snapshot,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            mode_scan_body,
            FunctionSpanView<'static>
        );
        field!(
            OperationBorrowChainInventory,
            mode_scan_scratch,
            &'static mut &'static mut [decode::Patch]
        );
        field!(
            OperationBorrowChainInventory,
            mode_scan_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            mode_build_snapshot,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            mode_build_body,
            FunctionSpanView<'static>
        );
        field!(
            OperationBorrowChainInventory,
            mode_build_scratch,
            &'static mut &'static mut [decode::Patch]
        );
        field!(
            OperationBorrowChainInventory,
            mode_build_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            build_payload_snapshot,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            build_payload_body,
            FunctionSpanView<'static>
        );
        field!(
            OperationBorrowChainInventory,
            build_payload_scratch,
            &'static mut &'static mut [decode::Patch]
        );
        field!(
            OperationBorrowChainInventory,
            build_payload_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            decode_scan_body,
            &'static [u8]
        );
        field!(
            OperationBorrowChainInventory,
            decode_scan_policy,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            decode_scan_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            decode_build_body,
            &'static [u8]
        );
        field!(
            OperationBorrowChainInventory,
            decode_build_policy,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            decode_build_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_take_filter_capture,
            &'static &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_take_filter_argument,
            &'static usize
        );
        field!(
            OperationBorrowChainInventory,
            locals_filter_policy_capture,
            &'static &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            locals_filter_argument,
            &'static usize
        );
        field!(
            OperationBorrowChainInventory,
            locals_is_some_and_policy_capture,
            &'static &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            locals_is_some_and_argument,
            usize
        );
        field!(
            OperationBorrowChainInventory,
            reader_byte_reader,
            &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_byte_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_take_reader,
            &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_take_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_uint_reader,
            &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_uint_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_signed_reader,
            &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_signed_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_type_reader,
            &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_type_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_zero_reader,
            &'static mut decode::Reader<'static>
        );
        field!(
            OperationBorrowChainInventory,
            reader_zero_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            push_local_values,
            &'static mut Vec<crate::Type>
        );
        field!(
            OperationBorrowChainInventory,
            push_local_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            allocate_local_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            push_instruction_values,
            &'static mut Vec<crate::experimental::cache::DecodedInstruction>
        );
        field!(
            OperationBorrowChainInventory,
            push_instruction_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            allocate_instruction_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            push_target_values,
            &'static mut Vec<u32>
        );
        field!(
            OperationBorrowChainInventory,
            push_target_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            allocate_target_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            reset_patches,
            &'static mut [decode::Patch]
        );
        field!(
            OperationBorrowChainInventory,
            reset_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_snapshot,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            policy_body,
            FunctionSpanView<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_meter,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_error_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_check_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_work_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_set_offset_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_exact_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_base_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_capacity_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_entry_capacity_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_construction_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_work_used_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_acquire_pin_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_abandon_pin_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_detailed_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_usage_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            swift_meter_usage_mut_receiver,
            &'static mut SwiftMeter<'static, 'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_error_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_check_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_work_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_admit_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_exact_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_drop_reserved_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_remove_live_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            control_check_header_receiver,
            &'static mut CacheControl<'static>
        );
        field!(
            OperationBorrowChainInventory,
            snapshot_function_receiver,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            snapshot_signature_receiver,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            snapshot_source_receiver,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            snapshot_policy_receiver,
            &'static ValidatedSwiftReactor
        );
        field!(
            OperationBorrowChainInventory,
            policy_floats_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_tables_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_source_extent_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_parameters_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_parameters_limit_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_local_groups_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_total_locals_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_instructions_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_control_depth_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            policy_counts_parameters_receiver,
            &'static SwiftPolicy<'static>
        );
        field!(
            OperationBorrowChainInventory,
            statistics_decoded_receiver,
            &'static mut SwiftCacheUsage
        );
        field!(
            OperationBorrowChainInventory,
            statistics_pin_receiver,
            &'static mut SwiftCacheUsage
        );
        field!(
            OperationBorrowChainInventory,
            statistics_evicted_receiver,
            &'static mut SwiftCacheUsage
        );
        field!(
            OperationBorrowChainInventory,
            mode_build_counts,
            decode::Counts
        );
        field!(
            OperationBorrowChainInventory,
            build_payload_counts,
            decode::Counts
        );
        field!(
            OperationBorrowChainInventory,
            decode_build_counts,
            decode::Counts
        );
        field!(
            OperationBorrowChainInventory,
            counts_bytes_counts,
            decode::Counts
        );
        field!(
            PermanentScalarInventory,
            owner,
            &'static mut Option<SwiftFunctionCache>
        );
        field!(
            PermanentScalarInventory,
            control,
            &'static mut RuntimeControl
        );
        field!(
            PermanentScalarInventory,
            wasi,
            Option<&'static AccountedWasi>
        );
        field!(PermanentScalarInventory, cache, &'static SwiftFunctionCache);
        field!(PermanentScalarInventory, pin, &'static SwiftFunctionPin);
        field!(PermanentScalarInventory, record, PinRecord);
        field!(PermanentScalarInventory, slot, &'static mut SwiftSlot);
        field!(PermanentScalarInventory, pin_record, &'static mut PinRecord);
        field!(
            PermanentScalarInventory,
            pins_iter,
            std::slice::IterMut<'static, PinRecord>
        );
        field!(
            PermanentScalarInventory,
            slots_iter,
            std::slice::IterMut<'static, SwiftSlot>
        );
        field!(
            PermanentScalarInventory,
            buffers_range,
            std::ops::Range<usize>
        );
        field!(PermanentScalarInventory, buffer_index, usize);
        field!(PermanentScalarInventory, bytes, usize);
        field!(PermanentScalarInventory, last_pin, bool);
        field!(
            PermanentScalarInventory,
            control_wrapper,
            &'static mut CacheControl<'static>
        );
        field!(
            PermanentScalarInventory,
            outcome,
            &'static mut Option<SwiftRunFailure>
        );
        field!(
            PermanentScalarInventory,
            borrowed_parts,
            CleanupCompletionParts<'static>
        );
        field!(PreparedBounds, previous, usize);
        field!(PreparedBounds, enlarged, usize);
        field!(
            PreflightSetupInventory,
            prepare_control,
            &'static mut RuntimeControl
        );
        field!(
            PreflightSetupInventory,
            prepare_wasi,
            Option<&'static AccountedWasi>
        );
        field!(
            PreflightSetupInventory,
            prepare_adopted,
            Option<&'static AdoptedProof>
        );
        field!(
            PreflightSetupInventory,
            prepare_cache,
            Option<&'static SwiftFunctionCache>
        );
        field!(PreflightSetupInventory, prepare_cursor, Cursor);
        field!(
            PreflightSetupInventory,
            helper_control,
            &'static mut RuntimeControl
        );
        field!(
            PreflightSetupInventory,
            helper_wasi,
            Option<&'static AccountedWasi>
        );
        field!(
            PreflightSetupInventory,
            helper_adopted,
            Option<&'static AdoptedProof>
        );
        field!(
            PreflightSetupInventory,
            helper_cache,
            Option<&'static SwiftFunctionCache>
        );
        field!(PreflightSetupInventory, helper_cursor, Cursor);
        field!(
            PreflightSetupInventory,
            pairing_control,
            &'static mut RuntimeControl
        );
        field!(
            PreflightSetupInventory,
            pairing_wasi,
            Option<&'static AccountedWasi>
        );
        field!(PreflightSetupInventory, pairing_cursor, Cursor);
        field!(
            PreflightSetupInventory,
            pairing_closure_control,
            &'static mut RuntimeControl
        );
        field!(
            PreflightSetupInventory,
            pairing_closure_wasi,
            &'static AccountedWasi
        );
        field!(
            PreflightSetupInventory,
            pairing_closure_cursor,
            &'static Cursor
        );
        field!(
            PreflightSetupInventory,
            header_borrow,
            Option<&'static ReservationTicket>
        );
        field!(
            PreflightSetupInventory,
            failure_closure_control,
            &'static mut RuntimeControl
        );
        field!(
            PreflightSetupInventory,
            failure_closure_observation,
            &'static Option<WasiUsage>
        );
        field!(
            PreflightSetupInventory,
            failure_closure_cursor,
            &'static Cursor
        );
        field!(
            PreflightSetupInventory,
            bound_closure_previous,
            &'static usize
        );
        field!(PreflightSetupInventory, bound_closure_argument, usize);
        field!(
            PreflightSetupInventory,
            layout_failure_control,
            &'static mut RuntimeControl
        );
        field!(
            PreflightSetupInventory,
            layout_failure_observation,
            Option<WasiUsage>
        );
        field!(PreflightSetupInventory, layout_failure_cursor, Cursor);
        field!(
            PreflightSetupInventory,
            checkpoint_control,
            &'static RuntimeControl
        );
        field!(PreflightSetupInventory, checkpoint_cursor, Cursor);
        field!(
            PreflightOwnerInventory,
            checked_usage_self,
            &'static AccountedWasi
        );
        field!(
            PreflightOwnerInventory,
            checked_usage_control,
            &'static mut RuntimeControl
        );
        field!(PreflightOwnerInventory, checked_usage_cursor, Cursor);
        field!(
            PreflightOwnerInventory,
            checked_usage_header,
            &'static ReservationTicket
        );
        field!(
            PreflightOwnerInventory,
            checked_usage_then_self,
            &'static AccountedWasi
        );
        field!(
            PreflightOwnerInventory,
            wasi_usage_self,
            &'static AccountedWasi
        );
        field!(
            PreflightOwnerInventory,
            context_usage_self,
            &'static crate::experimental_wasi::WasiContext
        );
        field!(
            PreflightOwnerInventory,
            reservation_matches_self,
            &'static RuntimeControl
        );
        field!(
            PreflightOwnerInventory,
            reservation_matches_ticket,
            &'static ReservationTicket
        );
        field!(
            PreflightOwnerInventory,
            adopted_owner_self,
            &'static mut RuntimeControl
        );
        field!(
            PreflightOwnerInventory,
            adopted_owner_adopted,
            &'static AdoptedProof
        );
        field!(PreflightOwnerInventory, adopted_owner_cursor, Cursor);
        field!(
            PreflightOwnerInventory,
            reservation_owner_self,
            &'static mut RuntimeControl
        );
        field!(
            PreflightOwnerInventory,
            reservation_owner_ticket,
            &'static ReservationTicket
        );
        field!(PreflightOwnerInventory, reservation_owner_cursor, Cursor);
        field!(
            PreflightOwnerInventory,
            reservation_violation,
            Option<(SwiftCleanupInvariant, &'static str)>
        );
        field!(
            PreflightOwnerInventory,
            reservation_match_option,
            Option<(SwiftCleanupInvariant, &'static str)>
        );
        field!(
            PreflightOwnerInventory,
            reservation_match_tuple,
            (SwiftCleanupInvariant, &'static str)
        );
        field!(
            PreflightOwnerInventory,
            reservation_insert_receiver,
            &'static mut Option<SwiftCleanupInvariant>
        );
        field!(
            PreflightOwnerInventory,
            reservation_insert_argument,
            SwiftCleanupInvariant
        );
        field!(
            PreflightOwnerInventory,
            reservation_invariant,
            SwiftCleanupInvariant
        );
        field!(PreflightOwnerInventory, reservation_code, &'static str);
        field!(
            PreflightOwnerInventory,
            reservation_inserted,
            &'static mut SwiftCleanupInvariant
        );
        field!(
            PreflightOwnerInventory,
            category_self,
            &'static SwiftReservations
        );
        field!(
            PreflightOwnerInventory,
            category_argument,
            SwiftReservationCategory
        );
        field!(
            PreflightOwnerInventory,
            category_result,
            &'static SwiftReservationUsage
        );
        field!(
            PreflightOwnerInventory,
            header_option_receiver,
            &'static Option<ReservationTicket>
        );
        field!(
            PreflightOwnerInventory,
            header_option_return,
            Option<&'static ReservationTicket>
        );
        field!(PreflightOwnerInventory, reservation_matches_result, bool);
        field!(PreflightOwnerInventory, then_receiver, bool);
        field!(
            PreflightOwnerInventory,
            adopted_source_borrow,
            &'static ReservationTicket
        );
        field!(
            PreflightOwnerInventory,
            adopted_metadata_borrow,
            &'static ReservationTicket
        );
        field!(
            PreflightPrimitiveInventory,
            fail_self,
            &'static mut RuntimeControl
        );
        field!(PreflightPrimitiveInventory, fail_cursor, Cursor);
        field!(PreflightPrimitiveInventory, fault_source, Fault);
        field!(PreflightPrimitiveInventory, fault_transfer, Fault);
        field!(PreflightPrimitiveInventory, fault_kind, SwiftRunFailureKind);
        field!(PreflightPrimitiveInventory, fault_code, &'static str);
        field!(
            PreflightPrimitiveInventory,
            usage_self,
            &'static RuntimeControl
        );
        field!(PreflightPrimitiveInventory, usage_now, std::time::Instant);
        field!(
            PreflightPrimitiveInventory,
            elapsed_receiver,
            &'static std::time::Instant
        );
        field!(
            PreflightPrimitiveInventory,
            elapsed_earlier,
            std::time::Instant
        );
        field!(
            PreflightPrimitiveInventory,
            elapsed_duration,
            std::time::Duration
        );
        field!(
            PreflightPrimitiveInventory,
            overshoot_receiver,
            &'static std::time::Instant
        );
        field!(
            PreflightPrimitiveInventory,
            overshoot_earlier,
            std::time::Instant
        );
        field!(
            PreflightPrimitiveInventory,
            overshoot_duration,
            std::time::Duration
        );
        field!(
            PreflightPrimitiveInventory,
            micros_duration,
            std::time::Duration
        );
        field!(PreflightPrimitiveInventory, micros_u128, u128);
        field!(PreflightPrimitiveInventory, micros_conversion, Result<u64, std::num::TryFromIntError>);
        field!(PreflightPrimitiveInventory, elapsed_return, u64);
        field!(PreflightPrimitiveInventory, overshoot_return, u64);
        field!(
            PreflightEnlargeInventory,
            enlarge_self,
            &'static mut RuntimeControl
        );
        field!(PreflightEnlargeInventory, enlarge_bytes, usize);
        field!(PreflightEnlargeInventory, enlarge_cursor, Cursor);
        field!(PreflightEnlargeInventory, old, usize);
        field!(
            PreflightEnlargeInventory,
            construction_option_receiver,
            &'static Option<ReservationTicket>
        );
        field!(
            PreflightEnlargeInventory,
            construction_option_return,
            Option<&'static ReservationTicket>
        );
        field!(
            PreflightEnlargeInventory,
            map_ticket,
            &'static ReservationTicket
        );
        field!(PreflightEnlargeInventory, map_bytes, usize);
        field!(PreflightEnlargeInventory, map_option, Option<usize>);
        field!(
            PreflightEnlargeInventory,
            old_option_receiver,
            Option<usize>
        );
        field!(
            PreflightEnlargeInventory,
            missing_closure_control,
            &'static mut &'static mut RuntimeControl
        );
        field!(
            PreflightEnlargeInventory,
            missing_closure_cursor,
            &'static Cursor
        );
        field!(
            PreflightEnlargeInventory,
            missing_closure_wasi,
            &'static Option<WasiUsage>
        );
        field!(
            PreflightEnlargeInventory,
            check_self,
            &'static mut RuntimeControl
        );
        field!(PreflightEnlargeInventory, check_cursor, Cursor);
        field!(
            PreflightEnlargeInventory,
            cancel_self,
            &'static crate::Cancellation
        );
        field!(PreflightEnlargeInventory, cancelled, bool);
        field!(PreflightEnlargeInventory, check_now, std::time::Instant);
        field!(
            PreflightEnlargeInventory,
            check_left,
            &'static std::time::Instant
        );
        field!(
            PreflightEnlargeInventory,
            check_right,
            &'static std::time::Instant
        );
        field!(PreflightEnlargeInventory, expired, bool);
        field!(
            PreflightEnlargeInventory,
            bytes_self,
            &'static mut RuntimeControl
        );
        field!(
            PreflightEnlargeInventory,
            bytes_category,
            SwiftReservationCategory
        );
        field!(PreflightEnlargeInventory, bytes_amount, usize);
        field!(PreflightEnlargeInventory, bytes_cursor, Cursor);
        field!(PreflightEnlargeInventory, category_next, Option<usize>);
        field!(PreflightEnlargeInventory, category_limit, usize);
        field!(PreflightEnlargeInventory, combined_next, Option<usize>);
        field!(
            PreflightEnlargeInventory,
            category_kind,
            SwiftRunFailureKind
        );
        field!(
            PreflightEnlargeInventory,
            limit_self,
            &'static RuntimeControl
        );
        field!(
            PreflightEnlargeInventory,
            limit_category,
            SwiftReservationCategory
        );
        field!(PreflightEnlargeInventory, limit_return, usize);
        field!(
            PreflightEnlargeInventory,
            category_self,
            &'static SwiftReservations
        );
        field!(
            PreflightEnlargeInventory,
            category_argument,
            SwiftReservationCategory
        );
        field!(
            PreflightEnlargeInventory,
            category_return,
            &'static SwiftReservationUsage
        );
        field!(
            PreflightEnlargeInventory,
            category_predicate_limit,
            &'static usize
        );
        field!(PreflightEnlargeInventory, category_predicate_n, usize);
        field!(
            PreflightEnlargeInventory,
            category_predicate_option,
            Option<usize>
        );
        field!(
            PreflightEnlargeInventory,
            combined_predicate_limit,
            &'static usize
        );
        field!(PreflightEnlargeInventory, combined_predicate_n, usize);
        field!(
            PreflightEnlargeInventory,
            combined_predicate_option,
            Option<usize>
        );
        field!(PreflightEnlargeInventory, map_or_default, u64);
        field!(PreflightEnlargeInventory, map_or_n, usize);
        field!(PreflightEnlargeInventory, map_or_return, u64);
        field!(PreflightEnlargeInventory, map_or_option, Option<usize>);
        field!(PreflightEnlargeInventory, limit_fault, Fault);
        field!(PreflightEnlargeInventory, limit_resource, SwiftRunResource);
        field!(PreflightEnlargeInventory, limit_attempted, u64);
        field!(PreflightEnlargeInventory, limit_ceiling, u64);
        field!(PreflightEnlargeInventory, next_category, usize);
        field!(PreflightEnlargeInventory, next_combined, usize);
        field!(PreflightEnlargeInventory, next_pair, (usize, usize));
        field!(
            PreflightEnlargeInventory,
            commit_self,
            &'static mut RuntimeControl
        );
        field!(
            PreflightEnlargeInventory,
            commit_category,
            SwiftReservationCategory
        );
        field!(PreflightEnlargeInventory, commit_category_next, usize);
        field!(PreflightEnlargeInventory, commit_combined_next, usize);
        field!(
            PreflightEnlargeInventory,
            category_mut_self,
            &'static mut SwiftReservations
        );
        field!(
            PreflightEnlargeInventory,
            category_mut_argument,
            SwiftReservationCategory
        );
        field!(
            PreflightEnlargeInventory,
            category_mut_return,
            &'static mut SwiftReservationUsage
        );
        field!(
            PreflightEnlargeInventory,
            construction_mut_option,
            Option<&'static mut ReservationTicket>
        );
        field!(
            PreflightEnlargeInventory,
            construction_mut_ticket,
            &'static mut ReservationTicket
        );
        field!(
            RootAdmissionExtraInventory,
            admit_self,
            &'static mut RuntimeControl
        );
        field!(
            RootAdmissionExtraInventory,
            admit_category,
            SwiftReservationCategory
        );
        field!(RootAdmissionExtraInventory, admit_bytes, usize);
        field!(RootAdmissionExtraInventory, admit_cursor, Cursor);
        field!(
            RootAdmissionExtraInventory,
            entry_self,
            &'static mut RuntimeControl
        );
        field!(RootAdmissionExtraInventory, entry_bytes, usize);
        field!(RootAdmissionExtraInventory, entry_cursor, Cursor);
        field!(RootAdmissionExtraInventory, ticket_count, usize);
        field!(RootAdmissionExtraInventory, ticket_attempted, u64);
        field!(RootAdmissionExtraInventory, entry_limit, usize);
        field!(
            RootAdmissionBoundaryInventory,
            bytes_and_check,
            PreflightEnlargeInventory
        );
        field!(
            RootAdmissionBoundaryInventory,
            primitive,
            PreflightPrimitiveInventory
        );
        field!(
            RootAdmissionBoundaryInventory,
            entry_and_ticket,
            RootAdmissionExtraInventory
        );
        field!(RootOwnerBoundaryInventory, owner, PreflightOwnerInventory);
        field!(
            RootOwnerBoundaryInventory,
            primitive,
            PreflightPrimitiveInventory
        );
        field!(
            RootWorkLiveInventory,
            work_self,
            &'static mut RuntimeControl
        );
        field!(RootWorkLiveInventory, component, Work);
        field!(RootWorkLiveInventory, credits, u64);
        field!(RootWorkLiveInventory, work_cursor, Cursor);
        field!(RootWorkLiveInventory, used, u64);
        field!(RootWorkLiveInventory, work_limit, u64);
        field!(RootWorkLiveInventory, work_resource, SwiftRunResource);
        field!(
            RootWorkLiveInventory,
            work_tuple,
            (u64, u64, SwiftRunResource)
        );
        field!(RootWorkLiveInventory, work_next, Option<u64>);
        field!(RootWorkLiveInventory, work_filter_input, Option<u64>);
        field!(RootWorkLiveInventory, work_filter_output, Option<u64>);
        field!(RootWorkLiveInventory, work_pattern, u64);
        field!(RootWorkLiveInventory, work_filter_limit, &'static u64);
        field!(RootWorkLiveInventory, work_filter_value, &'static u64);
        field!(RootWorkLiveInventory, add_self, &'static mut RuntimeControl);
        field!(RootWorkLiveInventory, add_resource, Live);
        field!(RootWorkLiveInventory, add_amount, usize);
        field!(RootWorkLiveInventory, add_cursor, Cursor);
        field!(
            RootWorkLiveInventory,
            live_parts_self,
            &'static RuntimeControl
        );
        field!(RootWorkLiveInventory, live_parts_resource, Live);
        field!(
            RootWorkLiveInventory,
            live_tuple,
            (
                SwiftReservationUsage,
                usize,
                SwiftRunResource,
                SwiftRunFailureKind,
            )
        );
        field!(RootWorkLiveInventory, live_usage, SwiftReservationUsage);
        field!(RootWorkLiveInventory, live_limit, usize);
        field!(RootWorkLiveInventory, live_diagnostic, SwiftRunResource);
        field!(RootWorkLiveInventory, live_kind, SwiftRunFailureKind);
        field!(RootWorkLiveInventory, live_next, Option<usize>);
        field!(RootWorkLiveInventory, live_filter_input, Option<usize>);
        field!(RootWorkLiveInventory, live_filter_output, Option<usize>);
        field!(RootWorkLiveInventory, live_pattern, usize);
        field!(RootWorkLiveInventory, live_filter_limit, &'static usize);
        field!(RootWorkLiveInventory, live_filter_value, &'static usize);
        field!(RootWorkLiveInventory, live_map_or_input, Option<usize>);
        field!(RootWorkLiveInventory, live_map_or_value, usize);
        field!(RootWorkLiveInventory, live_map_or_return, u64);
        field!(
            RootWorkLiveInventory,
            live_mut_self,
            &'static mut RuntimeControl
        );
        field!(RootWorkLiveInventory, live_mut_resource, Live);
        field!(
            RootWorkLiveInventory,
            live_mut_return,
            &'static mut SwiftReservationUsage
        );
        field!(
            RootWorkLiveInventory,
            live_usage_borrow,
            &'static mut SwiftReservationUsage
        );
        field!(
            RootWorkLiveInventory,
            remove_self,
            &'static mut RuntimeControl
        );
        field!(RootWorkLiveInventory, remove_resource, Live);
        field!(RootWorkLiveInventory, remove_amount, usize);
        field!(
            RootWorkLiveInventory,
            remove_tuple,
            (
                SwiftReservationUsage,
                usize,
                SwiftRunResource,
                SwiftRunFailureKind,
            )
        );
        field!(RootWorkLiveInventory, remove_usage, SwiftReservationUsage);
        field!(RootWorkLiveInventory, remove_next, Option<usize>);
        field!(RootWorkLiveInventory, remove_pattern, usize);
        field!(
            RootWorkLiveInventory,
            exact_self,
            &'static mut RuntimeControl
        );
        field!(RootWorkLiveInventory, requested, usize);
        field!(RootWorkLiveInventory, observed, usize);
        field!(RootWorkLiveInventory, exact_cursor, Cursor);
        field!(RootWorkLiveInventory, exact_fault, Fault);
        field!(RootWorkLiveInventory, observed_option, Option<usize>);
        field!(
            RootWorkLiveBoundaryInventory,
            work_live_exact,
            RootWorkLiveInventory
        );
        field!(
            RootWorkLiveBoundaryInventory,
            check,
            PreflightEnlargeInventory
        );
        field!(
            RootWorkLiveBoundaryInventory,
            primitive,
            PreflightPrimitiveInventory
        );
        field!(
            RootRemoveLiveInventory,
            remove_self,
            &'static mut RuntimeControl
        );
        field!(RootRemoveLiveInventory, remove_resource, Live);
        field!(RootRemoveLiveInventory, remove_amount, usize);
        field!(
            RootRemoveLiveInventory,
            live_parts_self,
            &'static RuntimeControl
        );
        field!(RootRemoveLiveInventory, live_parts_resource, Live);
        field!(
            RootRemoveLiveInventory,
            live_tuple,
            (
                SwiftReservationUsage,
                usize,
                SwiftRunResource,
                SwiftRunFailureKind,
            )
        );
        field!(RootRemoveLiveInventory, usage, SwiftReservationUsage);
        field!(RootRemoveLiveInventory, next, Option<usize>);
        field!(RootRemoveLiveInventory, next_pattern, usize);
        field!(
            RootRemoveLiveInventory,
            live_mut_self,
            &'static mut RuntimeControl
        );
        field!(RootRemoveLiveInventory, live_mut_resource, Live);
        field!(
            RootRemoveLiveInventory,
            live_mut_return,
            &'static mut SwiftReservationUsage
        );
        field!(
            RootRemoveLiveInventory,
            cleanup_fault_self,
            &'static mut RuntimeControl
        );
        field!(
            RootRemoveLiveInventory,
            cleanup_invariant,
            SwiftCleanupInvariant
        );
        field!(RootRemoveLiveInventory, cleanup_code, &'static str);
        field!(RootRemoveLiveInventory, cleanup_cursor, Cursor);
        field!(
            RootRemoveLiveInventory,
            insert_receiver,
            &'static mut Option<SwiftCleanupInvariant>
        );
        field!(
            RootRemoveLiveInventory,
            insert_argument,
            SwiftCleanupInvariant
        );
        field!(
            RootRemoveLiveInventory,
            inserted,
            &'static mut SwiftCleanupInvariant
        );
        field!(
            RootRemoveLiveBoundaryInventory,
            remove_and_cleanup_fault,
            RootRemoveLiveInventory
        );
        field!(
            RootRemoveLiveBoundaryInventory,
            primitive,
            PreflightPrimitiveInventory
        );
        field!(RootRefundInventory, drop_self, &'static mut RuntimeControl);
        field!(
            RootRefundInventory,
            refund_self,
            &'static mut RuntimeControl
        );
        field!(RootRefundInventory, category, Option<usize>);
        field!(RootRefundInventory, combined, Option<usize>);
        field!(RootRefundInventory, count, Option<usize>);
        field!(
            RootRefundInventory,
            option_match,
            (Option<usize>, Option<usize>, Option<usize>)
        );
        field!(RootRefundInventory, category_pattern, usize);
        field!(RootRefundInventory, combined_pattern, usize);
        field!(RootRefundInventory, count_pattern, usize);
        field!(
            RootRefundInventory,
            category_self,
            &'static SwiftReservations
        );
        field!(
            RootRefundInventory,
            category_argument,
            SwiftReservationCategory
        );
        field!(
            RootRefundInventory,
            category_return,
            &'static SwiftReservationUsage
        );
        field!(
            RootRefundInventory,
            category_mut_self,
            &'static mut SwiftReservations
        );
        field!(
            RootRefundInventory,
            category_mut_argument,
            SwiftReservationCategory
        );
        field!(
            RootRefundInventory,
            category_mut_return,
            &'static mut SwiftReservationUsage
        );
        field!(
            RootRefundInventory,
            cleanup_fault_self,
            &'static mut RuntimeControl
        );
        field!(
            RootRefundInventory,
            cleanup_invariant,
            SwiftCleanupInvariant
        );
        field!(RootRefundInventory, cleanup_code, &'static str);
        field!(RootRefundInventory, cleanup_cursor, Cursor);
        field!(
            RootRefundInventory,
            insert_receiver,
            &'static mut Option<SwiftCleanupInvariant>
        );
        field!(RootRefundInventory, insert_argument, SwiftCleanupInvariant);
        field!(
            RootRefundInventory,
            inserted,
            &'static mut SwiftCleanupInvariant
        );
        field!(
            RootRefundInventory,
            record_self,
            &'static mut RuntimeControl
        );
        field!(
            RootRefundInventory,
            record_failure,
            &'static mut SwiftRunFailure
        );
        field!(
            RootRefundInventory,
            record_failure_option,
            Option<&'static mut SwiftRunFailure>
        );
        field!(
            RootRefundInventory,
            complete_outcome,
            &'static mut Option<SwiftRunFailure>
        );
        field!(RootPhaseEndInventory, end_self, &'static mut RuntimeControl);
        field!(RootPhaseEndInventory, end_bytes, usize);
        field!(
            RootPhaseEndInventory,
            construction_receiver,
            &'static Option<ReservationTicket>
        );
        field!(
            RootPhaseEndInventory,
            construction_return,
            Option<&'static ReservationTicket>
        );
        field!(
            RootPhaseEndInventory,
            construction_ticket,
            &'static ReservationTicket
        );
        field!(RootPhaseEndInventory, floor, usize);
        field!(RootPhaseEndInventory, difference, usize);
        field!(RootPhaseEndInventory, category, Option<usize>);
        field!(RootPhaseEndInventory, combined, Option<usize>);
        field!(
            RootPhaseEndInventory,
            option_match,
            (Option<usize>, Option<usize>)
        );
        field!(RootPhaseEndInventory, category_pattern, usize);
        field!(RootPhaseEndInventory, combined_pattern, usize);
        field!(
            RootPhaseEndInventory,
            construction_mut_option,
            Option<&'static mut ReservationTicket>
        );
        field!(
            RootPhaseEndInventory,
            construction_mut_ticket,
            &'static mut ReservationTicket
        );
        field!(RootPhaseEndInventory, foundation_items, [(usize, usize); 7]);
        field!(RootPhaseEndInventory, foundation_iterator, std::array::IntoIter<(usize, usize), 7>);
        field!(RootPhaseEndInventory, foundation_sum, usize);
        field!(RootPhaseEndInventory, foundation_count, usize);
        field!(RootPhaseEndInventory, foundation_bytes, usize);
        field!(RootPhaseEndInventory, foundation_product, Option<usize>);
        field!(RootPhaseEndInventory, foundation_next, Option<usize>);
        field!(RootRefundBoundaryInventory, refund, RootRefundInventory);
        field!(
            RootRefundBoundaryInventory,
            phase_end,
            RootPhaseEndInventory
        );
        field!(
            RootRefundBoundaryInventory,
            primitive,
            PreflightPrimitiveInventory
        );
        field!(
            CompletionBorrowInventory,
            returned_parts,
            CleanupCompletionParts<'static>
        );
        field!(
            CompletionBorrowInventory,
            outcome,
            &'static mut Option<SwiftRunFailure>
        );
        field!(
            CompletionBorrowInventory,
            phase_control,
            &'static mut RuntimeControl
        );
        field!(
            CompletionBorrowInventory,
            phase_wasi,
            Option<&'static AccountedWasi>
        );
        field!(CompletionBorrowInventory, phase_previous, usize);
        field!(
            CompletionBorrowInventory,
            construction_phase,
            CacheConstructionPhase<'static>
        );
        field!(
            CompletionBorrowInventory,
            operation_phase,
            CacheOperationPhase<'static>
        );
        field!(PreflightGroupA, layout_fault, Fault);
        field!(PreflightGroupA, result, Result<PreparedBounds, SwiftRunFailure>);
        field!(PreflightGroupA, observation, Option<WasiUsage>);
        field!(PreflightGroupA, cursor, Cursor);
        field!(PreflightGroupA, control, &'static mut RuntimeControl);
        field!(PreflightGroupA, wasi, Option<&'static AccountedWasi>);
        field!(PreflightGroupA, adopted, Option<&'static AdoptedProof>);
        field!(PreflightGroupA, cache, Option<&'static SwiftFunctionCache>);
        field!(PreflightGroupA, previous, usize);
        field!(PreflightGroupA, enlarged, usize);
        field!(PreflightGroupB, function_return_option, Option<usize>);
        field!(PreflightGroupB, and_then_receiver, Option<usize>);
        field!(PreflightGroupB, and_then_return, Option<usize>);
        field!(PreflightGroupB, ok_or_receiver, Option<usize>);
        field!(PreflightGroupB, return_transfer, Result<PreparedBounds, SwiftRunFailure>);
        field!(PreflightGroupB, usage_return, SwiftRunUsage);
        println!(
            "cache offsets adopted={} slots={} pins={} patches={} buffers={} header={}",
            offset_of!(SwiftFunctionCache, adopted),
            offset_of!(SwiftFunctionCache, slots),
            offset_of!(SwiftFunctionCache, pins),
            offset_of!(SwiftFunctionCache, patches),
            offset_of!(SwiftFunctionCache, buffers),
            offset_of!(SwiftFunctionCache, header)
        );
        println!(
            "bounds cleanup={} header={} construction={} operation={} foundation={}",
            cache_cleanup_temporary_bytes().unwrap(),
            cache_header_bytes().unwrap(),
            cache_construction_bytes().unwrap(),
            cache_operation_bytes().unwrap(),
            foundation_construction_bytes().unwrap()
        );
    }
}
