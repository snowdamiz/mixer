//! Complete preflight precedes every output write. Generic root registry adapter
//! is private; no native function or global pool is exported by this file.
use super::{
    error::{self, Failure},
    preflight as p,
    session::{AccessMode, CapabilitySession, Registry, Reservation},
    types::*,
};
use crate::{
    experimental_capability as mb,
    experimental_capability_guest::{CapabilityGuest, GuestLimits},
    Limits, MixerVmLimits, MixerVmReport, MixerVmValue, Profile, Value,
};

unsafe fn boundary<F: FnOnce() -> Result<MixerVmReport, Failure>>(
    out: *mut MixerVmReport,
    body: F,
) -> u32 {
    // Every call site has completed full numeric preflight, including out.
    unsafe { out.write_unaligned(MixerVmReport::default()) };
    let report = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(body)) {
        Ok(Ok(report)) => report,
        Ok(Err(failure)) => failure.report(),
        Err(payload) => {
            std::mem::forget(payload);
            Failure {
                status: 4,
                code: "internal_panic",
                message: "capability native panic contained; session quarantined if published",
            }
            .report()
        }
    };
    let status = report.status;
    unsafe { out.write_unaligned(report) };
    status
}
unsafe fn input<'a>(ptr: *const u8, len: usize) -> &'a [u8] {
    if len == 0 {
        &[]
    } else {
        unsafe { std::slice::from_raw_parts(ptr, len) }
    }
}
unsafe fn output<'a>(ptr: *mut u8, len: usize) -> &'a mut [u8] {
    if len == 0 {
        &mut []
    } else {
        unsafe { std::slice::from_raw_parts_mut(ptr, len) }
    }
}
unsafe fn name<'a>(ptr: *const u8, len: usize) -> Result<&'a str, Failure> {
    if len == 0 {
        return Err(Failure::api("empty function name"));
    }
    std::str::from_utf8(unsafe { input(ptr, len) })
        .map_err(|_| Failure::api("function name is not UTF-8"))
}
unsafe fn limits(
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
) -> Result<(Limits, mb::Limits, GuestLimits), Failure> {
    let mut vm =
        unsafe { crate::ffi::limits_from(vm) }.map_err(|_| Failure::api("invalid VM limits"))?;
    vm.profile = Profile::TableMemoryV3;
    let c = if cap.is_null() {
        MixerVmCapabilityLimitsV1::default()
    } else {
        unsafe { cap.read_unaligned() }
    };
    if c.struct_size != 32
        || c.abi_version != 1
        || c.reserved != 0
        || c.maximum_requests == 0
        || c.maximum_requests > 8
        || c.timeout_milliseconds == 0
        || c.timeout_milliseconds > 30000
        || c.turn_milliseconds == 0
        || c.turn_milliseconds > 50
        || c.reservation_bytes == 0
        || c.reservation_bytes > 8388608
    {
        return Err(Failure::api("invalid capability limits"));
    }
    Ok((
        vm,
        mb::Limits {
            maximum_requests: c.maximum_requests as usize,
            timeout_milliseconds: c.timeout_milliseconds,
            reservation_bytes: c.reservation_bytes as usize,
        },
        GuestLimits {
            turn_milliseconds: c.turn_milliseconds,
        },
    ))
}
fn vm_report(
    session: &CapabilitySession,
    guest: &CapabilityGuest,
    result: Result<Option<Value>, crate::Error>,
) -> MixerVmReport {
    let mut report = match result {
        Ok(value) => {
            let mut report = MixerVmReport::default();
            if let Some(value) = value {
                (report.value_type, report.value) = match value {
                    Value::I32(n) => (1, n as i64),
                    Value::I64(n) => (2, n),
                    Value::F32(n) => (3, n as i64),
                    Value::F64(n) => (4, n as i64),
                };
            }
            report
        }
        Err(e) if e.code == "capability_state" => return error::vm(e, 3),
        Err(e) => {
            session.mark_terminal();
            let _ = session.close_native();
            error::vm(e, 2)
        }
    };
    report.fuel_used = session.limits.fuel.saturating_sub(guest.fuel_remaining());
    report.host_calls_used = guest.host_calls_used();
    report
}
#[allow(clippy::too_many_arguments)]
pub(super) unsafe fn validate(
    module: *const u8,
    n: usize,
    startup: *const u8,
    startup_len: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    out: *mut MixerVmReport,
) -> u32 {
    if p::validate(module, n, startup, startup_len, vm, cap, out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let (vm, mb, guest) = limits(vm, cap)?;
            let startup = name(startup, startup_len)?;
            Ok(
                match CapabilityGuest::validate_only(input(module, n), &vm, &mb, guest, startup) {
                    Ok(()) => MixerVmReport::default(),
                    Err(e) => error::vm(e, 1),
                },
            )
        })
    }
}
pub(super) unsafe fn guest_ui_validate(
    module: *const u8,
    n: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    out: *mut MixerVmReport,
) -> u32 {
    if p::guest_ui_validate(module, n, vm, cap, out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let (vm, mb, guest) = limits(vm, cap)?;
            Ok(
                match CapabilityGuest::validate_guest_ui_only(input(module, n), &vm, &mb, guest) {
                    Ok(()) => MixerVmReport::default(),
                    Err(e) => error::vm(e, 1),
                },
            )
        })
    }
}
#[allow(clippy::too_many_arguments)]
pub(super) unsafe fn create<R: Registry>(
    registry: &R,
    module: *const u8,
    n: usize,
    startup: *const u8,
    startup_len: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    handle: *mut u64,
    out: *mut MixerVmReport,
) -> u32 {
    if p::create(module, n, startup, startup_len, vm, cap, handle, out).is_err() {
        return 3;
    }
    unsafe {
        handle.write_unaligned(0);
        boundary(out, || {
            let (vm, mb, guest) = limits(vm, cap)?;
            let startup = name(startup, startup_len)?;
            let reservation = registry.reserve()?;
            if let Err(e) =
                CapabilityGuest::validate_only(input(module, n), &vm, &mb, guest, startup)
            {
                return Ok(error::vm(e, 1));
            }
            // Bounded second decode keeps the existing constructor as the single
            // executable owner. Validation above never instantiates memory/owner.
            let guest = match CapabilityGuest::new(input(module, n), vm.clone(), mb, guest, startup)
            {
                Ok(g) => g,
                Err(e) => return Ok(error::vm(e, 2)),
            };
            let id = reservation.publish(CapabilitySession::new(guest, vm))?;
            handle.write_unaligned(id);
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn startup<R: Registry>(
    registry: &R,
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    if p::simple(out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            let mut guest = session.guest()?;
            let result = guest.startup();
            let report = vm_report(&session, &guest, result);
            guard.disarm();
            Ok(report)
        })
    }
}
pub(super) unsafe fn enable<R: Registry>(
    registry: &R,
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    if p::simple(out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            let mut guest = session.guest()?;
            let result = guest.enable_effects().map(|_| None);
            let mut report = vm_report(&session, &guest, result);
            report.fuel_used = 0;
            report.host_calls_used = 0;
            guard.disarm();
            Ok(report)
        })
    }
}
pub(super) unsafe fn invoke<R: Registry>(
    registry: &R,
    handle: u64,
    export: *const u8,
    n: usize,
    args: *const MixerVmValue,
    count: usize,
    out: *mut MixerVmReport,
) -> u32 {
    if p::invoke(export, n, args, count, out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let name = name(export, n)?;
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            let values =
                crate::ffi::arguments(Profile::TableMemoryV3, session.limits.locals, args, count)
                    .map_err(|_| Failure::api("invalid invocation value"))?;
            let mut guest = session.guest()?;
            let result = guest.invoke(name, &values);
            let report = vm_report(&session, &guest, result);
            guard.disarm();
            Ok(report)
        })
    }
}
pub(super) unsafe fn wake<R: Registry>(
    registry: &R,
    handle: u64,
    did: *mut u32,
    out: *mut MixerVmReport,
) -> u32 {
    if p::wake(did, out).is_err() {
        return 3;
    }
    unsafe {
        did.write_unaligned(0);
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            let mut guest = session.guest()?;
            let result = guest.wake_once();
            let report = match result {
                Ok(did_invoke) => {
                    did.write_unaligned(u32::from(did_invoke));
                    if did_invoke {
                        vm_report(&session, &guest, Ok(None))
                    } else {
                        MixerVmReport::default()
                    }
                }
                Err(e) => vm_report(&session, &guest, Err(e)),
            };
            guard.disarm();
            Ok(report)
        })
    }
}
pub(super) unsafe fn read<R: Registry>(
    registry: &R,
    handle: u64,
    offset: u32,
    destination: *mut u8,
    n: usize,
    out: *mut MixerVmReport,
) -> u32 {
    if p::read_memory(destination, n, out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            let guest = session.guest()?;
            let end = (offset as usize)
                .checked_add(n)
                .filter(|end| *end <= guest.memory().len())
                .ok_or_else(|| Failure::api("read exceeds guest memory"))?;
            if n != 0 {
                std::ptr::copy_nonoverlapping(
                    guest.memory()[offset as usize..end].as_ptr(),
                    destination,
                    n,
                );
            }
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn write<R: Registry>(
    registry: &R,
    handle: u64,
    offset: u32,
    source: *const u8,
    n: usize,
    out: *mut MixerVmReport,
) -> u32 {
    if p::write_memory(source, n, out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            let mut guest = session.guest()?;
            let result = guest
                .write_memory(offset, input(source, n))
                .map_err(|_| Failure::api("write exceeds guest memory"));
            guard.disarm();
            result?;
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn cancel<R: Registry>(
    registry: &R,
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    if p::simple(out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            session.close_native()?;
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn close<R: Registry>(registry: &R, handle: u64, out: *mut MixerVmReport) -> u32 {
    if p::simple(out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.close(handle)?;
            let mut guard = session.unwind_guard();
            session.close_native()?;
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn take<R: Registry>(
    registry: &R,
    handle: u64,
    message: *mut MixerVmCapabilityMessageV1,
    bytes: *mut u8,
    n: usize,
    out: *mut MixerVmReport,
) -> u32 {
    if p::take(message, bytes, n, out).is_err() {
        return 3;
    }
    unsafe {
        message.write_unaligned(MixerVmCapabilityMessageV1::default());
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let transaction = session.take(output(bytes, n))?;
            message.write_unaligned(transaction.message);
            out.write_unaligned(MixerVmReport::default());
            transaction.commit();
            Ok(MixerVmReport::default())
        })
    }
}
#[allow(clippy::too_many_arguments)]
pub(super) unsafe fn post<R: Registry>(
    registry: &R,
    handle: u64,
    token: u64,
    op: u32,
    completion: *const u8,
    n: usize,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> u32 {
    if p::post(completion, n, result, out).is_err() {
        return 3;
    }
    unsafe {
        result.write_unaligned(MixerVmCapabilityResultV1::default());
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            result.write_unaligned(session.post(token, op, input(completion, n))?);
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn ack_exit<R: Registry>(
    registry: &R,
    handle: u64,
    token: u64,
    op: u32,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> u32 {
    if p::result(result, out).is_err() {
        return 3;
    }
    unsafe {
        result.write_unaligned(MixerVmCapabilityResultV1::default());
        boundary(out, || {
            let session = registry.get(handle, AccessMode::AckClosing)?;
            let mut guard = session.unwind_guard();
            result.write_unaligned(session.ack_exit(token, op)?);
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
#[allow(clippy::too_many_arguments)]
pub(super) unsafe fn limit_deadline<R: Registry>(
    registry: &R,
    handle: u64,
    token: u64,
    op: u32,
    timeout: u32,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> u32 {
    if p::result(result, out).is_err() {
        return 3;
    }
    unsafe {
        result.write_unaligned(MixerVmCapabilityResultV1::default());
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            result.write_unaligned(session.limit_deadline(token, op, timeout)?);
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
pub(super) unsafe fn expire<R: Registry>(
    registry: &R,
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    if p::simple(out).is_err() {
        return 3;
    }
    unsafe {
        boundary(out, || {
            let session = registry.get(handle, AccessMode::Live)?;
            let mut guard = session.unwind_guard();
            session.expire()?;
            guard.disarm();
            Ok(MixerVmReport::default())
        })
    }
}
