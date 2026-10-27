"""Independent source-slot/layout/call-closure audit. Imports no producer code."""
from pathlib import Path
from collections import Counter, defaultdict
import copy, hashlib, json, platform, re, struct, sys

HERE = Path(__file__).resolve().parent
PRODUCER = HERE.parent / 'swift-guarded-snapshot-encoder-storage-closure'
SOURCE = HERE.parent / 'swift-guarded-snapshot-composition-source-preparation'
ENCODER = HERE.parent / 'swift-guarded-snapshot-encoder-implementation'
BASE = str(SOURCE / 'source/vm/src') + '/'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())
MAX = (1 << 64) - 1

def require(ok, message):
    if not ok:
        raise AssertionError(message)

def checked_sum(values):
    value = 0
    for term in values:
        require(type(term) is int and 0 <= term <= MAX-value, 'u64 add overflow/type')
        value += term
    return value

def norm(text):
    return text.replace(BASE, 'source/')

def sealed(directory, expected):
    seal = (directory/'seal.json').read_bytes()
    require(sha(seal) == expected, 'seal: '+str(directory))
    entries = read(directory/'seal.json')['members']
    require(len({m['path'] for m in entries}) == len(entries), 'duplicate member')
    for m in entries:
        path = directory/m['path']
        require(path.resolve().is_relative_to(directory.resolve()), 'member escapes packet')
        data = path.read_bytes()
        require((len(data), sha(data)) == (m['bytes'],m['sha256']), 'member: '+str(path))
    return {'seal_sha256':sha(seal),'members':len(entries),
            'member_bytes':sum(m['bytes'] for m in entries),'all_bytes_and_hashes_verified':True}

def blocks(text, selected_headers=None):
    result, active = {}, None
    for line in text.splitlines():
        if line.startswith('fn '):
            require(active is None, 'nested MIR body')
            active = [line]
        elif active is not None:
            active.append(line)
            if line == '}':
                header = norm(active[0])
                if selected_headers is None or header in selected_headers:
                    require(header not in result, 'duplicate selected MIR header')
                    result[header] = '\n'.join(active)
                active = None
    require(active is None,'unterminated MIR')
    return result

def split_parameters(text):
    # MIR selected parameters contain nested tuples/generic types; commas inside
    # those types cannot delimit arguments. Ignore the > in a function arrow.
    parts, start, stack = [], 0, []
    opening, closing = '<([{', '>)]}'
    for i, ch in enumerate(text):
        if ch in opening:
            stack.append(ch)
        elif ch in closing and not (ch == '>' and i and text[i-1] == '-'):
            require(stack and opening.index(stack[-1]) == closing.index(ch),'parameter delimiters')
            stack.pop()
        elif ch == ',' and not stack:
            parts.append(text[start:i].strip());start=i+1
    require(not stack,'parameter balance')
    parts.append(text[start:].strip())
    return [p for p in parts if p]

def declaration_map(body):
    header = body.splitlines()[0]
    start, end = header.index('('), header.rindex(') ->')
    parameters = dict(p.split(': ',1) for p in split_parameters(header[start+1:end]))
    declared = {}
    for line in body.splitlines()[1:]:
        m = re.match(r'\s*let (?:mut )?(_\d+): (.*?);\s*//', line)
        if m:
            require(m[1] not in declared, 'duplicate declaration')
            declared[m[1]] = m[2]
    require(not (parameters.keys() & declared.keys()), 'argument/local overlap')
    return parameters, declared

def decode_constant(path):
    text = path.read_text()
    match = re.search(r'constant \[(\d+) x i8\] c"(.*?)"',text)
    require(match is not None,'LLVM byte-array constant')
    raw, i, data = match[2], 0, bytearray()
    while i < len(raw):
        if raw[i] == '\\':
            data.append(int(raw[i+1:i+3],16));i += 3
        else:
            data.append(ord(raw[i]));i += 1
    require(len(data)==int(match[1]) and len(data)%16==0,'LLVM constant length')
    return [struct.unpack_from('<QQ',data,i) for i in range(0,len(data),16)]

def verify_generic_alternatives(generic):
    expected={'crate::experimental::metadata::Signature','crate::Type',
              'crate::experimental::metadata::Import','crate::experimental::metadata::Function',
              'crate::experimental::metadata::Global','crate::experimental::metadata::Export',
              'crate::experimental::metadata::Segment'}
    require(len(generic)==4,'generic identity count')
    for compiler_type, actual_types in generic.items():
        require(len(actual_types)==7 and len(set(actual_types))==7,'generic alternative multiplicity')
        substitutions=set()
        for actual_type in actual_types:
            matches=[t for t in expected if t in actual_type]
            require(len(matches)==1,'unrecognized generic substitution')
            substitutions.add(matches[0])
        require(substitutions==expected,'generic alternative omission')

def verify_acyclic(graph):
    active,done=set(),set()
    def visit(node):
        require(node not in active,'recursive source invocation')
        require(node in graph,'missing graph dependency')
        if node in done:return
        active.add(node)
        for child in graph[node]:visit(child)
        active.remove(node);done.add(node)
    for node in graph:visit(node)

def parse_call(line):
    # Walk backwards from the final call argument delimiter. The producer's
    # forward scanner truncates a target containing for<'a> fn(&'a ...) -> ... .
    statement = norm(line.strip())
    code = statement.split('; //',1)[0]
    if ') -> [' not in code or not re.match(r'_\d+ = ',code):
        return None
    destination, expression = code.split(' = ',1)
    last = expression.rindex(') -> [')
    depth, first = 1, last-1
    while first >= 0:
        if expression[first] == ')': depth += 1
        elif expression[first] == '(':
            depth -= 1
            if depth == 0: break
        first -= 1
    require(first >= 0,'call parentheses')
    return destination, expression[:first], expression[first+1:last], statement

def resolve_product(target, functions):
    path, impl = None, None
    if target in {'field','require','put','optional','result_id','wasi_id','validate_runtime'}:
        method, path = target, 'experimental/swift.rs'
    else:
        method = target.rsplit('::',1)[-1]
        if target.startswith('experimental::account::Buffer::'):
            path='experimental/account.rs'
        elif target.startswith(('snapshot_encoder_v2::','SnapshotViewV2::','SpanCheckV2::')):
            path='experimental/swift.rs'
        elif target.startswith('initial_profile_v1::InitialProfileBorrowV1::'):
            path='experimental_swift_reactor/cache/initial_profile_v1.rs'
        elif target.startswith(('LoaderProvenanceV1::','AdoptionBodyV1::','FileIdentityV1::')):
            path='experimental_swift_reactor/retained_profile_loader_v1.rs'
        elif target.startswith('control::AdoptedProof::'):
            path='experimental_swift_reactor/control.rs';impl=':350:'
        elif target.startswith('control::RuntimeControl::'):
            path='experimental_swift_reactor/control.rs';impl=':590:'
        elif target.startswith('experimental_swift_reactor::cache::SwiftFunctionCache::'):
            path='experimental_swift_reactor/cache.rs'
        elif target.startswith('WasiContext::'):
            path='experimental_wasi/mod.rs'
        else:
            allowed = ('<','Option::','Result::','Vec::','core::','std::')
            require(target.startswith(allowed), 'unclassified callee '+target)
            return None
    candidates = [f['id'] for f in functions if f['source']['path']==path and
                  f['id'].endswith('::'+method) and (impl is None or impl in f['id'])]
    require(len(candidates)==1,'product callee not unique/covered '+target)
    return candidates[0]

def audit_inventory(inv, selected, layouts, capture_shapes, source_manifest):
    functions, roles = inv['functions'], inv['roles']
    require(len(functions)==64 and len(roles)==2658,'cardinality')
    require(len({f['id'] for f in functions})==64,'function uniqueness')
    require(len({r['id'] for r in roles})==2658,'role uniqueness')
    rolemap = {r['id']:r for r in roles}
    referenced = [rid for f in functions for rid in f['role_ids']]
    require(Counter(referenced)==Counter(rolemap.keys()),'omission/overlap in function role ownership')
    by_function, all_calls, closure_creation = [], [], []
    for f in functions:
        body = selected[f['header']]
        args, locals_ = declaration_map(body)
        expected = {k:norm(v) for k,v in (args|locals_).items()}
        actual = [rolemap[rid] for rid in f['role_ids']]
        require(len({r['mir_local'] for r in actual})==len(actual),'slot aliases charged twice')
        require({r['mir_local']:r['compiler_type'] for r in actual}==expected,'slot/type projection')
        debug = defaultdict(list)
        for name, local in re.findall(r'debug (\w+) => (_\d+);',body):
            debug[local].append(name)
        debug = dict(debug)
        declarations={}
        for line in body.splitlines():
            m=re.match(r'\s*let (?:mut )?(_\d+): ',line)
            if m:declarations[m[1]]=line
        def span_of(line):
            m=re.search(r'source/([^:]+):(\d+):(\d+): (\d+):(\d+)',norm(line.split('//',1)[-1]))
            return None if not m else dict(path=m[1],start_line=int(m[2]),start_column=int(m[3]),end_line=int(m[4]),end_column=int(m[5]))
        return_span=span_of(declarations['_0'])
        require(return_span is not None,'missing return source span')
        for r in actual:
            slot = r['mir_local']
            kind = 'return-expression' if slot=='_0' else 'parameter' if slot in args else 'named-local-or-pattern' if slot in debug else 'temporary'
            require(r['kind']==kind and r['debug_names']==debug.get(slot,[]),'source role kind/debug aliases')
            role_name = 'return-expression' if slot=='_0' else 'arg.'+','.join(debug.get(slot,[]) or [slot]) if slot in args else 'local.'+','.join(debug[slot]) if slot in debug else 'temporary.'+slot
            expected_id = f['id']+'::'+role_name+('::'+slot if slot!='_0' else '')
            require(r['id']==expected_id and r['partition']=='encoder-callee',('source role identity/partition',r['id'],expected_id))
            uses = [norm(line.strip()) for line in body.splitlines()
                    if re.search(r'(?<!\w)'+slot+r'(?!\d)',line) and not re.match(r'\s*(let |debug )',line)]
            require(r['source_uses']==uses,'source movement/use edges')
            for prefix, token in [('move_use_count','move '),('copy_use_count','copy ')]:
                count=sum(len(re.findall(r'\b'+token+slot+r'(?!\d)',line)) for line in uses)
                require(r[prefix]==count,'move/copy count')
            for key, marker in [('storage_live_count','StorageLive'),('storage_dead_count','StorageDead')]:
                require(r[key]==sum(marker+'('+slot+')' in line for line in uses),'lifetime marker count')
            require(r['multiplicity']==1,'record/loop multiplication')
            shape = layouts[r['compiler_type']] if '{closure@' not in r['compiler_type'] else (8,8) if r['compiler_type'].startswith('&') else capture_shapes[r['compiler_type']]
            require((r['bytes'],r['alignment'])==shape,'actual compiler layout')
            require(r['type_key'] in inv['types'],'missing type dependency')
            t=inv['types'][r['type_key']]
            require((t['compiler_identity'],t['bytes'],t['alignment'])==(r['compiler_type'],*shape),'type-table mismatch')
            src=r['source'];member=source_manifest['src/'+src['path']]
            projected_span=span_of(declarations.get(slot,''))
            if slot in args:
                debug_line=next((line for line in body.splitlines() if any('debug '+name+' => '+slot+';' in line for name in debug.get(slot,[]))),None)
                projected_span=span_of(debug_line or '')
            if projected_span is None:
                projected_span={k:return_span[k] for k in ['path','start_line','end_line']}
            require(src==projected_span,('exact source span',r['id'],src,projected_span))
            text=(SOURCE/'source/vm/src'/src['path']).read_text().splitlines()
            require(1<=src['start_line']<=src['end_line']<=len(text),'source span bounds')
            excerpt='\n'.join(text[src['start_line']-1:min(src['end_line'],src['start_line']+3)])
            require(r['source_member_sha256']==member['sha256'] and r['source_text']==excerpt,'source custody/text')
        by_local={r['mir_local']:r for r in actual}
        for line in body.splitlines():
            call=parse_call(line)
            if call:
                destination,target,arguments,statement=call
                require(destination in by_local,'call result omitted')
                all_calls.append(dict(caller=f['id'],destination_role=by_local[destination]['id'],
                                      target=target,arguments=arguments,mir_statement=statement))
            creation=re.match(r'\s*(_\d+) = (\{closure@.*?\})(.*?);',norm(line))
            if creation:
                captured=re.findall(r'\w+: (?:move|copy) (_\d+)',creation[3])
                shape=capture_shapes[creation[2]]
                require(all(by_local[n]['bytes']==8 and by_local[n]['alignment']==8 for n in captured),'unexpected closure field shape')
                require(shape==((8*len(captured),8) if captured else (0,1)),'capture payload reconstruction')
                closure_creation.append(dict(caller=f['id'],role=by_local[creation[1]]['id'],
                                             compiler_type=creation[2],captured_roles=[by_local[n]['id'] for n in captured],
                                             bytes=shape[0],alignment=shape[1]))
        subtotal=checked_sum(r['bytes'] for r in actual)
        require(f['enumerated_bytes']==subtotal and f['role_count']==len(actual),'function subtotal')
        by_function.append(dict(id=f['id'],roles=len(actual),bytes=subtotal,body_sha256=sha(body.encode())))
    total=checked_sum(r['bytes'] for r in roles)
    require(total==40531==inv['enumerated_bytes'],'finite formula')
    require(inv['formula']=='E = checked_u64_fold(0, roles, |sum, role| sum.checked_add(size_of(actual_type(role))))','formula changed')
    require(len(inv['types'])==243 and len({r['type_key'] for r in roles})==243,'type identity coverage')
    require(not any(r['compiler_type']=='[u8; 4096]' or 'PlacesV2' in r['compiler_type'] for r in roles),'external owner/inherited aggregate overlap')
    require(sum(r['kind']=='return-expression' for r in roles)==64,'return identity coverage')
    return by_function, all_calls, closure_creation

def main():
    custody = {
        'producer':sealed(PRODUCER,'a1d597f634b805344ecc3edc1e6bfe0095323130d201d68b5da819c50ac1b322'),
        'composition':sealed(SOURCE,'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'),
        'encoder':sealed(ENCODER,'eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f')}
    release=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-encoder-storage-closure-release.json'
    require(sha(release.read_bytes())=='7e4d5748d61527c3dbed3268ebec43a8eb18c959bbc85ec28fc45a712efa7fc6','root release binding')
    members=read(SOURCE/'source-manifest.json')['members']
    require(len(members)==144 and sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())=='140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395','source tree')
    source_manifest={m['path']:m for m in members}
    for m in members:
        data=(SOURCE/'source/vm'/m['path']).read_bytes()
        require((len(data),sha(data))==(m['bytes'],m['sha256']),'source member')
    inv=read(PRODUCER/'inventory.json')
    bounded=blocks((PRODUCER/'function-bodies.mir').read_text())
    require(set(bounded)=={f['header'] for f in inv['functions']},'bounded template set')
    compiler=read(HERE/'compiler-receipt.json')
    raw=HERE/'owned-work/independent.mir'
    if raw.exists():
        data=raw.read_bytes()
        require((len(data),sha(data))==(compiler['output_bytes'],compiler['output_sha256']),'fresh MIR custody')
        fresh=blocks(data.decode(),set(bounded))
        require(all(fresh[header]==body for header,body in bounded.items()),'fresh compiler projection mismatch')
        require(compiler['output_sha256']==read(PRODUCER/'source-projection-custody.json')['unoptimized_MIR_artifact']['sha256'],'complete fresh MIR differs')
    else:
        require(compiler['output_sha256']=='8c266c7d22b79965946b01015b03344776d56dde4c29a71987f3fa118613b384','retained fresh compiler custody')
    require(compiler['exit_code']==0 and compiler['child_reaped'] and not compiler['timed_out'],'bounded compiler failed')
    requests=read(PRODUCER/'layout-requests.json')
    actual=read(PRODUCER/'actual-type-layouts.json')
    require(len(requests)==len(actual)==247,'nameable alternatives')
    actual_by_key={a['key']:a for a in actual}
    require(len(actual_by_key)==247,'duplicate measurement')
    layouts, alternatives=defaultdict(set),defaultdict(list)
    for group in ['encoder','initial','loader']:
        group_requests=[r for r in requests if r['group']==group]
        shapes=decode_constant(PRODUCER/('MIXER_ENCODER_STORAGE_'+group.upper()+'.llvm'))
        seam=(PRODUCER/(group+'-layout-seam.rs')).read_text().splitlines()
        seam_rows=[line.strip() for line in seam if 'size_of::<' in line]
        require(len(shapes)==len(group_requests)==len(seam_rows),'layout seam count')
        for request,shape,line in zip(group_requests,shapes,seam_rows):
            a=actual_by_key[request['key']]
            require((a['actual_type'],a['bytes'],a['alignment'])==(request['actual_type'],*shape),'decoded LLVM measurement')
            require(line=='std::mem::size_of::<'+request['actual_type']+'>(),std::mem::align_of::<'+request['actual_type']+'>(), // '+request['key'],'measurement seam type order')
            layouts[norm(request['compiler_type'])].add(shape)
            alternatives[norm(request['compiler_type'])].append(request['actual_type'])
    require(all(len(shapes)==1 for shapes in layouts.values()),'generic storage alternatives differ')
    layouts={t:next(iter(s)) for t,s in layouts.items()}
    generic={t:a for t,a in alternatives.items() if re.search(r'\bT\b',t)}
    verify_generic_alternatives(generic)
    occurrences=read(PRODUCER/'closure-occurrences.json')['occurrences']
    capture_shapes={}
    for occurrence in occurrences:
        function=next(f for f in inv['functions'] if f['id']==occurrence['closure_function'])
        _,declared=declaration_map(bounded[function['header']])
        header=bounded[function['header']].splitlines()[0]
        args,_=declaration_map(header+'\n}')
        closure_type=norm(args['_1']).removeprefix('&')
        shape=(occurrence['bytes'],occurrence['alignment'])
        require(closure_type not in capture_shapes or capture_shapes[closure_type]==shape,'closure layout inconsistency')
        capture_shapes[closure_type]=shape
    frozen_captures=read(SOURCE/'layout-results.json')['profiles']['gated-production-debug']['exact_captures']
    require({c['name']:(c['bytes'],c['alignment']) for c in frozen_captures}=={c['name']:(c['bytes'],c['alignment']) for c in occurrences},'inherited exact closure measurements')
    capture_constants=decode_constant(SOURCE/'commands/gated-production-debug/MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1.llvm')
    require(capture_constants==[(c['bytes'],c['alignment']) for c in frozen_captures if c['name']!='parameter-range'],'capture constant decoding')
    parameter_llvm=(SOURCE/'commands/gated-production-debug/exact-parameter-capture.llvm').read_text()
    for name in ['size_of_val','align_of_val']:
        require(re.search(r'define i64 @[^\n]*'+name+r'[^\n]*composer_measure_parameter_span_capture_v1[^\n]*\{\nstart:\n  ret i64 8\n\}',parameter_llvm) is not None,'parameter closure exact LLVM layout')
    by_function,calls,creations=audit_inventory(inv,bounded,layouts,capture_shapes,source_manifest)
    require(len(creations)==26 and sum(c['bytes'] for c in creations)==160,'actual closure expression count/bytes')
    require(sum('swift.rs:1169:' in c['compiler_type'] for c in creations)==8,'entry macro closure occurrences')
    require(sum(r['bytes'] for r in inv['roles'] if '{closure@' in r['compiler_type'])==416,'closure roles additive overlap')
    graph={f['id']:set() for f in inv['functions']}
    for call in calls:
        target=resolve_product(call['target'],inv['functions'])
        if target: graph[call['caller']].add(target)
        call['resolved_product_callee']=target
    for function in graph:
        if '::{closure#' in function:
            graph[function.rsplit('::{closure#',1)[0]].add(function)
    bridge=next(f['id'] for f in inv['functions'] if f['id'].endswith('::snapshot_runtime_v2'))
    callback=next(f['id'] for f in inv['functions'] if f['source']['path']=='experimental_wasi/accounted.rs')
    map_calls=[c for c in calls if c['caller']==bridge and c['target'].startswith('Option::<&accounted::AccountedWasi>::map')]
    require(len(map_calls)==1 and 'AccountedWasi::snapshot_configuration_v2' in map_calls[0]['arguments'],'indirect function-item callback')
    graph[bridge].add(callback)
    verify_acyclic(graph)
    require({k:sorted(v) for k,v in graph.items()}==read(PRODUCER/'product-callgraph.json')['nodes'],'independent graph differs')
    roots=[n for n in graph if n.rsplit('::',1)[-1] in {'bytes','offset','is_final','borrow_snapshot_v2','into_cursor','encoded_extent','emitted_extent','next_block'}]
    reached=set()
    def reach(n):
        if n in reached:return
        reached.add(n)
        for c in graph[n]:reach(c)
    for root in roots:reach(root)
    require(len(roots)==8 and reached==set(graph),'unused or omitted reachable template')
    producer_calls=read(PRODUCER/'call-sites.json')['calls']
    require(len(calls)==len(producer_calls),'call-site omission')
    differences=[]
    for independent,producer in zip(calls,producer_calls):
        require(all(independent[k]==producer[k] for k in ['caller','destination_role','mir_statement']),'call identity/result mismatch')
        if independent['target']!=producer['target']:
            differences.append({'caller':independent['caller'],'producer_target':producer['target'],'complete_target':independent['target'],'storage_or_graph_omission':False})
    require(len(differences)==1 and differences[0]['complete_target'].startswith('Option::<&accounted::AccountedWasi>::map'),'unexpected target mismatch')
    behavior=(SOURCE/'source/vm/src/experimental/swift.rs').read_text().splitlines(keepends=True)[731:1374]
    require(behavior==(ENCODER/'host/encoder.rs').read_text().splitlines(keepends=True)[:643],'encoder behavior changed')
    # Controls preserve cardinality/total where possible, so a simple count/sum
    # checker cannot pass them. Nothing is written back to the producer packet.
    controls={}
    def reject(name,mutate):
        bad=copy.deepcopy(inv);mutate(bad)
        try:audit_inventory(bad,bounded,layouts,capture_shapes,source_manifest)
        except (AssertionError,KeyError):controls[name]=True
        else:raise AssertionError('negative control accepted: '+name)
    reject('zero_sized_role_omission_with_duplicate_substitution',lambda j:j['roles'].__setitem__(next(i for i,r in enumerate(j['roles']) if r['bytes']==0),copy.deepcopy(j['roles'][0])))
    reject('equal_count_and_total_wrong_function_partition',lambda j:j['functions'][0]['role_ids'].__setitem__(0,j['functions'][1]['role_ids'][0]))
    reject('same_total_size_swaps',lambda j:(j['roles'][0].__setitem__('bytes',9),j['roles'][1].__setitem__('bytes',7)))
    reject('wrong_source_type_at_same_size',lambda j:j['roles'][0].__setitem__('compiler_type','u64'))
    reject('fabricated_move_edge',lambda j:j['roles'][0]['source_uses'].append('_0 = move _9;'))
    reject('loop_repetition_multiplier',lambda j:j['roles'][0].__setitem__('multiplicity',9))
    reject('callee_return_reclassified_as_caller',lambda j:j['roles'][0].__setitem__('partition','caller'))
    reject('inherited_aggregate_added',lambda j:j['roles'][0].__setitem__('compiler_type','EncoderInitPlacesV2'))
    reject('wrong_source_binding',lambda j:j['roles'][0].__setitem__('source_member_sha256','0'*64))
    reject('plausible_but_wrong_source_column',lambda j:j['roles'][0]['source'].__setitem__('start_column',27))
    bad_generic=copy.deepcopy(generic);bad_generic[next(iter(bad_generic))].pop()
    try:verify_generic_alternatives(bad_generic)
    except AssertionError:controls['omitted_generic_alternative']=True
    else:raise AssertionError('generic omission accepted')
    bad_graph=copy.deepcopy(graph);bad_graph[next(iter(bad_graph))].add(next(iter(bad_graph)))
    try:verify_acyclic(bad_graph)
    except AssertionError:controls['recursive_invocation_cycle']=True
    else:raise AssertionError('recursive cycle accepted')
    try:checked_sum([MAX,1])
    except AssertionError:controls['u64_overflow']=True
    else:raise AssertionError('overflow accepted')
    result=dict(schema=1,status='accepted within bounded encoder-callee logical source-storage contract',
                command=[sys.executable,str(Path(__file__).resolve())],python_version=platform.python_version(),
                reviewer_script_sha256=sha(Path(__file__).read_bytes()),source_binding=inv['source_binding'],
                custody=custody,root_release_sha256=sha(release.read_bytes()),
                independent_fresh_metadata_projection_identical=True,
                source_roles=2658,function_templates=64,type_identities=243,
                nameable_layout_instantiations=247,checked_source_bytes=40531,
                by_role_kind=dict(Counter(r['kind'] for r in inv['roles'])),
                call_sites=len(calls),product_call_sites=sum(c['resolved_product_callee'] is not None for c in calls),
                acyclic_product_graph=True,externally_consumed_roots=8,all_templates_reachable=True,
                closures=26,entry_macro_occurrences=8,expression_capture_bytes=160,
                all_closure_or_reference_role_bytes=416,negative_controls=controls,
                metadata_findings=differences,blocking_product_source_findings=[],
                encoder_behavior_lines=643,encoder_behavior_sha256=sha(''.join(behavior).encode()),
                runtime_executions=0,native_device_simulator_emulator_UI_capture_process_inventory_executions=0,
                full_storage_floor_or_operational_writer_acceptance=False,GA_gates_verified=0,
                limits=['Logical source roles only; no physical stack/RSS/ABI/unwind/spill/private stdlib/static-pointee bound.',
                        'Frozen 495/144 input only; root-selected authority correction is not independently accepted here.',
                        'External proof/guard/provenance/transfer and caller view/cursor/block/result roles require separate integration.'])
    (HERE/'review-results.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'reconstructed-functions.json').write_text(json.dumps(by_function,indent=2)+'\n')
    targets=Counter(c['target'] for c in calls)
    call_summary={'count':len(calls),'direct_product_count':sum(c['resolved_product_callee'] is not None for c in calls),
                  'complete_target_counts':dict(sorted(targets.items())),
                  'by_function':[dict(id=f['id'],calls=sum(c['caller']==f['id'] for c in calls),
                                      exact_statements_sha256=sha('\n'.join(c['mir_statement'] for c in calls if c['caller']==f['id']).encode())) for f in inv['functions']]}
    (HERE/'reconstructed-calls.json').write_text(json.dumps(call_summary,indent=2)+'\n')
    (HERE/'reconstructed-closures.json').write_text(json.dumps(creations,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','checked_source_bytes','source_roles','call_sites','product_call_sites','negative_controls','metadata_findings']}))

if __name__ == '__main__':
    main()
