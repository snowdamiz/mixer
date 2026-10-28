// Original actual-owner controls, plus independently authored representation
// checks. Every success/failure owner is consumed by the original finish path.
#[test]
fn dense_campaign_retention_churn_and_pin_bound() {
    campaign_retention_churn_and_pin_bound();
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 79_966);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for function in [34, 79_999] {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().function, function);
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    }
    resident_assert_index(&cache);
    assert_eq!(pin(&mut cache, &mut c, 0, None).unwrap_err().code, "not_defined_function");
    finish(cache, c);
    println!("DENSE keys=34,79999 import_rejected=true payload_bytes=160000 free_pin_bytes=8");
}

#[test]
fn dense_campaign_map_corruption_and_duplicate_prevention() {
    for case in 0..6 {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 500);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        for function in [34, 35] { plan_reuse_release(&mut cache, &mut c, function); }
        let first = inspection::resident_index(&cache)[34];
        let second = inspection::resident_index(&cache)[35];
        let attempted = match case {
            0 => { inspection::corrupt_index(&mut cache, 34, 257); 34 }
            1 => { inspection::corrupt_index(&mut cache, 34, second); 34 }
            2 => { inspection::corrupt_index(&mut cache, 34, 0); 34 }
            3 => { inspection::corrupt_index(&mut cache, 36, first); 36 }
            4 => { inspection::corrupt_index(&mut cache, 34, 0); 36 }
            _ => { inspection::corrupt_index(&mut cache, 35, first); 36 }
        };
        let decodes = cache.usage().decodes;
        let failure = pin(&mut cache, &mut c, attempted, None).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::DecoderMismatch);
        assert_eq!(cache.usage().decodes, decodes);
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        plan_reuse_primary(failure, pin(&mut cache, &mut c, 34, None).unwrap_err());
        finish(cache, c);
    }
    println!("DENSE corruption_cases=6 authorization_from_actual_slot=true duplicate_prevented=true");
}

#[test]
fn dense_campaign_pin_identity_mask_and_release() {
    foreign_stale_nonce_and_control_ownership();
    for case in 0..4 {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget { active_pins: 4, ..SwiftRunBudget::default() });
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let held = inspection::dense_pin_mask(&cache);
        match case {
            0 => inspection::dense_set_pin_mask(&mut cache, held | (1u64 << 63)),
            1 => inspection::dense_set_pin_mask(&mut cache, held ^ 3), // occupied bit made free, popcount unchanged
            2 => inspection::dense_set_pin_mask(&mut cache, 0),
            _ => inspection::dense_set_pin_mask(&mut cache, held | 1),
        }
        if case == 3 {
            let rejected = cache.release(p, &mut c, None).err().unwrap();
            assert_eq!(rejected.failure.code, "swift_dense_release_mask");
            inspection::dense_set_pin_mask(&mut cache, held);
            cache.release(rejected.into_pin(), &mut c, None).map_err(|e| e.failure).unwrap();
        } else {
            assert_eq!(pin(&mut cache, &mut c, 35, None).unwrap_err().kind, SwiftRunFailureKind::Invariant);
            inspection::dense_set_pin_mask(&mut cache, held);
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        }
        resident_assert_index(&cache);
        finish(cache, c);
    }
    // A released token is stale even if its free slot has been reused.
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let stale = inspection::stale(&p);
    cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    let reused = pin(&mut cache, &mut c, 35, None).unwrap();
    assert_eq!(cache.release(stale, &mut c, None).err().unwrap().failure.code, "stale_pin");
    cache.release(reused, &mut c, None).map_err(|e| e.failure).unwrap();
    finish(cache, c);
    println!("DENSE foreign_stale_reused_nonce_and_mask_fail_closed=true release_after_failure=true");
}

#[test]
fn dense_campaign_every_replacement_and_hit_failure_prefix() {
    resident_index_every_collision_replacement_work_and_cancel_boundary();
    let bytes = fixture(0, &[0, 0x0b], 100);
    hooks(Hooks::default());
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    plan_reuse_release(&mut cache, &mut c, 34);
    let before = c.usage(None).cache_work;
    hooks(Hooks::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let credits = c.usage(None).cache_work - before;
    let checks = HOOKS.with(|h| h.get().checks);
    hooks(Hooks::default());
    cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    finish(cache, c);
    for short in 0..credits {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget { cache_work: before + short, ..SwiftRunBudget::default() });
        plan_reuse_release(&mut cache, &mut c, 34);
        assert_eq!(pin(&mut cache, &mut c, 34, None).unwrap_err().resource, Some(SwiftRunResource::CacheWork));
        resident_assert_index(&cache);
        finish(cache, c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        plan_reuse_release(&mut cache, &mut c, 34);
        hooks(Hooks { cancel: Some(ordinal), ..Hooks::default() });
        assert_eq!(pin(&mut cache, &mut c, 34, None).unwrap_err().kind, SwiftRunFailureKind::Cancelled);
        hooks(Hooks::default());
        resident_assert_index(&cache);
        finish(cache, c);
    }
    println!("DENSE hit_work_prefixes={credits} hit_cancel_prefixes={checks} masks_atomic=true");
}

#[test]
fn dense_campaign_constructor_allocation_and_header_lifetimes() {
    plan_reuse_constructor_all_boundaries();
    plan_reuse_header_lifetime_and_narrow_admission();
    println!("DENSE constructor_allocation_capacity_work_cancel_and_header_lifetimes=true");
}

#[test]
fn dense_campaign_full_geometry_and_conservative_envelope() {
    let budget = SwiftRunBudget::default();
    assert_eq!((budget.cache_entries, budget.active_pins, budget.frames), (256, 64, 64));
    assert_eq!((budget.cache_work, budget.instruction_fuel, budget.execution_work, budget.deadline_ms), (768_000_000, 1_000_000_000, 8_000_000_000, 600_000));
    assert_eq!((budget.cache_bytes, budget.cache_entry_bytes, budget.combined_bytes), (16 << 20, 8 << 20, 256 << 20));
    assert_eq!(MAX_RESERVATION_TICKETS, 278);
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 296);
    let (mut c, mut cache) = new(&bytes, budget);
    for function in 34..290 { plan_reuse_release(&mut cache, &mut c, function); }
    resident_assert_index(&cache);
    assert_eq!(inspection::resident_index(&cache)[289], 256);
    assert_eq!(inspection::resident_index(&cache).len() * size_of::<u16>(), 160_000);
    assert_eq!(c.usage(None).live.cache_entries.current, 256);
    println!("DENSE geometry index_bytes=160000 pin_bitmap_bytes=8 header={} operation={} logical_peak={}", cache_header_bytes().unwrap(), cache_operation_bytes().unwrap(), c.usage(None).reservations.combined.peak);
    finish(cache, c);
    plan_reuse_profile_envelopes_without_guest_execution();
    crate::experimental::cache::architecture_frozen_controls();
}
