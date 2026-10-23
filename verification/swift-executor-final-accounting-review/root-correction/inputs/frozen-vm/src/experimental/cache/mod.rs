//! Nondefault, fallible decoded-function cache. This module cannot execute guests.
// Static bounded diagnostic snapshots must remain usable after allocation failure.
#![allow(clippy::result_large_err)]
// The frozen public specialization is intentionally private/unselected when only
// the Swift experiment needs the borrowed decoder and cache algorithm.
#![cfg_attr(
    all(
        feature = "experimental-swift-reactor",
        not(feature = "experimental-function-cache")
    ),
    allow(dead_code)
)]
pub(crate) mod borrowed;
pub(crate) mod decode;

use super::ValidatedSpans;
use crate::{Cancellation, Profile, Type, Value};
use std::sync::atomic::{AtomicU64, Ordering};

const MAX_ENTRIES: usize = 64;
const MAX_PINS: usize = 64;
static NEXT_OWNER: AtomicU64 = AtomicU64::new(1);

/// Auxiliary cache ceilings. They can only narrow these defaults.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CacheBudget {
    pub capacity_bytes: usize,
    pub entry_bytes: usize,
    pub max_entries: usize,
    pub max_pins: usize,
    pub work_credits: u64,
}
impl Default for CacheBudget {
    fn default() -> Self {
        Self {
            capacity_bytes: 16 * 1024 * 1024,
            entry_bytes: 8 * 1024 * 1024,
            max_entries: MAX_ENTRIES,
            max_pins: MAX_PINS,
            work_credits: 64_000_000,
        }
    }
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct CacheUsage {
    pub source_bytes: usize,
    pub validation_metadata_bytes: usize,
    pub fixed_reserved: usize,
    pub resident_bytes: usize,
    /// Subset of resident_bytes, not an additional reservation.
    pub pinned_bytes: usize,
    pub construction_bytes: usize,
    pub peak_resident_bytes: usize,
    pub peak_pinned_bytes: usize,
    pub peak_construction_bytes: usize,
    pub scratch_reserved: usize,
    pub peak_cache_reserved: usize,
    pub peak_total_reserved: usize,
    pub work_used: u64,
    pub active_pins: usize,
    pub hits: u64,
    pub misses: u64,
    pub decodes: u64,
    pub evictions: u64,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CacheFailureKind {
    InvalidBudget,
    InvalidFunction,
    InvalidPin,
    EntryOversize,
    Capacity,
    AllPinned,
    PinExhausted,
    WorkExhausted,
    IdentityExhausted,
    NonceExhausted,
    Cancelled,
    AllocationFailure,
    DecoderMismatch,
}
/// Static diagnostics and scalar observations; constructing failures allocates nothing.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CacheFailure {
    pub kind: CacheFailureKind,
    pub code: &'static str,
    pub function: Option<u32>,
    pub offset: usize,
    pub attempted: u64,
    pub limit: u64,
    pub usage: CacheUsage,
}
impl std::fmt::Display for CacheFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at byte {}", self.code, self.offset)
    }
}
impl std::error::Error for CacheFailure {}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CacheIdentity {
    pub owner: u64,
    pub validator_revision: u32,
    pub decoder_revision: u32,
    pub profile: Profile,
}
/// Opaque non-Clone token. Forgetting it keeps its payload counted and pinned.
#[derive(Debug)]
pub struct FunctionPin {
    owner: u64,
    slot: usize,
    nonce: u64,
}
#[derive(Debug)]
pub struct ReleaseFailure {
    pub failure: CacheFailure,
    pin: FunctionPin,
}
impl ReleaseFailure {
    pub fn into_pin(self) -> FunctionPin {
        self.pin
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ControlKind {
    Block,
    Loop,
    If,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Operation {
    Unreachable,
    Nop,
    Block {
        kind: ControlKind,
        result: Option<Type>,
        end: usize,
        alternative: Option<usize>,
    },
    Else {
        end: usize,
    },
    End,
    Br(u32),
    BrIf(u32),
    BrTable {
        first: usize,
        count: usize,
        default: u32,
    },
    Return,
    Call(u32),
    CallIndirect(u32),
    MemoryCopy,
    MemoryFill,
    Drop,
    Select,
    LocalGet(u32),
    LocalSet(u32),
    LocalTee(u32),
    GlobalGet(u32),
    GlobalSet(u32),
    Load {
        opcode: u8,
        offset: u32,
    },
    Store {
        opcode: u8,
        offset: u32,
    },
    MemorySize,
    MemoryGrow,
    Const(Value),
    Numeric(u8),
    Saturating(u8),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DecodedInstruction {
    pub operation: Operation,
    pub offset: usize,
}
/// A borrow from a checked pin. It cannot survive a mutable cache operation.
pub struct FunctionView<'a> {
    pub function: u32,
    pub type_index: u32,
    pub body_offset: usize,
    pub locals: &'a [Type],
    pub instructions: &'a [DecodedInstruction],
    pub branch_targets: &'a [u32],
}
pub(crate) struct DecodedFunction {
    pub(crate) function: u32,
    pub(crate) type_index: u32,
    pub(crate) body_offset: usize,
    pub(crate) locals: Vec<Type>,
    pub(crate) instructions: Vec<DecodedInstruction>,
    pub(crate) branch_targets: Vec<u32>,
    pub(crate) bytes: usize,
}
pub(crate) struct Slot {
    entry: Option<DecodedFunction>,
    pins: usize,
    last_used: u64,
}
#[derive(Clone, Copy, Default)]
pub(crate) struct PinRecord {
    pub(crate) nonce: u64,
    pub(crate) entry: usize,
}
/// Owns one complete validated snapshot and bounded decoded entries.
///
/// A view cannot remain live across a cache mutation:
/// ```compile_fail
/// use mixer_vm::{Cancellation, Limits};
/// use mixer_vm::experimental::{validate_spans, ValidationBudget};
/// use mixer_vm::experimental::cache::{CacheBudget, FunctionCache};
/// let cancel = Cancellation::default();
/// let bytes = b"\0asm\x01\0\0\0\x01\x04\x01\x60\0\0\x03\x02\x01\0\x0a\x04\x01\x02\0\x0b";
/// let spans = validate_spans(bytes, Limits::default(), ValidationBudget::default(), &cancel).unwrap();
/// let mut cache = FunctionCache::new(spans, CacheBudget::default(), &cancel).unwrap();
/// let pin = cache.pin(0, &cancel).unwrap();
/// let view = cache.view(&pin).unwrap();
/// let other = cache.pin(0, &cancel).unwrap();
/// println!("{}", view.instructions.len());
/// ```
pub struct FunctionCache {
    spans: ValidatedSpans,
    budget: CacheBudget,
    usage: CacheUsage,
    owner: u64,
    next_nonce: u64,
    slots: Vec<Slot>,
    pins: Vec<PinRecord>,
}
fn failure(
    usage: CacheUsage,
    kind: CacheFailureKind,
    code: &'static str,
    function: Option<u32>,
    offset: usize,
    attempted: u64,
    limit: u64,
) -> CacheFailure {
    CacheFailure {
        kind,
        code,
        function,
        offset,
        attempted,
        limit,
        usage,
    }
}
pub(crate) struct Meter<'a> {
    budget: CacheBudget,
    usage: &'a mut CacheUsage,
    cancellation: &'a Cancellation,
    function: Option<u32>,
    offset: usize,
}
impl Meter<'_> {
    fn error(&self, kind: CacheFailureKind, code: &'static str) -> CacheFailure {
        failure(*self.usage, kind, code, self.function, self.offset, 0, 0)
    }
    fn check(&self) -> Result<(), CacheFailure> {
        if self.cancellation.is_cancelled() {
            Err(self.error(CacheFailureKind::Cancelled, "cancelled"))
        } else {
            Ok(())
        }
    }
    fn work(&mut self, amount: u64) -> Result<(), CacheFailure> {
        self.check()?;
        let attempted = self
            .usage
            .work_used
            .checked_add(amount)
            .ok_or_else(|| self.error(CacheFailureKind::WorkExhausted, "work_overflow"))?;
        if attempted > self.budget.work_credits {
            return Err(failure(
                *self.usage,
                CacheFailureKind::WorkExhausted,
                "cache_work",
                self.function,
                self.offset,
                attempted,
                self.budget.work_credits,
            ));
        }
        self.usage.work_used = attempted;
        Ok(())
    }
}
fn allocate<T>(capacity: usize, meter: &mut Meter<'_>) -> Result<Vec<T>, CacheFailure> {
    meter.check()?;
    let mut values = Vec::new();
    values
        .try_reserve_exact(capacity)
        .map_err(|_| meter.error(CacheFailureKind::AllocationFailure, "cache_allocation"))?;
    if values.capacity() != capacity {
        return Err(meter.error(CacheFailureKind::AllocationFailure, "cache_capacity"));
    }
    meter.check()?;
    Ok(values)
}
fn issue_owner(counter: &AtomicU64, meter: &Meter<'_>) -> Result<u64, CacheFailure> {
    counter
        .try_update(Ordering::Relaxed, Ordering::Relaxed, |n| n.checked_add(1))
        .map_err(|_| {
            meter.error(
                CacheFailureKind::IdentityExhausted,
                "cache_identity_exhausted",
            )
        })
}
fn scratch_bytes() -> usize {
    // Both pass states include their fixed control patch arrays. The eviction
    // plan, two readers, meter, bounded failures and scalar temporaries are extra.
    2 * std::mem::size_of::<decode::PassState>()
        + 2 * std::mem::size_of::<decode::Reader<'static>>()
        + std::mem::size_of::<[bool; MAX_ENTRIES]>()
        + std::mem::size_of::<Meter<'static>>()
        + 3 * std::mem::size_of::<CacheFailure>()
        + 256
}
fn update_peak(usage: &mut CacheUsage, budget: CacheBudget) -> Result<(), CacheFailure> {
    let bytes = usage
        .fixed_reserved
        .checked_add(usage.resident_bytes)
        .and_then(|n| n.checked_add(usage.construction_bytes))
        .and_then(|n| n.checked_add(usage.scratch_reserved))
        .ok_or_else(|| {
            failure(
                *usage,
                CacheFailureKind::Capacity,
                "cache_capacity_overflow",
                None,
                0,
                u64::MAX,
                budget.capacity_bytes as u64,
            )
        })?;
    if bytes > budget.capacity_bytes {
        return Err(failure(
            *usage,
            CacheFailureKind::Capacity,
            "cache_capacity",
            None,
            0,
            bytes as u64,
            budget.capacity_bytes as u64,
        ));
    }
    let total = bytes
        .checked_add(usage.source_bytes)
        .and_then(|n| n.checked_add(usage.validation_metadata_bytes))
        .ok_or_else(|| {
            failure(
                *usage,
                CacheFailureKind::Capacity,
                "total_capacity_overflow",
                None,
                0,
                u64::MAX,
                usize::MAX as u64,
            )
        })?;
    usage.peak_construction_bytes = usage.peak_construction_bytes.max(usage.construction_bytes);
    usage.peak_cache_reserved = usage.peak_cache_reserved.max(bytes);
    usage.peak_total_reserved = usage.peak_total_reserved.max(total);
    Ok(())
}
impl FunctionCache {
    pub const DECODER_REVISION: u32 = 1;
    pub fn new(
        spans: ValidatedSpans,
        budget: CacheBudget,
        cancellation: &Cancellation,
    ) -> Result<Self, CacheFailure> {
        let defaults = CacheBudget::default();
        let mut usage = CacheUsage {
            source_bytes: spans.source().len(),
            validation_metadata_bytes: spans.usage().metadata_reserved,
            scratch_reserved: scratch_bytes(),
            ..CacheUsage::default()
        };
        if budget.capacity_bytes > defaults.capacity_bytes
            || budget.entry_bytes > defaults.entry_bytes
            || budget.max_entries == 0
            || budget.max_entries > defaults.max_entries
            || budget.max_pins == 0
            || budget.max_pins > defaults.max_pins
            || budget.work_credits > defaults.work_credits
        {
            return Err(failure(
                usage,
                CacheFailureKind::InvalidBudget,
                "invalid_cache_budget",
                None,
                0,
                0,
                0,
            ));
        }
        let entries = budget.max_entries.min(spans.defined_function_count());
        usage.fixed_reserved = std::mem::size_of::<Self>()
            + entries * std::mem::size_of::<Slot>()
            + budget.max_pins * std::mem::size_of::<PinRecord>();
        update_peak(&mut usage, budget)?;
        let mut meter = Meter {
            budget,
            usage: &mut usage,
            cancellation,
            function: None,
            offset: 0,
        };
        meter.check()?;
        let mut slots = allocate(entries, &mut meter)?;
        for _ in 0..entries {
            meter.work(1)?;
            slots.push(Slot {
                entry: None,
                pins: 0,
                last_used: 0,
            });
        }
        let mut pins = allocate(budget.max_pins, &mut meter)?;
        for _ in 0..budget.max_pins {
            meter.work(1)?;
            pins.push(PinRecord::default());
        }
        meter.check()?;
        let owner = issue_owner(&NEXT_OWNER, &meter)?;
        usage.scratch_reserved = 0;
        Ok(Self {
            spans,
            budget,
            usage,
            owner,
            next_nonce: 1,
            slots,
            pins,
        })
    }
    pub fn identity(&self) -> CacheIdentity {
        CacheIdentity {
            owner: self.owner,
            validator_revision: ValidatedSpans::VALIDATOR_REVISION,
            decoder_revision: Self::DECODER_REVISION,
            profile: self.spans.profile(),
        }
    }
    pub fn spans(&self) -> &ValidatedSpans {
        &self.spans
    }
    pub fn usage(&self) -> CacheUsage {
        self.usage
    }
    pub fn view(&self, pin: &FunctionPin) -> Result<FunctionView<'_>, CacheFailure> {
        borrowed::view::<borrowed::FrozenMode>(
            borrowed::CacheViewParts {
                slots: &self.slots,
                pins: &self.pins,
                owner: self.owner,
            },
            pin,
            &mut borrowed::FrozenDiagnostics { usage: &self.usage },
        )
    }
    pub fn release(&mut self, pin: FunctionPin) -> Result<(), ReleaseFailure> {
        let mut operation = borrowed::FrozenRelease { usage: self.usage };
        borrowed::release::<borrowed::FrozenMode>(
            borrowed::CacheParts {
                snapshot: &self.spans,
                slots: &mut self.slots,
                pins: &mut self.pins,
                owner: self.owner,
                next_nonce: &mut self.next_nonce,
                usage: &mut self.usage,
                scratch: (),
            },
            pin,
            &mut operation,
        )
        .map_err(|(failure, pin)| ReleaseFailure { failure, pin })
    }
    pub fn pin(
        &mut self,
        function: u32,
        cancellation: &Cancellation,
    ) -> Result<FunctionPin, CacheFailure> {
        self.usage.scratch_reserved = scratch_bytes();
        let result = update_peak(&mut self.usage, self.budget)
            .and_then(|()| self.pin_inner(function, cancellation));
        self.usage.scratch_reserved = 0;
        match result {
            Ok(pin) => Ok(pin),
            Err(mut error) => {
                error.usage = self.usage;
                Err(error)
            }
        }
    }
    fn pin_inner(
        &mut self,
        function: u32,
        cancellation: &Cancellation,
    ) -> Result<FunctionPin, CacheFailure> {
        borrowed::pin::<borrowed::FrozenMode>(
            borrowed::CacheParts {
                snapshot: &self.spans,
                slots: &mut self.slots,
                pins: &mut self.pins,
                owner: self.owner,
                next_nonce: &mut self.next_nonce,
                usage: &mut self.usage,
                scratch: (),
            },
            function,
            &mut borrowed::FrozenOperation {
                budget: &self.budget,
                cancellation,
            },
        )
    }
}

#[cfg(test)]
mod tests;
