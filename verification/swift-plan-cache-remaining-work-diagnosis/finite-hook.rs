// Appended only to an isolated copy of the accepted source. No guest execution.
use std::cell::RefCell;
#[derive(Default)]
struct RemainingPlanObserver {
    site: usize,
    credits: [u64; 16],
    calls: [u64; 16],
    plans: [u64; 4], // empty, conflicting identity, hit, published
    completed: u64,
    rejected: Option<(usize, u64)>,
}
thread_local! { static REMAINING_PLAN: RefCell<RemainingPlanObserver> = RefCell::new(RemainingPlanObserver::default()); }
pub(super) fn remaining_plan_site(site: u8) { REMAINING_PLAN.with(|x| x.borrow_mut().site = site as usize); }
pub(super) fn remaining_plan_event(event: u8) { REMAINING_PLAN.with(|x| x.borrow_mut().plans[event as usize] += 1); }
pub(super) fn remaining_plan_completed() { REMAINING_PLAN.with(|x| x.borrow_mut().completed += 1); }
pub(super) fn remaining_plan_work(n: u64, ok: bool) {
    REMAINING_PLAN.with(|x| {
        let mut x = x.borrow_mut(); let site = x.site;
        if ok { x.credits[site] += n; x.calls[site] += 1; }
        else if x.rejected.is_none() { x.rejected = Some((site, n)); }
    });
}
fn remaining_plan_reset() { REMAINING_PLAN.with(|x| *x.borrow_mut() = RemainingPlanObserver::default()); }
fn remaining_plan_emit(label: &str, c: &RuntimeControl, cache: &SwiftFunctionCache, before: u64) -> u64 {
    let work = c.usage(None).cache_work - before;
    REMAINING_PLAN.with(|x| {
        let x = x.borrow(); assert_eq!(x.credits.iter().sum::<u64>(), work);
        println!("PLAN_REMAINING {{\"case\":\"{label}\",\"work\":{work},\"credits\":{:?},\"calls\":{:?},\"plans\":{:?},\"completed\":{},\"rejected\":{:?},\"hits\":{},\"misses\":{},\"decodes\":{},\"evictions\":{}}}",
            x.credits,x.calls,x.plans,x.completed,x.rejected.map(|(s,n)|[s as u64,n]),cache.usage().hits,cache.usage().misses,cache.usage().decodes,cache.usage().evictions);
    }); work
}
fn remaining_plan_one(cache: &mut SwiftFunctionCache, c: &mut RuntimeControl, f: u32) {
    let p=pin(cache,c,f,None).unwrap();
    cache.release(p,c,None).map_err(|e| e.failure).unwrap();
}
#[test]
fn remaining_plan_actual_cache_finite() {
    use crate::experimental::cache::{Operation,ControlKind};
    let mut flat_work=0;
    for (label, helper) in [
        ("flat_cold",vec![0,0x0b]),
        ("nested_cold",body(0,&[2,0x40,3,0x40,1,0x0b,0x0b,0x41,0,4,0x40,1,5,1,0x0b,0x0b])),
    ] {
        hooks(Hooks::default()); remaining_plan_reset();
        let bytes=fixture(0,&helper,600); let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
        assert_eq!(c.usage(None).cache_work,4928);
        remaining_plan_emit("constructor",&c,&cache,0);
        remaining_plan_reset(); let before=c.usage(None).cache_work;
        let p=pin(&mut cache,&mut c,34,None).unwrap(); let v=cache.view(&p,&mut c,None).unwrap();
        if label=="flat_cold" { assert_eq!(v.instructions.len(),1);assert_eq!(v.instructions[0].operation,Operation::End); }
        else {
            assert_eq!(v.instructions.len(),12);
            assert_eq!(v.instructions[0].operation,Operation::Block{kind:ControlKind::Block,result:None,end:4,alternative:None});
            assert_eq!(v.instructions[1].operation,Operation::Block{kind:ControlKind::Loop,result:None,end:3,alternative:None});
            assert_eq!(v.instructions[6].operation,Operation::Block{kind:ControlKind::If,result:None,end:10,alternative:Some(8)});
            assert_eq!(v.instructions[8].operation,Operation::Else{end:10});
        }
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
        let w=remaining_plan_emit(label,&c,&cache,before);if label=="flat_cold" {flat_work=w;}
        remaining_plan_reset();let before=c.usage(None).cache_work;
        remaining_plan_one(&mut cache,&mut c,34);assert_eq!(c.usage(None).cache_work-before,8);
        remaining_plan_emit("resident_hit_free_0",&c,&cache,before);
        let mut held=Vec::new();for _ in 0..63 {held.push(pin(&mut cache,&mut c,34,None).unwrap());}
        remaining_plan_reset();let before=c.usage(None).cache_work;
        remaining_plan_one(&mut cache,&mut c,34);assert_eq!(c.usage(None).cache_work-before,71);
        remaining_plan_emit("resident_hit_free_63",&c,&cache,before);
        for p in held {cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}finish(cache,c);
    }
    for count in [64,65] {
        hooks(Hooks::default());let bytes=fixture(0,&[0,0x0b],600);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
        remaining_plan_reset();let before=c.usage(None).cache_work;
        for _ in 0..2 {for f in 34..34+count {remaining_plan_one(&mut cache,&mut c,f);}}
        REMAINING_PLAN.with(|x|{let x=x.borrow();assert_eq!(x.plans,[count as u64,0,if count==65 {65} else {0},count as u64]);assert_eq!(x.completed,cache.usage().decodes);});
        if count==64 {assert_eq!((cache.usage().hits,cache.usage().decodes,cache.usage().evictions),(64,64,0));}
        else {assert_eq!((cache.usage().hits,cache.usage().decodes,cache.usage().evictions),(0,130,66));}
        remaining_plan_emit(if count==64 {"64_cycle_twice"} else {"65_cycle_twice"},&c,&cache,before);finish(cache,c);
    }
    // 34 and 546 share the direct-map index. Distinct 64-resident fills evict
    // the IR while keeping the count plan until the colliding identity replaces it.
    hooks(Hooks::default());let bytes=fixture(0,&[0,0x0b],600);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    remaining_plan_one(&mut cache,&mut c,34);for f in 35..99 {remaining_plan_one(&mut cache,&mut c,f);}
    remaining_plan_reset();let before=c.usage(None).cache_work;remaining_plan_one(&mut cache,&mut c,34);
    REMAINING_PLAN.with(|x|assert_eq!(x.borrow().plans,[0,0,1,0]));remaining_plan_emit("evicted_IR_plan_hit",&c,&cache,before);
    remaining_plan_reset();let before=c.usage(None).cache_work;remaining_plan_one(&mut cache,&mut c,546);
    REMAINING_PLAN.with(|x|assert_eq!(x.borrow().plans,[0,1,0,1]));remaining_plan_emit("plan_conflict_546",&c,&cache,before);
    for f in 99..163 {remaining_plan_one(&mut cache,&mut c,f);}
    remaining_plan_reset();let before=c.usage(None).cache_work;remaining_plan_one(&mut cache,&mut c,34);
    REMAINING_PLAN.with(|x|assert_eq!(x.borrow().plans,[0,1,0,1]));remaining_plan_emit("plan_conflict_34",&c,&cache,before);finish(cache,c);
    // All cold work prefixes exercise the observer after the original debit.
    // Smaller work budgets select failure controls; production budgets never change.
    let bytes=fixture(0,&[0,0x0b],600);
    for shorter in 0..flat_work {
        hooks(Hooks::default());let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_work:4928+shorter,..SwiftRunBudget::default()});
        remaining_plan_reset();let before=c.usage(None).cache_work;
        let f=pin(&mut cache,&mut c,34,None).unwrap_err();assert_eq!(f.resource,Some(SwiftRunResource::CacheWork));
        REMAINING_PLAN.with(|x|{let x=x.borrow();assert_eq!(x.credits.iter().sum::<u64>(),c.usage(None).cache_work-before);assert!(x.rejected.is_some());});
        let stopped=c.usage(None).cache_work;plan_reuse_primary(f,pin(&mut cache,&mut c,35,None).unwrap_err());assert_eq!(c.usage(None).cache_work,stopped);finish(cache,c);
    }
    for ordinal in [0,4,16] {
        hooks(Hooks::default());let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());remaining_plan_reset();let before=c.usage(None).cache_work;
        hooks(Hooks{cancel:Some(ordinal),..Hooks::default()});let f=pin(&mut cache,&mut c,34,None).unwrap_err();hooks(Hooks::default());assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);
        REMAINING_PLAN.with(|x|assert_eq!(x.borrow().credits.iter().sum::<u64>(),c.usage(None).cache_work-before));finish(cache,c);
    }
    println!("PLAN_REMAINING_CONTROL cold_prefixes={flat_work} cancellations=3 guest_instructions=0 initializes=0 invokes=0 cleanup_zero=true");
}
