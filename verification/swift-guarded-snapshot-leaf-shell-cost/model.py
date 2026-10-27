"""Pure source-shape/MIR helpers adapted from accepted parent source146 data.
No compiler, runtime, or frozen packet script is executed on import.
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
    body = re.sub(r'#\[cfg\(test\)\]\s*[^,]+,', '', body)
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
        self.tuples = {}
        for path, raw in source.items():
            if not path.endswith('.rs') or '/test' in path or path.endswith('_tests.rs'):
                continue
            if b'struct ' not in raw and b'enum ' not in raw: continue
            txt = uncomment(raw.decode())
            for m in re.finditer(r'\bstruct\s+(\w+)\s*(?:<[^;{}]*>)?\s*\(([^;{}]*)\)\s*;', txt):
                self.tuples.setdefault(m[1], []).append((path, m[2], m[0]))
            for m in re.finditer(r'\b(struct|enum)\s+(\w+)\s*([^;{]*)\{', txt):
                if m[3].strip() and not m[3].strip().startswith('<'):
                    continue
                end = close_brace(txt, m.end() - 1)
                self.defs[m[2]].append((path, m[1], txt[m.end():end], txt[m.start():end+1]))

    def n(self, ty):
        original = ty
        ty = {'AError': 'SnapshotAdmissionErrorV1', 'Stop': 'SnapshotStopV1', 'SnapshotClaimsV1': 'UnverifiedProfileDigestBytesV1', 'SwiftMetadata': 'Metadata<SwiftDeclaration>'}.get(ty.strip(), ty.strip())
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
            elif name in self.tuples:
                ds = self.tuples[name]
                if len(ds) != 1:
                    raise ValueError('ambiguous tuple source type: ' + ty)
                path, body, declaration = ds[0]
                fs = [re.sub(r'^pub(?:\([^)]*\))?\s+', '', x) for x in split(body)]
                n = sum(map(self.n, fs)) or 1
                self.used[name] = dict(path=path, kind='tuple-struct', fields=fs, declaration_sha256=sha(declaration.encode()), scalar_leaves=n)
            elif name in ('File', 'Error', 'Cancellation', 'Instant', 'Duration', 'Path', 'OpenOptions', 'Vec', 'String', 'Arc', 'Rc', 'Box', 'IntoIter', 'Enumerate'):
                n = 1  # Explicit abstract std/resource boundary, no backing price.
            else:
                ds = self.defs[name]
                route = {'Refusal': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'Role': 'src/experimental_swift_reactor/retained_profile_loader_v1.rs', 'Resource': 'src/experimental/mod.rs', 'Policy': 'src/experimental/policy.rs', 'Metadata': 'src/experimental/metadata.rs', 'Buffer': 'src/experimental/account.rs', 'Span': 'src/experimental_wasi/mod.rs', 'Limits': 'src/lib.rs'}.get(name)
                if name == 'Resource' and ty.startswith('experimental_wasi::'): route = 'src/experimental_wasi/mod.rs'
                if route:
                    ds = [d for d in ds if d[0] == route]
                if len(ds) != 1:
                    raise ValueError('unknown or ambiguous source type: ' + ty)
                path, kind, body, declaration = ds[0]
                detail = {'path': path, 'kind': kind, 'declaration_sha256': sha(declaration.encode())}
                if kind == 'struct':
                    fs = fields(body)
                    if name == 'Buffer': fs = [re.sub(r'\bResource\b', 'experimental::Resource', x) for x in fs]
                    if name == 'Metadata':
                        if len(args) != 1: raise ValueError('unbound Metadata declaration')
                        fs = [re.sub(r'\bD\b', args[0], x) for x in fs]
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
                        if name == 'WasiFailure': fs = [re.sub(r'\bResource\b', 'experimental_wasi::Resource', x) for x in fs]
                        variants.append({'name': m[1], 'fields': fs, 'payload_leaves': sum(map(self.n, fs))})
                    n = 1 + max([0] + [v['payload_leaves'] for v in variants])
                    detail['variants'] = variants
                detail['scalar_leaves'] = n
                self.used[ty if name == 'Resource' else name] = detail
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


# All arithmetic is proposal-only checked u64 arithmetic, never a runtime grant.
U64_MAX=(1 << 64)-1

def checked_sum(values):
    total=0
    for value in values:
        if isinstance(value,bool) or not isinstance(value,int) or value<0 or value>U64_MAX-total:
            raise ValueError('invalid or overflowing u64 sum')
        total+=value
    return total

def checked_product(a,b):
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 or v>U64_MAX for v in (a,b)) or (b and a>U64_MAX//b):
        raise ValueError('invalid or overflowing u64 product')
    return a*b

def canonical_type(ty):
    ty=re.sub(r"&\s*'(?:[A-Za-z_]\w*)\s*", '&',ty)
    ty=re.sub(r'\b(?:[A-Za-z_]\w*::)+','',ty)
    ty=re.sub(r"\s+", ' ',ty).strip()
    return ty.replace('SnapshotClaimsV1','UnverifiedProfileDigestBytesV1')

def pointee_type(ty):
    if not ty.startswith('&'):return None
    return re.sub(r"^&\s*(?:'[A-Za-z_]\w*\s*)?(?:mut\s+)?", '',ty)

def pointees(ty,shapes,active=()):
    """All finite typed pointees reachable through source aggregates.

    Counts sum all enum alternatives, conservatively, without claiming their
    simultaneous liveness. Opaque std backing/destructor bodies remain cuts.
    Unsized str/slices stay positive symbolic terms, never scalar-width zero.
    """
    key=canonical_type(ty)
    if key in active:raise ValueError('recursive reference closure '+key)
    active=active+(key,)
    target=pointee_type(ty)
    if target is not None:
        if target=='str' or (target.startswith('[') and ';' not in target):
            return 0,collections.Counter(),collections.Counter({canonical_type(target):1})
        more,types,unsized=pointees(target,shapes,active)
        return shapes.n(target)+more,types+collections.Counter({canonical_type(target):1}),unsized
    ty={'SnapshotClaimsV1':'UnverifiedProfileDigestBytesV1','SwiftMetadata':'Metadata<SwiftDeclaration>','AError':'SnapshotAdmissionErrorV1','Stop':'SnapshotStopV1'}.get(ty,ty)
    head=ty.split('<',1)[0];name=head.rsplit('::',1)[-1]
    if ty.startswith('('):children=split(ty[1:-1])
    elif ty.startswith('['):
        el,count=split(ty[1:-1],';');n=int(count.replace('_',''))
        if n>100000:raise ValueError('unbounded source array')
        a,b,c=pointees(el,shapes,active)
        return n*a,collections.Counter({k:n*v for k,v in b.items()}),collections.Counter({k:n*v for k,v in c.items()})
    elif name in ('Option','Result','ControlFlow'):
        children=split(ty[len(head)+1:-1])
    elif name in ('File','Error','Cancellation','Instant','Duration','Path','OpenOptions','Vec','String','Arc','Rc','Box','IntoIter','Enumerate','Cell','Infallible') or ty in ('()','!','str','u8','u16','u32','u64','u128','i8','i16','i32','i64','i128','usize','isize','bool','f32','f64','char'):
        children=[]
    else:
        shapes.n(ty)
        d=shapes.used.get(ty if name=='Resource' else name)
        if d is None:raise ValueError('unresolved referenced shape '+ty)
        children=d.get('fields',[])+[f for v in d.get('variants',[]) for f in v['fields']]
    count=0;types=collections.Counter();unsized=collections.Counter()
    for child in children:
        a,b,c=pointees(child,shapes,active)
        count+=a;types+=b;unsized+=c
    return count,types,unsized

def paths(graph):
    """All CFG alternatives including cleanup; a reachable cycle refuses."""
    terminal=[];todo=[('bb0',[])]
    while todo:
        block,past=todo.pop()
        if block in past:raise ValueError('cycle in selected finite shell')
        if block not in graph:raise ValueError('missing MIR target')
        path=past+[block]
        if len(path)>1000 or len(terminal)>100000:raise ValueError('finite graph bound exceeded')
        final=graph[block]['lines'][-1][1]
        nexts=sorted(set(re.findall(r'\bbb\d+\b',final)))
        if not nexts:
            if final not in ('return;','resume;','unreachable;') and 'unwind continue' not in final and 'unwind terminate' not in final:
                raise ValueError('unknown terminal '+final)
            terminal.append(path)
        if 'unwind continue' in final or 'unwind terminate' in final:
            terminal.append(path)
        todo.extend((b,path) for b in nexts)
    return terminal

def require_complete(interface,sizes,cuts,unsized):
    """Synthetic-capable component evaluator; cannot issue a host grant."""
    values=[interface['fixed_source_action_units'],interface['known_native_occurrence_bytes']]
    for ty,n in interface['missing_native_occurrence_coefficients'].items():
        if ty not in sizes or isinstance(sizes[ty],bool) or not isinstance(sizes[ty],int) or sizes[ty]<=0:raise ValueError('missing positive actual146 sizeof '+ty)
        values.append(checked_product(n,sizes[ty]))
    for term,n in interface['unsized_source_and_native_byte_coefficients'].items():
        if term not in unsized or isinstance(unsized[term],bool) or not isinstance(unsized[term],int) or unsized[term]<=0:raise ValueError('missing positive unsized backing '+term)
        # Explicit independent source-leaf and byte dimensions, two units/byte.
        values.append(checked_product(2*n,unsized[term]))
    for cut,n in interface['required_nonzero_callee_drop_and_backing_cuts'].items():
        if cut not in cuts or isinstance(cuts[cut],bool) or not isinstance(cuts[cut],int) or cuts[cut]<=0:raise ValueError('missing positive cut '+cut)
        values.append(checked_product(n,cuts[cut]))
    return checked_sum(values)
