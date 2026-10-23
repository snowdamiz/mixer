#[cfg(test)]
mod review {
    use mixer_vm::{Cancellation, Value};
    use mixer_vm::experimental_wasi::{Errno, Resource, WasiBudget, WasiContext, WasiFailure, WasiFunction as F, WasiGrants, WasiOutcome};
    fn i(n: usize) -> Value { Value::I32(n as u32 as i32) }
    fn errno(e: Errno) -> WasiOutcome { WasiOutcome::Errno(e) }
    fn ctx(grants: WasiGrants) -> WasiContext { WasiContext::new(grants,WasiBudget::default(),Cancellation::default()).unwrap() }
    fn sink() -> WasiGrants { WasiGrants { stdout:true,stderr:true,..WasiGrants::default() } }
    fn word(memory:&mut [u8],at:usize,value:u32) { memory[at..at+4].copy_from_slice(&value.to_le_bytes()); }
    fn overlap(a:usize,n:usize,b:usize,m:usize)->bool { a<b+m && b<a+n }

    #[test]
    fn argv_entire_range_alias_grid_is_atomic_and_errno_does_not_poison_context() {
        let mut vm=ctx(WasiGrants::default());
        let mut count=0;
        for pointers in 0..=33 {
            for text in 0..=33 {
                let mut memory=[0xad;32]; let prior=memory;
                let expected=if pointers+4>32 || text+6>32 {Errno::Fault} else if overlap(pointers,4,text,6) {Errno::Inval} else {Errno::Success};
                let actual=vm.dispatch(F::ArgsGet,&[i(pointers),i(text)],&mut memory);
                assert_eq!(actual,errno(expected),"pointers={pointers}, text={text}");
                if expected==Errno::Success {
                    let mut want=prior; word(&mut want,pointers,text as u32); want[text..text+6].copy_from_slice(b"mixer\0"); assert_eq!(memory,want);
                } else {assert_eq!(memory,prior);}
                assert_eq!(vm.terminal(),None);
                count+=1;
            }
        }
        assert_eq!(vm.usage().calls,count);
        assert!(vm.stdout().is_empty() && vm.stderr().is_empty());
        println!("argv range/alias cases={count}; exact immutable failures and recovery");
    }
    #[test]
    fn every_nwritten_offset_checks_metadata_and_payload_alias_before_single_append() {
        for written in 0..=65 {
            let mut vm=ctx(sink()); let mut memory=[0xbc;64];
            word(&mut memory,0,16); word(&mut memory,4,16);
            memory[16..32].copy_from_slice(b"abcdefghijklmnop");
            let prior=memory;
            let expected=if written+4>64 {Errno::Fault} else if overlap(written,4,0,8) || overlap(written,4,16,16) {Errno::Inval} else {Errno::Success};
            assert_eq!(vm.dispatch(F::FdWrite,&[i(1),i(0),i(1),i(written)],&mut memory),errno(expected),"nwritten={written}");
            if expected==Errno::Success {
                let mut want=prior; word(&mut want,written,16); assert_eq!(memory,want); assert_eq!(vm.stdout(),&prior[16..32]); assert_eq!(vm.usage().log_bytes,16);
            } else {assert_eq!(memory,prior); assert!(vm.stdout().is_empty()); assert_eq!(vm.usage().log_bytes,0);}
            assert_eq!(vm.terminal(),None);
        }
        println!("fd_write output offsets=66; alias and bounds checked before append");
    }
    #[test]
    fn input_iovecs_may_overlap_each_other_and_metadata_without_output_alias() {
        let mut vm=ctx(sink()); let mut memory=[0;96];
        word(&mut memory,0,0); word(&mut memory,4,16);
        word(&mut memory,8,4); word(&mut memory,12,12);
        let prior=memory;
        assert_eq!(vm.dispatch(F::FdWrite,&[i(1),i(0),i(2),i(80)],&mut memory),errno(Errno::Success));
        let expected:[u8;28]=std::array::from_fn(|at| if at<16 {prior[at]} else {prior[4+at-16]});
        assert_eq!(vm.stdout(),expected);
        let mut want=prior; word(&mut want,80,28); assert_eq!(memory,want);
    }
    #[test]
    fn denied_authority_ignores_unsigned_bad_ranges_then_still_allows_fixed_argv() {
        let mut vm=ctx(WasiGrants::default()); let mut memory=[0xca;32];
        for (function,args,expected) in [
            (F::RandomGet,vec![i(u32::MAX as usize),i(u32::MAX as usize)],Errno::Notcapable),
            (F::ClockTimeGet,vec![i(0),Value::I64(-1),i(u32::MAX as usize)],Errno::Notcapable),
            (F::FdWrite,vec![i(1),i(u32::MAX as usize),i(u32::MAX as usize),i(u32::MAX as usize)],Errno::Badf),
            (F::PathOpen,vec![i(1),i(0),i(u32::MAX as usize),i(u32::MAX as usize),i(0),Value::I64(-1),Value::I64(-1),i(0),i(u32::MAX as usize)],Errno::Badf),
        ] {
            let prior=memory; assert_eq!(vm.dispatch(function,&args,&mut memory),errno(expected)); assert_eq!(memory,prior); assert_eq!(vm.terminal(),None);
        }
        assert_eq!(vm.usage().random_bytes,0);
        assert_eq!(vm.dispatch(F::ArgsGet,&[i(0),i(8)],&mut memory),errno(Errno::Success));
        assert_eq!(&memory[8..14],b"mixer\0");
    }
    #[test]
    fn zero_log_capacity_accepts_zero_write_and_rejects_payload_without_closing_sink() {
        let mut vm=WasiContext::new(sink(),WasiBudget {log_bytes:0,..WasiBudget::default()},Cancellation::default()).unwrap();
        let mut memory=[0;48]; word(&mut memory,0,32); word(&mut memory,4,1); memory[32]=42;
        let prior=memory;
        assert_eq!(vm.dispatch(F::FdWrite,&[i(1),i(0),i(1),i(40)],&mut memory),errno(Errno::Nospc));
        assert_eq!(memory,prior); assert_eq!(vm.terminal(),None); assert!(vm.stdout().is_empty());
        assert_eq!(vm.dispatch(F::FdWrite,&[i(1),i(48),i(0),i(40)],&mut memory),errno(Errno::Success));
        assert_eq!(&memory[40..44],&0u32.to_le_bytes());
        assert_eq!(vm.dispatch(F::FdClose,&[i(1)],&mut memory),errno(Errno::Success));
        assert_eq!(vm.dispatch(F::FdWrite,&[i(1),i(u32::MAX as usize),i(0),i(40)],&mut memory),errno(Errno::Badf));
    }
    #[test]
    fn exact_budget_failure_is_terminal_and_replay_does_no_work_even_with_bad_args() {
        let cancel=Cancellation::default();
        let mut vm=WasiContext::new(sink(),WasiBudget {calls:1,..WasiBudget::default()},cancel.clone()).unwrap();
        let mut memory=[0xd3;32];
        assert_eq!(vm.dispatch(F::FdSync,&[i(1)],&mut memory),errno(Errno::Notcapable));
        let prior=memory;
        let error=WasiOutcome::Failure(WasiFailure::Budget(Resource::Calls));
        assert_eq!(vm.dispatch(F::ArgsGet,&[i(0),i(8)],&mut memory),error);
        let usage=vm.usage(); cancel.cancel();
        assert_eq!(vm.dispatch(F::ProcExit,&[],&mut memory),error); assert_eq!(vm.usage(),usage); assert_eq!(memory,prior);
        assert_eq!(usage.calls,1); assert_eq!(usage.failures,2);
    }
}
