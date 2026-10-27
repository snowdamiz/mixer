"""Pure host conditional arithmetic; this module cannot construct authority.

describe() models exactly the Rust shape checks, including its intentional lack
of digest/authenticated-owner checks. storage()/work() additionally require the
inherited independently described input conditions. Neither selects those facts.
"""
from dataclasses import dataclass, fields
from pathlib import Path
import hashlib, importlib.util, json, sys
from functools import lru_cache
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TREE = 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
OLD_TREE = '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
U64 = (1 << 64)-1
SOURCE_SHA256 = '9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806'
IDENTITIES = ('source','build','session','executable','compiler','compiler_version','compile_manifest','compile_argv','compile_environment','process_argv','process_environment','review')
BUDGET_FIELDS = ('source_bytes','metadata_bytes','cache_bytes','cache_entry_bytes','cache_entries','active_pins','cache_work','frames','values','controls','memory_pages','state_bytes','combined_bytes','instruction_fuel','execution_work','host_calls','deadline_ms')
UPSTREAM = ('acquisition_work','acquisition_inline_and_temporary_storage','acquisition_owned_backing','provider_work_and_inline_storage','original_diagnostic_pointee_backing','admitted_owner_and_authenticated_correspondence')
INHERITED_WORK = {'L_str':67424,'P0_dynamic_backing':1,'P0_fixture_binding':1,'P0_root_route':1,'native_error_request':1,**{'native_open_request_'+str(i):1 for i in range(5)}}
class Refused(ValueError): pass
def need(ok, reason):
    if not ok: raise Refused(reason)
def natural(value):
    need(type(value) is int and 0 <= value <= U64, 'not-u64'); return value
def positive(value):
    natural(value); need(value > 0,'positive-obligation-required'); return value
def add(*values):
    result=0
    for value in values:
        natural(value); need(value <= U64-result,'addition-overflow'); result += value
    return result
def mul(a,b):
    natural(a); natural(b); need(not a or b <= U64//a,'multiplication-overflow'); return a*b
def digest(data): return hashlib.sha256(data).hexdigest()
def hex_digest(value):
    need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'digest-label-required'); return value
@dataclass(frozen=True)
class Bound:
    value: int
    obligation: str
    source_tree: str
    evidence_sha256: str
    unit: str = 'bytes'
def bound(value, unit='bytes'):
    need(type(value) is Bound,'typed-bound-required'); positive(value.value)
    need(value.source_tree == TREE,'exact-provider-source-bound-required')
    need(value.unit == unit,'wrong-bound-unit')
    need(type(value.obligation) is str and bool(value.obligation.strip()),'named-obligation-required'); hex_digest(value.evidence_sha256)
    return value.value
@dataclass(frozen=True)
class Identity:
    name: str
    preimage: bytes
    sha256: str
    backing: Bound
@dataclass(frozen=True)
class PathInput:
    native_body: bytes
    retained_byte_preimage: bytes
    native_backing: Bound
    byte_preimage_backing: Bound
    open_temporary: Bound
    correspondence_sha256: str
@dataclass(frozen=True)
class BindingInput:
    source_tree: str
    identities: tuple
    paths: tuple
    claims: tuple
    product_budget: dict
    binding_review_sha256: str
    future_root_inline: Bound
    future_root_owned_backing: Bound
    immutable_diagnostic_backing: Bound
    loader_native_temporaries: Bound
    executable_open_temporary: Bound
    file_resource_backing_each: Bound
    error_backing_each: Bound
    error_owner_count: Bound
    all_payload_destructor_temporaries: Bound
def describe(value, *, limit=U64):
    """Rust shape model only; digest labels remain unverified claims."""
    need(type(value) is BindingInput and value.source_tree == TREE,'exact-provider-input-required')
    need(type(value.identities) is tuple and len(value.identities)==12 and all(type(x) is Identity for x in value.identities),'exact12-identities-required')
    need(tuple(x.name for x in value.identities)==IDENTITIES,'exact-identity-order')
    positive(limit); total=0; identity_counts=[]
    for i,item in enumerate(value.identities):
        need(type(item.preimage) is bytes and item.preimage,'empty-or-mutable-identity-'+str(i))
        hex_digest(item.sha256)
        count=len(item.preimage); natural(count); need(count <= limit-total,'logical-backing-overflow'); total += count; identity_counts.append(count)
    need(identity_counts[0]==1947 and value.identities[0].sha256==SOURCE_SHA256,'selected-source-length-or-claim')
    need(type(value.paths) is tuple and len(value.paths)==5 and all(type(x) is PathInput for x in value.paths),'exact5-paths-required')
    native_counts=[]; retained_counts=[]
    for i,path in enumerate(value.paths):
        need(type(path.native_body) is bytes and type(path.retained_byte_preimage) is bytes,'immutable-path-bodies-required')
        need(path.native_body,'empty-native-path-'+str(i)); need(b'\0' not in path.native_body,'native-path-contains-NUL-'+str(i))
        need(path.native_body==path.retained_byte_preimage,'retained-path-mismatch-'+str(i))
        native=len(path.native_body); retained=len(path.retained_byte_preimage)
        for count in (native,retained):
            natural(count); need(count <= limit-total,'logical-backing-overflow'); total += count
        native_counts.append(native); retained_counts.append(retained)
    return {'status':'unqualified-shape-only-candidate','identity_bytes':tuple(identity_counts),'native_path_bytes':tuple(native_counts),'separately_retained_path_bytes':tuple(retained_counts),'logical_input_backing_bytes':total,'input_operand_bytes':max(identity_counts+native_counts+retained_counts),'upstream':{name:'Pending' for name in UPSTREAM},'selectors':{'binding':'Pending','root_policy':'Pending','whole_quote':'Pending'},'digest_validation_performed':False,'authenticated_owner':False,'accepted_bound':False,'operational_grant':False}
@lru_cache(maxsize=1)
def old_module():
    folder=ROOT/'verification/swift-guarded-snapshot-outer-parent-work-storage'
    seal=(folder/'seal.json').read_bytes(); need(digest(seal)=='7d7c6be167de0a7e20dbde2a50a5ea900a954a8e5e32262cf185411f1dc041b0','accepted-inherited-seal')
    data=(folder/'model.py').read_bytes(); member=next(r for r in json.loads(seal)['members'] if r['path']=='model.py')
    need((len(data),digest(data))==(member['bytes'],member['sha256']),'accepted-inherited-model-bytes')
    storage=ROOT/'verification/swift-guarded-snapshot-host-storage-composition';storage_seal=(storage/'seal.json').read_bytes()
    need(digest(storage_seal)=='ddbd969da4b25240fbc5883e8691905b1b6204fcca47a6a1a9ada4e6a41420a4','accepted-old-storage-composer-seal')
    for name in ('model.py','inline-inventory.json'):
        actual=(storage/name).read_bytes();expected=next(r for r in json.loads(storage_seal)['members'] if r['path']==name)
        need((len(actual),digest(actual))==(expected['bytes'],expected['sha256']),'accepted-old-storage-composer-member')
    spec=importlib.util.spec_from_file_location('provider_frozen_outer_model',folder/'model.py'); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
    return module
def old_input(value):
    """Explicit source-only transport, never rewrite the frozen old model."""
    describe(value); old=old_module()
    def convert(item, unit='bytes'):
        bound(item,unit)
        return old.Bound(item.value,item.obligation+'; conditional source-only6006-MIR rebind; no selected authority',OLD_TREE,item.evidence_sha256,item.unit)
    ids=tuple(old.Identity(x.name,x.preimage,x.sha256,convert(x.backing)) for x in value.identities)
    paths=tuple(old.PathInput(x.native_body,x.retained_byte_preimage,convert(x.native_backing),convert(x.byte_preimage_backing),convert(x.open_temporary),x.correspondence_sha256) for x in value.paths)
    kwargs={f.name:convert(getattr(value,f.name),'count' if f.name=='error_owner_count' else 'bytes') for f in fields(BindingInput) if f.name not in ('source_tree','identities','paths','claims','product_budget','binding_review_sha256')}
    result=old.BindingInput(OLD_TREE,ids,paths,value.claims,value.product_budget,value.binding_review_sha256,**kwargs)
    try: old.check_inputs(result)
    except old.Refused as error: raise Refused('inherited-input-condition:'+str(error)) from error
    return old,result
def candidate(): return json.loads((HERE/'candidate.json').read_bytes())
def storage(value):
    shape=describe(value); old, converted=old_input(value)
    try: inherited=old.storage(converted)
    except old.Refused as error: raise Refused('inherited-storage:'+str(error)) from error
    report=candidate(); extra=add(report['typed_inline_slots'],report['external_caller_result_slot'])
    preexisting=add(inherited['P0_preexisting'],extra)
    required=add(report['conditional_P0_fixed'],value.future_root_inline.value,value.future_root_owned_backing.value,value.immutable_diagnostic_backing.value,*(x.backing.value for x in value.identities),*(x.native_backing.value+x.byte_preimage_backing.value for x in value.paths))
    need(preexisting==required,'provider-P0-omission-or-double-charge')
    return {'schema':1,'source_tree':TREE,'P0_preexisting':preexisting,'provider_inline_slots':report['typed_inline_slots'],'provider_external_result':report['external_caller_result_slot'],'provider_total_addition':extra,'fixed_P0':report['conditional_P0_fixed'],'original_binding_inline':1168,'identity_preimage_backing':inherited['identity_preimage_backing'],'native_path_backing':inherited['five_native_Path_pointee_backing'],'separate_retained_path_backing':inherited['five_separate_retained_byte_body_backing'],'logical_length_descriptor_not_another_allocation':shape['logical_input_backing_bytes'],'inherited_six_child_storage_parts':inherited['inherited_six_child_storage_parts'],'inherited_child_prepaid':inherited['inherited_child_prepaid'],'whole_external_storage':add(inherited['whole_external_storage'],extra),'all_original_diagnostic_error_payload_carrier_destructor_terms_preserved':True,'future_root_inline_and_backing_still_positive':True,'None_refusal_unwind_refund':False,'P0_through_final_result_consumption':True,'upstream':shape['upstream'],'selectors':shape['selectors'],'actual_owner_or_funding_selected':False,'accepted_bound':False,'operational_grant':False}
def work(value, inherited_terms, new_std_terms, acquisition_work, future_caller_work):
    shape=describe(value); old,converted=old_input(value); report=candidate()
    need(type(inherited_terms) is dict and set(inherited_terms)==set(INHERITED_WORK),'exact10-inherited-work-terms-required')
    terms={name:old.Bound(bound(item,'work'),item.obligation+'; source-only rebind',OLD_TREE,item.evidence_sha256,'work') for name,item in inherited_terms.items()}
    try: inherited=old.work(terms)['whole_work']
    except old.Refused as error: raise Refused('inherited-work:'+str(error)) from error
    counts=report['new_required_std_interface_terms']; need(type(new_std_terms) is dict and set(new_std_terms)==set(counts),'all14-new-std-interface-prices-required')
    std=add(*(mul(counts[name],bound(new_std_terms[name],'work')) for name in counts))
    own=add(report['provider_source_work']['fixed'],mul(report['provider_source_work']['input_operand_bytes'],shape['input_operand_bytes']))
    result=add(inherited,own,std,bound(acquisition_work,'work'),bound(future_caller_work,'work'))
    return {'schema':1,'source_tree':TREE,'whole_work':result,'inherited_work_with_all10_terms':inherited,'provider_source_work':own,'dynamic_input_operand_bytes':shape['input_operand_bytes'],'new_std_interfaces':std,'actual_prepaid_acquisition_work':acquisition_work.value,'future_provider_caller_and_launcher_work':future_caller_work.value,'all6_upstream':shape['upstream'],'all3_selectors':shape['selectors'],'source_unit_only':True,'L_str_selected':False,'accepted_bound':False,'operational_grant':False,'runtime_or_native_or_GA':False}
