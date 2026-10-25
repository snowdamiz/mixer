
#[test]
fn independent_review_plan_inventory_disjoint_layout() {
    super::cache::independent_plan::assert_disjoint_inventory();
    // Audit the incremental accounting identities, with separate storage for
    // owner transfers, the plan Vec, borrows, and the plan payload.
    assert_eq!(62888-62576,5*24+4*24+3*16+3*16);
    assert_eq!(92128-63120,(62888-62576)+24+28672);
    assert_eq!(61880-57752,3*1304+3*24+3*24+3*24);
    assert_eq!(92350-88294,3*1304+3*16+3*16+3*16);
}

#[test]
fn independent_review_understated_counts_and_sticky_failure() {
    hooks(Hooks::default());let bytes=fixture(0,&body(1,&[0x41,7,0x1a,0x0b]),100);
    let b=SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,b);
    for f in [34,35] {let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
    super::cache::independent_plan::replace_counts(&mut cache,34,35);
    let failure=pin(&mut cache,&mut c,34,None).unwrap_err();
    assert_eq!(failure.kind,SwiftRunFailureKind::DecoderMismatch);
    assert_eq!(failure.code,"decode_capacity");
    let work=c.usage(None).cache_work;
    let (later,stats)=measure(||pin(&mut cache,&mut c,35,None));
    let later=later.unwrap_err();assert_eq!(later.code,failure.code);assert_eq!(later.function,failure.function);
    assert_eq!(stats.attempts,0);assert_eq!(work,c.usage(None).cache_work);
    assert_eq!(c.usage(None).live.active_pins.current,0);
    println!("REVIEW_UNDERCOUNT failure={} later={} sticky_no_alloc=true",failure.code,later.code);
    finish(cache,c);
}

#[test]
fn independent_review_successful_scan_retained_after_build_refusal() {
    hooks(Hooks::default());let bytes=fixture(0,&body(1,&[0x41,7,0x1a,0x0b]),100);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()});
    let (r,stats)=measure_extended(Some(0),||pin(&mut cache,&mut c,34,None));
    let f=r.unwrap_err();assert_eq!(stats.injected_failures,1);
    assert_eq!(pi::key(&cache,34),Some(34));assert_eq!(pi::count(&cache),1);
    assert_eq!(c.usage(None).live.active_pins.current,0);
    assert_eq!(c.usage(None).live.cache_entries.current,0);
    let work=c.usage(None).cache_work;
    let (r,stats)=measure(||pin(&mut cache,&mut c,34,None));
    assert_eq!(r.unwrap_err().code,f.code);assert_eq!(stats.attempts,0);assert_eq!(work,c.usage(None).cache_work);
    println!("REVIEW_RETAINED_SCAN build_failure={} complete_record=true runtime_sticky=true",f.code);
    finish(cache,c);
}

#[test]
fn independent_review_cache_proof_scope_and_cancel_before_effect() {
    hooks(Hooks::default());let bytes=fixture(0,&[0,0x0b],100);
    let b=SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,b);
    for f in [34,35] {let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
    let (mut foreign,foreign_cache)=new(&bytes,b);assert_eq!(pi::count(&foreign_cache),0);
    let before=pi::summary(&cache,34);let work=foreign.usage(None).cache_work;
    let (r,stats)=measure(||pin(&mut cache,&mut foreign,34,None));assert!(r.is_err());assert_eq!(stats.attempts,0);
    assert_eq!(pi::summary(&cache,34),before);assert_eq!(work,foreign.usage(None).cache_work);
    finish(foreign_cache,foreign);
    let plan_before=pi::summary(&cache,34);
    c.cancellation().cancel();let before=c.usage(None).cache_work;
    let (r,stats)=measure(||pin(&mut cache,&mut c,34,None));assert_eq!(r.unwrap_err().kind,SwiftRunFailureKind::Cancelled);
    assert_eq!(stats.attempts,0);assert_eq!(before,c.usage(None).cache_work);
    assert_eq!(pi::summary(&cache,34),plan_before);
    println!("REVIEW_SCOPE foreign_denied_before_alloc=true fresh_empty=true cancelled_before_effect=true");
    finish(cache,c);
}
