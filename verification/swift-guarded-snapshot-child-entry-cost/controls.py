#!/usr/bin/env python3
import copy,hashlib,json,sys
from pathlib import Path
from quote import RequiredCuts,evaluate,Refused,U64,add,mul
D=Path(__file__).resolve().parent;checks=[]
def check(name,yes):
    if not yes:raise AssertionError(name)
    checks.append(name)
def refused(name,fn):
    try:fn()
    except (Refused,TypeError,KeyError):checks.append(name);return
    raise AssertionError('not refused:'+name)
L=json.loads((D/'ledger.json').read_text());S=json.loads((D/'source-shapes.json').read_text())['new_shapes']
check('claims-source256',S['UnverifiedProfileDigestBytesV1']['leaves']==256)
check('actual-return-source2556-not-native13608',S['OwnedFixtureOutcomeV1']['leaves']==2556)
check('six-source-functions-fully-expanded',len(L['functions'])==6 and L['complete_four_plus_helpers_source_work']==119922)
check('setup15384-six-times2564',L['setup_source_work']==6*2564==15384)
check('24-default59-clone',L['functions']['cancellation_default']['local_actions']==24 and L['functions']['cancellation_clone']['local_actions']==59)
check('188roles-native-layouts-not-work',len(L['actual_native_layouts_as_data'])==188 and sum(v['bytes'] for v in L['actual_native_layouts_as_data'])==76696 and L['complete_four_plus_helpers_source_work']!=76696)
check('pointee-Copy12-complete-value-destinations',len(L['dereference_Copy_coverage'])==12 and all(w['all_applicable_mention_charge']>=w['pointee_value_transfer_leaves'] for w in L['dereference_Copy_coverage']))
check('53drop-visits',L['during_entry_drop_visit_bound']==53)
for attempts in range(6):
    next_checks=attempts+1
    check('finite-setup-prefix:'+str(attempts),attempts<=5 and next_checks<=6)
check('fifth-completion-needs-sixth-next',5+1==6)
# These are explicit abstract finite controls only, never selected real paths,
# error bounds, payload prices, root policy or a genuine fixture.
values=dict(path_bytes=(1,2,3,4,5),path_native_request_bytes=(2,3,4,5,6),p0_path_backing_bytes=(1,2,3,4,5),io_error_native_request_bytes=1,retained_io_error_backing_bytes=1,during_entry_payload_drop_work=1,loader_payload_work=1,leaf_payload_work=1,returned_outcome_payload_drop_work=1)
g=RequiredCuts(**values);result=evaluate(g,L)
check('explicit-cut-arithmetic',result['entry_shell_work']==119922+24+20+1+53)
check('payload-cuts-stay-separate',result['separate_external_payload_work']==dict(loader=1,leaf_P3_P4=1,returned_P5=1))
check('not-complete-or-granted',not result['complete_component_accepted'] and not result['operational_grant'] and not result['root_bindings_verified'])
for key in values:
    d=values.copy();d.pop(key);refused('missing-cut:'+key,lambda d=d:RequiredCuts(**d))
    d=values.copy();d[key]=(0,)*5 if isinstance(values[key],tuple) else 0;refused('zero-cut:'+key,lambda d=d:evaluate(RequiredCuts(**d),L))
    d=values.copy();d[key]=None;refused('unknown-cut:'+key,lambda d=d:evaluate(RequiredCuts(**d),L))
for unknown in ((1,2,3,4),(),(1,2,3,4,5,6),(1,2,3,4,None)):
    d=values.copy();d['path_bytes']=unknown;refused('path-shape:'+str(unknown),lambda d=d:evaluate(RequiredCuts(**d),L))
d=values.copy();d['path_bytes']=(1,2,3,4,4097);d['path_native_request_bytes']=(2,3,4,5,4098);d['p0_path_backing_bytes']=(1,2,3,4,4097)
check('no-invented4096-cap',evaluate(RequiredCuts(**d),L)['cuts']['path_bytes'][4]==4097)
for field in ('path_native_request_bytes','p0_path_backing_bytes'):
    d=values.copy();d[field]=(1,1,1,1,1);refused('path-not-covered:'+field,lambda d=d:evaluate(RequiredCuts(**d),L))
for n in (0,1,2,U64-1,U64):
    check('checked-multiply-zero:'+str(n),mul(n,0)==0)
refused('add-overflow',lambda:add(U64,1));refused('mul-overflow',lambda:mul(U64,2))
d=values.copy();d['during_entry_payload_drop_work']=U64;refused('payload-overflow',lambda:evaluate(RequiredCuts(**d),L))
for label,mutate in [('omitted-source-part',lambda q:q['functions']['copy_claims_v1']['parts'].pop('parameter_leaf_fetch_store')),('sixth-endpoint',lambda q:q['functions']['setup_files_once_v1'].update(repeat=5)),('native-allocation-omitted',lambda q:q.update(requested_Cancellation_allocation_bytes=0)),('unknown-authored-helper',lambda q:q['functions']['cancellation_clone']['calls'][0].update(role='UNKNOWN')),('cycle',lambda q:q['functions']['cancellation_clone']['calls'][0].update(role='run_prepaid_fixture_v1')),('drop-visit-omitted',lambda q:q.update(during_entry_drop_visit_bound=0))]:
    q=copy.deepcopy(L);mutate(q);refused(label,lambda q=q:evaluate(g,q))
# Removing a whole known callee is a semantic omission. Detect it against exact
# source statement/call binding; arithmetic evaluation alone is not authority.
q=copy.deepcopy(L);q['functions']['run_prepaid_fixture_v1']['calls']=[c for c in q['functions']['run_prepaid_fixture_v1']['calls'] if c['role']!='copy_claims_v1']
refused('authored-copy-helper-omission',lambda:evaluate(g,q))
report=dict(schema=1,checks_passed=len(checks),python=sys.version,passed=True,synthetic_geometry_only=True,selected_final_paths=False,selected_complete_quote=False,independent_review_required=True,names=checks)
(D/'controls.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(D/'synthetic-quote-control.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(checks=len(checks),source_core=119922,real_geometry_selected=False,complete_component=False)))
