"""Conditional host arithmetic, never price authority, identity or execution proof."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import hashlib, importlib.util, json, sys
from ledger import COUNTS, FRONTIERS, closure_frontiers
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TREE='acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
TARGET='aarch64-apple-darwin'
COMPILER='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
U64=(1<<64)-1
class Refused(ValueError):pass
def need(x,why):
    if not x:raise Refused(why)
def nat(x):need(type(x)is int and 0<=x<=U64,'not-u64');return x
def pos(x):nat(x);need(x>0,'positive-unresolved-frontier-required');return x
def add(*xs):
    n=0
    for x in xs:nat(x);need(x<=U64-n,'addition-overflow');n+=x
    return n
def mul(a,b):nat(a);nat(b);need(not a or b<=U64//a,'multiplication-overflow');return a*b
def hex64(s):need(type(s)is str and len(s)==64 and all(c in '0123456789abcdef' for c in s),'evidence-digest-required');return s
def sha(b):return hashlib.sha256(b).hexdigest()
def sealed_input(path):
    lock=json.loads((HERE/'input-lock.json').read_bytes());name=path.relative_to(ROOT).as_posix()
    found=[x for x in lock['files'] if x['path']==name];need(len(found)==1,'exact retained input membership')
    b=path.read_bytes();need((len(b),sha(b))==(found[0]['bytes'],found[0]['sha256']),'retained input drift');return b
@lru_cache(maxsize=1)
def provider():
    p=ROOT/'verification/swift-guarded-snapshot-owned-provider-work-storage/model.py';sealed_input(p)
    s=importlib.util.spec_from_file_location('callee_frozen_provider_model',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def validate_proposal(p):
    need(p['source_tree_sha256']==TREE and p['compiler_sha256']==COMPILER and p['target']==TARGET,'exact source/compiler/target proposal')
    need(p['counts']==COUNTS and p['positive_residual_contracts']==FRONTIERS,'exact14 interfaces and4 positive composite frontier contracts')
    need(p['all10_inherited_terms']==provider().INHERITED_WORK and p['prior_conditional_whole_fixed']==895084428326233374,'all10 original work terms and fixed caller remain intact')
    need(p['provider_source_work_unchanged']=={'fixed':276580,'input_operand_bytes':1324} and p['provider_slots_unchanged']==9696 and p['authored_callback_body_cap_inherited']==5 and p['authored_callback_adapter_calls']==5 and p['authored_callback_body_new_charge']==0,'immutable caller/callback conservation')
    import derive as D
    need(p==expected_proposal(), 'exact corrected shell, phases, storage and typed source obligations')
    return p
@lru_cache(maxsize=1)
def expected_proposal():
    import derive as D
    return D.derive()['proposal.json']
def proposal():return validate_proposal(json.loads((HERE/'proposal.json').read_bytes()))
@dataclass(frozen=True)
class ResidualBound:
    value:int
    unit:str
    frontier:str
    occurrence:int
    source_tree:str
    target:str
    compiler_sha256:str
    native_target:str
    argument_types:tuple
    return_type:str
    body_lengths:tuple
    evidence_sha256:str
    obligation:str
    source_contract_sha256:str
    invocation_context:tuple
def contexts(value):
    M=provider()
    try:shape=M.describe(value)
    except M.Refused as error:raise Refused('provider-input:'+str(error)) from error
    x=[{'frontier':'DIGEST_MEMCMP_FRONTIER','occurrence':0,'body_lengths':(32,32)}]
    x += [{'frontier':'PATH_MEMCMP_FRONTIER','occurrence':i,'body_lengths':(shape['native_path_bytes'][i],shape['separately_retained_path_bytes'][i])} for i in range(5)]
    x += [{'frontier':'CONTAINS_RESIDUAL_FRONTIER','occurrence':i,'body_lengths':(shape['native_path_bytes'][i],)} for i in range(5)]
    x += [{'frontier':'RANGE_NEXT_SOURCE_CLOSURE_FRONTIER','occurrence':s['occurrence'],'body_lengths':(),'invocation_context':(s['loop'],s['limit'],s['header_index'])} for s in closure_frontiers()['range_next']['conservative_schedule']]
    return shape,x
def residuals(value,items,unit):
    need(type(items)is tuple,'immutable-residual-roster-required');_,expected=contexts(value);p=proposal()
    need(len(items)==30,'exact1plus5plus5plus19-frontier-contexts-required')
    result=0
    for item,context in zip(items,expected):
        need(type(item)is ResidualBound,'typed-exact-residual-bound-required');pos(item.value)
        need(item.unit==unit and unit in ('work','bytes'),'exact-frontier-unit-required')
        need(item.source_tree==TREE and item.target==TARGET and item.compiler_sha256==COMPILER,'exact-frontier-source-compiler-target')
        need(item.frontier==context['frontier'] and type(item.occurrence)is int and item.occurrence==context['occurrence'],'exact-frontier-identity-order-count')
        need(type(item.body_lengths)is tuple and all(type(x)is int for x in item.body_lengths) and item.body_lengths==context['body_lengths'],'actual-length-aware-frontier-no-selected-max')
        need(item.source_contract_sha256==p['source_closure_frontiers_sha256'],'exact full R1-R3 source obligation contract digest')
        need(type(item.invocation_context)is tuple and item.invocation_context==context.get('invocation_context',()) and all(type(a)is type(b) for a,b in zip(item.invocation_context,context.get('invocation_context',()))),'exact immutable loop/header context required')
        spec=p['positive_residual_contracts'][item.frontier]
        need(item.native_target==spec['native_target'] and type(item.argument_types)is tuple and item.argument_types==tuple(spec['argument_types']) and item.return_type==spec['return_type'],'exact-frontier-target-type-arity-return')
        hex64(item.evidence_sha256);need(type(item.obligation)is str and bool(item.obligation.strip()),'reviewed-composed-callee-obligation-required')
        result=add(result,item.value)
    return result
def base_bound(item,unit):
    M=provider()
    try:return M.bound(item,unit)
    except M.Refused as error:raise Refused('inherited-bound:'+str(error)) from error
def polynomial(p,b):return add(p['fixed'],mul(p['B'],b),mul(p['B2'],mul(b,b)))
def evaluate(value,inherited_work,frontier_work,frontier_storage,acquisition_work,future_caller_work,*,outcome='normal'):
    need(outcome in ('normal','refusal','unwind'),'known-conservative-outcome-required')
    M=provider();p=proposal();shape,_=contexts(value)
    try:base_storage=M.storage(value)
    except M.Refused as error:raise Refused('mandatory-inherited-backing-storage:'+str(error)) from error
    need(type(inherited_work)is dict and set(inherited_work)==set(p['all10_inherited_terms']),'exact10-original-residual-terms-required')
    old_work=add(*(mul(coefficient,base_bound(inherited_work[key],'work')) for key,coefficient in p['all10_inherited_terms'].items()))
    fw=residuals(value,frontier_work,'work');fs=residuals(value,frontier_storage,'bytes')
    b=shape['input_operand_bytes'];shell=polynomial(p['callee_source_shell_work'],b)
    provider_work=add(276580,mul(1324,b))
    total=add(p['prior_conditional_whole_fixed'],mul(1324,b),shell,old_work,fw,base_bound(acquisition_work,'work'),base_bound(future_caller_work,'work'))
    storage_add=add(p['additional_total_slots'],fs)
    return {'schema':1,'whole_conditional_work':total,'provider_source_work_unchanged':provider_work,'new_callee_source_native_shell':shell,'positive_unresolved_frontier_work':fw,'positive_unresolved_frontier_storage':fs,'B_from_all22_actual_bodies':b,'all10_original_residual_work':old_work,'source_ledger_and_native_ABI_slot_addition':p['additional_total_slots'],'P0_preexisting':add(base_storage['P0_preexisting'],storage_add),'whole_external_storage':add(base_storage['whole_external_storage'],storage_add),'all15_phases_hold_new_storage':True,'inherited_six_child_storage_parts':base_storage['inherited_six_child_storage_parts'],'inherited_child_prepaid':base_storage['inherited_child_prepaid'],'original_binding1168_preserved':True,'all12plus5plus5_backing_and_diagnostics_upstream_preserved':True,'all_original_destructor_error_and_native_operand_obligations_preserved':True,'outcome':outcome,'None_refusal_unwind_refund':False,'normal_release_requires_actual_original_payload_carrier_destruction_Some_token':True,'authored_callback_body_cap_inherited':5,'authored_callback_adapter_cap':5,'authored_callback_body_charge_added_again':False,'all_six_upstream':'Pending','all_three_selectors':'Pending','L_str_selected':False,'frontier_prices_selected':False,'actual_acquisition_authenticated_owner_or_root_funding':False,'accepted_bound':False,'operational_grant':False,'native_FieldLog_OTA_GA':False}
