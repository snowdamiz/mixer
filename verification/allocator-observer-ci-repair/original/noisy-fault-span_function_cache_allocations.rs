#![cfg(feature = "experimental-function-cache")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, validate_spans, ValidatedSpans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Type};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicPtr, AtomicUsize, Ordering::SeqCst};

// One test in its own process: gate allocation failures and cancellation without
// allocator hooks or test-only branches in product code.
struct Observed;
static ACTIVE: AtomicBool = AtomicBool::new(false);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static REALLOCATIONS: AtomicUsize = AtomicUsize::new(0);
static FAIL: AtomicUsize = AtomicUsize::new(0);
static CANCEL_AT: AtomicUsize = AtomicUsize::new(0);
static CANCEL: AtomicPtr<Cancellation> = AtomicPtr::new(std::ptr::null_mut());
fn request() -> bool {
    if !ACTIVE.load(SeqCst) {
        return true;
    }
    let call = CALLS.fetch_add(1, SeqCst) + 1;
    if call == CANCEL_AT.load(SeqCst) {
        let pointer = CANCEL.load(SeqCst);
        if !pointer.is_null() {
            // The single test publishes a borrowed stable cancellation flag only
            // for this synchronous allocation interval and clears it afterwards.
            unsafe {
                (&*pointer).cancel();
            }
        }
    }
    call != FAIL.load(SeqCst)
}
fn added(bytes: usize) {
    let live = LIVE.fetch_add(bytes, SeqCst) + bytes;
    if ACTIVE.load(SeqCst) {
        PEAK.fetch_max(live, SeqCst);
    }
}
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let pointer = System.alloc(layout);
        if !pointer.is_null() {
            added(layout.size());
        }
        pointer
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let pointer = System.alloc_zeroed(layout);
        if !pointer.is_null() {
            added(layout.size());
        }
        pointer
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        System.dealloc(pointer, layout);
        LIVE.fetch_sub(layout.size(), SeqCst);
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if ACTIVE.load(SeqCst) {
            REALLOCATIONS.fetch_add(1, SeqCst);
        }
        if !request() {
            return std::ptr::null_mut();
        }
        let next = System.realloc(pointer, layout, bytes);
        if !next.is_null() {
            LIVE.fetch_sub(layout.size(), SeqCst);
            added(bytes);
        }
        next
    }
}
#[global_allocator]
static ALLOCATOR: Observed = Observed;
fn begin(fail: usize, cancel_at: usize, cancellation: &Cancellation) -> usize {
    let baseline = LIVE.load(SeqCst);
    PEAK.store(baseline, SeqCst);
    CALLS.store(0, SeqCst);
    REALLOCATIONS.store(0, SeqCst);
    FAIL.store(fail, SeqCst);
    CANCEL_AT.store(cancel_at, SeqCst);
    CANCEL.store(std::ptr::from_ref(cancellation).cast_mut(), SeqCst);
    ACTIVE.store(true, SeqCst);
    baseline
}
fn finish() {
    ACTIVE.store(false, SeqCst);
    FAIL.store(0, SeqCst);
    CANCEL_AT.store(0, SeqCst);
    CANCEL.store(std::ptr::null_mut(), SeqCst);
}
fn proof(bytes: &[u8]) -> ValidatedSpans {
    validate_spans(
        bytes,
        Limits::default(),
        ValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn bytes() -> Vec<u8> {
    let mut code = vec![2, 0x40, 0x41, 0, 0x0e];
    code.extend(u32leb(1000));
    code.extend(vec![0; 1001]);
    code.extend([0x0b, 0x0b]);
    let mut spec = Spec::one(vec![], None, code);
    spec.functions[0].locals = vec![Type::I64; 77];
    spec.functions.push(Function::new(vec![], None, vec![0x0b]));
    spec.bytes()
}
fn observe(label: &str, bytes: &[u8]) {
    let cancel = Cancellation::default();
    let before = LIVE.load(SeqCst);
    let spans = proof(bytes);
    let proof_requested = LIVE.load(SeqCst) - before;
    let baseline = begin(0, 0, &cancel);
    let mut cache = FunctionCache::new(spans, CacheBudget::default(), &cancel).unwrap();
    let pin = cache.pin(0, &cancel).unwrap();
    finish();
    let peak = PEAK.load(SeqCst) - baseline;
    let calls = CALLS.load(SeqCst);
    let usage = cache.usage();
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    assert!(peak <= usage.peak_cache_reserved);
    assert!(proof_requested + peak <= usage.peak_total_reserved);
    assert_eq!(usage.peak_construction_bytes, usage.resident_bytes);
    cache.release(pin).unwrap();
    drop(cache);
    assert_eq!(LIVE.load(SeqCst), before);
    println!("cache maximum {label}: source={} requested_cache_peak={peak} requested_retained_proof={proof_requested} allocations={calls} resident={} cache_reserved_peak={} total_reserved_peak={} work={}", bytes.len(), usage.resident_bytes, usage.peak_cache_reserved, usage.peak_total_reserved, usage.work_used);
}

// Deterministic reproduction only: independent allocation on a different thread.
static NOISE_COMMAND: AtomicUsize = AtomicUsize::new(0);
static NOISE_DONE: AtomicUsize = AtomicUsize::new(0);
static NOISE_ALLOCATED: AtomicBool = AtomicBool::new(false);
struct OriginalNoise(Option<std::thread::JoinHandle<()>>);
impl OriginalNoise {
    fn new() -> Self {
        let worker = std::thread::spawn(|| {
            let layout = Layout::from_size_align(900, 1).unwrap();
            let mut held = std::ptr::null_mut();
            NOISE_DONE.store(1, SeqCst);
            loop {
                match NOISE_COMMAND.load(SeqCst) {
                    1 => {
                        held = unsafe { std::alloc::alloc(layout) };
                        NOISE_ALLOCATED.store(!held.is_null(), SeqCst);
                        NOISE_DONE.store(2, SeqCst);
                        while NOISE_COMMAND.load(SeqCst) == 1 {
                            std::hint::spin_loop();
                        }
                    }
                    2 => {
                        if !held.is_null() {
                            unsafe { std::alloc::dealloc(held, layout) };
                        }
                        return;
                    }
                    _ => std::hint::spin_loop(),
                }
            }
        });
        while NOISE_DONE.load(SeqCst) != 1 {
            std::hint::spin_loop();
        }
        Self(Some(worker))
    }
    fn allocate(&self) {
        NOISE_COMMAND.store(1, SeqCst);
        while NOISE_DONE.load(SeqCst) != 2 {
            std::hint::spin_loop();
        }
    }
}
impl Drop for OriginalNoise {
    fn drop(&mut self) {
        NOISE_COMMAND.store(2, SeqCst);
        self.0.take().unwrap().join().unwrap();
    }
}

#[test]
fn every_allocation_ordinal_cancellation_and_requested_peak_cleanup() {
    let noise = OriginalNoise::new();
    let bytes = bytes();
    let cancel = Cancellation::default();
    let before_proof = LIVE.load(SeqCst);
    let spans = proof(&bytes);
    let baseline = begin(0, 0, &cancel);
    let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
    finish();
    let constructor_calls = CALLS.load(SeqCst);
    let mut cache = result.unwrap();
    assert_eq!(constructor_calls, 2);
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    let constructor_peak = PEAK.load(SeqCst) - baseline;
    assert!(constructor_peak <= cache.usage().peak_cache_reserved);
    let baseline = begin(0, 0, &cancel);
    let result = cache.pin(0, &cancel);
    finish();
    let decode_calls = CALLS.load(SeqCst);
    let requested_peak = PEAK.load(SeqCst) - baseline;
    let pin = result.unwrap();
    assert_eq!(decode_calls, 3);
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    assert_eq!(requested_peak, cache.usage().resident_bytes);
    assert!(constructor_peak + requested_peak <= cache.usage().peak_cache_reserved);
    let usage = cache.usage();
    let baseline = begin(1, 0, &cancel);
    let hit = cache.pin(0, &cancel);
    finish();
    let hit = hit.unwrap();
    assert_eq!(CALLS.load(SeqCst), 0);
    assert_eq!(LIVE.load(SeqCst), baseline);
    cache.release(hit).unwrap();
    cache.release(pin).unwrap();
    drop(cache);
    assert_eq!(LIVE.load(SeqCst), before_proof);
    println!("cache observation: constructor_allocations={constructor_calls} decode_allocations={decode_calls} constructor_requested_peak={constructor_peak} decode_requested_peak={requested_peak} peak_cache_reserved={} peak_total_reserved={} work={}", usage.peak_cache_reserved, usage.peak_total_reserved, usage.work_used);
    for ordinal in 1..=constructor_calls {
        let before = LIVE.load(SeqCst);
        let spans = proof(&bytes);
        begin(ordinal, 0, &cancel);
        if ordinal == 1 { noise.allocate(); }
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        finish();
        println!("original fault reproduction: background_allocated={} requested_calls={}", NOISE_ALLOCATED.load(SeqCst), CALLS.load(SeqCst));
        assert_eq!(
            result.err().unwrap().kind,
            CacheFailureKind::AllocationFailure,
            "constructor ordinal {ordinal}"
        );
        assert_eq!(LIVE.load(SeqCst), before);
    }
    for ordinal in 1..=constructor_calls {
        let before = LIVE.load(SeqCst);
        let cancel = Cancellation::default();
        let spans = proof(&bytes);
        begin(0, ordinal, &cancel);
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        finish();
        assert_eq!(
            result.err().unwrap().kind,
            CacheFailureKind::Cancelled,
            "constructor cancellation ordinal {ordinal}"
        );
        drop(cancel);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    for ordinal in 1..=decode_calls {
        let before = LIVE.load(SeqCst);
        let mut cache = FunctionCache::new(proof(&bytes), CacheBudget::default(), &cancel).unwrap();
        let baseline = begin(ordinal, 0, &cancel);
        let result = cache.pin(0, &cancel);
        finish();
        assert_eq!(
            result.unwrap_err().kind,
            CacheFailureKind::AllocationFailure,
            "decode ordinal {ordinal}"
        );
        assert_eq!(LIVE.load(SeqCst), baseline);
        assert_eq!(
            (
                cache.usage().resident_bytes,
                cache.usage().construction_bytes,
                cache.usage().active_pins
            ),
            (0, 0, 0)
        );
        let retry = cache.pin(0, &cancel).unwrap();
        cache.release(retry).unwrap();
        drop(cache);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    for ordinal in 1..=decode_calls {
        let before = LIVE.load(SeqCst);
        let cancel = Cancellation::default();
        let mut cache = FunctionCache::new(proof(&bytes), CacheBudget::default(), &cancel).unwrap();
        let baseline = begin(0, ordinal, &cancel);
        let result = cache.pin(0, &cancel);
        finish();
        assert_eq!(
            result.unwrap_err().kind,
            CacheFailureKind::Cancelled,
            "decode cancellation ordinal {ordinal}"
        );
        assert_eq!(LIVE.load(SeqCst), baseline);
        assert_eq!(
            (
                cache.usage().resident_bytes,
                cache.usage().construction_bytes,
                cache.usage().active_pins
            ),
            (0, 0, 0)
        );
        drop(cache);
        drop(cancel);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    // Failure after an eviction must release partial construction and keep
    // a separately pinned function usable, including allocation-free release.
    let mut cache = FunctionCache::new(
        proof(&bytes),
        CacheBudget {
            max_entries: 1,
            ..CacheBudget::default()
        },
        &cancel,
    )
    .unwrap();
    let old = cache.pin(1, &cancel).unwrap();
    cache.release(old).unwrap();
    begin(2, 0, &cancel);
    let failed = cache.pin(0, &cancel);
    finish();
    assert_eq!(
        failed.unwrap_err().kind,
        CacheFailureKind::AllocationFailure
    );
    assert_eq!(
        (
            cache.usage().resident_bytes,
            cache.usage().construction_bytes,
            cache.usage().evictions
        ),
        (0, 0, 1)
    );
    let pin = cache.pin(0, &cancel).unwrap();
    begin(1, 0, &cancel);
    let result = cache.release(pin);
    finish();
    result.unwrap();
    assert_eq!(CALLS.load(SeqCst), 0);
    drop(cache);
    let mut locals = Spec::one(vec![], None, vec![0x0b]);
    locals.functions[0].locals = vec![Type::I64; 4096];
    observe("4096-locals", &locals.bytes());
    let mut instructions = vec![1; 199_999];
    instructions.push(0x0b);
    observe(
        "200000-instructions",
        &Spec::one(vec![], None, instructions).bytes(),
    );
    let mut branches = vec![2, 0x40, 0x41, 0, 0x0e];
    branches.extend(u32leb(200_000));
    branches.extend(vec![0; 200_001]);
    branches.extend([0x0b, 0x0b]);
    observe(
        "200000-branch-targets",
        &Spec::one(vec![], None, branches).bytes(),
    );
    let mut controls = Vec::new();
    for _ in 0..127 {
        controls.extend([2, 0x40]);
    }
    controls.extend(vec![0x0b; 128]);
    observe("128-controls", &Spec::one(vec![], None, controls).bytes());
}
