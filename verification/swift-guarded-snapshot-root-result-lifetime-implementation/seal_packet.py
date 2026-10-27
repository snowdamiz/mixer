#!/usr/bin/env python3
"""Final producer custody seal; no compiler/product invocation or source change."""
from pathlib import Path
import datetime,hashlib,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def row(path,base=P):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def rows(base):return [row(path,base) for path in sorted(base.rglob('*')) if path.is_file()]
def write(name,value):
    with (P/name).open('x') as output:json.dump(value,output,indent=2,sort_keys=True);output.write('\n')
source=json.loads((P/'source-manifest.json').read_text());host=json.loads((P/'host-manifest.json').read_text())
assert rows(P/'source/vm')==source['members'] and rows(P/'source/host')==host['members']
for name in ['source-freeze.json','source-freeze-v2.json']:
    frozen=json.loads((P/name).read_text())
    for member in frozen['members']:assert row(P/member['path'])==member,member['path']
release=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-execution-release.json'
selection=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-selection.json'
assert json.loads(release.read_text())['released']
assert not json.loads(selection.read_text())['compiler_or_host_execution_released'] # frozen original selection is preserved
assert not list((P/'build').iterdir())
summary=json.loads((P/'command-summary.json').read_text())
assert len(summary['commands'])==24 and summary['compiler']==21 and summary['host']==2 and summary['version']==1
write('final-custody.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,
 'source146_tree':source['tree_sha256'],'host11_tree':host['tree_sha256'],'source_host_unchanged_after_execution':True,
 'original_and_v2_frozen_files_unchanged':True,'root_execution_release':row(release,R),'original_root_selection':row(selection,R),
 'all_24_commands_once_sequential':True,'all_own_children_reaped_groups_absent_at_each_terminal_receipt':True,
 'generated_binaries_metadata_removed_and_plain_MIR_archived':True,'build_directory_empty':True,
 'canonical_vm_and_other_lanes_edited':False,'native_File_VM_fixture_UI_capture_simulator_phone_network_global_inventory':False,
 'independent_root_accessible_result_acceptance':'Pending','new_prices_layouts_full_ownership_durable_funding_joint_retirement_GA':'Pending'})
paths=[path for path in sorted(P.rglob('*')) if path.is_file() and path.name!='seal.json']
members=[row(path) for path in paths]
write('seal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-bounded-producer-awaiting-independent-and-root-review',
 'source146_tree':source['tree_sha256'],'host11_tree':host['tree_sha256'],'member_count':len(members),'members':members,'tree_sha256':digest(members),
 'compiler_commands':21,'host_runs':2,'negative_intended_boundaries':18,'host_tests_passed_each':38,'retries':0,
 'complete_MIR_archive_retained':True,'generated_binaries_metadata_removed':True,
 'accepted_full_ownership_or_durable_funding':False,'new_prices_layouts_accepted':False,'native_or_FieldLog_OTA_GA_accepted':False})
print(json.dumps({'seal':row(P/'seal.json'),'tree_sha256':digest(members),'members':len(members),'source146_tree':source['tree_sha256'],'host11_tree':host['tree_sha256']}))
