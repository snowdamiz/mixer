// Same host instrumentation on both copies; only expected cold priority differs.
use super::cache::count_candidate_inspection as ci;
#[derive(Clone,Copy,Debug)]
struct CountCheckpoint { work:u64, construction:usize, cache:usize, combined:usize,tickets:usize,pins:usize,entries:usize,step:usize }
const COUNT_EMPTY:CountCheckpoint=CountCheckpoint {work:0,construction:0,cache:0,combined:0,tickets:0,pins:0,entries:0,step:0};
thread_local! { static COUNT_OBSERVE:Cell<(bool,usize,[CountCheckpoint;128])>=const {Cell::new((false,0,[COUNT_EMPTY;128]))}; }
fn count_candidate_checkpoint(control:&RuntimeControl) {
    COUNT_OBSERVE.with(|s| { let (enabled,n,mut trace)=s.get();if enabled {
        assert!(n<trace.len());let u=control.usage(None);
        trace[n]=CountCheckpoint { work:u.cache_work,construction:u.reservations.construction.current,cache:u.reservations.cache.current,
          combined:u.reservations.combined.current,tickets:u.reservations.live_tickets,pins:u.live.active_pins.current,
          entries:u.live.cache_entries.current,step:HOOKS.with(|h|h.get().step as usize) };
        s.set((enabled,n+1,trace));
    }});
}
fn count_priority(cache:&SwiftFunctionCache,f:u32)->u64 { ci::rank_state(cache).into_iter().find(|r|r.0==f).unwrap().2 }
fn count_seed(bytes:&[u8],budget:SwiftRunBudget,reused:bool)->(RuntimeControl,SwiftFunctionCache) {
    let (mut c,mut cache)=new(bytes,budget);
    if reused {cost_trace_release(&mut cache,&mut c,34);cost_trace_release(&mut cache,&mut c,35);}
    (c,cache)
}
#[test]
fn count_candidate_shape_hit_trace_and_reservation() {
    hooks(Hooks::default());
    let bytes=fixture(0,&[0,0x0b],100);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    cost_trace_release(&mut cache,&mut c,34);
    println!("COUNT_SHAPE {:?}",ci::common_shape());
    let start=c.usage(None).cache_work;let before=cache.usage();
    let (_,alloc)=measure(||for _ in 0..256 {cost_trace_release(&mut cache,&mut c,34)});
    assert_eq!(c.usage(None).cache_work-start,2048);assert_eq!(alloc.attempts,0);assert_eq!(alloc.allocated_bytes,0);
    assert_eq!(cache.usage().decodes,before.decodes);assert_eq!(cache.usage().evictions,before.evictions);
    hooks(Hooks::default());COUNT_OBSERVE.with(|s|s.set((true,0,[COUNT_EMPTY;128])));
    let start=c.usage(None).cache_work;cost_trace_release(&mut cache,&mut c,34);
    let (_,n,mut trace)=COUNT_OBSERVE.with(|s|{let x=s.get();s.set((false,0,[COUNT_EMPTY;128]));x});
    for t in trace.iter_mut().take(n) {t.work-=start;println!("COUNT_HIT_CHECKPOINT {t:?}");}
    println!("COUNT_HIT {{\"work256\":2048,\"allocations\":0,\"allocationBytes\":0,\"checkpoints\":{n},\"operationBytes\":{}}}",cache_operation_bytes().unwrap());
    finish(cache,c);
}
#[test]
fn count_candidate_original_observation_pin_borrow_and_identity() {
    let helper=body(1,&[0x0b]);let bytes=fixture(0,&helper,600);
    let budget=SwiftRunBudget { cache_entries:1,..SwiftRunBudget::default() };
    let (mut c,mut cache)=new(&bytes,budget);
    for f in [34,546,34] {cost_trace_release(&mut cache,&mut c,f);assert_eq!(count_priority(&cache,f),if COUNT_POLICY {0}else{c.usage(None).cache_work});}
    cost_trace_release(&mut cache,&mut c,35);cost_trace_release(&mut cache,&mut c,34);
    assert_eq!(count_priority(&cache,34),c.usage(None).cache_work);finish(cache,c);
    for field in 0..4 {
        let (mut c,mut cache)=count_seed(&bytes,budget,true);pi::corrupt(&mut cache,34,field);
        let e=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!(e.code,if field<3 {"swift_plan_identity"}else{"decode_count_mismatch"});assert_eq!(c.usage(None).live.active_pins.current,0);
        finish(cache,c);
    }
    // Real opaque held pin and the exact underlying instruction allocation survive turnover.
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget {cache_entries:3,..SwiftRunBudget::default()});
    let held=pin(&mut cache,&mut c,34,None).unwrap();let ptr=cache.view(&held,&mut c,None).unwrap().instructions.as_ptr();
    for f in 35..100 {cost_trace_release(&mut cache,&mut c,f);assert_eq!(cache.view(&held,&mut c,None).unwrap().instructions.as_ptr(),ptr);}
    assert_eq!(cache.view(&held,&mut c,None).unwrap().function,34);cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();
    finish(cache,c);
    let (mut c,mut cache)=new(&bytes,budget);let e=ci::bad_scan(&mut cache,&mut c);assert_eq!(e.kind,SwiftRunFailureKind::DecoderMismatch);
    assert_eq!(pi::count(&cache),0);assert_eq!(cache.usage().decodes,0);finish(cache,c);
    println!("COUNT_OWNERS full_identity=4 original_collision=3 held_actual_pin_and_allocation=true failed_real_scan_no_plan=true cleanup_zero=true");
}
#[test]
fn count_candidate_work_cancel_build_publication_all_prefixes() {
    let bytes=fixture(0,&body(1,&[0,0x0e,1,0,0,0x0b]),100);
    let base=SwiftRunBudget {cache_entries:1,..SwiftRunBudget::default()};
    for reused in [false,true] {
        hooks(Hooks::default());let (mut c,mut cache)=count_seed(&bytes,base,reused);
        let before=c.usage(None).cache_work;hooks(Hooks::default());let p=pin(&mut cache,&mut c,34,None).unwrap();
        let checks=HOOKS.with(|h|h.get().checks);let work=c.usage(None).cache_work-before;
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
        let mut scanned_then_failed=0;let mut eviction_prefixes=std::collections::BTreeSet::new();
        for prefix in 0..work {
            hooks(Hooks::default());let (mut c,mut cache)=count_seed(&bytes,SwiftRunBudget {cache_work:before+prefix,..base},reused);
            let old=ci::rank_state(&cache);let e=pin(&mut cache,&mut c,34,None).unwrap_err();
            assert_eq!(e.resource,Some(SwiftRunResource::CacheWork));assert_eq!(c.usage(None).live.active_pins.current,0);
            assert!(!ci::rank_state(&cache).iter().any(|r|r.0==34));
            if pi::key(&cache,34)==Some(34) {scanned_then_failed+=1;}
            eviction_prefixes.insert(cache.usage().evictions);
            let stopped=c.usage(None).cache_work;let r=pin(&mut cache,&mut c,35,None).unwrap_err();plan_reuse_primary(e,r);assert_eq!(c.usage(None).cache_work,stopped);
            if cache.usage().evictions==u64::from(reused) {assert_eq!(ci::rank_state(&cache),old);}
            finish(cache,c);
        }
        assert!(scanned_then_failed>0);
        for ordinal in 0..checks {
            hooks(Hooks::default());let (mut c,mut cache)=count_seed(&bytes,base,reused);hooks(Hooks {cancel:Some(ordinal),..Hooks::default()});
            let e=pin(&mut cache,&mut c,34,None).unwrap_err();hooks(Hooks::default());assert_eq!(e.kind,SwiftRunFailureKind::Cancelled);
            assert_eq!(c.usage(None).live.active_pins.current,0);assert!(!ci::rank_state(&cache).iter().any(|r|r.0==34));finish(cache,c);
        }
        for allocation in 0..3 {
            let (mut c,mut cache)=count_seed(&bytes,base,reused);
            let (r,s)=measure_extended(Some(allocation),||pin(&mut cache,&mut c,34,None));assert!(r.is_err());assert_eq!(s.injected_failures,1);
            assert_eq!(pi::key(&cache,34),Some(34));assert_eq!(c.usage(None).live.active_pins.current,0);finish(cache,c);
        }
        println!("COUNT_PREFIX reused={reused} work={work} cancellation_checks={checks} scanned_then_failed={scanned_then_failed} eviction_prefixes={eviction_prefixes:?} allocation_failures=3 cleanup_zero=true");
    }
}
#[test]
fn count_candidate_changed_memory_admission_boundary() {
    let bytes=fixture(0,&[0,0x0b],100);let (c,cache)=new(&bytes,SwiftRunBudget::default());let resident=c.usage(None).reservations.combined.current;finish(cache,c);
    for operation in [92350usize,112821,112822] {
        let (mut c,cache)=new(&bytes,SwiftRunBudget {combined_bytes:resident+operation,..SwiftRunBudget::default()});
        let (r,a)=measure(||cache.prepare_operation(&mut c,None,cache_cursor()));assert_eq!(a.attempts,0);
        let accepted=match r {Ok(phase)=>{phase.complete(()).unwrap();true},Err(e)=>{assert_eq!(e.kind,SwiftRunFailureKind::CombinedExhausted);false}};
        assert_eq!(accepted,operation>=cache_operation_bytes().unwrap());println!("COUNT_ADMISSION headroom={operation} accepted={accepted} ownOperationBytes={}",cache_operation_bytes().unwrap());finish(cache,c);
    }
}
#[test]
fn count_candidate_phase_and_scan_controls() {
    let bytes=plan_reuse_wide_fixture(&[0,0x0b],1000);
    for (label,old,cycles,expected) in [("phase_old16",16,12,if COUNT_POLICY {81}else{64}), ("phase_old64",64,12,if COUNT_POLICY {128}else{64}), ("phase_old16_long",16,64,if COUNT_POLICY {81}else{64})] {
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
        for _ in 0..3 {for f in 100..100+old {cost_trace_release(&mut cache,&mut c,f)}}
        let start=cache.usage().decodes;
        for _ in 0..cycles {for f in 200..264 {cost_trace_release(&mut cache,&mut c,f)}}
        assert_eq!(cache.usage().decodes-start,expected);println!("COUNT_PHASE {label} decodes={expected}");finish(cache,c);
    }
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    for f in 100..116 {for _ in 0..2 {cost_trace_release(&mut cache,&mut c,f)}}
    for f in 200..840 {cost_trace_release(&mut cache,&mut c,f)}
    let retained=ci::rank_state(&cache).iter().filter(|r|(100..116).contains(&r.0)).count();
    assert_eq!(retained,if COUNT_POLICY {16}else{0});println!("COUNT_SCAN640 retained_hot={retained}");finish(cache,c);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    for _ in 0..3 {for f in 100..164 {cost_trace_release(&mut cache,&mut c,f)}}
    let start=cache.usage().decodes;
    for _ in 0..12 {for f in 612..676 {cost_trace_release(&mut cache,&mut c,f)}}
    assert_eq!(cache.usage().decodes-start,if COUNT_POLICY {128}else{64});println!("COUNT_COLLISION_PHASE decodes={}",cache.usage().decodes-start);finish(cache,c);
}
#[test]
fn count_candidate_three_victims_partial_prefixes_and_real_borrow() {
    hooks(Hooks::default());let mut lengths=vec![0;100];lengths[6]=12;let bytes=cost_trace_fixture(&lengths);
    let base=SwiftRunBudget {cache_entries:4,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,base);let fixed=cache.usage().fixed_reserved;
    cost_trace_release(&mut cache,&mut c,34);let small=cache.usage().resident_bytes;
    cost_trace_release(&mut cache,&mut c,40);let large=cache.usage().resident_bytes-small;finish(cache,c);
    let budget=SwiftRunBudget {cache_bytes:fixed+small+large,..base};
    fn seeded(bytes:&[u8],budget:SwiftRunBudget)->(RuntimeControl,SwiftFunctionCache,SwiftFunctionPin,usize) {
        let (mut c,mut cache)=new(bytes,budget);let held=pin(&mut cache,&mut c,34,None).unwrap();
        let ptr=cache.view(&held,&mut c,None).unwrap().instructions.as_ptr() as usize;
        for f in 35..38 {cost_trace_release(&mut cache,&mut c,f)}(c,cache,held,ptr)
    }
    let (mut c,mut cache,held,ptr)=seeded(&bytes,budget);let before=c.usage(None).cache_work;
    cost_trace_release(&mut cache,&mut c,40);let work=c.usage(None).cache_work-before;
    assert_eq!(cache.usage().evictions,3);assert_eq!(cache.view(&held,&mut c,None).unwrap().instructions.as_ptr() as usize,ptr);
    assert_eq!(ci::rank_state(&cache).len(),2);cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    let mut prefixes=std::collections::BTreeSet::new();
    for prefix in 0..work {
        let (mut c,mut cache,held,ptr)=seeded(&bytes,SwiftRunBudget {cache_work:before+prefix,..budget});
        let e=pin(&mut cache,&mut c,40,None).unwrap_err();assert_eq!(e.resource,Some(SwiftRunResource::CacheWork));
        assert!(!ci::rank_state(&cache).iter().any(|r|r.0==40));prefixes.insert(cache.usage().evictions);
        assert_eq!(cache.view(&held,&mut c,None).unwrap().instructions.as_ptr() as usize,ptr);
        assert_eq!(c.usage(None).live.active_pins.current,1);cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    }
    assert_eq!(prefixes,[0,1,2,3].into_iter().collect());
    println!("COUNT_MULTIVICTIM shorter_work={work} actual_completed_prefixes={prefixes:?} held_pin_and_allocation_preserved=true cleanup_zero=true");
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget {cache_entries:1,..base});let held=pin(&mut cache,&mut c,34,None).unwrap();
    let e=pin(&mut cache,&mut c,35,None).unwrap_err();assert_eq!(e.code,"all_entries_pinned");assert_eq!(pi::key(&cache,35),Some(35));
    assert_eq!(cache.view(&held,&mut c,None).unwrap().function,34);cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
}
#[test]
fn count_candidate_all_capacities_finite_slot_oracle() {
    let bytes=plan_reuse_wide_fixture(&[0,0x0b],1000);let mut transitions=0;
    for capacity in 0..=64 {
        hooks(Hooks::default());let (mut c,mut cache)=new(&bytes,SwiftRunBudget {cache_entries:capacity,..SwiftRunBudget::default()});
        if capacity==0 {assert!(pin(&mut cache,&mut c,100,None).is_err());assert_eq!(pi::key(&cache,100),Some(100));finish(cache,c);continue;}
        let mut slots=vec![None::<(u32,u64)>;capacity];let mut plans=[None::<u32>;512];let mut ordinal=0;let mut seed=17u32;
        for i in 0..384 {
            seed=seed.wrapping_mul(1664525).wrapping_add(1013904223);
            let function=100+(seed%70)+if i%3==0 {512}else{0};ordinal+=1;
            let found=slots.iter().position(|s|s.is_some_and(|r|r.0==function));
            let index=if let Some(index)=found {slots[index]=Some((function,ordinal));index} else {
                let reused=plans[function as usize&511]==Some(function);plans[function as usize&511]=Some(function);
                let index=slots.iter().position(Option::is_none).unwrap_or_else(||(0..capacity).min_by_key(|j|(slots[*j].unwrap().1,*j)).unwrap());
                slots[index]=Some((function,if COUNT_POLICY&&!reused {0}else{ordinal}));index
            };
            cost_trace_release(&mut cache,&mut c,function);let actual=ci::rank_state(&cache);
            assert_eq!(actual.iter().find(|r|r.0==function).unwrap().3,index);
            for (f,pins,time,slot) in &actual {let expected=slots[*slot].unwrap();assert_eq!(*f,expected.0);assert_eq!(*pins,0);assert_eq!(*time==0,expected.1==0);}
            let mut observed:Vec<_>=actual.iter().map(|r|(r.2,r.3,r.0)).collect();observed.sort();
            let mut expected:Vec<_>=slots.iter().enumerate().filter_map(|(i,s)|s.map(|(f,t)|(t,i,f))).collect();expected.sort();
            assert_eq!(observed.iter().map(|r|(r.1,r.2)).collect::<Vec<_>>(),expected.iter().map(|r|(r.1,r.2)).collect::<Vec<_>>());transitions+=1;
        }
        finish(cache,c);
    }
    println!("COUNT_ORACLE capacities=65 transitions={transitions} full_identity_collision_slots_and_order=true cleanup_zero=true");
}
