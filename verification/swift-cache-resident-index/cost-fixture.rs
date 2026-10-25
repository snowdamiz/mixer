
#[test]
fn resident_index_finite_cost_fixture() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let constructor = c.usage(None).cache_work;
    for function in 34..98 {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    }
    let cold = c.usage(None).cache_work - constructor;
    let before = c.usage(None).cache_work;
    let (_, allocations) = measure(|| {
        for _ in 0..4 {
            for function in 34..98 {
                let p = pin(&mut cache, &mut c, function, None).unwrap();
                assert_eq!(cache.view(&p, &mut c, None).unwrap().function, function);
                cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
            }
        }
    });
    assert_eq!(allocations.attempts, 0);
    assert_eq!(cache.usage().hits, 256);
    assert_eq!(cache.usage().misses, 64);
    assert_eq!(cache.usage().evictions, 0);
    let hits = c.usage(None).cache_work - before;
    println!("RESIDENT_COST {{\"constructorWork\":{constructor},\"cold64Work\":{cold},\"hit256Work\":{hits},\"fixedReserved\":{},\"residentBytes\":{},\"hitAllocatorRequests\":{},\"slots\":{:?}}}",cache.usage().fixed_reserved,cache.usage().resident_bytes,allocations.attempts,inspection::elision_slots(&cache));
    finish(cache, c);
}
