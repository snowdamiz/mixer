#!/usr/bin/env python3
"""Independent read-only review of the frozen one-overload association packet.

Only imports the inspected pure data helper; never starts a JVM or harness.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from example_adapter import PACKET, SEAL, read_rows

def require(value, reason):
    if not value: raise ValueError(reason)

def checked_member(name):
    seal=json.loads((PACKET/'seal.json').read_text())
    require(hashlib.sha256((PACKET/'seal.json').read_bytes()).hexdigest()==SEAL,'input seal drift')
    entry=next(m for m in seal['members'] if m['path']==name)
    path=PACKET/name
    require(path.stat().st_size==entry['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],'member identity drift: '+name)
    return path

def selected_pair(row):
    return [i for i in row['actual_native_outcomes'] if i['method']=='BaseInputConnection.setComposingRegion' and i['receiver_identity']==row['original_target'] and i['completion']=='return']

def joined_review(row):
    """Add immutable raw-event and authority checks to the pair-level helper.

    This bounded review only accepts the frozen current state; it does not
    generalize lifecycle or query successor behavior or authorize execution.
    """
    require(row['state']=='current','bounded current-state review only')
    pair=selected_pair(row)
    require(len(pair)==2,'exact pair count')
    inner,outer=pair
    require([x['descriptor'] for x in pair]==['(II)Z','(IILandroid/view/inputmethod/TextAttribute;)Z'],'exact pair descriptor order')
    selected=row['selected_event']
    require(len(selected)==1,'one selected event')
    authority=selected[0]['authority']
    require(row['original_target']==row['original_authority']['receiver']==row['original_authority']['attempt']['target']==authority['receiver']==authority['attempt']['target'],'immutable selected original receiver binding')
    index=inner['native_event_sequence_index']
    require(type(index)is int and index==outer['native_event_sequence_index']==selected[0]['sequence_index'],'selected exact immutable event index')
    require(0<=index<len(row['native_sequence']),'event index in raw trace')
    event=row['native_sequence'][index]
    require(event['method']==inner['method'] and event['phase']==inner['native_event_phase']==outer['native_event_phase']=='beforeReturn','actual raw event method/phase')
    require(event['frame_set']==selected[0]['frame_set'] and row['frame_sets'][event['frame_set']]==inner['production_frames']==outer['production_frames'],'immutable complete raw frame chain')
    # Global identity strings and row ordinals intentionally stay distinct.
    # Their binding comes from selected event index + captured authority.
    require(isinstance(event['receiver_identity'],str) and '@row-' in event['receiver_identity'],'raw receiver ordinal representation')
    before=row['native_sequence'][:row['operation_end_sequence']]
    entries=[(at,e) for at,e in enumerate(before) if e['method']==event['method'] and e['receiver_identity']==event['receiver_identity'] and e['phase']=='entry' and e['frame_set']==event['frame_set']]
    returns=[(at,e) for at,e in enumerate(before) if e['method']==event['method'] and e['receiver_identity']==event['receiver_identity'] and e['phase']=='beforeReturn' and e['frame_set']==event['frame_set']]
    require(len(entries)==row['native_target_entries']==1 and len(returns)==1 and entries[0][0]<index==returns[0][0],'one actual entry/return pair; no intervening or duplicate entry')
    expected={'kind':'boolean','value':True}
    require(inner['value']==outer['value']==row['actual_operation_outcome']==expected,'current native and public exact actual typed value')
    return {'selected_event_sequence_index':index,'raw_event_frame_set':event['frame_set'],'entry_index':entries[0][0],'native_normal_returns':2,'public_result':True,'qualified':False}

def attempt(fn,row):
    try: fn(row)
    except (ValueError,KeyError,TypeError,IndexError) as error: return {'refused':True,'reason':str(error)}
    return {'refused':False}

def run():
    reviewed=['delegated_association.py','test_delegated_association.py','producer-run/OutcomeCapture.java','producer-run/DirectBoundaryStates.java','producer-run/EventJoinControls.java','inputs/102/NativeOutcomeProbe.java','producer-run/event-join-controls.stdout','standalone-replay/EventJoinControls.stdout']
    identities={name:hashlib.sha256(checked_member(name).read_bytes()).hexdigest() for name in reviewed}
    spec=importlib.util.spec_from_file_location('frozen_delegated_association',checked_member('delegated_association.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    positives=[]
    rows_by_file={}
    for name in ('producer-run/direct-setComposingRegionWithAttributes.rows.jsonl.gz','standalone-replay/attribute-states.rows.jsonl.gz'):
        rows,_=read_rows(name);rows_by_file[name]=rows
        for row in rows:module.validate_row(row)
        base=next(r for r in rows if r['state']=='current')
        positives.append({'input':name,'pair_helper_rows_checked':len(rows),'independent_current_join':joined_review(base)})
    base=copy.deepcopy(rows_by_file['producer-run/direct-setComposingRegionWithAttributes.rows.jsonl.gz'][0])
    def both(row, fn):
        for item in selected_pair(row):fn(item)
    def coherent_receiver(row):
        pair=selected_pair(row)
        row['original_target']='foreign.receiver@999'
        for item in pair:item['receiver_identity']=row['original_target']
    def intervening_entry(row):
        pair=selected_pair(row);at=pair[0]['native_event_sequence_index'];event=copy.deepcopy(row['native_sequence'][at]);event['phase']='entry';row['native_sequence'].insert(at+1,event);row['operation_end_sequence']+=1
    mutations={
        'wrong-one-frame':lambda r:selected_pair(r)[1].__setitem__('production_frames',[]),
        'missing-both-frames':lambda r:both(r,lambda i:i.__setitem__('production_frames',[])),
        'coherent-truncated-frame-chain':lambda r:both(r,lambda i:i.__setitem__('production_frames',i['production_frames'][:1])),
        'coherent-wrong-event-index':lambda r:both(r,lambda i:i.__setitem__('native_event_sequence_index',i['native_event_sequence_index']+1)),
        'coherent-wrong-receiver':coherent_receiver,
        'coherent-wrong-native-value':lambda r:both(r,lambda i:i.__setitem__('value',{'kind':'boolean','value':False})),
        'wrong-outer-descriptor':lambda r:selected_pair(r)[1].__setitem__('descriptor','(II)Z'),
        'intervening-raw-native-entry':intervening_entry,
        'duplicate-outer-completion':lambda r:r['actual_native_outcomes'].append(copy.deepcopy(selected_pair(r)[1])),
    }
    controls=[]
    for name,mutation in mutations.items():
        row=copy.deepcopy(base);mutation(row)
        helper=attempt(module.validate_row,row);independent=attempt(joined_review,row)
        require(independent['refused'],'independent immutable join accepted '+name)
        controls.append({'name':name,'producer_pair_helper':helper,'independent_raw_join':independent})
    source_findings=[
        {'source':'producer-run/OutcomeCapture.java:7-11','finding':'Capture faults dirty the attempt; end latches cleanliness. Original return/exception identity is preserved by NativeOutcomeProbe. No authority decision is granted.'},
        {'source':'producer-run/OutcomeCapture.java:14-21','finding':'Actual boolean/integer and selected mutable text/reference snapshots are distinct. Unsupported reference bodies and absent outcomes do not supply typed snapshot/body coverage.'},
        {'source':'producer-run/DirectBoundaryStates.java:34-44','finding':'Recorder binds actual receiver object and exact complete frame chain to immutable original events. Only the exact inner(II)Z -> outer(II,TextAttribute)Z descriptor pair can share the last return, with equal actual Boolean values; extra pending entry, wrong value/receiver/order/descriptor and duplicate outer refuse.'},
        {'source':'producer-run/EventJoinControls.java:26-30','finding':'Frozen JVM controls cover real two-return/one-event delegation and actual wrong value, intervening entry, wrong descriptor, duplicate outer, wrong receiver and missing inner/order refusal. This review did not rerun a JVM.'},
        {'source':'delegated_association.py:5-23','finding':'The pair-level offline helper checks two typed observations, exact descriptors/order, equality, fixed first caller BCI and markers. It does not itself authenticate raw event index/full frame chain, original authority receiver, raw intervening entry or native/public value. Coherent data mutations accepted by that helper are refused by the independent bounded raw join.'},
    ]
    return {'schema':1,'input_seal_sha256':SEAL,'checked_members':identities,'positive_reviews':positives,'mutation_controls':controls,'source_findings':source_findings,
        'source_recorder_association_verdict':'bounded exact source-selected delegation supported; missing body outcomes remain pending',
        'pair_helper_general_use':'requires immutable raw/compact binding plus source-specific public result checks; pair helper alone is insufficient',
        'execution_closure':'excluded and pending','stopped_v5_experiment':'excluded','native_runtime_started':False,'qualified':False}

if __name__=='__main__': print(json.dumps(run(),indent=2))
