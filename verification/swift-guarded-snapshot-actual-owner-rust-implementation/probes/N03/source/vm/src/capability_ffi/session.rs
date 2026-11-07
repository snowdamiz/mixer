//! Native session payload and fixed ticket ledger; intentionally no global pool.
//! Root's shared registry obtains/drops transient leases under its own lock.
//! This module never calls the registry or acquires its lock.
use super::{
    error::{self, Failure},
    types::*,
};
use crate::{
    experimental_capability as mb,
    experimental_capability_guest::{CapabilityGuest, CapabilityPort, DispatchLease, NativeTake},
    Cancellation, Limits,
};
use std::{
    ops::Deref,
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        Mutex, MutexGuard, TryLockError,
    },
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum AccessMode {
    Live,
    AckClosing,
}
/// Crate-private, statically selected root adapter; never implemented by users.
pub(crate) trait Reservation {
    fn publish(self, session: CapabilitySession) -> Result<u64, Failure>;
}
pub(crate) trait Registry {
    type Reservation: Reservation;
    type Lease: Deref<Target = CapabilitySession>;
    fn reserve(&self) -> Result<Self::Reservation, Failure>;
    fn get(&self, handle: u64, mode: AccessMode) -> Result<Self::Lease, Failure>;
    /// Moves only the matching capability variant Live->Closing under registry,
    /// calls mark_terminal without locks, and returns a retained transient lease.
    /// Caller must invoke close_native outside registry. Repeated close rejects3.
    fn close(&self, handle: u64) -> Result<Self::Lease, Failure>;
}
struct Ticket {
    lease: DispatchLease,
    acknowledged: bool,
}
struct Ledger {
    entries: [Option<Ticket>; mb::MAX_REQUESTS],
}
pub(crate) struct CapabilitySession {
    guest: Mutex<CapabilityGuest>,
    port: CapabilityPort,
    pub(crate) limits: Limits,
    cancellation: Cancellation,
    terminal: AtomicBool,
    quarantined: AtomicBool,
    outstanding: AtomicUsize,
    ledger: Mutex<Ledger>,
}
impl CapabilitySession {
    pub(crate) fn new(guest: CapabilityGuest, limits: Limits) -> Self {
        let port = guest.native_port();
        let cancellation = guest.cancellation();
        Self {
            guest: Mutex::new(guest),
            port,
            limits,
            cancellation,
            terminal: AtomicBool::new(false),
            quarantined: AtomicBool::new(false),
            outstanding: AtomicUsize::new(0),
            ledger: Mutex::new(Ledger {
                entries: std::array::from_fn(|_| None),
            }),
        }
    }
    /// Nonlocking phase permitted under registry; no mailbox/ledger access.
    pub(crate) fn mark_terminal(&self) {
        self.terminal.store(true, Ordering::Release);
        self.cancellation.cancel();
    }
    pub(crate) fn quarantine(&self) {
        self.quarantined.store(true, Ordering::Release);
        self.mark_terminal();
    }
    pub(crate) fn outstanding(&self) -> usize {
        self.outstanding.load(Ordering::Acquire)
    }
    pub(crate) fn quarantined(&self) -> bool {
        self.quarantined.load(Ordering::Acquire)
    }
    /// Only root may use this after synchronized transient lease release while
    /// its Closing Arc still prevents destruction. It is not a standalone proof.
    pub(crate) fn reclaim_ready(&self) -> bool {
        self.outstanding() == 0 && !self.quarantined()
    }
    pub(crate) fn ensure_live(&self) -> Result<(), Failure> {
        if self.quarantined() {
            Err(Failure::poisoned())
        } else if self.terminal.load(Ordering::Acquire) || self.cancellation.is_cancelled() {
            Err(Failure::terminal())
        } else {
            Ok(())
        }
    }
    pub(crate) fn close_native(&self) -> Result<(), Failure> {
        self.mark_terminal();
        self.port
            .close()
            .map(|_| ())
            .map_err(|e| self.mailbox_error(e))
    }
    fn mailbox_error(&self, e: mb::Error) -> Failure {
        if e == mb::Error::Poisoned {
            self.quarantine();
        }
        error::mailbox(e)
    }
    fn invariant(&self, message: &'static str) -> Failure {
        self.quarantine();
        Failure::invariant(message)
    }
    fn ledger(&self) -> Result<MutexGuard<'_, Ledger>, Failure> {
        self.ledger.lock().map_err(|_| {
            self.quarantine();
            Failure::poisoned()
        })
    }
    pub(crate) fn guest(&self) -> Result<MutexGuard<'_, CapabilityGuest>, Failure> {
        self.ensure_live()?;
        let guard = match self.guest.try_lock() {
            Ok(guard) => guard,
            Err(TryLockError::WouldBlock) => {
                return Err(Failure {
                    status: 3,
                    code: "session_busy",
                    message: "another guest operation is running",
                })
            }
            Err(TryLockError::Poisoned(_)) => {
                self.quarantine();
                return Err(Failure::poisoned());
            }
        };
        self.ensure_live()?;
        Ok(guard)
    }
    pub(crate) fn unwind_guard(&self) -> UnwindGuard<'_> {
        UnwindGuard {
            session: self,
            armed: true,
            require_commit: false,
        }
    }
    pub(crate) fn take<'a>(&'a self, output: &mut [u8]) -> Result<PreparedTake<'a>, Failure> {
        self.ensure_live()?;
        if output.len() > mb::MAX_PAYLOAD_BYTES {
            return Err(Failure::api("take buffer exceeds payload limit"));
        }
        let mut ledger = self.ledger()?;
        self.ensure_live()?;
        let mut guard = self.unwind_guard();
        guard.require_commit = true;
        let taken = match self.port.take(output) {
            Ok(t) => t,
            Err(e) => {
                guard.disarm();
                return Err(self.mailbox_error(e));
            }
        };
        let mut message = MixerVmCapabilityMessageV1::default();
        match taken {
            NativeTake::None => guard.disarm(),
            NativeTake::BufferTooSmall { required } => {
                message.kind = 3;
                message.payload_length = required as u32;
                guard.disarm();
            }
            NativeTake::Cancel { lease } => {
                let index = slot(lease.token_bits())
                    .ok_or_else(|| self.invariant("cancel returned malformed token"))?;
                let entry = ledger.entries[index]
                    .as_ref()
                    .ok_or_else(|| self.invariant("cancel has no native ticket"))?;
                if entry.acknowledged
                    || entry.lease.token_bits() != lease.token_bits()
                    || entry.lease.operation() != lease.operation()
                {
                    return Err(self.invariant("cancel does not match pending ticket"));
                }
                message.kind = 2;
                message.operation = operation(lease.operation());
                message.token = lease.token_bits();
                guard.disarm();
            }
            NativeTake::Call {
                lease,
                length,
                remaining_milliseconds,
            } => {
                let index = slot(lease.token_bits())
                    .ok_or_else(|| self.invariant("call returned malformed token"))?;
                if let Some(old) = &ledger.entries[index] {
                    if !old.acknowledged || old.lease.token_bits() >> 32 >= lease.token_bits() >> 32
                    {
                        return Err(
                            self.invariant("unacknowledged or nonmonotonic ticket replacement")
                        );
                    }
                }
                if self.outstanding() >= mb::MAX_REQUESTS {
                    return Err(self.invariant("native obligation count exceeds ledger"));
                }
                message.kind = 1;
                message.operation = operation(lease.operation());
                message.token = lease.token_bits();
                message.payload_length = length as u32;
                message.remaining_milliseconds = remaining_milliseconds;
                self.outstanding.fetch_add(1, Ordering::Release);
                ledger.entries[index] = Some(Ticket {
                    lease,
                    acknowledged: false,
                });
                // Keep guard armed through the caller's message/report writes.
            }
        }
        Ok(PreparedTake { message, guard })
    }
    fn ticket<'a>(
        &self,
        ledger: &'a mut Ledger,
        token: u64,
        op: u32,
    ) -> Result<&'a mut Ticket, Failure> {
        let index = slot(token).ok_or_else(|| Failure::api("invalid request token"))?;
        let entry = ledger.entries[index]
            .as_mut()
            .ok_or_else(|| Failure::api("request has no native ticket"))?;
        if entry.lease.token_bits() != token || operation(entry.lease.operation()) != op {
            return Err(Failure::api("stale token or operation mismatch"));
        }
        Ok(entry)
    }
    pub(crate) fn post(
        &self,
        token: u64,
        op: u32,
        bytes: &[u8],
    ) -> Result<MixerVmCapabilityResultV1, Failure> {
        self.ensure_live()?;
        if bytes.is_empty() || bytes.len() > mb::MAX_PAYLOAD_BYTES {
            return Err(Failure::api("invalid completion length"));
        }
        let mut ledger = self.ledger()?;
        self.ensure_live()?;
        let entry = self.ticket(&mut ledger, token, op)?;
        let mut guard = self.unwind_guard();
        let result = match self.port.post_trusted(&entry.lease, bytes) {
            Ok(()) => Ok(MixerVmCapabilityResultV1::default()),
            Err(mb::Error::AlreadyTerminal) => Ok(MixerVmCapabilityResultV1 {
                kind: 1,
                ..Default::default()
            }),
            Err(e) => Err(self.mailbox_error(e)),
        };
        guard.disarm();
        result
    }
    pub(crate) fn ack_exit(
        &self,
        token: u64,
        op: u32,
    ) -> Result<MixerVmCapabilityResultV1, Failure> {
        if self.quarantined() {
            return Err(Failure::poisoned());
        }
        let mut ledger = self.ledger()?;
        let entry = self.ticket(&mut ledger, token, op)?;
        let mut guard = self.unwind_guard();
        let result = match entry.lease.ack_exit() {
            Ok(()) => {
                if entry.acknowledged || self.outstanding() == 0 {
                    return Err(self.invariant("ack count has no pending obligation"));
                }
                entry.acknowledged = true;
                self.outstanding.fetch_sub(1, Ordering::Release);
                Ok(MixerVmCapabilityResultV1::default())
            }
            Err(mb::Error::AlreadyAcknowledged) if entry.acknowledged => {
                Ok(MixerVmCapabilityResultV1 {
                    kind: 2,
                    ..Default::default()
                })
            }
            Err(mb::Error::AlreadyAcknowledged) => {
                return Err(self.invariant("mailbox ack bypassed native ledger"))
            }
            Err(e) => Err(self.mailbox_error(e)),
        };
        guard.disarm();
        result
    }
    pub(crate) fn limit_deadline(
        &self,
        token: u64,
        op: u32,
        timeout: u32,
    ) -> Result<MixerVmCapabilityResultV1, Failure> {
        self.ensure_live()?;
        if timeout == 0 || timeout > mb::MAX_TIMEOUT_MILLISECONDS {
            return Err(Failure::api("invalid request timeout"));
        }
        let mut ledger = self.ledger()?;
        self.ensure_live()?;
        let entry = self.ticket(&mut ledger, token, op)?;
        let mut guard = self.unwind_guard();
        let result = match self.port.limit_deadline(&entry.lease, timeout) {
            Ok(remaining_milliseconds) => Ok(MixerVmCapabilityResultV1 {
                remaining_milliseconds,
                ..Default::default()
            }),
            Err(mb::Error::AlreadyTerminal) => Ok(MixerVmCapabilityResultV1 {
                kind: 1,
                ..Default::default()
            }),
            Err(e) => Err(self.mailbox_error(e)),
        };
        guard.disarm();
        result
    }
    pub(crate) fn expire(&self) -> Result<(), Failure> {
        self.ensure_live()?;
        self.port.expire().map_err(|e| self.mailbox_error(e))
    }
}
fn slot(token: u64) -> Option<usize> {
    if token >> 32 == 0 {
        return None;
    }
    (token as u32)
        .checked_sub(1)
        .map(|n| n as usize)
        .filter(|n| *n < mb::MAX_REQUESTS)
}
fn operation(op: mb::Operation) -> u32 {
    match op {
        mb::Operation::HttpRequest => 1,
        mb::Operation::Get => 2,
        mb::Operation::Put => 3,
        mb::Operation::Delete => 4,
    }
}
pub(crate) struct PreparedTake<'a> {
    pub(crate) message: MixerVmCapabilityMessageV1,
    guard: UnwindGuard<'a>,
}
impl PreparedTake<'_> {
    pub(crate) fn commit(mut self) {
        self.guard.disarm();
    }
}
pub(crate) struct UnwindGuard<'a> {
    session: &'a CapabilitySession,
    armed: bool,
    require_commit: bool,
}
impl UnwindGuard<'_> {
    pub(crate) fn disarm(&mut self) {
        self.armed = false;
    }
}
impl Drop for UnwindGuard<'_> {
    fn drop(&mut self) {
        if self.armed && (self.require_commit || std::thread::panicking()) {
            self.session.quarantine();
        }
    }
}
#[cfg(test)]
#[path = "../../tests/capability_ffi/ledger.rs"]
mod tests;
