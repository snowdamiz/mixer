#!/usr/bin/env python3
"""Independent, compiler-free transfer check of the released P0 source146 proof.

Only this directory is writable. No frozen producer/checker is imported or run.
The prior accepted proof is a premise, not a generic MIR/shape verifier grant.
"""
from __future__ import annotations
import collections
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V = ROOT / 'verification'
P = V / 'swift-guarded-snapshot-parent-work-source146'
OLD = V / 'swift-guarded-snapshot-parent-work'
PRIOR = V / 'swift-guarded-snapshot-parent-work-independent'
ACCOUNT = V / 'swift-guarded-snapshot-host-account-entry'
COMPOSE = V / 'swift-guarded-snapshot-host-composition'
FRESH = V / 'swift-guarded-snapshot-host-composition-independent'
BASE = V / 'swift-guarded-snapshot-funding-implementation/source/vm'
S145 = '5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
S146 = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
APATH = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
EPATH = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
CONTROL = 'src/experimental_swift_reactor/control.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
checks, inputs = [], {}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()

def require(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def read(path):
    path = Path(path)
    raw = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': digest(raw)}
    return raw

def load(path):
    return json.loads(read(path))

def row(name, raw):
    return {'path': name, 'bytes': len(raw), 'sha256': digest(raw)}

def manifest(source):
    members = [row(p, source[p]) for p in sorted(source, key=Path)]
    return {'schema': 1, 'members': members, 'member_count': len(members), 'tree_sha256': digest(canonical(members))}

def packet(folder, expected, count, size):
    raw = read(folder / 'seal.json')
    require('seal ' + folder.name, digest(raw) == expected)
    seal = json.loads(raw)
    require('closure dimensions ' + folder.name, len(seal['members']) == count and sum(r['bytes'] for r in seal['members']) == size)
    names = set()
    for member in seal['members']:
        name = member['path']
        require('unique safe member ' + folder.name + '/' + name, name not in names and not Path(name).is_absolute() and '..' not in Path(name).parts)
        names.add(name)
        require('custody ' + folder.name + '/' + name, row(name, read(folder / name)) == member)
    return seal

def split_top(text, separator=','):
    """Finite balanced scanner for the actual closed types, not Rust parsing."""
    out, stack, begin = [], [], 0
    pairs = {'<': '>', '(': ')', '[': ']', '{': '}'}
    for i, char in enumerate(text):
        if char in pairs:
            stack.append(pairs[char])
        elif char in '>)]}':
            if not stack or stack.pop() != char:
                raise ValueError('unbalanced concrete type')
        elif char == separator and not stack:
            out.append(text[begin:i].strip())
            begin = i+1
    if stack:
        raise ValueError('unfinished concrete type')
    out.append(text[begin:].strip())
    return [x for x in out if x]

def short(text):
    return re.sub(r'\bexperimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::(?:host_account_v1::)?', '', text).replace('std::', '')

class ClosedShapes:
    """Recompute prior accepted leaf rules only for byte-identical declarations."""
    def __init__(self, definitions):
        self.defs, self.used, self.active = definitions, set(), set()

    def leaves(self, original):
        text = original.strip()
        text = {'AError': 'SnapshotAdmissionErrorV1', 'Stop': 'SnapshotStopV1'}.get(text, text)
        if text in self.active:
            raise ValueError('by-value recursion')
        self.active.add(text)
        try:
            if text.startswith(('&', '*const ', '*mut ')) or text.startswith('{closure@') or text == 'impl FnOnce() -> T':
                return 1
            if text in ('()', '!', 'u8', 'u16', 'u32', 'u64', 'u128', 'i8', 'i16', 'i32', 'i64', 'i128', 'usize', 'isize', 'bool', 'f32', 'f64', 'char', 'str'):
                return 1
            if text.startswith('['):
                part, number = split_top(text[1:-1], ';')
                count = 6 if number == 'COMPONENT_COUNT_V1' else int(number.replace('_', ''))
                if count < 0:
                    raise ValueError('negative array')
                return count * self.leaves(part)
            if text.startswith('(') and text.endswith(')'):
                return sum(self.leaves(t) for t in split_top(text[1:-1])) or 1
            head = text.split('<', 1)[0]
            name = head.rsplit('::', 1)[-1]
            args = split_top(text[len(head)+1:-1]) if '<' in text else []
            if name in ('Option', 'Result', 'ControlFlow'):
                if len(args) != (1 if name == 'Option' else 2):
                    raise ValueError('wrong shape arity')
                return 1+max([0]+[self.leaves(a) for a in args])
            if name == 'Infallible':
                return 0
            if name == 'Cell':
                if len(args) != 1:
                    raise ValueError('wrong Cell arity')
                return self.leaves(args[0])
            if name in ('File', 'Error', 'Cancellation', 'Instant', 'Duration', 'Path', 'OpenOptions', 'Vec', 'String', 'Arc', 'Rc', 'Box', 'IntoIter', 'Enumerate'):
                return 1  # Accepted explicit standard-resource primitive boundary.
            if name not in self.defs:
                raise ValueError('unsupported closed shape: '+text)
            self.used.add(name)
            definition = self.defs[name]
            def sum_fields(fields):
                fields = list(fields)
                if name == 'PrepaidOwnedV1':
                    if len(args) != 2 or args[1].rsplit('::', 1)[-1] != 'OwnedFixtureOutcomeV1':
                        raise ValueError('unbound payload specialization')
                    fields = [re.sub(r'\bT\b', args[1], f) for f in fields]
                return sum(self.leaves(f) for f in fields)
            if definition['kind'] == 'struct':
                answer = sum_fields(definition['fields']) or 1
            else:
                answer = 1+max([0]+[sum_fields(v['fields']) for v in definition['variants']])
            if answer != definition['scalar_leaves']:
                raise ValueError('accepted shape leaf count disagreement: '+name)
            return answer
        finally:
            self.active.remove(text)

def declarations(source, proof):
    """Locate exact declaration bytes in its accepted path; no type inference."""
    text = source[proof['path']].decode()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = '\n'.join(line.split('//', 1)[0] for line in text.splitlines())
    pattern = r'\b'+proof['kind']+r'\s+'
    found = []
    for m in re.finditer(pattern+r'\w+\s*[^;{]*\{', text):
        depth, end = 1, m.end()
        while depth and end < len(text):
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        if depth:
            raise ValueError('unfinished selected declaration')
        part = text[m.start():end]
        if digest(part.encode()) == proof['declaration_sha256']:
            found.append(part)
    if len(found) != 1:
        raise ValueError('selected declaration is not unique/exact')
    return found[0]

def mir_bodies(raw):
    text = raw.decode()
    begins = list(re.finditer(r'^fn ', text, re.M))
    bodies = []
    for i, start in enumerate(begins):
        end = begins[i+1].start() if i+1 < len(begins) else len(text)
        part = text[start.start():end]
        terminal = re.search(r'^}\n', part, re.M)
        if terminal is None or part[terminal.end():].strip():
            raise ValueError('incomplete/unrecognized MIR body')
        bodies.append(part[:terminal.end()])
    if not begins or text[:begins[0].start()].strip():
        raise ValueError('unparsed MIR prefix')
    return bodies

def normalize(text, prefix):
    # Only the two exact bound compile roots and compiler source-span metadata.
    text = text.replace(prefix+'/', '<VM>/')
    return re.sub(r'(?<=\.rs):\d+:\d+: \d+:\d+', ':<SPAN>', text)

def semantic(body, prefix):
    # Actual selected bodies have no string values containing //; check callers.
    return '\n'.join(normalize(line.split('//', 1)[0].rstrip(), prefix) for line in body.splitlines())

def roles(body):
    head = body.splitlines()[0]
    m = re.fullmatch(r'fn [^(]+\((.*)\) -> (.*) \{', head)
    if not m:
        raise ValueError('unrecognized retained header')
    result = [(n, 'parameter', t) for n, t in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)', m[1])]
    for n, t in re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);(?:\s*//[^\n]*)?$', body, re.M):
        result.append((n, 'return-place' if n == '_0' else 'local-or-temporary', t))
    if len({n for n, _, _ in result}) != len(result):
        raise ValueError('duplicate role')
    return result

def blocks(body):
    output, selected = {}, None
    for n, raw in enumerate(body.splitlines(), 1):
        line = raw.split('//', 1)[0].rstrip()
        m = re.fullmatch(r'    (bb\d+)( \(cleanup\))?: \{', line)
        if m:
            if m[1] in output:
                raise ValueError('duplicate block')
            selected = {'cleanup': bool(m[2]), 'rows': []}
            output[m[1]] = selected
        elif line == '    }':
            selected = None
        elif selected is not None and line.strip():
            selected['rows'].append((n, line.strip()))
    if not output or any(not bb['rows'] for bb in output.values()):
        raise ValueError('incomplete block set')
    return output

def measure(code, dimensions):
    names = re.findall(r'\b_\d+\b', code)
    const = []
    for token in re.split(r'\bconst\s+', code)[1:]:
        m = re.match(r'(\d+_(?:u64|usize)|true\b|false\b|\(\))', token)
        if not m:
            raise ValueError('unpriced constant')
        const.append({'text': m[1], 'bytes': 0 if m[1]=='()' else 1 if m[1] in ('true','false') else 8, 'scalar_leaves': 1})
    basic = 2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b', code))
    used = [dimensions[n] for n in names]
    if code == 'return;':
        used.append(dimensions['_0'])
    scalar = 2*(sum(r['scalar_leaves']+r['pointee_scalar_leaves'] for r in used)+len(const))
    native = 2*(sum(r['bytes']+r['pointee_bytes'] for r in used)+sum(c['bytes'] for c in const))
    return {'local_mentions': names, 'constants': const, 'base_action_units': basic, 'scalar_fetch_store_units': scalar, 'source_action_units': basic+scalar, 'native_sized_occurrence_bytes': native}

def terminal_paths(graph, identity):
    # Accepted six-element IntoIterator contract. Only next's six Some outcomes
    # repeat; the seventh observation is final None. No arbitrary graph cap pays
    # a cycle. This body and its calls must be identical to the prior proof.
    todo, terminal = [('bb0', (), 0)], []
    while todo:
        bid, path, some = todo.pop()
        if len(path) > 300:
            raise ValueError('unsupported repeated control')
        if identity != 'checked_components_v1' and bid in path:
            raise ValueError('new cycle')
        if identity == 'checked_components_v1' and bid == 'bb7':
            some += 1
        if some > 6:
            raise ValueError('too many fixed-array elements')
        path = path+(bid,)
        last = graph[bid]['rows'][-1][1]
        edges = set(re.findall(r'\bbb\d+\b', last))
        if identity == 'checked_components_v1' and bid == 'bb5' and some == 6:
            edges.remove('bb7')
        if 'unwind continue' in last:
            terminal.append(('unwind-continue', path))
        if 'unwind terminate' in last:
            terminal.append(('unwind-terminate', path))
        if not edges:
            terminal.append(({'return;':'return', 'resume;':'resume', 'unreachable;':'unreachable'}[last], path))
        for successor in sorted(edges):
            if successor not in graph:
                raise ValueError('missing successor')
            todo.append((successor, path, some))
    return terminal

def vector(raw):
    if len(raw) < 8:
        raise ValueError('short vector')
    count, offset, strings = int.from_bytes(raw[:8], 'little'), 8, []
    for _ in range(count):
        if offset+8 > len(raw):
            raise ValueError('short vector length')
        size = int.from_bytes(raw[offset:offset+8], 'little')
        offset += 8
        if offset+size > len(raw):
            raise ValueError('short vector string')
        strings.append(raw[offset:offset+size].decode())
        offset += size
    if offset != len(raw):
        raise ValueError('vector trailing bytes')
    return strings

def compiler_data(mode, compiled, distribution):
    pre = FRESH/'preimages'/mode
    raw_manifest = read(pre/'manifest.json')
    mf = json.loads(raw_manifest)
    binding = load(pre/'binding.json')
    receipt = load(FRESH/'commands'/mode/'receipt.json')
    av, en, ve = [read(pre/n) for n in ('argv.bin','environment.bin','compiler-version.txt')]
    keys = {'MIXER_LOADER_MANIFEST_SHA256': digest(raw_manifest), 'MIXER_LOADER_COMMAND_SHA256': digest(av), 'MIXER_LOADER_COMPILE_ENV_SHA256': digest(en), 'MIXER_LOADER_COMPILER_SHA256': mf['tools']['rustc']['sha256'], 'MIXER_LOADER_COMPILER_VERSION_SHA256': digest(ve)}
    require('five exact compiler keys '+mode, keys==binding['keys'] and all(receipt['environment'][k]==v for k,v in keys.items()))
    require('argv preimage '+mode, vector(av)==receipt['argv'])
    require('environment preimage '+mode, dict(x.split('=',1) for x in vector(en))=={k:v for k,v in receipt['environment'].items() if k not in keys})
    require('bound compiler source '+mode, mf['distribution']==distribution and mf['compiled_source']==compiled and binding['compiled_tree']==compiled['tree_sha256'] and binding['distribution_tree']==S146)
    require('compiler/target/version fixed '+mode, keys['MIXER_LOADER_COMPILER_SHA256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0' and keys['MIXER_LOADER_COMPILER_VERSION_SHA256']=='352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909' and receipt['argv'][receipt['argv'].index('--target')+1]=='aarch64-apple-darwin')
    require('frozen compile-only scope '+mode, '--test' not in receipt['argv'] and '-Zmir-opt-level=0' in receipt['argv'] and receipt['argv'][receipt['argv'].index('--crate-type')+1]=='rlib' and any(x.startswith('--emit=metadata=') for x in receipt['argv']) and mf['genuine_fixture_loader_VM_cache_scope_construct_writer_execution'] is False)
    require('bounded waited frozen compiler '+mode, receipt['timeout_seconds']==180 and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['global_process_inventory'] is False and receipt['exit_code']==(0 if mode=='exact146-metadata-mir' else 1))
    stdout = gzip.decompress(read(FRESH/'commands'/mode/'stdout.gz')) if mode=='exact146-metadata-mir' else read(FRESH/'commands'/mode/'stdout')
    stderr = read(FRESH/'commands'/mode/'stderr')
    for name, data in [('stdout',stdout),('stderr',stderr)]:
        require('complete archived output '+mode+'/'+name, digest(data)==receipt[name]['sha256'] and len(data)==receipt[name]['bytes'])
    return receipt, keys, stdout, stderr

def audit():
    release = V/'swift-semantic-adapter-root-review/guarded-snapshot-parent-work-source146-independent-release.json'
    require('exact root release', digest(read(release))=='85a2570dab0f64d1038aad02ab8be77e5ea13ca79fea3e7b68f5db493f94fe88')
    for name, sha in [('guarded-snapshot-parent-work-host-acceptance.json','479d0fd1114cd7512c369dae0038a7ccd2407854f5089669ba5e020f2225cd3a'),('guarded-snapshot-host-composition-host-acceptance.json','c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8')]:
        require('exact root accepted premise '+name, digest(read(V/'swift-semantic-adapter-root-review'/name))==sha)
    sealed = [(P,'91144a1c47213edd046be33f5db059ee4e326970141f9add3c7f3438e3d5f2b1',44,1106266),(OLD,'bc9426ad22da41b354094b1778685bb7bf834e03fc22101272c2f08bf5d2b857',52,1665166),(PRIOR,'ffdd027f5550f315fb7c63dcee7e532e7aea1d4be39c478d225f8f6ed09a7b2b',46,767864),(COMPOSE,'2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e',152,1301753),(FRESH,'c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63',96,1453031)]
    for args in sealed:
        packet(*args)
    old_mf, fresh_mf = load(ACCOUNT/'source-manifest.json'), load(COMPOSE/'source-manifest.json')
    old_source, source = {}, {}
    for member in old_mf['members']:
        name = member['path']
        raw = read(ACCOUNT/'host_account.rs') if name==APATH else read(BASE/name)
        if name==PROFILE:
            raw += b'\n\n'+read(V/'swift-guarded-snapshot-bootstrap-host-boundary/driver.inc.rs')+b'\n\n'+read(ACCOUNT/'entry.inc.rs')
        require('actual old source '+name, row(name,raw)==member)
        old_source[name]=raw
    for member in fresh_mf['members']:
        name=member['path']
        raw = read(COMPOSE/'overlay/vm'/name) if name in {PROFILE,CONTROL,LOADER,APATH,EPATH} else read(BASE/name)
        require('actual current source '+name, row(name,raw)==member)
        source[name]=raw
    require('both complete source identities', manifest(old_source)==old_mf and old_mf['tree_sha256']==S145 and manifest(source)==fresh_mf and fresh_mf['tree_sha256']==S146 and len(source)==146)
    require('candidate manifest exact', load(P/'source-manifest.json')==fresh_mf)
    changed = sorted(p for p in old_source if old_source[p]!=source[p])
    added = sorted(set(source)-set(old_source))
    require('complete source impact roster', set(changed)=={PROFILE,CONTROL,LOADER} and added==[EPATH] and len(set(old_source)-set(source))==0)
    require('unchanged account and typed entry', source[APATH]==old_source[APATH] and source[PROFILE].endswith(b'\n\n'+read(V/'swift-guarded-snapshot-bootstrap-host-boundary/driver.inc.rs')+b'\n\n'+read(ACCOUNT/'entry.inc.rs')))
    require('new helper is not called', all(b'checked_snapshot_emission_bound_v1' not in raw for name,raw in source.items() if name!=EPATH))
    source_delta={'changed':[{'path':n,'old_sha256':digest(old_source[n]),'new_sha256':digest(source[n]),'old_bytes':len(old_source[n]),'new_bytes':len(source[n])} for n in changed], 'added':[row(n,source[n]) for n in added], 'unchanged':142,'net_bytes':sum(map(len,source.values()))-sum(map(len,old_source.values()))}
    require('source byte delta exact', source_delta['net_bytes']==2786)
    query = load(FRESH/'layout-query-bindings.json')
    fragment = read(FRESH/'layout-queries.inc.rs')
    query_source = dict(source)
    query_source[APATH] += fragment
    query_source['src/lib.rs'] = b'#![feature(never_type)]\n'+query_source['src/lib.rs']
    require('query-only source overlay exact', manifest(query_source)==query['compiled_source'] and query['distribution_tree']==S146 and query['fixture_or_binding_constructor_created'] is False)
    mr,mkeys,stdout,_ = compiler_data('exact146-metadata-mir',fresh_mf,fresh_mf)
    _,qkeys,_,stderr = compiler_data('actual90-layout-queries',manifest(query_source),fresh_mf)
    old_prefix = str(ACCOUNT/'owned-mir-work/vm')
    new_prefix = mr['environment']['CARGO_MANIFEST_DIR']
    inventory = load(ACCOUNT/'caller-inventory.json')
    old_mir_raw = read(ACCOUNT/'entry-and-account.mir')
    fresh_archive = read(FRESH/'entry-and-account.mir.gz')
    fresh_mir_raw = gzip.decompress(fresh_archive)
    archive_info = load(FRESH/'entry-and-account.mir-archive.json')
    require('raw MIR archive digest', digest(fresh_mir_raw)==archive_info['raw_sha256'] and len(fresh_mir_raw)==archive_info['raw_bytes'] and digest(fresh_archive)==archive_info['archive_sha256'])
    previous, current = mir_bodies(old_mir_raw), mir_bodies(fresh_mir_raw)
    require('nineteen complete MIR identities', len(previous)==len(current)==len(inventory['functions'])==19)
    mir_results=[]
    raw_role_count=0
    for i,(before,after,fn) in enumerate(zip(previous,current,inventory['functions'])):
        require('no quoted slash comment ambiguity '+str(i), not re.search(r'"[^"\n]*//', before+after))
        require('complete semantic MIR equality '+str(i), semantic(before,old_prefix)==semantic(after,new_prefix))
        old_roles,new_roles=roles(before),roles(after)
        require('complete raw role identity '+str(i), normalize(canonical(old_roles).decode(),old_prefix)==normalize(canonical(new_roles).decode(),new_prefix))
        expected=[(r['local'],r['kind'],r['compiler_type']) for r in fn['roles']]
        require('old inventory backed by actual MIR '+str(i), old_roles==expected)
        raw_role_count+=len(new_roles)
        mir_results.append({'index':i,'phase':fn['phase'],'old_sha256':digest(before.encode()),'new_sha256':digest(after.encode()),'semantic_sha256':digest(semantic(after,new_prefix).encode()),'roles':len(new_roles),'header':after.splitlines()[0]})
    require('all396 raw roles covered', raw_role_count==396)
    # Keep every raw difference, including comments; none is silently called equal.
    raw_patch=''.join(difflib.unified_diff(old_mir_raw.decode().splitlines(True),fresh_mir_raw.decode().splitlines(True),fromfile='accepted-source145/19.mir',tofile='exact-source146/19.mir'))
    closure=load(FRESH/'mir-and-closure.json')['closure']
    closure_ty=closure['compiler_type']
    match=re.search(r'^print-type-size type: `'+re.escape(closure_ty)+r'`: (\d+) bytes, alignment: (\d+) bytes$',stdout.decode(),re.M)
    require('exact concrete dispatch closure measured', match is not None and tuple(map(int,match.groups()))==(8,8) and closure['bytes']==8 and closure['alignment']==8)
    sizes={'()':0}
    diagnostics=[]
    require('exact90 diagnostic declarations', len(query['query'])==90 and re.findall(rb'const FINAL146_LAYOUT_(\d+):',fragment)==[str(i).encode() for i in range(90)])
    chunks=stderr.decode().split('error[E0308]:')[1:]
    require('only90 expected diagnostics',len(chunks)==90 and re.findall(rb'error\[E\d+\]',stderr)==[b'error[E0308]']*90)
    seen=set()
    for chunk in chunks:
        ids={int(i) for i in re.findall(r'FINAL146_LAYOUT_(\d+)',chunk)}
        require('unique diagnostic id '+str(len(seen)),len(ids)==1)
        i=ids.pop()
        require('no repeated query '+str(i),i not in seen)
        seen.add(i)
        spelling=query['query'][i]['concrete']
        require('actual query spelling '+str(i),spelling in re.findall(r'const FINAL146_LAYOUT_'+str(i)+r':.*std::mem::size_of::<(.+)>\(\)\];',chunk))
        size=int(re.search(r'found one with a size of (\d+)',chunk)[1])
        require('consistent diagnostic size '+str(i),spelling not in sizes or sizes[spelling]==size)
        sizes[spelling]=size
        diagnostics.append({'index':i,'type':spelling,'bytes':size})
    require('complete measured size roster',seen==set(range(90)) and len(sizes)==90 and sizes==inventory['actual_type_sizes']==load(FRESH/'fresh-layout-results.json')['actual_type_sizes'])
    # Prior shape rules are inherited only after exact declaration-byte binding.
    defs=load(OLD/'scalar-shapes.json')['definitions']
    require('fresh candidate shape table exact accepted table',load(P/'scalar-shapes.json')['definitions']==defs and len(defs)==54)
    shape_evidence=[]
    for name,proof in defs.items():
        before=declarations(old_source,proof)
        after=declarations(source,proof)
        require('full source declaration bytes '+name,before==after)
        shape_evidence.append({'name':name,**proof,'bytes':len(after.encode())})
    shapes=ClosedShapes(defs)
    short_sizes={}
    for ty,size in sizes.items():
        key=short(ty)
        require('unambiguous native type alias '+key,key not in short_sizes or short_sizes[key]==size)
        short_sizes[key]=size
    old_ledger=load(OLD/'operation-ledger.json')['functions']
    new_ledger=load(P/'operation-ledger.json')['functions']
    accepted_review=load(PRIOR/'review.json')
    p0=[(body,inv) for body,inv in zip(current,inventory['functions']) if inv['phase']=='P0-pre-existing-parent-account-bookkeeping']
    require('complete P0 function identities',len(p0)==len(old_ledger)==len(new_ledger)==15 and [f['id'] for f in old_ledger]==[f['id'] for f in new_ledger])
    functions=[]
    operations,role_count,logical_bytes,closure_roles=0,0,0,0
    for (body,inv),old,new in zip(p0,old_ledger,new_ledger):
        identity=old['id']
        require('actual candidate MIR hash '+identity,new['MIR_sha256']==digest(body.encode()))
        actual_roles={n:(kind,ty) for n,kind,ty in roles(body)}
        dimensions={}
        for old_role in inv['roles']:
            local=old_role['local']
            ty=old_role['concrete_production_type']
            if '{closure@' in ty:
                closure_roles+=1
                ty=closure_ty
                size=8
            else:
                size=sizes[ty]
            point=re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?",'',ty) if ty.startswith('&') else None
            record={'kind':actual_roles[local][0],'compiler_type':actual_roles[local][1],'concrete_production_type':ty,'bytes':size,'scalar_leaves':shapes.leaves(ty),'pointee_type':point,'pointee_bytes':short_sizes[short(point)] if point else 0,'pointee_scalar_leaves':shapes.leaves(point) if point else 0}
            require('fresh role dimensions '+identity+local,all(new['roles'][local][k]==v for k,v in record.items()))
            require('old numeric role dimensions '+identity+local,all(old['roles'][local][k]==record[k] for k in ('bytes','scalar_leaves','pointee_bytes','pointee_scalar_leaves')))
            dimensions[local]=record
        require('no omitted role '+identity,set(dimensions)==set(actual_roles)==set(new['roles']))
        graph=blocks(body)
        require('all normal and cleanup blocks '+identity,set(graph)==set(old['blocks'])==set(new['blocks']))
        entry_s=2+2*sum(r['scalar_leaves']+r['pointee_scalar_leaves'] for r in dimensions.values() if r['kind']=='parameter')
        entry_b=2*sum(r['bytes']+r['pointee_bytes'] for r in dimensions.values() if r['kind']=='parameter')
        src,native=entry_s,entry_b
        calls=collections.Counter()
        block_cost={}
        for bid,bb in graph.items():
            ob,nb=old['blocks'][bid],new['blocks'][bid]
            require('cleanup block identity '+identity+bid,bb['cleanup']==ob['cleanup']==nb['cleanup'])
            require('complete operations '+identity+bid,len(bb['rows'])==len(ob['lines'])==len(nb['lines']))
            s,b=0,0
            weight=nb['occurrence_bound']
            require('accepted fixed occurrence rule '+identity+bid,weight==ob['occurrence_bound'] and weight>0)
            for (line,code),orow,nrow in zip(bb['rows'],ob['lines'],nb['lines']):
                require('exact operation and known call cut '+identity+':'+str(line),normalize(code,new_prefix)==normalize(orow['code'],old_prefix) and code==nrow['code'] and nrow['call_cut']==orow['call_cut'])
                cost=measure(code,dimensions)
                require('recomputed operation price '+identity+':'+str(line),all(nrow[k]==v and orow[k]==v for k,v in cost.items()))
                s+=cost['source_action_units'];b+=cost['native_sized_occurrence_bytes']
                if nrow['call_cut']:
                    calls[nrow['call_cut']]+=weight
                operations+=1
            require('block price '+identity+bid,(s,b)==(nb['source_action_units'],nb['native_sized_occurrence_bytes']))
            block_cost[bid]=(s,b,weight)
            src+=s*weight;native+=b*weight
        paths=terminal_paths(graph,identity)
        maxima=collections.Counter()
        for kind,path in paths:
            counts=collections.Counter(path)
            maxima |= counts
            require('bounded source and native path '+identity+str(len(checks)),all(n<=block_cost[bid][2] for bid,n in counts.items()) and entry_s+sum(block_cost[x][0] for x in path)<=src and entry_b+sum(block_cost[x][1] for x in path)<=native)
        report={'terminal_paths':len(paths),'terminal_kinds':dict(collections.Counter(k for k,_ in paths)),'max_block_occurrences':dict(maxima)}
        require('complete path mapping '+identity,report==load(P/'candidate.json')['path_report'][identity])
        require('function arithmetic and closed calls '+identity,(src,native,src+native)==(new['source_actions'],new['native_occurrence_allowance'],new['combined'])==(old['source_action_units_per_invocation'],old['native_sized_occurrence_bytes_per_invocation'],old['combined_surface_units_per_invocation']) and dict(calls)==new['calls_per_invocation_bound']==old['calls_per_invocation_bound']==accepted_review['call_union'][identity])
        role_count+=len(dimensions)
        logical_bytes+=sum(r['bytes'] for r in dimensions.values())
        functions.append({'id':identity,'roles':dimensions,'source':src,'native':native,'combined':src+native,'entry_source':entry_s,'entry_native':entry_b,'paths':report,'calls':dict(calls),'block_cost':{k:{'source':v[0],'native':v[1],'occurrence':v[2]} for k,v in block_cost.items()}})
    require('complete15/208/613/273/54 dimensions',(len(functions),role_count,operations,sum(f['paths']['terminal_paths'] for f in functions),len(shapes.used))==(15,208,613,273,54) and shapes.used==set(defs))
    require('actual source146 payload/wrapper shapes',shapes.leaves('OwnedFixtureOutcomeV1')==2556 and shapes.leaves("PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>")==2560 and sizes['OwnedFixtureOutcomeV1']==13608 and sizes["PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>"]==13624 and logical_bytes==234375 and closure_roles==4)
    drop=load(P/'drop-surface.json')
    drop_old=load(OLD/'drop-surface.json')
    require('exact10 inherited finite drop rows',drop['rows']==drop_old['rows'] and len(drop['rows'])==10)
    byid={f['id']:f for f in functions}
    drop_source=drop_native=0
    drop_evidence=[]
    for d in drop['rows']:
        operands=[byid[f]['roles'][n] for f,n in d['operand_selectors']]
        s=4+2*sum(r['scalar_leaves'] for r in operands)
        b=2*sum(r['bytes'] for r in operands)
        require('fresh finite drop arithmetic '+d['operation'],(s,b,s+b)==(d['source_action_units_each'],d['native_sized_occurrence_bytes_each'],d['combined_surface_units_each']) and d['occurrence_bound']>0)
        drop_source+=s*d['occurrence_bound'];drop_native+=b*d['occurrence_bound']
        drop_evidence.append({'operation':d['operation'],'source_each':s,'native_each':b,'occurrences':d['occurrence_bound']})
    require('take before payload drop and no refund in hook',re.search(rb'fn drop\(&mut self\).*?self\.owned\.take\(\).*?drop\(',source[APATH],re.S) is not None and drop['authored_P0_Drop_body_occurrences']==1 and drop['actual_payload_destructor_body_occurrences_bound']==1 and drop['actual_payload_destructor_body_priced_here'] is False)
    fixed_s=drop_source+sum(f['source'] for f in functions if f['id'] not in ('inspect_v1','usage_v1'))
    fixed_b=drop_native+sum(f['native'] for f in functions if f['id'] not in ('inspect_v1','usage_v1'))
    dims={'fixed_source':fixed_s,'fixed_native':fixed_b,'fixed_combined':fixed_s+fixed_b,'I':byid['inspect_v1']['combined'],'U':byid['usage_v1']['combined'],'finite_drop':drop_source+drop_native}
    require('complete formula arithmetic',dims=={'fixed_source':416998,'fixed_native':2211090,'fixed_combined':2628088,'I':194231,'U':1039,'finite_drop':131334})
    candidate=load(P/'candidate.json');interface=load(P/'cost-interface.json')
    require('cuts and symbolic occurrence counts retained',candidate['required_cuts']==accepted_review['required_unselected_cuts'] and candidate['symbolic_I_and_U_selected'] is False and interface['root_constructors_currently_pending'] and 'neither can default to zero' in interface['I_U'] and 'both explicit and positive' in interface['P5_component_composition'])
    require('no missing cost treated as zero',interface['operational_grant'] is False and 'P0_dynamic_backing' in interface['separate_required_terms'] and 'P5_actual_payload_destruction' in interface['separate_required_terms'] and 'P0 provisioned before' in ' '.join(interface['required_checks']))
    require('actual constructors remain pending',b'Err(RefusalV1::RootPolicyPending)' in source[APATH] and b'Err(RefusalV1::WholeQuotePending)' in source[APATH] and all('::Ok(' not in '\n'.join(r['code'] for b in new['blocks'].values() for r in b['lines']) for new in new_ledger if new['id'] in ('selected_parent_account_v1','selected_whole_quote_v1')))
    historical='Current pending constructors cannot price future successful bodies. Source146 needs new binding; no active composition evidence was read.'
    require('historical limitation exactly prior provenance',historical in candidate['limitations'] and historical in accepted_review['limitations'])
    # Mutation controls exercise the transfer boundary without altering inputs.
    require('semantic literal mutation refused',semantic(current[0].replace('const 0_u64','const 1_u64',1),new_prefix)!=semantic(previous[0],old_prefix))
    require('semantic control mutation refused',semantic(current[0].replace('return;','unreachable;',1),new_prefix)!=semantic(previous[0],old_prefix))
    require('unknown source root is not normalized',semantic(current[0].replace(new_prefix,'/unbound/vm'),new_prefix)!=semantic(previous[0],old_prefix))
    require('new call cannot inherit accepted body',semantic(current[0].replace('::checked_add(', '::new_callback(',1),new_prefix)!=semantic(previous[0],old_prefix))
    require('raw64bit header cannot substitute aggregate',sizes['OwnedFixtureOutcomeV1']!=8 and sizes["PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>"]!=8)
    for bad in ('UnknownNewProductV1','PrepaidOwnedV1<\'_, NewPayloadV1>','Result<u64>'):
        try:
            shapes.leaves(bad)
        except (ValueError,KeyError):
            require('unknown/specialization/arity refusal '+bad,True)
        else:
            raise AssertionError('unsupported shape accepted')
    # A changed scalar shape/native extent or missing row must alter arithmetic.
    first=next(f for f in functions if any(r['pointee_bytes']>8 for r in f['roles'].values()))
    require('native pointee surcharge present',sum(r['pointee_bytes'] for r in first['roles'].values())>8)
    require('drop omission changes fixed cost',dims['fixed_combined']-drop_source-drop_native!=dims['fixed_combined'])
    require('count omission changes symbolic quote',dims['I']>0 and dims['U']>0)
    return {
      'review.json': {'schema':1,'status':'independently-checked-source146-P0-account-surface-transfer-only','source_tree_sha256':S146,'source_members':146,'formula':'2628088 + 194231*I + 1039*U','dimensions':dims,'functions':15,'roles':208,'operations':613,'transitive_shapes':54,'terminal_paths':273,'retained_MIR_functions':19,'retained_MIR_roles':396,'native_queries':90,'logical_source_object_bytes':logical_bytes,'exact_closure_role_occurrences':closure_roles,'source_delta':source_delta,'required_unselected_cuts':accepted_review['required_unselected_cuts'],'historical_limitation_resolution':{'verbatim_prior_text':historical,'origin':'accepted source145 review, copied into source146 candidate','current_finding':'Exact source146 account-surface/MIR/layout binding is established by this review. The sentence is historical provenance, not a current binding failure. Future successful constructors and new root/caller/backing remain unpriced.'},'compiler_invoked':False,'producer_or_old_reviewer_executed':False,'product_or_native_invoked':False,'full_P0_or_host_quote_accepted':False,'selected_I_U_policy_root_fixture_or_grant':False,'P5_actual_payload_destruction_required_nonzero':True,'logical_allowance_is_CPU_physical_copy_storage_or_RSS_bound':False,'python':platform.python_version()},
      'MIR-binding.json':{'normalization':'Only exact bound old/new source roots and numeric .rs source spans; compiler comments excluded from semantic comparison. Full raw differences retained separately. All roles/operations/control/call targets otherwise exact. No optimization or type substitution normalization.','old_raw_sha256':digest(old_mir_raw),'new_raw_sha256':digest(fresh_mir_raw),'bodies':mir_results},
      'raw19-MIR-differences.patch.gz':gzip.compress(raw_patch.encode(),mtime=0),
      'compiler-binding.json':{'source146_keys':mkeys,'layout_diagnostic_keys':qkeys,'diagnostics':diagnostics,'exact_closure':closure,'current_compiler_invocations':0},
      'source-shape-binding.json':{'definitions':shape_evidence,'accepted_prior_source_tree':S145,'current_source_tree':S146,'byte_identical':True,'rule':'sum fields; enum tag plus max variant payload; accepted explicit standard primitive boundaries; concrete payload specialization only'},
      'recomputed-functions.json':{'functions':functions,'drop_rows':drop_evidence,'drop_source':drop_source,'drop_native':drop_native},
      'cleanup.json':{'schema':1,'owned_scratch_created':False,'compiler_or_product_or_native_process_created':False,'global_process_inventory':False,'cleanup_required':False,'frozen_inputs_mutated':False,'writes_only':str(HERE.relative_to(ROOT))},
    }

def main():
    out=audit()
    out['review.json']['checks']=len(checks)
    out['checks.json']={'checks':len(checks),'labels':checks}
    out['input-custody.json']={'schema':1,'files':dict(sorted(inputs.items()))}
    check='--check-only' in sys.argv
    for name,value in out.items():
        data=value if isinstance(value,bytes) else (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        if check:
            require('read-only reproduction '+name,(HERE/name).read_bytes()==data)
        else:
            (HERE/name).write_bytes(data)
    print(json.dumps({'passed':True,'checks':out['review.json']['checks'],'mode':'check-only' if check else 'independent-review','formula':out['review.json']['formula'],'source_tree_sha256':S146}))

if __name__=='__main__':
    main()
