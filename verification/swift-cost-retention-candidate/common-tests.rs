// Fresh finite traces run unchanged against both copied engines. No guest runs.
fn cost_trace_release(cache: &mut SwiftFunctionCache, c: &mut RuntimeControl, f: u32) {
    let p = pin(cache, c, f, None).unwrap();
    cache.release(p, c, None).map_err(|e| e.failure).unwrap();
}
fn cost_trace_report(label: &str, start: u64, cache: &SwiftFunctionCache, c: &RuntimeControl) {
    let u = cache.usage(); let r = c.usage(None);
    assert_eq!(r.instructions, 0);
    assert_eq!(r.live.active_pins.current, 0);
    assert!(r.reservations.peak_tickets <= 86);
    println!("COST_TRACE {{\"case\":\"{label}\",\"decodes\":{},\"hits\":{},\"evictions\":{},\"traceWork\":{},\"fixedBytes\":{},\"peakTickets\":{},\"instructions\":0}}",u.decodes,u.hits,u.evictions,r.cache_work-start,u.fixed_reserved,r.reservations.peak_tickets);
}
fn cost_trace_fixture(lengths: &[usize]) -> Vec<u8> {
    let mut module = fixture(0, &[0, 0x0b], lengths.len());
    // The fixture has only its final code section after section7. Retain its
    // independently validated ABI and replace only the finite synthetic bodies.
    let mut cursor = 8;
    loop {
        let section_start=cursor; let id=module[cursor]; cursor+=1;
        let mut length=0usize; let mut shift=0;
        loop { let b=module[cursor]; cursor+=1; length|=usize::from(b&127)<<shift;
            if b&128==0 { break; } shift+=7; }
        if id==10 {
            module.truncate(section_start);
            let mut code=Vec::new(); uint(lengths.len() as u32,&mut code);
            for (index,nops) in lengths.iter().enumerate() {
                let mut body=vec![0];
                if index==28 { body.extend([0x41,0]); }
                else { body.extend(std::iter::repeat_n(1,*nops)); }
                body.push(0x0b); uint(body.len() as u32,&mut code); code.extend(body);
            }
            section(10,&code,&mut module); return module;
        }
        cursor+=length;
    }
}
#[test]
fn cost_retention_common_original_traces_and_shapes() {
    hooks(Hooks::default());
    let helper=body(0,&[vec![1;512],vec![0x0b]].concat());
    let bytes=plan_reuse_wide_fixture(&helper,700);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    for f in 34..50 { for _ in 0..2 { cost_trace_release(&mut cache,&mut c,f); } }
    let start=c.usage(None).cache_work;
    for round in 0..4 {
        for f in 100+128*round..228+128*round { cost_trace_release(&mut cache,&mut c,f); }
        for f in 34..50 { cost_trace_release(&mut cache,&mut c,f); }
    }
    cost_trace_report("hot16_scan128_four_rounds",start,&cache,&c); finish(cache,c);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    let start=c.usage(None).cache_work;
    for _ in 0..3 { for f in 100..165 { cost_trace_release(&mut cache,&mut c,f); } }
    cost_trace_report("cyclic65_three_rounds",start,&cache,&c); finish(cache,c);
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
    let (result,alloc)=measure(||construct(&mut c,a,None)); let cache=result.unwrap();
    assert_eq!(alloc.attempts,5); assert_eq!(alloc.reallocations,0);
    println!("COST_SHAPE {{\"slotBytes\":{},\"residentBytes\":{},\"headerBytes\":{},\"fixedBytes\":{},\"operationBytes\":{},\"constructionBytes\":{},\"constructorWork\":{},\"allocationBytes\":{},\"payloadBytes\":{}}}",size_of::<SwiftSlot>(),size_of::<SwiftResident>(),cache_header_bytes().unwrap(),cache.usage().fixed_reserved,cache_operation_bytes().unwrap(),cache_construction_bytes().unwrap(),c.usage(None).cache_work,alloc.allocated_bytes,c.budget().cache_bytes-cache.usage().fixed_reserved);
    finish(cache,c);
}
#[test]
fn cost_retention_common_mixed_and_phase_controls() {
    for (label,hot_cost,cold_cost) in [("expensive_hot_cheap_cold",512,0),("cheap_hot_expensive_cold",0,512),("uniform_hot_cold",32,32)] {
        let mut lengths=vec![cold_cost;700];
        for f in 100..116 { lengths[f-34]=hot_cost; }
        let bytes=cost_trace_fixture(&lengths);
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
        for f in 100..116 { for _ in 0..2 { cost_trace_release(&mut cache,&mut c,f); } }
        let start=c.usage(None).cache_work;
        // Four short interleaved streams, each128cold calls, then all16hot.
        for round in 0..4 {
            for f in 200+128*round..328+128*round { cost_trace_release(&mut cache,&mut c,f); }
            for f in 100..116 { cost_trace_release(&mut cache,&mut c,f); }
        }
        cost_trace_report(label,start,&cache,&c); finish(cache,c);
    }
    let mut lengths=vec![0;700];
    for f in 100..116 { lengths[f-34]=512; }
    let bytes=cost_trace_fixture(&lengths);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    for _ in 0..3 { for f in 100..116 { cost_trace_release(&mut cache,&mut c,f); } }
    let start=c.usage(None).cache_work;
    for _ in 0..12 { for f in 200..264 { cost_trace_release(&mut cache,&mut c,f); } }
    cost_trace_report("expensive_old_to_cheap_cycle64_phase_shift",start,&cache,&c);
    println!("COST_PHASE residents={:?}",inspection::elision_slots(&cache)); finish(cache,c);
}
#[test]
fn cost_retention_common_hit_path_is_original() {
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    for f in 34..98 { cost_trace_release(&mut cache,&mut c,f); }
    let start=c.usage(None).cache_work;
    let before=cache.usage();
    let (_,alloc)=measure(||for _ in 0..4 { for f in 34..98 { cost_trace_release(&mut cache,&mut c,f); } });
    assert_eq!(c.usage(None).cache_work-start,2048); assert_eq!(alloc.attempts,0);
    assert_eq!(cache.usage().decodes,before.decodes); assert_eq!(cache.usage().evictions,before.evictions);
    println!("COST_HIT work256=2048 allocations=0 decodes=0 evictions=0"); finish(cache,c);
}
