#![cfg(feature = "experimental-capability-native")]
//! Original caller-thread requested-allocation probe; no process heap/RSS claim.
use mixer_vm::*;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    cell::Cell,
    ptr,
};
#[path = "guest_ui/fixture.rs"]
mod fixture;
#[derive(Clone, Copy, Default, Debug)]
struct Counts {
    enabled: bool,
    calls: usize,
    live: isize,
    peak: usize,
    largest: usize,
}
thread_local! { static COUNTS: Cell<Counts> = const { Cell::new(Counts { enabled: false, calls: 0, live: 0, peak: 0, largest: 0 }) }; }
struct Probe;
fn record(add: usize, remove: usize, allocation: bool) {
    let _ = COUNTS.try_with(|cell| {
        let mut c = cell.get();
        if c.enabled {
            c.calls += usize::from(allocation);
            c.live += add as isize - remove as isize;
            c.peak = c.peak.max(c.live.max(0) as usize);
            c.largest = c.largest.max(add);
            cell.set(c);
        }
    });
}
unsafe impl GlobalAlloc for Probe {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc(l) };
        if !p.is_null() {
            record(l.size(), 0, true);
        }
        p
    }
    unsafe fn alloc_zeroed(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc_zeroed(l) };
        if !p.is_null() {
            record(l.size(), 0, true);
        }
        p
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        let q = unsafe { System.realloc(p, l, n) };
        if !q.is_null() {
            record(n, l.size(), true);
        }
        q
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        record(0, l.size(), false);
        unsafe { System.dealloc(p, l) };
    }
}
#[global_allocator]
static ALLOCATOR: Probe = Probe;
fn measured<F: FnOnce() -> u32>(f: F) -> (u32, Counts) {
    COUNTS.with(|c| {
        c.set(Counts {
            enabled: true,
            ..Counts::default()
        })
    });
    let status = f();
    let counts = COUNTS.with(|c| {
        let v = c.get();
        c.set(Counts::default());
        v
    });
    (status, counts)
}
#[test]
fn validation_has_no_instance_memory_or_retained_owner_and_creation_probe_detects_memory() {
    let p = fixture::Program {
        memory: Some(vec![1, 1, 32, 32]),
        ..fixture::Program::default()
    };
    let bytes = p.bytes();
    let mut r = MixerVmReport::default();
    let (status, validation) = measured(|| unsafe {
        mixer_vm_capability_guest_ui_validate_v1(
            bytes.as_ptr(),
            bytes.len(),
            ptr::null(),
            ptr::null(),
            &mut r,
        )
    });
    assert_eq!(status, 0);
    assert_eq!(validation.live, 0);
    assert!(validation.largest < 65536 && validation.peak < 65536);
    assert_eq!((r.fuel_used, r.host_calls_used), (0, 0));
    let mut handle = 0;
    let (status, creation) = measured(|| unsafe {
        mixer_vm_capability_session_create_v1(
            bytes.as_ptr(),
            bytes.len(),
            fixture::NAMES[0].as_ptr(),
            fixture::NAMES[0].len(),
            ptr::null(),
            ptr::null(),
            &mut handle,
            &mut r,
        )
    });
    assert_eq!(status, 0);
    assert_ne!(handle, 0);
    assert_eq!(creation.largest, 32 * 65536);
    assert!(creation.live >= 32 * 65536);
    assert_eq!(
        unsafe { mixer_vm_capability_session_close_v1(handle, &mut r) },
        0
    );
    println!("guest-UI native validation requested counts={validation:?}; construction positive-control={creation:?}; caller-thread requested allocation sizes only, no heap/RSS claim");
}
