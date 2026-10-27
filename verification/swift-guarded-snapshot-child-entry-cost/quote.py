"""Pure symbolic child-entry candidate. No defaults, price selection or grant."""
from dataclasses import dataclass
from pathlib import Path
import json
D=Path(__file__).resolve().parent;U64=2**64-1
class Refused(ValueError):pass
def natural(v,positive=False):
    if type(v) is not int or v<0 or v>U64 or (positive and v==0):raise Refused('unpriced-or-invalid-u64')
    return v
def add(*values):
    out=0
    for v in values:
        natural(v)
        if out>U64-v:raise Refused('addition-overflow')
        out+=v
    return out
def mul(a,b):
    natural(a);natural(b)
    if a and b>U64//a:raise Refused('multiplication-overflow')
    return a*b
@dataclass(frozen=True)
class RequiredCuts:
    # Bounds, not actual measured path length or a selected policy. Each must be
    # bound to the immutable five actual paths by a later root review.
    path_bytes:tuple
    path_native_request_bytes:tuple
    p0_path_backing_bytes:tuple
    io_error_native_request_bytes:int
    retained_io_error_backing_bytes:int
    during_entry_payload_drop_work:int
    loader_payload_work:int
    leaf_payload_work:int
    returned_outcome_payload_drop_work:int
    def checked(self):
        for name in ('path_bytes','path_native_request_bytes','p0_path_backing_bytes'):
            values=getattr(self,name)
            if not isinstance(values,(tuple,list)) or len(values)!=5:raise Refused('five-explicit-path-bounds-required')
            for v in values:natural(v,True)
        for p,n,b in zip(self.path_bytes,self.path_native_request_bytes,self.p0_path_backing_bytes):
            if n<p or b<p:raise Refused('uncovered-path-extent')
        for name in ('io_error_native_request_bytes','retained_io_error_backing_bytes','during_entry_payload_drop_work','loader_payload_work','leaf_payload_work','returned_outcome_payload_drop_work'):natural(getattr(self,name),True)
        return self
def evaluate(cuts,ledger=None):
    cuts.checked()
    if ledger is None:ledger=json.loads((D/'ledger.json').read_text())
    expected={'setup_files_once_v1','copy_claims_v1','run_prepaid_fixture_v1','invoke_loaded_leaf_once_v1','cancellation_default','cancellation_clone'}
    nodes=ledger['functions']
    if set(nodes)!=expected or ledger['schema']!=1:raise Refused('unknown-function-or-ledger')
    seen=set()
    def expand(n,stack=()):
        if n not in nodes:raise Refused('unknown-authored-callee')
        if n in stack:raise Refused('unclassified-cycle')
        seen.add(n);r=nodes[n]
        if r['local_actions']!=add(2,*r['parts'].values()):raise Refused('omitted-source-transfer-or-control-part')
        repeat=6 if n=='setup_files_once_v1' else 1
        if r['repeat']!=repeat:raise Refused('setup-exhaustion-or-repeat-omitted')
        value=natural(r['local_actions'],True)
        for call in r['calls']:
            role=call['role']
            if role in nodes:value=add(value,expand(role,stack+(n,)))
            elif role not in ('primitive','native_open_cut','loader_payload_cut','leaf_payload_cut','primitive_with_observed_24B_allocation','primitive_no_new_allocation_observed'):raise Refused('unpriced-helper')
        return mul(repeat,value)
    core=expand(ledger['core_root'])
    if len(seen)!=6:raise Refused('authored-helper-omitted')
    if ledger['requested_Cancellation_allocation_bytes']!=24 or ledger['requested_Cancellation_allocation_alignment']!=8 or ledger['clone_additional_allocation_bytes']!=0:raise Refused('probe-bound-native-term-changed')
    if ledger['during_entry_drop_visit_bound']!=sum(d['repeat'] for d in ledger['drop_sites']):raise Refused('drop-visit-omission')
    during_drop=mul(ledger['during_entry_drop_visit_bound'],cuts.during_entry_payload_drop_work)
    native=add(24,*cuts.path_native_request_bytes,cuts.io_error_native_request_bytes)
    entry_shell=add(core,during_drop,native)
    external=add(cuts.loader_payload_work,cuts.leaf_payload_work,cuts.returned_outcome_payload_drop_work)
    return dict(schema=1,status='symbolic-producer-candidate-requires-independent-review-and-final-bindings',source146=True,
        core_source_work=core,setup_source_work=ledger['setup_source_work'],remaining_caller_argument_source_work=ledger['remaining_caller_and_argument_source_work'],
        native_requested_byte_allowance=native,during_entry_payload_drop_work=during_drop,entry_shell_work=entry_shell,
        separate_external_payload_work=dict(loader=cuts.loader_payload_work,leaf_P3_P4=cuts.leaf_payload_work,returned_P5=cuts.returned_outcome_payload_drop_work),
        arithmetic_sum_with_external_cuts=add(entry_shell,external),cuts=cuts.__dict__,
        storage_obligations=dict(p0_path_backing_bytes=cuts.p0_path_backing_bytes,Cancellation_requested_backing_bytes=24,Cancellation_alignment=8,retained_error_backing_bytes=cuts.retained_io_error_backing_bytes,inline188_role_inventory_bytes=76696,selected_lifetime_union=False),
        root_bindings_verified=False,complete_component_accepted=False,whole_quote=False,operational_grant=False,
        qualifications=['Native/path/error/destructor cuts are explicit required positive reviewed upper bounds, not prices proved by evaluating this arithmetic.',
        'Five source setup attempts plus sixth loop/exhaustion visit are covered; path lengths are not capped by this source.',
        'One fixed24-byte/align8 allocation request is qualified only for the exact1.99 Arc<AtomicBool> probe; no allocator overhead/RSS/CPU evidence.',
        'Loader146/P3/P4/P5 payload costs and final complete host policy remain separately required.'])
