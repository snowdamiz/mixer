"""Eight bounded single-purpose actual compiler rejection controls."""
from pathlib import Path
import json,shutil,sys
from run_bounded import HERE,common,run,write,source_manifest,digest
PROBES={
'N01':('inline','''
    fn negative_require_copy_v1<T:Copy>(_:T) {}
    fn negative_copy_v1(reservation:AcquisitionReservationV1<'_>,attempt:PrepaidCorrelationAttemptV1<'_>) {
        negative_require_copy_v1(reservation); negative_require_copy_v1(attempt);
    }
''',['E0277'],['AcquisitionReservationV1','PrepaidCorrelationAttemptV1']),
'N02':('inline','''
    fn negative_twice_v1(attempt:PrepaidCorrelationAttemptV1<'_>,one:SuppliedLoaderCarrierV1,two:SuppliedLoaderCarrierV1,expected:&AdmittedLoaderCorrespondenceV1<'_>) {
        let _=correlate_admitted_loader_v1(attempt,one,expected);
        let _=correlate_admitted_loader_v1(attempt,two,expected);
    }
''',['E0382'],['attempt']),
'N03':('inline','''
    fn negative_retire_borrowed_v1(owner:AdmittedImmutableOwnerV1<'_>) {
        let binding=owner.scoped_binding_v1();
        retire_admitted_owner_v1(owner);
        let _still_live=binding.paths[0];
    }
''',['E0505'],['owner','borrow']),
'N04':('inline','''
    fn negative_static_v1<'a,'root>(owner:&'a AdmittedImmutableOwnerV1<'root>)->BorrowedOwnerDataV1<'static> {
        owner.scoped_binding_v1()
    }
''',['lifetime may not live long enough'],["'static"]),
'N05':('loader','''
fn negative_parts_v1(p:LoaderProvenanceV1,selected:SelectedValidatedProfileV1) {
    let _expected=AdmittedLoaderCorrespondenceV1 {owner_data:&p,association:1};
    let _wrapper=CorrelatedSelectedProfileV1(selected);
}
''',['private'],['CorrelatedSelectedProfileV1','AdmittedLoaderCorrespondenceV1']),
'N06':('caller','''
    fn negative_unqualified_v1(candidate:existing_owner_candidate_v1::UnqualifiedExistingOwnerCandidateV1<'_>) {
        let _=consume_admitted_owner_once_v1(candidate);
    }
''',['E0308'],['AdmittedImmutableOwnerV1','UnqualifiedExistingOwnerCandidateV1']),
'N07':('inline','''
    fn negative_dictionary_v1(attempt:PrepaidCorrelationAttemptV1<'_>,carrier:SuppliedLoaderCarrierV1) {
        let dictionary=std::collections::HashMap::<String,[u8;32]>::new();
        let _=correlate_admitted_loader_v1(attempt,carrier,&dictionary);
    }
''',['E0308'],['AdmittedLoaderCorrespondenceV1','HashMap']),
'N08':('inline','''
    fn negative_production_test_constructor_v1() {
        let _=UnverifiedProfileDigestBytesV1::test_prepaid_actual_owner_fixed_claims_v1();
    }
''',['E0599'],['test_prepaid_actual_owner_fixed_claims_v1']),
}
if __name__=='__main__':
 name=sys.argv[1];where,probe,diagnostics,names=PROBES[name]
 base=HERE/'probes'/name;base.mkdir(parents=True,exist_ok=False);source=base/'source';shutil.copytree(HERE/'source',source)
 filename=source/'vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
 if where=='inline':s=filename.read_text();assert s.count('    // OWNER_PROBE_INSERTION')==1;s=s.replace('    // OWNER_PROBE_INSERTION',probe);filename.write_text(s)
 elif where=='loader':filename.write_text(filename.read_text()+probe)
 else:
  filename=source/'vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs';s=filename.read_text();anchor='    enum AdmittedOuterResultV1 {';assert s.count(anchor)==1;s=s.replace(anchor,probe+'\n'+anchor);filename.write_text(s)
 write(base/'probe.json',dict(id=name,injection=where,source=probe,intended_diagnostics=diagnostics,intended_names=names,source_manifest_tree=digest(source_manifest(source)),product_authority=False))
 argv=common(source)+['-C','opt-level=0','--crate-type','rlib',str(source/'vm/src/lib.rs'),'--emit=metadata='+str(base/'negative.rmeta')]
 code=run(name,argv,source=source);stderr=(HERE/'commands'/name/'stderr').read_text()
 result=dict(exit=code,compiler_refused=code!=0,expected_diagnostics=diagnostics,diagnostics_found=all(d in stderr for d in diagnostics),intended_names_found=all(n in stderr for n in names),rmeta_created=(base/'negative.rmeta').exists(),scope='actual copied production crate; single inert rejected probe')
 write(base/'result.json',result);assert result['compiler_refused'] and result['diagnostics_found'] and result['intended_names_found'] and not result['rmeta_created'],result
 print(json.dumps(result,sort_keys=True))
