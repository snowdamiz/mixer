"""Finite source/MIR role derivation for the proposed direct delegation."""
from pathlib import Path
import collections, json, re, sys
from probe import HERE, BASE, OWNER, INITIAL, CALLEE, sha, save, canonical, members

NAMES=['checked_snapshot_emission_bound_v1','proposed_emission_work_v1','begin_snapshot_access_v1','begin_snapshot_access_v1::{closure#0}']
PREFIX='delta::'
def split_top(s):
 out=[];start=depth=0
 for i,c in enumerate(s):
  if c in '<([{':depth+=1
  elif c in '>)]}':depth-=1
  elif c==',' and depth==0:out.append(s[start:i].strip());start=i+1
 out.append(s[start:].strip());return out
def functions(t):
 return {b.splitlines()[0][3:].split('(')[0]:b for m in re.finditer(r'(?m)^fn .*?\n\}',t,re.S) for b in [m.group()] if b.splitlines()[0][3:].split('(')[0] in NAMES}
def normalize_mir(t):
 t='\n'.join(l.split('//')[0].rstrip() for l in t.splitlines())
 t=re.sub(r'(?<=\.rs):\d+:\d+: \d+:\d+',':<span>',t)
 return '\n'.join(l for l in t.splitlines() if l)
def normalize_type(t):
 return t.replace('&SnapshotShapeV1','&experimental_swift_reactor::cache::initial_profile_v1::SnapshotShapeV1')
def parse(name,body,mode):
 header=body.splitlines()[0];args=header[header.index('(')+1:header.rindex(') ->')]
 decl={}
 for a in split_top(args):
  if a:n,t=a.split(': ',1);decl[n]={'type':normalize_type(t),'argument':True,'origin':'actual function parameter'}
 for m in re.finditer(r'^\s+let (?:mut )?(_\d+): (.*?);\s*// ([^\n]*)',body,re.M):decl[m[1]]={'type':normalize_type(m[2]),'argument':False,'origin':m[3]}
 names={}
 for m in re.finditer(r'debug (\w+) => (_\d+);',body):names.setdefault(m[2],[]).append(m[1])
 rows=[]
 for local,d in sorted(decl.items(),key=lambda z:int(z[0][1:])):
  spantext=d['origin']
  if d['argument']:
   spantext=next((l for l in body.splitlines() if '=> '+local+';' in l),'')
  m=re.search(r'at source/([^:]+):(\d+):(\d+): (\d+):(\d+)',spantext);assert m,(name,local,spantext)
  path,start,col,end,endcol=m[1],int(m[2]),int(m[3]),int(m[4]),int(m[5]);src=(HERE/'overlay/vm/src'/path).read_text().splitlines()
  lines=src[start-1:end]
  if len(lines)==1:snippet=lines[0][col-1:endcol-1]
  else:lines[0]=lines[0][col-1:];lines[-1]=lines[-1][:endcol-1];snippet='\n'.join(lines)
  rows.append({'id':PREFIX+name+'::'+local,'mir_local':local,'type':d['type'],'debug_names':names.get(local,[]),
   'kind':'return' if local=='_0' else 'parameter' if d['argument'] else 'binding-or-pattern' if local in names else 'temporary',
   'source':{'path':'src/'+path,'start_line':start,'start_column':col,'end_line':end,'end_column':endcol,'text':snippet},
   'source_member_sha256':sha((HERE/'overlay/vm/src'/path).read_bytes()),'declaration_origin':d['origin'],
   'uses':[l.strip() for l in body.splitlines() if re.search(r'(?<![A-Za-z0-9_])'+local+r'(?!\d)',l) and not re.match(r'\s*(let |debug )',l)],
   'multiplicity':1,'funding_partition':'S selected-unconditional before evaluator and phase commit','context':mode})
 return rows

def raw():
 source={r['path']:r for r in members(BASE/'source/vm')}
 for p in (HERE/'overlay/vm').rglob('*'):
  if p.is_file():
   path=str(p.relative_to(HERE/'overlay/vm'));b=p.read_bytes();source[path]={'path':path,'bytes':len(b),'sha256':sha(b)}
 roster=[source[k] for k in sorted(source,key=Path)];assert len(roster)==145
 save('source-manifest.json',{'schema':1,'members':roster,'source_tree_sha256':sha(canonical(roster)),'source_count':145,'base_source_count':144,'loader_descriptor_source_count':144,'loader_descriptor_support_count':11,'genuine_loader_claim':False})
 modes={mode:functions((HERE/(mode+'-functions.mir')).read_text()) for mode in ['production','unit']}
 assert all(set(v)==set(NAMES) for v in modes.values())
 for n in NAMES:assert normalize_mir(modes['production'][n])==normalize_mir(modes['unit'][n]),n
 helper=parse(NAMES[0],modes['production'][NAMES[0]],'production+cfg(test) identical source MIR')
 wrapper=parse(NAMES[1],modes['production'][NAMES[1]],'production+cfg(test) identical source MIR')
 assert len(helper)==39 and len(wrapper)==3
 save('raw-added-roles.json',{'helper':helper,'proposed_wrapper':wrapper})
 types=list(dict.fromkeys(r['type'] for r in helper+wrapper))
 types.append('experimental_swift_reactor::cache::initial_profile_v1::SnapshotShapeV1')
 save('layout-requests.json',[{'symbol':'MIXER_EMISSION_LAYOUT_'+str(i),'type':t} for i,t in enumerate(types)])
 owner=json.loads((OWNER/'inventory.json').read_text());old=functions((OWNER/'function-bodies.mir').read_text())
 preserved=[]
 for n in NAMES[2:]:
  assert normalize_mir(old[n])==normalize_mir(modes['production'][n]),n
  rows=[r for r in owner['roles'] if r['template']=='owner::'+n]
  actual=re.findall(r'^\s+let (?:mut )?(_\d+):',modes['production'][n],re.M)+re.findall(r'(_\d+): ',modes['production'][n].splitlines()[0])
  assert sorted(actual)==sorted(r['mir_local'] for r in rows)
  preserved.extend({'baseline_id':r['id'],'bytes':r['bytes'],'source_text':r['source_text'],'compiler_type':r['compiler_type'],'funding':r['funding'],'reason':'structurally identical MIR excluding spans and physical source line movement'} for r in rows)
 save('preserved-begin-roles.json',{'roles':preserved,'role_count':len(preserved),'bytes':sum(r['bytes'] for r in preserved),'mir_unchanged_except_spans':True,
  'existing_caller_actions':3,'actions':'one binding and two ? inspection/return actions already in future-begin; unchanged',
  'caller_slice':[r for r in preserved if r['baseline_id'].startswith('owner::begin_snapshot_access_v1::{closure#0}::') and 47<=int(r['baseline_id'].rsplit('::_',1)[1])<=56]})
 baseline=[r for r in owner['roles'] if r['template']=='owner::proposed_emission_work_v1']
 assert [(r['mir_local'],r['bytes']) for r in baseline]==[('_0',1096),('_1',8),('_2',1096)]
 assert baseline[2]['source_text']=='AError::WorkAuditPending'
 save('baseline-wrapper-roles.json',baseline)

def derived():
 data=json.loads((HERE/'raw-added-roles.json').read_text());layouts=json.loads((HERE/'type-layouts.json').read_text());by={r['type']:r for r in layouts['types']}
 for group in data:
  for r in data[group]:
   t=by[r['type']];r['bytes']=max(t[m]['bytes'] for m in ['production','unit']);r['alignment']=max(t[m]['alignment'] for m in ['production','unit']);r['layout_evidence']=t
 save('roles.json',data)
 helper=sum(r['bytes'] for r in data['helper']);wrap=sum(r['bytes'] for r in data['proposed_wrapper']);old=json.loads((HERE/'baseline-wrapper-roles.json').read_text())
 retained=[{'baseline_id':r['id'],'proposed_id':p['id'],'bytes':r['bytes'],'reason':'same result return or borrowed shape parameter identity; no second charge'} for r,p in zip(old[:2],data['proposed_wrapper'][:2])]
 removed=[{'baseline_id':old[2]['id'],'source_text':old[2]['source_text'],'bytes':old[2]['bytes'],'reason':'only removed refusal constructor temporary; no return or outer caller slot removed'}]
 new=[data['proposed_wrapper'][2]];assert new[0]['bytes']==8 and new[0]['type'].startswith('&')
 delta=helper+sum(r['bytes'] for r in new)-sum(r['bytes'] for r in removed)
 baseline=json.loads((OWNER/'formula.json').read_text())
 formula={'schema':1,'helper_roles':len(data['helper']),'helper_bytes':helper,'proposed_wrapper_bytes':wrap,'baseline_wrapper_bytes':sum(r['bytes'] for r in old),
  'wrapper_retained_bytes':sum(r['bytes'] for r in retained),'wrapper_added_bytes':sum(r['bytes'] for r in new),'wrapper_removed_bytes':sum(r['bytes'] for r in removed),
  'net_S_addition':delta,'candidate_S':baseline['selected_unconditional_extra']+delta,'baseline_S':baseline['selected_unconditional_extra'],
  'candidate_C':baseline['common_extra'],'candidate_A':baseline['admitted_only_extra'],'candidate_H':baseline['host_caller_extra'],
  'recipe':'S_candidate = checked_add(checked_sub(S_frozen_owner, removed_old_refusal1096), checked_add(helper_all_source_places, wrapper_forwarding8))',
  'base_status':'frozen owner producer candidate; not accepted; conditional composition only; independent alias identity defect reported by root','operational_selection':False,
  'funding_placement':'Include delta in S initial selected funding, before helper evaluation, computed emission debit and phase commit. A is too late.',
  'lifetime':'Retain all baseline caller/phase/cleanup owners; no physical stack alias or healthy/narrowing deduction. Add source occurrence reservations conservatively; no simultaneous stack/RSS claim.',
  'helper_action_count':29,'old_wrapper_actions':3,'proposed_wrapper_actions':2,'wrapper_action_delta':-1,
  'proposed_evaluator_actions':31,'action_delta_with_helper':28,'existing_begin_caller_actions_retained':3,'initializer_occurrences':1,'initializer_bytes':4096,
  'action_definition':'Accepted convention makes literals/bound operands free. Wrapper entry+return2; bare shape forwarding has no source borrow or binding and no new call boundary allowance. Old wrapper entry+return2 plus WorkAuditPending/Err refusal construction1. Helper29 includes its own entry/return. Begin existing ?/binding3 is retained. Compiler reborrow storage does not invent an action. These source logical actions are not CPU/stack/time.',
  'accepted_emission_expression':'19537+299377B+32E','emission_expression_changed':False,'planning_16384_coverage_proved':False,
  'inherited_work_and_cleanup_paid':False,'changed_source_members':2,'proposed_source_members':145,'descriptor_source_count':144,'descriptor_support_count':11,'genuine_loader_claim':False,
  'stdlib_scope':'Exact product source MIR occurrence convention matches frozen owner recipe. Rust standard-library primitive internals are not separately expanded; no native/CPU/physical stack closure is claimed.'}
 save('formula.json',formula);save('wrapper-delta.json',{'retained':retained,'removed':removed,'added':new,'caller_begin_all_preserved':True})
 convention=HERE.parent/'swift-guarded-snapshot-writer-work-audit/cost-convention.md'
 ledger=HERE.parent/'swift-guarded-snapshot-writer-work-correction/corrected-ledger.json'
 save('work-attribution.json',{'schema':1,'convention_sha256':sha(convention.read_bytes()),'accepted_corrected_ledger_sha256':sha(ledger.read_bytes()),
  'wrapper_before':{'entry_return':2,'Err_WorkAuditPending':1,'total':3},
  'wrapper_after':{'entry_return':2,'bare_bound_operand_forwarding':0,'implicit_compiler_reborrow_action':0,'extra_call_boundary':0,'total':2},
  'accepted_helper29_separate':29,'proposed_evaluator_total':31,'net_evaluator_delta':28,
  'scope':'Evaluator matched invocation only. Replacing refusal would allow additional already specified begin/admitted branches; +28 is not a bound for the entire operational change.',
  'already_in_future_begin':{'question_inspection_and_payload':2,'emission_binding':1},
  'future_begin_interface_excluding_evaluator':7930,'future_begin_includes_initializer4096':True,'accepted_emission_includes_same_initializer4096':True,
  'combination_rule':'Count initializer4096 once, e.g. (future_begin7930-4096)+evaluator31+accepted_emission(19537+299377B+32E), while separately preserving authority19, shell/inherited/caller/stop/cleanup/F1 obligations. This arithmetic is not complete paid planning or selected admission.',
  'unchanged_planning_literal16384_coverage_proved':False,'unchanged_execution_work_ceiling':1000000000})
 grouped={}
 for r in data['helper']:grouped.setdefault(r['type'],{'roles':[],'bytes':0});grouped[r['type']]['roles'].append(r['id']);grouped[r['type']]['bytes']+=r['bytes']
 save('helper-type-occurrences.json',grouped)
 recipe='// Const-only conditional additive recipe; no runtime admission or arrays.\n'
 for k,v in [('BASE_C',formula['candidate_C']),('BASE_S',formula['baseline_S']),('BASE_A',formula['candidate_A']),('BASE_H',formula['candidate_H']),('OLD_REFUSAL',1096),('WRAPPER_FORWARD',8)]:recipe+='pub const '+k+':u64='+str(v)+';\n'
 recipe+='pub const HELPER_ALL_PLACES:u64=0u64\n'
 for r in data['helper']:recipe+=' // '+r['id']+'\n .checked_add('+str(r['bytes'])+').expect("helper source occurrence sum")\n'
 recipe+=';\npub const HELPER_PLUS_FORWARD:u64=HELPER_ALL_PLACES.checked_add(WRAPPER_FORWARD).expect("helper and wrapper");\n'
 recipe+='pub const BASE_S_LESS_REFUSAL:u64=BASE_S.checked_sub(OLD_REFUSAL).expect("baseline identity subtraction");\n'
 recipe+='pub const CANDIDATE_S:u64=BASE_S_LESS_REFUSAL.checked_add(HELPER_PLUS_FORWARD).expect("S addition");\n'
 recipe+='pub const NET_DELTA:u64=HELPER_PLUS_FORWARD.checked_sub(OLD_REFUSAL).expect("positive delta");\n'
 recipe+='pub const SELECTED_FROM_LEGACY:u64=BASE_C.checked_add(CANDIDATE_S).expect("selected sum");\n'
 recipe+='pub const PHASE_FROM_LEGACY:u64=SELECTED_FROM_LEGACY.checked_add(BASE_A).expect("phase sum");\n'
 recipe+='pub const HOST_PHASE_FROM_LEGACY:u64=PHASE_FROM_LEGACY.checked_add(BASE_H).expect("host sum");\n'
 recipe+='const _:()=assert!(HELPER_ALL_PLACES=='+str(helper)+' && NET_DELTA=='+str(delta)+' && CANDIDATE_S=='+str(formula['candidate_S'])+');\n'
 (HERE/'checked-additive-recipe.rs').write_text(recipe)
 print(json.dumps({'helper_roles':len(data['helper']),'helper_bytes':helper,'wrapper_added':8,'old_refusal_removed':1096,'net_S_delta':delta,'candidate_S':formula['candidate_S']}))

if __name__=='__main__':
 if sys.argv[1]=='raw':raw()
 elif sys.argv[1]=='derived':derived()
 else:raise ValueError(sys.argv[1])
