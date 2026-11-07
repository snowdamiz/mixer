mod common;
use common::Spec;
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
static CLOSED: AtomicBool = AtomicBool::new(false);
unsafe impl GlobalAlloc for GatedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        unsafe { System.alloc(layout) }
    }
    unsafe fn dealloc(&self, p: *mut u8, layout: Layout) {
        if layout.size() == 65536 && layout.align() == 1 && ARMED.swap(false, Ordering::AcqRel) {
            ENTERED.store(true, Ordering::Release);
            while !RELEASE.load(Ordering::Acquire) {
                std::thread::yield_now();
            }
        }
        unsafe { System.dealloc(p, layout) }
    }
}
#[global_allocator]
static ALLOCATOR: GatedAllocator = GatedAllocator;
fn create(bytes: &[u8]) -> (u64, u32) {
    let mut handle = 0;
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
    (handle, status)
}
fn close(handle: u64) -> u32 {
    let mut report = MixerVmReport::default();
    unsafe { mixer_vm_session_close_v1(handle, &mut report) }
}
#[test]
fn closed_in_flight_storage_counts_until_destructor_finishes() {
    let mut spec = Spec::one(vec![], None, vec![0x0b]);
    spec.memory = Some((1, 1));
    let bytes = spec.bytes();
    let mut handles = Vec::new();
    for _ in 0..16 {
        let (h, s) = create(&bytes);
        assert_eq!(s, 0);
        handles.push(h);
    }
    let closing = handles.pop().unwrap();
    ARMED.store(true, Ordering::Release);
    let thread = std::thread::spawn(move || {
        let status = close(closing);
        CLOSED.store(true, Ordering::Release);
        status
    });
    let start = Instant::now();
    while !ENTERED.load(Ordering::Acquire) && start.elapsed() < Duration::from_secs(5) {
        std::thread::yield_now();
    }
    let entered = ENTERED.load(Ordering::Acquire);
    let close_already_returned = CLOSED.load(Ordering::Acquire);
    let (replacement, status) = if entered { create(&bytes) } else { (0, 999) };
    RELEASE.store(true, Ordering::Release);
    let close_status = thread.join().unwrap();
    for handle in handles {
        assert_eq!(close(handle), 0);
    }
    if replacement != 0 {
        assert_eq!(close(replacement), 0);
    }
    assert!(entered, "did not reach 64KiB guest-memory destructor");
    assert!(!close_already_returned, "old close must still be in flight");
    assert_eq!(close_status, 0);
    assert_eq!(status,3,"creation must reject while 15 live instances plus the still-allocated in-flight closing instance exhaust the16-session ceiling; got success with17th allocation");
}
