// Diagnosis-only controls on the actual copied cache and original composed owner.
#[test]
fn diagnosis_original_owner_ticket_headroom_and_zero_cleanup() {
    hooks(Hooks::default());
    let bytes=fixture(0,&[0,0x0b],100);
    let mut pair=Some(adopt(&bytes,SwiftRunBudget::default()));
    let mut owner=super::execution_tests::construct_owned(&mut pair).unwrap_or_else(|_|panic!("owner construction refused"));
    assert!(pair.is_none());
    let constructed=owner.control.as_ref().unwrap().usage(owner.wasi.as_ref().map(AccountedWasi::usage));
    for f in 34..98 {
        let cache=owner.cache.as_mut().unwrap();
        let c=owner.control.as_mut().unwrap();
        let w=owner.wasi.as_ref().unwrap();
        let p=pin(cache,c,f,Some(w)).unwrap();
        cache.release(p,c,Some(w)).map_err(|e|e.failure).unwrap();
    }
    let c=owner.control.as_mut().unwrap();
    let w=owner.wasi.as_ref().unwrap();
    let full=c.usage(Some(w.usage()));
    assert_eq!(full.live.cache_entries.current,64);
    assert_eq!(MAX_RESERVATION_TICKETS,86);
    let mut held=Vec::new();
    let mut accepted=0;
    let refusal=loop {
        match c.admit_with_wasi(SwiftReservationCategory::Cache,0,cache_cursor(),Some(w.usage())) {
            Ok(t)=>{held.push(t);accepted+=1;assert!(accepted<=1);},
            Err(f)=>break f,
        }
    };
    assert_eq!(refusal.resource,Some(SwiftRunResource::TicketInventory));
    assert_eq!(refusal.attempted,87);
    assert_eq!(refusal.limit,86);
    for t in held {c.drop_reserved_with_wasi((),t,Some(w.usage())).unwrap();}
    println!("DIAG_OWNER constructed={} resident64={} accepted_transient={} failure_attempted={} fixed={} execution_header={} execution_construction={} execution_cleanup={} execution_active={} execution_final={}",constructed.reservations.live_tickets,full.reservations.live_tickets,accepted,refusal.attempted,owner.cache.as_ref().unwrap().usage().fixed_reserved,super::execution::execution_header_bytes().unwrap(),super::execution::construction_bytes().unwrap(),super::execution::CONSTRUCTION_POSITIVE_CLEANUP_BYTES,super::execution::CONSTRUCTION_POSITIVE_ACTIVE_BYTES,super::execution::CONSTRUCTION_POSITIVE_FINAL_BYTES);
    let mut owned=Some(owner);
    let mut returned=Some(super::execution::SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail=returned.take().unwrap().unwrap_or_else(|e|panic!("cleanup {}",e.code));
    let (mut failure,mut usage)=(None,None);
    tail.complete((owned,returned),&mut failure,&mut usage);
    let u=usage.unwrap();
    let after=failure.unwrap();
    assert_eq!(after.code,refusal.code);assert_eq!(after.resource,refusal.resource);
    assert_eq!(after.attempted,87);assert_eq!(after.limit,86);
    assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);
    assert_eq!(u.cleanup_invariant,None);
    assert_eq!([u.live.cache_entries.current,u.live.active_pins.current,u.live.frames.current,u.live.values.current,u.live.controls.current,u.live.memory_pages.current],[0;6]);
    println!("DIAG_OWNER_CLEANUP combined={} tickets={} live_categories=[0,0,0,0,0,0] first_failure_preserved=true invariant={:?}",u.reservations.combined.current,u.reservations.live_tickets,u.cleanup_invariant);
    super::cache::diagnosis_layout_report();
}

#[test]
fn diagnosis_constructor_every_work_prefix_cancel_and_header_lifetime() {
    hooks(Hooks::default());
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
    hooks(Hooks::default());
    let (cache,alloc)=measure(||construct(&mut c,a,None).unwrap());
    let work=c.usage(None).cache_work;
    let checks=HOOKS.with(|h|h.get().checks);
    assert_eq!(work,832);
    assert_eq!(alloc.attempts,4);
    assert_eq!(alloc.allocated_bytes,26304);
    assert_eq!(inspection::resident_index(&cache),[0;192]);
    hooks(Hooks::default());
    let mut owned=Some(cache);
    let header=cache_header_bytes().unwrap();
    let (tail,freed)=measure(||SwiftFunctionCache::cleanup(&mut owned,&mut c,None).unwrap());
    assert_eq!(freed.attempts,0);
    assert!(freed.freed_bytes>=26304);
    let mut outcome=None;
    // Header remains charged after the real Vec payload is already destroyed.
    assert_eq!(super::cache::diagnosis_tail_cache_reserved(&tail),header);
    tail.complete(owned,&mut outcome);
    assert!(outcome.is_none());
    let u=c.finish_owned_cleanup(None);
    assert_eq!(u.reservations.combined.current,0);
    assert_eq!(u.reservations.live_tickets,0);
    for prefix in 0..work {
        hooks(Hooks::default());
        let (mut c,a)=adopt(&bytes,SwiftRunBudget{cache_work:prefix,..SwiftRunBudget::default()});
        let f=construct(&mut c,a,None).err().unwrap();
        assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        assert_eq!(c.usage(None).reservations.cache.current,0);
        let u=c.finish_owned_cleanup(None);
        assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});
        let f=construct(&mut c,a,None).err().unwrap();
        assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);hooks(Hooks::default());
        assert_eq!(c.usage(None).reservations.cache.current,0);
        let u=c.finish_owned_cleanup(None);
        assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);
    }
    println!("DIAG_CONSTRUCTOR work_prefixes={work} cancellation_checkpoints={checks} allocations={} payload={} freed_before_header={} cleanup=zero",alloc.attempts,alloc.allocated_bytes,freed.freed_bytes);
}
