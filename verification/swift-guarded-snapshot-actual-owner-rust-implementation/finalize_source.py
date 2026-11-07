from pathlib import Path
base=Path(__file__).parent
m=(base/'owner_module.inc.rs').read_text()
# Pre-admission verification runs in both production and guarded tests. It
# consumes tickets BEFORE every final identity/hash call and retains errors.
a=m.index('    fn complete_admission_core_v1')
m=m[:a]+'''    fn verify_actual_bodies_core_v1<R,B:InputBridgeV1<R>>(paid:&mut AcquisitionReservationV1<'_>,actual:&mut AcquiredUnverifiedOwnerV1<R>,bridge:&mut B)
        -> Result<LoaderProvenanceV1,OriginalAcquisitionFailureV1>
    {
        if actual.partial.original.is_some() { return Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)); }
        for i in 0..13 {
            let fail=|kind|OriginalAcquisitionFailureV1::new(kind,i);
            let owned=match &mut actual.partial.slots[i] { ActualInputSlotV1::Owned(v)=>v,_=>return Err(fail(BootstrapFailureV1::Incomplete)) };
            let t=paid.operation_v1(paid.root.policy.bridge.metadata,0).map_err(fail)?;
            if bridge.metadata_v1(t,&mut owned.resource,i)?!=owned.initial { return Err(fail(BootstrapFailureV1::MetadataChanged)); }
            let body=match owned.body.as_ref() {Some(v) if v.complete_v1()=>v,_=>return Err(fail(BootstrapFailureV1::Incomplete))};
            let work=paid.root.policy.bridge.hash_per_byte.checked_mul(body.bytes.len() as u64).ok_or_else(||fail(BootstrapFailureV1::Overflow))?;
            let t=paid.operation_v1(work,0).map_err(fail)?;
            if Some(bridge.hash_v1(t,body.slice_v1(),i)?)!=owned.sha256 {return Err(fail(BootstrapFailureV1::Digest));}
        }
        let bytes=body_v1(actual,1).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,1))?.len()
            .checked_add(body_v1(actual,2).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,2))?.len())
            .and_then(|n|n.checked_add(64)).ok_or_else(||OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Overflow,1))?;
        let _paid=paid.operation_v1(bytes as u64,0).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,1))?;
        derive_provenance_v1(actual,&paid.root.policy)
    }
''' +m[a:]
m=m.replace("fn complete_admission_core_v1<'root,R>(mut owned: PrepaidInputOwnerV1<'root,R>, custody: TrustedLocalLauncherCustodyV1)","fn complete_admission_core_v1<'root,R,B:InputBridgeV1<R>>(mut owned: PrepaidInputOwnerV1<'root,R>, custody: TrustedLocalLauncherCustodyV1,bridge:&mut B)")
m=m.replace('''let derived = match owned.actual.as_ref() {
            Some(actual) => derive_provenance_v1(actual, &owned.reservation.root.policy),''','''let derived = match owned.actual.as_mut() {
            Some(actual) => verify_actual_bodies_core_v1(&mut owned.reservation,actual,bridge),''')
m=m.replace('''let result = match owner.actual.as_ref() {
            Some(actual) => derive_provenance_v1(actual, &owner.reservation.root.policy),''','''let result = match owner.actual.as_mut() {
            Some(actual) => verify_actual_bodies_core_v1(&mut owner.reservation,actual,&mut NativeInputBridgeV1),''')
(base/'owner_module.inc.rs').write_text(m)
t=(base/'owner_tests.inc.rs').read_text()
t=t.replace('complete_admission_core_v1(acquired(root,trace),TrustedLocalLauncherCustodyV1 {_private:()})','complete_admission_core_v1(acquired(root,trace),TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(trace))')
t=t.replace('complete_admission_core_v1(owner,TrustedLocalLauncherCustodyV1 {_private:()})','complete_admission_core_v1(owner,TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(&trace))')
t=t.replace('''            let path_bytes=body_v1(actual,12).unwrap();let paths=decode_path_packet_v1(path_bytes,&root.policy).unwrap();
            copy_native_paths_once_v1(&mut owner.reservation,paths,&mut actual.partial.paths,&mut b)''','''            let PartialActualOwnersV1 {slots,paths:output,..}=&mut actual.partial;
            let path_bytes=match &slots[12] {ActualInputSlotV1::Owned(f)=>f.body.as_ref().unwrap().slice_v1(),_=>panic!()};
            let paths=decode_path_packet_v1(path_bytes,&root.policy).unwrap();
            copy_native_paths_once_v1(&mut owner.reservation,paths,output,&mut b)''')
(base/'owner_tests.inc.rs').write_text(t)
p=base/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs';s=p.read_text().split('// Actual private ownership core.')[0];p.write_text(s+m.replace('    // OWNER_TESTS_INSERTION',t+'\n    // OWNER_PROBE_INSERTION'))
p=base/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs';s=p.read_text()
s=s.replace('''    fn consume_admitted_owner_once_v1(owner: super::AdmittedImmutableOwnerV1<'_>)
        -> Result<(),super::BootstrapFailureV1>
''','''    enum AdmittedOuterResultV1 {
        BootstrapRefused(super::BootstrapFailureV1),
        AccountRefused(RefusalV1), EntryRefused(RefusalV1),
        Returned { original_observation:OriginalObservationV1,retirement:RetirementObservationV1 },
    }
    fn consume_admitted_owner_once_v1(owner: super::AdmittedImmutableOwnerV1<'_>)
        -> AdmittedOuterResultV1
''')
s=s.replace('''                Err(original) => Err(original),
                Ok((expected,attempt)) => match host_account_v1::selected_parent_account_v1() {
                    Err(_original_pending_account) => Ok(()),''','''                Err(original) => AdmittedOuterResultV1::BootstrapRefused(original),
                Ok((expected,attempt)) => match host_account_v1::selected_parent_account_v1() {
                    Err(original) => AdmittedOuterResultV1::AccountRefused(original),''')
s=s.replace('''                            Err(_original_pending_quote) => {},
                            Ok(owned_child) => {
                                let borrowed = borrow_original_diagnostics_once_v1(&owned_child);
                                let _observation = observe_borrowed_originals_v1(borrowed);
                                if let Some(original_token) = destroy_returned_fixture_v1(owned_child) {
                                    release_after_retirement_v1(original_token);
                                }
                            }
                        }
                        Ok(())''','''                            Err(original) => AdmittedOuterResultV1::EntryRefused(original),
                            Ok(owned_child) => {
                                let borrowed = borrow_original_diagnostics_once_v1(&owned_child);
                                let original_observation = observe_borrowed_originals_v1(borrowed);
                                let retirement = match destroy_returned_fixture_v1(owned_child) {
                                    Some(original_token) => { release_after_retirement_v1(original_token);
                                        RetirementObservationV1::DestructionTokenReleased },
                                    None => RetirementObservationV1::NoDestructionToken,
                                };
                                AdmittedOuterResultV1::Returned { original_observation,retirement }
                            }
                        }''')
p.write_text(s)
