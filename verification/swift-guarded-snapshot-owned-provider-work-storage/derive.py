#!/usr/bin/env python3
"""Derive a logical source/typed-inline interface from frozen source and MIR.

No compiler, native process, input acquisition or product execution is invoked.
Dynamic operand bodies and every newly encountered std call remain explicit.
"""
from pathlib import Path
import collections, gzip, hashlib, importlib.util, json, re, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
PROVIDER = V / 'swift-guarded-snapshot-owned-binding-provider'
INDEPENDENT = V / 'swift-guarded-snapshot-owned-provider-independent'
OUTER = V / 'swift-guarded-snapshot-outer-parent-work-storage'
TREE = 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
NAME = 'describe_existing_owner_candidate_v1'
INPUTS = {}
def sha(data): return hashlib.sha256(data).hexdigest()
def canon(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(path, data): return {'path': path, 'bytes': len(data), 'sha256': sha(data)}
def require(ok, label):
    if not ok: raise ValueError(label)
def read(path):
    data = path.read_bytes(); name = path.relative_to(ROOT).as_posix()
    INPUTS[name] = row(name, data); return data
def load(path): return json.loads(read(path))
def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod); return mod
def norm(ty):
    ty = re.sub(r'\b(?:[A-Za-z_]\w*::)+', '', ty).replace("'static", "'_")
    ty = re.sub(r"(&)\s*'[_A-Za-z]\w*\s+", r'\1', ty)
    return re.sub(r';\s*', '; ', ty)
def strip_comment(line):
    quoted = escaped = False
    for i, char in enumerate(line):
        if escaped: escaped = False; continue
        if quoted and char == '\\': escaped = True; continue
        if char == '"': quoted = not quoted
        if not quoted and line[i:i+2] == '//': return line[:i].rstrip()
    return line.rstrip()
def partition(text):
    lines = text.splitlines(); out = []; i = 0; covered = ignored = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith('//'): ignored += 1; i += 1; continue
        require(not line[0].isspace() and not line.startswith('}'), 'unpartitioned MIR top-level')
        start = i; i += 1
        if line.endswith(' {'):
            while i < len(lines) and not lines[i].startswith('}'): i += 1
            require(i < len(lines) and lines[i] == '}', 'unfinished MIR construct'); i += 1
        else: require(line.startswith('const ') and line.endswith(';'), 'unknown MIR top-level')
        out.append('\n'.join(lines[start:i])); covered += i-start
    require(covered + ignored == len(lines), 'complete MIR partition')
    return out
def provider_constructs(blocks):
    return [b for b in blocks if b.startswith(('fn '+NAME+'(', 'fn '+NAME+'::', 'const '+NAME, 'const InputBackingDescriptionV1::'))]
def normalized(body):
    # Remove comments only outside strings; all paths are replaced literally,
    # including closure type identity. Production source coordinates stay exact.
    a = str(INDEPENDENT / 'owned-work/compiler-metadata-mir/vm')
    b = str(HERE / 'owned-work/capture-layout/vm')
    return '\n'.join(strip_comment(l).replace(a, '<SOURCE>').replace(b, '<SOURCE>') for l in body.splitlines() if strip_comment(l).strip())
def packet(folder, expected, count, size):
    seal_bytes = read(folder / 'seal.json'); seal = json.loads(seal_bytes)
    require(sha(seal_bytes) == expected, 'frozen packet seal:'+str(folder))
    require(len(seal['members']) == count and sum(r['bytes'] for r in seal['members']) == size, 'frozen packet closure')
    for item in seal['members']: require(row(item['path'], read(folder / item['path'])) == item, 'frozen member:'+item['path'])
def source():
    custody = load(PROVIDER / 'proposed-source-custody.json'); src = {}
    for item in custody:
        data = read(ROOT / item['origin']); require(row(item['path'], data) == {k: item[k] for k in ('path', 'bytes', 'sha256')}, 'source custody:'+item['path']); src[item['path']] = data
    rows = [row(name, data) for name, data in src.items()]
    require(len(rows) == 146 and sha(canon(rows)) == TREE, 'exact accepted source146')
    return src
def parse_roles(body, helper):
    params = re.search(r'\((.*)\) ->', body.splitlines()[0])[1]
    parsed = [{'local': name, 'type': ty, 'kind': 'parameter'} for name, ty in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)', params)]
    parsed += [{'local': name, 'type': ty, 'kind': 'return' if name == '_0' else 'local'} for name, ty in re.findall(r'^\s+let(?: mut)? (_\d+): ([^\n]+?);(?: +//|$)', body, re.M)]
    require(len(parsed) == len({r['local'] for r in parsed}), 'unique complete typed roles')
    return parsed
def parse_blocks(body):
    out = {}
    for match in re.finditer(r'^    (bb\d+)( \(cleanup\))?: \{\n(.*?)^    \}', body, re.M | re.S):
        operations = [strip_comment(l).strip() for l in match[3].splitlines()]
        operations = [line for line in operations if line]
        require(operations, 'empty block')
        last = operations[-1]
        out[match[1]] = {'cleanup': bool(match[2]), 'operations': operations, 'successors': sorted(set(re.findall(r'\bbb\d+\b', last))), 'unwind': 'unwind continue' in last, 'terminator': last}
    require(out and all(s in out for b in out.values() for s in b['successors']), 'all successors bound')
    return out
def sccs(blocks):
    index = 0; stack = []; indices = {}; low = {}; active = set(); result = []
    def visit(node):
        nonlocal index
        indices[node] = low[node] = index; index += 1; stack.append(node); active.add(node)
        for successor in blocks[node]['successors']:
            if successor not in indices: visit(successor); low[node] = min(low[node], low[successor])
            elif successor in active: low[node] = min(low[node], indices[successor])
        if low[node] == indices[node]:
            component = []
            while True:
                nxt = stack.pop(); active.remove(nxt); component.append(nxt)
                if nxt == node: break
            result.append(sorted(component))
    for node in blocks:
        if node not in indices: visit(node)
    return result
IDENTITY_SCC = {'bb2','bb3','bb5','bb7','bb8','bb10','bb11','bb12','bb13','bb14','bb15'}
PATH_SCC = {'bb26','bb27','bb28','bb30','bb31','bb32','bb33','bb35','bb36','bb38','bb39','bb40','bb42','bb43','bb44','bb45','bb46','bb47','bb48','bb49','bb50','bb51','bb52','bb53'}
def bounded_multiplicities(blocks, main):
    cycles = [set(c) for c in sccs(blocks) if len(c) > 1 or c[0] in blocks[c[0]]['successors']]
    if not main: require(not cycles, 'unexpected secondary cycle'); return {n: 1 for n in blocks}
    require({frozenset(c) for c in cycles} == {frozenset(IDENTITY_SCC), frozenset(PATH_SCC)}, 'exact two source-bounded loops')
    require(blocks['bb15']['successors'] == ['bb2'] and blocks['bb53']['successors'] == ['bb26'], 'exact loop backedges')
    require('end: const 12_usize' in '\n'.join(blocks['bb0']['operations']) and 'end: const 5_usize' in '\n'.join(blocks['bb24']['operations']), 'exact source range caps')
    out = {name: 1 for name in blocks}
    for name in IDENTITY_SCC: out[name] = 13 if name in ('bb2', 'bb3') else 12
    for name in PATH_SCC: out[name] = 6 if name in ('bb26', 'bb27') else 5
    return out
def cut_paths(blocks, main):
    backedges = {('bb15','bb2'),('bb53','bb26')} if main else set(); paths = []
    def visit(node, prior):
        require(node not in prior, 'unfunded cycle'); route = prior + [node]; block = blocks[node]
        if block['unwind']: paths.append({'blocks': route, 'terminal': 'unwind-continue'})
        if not block['successors']:
            require(block['terminator'] in ('return;', 'unreachable;'), 'unknown terminal')
            paths.append({'blocks': route, 'terminal': block['terminator'][:-1]})
        for successor in block['successors']:
            if (node, successor) in backedges: paths.append({'blocks': route, 'terminal': 'bounded-loop-backedge', 'successor': successor})
            else: visit(successor, route)
    visit('bb0', []); return paths
def layouts(src):
    plan = load(HERE / 'compiler-plan.json'); receipt = load(HERE / 'commands/capture-layout/receipt.json')
    require(sha(read(HERE / 'query_once.py')) == plan['runner_sha256'], 'exact compiler runner')
    require(all(receipt[k] == value for k, value in plan.items()), 'exact predeclared compiler argv/env/source')
    require(receipt['success'] and receipt['exit_code'] == 0 and receipt['compiler_invocations'] == 1 and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['owned_scratch_removed'], 'sole compiler terminal/cleanup')
    auth = load(HERE / 'compiler-root-authorization.json'); require(auth['plan_sha256'] == sha(read(HERE / 'compiler-plan.json')) and auth['authorized_invocations'] == 1, 'exact root-authorized compiler plan')
    manifest=load(HERE/'query-source-manifest.json');tail=read(HERE/'query-layout.inc.rs');profile=read(HERE/'query-profile.rs')
    require(row('query-layout.inc.rs',tail)==plan['query_tail'] and row('query-profile.rs',profile)==plan['query_profile'],'exact predeclared query text')
    fragment=read(PROVIDER/'existing-owner-candidate.inc.rs');needle=fragment+b'\n}\n}\n'
    require(src[PROFILE].endswith(needle),'exact provider insertion boundary')
    expected_profile=src[PROFILE][:-len(needle)]+fragment[:-2]+tail+fragment[-2:]+b'\n}\n}\n'
    require(profile==expected_profile,'unchanged production body plus exact inert query suffix')
    expected_rows=[row(name,profile if name==PROFILE else data) for name,data in src.items()]
    require(manifest['members']==expected_rows and manifest['member_count']==146 and sha(canon(expected_rows))==manifest['tree_sha256']==plan['query_tree_sha256'],'complete predeclared146 query source custody')
    for name in ('stdout', 'stderr'): require(row(name, read(HERE / 'commands/capture-layout' / name)) == receipt[name], 'compiler output:'+name)
    raw = None
    for artifact in receipt['artifacts']:
        if artifact['path'] == 'query.rmeta': continue
        compressed = read(HERE / 'commands/capture-layout' / (artifact['path'] + '.gz'))
        require(len(compressed) == artifact['gzip_bytes'] and sha(compressed) == artifact['gzip_sha256'], 'compiler compressed artifact')
        data = gzip.decompress(compressed); require(row(artifact['path'], data) == {k: artifact[k] for k in ('path','bytes','sha256')}, 'compiler raw artifact')
        if artifact['path'] == 'query.mir': raw = data.decode()
    require(raw is not None, 'full MIR retained')
    q = next(b for b in partition(raw) if b.startswith('fn owned_provider_remaining_layout_query_v1('))
    values = list(map(int, re.findall(r'\[u8; (\d+)\]', q.splitlines()[0])))
    require(len(values) == 36, 'all18 named query pairs')
    observed = [{'name': item['name'], 'type': item['type'], 'size': values[2*i], 'align': values[2*i+1], 'evidence': 'exact production MIR query signature'} for i, item in enumerate(plan['named_layout_queries'])]
    table = {norm(r['type']): {'bytes': r['size'], 'alignment': r['align'], 'rule': r['evidence']} for r in observed}
    previous = load(INDEPENDENT / 'layouts.json')
    for item in previous['rows']:
        key = norm(item['type']); data = {'bytes': item['size'], 'alignment': item['align'], 'rule': 'root-accepted provider exact named query'}
        if key in table: require((table[key]['bytes'], table[key]['alignment']) == (item['size'], item['align']), 'layout conflict')
        else: table[key] = data
    stdout = read(HERE / 'commands/capture-layout/stdout').decode()
    prefix = str(HERE / 'owned-work/capture-layout/vm')
    capture = '{closure@' + prefix + '/'+PROFILE+':1185:27: 1185:30}'
    matches = re.findall(r'^print-type-size type: `'+re.escape(capture)+r'`: (\d+) bytes, alignment: (\d+) bytes$', stdout, re.M)
    require(len(matches) == 1, 'actual production closure aggregate observed exactly once')
    closure = {'bytes': int(matches[0][0]), 'alignment': int(matches[0][1]), 'rule': 'actual unchanged production closure forced by exact HRTB pointer; print-type-sizes aggregate observation'}
    require((closure['bytes'], closure['alignment']) == (16,8), 'concrete capture16/8')
    # Exact named print-type-size record supplies the referenced preimage body.
    full = 'experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::outer_parent_v1::ImmutableIdentityPreimageV1<\'_>'
    found = re.findall(r'^print-type-size type: `'+re.escape(full)+r'`: (\d+) bytes, alignment: (\d+) bytes$', stdout, re.M)
    require(found == [('48','8')], 'exact original preimage48/8')
    table["ImmutableIdentityPreimageV1<'_>"] = {'bytes': 48, 'alignment': 8, 'rule': 'exact named production print-type-sizes record'}
    table.update({name: {'bytes': size, 'alignment': align, 'rule': 'inherited aarch64 primitive extent'} for name,size,align in [('()',0,1),('!',0,1),('bool',1,1),('u8',1,1),('usize',8,8),('isize',8,8)]})
    return raw, table, closure, {'schema': 1, 'named_observations': observed, 'anonymous_capture': closure | {'exact_type': capture, 'MIR_capture_fields': ['native_path_bodies: &[&[u8]; 5]', 'position: &usize'], 'padding_inferred_from_fields': False, 'compiler_record_detail': 'end padding:16 bytes; retained verbatim compiler presentation, not a claim that captures are padding'}, 'closure_layout_observations': 2, 'previous_named_observations': previous['observations'], 'new_named_observations': len(values), 'compiler_success': True}
def extent(ty, table, closure, helper):
    ty = norm(ty)
    if ty.startswith('{closure@'): return dict(closure)
    if ty in table: return dict(table[ty])
    if ty.startswith('['):
        element, count = helper.split(ty[1:-1], ';'); base = extent(element, table, closure, helper)
        return {'bytes': base['bytes']*int(count), 'alignment': base['alignment'], 'rule': 'fixed array of observed element extents'}
    raise ValueError('missing concrete native layout:'+ty)
def affine(fixed=0, body=0): return {'fixed': fixed, 'input_operand_bytes': body}
def plus(*items): return {key: sum(item[key] for item in items) for key in ('fixed','input_operand_bytes')}
def times(value, count): return {key: value[key]*count for key in value}
def shape(ty, shapes):
    ty = norm(ty)
    if ty.startswith('{closure@'): return 2
    if ty == 'Range<usize>': return 2
    if ty == 'OsStr': return 1
    return shapes.n(ty)
def role_layout(role, table, closure, helper, shapes):
    ty = norm(role['type']); role.update(extent(ty, table, closure, helper)); role['scalar_leaves'] = shape(ty, shapes)
    pointee = re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?", '', ty) if ty.startswith('&') else None
    role['pointee_type'] = pointee
    if pointee in ('[u8]', 'Path', 'OsStr'):
        role['pointee_bytes'] = affine(body=1); role['pointee_scalar_leaves'] = affine(body=1)
        role['pointee_rule'] = 'actual logical input byte body <= input_operand_bytes=max22 actual body lengths; allocator/private representation not claimed'
    elif pointee:
        role['pointee_bytes'] = affine(extent(pointee,table,closure,helper)['bytes']); role['pointee_scalar_leaves'] = affine(shape(pointee,shapes)); role['pointee_rule'] = 'one immediate observed pointee extent; no recursive ownership/backing credit'
    else: role['pointee_bytes'] = affine(); role['pointee_scalar_leaves'] = affine(); role['pointee_rule'] = None
    return role
def constants(code):
    result = []
    for match in re.finditer(r'\bconst\s+',code):
        tail = code[match.end():]
        found = re.match(r'(\d+)_(usize|isize|u8)|true\b|false\b|\(\)|(?:[A-Za-z_]\w*::)*SELECTED_SOURCE_BYTES_V1\b|(?:[A-Za-z_]\w*::)*SELECTED_SOURCE_SHA256_V1\b|(?:[A-Za-z_]\w*::)*describe_existing_owner_candidate_v1::promoted\[[01]\]', tail)
        require(found is not None, 'unpriced constant:'+code)
        text = found[0]
        width = 0 if text == '()' else 1 if text in ('true','false') or text.endswith('_u8') else 32 if norm(text) == 'SELECTED_SOURCE_SHA256_V1' else 8
        result.append({'text': text, 'bytes': width, 'scalar_leaves': 32 if width == 32 else 1})
    return result
def price(code, by):
    mentions = re.findall(r'\b_\d+\b',code); require(all(n in by for n in mentions), 'unbound typed operand')
    const = constants(code)
    base = 2 + sum(code.count(char) for char in '()[].*&') + len(re.findall(r'\bas\b',code))
    source = affine(base + 2*sum(by[n]['scalar_leaves'] for n in mentions) + 2*sum(c['scalar_leaves'] for c in const))
    native = affine(2*sum(by[n]['bytes'] for n in mentions) + 2*sum(c['bytes'] for c in const))
    source = plus(source, *[times(by[n]['pointee_scalar_leaves'],2) for n in mentions])
    native = plus(native, *[times(by[n]['pointee_bytes'],2) for n in mentions])
    if code == 'return;':
        source = plus(source, affine(2*by['_0']['scalar_leaves']), times(by['_0']['pointee_scalar_leaves'],2))
        native = plus(native, affine(2*by['_0']['bytes']), times(by['_0']['pointee_bytes'],2))
    return {'code':code, 'mentions':mentions, 'constants':const, 'source_action_units':source, 'native_sized_occurrence_bytes':native, 'combined':plus(source,native)}
CALL_KEYS = [
    ('IntoIterator>::into_iter', 'range_into_iter'), ('as Iterator>::next', 'range_next'),
    ('core::slice::<impl [u8]>::len', 'slice_len'), ('::checked_add(', 'usize_checked_add'),
    ('Option::<usize>::ok_or', 'option_ok_or_shape_refusal'), (' as Try>::branch', 'result_try_branch'),
    (' as FromResidual<', 'candidate_result_from_residual'), ('<[u8; 32] as PartialEq>::ne', 'digest_array_ne32'),
    ('Path::as_os_str', 'path_as_os_str'), ('<OsStr as OsStrExt>::as_bytes', 'osstr_as_bytes'),
    ('core::slice::<impl [u8]>::is_empty', 'slice_is_empty'), ('core::slice::<impl [u8]>::contains', 'slice_contains_u8'),
    ('<&[u8] as PartialEq>::ne', 'slice_reference_ne'), ('Option::<usize>::and_then', 'option_and_then_excluding_authored_callback'),
]
def classify_call(code):
    if ' -> [return:' not in code: return None
    found = [key for needle,key in CALL_KEYS if needle in code]
    require(len(found) == 1, 'unknown or ambiguous std interface:'+code); return found[0]
def derive():
    INPUTS.clear()
    packet(PROVIDER,'7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de',50,431429)
    packet(INDEPENDENT,'8138bc61fdcca8662a9a7a3784f4dd8f4db9742db59faeffa872e899fc18e801',41,4276782)
    accepted = {}
    for name, digest in [('owned-binding-provider','998a7f6de2918e6b643360b4e67475fdc9a468d69792eb5cda3bb773272fcba3'),('scoped-binding-source','1bc55306a1f6cf220660efa8ab9e34485d610ae806ebd56a1733d892ddfcd2e1'),('outer-parent-work-storage','8b6190049be7d5c995b6bd01c477454e503ac1dcad518602370416f510779d9c'),('host-storage','9862bbe187dea2e1c6999218604ec43db3d3c9bc28d4fd815615d81dd98df432')]:
        path = V/'swift-semantic-adapter-root-review'/('guarded-snapshot-'+name+'-host-acceptance.json')
        data = read(path); require(sha(data) == digest, 'exact root acceptance:'+name); accepted[name] = json.loads(data)
    require(accepted['owned-binding-provider']['old_production_MIR_constructs_preserved'] == 6006 and accepted['scoped-binding-source']['explicit_conditional_source_work_storage_rebind']['selected'], 'mandatory complete6006 source-only rebind')
    # The old model and its complete storage composer remain byte-bound imports.
    for folder, files in [(OUTER, ['model.py','candidate.json','source-shapes.json','phase-roster.json','seal.json']), (V/'swift-guarded-snapshot-host-storage-composition',['model.py','inline-inventory.json'])]:
        for file in files: read(folder/file)
    old_seal = load(OUTER/'seal.json'); require(sha(read(OUTER/'seal.json')) == accepted['outer-parent-work-storage']['producer']['seal_sha256'], 'accepted inherited model seal')
    for name in ('model.py','candidate.json','source-shapes.json','phase-roster.json'):
        require(row(name,read(OUTER/name)) == next(r for r in old_seal['members'] if r['path']==name), 'accepted inherited member:'+name)
    storage_folder=V/'swift-guarded-snapshot-host-storage-composition';storage_seal=load(storage_folder/'seal.json')
    require(sha(read(storage_folder/'seal.json'))==accepted['host-storage']['producer']['seal_sha256'],'accepted complete old storage composer seal')
    for name in ('model.py','inline-inventory.json'):
        require(row(name,read(storage_folder/name))==next(r for r in storage_seal['members'] if r['path']==name),'complete old storage import:'+name)
    src = source(); helper_path = V/'swift-guarded-snapshot-parent-work-source146/helpers.py'; helper_data = read(helper_path)
    require(sha(helper_data) == load(OUTER/'candidate.json')['source_helper_sha256'], 'accepted bounded source shape helper')
    helper = module(helper_path,'provider_work_accepted_shapes'); shapes = helper.SourceShapes(src)
    raw, table, closure, layout_report = layouts(src)
    new = provider_constructs(partition(raw)); old = provider_constructs(partition(read(INDEPENDENT/'provider.mir').decode()))
    require(len(new) == len(old) == 11 and [normalized(b) for b in new] == [normalized(b) for b in old], 'all11 provider constructs byte-identical modulo exact query path/comments')
    functions = []; slots = []; calls = collections.Counter(); full_calls = []
    for body in new:
        header = body.splitlines()[0]
        standalone = '\n' not in body
        if standalone:
            name = header.split(': usize',1)[0]; rs = [{'local':'_constant','type':'usize','kind':'standalone-constant'}]
            role_layout(rs[0],table,closure,helper,shapes)
            # Standalone constant definitions are compiler-time constructs;
            # they are nevertheless separately conservatively source-charged.
            code = header.split(' = ',1)[1]; by = {r['local']:r for r in rs}; blocks = {'constant':{'operations':[code],'successors':[],'cleanup':False,'unwind':False,'terminator':'constant-definition'}}; caps={'constant':1}; routes=[]
        else:
            main = header.startswith('fn '+NAME+'(')
            name = header.split('(',1)[0] if header.startswith('fn ') else header.split(': &',1)[0]
            if header.startswith('fn '): rs = parse_roles(body,helper)
            else:
                rs = [{'local': n, 'type': ty, 'kind': 'return' if n=='_0' else 'promoted-local'} for n,ty in re.findall(r'^\s+let(?: mut)? (_\d+): ([^\n]+?);(?: +//|$)',body,re.M)]
            for role in rs: role_layout(role,table,closure,helper,shapes)
            by={r['local']:r for r in rs}; blocks=parse_blocks(body); caps=bounded_multiplicities(blocks,main); routes=cut_paths(blocks,main)
        invocation_cap = 5 if header.startswith('fn '+NAME+'::{closure#0}') else 1
        for block_name, block in blocks.items():
            block['per_invocation_cap'] = caps[block_name]; block['rows'] = [price(code,by) for code in block['operations']]
            for code in block['operations']:
                key=classify_call(code)
                if key:
                    count=caps[block_name]*invocation_cap; calls[key] += count
                    full_calls.append({'function':name,'block':block_name,'code':code,'interface':key,'call_cap':count,'callee_work_selected':False,'authored_callback_work_separately_charged':key=='option_and_then_excluding_authored_callback'})
        params=[r for r in rs if r['kind']=='parameter']
        entry = plus(affine(2+2*sum(r['scalar_leaves']+r['bytes'] for r in params)),*[times(plus(r['pointee_bytes'],r['pointee_scalar_leaves']),2) for r in params])
        surface=plus(entry,*[times(row_['combined'],caps[bn]) for bn,b in blocks.items() for row_ in b['rows']])
        end=sum(2+2*r['scalar_leaves']+2*r['bytes'] for r in rs)
        work=times(plus(surface,affine(end)),invocation_cap)
        for role in rs:
            uses=[bn for bn,b in blocks.items() if any(role['local'] in x['mentions'] for x in b['rows'])]
            slots.append({'id':name+':'+role['local'],'type':role['type'],'kind':role['kind'],'bytes':role['bytes'],'alignment':role['alignment'],'used_in_blocks':uses,'reserved_first':'P0_BEFORE_ANY_PROVIDER_OR_ACQUISITION_POLICY_QUOTE_ACCOUNT_ENTRY','reserved_last':'P0_AFTER_FINAL_OUTER_RESULT_CONSUMPTION','funded_by':'P0','invocation_storage_instances':1,'invocation_work_cap':invocation_cap,'rule':'every written logical slot retained, including moved/copied parameters, constructors, returns, closure captures, promoted/standalone constants; no physical alias/stack-reuse/refund credit'})
        functions.append({'name':name,'header':header,'kind':'standalone-constant' if standalone else 'function' if header.startswith('fn ') else 'promoted-constant','MIR_sha256':sha(body.encode()),'roles':rs,'blocks':blocks,'bounded_cut_paths':routes,'per_request_invocation_cap':invocation_cap,'entry':entry,'weighted_surface':surface,'finite_role_end_envelope_per_invocation':end,'work_per_request':work,'logical_inline_slots':sum(r['bytes'] for r in rs)})
    require(len(functions)==11 and len(slots)==193,'complete11 constructs193 typed/constant roles')
    main=next(f for f in functions if f['header'].startswith('fn '+NAME+'(')); callback=next(f for f in functions if f['header'].startswith('fn '+NAME+'::{closure#0}'))
    require(len(main['roles'])==171 and len(callback['roles'])==11,'171 main +11 closure roles')
    require(sum(len(b['operations']) for b in main['blocks'].values()) > 500,'raw MIR includes full storage annotations')
    require(len(full_calls)==26 and calls['range_next']==19 and calls['slice_len']==33 and calls['usize_checked_add']==22 and calls['option_and_then_excluding_authored_callback']==5,'loop and callback call multiplicities')
    inline=sum(r['bytes'] for r in slots)
    # One external caller-result place is distinct from every written return /
    # intermediate slot. Unwritten future caller/launcher slots remain input.
    output=table["Result<UnqualifiedExistingOwnerCandidateV1<'_>, CandidateShapeRefusalV1>"]['bytes']
    output_shape=shape("Result<UnqualifiedExistingOwnerCandidateV1<'_>, CandidateShapeRefusalV1>",shapes)
    result_end=2+2*output_shape+2*output
    work=plus(*[f['work_per_request'] for f in functions],affine(result_end))
    old=accepted['outer-parent-work-storage']['arithmetic']
    source_map={'schema':1,'tree_sha256':TREE,'old6006_constructs_preserved':True,'old1785_standalone_constants_preserved':True,'old_source_costs_reused_only_through_root_accepted_scoped_binding_rebind':True,'new11_constructs_unchanged_by_forced_query':True,'main_roles':len(main['roles']),'closure_roles':len(callback['roles']),'promoted_roles':4,'standalone_constant_roles':7,'total_roles':len(slots),'functions':functions}
    candidate={'schema':1,'status':'conditional-provider-source-work-storage-interface-candidate-needs-fresh-independent-review','source_tree_sha256':TREE,'constructs':11,'main_roles':171,'closure_roles':11,'promoted_roles':4,'standalone_constant_roles':7,'roles':len(slots),'written_operations':sum(len(b['operations']) for f in functions for b in f['blocks'].values()),'typed_inline_slots':inline,'external_caller_result_slot':output,'provider_inline_addition':inline+output,'prior_P0_fixed':old['fixed_P0'],'conditional_P0_fixed':old['fixed_P0']+inline+output,'prior_whole_work_fixed':old['whole_fixed'],'provider_source_work':work,'conditional_whole_fixed_excluding_dynamic_operands_and_new_std_or_upstream_terms':old['whole_fixed']+work['fixed'],'external_result_end':result_end,'original_binding1168_preserved':True,'source_only_inherited_outer_work':2706170,'source_only_inherited_outer_roles':130,'inherited_residual_work_terms':{'L_str':67424,'P0_dynamic_backing':1,'P0_fixture_binding':1,'P0_root_route':1,'native_error_request':1,**{'native_open_request_'+str(i):1 for i in range(5)}},'new_required_std_interface_terms':dict(sorted(calls.items())),'new_required_upstream_work_terms':['actual_prepaid_acquisition_work','future_provider_caller_and_launcher_work'],'input_operand_bytes':'max of all12 identity +5native +5separately retained actual body lengths; no chosen finite maximum','all_written_slots_retained_P0':True,'zero_alias_move_or_sharing_credit':True,'caller_input_staging_unwritten':'future_root_inline mandatory positive input; no guessed extra moved-container size','backing_ownership':'original12 full preimages +5native Path allocations +5separately retained byte allocations are preserved exactly once; logical_input_backing_bytes is a descriptor, never a second allocation or alias credit','actual_input_caps':'provider only exactsource1947/claim and nonempty12/5, equality/noNUL and checkedu64 sum; frozen loader build/session/executable caps are additional conditional upstream checks in model.storage, not provider enforcement','anonymous_capture_layout':{'bytes':closure['bytes'],'alignment':closure['alignment'],'observed':True},'compiler_invocations':1,'Rust_runtime_tests':0,'source_unit':'inherited source/typed aggregate/finite-end occurrences plus native logical typed-byte allowances; every block weighted by explicit loop cap; no CPU, private std/compiler/panic/allocator/kernel cost','new_callee_contracts_selected':False,'actual_acquisition_or_authenticated_owner':False,'all_six_upstream_requirements':'Pending','all_three_selectors':'Pending','L_str_selected':False,'whole_quote_or_root_funding_or_operational_grant':False,'native_runtime_FieldLog_OTA_GA':False,'original_destructors_and_error_backing':'inherited full child/loader/payload/carrier/destructor/error and diagnostic backing terms retained; shared descriptor adds no error ownership','no_refund_on_None_refusal_unwind':True,'normal_release':'only after original payload/carrier destruction returns Some actual DestroyedStorageV1; P0 provider/output slots remain through final result consumption','fresh_independent_review_required':True}
    phases=load(OUTER/'phase-roster.json')['phases'];phase={'schema':1,'all_new_roles':slots,'provider_slots_bytes_each_phase':{p:inline for p in phases},'external_result_bytes_each_phase':{p:output for p in phases},'P0_new_total_each_phase':{p:inline+output for p in phases},'binding_container_inherited_once':1168,'all12identity_and5native_and5separate_body_backing_remain_required':True,'future_root_inline_backing_and_original_diagnostic_backing_remain_required':True,'destruction':'provider contains only shared references, scalar descriptions and pending marker values; no owned File/Error/backing acquisition. Finite ends price all roles, while original owner payload/carrier and upstream destructor obligations remain unchanged. No drop/refund authority derived from shape.'}
    contracts={'schema':1,'std_interfaces':[{'name':name,'count':count,'price':'strict positive externally reviewed bound required per logical callee interface invocation','unit':'logical work','selected':False,'scope':'new caller operand surface is priced; full std adapter source/private work has no invented0/1 cost; authored and_then closure work is charged separately'} for name,count in sorted(calls.items())],'full_call_roster':full_calls,'inherited10_residual_terms_preserved':candidate['inherited_residual_work_terms'],'upstream_six_Pending':['acquisition_work','acquisition_inline_and_temporary_storage','acquisition_owned_backing','provider_work_and_inline_storage','original_diagnostic_pointee_backing','admitted_owner_and_authenticated_correspondence'],'actual_backing_maximum_and_future_acquisition_required':True}
    return {'candidate.json':candidate,'source-typed-MIR-map.json':source_map,'phase-roster.json':phase,'layouts.json':layout_report,'required-input-contracts.json':contracts,'source-shapes.json':{'schema':1,'types':shapes.used},'input-custody.json':{'schema':1,'members':sorted(INPUTS.values(),key=lambda r:r['path'])}}
def main():
    result=derive()
    if sys.argv[1:]==['--check']:
        for name,value in result.items(): require(json.loads((HERE/name).read_bytes())==value,'stale derived evidence:'+name)
    else:
        require(not (HERE/'seal.json').exists(),'immutable packet')
        for name,value in result.items(): (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result['candidate.json'][k] for k in ('constructs','roles','written_operations','typed_inline_slots','provider_inline_addition','conditional_P0_fixed','provider_source_work','conditional_whole_fixed_excluding_dynamic_operands_and_new_std_or_upstream_terms')}))
if __name__=='__main__': main()
