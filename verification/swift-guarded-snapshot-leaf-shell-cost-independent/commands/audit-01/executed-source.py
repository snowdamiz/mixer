#!/usr/bin/env python3
"""Independent byte/source/MIR audit. No compiler or product runtime is invoked.

All discovery and arithmetic below are owned review code. The three reviewed
pure evaluator functions are AST-selected only for adversarial interface tests;
no producer module is imported and no producer collector is run.
"""
import ast
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-leaf-shell-cost'
COMPOSE = ROOT / 'verification/swift-guarded-snapshot-host-composition'
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-leaf-shell-cost-independent-release.json'
RELEASE_SHA = 'd4ca04dc54c69655d519a0ce62f8ce3e2734314c79db9af25c743a9b2bcbc877'
SEAL_SHA = '10321f6bdadbe8ff193d553063b978e59857f7390e243e63054f0d4e1997cd57'
TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
U64 = (1 << 64) - 1
CHECKS = []
INPUTS = {}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def need(label, value):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def read(path):
    need('regular non-symlink input ' + str(path.relative_to(ROOT)), path.is_file() and not path.is_symlink())
    raw = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': digest(raw)}
    return raw


def load(path):
    return json.loads(read(path))


def verify_packet(folder, expected, count=None):
    raw = read(folder / 'seal.json')
    need('seal identity ' + folder.name, digest(raw) == expected)
    seal = json.loads(raw)
    rows = seal['members']
    paths = [r['path'] for r in rows]
    need('unique relative packet paths ' + folder.name, len(paths) == len(set(paths)) and all(not Path(p).is_absolute() and '..' not in Path(p).parts for p in paths))
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != folder / 'seal.json'}
    need('complete packet closure ' + folder.name, set(paths) == actual)
    need('packet member count ' + folder.name, len(rows) == seal['member_count'] and (count is None or count == len(rows)))
    total = 0
    for row in rows:
        p = folder / row['path']
        need('no symlink packet ancestors ' + str(p.relative_to(ROOT)), all(not parent.is_symlink() for parent in [p, *p.parents] if parent != ROOT and ROOT in parent.parents))
        b = read(p)
        need('sealed member ' + str(p.relative_to(ROOT)), len(b) == row['bytes'] and digest(b) == row['sha256'])
        total += len(b)
    need('packet byte total ' + folder.name, total == seal['total_bytes'])
    return {'path': str(folder.relative_to(ROOT)), 'seal_sha256': expected, 'members': len(rows), 'bytes': total}


def lexical_mask(text, strings=True):
    """Preserve offsets/newlines while masking nested comments and literals."""
    out = list(text)
    i = 0
    while i < len(text):
        end = None
        if text.startswith('//', i):
            end = text.find('\n', i)
            if end < 0:
                end = len(text)
        elif text.startswith('/*', i):
            j, depth = i + 2, 1
            while depth and j < len(text):
                if text.startswith('/*', j):
                    depth += 1
                    j += 2
                elif text.startswith('*/', j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            if depth:
                raise ValueError('unterminated Rust comment')
            end = j
        elif strings:
            raw = re.match(r'(?:br|r)(#*)"', text[i:])
            if raw:
                terminator = '"' + raw[1]
                j = text.find(terminator, i + len(raw[0]))
                if j < 0:
                    raise ValueError('unterminated raw string')
                end = j + len(terminator)
            elif text[i] == '"':
                j = i + 1
                while j < len(text):
                    if text[j] == '\\':
                        j += 2
                    elif text[j] == '"':
                        end = j + 1
                        break
                    else:
                        j += 1
                if end is None:
                    raise ValueError('unterminated string')
            elif text[i] == "'":
                char = re.match(r"'(?:\\(?:.|u\{[0-9A-Fa-f_]+\})|[^'\\\n])'", text[i:])
                if char:
                    end = i + len(char[0])
        if end is not None:
            for k in range(i, end):
                if out[k] != '\n':
                    out[k] = ' '
            i = end
        else:
            i += 1
    return ''.join(out)


def end_brace(mask, start, left='{', right='}'):
    if mask[start] != left:
        raise ValueError('bad balanced start')
    depth = 0
    for i in range(start, len(mask)):
        if mask[i] == left:
            depth += 1
        elif mask[i] == right:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('unclosed balanced extent')


def pieces(text, sep=','):
    stack, begin, result = [], 0, []
    pairs = {'<': '>', '(': ')', '[': ']', '{': '}'}
    for i, ch in enumerate(text):
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in '>)]}':
            if not stack or stack.pop() != ch:
                raise ValueError('unbalanced type ' + text)
        elif ch == sep and not stack:
            result.append(text[begin:i].strip())
            begin = i + 1
    if stack:
        raise ValueError('unclosed type ' + text)
    result.append(text[begin:].strip())
    return [s for s in result if s]


def canon_type(ty):
    ty = re.sub(r"&\s*'[A-Za-z_]\w*\s*", '&', ty)
    ty = re.sub(r'\b\w+::', '', ty)
    return re.sub(r'\s+', ' ', ty).strip().replace('SnapshotClaimsV1', 'UnverifiedProfileDigestBytesV1')


def remove_attrs(text):
    attrs = []
    text = text.strip()
    while text.startswith('#['):
        j = end_brace(text, 1, '[', ']')
        attrs.append(text[2:j])
        text = text[j+1:].strip()
    return attrs, text


def named_fields(body):
    result = []
    for part in pieces(body):
        attrs, part = remove_attrs(part)
        if 'cfg(test)' in attrs:
            continue
        part = re.sub(r'^pub(?:\([^)]*\))?\s+', '', part)
        m = re.fullmatch(r'\w+\s*:\s*(.+)', part, re.S)
        if not m:
            raise ValueError('unrecognized source field ' + part)
        result.append(m[1].strip())
    return result


class Types:
    """Resolve concrete inline source and finite reference closure separately."""
    PRIMS = {'()', '!', 'u8', 'u16', 'u32', 'u64', 'u128', 'i8', 'i16', 'i32', 'i64', 'i128', 'usize', 'isize', 'bool', 'f32', 'f64', 'char', 'str'}
    OPAQUE = {'File', 'Error', 'Cancellation', 'Instant', 'Duration', 'Path', 'OpenOptions', 'Vec', 'String', 'Arc', 'Rc', 'Box', 'IntoIter', 'Enumerate'}
    ALIASES = {'AError': 'SnapshotAdmissionErrorV1', 'Stop': 'SnapshotStopV1', 'SnapshotClaimsV1': 'UnverifiedProfileDigestBytesV1', 'SwiftMetadata': 'Metadata<SwiftDeclaration>'}
    ROUTES = {'Resource': 'src/experimental/mod.rs', 'Policy': 'src/experimental/policy.rs', 'Buffer': 'src/experimental/account.rs', 'Metadata': 'src/experimental/metadata.rs', 'Limits': 'src/lib.rs', 'Span': 'src/experimental_wasi/mod.rs'}

    def __init__(self, sources):
        self.defs = collections.defaultdict(list)
        self.seen = {}
        for path, raw in sources.items():
            if not path.endswith('.rs') or '/test' in path or path.endswith('_tests.rs'):
                continue
            original = raw.decode()
            mask = lexical_mask(original)
            for m in re.finditer(r'\b(struct|enum)\s+(\w+)\b', mask):
                i = m.end()
                while i < len(mask) and mask[i].isspace():
                    i += 1
                if mask[i:i+1] == '<':
                    i = end_brace(mask, i, '<', '>') + 1
                    while mask[i].isspace():
                        i += 1
                if mask[i:i+1] not in ('{', '('):
                    continue
                left, right = ('(', ')') if mask[i] == '(' else ('{', '}')
                end = end_brace(mask, i, left, right)
                body = lexical_mask(original[i+1:end], strings=False)
                if left == '(':
                    fields = [re.sub(r'^pub(?:\([^)]*\))?\s+', '', f) for f in pieces(body)]
                    detail = {'kind': 'tuple-struct', 'fields': fields}
                elif m[1] == 'struct':
                    detail = {'kind': 'struct', 'fields': named_fields(body)}
                else:
                    variants = []
                    for part in pieces(body):
                        attrs, part = remove_attrs(part)
                        if 'cfg(test)' in attrs:
                            continue
                        name = re.match(r'\w+', part)
                        if name is None:
                            raise ValueError('unrecognized enum variant')
                        rest = part[name.end():].strip()
                        if rest.startswith('('):
                            fs = pieces(rest[1:end_brace(rest, 0, '(', ')')])
                        elif rest.startswith('{'):
                            fs = named_fields(rest[1:end_brace(rest, 0)])
                        elif not rest or rest.startswith('='):
                            fs = []
                        else:
                            raise ValueError('unrecognized enum payload ' + rest)
                        variants.append({'name': name[0], 'fields': fs})
                    detail = {'kind': 'enum', 'variants': variants}
                detail.update(path=path, start=m.start(), end=end+1)
                self.defs[m[2]].append(detail)

    def resolve(self, ty):
        ty = self.ALIASES.get(ty.strip(), ty.strip())
        head = ty.split('<', 1)[0]
        name = head.rsplit('::', 1)[-1]
        args = pieces(ty[len(head)+1:-1]) if '<' in ty and ty.endswith('>') else []
        return ty, name, args

    def declaration(self, ty):
        ty, name, args = self.resolve(ty)
        rows = self.defs.get(name, [])
        route = self.ROUTES.get(name)
        if name == 'Resource' and ty.startswith('experimental_wasi::'):
            route = 'src/experimental_wasi/mod.rs'
        if route:
            rows = [r for r in rows if r['path'] == route]
        if len(rows) != 1:
            raise ValueError('unknown/ambiguous actual source type ' + ty)
        detail = dict(rows[0])
        def subst(field):
            if name == 'Buffer':
                field = re.sub(r'\bResource\b', 'experimental::Resource', field)
            if name == 'Metadata':
                if len(args) != 1:
                    raise ValueError('unbound Metadata')
                field = re.sub(r'\bD\b', args[0], field)
            if name == 'WasiFailure':
                field = re.sub(r'\bResource\b', 'experimental_wasi::Resource', field)
            return field
        detail['fields'] = [subst(f) for f in detail.get('fields', [])]
        detail['variants'] = [dict(v, fields=[subst(f) for f in v['fields']]) for v in detail.get('variants', [])]
        return detail

    def inline(self, ty, past=()):
        ty, name, args = self.resolve(ty)
        if ty in past:
            raise ValueError('recursive by-value type')
        past = past + (ty,)
        if ty.startswith(('&', '*const ', '*mut ')) or ty in self.PRIMS:
            return 1
        if ty.startswith('['):
            element, count = pieces(ty[1:-1], ';')
            count = int(count.replace('_', ''))
            if count < 0:
                raise ValueError('negative array')
            return count * self.inline(element, past)
        if ty.startswith('('):
            return sum(self.inline(v, past) for v in pieces(ty[1:-1])) or 1
        if name in {'Option', 'Result', 'ControlFlow'}:
            if len(args) != (1 if name == 'Option' else 2):
                raise ValueError('generic variant arity')
            return 1 + max([0] + [self.inline(t, past) for t in args])
        if name == 'Infallible':
            return 0
        if name == 'Cell':
            return self.inline(args[0], past)
        # Cancellation is also source-defined but its one Arc carrier is opaque.
        if name in self.OPAQUE:
            return 1
        d = self.declaration(ty)
        if d['kind'] == 'enum':
            result = 1 + max([0] + [sum(self.inline(f, past) for f in v['fields']) for v in d['variants']])
        else:
            result = sum(self.inline(f, past) for f in d['fields']) or 1
        self.seen[ty] = dict(d, scalar_leaves=result)
        return result

    def refs(self, ty, past=()):
        ty, name, args = self.resolve(ty)
        key = canon_type(ty)
        if key in past:
            raise ValueError('recursive reference closure')
        past = past + (key,)
        if ty.startswith('&'):
            target = re.sub(r"^&\s*(?:'[A-Za-z_]\w*\s*)?(?:mut\s+)?", '', ty)
            if target == 'str' or (target.startswith('[') and ';' not in target):
                return 0, collections.Counter(), collections.Counter({canon_type(target): 1})
            n, refs, unsized = self.refs(target, past)
            return self.inline(target) + n, refs + collections.Counter({canon_type(target): 1}), unsized
        if ty.startswith('['):
            element, count = pieces(ty[1:-1], ';')
            count = int(count.replace('_', ''))
            if count < 0 or count > 100000:
                raise ValueError('bad array reference bound')
            n, refs, unsized = self.refs(element, past)
            return count*n, collections.Counter({k: count*v for k,v in refs.items()}), collections.Counter({k: count*v for k,v in unsized.items()})
        if ty.startswith('('):
            children = pieces(ty[1:-1])
        elif name in {'Option', 'Result', 'ControlFlow'}:
            children = args
        elif name in self.OPAQUE | {'Cell', 'Infallible'} or ty in self.PRIMS:
            children = []
        else:
            d = self.declaration(ty)
            children = d['fields'] + [f for v in d['variants'] for f in v['fields']]
        n, refs, unsized = 0, collections.Counter(), collections.Counter()
        for child in children:
            a, b, c = self.refs(child, past)
            n += a
            refs.update(b)
            unsized.update(c)
        return n, refs, unsized


def mir_functions(raw):
    lines = raw.splitlines(keepends=True)
    result, active = [], None
    for line in lines:
        if line.startswith('fn '):
            if active is not None:
                raise ValueError('nested/incomplete MIR fn')
            active = [line]
        elif active is not None:
            active.append(line)
            if line == '}\n':
                result.append(''.join(active))
                active = None
    if active is not None:
        raise ValueError('incomplete MIR fn')
    return result


def select_functions(all_bodies):
    output = {}
    for body in all_bodies:
        header = body.splitlines()[0]
        key = None
        if header.startswith('fn run_one_loaded_fixture_v1('):
            key = 'leaf'
        elif header.startswith('fn control::<impl at '):
            for name, label in [('adopt_snapshot_body_v1', 'adopt_snapshot'), ('construct_v1', 'construct'), ('outer_v1', 'outer'), ('finish_v1', 'finish')]:
                if '>::' + name + '(' in header:
                    key = label
        elif header.startswith('fn retained_profile_loader_v1::<impl at '):
            if '>::into_snapshot_scope_v1(' in header:
                key = 'into_scope'
            elif '>::into_adoption_body_v1(_1: SelectedValidatedProfileV1)' in header:
                key = 'selected_into_body'
            elif '>::into_adoption_body_v1(_1: SelectedSnapshotBodyV1)' in header:
                key = 'snapshot_into_body'
        if key:
            if key in output:
                raise ValueError('ambiguous concrete MIR body ' + key)
            output[key] = body
    if set(output) != {'leaf', 'adopt_snapshot', 'construct', 'outer', 'finish', 'snapshot_into_body', 'selected_into_body', 'into_scope'}:
        raise ValueError('missing concrete MIR body')
    return output


def roles_of(body):
    header = body.splitlines()[0]
    args = header[header.index('(')+1:header.rfind(') -> ')]
    output = {}
    for arg in pieces(args):
        name, ty = arg.split(': ', 1)
        output[name] = {'compiler_type': ty, 'kind': 'parameter'}
    for line in body.splitlines()[1:]:
        code = lexical_mask(line, strings=False).strip()
        m = re.fullmatch(r'let (?:mut )?(_\d+): (.*);', code)
        if m:
            if m[1] in output:
                raise ValueError('redeclared role')
            output[m[1]] = {'compiler_type': m[2], 'kind': 'return' if m[1] == '_0' else 'local'}
    return output


def blocks_of(body):
    output, current = {}, None
    for line_no, line in enumerate(body.splitlines(), 1):
        code = lexical_mask(line, strings=False).rstrip()
        m = re.fullmatch(r'    (bb\d+)( \(cleanup\))?: \{', code)
        if m:
            if current or m[1] in output:
                raise ValueError('overlapping/duplicate MIR block')
            current = m[1]
            output[current] = {'cleanup': bool(m[2]), 'operations': []}
        elif code == '    }':
            current = None
        elif current and code.strip():
            output[current]['operations'].append((line_no, code.strip()))
    return output


def terminal_paths(blocks):
    paths = []
    todo = [('bb0', [])]
    while todo:
        current, previous = todo.pop()
        if current in previous or current not in blocks:
            raise ValueError('cyclic/incomplete MIR CFG')
        path = previous + [current]
        final = blocks[current]['operations'][-1][1]
        targets = sorted(set(re.findall(r'\bbb\d+\b', final)))
        terminal = final in {'return;', 'resume;', 'unreachable;'} or 'unwind continue' in final or 'unwind terminate' in final
        if not targets and not terminal:
            raise ValueError('unknown MIR terminator')
        if terminal:
            paths.append(path)
        todo.extend((target, path) for target in targets)
        if len(paths) > 100000 or len(path) > 1000:
            raise ValueError('bounded CFG budget exceeded')
    return paths


def literal_constants(code):
    result = []
    for m in re.finditer(r'\bconst\s+', code):
        rest = code[m.end():]
        if rest.startswith('"'):
            token = re.match(r'"(?:\\.|[^"\\])*"', rest)
            if not token:
                raise ValueError('unrecognized literal')
            value = json.loads(token[0])
            n = len(value.encode())
            result.append({'text': token[0], 'scalar_leaves': 1+n, 'native_bytes': None, 'string_bytes': n})
        else:
            token = re.match(r'(?:true|false)\b|\(\)', rest)
            if not token:
                raise ValueError('unsupported constant')
            result.append({'text': token[0], 'scalar_leaves': 1, 'native_bytes': 0 if token[0] == '()' else 1, 'string_bytes': 0})
    return result


INTERNAL = {
    'SelectedValidatedProfileV1::into_snapshot_scope_v1': 'into_scope',
    'SelectedValidatedProfileV1::into_adoption_body_v1': 'selected_into_body',
    'SelectedSnapshotBodyV1::into_adoption_body_v1': 'snapshot_into_body',
    'control::RuntimeControl::adopt_snapshot_body_v1': 'adopt_snapshot',
    'SnapshotScopeV1::construct_v1': 'construct',
    'SnapshotRunV1::outer_v1': 'outer',
    'SnapshotRunV1::finish_v1': 'finish',
}


def classify(code):
    """Exhaustive selected grammar; unknown statements do not get generic credit."""
    if code in {'return;', 'resume;', 'unreachable;'}:
        return 'terminal'
    if re.fullmatch(r'Storage(?:Live|Dead)\(_\d+\);', code):
        return 'storage'
    if re.fullmatch(r'goto -> bb\d+;', code):
        return 'goto'
    if code.startswith('switchInt(') and ' -> [' in code:
        return 'switch'
    if code.startswith('drop(') and ' -> [' in code:
        return 'drop'
    if not re.match(r'^_\d+ = ', code):
        raise ValueError('unsupported selected MIR operation ' + code)
    rhs = code.split(' = ', 1)[1]
    if ' -> [' in rhs:
        return 'call'
    if not rhs.endswith(';'):
        raise ValueError('incomplete assignment')
    if rhs.startswith(('move ', 'copy ', 'const ', '&', 'no_retag copy ')) or rhs == '();':
        return 'transfer'
    if rhs.startswith('discriminant('):
        return 'discriminant'
    if rhs.startswith(('Result::<', 'Option::<')) or rhs.startswith(('SnapshotScopeV1 {', "SnapshotScopeBorrowV1::<'_> {", 'SnapshotRunV1 {', 'SnapshotScopeFinishV1 {', 'AdoptionBodyV1 {', 'SelectedSnapshotBodyV1(')):
        return 'aggregate'
    raise ValueError('unsupported RHS ' + rhs)


def cut_of(code, roles):
    kind = classify(code)
    if kind == 'drop':
        operand = code[5:code.index(' -> [')-1]
        local = re.search(r'\b_\d+\b', operand)[0]
        return {'kind': 'required-drop-payload', 'key': 'drop_payload::' + canon_type(roles[local]['compiler_type']), 'operand': operand}
    if kind != 'call':
        return None
    expr = code.split(' = ', 1)[1].split(' -> [', 1)[0]
    callee = expr[:expr.rfind('(')]
    if callee in INTERNAL:
        return {'kind': 'included-source-body', 'key': INTERNAL[callee], 'callee': callee}
    if callee == 'control::RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>':
        return {'kind': 'required-core-split', 'key': 'adopt_body_core_v1', 'callee': callee, 'split': ['core_before_fixed_store', 'core_fixed_store_and_after']}
    return {'kind': 'required-callee', 'key': 'callee::' + callee, 'callee': callee}


def operation_of(code, roles):
    classify(code)
    mentions = re.findall(r'\b_\d+\b', code) + (['_0'] if code == 'return;' else [])
    if set(mentions) - set(roles):
        raise ValueError('unbound role')
    constants = literal_constants(code)
    base = 2 + sum(code.count(ch) for ch in '()[].*&') + len(re.findall(r'\bas\b', code))
    scalar = 2 * sum(roles[r]['scalar_leaves'] + roles[r]['pointee_scalar_leaves'] for r in mentions) + 2 * sum(c['scalar_leaves'] for c in constants)
    native, unsized, known = collections.Counter(), collections.Counter(), 0
    for role in mentions:
        d = roles[role]
        native[canon_type(d['compiler_type'])] += 2
        native.update({k: 2*v for k,v in d['pointee_types'].items()})
        unsized.update({k: 2*v for k,v in d['unsized_pointees'].items()})
    for c in constants:
        if c['native_bytes'] is None:
            native['&str'] += 2
            known += 2*c['string_bytes']
        else:
            known += 2*c['native_bytes']
    return {'code': code, 'local_mentions': mentions, 'constants': constants, 'base_action_units': base, 'scalar_fetch_store_units': scalar, 'source_action_units': base+scalar, 'native_type_coefficients': dict(native), 'known_constant_bytes': known, 'unsized_coefficients': dict(unsized), 'cut': cut_of(code, roles)}


def source_function(sources, path, name, index=0):
    text = sources[path].decode()
    mask = lexical_mask(text)
    matches = list(re.finditer(r'\bfn\s+' + name + r'\b', mask))
    if len(matches) <= index:
        raise ValueError('missing source function')
    m = matches[index]
    brace = mask.index('{', m.end())
    end = end_brace(mask, brace) + 1
    fragment = text[m.start():end]
    return {'path': path, 'line_start': text[:m.start()].count('\n')+1, 'line_end': text[:end].count('\n')+1, 'source_function_bytes': len(fragment.encode()), 'source_function_sha256': digest(fragment.encode()), 'signature': text[m.start():brace].strip()}, fragment


def checked_total(interface, sizes, cuts, unsized):
    def valid(value, positive=False):
        if type(value) is not int or value < (1 if positive else 0) or value > U64:
            raise ValueError('not checked u64')
        return value
    values = [valid(interface['fixed_source_action_units']), valid(interface['known_native_occurrence_bytes'])]
    for name, coefficient in interface['missing_native_occurrence_coefficients'].items():
        values.append(valid(coefficient*valid(sizes.get(name), True)))
    for name, coefficient in interface['required_nonzero_callee_drop_and_backing_cuts'].items():
        values.append(valid(coefficient*valid(cuts.get(name), True)))
    for name, coefficient in interface['unsized_source_and_native_byte_coefficients'].items():
        values.append(valid(2*coefficient*valid(unsized.get(name), True)))
    return valid(sum(values))


def reject(label, function, *args):
    try:
        function(*args)
    except (ValueError, AssertionError):
        CHECKS.append(label)
        return
    raise AssertionError('did not refuse ' + label)


def main():
    need('root release sha', digest(read(RELEASE)) == RELEASE_SHA)
    release = load(RELEASE)
    need('release source/tree/owner', release['source_tree_sha256'] == TREE and release['review_ownership'] == str(HERE.relative_to(ROOT)))
    packets = [verify_packet(PRODUCER, SEAL_SHA, 37)]
    need('released exact totals', packets[0]['bytes'] == 7435220 and release['bytes_verified'] == 7435220)
    custody = load(PRODUCER / 'input-custody.json')
    for row in custody['seals']:
        packets.append(verify_packet(ROOT / row['path'], row['seal_sha256'], row['members']))
    for path, expected in custody['inputs'].items():
        b = read(ROOT / path)
        need('producer frozen input rehashed ' + path, digest(b) == expected['sha256'] and len(b) == expected['bytes'])
    for row in custody['acceptance_bindings']:
        p = ROOT / 'verification/swift-semantic-adapter-root-review' / row['path']
        need('accepted dependency binding ' + row['path'], digest(read(p)) == row['sha256'])
    manifest = load(PRODUCER / 'source-manifest.json')
    need('actual146 manifest', manifest['member_count'] == 146 and len(manifest['members']) == 146 and digest(canon(manifest['members'])) == TREE)
    need('same composed manifest', read(PRODUCER / 'source-manifest.json') == read(COMPOSE / 'source-manifest.json'))
    sources = {}
    for row in manifest['members']:
        path = row['path']
        overlay = COMPOSE / 'overlay/vm' / path
        raw = read(overlay if overlay.exists() else BASE / path)
        need('actual146 concrete member ' + path, len(raw) == row['bytes'] and digest(raw) == row['sha256'] and path not in sources)
        sources[path] = raw
    compiler = load(ROOT / 'verification/swift-guarded-snapshot-loader-work-source146/compiler-receipt.json')
    need('retained compile identity', compiler['source_tree_sha256'] == TREE and compiler['source_manifest_sha256'] == digest(read(PRODUCER / 'source-manifest.json')) and compiler['exit_code'] == 0 and not compiler['product_runtime'] and not compiler['test_overlay'])
    archive = read(ROOT / 'verification/swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz')
    raw_mir = gzip.decompress(archive)
    need('retained MIR hash and extent', len(raw_mir) == 76655228 and digest(raw_mir) == 'e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2' and digest(archive) == compiler['MIR']['archive_sha256'])
    bodies = select_functions(mir_functions(raw_mir.decode()))
    need('complete selected body extraction', '\n'.join(bodies.values()).encode() == read(PRODUCER / 'selected-boundaries.mir'))
    ledger = load(PRODUCER / 'operation-ledger.json')
    frozen_functions = {f['function']: f for f in ledger['functions']}
    need('unique eight ledger bodies', len(frozen_functions) == len(ledger['functions']) == 8 and set(frozen_functions) == set(bodies))
    shapes = Types(sources)
    profile = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    control = 'src/experimental_swift_reactor/control.rs'
    loader = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    bindings = {'leaf': (profile, 'run_one_loaded_fixture_v1', 0), 'adopt_snapshot': (control, 'adopt_snapshot_body_v1', 0), 'construct': (control, 'construct_v1', 0), 'outer': (control, 'outer_v1', 0), 'finish': (control, 'finish_v1', 0), 'snapshot_into_body': (loader, 'into_adoption_body_v1', 0), 'selected_into_body': (loader, 'into_adoption_body_v1', 1), 'into_scope': (loader, 'into_snapshot_scope_v1', 0)}
    totals = collections.Counter()
    native, unsized, cuts = collections.Counter(), collections.Counter(), collections.Counter()
    internal = []
    function_results = []
    drop_operands = []
    op_classes = collections.Counter()
    for name, body in bodies.items():
        frozen = frozen_functions[name]
        source_binding, fragment = source_function(sources, *bindings[name])
        need('exact source function extent ' + name, all(frozen['binding'][k] == v for k,v in source_binding.items()))
        need('exact complete MIR function ' + name, digest(body.encode()) == frozen['binding']['MIR_sha256'] and body.splitlines()[0] == frozen['binding']['MIR_header'])
        roles = roles_of(body)
        for role, row in roles.items():
            ty = row['compiler_type']
            row['scalar_leaves'] = shapes.inline(ty)
            n, refs, u = shapes.refs(ty)
            row.update(pointee_scalar_leaves=n, pointee_types=dict(refs), unsized_pointees=dict(u))
            need('independent typed role ' + name + role, row == frozen['roles'].get(role))
            need('no raw-pointer elision ' + name + role, not ty.startswith(('*const ', '*mut ')))
        need('all role declarations accounted ' + name, set(roles) == set(frozen['roles']))
        blocks = blocks_of(body)
        need('all MIR blocks accounted ' + name, set(blocks) == set(frozen['blocks']))
        paths = terminal_paths(blocks)
        need('all terminal paths including unwind ' + name, paths == frozen['terminal_paths'] and len(paths) == frozen['terminal_path_count'])
        need('finite all-blocks envelope ' + name, all(len(p) == len(set(p)) for p in paths))
        sites, units, constant_bytes = [], 0, 0
        block_units = {}
        for block, row in blocks.items():
            fb = frozen['blocks'][block]
            need('cleanup/source block shape ' + name + block, row['cleanup'] == fb['cleanup'] and len(row['operations']) == len(fb['lines']))
            block_units[block] = 0
            for (line, code), frozen_op in zip(row['operations'], fb['lines']):
                independent = operation_of(code, roles)
                independent['MIR_body_line'] = line
                need('full written operation ' + name + ':' + str(line), independent == frozen_op)
                op_classes[classify(code)] += 1
                block_units[block] += independent['source_action_units']
                native.update(independent['native_type_coefficients'])
                unsized.update(independent['unsized_coefficients'])
                constant_bytes += independent['known_constant_bytes']
                cut = independent['cut']
                if cut:
                    site = dict(cut, block=block, MIR_body_line=line, code=code)
                    sites.append(site)
                    if cut['kind'] == 'included-source-body':
                        internal.append([name, cut['key']])
                    elif cut['kind'] == 'required-core-split':
                        cuts.update(cut['split'])
                    else:
                        cuts[cut['key']] += 1
                    if cut['kind'] == 'required-drop-payload':
                        operand = cut['operand']
                        actual = re.search(r': ([\w:]+)\)\)$', operand)
                        root_type = cut['key'].split('::', 1)[1]
                        drop_operands.append({'function': name, 'block': block, 'MIR_body_line': line, 'operand': operand, 'enclosing_role_type': root_type, 'actual_payload_type': canon_type(actual[1]) if actual else root_type, 'required_cut': cut['key'], 'wrapper_price_must_cover_projected_variant': actual is not None})
            need('block price agrees ' + name + block, block_units[block] == fb['source_action_units'])
            units += block_units[block]
        max_path = max(sum(block_units[b] for b in path) for path in paths)
        need('source upper envelope agrees ' + name, units == frozen['all_blocks_once_source_action_units'] and units >= max_path == frozen['maximum_single_CFG_path_source_action_units'])
        need('all exact callee/drop sites ' + name, sites == frozen['callee_and_drop_sites'])
        totals.update(source_actions=units, known_constant_bytes=constant_bytes, roles=len(roles), blocks=len(blocks), operations=sum(len(b['operations']) for b in blocks.values()), terminal_paths=len(paths), cleanup_blocks=sum(b['cleanup'] for b in blocks.values()))
        function_results.append({'function': name, 'binding': source_binding, 'source_actions': units, 'maximum_single_path_actions': max_path, 'roles': len(roles), 'blocks': len(blocks), 'operations': sum(len(b['operations']) for b in blocks.values()), 'terminal_paths': len(paths), 'cleanup_blocks': sum(b['cleanup'] for b in blocks.values()), 'actual_source_loops': bool(re.search(r'\b(?:for|while|loop)\b', lexical_mask(fragment)))})
    need('total dimensions independently recovered', totals['source_actions'] == 639237 and totals['roles'] == 205 and totals['operations'] == 598 and totals['terminal_paths'] == 13827)
    need('consuming call graph matches', internal == ledger['internal_edges'])
    inbound = collections.Counter(b for a,b in internal)
    need('at most one selected invocation site per consuming body', inbound == collections.Counter({k:1 for k in bodies if k != 'leaf'}))
    todo = [('leaf', set())]
    reachable = set()
    while todo:
        name, previous = todo.pop()
        need('acyclic consuming call graph ' + name, name not in previous)
        reachable.add(name)
        todo.extend((b, previous | {name}) for a,b in internal if a == name)
    need('all selected bodies reachable', reachable == set(bodies))
    ni = load(PRODUCER / 'native-occurrence-interface.json')
    ci = load(PRODUCER / 'cost-interface.json')
    need('native occurrence coefficients reconstructed', dict(native) == ni['all_type_occurrence_coefficients'])
    known_sizes = {}
    prior_layouts = load(ROOT / 'verification/swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')['actual_type_sizes']
    for ty, size in prior_layouts.items():
        key = canon_type(ty)
        need('actual146 layout alias agrees ' + key, key not in known_sizes or known_sizes[key] == size)
        known_sizes[key] = size
    need('known actual146 layouts only', {t:known_sizes[t] for t in native if t in known_sizes} == ni['known_actual146_layouts_used'])
    missing = {t:n for t,n in native.items() if t not in known_sizes}
    known_bytes = totals['known_constant_bytes'] + sum(n*known_sizes[t] for t,n in native.items() if t in known_sizes)
    need('native missing/known terms', missing == ci['missing_native_occurrence_coefficients'] and len(missing) == 53 and known_bytes == ci['known_native_occurrence_bytes'] == 118660 and totals['known_constant_bytes'] == ni['known_constant_bytes'] == 208)
    need('both independent unsized dimensions retained', dict(unsized) == ci['unsized_source_and_native_byte_coefficients'] == {'str':2188})
    cuts.update({'private_std_compiler_lowering_and_requested_backing_allowance':1, 'retained_dynamic_resource_backing_and_native_transfer_allowance':1})
    need('all 33 positive cuts and multiplicities reconstructed', dict(cuts) == ci['required_nonzero_callee_drop_and_backing_cuts'] and len(cuts) == 33)
    need('projected payload drop mapping explicit', len([d for d in drop_operands if d['wrapper_price_must_cover_projected_variant']]) == 2)
    need('no selected body loops', not any(f['actual_source_loops'] for f in function_results))
    core_binding, core_fragment = source_function(sources, control, 'adopt_body_core_v1')
    bm = load(PRODUCER / 'accepted-core-boundary-map.json')
    fixed = 'control.execution_work = P::FIXED_EXECUTION_WORK_V1;'
    text = sources[control].decode()
    need('exact source core function boundary', all(bm['exact_source_core_boundary'][k] == v for k,v in core_binding.items()))
    need('unique fixed counter store', text.count(fixed) == 1 and core_fragment.count(fixed) == 1)
    store_pos = text.index(fixed)
    need('prestore exact slice binding', bm['exact_source_core_boundary']['fixed_store_line'] == text[:store_pos].count('\n')+1 == 716 and bm['exact_source_core_boundary']['pre_store_source_slice_sha256'] == digest(core_fragment[:core_fragment.index(fixed)].encode()))
    need('no product 451814442 transfer or discount', not bm['accepted_core_price_transferred'] and bm['claimed_451814442_discount'] == ci['product_work_discount'] == 0 and not ci['work451814442_reused_as_shell_or_callee_price'] and ci['product_work451814442_unchanged'])
    need('interface explicit incomplete boundaries', ci['WorkAuditPending'] and not ci['operational_grant'] and not ci['complete_host_quote'] and not ci['actual_callees_priced'] and not ci['actual_native_layouts_complete'] and not ci['actual_writer_or_fixture_execution'] and not ci['native_OTA_GA_accepted'])
    # Select only these three reviewed pure function definitions from frozen data.
    model_source = read(PRODUCER / 'model.py').decode()
    module = ast.parse(model_source)
    selected = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name in {'checked_sum','checked_product','require_complete'}]
    need('three reviewed evaluator functions selected', len(selected) == 3)
    namespace = {'U64_MAX':U64}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(PRODUCER / 'model.py') + ':selected-pure-functions', 'exec'), namespace)
    evaluate = namespace['require_complete']
    sizes = {k: 8 for k in missing}
    cut_values = {k: 17 for k in cuts}
    unsized_values = {'str': 31}
    baseline = evaluate(ci, sizes, cut_values, unsized_values)
    need('synthetic complete evaluator matches independent arithmetic', baseline == checked_total(ci, sizes, cut_values, unsized_values))
    hostile = 0
    for category, mapping in [('layout', sizes), ('cut', cut_values), ('unsized', unsized_values)]:
        for key in mapping:
            for invalid in [None, 0, -1, True, False, '8', 8.0, U64+1]:
                changed = dict(mapping)
                if invalid is None:
                    del changed[key]
                else:
                    changed[key] = invalid
                args = [ci, changed if category == 'layout' else sizes, changed if category == 'cut' else cut_values, changed if category == 'unsized' else unsized_values]
                reject('hostile ' + category + ' ' + key + '=' + repr(invalid), evaluate, *args)
                reject('independent hostile ' + category + ' ' + key + '=' + repr(invalid), checked_total, *args)
                hostile += 1
    for category, mapping in [('layout', sizes), ('cut', cut_values), ('unsized', unsized_values)]:
        for key in mapping:
            changed = dict(mapping)
            changed[key] = U64
            args = [ci, changed if category == 'layout' else sizes, changed if category == 'cut' else cut_values, changed if category == 'unsized' else unsized_values]
            reject('checked complete quote overflow ' + category + key, evaluate, *args)
            hostile += 1
    for delta in [1, 7, 1024, 1 << 32]:
        for key, coefficient in missing.items():
            changed = dict(sizes)
            changed[key] += delta
            need('layout marginal exact ' + key + ':' + str(delta), evaluate(ci, changed, cut_values, unsized_values) - baseline == coefficient*delta)
        for key, coefficient in cuts.items():
            changed = dict(cut_values)
            changed[key] += delta
            need('callee marginal exact ' + key + ':' + str(delta), evaluate(ci, sizes, changed, unsized_values) - baseline == coefficient*delta)
        need('two unsized byte dimensions exact ' + str(delta), evaluate(ci, sizes, cut_values, {'str':31+delta}) - baseline == 4376*delta)
    # Hostile pure structural controls are checked by independent parsers.
    for bad in ['StorageLive(_999);', '_0 = UnsupportedIntrinsic(_1);', 'assert(copy _1) -> [success: bb1, unwind: bb2];']:
        reject('unknown operation refuses ' + bad, operation_of, bad, {'_0':{}, '_1':{}})
    for graph in [{'bb0':{'operations':[(1,'goto -> bb0;')]}}, {'bb0':{'operations':[(1,'goto -> bb1;')]}}, {'bb0':{'operations':[(1,'unknown;')]}}]:
        reject('cyclic/incomplete/unknown CFG refuses ' + repr(graph), terminal_paths, graph)
    reject('missing selected MIR boundary refuses', select_functions, [b for n,b in bodies.items() if n != 'leaf'])
    reject('duplicate selected MIR boundary refuses', select_functions, list(bodies.values()) + [bodies['leaf']])
    reject('unknown actual source type refuses', shapes.inline, 'UnpricedUnknownPayload')
    reject('unknown constant refuses', literal_constants, '_0 = const MissingGlobal;')
    need('lexical source body handles literal braces', lexical_mask('fn f(){"}"; /* { /* } */ } */ 0}') == 'fn f(){   ;                  0}')
    report = {'schema':1, 'status':'bounded-finite-source-interface-independent-review-pass', 'producer_seal_sha256':SEAL_SHA, 'root_release_sha256':RELEASE_SHA, 'source_members':146, 'source_tree_sha256':TREE, 'source_actions':639237, 'known_native_occurrence_bytes':118660, 'missing_native_layout_terms':53, 'unsized_source_coefficient':2188, 'unsized_native_coefficient':2188, 'required_positive_callee_drop_backing_terms':33, 'totals':dict(totals), 'functions':function_results, 'operation_categories':dict(op_classes), 'drop_operands':drop_operands, 'hostile_evaluator_cases':hostile, 'independent_assertions':len(CHECKS), 'compiler_invoked':False, 'producer_collector_or_module_imported':False, 'selected_pure_evaluator_functions_executed':['checked_sum','checked_product','require_complete'], 'actual_product_runtime':False, 'UI_capture_native_process_inventory':False, 'complete_component_price':False, 'operational_host_grant':False, 'full_host_quote':False, 'native_OTA_GA':False, 'layout_query_lane_consumed':False, 'limitations':['53 native layout terms remain unresolved in this producer interface pending released compile-only data', 'all callee/drop/backing prices and finite positive unsized string bounds remain required and unselected', 'projected Some.0 cleanup cuts require full Some-case payload destruction coverage', 'core before fixed store and store-and-after remain positive external terms; aggregate 451814442 transfers zero credit', 'no actual setup/loader/leaf/VM/scope/constructor/writer/fixture/destructor execution or cleanup qualification', 'native runtime, computer use and capture remain paused; physical phones disconnected']}
    (HERE / 'review-results.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    (HERE / 'input-custody.json').write_text(json.dumps({'schema':1, 'packets':packets, 'inputs':INPUTS}, sort_keys=True, indent=2)+'\n')
    (HERE / 'assertions.json').write_text(json.dumps({'count':len(CHECKS), 'checks':CHECKS}, sort_keys=True, indent=2)+'\n')
    print(json.dumps({'status':report['status'], 'independent_assertions':len(CHECKS), 'hostile_evaluator_cases':hostile, 'source_actions':639237, 'native_known_bytes':118660, 'runtime':False, 'compiler':False}))


if __name__ == '__main__':
    main()
