#!/usr/bin/env python3
"""Independent host-only source/MIR/data review. Never invokes product/compiler."""
from pathlib import Path
import copy, dataclasses, gzip, hashlib, importlib.util, json, re, sys
sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
C = V / 'swift-guarded-snapshot-child-entry-cost'
COMP = V / 'swift-guarded-snapshot-host-composition'
BASE = V / 'swift-guarded-snapshot-funding-implementation/source/vm'
checks = []
def sha(b): return hashlib.sha256(b).hexdigest()
def save(name, value): (D/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def require(name, value):
    if not value: raise AssertionError(name)
    checks.append(name)
def load(p): return json.loads(p.read_text())
def canon(v): return json.dumps(v, sort_keys=True, separators=(',',':')).encode()
def checked_seal(folder, expected):
    require('seal '+folder.name, sha((folder/'seal.json').read_bytes()) == expected)
    seal = load(folder/'seal.json')
    for row in seal['members']:
        p = folder/row['path']; data = p.read_bytes()
        require('sealed member '+str(p.relative_to(R)), len(data)==row['bytes'] and sha(data)==row['sha256'])
    require('seal count '+folder.name, len(seal['members'])==seal['member_count'])
    return {'path':str(folder.relative_to(R)), 'seal_sha256':expected,
            'members':len(seal['members']), 'bytes':sum(x['bytes'] for x in seal['members'])}
release = V/'swift-semantic-adapter-root-review/guarded-snapshot-child-entry-cost-independent-release.json'
require('root review release', sha(release.read_bytes())=='6bae895fc0291495745993340de7971467944c4e5ac1ff9ca4588b80ef49ce3e')
custody = [checked_seal(C, '68638fbe90b9de726b18441d8338dd018ea2ff701133c63636a5e393f5a647c9')]
for item in load(C/'bindings.json')['custody']:
    custody.append(checked_seal(R/item['path'], item['seal_sha256']))
manifest = load(COMP/'source-manifest.json')
require('source146 canonical roster digest', sha(canon(manifest['members']))==manifest['tree_sha256']=='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185')
require('source146 loader roster identical', manifest==load(V/'swift-guarded-snapshot-loader-work-source146/source146-manifest.json'))
sources = {}
for row in manifest['members']:
    p = COMP/'overlay/vm'/row['path']
    if not p.is_file(): p=BASE/row['path']
    data=p.read_bytes()
    require('actual effective146 '+row['path'], len(data)==row['bytes'] and sha(data)==row['sha256'])
    sources[row['path']]=data.decode()
hosts=load(COMP/'host-support-manifest.json')
require('host11 roster digest',len(hosts['members'])==11 and sha(canon(hosts['members']))==hosts['tree_sha256'])
for row in hosts['members']:
    b=(V/'swift-real-profile-loader-binding/host'/row['path']).read_bytes()
    require('host11 '+row['path'],len(b)==row['bytes'] and sha(b)==row['sha256'])
prior = V/'swift-guarded-snapshot-loader-work-independent/review'
require('prior shape seal',sha((prior/'seal.json').read_bytes())=='28d14ca65eed39ac22b01f562ccc74178f3ee361c2c0a73d16e0da9b122f4be5')
prior_row=next(x for x in load(prior/'seal.json')['members'] if x['path']=='source-shapes.json')
require('prior shape bytes',sha((prior/'source-shapes.json').read_bytes())==prior_row['sha256'])

# Declaration parser is independently authored; old shapes supply only a roster
# and source paths. Every field and enum payload is read anew from frozen146.
def separate(text, delimiter=','):
    depth=0; result=[]; start=0
    for i,c in enumerate(text):
        if c in '[({<': depth+=1
        elif c in '])}>': depth-=1
        if c==delimiter and depth==0:
            result.append(text[start:i].strip()); start=i+1
    result.append(text[start:].strip())
    return [x for x in result if x]
def matching(text, pos, opening='{', closing='}'):
    count=1
    for i in range(pos+1,len(text)):
        if text[i]==opening: count+=1
        if text[i]==closing: count-=1
        if count==0:return i
    raise ValueError('unbalanced frozen declaration')
def strip_comments(t):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', t, flags=re.S)
def fields(text):
    result=[]
    for f in separate(text):
        f=re.sub(r'#\[[^]]*\]\s*','',f)
        f=re.sub(r'^pub(?:\([^)]*\))?\s+','',f)
        name,ty=f.split(':',1);result.append([name.strip(),ty.strip()])
    return result
def declaration(name, path):
    text=strip_comments(sources[path])
    found=list(re.finditer(r'\b(struct|enum)\s+'+re.escape(name)+r'\b',text))
    require('single actual declaration '+name,len(found)==1)
    m=found[0]; left=text.index('{',m.end()); right=matching(text,left)
    body=text[left+1:right]
    if m[1]=='struct':return {'fields':fields(body),'source_path':path}
    variants=[]
    for part in separate(body):
        part=re.sub(r'#\[[^]]*\]\s*','',part)
        vn=re.match(r'\w+',part)[0]
        if '{' in part: ts=[t for _,t in fields(part[part.index('{')+1:part.rindex('}')])]
        elif '(' in part:ts=separate(part[part.index('(')+1:part.rindex(')')])
        else: ts=[]
        variants.append({'name':vn,'types':ts})
    return {'variants':variants,'source_path':path}
old=load(prior/'source-shapes.json')['structs']
shapes={n:declaration(n,x['source_path']) for n,x in old.items()}
new=load(C/'source-shapes.json')['new_shapes']
for n,x in new.items():
    path=x['origin']['path']; rel=path.split('/vm/',1)[1] if '/vm/' in path else path
    shapes[n]=declaration(n,rel)
    for key in ('fields','variants'):
        if key in x: require('actual new source shape '+n, shapes[n][key]==x[key])
for n,x in old.items():
    if 'fields' in x:require('actual inherited source fields '+n,shapes[n]['fields']==x['fields'])
scalar=set('bool char u8 u16 u32 u64 u128 usize i8 i16 i32 i64 i128 isize f32 f64 Instant Type BlockKind Profile Resource FailureKind SwiftValidationFailureKind SwiftValidationResource WasiFunction ResolveError Role Refusal TryFromIntError TryReserveError'.split())
aliases={'SwiftMetadata':'Metadata','Stop':'SnapshotStopV1','AError':'SnapshotAdmissionErrorV1'}
def width(ty, active=()):
    ty=ty.strip()
    if ty.startswith(('&','*')):return 1
    if ty in ('()','!'):return 1
    if ty.startswith('('):return sum(width(x,active) for x in separate(ty[1:-1]))
    if ty.startswith('['):
        t,n=separate(ty[1:-1],';');return int(n)*width(t,active)
    base=ty.split('<',1)[0].split('::')[-1]
    inner=ty.split('<',1)[1][:-1] if '<' in ty else ''
    base=aliases.get(base,base)
    if base in ('Option','Result','ControlFlow'):return 1+max(width(x,active) for x in separate(inner))
    if base in ('Range','RangeInclusive'):return 2*width(inner,active)+(base=='RangeInclusive')
    if base=='Bytes': return int(inner)+1
    if base in ('T','C','D'):return 6
    if base in scalar or base=='Cancellation':return 1
    if base in active:raise ValueError('value cycle')
    if base in shapes:
        s=shapes[base]
        if 'fields' in s:return sum(width(t,active+(base,)) for _,t in s['fields'])
        return 1+max(sum(width(t,active+(base,)) for t in v['types']) for v in s['variants'])
    if ty.startswith(('std::','io::','Vec<','Box<','Arc<')) or base in ('File','OpenOptions'):return 1
    raise ValueError('unknown type '+ty)
for name in new:require('independent new leaf total '+name,width(name)==new[name]['leaves'])

mir=gzip.decompress((C/'selected-six.mir.gz').read_bytes()).decode()
require('selected MIR digest',sha(mir.encode())==load(C/'bindings.json')['selected_MIR_sha256'])
entry=gzip.decompress((V/'swift-guarded-snapshot-host-composition-independent/entry-and-account.mir.gz').read_bytes()).decode()
whole=gzip.decompress((V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz').read_bytes()).decode()
require('entry original MIR',sha(entry.encode())==load(C/'bindings.json')['entry_and_account_MIR_sha256'])
require('helper original whole MIR',sha(whole.encode())==load(C/'bindings.json')['helper_whole_MIR_sha256'])
functions={}; declared=list(re.finditer(r'^fn .+',mir,re.M))
names=['setup_files_once_v1','copy_claims_v1','run_prepaid_fixture_v1','invoke_loaded_leaf_once_v1','cancellation_default','cancellation_clone']
L=load(C/'ledger.json')
typed_reads=[];drop_visits=[]
for index,m in enumerate(declared):
    name=names[index]; body=mir[m.start():mir.index('\n}\n',m.start())+3]
    origin=entry if index<4 else whole
    require('complete original MIR body '+name,body in origin)
    types={x[1]:x[2].strip() for x in re.finditer(r'^\s*let (?:mut )?(_\d+): ([^\n]+?);\s*(?://.*)?$',body,re.M)}
    signature=body.splitlines()[0]; args=signature[signature.index('(')+1:signature.rindex(') -> ')]
    param=[]
    for arg in separate(args):
        var,ty=arg.split(': ',1);types[var]=ty;param.append(var)
    blocks={}; current=None
    for raw in body.splitlines():
        line=raw.split(' // ',1)[0].strip()
        match=re.fullmatch(r'(bb\d+)( \(cleanup\))?: \{',line)
        if match: current=match[1];blocks[current]={'cleanup':bool(match[2]),'statements':[]};continue
        if raw=='    }':current=None
        if current and line:blocks[current]['statements'].append(line)
    statements=[s for b in blocks.values() for s in b['statements']]
    require('all local types independent '+name,types==L['functions'][name]['local_types'])
    require('all statements independent '+name,statements==L['functions'][name]['statements'])
    parts={'parameter_leaf_fetch_store':2*sum(width(types[x]) for x in param),
           'local_leaf_fetch_store':sum(2*width(types[x]) for s in statements for x in re.findall(r'\b_\d+\b',s)),
           'primitive_control_projection':sum(2+sum(s.count(c) for c in '.*[]') for s in statements)}
    require('independent parts '+name,parts==L['functions'][name]['parts'])
    own=2+sum(parts.values())
    require('independent local work '+name,own==L['functions'][name]['local_actions'])
    for block,b in blocks.items():
        for s in b['statements']:
            for target in re.findall(r'\bbb\d+\b',s):require('closed CFG '+name+':'+block+':'+target,target in blocks)
            if s.startswith('drop('):drop_visits.append({'function':name,'block':block,'statement':s,'repeat':6 if index==0 else 1})
            if re.match(r'_\d+ = copy ',s) and '*_' in s:
                destination=s.split(' = ',1)[0]
                rhs=s.split(' = copy ',1)[1]
                # Indexed paths copy one reference; typed direct fields copy
                # arrays or complete validator/product budgets.
                annotation=re.search(r': (.+)\)',rhs)
                pointee=types[destination] if '])[' in rhs else annotation[1]
                require('typed deref value agrees '+name+':'+destination,width(pointee)==width(types[destination]))
                paid=2*sum(width(types[x]) for x in re.findall(r'\b_\d+\b',s))
                need=2*width(pointee)
                require('dereference transfer paid '+name+':'+destination,paid>=need)
                typed_reads.append({'function':name,'destination':destination,'statement':s,'value_type':pointee,'required_fetch_store_actions':need,'paid_mention_actions':paid})
    functions[name]={'local_count':len(types),'local_actions':own,'parts':parts,'blocks':blocks}
require('six complete bodies',len(functions)==6)

# Resolve actual calls independently from the full MIR statements, then prove
# the only control-flow recurrence is the source-bounded setup iterator.
expected_calls={
 'setup_files_once_v1':[
  '<std::ops::Range<usize> as IntoIterator>::into_iter',
  '<std::ops::Range<usize> as Iterator>::next',
  'std::fs::File::open::<&Path>','OpenOptions::new','OpenOptions::write',
  'OpenOptions::create_new','OpenOptions::open::<&Path>'],
 'copy_claims_v1':[],
 'run_prepaid_fixture_v1':['setup_files_once_v1','<execute::Cancellation as Default>::default',
  'load_selected_retained_profile_v1','copy_claims_v1','Instant::now',
  '<execute::Cancellation as Clone>::clone','invoke_loaded_leaf_once_v1'],
 'invoke_loaded_leaf_once_v1':['run_one_loaded_fixture_v1'],
 'cancellation_default':['<Arc<Atomic<bool>> as Default>::default'],
 'cancellation_clone':['<Arc<Atomic<bool>> as Clone>::clone'],
}
call_inventory={}; cfg_cycles={}
for name,f in functions.items():
    calls=[]; graph={}
    for block,b in f['blocks'].items():
        graph[block]=set()
        for s in b['statements']:
            graph[block].update(re.findall(r'\bbb\d+\b',s))
            if ') -> [' in s and ' = ' in s:
                expr=s.split(' = ',1)[1].split(' -> [',1)[0]
                depth=0
                for i in range(len(expr)-1,-1,-1):
                    if expr[i]==')':depth+=1
                    elif expr[i]=='(':
                        depth-=1
                        if depth==0:break
                calls.append(expr[:i])
    require('all actual callees '+name,calls==expected_calls[name])
    require('candidate callee inventory '+name,calls==[x['target'] for x in L['functions'][name]['calls']])
    call_inventory[name]=calls
    # A node is cyclic exactly when it can reach itself via one or more edges.
    cyclic=[]
    for start in graph:
        pending=list(graph[start]);visited=set()
        while pending:
            node=pending.pop()
            if node==start:cyclic.append(start);break
            if node in visited:continue
            visited.add(node);pending.extend(graph[node])
    cfg_cycles[name]=cyclic
    if name!='setup_files_once_v1':require('acyclic complete CFG '+name,not cyclic)
    else:
        require('setup sole iterator recurrence','bb2' in cyclic and all(not f['blocks'][b]['cleanup'] for b in cyclic))
        require('setup back edge source-bounded','goto -> bb2;' in f['blocks']['bb20']['statements'])
        require('setup no unclassified repeat',all(int(b[2:]) in set(range(2,6))|set(range(7,21)) for b in cyclic))
save('callee-control-review.json',{'actual_calls':call_inventory,'cyclic_blocks':cfg_cycles,
 'setup_recurrence_bound':'source Range0..5 allows five successful Some observations and a sixth None; early failure/unwind has no retry entry',
 'all_success_refusal_unwind_blocks_retained':True,
 'standard_opaque_primitive_internals_are_not_CPU_or_runtime_prices':True})
require('188 source-object roles',sum(functions[n]['local_count'] for n in names[:4])==188)
native=load(V/'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')
native_bytes=sum(native['actual_type_sizes'][ty] for n in names[:4] for ty in L['functions'][n]['local_types'].values())
require('76696 source-object byte attribution',native_bytes==76696)
require('12 actual typed dereference copies',len(typed_reads)==12)
require('eight actual32byte arrays',sum(r['required_fetch_store_actions']==64 for r in typed_reads)==8)
require('validator5 and product17 leaves',sorted(r['required_fetch_store_actions'] for r in typed_reads)==[2,2,10,34]+[64]*8)
require('53 conservative payload visits',sum(x['repeat'] for x in drop_visits)==53)
require('7 setup plus11 caller payload sites',sum(x['function']==names[0] for x in drop_visits)==7 and sum(x['function']==names[2] for x in drop_visits)==11)
local={n:x['local_actions'] for n,x in functions.items()}
core=local['run_prepaid_fixture_v1']+6*local['setup_files_once_v1']+sum(local[n] for n in ['copy_claims_v1','invoke_loaded_leaf_once_v1','cancellation_default','cancellation_clone'])
require('119922 expanded source core',core==119922==L['complete_four_plus_helpers_source_work'])

profile=sources['src/experimental_swift_reactor/cache/initial_profile_v1.rs']
require('actual single finite range', 'for stage in 0..5 {' in profile)
require('actual no truncation setup', 'OpenOptions::new().write(true).create_new(true).open(binding.paths[stage])' in profile)
require('original five-limit transfer preserved','binding.original_validation_budget, &cancellation' in profile)
require('actual product budget transfer preserved','selected, binding.product_budget, Instant::now(), cancellation.clone()' in profile)
prefix_controls=[]
for stop in range(6):
    for unwind in (False,True):
        attempts=min(stop+1,5) if stop<5 else 5
        observations=attempts if stop<5 else 6
        require('prefix counts '+str((stop,unwind)),attempts<=5 and observations<=6)
        prefix_controls.append({'first_failure_or_success_endpoint':stop,'unwind':unwind,'attempts':attempts,'iterator_observations':observations,'read_attempts':min(attempts,3),'write_create_new_attempts':max(attempts-3,0)})

# Import only the reviewed pure arithmetic interface, never producer runners.
spec=importlib.util.spec_from_file_location('reviewed_child_quote',C/'quote.py')
q=importlib.util.module_from_spec(spec);sys.modules[spec.name]=q;spec.loader.exec_module(q)
valid=q.RequiredCuts((1,2,3,4,4097),(2,3,4,5,4098),(3,4,5,6,4099),7,8,9,10,11,12)
result=q.evaluate(valid)
require('independent formula',result['entry_shell_work']==119922+24+sum(valid.path_native_request_bytes)+7+53*9)
require('external cuts separate',result['arithmetic_sum_with_external_cuts']==result['entry_shell_work']+10+11+12)
require('no grant after arithmetic',not any(result[k] for k in ('root_bindings_verified','complete_component_accepted','whole_quote','operational_grant')))
def rejects(label, func):
    try:func()
    except (q.Refused,TypeError,ValueError):checks.append('refused '+label);return
    raise AssertionError('accepted hostile control '+label)
for f in dataclasses.fields(q.RequiredCuts):
    require('no default '+f.name,f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING)
    for bad in (None,True,False,-1,0,2**64,1.5,'1'):
        if f.name in ('path_bytes','path_native_request_bytes','p0_path_backing_bytes'):
            for i in range(5):
                arr=list(getattr(valid,f.name));arr[i]=bad
                rejects(f.name+str(i)+repr(bad),lambda f=f,arr=arr:q.evaluate(dataclasses.replace(valid,**{f.name:tuple(arr)})))
        else:rejects(f.name+repr(bad),lambda f=f,bad=bad:q.evaluate(dataclasses.replace(valid,**{f.name:bad})))
    rejects('omitted '+f.name,lambda f=f:q.RequiredCuts(**{x.name:getattr(valid,x.name) for x in dataclasses.fields(valid) if x!=f}))
for field in ('path_bytes','path_native_request_bytes','p0_path_backing_bytes'):
    for wrong in ((),(1,)*4,(1,)*6,None,1,'12345'):
        rejects('cardinality '+field+repr(wrong),lambda field=field,wrong=wrong:q.evaluate(dataclasses.replace(valid,**{field:wrong})))
for i in range(5):
    for f in ('path_native_request_bytes','p0_path_backing_bytes'):
        arr=list(getattr(valid,f));arr[i]=valid.path_bytes[i]-1
        rejects('uncovered '+f+str(i),lambda f=f,arr=arr:q.evaluate(dataclasses.replace(valid,**{f:tuple(arr)})))
for n in (4096,4097,65536,2**32):
    val=dataclasses.replace(valid,path_bytes=(n,)*5,path_native_request_bytes=(n,)*5,p0_path_backing_bytes=(n,)*5)
    require('no unproved4096 cap '+str(n),q.evaluate(val)['entry_shell_work']==119922+24+5*n+7+53*9)
for f in ('during_entry_payload_drop_work','loader_payload_work','leaf_payload_work','returned_outcome_payload_drop_work','io_error_native_request_bytes'):
    rejects('u64 total overflow '+f,lambda f=f:q.evaluate(dataclasses.replace(valid,**{f:2**64-1})))
for a in (0,1,2,53,2**32,2**64-1):
    for b in (0,1,2,53,2**32,2**64-1):
        for op,fn in (('add',q.add),('mul',q.mul)):
            exact=a+b if op=='add' else a*b
            if exact>2**64-1:rejects('checked '+str((op,a,b)),lambda fn=fn,a=a,b=b:fn(a,b))
            else:require('exact '+str((op,a,b)),fn(a,b)==exact)
for n in names:
    mutant=copy.deepcopy(L);del mutant['functions'][n]
    rejects('missing function '+n,lambda mutant=mutant:q.evaluate(valid,mutant))
for tag in ('native_allocation','alignment','clone','repeat','unknown_callee','cycle','drop_count'):
    mutant=copy.deepcopy(L)
    if tag=='native_allocation':mutant['requested_Cancellation_allocation_bytes']=0
    elif tag=='alignment':mutant['requested_Cancellation_allocation_alignment']=1
    elif tag=='clone':mutant['clone_additional_allocation_bytes']=1
    elif tag=='repeat':mutant['functions'][names[0]]['repeat']=5
    elif tag=='unknown_callee':mutant['functions'][names[2]]['calls'].append({'target':'unknown','role':'unknown'})
    elif tag=='cycle':mutant['functions'][names[2]]['calls'].append({'target':names[2],'role':names[2]})
    else:mutant['during_entry_drop_visit_bound']=52
    rejects('ledger mutation '+tag,lambda mutant=mutant:q.evaluate(valid,mutant))

# Retained compiler evidence is read, never regenerated or executed.
probe=load(C/'probe-receipt.json');ir=(C/'cancellation-backing-probe.ll').read_text()
require('probe source bind',sha((C/'cancellation-backing-probe.rs').read_bytes())==probe['source_sha256'])
require('probe IR bind',sha(ir.encode())==probe['IR_sha256'])
require('probe output bind',sha((C/'probe.stdout').read_bytes())==probe['stdout_sha256'] and sha((C/'probe.stderr').read_bytes())==probe['stderr_sha256'])
require('probe exact binary current hash only',sha(Path(probe['command'][0]).read_bytes())==probe['compiler_sha256'])
require('probe exact1.99 version','rustc 1.99.0 (b940084d7 2026-09-28)' in probe['compiler_version_bound_by_immutable_receipt'])
require('compile only receipt',probe['exit_code']==0 and probe['direct_child_waited'] and not probe['executable_created'] and not probe['product_or_probe_executed'])
require('probe target',probe['command'][probe['command'].index('--target')+1]=='aarch64-apple-darwin')
require('probe flags',all(x in probe['command'] for x in ('opt-level=0','panic=unwind','-Zmir-opt-level=0')))
require('probe identical derive','#[derive(Clone, Default)]\npub struct Cancellation(Arc<AtomicBool>);' in sources['src/execute.rs'] and '#[derive(Clone, Default)]\npub struct Cancellation(Arc<AtomicBool>);' in (C/'cancellation-backing-probe.rs').read_text())
regions={}
for match in re.finditer(r'^define .*?^}',ir,re.M|re.S):
    text=match[0]
    for role,fragment in [('arc_default','4syncINtB5_3Arc'),('arc_clone','atomicrmw add'),('box_new','14box_new_uninit'),('allocator','18alloc_impl_runtime'),('global_clone','5allocNtB5_6GlobalNtNt')]:
        head=text.splitlines()[0]
        if (role=='arc_clone' and fragment in text) or (role!='arc_clone' and fragment in head):
            if role=='arc_default' and 'Default7default' not in head:continue
            regions[role]=text
require('Arc layout stdout','`alloc::sync::ArcInner<std::sync::atomic::Atomic<bool>>`: 24 bytes, alignment: 8 bytes' in (C/'probe.stdout').read_text())
require('one Arc default allocation call',len(re.findall(r'call ptr .*14box_new_uninit.*\(i64 8, i64 24\)',regions['arc_default']))==1)
require('box calls unzeroed runtime',bool(re.search(r'call .*18alloc_impl_runtime.*\(i64 %layout.0, i64 %layout.1, i1 zeroext false\)',regions['box_new'])))
require('allocator exact byte align order',bool(re.search(r'call ptr .*12___rust_alloc\(i64 %layout.1, i64 %layout.0\)',regions['allocator'])))
require('clone atomic increment',re.search(r'atomicrmw add ptr .*i64 1 monotonic',regions['arc_clone']) is not None)
require('clone overflow trap','call void @llvm.trap()' in regions['arc_clone'])
require('clone no allocation request',not any(x in regions['arc_clone'] for x in ('___rust_alloc','box_new','alloc_impl_runtime')))
require('Global clone empty',regions['global_clone'].split('{',1)[1].strip()=='start:\n  ret void\n}')

save('custody.json',{'release_sha256':sha(release.read_bytes()),'packets':custody,'source_tree_sha256':manifest['tree_sha256'],'source_members':len(sources),'source_bytes':sum(x['bytes'] for x in manifest['members']),'host_members':11,'all_frozen_inputs_unchanged':True})
save('recomputed-shapes.json',{n:{**x,'leaves':width(n)} for n,x in shapes.items() if n in new})
save('recomputed-work.json',{'functions':functions,'expanded_source_core':core,'native_inventory_bytes':native_bytes,'inventory_is_work':False,'typed_dereference_copies':typed_reads,'drop_sites':drop_visits,'drop_visit_bound':53,'setup_prefix_controls':prefix_controls,'formula':'119922 + 24 + sum(five native-open request bounds) + io-error native bound + 53*entry-drop-payload-bound','synthetic_arithmetic_example_only':result})
save('probe-review.json',{'retained_probe_receipt_sha256':sha((C/'probe-receipt.json').read_bytes()),'compiler_sha256_reverified_without_invocation':probe['compiler_sha256'],'requested_bytes':24,'alignment':8,'normal_default_allocation_requests':1,'clone_new_allocation_requests':0,'retained_IR_regions':regions,'independent_compiler_invocations':0,'standalone_compilation_is_product_or_runtime_evidence':False})
save('checks.json',{'count':len(checks),'passed':checks,'producer_checks_reused_as_independent_evidence':0,'compiler_invocations':0,'product_or_fixture_executions':0})
print(json.dumps({'checks':len(checks),'source_work_core':core,'during_entry_payload_drop_visits':53,'typed_dereference_Copy_transfers':len(typed_reads),'bounded_interface_review':True,'complete_component_or_grant':False}))
