"""Strict conditional arithmetic for declared inputs, never receipt authority.

Real identities, path correspondence, capacities, unit coverage and funding
must be selected independently by root. This evaluator cannot select them.
"""
from dataclasses import dataclass
import hashlib, importlib.util, json, sys
from pathlib import Path
U64=(1<<64)-1
TREE='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
OLD_TREE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
IDENTITIES=('source','build','session','executable','compiler','compiler_version','compile_manifest','compile_argv','compile_environment','process_argv','process_environment','review')
BUDGET_FIELDS=('source_bytes','metadata_bytes','cache_bytes','cache_entry_bytes','cache_entries','active_pins','cache_work','frames','values','controls','memory_pages','state_bytes','combined_bytes','instruction_fuel','execution_work','host_calls','deadline_ms')
WORK_TERMS={'L_str':67424,'P0_dynamic_backing':1,'P0_fixture_binding':1,'P0_root_route':1,'native_error_request':1,**{'native_open_request_'+str(i):1 for i in range(5)}}
HERE=Path(__file__).resolve().parent
class Refused(ValueError):pass
def natural(x):
    if type(x) is not int or x<0 or x>U64:raise Refused('not-u64')
    return x
def positive(x):
    natural(x)
    if not x:raise Refused('missing-positive-obligation')
    return x
def add(*xs):
    n=0
    for x in xs:
        natural(x)
        if x>U64-n:raise Refused('addition-overflow')
        n+=x
    return n
def mul(a,b):
    natural(a);natural(b)
    if a and b>U64//a:raise Refused('multiplication-overflow')
    return a*b
def digest(b):return hashlib.sha256(b).hexdigest()
def hex_digest(s):
    if type(s) is not str or len(s)!=64 or any(c not in '0123456789abcdef' for c in s):raise Refused('digest-required')
    return s
@dataclass(frozen=True)
class Bound:
    value:int
    obligation:str
    source_tree:str
    evidence_sha256:str
    unit:str='bytes'
    def checked(self,tree=TREE,unit='bytes'):
        positive(self.value)
        if type(self.obligation) is not str or not self.obligation.strip():raise Refused('named-obligation-required')
        if self.source_tree!=tree:raise Refused('wrong-bound-source')
        if self.unit!=unit:raise Refused('wrong-bound-unit')
        hex_digest(self.evidence_sha256)
        return self.value
def bound(x,unit='bytes'):
    if type(x) is not Bound:raise Refused('typed-byte-or-work-bound-required')
    return x.checked(unit=unit)
@dataclass(frozen=True)
class Identity:
    name:str
    preimage:bytes
    sha256:str
    backing:Bound
    def checked(self):
        if self.name not in IDENTITIES or type(self.preimage) is not bytes or not self.preimage:raise Refused('all-full-identity-preimages-required')
        if digest(self.preimage)!=hex_digest(self.sha256):raise Refused('identity-preimage-mismatch')
        b=bound(self.backing)
        if b<len(self.preimage):raise Refused('identity-backing-does-not-cover-preimage')
        return b
@dataclass(frozen=True)
class PathInput:
    native_body:bytes
    retained_byte_preimage:bytes
    native_backing:Bound
    byte_preimage_backing:Bound
    open_temporary:Bound
    correspondence_sha256:str
    def checked(self):
        if type(self.native_body) is not bytes or not self.native_body or type(self.retained_byte_preimage) is not bytes:raise Refused('actual-native-and-byte-path-preimages-required')
        if self.native_body!=self.retained_byte_preimage:raise Refused('native-path-byte-correspondence')
        hex_digest(self.correspondence_sha256)
        native=bound(self.native_backing);byte=bound(self.byte_preimage_backing);temp=bound(self.open_temporary)
        if native<len(self.native_body) or byte<len(self.retained_byte_preimage):raise Refused('path-backing-omission')
        if temp<add(len(self.native_body),1):raise Refused('path-open-temporary-omits-terminator')
        # Equal content is never proof of shared allocation; charge both.
        return native,byte,temp
@dataclass(frozen=True)
class BindingInput:
    source_tree:str
    identities:tuple
    paths:tuple
    claims:tuple
    product_budget:dict
    binding_review_sha256:str
    future_root_inline:Bound
    future_root_owned_backing:Bound
    immutable_diagnostic_backing:Bound
    loader_native_temporaries:Bound
    executable_open_temporary:Bound
    file_resource_backing_each:Bound
    error_backing_each:Bound
    error_owner_count:Bound
    all_payload_destructor_temporaries:Bound
def check_inputs(v):
    if type(v) is not BindingInput or v.source_tree!=TREE:raise Refused('typed-exact-candidate-binding-required')
    if type(v.identities) is not tuple or len(v.identities)!=12 or any(type(x) is not Identity for x in v.identities):raise Refused('exact-twelve-identities-required')
    names=[x.name for x in v.identities]
    if tuple(names)!=IDENTITIES:raise Refused('identity-order-or-duplicate')
    identities={x.name:x for x in v.identities};identity_backing=add(*(x.checked() for x in v.identities))
    source=identities['source'].preimage
    if len(source)!=1947 or digest(source)!='9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806':raise Refused('selected-source-constraint')
    sizes={n:len(identities[n].preimage) for n in ('source','build','session','executable')}
    if sizes['build']>128*1024 or sizes['session']>64*1024 or sizes['executable']>64*1024**2:raise Refused('file-geometry-exceeds-original-cap')
    if type(v.paths) is not tuple or len(v.paths)!=5 or any(type(x) is not PathInput for x in v.paths):raise Refused('all-five-distinct-path-positions-required')
    paths=[x.checked() for x in v.paths]
    if type(v.claims) is not tuple or len(v.claims)!=8 or any(type(x) is not bytes or len(x)!=32 for x in v.claims):raise Refused('all-eight-original-unverified-claims-required')
    if type(v.product_budget) is not dict or set(v.product_budget)!=set(BUDGET_FIELDS):raise Refused('all17-product-fields-explicit-required')
    for value in v.product_budget.values():positive(value)
    if v.product_budget['execution_work']!=1_000_000_000 or v.product_budget['combined_bytes']!=268435456:raise Refused('changed-selected-product-constraint')
    hex_digest(v.binding_review_sha256)
    for field in ('future_root_inline','future_root_owned_backing','immutable_diagnostic_backing','loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','all_payload_destructor_temporaries'):bound(getattr(v,field))
    bound(v.error_owner_count,'count')
    minima={'loader_native_temporaries':8572,'executable_open_temporary':4097,'file_resource_backing_each':73,'error_backing_each':32,'error_owner_count':396924,'all_payload_destructor_temporaries':29394}
    if any(getattr(v,k).value<n for k,n in minima.items()):raise Refused('omits-inherited-positive-native-owner-or-destructor-operand-envelope')
    return identities,identity_backing,paths,sizes
def old_storage_module():
    p=HERE.parent/'swift-guarded-snapshot-host-storage-composition/model.py'
    spec=importlib.util.spec_from_file_location('outer_inherited_storage',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
def storage(v):
    ids,identity_backing,paths,sizes=check_inputs(v);M=old_storage_module()
    old=lambda value,name:M.Bound(value,name+'; explicitly supplied candidate obligation, source-rebound through unchanged-body proof')
    immutable=add(identity_backing,*(p[1] for p in paths),v.immutable_diagnostic_backing.value)
    old_input=M.RequiredStorage(OLD_TREE,HOST,
        tuple(M.PathBacking(old(len(p.native_body),'actual native path length'),old(paths[i][0],'actual native path backing'),old(paths[i][2],'native open temporary')) for i,p in enumerate(v.paths)),
        old(add(56414,80,v.future_root_inline.value),'all130 new roles plus external result and future launcher'),
        old(v.future_root_owned_backing.value,'future upstream P0 owner'),old(1168,'full measured immutable binding including12 identity records and5 byte headers'),old(immutable,'actual12identity backing +5separatebyte backing + original diagnostic backing'),
        M.OriginalValidationBudget(old(1947,'selected source bytes'),old(1_000_000,'selected metadata bytes'),old(65536,'selected scratch bytes')),
        old(sizes['source'],'source'),old(sizes['executable'],'executable'),old(sizes['build'],'build'),old(sizes['session'],'session'),
        old(v.loader_native_temporaries.value,'loader'),old(v.executable_open_temporary.value,'executable open'),old(v.file_resource_backing_each.value,'File resource'),old(v.error_backing_each.value,'original Error backing'),M.CountBound(v.error_owner_count.value,'all original owner counts unchanged; borrowed view creates zero new Error owners'),old(v.all_payload_destructor_temporaries.value,'uniform full transitive destructor envelope'))
    inv=json.loads((HERE.parent/'swift-guarded-snapshot-host-storage-composition/inline-inventory.json').read_bytes())
    result=M.evaluate(inv,old_input)
    expected=add(292037,v.future_root_inline.value,v.future_root_owned_backing.value,immutable,*(p[0] for p in paths))
    if result['P0_preexisting_required_before_policy_quote_account_entry']!=expected:raise Refused('P0-rebind-double-count-or-omission')
    return {'schema':1,'candidate_source_tree':TREE,'inherited_source_tree':OLD_TREE,'P0_preexisting':expected,'inherited_six_child_storage_parts':result['six_child_storage_parts'],'inherited_child_prepaid':result['child_prepaid_storage'],'whole_external_storage':result['whole_external_storage'],
        'fixed_inline_owners':292037,'identity_preimage_backing':identity_backing,'five_native_Path_pointee_backing':add(*(p[0] for p in paths)),'five_separate_retained_byte_body_backing':add(*(p[1] for p in paths)),
        'all_original_diagnostic_and_file_owner_lifetimes_preserved':True,'all_new_roles_and_immutable_inputs_P0_before_policy_quote_account_entry':True,
        'normal_token_release_only_after_original_payload_and_carrier_destruction_return':True,'none_refusal_unwind_refund':False,'P0_survives_result_consumption':True,
        'binding_reviewed_or_accepted':False,'actual_fixture_or_root_policy_selected':False,'healthy_cleanup_native_OTA_GA':False,'arithmetic_only_not_receipt_validator':True,
        'self_embedding_or_static_provider_proven':False}
def work(terms):
    if type(terms) is not dict or set(terms)!=set(WORK_TERMS):raise Refused('exact-residual-work-scope-required')
    result=895084428325956794
    for name,coefficient in WORK_TERMS.items():result=add(result,mul(coefficient,bound(terms[name],'work')))
    return {'whole_work':result,'conditional_fixed':895084428325956794,'new_outer_work_once':2706170,'inherited_account_once_at_conditional_I1_U3':2825436,'L_str5080_selected':False,'accepted_bound':False,'operational_grant':False}
class Retirement:
    """Finite route guard model; no product owner or account is constructed."""
    def __init__(self):self.p0=False;self.held=False;self.owned=False;self.view=False;self.destroyed=False;self.token=False;self.aborted=False;self.result=False;self.entered=False;self.inspections=0
    def provision_p0(self):self.p0=True
    def enter(self):
        if not self.p0 or self.held or self.aborted or self.entered:raise Refused('P0-and-affine-entry-required')
        self.held=True;self.owned=True;self.entered=True
    def borrow(self):
        if not self.owned or self.view or self.aborted or self.inspections:raise Refused('one-live-original-owner-required')
        self.view=True;self.inspections+=1
    def end_view(self):
        if not self.view:raise Refused('no-live-view')
        self.view=False
    def destroy(self,route):
        if route not in ('some','none','unwind') or not self.owned or self.view or self.aborted:raise Refused('view-must-end-before-affine-destruction')
        self.owned=False
        if route=='some':self.destroyed=True;self.token=True
        elif route=='unwind':self.aborted=True
    def release(self):
        if not self.p0 or not self.destroyed or not self.token or self.aborted:raise Refused('actual-returned-token-required')
        self.token=False;self.held=False
    def unwind(self):self.aborted=True;return self.held
    def final_result(self):
        if not self.p0 or self.view:raise Refused('P0-owned-finite-result-required')
        self.result=True
    def consume_result(self):
        if not self.result or not self.p0:raise Refused('P0-through-result-consumption-required')
        self.result=False
