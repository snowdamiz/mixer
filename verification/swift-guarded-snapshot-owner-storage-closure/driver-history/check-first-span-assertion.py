"""Finite source occurrence/partition/layout/funding integrity and negative controls."""
import copy,json,re
from collections import Counter,defaultdict
from probe import ROOT,INPUT,ENC,save,sha,verify
from close_recipe import add,measured_type
from layouts import table,normalize
checks=[]
def check(name,fn):
 fn();checks.append({'name':name,'pass':True})
def reject(name,fn):
 try:fn()
 except (AssertionError,KeyError,OverflowError):checks.append({'name':name,'pass':True,'expected':'rejected'});return
 raise AssertionError('negative accepted: '+name)
raw=json.loads((ROOT/'raw-inventory.json').read_text());d=json.loads((ROOT/'inventory.json').read_text());h=json.loads((ROOT/'host-caller.json').read_text());b=json.loads((ROOT/'call-boundaries.json').read_text());a=json.loads((ROOT/'inherited-aliases.json').read_text());e=json.loads((ENC/'inventory.json').read_text())
prod=table();unit={normalize(r['compiler_type']):r for r in json.loads((ROOT/'unit-type-layouts.json').read_text())}
def validate(x):
 expected={r['id']:r for f in raw['functions'] for r in f['roles']}
 assert len(x['roles'])==len(expected)==3115
 assert len({r['id'] for r in x['roles']})==len(expected)
 assert {r['id'] for r in x['roles']}==set(expected)
 for r in x['roles']:
  q=expected[r['id']];assert r['compiler_type']==q['compiler_type'] and r['source']==q['source'] and r['source_member_sha256']==sha((INPUT/'source/vm/src'/r['source']['path']).read_bytes())
  assert r['multiplicity']==1
  layouts=[measured_type(v['actual_type'],prod,unit) for v in r['actual_variants']]
  assert r['bytes']==max(t['bytes'] for t in layouts)
 sums={c:0 for c in x['formulas']}
 for r in x['roles']:
  for c,n in r['funding'].items():sums[c]=add(sums[c],n)
 assert sums==x['owner_only_formulas']
 sums['selected-unconditional']=add(sums['selected-unconditional'],x['encoder_join']['unconditional_bytes'])
 sums['admitted-only']=add(sums['admitted-only'],x['encoder_join']['admitted_only_bytes'])
 assert sums==x['formulas']
check('all frozen225 and encoder49 bytes + accepted encoder contract',verify)
check('all source-declared arguments/returns/locals/temps and checked folds',lambda:validate(d))
def mir_complete():
 text=(ROOT/'function-bodies.mir').read_text()
 bodies=re.findall(r'(?m)^fn .*?\n\}',text,re.S);assert len(bodies)==81
 for f,body in zip(raw['functions'],bodies):
  args=set(re.findall(r'(_\d+):',body.splitlines()[0]));decls=set(re.findall(r'^\s+let (?:mut )?(_\d+):',body,re.M))
  assert {r['mir_local'] for r in f['roles']}==args|decls
  assert sum(r['kind']=='return-expression' for r in f['roles'])==1
  assert all(r['product_source_span_found'] or r['kind']=='parameter' for r in f['roles'])
check('exact unoptimized MIR declaration coverage including unnamed args',mir_complete)
def inherit():
 aa=a['aliases'];assert len(aa)==357 and len({q['new_id'] for q in aa})==357 and len({q['old_id'] for q in aa})==357
 for q in aa:assert q['old_id']!=q['new_id'] or q['old_source_member_sha256']
check('one-to-one old role aliases; unused old floor retained',inherit)
def partition():
 owned={(f['source']['path'],f['source']['return_line']) for f in d['functions']}
 assert not owned&{(f['source']['path'],f['source']['return_line']) for f in e['functions']}
 ids=[i for f in d['encoder_join']['functions'] for i in f['role_ids']]
 assert len(ids)==len(set(ids))==2658
 assert set(ids)=={r['id'] for r in e['roles']}
 assert sum(f['bytes'] for f in d['encoder_join']['functions'])==40531
 assert (d['encoder_join']['unconditional_bytes'],d['encoder_join']['admitted_only_bytes'])==(256,40275)
check('accepted E joined once, pregrant proof/budget/count-len256 in S',partition)
def dag():
 assert len(b['calls'])==627 and len(b['inherited_callees'])==35 and not b['unresolved']
 nodes={f['id'] for f in d['functions']};edges=defaultdict(list)
 for q in b['edges']:
  if q['to'] in nodes:edges[q['from']].append(q['to'])
 visited=set();active=set()
 def dfs(n):
  assert n not in active,'recursive source-template lifetime'
  if n in visited:return
  active.add(n)
  for child in edges[n]:dfs(child)
  active.remove(n);visited.add(n)
 for n in nodes:dfs(n)
 assert len(visited)==81
check('finite product boundaries and nonrecursive owned callback graph',dag)
def helpers():
 fs=[f for f in d['functions'] if f['source']['return_line']==1180 or (f['source']['path'].endswith('/cache.rs') and f['source']['return_line']<1800)]
 assert len(fs)==3 and sum(f['role_count'] for f in fs)==110 and sum(f['additional_bytes'] for f in fs)==34257
 assert all(f['funding_class']=='selected-unconditional' for f in fs)
check('new generic completion/drop specializations110 roles fully funded',helpers)
def none_full():
 r=next(r for r in d['roles'] if r['id']=='owner::begin_snapshot_access_v1::_38')
 assert r['source_text']=='None' and r['bytes']==4097 and r['funding']['selected-unconditional']==4097
 assert any(v['bytes']==5328 and v['actual_type'].endswith('::SnapshotPhaseStorageV1') for r in d['roles'] for v in r['actual_variants'])
check('refused None4097 inline transfer and full5328 phase storage counted',none_full)
def host():
 roles=h['function']['roles'];assert len(roles)==216 and Counter(r['funding_class'] for r in roles)=={'host-caller':53,'external-harness':163}
 assert sum(r['bytes'] for r in roles if r['funding_class']=='host-caller')==81327
 assert all(r['exclusion_reason'] for r in roles if r['funding_class']=='external-harness')
 assert len(re.findall(r'^\s+_\d+ = SnapshotRunV1::outer_v1\(', (ROOT/'host-caller.mir').read_text(),re.M))==1
 assert h['optional_wasi_paths'][0]=='None'
 assert not h['runtime_dispatched'] and not h['production_caller_integrated']
check('concrete host216 classified53 funded, Some/None and getter count1',host)
def instruments():
 x=json.loads((ROOT/'unit-instrumentation-exclusions.json').read_text())['core_extra_roles'];assert len(x)==19
 assert {r['source']['start_line'] for r in x}<={144,150,152,163,175,177,182}
check('unit-only extra19 core slots are explicit external test instrumentation',instruments)
bad=copy.deepcopy(d);bad['roles'].pop();reject('omitted source role',lambda:validate(bad))
bad=copy.deepcopy(d);bad['roles'][1]=copy.deepcopy(bad['roles'][0]);reject('duplicate source role',lambda:validate(bad))
bad=copy.deepcopy(d);bad['roles'][0]['bytes']+=1;reject('unmeasured guessed byte size',lambda:validate(bad))
bad=copy.deepcopy(d);bad['roles'][0]['multiplicity']=2;reject('loop iteration multiplied storage',lambda:validate(bad))
bad=copy.deepcopy(d);bad['roles'][0]['source_member_sha256']='0'*64;reject('foreign source member',lambda:validate(bad))
bad=copy.deepcopy(d);bad['encoder_join']['unconditional_bytes']+=40531;reject('whole encoder added twice',lambda:validate(bad))
reject('u64 overflow',lambda:add((1<<64)-1,1))
assert add(77144,add(941467,add(430175,81327)))==1530113
save(ROOT/'checks.json',{'schema':1,'checks':checks,'count':len(checks),'all_pass':True,'runtime_execution':False,'scope':'source recipe integrity and compiler metadata; no operational admission/cleanup/writer qualification'})
print('PASS',len(checks),'finite integrity/negative controls')
