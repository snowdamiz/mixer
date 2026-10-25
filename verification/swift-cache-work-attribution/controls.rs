// Finite independently authored controls on the actual copied Swift cache.
fn attribution_emit(label: &str, control: &RuntimeControl, cache: &SwiftFunctionCache) {
    let (json, valid) = attribution_json(control.usage(None).cache_work, Some(&cache.usage()));
    println!("MIXER_ATTRIBUTION {{\"case\":\"{}\",\"observer\":{}}}", label, json);
    assert!(valid, "credit, lookup, bitmap and completed-decode reconciliation: {json}");
}
#[test]
fn attribution_actual_cache_controls() {
    for count in [64, 65] {
        hooks(Hooks::default()); attribution_reset();
        let bytes = fixture(0, &[0, 0x0b], 100);
        let (mut control, mut cache) = new(&bytes, SwiftRunBudget::default());
        attribution_emit("constructed", &control, &cache);
        assert_eq!(attribution_state().credits[0], 640);
        for _ in 0..2 {
            for function in 34..34 + count {
                let p = pin(&mut cache, &mut control, function, None).unwrap();
                cache.release(p, &mut control, None).map_err(|e| e.failure).unwrap();
            }
        }
        let s = attribution_state();
        if count == 64 {
            assert_eq!((s.hits, s.distinct, s.repeated, cache.usage().evictions), (64, 64, 0, 0));
            let before = s.credits;
            let p = pin(&mut cache, &mut control, 97, None).unwrap();
            cache.release(p, &mut control, None).map_err(|e| e.failure).unwrap();
            let after = attribution_state();
            assert_eq!(after.credits[1] - before[1], 1);
            assert_eq!(after.credits[2] - before[2], 1);
            assert_eq!(after.credits[3] - before[3], 64);
            assert_eq!(after.hit_histogram[64], s.hit_histogram[64] + 1);
            let mut held = Vec::new();
            for _ in 0..63 { held.push(pin(&mut cache, &mut control, 34, None).unwrap()); }
            let before = attribution_state();
            let p = pin(&mut cache, &mut control, 97, None).unwrap();
            cache.release(p, &mut control, None).map_err(|e| e.failure).unwrap();
            let after = attribution_state();
            assert_eq!(after.credits[2] - before.credits[2], 64);
            assert_eq!(after.free_histogram[64], before.free_histogram[64] + 1);
            for p in held { cache.release(p, &mut control, None).map_err(|e| e.failure).unwrap(); }
        } else {
            assert_eq!((s.hits, s.distinct, s.repeated, cache.usage().evictions), (0, 65, 65, 66));
            assert_eq!(s.sample_len, 16);
            assert_eq!(s.samples, std::array::from_fn(|i| 34 + i as u32));
            assert_eq!(s.untracked_repeated_occurrences, 49);
        }
        attribution_emit(if count == 64 { "64_cycle_twice_and_hot_positions" } else { "65_cycle_twice" }, &control, &cache);
        finish(cache, control);
    }
    // Exercise scan/build policy and nested decoder credits without equating this with target behavior.
    hooks(Hooks::default()); attribution_reset();
    let bytes = fixture(0, &body(0, &[2,0x40,3,0x40,1,0x0b,0x0b,0x41,0,4,0x40,1,5,1,0x0b,0x0b]), 100);
    let (mut control, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut control, 34, None).unwrap();
    cache.release(p, &mut control, None).map_err(|e| e.failure).unwrap();
    let s = attribution_state();
    assert!(s.credits[4] > 0 && s.credits[5] > 0 && s.credits[6] > 0 && s.credits[8] > 0 && s.credits[9] > 0 && s.credits[10] > 0);
    assert_eq!(s.credits[11], 0);
    attribution_emit("nested_decode", &control, &cache);
    finish(cache, control);
}
fn attribution_failure_signature(f: &SwiftRunFailure) -> String {
    // Elapsed timings are observational; preserve and compare all typed authority/failure fields.
    format!("{:?}|{:?}|{}|{:?}|{:?}|{:?}|{}|{}|{:?}|{:?}|{:?}|{:?}|{}|{}|{}",
        f.stage, f.kind, f.code, f.function, f.offset, f.resource, f.attempted, f.limit,
        f.observed_capacity, f.deadline_origin, f.wasi_failure, f.guest_exit,
        f.at_failure.cache_work, f.at_failure.execution_work, f.at_failure.instructions)
}
#[test]
fn attribution_finite_failure_prefixes_and_invalidity_are_observational() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    // Exact constructor=640, flat cold pin=205; all finite cache-credit failure prefixes.
    for cap in [640, 641, 642, 643, 706, 707, 708, 772, 836, 844] {
        let mut signatures = Vec::new();
        for mode in 0..3 {
            hooks(Hooks::default()); attribution_reset();
            if mode == 0 { ATTRIBUTION.with(|s| s.borrow_mut().enabled = false); }
            let (mut control, mut cache) = new(&bytes, SwiftRunBudget { cache_work: cap, ..SwiftRunBudget::default() });
            if mode == 2 { attribution_site(255); attribution_decode_completed(80_000); }
            let failure = pin(&mut cache, &mut control, 34, None).err().expect("finite prefix rejects original work");
            signatures.push(attribution_failure_signature(&failure));
            assert_eq!(failure.kind, SwiftRunFailureKind::WorkExhausted);
            assert_eq!(failure.resource, Some(SwiftRunResource::CacheWork));
            if mode == 1 {
                let rejected = attribution_state().rejected.expect("first original work rejection");
                assert_eq!(attribution_failure_signature(&rejected.failure), attribution_failure_signature(&failure));
                attribution_emit("finite_cache_work_failure", &control, &cache);
            }
            if mode == 2 { assert_ne!(attribution_state().invalid, 0); }
            finish(cache, control);
        }
        assert_eq!(signatures[0], signatures[1]); assert_eq!(signatures[0], signatures[2]);
    }
    for ordinal in [0, 1, 2, 5, 20, 60] {
        let mut signatures = Vec::new();
        for enabled in [false, true] {
            hooks(Hooks::default()); attribution_reset();
            ATTRIBUTION.with(|s| s.borrow_mut().enabled = enabled);
            let (mut control, mut cache) = new(&bytes, SwiftRunBudget::default());
            hooks(Hooks { cancel: Some(ordinal), ..Hooks::default() });
            let failure = pin(&mut cache, &mut control, 34, None).err().expect("finite checkpoint cancels");
            assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
            signatures.push(attribution_failure_signature(&failure));
            if enabled { attribution_emit("finite_cancellation_failure", &control, &cache); }
            finish(cache, control);
        }
        assert_eq!(signatures[0], signatures[1]);
    }
    // Saturated counters and reentrant observer borrowing flag invalidity without panic or VM authority.
    hooks(Hooks::default()); attribution_reset();
    let (mut control, mut cache) = new(&bytes, SwiftRunBudget::default());
    ATTRIBUTION.with(|s| { s.borrow_mut().credits[1] = u64::MAX; let _held = s.borrow(); attribution_site(1); });
    let p = pin(&mut cache, &mut control, 34, None).unwrap();
    cache.release(p, &mut control, None).map_err(|e| e.failure).unwrap();
    assert_ne!(attribution_state().invalid, 0);
    assert!(!attribution_json(control.usage(None).cache_work, Some(&cache.usage())).1);
    finish(cache, control);
    println!("MIXER_ATTRIBUTION {{\"cleanup\":\"all_finite_original_owners_drained\",\"observer_invalidity_did_not_change_vm_results\":true}}");
}
