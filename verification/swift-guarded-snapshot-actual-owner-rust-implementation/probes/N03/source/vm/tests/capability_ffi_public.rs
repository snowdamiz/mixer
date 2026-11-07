#![cfg(feature = "experimental-capability-native")]
use mixer_vm::*;
#[path = "capability_ffi/fixture.rs"]
mod fixture;
use std::{ptr, sync::Mutex};
static SERIAL: Mutex<()> = Mutex::new(());
fn c(status: u32, r: &MixerVmReport, expected: u32) {
    assert_eq!(
        status,
        expected,
        "report status={} code={:?}",
        r.status,
        String::from_utf8_lossy(&r.code)
    );
    assert_eq!(r.status, expected);
}
fn args(v: &[Value]) -> Vec<MixerVmValue> {
    v.iter()
        .map(|v| {
            let (t, n) = match *v {
                Value::I32(n) => (1, n as i64),
                Value::I64(n) => (2, n),
                Value::F32(n) => (3, n as i64),
                Value::F64(n) => (4, n as i64),
            };
            MixerVmValue {
                value_type: t,
                reserved: 0,
                value: n,
            }
        })
        .collect()
}
unsafe fn invoke(h: u64, name: &str, v: &[Value], r: &mut MixerVmReport) -> u32 {
    let a = args(v);
    unsafe {
        mixer_vm_capability_session_invoke_v1(h, name.as_ptr(), name.len(), a.as_ptr(), a.len(), r)
    }
}
unsafe fn create(r: &mut MixerVmReport) -> u64 {
    let w = fixture::wasm();
    let mut h = 0;
    let status = unsafe {
        mixer_vm_capability_session_create_v1(
            w.as_ptr(),
            w.len(),
            b"start".as_ptr(),
            5,
            ptr::null(),
            ptr::null(),
            &mut h,
            r,
        )
    };
    c(status, r, 0);
    h
}
#[test]
fn public_actual_wasm_startup_memory_dispatch_terminal_and_exit_roundtrip() {
    let _serial = SERIAL.lock().unwrap();
    unsafe {
        let mut r = MixerVmReport::default();
        let h = create(&mut r);
        c(mixer_vm_capability_session_enable_v1(h, &mut r), &r, 3);
        c(mixer_vm_capability_session_startup_v1(h, &mut r), &r, 0);
        c(mixer_vm_capability_session_startup_v1(h, &mut r), &r, 3);
        assert_eq!(r.fuel_used, 0);
        c(mixer_vm_capability_session_enable_v1(h, &mut r), &r, 0);
        assert_eq!((r.fuel_used, r.host_calls_used), (0, 0));
        let mut did = 9;
        c(
            mixer_vm_capability_session_wake_v1(h, &mut did, &mut r),
            &r,
            0,
        );
        assert_eq!((did, r.fuel_used, r.host_calls_used), (0, 0, 0));
        c(
            mixer_vm_capability_session_write_v1(h, 0, b"note".as_ptr(), 4, &mut r),
            &r,
            0,
        );
        c(
            invoke(
                h,
                "get",
                &[Value::I32(0), Value::I32(4), Value::I32(32)],
                &mut r,
            ),
            &r,
            0,
        );
        assert_eq!((r.value_type, r.value), (1, 0));
        let mut message = MixerVmCapabilityMessageV1::default();
        let mut output = [0u8; 512];
        c(
            mixer_vm_capability_take_v1(h, &mut message, ptr::null_mut(), 0, &mut r),
            &r,
            0,
        );
        assert_eq!(
            (message.kind, message.payload_length, message.token),
            (3, 4, 0)
        );
        c(
            mixer_vm_capability_take_v1(h, &mut message, output.as_mut_ptr(), output.len(), &mut r),
            &r,
            0,
        );
        assert_eq!(
            (message.kind, message.operation, message.payload_length),
            (1, 2, 4)
        );
        assert_eq!(&output[..4], b"note");
        let token = message.token;
        let mut result = MixerVmCapabilityResultV1::default();
        c(
            mixer_vm_capability_post_v1(h, token, 3, b"opaque".as_ptr(), 6, &mut result, &mut r),
            &r,
            3,
        );
        c(
            mixer_vm_capability_post_v1(h, token, 2, b"opaque".as_ptr(), 6, &mut result, &mut r),
            &r,
            0,
        );
        assert_eq!(result.kind, 0);
        c(
            mixer_vm_capability_ack_exit_v1(h, token, 2, &mut result, &mut r),
            &r,
            0,
        );
        assert_eq!(result.kind, 0);
        c(
            mixer_vm_capability_ack_exit_v1(h, token, 2, &mut result, &mut r),
            &r,
            0,
        );
        assert_eq!(result.kind, 2);
        c(
            mixer_vm_capability_post_v1(h, token, 2, b"again".as_ptr(), 5, &mut result, &mut r),
            &r,
            0,
        );
        assert_eq!(result.kind, 1);
        c(
            mixer_vm_capability_limit_deadline_v1(h, token, 2, 1, &mut result, &mut r),
            &r,
            0,
        );
        assert_eq!((result.kind, result.remaining_milliseconds), (1, 0));
        c(
            invoke(
                h,
                "poll",
                &[
                    Value::I64(token as i64),
                    Value::I32(256),
                    Value::I32(512),
                    Value::I32(48),
                ],
                &mut r,
            ),
            &r,
            0,
        );
        assert_eq!(r.value, 0);
        c(
            mixer_vm_capability_session_read_v1(h, 256, output.as_mut_ptr(), 6, &mut r),
            &r,
            0,
        );
        assert_eq!(&output[..6], b"opaque");
        c(
            mixer_vm_capability_ack_exit_v1(h, token, 2, &mut result, &mut r),
            &r,
            3,
        );
        c(
            mixer_vm_capability_session_read_v1(h, 65536, ptr::null_mut(), 0, &mut r),
            &r,
            0,
        );
        c(
            mixer_vm_capability_session_read_v1(h, 65537, ptr::null_mut(), 0, &mut r),
            &r,
            3,
        );
        c(
            mixer_vm_capability_session_write_v1(h, 65537, ptr::null(), 0, &mut r),
            &r,
            3,
        );
        c(mixer_vm_capability_session_close_v1(h, &mut r), &r, 0);
        c(
            mixer_vm_capability_session_read_v1(h, 0, ptr::null_mut(), 0, &mut r),
            &r,
            3,
        );
    }
}
#[test]
fn required_outputs_and_report_aliases_reject_without_any_mutation() {
    let _serial = SERIAL.lock().unwrap();
    let mut bytes = vec![0xa5u8; 2048];
    let original = bytes.clone();
    unsafe {
        let r = bytes.as_mut_ptr().add(513).cast::<MixerVmReport>();
        let mut h = 0xa5a5a5a5a5a5a5a5;
        assert_eq!(
            mixer_vm_capability_validate_v1(
                r.cast(),
                8,
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                r
            ),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_session_create_v1(
                r.cast(),
                8,
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut h,
                r
            ),
            3
        );
        assert_eq!(h, 0xa5a5a5a5a5a5a5a5);
        assert_eq!(bytes, original);
        assert_eq!(mixer_vm_capability_session_wake_v1(0, r.cast(), r), 3);
        assert_eq!(bytes, original);
        assert_eq!(mixer_vm_capability_session_read_v1(0, 0, r.cast(), 1, r), 3);
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_session_write_v1(0, 0, r.cast(), 1, r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_take_v1(0, r.cast(), ptr::null_mut(), 0, r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_take_v1(0, bytes.as_mut_ptr().cast(), r.cast(), 1, r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_post_v1(0, 0, 2, r.cast(), 1, bytes.as_mut_ptr().cast(), r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(mixer_vm_capability_ack_exit_v1(0, 0, 2, r.cast(), r), 3);
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_limit_deadline_v1(0, 0, 2, 1, r.cast(), r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_session_invoke_v1(0, b"get".as_ptr(), 3, r.cast(), 1, r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(
            mixer_vm_capability_session_invoke_v1(0, r.cast(), 1, ptr::null(), 0, r),
            3
        );
        assert_eq!(bytes, original);
        assert_eq!(mixer_vm_capability_session_cancel_v1(0, ptr::null_mut()), 3);
        assert_eq!(bytes, original);
        assert_eq!(mixer_vm_capability_session_close_v1(0, ptr::null_mut()), 3);
        assert_eq!(bytes, original);
        assert_eq!(mixer_vm_capability_expire_v1(0, ptr::null_mut()), 3);
        assert_eq!(bytes, original);
    }
}
#[test]
fn unaligned_limits_handle_report_message_and_result_storage_work() {
    let _serial = SERIAL.lock().unwrap();
    unsafe {
        let w = fixture::wasm();
        let mut report = vec![0xa5; std::mem::size_of::<MixerVmReport>() + 1];
        let r = report.as_mut_ptr().add(1).cast();
        let mut handle = [0xa5u8; 9];
        let hptr = handle.as_mut_ptr().add(1).cast::<u64>();
        let mut limits = [0u8; 33];
        let l = limits
            .as_mut_ptr()
            .add(1)
            .cast::<MixerVmCapabilityLimitsV1>();
        l.write_unaligned(MixerVmCapabilityLimitsV1::default());
        assert_eq!(
            mixer_vm_capability_session_create_v1(
                w.as_ptr(),
                w.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                l,
                hptr,
                r
            ),
            0
        );
        let h = hptr.read_unaligned();
        assert_ne!(h, 0);
        assert_eq!(handle[0], 0xa5);
        assert_eq!(report[0], 0xa5);
        assert_eq!(mixer_vm_capability_session_startup_v1(h, r), 0);
        assert_eq!(mixer_vm_capability_session_enable_v1(h, r), 0);
        let mut a = vec![0u8; 3 * std::mem::size_of::<MixerVmValue>() + 1];
        let ap = a.as_mut_ptr().add(1).cast::<MixerVmValue>();
        for (i, v) in [0, 4, 32].into_iter().enumerate() {
            ap.add(i).write_unaligned(MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: v,
            });
        }
        assert_eq!(
            mixer_vm_capability_session_invoke_v1(h, b"get".as_ptr(), 3, ap, 3, r),
            0
        );
        let mut message = [0u8; 41];
        let m = message
            .as_mut_ptr()
            .add(1)
            .cast::<MixerVmCapabilityMessageV1>();
        let mut output = [0; 4];
        assert_eq!(
            mixer_vm_capability_take_v1(h, m, output.as_mut_ptr(), 4, r),
            0
        );
        let token = m.read_unaligned().token;
        let mut result = [0u8; 25];
        let result = result
            .as_mut_ptr()
            .add(1)
            .cast::<MixerVmCapabilityResultV1>();
        assert_eq!(mixer_vm_capability_session_close_v1(h, r), 0);
        assert_eq!(mixer_vm_capability_ack_exit_v1(h, token, 2, result, r), 0);
        assert_eq!(result.read_unaligned().abi_version, 1);
    }
}
#[test]
fn invalid_limit_fields_and_names_reject_before_publishing_handle() {
    let _serial = SERIAL.lock().unwrap();
    unsafe {
        let w = fixture::wasm();
        let mut r = MixerVmReport::default();
        for field in 0..12 {
            let mut limits = MixerVmCapabilityLimitsV1::default();
            match field {
                0 => limits.struct_size = 31,
                1 => limits.abi_version = 2,
                2 => limits.maximum_requests = 0,
                3 => limits.maximum_requests = 9,
                4 => limits.timeout_milliseconds = 0,
                5 => limits.timeout_milliseconds = 30001,
                6 => limits.turn_milliseconds = 0,
                7 => limits.turn_milliseconds = 51,
                8 => limits.reserved = 1,
                9 => limits.reservation_bytes = 0,
                10 => limits.reservation_bytes = 8388609,
                _ => limits.struct_size = 33,
            };
            let mut handle = 99;
            c(
                mixer_vm_capability_session_create_v1(
                    w.as_ptr(),
                    w.len(),
                    b"start".as_ptr(),
                    5,
                    ptr::null(),
                    &limits,
                    &mut handle,
                    &mut r,
                ),
                &r,
                3,
            );
            assert_eq!(handle, 0);
        }
        for name in [&b""[..], &b"\xff"[..]] {
            let mut handle = 99;
            c(
                mixer_vm_capability_session_create_v1(
                    w.as_ptr(),
                    w.len(),
                    name.as_ptr(),
                    name.len(),
                    ptr::null(),
                    ptr::null(),
                    &mut handle,
                    &mut r,
                ),
                &r,
                3,
            );
            assert_eq!(handle, 0);
        }
        let mut handle = 99;
        c(
            mixer_vm_capability_session_create_v1(
                w.as_ptr(),
                w.len(),
                b"missing".as_ptr(),
                7,
                ptr::null(),
                ptr::null(),
                &mut handle,
                &mut r,
            ),
            &r,
            1,
        );
        assert_eq!(handle, 0);
        let mut malformed = w.clone();
        let pos = malformed.windows(3).position(|p| p == b"get").unwrap();
        malformed[pos] = b'X';
        // Rename a function export only: validity remains; missing selected entry
        // still rejects1 by the same constructor/export validation path.
        c(
            mixer_vm_capability_validate_v1(
                malformed.as_ptr(),
                malformed.len(),
                b"missing".as_ptr(),
                7,
                ptr::null(),
                ptr::null(),
                &mut r,
            ),
            &r,
            1,
        );
        let h = create(&mut r);
        c(mixer_vm_capability_session_startup_v1(h, &mut r), &r, 0);
        c(mixer_vm_capability_session_cancel_v1(h, &mut r), &r, 0);
        c(mixer_vm_capability_session_cancel_v1(h, &mut r), &r, 0);
        c(mixer_vm_capability_session_enable_v1(h, &mut r), &r, 2);
        c(mixer_vm_capability_session_close_v1(h, &mut r), &r, 0);
        c(mixer_vm_capability_session_cancel_v1(h, &mut r), &r, 3);
    }
}
