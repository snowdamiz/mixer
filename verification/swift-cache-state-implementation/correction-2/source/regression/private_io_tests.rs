#[cfg(test)]
mod independent_transport_review {
    use super::*;

    struct In<'a> {
        bytes: &'a [u8], pos: usize, declared: u64, id: u64,
        quantum: usize, interrupts: usize, calls: usize,
        zero: bool, fail: bool, over: bool, stamps: usize, drift_at: usize,
    }
    impl<'a> In<'a> {
        fn new(bytes: &'a [u8], id: u64) -> Self { Self {bytes,pos:0,declared:bytes.len() as u64,id,quantum:usize::MAX,interrupts:0,calls:0,zero:false,fail:false,over:false,stamps:0,drift_at:usize::MAX} }
    }
    impl Read for In<'_> {
        fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
            self.calls+=1;
            if self.interrupts>0 {self.interrupts-=1;return Err(io::ErrorKind::Interrupted.into());}
            if self.fail {return Err(io::ErrorKind::PermissionDenied.into());}
            if self.over {return Ok(out.len()+1);}
            if self.zero {return Ok(0);}
            let count=out.len().min(self.quantum).min(self.bytes.len().saturating_sub(self.pos));
            out[..count].copy_from_slice(&self.bytes[self.pos..self.pos+count]);self.pos+=count;Ok(count)
        }
    }
    impl InputFile for In<'_> {
        fn stamp(&mut self) -> io::Result<Stamp> {
            self.stamps+=1;
            Ok(Stamp {fields:[8,self.id,0o100600,self.declared,0,0,u64::from(self.stamps>=self.drift_at),0],regular:1})
        }
        fn position(&mut self) -> io::Result<u64> {Ok(self.pos as u64)}
    }
    struct Out {
        bytes: Vec<u8>, calls: usize, interrupts: usize, quantum: usize,
        fail: bool, zero: bool, over: bool, fail_after: usize,
        stamps: usize, drift_at: usize, stamp_error_at: usize,
    }
    impl Out {
        fn new() -> Self { Self {bytes:Vec::new(),calls:0,interrupts:0,quantum:usize::MAX,fail:false,zero:false,over:false,fail_after:usize::MAX,stamps:0,drift_at:usize::MAX,stamp_error_at:usize::MAX} }
    }
    impl Write for Out {
        fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
            self.calls+=1;
            if self.interrupts>0 {self.interrupts-=1;return Err(io::ErrorKind::Interrupted.into());}
            if self.fail || self.bytes.len()>=self.fail_after {return Err(io::ErrorKind::BrokenPipe.into());}
            if self.zero {return Ok(0);}
            if self.over {return Ok(bytes.len()+1);}
            let count=bytes.len().min(self.quantum);self.bytes.extend_from_slice(&bytes[..count]);Ok(count)
        }
        fn flush(&mut self)->io::Result<()> {Ok(())}
    }
    impl OutputFile for Out {
        fn stamp(&mut self)->io::Result<Stamp> {
            self.stamps+=1;if self.stamps==self.stamp_error_at {return Err(io::ErrorKind::Other.into());}
            Ok(Stamp {fields:[8,104+u64::from(self.stamps>=self.drift_at),0o100600,self.bytes.len() as u64,0,0,0,0],regular:1})
        }
        fn position(&mut self)->io::Result<u64> {Ok(self.bytes.len() as u64)}
    }
    fn invoke(f: &crate::Fixture, output: &mut Out, limit: u64)->Result<ReplayOutcome,AnalyzerError> {
        analyze_core(&mut In::new(&f.stream,101),&mut In::new(&f.profile,102),&mut In::new(&f.context,103),output,limit)
    }
    fn assert_unaccepted(output: &Out) {
        assert!(output.bytes.len()<=REPORT_BYTES);
        if output.bytes.len()==REPORT_BYTES {assert_eq!(crate::get(&output.bytes,4),0);assert_eq!(crate::get(&output.bytes,5),0);assert!(output.bytes[512..].iter().all(|b|*b==0));}
    }

    #[test]
    fn independent_exact_32_read_attempts_short_and_interrupted() {
        for (length,interrupts,quantum,success) in [(1,31,usize::MAX,true),(1,32,usize::MAX,false),(32,0,1,true),(33,0,1,false)] {
            let data=[9u8;64];let mut input=In::new(&data,1);input.interrupts=interrupts;input.quantum=quantum;
            let mut block=[0u8;64];let mut budget=Budget::new(STEP_LIMIT).unwrap();
            let result=bounded_read(&mut input,&mut block[..length],&mut budget,77,123);
            assert_eq!(result.is_ok(),success);assert_eq!(input.calls,32);assert_eq!(budget.io_spent,32);
            assert_eq!(budget.read_bytes,if success {length as u64} else if interrupts==32 {0} else {32});
            if let Err(error)=result {assert_eq!(error.code,IO_EXHAUSTED);assert_eq!(error.stage,77);assert_eq!(error.reserved,0);}
        }
        for mode in 0..3 {
            let mut input=In::new(&[1],1);input.zero=mode==0;input.fail=mode==1;input.over=mode==2;
            let mut budget=Budget::new(STEP_LIMIT).unwrap();let mut byte=[0];
            let error=bounded_read(&mut input,&mut byte,&mut budget,77,123).unwrap_err();
            assert_eq!(input.calls,1);assert_eq!(budget.io_spent,1);assert_eq!(budget.read_bytes,0);
            assert_eq!(error.code,[IO_ZERO,IO_ERROR,IO_OVERREPORTED][mode]);assert_eq!(error.offset,123);
        }
    }
    #[test]
    fn independent_eof_exact_limit_trailing_and_transport_failures() {
        for (interrupts,success) in [(31,true),(32,false)] {
            let mut input=In::new(&[],1);input.interrupts=interrupts;let mut budget=Budget::new(STEP_LIMIT).unwrap();
            assert_eq!(eof(&mut input,&mut budget,77,123).is_ok(),success);assert_eq!(input.calls,32);assert_eq!(budget.io_spent,32);
        }
        for mode in 0..3 {
            let mut input=In::new(&[1],1);input.fail=mode==1;input.over=mode==2;let mut budget=Budget::new(STEP_LIMIT).unwrap();
            let error=eof(&mut input,&mut budget,77,123).unwrap_err();assert_eq!(error.code,[INPUT,IO_ERROR,IO_OVERREPORTED][mode]);assert_eq!(input.calls,1);
        }
    }
    #[test]
    fn independent_output_exact_limit_and_retained_partial_failures() {
        let f=crate::Fixture::new();
        for (interrupts,quantum,success,length) in [(0,1536,true,49152),(0,1535,false,49120),(31,usize::MAX,true,49152),(32,usize::MAX,false,0)] {
            let mut out=Out::new();out.interrupts=interrupts;out.quantum=quantum;
            let result=invoke(&f,&mut out,STEP_LIMIT);assert_eq!(result.is_ok(),success);assert_eq!(out.calls,32);assert_eq!(out.bytes.len(),length);assert_unaccepted(&out);
            if let Ok(outcome)=result {assert!(outcome.fixture_framing_observed());assert!(!outcome.full_replay_accepted());assert_eq!(outcome.output_attempts,32);assert_eq!(crate::get(&out.bytes,9),outcome.steps_used);}
            else {assert_eq!(result.unwrap_err().code,IO_EXHAUSTED);}
        }
        for mode in 0..4 {
            let mut out=Out::new();out.zero=mode==0;out.fail=mode==1;out.over=mode==2;
            if mode==3 {out.quantum=1024;out.fail_after=1024;}
            let error=invoke(&f,&mut out,STEP_LIMIT).unwrap_err();assert_eq!(error.code,[IO_ZERO,IO_ERROR,IO_OVERREPORTED,IO_ERROR][mode]);assert_eq!(out.calls,if mode==3 {2} else {1});assert_unaccepted(&out);
        }
    }
    #[test]
    fn independent_each_input_eof_and_error_paths_refuse_observation() {
        let fixture=crate::Fixture::new();
        for member in 0..3 {for mode in 0..5 {
            let mut f=fixture.clone();
            let lengths=[f.stream.len(),f.profile.len(),f.context.len()];
            if mode==4 {match member {0=>f.stream.push(1),1=>f.profile.push(1),_=>f.context.push(1)}}
            let mut stream=In::new(&f.stream,101);let mut profile=In::new(&f.profile,102);let mut context=In::new(&f.context,103);
            let target=match member {0=>&mut stream,1=>&mut profile,_=>&mut context};
            target.zero=mode==0;target.fail=mode==1;target.over=mode==2;target.interrupts=if mode==3 {32} else {0};target.declared=lengths[member] as u64;
            let mut out=Out::new();let outcome=analyze_core(&mut stream,&mut profile,&mut context,&mut out,STEP_LIMIT).unwrap();
            assert_eq!(outcome.decision,Decision::Invalid,"input {member} mode {mode}");assert!(!outcome.fixture_framing_observed());assert!(!outcome.stored_prefix_validated());assert_unaccepted(&out);
        }}
    }
    #[test]
    fn independent_input_and_output_metadata_drift_refuse_authority() {
        let f=crate::Fixture::new();
        for member in 0..3 {
            let mut stream=In::new(&f.stream,101);let mut profile=In::new(&f.profile,102);let mut context=In::new(&f.context,103);
            match member {0=>stream.drift_at=3,1=>profile.drift_at=3,_=>context.drift_at=3};
            let mut out=Out::new();let outcome=analyze_core(&mut stream,&mut profile,&mut context,&mut out,STEP_LIMIT).unwrap();
            assert_eq!(outcome.decision,Decision::Invalid);assert_eq!(outcome.observation.code,DRIFT);assert!(!outcome.fixture_framing_observed());assert_unaccepted(&out);
        }
        for (drift,stamp_error,length) in [(2,usize::MAX,0),(3,usize::MAX,49152),(usize::MAX,2,0),(usize::MAX,3,49152)] {
            let mut out=Out::new();out.drift_at=drift;out.stamp_error_at=stamp_error;assert!(invoke(&f,&mut out,STEP_LIMIT).is_err());assert_eq!(out.bytes.len(),length);assert_unaccepted(&out);
        }
    }
    #[test]
    fn independent_allocation_results_and_inventory_value_layouts() {
        fn unavailable(_: &mut Vec<u8>,_:usize)->Result<(),TryReserveError> {let mut value=Vec::<u8>::new();value.try_reserve_exact(usize::MAX)}
        fn no_reserve(_: &mut Vec<u8>,_:usize)->Result<(),TryReserveError> {Ok(())}
        let mut budget=Budget::new(STEP_LIMIT).unwrap();assert!(matches!(Arena::new_with(&mut budget,unavailable),Err(AnalyzerError{code:ALLOCATION,..})));
        let mut budget=Budget::new(STEP_LIMIT).unwrap();assert!(matches!(Arena::new_with(&mut budget,no_reserve),Err(AnalyzerError{code:CAPACITY,..})));
        assert!(Budget::new(STEP_LIMIT+1).is_err());assert!(Budget::new(REPORT_RESERVE+IO_RESERVE-1).is_err());
        let mut budget=Budget::new(REPORT_RESERVE+IO_RESERVE).unwrap();assert!(matches!(Arena::new(&mut budget),Err(AnalyzerError{code:BUDGET,..})));
        use std::mem::size_of;
        assert_eq!(size_of::<ReplayOutcome>(),104);assert_eq!(size_of::<AnalyzerError>(),32);assert_eq!(size_of::<Result<ReplayOutcome,AnalyzerError>>(),104);
        assert_eq!(size_of::<Result<(),AnalyzerError>>(),40);assert_eq!(size_of::<std::fs::Metadata>(),144);assert_eq!(size_of::<io::Result<std::fs::Metadata>>(),152);
        assert_eq!(size_of::<Stamp>(),72);assert_eq!(size_of::<std::array::IntoIter<Region,12>>(),304);assert_eq!(size_of::<Budget>(),56);
    }
    #[test]
    fn independent_actual_budget_boundary_and_malformed_tail_override() {
        let fixture=crate::Fixture::new();
        let mut low=REPORT_RESERVE+IO_RESERVE+ARENA_BYTES as u64/8+640000;
        let mut high=low+65536+RECORD_PREFLIGHT+1024;
        while low<high {
            let middle=low+(high-low)/2;let mut out=Out::new();
            let complete=invoke(&fixture,&mut out,middle).is_ok_and(|x|x.fixture_framing_observed());
            if complete {high=middle;} else {low=middle+1;}
        }
        let mut out=Out::new();let boundary=invoke(&fixture,&mut out,low).unwrap();assert!(boundary.fixture_framing_observed());assert_eq!(boundary.decision,Decision::Unavailable);assert!(boundary.steps_used<=low);
        let mut out=Out::new();let prior=invoke(&fixture,&mut out,low-1).unwrap();assert_eq!(prior.decision,Decision::AnalysisLimited);assert!(!prior.fixture_framing_observed());assert!(prior.framed_records<13);assert_unaccepted(&out);
        let mut damaged=fixture;damaged.footer(63,1);let mut out=Out::new();let invalid=invoke(&damaged,&mut out,low-1).unwrap();assert_eq!(invalid.decision,Decision::Invalid);assert!(!invalid.fixture_framing_observed());assert_unaccepted(&out);
        println!("INDEPENDENT_BUDGET_MINIMUM={low} PRIOR_FRAMED={} PRIOR_STEPS={}",prior.framed_records,prior.steps_used);
    }
}
