#!/usr/bin/env python3
"""Seal preaccess evidence only; do not inspect the active correction directory."""
from pathlib import Path
import datetime,hashlib,json,sys,shutil
D=Path(__file__).resolve().parent
ROOT=D.parents[1]
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def verify(directory,name,expected):
    seal=directory/name;assert row(seal)['sha256']==expected
    members=json.loads(seal.read_text())['members']
    for item in members:
        path=directory/item['path'];assert not path.is_symlink();assert row(path)=={key:item[key] for key in ['bytes','sha256']},str(path)
    return {'seal':str(seal.relative_to(ROOT)),**row(seal),'members':len(members),'member_bytes':sum(item['bytes'] for item in members)}
assert not (D/'preaccess-seal.json').exists()
protected=[verify(ROOT/'verification/android-editor-replacement-independent','review-seal.json','11cd26bbc78f54e48de297b931fab2fcb9becce4d4aa4884d145641f2a615b15'),verify(ROOT/'verification/android-editor-focus-history-contract-independent','seal.json','d9322aa82b39a83eacc1deacf90801f8b89cee2ed23babc968520bf9f38c881f')]
contracts={}
for name,expected in [('focus-history-event-reentry-amendment.md','33000d3b55f0a7258c396b8ea846595371a590e16a5679cb4640d1782a4c6f3c'),('focus-history-event-reentry-selection.json','f14d6ef48e0e54211ec3a6968f47d3e09538bf03df428d58a19d620dac12213f')]:
    source=ROOT/'verification/android-editor-boundary-root-review'/name;assert row(source)['sha256']==expected;shutil.copyfile(source,D/'inputs'/name);contracts[name]=row(source)
for name in ['AGENTS.md','mixer-product-plan.md']:
    shutil.copyfile(ROOT/name,D/'inputs'/name)
checks=[]
for index in [1,2,3]:
    run=D/('typecheck-'+str(index));receipt=json.loads((run/'receipt.json').read_text());assert not (run/'empty-source').exists()
    if index==1:
        assert all(item['reaped'] and item['exit_code']==0 for item in receipt['commands']);expected=receipt['source']['sha256']
    else:
        assert receipt['reaped'] and receipt['exit_code']==0;expected=receipt['control_source_sha256']
    assert row(run/'FocusHistoryControls.java')['sha256']==expected
    checks.append({'path':str(run.relative_to(D)),'receipt':row(run/'receipt.json'),'product_executions':0,'status':'compiled-controls-only'})
assert row(D/'FocusHistoryControls.java')==row(D/'typecheck-3/FocusHistoryControls.java')
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'scope':'Independent actual-source controls/roster preaccess only; not candidate review or product execution','protected_prior_packets_verified_unchanged':protected,'additional_event_reentry_contracts':contracts,'all_input_copies':{str(path.relative_to(D)):row(path) for path in sorted((D/'inputs').iterdir()) if path.is_file()},'source_controls':{'FocusHistoryControls.java':row(D/'FocusHistoryControls.java'),'prospective_entrypoints':12,'required_real_twofield_witnesses':'foundation/AdditionalReplacementControls.java (both retained required-success assertions)','obligation_groups':19},'control_typechecks':checks,'new_interfaces':'The five new Input methods and FieldPreservation are prospective reflective hooks only; they are not present in the old types and not validated by compilation. Exact hook binding and full actual-source execution await root release.','candidate_reads':0,'candidate_directory_enumerations':0,'candidate_hashes':0,'candidate_executions':0,'any_product_method_or_constructor_invoked':0,'canonical_Git_or_prior_sealed_writes':False,'native_UI_capture_or_process_inventory':False,'cleanup':{'compiler_and_version_children_reaped':True,'empty_source_directories_removed':True,'compiled_control_artifacts_retained_for_evidence':True,'other_projects_touched':False},'pending':['Root exact frozen correction release and admission verification','Complete actual-source audit, source-preserving hook binding, producer and independent host replay','Pinned official SDK/D8 as appropriate','Native qualification and all public/GA gates after separate authorization']}
(D/'preaccess-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
members=[]
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():members.append({'path':str(path.relative_to(D)),**row(path)})
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent focus-history preaccess requirements/control-source/typecheck packet; zero active-candidate access or product execution','members':members,'member_count':len(members),'member_bytes':sum(item['bytes'] for item in members)}
data=(json.dumps(seal,indent=2)+'\n').encode();(D/'preaccess-seal.json').write_bytes(data);print(json.dumps({'seal':str(D/'preaccess-seal.json'),'sha256':hashlib.sha256(data).hexdigest(),'members':len(members),'bytes':seal['member_bytes'],'candidate_access':0,'product_executions':0}))
