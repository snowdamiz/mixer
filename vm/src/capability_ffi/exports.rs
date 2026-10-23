//! Feature-only C symbols; all unsafe work is centralized in complete-preflight
//! helpers. Default and guest-only builds do not compile this module.
use super::{api, types::*};
use crate::{session::CapabilityRegistry, MixerVmLimits, MixerVmReport, MixerVmValue};
// Safety requirements for all functions are the complete storage/lifetime/range
// contract in the optional mixer_vm_capability.h. No native pointers are retained.
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_validate_v1(
    module: *const u8,
    n: usize,
    startup: *const u8,
    startup_len: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::validate(module, n, startup, startup_len, vm, cap, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_create_v1(
    module: *const u8,
    n: usize,
    startup: *const u8,
    startup_len: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    handle: *mut u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        api::create(
            &CapabilityRegistry,
            module,
            n,
            startup,
            startup_len,
            vm,
            cap,
            handle,
            out,
        )
    }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_startup_v1(
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::startup(&CapabilityRegistry, handle, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_enable_v1(
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::enable(&CapabilityRegistry, handle, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_invoke_v1(
    handle: u64,
    name: *const u8,
    n: usize,
    args: *const MixerVmValue,
    count: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::invoke(&CapabilityRegistry, handle, name, n, args, count, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_wake_v1(
    handle: u64,
    did: *mut u32,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::wake(&CapabilityRegistry, handle, did, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_read_v1(
    handle: u64,
    offset: u32,
    destination: *mut u8,
    n: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::read(&CapabilityRegistry, handle, offset, destination, n, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_write_v1(
    handle: u64,
    offset: u32,
    source: *const u8,
    n: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::write(&CapabilityRegistry, handle, offset, source, n, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_cancel_v1(
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::cancel(&CapabilityRegistry, handle, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_session_close_v1(
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::close(&CapabilityRegistry, handle, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_take_v1(
    handle: u64,
    message: *mut MixerVmCapabilityMessageV1,
    output: *mut u8,
    n: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::take(&CapabilityRegistry, handle, message, output, n, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_post_v1(
    handle: u64,
    token: u64,
    op: u32,
    bytes: *const u8,
    n: usize,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        api::post(
            &CapabilityRegistry,
            handle,
            token,
            op,
            bytes,
            n,
            result,
            out,
        )
    }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_ack_exit_v1(
    handle: u64,
    token: u64,
    op: u32,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::ack_exit(&CapabilityRegistry, handle, token, op, result, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_limit_deadline_v1(
    handle: u64,
    token: u64,
    op: u32,
    timeout: u32,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::limit_deadline(&CapabilityRegistry, handle, token, op, timeout, result, out) }
}
/// # Safety
/// Every pointer obeys the complete storage and lifetime contract in mixer_vm_capability.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_capability_expire_v1(
    handle: u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { api::expire(&CapabilityRegistry, handle, out) }
}
