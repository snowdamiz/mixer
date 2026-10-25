// Independent graph walk: a set of actual (slot, identity) pairs must equal
// every link reachable across all buckets; every absent slot must have no link.
fn independent_review_extra(cache: &SwiftFunctionCache) {
    let bytes=inspection::resident_index(cache);
    assert_eq!(bytes.len(),192);
    let actual=inspection::elision_slots(cache);
    let mut observed=std::collections::BTreeSet::new();
    let expected:std::collections::BTreeSet<_>=actual.iter().filter(|s|s[1]!=u64::MAX).map(|s|(s[0] as usize,s[1])).collect();
    for b in 0..128 {
        let mut node=bytes[b];
        let mut visited=0;
        while node!=0 {
            visited+=1;assert!(visited<=64);
            let s=usize::from(node-1);assert!(s<actual.len());
            let f=actual[s][1];assert_ne!(f,u64::MAX);
            assert_eq!(((f.wrapping_mul(2654435769) & 0xffff_ffff)/33554432) as usize,b);
            assert!(observed.insert((s,f)));
            node=bytes[128+s];
        }
    }
    assert_eq!(observed,expected);
    for s in 0..64 {if s>=actual.len() || actual[s][1]==u64::MAX {assert_eq!(bytes[128+s],0);}}
}
fn independent_review_zero(mut c: RuntimeControl) {
    let u=c.finish_owned_cleanup(None);
    assert_eq!(u.reservations.combined.current,0);
    assert_eq!(u.reservations.live_tickets,0);
    assert_eq!(u.live.cache_entries.current,0);
    assert_eq!(u.live.active_pins.current,0);
}
#[test]
fn independent_review_constructor_every_work_prefix_and_cancel_checkpoint() {
    hooks(Hooks::default());
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
    hooks(Hooks::default());
    let cache=construct(&mut c,a,None).unwrap();
    let work=c.usage(None).cache_work;
    let checks=HOOKS.with(|h|h.get().checks);
    hooks(Hooks::default());finish(cache,c);
    for prefix in 0..work {
        hooks(Hooks::default());
        let (mut c,a)=adopt(&bytes,SwiftRunBudget {cache_work:prefix,..SwiftRunBudget::default()});
        let f=construct(&mut c,a,None).err().unwrap();
        assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        assert_eq!(c.usage(None).reservations.cache.current,0);
        independent_review_zero(c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        hooks(Hooks {cancel:Some(ordinal),..Hooks::default()});
        let f=construct(&mut c,a,None).err().unwrap();
        assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);
        hooks(Hooks::default());
        assert_eq!(c.usage(None).reservations.cache.current,0);
        independent_review_zero(c);
    }
    println!("INDEPENDENT_CONSTRUCTOR work_prefixes={work} cancellation_checkpoints={checks} cleanup=zero");
}
#[test]
fn independent_review_match_before_bad_tail_never_bypasses_validation() {
    let bytes=fixture(0,&[0,0x0b],500);
    for code in ["swift_cache_index_slot","swift_cache_index_empty","swift_cache_index_bucket","swift_cache_index_cycle"] {
        hooks(Hooks::default());
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
        // slot0=34, slot1=178, slot2=267, slot3=35; head267 requested.
        for f in [34,178,267,35] {let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
        let replacement=match code {"swift_cache_index_slot"=>255,"swift_cache_index_empty"=>64,"swift_cache_index_bucket"=>4,_=>3};
        inspection::corrupt_index(&mut cache,128,replacement);
        let before=inspection::resident_index(&cache).to_vec();
        let slots=inspection::elision_slots(&cache);
        let usage=cache.usage();
        let (failure,stats)=measure(||pin(&mut cache,&mut c,267,None).unwrap_err());
        assert_eq!(failure.code,code);assert_eq!(stats.attempts,0);
        assert_eq!(cache.usage(),usage);assert_eq!(inspection::elision_slots(&cache),slots);assert_eq!(inspection::resident_index(&cache),before);
        assert_eq!(c.usage(None).live.active_pins.current,0);
        assert_eq!(pin(&mut cache,&mut c,35,None).unwrap_err(),failure);
        finish(cache,c);
    }
    println!("INDEPENDENT_TAIL matched_head=267 bad_tail_cases=4 no_publication=true cleanup=zero");
}
fn independent_review_multi_seed(bytes:&[u8],budget:SwiftRunBudget)->(RuntimeControl,SwiftFunctionCache) {
    hooks(Hooks::default());let (mut c,mut cache)=new(bytes,budget);
    for f in 35..39 {let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
    (c,cache)
}
fn independent_review_coherent(cache:&SwiftFunctionCache,c:&RuntimeControl) {
    independent_review_extra(cache);
    let actual=inspection::elision_slots(cache);
    let live=actual.iter().filter(|s|s[1]!=u64::MAX).count();
    assert_eq!(c.usage(None).live.cache_entries.current,live);
    assert_eq!(c.usage(None).live.active_pins.current,0);
    assert_eq!(cache.usage().active_pins,0);
    assert_eq!(cache.usage().construction_bytes,0);
    assert_eq!(c.usage(None).reservations.cache.current,cache.usage().fixed_reserved+cache.usage().resident_bytes);
}
#[test]
fn independent_review_multiple_eviction_prefixes_and_checkpoints() {
    let mut helper=vec![0];helper.extend([1;10]);helper.push(0x0b);
    let bytes=fixture(0,&helper,100);
    let initial=SwiftRunBudget {cache_entries:4,..SwiftRunBudget::default()};
    let (c,cache)=new(&bytes,initial);
    let fixed=cache.usage().fixed_reserved;finish(cache,c);
    let budget=SwiftRunBudget {cache_bytes:fixed+11*size_of::<crate::experimental::cache::DecodedInstruction>(),..initial};
    let (mut c,mut cache)=independent_review_multi_seed(&bytes,budget);
    let base=c.usage(None).cache_work;
    hooks(Hooks::default());
    let p=pin(&mut cache,&mut c,34,None).unwrap();
    let cost=c.usage(None).cache_work-base;
    let checks=HOOKS.with(|h|h.get().checks);
    hooks(Hooks::default());
    assert_eq!(cache.usage().evictions,4);
    cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    assert_eq!(c.usage(None).reservations.cache.current,budget.cache_bytes);
    independent_review_coherent(&cache,&c);finish(cache,c);
    let mut observed_evictions=std::collections::BTreeSet::new();
    for prefix in 0..cost {
        let (mut c,mut cache)=independent_review_multi_seed(&bytes,SwiftRunBudget {cache_work:base+prefix,..budget});
        let f=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        independent_review_coherent(&cache,&c);
        observed_evictions.insert(cache.usage().evictions);
        assert_eq!(pin(&mut cache,&mut c,34,None).unwrap_err(),f);
        finish(cache,c);
    }
    for ordinal in 0..checks {
        let (mut c,mut cache)=independent_review_multi_seed(&bytes,budget);
        hooks(Hooks {cancel:Some(ordinal),..Hooks::default()});
        let f=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);hooks(Hooks::default());
        independent_review_coherent(&cache,&c);
        finish(cache,c);
    }
    assert_eq!(observed_evictions,std::collections::BTreeSet::from([0,1,2,3,4]));
    println!("INDEPENDENT_MULTI work_prefixes={cost} cancellation_checkpoints={checks} partial_evictions={observed_evictions:?} cleanup=zero");
}
