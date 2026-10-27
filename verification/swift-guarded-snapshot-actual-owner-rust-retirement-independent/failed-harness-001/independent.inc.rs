
        // All functions below are additive private cfg(test) review methods.
        // Frozen producer methods and every production byte are unchanged.
        fn independent_retained_v1<'r>(owner:AdmittedImmutableOwnerCoreV1<'r,Guard>, trace:&Rc<Trace>) -> PrepaidInputOwnerV1<'r,Guard> {
            let before=owner.owned.reservation.root.usage.get();
            let cleanup=owner.owned.reservation.cleanup_left;
            let operation=owner.owned.reservation.operation_left;
            let storage=owner.owned.reservation.storage_left;
            let retained=match retire_acquired_owner_core_v1(owner.owned,&mut bridge(trace)) {
                AcquisitionRetirementOutcomeV1::Retained(v)=>v,
                AcquisitionRetirementOutcomeV1::Complete(_)=>panic!("independent: issued scope minted Complete"),
            };
            assert!(!retained.retirement_started);
            assert_eq!(retained.reservation.cleanup_left,cleanup);
            assert_eq!(retained.reservation.operation_left,operation);
            assert_eq!(retained.reservation.storage_left,storage);
            assert_eq!(retained.reservation.root.usage.get(),before);
            retained
        }
        fn independent_usage_v1()->LoaderUsageV1 { LoaderUsageV1 {read_calls:[11,13,17,19],read_bytes:[23,29,31,37],
            hash_bytes:41,source_equality_bytes:43,allocated_peak_requested:47} }
        #[test]
        fn independent_i01_all_51_frozen_binary_substitutions_v1() {
            let mut r=root();r.policy.path_caps=[6,5,7,6,10];r.policy.packet_cap=98;
            assert!(parse_build(INDEPENDENT_MIXLBD01).is_ok());
            assert!(parse_session(INDEPENDENT_MIXLSE01).is_ok());
            let paths=decode_path_packet_v1(INDEPENDENT_MIXPTH01,&r.policy).unwrap();
            assert_eq!(paths,[b"source".as_slice(),b"build",b"session",b"rows-\xff",b"snapshot-\xfe"]);
            let vectors=independent_binary_vectors_v1();assert_eq!(vectors.len(),51);
            let mut strict=0;
            for (id,kind,bytes,owner_only,diagnostic) in vectors {
                if kind==2 {assert!(decode_path_packet_v1(&bytes,&r.policy).is_err(),"{}",id);continue;}
                let err=if kind==0 {parse_build(&bytes).err()} else {parse_session(&bytes).err()};
                if owner_only {
                    assert!(err.is_none(),"{} old parser must remain positive",id);
                    // Same absolute frozen replacement at the same session byte
                    // offset, applied to actual proof-valid acquisition bodies.
                    let selected=root();let trace=Rc::new(Trace::default());let mut acquired=acquired(&selected,&trace);
                    let actual=acquired.actual.as_mut().unwrap();
                    let f=match &mut actual.partial.slots[2] {ActualInputSlotV1::Owned(v)=>v,_=>panic!()};
                    let (at,n)=if id=="session-zero-source-extent" {(32,0)}
                        else if id=="session-nonregular-identity" {(536,0o040600)}
                        else {let i=id.rsplit('-').next().unwrap().parse::<usize>().unwrap();(72+i*8,0)};
                    f.body.as_mut().unwrap().bytes[at..at+8].copy_from_slice(&(n as u64).to_le_bytes());
                    assert!(parse_session(f.body.as_ref().unwrap().slice_v1()).is_ok());
                    let held=match complete_admission_core_v1(acquired,TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(&trace)) {
                        OwnedAdmissionCoreOutcomeV1::Refused(v)=>v,_=>panic!("{} owner accepted invalid input",id)};
                    let original=held.actual.as_ref().unwrap().partial.original.as_ref().unwrap();
                    assert_eq!(original.kind,BootstrapFailureV1::Record,"{}",id);
                    assert!(trace.drops.borrow().is_empty());assert_eq!(selected.usage.get().storage,1_000_000);
                    drop(held);assert_eq!(trace.drops.borrow().len(),13);assert_eq!(selected.usage.get().storage,1_000_000);
                    strict+=1;continue;
                }
                let err=err.unwrap_or_else(||panic!("{} accepted",id));
                let expected=diagnostic.split('/').collect::<Vec<_>>();
                assert_eq!(format!("{:?}",err.kind),expected[0],"{}",id);
                assert_eq!(format!("{:?}",err.role),expected[1],"{}",id);
                let offset=if expected[2]=="current cursor" {
                    let index=id.rsplit('-').next().unwrap().parse::<usize>().unwrap();
                    let base=if kind==0 {INDEPENDENT_MIXLBD01}else{INDEPENDENT_MIXLSE01};
                    let start=if kind==0 {48}else{40};512+(0..index).map(|i|word(base,start+i*8)).sum::<u64>()
                }else{expected[2].parse::<u64>().unwrap()};
                assert_eq!(err.offset,offset,"{}",id);assert_eq!(err.attempts,0,"{}",id);
            }
            assert_eq!(strict,7);
            eprintln!("INDEPENDENT_BINARY51 exact_frozen_bytes=51 strict_owner_mapped=7 original_parser_positives_preserved=true");
        }
        fn independent_mutate_provenance_v1(p:&mut LoaderProvenanceV1,g:usize,a:usize,b:usize,delta:u64) {
            match g {
                0=>p.source[a]^=delta as u8,1=>p.manifest[a]^=delta as u8,2=>p.build[a]^=delta as u8,
                3=>p.session[a]^=delta as u8,4=>p.executable[a]^=delta as u8,5=>p.nonce[a]^=delta as u8,
                6=>match a {0=>p.validation_budget.source_bytes^=delta as usize,1=>p.validation_budget.metadata_bytes^=delta as usize,
                    2=>p.validation_budget.scratch_bytes^=delta as usize,3=>p.validation_budget.work_credits^=delta,4=>p.validation_budget.deadline_ms^=delta,_=>panic!()},
                7=>p.source_extent^=delta,
                8=>{let f=&mut p.identities[a];match b {0=>f.dev^=delta,1=>f.inode^=delta,2=>f.bytes^=delta,3=>f.mode^=delta,
                    4=>f.mtime=((f.mtime as u64)^delta) as i64,5=>f.mtime_ns=((f.mtime_ns as u64)^delta) as i64,
                    6=>f.ctime=((f.ctime as u64)^delta) as i64,7=>f.ctime_ns=((f.ctime_ns as u64)^delta) as i64,_=>panic!()}},_=>panic!()
            }
        }
        #[test]
        fn independent_i02_all_230_frozen_provenance_deltas_actual_proof_v1() {
            let vectors=independent_provenance_vectors_v1();assert_eq!(vectors.len(),230);
            for optional in [false,true] { for &(id,group,a,b,delta) in &vectors {
                let r=root();let trace=Rc::new(Trace::default());let mut owner=admitted(&r,&trace);
                let usage=independent_usage_v1();
                if !optional && id=="correlation-source-byte-00" {
                    let encoded=test_provenance_encoding_v1(&owner.expected);
                    let hex=encoded.iter().map(|b|format!("{:02x}",b)).collect::<String>();
                    eprintln!("INDEPENDENT_ACTUAL_PROVENANCE_BASELINE496 {}",hex);
                }
                // Admission already prepaid ingress. Later exhaustion must not
                // renew it or borrow cleanup funds to preserve originals.
                owner.owned.reservation.operation_left=0;owner.owned.reservation.storage_left=0;
                let (original,held,pointer)={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();
                    let mut supplied=carrier(&owner.expected,&trace);supplied.usage=usage;
                    if !optional {drop(supplied.executable.take());}
                    let selected=supplied.selected.as_mut().unwrap();let pointer=selected.proof.source().as_ptr();
                    independent_mutate_provenance_v1(&mut selected.provenance,group,a,b,delta);
                    let (original,held)=match correlate_core_v1(attempt,supplied,&expected) {Err(v)=>v,Ok(_)=>panic!("{} accepted",id)};
                    (original,held,pointer)};
                assert_eq!(original.kind,BootstrapFailureV1::Correlation(group),"{}",id);
                assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
                let retained=independent_retained_v1(owner,&trace);
                assert_eq!(*trace.drops.borrow(),if optional {vec![]}else{vec![23]});
                assert_eq!(held.usage,usage);assert_eq!(held.files.each_ref().map(|v|v.tag),[20,21,22]);
                assert_eq!(held.executable.as_ref().map(|v|v.tag),if optional {Some(23)}else{None});
                drop(retained);
                let proof=&held.selected.as_ref().unwrap().proof;assert_eq!(proof.source().as_ptr(),pointer);assert_eq!(proof.source().len(),1947);
                let before=r.usage.get();assert_eq!(before.storage,1_000_000);drop(held);assert_eq!(r.usage.get(),before);
                assert_eq!(trace.drops.borrow().len(),17);
                assert_eq!(refusal(r.reserve_before_any_input_effect_v1(ReviewedAcquisitionQuoteV1 {acquisition_work:1,cleanup_work:1,peak_storage:1})),BootstrapFailureV1::AlreadyReserved);
            }}
            eprintln!("INDEPENDENT_PROVENANCE230 vectors=230 optional_shapes=2 actual_cases=460 proof_pointer_and_all_usage_preserved=true issued_charge_permanent=true");
        }
        struct IndependentScheduleBridgeV1 { inner:TestBridge,responses:Vec<i64>,at:usize,bytes:usize,
            marker_drops:std::sync::Arc<std::sync::atomic::AtomicUsize> }
        impl InputBridgeV1<Guard> for IndependentScheduleBridgeV1 {
            fn metadata_v1(&mut self,p:PaidOperationV1<'_>,r:&mut Guard,s:usize)->Result<FileIdentityV1,OriginalAcquisitionFailureV1>{self.inner.metadata_v1(p,r,s)}
            fn offset_v1(&mut self,p:PaidOperationV1<'_>,r:&mut Guard,s:usize)->Result<u64,OriginalAcquisitionFailureV1>{self.inner.offset_v1(p,r,s)}
            fn allocate_v1(&mut self,p:PaidOperationV1<'_>,n:usize,b:u64,s:usize)->Result<ImmutableOwnedBytesV1,OriginalAcquisitionFailureV1>{self.inner.allocate_v1(p,n,b,s)}
            fn hash_v1(&mut self,p:PaidOperationV1<'_>,b:&[u8],s:usize)->Result<[u8;32],OriginalAcquisitionFailureV1>{self.inner.hash_v1(p,b,s)}
            fn retire_v1(&mut self,p:PaidOperationV1<'_>,r:Guard,s:usize)->Result<(),(Guard,OriginalAcquisitionFailureV1)>{self.inner.retire_v1(p,r,s)}
            fn read_v1(&mut self,_p:PaidOperationV1<'_>,r:&mut Guard,out:&mut[u8])->io::Result<usize> {
                let response=*self.responses.get(self.at).expect("read beyond exact frozen schedule");self.at+=1;
                if response==-1 {return Err(io::Error::from(io::ErrorKind::Interrupted));}
                if response==-2 {return Err(io::Error::new(io::ErrorKind::Other,OriginalIoMarkerV1 {id:0x7712,drops:self.marker_drops.clone()}));}
                let n=response as usize;
                if n<=out.len() {out[..n].fill(0x71);r.position+=n;self.bytes+=n;}Ok(n)
            }
        }
        #[test]
        fn independent_i03_all_12_frozen_read_schedules_actual_core_v1() {
            let vectors=independent_read_vectors_v1();assert_eq!(vectors.len(),12);
            for (id,extent,calls,bytes,responses,outcome) in vectors {
                let r=root();let trace=Rc::new(Trace::default());let mut paid=paid(&r);
                let resource=guard(77,vec![0;extent],&trace);let initial=resource.identity;
                let mut owned=RetainedIdentityFileV1 {role:0,resource,initial,body:None,sha256:None};
                let drops=std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
                let mut b=IndependentScheduleBridgeV1 {inner:bridge(&trace),responses,at:0,bytes:0,marker_drops:drops.clone()};
                let old=r.usage.get();let result=read_owned_body_once_v1(&mut paid,&mut owned,extent,&mut b);
                assert_eq!(b.at,calls,"{}",id);assert_eq!(b.bytes,bytes,"{}",id);
                let body=owned.body.as_ref().unwrap();assert_eq!(body.bytes.len(),extent);
                let expected_initialized=if outcome==5 {extent}else{bytes};assert_eq!(body.initialized,expected_initialized,"{}",id);
                assert_eq!(body.allocation_bound,extent as u64+26);assert_eq!(trace.storage_at_allocation.get(),old.storage);
                match outcome {
                    0=>{assert!(result.is_ok(),"{}",id);assert_eq!(body.initialized,extent);assert!(owned.sha256.is_some());},
                    n=>{let e=match result {Err(v)=>v,Ok(())=>panic!("{} accepted",id)};
                        assert_eq!(e.kind,match n {1=>BootstrapFailureV1::Attempts,2=>BootstrapFailureV1::Io,3=>BootstrapFailureV1::ShortInput,4=>BootstrapFailureV1::OverreportedRead,5=>BootstrapFailureV1::ExtraInput,_=>panic!()},"{}",id);
                        if n==2 {let marker=e.io.as_ref().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();assert_eq!(marker.id,0x7712);assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),0);}
                        assert!(owned.sha256.is_none());drop(e);
                    }
                }
                let before_retry=(b.at,paid.operation_left,paid.storage_left);
                assert_eq!(match read_owned_body_once_v1(&mut paid,&mut owned,extent,&mut b) {Err(v)=>v.kind,_=>panic!()},BootstrapFailureV1::AlreadyAttempted);
                assert_eq!((b.at,paid.operation_left,paid.storage_left),before_retry);
                assert!(trace.drops.borrow().is_empty());drop(owned);drop(paid);assert_eq!(*trace.drops.borrow(),vec![77]);assert_eq!(r.usage.get(),old);
                if outcome==2 {assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),1);}
            }
            eprintln!("INDEPENDENT_READ12 exact_response_queues=12 no33rd_read=true original_io_and_partial_allocation_retained=true no_retry=true");
        }
        // This helper uses ONLY the production-visible opaque File facade API.
        // It is compiled but never called: no File or native fixture is created.
        // The result type lacks the input's root lifetime and can be returned
        // after consuming its owner. No private expected/result fields needed.
        #[allow(dead_code)]
        fn independent_facade_result_escape_signature_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,supplied:SuppliedLoaderCarrierV1)->OwnedCorrelationOutcomeV1 {
            let result={let(expected,attempt)=owner.correlation_scope_v1().unwrap();correlate_admitted_loader_v1(attempt,supplied,&expected)};
            retire_admitted_owner_v1(owner);result
        }
        #[test]
        fn independent_i04_result_outlives_original_owner_and_ledger_v1() {
            let trace=Rc::new(Trace::default());
            let (held,pointer,charged_at_ledger_end)={let r=root();let owner=admitted(&r,&trace);
                let (held,pointer)={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();let c=carrier(&owner.expected,&trace);
                    let pointer=c.selected.as_ref().unwrap().proof.source().as_ptr();let held=match correlate_core_v1(attempt,c,&expected) {Ok(v)=>v,Err(_)=>panic!()};(held,pointer)};
                let retained=independent_retained_v1(owner,&trace);drop(retained);
                assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());
                let charge=r.usage.get();assert_eq!(charge.storage,1_000_000);(held,pointer,charge)};
            // The originating ledger has ended; carrier remains accessible.
            assert_eq!(held.selected.as_ref().unwrap().proof.source().as_ptr(),pointer);
            assert_eq!(held.selected.as_ref().unwrap().proof.source().len(),1947);
            assert_eq!(held.files.each_ref().map(|v|v.tag),[20,21,22]);assert_eq!(held.executable.as_ref().unwrap().tag,23);
            assert_eq!(charged_at_ledger_end.storage,1_000_000);drop(held);assert_eq!(trace.drops.borrow().len(),17);
            eprintln!("INDEPENDENT_ROOT_LIFETIME carrier_accessible_after_ledger_end=true last_live_ledger_charge={} Complete_or_refund=false full_root_charge_lifetime_established=false",charged_at_ledger_end.storage);
        }
        #[test]
        fn independent_i05_unissued_immediate_token_release_drop_and_no_renewal_v1() {
            for release in [false,true] {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                let before=r.usage.get();let token=match retire_acquired_owner_core_v1(owner.owned,&mut bridge(&trace)) {
                    AcquisitionRetirementOutcomeV1::Complete(v)=>v,_=>panic!("unissued positive control")};
                assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get(),before);
                if release {token.release_v1();}else{drop(token);}
                let after=r.usage.get();assert_eq!(after.work,before.work);assert_eq!(after.peak,before.peak);
                assert_eq!(after.storage,if release {0}else{before.storage});
                assert_eq!(refusal(r.reserve_before_any_input_effect_v1(ReviewedAcquisitionQuoteV1 {acquisition_work:1,cleanup_work:1,peak_storage:1})),BootstrapFailureV1::AlreadyReserved);
                assert_eq!(r.usage.get(),after);
            }
        }
        #[test]
        fn independent_i06_issued_barrier_preempts_failing_or_panicking_bridge_v1() {
            for fail in 0..13 {for panic in [false,true] {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                {let(_expected,_attempt)=owner.correlation_scope_core_v1().unwrap();}
                let mut b=bridge(&trace);if panic {b.unwind_retirement=Some(fail);}else{b.fail_retirement=Some(fail);}
                let before=r.usage.get();let cleanup=owner.owned.reservation.cleanup_left;
                let retained=match retire_acquired_owner_core_v1(owner.owned,&mut b) {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!()};
                assert_eq!(retained.reservation.cleanup_left,cleanup);assert!(!retained.retirement_started);assert!(trace.drops.borrow().is_empty());
                let retained=match retire_acquired_owner_core_v1(retained,&mut b) {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!()};
                assert_eq!(retained.reservation.cleanup_left,cleanup);assert!(trace.drops.borrow().is_empty());drop(retained);assert_eq!(r.usage.get(),before);
            }}
        }
