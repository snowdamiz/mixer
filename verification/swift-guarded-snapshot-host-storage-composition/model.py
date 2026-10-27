"""Typed checked logical-storage composition; no authority or runtime dispatch.

Extent inputs are conservative source-bound upper bounds, not WORK prices.
Every unknown byte/count input is positive, finite, and accompanied by a named
review obligation. Synthetic evaluations do not discharge those obligations.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import Mapping
import hashlib,json
U64=(1<<64)-1
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
FROZEN_INLINE_INVENTORY_SHA256='fa432d8c2cfa35c0197451b15078bd177586bc873da5596daba76c26a7e9fe13'
PRODUCT_RETENTION=1899541
PRODUCT_C=79676
PRODUCT_S=941467
PRODUCT_A=430175
PRODUCT_H=81327
CANCELLATION_BACKING=24
INITIAL_CACHE_MAX_REQUESTED_BACKING=64*136+64*16+512*32+512*56+192
BINDING_DECLARED_FIELD_BYTES=5*16+256+40+136
class Refused(ValueError):pass

def natural(n):
 if type(n) is not int or n<0 or n>U64:raise Refused('not-u64')
 return n
def positive(n):
 natural(n)
 if not n:raise Refused('required-positive-bound')
 return n
def add(*values):
 result=0
 for v in values:
  natural(v)
  if v>U64-result:raise Refused('add-overflow')
  result+=v
 return result
def mul(a,b):
 natural(a);natural(b)
 if a and b>U64//a:raise Refused('multiply-overflow')
 return a*b

@dataclass(frozen=True)
class Bound:
 bytes:int
 evidence:str
 def checked(self):
  positive(self.bytes)
  if type(self.evidence) is not str or not self.evidence.strip():raise Refused('missing-source-bound-obligation')
  return self.bytes

@dataclass(frozen=True)
class CountBound:
 count:int
 evidence:str
 def checked(self):
  positive(self.count)
  if type(self.evidence) is not str or not self.evidence.strip():raise Refused('missing-count-source-bound-obligation')
  return self.count

@dataclass(frozen=True)
class PathBacking:
 encoded_bytes:Bound
 p0_backing_bytes:Bound
 open_temporary_bytes:Bound
 def checked(self):
  if any(type(v) is not Bound for v in [self.encoded_bytes,self.p0_backing_bytes,self.open_temporary_bytes]):raise Refused('typed-path-byte-bounds-required')
  encoded=self.encoded_bytes.checked();backing=self.p0_backing_bytes.checked();temp=self.open_temporary_bytes.checked()
  if backing<encoded:raise Refused('path-backing-smaller-than-encoded-bytes')
  # Native conversion is a separate request contract; no loader STR_CAP reuse.
  if temp<add(encoded,1):raise Refused('open-temporary-does-not-cover-path-and-terminator')
  return encoded,backing,temp

@dataclass(frozen=True)
class OriginalValidationBudget:
 source_bytes:Bound
 metadata_bytes:Bound
 scratch_bytes:Bound
 def checked(self):
  if any(type(v) is not Bound for v in [self.source_bytes,self.metadata_bytes,self.scratch_bytes]):raise Refused('typed-validator-byte-bounds-required')
  values=(self.source_bytes.checked(),self.metadata_bytes.checked(),self.scratch_bytes.checked())
  if any(v>cap for v,cap in zip(values,(64*1024**2,16*1024**2,1024**2))):raise Refused('widens-original-validator-cap')
  return values

@dataclass(frozen=True)
class RequiredStorage:
 source_tree_sha256:str
 host_tree_sha256:str
 paths:tuple[PathBacking,...]
 # The future actual root constructor, calling frame and any backing it owns
 # are outside the frozen private entry. Both cuts must precede quote creation.
 outer_parent_inline:Bound
 outer_parent_owned_backing:Bound
 reviewed_binding_object:Bound
 immutable_identity_and_diagnostic_backing:Bound
 original_validation:OriginalValidationBudget
 source_file_bytes:Bound
 executable_file_bytes:Bound
 build_file_bytes:Bound
 session_file_bytes:Bound
 # Fixed-callee/native/source runtime temporaries are separate from authored
 # 219-function role slots, requested Vec/Box backing and inline File/Error.
 loader_native_temporaries:Bound
 executable_open_temporary:Bound
 file_resource_backing_each:Bound
 error_backing_each:Bound
 error_owner_count:CountBound
 all_payload_destructor_temporaries:Bound

class Phase(IntEnum):
 P0_PREEXISTING=0
 P0_QUOTE=1
 P0_CHILD_RESERVED=2
 P1_SETUP=3
 P1_LOADER_OBSERVE=4
 P1_EXECUTABLE=5
 P1_VALIDATE=6
 P2_ARGUMENTS=7
 P3_SHELL=8
 P4_LEAF=9
 P5_RETURNED=10
 P5_DESTROYING=11
 P0_DESTROYED_TOKEN=12
 P0_RETIRED=13

@dataclass(frozen=True)
class Owner:
 id:str
 bytes:int
 first:Phase
 last:Phase
 funded_by:str
 interpretation:str

COMPONENTS=('P1_setup','P1_loader','P2_arguments','P3_shell','P4_leaf','P5_returned')

def checked_inventory(inv,extents):
 if hashlib.sha256(json.dumps(inv,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=FROZEN_INLINE_INVENTORY_SHA256:raise Refused('unbound-inline-inventory')
 expected=set(inv['required_layouts'])
 if set(extents)!=expected:raise Refused('missing-or-unknown-layout-extent')
 if any(type(v) is not Bound for v in extents.values()):raise Refused('layout-extent-requires-byte-type')
 supplied={k:v.checked() for k,v in extents.items()}
 ids=[];sums={'P0':0,'child':0,'leaf':0,'loader':0,'validator':0}
 for row in inv['caller_slots']:
  ids.append(row['id']);tag='P0' if row['phase'].startswith('P0') else 'child'
  sums[tag]=add(sums[tag],natural(row['bytes']))
 for row in inv['leaf_slots']:
  ids.append(row['id']);sums['leaf']=add(sums['leaf'],natural(row['bytes']))
 for row in inv['loader_slots']:
  ids.append(row['id'])
  size=natural(row['known_bytes']) if row['known_bytes'] is not None else supplied[row['required_layout']]
  sums['loader']=add(sums['loader'],size)
  if row['validator']:sums['validator']=add(sums['validator'],size)
 if len(ids)!=len(set(ids)):raise Refused('duplicate-source-object-identity')
 if (len(inv['caller_slots']),sums['P0'],sums['child'],len(inv['leaf_slots']),sums['leaf'],len(inv['loader_slots']))!=(396,234375,76696,205,320766,9403):raise Refused('changed-fixed-inline-roster')
 if inv['source_tree_sha256']!=SOURCE or inv['host_tree_sha256']!=HOST or inv['all_authored_frame_call_graph_acyclic'] is not True:raise Refused('unbound-or-recursive-inline-roster')
 return sums

def evaluate(inv,inputs:RequiredStorage):
 if type(inputs) is not RequiredStorage:raise Refused('untyped-storage-input')
 if type(inputs.error_owner_count) is not CountBound:raise Refused('error-owner-count-requires-count-type')
 for field in ['outer_parent_inline','outer_parent_owned_backing','reviewed_binding_object','immutable_identity_and_diagnostic_backing','source_file_bytes','executable_file_bytes','build_file_bytes','session_file_bytes','loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','all_payload_destructor_temporaries']:
  if type(getattr(inputs,field)) is not Bound:raise Refused('byte-bound-requires-byte-type')
 if type(inputs.original_validation) is not OriginalValidationBudget:raise Refused('typed-original-validation-required')
 if inputs.source_tree_sha256!=SOURCE or inputs.host_tree_sha256!=HOST:raise Refused('wrong-source-or-host')
 if type(inputs.paths) is not tuple or len(inputs.paths)!=5:raise Refused('all-five-immutable-paths-required')
 if any(type(p) is not PathBacking for p in inputs.paths):raise Refused('typed-path-backing-required')
 paths=[p.checked() for p in inputs.paths]
 sums=checked_inventory(inv,{})
 bindings=inputs.reviewed_binding_object.checked()
 if bindings<BINDING_DECLARED_FIELD_BYTES:raise Refused('binding-omits-inline-declared-fields')
 source_limit,metadata_limit,scratch_limit=inputs.original_validation.checked()
 source=inputs.source_file_bytes.checked();exe=inputs.executable_file_bytes.checked();build=inputs.build_file_bytes.checked();session=inputs.session_file_bytes.checked()
 if source>source_limit or exe>64*1024**2 or build>128*1024 or session>64*1024:raise Refused('file-geometry-exceeds-authored-cap')
 cache=INITIAL_CACHE_MAX_REQUESTED_BACKING
 outer_inline=inputs.outer_parent_inline.checked();outer_backing=inputs.outer_parent_owned_backing.checked();immutable=inputs.immutable_identity_and_diagnostic_backing.checked()
 error_count=inputs.error_owner_count.checked();error=mul(error_count,inputs.error_backing_each.checked())
 file=mul(6,inputs.file_resource_backing_each.checked())
 loader_native=inputs.loader_native_temporaries.checked();exe_open=inputs.executable_open_temporary.checked()
 if exe_open<4097:raise Refused('executable-open-misses-original4096-path-plus-terminator')
 destructor=inputs.all_payload_destructor_temporaries.checked()
 # Four physical loader buffers, one original immutable proof, and validator
 # growth/scratch envelopes have distinct identities. Executable Vec is explicitly
 # dropped before input/proof creation, so only this proven disjoint lifetime
 # permits reuse inside the precharged P1-loader envelope. No host refund occurs.
 validation_backing=add(source,source_limit,metadata_limit,scratch_limit)
 loader_buffer_peak=add(build,session,max(exe,validation_backing))
 p0=add(sums['P0'],outer_inline,outer_backing,bindings,immutable,*[p[1] for p in paths])
 # P1 caller59695 spans P1..P5. P2/P4 wrappers have their own source roles;
 # their 76,696 bytes are never charged twice among the six child components.
 leaf_only=sum(r['bytes'] for r in inv['leaf_slots'] if r['function']=='leaf')
 if leaf_only!=95850:raise Refused('changed-leaf30-role-layout')
 shell=add(sums['leaf']-leaf_only)
 parts={
  'P1_setup':add(59695,561,file,*[p[2] for p in paths]),
  'P1_loader':add(sums['loader'],loader_buffer_peak,loader_native,exe_open),
  'P2_arguments':add(520,CANCELLATION_BACKING),
  'P3_shell':shell,
  'P4_leaf':add(15920,leaf_only,PRODUCT_RETENTION,cache),
  'P5_returned':add(error,destructor),
 }
 if set(parts)!=set(COMPONENTS) or any(v<=0 for v in parts.values()):raise Refused('all-six-storage-parts-required-positive')
 child=add(*(parts[k] for k in COMPONENTS));total=add(p0,child)
 owners=[
  Owner('P0-parent208-inline-roster',sums['P0'],Phase.P0_PREEXISTING,Phase.P0_RETIRED,'P0','208 actual parent/account/wrapper/token source slots; not child-funded'),
  Owner('P0-future-outer-parent-inline',outer_inline,Phase.P0_PREEXISTING,Phase.P0_RETIRED,'P0','actual outer producer/caller/return/retirement frame obligation'),
  Owner('P0-future-outer-parent-owned-backing',outer_backing,Phase.P0_PREEXISTING,Phase.P0_RETIRED,'P0','all backing owned by future root producer'),
  Owner('P0-immutable-fixture-binding',bindings,Phase.P0_PREEXISTING,Phase.P0_RETIRED,'P0','5 fat path handles+claims256+original budget40+product budget136; source fields>=512, no pointee savings'),
  Owner('P0-immutable-identity-diagnostic-backing',immutable,Phase.P0_PREEXISTING,Phase.P0_RETIRED,'P0','compiled identity and static diagnostic bytes; inline str handles are not backing'),
  Owner('caller-typed-child188-inline',sums['child'],Phase.P1_SETUP,Phase.P5_DESTROYING,'child','188 exact source roles from four entry bodies, one charge'),
  Owner('loader-validator219-inline',sums['loader'],Phase.P1_LOADER_OBSERVE,Phase.P1_VALIDATE,'child','219 complete authored frames, including152 validator frames; one declared slot set per nonrecursive body'),
  Owner('leaf-shell205-inline',sums['leaf'],Phase.P3_SHELL,Phase.P5_RETURNED,'child','205 actual source roles counted once; source-operation byte occurrences excluded'),
  Owner('loader-build-Vec',build,Phase.P1_LOADER_OBSERVE,Phase.P1_VALIDATE,'child','fresh exact-reserve allocation; root-released capacity contract still required'),
  Owner('loader-session-Vec',session,Phase.P1_LOADER_OBSERVE,Phase.P1_VALIDATE,'child','fresh exact-reserve allocation'),
  Owner('loader-executable-Vec',exe,Phase.P1_EXECUTABLE,Phase.P1_EXECUTABLE,'child','ends before loader-input-Vec/proof construction; local subphase is checked in peak equation'),
  Owner('loader-input-Vec',source,Phase.P1_VALIDATE,Phase.P1_VALIDATE,'child','separate retained original input; coexists with proof for equality'),
  Owner('original-proof-source-Box',source_limit,Phase.P1_VALIDATE,Phase.P4_LEAF,'child','one non-Clone sealed proof moves loader->body->adopted/cache/refusal; finish/refusal destroys it before returned outcome; full host charge remains held'),
  Owner('original-proof-metadata-pool',metadata_limit,Phase.P1_VALIDATE,Phase.P4_LEAF,'child','category sum includes growth overlap; not one allowance per Vec/field'),
  Owner('original-validator-scratch-pool',scratch_limit,Phase.P1_VALIDATE,Phase.P1_VALIDATE,'child','category maximum, including rejection/growth overlap'),
  Owner('actual-shared-Cancellation-ArcInner',CANCELLATION_BACKING,Phase.P1_LOADER_OBSERVE,Phase.P5_DESTROYING,'child','one24B requested allocation/alignment8; clone adds zero; last owner must finish before retirement'),
  Owner('actual-six-File-resource-envelope',file,Phase.P1_SETUP,Phase.P5_DESTROYING,'child','source/build/session/executable+rows+snapshot maximum6; each original File retained; handles inline elsewhere'),
  Owner('actual-original-Error-backing-envelope',error,Phase.P1_SETUP,Phase.P5_DESTROYING,'child','positive finite original-error owner count/backing bound, including returned setup/loader/leaf diagnostics'),
  Owner('product-accepted-full-retention',PRODUCT_RETENTION,Phase.P4_LEAF,Phase.P5_DESTROYING,'child','accepted conservative logical reservation includes C/S/A/H once; overlapping conservative reserve coverage is not an alias credit'),
  Owner('initial-cache-requested-allocation-pool',cache,Phase.P4_LEAF,Phase.P4_LEAF,'child','source fixed maximum54976 requested bytes for fresh initial buffers and failed Partial cleanup; conditional frozen Global/capacity correspondence; no residents/VM/WASI; proof pools excluded'),
  Owner('native-loader-temporary-envelope',add(loader_native,exe_open,*[p[2] for p in paths]),Phase.P1_SETUP,Phase.P1_VALIDATE,'child','native request/backing interface only, distinct from known data buffers and all authored inline slots'),
  Owner('all-payload-destructor-temporary-envelope',destructor,Phase.P1_SETUP,Phase.P5_DESTROYING,'child','uniform complete transitive teardown temporary bound covers every during-entry7-type visit, leaf cleanup and late outcome; separate from WORK/carrier'),
 ]
 for i,p in enumerate(paths):owners.append(Owner(f'P0-immutable-path-{i}',p[1],Phase.P0_PREEXISTING,Phase.P0_RETIRED,'P0','actual native bytes of immutable Path pointee'))
 if len({o.id for o in owners})!=len(owners):raise Refused('duplicate-owned-backing')
 # Held prepaid envelope is constant despite actual object deaths. P0 has a
 # different funding source and survives the child-destruction return boundary.
 actual_union={p.name:add(*(o.bytes for o in owners if o.first<=p<=o.last)) for p in Phase}
 if any(actual_union[p.name]>add(p0,child) for p in Phase):raise Refused('owner-union-exceeds-prepaid-envelope')
 trace=[{'phase':p.name,'P0_held':p0,'child_held':child if Phase.P0_CHILD_RESERVED<=p<Phase.P0_RETIRED else 0,'total_held':add(p0,child if Phase.P0_CHILD_RESERVED<=p<Phase.P0_RETIRED else 0)} for p in Phase]
 return {'schema':1,'conditional_storage_interface_only':True,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,
  'P0_preexisting_required_before_policy_quote_account_entry':p0,'six_child_storage_parts':parts,'child_prepaid_storage':child,'whole_external_storage':total,
  'loader_buffer_peak':loader_buffer_peak,'validator_inline_subtotal':sums['validator'],'inline_subtotals':sums,
  'late_returned_payload_owners':{'Loaded':['original_files.source','original_files.build','original_files.session','original_files.executable: Option<File>','rows','snapshot','cancellation_owner: shared Arc24','claims_owner: inline256','original_loader_usage: inline88','primary: original structured loader/leaf result and any original io::Error'],'SetupRefused':['original typed SetupOutcomeV1','up to5 original Option<File> owners','original io::Error when Refused'],'whole_outer_carrier_bytes':13624,'outcome_inline_bytes':13608,'carrier_inline_already_in_P0_roster':True,'proof_or_cache_dynamic_backing_survives_P5':False},
  'source_object_owner_roster':[dict(id=o.id,bytes=o.bytes,first=o.first.name,last=o.last.name,funded_by=o.funded_by,interpretation=o.interpretation) for o in owners],
  'logical_owner_and_reservation_union_by_phase':actual_union,'conservative_held_charge_trace':trace,'explicit_retirement_only':True,'implicit_drop_or_unwind_releases_storage':False,
  'product_recipe':{'C':PRODUCT_C,'S':PRODUCT_S,'A':PRODUCT_A,'H_unit':PRODUCT_H,'retained':PRODUCT_RETENTION,'H_added_again':0,'product_limit_unchanged':268435456},
  'resource_capacity_basis':{'packet':'verification/swift-guarded-snapshot-resource-cost','acceptance':False,'initial_cache_max_requested_bytes':INITIAL_CACHE_MAX_REQUESTED_BACKING,'allocator_footprint':False,'compiled_std_correspondence_pending':True},
  'reservation_overlap':'Product retained floor is an opaque accepted reserve, not a second roster of actual owners. It is conservatively retained without H subtraction; new actual219/205/396 role rosters may have redundant reserve coverage. No identical own-role/backing identity is added twice within this interface. No shared accounting or runtime grant is inferred.',
  'RootPolicyPending':True,'WholeQuotePending':True,'WorkAuditPending':True,'whole_host_grant':False,'native_runtime_or_GA':False}

class RetentionControl:
 """Pure finite account-order control; it creates no source root policy."""
 def __init__(self):self.p0=False;self.quote=False;self.held=0;self.entered=False;self.destroyed=False;self.token=False;self.aborted=False;self.destroy_attempted=False
 def provision_p0(self,b):positive(b);self.p0=True
 def quote_after_p0(self):
  if not self.p0:raise Refused('P0-must-preexist-quote')
  self.quote=True
 def reserve(self,b):
  if not self.p0 or not self.quote:raise Refused('missing-preexisting-policy-and-quote')
  if self.held:raise Refused('single-use-quote')
  self.held=positive(b)
 def dispatch(self):
  if not self.held or self.entered or self.aborted:raise Refused('unpaid-or-repeated-entry')
  self.entered=True
 def destroy(self,returns):
  if not self.entered:raise Refused('not-entered')
  if type(returns) is not bool:raise Refused('unknown-destructor-completion')
  if self.aborted or self.destroy_attempted:raise Refused('consumed-destruction-attempt')
  self.destroy_attempted=True
  if returns:self.destroyed=True;self.token=True
  else:self.aborted=True
 def implicit_drop_or_unwind(self):
  self.aborted=True
  return self.held
 def retire(self):
  if self.aborted or not self.p0 or not self.destroyed or not self.token:raise Refused('early-refund')
  self.token=False;self.held=0
