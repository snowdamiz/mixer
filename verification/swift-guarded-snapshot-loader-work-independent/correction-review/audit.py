#!/usr/bin/env python3
"""Read-only inputs; pure actual receiver/resolve calls; no pricing-script replay."""
from pathlib import Path
import ast,collections,copy,hashlib,importlib.util,json,re,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent
P=ROOT/'verification/swift-guarded-snapshot-loader-work'
C=ROOT/'verification/swift-guarded-snapshot-loader-work-correction'
I=D.parent/'review';PRE=D.parent/'preaccess'
checks=[]
def check(name,yes):
    if not yes:raise AssertionError(name)
    checks.append(name)
def sha(b):return hashlib.sha256(b).hexdigest()
def put(name,data):(D/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-loader-work-correction-independent-release.json'
check('root-release',sha(release.read_bytes())=='366fc0cf92463d1c99b4f36026ae88687e02164be3d0fa7e472ef94eac00cac0')
custody=[]
for path,expected in [(C,'b7142125a8b00f0fbf9ade17d2c7697e42c1ef20d972a995dddfd452e92eff4e'),(P,'0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c'),(I,'28d14ca65eed39ac22b01f562ccc74178f3ee361c2c0a73d16e0da9b122f4be5'),(PRE,'37aaa40dcfa3cf599d35f3466d12dffc7431c5c53d689ebe7e4f388958834fa2')]:
    check('seal:'+path.name,sha((path/'seal.json').read_bytes())==expected)
    members=json.loads((path/'seal.json').read_text())['members']
    for row in members:
        data=(path/row['path']).read_bytes()
        check('member:'+path.name+':'+row['path'],len(data)==row['bytes'] and sha(data)==row['sha256'])
    custody.append(dict(path=str(path.relative_to(ROOT)),seal_sha256=expected,members=len(members)))
source=json.loads((P/'compiler-source-manifest.json').read_text())
FUND=ROOT/'verification/swift-guarded-snapshot-funding-implementation/source/vm'
OVER=ROOT/'verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm'
for row in source['members']:
    path=OVER/row['path']
    if not path.exists():path=FUND/row['path']
    b=path.read_bytes();check('source145:'+row['path'],len(b)==row['bytes'] and sha(b)==row['sha256'])
check('exact145source',len(source['members'])==145 and source['tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a')
policy=(FUND/'src/experimental/policy.rs').read_text()
check('signature-ceiling128',bool(re.search(r'pub fn parameters_per_signature\([^}]+?Self::SwiftReactorExperimentV1 => 128',policy,re.S)))
old=json.loads((P/'mir-ledger.json').read_text());new=json.loads((C/'mir-ledger.json').read_text())
X=json.loads((P/'mir-extraction.json').read_text());F=X['functions']
check('complete219same-MIR',set(old['nodes'])==set(new['nodes'])==set(F) and len(F)==219)
for key,value in old.items():
    if key not in ('nodes','standard_targets'):check('unchanged-top-level:'+key,new[key]==value)
for n,row in old['nodes'].items():
    for field,value in row.items():
        if field not in ('calls','standard_calls','callback_bound'):check('unchanged-field:'+n+':'+field,new['nodes'][n][field]==value)
def normalized(call):
    c=copy.deepcopy(call)
    for prefix in ('type-option equality closed callbacks: ','type-slice equality closed callbacks: '):
        if c['target'].startswith(prefix):c['target']=c['target'][len(prefix):]
    return c
deltas=[]
for n,row in old['nodes'].items():
    a=sorted(map(normalized,row['calls']),key=lambda c:(c['target'],c['callee'],c['multiplicity']))
    b=sorted(map(normalized,new['nodes'][n]['calls']),key=lambda c:(c['target'],c['callee'],c['multiplicity']))
    check('same-call-number:'+n,len(a)==len(b))
    for before,after in zip(a,b):
        check('same-target-and-callee:'+n,before['target']==after['target'] and before['callee']==after['callee'])
        if before['multiplicity']!=after['multiplicity']:deltas.append(dict(function=n,owner=row['owner'],before=before,after=after))
check('exact-two-width-changes',len(deltas)==2 and all(v['owner']=='wresolve' and v['before']['multiplicity']==1 and v['after']['multiplicity']==128 and v['before']['target']=='<&[Type] as PartialEq>::ne' for v in deltas))
check('407-explicit-primitive-targets',len(new['standard_targets'])==407 and len(old['standard_targets'])==403 and set(old['standard_targets'])<=set(new['standard_targets']))
check('same-Type-equality104',all(new['nodes'][v['after']['callee']]['local_actions']==104 and not new['nodes'][v['after']['callee']]['calls'] for v in deltas))

# Import only the actual receiver module: reviewed pure definitions/constants,
# no file writes. Compile just the actual pure resolver functions from the
# pricing AST, excluding every original/correction top-level effect.
spec=importlib.util.spec_from_file_location('independent_receiver',C/'receiver.py')
receiver=importlib.util.module_from_spec(spec);sys.modules[spec.name]=receiver;spec.loader.exec_module(receiver)
tree=ast.parse((C/'price_mir.py').read_text())
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('primary','target_of','resolve')]
constants={}
for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='FREE':
        constants[node.targets[0].id]=ast.literal_eval(node.value)
# METHODS contains comprehensions, so take only the unchanged original object
# expression for evaluation with an empty builtins except safe range-free data.
for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='METHODS':
        constants['METHODS']=eval(compile(ast.Expression(node.value),'<pure method table>','eval'),{'__builtins__':{}},{})
byowner=collections.defaultdict(list)
for n,f in F.items():
    if '{closure#' not in n:byowner[f['owner']].append(n)
ns=dict(F=F,BYOWNER=byowner,re=re,classify_partial_eq=receiver.classify_partial_eq,**constants)
exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual pure resolver functions>','exec'),ns)
resolver=ns['resolve'];target_of=ns['target_of'];classify=receiver.classify_partial_eq
actual_dispatch=[]
for n,f in F.items():
    for st in f['calls']:
        target=target_of(st)
        if 'PartialEq' not in target:continue
        d=classify(target);actual_dispatch.append(dict(function=n,target=target,**d.__dict__))
        check('actual-equality-classified:'+target,d is not None)
        if d.kind=='authored-scalar':
            callee=resolver(target);check('exact-scalar-resolves',callee is not None and '_1: &'+d.authored_type+',' in F[callee]['head'])
        else:check('wrapped-and-primitive-not-scalar-substitution',resolver(target) is None)
        if d.kind in ('type-slice','type-option'):
            edge=[c for c in new['nodes'][n]['calls'] if c['target']==d.kind+' equality closed callbacks: '+target]
            expected=128 if target=='<&[Type] as PartialEq>::ne' else 1
            check('actual-wrapper-count:'+target,d.callbacks==expected)
            check('actual-wrapper-edge:'+target,bool(edge) and all(c['multiplicity']==expected and '_1: &Type,' in F[c['callee']]['head'] for c in edge))
for target,kind,width in [('<Type as PartialEq>::eq','authored-scalar',1),('<Option<Type> as PartialEq>::eq','type-option',1),('<&[Type] as PartialEq>::eq','type-slice',128),('<&[Type] as PartialEq<[Type; 1]>>::eq','type-slice',1),('<&[u8] as PartialEq>::ne','primitive',0)]:
    d=classify(target);check('independent-classifier-regression:'+target,(d.kind,d.callbacks)==(kind,width))
unknowns=['<Vec<Type> as PartialEq>::eq','<Option<&Type> as PartialEq>::eq','<OtherType as PartialEq>::eq','<&[Type] as PartialEq<[Type; 2]>>::eq','<&[Type] as PartialEq<[Type; N]>>::eq','<&[Type; 128] as PartialEq>::eq','<Type as PartialEq<Option<Type>>>::eq','<Type as NotPartialEq>::eq','<Option<Option<Type>> as PartialEq>::eq']
for target in unknowns:
    try:resolver(target)
    except receiver.UnsupportedReceiver:checks.append('actual-tool-unknown-fails:'+target)
    else:raise AssertionError('unknown receiver accepted:'+target)
check('scalar-substring-branch-removed','any(t in target' not in ast.get_source_segment((C/'price_mir.py').read_text(),next(n for n in functions if n.name=='resolve')))
put('receiver-and-edge-review.json',dict(actual_dispatches=actual_dispatch,numeric_edges=deltas,unknown_receiver_controls=unknowns,executed='Only receiver.py pure definitions plus AST-extracted primary/target_of/resolve. No top-level pricing/custody/verification/freeze script executed.'))

# Independent acyclic expansion, preserving all exact original/native terms.
g=json.loads((C/'cap-geometry.json').read_text());U64=2**64-1
variables=dict(source=g['source'],validator_source=g['validator_source'],maximum_file=max(g[k] for k in ('source','executable','build','session')),allocation_cap=max(g['metadata'],g['scratch']),read_buffer=4096)
variables['retained_visits']=(variables['maximum_file']+4095)//4096+1
def totals(ledger):
    cache={};seen=set()
    def expand(n,mode,stack=()):
        if n not in ledger['nodes']:raise ValueError('unknown callee')
        if n in stack:raise ValueError('cycle')
        if mode=='wrapper' and n==ledger['roots']['validator']:return 0
        key=(n,mode)
        if key in cache:return cache[key]
        row=ledger['nodes'][n];seen.add(n);value=row['local_actions']
        for term in row['native']:value+=term['count']*(variables[term['extent']] if isinstance(term['extent'],str) else term['extent'])
        for call in row['calls']:value+=call['multiplicity']*expand(call['callee'],mode,stack+(n,))
        repeat=row['repeat'] if mode=='wrapper' else row.get('validator_fixed_repeat',1)
        value*=variables[repeat] if isinstance(repeat,str) else repeat
        check('checked-independent-intermediate',0<value<=U64);cache[key]=value;return value
    wrapper=expand(ledger['roots']['loader'],'wrapper');coefficient=expand(ledger['roots']['validator'],'validator')
    check('all219-reachable',len(seen)==219);return wrapper,coefficient
a=totals(old);b=totals(new)
check('fixed-wrapper',a[0]==b[0]==97394558768720)
check('exact-coefficient-delta',a[1]==1747993923 and b[1]==1748020339 and b[1]-a[1]==2*127*104==26416)
numeric=[]
for B in (0,1,2,31,32,33,4095,4096,512000000):
    oldW=a[0]+(B+1)*a[1];newW=b[0]+(B+1)*b[1]
    check('positive-delta-and-u64-grid:'+str(B),newW-oldW==(B+1)*26416 and newW<=U64)
    numeric.append(dict(B=B,old=oldW,corrected=newW,delta=newW-oldW))
check('corrected-exact-cap',numeric[-1]['corrected']==895083809874789059 and numeric[-1]['delta']==13524992026416)
for name in ('quote.py','mir_quote.py'):check('pure-evaluator-unchanged:'+name,(C/name).read_bytes()==(P/name).read_bytes())
sys.path.insert(0,str(C))
from quote import Geometry,Refused,add,mul
from mir_quote import evaluate
geometry=Geometry(**g)
check('actual-pure-evaluator-matches-independent',evaluate(geometry,new)['W_loader']==numeric[-1]['corrected'])
for label,modify in [('unknown',lambda q:q['roots'].update(loader='UNKNOWN')),('cycle',lambda q:q['nodes'][q['roots']['loader']]['calls'].append(dict(target='negative',callee=q['roots']['loader'],multiplicity=1)))]:
    q=copy.deepcopy(new);modify(q)
    try:evaluate(geometry,q)
    except Refused:checks.append('pure-refuses-'+label)
    else:raise AssertionError('pure accepted '+label)
for label,fn in [('overflow-add',lambda:add(U64,1)),('overflow-mul',lambda:mul(U64,2))]:
    try:fn()
    except Refused:checks.append(label)
    else:raise AssertionError('overflow accepted')
q=copy.deepcopy(new)
for n in [v['function'] for v in deltas]:
    for c in q['nodes'][n]['calls']:
        if c['target'].endswith('<&[Type] as PartialEq>::ne'):c['multiplicity']=1
check('counterfactual-old-W-restored',evaluate(geometry,q)['W_loader']==numeric[-1]['old'])
check('counterfactual-rejected-by-independent-width-rule',any(c['multiplicity']!=128 for r in q['nodes'].values() for c in r['calls'] if c['target'].endswith('<&[Type] as PartialEq>::ne')))
prior=json.loads((I/'receipt.json').read_text());prior_native=json.loads((I/'native-audit.json').read_text())
check('prior-projection-and-native-pass-bound',prior['checks_passed']==21227 and prior_native['checks_passed']==320)
projection=json.loads((I/'projected-value-ledger.json').read_text())
check('all1456-sites-and37stores-composed',len(projection['all_dereference_statements'])==1456 and len(projection['projected_stores'])==37)
put('numeric-and-composition.json',dict(wrapper=b[0],validator_coefficient=b[1],W_loader=numeric[-1]['corrected'],coefficient_delta=26416,cap_delta=13524992026416,credit_grid=numeric,prior_review_seal_sha256=custody[2]['seal_sha256'],prior_value_sites=1456,prior_stores=37,prior_partition_cases=972,prior_native_controls=320,native_reallocated=False,source145_only=True,host11=True,operational_grant=False))
put('receipt.json',dict(schema=1,status='independently-accepted-source145-loader-work-component-only',command='python3 verification/swift-guarded-snapshot-loader-work-independent/correction-review/audit.py',python=sys.version,checks_passed=len(checks),custody=custody,source_tree=source['tree_sha256'],preaccess_and_review_unchanged=True,executed='pure independent graph/numeric/regression models and actual pure receiver/resolver functions only',frozen_write_effect_scripts_replayed=False,compiler_execution=False,product_execution=False,native_UI_capture='paused and not used',global_process_inventory=False,cleanup='Owned pure Python process completes; no native/compiler/runtime child created; bytecode writes disabled.',acceptance_scope='Frozen corrected source145/host11 loader logical-source/call/requested-native-byte work component composed with original fixed-source value, loop and native audit.',pending=['source146 final quote/descriptor/caller/fixture rebinding','P0 and P2-P5 components and complete host enforcement','native/device/UI/runtime and final physical acceptance','OTA/FieldLog/store/operational/GA evidence'],operational_grant=False))
print(json.dumps(dict(checks=len(checks),same_MIR_definitions=219,corrected_slice_widths=[128,128],coefficient=b[1],W_loader=numeric[-1]['corrected'],delta=numeric[-1]['delta'],accepted_scope='frozen source145 component only')))
