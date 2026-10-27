"""Fresh complete MIR/source reconstruction; no producer analyzer imported.

The later resolver controls import only the previously accepted exact-binding
analyzers. All input parsing, census, lineage and allocation transport below is
independently implemented here.
"""
from support import *
import collections, copy, gzip, importlib.util, re
LEX=re.compile(r'''//[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])' ''',re.X)
ALLOC=re.compile(r'\balloc\d+\b')
ROOTS=[str(V/p) for p in ['swift-guarded-snapshot-loader-work-source146/owned-work/vm','swift-guarded-snapshot-outer-parent-independent/owned-work/compiler-metadata-mir/vm','swift-guarded-snapshot-scoped-binding-source/owned-work/positive/vm','swift-guarded-snapshot-owned-provider-work-storage/owned-work/capture-layout/vm']]
TYPES=['ReviewedFixtureBindingV1','FrozenFixtureV1','ImmutableIdentityPreimageV1','ImmutableFixtureIdentitiesV1','PreexistingImmutableBindingV1','OneFixtureOuterRequestV1']
BASE='experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1'
TYPE_PATHS=TYPES+[BASE+'::'+n for n in TYPES[:2]]+[BASE+'::outer_parent_v1::'+n for n in TYPES[2:]]
LIFES=re.compile(r'(?<![\w:])('+'|'.join(map(re.escape,sorted(TYPE_PATHS,key=len,reverse=True)))+r")(?:::)?<'_>")
PROBES=[[],['outer_parent_account_layout_query_v1','outer_parent_layout_query_v1'],['outer_parent_account_layout_query_v1','outer_parent_layout_query_v1','scoped_result_layout_query_v1','scoped_local_binding_compiles_v1'],['owned_provider_remaining_layout_query_v1']]
def outside(text,fn,comments=True):
    pieces=[];pos=0
    for m in LEX.finditer(text):
        pieces.append(fn(text[pos:m.start()]));token=m[0]
        if not (comments and token.startswith('//')):pieces.append(token)
        pos=m.end()
    pieces.append(fn(text[pos:]));return ''.join(pieces)
def projected(text,oldroot=False):
    if text.startswith('alloc'):return text
    def f(s):
        for p in ROOTS:s=s.replace(p,ROOTS[0] if oldroot else '<SOURCE>')
        if not oldroot:s=re.sub(r'(?<=<impl at )<SOURCE>/([^\s:]+):\d+:\d+: \d+:\d+(?=>)',r'<SOURCE>/\1:<DISPLAY-SPAN>',s)
        s=LIFES.sub(r'\1',s)
        return s.replace("selected_outer_request_v1::<'_>",'selected_outer_request_v1')
    return '\n'.join(s.rstrip() for s in outside(text,f).splitlines() if s.strip())
def allocation_shape(text):
    refs=[]
    def f(s):
        def sub(m):refs.append(m[0]);return '<ALLOC>'
        return ALLOC.sub(sub,s)
    if text.startswith('alloc'):
        out=[]
        for line in text.splitlines():
            a,sep,z=line.rpartition('│')
            out.append(f(a)+sep+z if sep else f(line))
        return '\n'.join(out),refs
    return outside(text,f,comments=False),refs
def blocks(stage):
    # Top-level boundaries are structural lines in compiler MIR. Every byte
    # belongs to a construct or to blank/top-level comment text; unknown syntax
    # fails rather than silently disappearing.
    raw=gzip.decompress((V/MIRS[stage]).read_bytes()).decode();out=[];start=None;offset=0;ignored=0
    for line in raw.splitlines(keepends=True):
        stripped=line.rstrip('\r\n')
        if start is None:
            if not stripped.strip() or stripped.startswith('//'):ignored+=len(line)
            else:
                require(not stripped[0].isspace(),'independent MIR top-level indentation')
                require(stripped.startswith(('fn ','const ','static ','alloc')) or '::{constant#' in stripped,'unrecognized top-level syntax')
                if stripped.endswith(';'):out.append(stripped)
                else:require(stripped.endswith(' {'),'non-braced top-level');start=offset
        else:
            if stripped=='}':out.append(raw[start:offset+len(line)].rstrip('\r\n'));start=None
            elif stripped:require(stripped[0].isspace(),'unexpected nested top-level line')
        offset+=len(line)
    require(start is None and offset==len(raw),'complete MIR coverage')
    return out,{'raw_sha256':sha(raw.encode()),'raw_bytes':len(raw.encode()),'characters':len(raw),'top_level_comment_or_blank_characters':ignored,'constructs':len(out),'uncovered_noncomment_bytes':0}
def isprobe(b,stage):
    h=b.split('\n',1)[0]
    if stage==3 and h.startswith(('static OWNED_PROVIDER_LAYOUT_FORCE_V1:', 'const OWNED_PROVIDER_LAYOUT_FORCE_V1::{constant#')):return True
    return any(h.startswith('fn '+n+'(') or h.startswith(n+'::{constant#') or h.startswith('const '+n+'::{constant#') for n in PROBES[stage])
def isprovider(b):return b.startswith(('fn describe_existing_owner_candidate_v1(', 'fn describe_existing_owner_candidate_v1::', 'const describe_existing_owner_candidate_v1', 'const InputBackingDescriptionV1::'))
def decode_string(token):
    s=token[1:-1];o=[];i=0
    while i<len(s):
        if s[i]!='\\':o.append(s[i]);i+=1;continue
        i+=1;c=s[i];i+=1
        basic={'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\','"':'"',"'":"'"}
        if c in basic:o.append(basic[c])
        elif c=='x':o.append(chr(int(s[i:i+2],16)));i+=2
        elif c=='u':
            require(s[i]=='{','unicode escape open');end=s.index('}',i);o.append(chr(int(s[i+1:end].replace('_',''),16)));i=end+1
        else:raise AssertionError('unsupported cooked string escape '+c)
    result=''.join(o);result.encode('utf8');return result
def census(pool):
    kinds=collections.Counter();lits=[];alloc=[];refs=set();details=[]
    for b in pool:
        k='allocation' if b.startswith('alloc') else 'function' if b.startswith('fn ') else 'singleline_constant' if '\n' not in b else 'braced_constant_static_anonymous';kinds[k]+=1
        refs.update(allocation_shape(b)[1]);details.append({'header':b.split('\n',1)[0],'raw_sha256':sha(b.encode()),'projected_shape_sha256':sha(allocation_shape(projected(b))[0].encode())})
        if k=='allocation':
            h=re.fullmatch(r'(alloc\d+) \(.*?size: (\d+), align: (\d+)\) \{',b.split('\n',1)[0]);require(h is not None,'independent allocation header')
            alloc.append({'id':h[1],'bytes':int(h[2]),'alignment':int(h[3]),'raw_header':h[0],'raw_sha256':sha(b.encode())});continue
        for m in LEX.finditer(b):
            if m[0].startswith('"') and not (m.start()>0 and b[m.start()-1]=='b'):lits.append(decode_string(m[0]))
    ids={a['id'] for a in alloc};values=sorted(set(lits));ml=max(map(lambda s:len(s.encode()),values),default=0);ma=max((x['bytes'] for x in alloc),default=0)
    return {'constructs':len(pool),'counts':dict(kinds),'literal_occurrences':len(lits),'literal_unique':len(values),'literal_values':values,'max_literal_utf8_bytes':ml,'allocations':len(alloc),'unique_allocation_ids':len(ids),'allocation_members':alloc,'unresolved_ids':sorted(refs-ids),'max_allocation_extent':ma,'conditional_conservative_envelope':max(ml,ma)},details
def census_review(stage):
    bs,coverage=blocks(stage);prod=[b for b in bs if not isprobe(b,stage)];probe=[b for b in bs if isprobe(b,stage)]
    p,details=census(prod);q,qd=census(probe);expected=read(C/'constant-census.json')['stages'][stage]
    require(p==expected['production'] and q==expected['query_suffix'],'independent entire census differs')
    require([dict(header=b.split('\n',1)[0],raw_sha256=sha(b.encode()),raw_text=b) for b in probe]==expected['query_constructs'],'exact query body census')
    save(f'census-stage-{stage}.json',{'schema':1,'source_tree':TREES[stage],'coverage':coverage,'production':p,'query_suffix':q,'construct_inventory':details,'query_inventory':qd})
    print(json.dumps({'stage':stage,'production_constructs':len(prod),'query_constructs':len(probe),'literal_occurrences':p['literal_occurrences'],'envelope':p['conditional_conservative_envelope'],'complete_independent_census':True}))
def compare(old,new):
    require(len(old)==len(new),'independent full transport count')
    mapping={};inverse={};od={};nd={};oc=collections.defaultdict(set);nc=collections.defaultdict(set);context=None;positions=[];nonalloc=[]
    def bind(a,b):
        require(mapping.get(a,b)==b and inverse.get(b,a)==a,'allocation role non-bijection');mapping[a]=b;inverse[b]=a
    def match(a,b):
        aa,ar=allocation_shape(a);bb,br=allocation_shape(b);require(aa==bb,'complete typed operation/payload mismatch '+a[:180]);require(len(ar)==len(br),'allocation role arity')
        for x,y in zip(ar,br):bind(x,y)
    for i,(a,b) in enumerate(zip(old,new)):
        a=projected(a);b=projected(b)
        require(a.startswith('alloc')==b.startswith('alloc'),'construct kind mismatch')
        if a.startswith('alloc'):
            x=ALLOC.match(a)[0];y=ALLOC.match(b)[0];require(od.get(x,a)==a and nd.get(y,b)==b,'repeated ID payload mismatch')
            od[x]=a;nd[y]=b;oc[x].add(context);nc[y].add(context);positions.append((x,y))
        else:
            match(a,b);context=sha(allocation_shape(a)[0].encode());nonalloc.append({'index':i,'header':a.split('\n',1)[0],'shape_sha256':context})
    visited=set()
    while len(visited)<len(od):
        todo=[a for a in mapping if a in od and a not in visited]
        if not todo:
            left=collections.defaultdict(list);right=collections.defaultdict(list)
            for a in set(od)-visited:left[(allocation_shape(od[a])[0],tuple(sorted(oc[a])))].append(a)
            for b in set(nd)-set(inverse):right[(allocation_shape(nd[b])[0],tuple(sorted(nc[b])))].append(b)
            for key,aa in left.items():
                bb=right.get(key,[])
                if len(aa)==len(bb)==1:bind(aa[0],bb[0])
            todo=[a for a in mapping if a in od and a not in visited];require(todo,'unresolved ambiguous allocation mapping')
        for a in todo:
            require(mapping[a] in nd,'relocation unresolved');match(od[a],nd[mapping[a]]);visited.add(a)
    require(set(mapping)==set(od) and set(inverse)==set(nd),'complete allocation identity coverage')
    require(all(mapping[a]==b for a,b in positions),'allocation occurrence positions disagree with role-derived mapping')
    return {'constructs':len(old),'functions':sum(b.startswith('fn ') for b in old),'singleline_constants':sum('\n' not in b for b in old),'allocation_occurrences':len(positions),'allocation_ids':len(od),'mapping':mapping,'all_nonallocation_rows':nonalloc,'allocation_pairing_uses_offset_or_position':False,'complete_typed_body_payload_extent_alignment_relocation_equality':True}
def transport_review(which):
    cur,_=blocks(3);cur=[b for b in cur if not isprobe(b,3)]
    if which=='scoped':
        old,_=blocks(2);old=[b for b in old if not isprobe(b,2)];cur=[b for b in cur if not isprovider(b)]
        r=compare(old,cur);require(r['constructs']==6006 and r['singleline_constants']==1785,'full6006 amendment missing');expected=read(C/'full-base-correspondence.json')
    else:
        old,_=blocks(0);oldconst=next(b for b in old if b.startswith('const COMPILED: '));values=[decode_string(m[0]) for m in LEX.finditer(oldconst) if m[0].startswith('"')]
        require(len(values)==5 and all(len(x.encode())==64 for x in values),'exact original identity literals')
        def payload(b):
            if not b.startswith('alloc'):return None
            raw=[]
            for line in b.splitlines()[1:-1]:
                p=line.split('│')
                if len(p)!=3 or not all(re.fullmatch('[0-9a-f]{2}',w) for w in p[1].split()):return None
                raw.extend(int(w,16) for w in p[1].split())
            return bytes(raw)
        removed=[b for b in old if payload(b) in {s.encode() for s in values}];require(len(removed)==5,'exact five allocation removals')
        index=collections.defaultdict(list)
        for i,b in enumerate(cur):
            if not b.startswith('alloc'):index[allocation_shape(projected(b))[0]].append(i)
        used=set();rows=[];unmatched=[]
        for b in old:
            if b.startswith('alloc'):continue
            choices=[i for i in index[allocation_shape(projected(b))[0]] if i not in used]
            if not choices:unmatched.append(b);continue
            i=choices[0];used.add(i);rows.append({'old_header':b.split('\n',1)[0],'current_header':cur[i].split('\n',1)[0],'old_raw_sha256':sha(b.encode()),'current_raw_sha256':sha(cur[i].encode())})
        require(unmatched==[oldconst],'all original nonallocation bodies except COMPILED correspond')
        new=[b for i,b in enumerate(cur) if b.startswith('alloc') or i in used]
        r=compare([b for b in old if b not in removed and b!=oldconst],new);require(r['constructs']==5987 and r['functions']==2009,'original whole conservation');r['nonallocation_occurrence_mapping']=rows;r['five_removed_allocations']=[b.split('\n',1)[0] for b in removed];expected=read(C/'original-allocation-transport.json')
    require(r['mapping']==expected['allocation_mapping'],'independently derived mapping differs from candidate')
    save('transport-'+which+'.json',r);print(json.dumps({k:v for k,v in r.items() if not isinstance(v,(list,dict))}))
def sources():
    a={x['path']:(R/x['source']).read_bytes() for x in read(V/'swift-guarded-snapshot-loader-work-source146/source-reference-map.json')['members']}
    b={x['path']:(R/x['origin']).read_bytes() for x in read(V/'swift-guarded-snapshot-scoped-binding-source/accepted-source-custody.json')}
    c={x['path']:(V/'swift-guarded-snapshot-scoped-binding-source/source/vm'/x['path']).read_bytes() for x in read(V/'swift-guarded-snapshot-scoped-binding-source/source-manifest.json')['members']}
    d={x['path']:(R/x['origin']).read_bytes() for x in read(V/'swift-guarded-snapshot-owned-binding-provider/proposed-source-custody.json')}
    for table,tree in zip((a,b,c,d),TREES):
        members=[row(n,table[n]) for n in sorted(table,key=Path)]
        require(len(table)==146 and sha(canon(members))==tree,'independent actual source146 tree')
    return a,b,c,d
def source_norm(text):
    def f(s):
        s=re.sub(r'\b('+'|'.join(TYPES)+r")<'(?:p0|_)>",r'\1',s)
        return s.replace("selected_outer_request_v1<'p0>",'selected_outer_request_v1').replace("&'p0 ","&'static ")
    return '\n'.join(s.rstrip() for s in outside(text,f).splitlines() if s.strip())
def source_review():
    a,b,c,d=sources();transitions=[]
    for old,new in zip((a,b,c),(b,c,d)):
        require([n for n in old if old[n]!=new[n]]==[PROFILE],'only profile changed across lineage')
        transitions.append({'unchanged_members':145,'changed_member':PROFILE,'old_sha256':sha(old[PROFILE]),'current_sha256':sha(new[PROFILE])})
    outer=(V/'swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs').read_bytes()
    require(b[PROFILE]==a[PROFILE][:-2]+b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n'+outer+b'}\n','original outer append exact')
    changed=b[PROFILE].decode()
    for x in read(V/'swift-guarded-snapshot-scoped-binding-source/exact-edits.json'):
        require(changed.count(x['before'])==x['occurrences'],'exact lifetime occurrence count');changed=changed.replace(x['before'],x['after'])
    require(changed.encode()==c[PROFILE] and source_norm(b[PROFILE].decode())==source_norm(changed),'exact lifetime only edit')
    fragment=(V/'swift-guarded-snapshot-owned-binding-provider/existing-owner-candidate.inc.rs').read_bytes()
    require(d[PROFILE]==c[PROFILE][:-5]+b'\n\n// Isolated unqualified existing-owner preparation proposal.\n'+fragment+b'\n}\n}\n','provider append exact')
    queries=[]
    for stage,table in [(1,dict(b)),(2,dict(c)),(3,dict(d))]:
        if stage==1:
            p=V/'swift-guarded-snapshot-outer-parent-independent';table[PROFILE]=table[PROFILE].replace(outer,outer[:-2]+b'\n'+(p/'query-layout.inc.rs').read_bytes()+b'}\n',1);table[ACCOUNT]+=b'\n'+(p/'query-account-layout.inc.rs').read_bytes();mf=p/'query-source-manifest.json'
        elif stage==2:
            p=V/'swift-guarded-snapshot-scoped-binding-source';tail=b'\n'.join((p/n).read_bytes() for n in ('query-layout.inc.rs','query-result-layout.inc.rs','positive.inc.rs'));table[PROFILE]=table[PROFILE][:-4]+b'\n'+tail+b'}\n}\n';table[ACCOUNT]+=b'\n'+(p/'query-account-layout.inc.rs').read_bytes();mf=p/'positive-source-manifest.json'
        else:
            p=V/'swift-guarded-snapshot-owned-provider-work-storage';needle=fragment+b'\n}\n}\n';require(table[PROFILE].endswith(needle),'provider query anchor');table[PROFILE]=table[PROFILE][:-len(needle)]+fragment[:-2]+(p/'query-layout.inc.rs').read_bytes()+fragment[-2:]+b'\n}\n}\n';require(table[PROFILE]==(p/'query-profile.rs').read_bytes(),'actual current query profile reconstruction');mf=p/'query-source-manifest.json'
        members=[row(n,table[n]) for n in sorted(table,key=Path)];manifest=read(mf)
        require(members==manifest['members'] and sha(canon(members))==manifest['tree_sha256'],'complete compiler query source146 reconstruction')
        queries.append({'stage':stage,'tree_sha256':sha(canon(members)),'members':146})
    origin=read(C/'source-owner-alias-rebind.json');aliases=[];destinations=[];constants=[]
    for x in origin['source_aliases']:
        for s in x['current_sites']:
            line=d[s['path']].decode().splitlines()[s['line']-1]
            require(line==s['current_declaration'] and sha(d[s['path']])==s['source_sha256'],'source alias current owner bytes')
            require(source_norm(line)==source_norm(s['declaration']),'source alias preserved declaration')
        if not x['current_sites']:require(x['canonical_path'].startswith('std::') and x['standard_compiler_path']==x['canonical_path'],'standard alias exact path')
        aliases.append(x['compiler_alias'])
    for x in origin['complete_authored_destinations']:
        if 'current_source_origin' in x:
            s=x['current_source_origin'];require(d[s['path']].decode().splitlines()[s['line']-1]==s['text'] and sha(d[s['path']])==s['source_sha256'],'authored destination exact current owner')
        else:require(x['source_origin'] is None,'unexpected absent current owner')
        destinations.append({'target':x['target'],'definition':x['definition'],'historical_destination':x['destination'],'current_owner':x.get('current_source_origin'),'source_origin_is_synthetic_constructor':x['source_origin'] is None})
    for x in origin['typed_constant_origins']:
        if 'source_path' in x:require(x['declaration'] in d[x['source_path']].decode() and sha(d[x['source_path']])==x['current_source_sha256'],'typed constant actual declaration')
        else:require(x['constant'] in ('core::num::<impl u64>::MAX','core::num::<impl usize>::MAX'),'unknown primitive constant origin')
        constants.append(x)
    require((len(aliases),len(destinations),len(constants))==(129,426,14),'complete origin census')
    profile=d[PROFILE].decode();account=d[ACCOUNT].decode();loader=d['src/experimental_swift_reactor/retained_profile_loader_v1.rs'].decode()
    # These exact actual-source fragments are read together with all unchanged
    # typed bodies; they do not establish a future caller from syntax alone.
    fragments=["struct ReviewedFixtureBindingV1<'p0> {\n        paths: [&'p0 Path; 5],", "struct FrozenFixtureV1<'p0> { binding: &'p0 ReviewedFixtureBindingV1<'p0> }", "struct PreexistingImmutableBindingV1<'p0> {\n        binding: ReviewedFixtureBindingV1<'p0>,\n        native_path_bodies: [&'p0 [u8]; 5],\n        identities: ImmutableFixtureIdentitiesV1<'p0>,",'let cancellation = Cancellation::default();','let LoaderOutcomeV1 { selected, files, usage } = load_selected_retained_profile_v1(','Ok(selected) => PrimaryOutcomeV1::Leaf(invoke_loaded_leaf_once_v1(\n                selected, binding.product_budget, Instant::now(), cancellation.clone(),','let fixture = FrozenFixtureV1 { binding: &request.preexisting.binding };','let retirement = match destroy_returned_fixture_v1(owned) {\n            Some(destroyed) => {','release_after_retirement_v1(destroyed);','Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)']
    for s in fragments:require(s in profile,'actual caller obligation/source route')
    require('Err(RefusalV1::RootPolicyPending)' in account and 'Err(RefusalV1::WholeQuotePending)' in account,'root account and quote remain pending')
    owner_structs=["struct "+name+"<'p0>" for name in TYPES]
    require(all(profile.count(s)==1 for s in owner_structs),'exact shared lifetime owner declarations')
    mentions=[]
    for p,data in d.items():
        for n,line in enumerate(outside(data.decode(),lambda s:s).splitlines(),1):
            if re.search(r'\bdescribe_existing_owner_candidate_v1\b',line):mentions.append({'path':p,'line':n,'text':line})
    require(len(mentions)==1 and 'pub(super) fn describe_existing_owner_candidate_v1' in mentions[0]['text'],'provider production source declaration only')
    const=read(C/'compiler-constant-review.json');keys=const['environment_keys'];receipt=read(V/'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/receipt.json');oldreceipt=read(V/'swift-guarded-snapshot-loader-work-source146/compiler-receipt.json')
    require(all(k not in receipt['environment'] for k in keys),'current identity env absent');require([oldreceipt['environment'][k] for k in keys]==const['old_values'],'old five exact compiler identities')
    require(const['source_declaration'] in loader and sha(d['src/experimental_swift_reactor/retained_profile_loader_v1.rs'])==const['source_sha256'],'actual COMPILED source')
    # Read the actual check and the closure instead of inferring a successful
    # path from the now-None constant. Full graph retention is separately tested.
    require('let embedded = COMPILED.map(|v| v.and_then(|s| parse_hex(s.as_bytes())));\n    if embedded.iter().any(Option::is_none) {\n        return Err(LoaderFailureV1::new(\n            Refusal::UnsupportedBuild,' in loader,'actual current loader refusal check')
    save('source-review.json',{'schema':1,'trees':TREES,'transitions':transitions,'query_reconstructions':queries,'complete_source_aliases':aliases,'authored_destination_origins':destinations,'typed_constant_origins':constants,'actual_caller_fragments':fragments,'provider_source_mentions':mentions,'current_compiler_environment_has_identity_keys':False,'COMPILED_change_is_substantive':True,'current_query_success_proof':False,'conditional_success_obligations_retained':True,'owner_authentication_acquisition_and_P0_pending':True})
    print(json.dumps({'source_lineage_and_queries_reconstructed':True,'aliases':len(aliases),'destination_origins':len(destinations),'constant_origins':len(constants),'actual_caller_qualified':False}))
def accepted_modules():
    folder=V/'swift-guarded-snapshot-string-exact-binding-correction';sys.path.insert(0,str(folder))
    def mod(name):
        spec=importlib.util.spec_from_file_location(name,folder/(name+'.py'));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
    return mod('mir_graph'),mod('type_contracts')
def graph_inputs():
    bs,_=blocks(3);prod=[b for b in bs if not isprobe(b,3)];text='\n'.join(projected(b,oldroot=True) for b in prod)+'\n';src={p:b.decode() for p,b in sources()[3].items() if p.endswith('.rs')};return bs,prod,text,src
def typed_review():
    M,T=accepted_modules();bs,prod,text,src=graph_inputs();graph=M.analyze(text,src);require(graph==read(C/'selected-graph.json'),'accepted resolver rebuilt actual current graph')
    fs,byname,bybase=M.parse_functions(text,src);raw=M.parse_functions('\n'.join(prod)+'\n',src)[0]
    require({k:{n:r[n] for n in ('name','header','params','return_type','local_types')} for k,r in raw.items()}==read(C/'raw-current-typed-headers.json'),'all raw current typed headers')
    old,_=blocks(0);oldfs=[b for b in old if b.startswith('fn ')];curfs=[b for b in prod if b.startswith('fn ')];index=collections.defaultdict(list)
    for i,b in enumerate(curfs):index[allocation_shape(projected(b))[0]].append(i)
    forward={};used=set();mapping=[]
    for i,b in enumerate(oldfs):
        options=[j for j in index[allocation_shape(projected(b))[0]] if j not in used];require(options,'original complete typed function missing');j=options[0];used.add(j);forward[f'f{i:04d}']=f'f{j:04d}';mapping.append({'old':f'f{i:04d}','current':f'f{j:04d}','old_header':b.split('\n',1)[0],'current_header':curfs[j].split('\n',1)[0],'old_raw_sha256':sha(b.encode()),'current_raw_sha256':sha(curfs[j].encode())})
    saved=read(C/'definition-role-map.json');require([{k:r[k] for k in mapping[0]} for r in saved['all_function_rows']]==mapping,'all2009 definition roles independently reconstructed')
    accepted=read(V/'swift-guarded-snapshot-string-exact-binding-correction/graph.json')
    for k,r in accepted['nodes'].items():require(sha((oldfs[int(k[1:])]+'\n').encode())==r['MIR_sha256'],'accepted original raw selected body identity')
    # Historical graph line numbers include raw compiler comments. Reconstruct
    # the original graph using the same independently written display-only
    # projection, then transport actual typed statements and callsite roles.
    original=M.analyze('\n'.join(projected(b,oldroot=True) for b in old)+'\n',{p:b.decode() for p,b in sources()[0].items() if p.endswith('.rs')})
    require(set(original['nodes'])==set(accepted['nodes']),'original accepted root closure')
    require(set(graph['nodes'])=={forward[k] for k in original['nodes']},'full potential success selected bodies retained')
    ed=lambda es:sorted(es,key=lambda e:(e['caller'],e['line'],e['kind'],e['callee']))
    mapped_edges=ed([dict(e,caller=forward[e['caller']],callee=forward[e['callee']]) for e in original['edges']]);require(ed(graph['edges'])==mapped_edges,'all potential success edges independently transported')
    require(forward['f1405']=='f1412' and any(e['caller']=='f1612' and e['callee']=='f1704' for e in graph['edges']),'changed IDs and transitive edge exact')
    equations=[];named=[];closures=[]
    for caller,r in graph['nodes'].items():
        for call in r['calls']:
            dests=M.resolve(call['target'],fs,byname,bybase);M.validate_authored_call(call['target'],call,dests,fs) if dests else None
            for dest in dests:
                decl=fs[dest];templates=list(decl['params'].values())+[decl['return_type']];actuals=[a['type'] for a in call['arguments']]+[call['result_type']];require(len(templates)==len(actuals),'full positional equation arity');bindings={};eq=[]
                for a,b in zip(templates,actuals):
                    T.unify_closure(a,b,bindings,fs) if a.startswith('impl Fn') else T.unify(a,b,bindings);eq.append({'template':a,'actual':b,'bindings_after':dict(bindings)})
                equations.append({'caller':caller,'callee':dest,'line':call['line'],'target':call['target'],'equations':eq,'substitutions':bindings})
            for item in call['named_callbacks']:
                dests=M.resolve(item,fs,byname,bybase)
                if dests:named.append({'caller':caller,'line':call['line'],'callback':item,'contract':M.validate_named_callback(item,call['target'],dests,fs)})
            for site in call['closures']:closures.append({'caller':caller,'line':call['line'],'site':site,'contract':M.validate_closure_callback(site,call,[k for k,r in fs.items() if r['closure_site']==site],fs)})
    eqsaved=read(C/'typed-equations.json');require(equations==eqsaved['equations'] and named==eqsaved['named_callback_sites'] and closures==eqsaved['closure_sites'],'complete typed equation/callback reconstruction')
    require(eqsaved['source_aliases']==T.ALIASES and eqsaved['finite_specializations']==T.SPECIALIZATIONS and eqsaved['finite_constant_types']==T.CONSTANT_TYPES,'exact finite type context')
    # Reconstruct the carrier fixed point, every incoming edge, and every
    # operation from the actual graph. Declarations are tied back to source.
    ci=read(C/'carrier-induction.json');decls=ci['declarations']
    for r in decls:
        clean='\n'.join(outside(line,lambda s:s) for line in src[r['path']].splitlines())
        require(r['declaration'] in clean and sha(r['declaration'].encode())==r['declaration_sha256'],'carrier actual declaration')
        require(sorted(set(re.findall(r'\b[A-Za-z_]\w*\b',r['declaration'])))==r['tokens'],'complete carrier declaration tokens')
    names={r['name'] for r in decls if 'str' in r['tokens']}|{'Policy'}
    while True:
        new=names|{r['name'] for r in decls if set(r['tokens'])&names}
        if new==names:break
        names=new
    require(sorted(names)==ci['carrier_names'],'independent carrier fixed point')
    inbound=collections.defaultdict(list)
    for e in graph['edges']:
        call=next(c for c in graph['nodes'][e['caller']]['calls'] if c['line']==e['line']);inbound[e['callee']].append(dict(e,arguments=call['arguments'],statement=call['statement']))
    def carrier(t):return bool(re.search(r'\bstr\b',t) or set(re.findall(r'\b[A-Za-z_]\w*\b',t))&names or '::Failure' in t)
    ports=[];ops=[]
    for k,r in graph['nodes'].items():
        locals_={p:t for p,t in r['local_types'].items() if carrier(t)}
        for p,t in r['params'].items():
            if carrier(t):ports.append({'function':k,'parameter':p,'type':t,'incoming':inbound[k]})
        for s in r['typed_statements']:
            refs=set(re.findall(r'\b_\d+\b',s['statement']));uses={p:locals_[p] for p in sorted(refs&locals_.keys())}
            if uses or any(n in s['statement'] for n in names):ops.append(dict(s,function=k,carrier_locals=uses))
    require(ports==ci['incoming_ports'] and ops==ci['carrier_operations'] and graph['source_str_assignments']==ci['all_str_assignments'] and graph['direct_str_parameters']==ci['direct_ports'],'all carrier edges and operations')
    # No incoming authored call or named item uses the provider. Its extra
    # reified pointer is only in the separately reconstructed query suffix.
    incoming=[{'caller':k,'call':c} for k,r in fs.items() for c in r['calls'] if 'describe_existing_owner_candidate_v1' in c['target'] or any('describe_existing_owner_candidate_v1' in x for x in c['named_callbacks'])];require(not incoming,'provider is production-called')
    save('typed-graph-review.json',{'schema':1,'current_functions':len(fs),'definition_role_rows':mapping,'selected_bodies':len(graph['nodes']),'selected_edges':len(graph['edges']),'all_success_edges_transported':True,'direct_equation_edges':len(equations),'positional_equations':sum(len(r['equations']) for r in equations),'nonidentical_pairs':len({(e['template'],e['actual']) for r in equations for e in r['equations'] if e['template']!=e['actual']}),'named_sites':len(named),'named_edges':sum(e['kind']=='named-authored-callback' for e in graph['edges']),'exact_closure_contracts':len({r['site']+' | '+str(r['contract']['outer_identity']) for r in closures}),'direct_str_ports':len(graph['direct_str_parameters']),'str_assignments':len(graph['source_str_assignments']),'carrier_ports':len(ports),'carrier_operations':len(ops),'provider_incoming_production_uses':incoming,'envelope_is_conditional_only':True,'actual_current_success_qualified':False})
    print(json.dumps({'complete_actual_typed_graph_reconstructed':True,'bodies':len(graph['nodes']),'edges':len(graph['edges']),'positional_equations':sum(len(r['equations']) for r in equations),'carrier_ports':len(ports)}))
def refused(fn,*args):
    try:fn(*args)
    except (ValueError,AssertionError):return True
    raise AssertionError('adverse control unexpectedly accepted')
def census_controls():
    bs,_=blocks(3);prod=[b for b in bs if not isprobe(b,3)];base=[b for b in prod if not isprovider(b)];scoped,_=blocks(2);scoped=[b for b in scoped if not isprobe(b,2)];tests=[]
    # The array-length constant belongs to the original COMPILED object but
    # must survive its substantive payload exception. This targets the exact
    # prior overly broad prefix, not an arbitrary first constant.
    i=next(i for i,b in enumerate(base) if b.startswith('const COMPILED::{constant#') and '\n' not in b)
    changed=list(base);del changed[i];refused(compare,scoped,changed);tests.append('COMPILED independent array-length constant deletion refused')
    changed=list(base);changed[i]=changed[i].replace('5_usize','4_usize');require(changed[i]!=base[i],'actual array-length control changed');refused(compare,scoped,changed);tests.append('COMPILED array-length value 5 to 4 refused')
    # Coherent arbitrary allocation renaming is a positive control. It checks
    # that offset and occurrence numbers do not authorize an allocation pair.
    def rename(b):
        def f(s):return ALLOC.sub(lambda m:'alloc'+str(int(m[0][5:])+100003),s)
        if b.startswith('alloc'):
            out=[]
            for s in b.splitlines():
                a,sep,z=s.rpartition('│');out.append(f(a)+sep+z if sep else f(s))
            return '\n'.join(out)
        return outside(b,f,comments=False)
    renamed=[rename(b) for b in base];r=compare(scoped,renamed);require(r['allocation_ids']==1459,'positive allocation rename full coverage');tests.append('all1459 allocations coherently renamed by arbitrary IDs accepted')
    changed=list(renamed);j=next(j for j,b in enumerate(changed) if b.startswith('alloc') and len(allocation_shape(b)[1])>1);b=changed[j];refs=allocation_shape(b)[1];target=next(x for x in r['mapping'].values() if x!=refs[1]);changed[j]=b.replace(refs[1],target,1);refused(compare,scoped,changed);tests.append('same-payload relocation target substitution refused')
    # A cooked supplementary-plane value is measured in UTF-8 bytes, never
    # Unicode scalars. The new real selected literal is 5084 bytes/1271 scalars.
    k=next(k for k,b in enumerate(prod) if 'const "swift_cache_layout_overflow"' in b);mutated=list(prod);mutated[k]=mutated[k].replace('const "swift_cache_layout_overflow"','const "'+('\\u{1f680}'*1271)+'"',1)
    c,_=census(mutated);require(c['max_literal_utf8_bytes']==c['conditional_conservative_envelope']==5084,'UTF8 envelope recomputation');refused(compare,prod,mutated);tests.append('actual selected1271-scalar literal recomputes5084 UTF8 bytes and refuses exact transport')
    token='"'+ROOTS[3]+' FrozenFixtureV1::<'+'_> alloc100 // literal"';require(token in projected('const TEST: &str = '+token+';'),'projection literal untouched');require(token in allocation_shape('const TEST: &str = '+token+';')[0],'literal alloc spelling untouched');tests.append('scratch/lifetime/allocation-looking tokens inside literals remain exact')
    require(not isprobe('fn foreign::owned_provider_remaining_layout_query_v1() -> () {\n}',3),'foreign query name must remain production');tests.append('foreign query basename is never excluded')
    save('fresh-census-controls.json',{'schema':1,'tests':tests,'count':len(tests),'all_pass':True,'mutation_scope':'in-memory actual frozen MIR; no Rust compiler or product runtime'});print(json.dumps({'fresh_census_controls':len(tests),'all_pass':True}))
def typed_controls():
    M,T=accepted_modules();bs,prod,text,src=graph_inputs();fs,byname,bybase=M.parse_functions(text,src);g=read(C/'selected-graph.json');tests=[];identities={};signatures={}
    for k,r in g['nodes'].items():
        for c in r['calls']:
            dests=M.resolve(c['target'],fs,byname,bybase)
            if dests:
                identities[c['target']]=(c,dests);signatures[(c['target'],tuple(a['type'] for a in c['arguments']),c['result_type'])]=(c,dests)
    # Three catalog entries enter only as named callbacks. Bind every exact
    # catalog declaration to actual current definitions, then exercise all434
    # recorded typed signatures, including those named function-item contracts.
    direct_targets=len(identities);direct_signatures=len(signatures);identities={};signatures={}
    for target,contract in M.authored_catalog().items():
        dests=M.resolve(target,fs,byname,bybase);require(dests,'catalog definition absent from actual current MIR')
        for sig in contract['signatures']:
            call={'target':target,'arguments':[{'operand':'catalog-signature-position-'+str(i),'type':t} for i,t in enumerate(sig['arguments'])],'result_type':sig['result']}
            M.validate_authored_call(target,call,dests,fs);identities[target]=(call,dests);signatures[(target,tuple(sig['arguments']),sig['result'])]=(call,dests)
    require(len(identities)==423 and len(signatures)==434,'complete exact finite catalog census')
    # Foreign prefixes preserve the full apparent basename and every generic
    # argument. New identity cannot bind an exact known source definition.
    for target,(c,dests) in identities.items():require(not M.resolve('shadow_owner_v1::'+target,fs,byname,bybase),'new prefixed identity fallback')
    tests.append({'test':'every423 current complete target rejects prefixed owner preserving original identity tail','controls':len(identities)})
    for target,(c,dests) in signatures.items():
        changed=copy.deepcopy(c);changed['result_type']='[('+c['result_type']+',); 2]';refused(M.validate_authored_call,c['target'],changed,dests,fs)
    tests.append({'test':'every434 exact current signature refuses result nested in array-of-tuple','controls':len(signatures)})
    permuted=0
    for c,dests in signatures.values():
        if len(c['arguments'])<2:continue
        j=next((j for j in range(1,len(c['arguments'])) if c['arguments'][j]['type']!=c['arguments'][0]['type']),None)
        if j is None:continue
        changed=copy.deepcopy(c);changed['arguments'][0],changed['arguments'][j]=changed['arguments'][j],changed['arguments'][0];refused(M.validate_authored_call,c['target'],changed,dests,fs);permuted+=1
    tests.append({'test':'distinct positional argument types exchanged at actual current calls','controls':permuted})
    nested=next((c,d) for c,d in signatures.values() if any('Result<' in a['type'] or 'Option<' in a['type'] for a in c['arguments']))
    c,dests=nested;changed=copy.deepcopy(c);j=next(j for j,a in enumerate(c['arguments']) if 'Result<' in a['type'] or 'Option<' in a['type']);changed['arguments'][j]['type']=changed['arguments'][j]['type'].replace('Option<','foreign::Option<').replace('Result<','foreign::Result<');refused(M.validate_authored_call,c['target'],changed,dests,fs);tests.append({'test':'nested Option/Result namespace stays exact in actual current argument','controls':1})
    # Actual new provider callback is outside the selected roots. Adding a
    # selected edge to it cannot be licensed by the existing graph contracts.
    provider=next(k for k,r in fs.items() if r['name']=='describe_existing_owner_candidate_v1');require(provider not in g['nodes'],'provider remains outside selected closure')
    call=next(c for r in g['nodes'].values() for c in r['calls'] if c['closures']);site=call['closures'][0];dests=[k for k,r in fs.items() if r['closure_site']==site];M.validate_closure_callback(site,call,dests,fs)
    changed=copy.deepcopy(fs);first=dests[0];changed[first]['params']['_1']='&mut '+changed[first]['params']['_1'];refused(M.validate_closure_callback,site,call,dests,changed);tests.append({'test':'actual selected closure environment gains extra mutable borrow and refuses','controls':1})
    named=next(c for r in g['nodes'].values() for c in r['calls'] if 'accounted::AccountedWasi::usage' in c['named_callbacks']);item='accounted::AccountedWasi::usage';dests=M.resolve(item,fs,byname,bybase);M.validate_named_callback(item,named['target'],dests,fs)
    changed=copy.deepcopy(fs)
    for k in dests:changed[k]['return_type']='(experimental_wasi::WasiUsage, ())'
    refused(M.validate_named_callback,item,named['target'],dests,changed);tests.append({'test':'actual named usage callback wraps return in tuple and refuses','controls':1})
    # Source+typed metadata can neither prune successful-path obligations on
    # current None nor treat a raw function ID as an immutable definition.
    old,_=blocks(0);oldfs=[b for b in old if b.startswith('fn ')];curfs=[b for b in prod if b.startswith('fn ')];mapping=read(D/'typed-graph-review.json')['definition_role_rows'];actual={r['current']:r for r in mapping};require(actual['f1412']['old']=='f1405','renumbered critical definition preserved')
    forged=copy.deepcopy(actual['f1412']);forged['current']='f1405';require(sha(curfs[int(forged['current'][1:])].encode())!=forged['current_raw_sha256'],'stale ID accidentally matches');tests.append({'test':'stale f1405 label cannot stand in for actual f1412 definition','controls':1})
    duplicate=collections.Counter(allocation_shape(projected(b))[0] for b in curfs);require(any(n>1 and 'SnapshotAdmissionErrorV1::Stop' in key for key,n in duplicate.items()),'duplicate constructor occurrences retained');tests.append({'test':'duplicate fully qualified constructor bodies retain separate occurrences','controls':1})
    save('fresh-typed-controls.json',{'schema':1,'tests':tests,'test_groups':len(tests),'controls':sum(x['controls'] for x in tests),'direct_observed_resolved_targets':direct_targets,'direct_observed_resolved_signatures':direct_signatures,'catalog_targets':len(identities),'catalog_signatures':len(signatures),'all_pass':True,'basis':'new current-input mutations using accepted exact identity/type/callback checker; all catalog definitions rebound to actual current MIR; no producer test methods imported'});print(json.dumps({'fresh_typed_groups':len(tests),'controls':sum(x['controls'] for x in tests),'all_pass':True}))
def caller_controls():
    _,_,_,d=sources();source=d[PROFILE].decode();report=read(D/'source-review.json');tests=[]
    def validate(actual):
        for s in report['actual_caller_fragments']:require(s in actual,'current caller route changed')
        require(source_norm(actual)==source_norm(source),'whole source caller/owner change beyond scoped lifetime')
    validate(source)
    mutations=[('selected proof argument replaced before leaf','selected, binding.product_budget, Instant::now(), cancellation.clone(),','forged_selected, binding.product_budget, Instant::now(), cancellation.clone(),'),('shared binding changed to mutable owner',"binding: &'p0 ReviewedFixtureBindingV1<'p0>","binding: &'p0 mut ReviewedFixtureBindingV1<'p0>"),('native backing lifetime severed',"native_path_bodies: [&'p0 [u8]; 5]","native_path_bodies: [&'static [u8]; 5]"),('fresh cancellation replaced','let cancellation = Cancellation::default();','let cancellation = caller_cancellation;'),('loader no longer supplies selected','let LoaderOutcomeV1 { selected, files, usage } = load_selected_retained_profile_v1(','let LoaderOutcomeV1 { selected, files, usage } = substitute_loader('),('unconditional retirement release','Some(destroyed) => {','Some(destroyed) => { arbitrary_release();'),('binding selector mints an owner','Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)','Ok(forged_request)'),('custom callback enters','reservation.dispatch_v1(|| run_prepaid_fixture_v1(fixture))','reservation.dispatch_v1(custom_callback)'),('File setup Read owner substituted','File::open(binding.paths[stage])','ForeignReader::open(binding.paths[stage])')]
    for name,before,after in mutations:
        require(before in source,'fresh actual source mutation anchor '+name);mutated=source.replace(before,after,1)
        # Static lifetime replacement is outside the exact eighteen reviewed
        # source edits even though lifetime projection intentionally agrees.
        if name=='native backing lifetime severed':require(mutated!=source and sha(mutated.encode())!=sha(source.encode()),'exact source tree must reject unreviewed lifetime choice')
        else:refused(validate,mutated)
        tests.append(name)
    contract=read(C/'caller-contract.json');flags=['L_str_selected','whole_host_funding','operational_grant','OTA','GA','authenticated_owner_created_by_provider','actual_acquisition_implemented','actual_P0_root_caller_and_fixture_binding_selected','current_success_path_executed','current_metadata_query_is_final_fixture_executable','current_compiled_five_identity_values_present']
    require(all(contract[k] is False for k in flags),'unqualified authority must remain false');require(contract['future_compiler_identity_change_requires_fresh_rebind'] and contract['potential_success_graph_preserved'],'success obligations may not be removed on early refusal')
    const=read(C/'compiler-constant-review.json');require(const['current_values']==[None]*5 and all(len(s)==64 for s in const['old_values']),'recorded current/old constant values');current,_=blocks(3);b=next(b for b in current if b.startswith('const COMPILED: '));require(projected(b)==const['current_typed_constant'],'actual typed compiler constant')
    mutated=b.replace('_1 = Option::<&str>::None;','_1 = Option::<&str>::Some(const "'+('f'*6000)+'");',1);c,_=census([mutated]);require(c['conditional_conservative_envelope']==6000 and projected(mutated)!=const['current_typed_constant'],'future injected build identity invalidates current envelope/constant');tests.append('new6000-byte injected identity forces fresh constant/census/build/session/executable rebind')
    save('fresh-caller-controls.json',{'schema':1,'tests':tests,'count':len(tests),'all_pass':True,'authority_flags_preserved_false':flags,'whole_source_membership_remains_required_for_lifetime_changes':True,'none_early_refusal_is_never_success_or_obligation_waiver':True,'native_Path_OsStr_and_io_Error_backing_separate':True});print(json.dumps({'fresh_caller_controls':len(tests),'all_pass':True}))
def main():
    mode=sys.argv[1]
    if mode=='census':census_review(int(sys.argv[2]))
    elif mode=='transport':transport_review(sys.argv[2])
    elif mode=='source':source_review()
    elif mode=='typed':typed_review()
    elif mode=='census-controls':census_controls()
    elif mode=='typed-controls':typed_controls()
    elif mode=='caller-controls':caller_controls()
    else:raise AssertionError('unknown owned review mode')
if __name__=='__main__':main()
