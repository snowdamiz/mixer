"""Independent, read-only source/MIR/LLVM reconstruction. No compiler execution.

The logical work unit is inherited source/typed occurrence accounting. It is
not a clock, instruction bound, private stdlib/panic cost, or operational grant.
"""
from pathlib import Path
from functools import lru_cache
import collections, gzip, hashlib, json, re, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
P = V / 'swift-guarded-snapshot-owned-provider-work-storage'
PROVIDER = V / 'swift-guarded-snapshot-owned-binding-provider'
OLD = V / 'swift-guarded-snapshot-owned-provider-independent'
TREE = 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
NAME = 'describe_existing_owner_candidate_v1'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
EXPECTED_SEAL = '28ba8099ce8b57f91cd46baac21f130986000ecbbf7df07b16e6bf061fc342d1'
EXPECTED_RELEASE = 'e38b888c5f737e6a3df414f81801996676348cd61337dc08d15b1fda0bbaffd9'
ASSERTIONS = collections.Counter()
def digest(b): return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v, sort_keys=True, separators=(',', ':')).encode()
def require(condition, message):
    ASSERTIONS[message.split(':')[0]] += 1
    if not condition: raise ValueError(message)
def load(p): return json.loads(p.read_bytes())
def record(path, name=None):
    data=path.read_bytes()
    return {'path':name or path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':digest(data)}
def closure_snapshot():
    seal=P/'seal.json';require(digest(seal.read_bytes())==EXPECTED_SEAL,'frozen seal')
    sealed=load(seal);rows=[]
    for path in sorted(P.rglob('*')):
        if path.is_dir():continue
        require(not path.is_symlink(),'no symlink')
        if path.name=='seal.json':continue
        rows.append(record(path,path.relative_to(P).as_posix()))
    require(rows==sealed['members'],'exact candidate membership')
    require(len(rows)==56 and sum(r['bytes'] for r in rows)==13734810,'exact candidate closure')
    require(sealed['member_table_sha256']==digest(canon(rows)),'candidate member table')
    external=[]
    for row in load(P/'input-custody.json')['members']:
        actual=record(ROOT/row['path']);require(actual==row,'frozen input:'+row['path']);external.append(actual)
    release=V/'swift-semantic-adapter-root-review/guarded-snapshot-owned-provider-work-storage-frozen-release.json'
    require(digest(release.read_bytes())==EXPECTED_RELEASE,'root release')
    selected_source=V/'swift-real-profile-loader-binding/source-preimages/genuine.wasm'
    require(digest(selected_source.read_bytes())=='9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806','selected source fixture custody')
    return {'candidate_seal_sha256':EXPECTED_SEAL,'candidate_members':rows,'input_members':external,'root_release':record(release),'selected_source_fixture':record(selected_source)}
def strip_comment(line):
    # MIR contains quoted assertion strings. Only // outside a string is trivia.
    quoted=False;escaped=False
    for i,c in enumerate(line):
        if escaped:escaped=False;continue
        if quoted and c=='\\':escaped=True;continue
        if c=='"':quoted=not quoted
        if not quoted and line[i:i+2]=='//':return line[:i].rstrip()
    return line.rstrip()
def all_constructs(text):
    out=[];current=[]
    for line in text.splitlines():
        if not current:
            if not line.strip() or line.startswith('//'):continue
            require(not line[0].isspace() and line!='}','all MIR top level')
            current=[line]
            if line.endswith(';'):
                require(line.startswith('const '),'only standalone const');out.append('\n'.join(current));current=[]
            else:require(line.endswith(' {'),'braced top level')
        else:
            current.append(line)
            if line=='}':out.append('\n'.join(current));current=[]
    require(not current,'closed MIR top level')
    return out
def selected_constructs(text):
    return [b for b in all_constructs(text) if b.startswith(('fn '+NAME+'(', 'fn '+NAME+'::', 'const '+NAME, 'const InputBackingDescriptionV1::'))]
def normalize_body(body):
    rows=[]
    for line in body.splitlines():
        line=strip_comment(line)
        for folder in (P/'owned-work/capture-layout/vm',OLD/'owned-work/compiler-metadata-mir/vm'):
            line=line.replace(str(folder),'<SOURCE>')
        if line.strip():rows.append(line)
    return '\n'.join(rows)
def norm(ty):
    ty=re.sub(r'\b(?:[A-Za-z_]\w*::)+','',ty)
    ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*", "'_", ty)
    ty=re.sub(r"(&)\s*'_\s+",r'\1',ty)
    return re.sub(r'\s+','',ty)
def split_top(text, sep=','):
    stack=[];parts=[];start=0;pairs={')':'(',']':'[','}':'{','>':'<'}
    for i,c in enumerate(text):
        if c in '([{<':stack.append(c)
        elif c in ')]}>':
            require(bool(stack) and stack.pop()==pairs[c],'balanced type')
        elif c==sep and not stack:parts.append(text[start:i].strip());start=i+1
    require(not stack,'closed type');parts.append(text[start:].strip())
    return [x for x in parts if x]
def source_members():
    source={};rows=[]
    for row in load(PROVIDER/'proposed-source-custody.json'):
        data=(ROOT/row['origin']).read_bytes();want={k:row[k] for k in ('path','bytes','sha256')}
        require({'path':row['path'],'bytes':len(data),'sha256':digest(data)}==want,'source member')
        rows.append(want);source[row['path']]=data
    require(len(rows)==146 and digest(canon(rows))==TREE,'exact source146')
    return source
class Shapes:
    """Separate source declaration reader and finite aggregate recursion."""
    paths={**{x:PROFILE for x in ('CandidateShapeRefusalV1','ImmutableFixtureIdentitiesV1','ImmutableIdentityPreimageV1','InputBackingDescriptionV1','PendingUpstreamRequirementV1','PendingUpstreamRequirementsV1','PreexistingImmutableBindingV1','ReviewedFixtureBindingV1','UnqualifiedExistingOwnerCandidateV1','UnverifiedProfileDigestBytesV1')},'SwiftRunBudget':'src/experimental_swift_reactor/control.rs','SwiftValidationBudget':'src/experimental/swift.rs'}
    def __init__(self,source):
        self.definitions={};self.declarations={}
        for name,path in self.paths.items():
            text=source[path].decode();matches=list(re.finditer(r'\b(struct|enum) '+name+r'\b',text))
            require(len(matches)==1,'unique source declaration:'+name)
            m=matches[0];start=text.index('{',m.end());depth=1;end=start+1
            while depth:
                if text[end]=='{':depth+=1
                elif text[end]=='}':depth-=1
                end+=1
            declaration=text[m.start():end];body=text[start+1:end-1]
            # These twelve exact audited declarations contain no string/comment body.
            require('//' not in body and '/*' not in body,'simple authored declaration')
            if m[1]=='struct':
                fields=[]
                for field in split_top(body):
                    field=re.sub(r'^\s*pub(?:\([^)]*\))?\s+','',field)
                    field_name,ty=field.split(':',1);require(field_name.strip().isidentifier(),'named source field');fields.append(ty.strip())
                self.definitions[name]=('struct',fields)
            else:
                variants=[]
                for variant in split_top(body):
                    if '{' in variant:fields=[f.split(':',1)[1].strip() for f in split_top(variant.split('{',1)[1].rsplit('}',1)[0])]
                    else:require(variant.strip().isidentifier(),'unit variant');fields=[]
                    variants.append(fields)
                self.definitions[name]=('enum',variants)
            self.declarations[name]={'path':path,'declaration_sha256':digest(declaration.encode())}
    def leaves(self,ty):
        ty=norm(ty)
        if ty.startswith('&'):return 1
        if ty.startswith('{closure@'):return 2
        if ty in ('()','!','bool','u8','u32','u64','usize','isize','Infallible','Path','OsStr'):return 1
        if ty.startswith('['):
            element,count=split_top(ty[1:-1],';');return int(count)*self.leaves(element)
        if '<' in ty:
            name,params=ty.split('<',1);args=split_top(params[:-1])
            if name=='Range':return 2*self.leaves(args[0])
            if name in ('Option','Result','ControlFlow'):return 1+max(self.leaves(a) for a in args)
        else:name=ty
        require(name in self.definitions,'known authored type:'+name)
        kind,fs=self.definitions[name]
        return sum(self.leaves(t) for t in fs) if kind=='struct' else 1+max(sum(self.leaves(t) for t in variant) for variant in fs)
def role_roster(body):
    lines=body.splitlines();roles={};header=lines[0]
    if len(lines)==1:return {'_constant':'usize'}
    if header.startswith('fn '):
        params=header.split('(',1)[1].rsplit(') -> ',1)[0]
        for param in split_top(params):
            name,ty=param.split(': ',1);require(re.fullmatch(r'_\d+',name) is not None,'parameter role');roles[name]=ty
    for line in lines[1:]:
        line=strip_comment(line).strip()
        if line.startswith('let '):
            m=re.fullmatch(r'let (?:mut )?(_\d+): (.+);',line)
            require(m is not None,'MIR role declaration')
            require(m[1] not in roles,'unique role');roles[m[1]]=m[2]
    require(set(roles)=={'_'+str(i) for i in range(len(roles))},'contiguous complete MIR roles')
    return roles
def basic_blocks(body):
    if '\n' not in body:return {'constant':[body.split(' = ',1)[1]]}
    blocks={};current=None
    for line in body.splitlines()[1:]:
        code=strip_comment(line).strip()
        m=re.fullmatch(r'(bb\d+)(?: \(cleanup\))?: \{',code)
        if m:current=m[1];require(current not in blocks,'unique basic block');blocks[current]=[]
        elif current is not None:
            if code=='}':current=None
            elif code:require(code.endswith(';'),'one complete MIR operation');blocks[current].append(code)
    require(all(blocks.values()),'nonempty basic blocks')
    return blocks
def successors(ops):return set(re.findall(r'\bbb\d+\b',ops[-1]))
def finite_maxima(blocks, main):
    """Unroll actual range counters and compute maximum visits to each block.

    Early exits (including every unwind) remain possible, so all arms obtain
    individual maxima; incompatible arms are conservatively summed afterward.
    """
    names=list(blocks);index={name:i for i,name in enumerate(names)}
    if not main:
        def walk(node,seen):
            require(node not in seen,'acyclic secondary CFG')
            return {x for s in successors(blocks[node]) for x in walk(s,seen|{node})}|{node}
        require(walk('bb0',set())==set(names),'all secondary blocks reachable')
        return {n:1 for n in names}
    # Source-reviewed range fields and actual branching/backedges are mandatory.
    require('end: const 12_usize' in '\n'.join(blocks['bb0']) and 'end: const 5_usize' in '\n'.join(blocks['bb24']),'12/5 ranges')
    require(successors(blocks['bb15'])=={'bb2'} and successors(blocks['bb53'])=={'bb26'},'exact backedges')
    @lru_cache(None)
    def walk(node,identities,paths):
        choices=[]
        for target in successors(blocks[node]):
            i,p=identities,paths
            if (node,target)==('bb3','bb5') and i>=12:continue
            if (node,target)==('bb27','bb28') and p>=5:continue
            if (node,target)==('bb15','bb2'):i+=1
            if (node,target)==('bb53','bb26'):p+=1
            require(i<=12 and p<=5,'finite source iteration')
            choices.append(walk(target,i,p))
        maximum=[max((v[j] for v in choices),default=0) for j in range(len(names))]
        maximum[index[node]]+=1
        return tuple(maximum)
    counts=walk('bb0',0,0)
    require(all(counts),'all main CFG blocks reachable')
    return dict(zip(names,counts))
def cut_paths(blocks,main):
    paths=[]
    def visit(n,previous):
        require(n not in previous,'only explicit bounded cycles');route=previous+[n];term=blocks[n][-1];targets=successors(blocks[n])
        if 'unwind continue' in term:paths.append((tuple(route),'unwind-continue',None))
        if not targets:require(term in ('return;','unreachable;'),'finite terminal');paths.append((tuple(route),term[:-1],None))
        for target in targets:
            if main and (n,target) in (('bb15','bb2'),('bb53','bb26')):paths.append((tuple(route),'bounded-loop-backedge',target))
            else:visit(target,route)
    visit('bb0',[]);return sorted(paths,key=str)
def parse_literals(code):
    out=[]
    for tail in code.split('const ')[1:]:
        if re.match(r'\d+_(?:usize|isize)\b',tail):width,leaves=8,1
        elif re.match(r'\d+_u8\b|true\b|false\b',tail):width,leaves=1,1
        elif tail.startswith('()'):width,leaves=0,1
        else:
            token=re.match(r'[A-Za-z_][A-Za-z_0-9:]*',tail)
            require(token is not None,'known constant token')
            prefix='experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::outer_parent_v1::'
            if token[0]==prefix+'SELECTED_SOURCE_SHA256_V1':width,leaves=32,32
            elif token[0]==prefix+'SELECTED_SOURCE_BYTES_V1':width,leaves=8,1
            elif re.match(re.escape(NAME)+r'::promoted\[[01]\]',tail):width,leaves=8,1
            else:raise ValueError('unpriced literal:'+tail)
        out.append((width,leaves))
    return out
def price_operation(code,roles,B):
    require(code.startswith(('StorageLive(', 'StorageDead(', 'goto ', 'switchInt(', 'assert(', 'return;', 'unreachable;', '_', 'const ')),'known operation category')
    source=2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b',code));native=0
    for local in re.findall(r'\b_\d+\b',code):
        require(local in roles,'every operand bound');r=roles[local]
        source+=2*(r['leaves']+r['pointee_leaves'][0]+B*r['pointee_leaves'][1])
        native+=2*(r['bytes']+r['pointee_bytes'][0]+B*r['pointee_bytes'][1])
    for width,leaves in parse_literals(code):source+=2*leaves;native+=2*width
    if code=='return;':
        r=roles['_0'];source+=2*(r['leaves']+r['pointee_leaves'][0]+B*r['pointee_leaves'][1]);native+=2*(r['bytes']+r['pointee_bytes'][0]+B*r['pointee_bytes'][1])
    return source,native
CALLS={
    'IntoIterator>::into_iter':'range_into_iter','as Iterator>::next':'range_next',
    'core::slice::<impl [u8]>::len':'slice_len','::checked_add(':'usize_checked_add',
    'Option::<usize>::ok_or':'option_ok_or_shape_refusal',' as Try>::branch':'result_try_branch',
    ' as FromResidual<':'candidate_result_from_residual','<[u8; 32] as PartialEq>::ne':'digest_array_ne32',
    'Path::as_os_str':'path_as_os_str','<OsStr as OsStrExt>::as_bytes':'osstr_as_bytes',
    'core::slice::<impl [u8]>::is_empty':'slice_is_empty','core::slice::<impl [u8]>::contains':'slice_contains_u8',
    '<&[u8] as PartialEq>::ne':'slice_reference_ne','Option::<usize>::and_then':'option_and_then_excluding_authored_callback'}
EXPECTED_CALLS={'range_into_iter':2,'range_next':19,'slice_len':33,'usize_checked_add':22,'option_ok_or_shape_refusal':17,'result_try_branch':17,'candidate_result_from_residual':2,'digest_array_ne32':1,'path_as_os_str':5,'osstr_as_bytes':5,'slice_is_empty':5,'slice_contains_u8':5,'slice_reference_ne':5,'option_and_then_excluding_authored_callback':5}
def call_interface(code):
    if ' -> [return:' not in code:return None
    found=[v for k,v in CALLS.items() if k in code]
    require(len(found)==1,'fully classified external call')
    return found[0]
@lru_cache(None)
def reconstruct():
    source=source_members();shapes=Shapes(source)
    plan=load(P/'compiler-plan.json');receipt=load(P/'commands/capture-layout/receipt.json')
    require(digest((P/'compiler-plan.json').read_bytes())=='63b3274f5e90218cf2d58f09d67aabbeff4e53c4c7a1c2195aca429a4be193bc','root authorized plan')
    auth=load(P/'compiler-root-authorization.json');require(auth['plan_sha256']==digest((P/'compiler-plan.json').read_bytes()) and auth['authorized_invocations']==1,'single authorized invocation')
    require(all(receipt[k]==v for k,v in plan.items()),'retained exact compile plan')
    require(receipt['success'] and receipt['exit_code']==0 and not receipt['timed_out'] and not receipt['output_exceeded'],'retained compile success')
    require(receipt['compiler_invocations']==1 and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['owned_scratch_removed'],'retained sole compile cleanup')
    require(receipt['elapsed_seconds']<=55 and receipt['output_limit_bytes']==16*1024**2 and not receipt['linked_executable'] and not receipt['runtime_or_native_execution'],'retained compile scope')
    require(receipt['compiler_sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0' and 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4' in receipt['compiler_version_preimage'],'retained exact compiler')
    require(not any(x in receipt['argv'] for x in ('--test','--run')) and '-Zmir-opt-level=0' in receipt['argv'] and 'opt-level=0' in receipt['argv'] and '--emit=metadata=' in ' '.join(receipt['argv']),'retained production emit only')
    initial=load(P/'attempts/initial-compiler-plan/compiler-plan.json')
    difference=[k for k in set(initial)|set(plan) if initial.get(k)!=plan.get(k)]
    require(set(difference)=={'output_limit_bytes','runner_sha256'} and initial['output_limit_bytes']==4*1024**2,'preserved unexecuted initial proposal')
    fragment=(PROVIDER/'existing-owner-candidate.inc.rs').read_bytes();tail=(P/'query-layout.inc.rs').read_bytes();profile=(P/'query-profile.rs').read_bytes();original=source[PROFILE]
    ending=fragment+b'\n}\n}\n';require(original.endswith(ending),'actual source insertion boundary')
    require(profile==original[:-len(ending)]+fragment[:-2]+tail+fragment[-2:]+b'\n}\n}\n','exact additive inert query')
    require('for<\'p0> fn(' in tail.decode() and '= describe_existing_owner_candidate_v1;' in tail.decode() and '#[used]' in tail.decode(),'actual HRTB pointer')
    manifest=load(P/'query-source-manifest.json');queryrows=[{'path':n,'bytes':len(profile if n==PROFILE else b),'sha256':digest(profile if n==PROFILE else b)} for n,b in source.items()]
    require(manifest['members']==queryrows and digest(canon(queryrows))==manifest['tree_sha256']==plan['query_tree_sha256'],'full146 query custody')
    artifacts={}
    for artifact in receipt['artifacts']:
        if artifact['path']=='query.rmeta':continue # Metadata was intentionally removed; retained digest is historical.
        compressed=(P/'commands/capture-layout'/(artifact['path']+'.gz')).read_bytes();raw=gzip.decompress(compressed)
        require(len(compressed)==artifact['gzip_bytes'] and digest(compressed)==artifact['gzip_sha256'],'compressed artifact custody')
        require(len(raw)==artifact['bytes'] and digest(raw)==artifact['sha256'],'raw artifact custody');artifacts[artifact['path']]=raw.decode()
    for name in ('stdout','stderr'):
        require(record(P/'commands/capture-layout'/name,name)==receipt[name],'retained compiler stream')
    mir=artifacts['query.mir'];llvm=artifacts['query.ll'];stdout=(P/'commands/capture-layout/stdout').read_text()
    raw=selected_constructs(mir);previous=selected_constructs((OLD/'provider.mir').read_text())
    require(len(raw)==len(previous)==11 and [normalize_body(x) for x in raw]==[normalize_body(x) for x in previous],'exact all11 construct correspondence')
    query=next(b for b in all_constructs(mir) if b.startswith('fn owned_provider_remaining_layout_query_v1('))
    values=[int(x) for x in re.findall(r'\[u8; (\d+)\]',query.splitlines()[0])];require(len(values)==36,'18 named layout pairs')
    layout={};observations=[]
    for i,row in enumerate(plan['named_layout_queries']):
        layout[norm(row['type'])]=(values[2*i],values[2*i+1]);observations.append({'name':row['name'],'type':row['type'],'size':values[2*i],'align':values[2*i+1]})
    require([{k:r[k] for k in ('name','type','size','align')} for r in load(P/'layouts.json')['named_observations']]==observations,'named layout raw data')
    for row in load(OLD/'layouts.json')['rows']:
        key=norm(row['type']);pair=(row['size'],row['align'])
        require(key not in layout or layout[key]==pair,'old/new layout agreement');layout[key]=pair
    closure='{closure@'+str(P/'owned-work/capture-layout/vm')+'/'+PROFILE+':1185:27: 1185:30}'
    exact_record='print-type-size type: `'+closure+'`: 16 bytes, alignment: 8 bytes'
    require(stdout.count(exact_record)==1,'actual anonymous aggregate16/8')
    record_start=stdout.index(exact_record);record_end=stdout.find('\nprint-type-size type:',record_start)
    capture_record=stdout[record_start:record_end]
    require(capture_record==exact_record+'\nprint-type-size     end padding: 16 bytes','opaque actual closure compiler padding retained')
    layout[norm(closure)]=(16,8);layout["ImmutableIdentityPreimageV1<'_>"]=(48,8)
    require(re.search(r'print-type-size type: `[^`]*::ImmutableIdentityPreimageV1<\'_>`: 48 bytes, alignment: 8 bytes',stdout) is not None,'original preimage48/8')
    layout.update({'()':(0,1),'!':(0,1),'bool':(1,1),'u8':(1,1),'usize':(8,8),'isize':(8,8)})
    def extent(ty):
        ty=norm(ty)
        if ty in layout:return layout[ty]
        if ty.startswith('['):
            elem,n=split_top(ty[1:-1],';');size,align=extent(elem);return size*int(n),align
        raise ValueError('unobserved extent:'+ty)
    typedmap=load(P/'source-typed-MIR-map.json');reported={f['header']:f for f in typedmap['functions']}
    functions=[];total=[0,0];calls=collections.Counter();operations=0;slots=[];callrows=[]
    for body in raw:
        header=body.splitlines()[0];rr=role_roster(body);blocks=basic_blocks(body);main=header.startswith('fn '+NAME+'(');callback=header.startswith('fn '+NAME+'::{closure#0}');standalone='\n' not in body
        cap=5 if callback else 1;weights={'constant':1} if standalone else finite_maxima(blocks,main);roles={}
        for local,ty in rr.items():
            size,align=extent(ty);key=norm(ty);pointee=key[1:] if key.startswith('&') else None
            if pointee and pointee.startswith('mut'):pointee=pointee[3:]
            if pointee in ('[u8]','Path','OsStr'):pb=pl=(0,1)
            elif pointee:pb=(extent(pointee)[0],0);pl=(shapes.leaves(pointee),0)
            else:pb=pl=(0,0)
            roles[local]={'type':ty,'bytes':size,'align':align,'leaves':shapes.leaves(ty),'pointee_bytes':pb,'pointee_leaves':pl}
        expected=reported[header];byreported={r['local']:r for r in expected['roles']}
        require(set(roles)==set(byreported),'complete reported role identity')
        for local,r in roles.items():
            other=byreported[local];require((r['bytes'],r['align'],r['leaves'])==(other['bytes'],other['alignment'],other['scalar_leaves']),'independent role type/size/shape')
            require(r['pointee_bytes']==(other['pointee_bytes']['fixed'],other['pointee_bytes']['input_operand_bytes']) and r['pointee_leaves']==(other['pointee_scalar_leaves']['fixed'],other['pointee_scalar_leaves']['input_operand_bytes']),'independent pointee role shape')
            slots.append({'function':expected['name'],'local':local,**r})
        require(set(blocks)==set(expected['blocks']),'complete basic blocks')
        values=[]
        for B in (0,1,1947,65537):
            params=[roles[n] for n in rr if header.startswith('fn ') and n in re.findall(r'(_\d+):',header)]
            entry=2+sum(2*(r['leaves']+r['bytes']+r['pointee_bytes'][0]+r['pointee_leaves'][0]+B*(r['pointee_bytes'][1]+r['pointee_leaves'][1])) for r in params)
            subtotal=entry
            for bn,ops in blocks.items():
                other=expected['blocks'][bn];require(ops==other['operations'],'complete operation text')
                require(weights[bn]==other['per_invocation_cap'],'independent CFG block maximum')
                for code,row in zip(ops,other['rows']):
                    s,n=price_operation(code,roles,B)
                    for observed,field in ((s,'source_action_units'),(n,'native_sized_occurrence_bytes'),(s+n,'combined')):
                        require(observed==row[field]['fixed']+B*row[field]['input_operand_bytes'],'independent operation price')
                    subtotal+=weights[bn]*(s+n)
            end=sum(2+2*(r['leaves']+r['bytes']) for r in roles.values());require(end==expected['finite_role_end_envelope_per_invocation'],'every finite role end')
            subtotal=(subtotal+end)*cap;require(subtotal==expected['work_per_request']['fixed']+B*expected['work_per_request']['input_operand_bytes'],'whole construct work')
            values.append(subtotal)
        own=[values[0],values[1]-values[0]];total=[total[i]+own[i] for i in range(2)]
        for bn,ops in blocks.items():
            operations+=len(ops)
            for code in ops:
                interface=call_interface(code)
                if interface:calls[interface]+=weights[bn]*cap;callrows.append({'function':expected['name'],'block':bn,'interface':interface,'cap':weights[bn]*cap,'code':code})
        if not standalone:
            paths=cut_paths(blocks,main);other=sorted([(tuple(r['blocks']),r['terminal'],r.get('successor')) for r in expected['bounded_cut_paths']],key=str)
            require(paths==other,'complete normal/refusal/unwind/backedge paths')
        functions.append({'name':expected['name'],'roles':len(roles),'blocks':len(blocks),'operations':sum(map(len,blocks.values())),'inline':sum(r['bytes'] for r in roles.values()),'work':own,'block_maxima':weights,'authored_invocations':cap})
    require(operations==565 and len(slots)==193,'all565 operations193 roles')
    require(calls==EXPECTED_CALLS==load(P/'candidate.json')['new_required_std_interface_terms'],'all14 external positive term multiplicities')
    out_size,out_align=extent("Result<UnqualifiedExistingOwnerCandidateV1<'_>, CandidateShapeRefusalV1>");result_end=2+2*(shapes.leaves("Result<UnqualifiedExistingOwnerCandidateV1<'_>, CandidateShapeRefusalV1>")+out_size)
    total[0]+=result_end;require(total==[276580,1324] and result_end==4134,'independent full work formula')
    inline=sum(r['bytes'] for r in slots);require(inline==8344 and out_size==1352 and inline+out_size==9696,'all logical slots plus distinct caller result')
    require(292037+inline+out_size==301733 and 895084428325956794+total[0]==895084428326233374,'fixed composed arithmetic')
    # LLVM ties the forced pointer to actual production and actual callback ABI.
    force=next(line for line in llvm.splitlines() if line.startswith('@') and 'OWNED_PROVIDER_LAYOUT_FORCE_V1 = constant ptr ' in line)
    symbol=force.split(' = constant ptr ',1)[1].split(',',1)[0]
    require(re.search(r'^define void '+re.escape(symbol)+r'\(ptr sret\(\[1352 x i8\]\) align 8 %_0, ptr align 8 %binding, ptr align 8 %identities, ptr align 8 %native_path_bodies\)',llvm,re.M) is not None,'LLVM exact production pointer and result')
    require(re.search(r'^define internal \{ i64, i64 \} @[^\n]*describe_existing_owner_candidate_v1[^\n]*\(ptr align 8 %_1.0, ptr align 8 %_1.1, i64 %n\)',llvm,re.M) is not None,'LLVM actual two-capture callback')
    require('debug native_path_bodies => (*(_1.0: &[&[u8]; 5]))' in raw[-1] and 'debug position => (*(_1.1: &usize))' in raw[-1],'actual MIR captures')
    return {'schema':1,'source_tree_sha256':TREE,'constructs':functions,'roles':len(slots),'operations':operations,'slots':slots,'named_layouts':observations,'closure_size_align':[16,8],'work':{'fixed':total[0],'B_coefficient':total[1]},'external_result_end':result_end,'typed_inline':inline,'external_result':out_size,'P0_addition':inline+out_size,'conditional_P0_fixed':301733,'conditional_whole_fixed':895084428326233374,'external_call_counts':dict(calls),'external_call_sites':callrows,'new_compiler_invocations':0,'new_runtime_invocations':0}
def validate_documents(report,candidate,phase,contracts):
    for key,value in {'source_tree_sha256':TREE,'constructs':11,'roles':193,'written_operations':565,'typed_inline_slots':8344,'external_caller_result_slot':1352,'provider_inline_addition':9696,'conditional_P0_fixed':301733,'external_result_end':4134}.items():require(candidate[key]==value,'candidate exact reconstruction:'+key)
    require(candidate['provider_source_work']=={'fixed':276580,'input_operand_bytes':1324},'candidate source formula')
    require(candidate['conditional_whole_fixed_excluding_dynamic_operands_and_new_std_or_upstream_terms']==895084428326233374,'candidate composed fixed')
    require(candidate['new_required_std_interface_terms']==EXPECTED_CALLS,'all new callee terms')
    old={'L_str':67424,'P0_dynamic_backing':1,'P0_fixture_binding':1,'P0_root_route':1,'native_error_request':1,**{'native_open_request_'+str(i):1 for i in range(5)}}
    require(candidate['inherited_residual_work_terms']==contracts['inherited10_residual_terms_preserved']==old,'all10 old residuals')
    require(candidate['all_six_upstream_requirements']==candidate['all_three_selectors']=='Pending','pending upstream/selectors')
    require(not any(candidate[k] for k in ('new_callee_contracts_selected','actual_acquisition_or_authenticated_owner','L_str_selected','whole_quote_or_root_funding_or_operational_grant','native_runtime_FieldLog_OTA_GA')),'no invented operational authority')
    require(candidate['zero_alias_move_or_sharing_credit'] and candidate['original_binding1168_preserved'] and candidate['no_refund_on_None_refusal_unwind'],'conservative storage/refusal')
    slots={r['function']+':'+r['local']:r for r in report['slots']}
    require(set(slots)=={r['id'] for r in phase['all_new_roles']} and len(slots)==len(phase['all_new_roles'])==193,'complete distinct slot roster')
    for r in phase['all_new_roles']:
        own=slots[r['id']];require((r['type'],r['bytes'],r['alignment'])==(own['type'],own['bytes'],own['align']),'exact written slot extent')
        require(r['reserved_first']=='P0_BEFORE_ANY_PROVIDER_OR_ACQUISITION_POLICY_QUOTE_ACCOUNT_ENTRY' and r['reserved_last']=='P0_AFTER_FINAL_OUTER_RESULT_CONSUMPTION' and r['funded_by']=='P0' and r['invocation_storage_instances']==1,'every slot held throughout')
    expected_phases=set(load(V/'swift-guarded-snapshot-outer-parent-work-storage/phase-roster.json')['phases'])
    require(len(expected_phases)==15,'all15 inherited phases')
    for field,amount in (('provider_slots_bytes_each_phase',8344),('external_result_bytes_each_phase',1352),('P0_new_total_each_phase',9696)):
        require(set(phase[field])==expected_phases and all(type(v) is int and v==amount for v in phase[field].values()),'every phase full allocation:'+field)
    require(phase['binding_container_inherited_once']==1168 and phase['all12identity_and5native_and5separate_body_backing_remain_required'] and phase['future_root_inline_backing_and_original_diagnostic_backing_remain_required'],'backing and original container mandatory')
    prices={r['name']:r for r in contracts['std_interfaces']}
    require(set(prices)==set(EXPECTED_CALLS) and len(prices)==len(contracts['std_interfaces'])==14,'exact external price roster')
    for name,count in EXPECTED_CALLS.items():
        require(prices[name]['count']==count and prices[name]['selected'] is False and prices[name]['unit']=='logical work' and 'strict positive externally reviewed' in prices[name]['price'],'positive external work remains required')
    actual=[{k:r[k] for k in ('function','block','interface','code')}|{'cap':r['call_cap']} for r in contracts['full_call_roster']]
    require(actual==report['external_call_sites'],'all26 actual call sites')
    return True
if __name__=='__main__':
    before=closure_snapshot();report=reconstruct();after=closure_snapshot();require(before==after,'before/after immutable custody')
    validate_documents(report,load(P/'candidate.json'),load(P/'phase-roster.json'),load(P/'required-input-contracts.json'))
    (HERE/'reconstruction.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    (HERE/'input-custody.json').write_text(json.dumps({'before':before,'after':after,'unchanged':True},sort_keys=True,indent=2)+'\n')
    (HERE/'assertion-counts.json').write_text(json.dumps(dict(ASSERTIONS),sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('roles','operations','typed_inline','P0_addition','work','external_call_counts')}))
