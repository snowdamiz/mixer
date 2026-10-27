#!/usr/bin/env python3
"""Close this independent review without mutating its frozen producer input."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

D=Path(__file__).resolve().parent
P=D.parent/'android-field-preservation-replacement-finite-controls'
SEAL='309dc0fe8b70849fd95df09b673577cbbb74dbeeac02c4aee9b01870306a9626'
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'

def identity(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

assert identity(P/'seal.json')['sha256']==SEAL
producer=json.loads((P/'seal.json').read_bytes())
assert producer['member_count']==146 and producer['member_bytes']==1408355
assert {str(path.relative_to(P)) for path in P.rglob('*') if path.is_file()}=={row['path'] for row in producer['members']}|{'seal.json'}
for row in producer['members']:
    assert not (P/row['path']).is_symlink()
    assert identity(P/row['path'])=={key:row[key] for key in ('bytes','sha256')}
run=D/'run-2';receipt=json.loads((run/'receipt.json').read_bytes())
assert receipt['status']=='narrow-four-body-finite-host-facets-accepted' and receipt['producer_replay_exact_json_equal']
assert identity(run/'actual-results.json')==identity(P/'run-2/actual-results.json')
for name in ('replay.py','IndependentFieldControls.java'):assert identity(D/name)==identity(run/name)
commands=json.loads((run/'commands.json').read_bytes())
assert [row['name'] for row in commands]==['java-version','javac-version','compile','producer-replay','independent-controls']
for row in commands:
    assert row['exit']==0 and row['reaped'] and not row['timeout']
    for stream in ('stdout','stderr'):assert identity(run/row[stream]['path'])=={key:row[stream][key] for key in ('bytes','sha256')}
argv=commands[2]['argv']
for flag in ('--release','17','-proc:none','-Xlint:all','-Werror'):assert flag in argv
assert '-g' not in argv and '-g:none' not in argv
for flag in ('-sourcepath','-classpath'):assert argv[argv.index(flag)+1].endswith('/scratch/empty')
for attempt in ('run-1','run-2'):
    cleanup=json.loads((D/attempt/'cleanup.json').read_bytes())
    assert cleanup['all_started_children_reaped'] and cleanup['maximum_concurrent_children']==1 and cleanup['owned_scratch_removed'] and cleanup['jdk_lease_preserved']
    assert not (D/attempt/'scratch').exists()
    provenance=json.loads((D/attempt/'provenance.json').read_bytes())
    assert provenance['runner']==identity(D/attempt/'replay.py')
    assert provenance['independent_control']==identity(D/attempt/'IndependentFieldControls.java')
failure=json.loads((D/'run-1/failure.json').read_bytes())
assert failure['status']=='actual-failed-attempt-no-pass-credit'
assert 'cannot assign a value to final variable input' in (D/'run-1/compile.stderr').read_text()
provenance=json.loads((P/'run-2/provenance.json').read_bytes())
closure={'source_roster':identity(P/'inputs/source-roster.json'),'control':identity(P/'FieldFiniteControls.java'),'runner':identity(P/'run_controls.py'),'product_source_map':identity(P/'inputs/selected-product-source-map.json'),'product_class_map':identity(P/'inputs/selected-product-class-map.json'),'contracts':identity(P/'inputs/exact-four-subject-contracts.json'),'tools':provenance['tools']}
closure_digest=hashlib.sha256(json.dumps(closure,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert closure_digest==producer['summary']['source_tool_closure_sha256']=='beae3c1db246c95cd24528848e8e7e3845d4efcd876ce5be889f42dc859c4411'
contracts=json.loads((P/'inputs/exact-four-subject-contracts.json').read_bytes())
joins=json.loads((P/'finite-facet-joins.json').read_bytes())
assert len(contracts['subjects'])==len(joins['subjects'])==4
subjects={subject['id']:subject for subject in contracts['subjects']}
results=json.loads((run/'actual-results.json').read_bytes())
row_counts=collections.Counter(row['subject_id'] for row in results['rows'])
reviewed=[]
for join in joins['subjects']:
    subject=subjects[join['subject_id']]
    assert join['categories']==subject['categories'] and join['required_semantic_cases']==subject['required_semantic_cases']
    assert join['original_required_finite_or_enclosing_cases']==subject['required_finite_or_enclosing_cases']
    assert join['source_sha256']==subject['source_sha256'] and join['class_sha256']==subject['class_sha256']
    assert row_counts[subject['id']]==join['actual_direct_host_rows']
    reviewed.append({'subject_id':subject['id'],'finite_host_facet':'accepted','actual_direct_rows':row_counts[subject['id']],'original_categories':subject['categories'],'original_required_semantic_cases':subject['required_semantic_cases'],'original_enclosing_semantic_cases':'retained-pending','allocation_or_partial_receiver_acceptance':False,'membership_release_authority':False,'native_callback_state_credit':0})
save(D/'review.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'accepted-only-four-exact-body-finite-host-facets','actionable_blockers_for_this_scope':[],'candidate':{'packet':str(P.relative_to(D.parent.parent)),'seal':identity(P/'seal.json'),'member_count':146,'member_bytes':1408355,'closed_custody_before_after':True},'selected_independent_run':'run-2','source_context':CONTEXT,'source_tool_closure_sha256':closure_digest,'producer_replay_actual_results':identity(run/'actual-results.json'),'producer_replay_byte_identical':True,'summary':receipt['producer_replay'],'additional_independent_controls':receipt['independent_controls'],'subjects':reviewed,'independent_failed_attempt':{'run':'run-1','status':'retained-actual-javac-failure-no-pass-credit','reason':'direct assignment to final Record.input in supplemental test; corrected to reversible reflection','source':identity(D/'run-1/IndependentFieldControls.java'),'runner':identity(D/'run-1/replay.py'),'stderr':identity(D/'run-1/compile.stderr')},'producer_failed_attempt':'sealed run-1 javac accessor collision retained without pass credit','original_full_checklist_equality':'producer sealed attestation only; no external originating packet reread in this independent review','scope_limitations':receipt['pending'],'Input_observations':'actual original NativeRenderer$2 interface returns/exceptions; separate from native callbacks','host_threads_total_started_joined':4,'maximum_concurrent_subprocesses':1,'all_children_reaped_owned_scratch_removed':True,'jdk_tool_lease_preserved':True,'native_UI_capture_process_inventory_started':False,'physical_cleanup_credit':False,'canonical_membership_release_native_OTA_GA_accepted':False})
members=[]
for path in sorted(D.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name!='seal.json':members.append({'path':str(path.relative_to(D)),**identity(path)})
save(D/'seal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed-independent-review-accepted-four-finite-host-facets','input_seal_sha256':SEAL,'source_context':CONTEXT,'selected_run':'run-2','members':members,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'scope':'only four exact FieldPreservation/Replacement finite host facets; no enclosing or release authority','pending':receipt['pending'],'native_UI_capture_process_inventory_started':False,'canonical_membership_release_native_OTA_GA_accepted':False})
for row in members:assert identity(D/row['path'])=={key:row[key] for key in ('bytes','sha256')}
print(json.dumps({'seal':identity(D/'seal.json'),'members':len(members),'bytes':sum(row['bytes'] for row in members),'status':'accepted-only-four-exact-body-finite-host-facets'},indent=2))
