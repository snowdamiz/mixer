#!/usr/bin/env python3
"""Independent fixed-source/MIR value and finite-bound review. No product execution."""
from pathlib import Path
import collections, copy, gzip, hashlib, json, re, sys, time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
P = ROOT / 'verification/swift-guarded-snapshot-loader-work'
FUND = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
OVER = ROOT / 'verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm'
U64 = 2**64-1
checks=[]
def check(name, yes):
    if not yes: raise AssertionError(name)
    checks.append(name)
def sha(b): return hashlib.sha256(b).hexdigest()
def put(name, value): (D/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
check('producer-seal',sha((P/'seal.json').read_bytes())=='0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c')
release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-loader-work-independent-release.json'
check('root-explicit-release',sha(release.read_bytes())=='421fba546509dabdd6001b41590fc27019ce64508d982be4f2d0202e06e31c9d')
seal=json.loads((P/'seal.json').read_text())
for row in seal['members']:
    b=(P/row['path']).read_bytes()
    check('sealed-member:'+row['path'],len(b)==row['bytes'] and sha(b)==row['sha256'])
pre=D.parent/'preaccess'
check('preaccess-seal-unchanged',sha((pre/'seal.json').read_bytes())=='37aaa40dcfa3cf599d35f3466d12dffc7431c5c53d689ebe7e4f388958834fa2')
for row in json.loads((pre/'seal.json').read_text())['members']:
    check('preaccess-member:'+row['path'],sha((pre/row['path']).read_bytes())==row['sha256'])
manifest=json.loads((P/'compiler-source-manifest.json').read_text())
sources={}
for row in manifest['members']:
    path=OVER/row['path']
    if not path.exists():path=FUND/row['path']
    b=path.read_bytes();sources[row['path']]=b.decode()
    check('source-member:'+row['path'],len(b)==row['bytes'] and sha(b)==row['sha256'])
check('source145-exact',len(manifest['members'])==145 and manifest['tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a')
raw=gzip.decompress((P/'whole-source.mir.gz').read_bytes())
selected=gzip.decompress((P/'selected-definitions.mir.gz').read_bytes())
X=json.loads((P/'mir-extraction.json').read_text());L=json.loads((P/'mir-ledger.json').read_text())
check('whole-MIR-exact',len(raw)==73052563 and sha(raw)=='eb7d6cc19af68fdbc83b2813e9bbddd35b1d431f634b52b1d5e4e61c6cc4e7f4')
check('selected-MIR-exact',sha(selected)==X['selected_sha256'] and len(selected)==X['selected_bytes'])
definitions=[]
text=selected.decode()
for m in re.finditer(r'^fn ',text,re.M):
    body=text[m.start():text.index('\n}\n',m.start())+3]
    definitions.append(body)
    check('complete-definition-in-whole:'+str(len(definitions)),raw.count(body.encode())==1)
check('219-complete-definitions',len(definitions)==len(X['functions'])==len(L['nodes'])==219)
for n,f in X['functions'].items():
    check('definition-fingerprint:'+n,sum(sha(b.encode())==f['sha256'] for b in definitions)==1)

# Independent source-visible shapes. Actual Rust field type strings are read
# from the frozen source, rather than importing the producer's numeric FIELDS.
struct_paths={
 'SwiftValidationBudget':'src/experimental/swift.rs','SwiftValidationUsage':'src/experimental/swift.rs',
 'SwiftValidationFailure':'src/experimental/swift.rs','SwiftReactorObservations':'src/experimental/swift.rs',
 'ValidatedSwiftReactor':'src/experimental/swift.rs',
 'ValidationBudget':'src/experimental/mod.rs','Usage':'src/experimental/mod.rs','Failure':'src/experimental/mod.rs',
 'Cursor':'src/experimental/account.rs','BodyObservations':'src/experimental/account.rs','SwiftControl':'src/experimental/account.rs',
 'Meter':'src/experimental/account.rs','Buffer':'src/experimental/account.rs',
 'Span':'src/experimental/metadata.rs','Signature':'src/experimental/metadata.rs','Import':'src/experimental/metadata.rs',
 'Function':'src/experimental/metadata.rs','Global':'src/experimental/metadata.rs','Export':'src/experimental/metadata.rs',
 'Segment':'src/experimental/metadata.rs','SwiftDeclaration':'src/experimental/metadata.rs','Metadata':'src/experimental/metadata.rs',
 'Reader':'src/experimental/reader.rs','Control':'src/experimental/validate.rs','BodyState':'src/experimental/validate.rs',
}
for name in ('FileIdentityV1','LoaderUsageV1','LoaderFailureV1','ReturnedLoaderFilesV1','LoaderProvenanceV1','SelectedValidatedProfileV1','LoaderOutcomeV1','ProcessObservationV1','Section','BuildView','SessionView'):
    struct_paths[name]='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
fields={}
for name,path in struct_paths.items():
    match=re.search(r'\bstruct '+name+r'\b[^\{;]*\{([^}]+)\}',sources[path],re.S)
    check('source-struct-found:'+name,match is not None)
    body=re.sub(r'//[^\n]*','',match[1])
    fields[name]=re.findall(r'(?:^|\n)\s*(?:pub(?:\([^)]*\))?\s+)?([a-zA-Z_][a-zA-Z_0-9]*):\s*([^\n]+?),\s*(?=\n|$)',body)
    check('source-fields-nonempty:'+name,bool(fields[name]))
def split(s,sep=','):
    depth=0;start=0;out=[]
    for i,c in enumerate(s):
        if c in '<[(':depth+=1
        elif c in '>])':depth-=1
        elif c==sep and depth==0:out.append(s[start:i].strip());start=i+1
    out.append(s[start:].strip());return out
atoms=set('Type BlockKind Profile Resource FailureKind SwiftValidationFailureKind SwiftValidationResource WasiFunction ResolveError Role Refusal TryFromIntError TryReserveError Instant Ordering Infallible bool char u8 u16 u32 u64 u128 usize i8 i16 i32 i64 i128 isize f32 f64'.split())
closures={};opaque=set()
def leaves(t,stack=()):
    t=t.strip()
    if t.startswith(('&','*')):return 1
    if t in ('()','!'):return 1
    if t.startswith('{closure@'):
        if t not in closures:raise AssertionError('unknown-closure-shape:'+t)
        return closures[t]
    if t.startswith('(') and t.endswith(')'):return sum(leaves(x,stack) for x in split(t[1:-1]) if x)
    if t.startswith('[') and t.endswith(']'):
        inner,count=split(t[1:-1],';');return leaves(inner,stack)*(16384 if count=='N' else int(count))
    base=t.split('<',1)[0].rsplit('::',1)[-1]
    inner=t[t.index('<')+1:-1] if '<' in t and t.endswith('>') else ''
    if base=='SwiftMetadata':return leaves('Metadata<SwiftDeclaration>',stack)
    if base in ('Option','Result','ControlFlow'):return 1+max(leaves(v,stack) for v in split(inner))
    if base in ('Range','RangeInclusive'):return 2*leaves(inner,stack)+int(base=='RangeInclusive')
    if base=='Bytes':return ({'N':16384,'PROCESS_CAP':16384,'STR_CAP':4096}.get(inner) if inner in ('N','PROCESS_CAP','STR_CAP') else int(inner))+1
    if base=='Policy':return 2 # source enum: tag plus Frozen(&Limits), max over Swift unit case
    if base in ('T','C','D'):return 6
    if base=='R':return 1 # closed loader call uses File; no arbitrary Read implementation invoked
    if base in fields:
        if base in stack:raise AssertionError('recursive-value-type:'+base)
        return sum(leaves(ty,stack+(base,)) for _,ty in fields[base])
    if base in atoms:return 1
    if t.startswith(('std::','io::','Vec<','Box<')) or base in ('TryFromIntError','TryReserveError','File'):
        opaque.add(t);return 1
    raise AssertionError('unknown-value-type:'+t)
# All closure constructors are retained; noncapturing closures have an explicit
# constructor too. Captures are fully typed materialized MIR local values.
constructors=[]
for n,f in X['functions'].items():
    for st in f['statements']:
        m=re.search(r'= (\{closure@.+?\})(?: \{(.*?)\})?;',st)
        if m:constructors.append((n,f,st,m))
pending=list(constructors)
while pending:
    next_pending=[]
    for n,f,st,m in pending:
        try:
            values=re.findall(r'\b(?:copy|move) (_\d+)\b',m[2] or '')
            total=sum(leaves(f['locals'][v]) for v in values)
            closures[m[1]]=max(1,total)
        except AssertionError as error:
            if 'unknown-closure-shape' not in str(error):raise
            next_pending.append((n,f,st,m))
    check('closure-shape-progress:'+str(len(pending)),len(next_pending)<len(pending) or not next_pending)
    pending=next_pending
shapes={name:dict(source_path=path,fields=fields[name],leaves=leaves(name)) for name,path in struct_paths.items()}
shapes['Policy']=dict(source_path='src/experimental/policy.rs',leaves=2,variants=['Frozen(&Limits)','SwiftReactorExperimentV1'])
for name,expected in L['fields'].items():check('independent-source-shape:'+name,leaves(name)==sum(expected))
admitted=['u32','Type','Option<Type>','Signature','Import','Function','Global','Export','Segment','Control']
check('generic-T-six-is-real-maximum',max(leaves(t) for t in admitted)==6)
check('generic-Control-six-fields',leaves('Control')==6)
for n,f in X['functions'].items():
    for local,ty in f['locals'].items():check('known-local-shape:'+n+':'+local,leaves(ty)>=0)
check('all-captured-closure-shapes-match',all(closures[k]==v for k,v in L['closure_leaves'].items()))
check('extra-closure-shapes-are-known-noncapturing',all(v==1 for k,v in closures.items() if k not in L['closure_leaves']))
put('source-shapes.json',dict(structs=shapes,admitted_copy_types={t:leaves(t) for t in admitted},closures=closures,opaque_standard_types=sorted(opaque)))

def matching(s,start):
    opening=s[start];closing={'(':')','[':']'}[opening];depth=0
    for i in range(start,len(s)):
        if s[i]==opening:depth+=1
        if s[i]==closing:
            depth-=1
            if depth==0:return i
    raise AssertionError('unbalanced-place:'+s)
def place_at(s,start):
    end=start
    if s[end]=='(':end=matching(s,end)+1
    else:
        m=re.match(r'\**_\d+',s[end:]);check('place-token',m is not None);end+=len(m[0])
    while end<len(s) and s[end]=='[':end=matching(s,end)+1
    return s[start:end]
def place_type(s,locals_):
    s=s.strip()
    if s.endswith(']'):
        parens=0
        for i,c in enumerate(s):
            if c=='(':parens+=1
            elif c==')':parens-=1
            if c=='[' and i>0 and parens==0:
                base=place_type(s[:i],locals_)
                if base.startswith('&'):base=re.sub(r'^&(?:mut )?','',base)
                check('indexed-array-or-slice',base.startswith('['))
                return split(base[1:-1],';')[0]
    if s.startswith('(') and matching(s,0)==len(s)-1:
        inside=s[1:-1];depth=0
        for i,c in enumerate(inside):
            if c in '<[(':depth+=1
            elif c in '>])':depth-=1
            elif c==':' and depth==0 and inside[i-1:i]!=':' and inside[i+1:i+2]!=':':return inside[i+1:].strip()
        return place_type(inside,locals_)
    if s.startswith('*'):
        ty=place_type(s[1:],locals_)
        check('dereference-has-reference-type',ty.startswith(('&','*')))
        return re.sub(r'^(?:&(?:mut )?|\*(?:const |mut ))','',ty)
    if re.fullmatch(r'_\d+',s):return locals_[s]
    raise AssertionError('unclassified-place:'+s)

roster=[];categories=collections.Counter();stores=[];nondest=[];smallest_margin=None
for n,f in X['functions'].items():
    for st in f['statements']:
        if '*_' not in st:continue
        mentions=re.findall(r'\b_\d+\b',st)
        paid=2*sum(leaves(f['locals'][v]) for v in mentions)
        record=dict(function=n,owner=f['owner'],statement=st,local_fetch_store_paid=paid)
        localdest=re.match(r'(_\d+) = (.*)',st)
        if localdest:
            dest,rhs=localdest.groups();width=leaves(f['locals'][dest]);record['destination_type']=f['locals'][dest]
            if rhs.startswith('&'):category='borrow/address; pointer traversal only'
            elif rhs.startswith('discriminant('):category='discriminant/tag only'
            elif rhs.startswith(('copy ','no_retag copy ')):
                category='typed value read' if rhs.startswith('copy ') else 'no_retag reference value read'
                at=rhs.index('copy ')+5;place=place_at(rhs,at);ty=place_type(place,f['locals'])
                check('copy-type-width:'+n+':'+dest,leaves(ty)==width)
                record.update(read_place=place,read_type=ty,required_transfer=2*width)
                check('deref-read-total-covered:'+n+':'+dest,paid>=2*width)
                margin=paid-2*width;smallest_margin=margin if smallest_margin is None else min(smallest_margin,margin)
            elif rhs.startswith(('AddWithOverflow(','SubWithOverflow(')):
                category='scalar overflow rvalue'
                for m in re.finditer(r'\b(?:copy|move) ',rhs):
                    ty=place_type(place_at(rhs,m.end()),f['locals']);check('scalar-overflow-operands',leaves(ty)==1)
            else:raise AssertionError('unclassified-deref-rvalue:'+st)
        elif ' = ' in st:
            category='projected store';lhs,rhs=st.split(' = ',1);destty=place_type(lhs,f['locals'])
            if rhs.startswith('const '):
                check('only-scalar-constant-projected-stores',leaves(destty)==1);required=1
            else:
                m=re.match(r'(?:move|copy) ',rhs);check('store-materialized-value',m is not None)
                value=place_at(rhs,m.end());srcty=place_type(value,f['locals'])
                check('projected-store-value-width',leaves(destty)==leaves(srcty));required=2*leaves(destty)
                record.update(value_place=value,value_type=srcty)
            record.update(destination_type=destty,required_transfer=required)
            check('projected-store-total-covered',paid>=required);stores.append(record)
        elif st.startswith(('assert(','switchInt(')):
            category='scalar assert/switch read'
            for m in re.finditer(r'\b(?:copy|move) ',st):
                place=place_at(st,m.end());ty=place_type(place,f['locals']);check('nonassignment-read-scalar',leaves(ty)==1)
            nondest.append(record)
        elif st.startswith('drop('):
            category='closed opaque standard-resource drop'
            dropped=place_at(st,5);ty=place_type(dropped,f['locals'])
            check('only-opaque-File-owner-deref-drop',ty=='std::option::Option<std::fs::File>')
            check('opaque-owner-drop-value-covered',paid>=leaves(ty))
            record.update(dropped_place=dropped,dropped_type=ty,required_transfer=leaves(ty))
        else:raise AssertionError('unclassified-nonassignment-deref:'+st)
        record['category']=category;roster.append(record);categories[category]+=1
check('all1456-deref-statements-classified',len(roster)==1456)
check('all37-projected-stores-classified',len(stores)==37)
byvalue_projected=[]
for n,f in X['functions'].items():
    for st in f['calls']:
        # Call operands that move/copy aggregate values are materialized locals;
        # references taken earlier are primitive one-place addresses.
        for m in re.finditer(r'\b(?:copy|move) ',st):
            place=place_at(st,m.end())
            if not re.fullmatch(r'_\d+',place):byvalue_projected.append((n,st,place))
check('no-direct-projected-byvalue-call-operands',not byvalue_projected)
put('projected-value-ledger.json',dict(categories=dict(categories),minimum_read_transfer_margin=smallest_margin,projected_stores=stores,all_dereference_statements=roster,byvalue_projected_call_operands=byvalue_projected,scope='actual selected219 definitions only; no generic reference-base overcoverage theorem'))

# Check exact statement-to-call edge coverage and actual closure identities,
# without executing or importing the producer's extraction/pricing scripts.
def call_target(st):
    rhs=st.split(' = ',1)[1];depth=0
    for i,c in enumerate(rhs):
        if c=='<':depth+=1
        elif c=='>' and (i==0 or rhs[i-1]!='-'):depth-=1
        elif c=='(' and depth==0:return rhs[:i]
    raise AssertionError('unknown-call-syntax:'+st)
call_roster=[];primitive_counts=collections.Counter()
for n,f in X['functions'].items():
    actual=collections.Counter(call_target(st) for st in f['calls'])
    edges=collections.defaultdict(list)
    for c in L['nodes'][n]['calls']:
        target=c['target'];callee=X['functions'][c['callee']]
        if target.startswith('Type-slice equality closed callbacks: '):
            actual_target=target.split(': ',1)[1]
            check('Type-equality-edge-is-actual',actual_target in actual and 'Type' in actual_target and 'PartialEq' in actual_target)
            check('Type-equality-exact-callback',c['multiplicity']==128 and '_1: &Type,' in callee['head'])
        else:
            check('edge-is-an-actual-callsite',target in actual)
            closure_ids=re.findall(r'\{closure@[^}]+\}',target)
            if '{closure#' in c['callee']:
                check('callback-identity-exact',any(closure in callee['head'] for closure in closure_ids))
                expected=34 if '::find::<' in target else 5 if target.startswith(('array::','std::array::')) and '::map::<' in target else 5 if f['owner']=='list' and '::any::<' in target else 4096 if '::position::<' in target or '::any::<' in target else 1
                check('callback-maximum-bounded',c['multiplicity']==expected)
            else:
                check('direct-product-single-invocation',c['multiplicity']==1)
                method=re.findall(r'::([A-Za-z_][A-Za-z_0-9]*)(?=::<|$)',target)
                method=method[-1] if method else target.split('::<',1)[0].rsplit('::',1)[-1]
                declared=callee['declared_name'].rsplit('::',1)[-1]
                check('direct-callee-method-corresponds',declared==method or (method=='ne' and declared=='eq'))
            edges[target].append(c)
    for target,count in actual.items():
        is_primitive=target in L['standard_targets']
        check('every-call-has-closed-product-or-primitive',is_primitive or target in edges)
        if is_primitive:primitive_counts[target]+=count
        else:check('each-direct-site-expanded',len(edges[target])==count)
        call_roster.append(dict(function=n,target=target,sites=count,closed_edges=edges.get(target,[]),standard_primitive=is_primitive))
check('all403-primitive-targets-attributed',dict(primitive_counts)==L['standard_targets'] and len(primitive_counts)==403)
put('call-closure-ledger.json',dict(call_sites=call_roster,primitive_targets=dict(primitive_counts),scope='fixed selected source/MIR targets; primitive implementations excluded; callbacks retained by exact compiler identities'))

# Re-expand the fixed graph independently with unbounded integers, then prove
# each nonnegative intermediate fits the explicit u64 ceiling.
g=json.loads((P/'cap-geometry.json').read_text())
vars_=dict(source=g['source'],validator_source=g['validator_source'],maximum_file=max(g[k] for k in ('source','executable','build','session')),allocation_cap=max(g['metadata'],g['scratch']),read_buffer=4096)
vars_['retained_visits']=(vars_['maximum_file']+4095)//4096+1
visiting=set();visited=set();totals={};intermediates=[]
def expand(n,mode):
    check('known-callee:'+n,n in L['nodes'])
    if mode=='wrapper' and n==L['roots']['validator']:return 0
    key=(n,mode)
    if key in totals:return totals[key]
    if key in visiting:raise AssertionError('cycle:'+n)
    visiting.add(key);visited.add(n);r=L['nodes'][n]
    local=2
    f=X['functions'][n]
    params=re.findall(r'(_\d+):',f['head'].split(' -> ',1)[0])
    local+=2*sum(leaves(f['locals'][v]) for v in params)
    for st in f['statements']:
        local+=2+sum(st.count(c) for c in '.*[]')+2*sum(leaves(f['locals'][v]) for v in re.findall(r'\b_\d+\b',st))
    check('independent-entire-local-amount:'+n,local==r['local_actions'])
    value=local
    for term in r['native']:value+=term['count']*(vars_[term['extent']] if isinstance(term['extent'],str) else term['extent'])
    for call in r['calls']:
        check('positive-call-multiplicity',type(call['multiplicity']) is int and call['multiplicity']>0)
        value+=call['multiplicity']*expand(call['callee'],mode)
    repeat=r['repeat'] if mode=='wrapper' else r.get('validator_fixed_repeat',1)
    value*=vars_[repeat] if isinstance(repeat,str) else repeat
    check('u64-expanded-intermediate:'+n,0<value<=U64)
    intermediates.append(value);visiting.remove(key);totals[key]=value;return value
wrapper=expand(L['roots']['loader'],'wrapper');coefficient=expand(L['roots']['validator'],'validator')
W=wrapper+(g['credits']+1)*coefficient
check('exact219-graph-closure',len(visited)==219)
check('exact-cap-values',(wrapper,coefficient,W)==(97394558768720,1747993923,895070284882762643))
check('final-u64',W<=U64)

# Pure checker tests import only the sealed quote modules; bytecode writes are
# disabled. Negative omission tests assert binding/attribution changes rather
# than claiming that the standalone evaluator is a generic semantic verifier.
sys.path.insert(0,str(P))
from quote import Geometry,Refused,add,mul
from mir_quote import evaluate
geometry=Geometry(**g)
check('pure-evaluator-matches-independent-graph',evaluate(geometry,L)['W_loader']==W)
negative=[]
def refusal(name,fn):
    try:fn()
    except (Refused,KeyError,TypeError):negative.append(dict(name=name,result='refused'));return
    raise AssertionError('negative-not-refused:'+name)
for label,callee in [('unknown-callee','INDEPENDENT_UNKNOWN'),('cycle',L['roots']['loader'])]:
    q=copy.deepcopy(L);q['nodes'][q['roots']['loader']]['calls'].append(dict(target='independent negative',callee=callee,multiplicity=1))
    refusal(label,lambda q=q:evaluate(geometry,q))
refusal('add-overflow',lambda:add(U64,1));refusal('multiply-overflow',lambda:mul(U64,2))
for label,owner,field,replacement in [('resolver34-omission','wresolve','calls',[]),('native-read-omission','read_attempt','native',[]),('fixed-empty-segment2-omission','vsegments','validator_fixed_repeat',1)]:
    q=copy.deepcopy(L);row=next(v for v in q['nodes'].values() if v['owner']==owner);row[field]=replacement
    changed=evaluate(geometry,q)['W_loader'];check('independent-'+label,changed!=W)
    negative.append(dict(name=label,result='changes exact sealed quote; cannot pass frozen member binding',mutated_W=changed))
partition_cases=0
for budget in range(12):
    # Arbitrary nested counts share one debit sequence. Every successful debit
    # adds at least1, and the single terminal refusal adds at most one epoch.
    for outer in range(9):
        for inner in range(9):
            demanded=outer*inner;successful=min(budget,demanded)
            terminal=int(demanded>budget)
            check('independent-credit-partition',successful+terminal<=budget+1);partition_cases+=1
check('take0-countermodel-is-not-progress',sum([0]*100)==0)
check('environment-pointer-inclusive65',len(range(65))==65)
check('environment-descending-sort2016',sum(range(64))==2016)
check('environment-while-visits2079-covered',2016+63<2080)
check('resolver34-is-present',any(c['multiplicity']==34 and '::find::<' in c['target'] for v in L['nodes'].values() for c in v['calls']))
wr=next(v for v in L['nodes'].values() if v['owner']=='wresolve' and v['native'])
slice_edges=[c for c in wr['calls'] if c['target']=='<&[Type] as PartialEq>::ne']
check('concrete-defect-two-width1-slice-edges',len(slice_edges)==2 and all(c['multiplicity']==1 for c in slice_edges))
check('concrete-defect-advertised128-is-absent',not any(c['multiplicity']==128 and 'Type' in c['target'] for v in L['nodes'].values() for c in v['calls']))
eq=slice_edges[0]['callee'];check('Type-equality-body104',L['nodes'][eq]['local_actions']==104 and not L['nodes'][eq]['calls'])
# Source-only finite countermodel: PathOpen's nine parameters all compare equal,
# then its single result compares equal. No product resolver code is executed.
descriptor=sources['src/experimental_wasi/descriptor.rs']
pathopen=re.search(r'Self::PathOpen => &\[([^]]+)\]',descriptor)[1]
pathopen_count=len(pathopen.split(','))
check('PathOpen-nine-parameters',pathopen_count==9)
callback_model=dict(parameters=pathopen_count,results=1,maximum_callbacks=pathopen_count+1,priced_callbacks=2,unattributed_callbacks=pathopen_count-1,unattributed_logical_actions=(pathopen_count-1)*104)
name_section=descriptor.split('pub fn name(self)',1)[1].split('pub fn parameters',1)[0]
names=re.findall(r'b"([^"]+)"',name_section)
check('34-authored-names-max23',len(names)==34 and max(map(len,names))==23)
native_comparison_upper=34*(4096+23)+(4096+22)
unused_native_name_bound=34*8192-native_comparison_upper
omitted_advertised_callback_bound=2*127*104
check('aggregate-scalar-slack-is-not-an-edge-fix',unused_native_name_bound>omitted_advertised_callback_bound)
put('blocking-callback-witness.json',dict(status='concrete per-operation ledger defect; candidate not independently accepted',source_path='src/experimental_wasi/descriptor.rs',source_lines=[167,185],exact_edges=slice_edges,authored_Type_equality_body=eq,body_actions=104,PathOpen_source_only_model=callback_model,advertised128_edge_present=False,why='resolve() finds Type substring inside the slice target and returns direct Type::eq first; the later128 fallback runs only if resolve(target) is None, so it is bypassed',severity_analysis=dict(native_name_bound=34*8192,source_specific_comparison_upper=native_comparison_upper,scalar_surplus=unused_native_name_bound,missing_advertised_callbacks_actions=omitted_advertised_callback_bound,scope='Scalar surplus explains that a whole-quote shortfall is not demonstrated; it does not complete or fix the named edge ledger. No slack reattribution is accepted.'),other_broad_matches=dict(Option_Type='At most one Type callback, so multiplicity1 covers the actual Option<Type> comparisons.',metadata_Type_slice_vs_array1='At most one Type callback because the authored other slice is [Type;1]; multiplicity1 covers this frozen site.',direct_Type_ne='Standard ne delegates to one authored Type equality; multiplicity1 is sufficient.')))
check('read32-plus-exit33',next(v for v in L['nodes'].values() if v['owner']=='read_attempt')['repeat']==33)
put('graph-and-controls.json',dict(wrapper=wrapper,validator_coefficient=coefficient,W_loader=W,visited_nodes=len(visited),maximum_expanded_intermediate=max(intermediates),partition_cases=partition_cases,negative_controls=negative,source_tree=manifest['tree_sha256'],operational_grant=False))
put('receipt.json',dict(schema=1,command='python3 verification/swift-guarded-snapshot-loader-work-independent/review/audit.py',python=sys.version,checks_passed=len(checks),source_tree=manifest['tree_sha256'],producer_seal_sha256=sha((P/'seal.json').read_bytes()),root_release_sha256=sha(release.read_bytes()),selected_MIR_sha256=sha(selected),whole_MIR_sha256=sha(raw),preaccess_unchanged=True,product_execution=False,compiler_execution=False,native_UI_capture='paused and not used',global_process_inventory=False,cleanup='Pure Python process completes; owned review data retained. No native, compiler, loader, VM, cache, scope, constructor or writer process started.',decision='not accepted: two Type-slice callback edges are under-attributed; direct isolated pricing correction and independent re-review required. Value/projection and custody audits pass for this fixed source.'))
print(json.dumps(dict(checks_passed=len(checks),deref_statements=len(roster),projected_stores=len(stores),partition_cases=partition_cases,W_loader=W)))
