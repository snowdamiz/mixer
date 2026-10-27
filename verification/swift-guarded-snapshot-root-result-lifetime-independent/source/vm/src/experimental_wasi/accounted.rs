//! Closed Swift-only ownership for the unchanged standalone WASI adapter.
//!
//! A prepared phase borrows the one runtime authority until its caller closes
//! the phase after construction returns. Dropping a phase retains its charge.
#![allow(dead_code)] // Private prerequisite; no Swift executable owner exists yet.
#![allow(clippy::result_large_err)] // Terminal diagnostics must remain allocation free.

use super::{Errno, Span, WasiBudget, WasiContext, WasiFailure, WasiFunction, WasiGrants};
use super::{WasiOutcome, WasiReservations, WasiUsage};
use crate::experimental_swift_reactor::control::{
    Cursor, Fault, ReservationTicket, RuntimeControl, SwiftReservationCategory, SwiftRunFailure,
    SwiftRunFailureKind,
};
use crate::Value;
use std::mem::{size_of, take};
use std::time::Instant;

/// Neither the context nor its reservation tickets can escape independently.
pub(crate) struct AccountedWasi {
    context: WasiContext,
    buffers: [Option<ReservationTicket>; 4],
    header: Option<ReservationTicket>,
    #[cfg(test)]
    test: DispatchTest,
}

/// No independent ledger or owner identity: the same authority is borrowed for
/// the entire phase. It cannot be completed against a different control.
pub(crate) struct WasiConstructionPhase<'a> {
    control: &'a mut RuntimeControl,
    previous_bound: usize,
    constructed: bool,
    #[cfg(test)]
    test: ConstructionTest,
}

struct Partial {
    storage: [Vec<u8>; 4],
    buffers: [Option<ReservationTicket>; 4],
    header: Option<ReservationTicket>,
}
impl Partial {
    fn empty() -> Self {
        Self {
            storage: std::array::from_fn(|_| Vec::new()),
            buffers: std::array::from_fn(|_| None),
            header: None,
        }
    }

    /// Actual partial storage is destroyed before its reservations are released.
    fn cleanup(mut self, control: &mut RuntimeControl) {
        for index in 0..4 {
            let bytes = take(&mut self.storage[index]);
            if let Some(ticket) = self.buffers[index].take() {
                let _ = control.drop_reserved(bytes, ticket);
            } else {
                drop(bytes);
            }
        }
        if let Some(header) = self.header.take() {
            let _ = control.drop_reserved(self, header);
        }
    }
}

/// Includes every inline Option/ticket through the actual owner type. Additional
/// named cleanup temporaries stay charged until consuming cleanup destroys them:
/// local observation and observed drop/refund/fault/fail/usage argument transfers.
pub(crate) fn accounted_header_bytes() -> Option<usize> {
    size_of::<AccountedWasi>()
        .checked_add(2usize.checked_mul(size_of::<Vec<u8>>())?)?
        .checked_add(4usize.checked_mul(size_of::<Option<ReservationTicket>>())?)?
        .checked_add(6usize.checked_mul(size_of::<Option<WasiUsage>>())?)
}

/// Additional simultaneous constructor/transfer objects beyond the caller's
/// previous bound. This is a named Rust object reservation, not compiler stack
/// measurement. Buffer payloads occur only in their four separate tickets.
pub(crate) fn accounted_construction_bytes() -> Option<usize> {
    [
        (1usize, size_of::<WasiConstructionPhase<'static>>()),
        (3, size_of::<Partial>()),
        (3, size_of::<WasiContext>()),
        (3, size_of::<AccountedWasi>()),
        (2, size_of::<Result<AccountedWasi, SwiftRunFailure>>()),
        (2, size_of::<WasiReservations>()),
        (2, size_of::<WasiUsage>()),
        (4, size_of::<Option<ReservationTicket>>()),
        (4, size_of::<Vec<u8>>()),
        (2, size_of::<WasiBudget>()),
        (2, size_of::<WasiGrants>()),
        (2, size_of::<Cursor>()),
        (2, size_of::<Fault>()),
    ]
    .into_iter()
    .try_fold(0usize, |sum, (count, bytes)| {
        sum.checked_add(count.checked_mul(bytes)?)
    })
}

impl AccountedWasi {
    /// Enlarge the existing shared construction ticket before creating any
    /// phase, partial builder, context, or accounted owner wrapper.
    pub(crate) fn prepare(
        control: &mut RuntimeControl,
        cursor: Cursor,
    ) -> Result<WasiConstructionPhase<'_>, SwiftRunFailure> {
        let previous_bound = control.usage(None).reservations.construction.current;
        let bound = accounted_construction_bytes()
            .and_then(|extra| previous_bound.checked_add(extra))
            .ok_or_else(|| layout_failure(control, cursor))?;
        control.enlarge_construction(bound, cursor)?;
        Ok(WasiConstructionPhase {
            control,
            previous_bound,
            constructed: false,
            #[cfg(test)]
            test: ConstructionTest::default(),
        })
    }

    pub(crate) fn usage(&self) -> WasiUsage {
        self.context.usage()
    }

    /// Attribute observations only after pairing this actual owner with the
    /// control. This borrows without work/admission/cancellation so terminal
    /// cleanup can use it. Same-owner ledger faults retain actual context data;
    /// a foreign owner cannot populate another runtime's WASI diagnostics.
    pub(crate) fn checked_usage(
        &self,
        control: &mut RuntimeControl,
        cursor: Cursor,
    ) -> Result<WasiUsage, SwiftRunFailure> {
        let Some(header) = self.header.as_ref() else {
            return Err(control.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::Invariant,
                    "swift_run_wasi_missing_header",
                ),
                None,
            ));
        };
        let observation = control
            .reservation_owner_matches(header)
            .then(|| self.context.usage());
        control.check_reservation_owner(header, cursor, observation)?;
        Ok(self.context.usage())
    }
    pub(crate) fn stdout(&self) -> &[u8] {
        self.context.stdout()
    }
    pub(crate) fn stderr(&self) -> &[u8] {
        self.context.stderr()
    }

    /// The context is the only WASI meter. The runtime host counter advances
    /// exactly when this wrapper is about to enter the real adapter dispatch.
    pub(crate) fn dispatch(
        &mut self,
        control: &mut RuntimeControl,
        function: WasiFunction,
        arguments: &[Value],
        memory: &mut [u8],
        cursor: Cursor,
    ) -> Result<Errno, SwiftRunFailure> {
        let usage = Some(self.context.usage());
        let Some(ticket) = self.header.as_ref() else {
            return Err(control.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::Invariant,
                    "swift_run_wasi_missing_header",
                ),
                usage,
            ));
        };
        control.check_reservation_owner(ticket, cursor, usage)?;
        control.check_with_wasi(cursor, Some(self.context.usage()))?;
        control.enter_host_with_wasi(cursor, Some(self.context.usage()))?;
        #[cfg(test)]
        self.dispatch_checkpoint(false);
        let outcome = self.context.dispatch(function, arguments, memory);
        #[cfg(test)]
        self.dispatch_checkpoint(true);
        let usage = self.context.usage();
        let result = match outcome {
            WasiOutcome::Failure(error) => {
                let mut fault = Fault::new(SwiftRunFailureKind::Wasi, "swift_run_wasi");
                fault.wasi_failure = Some(error);
                Err(control.fail(cursor, fault, Some(usage)))
            }
            WasiOutcome::Exit(code) => {
                let mut fault = Fault::new(SwiftRunFailureKind::GuestExit, "swift_run_guest_exit");
                fault.guest_exit = Some(code);
                Err(control.fail(cursor, fault, Some(usage)))
            }
            WasiOutcome::Errno(errno) => Ok(errno),
        };
        // Terminal adapter outcomes latch before this check so a later clock or
        // cancellation observation cannot replace the original terminal cause.
        let after = control.check_with_wasi(cursor, Some(usage));
        match result {
            Err(failure) => Err(failure),
            Ok(errno) => after.map(|()| errno),
        }
    }

    /// No checks, admission, work charging, allocation or services during cleanup.
    /// Even an already terminal control can release its actual owned storage.
    pub(crate) fn cleanup(mut self, control: &mut RuntimeControl) -> Result<(), SwiftRunFailure> {
        let wasi = Some(self.context.usage());
        let mut result = Ok(());
        for index in 0..4 {
            let bytes = match index {
                0 => take(&mut self.context.scratch),
                1 => take(&mut self.context.rollback),
                2 => take(&mut self.context.stdout),
                _ => take(&mut self.context.stderr),
            };
            if let Some(ticket) = self.buffers[index].take() {
                let released = control.drop_reserved_with_wasi(bytes, ticket, wasi);
                result = result.and(released);
            } else {
                drop(bytes);
            }
        }
        if let Some(ticket) = self.header.take() {
            let released = control.drop_reserved_with_wasi(self, ticket, wasi);
            result = result.and(released);
        }
        result
    }
}

impl WasiConstructionPhase<'_> {
    /// Exactly one attempt. Failure retains the first terminal control cause and
    /// destroys all partial actual storage; the caller still completes the phase.
    pub(crate) fn construct(
        &mut self,
        grants: WasiGrants,
        budget: WasiBudget,
        started: Instant,
        cursor: Cursor,
    ) -> Result<AccountedWasi, SwiftRunFailure> {
        if self.constructed {
            return Err(self.control.fail(
                cursor,
                Fault::new(
                    SwiftRunFailureKind::Invariant,
                    "swift_run_wasi_construct_once",
                ),
                None,
            ));
        }
        self.constructed = true;
        let deadline = self.control.carry_wasi_deadline(started, budget, cursor)?;
        let header =
            accounted_header_bytes().ok_or_else(|| layout_failure(self.control, cursor))?;
        let mut partial = Partial::empty();
        let result = (|| {
            partial.header = Some(self.control.admit(
                SwiftReservationCategory::Wasi,
                header,
                cursor,
            )?);
            for (index, bytes) in [
                budget.one_transfer_bytes as usize,
                budget.one_transfer_bytes as usize,
                budget.log_bytes as usize,
                budget.log_bytes as usize,
            ]
            .into_iter()
            .enumerate()
            {
                partial.buffers[index] = Some(self.control.admit(
                    SwiftReservationCategory::Wasi,
                    bytes,
                    cursor,
                )?);
                #[cfg(test)]
                self.checkpoint(index, false);
                self.control.check(cursor)?;
                partial.storage[index]
                    .try_reserve_exact(bytes)
                    .map_err(|_| {
                        let mut fault = Fault::new(
                            SwiftRunFailureKind::Allocation,
                            "swift_run_wasi_allocation",
                        );
                        fault.wasi_failure = Some(WasiFailure::Allocation);
                        fault.attempted = bytes as u64;
                        self.control.fail(cursor, fault, None)
                    })?;
                #[cfg(test)]
                self.checkpoint(index, true);
                self.control
                    .exact_capacity(bytes, partial.storage[index].capacity(), cursor)?;
            }
            self.control.check(cursor)
        })();
        if let Err(failure) = result {
            partial.cleanup(self.control);
            return Err(failure);
        }
        let current = partial
            .storage
            .iter()
            .try_fold(size_of::<WasiContext>(), |sum, bytes| {
                sum.checked_add(bytes.capacity())
            });
        let Some(current) = current else {
            let failure = layout_failure(self.control, cursor);
            partial.cleanup(self.control);
            return Err(failure);
        };
        let [scratch, rollback, stdout, stderr] = take(&mut partial.storage);
        let reservations = WasiReservations {
            fixed_state_bytes: size_of::<WasiContext>() as u64,
            staging_bytes: scratch.capacity() as u64,
            rollback_bytes: rollback.capacity() as u64,
            stdout_bytes: stdout.capacity() as u64,
            stderr_bytes: stderr.capacity() as u64,
            current_bytes: current as u64,
            peak_bytes: current as u64,
        };
        Ok(AccountedWasi {
            context: WasiContext {
                grants,
                budget,
                cancellation: self.control.cancellation(),
                deadline,
                terminal: None,
                usage: WasiUsage {
                    reservations,
                    ..WasiUsage::default()
                },
                scratch,
                rollback,
                stdout,
                stderr,
                stdout_len: 0,
                stderr_len: 0,
                stdout_open: grants.stdout,
                stderr_open: grants.stderr,
                iovec_scratch: [Span::default(); 64],
                #[cfg(test)]
                test: super::tests::TestState::default(),
            },
            buffers: take(&mut partial.buffers),
            header: partial.header.take(),
            #[cfg(test)]
            test: DispatchTest::default(),
        })
    }

    /// Call only after construct has returned. Consuming this borrowed phase
    /// drops its actual stored values before restoring the exact previous bound.
    pub(crate) fn complete(self) -> Result<(), SwiftRunFailure> {
        let Self {
            control,
            previous_bound,
            ..
        } = self;
        control.end_construction_phase((), previous_bound)
    }
}

fn layout_failure(control: &mut RuntimeControl, cursor: Cursor) -> SwiftRunFailure {
    control.fail(
        cursor,
        Fault::new(
            SwiftRunFailureKind::Invariant,
            "swift_run_wasi_layout_overflow",
        ),
        None,
    )
}

#[cfg(test)]
#[derive(Default)]
struct ConstructionTest {
    cancel_at: Option<(usize, bool)>,
    expire_at: Option<(usize, bool)>,
    reached: usize,
}
#[cfg(test)]
#[derive(Default)]
struct DispatchTest {
    cancel_before: bool,
    expire_before: bool,
    cancel_after: bool,
}
#[cfg(test)]
impl AccountedWasi {
    fn dispatch_checkpoint(&self, after: bool) {
        if (!after && self.test.cancel_before) || (after && self.test.cancel_after) {
            self.context.cancellation.cancel();
        }
        if !after && self.test.expire_before {
            std::thread::sleep(std::time::Duration::from_millis(5));
        }
    }
}
#[cfg(test)]
impl WasiConstructionPhase<'_> {
    fn checkpoint(&mut self, index: usize, after: bool) {
        self.test.reached += 1;
        if self.test.cancel_at == Some((index, after)) {
            self.control.cancellation().cancel();
        }
        if self.test.expire_at == Some((index, after)) {
            std::thread::sleep(std::time::Duration::from_millis(5));
        }
    }
}

#[cfg(test)]
#[path = "accounted_tests.rs"]
mod tests;

#[cfg(test)] impl AccountedWasi {
 pub(crate) fn host_test_header(&mut self,next:Option<ReservationTicket>)->Option<ReservationTicket>{std::mem::replace(&mut self.header,next)}
 pub(crate) fn host_test_dispatch(&mut self,before:bool,after:bool){self.test.cancel_before=before;self.test.cancel_after=after;}
 pub(crate) fn host_test_cancel_at(&mut self,at:usize){self.context.test.host_set_cancel(at);}
 pub(crate) fn host_test_service(&mut self,kind:u8){self.context.test.host_set_service(kind);}
 pub(crate) fn host_test_services(&self)->usize{self.context.test.host_services()}
}

impl AccountedWasi {pub(crate) fn snapshot_configuration_v2(&self)->(WasiBudget,WasiGrants){self.context.snapshot_configuration_v2()}}


impl AccountedWasi {
    pub(crate) fn snapshot_pair_v1(&self,control:&RuntimeControl)->Result<usize,crate::experimental_swift_reactor::control::SnapshotAdmissionErrorV1>{
        use crate::experimental_swift_reactor::control::SnapshotAdmissionErrorV1 as E;
        use crate::experimental_swift_reactor::control::SwiftReservationCategory as C;
        let header=accounted_header_bytes().ok_or(E::Arithmetic)?;
        control.snapshot_ticket_identity_v1(self.header.as_ref().ok_or(E::Layout)?)?;
        for ticket in &self.buffers {control.snapshot_ticket_identity_v1(ticket.as_ref().ok_or(E::Layout)?)?;}
        control.snapshot_ticket_v1(self.header.as_ref().ok_or(E::Layout)?,C::Wasi,header)?;
        let capacities=[self.context.scratch.capacity(),self.context.rollback.capacity(),self.context.stdout.capacity(),self.context.stderr.capacity()];
        let mut total=header;
        for (ticket,bytes) in self.buffers.iter().zip(capacities) {
            control.snapshot_ticket_v1(ticket.as_ref().ok_or(E::Layout)?,C::Wasi,bytes)?;
            total=total.checked_add(bytes).ok_or(E::Arithmetic)?;
        }
        Ok(total)
    }
}
