"""Finite integrity and deliberate negative controls; no compiler/runtime launch."""
import copy, json, re, sys
from pathlib import Path
from probe import HERE, BASE, HELPER, OWNER, INITIAL, CALLEE, custody, sha, canonical, decode_tuple, members
from derive import NAMES, functions, normalize_mir, parse

def load(n):return json.loads((HERE/n).read_text())
def output(n,value):
 raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();p=HERE/n
 if '--verify' in sys.argv:assert p.read_bytes()==raw,('output drift',n)
 else:p.write_bytes(raw)
def main():
 controls=[]
 def yes(name,condition):
  assert condition,name;controls.append({'name':name,'passed':True})
 def rejected(name,action):
  try:action()
  except (AssertionError,OverflowError,ValueError,KeyError):controls.append({'name':name,'passed':True,'expected':'rejection'})
  else:raise AssertionError(('mutation accepted',name))
 checked=custody();record=load('input-custody.json')
 yes('all-predecessor-seal-members-rehashed',checked['inputs']==record['inputs'])
 yes('conditional-owner-base-not-accepted',not record['owner_base_accepted'])
 yes('corrected144-base-and-accepted-helper-bound',record['source144_tree_sha256']=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896' and sha((HERE/'overlay/vm'/CALLEE).read_bytes())=='ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a')
 raw=load('raw-added-roles.json');roles=load('roles.json');layout=load('type-layouts.json');formula=load('formula.json');delta=load('wrapper-delta.json');old=load('baseline-wrapper-roles.json')
 modes={m:functions((HERE/(m+'-functions.mir')).read_text()) for m in ['production','unit']}
 yes('four-functions-production-unit-identical-source-mir',all(normalize_mir(modes['production'][n])==normalize_mir(modes['unit'][n]) for n in NAMES))
 for key,name in [('helper',NAMES[0]),('proposed_wrapper',NAMES[1])]:
  expected=parse(name,modes['production'][name],'production+cfg(test) identical source MIR')
  yes('complete-declarations-'+key,raw[key]==expected)
  yes('exact-declaration-ids-'+key,[r['mir_local'] for r in expected]==['_'+str(i) for i in range(39 if key=='helper' else 3)])
 by={r['type']:r for r in layout['types']};yes('ten-actual-nameable-type-layouts',len(by)==10)
 for mode in ['production','unit']:
  ir=(HERE/(mode+'-layout-tuples.llvm')).read_text()
  for r in layout['types']:
   line=next(l for l in ir.splitlines() if l.startswith('@'+r[mode]['symbol']+' ='))
   yes('actual-layout-'+mode+'-'+r[mode]['symbol'],decode_tuple(line)=={k:r[mode][k] for k in ['bytes','alignment']})
 yes('production-unit-layouts-agree',all((r['production']['bytes'],r['production']['alignment'])==(r['unit']['bytes'],r['unit']['alignment']) for r in layout['types']))
 def validate_roles(candidate):
  for group in ['helper','proposed_wrapper']:
   assert len({r['id'] for r in candidate[group]})==len(candidate[group])
   assert len(candidate[group])==len(raw[group])
   for r,ref in zip(candidate[group],raw[group]):
    assert {k:r[k] for k in ref}==ref
    l=by[r['type']]
    assert r['bytes']==max(l[m]['bytes'] for m in ['production','unit'])
    assert r['alignment']==max(l[m]['alignment'] for m in ['production','unit'])
    assert r['layout_evidence']==l
 validate_roles(roles);yes('every-role-layout-and-source-occurrence-identity',True)
 mutations=[]
 x=copy.deepcopy(roles);x['helper'].pop(3);mutations.append(('omit-ControlFlow-role',x))
 x=copy.deepcopy(roles);x['helper'].append(copy.deepcopy(x['helper'][0]));mutations.append(('duplicate-return-role',x))
 x=copy.deepcopy(roles);x['helper'][7]['bytes']=1;mutations.append(('guess-eager-Arithmetic-tag-only',x))
 x=copy.deepcopy(roles);x['helper'][9]['bytes']=0;mutations.append(('drop-actual-residual-storage',x))
 x=copy.deepcopy(roles);x['helper'][1]['bytes']=104;mutations.append(('copy-shape-instead-of-borrow',x))
 x=copy.deepcopy(roles);x['proposed_wrapper'][2]['bytes']=0;mutations.append(('omit-wrapper-compiler-reborrow',x))
 x=copy.deepcopy(roles);x['helper'][2]['source']['start_line']+=1;mutations.append(('foreign-source-occurrence',x))
 x=copy.deepcopy(roles);x['helper'][2]['multiplicity']=3;mutations.append(('invent-loop-multiplier',x))
 x=copy.deepcopy(roles);x['helper'][0]['funding_partition']='A admitted-only after commit';mutations.append(('late-admitted-partition-funding',x))
 for name,x in mutations:rejected(name,lambda x=x:validate_roles(x))
 tally={}
 for r in roles['helper']:tally.setdefault(r['type'],[0,0]);tally[r['type']][0]+=1;tally[r['type']][1]+=r['bytes']
 yes('helper-closed39-source-places18816',sum(x[0] for x in tally.values())==39 and sum(x[1] for x in tally.values())==18816)
 yes('four-eager-errors-full1096-each',tally['experimental_swift_reactor::control::SnapshotAdmissionErrorV1']==[4,4384])
 yes('four-Options-three-branch-carriers-six-residual-places',tally['std::option::Option<u64>']==[4,64] and any(t.startswith('std::ops::ControlFlow<') and v==[3,3288] for t,v in tally.items()) and any(t.startswith('std::result::Result<std::convert::Infallible,') and v==[6,6576] for t,v in tally.items()))
 def validate_delta(value):
  assert len(value['retained'])==2 and len(value['removed'])==1 and len(value['added'])==1
  assert [(r['baseline_id'],r['proposed_id'],r['bytes']) for r in value['retained']]==[(old[i]['id'],roles['proposed_wrapper'][i]['id'],old[i]['bytes']) for i in range(2)]
  assert value['removed'][0]['baseline_id']=='owner::proposed_emission_work_v1::_2'
  assert value['removed'][0]['source_text']=='AError::WorkAuditPending' and value['removed'][0]['bytes']==1096
  assert value['added']==[roles['proposed_wrapper'][2]] and value['added'][0]['bytes']==8
 validate_delta(delta);yes('wrapper-exact-return-parameter-retain-refusal-remove-forward-add',True)
 x=copy.deepcopy(delta);x['removed'][0]['baseline_id']='owner::proposed_emission_work_v1::_0'
 rejected('wrong-return-slot-removal',lambda:validate_delta(x))
 x=copy.deepcopy(delta);x['removed'][0]['baseline_id']='owner::begin_snapshot_access_v1::{closure#0}::_49'
 rejected('wrong-caller-result-removal',lambda:validate_delta(x))
 base=json.loads((OWNER/'inventory.json').read_text());preserved=load('preserved-begin-roles.json');oldmir=functions((OWNER/'function-bodies.mir').read_text())
 yes('all131-existing-begin-places-retained',preserved['role_count']==131 and preserved['bytes']==77098 and len({r['baseline_id'] for r in preserved['roles']})==131)
 for n in NAMES[2:]:
  yes('begin-MIR-exact-except-spans-'+n,normalize_mir(oldmir[n])==normalize_mir(modes['production'][n]))
  expected=[r for r in base['roles'] if r['template']=='owner::'+n]
  got=[r for r in preserved['roles'] if r['baseline_id'].startswith('owner::'+n+'::_')]
  yes('all-caller-identities-retained-'+n,[(r['baseline_id'],r['bytes'],r['compiler_type']) for r in got]==[(r['id'],r['bytes'],r['compiler_type']) for r in expected])
 yes('ten-explicit-caller-evaluator-boundary-places-preserved',len(preserved['caller_slice'])==10 and [int(r['baseline_id'].rsplit('::_',1)[1]) for r in preserved['caller_slice']]==list(range(47,57)))
 src=(HERE/'overlay/vm'/INITIAL).read_text();wrapper=load('proposal.json')['body'];accepted=(HELPER/'overlay/vm'/INITIAL).read_text()
 yes('only-proposed-wrapper-replacement',src==accepted.replace(load('proposal.json')['baseline_wrapper'],wrapper))
 yes('old-refusal-preserved-in-actual-base',load('proposal.json')['baseline_wrapper'] in (BASE/'source/vm'/INITIAL).read_text())
 yes('storage-before-evaluation-and-commit',src.index('control.snapshot_storage_preflight_v1(additional)?')<src.index('let emission=proposed_emission_work_v1(&shape)?')<src.index('control.snapshot_debit_v1(emission)?')<src.index('control.snapshot_commit_storage_v1(additional)?') and formula['funding_placement'].startswith('Include delta in S'))
 convention=(HERE.parent/'swift-guarded-snapshot-writer-work-audit/cost-convention.md').read_text()
 ledger=json.loads((HERE.parent/'swift-guarded-snapshot-writer-work-correction/corrected-ledger.json').read_text())
 yes('bound-operands-free-entry-return-two', 'literal and\nbound local operands are free' in convention and 'entry and return cost two' in convention)
 yes('old-wrapper-three-from-accepted-ledger',ledger['admission']['actual_proposed_emission_helper'].startswith('entry2 + Err WorkAuditPending1'))
 yes('exact-tail-delegation-no-source-borrow-binding',wrapper.splitlines()[1].strip()=='emission_bound_v1::checked_snapshot_emission_bound_v1(shape)')
 yes('helper29-wrapper2-old3-net28-caller3-once',formula['helper_action_count']==29 and formula['proposed_wrapper_actions']==2 and formula['old_wrapper_actions']==3 and formula['wrapper_action_delta']==-1 and formula['action_delta_with_helper']==28 and formula['proposed_evaluator_actions']==31 and formula['existing_begin_caller_actions_retained']==3)
 yes('initializer4096-one-occurrence',formula['initializer_bytes']==4096 and formula['initializer_occurrences']==1 and formula['accepted_emission_expression']=='19537+299377B+32E')
 work=load('work-attribution.json')
 yes('work-convention-source-attribution',work['convention_sha256']==sha(convention.encode()) and work['accepted_corrected_ledger_sha256']==sha((HERE.parent/'swift-guarded-snapshot-writer-work-correction/corrected-ledger.json').read_bytes()) and work['proposed_evaluator_total']==31 and work['net_evaluator_delta']==28)
 acceptance=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-writer-work-host-acceptance.json'
 yes('writer-work-acceptance-bound',sha(acceptance.read_bytes())=='21251a3aef2d42373ba71711f8eb389634294d4b5b3b61388e718bfb0a25e281')
 yes('conditional-net-delta-and-sum',formula['helper_bytes']==18816 and formula['wrapper_added_bytes']==8 and formula['wrapper_removed_bytes']==1096 and formula['net_S_addition']==17728 and formula['candidate_S']==959195 and formula['baseline_S']==941467)
 yes('all-other-partitions-retained',formula['candidate_C']==77144 and formula['candidate_A']==430175 and formula['candidate_H']==81327)
 limit=2**64-1
 def add(a,b):
  if not 0<=a<=limit or not 0<=b<=limit or a+b>limit:raise OverflowError
  return a+b
 def sub(a,b):
  if not 0<=b<=a<=limit:raise OverflowError
  return a-b
 yes('last-fitting-u64-add',add(limit-17728,17728)==limit)
 rejected('first-overflow-u64-add',lambda:add(limit-17727,17728))
 rejected('underfunded-baseline-subtraction',lambda:sub(1095,1096))
 yes('exact-baseline-removal-boundary',sub(1096,1096)==0)
 yes('complete-checked-conditional-fold',add(sub(941467,1096),add(18816,8))==959195 and add(add(add(77144,959195),430175),81327)==1547841)
 proposal=load('proposal.json');yes('descriptor145-versus144-support11-remains-pending',proposal['source_count']==145 and proposal['unchanged_loader_descriptor']=={'source_count':144,'support_count':11} and not proposal['genuine_loader_binding'])
 yes('no-selected-admission-work-or-physical-layout-claim',not formula['operational_selection'] and not formula['planning_16384_coverage_proved'] and not formula['inherited_work_and_cleanup_paid'])
 receipts=[]
 source={r['path']:r for r in members(BASE/'source/vm')}
 def row(path,b):return {'path':path,'bytes':len(b),'sha256':sha(b)}
 for path in [INITIAL,CALLEE]:source[path]=row(path,(HERE/'overlay/vm'/path).read_bytes())
 source_rows=[source[k] for k in sorted(source,key=Path)]
 manifest=load('source-manifest.json')
 yes('complete-proposed145-source-manifest',manifest['members']==source_rows and manifest['source_tree_sha256']==sha(canonical(source_rows)) and manifest['source_count']==145 and manifest['loader_descriptor_source_count']==144 and not manifest['genuine_loader_claim'])
 layout_source=dict(source)
 layout_source[CALLEE]=row(CALLEE,(HERE/'overlay/vm'/CALLEE).read_bytes()+(HERE/'layout-seam.rs').read_bytes())
 layout_source['src/lib.rs']=row('src/lib.rs',b'#![feature(never_type)]\n'+(BASE/'source/vm/src/lib.rs').read_bytes())
 layout_rows=[layout_source[k] for k in sorted(layout_source,key=Path)]
 for p in sorted((HERE/'commands').glob('*/receipt.json')):
  r=json.loads(p.read_text());d=p.parent
  yes('receipt-output-and-reaping-'+d.name,sha((d/'stdout').read_bytes())==r['stdout_sha256'] and sha((d/'stderr').read_bytes())==r['stderr_sha256'] and r['child_reaped'] and r['owned_group_absent'] and not r['timed_out'] and r['timeout_seconds']==55)
  yes('compiler-only-command-'+d.name,r['argv'][0].endswith('/rustc') and any(x in r['argv'] for x in ['--emit=mir','--emit=llvm-ir','--emit=metadata']))
  pre=json.loads((d/'source-preimage.json').read_text());yes('preimage-member-roster-'+d.name,len(pre['members'])==(1 if 'checked-recipe' in d.name else 145))
  if 'checked-recipe' in d.name:
   b=(HERE/'checked-additive-recipe.rs').read_bytes()
   if 'overflow-negative' in d.name:b+=(HERE/'overflow-negative-seam.rs').read_bytes()
   expected=[row('src/lib.rs',b)]
  else:expected=layout_rows if 'layouts' in d.name else source_rows
  yes('exact-source-preimage-reconstructed-'+d.name,pre['members']==expected)
  env=r['environment'];env_pre={k:v for k,v in env.items() if k!='MIXER_LOADER_COMPILE_ENV_SHA256'}
  yes('exact-command-environment-digests-'+d.name,env['MIXER_LOADER_MANIFEST_SHA256']==sha(canonical(expected)) and env['MIXER_LOADER_COMMAND_SHA256']==sha(canonical(r['argv'])) and env['MIXER_LOADER_COMPILE_ENV_SHA256']==sha(canonical(env_pre)))
  if (d/'probe-source.py').exists():yes('exact-driver-snapshot-'+d.name,sha((d/'probe-source.py').read_bytes())==pre['probe_sha256'])
  receipts.append({'path':str(p.relative_to(HERE)),'exit_code':r['exit_code'],'owned_group':r['owned_process_group'],'child_reaped':r['child_reaped'],'owned_group_absent':r['owned_group_absent'],'elapsed_seconds':r['elapsed_seconds']})
 yes('eleven-compiler-commands-ten-pass-one-required-overflow',len(receipts)==11 and sum(r['exit_code']==0 for r in receipts)==10 and next(r for r in receipts if 'overflow-negative' in r['path'])['exit_code']!=0)
 yes('required-overflow-E0080-preserved','E0080' in (HERE/'commands/checked-recipe-overflow-negative/stderr').read_text())
 yes('all-owned-scratch-removed',not (HERE/'owned-work').exists() and all(load(n)['scratch_absent'] for n in ['mir-cleanup.json','layout-cleanup.json','recipe-cleanup.json']))
 output('checks.json',{'schema':1,'count':len(controls),'controls':controls})
 output('compiler-command-summary.json',{'schema':1,'commands':receipts,'compiler_only':True,'runtime_invocations':0,'all_children_reaped':True,'all_owned_groups_absent':True,'no_global_inventory':True})
 output('result.json',{'schema':1,'status':'frozen-separable-conditional-additive-candidate-awaiting-independent-review','checks':len(controls),
  'helper_places':39,'helper_bytes':18816,'wrapper_added_bytes':8,'old_refusal_removed_bytes':1096,'net_S_addition':17728,'conditional_S':959195,
  'preserved_begin_places':131,'preserved_begin_bytes':77098,'helper_actions':29,'proposed_wrapper_actions':2,'proposed_evaluator_actions':31,'old_wrapper_actions':3,'net_evaluator_action_delta':28,
  'compiler_commands':11,'expected_overflow_failures':1,'product_runtime_invocations':0,'owner_base_accepted':False,'actual_WorkAuditPending_preserved':True,'operational_selection':False,
  'root_reported_base_limitation':'Frozen owner alias357 map has cross-function source identity defects; not read or used here. Conditional base constants do not gain acceptance from this delta.',
  'pending':['independent delta review','correct and accept owner base source aliases','full planning/inherited/caller/cleanup/finalizer work and lifetime decisions','real direct delegation and admission integration','descriptor144/support11 requalification for145 sources','paused native/device/simulator/emulator checks','canonical/OTA/FieldLog/store/customer/GA qualification']})
 print(json.dumps({'checks':len(controls),'net_S_addition':17728,'net_evaluator_action_delta':28,'compiler_only':True}))

if __name__=='__main__':main()
