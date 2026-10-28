#!/usr/bin/env python3
"""Finite read-only evidence join; writes only this new proposal packet."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import sys
import time
import contract

D=Path(__file__).resolve().parent;R=D.parents[1]
I=R/'verification/swift-root-bound-work-storage-delta'
A=R/'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json'
V3=R/'verification/swift-root-bound-work-storage-layout-probe-v3'
SOURCE=R/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm'
PREFIXES=['experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::',
 'experimental_swift_reactor::retained_profile_loader_v1::',
 'experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::',
 'experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::',
 'std::result::','std::option::','std::fs::']

def need(value,reason):
    if not value:raise ValueError(reason)
def unique(pairs):
    obj={}
    for k,v in pairs:need(k not in obj,'duplicate JSON key');obj[k]=v
    return obj
def decode(raw):return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def hashed(path):
    need(path.is_file() and not path.is_symlink(),'regular input:'+str(path));raw=path.read_bytes();return {'bytes':len(raw),'sha256':sha(raw)}
def row(path):return {'path':str(path.relative_to(R)) if path.is_relative_to(R) else str(path),**hashed(path)}
def pin(record,base=R):
    path=Path(record['path']);path=path if path.is_absolute() else base/path
    need(hashed(path)=={k:record[k] for k in ['bytes','sha256']},'pin:'+str(path));return path
def put(name,obj):
    with (D/name).open('x') as handle:json.dump(obj,handle,indent=2,sort_keys=True);handle.write('\n')
def normalized_type(text):
    # Finite source-scope qualifier aliases and lifetime erasure only. No generic
    # type substitution, borrowed-pointee matching or arbitrary suffix matching.
    for prefix in PREFIXES:text=text.replace(prefix,'')
    return text.replace("&'static ",'&').replace("&'_ ",'&').replace("'_","'static").replace(' ','')

def roles(inventory):
    result=[]
    for fi,fn in enumerate(inventory['functions_and_constructor_occurrences']):
        for kind,items in [('argument',fn['argument_places']),('local_return',fn['rows'])]:
            for ri,item in enumerate(items):
                if 'storage_role' not in item:continue
                role=item['storage_role']
                result.append({'id':f'F{fi:02d}:{kind}:{ri}','function_selector':fn['selector'],
                    'function_index':fi,'item_index':ri,'kind':kind,'place':item.get('place'),
                    'MIR_item_index':fn['MIR']['index'],'MIR_item_sha256':fn['MIR']['sha256'],
                    'MIR_row_line':item.get('line'),'MIR_row_sha256':item.get('sha256'),
                    'type_spelling':role['type_spelling'],'representation_class':role['representation_class'],
                    'storage_obligations':role['obligations'],'function_obligations':fn['obligations']})
    return result

def make(inventory,accepted,query):
    need(len(contract.SHAPES)==len(accepted['named_layouts'])==28,'28 shapes')
    catalogue=[]
    for i,(observed,(storage,work,why)) in enumerate(zip(accepted['named_layouts'],contract.SHAPES),1):
        related=sorted(set(storage)|{key for key,ids in contract.EXTRA_RELATED.items() if i in ids})
        catalogue.append({'id':f'L{i:02d}',**observed,'unit':'inline representation bytes; alignment bytes',
            'primary_storage_obligations':storage,'related_storage_obligations':related,'work_context_obligations':work,
            'meaning':why,'numeric_charge_bytes':None,'runtime_work_price':None,
            'observation_scope':'Exact accepted target/compiler/source/cfg shape only; no allocation, capacity or simultaneous peak.'})
    catalogue.append({'id':'L29','type':'actual run_one_admitted_fixture_v1 dispatch closure',
        'size':accepted['actual_closure']['size'],'align':accepted['actual_closure']['align'],'unit':'inline representation bytes; alignment bytes',
        'primary_storage_obligations':['S06'],'related_storage_obligations':['S01','S05','S06','S10','S11','S12'],
        'work_context_obligations':['W07','W10'],'meaning':'Actual fixture-by-value/attempt-by-value/expected-shared-reference closure; observed directly, not a capture sum.',
        'numeric_charge_bytes':None,'runtime_work_price':None,'observation_scope':'Exact anonymous dispatch closure only; no caller/callee overlap or pointee backing.'})
    lookup={normalized_type(r['type']):r['id'] for r in catalogue[:28]};need(len(lookup)==28,'unique normalized shapes')
    all_roles=roles(inventory);closure_type=None
    dispatch=[r for r in all_roles if r['function_selector']=='run_one_admitted_fixture_v1::{closure#0}' and r['kind']=='argument']
    need(len(dispatch)==1,'one dispatch closure argument');closure_type=dispatch[0]['type_spelling']
    expression=query['diagnostics']['actual_closure']['expression'];cache=SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    text=expression['source_text'].encode();need(cache.read_bytes().count(text)==1 and sha(text)==expression['source_sha256'],'original exact closure expression')
    diagnostic=Path(query['diagnostics']['actual_closure']['file']).read_bytes()
    need(diagnostic[expression['byte_start']:expression['byte_end']]==text,'diagnostic exact same closure expression')
    for role in all_roles:
        binding=lookup.get(normalized_type(role['type_spelling']))
        if role['type_spelling']==closure_type and role['function_selector'] in ['run_one_admitted_fixture_v1','run_one_admitted_fixture_v1::{closure#0}']:binding='L29'
        role.update({'layout_id':binding,'binding_scope':'finite qualifier/lifetime-erased exact shape' if binding and binding!='L29' else 'exact original dispatch expression and capture item' if binding else 'no exact layout in this frontier',
            'physical_storage_region_id':None,'lifetime_interval':None,'incremental_charge_bytes':None,'runtime_work_price':None})
    counts=Counter(r['layout_id'] or 'UNBOUND' for r in all_roles)
    for layout in catalogue:
        matching=[r for r in all_roles if r['layout_id']==layout['id']]
        layout['matching_inventory_place_ids']=[r['id'] for r in matching]
        layout['matching_place_count_is_coverage_not_charge']=len(matching)
        layout['matched_context_obligation_union']=sorted({ob for r in matching for ob in r['function_obligations']})
    obligation_rows=[]
    for old in inventory['obligations']:
        key=old['id'];related=[r['id'] for r in catalogue if key in (r['related_storage_obligations'] if key.startswith('S') else r['work_context_obligations'])]
        fs=[f for f in inventory['functions_and_constructor_occurrences'] if key in f['obligations']]
        obligation_rows.append({'id':key,'original_inventory_obligation':old,'related_layout_ids':related,
            'source_function_or_constructor_selectors':[f['selector'] for f in fs],
            'status':'OPEN_FOR_INCREMENTAL_ACCOUNTING','numeric_storage_charge_proposed_closed':False,
            'work_price':None,'storage_charge_bytes':None,
            'newly_resolved_representation_scope':'Exact actual closure shape48/align8 only' if key=='S06' else 'Only the related listed concrete shapes' if key.startswith('S') and related else 'No work price or new backing/capacity bound',
            'remaining_evidence':contract.MISSING[key] if key.startswith('S') else old['required_positive_obligation']+' Complete action/callee/stdlib/drop/unwind cost basis and dynamic multiplicity remain unpriced; layout widths are not work prices.'})
    by_id={r['id']:r for r in catalogue};diffs=[]
    for key,left,right,meaning in contract.DIFFERENCES:
        l,r=by_id[f'L{left:02d}'],by_id[f'L{right:02d}']
        diffs.append({'id':key,'left_layout':l['id'],'right_layout':r['id'],'arithmetic':f"{l['size']} - {r['size']} = {l['size']-r['size']}",
            'difference_bytes':l['size']-r['size'],'meaning':meaning,'unit':'bytes of observed whole-type size difference',
            'is_price_or_baseline_version_delta':False,'numeric_charge_bytes':None,'work_price':None})
    return {'catalogue':catalogue,'place_join':{'roles':all_roles,'counts':{'arguments':65,'locals_returns':580,'total_roles':645,'named_shape_roles':sum(v for k,v in counts.items() if k not in ['L29','UNBOUND']),'actual_closure_roles':counts['L29'],'unbound_roles':counts['UNBOUND']},
        'alias_rule':'Only exact finite qualifier aliases and lifetime erasure. No generic substitution or applying aggregate layout to a borrow. All roles remain uncharged; no sum is a peak.',
        'finite_qualifier_aliases':PREFIXES,'closure_expression_pin':expression},'obligations':obligation_rows,'differences':diffs}

def main():
    start=time.monotonic();need(not (D/'seal.json').exists(),'already frozen')
    accepted_packet=decode(A.read_bytes());accepted=accepted_packet['acceptance'];inventory=decode((I/'delta-inventory.json').read_bytes());query=decode((V3/'plan.json').read_bytes())
    need(hashed(A)['sha256']=='5bbed125873c4082ac0d7f62f9e1ee575ff67a96bfd27fe6eadee0a5ff83b9a8','exact root layout receipt')
    need(accepted['status']=='accepted-retrospective-source-tool-target-bound-diagnostic-layout-observations' and accepted['original_contract_accepted'] is False,'retrospective accepted scope')
    need(accepted['source146_tree']==inventory['candidate_source146_tree']=='91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f','same source tree')
    paths={A,I/'delta-inventory.json',I/'contract.py',I/'README.md',I/'seal.json',V3/'plan.json',
        R/'verification/swift-root-bound-work-storage-delta-independent/seal.json',R/'verification/swift-root-bound-work-storage-delta-independent/REVIEW.md',
        R/'verification/swift-semantic-adapter-root-review/root-bound-work-storage-delta-acceptance.json',
        R/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json'}
    for field in ['candidate','offline_receipt','independent_terminal_seal','independent_observation','independent_terminal_review','warning_provenance_seal','amendment_plan','amendment_seal','root_release','historical_query_plan','historical_query_receipt']:
        paths.add(pin(accepted[field]))
    for rel in ['src/experimental_swift_reactor/retained_profile_loader_v1.rs','src/experimental_swift_reactor/cache/initial_profile_v1.rs','src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs']:paths.add(SOURCE/rel)
    paths.add(Path(query['diagnostics']['actual_closure']['file']))
    candidate=decode(pin(accepted['candidate']).read_bytes());independent=decode(pin(accepted['independent_observation']).read_bytes())
    need(candidate['named_layout_candidates']==independent['named_layouts']==accepted['named_layouts'],'three-way named observations')
    need(candidate['actual_closure_candidate']==independent['actual_closure']==accepted['actual_closure'],'three-way closure observation')
    need(accepted['actual_closure']=={'size':48,'align':8,'source_bits':384,'wrapper_bits':448},'actual closure literal')
    for packet,expected,count in [(I,'1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29',25),(R/'verification/swift-root-bound-work-storage-delta-independent','addd2beb80ae25174c210563bffc9122cbe655f69420170ad16305eaeef544ec',41)]:
        need(hashed(packet/'seal.json')['sha256']==expected,'accepted inventory seal')
        seal=decode((packet/'seal.json').read_bytes());need(len(seal['members'])==count,'inventory membership count')
        for member in seal['members']:paths.add(pin(member,packet))
    manifest=decode((R/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json').read_bytes())
    need(manifest['tree_sha256']==accepted['source146_tree'],'used source manifest')
    for member in manifest['members']:
        p=SOURCE/member['path']
        if p in paths:pin(member,SOURCE)
    data=make(inventory,accepted,query)
    put('input-manifest.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':[row(p) for p in sorted(paths)],
        'root_layout_acceptance':row(A),'root_inventory_acceptance':row(R/'verification/swift-semantic-adapter-root-review/root-bound-work-storage-delta-acceptance.json'),
        'source146_tree':accepted['source146_tree'],'diagnostic146_tree':accepted['diagnostic146_tree'],'python':{'version':sys.version,'tool':row(Path(sys.executable).resolve())},
        'compiler_target_cfg_provenance':{'toolchain_version_from_frozen_query_plan':query['toolchain_version'],'argv':query['argv'],'environment':query['environment']},
        'scope':'Rehash used immutable inputs, full two inventory packet members and four used source files; no source/MIR/compiler/oracle/runtime replay. Central metadata references inside root receipt are historical and not requalified here.'})
    put('layout-crosswalk.json',{'schema':1,'root_layout_observations_accepted':True,'accounting_join_accepted':False,'catalogue':data['catalogue']})
    put('inventory-place-join.json',data['place_join'])
    put('obligation-dispositions.json',{'schema':1,'work_obligations':12,'storage_obligations':12,'fully_closed_storage_charge_obligations':0,'obligations':data['obligations']})
    put('representation-differences.json',{'schema':1,'differences':data['differences'],'pair_composition_identity':'24 + 32 = 56 bytes inside the observed scope tuple; charge tuple OR included members, never both.',
        'closure_arithmetic':'384/8 = 48 bytes;448/8 = 56 bytes wrapper;56 - 48 = 8-byte alignment.56 is the diagnostic alignment wrapper, not another runtime closure allocation.',
        'all_values_are_static_representations_not_prices':True})
    put('prospective-controls.json',{'schema':1,'status':'REQUIRED_FOR_LATER_ACCOUNTING_ACCEPTANCE_NOT_EXECUTED_RUNTIME_CONTROLS','controls':[{'id':i,'requirement':text} for i,text in contract.PROSPECTIVE]})
    put('next-contract.json',{'schema':1,'status':'SOURCE_ONLY_MINIMUM_INCREMENTAL_CONTRACT_PROPOSAL','select_storage_grant':False,'select_work_prices':False,
        'numeric_leaves':[{'layout':'L29','size_bytes':48,'align_bytes':8,'use':'single actual dispatch closure representation only'},
            {'layout':'L25','size_bytes':13640,'align_bytes':8,'use':'single complete returned child owner representation only'},
            {'layout':'L20','size_bytes':56,'align_bytes':8,'use':'single complete scope pair representation only'},
            {'layout':'L19','size_bytes':16,'align_bytes':8,'use':'single primary shared-view representation only'},
            {'layout':'L28','size_bytes':8,'align_bytes':8,'use':'single Option<&admitted> shared-view representation only'}],
        'next_slice':'Bind the dispatch closure, complete returned child and destruction boundary to explicit physical storage regions and normal/refusal/unwind live intervals; retain all unobserved callee/parent/token and carried backing inputs. This is a representation/lifetime contract before a charge selection.',
        'events':['scope pair produced and original acquisition charge sticky','attempt/fixture move into actual closure; expected remains borrowed','dispatch call and complete admitted child return','shared inspection while complete child remains live','complete child destruction/cleanup and child-only token returned to separately provisioned P0','child-only release; original acquisition charge remains retained'],
        'storage_expression':'B_peak >= max_t(bytes(union of proven live physical inline regions at t) + unique separately retained backing capacities at t + independently provisioned parent/token regions). No numeric bound until every term and overlap is established.',
        'aliasing_rules':['Nested field extents are contained in their complete aggregate, not added as new allocations.','Same owned payload moved between places does not prove physical slot overlap or new allocation.','Alternative enum arms are not summed; call/return and cleanup overlaps require evidence.','Shared backing is charged once to its complete live ownership set through final destruction; borrowed views retain distinct representation only.','Unknown backing capacities or live regions refuse admission, never default to zero.'],
        'arithmetic':'Use checked finite integer byte arithmetic; account for full selected storage-region capacity/alignment/padding. Work units/prices remain independently selected later.',
        'not_qualified':['physical stack/peak','allocator or File/OS backing capacities','durable forgotten-root funding','dynamic work/drop/std-library prices','useful joint retirement/root shutdown','native/runtime/FieldLog/OTA/GA']})
    put('build-receipt.json',{'schema':1,'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],
        'python':sys.version,'python_tool':row(Path(sys.executable).resolve()),'source_scripts':[row(D/'build.py'),row(D/'contract.py')],
        'source146_tree':accepted['source146_tree'],'input_manifest_sha256':sha((D/'input-manifest.json').read_bytes()),'elapsed_seconds':time.monotonic()-start,
        'limits':{'wall_seconds':55,'compiler_invocations':0,'runtime_or_child_workloads':0,'global_process_inventory':False},'scope':'Source-only accounting join; no parser replay or product code execution.'})
    print(json.dumps({'status':'source-only-accounting-join-prepared','catalogue_shapes':29,**data['place_join']['counts'],'fully_closed_storage_charge_obligations':0,'compiler_runtime_children':0}))
if __name__=='__main__':main()
