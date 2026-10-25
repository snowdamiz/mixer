
#[test]
fn plan_reuse_header_lifetime_and_narrow_admission() {
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,cache)=new(&bytes,SwiftRunBudget::default());
    let mut owned=Some(cache);
    let (tail,s)=measure(||SwiftFunctionCache::cleanup(&mut owned,&mut c,None).unwrap());
    assert!(owned.is_none());assert!(s.freed_bytes>=pi::shape().1);
    assert_eq!(pi::tail_usage(&tail).reservations.cache.current,cache_header_bytes().unwrap());
    let mut result=None;tail.complete(owned,&mut result);
    assert_eq!(c.usage(None).reservations.cache.current,0);
    assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
    // The additional table cannot silently outgrow a narrowed cache ceiling.
    for limit in [0,pi::shape().1-1,cache_header_bytes().unwrap()-1] {
        let (mut c,a)=adopt(&bytes,SwiftRunBudget{cache_bytes:limit,..SwiftRunBudget::default()});
        assert!(construct(&mut c,a,None).is_err());
        assert_eq!(c.usage(None).reservations.cache.current,0);
        assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
    }
    println!("PLAN_HEADER payload_dropped_before_header=true narrowed_limits=3 cleanup_zero=true");
}
#[test]
fn plan_reuse_collision_publish_boundaries() {
    let bytes=fixture(0,&body(1,&[0x0b]),600);
    let base=SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,base);plan_reuse_release(&mut cache,&mut c,34);
    let begin=c.usage(None).cache_work;hooks(Hooks::default());
    plan_reuse_release(&mut cache,&mut c,546);
    let checks=HOOKS.with(|h|h.get().checks);let credits=c.usage(None).cache_work-begin;
    let published=pi::summary(&cache,546).unwrap();hooks(Hooks::default());finish(cache,c);
    for (is_cancel,n) in [(false,credits as usize),(true,checks)] {
        for ordinal in 0..n {
            let (mut c,mut cache)=new(&bytes,if is_cancel {base} else {SwiftRunBudget{cache_work:begin+ordinal as u64,..base}});
            plan_reuse_release(&mut cache,&mut c,34);let old=pi::summary(&cache,34).unwrap();
            if is_cancel {hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});}
            let f=pin(&mut cache,&mut c,546,None).unwrap_err();hooks(Hooks::default());
            let actual=pi::summary(&cache,546).unwrap();assert!(actual==old||actual==published,"atomic metadata publish ordinal {ordinal}");
            plan_reuse_primary(f,pin(&mut cache,&mut c,34,None).unwrap_err());finish(cache,c);
        }
    }
    println!("PLAN_COLLISION shorter_work={credits} cancellation_checks={checks} atomic=true cleanup_zero=true");
}
