// Independently authored review-only test additions. No production source edit.
#[test]
fn reviewer_r01_parameter_scan_budget_precedes_missing_range() {
    let _b=Bounds::new();
    fixture(|p| {
        let before=observed(p);
        let old=p.phase.operation.control.test_replace_execution_work_limit(before.execution_work+1);
        let mut outcome=None;
        p.host_operation(1,&mut outcome).unwrap();
        let failure=outcome.unwrap().unwrap_err();
        p.phase.operation.control.test_replace_execution_work_limit(old);
        assert_eq!(failure.kind,SwiftRunFailureKind::WorkExhausted);
        assert_eq!(failure.attempted,before.execution_work+2);
        assert_eq!(observed(p).execution_work,before.execution_work);
        assert_eq!(observed(p).host_calls,0);
        assert!(p.phase.parts.values.is_empty());
    });
}
#[test]
fn reviewer_r02_original_local_and_operand_prefix_survive_multivalue_import() {
    let _b=Bounds::new();
    fixture_with(SwiftRunBudget::default(),small(),WasiGrants::default(),&[Type::I32],|p|{
        push(p,&[i(0x12345678)]);
        let pins=pin_ids(p);let before=observed(p);
        call(p,WasiFunction::ArgsSizesGet,&[i(0),i(4)]).unwrap();
        assert_eq!(p.phase.parts.values.as_slice(),&[i(0),i(0x12345678),i(0)]);
        assert_eq!(observed(p).live.values.current,3);
        assert_eq!(observed(p).host_calls-before.host_calls,1);
        assert_eq!(observed(p).wasi.unwrap().calls-before.wasi.unwrap().calls,1);
        assert_eq!(pin_ids(p),pins);
        assert_eq!(p.phase.parts.frames[0].pc,0);
    });
}
#[test]
fn reviewer_r03_ordered_float_mismatches_reject_without_host_effect() {
    let _b=Bounds::new();
    for at in 0..3 {for wrong in [Value::F32(0),Value::F64(0)] {
        fixture(|p|{
            let mut args=[i(0),Value::I64(0),i(8)];args[at]=wrong;
            let pins=pin_ids(p);let before=observed(p);
            let failure=call(p,WasiFunction::ClockTimeGet,&args).unwrap_err();
            assert_eq!(failure.code,"swift_host_parameter_type");
            assert_eq!(p.phase.parts.values.as_slice(),&args);
            assert_eq!(observed(p).execution_work-before.execution_work,6);
            assert_eq!(observed(p).host_calls,0);assert_eq!(observed(p).wasi.unwrap().calls,0);
            assert_eq!(pin_ids(p),pins);
        });
    }}
}
#[test]
fn reviewer_r04_postdispatch_cancel_preserves_committed_log_and_first_observation() {
    let _b=Bounds::new();
    fixture_with(SwiftRunBudget::default(),small(),grants(),&[],|p|{
        p.phase.parts.memory[0..8].copy_from_slice(&[32,0,0,0,3,0,0,0]);
        p.phase.parts.memory[32..35].copy_from_slice(b"log");
        p.phase.operation.wasi.host_test_dispatch(false,true);
        let args=[i(1),i(0),i(1),i(16)];
        let failure=call(p,WasiFunction::FdWrite,&args).unwrap_err();
        assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);
        assert_eq!(p.phase.operation.wasi.stdout(),b"log");
        assert_eq!(&p.phase.parts.memory[16..20],&3u32.to_le_bytes());
        assert_eq!(p.phase.parts.values.as_slice(),&args);
        assert_eq!(failure.at_failure.host_calls,1);
        assert_eq!(failure.at_failure.wasi.unwrap().calls,1);
        let report=p.drain();let later=report.first_failure.unwrap();
        assert_eq!(later.at_failure,failure.at_failure);
        assert!(later.after_cleanup.is_some());
        assert_eq!(p.phase.operation.wasi.stdout(),b"log");
    });
}
#[test]
fn reviewer_r05_consuming_failed_slot_cannot_reenter_terminal_phase() {
    let _b=Bounds::new();
    fixture(|p|{
        push(p,&[i(0)]);p.phase.parts.frames[0].pc=1;
        let mut slot=storage();p.host_operation(34,&mut slot.entry).unwrap();
        let first=slot.entry.take().unwrap().unwrap_err();
        assert_eq!(first.code,"swift_host_import_index");
        let before=observed(p);let pc=p.phase.parts.frames[0].pc;
        host_operation_pinned_caller(p,&mut slot).unwrap();
        assert_eq!(slot.entry.unwrap().unwrap_err().at_failure,first.at_failure);
        assert_eq!(slot.entry.unwrap().unwrap_err().code,first.code);
        assert_eq!(p.phase.parts.frames[0].pc,pc);
        assert_eq!(observed(p).instructions,before.instructions);
        assert_eq!(observed(p).execution_work,before.execution_work);
        assert_eq!(observed(p).host_calls,0);
        assert_eq!(p.phase.parts.values.as_slice(),&[i(0)]);
    });
}
