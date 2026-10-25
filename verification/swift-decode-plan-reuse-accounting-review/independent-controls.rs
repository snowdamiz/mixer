
// Independently authored review controls. Shared fixture builders supply only ABI
// setup; expectations below are independent from the producer's diagnostic tests.
use super::cache::independent_accounting as review_acct;

#[test]
fn independent_review_named_shapes_and_default_ceilings() {
    let s=review_acct::shapes();
    let expected=if review_acct::CANDIDATE {[62888,92128,61880,92350,269616]} else {[62576,63120,57752,88294,269424]};
    assert_eq!(&s[4..],&expected);
    let b=SwiftRunBudget::default();
    assert_eq!((b.cache_entries,b.active_pins,b.cache_work,b.cache_bytes,b.cache_entry_bytes,b.combined_bytes),(64,64,64_000_000,16_777_216,8_388_608,268_435_456));
    println!("REVIEW_LAYOUT candidate={} shapes={s:?} limits={b:?}",review_acct::CANDIDATE);
}

#[test]
fn independent_review_constructor_ordinals_and_consuming_zero() {
    hooks(Hooks::default());
    let bytes=fixture(0,&[0,0x0b],100);
    let expected=if review_acct::CANDIDATE {5} else {4};
    for ordinal in 0..expected {
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        let (r,stats)=measure_extended(Some(ordinal),||construct(&mut c,a,None));
        assert!(r.is_err());
        assert_eq!(stats.injected_failures,1);assert_eq!(stats.attempts,ordinal+1);
        assert_eq!(c.usage(None).reservations.cache.current,0);
        assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current,0);
        println!("REVIEW_CONSTRUCTOR ordinal={ordinal} requested_size={} stats={stats:?} zero=true",stats.last_size);
    }
    let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
    let (r,stats)=measure(||construct(&mut c,a,None));let cache=r.unwrap();
    assert_eq!(stats.attempts,expected);assert_eq!(stats.reallocations,0);
    let expected_fixed=if review_acct::CANDIDATE {118240} else {89232};
    assert_eq!(cache.usage().fixed_reserved,expected_fixed);
    let before=c.usage(None).cache_work;
    assert_eq!(before,if review_acct::CANDIDATE {4928} else {832});
    finish(cache,c);
    println!("REVIEW_CONSTRUCTOR success allocations={expected} fixed={expected_fixed} credits={before} cleanup_zero=true");
}

#[test]
fn independent_review_cold_cached_collision_ir_and_work() {
    let helper=body(1,&[0x41,7,0x1a,2,0x40,1,0x0b,0x0b]);
    let bytes=fixture(0,&helper,600);
    let b=SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()};
    let (mut c,mut cache)=new(&bytes,b);
    let mut credits=Vec::new();
    for (i,f) in [34,35,34,546,34].into_iter().enumerate() {
        hooks(Hooks::default());let start=c.usage(None).cache_work;
        let p=pin(&mut cache,&mut c,f,None).unwrap();
        let scan=HOOKS.with(|h|h.get().steps[CacheStep::Scan as usize]);
        let build=HOOKS.with(|h|h.get().steps[CacheStep::Build as usize]);
        if f==34 {
            let v=cache.view(&p,&mut c,None).unwrap();
            assert_eq!(v.locals,&[Type::I32]);assert!(v.branch_targets.is_empty());
            let operations:Vec<_>=v.instructions.iter().map(|x|format!("{:?}",x.operation)).collect();
            assert_eq!(operations,["Const(I32(7))","Drop","Block { kind: Block, result: None, end: 4, alternative: None }","Nop","End","End"]);
            println!("REVIEW_IR pass={i} operations={operations:?}");
        }
        assert!(build>0);
        if review_acct::CANDIDATE && i==2 {assert_eq!(scan,0)} else {assert!(scan>0)}
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
        let charged=c.usage(None).cache_work-start;credits.push(charged);
        println!("REVIEW_PATH pass={i} function={f} scans={scan} builds={build} credits={charged}");
    }
    if review_acct::CANDIDATE {assert!(credits[2]<credits[0]);assert!(credits[4]>credits[2]);}
    else {assert_eq!(credits[2],credits[4]);}
    hooks(Hooks::default());finish(cache,c);
}

#[test]
fn independent_review_exact_phase_helper() {
    review_exact_phase_and_header_admission_boundaries();
    println!("REVIEW_EXACT_PHASE helper_invoked=true exact_and_minus_one=true");
}

#[test]
fn independent_review_header_retained_through_return_storage() {
    hooks(Hooks::default());let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,cache)=new(&bytes,SwiftRunBudget::default());
    let header=cache_header_bytes().unwrap();let mut owned=Some(cache);
    let (tail,stats)=measure(||SwiftFunctionCache::cleanup(&mut owned,&mut c,None).unwrap());
    assert!(owned.is_none());assert_eq!(stats.attempts,0);
    assert!(stats.freed_bytes>=if review_acct::CANDIDATE {28672+192} else {192});
    // The tail borrows the ledger. Deliberately omitting completion must keep
    // the header charged, including already-freed grouped payload storage.
    drop(tail);assert_eq!(c.usage(None).reservations.cache.current,header);
    assert!(c.finish_owned_cleanup(None).reservations.combined.current>=header);
    println!("REVIEW_HEADER retained={header} freed={} incomplete_cleanup_not_zero=true",stats.freed_bytes);
    let (c,cache)=new(&bytes,SwiftRunBudget::default());finish(cache,c);
}
