#!/usr/bin/env python3
"""Keep the original production-core guard witnesses inside root envelopes."""
from pathlib import Path
p=Path(__file__).resolve().parent/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
s=p.read_text(); at=s.index('    mod prepaid_actual_owner_v1 {'); prefix=s[:at]; t=s[at:]
# Every test goes through the actual changed production generic program; the
# private result partition retains original root in both original result arms.
needle='correlate_core_v1('; cursor=0; out=''
while (a:=t.find(needle,cursor))!=-1:
    b=a+len(needle); depth=1
    while depth:
        if t[b]=='(': depth+=1
        elif t[b]==')': depth-=1
        b+=1
    out+=t[cursor:b]+'.into_result_v1()'; cursor=b
t=out+t[cursor:]
t=t.replace('Err((e,held))=>{','Err(refused)=>{let(e,held)=refused.split_pair_v1();')
t=t.replace('Err(v)=>v,Ok(_)=>panic!','Err(v)=>v.split_pair_v1(),Ok(_)=>panic!')
t=t.replace('Err((_original,v))=>(true,v)','Err(refused)=>{let(_original,v)=refused.split_pair_v1();(true,v)}')
for variable in ['held','retained_result']:
    for field in ['selected','files','executable','usage']:
        t=t.replace(f'{variable}.{field}',f'{variable}.payload.{field}')
t=t.replace('e.kind,BootstrapFailureV1::Correlation','e.payload.kind,BootstrapFailureV1::Correlation')
t=t.replace('e.kind,BootstrapFailureV1::LiveOwner','e.payload.kind,BootstrapFailureV1::LiveOwner')
t=t.replace('original.kind,BootstrapFailureV1::LiveOwner','original.payload.kind,BootstrapFailureV1::LiveOwner')
t=t.replace('original.kind,BootstrapFailureV1::Correlation','original.payload.kind,BootstrapFailureV1::Correlation')
t=t.replace('let e=c.selected.as_ref().err().unwrap();','let e=c.payload.selected.as_ref().err().unwrap();')
t=t.replace('assert_eq!(c.files.each_ref().map(|r|r.tag),[20,21,22]);assert_eq!(c.executable.as_ref().unwrap().tag,23);assert_eq!(c.usage.hash_bytes,912);','assert_eq!(c.payload.files.each_ref().map(|r|r.tag),[20,21,22]);assert_eq!(c.payload.executable.as_ref().unwrap().tag,23);assert_eq!(c.payload.usage.hash_bytes,912);')
start=t.index('        struct OwnedSentinelResultV1 {'); end=t.index('        #[test] fn h08_cross_owner',start)
t=t[:start]+'''        #[test] fn h09_distinct_guard_handles_same_identity_real_proof_complete_bound_result() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let (expected,attempt)=owner.correlation_scope_core_v1().unwrap();let c=carrier(&owner.expected,&trace);
            assert!(c.files[0].tag!=0);let proof_source=c.selected.as_ref().unwrap().proof.source().as_ptr();
            let result=match correlate_core_v1(attempt,c,&expected).into_result_v1() {Ok(v)=>v,Err(_)=>panic!("correlation")};
            assert!(std::ptr::eq(result.root,&r));
            let selected=result.payload.selected.as_ref().unwrap();
            assert_eq!(selected.proof.source().as_ptr(),proof_source);
            assert_eq!(selected.source(),body_v1(owner.owned.actual.as_ref().unwrap(),0).unwrap());
            assert_eq!(result.payload.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(result.payload.executable.as_ref().unwrap().tag,23);
            for i in 0..3 {assert_eq!(result.payload.files[i].identity,owner.expected.identities[i]);}
            assert_eq!(result.payload.executable.as_ref().unwrap().identity,owner.expected.identities[3]);
            assert_eq!(result.payload.usage.hash_bytes,912);assert!(trace.drops.borrow().is_empty());
            assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
            drop(result);assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);
            let AdmittedImmutableOwnerCoreV1 {owned,..}=owner;
            let retained=match retire_acquired_owner_core_v1(owned,&mut bridge(&trace)) {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!("correlation barrier")};
            assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);assert_eq!(r.usage.get().storage,1_000_000);
            drop(retained);assert_eq!(*trace.drops.borrow(),(20..24).chain(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get().storage,1_000_000);
        }
''' +t[end:]
start=t.index('        #[test] fn h18_extracted_selected'); end=t.index('        #[test] fn h19_',start)
t=t[:start]+'''        #[test] fn h18_complete_bound_selected_carrier_cannot_discharge_barrier() {
            // Historical bare extraction remains in the frozen IR01/IR02
            // packet. This counterpart keeps proof and all guards bound.
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let held={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();
                match correlate_core_v1(attempt,carrier(&owner.expected,&trace),&expected).into_result_v1() {Ok(v)=>v,Err(_)=>panic!()}};
            let proof_source=held.payload.selected.as_ref().unwrap().proof.source().as_ptr();
            let retained=assert_correlation_barrier_v1(owner,&trace);assert!(trace.drops.borrow().is_empty());drop(retained);
            assert!(std::ptr::eq(held.root,&r));
            assert_eq!(held.payload.selected.as_ref().unwrap().proof.source().as_ptr(),proof_source);
            assert_eq!(held.payload.selected.as_ref().unwrap().proof.source().len(),1947);
            assert_eq!(held.payload.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(held.payload.executable.as_ref().unwrap().tag,23);
            assert_eq!(held.payload.usage.hash_bytes,912);assert_eq!(r.usage.get().storage,1_000_000);
            drop(held);assert_eq!(r.usage.get().storage,1_000_000);
        }
''' +t[end:]
t=t.replace("fn move_attempt<'o>(attempt:PrepaidCorrelationAttemptV1<'o>)->PrepaidCorrelationAttemptV1<'o> {attempt}","fn move_attempt<'o,'r:'o>(attempt:PrepaidCorrelationAttemptV1<'o,'r>)->PrepaidCorrelationAttemptV1<'o,'r> {attempt}")
t=t.replace("fn borrow_correspondence<'o>(expected:&AdmittedLoaderCorrespondenceV1<'o>)->&'o LoaderProvenanceV1 {expected.owner_data}","fn borrow_correspondence<'o,'r:'o>(expected:&AdmittedLoaderCorrespondenceV1<'o,'r>)->&'o LoaderProvenanceV1 {expected.owner_data}")
# Compile-only facade positive: genuine File shape supplied as inputs, with no
# native acquisition, runtime fixture, public constructor or alternate core.
anchor='        // Independent desired-property witness.'
pos=t.index(anchor)
t=t[:pos]+'''        fn positive_facade_owner_retirement_v1<'root>(
            owner: AdmittedImmutableOwnerV1<'root>, carrier: SuppliedLoaderCarrierV1,
        ) -> OwnedCorrelationOutcomeV1<'root> {
            let returned = {
                let (expected, attempt) = owner.correlation_scope_v1().unwrap();
                correlate_admitted_loader_v1(attempt, carrier, &expected)
            };
            retire_admitted_owner_v1(owner);
            returned
        }
        #[test] fn h23_foreign_expected_root_ends_before_bound_attempt_result() {
            let original=root();let trace=Rc::new(Trace::default());let owner=admitted(&original,&trace);
            let held={
                let foreign_root=root();let foreign_owner=admitted(&foreign_root,&trace);
                let(_own,attempt)=owner.correlation_scope_core_v1().unwrap();
                let(foreign,_unused)=foreign_owner.correlation_scope_core_v1().unwrap();
                let returned=correlate_core_v1(attempt,carrier(&owner.expected,&trace),&foreign);
                assert!(std::ptr::eq(returned.root,&original));
                assert!(!std::ptr::eq(returned.root,&foreign_root));
                returned
            };
            assert!(std::ptr::eq(held.root,&original));
            let refused=held.into_result_v1().err().unwrap();
            assert_eq!(refused.payload.0.kind,BootstrapFailureV1::LiveOwner);
            assert_eq!(refused.payload.1.selected.as_ref().unwrap().source().len(),1947);
            assert_eq!(refused.payload.1.files.each_ref().map(|v|v.tag),[20,21,22]);
            let retained=assert_correlation_barrier_v1(owner,&trace);drop(retained);
            assert_eq!(original.usage.get().storage,1_000_000);drop(refused);
        }
''' +t[pos:]
p.write_text(prefix+t)
