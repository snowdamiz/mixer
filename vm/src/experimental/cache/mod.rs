//! Nondefault, fallible decoded-function cache. This module cannot execute guests.
// Static bounded diagnostic snapshots must remain usable after allocation failure.
#![allow(clippy::result_large_err)]
mod decode;

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
struct DecodedFunction {
    function: u32,
    type_index: u32,
    body_offset: usize,
    locals: Vec<Type>,
    instructions: Vec<DecodedInstruction>,
    branch_targets: Vec<u32>,
    bytes: usize,
}
struct Slot {
    entry: Option<DecodedFunction>,
    pins: usize,
    last_used: u64,
}
#[derive(Clone, Copy, Default)]
struct PinRecord {
    nonce: u64,
    entry: usize,
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
struct Meter<'a> {
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
    fn error(&self, kind: CacheFailureKind, code: &'static str) -> CacheFailure {
        failure(self.usage, kind, code, None, 0, 0, 0)
    }
    fn checked_record(&self, pin: &FunctionPin) -> Result<PinRecord, CacheFailure> {
        if pin.owner != self.owner {
            return Err(self.error(CacheFailureKind::InvalidPin, "wrong_cache_owner"));
        }
        let record = self
            .pins
            .get(pin.slot)
            .copied()
            .filter(|record| record.nonce != 0 && record.nonce == pin.nonce)
            .ok_or_else(|| self.error(CacheFailureKind::InvalidPin, "stale_pin"))?;
        if self
            .slots
            .get(record.entry)
            .is_none_or(|slot| slot.pins == 0 || slot.entry.is_none())
        {
            return Err(self.error(CacheFailureKind::InvalidPin, "stale_entry"));
        }
        Ok(record)
    }
    pub fn view(&self, pin: &FunctionPin) -> Result<FunctionView<'_>, CacheFailure> {
        let record = self.checked_record(pin)?;
        let entry = self.slots[record.entry]
            .entry
            .as_ref()
            .ok_or_else(|| self.error(CacheFailureKind::InvalidPin, "stale_entry"))?;
        Ok(FunctionView {
            function: entry.function,
            type_index: entry.type_index,
            body_offset: entry.body_offset,
            locals: &entry.locals,
            instructions: &entry.instructions,
            branch_targets: &entry.branch_targets,
        })
    }
    pub fn release(&mut self, pin: FunctionPin) -> Result<(), ReleaseFailure> {
        let record = match self.checked_record(&pin) {
            Ok(r) => r,
            Err(failure) => return Err(ReleaseFailure { failure, pin }),
        };
        let slot = &mut self.slots[record.entry];
        if slot.pins == 1 {
            self.usage.pinned_bytes -= slot.entry.as_ref().expect("checked entry").bytes;
        }
        slot.pins -= 1;
        self.usage.active_pins -= 1;
        self.pins[pin.slot] = PinRecord::default();
        Ok(())
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
        let mut meter = Meter {
            budget: self.budget,
            usage: &mut self.usage,
            cancellation,
            function: Some(function),
            offset: 0,
        };
        meter.work(1)?;
        let defined = (function as usize)
            .checked_sub(self.spans.metadata.imports.len())
            .and_then(|n| self.spans.metadata.functions.get(n))
            .copied()
            .ok_or_else(|| {
                meter.error(CacheFailureKind::InvalidFunction, "not_defined_function")
            })?;
        meter.offset = defined.body.offset as usize;
        let nonce = self
            .next_nonce
            .checked_add(1)
            .ok_or_else(|| meter.error(CacheFailureKind::NonceExhausted, "pin_nonce_exhausted"))?;
        let mut pin_slot = None;
        for (index, record) in self.pins.iter().enumerate() {
            meter.work(1)?;
            if record.nonce == 0 {
                pin_slot = Some(index);
                break;
            }
        }
        let pin_slot = pin_slot
            .ok_or_else(|| meter.error(CacheFailureKind::PinExhausted, "pin_slots_exhausted"))?;
        let mut hit = None;
        for (index, slot) in self.slots.iter().enumerate() {
            meter.work(1)?;
            if slot
                .entry
                .as_ref()
                .is_some_and(|entry| entry.function == function)
            {
                hit = Some(index);
                break;
            }
        }
        let slot_index =
            if let Some(index) = hit {
                meter.check()?;
                meter.usage.hits =
                    meter.usage.hits.checked_add(1).ok_or_else(|| {
                        meter.error(CacheFailureKind::WorkExhausted, "hits_overflow")
                    })?;
                index
            } else {
                meter.usage.misses = meter.usage.misses.checked_add(1).ok_or_else(|| {
                    meter.error(CacheFailureKind::WorkExhausted, "misses_overflow")
                })?;
                let next_decodes = meter.usage.decodes.checked_add(1).ok_or_else(|| {
                    meter.error(CacheFailureKind::WorkExhausted, "decodes_overflow")
                })?;
                let body = defined.body.slice(self.spans.source());
                let counts = decode::scan(
                    body,
                    defined.body.offset as usize,
                    self.spans.limits(),
                    &mut meter,
                    None,
                )?;
                let bytes = counts.bytes(&meter)?;
                if bytes > self.budget.entry_bytes {
                    return Err(failure(
                        *meter.usage,
                        CacheFailureKind::EntryOversize,
                        "entry_bytes",
                        Some(function),
                        meter.offset,
                        bytes as u64,
                        self.budget.entry_bytes as u64,
                    ));
                }
                let base = meter.usage.fixed_reserved + meter.usage.scratch_reserved;
                if base
                    .checked_add(bytes)
                    .is_none_or(|n| n > self.budget.capacity_bytes)
                {
                    return Err(meter.error(CacheFailureKind::Capacity, "entry_cannot_fit"));
                }
                let mut plan = [false; MAX_ENTRIES];
                let mut remaining = meter.usage.resident_bytes;
                meter.work(self.slots.len() as u64)?;
                let mut empty = self.slots.iter().position(|slot| slot.entry.is_none());
                while empty.is_none() || base + remaining + bytes > self.budget.capacity_bytes {
                    let mut oldest: Option<usize> = None;
                    for (index, slot) in self.slots.iter().enumerate() {
                        meter.work(1)?;
                        if !plan[index]
                            && slot.pins == 0
                            && slot.entry.is_some()
                            && oldest.is_none_or(|previous| {
                                slot.last_used < self.slots[previous].last_used
                            })
                        {
                            oldest = Some(index);
                        }
                    }
                    let victim = oldest.ok_or_else(|| {
                        meter.error(CacheFailureKind::AllPinned, "all_entries_pinned")
                    })?;
                    plan[victim] = true;
                    remaining -= self.slots[victim]
                        .entry
                        .as_ref()
                        .expect("selected entry")
                        .bytes;
                    empty = Some(victim);
                }
                // Precharge the whole bounded application before any eviction.
                meter.work(MAX_ENTRIES as u64)?;
                let evictions = plan.iter().filter(|v| **v).count() as u64;
                meter
                    .usage
                    .evictions
                    .checked_add(evictions)
                    .ok_or_else(|| {
                        meter.error(CacheFailureKind::WorkExhausted, "evictions_overflow")
                    })?;
                meter.check()?;
                for (index, selected) in plan.iter().enumerate().take(self.slots.len()) {
                    if *selected {
                        let old = self.slots[index].entry.take().expect("planned entry");
                        let old_bytes = old.bytes;
                        drop(old);
                        meter.usage.resident_bytes -= old_bytes;
                        meter.usage.evictions += 1;
                    }
                }
                let index = empty
                    .ok_or_else(|| meter.error(CacheFailureKind::Capacity, "no_entry_slot"))?;
                meter.usage.construction_bytes = bytes;
                update_peak(meter.usage, self.budget)?;
                let decoded = decode::build(
                    body,
                    defined.body.offset as usize,
                    defined.type_index,
                    function,
                    self.spans.limits(),
                    counts,
                    &mut meter,
                );
                let entry = match decoded {
                    Ok(entry) => entry,
                    Err(error) => {
                        meter.usage.construction_bytes = 0;
                        return Err(error);
                    }
                };
                if let Err(error) = meter.check() {
                    drop(entry);
                    meter.usage.construction_bytes = 0;
                    return Err(error);
                }
                meter.usage.decodes = next_decodes;
                meter.usage.construction_bytes = 0;
                meter.usage.resident_bytes += bytes;
                meter.usage.peak_resident_bytes = meter
                    .usage
                    .peak_resident_bytes
                    .max(meter.usage.resident_bytes);
                self.slots[index].entry = Some(entry);
                index
            };
        // No fallible operation follows entry publication.
        let slot = &mut self.slots[slot_index];
        if slot.pins == 0 {
            meter.usage.pinned_bytes += slot.entry.as_ref().expect("resident entry").bytes;
        }
        meter.usage.peak_pinned_bytes = meter.usage.peak_pinned_bytes.max(meter.usage.pinned_bytes);
        slot.pins += 1; // bounded by the preallocated pin table
        slot.last_used = meter.usage.work_used;
        self.pins[pin_slot] = PinRecord {
            nonce: self.next_nonce,
            entry: slot_index,
        };
        meter.usage.active_pins += 1;
        let pin = FunctionPin {
            owner: self.owner,
            slot: pin_slot,
            nonce: self.next_nonce,
        };
        self.next_nonce = nonce;
        Ok(pin)
    }
}

#[cfg(test)]
mod tests;
