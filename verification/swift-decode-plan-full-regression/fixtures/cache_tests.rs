#[test]
fn full_regression_observe_cache_fixture_shapes() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (cache, stats) = measure(|| construct(&mut c, a, None).unwrap());
    println!(
        "REGRESSION_CACHE stats={stats:?} header={} fixed={} work={}",
        cache_header_bytes().unwrap(),
        c.usage(None).reservations.cache.current,
        c.usage(None).cache_work
    );
    assert_eq!(stats.reallocations, 0);
    finish(cache, c);
}
