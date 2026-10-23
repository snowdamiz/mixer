// Independently authored adversarial tests. Included into cache_tests only in
// the derived test tree. Every authority comes from the complete Swift validator.

fn independent_assert_category_sum(u: SwiftRunUsage) {
    let r = u.reservations;
    assert_eq!(r.combined.current, r.retained_source.current + r.retained_metadata.current
        + r.cache.current + r.state.current + r.wasi.current + r.shared.current
        + r.construction.current);
}

#[test]
fn independent_accounting_missing_shapes_are_measured() {
    super::cache::independent_print_missing_shapes();
}

#[test]
fn independent_64_distinct_live_pins_then_65th_and_terminal_release() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let mut pins = Vec::with_capacity(64);
    for function in 34..98 {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().function, function);
        pins.push(p);
        independent_assert_category_sum(c.usage(None));
    }
    let before = cache.usage();
    let ledger = c.usage(None);
    assert_eq!(ledger.live.active_pins.current, 64);
    assert_eq!(ledger.live.cache_entries.current, 64);
    assert_eq!(ledger.reservations.live_tickets, 73);
    assert_eq!(before.pinned_bytes, before.resident_bytes);
    let (failure, stats) = measure(|| pin(&mut cache, &mut c, 98, None).unwrap_err());
    assert_eq!(failure.code, "pin_slots_exhausted");
    assert_eq!(stats.attempts, 0);
    assert_eq!(cache.usage(), before);
    assert_eq!(c.usage(None).live, ledger.live);
    let work = c.usage(None).cache_work;
    let (_, stats) = measure(|| {
        for p in pins {
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        }
    });
    assert_eq!(stats.attempts, 0);
    assert_eq!(c.usage(None).cache_work, work);
    assert_eq!(cache.usage().pinned_bytes, 0);
    assert_eq!(cache.usage().resident_bytes, before.resident_bytes);
    finish(cache, c);
}

#[test]
fn independent_parameter_and_group_boundaries() {
    for (params, locals, accepted) in [(128,128,true),(129,0,false),(128,129,false),(0,256,true),(0,257,false)] {
        let bytes = fixture(params, &body(locals, &[0x0b]), 100);
        let p = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &Cancellation::default());
        assert_eq!(p.is_ok(), accepted, "params={params} locals={locals}");
        if accepted {
            let (mut c, a) = RuntimeControl::adopt(p.unwrap(), SwiftRunBudget::default(), Instant::now(), Cancellation::default()).unwrap();
            let mut cache = construct(&mut c, a, None).unwrap();
            let p = pin(&mut cache, &mut c, 34, None).unwrap();
            assert_eq!(cache.view(&p, &mut c, None).unwrap().locals.len(), locals);
            finish(cache, c);
        }
    }
    for groups in [256,257] {
        let mut helper = Vec::new();
        uint(groups, &mut helper);
        for _ in 0..groups { helper.extend([0,0x7f]); }
        helper.push(0x0b);
        let bytes = fixture(0, &helper, 100);
        let p = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &Cancellation::default());
        assert_eq!(p.is_ok(), groups == 256);
        if groups == 256 {
            let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
            let p = pin(&mut cache, &mut c, 34, None).unwrap();
            assert!(cache.view(&p, &mut c, None).unwrap().locals.is_empty());
            finish(cache,c);
        }
    }
}

fn independent_owned_fixture(helper: &[u8]) -> Vec<u8> {
    let mut module = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for _ in 0..37 { signature(&[], &[], &mut types); }
    section(1, &types, &mut module);
    let mut functions=vec![100]; functions.extend([0;100]);
    section(3, &functions, &mut module);
    section(4, &[1,0x70,1,1,1], &mut module);
    section(5, &[1,0,1], &mut module);
    section(6, &[1,0x7f,1,0x41,0,0x0b], &mut module);
    let mut code=vec![100];
    for index in 0..100 {
        let helper = if index == 0 {helper} else {&[0,0x0b]};
        uint(helper.len() as u32, &mut code); code.extend_from_slice(helper);
    }
    section(10, &code, &mut module);
    module
}

fn independent_operation(op: &crate::Op, targets: &mut Vec<u32>) -> crate::experimental::cache::Operation {
    use crate::experimental::cache::{Operation as C, ControlKind as K};
    use crate::{Op as O, BlockKind as B};
    match op {
        O::Unreachable=>C::Unreachable, O::Nop=>C::Nop,
        O::Block{kind,result,end,alternative} => C::Block{kind:match kind {B::Block=>K::Block,B::Loop=>K::Loop,B::If=>K::If,B::Function=>panic!("no synthetic owned Function opcode")},result:*result,end:*end,alternative:*alternative},
        O::Else{end}=>C::Else{end:*end}, O::End=>C::End, O::Br(n)=>C::Br(*n), O::BrIf(n)=>C::BrIf(*n),
        O::BrTable(values,default)=>{let first=targets.len();targets.extend_from_slice(values);C::BrTable{first,count:values.len(),default:*default}},
        O::Return=>C::Return,O::Call(n)=>C::Call(*n),O::CallIndirect(n)=>C::CallIndirect(*n),
        O::MemoryCopy=>C::MemoryCopy,O::MemoryFill=>C::MemoryFill,O::Drop=>C::Drop,O::Select=>C::Select,
        O::LocalGet(n)=>C::LocalGet(*n),O::LocalSet(n)=>C::LocalSet(*n),O::LocalTee(n)=>C::LocalTee(*n),
        O::GlobalGet(n)=>C::GlobalGet(*n),O::GlobalSet(n)=>C::GlobalSet(*n),
        O::Load{opcode,offset}=>C::Load{opcode:*opcode,offset:*offset},O::Store{opcode,offset}=>C::Store{opcode:*opcode,offset:*offset},
        O::MemorySize=>C::MemorySize,O::MemoryGrow=>C::MemoryGrow,O::Const(v)=>C::Const(*v),O::Numeric(n)=>C::Numeric(*n),O::Saturating(n)=>C::Saturating(*n),
    }
}

#[test]
fn independent_every_decoded_instruction_matches_independent_owned_ir() {
    // Unreachable stack permits every admitted instruction to be decoded and
    // type-validated. Absolute module offsets differ; relative offsets must not.
    let mut code = vec![0,1,0,0x0c,0,0,0x0d,0,0,0x0e,3,0,0,0,0,0,0x0f,0,0x10,35,0,0x1a,0,0x1b];
    for opcode in 0x20..=0x24 { code.extend([0,opcode,0x80,0]); }
    for opcode in 0x28..=0x3e { code.extend([0,opcode,0,0x80,1]); }
    code.extend([0,0x3f,0,0,0x40,0,0,0x41,0x80,0x80,0x80,0x80,0x78,0,0x42,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0]);
    for opcode in 0x45..=0xc4 {
        if matches!(opcode,0x45..=0x5a|0x67..=0x8a|0xa7|0xac|0xad|0xc0..=0xc4|0x5b..=0x66|0x8b..=0xa6|0xa8..=0xab|0xae..=0xbf) { code.extend([0,opcode]); }
    }
    code.extend([0,0x43,1,0,0xc0,0x7f,0,0x44,1,2,3,4,5,6,7,8]);
    for sub in 0..=7 { code.extend([0,0xfc,sub]); }
    code.extend([0,0x11,34,0,0,0xfc,10,0,0,0,0xfc,11,0,0,2,0x40,3,0x40,0,0x0d,1,0x0b,0x0b,0,4,0x40,1,5,1,0x0b,0x0b]);
    let helper=body(1,&code);
    let bytes=fixture(0,&helper,100);
    let owned_bytes=independent_owned_fixture(&helper);
    let limits=crate::Limits{profile:crate::Profile::TableMemoryV3,..crate::Limits::default()};
    let owned=crate::Module::decode(&owned_bytes,&limits).unwrap();
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    let p=pin(&mut cache,&mut c,34,None).unwrap();
    let view=cache.view(&p,&mut c,None).unwrap();
    let expected=&owned.functions[0];
    assert_eq!(view.locals,expected.locals);
    assert_eq!(view.instructions.len(),expected.code.len());
    let mut targets=Vec::new();
    for (index,(actual,original)) in view.instructions.iter().zip(&expected.code).enumerate() {
        assert_eq!(actual.operation,independent_operation(&original.op,&mut targets),"instruction{index}");
        assert_eq!(actual.offset-view.body_offset,original.offset-expected.offset,"offset{index}");
    }
    assert_eq!(view.branch_targets,targets);
    println!("review compared exact owned IR instructions={} targets={}",view.instructions.len(),targets.len());
    finish(cache,c);
}

#[test]
fn independent_final_header_refund_fault_actual_wasi_and_prior_cause() {
    for prior in [false,true] {
        hooks(Hooks::default());
        let bytes=fixture(0,&[0,0x0b],100);
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        let mut w=wasi(&mut c);
        w.dispatch(&mut c,WasiFunction::FdClose,&[Value::I32(47)],&mut [],cache_cursor()).unwrap();
        let actual=w.usage();
        let mut cache=construct(&mut c,a,Some(&w)).unwrap();
        for f in [34,34,35,36] {let _=pin(&mut cache,&mut c,f,Some(&w)).unwrap();}
        let first=if prior {c.cancellation().cancel();Some(c.check_with_wasi(cache_cursor(),Some(actual)).unwrap_err())} else {None};
        let (mut foreign,foreign_proof)=adopt(&bytes,SwiftRunBudget::default());
        let foreign_ticket=foreign.admit(SwiftReservationCategory::Cache,1,cache_cursor()).unwrap();
        let before=c.usage(Some(actual));
        let mut owner=Some(cache);
        let (mut tail,drops)=measure(||SwiftFunctionCache::cleanup(&mut owner,&mut c,Some(&w)).unwrap());
        assert_eq!(drops.attempts,0);
        assert!(owner.is_none());
        let original=super::cache::independent_replace_tail_header(&mut tail,foreign_ticket);
        let mut outcome=None;
        let (_,completion)=measure(||tail.complete(owner,&mut outcome));
        assert_eq!(completion.attempts,0);
        let failure=outcome.unwrap();
        assert_eq!(failure.at_failure.wasi,Some(actual));
        if let Some(first)=first {assert_eq!(failure.code,first.code);assert_eq!(failure.at_failure,first.at_failure);} else {
            assert_eq!(failure.code,"swift_run_release_owner");
            assert_eq!(failure.stage,SwiftRunStage::Cleanup);
            assert_eq!(failure.at_failure.reservations.cache.current,cache_header_bytes().unwrap());
            assert_eq!(failure.at_failure.reservations.retained_source.current,0);
            assert_eq!(failure.at_failure.reservations.retained_metadata.current,0);
        }
        let after=failure.after_cleanup.unwrap();
        assert_eq!(after.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationOwner));
        assert_eq!(after.wasi,Some(actual));
        assert_eq!(after.reservations.cache.current,cache_header_bytes().unwrap());
        assert_eq!(after.reservations.construction.current,foundation_construction_bytes().unwrap());
        assert_eq!(after.live.active_pins.current,0);
        assert_eq!(after.live.cache_entries.current,0);
        assert_eq!(c.usage(Some(actual)).cache_work,before.cache_work);
        assert_eq!(c.usage(Some(actual)).reservations.wasi,before.reservations.wasi);
        c.drop_reserved_with_wasi((),original,Some(actual)).unwrap();
        w.cleanup(&mut c).unwrap();
        let final_usage=c.finish_owned_cleanup(None);
        assert_eq!(final_usage.reservations.combined.current,0);
        assert_eq!(final_usage.reservations.live_tickets,0);
        foreign.drop_proof(foreign_proof).unwrap();
        let corrupted=foreign.finish_owned_cleanup(None);
        assert_eq!(corrupted.reservations.combined.current,1);
        assert_eq!(corrupted.reservations.live_tickets,1);
        println!("review final refund fault prior={prior}; original owner drained; corrupted foreign1-byte charge retained");
    }
}

#[test]
fn independent_missing_and_same_owner_underflow_wasi_preflight_retains_cache() {
    for missing in [true,false] {
        let bytes=fixture(0,&[0,0x0b],100);
        let (mut c,a)=adopt(&bytes,SwiftRunBudget::default());
        let mut w=wasi(&mut c);
        w.dispatch(&mut c,WasiFunction::FdClose,&[Value::I32(39)],&mut [],cache_cursor()).unwrap();
        let mut cache=construct(&mut c,a,Some(&w)).unwrap();
        let _=pin(&mut cache,&mut c,34,Some(&w)).unwrap();
        let usage=cache.usage();
        let source=cache.proof().source().as_ptr();
        let mut owner=Some(cache);
        let mut saved_header=None;
        let mut saved_current=None;
        if missing {saved_header=Some(w.independent_take_header());} else {saved_current=Some(c.independent_wasi_current(0));}
        let before=c.usage(Some(w.usage()));
        let (failure,stats)=measure(||SwiftFunctionCache::cleanup(&mut owner,&mut c,Some(&w)).err().unwrap());
        assert_eq!(stats.attempts,0);
        assert_eq!(failure.at_failure.wasi,if missing {None} else {Some(w.usage())});
        assert_eq!(failure.code,if missing {"swift_run_wasi_missing_header"} else {"swift_run_reservation_underflow"});
        assert_eq!(owner.as_ref().unwrap().proof().source().as_ptr(),source);
        assert_eq!(owner.as_ref().unwrap().usage(),usage);
        assert_eq!(c.usage(None).reservations,before.reservations);
        assert_eq!(c.usage(None).live,before.live);
        assert_eq!(c.usage(None).cache_work,before.cache_work);
        if let Some(header)=saved_header {w.independent_restore_header(header);}
        if let Some(current)=saved_current {assert_eq!(c.independent_wasi_current(current),0);}
        let tail=SwiftFunctionCache::cleanup(&mut owner,&mut c,Some(&w)).unwrap();
        let mut outcome=None;tail.complete(owner,&mut outcome);
        assert_eq!(outcome.unwrap().code,failure.code);
        w.cleanup(&mut c).unwrap();
        let final_usage=c.finish_owned_cleanup(None);
        assert_eq!(final_usage.reservations.combined.current,0);
        assert_eq!(final_usage.reservations.live_tickets,0);
    }
}

#[test]
fn independent_cleanup_expired_deadline_exact_work_and_latched_terminal() {
    let bytes=fixture(0,&[0,0x0b],100);
    let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
    let _=pin(&mut cache,&mut c,34,None).unwrap();
    let exact_work=c.usage(None).cache_work;
    finish(cache,c);
    for case in ["deadline","work","terminal"] {
        let budget=SwiftRunBudget{deadline_ms:if case=="deadline" {50} else {30_000},cache_work:if case=="work" {exact_work} else {64_000_000},..SwiftRunBudget::default()};
        let (mut c,mut cache)=new(&bytes,budget);
        let _=pin(&mut cache,&mut c,34,None).unwrap();
        if case=="deadline" {std::thread::sleep(Duration::from_millis(60));}
        if case=="work" {assert_eq!(c.usage(None).cache_work,exact_work);}
        let first=if case=="terminal" {c.cancellation().cancel();Some(c.check(cache_cursor()).unwrap_err())} else {None};
        let before=c.usage(None);
        let mut owner=Some(cache);let mut outcome=None;
        let (_,stats)=measure(||{let tail=SwiftFunctionCache::cleanup(&mut owner,&mut c,None).unwrap();tail.complete(owner,&mut outcome);});
        assert_eq!(stats.attempts,0);
        assert_eq!(c.usage(None).cache_work,before.cache_work);
        assert_eq!(c.usage(None).reservations.construction.current,foundation_construction_bytes().unwrap());
        assert_eq!(c.usage(None).reservations.cache.current,0);
        match first {Some(f)=>assert_eq!(outcome.unwrap().at_failure,f.at_failure),None=>assert!(outcome.is_none())}
        let final_usage=c.finish_owned_cleanup(None);
        assert_eq!(final_usage.reservations.combined.current,0);
        assert_eq!(final_usage.reservations.live_tickets,0);
    }
}

#[test]
fn independent_owner_thread_isolation_and_restore() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let barrier = std::sync::Barrier::new(2);
    std::thread::scope(|scope| {
        let barrier = &barrier;
        let bytes = &bytes;
        let seeded = scope.spawn(move || {
            let original = inspection::owner_counter();
            inspection::with_owner_counter(u64::MAX, || {
                barrier.wait();
                let (mut control, adopted) = adopt(bytes, SwiftRunBudget::default());
                let error = construct(&mut control, adopted, None).err().unwrap();
                assert_eq!(error.code, "swift_cache_owner_exhausted");
                assert_eq!(inspection::owner_counter(), u64::MAX);
                let after = control.finish_owned_cleanup(None);
                assert_eq!(after.reservations.combined.current, 0);
                assert_eq!(after.reservations.live_tickets, 0);
                assert_eq!(after.cleanup_invariant, None);
            });
            assert!(!inspection::owner_override_active());
            assert_eq!(inspection::owner_counter(), original);
        });
        let normal = scope.spawn(move || {
            barrier.wait();
            let mut owners = Vec::new();
            for _ in 0..3 {
                let (control, cache) = new(bytes, SwiftRunBudget::default());
                let owner = cache.identity().owner;
                assert!(owner != 0 && owner < u64::MAX - 1);
                assert!(!owners.contains(&owner));
                owners.push(owner);
                finish(cache, control);
            }
            assert!(!inspection::owner_override_active());
        });
        seeded.join().unwrap();
        normal.join().unwrap();
    });
    assert!(!inspection::owner_override_active());
    println!("independent owner thread isolation private=MAX global_unique=3 honest_zero=true");
}
