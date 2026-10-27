#!/usr/bin/env python3
"""Independently authored exact compile-only boundary probes; no extra source copy."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
facade='''
// Paired control: genuine File facade, original owner supplied as input. This
// compiles without acquiring Files or constructing an admitted owner.
fn ir02_positive_correlate_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1)
    -> OwnedCorrelationOutcomeV1<'root> {
    let returned={let(expected,attempt)=owner.correlation_scope_v1().unwrap();
        correlate_admitted_loader_v1(attempt,carrier,&expected)};
    retire_admitted_owner_v1(owner);
    returned
}
'''
final='''
fn ir02_positive_final_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1,args:FixtureLeafArgumentsV1)
    -> RootBoundFixtureOutcomeV1<'root> {
    ir02_positive_correlate_v1(owner,carrier).run_fixture_once_v1(args)
}
fn ir02_positive_scalar_v1(value:&RootBoundFixtureOutcomeV1<'_>)->LoaderUsageV1 {value.usage_v1()}
'''
provider="provider:for<'root> fn(&'root BootstrapLedgerV1)->AdmittedImmutableOwnerV1<'root>"
probes=[]
def add(id,scope,content,diagnostics,positive,limit=None):
    path=P/'probes'/f'{id}.inc.rs';path.parent.mkdir(exist_ok=True)
    path.write_text('// COMPILE ONLY; never invoked. Exactly one intended boundary.\n'+content)
    probes.append({'id':id,'scope':scope,'fragment':str(path.relative_to(P)),'intended_diagnostics':diagnostics,
                   'paired_control':positive,'runtime':False,'limitation':limit})
add('N01','facade',facade+f'''
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},carrier:SuppliedLoaderCarrierV1) {{
    let returned={{let local_root=root;ir02_positive_correlate_v1(provider(&local_root),carrier)}};
    drop(returned);
}}
''',['E0597','local_root','does not live long enough'],'ir02_positive_correlate_v1 returns after owner retirement; also in normal test build')
add('N02','facade',facade+f'''
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},carrier:SuppliedLoaderCarrierV1) {{
    let returned=ir02_positive_correlate_v1(provider(&root),carrier);
    drop(root);
    drop(returned);
}}
''',['E0505','root','borrow'],'destroy returned before root')
add('N03','facade',facade+f'''
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},has_executable:bool,
    some:SuppliedLoaderCarrierV1,none:SuppliedLoaderCarrierV1) {{
    let returned={{let local_root=root;
        let original=if has_executable {{some}} else {{none}};
        ir02_positive_correlate_v1(provider(&local_root),original)}};
    drop(returned);
}}
''',['E0597','local_root'],'same facade return type for both complete optional shapes',
    'Compiler property is universal over the supplied carrier; actual Some/None guard execution is host H09/H21, File variants are not executed.')
add('N04','facade',facade+f'''
fn ir02_positive_foreign_v1<'root,'foreign>(owner:AdmittedImmutableOwnerV1<'root>,foreign:AdmittedImmutableOwnerV1<'foreign>,carrier:SuppliedLoaderCarrierV1)
    -> OwnedCorrelationOutcomeV1<'root> {{
    let returned={{let(_own,attempt)=owner.correlation_scope_v1().unwrap();
        let(expected,_unused)=foreign.correlation_scope_v1().unwrap();
        correlate_admitted_loader_v1(attempt,carrier,&expected)}};
    retire_admitted_owner_v1(foreign);retire_admitted_owner_v1(owner);returned
}}
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},foreign:AdmittedImmutableOwnerV1<'_>,carrier:SuppliedLoaderCarrierV1) {{
    let returned={{let local_root=root;ir02_positive_foreign_v1(provider(&local_root),foreign,carrier)}};
    drop(returned);
}}
''',['E0597','local_root'],'foreign expected root is independent; actual cross-root generic host H23',
    'This facade compiler probe covers the complete refused family; original retained-selection identity is host guard evidence.')
add('N05','owner',facade+f'''
fn ir02_positive_refusal_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,carrier:SuppliedLoaderCarrierV1,live_refusal:bool)
    -> OwnedCorrelationOutcomeV1<'root> {{
    let returned={{let(mut expected,attempt)=owner.correlation_scope_v1().unwrap();
        if live_refusal {{owner.0.attempt_taken.set(false)}} else {{expected.association+=1}}
        correlate_admitted_loader_v1(attempt,carrier,&expected)}};
    retire_admitted_owner_v1(owner);returned
}}
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},carrier:SuppliedLoaderCarrierV1,live_refusal:bool) {{
    let returned={{let local_root=root;ir02_positive_refusal_v1(provider(&local_root),carrier,live_refusal)}};
    drop(returned);
}}
''',['E0597','local_root'],'both exact live and association refusal controls retain root')
add('N06','facade',facade+final+f'''
fn ir02_positive_io_v1<'view>(value:&'view RootBoundFixtureOutcomeV1<'_>)->Option<&'view io::Error> {{
    match value.primary_v1() {{RootBoundPrimaryBorrowV1::LoaderRefused(original)=>original.io.as_ref(),_=>None}}
}}
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},carrier:SuppliedLoaderCarrierV1,args:FixtureLeafArgumentsV1) {{
    let returned={{let local_root=root;ir02_positive_final_v1(provider(&local_root),carrier,args)}};
    let _original_io=ir02_positive_io_v1(&returned);drop(returned);
}}
''',['E0597','local_root'],'borrowed original io view tied to carrier; exact io identity is generic host H10/H15')
add('N07','facade',facade+final+f'''
fn ir02_positive_validation_v1<'view>(value:&'view RootBoundFixtureOutcomeV1<'_>)->Option<&'view SwiftValidationFailure> {{
    match value.primary_v1() {{RootBoundPrimaryBorrowV1::LoaderRefused(original)=>original.validation.as_ref(),_=>None}}
}}
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},carrier:SuppliedLoaderCarrierV1,args:FixtureLeafArgumentsV1) {{
    let returned={{let local_root=root;ir02_positive_final_v1(provider(&local_root),carrier,args)}};
    let _original_validation=ir02_positive_validation_v1(&returned);drop(returned);
}}
''',['E0597','local_root'],'borrowed original typed validation view tied to carrier')
add('N08','facade',facade+final+'''
fn ir02_negative_v1() {let _missing_reexport:Option<CorrelatedSelectedProfileV1<'_>>=None;}
''',['E0425','CorrelatedSelectedProfileV1'],'ir02_positive_final_v1 fixed consuming operation')
add('N09','facade',facade+final+'''
fn ir02_negative_v1(value:OwnedCorrelationOutcomeV1<'_>) {let OwnedCorrelationOutcomeV1(_raw)=value;}
''',['E0532','OwnedCorrelationOutcomeV1'],'ir02_positive_scalar_v1 copies scalar usage only')
add('N10','facade',facade+final+'''
fn ir02_negative_v1(value:OwnedCorrelationOutcomeV1<'_>) {let _raw=value.into_selected_v1();}
''',['E0599','into_selected_v1'],'ir02_positive_final_v1 encloses adoption/scope/run/finish')
for id,arm in [('N11','Ok'),('N12','Err')]:
    add(id,'facade',facade+final+f'''
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},carrier:SuppliedLoaderCarrierV1,args:FixtureLeafArgumentsV1) {{
    let returned={{let local_root=root;ir02_positive_final_v1(provider(&local_root),carrier,args)}};
    if let RootBoundPrimaryBorrowV1::Leaf({arm}(original))=returned.primary_v1() {{let _original=original;}}
    drop(returned);
}}
''',['E0597','local_root'],'fixed operation returns one root-bound type covering both typed leaf arms',
        'Compile-only File facade covers arm lifetime universally; actual VM leaf Ok/Err execution remains Pending and is not replaced by a structural model.')
cachepositive='''
fn ir02_positive_child_v1<'child,'root>(account:&'child TrustedHostAccountV1,fixture:FrozenFixtureV1<'_>,owner:AdmittedImmutableOwnerV1<'root>)
    -> Result<PrepaidOwnedV1<'child,AdmittedFixtureOutcomeV1<'root>>,RefusalV1> {
    let returned={let(expected,attempt)=owner.correlation_scope_v1().unwrap();
        run_one_admitted_fixture_v1(account,fixture,attempt,&expected)};
    crate::experimental_swift_reactor::retained_profile_loader_v1::retire_admitted_owner_v1(owner);returned
}
'''
add('N13','cache',cachepositive+f'''
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},account:&TrustedHostAccountV1,fixture:FrozenFixtureV1<'_>) {{
    let returned={{let local_root=root;ir02_positive_child_v1(account,fixture,provider(&local_root))}};
    if let Ok(child)=&returned {{let _original=child.inspect_v1();}}
    drop(returned);
}}
''',['E0597','local_root'],'positive child root and child account have independent lifetimes; child can survive owner with live root')
add('N14','cache',cachepositive+f'''
fn ir02_positive_setup_family_v1<'root>(fixture:FrozenFixtureV1<'_>,owner:AdmittedImmutableOwnerV1<'root>)
    -> AdmittedFixtureOutcomeV1<'root> {{
    let returned={{let(expected,attempt)=owner.correlation_scope_v1().unwrap();
        run_prepaid_admitted_fixture_v1(fixture,attempt,&expected)}};
    crate::experimental_swift_reactor::retained_profile_loader_v1::retire_admitted_owner_v1(owner);returned
}}
fn ir02_negative_v1(root:BootstrapLedgerV1,{provider},fixture:FrozenFixtureV1<'_>) {{
    let returned={{let local_root=root;ir02_positive_setup_family_v1(fixture,provider(&local_root))}};
    if let AdmittedFixturePayloadV1::SetupRefused(original)=&returned.payload {{let _original=original;}}
    drop(returned);
}}
''',['E0597','local_root'],'complete cache final type binds every setup partial prefix',
    'Actual native File setup failures at each prefix remain Pending; no File acquisition is run.')
add('N15','facade',facade+final+'''
fn ir02_positive_view_v1<'view>(value:&'view RootBoundFixtureOutcomeV1<'_>)->RootBoundPrimaryBorrowV1<'view> {value.primary_v1()}
fn ir02_negative_v1(value:RootBoundFixtureOutcomeV1<'_>) {
    let borrowed=value.primary_v1();drop(value);
    match borrowed {RootBoundPrimaryBorrowV1::LoaderRefused(original)=>{let _=original.io.as_ref();},_=>{}}
}
''',['E0505','value','borrow'],'short view return tied to borrowed carrier, no root-length/static borrow')
add('N16','facade',facade+final+'''
fn ir02_negative_v1() {let _private_core=prepaid_input_owner_v1::correlate_core_v1::<File>;}
''',['E0603','correlate_core_v1','private'],'complete facade remains available without raw carrier construction')
add('N17','facade',facade+final+'''
fn ir02_negative_v1<'root>(value:OwnedCorrelationOutcomeV1<'root>) {
    let mut caller_slot:Option<OwnedCorrelationOutcomeV1<'root>>=None;
    value.map(|raw|caller_slot=Some(raw));
}
''',['E0599','map'],'fixed non-generic consuming operation is the sole facade transition')
add('N18','facade',facade+final+'''
fn ir02_negative_v1(value:&mut OwnedCorrelationOutcomeV1<'_>) {let _mutable=std::ops::DerefMut::deref_mut(value);}
''',['E0277','DerefMut'],'shared diagnostic view/scalar usage helpers remain available',
    'This compiler rejection covers DerefMut; absence of other mutable/owning/AsRef/AsMut APIs also requires the finite source/MIR inventory.')
(P/'probe-roster.json').write_text(json.dumps({'schema':1,'status':'source-only-unrun','probes':probes,'copied_independent_test_material':False},indent=2)+'\n')
print(json.dumps({'negative_fragments':len(probes),'compiler_execution':False,'extra_source_copies':0}))
