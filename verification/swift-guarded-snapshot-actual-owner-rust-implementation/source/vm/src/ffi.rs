//! C ABI safety boundary. Callers own input buffers for the duration of each call.
//! Only pointer-to-slice conversion and unaligned fixed-struct transfers are unsafe.
use crate::*;
use std::{
    panic::{catch_unwind, AssertUnwindSafe},
    slice,
};
pub const MIXER_VM_ABI_VERSION: u32 = 1;
#[repr(C)]
#[derive(Clone, Copy)]
pub struct MixerVmLimits {
    pub struct_size: u32,
    pub abi_version: u32,
    pub fuel: u64,
    pub memory_pages: u32,
    pub operand_stack: u32,
    pub call_depth: u32,
    pub host_calls: u32,
}
#[repr(C)]
#[derive(Clone, Copy)]
pub struct MixerVmValue {
    pub value_type: u32,
    pub reserved: u32,
    pub value: i64,
}
#[repr(C)]
#[derive(Clone, Copy)]
pub struct MixerVmReport {
    pub abi_version: u32,
    pub status: u32,
    pub value_type: u32,
    pub reserved: u32,
    pub value: i64,
    pub fuel_used: u64,
    pub host_calls_used: u64,
    pub function: u32,
    pub offset: u32,
    pub code: [u8; 48],
    pub message: [u8; 256],
}
impl Default for MixerVmReport {
    fn default() -> Self {
        Self {
            abi_version: 1,
            status: 0,
            value_type: 0,
            reserved: 0,
            value: 0,
            fuel_used: 0,
            host_calls_used: 0,
            function: u32::MAX,
            offset: 0,
            code: [0; 48],
            message: [0; 256],
        }
    }
}
fn copy_text<const N: usize>(out: &mut [u8; N], text: &str) {
    let n = text.len().min(N - 1);
    out[..n].copy_from_slice(&text.as_bytes()[..n]);
}
pub(crate) fn report_error(e: Error, status: u32) -> MixerVmReport {
    let mut r = MixerVmReport {
        status,
        function: e.function.unwrap_or(u32::MAX),
        offset: e.offset.min(u32::MAX as usize) as u32,
        ..Default::default()
    };
    copy_text(&mut r.code, e.code);
    copy_text(&mut r.message, &e.message);
    r
}
pub(crate) fn arg(m: &str) -> Error {
    Error::new("invalid_arguments", m, None, 0)
}
pub(crate) unsafe fn limits_from(p: *const MixerVmLimits) -> Result<Limits, Error> {
    let mut l = Limits::default();
    if !p.is_null() {
        // SAFETY: API requires readable sizeof(MixerVmLimits) bytes; unaligned pointers are accepted.
        let c = unsafe { p.read_unaligned() };
        if c.struct_size as usize != std::mem::size_of::<MixerVmLimits>() || c.abi_version != 1 {
            return Err(arg("invalid limits struct size or ABI version"));
        }
        l.fuel = c.fuel;
        l.memory_pages = c.memory_pages;
        l.operand_stack = c.operand_stack as usize;
        l.call_depth = c.call_depth as usize;
        l.host_calls = c.host_calls as u64;
    }
    l.check()?;
    Ok(l)
}
pub(crate) unsafe fn bytes<'a>(p: *const u8, n: usize, max: usize) -> Result<&'a [u8], Error> {
    if n > max || n > isize::MAX as usize {
        return Err(arg("input length exceeds profile"));
    }
    if n == 0 {
        return Ok(&[]);
    }
    if p.is_null() {
        return Err(arg("null pointer with nonzero input length"));
    } // SAFETY: caller guarantees readable n-byte buffer; length and null checked above.
    Ok(unsafe { slice::from_raw_parts(p, n) })
}
pub(crate) unsafe fn boundary<F: FnOnce() -> Result<MixerVmReport, (Error, u32)>>(
    out: *mut MixerVmReport,
    body: F,
) -> u32 {
    if out.is_null() {
        return 3;
    }
    let report = match catch_unwind(AssertUnwindSafe(body)) {
        Ok(Ok(r)) => r,
        Ok(Err((e, s))) => report_error(e, s),
        Err(_) => report_error(
            Error::new(
                "internal_panic",
                "VM panic contained at C ABI boundary",
                None,
                0,
            ),
            4,
        ),
    };
    let status = report.status; // SAFETY: caller guarantees writable sizeof(report) bytes; write_unaligned accepts any alignment.
    unsafe { out.write_unaligned(report) };
    status
}
// Same encoding and bounds for one-shot and persistent entry points.
pub(crate) unsafe fn arguments(
    profile: Profile,
    max: usize,
    args: *const MixerVmValue,
    args_len: usize,
) -> Result<Vec<Value>, Error> {
    if args_len > max || args_len > 0 && args.is_null() {
        return Err(arg("invalid argument buffer"));
    }
    let mut values = vec![];
    for i in 0..args_len {
        // SAFETY: caller guarantees readable args_len consecutive argument structs. The limit bounds offset arithmetic.
        let a = unsafe { args.add(i).read_unaligned() };
        if a.reserved != 0 {
            return Err(arg("argument reserved field must be zero"));
        }
        values.push(match a.value_type {
            1 if i32::try_from(a.value).is_ok() => Value::I32(a.value as i32),
            2 => Value::I64(a.value),
            3 if profile.floats() && u32::try_from(a.value).is_ok() => Value::F32(a.value as u32),
            4 if profile.floats() => Value::F64(a.value as u64),
            _ => return Err(arg("invalid argument type or i32 range")),
        });
    }
    Ok(values)
}

/// Validate without instantiating or executing. See include/mixer_vm.h for pointer contract.
///
/// # Safety
/// All non-null pointers must reference valid readable/writable buffers of the documented size.
unsafe fn validate_profile(
    profile: Profile,
    data: *const u8,
    len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        boundary(out, || {
            let mut l = limits_from(limits).map_err(|e| (e, 3))?;
            l.profile = profile;
            let b = bytes(data, len, l.module_bytes).map_err(|e| (e, 3))?;
            Module::decode(b, &l).map_err(|e| (e, 1))?;
            Ok(MixerVmReport::default())
        })
    }
}
/// Decode, validate, instantiate, and invoke one export. Instances do not persist across C calls.
///
/// # Safety
/// All non-null pointers must reference valid readable/writable buffers of the documented size.
// Mirrors the stable C buffer ABI so pointer ownership remains centralized.
#[allow(clippy::too_many_arguments)]
unsafe fn invoke_profile(
    profile: Profile,
    data: *const u8,
    len: usize,
    export: *const u8,
    export_len: usize,
    args: *const MixerVmValue,
    args_len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        boundary(out, || {
            let mut l = limits_from(limits).map_err(|e| (e, 3))?;
            l.profile = profile;
            let b = bytes(data, len, l.module_bytes).map_err(|e| (e, 3))?;
            let n = bytes(export, export_len, 4096).map_err(|e| (e, 3))?;
            let name = std::str::from_utf8(n).map_err(|_| (arg("export name is not UTF-8"), 3))?;
            let values = arguments(profile, l.locals, args, args_len).map_err(|e| (e, 3))?;
            let module = Module::decode(b, &l).map_err(|e| (e, 1))?;
            let mut instance = Instance::new(module, l.clone()).map_err(|e| (e, 2))?;
            match instance.invoke(name, &values) {
                Ok(value) => {
                    let mut r = MixerVmReport {
                        fuel_used: l.fuel - instance.fuel_remaining,
                        host_calls_used: instance.host_calls_used,
                        ..Default::default()
                    };
                    if let Some(value) = value {
                        match value {
                            Value::I32(v) => {
                                r.value_type = 1;
                                r.value = v as i64;
                            }
                            Value::I64(v) => {
                                r.value_type = 2;
                                r.value = v;
                            }
                            Value::F32(v) => {
                                r.value_type = 3;
                                r.value = v as i64;
                            }
                            Value::F64(v) => {
                                r.value_type = 4;
                                r.value = v as i64;
                            }
                        }
                    }
                    Ok(r)
                }
                Err(e) => {
                    let mut r = report_error(e, 2);
                    r.fuel_used = l.fuel - instance.fuel_remaining;
                    r.host_calls_used = instance.host_calls_used;
                    Ok(r)
                }
            }
        })
    }
}
/// Validate the stable integer-v1 profile.
/// # Safety
/// All pointers obey the buffer contract in mixer_vm.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_validate(
    data: *const u8,
    len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { validate_profile(Profile::IntegerV1, data, len, limits, out) }
}
/// Validate the opt-in numeric-v2 profile.
/// # Safety
/// All pointers obey the buffer contract in mixer_vm.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_validate_numeric_v2(
    data: *const u8,
    len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { validate_profile(Profile::NumericV2, data, len, limits, out) }
}
/// Invoke with the stable integer-v1 profile.
/// # Safety
/// All pointers obey the buffer contract in mixer_vm.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_invoke(
    data: *const u8,
    len: usize,
    export: *const u8,
    export_len: usize,
    args: *const MixerVmValue,
    args_len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        invoke_profile(
            Profile::IntegerV1,
            data,
            len,
            export,
            export_len,
            args,
            args_len,
            limits,
            out,
        )
    }
}
/// Invoke with the opt-in numeric-v2 profile; type3/4 values carry IEEE bits.
/// # Safety
/// All pointers obey the buffer contract in mixer_vm.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_invoke_numeric_v2(
    data: *const u8,
    len: usize,
    export: *const u8,
    export_len: usize,
    args: *const MixerVmValue,
    args_len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        invoke_profile(
            Profile::NumericV2,
            data,
            len,
            export,
            export_len,
            args,
            args_len,
            limits,
            out,
        )
    }
}
/// Validate the explicit table-memory-v3 profile with its fixed table ceiling.
/// # Safety
/// All pointers obey the unchanged buffer/layout contract in mixer_vm.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_validate_table_memory_v3(
    data: *const u8,
    len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe { validate_profile(Profile::TableMemoryV3, data, len, limits, out) }
}
/// Invoke table-memory-v3. The legacy limits struct/layout remains unchanged.
/// # Safety
/// All pointers obey the unchanged buffer/layout contract in mixer_vm.h.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_invoke_table_memory_v3(
    data: *const u8,
    len: usize,
    export: *const u8,
    export_len: usize,
    args: *const MixerVmValue,
    args_len: usize,
    limits: *const MixerVmLimits,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        invoke_profile(
            Profile::TableMemoryV3,
            data,
            len,
            export,
            export_len,
            args,
            args_len,
            limits,
            out,
        )
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn null_inputs_fail_without_unwind() {
        let mut r = MixerVmReport::default();
        let s = unsafe { mixer_vm_validate(std::ptr::null(), 1, std::ptr::null(), &mut r) };
        assert_eq!(s, 3);
        assert_eq!(r.status, 3);
        assert_eq!(
            unsafe {
                mixer_vm_validate(std::ptr::null(), 0, std::ptr::null(), std::ptr::null_mut())
            },
            3
        );
    }
    #[test]
    fn panic_is_contained() {
        let mut r = MixerVmReport::default();
        assert_eq!(
            unsafe { boundary(&mut r, || panic!("test contained panic")) },
            4
        );
        assert_eq!(r.status, 4);
    }
}
