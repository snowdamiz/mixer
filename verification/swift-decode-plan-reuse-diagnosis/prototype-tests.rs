
use super::cache::plan_inspection as pi;
fn plan_reuse_release(cache:&mut SwiftFunctionCache,c:&mut RuntimeControl,f:u32) {
    let p=pin(cache,c,f,None).unwrap();
    cache.release(p,c,None).map_err(|e|e.failure).unwrap();
}
fn plan_reuse_seed(bytes:&[u8], budget:SwiftRunBudget) -> (RuntimeControl,SwiftFunctionCache) {
    let (mut c,mut cache)=new(bytes,budget);
    plan_reuse_release(&mut cache,&mut c,34);
    plan_reuse_release(&mut cache,&mut c,35);
    assert_eq!(pi::key(&cache,34),Some(34));
    (c,cache)
}
fn plan_reuse_primary(a:SwiftRunFailure,b:SwiftRunFailure) {
    assert_eq!((a.kind,a.code,a.function,a.offset,a.resource,a.attempted,a.limit),(b.kind,b.code,b.function,b.offset,b.resource,b.attempted,b.limit));
}
#[test]
fn plan_reuse_shapes_and_admission() {
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
    let (result,stats)=measure(||construct(&mut c,a,None));
    let cache=result.unwrap();
    assert_eq!(stats.attempts,5);
    assert_eq!(c.budget(),SwiftRunBudget::default());
    assert_eq!(c.usage(None).reservations.live_tickets,7);
    println!("PLAN_SHAPE {:?} constructor_allocations={stats:?} fixed={} cleanup={:?}",pi::shape(),cache.usage().fixed_reserved,cache_cleanup_temporary_bytes());
    assert_eq!(pi::count(&cache),0);
    finish(cache,c);
}
#[test]
fn plan_reuse_collisions_and_independent_identity() {
    let bytes=fixture(0,&body(1,&[0x0b]),600);
    let budget=SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,budget);
    plan_reuse_release(&mut cache,&mut c,34);
    assert_eq!(pi::key(&cache,34),Some(34));
    plan_reuse_release(&mut cache,&mut c,546);
    assert_eq!(pi::key(&cache,34),Some(546));
    plan_reuse_release(&mut cache,&mut c,34);
    assert_eq!(pi::key(&cache,546),Some(34));
    plan_reuse_release(&mut cache,&mut c,35);
    let ((r,scans),stats)=measure(||{
        hooks(Hooks::default());
        let r=pin(&mut cache,&mut c,34,None).unwrap();
        (r,HOOKS.with(|h|h.get().steps[CacheStep::Scan as usize]))
    });
    assert_eq!(scans,0);
    assert_eq!(stats.attempts,2);
    cache.release(r,&mut c,None).map_err(|e|e.failure).unwrap();
    finish(cache,c);
    let (c,cache)=new(&bytes,budget); assert_eq!(pi::count(&cache),0); finish(cache,c);
    for field in 0..4 {
        let (mut c,mut cache)=plan_reuse_seed(&bytes,budget);
        pi::corrupt(&mut cache,34,field);
        let f=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!(f.kind,SwiftRunFailureKind::DecoderMismatch);
        assert_eq!(f.code,if field<3 {"swift_plan_identity"} else {"decode_count_mismatch"});
        let work=c.usage(None).cache_work;
        let second=pin(&mut cache,&mut c,35,None).unwrap_err();
        plan_reuse_primary(f,second);assert_eq!(c.usage(None).cache_work,work);
        assert_eq!(c.usage(None).live.active_pins.current,0);
        finish(cache,c);
    }
    let (mut c,mut cache)=plan_reuse_seed(&bytes,budget);
    let (mut other,other_cache)=new(&bytes,budget);
    let before=pi::count(&cache);
    let (r,stats)=measure(||pin(&mut cache,&mut other,34,None));
    assert!(r.is_err());assert_eq!(stats.attempts,0);assert_eq!(pi::count(&cache),before);
    finish(other_cache,other);finish(cache,c);
}
#[test]
fn plan_reuse_constructor_all_boundaries() {
    let bytes=fixture(0,&[0,0x0b],29);
    hooks(Hooks::default());
    let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
    hooks(Hooks::default());
    let cache=construct(&mut c,a,None).unwrap();
    let checks=HOOKS.with(|h|h.get().checks);
    let credits=c.usage(None).cache_work;
    hooks(Hooks::default());finish(cache,c);
    for ordinal in 0..5 {
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        let (r,s)=measure_extended(Some(ordinal),||construct(&mut c,a,None));
        assert!(r.is_err());assert_eq!(s.injected_failures,1);
        assert_eq!(c.usage(None).reservations.cache.current,0);
        assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        hooks(Hooks{capacity:Some(ordinal),..Hooks::default()});
        let f=construct(&mut c,a,None).err().unwrap();hooks(Hooks::default());
        assert_eq!(f.resource,Some(SwiftRunResource::ExactCapacity));
        assert_eq!(c.usage(None).reservations.cache.current,0);
        assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
    }
    for work in 0..credits {
        let (mut c,a)=adopt(&bytes,SwiftRunBudget{cache_work:work,..SwiftRunBudget::default()});
        let r=construct(&mut c,a,None);assert!(r.is_err(),"work {work}");
        assert_eq!(c.usage(None).reservations.cache.current,0);
        assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
    }
    for ordinal in 0..checks {
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});
        let r=construct(&mut c,a,None);hooks(Hooks::default());assert!(r.is_err(),"check {ordinal}");
        assert_eq!(c.usage(None).reservations.cache.current,0);
        assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
    }
    println!("PLAN_CONSTRUCTOR allocation=5 capacity=5 shorter_work={credits} cancellation_checks={checks} cleanup_zero=true");
}
#[test]
fn plan_reuse_cold_cached_all_boundaries() {
    let bytes=fixture(0,&body(1,&[0,0x0e,1,0,0,0x0b]),100);
    let base=SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()};
    for cached in [false,true] {
        hooks(Hooks::default());
        let (mut c,mut cache)=if cached {plan_reuse_seed(&bytes,base)} else {new(&bytes,base)};
        let before=c.usage(None).cache_work;
        hooks(Hooks::default());
        let p=pin(&mut cache,&mut c,34,None).unwrap();
        let checks=HOOKS.with(|h|h.get().checks);
        let work=c.usage(None).cache_work-before;
        hooks(Hooks::default());cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
        for shorter in 0..work {
            hooks(Hooks::default());
            let (mut c,mut cache)=if cached {plan_reuse_seed(&bytes,SwiftRunBudget{cache_work:before+shorter,..base})} else {new(&bytes,SwiftRunBudget{cache_work:before+shorter,..base})};
            let f=pin(&mut cache,&mut c,34,None).unwrap_err();
            assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
            let retained=pi::key(&cache,34);assert!(retained.is_none()||retained==Some(34));
            let stopped=c.usage(None).cache_work;
            plan_reuse_primary(f,pin(&mut cache,&mut c,34,None).unwrap_err());
            assert_eq!(c.usage(None).cache_work,stopped);
            finish(cache,c);
        }
        for ordinal in 0..checks {
            let (mut c,mut cache)=if cached {plan_reuse_seed(&bytes,base)} else {new(&bytes,base)};
            hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});
            let f=pin(&mut cache,&mut c,34,None).unwrap_err();hooks(Hooks::default());
            assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);
            assert_eq!(c.usage(None).live.active_pins.current,0);
            plan_reuse_primary(f,pin(&mut cache,&mut c,34,None).unwrap_err());
            finish(cache,c);
        }
        for ordinal in 0..3 {
            let (mut c,mut cache)=if cached {plan_reuse_seed(&bytes,base)} else {new(&bytes,base)};
            let (r,s)=measure_extended(Some(ordinal),||pin(&mut cache,&mut c,34,None));
            assert!(r.is_err());assert_eq!(s.injected_failures,1);
            assert_eq!(pi::key(&cache,34),Some(34));
            assert_eq!(c.usage(None).live.active_pins.current,0);finish(cache,c);
        }
        println!("PLAN_OPERATION cached={cached} shorter_work={work} cancellation_checks={checks} allocations=3 cleanup_zero=true");
    }
}
