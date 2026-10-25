// Final focused independent equal-age and all-pinned control.
#[test]
fn retention_review_equal_ages_and_all_pinned() {
    let bytes=fixture(0,&[0,0x0b],300);
    let mut cases=0;
    for n in [2,3,5,8] {for shift in [0,12345] {
        hooks(Hooks::default());
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:n,..SwiftRunBudget::default()});
        for f in 100..100+n as u32 {plan_reuse_release(&mut cache,&mut c,f);}
        for f in 100..100+(n*3/4)as u32 {plan_reuse_release(&mut cache,&mut c,f);}
        let held=pin(&mut cache,&mut c,100,None).unwrap();
        ri::ages(&mut cache,Some(7),shift);
        plan_reuse_release(&mut cache,&mut c,100+n as u32-1);
        let states=ri::states(&cache);
        assert_eq!(states[0].1,Some(100));assert!(!states[0].2);assert_eq!(states[0].3,1);
        assert!(states[n-1].2,"equal ages demote the first protected slot even while pinned");
        ri::ages(&mut cache,Some(7),shift);
        let mut eligible:Vec<_>=ri::states(&cache).iter().filter(|s|s.3==0).map(|s|(s.2,s.4,s.0,s.1.unwrap())).collect();eligible.sort();
        let victim=eligible[0];
        plan_reuse_release(&mut cache,&mut c,200);
        let after=ri::states(&cache);
        assert!(!after.iter().any(|s|s.1==Some(victim.3)));
        assert_eq!(after[victim.2].1,Some(200));assert!(!after[victim.2].2);
        assert_eq!(cache.view(&held,&mut c,None).unwrap().function,100);
        cache.release(held,&mut c,None).map_err(|e|e.failure).unwrap();finish(cache,c);cases+=1;
    }}
    for n in [1,2,3,5] {
        hooks(Hooks::default());
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:n,..SwiftRunBudget::default()});
        let mut handles=Vec::new();
        for f in 100..100+n as u32 {plan_reuse_release(&mut cache,&mut c,f);handles.push(pin(&mut cache,&mut c,f,None).unwrap());}
        let before=ri::states(&cache);let work=c.usage(None).cache_work;
        let failure=pin(&mut cache,&mut c,200,None).unwrap_err();
        assert_eq!(failure.code,"all_entries_pinned");assert_eq!(ri::states(&cache),before);
        assert_eq!(c.usage(None).live.active_pins.current,n);assert!(c.usage(None).cache_work>work);
        for p in handles {cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
        finish(cache,c);
    }
    println!("REVIEW_TIES equal_age_cases={cases} capacities=4 shifts=2 pinned_demotion=true victim_slot_order=true all_pinned_capacities=4 rejection_unchanged=true cleanup=zero");
}
