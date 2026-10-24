#[test]
fn cdr14_value_and_frame_admission_exact_bound_and_one_below() {
    for frame in [false,true] {for below in [false,true] {
        let mut own=owner();let before=usage(&own);let added=if frame{FRAME_OPERATION_BYTES.unwrap()}else{value_operations::VALUE_OPERATION_BYTES.unwrap()};
        let remaining=own.control.as_ref().unwrap().budget().combined_bytes-before.reservations.combined.current;
        let fill=remaining.checked_sub(added).unwrap()+usize::from(below);
        let ticket=own.control.as_mut().unwrap().admit_with_wasi(SwiftReservationCategory::Shared,fill,cursor(),Some(own.wasi.as_ref().unwrap().usage())).unwrap();
        if frame {
            let mut slot=Some(own.prepare_frames(cursor()));let result=slot.take().unwrap();
            if below {let failure=result.err().unwrap();assert_eq!(failure.kind,SwiftRunFailureKind::CombinedExhausted);}
            else {let mut p=result.ok().unwrap();assert_eq!(p.phase.operation.control.usage(None).reservations.combined.current,p.phase.operation.control.budget().combined_bytes);p.drain();assert!(matches!(p.complete(FrameOperationStorage{preparation:slot,entry:None,returned:None,drained:None,controlled:None}),FrameCompletion::Completed));}
        } else {
            let mut slot=Some(own.prepare_value_operation(cursor()));let result=slot.take().unwrap();
            if below {let failure=result.err().unwrap();assert_eq!(failure.kind,SwiftRunFailureKind::CombinedExhausted);}
            else {let p=result.ok().unwrap();assert_eq!(p.operation.control.usage(None).reservations.combined.current,p.operation.control.budget().combined_bytes);p.complete_values(value_operations::ValueOperationStorage{preparation:slot,outcome:None}).unwrap();}
        }
        assert_eq!(usage(&own).reservations.construction.current,before.reservations.construction.current);
        own.control.as_mut().unwrap().drop_reserved_with_wasi((),ticket,Some(own.wasi.as_ref().unwrap().usage())).unwrap();retire(own);
    }}
}
