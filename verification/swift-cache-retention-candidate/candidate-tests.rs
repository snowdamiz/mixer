use super::cache::retention_inspection as ri;

fn retention_seed_four(bytes: &[u8], budget: SwiftRunBudget) -> (RuntimeControl, SwiftFunctionCache) {
    let (mut c, mut cache) = new(bytes, budget);
    for f in [34,34,35,35,36,36,37] { plan_reuse_release(&mut cache,&mut c,f); }
    (c,cache)
}

#[test]
fn retention_candidate_capacity_ties_rebase_and_phase_adaptation() {
    let bytes=fixture(0,&[0,0x0b],100);
    for slots in [0,1,2,3,4,5,63,64] {
        assert_eq!(ri::capacity(slots),3*slots/4);
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:slots,..SwiftRunBudget::default()});
        for f in 34..34+slots as u32 {
            plan_reuse_release(&mut cache,&mut c,f);
            plan_reuse_release(&mut cache,&mut c,f);
        }
        let states=ri::states(&cache);
        assert_eq!(states.iter().filter(|s|s.1.is_some()&&s.2).count(),ri::capacity(slots));
        if slots==0 { assert!(pin(&mut cache,&mut c,34,None).is_err()); }
        finish(cache,c);
    }
    for shift in [0,10_000] {
        let (mut c,mut cache)=retention_seed_four(&bytes,SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()});
        ri::ages(&mut cache,Some(7),shift);
        plan_reuse_release(&mut cache,&mut c,37);
        let states=ri::states(&cache);
        assert!(!states.iter().find(|s|s.1==Some(34)).unwrap().2,"equal-age tie demotes lowest slot");
        assert!(states.iter().find(|s|s.1==Some(37)).unwrap().2);
        assert_eq!(states.iter().filter(|s|s.2).count(),3);
        finish(cache,c);
    }
    // Phase adaptation uses real, monotonic work timestamps. The test-only
    // order-preserving shift above applies only to one victim selection.
    let (mut c,mut cache)=retention_seed_four(&bytes,SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()});
    plan_reuse_release(&mut cache,&mut c,37);
    plan_reuse_release(&mut cache,&mut c,34);
    let states=ri::states(&cache);
    assert!(states.iter().find(|s|s.1==Some(34)).unwrap().2);
    assert!(!states.iter().find(|s|s.1==Some(35)).unwrap().2);
    finish(cache,c);
    let (mut c,mut cache)=retention_seed_four(&bytes,SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()});
    ri::ages(&mut cache,Some(1),0);
    plan_reuse_release(&mut cache,&mut c,38);
    assert!(!ri::states(&cache).iter().any(|s|s.1==Some(37)),"probationary evicted before equal-age protected entries");
    finish(cache,c);
    println!("RETENTION_CANDIDATE capacity_cases=8 equal_age_rebases=2 phase_adaptation=true cleanup=zero");
}

#[test]
fn retention_candidate_pins_and_memory_multiple_victims() {
    let bytes=fixture(0,&[0,0x01,0x01,0x0b],100);
    let b=SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,b);
    let fixed=cache.usage().fixed_reserved;
    plan_reuse_release(&mut cache,&mut c,35);
    let small=cache.usage().resident_bytes;
    finish(cache,c);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_bytes:fixed+4*small,..b});
    plan_reuse_release(&mut cache,&mut c,35);
    let protected_pin=pin(&mut cache,&mut c,35,None).unwrap();
    for f in 36..39 { plan_reuse_release(&mut cache,&mut c,f); }
    assert!(ri::states(&cache).iter().find(|s|s.1==Some(35)).unwrap().2);
    let p=pin(&mut cache,&mut c,34,None).unwrap();
    assert_eq!(cache.usage().evictions,3);
    assert_eq!(cache.usage().resident_bytes,small*4);
    assert_eq!(c.usage(None).live.cache_entries.current,2);
    let remaining:Vec<_>=ri::states(&cache).iter().filter_map(|s|s.1).collect();
    assert_eq!(remaining,vec![35,34]);
    cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    cache.release(protected_pin,&mut c,None).map_err(|e|e.failure).unwrap();
    resident_assert_index(&cache);
    finish(cache,c);

    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,mut cache)=new(&bytes,b);
    let mut pins=Vec::new();
    for f in 34..38 {
        plan_reuse_release(&mut cache,&mut c,f);
        pins.push(pin(&mut cache,&mut c,f,None).unwrap());
    }
    let before=ri::states(&cache);
    let failure=pin(&mut cache,&mut c,38,None).unwrap_err();
    assert_eq!(failure.code,"all_entries_pinned");
    assert_eq!(ri::states(&cache),before);
    for p in pins { cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap(); }
    assert_eq!(c.usage(None).live.active_pins.current,0);
    finish(cache,c);
    println!("RETENTION_CANDIDATE memory_victims=3 protected_pin_retained=true all_pinned_staged=true terminal_release=true cleanup=zero");
}

#[test]
fn retention_candidate_every_promotion_prefix_and_cancellation() {
    let bytes=fixture(0,&[0,0x0b],100);
    let budget=SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()};
    let (mut c,mut cache)=retention_seed_four(&bytes,budget);
    let base=c.usage(None).cache_work;
    hooks(Hooks::default());
    plan_reuse_release(&mut cache,&mut c,37);
    let credits=c.usage(None).cache_work-base;
    // Existing indexed hit path costs 8 credits. Additional preparation is
    // 1 tier + 2*4 occupied/tier + 3 protected ages + 2 tier writes = 14.
    assert_eq!(credits,8+1+2*4+3+2);
    let checks=HOOKS.with(|h|h.get().checks);
    finish(cache,c);
    for prefix in 0..credits {
        hooks(Hooks::default());
        let (mut c,mut cache)=retention_seed_four(&bytes,SwiftRunBudget{cache_work:base+prefix,..budget});
        let before=ri::states(&cache);
        let usage=cache.usage();
        let f=pin(&mut cache,&mut c,37,None).unwrap_err();
        assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        assert_eq!(ri::states(&cache),before,"retention and age unchanged at prefix {prefix}");
        assert_eq!(cache.usage().hits,usage.hits);
        assert_eq!(c.usage(None).live.active_pins.current,0);
        let repeated=pin(&mut cache,&mut c,34,None).unwrap_err();
        plan_reuse_primary(f,repeated);
        finish(cache,c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());
        let (mut c,mut cache)=retention_seed_four(&bytes,budget);
        let before=ri::states(&cache);
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});
        let f=pin(&mut cache,&mut c,37,None).unwrap_err();
        assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);
        assert_eq!(ri::states(&cache),before);
        hooks(Hooks::default());
        finish(cache,c);
    }
    println!("RETENTION_CANDIDATE promotion_work_prefixes={credits} cancellation_boundaries={checks} atomic=true cleanup=zero");
}

#[test]
fn retention_candidate_every_replacement_prefix_and_cancellation() {
    let bytes=fixture(0,&[0,0x0b],100);
    let budget=SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()};
    let (mut c,mut cache)=retention_seed_four(&bytes,budget);
    let base=c.usage(None).cache_work;
    hooks(Hooks::default());
    plan_reuse_release(&mut cache,&mut c,38);
    let credits=c.usage(None).cache_work-base;
    let checks=HOOKS.with(|h|h.get().checks);
    finish(cache,c);
    for prefix in 0..credits {
        hooks(Hooks::default());
        let (mut c,mut cache)=retention_seed_four(&bytes,SwiftRunBudget{cache_work:base+prefix,..budget});
        let before=ri::states(&cache);
        let f=pin(&mut cache,&mut c,38,None).unwrap_err();
        assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        let after=ri::states(&cache);
        assert!(!after.iter().any(|s|s.1==Some(38)));
        for s in after.iter().filter(|s|s.1.is_some()) {
            let previous=before.iter().find(|p|p.1==s.1).unwrap();
            assert_eq!((s.2,s.3,s.4),(previous.2,previous.3,previous.4));
        }
        assert_eq!(c.usage(None).live.active_pins.current,0);
        resident_assert_index(&cache);
        finish(cache,c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());
        let (mut c,mut cache)=retention_seed_four(&bytes,budget);
        let before=ri::states(&cache);
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});
        let f=pin(&mut cache,&mut c,38,None).unwrap_err();
        assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);
        let after=ri::states(&cache);
        assert!(!after.iter().any(|s|s.1==Some(38)));
        for s in after.iter().filter(|s|s.1.is_some()) {
            let previous=before.iter().find(|p|p.1==s.1).unwrap();
            assert_eq!((s.2,s.3,s.4),(previous.2,previous.3,previous.4));
        }
        hooks(Hooks::default());
        resident_assert_index(&cache);
        finish(cache,c);
    }
    println!("RETENTION_CANDIDATE replacement_work_prefixes={credits} cancellation_boundaries={checks} surviving_tiers_unchanged=true cleanup=zero");
}

#[test]
fn retention_candidate_accounted_shapes_and_slot_admission() {
    use crate::experimental::cache::borrowed::{CacheMode,FrozenMode};
    let (plan,inventory,unit)=ri::plan_bytes();
    assert_eq!(unit,0);
    assert_eq!(size_of::<<FrozenMode as CacheMode>::HitPlan>(),0);
    let bytes=fixture(0,&[0,0x0b],100);
    let (c,cache)=new(&bytes,SwiftRunBudget::default());
    let fixed=cache.usage().fixed_reserved;
    assert_eq!(c.budget(),SwiftRunBudget::default());
    assert!(cache_operation_bytes().unwrap()>=3*inventory);
    finish(cache,c);
    let (mut c,a)=adopt(&bytes,SwiftRunBudget{cache_bytes:cache_header_bytes().unwrap()+64*size_of::<SwiftSlot>()-1,..SwiftRunBudget::default()});
    let (result,stats)=measure(||construct(&mut c,a,None));
    assert!(result.is_err());
    assert_eq!(stats.attempts,0,"tier-bearing slot payload must be admitted before allocator");
    assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
    println!("RETENTION_CANDIDATE hit_plan_bytes={plan} inventory_bytes={inventory} copies=3 fixed_bytes={fixed} frozen_hit_plan_bytes={unit} preallocation_reject=true cleanup=zero");
}
