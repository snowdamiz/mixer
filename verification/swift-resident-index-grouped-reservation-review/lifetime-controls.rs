// These tests call the actual selected cache, allocator observer and ledger.
fn grouped_review_zero(mut c:RuntimeControl, first:Option<SwiftRunFailure>) {
    if let Some(f)=first {
        let saved=c.record_cleanup(None).unwrap();
        assert_eq!((saved.code,saved.kind,saved.resource,saved.attempted,saved.limit),(f.code,f.kind,f.resource,f.attempted,f.limit));
    }
    let u=c.finish_owned_cleanup(None);
    assert_eq!((u.reservations.combined.current,u.reservations.live_tickets),(0,0));
    assert_eq!([u.live.cache_entries.current,u.live.active_pins.current,u.live.frames.current,u.live.values.current,u.live.controls.current,u.live.memory_pages.current],[0;6]);
    assert_eq!(u.cleanup_invariant,None);
}
#[test]
fn grouped_review_header_payload_and_completion_order() {
    use super::cache::grouped_review as r;
    hooks(Hooks::default());
    let input=fixture(0,&[0,0x0b],100);
    let (mut c,a)=adopt(&input,SwiftRunBudget::default());
    let (cache,requests)=measure(||construct(&mut c,a,None).unwrap());
    let work=c.usage(None).cache_work;
    let checkpoints=HOOKS.with(|h|h.get().checks);
    let header=cache_header_bytes().unwrap();
    let exclusive=size_of::<SwiftFunctionCache>()-size_of::<ValidatedSwiftReactor>();
    assert_eq!(header,exclusive.checked_add(cache_cleanup_temporary_bytes().unwrap()).unwrap().checked_add(192).unwrap());
    assert_eq!(requests.attempts,4);
    assert_eq!(requests.reallocations,0);
    assert_eq!(requests.allocated_bytes,26304);
    assert_eq!(work,832);
    assert_eq!(checkpoints,851);
    assert_eq!(inspection::resident_index(&cache),[0;192]);
    assert_eq!(cache.usage().fixed_reserved,header+requests.allocated_bytes-192);
    assert_eq!(cache.usage().fixed_reserved,c.usage(None).reservations.cache.current);
    r::reset(true);
    let mut owned=Some(cache);
    let (tail,cleanup)=measure(||SwiftFunctionCache::cleanup(&mut owned,&mut c,None).unwrap());
    assert!(owned.is_none());
    assert_eq!(cleanup.attempts,0);
    let observed=r::report();
    assert_eq!((observed.before,observed.after,observed.capacity,observed.length,observed.reserved,observed.freed_index),(1,1,192,192,header,192));
    assert_eq!(r::tail_usage(&tail).reservations.cache.current,header);
    r::expect_storage();
    let mut outcome=None;
    let (_,completed)=measure(||tail.complete((owned,r::ReturnedStorage),&mut outcome));
    assert!(outcome.is_none());
    let observed=r::report();
    assert!(observed.storage_dropped);
    assert_eq!((observed.completion,observed.completion_reserved),(1,header));
    assert_eq!(completed.attempts,0);
    assert_eq!(c.usage(None).cache_work,work);
    r::reset(false);
    grouped_review_zero(c,None);
    println!("REVIEW_PAYLOAD header={header} owner={} exclusive={exclusive} cleanup={} fixed={} allocations=4 payload=26304 index=192 work=832 checkpoints=851 index_freed_while_header_charged=192 caller_storage_dropped_before_header_refund=true",size_of::<SwiftFunctionCache>(),cache_cleanup_temporary_bytes().unwrap(),header+26304-192);
}
#[test]
fn grouped_review_all_partial_failures_keep_index_charged() {
    use super::cache::grouped_review as r;
    let input=fixture(0,&[0,0x0b],100);
    let mut allocated_prefixes=0;
    for budget in 0..832 {
        hooks(Hooks::default());
        let (mut c,a)=adopt(&input,SwiftRunBudget{cache_work:budget,..SwiftRunBudget::default()});
        r::reset(true);
        let (result,_)=measure(||construct(&mut c,a,None));
        let failure=result.err().unwrap();
        assert_eq!(failure.resource,Some(SwiftRunResource::CacheWork));
        let v=r::report();
        assert_eq!((v.before,v.after),(1,1));
        assert_eq!(v.capacity,if budget>=640 {192}else{0});
        if v.capacity!=0 {allocated_prefixes+=1;assert_eq!(v.reserved,cache_header_bytes().unwrap());}
        r::reset(false);
        grouped_review_zero(c,Some(failure));
    }
    let mut allocated_cancels=0;
    let mut preflight_cancels=0;
    for ordinal in 0..851 {
        hooks(Hooks::default());
        let (mut c,a)=adopt(&input,SwiftRunBudget::default());
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});
        r::reset(true);
        let (result,requests)=measure(||construct(&mut c,a,None));
        let failure=result.err().unwrap();
        assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);
        let v=r::report();
        if v.before==0 {
            preflight_cancels+=1;
            assert_eq!(v.after,0);
            assert_eq!(requests.attempts,0);
        } else { assert_eq!((v.before,v.after),(1,1)); }
        if v.capacity!=0 {allocated_cancels+=1;assert_eq!(v.capacity,192);assert_eq!(v.reserved,cache_header_bytes().unwrap());}
        r::reset(false);hooks(Hooks::default());
        grouped_review_zero(c,Some(failure));
    }
    let (mut base,p)=adopt(&input,SwiftRunBudget::default());
    let (_,proof_drop)=measure(||base.drop_proof(p).unwrap());
    grouped_review_zero(base,None);
    for ordinal in 0..4 {
        hooks(Hooks::default());
        let (mut c,a)=adopt(&input,SwiftRunBudget::default());
        r::reset(true);
        let (result,allocation)=measure_extended(Some(ordinal),||construct(&mut c,a,None));
        let failure=result.err().unwrap();
        assert_eq!(allocation.injected_failures,1);
        assert_eq!(allocation.freed_bytes-proof_drop.freed_bytes,allocation.allocated_bytes-allocation.last_size);
        assert_eq!(r::report().capacity,0);
        r::reset(false);grouped_review_zero(c,Some(failure));
    }
    hooks(Hooks::default());
    let (mut c,a)=adopt(&input,SwiftRunBudget{cache_bytes:cache_header_bytes().unwrap()-1,..SwiftRunBudget::default()});
    r::reset(true);
    let (result,requests)=measure(||construct(&mut c,a,None));
    let failure=result.err().unwrap();
    assert_eq!(failure.kind,SwiftRunFailureKind::CategoryExhausted);
    assert_eq!(requests.attempts,0);
    assert_eq!(r::report().reserved,0);
    assert_eq!(r::report().capacity,0);
    r::reset(false);grouped_review_zero(c,Some(failure));
    println!("REVIEW_PARTIAL work_prefixes=832 allocated_prefixes={allocated_prefixes} cancel_checkpoints=851 preflight_cancels={preflight_cancels} allocated_cancels={allocated_cancels} allocation_failure_ordinals=0..3 header_refusal_allocations=0 first_failure_preserved=true cleanup_zero=true");
}
