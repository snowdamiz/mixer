
#[test]
fn plan_reuse_observation() {
    use crate::experimental::cache::Operation as O;
    let bytes = fixture(0, &body(1, &[0x41, 7, 0x21, 0, 0x20, 0, 0x1a, 0x0b]), 600);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let fixed = cache.usage().fixed_reserved;
    let start = c.usage(None).cache_work;
    let mut credits = vec![];
    for sweep in 0..3 {
        let begin = c.usage(None).cache_work;
        for f in 34..130 {
            let p = pin(&mut cache, &mut c, f, None).unwrap();
            let v = cache.view(&p, &mut c, None).unwrap();
            if f == 34 {
                let operations:Vec<_> = v.instructions.iter().map(|x|x.operation.clone()).collect();
                assert_eq!(v.locals, &[Type::I32]);
                assert_eq!(operations, vec![O::Const(Value::I32(7)),O::LocalSet(0),O::LocalGet(0),O::Drop,O::End]);
                assert!(v.branch_targets.is_empty());
                println!("PLAN_IR sweep={sweep} operations={operations:?} offsets={:?}", v.instructions.iter().map(|x|x.offset-v.body_offset).collect::<Vec<_>>());
            }
            cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
        }
        credits.push(c.usage(None).cache_work-begin);
    }
    assert_eq!(cache.usage().decodes,288);
    assert_eq!(cache.usage().evictions,224);
    assert!(c.usage(None).reservations.peak_tickets <= 86);
    println!("PLAN_COST fixed={fixed} constructor_work={start} sweeps={credits:?} usage={:?} tickets={}/{}",cache.usage(),c.usage(None).reservations.live_tickets,c.usage(None).reservations.peak_tickets);
    println!("PLAN_LRU slots={:?}",inspection::elision_slots(&cache));
    finish(cache,c);
}
