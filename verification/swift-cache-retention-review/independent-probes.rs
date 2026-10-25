// Independent finite reviewer probes, appended only to the extracted candidate.
// The model uses an ordinal clock and a sorted reference selection, rather than
// the implementation's work clock and incremental minimum scan.
#[derive(Clone, Debug, Default)]
struct ReviewSlot { function: Option<u32>, protected: bool, pins: usize, time: u64 }

fn review_model_pin(model: &mut [ReviewSlot], function: u32, time: u64) -> usize {
    if let Some(index) = model.iter().position(|s| s.function == Some(function)) {
        let capacity = model.len() * 3 / 4;
        if !model[index].protected && capacity != 0 {
            let mut protected: Vec<_> = model.iter().enumerate()
                .filter(|(_,s)| s.function.is_some() && s.protected)
                .map(|(i,s)| (s.time,i)).collect();
            protected.sort();
            if protected.len() == capacity { model[protected[0].1].protected = false; }
            model[index].protected = true;
        }
        model[index].pins += 1;
        model[index].time = time;
        return index;
    }
    let index = model.iter().position(|s| s.function.is_none()).unwrap_or_else(|| {
        let mut choices: Vec<_> = model.iter().enumerate().filter(|(_,s)|s.pins==0)
            .map(|(i,s)| (s.protected,s.time,i)).collect();
        choices.sort(); choices[0].2
    });
    model[index] = ReviewSlot { function:Some(function), protected:false, pins:1, time };
    index
}

fn review_compare(cache: &SwiftFunctionCache, c: &RuntimeControl, model: &[ReviewSlot]) {
    let actual = ri::states(cache);
    for (a,m) in actual.iter().zip(model) {
        assert_eq!((a.1,a.2,a.3),(m.function,m.protected,m.pins));
    }
    // Recency order must agree even though credit counts change its distances.
    for i in 0..model.len() { for j in 0..model.len() {
        if model[i].function.is_some() && model[j].function.is_some() {
            assert_eq!(actual[i].4.cmp(&actual[j].4),model[i].time.cmp(&model[j].time));
        }
    }}
    assert!(actual.iter().filter(|s|s.1.is_some()&&s.2).count() <= model.len()*3/4);
    assert_eq!(cache.usage().active_pins,model.iter().map(|s|s.pins).sum());
    assert_eq!(c.usage(None).live.active_pins.current,model.iter().map(|s|s.pins).sum());
    assert_eq!(c.usage(None).live.cache_entries.current,model.iter().filter(|s|s.function.is_some()).count());
    resident_assert_index(cache);
}

#[test]
fn retention_review_independent_reference_model() {
    let bytes=fixture(0,&[0,0x0b],400);
    let mut total=0;
    for slots in [1,2,3,4,5,6,7,8,63,64] {
        hooks(Hooks::default());
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:slots,..SwiftRunBudget::default()});
        let identity=cache.identity();
        let source=cache.proof().source().as_ptr();
        let mut model=vec![ReviewSlot::default();slots];
        let mut handles:Vec<(SwiftFunctionPin,usize)>=Vec::new();
        let mut random=0x83d2_fa91_u64+slots as u64;
        for step in 1..=640 {
            random=random.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let function=100+((random>>32)%(3*slots as u64+9)) as u32;
            let unavailable=model.iter().all(|s|s.pins>0)&&!model.iter().any(|s|s.function==Some(function));
            if !handles.is_empty() && (step%4==0 || unavailable || handles.len()>=24) {
                let index=(random as usize)%handles.len();
                let (p,slot)=handles.swap_remove(index);
                cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
                model[slot].pins-=1;
            } else {
                let index=review_model_pin(&mut model,function,step as u64);
                let p=pin(&mut cache,&mut c,function,None).unwrap();
                assert_eq!(cache.view(&p,&mut c,None).unwrap().function,function);
                handles.push((p,index));
            }
            review_compare(&cache,&c,&model);
            assert_eq!(cache.identity(),identity);
            assert_eq!(cache.proof().source().as_ptr(),source);
            assert_eq!(c.usage(None).instructions,0);
            total+=1;
        }
        for (p,index) in handles { cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap(); model[index].pins-=1; }
        review_compare(&cache,&c,&model);
        finish(cache,c);
    }
    println!("REVIEW_MODEL capacities=10 transitions={total} ordinal_clock=true active_pins_and_index=true cleanup=zero");
}

#[test]
fn retention_review_pinned_demotion_and_identity() {
    let bytes=fixture(0,&[0,0x0b],100);
    hooks(Hooks::default());
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()});
    plan_reuse_release(&mut cache,&mut c,34);
    let held=pin(&mut cache,&mut c,34,None).unwrap();
    let stale=inspection::stale(&held);
    let identity=cache.identity();
    let pin_identity=inspection::elision_pin_parts(&held);
    let (type_index,offset,locals,instructions,targets)={let v=cache.view(&held,&mut c,None).unwrap();
        (v.type_index,v.body_offset,v.locals.to_vec(),v.instructions.to_vec(),v.branch_targets.to_vec())};
    for f in [35,35,36,36,37] {plan_reuse_release(&mut cache,&mut c,f);}
    plan_reuse_release(&mut cache,&mut c,37);
    let demoted=ri::states(&cache).into_iter().find(|s|s.1==Some(34)).unwrap();
    assert!(!demoted.2); assert_eq!(demoted.3,1);
    plan_reuse_release(&mut cache,&mut c,38);
    assert!(!ri::states(&cache).iter().any(|s|s.1==Some(35)));
    assert_eq!(inspection::elision_pin_parts(&held),pin_identity);
    assert_eq!(cache.identity(),identity);
    {let v=cache.view(&held,&mut c,None).unwrap();
        assert_eq!((v.function,v.type_index,v.body_offset),(34,type_index,offset));
        assert_eq!(v.locals,locals); assert_eq!(v.instructions,instructions); assert_eq!(v.branch_targets,targets);}
    cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();
    plan_reuse_release(&mut cache,&mut c,39);
    assert!(!ri::states(&cache).iter().any(|s|s.1==Some(34)));
    assert_eq!(cache.view(&stale,&mut c,None).err().unwrap().code,"stale_pin");
    finish(cache,c);
    println!("REVIEW_PIN pinned_oldest_demoted=true pinned_probation_not_evicted=true proof_and_decoded_identity=true stale_rejected=true cleanup=zero");
}

fn review_seed_five(bytes:&[u8],budget:SwiftRunBudget)->(RuntimeControl,SwiftFunctionCache,SwiftFunctionPin){
    let (mut c,mut cache)=new(bytes,budget);
    plan_reuse_release(&mut cache,&mut c,35);
    let held=pin(&mut cache,&mut c,35,None).unwrap();
    for f in [36,36,37,37,38,39] {plan_reuse_release(&mut cache,&mut c,f);}
    (c,cache,held)
}

#[test]
fn retention_review_failed_promotion_with_live_pin() {
    let bytes=fixture(0,&[0,0x0b],100);
    let budget=SwiftRunBudget{cache_entries:5,..SwiftRunBudget::default()};
    hooks(Hooks::default());
    let (mut c,mut cache,held)=review_seed_five(&bytes,budget);
    let base=c.usage(None).cache_work;
    hooks(Hooks::default());
    let p=pin(&mut cache,&mut c,39,None).unwrap();
    let credits=c.usage(None).cache_work-base;
    let checks=HOOKS.with(|h|h.get().checks);
    // One held handle occupies the first pin record: the unchanged indexed
    // lookup path is nine credits here, versus eight with no live pin.
    assert_eq!(credits,9+1+2*5+3+2);
    cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    for boundary in 0..credits+checks as u64 {
        hooks(Hooks::default());
        let work=if boundary<credits {base+boundary}else{budget.cache_work};
        let (mut c,mut cache,held)=review_seed_five(&bytes,SwiftRunBudget{cache_work:work,..budget});
        let before=ri::states(&cache);let usage=cache.usage();
        if boundary>=credits {hooks(Hooks{cancel:Some((boundary-credits) as usize),..Hooks::default()});}
        let f=pin(&mut cache,&mut c,39,None).unwrap_err();
        if boundary<credits {assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));}
        else {assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);}
        assert_eq!(ri::states(&cache),before);assert_eq!(cache.usage(),usage);
        assert_eq!(c.usage(None).live.active_pins.current,1);
        let again=pin(&mut cache,&mut c,38,None).unwrap_err();plan_reuse_primary(f,again);
        hooks(Hooks::default());
        cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();
        finish(cache,c);
    }
    println!("REVIEW_FAILURE work_prefixes={credits} cancel_boundaries={checks} held_pin_retained=true hit_publication_atomic=true sticky_first_failure=true cleanup=zero");
}

#[test]
fn retention_review_memory_protected_victims_and_partial_failure() {
    let bytes=fixture(0,&[0,0x01,0x01,0x0b],100);
    let b=SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()};
    hooks(Hooks::default());
    let (mut c,mut cache)=new(&bytes,b);
    let fixed=cache.usage().fixed_reserved;plan_reuse_release(&mut cache,&mut c,35);
    let small=cache.usage().resident_bytes;finish(cache,c);
    let b=SwiftRunBudget{cache_bytes:fixed+4*small,..b};
    let seed=||{
        let (mut c,mut cache)=new(&bytes,b);
        for f in [35,35,36,36,37,37,38,38] {plan_reuse_release(&mut cache,&mut c,f);}
        let held=pin(&mut cache,&mut c,36,None).unwrap();
        (c,cache,held)
    };
    let (mut c,mut cache,held)=seed();let base=c.usage(None).cache_work;
    let p=pin(&mut cache,&mut c,34,None).unwrap();let credits=c.usage(None).cache_work-base;
    assert_eq!(cache.usage().evictions,3);
    assert_eq!(cache.usage().resident_bytes,4*small);
    assert_eq!(ri::states(&cache).iter().filter_map(|s|s.1).collect::<Vec<_>>(),vec![36,34]);
    cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    // Cancellation can retire already selected old residents. It must preserve
    // every surviving resident, the held pin, and unpublished-new-entry state.
    for prefix in 0..credits {
        hooks(Hooks::default());
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_work:base+prefix,..b});
        for f in [35,35,36,36,37,37,38,38] {plan_reuse_release(&mut cache,&mut c,f);}
        let held=pin(&mut cache,&mut c,36,None).unwrap();
        let before=ri::states(&cache);
        let f=pin(&mut cache,&mut c,34,None).unwrap_err();
        assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        let after=ri::states(&cache);assert!(!after.iter().any(|s|s.1==Some(34)));
        for a in after.iter().filter(|s|s.1.is_some()) {assert_eq!(a,before.iter().find(|s|s.1==a.1).unwrap());}
        assert!(after.iter().any(|s|s.1==Some(36)&&s.3==1));
        resident_assert_index(&cache);
        cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);
    }
    println!("REVIEW_MEMORY victims=3 includes_protected=true work_prefixes={credits} survivors_unchanged=true live_pin_preserved=true cleanup=zero");
}

#[test]
fn retention_review_exact_layouts_and_zero_capacity() {
    use crate::experimental::cache::borrowed::{CacheMode,FrozenMode};
    let (_,inventory,unit)=ri::plan_bytes();
    assert_eq!(size_of::<SwiftSlot>(),144);assert_eq!(inventory,2672);assert_eq!(unit,0);
    assert_eq!(size_of::<<FrozenMode as CacheMode>::HitPlan>(),0);
    assert_eq!(cache_operation_bytes().unwrap(),92350+3*2672);
    assert_eq!(cache_header_bytes().unwrap(),92128);
    assert_eq!(cache_construction_bytes().unwrap(),61880);
    let bytes=fixture(0,&[0,0x0b],100);
    hooks(Hooks::default());
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:0,..SwiftRunBudget::default()});
    assert!(pin(&mut cache,&mut c,35,None).is_err());assert!(ri::states(&cache).is_empty());finish(cache,c);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()});
    plan_reuse_release(&mut cache,&mut c,35);
    let before=c.usage(None).cache_work;plan_reuse_release(&mut cache,&mut c,35);
    assert_eq!(c.usage(None).cache_work-before,9);assert!(!ri::states(&cache)[0].2);finish(cache,c);
    println!("REVIEW_LAYOUT slot=144 slot_delta=8 fixed_delta_at64=512 inventory=2672 operation_delta=8016 frozen_hit_plan=0 zero_and_one_capacity=true cleanup=zero");
}
