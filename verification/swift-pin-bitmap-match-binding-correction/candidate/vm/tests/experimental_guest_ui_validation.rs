#![cfg(feature = "experimental-capability-native")]
use mixer_vm::*;
use std::{
    mem::{offset_of, size_of},
    ptr,
    sync::Mutex,
};
#[path = "guest_ui/fixture.rs"]
mod fixture;
use fixture::{Program, NAMES};
static SERIAL: Mutex<()> = Mutex::new(());
fn validate(
    bytes: &[u8],
    vm: *const MixerVmLimits,
    cap: *const MixerVmCapabilityLimitsV1,
) -> MixerVmReport {
    let mut report = MixerVmReport::default();
    let status = unsafe {
        mixer_vm_capability_guest_ui_validate_v1(bytes.as_ptr(), bytes.len(), vm, cap, &mut report)
    };
    assert_eq!(status, report.status);
    assert_eq!(
        (
            report.abi_version,
            report.reserved,
            report.value_type,
            report.value
        ),
        (1, 0, 0, 0)
    );
    assert_eq!((report.fuel_used, report.host_calls_used), (0, 0));
    report
}
fn code(report: &MixerVmReport) -> &str {
    std::str::from_utf8(report.code.split(|&b| b == 0).next().unwrap()).unwrap()
}
fn export_error(p: &Program) {
    let r = validate(&p.bytes(), ptr::null(), ptr::null());
    assert_eq!(
        (r.status, code(&r), r.function, r.offset),
        (1, "capability_export", u32::MAX, 0)
    );
    assert!(r.code.contains(&0) && r.message.contains(&0));
}
fn vm_limits() -> MixerVmLimits {
    MixerVmLimits {
        struct_size: 32,
        abi_version: 1,
        fuel: 1000000,
        memory_pages: 64,
        operand_stack: 4096,
        call_depth: 64,
        host_calls: 1024,
    }
}
#[test]
fn exact_defined_exports_and_legacy_validation_preserved() {
    let _serial = SERIAL.lock().unwrap();
    assert_eq!(
        validate(&Program::default().bytes(), ptr::null(), ptr::null()).status,
        0
    );
    for required in 0..3 {
        let mut p = Program::default();
        p.exports.remove(required);
        export_error(&p);
        let mut p = Program::default();
        p.exports[required].1 = 2;
        p.exports[required].2 = 0; // existing memory, not function
        export_error(&p);
        let mut p = Program::default();
        p.exports[required].2 = if required == 1 { 1 } else { 0 }; // approved imported function
        export_error(&p);
    }
    // Each function has independently valid code for every wrong signature.
    for (required, ty, body) in [
        (0, 2, vec![0, 0x0b]),
        (0, 3, vec![0, 0x42, 0, 0x0b]),
        (0, 1, vec![0, 0x20, 0, 0x0b]),
        (1, 0, vec![0, 0x41, 0, 0x0b]),
        (1, 4, vec![0, 0x41, 0, 0x0b]),
        (1, 5, vec![0, 0x0b]),
        (1, 3, vec![0, 0x42, 0, 0x0b]),
        (2, 0, vec![0, 0x41, 0, 0x0b]),
        (2, 5, vec![0, 0x0b]),
    ] {
        let mut p = Program::default();
        p.functions[required] = (ty, body);
        export_error(&p);
        if required == 0 && (ty == 2 || ty == 3) {
            let bytes = p.bytes();
            let mut r = MixerVmReport::default();
            // Existing selected no-argument startup semantics accept void/i64.
            assert_eq!(
                unsafe {
                    mixer_vm_capability_validate_v1(
                        bytes.as_ptr(),
                        bytes.len(),
                        NAMES[0].as_ptr(),
                        NAMES[0].len(),
                        ptr::null(),
                        ptr::null(),
                        &mut r,
                    )
                },
                0
            );
        }
    }
}
#[test]
fn complete_validation_precedes_export_checks_without_running_startup() {
    let _serial = SERIAL.lock().unwrap();
    let mut p = Program::default();
    p.functions[0].1 = vec![0, 0, 0x0b]; // unreachable would trap if executed
    assert_eq!(validate(&p.bytes(), ptr::null(), ptr::null()).status, 0);
    p.functions.push((0, vec![0, 0x42, 0, 0x0b])); // uncalled i64 result in i32 function
    p.exports.remove(1); // export error must not hide bad body
    let r = validate(&p.bytes(), ptr::null(), ptr::null());
    assert_eq!((r.status, code(&r), r.function), (1, "validation", 5));
    assert!(r.offset > 8);
    let mut p = Program {
        unknown_import: true,
        ..Program::default()
    };
    p.exports.remove(1);
    let r = validate(&p.bytes(), ptr::null(), ptr::null());
    assert_eq!((r.status, code(&r)), (1, "unsupported"));
    let p = Program {
        start_section: true,
        ..Program::default()
    };
    let r = validate(&p.bytes(), ptr::null(), ptr::null());
    assert_eq!((r.status, code(&r)), (1, "unsupported"));
    let mut p = Program::default();
    p.functions.push((2, vec![0, 0xfd, 0x0b]));
    let r = validate(&p.bytes(), ptr::null(), ptr::null());
    assert_eq!((r.status, code(&r)), (1, "unsupported"));
    for bytes in [&b""[..], &b"\0asm\x01\0\0"[..], &b"notwasm!"[..]] {
        let r = validate(bytes, ptr::null(), ptr::null());
        assert_eq!(r.status, 1);
        assert_ne!(code(&r), "capability_export");
    }
}
#[test]
fn same_limits_and_exact_zero_defined_memory_fail_closed() {
    let _serial = SERIAL.lock().unwrap();
    let mut p = Program {
        memory: Some(vec![1, 1, 0, 0]),
        ..Program::default()
    };
    let mut vm = vm_limits();
    vm.memory_pages = 0;
    assert_eq!(validate(&p.bytes(), &vm, ptr::null()).status, 0);
    assert_eq!(
        validate(&Program::default().bytes(), &vm, ptr::null()).status,
        1
    );
    p.memory = None;
    assert_eq!(code(&validate(&p.bytes(), &vm, ptr::null())), "unsupported");
    for memory in [
        vec![2, 1, 0, 0, 1, 0, 0],
        vec![1, 3, 0, 0],
        vec![1, 1, 2, 1],
    ] {
        let p = Program {
            memory: Some(memory),
            ..Program::default()
        };
        assert_eq!(validate(&p.bytes(), ptr::null(), ptr::null()).status, 1);
    }
    for field in 0..8 {
        let mut vm = vm_limits();
        match field {
            0 => vm.struct_size = 31,
            1 => vm.abi_version = 2,
            2 => vm.fuel += 1,
            3 => vm.memory_pages += 1,
            4 => vm.operand_stack = 0,
            5 => vm.call_depth = 0,
            6 => vm.host_calls += 1,
            _ => vm.operand_stack += 1,
        };
        let r = validate(&Program::default().bytes(), &vm, ptr::null());
        assert_eq!((r.status, code(&r)), (3, "invalid_arguments"));
    }
    for field in 0..11 {
        let mut cap = MixerVmCapabilityLimitsV1::default();
        match field {
            0 => cap.struct_size = 31,
            1 => cap.abi_version = 2,
            2 => cap.maximum_requests = 0,
            3 => cap.maximum_requests = 9,
            4 => cap.timeout_milliseconds = 0,
            5 => cap.timeout_milliseconds = 30001,
            6 => cap.turn_milliseconds = 0,
            7 => cap.turn_milliseconds = 51,
            8 => cap.reserved = 1,
            9 => cap.reservation_bytes = 0,
            _ => cap.reservation_bytes = 8388609,
        };
        let r = validate(&Program::default().bytes(), ptr::null(), &cap);
        assert_eq!((r.status, code(&r)), (3, "invalid_arguments"));
    }
}
#[test]
fn numeric_preflight_covers_every_pointer_before_any_write_and_accepts_unaligned() {
    let _serial = SERIAL.lock().unwrap();
    assert_eq!(
        (
            size_of::<MixerVmLimits>(),
            size_of::<MixerVmCapabilityLimitsV1>(),
            size_of::<MixerVmReport>()
        ),
        (32, 32, 352)
    );
    assert_eq!(
        (
            offset_of!(MixerVmReport, fuel_used),
            offset_of!(MixerVmReport, code)
        ),
        (24, 48)
    );
    let bytes = Program::default().bytes();
    let mut storage = vec![0xa5u8; 2048];
    let original = storage.clone();
    let out = unsafe { storage.as_mut_ptr().add(1025).cast::<MixerVmReport>() };
    unsafe {
        for (module, len, vm, cap, report) in [
            (ptr::null(), 1, ptr::null(), ptr::null(), out),
            (usize::MAX as *const u8, 1, ptr::null(), ptr::null(), out),
            (
                ptr::with_exposed_provenance::<u8>(1),
                4 * 1024 * 1024 + 1,
                ptr::null(),
                ptr::null(),
                out,
            ),
            (
                bytes.as_ptr(),
                bytes.len(),
                usize::MAX as *const MixerVmLimits,
                ptr::null(),
                out,
            ),
            (
                bytes.as_ptr(),
                bytes.len(),
                ptr::null(),
                usize::MAX as *const MixerVmCapabilityLimitsV1,
                out,
            ),
            (
                bytes.as_ptr(),
                bytes.len(),
                ptr::null(),
                ptr::null(),
                ptr::null_mut(),
            ),
            (
                bytes.as_ptr(),
                bytes.len(),
                ptr::null(),
                ptr::null(),
                usize::MAX as *mut MixerVmReport,
            ),
            (out.cast(), 1, ptr::null(), ptr::null(), out),
            (bytes.as_ptr(), bytes.len(), out.cast(), ptr::null(), out),
            (bytes.as_ptr(), bytes.len(), ptr::null(), out.cast(), out),
        ] {
            assert_eq!(
                mixer_vm_capability_guest_ui_validate_v1(module, len, vm, cap, report),
                3
            );
            assert_eq!(storage, original);
        }
        // Preflight must reject report/input overlap even when report starts
        // inside an input, and the ranges need no C alignment.
        let input = storage.as_mut_ptr().add(900);
        assert_eq!(
            mixer_vm_capability_guest_ui_validate_v1(input, 200, ptr::null(), ptr::null(), out),
            3
        );
        assert_eq!(storage, original);
        let vm = storage.as_mut_ptr().add(1).cast::<MixerVmLimits>();
        let cap = storage
            .as_mut_ptr()
            .add(65)
            .cast::<MixerVmCapabilityLimitsV1>();
        vm.write_unaligned(vm_limits());
        cap.write_unaligned(MixerVmCapabilityLimitsV1::default());
        assert_eq!(
            mixer_vm_capability_guest_ui_validate_v1(bytes.as_ptr(), bytes.len(), vm, cap, out),
            0
        );
        assert_eq!(out.read_unaligned().status, 0);
        assert_eq!(storage[0], 0xa5);
        assert_eq!(storage[64], 0xa5);
        assert_eq!(storage[1024], 0xa5);
        // An exact 4 MiB numeric boundary reaches module validation, not status3.
        let big = vec![0u8; 4 * 1024 * 1024];
        assert_eq!(
            mixer_vm_capability_guest_ui_validate_v1(
                big.as_ptr(),
                big.len(),
                ptr::null(),
                ptr::null(),
                out
            ),
            1
        );
        assert_eq!(
            mixer_vm_capability_guest_ui_validate_v1(ptr::null(), 0, ptr::null(), ptr::null(), out),
            1
        );
    }
}
#[test]
fn validation_does_not_consume_or_require_registry_slots() {
    let _serial = SERIAL.lock().unwrap();
    let bytes = Program::default().bytes();
    for _ in 0..32 {
        assert_eq!(validate(&bytes, ptr::null(), ptr::null()).status, 0);
    }
    let mut handles = Vec::new();
    let mut r = MixerVmReport::default();
    let empty = b"\0asm\x01\0\0\0";
    unsafe {
        for _ in 0..16 {
            let mut h = 0;
            assert_eq!(
                mixer_vm_session_create_v1(
                    1,
                    empty.as_ptr(),
                    empty.len(),
                    ptr::null(),
                    &mut h,
                    &mut r
                ),
                0
            );
            handles.push(h);
        }
        let mut rejected = 99;
        assert_eq!(
            mixer_vm_session_create_v1(
                1,
                empty.as_ptr(),
                empty.len(),
                ptr::null(),
                &mut rejected,
                &mut r
            ),
            3
        );
        assert_eq!(rejected, 0);
        assert_eq!(validate(&bytes, ptr::null(), ptr::null()).status, 0);
        let mut p = Program::default();
        p.exports.remove(1);
        export_error(&p);
        for handle in handles {
            assert_eq!(mixer_vm_session_close_v1(handle, &mut r), 0);
        }
    }
}
