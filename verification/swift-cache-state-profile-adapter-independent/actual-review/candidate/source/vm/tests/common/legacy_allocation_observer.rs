//! Size/fault observations for the original single synchronous test lane.
//! The reviewed observer owns pointer lifetimes; this adapter adds only the
//! legacy requested-size and allocation-boundary cancellation measurements.
#![allow(dead_code)]
#[path = "allocation_observer.rs"]
mod ownership;
use mixer_vm::Cancellation;
use std::alloc::{GlobalAlloc, Layout};
use std::cell::Cell;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};

pub use ownership::{LIVE, MAX_SLOTS, PEAK};
pub static CALLS: AtomicUsize = AtomicUsize::new(0);
pub static REALLOCS: AtomicUsize = AtomicUsize::new(0);
pub static LARGEST: AtomicUsize = AtomicUsize::new(0);
pub static SOURCE_HITS: AtomicUsize = AtomicUsize::new(0);
pub static SIZES: [AtomicUsize; 128] = [const { AtomicUsize::new(0) }; 128];
pub static REACHED: AtomicBool = AtomicBool::new(false);
pub static RELEASE: AtomicBool = AtomicBool::new(false);
thread_local! {
    static ACTIVE: Cell<bool> = const { Cell::new(false) };
    static FAIL: Cell<usize> = const { Cell::new(0) };
    static FAIL_SIZE: Cell<usize> = const { Cell::new(0) };
    static SOURCE_SIZE: Cell<usize> = const { Cell::new(0) };
    static GATE_CALL: Cell<usize> = const { Cell::new(0) };
}
fn active() -> bool {
    ACTIVE.try_with(Cell::get).unwrap_or(false)
}
fn permit(size: usize) -> bool {
    if !active() {
        return true;
    }
    let index = CALLS.fetch_add(1, SeqCst);
    if index < SIZES.len() {
        SIZES[index].store(size, SeqCst);
    }
    LARGEST.fetch_max(size, SeqCst);
    if size == SOURCE_SIZE.with(Cell::get) {
        SOURCE_HITS.fetch_add(1, SeqCst);
    }
    let call = index + 1;
    if call == GATE_CALL.with(Cell::get) {
        REACHED.store(true, SeqCst);
        while !RELEASE.load(SeqCst) {
            std::hint::spin_loop();
        }
    }
    call != FAIL.with(Cell::get) && size != FAIL_SIZE.with(Cell::get)
}

pub struct Observed;
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !permit(layout.size()) {
            return std::ptr::null_mut();
        }
        unsafe { ownership::Observed.alloc(layout) }
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !permit(layout.size()) {
            return std::ptr::null_mut();
        }
        unsafe { ownership::Observed.alloc_zeroed(layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if active() {
            REALLOCS.fetch_add(1, SeqCst);
        }
        if !permit(bytes) {
            return std::ptr::null_mut();
        }
        unsafe { ownership::Observed.realloc(pointer, layout, bytes) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { ownership::Observed.dealloc(pointer, layout) };
    }
}

pub struct Lane {
    // Ownership ends after the caller's later-declared fixtures are destroyed.
    _ownership: ownership::Ownership,
    cancellation: Cancellation,
    _background: ownership::Background,
}
impl Lane {
    pub fn new() -> Self {
        // Neither the noise worker nor the adapter's retained token belongs to
        // the measured lane. The token is cloned without allocation per interval.
        let background = ownership::Background::new();
        let cancellation = Cancellation::default();
        let ownership = ownership::Ownership::new();
        background.check_observer();
        let lane = Self {
            _ownership: ownership,
            cancellation,
            _background: background,
        };
        lane.check_adapter();
        lane
    }
    pub fn begin(&self, source: usize, fail: usize) -> Operation<'_> {
        assert!(!active());
        CALLS.store(0, SeqCst);
        REALLOCS.store(0, SeqCst);
        LARGEST.store(0, SeqCst);
        SOURCE_HITS.store(0, SeqCst);
        SOURCE_SIZE.with(|value| value.set(source));
        FAIL.with(|value| value.set(fail));
        FAIL_SIZE.with(|value| value.set(0));
        ACTIVE.with(|value| value.set(true));
        let baseline = LIVE.load(SeqCst);
        let operation = ownership::begin(0, 0, &self.cancellation);
        Operation {
            baseline,
            _ownership: operation,
        }
    }
    fn check_adapter(&self) {
        static COMMAND: AtomicBool = AtomicBool::new(false);
        static READY: AtomicBool = AtomicBool::new(false);
        static DONE: AtomicBool = AtomicBool::new(false);
        static STOP: AtomicBool = AtomicBool::new(false);
        // Construct before arming a fault. The worker makes all three request
        // kinds through this adapter while the foreground ordinal is armed.
        let worker = std::thread::spawn(|| {
            READY.store(true, SeqCst);
            while !COMMAND.load(SeqCst) {
                std::hint::spin_loop();
            }
            let allocator: &dyn GlobalAlloc = std::hint::black_box(&Observed);
            let layout = Layout::from_size_align(900, 1).unwrap();
            let plain = unsafe { allocator.alloc(layout) };
            assert!(!plain.is_null());
            unsafe { allocator.dealloc(plain, layout) };
            let pointer = unsafe { allocator.alloc_zeroed(layout) };
            assert!(!pointer.is_null());
            let next = unsafe { allocator.realloc(pointer, layout, 1800) };
            assert!(!next.is_null());
            unsafe { allocator.dealloc(next, Layout::from_size_align(1800, 1).unwrap()) };
            DONE.store(true, SeqCst);
            // Keep the thread's own lifetime stable through the foreground
            // live/peak assertions; join-packet destruction is outside them.
            while !STOP.load(SeqCst) {
                std::hint::spin_loop();
            }
        });
        while !READY.load(SeqCst) {
            std::hint::spin_loop();
        }
        let operation = self.begin(64, 1);
        COMMAND.store(true, SeqCst);
        while !DONE.load(SeqCst) {
            std::hint::spin_loop();
        }
        assert_eq!(CALLS.load(SeqCst), 0);
        assert_eq!(REALLOCS.load(SeqCst), 0);
        assert_eq!(SOURCE_HITS.load(SeqCst), 0);
        assert_eq!(LARGEST.load(SeqCst), 0);
        assert_eq!(LIVE.load(SeqCst), operation.baseline());
        assert_eq!(PEAK.load(SeqCst), operation.baseline());
        let allocator: &dyn GlobalAlloc = std::hint::black_box(&Observed);
        let pointer = unsafe { allocator.alloc(Layout::from_size_align(64, 8).unwrap()) };
        operation.finish();
        assert!(pointer.is_null());
        assert_eq!(CALLS.load(SeqCst), 1);
        assert_eq!(SOURCE_HITS.load(SeqCst), 1);
        assert_eq!(LARGEST.load(SeqCst), 64);
        STOP.store(true, SeqCst);
        worker.join().unwrap();
        drop(self.begin(0, 1));
        let pointer = unsafe { allocator.alloc(Layout::from_size_align(64, 8).unwrap()) };
        assert!(!pointer.is_null());
        unsafe { allocator.dealloc(pointer, Layout::from_size_align(64, 8).unwrap()) };
    }
}
pub fn fail_size(bytes: usize) {
    assert!(active());
    FAIL_SIZE.with(|value| value.set(bytes));
}
pub fn gate(ordinal: usize) {
    assert!(!active());
    GATE_CALL.with(|value| value.set(ordinal));
    REACHED.store(false, SeqCst);
    RELEASE.store(false, SeqCst);
}
pub fn ungate() {
    assert!(!active());
    GATE_CALL.with(|value| value.set(0));
}
#[must_use]
pub struct Operation<'a> {
    baseline: usize,
    _ownership: ownership::Operation<'a>,
}
fn disarm() {
    ACTIVE.with(|value| value.set(false));
    FAIL.with(|value| value.set(0));
    FAIL_SIZE.with(|value| value.set(0));
    GATE_CALL.with(|value| value.set(0));
}
impl Drop for Lane {
    fn drop(&mut self) {
        disarm();
    }
}
impl Operation<'_> {
    pub fn baseline(&self) -> usize {
        self.baseline
    }
    pub fn finish(self) -> usize {
        self.baseline
    }
}
impl Drop for Operation<'_> {
    fn drop(&mut self) {
        disarm();
    }
}
