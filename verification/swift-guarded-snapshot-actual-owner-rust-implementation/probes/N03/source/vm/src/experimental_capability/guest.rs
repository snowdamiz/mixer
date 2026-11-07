//! Private transactional guest boundary; no external callbacks under mailbox lock.
use super::*;
use crate::experimental_capability_guest::{fixed_terminal, GuestBudget};

impl Mailbox {
    pub(crate) fn guest_enqueue(
        &self,
        turn: TurnId,
        operation: Operation,
        arguments: &[u8],
        token_output: &mut [u8],
        budget: &mut GuestBudget<'_>,
    ) -> Result<u32, crate::Error> {
        let mut state = self.lock().map_err(|e| budget.trap(e))?;
        if let Err(e) = state.live() {
            return budget.status(e);
        }
        if turn.owner != self.owner || state.active_turn != Some(turn.sequence) {
            return Err(budget.trap(Error::InvalidTurn));
        }
        let reservation = arguments
            .len()
            .checked_add(MAX_PAYLOAD_BYTES)
            .ok_or_else(|| budget.trap(Error::QuotaExceeded))?;
        let Some(reserved) = state
            .reserved_bytes
            .checked_add(reservation)
            .filter(|n| *n <= self.limits.reservation_bytes)
        else {
            return Ok(5);
        };
        let Some(index) = state.slots[..self.limits.maximum_requests]
            .iter()
            .position(|s| !s.retired && s.request.is_none())
        else {
            return Ok(5);
        };
        budget.charge(
            arguments
                .len()
                .checked_add(8)
                .ok_or_else(|| budget.trap(Error::InvalidArguments))?,
        )?;
        let arguments = snapshot(arguments).map_err(|e| budget.trap(e))?;
        let enqueued = Instant::now();
        let deadline = enqueued
            .checked_add(Duration::from_millis(
                self.limits.timeout_milliseconds as u64,
            ))
            .ok_or_else(|| budget.trap(Error::InvalidLimits))?;
        let terminal = if state.enabled {
            None
        } else {
            Some(Terminal::Failure(FailureCode::Unavailable))
        };
        let bits = ((state.slots[index].generation as u64) << 32) | (index as u64 + 1);
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
        token_output.copy_from_slice(&bits.to_le_bytes());
        Ok(0)
    }
    pub(crate) fn guest_poll(
        &self,
        bits: u64,
        memory: &mut [u8],
        output: std::ops::Range<usize>,
        length: std::ops::Range<usize>,
        budget: &mut GuestBudget<'_>,
    ) -> Result<u32, crate::Error> {
        let mut state = self.lock().map_err(|e| budget.trap(e))?;
        if let Err(e) = state.live() {
            return budget.status(e);
        }
        let index = match state.index(
            self.owner,
            RequestId {
                owner: self.owner,
                bits,
            },
            true,
        ) {
            Ok(n) => n,
            Err(e) => return budget.status(e),
        };
        let request = state.slots[index].request.as_mut().unwrap();
        request.expire(Instant::now());
        let payload = match &request.terminal {
            None => None,
            Some(Terminal::Payload(bytes)) => Some(bytes.as_slice()),
            Some(Terminal::Failure(code)) => Some(fixed_terminal(request.operation, *code)),
        };
        let Some(bytes) = payload else {
            budget.charge(4)?;
            memory[length].copy_from_slice(&0u32.to_le_bytes());
            return Ok(1);
        };
        let required = bytes.len();
        if output.len() < required {
            budget.charge(4)?;
            memory[length].copy_from_slice(&(required as u32).to_le_bytes());
            return Ok(2);
        }
        budget.charge(
            required
                .checked_add(4)
                .ok_or_else(|| budget.trap(Error::InvalidArguments))?,
        )?;
        memory[output.start..output.start + required].copy_from_slice(bytes);
        memory[length].copy_from_slice(&(required as u32).to_le_bytes());
        request.consumed = true;
        request.terminal = None;
        if !request.dispatched || request.native_done {
            state.release(index);
        }
        Ok(0)
    }
    pub(crate) fn guest_cancel(&self, bits: u64) -> Result<(), Error> {
        self.cancel(RequestId {
            owner: self.owner,
            bits,
        })
    }
    /// One bounded coalesced readiness predicate, not a callback/event queue.
    pub(crate) fn guest_ready(&self) -> Result<bool, Error> {
        let mut state = self.lock()?;
        state.live()?;
        state.expire(Instant::now());
        Ok(state.active_turn.is_none()
            && state.slots.iter().any(|s| {
                s.request
                    .as_ref()
                    .is_some_and(|r| r.ready && !r.consumed && r.terminal.is_some())
            }))
    }
}

#[cfg(test)]
impl Mailbox {
    pub(crate) fn guest_set_generation_for_test(&self, index: usize, generation: u32) {
        let mut state = self.lock().unwrap();
        assert!(state.slots[index].request.is_none());
        state.slots[index].generation = generation;
    }
    pub(crate) fn guest_set_turn_for_test(&self, sequence: u64) {
        self.lock().unwrap().last_turn = sequence;
    }
    pub(crate) fn guest_poison_for_test(&self) {
        let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _guard = self.state.lock().unwrap();
            panic!("original mailbox poison fixture");
        }));
    }
}
