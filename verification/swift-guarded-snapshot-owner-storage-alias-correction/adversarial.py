"""Targeted counterexamples for equal-text aliases and complete callee parsing."""
from collections import defaultdict
import copy, json, re
from correct import ROOT,PRODUCER,NEW_VM,OLD_VM,Source,save,build,concrete_type,spans_for_uses
from calls import parse_call,build_calls

d,aliases,_,_,_=build()
raw=json.loads((PRODUCER/'raw-inventory.json').read_text())
old={r['id']:(f,r) for f in raw['baseline_functions'] for r in f['roles']}
new={r['id']:(f,r) for f in raw['functions'] for r in f['roles']}
checks=[]
def check(name,fn):
    fn();checks.append({'name':name,'pass':True})
def reject(name,fn):
    try:fn()
    except (AssertionError,KeyError):
        checks.append({'name':name,'pass':True,'expected':'rejected'});return
    raise AssertionError('mutation accepted: '+name)

def equal(a,b):assert a==b,(a,b)
def alias_for(new_id,old_id):
    assert new_id in aliases and aliases[new_id]['old_id']==old_id

def control_receivers(rows,current):
    # This is an independent context reconstruction from compiler call spans,
    # not the correction matcher's token alignment or a type/size comparison.
    extracted=[]
    for rid,(f,r) in rows.items():
        if 'adopt_body' not in f['name'] and '1833:1' not in f['name']:continue
        if concrete_type(r,NEW_VM if current else OLD_VM)!='&mut experimental_swift_reactor::control::RuntimeControl':continue
        for use in r['uses']:
            if ' -> [return:' not in use:continue
            local,target,args=parse_call(use.split('//',1)[0].strip())
            if not re.search(r'RuntimeControl::(?:check_budget|check|admit|fail|refund)$',target):continue
            assert args.startswith('move '+r['mir_local']+',')
            source=spans_for_uses({'uses':[use]})[0]
            vm=NEW_VM if current else OLD_VM
            src=Source(vm,source['path'],source['start_line'],source['end_line'])
            text=re.sub(r'\s+','',src.snippet(source))
            logical=f['name'].replace('::adopt_body_core_v1','::adopt_body')
            if '1833:1' in logical:
                logical=next(g['name'] for g in raw['baseline_functions'] if g['name'].endswith('::adopt_body'))
            extracted.append((logical,text,source['start_line'],source['start_column'],rid))
    groups=defaultdict(list)
    for f,text,line,col,rid in extracted:groups[f,text].append((line,col,rid))
    result={}
    for (f,text),items in groups.items():
        for rank,(_,_,rid) in enumerate(sorted(items)):
            result[rid]=(f,text,rank)
    return result

nr=control_receivers(new,True);orr=control_receivers(old,False)
def receiver(new_id,old_id):assert nr[new_id]==orr[old_id]
receiver_aliases=[r for r in aliases.values() if r['new_id'] in nr]
check('all13 repeated control receivers preserve full call text, enclosing function and ordered occurrence',
      lambda:(equal(len(receiver_aliases),13),[receiver(r['new_id'],r['old_id']) for r in receiver_aliases]))
prior=json.loads((PRODUCER/'inherited-aliases.json').read_text())['aliases']
for q in prior:
    if q['new_id'] in nr:
        reject('reject original receiver swap '+q['new_id'].split('::adopt_body_core_v1')[-1],
               lambda q=q:receiver(q['new_id'],q['old_id']))

def id_for(suffix,current=True):
    source=new if current else old
    matches=[rid for rid in source if rid.endswith(suffix)]
    assert len(matches)==1,suffix
    return matches[0]
core='owner::construct_profile_core_v1'
legacy='owner::construct_with_initial_profile_v1'
for current_local,old_local in [(122,97),(126,99),(137,103),(138,104),(148,112),(149,113),
                               (165,117),(166,118),(167,119),(169,120)]:
    check('proved constructor occurrence _'+str(current_local)+' -> _'+str(old_local),
          lambda c=current_local,o=old_local:alias_for(core+'::_'+str(c),legacy+'::_'+str(o)))
for local in [115,117,130,131,160,161,162,163]:
    check('new constructor operation/owner flag charged _'+str(local),
          lambda local=local:equal(core+'::_'+str(local) in aliases,False))
for current_local,old_local in [(115,97),(117,99),(130,103),(131,104),(137,112),(138,113),
                               (160,117),(161,118),(162,119),(163,120)]:
    reject('reject same text constructor context swap _'+str(current_local),
           lambda c=current_local,o=old_local:alias_for(core+'::_'+str(c),legacy+'::_'+str(o)))
adopt=next(f['id'] for f in raw['functions'] if f['name'].endswith('::adopt_body_core_v1'))
old_adopt=next(f['id'] for f in raw['baseline_functions'] if f['name'].endswith('::adopt_body'))
for c,o in [(61,66),(65,70),(69,73),(70,74),(71,75)]:
    check('proved adoption occurrence _'+str(c)+' -> _'+str(o),
          lambda c=c,o=o:alias_for(adopt+'::_'+str(c),old_adopt+'::_'+str(o)))
for c,o in [(47,66),(48,70),(68,73),(69,74),(70,75)]:
    reject('reject same text adoption context swap _'+str(c),
           lambda c=c,o=o:alias_for(adopt+'::_'+str(c),old_adopt+'::_'+str(o)))
check('new P::failure argument has no inherited discount and costs1096 C',lambda:(
    equal(adopt+'::_54' in aliases,False),
    equal(next(r for r in d['roles'] if r['id']==adopt+'::_54')['funding']['common-extra'],1096)))
optional=json.loads((ROOT/'optional-credits-unselected.json').read_text())
check('two new foundation credits remain unselected with2192 conservative bytes retained',lambda:(
    equal(optional['selected'],False),equal(len(optional['correspondences']),2),
    equal(sum(next(r for r in d['roles'] if r['id']==q['new_id'])['funding']['common-extra'] for q in optional['correspondences']),2192)))
check('corrected C/S/A/H exact checked sums',lambda:equal(
    (d['formulas']['common-extra'],d['formulas']['selected-unconditional'],d['formulas']['admitted-only'],d['host_caller_bytes']),
    (78240,941467,430175,81327)))

statement='_1 = Target::<(), (u8, u64), fn(u8) -> ()>::method(move _2, const ")(") -> [return: bb1, unwind continue];'
check('complete target retains unit tuple and function-pointer generic parentheses',lambda:equal(
    parse_call(statement),('_1','Target::<(), (u8, u64), fn(u8) -> ()>::method','move _2, const ")("')))
calls,changes=build_calls()
check('627 complete call targets,107 repairs,2 missing callback edges and acyclic81-template graph',lambda:(
    equal(len(calls['calls']),627),equal(calls['correction']['complete_target_changes'],107),
    equal(len(calls['correction']['added_owned_callback_edges']),2),equal(calls['correction']['graph_acyclic'],True)))
def validate_calls(data):
    assert data['calls']==calls['calls'] and data['edges']==calls['edges']
bad=copy.deepcopy(calls);q=next(q for q in changes if q['before_target']!=q['after_target'])
target=next(r for r in bad['calls'] if r['source_statement_sha256']==q['source_statement_sha256'])
target['target']=q['before_target']
reject('reject target truncated at generic tuple/unit/function first parenthesis',lambda:validate_calls(bad))
for omitted in calls['correction']['added_owned_callback_edges']:
    bad=copy.deepcopy(calls);bad['edges'].remove(omitted)
    reject('reject omitted owned callback '+omitted['to'],lambda bad=bad:validate_calls(bad))

save('adversarial-controls.json',{'schema':1,'count':len(checks),'checks':checks,'all_pass':True,
    'runtime_executions':0,'scope':'frozen-source/MIR alias and target integrity; no admission-floor selection or engine/runtime qualification'})
print('PASS',len(checks),'targeted adversarial/context controls')
