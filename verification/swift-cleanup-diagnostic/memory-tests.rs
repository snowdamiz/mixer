#[test]
fn cdr01_actual_pinned_load_34_1713_keeps_source_and_cleanup_snapshot() {
    let _b=Bounds::new();fixture(true,Some(BODY),|p| {
        p.phase.operation.wasi.dispatch(p.phase.operation.control,crate::experimental_wasi::WasiFunction::ArgsSizesGet,&[Value::I32(0),Value::I32(4)],&mut [0;8],cursor()).unwrap();
        let wasi=p.phase.operation.wasi.usage();push(p,&[Value::I32(0)]);p.phase.parts.frames[0].pc=1;
        let actual={let f=&p.phase.parts.frames[0];(f.function,p.phase.parts.cache.view(&f.pin,p.phase.operation.control,Some(&*p.phase.operation.wasi)).unwrap().instructions[1])};
        assert_eq!((actual.0,actual.1.offset),(34,1713));let before=observed(p);let pins=pin_ids(p);
        hooks(Hooks{push_fault:5,..Hooks::default()});let mut s=storage();pinned(p,&mut s).unwrap();hooks(Hooks::default());
        let failure=s.entry.unwrap().unwrap_err();assert_eq!(failure.stage,SwiftRunStage::Invocation);
        assert_eq!((failure.function,failure.offset,failure.resource),(Some(34),Some(1713),Some(SwiftRunResource::Values)));
        assert_eq!((failure.attempted,failure.limit),(1,0));assert_eq!(failure.at_failure.wasi,Some(wasi));
        assert_eq!(p.phase.parts.frames[0].pc,2);assert_eq!(pin_ids(p),pins);assert!(p.phase.parts.values.is_empty());assert!(p.cleanup.live_unreconciled);
        assert_eq!((observed(p).instructions-before.instructions,observed(p).instruction_fuel-before.instruction_fuel,observed(p).execution_work-before.execution_work),(1,1,2));
        p.phase.operation.control.cancellation().cancel();assert_eq!(p.phase.operation.control.check(p.phase.operation.cursor).unwrap_err(),failure);
        for _ in 0..2 {let report=p.drain();let after=report.first_failure.unwrap();let mut original=after;original.after_cleanup=None;assert_eq!(original,failure);assert!(after.after_cleanup.is_some());assert!(report.live_unreconciled);}
        println!("CDR01 actualFunction=34 actualOffset=1713 resource=Values attempted=1 available=0 wasiCalls={} firstFailureExact=true cleanupObservationSeparate=true",wasi.calls);
    });
}
#[test]
fn cdr02_actual_pinned_store_both_pop_prefixes() {
    let _b=Bounds::new();let body=&[0x41,0,0x41,9,0x36,2,0,0x0b];
    for second in [false,true] {fixture(true,Some(body),|p| {
        push(p,&[Value::I32(0),Value::I32(9)]);p.phase.parts.frames[0].pc=2;
        let actual={let f=&p.phase.parts.frames[0];p.phase.parts.cache.view(&f.pin,p.phase.operation.control,Some(&*p.phase.operation.wasi)).unwrap().instructions[2]};
        hooks(Hooks{push_fault:if second{14}else{5},cancel_local:if second{Some(1)}else{None},..Hooks::default()});
        let before=observed(p);let mut s=storage();pinned(p,&mut s).unwrap();hooks(Hooks::default());let f=s.entry.unwrap().unwrap_err();
        assert_eq!((f.stage,f.function,f.offset,f.resource),(SwiftRunStage::Invocation,Some(34),Some(actual.offset),Some(SwiftRunResource::Values)));
        assert_eq!((f.attempted,f.limit),(1,0));assert_eq!(p.phase.parts.values.len(),if second{0}else{1});assert_eq!(&p.phase.parts.memory[..4],&[0;4]);
        assert_eq!(observed(p).execution_work-before.execution_work,if second{3}else{2});assert!(p.cleanup.live_unreconciled);
    });}
}
