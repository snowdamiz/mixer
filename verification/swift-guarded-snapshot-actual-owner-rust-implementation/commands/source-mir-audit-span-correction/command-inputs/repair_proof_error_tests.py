from pathlib import Path
b=Path(__file__).parent;p=b/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs';s=p.read_text()
a=s.index('        #[test] fn h09_distinct_guard_handles_same_identity_real_proof_only_one_leaf()')
z=s.index('        #[test] fn h08_cross_owner_equal_metadata_retains_complete_carrier()',a)
s=s[:a]+'''        struct OwnedSentinelResultV1 {
            selected:CorrelatedSelectedProfileV1, files:[Guard;3],executable:Option<Guard>,usage:LoaderUsageV1,
        }
        fn leaf_sentinel_return_owned_v1(matched:LoaderCarrierCoreV1<Guard>,leaf:&Cell<usize>)->OwnedSentinelResultV1 {
            let LoaderCarrierCoreV1 {selected,files,executable,usage}=matched;
            let selected=CorrelatedSelectedProfileV1(selected.unwrap());
            leaf.set(leaf.get()+1);
            OwnedSentinelResultV1 {selected,files,executable,usage}
        }
        #[test] fn h09_distinct_guard_handles_same_identity_real_proof_only_one_leaf() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let (expected,attempt)=owner.correlation_scope_core_v1().unwrap();let c=carrier(&owner.expected,&trace);
            assert!(c.files[0].tag!=0);let proof_source=c.selected.as_ref().unwrap().proof.source().as_ptr();
            let leaf=Cell::new(0);let matched=match correlate_core_v1(attempt,c,&expected) {Ok(v)=>v,Err(_)=>panic!("correlation")};
            let result=leaf_sentinel_return_owned_v1(matched,&leaf);
            // The owned result retains the SAME real validator-created Box and
            // every original File substitute through this complete inspection.
            assert_eq!(result.selected.0.proof.source().as_ptr(),proof_source);
            assert_eq!(result.selected.0.source(),body_v1(owner.owned.actual.as_ref().unwrap(),0).unwrap());
            assert_eq!(result.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(result.executable.as_ref().unwrap().tag,23);
            assert_eq!(result.usage.hash_bytes,912);assert_eq!(leaf.get(),1);assert!(trace.drops.borrow().is_empty());
            assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
            drop(result);assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);
            let AdmittedImmutableOwnerCoreV1 {owned,..}=owner;
            let token=match retire_acquired_owner_core_v1(owned,&mut bridge(&trace)) {AcquisitionRetirementOutcomeV1::Complete(v)=>v,_=>panic!("typed retirement")};
            assert_eq!(*trace.drops.borrow(),(20..24).chain(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get().storage,1_000_000);
            token.release_v1();assert_eq!(r.usage.get().storage,0);
        }
''' +s[z:]
a=s.index('        #[test] fn h10_whole_error_result')
z=s.index('        #[test] fn h11_retirement_order',a)
s=s[:a]+'''        #[derive(Debug)]
        struct OriginalIoMarkerV1 { id:u64,drops:std::sync::Arc<std::sync::atomic::AtomicUsize> }
        impl std::fmt::Display for OriginalIoMarkerV1 {fn fmt(&self,f:&mut std::fmt::Formatter<'_>)->std::fmt::Result {write!(f,"original-test-marker-{}",self.id)}}
        impl std::error::Error for OriginalIoMarkerV1 {}
        impl Drop for OriginalIoMarkerV1 {fn drop(&mut self){self.drops.fetch_add(1,std::sync::atomic::Ordering::SeqCst);}}
        #[test] fn h10_whole_error_result_files_usage_move_before_live_refusal() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();owner.attempt_taken.set(false);
            let mut c=carrier(&owner.expected,&trace);let failure=validate_swift_reactor(b"bad",owner.expected.validation_budget,&Cancellation::default()).err().unwrap();
            let drops=std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let original_io=io::Error::new(io::ErrorKind::Other,OriginalIoMarkerV1 {id:0x9197,drops:drops.clone()});
            let payload_before=original_io.get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap() as *const OriginalIoMarkerV1;
            c.selected=Err(LoaderFailureV1 {io:Some(original_io),validation:Some(failure),..LoaderFailureV1::new(Refusal::Validation,Role::Source,7,3)});
            let (original,c)=match correlate_core_v1(attempt,c,&expected) {Err(v)=>v,Ok(_)=>panic!()};assert_eq!(original.kind,BootstrapFailureV1::LiveOwner);
            let e=c.selected.as_ref().err().unwrap();let payload_after=e.io.as_ref().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();
            assert_eq!(payload_after.id,0x9197);assert!(std::ptr::eq(payload_before,payload_after));assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),0);
            assert!(e.validation.is_some());assert_eq!(e.offset,7);assert_eq!(e.attempts,3);
            assert_eq!(c.files.each_ref().map(|r|r.tag),[20,21,22]);assert_eq!(c.executable.as_ref().unwrap().tag,23);assert_eq!(c.usage.hash_bytes,912);
            assert!(trace.drops.borrow().is_empty());drop(c);assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),1);
            assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);assert_eq!(r.usage.get().storage,1_000_000);
        }
''' +s[z:]
p.write_text(s)
p=b/'run_bounded.py';s=p.read_text().replace("('production','production-repair1')","('production','production-repair1','production-final')").replace("('build-debug','build-opt','build-debug-repair1')","('build-debug','build-opt','build-debug-repair1','build-debug-proof-error','build-opt-proof-error')").replace("('run-debug','run-opt','run-debug-repair1')","('run-debug','run-opt','run-debug-repair1','run-debug-proof-error','run-opt-proof-error')");p.write_text(s)
