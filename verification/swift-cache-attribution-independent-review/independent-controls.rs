// Independent finite review controls. Synthetic proof/cache operations only.
#[test]
fn independent_attribution_policy_rejections() {
    use super::cache::plan_inspection as review_pi;
    let bytes=fixture(0,&[0,0x0b],600);
    for (limit,site,published) in [(4932,4,0),(5078,12,1)] {
        hooks(Hooks::default());attr_reset();
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_work:limit,..SwiftRunBudget::default()});
        let failure=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!(failure.kind,SwiftRunFailureKind::WorkExhausted);
        assert_eq!(failure.resource,Some(SwiftRunResource::CacheWork));
        assert_eq!((failure.attempted,failure.limit),(limit+1,limit));
        let (totals,rejection,bitmap)=CURRENT_ATTRIBUTION.with(|state| {
            let x=state.borrow();assert_eq!(x.invalid,0);
            (x.totals,x.rejected.unwrap(),x.seen.iter().map(|v|v.count_ones()).sum::<u32>())
        });
        assert_eq!((rejection.site,rejection.requested),(site,1));
        assert_eq!((rejection.function,rejection.offset,rejection.attempted,rejection.limit),
            (failure.function,failure.offset,failure.attempted,failure.limit));
        assert_eq!(totals.credits[site],0);assert_eq!(totals.calls[site],0);
        assert_eq!(totals.credits.iter().sum::<u64>(),limit);
        assert_eq!((totals.completed,totals.distinct,totals.repeated,bitmap),(0,0,0,0));
        assert_eq!(totals.plans[3],published);
        assert_eq!(review_pi::key(&cache,34),if published==1 {Some(34)}else{None});
        // A count plan can exist before completion. The original control owns
        // the sticky failure, so a same-identity retry cannot consume that plan.
        let retry=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!((failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit),
            (retry.stage,retry.kind,retry.code,retry.function,retry.offset,retry.resource,retry.attempted,retry.limit));
        assert_eq!(attr_totals(),totals);
        assert_eq!(CURRENT_ATTRIBUTION.with(|s|s.borrow().rejected),Some(rejection));
        attr_finish(cache,c);
        println!("REVIEW_POLICY limit={limit} rejected_site={site} published_plan={published} bitmap=0 sticky_same_identity=true cleanup_zero=true");
    }
}

#[test]
fn independent_attribution_bitmap_words_and_repeated_conflict() {
    hooks(Hooks::default());attr_reset();
    let bytes=fixture(0,&[0,0x0b],1100);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    for f in [63,64,127] {attr_one(&mut cache,&mut c,f);}
    CURRENT_ATTRIBUTION.with(|s| {
        let x=s.borrow();assert_eq!(x.seen[0],1u64<<63);
        assert_eq!(x.seen[1],1 | (1u64<<63));
        assert_eq!((x.totals.distinct,x.totals.repeated),(3,0));
    });
    // Evict those IR entries, then overwrite only the 63 count-plan cell.
    for f in 200..264 {attr_one(&mut cache,&mut c,f);}
    let before=attr_totals();attr_one(&mut cache,&mut c,575);
    let first=attr_diff(attr_totals(),before);
    assert_eq!(first.plans,[0,1,0,1]);assert_eq!(first.scan_credits,[4,0]);
    assert_eq!(first.build_credits,[5,0]);assert_eq!((first.distinct,first.repeated),(1,0));
    let before=attr_totals();attr_one(&mut cache,&mut c,63);
    let repeated=attr_diff(attr_totals(),before);
    assert_eq!(repeated.plans,[0,1,0,1]);assert_eq!(repeated.scan_credits,[0,4]);
    assert_eq!(repeated.scan_published,[0,1]);assert_eq!(repeated.build_credits,[0,5]);
    assert_eq!((repeated.distinct,repeated.repeated),(0,1));
    CURRENT_ATTRIBUTION.with(|s| {
        let x=s.borrow();assert_eq!(x.seen[0],1u64<<63);
        assert_eq!(x.seen[1],1 | (1u64<<63));assert_eq!(x.invalid,0);
    });
    attr_finish(cache,c);
    println!("REVIEW_BITMAP same_word_and_adjacent_word=true first_scan=4 repeated_scan=4 first_build=5 repeated_build=5 completed_bit_persists_across_eviction=true cleanup_zero=true");
}

#[test]
fn independent_attribution_invalid_output_preserves_failure() {
    let bytes=fixture(0,&[0,0x0b],600);
    let mut clean_failure=None;
    for mode in 0..4 {
        hooks(Hooks::default());attr_reset();
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_work:5078,..SwiftRunBudget::default()});
        if mode==1 {CURRENT_ATTRIBUTION.with(|s|s.borrow_mut().site(255));}
        if mode==2 {CURRENT_ATTRIBUTION.with(|s|s.borrow_mut().totals.credits[1]=u64::MAX);}
        let failure=pin(&mut cache,&mut c,34,None).unwrap_err();
        if let Some(original)=clean_failure {
            let original:SwiftRunFailure=original;
            assert_eq!((original.stage,original.kind,original.code,original.function,original.offset,original.resource,original.attempted,original.limit),
                (failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit));
        } else {clean_failure=Some(failure);}
        let work=c.usage(None).cache_work;
        let mut partial=0;
        let invalid=CURRENT_ATTRIBUTION.with(|s| {
            let mut x=s.borrow_mut();let mut out=AttributionText::new(if mode==3 {64}else{ATTR_OUTPUT});
            let okay=attr_format(&mut x,&mut out);
            // Illustrative bounded caller contract only: a false return drops
            // the partial payload, and an invalid snapshot is not attribution.
            let usable=if okay && x.invalid==0 {Some(&out.bytes[..out.len])}else{None};
            if mode==0 {assert!(usable.is_some());}
            else {assert!(usable.is_none());}
            if mode==3 {assert!(!okay);assert!(out.len>0 && out.len<=64);partial=out.len;}
            x.invalid
        });
        assert_eq!(invalid,match mode {0=>0,1=>ATTR_CONTEXT,2=>ATTR_OVERFLOW,_=>ATTR_OUTPUT_OVERFLOW});
        let retry=pin(&mut cache,&mut c,35,None).unwrap_err();
        assert_eq!((failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit),
            (retry.stage,retry.kind,retry.code,retry.function,retry.offset,retry.resource,retry.attempted,retry.limit));
        assert_eq!(c.usage(None).cache_work,work);
        assert_eq!(cache.usage().decodes,0);
        attr_finish(cache,c);
        println!("REVIEW_INVALID mode={mode} invalid={invalid} partial_discarded_bytes={partial} original_failure=WorkExhausted original_attempted=5079 original_limit=5078 sticky_failure_preserved=true cleanup_zero=true");
    }
}
