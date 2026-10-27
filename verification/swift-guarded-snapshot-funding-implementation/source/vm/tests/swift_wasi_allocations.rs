#![cfg(feature = "experimental-swift-wasi")]
use mixer_vm::experimental_wasi::*;
use mixer_vm::{Cancellation, Value};
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;
use std::sync::atomic::{AtomicUsize, Ordering::SeqCst};

struct Meter;
thread_local! {
    static ACTIVE:Cell<bool>=const { Cell::new(false) };
    static ORDINAL:Cell<usize>=const { Cell::new(0) };
    static FAIL:Cell<usize>=const { Cell::new(0) };
}
// Track only the at-most-four owned allocations, avoiding assumptions about which
// harness thread eventually frees unrelated process allocations.
static SLOTS: [(AtomicUsize, AtomicUsize); 8] =
    [const { (AtomicUsize::new(0), AtomicUsize::new(0)) }; 8];
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
fn request() -> bool {
    ACTIVE.with(|active| {
        if !active.get() {
            return true;
        }
        ORDINAL.with(|ordinal| {
            let n = ordinal.get() + 1;
            ordinal.set(n);
            FAIL.with(|fail| n != fail.get())
        })
    })
}
fn allocated(pointer: *mut u8, size: usize) {
    if !ACTIVE.with(Cell::get) {
        return;
    }
    for (address, bytes) in &SLOTS {
        if address.load(SeqCst) == 0 {
            bytes.store(size, SeqCst);
            address.store(pointer as usize, SeqCst);
            let live = LIVE.fetch_add(size, SeqCst) + size;
            PEAK.fetch_max(live, SeqCst);
            return;
        }
    }
    std::process::abort();
}
fn freed(pointer: *mut u8) {
    for (address, bytes) in &SLOTS {
        if address
            .compare_exchange(pointer as usize, 0, SeqCst, SeqCst)
            .is_ok()
        {
            LIVE.fetch_sub(bytes.load(SeqCst), SeqCst);
            return;
        }
    }
}
unsafe impl GlobalAlloc for Meter {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let p = unsafe { System.alloc(layout) };
        if !p.is_null() {
            allocated(p, layout.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let p = unsafe { System.alloc_zeroed(layout) };
        if !p.is_null() {
            allocated(p, layout.size());
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, layout: Layout) {
        unsafe {
            System.dealloc(p, layout);
        }
        freed(p);
    }
    unsafe fn realloc(&self, p: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let next = unsafe { System.realloc(p, layout, size) };
        if !next.is_null() {
            freed(p);
            allocated(next, size);
        }
        next
    }
}
#[global_allocator]
static ALLOCATOR: Meter = Meter;
fn arm(fail: usize) -> usize {
    ORDINAL.with(|n| n.set(0));
    FAIL.with(|n| n.set(fail));
    let baseline = LIVE.load(SeqCst);
    PEAK.store(baseline, SeqCst);
    ACTIVE.with(|n| n.set(true));
    baseline
}
fn disarm() -> (usize, usize) {
    ACTIVE.with(|n| n.set(false));
    (ORDINAL.with(Cell::get), PEAK.load(SeqCst))
}
fn i(n: u32) -> Value {
    Value::I32(n as i32)
}

#[test]
fn each_constructor_allocation_fails_cleanly_and_dispatch_never_allocates() {
    let grants = WasiGrants {
        secure_random: true,
        realtime: true,
        monotonic: true,
        stdout: true,
        stderr: true,
    };
    for fail in 1..=4 {
        let cancel = Cancellation::default();
        let baseline = arm(fail);
        let result = WasiContext::new(grants, WasiBudget::default(), cancel.clone());
        let (allocations, _) = disarm();
        assert!(matches!(result, Err(WasiFailure::Allocation)));
        assert_eq!(allocations, fail);
        assert_eq!(LIVE.load(SeqCst), baseline);
    }
    let cancel = Cancellation::default();
    let baseline = arm(0);
    let mut context = WasiContext::new(grants, WasiBudget::default(), cancel.clone()).unwrap();
    let (allocations, peak) = disarm();
    let reservations = context.usage().reservations;
    assert_eq!(allocations, 4);
    assert_eq!(
        peak - baseline,
        (reservations.staging_bytes
            + reservations.rollback_bytes
            + reservations.stdout_bytes
            + reservations.stderr_bytes) as usize
    );
    let mut memory = [0xa5; 2048];
    memory[..4].copy_from_slice(&32u32.to_le_bytes());
    memory[4..8].copy_from_slice(&1024u32.to_le_bytes());
    let native_calls = [
        (WasiFunction::RandomGet, [i(32), i(1024), i(0), i(0)], 2),
        (WasiFunction::FdWrite, [i(1), i(0), i(1), i(16)], 4),
        (WasiFunction::ClockResGet, [i(0), i(24), i(0), i(0)], 2),
        (WasiFunction::ArgsGet, [i(24), i(32), i(0), i(0)], 2),
        (WasiFunction::FdFdstatGet, [i(1), i(40), i(0), i(0)], 2),
        (WasiFunction::FdClose, [i(1), i(0), i(0), i(0)], 1),
    ];
    for (function, args, count) in native_calls {
        arm(1);
        let outcome = context.dispatch(function, &args[..count], &mut memory);
        let (calls, _) = disarm();
        assert_eq!(calls, 0, "{function:?}");
        assert_eq!(outcome, WasiOutcome::Errno(Errno::Success), "{function:?}");
    }
    cancel.cancel();
    arm(1);
    let outcome = context.dispatch(WasiFunction::RandomGet, &[i(0), i(4)], &mut memory);
    let (calls, _) = disarm();
    assert_eq!(calls, 0);
    assert_eq!(outcome, WasiOutcome::Failure(WasiFailure::Cancelled));
    arm(1);
    let outcome = context.dispatch(WasiFunction::ProcExit, &[], &mut memory);
    let (calls, _) = disarm();
    assert_eq!(calls, 0);
    assert_eq!(outcome, WasiOutcome::Failure(WasiFailure::Cancelled));
    assert_eq!(context.usage().reservations, reservations);
    drop(context);
    assert_eq!(LIVE.load(SeqCst), baseline);
    println!("constructor allocations={allocations}, requested heap peak={}, fixed state={}, allocation-failure ordinals=4, dispatch allocations=0",peak-baseline,reservations.fixed_state_bytes);
}
