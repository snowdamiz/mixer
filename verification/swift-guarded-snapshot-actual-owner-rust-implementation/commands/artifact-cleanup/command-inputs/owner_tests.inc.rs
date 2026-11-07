    #[cfg(test)]
    mod prepaid_actual_owner_v1 {
        use super::*;
        use std::rc::Rc;
        use std::panic::{catch_unwind,AssertUnwindSafe};
        #[derive(Default)]
        struct Trace { drops: std::cell::RefCell<Vec<usize>>, allocated: Cell<usize>, read_calls: Cell<usize>, storage_at_allocation: Cell<u64> }
        struct Guard {
            tag:usize, identity:FileIdentityV1, data:Vec<u8>, position:usize,
            interruptions:u32, chunk:usize, overreported:bool, error:Option<i32>,
            meta_fail:bool, trace:Rc<Trace>,
        }
        impl Drop for Guard { fn drop(&mut self) { self.trace.drops.borrow_mut().push(self.tag); } }
        struct TestBridge { trace:Rc<Trace>, fail_allocation:bool, fail_retirement:Option<usize>, unwind_retirement:Option<usize> }
        impl InputBridgeV1<Guard> for TestBridge {
            fn metadata_v1(&mut self,_paid:PaidOperationV1<'_>,r:&mut Guard,slot:usize)->Result<FileIdentityV1,OriginalAcquisitionFailureV1> {
                if r.meta_fail { return Err(OriginalAcquisitionFailureV1::io(slot,0,0,io::Error::from_raw_os_error(817))); }
                Ok(r.identity)
            }
            fn offset_v1(&mut self,_paid:PaidOperationV1<'_>,r:&mut Guard,_slot:usize)->Result<u64,OriginalAcquisitionFailureV1> { Ok(r.position as u64) }
            fn allocate_v1(&mut self,paid:PaidOperationV1<'_>,n:usize,bound:u64,slot:usize)->Result<ImmutableOwnedBytesV1,OriginalAcquisitionFailureV1> {
                self.trace.allocated.set(self.trace.allocated.get()+1);
                self.trace.storage_at_allocation.set(paid._root.usage.get().storage);
                if self.fail_allocation {
                    let mut empty=Vec::<u8>::new();
                    let original=empty.try_reserve(usize::MAX).unwrap_err();
                    return Err(OriginalAcquisitionFailureV1 { allocation:Some(original),..OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Allocation,slot) });
                }
                // Test-only std allocation exercises the same pre-call ordering;
                // it is not an assertion about a native allocation/slack price.
                Ok(ImmutableOwnedBytesV1 { bytes:vec![0;n].into_boxed_slice(),initialized:0,allocation_bound:bound })
            }
            fn read_v1(&mut self,_paid:PaidOperationV1<'_>,r:&mut Guard,output:&mut[u8])->io::Result<usize> {
                self.trace.read_calls.set(self.trace.read_calls.get()+1);
                if r.interruptions>0 { r.interruptions-=1;return Err(io::Error::from(io::ErrorKind::Interrupted)); }
                if let Some(code)=r.error.take() { return Err(io::Error::from_raw_os_error(code)); }
                if r.overreported { return Ok(output.len()+1); }
                let n=output.len().min(r.chunk).min(r.data.len().saturating_sub(r.position));
                output[..n].copy_from_slice(&r.data[r.position..r.position+n]);r.position+=n;Ok(n)
            }
            fn hash_v1(&mut self,_paid:PaidOperationV1<'_>,bytes:&[u8],_slot:usize)->Result<[u8;32],OriginalAcquisitionFailureV1> {
                // Fixed test digest labels, not cryptographic authentication.
                Ok(test_digest(bytes))
            }
            fn retire_v1(&mut self,_paid:PaidOperationV1<'_>,r:Guard,slot:usize)->Result<(),(Guard,OriginalAcquisitionFailureV1)> {
                if self.unwind_retirement==Some(slot) { panic!("owned retirement test unwind"); }
                if self.fail_retirement==Some(slot) { return Err((r,OriginalAcquisitionFailureV1::io(slot,0,0,io::Error::from_raw_os_error(829)))); }
                drop(r);Ok(())
            }
        }
        fn test_digest(bytes:&[u8])->[u8;32] { [bytes.first().copied().unwrap_or(0);32] }
        fn root()->BootstrapLedgerV1 {
            BootstrapLedgerV1 { policy:FixtureBootstrapPolicyV1 { role_caps:[100_000;12],path_caps:[9000;5],packet_cap:100_000,
                validation:SwiftValidationBudget { source_bytes:1947,metadata_bytes:1_000_000,scratch_bytes:65_536,work_credits:1_000_000,deadline_ms:10_000 },
                product:SwiftRunBudget::default(),allocation_slack:7,original_failure_backing:19,
                bridge:BridgePricesV1 { metadata:1,offset:1,allocation:1,read:1,hash_per_byte:1,path_per_byte:1,
                    correlation:31,correlation_storage:43,retirement:1 } },
                work_limit:10_000_000,storage_limit:10_000_000,usage:Cell::new(BootstrapUsageV1::default()),reserved:Cell::new(false) }
        }
        fn paid(root:&BootstrapLedgerV1)->AcquisitionReservationV1<'_> { root.reserve_before_any_input_effect_v1(
            ReviewedAcquisitionQuoteV1 { acquisition_work:1_000_000,cleanup_work:100,peak_storage:1_000_000 }).unwrap() }
        fn identity_for(tag:usize,n:usize)->FileIdentityV1 { FileIdentityV1 { dev:19,inode:tag as u64+1,bytes:n as u64,mode:0o100600,
            mtime:i64::MIN,mtime_ns:-1,ctime:i64::MAX,ctime_ns:-9 } }
        fn guard(tag:usize,data:Vec<u8>,trace:&Rc<Trace>)->Guard { Guard { tag,identity:identity_for(tag,data.len()),data,
            position:0,interruptions:0,chunk:usize::MAX,overreported:false,error:None,meta_fail:false,trace:trace.clone() } }
        fn bridge(trace:&Rc<Trace>)->TestBridge { TestBridge { trace:trace.clone(),fail_allocation:false,fail_retirement:None,unwind_retirement:None } }
        fn claims()->UnverifiedProfileDigestBytesV1 { UnverifiedProfileDigestBytesV1::test_prepaid_actual_owner_fixed_claims_v1() }
        fn word_put(bytes:&mut[u8],at:usize,n:u64) { bytes[at..at+8].copy_from_slice(&n.to_le_bytes()); }
        fn packet(paths:[&[u8];5])->Vec<u8> {
            let mut out=vec![0;64];out[..8].copy_from_slice(b"MIXPTH01");word_put(&mut out,8,1);
            for (i,path) in paths.into_iter().enumerate() { word_put(&mut out,24+i*8,path.len() as u64);out.extend_from_slice(path); }
            let n=out.len();word_put(&mut out,16,n as u64);out
        }
        fn list(value:&[u8])->Vec<u8> { let mut out=1u64.to_le_bytes().to_vec();out.extend_from_slice(&(value.len() as u64).to_le_bytes());out.extend_from_slice(value);out }
        fn encode_record(magic:&[u8;8],sections:[&[u8];4],offset:usize)->Vec<u8> {
            let mut out=vec![0;512];out[..8].copy_from_slice(magic);word_put(&mut out,8,1);word_put(&mut out,16,512);
            for (i,s) in sections.into_iter().enumerate() { word_put(&mut out,offset+i*8,s.len() as u64);out.extend_from_slice(s); }
            let n=out.len();word_put(&mut out,24,n as u64);out
        }
        fn leb(mut n:u32,out:&mut Vec<u8>) { loop { let b=(n&127) as u8;n>>=7;out.push(b|if n>0 {128}else{0});if n==0{return;} } }
        fn text(s:&[u8],out:&mut Vec<u8>) { leb(s.len() as u32,out);out.extend_from_slice(s); }
        fn section(id:u8,bytes:&[u8],out:&mut Vec<u8>) { out.push(id);leb(bytes.len() as u32,out);out.extend_from_slice(bytes); }
        fn wasm_source()->Vec<u8> {
            // Independently assembled product-owned validator component input.
            // It is never emitted to disk or passed to the genuine File loader.
            use crate::{Type,experimental_wasi::WasiFunction};
            fn ty(t:Type)->u8 { match t {Type::I32=>0x7f,Type::I64=>0x7e,Type::F32=>0x7d,Type::F64=>0x7c} }
            let mut out=b"\0asm\x01\0\0\0".to_vec();let mut types=vec![37];
            for import in WasiFunction::ALL { types.push(0x60);leb(import.parameters().len() as u32,&mut types);
                types.extend(import.parameters().iter().copied().map(ty));leb(import.results().len() as u32,&mut types);types.extend(import.results().iter().copied().map(ty)); }
            types.extend_from_slice(&[0x60,0,0,0x60,0,1,0x7f,0x60,0,0]);section(1,&types,&mut out);
            let mut imports=vec![34];for (i,import) in WasiFunction::ALL.into_iter().enumerate() {
                text(b"wasi_snapshot_preview1",&mut imports);text(import.name(),&mut imports);imports.push(0);leb(i as u32,&mut imports); }
            section(2,&imports,&mut out);let mut functions=vec![64];for i in 0..64 {leb(if i==0 {36}else if i==28 {35}else{34},&mut functions);}
            section(3,&functions,&mut out);let mut table=vec![1,0x70,1];leb(46713,&mut table);leb(46713,&mut table);section(4,&table,&mut out);
            let mut memory=vec![1,0];leb(584,&mut memory);section(5,&memory,&mut out);section(6,&[1,0x7f,1,0x41,0,0x0b],&mut out);
            let mut exports=vec![3];for (name,kind,index) in [(b"memory".as_slice(),2,0),(b"_initialize".as_slice(),0,35),(b"mixer_fieldlog_corpus_v1".as_slice(),0,62)] {
                text(name,&mut exports);exports.push(kind);leb(index,&mut exports); }
            section(7,&exports,&mut out);let mut code=vec![64];for i in 0..64 { let body:&[u8]=if i==28 {&[0,0x41,0,0x0b]}else{&[0,0x0b]};leb(body.len() as u32,&mut code);code.extend_from_slice(body); }
            section(10,&code,&mut out);assert_eq!(out.len(),1947);out
        }
        fn data_set(policy:&FixtureBootstrapPolicyV1)->[Vec<u8>;13] {
            let source=wasm_source();let executable=vec![0x45;17];let compiler=vec![0x43;9];
            let version=b"rust-test-only".to_vec();let manifest=b"exact-source-shape-test".to_vec();
            let argv=list(b"rustc");let env=list(b"A=B");let proc_argv=list(b"host");let proc_env=list(b"X=Y");
            let mut build=encode_record(b"MIXLBD01",[&manifest,&argv,&env,&version],48);
            word_put(&mut build,32,146);word_put(&mut build,40,11);word_put(&mut build,80,executable.len() as u64);
            build[88..107].copy_from_slice(b"aarch64-apple-darwin");
            for (i,data) in [&manifest,&argv,&env,&version,&compiler,&executable].into_iter().enumerate() {build[152+i*32..184+i*32].copy_from_slice(&test_digest(data));}
            let source_id=identity_for(0,source.len()).encode();
            let mut session=encode_record(b"MIXLSE01",[&source_id,&proc_argv,&proc_env,b"/test"],40);
            word_put(&mut session,32,source.len() as u64);
            for (at,n) in [(72,policy.validation.source_bytes as u64),(80,policy.validation.metadata_bytes as u64),(88,policy.validation.scratch_bytes as u64),(96,policy.validation.work_credits),(104,policy.validation.deadline_ms)] {word_put(&mut session,at,n);}
            session[112..144].fill(0x61);session[144..176].copy_from_slice(&test_digest(&source));session[176..208].copy_from_slice(&test_digest(&build));session[208..240].copy_from_slice(&test_digest(&executable));
            for (i,data) in [&source_id[..],&proc_argv,&proc_env,b"/test"].into_iter().enumerate() {session[240+i*32..272+i*32].copy_from_slice(&test_digest(data));}
            [source,build,session,executable,compiler,version,manifest,argv,env,proc_argv,proc_env,b"review-test-only".to_vec(),packet([b"/s",b"/b",b"/t",b"/r",b"/o"])]
        }
        fn preowned<'r>(root:&'r BootstrapLedgerV1,data:[Vec<u8>;13],trace:&Rc<Trace>)->PrepaidInputOwnerV1<'r,Guard> {
            let mut iter=data.into_iter().enumerate();let slots=std::array::from_fn(|_| {let(i,bytes)=iter.next().unwrap();let resource=guard(i,bytes,trace);let initial=resource.identity;ActualInputSlotV1::Preowned {resource,initial}});
            PrepaidInputOwnerV1 { reservation:paid(root),actual:Some(AcquiredUnverifiedOwnerV1 { partial:PartialActualOwnersV1 {
                slots,adoption_bits:0,paths:NativePathBackingV1::empty_v1(),original:None,unresolved:false },claims:claims() }),retirement_started:false }
        }
        fn acquired<'r>(root:&'r BootstrapLedgerV1,trace:&Rc<Trace>)->PrepaidInputOwnerV1<'r,Guard> {
            let mut owner=preowned(root,data_set(&root.policy),trace);let mut b=bridge(trace);let actual=owner.actual.as_mut().unwrap();
            adopt_preowned_slots_core_v1(&mut owner.reservation,&mut actual.partial,&mut b);
            for i in 0..13 {let cap=if i<12 {root.policy.role_caps[i]}else{root.policy.packet_cap};if let ActualInputSlotV1::Owned(file)=&mut actual.partial.slots[i] {
                read_owned_body_once_v1(&mut owner.reservation,file,cap,&mut b).unwrap_or_else(|e|panic!("read slot{} {:?}",i,e.kind)); }else{panic!("missing slot");}}
            let PartialActualOwnersV1 {slots,paths:output,..}=&mut actual.partial;
            let path_bytes=match &slots[12] {ActualInputSlotV1::Owned(f)=>f.body.as_ref().unwrap().slice_v1(),_=>panic!()};
            let paths=decode_path_packet_v1(path_bytes,&root.policy).unwrap();
            copy_native_paths_once_v1(&mut owner.reservation,paths,output,&mut b).unwrap_or_else(|e|panic!("path {:?}",e.kind));owner
        }
        fn admitted<'r>(root:&'r BootstrapLedgerV1,trace:&Rc<Trace>)->AdmittedImmutableOwnerCoreV1<'r,Guard> {
            match complete_admission_core_v1(acquired(root,trace),TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(trace)) {
                OwnedAdmissionCoreOutcomeV1::Admitted(v)=>v,OwnedAdmissionCoreOutcomeV1::Refused(v)=>panic!("admission {:?}",v.actual.as_ref().unwrap().partial.original.as_ref().map(|e|e.kind)), }
        }
        fn provenance_copy(p:&LoaderProvenanceV1)->LoaderProvenanceV1 { LoaderProvenanceV1 {
            validation_budget:p.validation_budget,source_extent:p.source_extent,source:p.source,manifest:p.manifest,
            build:p.build,session:p.session,executable:p.executable,nonce:p.nonce,identities:p.identities } }
        fn carrier(p:&LoaderProvenanceV1,trace:&Rc<Trace>)->LoaderCarrierCoreV1<Guard> {
            let source=wasm_source();let proof=validate_swift_reactor(&source,p.validation_budget,&Cancellation::default()).unwrap();
            assert_eq!(proof.source(),source);assert_ne!(proof.source().as_ptr(),source.as_ptr());
            LoaderCarrierCoreV1 { selected:Ok(SelectedValidatedProfileV1 {proof,provenance:provenance_copy(p)}),
                files:std::array::from_fn(|i|guard(20+i,vec![7;3],trace)),executable:Some(guard(23,vec![8;3],trace)),
                usage:LoaderUsageV1 {hash_bytes:912,source_equality_bytes:1947,..LoaderUsageV1::default()} }
        }
        fn refusal<T>(r:Result<T,BootstrapFailureV1>)->BootstrapFailureV1 {match r {Err(e)=>e,Ok(_)=>panic!("expected refusal")}}
        #[test] fn h01_startup_policy_is_closed_and_original_policy_claims_retained() {
            assert_eq!(refusal(FixtureBootstrapPolicyV1::selected_fixture_v1()),BootstrapFailureV1::BootstrapPolicyPending);
            assert_eq!(refusal(selected_bootstrap_ledger_v1()),BootstrapFailureV1::BootstrapPolicyPending);
            let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);
            assert_eq!(owner.reservation.root.policy.product,SwiftRunBudget::default());
            assert_eq!(owner.reservation.root.policy.product.execution_work,1_000_000_000);
            assert_eq!(owner.reservation.root.policy.product.combined_bytes,268_435_456);
            let _original_claims=&owner.actual.as_ref().unwrap().claims;
            assert!(trace.drops.borrow().is_empty());drop(owner);assert_eq!(trace.drops.borrow().len(),13);
        }
        #[test] fn h02_atomic_reservation_overflow_and_partition_exhaustion() {
            for case in 0..4 {let mut r=root();let before=r.usage.get();let mut q=ReviewedAcquisitionQuoteV1 {acquisition_work:10,cleanup_work:11,peak_storage:12};
                let expected=match case {0=>{q.acquisition_work=u64::MAX;BootstrapFailureV1::Overflow},1=>{r.work_limit=20;BootstrapFailureV1::InsufficientAcquisitionWork},2=>{r.storage_limit=11;BootstrapFailureV1::InsufficientStorage},_=>{r.usage.set(BootstrapUsageV1 {work:0,storage:u64::MAX,peak:u64::MAX});BootstrapFailureV1::Overflow}};
                let before=if case==3 {r.usage.get()}else{before};assert_eq!(refusal(r.reserve_before_any_input_effect_v1(q)),expected);assert_eq!(r.usage.get(),before);assert!(!r.reserved.get());}
            let r=root();let mut p=paid(&r);let old=r.usage.get();p.operation_left=0;assert_eq!(refusal(p.operation_v1(1,0)),BootstrapFailureV1::InsufficientAcquisitionWork);assert_eq!(p.cleanup_left,100);
            p.cleanup_left=0;assert_eq!(refusal(p.cleanup_v1()),BootstrapFailureV1::InsufficientCleanupWork);drop(p);assert_eq!(r.usage.get(),old);
        }
        #[test] fn h03_all_thirteen_partial_refusals_keep_original_resources() {
            for stop in 0..13 {let r=root();let trace=Rc::new(Trace::default());let mut owner=preowned(&r,std::array::from_fn(|_|vec![9]),&trace);
                if let ActualInputSlotV1::Preowned {resource,..}=&mut owner.actual.as_mut().unwrap().partial.slots[stop] {resource.meta_fail=true;}
                let actual=owner.actual.as_mut().unwrap();adopt_preowned_slots_core_v1(&mut owner.reservation,&mut actual.partial,&mut bridge(&trace));
                let e=actual.partial.original.as_ref().unwrap();assert_eq!(e.slot,stop);assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(817));assert!(trace.drops.borrow().is_empty());
                assert_eq!(actual.partial.adoption_bits,(1u16<<stop)-1);drop(owner);assert_eq!(trace.drops.borrow().len(),13);assert_eq!(r.usage.get().storage,1_000_000);}
            let r=root();let owner=acquire_inherited_inputs_once_v1(paid(&r),claims());assert!(owner.actual.as_ref().unwrap().partial.unresolved);
            let before=r.usage.get();let result=retire_acquired_owner_core_v1(owner,&mut NativeInputBridgeV1);
            assert!(matches!(result,AcquisitionRetirementOutcomeV1::Retained(_)));assert_eq!(r.usage.get(),before);
        }
        fn read_case(n:usize,adjust:impl FnOnce(&mut Guard))->(Result<(),OriginalAcquisitionFailureV1>,RetainedIdentityFileV1<Guard>,Rc<Trace>) {
            let r=Box::new(root()); // root cannot escape; return contains no reservation borrow
            let trace=Rc::new(Trace::default());let mut resource=guard(0,vec![3;n],&trace);adjust(&mut resource);
            let mut file=RetainedIdentityFileV1 {role:0,initial:identity_for(0,n),resource,body:None,sha256:None};
            let result=read_owned_body_once_v1(&mut paid(&r),&mut file,9000,&mut bridge(&trace));(result,file,trace)
        }
        #[test] fn h04_bounded_read_blocks_attempts_and_original_io() {
            for n in [4095,4096,4097,8192] {let(result,file,trace)=read_case(n,|_|{});assert!(result.is_ok());assert_eq!(file.body.as_ref().unwrap().initialized,n);assert_eq!(trace.read_calls.get(),n.div_ceil(4096)+1);}
            let(result,_,trace)=read_case(1,|r|r.interruptions=31);assert!(result.is_ok());assert_eq!(trace.read_calls.get(),33); //32 data+one EOF
            let(result,file,trace)=read_case(1,|r|r.interruptions=32);assert_eq!(result.err().unwrap().kind,BootstrapFailureV1::Attempts);assert_eq!(trace.read_calls.get(),32);assert_eq!(file.body.as_ref().unwrap().initialized,0);
            let(result,_,_)=read_case(3,|r|r.chunk=1);assert!(result.is_ok());
            for kind in 0..4 {let(result,file,_)=read_case(3,|r|match kind {0=>{r.data.pop();},1=>r.data.push(4),2=>r.overreported=true,_=>r.error=Some(911)});let e=result.err().unwrap();
                assert_eq!(e.kind,[BootstrapFailureV1::ShortInput,BootstrapFailureV1::ExtraInput,BootstrapFailureV1::OverreportedRead,BootstrapFailureV1::Io][kind]);
                if kind==3 {assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(911));}assert!(file.body.is_some());}
        }
        #[test] fn h05_allocator_bound_precedes_call_and_original_error_stays() {
            let r=root();let trace=Rc::new(Trace::default());let mut p=paid(&r);let mut resource=guard(0,vec![1;9],&trace);
            let mut f=RetainedIdentityFileV1 {role:0,initial:resource.identity,resource,body:None,sha256:None};p.storage_left=34; //9+7+19 needs35
            let e=read_owned_body_once_v1(&mut p,&mut f,9,&mut bridge(&trace)).err().unwrap();assert_eq!(e.kind,BootstrapFailureV1::InsufficientStorage);assert_eq!(trace.allocated.get(),0);
            p.storage_left=35;let mut b=bridge(&trace);b.fail_allocation=true;let e=read_owned_body_once_v1(&mut p,&mut f,9,&mut b).err().unwrap();assert!(e.allocation.is_some());assert_eq!(p.storage_left,0);assert_eq!(trace.storage_at_allocation.get(),1_000_000);
            assert_eq!(allocation_bound_v1(usize::MAX,&r.policy),Err(BootstrapFailureV1::Overflow));
        }
        #[test] fn h06_production_packet_and_separate_raw_path_backing() {
            let r=root();let bytes=packet([b"/a",b"/b",b"/c",b"/d",b"/\xff"]);let paths=decode_path_packet_v1(&bytes,&r.policy).unwrap();assert_eq!(paths[4],b"/\xff");
            let trace=Rc::new(Trace::default());let mut p=paid(&r);let mut out=NativePathBackingV1::empty_v1();copy_native_paths_once_v1(&mut p,paths,&mut out,&mut bridge(&trace)).unwrap_or_else(|_|panic!());
            for i in 0..5 {let a=out.native[i].as_ref().unwrap();let b=out.retained[i].as_ref().unwrap();assert_eq!(a.slice_v1(),b.slice_v1());assert_ne!(a.bytes.as_ptr(),b.bytes.as_ptr());}
            assert_eq!(trace.allocated.get(),10);
            for case in 0..8 {let mut b=bytes.clone();match case {0=>b[0]=0,1=>word_put(&mut b,8,2),2=>word_put(&mut b,16,1),3=>word_put(&mut b,24,u64::MAX),4=>word_put(&mut b,24,0),5=>{b.pop();},6=>b.push(9),_=>b[64]=0};assert!(decode_path_packet_v1(&b,&r.policy).is_err());}
        }
        #[test] fn h07_binary_records_and_full_signed_identity() {
            let r=root();let d=data_set(&r.policy);assert!(parse_build(&d[1]).is_ok());let s=parse_session(&d[2]).unwrap();assert_eq!(s.budget,r.policy.validation);
            let id=decode_identity_v1(s.sections[0].bytes).unwrap();assert_eq!(id.mtime,i64::MIN);assert_eq!(id.ctime,i64::MAX);assert_eq!(id.mtime_ns,-1);
            assert!(parse_session(b"{\"extent\":1947}").is_err());
            for slot in [1,2] {for at in [0,8,16,24] {let mut b=d[slot].clone();b[at]^=1;assert!(if slot==1 {parse_build(&b).is_err()}else{parse_session(&b).is_err()});}}
            for at in [32,40] {let mut b=d[1].clone();word_put(&mut b,at,145);assert!(parse_build(&b).is_err());}
            for index in 0..5 {let r=root();let trace=Rc::new(Trace::default());let mut owner=acquired(&r,&trace);let at=[72,80,88,96,104][index];
                if let ActualInputSlotV1::Owned(f)=&mut owner.actual.as_mut().unwrap().partial.slots[2] {word_put(&mut f.body.as_mut().unwrap().bytes,at,0);}
                assert!(derive_provenance_v1(owner.actual.as_ref().unwrap(),&r.policy).is_err());}
        }
        #[test] fn h08_all_nine_groups_five_limits_and_thirty_two_identity_fields_refuse() {
            for mutation in 0..46 {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let (expected,attempt)=owner.correlation_scope_core_v1().unwrap();let mut c=carrier(&owner.expected,&trace);
                let p=&mut c.selected.as_mut().unwrap().provenance;
                match mutation {0=>p.source[0]^=1,1=>p.manifest[0]^=1,2=>p.build[0]^=1,3=>p.session[0]^=1,4=>p.executable[0]^=1,5=>p.nonce[0]^=1,6..=10=>match mutation-6 {0=>p.validation_budget.source_bytes+=1,1=>p.validation_budget.metadata_bytes+=1,2=>p.validation_budget.scratch_bytes+=1,3=>p.validation_budget.work_credits+=1,_=>p.validation_budget.deadline_ms+=1},11=>p.source_extent+=1,
                    12..=43=>{let n=mutation-12;let id=&mut p.identities[n/8];match n%8 {0=>id.dev^=1,1=>id.inode^=1,2=>id.bytes^=1,3=>id.mode^=1,4=>id.mtime^=1,5=>id.mtime_ns^=1,6=>id.ctime^=1,_=>id.ctime_ns^=1}},44=>p.source_extent=0,_=>p.identities[0].mtime_ns=i64::MAX}
                match correlate_core_v1(attempt,c,&expected) {Err((e,held))=>{assert!(matches!(e.kind,BootstrapFailureV1::Correlation(_)));assert!(held.selected.is_ok());assert_eq!(held.usage.hash_bytes,912);assert!(trace.drops.borrow().is_empty());drop(held);},Ok(_)=>panic!("mutation{} admitted",mutation)}
                assert_eq!(trace.drops.borrow().len(),4);drop(owner);assert_eq!(trace.drops.borrow().len(),17);
            }
        }
        #[test] fn h09_distinct_guard_handles_same_identity_real_proof_only_one_leaf() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let (expected,attempt)=owner.correlation_scope_core_v1().unwrap();let c=carrier(&owner.expected,&trace);
            assert!(c.files[0].tag!=0);let leaf=Cell::new(0);let matched=match correlate_core_v1(attempt,c,&expected) {Ok(v)=>v,Err(_)=>panic!("correlation")};
            let selected=CorrelatedSelectedProfileV1(matched.selected.unwrap());assert_eq!(selected.into_selected_v1().source().len(),1947);leaf.set(leaf.get()+1);
            assert_eq!(leaf.get(),1);assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
        }
        #[test] fn h10_whole_error_result_files_usage_move_before_live_refusal() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();owner.attempt_taken.set(false);
            let mut c=carrier(&owner.expected,&trace);let failure=validate_swift_reactor(b"bad",owner.expected.validation_budget,&Cancellation::default()).err().unwrap();
            c.selected=Err(LoaderFailureV1 {io:Some(io::Error::from_raw_os_error(977)),validation:Some(failure),..LoaderFailureV1::new(Refusal::Validation,Role::Source,7,3)});
            let (original,c)=match correlate_core_v1(attempt,c,&expected) {Err(v)=>v,Ok(_)=>panic!()};assert_eq!(original.kind,BootstrapFailureV1::LiveOwner);
            let e=c.selected.as_ref().err().unwrap();assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(977));assert!(e.validation.is_some());assert_eq!(e.offset,7);assert_eq!(e.attempts,3);
            assert_eq!(c.files.map(|r|r.tag),[20,21,22]);assert_eq!(c.executable.as_ref().unwrap().tag,23);assert_eq!(c.usage.hash_bytes,912);
        }
        #[test] fn h11_retirement_order_complete_token_failure_unwind_no_token() {
            let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);let before=r.usage.get();let token=match retire_acquired_owner_core_v1(owner,&mut bridge(&trace)) {
                AcquisitionRetirementOutcomeV1::Complete(t)=>t,_=>panic!("complete typed guards")};assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get(),before);token.release_v1();assert_eq!(r.usage.get().storage,0);assert_eq!(r.usage.get().work,before.work);
            for fail in 0..13 {let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);let mut b=bridge(&trace);b.fail_retirement=Some(fail);let result=retire_acquired_owner_core_v1(owner,&mut b);
                let owner=match result {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!()};assert_eq!(trace.drops.borrow().len(),fail);assert_eq!(r.usage.get().storage,1_000_000);assert!(owner.retirement_started);drop(owner);}
            let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);let mut b=bridge(&trace);b.unwind_retirement=Some(3);let result=catch_unwind(AssertUnwindSafe(||retire_acquired_owner_core_v1(owner,&mut b)));assert!(result.is_err());assert_eq!(r.usage.get().storage,1_000_000);
            let r=root();let trace=Rc::new(Trace::default());let mut owner=acquired(&r,&trace);owner.reservation.cleanup_left=0;assert!(matches!(retire_acquired_owner_core_v1(owner,&mut bridge(&trace)),AcquisitionRetirementOutcomeV1::Retained(_)));assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h12_prepaid_ingress_required_before_private_admission_publication() {
            for work in [true,false] {let r=root();let trace=Rc::new(Trace::default());let mut owner=acquired(&r,&trace);if work {owner.reservation.operation_left=30;}else{owner.reservation.storage_left=42;}
                let result=complete_admission_core_v1(owner,TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(&trace));let held=match result {OwnedAdmissionCoreOutcomeV1::Refused(v)=>v,_=>panic!("unprepaid admission")};assert!(held.actual.as_ref().unwrap().partial.original.is_some());assert!(trace.drops.borrow().is_empty());}
        }
        #[test] fn h13_real_validator_backing_owned_independently_and_old_limits_unselected() {
            let r=root();let source=wasm_source();let proof=validate_swift_reactor(&source,r.policy.validation,&Cancellation::default()).unwrap();assert_eq!(proof.source(),source);assert_ne!(proof.source().as_ptr(),source.as_ptr());drop(source);assert_eq!(proof.source().len(),1947);
            assert_eq!(refusal(selected_bootstrap_ledger_v1()),BootstrapFailureV1::BootstrapPolicyPending);
        }
    }
