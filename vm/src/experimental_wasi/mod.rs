//! Experimental standalone bounded Preview1 adapter for the selected Swift reactor.
//!
//! This module does not admit a module or authorize a VM import. Every context has
//! explicit native grants, cumulative lifetime budgets, and private OS services.
//! Deadline/cancellation are cooperative: an individual platform call or bounded
//! copy cannot be preempted. Failed commits restore outputs before returning.
#[cfg(feature = "experimental-swift-reactor")]
pub(crate) mod accounted;
mod descriptor;
mod platform;
use crate::{Cancellation, Value};
pub use descriptor::{ResolveError, WasiFunction};
use std::time::{Duration, Instant};

const CHUNK: usize = 256;

/// Official Preview1 errno numbers, never host errno values.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u16)]
pub enum Errno {
    Success = 0,
    Badf = 8,
    Fault = 21,
    Inval = 28,
    Io = 29,
    Nospc = 51,
    Notsup = 58,
    Overflow = 61,
    Notcapable = 76,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WasiGrants {
    pub secure_random: bool,
    pub realtime: bool,
    pub monotonic: bool,
    pub stdout: bool,
    pub stderr: bool,
}

/// All fields are independently narrowing-only. Zero is a real exhausted limit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WasiBudget {
    pub calls: u64,
    pub transfer_bytes: u64,
    pub work: u64,
    pub one_transfer_bytes: u32,
    pub iovecs: u32,
    pub log_bytes: u32,
    pub deadline_ms: u64,
}
impl Default for WasiBudget {
    fn default() -> Self {
        Self {
            calls: 32_768,
            transfer_bytes: 4 * 1024 * 1024,
            work: 32_000_000,
            one_transfer_bytes: 65_536,
            iovecs: 64,
            log_bytes: 65_536,
            deadline_ms: 30_000,
        }
    }
}
impl WasiBudget {
    pub fn check(self) -> Result<(), WasiFailure> {
        let max = Self::default();
        if self.calls > max.calls
            || self.transfer_bytes > max.transfer_bytes
            || self.work > max.work
            || self.one_transfer_bytes > max.one_transfer_bytes
            || self.iovecs > max.iovecs
            || self.log_bytes > max.log_bytes
            || self.deadline_ms > max.deadline_ms
        {
            Err(WasiFailure::InvalidBudget)
        } else {
            Ok(())
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Resource {
    Calls,
    Transfer,
    TransferSize,
    Work,
    Iovecs,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WasiFailure {
    InvalidBudget,
    Allocation,
    InvalidArguments,
    InvalidMemory,
    Budget(Resource),
    Cancelled,
    Deadline,
    Invariant,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WasiOutcome {
    Errno(Errno),
    Exit(u32),
    Failure(WasiFailure),
}

/// Capacity accounting, not RSS. Fixed state excludes the caller-shared cancellation Arc.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WasiReservations {
    pub fixed_state_bytes: u64,
    pub staging_bytes: u64,
    pub rollback_bytes: u64,
    pub stdout_bytes: u64,
    pub stderr_bytes: u64,
    pub current_bytes: u64,
    pub peak_bytes: u64,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WasiUsage {
    pub calls: u64,
    pub work: u64,
    pub transfer_bytes: u64,
    /// Successful OS random bytes, including bytes discarded after a later failure.
    pub random_bytes: u64,
    pub log_bytes: u64,
    /// Non-success errno outcomes and the first terminal failure/exit.
    pub failures: u64,
    pub reservations: WasiReservations,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Span {
    start: usize,
    end: usize,
}
impl Span {
    fn len(self) -> usize {
        self.end - self.start
    }
    fn overlaps(self, other: Self) -> bool {
        self.start < other.end && other.start < self.end && self.len() != 0 && other.len() != 0
    }
}
enum Fault {
    Errno(Errno),
    Terminal(WasiFailure),
}
impl From<Errno> for Fault {
    fn from(e: Errno) -> Self {
        Self::Errno(e)
    }
}
impl From<WasiFailure> for Fault {
    fn from(e: WasiFailure) -> Self {
        Self::Terminal(e)
    }
}
type CallResult = Result<(), Fault>;

pub struct WasiContext {
    grants: WasiGrants,
    budget: WasiBudget,
    cancellation: Cancellation,
    deadline: Instant,
    terminal: Option<WasiOutcome>,
    usage: WasiUsage,
    scratch: Vec<u8>,
    rollback: Vec<u8>,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    stdout_len: usize,
    stderr_len: usize,
    stdout_open: bool,
    stderr_open: bool,
    iovec_scratch: [Span; 64],
    #[cfg(test)]
    test: tests::TestState,
}

impl WasiContext {
    pub fn new(
        grants: WasiGrants,
        budget: WasiBudget,
        cancellation: Cancellation,
    ) -> Result<Self, WasiFailure> {
        budget.check()?;
        let deadline = Instant::now()
            .checked_add(Duration::from_millis(budget.deadline_ms))
            .ok_or(WasiFailure::InvalidBudget)?;
        fn buffer(len: usize) -> Result<Vec<u8>, WasiFailure> {
            let mut bytes = Vec::new();
            bytes
                .try_reserve_exact(len)
                .map_err(|_| WasiFailure::Allocation)?;
            Ok(bytes)
        }
        let scratch = buffer(budget.one_transfer_bytes as usize)?;
        let rollback = buffer(budget.one_transfer_bytes as usize)?;
        let stdout = buffer(budget.log_bytes as usize)?;
        let stderr = buffer(budget.log_bytes as usize)?;
        let mut reservations = WasiReservations {
            fixed_state_bytes: std::mem::size_of::<Self>() as u64,
            staging_bytes: scratch.capacity() as u64,
            rollback_bytes: rollback.capacity() as u64,
            stdout_bytes: stdout.capacity() as u64,
            stderr_bytes: stderr.capacity() as u64,
            ..WasiReservations::default()
        };
        reservations.current_bytes = reservations
            .fixed_state_bytes
            .checked_add(reservations.staging_bytes)
            .and_then(|n| n.checked_add(reservations.rollback_bytes))
            .and_then(|n| n.checked_add(reservations.stdout_bytes))
            .and_then(|n| n.checked_add(reservations.stderr_bytes))
            .ok_or(WasiFailure::Invariant)?;
        reservations.peak_bytes = reservations.current_bytes;
        Ok(Self {
            grants,
            budget,
            cancellation,
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
            test: tests::TestState::default(),
        })
    }

    pub fn usage(&self) -> WasiUsage {
        self.usage
    }
    pub fn stdout(&self) -> &[u8] {
        &self.stdout[..self.stdout_len]
    }
    pub fn stderr(&self) -> &[u8] {
        &self.stderr[..self.stderr_len]
    }
    pub fn terminal(&self) -> Option<WasiOutcome> {
        self.terminal
    }

    fn check(&self) -> Result<(), WasiFailure> {
        #[cfg(test)]
        self.test.check(&self.cancellation);
        if self.cancellation.is_cancelled() {
            return Err(WasiFailure::Cancelled);
        }
        if Instant::now() >= self.deadline {
            return Err(WasiFailure::Deadline);
        }
        Ok(())
    }
    fn work(&mut self, amount: u64) -> CallResult {
        let next = self
            .usage
            .work
            .checked_add(amount)
            .ok_or(WasiFailure::Invariant)?;
        if next > self.budget.work {
            return Err(WasiFailure::Budget(Resource::Work).into());
        }
        self.usage.work = next;
        Ok(())
    }
    fn transfer(&mut self, amount: usize) -> CallResult {
        if amount > self.budget.one_transfer_bytes as usize {
            return Err(WasiFailure::Budget(Resource::TransferSize).into());
        }
        let next = self
            .usage
            .transfer_bytes
            .checked_add(amount as u64)
            .ok_or(WasiFailure::Invariant)?;
        if next > self.budget.transfer_bytes {
            return Err(WasiFailure::Budget(Resource::Transfer).into());
        }
        // Covers buffer initialization, service/staging, backup, commit, sink
        // initialization/copy, and worst-case rollback byte work.
        // Conservatively charged up front; failures do not refund credits.
        self.work(
            (amount as u64)
                .checked_mul(8)
                .ok_or(WasiFailure::Invariant)?,
        )?;
        self.usage.transfer_bytes = next;
        while self.scratch.len() < amount || self.rollback.len() < amount {
            self.check()?;
            if self.scratch.len() < amount {
                self.scratch
                    .resize((self.scratch.len() + CHUNK).min(amount), 0);
            }
            if self.rollback.len() < amount {
                self.rollback
                    .resize((self.rollback.len() + CHUNK).min(amount), 0);
            }
        }
        Ok(())
    }
    fn span(&mut self, memory: &[u8], pointer: u32, length: u32) -> Result<Span, Fault> {
        self.work(1)?;
        let end = (pointer as u64)
            .checked_add(length as u64)
            .ok_or(Errno::Fault)?;
        if end > 1u64 << 32 || end > memory.len() as u64 {
            return Err(Errno::Fault.into());
        }
        Ok(Span {
            start: pointer as usize,
            end: end as usize,
        })
    }
    fn fd(&self, fd: u32) -> Result<(), Fault> {
        if (fd == 1 && self.stdout_open) || (fd == 2 && self.stderr_open) {
            Ok(())
        } else {
            Err(Errno::Badf.into())
        }
    }

    /// Copies staged bytes to up to two disjoint output spans. Backup occurs before
    /// mutation. Bounded commit checks can fail; rollback requires no remaining budget.
    fn commit(&mut self, memory: &mut [u8], outputs: &[Span]) -> CallResult {
        let mut offset = 0;
        for span in outputs {
            for chunk in (0..span.len()).step_by(CHUNK) {
                self.check()?;
                let end = (chunk + CHUNK).min(span.len());
                self.rollback[offset + chunk..offset + end]
                    .copy_from_slice(&memory[span.start + chunk..span.start + end]);
            }
            offset += span.len();
        }
        let mut failure = None;
        offset = 0;
        'write: for span in outputs {
            for chunk in (0..span.len()).step_by(CHUNK) {
                if let Err(error) = self.check() {
                    failure = Some(error);
                    break 'write;
                }
                let end = (chunk + CHUNK).min(span.len());
                memory[span.start + chunk..span.start + end]
                    .copy_from_slice(&self.scratch[offset + chunk..offset + end]);
            }
            offset += span.len();
        }
        if failure.is_none() {
            failure = self.check().err();
        }
        if let Some(error) = failure {
            offset = 0;
            for span in outputs {
                memory[span.start..span.end]
                    .copy_from_slice(&self.rollback[offset..offset + span.len()]);
                offset += span.len();
            }
            return Err(error.into());
        }
        Ok(())
    }

    pub fn dispatch(
        &mut self,
        function: WasiFunction,
        arguments: &[Value],
        memory: &mut [u8],
    ) -> WasiOutcome {
        if let Some(outcome) = self.terminal {
            return outcome;
        }
        let result = self.invoke(function, arguments, memory);
        let outcome = match result {
            Ok(()) => WasiOutcome::Errno(Errno::Success),
            Err(Fault::Errno(errno)) => WasiOutcome::Errno(errno),
            Err(Fault::Terminal(error)) => WasiOutcome::Failure(error),
        };
        if matches!(outcome, WasiOutcome::Failure(_)) {
            self.terminal = Some(outcome);
        }
        if outcome != WasiOutcome::Errno(Errno::Success) {
            self.usage.failures += 1;
        }
        self.terminal.unwrap_or(outcome)
    }

    fn invoke(&mut self, function: WasiFunction, args: &[Value], memory: &mut [u8]) -> CallResult {
        if args.len() != function.parameters().len()
            || args
                .iter()
                .zip(function.parameters())
                .any(|(v, t)| v.ty() != *t)
        {
            return Err(WasiFailure::InvalidArguments.into());
        }
        if self.usage.calls == self.budget.calls {
            return Err(WasiFailure::Budget(Resource::Calls).into());
        }
        self.usage.calls += 1;
        self.work(args.len() as u64 + 1)?;
        self.check()?;
        if memory.len() as u64 > 1u64 << 32 {
            return Err(WasiFailure::InvalidMemory.into());
        }
        let u = |i: usize| match args[i] {
            Value::I32(n) => n as u32,
            _ => 0,
        };
        use WasiFunction::*;
        match function {
            ArgsGet => {
                let pointers = self.span(memory, u(0), 4)?;
                let text = self.span(memory, u(1), 6)?;
                if pointers.overlaps(text) {
                    return Err(Errno::Inval.into());
                }
                self.transfer(10)?;
                self.scratch[..4].copy_from_slice(&u(1).to_le_bytes());
                self.scratch[4..10].copy_from_slice(b"mixer\0");
                self.commit(memory, &[pointers, text])
            }
            ArgsSizesGet | EnvironSizesGet => {
                let count = self.span(memory, u(0), 4)?;
                let bytes = self.span(memory, u(1), 4)?;
                if count.overlaps(bytes) {
                    return Err(Errno::Inval.into());
                }
                self.transfer(8)?;
                let (n, b) = if function == ArgsSizesGet {
                    (1u32, 6u32)
                } else {
                    (0, 0)
                };
                self.scratch[..4].copy_from_slice(&n.to_le_bytes());
                self.scratch[4..8].copy_from_slice(&b.to_le_bytes());
                self.commit(memory, &[count, bytes])
            }
            EnvironGet => {
                self.span(memory, u(0), 0)?;
                self.span(memory, u(1), 0)?;
                self.check()?;
                Ok(())
            }
            RandomGet => self.random(memory, u(0), u(1)),
            ClockResGet | ClockTimeGet => self.clock(
                memory,
                u(0),
                u(if function == ClockResGet { 1 } else { 2 }),
                function == ClockResGet,
            ),
            FdClose => {
                self.fd(u(0))?;
                self.check()?;
                if u(0) == 1 {
                    self.stdout_open = false;
                } else {
                    self.stderr_open = false;
                }
                Ok(())
            }
            FdFdstatGet => {
                self.fd(u(0))?;
                let output = self.span(memory, u(1), 24)?;
                self.transfer(24)?;
                self.scratch[..24].fill(0);
                self.scratch[8..16].copy_from_slice(&64u64.to_le_bytes());
                self.commit(memory, &[output])
            }
            FdWrite => self.write(memory, u(0), u(1), u(2), u(3)),
            FdFdstatSetFlags | FdFilestatGet | FdFilestatSetSize | FdFilestatSetTimes | FdPread
            | FdRead | FdReaddir | FdSeek | FdSync | FdTell => {
                self.fd(u(0))?;
                Err(Errno::Notcapable.into())
            }
            FdPrestatGet | FdPrestatDirName | PathCreateDirectory | PathFilestatGet
            | PathFilestatSetTimes | PathLink | PathOpen | PathReadlink | PathRemoveDirectory
            | PathRename | PathSymlink | PathUnlinkFile => Err(Errno::Badf.into()),
            PollOneoff => Err(Errno::Notsup.into()),
            ProcExit => {
                self.terminal = Some(WasiOutcome::Exit(u(0)));
                self.usage.failures += 1;
                Ok(())
            }
        }
    }

    fn random(&mut self, memory: &mut [u8], pointer: u32, length: u32) -> CallResult {
        if !self.grants.secure_random {
            return Err(Errno::Notcapable.into());
        }
        let output = self.span(memory, pointer, length)?;
        self.transfer(output.len())?;
        for start in (0..output.len()).step_by(CHUNK) {
            self.check()?;
            let end = (start + CHUNK).min(output.len());
            #[cfg(test)]
            let result = self
                .test
                .random(&mut self.scratch[start..end], &self.cancellation);
            #[cfg(not(test))]
            let result = platform::random(&mut self.scratch[start..end]);
            result?;
            self.usage.random_bytes += (end - start) as u64;
            self.check()?;
        }
        self.check()?;
        self.commit(memory, &[output])
    }
    fn clock(&mut self, memory: &mut [u8], id: u32, pointer: u32, resolution: bool) -> CallResult {
        let clock = match id {
            0 if self.grants.realtime => platform::Clock::Realtime,
            1 if self.grants.monotonic => platform::Clock::Monotonic,
            0..=3 => return Err(Errno::Notcapable.into()),
            _ => return Err(Errno::Inval.into()),
        };
        let output = self.span(memory, pointer, 8)?;
        self.transfer(8)?;
        self.check()?;
        #[cfg(test)]
        let result = self.test.clock(clock, resolution, &self.cancellation);
        #[cfg(not(test))]
        let result = platform::clock(clock, resolution);
        let value = result?;
        self.check()?;
        self.scratch[..8].copy_from_slice(&value.to_le_bytes());
        self.commit(memory, &[output])
    }
    fn write(
        &mut self,
        memory: &mut [u8],
        fd: u32,
        pointer: u32,
        count: u32,
        written: u32,
    ) -> CallResult {
        self.fd(fd)?;
        if count > self.budget.iovecs {
            return Err(WasiFailure::Budget(Resource::Iovecs).into());
        }
        let metadata = self.span(memory, pointer, count.checked_mul(8).ok_or(Errno::Fault)?)?;
        let output = self.span(memory, written, 4)?;
        if output.overlaps(metadata) {
            return Err(Errno::Inval.into());
        }
        self.work(count as u64 * 8)?;
        let mut total = 0usize;
        for index in 0..count as usize {
            self.check()?;
            let position = metadata.start + index * 8;
            let p = u32::from_le_bytes(
                memory[position..position + 4]
                    .try_into()
                    .map_err(|_| WasiFailure::Invariant)?,
            );
            let n = u32::from_le_bytes(
                memory[position + 4..position + 8]
                    .try_into()
                    .map_err(|_| WasiFailure::Invariant)?,
            );
            let span = self.span(memory, p, n)?;
            if output.overlaps(span) {
                return Err(Errno::Inval.into());
            }
            total = total.checked_add(span.len()).ok_or(Errno::Overflow)?;
            self.iovec_scratch[index] = span;
        }
        self.transfer(total)?;
        // The scalar output also consumes transfer/work credits, independently of
        // the payload's per-transfer ceiling, allowing an exact 65,536-byte payload.
        self.transfer(4)?;
        let combined = self
            .stdout_len
            .checked_add(self.stderr_len)
            .and_then(|n| n.checked_add(total))
            .ok_or(WasiFailure::Invariant)?;
        if combined > self.budget.log_bytes as usize {
            return Err(Errno::Nospc.into());
        }
        let mut offset = 0;
        for index in 0..count as usize {
            let span = self.iovec_scratch[index];
            for start in (0..span.len()).step_by(CHUNK) {
                self.check()?;
                let end = (start + CHUNK).min(span.len());
                self.scratch[offset + start..offset + end]
                    .copy_from_slice(&memory[span.start + start..span.start + end]);
            }
            offset += span.len();
        }
        let old_len = if fd == 1 {
            self.stdout_len
        } else {
            self.stderr_len
        };
        for start in (0..total).step_by(CHUNK) {
            self.check()?;
            let end = (start + CHUNK).min(total);
            let sink = if fd == 1 {
                &mut self.stdout
            } else {
                &mut self.stderr
            };
            if sink.len() < old_len + end {
                sink.resize(old_len + end, 0);
            }
            sink[old_len + start..old_len + end].copy_from_slice(&self.scratch[start..end]);
        }
        self.check()?;
        // Logical capture length and the four-byte guest output become visible
        // together after the last cooperative check. No subsequent fallible step.
        memory[output.start..output.end].copy_from_slice(&(total as u32).to_le_bytes());
        if fd == 1 {
            self.stdout_len += total;
        } else {
            self.stderr_len += total;
        }
        self.usage.log_bytes += total as u64;
        Ok(())
    }
}

#[cfg(test)]
mod tests;
