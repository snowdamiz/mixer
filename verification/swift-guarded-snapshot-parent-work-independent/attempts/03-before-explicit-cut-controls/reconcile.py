#!/usr/bin/env python3
"""Independent, data-only review; never imports or executes producer code.

Only this packet is writable. Compiler diagnostics and MIR are frozen inputs,
not a compiler invocation or an executable authorization.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PROPOSAL = ROOT / 'verification/swift-guarded-snapshot-parent-work'
ACCOUNT = ROOT / 'verification/swift-guarded-snapshot-host-account-entry'
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
SOURCE = '5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
MAX = (1 << 64) - 1
checks = []
inputs = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(path):
    path = Path(path)
    b = path.read_bytes()
    inputs[path.relative_to(ROOT).as_posix()] = {'bytes': len(b), 'sha256': sha(b)}
    return b


def load(path):
    return json.loads(read(path))


def require(label, ok):
    if not ok:
        raise AssertionError(label)
    checks.append(label)


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def split(text, separator=','):
    """Independent bounded type-field scanner; no source execution."""
    stack, start, answer = [], 0, []
    pairs = {'(': ')', '[': ']', '{': '}', '<': '>'}
    for i, ch in enumerate(text):
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in ')]}>':
            if not stack or stack.pop() != ch:
                raise ValueError('unbalanced field/type: ' + text)
        elif ch == separator and not stack:
            answer.append(text[start:i].strip())
            start = i + 1
    if stack:
        raise ValueError('unfinished type: ' + text)
    answer.append(text[start:].strip())
    return [p for p in answer if p]


def close_brace(text, start):
    depth = 0
    for i in range(start, len(text)):
        depth += (text[i] == '{') - (text[i] == '}')
        if depth == 0:
            return i
    raise ValueError('unfinished declaration')


def uncomment(text):
    # Selected bounded data declarations have no comment delimiters in literals.
    return '\n'.join(x.split('//', 1)[0] for x in re.sub(r'/\*.*?\*/', '', text, flags=re.S).splitlines())


def fields(body):
    result = []
    for f in split(body):
        f = re.sub(r'#\[[^\]]*\]', '', f).strip()
        f = re.sub(r'^pub(?:\([^)]*\))?\s+', '', f)
        m = re.fullmatch(r'\w+\s*:\s*(.+)', f, re.S)
        if not m:
            raise ValueError('unrecognized field: ' + f)
        result.append(m[1].strip())
    return result


def short(ty):
    return ty.replace('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::', '').replace('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::', '').replace('std::', '')


class SourceShapes:
    def __init__(self, source):
        self.source = source
        self.defs = collections.defaultdict(list)
        self.cache, self.used, self.active = {}, {}, []
        for path, raw in source.items():
            if not path.endswith('.rs') or '/test' in path or path.endswith('_tests.rs'):
                continue
            txt = uncomment(raw.decode())
            for m in re.finditer(r'\b(struct|enum)\s+(\w+)\s*([^;{]*)\{', txt):
                if m[3].strip() and not m[3].strip().startswith('<'):
                    continue
                end = close_brace(txt, m.end() - 1)
                self.defs[m[2]].append((path, m[1], txt[m.end():end], txt[m.start():end+1]))

    def n(self, ty):
        original = ty
        ty = {'AError': 'SnapshotAdmissionErrorV1', 'Stop': 'SnapshotStopV1'}.get(ty.strip(), ty.strip())
        if original in self.cache:
            return self.cache[original]
        if ty in self.active:
            raise ValueError('recursive by-value type')
        self.active.append(ty)
        if ty.startswith(('&', '*const ', '*mut ')):
            n = 1
        elif ty in ('()', '!', 'u8', 'u16', 'u32', 'u64', 'u128', 'i8', 'i16', 'i32', 'i64', 'i128', 'usize', 'isize', 'bool', 'f32', 'f64', 'char', 'str'):
            n = 1
        elif ty.startswith('{closure@') or ty == 'impl FnOnce() -> T':
            n = 1  # Source-audited exact fixture capture; no generic claim.
        elif ty.startswith('['):
            element, number = split(ty[1:-1], ';')
            count = 6 if number == 'COMPONENT_COUNT_V1' else int(number.replace('_', ''))
            if count < 0:
                raise ValueError('negative array')
            n = count * self.n(element)
        elif ty.startswith('(') and ty.endswith(')'):
            n = sum(map(self.n, split(ty[1:-1]))) or 1
        else:
            head = ty.split('<', 1)[0]
            name = head.rsplit('::', 1)[-1]
            args = split(ty[len(head)+1:-1]) if '<' in ty and ty.endswith('>') else []
            if name in ('Option', 'Result', 'ControlFlow'):
                if len(args) != (1 if name == 'Option' else 2):
                    raise ValueError('arity')
                n = 1 + max([0] + [self.n(x) for x in args])
            elif name == 'Infallible':
                n = 0
            elif name == 'Cell':
                n = self.n(args[0])
            elif name in ('File', 'Error', 'Cancellation', 'Instant', 'Duration', 'Path', 'OpenOptions', 'Vec', 'String', 'Arc', 'Rc', 'Box', 'IntoIter', 'Enumerate'):
                n = 1  # Explicit abstract std/resource boundary, no backing price.
            else:
                ds = self.defs[name]
                route = {'Refusal': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'Role': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'Resource': 'src/experimental_wasi/mod.rs'}.get(name)
                if route:
                    ds = [d for d in ds if d[0] == route]
                if len(ds) != 1:
                    raise ValueError('unknown or ambiguous source type: ' + ty)
                path, kind, body, declaration = ds[0]
                detail = {'path': path, 'kind': kind, 'declaration_sha256': sha(declaration.encode())}
                if kind == 'struct':
                    fs = fields(body)
                    if name == 'PrepaidOwnedV1':
                        if len(args) != 2 or args[1].rsplit('::', 1)[-1] != 'OwnedFixtureOutcomeV1':
                            raise ValueError('unbound generic payload')
                        fs = [re.sub(r'\bT\b', args[1], x) for x in fs]
                    n = sum(map(self.n, fs)) or 1
                    detail['fields'] = fs
                else:
                    variants = []
                    for raw in split(body):
                        raw = re.sub(r'#\[[^\]]*\]', '', raw).strip()
                        m = re.fullmatch(r'(\w+)(.*)', raw, re.S)
                        tail = m[2].strip()
                        if tail.startswith('('):
                            fs = split(tail[1:tail.rfind(')')])
                        elif tail.startswith('{'):
                            fs = fields(tail[1:tail.rfind('}')])
                        elif not tail or tail.startswith('='):
                            fs = []
                        else:
                            raise ValueError('unknown variant')
                        variants.append({'name': m[1], 'fields': fs, 'payload_leaves': sum(map(self.n, fs))})
                    n = 1 + max([0] + [v['payload_leaves'] for v in variants])
                    detail['variants'] = variants
                detail['scalar_leaves'] = n
                self.used[name] = detail
        self.active.pop()
        self.cache[original] = n
        return n


def mir_functions(text):
    # Independent whole-function slicing keyed by column-zero declarations.
    starts = [m.start() for m in re.finditer(r'^fn ', text, flags=re.M)]
    answer = []
    for a, b in zip(starts, starts[1:] + [len(text)]):
        segment = text[a:b]
        final = re.search(r'^}\n', segment, flags=re.M)
        if not final or segment[final.end():].strip():
            raise ValueError('unparsed MIR tail')
        answer.append(segment[:final.end()])
    return answer


def mir_blocks(body):
    answer, current = {}, None
    for no, line in enumerate(body.splitlines(), 1):
        line = line.split('//', 1)[0].rstrip()
        m = re.fullmatch(r'    (bb\d+)( \(cleanup\))?: \{', line)
        if m:
            current = m[1]
            answer[current] = {'cleanup': bool(m[2]), 'lines': []}
        elif line == '    }':
            current = None
        elif current is not None and line.strip():
            answer[current]['lines'].append((no, line.strip()))
    return answer


def call_kind(code, function):
    if ' -> [' not in code or code.startswith('switchInt('):
        return None
    if code.startswith('drop('):
        return 'std_iterator_drop' if function == 'checked_components_v1' else 'wrapper_drop_glue'
    expression = code.split(' = ', 1)[1].split(' -> [', 1)[0]
    if expression.startswith('<impl FnOnce() -> T as FnOnce<()>>::call_once'):
        return 'p0:fixture_dispatch_closure'
    for name in ('selected_whole_quote_v1', 'reserve_whole_v1', 'dispatch_v1', 'destroy_owned_v1', 'release_destroyed_v1'):
        if re.search(r'\b' + name + r'(?:::|\()', expression):
            return 'p0:' + name
    if expression.startswith('run_prepaid_fixture_v1('):
        return 'required:P1_P5_callback_body'
    if expression.startswith('std::mem::drop::<T>'):
        return 'required:P5_actual_payload_destruction'
    if expression.startswith('std::mem::drop::<PrepaidOwnedV1'):
        return 'wrapper_drop_glue'
    prefixes = [
        ('<[CostV1; 6] as IntoIterator>::into_iter', 'array_into_iter'),
        ('<std::array::IntoIter<CostV1, 6> as Iterator>::enumerate', 'enumerate_constructor'),
        ('<Enumerate<std::array::IntoIter<CostV1, 6>> as IntoIterator>::into_iter', 'enumerate_into_iter'),
        ('<Enumerate<std::array::IntoIter<CostV1, 6>> as Iterator>::next', 'enumerate_next'),
        ('core::num::<impl u64>::checked_add', 'checked_add_u64'),
        ('core::num::<impl u64>::checked_sub', 'checked_sub_u64'),
        ('Option::<u64>::ok_or::<RefusalV1>', 'option_ok_or'),
        ('Cell::<UsageV1>::new', 'cell_new'), ('Cell::<UsageV1>::get', 'cell_get'),
        ('Cell::<UsageV1>::set', 'cell_set'), ('<u64 as Ord>::max', 'u64_max'),
        ('Option::<T>::as_ref', 'option_as_ref'), ('Option::<T>::take', 'option_take_payload'),
        ("Option::<ReservationV1<'_>>::take", 'option_take_reservation'),
    ]
    for prefix, meaning in prefixes:
        if expression.startswith(prefix):
            return 'abstract_std:' + meaning
    if expression.startswith('<Result<') and ' as Try>::branch(' in expression:
        return 'abstract_std:result_try_branch'
    if expression.startswith('<Result<') and ' as FromResidual<' in expression and '>>::from_residual(' in expression:
        return 'abstract_std:result_from_residual'
    raise ValueError('unknown call: ' + expression)


def enumerate_paths(identity, graph):
    """Independent DFS computes actual graph maxima; no ledger occurrence caps."""
    terminal = []
    todo = [('bb0', [], 0)]
    while todo:
        bid, past, yielded = todo.pop()
        path = past + [bid]
        if len(path) > 300:
            raise ValueError('unbounded graph')
        if identity == 'checked_components_v1' and bid == 'bb7':
            yielded += 1
        if yielded > 6:
            raise ValueError('more than six array yields')
        if identity != 'checked_components_v1' and bid in past:
            raise ValueError('unexpected cycle')
        final = graph[bid]['lines'][-1][1]
        nexts = sorted(set(re.findall(r'\bbb\d+\b', final)))
        if identity == 'checked_components_v1' and bid == 'bb5' and yielded == 6:
            nexts.remove('bb7')
        for n in nexts:
            todo.append((n, path, yielded))
        if 'unwind continue' in final:
            terminal.append(('unwind-continue', path))
        if 'unwind terminate' in final:
            terminal.append(('unwind-terminate', path))
        if not nexts:
            kind = {'return;': 'return', 'resume;': 'resume', 'unreachable;': 'unreachable'}[final]
            terminal.append((kind, path))
    return terminal


def audit():
    release_path = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-parent-work-independent-release.json'
    require('root release hash', sha(read(release_path)) == '9c44a8d6b637aebc00315f9c673fc8fa16daf3d4503d4c193e01b076e3507a3f')
    require('producer seal hash', sha(read(PROPOSAL / 'seal.json')) == 'bc9426ad22da41b354094b1778685bb7bf834e03fc22101272c2f08bf5d2b857')
    sealed = load(PROPOSAL / 'seal.json')
    require('producer closure counts', (len(sealed['members']), sum(m['bytes'] for m in sealed['members'])) == (52, 1665166))
    for member in sealed['members']:
        data = read(PROPOSAL / member['path'])
        require('producer sealed member ' + member['path'], len(data) == member['bytes'] and sha(data) == member['sha256'])
    declared = load(PROPOSAL / 'input-custody.json')
    for path, claim in declared['files'].items():
        data = read(ROOT / path)
        require('producer input custody ' + path, {'bytes': len(data), 'sha256': sha(data)} == claim)
    manifest = load(ACCOUNT / 'source-manifest.json')
    sources = {}
    for member in manifest['members']:
        path = member['path']
        if path == 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs':
            data = read(ACCOUNT / 'host_account.rs')
        else:
            data = read(BASE / path)
            if path == 'src/experimental_swift_reactor/cache/initial_profile_v1.rs':
                data += b'\n\n' + read(ROOT / 'verification/swift-guarded-snapshot-bootstrap-host-boundary/driver.inc.rs') + b'\n\n' + read(ACCOUNT / 'entry.inc.rs')
        require('source member ' + path, {'path': path, 'bytes': len(data), 'sha256': sha(data)} == member)
        sources[path] = data
    require('source145 manifest digest', len(sources) == 145 and sha(canon(manifest['members'])) == manifest['source_tree_sha256'] == SOURCE)

    inventory = load(ACCOUNT / 'caller-inventory.json')
    ledger = load(PROPOSAL / 'operation-ledger.json')
    summary = load(PROPOSAL / 'summary.json')
    shapes_claim = load(PROPOSAL / 'scalar-shapes.json')
    layout = read(ACCOUNT / 'compiler-commands/actual-type-layout-queries/stderr').decode()
    # Parse each intentionally failing size-query diagnostic, not its summary.
    diagnostic_sizes = {}
    for chunk in layout.split('error[E0308]: mismatched types')[1:]:
        q = re.search(r'const ENTRY_LAYOUT_\d+:.*std::mem::size_of::<(.+)>\(\)\];', chunk)
        value = re.search(r'found one with a size of (\d+)', chunk)
        if q and value:
            diagnostic_sizes[q[1]] = int(value[1])
    require('ninety diagnostic queries with eighty-nine unique spellings', len(layout.split('error[E0308]: mismatched types'))-1 == inventory['actual_type_queries'] == 90 and len(diagnostic_sizes) == 89)
    require('only unit is absent from intentional mismatch diagnostics', set(inventory['actual_type_sizes']) - set(diagnostic_sizes) == {'()'} and inventory['actual_type_sizes']['()'] == 0)
    for ty, extent in diagnostic_sizes.items():
        require('raw diagnostic native size ' + ty, inventory['actual_type_sizes'][ty] == extent)
    sizes = {short(k): v for k, v in inventory['actual_type_sizes'].items()}
    actual_shapes = SourceShapes(sources)
    mir = mir_functions(read(ACCOUNT / 'entry-and-account.mir').decode())
    require('nineteen whole MIR functions', len(mir) == len(inventory['functions']) == 19)
    p0 = [(body, old) for body, old in zip(mir, inventory['functions']) if old['phase'] == 'P0-pre-existing-parent-account-bookkeeping']
    require('fifteen P0 functions selected from accepted inventory', len(p0) == len(ledger['functions']) == 15)
    totals, paths_report, call_report = {}, {}, {}
    line_count = reference_occurrences = aggregate_occurrences = 0
    body_map = {}
    for (body, old), f in zip(p0, ledger['functions']):
        fid = f['id']
        body_map[fid] = body
        require('whole MIR digest ' + fid, sha(body.encode()) == old['sha256'] == f['MIR_sha256'])
        require('whole MIR header ' + fid, body.splitlines()[0] == old['header'] == f['header'])
        require('all accepted roles retained ' + fid, set(f['roles']) == {x['local'] for x in old['roles']} and all(r == {n: f['roles'][r['local']][n] for n in r} for r in old['roles']))
        graph = mir_blocks(body)
        require('all written blocks retained ' + fid, set(graph) == set(f['blocks']))
        role_cost = {}
        for local, role in f['roles'].items():
            ty = role['concrete_production_type']
            n = actual_shapes.n(ty)
            pointed = re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?", '', ty) if ty.startswith('&') else None
            pn = actual_shapes.n(pointed) if pointed else 0
            pb = sizes[short(pointed)] if pointed else 0
            require('concrete role leaf and pointee surcharge ' + fid + local, (n, pn, pb, pointed) == (role['scalar_leaves'], role['pointee_scalar_leaves'], role['pointee_bytes'], role['pointee_type']))
            extent = inventory['actual_type_sizes'].get(ty)
            if extent is None:
                extent = inventory['actual_compiler_anonymous_types'][ty]['bytes']
            require('native base size retained ' + fid + local, role['bytes'] == extent)
            role_cost[local] = (2 * (n + pn), 2 * (role['bytes'] + pb))
        block_cost, weighted_calls = {}, collections.Counter()
        for bid, bb in graph.items():
            saved = f['blocks'][bid]
            require('block cleanup flag ' + fid + bid, bb['cleanup'] == saved['cleanup'])
            require('all written operations retained ' + fid + bid, bb['lines'] == [(x['body_line'], x['code']) for x in saved['lines']])
            source_cost = native_cost = 0
            for (number, code), row in zip(bb['lines'], saved['lines']):
                line_count += 1
                locals_ = re.findall(r'\b_\d+\b', code)
                require('all occurrence locals measured ' + fid + str(number), set(locals_) <= set(role_cost))
                constants = []
                for m in re.finditer(r'\bconst\s+', code):
                    token = re.match(r'(?:\d+_(?:u64|usize)|true\b|false\b|\(\))', code[m.end():])
                    require('explicit known constant ' + fid + str(number), token is not None)
                    value = token[0]
                    constants.append({'text': value, 'bytes': 0 if value == '()' else 1 if value in ('true', 'false') else 8, 'scalar_leaves': 1})
                base = 2 + sum(code.count(x) for x in '()[].*&') + len(re.findall(r'\bas\b', code))
                scalar = sum(role_cost[x][0] for x in locals_) + 2 * len(constants)
                native = sum(role_cost[x][1] for x in locals_) + 2 * sum(x['bytes'] for x in constants)
                if code == 'return;':
                    scalar += role_cost['_0'][0]
                    native += role_cost['_0'][1]
                cut = call_kind(code, fid)
                require('recomputed operation allowance ' + fid + str(number), (base, scalar, base+scalar, native, locals_, constants, cut) == (row['base_action_units'], row['scalar_fetch_store_units'], row['source_action_units'], row['native_sized_occurrence_bytes'], row['local_mentions'], row['constants'], row['call_cut']))
                source_cost += base + scalar
                native_cost += native
                if cut:
                    weighted_calls[cut] += saved['occurrence_bound']
                reference_occurrences += sum(bool(f['roles'][x]['pointee_type']) for x in locals_)
                aggregate_occurrences += sum(f['roles'][x]['scalar_leaves'] > 1 for x in locals_)
            block_cost[bid] = source_cost, native_cost
            require('block cost totals ' + fid + bid, (source_cost, native_cost) == (saved['source_action_units'], saved['native_sized_occurrence_bytes']))
        entry_s = 2 + sum(role_cost[k][0] for k, r in f['roles'].items() if r['kind'] == 'parameter')
        entry_b = sum(role_cost[k][1] for k, r in f['roles'].items() if r['kind'] == 'parameter')
        require('entry parameter dimensions ' + fid, (entry_s, entry_b) == (f['entry_source_action_units'], f['entry_native_sized_occurrence_bytes']))
        sum_s = entry_s + sum(f['blocks'][b]['occurrence_bound'] * value[0] for b, value in block_cost.items())
        sum_b = entry_b + sum(f['blocks'][b]['occurrence_bound'] * value[1] for b, value in block_cost.items())
        totals[fid] = {'source': sum_s, 'native': sum_b, 'combined': sum_s + sum_b}
        require('function cost dimensions ' + fid, (sum_s, sum_b, sum_s+sum_b) == (f['source_action_units_per_invocation'], f['native_sized_occurrence_bytes_per_invocation'], f['combined_surface_units_per_invocation']))
        require('weighted direct call union ' + fid, dict(weighted_calls) == f['calls_per_invocation_bound'])
        direct_paths = enumerate_paths(fid, graph)
        maxima = collections.Counter()
        max_s = max_b = 0
        max_calls = collections.Counter()
        for kind, path in direct_paths:
            counts = collections.Counter(path)
            maxima |= counts
            max_s = max(max_s, sum(block_cost[b][0] for b in path))
            max_b = max(max_b, sum(block_cost[b][1] for b in path))
            c = collections.Counter(call_kind(graph[b]['lines'][-1][1], fid) for b in path)
            c.pop(None, None)
            max_calls |= c
            require('complete path covered ' + fid + ':' + str(len(checks)), entry_s + sum(block_cost[b][0] for b in path) <= sum_s and entry_b + sum(block_cost[b][1] for b in path) <= sum_b)
        for b, n in maxima.items():
            require('independent path occurrence max ' + fid + b, n <= f['blocks'][b]['occurrence_bound'])
        paths_report[fid] = {'terminal_paths': len(direct_paths), 'terminal_kinds': dict(collections.Counter(k for k, p in direct_paths)), 'max_block_occurrences': dict(maxima), 'max_path_source_excluding_entry': max_s, 'max_path_native_excluding_entry': max_b, 'max_calls_on_one_path': dict(max_calls)}
        call_report[fid] = dict(weighted_calls)
    require('independent transitive fifty-four data declarations', len(actual_shapes.used) == 54 and actual_shapes.used == shapes_claim['definitions'])
    require('actual payload and wrapper scalar leaves', actual_shapes.n('OwnedFixtureOutcomeV1') == 2556 and actual_shapes.n("PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>") == 2560)
    require('independent path count 273', sum(x['terminal_paths'] for x in paths_report.values()) == 273)
    quote = paths_report['checked_components_v1']
    require('quote six yields seven next and twelve adds', quote['max_block_occurrences']['bb7'] == 6 and quote['max_calls_on_one_path']['abstract_std:enumerate_next'] == 7 and quote['max_calls_on_one_path']['abstract_std:checked_add_u64'] == 12)
    require('no repeated P0 direct callee per body', all(count <= 1 for calls in call_report.values() for k, count in calls.items() if k.startswith('p0:')))
    require('callback cut exactly one', call_report['fixture_dispatch_closure'] == {'required:P1_P5_callback_body': 1})
    require('two written P5 cut sites are alternatives', sum(c.get('required:P5_actual_payload_destruction', 0) for c in call_report.values()) == 2)

    account_source = read(ACCOUNT / 'host_account.rs').decode().split('#[cfg(test)]', 1)[0]
    entry_source = read(ACCOUNT / 'entry.inc.rs').decode()
    require('only one authored P0 destructor', len(re.findall(r'\bDrop\s+for\b', account_source)) == 1)
    require('both payload destruction routes take first', account_source.count('if let Some(owned) = self.owned.take() { drop(owned); }') == 2)
    require('exact generic inspect returns shared borrow', 'pub(super) fn inspect_v1(&self) -> Option<&T> { self.owned.as_ref() }' in account_source)
    require('exact dispatch closure no extra callback', 'Ok(reservation.dispatch_v1(|| run_prepaid_fixture_v1(fixture)))' in entry_source)
    require('two selected constructors still pending', 'WholeQuotePending' in body_map['selected_whole_quote_v1'] and '::Ok(' not in body_map['selected_whole_quote_v1'] and 'RootPolicyPending' in body_map['selected_parent_account_v1'] and '::Ok(' not in body_map['selected_parent_account_v1'])

    drop = load(PROPOSAL / 'drop-surface.json')
    expected_drop = [
        ('call_authored_wrapper_Drop', 1, [('drop', '_1'), ('dispatch_v1', '_0')]),
        ('owned_None_discriminant_and_branch_after_hook', 2, [('dispatch_v1', '_6')]),
        ('reservation_option_discriminant_and_branch', 2, [('dispatch_v1', '_8')]),
        ('reservation_scalar_field_end', 2, [('dispatch_v1', '_1')]),
        ('wrapper_carrier_retirement_end', 1, [('dispatch_v1', '_0')]),
        ('wrapper_normal_and_unwind_control_flags', 2, [('drop', '_8')]),
        ('iterator_remaining_Cost_scalar_field_ends', 3*6*2, [('checked_components_v1', '_2')]),
        ('unused_reservation_field_ends', 2, [('dispatch_v1', '_1')]),
        ('destroyed_token_discard_or_release_field_ends', 2*2, [('release_destroyed_v1', '_1')]),
        ('unused_fixture_or_closure_header_end', 2, [('run_one_fixture_v1', '_2')]),
    ]
    fs = {f['id']: f for f in ledger['functions']}
    drop_s = drop_b = 0
    require('ten explicit primitive destruction operations', len(drop['rows']) == len(expected_drop) == 10)
    for row, (name, count, selectors) in zip(drop['rows'], expected_drop):
        require('drop operation and occurrences ' + name, row['operation'] == name and row['occurrence_bound'] == count and [tuple(x) for x in row['operand_selectors']] == selectors)
        leaves = extent = 0
        for op, (fid, local) in zip(row['operands'], selectors):
            role = fs[fid]['roles'][local]
            require('drop typed operand ' + name + local, op == {'type': role['concrete_production_type'], 'bytes': role['bytes'], 'scalar_leaves': actual_shapes.n(role['concrete_production_type'])})
            leaves += op['scalar_leaves']
            extent += op['bytes']
        ds, db = 4 + 2*leaves, 2*extent
        require('drop independent arithmetic ' + name, (ds, db, ds+db) == (row['source_action_units_each'], row['native_sized_occurrence_bytes_each'], row['combined_surface_units_each']))
        drop_s += count * ds
        drop_b += count * db
    require('drop addendum dimensions', (drop_s, drop_b, drop_s+drop_b) == (20882, 110452, 131334))
    fixed_s = drop_s + sum(v['source'] for k, v in totals.items() if k not in ('inspect_v1', 'usage_v1'))
    fixed_b = drop_b + sum(v['native'] for k, v in totals.items() if k not in ('inspect_v1', 'usage_v1'))
    require('formula independent dimensions', (fixed_s, fixed_b, fixed_s+fixed_b, totals['inspect_v1']['combined'], totals['usage_v1']['combined']) == (416998, 2211090, 2628088, 194231, 1039))
    require('source-object inventory is separate from work', sum(f['logical_role_bytes'] for f in ledger['functions']) == 234375 and sum(f['role_count'] for f in ledger['functions']) == 208)

    examples = independent_counterexamples(actual_shapes, fs, paths_report)
    return {
        'schema': 1, 'status': 'accepted-bounded-source145-account-surface-and-required-cut-interface-only',
        'source_tree_sha256': SOURCE, 'source_members': 145,
        'producer_seal_sha256': sha(read(PROPOSAL / 'seal.json')),
        'formula': '2628088 + 194231*I + 1039*U',
        'dimensions': {'fixed_source_actions': fixed_s, 'fixed_native_occurrence_allowance': fixed_b, 'fixed_combined': fixed_s+fixed_b, 'I': totals['inspect_v1'], 'U': totals['usage_v1'], 'drop_addendum': {'source': drop_s, 'native': drop_b, 'combined': drop_s+drop_b}},
        'independent_reconciliation': {'checks': len(checks), 'MIR_functions': 15, 'roles': 208, 'logical_inventory_bytes': 234375, 'written_MIR_operations': line_count, 'reference_mentions_surcharged': reference_occurrences, 'aggregate_mentions': aggregate_occurrences, 'transitive_source_shapes': len(actual_shapes.used), 'native_diagnostic_queries': 90, 'native_diagnostic_unique_spellings': len(diagnostic_sizes), 'terminal_paths': 273},
        'function_arithmetic': totals, 'path_review': paths_report, 'call_union': call_report,
        'independent_counterexamples': examples,
        'not_accepted': ['full_P0_work_or_storage', 'whole_host_quote', 'root_policy_or_grant', 'source146_rebinding', 'fixture_execution_qualification', 'CPU_or_physical_byte_copy_bound', 'native_or_device_or_OTA_or_FieldLog_or_customer_or_GA'],
        'required_unselected_cuts': ['exact_root_quote_constructor_caller_route', 'finite_I_and_U_no_default_zero', 'immutable_fixture_binding_and_backing', 'eventual_P0_dynamic_and_native_backing', 'complete_P0_storage_and_preexisting_root_provisioning', 'P1_setup', 'P1_loader_including_original_validation', 'P2_arguments', 'P3_pre_store_shell', 'P4_selected_route', 'P5_owned_return', 'P5_actual_payload_destruction_nonzero'],
        'limitations': ['Opaque standard resources and closed source-level std operations are abstract primitives; private std/compiler/kernel/allocator implementations and retry traces are excluded, not priced zero.', 'The ten drop rows cover finite source-visible carrier/field/control operations, not compiler instruction sequences or transitive payload destruction.', 'Borrowed T can in general clone or use interior mutation; this review binds only the frozen private T and exact audited entry. Future inspecting callers need work/backing/ownership review.', 'The authored P0 Drop body occurs at most once across explicit, cleanup, and ordinary alternatives; owned.take clears before T destruction. Actual payload destruction stays a required nonzero P5 term.', 'Current pending constructors cannot price future successful bodies. Source146 needs new binding; no active composition evidence was read.'],
        'python': platform.python_version(), 'producer_code_executed': False, 'compiler_invoked': False, 'product_or_native_invoked': False,
    }


def independent_counterexamples(shapes, fs, paths):
    """New arithmetic/state witnesses independent of producer's model code."""
    examples = []
    loaded = next(x for x in shapes.used['OwnedFixtureOutcomeV1']['variants'] if x['name'] == 'Loaded')['payload_leaves']
    refused = next(x for x in shapes.used['OwnedFixtureOutcomeV1']['variants'] if x['name'] == 'SetupRefused')['payload_leaves']
    require('new enum first-variant underpricing witness', (loaded, refused, loaded-refused) == (2555, 13, 2542))
    examples.append({'bad_rule': 'price_only_first_payload_variant', 'first_variant_leaves_with_tag': refused+1, 'actual_max_variant_leaves_with_tag': loaded+1, 'missed_leaves_per_occurrence': loaded-refused})
    require('new fixed-array scalar collapse witness', shapes.n('UnverifiedProfileHeaderV1') == 512 and shapes.n('UnverifiedProfileDigestBytesV1') == 8*32 == 256)
    examples.append({'bad_rule': 'collapse_fixed_array_to_one_scalar', 'header_bytes_scalar_leaves': 512, 'claims_eight_digests_scalar_leaves': 256, 'lost_header_leaves': 511})
    inspect_roles = fs['inspect_v1']['roles']
    inner = next(r for r in inspect_roles.values() if r['pointee_type'] and 'Option<' in r['pointee_type'])
    require('new full pointee surcharge witness', inner['bytes'] == 8 and inner['pointee_bytes'] == 13608 and inner['pointee_scalar_leaves'] == 2557)
    examples.append({'bad_rule': 'charge_reference_header_without_pointee', 'reference_bytes': 8, 'additional_native_allowance_per_mention': 2*inner['pointee_bytes'], 'additional_scalar_actions_per_mention': 2*inner['pointee_scalar_leaves'], 'physical_copy_inferred': False})
    # Dropping any written block underprices that defined all-block allowance,
    # even if source route constraints make the block currently unreachable.
    cleanup = [(f['id'], bid, bb) for f in fs.values() for bid, bb in f['blocks'].items() if bb['cleanup']]
    cleanup_s = sum(bb['occurrence_bound']*bb['source_action_units'] for fid, bid, bb in cleanup if fid not in ('inspect_v1', 'usage_v1'))
    cleanup_b = sum(bb['occurrence_bound']*bb['native_sized_occurrence_bytes'] for fid, bid, bb in cleanup if fid not in ('inspect_v1', 'usage_v1'))
    require('new cleanup omission has positive independent cost', cleanup_s > 0 and cleanup_b > 0)
    examples.append({'bad_rule': 'omit_all_written_cleanup_blocks', 'cleanup_blocks': len(cleanup), 'missed_source_actions': cleanup_s, 'missed_native_allowance': cleanup_b, 'missed_combined': cleanup_s+cleanup_b})
    # Six yield events permit a final exhaustion test after the sixth yield.
    require('new six-next assumption misses exhaustion call', paths['checked_components_v1']['max_calls_on_one_path']['abstract_std:enumerate_next'] == 7)
    examples.append({'bad_rule': 'six_elements_means_six_next_calls', 'six_some_yields': 6, 'final_none_next': 1, 'required_next_bound': 7, 'checked_add_bound': 12})
    fixed, ci, cu = 2628088, 194231, 1039
    max_i = (MAX-fixed)//ci
    max_u = (MAX-fixed)//cu
    for name, n, coef in [('I', max_i, ci), ('U', max_u, cu)]:
        require('new exact u64 coefficient threshold ' + name, fixed+n*coef <= MAX < fixed+(n+1)*coef)
    examples.append({'bad_rule': 'wrapping_or_unchecked_occurrence_arithmetic', 'MAX': MAX, 'largest_I_ignoring_required_positive_cuts': max_i, 'largest_U_ignoring_required_positive_cuts': max_u, 'I_next_overflow': fixed+(max_i+1)*ci, 'U_next_overflow': fixed+(max_u+1)*cu, 'thresholds_are_not_selected_counts_or_grants': True})
    # State exploration distinguishes inner payload invocation from P0 hook.
    states = []
    for route in ('explicit', 'ordinary'):
        for payload_unwinds in (False, True):
            owned, payload_calls, hook_calls, token, released = True, 0, 0, False, False
            if route == 'explicit':
                owned = False
                payload_calls += 1
                hook_calls += 1  # explicit drop(self), or cleanup if payload unwinds
                if owned:
                    payload_calls += 1
                token = not payload_unwinds
            else:
                hook_calls += 1
                owned = False
                payload_calls += 1
            require('new take-before-unwind finite state ' + str((route, payload_unwinds)), payload_calls == 1 and hook_calls == 1 and not owned and not released and (not payload_unwinds or not token))
            states.append({'route': route, 'payload_unwinds': payload_unwinds, 'P0_hook_calls': hook_calls, 'P5_payload_calls': payload_calls, 'successful_token': token, 'charge_released_here': released})
    bad_calls = 1 + int(True)  # payload still Some when unwind field finalization begins
    require('new delayed-take double-destructor countermodel', bad_calls == 2)
    examples.append({'bad_rule': 'count_Drop_hook_as_payload_work_or_clear_owned_after_drop', 'correct_states': states, 'delayed_take_unwind_payload_calls': bad_calls, 'required_P5_term_may_not_be_zero': True})
    # Generic shared borrow is not a no-clone/no-allocation theorem.
    examples.append({'bad_rule': 'shared_borrow_proves_no_resource_escape_for_any_T', 'countermodel': 'T with Clone or interior Cell/RefCell/Arc can clone or mutate via &T; compiler borrow escape rejection alone does not forbid that.', 'frozen_scope': 'private OwnedFixtureOutcomeV1 and existing entry only; any future inspector/caller has separate P0/backing/ownership cuts'})
    examples.append({'bad_rule': 'child_storage_return_can_fund_parent_execution', 'pregrant_known_pending_quote_cost': fs['selected_whole_quote_v1']['combined_surface_units_per_invocation'], 'no_child_grant_on_pending_return': True, 'root_and_parent_preexisting_funding_still_required': True})
    return examples


def main():
    result = audit()
    require('input source release remained immutable', sha(read(PROPOSAL / 'seal.json')) == 'bc9426ad22da41b354094b1778685bb7bf834e03fc22101272c2f08bf5d2b857')
    result['independent_reconciliation']['checks'] = len(checks)
    artifacts = {'review.json': result, 'checks.json': {'checks': len(checks), 'labels': checks}, 'input-custody.json': {'schema': 1, 'source_tree_sha256': SOURCE, 'files': dict(sorted(inputs.items()))}}
    if '--check-only' in sys.argv:
        for name, data in artifacts.items():
            require('frozen independent artifact ' + name, (HERE/name).read_bytes() == (json.dumps(data, sort_keys=True, indent=2)+'\n').encode())
    else:
        for name, data in artifacts.items():
            (HERE/name).write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')
    print(json.dumps({'passed': True, 'checks': result['independent_reconciliation']['checks'], 'source_tree_sha256': SOURCE, 'status': result['status'], 'mode': 'check-only' if '--check-only' in sys.argv else 'derive'}))


if __name__ == '__main__':
    main()
