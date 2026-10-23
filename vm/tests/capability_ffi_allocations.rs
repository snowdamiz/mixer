#![cfg(feature = "experimental-capability-native")]
//! Original isolated allocator probe: no deployment/RSS/physical heap claim.
use mixer_vm::*;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    ptr,
    sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst},
};
#[path = "capability_ffi/fixture.rs"]
mod fixture;
struct Probe;
static TRACK: AtomicBool = AtomicBool::new(false);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static FAIL: AtomicUsize = AtomicUsize::new(0);
static LARGEST: AtomicUsize = AtomicUsize::new(0);
fn permit(size: usize) -> bool {
    if !TRACK.load(SeqCst) {
        return true;
    }
    LARGEST.fetch_max(size, SeqCst);
    CALLS.fetch_add(1, SeqCst) + 1 != FAIL.load(SeqCst)
}
fn add(size: usize) {
    let live = LIVE.fetch_add(size, SeqCst) + size;
    if TRACK.load(SeqCst) {
        PEAK.fetch_max(live, SeqCst);
    }
}
unsafe impl GlobalAlloc for Probe {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        if !permit(l.size()) {
            return ptr::null_mut();
        }
        let p = unsafe { System.alloc(l) };
        if !p.is_null() {
            add(l.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, l: Layout) -> *mut u8 {
        if !permit(l.size()) {
            return ptr::null_mut();
        }
        let p = unsafe { System.alloc_zeroed(l) };
        if !p.is_null() {
            add(l.size());
        }
        p
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        if !permit(n) {
            return ptr::null_mut();
        }
        let q = unsafe { System.realloc(p, l, n) };
        if !q.is_null() {
            LIVE.fetch_sub(l.size(), SeqCst);
            add(n);
        }
        q
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        unsafe { System.dealloc(p, l) };
        LIVE.fetch_sub(l.size(), SeqCst);
    }
}
#[global_allocator]
static ALLOCATOR: Probe = Probe;
fn begin(fail: usize) -> usize {
    CALLS.store(0, SeqCst);
    FAIL.store(fail, SeqCst);
    LARGEST.store(0, SeqCst);
    let base = LIVE.load(SeqCst);
    PEAK.store(base, SeqCst);
    TRACK.store(true, SeqCst);
    base
}
fn end(base: usize) -> (usize, usize, usize, usize) {
    TRACK.store(false, SeqCst);
    (
        CALLS.load(SeqCst),
        LIVE.load(SeqCst).saturating_sub(base),
        PEAK.load(SeqCst).saturating_sub(base),
        LARGEST.load(SeqCst),
    )
}
#[test]
fn validation_has_no_instance_memory_and_post_allocation_failure_remains_retryable() {
    unsafe {
        let source = fixture::wasm_with_memory(32);
        let mut r = MixerVmReport::default();
        let base = begin(0);
        assert_eq!(
            mixer_vm_capability_validate_v1(
                source.as_ptr(),
                source.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut r
            ),
            0
        );
        let validation = end(base);
        assert_eq!(validation.1, 0);
        assert!(validation.2 < 65536);
        assert!(validation.3 < 65536);
        println!("native validate-only requested(calls,retained,logical_peak,largest)={validation:?};32-page module not instantiated");
        let base = begin(0);
        let mut handle = 0;
        assert_eq!(
            mixer_vm_capability_session_create_v1(
                source.as_ptr(),
                source.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut handle,
                &mut r
            ),
            0
        );
        let construction = end(base);
        assert_eq!(construction.3, 32 * 65536);
        assert!(construction.1 >= 32 * 65536);
        println!("native create32pages requested(calls,retained,logical_peak,largest)={construction:?};includes shared registry first-use overhead if any");
        assert_eq!(mixer_vm_capability_session_close_v1(handle, &mut r), 0);
        let source = fixture::wasm();
        let mut handle = 0;
        assert_eq!(
            mixer_vm_capability_session_create_v1(
                source.as_ptr(),
                source.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut handle,
                &mut r
            ),
            0
        );
        assert_eq!(mixer_vm_capability_session_startup_v1(handle, &mut r), 0);
        assert_eq!(mixer_vm_capability_session_enable_v1(handle, &mut r), 0);
        let args = [
            MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 0,
            },
            MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 4,
            },
            MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 32,
            },
        ];
        assert_eq!(
            mixer_vm_capability_session_invoke_v1(
                handle,
                b"get".as_ptr(),
                3,
                args.as_ptr(),
                3,
                &mut r
            ),
            0
        );
        let mut message = MixerVmCapabilityMessageV1::default();
        let mut output = [0u8; 4];
        assert_eq!(
            mixer_vm_capability_take_v1(handle, &mut message, output.as_mut_ptr(), 4, &mut r),
            0
        );
        let payload = vec![7u8; 1024];
        let mut result = MixerVmCapabilityResultV1::default();
        let base = begin(1);
        assert_eq!(
            mixer_vm_capability_post_v1(
                handle,
                message.token,
                2,
                payload.as_ptr(),
                payload.len(),
                &mut result,
                &mut r
            ),
            2
        );
        let refusal = end(base);
        assert_eq!(refusal, (1, 0, 0, 1024));
        assert_eq!(r.status, 2);
        assert_eq!(result.kind, 0);
        let base = begin(0);
        assert_eq!(
            mixer_vm_capability_post_v1(
                handle,
                message.token,
                2,
                payload.as_ptr(),
                payload.len(),
                &mut result,
                &mut r
            ),
            0
        );
        assert_eq!(end(base), (1, 1024, 1024, 1024));
        println!("native post allocation refusal={refusal:?};retry succeeded;no quarantine/terminal/exit fabricated");
        assert_eq!(mixer_vm_capability_session_close_v1(handle, &mut r), 0);
        let base = begin(1);
        assert_eq!(
            mixer_vm_capability_ack_exit_v1(handle, message.token, 2, &mut result, &mut r),
            0
        );
        assert_eq!(end(base).0, 0);
        let mut sentinel = vec![0xa5u8; std::mem::size_of::<MixerVmReport>() + 1];
        let report = sentinel.as_mut_ptr().add(1).cast::<MixerVmReport>();
        let base = begin(1);
        assert_eq!(
            mixer_vm_capability_validate_v1(
                report.cast(),
                8,
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                report
            ),
            3
        );
        assert_eq!(end(base), (0, 0, 0, 0));
        assert!(sentinel.iter().all(|b| *b == 0xa5));
    }
}
