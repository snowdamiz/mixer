//! Unit-only synchronous allocator observations; never product admission input.
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct AllocationStats {
    pub allocations: usize,
    pub reallocations: usize,
    pub deallocations: usize,
    pub allocated_bytes: usize,
    pub freed_bytes: usize,
    pub last_size: usize,
    pub last_align: usize,
    pub attempts: usize,
    pub injected_failures: usize,
}
thread_local! {
    static ACTIVE: Cell<bool> = const { Cell::new(false) };
    static FAIL_AT: Cell<Option<usize>> = const { Cell::new(None) };
    static STATS: Cell<AllocationStats> = const { Cell::new(AllocationStats {
        allocations: 0, reallocations: 0, deallocations: 0,
        allocated_bytes: 0, freed_bytes: 0, last_size: 0, last_align: 0,
        attempts: 0, injected_failures: 0,
    }) };
}
fn observe(operation: u8, layout: Layout) -> bool {
    if ACTIVE.try_with(Cell::get).unwrap_or(false) {
        return STATS.with(|slot| {
            let mut stats = slot.get();
            let fail = operation != 2 && FAIL_AT.with(Cell::get) == Some(stats.attempts);
            if operation != 2 {
                stats.attempts += 1;
                stats.injected_failures += usize::from(fail);
            }
            match operation {
                0 => {
                    stats.allocations += 1;
                    stats.allocated_bytes += layout.size();
                    stats.last_size = layout.size();
                    stats.last_align = layout.align();
                }
                1 => stats.reallocations += 1,
                _ => {
                    stats.deallocations += 1;
                    stats.freed_bytes += layout.size();
                }
            }
            slot.set(stats);
            fail
        });
    }
    false
}
struct Observed;
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if observe(0, layout) {
            return std::ptr::null_mut();
        }
        unsafe { System.alloc(layout) }
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if observe(0, layout) {
            return std::ptr::null_mut();
        }
        unsafe { System.alloc_zeroed(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        observe(2, layout);
        unsafe { System.dealloc(pointer, layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if observe(1, layout) {
            // Returning null must leave the original allocation untouched.
            return std::ptr::null_mut();
        }
        unsafe { System.realloc(pointer, layout, bytes) }
    }
}
#[global_allocator]
static ALLOCATOR: Observed = Observed;

/// Captures requests on this thread only. Deallocations may concern storage
/// allocated before this interval; this is not a general live-pointer ledger.
pub(crate) fn measure<T>(body: impl FnOnce() -> T) -> (T, AllocationStats) {
    measure_extended(None, body)
}

/// Injects a null result at one zero-based allocation/reallocation attempt on
/// this thread. Counts include failed requests. `allocated_bytes` retains the
/// original meaning: requested alloc/alloc_zeroed bytes, excluding realloc.
/// This is a unit-test fault injector, never runtime accounting authority.
pub(crate) fn measure_extended<T>(
    fail_at: Option<usize>,
    body: impl FnOnce() -> T,
) -> (T, AllocationStats) {
    struct Reset;
    impl Drop for Reset {
        fn drop(&mut self) {
            ACTIVE.with(|active| active.set(false));
            FAIL_AT.with(|fault| fault.set(None));
        }
    }
    assert!(!ACTIVE.with(Cell::get));
    STATS.with(|stats| stats.set(AllocationStats::default()));
    FAIL_AT.with(|fault| fault.set(fail_at));
    ACTIVE.with(|active| active.set(true));
    let reset = Reset;
    let result = body();
    drop(reset);
    (result, STATS.with(Cell::get))
}

#[test]
fn cancellation_requested_layout_matches_actual_allocation_and_clones_share_it() {
    let layout = crate::Cancellation::requested_backing_layout();
    let (_, stats) = measure(|| {
        let first = std::hint::black_box(crate::Cancellation::default());
        let second = std::hint::black_box(first.clone());
        first.cancel();
        assert!(second.is_cancelled());
        drop(first);
        drop(second);
    });
    assert_eq!(stats.allocations, 1);
    assert_eq!(stats.reallocations, 0);
    assert_eq!(stats.deallocations, 1);
    assert_eq!(stats.allocated_bytes, layout.size());
    assert_eq!(stats.freed_bytes, layout.size());
    assert_eq!(stats.last_size, layout.size());
    assert_eq!(stats.last_align, layout.align());
}

#[test]
fn fallible_vec_allocation_fault_is_real_and_interval_scoped() {
    let (failed, stats) = measure_extended(Some(0), || {
        let mut bytes = Vec::<u8>::new();
        let failed = bytes.try_reserve_exact(61).is_err();
        (failed, bytes.capacity())
    });
    assert_eq!(failed, (true, 0));
    assert_eq!((stats.attempts, stats.injected_failures), (1, 1));
    assert_eq!((stats.allocations, stats.allocated_bytes), (1, 61));
    let (_, stats) = measure(|| {
        let mut bytes = Vec::<u8>::new();
        bytes.try_reserve_exact(61).unwrap();
        std::hint::black_box(&bytes);
    });
    assert_eq!((stats.attempts, stats.injected_failures), (1, 0));
    assert_eq!(stats.deallocations, 1);
}

#[test]
fn allocation_kinds_share_fault_ordinal_and_failed_realloc_preserves_storage() {
    let layout = Layout::from_size_align(32, 8).unwrap();
    // Direct std::alloc calls may be elided under optimization. Exercise the
    // actual observer through an opaque allocator, as an allocator test requires.
    let allocator: &dyn GlobalAlloc = std::hint::black_box(&Observed);
    let (observation, stats) = measure_extended(Some(2), || unsafe {
        let plain = allocator.alloc(layout);
        let zeroed = allocator.alloc_zeroed(layout);
        assert!(!plain.is_null() && !zeroed.is_null());
        *plain = 73;
        let replacement = allocator.realloc(plain, layout, 64);
        let (live, live_layout) = if replacement.is_null() {
            (plain, layout)
        } else {
            (replacement, Layout::from_size_align(64, 8).unwrap())
        };
        let observation = (replacement.is_null(), *live, *zeroed);
        allocator.dealloc(live, live_layout);
        allocator.dealloc(zeroed, layout);
        observation
    });
    assert_eq!(observation, (true, 73, 0));
    assert_eq!((stats.attempts, stats.injected_failures), (3, 1));
    assert_eq!(
        (stats.allocations, stats.reallocations, stats.deallocations),
        (2, 1, 2)
    );
    assert_eq!((stats.allocated_bytes, stats.freed_bytes), (64, 64));
}

#[test]
fn unwinding_clears_the_observer_and_fault() {
    let failed = std::panic::catch_unwind(|| {
        measure_extended(Some(usize::MAX), || panic!("unit observer reset probe"));
    });
    assert!(failed.is_err());
    assert!(!ACTIVE.with(Cell::get));
    assert_eq!(FAIL_AT.with(Cell::get), None);
    let (_, stats) = measure(|| {
        let mut bytes = Vec::<u8>::new();
        bytes.try_reserve_exact(17).unwrap();
        std::hint::black_box(&bytes);
    });
    assert_eq!((stats.attempts, stats.injected_failures), (1, 0));
}
