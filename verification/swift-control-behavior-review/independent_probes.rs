// Independent finite review cases. Appended only in the review scratch tree;
// reuses real proof/owner fixture construction, never changes product behavior.
fn review_same_first(actual: SwiftRunFailure, mut first: SwiftRunFailure) {
    // record_cleanup adds its separate observation by the original contract.
    // The complete original diagnostic and at_failure snapshot stay identical.
    first.after_cleanup = actual.after_cleanup;
    assert_eq!(actual, first);
}
#[test]
fn review_new_result_compositions() {
    for case in [
        Case { name: "review_two_level_br_if", body: &[2,0x7f,2,0x7f,0x41,21,0x41,0x7f,0x0d,1,0x0b,0x0b,0x0b], result:true, answer:Some(Value::I32(21)), expected:&[(1,0,2,1),(2,0,3,1),(3,1,3,1),(4,2,3,1),(7,1,1,6),(8,1,0,4)] },
        Case { name: "review_false_if_inner_branch", body:&[0x41,0,4,0x7f,0x41,24,5,2,0x7f,0x41,25,0x0c,0,0x0b,0x0b,0x0b], result:true, answer:Some(Value::I32(25)), expected:&[(1,1,1,1),(4,0,2,2),(5,0,3,1),(6,1,3,1),(8,1,2,4),(9,1,1,4),(10,1,0,4)] },
        Case { name: "review_return_open_result_loop", body:&[2,0x7f,3,0x7f,0x41,26,0x0f,0x0b,0x0b,0x0b], result:true, answer:Some(Value::I32(26)), expected:&[(1,0,2,1),(2,0,3,1),(3,1,3,1),(4,1,3,0)] },
    ] { run_case(case); }
    let mut owner=body_owner(&[3,0x7f,0x41,23,0x41,0x7f,0x0d,0,0x0b,0x0b],true,&[],SwiftRunBudget::default());
    let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();phase.enter(34).unwrap();
    for _ in 0..4 {assert!(!step(&mut phase).unwrap());}
    assert_eq!((phase.phase.parts.frames[0].pc,phase.phase.parts.values.len(),phase.phase.parts.controls.len()),(1,0,2));
    assert!(phase.phase.parts.controls[1].is_loop());assert!(phase.phase.parts.controls[1].result());
    settle(phase,prep);retire(owner);
    println!("REVIEW result compositions=3; signed true loop retains original result-bearing label and discards branch result");
}

#[test]
fn review_pinned_table_distinct_targets_and_warm_refusal() {
    for (selector,expected_target,expected_pc,expected_controls) in [(0,0,6,2),(1,1,7,1),(0x7f,2,8,0)] {
        let body=[2,0x7f,2,0x7f,0x41,31,0x41,selector,0x0e,2,0,1,2,0x0b,0x0b,0x0b];
        let mut owner=body_owner(&body,true,&[],SwiftRunBudget::default());
        for warm in [false,true] {
            let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();
            let (answer,alloc)=measure_extended(if warm {Some(0)} else {None},|| {
                phase.enter(34)?;
                for _ in 0..4 {assert!(!step(&mut phase)?);}
                // Copy only the chosen depth from the currently pinned view.
                let (instruction,target)={
                    let frame=phase.phase.parts.frames.last().unwrap();
                    let view=phase.phase.parts.cache.view(&frame.pin,phase.phase.operation.control,Some(&*phase.phase.operation.wasi)).unwrap();
                    let instruction=view.instructions[frame.pc];
                    let (first,count,default)=match instruction.operation {Operation::BrTable{first,count,default}=>(first,count,default),_=>panic!("real table")};
                    assert_eq!(&view.branch_targets[first..first+count],&[0,1]);assert_eq!(default,2);
                    let index=match phase.phase.parts.values.last().unwrap(){Value::I32(v)=>*v as u32 as usize,_=>panic!("i32 selector")};
                    let target=if index<count {view.branch_targets[first+index]}else{default};
                    (instruction,target)
                };
                assert_eq!(target,expected_target);
                let cache_before=phase.phase.parts.cache.usage();
                boundary(&mut phase,instruction)?;let charged=observed(&phase);
                let done=phase.control_operation(instruction.operation,Some(target))?;
                let after=observed(&phase);
                assert_eq!((after.instructions,after.instruction_fuel),(charged.instructions,charged.instruction_fuel));
                assert_eq!(after.execution_work-charged.execution_work,5+u64::from(target));
                assert_eq!(phase.phase.parts.cache.usage(),cache_before);
                assert_eq!((phase.phase.parts.frames[0].pc,phase.phase.parts.controls.len()),(expected_pc,expected_controls));
                assert_eq!(phase.phase.parts.values.as_slice(),[Value::I32(31)]);
                assert_eq!(done,target==2);
                for _ in 0..2-target { assert_eq!(step(&mut phase)?,phase.phase.parts.controls.is_empty()); }
                phase.finish()
            });
            assert!(matches!(answer.unwrap(),FrameReturn::Outermost(Some(Value::I32(31)))));
            if warm {assert_eq!((alloc.attempts,alloc.allocations,alloc.reallocations),(0,0,0));}else{assert!(alloc.attempts>0);}
            complete_ok(phase,prep);
        }
        retire(owner);
    }
    println!("REVIEW pinned tables: first=0 last=1 unsigned-default=2; warm complete trace zero allocation requests");
}

#[test]
fn review_branch_exact_work_and_cancellation_prefixes() {
    // Independent six-row oracle for an actual decoded br discarding one value.
    for (allowance,want_values,want_controls,want_work,want_pc) in [
        (0,&[Value::I32(31),Value::I32(32)][..],2,0,4),
        (1,&[Value::I32(31),Value::I32(32)][..],2,1,4),
        (2,&[Value::I32(31)][..],2,2,4),
        (3,&[Value::I32(31)][..],2,2,4),
        (4,&[][..],2,4,4),
        (5,&[Value::I32(32)][..],1,5,5),
    ] {
        let mut owner=body_owner(&[2,0x7f,0x41,31,0x41,32,0x0c,0,0x0b,0x0b],true,&[],SwiftRunBudget::default());
        let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();phase.enter(34).unwrap();
        for _ in 0..3 {step(&mut phase).unwrap();}
        let (instruction,target)=fetched(&mut phase);boundary(&mut phase,instruction).unwrap();let before=observed(&phase);
        let old=phase.phase.operation.control.test_replace_execution_work_limit(before.execution_work+allowance);
        let result=phase.control_operation(instruction.operation,target);
        if allowance<5 {assert_eq!(result.unwrap_err().kind,SwiftRunFailureKind::WorkExhausted);}else{assert!(!result.unwrap());}
        assert_eq!(phase.phase.parts.values.as_slice(),want_values);assert_eq!(phase.phase.parts.controls.len(),want_controls);assert_eq!(phase.phase.parts.frames[0].pc,want_pc);
        let after=observed(&phase);assert_eq!(after.execution_work-before.execution_work,want_work);assert_eq!((after.instructions,after.instruction_fuel),(before.instructions,before.instruction_fuel));
        assert_eq!((after.live.values.current,after.live.controls.current),(want_values.len(),want_controls));
        phase.phase.operation.control.test_replace_execution_work_limit(old);settle(phase,prep);retire(owner);
    }
    // Cancel separately at branch debit, result-pop debit, close debit, push debit.
    for (checkpoint,want_values,want_work) in [(0,&[Value::I32(31),Value::I32(32)][..],0),(1,&[Value::I32(31),Value::I32(32)][..],1),(2,&[Value::I32(31)][..],2),(3,&[][..],4)] {
        let mut owner=body_owner(&[2,0x7f,0x41,31,0x41,32,0x0c,0,0x0b,0x0b],true,&[],SwiftRunBudget::default());
        let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();phase.enter(34).unwrap();for _ in 0..3 {step(&mut phase).unwrap();}
        let (instruction,target)=fetched(&mut phase);boundary(&mut phase,instruction).unwrap();let before=observed(&phase);
        hooks(Hooks{push_fault:6,cancel_local:Some(checkpoint),..Hooks::default()});let failure=phase.control_operation(instruction.operation,target).unwrap_err();hooks(Hooks::default());
        assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);assert_eq!(phase.phase.parts.values.as_slice(),want_values);assert_eq!(observed(&phase).execution_work-before.execution_work,want_work);
        let later=phase.finish().unwrap_err();assert_eq!(later,failure);settle(phase,prep);retire(owner);
    }
    println!("REVIEW six exact br work prefixes and four cancellation checkpoints; preserved first failure through finish");
}

#[test]
fn review_actual_after_pop_latch_survives_finish_and_reacquisition() {
    for (body,steps) in [
        (&[0x41,1,4,0x40,0x0b,0x0b][..],1),
        (&[2,0x40,0x41,1,0x0d,0,0x0b,0x0b][..],2),
        (&[2,0x40,0x41,0x7f,0x0e,1,0,0,0x0b,0x0b][..],2),
        (&[2,0x7f,0x41,17,0x0b,0x1a,0x0b][..],2),
    ] {
        let mut owner=body_owner(body,false,&[],SwiftRunBudget::default());
        owner.wasi.as_mut().unwrap().dispatch(owner.control.as_mut().unwrap(),WasiFunction::ArgsSizesGet,&[Value::I32(0),Value::I32(4)],&mut [0;8],cursor()).unwrap();
        let wasi=owner.wasi.as_ref().unwrap().usage();let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();phase.enter(34).unwrap();for _ in 0..steps {step(&mut phase).unwrap();}
        let (instruction,target)=fetched(&mut phase);boundary(&mut phase,instruction).unwrap();let old_values=phase.phase.parts.values.len();
        hooks(Hooks{push_fault:5,..Hooks::default()});let first=phase.control_operation(instruction.operation,target).unwrap_err();hooks(Hooks::default());
        assert_eq!(first.code,"swift_run_live_underflow");assert_eq!((first.stage,first.function,first.offset,first.resource),(SwiftRunStage::Cleanup,None,None,None));assert_eq!(first.at_failure.wasi,Some(wasi));
        assert_eq!(phase.phase.parts.values.len(),old_values-1);assert!(phase.cleanup.live_unreconciled);assert_eq!(phase.finish().unwrap_err(),first);
        phase.phase.operation.control.cancellation().cancel();let report=phase.drain();assert!(report.live_unreconciled);assert!(report.first_failure.unwrap().after_cleanup.is_some());review_same_first(report.first_failure.unwrap(),first);
        assert!(matches!(complete(phase,prep),FrameCompletion::Retained(_)));assert!(owner.prepare_frames(cursor()).is_err());
        let mut resumed=Some(owner.resume_frame_cleanup());let mut cleanup=resumed.take().unwrap().unwrap();review_same_first(cleanup.finish().unwrap_err(),first);assert!(cleanup.cleanup.live_unreconciled);
        review_same_first(cleanup.drain().first_failure.unwrap(),first);assert!(cleanup.cleanup.live_unreconciled);assert!(matches!(complete(cleanup,resumed),FrameCompletion::Retained(_)));
        let mut owned=Some(owner);assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());assert!(owned.is_some());drop(owned);
    }
    println!("REVIEW original rejected value removal for If/BrIf/BrTable/saved-End; exact original Cleanup diagnostic + WASI; latch survives finish, drain, completion, explicit reacquisition");
}

#[test]
fn review_deepest_and_shallowest_real_pin_rejections() {
    let mut foreign=owner();let mut owner=body_owner(&[2,0x40,0x0b,0x0b],false,&[],SwiftRunBudget::default());install_foreign(&mut foreign);
    let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();for function in [34,34,36,36,34] {phase.enter(function).unwrap();}
    let ids=pin_ids(&phase);let (instruction,target)=fetched(&mut phase);boundary(&mut phase,instruction).unwrap();
    let before=observed(&phase);let old=phase.phase.operation.control.test_replace_execution_work_limit(before.execution_work);
    let first=phase.control_operation(instruction.operation,target).unwrap_err();phase.phase.operation.control.cancellation().cancel();hooks(Hooks{release_mask:0b10001,..Hooks::default()});
    let report=phase.drain();assert_eq!(report.retained_frames,2);assert_eq!(pin_ids(&phase),vec![ids[0],ids[4]]);review_same_first(report.first_failure.unwrap(),first);
    HOOKS.with(|slot|{let h=slot.get();assert_eq!(h.release_seen,5);assert_eq!(&h.release_order[..5],&[34,36,36,34,34]);});
    assert_eq!(phase.drain().retained_frames,2);assert_eq!(HOOKS.with(|s|s.get().release_seen),5);
    phase.phase.operation.control.test_replace_execution_work_limit(old);assert!(matches!(complete(phase,prep),FrameCompletion::Retained(_)));restore_foreign(&mut foreign);
    drain_complete(&mut owner);assert_eq!(HOOKS.with(|s|s.get().release_seen),2);retire(owner);retire(foreign);
    println!("REVIEW five real frame pins; first and fifth release rejected deepest-first; no implicit retry; explicit cleanup retries only two authorities");
}

#[test]
fn review_completion_slot_all_values_drop_and_exact_formula() {
    for occupied in [None,Some(false),Some(true)] {
        let mut owner=body_owner(&[0x0b],false,&[],SwiftRunBudget::default());let before=usage(&owner).reservations.construction.current;
        let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();phase.enter(34).unwrap();assert!(step(&mut phase).unwrap());phase.finish().unwrap();
        let completion=phase.complete(FrameOperationStorage{preparation:prep,entry:None,returned:None,drained:None,controlled:occupied.map(Ok)});
        if occupied.is_none(){assert!(matches!(completion,FrameCompletion::Completed));}else{assert!(matches!(completion,FrameCompletion::Retained(_)));assert_eq!(usage(&owner).reservations.construction.current,before+FRAME_OPERATION_BYTES.unwrap());drain_complete(&mut owner);}
        assert_eq!(usage(&owner).reservations.construction.current,before);retire(owner);
    }
    // The exact admission formula is recomputed from this actual owner's usage.
    for delta in [-1isize,0] {
        let mut owner=owner();let current=usage(&owner);let exact=current.reservations.combined.current+FRAME_OPERATION_BYTES.unwrap();
        let limit=exact.checked_add_signed(delta).unwrap();let previous=current.reservations.construction.current;let old=owner.control.as_mut().unwrap().test_replace_combined_limit(limit);
        let mut prep=Some(owner.prepare_frames(cursor()));
        if delta<0 {let failure=prep.take().unwrap().err().unwrap();assert_eq!(failure.kind,SwiftRunFailureKind::CombinedExhausted);assert_eq!(failure.attempted,exact as u64);assert_eq!(usage(&owner).reservations.construction.current,previous);}else{let phase=prep.take().unwrap().unwrap();assert_eq!(phase.cleanup.bound.unwrap().admitted,previous+FRAME_OPERATION_BYTES.unwrap());drop(phase);assert_eq!(usage(&owner).reservations.construction.current,previous+FRAME_OPERATION_BYTES.unwrap());assert!(owner.prepare_value_operation(cursor()).is_err());drain_complete(&mut owner);}
        owner.control.as_mut().unwrap().test_replace_combined_limit(old);retire(owner);
    }
    assert_eq!(FRAME_OPERATION_BYTES,Some(ACTIVE_BYTES+119576+control_operations::ACTIVE_BYTES));
    println!("REVIEW completion new slot None/Some(false)/Some(true); actual exact/below formula and dropped phase debt; nested value charged once");
}

#[test]
fn review_nested_floor_and_guard_side_effects() {
    for fault in 0..4 {
        let body: &[u8]=match fault {0=>&[0x41,1,0x0d,0,0x0b],1=>&[0x0c,0,0x0b],2=>&[2,0x40,0x0b,0x0b],_=>&[0x41,0,4,0x40,1,0x0b,0x0b]};
        let mut owner=body_owner(body,false,&[Type::I32],SwiftRunBudget::default());let mut prep=Some(owner.prepare_frames(cursor()));let mut phase=prep.take().unwrap().unwrap();
        phase.enter(34).unwrap();phase.phase.push_value(Value::I32(55)).unwrap();phase.enter(36).unwrap();
        let pins=pin_ids(&phase);let caller=phase.phase.parts.values[..2].to_vec();let caller_controls=control_image(&phase)[..1].to_vec();
        if fault==0 {step(&mut phase).unwrap();phase.phase.pop_value().unwrap();}
        if fault==2 {step(&mut phase).unwrap();let c=*phase.phase.parts.controls.last().unwrap();let floor=phase.phase.parts.frames.last().unwrap().operands;*phase.phase.parts.controls.last_mut().unwrap()=Control::decoded(ControlKind::Block,c.start(),c.end(),floor-1,false);}
        if fault==3 {step(&mut phase).unwrap();}
        let (mut instruction,target)=fetched(&mut phase);
        if fault==1 {instruction.operation=Operation::Br(1);}
        if fault==3 {if let Operation::Block{kind,result,end,..}=instruction.operation {instruction.operation=Operation::Block{kind,result,end,alternative:Some(end)};}else{panic!("decoded If");}}
        boundary(&mut phase,instruction).unwrap();let before=observed(&phase);let values=phase.phase.parts.values.len();let controls=phase.phase.parts.controls.len();let pc=phase.phase.parts.frames.last().unwrap().pc;
        let failure=phase.control_operation(instruction.operation,target).unwrap_err();assert_eq!(failure.kind,SwiftRunFailureKind::Invariant);
        assert_eq!(&phase.phase.parts.values[..2],caller);assert_eq!(control_image(&phase)[..1],caller_controls);assert_eq!(pin_ids(&phase),pins);assert_eq!(phase.phase.parts.frames.last().unwrap().pc,pc);
        assert_eq!(phase.phase.parts.values.len(),values-usize::from(fault==3));assert_eq!(phase.phase.parts.controls.len(),controls-usize::from(fault==2));
        let after=observed(&phase);assert_eq!((after.live.values.current,after.live.controls.current),(phase.phase.parts.values.len(),phase.phase.parts.controls.len()));
        assert_eq!(after.execution_work-before.execution_work,if fault==1 {0}else{1});assert!(matches!(phase.lifecycle,Lifecycle::Terminal));
        settle(phase,prep);retire(owner);
    }
    println!("REVIEW nested-frame empty condition, one-beyond branch depth, below-floor popped End, malformed false-If alternative; exact caller floor/pin and prefix effects");
}
