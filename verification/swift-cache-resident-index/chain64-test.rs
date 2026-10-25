
#[test]
fn resident_index_inclusive_64_node_chain_and_cycle_bound() {
    hooks(Hooks::default());
    let functions: Vec<u32> = (34..12034).filter(|f| ((u64::from(*f) * 0x9e37_79b9) & 0xffff_ffff) >> 25 == ((34u64 * 0x9e37_79b9) & 0xffff_ffff) >> 25).take(64).collect();
    assert_eq!(functions.len(), 64);
    let bytes = fixture(0, &[0, 0x0b], 12000);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for function in &functions {
        let p=pin(&mut cache,&mut c,*function,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    }
    resident_assert_index(&cache);
    let before = c.usage(None).cache_work;
    let p=pin(&mut cache,&mut c,functions[0],None).unwrap();
    assert_eq!(cache.view(&p,&mut c,None).unwrap().function, functions[0]);
    let hit_work = c.usage(None).cache_work - before;
    assert_eq!(hit_work, 260); // two ordinary headers plus hash/head plus4*64 nodes.
    cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
    let bucket=(((34u64 * 0x9e37_79b9) & 0xffff_ffff) >> 25) as usize;
    let head=inspection::resident_index(&cache)[bucket];
    inspection::corrupt_index(&mut cache,128,head); // tail slot0 now closes a64-node cycle.
    assert_eq!(pin(&mut cache,&mut c,functions[0],None).unwrap_err().code,"swift_cache_index_cycle");
    finish(cache,c);
    println!("RESIDENT chain64 inclusive=true full_chain_hit_work={hit_work} adversarial_cost_not_discounted=true cycle_failclosed=true cleanup=zero");
}
