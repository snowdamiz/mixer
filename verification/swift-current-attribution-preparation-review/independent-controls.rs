// Independent actual-cache controls; finite synthetic proof/cache operations only.
fn review_full_finish(cache:SwiftFunctionCache,mut control:RuntimeControl,sink:&mut FullTestSink) {
    let decodes=cache.usage().decodes;let work=control.usage(None).cache_work;
    let _=cleanup(cache,&mut control,None);let u=control.finish_owned_cleanup(None);
    assert_eq!(u.cache_work,work);assert_eq!(u.cleanup_invariant,None);
    assert_eq!((u.reservations.retained_source.current,u.reservations.retained_metadata.current,u.reservations.cache.current,u.reservations.state.current,u.reservations.wasi.current,u.reservations.shared.current,u.reservations.construction.current,u.reservations.combined.current,u.reservations.live_tickets),(0,0,0,0,0,0,0,0,0));
    assert_eq!((u.live.cache_entries.current,u.live.active_pins.current,u.live.frames.current,u.live.values.current,u.live.controls.current,u.live.memory_pages.current),(0,0,0,0,0,0));
    assert!(full_snapshot_to(FullAttributionPhase::FinalCleanup,u.cache_work,decodes,true,ATTR_OUTPUT,sink));
}
#[test]
fn independent_full_attribution_cancel_and_output_failures() {
    let bytes=fixture(0,&[0,0x0b],600);let mut original=None;
    for mode in 0..4 {
        hooks(Hooks::default());full_attribution_begin();
        let (mut control,mut cache)=new(&bytes,SwiftRunBudget::default());let mut sink=FullTestSink::new();
        assert!(full_snapshot_to(FullAttributionPhase::Constructed,control.usage(None).cache_work,0,false,ATTR_OUTPUT,&mut sink));
        control.cancellation().cancel();let failure=pin(&mut cache,&mut control,34,None).unwrap_err();
        assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);
        if let Some(previous)=original {let previous:SwiftRunFailure=previous;assert_eq!((previous.stage,previous.kind,previous.code,previous.function,previous.offset,previous.resource,previous.attempted,previous.limit),(failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit));}else{original=Some(failure);}
        let work=control.usage(None).cache_work;let totals=attr_totals();
        assert!(CURRENT_ATTRIBUTION.with(|s|s.borrow().rejected.is_none()));
        if mode==2 {CURRENT_ATTRIBUTION.with(|s|s.borrow_mut().site(255));}
        if mode==3 {let mut failed=FullTestSink::new();failed.fail=true;assert!(!full_snapshot_to(FullAttributionPhase::Initialize,work,0,false,ATTR_OUTPUT,&mut failed));assert_eq!(failed.len,0);}
        else {assert!(full_snapshot_to(FullAttributionPhase::Initialize,work,0,false,if mode==1{1}else{ATTR_OUTPUT},&mut sink));}
        let retry=pin(&mut cache,&mut control,35,None).unwrap_err();
        assert_eq!((failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit),(retry.stage,retry.kind,retry.code,retry.function,retry.offset,retry.resource,retry.attempted,retry.limit));
        assert_eq!(control.usage(None).cache_work,work);assert_eq!(attr_totals(),totals);
        review_full_finish(cache,control,&mut sink);
        if mode==0 {assert!(sink.text().lines().all(|l|l.contains("\"valid\":true")));}
        else {let final_line=sink.text().lines().last().unwrap();assert!(final_line.contains("\"valid\":false") && final_line.contains("\"payload\":null"));}
        if mode==1 {assert!(sink.text().contains("\"formatted\":false,\"observer_invalid\":8"));}
        if mode==3 {assert!(sink.text().contains("\"prior_write_failed\":true"));}
        println!("REVIEW_FULL_CANCEL mode={mode} original=Cancelled sticky_original=true rejected_debit_absent=true original_work_unchanged=true guest_instructions=0 cleanup_zero=true");
    }
}
#[test]
fn independent_full_attribution_new_lifetimes_reset_after_consumption() {
    let bytes=fixture(0,&[0,0x0b],600);
    for function in [63,64] {
        hooks(Hooks::default());full_attribution_begin();
        let (mut control,mut cache)=new(&bytes,SwiftRunBudget::default());let mut sink=FullTestSink::new();
        assert!(full_snapshot_to(FullAttributionPhase::Constructed,control.usage(None).cache_work,0,false,ATTR_OUTPUT,&mut sink));
        assert_eq!(attr_totals().completed,0);attr_one(&mut cache,&mut control,function);
        let totals=attr_totals();assert_eq!((totals.completed,totals.distinct,totals.repeated),(1,1,0));
        CURRENT_ATTRIBUTION.with(|s| {let state=s.borrow();assert_eq!(state.seen.iter().map(|w|w.count_ones()).sum::<u32>(),1);assert_eq!(state.seen[function as usize/64],1u64<<(function%64));});
        assert!(full_snapshot_to(FullAttributionPhase::BeforeCleanup,control.usage(None).cache_work,1,false,ATTR_OUTPUT,&mut sink));
        review_full_finish(cache,control,&mut sink);assert_eq!(attr_totals(),totals);
        assert_eq!(sink.text().lines().count(),3);assert!(sink.text().lines().all(|l|l.contains("\"valid\":true") && l.contains("\"reset_count\":1")));
        FULL_ATTRIBUTION_LIFETIME.with(|s|{let state=s.borrow();assert!(!state.active);assert_eq!((state.reset_count,state.emissions,state.invalid),(1,3,0));});
        println!("REVIEW_FULL_LIFETIME function={function} first_decode=1 repeated_decode=0 reset=1 snapshots=3 final_bitmap_preserved=true guest_instructions=0 cleanup_zero=true");
    }
}
