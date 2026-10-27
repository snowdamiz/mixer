#![cfg(feature = "experimental-function-cache")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, validate_spans, ValidatedSpans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Type};
#[path = "common/allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{
    begin, Background, Observed, Ownership, CALLS, LIVE, MAX_SLOTS, PEAK, REALLOCATIONS,
};
use std::sync::atomic::Ordering::SeqCst;

#[global_allocator]
static ALLOCATOR: Observed = Observed;
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
    let operation = begin(0, 0, &cancel);
    let mut cache = FunctionCache::new(spans, CacheBudget::default(), &cancel).unwrap();
    let pin = cache.pin(0, &cancel).unwrap();
    let baseline = operation.finish();
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
#[test]
fn every_allocation_ordinal_cancellation_and_requested_peak_cleanup() {
    let background = Background::new();
    let _ownership = Ownership::new();
    background.check_observer();
    let bytes = bytes();
    let cancel = Cancellation::default();
    let before_proof = LIVE.load(SeqCst);
    let spans = proof(&bytes);
    let operation = begin(0, 0, &cancel);
    let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
    let baseline = operation.finish();
    let constructor_calls = CALLS.load(SeqCst);
    let mut cache = result.unwrap();
    assert_eq!(constructor_calls, 2);
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    let constructor_peak = PEAK.load(SeqCst) - baseline;
    assert!(constructor_peak <= cache.usage().peak_cache_reserved);
    let operation = begin(0, 0, &cancel);
    let result = cache.pin(0, &cancel);
    let baseline = operation.finish();
    let decode_calls = CALLS.load(SeqCst);
    let requested_peak = PEAK.load(SeqCst) - baseline;
    let pin = result.unwrap();
    assert_eq!(decode_calls, 3);
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    assert_eq!(requested_peak, cache.usage().resident_bytes);
    assert!(constructor_peak + requested_peak <= cache.usage().peak_cache_reserved);
    let usage = cache.usage();
    let operation = begin(1, 0, &cancel);
    let hit = cache.pin(0, &cancel);
    let baseline = operation.finish();
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
        let operation = begin(ordinal, 0, &cancel);
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        operation.finish();
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
        let operation = begin(0, ordinal, &cancel);
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        operation.finish();
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
        let operation = begin(ordinal, 0, &cancel);
        let result = cache.pin(0, &cancel);
        let baseline = operation.finish();
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
        let operation = begin(0, ordinal, &cancel);
        let result = cache.pin(0, &cancel);
        let baseline = operation.finish();
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
    let operation = begin(2, 0, &cancel);
    let failed = cache.pin(0, &cancel);
    operation.finish();
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
    let operation = begin(1, 0, &cancel);
    let result = cache.release(pin);
    operation.finish();
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
    println!(
        "observer maximum ownership slots={} capacity=4096 background_noise={}",
        MAX_SLOTS.load(SeqCst),
        std::env::var_os("MIXER_ALLOCATOR_NOISE").is_some()
    );
}
