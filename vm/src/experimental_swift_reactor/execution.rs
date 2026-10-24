//! Private bounded construction of an uninitialized Swift reactor owner.
//! Private accounted zero-frame value operations are also implemented.
//! No initialize, invoke, or interpreter loop is provided.
#![allow(dead_code)] // The constructor remains private, with no activation route.
#![allow(clippy::result_large_err)]

use super::cache::{
    CacheCleanupTail, CacheConstructionFailure, CacheConstructionPhase, CacheControl,
    CacheOperationPhase, SwiftFunctionCache, SwiftFunctionPin, SwiftReleaseFailure,
};
use super::control::*;
use crate::experimental::cache::{DecodedInstruction, FunctionView, Operation};
use crate::experimental::descriptors::{
    FunctionSpanView, GlobalView, MemoryExecutionView, SegmentExecutionView, SignatureView,
    TableExecutionView,
};
use crate::experimental::execution::{borrowed::*, Control};
use crate::experimental_wasi::{
    accounted::{AccountedWasi, WasiConstructionPhase},
    WasiBudget, WasiGrants, WasiUsage,
};
use crate::{Type, Value};
use std::mem::{size_of, take};
use std::time::Instant;

#[path = "frame_operations.rs"]
pub(crate) mod frame_operations;
#[path = "value_operations.rs"]
pub(crate) mod value_operations;

#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct SwiftMode;
impl sealed::Mode for SwiftMode {}
impl ExecutionMode for SwiftMode {
    type Cache = SwiftFunctionCache;
    type Pin = SwiftFunctionPin;
    type Frame = SwiftFrame;
    type Operation<'a> = SwiftExecutionOperation<'a>;
    type Failure = SwiftRunFailure;
}

#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct SwiftFrame {
    pub function: u32,
    pub pc: usize,
    pub base: usize,
    pub operands: usize,
    pub controls: usize,
    pub result: bool,
    pub pin: SwiftFunctionPin,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct SwiftExecutionState {
    pub memory: Vec<u8>,
    pub table: Vec<Option<u32>>,
    pub globals: Vec<Value>,
    pub values: Vec<Value>,
    pub controls: Vec<Control>,
    pub frames: Vec<SwiftFrame>,
    pub buffers: [Option<ReservationTicket>; 6],
    pub execution_header: Option<ReservationTicket>,
    pub frame_cleanup: frame_operations::FrameCleanupState,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) enum Lifecycle {
    Uninitialized,
    Ready,
    Terminal,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct SwiftReactorInstance {
    pub control: Option<RuntimeControl>,
    pub cache: Option<SwiftFunctionCache>,
    pub wasi: Option<AccountedWasi>,
    pub state: Option<SwiftExecutionState>,
    pub lifecycle: Lifecycle,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct SwiftExecutionOperation<'a> {
    pub control: &'a mut RuntimeControl,
    pub wasi: &'a mut AccountedWasi,
    pub cursor: Cursor,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct ExecutionConstructionPhase<'a> {
    pub control: &'a mut RuntimeControl,
    pub cache: &'a SwiftFunctionCache,
    pub wasi: &'a AccountedWasi,
    pub cursor: Cursor,
    pub previous_bound: usize,
    pub constructed: bool,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct ExecutionOperationPhase<'a> {
    pub parts: ExecutionParts<'a, SwiftMode>,
    pub operation: SwiftExecutionOperation<'a>,
    pub previous_bound: usize,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct PartialState {
    pub state: SwiftExecutionState,
    pub next_arena: usize,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct PartialInstance {
    pub control: Option<RuntimeControl>,
    pub cache: Option<SwiftFunctionCache>,
    pub wasi: Option<AccountedWasi>,
    pub state: Option<SwiftExecutionState>,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct EntryGuard {
    pub pin: Option<SwiftFunctionPin>,
    pub values_debited: usize,
    pub controls_debited: usize,
    pub frame_debited: bool,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct ScalarReader<'a> {
    pub bytes: &'a [u8],
    pub at: usize,
    pub absolute_offset: usize,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct SelectedInstruction {
    pub instruction: DecodedInstruction,
    pub branch_target: Option<u32>,
    pub cursor: Cursor,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct GrowthTransfer {
    pub replacement: Vec<u8>,
    pub ticket: Option<ReservationTicket>,
    pub old: Vec<u8>,
    pub old_ticket: Option<ReservationTicket>,
    pub old_pages: u32,
    pub next_pages: u32,
    pub copied: usize,
}

#[must_use = "The same execution header remains charged until completion consumes all returned storage"]
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct ExecutionCleanupTail {
    pub control: RuntimeControl,
    pub header: Option<ReservationTicket>,
    pub final_wasi: Option<WasiUsage>,
    pub failure: Option<SwiftRunFailure>,
}
#[must_use = "Constructor failure retains authority until caller return storage is supplied for completion"]
pub(crate) struct ConstructionCleanupTail {
    pub tail: ExecutionCleanupTail,
    pub previous_bound: usize,
}
#[must_use = "A rejected pair stays owned; a cleanup variant must be completed"]
// Keep the original control and accounting tail inline; boxing would allocate
// while returning a construction failure and change the measured authority.
#[allow(clippy::large_enum_variant)]
pub(crate) enum ConstructionFailure {
    Rejected(SwiftRunFailure),
    Cleanup(ConstructionCleanupTail),
}
impl std::fmt::Debug for ConstructionFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Rejected(failure) => f.debug_tuple("Rejected").field(failure).finish(),
            Self::Cleanup(tail) => f.debug_tuple("Cleanup").field(&tail.tail.failure).finish(),
        }
    }
}
fn drop_construction_return_storage<T>(
    tail: ConstructionCleanupTail,
    storage: T,
) -> (HeaderCompletionParts, usize) {
    let ConstructionCleanupTail {
        tail,
        previous_bound,
    } = tail;
    (drop_cleanup_return_storage(tail, storage), previous_bound)
}
impl ConstructionCleanupTail {
    /// No whole possible-instance Result/Option/pair or partial builder may be
    /// retained by the caller after this consumes its supplied storage.
    pub(crate) fn complete<T>(
        self,
        storage: T,
        outcome: &mut Option<SwiftRunFailure>,
        usage: &mut Option<SwiftRunUsage>,
    ) {
        let (
            HeaderCompletionParts {
                mut control,
                mut header,
                final_wasi,
            },
            previous_bound,
        ) = drop_construction_return_storage(self, storage);
        let _ = control.end_construction_phase_with_wasi((), previous_bound, final_wasi);
        if let Some(ticket) = header.take() {
            let _ = control.drop_reserved_with_wasi((), ticket, final_wasi);
        }
        *outcome = control.record_cleanup(final_wasi);
        *usage = Some(control.finish_owned_cleanup(final_wasi));
    }
}
/// This is the only selected representation at the final header boundary.
/// The function frame owning all large return/Option/tail storage ends first.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct HeaderCompletionParts {
    pub control: RuntimeControl,
    pub header: Option<ReservationTicket>,
    pub final_wasi: Option<WasiUsage>,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
fn drop_cleanup_return_storage<T>(tail: ExecutionCleanupTail, storage: T) -> HeaderCompletionParts {
    let ExecutionCleanupTail {
        control,
        header,
        final_wasi,
        failure,
    } = tail;
    drop((storage, failure));
    HeaderCompletionParts {
        control,
        header,
        final_wasi,
    }
}
impl ExecutionCleanupTail {
    /// Cleanup helper only. There is no route that creates a runnable owner.
    #[allow(dead_code)] // Final cleanup helper pending disjoint foundation boundary review.
    pub(crate) fn complete<T>(
        self,
        storage: T,
        outcome: &mut Option<SwiftRunFailure>,
        usage: &mut Option<SwiftRunUsage>,
    ) {
        let HeaderCompletionParts {
            mut control,
            mut header,
            final_wasi,
        } = drop_cleanup_return_storage(self, storage);
        if let Some(ticket) = header.take() {
            // This temporary result ends before record_cleanup/finish below.
            let _ = control.drop_reserved_with_wasi((), ticket, final_wasi);
        }
        *outcome = control.record_cleanup(final_wasi);
        *usage = Some(control.finish_owned_cleanup(final_wasi));
    }
}

/// Compiles the strict-shorter cache reborrow without changing the operation.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) fn with_cache_operation<R>(
    phase: &mut ExecutionOperationPhase<'_>,
    body: impl for<'short> FnOnce(
        &mut ExecutionParts<'short, SwiftMode>,
        &mut SwiftExecutionOperation<'short>,
    ) -> R,
) -> R {
    let parts = &mut phase.parts;
    let operation = &mut phase.operation;
    let mut short_parts = ExecutionParts {
        cache: &mut *parts.cache,
        memory: &mut *parts.memory,
        table: &mut *parts.table,
        globals: &mut *parts.globals,
        values: &mut *parts.values,
        controls: &mut *parts.controls,
        frames: &mut *parts.frames,
    };
    let mut short_operation = SwiftExecutionOperation {
        control: &mut *operation.control,
        wasi: &mut *operation.wasi,
        cursor: operation.cursor,
    };
    body(&mut short_parts, &mut short_operation)
}

/// Named rows are additional objects, never bytes borrowed from another owner.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct LayoutTerm {
    pub phase: &'static str,
    pub binding: &'static str,
    pub shape: &'static str,
    pub count: usize,
    pub bytes: usize,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) const fn terms() -> &'static [LayoutTerm] {
    macro_rules! row {
        ($p:literal,$b:literal,$n:expr,$t:ty) => {
            LayoutTerm {
                phase: $p,
                binding: $b,
                shape: stringify!($t),
                count: $n,
                bytes: size_of::<$t>(),
            }
        };
    }
    &[
        row!(
            "construction",
            "state source/return/caller",
            3,
            SwiftExecutionState
        ),
        row!(
            "construction",
            "instance source/return/caller",
            3,
            SwiftReactorInstance
        ),
        row!(
            "construction",
            "partial state source/return/caller",
            3,
            PartialState
        ),
        row!(
            "construction",
            "partial instance source/return/caller",
            3,
            PartialInstance
        ),
        row!(
            "construction",
            "state return plus caller slot",
            2,
            Option<Result<SwiftExecutionState, SwiftRunFailure>>
        ),
        row!(
            "construction",
            "instance return plus caller slot",
            2,
            Option<Result<SwiftReactorInstance, SwiftRunFailure>>
        ),
        row!(
            "construction",
            "cache return plus caller slot",
            2,
            Option<Result<SwiftFunctionCache, CacheConstructionFailure>>
        ),
        row!(
            "construction",
            "wasi return plus caller slot",
            2,
            Option<Result<AccountedWasi, SwiftRunFailure>>
        ),
        row!(
            "construction",
            "state preparation source/return/caller",
            3,
            ExecutionConstructionPhase<'static>
        ),
        row!(
            "construction",
            "cache preparation source/return/caller",
            3,
            CacheConstructionPhase<'static>
        ),
        row!(
            "construction",
            "wasi preparation source/return/caller",
            3,
            WasiConstructionPhase<'static>
        ),
        row!(
            "construction",
            "segment/initializer reader",
            3,
            ScalarReader<'static>
        ),
        row!(
            "construction",
            "descriptor and return",
            2,
            Option<FunctionSpanView<'static>>
        ),
        row!(
            "operation",
            "phase source/return/caller",
            3,
            ExecutionOperationPhase<'static>
        ),
        row!(
            "operation",
            "short parts + helper argument",
            2,
            ExecutionParts<'static, SwiftMode>
        ),
        row!(
            "operation",
            "short operation + helper argument",
            2,
            SwiftExecutionOperation<'static>
        ),
        row!(
            "operation",
            "cache phase source/return/caller",
            3,
            CacheOperationPhase<'static>
        ),
        row!(
            "operation",
            "owned entry guard source/return/caller",
            3,
            EntryGuard
        ),
        row!("operation", "frame source/push/return", 3, SwiftFrame),
        row!(
            "operation",
            "selected instruction source/return/caller",
            3,
            SelectedInstruction
        ),
        row!(
            "operation",
            "selected target source/return/caller",
            3,
            Option<u32>
        ),
        row!(
            "operation",
            "view result/caller",
            2,
            Result<FunctionView<'static>, SwiftRunFailure>
        ),
        row!(
            "operation",
            "pin result/caller slot",
            2,
            Option<Result<SwiftFunctionPin, SwiftRunFailure>>
        ),
        row!("operation","release result/caller",2,Result<(),SwiftReleaseFailure>),
        row!(
            "operation",
            "full structural signature pair",
            2,
            SignatureView<'static>
        ),
        row!(
            "operation",
            "return value source/return/caller",
            3,
            Result<Option<Value>, SwiftRunFailure>
        ),
        row!(
            "growth",
            "old/new vector and ticket transfer source/return/caller",
            3,
            GrowthTransfer
        ),
        row!(
            "growth",
            "allocate result/caller",
            2,
            Result<Vec<u8>, SwiftRunFailure>
        ),
        row!("growth","reserve result/caller",2,Result<ReservationTicket,SwiftRunFailure>),
        row!(
            "cleanup",
            "whole owner caller slot",
            1,
            Option<SwiftReactorInstance>
        ),
        row!(
            "cleanup",
            "taken owner and helper transfer",
            2,
            SwiftReactorInstance
        ),
        row!(
            "cleanup",
            "state source/argument transfer",
            2,
            SwiftExecutionState
        ),
        row!(
            "cleanup",
            "tail source/return/caller",
            3,
            ExecutionCleanupTail
        ),
        row!(
            "cleanup",
            "tail result and caller slot",
            2,
            Option<Result<ExecutionCleanupTail, SwiftRunFailure>>
        ),
        row!(
            "cleanup",
            "cache slot source/argument",
            2,
            Option<SwiftFunctionCache>
        ),
        row!(
            "cleanup",
            "cache tail result and caller slot",
            2,
            Option<Result<CacheCleanupTail<'static>, SwiftRunFailure>>
        ),
        row!(
            "cleanup",
            "cache outcome held by executor",
            1,
            Option<SwiftRunFailure>
        ),
        row!("cleanup", "wasi source/argument", 2, AccountedWasi),
        row!("cleanup","wasi released/accumulator/and-input/and-output",4,Result<(),SwiftRunFailure>),
        row!(
            "cleanup",
            "executor outcome held across component drains",
            1,
            Option<SwiftRunFailure>
        ),
        row!(
            "cleanup",
            "external final observation plus copied drain argument",
            2,
            Option<WasiUsage>
        ),
        row!("cleanup", "frame drain source/argument", 2, SwiftFrame),
        row!("cleanup","owned pin plus release rejected wrapper",2,Result<(),SwiftReleaseFailure>),
        row!("cleanup", "state vector source/argument", 2, Vec<Value>),
        row!(
            "cleanup",
            "state ticket source/argument",
            2,
            Option<ReservationTicket>
        ),
        row!(
            "construction",
            "scalar/borrow source/argument/return inventories",
            3,
            ScalarBorrowInventory
        ),
        row!(
            "construction",
            "caller failure/usage outside foundation",
            2,
            CallerDiagnostics
        ),
        row!(
            "operation",
            "scalar/borrow source/argument/return inventories",
            3,
            ScalarBorrowInventory
        ),
        row!(
            "operation",
            "caller failure/usage outside foundation",
            2,
            CallerDiagnostics
        ),
        row!(
            "growth",
            "scalar/borrow source/argument/return inventories",
            3,
            ScalarBorrowInventory
        ),
        row!(
            "growth",
            "caller failure/usage outside foundation",
            2,
            CallerDiagnostics
        ),
        row!(
            "cleanup",
            "scalar/borrow source/argument/return inventories",
            3,
            ScalarBorrowInventory
        ),
        row!(
            "cleanup",
            "caller failure/usage outside foundation",
            2,
            CallerDiagnostics
        ),
    ]
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct ScalarBorrowInventory {
    pub control: &'static mut RuntimeControl,
    pub cache: &'static mut SwiftFunctionCache,
    pub wasi: &'static mut AccountedWasi,
    pub state: &'static mut SwiftExecutionState,
    pub phase: &'static mut ExecutionOperationPhase<'static>,
    pub pin: &'static SwiftFunctionPin,
    pub view: FunctionView<'static>,
    pub initializer: ScalarReader<'static>,
    pub signature: SignatureView<'static>,
    pub values: &'static [Value],
    pub memory: &'static mut [u8],
    pub indices: std::ops::Range<usize>,
    pub cursor: Cursor,
    pub fault: Fault,
    pub capacity: usize,
    pub requested: usize,
    pub observed: usize,
    pub index: usize,
    pub length: usize,
    pub base: usize,
    pub operands: usize,
    pub controls: usize,
    pub frame_count: usize,
    pub value_count: usize,
    pub control_count: usize,
    pub destination: usize,
    pub source: usize,
    pub end: usize,
    pub chunk_end: usize,
    pub copied: usize,
    pub absolute_function: u32,
    pub type_index: u32,
    pub table_index: u32,
    pub branch_depth: u32,
    pub old_pages: u32,
    pub next_pages: u32,
    pub delta_pages: u32,
    pub opcode: u32,
    pub value: Option<Value>,
    pub selected: Operation,
    pub reserve_error: Option<std::collections::TryReserveError>,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct CallerDiagnostics {
    pub failure: Option<SwiftRunFailure>,
    pub usage: Option<SwiftRunUsage>,
    pub observation: Option<WasiUsage>,
}
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) fn phase_bytes(phase: &str) -> Option<usize> {
    terms()
        .iter()
        .filter(|r| r.phase == phase)
        .try_fold(0usize, |sum, r| {
            sum.checked_add(r.count.checked_mul(r.bytes)?)
        })
}
const fn named_bytes(phase: &str) -> Option<usize> {
    let rows = terms();
    let mut total = 0usize;
    let mut index = 0;
    while index < rows.len() {
        let a = rows[index].phase.as_bytes();
        let b = phase.as_bytes();
        let mut same = a.len() == b.len();
        let mut at = 0;
        while same && at < a.len() {
            same = a[at] == b[at];
            at += 1;
        }
        if same {
            let Some(bytes) = rows[index].count.checked_mul(rows[index].bytes) else {
                return None;
            };
            let Some(next) = total.checked_add(bytes) else {
                return None;
            };
            total = next;
        }
        index += 1;
    }
    Some(total)
}
/// No negative subtraction; count nested payload once and every Option tag or
/// containing alignment byte in the exclusive residual. Arena payloads have
/// their separate six tickets; all additional cleanup rows use this same header.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) fn execution_header_bytes() -> Option<usize> {
    EXECUTION_HEADER_BYTES
}
const EXECUTION_HEADER_BYTES: Option<usize> = {
    let nested = size_of::<RuntimeControl>()
        + size_of::<SwiftFunctionCache>()
        + size_of::<AccountedWasi>()
        + size_of::<SwiftExecutionState>();
    match (
        size_of::<SwiftReactorInstance>().checked_sub(nested),
        named_bytes("cleanup"),
    ) {
        (Some(residual), Some(cleanup)) => {
            match residual.checked_add(size_of::<SwiftExecutionState>()) {
                Some(header) => match header.checked_add(cleanup) {
                    Some(header) => {
                        match header.checked_add(size_of::<CleanupPreflightInventory>()) {
                            Some(header) => {
                                match header.checked_add(CONSTRUCTION_POSITIVE_CLEANUP_BYTES) {
                                    Some(header) => {
                                        match header.checked_add(value_operations::PERMANENT_BYTES)
                                        {
                                            Some(header) => match header.checked_add(frame_operations::PERMANENT_BYTES) {
                                                Some(header) => match header.checked_add(frame_operations::control_operations::PERMANENT_BYTES) { Some(header) => match header.checked_add(frame_operations::memory_operations::PERMANENT_BYTES) { Some(header) => match header.checked_add(frame_operations::bulk_memory_operations::PERMANENT_BYTES) {Some(header)=>header.checked_add(frame_operations::memory_growth_operations::PERMANENT_BYTES),None=>None}, None => None }, None => None }, None => None,
                                            },
                                            None => None,
                                        }
                                    }
                                    None => None,
                                }
                            }
                            None => None,
                        }
                    }
                    None => None,
                },
                None => None,
            }
        }
        _ => None,
    }
};

/// Pure checked arena formula; this does not admit, allocate or instantiate.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) fn arena_bytes(
    values: usize,
    controls: usize,
    frames: usize,
    pages: usize,
    table: usize,
    globals: usize,
) -> Option<[usize; 6]> {
    Some([
        values.checked_mul(size_of::<Value>())?,
        controls.checked_mul(size_of::<Control>())?,
        frames.checked_mul(size_of::<SwiftFrame>())?,
        pages.checked_mul(65536)?,
        table.checked_mul(size_of::<Option<u32>>())?,
        globals.checked_mul(size_of::<Value>())?,
    ])
}

const PAGE: usize = 65_536;
const CHUNK: usize = 4_096;

/// Newly named roles, disjoint from the eight original maps. These inventory
/// types are never instantiated; their layouts reserve requested object bytes,
/// not physical stack or allocator overhead. Each repeated position accounts
/// source/argument/return independently, without borrowing containing padding.
struct ConstructionDescriptors {
    memory: Option<MemoryExecutionView>,
    table: Option<TableExecutionView>,
    global: Option<GlobalView<'static>>,
    segment: Option<SegmentExecutionView<'static>>,
    initializer_offset: Option<usize>,
    capacities: [usize; 6],
    requests: Option<[usize; 6]>,
    budget: SwiftRunBudget,
    target_type: Type,
    opcode: u8,
    byte: u8,
    bits: u64,
    shift: u32,
    width: u32,
    signed: i64,
    float32: [u8; 4],
    float64: [u8; 8],
}
struct ConstructionTransfers {
    pair: Option<(RuntimeControl, AdoptedProof)>,
    owned_slot: &'static mut Option<(RuntimeControl, AdoptedProof)>,
    grants: WasiGrants,
    wasi_budget: WasiBudget,
    started: Instant,
    state_phase: Result<ExecutionConstructionPhase<'static>, SwiftRunFailure>,
    cache_phase: Result<CacheConstructionPhase<'static>, SwiftRunFailure>,
    wasi_phase: Result<WasiConstructionPhase<'static>, SwiftRunFailure>,
    reserve: Result<ReservationTicket, SwiftRunFailure>,
    allocate: Result<Vec<Value>, SwiftRunFailure>,
    initialized: Result<(), SwiftRunFailure>,
    constant: Result<Value, SwiftRunFailure>,
    scalar: Result<u64, SwiftRunFailure>,
    end: Option<usize>,
}
/// Names only execution-owned call/borrow/scalar roles. The nested runtime
/// control paths have their separately declared bootstrap dependency below.
struct ConstructionBorrowChain {
    control: [&'static mut RuntimeControl; 6],
    state: [&'static mut SwiftExecutionState; 3],
    cache: [&'static SwiftFunctionCache; 4],
    wasi: [&'static AccountedWasi; 6],
    phase: [&'static mut ExecutionConstructionPhase<'static>; 3],
    reader: [&'static mut ScalarReader<'static>; 3],
    vector: [&'static mut Vec<Value>; 2],
    slice: [&'static [u8]; 4],
    mutable_slice: [&'static mut [u8]; 2],
    index: [usize; 12],
    cursor: [Cursor; 4],
    observation: [Option<WasiUsage>; 2],
    fault: [Fault; 2],
}
struct ConstructionIterationInventory {
    global_range: std::ops::Range<usize>,
    table_range: std::ops::Range<u32>,
    descriptor_range: std::ops::Range<usize>,
    element_range: std::ops::Range<usize>,
    leb_range: std::ops::Range<u32>,
    leb_steps: std::iter::StepBy<std::ops::Range<u32>>,
    float_iter: std::slice::IterMut<'static, u8>,
    float_item: Option<&'static mut u8>,
    descriptor_item: Option<usize>,
    table_item: Option<u32>,
    borrowed_segment: SegmentExecutionView<'static>,
    borrowed_global: GlobalView<'static>,
    typed_result: Result<Value, SwiftRunFailure>,
    signed_result: Result<i64, SwiftRunFailure>,
    unsigned_result: Result<u32, SwiftRunFailure>,
    byte_result: Result<u8, SwiftRunFailure>,
    error: Option<std::collections::TryReserveError>,
    error_callback: (
        &'static mut ExecutionConstructionPhase<'static>,
        &'static usize,
    ),
    descriptor_callback: &'static mut ExecutionConstructionPhase<'static>,
    reader_callback: (
        &'static ScalarReader<'static>,
        &'static mut RuntimeControl,
        &'static AccountedWasi,
        &'static Cursor,
    ),
}
struct CleanupPreflightInventory {
    owner_option: Option<&'static mut SwiftReactorInstance>,
    owner: &'static mut SwiftReactorInstance,
    control_option: Option<&'static mut RuntimeControl>,
    control: &'static mut RuntimeControl,
    wasi_option: Option<&'static AccountedWasi>,
    wasi: &'static AccountedWasi,
    cache_option: Option<&'static SwiftFunctionCache>,
    cache: &'static SwiftFunctionCache,
    state_option: Option<&'static SwiftExecutionState>,
    state: &'static SwiftExecutionState,
    header_option: Option<&'static ReservationTicket>,
    header: &'static ReservationTicket,
    buffer_iter: std::slice::Iter<'static, Option<ReservationTicket>>,
    buffer_item: Option<&'static Option<ReservationTicket>>,
    buffer: &'static Option<ReservationTicket>,
    buffer_ticket: Option<&'static ReservationTicket>,
    cache_usage: super::cache::SwiftCacheUsage,
    cursor_arguments: [Cursor; 2],
    header_error_callback: (&'static mut RuntimeControl, &'static AccountedWasi),
    buffer_error_callback: (&'static mut RuntimeControl, &'static AccountedWasi),
    nonempty: [bool; 4],
}
/// This group must be charged by the foundation before a caller enters either
/// constructor/preparation. The later enlarged phase cannot retroactively cover
/// its own inputs and provenance/admission call chain. Whole groups are a
/// conservative maximum; diagnostic/fault transfers already named by foundation
/// retain those classes and are not reused as smaller borrow slots here.
pub(super) struct ConstructionBootstrapInventory {
    pair_slot: [&'static mut Option<(RuntimeControl, AdoptedProof)>; 2],
    control: [&'static mut RuntimeControl; 8],
    adopted: [&'static AdoptedProof; 3],
    cache: [&'static SwiftFunctionCache; 4],
    wasi: [&'static AccountedWasi; 4],
    cursor: [Cursor; 5],
    grants: [WasiGrants; 3],
    budget: [WasiBudget; 3],
    started: [Instant; 3],
    cache_control: CacheControl<'static>,
    header_option: [Option<&'static ReservationTicket>; 3],
    header: [&'static ReservationTicket; 5],
    observation: [Option<WasiUsage>; 3],
    snapshot_return: [SwiftRunUsage; 2],
    previous_bound: [usize; 4],
    checked_bound: [Option<usize>; 2],
    owner_verdict: [Option<(SwiftCleanupInvariant, &'static str)>; 2],
    ticket_option: Option<&'static ReservationTicket>,
    current: usize,
    requested: usize,
    difference: usize,
    category_next: usize,
    combined_next: usize,
    checked_category: Option<usize>,
    checked_combined: Option<usize>,
    category: SwiftReservationCategory,
    category_usage: &'static SwiftReservationUsage,
    category_mut: &'static mut SwiftReservationUsage,
    reservations: &'static mut SwiftReservations,
    construction_ticket: Option<&'static mut ReservationTicket>,
}
pub(super) const CONSTRUCTION_BOOTSTRAP_BYTES: usize = {
    let base = size_of::<ConstructionBootstrapInventory>();
    match base.checked_add(CONSTRUCTION_POSITIVE_PREFLIGHT_BYTES) {
        Some(value) => match value.checked_add(CONSTRUCTION_POSITIVE_FINAL_BYTES) {
            Some(value) => match value.checked_add(CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES) {
                Some(value) => value,
                None => usize::MAX,
            },
            None => usize::MAX,
        },
        None => usize::MAX,
    }
};
#[cfg(test)]
pub(super) fn print_construction_layouts() {
    println!("construction bootstrap {}", CONSTRUCTION_BOOTSTRAP_BYTES);
    println!(
        "construction descriptors {}",
        size_of::<ConstructionDescriptors>()
    );
    println!(
        "construction transfers {}",
        size_of::<ConstructionTransfers>()
    );
    println!(
        "construction borrows {}",
        size_of::<ConstructionBorrowChain>()
    );
    println!("construction total {}", construction_bytes().unwrap());
    println!(
        "construction iterations {}",
        size_of::<ConstructionIterationInventory>()
    );
}
const BASE_CONSTRUCTION_BYTES: Option<usize> = match named_bytes("construction") {
    Some(base) => match base.checked_add(3 * size_of::<ConstructionDescriptors>()) {
        Some(n) => match n.checked_add(3 * size_of::<ConstructionTransfers>()) {
            Some(n) => match n.checked_add(size_of::<ConstructionBorrowChain>()) {
                Some(n) => n.checked_add(3 * size_of::<ConstructionIterationInventory>()),
                None => None,
            },
            None => None,
        },
        None => None,
    },
    None => None,
};
const CONSTRUCTION_BYTES: Option<usize> = match BASE_CONSTRUCTION_BYTES {
    Some(base) => match base.checked_add(CONSTRUCTION_POSITIVE_ACTIVE_BYTES) {
        Some(value) => {
            value.checked_add(crate::experimental::swift::CONSTRUCTION_POSITIVE_DESCRIPTOR_BYTES)
        }
        None => None,
    },
    None => None,
};
pub(crate) fn construction_bytes() -> Option<usize> {
    CONSTRUCTION_BYTES
}

fn construction_failure(
    control: &mut RuntimeControl,
    wasi: &AccountedWasi,
    cursor: Cursor,
    kind: SwiftRunFailureKind,
    code: &'static str,
) -> SwiftRunFailure {
    control.fail(cursor, Fault::new(kind, code), Some(wasi.usage()))
}
fn layout_failure(
    control: &mut RuntimeControl,
    wasi: &AccountedWasi,
    cursor: Cursor,
) -> SwiftRunFailure {
    construction_failure(
        control,
        wasi,
        cursor,
        SwiftRunFailureKind::Invariant,
        "swift_execution_layout_overflow",
    )
}
fn checked(
    control: &mut RuntimeControl,
    wasi: &AccountedWasi,
    cursor: Cursor,
) -> Result<(), SwiftRunFailure> {
    #[cfg(test)]
    super::execution_tests::construction_checkpoint(control, cursor);
    control.check_with_wasi(cursor, Some(wasi.usage()))
}
fn work(
    control: &mut RuntimeControl,
    wasi: &AccountedWasi,
    cursor: Cursor,
    credits: usize,
) -> Result<(), SwiftRunFailure> {
    checked(control, wasi, cursor)?;
    control.work_with_wasi(Work::Execution, credits as u64, cursor, Some(wasi.usage()))
}
impl SwiftExecutionState {
    pub(crate) fn prepare<'a>(
        control: &'a mut RuntimeControl,
        cache: &'a SwiftFunctionCache,
        wasi: &'a AccountedWasi,
        cursor: Cursor,
    ) -> Result<ExecutionConstructionPhase<'a>, SwiftRunFailure> {
        // The actual WASI pair wins over cache/ordinary checks. No owner moves.
        wasi.checked_usage(control, cursor)?;
        cache.check_owner(control, Some(wasi), cursor)?;
        checked(control, wasi, cursor)?;
        if cache.usage().active_pins != 0 {
            return Err(construction_failure(
                control,
                wasi,
                cursor,
                SwiftRunFailureKind::Invariant,
                "swift_execution_preexisting_pins",
            ));
        }
        let previous_bound = control
            .usage(Some(wasi.usage()))
            .reservations
            .construction
            .current;
        let bound = construction_bytes()
            .and_then(|n| previous_bound.checked_add(n))
            .ok_or_else(|| layout_failure(control, wasi, cursor))?;
        control.enlarge_construction_with_wasi(bound, cursor, Some(wasi.usage()))?;
        Ok(ExecutionConstructionPhase {
            control,
            cache,
            wasi,
            cursor,
            previous_bound,
            constructed: false,
        })
    }
    fn empty() -> Self {
        Self {
            memory: Vec::new(),
            table: Vec::new(),
            globals: Vec::new(),
            values: Vec::new(),
            controls: Vec::new(),
            frames: Vec::new(),
            buffers: std::array::from_fn(|_| None),
            execution_header: None,
            frame_cleanup: const { frame_operations::FrameCleanupState::empty() },
        }
    }
    /// Only this constructor's unpublished State is accepted. Its last fallible
    /// action is the page debit, so every failure here has zero State live counts.
    fn cleanup_unpublished(mut self, control: &mut RuntimeControl, wasi: &AccountedWasi) {
        self.drop_arenas(control, wasi);
        if let Some(header) = self.execution_header.take() {
            let _ = control.drop_reserved_with_wasi(self, header, Some(wasi.usage()));
        }
    }
    fn drop_arenas(&mut self, control: &mut RuntimeControl, wasi: &AccountedWasi) {
        macro_rules! release {
            ($field:ident, $index:literal) => {{
                if let Some(ticket) = self.buffers[$index].take() {
                    let _ = control.drop_reserved_with_wasi(
                        take(&mut self.$field),
                        ticket,
                        Some(wasi.usage()),
                    );
                } else {
                    drop(take(&mut self.$field));
                }
            }};
        }
        release!(values, 0);
        release!(controls, 1);
        release!(frames, 2);
        release!(memory, 3);
        release!(table, 4);
        release!(globals, 5);
    }
}
impl ExecutionConstructionPhase<'_> {
    pub(crate) fn construct(&mut self) -> Result<SwiftExecutionState, SwiftRunFailure> {
        if std::mem::replace(&mut self.constructed, true) {
            return Err(construction_failure(
                self.control,
                self.wasi,
                self.cursor,
                SwiftRunFailureKind::Invariant,
                "swift_execution_construct_once",
            ));
        }
        let mut partial = PartialState {
            state: SwiftExecutionState::empty(),
            next_arena: 0,
        };
        match self.construct_partial(&mut partial) {
            Ok(()) => Ok(partial.state),
            Err(failure) => {
                partial.state.cleanup_unpublished(self.control, self.wasi);
                Err(failure)
            }
        }
    }
    fn construct_partial(&mut self, partial: &mut PartialState) -> Result<(), SwiftRunFailure> {
        checked(self.control, self.wasi, self.cursor)?;
        let budget = self.control.budget();
        let memory = self
            .cache
            .proof()
            .execution_memory()
            .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
        if memory.minimum > budget.memory_pages {
            let mut fault = Fault::new(
                SwiftRunFailureKind::ResourceExhausted,
                "swift_execution_memory_minimum",
            );
            fault.resource = Some(SwiftRunResource::MemoryPages);
            fault.attempted = memory.minimum as u64;
            fault.limit = budget.memory_pages as u64;
            return Err(self
                .control
                .fail(self.cursor, fault, Some(self.wasi.usage())));
        }
        let table = self
            .cache
            .proof()
            .execution_table()
            .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
        let globals = self.cache.proof().execution_global_count();
        let requests = arena_bytes(
            budget.values,
            budget.controls,
            budget.frames,
            memory.minimum as usize,
            table.minimum as usize,
            globals,
        )
        .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
        let header = execution_header_bytes()
            .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
        partial.state.execution_header = Some(self.control.admit_with_wasi(
            SwiftReservationCategory::State,
            header,
            self.cursor,
            Some(self.wasi.usage()),
        )?);
        macro_rules! arena {
            ($field:ident, $index:literal, $capacity:expr) => {{
                partial.state.buffers[$index] = Some(self.control.admit_with_wasi(
                    SwiftReservationCategory::State,
                    requests[$index],
                    self.cursor,
                    Some(self.wasi.usage()),
                )?);
                self.reserve(&mut partial.state.$field, $capacity)?;
                partial.next_arena += 1;
            }};
        }
        arena!(values, 0, budget.values);
        arena!(controls, 1, budget.controls);
        arena!(frames, 2, budget.frames);
        arena!(memory, 3, requests[3]);
        arena!(table, 4, table.minimum as usize);
        arena!(globals, 5, globals);
        let credits = requests[3]
            .checked_add(table.minimum as usize)
            .and_then(|n| n.checked_add(globals))
            .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
        work(self.control, self.wasi, self.cursor, credits)?;
        while partial.state.memory.len() < requests[3] {
            checked(self.control, self.wasi, self.cursor)?;
            let end = (partial.state.memory.len() + CHUNK).min(requests[3]);
            partial.state.memory.resize(end, 0);
        }
        for _ in 0..table.minimum {
            checked(self.control, self.wasi, self.cursor)?;
            partial.state.table.push(None);
        }
        for index in 0..globals {
            work(self.control, self.wasi, self.cursor, 16)?;
            let global = self
                .cache
                .proof()
                .execution_global(index)
                .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
            let offset = self
                .cache
                .proof()
                .execution_global_initializer_offset(index)
                .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
            let mut reader = ScalarReader {
                bytes: global.initializer,
                at: 0,
                absolute_offset: offset,
            };
            let value = reader.constant(global.ty, self.control, self.wasi, self.cursor)?;
            partial.state.globals.push(value);
        }
        self.initialize_segments(&mut partial.state)?;
        // Last fallible operation. No publication check/effect follows a failure.
        self.control.add_live_with_wasi(
            Live::MemoryPages,
            memory.minimum as usize,
            self.cursor,
            Some(self.wasi.usage()),
        )
    }
    fn reserve<T>(&mut self, values: &mut Vec<T>, requested: usize) -> Result<(), SwiftRunFailure> {
        checked(self.control, self.wasi, self.cursor)?;
        values.try_reserve_exact(requested).map_err(|_| {
            let mut fault = Fault::new(
                SwiftRunFailureKind::Allocation,
                "swift_execution_allocation",
            );
            fault.attempted = requested as u64;
            self.control
                .fail(self.cursor, fault, Some(self.wasi.usage()))
        })?;
        #[cfg(test)]
        let observed = super::execution_tests::construction_capacity(values.capacity());
        #[cfg(not(test))]
        let observed = values.capacity();
        self.control.exact_capacity_with_wasi(
            requested,
            observed,
            self.cursor,
            Some(self.wasi.usage()),
        )?;
        checked(self.control, self.wasi, self.cursor)
    }
    fn initialize_segments(
        &mut self,
        state: &mut SwiftExecutionState,
    ) -> Result<(), SwiftRunFailure> {
        // All ranges, in the specified order, precede the first payload effect.
        for index in 0..self.cache.proof().execution_data_count() {
            work(self.control, self.wasi, self.cursor, 1)?;
            let segment = self
                .cache
                .proof()
                .execution_data(index)
                .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
            self.range(segment, state.memory.len(), "swift_execution_data_bounds")?;
            if segment.count as usize != segment.encoded_payload.len() {
                return Err(self.segment_failure(segment, "swift_execution_data_count"));
            }
        }
        for index in 0..self.cache.proof().execution_element_count() {
            work(self.control, self.wasi, self.cursor, 1)?;
            let segment = self
                .cache
                .proof()
                .execution_element(index)
                .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
            self.range(segment, state.table.len(), "swift_execution_element_bounds")?;
        }
        for index in 0..self.cache.proof().execution_data_count() {
            let segment = self
                .cache
                .proof()
                .execution_data(index)
                .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
            work(
                self.control,
                self.wasi,
                self.cursor,
                segment.encoded_payload.len(),
            )?;
            let mut copied = 0;
            while copied < segment.encoded_payload.len() {
                let cursor = Cursor {
                    offset: Some(segment.payload_offset + copied),
                    ..self.cursor
                };
                checked(self.control, self.wasi, cursor)?;
                let end = (copied + CHUNK).min(segment.encoded_payload.len());
                let destination = segment.destination as usize + copied;
                state.memory[destination..destination + end - copied]
                    .copy_from_slice(&segment.encoded_payload[copied..end]);
                copied = end;
            }
            checked(
                self.control,
                self.wasi,
                Cursor {
                    offset: Some(segment.payload_offset + copied),
                    ..self.cursor
                },
            )?;
        }
        for index in 0..self.cache.proof().execution_element_count() {
            let segment = self
                .cache
                .proof()
                .execution_element(index)
                .ok_or_else(|| layout_failure(self.control, self.wasi, self.cursor))?;
            work(
                self.control,
                self.wasi,
                self.cursor,
                segment.encoded_payload.len(),
            )?;
            let mut reader = ScalarReader {
                bytes: segment.encoded_payload,
                at: 0,
                absolute_offset: segment.payload_offset,
            };
            for slot in 0..segment.count as usize {
                let function = reader.unsigned(self.control, self.wasi, self.cursor)?;
                if self.cache.proof().execution_signature(function).is_none() {
                    return Err(reader.failure(
                        self.control,
                        self.wasi,
                        self.cursor,
                        "swift_execution_element_function",
                    ));
                }
                state.table[segment.destination as usize + slot] = Some(function);
            }
            reader.end(self.control, self.wasi, self.cursor)?;
        }
        checked(self.control, self.wasi, self.cursor)
    }
    fn range(
        &mut self,
        segment: SegmentExecutionView<'_>,
        length: usize,
        code: &'static str,
    ) -> Result<(), SwiftRunFailure> {
        if (segment.destination as usize)
            .checked_add(segment.count as usize)
            .is_none_or(|end| end > length)
        {
            return Err(self.segment_failure(segment, code));
        }
        Ok(())
    }
    fn segment_failure(
        &mut self,
        segment: SegmentExecutionView<'_>,
        code: &'static str,
    ) -> SwiftRunFailure {
        construction_failure(
            self.control,
            self.wasi,
            Cursor {
                offset: Some(segment.payload_offset),
                ..self.cursor
            },
            SwiftRunFailureKind::GuestTrap,
            code,
        )
    }
    pub(crate) fn complete<T>(self, returned_phase_storage: T) -> Result<(), SwiftRunFailure> {
        let Self {
            control,
            wasi,
            previous_bound,
            ..
        } = self;
        control.end_construction_phase_with_wasi(
            returned_phase_storage,
            previous_bound,
            Some(wasi.usage()),
        )
    }
}

impl ScalarReader<'_> {
    fn failure(
        &self,
        control: &mut RuntimeControl,
        wasi: &AccountedWasi,
        cursor: Cursor,
        code: &'static str,
    ) -> SwiftRunFailure {
        construction_failure(
            control,
            wasi,
            Cursor {
                offset: Some(self.absolute_offset + self.at),
                ..cursor
            },
            SwiftRunFailureKind::Invariant,
            code,
        )
    }
    fn byte(
        &mut self,
        control: &mut RuntimeControl,
        wasi: &AccountedWasi,
        cursor: Cursor,
    ) -> Result<u8, SwiftRunFailure> {
        checked(
            control,
            wasi,
            Cursor {
                offset: Some(self.absolute_offset + self.at),
                ..cursor
            },
        )?;
        let byte = self
            .bytes
            .get(self.at)
            .copied()
            .ok_or_else(|| self.failure(control, wasi, cursor, "swift_execution_scalar_eof"))?;
        self.at += 1;
        Ok(byte)
    }
    fn unsigned(
        &mut self,
        control: &mut RuntimeControl,
        wasi: &AccountedWasi,
        cursor: Cursor,
    ) -> Result<u32, SwiftRunFailure> {
        let mut bits = 0u32;
        for shift in (0..35).step_by(7) {
            let byte = self.byte(control, wasi, cursor)?;
            if shift == 28 && byte & 0xf0 != 0 {
                self.at -= 1;
                return Err(self.failure(control, wasi, cursor, "swift_execution_scalar_u32"));
            }
            bits |= ((byte & 0x7f) as u32) << shift;
            if byte & 0x80 == 0 {
                return Ok(bits);
            }
        }
        Err(self.failure(control, wasi, cursor, "swift_execution_scalar_u32"))
    }
    fn signed(
        &mut self,
        width: u32,
        control: &mut RuntimeControl,
        wasi: &AccountedWasi,
        cursor: Cursor,
    ) -> Result<i64, SwiftRunFailure> {
        let mut bits = 0u64;
        let mut shift = 0;
        loop {
            let byte = self.byte(control, wasi, cursor)?;
            let remaining = width - shift;
            if remaining < 7 {
                let mask = (0x7f_u8 << remaining) & 0x7f;
                let sign = byte & (1 << (remaining - 1)) != 0;
                if byte & 0x80 != 0 || byte & mask != if sign { mask } else { 0 } {
                    self.at -= 1;
                    return Err(self.failure(
                        control,
                        wasi,
                        cursor,
                        "swift_execution_scalar_signed",
                    ));
                }
            }
            bits |= ((byte & 0x7f) as u64) << shift;
            shift += 7;
            if byte & 0x80 == 0 {
                if shift < 64 && byte & 0x40 != 0 {
                    bits |= u64::MAX << shift;
                }
                return Ok(bits as i64);
            }
        }
    }
    fn constant(
        &mut self,
        ty: Type,
        control: &mut RuntimeControl,
        wasi: &AccountedWasi,
        cursor: Cursor,
    ) -> Result<Value, SwiftRunFailure> {
        let value = match self.byte(control, wasi, cursor)? {
            0x41 => Value::I32(self.signed(32, control, wasi, cursor)? as i32),
            0x42 => Value::I64(self.signed(64, control, wasi, cursor)?),
            0x43 => {
                let mut bytes = [0; 4];
                for byte in &mut bytes {
                    *byte = self.byte(control, wasi, cursor)?;
                }
                Value::F32(u32::from_le_bytes(bytes))
            }
            0x44 => {
                let mut bytes = [0; 8];
                for byte in &mut bytes {
                    *byte = self.byte(control, wasi, cursor)?;
                }
                Value::F64(u64::from_le_bytes(bytes))
            }
            _ => {
                self.at -= 1;
                return Err(self.failure(control, wasi, cursor, "swift_execution_scalar_opcode"));
            }
        };
        if value.ty() != ty {
            self.at = 0;
            return Err(self.failure(control, wasi, cursor, "swift_execution_scalar_type"));
        }
        if self.byte(control, wasi, cursor)? != 0x0b {
            self.at -= 1;
            return Err(self.failure(control, wasi, cursor, "swift_execution_scalar_end"));
        }
        self.end(control, wasi, cursor)?;
        Ok(value)
    }
    fn end(
        &self,
        control: &mut RuntimeControl,
        wasi: &AccountedWasi,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        checked(
            control,
            wasi,
            Cursor {
                offset: Some(self.absolute_offset + self.at),
                ..cursor
            },
        )?;
        if self.at != self.bytes.len() {
            return Err(self.failure(control, wasi, cursor, "swift_execution_scalar_trailing"));
        }
        Ok(())
    }
}
#[cfg(test)]
pub(super) fn scalar_constant_probe(
    bytes: &[u8],
    absolute_offset: usize,
    ty: Type,
    control: &mut RuntimeControl,
    wasi: &AccountedWasi,
) -> Result<Value, SwiftRunFailure> {
    ScalarReader {
        bytes,
        at: 0,
        absolute_offset,
    }
    .constant(
        ty,
        control,
        wasi,
        Cursor {
            stage: SwiftRunStage::Initialization,
            function: None,
            offset: Some(absolute_offset),
        },
    )
}

impl SwiftReactorInstance {
    /// The caller retains exact ownership if bootstrap provenance/admission
    /// rejects. Once taken, any failure destroys every acquired component.
    pub(crate) fn construct(
        owned: &mut Option<(RuntimeControl, AdoptedProof)>,
        grants: WasiGrants,
        wasi_budget: WasiBudget,
        started: Instant,
        cursor: Cursor,
    ) -> Result<Self, ConstructionFailure> {
        let (control, adopted) = owned
            .as_mut()
            .expect("private constructor requires an adopted owner slot");
        control
            .check_adopted_owner(adopted, cursor, None)
            .map_err(ConstructionFailure::Rejected)?;
        let previous_bound = control.usage(None).reservations.construction.current;
        let bound = construction_bytes()
            .and_then(|n| previous_bound.checked_add(n))
            .ok_or_else(|| {
                control.fail(
                    cursor,
                    Fault::new(
                        SwiftRunFailureKind::Invariant,
                        "swift_execution_layout_overflow",
                    ),
                    None,
                )
            })
            .map_err(ConstructionFailure::Rejected)?;
        control
            .enlarge_construction(bound, cursor)
            .map_err(ConstructionFailure::Rejected)?;
        // No owning transfer or partial builder exists before enlargement.
        let (control, adopted) = owned.take().expect("preflight retained adopted owner");
        let mut partial = PartialInstance {
            control: Some(control),
            cache: None,
            wasi: None,
            state: None,
        };
        let result = partial.construct(adopted, grants, wasi_budget, started, cursor);
        if let Err(failure) = result {
            return Err(ConstructionFailure::Cleanup(
                partial.cleanup_failed(previous_bound, failure),
            ));
        }
        let mut instance = Self {
            control: partial.control.take(),
            cache: partial.cache.take(),
            wasi: partial.wasi.take(),
            state: partial.state.take(),
            lifecycle: Lifecycle::Uninitialized,
        };
        // Every partial/ordinary phase has ended before the exact outer restore.
        #[cfg(test)]
        let previous_bound = super::execution_tests::construction_restore_bound(previous_bound);
        if let Err(failure) = instance
            .control
            .as_mut()
            .unwrap()
            .end_construction_phase_with_wasi(
                (partial, result),
                previous_bound,
                instance.wasi.as_ref().map(AccountedWasi::usage),
            )
        {
            // A restore fault changes no component provenance. Keep the owner
            // charged while draining those exact components and return only
            // copied diagnostics. An invalid construction ticket remains charged.
            return Err(ConstructionFailure::Cleanup(
                Self::cleanup_after_restore_failure(instance, previous_bound, failure),
            ));
        }
        Ok(instance)
    }
    fn cleanup_after_restore_failure(
        instance: Self,
        previous_bound: usize,
        _: SwiftRunFailure,
    ) -> ConstructionCleanupTail {
        let mut owned = Some(instance);
        let mut returned = Some(Self::cleanup_owned(&mut owned));
        let tail = returned
            .take()
            .expect("one cleanup return")
            .expect("restore cannot change component provenance");
        drop((owned, returned));
        ConstructionCleanupTail {
            tail,
            previous_bound,
        }
    }
    /// Bounded construction cleanup only. Populated interpreter frames and live
    /// values/controls are rejected intact until their separate unwind slice.
    pub(crate) fn cleanup_owned(
        owned: &mut Option<Self>,
    ) -> Result<ExecutionCleanupTail, SwiftRunFailure> {
        {
            let owner = owned
                .as_mut()
                .expect("private cleanup requires an owned slot");
            let control = owner.control.as_mut().expect("owned control");
            let wasi = owner.wasi.as_ref().expect("owned WASI");
            wasi.checked_usage(control, cleanup_cursor())?;
            owner.cache.as_ref().expect("owned cache").check_owner(
                control,
                Some(wasi),
                cleanup_cursor(),
            )?;
            let state = owner.state.as_ref().expect("owned State");
            let header = state.execution_header.as_ref().ok_or_else(|| {
                construction_failure(
                    control,
                    wasi,
                    cleanup_cursor(),
                    SwiftRunFailureKind::Invariant,
                    "swift_execution_missing_header",
                )
            })?;
            control.check_reservation_owner(header, cleanup_cursor(), Some(wasi.usage()))?;
            for ticket in &state.buffers {
                let ticket = ticket.as_ref().ok_or_else(|| {
                    construction_failure(
                        control,
                        wasi,
                        cleanup_cursor(),
                        SwiftRunFailureKind::Invariant,
                        "swift_execution_missing_buffer",
                    )
                })?;
                control.check_reservation_owner(ticket, cleanup_cursor(), Some(wasi.usage()))?;
            }
            frame_operations::original_owners(
                control,
                owner.cache.as_ref().unwrap(),
                wasi,
                state,
                cleanup_cursor(),
            )?;
            let live = control.usage(Some(wasi.usage())).live;
            if !state.frame_cleanup.is_empty()
                || live.values.current != 0
                || live.controls.current != 0
                || live.frames.current != 0
                || live.active_pins.current != 0
                || !state.frames.is_empty()
                || !state.values.is_empty()
                || !state.controls.is_empty()
                || owner.cache.as_ref().unwrap().usage().active_pins != 0
            {
                return Err(construction_failure(
                    control,
                    wasi,
                    cleanup_cursor(),
                    SwiftRunFailureKind::Invariant,
                    "swift_execution_cleanup_nonempty",
                ));
            }
        }
        let mut owner = owned.take().expect("all component provenance retained");
        owner.lifecycle = Lifecycle::Terminal;
        let mut control = owner.control.take().unwrap();
        let wasi = owner.wasi.take().unwrap();
        let mut state = owner.state.take().unwrap();
        let pages = state.memory.len() / PAGE;
        state.drop_arenas(&mut control, &wasi);
        let _ = control.remove_live_with_wasi(Live::MemoryPages, pages, Some(wasi.usage()));
        let header = state.execution_header.take();
        // State and its empty Vec handles end while the one header stays live.
        drop(state);
        let mut outcome = None;
        match SwiftFunctionCache::cleanup(&mut owner.cache, &mut control, Some(&wasi)) {
            Ok(tail) => tail.complete(owner.cache.take(), &mut outcome),
            Err(failure) => {
                outcome = Some(failure);
            }
        }
        let final_wasi = Some(wasi.usage());
        let _ = wasi.cleanup(&mut control);
        drop(owner);
        let failure = control.record_cleanup(final_wasi).or(outcome);
        Ok(ExecutionCleanupTail {
            control,
            header,
            final_wasi,
            failure,
        })
    }
}
fn cleanup_cursor() -> Cursor {
    Cursor {
        stage: SwiftRunStage::Cleanup,
        function: None,
        offset: None,
    }
}
impl PartialInstance {
    fn construct(
        &mut self,
        adopted: AdoptedProof,
        grants: WasiGrants,
        wasi_budget: WasiBudget,
        started: Instant,
        cursor: Cursor,
    ) -> Result<(), SwiftRunFailure> {
        let control = self.control.as_mut().unwrap();
        match SwiftFunctionCache::prepare(control, None, &adopted, cursor) {
            Ok(mut phase) => {
                let mut returned = Some(phase.construct(adopted));
                let failure = match returned.take().unwrap() {
                    Ok(cache) => {
                        self.cache = Some(cache);
                        None
                    }
                    Err(error) => {
                        // The same-owner adopted pair passed bootstrap. Repeated
                        // construction is impossible on this fresh local phase.
                        debug_assert!(error.rejected_adopted.is_none());
                        Some(error.failure)
                    }
                };
                phase.complete(returned)?;
                if let Some(failure) = failure {
                    return Err(failure);
                }
            }
            Err(failure) => {
                let _ = control.drop_proof(adopted);
                return Err(failure);
            }
        }
        {
            let mut phase = AccountedWasi::prepare(control, cursor)?;
            let mut returned = Some(phase.construct(grants, wasi_budget, started, cursor));
            let result = returned.take().unwrap();
            match result {
                Ok(wasi) => self.wasi = Some(wasi),
                Err(failure) => {
                    phase.complete()?;
                    return Err(failure);
                }
            }
            phase.complete()?;
        }
        {
            let mut phase = SwiftExecutionState::prepare(
                control,
                self.cache.as_ref().unwrap(),
                self.wasi.as_ref().unwrap(),
                cursor,
            )?;
            let mut returned = Some(phase.construct());
            let failure = match returned.take().unwrap() {
                Ok(state) => {
                    self.state = Some(state);
                    None
                }
                Err(failure) => Some(failure),
            };
            phase.complete(returned)?;
            if let Some(failure) = failure {
                return Err(failure);
            }
        }
        Ok(())
    }
    fn cleanup_failed(
        mut self,
        previous_bound: usize,
        failure: SwiftRunFailure,
    ) -> ConstructionCleanupTail {
        let mut control = self.control.take().unwrap();
        let mut header = None;
        if let Some(mut state) = self.state.take() {
            let wasi = self.wasi.as_ref().unwrap();
            let pages = state.memory.len() / PAGE;
            state.drop_arenas(&mut control, wasi);
            let _ = control.remove_live_with_wasi(Live::MemoryPages, pages, Some(wasi.usage()));
            header = state.execution_header.take();
            drop(state);
        }
        let mut outcome = None;
        if self.cache.is_some() {
            match SwiftFunctionCache::cleanup(&mut self.cache, &mut control, self.wasi.as_ref()) {
                Ok(tail) => tail.complete(self.cache.take(), &mut outcome),
                Err(error) => {
                    outcome = Some(error);
                }
            }
        }
        let final_wasi = self.wasi.as_ref().map(AccountedWasi::usage);
        if let Some(wasi) = self.wasi.take() {
            let _ = wasi.cleanup(&mut control);
        }
        // Keep the outer envelope through the whole constructor error return.
        // The caller supplies its possible-owner slots to unit completion.
        drop(self);
        let tail = ExecutionCleanupTail {
            control,
            header,
            final_wasi,
            failure: outcome.or(Some(failure)),
        };
        ConstructionCleanupTail {
            tail,
            previous_bound,
        }
    }
}

// Frozen positive exact-type supplement; independently reviewed binding map is
// verification/swift-executor-construction-independent-review/candidate2-api/positive-accounting-map.json.
// Independent positive named authored-object/callsite accounting.
// Class array indices map one-to-one to positive-accounting-map.json bindings.
// Every old inventory remains charged. No phase padding or diagnostic slot is reused.
#[allow(dead_code)]
// Retain each exact mapped tuple identity in this const-only inventory.
#[allow(clippy::type_complexity)]
pub(crate) struct ConstructionPositivePreflight {
    class_0: [bool; 24],
    class_1: [&'static crate::execute::Cancellation; 3],
    class_2: [&'static std::sync::atomic::AtomicBool; 2],
    class_3: [&'static std::sync::Arc<std::sync::atomic::AtomicBool>; 2],
    class_4: [std::sync::atomic::Ordering; 2],
    class_5: [std::result::Result<
        std::option::Option<crate::experimental_wasi::WasiUsage>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 3],
    class_6: [&'static mut super::control::RuntimeControl; 37],
    class_7: [Option<&'static AccountedWasi>; 3],
    class_8: [super::control::Cursor; 38],
    class_9: [std::option::Option<
        std::result::Result<
            crate::experimental_wasi::WasiUsage,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 2],
    class_10: [(
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_swift_reactor::control::Cursor,
    ); 6],
    class_11: [&'static crate::experimental_swift_reactor::control::Cursor; 8],
    class_12: [std::option::Option<crate::experimental_wasi::WasiUsage>; 28],
    class_13: [&'static CacheControl<'static>; 1],
    class_14: [std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>; 6],
    class_15: [crate::experimental_swift_reactor::control::SwiftRunFailure; 19],
    class_16: [&'static mut CacheControl<'static>; 3],
    class_17: [crate::experimental::cache::CacheFailureKind; 3],
    class_18: [&'static str; 21],
    class_19: [crate::experimental_swift_reactor::control::SwiftRunFailureKind; 27],
    class_20: [isize; 24],
    class_21: [crate::experimental_swift_reactor::control::Cursor; 14],
    class_22: [crate::experimental_swift_reactor::control::Fault; 28],
    class_23: [&'static crate::experimental_swift_reactor::cache::CacheControl<'static>; 4],
    class_24: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl; 17],
    class_25:
        [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>; 24],
    class_26: [&'static SwiftFunctionCache; 7],
    class_27: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        std::option::Option<crate::experimental_wasi::WasiUsage>,
    >; 1],
    class_28: [std::result::Result<
        std::convert::Infallible,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 22],
    class_29: [&'static crate::experimental_swift_reactor::control::ReservationTicket; 9],
    class_30: [std::option::Option<
        &'static crate::experimental_swift_reactor::control::ReservationTicket,
    >; 4],
    class_31: [&'static std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 6],
    class_32: [&'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>; 2],
    class_33: [crate::experimental_swift_reactor::cache::CacheControl<'static>; 1],
    class_34: [crate::experimental_swift_reactor::cache::SwiftCacheUsage; 2],
    class_35: [&'static crate::experimental_swift_reactor::control::SwiftReservationUsage; 11],
    class_36: [&'static super::control::SwiftReservations; 1],
    class_37: [super::control::SwiftReservationCategory; 8],
    class_38: [&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage; 10],
    class_39: [&'static mut super::control::SwiftReservations; 1],
    class_40: [super::control::SwiftRunFailureKind; 3],
    class_41:
        [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>; 3],
    class_42: [std::option::Option<usize>; 24],
    class_43: [std::option::Option<crate::experimental_wasi::WasiFailure>; 2],
    class_44: [std::option::Option<u32>; 3],
    class_45: [super::control::Fault; 2],
    class_46: [super::control::SwiftRunResource; 1],
    class_47: [u64; 32],
    class_48: [crate::experimental_swift_reactor::control::SwiftRunUsage; 4],
    class_49: [&'static super::control::RuntimeControl; 3],
    class_50: [Option<WasiUsage>; 18],
    class_51: [std::time::Instant; 6],
    class_52: [crate::experimental_swift_reactor::control::SwiftReservations; 1],
    class_53: [crate::experimental_swift_reactor::control::SwiftLiveUsage; 1],
    class_54:
        [std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>; 1],
    class_55: [std::time::Duration; 5],
    class_56: [&'static std::time::Instant; 8],
    class_57: [crate::experimental_swift_reactor::control::SwiftDeadlineOrigin; 2],
    class_58: [crate::experimental::swift::SwiftValidationUsage; 1],
    class_59: [crate::experimental_swift_reactor::control::SwiftRunStage; 1],
    class_60: [&'static crate::experimental_swift_reactor::control::RuntimeControl; 10],
    class_61: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>; 1],
    class_62: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>; 1],
    class_63: [usize; 59],
    class_64: [std::result::Result<
        (usize, usize),
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 3],
    class_65: [&'static crate::experimental_swift_reactor::control::SwiftReservations; 4],
    class_66: [(&'static usize,); 12],
    class_67: [&'static usize; 8],
    class_68: [crate::experimental_swift_reactor::control::SwiftRunResource; 4],
    class_69: [(usize, usize); 2],
    class_70: [(); 5],
    class_71: [&'static mut crate::experimental_swift_reactor::control::SwiftReservations; 2],
    class_72: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 6],
    class_73: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        usize,
    >; 2],
    class_74:
        [std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>;
            6],
    class_75: [(
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_swift_reactor::control::Cursor,
        &'static std::option::Option<crate::experimental_wasi::WasiUsage>,
    ); 3],
    class_76: [&'static std::option::Option<crate::experimental_wasi::WasiUsage>; 2],
    class_77: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        (usize, usize),
    >; 1],
    class_78: [crate::experimental_swift_reactor::control::SwiftReservationCategory; 6],
    class_79: [(usize, bool); 1],
    class_80: [&'static mut crate::experimental_swift_reactor::control::ReservationTicket; 1],
    class_81: [std::option::Option<
        &'static mut crate::experimental_swift_reactor::control::ReservationTicket,
    >; 2],
    class_82: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 2],
    class_83: [&'static super::control::AdoptedProof; 1],
    class_84: [&'static super::control::ReservationTicket; 3],
    class_85: [std::option::Option<(
        crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
        &'static str,
    )>; 1],
    class_86: [(
        crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
        &'static str,
    ); 2],
    class_87: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 4],
    class_88: [&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 1],
    class_89: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    >; 2],
    class_90: [std::result::Result<u64, std::num::TryFromIntError>; 2],
    class_91: [u128; 2],
    class_92: [&'static std::time::Duration; 2],
    class_93: [&'static AccountedWasi; 16],
    class_94: [crate::experimental_wasi::WasiUsage; 9],
    class_95: [std::result::Result<
        crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 1],
    class_96: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental_wasi::WasiUsage,
    >; 1],
    class_97: [std::result::Result<
        crate::experimental_wasi::WasiUsage,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 4],
    class_98: [(
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_wasi::accounted::AccountedWasi,
        &'static crate::experimental_swift_reactor::control::Cursor,
    ); 3],
    class_99:
        [crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>; 1],
    class_100: [std::result::Result<
        crate::experimental_swift_reactor::execution::SwiftReactorInstance,
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 1],
    class_101:
        [&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>; 2],
    class_102: [WasiGrants; 1],
    class_103: [WasiBudget; 1],
    class_104: [Instant; 1],
    class_105: [&'static mut crate::experimental_swift_reactor::control::AdoptedProof; 1],
    class_106: [&'static mut (
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    ); 1],
    class_107: [std::option::Option<&'static mut (
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    )>; 2],
    class_108: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::execution::ConstructionFailure,
        >,
    >; 2],
    class_109: [std::result::Result<
        (),
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 4],
    class_110: [&'static crate::experimental_swift_reactor::control::AdoptedProof; 2],
    class_111: [std::result::Result<
        std::convert::Infallible,
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 6],
    class_112: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::execution::ConstructionFailure,
        >,
        usize,
    >; 1],
    class_113: [std::result::Result<
        usize,
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 2],
    class_114: [std::option::Option<(
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    )>; 1],
    class_115: [&'static crate::experimental_wasi::WasiContext; 7],
    class_116: [(&'static crate::experimental_wasi::accounted::AccountedWasi,); 3],
    class_117: [crate::experimental_swift_reactor::execution::ConstructionFailure; 1],
    class_118: [super::control::SwiftRunFailure; 1],
    class_119: [&'static crate::experimental_wasi::accounted::AccountedWasi; 3],
    class_120: [Result<SwiftReactorInstance, ConstructionFailure>; 2],
    class_121: [Option<Result<SwiftReactorInstance, ConstructionFailure>>; 2],
    class_122: [ConstructionFailure; 1],
    class_123: [ConstructionCleanupTail; 1],
    class_124: [(
        Option<(RuntimeControl, AdoptedProof)>,
        Option<Result<SwiftReactorInstance, ConstructionFailure>>,
    ); 1],
}
pub(crate) const CONSTRUCTION_POSITIVE_PREFLIGHT_BYTES: usize =
    std::mem::size_of::<ConstructionPositivePreflight>();
#[allow(dead_code)]
// Retain each exact mapped tuple identity in this const-only inventory.
#[allow(clippy::type_complexity)]
pub(crate) struct ConstructionPositiveActive {
    class_0: [std::result::Result<
        crate::experimental_swift_reactor::control::ReservationTicket,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 15],
    class_1: [&'static mut super::control::RuntimeControl; 84],
    class_2: [super::control::SwiftReservationCategory; 3],
    class_3: [usize; 319],
    class_4: [super::control::Cursor; 47],
    class_5: [Option<WasiUsage>; 42],
    class_6: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 48],
    class_7:
        [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>; 138],
    class_8: [isize; 135],
    class_9: [std::result::Result<
        std::convert::Infallible,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 160],
    class_10: [bool; 89],
    class_11: [crate::experimental_swift_reactor::control::SwiftRunFailure; 60],
    class_12: [crate::experimental_swift_reactor::control::Fault; 39],
    class_13: [crate::experimental_swift_reactor::control::SwiftRunFailureKind; 36],
    class_14: [crate::experimental_swift_reactor::control::SwiftRunResource; 17],
    class_15: [u64; 48],
    class_16: [(u64, bool); 1],
    class_17: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        (usize, usize),
    >; 1],
    class_18: [std::result::Result<
        (usize, usize),
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_19: [(usize, usize); 1],
    class_20: [(); 29],
    class_21: [(usize, bool); 25],
    class_22: [crate::experimental_swift_reactor::control::ReservationTicket; 22],
    class_23: [&'static str; 51],
    class_24: [Option<Result<SwiftExecutionState, SwiftRunFailure>>; 5],
    class_25: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 22],
    class_26: [&'static crate::experimental_swift_reactor::control::ReservationTicket; 2],
    class_27: [std::option::Option<
        &'static crate::experimental_swift_reactor::control::ReservationTicket,
    >; 2],
    class_28: [&'static std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 4],
    class_29: [&'static crate::experimental_swift_reactor::control::SwiftReservationCategory; 8],
    class_30: [std::option::Option<usize>; 59],
    class_31: [(std::option::Option<usize>, std::option::Option<usize>); 2],
    class_32: [&'static mut crate::experimental_swift_reactor::control::ReservationTicket; 2],
    class_33: [std::option::Option<
        &'static mut crate::experimental_swift_reactor::control::ReservationTicket,
    >; 4],
    class_34: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 20],
    class_35: [(PartialInstance, Result<(), SwiftRunFailure>); 2],
    class_36: [Vec<Value>; 2],
    class_37: [super::control::ReservationTicket; 13],
    class_38: [Vec<Control>; 2],
    class_39: [Vec<SwiftFrame>; 2],
    class_40: [Vec<u8>; 2],
    class_41: [Vec<Option<u32>>; 2],
    class_42: [SwiftExecutionState; 3],
    class_43: [&'static crate::experimental_swift_reactor::control::SwiftReservationUsage; 1],
    class_44: [&'static crate::experimental_swift_reactor::control::SwiftReservations; 2],
    class_45: [crate::experimental_swift_reactor::control::SwiftReservationCategory; 18],
    class_46: [(
        std::option::Option<usize>,
        std::option::Option<usize>,
        std::option::Option<usize>,
    ); 1],
    class_47: [&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage; 11],
    class_48: [&'static mut crate::experimental_swift_reactor::control::SwiftReservations; 2],
    class_49: [super::control::Work; 1],
    class_50: [(
        u64,
        u64,
        crate::experimental_swift_reactor::control::SwiftRunResource,
    ); 1],
    class_51: [std::option::Option<u64>; 3],
    class_52: [(&'static u64,); 3],
    class_53: [&'static u64; 3],
    class_54: [(
        crate::experimental_swift_reactor::control::SwiftReservationUsage,
        usize,
        crate::experimental_swift_reactor::control::SwiftRunResource,
        crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    ); 3],
    class_55: [&'static super::control::RuntimeControl; 1],
    class_56: [super::control::Live; 8],
    class_57: [crate::experimental_swift_reactor::control::SwiftReservationUsage; 8],
    class_58: [u32; 35],
    class_59: [&'static crate::experimental_swift_reactor::control::RuntimeControl; 8],
    class_60: [(&'static usize,); 12],
    class_61: [&'static usize; 19],
    class_62: [super::control::SwiftCleanupInvariant; 2],
    class_63: [&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 1],
    class_64: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    >; 2],
    class_65: [crate::experimental_swift_reactor::control::Cursor; 128],
    class_66: [crate::experimental_swift_reactor::control::SwiftRunStage; 1],
    class_67: [std::option::Option<u32>; 5],
    class_68: [(
        crate::experimental_swift_reactor::execution::HeaderCompletionParts,
        usize,
    ); 1],
    class_69: [ConstructionCleanupTail; 2],
    class_70: [(
        Option<(RuntimeControl, AdoptedProof)>,
        Option<Result<SwiftReactorInstance, ConstructionFailure>>,
    ); 3],
    class_71: [crate::experimental_swift_reactor::execution::ExecutionCleanupTail; 5],
    class_72: [crate::experimental_swift_reactor::execution::HeaderCompletionParts; 1],
    class_73: [std::option::Option<[usize; 6]>; 3],
    class_74: [[usize; 6]; 2],
    class_75: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>; 6],
    class_76: [Option<std::convert::Infallible>; 6],
    class_77: [&'static AccountedWasi; 38],
    class_78: [crate::experimental_swift_reactor::control::Work; 2],
    class_79: [std::option::Option<crate::experimental_wasi::WasiUsage>; 67],
    class_80: [crate::experimental_wasi::WasiUsage; 29],
    class_81: [crate::experimental_swift_reactor::execution::SwiftExecutionState; 11],
    class_82: [std::vec::Vec<u8>; 5],
    class_83: [std::vec::Vec<std::option::Option<u32>>; 5],
    class_84: [std::vec::Vec<Value>; 10],
    class_85: [std::vec::Vec<crate::experimental::execution::Control>; 5],
    class_86: [std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>; 5],
    class_87: [[std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;
        6]; 1],
    class_88:
        [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 19],
    class_89: [&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState; 6],
    class_90: [&'static mut SwiftExecutionState; 2],
    class_91: [&'static mut std::vec::Vec<Value>; 14],
    class_92: [&'static mut std::vec::Vec<crate::experimental::execution::Control>; 6],
    class_93:
        [&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>; 6],
    class_94: [&'static mut std::vec::Vec<u8>; 10],
    class_95: [&'static mut std::vec::Vec<std::option::Option<u32>>; 10],
    class_96: [std::result::Result<
        crate::experimental_swift_reactor::execution::SwiftExecutionState,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 3],
    class_97: [&'static mut ExecutionConstructionPhase<'static>; 22],
    class_98: [&'static mut bool; 2],
    class_99: [crate::experimental_swift_reactor::execution::PartialState; 1],
    class_100: [&'static mut crate::experimental_swift_reactor::execution::PartialState; 2],
    class_101: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl; 159],
    class_102: [&'static crate::experimental_wasi::accounted::AccountedWasi; 143],
    class_103: [&'static mut PartialState; 1],
    class_104: [crate::experimental_swift_reactor::control::SwiftRunBudget; 1],
    class_105: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental::descriptors::MemoryExecutionView,
    >; 1],
    class_106: [std::result::Result<
        crate::experimental::descriptors::MemoryExecutionView,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_107: [std::option::Option<crate::experimental::descriptors::MemoryExecutionView>; 2],
    class_108: [&'static crate::experimental::swift::ValidatedSwiftReactor; 30],
    class_109: [(
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_wasi::accounted::AccountedWasi,
        &'static crate::experimental_swift_reactor::control::Cursor,
    ); 33],
    class_110: [&'static crate::experimental_swift_reactor::control::Cursor; 36],
    class_111: [crate::experimental::descriptors::MemoryExecutionView; 1],
    class_112:
        [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>; 1],
    class_113: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental::descriptors::TableExecutionView,
    >; 1],
    class_114: [std::result::Result<
        crate::experimental::descriptors::TableExecutionView,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_115: [std::option::Option<crate::experimental::descriptors::TableExecutionView>; 2],
    class_116: [crate::experimental::descriptors::TableExecutionView; 1],
    class_117: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        [usize; 6],
    >; 1],
    class_118: [std::result::Result<
        [usize; 6],
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_119: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        usize,
    >; 3],
    class_120:
        [std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>;
            8],
    class_121: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 7],
    class_122: [&'static std::vec::Vec<u8>; 10],
    class_123: [std::ops::Range<u32>; 4],
    class_124: [&'static mut std::ops::Range<u32>; 2],
    class_125: [std::ops::Range<usize>; 28],
    class_126: [&'static mut std::ops::Range<usize>; 12],
    class_127: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental::descriptors::GlobalView<'static>,
    >; 1],
    class_128: [std::result::Result<
        crate::experimental::descriptors::GlobalView<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_129: [std::option::Option<crate::experimental::descriptors::GlobalView<'static>>; 2],
    class_130: [crate::experimental::descriptors::GlobalView<'static>; 1],
    class_131: [crate::experimental_swift_reactor::execution::ScalarReader<'static>; 2],
    class_132: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        Value,
    >; 1],
    class_133:
        [std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>;
            3],
    class_134:
        [&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>; 16],
    class_135: [Type; 5],
    class_136: [Value; 7],
    class_137: [crate::experimental_swift_reactor::control::Live; 4],
    class_138: [&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache; 30],
    class_139: [&'static [u8]; 14],
    class_140: [u8; 21],
    class_141: [&'static mut Vec<Value>; 2],
    class_142: [std::result::Result<(), std::collections::TryReserveError>; 10],
    class_143: [(
        &'static usize,
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_wasi::accounted::AccountedWasi,
        &'static crate::experimental_swift_reactor::control::Cursor,
    ); 15],
    class_144: [&'static std::vec::Vec<Value>; 2],
    class_145: [&'static mut Vec<Control>; 2],
    class_146: [&'static std::vec::Vec<Control>; 2],
    class_147: [&'static mut Vec<SwiftFrame>; 2],
    class_148: [&'static std::vec::Vec<SwiftFrame>; 2],
    class_149: [&'static mut Vec<u8>; 2],
    class_150: [&'static mut Vec<Option<u32>>; 2],
    class_151: [&'static std::vec::Vec<Option<u32>>; 2],
    class_152: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental::descriptors::SegmentExecutionView<'static>,
    >; 4],
    class_153: [std::result::Result<
        crate::experimental::descriptors::SegmentExecutionView<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 8],
    class_154:
        [std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>; 8],
    class_155: [crate::experimental::descriptors::SegmentExecutionView<'static>; 7],
    class_156: [&'static std::vec::Vec<std::option::Option<u32>>; 2],
    class_157: [&'static mut [u8]; 2],
    class_158: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        u32,
    >; 1],
    class_159:
        [std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>; 3],
    class_160:
        [&'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>; 2],
    class_161: [std::option::Option<crate::experimental::descriptors::SignatureView<'static>>; 1],
    class_162: [&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>; 24],
    class_163: [&'static mut std::option::Option<u32>; 1],
    class_164: [SegmentExecutionView<'static>; 3],
    class_165: [ExecutionConstructionPhase<'static>; 1],
    class_166:
        [std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>; 15],
    class_167: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        u8,
    >; 7],
    class_168: [std::option::Option<u8>; 2],
    class_169: [std::option::Option<&'static u8>; 2],
    class_170: [(
        &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_wasi::accounted::AccountedWasi,
        &'static crate::experimental_swift_reactor::control::Cursor,
    ); 3],
    class_171: [std::iter::StepBy<std::ops::Range<i32>>; 4],
    class_172: [std::ops::Range<i32>; 2],
    class_173: [std::option::Option<i32>; 1],
    class_174: [&'static mut std::iter::StepBy<std::ops::Range<i32>>; 2],
    class_175: [i32; 2],
    class_176:
        [std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>; 5],
    class_177: [(u32, bool); 3],
    class_178: [i64; 3],
    class_179: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        i64,
    >; 2],
    class_180: [[u8; 4]; 3],
    class_181: [std::slice::IterMut<'static, u8>; 4],
    class_182: [&'static mut [u8; 4]; 2],
    class_183: [std::option::Option<&'static mut u8>; 2],
    class_184: [&'static mut std::slice::IterMut<'static, u8>; 4],
    class_185: [&'static mut u8; 2],
    class_186: [[u8; 8]; 3],
    class_187: [&'static mut [u8; 8]; 2],
    class_188: [&'static Type; 4],
    class_189: [std::result::Result<
        crate::experimental_swift_reactor::execution::SwiftReactorInstance,
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 1],
    class_190:
        [&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>; 3],
    class_191: [WasiGrants; 4],
    class_192: [WasiBudget; 4],
    class_193: [Instant; 4],
    class_194: [&'static mut crate::experimental_swift_reactor::control::AdoptedProof; 1],
    class_195: [&'static mut (
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    ); 1],
    class_196: [std::option::Option<&'static mut (
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    )>; 2],
    class_197: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::execution::ConstructionFailure,
        >,
    >; 2],
    class_198: [std::result::Result<
        (),
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 4],
    class_199: [&'static crate::experimental_swift_reactor::control::AdoptedProof; 6],
    class_200: [std::result::Result<
        std::convert::Infallible,
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 6],
    class_201: [crate::experimental_swift_reactor::control::SwiftRunUsage; 1],
    class_202: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::execution::ConstructionFailure,
        >,
        usize,
    >; 1],
    class_203: [std::result::Result<
        usize,
        crate::experimental_swift_reactor::execution::ConstructionFailure,
    >; 2],
    class_204: [(
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_swift_reactor::control::Cursor,
    ); 3],
    class_205: [crate::experimental_swift_reactor::control::RuntimeControl; 4],
    class_206: [crate::experimental_swift_reactor::control::AdoptedProof; 7],
    class_207: [(
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    ); 1],
    class_208: [std::option::Option<(
        crate::experimental_swift_reactor::control::RuntimeControl,
        crate::experimental_swift_reactor::control::AdoptedProof,
    )>; 2],
    class_209: [crate::experimental_swift_reactor::execution::PartialInstance; 6],
    class_210: [std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>; 4],
    class_211:
        [std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>; 5],
    class_212: [std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>; 4],
    class_213:
        [std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>; 4],
    class_214: [&'static mut crate::experimental_swift_reactor::execution::PartialInstance; 2],
    class_215: [crate::experimental_swift_reactor::execution::ConstructionFailure; 2],
    class_216: [crate::experimental_swift_reactor::execution::ConstructionCleanupTail; 4],
    class_217: [crate::experimental_swift_reactor::execution::SwiftReactorInstance; 4],
    class_218: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::RuntimeControl,
    >; 8],
    class_219: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    >; 6],
    class_220:
        [&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>; 4],
    class_221: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::execution::SwiftExecutionState,
    >; 4],
    class_222: [crate::experimental_swift_reactor::execution::Lifecycle; 1],
    class_223: [std::option::Option<
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    >; 4],
    class_224: [(
        crate::experimental_swift_reactor::execution::PartialInstance,
        std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    ); 2],
    class_225:
        [std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>; 12],
    class_226:
        [&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>; 10],
    class_227: [SwiftReactorInstance; 1],
    class_228: [super::control::SwiftRunFailure; 2],
    class_229: [std::option::Option<
        crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    >; 2],
    class_230: [std::option::Option<
        std::result::Result<
            crate::experimental_swift_reactor::execution::ExecutionCleanupTail,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 4],
    class_231: [std::result::Result<
        crate::experimental_swift_reactor::execution::ExecutionCleanupTail,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 3],
    class_232: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    >; 2],
    class_233: [&'static mut std::option::Option<
        std::result::Result<
            crate::experimental_swift_reactor::execution::ExecutionCleanupTail,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 2],
    class_234: [(
        std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>,
        std::option::Option<
            std::result::Result<
                crate::experimental_swift_reactor::execution::ExecutionCleanupTail,
                crate::experimental_swift_reactor::control::SwiftRunFailure,
            >,
        >,
    ); 2],
    class_235: [&'static mut PartialInstance; 1],
    class_236: [super::control::AdoptedProof; 1],
    class_237: [std::result::Result<
        crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 1],
    class_238: [crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>; 3],
    class_239: [std::option::Option<
        std::result::Result<
            crate::experimental_swift_reactor::cache::SwiftFunctionCache,
            crate::experimental_swift_reactor::cache::CacheConstructionFailure,
        >,
    >; 5],
    class_240: [std::result::Result<
        crate::experimental_swift_reactor::cache::SwiftFunctionCache,
        crate::experimental_swift_reactor::cache::CacheConstructionFailure,
    >; 2],
    class_241:
        [&'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>; 2],
    class_242:
        [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>; 9],
    class_243: [&'static mut std::option::Option<
        std::result::Result<
            crate::experimental_swift_reactor::cache::SwiftFunctionCache,
            crate::experimental_swift_reactor::cache::CacheConstructionFailure,
        >,
    >; 2],
    class_244: [crate::experimental_swift_reactor::cache::SwiftFunctionCache; 1],
    class_245: [crate::experimental_swift_reactor::cache::CacheConstructionFailure; 1],
    class_246:
        [&'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>; 2],
    class_247: [crate::experimental_wasi::accounted::WasiConstructionPhase<'static>; 6],
    class_248: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
    >; 1],
    class_249: [std::result::Result<
        crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_250: [std::option::Option<
        std::result::Result<
            crate::experimental_wasi::accounted::AccountedWasi,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 3],
    class_251: [std::result::Result<
        crate::experimental_wasi::accounted::AccountedWasi,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_252:
        [&'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>; 2],
    class_253: [&'static mut std::option::Option<
        std::result::Result<
            crate::experimental_wasi::accounted::AccountedWasi,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 2],
    class_254: [crate::experimental_wasi::accounted::AccountedWasi; 3],
    class_255:
        [crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>; 4],
    class_256: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
    >; 1],
    class_257: [std::result::Result<
        crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_258: [std::option::Option<
        &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    >; 2],
    class_259: [&'static std::option::Option<
        crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    >; 4],
    class_260: [std::option::Option<
        std::result::Result<
            crate::experimental_swift_reactor::execution::SwiftExecutionState,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 5],
    class_261:
        [&'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<
            'static,
        >; 2],
    class_262: [&'static mut std::option::Option<
        std::result::Result<
            crate::experimental_swift_reactor::execution::SwiftExecutionState,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 2],
    class_263: [PartialInstance; 1],
    class_264: [std::result::Result<
        crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 1],
    class_265: [crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>; 2],
    class_266: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_267: [&'static SwiftFunctionCache; 1],
    class_268: [&'static super::control::AdoptedProof; 1],
    class_269: [&'static mut (); 1],
    class_270: [std::collections::TryReserveError; 5],
    class_271: [Result<SwiftReactorInstance, ConstructionFailure>; 2],
    class_272: [Option<Result<SwiftReactorInstance, ConstructionFailure>>; 2],
    class_273: [ConstructionFailure; 1],
}
pub(crate) const CONSTRUCTION_POSITIVE_ACTIVE_BYTES: usize =
    std::mem::size_of::<ConstructionPositiveActive>();
#[allow(dead_code)]
// Retain each exact mapped tuple identity in this const-only inventory.
#[allow(clippy::type_complexity)]
pub(crate) struct ConstructionPositiveCleanup {
    class_0:
        [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>; 21],
    class_1: [&'static mut super::control::RuntimeControl; 26],
    class_2: [Vec<Value>; 2],
    class_3: [super::control::ReservationTicket; 11],
    class_4: [Option<WasiUsage>; 17],
    class_5: [(); 16],
    class_6: [Vec<Control>; 2],
    class_7: [Vec<SwiftFrame>; 2],
    class_8: [Vec<u8>; 2],
    class_9: [Vec<Option<u32>>; 2],
    class_10: [bool; 22],
    class_11: [u64; 3],
    class_12: [crate::experimental_swift_reactor::control::SwiftRunFailure; 8],
    class_13: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 6],
    class_14: [std::option::Option<usize>; 6],
    class_15: [usize; 35],
    class_16: [&'static crate::experimental_swift_reactor::control::SwiftReservationUsage; 1],
    class_17: [&'static crate::experimental_swift_reactor::control::SwiftReservations; 2],
    class_18: [crate::experimental_swift_reactor::control::SwiftReservationCategory; 4],
    class_19: [(
        std::option::Option<usize>,
        std::option::Option<usize>,
        std::option::Option<usize>,
    ); 1],
    class_20: [isize; 20],
    class_21: [&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage; 10],
    class_22: [&'static mut crate::experimental_swift_reactor::control::SwiftReservations; 2],
    class_23: [&'static str; 20],
    class_24: [(
        crate::experimental_swift_reactor::control::SwiftReservationUsage,
        usize,
        crate::experimental_swift_reactor::control::SwiftRunResource,
        crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    ); 2],
    class_25: [&'static super::control::RuntimeControl; 1],
    class_26: [super::control::Live; 5],
    class_27: [crate::experimental_swift_reactor::control::SwiftReservationUsage; 7],
    class_28: [crate::experimental_swift_reactor::control::SwiftRunResource; 6],
    class_29: [crate::experimental_swift_reactor::control::SwiftRunFailureKind; 14],
    class_30: [u32; 1],
    class_31: [&'static crate::experimental_swift_reactor::control::RuntimeControl; 2],
    class_32: [super::control::SwiftCleanupInvariant; 2],
    class_33: [&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 1],
    class_34: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    >; 2],
    class_35: [crate::experimental_swift_reactor::control::Cursor; 17],
    class_36: [crate::experimental_swift_reactor::control::SwiftRunStage; 2],
    class_37: [std::option::Option<u32>; 2],
    class_38: [crate::experimental_swift_reactor::control::Fault; 2],
    class_39: [&'static mut SwiftExecutionState; 1],
    class_40: [&'static AccountedWasi; 7],
    class_41:
        [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 7],
    class_42: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 14],
    class_43: [crate::experimental_swift_reactor::control::ReservationTicket; 12],
    class_44: [std::vec::Vec<Value>; 8],
    class_45: [&'static mut std::vec::Vec<Value>; 8],
    class_46: [std::option::Option<crate::experimental_wasi::WasiUsage>; 20],
    class_47: [crate::experimental_wasi::WasiUsage; 11],
    class_48: [std::vec::Vec<crate::experimental::execution::Control>; 4],
    class_49: [&'static mut std::vec::Vec<crate::experimental::execution::Control>; 4],
    class_50: [std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>; 4],
    class_51:
        [&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>; 4],
    class_52: [std::vec::Vec<u8>; 4],
    class_53: [&'static mut std::vec::Vec<u8>; 4],
    class_54: [std::vec::Vec<std::option::Option<u32>>; 4],
    class_55: [&'static mut std::vec::Vec<std::option::Option<u32>>; 4],
    class_56: [std::result::Result<
        crate::experimental_swift_reactor::execution::ExecutionCleanupTail,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 1],
    class_57: [&'static mut Option<SwiftReactorInstance>; 3],
    class_58: [&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance; 1],
    class_59: [std::option::Option<
        &'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    >; 2],
    class_60: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl; 20],
    class_61: [std::option::Option<
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    >; 2],
    class_62: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::RuntimeControl,
    >; 4],
    class_63: [&'static crate::experimental_wasi::accounted::AccountedWasi; 16],
    class_64: [std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>; 6],
    class_65: [&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>; 2],
    class_66: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        crate::experimental_wasi::WasiUsage,
    >; 1],
    class_67: [std::result::Result<
        crate::experimental_wasi::WasiUsage,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_68: [std::result::Result<
        std::convert::Infallible,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 12],
    class_69: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
    >; 3],
    class_70: [&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache; 4],
    class_71: [std::option::Option<
        &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    >; 4],
    class_72: [&'static std::option::Option<
        crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    >; 4],
    class_73: [&'static crate::experimental_swift_reactor::execution::SwiftExecutionState; 1],
    class_74: [std::option::Option<
        &'static crate::experimental_swift_reactor::execution::SwiftExecutionState,
    >; 2],
    class_75: [&'static std::option::Option<
        crate::experimental_swift_reactor::execution::SwiftExecutionState,
    >; 2],
    class_76: [std::ops::ControlFlow<
        std::result::Result<
            std::convert::Infallible,
            crate::experimental_swift_reactor::control::SwiftRunFailure,
        >,
        &'static crate::experimental_swift_reactor::control::ReservationTicket,
    >; 2],
    class_77: [std::result::Result<
        &'static crate::experimental_swift_reactor::control::ReservationTicket,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 4],
    class_78: [std::option::Option<
        &'static crate::experimental_swift_reactor::control::ReservationTicket,
    >; 4],
    class_79: [&'static std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 4],
    class_80: [(
        &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
        &'static crate::experimental_wasi::accounted::AccountedWasi,
    ); 6],
    class_81: [&'static crate::experimental_swift_reactor::control::ReservationTicket; 4],
    class_82: [std::slice::Iter<
        'static,
        std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    >; 2],
    class_83: [&'static [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;
                 6]; 2],
    class_84: [std::option::Option<
        &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    >; 1],
    class_85: [&'static mut std::slice::Iter<
        'static,
        std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    >; 2],
    class_86: [&'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>; 2],
    class_87: [&'static std::vec::Vec<Value>; 2],
    class_88: [&'static std::vec::Vec<crate::experimental::execution::Control>; 2],
    class_89: [crate::experimental_swift_reactor::cache::SwiftCacheUsage; 1],
    class_90: [crate::experimental_swift_reactor::execution::SwiftReactorInstance; 3],
    class_91: [std::option::Option<
        crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    >; 2],
    class_92: [crate::experimental_swift_reactor::execution::Lifecycle; 1],
    class_93: [crate::experimental_swift_reactor::control::RuntimeControl; 2],
    class_94: [std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>; 2],
    class_95: [crate::experimental_wasi::accounted::AccountedWasi; 3],
    class_96: [std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>; 2],
    class_97:
        [&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>; 2],
    class_98: [crate::experimental_swift_reactor::execution::SwiftExecutionState; 3],
    class_99:
        [std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>; 2],
    class_100: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::execution::SwiftExecutionState,
    >; 2],
    class_101: [&'static std::vec::Vec<u8>; 2],
    class_102: [&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState; 2],
    class_103: [crate::experimental_swift_reactor::control::Live; 2],
    class_104:
        [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>; 7],
    class_105: [std::result::Result<
        crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>,
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 1],
    class_106: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    >; 4],
    class_107: [crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>; 2],
    class_108:
        [std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>; 2],
    class_109: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::SwiftRunFailure,
    >; 2],
    class_110: [crate::experimental_swift_reactor::execution::ExecutionCleanupTail; 1],
    class_111: [Result<SwiftReactorInstance, ConstructionFailure>; 2],
    class_112: [Option<Result<SwiftReactorInstance, ConstructionFailure>>; 2],
    class_113: [ConstructionFailure; 1],
    class_114: [ConstructionCleanupTail; 1],
    class_115: [(
        Option<(RuntimeControl, AdoptedProof)>,
        Option<Result<SwiftReactorInstance, ConstructionFailure>>,
    ); 1],
}
pub(crate) const CONSTRUCTION_POSITIVE_CLEANUP_BYTES: usize =
    std::mem::size_of::<ConstructionPositiveCleanup>();
#[allow(dead_code)]
// Retain each exact mapped tuple identity in this const-only inventory.
#[allow(clippy::type_complexity)]
pub(crate) struct ConstructionPositiveFinal {
    class_0:
        [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>; 4],
    class_1: [&'static mut super::control::RuntimeControl; 7],
    class_2: [(); 9],
    class_3: [usize; 16],
    class_4: [Option<WasiUsage>; 7],
    class_5: [crate::experimental_swift_reactor::control::SwiftRunFailure; 4],
    class_6: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant; 8],
    class_7: [&'static crate::experimental_swift_reactor::control::ReservationTicket; 1],
    class_8: [std::option::Option<
        &'static crate::experimental_swift_reactor::control::ReservationTicket,
    >; 1],
    class_9: [&'static std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 2],
    class_10: [isize; 4],
    class_11: [bool; 5],
    class_12: [u64; 2],
    class_13: [&'static crate::experimental_swift_reactor::control::SwiftReservationCategory; 4],
    class_14: [std::option::Option<usize>; 4],
    class_15: [(usize, bool); 1],
    class_16: [(std::option::Option<usize>, std::option::Option<usize>); 1],
    class_17: [&'static mut crate::experimental_swift_reactor::control::ReservationTicket; 1],
    class_18: [std::option::Option<
        &'static mut crate::experimental_swift_reactor::control::ReservationTicket,
    >; 2],
    class_19: [&'static mut std::option::Option<
        crate::experimental_swift_reactor::control::ReservationTicket,
    >; 4],
    class_20: [&'static str; 4],
    class_21: [super::control::ReservationTicket; 2],
    class_22: [ConstructionCleanupTail; 2],
    class_23: [(
        Option<(RuntimeControl, AdoptedProof)>,
        Option<Result<SwiftReactorInstance, ConstructionFailure>>,
    ); 2],
    class_24: [&'static mut Option<super::control::SwiftRunFailure>; 1],
    class_25: [&'static mut Option<super::control::SwiftRunUsage>; 1],
    class_26: [crate::experimental_swift_reactor::control::RuntimeControl; 3],
    class_27:
        [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 2],
    class_28: [std::option::Option<crate::experimental_wasi::WasiUsage>; 5],
    class_29: [(
        crate::experimental_swift_reactor::execution::HeaderCompletionParts,
        usize,
    ); 1],
    class_30: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl; 6],
    class_31: [crate::experimental_swift_reactor::control::ReservationTicket; 2],
    class_32: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>; 1],
    class_33: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>; 1],
    class_34: [crate::experimental_swift_reactor::control::SwiftRunUsage; 1],
}
pub(crate) const CONSTRUCTION_POSITIVE_FINAL_BYTES: usize =
    std::mem::size_of::<ConstructionPositiveFinal>();
// Unit-only engine-side hook call boundaries. Callback storage/Cell bodies are
// test harness instrumentation and are excluded, not production authority.
#[cfg(test)]
#[allow(dead_code)]
struct ConstructionPositiveTestHookArguments {
    checkpoint_reborrow: &'static RuntimeControl,
    checkpoint_argument: &'static RuntimeControl,
    checkpoint_callback_parameter: &'static RuntimeControl,
    checkpoint_cursor_argument: Cursor,
    checkpoint_cursor_callback_parameter: Cursor,
    checkpoint_call_return: (),
    checkpoint_callback_return: (),
    capacity_new_source: usize,
    capacity_argument: usize,
    capacity_callback_parameter: usize,
    capacity_callback_return: usize,
    restore_new_source: usize,
    restore_argument: usize,
    restore_callback_parameter: usize,
    restore_callback_return: usize,
}
#[cfg(test)]
pub(super) const CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES: usize =
    std::mem::size_of::<ConstructionPositiveTestHookArguments>();
#[cfg(not(test))]
pub(super) const CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES: usize = 0;
