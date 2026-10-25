// Focused default-hook oracle; no broad regression-context rerun.
#[test]
fn retention_review_generic_default_literal_lru_and_unit_hooks() {
    use super::borrowed::{CacheMode,FrozenMode};
    use std::mem::size_of;
    assert_eq!(size_of::<<FrozenMode as CacheMode>::HitPlan>(),0);
    assert_eq!((size_of::<FunctionCache>(),size_of::<Slot>(),size_of::<PinRecord>()),(768,112,16));
    assert_eq!(SCRATCH_BYTES,9312);
    let cancellation=Cancellation::default();
    let mut cases=0;
    for n in 1..=8 {
        for case in 0..256usize {
            let mut slots=Vec::new();let mut selected=vec![false;n];
            for i in 0..n {
                let occupied=((case.wrapping_mul(17)^0x95)>>i)&1!=0;
                selected[i]=((case.wrapping_mul(43)^0x53)>>i)&1!=0;
                slots.push(Slot {entry:occupied.then(||DecodedFunction{function:i as u32,type_index:0,body_offset:0,locals:vec![],instructions:vec![],branch_targets:vec![],bytes:0}),pins:((case>>2)>>i)&1,last_used:((case+i*3)%5)as u64});
            }
            let before:Vec<_>=slots.iter().map(|s|(s.entry.as_ref().map(|e|e.function),s.pins,s.last_used)).collect();
            let mut choices:Vec<_>=slots.iter().enumerate().filter(|(i,s)|!selected[*i]&&s.pins==0&&s.entry.is_some()).map(|(i,s)|(s.last_used,i)).collect();choices.sort();
            let expected=choices.first().map(|p|p.1);
            let mut usage=CacheUsage::default();
            let mut meter=Meter{budget:CacheBudget::default(),usage:&mut usage,cancellation:&cancellation,function:None,offset:0};
            assert_eq!(FrozenMode::resident_victim(&slots,&selected,&mut meter).unwrap(),expected);
            assert_eq!(meter.usage.work_used,n as u64);
            let plan=FrozenMode::prepare_resident_hit(&slots,0,&mut meter).unwrap();
            assert_eq!(meter.usage.work_used,n as u64);
            FrozenMode::commit_resident_hit(&mut slots,0,plan);
            let after:Vec<_>=slots.iter().map(|s|(s.entry.as_ref().map(|e|e.function),s.pins,s.last_used)).collect();assert_eq!(before,after);
            cases+=1;
        }
    }
    println!("REVIEW_GENERIC cases={cases} full_scan_credits_exact=true lru_ties_and_eligibility=true unit_hooks_no_effect=true layout_unchanged=true");
}
