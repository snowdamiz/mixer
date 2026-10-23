//! Unit-only synchronous allocator observations; never product admission input.
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;

#[derive(Clone, Copy, Debug, Default)]
pub(super) struct AllocationStats {
    pub allocations: usize,
    pub reallocations: usize,
    pub deallocations: usize,
    pub allocated_bytes: usize,
    pub freed_bytes: usize,
    pub last_size: usize,
    pub last_align: usize,
}
thread_local! {
    static ACTIVE: Cell<bool> = const { Cell::new(false) };
    static STATS: Cell<AllocationStats> = const { Cell::new(AllocationStats {
        allocations: 0, reallocations: 0, deallocations: 0,
        allocated_bytes: 0, freed_bytes: 0, last_size: 0, last_align: 0,
    }) };
}
fn observe(operation: u8, layout: Layout) {
    if ACTIVE.try_with(Cell::get).unwrap_or(false) {
        STATS.with(|slot| {
            let mut stats = slot.get();
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
        });
    }
}
struct Observed;
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        observe(0, layout);
        unsafe { System.alloc(layout) }
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        observe(0, layout);
        unsafe { System.alloc_zeroed(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        observe(2, layout);
        unsafe { System.dealloc(pointer, layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        observe(1, layout);
        unsafe { System.realloc(pointer, layout, bytes) }
    }
}
#[global_allocator]
static ALLOCATOR: Observed = Observed;

/// Captures requests on this thread only. Deallocations may concern storage
/// allocated before this interval; this is not a general live-pointer ledger.
pub(super) fn measure<T>(body: impl FnOnce() -> T) -> (T, AllocationStats) {
    struct Reset;
    impl Drop for Reset {
        fn drop(&mut self) {
            ACTIVE.with(|active| active.set(false));
        }
    }
    assert!(!ACTIVE.with(Cell::get));
    STATS.with(|stats| stats.set(AllocationStats::default()));
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
