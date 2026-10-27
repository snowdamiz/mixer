//! Foundation for the Swift-only runtime. No cache, executor or WASI dispatch is
//! selected by this module. All authority below is crate-private and sealed by
//! an actual complete-validation proof.
#![allow(dead_code)] // Staged private seams are used by later bounded slices.
#![allow(clippy::result_large_err)] // Failure reporting must not allocate.

use super::{SwiftValidationUsage, ValidatedSwiftReactor};
use crate::experimental_wasi::{WasiBudget, WasiFailure, WasiUsage};
use crate::Cancellation;
use std::mem::size_of;
use super::retained_profile_loader_v1::{AdoptionBodyV1, LoaderProvenanceV1};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

const MIB: usize = 1024 * 1024;
pub(crate) const MAX_RESERVATION_TICKETS: usize = 86;
static NEXT_OWNER: AtomicU64 = AtomicU64::new(1);

/// Every field independently narrows the fixed experimental envelope. Zero is
/// an exhausted limit. Neither validation grammar nor the sealed ABI is changed.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftRunBudget {
    pub source_bytes: usize,
    pub metadata_bytes: usize,
    pub cache_bytes: usize,
    pub cache_entry_bytes: usize,
    pub cache_entries: usize,
    pub active_pins: usize,
    pub cache_work: u64,
    pub frames: usize,
    pub values: usize,
    pub controls: usize,
    pub memory_pages: u32,
    pub state_bytes: usize,
    pub combined_bytes: usize,
    pub instruction_fuel: u64,
    pub execution_work: u64,
    pub host_calls: u64,
    pub deadline_ms: u64,
}
impl Default for SwiftRunBudget {
    fn default() -> Self {
        Self {
            source_bytes: 64 * MIB,
            metadata_bytes: 16 * MIB,
            cache_bytes: 16 * MIB,
            cache_entry_bytes: 8 * MIB,
            cache_entries: 64,
            active_pins: 64,
            cache_work: 64_000_000,
            frames: 64,
            values: 16_384,
            controls: 4_096,
            memory_pages: 768,
            state_bytes: 128 * MIB,
            combined_bytes: 256 * MIB,
            instruction_fuel: 100_000_000,
            execution_work: 1_000_000_000,
            host_calls: 32_768,
            deadline_ms: 30_000,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftReservationCategory {
    RetainedSource,
    RetainedMetadata,
    Cache,
    State,
    Wasi,
    Shared,
    Construction,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftReservationUsage {
    pub current: usize,
    pub peak: usize,
}
/// Logical requested capacity and explicitly modelled headers; excludes allocator
/// overhead and is never an RSS or compiler-stack measurement.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftReservations {
    pub retained_source: SwiftReservationUsage,
    pub retained_metadata: SwiftReservationUsage,
    pub cache: SwiftReservationUsage,
    pub state: SwiftReservationUsage,
    pub wasi: SwiftReservationUsage,
    pub shared: SwiftReservationUsage,
    pub construction: SwiftReservationUsage,
    pub combined: SwiftReservationUsage,
    pub live_tickets: usize,
    pub peak_tickets: usize,
}
impl SwiftReservations {
    fn category(&self, category: SwiftReservationCategory) -> &SwiftReservationUsage {
        match category {
            SwiftReservationCategory::RetainedSource => &self.retained_source,
            SwiftReservationCategory::RetainedMetadata => &self.retained_metadata,
            SwiftReservationCategory::Cache => &self.cache,
            SwiftReservationCategory::State => &self.state,
            SwiftReservationCategory::Wasi => &self.wasi,
            SwiftReservationCategory::Shared => &self.shared,
            SwiftReservationCategory::Construction => &self.construction,
        }
    }
    fn category_mut(&mut self, category: SwiftReservationCategory) -> &mut SwiftReservationUsage {
        match category {
            SwiftReservationCategory::RetainedSource => &mut self.retained_source,
            SwiftReservationCategory::RetainedMetadata => &mut self.retained_metadata,
            SwiftReservationCategory::Cache => &mut self.cache,
            SwiftReservationCategory::State => &mut self.state,
            SwiftReservationCategory::Wasi => &mut self.wasi,
            SwiftReservationCategory::Shared => &mut self.shared,
            SwiftReservationCategory::Construction => &mut self.construction,
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftDeadlineOrigin {
    Run,
    Wasi,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftRunStage {
    Adoption,
    Cache,
    Initialization,
    Invocation,
    Wasi,
    Cleanup,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftRunResource {
    Reservation(SwiftReservationCategory),
    Combined,
    CacheEntryBytes,
    CacheEntries,
    ActivePins,
    Frames,
    Values,
    Controls,
    MemoryPages,
    CacheWork,
    ExecutionWork,
    InstructionFuel,
    HostCalls,
    Deadline,
    TicketInventory,
    OwnerIdentity,
    ExactCapacity,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftRunFailureKind {
    InvalidBudget,
    Cancelled,
    Deadline,
    Allocation,
    Adoption,
    CategoryExhausted,
    CombinedExhausted,
    ResourceExhausted,
    FuelExhausted,
    WorkExhausted,
    HostCallLimit,
    PinLimit,
    FrameLimit,
    ValueLimit,
    ControlLimit,
    DecoderMismatch,
    UnsupportedEnvironment,
    GuestTrap,
    GuestExit,
    Wasi,
    Invariant,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftCleanupInvariant {
    ReservationOwner,
    ReservationUnderflow,
    MissingConstruction,
    ConstructionBound,
    LiveUnderflow,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftLiveUsage {
    pub cache_entries: SwiftReservationUsage,
    pub active_pins: SwiftReservationUsage,
    pub frames: SwiftReservationUsage,
    pub values: SwiftReservationUsage,
    pub controls: SwiftReservationUsage,
    pub memory_pages: SwiftReservationUsage,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftRunUsage {
    pub reservations: SwiftReservations,
    pub live: SwiftLiveUsage,
    pub cache_work: u64,
    pub execution_work: u64,
    pub instruction_fuel: u64,
    pub instructions: u64,
    pub host_calls: u64,
    /// Independent cleanup observation; never replaces the first terminal cause.
    pub cleanup_invariant: Option<SwiftCleanupInvariant>,
    pub elapsed_micros: u64,
    pub deadline_ms: u64,
    pub deadline_origin: SwiftDeadlineOrigin,
    pub deadline_overshoot_micros: u64,
    /// Historical validation observations, never added to runtime admission.
    pub validation: SwiftValidationUsage,
    /// Copied observation only. None means no context observation was supplied;
    /// no field in this snapshot is consulted for admission by RuntimeControl.
    pub wasi: Option<WasiUsage>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftRunFailure {
    pub stage: SwiftRunStage,
    pub kind: SwiftRunFailureKind,
    pub code: &'static str,
    pub function: Option<u32>,
    pub offset: Option<usize>,
    pub resource: Option<SwiftRunResource>,
    pub attempted: u64,
    pub limit: u64,
    pub observed_capacity: Option<usize>,
    pub deadline_origin: SwiftDeadlineOrigin,
    pub wasi_failure: Option<WasiFailure>,
    pub guest_exit: Option<u32>,
    pub at_failure: SwiftRunUsage,
    pub after_cleanup: Option<SwiftRunUsage>,
}
impl std::fmt::Display for SwiftRunFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at {:?}", self.code, self.offset)
    }
}
impl std::error::Error for SwiftRunFailure {}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Cursor {
    pub stage: SwiftRunStage,
    pub function: Option<u32>,
    pub offset: Option<usize>,
}
impl Cursor {
    pub(crate) const fn adoption() -> Self {
        Self {
            stage: SwiftRunStage::Adoption,
            function: None,
            offset: None,
        }
    }
}
#[derive(Clone, Copy)]
pub(crate) struct Fault {
    pub kind: SwiftRunFailureKind,
    pub code: &'static str,
    pub resource: Option<SwiftRunResource>,
    pub attempted: u64,
    pub limit: u64,
    pub observed_capacity: Option<usize>,
    pub wasi_failure: Option<WasiFailure>,
    pub guest_exit: Option<u32>,
}
impl Fault {
    pub(crate) fn new(kind: SwiftRunFailureKind, code: &'static str) -> Self {
        Self {
            kind,
            code,
            resource: None,
            attempted: 0,
            limit: 0,
            observed_capacity: None,
            wasi_failure: None,
            guest_exit: None,
        }
    }
    fn limit(mut self, resource: SwiftRunResource, attempted: u64, limit: u64) -> Self {
        self.resource = Some(resource);
        self.attempted = attempted;
        self.limit = limit;
        self
    }
}

/// Inline, non-Clone ownership. Forgetting a ticket retains the charge. No
/// pointer, borrow of the ledger, heap registry, or ticket per cache pin exists.
#[derive(Debug)]
pub(crate) struct ReservationTicket {
    owner: u64,
    category: SwiftReservationCategory,
    bytes: usize,
}
impl ReservationTicket {
    /// Read-only layout evidence. The original owner check remains mandatory;
    /// this comparison grants no authority to debit, refund or repair a ledger.
    pub(crate) fn matches_layout(&self, category: SwiftReservationCategory, bytes: usize) -> bool {
        self.category == category && self.bytes == bytes
    }
}

#[cfg(test)]
impl RuntimeControl {
    /// Derived boundary fault injection only. Returns the actual replaced
    /// authority; fixtures must restore it before consuming owner cleanup.
    pub(crate) fn test_replace_construction(
        &mut self,
        ticket: Option<ReservationTicket>,
    ) -> Option<ReservationTicket> {
        std::mem::replace(&mut self.construction, ticket)
    }
    /// Temporarily narrow one actual live budget, then restore the returned
    /// scalar. Never changes live usage or repairs a cleanup mismatch.
    pub(crate) fn test_replace_live_limit(&mut self, resource: Live, ceiling: usize) -> usize {
        let destination = match resource {
            Live::Values => &mut self.budget.values,
            Live::Controls => &mut self.budget.controls,
            Live::Frames => &mut self.budget.frames,
            Live::ActivePins => &mut self.budget.active_pins,
            _ => panic!("unsupported boundary fixture"),
        };
        std::mem::replace(destination, ceiling)
    }
    pub(crate) fn test_replace_combined_limit(&mut self, ceiling: usize) -> usize {
        std::mem::replace(&mut self.budget.combined_bytes, ceiling)
    }
    pub(crate) fn test_replace_state_limit(&mut self, ceiling: usize) -> usize {
        std::mem::replace(&mut self.budget.state_bytes, ceiling)
    }
    pub(crate) fn test_replace_execution_work_limit(&mut self, ceiling: u64) -> u64 {
        std::mem::replace(&mut self.budget.execution_work, ceiling)
    }
    /// Expire a healthy prepared fixture without racing its construction time.
    /// Keep its actual origin, budgets, counters and first-failure state intact.
    pub(crate) fn test_expire_deadline(&mut self) -> Instant {
        assert!(self.first_failure.is_none());
        let expired = Instant::now();
        assert!(expired < self.deadline);
        self.deadline = expired;
        expired
    }
}
/// The actual proof moves with both adopted tickets. This does not modify the
/// sealed proof's layout or manufacture independently executable authority.
pub(crate) struct AdoptedProof {
    body: AdoptionBodyV1,
    source: ReservationTicket,
    metadata: ReservationTicket,
}
impl AdoptedProof {
    pub(crate) fn proof(&self) -> &ValidatedSwiftReactor {
        self.body.proof()
    }
    pub(super) fn selected_provenance(&self) -> Option<&LoaderProvenanceV1> {
        self.body.selected_provenance()
    }
}
#[derive(Clone, Copy, Debug)]
pub(crate) enum Work {
    Cache,
    Execution,
}
#[derive(Clone, Copy, Debug)]
pub(crate) enum Live {
    CacheEntries,
    ActivePins,
    Frames,
    Values,
    Controls,
    MemoryPages,
}

// New source-authored destruction/refund places. Foundation retains this floor
// until all authentic body/proof owners are destroyed. Not physical stack/RSS.
#[allow(dead_code)]
struct AdoptionCleanupPlacesV1 {
    adopted_argument: AdoptedProof,
    body_pattern: AdoptionBodyV1,
    body_drop_argument: AdoptionBodyV1,
    source_pattern: ReservationTicket,
    metadata_pattern: ReservationTicket,
    observation: Option<WasiUsage>,
    source_result: Result<(), SwiftRunFailure>,
    metadata_result: Result<(), SwiftRunFailure>,
    combined_return: Result<(), SwiftRunFailure>,
    refused_body_drop: AdoptionBodyV1,
    refused_source: Option<ReservationTicket>,
    refused_metadata: Option<ReservationTicket>,
    refused_ticket_patterns: [ReservationTicket; 2],
    refused_refund_results: [Result<(), SwiftRunFailure>; 2],
    failure_pattern: SwiftRunFailure,
    cleanup_return: SwiftRunUsage,
    cleanup_some: Option<SwiftRunUsage>,
    receiver_borrows: [&'static mut RuntimeControl; 5],
}
pub(super) const ADOPTION_CLEANUP_BYTES_V1: usize = size_of::<AdoptionCleanupPlacesV1>();
pub(super) const ADOPTION_CLEANUP_ALIGNMENT_V1: usize = std::mem::align_of::<AdoptionCleanupPlacesV1>();

/// The sole runtime admission authority. All fields and tickets are inline.
/// WASI retains sole ownership of its existing active counters and budgets.
pub(crate) struct RuntimeControl {
    owner: u64,
    budget: SwiftRunBudget,
    started: Instant,
    deadline: Instant,
    deadline_origin: SwiftDeadlineOrigin,
    cancellation: Cancellation,
    validation: SwiftValidationUsage,
    reservations: SwiftReservations,
    live: SwiftLiveUsage,
    cache_work: u64,
    execution_work: u64,
    instruction_fuel: u64,
    instructions: u64,
    host_calls: u64,
    cleanup_invariant: Option<SwiftCleanupInvariant>,
    first_failure: Option<SwiftRunFailure>,
    control_header: Option<ReservationTicket>,
    cancellation_backing: Option<ReservationTicket>,
    construction: Option<ReservationTicket>,
}

// Final cleanup has no cache/WASI/execution owner envelope after its header is
// refunded. These never-instantiated inventories name its surviving output borrows
// and directly authored refund/record/finish operation and return roles. Existing
// diagnostic, control, ticket and optional-WASI classes remain disjoint below.
// See docs/swift-final-boundary-accounting.md for the source-role map and whole
// phase switch: refund ends, then record ends, then finish consumes control.
// Opaque standard-library frames and compiler-generated spills are not modelled.
#[allow(dead_code)]
struct FinalOutputBorrows {
    outcome: &'static mut Option<SwiftRunFailure>,
    usage: &'static mut Option<SwiftRunUsage>,
}
#[allow(dead_code)]
struct FinalClockInventory {
    usage_receiver: &'static RuntimeControl,
    usage_now: Instant,
    elapsed_receiver: &'static Instant,
    elapsed_earlier: Instant,
    elapsed_duration: Duration,
    overshoot_receiver: &'static Instant,
    overshoot_earlier: Instant,
    overshoot_duration: Duration,
    micros_duration: Duration,
    as_micros_receiver: &'static Duration,
    micros_u128: u128,
    try_from_input: u128,
    try_from_output: Result<u64, std::num::TryFromIntError>,
    unwrap_input: Result<u64, std::num::TryFromIntError>,
    unwrap_default: u64,
    micros_return: u64,
    elapsed_return: u64,
    overshoot_return: u64,
}
#[allow(dead_code)]
struct FinalFaultInventory {
    cleanup_receiver: &'static mut RuntimeControl,
    invariant: SwiftCleanupInvariant,
    code: &'static str,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    insert_result: &'static mut SwiftCleanupInvariant,
    cursor_source: Cursor,
    fault_kind: SwiftRunFailureKind,
    fault_code: &'static str,
    fault_source: Fault,
    fail_receiver: &'static mut RuntimeControl,
    cursor_transfer: Cursor,
    fault_transfer: Fault,
}
#[allow(dead_code)]
struct FinalCategoryInventory {
    category_receiver: &'static SwiftReservations,
    category_argument: SwiftReservationCategory,
    category_return: &'static SwiftReservationUsage,
    category_mut_receiver: &'static mut SwiftReservations,
    category_mut_argument: SwiftReservationCategory,
    category_mut_return: &'static mut SwiftReservationUsage,
}
#[allow(dead_code)]
struct FinalRefundInventory {
    outputs: FinalOutputBorrows,
    header_take_receiver: &'static mut Option<ReservationTicket>,
    drop_receiver: &'static mut RuntimeControl,
    refund_receiver: &'static mut RuntimeControl,
    category: Option<usize>,
    combined: Option<usize>,
    count: Option<usize>,
    option_match: (Option<usize>, Option<usize>, Option<usize>),
    category_pattern: usize,
    combined_pattern: usize,
    count_pattern: usize,
    categories: FinalCategoryInventory,
    fault: FinalFaultInventory,
    clock: FinalClockInventory,
}
#[allow(dead_code)]
struct FinalRecordInventory {
    outputs: FinalOutputBorrows,
    record_receiver: &'static mut RuntimeControl,
    failure_option_receiver: &'static mut Option<SwiftRunFailure>,
    failure_pattern: &'static mut SwiftRunFailure,
    clock: FinalClockInventory,
}
#[allow(dead_code)]
struct FinalFinishInventory {
    outputs: FinalOutputBorrows,
    started: Instant,
    deadline: Instant,
    control_take_receiver: &'static mut Option<ReservationTicket>,
    cancel_take_receiver: &'static mut Option<ReservationTicket>,
    construction_take_receiver: &'static mut Option<ReservationTicket>,
    array: [Option<ReservationTicket>; 3],
    into_tickets: std::array::IntoIter<Option<ReservationTicket>, 3>,
    flatten_tickets: std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>, 3>>,
    flatten_receiver:
        &'static mut std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>, 3>>,
    iterator_next: Option<ReservationTicket>,
    category: Option<usize>,
    combined: Option<usize>,
    count: Option<usize>,
    option_match: (Option<usize>, Option<usize>, Option<usize>),
    category_pattern: usize,
    combined_pattern: usize,
    count_pattern: usize,
    categories: FinalCategoryInventory,
    ticket_bytes_some: Option<usize>,
    formula_return: Option<usize>,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    insert_return: &'static mut SwiftCleanupInvariant,
    clock: FinalClockInventory,
    now: Instant,
}

pub(super) const FOUNDATION_FINAL_BOUNDARY_BYTES: usize = {
    let refund = size_of::<FinalRefundInventory>();
    let record = size_of::<FinalRecordInventory>();
    let finish = size_of::<FinalFinishInventory>();
    let first = if refund > record { refund } else { record };
    if first > finish {
        first
    } else {
        finish
    }
};

// All array/loop/closure metadata computation occurs in this const initializer.
// The public spelling remains a function that copies the precomputed Option.
// No runtime temporary array, IntoIter or try_fold is created by this formula.
const FOUNDATION_CONSTRUCTION_BYTES: Option<usize> = {
    let terms: [(usize, usize); 13] = [
        (3, size_of::<ValidatedSwiftReactor>()),
        (3, size_of::<RuntimeControl>()),
        (3, size_of::<AdoptedProof>()),
        (4, size_of::<SwiftRunFailure>()),
        (4, size_of::<SwiftRunUsage>()),
        (6, size_of::<ReservationTicket>()),
        (6, size_of::<Option<WasiUsage>>()),
        (1, FOUNDATION_FINAL_BOUNDARY_BYTES),
        // Composed constructor inputs and provenance/admission borrows exist
        // before its outer enlargement, so they belong in the initial floor.
        (1, super::execution::CONSTRUCTION_BOOTSTRAP_BYTES),
        // Source ingress/body/result moves precede dependent preparation, and
        // body destruction/refund places survive through final cleanup.
        (1, super::retained_profile_loader_v1::ADOPTION_ENTRY_BYTES_V1),
        (1, super::retained_profile_loader_v1::ADOPTION_MOVE_BYTES_V1),
        (1, ADOPTION_CLEANUP_BYTES_V1),
        (1, super::cache::INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1),
    ];
    let mut sum = Some(0usize);
    let mut index = 0usize;
    while index < terms.len() {
        sum = match (sum, terms[index].0.checked_mul(terms[index].1)) {
            (Some(accumulated), Some(term)) => accumulated.checked_add(term),
            _ => None,
        };
        index += 1;
    }
    sum
};

// Exact logical source-place recipe bound to the separately frozen owner
// correction. Every addition is const-evaluated; no runtime helper, local,
// iterable, allocation or second foundation is introduced by this recipe.
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new unoptimized compiler source roles total1436 logical bytes.
// No old role is credited; core and all existing closure captures are unchanged.
const SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => match common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1) {
            Some(selected) => selected.checked_add(SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.

/// Common named-source foundation: the unchanged Original F0 plus C once.
/// Composition enlarges the same ticket; this is not physical stack/RSS.
pub(crate) fn foundation_construction_bytes() -> Option<usize> {
    COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1
}

impl RuntimeControl {
    /// Consume the actual sealed proof before any new runtime allocation. No
    /// caller-supplied usage or raw-byte constructor can mint adopted authority.
    /// On failure the proof and this entire private closure actually drop before
    /// the returned cleanup snapshot can report their reservations as zero.
    pub(crate) fn adopt(
        proof: ValidatedSwiftReactor,
        budget: SwiftRunBudget,
        started: Instant,
        cancellation: Cancellation,
    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        Self::adopt_body(AdoptionBodyV1::ordinary(proof), budget, started, cancellation)
    }

    /// One shared original admission/cleanup implementation for both ingresses.
    /// The opaque body cannot be made selected from arbitrary proof/digest parts.
    pub(super) fn adopt_body(
        body: AdoptionBodyV1,
        budget: SwiftRunBudget,
        started: Instant,
        cancellation: Cancellation,
    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        Self::adopt_body_core_v1::<OriginalAdoptionV1>(body,budget,started,cancellation)
    }

    fn adopt_body_core_v1<P: ClosedAdoptionV1>(
        body: AdoptionBodyV1, budget: SwiftRunBudget, started: Instant,
        cancellation: Cancellation,
    ) -> Result<(Self, AdoptedProof), P::Failure> {
        let validation = body.proof().usage();
        let mut control = Self {
            owner: 0,
            budget,
            started,
            deadline: started,
            deadline_origin: SwiftDeadlineOrigin::Run,
            cancellation,
            validation,
            reservations: SwiftReservations::default(),
            live: SwiftLiveUsage::default(),
            cache_work: 0,
            execution_work: 0,
            instruction_fuel: 0,
            instructions: 0,
            host_calls: 0,
            cleanup_invariant: None,
            first_failure: None,
            control_header: None,
            cancellation_backing: None,
            construction: None,
        };
        let cursor = Cursor::adoption();
        let mut source = None;
        let mut metadata = None;
        let result = (|| {
            control.check_budget(cursor)?;
            control.deadline = started
                .checked_add(Duration::from_millis(budget.deadline_ms))
                .ok_or_else(|| {
                    control.fail(
                        cursor,
                        Fault::new(
                            SwiftRunFailureKind::InvalidBudget,
                            "swift_run_deadline_overflow",
                        ),
                        None,
                    )
                })?;
            control.check(cursor)?;
            // Private selected admission shell. Budget/deadline/stop checks
            // above retain precedence. No host bootstrap grant is minted here.
            // Only the sealed policy selects this source-derived fixed price.
            if P::FIXED_EXECUTION_WORK_V1 != 0 {
                if P::FIXED_EXECUTION_WORK_V1 > control.budget.execution_work {
                    return Err(control.fail(
                        cursor,
                        Fault::new(SwiftRunFailureKind::WorkExhausted, "swift_run_work")
                            .limit(SwiftRunResource::ExecutionWork,
                                P::FIXED_EXECUTION_WORK_V1, control.budget.execution_work),
                        None,
                    ));
                }
                // The prepaid interval starts after this same-counter commit.
                // Refusal leaves the counter and all reservations unchanged.
                control.execution_work = P::FIXED_EXECUTION_WORK_V1;
            }
            control.owner = NEXT_OWNER
                .try_update(Ordering::Relaxed, Ordering::Relaxed, |n| n.checked_add(1))
                .map_err(|_| {
                    control.fail(
                        cursor,
                        Fault::new(SwiftRunFailureKind::Invariant, "swift_run_owner_exhausted")
                            .limit(SwiftRunResource::OwnerIdentity, u64::MAX, u64::MAX - 1),
                        None,
                    )
                })?;
            source = Some(control.admit(
                SwiftReservationCategory::RetainedSource,
                validation.source_bytes,
                cursor,
            )?);
            metadata = Some(control.admit(
                SwiftReservationCategory::RetainedMetadata,
                validation.metadata_reserved,
                cursor,
            )?);
            control.control_header =
                Some(control.admit(SwiftReservationCategory::Shared, size_of::<Self>(), cursor)?);
            control.cancellation_backing = Some(control.admit(
                SwiftReservationCategory::Shared,
                Cancellation::requested_backing_layout().size(),
                cursor,
            )?);
            let construction = P::foundation().ok_or_else(|| {
                control.fail(
                    cursor,
                    Fault::new(SwiftRunFailureKind::Invariant, "swift_run_layout_overflow"),
                    None,
                )
            })?;
            control.construction = Some(control.admit(
                SwiftReservationCategory::Construction,
                construction,
                cursor,
            )?);
            control.check(cursor)
        })();
        if let Err(mut failure) = result {
            // Actual storage destruction precedes every proof refund. Refunding
            // control's own headers is possible only by consuming/dropping the
            // entire closure below; no admission can follow that operation.
            drop(body);
            let retirement = P::retire_tickets(&mut control,source,metadata);
            failure.after_cleanup = Some(control.finish_owned_cleanup(None));
            return Err(P::failure(failure,retirement));
        }
        Ok((
            control,
            AdoptedProof {
                body,
                source: source.expect("successful sealed adoption owns source ticket"),
                metadata: metadata.expect("successful sealed adoption owns metadata ticket"),
            },
        ))
    }

    fn check_budget(&mut self, cursor: Cursor) -> Result<(), SwiftRunFailure> {
        let max = SwiftRunBudget::default();
        let fields = [
            (
                SwiftRunResource::Reservation(SwiftReservationCategory::RetainedSource),
                self.budget.source_bytes as u64,
                max.source_bytes as u64,
            ),
            (
                SwiftRunResource::Reservation(SwiftReservationCategory::RetainedMetadata),
                self.budget.metadata_bytes as u64,
                max.metadata_bytes as u64,
            ),
            (
                SwiftRunResource::Reservation(SwiftReservationCategory::Cache),
                self.budget.cache_bytes as u64,
                max.cache_bytes as u64,
            ),
            (
                SwiftRunResource::CacheEntryBytes,
                self.budget.cache_entry_bytes as u64,
                max.cache_entry_bytes as u64,
            ),
            (
                SwiftRunResource::CacheEntries,
                self.budget.cache_entries as u64,
                max.cache_entries as u64,
            ),
            (
                SwiftRunResource::ActivePins,
                self.budget.active_pins as u64,
                max.active_pins as u64,
            ),
            (
                SwiftRunResource::CacheWork,
                self.budget.cache_work,
                max.cache_work,
            ),
            (
                SwiftRunResource::Frames,
                self.budget.frames as u64,
                max.frames as u64,
            ),
            (
                SwiftRunResource::Values,
                self.budget.values as u64,
                max.values as u64,
            ),
            (
                SwiftRunResource::Controls,
                self.budget.controls as u64,
                max.controls as u64,
            ),
            (
                SwiftRunResource::MemoryPages,
                self.budget.memory_pages as u64,
                max.memory_pages as u64,
            ),
            (
                SwiftRunResource::Reservation(SwiftReservationCategory::State),
                self.budget.state_bytes as u64,
                max.state_bytes as u64,
            ),
            (
                SwiftRunResource::Combined,
                self.budget.combined_bytes as u64,
                max.combined_bytes as u64,
            ),
            (
                SwiftRunResource::InstructionFuel,
                self.budget.instruction_fuel,
                max.instruction_fuel,
            ),
            (
                SwiftRunResource::ExecutionWork,
                self.budget.execution_work,
                max.execution_work,
            ),
            (
                SwiftRunResource::HostCalls,
                self.budget.host_calls,
                max.host_calls,
            ),
            (
                SwiftRunResource::Deadline,
                self.budget.deadline_ms,
                max.deadline_ms,
            ),
        ];
        for (resource, attempted, limit) in fields {
            if attempted > limit {
                return Err(self.fail(
                    cursor,
                    Fault::new(
                        SwiftRunFailureKind::InvalidBudget,
                        "swift_run_invalid_budget",
                    )
                    .limit(resource, attempted, limit),
                    None,
                ));
            }
        }
        Ok(())
    }

    pub(crate) fn budget(&self) -> SwiftRunBudget {
        self.budget
    }
    pub(crate) fn cancellation(&self) -> Cancellation {
        self.cancellation.clone()
    }
    pub(crate) fn deadline(&self) -> Instant {
        self.deadline
    }
    pub(crate) fn deadline_origin(&self) -> SwiftDeadlineOrigin {
        self.deadline_origin
    }

    /// Carry the earliest deadline into the actual unchanged WASI context. This
    /// method does not construct a context or reset/admit any WASI counters.
    pub(crate) fn carry_wasi_deadline(
        &mut self,
        started: Instant,
        budget: WasiBudget,
        cursor: Cursor,
    ) -> Result<Instant, SwiftRunFailure> {
        self.check(cursor)?;
        if let Err(error) = budget.check() {
            let mut fault = Fault::new(SwiftRunFailureKind::InvalidBudget, "swift_run_wasi_budget");
            fault.wasi_failure = Some(error);
            return Err(self.fail(cursor, fault, None));
        }
        let deadline = started
            .checked_add(Duration::from_millis(budget.deadline_ms))
            .ok_or_else(|| {
                self.fail(
                    cursor,
                    Fault::new(
                        SwiftRunFailureKind::InvalidBudget,
                        "swift_run_wasi_deadline_overflow",
                    ),
                    None,
                )
            })?;
        if deadline < self.deadline {
            self.deadline = deadline;
            self.deadline_origin = SwiftDeadlineOrigin::Wasi;
        }
        self.check(cursor)?;
        Ok(self.deadline)
    }

    pub(crate) fn usage(&self, wasi: Option<WasiUsage>) -> SwiftRunUsage {
        let now = Instant::now();
        SwiftRunUsage {
            reservations: self.reservations,
            live: self.live,
            cache_work: self.cache_work,
            execution_work: self.execution_work,
            instruction_fuel: self.instruction_fuel,
            instructions: self.instructions,
            host_calls: self.host_calls,
            cleanup_invariant: self.cleanup_invariant,
            elapsed_micros: micros(now.saturating_duration_since(self.started)),
            deadline_ms: self.budget.deadline_ms,
            deadline_origin: self.deadline_origin,
            deadline_overshoot_micros: micros(now.saturating_duration_since(self.deadline)),
            validation: self.validation,
            wasi,
        }
    }

    /// No caller clock hook. A single native call is cooperative, so callers
    /// must check both sides and inside all bounded loops before publication.
    pub(crate) fn check(&mut self, cursor: Cursor) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, None)
    }

    /// Preserve the actual WASI observation when the first terminal condition
    /// originates at the shared control boundary. No duplicate counters live here.
    pub(crate) fn check_with_wasi(
        &mut self,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        if let Some(failure) = self.first_failure {
            return Err(failure);
        }
        if self.cancellation.is_cancelled() {
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::Cancelled, "swift_run_cancelled"),
                wasi,
            ));
        }
        if Instant::now() >= self.deadline {
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::Deadline, "swift_run_deadline"),
                wasi,
            ));
        }
        Ok(())
    }

    pub(crate) fn fail(
        &mut self,
        cursor: Cursor,
        fault: Fault,
        wasi: Option<WasiUsage>,
    ) -> SwiftRunFailure {
        if let Some(failure) = self.first_failure {
            return failure;
        }
        let failure = SwiftRunFailure {
            stage: cursor.stage,
            kind: fault.kind,
            code: fault.code,
            function: cursor.function,
            offset: cursor.offset,
            resource: fault.resource,
            attempted: fault.attempted,
            limit: fault.limit,
            observed_capacity: fault.observed_capacity,
            deadline_origin: self.deadline_origin,
            wasi_failure: fault.wasi_failure,
            guest_exit: fault.guest_exit,
            at_failure: self.usage(wasi),
            after_cleanup: None,
        };
        self.first_failure = Some(failure);
        failure
    }

    fn category_limit(&self, category: SwiftReservationCategory) -> usize {
        match category {
            SwiftReservationCategory::RetainedSource => self.budget.source_bytes,
            SwiftReservationCategory::RetainedMetadata => self.budget.metadata_bytes,
            SwiftReservationCategory::Cache => self.budget.cache_bytes,
            SwiftReservationCategory::State => self.budget.state_bytes,
            SwiftReservationCategory::Wasi
            | SwiftReservationCategory::Shared
            | SwiftReservationCategory::Construction => self.budget.combined_bytes,
        }
    }

    fn preflight_bytes(
        &mut self,
        category: SwiftReservationCategory,
        bytes: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(usize, usize), SwiftRunFailure> {
        let category_next = self
            .reservations
            .category(category)
            .current
            .checked_add(bytes);
        let limit = self.category_limit(category);
        if category_next.is_none_or(|n| n > limit) {
            let kind = if matches!(
                category,
                SwiftReservationCategory::RetainedSource
                    | SwiftReservationCategory::RetainedMetadata
            ) {
                SwiftRunFailureKind::Adoption
            } else {
                SwiftRunFailureKind::CategoryExhausted
            };
            return Err(self.fail(
                cursor,
                Fault::new(kind, "swift_run_category_capacity").limit(
                    SwiftRunResource::Reservation(category),
                    category_next.map_or(u64::MAX, |n| n as u64),
                    limit as u64,
                ),
                wasi,
            ));
        }
        let combined_next = self.reservations.combined.current.checked_add(bytes);
        if combined_next.is_none_or(|n| n > self.budget.combined_bytes) {
            return Err(self.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::CombinedExhausted,
                    "swift_run_combined_capacity",
                )
                .limit(
                    SwiftRunResource::Combined,
                    combined_next.map_or(u64::MAX, |n| n as u64),
                    self.budget.combined_bytes as u64,
                ),
                wasi,
            ));
        }
        Ok((category_next.unwrap(), combined_next.unwrap()))
    }
    fn commit_bytes(
        &mut self,
        category: SwiftReservationCategory,
        category_next: usize,
        combined_next: usize,
    ) {
        let usage = self.reservations.category_mut(category);
        usage.current = category_next;
        usage.peak = usage.peak.max(category_next);
        self.reservations.combined.current = combined_next;
        self.reservations.combined.peak = self.reservations.combined.peak.max(combined_next);
    }
    pub(crate) fn admit(
        &mut self,
        category: SwiftReservationCategory,
        bytes: usize,
        cursor: Cursor,
    ) -> Result<ReservationTicket, SwiftRunFailure> {
        self.admit_with_wasi(category, bytes, cursor, None)
    }

    pub(crate) fn admit_with_wasi(
        &mut self,
        category: SwiftReservationCategory,
        bytes: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<ReservationTicket, SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        if self.reservations.live_tickets >= MAX_RESERVATION_TICKETS {
            return Err(self.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::ResourceExhausted,
                    "swift_run_ticket_inventory",
                )
                .limit(
                    SwiftRunResource::TicketInventory,
                    self.reservations.live_tickets as u64 + 1,
                    MAX_RESERVATION_TICKETS as u64,
                ),
                wasi,
            ));
        }
        let (category_next, combined_next) = self.preflight_bytes(category, bytes, cursor, wasi)?;
        self.commit_bytes(category, category_next, combined_next);
        self.reservations.live_tickets += 1;
        self.reservations.peak_tickets = self
            .reservations
            .peak_tickets
            .max(self.reservations.live_tickets);
        Ok(ReservationTicket {
            owner: self.owner,
            category,
            bytes,
        })
    }

    /// Aggregate locals/instructions/targets before allocating the first vector.
    /// This only admits payload bytes; fixed cache/header/scratch are additional.
    pub(crate) fn admit_cache_entry(
        &mut self,
        bytes: usize,
        cursor: Cursor,
    ) -> Result<ReservationTicket, SwiftRunFailure> {
        self.admit_cache_entry_with_wasi(bytes, cursor, None)
    }

    pub(crate) fn admit_cache_entry_with_wasi(
        &mut self,
        bytes: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<ReservationTicket, SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        if bytes > self.budget.cache_entry_bytes {
            return Err(self.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::ResourceExhausted,
                    "swift_run_cache_entry_capacity",
                )
                .limit(
                    SwiftRunResource::CacheEntryBytes,
                    bytes as u64,
                    self.budget.cache_entry_bytes as u64,
                ),
                wasi,
            ));
        }
        self.admit_with_wasi(SwiftReservationCategory::Cache, bytes, cursor, wasi)
    }

    /// Grow the one construction ticket BEFORE entering a larger phase. It is
    /// never replaced by another authoritative construction reservation.
    pub(crate) fn enlarge_construction(
        &mut self,
        bytes: usize,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        self.enlarge_construction_with_wasi(bytes, cursor, None)
    }

    pub(crate) fn enlarge_construction_with_wasi(
        &mut self,
        bytes: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        let old = self
            .construction
            .as_ref()
            .map(|ticket| ticket.bytes)
            .ok_or_else(|| {
                self.fail(
                    cursor,
                    Fault::new(
                        SwiftRunFailureKind::Invariant,
                        "swift_run_missing_construction",
                    ),
                    wasi,
                )
            })?;
        if bytes < old {
            return Err(self.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::Invariant,
                    "swift_run_construction_shrink_before_drop",
                ),
                wasi,
            ));
        }
        let (category_next, combined_next) = self.preflight_bytes(
            SwiftReservationCategory::Construction,
            bytes - old,
            cursor,
            wasi,
        )?;
        self.commit_bytes(
            SwiftReservationCategory::Construction,
            category_next,
            combined_next,
        );
        self.construction.as_mut().unwrap().bytes = bytes;
        Ok(())
    }

    /// Drop phase-owned temporaries before narrowing their shared scratch bound.
    /// The named foundation envelope remains reserved through closure teardown.
    pub(crate) fn end_construction_phase<T>(
        &mut self,
        storage: T,
        bytes: usize,
    ) -> Result<(), SwiftRunFailure> {
        self.end_construction_phase_with_wasi(storage, bytes, None)
    }

    pub(crate) fn end_construction_phase_with_wasi<T>(
        &mut self,
        storage: T,
        bytes: usize,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        drop(storage);
        let Some(ticket) = self.construction.as_ref() else {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::MissingConstruction,
                "swift_run_missing_construction",
                wasi,
            ));
        };
        if ticket.owner != self.owner || ticket.category != SwiftReservationCategory::Construction {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::ReservationOwner,
                "swift_run_construction_owner",
                wasi,
            ));
        }
        let floor = foundation_construction_bytes().unwrap_or(usize::MAX);
        if bytes < floor || bytes > ticket.bytes {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::ConstructionBound,
                "swift_run_construction_phase_bound",
                wasi,
            ));
        }
        let difference = ticket.bytes - bytes;
        let category = self
            .reservations
            .construction
            .current
            .checked_sub(difference);
        let combined = self.reservations.combined.current.checked_sub(difference);
        let (Some(category), Some(combined)) = (category, combined) else {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::ReservationUnderflow,
                "swift_run_release_underflow",
                wasi,
            ));
        };
        self.reservations.construction.current = category;
        self.reservations.combined.current = combined;
        self.construction.as_mut().unwrap().bytes = bytes;
        Ok(())
    }

    /// Caller passes the actual storage, including every allocation covered by
    /// an aggregate ticket. Cleanup is cancellation/deadline/work independent.
    pub(crate) fn drop_reserved<T>(
        &mut self,
        storage: T,
        ticket: ReservationTicket,
    ) -> Result<(), SwiftRunFailure> {
        self.drop_reserved_with_wasi(storage, ticket, None)
    }

    /// The caller captures the actual context observation before destroying
    /// its owned storage. Cleanup may itself originate the first invariant fault.
    pub(crate) fn drop_reserved_with_wasi<T>(
        &mut self,
        storage: T,
        ticket: ReservationTicket,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        drop(storage);
        self.refund_with_wasi(ticket, wasi)
    }
    pub(crate) fn drop_proof(&mut self, adopted: AdoptedProof) -> Result<(), SwiftRunFailure> {
        self.drop_proof_with_wasi(adopted, None)
    }

    pub(crate) fn drop_proof_with_wasi(
        &mut self,
        adopted: AdoptedProof,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        let AdoptedProof {
            body,
            source,
            metadata,
        } = adopted;
        drop(body);
        let source_result = self.refund_with_wasi(source, wasi);
        let metadata_result = self.refund_with_wasi(metadata, wasi);
        source_result.and(metadata_result)
    }
    /// Check an internal component/control pairing before it can perform work.
    /// This borrows its sealed ticket and neither admits nor refunds storage.
    pub(crate) fn check_adopted_owner(
        &mut self,
        adopted: &AdoptedProof,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_reservation_owner(&adopted.source, cursor, wasi)?;
        self.check_reservation_owner(&adopted.metadata, cursor, wasi)
    }

    /// Identity alone lets a component attribute its diagnostic observation.
    /// It does not establish live accounting or authorize any effect/refund.
    pub(crate) fn reservation_owner_matches(&self, ticket: &ReservationTicket) -> bool {
        ticket.owner != 0 && ticket.owner == self.owner
    }

    pub(crate) fn check_reservation_owner(
        &mut self,
        ticket: &ReservationTicket,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        let violation = if ticket.owner != self.owner || ticket.owner == 0 {
            Some((
                SwiftCleanupInvariant::ReservationOwner,
                "swift_run_reservation_owner",
            ))
        } else if self.reservations.live_tickets == 0
            || self.reservations.category(ticket.category).current < ticket.bytes
            || self.reservations.combined.current < ticket.bytes
        {
            Some((
                SwiftCleanupInvariant::ReservationUnderflow,
                "swift_run_reservation_underflow",
            ))
        } else {
            None
        };
        if let Some((invariant, code)) = violation {
            self.cleanup_invariant.get_or_insert(invariant);
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::Invariant, code),
                wasi,
            ));
        }
        Ok(())
    }

    /// Cleanup-independent validation of the actual retained construction
    /// authority. This borrows its original ticket and records no live change,
    /// checkpoint, admission, refund or ledger repair.
    pub(crate) fn check_construction_owner(
        &mut self,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        let violation = match self.construction.as_ref() {
            None => Some((
                SwiftCleanupInvariant::MissingConstruction,
                "swift_run_missing_construction",
            )),
            Some(ticket) if ticket.owner == 0 || ticket.owner != self.owner => Some((
                SwiftCleanupInvariant::ReservationOwner,
                "swift_run_construction_owner",
            )),
            Some(ticket)
                if self.reservations.live_tickets == 0
                    || self.reservations.category(ticket.category).current < ticket.bytes
                    || self.reservations.combined.current < ticket.bytes =>
            {
                Some((
                    SwiftCleanupInvariant::ReservationUnderflow,
                    "swift_run_construction_underflow",
                ))
            }
            Some(ticket)
                if !ticket.matches_layout(
                    SwiftReservationCategory::Construction,
                    self.reservations.construction.current,
                ) =>
            {
                Some((
                    SwiftCleanupInvariant::ConstructionBound,
                    "swift_run_construction_layout",
                ))
            }
            Some(_) => None,
        };
        if let Some((invariant, code)) = violation {
            self.cleanup_invariant.get_or_insert(invariant);
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::Invariant, code),
                wasi,
            ));
        }
        Ok(())
    }

    // Only after actual storage drop. A mismatch consumes the unusable token but
    // conservatively retains the complete charge; it cannot create new room.
    fn refund(&mut self, ticket: ReservationTicket) -> Result<(), SwiftRunFailure> {
        self.refund_with_wasi(ticket, None)
    }

    fn refund_with_wasi(
        &mut self,
        ticket: ReservationTicket,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        if ticket.owner != self.owner || ticket.owner == 0 {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::ReservationOwner,
                "swift_run_release_owner",
                wasi,
            ));
        }
        let category = self
            .reservations
            .category(ticket.category)
            .current
            .checked_sub(ticket.bytes);
        let combined = self.reservations.combined.current.checked_sub(ticket.bytes);
        let count = self.reservations.live_tickets.checked_sub(1);
        let (Some(category), Some(combined), Some(count)) = (category, combined, count) else {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::ReservationUnderflow,
                "swift_run_release_underflow",
                wasi,
            ));
        };
        self.reservations.category_mut(ticket.category).current = category;
        self.reservations.combined.current = combined;
        self.reservations.live_tickets = count;
        Ok(())
    }

    pub(crate) fn exact_capacity(
        &mut self,
        requested: usize,
        observed: usize,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        self.exact_capacity_with_wasi(requested, observed, cursor, None)
    }

    pub(crate) fn exact_capacity_with_wasi(
        &mut self,
        requested: usize,
        observed: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        if requested != observed {
            let mut fault = Fault::new(
                SwiftRunFailureKind::Allocation,
                "swift_run_unexpected_capacity",
            )
            .limit(
                SwiftRunResource::ExactCapacity,
                requested as u64,
                requested as u64,
            );
            fault.observed_capacity = Some(observed);
            return Err(self.fail(cursor, fault, wasi));
        }
        Ok(())
    }

    pub(crate) fn work(
        &mut self,
        component: Work,
        credits: u64,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        self.work_with_wasi(component, credits, cursor, None)
    }

    pub(crate) fn work_with_wasi(
        &mut self,
        component: Work,
        credits: u64,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        let (used, limit, resource) = match component {
            Work::Cache => (
                self.cache_work,
                self.budget.cache_work,
                SwiftRunResource::CacheWork,
            ),
            Work::Execution => (
                self.execution_work,
                self.budget.execution_work,
                SwiftRunResource::ExecutionWork,
            ),
        };
        let Some(next) = used.checked_add(credits).filter(|next| *next <= limit) else {
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::WorkExhausted, "swift_run_work").limit(
                    resource,
                    used.saturating_add(credits),
                    limit,
                ),
                wasi,
            ));
        };
        match component {
            Work::Cache => self.cache_work = next,
            Work::Execution => self.execution_work = next,
        }
        Ok(())
    }
    /// Charge once before dispatch; bulk extra fuel uses charge_fuel separately.
    pub(crate) fn instruction(&mut self, cursor: Cursor) -> Result<(), SwiftRunFailure> {
        self.instruction_with_wasi(cursor, None)
    }

    pub(crate) fn instruction_with_wasi(
        &mut self,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.charge_fuel_with_wasi(1, cursor, wasi)?;
        self.instructions = self.instructions.checked_add(1).ok_or_else(|| {
            self.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::Invariant,
                    "swift_run_instruction_overflow",
                ),
                wasi,
            )
        })?;
        Ok(())
    }
    pub(crate) fn charge_fuel(
        &mut self,
        credits: u64,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        self.charge_fuel_with_wasi(credits, cursor, None)
    }

    pub(crate) fn charge_fuel_with_wasi(
        &mut self,
        credits: u64,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        let next = self.instruction_fuel.checked_add(credits);
        let Some(next) = next.filter(|next| *next <= self.budget.instruction_fuel) else {
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::FuelExhausted, "swift_run_fuel").limit(
                    SwiftRunResource::InstructionFuel,
                    next.unwrap_or(u64::MAX),
                    self.budget.instruction_fuel,
                ),
                wasi,
            ));
        };
        self.instruction_fuel = next;
        Ok(())
    }
    pub(crate) fn enter_host(&mut self, cursor: Cursor) -> Result<(), SwiftRunFailure> {
        self.enter_host_with_wasi(cursor, None)
    }

    pub(crate) fn enter_host_with_wasi(
        &mut self,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        let next = self.host_calls.checked_add(1);
        let Some(next) = next.filter(|next| *next <= self.budget.host_calls) else {
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::HostCallLimit, "swift_run_host_calls").limit(
                    SwiftRunResource::HostCalls,
                    next.unwrap_or(u64::MAX),
                    self.budget.host_calls,
                ),
                wasi,
            ));
        };
        self.host_calls = next;
        Ok(())
    }
    fn live_parts(
        &self,
        resource: Live,
    ) -> (
        SwiftReservationUsage,
        usize,
        SwiftRunResource,
        SwiftRunFailureKind,
    ) {
        match resource {
            Live::CacheEntries => (
                self.live.cache_entries,
                self.budget.cache_entries,
                SwiftRunResource::CacheEntries,
                SwiftRunFailureKind::ResourceExhausted,
            ),
            Live::ActivePins => (
                self.live.active_pins,
                self.budget.active_pins,
                SwiftRunResource::ActivePins,
                SwiftRunFailureKind::PinLimit,
            ),
            Live::Frames => (
                self.live.frames,
                self.budget.frames,
                SwiftRunResource::Frames,
                SwiftRunFailureKind::FrameLimit,
            ),
            Live::Values => (
                self.live.values,
                self.budget.values,
                SwiftRunResource::Values,
                SwiftRunFailureKind::ValueLimit,
            ),
            Live::Controls => (
                self.live.controls,
                self.budget.controls,
                SwiftRunResource::Controls,
                SwiftRunFailureKind::ControlLimit,
            ),
            Live::MemoryPages => (
                self.live.memory_pages,
                self.budget.memory_pages as usize,
                SwiftRunResource::MemoryPages,
                SwiftRunFailureKind::ResourceExhausted,
            ),
        }
    }
    fn live_mut(&mut self, resource: Live) -> &mut SwiftReservationUsage {
        match resource {
            Live::CacheEntries => &mut self.live.cache_entries,
            Live::ActivePins => &mut self.live.active_pins,
            Live::Frames => &mut self.live.frames,
            Live::Values => &mut self.live.values,
            Live::Controls => &mut self.live.controls,
            Live::MemoryPages => &mut self.live.memory_pages,
        }
    }
    pub(crate) fn add_live(
        &mut self,
        resource: Live,
        amount: usize,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        self.add_live_with_wasi(resource, amount, cursor, None)
    }

    pub(crate) fn add_live_with_wasi(
        &mut self,
        resource: Live,
        amount: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        self.check_with_wasi(cursor, wasi)?;
        let (usage, limit, diagnostic, kind) = self.live_parts(resource);
        let next = usage.current.checked_add(amount);
        let Some(next) = next.filter(|next| *next <= limit) else {
            return Err(self.fail(
                cursor,
                Fault::new(kind, "swift_run_live_limit").limit(
                    diagnostic,
                    next.map_or(u64::MAX, |n| n as u64),
                    limit as u64,
                ),
                wasi,
            ));
        };
        let usage = self.live_mut(resource);
        usage.current = next;
        usage.peak = usage.peak.max(next);
        Ok(())
    }
    /// Counts are removed only after corresponding owner/frame/arena cleanup.
    pub(crate) fn remove_live(
        &mut self,
        resource: Live,
        amount: usize,
    ) -> Result<(), SwiftRunFailure> {
        self.remove_live_with_wasi(resource, amount, None)
    }

    pub(crate) fn remove_live_with_wasi(
        &mut self,
        resource: Live,
        amount: usize,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        let (usage, _, _, _) = self.live_parts(resource);
        let Some(next) = usage.current.checked_sub(amount) else {
            return Err(self.cleanup_fault_with_wasi(
                SwiftCleanupInvariant::LiveUnderflow,
                "swift_run_live_underflow",
                wasi,
            ));
        };
        self.live_mut(resource).current = next;
        Ok(())
    }

    /// Active caller attribution is supplied before the immutable failure boundary.
    /// Cleanup callers keep the separate cursorless entry above.
    pub(crate) fn remove_live_at_with_wasi(
        &mut self,
        resource: Live,
        amount: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        let (usage, _, kind, _) = self.live_parts(resource);
        let Some(next) = usage.current.checked_sub(amount) else {
            self.cleanup_invariant
                .get_or_insert(SwiftCleanupInvariant::LiveUnderflow);
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::Invariant, "swift_run_live_underflow").limit(
                    kind,
                    amount as u64,
                    usage.current as u64,
                ),
                wasi,
            ));
        };
        self.live_mut(resource).current = next;
        Ok(())
    }

    fn cleanup_fault(
        &mut self,
        invariant: SwiftCleanupInvariant,
        code: &'static str,
    ) -> SwiftRunFailure {
        self.cleanup_fault_with_wasi(invariant, code, None)
    }

    fn cleanup_fault_with_wasi(
        &mut self,
        invariant: SwiftCleanupInvariant,
        code: &'static str,
        wasi: Option<WasiUsage>,
    ) -> SwiftRunFailure {
        self.cleanup_invariant.get_or_insert(invariant);
        self.fail(
            Cursor {
                stage: SwiftRunStage::Cleanup,
                function: None,
                offset: None,
            },
            Fault::new(SwiftRunFailureKind::Invariant, code),
            wasi,
        )
    }

    pub(crate) fn record_cleanup(&mut self, wasi: Option<WasiUsage>) -> Option<SwiftRunFailure> {
        let usage = self.usage(wasi);
        if let Some(failure) = &mut self.first_failure {
            failure.after_cleanup = Some(usage);
        }
        self.first_failure
    }

    /// Consume and actually drop this foundation closure, then return a copied
    /// observation. Only its inline-owned header/backing/construction tickets are
    /// removed from the observation. An enlarged construction phase must first
    /// pass its actual storage through end_construction_phase; otherwise the
    /// entire construction charge remains. Missing external tickets/storage are
    /// conservatively charged. This is not an arbitrary ledger-zeroing method.
    pub(crate) fn finish_owned_cleanup(mut self, wasi: Option<WasiUsage>) -> SwiftRunUsage {
        let started = self.started;
        let deadline = self.deadline;
        let mut observation = self.usage(wasi);
        for ticket in [
            self.control_header.take(),
            self.cancellation_backing.take(),
            self.construction.take(),
        ]
        .into_iter()
        .flatten()
        {
            if ticket.owner != self.owner || ticket.owner == 0 {
                observation
                    .cleanup_invariant
                    .get_or_insert(SwiftCleanupInvariant::ReservationOwner);
                continue;
            }
            // The control only owns the known foundation closure. Enlarging
            // this ticket did not transfer additional phase storage into it.
            // An omitted phase drop/refund therefore cannot produce free room
            // or a false zero-after-drop observation during control teardown.
            if ticket.category == SwiftReservationCategory::Construction
                && Some(ticket.bytes) != foundation_construction_bytes()
            {
                observation
                    .cleanup_invariant
                    .get_or_insert(SwiftCleanupInvariant::ConstructionBound);
                continue;
            }
            let category = observation
                .reservations
                .category(ticket.category)
                .current
                .checked_sub(ticket.bytes);
            let combined = observation
                .reservations
                .combined
                .current
                .checked_sub(ticket.bytes);
            let count = observation.reservations.live_tickets.checked_sub(1);
            if let (Some(category), Some(combined), Some(count)) = (category, combined, count) {
                observation
                    .reservations
                    .category_mut(ticket.category)
                    .current = category;
                observation.reservations.combined.current = combined;
                observation.reservations.live_tickets = count;
            } else {
                observation
                    .cleanup_invariant
                    .get_or_insert(SwiftCleanupInvariant::ReservationUnderflow);
            }
        }
        drop(self); // Includes the VM's last cancellation handle and control data.
        let now = Instant::now();
        observation.elapsed_micros = micros(now.saturating_duration_since(started));
        observation.deadline_overshoot_micros = micros(now.saturating_duration_since(deadline));
        observation
    }
}
fn micros(duration: Duration) -> u64 {
    u64::try_from(duration.as_micros()).unwrap_or(u64::MAX)
}

#[cfg(test)]
#[path = "control_tests.rs"]
mod tests;

#[cfg(test)] impl RuntimeControl {pub(crate) fn host_test_counter(&mut self,value:u64){self.host_calls=value;}}


// Isolated source preparation. No route in this tree invokes the new ingress.
mod adoption_state_seal_v1 { pub(super) trait Closed {} }
struct OriginalAdoptionV1;
struct SnapshotAdoptionV1;
impl adoption_state_seal_v1::Closed for OriginalAdoptionV1 {}
impl adoption_state_seal_v1::Closed for SnapshotAdoptionV1 {}
trait ClosedAdoptionV1: adoption_state_seal_v1::Closed {
    type Failure;
    type Retirement;
    const FIXED_EXECUTION_WORK_V1: u64;
    fn foundation()->Option<usize>;
    fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>)->Self::Retirement;
    fn failure(primary:SwiftRunFailure,retirement:Self::Retirement)->Self::Failure;
}
impl ClosedAdoptionV1 for OriginalAdoptionV1 {
    type Failure=SwiftRunFailure;
    type Retirement=();
    const FIXED_EXECUTION_WORK_V1: u64 = 0;
    fn foundation()->Option<usize>{foundation_construction_bytes()}
    fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>){
        // Exact Original order/semantics; there is no Selected retirement value.
        if let Some(ticket)=source {let _=control.refund(ticket);}
        if let Some(ticket)=metadata {let _=control.refund(ticket);}
    }
    fn failure(primary:SwiftRunFailure,_:())->SwiftRunFailure{primary}
}
pub(super) struct SnapshotPreScopeFailureV1 {
    pub(super) primary:SwiftRunFailure,
    pub(super) retirement:Result<(),SwiftRunFailure>,
}
impl ClosedAdoptionV1 for SnapshotAdoptionV1 {
    type Failure=SnapshotPreScopeFailureV1;
    type Retirement=Result<(),SwiftRunFailure>;
    const FIXED_EXECUTION_WORK_V1: u64 = SNAPSHOT_FIXED_EXECUTION_WORK_V1;
    fn foundation()->Option<usize>{snapshot_scope_candidate_foundation_v1()}
    fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>)->Self::Retirement{
        let source=match source {Some(ticket)=>control.refund(ticket),None=>Ok(())};
        let metadata=match metadata {Some(ticket)=>control.refund(ticket),None=>Ok(())};
        source.and(metadata) // Both actual refunds occur even when the first fails.
    }
    fn failure(primary:SwiftRunFailure,retirement:Self::Retirement)->Self::Failure{
        SnapshotPreScopeFailureV1 {primary,retirement}
    }
}

use super::cache::{SnapshotClaimsV1,SnapshotOuterV1,SnapshotPrimaryRetirementV1};
use crate::experimental_wasi::accounted::AccountedWasi;
use crate::experimental_wasi::WasiGrants;
use std::fs::File;

/// No control/proof extraction and no parts constructor. Actual slots only.
pub(super) struct SnapshotScopeV1 {
    control:RuntimeControl,
    adopted:Option<AdoptedProof>,
    cache:Option<super::cache::SwiftFunctionCache>,
    wasi:Option<AccountedWasi>,
    wasi_attachment:Option<SnapshotWasiAttachmentV1>,
    base_foundation:usize,
}
/// A single-use borrow of the actual selected scope's owners. Only this module
/// can mint it; callers cannot substitute a different control or cache slot.
pub(super) struct SnapshotScopeBorrowV1<'a> {
    cache:&'a mut Option<super::cache::SwiftFunctionCache>,
    control:&'a mut RuntimeControl,
    wasi:Option<&'a AccountedWasi>,
    adopted:AdoptedProof,
}
impl<'a> SnapshotScopeBorrowV1<'a> {
    pub(super) fn into_parts(self)->(&'a mut Option<super::cache::SwiftFunctionCache>,&'a mut RuntimeControl,Option<&'a AccountedWasi>,AdoptedProof){
        let Self {cache,control,wasi,adopted}=self;
        (cache,control,wasi,adopted)
    }
}
pub(super) struct SnapshotRunV1 { scope:SnapshotScopeV1,outer:SnapshotOuterV1 }
pub(super) struct SnapshotScopeFinishV1 {
    pub(super) primary_retirement:SnapshotPrimaryRetirementV1,
    pub(super) cache_retirement:Option<SwiftRunFailure>,
    pub(super) scope_adopted_retirement:Result<(),SwiftRunFailure>,
    pub(super) wasi_attachment:Option<SnapshotWasiAttachmentV1>,
    pub(super) wasi_retirement:Result<(),SwiftRunFailure>,
    pub(super) usage:SwiftRunUsage,
}
pub(super) struct SnapshotWasiAttachmentV1 {
    pub(super) construction:Result<(),SwiftRunFailure>,
    pub(super) completion:Result<(),SwiftRunFailure>,
}
impl RuntimeControl {
    // Only the authentic consuming carrier calls this. Selected provenance is
    // rechecked from the actual opaque body, never from a caller boolean.
    pub(super) fn adopt_snapshot_body_v1(body:super::retained_profile_loader_v1::SelectedSnapshotBodyV1,budget:SwiftRunBudget,started:Instant,cancellation:Cancellation)
        ->Result<SnapshotScopeV1,SnapshotPreScopeFailureV1> {
        let body=body.into_adoption_body_v1();
        let (control,adopted)=Self::adopt_body_core_v1::<SnapshotAdoptionV1>(body,budget,started,cancellation)?;
        let base_foundation=control.construction.as_ref().expect("actual Construction admitted").bytes;
        Ok(SnapshotScopeV1 {control,adopted:Some(adopted),cache:None,wasi:None,wasi_attachment:None,base_foundation})
    }
}
impl SnapshotScopeV1 {
    pub(super) fn attach_wasi_v1(&mut self,grants:WasiGrants,budget:WasiBudget,started:Instant)->&SnapshotWasiAttachmentV1 {
        if self.wasi_attachment.is_some(){return self.wasi_attachment.as_ref().expect("one actual attachment attempt");}
        let result=self.attach_wasi_inner_v1(grants,budget,started);
        self.wasi_attachment=Some(result);
        self.wasi_attachment.as_ref().expect("actual retained attachment result")
    }
    fn attach_wasi_inner_v1(&mut self,grants:WasiGrants,budget:WasiBudget,started:Instant)->SnapshotWasiAttachmentV1 {
        let cursor=Cursor {stage:SwiftRunStage::Initialization,function:None,offset:None};
        if self.wasi.is_some() {
            let failure=self.control.fail(cursor,Fault::new(SwiftRunFailureKind::Invariant,"swift_snapshot_wasi_slot_occupied"),None);
            return SnapshotWasiAttachmentV1 {construction:Err(failure),completion:Ok(())};
        }
        let mut phase=match AccountedWasi::prepare(&mut self.control,cursor) {
            Ok(phase)=>phase,
            Err(failure)=>return SnapshotWasiAttachmentV1 {construction:Err(failure),completion:Ok(())},
        };
        let construction=match phase.construct(grants,budget,started,cursor) {
            Ok(wasi)=>{self.wasi=Some(wasi);Ok(())},Err(failure)=>Err(failure),
        };
        let completion=phase.complete();
        SnapshotWasiAttachmentV1 {construction,completion}
    }
    pub(super) fn construct_v1(mut self,claims:&SnapshotClaimsV1,rows:&mut File,snapshot:&mut File)->SnapshotRunV1 {
        let adopted=self.adopted.take().expect("one-shot actual adopted owner");
        let owners=SnapshotScopeBorrowV1 {
            cache:&mut self.cache,control:&mut self.control,wasi:self.wasi.as_ref(),adopted,
        };
        let outer=super::cache::construct_snapshot_in_scope_v1(owners,claims,rows,snapshot);
        SnapshotRunV1 {scope:self,outer}
    }
}
impl SnapshotRunV1 {
    pub(super) fn outer_v1(&self)->&SnapshotOuterV1{&self.outer}
    // Consuming run ties this exact outer to this exact authentic owner.
    pub(super) fn finish_v1(self)->SnapshotScopeFinishV1 {
        let Self {scope,outer}=self;
        let SnapshotScopeV1 {mut control,adopted,mut cache,wasi,wasi_attachment,base_foundation}=scope;
        let observation=match wasi.as_ref(){
            Some(wasi) if wasi.snapshot_pair_v1(&control).is_ok()=>Some(wasi.usage()),_=>None,
        };
        let primary_retirement=outer.retire_v1(&mut control,observation);
        let scope_adopted_retirement=match adopted{Some(adopted)=>control.drop_proof_with_wasi(adopted,observation),None=>Ok(())};
        let mut cache_retirement=None;
        if cache.is_some() {
            match super::cache::SwiftFunctionCache::cleanup(&mut cache,&mut control,wasi.as_ref()) {
                Ok(tail)=>tail.complete(cache,&mut cache_retirement),
                Err(failure)=>{cache_retirement=Some(failure);drop(cache);},
            }
        }else{drop(cache);}
        // A failed original cleanup can leave a real cache owner in this slot.
        // Its storage dies, but its uncertain tickets are never repaired/refunded.
        let wasi_retirement=match wasi {Some(wasi)=>wasi.cleanup(&mut control),None=>Ok(())};
        let _captured_foundation=base_foundation;
        // Finalizer return/error/move lifetime closure is not proven. Do not
        // narrow to a byte-only alternate foundation. Original finish records
        // ConstructionBound and retains the enlarged charge, including F1.
        let usage=control.finish_owned_cleanup(observation);
        SnapshotScopeFinishV1 {primary_retirement,cache_retirement,scope_adopted_retirement,wasi_attachment,wasi_retirement,usage}
    }
}

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum SnapshotStopV1 {Existing(SwiftRunFailure),Cancelled,Deadline(SwiftDeadlineOrigin)}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum SnapshotAdmissionErrorV1 {
    Stop(SnapshotStopV1),Owner,Layout,Arithmetic,WorkAuditPending,
    Work {used:u64,requested:u64,limit:u64},
    Storage {current:usize,additional:usize,limit:usize},
}
impl RuntimeControl {
    pub(super) fn snapshot_existing_v1(&self)->Result<(),SnapshotAdmissionErrorV1>{
        match self.first_failure {Some(f)=>Err(SnapshotAdmissionErrorV1::Stop(SnapshotStopV1::Existing(f))),None=>Ok(())}
    }
    pub(super) fn snapshot_observe_stop_v1(&self)->Result<(),SnapshotStopV1>{
        if let Some(f)=self.first_failure{return Err(SnapshotStopV1::Existing(f));}
        if self.cancellation.is_cancelled(){return Err(SnapshotStopV1::Cancelled);}
        if Instant::now()>=self.deadline{return Err(SnapshotStopV1::Deadline(self.deadline_origin));}
        Ok(())
    }
    pub(crate) fn snapshot_ticket_v1(&self,ticket:&ReservationTicket,category:SwiftReservationCategory,bytes:usize)
        ->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_existing_v1()?;
        if ticket.owner==0 || ticket.owner!=self.owner{return Err(SnapshotAdmissionErrorV1::Owner);}
        if !ticket.matches_layout(category,bytes) || self.reservations.live_tickets==0
            || self.reservations.category(category).current<bytes || self.reservations.combined.current<bytes {
            return Err(SnapshotAdmissionErrorV1::Layout);
        }
        Ok(())
    }
    pub(super) fn snapshot_owner_v1(&self,owner:u64)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_existing_v1()?;
        if owner==0 || owner!=self.owner{return Err(SnapshotAdmissionErrorV1::Owner);}
        Ok(())
    }
    pub(crate) fn snapshot_ticket_identity_v1(&self,ticket:&ReservationTicket)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_ticket_v1(ticket,ticket.category,ticket.bytes)
    }
    pub(super) fn snapshot_adopted_pair_v1(&self,adopted:&AdoptedProof)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_ticket_identity_v1(&adopted.source)?;
        self.snapshot_ticket_identity_v1(&adopted.metadata)?;
        self.snapshot_ticket_v1(&adopted.source,SwiftReservationCategory::RetainedSource,adopted.proof().usage().source_bytes)?;
        self.snapshot_ticket_v1(&adopted.metadata,SwiftReservationCategory::RetainedMetadata,adopted.proof().usage().metadata_reserved)
    }
    pub(super) fn snapshot_foundation_pair_v1(&self)->Result<usize,SnapshotAdmissionErrorV1>{
        let construction=self.construction.as_ref().ok_or(SnapshotAdmissionErrorV1::Layout)?;
        self.snapshot_ticket_v1(construction,SwiftReservationCategory::Construction,construction.bytes)?;
        self.snapshot_ticket_v1(self.control_header.as_ref().ok_or(SnapshotAdmissionErrorV1::Layout)?,SwiftReservationCategory::Shared,size_of::<Self>())?;
        self.snapshot_ticket_v1(self.cancellation_backing.as_ref().ok_or(SnapshotAdmissionErrorV1::Layout)?,SwiftReservationCategory::Shared,Cancellation::requested_backing_layout().size())?;
        if self.reservations.construction.current!=construction.bytes{return Err(SnapshotAdmissionErrorV1::Layout);}
        Ok(construction.bytes)
    }
    pub(super) fn snapshot_totals_v1(&self,source:usize,metadata:usize,cache:usize,wasi:usize,wasi_tickets:usize)->Result<(),SnapshotAdmissionErrorV1>{
        let construction=self.snapshot_foundation_pair_v1()?;
        let shared=size_of::<Self>().checked_add(Cancellation::requested_backing_layout().size()).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        let terms=[(SwiftReservationCategory::RetainedSource,source),(SwiftReservationCategory::RetainedMetadata,metadata),
            (SwiftReservationCategory::Cache,cache),(SwiftReservationCategory::Wasi,wasi),
            (SwiftReservationCategory::Shared,shared),(SwiftReservationCategory::Construction,construction)];
        let mut sum=0usize;
        for (category,bytes) in terms {
            if self.reservations.category(category).current<bytes{return Err(SnapshotAdmissionErrorV1::Layout);}
            sum=sum.checked_add(bytes).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        }
        let tickets=9usize.checked_add(wasi_tickets).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        if self.reservations.combined.current<sum || self.reservations.live_tickets<tickets{return Err(SnapshotAdmissionErrorV1::Layout);}
        Ok(())
    }
    pub(super) fn snapshot_debit_v1(&mut self,credits:u64)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_observe_stop_v1().map_err(SnapshotAdmissionErrorV1::Stop)?;
        let used=self.execution_work;let limit=self.budget.execution_work;
        let next=used.checked_add(credits).filter(|next|*next<=limit)
            .ok_or(SnapshotAdmissionErrorV1::Work {used,requested:credits,limit})?;
        self.execution_work=next;Ok(())
    }
    pub(super) fn snapshot_storage_preflight_v1(&self,additional:usize)->Result<usize,SnapshotAdmissionErrorV1>{
        let previous=self.snapshot_foundation_pair_v1()?;
        for (current,limit) in [(self.reservations.construction.current,self.category_limit(SwiftReservationCategory::Construction)),
            (self.reservations.combined.current,self.budget.combined_bytes)] {
            current.checked_add(additional).filter(|next|*next<=limit)
                .ok_or(SnapshotAdmissionErrorV1::Storage {current,additional,limit})?;
        }
        self.snapshot_observe_stop_v1().map_err(SnapshotAdmissionErrorV1::Stop)?;
        Ok(previous)
    }
    pub(super) fn snapshot_commit_storage_v1(&mut self,additional:usize)->Result<usize,SnapshotAdmissionErrorV1>{
        let previous=self.snapshot_storage_preflight_v1(additional)?;
        // All fallible operations precede this one atomic same-ticket commit.
        let construction=previous.checked_add(additional).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        let combined=self.reservations.combined.current.checked_add(additional).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        self.construction.as_mut().expect("preflight actual ticket").bytes=construction;
        self.reservations.construction.current=construction;
        self.reservations.construction.peak=self.reservations.construction.peak.max(construction);
        self.reservations.combined.current=combined;
        self.reservations.combined.peak=self.reservations.combined.peak.max(combined);
        Ok(previous)
    }
}

// Conservative candidate source roles. Not a selected operational floor.
struct CommonAdoptionPlacesV1 {
    body_argument:AdoptionBodyV1,body_move:AdoptionBodyV1,
    budgets:[SwiftRunBudget;2],started:[Instant;2],cancellations:[Cancellation;2],
    original_return:Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>,
    original_adapter_return:Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>,
}
struct SnapshotScopePlacesV1 {
    scopes:[SnapshotScopeV1;3],scope_return:Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>,
    scope_option:Option<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>,
    core_returns:[Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>;3],
    pre_scope_errors:[SnapshotPreScopeFailureV1;4],
    retirement:[Result<(),SwiftRunFailure>;4],
    run:SnapshotRunV1,run_move:SnapshotRunV1,
    finish_return:SnapshotScopeFinishV1,finish_move:SnapshotScopeFinishV1,
    attachment:SnapshotWasiAttachmentV1,attachment_return:SnapshotWasiAttachmentV1,
    body_moves:[AdoptionBodyV1;3],outer_return:SnapshotOuterV1,outer_option:Option<SnapshotOuterV1>,
    selected_body_moves:[super::retained_profile_loader_v1::SelectedSnapshotBodyV1;4],
    borrows:[&'static mut RuntimeControl;8],scalars:[usize;16],
}
fn snapshot_scope_candidate_foundation_v1()->Option<usize>{
    // Exact selected source recipe, with no placeholder type aggregates.
    // The original selected-finalizer conservative charge remains unchanged.
    SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1
}
#[cfg(mixer_snapshot_composition_layout)]
#[no_mangle]
pub static MIXER_COMPOSITION_CONTROL_LAYOUTS_V1:[usize;24]=[
 size_of::<RuntimeControl>(),std::mem::align_of::<RuntimeControl>(),
 size_of::<CommonAdoptionPlacesV1>(),std::mem::align_of::<CommonAdoptionPlacesV1>(),
 size_of::<SnapshotScopeV1>(),std::mem::align_of::<SnapshotScopeV1>(),
 size_of::<SnapshotPreScopeFailureV1>(),std::mem::align_of::<SnapshotPreScopeFailureV1>(),
 size_of::<SnapshotScopePlacesV1>(),std::mem::align_of::<SnapshotScopePlacesV1>(),
 size_of::<SnapshotRunV1>(),std::mem::align_of::<SnapshotRunV1>(),
 size_of::<SnapshotScopeFinishV1>(),std::mem::align_of::<SnapshotScopeFinishV1>(),
 size_of::<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>(),std::mem::align_of::<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>(),
 size_of::<Option<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>>(),std::mem::align_of::<Option<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>>(),
 size_of::<Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>>(),std::mem::align_of::<Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>>(),
 size_of::<SnapshotWasiAttachmentV1>(),std::mem::align_of::<SnapshotWasiAttachmentV1>(),
 size_of::<SnapshotStopV1>(),size_of::<SnapshotAdmissionErrorV1>(),
];
