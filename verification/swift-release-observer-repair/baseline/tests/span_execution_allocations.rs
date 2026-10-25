#![cfg(feature = "experimental-span-execution")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type, Value};
#[path = "common/allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{
    begin as start, Background, Observed, Ownership, CALLS as REQUESTS, LIVE, MAX_SLOTS,
    PEAK as HIGH, REALLOCATIONS as RESIZES,
};
use std::sync::atomic::Ordering::SeqCst;

#[global_allocator]
static ALLOCATOR: Observed = Observed;
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
    let background = Background::new();
    let _ownership = Ownership::new();
    background.check_observer();
    let bytes = module();
    let token = Cancellation::default();
    let proof = cache(&bytes);
    let operation = start(0, 0, &token);
    let result = SpanInstance::new(proof, ExecutionBudget::default(), token.clone());
    let baseline = operation.finish();
    let constructor_allocations = REQUESTS.load(SeqCst);
    let constructor_peak = HIGH.load(SeqCst) - baseline;
    let mut span = result.unwrap();
    assert_eq!(constructor_allocations, 6);
    assert_eq!(RESIZES.load(SeqCst), 0);
    assert!(constructor_peak <= span.usage().peak_state_reserved);
    let operation = start(0, 0, &token);
    let result = span.invoke("run", &[]);
    let baseline = operation.finish();
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
    let operation = start(1, 0, &token);
    let third = span.invoke("run", &[]);
    operation.finish();
    assert_eq!(third.unwrap(), Some(Value::I32(-1)));
    assert_eq!(REQUESTS.load(SeqCst), 0);
    drop(span);
    for ordinal in 1..=constructor_allocations {
        let token = Cancellation::default();
        let before = LIVE.load(SeqCst);
        let proof = cache(&bytes);
        let operation = start(ordinal, 0, &token);
        let result = SpanInstance::new(proof, ExecutionBudget::default(), token.clone());
        operation.finish();
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
        let operation = start(0, ordinal, &token);
        let result = SpanInstance::new(proof, ExecutionBudget::default(), token.clone());
        operation.finish();
        assert_eq!(result.err().unwrap().kind, ExecutionFailureKind::Cancelled);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    for ordinal in 1..=invoke_allocations {
        let token = Cancellation::default();
        let mut span =
            SpanInstance::new(cache(&bytes), ExecutionBudget::default(), token.clone()).unwrap();
        let before = LIVE.load(SeqCst);
        let operation = start(ordinal, 0, &token);
        let result = span.invoke("run", &[]);
        operation.finish();
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
        let operation = start(1, 0, &token);
        let repeated = span.invoke("run", &[]);
        operation.finish();
        assert_eq!(repeated, Err(error));
        assert_eq!(REQUESTS.load(SeqCst), 0);
        let token = Cancellation::default();
        let mut span =
            SpanInstance::new(cache(&bytes), ExecutionBudget::default(), token.clone()).unwrap();
        let operation = start(0, ordinal, &token);
        let result = span.invoke("run", &[]);
        operation.finish();
        let error = result.unwrap_err();
        assert!(
            error.kind == ExecutionFailureKind::Cancelled
                || error
                    .cache_failure
                    .is_some_and(|c| c.kind == CacheFailureKind::Cancelled)
        );
        clean(&span);
    }
    println!(
        "observer maximum ownership slots={} capacity=4096 background_noise={}",
        MAX_SLOTS.load(SeqCst),
        std::env::var_os("MIXER_ALLOCATOR_NOISE").is_some()
    );
    println!("owned allocation observations: constructor_allocations={constructor_allocations} initial_invoke_allocations={invoke_allocations} constructor_requested_peak={constructor_peak} invoke_requested_peak={invoke_peak}; every failure/cancellation ordinal cleaned");
}
