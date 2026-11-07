mod common;
use common::{Function, Spec};
use mixer_vm::*;
use std::{
    ptr::{null, null_mut},
    sync::Mutex,
};

static TEST_LOCK: Mutex<()> = Mutex::new(());
struct Session(u64);
impl Drop for Session {
    fn drop(&mut self) {
        unsafe {
            mixer_vm_session_close_v1(self.0, &mut MixerVmReport::default());
        }
    }
}
fn code(r: &MixerVmReport) -> &str {
    std::str::from_utf8(r.code.split(|b| *b == 0).next().unwrap()).unwrap()
}
fn create(profile: u32, module: &[u8], limits: *const MixerVmLimits) -> (Session, MixerVmReport) {
    let mut handle = u64::MAX;
    let mut r = MixerVmReport::default();
    let status = unsafe {
        mixer_vm_session_create_v1(
            profile,
            module.as_ptr(),
            module.len(),
            limits,
            &mut handle,
            &mut r,
        )
    };
    assert_eq!(status, r.status);
    (Session(handle), r)
}
fn invoke(handle: u64, name: &str, args: &[MixerVmValue]) -> MixerVmReport {
    let mut r = MixerVmReport::default();
    let status = unsafe {
        mixer_vm_session_invoke_v1(
            handle,
            name.as_ptr(),
            name.len(),
            args.as_ptr(),
            args.len(),
            &mut r,
        )
    };
    assert_eq!(status, r.status);
    r
}
fn counter() -> Vec<u8> {
    Spec {
        functions: vec![Function::new(
            vec![],
            Some(Type::I32),
            vec![
                0x23, 0, 0x41, 1, 0x6a, 0x24, 0, // increment global
                0x41, 0, 0x23, 0, 0x36, 2, 0, // store to memory
                0x23, 0, 0x0b,
            ],
        )],
        memory: Some((1, 1)),
        globals: vec![(Value::I32(0), true)],
        ..Default::default()
    }
    .bytes()
}

#[test]
fn retained_memory_globals_and_owned_input() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let mut module = counter();
    let (session, r) = create(1, &module, null());
    assert_eq!(r.status, 0);
    module.fill(0);
    drop(module);
    for i in 1..=3 {
        let r = invoke(session.0, "run", &[]);
        assert_eq!((r.status, r.value_type, r.value), (0, 1, i));
        assert_eq!(r.fuel_used, 9);
    }
    let mut result = [0; 4];
    let mut report = MixerVmReport::default();
    assert_eq!(
        unsafe { mixer_vm_session_read_v1(session.0, 0, result.as_mut_ptr(), 4, &mut report) },
        0
    );
    assert_eq!(result, 3u32.to_le_bytes());
    let (other, r) = create(1, &counter(), null());
    assert_eq!(r.status, 0);
    assert_eq!(invoke(other.0, "run", &[]).value, 1);
}

#[test]
fn copied_memory_whole_bounds_zero_length_and_no_partial_write() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let (s, _) = create(1, &counter(), null());
    let mut r = MixerVmReport::default();
    let bytes = [9, 8, 7, 6];
    assert_eq!(
        unsafe { mixer_vm_session_write_v1(s.0, 65532, bytes.as_ptr(), 4, &mut r) },
        0
    );
    assert_eq!(
        unsafe { mixer_vm_session_write_v1(s.0, 65534, bytes.as_ptr(), 4, &mut r) },
        3
    );
    assert_eq!(code(&r), "memory_out_of_bounds");
    let mut out = [0; 4];
    assert_eq!(
        unsafe { mixer_vm_session_read_v1(s.0, 65532, out.as_mut_ptr(), 4, &mut r) },
        0
    );
    assert_eq!(out, bytes);
    out.fill(42);
    assert_eq!(
        unsafe { mixer_vm_session_read_v1(s.0, 65534, out.as_mut_ptr(), 4, &mut r) },
        3
    );
    assert_eq!(out, [42; 4]);
    for offset in [65536, 65537, u32::MAX] {
        let expected = if offset == 65536 { 0 } else { 3 };
        assert_eq!(
            unsafe { mixer_vm_session_read_v1(s.0, offset, null_mut(), 0, &mut r) },
            expected
        );
        assert_eq!(
            unsafe { mixer_vm_session_write_v1(s.0, offset, null(), 0, &mut r) },
            expected
        );
    }
    assert_eq!(
        unsafe { mixer_vm_session_write_v1(s.0, 0, null(), 1, &mut r) },
        3
    );
    assert_eq!(
        unsafe { mixer_vm_session_read_v1(s.0, 0, null_mut(), 1, &mut r) },
        3
    );
    // Oversized buffers reject before dereferencing the intentionally tiny pointer.
    assert_eq!(
        unsafe { mixer_vm_session_write_v1(s.0, 0, bytes.as_ptr(), 1048577, &mut r) },
        3
    );
    assert_eq!(
        unsafe { mixer_vm_session_read_v1(s.0, 0, out.as_mut_ptr(), 1048577, &mut r) },
        3
    );
    assert_eq!(invoke(s.0, "run", &[]).status, 0);
}

#[test]
fn failed_creates_release_reservations_and_cap_is_enforced() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    for _ in 0..40 {
        let (s, r) = create(1, &[0], null());
        assert_eq!((s.0, r.status), (0, 1));
    }
    let bad = Spec {
        memory: Some((1, 1)),
        data: vec![(65536, vec![1])],
        ..Spec::one(vec![], None, vec![0x0b])
    }
    .bytes();
    let (s, r) = create(1, &bad, null());
    assert_eq!((s.0, r.status), (0, 2));
    assert_eq!(code(&r), "memory_out_of_bounds");
    let mut sessions = Vec::new();
    for _ in 0..16 {
        let (s, r) = create(1, &counter(), null());
        assert_eq!(r.status, 0);
        sessions.push(s);
    }
    let (s, r) = create(1, &counter(), null());
    assert_eq!((s.0, r.status), (0, 3));
    assert_eq!(code(&r), "session_limit");
    drop(sessions.pop());
    let (s, r) = create(1, &counter(), null());
    assert_eq!(r.status, 0);
    drop(s);
}

#[test]
fn close_and_slot_reuse_reject_stale_handles() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let (s, _) = create(1, &counter(), null());
    let stale = s.0;
    drop(s);
    let (replacement, _) = create(1, &counter(), null());
    assert_ne!(stale, replacement.0);
    for handle in [0, u64::MAX, stale, 1, 1u64 << 32] {
        let r = invoke(handle, "run", &[]);
        assert_eq!(r.status, 3);
        assert_eq!(code(&r), "invalid_session");
        let mut r = MixerVmReport::default();
        assert_eq!(unsafe { mixer_vm_session_close_v1(handle, &mut r) }, 3);
        assert_eq!(unsafe { mixer_vm_session_cancel_v1(handle, &mut r) }, 3);
    }
    assert_eq!(invoke(replacement.0, "run", &[]).value, 1);
}

#[test]
fn trap_cancellation_and_signature_errors_are_terminal() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    for module in [
        Spec::one(vec![], None, vec![0, 0x0b]).bytes(),
        Spec::one(vec![], None, vec![3, 0x40, 0x0c, 0, 0x0b, 0x0b]).bytes(),
    ] {
        let (s, r) = create(1, &module, null());
        assert_eq!(r.status, 0);
        assert_eq!(invoke(s.0, "run", &[]).status, 2);
        assert_eq!(code(&invoke(s.0, "run", &[])), "session_terminal");
    }
    let (s, _) = create(1, &counter(), null());
    let mut r = MixerVmReport::default();
    assert_eq!(unsafe { mixer_vm_session_cancel_v1(s.0, &mut r) }, 0);
    assert_eq!(unsafe { mixer_vm_session_cancel_v1(s.0, &mut r) }, 0);
    assert_eq!(code(&invoke(s.0, "run", &[])), "session_terminal");
    let mut byte = 0;
    assert_eq!(
        unsafe { mixer_vm_session_read_v1(s.0, 0, &mut byte, 1, &mut r) },
        2
    );
    assert_eq!(
        unsafe { mixer_vm_session_write_v1(s.0, 0, &byte, 1, &mut r) },
        2
    );
    let (s, _) = create(1, &counter(), null());
    assert_eq!(code(&invoke(s.0, "missing", &[])), "unknown_export");
    assert_eq!(code(&invoke(s.0, "run", &[])), "session_terminal");
    let (s, _) = create(1, &counter(), null());
    assert_eq!(
        invoke(
            s.0,
            "run",
            &[MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 1
            }]
        )
        .status,
        2
    );
    assert_eq!(code(&invoke(s.0, "run", &[])), "session_terminal");
}

#[test]
fn malformed_abi_arguments_leave_session_usable() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let (s, _) = create(1, &counter(), null());
    for arg in [
        MixerVmValue {
            value_type: 1,
            reserved: 1,
            value: 0,
        },
        MixerVmValue {
            value_type: 1,
            reserved: 0,
            value: i64::MAX,
        },
        MixerVmValue {
            value_type: 3,
            reserved: 0,
            value: 0,
        },
    ] {
        assert_eq!(invoke(s.0, "run", &[arg]).status, 3);
    }
    let mut r = MixerVmReport::default();
    assert_eq!(
        unsafe { mixer_vm_session_invoke_v1(s.0, [255].as_ptr(), 1, null(), 0, &mut r) },
        3
    );
    assert_eq!(invoke(s.0, "run", &[]).status, 0);
    let (s, r) = create(0, &counter(), null());
    assert_eq!((s.0, r.status), (0, 3));
    let mut handle = 123;
    assert_eq!(
        unsafe { mixer_vm_session_create_v1(1, null(), 0, null(), &mut handle, null_mut()) },
        3
    );
    assert_eq!(handle, 123); // null report means no work or output mutation
    assert_eq!(
        unsafe { mixer_vm_session_create_v1(1, null(), 0, null(), null_mut(), &mut r.clone()) },
        3
    );
}

#[test]
fn opt_in_profiles_and_per_call_budgets_are_retained() {
    let _serial = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let float = Spec::one(vec![], Some(Type::F32), vec![0x43, 0, 0, 0, 0x80, 0x0b]).bytes();
    let (s, r) = create(1, &float, null());
    assert_eq!((s.0, r.status), (0, 1));
    for profile in [2, 3] {
        let (s, r) = create(profile, &float, null());
        assert_eq!(r.status, 0);
        for _ in 0..2 {
            let r = invoke(s.0, "run", &[]);
            assert_eq!((r.status, r.value_type, r.value), (0, 3, 0x80000000));
        }
    }
    let limits = MixerVmLimits {
        struct_size: 32,
        abi_version: 1,
        fuel: 9,
        memory_pages: 1,
        operand_stack: 32,
        call_depth: 4,
        host_calls: 0,
    };
    let (s, r) = create(1, &counter(), &limits);
    assert_eq!(r.status, 0);
    for i in 1..=3 {
        let r = invoke(s.0, "run", &[]);
        assert_eq!((r.status, r.value, r.fuel_used), (0, i, 9));
    }
    let limits = MixerVmLimits { fuel: 8, ..limits };
    let (s, r) = create(1, &counter(), &limits);
    assert_eq!(r.status, 0);
    let r = invoke(s.0, "run", &[]);
    assert_eq!(code(&r), "fuel_exhausted");
    assert_eq!(r.fuel_used, 8);
}
