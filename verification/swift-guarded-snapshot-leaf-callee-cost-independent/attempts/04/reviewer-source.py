#!/usr/bin/env python3
"""Independent frozen-data review. No Rust compiler, product or native runner."""
from pathlib import Path
from collections import Counter
import copy, gzip, hashlib, json, re, sys, unittest
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
PRODUCER = V / 'swift-guarded-snapshot-leaf-callee-cost'
TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
SEAL = 'ffbe8f0e91125df2f769df1b431575431caa8103f1f920aa26acac0255214564'
RELEASE = '09a79705f30fc83f01a328dd6e98a1230f6678ffdf1d9c7f095adfa794888020'
sha = lambda b: hashlib.sha256(b).hexdigest()
canon = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':')).encode()
load = lambda p: json.loads(p.read_text())

def require(ok, message):
    if not ok:
        raise ValueError(message)

def rehash_packet(folder, expected):
    raw = (folder / 'seal.json').read_bytes()
    require(sha(raw) == expected, 'seal identity')
    seal = json.loads(raw)
    members = seal['members']
    actual = sorted(str(p.relative_to(folder)) for p in folder.rglob('*')
                    if p.is_file() and p != folder / 'seal.json')
    require(actual == sorted(m['path'] for m in members), 'sealed membership')
    for row in members:
        b = (folder / row['path']).read_bytes()
        require((len(b), sha(b)) == (row['bytes'], row['sha256']), 'member ' + row['path'])
    require(sha(canon(members)) == seal['tree_sha256'], 'member tree')
    return dict(path=str(folder.relative_to(ROOT)), seal_sha256=expected,
                members=len(members), bytes=sum(m['bytes'] for m in members))

def bodies(text):
    result = {}
    for match in re.finditer(r'^fn .*$', text, re.M):
        end = re.search(r'^}\n', text[match.start():], re.M)
        require(end is not None, 'unterminated MIR')
        body = text[match.start():match.start() + end.end()]
        header = body.splitlines()[0]
        require(header not in result, 'duplicate MIR header')
        result[header] = body
    return result

def operations(body):
    out = []; block = None
    for number, line in enumerate(body.splitlines(), 1):
        # This printer's selected code has no // inside string constants.
        code = line.split('//', 1)[0].rstrip()
        m = re.fullmatch(r'    (bb\d+)(?: \(cleanup\))?: \{', code)
        if m:
            block = m[1]
        elif code == '    }':
            block = None
        elif block and code.strip():
            out.append(dict(block=block, line=number, code=code.strip()))
    return out

def graph_of(body):
    graph = {}
    for op in operations(body):
        graph[op['block']] = sorted(set(re.findall(r'\bbb\d+\b', op['code'])))
    require(all(t in graph for values in graph.values() for t in values), 'unknown CFG target')
    return graph

def components(graph):
    # Reachability equivalence, separate from producer Tarjan traversal.
    def reachable(n):
        seen = set(); pending = [n]
        while pending:
            x = pending.pop()
            if x not in seen:
                seen.add(x); pending += graph[x]
        return seen
    reach = {n: reachable(n) for n in graph}
    remaining = set(graph); out = []
    while remaining:
        a = min(remaining)
        group = {b for b in remaining if b in reach[a] and a in reach[b]}
        remaining -= group
        if len(group) > 1 or a in graph[a]:
            out.append(group)
    return out

def short_type(t):
    return re.sub(r'\b(?:[A-Za-z_]\w*::)+', '', t)

def roles(body):
    header = body.splitlines()[0]
    args = header.split('(', 1)[1].rsplit(') -> ', 1)[0]
    return dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)', args)
                + re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);(?:\s*//.*)?$', body, re.M))

def fold(ledger, key, stack=()):
    require(key not in stack and key in ledger['nodes'], 'cyclic/missing node')
    n = ledger['nodes'][key]
    f = n['own'] + n.get('known_native', 0)
    maps = [Counter(n.get(k, {})) for k in ('missing_native', 'unsized', 'payload')]
    for child, count in n['calls'].items():
        require(type(count) is int and count > 0, 'invalid child multiplicity')
        cf, cm = fold(ledger, child, stack + (key,))
        f += count * cf
        for a, b in zip(maps, cm):
            a.update({k: count*v for k, v in b.items()})
    require(0 <= f <= (1 << 64)-1, 'fixed overflow')
    return f, maps

def check_operation_coverage(ledger, mir):
    count = 0
    for key, node in ledger['nodes'].items():
        if node['kind'] != 'MIR-all-written-block-upper':
            continue
        body = mir[node['MIR_header']]
        require(sha(body.encode()) == node['MIR_sha256'], 'MIR binding ' + key)
        actual = operations(body)
        retained = [{k:o[k] for k in ('block','line','code')} for o in node['operations']]
        require(actual == retained, 'written MIR operation omitted ' + key)
        require(graph_of(body) == node['graph'] or key.startswith('closure::c431'), 'CFG mismatch')
        for o in node['operations']:
            require(type(o['weight']) is int and o['weight'] > 0, 'invalid op weight')
        count += len(actual)
    return count

def check_call_edges(ledger, mir):
    callback_count = 0; callsites = 0; rows = []
    for key, node in ledger['nodes'].items():
        if node['kind'] != 'MIR-all-written-block-upper':
            continue
        calls = Counter(); primitives = Counter(); payload = Counter()
        for op in node['operations']:
            code = op['code']; edges = op['edges']; weight = op['weight']
            iscall = ' -> [' in code and not code.startswith(('switchInt(', 'assert('))
            require(bool(edges) == iscall, 'unmapped or spurious callsite ' + key)
            if not iscall:
                continue
            callsites += 1
            for e in edges:
                if e['kind'] == 'call': calls[e['target']] += weight
                elif e['kind'] == 'payload': payload[e['target']] += weight
                elif e['kind'] == 'closed-primitive': primitives[e['target']] += weight
                else: raise ValueError('unknown edge kind')
            if code.startswith('drop('):
                require(len(edges) == 1 and edges[0]['kind'] == 'payload', 'real drop lost')
                local = re.search(r'_\d+', code)[0]
                raw = roles(mir[node['MIR_header']])[local]
                # T has one concrete argument at the leaf cleanup cut.
                want = 'Option<SwiftFunctionCache>' if raw == 'T' else short_type(raw)
                if raw.endswith('ClosedAdoptionV1>::Retirement'):want='Result<(), SwiftRunFailure>'
                if raw.endswith('ClosedAdoptionV1>::Failure'):want='SnapshotPreScopeFailureV1'
                require(edges[0]['target'] == 'payload::' + want, 'drop type mismatch '+key+' '+raw+' -> '+edges[0]['target'])
                continue
            expression = code.split(' = ',1)[1].split(' -> [',1)[0]
            callee = expression[:expression.rfind('(')]
            spans = set(re.findall(r'\{closure@[^}]+\}', callee))
            actual_callbacks = [e['target'] for e in edges if e['kind']=='call'
                                and ledger['nodes'][e['target']].get('MIR_header','').find('::{closure#') != -1]
            matched = set()
            for target in actual_callbacks:
                header = ledger['nodes'][target]['MIR_header']
                matched.update(span for span in spans if span in header)
            require(matched == spans and len(actual_callbacks) == len(spans), 'callback edge incomplete')
            callback_count += len(spans)
            if '<P as ClosedAdoptionV1>::' in callee:
                method = callee.rsplit('::',1)[1]
                require([e['target'] for e in edges] == ['policy_' + ('retire' if method=='retire_tickets' else method)], 'policy edge')
                b = ledger['source_bindings'][edges[0]['target']]
                require('control.rs:1909:1:' in ledger['nodes'][edges[0]['target']]['MIR_header'], 'wrong policy impl')
            for e in edges:
                if e['kind'] != 'closed-primitive': continue
                require(e['target'] == callee, 'primitive call identity')
                require(callee.startswith(('<','Option::','Result::','Vec::','std::','core::','Atomic::','Duration::','Instant::','Layout::','ptr::')),
                        'authored callee laundered as primitive')
            for e in edges:
                if e['kind'] != 'call' or e['target'] in actual_callbacks: continue
                target = e['target']; n = ledger['nodes'][target]
                if target == 'accepted_constructor_region':
                    require(key == 'construct_owned' and callee.startswith('construct_profile_core_v1::<'), 'constructor reuse edge')
                elif target.startswith('policy_'): pass
                elif 'AccountedWasi::usage}' in callee and target=='accepted::wasi_usage': pass
                elif target in ('accepted::live_default','accepted::reservations_default'):
                    typename='SwiftLiveUsage' if target.endswith('live_default') else 'SwiftReservations'
                    require(callee=='<control::'+typename+' as Default>::default', 'derived default target')
                    require(n['binding']['source'].startswith('pub struct '+typename+' {'), 'derived default type source')
                else:
                    source = ledger.get('source_bindings',{}).get(target, n.get('binding',{})).get('source','')
                    m = re.search(r'\bfn\s+(\w+)\b', source)
                    require(m is not None, 'callee source absent ' + target + ' from ' + callee)
                    name = re.search(r'(\w+)(?:::<.*>)?$',callee)[1]
                    require(m[1] == name, 'callee function identity ' + callee + ' -> ' + m[1])
            rows.append(dict(node=key, block=op['block'], line=op['line'], callee=callee,
                             weight=weight, edges=edges))
        require(dict(calls) == node['calls'], 'call multiplicity ' + key)
        require(dict(primitives) == node['primitive'], 'primitive multiplicity ' + key)
        # Recompute only the explicit, reviewed inline/borrowed adapters. Every
        # owning payload remains a separately priced destructor interface.
        for term in list(payload):
            t=term.removeprefix('payload::');count=payload[term]
            if t in ('()','Result<(), SwiftRunFailure>') or t.startswith('Zip<'):
                del payload[term]
            elif t=='(Option<SwiftFunctionCache>, Option<SwiftRunFailure>)':
                del payload[term];payload['payload::Option<SwiftFunctionCache>']+=count
        require(dict(payload)==node['payload'],'typed destructor interface omitted '+key)
    return dict(callsites=callsites, callback_callsites=callback_count, rows=rows)

def actual_core_capture_binding(ledger, mir):
    parent = mir[ledger['nodes']['core']['MIR_header']]
    callback_key = next(k for k,n in ledger['nodes'].items()
                        if '::{closure#0}(_1:' in n.get('MIR_header','')
                        and 'control.rs:686:23:' in n['MIR_header'])
    callback = mir[ledger['nodes'][callback_key]['MIR_header']]
    debug = []
    for line in callback.splitlines():
        m = re.match(r'\s*debug (\w+) => \(\*\(\(\*_1\)\.(\d+): (.+)\)\);', line)
        if m: debug.append(dict(index=int(m[2]), field=m[1], compiler_type=m[3]))
    require([r['index'] for r in debug] == list(range(8)), 'eight actual capture projections')
    pr = roles(parent)
    for row, local in zip(debug, range(29,37)):
        name = '_' + str(local)
        assignment = next(o['code'] for o in operations(parent) if o['code'].startswith(name+' = '))
        require(pr[name] == row['compiler_type'], 'capture local type')
        row.update(local=name, assignment=assignment)
    expected = ['control','cursor','started','budget__deadline_ms','source',
                'validation__source_bytes','validation__metadata_reserved','metadata']
    require([r['field'] for r in debug] == expected, 'capture field identity')
    require(debug[-1]['assignment'] == '_36 = &mut _25;', 'metadata capture origin')
    require(debug[4]['assignment'] == '_33 = &mut _24;', 'source capture origin')
    return dict(callback_node=callback_key, callback_MIR_sha256=sha(callback.encode()),
                parent_MIR_sha256=sha(parent.encode()), fields=debug,
                authority='MIR debug projections plus actual typed local assignments; not aggregate pretty field labels',
                native_size_observed=False)

def validate_roster_capture_plan(roster, actual):
    captures = next(q for q in roster['queries'] if q['index']==8)['creation_contexts'][0]['captures']
    fields = actual['fields']
    require(len(captures) == len(fields), 'printed roster omitted actual eighth metadata capture')
    for a,b in zip(captures,fields):
        require(a['field'] == b['field'] and a['local'] == b['local'] and a['compiler_type'] == b['compiler_type'], 'printed capture role mismatch')

def verify_compiler_custody(folder, anonymous=False):
    """Reconstruct the appended source and all five recorded identity bindings."""
    manifest=load(folder/'compiled-manifest.json');binding=load(folder/'binding.json')
    receipt=load(folder/'compiler-receipt.json');cleanup=load(folder/'cleanup.json')
    original=manifest['source_manifest']['members']
    require(len(original)==146 and sha(canon(original))==TREE,'compiler source146')
    compiled={r['path']:r for r in manifest['compiled_source_members']}
    require(set(compiled)=={r['path'] for r in original},'compiled source membership')
    for row in original:
        p=V/'swift-guarded-snapshot-host-composition/overlay/vm'/row['path']
        if not p.exists():p=V/'swift-guarded-snapshot-funding-implementation/source/vm'/row['path']
        raw=p.read_bytes();require((len(raw),sha(raw))==(row['bytes'],row['sha256']),'compiler original member')
        if anonymous:
            if row['path'] in manifest['additions']:
                fragment=(folder/(Path(row['path']).stem+'-append.inc.rs')).read_bytes()
                extra=manifest['additions'][row['path']]
                require((len(fragment),sha(fragment))==(extra['bytes'],extra['sha256']),'append identity')
                raw+=fragment
        elif row['path']==load(folder/'selection.json')['append_to']:
            raw+=(folder/'layout-queries.inc.rs').read_bytes()
        require((len(raw),sha(raw))==(compiled[row['path']]['bytes'],compiled[row['path']]['sha256']),'compiled append-only source')
    require(sha(canon(manifest['compiled_source_members']))==manifest['compiled_tree_sha256'],'compiled tree')
    for key,file in [('MIXER_LOADER_MANIFEST_SHA256','compiled-manifest.json'),('MIXER_LOADER_COMMAND_SHA256','argv.bin'),
                     ('MIXER_LOADER_COMPILE_ENV_SHA256','environment.bin'),('MIXER_LOADER_COMPILER_VERSION_SHA256','compiler-version.stdout')]:
        require(sha((folder/file).read_bytes())==binding['compile_identity_keys'][key]==receipt['environment'][key],'compiler identity '+key)
    require(manifest['compiler_sha256']==binding['compile_identity_keys']['MIXER_LOADER_COMPILER_SHA256']==receipt['environment']['MIXER_LOADER_COMPILER_SHA256'],'compiler binary identity')
    require(receipt['direct_child_waited'] and receipt['owned_group_absent'] and not receipt['timed_out'],'compiler wait/timeout')
    require(cleanup['completed'] and cleanup['owned_scratch_removed'] and cleanup['command_children_waited_and_groups_absent'],'owned cleanup')
    require(not (folder/'owned-work').exists(),'owned scratch remains')
    require(receipt['product_runtime'] is False,'compiler product runtime')
    require(receipt['exit_code']==(0 if anonymous else 1),'unexpected compiler outcome')
    argv=receipt['argv'];require(argv[argv.index('--target')+1]=='aarch64-apple-darwin' and binding['source_tree_sha256']==TREE,'compiler target')
    if 'target' in binding:require(binding['target']=='aarch64-apple-darwin','binding target')
    err=(folder/'compiler.stderr').read_bytes()
    require((len(err),sha(err))==(receipt['outputs']['stderr']['bytes'],receipt['outputs']['stderr']['sha256']),'compiler stderr binding')
    return receipt

def native_observations(roster):
    named=V/'swift-guarded-snapshot-source146-callee-storage-layouts'
    anonymous=V/'swift-guarded-snapshot-source146-closure-layouts'
    rehash_packet(named,'9e2cd764548188b30c93d045fdc72d59c771a4cd489858d6340f131bc67b1001')
    rehash_packet(anonymous,'d630481ae157d9b406334031d6592a24fa8e96da5b9fb298f255edfa70782e9b')
    named_receipt=verify_compiler_custody(named)
    anon_receipt=verify_compiler_custody(anonymous,True)
    release=V/'swift-semantic-adapter-root-review/guarded-snapshot-source146-closure-layout-release.json'
    require(sha(release.read_bytes())=='a227230401e302ade845702f88a10bb33110486a9cb0b157bfc69424053b09c7','closure data release')
    raw=gzip.decompress((anonymous/'compiler.stdout.gz').read_bytes())
    archive=load(anonymous/'layout-archive.json')
    require((len(raw),sha(raw))==(archive['raw_bytes'],archive['raw_sha256'])==
            (anon_receipt['outputs']['stdout']['bytes'],anon_receipt['outputs']['stdout']['sha256']),'full original closure output')
    ir=gzip.decompress((anonymous/'source146.ll.gz').read_bytes());ir_identity=load(anonymous/'llvm-archive.json')
    require((len(ir),sha(ir))==(ir_identity['raw_bytes'],ir_identity['raw_sha256']),'full LLVM archive')
    require(b'SOURCE146_CLOSURE_LAYOUT_CORE_V1' in ir and b'SnapshotAdoptionV1' in ir,'actual selected core instantiation')
    # Distinct from producer result parser: bind primary diagnostic source text,
    # exact const identifier, exact fully qualified Rust expression and label.
    observed={};diagnostics={}
    for line in (named/'compiler.stderr').read_text().splitlines():
        d=json.loads(line)
        if not d.get('code') or d['code'].get('code')!='E0308':continue
        primary=[s for s in d['spans'] if s['is_primary']]
        require(len(primary)==1,'ambiguous named primary diagnostic')
        span=primary[0];text=span['text'][0]['text']
        m=re.fullmatch(r'const LP_(SIZE|ALIGN)_(\d+): \[\(\); usize::MAX\] = \[\(\); std::mem::(?:size|align)_of::<(.+)>\(\)\];',text)
        require(m is not None,'unknown named diagnostic source')
        kind,index,concrete=m[1],int(m[2]),m[3]
        label=re.fullmatch(r'expected an array with a size of usize::MAX, found one with a size of (\d+)',span['label'])
        require(label is not None,'named layout not observed')
        require((index,kind) not in observed,'duplicate named layout')
        observed[index,kind]=(concrete,int(label[1]));diagnostics[index,kind]=d
    require(len(observed)==42,'full named diagnostic count')
    rows=[]
    for query in roster['queries']:
        key=query['key'];index=query['index']
        if index<8:
            concrete,size=observed[index,'SIZE'];align_concrete,alignment=observed[index,'ALIGN']
            require(concrete==align_concrete==query['concrete_type'],'exact named query applicability')
            binding=dict(kind='exact-qualified-E0308-const-size-and-alignment',query_index=index,concrete=concrete,
                         raw_diagnostics=[diagnostics[index,'SIZE'],diagnostics[index,'ALIGN']],
                         compiler_receipt_path=str((named/'compiler-receipt.json').relative_to(ROOT)),
                         compiler_receipt_sha256=sha((named/'compiler-receipt.json').read_bytes()))
        else:
            # Exact original span, scoped to this retained compiler invocation.
            span='src/'+key.split('/vm/src/',1)[1].removesuffix('}')
            prefix='print-type-size type: `{closure@'+str(anonymous/'owned-work/vm')+'/'+span+'}`: '
            matches=[line for line in raw.decode().splitlines() if line.startswith(prefix)]
            require(len(matches)==1,'missing/ambiguous exact original closure observation')
            match=re.fullmatch(re.escape(prefix)+r'(\d+) bytes, alignment: (\d+) bytes',matches[0])
            require(match is not None,'closure output shape')
            size,alignment=map(int,match.groups())
            binding=dict(kind='actual-original-expression-monomorphized-layout',source_span=span,raw_line=matches[0],
                         selected_policy='SnapshotAdoptionV1',body_bytes_and_source_span_preserved=True,
                         compiler_receipt_path=str((anonymous/'compiler-receipt.json').relative_to(ROOT)),
                         compiler_receipt_sha256=sha((anonymous/'compiler-receipt.json').read_bytes()))
        require(alignment>0 and alignment&(alignment-1)==0 and size%alignment==0,'actual layout validity')
        rows.append(dict(key=key,size=size,alignment=alignment,kind='actual-size-and-alignment',source_tree_sha256=TREE,
                         compiler_diagnostic_binding_sha256=sha(canon(binding)),diagnostic_binding=binding))
    require(len(rows)==13 and len({r['key'] for r in rows})==13,'complete13native observations')
    return rows

class IndependentReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load(PRODUCER/'callee-ledger.json')
        cls.contract = load(PRODUCER/'cost-interface.json')
        cls.obs = load(PRODUCER/'native-layout-observations.json')
        cls.roster = load(PRODUCER/'native-query-roster/roster.json')
        cls.mir = bodies((PRODUCER/'selected.mir').read_text())
        cls.captures = actual_core_capture_binding(cls.ledger,cls.mir)
        sys.path.insert(0,str(PRODUCER))
        import evaluator
        cls.evaluator = evaluator
        cls.required_negatives = 0

    def test_01_released_packet_and_source146_custody(self):
        self.assertEqual((34,7774320), tuple(rehash_packet(PRODUCER,SEAL)[k] for k in ('members','bytes')))
        self.assertEqual(RELEASE,sha((V/'swift-semantic-adapter-root-review/guarded-snapshot-callee-storage-query-release.json').read_bytes()))
        m = load(V/'swift-guarded-snapshot-leaf-shell-cost/source-manifest.json')
        self.assertEqual(TREE,sha(canon(m['members'])))
        self.assertEqual(146,len(m['members']))
        for r in m['members']:
            p = V/'swift-guarded-snapshot-host-composition/overlay/vm'/r['path']
            if not p.exists():p=V/'swift-guarded-snapshot-funding-implementation/source/vm'/r['path']
            b=p.read_bytes();self.assertEqual((r['bytes'],r['sha256']),(len(b),sha(b)))

    def test_02_every_retained_input_binding_and_selected_MIR(self):
        for p,r in self.ledger['input_bindings'].items():
            b=(ROOT/p).read_bytes();self.assertEqual((r['bytes'],r['sha256']),(len(b),sha(b)))
        raw=gzip.decompress((V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz').read_bytes())
        self.assertEqual('e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2',sha(raw))
        self.assertEqual(38,len(self.mir))
        # Whole-program MIR can repeat unqualified textual headers for unrelated
        # functions. Bind the selected complete bytes, not a whole-program header map.
        for h,b in self.mir.items():self.assertEqual(1,raw.decode().count(b))

    def test_03_independent_complete_operation_and_call_edge_walk(self):
        self.assertGreater(check_operation_coverage(self.ledger,self.mir),1000)
        self.assertGreater(check_call_edges(self.ledger,self.mir)['callsites'],200)

    def test_04_missing_operation_and_callback_adversaries(self):
        m=copy.deepcopy(self.ledger);m['nodes']['drop_proof']['operations'].pop()
        with self.assertRaises(ValueError):check_operation_coverage(m,self.mir)
        m=copy.deepcopy(self.ledger)
        op=next(o for o in m['nodes']['core']['operations'] if any(e['target'].startswith('closure::') for e in o['edges']))
        op['edges']=[e for e in op['edges'] if not e['target'].startswith('closure::')]
        with self.assertRaises(ValueError):check_call_edges(m,self.mir)

    def test_05_independent_flatten_all_exports_and_cycle_controls(self):
        for name,key in self.ledger['exports'].items():
            fixed,maps=fold(self.ledger,key);r=self.contract['exports'][name]
            self.assertEqual(fixed,r['fixed'])
            for actual,label in zip(maps,('native','unsized','payload')):self.assertEqual(dict(actual),r[label])
        m=copy.deepcopy(self.ledger);m['nodes']['drop_proof']['calls']['drop_proof']=1
        with self.assertRaises(ValueError):fold(m,'drop_proof')

    def test_06_actual_loops_and_closed_source_maxima(self):
        for name,cap in [('cache_cleanup',64),('wasi_pair',4)]:
            node=self.ledger['nodes'][name];actual=components(graph_of(self.mir[node['MIR_header']]))
            self.assertEqual(2,len(actual));self.assertEqual({frozenset(s) for s in actual},{frozenset(r['blocks']) for r in node['loops']})
            for r in node['loops']:
                self.assertEqual((cap,cap+1),(r['max_iterations'],r['block_visits_upper']))
                for o in node['operations']:
                    if o['block'] in r['blocks']:self.assertEqual(cap+1,o['weight'])
        source=self.ledger['source_bindings']['cache_cleanup']['source']
        self.assertIn('for record in &mut cache.pins',source);self.assertIn('for slot in &mut cache.slots',source)
        self.assertNotIn('while ',source)
        route=self.evaluator.canonical_route()
        for key in ('cache_pin_bound','cache_slot_bound','wasi_buffer_bound'):
            m=dict(route);m[key]-=1
            with self.assertRaises(ValueError):self.evaluator.check_route(m)

    def test_07_exact_counter_cut_refusal_and_admission_order(self):
        phase=self.ledger['core_phase_binding'];node=self.ledger['nodes'][self.captures['callback_node']]
        store=phase['counter_store'];self.assertEqual('bb25',store['block'])
        before=self.ledger['nodes']['core_callback_before'];after=self.ledger['nodes']['core_fixed_store_and_after']
        self.assertNotIn(store['code'],[o['code'] for o in before['operations']])
        self.assertEqual(1,[o['code'] for o in after['operations']].count(store['code']))
        self.assertEqual(5,after['calls']['accepted::admit']);self.assertNotIn('accepted::admit',before['calls'])
        self.assertEqual(1,before['calls']['accepted::check_budget']);self.assertEqual(1,before['calls']['accepted::check'])
        self.assertEqual({'bb3','bb69'},set(phase['overlap_blocks']))
        # Recompute selected branch reachability using original full generic CFG.
        graph=graph_of(self.mir[node['MIR_header']]);self.assertEqual(['bb19','bb20'],graph['bb16']);graph['bb16']=['bb19']
        def reach(start,stop=None):
            out=set();todo=[start]
            while todo:
                b=todo.pop()
                if b not in out and b!=stop:out.add(b);todo+=graph[b]
            return out
        self.assertEqual(reach('bb0','bb25'),set(phase['pre_callback_blocks']))
        self.assertEqual(reach('bb25'),set(phase['post_callback_blocks']))
        outer=self.ledger['nodes']['core_before_fixed_store']
        self.assertEqual(self.ledger['nodes']['core']['operations'],outer['operations'])
        self.assertNotIn(self.captures['callback_node'],outer['calls'])
        self.assertEqual(1,outer['calls']['core_callback_before'])

    def test_08_concrete_selected_policy_and_real_payload_before_refunds(self):
        source=self.ledger['source_bindings']['drop_proof']['source']
        self.assertLess(source.index('drop(body)'),source.index('self.refund_with_wasi(source'))
        self.assertEqual(2,self.ledger['nodes']['drop_proof']['calls']['accepted::refund_with_wasi'])
        for key in ('policy_failure','policy_foundation','policy_retire'):
            self.assertIn('control.rs:1909:1:',self.ledger['nodes'][key]['MIR_header'])
        retire=self.ledger['source_bindings']['policy_retire']['source']
        self.assertIn('source.and(metadata)',retire);self.assertEqual(2,retire.count('control.refund(ticket)'))
        self.assertEqual(1,self.ledger['nodes']['drop_proof']['payload']['payload::AdoptionBodyV1'])

    def test_09_specific_source144_rows_and_no_aggregate_transfer(self):
        old=load(V/'swift-guarded-snapshot-ingress-work/ledger.json')
        accepted=[(k,n) for k,n in self.ledger['nodes'].items() if n['kind']=='accepted-specific-row-own-actions']
        self.assertEqual(32,len(accepted))
        for key,n in accepted:
            name=key.removeprefix('accepted::');r=old['rows'][name]
            self.assertEqual(r['own_actions'],n['own']);self.assertEqual(r['parts'],n['parts'])
            self.assertEqual({'accepted::'+c:v for c,v in r['calls'].items()},n['calls'])
            b=old['source_bindings'][r['binding']]
            self.assertEqual(b['sha256'],n['binding']['sha256'])
            self.assertEqual(sha(b['source'].encode()),n['binding']['sha256'])
        uses=[(k,n['calls']['accepted_constructor_region']) for k,n in self.ledger['nodes'].items() if 'accepted_constructor_region' in n['calls']]
        self.assertEqual([('construct_owned',1)],uses)
        region=self.ledger['nodes']['accepted_constructor_region']
        self.assertEqual(sum(region['parts'].values()),region['own']);self.assertNotEqual(451814442,region['own'])
        self.assertFalse(self.ledger['constructor_applicability']['product451814442_transferred'])
        self.assertEqual(3,self.ledger['nodes']['accepted::foundation']['own'])

    def test_10_constructor_refusal_reachable_original_rows_and_empty_carriers(self):
        text=(V/'swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
        self.assertIn('Err(AError::WorkAuditPending)',self.ledger['constructor_applicability']['unconditional_refusal_body'])
        self.assertFalse(self.ledger['constructor_applicability']['writer_encoder_initializer_entered'])
        a=text.index('let emission=proposed_emission_work_v1(&shape)?;')
        self.assertLess(a,text.index('control.snapshot_commit_storage_v1(additional)?;',a))
        # Original header/row work still follows refused snapshot branch export.
        self.assertLess(text.index('let attempt=branch.export('),text.index('let rows=write_initial_profile_rows_v1('))
        self.assertIn('match original_return.take().expect("actual constructor return")',text)
        self.assertIn('match preparation.take().expect("actual prepare return")',text)
        self.assertEqual(2,text.count('phase.complete((preparation,original_return))'))

    def test_11_constructor_actual_destructor_frontier(self):
        frozen=load(PRODUCER/'constructor-destructor-roster/roster.json')
        selected=bodies((PRODUCER/'constructor-destructor-roster/selected-constructor.mir').read_text())
        self.assertEqual(5,len(selected));raws=Counter();forwarded=Counter()
        for row in frozen['body_occurrences']:
            body=selected[row['header']];self.assertEqual(sha(body.encode()),row['MIR_sha256'])
            rs=roles(body)
            for o in operations(body):
                code=o['code'];drop=re.match(r'drop\((_\d+)\)',code)
                if drop:raws[short_type(rs[drop[1]])]+=1
                if 'drop_reserved::<' in code or 'std::mem::drop::<' in code:
                    expr=code.split(' = ',1)[1].split(' -> [',1)[0];callee=expr[:expr.rfind('(')]
                    marker='drop_reserved::<' if 'drop_reserved::<' in callee else 'std::mem::drop::<'
                    forwarded[short_type(callee.split(marker,1)[1][:-1])]+=1
        # Only actual operations count: diagnostic Const comments are not calls.
        expected={'Partial':5,'Vec<SwiftSlot>':2,'Vec<PinRecord>':2,'Vec<Patch>':2,'Vec<u8>':2,'Vec<Option<ScanPlan>>':2,
                  'AdoptedProof':4,'AdoptionBodyV1':1,'CacheConstructionFailure':1,
                  'Option<Result<SwiftFunctionCache, CacheConstructionFailure>>':1,
                  'InitialProfileConstructionOutcomeV1':1,'SnapshotAttemptV1':2}
        for key in ('Partial','Vec<SwiftSlot>','Vec<PinRecord>','Vec<Patch>','Vec<u8>','Vec<Option<ScanPlan>>','AdoptedProof','CacheConstructionFailure','Option<Result<SwiftFunctionCache, CacheConstructionFailure>>','InitialProfileConstructionOutcomeV1'):
            self.assertEqual(expected[key],raws[key]+forwarded[key],key)
        self.assertEqual(2,sum(v for k,v in raws.items() if k.endswith('>::Attempt')))
        self.assertEqual(expected,self.ledger['constructor_applicability']['typed_internal_destructor_cuts'])
        self.assertEqual({'payload::'+k:v for k,v in expected.items()},self.ledger['nodes']['accepted_constructor_region']['payload'])
        self.assertEqual(1,forwarded['Partial']);self.assertEqual(4,raws['Partial'])

    def test_12_all33_leaf_cuts_composition_and_required_inputs(self):
        leaf=load(V/'swift-guarded-snapshot-leaf-shell-cost/cost-interface.json')
        cuts=leaf['required_nonzero_callee_drop_and_backing_cuts']
        self.assertEqual(33,len(cuts));self.assertEqual(21,len(self.contract['exports']))
        self.assertEqual(set(self.contract['exports']),{k for k in cuts if k.startswith('callee::') or k.startswith('core_')})
        self.assertEqual(2,cuts['callee::std::mem::drop::<Option<experimental_swift_reactor::cache::SwiftFunctionCache>>'])
        self.assertEqual(12,len(set(cuts)-set(self.contract['exports'])))
        self.assertIn('retained_dynamic_resource_backing_and_native_transfer_allowance',cuts)
        e=self.evaluator;route=e.canonical_route();rows=self.contract['exports'].values()
        maps=[{k:16 for r in rows for k in r['native']},{k:256 for r in rows for k in r['unsized']},
              {k:100 for r in rows for k in r['payload']},{r['required_private_primitive_cut']:100 for r in rows}]
        for name,row in self.contract['exports'].items():
            terms=[(0,k) for k in row['native']]+[(1,k) for k in row['unsized']]+[(2,k) for k in row['payload']]+[(3,row['required_private_primitive_cut'])]
            for i,k in terms:
                for bad in (None,0,-1,True,False,1.5,'8',e.MAX+1):
                    m=copy.deepcopy(maps)
                    if bad is None:m[i].pop(k)
                    else:m[i][k]=bad
                    with self.assertRaises(ValueError):e.evaluate_synthetic(self.contract,name,route,*m)
                    type(self).required_negatives+=1
        self.assertEqual(19,len({k for r in rows for k in r['payload']}))
        self.assertEqual({'str','[Option<ReservationTicket>]'},set(maps[1]))

    def test_13_capture_roster_finding_and_corrected_control(self):
        with self.assertRaisesRegex(ValueError,'omitted actual eighth'):validate_roster_capture_plan(self.roster,self.captures)
        amended=copy.deepcopy(self.roster)
        next(q for q in amended['queries'] if q['index']==8)['creation_contexts'][0]['captures']=[
            {k:r[k] for k in ('field','local','compiler_type')} for r in self.captures['fields']]
        validate_roster_capture_plan(amended,self.captures)
        for index in (4,5,6,7):
            m=copy.deepcopy(amended);next(q for q in m['queries'] if q['index']==8)['creation_contexts'][0]['captures'][index]['field']='wrong'
            with self.assertRaises(ValueError):validate_roster_capture_plan(m,self.captures)

    def test_14_verified_ZST_receipt_and_unqualified_zero_controls(self):
        e=self.evaluator;keys={k for r in self.contract['exports'].values() for k in r['native']}
        zst=next(q['key'] for q in self.roster['queries'] if q['index']==10)
        self.assertEqual([],next(q for q in self.roster['queries'] if q['index']==10)['creation_contexts'][0]['captures'])
        n=next(n for n in self.ledger['nodes'].values() if 'control.rs:719:67:' in n.get('MIR_header',''))
        body=self.mir[n['MIR_header']]
        self.assertNotRegex(body,r'\(\*_1\)\.\d+:')
        sizes={k:16 for k in keys};sizes[zst]=0
        receipt=dict(source_tree_sha256=TREE,native_query_roster_sha256=self.contract['native_query_roster_sha256'],
                     target='aarch64-apple-darwin',scope='compiler-observed-source146-size-and-alignment',product_executed=False,
                     compiler_receipt_sha256='0'*64,observations=[dict(key=k,size=v,alignment=1 if v==0 else 8,
                         kind='actual-size-and-alignment',source_tree_sha256=TREE,compiler_diagnostic_binding_sha256='0'*64) for k,v in sorted(sizes.items())])
        raw=canon(receipt);bound=e.bind_native(raw,sha(raw),self.contract)
        unsized={k:256 for r in self.contract['exports'].values() for k in r['unsized']}
        payload={k:100 for r in self.contract['exports'].values() for k in r['payload']}
        private={r['required_private_primitive_cut']:100 for r in self.contract['exports'].values()}
        safe=dict(sizes);safe[zst]=1
        for name,row in self.contract['exports'].items():
            actual=e.evaluate_bound(self.contract,name,e.canonical_route(),bound,unsized,payload,private)
            expected=e.evaluate_synthetic(self.contract,name,e.canonical_route(),safe,unsized,payload,private)-row['native'].get(zst,0)
            self.assertEqual(expected,actual['conditional_logical_price']);self.assertFalse(actual['operational_grant'])
            if zst in row['native']:
                with self.assertRaises(ValueError):e.evaluate_synthetic(self.contract,name,e.canonical_route(),sizes,unsized,payload,private)
        with self.assertRaises(ValueError):e.bind_native(raw,'f'*64,self.contract)
        bad=copy.deepcopy(receipt);bad['observations']=[r for r in bad['observations'] if r['key']!=zst];b=canon(bad)
        with self.assertRaises(ValueError):e.bind_native(b,sha(b),self.contract)
        # This is a synthetic receipt-format control; no actual ZST layout is observed here.

    def test_15_full3072_layout_context_binding_and_named_release(self):
        raw=gzip.decompress((V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz').read_bytes())
        self.assertEqual('6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a',sha(raw))
        records=re.findall(rb'^print-type-size type: `(.+)`: (\d+) bytes, alignment: (\d+) bytes$',raw,re.M)
        self.assertEqual(3072,len(records));self.assertEqual(87,len(self.obs['resolved']));self.assertEqual(13,len(self.obs['missing']))
        self.assertEqual('experimental_swift_reactor::control::Cursor',self.obs['resolved']['Cursor']['qualified'])
        self.assertEqual(32,self.obs['resolved']['Cursor']['size']);self.assertEqual(64,self.obs['resolved']['Fault']['size'])
        release=V/'swift-semantic-adapter-root-review/guarded-snapshot-source146-callee-storage-layout-release.json'
        self.assertEqual('a7ac0e94930307cb667e8dc0d2bfa516da192957a66b5089bc873795e76211b6',sha(release.read_bytes()))
        folder=V/'swift-guarded-snapshot-source146-callee-storage-layouts'
        self.assertEqual(22,rehash_packet(folder,'9e2cd764548188b30c93d045fdc72d59c771a4cd489858d6340f131bc67b1001')['members'])
        results=load(folder/'results.json');diagnostics=results['diagnostics']
        self.assertEqual(42,len(diagnostics))
        for q in self.roster['queries'][:8]:
            rows=[r for r in diagnostics if r['index']==q['index']]
            self.assertEqual({'size','align'},{r['kind'] for r in rows})
            self.assertTrue(all(r['concrete']==q['concrete_type'] for r in rows))

    def test_16_all13_actual_native_observations_and_receipt_bound_zero(self):
        rows=native_observations(self.roster)
        self.assertEqual([16,1240,40,2640,24,32,4024,16,64,16,0,16,16],[r['size'] for r in rows])
        compiler_inputs=[dict(path=p,sha256=sha((ROOT/p).read_bytes())) for p in [
            'verification/swift-guarded-snapshot-source146-callee-storage-layouts/compiler-receipt.json',
            'verification/swift-guarded-snapshot-source146-closure-layouts/compiler-receipt.json']]
        receipt=dict(source_tree_sha256=TREE,native_query_roster_sha256=self.contract['native_query_roster_sha256'],
                     target='aarch64-apple-darwin',scope='compiler-observed-source146-size-and-alignment',
                     product_executed=False,compiler_receipt_sha256=sha(canon(compiler_inputs)),observations=rows)
        raw=canon(receipt);bound=self.evaluator.bind_native(raw,sha(raw),self.contract)
        sizes={r['key']:r['size'] for r in rows};route=self.evaluator.canonical_route()
        unsized={k:256 for r in self.contract['exports'].values() for k in r['unsized']}
        payload={k:100 for r in self.contract['exports'].values() for k in r['payload']}
        private={r['required_private_primitive_cut']:100 for r in self.contract['exports'].values()}
        for name,row in self.contract['exports'].items():
            expected=row['fixed']+sum(n*sizes[k] for k,n in row['native'].items())
            expected+=sum(2*n*unsized[k] for k,n in row['unsized'].items())
            expected+=sum(n*payload[k] for k,n in row['payload'].items())+private[row['required_private_primitive_cut']]
            actual=self.evaluator.evaluate_bound(self.contract,name,route,bound,unsized,payload,private)
            self.assertEqual(expected,actual['conditional_logical_price']);self.assertFalse(actual['operational_grant'])
        # Exact original span and fully qualified named type are both mandatory.
        for index in (0,8):
            altered=copy.deepcopy(self.roster)
            if index==0:altered['queries'][index]['concrete_type']='u64'
            else:altered['queries'][index]['key']=altered['queries'][index]['key'].replace(':686:23:',':686:24:')
            with self.assertRaises(ValueError):native_observations(altered)

    def test_17_real_payload_omission_adversary(self):
        m=copy.deepcopy(self.ledger);m['nodes']['drop_proof']['payload'].pop('payload::AdoptionBodyV1')
        with self.assertRaisesRegex(ValueError,'typed destructor interface omitted'):check_call_edges(m,self.mir)

if __name__ == '__main__':
    unittest.main(verbosity=2)
