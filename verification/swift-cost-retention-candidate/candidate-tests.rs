use super::cache::cost_inspection as ci;
#[test]
fn cost_retention_capacities_and_exact_rank_work() {
    for capacity in [0,1,2,3,4,8,63,64] {
        hooks(Hooks::default()); let bytes=fixture(0,&[0,0x0b],100);
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:capacity,..SwiftRunBudget::default()});
        for f in 34..34+capacity as u32 { cost_trace_release(&mut cache,&mut c,f); }
        let before=ci::records(&cache); let work=c.usage(None).cache_work;
        let selected=ci::select(&mut cache,&mut c,&[false;64]);
        assert_eq!(c.usage(None).cache_work-work,1+9*capacity as u64);
        if capacity==0 { assert_eq!(selected.unwrap_err().code,"all_entries_pinned"); }
        else { assert_eq!(selected.unwrap(),0); }
        assert_eq!(ci::records(&cache),before);
        finish(cache,c);
    }
    println!("COST_CAPACITIES capacities=8 work=1+9*eligible selection_readonly=true cleanup=zero");
}
#[test]
fn cost_retention_ratios_ties_extremes_and_fail_closed() {
    for (a,b,want) in [
        ([0,2,4,1],[1,1,2,3],true), // exactratio tie, older wins
        ([1,2,4,1],[0,1,2,1],false), // exactratio+age tie, lowerslot wins
        ([0,u64::MAX,u64::MAX,0],[1,u64::MAX,u64::MAX-1,1],true),
        ([0,u64::MAX,1,0],[1,1,u64::MAX,1],false),
        ([0,1,u64::MAX,0],[1,u64::MAX,1,1],true),
    ] {
        let bytes=fixture(0,&[0,0x0b],100); let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
        assert_eq!(ci::compare(&mut cache,&mut c,a,b),want); finish(cache,c);
    }
    assert_eq!(decode::Counts::test_retention_parts([0,0,0]).estimated_build_work(0),Some(1));
    assert_eq!(decode::Counts::test_retention_parts([2,3,4]).estimated_build_work(5),Some(23));
    assert_eq!(decode::Counts::test_retention_parts([usize::MAX,0,0]).estimated_build_work(0),None);
    assert_eq!(decode::Counts::test_retention_parts([0,0,0]).estimated_build_work(usize::MAX),Some(u64::MAX));
    for corrupt in ["future_age","zero_cost"] {
        let bytes=fixture(0,&[0,0x0b],100); let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:2,..SwiftRunBudget::default()});
        cost_trace_release(&mut cache,&mut c,34); cost_trace_release(&mut cache,&mut c,35);
        ci::metadata(&mut cache,34,if corrupt=="future_age"{u64::MAX}else{0},if corrupt=="zero_cost"{0}else{4});
        let before=ci::records(&cache);
        let f=ci::select(&mut cache,&mut c,&[false;64]).unwrap_err();
        assert_eq!(f.code,if corrupt=="future_age"{"swift_retention_age"}else{"swift_retention_cost"});
        assert_eq!(ci::records(&cache),before); finish(cache,c);
    }
    println!("COST_RATIOS checked_u64_u128_extremes=true exact_ties=true corrupt_metadata_failclosed=true cleanup=zero");
}
#[test]
fn cost_retention_sorted_oracle_pins_and_selected() {
    let mut transitions=0;
    for capacity in [1,2,3,4,8,63,64] {
        hooks(Hooks::default()); let bytes=fixture(0,&[0,0x0b],100);
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:capacity,..SwiftRunBudget::default()});
        let mut held=Vec::new();
        for f in 34..34+capacity as u32 {
            let p=pin(&mut cache,&mut c,f,None).unwrap();
            if f%3==0 { held.push(p); } else { cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap(); }
        }
        for iteration in 0..64 {
            let now=c.usage(None).cache_work;
            for f in 34..34+capacity as u32 { ci::metadata(&mut cache,f,now-(u64::from(f)*17+iteration)%1024,1+(u64::from(f)*13+iteration*7)%4096); }
            let mut plan=[false;64];
            for (i,_,_,_,_,_) in ci::records(&cache) { plan[i]=(i+iteration as usize)%5==0; }
            // Independently sort rational costs using a fixed pre-scan clock.
            let clock=c.usage(None).cache_work+1;
            let mut eligible:Vec<_>=ci::records(&cache).into_iter().filter(|r|r.2==0&&!plan[r.0]).collect();
            eligible.sort_by(|a,b|{
                let left=u128::from(a.4)*u128::from((clock-b.3).max(1));
                let right=u128::from(b.4)*u128::from((clock-a.3).max(1));
                left.cmp(&right).then_with(||a.3.cmp(&b.3)).then_with(||a.0.cmp(&b.0))
            });
            let before=ci::records(&cache);
            let result=ci::select(&mut cache,&mut c,&plan);
            if eligible.is_empty() {
                assert_eq!(result.unwrap_err().code,"all_entries_pinned");
                assert_eq!(ci::records(&cache),before); transitions+=1; break;
            }
            assert_eq!(result.unwrap(),eligible[0].0); assert_eq!(ci::records(&cache),before); resident_assert_index(&cache); transitions+=1;
        }
        for p in held { cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap(); }
        finish(cache,c);
    }
    println!("COST_ORACLE transitions={transitions} capacities=7 sorted_ratio_reference=true pinned_and_selected_excluded=true cleanup=zero");
}
fn cost_retention_memory_seed(budget:SwiftRunBudget,bytes:&[u8])->(RuntimeControl,SwiftFunctionCache,SwiftFunctionPin) {
    let (mut c,mut cache)=new(bytes,budget);
    let held=pin(&mut cache,&mut c,100,None).unwrap();
    for f in 101..104 {cost_trace_release(&mut cache,&mut c,f);}
    (c,cache,held)
}
#[test]
fn cost_retention_three_victims_held_identity_and_every_boundary() {
    hooks(Hooks::default()); let mut lengths=vec![1;100];lengths[104-34]=4;
    let bytes=cost_trace_fixture(&lengths);
    let (c,cache)=new(&bytes,SwiftRunBudget::default()); let fixed=cache.usage().fixed_reserved; finish(cache,c);
    let budget=SwiftRunBudget{cache_entries:4,cache_bytes:fixed+4*2*size_of::<crate::experimental::cache::DecodedInstruction>(),..SwiftRunBudget::default()};
    // Narrow construction uses fewer slots than fixed's64; compute its actual
    // fixed reservation before setting the exact four-entry payload bound.
    let (c,cache)=new(&bytes,SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()});let fixed=cache.usage().fixed_reserved;finish(cache,c);
    let budget=SwiftRunBudget{cache_bytes:fixed+4*2*size_of::<crate::experimental::cache::DecodedInstruction>(),..budget};
    let (mut c,mut cache,held)=cost_retention_memory_seed(budget,&bytes);
    let held_record=ci::records(&cache).into_iter().find(|r|r.1==100).unwrap();
    let identity=cache.identity();let stale=inspection::stale(&held);
    let base=c.usage(None).cache_work; hooks(Hooks::default());
    cost_trace_release(&mut cache,&mut c,104);
    let work=c.usage(None).cache_work-base;let checks=HOOKS.with(|h|h.get().checks);
    assert_eq!(cache.usage().evictions,3);assert_eq!(cache.identity(),identity);
    assert_eq!(ci::records(&cache).into_iter().find(|r|r.1==100).unwrap(),held_record);
    assert_eq!(cache.view(&held,&mut c,None).unwrap().function,100);
    cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();assert!(cache.view(&stale,&mut c,None).is_err());finish(cache,c);
    for prefix in 0..work {
        hooks(Hooks::default());let (mut c,mut cache,held)=cost_retention_memory_seed(SwiftRunBudget{cache_work:base+prefix,..budget},&bytes);
        let held_record=ci::records(&cache).into_iter().find(|r|r.1==100).unwrap();
        let f=pin(&mut cache,&mut c,104,None).unwrap_err();assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        assert!(!ci::records(&cache).iter().any(|r|r.1==104));
        assert_eq!(ci::records(&cache).into_iter().find(|r|r.1==100).unwrap(),held_record);
        resident_assert_index(&cache);let usage=c.usage(None);plan_reuse_primary(f,pin(&mut cache,&mut c,104,None).unwrap_err());review_assert_same_control_effects(usage,c.usage(None));
        cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());let (mut c,mut cache,held)=cost_retention_memory_seed(budget,&bytes);let held_record=ci::records(&cache).into_iter().find(|r|r.1==100).unwrap();
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});let f=pin(&mut cache,&mut c,104,None).unwrap_err();assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);hooks(Hooks::default());
        assert!(!ci::records(&cache).iter().any(|r|r.1==104));assert_eq!(ci::records(&cache).into_iter().find(|r|r.1==100).unwrap(),held_record);resident_assert_index(&cache);
        cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    }
    println!("COST_MULTI victims=3 work_prefixes={work} cancellation_boundaries={checks} held_proof_pin_IR_identity=true sticky_failure=true cleanup=zero");
}
#[test]
fn cost_retention_all_pinned_and_hit_metadata_unchanged() {
    for capacity in [1,2,4,64] {
        hooks(Hooks::default());let bytes=fixture(0,&[0,0x0b],100);let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:capacity,..SwiftRunBudget::default()});let mut held=Vec::new();
        for f in 34..34+capacity as u32 {held.push(pin(&mut cache,&mut c,f,None).unwrap());}
        let before=ci::records(&cache);assert_eq!(pin(&mut cache,&mut c,99,None).unwrap_err().code,if capacity==64 {"pin_slots_exhausted"}else{"all_entries_pinned"});assert_eq!(ci::records(&cache),before);
        for p in held {cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}finish(cache,c);
    }
    let bytes=fixture(0,&[0,0x0b],100);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());cost_trace_release(&mut cache,&mut c,34);
    let before=ci::records(&cache)[0];let work=c.usage(None).cache_work;
    cost_trace_release(&mut cache,&mut c,34);let after=ci::records(&cache)[0];
    assert_eq!(c.usage(None).cache_work-work,8);assert_eq!((before.0,before.1,before.2,before.4,before.5),(after.0,after.1,after.2,after.4,after.5));assert!(after.3>before.3);finish(cache,c);
    println!("COST_PIN all_pinned_capacities=4 original_hit_work=8 cost_IR_unchanged=true cleanup=zero");
}
#[test]
fn cost_retention_rank_prefixes_and_translation_ties() {
    let bytes=fixture(0,&[0,0x0b],100);
    let seed=|budget| {
        let (mut c,mut cache)=new(&bytes,budget);
        for f in 34..38 {cost_trace_release(&mut cache,&mut c,f);}
        for f in 34..38 {ci::metadata(&mut cache,f,17,4);}
        (c,cache)
    };
    let budget=SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()};
    hooks(Hooks::default());let (mut c,mut cache)=seed(budget);let base=c.usage(None).cache_work;
    hooks(Hooks::default());assert_eq!(ci::select(&mut cache,&mut c,&[false;64]).unwrap(),0);
    let work=c.usage(None).cache_work-base;let checks=HOOKS.with(|h|h.get().checks);assert_eq!(work,37);
    for f in 34..38 {ci::metadata(&mut cache,f,1717,4);}
    assert_eq!(ci::select(&mut cache,&mut c,&[false;64]).unwrap(),0);finish(cache,c);
    for prefix in 0..work {
        hooks(Hooks::default());let (mut c,mut cache)=seed(SwiftRunBudget{cache_work:base+prefix,..budget});let before=ci::records(&cache);
        assert_eq!(ci::select(&mut cache,&mut c,&[false;64]).unwrap_err().resource,Some(SwiftRunResource::CacheWork));assert_eq!(ci::records(&cache),before);finish(cache,c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());let (mut c,mut cache)=seed(budget);let before=ci::records(&cache);
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});assert_eq!(ci::select(&mut cache,&mut c,&[false;64]).unwrap_err().kind,SwiftRunFailureKind::Cancelled);hooks(Hooks::default());assert_eq!(ci::records(&cache),before);finish(cache,c);
    }
    println!("COST_RANK_PREFIX work_prefixes={work} cancellation_boundaries={checks} equal_age_slot_tie=true selection_only_order_shift=true readonly=true cleanup=zero");
}
#[test]
fn cost_retention_exact_inventory_and_payload() {
    let (inventory,resident,slot,operation)=ci::shape();
    assert_eq!((resident,slot),(128,144));
    assert_eq!(operation,92_350+3*inventory+3*8);
    assert_eq!(cache_header_bytes().unwrap(),92_128+6*8);
    let bytes=fixture(0,&[0,0x0b],100);let (c,cache)=new(&bytes,SwiftRunBudget::default());
    assert_eq!(cache.usage().fixed_reserved,118_240+6*8+64*8);
    assert_eq!(c.usage(None).cache_work,4_928);
    println!("COST_INVENTORY bytes={inventory} disjoint_copies=3 operation={operation} header_growth=48 slot_growth=512 fixed_growth=560 constructor_work_growth=0");
    ci::print_inventory();finish(cache,c);
}
