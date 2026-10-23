//! Complete numeric pointer plans. These functions do not read or write storage.
use super::ranges::{preflight as checked_ranges, Access, Invalid, Range};
use super::types::*;
use crate::{MixerVmLimits, MixerVmReport, MixerVmValue};
pub(super) const MODULE_CAP: usize = 4 * 1024 * 1024;
pub(super) const NAME_CAP: usize = 4096;
pub(super) const VALUES_CAP: usize = 4096;
pub(super) const TRANSFER_CAP: usize = 1024 * 1024;
pub(super) const PAYLOAD_CAP: usize = 524288;
fn preflight<const N: usize>(ranges: [Result<Range, Invalid>; N]) -> Result<(), Invalid> {
    if !cfg!(all(
        target_pointer_width = "64",
        any(target_arch = "aarch64", target_arch = "x86_64")
    )) || std::mem::align_of::<u64>() != 8
    {
        return Err(Invalid::Length);
    }
    checked_ranges(ranges)
}
fn read<T>(p: *const T) -> Result<Range, Invalid> {
    Range::elements::<T>(p as usize, 1, 1, Access::Read)
}
fn optional<T>(p: *const T) -> Result<Range, Invalid> {
    if p.is_null() {
        Range::bytes(0, 0, 0, Access::Read)
    } else {
        read(p)
    }
}
fn write<T>(p: *mut T) -> Result<Range, Invalid> {
    Range::elements::<T>(p as usize, 1, 1, Access::Write)
}
pub(super) fn validate(
    module: *const u8,
    n: usize,
    name: *const u8,
    name_len: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        Range::bytes(module as usize, n, MODULE_CAP, Access::Read),
        Range::bytes(name as usize, name_len, NAME_CAP, Access::Read),
        optional(vm),
        optional(cap),
        write(out),
    ])
}
#[allow(clippy::too_many_arguments)]
pub(super) fn create(
    module: *const u8,
    n: usize,
    name: *const u8,
    name_len: usize,
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
    handle: *mut u64,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        Range::bytes(module as usize, n, MODULE_CAP, Access::Read),
        Range::bytes(name as usize, name_len, NAME_CAP, Access::Read),
        optional(vm),
        optional(cap),
        write(handle),
        write(out),
    ])
}
pub(super) fn invoke(
    name: *const u8,
    n: usize,
    args: *const MixerVmValue,
    count: usize,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        Range::bytes(name as usize, n, NAME_CAP, Access::Read),
        Range::elements::<MixerVmValue>(args as usize, count, VALUES_CAP, Access::Read),
        write(out),
    ])
}
pub(super) fn wake(did: *mut u32, out: *mut MixerVmReport) -> Result<(), Invalid> {
    preflight([write(did), write(out)])
}
pub(super) fn read_memory(
    destination: *mut u8,
    n: usize,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        Range::bytes(destination as usize, n, TRANSFER_CAP, Access::Write),
        write(out),
    ])
}
pub(super) fn write_memory(
    source: *const u8,
    n: usize,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        Range::bytes(source as usize, n, TRANSFER_CAP, Access::Read),
        write(out),
    ])
}
pub(super) fn take(
    message: *mut MixerVmCapabilityMessageV1,
    output: *mut u8,
    n: usize,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        write(message),
        Range::bytes(output as usize, n, PAYLOAD_CAP, Access::Write),
        write(out),
    ])
}
pub(super) fn post(
    bytes: *const u8,
    n: usize,
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([
        Range::bytes(bytes as usize, n, PAYLOAD_CAP, Access::Read),
        write(result),
        write(out),
    ])
}
pub(super) fn result(
    result: *mut MixerVmCapabilityResultV1,
    out: *mut MixerVmReport,
) -> Result<(), Invalid> {
    preflight([write(result), write(out)])
}
pub(super) fn simple(out: *mut MixerVmReport) -> Result<(), Invalid> {
    preflight([write(out)])
}
