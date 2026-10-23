#![cfg(feature = "experimental-span-execution")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type, Value};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicPtr, AtomicUsize, Ordering::SeqCst};

struct Allocator;
static TRACK: AtomicBool = AtomicBool::new(false);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static HIGH: AtomicUsize = AtomicUsize::new(0);
static REQUESTS: AtomicUsize = AtomicUsize::new(0);
static RESIZES: AtomicUsize = AtomicUsize::new(0);
static DENY: AtomicUsize = AtomicUsize::new(0);
static STOP: AtomicUsize = AtomicUsize::new(0);
static TOKEN: AtomicPtr<Cancellation> = AtomicPtr::new(std::ptr::null_mut());
fn admit() -> bool {
    if !TRACK.load(SeqCst) {
        return true;
    }
    let n = REQUESTS.fetch_add(1, SeqCst) + 1;
    if n == STOP.load(SeqCst) {
        let token = TOKEN.load(SeqCst);
        if !token.is_null() {
            // The only test keeps this token alive until tracking ends.
            unsafe {
                (&*token).cancel();
            }
        }
    }
    n != DENY.load(SeqCst)
}
fn account(bytes: usize) {
    let next = LIVE.fetch_add(bytes, SeqCst) + bytes;
    if TRACK.load(SeqCst) {
        HIGH.fetch_max(next, SeqCst);
    }
}
unsafe impl GlobalAlloc for Allocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !admit() {
            return std::ptr::null_mut();
        }
        let p = System.alloc(layout);
        if !p.is_null() {
            account(layout.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !admit() {
            return std::ptr::null_mut();
        }
        let p = System.alloc_zeroed(layout);
        if !p.is_null() {
            account(layout.size());
        }
        p
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if TRACK.load(SeqCst) {
            RESIZES.fetch_add(1, SeqCst);
        }
        if !admit() {
            return std::ptr::null_mut();
        }
        let p = System.realloc(pointer, layout, bytes);
        if !p.is_null() {
            LIVE.fetch_sub(layout.size(), SeqCst);
            account(bytes);
        }
        p
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        System.dealloc(pointer, layout);
        LIVE.fetch_sub(layout.size(), SeqCst);
    }
}
#[global_allocator]
static ALLOCATOR: Allocator = Allocator;
fn start(deny: usize, stop: usize, token: &Cancellation) -> usize {
    let before = LIVE.load(SeqCst);
    HIGH.store(before, SeqCst);
    REQUESTS.store(0, SeqCst);
    RESIZES.store(0, SeqCst);
    DENY.store(deny, SeqCst);
    STOP.store(stop, SeqCst);
    TOKEN.store(std::ptr::from_ref(token).cast_mut(), SeqCst);
    TRACK.store(true, SeqCst);
    before
}
fn end() {
    TRACK.store(false, SeqCst);
    TOKEN.store(std::ptr::null_mut(), SeqCst);
}
fn cache(bytes: &[u8]) -> FunctionCache {
    let token = Cancellation::default();
    let limits = Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    };
    let proof = validate_spans(bytes, limits, ValidationBudget::default(), &token).unwrap();
    FunctionCache::new(proof, CacheBudget::default(), &token).unwrap()
}
fn module() -> Vec<u8> {
    let mut spec = Spec::one(
        vec![],
        Some(Type::I32),
        vec![
            0x02, 0x40, 0x41, 0, 0x0e, 1, 0, 0, 0x0b, 0x41, 1, 0x40, 0, 0x0b,
        ],
    );
    spec.functions[0].locals = vec![Type::I64];
    spec.memory = Some((1, 3));
    spec.table = Some((1, 1));
    spec.globals = vec![(Value::I32(3), false)];
    spec.bytes()
}
fn clean(span: &SpanInstance) {
    let u = span.usage();
    assert_eq!(
        (u.frames, u.live_values, u.live_controls, u.active_pins),
        (0, 0, 0, 0)
    );
    assert_eq!(span.cache_usage().active_pins, 0);
}
#[test]
fn every_allocator_failure_and_cancel_ordinal_is_fallible_and_cleans_owned_pins() {
    let bytes = module();
    let token = Cancellation::default();
    let proof = cache(&bytes);
    let baseline = start(0, 0, &token);
    let result = SpanInstance::new(proof, ExecutionBudget::default(), token.clone());
    end();
    let constructor_allocations = REQUESTS.load(SeqCst);
    let constructor_peak = HIGH.load(SeqCst) - baseline;
    let mut span = result.unwrap();
    assert_eq!(constructor_allocations, 6);
    assert_eq!(RESIZES.load(SeqCst), 0);
    assert!(constructor_peak <= span.usage().peak_state_reserved);
    let baseline = start(0, 0, &token);
    let result = span.invoke("run", &[]);
    end();
    assert_eq!(result.unwrap(), Some(Value::I32(1)));
    let invoke_allocations = REQUESTS.load(SeqCst);
    let invoke_peak = HIGH.load(SeqCst) - baseline;
    assert_eq!(invoke_allocations, 4);
    assert_eq!(RESIZES.load(SeqCst), 0);
    clean(&span);
    assert!(
        constructor_peak + invoke_peak
            <= span.usage().peak_state_reserved + span.cache_usage().peak_cache_reserved
    );
    // Warm-cache dispatch, successful returns and a declared-limit grow denial
    // are allocation-free, even with the allocator refusing its first request.
    assert_eq!(span.invoke("run", &[]).unwrap(), Some(Value::I32(2)));
    start(1, 0, &token);
    let third = span.invoke("run", &[]);
    end();
    assert_eq!(third.unwrap(), Some(Value::I32(-1)));
    assert_eq!(REQUESTS.load(SeqCst), 0);
    drop(span);
    for ordinal in 1..=constructor_allocations {
        let token = Cancellation::default();
        let before = LIVE.load(SeqCst);
        let proof = cache(&bytes);
        start(ordinal, 0, &token);
        let result = SpanInstance::new(proof, ExecutionBudget::default(), token.clone());
        end();
        let error = result.err().unwrap();
        assert_eq!(
            error.kind,
            ExecutionFailureKind::AllocationFailure,
            "constructor allocation {ordinal}"
        );
        assert_eq!(error.usage.state_reserved, 0);
        assert_eq!(LIVE.load(SeqCst), before);
        let token = Cancellation::default();
        let before = LIVE.load(SeqCst);
        let proof = cache(&bytes);
        start(0, ordinal, &token);
        let result = SpanInstance::new(proof, ExecutionBudget::default(), token.clone());
        end();
        assert_eq!(result.err().unwrap().kind, ExecutionFailureKind::Cancelled);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    for ordinal in 1..=invoke_allocations {
        let token = Cancellation::default();
        let mut span =
            SpanInstance::new(cache(&bytes), ExecutionBudget::default(), token.clone()).unwrap();
        let before = LIVE.load(SeqCst);
        start(ordinal, 0, &token);
        let result = span.invoke("run", &[]);
        end();
        let error = result.unwrap_err();
        assert!(matches!(
            error.kind,
            ExecutionFailureKind::Cache | ExecutionFailureKind::AllocationFailure
        ));
        clean(&span);
        assert_eq!(span.memory().len(), 65536);
        // A failed cache decode releases all temporary allocations. A growth
        // failure may leave one retained decoded entry, still explicitly counted.
        assert!(LIVE.load(SeqCst) <= before + span.cache_usage().resident_bytes);
        start(1, 0, &token);
        let repeated = span.invoke("run", &[]);
        end();
        assert_eq!(repeated, Err(error));
        assert_eq!(REQUESTS.load(SeqCst), 0);
        let token = Cancellation::default();
        let mut span =
            SpanInstance::new(cache(&bytes), ExecutionBudget::default(), token.clone()).unwrap();
        start(0, ordinal, &token);
        let result = span.invoke("run", &[]);
        end();
        let error = result.unwrap_err();
        assert!(
            error.kind == ExecutionFailureKind::Cancelled
                || error
                    .cache_failure
                    .is_some_and(|c| c.kind == CacheFailureKind::Cancelled)
        );
        clean(&span);
    }
    println!("owned allocation observations: constructor_allocations={constructor_allocations} initial_invoke_allocations={invoke_allocations} constructor_requested_peak={constructor_peak} invoke_requested_peak={invoke_peak}; every failure/cancellation ordinal cleaned");
}
