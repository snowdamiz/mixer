// Same finite trace source is appended to the real baseline and candidate cache tests.
#[test]
fn retention_trace_hot_scans_and_cycle_control() {
    let mut helper = vec![0];
    helper.extend(std::iter::repeat_n(0x01, 512));
    helper.push(0x0b);
    let bytes = plan_reuse_wide_fixture(&helper, 700);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for f in 34..50 {
        plan_reuse_release(&mut cache, &mut c, f);
        plan_reuse_release(&mut cache, &mut c, f);
    }
    let warm = cache.usage();
    let start = c.usage(None).cache_work;
    for round in 0..4 {
        for f in 100 + round * 128..228 + round * 128 {
            plan_reuse_release(&mut cache, &mut c, f);
        }
        for f in 34..50 {
            plan_reuse_release(&mut cache, &mut c, f);
        }
    }
    let u = cache.usage();
    let actual = c.usage(None);
    assert_eq!(actual.instructions, 0);
    assert_eq!(actual.live.active_pins.current, 0);
    assert!(actual.reservations.peak_tickets <= 86);
    println!("RETENTION_TRACE {{\"case\":\"hot16_scan128_four_rounds\",\"decodes\":{},\"hits\":{},\"evictions\":{},\"traceWork\":{},\"warmDecodes\":{},\"warmWork\":{},\"fixedBytes\":{},\"peakTickets\":{},\"instructions\":0}}", u.decodes,u.hits,u.evictions,actual.cache_work-start,warm.decodes,start,u.fixed_reserved,actual.reservations.peak_tickets);
    finish(cache, c);

    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let start = c.usage(None).cache_work;
    for _ in 0..3 {
        for f in 100..165 {
            plan_reuse_release(&mut cache, &mut c, f);
        }
    }
    let u = cache.usage();
    assert_eq!(u.decodes, 195);
    assert_eq!(u.hits, 0);
    assert_eq!(u.evictions, 131);
    println!("RETENTION_TRACE {{\"case\":\"cyclic65_three_rounds\",\"decodes\":{},\"hits\":{},\"evictions\":{},\"traceWork\":{},\"fixedBytes\":{},\"instructions\":0}}",u.decodes,u.hits,u.evictions,c.usage(None).cache_work-start,u.fixed_reserved);
    finish(cache, c);
}

#[test]
fn retention_trace_shapes() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (result, stats) = measure(|| construct(&mut c, a, None));
    let cache = result.unwrap();
    assert_eq!(stats.attempts, 5);
    assert_eq!(stats.reallocations, 0);
    println!("RETENTION_SHAPE {{\"slotBytes\":{},\"headerBytes\":{},\"fixedBytes\":{},\"operationBytes\":{},\"constructionBytes\":{},\"constructorWork\":{},\"allocations\":{},\"payloadBytes\":{}}}",size_of::<SwiftSlot>(),cache_header_bytes().unwrap(),cache.usage().fixed_reserved,cache_operation_bytes().unwrap(),cache_construction_bytes().unwrap(),c.usage(None).cache_work,stats.attempts,c.budget().cache_bytes-cache.usage().fixed_reserved);
    finish(cache, c);
}

#[test]
fn retention_trace_hit_costs() {
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:4,..SwiftRunBudget::default()});
    for f in [34,34,35,35,36,36,37] { plan_reuse_release(&mut cache,&mut c,f); }
    let base=c.usage(None).cache_work;
    let (_,first)=measure(||plan_reuse_release(&mut cache,&mut c,37));
    let promoted=c.usage(None).cache_work-base;
    let base=c.usage(None).cache_work;
    let (_,second)=measure(||plan_reuse_release(&mut cache,&mut c,37));
    let protected=c.usage(None).cache_work-base;
    assert_eq!(first.attempts+second.attempts,0);
    println!("RETENTION_HIT {{\"promotionWork\":{promoted},\"protectedWork\":{protected},\"allocations\":0}}");
    finish(cache,c);
}
