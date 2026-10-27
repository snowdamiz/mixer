"""Pure146 preparation, compiler-custody and exact operation-shape controls."""
import copy,gzip,json,re,struct,sys,datetime
from pathlib import Path
from prepare import D,R,OLD,FIX,COMP,IND,inputs,sha,put,canonical
from bind_acceptance import verify_accepted_basis
from compare_mir import norm_paths,norm_bookkeeping,functions
from quote import Geometry,U64,mul,Refused
from mir_quote import evaluate
checks=[]
def check(name,ok):
 if not ok:raise AssertionError(name)
 checks.append(name)
def refuse(name,fn):
 try:fn()
 except (ValueError,Refused,KeyError):checks.append(name);return
 raise AssertionError('not-refused:'+name)
old,new,oldrefs,newrefs,oldm,newm,hosts,custody=inputs();accepted=verify_accepted_basis()
check('accepted-corrected145-basis',accepted['accepted_coefficient']==1748020339 and not accepted['source146_quote_accepted'])
sc=json.loads((D/'source-comparison.json').read_text());mc=json.loads((D/'MIR-comparison.json').read_text());overlap=json.loads((D/'account19-overlap.json').read_text())
check('exact146-source-and-host11',len(new)==146 and len(hosts['members'])==11)
check('four-changed-members',len(sc['delta'])==4 and sum(r['old'] is None for r in sc['delta'])==1 and sc['unchanged_members']==142)
check('exact-source-byte-delta',sc['old_bytes']==19651100 and sc['new_bytes']==19676994 and sc['new_bytes']-sc['old_bytes']==25894)
check('selected129-bodies-count-only',sc['body_unchanged']==128 and [r['name'] for r in sc['body_changed']]==['build'])
check('all219-complete-raw-definitions',mc['definitions']==219 and mc['normalized_complete_bodies_equal']==218 and mc['count_literal_only_bodies']==1 and not mc['unsupported_differences'])
check('all-local-type-call-closure-shapes-identical',mc['all_local_types_and_call_targets_equal'] and all(r['local_types_equal'] and r['call_targets_and_closure_identity_equal'] for r in mc['functions']))
check('fresh19-full-body-overlap',overlap['functions']==19 and all(r['normalized_equal'] for r in overlap['rows']))
# Actual descriptor guard is changed, not erased. Both versions use the same
# word read/Ne/switch and successor CFG; only this literal differs. It never
# supplies a loop iterator/count and all loop/request/credit bounds remain bound.
build=next(r for r in mc['functions'] if r['owner']=='build' and r['only_allowed_count_delta']);check('one-count-guard-body',build['only_allowed_count_delta'])
X=json.loads((D/'mir-extraction146.json').read_text());beforeX=json.loads((OLD/'mir-extraction.json').read_text())
newbuild=next(f for f in X['functions'].values() if f['owner']=='build' and '::{closure#' not in f['declared_name']);oldbuild=next(f for f in beforeX['functions'].values() if f['owner']=='build' and '::{closure#' not in f['declared_name'])
check('actual-Ne146-guard',sum('Ne(move _16, const 146_u64)' in s for s in newbuild['statements'])==1)
check('guard-value-replacement-restores-all-statements',[norm_paths(s).replace('const 146_u64','const 145_u64') for s in newbuild['statements']]==[norm_paths(s) for s in oldbuild['statements']])
loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
check('count-is-not-cardinality-driving',old[loader].replace(b'word(b, 32) != 145',b'word(b, 32) != 146')==new[loader] and new[loader].count(b'146')==1)
# Own compiler command is fresh production metadata/no selected WASI route;
# feature flags needed by the crate do not imply WASI attachment/runtime.
receipt=json.loads((D/'compiler-receipt.json').read_text());argv=receipt['argv'];env=receipt['environment']
check('one-production-preopt-compile',receipt['exit_code']==0 and not receipt['timed_out'] and receipt['direct_child_waited'] and receipt['owned_group_absent'] and '--test' not in argv and '-Zmir-opt-level=0' in argv and 'rlib' in argv and 'mixer_bootstrap_one_fixture_v1' in argv)
check('actual-toolchain-match',receipt['compiler_sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0')
check('nonempty-typed-metadata',receipt['metadata']['nonempty'] and receipt['metadata']['bytes']==25578040 and not receipt['metadata']['executed'])
raw=gzip.decompress((D/'whole-source146.mir.gz').read_bytes());selected=gzip.decompress((D/'selected-definitions146.mir.gz').read_bytes())
check('fresh-full-MIR-custody',len(raw)==receipt['MIR']['raw_bytes'] and sha(raw)==receipt['MIR']['raw_sha256']==mc['source146_MIR_sha256'])
check('complete-selected-MIR-custody',len(selected)==X['selected_bytes'] and sha(selected)==X['selected_sha256'] and X['parent_mir_sha256']==sha(raw))
manifest_bytes=(D/'preimages/manifest.json').read_bytes();manifest=json.loads(manifest_bytes);binding=json.loads((D/'preimages/binding.json').read_text())
check('fresh-manifest146-host11',manifest['distribution']==newm and manifest['host_support']==hosts and len(manifest_bytes)<=65536 and not manifest['orchestration']['test_overlay_selected'])
for t in manifest['orchestration']['source_tools']:
 b=(R/t['path']).read_bytes();check('compile-time-tool-retained:'+t['path'],len(b)==t['bytes'] and sha(b)==t['sha256'])
def decode(data):
 count=struct.unpack_from('<Q',data)[0];at=8;out=[]
 for _ in range(count):
  n=struct.unpack_from('<Q',data,at)[0];at+=8;out.append(data[at:at+n].decode());at+=n
 check('counted-exact-terminal',at==len(data));return out
check('counted-argv-exact',decode((D/'preimages/argv.bin').read_bytes())==argv)
keys=receipt['compile_identity_keys'];clean={k:v for k,v in env.items() if k not in keys}
check('counted-clean-env-exact',decode((D/'preimages/environment.bin').read_bytes())==[k+'='+v for k,v in sorted(clean.items())])
for field,key in [('manifest_sha256','MIXER_LOADER_MANIFEST_SHA256'),('argv_sha256','MIXER_LOADER_COMMAND_SHA256'),('environment_sha256','MIXER_LOADER_COMPILE_ENV_SHA256'),('compiler_sha256','MIXER_LOADER_COMPILER_SHA256'),('compiler_version_sha256','MIXER_LOADER_COMPILER_VERSION_SHA256')]:
 check('fresh-identity:'+key,binding[field]==keys[key]==env[key] and len(keys[key])==64)
constants=json.loads((D/'compile-constant-comparison.json').read_text());check('five-Some-identity-shapes',constants['all5_Some_branches_preserved'] and constants['same_normalized_constant_body_after_exact_identity_substitution'] and sum(r['changed'] for r in constants['identities'])==3)
# Fresh actual146 pricing output must equal accepted145 operation/callback/native
# terms after ONLY known VM-root normalization and freshly rebound MIR hashes.
A=json.loads((FIX/'mir-ledger.json').read_text());B=json.loads((D/'mir-ledger.json').read_text())
def normalize(value):
 if isinstance(value,str):return norm_paths(value)
 if isinstance(value,list):return [normalize(x) for x in value]
 if isinstance(value,dict):return {norm_paths(k):normalize(v) for k,v in value.items()}
 return value
NA=normalize(A);NB=normalize(B)
for key,value in NA.items():
 if key not in ('nodes','source_tree_sha256','parent_mir_sha256'):check('same-ledger-top:'+key,value==NB[key])
check('same219-node-identities',set(NA['nodes'])==set(NB['nodes']) and len(NB['nodes'])==219)
for name,row in NA['nodes'].items():
 for field,value in row.items():
  if field!='mir_sha256':check('same-pricing-term:'+name+':'+field,value==NB['nodes'][name][field])
check('fresh407-standard-roster',len(B['standard_targets'])==407)
check('corrected-two128-preserved',sum(c['multiplicity']==128 and c['target'].endswith('<&[Type] as PartialEq>::ne') for r in B['nodes'].values() if r['owner']=='wresolve' for c in r['calls'])==2)
g=Geometry(**json.loads((D/'cap-geometry.json').read_text()));a=evaluate(g,A);b=evaluate(g,B)
check('candidate-numeric-shape-zero-delta',a['W_loader']==b['W_loader']==895083809874789059 and a['wrapper_logical_actions']==b['wrapper_logical_actions']==97394558768720 and a['validator_acyclic_expanded_ceiling']==b['validator_acyclic_expanded_ceiling']==1748020339)
check('candidate-source146-provenance',b['source_tree_sha256']==newm['tree_sha256'] and b['parent_mir_sha256']==sha(raw))
check('no-acceptance-or-grant',not b['source146_quote_accepted'] and not b['operational_grant'] and not b['actual_genuine_fixture_bound'])
# Values wider than source-bound geometry and unsupported cycles still refuse.
q=g.__dict__.copy();q['credits']+=1;refuse('credit-cap-overflow',lambda:evaluate(Geometry(**q),B))
q=copy.deepcopy(B);q['nodes'][q['roots']['validator']]['calls'].append(dict(target='negative loop',callee=q['roots']['validator'],multiplicity=1));refuse('unknown-cycle',lambda:evaluate(g,q))
# New source scopes are named excluded intervals, not silently folded into P1.
account='src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs';profile='src/experimental_swift_reactor/cache/initial_profile_v1.rs';control='src/experimental_swift_reactor/control.rs'
check('new-account-unpriced-policy-stays-pending',b'Err(RefusalV1::WholeQuotePending)' in new[account] and b'Err(RefusalV1::RootPolicyPending)' in new[account])
check('common-work-constant-fixed-not-host-authority',b'451_703_621 + 33_613 + 68_781 + 7_155 + 1_272' in new[control] and b'COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436' in new[control])
check('retained-phase-preserved',b'Ok(construction)' in new[control] and b'control,retained,wasi' in new[profile])
helper='src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs';check('unused-helper-stays-unused',sum(data.count(b'checked_snapshot_emission_bound_v1') for name,data in new.items() if name!=helper)==0 and b'Err(AError::WorkAuditPending)' in new[profile])
put('candidate-cap-quote.json',b)
put('candidate-delta.json',dict(schema=1,source145_accepted_W=a['W_loader'],source146_preparation_W=b['W_loader'],W_delta=0,coefficient_delta=0,wrapper_delta=0,all_operation_type_native_repeat_callback_terms_unchanged=True,source_count_guard_changed_not_ignored=True,source146_independent_review_required=True,final_fixture_binding_pending=True,operational_grant=False))
put('controls.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),controls=len(checks),passed=True,names=checks,python=sys.version,scope='pure source146 preparation/custody/MIR/pricing-shape checks only; final146 review remains pending'))
print(json.dumps(dict(status='source146-pure-preparation-controls-pass',controls=len(checks),candidate_W=b['W_loader'],quote_accepted=False)))
