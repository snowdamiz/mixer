#![cfg(feature = "experimental-function-cache")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type};
fn make(bytes: &[u8], profile: Profile, budget: CacheBudget) -> FunctionCache {
    let cancel = Cancellation::default();
    let spans = validate_spans(
        bytes,
        Limits {
            profile,
            ..Limits::default()
        },
        ValidationBudget::default(),
        &cancel,
    )
    .unwrap();
    FunctionCache::new(spans, budget, &cancel).unwrap()
}
fn three() -> Vec<u8> {
    let mut spec = Spec::one(vec![], None, vec![0x10, 0, 0x0b]);
    spec.functions
        .push(Function::new(vec![], None, vec![0x10, 0, 0x0b]));
    spec.functions
        .push(Function::new(vec![], None, vec![0x10, 1, 0x0b]));
    spec.bytes()
}
#[test]
fn cache_pins_support_nested_frames_and_lru_pressure() {
    let bytes = three();
    let cancel = Cancellation::default();
    let mut cache = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            max_entries: 2,
            max_pins: 4,
            ..CacheBudget::default()
        },
    );
    let caller = cache.pin(0, &cancel).unwrap();
    let recursive = cache.pin(0, &cancel).unwrap();
    let callee = cache.pin(1, &cancel).unwrap();
    let before = cache.usage();
    assert_eq!((before.active_pins, before.hits, before.decodes), (3, 1, 2));
    assert_eq!(
        cache.pin(2, &cancel).unwrap_err().kind,
        CacheFailureKind::AllPinned
    );
    assert_eq!(cache.view(&caller).unwrap().function, 0);
    cache.release(callee).unwrap();
    let other = cache.pin(2, &cancel).unwrap();
    assert_eq!(cache.usage().evictions, 1);
    assert_eq!(cache.view(&recursive).unwrap().function, 0);
    cache.release(recursive).unwrap();
    cache.release(caller).unwrap();
    cache.release(other).unwrap();
    assert_eq!(
        (cache.usage().pinned_bytes, cache.usage().active_pins),
        (0, 0)
    );
    let one = cache.pin(1, &cancel).unwrap();
    cache.release(one).unwrap();
    assert_eq!(cache.usage().evictions, 2);
}
#[test]
fn source_owner_wrong_owner_move_release_and_forgotten_pins() {
    let mut bytes = three();
    let frozen = bytes.clone();
    let mut a = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            max_entries: 1,
            max_pins: 1,
            ..CacheBudget::default()
        },
    );
    let mut b = make(&bytes, Profile::IntegerV1, CacheBudget::default());
    bytes.fill(255);
    drop(bytes);
    assert_eq!(a.spans().source(), frozen);
    assert_ne!(a.identity().owner, b.identity().owner);
    let pin = a.pin(0, &Cancellation::default()).unwrap();
    assert_eq!(
        b.view(&pin).err().unwrap().kind,
        CacheFailureKind::InvalidPin
    );
    let rejected = b.release(pin).unwrap_err();
    assert_eq!(rejected.failure.kind, CacheFailureKind::InvalidPin);
    let mut moved = a;
    assert_eq!(moved.view(&rejected.into_pin()).unwrap().function, 0);
    // The intentionally forgotten token still consumes its sole pin slot.
    assert_eq!(moved.usage().active_pins, 1);
    assert_eq!(
        moved.pin(1, &Cancellation::default()).unwrap_err().kind,
        CacheFailureKind::PinExhausted
    );
}
#[test]
fn oversize_cancel_work_and_capacity_boundaries() {
    let bytes = three();
    let cancel = Cancellation::default();
    let small = CacheBudget {
        max_entries: 1,
        max_pins: 1,
        ..CacheBudget::default()
    };
    let mut probe = make(&bytes, Profile::IntegerV1, small);
    let pin = probe.pin(0, &cancel).unwrap();
    let usage = probe.usage();
    let peak = usage.peak_cache_reserved;
    let entry = usage.resident_bytes;
    let exact_work = usage.work_used;
    probe.release(pin).unwrap();
    let mut exact = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            capacity_bytes: peak,
            entry_bytes: entry,
            work_credits: exact_work,
            ..small
        },
    );
    let pin = exact.pin(0, &cancel).unwrap();
    assert_eq!(exact.usage().peak_cache_reserved, peak);
    assert_eq!(
        exact.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::WorkExhausted
    );
    exact.release(pin).unwrap(); // cleanup despite work exhaustion
    let mut short = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            work_credits: exact_work - 1,
            ..small
        },
    );
    assert_eq!(
        short.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::WorkExhausted
    );
    assert_eq!(
        (
            short.usage().construction_bytes,
            short.usage().resident_bytes,
            short.usage().active_pins
        ),
        (0, 0, 0)
    );
    let mut short = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            capacity_bytes: peak - 1,
            ..small
        },
    );
    assert_eq!(
        short.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::Capacity
    );
    let mut oversize = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            entry_bytes: entry - 1,
            ..small
        },
    );
    assert_eq!(
        oversize.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::EntryOversize
    );
    assert_eq!(
        (oversize.usage().evictions, oversize.usage().resident_bytes),
        (0, 0)
    );
    let pin = probe.pin(0, &cancel).unwrap();
    let cancelled = Cancellation::default();
    cancelled.cancel();
    let before = probe.usage();
    assert_eq!(
        probe.pin(0, &cancelled).unwrap_err().kind,
        CacheFailureKind::Cancelled
    );
    assert_eq!(
        probe.pin(1, &cancelled).unwrap_err().kind,
        CacheFailureKind::Cancelled
    );
    assert_eq!(probe.usage().evictions, before.evictions);
    probe.release(pin).unwrap();
}
#[test]
fn numeric_table_indirect_and_variable_payloads_are_decoded() {
    let cancel = Cancellation::default();
    let mut numeric = Spec::one(
        vec![],
        Some(Type::F64),
        vec![0x44, 1, 2, 3, 4, 5, 6, 7, 8, 0x0b],
    );
    numeric.functions[0].locals = vec![Type::F32; 17];
    let mut cache = make(&numeric.bytes(), Profile::NumericV2, CacheBudget::default());
    let pin = cache.pin(0, &cancel).unwrap();
    assert_eq!(cache.view(&pin).unwrap().locals, vec![Type::F32; 17]);
    cache.release(pin).unwrap();
    let mut table = Spec::one(vec![], None, vec![0x41, 0, 0x11, 0, 0, 0x0b]);
    table.table = Some((1, 1));
    table.elements = vec![(0, vec![0])];
    let mut cache = make(
        &table.bytes(),
        Profile::TableMemoryV3,
        CacheBudget::default(),
    );
    let caller = cache.pin(0, &cancel).unwrap();
    let target = cache.pin(0, &cancel).unwrap();
    assert_eq!(
        cache.view(&caller).unwrap().instructions[1].operation,
        Operation::CallIndirect(0)
    );
    cache.release(target).unwrap();
    cache.release(caller).unwrap();
    let mut code = vec![2, 0x40, 0x41, 0, 0x0e];
    code.extend(u32leb(513));
    code.extend(vec![0; 514]);
    code.extend([0x0b, 0x0b]);
    let mut cache = make(
        &Spec::one(vec![], None, code).bytes(),
        Profile::IntegerV1,
        CacheBudget::default(),
    );
    let pin = cache.pin(0, &cancel).unwrap();
    assert_eq!(cache.view(&pin).unwrap().branch_targets, vec![0; 513]);
    assert_eq!(
        cache.view(&pin).unwrap().instructions[2].operation,
        Operation::BrTable {
            first: 0,
            count: 513,
            default: 0
        }
    );
    cache.release(pin).unwrap();
}
#[test]
fn invalid_uncalled_code_never_produces_cache_authority() {
    let mut spec = Spec::one(vec![], None, vec![0x0b]);
    spec.functions
        .push(Function::new(vec![], None, vec![0, 0xff, 0x0b]));
    let result = validate_spans(
        &spec.bytes(),
        Limits::default(),
        ValidationBudget::default(),
        &Cancellation::default(),
    );
    assert_eq!(result.err().unwrap().function, Some(1));
    let spans = validate_spans(
        b"\0asm\x01\0\0\0",
        Limits::default(),
        ValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut empty =
        FunctionCache::new(spans, CacheBudget::default(), &Cancellation::default()).unwrap();
    assert_eq!(
        empty.pin(0, &Cancellation::default()).unwrap_err().kind,
        CacheFailureKind::InvalidFunction
    );
}

#[test]
fn every_work_credit_boundary_and_repeated_eviction_is_charged() {
    let bytes = three();
    let cancel = Cancellation::default();
    let small = CacheBudget {
        max_entries: 1,
        max_pins: 1,
        ..CacheBudget::default()
    };
    let mut probe = make(&bytes, Profile::IntegerV1, small);
    let pin = probe.pin(0, &cancel).unwrap();
    let used = probe.usage().work_used;
    probe.release(pin).unwrap();
    for credits in 2..used {
        let mut cache = make(
            &bytes,
            Profile::IntegerV1,
            CacheBudget {
                work_credits: credits,
                ..small
            },
        );
        let failure = cache.pin(0, &cancel).unwrap_err();
        assert_eq!(
            failure.kind,
            CacheFailureKind::WorkExhausted,
            "credit {credits}"
        );
        assert_eq!(
            (
                cache.usage().active_pins,
                cache.usage().construction_bytes,
                cache.usage().resident_bytes
            ),
            (0, 0, 0),
            "credit {credits}"
        );
    }
    let mut previous = probe.usage().work_used;
    for function in [1, 2, 0, 1, 2, 0, 1, 2] {
        let pin = probe.pin(function, &cancel).unwrap();
        assert!(probe.usage().work_used > previous);
        previous = probe.usage().work_used;
        probe.release(pin).unwrap();
    }
    assert_eq!((probe.usage().decodes, probe.usage().evictions), (9, 8));
    assert!(probe.usage().peak_construction_bytes > 0);
    assert_eq!(
        probe.usage().peak_pinned_bytes,
        probe.usage().peak_resident_bytes
    );
}

#[test]
fn zero_count_groups_limits_and_import_indexes_fail_closed() {
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    section(&mut bytes, 1, vec![1, 0x60, 0, 0]);
    section(&mut bytes, 3, vec![1, 0]);
    let mut body = u32leb(129);
    for _ in 0..129 {
        body.extend([0, 0x7f]);
    }
    body.push(0x0b);
    let mut payload = vec![1];
    payload.extend(u32leb(body.len() as u32));
    payload.extend(body);
    section(&mut bytes, 10, payload);
    let cancel = Cancellation::default();
    let spans = validate_spans(
        &bytes,
        Limits {
            locals: 129,
            ..Limits::default()
        },
        ValidationBudget::default(),
        &cancel,
    )
    .unwrap();
    let mut cache = FunctionCache::new(spans, CacheBudget::default(), &cancel).unwrap();
    assert_eq!(cache.spans().limits().locals, 129);
    let pin = cache.pin(0, &cancel).unwrap();
    assert!(cache.view(&pin).unwrap().locals.is_empty());
    assert!(cache.usage().work_used > 3 * 129);
    cache.release(pin).unwrap();
    let invalid = CacheBudget {
        max_entries: 65,
        ..CacheBudget::default()
    };
    let spans = validate_spans(
        &bytes,
        Limits::default(),
        ValidationBudget::default(),
        &cancel,
    )
    .unwrap();
    assert_eq!(
        FunctionCache::new(spans, invalid, &cancel)
            .err()
            .unwrap()
            .kind,
        CacheFailureKind::InvalidBudget
    );
    let spans = validate_spans(
        &bytes,
        Limits::default(),
        ValidationBudget::default(),
        &cancel,
    )
    .unwrap();
    let cancelled = Cancellation::default();
    cancelled.cancel();
    assert_eq!(
        FunctionCache::new(spans, CacheBudget::default(), &cancelled)
            .err()
            .unwrap()
            .kind,
        CacheFailureKind::Cancelled
    );
    assert_eq!(
        cache.pin(u32::MAX, &cancel).unwrap_err().kind,
        CacheFailureKind::InvalidFunction
    );
}

#[test]
fn construction_overlap_counts_pinned_payload_and_oversize_keeps_resident() {
    let bytes = three();
    let cancel = Cancellation::default();
    let budget = CacheBudget {
        max_entries: 2,
        ..CacheBudget::default()
    };
    let mut probe = make(&bytes, Profile::IntegerV1, budget);
    let pin = probe.pin(0, &cancel).unwrap();
    let one_entry_peak = probe.usage().peak_cache_reserved;
    probe.release(pin).unwrap();
    let mut cache = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            capacity_bytes: one_entry_peak,
            ..budget
        },
    );
    let caller = cache.pin(0, &cancel).unwrap();
    assert_eq!(
        cache.pin(1, &cancel).unwrap_err().kind,
        CacheFailureKind::AllPinned
    );
    assert_eq!(cache.usage().evictions, 0);
    assert_eq!(cache.view(&caller).unwrap().function, 0);
    cache.release(caller).unwrap();
    let next = cache.pin(1, &cancel).unwrap();
    assert_eq!(cache.usage().evictions, 1);
    cache.release(next).unwrap();
    let mut spec = Spec::one(vec![], None, vec![0x0b]);
    spec.functions
        .push(Function::new(vec![], None, vec![1, 1, 0x0b]));
    let bytes = spec.bytes();
    let mut probe = make(&bytes, Profile::IntegerV1, budget);
    let pin = probe.pin(0, &cancel).unwrap();
    let entry = probe.usage().resident_bytes;
    probe.release(pin).unwrap();
    let mut cache = make(
        &bytes,
        Profile::IntegerV1,
        CacheBudget {
            entry_bytes: entry,
            max_entries: 1,
            ..budget
        },
    );
    let pin = cache.pin(0, &cancel).unwrap();
    cache.release(pin).unwrap();
    assert_eq!(
        cache.pin(1, &cancel).unwrap_err().kind,
        CacheFailureKind::EntryOversize
    );
    assert_eq!(cache.usage().evictions, 0);
    let pin = cache.pin(0, &cancel).unwrap();
    assert_eq!((cache.usage().hits, cache.usage().decodes), (1, 1));
    cache.release(pin).unwrap();
}

#[test]
fn imports_remain_metadata_and_absolute_defined_index_is_preserved() {
    let mut spec = Spec::one(vec![], None, vec![0x10, 0, 0x0b]);
    spec.imports.push(("checkpoint".into(), vec![], None));
    let mut cache = make(&spec.bytes(), Profile::IntegerV1, CacheBudget::default());
    let cancel = Cancellation::default();
    assert_eq!(
        cache.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::InvalidFunction
    );
    let pin = cache.pin(1, &cancel).unwrap();
    assert_eq!(cache.view(&pin).unwrap().function, 1);
    assert_eq!(
        cache.view(&pin).unwrap().instructions[0].operation,
        Operation::Call(0)
    );
    cache.release(pin).unwrap();
}
