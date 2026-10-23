//! Experimental, Rust-only capability mailbox. This does not admit Wasm imports,
//! execute adapters, implement a wire codec, or participate in the VM registry.
//!
//! All payloads here are opaque bytes. A future trusted bridge must strictly
//! validate and bind their operation/schema/grants before native I/O or posting.
//! Built-in failures are typed values, **not** the proposed JSON wire envelope.
//! No guest memory offsets, pointers, callbacks, scheduler, fuel or byte charging,
//! C ABI/panic boundary, process/session quota, or release admission is provided.
//!
//! The owner must retain this value through all native exit acknowledgements.
//! `close` retains its running entries while the mailbox exists; a standalone
//! value cannot enforce the existing VM registry's counted closing lifecycle.
//! Standard-library synchronization may allocate infallibly on first lock (64
//! bytes observed on this macOS host); payload reservation excludes that fixed
//! overhead. Fallible payload copies do not establish general OOM/panic safety.

use std::sync::{
    atomic::{AtomicU64, Ordering},
    Mutex, MutexGuard,
};
use std::time::{Duration, Instant};

pub const MAX_REQUESTS: usize = 8;
pub const MAX_PAYLOAD_BYTES: usize = 524_288;
pub const MAX_RESERVATION_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_TIMEOUT_MILLISECONDS: u32 = 30_000;

/// Only narrowing is supported. Reservation bytes include each argument length
/// plus one maximum completion, irrespective of actual allocation/delivery size.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Limits {
    pub maximum_requests: usize,
    pub reservation_bytes: usize,
    pub timeout_milliseconds: u32,
}
impl Default for Limits {
    fn default() -> Self {
        Self {
            maximum_requests: MAX_REQUESTS,
            reservation_bytes: MAX_RESERVATION_BYTES,
            timeout_milliseconds: MAX_TIMEOUT_MILLISECONDS,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Operation {
    HttpRequest,
    Get,
    Put,
    Delete,
}

/// These allocation-free errors are Rust experimental results, not C statuses
/// or the proposed guest transport return-code mapping.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Error {
    InvalidLimits,
    InvalidArguments,
    QuotaExceeded,
    AllocationFailure,
    IdentifierExhausted,
    SessionClosed,
    Poisoned,
    TurnActive,
    InvalidTurn,
    StaleRequest,
    AlreadyTerminal,
    AlreadyAcknowledged,
}

/// Opaque Rust ownership context. Equal `token_bits` in different mailboxes do
/// not identify the same request. This API does not validate hostile raw guest
/// tokens; that remains an explicit guest-import integration requirement.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RequestId {
    owner: u64,
    bits: u64,
}
impl RequestId {
    pub fn token_bits(self) -> u64 {
        self.bits
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TurnId {
    owner: u64,
    sequence: u64,
}

/// A successful call take establishes one exit obligation. Cloning/copying this
/// opaque identity does not establish another obligation; duplicate acks reject.
/// Dropping it never acknowledges native exit. `ack_exit` borrows it, so an error
/// cannot accidentally consume the only identity needed for a retry.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct NativeLease {
    request: RequestId,
    operation: Operation,
}
impl NativeLease {
    pub fn request(self) -> RequestId {
        self.request
    }
    pub fn operation(self) -> Operation {
        self.operation
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FailureCode {
    Unavailable,
    Cancelled,
    DeadlineExceeded,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Poll {
    Pending,
    BufferTooSmall {
        required: usize,
    },
    /// Exactly `length` bytes were copied; remaining destination bytes unchanged.
    Ready {
        length: usize,
    },
    /// No bytes were written. Encoding a future wire completion is separate.
    Failure(FailureCode),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Take {
    None,
    BufferTooSmall {
        required: usize,
    },
    Call {
        lease: NativeLease,
        length: usize,
        remaining_milliseconds: u32,
    },
    Cancel {
        lease: NativeLease,
    },
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TurnOutcome {
    Success,
    Trap,
}
/// Fixed bounded cancellation identities for the coordinator to act on after
/// the mutex is released. Repeat close reports still-running leases again.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CloseReport {
    pub cancellations: [Option<NativeLease>; MAX_REQUESTS],
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Usage {
    pub outstanding_requests: usize,
    pub native_leases: usize,
    pub reserved_bytes: usize,
    /// Actual retained Vec capacities, excludes this fixed metadata, allocator
    /// overhead, the caller's buffers, and all future native/bridge/codec copies.
    pub argument_bytes: usize,
    pub completion_bytes: usize,
    pub retired_slots: usize,
    pub closed: bool,
    pub enabled: bool,
    pub turn_active: bool,
}

pub struct Mailbox {
    owner: u64,
    limits: Limits,
    state: Mutex<State>,
}
struct State {
    enabled: bool,
    closed: bool,
    active_turn: Option<u64>,
    last_turn: u64,
    reserved_bytes: usize,
    slots: [Slot; MAX_REQUESTS],
}
struct Slot {
    generation: u32,
    retired: bool,
    request: Option<Request>,
}
struct Request {
    operation: Operation,
    turn: u64,
    ready: bool,
    enqueued: Instant,
    deadline: Instant,
    arguments: Vec<u8>,
    reservation: usize,
    dispatched: bool,
    native_done: bool,
    cancel_pending: bool,
    terminal: Option<Terminal>,
    consumed: bool,
}
enum Terminal {
    Payload(Vec<u8>),
    Failure(FailureCode),
}

// Owner zero is never issued; wrapping can never alias a previous mailbox.
static NEXT_OWNER: AtomicU64 = AtomicU64::new(1);
fn issue_owner(counter: &AtomicU64) -> Result<u64, Error> {
    let mut current = counter.load(Ordering::Relaxed);
    loop {
        let next = current.checked_add(1).ok_or(Error::IdentifierExhausted)?;
        match counter.compare_exchange_weak(current, next, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return Ok(current),
            Err(observed) => current = observed,
        }
    }
}
fn snapshot(bytes: &[u8]) -> Result<Vec<u8>, Error> {
    let mut result = Vec::new();
    result
        .try_reserve_exact(bytes.len())
        .map_err(|_| Error::AllocationFailure)?;
    // Reject unusual allocator over-allocation instead of understating retained
    // capacity. No reallocating shrink/boxing step can abort on a second OOM.
    if result.capacity() != bytes.len() {
        return Err(Error::AllocationFailure);
    }
    result.extend_from_slice(bytes);
    Ok(result)
}
fn remaining(deadline: Instant, now: Instant) -> u32 {
    deadline
        .saturating_duration_since(now)
        .as_millis()
        .min(u32::MAX as u128) as u32
}
impl Request {
    fn fail(&mut self, failure: FailureCode) {
        if self.terminal.is_none() && !self.consumed {
            self.terminal = Some(Terminal::Failure(failure));
            self.cancel_pending = self.dispatched && !self.native_done;
        }
    }
    fn expire(&mut self, now: Instant) {
        if now >= self.deadline {
            self.fail(FailureCode::DeadlineExceeded);
        }
    }
}
impl State {
    fn new() -> Self {
        Self {
            enabled: false,
            closed: false,
            active_turn: None,
            last_turn: 0,
            reserved_bytes: 0,
            slots: std::array::from_fn(|_| Slot {
                generation: 1,
                retired: false,
                request: None,
            }),
        }
    }
    fn live(&self) -> Result<(), Error> {
        if self.closed {
            Err(Error::SessionClosed)
        } else {
            Ok(())
        }
    }
    fn expire(&mut self, now: Instant) {
        for slot in &mut self.slots {
            if let Some(request) = &mut slot.request {
                request.expire(now);
            }
        }
    }
    fn index(&self, owner: u64, id: RequestId, delivery: bool) -> Result<usize, Error> {
        if id.owner != owner || (id.bits >> 32) == 0 {
            return Err(Error::StaleRequest);
        }
        let index = (id.bits as u32).checked_sub(1).ok_or(Error::StaleRequest)? as usize;
        let slot = self.slots.get(index).ok_or(Error::StaleRequest)?;
        let request = slot.request.as_ref().ok_or(Error::StaleRequest)?;
        if slot.generation != (id.bits >> 32) as u32 || (delivery && request.consumed) {
            return Err(Error::StaleRequest);
        }
        Ok(index)
    }
    fn lease_index(&self, owner: u64, lease: &NativeLease) -> Result<usize, Error> {
        let index = self.index(owner, lease.request, false)?;
        let request = self.slots[index].request.as_ref().unwrap();
        if !request.dispatched || request.operation != lease.operation {
            return Err(Error::StaleRequest);
        }
        Ok(index)
    }
    fn release(&mut self, index: usize) {
        let request = self.slots[index].request.take().unwrap();
        let reservation = request.reservation;
        drop(request); // retained allocation destruction completes before reuse/accounting release
        self.reserved_bytes -= reservation;
        let slot = &mut self.slots[index];
        if let Some(next) = slot.generation.checked_add(1) {
            slot.generation = next;
        } else {
            slot.retired = true;
        }
    }
    fn close(&mut self, owner: u64) -> CloseReport {
        self.closed = true;
        self.active_turn = None;
        let mut report = CloseReport {
            cancellations: [None; MAX_REQUESTS],
        };
        for index in 0..MAX_REQUESTS {
            let slot = &mut self.slots[index];
            let Some(request) = &mut slot.request else {
                continue;
            };
            if request.dispatched && !request.native_done {
                // Drop undelivered result, retain argument storage and its full
                // reservation until actual native exit is acknowledged.
                request.terminal = None;
                request.consumed = true;
                request.cancel_pending = false;
                report.cancellations[index] = Some(NativeLease {
                    request: RequestId {
                        owner,
                        bits: ((slot.generation as u64) << 32) | (index as u64 + 1),
                    },
                    operation: request.operation,
                });
            } else {
                self.release(index);
            }
        }
        report
    }
}

impl Mailbox {
    /// Construction has fixed inline state and does not allocate. The process
    /// owner-ID counter is an identity mechanism, not a process mailbox quota.
    pub fn new(limits: Limits) -> Result<Self, Error> {
        if limits.maximum_requests == 0
            || limits.maximum_requests > MAX_REQUESTS
            || limits.reservation_bytes == 0
            || limits.reservation_bytes > MAX_RESERVATION_BYTES
            || limits.timeout_milliseconds == 0
            || limits.timeout_milliseconds > MAX_TIMEOUT_MILLISECONDS
        {
            return Err(Error::InvalidLimits);
        }
        Ok(Self {
            owner: issue_owner(&NEXT_OWNER)?,
            limits,
            state: Mutex::new(State::new()),
        })
    }
    fn lock(&self) -> Result<MutexGuard<'_, State>, Error> {
        self.state.lock().map_err(|_| Error::Poisoned)
    }
    /// One-way opening after startup. Previously unavailable calls remain so.
    pub fn enable(&self) -> Result<(), Error> {
        let mut state = self.lock()?;
        state.live()?;
        state.enabled = true;
        Ok(())
    }
    pub fn begin_turn(&self) -> Result<TurnId, Error> {
        let mut state = self.lock()?;
        state.live()?;
        if state.active_turn.is_some() {
            return Err(Error::TurnActive);
        }
        let sequence = state
            .last_turn
            .checked_add(1)
            .ok_or(Error::IdentifierExhausted)?;
        state.last_turn = sequence;
        state.active_turn = Some(sequence);
        Ok(TurnId {
            owner: self.owner,
            sequence,
        })
    }
    /// A stale/foreign finish, including a trap, cannot affect a newer turn.
    /// A real trap closes all ownership; returned leases must be cancelled by
    /// the future coordinator outside this mailbox, then acknowledged on exit.
    pub fn finish_turn(
        &self,
        turn: TurnId,
        outcome: TurnOutcome,
    ) -> Result<Option<CloseReport>, Error> {
        let mut state = self.lock()?;
        state.live()?;
        if turn.owner != self.owner || state.active_turn != Some(turn.sequence) {
            return Err(Error::InvalidTurn);
        }
        if outcome == TurnOutcome::Trap {
            return Ok(Some(state.close(self.owner)));
        }
        state.expire(Instant::now());
        for slot in &mut state.slots {
            if let Some(request) = &mut slot.request {
                if request.turn == turn.sequence {
                    request.ready = true;
                }
            }
        }
        state.active_turn = None;
        Ok(None)
    }
    /// Budget/slot/range checks precede the only fallible payload allocation.
    /// Failure publishes no token or reservation and changes no turn state.
    pub fn enqueue(
        &self,
        turn: TurnId,
        operation: Operation,
        arguments: &[u8],
    ) -> Result<RequestId, Error> {
        if arguments.is_empty() || arguments.len() > MAX_PAYLOAD_BYTES {
            return Err(Error::InvalidArguments);
        }
        let mut state = self.lock()?;
        state.live()?;
        if turn.owner != self.owner || state.active_turn != Some(turn.sequence) {
            return Err(Error::InvalidTurn);
        }
        let reservation = arguments
            .len()
            .checked_add(MAX_PAYLOAD_BYTES)
            .ok_or(Error::QuotaExceeded)?;
        let reserved = state
            .reserved_bytes
            .checked_add(reservation)
            .ok_or(Error::QuotaExceeded)?;
        if reserved > self.limits.reservation_bytes {
            return Err(Error::QuotaExceeded);
        }
        let index = state.slots[..self.limits.maximum_requests]
            .iter()
            .position(|s| !s.retired && s.request.is_none())
            .ok_or(Error::QuotaExceeded)?;
        let arguments = snapshot(arguments)?;
        // Only this private clock is authoritative, after the successful copy.
        let enqueued = Instant::now();
        let deadline = enqueued
            .checked_add(Duration::from_millis(
                self.limits.timeout_milliseconds as u64,
            ))
            .ok_or(Error::InvalidLimits)?;
        let terminal = if state.enabled {
            None
        } else {
            Some(Terminal::Failure(FailureCode::Unavailable))
        };
        state.slots[index].request = Some(Request {
            operation,
            turn: turn.sequence,
            ready: false,
            enqueued,
            deadline,
            arguments,
            reservation,
            dispatched: false,
            native_done: false,
            cancel_pending: false,
            terminal,
            consumed: false,
        });
        state.reserved_bytes = reserved;
        Ok(RequestId {
            owner: self.owner,
            bits: ((state.slots[index].generation as u64) << 32) | (index as u64 + 1),
        })
    }
    /// Cancellation controls have priority and may drain during an active turn.
    /// Calls cannot drain during any turn, nor before their successful finish.
    /// Too-small outputs leave every byte unchanged and retain the entire call.
    pub fn take(&self, output: &mut [u8]) -> Result<Take, Error> {
        if output.len() > MAX_PAYLOAD_BYTES {
            return Err(Error::InvalidArguments);
        }
        let mut state = self.lock()?;
        state.live()?;
        let now = Instant::now();
        state.expire(now);
        for index in 0..MAX_REQUESTS {
            let slot = &mut state.slots[index];
            let Some(request) = &mut slot.request else {
                continue;
            };
            if request.cancel_pending {
                request.cancel_pending = false;
                return Ok(Take::Cancel {
                    lease: NativeLease {
                        request: RequestId {
                            owner: self.owner,
                            bits: ((slot.generation as u64) << 32) | (index as u64 + 1),
                        },
                        operation: request.operation,
                    },
                });
            }
        }
        if state.active_turn.is_some() {
            return Ok(Take::None);
        }
        for index in 0..MAX_REQUESTS {
            let slot = &mut state.slots[index];
            let Some(request) = &mut slot.request else {
                continue;
            };
            if request.ready
                && !request.dispatched
                && request.terminal.is_none()
                && !request.consumed
            {
                let remaining_milliseconds = remaining(request.deadline, Instant::now());
                if remaining_milliseconds == 0 {
                    request.fail(FailureCode::DeadlineExceeded);
                    continue;
                }
                let length = request.arguments.len();
                if output.len() < length {
                    return Ok(Take::BufferTooSmall { required: length });
                }
                // Linearize before the infallible bounded copy. No error path
                // follows an output write. The bridge must recheck/narrow the
                // original deadline immediately before actual native I/O.
                request.dispatched = true;
                output[..length].copy_from_slice(&request.arguments);
                return Ok(Take::Call {
                    lease: NativeLease {
                        request: RequestId {
                            owner: self.owner,
                            bits: ((slot.generation as u64) << 32) | (index as u64 + 1),
                        },
                        operation: request.operation,
                    },
                    length,
                    remaining_milliseconds,
                });
            }
        }
        Ok(Take::None)
    }
    /// Copies one opaque completion. Strict payload validation is a separate
    /// bridge obligation. Terminal success is not proof of adapter exit.
    /// Late/duplicate post cannot replace a cancellation/deadline/other result.
    pub fn post(&self, lease: &NativeLease, completion: &[u8]) -> Result<(), Error> {
        if completion.is_empty() || completion.len() > MAX_PAYLOAD_BYTES {
            return Err(Error::InvalidArguments);
        }
        let mut state = self.lock()?;
        state.live()?;
        let index = state.lease_index(self.owner, lease)?;
        let request = state.slots[index].request.as_mut().unwrap();
        request.expire(Instant::now());
        if request.consumed {
            return Err(Error::StaleRequest);
        }
        if request.terminal.is_some() {
            return Err(Error::AlreadyTerminal);
        }
        if request.native_done {
            return Err(Error::AlreadyAcknowledged);
        }
        let bytes = snapshot(completion)?;
        // Allocation/copy delay cannot authorize a late native success.
        request.expire(Instant::now());
        if request.terminal.is_some() {
            return Err(Error::AlreadyTerminal);
        }
        request.terminal = Some(Terminal::Payload(bytes));
        Ok(())
    }
    /// Actual adapter exit is independent of completion. An early ack is
    /// accepted, blocks future post, and retains pending delivery until its
    /// deadline/cancellation. It never reclaims a pending or unconsumed result.
    pub fn ack_exit(&self, lease: &NativeLease) -> Result<(), Error> {
        let mut state = self.lock()?;
        let index = state.lease_index(self.owner, lease)?;
        let closed = state.closed;
        let request = state.slots[index].request.as_mut().unwrap();
        if request.native_done {
            return Err(Error::AlreadyAcknowledged);
        }
        request.native_done = true;
        request.cancel_pending = false;
        if !closed {
            request.expire(Instant::now());
        }
        if closed || request.consumed {
            state.release(index);
        }
        Ok(())
    }
    /// Applies min(previous deadline, original enqueue + timeout), never now +
    /// timeout. Floored zero remaining installs expiry before future I/O.
    pub fn limit_deadline(
        &self,
        lease: &NativeLease,
        timeout_milliseconds: u32,
    ) -> Result<u32, Error> {
        if timeout_milliseconds == 0 || timeout_milliseconds > MAX_TIMEOUT_MILLISECONDS {
            return Err(Error::InvalidArguments);
        }
        let mut state = self.lock()?;
        state.live()?;
        let index = state.lease_index(self.owner, lease)?;
        let request = state.slots[index].request.as_mut().unwrap();
        request.expire(Instant::now());
        if request.consumed {
            return Err(Error::StaleRequest);
        }
        if request.terminal.is_some() {
            return Err(Error::AlreadyTerminal);
        }
        if request.native_done {
            return Err(Error::AlreadyAcknowledged);
        }
        let proposed = request
            .enqueued
            .checked_add(Duration::from_millis(timeout_milliseconds as u64))
            .ok_or(Error::InvalidArguments)?;
        request.deadline = request.deadline.min(proposed);
        let remaining = remaining(request.deadline, Instant::now());
        if remaining == 0 {
            request.fail(FailureCode::DeadlineExceeded);
        }
        Ok(remaining)
    }
    pub fn cancel(&self, id: RequestId) -> Result<(), Error> {
        let mut state = self.lock()?;
        state.live()?;
        let index = state.index(self.owner, id, true)?;
        let request = state.slots[index].request.as_mut().unwrap();
        request.expire(Instant::now());
        if request.terminal.is_some() {
            return Err(Error::AlreadyTerminal);
        }
        request.fail(FailureCode::Cancelled);
        Ok(())
    }
    /// Slice capacities include zero and are bounded even for pending/failure.
    /// Pending/too-small/error writes nothing; Ready copies in full and consumes
    /// once. Delivery consumption alone does not release a running native lease.
    pub fn poll(&self, id: RequestId, output: &mut [u8]) -> Result<Poll, Error> {
        if output.len() > MAX_PAYLOAD_BYTES {
            return Err(Error::InvalidArguments);
        }
        let mut state = self.lock()?;
        state.live()?;
        let index = state.index(self.owner, id, true)?;
        let request = state.slots[index].request.as_mut().unwrap();
        request.expire(Instant::now());
        let Some(terminal) = &request.terminal else {
            return Ok(Poll::Pending);
        };
        let result = match terminal {
            Terminal::Payload(bytes) => {
                if output.len() < bytes.len() {
                    return Ok(Poll::BufferTooSmall {
                        required: bytes.len(),
                    });
                }
                output[..bytes.len()].copy_from_slice(bytes);
                Poll::Ready {
                    length: bytes.len(),
                }
            }
            Terminal::Failure(failure) => Poll::Failure(*failure),
        };
        request.consumed = true;
        request.terminal = None;
        if !request.dispatched || request.native_done {
            state.release(index);
        }
        Ok(result)
    }
    /// Bounded scan; runs no native work or guest code. Expiry does not release
    /// guest delivery or native exit obligations.
    pub fn expire(&self) -> Result<(), Error> {
        let mut state = self.lock()?;
        state.live()?;
        state.expire(Instant::now());
        Ok(())
    }
    pub fn close(&self) -> Result<CloseReport, Error> {
        Ok(self.lock()?.close(self.owner))
    }
    /// Observation does not advance deadlines. Closed state remains observable.
    pub fn usage(&self) -> Result<Usage, Error> {
        let state = self.lock()?;
        let mut usage = Usage {
            reserved_bytes: state.reserved_bytes,
            closed: state.closed,
            enabled: state.enabled,
            turn_active: state.active_turn.is_some(),
            ..Usage::default()
        };
        for slot in &state.slots {
            if slot.retired {
                usage.retired_slots += 1;
            }
            if let Some(request) = &slot.request {
                usage.outstanding_requests += 1;
                usage.native_leases += usize::from(request.dispatched && !request.native_done);
                usage.argument_bytes += request.arguments.capacity();
                if let Some(Terminal::Payload(bytes)) = &request.terminal {
                    usage.completion_bytes += bytes.capacity();
                }
            }
        }
        Ok(usage)
    }
}

#[cfg(feature = "experimental-capability-guest")]
mod guest;

#[cfg(test)]
mod tests;
