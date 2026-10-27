#!/usr/bin/env python3
"""Narrow source-pinned raw row join for one attribute delegation.

API: validate_delegated_raw(raw_row) -> a typed consistency report, or
DelegatedRawRefusal. This grants no execution, helper, body or native admission.
"""
import hashlib
import json
from pathlib import Path

POLICY_SHA256='83b33c36c1945c137619d166f1f403bac142ecdb1144a34c3a1e9b19d3e41acf'

class DelegatedRawRefusal(ValueError):pass

def require(value,reason):
    if not value:raise DelegatedRawRefusal(reason)

def load_policy():
    raw=Path(__file__).with_name('policy.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==POLICY_SHA256,'immutable policy digest mismatch')
    policy=json.loads(raw)
    dependency=policy['mandatory_corrected_dependency']
    base=Path(__file__).resolve().parents[2]/dependency['packet']
    for name,key in [('seal.json','seal_sha256'),('typed_join.py','module_sha256'),('policy.json','policy_sha256')]:
        require(hashlib.sha256((base/name).read_bytes()).hexdigest()==dependency[key],'mandatory corrected dependency digest mismatch: '+name)
    return policy

def integer(value,reason):
    require(type(value)is int and value>=0,reason)
    return value

def boolean(value,expected,reason):
    require(type(value)is dict and set(value)=={'kind','value'} and value['kind']=='boolean' and type(value['value'])is bool and value['value']is expected,reason)

def frames_match(frames,policy):
    require(type(frames)is list and len(frames)==len(policy['exact_selected_frames']),'exact complete seven-frame selected chain')
    for actual,expected in zip(frames,policy['exact_selected_frames']):
        require(type(actual)is dict and set(actual)=={'class','method','descriptor','bci','line'},'selected frame fields')
        require(type(actual['class'])is str and type(actual['bci'])is int and type(actual['line'])is int,'selected frame scalar types')
        require(actual['class'].replace('.','/')==expected['class'] and all(actual[k]==expected[k] for k in ('method','descriptor','bci','line')),'exact selected source descriptor BCI full chain')

def native_observation(item,original,frames,index,policy):
    require(type(item)is dict,'native observation object')
    require(item.get('receiver_identity')==original,'actual selected native receiver')
    frames_match(item.get('production_frames'),policy)
    require(item.get('production_frames')==frames,'actual native complete frames equal immutable raw event')
    require(type(item.get('native_event_sequence_index'))is int and item['native_event_sequence_index']==index,'actual completion immutable event index')
    require(item.get('native_event_phase')=='beforeReturn','actual completion source hook phase')
    require(item.get('native_outcome_association') in ('original-own-hook-event','selected-original-delegated-overload-return'),'explicit source association marker')

def authority(row,selected=None):
    original=row['original_target']
    require(type(original)is str and original.startswith('android.view.inputmethod.BaseInputConnection@') and bool(original.rsplit('@',1)[1]),'original receiver identity')
    original_authority=row['original_authority']
    require(original_authority['receiver']==original_authority['attempt']['target']==original,'original captured receiver/attempt target')
    require(row['original_attempt']==original_authority['attempt']['identity'] and row['original_record']==original_authority['record']['identity'],'original attempt/record identity')
    if selected is not None:
        captured=selected['authority']
        require(captured['receiver']==captured['attempt']['target']==original,'selected immutable authority receiver')
        require(captured['attempt']['identity']==row['original_attempt'] and captured['record']['identity']==row['original_record'],'selected immutable original attempt/record')
    return original

def _validate(row):
    policy=load_policy()
    require(type(row)is dict and row.get('family')==policy['family'],'exact selected family')
    require(row.get('state') in policy['states'],'explicit selected state')
    state=row['state'];rule=policy['states'][state]
    original=authority(row)
    require(type(row.get('actual_native_outcomes'))is list and len(row['actual_native_outcomes'])<=65536,'actual native outcome bounded list')
    require(type(row.get('native_sequence'))is list and len(row['native_sequence'])<=100000,'immutable raw native sequence required')
    require(type(row.get('frame_sets'))is list and len(row['frame_sets'])<=100000,'immutable raw frame sets required')
    require(type(row.get('selected_event'))is list,'immutable selected event list required')
    end=integer(row.get('operation_end_sequence'),'public operation end index')
    require(end<=len(row['native_sequence']),'public operation end within raw trace')
    count=integer(row.get('native_target_entries'),'actual native entry count type')
    require(count==rule['selected_native_entries'],'source-specific actual native entry count')
    # Never filter away wrong receiver/completion rows before validating them.
    observations=[x for x in row['actual_native_outcomes'] if type(x)is dict and x.get('method')==policy['method']]
    require(all(type(x)is dict for x in row['actual_native_outcomes']),'native observation row type')
    events=[]
    for at,event in enumerate(row['native_sequence']):
        require(type(event)is dict,'raw native event object')
        if event.get('method')==policy['method']:events.append((at,event))
    public=row.get('actual_operation_outcome')
    if rule['phase']=='public-entry':
        require(not events and not observations and not row['selected_event'],'pre-public refusal has no selected native event/completion')
        boolean(public,False,'pre-public exact refused public result')
        return {'state':state,'state_phase':'public-entry','canonical_alias':None,'native_entries':0,'actual_normal_native_returns':0,'native_result':'not-entered','public_outcome':public,'join':'typed-consistent','helper_body_outcome':'pending','qualified':False}
    require(len(events)==2,'exact one selected native entry and one before-return event')
    (entry_at,entry),(return_at,returned)=events
    require(entry_at<return_at<end and entry.get('phase')=='entry' and returned.get('phase')=='beforeReturn','original chronological native entry/return pair')
    require(entry.get('receiver_identity')==returned.get('receiver_identity'),'same immutable raw ordinal receiver')
    raw_receiver=entry.get('receiver_identity')
    require(type(raw_receiver)is str,'raw receiver ordinal string')
    receiver_class,separator,ordinal=raw_receiver.partition('@row-')
    require(separator=='@row-' and receiver_class==original.rsplit('@',1)[0] and ordinal.isdecimal() and int(ordinal)>0,'raw ordinal and global receiver representations')
    entry_frame=integer(entry.get('frame_set'),'entry frame-set index type')
    return_frame=integer(returned.get('frame_set'),'return frame-set index type')
    require(entry_frame==return_frame<len(row['frame_sets']),'same exact immutable selected frame-set index')
    frames=row['frame_sets'][entry_frame];frames_match(frames,policy)
    require(len(row['selected_event'])==1,'exactly one selected immutable event')
    selected=row['selected_event'][0]
    expected_index=entry_at if rule['phase']=='native-hook-entry' else return_at
    require(type(selected)is dict and type(selected.get('sequence_index'))is int and selected['sequence_index']==expected_index,'selected immutable state-specific event index')
    require(type(selected.get('frame_set'))is int and selected['frame_set']==entry_frame,'selected immutable complete frame-set index')
    authority(row,selected)
    require(all(item.get('receiver_identity')==original for item in observations),'foreign selected method observation cannot be filtered away')
    if rule['normal_completion_count']==2:
        require(len(observations)==2,'two actual normal returns required, no duplicate/foreign/exception substitution')
        inner,outer=observations
        require(inner.get('descriptor')==policy['inner_descriptor'] and outer.get('descriptor')==policy['outer_descriptor'],'exact ordered inner and attribute overload descriptors')
        for item in observations:
            require(item.get('completion')=='return' and item.get('original_exception_class')is None and item.get('original_exception_identity')is None,'actual normal completion without exception')
            native_observation(item,original,frames,return_at,policy)
            boolean(item.get('value'),True,'source-specific original native typed Boolean result')
        require(inner['native_outcome_association']=='original-own-hook-event' and outer['native_outcome_association']=='selected-original-delegated-overload-return' and outer.get('delegated_leaf_descriptor_pair')==[policy['inner_descriptor'],policy['outer_descriptor']],'exact source-selected delegation marker and descriptor pair')
        boolean(public,rule['public_result'],'source-specific public result or postcheck refusal')
        return {'state':state,'state_phase':rule['phase'],'canonical_alias':rule['canonical_alias'],'native_entries':1,'actual_normal_native_returns':2,'selected_event_index':expected_index,'return_event_index':return_at,'native_result':{'kind':'boolean','value':True},'public_outcome':public,'join':'typed-consistent','supplier_helper_body_outcome':'pending-no-method-exit-observation','qualified':False}
    require(len(observations)==1,'one actual original hook exception observation, no normal return inference')
    exception=observations[0]
    native_observation(exception,original,frames,return_at,policy)
    require(exception.get('descriptor')=='hook-exception' and exception.get('completion')=='exception' and exception.get('native_outcome_association')=='original-own-hook-event','actual original hook exception descriptor/completion')
    require(type(exception.get('value'))is dict and set(exception['value'])=={'kind'} and exception['value']['kind']=='null','hook exception has no invented scalar value')
    expected_class='java.lang.IllegalStateException' if state=='ordinary-throw-after-callback' else 'dev.mixer.android.DirectBoundaryStates$Fatal'
    identity=exception.get('original_exception_identity')
    require(type(identity)is str and bool(identity) and exception.get('original_exception_class')==expected_class,'exact source-authored original exception class/identity')
    require(type(public)is dict and set(public)=={'kind','identity','class'} and public=={'kind':'exception','identity':identity,'class':expected_class},'public preserves actual original hook exception identity')
    editor=row['post_operation_authority']['editor']
    require(editor['primary']==identity,'post-operation primary original exception identity')
    if state=='ordinary-throw-after-callback':require(editor['firstFatal']is None,'ordinary path does not invent first-fatal')
    else:require(editor['firstFatal']==identity,'exact source-authored first fatal identity')
    return {'state':state,'state_phase':rule['phase'],'canonical_alias':rule['canonical_alias'],'native_entries':1,'actual_normal_native_returns':0,'selected_event_index':expected_index,'return_event_index':return_at,'native_result':'pending-no-actual-normal-native-body-completion','actual_hook_exception':{'kind':'exception','identity':identity,'class':expected_class},'public_outcome':public,'join':'typed-consistent-hook-and-public-exception-identity','supplier_helper_body_outcome':'pending-no-method-exit-observation','qualified':False}

def validate_delegated_raw(raw_row):
    """Refuse malformed/wrong raw evidence; never mutate row or policy.

    Source/class and execution authenticity must be verified by the enclosing
    reviewed producer. This function supplies only the exact data consistency
    join. Status/expected fields are diagnostic and cannot grant authority.
    """
    try:
        result=_validate(raw_row)
        result.update(policy_sha256=POLICY_SHA256, source_class_context='requires-enclosing-immutable-product-source-and-class-verification',
            state_mutation_and_authority_review='pending; typed data consistency is not state/helper/body admission',
            execution_closure='pending-external-trusted-source-closure',native='pending',OTA='pending',GA='pending')
        return result
    except DelegatedRawRefusal:raise
    except (KeyError,TypeError,ValueError,IndexError,AttributeError) as error:
        raise DelegatedRawRefusal('missing or malformed required raw observation: '+str(error)) from error
