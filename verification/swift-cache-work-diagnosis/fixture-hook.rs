
// Diagnosis-only instrumentation. It observes successful credits; no control,
// failure, work amount, cursor, decode, cache policy, or guest code is replaced.
thread_local! { static DIAGNOSTIC_WORK: Cell<[u64; 8]> = const { Cell::new([0; 8]) }; }
pub(super) fn diagnostic_note_work(n: u64) {
    let step = HOOKS.with(|h| h.get().step as usize);
    DIAGNOSTIC_WORK.with(|w| { let mut a=w.get(); a[step]+=n; w.set(a); });
}
fn diagnostic_reset_work() { DIAGNOSTIC_WORK.with(|w| w.set([0;8])); }
fn diagnostic_work() -> [u64;8] { DIAGNOSTIC_WORK.with(Cell::get) }
#[test]
fn diagnostic_cache_work_fixture() {
    use crate::experimental::cache::{Operation, ControlKind};
    for (label, helper) in [
        ("flat", vec![0,0x0b]),
        ("nested", body(0, &[2,0x40,3,0x40,1,0x0b,0x0b,0x41,0,4,0x40,1,5,1,0x0b,0x0b])),
    ] {
        hooks(Hooks::default());
        diagnostic_reset_work();
        let bytes=fixture(0,&helper,100);
        let (mut c, mut cache)=new(&bytes,SwiftRunBudget::default());
        assert_eq!(c.usage(None).cache_work,640);
        assert_eq!(diagnostic_work().iter().sum::<u64>(),640);
        diagnostic_reset_work();
        let before=c.usage(None).cache_work;
        let p=pin(&mut cache,&mut c,34,None).unwrap();
        let view=cache.view(&p,&mut c,None).unwrap();
        if label=="flat" {
            assert_eq!(view.instructions.len(),1);
            assert_eq!(view.instructions[0].operation,Operation::End);
        } else {
            assert_eq!(view.instructions.len(),12);
            assert_eq!(view.instructions[0].operation,Operation::Block{kind:ControlKind::Block,result:None,end:4,alternative:None});
            assert_eq!(view.instructions[1].operation,Operation::Block{kind:ControlKind::Loop,result:None,end:3,alternative:None});
            assert_eq!(view.instructions[6].operation,Operation::Block{kind:ControlKind::If,result:None,end:10,alternative:Some(8)});
            assert_eq!(view.instructions[8].operation,Operation::Else{end:10});
        }
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
        let cold=c.usage(None).cache_work-before; let cold_steps=diagnostic_work();
        assert_eq!(cold_steps.iter().sum::<u64>(),cold);
        assert_eq!(cold_steps[CacheStep::ScanReset as usize],512);
        assert_eq!(cold_steps[CacheStep::BuildReset as usize],512);
        diagnostic_reset_work();
        let before=c.usage(None).cache_work;
        let p=pin(&mut cache,&mut c,34,None).unwrap();
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
        let hit=c.usage(None).cache_work-before;let hit_steps=diagnostic_work();
        assert_eq!(hit_steps.iter().sum::<u64>(),hit);
        assert_eq!(hit_steps[CacheStep::ScanReset as usize],0);
        assert_eq!(hit_steps[CacheStep::BuildReset as usize],0);
        println!("DIAG {{\"case\":\"{}\",\"cold_work\":{},\"cold_steps\":{:?},\"hit_work\":{},\"hit_steps\":{:?},\"decodes\":{},\"misses\":{},\"hits\":{}}}",label,cold,cold_steps,hit,hit_steps,cache.usage().decodes,cache.usage().misses,cache.usage().hits);
        finish(cache,c);
    }
    hooks(Hooks::default());
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    diagnostic_reset_work();
    let before=c.usage(None).cache_work;
    for _ in 0..2 { for f in 34..99 { let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap(); } }
    let work=c.usage(None).cache_work-before;let steps=diagnostic_work();
    assert_eq!(steps.iter().sum::<u64>(),work);
    assert_eq!(cache.usage().misses,130);
    assert_eq!(cache.usage().hits,0);
    assert_eq!(cache.usage().decodes,130);
    assert_eq!(cache.usage().evictions,66);
    assert_eq!(steps[CacheStep::ScanReset as usize],130*512);
    assert_eq!(steps[CacheStep::BuildReset as usize],130*512);
    println!("DIAG {{\"case\":\"65_function_cycle_twice\",\"work\":{},\"steps\":{:?},\"decodes\":{},\"misses\":{},\"hits\":{},\"evictions\":{},\"resident_bytes\":{}}}",work,steps,cache.usage().decodes,cache.usage().misses,cache.usage().hits,cache.usage().evictions,cache.usage().resident_bytes);
    finish(cache,c);
    println!("DIAG {{\"cleanup\":\"all_three_actual_owners_drained\"}}");
}
