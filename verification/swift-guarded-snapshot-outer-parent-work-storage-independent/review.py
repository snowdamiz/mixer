#!/usr/bin/env python3
"""Independent offline reconstruction. Never imports a producer calculator.

The declared unit is logical typed/source occurrences plus retained native
inline extents. This is not a compiler, execution, provider or receipt check.
"""
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
C = V / 'swift-guarded-snapshot-outer-parent-work-storage'
OLD = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
NEW = '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
NAMES = ('selected_outer_request_v1', 'borrow_original_diagnostics_once_v1',
         'observe_borrowed_originals_v1', 'run_selected_one_fixture_outer_v1',
         'consume_outer_request_v1')
checks = []
inputs = {}

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()
def row(p, b): return dict(path=p, bytes=len(b), sha256=sha(b))
def require(label, condition):
    if not condition: raise AssertionError(label)
    checks.append(label)
def read(p):
    require('no active lane read: ' + str(p), all(x not in str(p) for x in (
        'swift-guarded-snapshot-scoped-binding-source', 'native-open', 'string-correction')))
    b = p.read_bytes()
    inputs[p.relative_to(ROOT).as_posix()] = row(p.relative_to(ROOT).as_posix(), b)
    return b
def load(p): return json.loads(read(p))
def out(name, x): (HERE / name).write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')

def seal(p, expected=None, counts=None):
    raw = read(p / 'seal.json'); s = json.loads(raw)
    if expected: require('seal sha ' + p.name, sha(raw) == expected)
    require('unique seal members ' + p.name,
            len({r['path'] for r in s['members']}) == len(s['members']))
    if counts: require('seal closure ' + p.name,
                       (len(s['members']), sum(r['bytes'] for r in s['members'])) == counts)
    for m in s['members']:
        require('member ' + p.name + '/' + m['path'], row(m['path'], read(p / m['path'])) == m)
    return s

def custody():
    release = V / 'swift-semantic-adapter-root-review/guarded-snapshot-outer-parent-work-storage-frozen-release.json'
    require('root frozen release', sha(read(release)) == '0a28f10bee285dc3c150eea771013001a9ad90d0a70f03cb362badf1b35a36ab')
    seal(C, '7d7c6be167de0a7e20dbde2a50a5ea900a954a8e5e32262cf185411f1dc041b0', (44, 693873))
    for r in load(C / 'input-custody.json')['members']:
        require('input ' + r['path'], row(r['path'], read(ROOT / r['path'])) == r)
    seal(V / 'swift-guarded-snapshot-outer-parent-source',
         '3936c73a0f3558000834c92c3ade9822465069492740a954765cb775684bcb57', (39, 613222))
    seal(V / 'swift-guarded-snapshot-outer-parent-independent',
         '70bbf1cdd9a63494e63c4c7cbda22cd8e8c1cd8c961af36dee37d528b695902e', (42, 4142412))
    clarification = V / 'swift-semantic-adapter-root-review/guarded-snapshot-outer-parent-path-count-clarification.json'
    require('path clarification sha', sha(read(clarification)) == '7aee69fb830199f8f939c8a4ea7f79102e66a94c45d22659f8ea9b42335f11c0')
    acceptance = V / 'swift-semantic-adapter-root-review/guarded-snapshot-outer-parent-host-acceptance.json'
    require('outer source acceptance sha', sha(read(acceptance)) == 'a9ebe62c104b7fd0ef61b6216ead52885e4f8a62b39834b3ac57ee5493a05d0b')

def source():
    manifest = load(V / 'swift-guarded-snapshot-host-composition/source-manifest.json')
    expected = load(V / 'swift-guarded-snapshot-outer-parent-source/source-manifest.json')
    require('old tree146', len(manifest['members']) == 146 and sha(canonical(manifest['members'])) == OLD)
    old = {}
    for r in manifest['members']:
        p = V / 'swift-guarded-snapshot-host-composition/overlay/vm' / r['path']
        if not p.is_file(): p = V / 'swift-guarded-snapshot-funding-implementation/source/vm' / r['path']
        old[r['path']] = read(p)
        require('old source member ' + r['path'], row(r['path'], old[r['path']]) == r)
    new = dict(old)
    new[PROFILE] = read(V / 'swift-guarded-snapshot-outer-parent-source/overlay/vm' / PROFILE)
    snippet = read(V / 'swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs')
    addition = b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n' + snippet
    require('exact append, restore every old byte', old[PROFILE].endswith(b'\n}\n') and new[PROFILE] == old[PROFILE][:-2] + addition + b'}\n')
    records = [row(p, new[p]) for p in sorted(new, key=lambda p: tuple(p.split('/')))]
    require('new tree146', records == expected['members'] and sha(canonical(records)) == NEW)
    require('145 unchanged members', sum(old[p] == new[p] for p in old) == 145)
    return new, dict(old_tree=OLD, new_tree=NEW, members=146, exact_unchanged=145,
                    old_bytes_removed=0, addition_sha256=sha(addition),
                    all_old_bytes_restored=True, binary_correspondence=False)

def split_top(text, separator=','):
    stack = []; start = 0; result = []
    for i, c in enumerate(text):
        if c in '([{<': stack.append({'(': ')', '[': ']', '{': '}', '<': '>'}[c])
        elif c in ')]}>':
            if not stack or stack.pop() != c: raise ValueError('unbalanced type ' + text)
        elif c == separator and not stack:
            result.append(text[start:i].strip()); start = i + 1
    if stack: raise ValueError('unfinished type ' + text)
    result.append(text[start:].strip())
    return [x for x in result if x]

def matching(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{': depth += 1
        if text[i] == '}': depth -= 1
        if depth == 0: return i
    raise ValueError('unterminated declaration')

def norm(t):
    return re.sub(r'\b(?:[A-Za-z_]\w*::)+', '', t).replace("'static", "'_")

class Shapes:
    """Independent bounded structural declaration walk, not a Rust compiler.

    Used only for the declared logical scalar metric. References and specified
    std/resources are one abstract leaf; recursive/ambiguous unknowns fail.
    Native size always comes from retained compiler data below.
    """
    def __init__(self, files):
        self.definitions = collections.defaultdict(list); self.memo = {}; self.trace = {}; self.open = set()
        for path, data in files.items():
            if not path.endswith('.rs') or '/test' in path or path.endswith('_tests.rs'): continue
            text = re.sub(r'/\*.*?\*/', '', data.decode(), flags=re.S)
            text = '\n'.join(line.partition('//')[0] for line in text.splitlines())
            for m in re.finditer(r'\b(struct|enum)\s+(\w+)\s*([^;{]*)\{', text):
                if m[3].strip() and not m[3].lstrip().startswith('<'): continue
                end = matching(text, m.end()-1)
                self.definitions[m[2]].append((path, m[1], text[m.end():end], text[m.start():end+1]))
    def fields(self, text):
        fields = []
        for field in split_top(text):
            field = re.sub(r'#\[[^\]]*\]', '', field).strip()
            field = re.sub(r'^pub(?:\([^)]*\))?\s+', '', field)
            m = re.fullmatch(r'\w+\s*:\s*(.+)', field, re.S)
            if not m: raise ValueError('unparsed field ' + field)
            fields.append(m[1].strip())
        return fields
    def count(self, original):
        t = {'AError': 'SnapshotAdmissionErrorV1', 'Stop': 'SnapshotStopV1'}.get(original.strip(), original.strip())
        if original in self.memo: return self.memo[original]
        if t in self.open: raise ValueError('recursive by value ' + t)
        self.open.add(t)
        if t.startswith(('&', '*const ', '*mut ')): value = 1
        elif t in ('()', '!', 'u8', 'u16', 'u32', 'u64', 'u128', 'i8', 'i16', 'i32', 'i64', 'i128', 'usize', 'isize', 'bool', 'f32', 'f64', 'char', 'str'): value = 1
        elif t.startswith('['):
            element, length = split_top(t[1:-1], ';')
            value = self.count(element) * (6 if length == 'COMPONENT_COUNT_V1' else int(length.replace('_', '')))
        elif t.startswith('('): value = sum(self.count(x) for x in split_top(t[1:-1])) or 1
        else:
            head = t.partition('<')[0]; name = head.rsplit('::', 1)[-1]
            args = split_top(t[len(head)+1:-1]) if '<' in t else []
            if name in ('Option', 'Result', 'ControlFlow'):
                if len(args) != (1 if name == 'Option' else 2): raise ValueError('type arity')
                value = 1 + max([0] + [self.count(x) for x in args])
            elif name == 'Cell': value = self.count(args[0])
            elif name == 'Infallible': value = 0
            elif name in ('File', 'Error', 'Cancellation', 'Instant', 'Duration', 'Path', 'OpenOptions', 'Vec', 'String', 'Arc', 'Rc', 'Box', 'IntoIter', 'Enumerate'): value = 1
            else:
                ds = self.definitions[name]
                path = {'Refusal': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'Role': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'Resource': 'src/experimental_wasi/mod.rs'}.get(name)
                if path: ds = [d for d in ds if d[0] == path]
                if len(ds) != 1: raise ValueError('unknown/ambiguous declaration ' + t)
                path, kind, body, declaration = ds[0]
                if kind == 'struct':
                    fs = self.fields(body)
                    if name == 'PrepaidOwnedV1':
                        if len(args) != 2 or args[1].rsplit('::',1)[-1] != 'OwnedFixtureOutcomeV1': raise ValueError('unbound generic')
                        fs = [re.sub(r'\bT\b', args[1], x) for x in fs]
                    parts = [self.count(x) for x in fs]; value = sum(parts) or 1
                else:
                    fs = []
                    for variant in split_top(body):
                        variant = re.sub(r'#\[[^\]]*\]', '', variant).strip()
                        tail = re.fullmatch(r'\w+(.*)', variant, re.S)[1].strip()
                        if tail.startswith('('): types = split_top(tail[1:tail.rfind(')')])
                        elif tail.startswith('{'): types = self.fields(tail[1:tail.rfind('}')])
                        elif not tail or tail.startswith('='): types = []
                        else: raise ValueError('unparsed variant')
                        fs.append(types)
                    parts = [sum(self.count(x) for x in variant) for variant in fs]
                    value = 1 + max([0] + parts)
                self.trace[name] = dict(path=path, kind=kind, declaration_sha256=sha(declaration.encode()),
                                        fields_or_variants=fs, contributions=parts, scalar_leaves=value)
        self.open.remove(t); self.memo[original] = value
        return value

def function(text, name):
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith('fn ' + name + '('))
    end = next(i for i in range(start+1, len(lines)) if lines[i] == '}\n')
    return ''.join(lines[start:end+1])

def native_catalog(mir):
    raw = gzip.decompress(read(V / 'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz')).decode()
    require('old raw layout binding', sha(raw.encode()) == '6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a')
    observations = collections.defaultdict(set)
    for ty, size, align in re.findall(r'^print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes$', raw, re.M):
        observations[norm(ty)].add((int(size), int(align)))
    catalog = {t: next(iter(v))[0] for t, v in observations.items() if len({size for size, align in v}) == 1}
    # Reconstruct every prior exact concrete observation directly from the
    # retained expected-error diagnostics, including the actual queried type.
    prior = V / 'swift-guarded-snapshot-host-composition-independent'
    s = load(prior / 'seal.json')
    stderr = read(prior / 'commands/actual90-layout-queries/stderr')
    member = next(x for x in s['members'] if x['path'] == 'commands/actual90-layout-queries/stderr')
    require('retained exact90 diagnostics member', row(member['path'], stderr) == member)
    exact = []
    for diagnostic in stderr.decode().split('error[E0308]:')[1:]:
        q = re.search(r'const FINAL146_LAYOUT_(\d+):.*?size_of::<(.+)>\(\)', diagnostic)
        observed = re.search(r'found one with a size of (\d+)', diagnostic)
        require('concrete exact90 diagnostic', q is not None and observed is not None)
        exact.append(dict(index=int(q[1]), concrete=q[2], bytes=int(observed[1])))
        catalog[norm(q[2])] = int(observed[1])
    summary = load(prior / 'fresh-layout-results.json')['queries']
    require('all90 concrete diagnostics reconstructed', len(exact) == 90 and exact == [{k:r[k] for k in ('index','concrete','bytes')} for r in summary])
    # Actual MIR argument array dimensions, bound to corresponding inert source
    # query signatures, independently recover the44 outer size/alignment values.
    dims = {}; outer = V / 'swift-guarded-snapshot-outer-parent-independent'
    for suffix, name in [('query-layout.inc.rs', 'outer_parent_layout_query_v1'), ('query-account-layout.inc.rs', 'outer_parent_account_layout_query_v1')]:
        signature = function(mir, name).splitlines()[0]
        values = [int(x) for x in re.findall(r'_\d+: \[u8; (\d+)\]', signature)]
        source_query = read(outer / suffix).decode()
        qs = re.findall(r'_(\w+): \[u8; std::mem::(size|align)_of::<(.+)>\(\)\]', source_query)
        require('query exact arity ' + name, len(qs) == len(values))
        for (label, operation, ty), value in zip(qs, values):
            dims[label] = value
            if operation == 'size': catalog[norm(ty)] = value
    require('all44 direct observations', len(dims) == 44 and dims == {r['query']:r['observed'] for r in load(outer / 'commands/compiler-metadata-mir/layouts.json')['rows']})
    # This intentionally failing single query adds only its two layout facts.
    diag = read(C / 'commands/result-layout/stderr').decode()
    sizes = [int(x) for x in re.findall(r'found one with a size of (\d+)', diag)]
    require('single query2E0308 dims8/8', sizes == [8,8] and diag.count('error[E0308]') == 2)
    receipt = load(C / 'commands/result-layout/receipt.json')
    require('expected diagnostic terminal, not production pass', receipt['exit_code'] == 1 and receipt['compiler_invocations'] == 1 and receipt['expected_diagnostic_exit_observed'] and not receipt['codegen_or_executable'] and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['owned_scratch_removed'])
    catalog['Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>'] = sizes[0]
    catalog.update({'()':0, '!':0, 'bool':1, 'isize':8})
    return catalog, dict(exact90=exact, direct44=dims, single_diagnostic_sizes=sizes,
                         normalized_conflicts={t: sorted(v) for t,v in observations.items() if len({x[0] for x in v}) > 1})

def extent(original, catalog):
    t = norm(original)
    if t in catalog: return catalog[t]
    if t.startswith('&'):
        pointee = re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?", '', t)
        if pointee in ('str', 'Path') or (pointee.startswith('[') and ';' not in pointee): raise ValueError('unsized reference needs direct evidence')
        return 8
    if t.startswith('('):
        fields = split_top(t[1:-1])
        if not all(x.startswith('&') for x in fields): raise ValueError('unobserved tuple')
        return sum(extent(x, catalog) for x in fields)
    if t.startswith('['):
        ty, count = split_top(t[1:-1], ';'); return extent(ty, catalog) * int(count)
    raise ValueError('missing concrete extent ' + t)

def paths(blocks):
    pending = [('bb0', ())]; result = []
    while pending:
        block, prior = pending.pop()
        if block in prior: raise ValueError('cycle')
        path = prior + (block,); last = blocks[block][-1]
        successors = sorted(set(re.findall(r'\bbb\d+\b', last)))
        if 'unwind continue' in last: result.append((path, 'unwind-continue'))
        if 'unwind terminate' in last: result.append((path, 'terminate-cleanup'))
        if not successors:
            known = {'return;':'return', 'resume;':'resume', 'unreachable;':'unreachable'}
            if last not in known: raise ValueError('unknown terminal')
            result.append((path, known[last]))
        pending.extend((successor, path) for successor in successors)
    return set(result)

def reconstruct(files):
    raw = read(V / 'swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/outer-and-query.mir').decode()
    complete = gzip.decompress(read(V / 'swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/query.mir.gz')).decode()
    for name in NAMES: require('exact retained full MIR ' + name, function(raw, name) == function(complete, name))
    catalog, native = native_catalog(raw); shapes = Shapes(files)
    producer = {f['name']: f for f in load(C / 'operation-ledger.json')['functions']}
    prior_paths = load(V / 'swift-guarded-snapshot-outer-parent-independent/mir-paths.json')
    result = []; slots = []; path_output = {}; occurrence = 0; ends = 0
    for name in NAMES:
        body = function(raw, name); head = body.splitlines()[0]; a = head.index('('); z = head.rindex(') ->')
        params = []
        for parameter in split_top(head[a+1:z]):
            key, ty = parameter.split(': ',1); params.append((key, ty, 'parameter'))
        declared = [(m[1],m[2], 'return' if m[1] == '_0' else 'local') for m in re.finditer(r'^\s+let(?: mut)? (_\d+): (.*?);\s*(?://.*)?$', body, re.M)]
        roles = {}
        for key, ty, kind in params + declared:
            if key in roles: raise ValueError('duplicate local')
            pointee = re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?", '', ty) if ty.startswith('&') else None
            roles[key] = dict(local=key, type=ty, kind=kind, bytes=extent(ty,catalog),
                              scalar_leaves=shapes.count(ty), pointee_type=pointee,
                              pointee_bytes=extent(pointee,catalog) if pointee else 0,
                              pointee_scalar_leaves=shapes.count(pointee) if pointee else 0)
        blocks = {}; current = None
        for line in body.splitlines():
            text = line.partition('//')[0].rstrip()
            start = re.fullmatch(r'    (bb\d+)(?: \(cleanup\))?: \{', text)
            if start: current = start[1]; blocks[current] = []
            elif text == '    }': current = None
            elif current and text.strip(): blocks[current].append(text.strip())
        def weights(keys):
            return (sum(roles[k]['scalar_leaves'] + roles[k]['pointee_scalar_leaves'] for k in keys),
                    sum(roles[k]['bytes'] + roles[k]['pointee_bytes'] for k in keys))
        def price(code):
            mentions = re.findall(r'\b_\d+\b', code)
            if any(x not in roles for x in mentions): raise ValueError('unknown local')
            constants = []
            for constant in re.finditer(r'\bconst\s+', code):
                value = re.match(r'(?:\d+_(?:u64|usize|isize)|true\b|false\b|\(\))', code[constant.end():])
                if value is None: raise ValueError('unpriced constant')
                token = value[0]; constants.append(0 if token == '()' else 1 if token in ('true','false') else 8)
            scalar, native_bytes = weights(mentions)
            if code == 'return;':
                return_scalar, return_native = weights(['_0']); scalar += return_scalar; native_bytes += return_native
            source = 2 + sum(code.count(c) for c in '()[].*&') + len(re.findall(r'\bas\b',code)) + 2*(scalar+len(constants))
            native_bytes = 2*(native_bytes+sum(constants))
            return dict(code=code, source=source, native=native_bytes, total=source+native_bytes)
        ledger = {block:[price(code) for code in codes] for block,codes in blocks.items()}
        entry_scalar, entry_native = weights([k for k,t,kind in params])
        entry = 2 + 2*entry_scalar + 2*entry_native
        surface = entry + sum(x['total'] for b in ledger.values() for x in b)
        finish = sum(2 + 2*r['scalar_leaves'] + 2*r['bytes'] for r in roles.values())
        ps = paths(blocks); path_output[name] = [dict(blocks=list(p),terminal=t) for p,t in sorted(ps)]
        require('exact terminal sets ' + name, ps == {(tuple(x['blocks']),x['terminal']) for x in prior_paths[name]})
        p = producer[name]
        require('body binding ' + name, p['MIR_sha256'] == sha(body.encode()))
        require('all typed roles ' + name, [{k:r[k] for k in roles['_0']} for r in p['roles']] == list(roles.values()))
        require('written block/operation sets ' + name, {b:[r['code'] for r in rows['rows']] for b,rows in p['blocks'].items()} == blocks)
        for b, rows in ledger.items():
            require('all per-operation prices ' + name + '/' + b,
                    [(x['source'],x['native'],x['total']) for x in rows] == [(x['source_action_units'],x['native_sized_occurrence_bytes'],x['combined']) for x in p['blocks'][b]['rows']])
        require('all-block path domination ' + name, all(entry + sum(x['total'] for b in path for x in ledger[b]) <= surface for path,terminal in ps))
        slots.extend(dict(id=name+':'+key, **r) for key,r in roles.items())
        occurrence += surface; ends += finish
        result.append(dict(name=name, roles=len(roles), operations=sum(map(len,blocks.values())),
                           inline=sum(r['bytes'] for r in roles.values()), occurrence=surface,
                           finite_ends=finish, work=surface+finish, terminal_paths=len(ps),
                           graph_leaf_paths=sum(1 for path,terminal in ps if terminal not in ('unwind-continue','terminate-cleanup'))))
        if name == 'consume_outer_request_v1':
            counts = []
            for path,terminal in ps:
                text = '\n'.join(code for b in path for code in blocks[b])
                calls = {call:len(re.findall(r'= .*?\b'+call+r'\(',text)) for call in ('usage_v1','borrow_original_diagnostics_once_v1','run_one_fixture_v1','destroy_returned_fixture_v1','release_after_retirement_v1')}
                require('route sole entry/inspection/destruction/release ' + ','.join(path), all(calls[k] <= 1 for k in calls if k != 'usage_v1') and calls['usage_v1'] <= 3)
                if calls['release_after_retirement_v1']:
                    require('release follows actual destruction call ' + ','.join(path), text.index('destroy_returned_fixture_v1(') < text.index('release_after_retirement_v1('))
                counts.append(calls)
            require('call conditional maxima', {k:max(c[k] for c in counts) for k in counts[0]} == dict(usage_v1=3,borrow_original_diagnostics_once_v1=1,run_one_fixture_v1=1,destroy_returned_fixture_v1=1,release_after_retirement_v1=1))
    final = 2 + 2*shapes.count('OuterResultV1') + 2*extent('OuterResultV1',catalog)
    totals = dict(roles=len(slots), operations=sum(x['operations'] for x in result), occurrence=occurrence,
                  finite_ends=ends, separate_result_end=final, work=occurrence+ends+final,
                  inline=sum(r['bytes'] for r in slots), paths=sum(x['terminal_paths'] for x in result),
                  graph_leaf_paths=sum(x['graph_leaf_paths'] for x in result))
    require('independent exact totals', totals == dict(roles=130,operations=386,occurrence=2571714,finite_ends=134270,separate_result_end=186,work=2706170,inline=56414,paths=56,graph_leaf_paths=43))
    out('native-layout-reconstruction.json', native); out('scalar-reconstruction.json',shapes.trace)
    out('role-reconstruction.json',slots); out('terminal-paths.json',path_output)
    return dict(functions=result, totals=totals)

def storage_and_work(reconstruction):
    phase = load(C / 'phase-roster.json')
    roles = load(HERE / 'role-reconstruction.json')
    require('complete separate role identity roster', {r['id'] for r in roles} == {r['id'] for r in phase['all_new_roles']})
    for r in phase['all_new_roles']:
        actual = next(x for x in roles if x['id'] == r['id'])
        require('P0 lifetime retains ' + r['id'], r['bytes'] == actual['bytes'] and r['funded_by'] == 'P0' and r['reserved_first'] == 'P0_BEFORE_BINDING_POLICY_QUOTE_ACCOUNT_ENTRY' and r['reserved_last'] == 'P0_AFTER_FINAL_RESULT_CONSUMPTION')
    require('full new role overlap each phase', set(phase['new_slot_reserved_bytes_each_phase'].values()) == {sum(r['bytes'] for r in roles)})
    require('no sharing/move/refund credit', phase['move_alias_sharing_refund_credit'] is False and phase['compiler_stack_or_physical_liveness_claim'] is False)
    inv = load(V / 'swift-guarded-snapshot-host-storage-composition/inline-inventory.json')
    subtotals = dict(P0=sum(r['bytes'] for r in inv['caller_slots'] if r['phase'].startswith('P0')),
                     child=sum(r['bytes'] for r in inv['caller_slots'] if not r['phase'].startswith('P0')),
                     leaf=sum(r['bytes'] for r in inv['leaf_slots']),
                     loader=sum(r['known_bytes'] for r in inv['loader_slots']))
    require('old source inline rosters retained', subtotals == dict(P0=234375,child=76696,leaf=320766,loader=644008))
    binding = 512 + 5*16 + 12*48
    fixed_p0 = subtotals['P0'] + reconstruction['totals']['inline'] + binding + 80
    account = 2628088 + 194231*1 + 1039*3
    prior_fixed = 895084428322997895 + 55381
    fixed_work = prior_fixed + 194231*1 + 1039*3 + reconstruction['totals']['work']
    candidate = load(C / 'candidate.json')
    require('complete immutable binding inline', binding == 1168)
    require('new fixed P0 independently summed', fixed_p0 == candidate['P0_fixed_inline_before_external_root_backing'] == 292037)
    require('account fixed included only once', account == candidate['conditional_account_surface_once'] == 2825436)
    require('P4 supplement included only once', prior_fixed == 895084428323053276)
    require('whole fixed new surface and I/U only', fixed_work == candidate['conditional_whole_work_fixed_with_new_outer'] == 895084428325956794)
    require('ten mandatory work obligations', candidate['inherited_remaining_work_terms'] == dict(L_str=67424,P0_dynamic_backing=1,P0_fixture_binding=1,P0_root_route=1,native_error_request=1,**{'native_open_request_'+str(i):1 for i in range(5)}))
    require('no selection/5080/production grant', not candidate['L_str5080_selected'] and not candidate['actual_immutable_binding_selected'] and not candidate['whole_root_policy_or_funding_selected'] and candidate['actual_execution_I_U_entry_release'] == dict(I=0,U=0,entry=0,release=0))
    return dict(old_inline_subtotals=subtotals,binding_inline=binding,fixed_P0=fixed_p0,account=account,
                inherited_fixed=prior_fixed,whole_fixed=fixed_work,
                P0_formula='292037 + future_root_inline + future_root_owned_backing + sum(12 identity backing) + sum(5 native Path backing) + sum(5 separately retained byte body backing) + original diagnostic backing',
                child_formula={'P1_setup':'59695+561+6*File_backing+sum(5 open temporary)',
                    'P1_loader':'644008+build+session+max(executable,source+1947+1000000+65536)+loader_native+executable_open',
                    'P2_arguments':'520+24','P3_shell':320766-95850,
                    'P4_leaf':15920+95850+1899541+54976,
                    'P5_returned':'error_owner_count*error_backing_each+full_payload_destructor_temporaries'},
                no_new_error_owners_from_shared_view=True,old_payload_and_carrier_charge_retained=True,
                no_alias_move_or_refund_credit=True,source_rebind_only=True)

def main():
    custody(); files,rebind = source(); reconstruction = reconstruct(files)
    arithmetic = storage_and_work(reconstruction)
    out('source-rebind-review.json', rebind)
    out('arithmetic-review.json', arithmetic)
    out('reconstruction.json', reconstruction)
    out('assertions.json',dict(count=len(checks),passed=checks))
    out('input-custody.json',dict(schema=1,members=sorted(inputs.values(),key=lambda x:x['path'])))
    print(json.dumps(dict(passed=True,assertions=len(checks),totals=reconstruction['totals'])))
if __name__ == '__main__': main()
