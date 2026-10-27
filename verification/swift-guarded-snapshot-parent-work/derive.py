#!/usr/bin/env python3
"""Finite source145 P0 work proposal. Compiler output is read as immutable data.

No product/native code is executed. Writes are confined to this packet.
The result is deliberately not a selected root policy or a whole-host quote.
"""
import ast
import collections
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-host-account-entry'
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
BOOT = ROOT / 'verification/swift-guarded-snapshot-bootstrap-host-boundary'
SOURCE_TREE = '5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
U64_MAX = 2**64 - 1
checks = []
inputs = {}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, predicate):
    if not predicate:
        raise AssertionError(label)
    checks.append(label)


def read(path):
    data = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = {'bytes': len(data), 'sha256': sha(data)}
    return data


def load(path):
    return json.loads(read(path))


def member(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': sha(data)}


def verify_seal(folder, expected, totals):
    data = read(folder / 'seal.json')
    check(str(folder.relative_to(ROOT)) + ' seal', sha(data) == expected)
    seal = json.loads(data)
    check('seal totals ' + str(folder), (seal['member_count'], seal['member_bytes']) == totals)
    check('seal member count ' + str(folder), len(seal['members']) == totals[0])
    for item in seal['members']:
        actual = read(folder / item['path'])
        check('sealed member ' + str(folder / item['path']), member(item['path'], actual) == item)
    check('seal byte sum ' + str(folder), sum(m['bytes'] for m in seal['members']) == totals[1])
    return seal


def split_top(text, delimiter=','):
    """Split the bounded Rust data-type grammar, balancing (), [], {}, and <>."""
    stack = []
    pairs = {'(': ')', '[': ']', '{': '}', '<': '>'}
    start = 0
    result = []
    for i, char in enumerate(text):
        if char in pairs:
            stack.append(pairs[char])
        elif char in ')]}>':
            if not stack or stack.pop() != char:
                raise AssertionError('unbalanced data type: ' + text)
        elif char == delimiter and not stack:
            result.append(text[start:i].strip())
            start = i + 1
    if stack:
        raise AssertionError('unfinished data type: ' + text)
    result.append(text[start:].strip())
    return [item for item in result if item]


def matching(text, start, opening='{', closing='}'):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError('unfinished source data declaration')


def stripped_source(raw):
    # This is a finite data-declaration reader, not an authority/release test.
    # The selected definitions have no string literals containing comment marks.
    raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.S)
    return '\n'.join(line.split('//', 1)[0] for line in raw.splitlines())


def named_field_types(body):
    result = []
    for field in split_top(body):
        field = re.sub(r'#\[[^\]]*\]', '', field).strip()
        field = re.sub(r'^pub(?:\([^)]*\))?\s+', '', field)
        match = re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*\s*:\s*(.+)', field, re.S)
        if not match:
            raise AssertionError('unsupported source field: ' + field)
        result.append(match[1].strip())
    return result


def data_definitions(source):
    definitions = collections.defaultdict(list)
    for path, raw in source.items():
        if not path.endswith('.rs') or '/test' in path or path.endswith('_tests.rs'):
            continue
        text = stripped_source(raw.decode())
        # A name is resolved only if its precise bounded data declaration is
        # unambiguous, or via the explicit module choices below.
        for match in re.finditer(r'\b(struct|enum)\s+([A-Za-z_][A-Za-z_0-9]*)\s*([^;{]*)\{', text):
            kind, name = match[1], match[2]
            extra = match[3].strip()
            if extra and not extra.startswith('<'):
                continue
            start = match.end() - 1
            stop = matching(text, start)
            body = text[start+1:stop]
            declaration = text[match.start():stop+1]
            definitions[name].append({'kind': kind, 'name': name, 'path': path,
                                      'declaration_sha256': sha(declaration.encode()),
                                      'body': body, 'declaration': declaration})
    return definitions


class Shapes:
    """Same max-inhabited-variant scalar abstraction as the loader work lane."""
    def __init__(self, source):
        self.defs = data_definitions(source)
        self.used = {}
        self.cache = {}
        self.stack = []
        self.constants = {'COMPONENT_COUNT_V1': 6}

    def shape(self, ty):
        original = ty
        ty = ty.strip()
        ty = {'AError':'SnapshotAdmissionErrorV1','Stop':'SnapshotStopV1'}.get(ty,ty)
        if ty in self.cache:
            return self.cache[ty]
        if ty in self.stack:
            raise AssertionError('recursive by-value type: ' + ty)
        self.stack.append(ty)
        if ty.startswith('&') or ty.startswith('*const ') or ty.startswith('*mut '):
            n = 1
        elif ty in ('()', '!'):
            n = 1
        elif ty in ('u8','u16','u32','u64','u128','i8','i16','i32','i64','i128',
                    'usize','isize','bool','f32','f64','char','str'):
            n = 1
        elif ty.startswith('{closure@') or 'impl FnOnce' in ty:
            # Exact closure captures one FrozenFixtureV1 reference header.
            n = 1
        elif ty.startswith('['):
            check('array shape closes ' + ty, ty.endswith(']'))
            parts = split_top(ty[1:-1], ';')
            check('fixed non-slice array ' + ty, len(parts) == 2)
            count = self.constants.get(parts[1], None)
            if count is None:
                count = ast.literal_eval(parts[1].replace('_', ''))
            check('bounded nonnegative array ' + ty, type(count) is int and count >= 0)
            n = count * self.shape(parts[0])
        elif ty.startswith('(') and ty.endswith(')'):
            n = sum(self.shape(x) for x in split_top(ty[1:-1])) or 1
        else:
            head = ty.split('<', 1)[0]
            name = head.split('::')[-1]
            args = split_top(ty[len(head)+1:-1]) if '<' in ty and ty.endswith('>') else []
            if name in ('Option','Result','ControlFlow'):
                check('arity ' + ty, len(args) == (1 if name == 'Option' else 2))
                n = 1 + max([0] + [self.shape(x) for x in args])
            elif name == 'Infallible':
                n = 0
            elif name == 'Cell':
                check('Cell concrete ' + ty, len(args) == 1)
                n = self.shape(args[0])
            elif name in ('File','Error','Cancellation','Instant','Duration','Path',
                          'OpenOptions','Vec','String','Arc','Rc','Box','IntoIter','Enumerate'):
                # Opaque std/resource header is one source-level primitive.
                # Its private implementation and dynamic backing are cut terms.
                n = 1
            else:
                candidates = self.defs.get(name, [])
                preferred = {
                    'Refusal': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs',
                    'Role': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs',
                    'Resource': 'src/experimental_wasi/mod.rs',
                }.get(name)
                if preferred:
                    candidates = [d for d in candidates if d['path'] == preferred]
                check('known unambiguous concrete source shape ' + ty, len(candidates) == 1)
                d = candidates[0]
                if d['kind'] == 'struct':
                    fields = named_field_types(d['body'])
                    if name == 'PrepaidOwnedV1':
                        check('only exact actual payload specialization ' + ty,
                              len(args) == 2 and args[-1].split('::')[-1] == 'OwnedFixtureOutcomeV1')
                        fields = [re.sub(r'\bT\b', args[-1], field) for field in fields]
                    n = sum(self.shape(x) for x in fields) or 1
                    proof = {'kind': 'struct', 'fields': fields}
                else:
                    variants = []
                    for variant in split_top(d['body']):
                        variant = re.sub(r'#\[[^\]]*\]', '', variant).strip()
                        vm = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)(.*)', variant, re.S)
                        check('variant parse ' + name, vm is not None)
                        suffix = vm[2].strip()
                        if suffix.startswith('('):
                            end = matching(suffix, 0, '(', ')')
                            fields = split_top(suffix[1:end])
                        elif suffix.startswith('{'):
                            end = matching(suffix, 0)
                            fields = named_field_types(suffix[1:end])
                        else:
                            check('unit/discriminant variant ' + name, not suffix or suffix.startswith('='))
                            fields = []
                        variants.append({'name': vm[1], 'fields': fields,
                                         'payload_leaves': sum(self.shape(x) for x in fields)})
                    n = 1 + max([0] + [v['payload_leaves'] for v in variants])
                    proof = {'kind': 'enum', 'variants': variants}
                self.used[name] = {'path': d['path'], 'declaration_sha256': d['declaration_sha256'],
                                   'scalar_leaves': n, **proof}
        self.stack.pop()
        self.cache[original] = n
        return n


def split_functions(raw):
    result = []
    current = None
    for line in raw.splitlines(keepends=True):
        if line.startswith('fn '):
            check('MIR function outside previous body', current is None)
            current = [line]
        elif current is not None:
            current.append(line)
        elif line.strip():
            raise AssertionError('unparsed MIR data outside function')
        if current is not None and line.rstrip('\n') == '}':
            result.append(''.join(current))
            current = None
    check('MIR complete final body', current is None)
    return result


def blocks(body):
    result = {}
    active = None
    for source_line, line in enumerate(body.splitlines(), 1):
        code = line.split('//', 1)[0].rstrip()
        match = re.fullmatch(r'    (bb\d+)( \(cleanup\))?: \{', code)
        if match:
            active = match[1]
            result[active] = {'cleanup': bool(match[2]), 'lines': []}
        elif active and code == '    }':
            active = None
        elif active and code.strip():
            result[active]['lines'].append({'code': code.strip(), 'body_line': source_line})
    for block in result.values():
        block['successors'] = sorted(set(re.findall(r'\bbb\d+\b', '\n'.join(x['code'] for x in block['lines']))))
        check('one final MIR terminator per block', any(
            block['lines'][-1]['code'].startswith(x) for x in
            ('goto ', 'switchInt(', 'return;', 'resume;', 'unreachable;', 'drop('))
            or ' -> [' in block['lines'][-1]['code'])
    return result


def constant_occurrences(code):
    result = []
    # All constants in these fifteen bodies must match this explicit grammar.
    matches = list(re.finditer(r'\bconst\s+', code))
    for m in matches:
        token = code[m.end():]
        cm = re.match(r'(\d+)_(u64|usize)|(?:true|false)\b|\(\)', token)
        check('known constant grammar ' + code, cm is not None)
        value = cm[0]
        size = 8 if value.endswith(('_u64','_usize')) else 0 if value == '()' else 1
        result.append({'text': value, 'bytes': size, 'scalar_leaves': 1})
    return result


def function_id(header):
    name = header.split('(', 1)[0]
    if '{closure#0}' in name:
        return 'fixture_dispatch_closure'
    return name.split('::')[-1].removeprefix('fn ')


def pointee_type(ty):
    if not ty.startswith('&'):
        return None
    ty = ty[1:].strip()
    ty = re.sub(r"^'[^ ]+\s+", '', ty)
    return ty.removeprefix('mut ').strip()


def full_type_name(ty):
    # Every spelling is from a compiler-measured role, not a size guess.
    return ty.replace('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::', '').replace('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::', '').replace('std::', '')


def classify_call(code):
    if ' -> [' not in code:
        return None
    if code.startswith('switchInt('):
        return None
    if code.startswith('drop('):
        return 'std_iterator_drop' if 'drop(_8)' in code else 'wrapper_drop_glue'
    symbol = code.split(' = ', 1)[1].split(' -> [', 1)[0]
    if symbol.startswith('<impl FnOnce() -> T as FnOnce<()>>::call_once'):
        return 'p0:fixture_dispatch_closure'
    products = ['selected_whole_quote_v1', 'reserve_whole_v1', 'dispatch_v1',
                'destroy_owned_v1', 'release_destroyed_v1']
    for name in products:
        if re.search(r'\b' + name + r'(?:::|\()', symbol):
            return 'p0:' + name
    if symbol.startswith('run_prepaid_fixture_v1('):
        return 'required:P1_P5_callback_body'
    if symbol.startswith('std::mem::drop::<T>'):
        return 'required:P5_actual_payload_destruction'
    if symbol.startswith('std::mem::drop::<PrepaidOwnedV1'):
        return 'wrapper_drop_glue'
    std_patterns = {
        'array_into_iter': r'^<\[CostV1; 6\] as IntoIterator>::into_iter',
        'enumerate_constructor': r'^<std::array::IntoIter<CostV1, 6> as Iterator>::enumerate',
        'enumerate_into_iter': r'^<Enumerate<std::array::IntoIter<CostV1, 6>> as IntoIterator>::into_iter',
        'enumerate_next': r'^<Enumerate<std::array::IntoIter<CostV1, 6>> as Iterator>::next',
        'checked_add_u64': r'^core::num::<impl u64>::checked_add',
        'checked_sub_u64': r'^core::num::<impl u64>::checked_sub',
        'option_ok_or': r'^Option::<u64>::ok_or::<RefusalV1>',
        'result_try_branch': r'^<Result<.+ as Try>::branch',
        'result_from_residual': r'^<Result<.+ as FromResidual<.+>>::from_residual',
        'cell_new': r'^Cell::<UsageV1>::new',
        'cell_get': r'^Cell::<UsageV1>::get',
        'cell_set': r'^Cell::<UsageV1>::set',
        'u64_max': r'^<u64 as Ord>::max',
        'option_as_ref': r'^Option::<T>::as_ref',
        'option_take_payload': r'^Option::<T>::take',
        'option_take_reservation': r"^Option::<ReservationV1<'_>>::take",
    }
    found = [name for name, pattern in std_patterns.items() if re.search(pattern, symbol)]
    check('one explicit call classification: ' + symbol, len(found) == 1)
    return 'abstract_std:' + found[0]


def checked_add(a, b):
    if not (type(a) is int and type(b) is int and 0 <= a <= U64_MAX and 0 <= b <= U64_MAX):
        raise ValueError('unknown/non-u64 input')
    result = a + b
    if result > U64_MAX:
        raise OverflowError('addition')
    return result


def checked_mul(a, b):
    if not (type(a) is int and type(b) is int and 0 <= a <= U64_MAX and 0 <= b <= U64_MAX):
        raise ValueError('unknown/non-u64 input')
    result = a * b
    if result > U64_MAX:
        raise OverflowError('multiplication')
    return result


def checked_quote(parts):
    if len(parts) != 6:
        return {'refusal': 'MissingSixComponents'}
    total = [0, 0]
    for i, part in enumerate(parts):
        if part is None or len(part) != 2:
            return {'refusal': 'UnknownComponent', 'index': i}
        work, storage = part
        if not (type(work) is int and type(storage) is int and 0 < work <= U64_MAX and 0 < storage <= U64_MAX):
            return {'refusal': 'UnpricedComponent', 'index': i}
        try:
            total[0] = checked_add(total[0], work)
            total[1] = checked_add(total[1], storage)
        except OverflowError:
            return {'refusal': 'QuoteOverflow', 'index': i}
    return {'total': total}


def reserve(before, limits, quote):
    work, storage, peak = before
    try:
        after_work = checked_add(work, quote[0])
    except OverflowError:
        return ('WorkOverflow', before)
    try:
        after_storage = checked_add(storage, quote[1])
    except OverflowError:
        return ('StorageOverflow', before)
    if after_work > limits[0]:
        return ('InsufficientWork', before)
    if after_storage > limits[1]:
        return ('InsufficientStorage', before)
    return ('Granted', (after_work, after_storage, max(peak, after_storage)))


def retirement(before, charge, exit_kind, token=False):
    """Separate finite ownership model, with no call into Rust/product code."""
    if exit_kind == 'explicit_destroy_returned':
        # Inner payload and wrapper are gone; account is still charged.
        return {'usage':before,'token':True,'payload_alive':False,'released':False}
    if exit_kind == 'successful_token_release' and token:
        if charge > before[1]:
            return {'usage':before,'token':False,'payload_alive':False,'released':False}
        return {'usage':(before[0],before[1]-charge,before[2]),'token':False,
                'payload_alive':False,'released':True}
    return {'usage':before,'token':False,
            'payload_alive':None if exit_kind in ('callback_unwind','payload_unwind') else False,
            'released':False}


def path_controls(functions):
    """Enumerate the bounded source-level CFG, including every unwind edge.

    Array iteration is closed at six yielded elements and a seventh next. This
    is the explicit finite route contract, not a guessed execution time bound.
    """
    result = {}
    for fn in functions:
        graph = fn['blocks']
        terminal_count = 0
        largest = collections.Counter()
        max_source = max_native = max_steps = 0
        terminal_kinds = collections.Counter()
        todo = [('bb0', collections.Counter(), 0, 0, 0)]
        while todo:
            bid, counts, yielded, source, native = todo.pop()
            counts = counts.copy()
            counts[bid] += 1
            check('finite CFG occurrence ' + fn['id'] + bid,
                  counts[bid] <= graph[bid]['occurrence_bound'])
            check('finite CFG steps ' + fn['id'], sum(counts.values()) <= 1000)
            block = graph[bid]
            source += block['source_action_units']
            native += block['native_sized_occurrence_bytes']
            if fn['id'] == 'checked_components_v1' and bid == 'bb7':
                yielded += 1
            check('at most six yielded quote components ' + fn['id'], yielded <= 6)
            line = block['lines'][-1]['code']
            successors = list(block['successors'])
            if fn['id'] == 'checked_components_v1' and bid == 'bb5' and yielded == 6:
                successors = [s for s in successors if s != 'bb7']
            terminal = []
            if 'unwind continue' in line:
                terminal.append('unwind-continue')
            if 'unwind terminate' in line:
                terminal.append('unwind-terminate')
            if not successors:
                terminal.append('return' if line == 'return;' else 'resume' if line=='resume;' else 'unreachable')
            for successor in successors:
                todo.append((successor,counts,yielded,source,native))
            for kind in terminal:
                terminal_count += 1
                terminal_kinds[kind] += 1
                largest |= counts
                max_source = max(max_source,source)
                max_native = max(max_native,native)
                max_steps = max(max_steps,sum(counts.values()))
                check('path surface source bound ' + fn['id'],
                      source+fn['entry_source_action_units'] <= fn['source_action_units_per_invocation'])
                check('path surface native bound ' + fn['id'],
                      native+fn['entry_native_sized_occurrence_bytes'] <= fn['native_sized_occurrence_bytes_per_invocation'])
        check('at least one terminal path ' + fn['id'], terminal_count > 0)
        result[fn['id']] = {'bounded_terminal_paths':terminal_count,'terminal_kinds':dict(terminal_kinds),
                            'max_block_occurrences':dict(largest),'max_path_blocks':max_steps,
                            'max_path_source_action_units_excluding_entry':max_source,
                            'max_path_native_sized_occurrence_bytes_excluding_entry':max_native}
    return result


def reachable(graph, start, excluded=()):
    todo = [start]
    seen = set()
    while todo:
        bid = todo.pop()
        if bid in seen or bid in excluded:
            continue
        seen.add(bid)
        todo.extend(graph[bid]['successors'])
    return seen


def ownership_controls(functions):
    by_name = {f['id']:f for f in functions}
    conclusions = []
    def require(label, condition):
        check(label,condition)
        conclusions.append(label)
    reserve_graph = by_name['reserve_whole_v1']['blocks']
    commits = [b for b,v in reserve_graph.items() if any(r['call_cut']=='abstract_std:cell_set' for r in v['lines'])]
    require('reserve exactly one Cell commit callsite', commits == ['bb19'])
    for refusal_block in ('bb7','bb13','bb15','bb17'):
        require('reserve refusal cannot reach commit '+refusal_block,
                'bb19' not in reachable(reserve_graph,refusal_block))
    require('both work/storage checked additions exist before success',
            sum(r['call_cut']=='abstract_std:checked_add_u64' for b in reserve_graph.values() for r in b['lines']) == 2)
    require('reserve commit dominated by both comparisons',
            'bb19' not in reachable(reserve_graph,'bb0',('bb12',))
            and 'bb19' not in reachable(reserve_graph,'bb0',('bb16',)))
    require('reserve success return cannot precede commit',
            'bb20' not in reachable(reserve_graph,'bb0',('bb19',)))
    destroy = by_name['destroy_owned_v1']['blocks']
    require('token construction after wrapper drop call returns',
            'bb10' not in reachable(destroy,'bb0',('bb6',))
            and 'bb10' not in reachable(destroy,'bb0',('bb7',)))
    require('cleanup cannot construct successful destroyed token',
            all('bb10' not in reachable(destroy,b) for b,v in destroy.items() if v['cleanup']))
    for name in ('destroy_owned_v1','drop'):
        calls = [r['call_cut'] for b in by_name[name]['blocks'].values() for r in b['lines']]
        require(name+' does not call storage release or Cell commit',
                'p0:release_destroyed_v1' not in calls and 'abstract_std:cell_set' not in calls)
    release = by_name['release_destroyed_v1']['blocks']
    require('release subtraction failure cannot reach commit',
            'bb3' not in reachable(release,'bb5'))
    release_source = '\n'.join(r['code'] for b in release.values() for r in b['lines'])
    require('release copies original work and peak without subtraction',
            'work: copy (_2.0: u64)' in release_source and 'peak_storage: copy (_2.2: u64)' in release_source)
    for name,refusal in [('selected_whole_quote_v1','WholeQuotePending'),('selected_parent_account_v1','RootPolicyPending')]:
        fn = by_name[name]
        code = '\n'.join(r['code'] for b in fn['blocks'].values() for r in b['lines'])
        require(name+' remains exact pending refusal', len(fn['blocks']) == 1 and refusal in code and '::Err(' in code and '::Ok(' not in code)
    fixture = by_name['run_one_fixture_v1']['blocks']
    require('dispatch after successful reserve branch',
            'bb9' not in reachable(fixture,'bb0',('bb4',))
            and 'bb9' not in reachable(fixture,'bb0',('bb7',)))
    require('no dispatch reachable from either written fixture refusal',
            all('bb9' not in reachable(fixture,b) for b in ('bb5','bb10')))
    require('single source callback callsite',
            by_name['fixture_dispatch_closure']['calls_per_invocation_bound'] == {'required:P1_P5_callback_body':1})
    return conclusions


def interface_evaluate(fixed, coefficients, I, U, terms, source_binding):
    """Checked component expression only. Success does not establish authority."""
    if source_binding != SOURCE_TREE:
        return {'refusal':'SourceRebindingRequired'}
    if any(type(n) is not int or n<0 or n>U64_MAX for n in (I,U)):
        return {'refusal':'UnknownOrInvalidOccurrenceBound'}
    required = ['P1_setup','P1_loader_and_original_validation','P2_arguments','P3_pre_store_shell',
                'P4_selected_route','P5_owned_return','P5_actual_payload_destruction',
                'P0_unselected_root_route','P0_fixture_binding_and_backing','P0_dynamic_backing']
    for name in required:
        if type(terms.get(name)) is not int or not 0<terms[name]<=U64_MAX:
            return {'refusal':'MissingRequiredTerm','name':name}
    try:
        value = checked_add(checked_add(fixed,checked_mul(I,coefficients['inspect_v1'])),
                            checked_mul(U,coefficients['usage_v1']))
        for name in required:
            value = checked_add(value,terms[name])
    except OverflowError:
        return {'refusal':'CostOverflow'}
    return {'bounded_expression':value,'operational_grant':False,'selected_policy':False}


def drop_surface(functions):
    """Conservative finite source-visible destructor boundary allowance.

    This does not invent a compiler instruction trace. Every reachable authored
    P0 destructor body is already counted once. Private Std/compiler lowering is
    excluded by the inherited unit. Each row pays extra finite source-level
    carrier field/control actions at measured operand extents; actual payload
    destructor bodies remain the required P5 cut.
    """
    by_name = {f['id']:f for f in functions}
    selectors = {
        'wrapper':('dispatch_v1','_0'),
        'wrapper_receiver':('drop','_1'),
        'owned_option':('dispatch_v1','_6'),
        'reservation_option':('dispatch_v1','_8'),
        'reservation':('dispatch_v1','_1'),
        'token':('release_destroyed_v1','_1'),
        'fixture_header':('run_one_fixture_v1','_2'),
        'cost':('checked_components_v1','_2'),
        'cleanup_flag':('drop','_8'),
    }
    operands = {name:by_name[fn]['roles'][local] for name,(fn,local) in selectors.items()}
    specifications = [
        ('call_authored_wrapper_Drop',1,['wrapper_receiver','wrapper'],
         'One P0 hook call; normal explicit drop(self), cleanup, and ordinary Drop are alternatives. The full authored body is charged separately once.'),
        ('owned_None_discriminant_and_branch_after_hook',2,['owned_option'],
         'Hook takes owned before any payload destructor; normal or payload-unwind field finalization sees None, preventing a second payload destructor.'),
        ('reservation_option_discriminant_and_branch',2,['reservation_option'],
         'Two carrier control actions; optional remaining ticket contains only account reference and storage u64, with no refund or authored destructor.'),
        ('reservation_scalar_field_end',2,['reservation'],
         'Conservatively charge both reference and u64 field ends using the whole measured reservation extent.'),
        ('wrapper_carrier_retirement_end',1,['wrapper'],
         'Final carrier end before returning any destroyed token.'),
        ('wrapper_normal_and_unwind_control_flags',2,['cleanup_flag'],
         'Both written exit alternatives charged without discount.'),
        ('iterator_remaining_Cost_scalar_field_ends',36,['cost'],
         'At most three written iterator drop sites times six Cost elements times two scalar fields; no Cost Drop impl or callback exists. Private iterator traversal instructions are outside the unit.'),
        ('unused_reservation_field_ends',2,['reservation'],
         'Unused ticket Drop retains charge; reference/u64 have no authored destructor.'),
        ('destroyed_token_discard_or_release_field_ends',4,['token'],
         'Both discard and consumed-release alternatives charged at two fields each; token holds a Reservation only and has no resource or payload.'),
        ('unused_fixture_or_closure_header_end',2,['fixture_header'],
         'FrozenFixture and its exact closure capture each contain one reference header; no authored destructor or child callback on discard.'),
    ]
    rows = []
    for name,count,keys,reason in specifications:
        leaves = sum(operands[k]['scalar_leaves'] for k in keys)
        extent = sum(operands[k]['bytes'] for k in keys)
        source = 4 + 2*leaves  # operation/rvalue + two conservative field/control events
        native = 2*extent
        rows.append({'operation':name,'occurrence_bound':count,'operand_selectors':[selectors[k] for k in keys],
                     'operands':[{'type':operands[k]['concrete_production_type'],
                                  'bytes':operands[k]['bytes'],'scalar_leaves':operands[k]['scalar_leaves']} for k in keys],
                     'source_action_units_each':source,'native_sized_occurrence_bytes_each':native,
                     'combined_surface_units_each':source+native,'reason':reason})
    source = sum(r['occurrence_bound']*r['source_action_units_each'] for r in rows)
    native = sum(r['occurrence_bound']*r['native_sized_occurrence_bytes_each'] for r in rows)
    account_source = read(PRODUCER/'host_account.rs').decode()
    production_account = account_source.split('#[cfg(test)]',1)[0]
    check('only one authored production P0 Drop impl',len(re.findall(r'impl<T> Drop for PrepaidOwnedV1',production_account)) == 1
          and len(re.findall(r'\bDrop for\b',production_account)) == 1)
    check('custom Drop takes owned before dropping payload',
          'if let Some(owned) = self.owned.take() { drop(owned); }' in production_account)
    historical = {}
    names = ['callback_unwind_or_unused_ticket_never_refunds',
             'ordinary_owner_drop_never_refunds_while_source_frame_is_live',
             'destructor_unwind_does_not_claim_storage_was_released',
             'original_refusal_output_and_diagnostic_owners_keep_storage_through_drop',
             'destroyed_token_releases_only_its_original_borrowed_account']
    for mode in ['debug','optimized']:
        output = read(PRODUCER/'account-commands'/f'{mode}-run'/'stdout').decode()
        for name in names:
            check('frozen historical '+mode+' drop control '+name,
                  'test host_account::tests::'+name+' ... ok' in output)
        historical[mode] = {'historical_only_not_rerun':True,'named_controls':names}
    return {'schema':1,'rows':rows,'source_action_units':source,
            'native_sized_occurrence_byte_allowance':native,'combined_surface_units':source+native,
            'authored_P0_Drop_body_occurrences':1,'actual_payload_destructor_body_occurrences_bound':1,
            'actual_payload_destructor_body_priced_here':False,
            'private_std_compiler_lowering_inherited_unit':'excluded, not a missing in-unit cost assigned zero',
            'historical_controls':historical,
            'counterexample_if_hook_did_not_take_before_drop':'If owned remained Some while its payload destructor unwound, wrapper field finalization could destroy it again; exact frozen take-before-drop source and tests rule out that state. Source change invalidates this schema.'}


def model_controls(functions):
    controls = []
    def require(label, predicate):
        check(label, predicate)
        controls.append(label)
    require('six exact positive components', checked_quote([(1, 1)] * 6) == {'total': [6, 6]})
    for index in range(6):
        for invalid in [None, (0, 1), (1, 0), (None, 1), (1, None), (-1, 1), (1, U64_MAX+1)]:
            parts = [(1, 1)]*6
            parts[index] = invalid
            require('six-component omission/refusal ' + str((index, invalid)), 'refusal' in checked_quote(parts))
        for large in [(U64_MAX, 1), (1, U64_MAX)]:
            parts = [(1, 1)]*6
            parts[index] = large
            require('quote checked overflow ' + str((index, large)), checked_quote(parts)['refusal'] == 'QuoteOverflow')
    require('five parts rejected', checked_quote([(1, 1)] * 5)['refusal'] == 'MissingSixComponents')
    require('seven parts rejected', checked_quote([(1, 1)] * 7)['refusal'] == 'MissingSixComponents')
    for before in [(0,0,0), (1,2,4), (U64_MAX,0,0), (0,U64_MAX,U64_MAX)]:
        for limits in [(0,0), (1,1), (8,9), (U64_MAX,U64_MAX)]:
            for quote in [(1,1), (7,8), (U64_MAX,1), (1,U64_MAX)]:
                status, after = reserve(before, limits, quote)
                require('atomic reserve ' + str((before,limits,quote)),
                        (status == 'Granted' and after[0] >= before[0] and after[1] >= before[1]
                         and after[2] >= before[2] and after[2] >= after[1]) or
                        (status != 'Granted' and after == before))
                for exit_kind in ['unused_ticket','callback_unwind','ordinary_drop','payload_unwind','discarded_token']:
                    # No explicit successful token release: immutable work,
                    # storage, peak remain. Payload work is never a credit.
                    observed = retirement(after,quote[1],exit_kind)
                    require('no retroactive credit ' + str((before,limits,quote,exit_kind)),
                            observed['usage'] == after and not observed['token'] and not observed['released'])
                if status == 'Granted':
                    destroyed = retirement(after,quote[1],'explicit_destroy_returned')
                    require('destroy precedes release and retains charges '+str((before,limits,quote)),
                            destroyed['usage']==after and destroyed['token'] and not destroyed['payload_alive']
                            and not destroyed['released'])
                    released = retirement(after,quote[1],'successful_token_release',token=destroyed['token'])['usage']
                    require('release preserves work/peak ' + str((before,limits,quote)),
                            released[0] == after[0] and released[2] == after[2]
                            and released[1] == before[1])
    require('inconsistent subtraction retains charges',
            retirement((3,1,7),2,'successful_token_release',token=True)['usage'] == (3,1,7))
    require('release without a token cannot change usage',
            retirement((3,7,7),7,'successful_token_release',token=False)['usage'] == (3,7,7))
    for fn in functions:
        require('positive zero-size action cost ' + fn['id'], all(
            row['source_action_units'] >= 2 for block in fn['blocks'].values() for row in block['lines']))
    for op, values in [('add', (U64_MAX,1)), ('mul', (U64_MAX,2))]:
        try:
            (checked_add if op == 'add' else checked_mul)(*values)
        except OverflowError:
            require('cost arithmetic overflow refuses ' + op, True)
        else:
            raise AssertionError('cost overflow did not fail closed')
    # Concrete finite witnesses, not merely tests which restate coefficients.
    witnesses = [
        {'bad_rule': 'token_count_only', 'function': 'destroy_returned_fixture_v1',
         'missed_native_bytes': 13624, 'reason': 'by-value wrapper parameter is not a 16-byte token'},
        {'bad_rule': 'projected_read_costs_reference_header_only', 'function': 'inspect_v1',
         'bad_bytes': 8, 'actual_projected_option_bytes': 13608,
         'reason': 'actual compiler-measured Option<OwnedFixtureOutcomeV1> pointee is read'},
        {'bad_rule': 'checked_quote_is_one_call', 'function': 'checked_components_v1',
         'six_parts': [(1,1)]*6, 'iterator_next_occurrences': 7, 'addition_occurrences': 12},
        {'bad_rule': 'child_can_pay_for_parent_before_grant', 'before': [0,0,0],
         'limits': [0,0], 'quote': [1,1], 'result': reserve((0,0,0),(0,0),(1,1))[0],
         'reason': 'quote/account/refusal work runs with no child grant'},
        {'bad_rule': 'drop_refunds_work_or_storage', 'before': [0,0,0], 'limits': [7,11],
         'quote': [7,11], 'usage_after_drop_without_token': [7,11,11]},
        {'bad_rule': 'unknown_child_or_destructor_cost_equals_zero', 'unknown_required_terms':
         ['P1_P5_callback_body', 'P5_actual_payload_destruction',
          'P0_unselected_root_route', 'P0_fixture_binding_and_backing'], 'grant_available': False},
    ]
    return controls, witnesses


def derive():
    release = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-host-composition-next-source-release.json'
    acceptance = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-host-account-host-acceptance.json'
    fixture_selection = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-host-fixture-source-selection.json'
    check('exact root selection', sha(read(release)) == '2f112a66bb382c7bce38866ac993acf95be01a939cf0d863cf9b98c60e3597ad')
    check('exact root account acceptance', sha(read(acceptance)) == '8bb780193f9039174b7f1dd503f6572f8cca9bf6ec01f81722ed3f25aa9d927a')
    check('future fixture selection retained as separate pending input',
          sha(read(fixture_selection)) == '5d7b4d01727c6163b25a309633f6952aa5625d14a124a0bc33c27737a51774e2')
    verify_seal(PRODUCER, '6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3', (136,3432402))
    verify_seal(ROOT / 'verification/swift-guarded-snapshot-host-account-inventory-independent',
                'a41ff779d707d246997ddcbb36d5b157edc1d6fc01be27b6f80dc210e3cf2295', (9,129818))
    manifest = load(PRODUCER / 'source-manifest.json')
    original = {p.relative_to(BASE).as_posix(): read(p) for p in sorted(BASE.rglob('*')) if p.is_file()}
    check('base source144', len(original) == 144)
    source = dict(original)
    profile = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    account = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
    source[profile] += b'\n\n' + read(BOOT/'driver.inc.rs') + b'\n\n' + read(PRODUCER/'entry.inc.rs')
    source[account] = read(PRODUCER/'host_account.rs')
    actual_members = [member(p,d) for p,d in sorted(source.items(),key=lambda x:Path(x[0]))]
    check('exact source145 member closure', len(actual_members) == 145 and actual_members == manifest['members'])
    check('exact source145 digest', sha(canonical(actual_members)) == manifest['source_tree_sha256'] == SOURCE_TREE)
    shapes = Shapes(source)
    inventory = load(PRODUCER/'caller-inventory.json')
    mir_roles = load(PRODUCER/'mir-roles.json')
    bodies = split_functions(read(PRODUCER/'entry-and-account.mir').decode())
    check('19 frozen MIR bodies', len(bodies) == len(inventory['functions']) == 19)
    check('396 frozen roles', sum(len(f['roles']) for f in inventory['functions']) == 396)
    sizes = inventory['actual_type_sizes']
    size_lookup = {}
    for ty, size in sizes.items():
        size_lookup[full_type_name(ty)] = size
    # Generic actual T and closure are already bound by independent diagnostics.
    selected = []
    for index, (body, recorded) in enumerate(zip(bodies, inventory['functions'])):
        check('frozen MIR body digest ' + str(index), sha(body.encode()) == recorded['sha256'] == mir_roles['functions'][index]['sha256'])
        check('frozen MIR header ' + str(index), body.splitlines()[0] == recorded['header'])
        if recorded['phase'] != 'P0-pre-existing-parent-account-bookkeeping':
            continue
        identity = function_id(recorded['header'])
        roles = {}
        for item in recorded['roles']:
            ty = item['concrete_production_type']
            leaves = shapes.shape(ty)
            size = item['bytes']
            # Leaves and native bytes are independent dimensions. This concrete
            # check allows byte charging as an additional conservative allowance.
            check('concrete leaves fit native extent or unit ' + identity + item['local'], leaves <= max(1,size))
            pointed = pointee_type(ty)
            pointed_bytes = 0
            pointed_leaves = 0
            if pointed:
                normal = full_type_name(pointed)
                check('measured concrete pointee ' + identity + item['local'], normal in size_lookup)
                pointed_bytes = size_lookup[normal]
                pointed_leaves = shapes.shape(pointed)
                check('pointee leaves fit concrete extent ' + identity + item['local'], pointed_leaves <= max(1,pointed_bytes))
            roles[item['local']] = {**item, 'scalar_leaves': leaves,
                                  'pointee_type': pointed, 'pointee_bytes': pointed_bytes,
                                  'pointee_scalar_leaves': pointed_leaves}
        graph = blocks(body)
        # Only the checked six-part loop has a back-edge. No per-function cap
        # is applied to a cyclic unknown graph.
        if identity == 'checked_components_v1':
            back_edges = [('bb23','bb4')]
        else:
            back_edges = []
        indegree = {b:0 for b in graph}
        for bid, block in graph.items():
            for successor in block['successors']:
                check('known MIR successor ' + identity + successor, successor in graph)
                if (bid,successor) not in back_edges:
                    indegree[successor] += 1
        queue = [b for b,n in indegree.items() if n==0]
        visited = []
        while queue:
            bid = queue.pop()
            visited.append(bid)
            for successor in graph[bid]['successors']:
                if (bid,successor) not in back_edges:
                    indegree[successor] -= 1
                    if indegree[successor] == 0:
                        queue.append(successor)
        check('only selected finite loop ' + identity, len(visited) == len(graph))
        source_units = native_bytes = 0
        call_counts = collections.Counter()
        for bid, block in graph.items():
            # Body blocks occur <=6; next and its discriminant <=7. All other
            # blocks (including failure, drop, cleanup) occur <=1 per invocation.
            if identity == 'checked_components_v1' and bid in ('bb4','bb5'):
                count = 7
            elif identity == 'checked_components_v1' and bid in ('bb7','bb9','bb10','bb11','bb13','bb14','bb15','bb16','bb17','bb20','bb21','bb22','bb23'):
                count = 6
            else:
                count = 1
            block['occurrence_bound'] = count
            block['source_action_units'] = 0
            block['native_sized_occurrence_bytes'] = 0
            for row in block['lines']:
                code = row['code']
                mentions = re.findall(r'\b_\d+\b', code)
                check('every operation local is measured ' + identity + code, set(mentions) <= set(roles))
                constants = constant_occurrences(code)
                # Count all punctuation in this superset of projection syntax;
                # type/generic/call punctuation is conservatively charged too.
                punctuation = sum(code.count(ch) for ch in '()[].*&') + len(re.findall(r'\bas\b', code))
                base_actions = 2 + punctuation
                scalar = 2 * sum(roles[m]['scalar_leaves'] + roles[m]['pointee_scalar_leaves'] for m in mentions)
                scalar += 2 * sum(c['scalar_leaves'] for c in constants)
                byte_count = 2 * sum(roles[m]['bytes'] + roles[m]['pointee_bytes'] for m in mentions)
                byte_count += 2 * sum(c['bytes'] for c in constants)
                # `return` implicitly reads the return place even when compiler
                # text names no operand. This is an additional explicit charge.
                if code == 'return;':
                    scalar += 2 * (roles['_0']['scalar_leaves'] + roles['_0']['pointee_scalar_leaves'])
                    byte_count += 2 * (roles['_0']['bytes'] + roles['_0']['pointee_bytes'])
                call = classify_call(code)
                row.update({'local_mentions': mentions, 'constants': constants,
                            'base_action_units': base_actions,
                            'scalar_fetch_store_units': scalar,
                            'source_action_units': base_actions+scalar,
                            'native_sized_occurrence_bytes': byte_count,
                            'call_cut': call})
                block['source_action_units'] += base_actions+scalar
                block['native_sized_occurrence_bytes'] += byte_count
                if call:
                    call_counts[call] += count
            source_units += count * block['source_action_units']
            native_bytes += count * block['native_sized_occurrence_bytes']
        # Entry parameters are separately charged even if they are only moved.
        entry_source = 2 + 2 * sum(r['scalar_leaves']+r['pointee_scalar_leaves'] for r in roles.values() if r['kind']=='parameter')
        entry_bytes = 2 * sum(r['bytes']+r['pointee_bytes'] for r in roles.values() if r['kind']=='parameter')
        source_units += entry_source
        native_bytes += entry_bytes
        selected.append({'id': identity, 'header': recorded['header'], 'MIR_sha256': recorded['sha256'],
                         'role_count': len(roles), 'logical_role_bytes': recorded['measured_logical_bytes'],
                         'roles': roles, 'blocks': graph, 'entry_source_action_units': entry_source,
                         'entry_native_sized_occurrence_bytes': entry_bytes,
                         'source_action_units_per_invocation': source_units,
                         'native_sized_occurrence_bytes_per_invocation': native_bytes,
                         'combined_surface_units_per_invocation': checked_add(source_units,native_bytes),
                         'calls_per_invocation_bound': dict(sorted(call_counts.items()))})
    check('15 exact P0 functions', len(selected) == 15)
    check('208 P0 roles', sum(f['role_count'] for f in selected) == 208)
    check('234375 P0 role bytes', sum(f['logical_role_bytes'] for f in selected) == 234375)
    paths = path_controls(selected)
    ownership = ownership_controls(selected)
    destructor_surface = drop_surface(selected)
    controls, witnesses = model_controls(selected)
    # A single bounded candidate envelope. These functions do not establish an
    # operational root route. I and U remain symbolic and ungrantable until an
    # exact source-reviewed root chooses them.
    counts = {f['id']: 1 for f in selected if f['id'] not in ('inspect_v1','usage_v1')}
    MIR_fixed_source = sum(counts.get(f['id'],0)*f['source_action_units_per_invocation'] for f in selected)
    MIR_fixed_native = sum(counts.get(f['id'],0)*f['native_sized_occurrence_bytes_per_invocation'] for f in selected)
    fixed_source = checked_add(MIR_fixed_source,destructor_surface['source_action_units'])
    fixed_native = checked_add(MIR_fixed_native,destructor_surface['native_sized_occurrence_byte_allowance'])
    coefficients = {f['id']:f['combined_surface_units_per_invocation'] for f in selected if f['id'] in ('inspect_v1','usage_v1')}
    required_terms = {name:1 for name in ['P1_setup','P1_loader_and_original_validation','P2_arguments','P3_pre_store_shell',
                'P4_selected_route','P5_owned_return','P5_actual_payload_destruction',
                'P0_unselected_root_route','P0_fixture_binding_and_backing','P0_dynamic_backing']}
    fixed = checked_add(fixed_source,fixed_native)
    for name in required_terms:
        for invalid in [None,0,-1,U64_MAX+1]:
            terms = dict(required_terms); terms[name] = invalid
            check('nonzero missing cut refuses '+str((name,invalid)),
                  interface_evaluate(fixed,coefficients,0,0,terms,SOURCE_TREE).get('refusal') == 'MissingRequiredTerm')
    for invalid in [None,-1,U64_MAX+1]:
        check('unknown I bound refuses '+str(invalid),
              interface_evaluate(fixed,coefficients,invalid,0,required_terms,SOURCE_TREE).get('refusal') == 'UnknownOrInvalidOccurrenceBound')
        check('unknown U bound refuses '+str(invalid),
              interface_evaluate(fixed,coefficients,0,invalid,required_terms,SOURCE_TREE).get('refusal') == 'UnknownOrInvalidOccurrenceBound')
    check('new composed source cannot inherit quote',
          interface_evaluate(fixed,coefficients,0,0,required_terms,'combined-source146').get('refusal') == 'SourceRebindingRequired')
    check('coefficient multiplication overflow refuses',
          interface_evaluate(fixed,coefficients,U64_MAX,0,required_terms,SOURCE_TREE).get('refusal') == 'CostOverflow')
    check('cut addition overflow refuses',
          interface_evaluate(fixed,coefficients,0,0,{**required_terms,'P0_unselected_root_route':U64_MAX},SOURCE_TREE).get('refusal') == 'CostOverflow')
    check('finite arithmetic success confers no grant',
          interface_evaluate(fixed,coefficients,0,0,required_terms,SOURCE_TREE).get('operational_grant') is False)
    try:
        classify_call('_0 = unreviewed_callback_v2(move _1) -> [return: bb1, unwind continue];')
    except AssertionError:
        check('unknown callee rejected rather than assigned zero',True)
    else:
        raise AssertionError('unknown callee accepted')
    try:
        Shapes(source).shape('UnreviewedParentPayloadV2')
    except AssertionError:
        check('unknown concrete payload rejected rather than assigned zero',True)
    else:
        raise AssertionError('unknown concrete payload accepted')
    summary = {
        'schema': 1, 'status': 'bounded-private-P0-source-surface-proposal-only',
        'source_binding': {'members':145,'sha256':SOURCE_TREE,
                           'basis':'funding144 + bootstrap + account include; distinct from combined145',
                           'final_composition_rebinding_required':True},
        'scope': {'functions':15,'roles':208,'logical_role_bytes':234375,
                  'compiler_run':False,'product_code_run':False,'native_runtime_run':False},
        'unit': {'source':'2 per MIR operation/control/lifetime marker + projection punctuation superset + 2 per concrete scalar leaf for every operand/destination/entry parameter and implicit return; full pointee surcharge on every reference mention',
                 'native':'2 * concrete measured native-sized extent for every local/constant operand or destination/entry/return occurrence, plus full measured pointee extent on each reference mention; a conservative logical work allowance, not physical copying or allocated storage',
                 'combined':'source_action_units + native_sized_occurrence_byte_allowance',
                 'enums':'1 discriminant + max inhabited payload leaves; all written alternative MIR blocks separately charged',
                 'std':'closed named source-level primitive/callsite actions only; private std/kernel/allocator/retry work excluded from this inherited unit'},
        'counts_per_one_fixture_candidate_envelope':counts,
        'unselected_symbolic_counts':{'I':'inspect_v1 invocations','U':'usage_v1 invocations'},
        'fixed_source_action_units':fixed_source,
        'fixed_native_sized_occurrence_byte_allowance':fixed_native,
        'fixed_combined_surface_units':checked_add(fixed_source,fixed_native),
        'fixed_MIR_surface_before_drop_addendum':{'source_action_units':MIR_fixed_source,
                                                'native_sized_occurrence_byte_allowance':MIR_fixed_native,
                                                'combined_surface_units':MIR_fixed_source+MIR_fixed_native},
        'finite_drop_surface_addendum':{k:destructor_surface[k] for k in ['source_action_units','native_sized_occurrence_byte_allowance','combined_surface_units']},
        'symbolic_coefficients':{f['id']:{'source_action_units':f['source_action_units_per_invocation'],
                                        'native_sized_occurrence_byte_allowance':f['native_sized_occurrence_bytes_per_invocation'],
                                        'combined_surface_units':f['combined_surface_units_per_invocation']}
                                 for f in selected if f['id'] in ('inspect_v1','usage_v1')},
        'tables':{f['id']:{k:f[k] for k in ['role_count','logical_role_bytes','source_action_units_per_invocation',
                                          'native_sized_occurrence_bytes_per_invocation','combined_surface_units_per_invocation','calls_per_invocation_bound']}
                  for f in selected},
        'required_nonzero_or_explicitly_priced_cut_terms':[
            {'name':'W_P1_P5_callback_body','owner_phase':'P1..P5','reason':'run_prepaid_fixture_v1 body, fixture setup, loader + original validation, argument production, shared shell, selected route and owned outcomes; not paid by this P0 surface'},
            {'name':'W_P5_actual_payload_destruction','owner_phase':'P5','reason':'exact OwnedFixtureOutcomeV1 transitive File/error/diagnostic/cancellation owners, custom and automatic payload destructors on normal/ordinary-drop/unwind paths; not a token cost'},
            {'name':'W_P0_unselected_root_route','owner_phase':'P0','reason':'trusted policy/authority creation, quote-component production/callsite, account constructor caller, I/U bounds, token selection and caller-owned argument/return/local places; no selected source currently connects them'},
            {'name':'W_P0_fixture_binding_and_backing','owner_phase':'P0','reason':'immutable paths/claims/budgets and source/tool/fixture identity/backing construction and validation before grant'},
            {'name':'W_P0_dynamic_backing','owner_phase':'P0','reason':'all eventual P0-owned dynamic backing and native byte operations outside these bodies; absent selection is unknown, not zero'},
        ],
        'required_child_components':['P1_setup','P1_loader_and_original_validation','P2_arguments','P3_pre_store_shell','P4_selected_route','P5_owned_return_and_destruction'],
        'future_fixture_geometry':{'selected_in_separate_root_receipt':True,
                                   'historical_source_bytes':1947,
                                   'historical_source_sha256':'9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806',
                                   'used_to_qualify_this_P0_component':False,
                                   'new_source146_build_session_process_authority_still_pending':True},
        'operational_grant_available':False,'complete_P0_allocation_or_work':False,
        'complete_host_quote':False,'selected_policy':False,'native_OTA_FieldLog_GA_authority':False,
        'finite_controls':len(controls), 'bounded_CFG_terminal_paths':sum(p['bounded_terminal_paths'] for p in paths.values()),
        'ownership_controls':len(ownership),'input_count':len(inputs),
    }
    return {'summary.json':summary,
            'operation-ledger.json':{'schema':1,'source_tree_sha256':SOURCE_TREE,'functions':selected},
            'scalar-shapes.json':{'schema':1,'rule':'opaque std=1; struct=sum; enum=1+max payload; fixed array=count*element; unit/!=1; source definitions read as data only',
                                  'concrete_owned_payload_leaves':shapes.shape('OwnedFixtureOutcomeV1'),
                                  'definitions':shapes.used,'type_leaves':shapes.cache},
            'countermodels.json':{'schema':1,'controls':controls,'concrete_witnesses':witnesses},
            'path-review.json':{'schema':1,'source_tree_sha256':SOURCE_TREE,'bounded_CFG_paths':paths,
                                'ownership_controls':ownership,
                                'quote_iteration_contract':'one [CostV1;6] move into closed array iterator; <=6 Some yields and <=7 next calls; all non-loop graphs acyclic',
                                'ordinary_Drop_bound':1,
                                'payload_destructor_bound':'<=1 actual payload destruction across explicit/ordinary/cleanup alternatives; ledger cut-site union separately overcounts both written sites',
                                'generated_drop_boundary':'finite source-visible primitive drop schema priced in drop-surface.json; only authored P0 Drop body <=1 already included; private std/compiler instructions excluded by inherited unit'},
            'drop-surface.json':destructor_surface,
            'cost-interface.json':{'schema':1,'status':'proposal-expression-only-no-root-policy',
                                   'component':'W_P0_account_surface_v1',
                                   'source_tree_sha256':SOURCE_TREE,'source_members':145,
                                   'combined_expression':f'{fixed} + {coefficients["inspect_v1"]}*I + {coefficients["usage_v1"]}*U',
                                   'I_U':'unknown until exact root source fixes finite occurrence counts; neither can default to zero',
                                   'entry_occurrence_envelope':counts,
                                   'source_and_native_dimensions':{'fixed_source_action_units':fixed_source,
                                                                   'fixed_native_sized_occurrence_byte_allowance':fixed_native},
                                   'separate_required_terms':list(required_terms),
                                   'P5_component_composition':'P5_owned_return + P5_actual_payload_destruction, both explicit and positive, checked-add; together they form the sixth child component',
                                   'complete_host_expression':'P0_account_surface + P0_unselected_root_route + P0_fixture_binding_and_backing + P0_dynamic_backing + six explicit child components',
                                   'P0_storage':'234375 logical source-object inventory bytes is not a complete P0 storage quote; exact caller frames, lifetime overlap, binding/native/dynamic backing and root provisioning remain unselected',
                                   'required_checks':['all terms known and positive or separately reviewed as inapplicable; omitted cost never zero',
                                                      'I/U exact finite source bounds, no arbitrary repeated inspection',
                                                      'all multiply/add operations checked in u64; overflow refuses before use',
                                                      'final source146 manifest/layout/ownership/role/source-work/tool/fixture identities rebind',
                                                      'new root policy and any changed constructor/quote/caller source independently reviewed',
                                                      'P0 provisioned before quote/account/child grant and retained through token release',
                                                      'P0 work is never credited to or refunded from child work/storage'],
                                   'root_constructors_currently_pending':True,'operational_grant':False},
            'input-custody.json':{'schema':1,'source_tree_sha256':SOURCE_TREE,'files':dict(sorted(inputs.items()))},
            'results.json':{'schema':1,'passed':True,'checks':len(checks),'check_labels':checks,
                            'python':platform.python_version(),'compiler_invoked':False,
                            'product_invoked':False,'native_invoked':False}}


def main():
    outputs = derive()
    if '--check-only' in sys.argv:
        for path,value in outputs.items():
            expected = (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
            if (HERE/path).read_bytes() != expected:
                raise AssertionError('frozen output mismatch: '+path)
        print(json.dumps({'passed':True,'checks':len(checks),'mode':'check-only','source_tree_sha256':SOURCE_TREE}))
    else:
        for path,value in outputs.items():
            (HERE/path).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
        print(json.dumps({'passed':True,'checks':len(checks),'source_tree_sha256':SOURCE_TREE,
                          'outputs':list(outputs)}))


if __name__ == '__main__':
    main()
