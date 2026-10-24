#[test]
fn cdr03_actual_pinned_truncation_values_and_controls() {
    for selector in [12,13] {
        let mut own=body_owner(&[2,0x40,0x41,1,0x41,2,0x0c,0,0x0b,0x0b],false,&[],SwiftRunBudget::default());
        let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();p.enter(34).unwrap();
        for _ in 0..3 {step(&mut p).unwrap();}
        let (instruction,target)=fetched(&mut p);boundary(&mut p,instruction).unwrap();
        let pins=pin_ids(&p);hooks(Hooks{push_fault:selector,..Hooks::default()});let failure=invoke(&mut p,instruction,target).unwrap_err();hooks(Hooks::default());
        assert_eq!((failure.stage,failure.function,failure.offset),(SwiftRunStage::Invocation,Some(34),Some(instruction.offset)));
        assert_eq!(failure.resource,Some(if selector==12{SwiftRunResource::Values}else{SwiftRunResource::Controls}));
        assert_eq!((failure.attempted,failure.limit),(if selector==12{2}else{1},0));assert_eq!(pin_ids(&p),pins);assert!(p.cleanup.live_unreconciled);
        let report=p.drain();let mut original=report.first_failure.unwrap();original.after_cleanup=None;assert_eq!(original,failure);
        assert!(matches!(complete(p,prep),FrameCompletion::Retained(_)));let mut retained=Some(own);assert!(SwiftReactorInstance::cleanup_owned(&mut retained).is_err());assert!(retained.is_some());drop(retained);
    }
}
#[test]
fn cdr05_actual_pinned_numeric_reconciliation_precedes_arithmetic_failure() {
    for opcode in [0x6a,0x6d] {
        let mut own=body_owner(&[0x41,9,0x41,0,opcode,0x1a,0x0b],false,&[],SwiftRunBudget::default());
        let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();p.enter(34).unwrap();
        p.phase.push_value(Value::I32(9)).unwrap();p.phase.push_value(Value::I32(0)).unwrap();p.phase.parts.frames[0].pc=2;
        let (instruction,_)=fetched(&mut p);boundary(&mut p,instruction).unwrap();
        hooks(Hooks{push_fault:8,..Hooks::default()});let failure=p.phase.numeric_value(opcode,false).unwrap_err();hooks(Hooks::default());
        assert_eq!(failure.code,"swift_run_live_underflow");assert_eq!((failure.function,failure.offset,failure.resource),(Some(34),Some(instruction.offset),Some(SwiftRunResource::Values)));
        assert_eq!((failure.attempted,failure.limit),(if opcode==0x6a{1}else{2},0));
        assert_eq!(p.phase.parts.values.as_slice(),if opcode==0x6a{&[Value::I32(9)][..]}else{&[][..]});
        let report=p.drain();assert!(report.live_unreconciled);assert!(matches!(complete(p,prep),FrameCompletion::Retained(_)));drop(own);
    }
}
#[test]
fn cdr06_actual_pin_active_finish_three_removals() {
    for selector in [9,10,11] {
        let mut own=body_owner(&[0x0b],false,&[Type::I32],SwiftRunBudget::default());
        let mut prep=Some(own.prepare_frames(cursor()));let mut p=prep.take().unwrap().unwrap();p.enter(34).unwrap();
        let (instruction,_)=fetched(&mut p);boundary(&mut p,instruction).unwrap();hooks(Hooks{push_fault:selector,..Hooks::default()});
        let failure=p.finish().unwrap_err();hooks(Hooks::default());
        assert_eq!((failure.stage,failure.function,failure.offset),(SwiftRunStage::Invocation,Some(34),Some(instruction.offset)));
        assert_eq!(failure.resource,Some(match selector{9=>SwiftRunResource::Values,10=>SwiftRunResource::Controls,_=>SwiftRunResource::Frames}));
        assert_eq!((failure.attempted,failure.limit),(1,0));assert!(p.cleanup.live_unreconciled);assert!(p.phase.parts.frames.is_empty());assert!(p.phase.parts.values.is_empty());assert!(p.phase.parts.controls.is_empty());assert_eq!(p.phase.parts.cache.usage().active_pins,0);
        let report=p.drain();let mut exact=report.first_failure.unwrap();exact.after_cleanup=None;assert_eq!(exact,failure);assert!(matches!(complete(p,prep),FrameCompletion::Retained(_)));drop(own);
    }
}
