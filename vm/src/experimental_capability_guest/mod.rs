//! Opt-in actual-Wasm composition experiment. No public profile4, C ABI, registry,
//! native I/O, strict dynamic payload codec, scheduler or release route is added.
//! Shared Arc/standard mutex/core interpreter allocations can abort on OOM.
mod fixed;
use crate::experimental_capability as mb;
use crate::{
    Cancellation, Error, Import, Instance, Limits, Module, Profile, Signature, Type, Value,
};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::{Duration, Instant};
pub const IMPORT_MODULE: &str = "mixer.capability.v1";
pub const WAKE_EXPORT: &str = "mixer_guest_capability_ready_v1";
#[derive(Clone, Copy, Debug)]
pub struct GuestLimits {
    pub turn_milliseconds: u32,
}
impl Default for GuestLimits {
    fn default() -> Self {
        Self {
            turn_milliseconds: 50,
        }
    }
}
struct Shared {
    mailbox: mb::Mailbox,
    cancellation: Cancellation,
    closed: AtomicBool,
}
impl Shared {
    fn live(&self) -> Result<(), mb::Error> {
        if self.closed.load(Ordering::Acquire) || self.cancellation.is_cancelled() {
            self.close_without_unwind();
            Err(mb::Error::SessionClosed)
        } else {
            Ok(())
        }
    }
    fn close(&self) -> Result<mb::CloseReport, mb::Error> {
        self.closed.store(true, Ordering::Release);
        self.cancellation.cancel();
        self.mailbox.close()
    }
    fn close_without_unwind(&self) {
        if let Err(payload) = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _ = self.close();
        })) {
            std::mem::forget(payload);
        }
    }
}
/// Native callers retain this owner and every outstanding ticket through cleanup.
/// Drop is not proof of adapter exit; no counted process registry exists here.
#[derive(Clone)]
pub struct CapabilityPort {
    shared: Arc<Shared>,
}
pub struct DispatchLease {
    shared: Arc<Shared>,
    lease: mb::NativeLease,
}
impl DispatchLease {
    /// Acknowledges only actual native cleanup; also usable after every port drops.
    pub fn ack_exit(&self) -> Result<(), mb::Error> {
        self.shared.mailbox.ack_exit(&self.lease)
    }
    pub fn operation(&self) -> mb::Operation {
        self.lease.operation()
    }
    pub fn token_bits(&self) -> u64 {
        self.lease.request().token_bits()
    }
}
pub enum NativeTake {
    None,
    BufferTooSmall {
        required: usize,
    },
    Call {
        lease: DispatchLease,
        length: usize,
        remaining_milliseconds: u32,
    },
    Cancel {
        lease: DispatchLease,
    },
}
impl CapabilityPort {
    fn check(&self, lease: &DispatchLease) -> Result<(), mb::Error> {
        if Arc::ptr_eq(&self.shared, &lease.shared) {
            Ok(())
        } else {
            Err(mb::Error::StaleRequest)
        }
    }
    pub fn take(&self, output: &mut [u8]) -> Result<NativeTake, mb::Error> {
        self.shared.live()?;
        Ok(match self.shared.mailbox.take(output)? {
            mb::Take::None => NativeTake::None,
            mb::Take::BufferTooSmall { required } => NativeTake::BufferTooSmall { required },
            mb::Take::Call {
                lease,
                length,
                remaining_milliseconds,
            } => NativeTake::Call {
                lease: DispatchLease {
                    shared: Arc::clone(&self.shared),
                    lease,
                },
                length,
                remaining_milliseconds,
            },
            mb::Take::Cancel { lease } => NativeTake::Cancel {
                lease: DispatchLease {
                    shared: Arc::clone(&self.shared),
                    lease,
                },
            },
        })
    }
    /// Trusted opaque bytes. Caller must validate/bind the dynamic wire payload.
    pub fn post_trusted(&self, lease: &DispatchLease, completion: &[u8]) -> Result<(), mb::Error> {
        self.shared.live()?;
        self.check(lease)?;
        self.shared.mailbox.post(&lease.lease, completion)
    }
    pub fn ack_exit(&self, lease: &DispatchLease) -> Result<(), mb::Error> {
        self.check(lease)?;
        self.shared.mailbox.ack_exit(&lease.lease)
    }
    pub fn limit_deadline(
        &self,
        lease: &DispatchLease,
        timeout_milliseconds: u32,
    ) -> Result<u32, mb::Error> {
        self.shared.live()?;
        self.check(lease)?;
        self.shared
            .mailbox
            .limit_deadline(&lease.lease, timeout_milliseconds)
    }
    pub fn expire(&self) -> Result<(), mb::Error> {
        self.shared.live()?;
        self.shared.mailbox.expire()
    }
    pub fn usage(&self) -> Result<mb::Usage, mb::Error> {
        self.shared.mailbox.usage()
    }
    pub fn close(&self) -> Result<mb::CloseReport, mb::Error> {
        self.shared.close()
    }
}
/// Non-Clone private engine owner; never exposes its privileged Module/Instance.
pub struct CapabilityGuest {
    instance: Instance,
    shared: Arc<Shared>,
    startup_index: u32,
    wake_index: u32,
    startup_complete: bool,
    limits: GuestLimits,
}
fn error(code: &'static str, message: &'static str) -> Error {
    Error::new(code, message, None, 0)
}
fn exported(module: &Module, name: &str, void: bool) -> Result<u32, Error> {
    let (kind, index) = module.exports.get(name).copied().ok_or_else(|| {
        error(
            "capability_export",
            "required capability guest export is missing",
        )
    })?;
    let signature = module
        .signature(index)
        .ok_or_else(|| error("capability_export", "required export signature is missing"))?;
    if kind != 0
        || (index as usize) < module.imports.len()
        || !signature.params.is_empty()
        || (void && signature.result.is_some())
    {
        return Err(error(
            "capability_export",
            "required export must be a defined no-argument function with the exact result",
        ));
    }
    Ok(index)
}
impl CapabilityGuest {
    pub fn new(
        wasm: &[u8],
        vm: Limits,
        mailbox: mb::Limits,
        guest: GuestLimits,
        installed_startup_export: &str,
    ) -> Result<Self, Error> {
        let (module, startup_index, wake_index) =
            Self::validated(wasm, &vm, &mailbox, guest, installed_startup_export)?;
        let instance = Instance::new_capability(module, vm)?;
        let shared = Arc::new(Shared {
            mailbox: mb::Mailbox::new(mailbox).map_err(|e| {
                if e == mb::Error::InvalidLimits {
                    error("invalid_limits", "invalid capability mailbox limits")
                } else {
                    mailbox_trap(e, None, 0)
                }
            })?,
            cancellation: instance.cancellation(),
            closed: AtomicBool::new(false),
        });
        Ok(Self {
            instance,
            shared,
            startup_index,
            wake_index,
            startup_complete: false,
            limits: guest,
        })
    }
    fn validated(
        wasm: &[u8],
        vm: &Limits,
        mailbox: &mb::Limits,
        guest: GuestLimits,
        installed_startup_export: &str,
    ) -> Result<(Module, u32, u32), Error> {
        if vm.profile != Profile::TableMemoryV3
            || guest.turn_milliseconds == 0
            || guest.turn_milliseconds > 50
        {
            return Err(error(
                "invalid_limits",
                "capability guest requires v3 grammar and a1..50ms turn ceiling",
            ));
        }
        if mailbox.maximum_requests == 0
            || mailbox.maximum_requests > mb::MAX_REQUESTS
            || mailbox.reservation_bytes == 0
            || mailbox.reservation_bytes > mb::MAX_RESERVATION_BYTES
            || mailbox.timeout_milliseconds == 0
            || mailbox.timeout_milliseconds > mb::MAX_TIMEOUT_MILLISECONDS
        {
            return Err(error("invalid_limits", "invalid capability mailbox limits"));
        }
        if installed_startup_export.is_empty() || installed_startup_export.len() > 4096 {
            return Err(error(
                "capability_export",
                "invalid installed startup export",
            ));
        }
        let module = Module::decode_capability(wasm, vm)?;
        let startup_index = exported(&module, installed_startup_export, false)?;
        let wake_index = exported(&module, WAKE_EXPORT, true)?;
        Ok((module, startup_index, wake_index))
    }
    /// Exact constructor validation, with no instance linear memory/owner/startup.
    #[cfg(feature = "experimental-capability-native")]
    pub(crate) fn validate_only(
        wasm: &[u8],
        vm: &Limits,
        mailbox: &mb::Limits,
        guest: GuestLimits,
        startup: &str,
    ) -> Result<(), Error> {
        Self::validated(wasm, vm, mailbox, guest, startup).map(|_| ())
    }
    #[cfg(feature = "experimental-capability-native")]
    pub(crate) fn write_memory(&mut self, offset: u32, source: &[u8]) -> Result<(), Error> {
        self.live()?;
        self.instance.write_memory(offset, source)
    }
    pub fn native_port(&self) -> CapabilityPort {
        CapabilityPort {
            shared: Arc::clone(&self.shared),
        }
    }
    pub fn cancellation(&self) -> Cancellation {
        self.instance.cancellation()
    }
    pub fn memory(&self) -> &[u8] {
        self.instance.memory()
    }
    pub fn fuel_remaining(&self) -> u64 {
        self.instance.fuel_remaining
    }
    pub fn host_calls_used(&self) -> u64 {
        self.instance.host_calls_used
    }
    fn live(&self) -> Result<(), Error> {
        if self.shared.closed.load(Ordering::Acquire) || self.shared.cancellation.is_cancelled() {
            self.shared.close_without_unwind();
            return Err(error(
                "capability_closed",
                "capability guest is permanently closed",
            ));
        }
        Ok(())
    }
    pub fn startup(&mut self) -> Result<Option<Value>, Error> {
        self.live()?;
        if self.startup_complete {
            return Err(error("capability_state", "startup already completed"));
        }
        let result = self.run(Some(self.startup_index), None, &[])?;
        self.startup_complete = true;
        Ok(result)
    }
    pub fn enable_effects(&mut self) -> Result<(), Error> {
        self.live()?;
        if !self.startup_complete {
            return Err(error(
                "capability_state",
                "startup must finish before enabling effects",
            ));
        }
        if let Err(e) = self.shared.mailbox.enable() {
            self.shared.close_without_unwind();
            return Err(mailbox_trap(e, None, 0));
        }
        Ok(())
    }
    pub fn invoke(&mut self, export: &str, args: &[Value]) -> Result<Option<Value>, Error> {
        self.live()?;
        if !self.startup_complete {
            return Err(error(
                "capability_state",
                "startup must finish before ordinary turns",
            ));
        }
        self.run(None, Some(export), args)
    }
    pub fn wake_once(&mut self) -> Result<bool, Error> {
        self.live()?;
        if !self.startup_complete {
            return Err(error("capability_state", "startup must finish before wake"));
        }
        match self.shared.mailbox.guest_ready() {
            Ok(false) => Ok(false),
            Ok(true) => {
                self.run(Some(self.wake_index), None, &[])?;
                Ok(true)
            }
            Err(e) => {
                self.shared.close_without_unwind();
                Err(mailbox_trap(e, None, 0))
            }
        }
    }
    pub fn close(&mut self) -> Result<mb::CloseReport, Error> {
        self.shared.close().map_err(|e| mailbox_trap(e, None, 0))
    }
    fn run(
        &mut self,
        index: Option<u32>,
        export: Option<&str>,
        args: &[Value],
    ) -> Result<Option<Value>, Error> {
        let shared = Arc::clone(&self.shared);
        let turn = match shared.mailbox.begin_turn() {
            Ok(turn) => turn,
            Err(e) => {
                shared.close_without_unwind();
                return Err(mailbox_trap(e, None, 0));
            }
        };
        let mut guard = TurnGuard {
            shared: &shared,
            finished: false,
        };
        let deadline = Instant::now()
            .checked_add(Duration::from_millis(self.limits.turn_milliseconds as u64))
            .ok_or_else(|| error("invalid_limits", "turn deadline overflow"))?;
        let imports = GuestImports {
            shared: &shared,
            turn,
            deadline,
        };
        let result = match index {
            Some(index) => self.instance.invoke_capability(index, args, &imports),
            None => self.instance.invoke_capability_export(
                export.expect("private entry selection"),
                args,
                &imports,
            ),
        };
        let result = result.and_then(|value| {
            // This check occurs after return, outside any active instruction.
            imports.check_boundary(None, 0)?;
            shared
                .mailbox
                .finish_turn(turn, mb::TurnOutcome::Success)
                .map_err(|e| mailbox_trap(e, None, 0))?;
            Ok(value)
        });
        if result.is_ok() {
            guard.finished = true;
        }
        result
    }
}
impl Drop for CapabilityGuest {
    fn drop(&mut self) {
        self.shared.close_without_unwind();
    }
}
struct TurnGuard<'a> {
    shared: &'a Shared,
    finished: bool,
}
impl Drop for TurnGuard<'_> {
    fn drop(&mut self) {
        if !self.finished {
            self.shared.close_without_unwind();
        }
    }
}

pub(crate) fn allowed_import(import: &Import, sig: &Signature) -> bool {
    if import.module != IMPORT_MODULE || sig.result != Some(Type::I32) {
        return false;
    }
    match import.name.as_str() {
        "http_request" | "storage_get" | "storage_put" | "storage_delete" => {
            sig.params == [Type::I32, Type::I32, Type::I32]
        }
        "cancel" => sig.params == [Type::I64],
        "poll" => sig.params == [Type::I64, Type::I32, Type::I32, Type::I32],
        _ => false,
    }
}
pub(crate) fn fixed_terminal(operation: mb::Operation, failure: mb::FailureCode) -> &'static [u8] {
    fixed::terminal(operation, failure)
}
fn mailbox_trap(e: mb::Error, function: Option<u32>, offset: usize) -> Error {
    let (code, message) = match e {
        mb::Error::AllocationFailure => (
            "capability_allocation",
            "capability payload allocation failed",
        ),
        mb::Error::IdentifierExhausted => (
            "capability_identifier_exhausted",
            "capability identity exhausted",
        ),
        mb::Error::Poisoned => ("capability_poisoned", "capability mailbox is poisoned"),
        _ => (
            "capability_protocol",
            "capability mailbox transition failed",
        ),
    };
    Error::new(code, message, function, offset)
}
pub(crate) struct GuestImports<'a> {
    shared: &'a Shared,
    turn: mb::TurnId,
    deadline: Instant,
}
impl GuestImports<'_> {
    pub(crate) fn check(&self, function: u32, offset: usize) -> Result<(), Error> {
        self.check_boundary(Some(function), offset)
    }
    fn check_boundary(&self, function: Option<u32>, offset: usize) -> Result<(), Error> {
        if self.shared.closed.load(Ordering::Acquire) || self.shared.cancellation.is_cancelled() {
            return Err(Error::new(
                "cancelled",
                "capability guest execution cancelled",
                function,
                offset,
            ));
        }
        if Instant::now() >= self.deadline {
            return Err(Error::new(
                "capability_turn_timeout",
                "cooperative capability guest turn deadline exceeded",
                function,
                offset,
            ));
        }
        Ok(())
    }
    pub(crate) fn import(
        &self,
        name: &str,
        args: &[Value],
        memory: &mut [u8],
        fuel: &mut u64,
        caller: u32,
        offset: usize,
    ) -> Result<Option<Value>, Error> {
        let mut budget = GuestBudget {
            fuel,
            imports: self,
            caller,
            offset,
        };
        let status = match name {
            "http_request" | "storage_get" | "storage_put" | "storage_delete" => {
                let start = i32arg(args, 0);
                let len = i32arg(args, 1) as usize;
                let token = i32arg(args, 2);
                let Some(input) = range(start, len, memory.len())
                    .filter(|_| (1..=mb::MAX_PAYLOAD_BYTES).contains(&len))
                else {
                    return Ok(Some(Value::I32(3)));
                };
                let Some(output) = range(token, 8, memory.len()) else {
                    return Ok(Some(Value::I32(3)));
                };
                if overlap(&input, &output) {
                    return Ok(Some(Value::I32(3)));
                }
                let operation = match name {
                    "http_request" => mb::Operation::HttpRequest,
                    "storage_get" => mb::Operation::Get,
                    "storage_put" => mb::Operation::Put,
                    _ => mb::Operation::Delete,
                };
                let (arguments, token_output) = if input.end <= output.start {
                    let (a, b) = memory.split_at_mut(output.start);
                    (&a[input], &mut b[..8])
                } else {
                    let (a, b) = memory.split_at_mut(input.start);
                    (&b[..len], &mut a[output])
                };
                self.shared.mailbox.guest_enqueue(
                    self.turn,
                    operation,
                    arguments,
                    token_output,
                    &mut budget,
                )?
            }
            "cancel" => match self.shared.mailbox.guest_cancel(i64arg(args, 0)) {
                Ok(()) => 0,
                Err(e) => budget.status(e)?,
            },
            "poll" => {
                let capacity = i32arg(args, 2) as usize;
                let Some(output) = range(i32arg(args, 1), capacity, memory.len())
                    .filter(|_| capacity <= mb::MAX_PAYLOAD_BYTES)
                else {
                    return Ok(Some(Value::I32(3)));
                };
                let Some(length) = range(i32arg(args, 3), 4, memory.len()) else {
                    return Ok(Some(Value::I32(3)));
                };
                if overlap(&output, &length) {
                    return Ok(Some(Value::I32(3)));
                }
                self.shared.mailbox.guest_poll(
                    i64arg(args, 0),
                    memory,
                    output,
                    length,
                    &mut budget,
                )?
            }
            _ => {
                return Err(Error::new(
                    "unsupported",
                    "unknown capability import",
                    Some(caller),
                    offset,
                ))
            }
        };
        Ok(Some(Value::I32(status as i32)))
    }
}
fn i32arg(args: &[Value], index: usize) -> u32 {
    match args[index] {
        Value::I32(n) => n as u32,
        _ => unreachable!("validated capability i32"),
    }
}
fn i64arg(args: &[Value], index: usize) -> u64 {
    match args[index] {
        Value::I64(n) => n as u64,
        _ => unreachable!("validated capability i64"),
    }
}
fn range(start: u32, len: usize, total: usize) -> Option<std::ops::Range<usize>> {
    let start = start as usize;
    let end = start.checked_add(len).filter(|n| *n <= total)?;
    Some(start..end)
}
fn overlap(a: &std::ops::Range<usize>, b: &std::ops::Range<usize>) -> bool {
    !a.is_empty() && !b.is_empty() && a.start < b.end && b.start < a.end
}
pub(crate) struct GuestBudget<'a> {
    fuel: &'a mut u64,
    imports: &'a GuestImports<'a>,
    caller: u32,
    offset: usize,
}
impl GuestBudget<'_> {
    pub(crate) fn charge(&mut self, bytes: usize) -> Result<(), Error> {
        self.imports.check(self.caller, self.offset)?;
        let extra = bytes.div_ceil(64) as u64;
        if *self.fuel < extra {
            *self.fuel = 0;
            return Err(Error::new(
                "fuel_exhausted",
                "capability byte fuel exhausted before mutation",
                Some(self.caller),
                self.offset,
            ));
        }
        *self.fuel -= extra;
        Ok(())
    }
    pub(crate) fn trap(&self, e: mb::Error) -> Error {
        mailbox_trap(e, Some(self.caller), self.offset)
    }
    pub(crate) fn status(&self, e: mb::Error) -> Result<u32, Error> {
        Ok(match e {
            mb::Error::InvalidArguments => 3,
            mb::Error::StaleRequest => 4,
            mb::Error::QuotaExceeded => 5,
            mb::Error::SessionClosed => 6,
            mb::Error::AlreadyTerminal => 7,
            _ => return Err(self.trap(e)),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn section(m: &mut Vec<u8>, id: u8, b: Vec<u8>) {
        assert!(b.len() < 128);
        m.extend([id, b.len() as u8]);
        m.extend(b);
    }
    fn fixture() -> Vec<u8> {
        let mut m = b"\0asm\x01\0\0\0".to_vec();
        section(
            &mut m,
            1,
            vec![2, 0x60, 3, 0x7f, 0x7f, 0x7f, 1, 0x7f, 0x60, 0, 0],
        );
        let mut imports = vec![1, IMPORT_MODULE.len() as u8];
        imports.extend(IMPORT_MODULE.as_bytes());
        imports.push(11);
        imports.extend(b"storage_get");
        imports.extend([0, 0]);
        section(&mut m, 2, imports);
        section(&mut m, 3, vec![2, 1, 1]);
        section(&mut m, 5, vec![1, 1, 1, 1]);
        let mut exports = vec![3, 5];
        exports.extend(b"start");
        exports.extend([0, 1, WAKE_EXPORT.len() as u8]);
        exports.extend(WAKE_EXPORT.as_bytes());
        exports.extend([0, 2, 3]);
        exports.extend(b"get");
        exports.extend([0, 0]);
        section(&mut m, 7, exports);
        section(&mut m, 10, vec![2, 2, 0, 0x0b, 2, 0, 0x0b]);
        m
    }
    fn guest() -> CapabilityGuest {
        let mut g = CapabilityGuest::new(
            &fixture(),
            Limits {
                profile: Profile::TableMemoryV3,
                ..Limits::default()
            },
            mb::Limits {
                maximum_requests: 1,
                ..mb::Limits::default()
            },
            GuestLimits::default(),
            "start",
        )
        .unwrap();
        g.startup().unwrap();
        g.enable_effects().unwrap();
        g
    }
    fn enqueue(g: &mut CapabilityGuest) -> u64 {
        assert_eq!(
            g.invoke("get", &[Value::I32(0), Value::I32(1), Value::I32(8)])
                .unwrap(),
            Some(Value::I32(0))
        );
        u64::from_le_bytes(g.memory()[8..16].try_into().unwrap())
    }
    fn lease(p: &CapabilityPort) -> DispatchLease {
        match p.take(&mut [0; 1]).unwrap() {
            NativeTake::Call { lease, .. } => lease,
            _ => panic!("expected lease"),
        }
    }
    #[test]
    fn privileged_decoded_module_cannot_bypass_public_instance_constructor() {
        let bytes = fixture();
        let limits = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        let m = Module::decode_capability(&bytes, &limits).unwrap();
        assert!(matches!(Instance::new(m,limits),Err(e) if e.code=="unsupported"));
    }
    #[test]
    fn raw_generation_max_retires_without_wrapping_and_turn_exhaustion_traps() {
        let mut g = guest();
        g.shared.mailbox.guest_set_generation_for_test(0, u32::MAX);
        let bits = enqueue(&mut g);
        assert_eq!(bits, (u32::MAX as u64) << 32 | 1);
        g.shared.mailbox.guest_cancel(bits).unwrap();
        let turn = g.shared.mailbox.begin_turn().unwrap();
        let mut fuel = 100;
        let imports = GuestImports {
            shared: &g.shared,
            turn,
            deadline: Instant::now() + Duration::from_secs(1),
        };
        let mut budget = GuestBudget {
            fuel: &mut fuel,
            imports: &imports,
            caller: 0,
            offset: 0,
        };
        let mut mem = [0; 512];
        g.shared
            .mailbox
            .guest_poll(bits, &mut mem, 0..400, 400..404, &mut budget)
            .unwrap();
        g.shared
            .mailbox
            .finish_turn(turn, mb::TurnOutcome::Success)
            .unwrap();
        assert_eq!(g.native_port().usage().unwrap().retired_slots, 1);
        assert_eq!(
            g.invoke("get", &[Value::I32(0), Value::I32(1), Value::I32(8)])
                .unwrap(),
            Some(Value::I32(5))
        );
        let mut g = guest();
        g.shared.mailbox.guest_set_turn_for_test(u64::MAX);
        assert_eq!(
            g.invoke("get", &[Value::I32(0), Value::I32(1), Value::I32(8)])
                .unwrap_err()
                .code,
            "capability_identifier_exhausted"
        );
        assert!(g.shared.closed.load(Ordering::Acquire));
    }
    #[test]
    fn unfinished_turn_guard_preserves_original_unwind_and_ackable_lease() {
        let mut g = guest();
        enqueue(&mut g);
        let p = g.native_port();
        let ticket = lease(&p);
        let shared = Arc::clone(&g.shared);
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _guard = TurnGuard {
                shared: &shared,
                finished: false,
            };
            panic!("original guest unwind payload");
        }));
        assert_eq!(
            result.unwrap_err().downcast_ref::<&str>(),
            Some(&"original guest unwind payload")
        );
        assert!(matches!(p.take(&mut [0; 1]), Err(mb::Error::SessionClosed)));
        p.ack_exit(&ticket).unwrap();
        assert_eq!(p.usage().unwrap().native_leases, 0);
    }
    #[test]
    fn poison_is_terminal_and_ack_failure_is_not_called_reclamation() {
        let mut g = guest();
        enqueue(&mut g);
        let p = g.native_port();
        let ticket = lease(&p);
        g.shared.mailbox.guest_poison_for_test();
        assert_eq!(
            g.invoke("get", &[Value::I32(0), Value::I32(1), Value::I32(8)])
                .unwrap_err()
                .code,
            "capability_poisoned"
        );
        assert!(g.shared.closed.load(Ordering::Acquire));
        assert_eq!(ticket.ack_exit(), Err(mb::Error::Poisoned));
    }
    #[test]
    fn ticket_keeps_shared_owner_after_guest_and_ports_drop() {
        let mut g = guest();
        enqueue(&mut g);
        let p = g.native_port();
        let ticket = lease(&p);
        let weak = Arc::downgrade(&g.shared);
        drop(g);
        drop(p);
        assert!(weak.upgrade().is_some());
        ticket.ack_exit().unwrap();
        drop(ticket);
        assert!(weak.upgrade().is_none());
    }
    #[test]
    fn fixed_layout_observation_and_static_payload_bounds() {
        println!("capability guest layout: guest={} shared={} port={} ticket={} mailbox={} vm_limits={} guest_limits={}",std::mem::size_of::<CapabilityGuest>(),std::mem::size_of::<Shared>(),std::mem::size_of::<CapabilityPort>(),std::mem::size_of::<DispatchLease>(),std::mem::size_of::<mb::Mailbox>(),std::mem::size_of::<Limits>(),std::mem::size_of::<GuestLimits>());
        for op in [
            mb::Operation::HttpRequest,
            mb::Operation::Get,
            mb::Operation::Put,
            mb::Operation::Delete,
        ] {
            for failure in [
                mb::FailureCode::Unavailable,
                mb::FailureCode::Cancelled,
                mb::FailureCode::DeadlineExceeded,
            ] {
                let bytes = fixed_terminal(op, failure);
                assert!(!bytes.is_empty() && bytes.len() < 512);
                assert!(bytes.is_ascii());
            }
        }
    }
}
