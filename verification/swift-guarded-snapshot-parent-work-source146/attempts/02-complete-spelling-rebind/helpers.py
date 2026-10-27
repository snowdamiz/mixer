"""Pure bounded helpers copied from the accepted independent source145 review.
No audit, producer, compiler, product or file access is executed on import.
"""
import collections
import hashlib
import json
import re
checks = []
def require(label, ok):
    if not ok:
        raise AssertionError(label)
    checks.append(label)

def sha(b):
    return hashlib.sha256(b).hexdigest()

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
