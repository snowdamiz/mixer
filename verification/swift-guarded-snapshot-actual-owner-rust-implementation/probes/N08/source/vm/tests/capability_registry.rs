#![cfg(feature = "experimental-capability-native")]
mod common;
use common::{section, u32leb};
use mixer_vm::*;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    ptr::null,
    sync::atomic::{AtomicBool, Ordering},
    time::{Duration, Instant},
};

struct GatedAllocator;
static ARMED: AtomicBool = AtomicBool::new(false);
static ENTERED: AtomicBool = AtomicBool::new(false);
static RELEASE: AtomicBool = AtomicBool::new(false);
unsafe impl GlobalAlloc for GatedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        unsafe { System.alloc(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        if layout.size() == 65536 && layout.align() == 1 && ARMED.swap(false, Ordering::AcqRel) {
            ENTERED.store(true, Ordering::Release);
            let deadline = Instant::now() + Duration::from_secs(10);
            while !RELEASE.load(Ordering::Acquire) && Instant::now() < deadline {
                std::thread::yield_now();
            }
        }
        unsafe { System.dealloc(pointer, layout) }
    }
}
#[global_allocator]
static ALLOCATOR: GatedAllocator = GatedAllocator;

fn name(value: &str, bytes: &mut Vec<u8>) {
    bytes.extend(u32leb(value.len() as u32));
    bytes.extend(value.as_bytes());
}
fn guest() -> Vec<u8> {
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    // Defined startup/wake are void; the enqueue wrapper forwards three i32s.
    section(
        &mut bytes,
        1,
        vec![2, 0x60, 0, 0, 0x60, 3, 0x7f, 0x7f, 0x7f, 1, 0x7f],
    );
    let mut imports = vec![1];
    name("mixer.capability.v1", &mut imports);
    name("storage_get", &mut imports);
    imports.extend([0, 1]);
    section(&mut bytes, 2, imports);
    section(&mut bytes, 3, vec![3, 0, 0, 1]);
    section(&mut bytes, 5, vec![1, 1, 1, 1]);
    let mut exports = vec![3];
    for (label, index) in [
        ("startup", 1),
        ("mixer_guest_capability_ready_v1", 2),
        ("enqueue", 3),
    ] {
        name(label, &mut exports);
        exports.extend([0, index]);
    }
    section(&mut bytes, 7, exports);
    let mut code = vec![3, 2, 0, 0x0b, 2, 0, 0x0b];
    let body = [0, 0x20, 0, 0x20, 1, 0x20, 2, 0x10, 0, 0x0b];
    code.extend(u32leb(body.len() as u32));
    code.extend(body);
    section(&mut bytes, 10, code);
    bytes
}
fn create_legacy() -> (u32, u64) {
    let bytes = b"\0asm\x01\0\0\0";
    let mut handle = 99;
    let mut report = MixerVmReport::default();
    let status = unsafe {
        mixer_vm_session_create_v1(
            1,
            bytes.as_ptr(),
            bytes.len(),
            null(),
            &mut handle,
            &mut report,
        )
    };
    (status, handle)
}
fn create_capability(bytes: &[u8]) -> (u32, u64) {
    let mut handle = 99;
    let mut report = MixerVmReport::default();
    let status = unsafe {
        mixer_vm_capability_session_create_v1(
            bytes.as_ptr(),
            bytes.len(),
            b"startup".as_ptr(),
            7,
            null(),
            null(),
            &mut handle,
            &mut report,
        )
    };
    (status, handle)
}

#[test]
fn mixed_pool_retains_closed_native_work_and_final_destructor_then_retires_handle() {
    // One integration test per process isolates the global sixteen-slot registry.
    let bytes = guest();
    let legacy: Vec<_> = (0..8)
        .map(|_| {
            let (s, h) = create_legacy();
            assert_eq!(s, 0);
            h
        })
        .collect();
    let capabilities: Vec<_> = (0..8)
        .map(|_| {
            let (s, h) = create_capability(&bytes);
            assert_eq!(s, 0);
            h
        })
        .collect();
    let target = capabilities[0];
    let mut report = MixerVmReport::default();
    unsafe {
        assert_eq!(mixer_vm_session_cancel_v1(target, &mut report), 3);
        assert_eq!(mixer_vm_session_close_v1(target, &mut report), 3);
        assert_eq!(
            mixer_vm_capability_session_cancel_v1(legacy[0], &mut report),
            3
        );
        assert_eq!(
            mixer_vm_capability_session_close_v1(legacy[0], &mut report),
            3
        );
        assert_eq!(
            mixer_vm_capability_session_startup_v1(target, &mut report),
            0
        );
        assert_eq!(
            mixer_vm_capability_session_enable_v1(target, &mut report),
            0
        );
        assert_eq!(
            mixer_vm_capability_session_write_v1(target, 0, b"{}".as_ptr(), 2, &mut report),
            0
        );
        let args = [0, 2, 16].map(|value| MixerVmValue {
            value_type: 1,
            reserved: 0,
            value,
        });
        assert_eq!(
            mixer_vm_capability_session_invoke_v1(
                target,
                b"enqueue".as_ptr(),
                7,
                args.as_ptr(),
                args.len(),
                &mut report
            ),
            0
        );
        assert_eq!((report.value_type, report.value), (1, 0));
    }
    let mut output = [0u8; 256];
    let mut message = MixerVmCapabilityMessageV1::default();
    unsafe {
        assert_eq!(
            mixer_vm_capability_take_v1(
                target,
                &mut message,
                output.as_mut_ptr(),
                output.len(),
                &mut report
            ),
            0
        );
    }
    assert_eq!(
        (message.kind, message.operation, message.payload_length),
        (1, 2, 2)
    );
    assert_eq!(&output[..2], b"{}");
    assert_eq!(create_legacy(), (3, 0));
    assert_eq!(create_capability(&bytes), (3, 0));
    unsafe {
        assert_eq!(mixer_vm_capability_session_close_v1(target, &mut report), 0);
        assert_eq!(
            mixer_vm_capability_session_read_v1(target, 0, output.as_mut_ptr(), 1, &mut report),
            3
        );
    }
    assert_eq!(create_legacy(), (3, 0));
    assert_eq!(create_capability(&bytes), (3, 0));

    // Last ack may reclaim, but the shared slot stays unavailable throughout
    // actual instance memory destruction, outside the registry mutex.
    ARMED.store(true, Ordering::Release);
    let token = message.token;
    let thread = std::thread::spawn(move || {
        let mut result = MixerVmCapabilityResultV1::default();
        let mut report = MixerVmReport::default();
        unsafe { mixer_vm_capability_ack_exit_v1(target, token, 2, &mut result, &mut report) }
    });
    let until = Instant::now() + Duration::from_secs(5);
    while !ENTERED.load(Ordering::Acquire) && Instant::now() < until {
        std::thread::yield_now();
    }
    let entered = ENTERED.load(Ordering::Acquire);
    let while_reclaiming = if entered { create_legacy() } else { (999, 0) };
    RELEASE.store(true, Ordering::Release);
    let ack_status = thread.join().unwrap();
    assert!(entered, "last native ack did not reach memory destructor");
    assert_eq!(while_reclaiming, (3, 0));
    assert_eq!(ack_status, 0);
    let (status, replacement) = create_capability(&bytes);
    assert_eq!(status, 0);
    assert_ne!(replacement, target);
    assert_eq!(replacement as u32, target as u32);
    let mut result = MixerVmCapabilityResultV1::default();
    unsafe {
        assert_eq!(
            mixer_vm_capability_ack_exit_v1(target, token, 2, &mut result, &mut report),
            3
        );
        assert_eq!(
            mixer_vm_capability_session_startup_v1(replacement, &mut report),
            0
        );
        assert_eq!(
            mixer_vm_capability_session_close_v1(replacement, &mut report),
            0
        );
        for handle in &capabilities[1..] {
            assert_eq!(
                mixer_vm_capability_session_close_v1(*handle, &mut report),
                0
            );
        }
        for handle in legacy {
            assert_eq!(mixer_vm_session_close_v1(handle, &mut report), 0);
        }
    }
}
