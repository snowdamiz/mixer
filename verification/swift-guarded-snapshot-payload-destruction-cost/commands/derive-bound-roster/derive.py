#!/usr/bin/env python3
"""Compiler-free, closed-source payload ownership/cost derivation.

Only this packet is writable. Frozen programs are never imported or executed.
This fixed scanner checks exact released source, not arbitrary Rust or OTA code.
"""
from __future__ import annotations
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from model import Refused, evaluate_row, per_visit_maximum, returned_payload, compose_p5, U64

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V = ROOT / 'verification'
COMPOSE = V / 'swift-guarded-snapshot-host-composition'
INDEPENDENT = V / 'swift-guarded-snapshot-host-composition-independent'
BASE = V / 'swift-guarded-snapshot-funding-implementation/source/vm'
FULL = V / 'swift-guarded-snapshot-loader-work-source146'
PRIOR = V / 'swift-guarded-snapshot-parent-work-source146-independent'
SOURCE_TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST_TREE = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CONTROL = 'src/experimental_swift_reactor/control.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
CACHE = 'src/experimental_swift_reactor/cache.rs'
inputs, checks = {}, []


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def read(path):
    raw = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': sha(raw)}
    return raw
def load(path): return json.loads(read(path))
def require(label, condition):
    if not condition: raise AssertionError(label)
    checks.append(label)
def row(path, raw): return {'path': path, 'bytes': len(raw), 'sha256': sha(raw)}


def packet(folder, expected, count):
    raw = read(folder / 'seal.json')
    require('seal:' + folder.name, sha(raw) == expected)
    seal = json.loads(raw)
    require('packet-count:' + folder.name, len(seal['members']) == count)
    names = set()
    for member in seal['members']:
        p = member['path']
        require('safe-member:' + folder.name + '/' + p,
                p not in names and not Path(p).is_absolute() and '..' not in Path(p).parts)
        names.add(p)
        require('member:' + folder.name + '/' + p, row(p, read(folder / p)) == member)


def split_top(text, separator=','):
    pairs, stack, start, out = {'<': '>', '[': ']', '(': ')', '{': '}'}, [], 0, []
    for index, char in enumerate(text):
        if char in pairs: stack.append(pairs[char])
        elif char in '>])}':
            if not stack or stack.pop() != char: raise ValueError('unbalanced type')
        elif char == separator and not stack:
            out.append(text[start:index].strip()); start = index + 1
    if stack: raise ValueError('unfinished type')
    out.append(text[start:].strip())
    return [x for x in out if x]


def uncomment(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return '\n'.join(line.split('//', 1)[0] for line in text.splitlines())


def balanced(text, start):
    pairs, depth = {'{': '}', '(': ')'}, 1
    endchar = pairs[text[start]]
    end = start + 1
    while depth and end < len(text):
        depth += (text[end] == text[start]) - (text[end] == endchar)
        end += 1
    if depth: raise ValueError('unfinished declaration')
    return end


def declaration(source, path, name, expected=None):
    text = uncomment(source[path].decode())
    matches = []
    for match in re.finditer(r'\b(struct|enum)\s+' + re.escape(name) + r'\b', text):
        first = match.start()
        cursor = match.end()
        # This closed set uses only simple lifetimes/trait generic parameters.
        if text[cursor:cursor+1] == '<':
            close = text.index('>', cursor); cursor = close + 1
        while cursor < len(text) and text[cursor].isspace(): cursor += 1
        if text[cursor] not in '{(': continue
        end = balanced(text, cursor)
        part = text[first:end]
        if expected is None or sha(part.encode()) == expected:
            matches.append((match.group(1), text[cursor], part, text[cursor+1:end-1]))
    if len(matches) != 1: raise ValueError('ambiguous/missing declaration:' + path + ':' + name)
    kind, delimiter, part, body = matches[0]
    def fields(text):
        out = []
        for field in split_top(text):
            # Test-only state is absent from this accepted production compile.
            if '#[cfg(test)]' in field: continue
            field = re.sub(r'#\[[^]]*\]', '', field).strip()
            field = re.sub(r'^pub(?:\([^)]*\))?\s+', '', field)
            if ':' not in field: raise ValueError('untyped field:' + field)
            out.append(field.split(':', 1)[1].strip())
        return out
    result = {'kind': kind, 'path': path, 'declaration_sha256': sha(part.encode()), 'source_bytes': len(part.encode())}
    if delimiter == '(':
        result['fields'] = split_top(body)
    elif kind == 'struct':
        result['fields'] = fields(body)
    else:
        variants = []
        for variant in split_top(body):
            variant = re.sub(r'#\[[^]]*\]', '', variant).strip()
            match = re.match(r'(\w+)\s*(.*)', variant, re.S)
            name, rest = match.groups()
            if rest.startswith('{'):
                end = balanced(rest, 0); items = fields(rest[1:end-1])
            elif rest.startswith('('):
                end = balanced(rest, 0); items = split_top(rest[1:end-1])
            else: items = []
            variants.append({'name': name, 'fields': items})
        result['variants'] = variants
    return result


NEW = {
    'Cancellation': ('src/execute.rs', 'Cancellation'),
    'SelectedValidatedProfileV1': (LOADER, 'SelectedValidatedProfileV1'),
    'AdoptionBodyV1': (LOADER, 'AdoptionBodyV1'),
    'LoaderProvenanceV1': (LOADER, 'LoaderProvenanceV1'),
    'FileIdentityV1': (LOADER, 'FileIdentityV1'),
    'ValidatedSwiftReactor': ('src/experimental/swift.rs', 'ValidatedSwiftReactor'),
    'SwiftReactorObservations': ('src/experimental/swift.rs', 'SwiftReactorObservations'),
    'SwiftValidationBudget': ('src/experimental/swift.rs', 'SwiftValidationBudget'),
    'Metadata': ('src/experimental/metadata.rs', 'Metadata'),
    'Buffer': ('src/experimental/account.rs', 'Buffer'),
    'SwiftDeclaration': ('src/experimental/metadata.rs', 'SwiftDeclaration'),
    'Signature': ('src/experimental/metadata.rs', 'Signature'),
    'Import': ('src/experimental/metadata.rs', 'Import'),
    'Function': ('src/experimental/metadata.rs', 'Function'),
    'Global': ('src/experimental/metadata.rs', 'Global'),
    'Export': ('src/experimental/metadata.rs', 'Export'),
    'Segment': ('src/experimental/metadata.rs', 'Segment'),
    'MetaSpan': ('src/experimental/metadata.rs', 'Span'),
    'Type': ('src/lib.rs', 'Type'),
    'Policy': ('src/experimental/policy.rs', 'Policy'),
    'WasiFunction': ('src/experimental_wasi/descriptor.rs', 'WasiFunction'),
    'ValidatorResource': ('src/experimental/mod.rs', 'Resource'),
    'AdoptedProof': (CONTROL, 'AdoptedProof'),
    'ReservationTicket': (CONTROL, 'ReservationTicket'),
    'SwiftRunBudget': (CONTROL, 'SwiftRunBudget'),
    'RuntimeControl': (CONTROL, 'RuntimeControl'),
    'SnapshotScopeV1': (CONTROL, 'SnapshotScopeV1'),
    'SnapshotRunV1': (CONTROL, 'SnapshotRunV1'),
    'SwiftFunctionCache': (CACHE, 'SwiftFunctionCache'),
    'SwiftCacheUsage': (CACHE, 'SwiftCacheUsage'),
    'SwiftSlot': (CACHE, 'SwiftSlot'),
    'SwiftResident': (CACHE, 'SwiftResident'),
    'ScanPlan': (CACHE, 'ScanPlan'),
    'CacheConstructionFailure': (CACHE, 'CacheConstructionFailure'),
    'DecodedFunction': ('src/experimental/cache/mod.rs', 'DecodedFunction'),
    'PinRecord': ('src/experimental/cache/mod.rs', 'PinRecord'),
    'DecodedInstruction': ('src/experimental/cache/mod.rs', 'DecodedInstruction'),
    'Operation': ('src/experimental/cache/mod.rs', 'Operation'),
    'ControlKind': ('src/experimental/cache/mod.rs', 'ControlKind'),
    'Value': ('src/lib.rs', 'Value'),
    'Patch': ('src/experimental/cache/decode.rs', 'Patch'),
    'Counts': ('src/experimental/cache/decode.rs', 'Counts'),
    'AccountedWasi': ('src/experimental_wasi/accounted.rs', 'AccountedWasi'),
    'WasiContext': ('src/experimental_wasi/mod.rs', 'WasiContext'),
    'WasiSpan': ('src/experimental_wasi/mod.rs', 'Span'),
    'WasiGrants': ('src/experimental_wasi/mod.rs', 'WasiGrants'),
    'WasiBudget': ('src/experimental_wasi/mod.rs', 'WasiBudget'),
    'WasiOutcome': ('src/experimental_wasi/mod.rs', 'WasiOutcome'),
    'Errno': ('src/experimental_wasi/mod.rs', 'Errno'),
    'SnapshotOuterV1': (PROFILE, 'SnapshotOuterV1'),
    'InitialProfileConstructionOutcomeV1': (PROFILE, 'InitialProfileConstructionOutcomeV1'),
}


def type_name(text):
    text = text.strip()
    if text in ('SwiftMetadata',): return 'Metadata<SwiftDeclaration>'
    text = {'AError': 'SnapshotAdmissionErrorV1', 'Stop': 'SnapshotStopV1'}.get(text, text)
    # Exact qualified paths only. No general Rust name resolution is claimed.
    return re.sub(r'(?:(?:crate|super|experimental|experimental_swift_reactor|experimental_wasi|cache|control|initial_profile_v1|retained_profile_loader_v1|trusted_local_host_account_entry_v1|host_account_v1|swift|execute|metadata|decode|policy|std|option|result|fs|io|sync|atomic)::)+', '', text)


def merge_add(parts):
    result = collections.Counter()
    for part in parts: result.update(part)
    return dict(result)
def merge_max(parts):
    result = collections.Counter()
    for part in parts:
        for k, v in part.items(): result[k] = max(result[k], v)
    return dict(result)


class Graph:
    def __init__(self, definitions):
        self.definitions, self.used, self.frontiers, self.active = definitions, set(), {}, set()
    def walk(self, original, substitutions=None):
        text = type_name(original)
        for key, value in (substitutions or {}).items(): text = re.sub(r'\b' + key + r'\b', value, text)
        if text in self.active: raise ValueError('recursive-value:' + text)
        self.active.add(text)
        try:
            def seq(items):
                parts = [self.walk(x) for x in items]
                return {'nodes': 1 + sum(p['nodes'] for p in parts),
                        'resources': merge_add(p['resources'] for p in parts)}
            def variant(items):
                parts = [seq(x) for x in items]
                return {'nodes': 1 + max([0]+[p['nodes'] for p in parts]),
                        'resources': merge_max(p['resources'] for p in parts)}
            if text.startswith(('&', '*const ', '*mut ')):
                return {'nodes': 1, 'resources': {}} # borrowed referent is not destroyed
            if text in ('()', '!', 'u8', 'u16', 'u32', 'u64', 'u128', 'usize', 'i8', 'i16', 'i32', 'i64', 'i128', 'isize', 'bool', 'f32', 'f64', 'char', 'Instant', 'Duration'):
                return {'nodes': 1, 'resources': {}}
            if text.startswith('['):
                part, count = split_top(text[1:-1], ';'); count = int(count.replace('_', ''))
                if not 0 <= count <= 8192: raise ValueError('unbound array')
                value = self.walk(part)
                return {'nodes': 1 + count * value['nodes'], 'resources': {k: count*v for k,v in value['resources'].items()}}
            if text.startswith('(') and text.endswith(')'): return seq(split_top(text[1:-1]))
            head = text.split('<',1)[0]
            args = split_top(text[len(head)+1:-1]) if '<' in text else []
            if head in ('Option', 'Result'):
                if len(args) != (1 if head == 'Option' else 2): raise ValueError('bad-arity')
                return variant([[], args[:1]] if head == 'Option' else [[args[0]], [args[1]]])
            if head in ('File', 'Error', 'Arc', 'Box', 'Vec'):
                if head in ('Arc','Box','Vec') and len(args) != 1: raise ValueError('bad-resource-arity')
                key = text.replace(' ', '')
                self.frontiers[key] = {'type': text, 'required_positive': ['interface_work','native_resource_backing'],
                                      'unknown': True, 'body_observed_in_full_MIR': False}
                return {'nodes': 1, 'resources': {key: 1}}
            if head not in self.definitions: raise ValueError('unknown-closed-type:' + text)
            self.used.add(head)
            definition = self.definitions[head]
            substitutions = {}
            if head == 'Metadata':
                if args != ['SwiftDeclaration']: raise ValueError('wrong Metadata specialization')
                substitutions = {'D': 'SwiftDeclaration'}
            elif head == 'Buffer':
                if len(args) != 1: raise ValueError('wrong Buffer specialization')
                substitutions = {'T': args[0]}
            def sub(field):
                for k,v in substitutions.items(): field = re.sub(r'\b'+k+r'\b',v,field)
                return field
            if definition['kind'] == 'struct': return seq([sub(f) for f in definition['fields']])
            return variant([[sub(f) for f in v['fields']] for v in definition['variants']])
        finally: self.active.remove(text)


ENTRY_TYPES = ['File','Option<File>','ReturnedLoaderFilesV1','SetupOutcomeV1',
               'SelectedValidatedProfileV1','LoaderFailureV1','Cancellation']
LEAF_TYPES = ['SnapshotScopeV1','SnapshotRunV1','RuntimeControl','AdoptedProof',
              'SwiftFunctionCache','AccountedWasi','AdoptionBodyV1','Cancellation',
              'Option<AdoptedProof>','Option<SwiftFunctionCache>','Option<AccountedWasi>',
              'SnapshotOuterV1','SnapshotPrimaryRetirementV1']


def main():
    packet(COMPOSE, '2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e', 152)
    packet(INDEPENDENT, 'c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63', 96)
    acceptance = V / 'swift-semantic-adapter-root-review/guarded-snapshot-host-composition-host-acceptance.json'
    require('root-acceptance', sha(read(acceptance)) == 'c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8')
    manifest = load(COMPOSE / 'source-manifest.json')
    source = {}
    for member in manifest['members']:
        name = member['path']; overlay = COMPOSE / 'overlay/vm' / name
        raw = read(overlay if overlay.is_file() else BASE / name)
        require('actual-source:' + name, row(name, raw) == member); source[name] = raw
    require('source146-tree', sha(canonical(manifest['members'])) == SOURCE_TREE and len(source) == 146)
    host = load(COMPOSE / 'host-support-manifest.json')
    for member in host['members']:
        require('host-support:' + member['path'], row(member['path'], read(V / 'swift-real-profile-loader-binding/host' / member['path'])) == member)
    require('host11-tree', sha(canonical(host['members'])) == HOST_TREE and len(host['members']) == 11)
    proof = load(PRIOR / 'source-shape-binding.json')
    definitions, declaration_bindings = {}, []
    for d in proof['definitions']:
        actual = declaration(source, d['path'], d['name'], d['declaration_sha256'])
        if d['name'] == 'PrepaidOwnedV1':
            # The accepted shape names its one payload specialization. This
            # declaration remains input custody only and is never a P5 root.
            require('accepted-Prepaid-generic',actual['fields']==['Option<T>',"Option<ReservationV1<'a>>"])
            actual['fields'][0]=d['fields'][0]
        for field in ('kind','fields','variants'):
            if field not in d: continue
            wanted = d[field]
            if field == 'variants': wanted = [{k:v for k,v in x.items() if k in ('name','fields')} for x in wanted]
            require('accepted-shape:' + d['name'] + ':' + field, actual[field] == wanted)
        definitions[d['name']] = actual; declaration_bindings.append({'name':d['name'],**actual})
    for key, (path,name) in NEW.items():
        actual = declaration(source,path,name)
        # Resolve the two unrelated Span and Resource declarations explicitly.
        if path == 'src/experimental/metadata.rs':
            actual = json.loads(json.dumps(actual).replace('"Span"','"MetaSpan"'))
        if key == 'Buffer': actual['fields'] = ['Vec<T>','usize','ValidatorResource']
        if key == 'WasiContext': actual['fields'] = [x.replace('[Span;', '[WasiSpan;') for x in actual['fields']]
        definitions[key] = actual; declaration_bindings.append({'name':key,**actual})
    graph = Graph(definitions)
    sizes = load(INDEPENDENT / 'fresh-layout-results.json')['actual_type_sizes']
    known = {'File':sizes['std::fs::File'], 'Option<File>':sizes['std::option::Option<std::fs::File>'],
             'ReturnedLoaderFilesV1':sizes['experimental_swift_reactor::retained_profile_loader_v1::ReturnedLoaderFilesV1'],
             'SetupOutcomeV1':sizes['experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::SetupOutcomeV1'],
             'SelectedValidatedProfileV1':sizes['SelectedValidatedProfileV1'],
             'LoaderFailureV1':sizes['experimental_swift_reactor::retained_profile_loader_v1::LoaderFailureV1'],
             'Cancellation':sizes['execute::Cancellation'], 'OwnedFixtureOutcomeV1':sizes['OwnedFixtureOutcomeV1']}
    rows = []
    for typ in dict.fromkeys(['OwnedFixtureOutcomeV1']+ENTRY_TYPES+LEAF_TYPES):
        value = graph.walk(typ)
        nodes = value['nodes']; extent = known.get(typ)
        rows.append({'type':typ, 'structural_occurrence_allowance':nodes,
                     'inline_bytes':extent, 'finite_structural_native_allowance':None if extent is None else nodes*(1+extent),
                     'resource_frontiers':value['resources'],
                     'known_statically_reachable_product_authored_drop_callbacks':0,
                     'opaque_resource_callback_count':'unknown; required positive resource interface cut',
                     'missing_inline_layout_cut':None if extent is not None else 'qualified_inline_bytes<' + typ + '>'})
    # Inspect non-Copy vector element closure even though dynamic element count/
    # capacity is an unresolved positive resource frontier, never a finite loop.
    dynamic_elements = {}
    for typ in ['SwiftSlot','SwiftResident','DecodedFunction','PinRecord','Patch','Option<ScanPlan>',
                'Signature','Type','Import','Function','Global','Export','Segment','DecodedInstruction']:
        dynamic_elements[typ] = graph.walk(typ)
    slot = dynamic_elements['SwiftSlot']
    slot_row = {'type':'SwiftSlot','inline_bytes':None,'structural_occurrence_allowance':slot['nodes'],
                'resource_frontiers':slot['resources']}
    for r in rows:
        r['dynamic_resource_elements'] = {'Vec<SwiftSlot>':slot_row} if 'Vec<SwiftSlot>' in r['resource_frontiers'] else {}
    require('complete-dynamic-slot-children',slot['resources']=={'Vec<Type>':1,'Vec<DecodedInstruction>':1,'Vec<u32>':1})
    require('all-other-vector-elements-no-transitive-resource',all(not value['resources'] for name,value in dynamic_elements.items() if name not in ('SwiftSlot','SwiftResident','DecodedFunction')))
    # Whole immutable source audit: cfg(test) helpers are recorded, not mistaken
    # for compiler-enabled production Drop implementations.
    drops = []
    for path, raw in source.items():
        text = raw.decode(errors='strict')
        for m in re.finditer(r'impl(?:<[^\n]*>)?\s+(?:std::ops::)?Drop\s+for\s+([^\s{]+)',text):
            drops.append({'path':path,'type':m.group(1),'line':text.count('\n',0,m.start())+1})
    mir_archive = read(FULL / 'whole-source146.mir.gz')
    require('archive-identity', sha(mir_archive) == '03b5265c5ae85b3a444f847f1b65af8f31e9fee7697845d6f9699ddf2d8e87e7' and len(mir_archive)==3595856)
    mir = gzip.decompress(mir_archive)
    require('raw-MIR-identity',sha(mir)=='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2' and len(mir)==76655228)
    receipt = load(FULL / 'compiler-receipt.json')
    require('compile-only-receipt', receipt['exit_code']==0 and not receipt['product_runtime'] and receipt['source_tree_sha256']==SOURCE_TREE and receipt['host_support_members']==11)
    functions = re.split(r'(?=^fn )',mir.decode(),flags=re.M)
    observed_drop_headers = [f.splitlines()[0] for f in functions if f.startswith('fn ') and '::drop(' in f.splitlines()[0]]
    require('only-three-authored-drop-bodies',len(observed_drop_headers)==3 and sum('PrepaidOwnedV1' in h for h in observed_drop_headers)==1 and sum('SessionLease' in h for h in observed_drop_headers)==1 and sum('session::Reservation' in h for h in observed_drop_headers)==1)
    require('no-payload-session-ownership',not any('SessionLease' in json.dumps(definitions[x]) or 'session::Reservation' in json.dumps(definitions[x]) for x in graph.used))
    selected = {}
    for f in functions:
        h=f.splitlines()[0] if f else ''
        for name in ('setup_files_once_v1','run_prepaid_fixture_v1','run_one_loaded_fixture_v1','invoke_loaded_leaf_once_v1'):
            if h.startswith('fn '+name+'('): selected[name]=f
    require('four-entry-MIR-bodies',len(selected)==4)
    sites = {}
    for name,f in selected.items():
        sites[name] = [line.split('//',1)[0].strip() for line in f.splitlines() if re.search(r'\bdrop\(',line)]
    require('setup-seven-drop-sites',len(sites['setup_files_once_v1'])==7)
    require('caller-eleven-drop-sites',len(sites['run_prepaid_fixture_v1'])==11)
    require('leaf-two-drop-sites',len(sites['run_one_loaded_fixture_v1'])==2)
    require('forwarder-no-drop-sites',not sites['invoke_loaded_leaf_once_v1'])
    child=V/'swift-guarded-snapshot-child-entry-cost'
    packet(child,'68638fbe90b9de726b18441d8338dd018ea2ff701133c63636a5e393f5a647c9',28)
    release=V/'swift-semantic-adapter-root-review/guarded-snapshot-child-entry-cost-independent-release.json'
    require('child-release-as-data',sha(read(release))=='6bae895fc0291495745993340de7971467944c4e5ac1ff9ca4588b80ef49ce3e')
    child_ledger=load(child/'ledger.json')
    require('frozen-child-same-drop-roster',child_ledger['drop_sites']==[
        {'function':name,'repeat':6 if name=='setup_files_once_v1' else 1,'statement':statement}
        for name in ('setup_files_once_v1','run_prepaid_fixture_v1') for statement in sites[name]])
    require('frozen-child-same53-visits',child_ledger['during_entry_drop_visit_bound']==7*6+11)
    p0 = next(f for f in functions if f.startswith('fn ') and '::drop(' in f.splitlines()[0] and 'PrepaidOwnedV1' in f.splitlines()[0])
    require('take-before-payload-drop',p0.index('Option::<T>::take') < p0.index('std::mem::drop::<T>'))
    inventory = {'schema':1,'source_tree_sha256':SOURCE_TREE,'host_tree_sha256':HOST_TREE,
        'rows':rows,'entry_per_visit_types':ENTRY_TYPES,'leaf_typed_cut_types':LEAF_TYPES,
        'resource_frontiers':graph.frontiers,'dynamic_element_destructor_schemas':dynamic_elements,
        'declarations':declaration_bindings,'used_type_names':sorted(graph.used),
        'source_drop_implementations_including_test_only':drops,'observed_production_authored_drop_headers':observed_drop_headers,
        'during_entry_drop_sites':sites,'during_entry_visit_bound':7*6+11,
        'P0_wrapper_hook_excluded':True,'P5_returned_carrier_separately_required_positive':True,
        'actual_generated_drop_glue_observed':False,'private_standard_compiler_allocator_kernel_retry_cost_outside_logical_unit':True,
        'child_candidate_as_immutable_data_only':{'seal_sha256':'68638fbe90b9de726b18441d8338dd018ea2ff701133c63636a5e393f5a647c9',
        'per_visit_not_aggregate':True,'independently_accepted':False,'Arc_backing_probe_is_not_destructor_evidence':True},
        'whole_host_funded':False,'healthy_cleanup':False,'compiler_receipt':receipt}
    controls = test_controls(inventory)
    out = {'inventory.json':inventory,'controls.json':controls,
           'input-custody.json':{'schema':1,'files':inputs},
           'results.json':{'schema':1,'checks':len(checks),'controls':controls['checks'],
                           'source_tree_sha256':SOURCE_TREE,'host_tree_sha256':HOST_TREE,
                           'scope':'conditional pure component only; no unknown resource cut selected; no executable admission',
                           'status':'candidate-with-required-positive-cuts'}}
    if '--check-only' in sys.argv:
        for name,obj in out.items():
            require('reproduce:'+name,json.loads((HERE/name).read_bytes())==obj)
    else:
        for name,obj in out.items(): (HERE/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'checks':len(checks),'adversarial_controls':controls['checks'],'rows':len(rows),
                      'frontiers':len(graph.frontiers),'status':'conditional-candidate; no product execution'},sort_keys=True))


def test_controls(inventory):
    tested = []
    def ok(label, condition):
        require('control:'+label, condition); tested.append(label)
    def reject(label, callback):
        try: callback()
        except (Refused, ValueError, TypeError, KeyError): ok(label,True)
        else: raise AssertionError('control did not refuse:'+label)
    rows={r['type']:r for r in inventory['rows']}
    def sample_cuts(r):
        out={name:{'interface_work':1,'native_resource_backing':1} for name in r['resource_frontiers']}
        for name,element in r.get('dynamic_resource_elements',{}).items():
            out[name].update(max_live_elements=1,element_inline_bytes=1,element_cuts=sample_cuts(element))
        return out
    entry=[rows[t] for t in ENTRY_TYPES]
    resources={name for r in entry for name in r['resource_frontiers']}
    cuts={name:{'interface_work':1,'native_resource_backing':1} for name in resources}
    finite=per_visit_maximum(entry,cuts)
    ok('synthetic-unit-cut-component-positive',finite>0)
    returned=rows['OwnedFixtureOutcomeV1']
    rr=returned['resource_frontiers']
    ok('returned-complete-resource-maxima',rr=={'File':6,'Error':1,'Arc<AtomicBool>':1})
    selected=rows['SelectedValidatedProfileV1']['resource_frontiers']
    ok('selected-eight-copy-vectors-one-source-box',len(selected)==8 and sum(selected.values())==9 and selected['Vec<Segment>']==2 and selected['Box<[u8]>']==1)
    for name in sorted(resources):
        omitted=dict(cuts); del omitted[name]
        reject('omit:'+name,lambda:per_visit_maximum(entry,omitted))
        for field in ('interface_work','native_resource_backing'):
            for bad in (None,0,-1,True,1.5,'1',U64+1):
                changed={k:dict(v) for k,v in cuts.items()}; changed[name][field]=bad
                reject('bad-cut:'+name+':'+field+':'+repr(bad),lambda:per_visit_maximum(entry,changed))
            changed={k:dict(v) for k,v in cuts.items()}; del changed[name][field]
            reject('missing-cut-field:'+name+':'+field,lambda:per_visit_maximum(entry,changed))
    excess={**cuts,'unobserved::<T>':{'interface_work':1,'native_resource_backing':1}}
    reject('unknown-resource-cut',lambda:per_visit_maximum(entry,excess))
    reject('returned-payload-wrong-type',lambda:returned_payload(entry,cuts))
    for bad in (0,-1,None,True,U64+1):
        reject('missing-P5-carrier:'+repr(bad),lambda:compose_p5(bad,finite))
        reject('missing-P5-payload:'+repr(bad),lambda:compose_p5(finite,bad))
    reject('P5-overflow',lambda:compose_p5(U64,1))
    for r in inventory['rows']:
        local=sample_cuts(r)
        if r['inline_bytes'] is None:
            reject('missing-qualified-inline-extent:'+r['type'],lambda:evaluate_row(r,local))
            reject('zero-qualified-inline-extent:'+r['type'],lambda:evaluate_row(r,local,0))
        ok('all-known-conditional-row-positive:'+r['type'],evaluate_row(r,local,1)>0)
        huge=dict(r); huge['structural_occurrence_allowance']=U64
        reject('structural-multiplication-overflow:'+r['type'],lambda:evaluate_row(huge,local,1))
        if 'Vec<SwiftSlot>' in local:
            for field in ('max_live_elements','element_inline_bytes','element_cuts'):
                changed=sample_cuts(r);del changed['Vec<SwiftSlot>'][field]
                reject('omit-nested-slot:'+r['type']+':'+field,lambda:evaluate_row(r,changed,1))
            for field in ('max_live_elements','element_inline_bytes'):
                for bad in (None,0,-1,True,U64+1):
                    changed=sample_cuts(r);changed['Vec<SwiftSlot>'][field]=bad
                    reject('bad-nested-slot:'+r['type']+':'+field+':'+repr(bad),lambda:evaluate_row(r,changed,1))
            for name in local['Vec<SwiftSlot>']['element_cuts']:
                changed=sample_cuts(r);del changed['Vec<SwiftSlot>']['element_cuts'][name]
                reject('omit-nested-vector:'+r['type']+':'+name,lambda:evaluate_row(r,changed,1))
    for value in range(1,65):
        local={name:{'interface_work':value,'native_resource_backing':value} for name in resources}
        ok('resource-monotonic:'+str(value),per_visit_maximum(entry,local)>=finite)
    # A typed graph rejects unknown ownership, unsupported specializations,
    # unbalanced type spellings, and cycles; synthetic fields cannot disappear.
    g=Graph({'Owner':{'kind':'struct','fields':['File','Error']}})
    ok('synthetic-field-preservation',g.walk('Owner')['resources']=={'File':1,'Error':1})
    for text in ('NeverObserved','Metadata<Other>','Vec<>','Result<File>','[File; dynamic]'):
        reject('unknown-ownership:'+text,lambda:g.walk(text))
    cyc=Graph({'Cycle':{'kind':'struct','fields':['Cycle']}})
    reject('recursive-by-value',lambda:cyc.walk('Cycle'))
    ok('borrow-does-not-destroy-pointee',g.walk('&mut Owner')['resources']=={})
    choice=Graph({'Choice':{'kind':'enum','variants':[{'fields':['File']},{'fields':['Error']}]}})
    ok('enum-alternatives-retain-all-resource-kinds',choice.walk('Choice')['resources']=={'File':1,'Error':1})
    ok('array-owns-all-five-elements',g.walk('[Owner;5]')['resources']=={'File':5,'Error':5})
    before=g.walk('Owner')['resources']
    g.definitions['Owner']['fields']=['File']
    ok('field-omission-changes-complete-inventory',g.walk('Owner')['resources']!=before)
    for field in ('interface_work','native_resource_backing'):
        local={name:{'interface_work':1,'native_resource_backing':1} for name in rr}
        local['File'][field]=U64
        reject('resource-multiplication-overflow:'+field,lambda:evaluate_row(returned,local))
    return {'schema':1,'checks':len(tested),'passed':True,'controls':tested,
            'synthetic_numbers_are_policy_or_cut_selection':False}


if __name__=='__main__': main()
