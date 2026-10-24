//! Compiling private owner/borrow/layout prerequisite only.
//! No constructor, initialize, invoke, or interpreter algorithm is provided.
#![allow(clippy::result_large_err)]

use super::cache::{
    CacheCleanupTail, CacheConstructionFailure, CacheConstructionPhase, CacheOperationPhase,
    SwiftFunctionCache, SwiftFunctionPin, SwiftReleaseFailure,
};
use super::control::*;
use crate::experimental::cache::{DecodedInstruction, FunctionView, Operation};
use crate::experimental::descriptors::{FunctionSpanView, SignatureView};
use crate::experimental::execution::{borrowed::*, Control};
use crate::experimental_wasi::{
    accounted::{AccountedWasi, WasiConstructionPhase},
    WasiUsage,
};
use crate::Value;
use std::mem::size_of;

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
pub(crate) fn terms() -> &'static [LayoutTerm] {
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
/// No negative subtraction; count nested payload once and every Option tag or
/// containing alignment byte in the exclusive residual. Arena payloads have
/// their separate six tickets; all additional cleanup rows use this same header.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) fn execution_header_bytes() -> Option<usize> {
    let nested = size_of::<RuntimeControl>()
        .checked_add(size_of::<SwiftFunctionCache>())?
        .checked_add(size_of::<AccountedWasi>())?
        .checked_add(size_of::<SwiftExecutionState>())?;
    size_of::<SwiftReactorInstance>()
        .checked_sub(nested)?
        .checked_add(size_of::<SwiftExecutionState>())?
        .checked_add(phase_bytes("cleanup")?)
}

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
