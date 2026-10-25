
// Selected bounded resident-index controls. The oracle walks actual owner slots
// independently and compares every chain membership with the resident set.
fn resident_assert_index(cache: &SwiftFunctionCache) {
    let index = inspection::resident_index(cache);
    assert_eq!(index.len(), 192);
    let slots = inspection::elision_slots(cache);
    let mut seen = [false; 64];
    for bucket in 0..128 {
        let mut node = index[bucket];
        let mut count = 0;
        while node != 0 {
            assert!(count < 64, "unbounded or cyclic chain");
            let slot = usize::from(node - 1);
            assert!(slot < slots.len());
            assert!(!seen[slot]);
            seen[slot] = true;
            let function = slots[slot][1];
            assert_ne!(function, u64::MAX);
            assert_eq!((((function * 0x9e37_79b9) & 0xffff_ffff) >> 25) as usize, bucket);
            node = index[128 + slot];
            count += 1;
        }
    }
    for (slot, actual) in slots.iter().enumerate() {
        assert_eq!(seen[slot], actual[1] != u64::MAX);
        if !seen[slot] { assert_eq!(index[128 + slot], 0); }
    }
    assert!(index[128 + slots.len()..].iter().all(|link| *link == 0));
}
fn resident_seed(c: &mut RuntimeControl, cache: &mut SwiftFunctionCache) {
    for function in [34, 178, 267] {
        let p = pin(cache, c, function, None).unwrap();
        cache.release(p, c, None).map_err(|e| e.failure).unwrap();
        resident_assert_index(cache);
    }
}
#[test]
fn resident_index_collision_delete_head_middle_tail_and_reinsert() {
    // These four independently calculated identities share bucket1.
    for victim in [267, 178, 34] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 500);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget { cache_entries: 3, ..SwiftRunBudget::default() });
        resident_seed(&mut c, &mut cache);
        let victim_slot = inspection::elision_slots(&cache).iter().find(|s| s[1] == victim).unwrap()[0];
        for function in [34, 178, 267].into_iter().filter(|f| u64::from(*f) != victim) {
            let (p, allocations) = measure(|| pin(&mut cache, &mut c, function, None).unwrap());
            assert_eq!(allocations.attempts, 0);
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        }
        let p = pin(&mut cache, &mut c, 411, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().function, 411);
        assert_eq!(cache.usage().evictions, 1);
        assert_eq!(inspection::elision_slots(&cache)[victim_slot as usize][1], 411);
        resident_assert_index(&cache);
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        let p = pin(&mut cache, &mut c, victim as u32, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().function, victim as u32);
        resident_assert_index(&cache);
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        finish(cache, c);
        println!("RESIDENT collision victim={victim} removed/reused/reinserted cleanup=zero");
    }
}
#[test]
fn resident_index_every_collision_replacement_work_and_cancel_boundary() {
    for victim in [34,178,267] {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 500);
    let budget = SwiftRunBudget { cache_entries: 3, ..SwiftRunBudget::default() };
    let (mut c, mut cache) = new(&bytes, budget);
    resident_seed(&mut c, &mut cache);
    for function in [34,178,267].into_iter().filter(|f| *f != victim) {
        let p=pin(&mut cache,&mut c,function,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    }
    let base = c.usage(None).cache_work;
    hooks(Hooks::default());
    let p = pin(&mut cache, &mut c, 411, None).unwrap();
    let credits = c.usage(None).cache_work - base;
    let checks = HOOKS.with(|h| h.get().checks);
    hooks(Hooks::default());
    cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    finish(cache, c);
    for prefix in 0..credits {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget { cache_work: base + prefix, ..budget });
        resident_seed(&mut c, &mut cache);
    for function in [34,178,267].into_iter().filter(|f| *f != victim) {
        let p=pin(&mut cache,&mut c,function,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    }
        let failure = pin(&mut cache, &mut c, 411, None).unwrap_err();
        assert_eq!(failure.resource, Some(SwiftRunResource::CacheWork));
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        resident_assert_index(&cache);
        let before = c.usage(None);
        assert_eq!(pin(&mut cache, &mut c, 411, None).unwrap_err().kind, failure.kind);
        review_assert_same_control_effects(before, c.usage(None));
        finish(cache, c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(&bytes, budget);
        resident_seed(&mut c, &mut cache);
    for function in [34,178,267].into_iter().filter(|f| *f != victim) {
        let p=pin(&mut cache,&mut c,function,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    }
        hooks(Hooks { cancel: Some(ordinal), ..Hooks::default() });
        assert_eq!(pin(&mut cache, &mut c, 411, None).unwrap_err().kind, SwiftRunFailureKind::Cancelled);
        hooks(Hooks::default());
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        resident_assert_index(&cache);
        finish(cache, c);
    }
    println!("RESIDENT every replacement victim={victim} work_prefixes={credits} cancellation_checks={checks} original_failure_sticky=true cleanup=zero");
    }
}

#[test]
fn resident_index_invalid_slot_empty_link_wrong_bucket_cycle_fail_closed() {
    for case in 0..4 {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 500);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        resident_seed(&mut c, &mut cache);
        let bucket = (((34u64 * 0x9e37_79b9) & 0xffff_ffff) >> 25) as usize;
        let head = inspection::resident_index(&cache)[bucket];
        match case {
            0 => inspection::corrupt_index(&mut cache, bucket, 255),
            1 => inspection::corrupt_index(&mut cache, 128 + usize::from(head - 1), 64),
            2 => { let p=pin(&mut cache,&mut c,35,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();inspection::corrupt_index(&mut cache,bucket,4); }
            _ => inspection::corrupt_index(&mut cache, 128 + usize::from(head - 1), head),
        }
        let failure = pin(&mut cache, &mut c, 34, None).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::DecoderMismatch);
        assert_eq!(cache.usage().decodes, if case == 2 { 4 } else { 3 });
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        finish(cache, c);
        println!("RESIDENT corrupt case={case} code={} failclosed cleanup=zero",failure.code);
    }
}
#[test]
fn resident_index_all_pinned_exact_capacity_and_empty_links() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 500);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget { cache_entries: 3, ..SwiftRunBudget::default() });
    let a=pin(&mut cache,&mut c,34,None).unwrap();
    let b=pin(&mut cache,&mut c,178,None).unwrap();
    let d=pin(&mut cache,&mut c,267,None).unwrap();
    let before = inspection::resident_index(&cache).to_vec();
    assert_eq!(pin(&mut cache,&mut c,411,None).unwrap_err().code,"all_entries_pinned");
    assert_eq!(inspection::resident_index(&cache),before);
    resident_assert_index(&cache);
    for p in [a,b,d] {cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
    finish(cache,c);
    println!("RESIDENT all_pinned original_index_retained=true terminal_release=true cleanup=zero");
}
