//! Closed, ephemeral adapters. These borrows never replace a validated owner.
use super::*;
use crate::experimental::descriptors::{FunctionSpanView, SignatureView};
use crate::Limits;

pub(crate) mod sealed {
    pub trait Snapshot {}
    pub trait Policy {}
    pub trait Mode {}
    pub trait Meter {}
}

pub(crate) trait SnapshotView: sealed::Snapshot {
    type Policy: ?Sized;
    fn policy(&self) -> &Self::Policy;
    fn source(&self) -> &[u8];
    fn defined_function_count(&self) -> usize;
    fn imported_function_count(&self) -> usize;
    fn function(&self, absolute: u32) -> Option<FunctionSpanView<'_>>;
    fn signature(&self, absolute: u32) -> Option<SignatureView<'_>>;
}
impl sealed::Snapshot for ValidatedSpans {}
impl SnapshotView for ValidatedSpans {
    type Policy = Limits;
    fn policy(&self) -> &Limits {
        self.limits()
    }
    fn source(&self) -> &[u8] {
        self.source()
    }
    fn defined_function_count(&self) -> usize {
        self.defined_function_count()
    }
    fn imported_function_count(&self) -> usize {
        self.metadata.imports.len()
    }
    fn function(&self, absolute: u32) -> Option<FunctionSpanView<'_>> {
        let defined = (absolute as usize).checked_sub(self.imported_function_count())?;
        let function = self.metadata.functions.get(defined)?;
        Some(FunctionSpanView {
            absolute_index: absolute,
            type_index: function.type_index,
            body_offset: function.body.offset as usize,
            body: function.body.slice(self.source()),
        })
    }
    fn signature(&self, absolute: u32) -> Option<SignatureView<'_>> {
        let signature = self.metadata.signature(absolute)?;
        Some(SignatureView {
            params: self.metadata.params(signature),
            result: signature.result,
        })
    }
}
#[cfg(feature = "experimental-swift-reactor")]
impl sealed::Snapshot for crate::experimental_swift_reactor::ValidatedSwiftReactor {}
#[cfg(feature = "experimental-swift-reactor")]
impl SnapshotView for crate::experimental_swift_reactor::ValidatedSwiftReactor {
    type Policy = crate::experimental::policy::Policy<'static>;
    fn policy(&self) -> &Self::Policy {
        self.decode_policy()
    }
    fn source(&self) -> &[u8] {
        self.source()
    }
    fn defined_function_count(&self) -> usize {
        self.observations().defined_functions
    }
    fn imported_function_count(&self) -> usize {
        self.observations().imported_functions
    }
    fn function(&self, absolute: u32) -> Option<FunctionSpanView<'_>> {
        self.execution_function(absolute)
    }
    fn signature(&self, absolute: u32) -> Option<SignatureView<'_>> {
        self.execution_signature(absolute)
    }
}

pub(crate) trait DecodePolicy: sealed::Policy {
    fn floats(&self) -> bool;
    fn tables(&self) -> bool;
    fn source_extent(&self) -> usize;
    fn parameters(&self) -> usize;
    fn parameters_limit(&self) -> usize;
    fn local_groups(&self) -> usize;
    fn total_locals(&self) -> usize;
    fn instructions(&self) -> usize;
    fn control_depth(&self) -> usize;
    fn counts_parameters(&self) -> bool;
}
pub(crate) struct FrozenPolicy<'a> {
    pub limits: &'a Limits,
    pub extent: usize,
}
impl sealed::Policy for FrozenPolicy<'_> {}
impl DecodePolicy for FrozenPolicy<'_> {
    fn floats(&self) -> bool {
        self.limits.profile.floats()
    }
    fn tables(&self) -> bool {
        self.limits.profile == Profile::TableMemoryV3
    }
    // Frozen validation already sealed the source/body extent; preserve its trace.
    fn source_extent(&self) -> usize {
        self.extent
    }
    fn parameters(&self) -> usize {
        0
    }
    fn parameters_limit(&self) -> usize {
        self.limits.locals
    }
    fn local_groups(&self) -> usize {
        self.limits.locals
    }
    fn total_locals(&self) -> usize {
        self.limits.locals
    }
    fn instructions(&self) -> usize {
        self.limits.instructions
    }
    fn control_depth(&self) -> usize {
        self.limits.control_depth
    }
    fn counts_parameters(&self) -> bool {
        false
    }
}
#[cfg(feature = "experimental-swift-reactor")]
pub(crate) struct SwiftPolicy<'a> {
    pub policy: &'a crate::experimental::policy::Policy<'static>,
    pub extent: usize,
    pub parameters: usize,
}
#[cfg(feature = "experimental-swift-reactor")]
impl sealed::Policy for SwiftPolicy<'_> {}
#[cfg(feature = "experimental-swift-reactor")]
impl DecodePolicy for SwiftPolicy<'_> {
    fn floats(&self) -> bool {
        self.policy.floats()
    }
    fn tables(&self) -> bool {
        self.policy.tables()
    }
    fn source_extent(&self) -> usize {
        self.extent
    }
    fn parameters(&self) -> usize {
        self.parameters
    }
    fn parameters_limit(&self) -> usize {
        self.policy.parameters_per_signature()
    }
    fn local_groups(&self) -> usize {
        self.policy.local_groups()
    }
    fn total_locals(&self) -> usize {
        self.policy.parameters_plus_locals()
    }
    fn instructions(&self) -> usize {
        self.policy.instructions()
    }
    fn control_depth(&self) -> usize {
        self.policy.control_depth()
    }
    fn counts_parameters(&self) -> bool {
        true
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum CacheStep {
    Constructor,
    Lookup,
    ScanReset,
    Scan,
    BuildReset,
    Build,
    Planning,
    Publication,
}
pub(crate) trait DecodeMeter: sealed::Meter {
    fn step(&mut self, _: CacheStep) {}
    type Failure;
    fn error(&mut self, kind: CacheFailureKind, code: &'static str) -> Self::Failure;
    fn check(&mut self) -> Result<(), Self::Failure>;
    fn work(&mut self, amount: u64) -> Result<(), Self::Failure>;
    fn set_offset(&mut self, offset: usize);
    fn exact_capacity(&mut self, requested: usize, observed: usize) -> Result<(), Self::Failure>;
}
impl sealed::Meter for Meter<'_> {}
impl DecodeMeter for Meter<'_> {
    type Failure = CacheFailure;
    fn error(&mut self, kind: CacheFailureKind, code: &'static str) -> CacheFailure {
        Meter::error(self, kind, code)
    }
    fn check(&mut self) -> Result<(), CacheFailure> {
        Meter::check(self)
    }
    fn work(&mut self, amount: u64) -> Result<(), CacheFailure> {
        Meter::work(self, amount)
    }
    fn set_offset(&mut self, offset: usize) {
        self.offset = offset;
    }
    fn exact_capacity(&mut self, requested: usize, observed: usize) -> Result<(), CacheFailure> {
        if requested != observed {
            Err(Meter::error(
                self,
                CacheFailureKind::AllocationFailure,
                "cache_capacity",
            ))
        } else {
            Ok(())
        }
    }
}
pub(crate) fn allocate<M: DecodeMeter, T>(
    capacity: usize,
    meter: &mut M,
) -> Result<Vec<T>, M::Failure> {
    meter.check()?;
    let mut values = Vec::new();
    values
        .try_reserve_exact(capacity)
        .map_err(|_| meter.error(CacheFailureKind::AllocationFailure, "cache_allocation"))?;
    meter.exact_capacity(capacity, values.capacity())?;
    meter.check()?;
    Ok(values)
}

pub(crate) trait Statistics {
    fn resident(&self) -> usize;

    fn hits(&self) -> u64;
    fn misses(&self) -> u64;
    fn decodes(&self) -> u64;
    fn evictions(&self) -> u64;
    fn hit(&mut self, value: u64);
    fn miss(&mut self, value: u64);
    fn decoded(&mut self, value: u64, bytes: usize);
    fn evicted(&mut self, bytes: usize);
    fn pin(&mut self, bytes: usize, first: bool);
    fn release(&mut self, bytes: usize, last: bool);
}
macro_rules! statistics {
    ($ty:ty) => {
        impl Statistics for $ty {
            fn resident(&self) -> usize {
                self.resident_bytes
            }

            fn hits(&self) -> u64 {
                self.hits
            }
            fn misses(&self) -> u64 {
                self.misses
            }
            fn decodes(&self) -> u64 {
                self.decodes
            }
            fn evictions(&self) -> u64 {
                self.evictions
            }
            fn hit(&mut self, n: u64) {
                self.hits = n;
            }
            fn miss(&mut self, n: u64) {
                self.misses = n;
            }
            fn decoded(&mut self, n: u64, bytes: usize) {
                self.decodes = n;
                self.construction_bytes = 0;
                self.resident_bytes += bytes;
                self.peak_resident_bytes = self.peak_resident_bytes.max(self.resident_bytes);
            }
            fn evicted(&mut self, bytes: usize) {
                self.resident_bytes -= bytes;
                self.evictions += 1;
            }
            fn pin(&mut self, bytes: usize, first: bool) {
                if first {
                    self.pinned_bytes += bytes;
                }
                self.peak_pinned_bytes = self.peak_pinned_bytes.max(self.pinned_bytes);
                self.active_pins += 1;
            }
            fn release(&mut self, bytes: usize, last: bool) {
                if last {
                    self.pinned_bytes -= bytes;
                }
                self.active_pins -= 1;
            }
        }
    };
}
pub(crate) use statistics;
statistics!(CacheUsage);

pub(crate) trait AlgorithmMeter: DecodeMeter {
    type Usage: Statistics;
    fn usage(&self) -> &Self::Usage;
    fn usage_mut(&mut self) -> &mut Self::Usage;
    fn detailed(
        &mut self,
        kind: CacheFailureKind,
        code: &'static str,
        attempted: u64,
        limit: u64,
    ) -> Self::Failure;
    fn base(&self) -> usize;
    fn capacity(&self) -> usize;
    fn entry_capacity(&self) -> usize;
    fn construction(&mut self, bytes: usize) -> Result<(), Self::Failure>;
    fn work_used(&self) -> u64;
    fn acquire_pin(&mut self) -> Result<(), Self::Failure>;
    fn abandon_pin(&mut self);
}
impl AlgorithmMeter for Meter<'_> {
    type Usage = CacheUsage;
    fn usage(&self) -> &CacheUsage {
        self.usage
    }
    fn usage_mut(&mut self) -> &mut CacheUsage {
        self.usage
    }
    fn detailed(
        &mut self,
        kind: CacheFailureKind,
        code: &'static str,
        attempted: u64,
        limit: u64,
    ) -> CacheFailure {
        failure(
            *self.usage,
            kind,
            code,
            self.function,
            self.offset,
            attempted,
            limit,
        )
    }
    fn base(&self) -> usize {
        self.usage.fixed_reserved + self.usage.scratch_reserved
    }
    fn capacity(&self) -> usize {
        self.budget.capacity_bytes
    }
    fn entry_capacity(&self) -> usize {
        self.budget.entry_bytes
    }
    fn construction(&mut self, bytes: usize) -> Result<(), CacheFailure> {
        self.usage.construction_bytes = bytes;
        update_peak(self.usage, self.budget)
    }
    fn work_used(&self) -> u64 {
        self.usage.work_used
    }
    fn acquire_pin(&mut self) -> Result<(), CacheFailure> {
        Ok(())
    }
    fn abandon_pin(&mut self) {}
}

pub(crate) trait CacheSlot {
    type Resident;
    fn entry(&self) -> Option<&DecodedFunction>;
    fn take(&mut self) -> Option<Self::Resident>;
    fn set(&mut self, resident: Self::Resident);
    fn pins(&self) -> usize;
    fn set_pins(&mut self, n: usize);
    fn last_used(&self) -> u64;
    fn set_last_used(&mut self, n: u64);
}
impl CacheSlot for Slot {
    type Resident = DecodedFunction;
    fn entry(&self) -> Option<&DecodedFunction> {
        self.entry.as_ref()
    }
    fn take(&mut self) -> Option<DecodedFunction> {
        self.entry.take()
    }
    fn set(&mut self, entry: DecodedFunction) {
        self.entry = Some(entry);
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
pub(crate) trait PinToken {
    fn new(owner: u64, slot: usize, nonce: u64) -> Self;
    fn owner(&self) -> u64;
    fn slot(&self) -> usize;
    fn nonce(&self) -> u64;
}
impl PinToken for FunctionPin {
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

pub(crate) trait CacheMode: sealed::Mode {
    type Snapshot: SnapshotView;
    type Slot: CacheSlot<Resident = Self::Resident>;
    type Resident;
    type Pin: PinToken;
    type Usage: Statistics;
    type Failure;
    type Operation<'a>;
    type Meter<'a, 'op>: AlgorithmMeter<Usage = Self::Usage, Failure = Self::Failure>
    where
        'op: 'a;
    type Scratch<'a>;
    fn meter<'a, 'op>(
        usage: &'a mut Self::Usage,
        operation: &'a mut Self::Operation<'op>,
        function: u32,
    ) -> Self::Meter<'a, 'op>
    where
        'op: 'a;
    fn scan(
        snapshot: &Self::Snapshot,
        body: FunctionSpanView<'_>,
        scratch: &mut Self::Scratch<'_>,
        meter: &mut Self::Meter<'_, '_>,
    ) -> Result<decode::Counts, Self::Failure>;
    fn build(
        snapshot: &Self::Snapshot,
        body: FunctionSpanView<'_>,
        counts: decode::Counts,
        scratch: &mut Self::Scratch<'_>,
        meter: &mut Self::Meter<'_, '_>,
    ) -> Result<Self::Resident, Self::Failure>;
    fn drop_entry(
        entry: Self::Resident,
        meter: &mut Self::Meter<'_, '_>,
    ) -> Result<(), Self::Failure>;
}
pub(crate) struct FrozenMode;
impl sealed::Mode for FrozenMode {}
pub(crate) struct FrozenOperation<'a> {
    pub budget: &'a CacheBudget,
    pub cancellation: &'a Cancellation,
}
impl CacheMode for FrozenMode {
    type Snapshot = ValidatedSpans;
    type Slot = Slot;
    type Resident = DecodedFunction;
    type Pin = FunctionPin;
    type Usage = CacheUsage;
    type Failure = CacheFailure;
    type Operation<'a> = FrozenOperation<'a>;
    type Meter<'a, 'op>
        = Meter<'a>
    where
        'op: 'a;
    type Scratch<'a> = ();
    fn meter<'a, 'op>(
        usage: &'a mut CacheUsage,
        operation: &'a mut FrozenOperation<'op>,
        function: u32,
    ) -> Meter<'a>
    where
        'op: 'a,
    {
        Meter {
            usage,
            budget: *operation.budget,
            cancellation: operation.cancellation,
            function: Some(function),
            offset: 0,
        }
    }
    fn scan(
        snapshot: &ValidatedSpans,
        body: FunctionSpanView<'_>,
        _: &mut (),
        meter: &mut Meter<'_>,
    ) -> Result<decode::Counts, CacheFailure> {
        decode::scan(
            body.body,
            body.body_offset,
            snapshot.policy(),
            snapshot.source().len(),
            meter,
            None,
        )
    }
    fn build(
        snapshot: &ValidatedSpans,
        body: FunctionSpanView<'_>,
        counts: decode::Counts,
        _: &mut (),
        meter: &mut Meter<'_>,
    ) -> Result<DecodedFunction, CacheFailure> {
        decode::build(
            body.body,
            body.body_offset,
            body.type_index,
            body.absolute_index,
            snapshot.policy(),
            snapshot.source().len(),
            counts,
            meter,
        )
    }
    fn drop_entry(entry: DecodedFunction, _: &mut Meter<'_>) -> Result<(), CacheFailure> {
        drop(entry);
        Ok(())
    }
}
pub(crate) struct CacheParts<'a, M: CacheMode> {
    pub snapshot: &'a M::Snapshot,
    pub slots: &'a mut [M::Slot],
    pub pins: &'a mut [PinRecord],
    pub owner: u64,
    pub next_nonce: &'a mut u64,
    pub usage: &'a mut M::Usage,
    pub scratch: M::Scratch<'a>,
}
pub(crate) struct CacheViewParts<'a, M: CacheMode> {
    pub slots: &'a [M::Slot],
    pub pins: &'a [PinRecord],
    pub owner: u64,
}

pub(crate) trait PinDiagnostic<F> {
    fn invalid(&mut self, code: &'static str) -> F;
}
impl<M: DecodeMeter> PinDiagnostic<M::Failure> for M {
    fn invalid(&mut self, code: &'static str) -> M::Failure {
        self.error(CacheFailureKind::InvalidPin, code)
    }
}
pub(crate) trait ReleaseControl<F>: PinDiagnostic<F> {
    fn release_pin(&mut self) -> Result<(), F>;
}
pub(crate) struct FrozenDiagnostics<'a> {
    pub usage: &'a CacheUsage,
}
impl PinDiagnostic<CacheFailure> for FrozenDiagnostics<'_> {
    fn invalid(&mut self, code: &'static str) -> CacheFailure {
        failure(
            *self.usage,
            CacheFailureKind::InvalidPin,
            code,
            None,
            0,
            0,
            0,
        )
    }
}
pub(crate) struct FrozenRelease {
    pub usage: CacheUsage,
}
impl PinDiagnostic<CacheFailure> for FrozenRelease {
    fn invalid(&mut self, code: &'static str) -> CacheFailure {
        failure(
            self.usage,
            CacheFailureKind::InvalidPin,
            code,
            None,
            0,
            0,
            0,
        )
    }
}
impl ReleaseControl<CacheFailure> for FrozenRelease {
    fn release_pin(&mut self) -> Result<(), CacheFailure> {
        Ok(())
    }
}
pub(crate) fn checked_record<M: CacheMode>(
    parts: CacheViewParts<'_, M>,
    pin: &M::Pin,
    meter: &mut impl PinDiagnostic<M::Failure>,
) -> Result<PinRecord, M::Failure> {
    if pin.owner() != parts.owner {
        return Err(meter.invalid("wrong_cache_owner"));
    }
    let record = parts
        .pins
        .get(pin.slot())
        .copied()
        .filter(|r| r.nonce != 0 && r.nonce == pin.nonce())
        .ok_or_else(|| meter.invalid("stale_pin"))?;
    if parts
        .slots
        .get(record.entry)
        .is_none_or(|s| s.pins() == 0 || s.entry().is_none())
    {
        return Err(meter.invalid("stale_entry"));
    }
    Ok(record)
}
pub(crate) fn view<'a, M: CacheMode>(
    parts: CacheViewParts<'a, M>,
    pin: &M::Pin,
    meter: &mut impl PinDiagnostic<M::Failure>,
) -> Result<FunctionView<'a>, M::Failure> {
    let record = checked_record::<M>(
        CacheViewParts {
            slots: parts.slots,
            pins: parts.pins,
            owner: parts.owner,
        },
        pin,
        meter,
    )?;
    let e = parts.slots[record.entry]
        .entry()
        .ok_or_else(|| meter.invalid("stale_entry"))?;
    Ok(FunctionView {
        function: e.function,
        type_index: e.type_index,
        body_offset: e.body_offset,
        locals: &e.locals,
        instructions: &e.instructions,
        branch_targets: &e.branch_targets,
    })
}
pub(crate) fn release<M: CacheMode>(
    parts: CacheParts<'_, M>,
    pin: M::Pin,
    operation: &mut impl ReleaseControl<M::Failure>,
) -> Result<(), (M::Failure, M::Pin)> {
    let record = match checked_record::<M>(
        CacheViewParts {
            slots: parts.slots,
            pins: parts.pins,
            owner: parts.owner,
        },
        &pin,
        operation,
    ) {
        Ok(r) => r,
        Err(e) => return Err((e, pin)),
    };
    if let Err(e) = operation.release_pin() {
        return Err((e, pin));
    }
    let slot = &mut parts.slots[record.entry];
    parts
        .usage
        .release(slot.entry().expect("checked entry").bytes, slot.pins() == 1);
    slot.set_pins(slot.pins() - 1);
    parts.pins[pin.slot()] = PinRecord::default();
    Ok(())
}
pub(crate) fn pin<M: CacheMode>(
    parts: CacheParts<'_, M>,
    function: u32,
    operation: &mut M::Operation<'_>,
) -> Result<M::Pin, M::Failure> {
    let CacheParts {
        snapshot,
        slots,
        pins,
        owner,
        next_nonce,
        usage,
        scratch,
    } = parts;
    let mut parts = CacheFields::<M> {
        snapshot,
        slots,
        pins,
        owner,
        next_nonce,
        scratch,
    };
    let mut meter = M::meter(usage, operation, function);
    meter.step(CacheStep::Lookup);
    meter.work(1)?;
    let defined = parts
        .snapshot
        .function(function)
        .ok_or_else(|| meter.error(CacheFailureKind::InvalidFunction, "not_defined_function"))?;
    meter.set_offset(defined.body_offset);
    let nonce = parts
        .next_nonce
        .checked_add(1)
        .ok_or_else(|| meter.error(CacheFailureKind::NonceExhausted, "pin_nonce_exhausted"))?;
    let mut pin_slot = None;
    for (index, record) in parts.pins.iter().enumerate() {
        meter.work(1)?;
        if record.nonce == 0 {
            pin_slot = Some(index);
            break;
        }
    }
    let pin_slot = pin_slot
        .ok_or_else(|| meter.error(CacheFailureKind::PinExhausted, "pin_slots_exhausted"))?;
    meter.acquire_pin()?;
    let result = pin_acquired::<M>(&mut parts, &mut meter, defined, pin_slot, nonce);
    if result.is_err() {
        meter.abandon_pin();
    }
    result
}
pub(crate) struct CacheFields<'a, M: CacheMode> {
    pub snapshot: &'a M::Snapshot,
    pub slots: &'a mut [M::Slot],
    pub pins: &'a mut [PinRecord],
    pub owner: u64,
    pub next_nonce: &'a mut u64,
    pub scratch: M::Scratch<'a>,
}
fn pin_acquired<M: CacheMode>(
    parts: &mut CacheFields<'_, M>,
    meter: &mut M::Meter<'_, '_>,
    defined: FunctionSpanView<'_>,
    pin_slot: usize,
    nonce: u64,
) -> Result<M::Pin, M::Failure> {
    let function = defined.absolute_index;
    let mut hit = None;
    for (index, slot) in parts.slots.iter().enumerate() {
        meter.work(1)?;
        if slot.entry().is_some_and(|e| e.function == function) {
            hit = Some(index);
            break;
        }
    }
    let index = if let Some(index) = hit {
        meter.check()?;
        let hits = meter
            .usage()
            .hits()
            .checked_add(1)
            .ok_or_else(|| meter.error(CacheFailureKind::WorkExhausted, "hits_overflow"))?;
        meter.usage_mut().hit(hits);
        index
    } else {
        let misses = meter
            .usage()
            .misses()
            .checked_add(1)
            .ok_or_else(|| meter.error(CacheFailureKind::WorkExhausted, "misses_overflow"))?;
        meter.usage_mut().miss(misses);
        let next_decodes = meter
            .usage()
            .decodes()
            .checked_add(1)
            .ok_or_else(|| meter.error(CacheFailureKind::WorkExhausted, "decodes_overflow"))?;
        let counts = M::scan(parts.snapshot, defined, &mut parts.scratch, meter)?;
        let bytes = counts.bytes(meter)?;
        if bytes > meter.entry_capacity() {
            return Err(meter.detailed(
                CacheFailureKind::EntryOversize,
                "entry_bytes",
                bytes as u64,
                meter.entry_capacity() as u64,
            ));
        }
        let base = meter.base();
        let capacity = meter.capacity();
        if base.checked_add(bytes).is_none_or(|n| n > capacity) {
            return Err(meter.error(CacheFailureKind::Capacity, "entry_cannot_fit"));
        }
        meter.step(CacheStep::Planning);
        let mut plan = [false; MAX_ENTRIES];
        let mut remaining = meter.usage().resident();
        meter.work(parts.slots.len() as u64)?;
        let mut empty = parts.slots.iter().position(|slot| slot.entry().is_none());
        while empty.is_none() || base + remaining + bytes > capacity {
            let mut oldest: Option<usize> = None;
            for (index, slot) in parts.slots.iter().enumerate() {
                meter.work(1)?;
                if !plan[index]
                    && slot.pins() == 0
                    && slot.entry().is_some()
                    && oldest.is_none_or(|p| slot.last_used() < parts.slots[p].last_used())
                {
                    oldest = Some(index);
                }
            }
            let victim = oldest
                .ok_or_else(|| meter.error(CacheFailureKind::AllPinned, "all_entries_pinned"))?;
            plan[victim] = true;
            remaining -= parts.slots[victim].entry().expect("selected entry").bytes;
            empty = Some(victim);
        }
        meter.work(MAX_ENTRIES as u64)?;
        let evictions = plan.iter().filter(|v| **v).count() as u64;
        meter
            .usage()
            .evictions()
            .checked_add(evictions)
            .ok_or_else(|| meter.error(CacheFailureKind::WorkExhausted, "evictions_overflow"))?;
        meter.check()?;
        for (index, selected) in plan.iter().enumerate().take(parts.slots.len()) {
            if *selected {
                let bytes = parts.slots[index].entry().expect("planned entry").bytes;
                let old = parts.slots[index].take().expect("planned entry");
                M::drop_entry(old, meter)?;
                meter.usage_mut().evicted(bytes);
            }
        }
        let index =
            empty.ok_or_else(|| meter.error(CacheFailureKind::Capacity, "no_entry_slot"))?;
        meter.construction(bytes)?;
        let decoded = M::build(parts.snapshot, defined, counts, &mut parts.scratch, meter);
        let entry = match decoded {
            Ok(entry) => entry,
            Err(error) => {
                let _ = meter.construction(0);
                return Err(error);
            }
        };
        meter.step(CacheStep::Publication);
        if let Err(error) = meter.check() {
            let _ = M::drop_entry(entry, meter);
            let _ = meter.construction(0);
            return Err(error);
        }
        meter.usage_mut().decoded(next_decodes, bytes);
        parts.slots[index].set(entry);
        index
    };
    let slot = &mut parts.slots[index];
    meter.usage_mut().pin(
        slot.entry().expect("resident entry").bytes,
        slot.pins() == 0,
    );
    slot.set_pins(slot.pins() + 1);
    slot.set_last_used(meter.work_used());
    parts.pins[pin_slot] = PinRecord {
        nonce: *parts.next_nonce,
        entry: index,
    };
    let pin = M::Pin::new(parts.owner, pin_slot, *parts.next_nonce);
    *parts.next_nonce = nonce;
    Ok(pin)
}
