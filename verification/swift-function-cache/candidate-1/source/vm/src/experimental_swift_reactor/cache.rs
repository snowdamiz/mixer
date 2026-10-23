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
fn sum_named(items: &[(usize, usize)]) -> Option<usize> {
    items.iter().try_fold(0usize, |n, (count, size)| {
        n.checked_add(count.checked_mul(*size)?)
    })
}
/// Permanent envelope: simultaneous *named Rust objects*, not stack/RSS claims.
/// Cache/header owner storage and every return/drop transfer remain covered until
/// CacheCleanupTail::complete has consumed the caller's empty owner/Result slots.
pub(crate) fn cache_cleanup_temporary_bytes() -> Option<usize> {
    sum_named(&[
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
pub(crate) fn cache_header_bytes() -> Option<usize> {
    size_of::<SwiftFunctionCache>()
        .checked_sub(size_of::<ValidatedSwiftReactor>())?
        .checked_add(cache_cleanup_temporary_bytes()?)
}
pub(crate) fn cache_construction_bytes() -> Option<usize> {
    sum_named(&[
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
pub(crate) fn cache_operation_bytes() -> Option<usize> {
    sum_named(&[
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
        self.control
            .work_with_wasi(Work::Cache, n, self.cursor, self.observation())
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
impl SwiftFunctionCache {
    pub(crate) const DECODER_REVISION: u32 = 1;
    pub(crate) fn prepare<'a>(
        control: &'a mut RuntimeControl,
        wasi: Option<&'a AccountedWasi>,
        adopted: &AdoptedProof,
        cursor: Cursor,
    ) -> Result<CacheConstructionPhase<'a>, SwiftRunFailure> {
        test_step(CacheStep::Constructor);
        let observation = pairing(control, wasi, cursor)?;
        control.check_adopted_owner(adopted, cursor, observation)?;
        let previous_bound = control.usage(observation).reservations.construction.current;
        let bound = cache_construction_bytes()
            .and_then(|n| previous_bound.checked_add(n))
            .ok_or_else(|| layout_failure(control, observation, cursor))?;
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
        let observation = pairing(control, wasi, cursor)?;
        let header = self
            .header
            .as_ref()
            .ok_or_else(|| layout_failure(control, observation, cursor))?;
        control.check_reservation_owner(header, cursor, observation)?;
        let previous_bound = control.usage(observation).reservations.construction.current;
        let bound = cache_operation_bytes()
            .and_then(|n| previous_bound.checked_add(n))
            .ok_or_else(|| layout_failure(control, observation, cursor))?;
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
        let owner = NEXT_OWNER
            .try_update(Ordering::Relaxed, Ordering::Relaxed, |n| n.checked_add(1))
            .map_err(|_| {
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
    // One Cache credit/check before each of 512 writes, in each sequential pass.
    for patch in patches {
        meter.work(1)?;
        *patch = decode::EMPTY_PATCH;
    }
    Ok(())
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
        let policy = policy(snapshot, body, meter)?;
        meter.step(CacheStep::ScanReset);
        reset(scratch, meter)?;
        meter.step(CacheStep::Scan);
        let mut depth = 0;
        let mut counts = decode::Counts::default();
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
        let policy = policy(snapshot, body, meter)?;
        meter.step(CacheStep::BuildReset);
        reset(scratch, meter)?;
        meter.step(CacheStep::Build);
        let mut depth = 0;
        let mut actual = decode::Counts::default();
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
    pub fn tail_construction(tail: &CacheCleanupTail<'_>) -> usize {
        tail.control
            .usage(tail.wasi.map(AccountedWasi::usage))
            .reservations
            .construction
            .current
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
        row!(ValidatedSwiftReactor);
        row!(RuntimeControl);
        row!(AdoptedProof);
        row!(Option<AdoptedProof>);
        row!(SwiftCacheUsage);
        row!(DecodedFunction);
        row!(decode::Counts);
        row!(FunctionSpanView<'static>);
        row!(CacheViewParts<'static, SwiftMode>);
        row!(SwiftReleaseFailure);
        row!(Result<(),SwiftReleaseFailure>);
        row!(Result<SwiftResident,SwiftRunFailure>);
        row!(Result<DecodedFunction,SwiftRunFailure>);
        row!(Result<SwiftFunctionPin,SwiftRunFailure>);
        row!(Vec<SwiftSlot>);
        row!(Vec<PinRecord>);
        row!([bool; 64]);
        row!(crate::Type);
        row!(crate::experimental::cache::DecodedInstruction);
        row!(u32);
        row!(ConstructionReturnSlot);
        row!(OperationReturnSlot);
        row!(Result<SwiftFunctionCache,SwiftRunFailure>);
        row!(SwiftFunctionCache);
        row!(Option<SwiftFunctionCache>);
        row!(SwiftResident);
        row!(Option<SwiftResident>);
        row!(SwiftSlot);
        row!(SwiftFunctionPin);
        row!(CacheControl<'static>);
        row!(CacheConstructionPhase<'static>);
        row!(CacheOperationPhase<'static>);
        row!(Partial);
        row!(CacheConstructionFailure);
        row!(Result<SwiftFunctionCache,CacheConstructionFailure>);
        row!(CacheCleanupTail<'static>);
        row!(CleanupCompletionParts<'static>);
        row!(Option<CacheCleanupTail<'static>>);
        row!(Result<CacheCleanupTail<'static>, SwiftRunFailure>);
        row!(SwiftRunFailure);
        row!(Option<SwiftRunFailure>);
        row!(Result<(),SwiftRunFailure>);
        row!(SwiftRunUsage);
        row!(ReservationTicket);
        row!(Option<ReservationTicket>);
        row!(WasiUsage);
        row!(Option<WasiUsage>);
        row!(Fault);
        row!(Cursor);
        row!(SwiftMeter<'static, 'static>);
        row!(CacheParts<'static, SwiftMode>);
        row!(CacheFields<'static, SwiftMode>);
        row!(SwiftPolicy<'static>);
        row!(decode::PassParts<'static>);
        row!(decode::Patch);
        row!(Vec<decode::Patch>);
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
