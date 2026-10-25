// Isolated diagnosis only. Count successful credits under existing CacheStep.
// No runtime authority, amount, limit, cursor or failure is replaced.
thread_local! {
    static REMAINING_WORK: Cell<[u64; 8]> = const { Cell::new([0; 8]) };
}
pub(super) fn remaining_note_work(n: u64) {
    let step = HOOKS.with(|h| h.get().step as usize);
    REMAINING_WORK.with(|w| {
        let mut counts = w.get();
        counts[step] += n;
        w.set(counts);
    });
}
fn remaining_reset() { REMAINING_WORK.with(|w| w.set([0; 8])); }
fn remaining_work() -> [u64; 8] { REMAINING_WORK.with(Cell::get) }
fn remaining_emit(label: &str, c: &RuntimeControl, cache: &SwiftFunctionCache, before: u64) {
    let work = c.usage(None).cache_work - before;
    let stages = remaining_work();
    assert_eq!(stages.iter().sum::<u64>(), work);
    assert_eq!(stages[CacheStep::ScanReset as usize], 0);
    assert_eq!(stages[CacheStep::BuildReset as usize], 0);
    println!("REMAINING {{\"case\":\"{}\",\"work\":{},\"stages\":{:?},\"hits\":{},\"misses\":{},\"decodes\":{},\"evictions\":{},\"resident_bytes\":{}}}",
        label, work, stages, cache.usage().hits, cache.usage().misses,
        cache.usage().decodes, cache.usage().evictions, cache.usage().resident_bytes);
}
#[test]
fn remaining_work_actual_cache_fixture() {
    use crate::experimental::cache::{ControlKind, Operation};
    for (label, helper) in [
        ("flat_cold", vec![0, 0x0b]),
        ("nested_cold", body(0, &[2,0x40,3,0x40,1,0x0b,0x0b,0x41,0,4,0x40,1,5,1,0x0b,0x0b])),
    ] {
        hooks(Hooks::default());
        let bytes = fixture(0, &helper, 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        assert_eq!(c.usage(None).cache_work, 640);
        remaining_reset();
        let before = c.usage(None).cache_work;
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let v = cache.view(&p, &mut c, None).unwrap();
        if label == "flat_cold" {
            assert_eq!(v.instructions.len(), 1);
            assert_eq!(v.instructions[0].operation, Operation::End);
        } else {
            assert_eq!(v.instructions.len(), 12);
            assert_eq!(v.instructions[0].operation, Operation::Block { kind: ControlKind::Block, result: None, end: 4, alternative: None });
            assert_eq!(v.instructions[1].operation, Operation::Block { kind: ControlKind::Loop, result: None, end: 3, alternative: None });
            assert_eq!(v.instructions[6].operation, Operation::Block { kind: ControlKind::If, result: None, end: 10, alternative: Some(8) });
            assert_eq!(v.instructions[8].operation, Operation::Else { end: 10 });
        }
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        remaining_emit(label, &c, &cache, before);
        remaining_reset();
        let before = c.usage(None).cache_work;
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        assert_eq!(c.usage(None).cache_work - before, 3);
        remaining_emit("resident_slot_0_free_pin_0", &c, &cache, before);
        finish(cache, c);
    }
    for count in [64, 65] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        remaining_reset();
        let before = c.usage(None).cache_work;
        for _ in 0..2 {
            for function in 34..34 + count {
                let p = pin(&mut cache, &mut c, function, None).unwrap();
                cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
            }
        }
        if count == 64 {
            assert_eq!((cache.usage().hits, cache.usage().decodes, cache.usage().evictions), (64, 64, 0));
        } else {
            assert_eq!((cache.usage().hits, cache.usage().decodes, cache.usage().evictions), (0, 130, 66));
        }
        remaining_emit(if count == 64 { "64_function_cycle_twice" } else { "65_function_cycle_twice" }, &c, &cache, before);
        if count == 64 {
            remaining_reset();
            let before = c.usage(None).cache_work;
            let p = pin(&mut cache, &mut c, 97, None).unwrap();
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
            assert_eq!(c.usage(None).cache_work - before, 66);
            remaining_emit("resident_slot_63_free_pin_0", &c, &cache, before);
            let mut held = Vec::new();
            for _ in 0..63 { held.push(pin(&mut cache, &mut c, 34, None).unwrap()); }
            remaining_reset();
            let before = c.usage(None).cache_work;
            let p = pin(&mut cache, &mut c, 97, None).unwrap();
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
            assert_eq!(c.usage(None).cache_work - before, 129);
            remaining_emit("resident_slot_63_free_pin_63", &c, &cache, before);
            for p in held { cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap(); }
        }
        finish(cache, c);
    }
    println!("REMAINING {{\"cleanup\":\"four_original_owners_drained\"}}");
}
