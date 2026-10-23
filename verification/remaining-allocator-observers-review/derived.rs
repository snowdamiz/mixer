//! Independent probes of the exact retained test-only observer implementation.
#[path = "probe-support/legacy_allocation_observer.rs"]
mod observer;
use observer::{Lane, Observed, CALLS, LARGEST, LIVE, PEAK, REALLOCS, SOURCE_HITS, SIZES};
use std::alloc::{GlobalAlloc, Layout};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};
#[global_allocator]
static ALLOCATOR: Observed = Observed;
static READY: AtomicBool = AtomicBool::new(false);
static COMMAND: AtomicUsize = AtomicUsize::new(0);
static DONE: AtomicUsize = AtomicUsize::new(0);
static STOP: AtomicBool = AtomicBool::new(false);
static SUCCESS: AtomicBool = AtomicBool::new(false);
fn allocator() -> &'static dyn GlobalAlloc { std::hint::black_box(&Observed) }
fn layout(bytes: usize) -> Layout { Layout::from_size_align(bytes, 8).unwrap() }
fn wait(flag: &AtomicBool) { while !flag.load(SeqCst) { std::hint::spin_loop(); } }
fn reset_worker() {
    READY.store(false, SeqCst); COMMAND.store(0, SeqCst);
    DONE.store(0, SeqCst); STOP.store(false, SeqCst); SUCCESS.store(false, SeqCst);
}
#[test]
fn independently_check_sizes_faults_ownership_and_cancel_worker() {
    let lane = Lane::new();
    let mut checks = 0;
    macro_rules! check { ($condition:expr) => {{ checks += 1; assert!($condition, stringify!($condition)); }} }
    let initial = LIVE.load(SeqCst);
    unsafe {
        // Ownership includes ordinary preparation outside a measurement interval.
        let preparation = allocator().alloc_zeroed(layout(32));
        check!(!preparation.is_null());
        check!(LIVE.load(SeqCst) == initial + 32);
        let op = lane.begin(48, 0); let baseline = op.baseline();
        let first = allocator().alloc(layout(48));
        let grown = allocator().realloc(first, layout(48), 80);
        let zeroed = allocator().alloc_zeroed(layout(48));
        op.finish();
        check!(!grown.is_null() && !zeroed.is_null());
        check!(CALLS.load(SeqCst) == 3);
        check!(REALLOCS.load(SeqCst) == 1);
        check!(SOURCE_HITS.load(SeqCst) == 2);
        check!(LARGEST.load(SeqCst) == 80);
        check!((0..3).map(|i| SIZES[i].load(SeqCst)).eq([48, 80, 48]));
        check!(LIVE.load(SeqCst) == baseline + 128);
        check!(PEAK.load(SeqCst) == baseline + 128);
        check!((0..48).all(|i| *zeroed.add(i) == 0));
        allocator().dealloc(grown, layout(80)); allocator().dealloc(zeroed, layout(48));
        allocator().dealloc(preparation, layout(32));
        check!(LIVE.load(SeqCst) == initial);

        // Refused realloc preserves both the old allocation and its ownership.
        let old = allocator().alloc(layout(64)); *old = 0xa5;
        let op = lane.begin(64, 2); let baseline = op.baseline();
        let one = allocator().alloc_zeroed(layout(64));
        let denied = allocator().realloc(old, layout(64), 128);
        let three = allocator().alloc(layout(32));
        op.finish();
        check!(!one.is_null() && denied.is_null() && !three.is_null());
        check!(*old == 0xa5);
        check!(CALLS.load(SeqCst) == 3 && REALLOCS.load(SeqCst) == 1);
        check!(SOURCE_HITS.load(SeqCst) == 1 && LARGEST.load(SeqCst) == 128);
        check!((0..3).map(|i| SIZES[i].load(SeqCst)).eq([64, 128, 32]));
        check!(LIVE.load(SeqCst) == baseline + 96);
        allocator().dealloc(old, layout(64)); allocator().dealloc(one, layout(64));
        allocator().dealloc(three, layout(32));
        check!(LIVE.load(SeqCst) == initial);

        let op = lane.begin(80, 0); let baseline = op.baseline(); observer::fail_size(80);
        let denied_plain = allocator().alloc(layout(80));
        let denied_zero = allocator().alloc_zeroed(layout(80));
        let kept = allocator().alloc(layout(64)); *kept = 0x5a;
        let denied_resize = allocator().realloc(kept, layout(64), 80);
        op.finish();
        check!(denied_plain.is_null() && denied_zero.is_null() && denied_resize.is_null());
        check!(*kept == 0x5a);
        check!(CALLS.load(SeqCst) == 4 && REALLOCS.load(SeqCst) == 1);
        check!(SOURCE_HITS.load(SeqCst) == 3 && LARGEST.load(SeqCst) == 80);
        check!(LIVE.load(SeqCst) == baseline + 64);
        allocator().dealloc(kept, layout(64)); check!(LIVE.load(SeqCst) == initial);

        // Dropping the guard also clears a never-reached cancellation gate.
        observer::gate(1); drop(lane.begin(64, 1));
        let resumed = allocator().alloc(layout(64));
        check!(!resumed.is_null() && !observer::REACHED.load(SeqCst));
        check!(CALLS.load(SeqCst) == 0);
        allocator().dealloc(resumed, layout(64)); check!(LIVE.load(SeqCst) == initial);

        // Owned pointers remain counted when another thread resizes/frees them;
        // that thread's unrelated allocations do not consume foreground faults.
        reset_worker(); let transferred = allocator().alloc(layout(64)) as usize;
        let worker = std::thread::spawn(move || {
            READY.store(true, SeqCst);
            while COMMAND.load(SeqCst) != 1 { std::hint::spin_loop(); }
            let next = allocator().realloc(transferred as *mut u8, layout(64), 128);
            let noise = allocator().alloc(layout(900));
            SUCCESS.store(!next.is_null() && !noise.is_null(), SeqCst);
            DONE.store(1, SeqCst);
            while COMMAND.load(SeqCst) != 2 { std::hint::spin_loop(); }
            allocator().dealloc(next, layout(128)); allocator().dealloc(noise, layout(900));
            DONE.store(2, SeqCst); wait(&STOP);
        });
        wait(&READY); let op = lane.begin(900, 1); let baseline = op.baseline();
        observer::fail_size(900); COMMAND.store(1, SeqCst);
        while DONE.load(SeqCst) != 1 { std::hint::spin_loop(); }
        let after_grow = LIVE.load(SeqCst); let peak = PEAK.load(SeqCst);
        COMMAND.store(2, SeqCst); while DONE.load(SeqCst) != 2 { std::hint::spin_loop(); }
        let after_free = LIVE.load(SeqCst);
        let refused = allocator().alloc(layout(32)); op.finish();
        check!(SUCCESS.load(SeqCst));
        check!(after_grow == baseline + 64 && peak == baseline + 64);
        check!(after_free == baseline - 64);
        check!(refused.is_null() && CALLS.load(SeqCst) == 1);
        check!(REALLOCS.load(SeqCst) == 0 && SOURCE_HITS.load(SeqCst) == 0);
        check!(SIZES[0].load(SeqCst) == 32 && LARGEST.load(SeqCst) == 32);
        STOP.store(true, SeqCst); worker.join().unwrap(); check!(LIVE.load(SeqCst) == initial);

        // The real cancellation helper does allocator work while a gate is armed.
        // Only the foreground request reaches the gate and returns after cancel.
        reset_worker(); let cancellation = mixer_vm::Cancellation::default();
        let canceller = cancellation.clone();
        let worker = std::thread::spawn(move || {
            READY.store(true, SeqCst);
            while COMMAND.load(SeqCst) != 1 { std::hint::spin_loop(); }
            let noise = allocator().alloc(layout(900));
            let zero = allocator().alloc_zeroed(layout(64));
            let resized = allocator().realloc(zero, layout(64), 128);
            SUCCESS.store(!noise.is_null() && !resized.is_null(), SeqCst);
            allocator().dealloc(noise, layout(900)); allocator().dealloc(resized, layout(128));
            DONE.store(1, SeqCst); wait(&observer::REACHED);
            canceller.cancel(); observer::RELEASE.store(true, SeqCst); wait(&STOP);
        });
        wait(&READY); observer::gate(1); let op = lane.begin(64, 0);
        let baseline = op.baseline(); observer::fail_size(900); COMMAND.store(1, SeqCst);
        while DONE.load(SeqCst) != 1 { std::hint::spin_loop(); }
        let untouched = (CALLS.load(SeqCst), REALLOCS.load(SeqCst), SOURCE_HITS.load(SeqCst), LARGEST.load(SeqCst), LIVE.load(SeqCst), PEAK.load(SeqCst), observer::REACHED.load(SeqCst));
        let foreground = allocator().alloc(layout(64)); op.finish();
        check!(SUCCESS.load(SeqCst));
        check!(untouched == (0, 0, 0, 0, baseline, baseline, false));
        check!(!foreground.is_null() && cancellation.is_cancelled());
        check!(observer::REACHED.load(SeqCst) && observer::RELEASE.load(SeqCst));
        check!(CALLS.load(SeqCst) == 1 && SOURCE_HITS.load(SeqCst) == 1);
        check!(REALLOCS.load(SeqCst) == 0 && LARGEST.load(SeqCst) == 64);
        check!(LIVE.load(SeqCst) == baseline + 64 && PEAK.load(SeqCst) == baseline + 64);
        allocator().dealloc(foreground, layout(64)); STOP.store(true, SeqCst);
        worker.join().unwrap(); drop(cancellation); check!(LIVE.load(SeqCst) == initial);
    }
    println!("independent observer checks={checks}; ownership, attempted sizes, ordinal/size refusal, guard drop, cross-thread realloc/free and cancellation-helper isolation");
}
