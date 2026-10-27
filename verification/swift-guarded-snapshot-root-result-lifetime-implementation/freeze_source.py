#!/usr/bin/env python3
"""Freeze the prepared source and exact prospective roster without running it."""
from pathlib import Path
import datetime,hashlib,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(v):return hashlib.sha256(v).hexdigest()
def row(path,base=P):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def write(name,v):(P/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
base=R/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction/source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
new=P/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
old_text=base.read_text();new_text=new.read_text()
def retirement(text):return text[text.index('    #[must_use]\n    struct CompleteAcquisitionRetirementV1'):text.index('    #[cfg(test)]\n    mod prepaid_actual_owner_v1')]
assert retirement(old_text)==retirement(new_text),'IR01 retirement path changed'
source=json.loads((P/'source-manifest.json').read_text());host=json.loads((P/'host-manifest.json').read_text())
selection=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-selection.json'
assert not json.loads(selection.read_text())['compiler_or_host_execution_released']
assert sha((R/'verification/swift-guarded-snapshot-root-result-lifetime-contract/seal.json').read_bytes())=='5cbf7f3c49baa7e8db9a61ee720a9e5eee0d81241a580d8997b75fad6030c4eb'
write('source-only-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'status':'source-frozen-awaiting-root-review-and-compiler-release','python':sys.version,
  'source146_tree':source['tree_sha256'],'host11_tree':host['tree_sha256'],'host11_byte_identical':True,
  'changed':source['changed'],'new_distribution_members':0,'source_copy_count':1,
  'IR01_retirement_region_byte_identical':True,'root_selection':row(selection,R),
  'preparation_commands':[['/opt/homebrew/opt/python@3.14/bin/python3.14','-B',str(P/name)] for name in ['prepare_source.py','edit_source.py','edit_cache.py','edit_tests.py','finish_source.py','prepare_probes.py','prepare_manifest.py','prepare_roster.py','freeze_source.py']],
  'source_work_authorized':True,'compiler_commands_executed':0,'host_product_runs_executed':0,'compiler_version_queries_executed':0,
  'native_File_acquisition_VM_fixture_UI_capture_simulator_phone_network_global_inventory':False,
  'owned_compiler_or_host_process_started':False,'generated_binaries':[],
  'contract_cases_status':'Prospective; source coverage and scope gaps detailed in README, probe roster and private inventory. No evidence passes claimed.',
  'Pending':['compiler diagnostics','complete MIR/private inventory review','host core/guard runs','new layouts/prices/funding review','native File setup and actual VM leaf/child evidence','forgotten root/result durable funding','root shutdown','full ownership','useful joint retirement','native selectors/custody/healthy close','FieldLog','OTA','GA'],
  'native_UI_capture_runtime':'Paused/Pending'})
names=['README.md','source-origin.json','source-manifest.json','host-manifest.json','source-audit.json','source-delta.patch','private-transition-inventory.json','probe-roster.json','proposed-command-roster.json','source-only-receipt.json','prepare_source.py','edit_source.py','edit_cache.py','edit_tests.py','finish_source.py','prepare_probes.py','prepare_manifest.py','prepare_roster.py','run_bounded.py','freeze_source.py']
paths=[P/name for name in names]+sorted((P/'probes').glob('*.inc.rs'))
write('source-freeze.json',{'schema':1,'status':'immutable-source-proposal-no-compiler-or-host-execution','source146_tree':source['tree_sha256'],'host11_tree':host['tree_sha256'],
  'members':[row(p) for p in sorted(paths)],'source_members_pinned_indirectly_by_manifests':True,
  'source_and_probes_must_remain_unchanged':True,'all_new_prices_layouts_funding_acceptance':False})
print(json.dumps({'source_freeze':row(P/'source-freeze.json'),'source_manifest':row(P/'source-manifest.json'),'command_roster':row(P/'proposed-command-roster.json'),'runner':row(P/'run_bounded.py')}))
